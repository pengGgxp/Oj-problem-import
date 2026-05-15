"""
Docker 沙箱执行器 - 封装容器执行逻辑
"""
import docker
import tempfile
import os
import shutil
import re
import shlex
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable, Dict, List, Mapping, Optional
from .state import ExecutionResult
from .user_messages import format_user_friendly_error


CommandBuilder = Callable[[str], str]


def _quote(path: str) -> str:
    """Quote a path or shell argument for commands executed inside Linux containers."""
    return shlex.quote(path.replace("\\", "/"))


def _safe_stem(code_file: str) -> str:
    stem = Path(code_file).stem or "solution"
    return re.sub(r"[^A-Za-z0-9_.-]", "_", stem)


def _python_command(code_file: str) -> str:
    return f"python3 {_quote(code_file)}"


def _cpp_command(code_file: str) -> str:
    binary = f".sandbox_build/{_safe_stem(code_file)}"
    return (
        f"mkdir -p .sandbox_build && "
        f"g++ -std=c++17 -O2 -pipe -o {_quote(binary)} {_quote(code_file)} && "
        f"{_quote('./' + binary)}"
    )


def _c_command(code_file: str) -> str:
    binary = f".sandbox_build/{_safe_stem(code_file)}"
    return (
        f"mkdir -p .sandbox_build && "
        f"gcc -std=c11 -O2 -pipe -o {_quote(binary)} {_quote(code_file)} && "
        f"{_quote('./' + binary)}"
    )


def _java_command(code_file: str) -> str:
    # OJ Java submissions often use public class Main, but official solutions
    # may use a different public class name. Copy to the matching file name.
    quoted_code_file = _quote(code_file)
    return (
        "mkdir -p .sandbox_build/java && "
        "class_name=$(grep -E 'public[[:space:]]+class[[:space:]]+[A-Za-z_][A-Za-z0-9_]*' "
        f"{quoted_code_file} | head -n 1 | sed -E "
        "'s/.*public[[:space:]]+class[[:space:]]+([A-Za-z_][A-Za-z0-9_]*).*/\\1/') && "
        "if [ -z \"$class_name\" ]; then class_name=Main; fi && "
        f"cp {quoted_code_file} \".sandbox_build/java/$class_name.java\" && "
        "javac -d .sandbox_build/java \".sandbox_build/java/$class_name.java\" && "
        "java -cp .sandbox_build/java \"$class_name\""
    )


def _javascript_command(code_file: str) -> str:
    return f"node {_quote(code_file)}"


def _go_command(code_file: str) -> str:
    return (
        "mkdir -p .sandbox_build/go-cache .sandbox_build/go-tmp && "
        "GOCACHE=/workspace/.sandbox_build/go-cache "
        f"GOTMPDIR=/workspace/.sandbox_build/go-tmp go run {_quote(code_file)}"
    )


def _rust_command(code_file: str) -> str:
    binary = f".sandbox_build/{_safe_stem(code_file)}"
    return (
        f"mkdir -p .sandbox_build && "
        f"rustc -O {_quote(code_file)} -o {_quote(binary)} && "
        f"{_quote('./' + binary)}"
    )


@dataclass(frozen=True)
class RuntimeSpec:
    """Docker runtime information for one submission language."""

    language: str
    image: str
    extensions: tuple[str, ...]
    aliases: tuple[str, ...]
    command_builder: CommandBuilder


DEFAULT_RUNTIME_SPECS: Dict[str, RuntimeSpec] = {
    "python": RuntimeSpec(
        language="python",
        image="python:3.10-slim",
        extensions=(".py",),
        aliases=("py", "python", "python3", "pypy", "pypy3"),
        command_builder=_python_command,
    ),
    "cpp": RuntimeSpec(
        language="cpp",
        image="gcc:13",
        extensions=(".cpp", ".cc", ".cxx", ".c++"),
        aliases=("cpp", "c++", "c++17", "cpp17", "g++", "gnu++17"),
        command_builder=_cpp_command,
    ),
    "c": RuntimeSpec(
        language="c",
        image="gcc:13",
        extensions=(".c",),
        aliases=("c", "gcc", "gnu11", "c11"),
        command_builder=_c_command,
    ),
    "java": RuntimeSpec(
        language="java",
        image="eclipse-temurin:17",
        extensions=(".java",),
        aliases=("java", "jdk", "openjdk"),
        command_builder=_java_command,
    ),
    "javascript": RuntimeSpec(
        language="javascript",
        image="node:20-slim",
        extensions=(".js", ".mjs"),
        aliases=("js", "javascript", "node", "nodejs"),
        command_builder=_javascript_command,
    ),
    "go": RuntimeSpec(
        language="go",
        image="golang:1.22",
        extensions=(".go",),
        aliases=("go", "golang"),
        command_builder=_go_command,
    ),
    "rust": RuntimeSpec(
        language="rust",
        image="rust:1",
        extensions=(".rs",),
        aliases=("rs", "rust", "rustlang"),
        command_builder=_rust_command,
    ),
}


def _alias_key(value: str) -> str:
    return value.strip().lower().replace(" ", "").replace("-", "")


LANGUAGE_ALIASES: Dict[str, str] = {}
EXTENSION_TO_LANGUAGE: Dict[str, str] = {}
for _language, _spec in DEFAULT_RUNTIME_SPECS.items():
    LANGUAGE_ALIASES[_alias_key(_language)] = _language
    for _alias in _spec.aliases:
        LANGUAGE_ALIASES[_alias_key(_alias)] = _language
    for _extension in _spec.extensions:
        EXTENSION_TO_LANGUAGE[_extension.lower()] = _language


def get_supported_languages() -> List[str]:
    """Return canonical language names supported by the sandbox runtime registry."""
    return sorted(DEFAULT_RUNTIME_SPECS.keys())


def infer_language_from_filename(code_file: str) -> Optional[str]:
    """Infer a canonical language from a source file extension."""
    suffix = Path(code_file).suffix.lower()
    return EXTENSION_TO_LANGUAGE.get(suffix)


def normalize_language(language: str = "", code_file: str = "") -> str:
    """Normalize a user-facing language name or infer it from the source filename."""
    if language and language.strip():
        key = _alias_key(language)
        if key in LANGUAGE_ALIASES:
            return LANGUAGE_ALIASES[key]
        supported = ", ".join(get_supported_languages())
        raise ValueError(f"Unsupported language '{language}'. Supported languages: {supported}")

    inferred = infer_language_from_filename(code_file)
    if inferred:
        return inferred

    supported = ", ".join(get_supported_languages())
    raise ValueError(
        f"Cannot infer language from file '{code_file}'. "
        f"Pass language explicitly. Supported languages: {supported}"
    )


def build_runtime_specs(
    image_overrides: Optional[Mapping[str, str]] = None,
) -> Dict[str, RuntimeSpec]:
    """Build runtime specs with optional per-language Docker image overrides."""
    specs = dict(DEFAULT_RUNTIME_SPECS)
    for language, image in (image_overrides or {}).items():
        if not image:
            continue
        canonical = normalize_language(language)
        specs[canonical] = replace(specs[canonical], image=image)
    return specs


CommandBuilder = Callable[[str], str]


def _quote(path: str) -> str:
    """Quote a path or shell argument for commands executed inside Linux containers."""
    return shlex.quote(path.replace("\\", "/"))


def _safe_stem(code_file: str) -> str:
    stem = Path(code_file).stem or "solution"
    return re.sub(r"[^A-Za-z0-9_.-]", "_", stem)


def _python_command(code_file: str) -> str:
    return f"python3 {_quote(code_file)}"


def _cpp_command(code_file: str) -> str:
    binary = f".sandbox_build/{_safe_stem(code_file)}"
    return (
        f"mkdir -p .sandbox_build && "
        f"g++ -std=c++17 -O2 -pipe -o {_quote(binary)} {_quote(code_file)} && "
        f"{_quote('./' + binary)}"
    )


def _c_command(code_file: str) -> str:
    binary = f".sandbox_build/{_safe_stem(code_file)}"
    return (
        f"mkdir -p .sandbox_build && "
        f"gcc -std=c11 -O2 -pipe -o {_quote(binary)} {_quote(code_file)} && "
        f"{_quote('./' + binary)}"
    )


def _java_command(code_file: str) -> str:
    # OJ Java submissions often use public class Main, but official solutions
    # may use a different public class name. Copy to the matching file name.
    quoted_code_file = _quote(code_file)
    return (
        "mkdir -p .sandbox_build/java && "
        "class_name=$(grep -E 'public[[:space:]]+class[[:space:]]+[A-Za-z_][A-Za-z0-9_]*' "
        f"{quoted_code_file} | head -n 1 | sed -E "
        "'s/.*public[[:space:]]+class[[:space:]]+([A-Za-z_][A-Za-z0-9_]*).*/\\1/') && "
        "if [ -z \"$class_name\" ]; then class_name=Main; fi && "
        f"cp {quoted_code_file} \".sandbox_build/java/$class_name.java\" && "
        "javac -d .sandbox_build/java \".sandbox_build/java/$class_name.java\" && "
        "java -cp .sandbox_build/java \"$class_name\""
    )


def _javascript_command(code_file: str) -> str:
    return f"node {_quote(code_file)}"


def _go_command(code_file: str) -> str:
    return (
        "mkdir -p .sandbox_build/go-cache .sandbox_build/go-tmp && "
        "GOCACHE=/workspace/.sandbox_build/go-cache "
        f"GOTMPDIR=/workspace/.sandbox_build/go-tmp go run {_quote(code_file)}"
    )


def _rust_command(code_file: str) -> str:
    binary = f".sandbox_build/{_safe_stem(code_file)}"
    return (
        f"mkdir -p .sandbox_build && "
        f"rustc -O {_quote(code_file)} -o {_quote(binary)} && "
        f"{_quote('./' + binary)}"
    )


@dataclass(frozen=True)
class RuntimeSpec:
    """Docker runtime information for one submission language."""

    language: str
    image: str
    extensions: tuple[str, ...]
    aliases: tuple[str, ...]
    command_builder: CommandBuilder


DEFAULT_RUNTIME_SPECS: Dict[str, RuntimeSpec] = {
    "python": RuntimeSpec(
        language="python",
        image="python:3.10-slim",
        extensions=(".py",),
        aliases=("py", "python", "python3", "pypy", "pypy3"),
        command_builder=_python_command,
    ),
    "cpp": RuntimeSpec(
        language="cpp",
        image="gcc:13",
        extensions=(".cpp", ".cc", ".cxx", ".c++"),
        aliases=("cpp", "c++", "c++17", "cpp17", "g++", "gnu++17"),
        command_builder=_cpp_command,
    ),
    "c": RuntimeSpec(
        language="c",
        image="gcc:13",
        extensions=(".c",),
        aliases=("c", "gcc", "gnu11", "c11"),
        command_builder=_c_command,
    ),
    "java": RuntimeSpec(
        language="java",
        image="eclipse-temurin:17",
        extensions=(".java",),
        aliases=("java", "jdk", "openjdk"),
        command_builder=_java_command,
    ),
    "javascript": RuntimeSpec(
        language="javascript",
        image="node:20-slim",
        extensions=(".js", ".mjs"),
        aliases=("js", "javascript", "node", "nodejs"),
        command_builder=_javascript_command,
    ),
    "go": RuntimeSpec(
        language="go",
        image="golang:1.22",
        extensions=(".go",),
        aliases=("go", "golang"),
        command_builder=_go_command,
    ),
    "rust": RuntimeSpec(
        language="rust",
        image="rust:1",
        extensions=(".rs",),
        aliases=("rs", "rust", "rustlang"),
        command_builder=_rust_command,
    ),
}


def _alias_key(value: str) -> str:
    return value.strip().lower().replace(" ", "").replace("-", "")


LANGUAGE_ALIASES: Dict[str, str] = {}
EXTENSION_TO_LANGUAGE: Dict[str, str] = {}
for _language, _spec in DEFAULT_RUNTIME_SPECS.items():
    LANGUAGE_ALIASES[_alias_key(_language)] = _language
    for _alias in _spec.aliases:
        LANGUAGE_ALIASES[_alias_key(_alias)] = _language
    for _extension in _spec.extensions:
        EXTENSION_TO_LANGUAGE[_extension.lower()] = _language


def get_supported_languages() -> List[str]:
    """Return canonical language names supported by the sandbox runtime registry."""
    return sorted(DEFAULT_RUNTIME_SPECS.keys())


def infer_language_from_filename(code_file: str) -> Optional[str]:
    """Infer a canonical language from a source file extension."""
    suffix = Path(code_file).suffix.lower()
    return EXTENSION_TO_LANGUAGE.get(suffix)


def normalize_language(language: str = "", code_file: str = "") -> str:
    """Normalize a user-facing language name or infer it from the source filename."""
    if language and language.strip():
        key = _alias_key(language)
        if key in LANGUAGE_ALIASES:
            return LANGUAGE_ALIASES[key]
        supported = ", ".join(get_supported_languages())
        raise ValueError(f"Unsupported language '{language}'. Supported languages: {supported}")

    inferred = infer_language_from_filename(code_file)
    if inferred:
        return inferred

    supported = ", ".join(get_supported_languages())
    raise ValueError(
        f"Cannot infer language from file '{code_file}'. "
        f"Pass language explicitly. Supported languages: {supported}"
    )


def build_runtime_specs(
    image_overrides: Optional[Mapping[str, str]] = None,
) -> Dict[str, RuntimeSpec]:
    """Build runtime specs with optional per-language Docker image overrides."""
    specs = dict(DEFAULT_RUNTIME_SPECS)
    for language, image in (image_overrides or {}).items():
        if not image:
            continue
        canonical = normalize_language(language)
        specs[canonical] = replace(specs[canonical], image=image)
    return specs


class SandboxSession:
    """
    持久化沙箱会话
    
    在 Agent 生命周期内维护一个工作目录和容器,
    避免重复创建和文件写入。
    """
    
    def __init__(self, image: str = "python:3.10-slim",
                 mem_limit: str = "512m",
                 cpu_quota: int = 50000,
                 default_language: str = "python",
                 language_images: Optional[Mapping[str, str]] = None,
                 runtime_specs: Optional[Mapping[str, RuntimeSpec]] = None):
        """
        初始化沙箱会话
        
        Args:
            image: 默认语言 Docker 镜像名称
            mem_limit: 内存限制
            cpu_quota: CPU 配额(微秒)
            default_language: 默认执行语言
            language_images: 语言到 Docker 镜像的覆盖配置
            runtime_specs: 完整运行时配置（用于测试或高级自定义）
        """
        self.default_language = normalize_language(default_language)
        image_overrides = dict(language_images or {})
        if image:
            image_overrides.setdefault(self.default_language, image)

        self.runtime_specs = dict(runtime_specs) if runtime_specs else build_runtime_specs(image_overrides)
        self.image = self.runtime_specs[self.default_language].image
        self.mem_limit = mem_limit
        self.cpu_quota = cpu_quota
        self.container = None
        self.containers = {}
        self.work_dir = None
        self.client = None
        self._initialized = False
        
    def initialize(self, language: str = ""):
        """
        初始化沙箱会话:创建容器和工作目录
        """
        runtime_language = normalize_language(language or self.default_language)
        self._ensure_workspace()
        self._ensure_container(runtime_language)
        self._initialized = True

    def _ensure_docker_client(self):
        if self.client is not None:
            return

        try:
            # 初始化 Docker 客户端
            self.client = docker.from_env()
            self.client.ping()
        except docker.errors.DockerException as e:
            raise RuntimeError(format_user_friendly_error(e, action="连接 Docker")) from e

    def _ensure_workspace(self):
        if self.work_dir:
            return

        # 创建工作目录
        self.work_dir = tempfile.mkdtemp(prefix="oj_sandbox_")
        print(f"[SandboxSession] 创建工作目录: {self.work_dir}")

    def _ensure_container(self, language: str):
        if language in self.containers:
            self.container = self.containers[language]
            return

        self._ensure_docker_client()
        self._ensure_workspace()
        spec = self.runtime_specs[language]

        try:
            container = self.client.containers.run(
                image=spec.image,
                command="sleep infinity",
                detach=True,
                mem_limit=self.mem_limit,
                cpu_quota=self.cpu_quota,
                network_disabled=True,
                volumes={self.work_dir: {'bind': '/workspace', 'mode': 'rw'}},
                tmpfs={'/tmp': 'rw,noexec,nosuid,size=100m'},
                working_dir='/workspace'
            )
        except docker.errors.ImageNotFound as e:
            raise RuntimeError(
                f"Docker 镜像 {spec.image} 不存在或无法下载。\n"
                f"请确认网络可用后运行 `docker pull {spec.image}`，然后重试。"
            ) from e
        except docker.errors.DockerException as e:
            raise RuntimeError(format_user_friendly_error(e, action="启动 Docker 容器")) from e

        self.containers[language] = container
        self.container = container
        print(
            f"[SandboxSession] {language} 容器启动成功: "
            f"{container.short_id} ({spec.image})"
        )
    
    def cleanup(self):
        """
        清理沙箱会话:停止容器并删除工作目录
        """
        if not self._initialized and not self.work_dir:
            return
        
        # 停止并删除容器
        for language, container in list(self.containers.items()):
            try:
                container.remove(force=True)
                print(f"[SandboxSession] {language} 容器已清理: {container.short_id}")
            except Exception as e:
                print(f"[SandboxSession] 清理 {language} 容器失败: {e}")
        
        # 删除工作目录
        if self.work_dir:
            try:
                shutil.rmtree(self.work_dir, ignore_errors=True)
                print(f"[SandboxSession] 工作目录已清理: {self.work_dir}")
            except Exception as e:
                print(f"[SandboxSession] 清理工作目录失败: {e}")
        
        self._initialized = False
        self.container = None
        self.containers = {}
        self.work_dir = None
    
    def write_file(self, filename: str, content: str):
        """
        写入文件到工作目录
        
        Args:
            filename: 文件名
            content: 文件内容
        """
        if not self.work_dir:
            self._ensure_workspace()

        filepath = self._resolve_workspace_path(filename, create_parent=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  [SandboxSession] 写入文件: {filename} ({len(content)} bytes)")

    def _resolve_workspace_path(self, filename: str, create_parent: bool = False) -> Path:
        if not self.work_dir:
            self._ensure_workspace()

        root = Path(self.work_dir).resolve()
        filepath = (root / filename).resolve()
        try:
            filepath.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"Path escapes sandbox workspace: {filename}") from exc

        if create_parent:
            filepath.parent.mkdir(parents=True, exist_ok=True)

        return filepath
    
    def execute_command(self, cmd: str, timeout: int = 30, language: str = "") -> dict:
        """
        在容器中执行命令
        
        Args:
            cmd: 要执行的命令
            timeout: 超时时间(秒)
            language: 使用哪个语言运行时的容器
            
        Returns:
            dict 包含 stdout, stderr, exit_code
        """
        runtime_language = normalize_language(language or self.default_language)
        self.initialize(runtime_language)
        container = self.containers[runtime_language]
        
        # 将命令中的 /tmp 替换为 /workspace
        cmd = cmd.replace('/tmp', '/workspace')
        wrapped_cmd = self._with_timeout(cmd, timeout)
        print(f"  [SandboxSession:{runtime_language}] 执行: {cmd}")
        
        exec_result = container.exec_run(
            cmd=["/bin/sh", "-lc", wrapped_cmd],
            demux=True,
            workdir='/workspace'
        )
        
        stdout = exec_result.output[0].decode('utf-8', errors='ignore') if exec_result.output[0] else ""
        stderr = exec_result.output[1].decode('utf-8', errors='ignore') if exec_result.output[1] else ""
        
        return {
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": exec_result.exit_code
        }

    def _with_timeout(self, cmd: str, timeout: int) -> str:
        if timeout and timeout > 0:
            return f"timeout {int(timeout)}s /bin/sh -lc {shlex.quote(cmd)}"
        return cmd

    def execute_code_file(
        self,
        code_file: str,
        input_file: str = "",
        timeout: int = 30,
        language: str = "",
    ) -> dict:
        """
        按代码语言选择 Docker 运行时并执行源码文件。

        Args:
            code_file: 代码文件路径（相对于工作目录）
            input_file: 输入文件路径（可选）
            timeout: 超时时间(秒)
            language: 代码语言；为空时根据扩展名推断

        Returns:
            dict 包含 stdout, stderr, exit_code, language, image, command
        """
        runtime_language = normalize_language(language, code_file)
        spec = self.runtime_specs[runtime_language]
        cmd = spec.command_builder(code_file)
        if input_file:
            cmd = f"{cmd} < {_quote(input_file)}"

        result = self.execute_command(cmd, timeout=timeout, language=runtime_language)
        result.update({
            "language": runtime_language,
            "image": spec.image,
            "command": cmd,
        })
        return result
    
    def read_file(self, filename: str) -> str:
        """
        从工作目录读取文件内容
        
        Args:
            filename: 文件名
            
        Returns:
            文件内容字符串
        """
        if not self.work_dir:
            raise RuntimeError("沙箱尚未初始化")

        filepath = self._resolve_workspace_path(filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()


class SandboxExecutor:
    """
    Docker 沙箱执行器 (兼容旧接口)
    
    提供隔离的代码执行环境,支持:
    - 代码文件挂载
    - 命令序列执行
    - 资源限制(CPU/内存)
    - 执行结果捕获
    """
    
    def __init__(self, image: str = "python:3.10-slim", 
                 mem_limit: str = "512m",
                 cpu_quota: int = 50000):
        """
        初始化沙箱执行器
        
        Args:
            image: Docker 镜像名称
            mem_limit: 内存限制
            cpu_quota: CPU 配额(微秒)
        """
        self.image = image
        self.mem_limit = mem_limit
        self.cpu_quota = cpu_quota
        
        # 初始化 Docker 客户端,添加错误处理
        try:
            self.client = docker.from_env()
            # 测试连接
            self.client.ping()
        except docker.errors.DockerException as e:
            raise RuntimeError(format_user_friendly_error(e, action="连接 Docker")) from e
    
    def execute(self, files: Dict[str, str], commands: List[str], 
                timeout: int = 30) -> ExecutionResult:
        """
        在沙箱中执行代码
        
        Args:
            files: 文件字典 {文件名: 文件内容}
            commands: 要执行的命令列表
            timeout: 超时时间(秒)
            
        Returns:
            ExecutionResult: 执行结果
        """
        import tempfile
        import os
        
        container = None
        temp_dir = None
        
        try:
            # 创建临时目录
            temp_dir = tempfile.mkdtemp()
            print(f"[Sandbox] 创建临时目录: {temp_dir}")
            
            # 将文件写入临时目录
            for filename, content in files.items():
                filepath = os.path.join(temp_dir, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"  - 写入: {filename} ({len(content)} bytes)")
            
            # 启动容器,挂载临时目录
            container = self.client.containers.run(
                image=self.image,
                command="sleep infinity",
                detach=True,
                mem_limit=self.mem_limit,
                cpu_quota=self.cpu_quota,
                network_disabled=True,  # 禁用网络
                volumes={temp_dir: {'bind': '/workspace', 'mode': 'rw'}},  # 读写挂载
                tmpfs={'/tmp': 'rw,noexec,nosuid,size=100m'},  # 临时目录用于中间文件
                working_dir='/workspace'
            )
            
            print(f"[Sandbox] 容器启动成功,工作目录: /workspace")
            
            # 执行命令
            all_stdout = []
            all_stderr = []
            exit_code = 0
            
            for cmd in commands:
                # 将命令中的 /tmp 替换为 /workspace
                cmd = cmd.replace('/tmp', '/workspace')
                print(f"[Sandbox] 执行: {cmd}")
                
                exec_result = container.exec_run(
                    cmd=f"/bin/sh -c '{cmd}'",
                    demux=True,
                    workdir='/workspace'
                )
                
                stdout = exec_result.output[0].decode('utf-8', errors='ignore') if exec_result.output[0] else ""
                stderr = exec_result.output[1].decode('utf-8', errors='ignore') if exec_result.output[1] else ""
                
                all_stdout.append(stdout)
                all_stderr.append(stderr)
                
                if exec_result.exit_code != 0:
                    exit_code = exec_result.exit_code
                    break
            
            # 获取资源使用情况(简化版)
            stats = container.stats(stream=False)
            memory_usage = stats['memory_stats']['usage'] / (1024 * 1024) if 'memory_stats' in stats else 0
            
            # 判断执行状态
            status = "success"
            error_type = None
            
            if exit_code != 0:
                status = "fail"
                error_type = "runtime_error"
            
            combined_stderr = "\n".join(all_stderr)
            if "timeout" in combined_stderr.lower() or exit_code == 124:
                status = "timeout"
                error_type = "time_limit_exceeded"
            
            return ExecutionResult(
                status=status,
                exit_code=exit_code,
                stdout="\n".join(all_stdout),
                stderr=combined_stderr,
                execution_time=0.0,  # TODO: 精确计时需要更复杂的实现
                memory_usage=memory_usage,
                error_type=error_type
            )
            
        except docker.errors.ContainerError as e:
            return ExecutionResult(
                status="error",
                exit_code=-1,
                stderr=format_user_friendly_error(e, action="执行 Docker 容器"),
                error_type="container_error"
            )
        except Exception as e:
            return ExecutionResult(
                status="error",
                exit_code=-1,
                stderr=format_user_friendly_error(e, action="执行沙箱"),
                error_type="system_error"
            )
        finally:
            # 清理容器
            if container:
                try:
                    container.remove(force=True)
                except:
                    pass
            
            # 清理临时目录
            if temp_dir:
                try:
                    import shutil
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    print(f"[Sandbox] 清理临时目录: {temp_dir}")
                except:
                    pass
    
    def _write_to_container(self, container, filename: str, content: str):
        """
        将文件内容写入容器 (使用 exec_run 方法)
        
        Args:
            container: Docker 容器对象
            filename: 文件名
            content: 文件内容
        """
        import base64
        
        # 使用 base64 编码内容,通过 shell 命令写入文件
        encoded_content = base64.b64encode(content.encode('utf-8')).decode('ascii')
        cmd = f"echo '{encoded_content}' | base64 -d > /tmp/{filename}"
        
        result = container.exec_run(cmd)
        if result.exit_code != 0:
            detail = result.output.decode(errors="ignore").strip()
            raise RuntimeError(f"写入沙箱文件失败: {filename}。{detail}")

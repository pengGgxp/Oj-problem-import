"""
Docker 沙箱执行器 - 封装容器执行逻辑
"""
import docker
import tempfile
import os
from pathlib import Path
from typing import Dict, List
from .state import ExecutionResult


class SandboxExecutor:
    """
    Docker 沙箱执行器
    
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
            raise RuntimeError(
                f"无法连接到 Docker Daemon。请确保:\n"
                f"1. Docker Desktop 正在运行\n"
                f"2. Docker Daemon 已启动\n"
                f"3. 当前用户有 Docker 权限\n"
                f"错误详情: {str(e)}"
            )
    
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
                stderr=str(e),
                error_type="container_error"
            )
        except Exception as e:
            return ExecutionResult(
                status="error",
                exit_code=-1,
                stderr=str(e),
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
            raise RuntimeError(f"Failed to write file {filename}: {result.output.decode()}")

"""
Sandbox Tools for Agent - 沙箱执行工具集

提供基础工具供 ReAct Agent 调用:
- execute_code: 在 Docker 沙箱中执行 Python 代码文件
- write_code_file: 将代码写入沙箱工作目录的文件
- read_file_content: 读取沙箱中的文件内容
- edit_file_content: 编辑沙箱中的文件内容
- search_in_file: 在文件中搜索特定字符串
- delete_file: 删除沙箱中的文件
- save_outputs_to_host: 将沙箱中的产物复制到主机 outputs 目录
"""
from langchain_core.tools import tool
from ..sandbox import SandboxExecutor, SandboxSession
from ..config import settings
import json
import shutil
import sys
from pathlib import Path
from datetime import datetime

# 全局沙箱会话(由 Agent 管理)
_global_sandbox_session: SandboxSession = None


def set_global_sandbox_session(session: SandboxSession):
    """
    设置全局沙箱会话
    
    Args:
        session: SandboxSession 实例
    """
    global _global_sandbox_session
    _global_sandbox_session = session


def get_sandbox_session() -> SandboxSession:
    """
    获取当前沙箱会话
    
    Returns:
        SandboxSession 实例,如果没有则创建临时会话
    """
    if _global_sandbox_session is not None:
        return _global_sandbox_session
    # 如果没有全局会话,创建一个临时的(向后兼容)
    return SandboxSession()


# ============================================================================
# Layer 1: 基础执行工具
# ============================================================================

@tool
def execute_code(code_file: str, input_file: str = "", timeout: int = 5) -> dict:
    """
    在 Docker 沙箱中执行 Python 代码文件并返回输出结果。
    
    Args:
        code_file: 代码文件路径（相对于工作目录），如 "solution.py"
        input_file: 输入文件路径（可选），如 "input.txt"
        timeout: 超时时间(秒),默认5秒
        
    Returns:
        dict 包含:
        - stdout: 标准输出
        - stderr: 标准错误
        - exit_code: 退出码 (0表示成功)
        - execution_time: 执行时间(秒)
        - memory_usage: 内存使用(MB)
        - status: "success" 或 "error"
        
    Example:
        >>> # 先写入文件
        >>> session.write_file("main.py", "print('hello')")
        >>> # 再执行
        >>> execute_code("main.py")
        {'stdout': 'hello\\n', 'stderr': '', 'exit_code': 0, ...}
    """
    session = get_sandbox_session()
    
    try:
        # 构建命令
        cmd = f"python3 {code_file}"
        if input_file:
            cmd = f"{cmd} < {input_file}"
        
        # 执行命令
        result = session.execute_command(cmd, timeout=timeout)
        
        # 获取资源使用情况(简化版)
        stats = session.container.stats(stream=False) if session.container else {}
        memory_usage = stats['memory_stats']['usage'] / (1024 * 1024) if 'memory_stats' in stats else 0
        
        # 判断执行状态
        status = "success"
        error_type = None
        
        if result["exit_code"] != 0:
            status = "fail"
            error_type = "runtime_error"
        
        combined_stderr = result["stderr"]
        if "timeout" in combined_stderr.lower() or result["exit_code"] == 124:
            status = "timeout"
            error_type = "time_limit_exceeded"
        
        return {
            "stdout": result["stdout"],
            "stderr": result["stderr"],
            "exit_code": result["exit_code"],
            "execution_time": 0.0,  # TODO: 精确计时需要更复杂的实现
            "memory_usage": memory_usage,
            "status": status
        }
        
    except Exception as e:
        return {
            "status": "error",
            "stderr": str(e),
            "exit_code": -1,
            "execution_time": 0,
            "memory_usage": 0
        }


@tool
def write_code_file(filename: str, code: str) -> dict:
    """
    将代码写入沙箱工作目录的文件。
    
    Args:
        filename: 文件名（如 "solution.py", "generator.py"）
        code: 代码内容
        
    Returns:
        dict 包含:
        - success: 是否成功
        - filepath: 文件路径
        - size: 文件大小(bytes)
        
    Example:
        >>> write_code_file("solution.py", "print('hello')")
        {'success': True, 'filepath': 'solution.py', 'size': 14}
    """
    session = get_sandbox_session()
    
    try:
        session.write_file(filename, code)
        return {
            "success": True,
            "filepath": filename,
            "size": len(code.encode('utf-8'))
        }
    except Exception as e:
        return {
            "success": False,
            "filepath": filename,
            "size": 0,
            "error": str(e)
        }


@tool
def read_file_content(filename: str, start_line: int = 1, max_lines: int = 100) -> dict:
    """
    读取沙箱工作目录中的文件内容。
    
    支持分页读取，可以指定起始行数和最大行数，适合处理大文件。
    
    Args:
        filename: 文件路径（相对于工作目录），如 "solution.py"
        start_line: 起始行号（从1开始），默认1
        max_lines: 最大读取行数，默认100行（防止读取过大文件）
        
    Returns:
        dict 包含:
        - success: 是否成功
        - content: 文件内容
        - lines: 总行数
        - start_line: 实际起始行号
        - end_line: 实际结束行号
        - preview: 内容预览（前500字符）
        
    Example:
        >>> # 读取前100行
        >>> read_file_content("solution.py")
        {'success': True, 'content': '...', 'lines': 250, 'start_line': 1, 'end_line': 100}
        
        >>> # 读取第101-200行
        >>> read_file_content("solution.py", start_line=101)
        {'success': True, 'content': '...', 'lines': 250, 'start_line': 101, 'end_line': 200}
    """
    session = get_sandbox_session()
    
    try:
        content = session.read_file(filename)
        lines = content.split('\n')
        total_lines = len(lines)
        
        # 验证起始行号
        if start_line < 1:
            start_line = 1
        if start_line > total_lines:
            return {
                "success": False,
                "content": "",
                "lines": total_lines,
                "start_line": start_line,
                "end_line": start_line,
                "preview": "",
                "error": f"Start line {start_line} exceeds total lines {total_lines}"
            }
        
        # 计算结束行号
        end_line = min(start_line + max_lines - 1, total_lines)
        
        # 截取指定范围的行
        selected_lines = lines[start_line - 1:end_line]
        selected_content = '\n'.join(selected_lines)
        
        # 如果还有更多内容，添加提示
        if end_line < total_lines:
            remaining = total_lines - end_line
            selected_content += f"\n... ({remaining} more lines, use start_line={end_line + 1} to continue)"
        
        return {
            "success": True,
            "content": selected_content,
            "lines": total_lines,
            "start_line": start_line,
            "end_line": end_line,
            "preview": selected_content[:500]
        }
        
    except FileNotFoundError:
        return {
            "success": False,
            "content": "",
            "lines": 0,
            "start_line": start_line,
            "end_line": start_line,
            "preview": "",
            "error": f"File not found: {filename}"
        }
    except Exception as e:
        return {
            "success": False,
            "content": "",
            "lines": 0,
            "start_line": start_line,
            "end_line": start_line,
            "preview": "",
            "error": str(e)
        }


@tool
def edit_file_content(filename: str, old_text: str, new_text: str, replace_all: bool = False) -> dict:
    """
    编辑沙箱工作目录中的文件内容。
    
    支持精确替换文本，可以替换所有匹配项或仅替换第一个匹配项。
    
    Args:
        filename: 文件路径（相对于工作目录），如 "solution.py"
        old_text: 要替换的原文本
        new_text: 替换后的新文本
        replace_all: 是否替换所有匹配项，默认False（只替换第一个）
        
    Returns:
        dict 包含:
        - success: 是否成功
        - replacements: 替换次数
        - new_content_preview: 新内容预览（前300字符）
        
    Example:
        >>> edit_file_content("solution.py", "print('old')", "print('new')")
        {'success': True, 'replacements': 1, 'new_content_preview': "print('new')..."}
    """
    session = get_sandbox_session()
    
    try:
        # 读取原文件
        content = session.read_file(filename)
        
        # 统计替换次数
        if replace_all:
            new_content = content.replace(old_text, new_text)
            replacements = content.count(old_text)
        else:
            new_content = content.replace(old_text, new_text, 1)
            replacements = 1 if old_text in content else 0
        
        if replacements == 0:
            return {
                "success": False,
                "replacements": 0,
                "new_content_preview": "",
                "error": f"Text not found in file: {old_text[:50]}"
            }
        
        # 写回文件
        session.write_file(filename, new_content)
        
        return {
            "success": True,
            "replacements": replacements,
            "new_content_preview": new_content[:300],
            "message": f"Replaced {replacements} occurrence(s)"
        }
        
    except FileNotFoundError:
        return {
            "success": False,
            "replacements": 0,
            "new_content_preview": "",
            "error": f"File not found: {filename}"
        }
    except Exception as e:
        return {
            "success": False,
            "replacements": 0,
            "new_content_preview": "",
            "error": str(e)
        }


@tool
def search_in_file(filename: str, search_text: str, case_sensitive: bool = True, max_results: int = 20) -> dict:
    """
    在文件中搜索特定字符串，返回匹配位置和上下文。
    
    Args:
        filename: 文件路径（相对于工作目录），如 "solution.py"
        search_text: 要搜索的文本
        case_sensitive: 是否区分大小写，默认True
        max_results: 最大返回结果数，默认20
        
    Returns:
        dict 包含:
        - success: 是否成功
        - matches: 匹配列表，每个包含 {line_number, line_content, position}
        - total_matches: 总匹配数
        
    Example:
        >>> search_in_file("solution.py", "def main")
        {'success': True, 'matches': [{'line_number': 5, 'line_content': 'def main():', ...}], 'total_matches': 1}
    """
    session = get_sandbox_session()
    
    try:
        content = session.read_file(filename)
        lines = content.split('\n')
        
        matches = []
        total_count = 0
        
        for line_num, line in enumerate(lines, 1):
            # 根据大小写敏感性进行搜索
            if case_sensitive:
                search_line = line
                search_term = search_text
            else:
                search_line = line.lower()
                search_term = search_text.lower()
            
            # 查找所有匹配位置
            start = 0
            while True:
                pos = search_line.find(search_term, start)
                if pos == -1:
                    break
                
                total_count += 1
                
                # 只收集前 max_results 个结果
                if len(matches) < max_results:
                    # 提取上下文（前后各50字符）
                    context_start = max(0, pos - 50)
                    context_end = min(len(line), pos + len(search_text) + 50)
                    context = line[context_start:context_end]
                    
                    matches.append({
                        "line_number": line_num,
                        "line_content": line.strip(),
                        "position": pos,
                        "context": context
                    })
                
                start = pos + 1
        
        return {
            "success": True,
            "matches": matches,
            "total_matches": total_count,
            "message": f"Found {total_count} match(es)"
        }
        
    except FileNotFoundError:
        return {
            "success": False,
            "matches": [],
            "total_matches": 0,
            "error": f"File not found: {filename}"
        }
    except Exception as e:
        return {
            "success": False,
            "matches": [],
            "total_matches": 0,
            "error": str(e)
        }


@tool
def delete_file(filename: str) -> dict:
    """
    删除沙箱工作目录中的文件。
    
    Args:
        filename: 文件路径（相对于工作目录），如 "temp.py"
        
    Returns:
        dict 包含:
        - success: 是否成功
        - message: 操作结果说明
        
    Example:
        >>> delete_file("temp.py")
        {'success': True, 'message': 'File deleted: temp.py'}
    """
    session = get_sandbox_session()
    
    if not session._initialized or not session.work_dir:
        return {
            "success": False,
            "message": "",
            "error": "Sandbox session not initialized"
        }
    
    try:
        import os
        filepath = os.path.join(session.work_dir, filename)
        
        # 检查文件是否存在
        if not os.path.exists(filepath):
            return {
                "success": False,
                "message": "",
                "error": f"File not found: {filename}"
            }
        
        # 检查是否是文件（防止误删目录）
        if not os.path.isfile(filepath):
            return {
                "success": False,
                "message": "",
                "error": f"Not a file: {filename}"
            }
        
        # 删除文件
        os.remove(filepath)
        
        return {
            "success": True,
            "message": f"File deleted: {filename}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": "",
            "error": str(e)
        }


@tool
def save_outputs_to_host(problem_title: str = "unnamed") -> dict:
    """
    将沙箱工作目录中的产物复制到主机的 outputs 目录。
    
    从沙箱的 /workspace 目录复制所有文件到项目的 outputs/{timestamp}_{title} 目录。
    
    Args:
        problem_title: 题目标题，用于命名输出目录
        
    Returns:
        dict 包含:
        - success: 是否成功
        - output_path: 主机上的输出目录路径
        - files_copied: 复制的文件列表
        
    Example:
        >>> save_outputs_to_host("A+B Problem")
        {'success': True, 'output_path': 'outputs/20260510_123456_A_B_Problem', ...}
    """
    session = get_sandbox_session()
    
    if not session._initialized or not session.work_dir:
        return {
            "success": False,
            "output_path": "",
            "files_copied": [],
            "error": "Sandbox session not initialized"
        }
    
    try:
        # 创建输出目录
        # 获取程序运行目录（支持 exe 和 Python 脚本）
        if getattr(sys, 'frozen', False):
            # 打包成 exe 的情况：使用 sys._MEIPASS (PyInstaller) 或当前工作目录
            # Nuitka onefile 模式下，使用 os.getcwd() 获取 exe 运行目录
            import os
            project_root = Path(os.getcwd())
        else:
            # Python 脚本运行的情况：获取项目根目录
            project_root = Path(__file__).parent.parent.parent  # oj_engine/tools -> oj_engine -> project root
        
        output_base = project_root / "outputs"
        output_base.mkdir(parents=True, exist_ok=True)
        
        # 生成带时间戳的目录名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = _sanitize_filename(problem_title)
        output_path = output_base / f"{timestamp}_{safe_title}"
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 复制沙箱工作目录的所有内容
        files_copied = []
        sandbox_work_dir = Path(session.work_dir)
        
        for item in sandbox_work_dir.iterdir():
            if item.is_file():
                dest = output_path / item.name
                shutil.copy2(item, dest)
                files_copied.append(item.name)
            elif item.is_dir():
                dest = output_path / item.name
                shutil.copytree(item, dest, dirs_exist_ok=True)
                # 记录目录中的文件
                for file in item.rglob('*'):
                    if file.is_file():
                        rel_path = file.relative_to(sandbox_work_dir)
                        files_copied.append(str(rel_path))
        
        print(f"[save_outputs_to_host] Copied {len(files_copied)} files to {output_path}")
        
        return {
            "success": True,
            "output_path": str(output_path),
            "files_copied": files_copied,
            "message": f"Successfully saved outputs to {output_path}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "output_path": "",
            "files_copied": [],
            "error": str(e)
        }


def _sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除非法字符
    
    Args:
        filename: 原始文件名
        
    Returns:
        清理后的文件名
    """
    # 移除非法字符
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # 限制长度
    if len(filename) > 50:
        filename = filename[:50]
    
    return filename.strip()



"""
oj problem import - AI OJ Content Engine

采用 ReAct Agent 架构,让 AI 自主决策执行流程。
"""
import warnings

warnings.filterwarnings(
    "ignore",
    message=r"The default value of `allowed_objects` will change in a future version.*",
)

# Agent 模式
from .agent import ProblemGenerationAgent
from .tools import (
    execute_code,
    supported_sandbox_languages,
    write_code_file,
    read_file_content,
    edit_file_content,
    search_in_file,
    delete_file,
    save_outputs_to_host,
)

# 底层支持
from .sandbox import SandboxExecutor
from .config import Settings, settings, get_settings

# 多任务处理
from .task_models import TaskItem, TaskBatch, TaskStatus
from .task_worker import TaskWorker
from .task_scheduler import TaskScheduler
from .file_scanner import FileScanner

__all__ = [
    # Agent
    "ProblemGenerationAgent",
    
    # Tools
    "execute_code",
    "supported_sandbox_languages",
    "write_code_file",
    "read_file_content",
    "edit_file_content",
    "search_in_file",
    "delete_file",
    "save_outputs_to_host",
    
    # Core
    "SandboxExecutor",
    "Settings",
    "settings",
    "get_settings",
    
    # Multi-task Processing
    "TaskItem",
    "TaskBatch",
    "TaskStatus",
    "TaskWorker",
    "TaskScheduler",
    "FileScanner",
]

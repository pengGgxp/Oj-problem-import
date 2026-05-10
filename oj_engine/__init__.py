"""
OJ Engine - AI OJ Content Engine

采用 ReAct Agent 架构,让 AI 自主决策执行流程。
"""
# Agent 模式
from .agent import ProblemGenerationAgent
from .tools import (
    execute_code,
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

__all__ = [
    # Agent
    "ProblemGenerationAgent",
    
    # Tools
    "execute_code",
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
]

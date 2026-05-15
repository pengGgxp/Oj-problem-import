"""
Task Models - 任务模型定义

定义多任务处理系统中的数据结构和状态枚举。
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List
from pathlib import Path


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TaskItem:
    """单个任务项"""
    task_id: str
    file_path: Path
    problem_title: str
    status: TaskStatus = TaskStatus.PENDING
    error_message: Optional[str] = None
    output_path: Optional[Path] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    base_path: str = ""  # 用于保持目录结构的基础路径
    execution_log: str = ""  # 子进程内捕获的执行日志，避免并行输出互相穿插
    
    def duration(self) -> Optional[float]:
        """计算任务执行时长（秒）"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None


@dataclass
class TaskBatch:
    """任务批次"""
    batch_id: str
    tasks: List[TaskItem] = field(default_factory=list)
    max_workers: int = 4
    created_at: float = 0.0

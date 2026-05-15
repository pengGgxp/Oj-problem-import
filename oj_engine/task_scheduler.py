"""
Task Scheduler - 任务调度器

管理多任务并行执行，提供失败隔离和重试机制。
"""
from concurrent.futures import ProcessPoolExecutor, as_completed
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from io import StringIO
from typing import List, Dict, Any
import traceback
import sys

from .agent import ProblemGenerationAgent
from .task_models import TaskItem, TaskStatus
from .task_worker import TaskWorker
import time
import logging

# 配置日志
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TaskScheduler:
    """任务调度器 - 管理多任务并行执行"""
    
    MAX_TASK_LOG_CHARS = 120_000

    def __init__(
        self,
        max_workers: int = 4,
        max_retries: int = 2,
        max_iterations: int = 20,
        show_logs: bool = False,
        log_lines: int = 40,
    ):
        """
        初始化调度器
        
        Args:
            max_workers: 最大并行工作进程数
            max_retries: 单个任务最大重试次数
            max_iterations: 单个任务 Agent 最大迭代轮次
            show_logs: 是否按任务分组打印完整执行日志
            log_lines: 失败任务默认展示的日志尾部行数
        """
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.max_iterations = max_iterations
        self.show_logs = show_logs
        self.log_lines = log_lines
        self.results: List[TaskItem] = []
    
    def run_batch(self, tasks: List[TaskItem]) -> List[TaskItem]:
        """
        执行任务批次
        
        Args:
            tasks: 任务列表
            
        Returns:
            完成的任务列表（包含状态）
        """
        total = len(tasks)
        logger.debug(f"Starting batch execution: {total} tasks, {self.max_workers} workers")
        
        print(f"\n{'='*80}")
        print(f"批量任务执行")
        print(f"{'='*80}")
        print(f"总任务数: {total}")
        print(f"并行进程: {self.max_workers}")
        print(f"Agent 最大迭代轮次: {self.max_iterations}")
        print(
            "LangGraph 图步数上限: "
            f"{ProblemGenerationAgent.get_graph_recursion_limit(self.max_iterations)}"
        )
        print(f"最大重试: {self.max_retries}")
        if self.show_logs:
            print("日志显示: 按任务分组显示完整日志")
        else:
            print(f"日志显示: 仅失败任务显示最后 {self.log_lines} 行")
        print(f"{'='*80}\n")

        print("任务队列:")
        for idx, task in enumerate(tasks, 1):
            print(f"  {idx:>3}. [{task.task_id}] {task.problem_title} | {task.file_path}")
        print()
        
        completed_tasks = []
        success_count = 0
        failed_count = 0
        
        # 使用进程池并行执行
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_task = {}
            for task in tasks:
                future = executor.submit(self._execute_with_retry, task)
                future_to_task[future] = task
            
            # 收集结果
            for idx, future in enumerate(as_completed(future_to_task), 1):
                task = future_to_task[future]
                try:
                    completed_task = future.result()
                    completed_tasks.append(completed_task)
                    
                    if completed_task.status == TaskStatus.SUCCESS:
                        success_count += 1
                        status_label = "OK"
                    else:
                        failed_count += 1
                        status_label = "FAIL"
                    
                    self._print_task_completion(idx, total, completed_task, status_label)
                    
                except Exception as e:
                    logger.debug(f"Task {task.task_id} failed with exception: {e}")
                    task.status = TaskStatus.FAILED
                    task.error_message = str(e)
                    task.execution_log = traceback.format_exc()
                    completed_tasks.append(task)
                    failed_count += 1
                    
                    self._print_task_completion(idx, total, task, "FAIL")
        
        # 排序：成功的在前，失败的在后
        completed_tasks.sort(key=lambda t: (t.status != TaskStatus.SUCCESS, t.start_time or 0))
        
        self.results = completed_tasks
        
        # 打印总结
        print(f"\n{'='*80}")
        print(f"执行完成")
        print(f"{'='*80}")
        print(f"成功: {success_count}")
        print(f"失败: {failed_count}")
        print(f"总计: {total}")
        if total > 0:
            print(f"成功率: {success_count/total*100:.1f}%")
        print(f"{'='*80}\n")
        
        return completed_tasks
    
    def _execute_with_retry(self, task: TaskItem) -> TaskItem:
        """
        带重试机制的任务执行（在独立进程中运行）
        
        Args:
            task: 任务项
            
        Returns:
            完成的任务项
        """
        worker = TaskWorker(max_iterations=self.max_iterations)
        last_error = None
        logs: List[str] = []
        
        for attempt in range(1, self.max_retries + 1):
            buffer = StringIO()
            with self._capture_task_output(buffer):
                print(f"[Task {task.task_id}] 尝试 {attempt}/{self.max_retries}")
                try:
                    result = worker.execute_task(task)
                    if result.status == TaskStatus.SUCCESS:
                        logs.append(self._format_attempt_log(attempt, buffer.getvalue()))
                        result.execution_log = self._merge_logs(logs)
                        return result

                    last_error = result.error_message
                    print(f"[Task {task.task_id}] 尝试失败: {last_error or 'Unknown error'}")

                except Exception as e:
                    last_error = str(e)
                    task.status = TaskStatus.FAILED
                    task.error_message = str(e)
                    print(f"[Task {task.task_id}] 尝试异常: {e}")
                    traceback.print_exc()

            logs.append(self._format_attempt_log(attempt, buffer.getvalue()))
        
        # 所有重试都失败
        task.status = TaskStatus.FAILED
        task.error_message = f"All {self.max_retries} attempts failed. Last error: {last_error}"
        task.execution_log = self._merge_logs(logs)
        return task

    def _print_task_completion(
        self,
        idx: int,
        total: int,
        task: TaskItem,
        status_label: str,
    ):
        """按任务分组打印完成状态，避免并行日志交错。"""
        duration = task.duration() or 0
        self._safe_print(f"[{idx}/{total}] {status_label} [{task.task_id}] {task.problem_title} ({duration:.1f}s)")
        self._safe_print(f"      文件: {task.file_path}")

        if task.status == TaskStatus.SUCCESS:
            if task.output_path:
                self._safe_print(f"      输出: {task.output_path}")
        else:
            error_msg = task.error_message or "Unknown error"
            self._safe_print(f"      错误: {error_msg}")

        if self.show_logs:
            self._print_task_log(task)
        elif task.status == TaskStatus.FAILED and self.log_lines > 0:
            self._print_task_log(task, tail_lines=self.log_lines)

    def _print_task_log(self, task: TaskItem, tail_lines: int = 0):
        """打印单个任务的分组日志。"""
        log_text = task.execution_log.strip()
        if not log_text:
            return

        lines = log_text.splitlines()
        if tail_lines > 0 and len(lines) > tail_lines:
            hidden = len(lines) - tail_lines
            lines = [f"... 已省略前 {hidden} 行日志，可使用 --show-logs 查看完整日志"] + lines[-tail_lines:]

        print(f"      日志 [{task.task_id}]:")
        for line in lines:
            self._safe_print(f"        {line}")

    @classmethod
    def _merge_logs(cls, logs: List[str]) -> str:
        merged = "\n".join(log.strip() for log in logs if log.strip()).strip()
        if len(merged) <= cls.MAX_TASK_LOG_CHARS:
            return merged

        omitted = len(merged) - cls.MAX_TASK_LOG_CHARS
        return (
            f"... 已截断前 {omitted} 个字符的日志，保留最后 "
            f"{cls.MAX_TASK_LOG_CHARS} 个字符\n"
            + merged[-cls.MAX_TASK_LOG_CHARS:]
        )

    @staticmethod
    def _format_attempt_log(attempt: int, content: str) -> str:
        content = content.strip()
        if not content:
            return f"--- Attempt {attempt} ---\n(无输出)"
        return f"--- Attempt {attempt} ---\n{content}"

    @staticmethod
    def _safe_print(text: str):
        """在 Windows 非 UTF-8 终端下尽量避免日志内容触发编码错误。"""
        try:
            print(text)
        except UnicodeEncodeError:
            encoding = sys.stdout.encoding or "utf-8"
            safe_text = text.encode(encoding, errors="replace").decode(encoding)
            print(safe_text)

    @staticmethod
    @contextmanager
    def _capture_task_output(buffer: StringIO):
        """捕获子进程 stdout/stderr 和 logging 输出，回到父进程后按任务打印。"""
        handlers = []
        loggers = [logging.getLogger()]

        for item in logging.Logger.manager.loggerDict.values():
            if isinstance(item, logging.Logger):
                loggers.append(item)

        seen = set()
        for logger_obj in loggers:
            for handler in logger_obj.handlers:
                handler_id = id(handler)
                if handler_id in seen or not hasattr(handler, "stream"):
                    continue

                seen.add(handler_id)
                old_stream = handler.stream
                handlers.append((handler, old_stream))
                try:
                    handler.setStream(buffer)
                except Exception:
                    handler.stream = buffer

        try:
            with redirect_stdout(buffer), redirect_stderr(buffer):
                yield
        finally:
            for handler, old_stream in handlers:
                try:
                    handler.setStream(old_stream)
                except Exception:
                    handler.stream = old_stream
    
    def get_summary(self) -> Dict[str, Any]:
        """
        获取执行摘要
        
        Returns:
            包含统计信息的字典
        """
        total = len(self.results)
        success = sum(1 for t in self.results if t.status == TaskStatus.SUCCESS)
        failed = sum(1 for t in self.results if t.status == TaskStatus.FAILED)
        pending = sum(1 for t in self.results if t.status == TaskStatus.PENDING)
        running = sum(1 for t in self.results if t.status == TaskStatus.RUNNING)
        
        # 计算平均耗时
        durations = [t.duration() for t in self.results if t.duration() is not None]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        return {
            "total": total,
            "success": success,
            "failed": failed,
            "pending": pending,
            "running": running,
            "success_rate": f"{success/total*100:.1f}%" if total > 0 else "0%",
            "avg_duration": f"{avg_duration:.2f}s",
            "tasks": self.results
        }
    
    def print_detailed_report(self):
        """打印详细报告"""
        summary = self.get_summary()
        
        print(f"\n{'='*80}")
        print(f"详细报告")
        print(f"{'='*80}")
        print(f"\n总体统计:")
        print(f"  总任务数: {summary['total']}")
        print(f"  成功: {summary['success']}")
        print(f"  失败: {summary['failed']}")
        print(f"  成功率: {summary['success_rate']}")
        print(f"  平均耗时: {summary['avg_duration']}")
        
        # 显示成功任务
        success_tasks = [t for t in self.results if t.status == TaskStatus.SUCCESS]
        if success_tasks:
            print(f"\n成功任务 ({len(success_tasks)}):")
            for task in success_tasks:
                duration = task.duration() or 0
                print(f"  [OK] [{task.task_id}] {task.problem_title}")
                print(f"    文件: {task.file_path}")
                if task.output_path:
                    print(f"    输出: {task.output_path}")
                print(f"    耗时: {duration:.2f}秒")
        
        # 显示失败任务
        failed_tasks = [t for t in self.results if t.status == TaskStatus.FAILED]
        if failed_tasks:
            print(f"\n失败任务 ({len(failed_tasks)}):")
            for task in failed_tasks:
                duration = task.duration() or 0
                print(f"  [FAIL] [{task.task_id}] {task.problem_title}")
                print(f"    文件: {task.file_path}")
                print(f"    错误: {task.error_message}")
                print(f"    耗时: {duration:.2f}秒")
        
        print(f"\n{'='*80}\n")

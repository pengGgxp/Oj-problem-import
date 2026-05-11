"""
Task Scheduler - 任务调度器

管理多任务并行执行，提供失败隔离和重试机制。
"""
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List, Dict, Any
from .task_models import TaskItem, TaskStatus
from .task_worker import TaskWorker
import time
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TaskScheduler:
    """任务调度器 - 管理多任务并行执行"""
    
    def __init__(self, max_workers: int = 4, max_retries: int = 2):
        """
        初始化调度器
        
        Args:
            max_workers: 最大并行工作进程数
            max_retries: 单个任务最大重试次数
        """
        self.max_workers = max_workers
        self.max_retries = max_retries
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
        logger.info(f"Starting batch execution: {total} tasks, {self.max_workers} workers")
        
        print(f"\n{'='*80}")
        print(f"批量任务执行")
        print(f"{'='*80}")
        print(f"总任务数: {total}")
        print(f"并行进程: {self.max_workers}")
        print(f"最大重试: {self.max_retries}")
        print(f"{'='*80}\n")
        
        completed_tasks = []
        success_count = 0
        failed_count = 0
        
        # 使用进程池并行执行
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_task = {}
            for task in tasks:
                future = executor.submit(
                    self._execute_with_retry, 
                    task, 
                    self.max_retries
                )
                future_to_task[future] = task
            
            # 收集结果
            for idx, future in enumerate(as_completed(future_to_task), 1):
                task = future_to_task[future]
                try:
                    completed_task = future.result()
                    completed_tasks.append(completed_task)
                    
                    if completed_task.status == TaskStatus.SUCCESS:
                        success_count += 1
                        status_icon = "✓"
                    else:
                        failed_count += 1
                        status_icon = "✗"
                    
                    # 显示进度
                    duration = completed_task.duration() or 0
                    print(f"[{idx}/{total}] {status_icon} {completed_task.problem_title} "
                          f"({duration:.1f}s)")
                    
                    if completed_task.status == TaskStatus.FAILED:
                        error_msg = completed_task.error_message or "Unknown error"
                        print(f"      错误: {error_msg[:100]}")
                    
                except Exception as e:
                    logger.error(f"Task {task.task_id} failed with exception: {e}")
                    task.status = TaskStatus.FAILED
                    task.error_message = str(e)
                    completed_tasks.append(task)
                    failed_count += 1
                    
                    print(f"[{idx}/{total}] ✗ {task.problem_title} - 异常: {str(e)[:100]}")
        
        # 排序：成功的在前，失败的在后
        completed_tasks.sort(key=lambda t: (t.status != TaskStatus.SUCCESS, t.start_time or 0))
        
        self.results = completed_tasks
        
        # 打印总结
        print(f"\n{'='*80}")
        print(f"执行完成")
        print(f"{'='*80}")
        print(f"成功: {success_count} ✓")
        print(f"失败: {failed_count} ✗")
        print(f"总计: {total}")
        if total > 0:
            print(f"成功率: {success_count/total*100:.1f}%")
        print(f"{'='*80}\n")
        
        return completed_tasks
    
    def _execute_with_retry(self, task: TaskItem, max_retries: int) -> TaskItem:
        """
        带重试机制的任务执行（在独立进程中运行）
        
        Args:
            task: 任务项
            max_retries: 最大重试次数
            
        Returns:
            完成的任务项
        """
        worker = TaskWorker()
        last_error = None
        
        for attempt in range(1, max_retries + 1):
            try:
                if attempt > 1:
                    logger.info(f"Retrying task {task.task_id}, attempt {attempt}/{max_retries}")
                
                result = worker.execute_task(task)
                
                if result.status == TaskStatus.SUCCESS:
                    return result
                
                last_error = result.error_message
                
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Attempt {attempt} failed for task {task.task_id}: {e}")
                
                # 更新任务状态
                task.status = TaskStatus.FAILED
                task.error_message = str(e)
        
        # 所有重试都失败
        task.status = TaskStatus.FAILED
        task.error_message = f"All {max_retries} attempts failed. Last error: {last_error}"
        return task
    
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
                print(f"  ✓ {task.problem_title}")
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
                print(f"  ✗ {task.problem_title}")
                print(f"    文件: {task.file_path}")
                print(f"    错误: {task.error_message}")
                print(f"    耗时: {duration:.2f}秒")
        
        print(f"\n{'='*80}\n")

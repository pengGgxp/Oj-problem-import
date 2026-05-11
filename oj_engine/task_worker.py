"""
Task Worker - 任务工作器

负责执行单个题目生成任务，封装 ProblemGenerationAgent 的调用逻辑。
"""
from pathlib import Path
from typing import Dict, Any, Optional
from .agent import ProblemGenerationAgent
from .task_models import TaskItem, TaskStatus
import time


class TaskWorker:
    """执行单个题目生成任务"""
    
    def __init__(self, max_iterations: int = 20):
        """
        初始化任务工作器
        
        Args:
            max_iterations: Agent 最大迭代次数
        """
        self.max_iterations = max_iterations
    
    def execute_task(self, task: TaskItem) -> TaskItem:
        """
        执行单个任务
        
        Args:
            task: 任务项
            
        Returns:
            更新后的任务项（包含执行结果）
        """
        task.status = TaskStatus.RUNNING
        task.start_time = time.time()
        
        try:
            # 读取题目描述
            with open(task.file_path, 'r', encoding='utf-8') as f:
                problem_description = f.read()
            
            if not problem_description or not problem_description.strip():
                raise ValueError("题目描述为空")
            
            # 提取题目名称（从文件名或内容）
            problem_title = self._extract_title(task.file_path, problem_description)
            task.problem_title = problem_title
            
            print(f"\n[Worker] 开始处理: {problem_title}")
            print(f"  文件: {task.file_path}")
            if task.base_path:
                print(f"  基础路径: {task.base_path}")
            else:
                print(f"  基础路径: (无，将平铺输出)")
            
            # 执行 Agent
            with ProblemGenerationAgent(max_iterations=self.max_iterations) as agent:
                result = agent.generate_problem(problem_description, base_path=task.base_path)
            
            # 获取输出路径（从 save_outputs_to_host 的结果中）
            output_path = self._get_output_path(result)
            task.output_path = output_path
            task.status = TaskStatus.SUCCESS
            
            print(f"[Worker] ✓ 完成: {problem_title}")
            if output_path:
                print(f"  输出: {output_path}")
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            print(f"[Worker] ✗ 失败: {task.problem_title} - {str(e)[:100]}")
        
        finally:
            task.end_time = time.time()
            duration = task.duration()
            if duration:
                print(f"  耗时: {duration:.2f}秒")
        
        return task
    
    def _extract_title(self, file_path: Path, description: str) -> str:
        """
        从文件或内容中提取题目标题
        
        Args:
            file_path: 文件路径
            description: 题目描述
            
        Returns:
            题目标题字符串
        """
        # 优先使用文件名（去掉扩展名）
        title = file_path.stem
        
        # 如果文件名不够清晰，尝试从内容第一行提取
        if len(title) < 3:
            lines = description.split('\n')
            for line in lines[:5]:  # 检查前5行
                line = line.strip()
                if line and len(line) > 3:
                    # 取第一个有意义的行作为标题
                    title = line[:50]
                    break
        
        # 清理标题中的非法字符
        title = self._sanitize_title(title)
        
        return title
    
    def _sanitize_title(self, title: str) -> str:
        """
        清理标题，移除非法字符
        
        Args:
            title: 原始标题
            
        Returns:
            清理后的标题
        """
        # 移除非法字符
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            title = title.replace(char, '_')
        
        # 限制长度
        if len(title) > 50:
            title = title[:50]
        
        return title.strip()
    
    def _get_output_path(self, result: Dict) -> Optional[Path]:
        """
        从 Agent 结果中提取输出路径
        
        Args:
            result: Agent 执行结果
            
        Returns:
            输出路径，如果未找到则返回 None
        """
        try:
            # 从最后的 assistant 消息中提取输出路径
            if "messages" in result:
                messages = result["messages"]
                # 查找最后一条包含 output_path 的消息
                for msg in reversed(messages):
                    if hasattr(msg, 'content') and isinstance(msg.content, str):
                        # 尝试从 JSON 中提取
                        if "output_path" in msg.content:
                            import json
                            # 查找 JSON 片段
                            start = msg.content.find('{')
                            if start != -1:
                                try:
                                    json_str = msg.content[start:]
                                    data = json.loads(json_str)
                                    if "output_path" in data:
                                        return Path(data["output_path"])
                                except:
                                    pass
                
                # 尝试从 tool 调用结果中提取
                for msg in reversed(messages):
                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        for tool_call in msg.tool_calls:
                            if tool_call.get('name') == 'save_outputs_to_host':
                                args = tool_call.get('args', {})
                                if isinstance(args, dict) and 'output_path' in args:
                                    return Path(args['output_path'])
            
            return None
            
        except Exception as e:
            print(f"[Worker] 警告: 无法提取输出路径 - {e}")
            return None

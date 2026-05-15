"""
状态定义模块 - 定义 LangGraph 工作流的数据结构
"""
from typing import TypedDict, List, Optional, Literal
from pydantic import BaseModel, Field


class ProblemRequirements(BaseModel):
    """题目需求解析结果"""
    time_limit: float = Field(default=1.0, description="时间限制(秒)")
    memory_limit: int = Field(default=256, description="内存限制(MB)")
    input_format: str = Field(default="", description="输入格式描述")
    output_format: str = Field(default="", description="输出格式描述")
    variable_ranges: dict = Field(default_factory=dict, description="变量范围约束")
    constraints: List[str] = Field(default_factory=list, description="约束条件列表")


class CodeArtifact(BaseModel):
    """代码产物"""
    solution_code: str = Field(default="", description="标答代码")
    solution_language: str = Field(default="python", description="标答语言")
    generator_code: str = Field(default="", description="数据生成器代码")
    checker_code: Optional[str] = Field(default=None, description="特殊判题器代码(SPJ)")


class ExecutionResult(BaseModel):
    """沙箱执行结果"""
    status: Literal["success", "fail", "timeout", "error"] = Field(default="success")
    exit_code: int = Field(default=0)
    stdout: str = Field(default="")
    stderr: str = Field(default="")
    error_type: Optional[str] = Field(default=None, description="错误类型")


class GraphState(TypedDict):
    """
    LangGraph 工作流状态
    
    包含整个题目生成流程中的所有状态信息
    """
    # 原始输入
    problem_description: str
    
    # 解析后的需求
    requirements: Optional[ProblemRequirements]
    
    # 生成的代码
    codes: Optional[CodeArtifact]
    
    # 执行结果
    execution_result: Optional[ExecutionResult]
    
    # 测试数据
    test_cases: List[dict]  # [{"input": "...", "output": "..."}]
    
    # 控制流
    retry_count: int  # 重试次数
    max_retries: int  # 最大重试次数
    current_step: str  # 当前执行的步骤
    
    # 错误历史(用于反思)
    error_history: List[dict]  # [{"attempt": 1, "error": "...", "code": "..."}]
    
    # 最终状态
    status: Literal["parsing", "generating", "executing", "reflecting", 
                    "completed", "failed"]

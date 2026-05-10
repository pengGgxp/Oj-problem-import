"""
LangGraph 工作流编排 - 整合所有节点
"""
from langgraph.graph import StateGraph, END
from .state import GraphState
from .nodes.parser import parse_problem_node
from .nodes.generator import generate_code_node
from .nodes.executor import execute_code_node
from .nodes.reflector import should_retry
from .services.output_manager import OutputManager


def create_workflow(max_retries: int = 3, auto_save: bool = True) -> StateGraph:
    """
    创建 OJ 题目生成工作流
    
    工作流结构:
    START -> Parser -> Generator -> Executor -> Reflector -> (Generator | END)
    
    Args:
        max_retries: 最大重试次数
        auto_save: 是否自动保存产物
        
    Returns:
        编译后的 LangGraph 工作流
    """
    
    # 初始化状态图
    workflow = StateGraph(GraphState)
    
    # 添加节点
    workflow.add_node("parser", parse_problem_node)
    workflow.add_node("generator", generate_code_node)
    workflow.add_node("executor", execute_code_node)
    
    # 如果启用自动保存,添加保存节点
    if auto_save:
        output_manager = OutputManager()
        
        def save_output_node(state: GraphState) -> GraphState:
            """保存产物节点"""
            try:
                # 从题目描述中提取标题(第一行)
                problem_title = state["problem_description"].strip().split('\n')[0][:50]
                output_manager.save_result(state, problem_title)
            except Exception as e:
                print(f"[Warning] 保存产物失败: {e}")
            return state
        
        workflow.add_node("save_output", save_output_node)
    
    # 设置入口点
    workflow.set_entry_point("parser")
    
    # 添加边
    workflow.add_edge("parser", "generator")
    workflow.add_edge("generator", "executor")
    
    # 添加条件边(Reflector 决定是重试还是结束)
    if auto_save:
        # 如果需要保存,先保存到 save_output,然后结束
        workflow.add_conditional_edges(
            "executor",
            should_retry,
            {
                "generator": "generator",  # 重试
                "end": "save_output"  # 结束后保存
            }
        )
        workflow.add_edge("save_output", END)
    else:
        workflow.add_conditional_edges(
            "executor",
            should_retry,
            {
                "generator": "generator",  # 重试
                "end": END  # 直接结束
            }
        )
    
    # 编译工作流
    app = workflow.compile()
    
    print("[Workflow] LangGraph 工作流已创建并编译完成")
    print(f"  - 最大重试次数: {max_retries}")
    print(f"  - 节点列表: parser -> generator -> executor -> reflector")
    
    return app


def initialize_state(problem_description: str, max_retries: int = 3) -> GraphState:
    """
    初始化工作流状态
    
    Args:
        problem_description: 题目描述文本
        max_retries: 最大重试次数
        
    Returns:
        初始化的状态对象
    """
    return GraphState(
        problem_description=problem_description,
        requirements=None,
        codes=None,
        execution_result=None,
        test_cases=[],
        retry_count=0,
        max_retries=max_retries,
        current_step="parsing",
        error_history=[],
        status="parsing"
    )

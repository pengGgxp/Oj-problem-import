"""
Reflector 节点 - 反思与路由决策
"""
from ..state import GraphState


def reflect_and_route(state: GraphState) -> dict:
    """
    反思执行结果并决定下一步
    
    逻辑:
    - 如果执行成功且重试次数 < 最大重试次数: 可以选择继续优化或结束
    - 如果执行失败且重试次数 < 最大重试次数: 回流到 Generator 重新生成
    - 如果达到最大重试次数: 结束(标记为失败)
    
    Args:
        state: 当前工作流状态
        
    Returns:
        下一个节点的名称 ("generator" 或 "end")
    """
    print("[Reflector] 开始反思执行结果...")
    
    execution_result = state.get("execution_result")
    retry_count = state["retry_count"]
    max_retries = state["max_retries"]
    
    # 如果没有执行结果,说明之前步骤失败
    if not execution_result:
        print(f"[Reflector] 无执行结果,流程失败")
        state["status"] = "failed"
        return "end"
    
    # 记录错误历史
    if execution_result.status != "success":
        error_record = {
            "attempt": retry_count + 1,
            "error_type": execution_result.error_type,
            "error": execution_result.stderr,
            "exit_code": execution_result.exit_code
        }
        
        if "error_history" not in state:
            state["error_history"] = []
        
        state["error_history"].append(error_record)
        
        print(f"[Reflector] 执行失败,记录错误:")
        print(f"  - 尝试次数: {retry_count + 1}")
        print(f"  - 错误类型: {execution_result.error_type}")
        print(f"  - 错误信息: {execution_result.stderr[:100]}")
    
    # 判断是否成功
    if execution_result.status == "success":
        print(f"[Reflector] ✓ 执行成功!")
        state["status"] = "completed"
        return "end"
    
    # 执行失败,检查是否可以重试
    if retry_count < max_retries:
        print(f"[Reflector] ⚠ 执行失败,准备第 {retry_count + 2} 次重试...")
        state["retry_count"] = retry_count + 1
        state["current_step"] = "generating"
        state["status"] = "generating"
        return "generator"
    else:
        print(f"[Reflector] ✗ 已达到最大重试次数 ({max_retries}),流程失败")
        state["status"] = "failed"
        return "end"


def should_retry(state: GraphState) -> str:
    """
    条件边函数:决定是否重试
    
    LangGraph 的条件边需要返回下一个节点的名称
    
    Args:
        state: 当前工作流状态
        
    Returns:
        "generator" (重试) 或 "end" (结束)
    """
    return reflect_and_route(state)

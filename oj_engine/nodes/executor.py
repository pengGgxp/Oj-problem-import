"""
Executor 节点 - 沙箱验证执行
"""
from ..state import GraphState, ExecutionResult
from ..sandbox import SandboxExecutor


def execute_code_node(state: GraphState) -> GraphState:
    """
    在 Docker 沙箱中执行生成的代码
    
    执行流程:
    1. 运行数据生成器产生测试输入
    2. 运行标答代码处理输入产生输出
    3. 记录执行结果和资源使用情况
    
    Args:
        state: 当前工作流状态
        
    Returns:
        更新后的状态(包含执行结果)
    """
    print("[Executor] 开始在沙箱中执行代码...")
    
    codes = state["codes"]
    requirements = state["requirements"]
    
    # 初始化沙箱执行器
    executor = SandboxExecutor(
        mem_limit=f"{requirements.memory_limit}m",
        cpu_quota=int(requirements.time_limit * 100000)  # 转换为微秒
    )
    
    # 准备要执行的文件
    files = {
        "generator.py": codes.generator_code,
    }
    
    # 根据语言添加标答文件
    if codes.solution_language == "python":
        files["solution.py"] = codes.solution_code
        solution_cmd = "python3 solution.py < input.txt > output.txt"
    elif codes.solution_language == "cpp":
        files["solution.cpp"] = codes.solution_code
        solution_cmd = "g++ -O2 -o solution solution.cpp && ./solution < input.txt > output.txt"
    else:
        raise ValueError(f"不支持的语言: {codes.solution_language}")
    
    # 如果有 SPJ,也添加
    if codes.checker_code:
        files["checker.cpp"] = codes.checker_code
    
    # 构建执行命令序列
    commands = [
        "python3 generator.py > input.txt",  # 生成测试数据
        solution_cmd,  # 运行标答
    ]
    
    try:
        # 执行代码
        result = executor.execute(
            files=files,
            commands=commands,
            timeout=int(requirements.time_limit * 2)  # 超时时间为限制的2倍
        )
        
        print(f"[Executor] 执行完成:")
        print(f"  - 状态: {result.status}")
        print(f"  - 退出码: {result.exit_code}")
        print(f"  - 内存使用: {result.memory_usage:.2f}MB")
        
        if result.stderr:
            print(f"  - 错误信息: {result.stderr[:200]}")
        
        # 如果执行成功,尝试提取测试用例
        test_cases = []
        if result.status == "success":
            # 这里可以进一步解析 stdout/stderr 来提取测试用例
            # 简化版:假设生成器和标答都正常工作
            test_cases.append({
                "input": "generated",  # 实际应该从容器中提取
                "output": "generated",
                "status": "passed"
            })
        
        # 更新状态
        state["execution_result"] = result
        state["test_cases"] = test_cases
        state["current_step"] = "reflecting"
        state["status"] = "reflecting"
        
    except Exception as e:
        print(f"[Executor] 执行过程出错: {str(e)}")
        
        state["execution_result"] = ExecutionResult(
            status="error",
            exit_code=-1,
            stderr=str(e),
            error_type="execution_exception"
        )
        state["current_step"] = "reflecting"
        state["status"] = "reflecting"
    
    return state

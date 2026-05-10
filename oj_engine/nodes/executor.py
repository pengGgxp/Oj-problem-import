"""
Executor 节点 - 沙箱验证执行
"""
from ..state import GraphState, ExecutionResult
from ..sandbox import SandboxExecutor
from ..config import settings
import json


def execute_code_node(state: GraphState) -> GraphState:
    """
    在 Docker 沙箱中执行代码,生成 .in/.out 文件
    
    执行流程:
    1. 读取 AI 生成的测试输入
    2. 对每组数据运行标答产生输出
    3. 保存成对的 .in/.out 文件到 state
    4. 记录执行结果和资源使用情况
    
    Args:
        state: 当前工作流状态
        
    Returns:
        更新后的状态(包含执行结果和测试数据)
    """
    print("[Executor] 开始执行代码生成输出...")
    
    codes = state.get("codes")
    test_cases = state.get("test_cases", [])
    
    # 检查代码是否生成成功
    if not codes:
        print("[Executor] Code not generated, skip execution")
        state["execution_result"] = ExecutionResult(
            status="error",
            exit_code=-1,
            stderr="Code generation failed",
            error_type="code_generation_failed"
        )
        state["current_step"] = "reflecting"
        state["status"] = "failed"
        return state
    
    # 如果没有测试数据,跳过
    if not test_cases:
        print("[Executor] No test cases to execute")
        state["execution_result"] = ExecutionResult(
            status="success",
            exit_code=0,
            stdout="No test cases",
            stderr=""
        )
        state["current_step"] = "reflecting"
        state["status"] = "reflecting"
        return state
    
    requirements = state.get("requirements")
    if not requirements:
        from ..state import ProblemRequirements
        requirements = ProblemRequirements()
    
    # 初始化沙箱执行器
    executor = SandboxExecutor(
        mem_limit=f"{requirements.memory_limit}m",
        cpu_quota=int(requirements.time_limit * 100000)
    )
    
    # 准备要执行的文件
    files = {}
    
    # 根据语言添加标答文件
    if codes.solution_language == "python":
        files["solution.py"] = codes.solution_code
        solution_cmd = "python3 solution.py"
    elif codes.solution_language == "cpp":
        files["solution.cpp"] = codes.solution_code
        solution_cmd = "g++ -O2 -o solution solution.cpp && ./solution"
    else:
        raise ValueError(f"Unsupported language: {codes.solution_language}")
    
    # 如果有 SPJ,也添加
    if codes.checker_code:
        files["checker.cpp"] = codes.checker_code
    
    print(f"[Executor] Executing {len(test_cases)} test cases...")
    
    try:
        executed_tests = []
        last_result = None
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"[Executor] Executing test case {i}/{len(test_cases)}...")
            
            test_input = test_case.get('input', '')
            
            # 构建命令序列
            commands = [
                f"echo '{test_input}' > input.txt",  # 写入输入
                f"{solution_cmd} < input.txt > output.txt",  # 运行标答
                f"cat output.txt",  # 读取输出
            ]
            
            # 执行
            result = executor.execute(
                files=files,
                commands=commands,
                timeout=int(requirements.time_limit * 2)
            )
            
            last_result = result
            
            if result.status != "success":
                print(f"  ⚠ Test case {i} execution failed: {result.error_type}")
                test_case["status"] = "failed"
                test_case["error"] = result.stderr
            else:
                # 解析输出
                test_output = result.stdout.strip()
                test_case["output"] = test_output
                test_case["status"] = "passed"
                test_case["execution_time"] = result.execution_time
                test_case["memory_usage"] = result.memory_usage
                print(f"  ✓ Test case {i} passed")
            
            executed_tests.append(test_case)
        
        print(f"[Executor] Execution complete: {len([t for t in executed_tests if t['status'] == 'passed'])}/{len(executed_tests)} passed")
        
        # 更新状态
        state["execution_result"] = last_result
        state["test_cases"] = executed_tests
        state["current_step"] = "reflecting"
        state["status"] = "reflecting"
        
    except Exception as e:
        print(f"[Executor] Execution error: {str(e)}")
        
        state["execution_result"] = ExecutionResult(
            status="error",
            exit_code=-1,
            stderr=str(e),
            error_type="execution_exception"
        )
        state["current_step"] = "reflecting"
        state["status"] = "reflecting"
    
    return state

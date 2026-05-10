"""
使用示例 - 演示如何运行 OJ 题目生成工作流
"""
import asyncio
from oj_engine import create_workflow, initialize_state


async def run_example():
    """运行一个简单的示例"""
    
    # 示例题目描述
    problem_description = """
    A + B Problem
    
    给定两个整数 A 和 B,计算它们的和。
    
    输入格式:
    一行,包含两个整数 A 和 B,用空格分隔。
    
    输出格式:
    一行,包含 A + B 的结果。
    
    数据范围:
    -1000 <= A, B <= 1000
    
    样例输入:
    3 5
    
    样例输出:
    8
    """
    
    print("=" * 60)
    print("OJ Engine - AI OJ Content Engine")
    print("=" * 60)
    print(f"\n题目描述:\n{problem_description}\n")
    
    # 创建工作流
    app = create_workflow(max_retries=3)
    
    # 初始化状态
    initial_state = initialize_state(
        problem_description=problem_description,
        max_retries=3
    )
    
    print("\n开始执行工作流...\n")
    
    try:
        # 执行工作流
        result = await app.ainvoke(initial_state)
        
        # 输出结果
        print("\n" + "=" * 60)
        print("工作流执行完成!")
        print("=" * 60)
        print(f"最终状态: {result['status']}")
        print(f"重试次数: {result['retry_count']}")
        
        if result.get('requirements'):
            print(f"\n解析的需求:")
            print(f"  - 时间限制: {result['requirements'].time_limit}s")
            print(f"  - 内存限制: {result['requirements'].memory_limit}MB")
        
        if result.get('codes'):
            print(f"\n生成的代码:")
            print(f"  - 标答语言: {result['codes'].solution_language}")
            print(f"  - 标答长度: {len(result['codes'].solution_code)} 字符")
            print(f"  - 生成器长度: {len(result['codes'].generator_code)} 字符")
        
        if result.get('execution_result'):
            print(f"\n执行结果:")
            print(f"  - 状态: {result['execution_result'].status}")
            print(f"  - 退出码: {result['execution_result'].exit_code}")
            if result['execution_result'].stderr:
                print(f"  - 错误信息: {result['execution_result'].stderr[:200]}")
        
        if result.get('error_history'):
            print(f"\n错误历史: {len(result['error_history'])} 次失败")
            for i, error in enumerate(result['error_history'], 1):
                print(f"  {i}. 尝试 #{error['attempt']}: {error['error_type']}")
        
        return result
        
    except Exception as e:
        print(f"\n❌ 工作流执行出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    # 注意: 需要设置 OPENAI_API_KEY 环境变量
    # export OPENAI_API_KEY="your-api-key"
    
    print("提示: 请确保已设置 OPENAI_API_KEY 环境变量")
    print("并且 Docker 服务正在运行\n")
    
    asyncio.run(run_example())

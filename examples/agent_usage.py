"""
Agent Usage Example - 使用 ReAct Agent 生成 OJ 题目内容

演示如何使用 ProblemGenerationAgent 自主决策并生成完整的测试数据包。
Agent 会自动调用 save_outputs_to_host 工具将产物保存到 outputs 目录。
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from oj_engine.agent import ProblemGenerationAgent


def main():
    """主函数"""
    
    # 示例题目: A + B Problem
    problem_description = """
第k小的数
题目描述
输入 N 个数字 a_i，输出这些数字的第 k 小的数。最小的数是第 0 小。

输入格式
第 1 行为两个正整数 N (1 ≤ n ≤ 5000000)，k (0 ≤ k ≤ N)。

第 2 行包含 N 个空格隔开的正整数 a_i，为你需要进行排序的数，数据保证了 a_i 不超过 10^9。

输出格式
输出一个整数。

样例
输入数据 1
5 3
2 4 1 5 3
输出数据 1
4
"""
    
    print("=" * 80)
    print("oj problem import - Agent Mode")
    print("=" * 80)
    print(f"\nProblem: A + B Problem")
    print("-" * 80)
    
    # 使用上下文管理器创建 Agent (自动管理沙箱生命周期)
    with ProblemGenerationAgent(max_iterations=20) as agent:
        try:
            # 执行问题生成
            print("\n" + "=" * 80)
            print("Starting Agent Execution...")
            print("=" * 80)
            print("\nNote: Agent will automatically save outputs using save_outputs_to_host tool")
            print("      when the task is completed.\n")
            
            result = agent.generate_problem(problem_description)
            
            # 显示 Agent 执行结果摘要
            print("\n" + "=" * 80)
            print("Agent Execution Completed")
            print("=" * 80)
            
            # 检查是否有输出
            if "output" in result:
                output_preview = result["output"][:500]
                print(f"\nAI visible reasoning and summary (first 500 chars):")
                print(output_preview)
                print("...")
            
            # 提示用户查看 outputs 目录
            outputs_dir = project_root / "outputs"
            if outputs_dir.exists():
                print(f"\n✓ Check the outputs directory for saved results:")
                print(f"  {outputs_dir.absolute()}")
                
                # 列出最新的输出
                output_dirs = sorted(outputs_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)
                if output_dirs:
                    latest = output_dirs[0]
                    print(f"\nLatest output:")
                    print(f"  {latest.name}")
                    print(f"\nFiles in latest output:")
                    for item in sorted(latest.rglob("*")):
                        if item.is_file():
                            rel_path = item.relative_to(latest)
                            print(f"    {rel_path}")
            else:
                print(f"\n⚠ No outputs directory found at: {outputs_dir}")
            
        except Exception as e:
            print(f"\n✗ Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return 1
    
    print("\n" + "=" * 80)
    print("Done!")
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

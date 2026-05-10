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
纸张尺寸
问题描述
在 ISO 国际标准中定义了 A0 纸张的大小为 1189mm × 841mm，将 A0 纸沿长边对折后为 A1 纸，大小为 841mm × 594mm，在对折的过程中长度直接取下整（实际裁剪时可能有损耗）。将 A1 纸沿长边对折后为 A2 纸，依此类推。

输入纸张的名称，请输出纸张的大小。

输入格式
输入一行包含一个字符串表示纸张的名称，该名称一定是 A0、A1、A2、A3、A4、A5、A6、A7、A8、A9 之一。

输出格式
输出两行，每行包含一个整数，依次表示长边和短边的长度。

样例输入 1
A0
样例输出 1
1189
841
样例输入 2
A1
样例输出 2
841
594
运行限制
最大运行时间：1s
最大运行内存：512M
难度
LV2

标签
2022, 模拟, 省赛
"""
    
    print("=" * 80)
    print("OJ Engine - Agent Mode")
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
                print(f"\nOutput preview (first 500 chars):")
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

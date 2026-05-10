"""
产物查看工具 - 列出和查看已保存的生成结果
"""
from pathlib import Path
from oj_engine.services.output_manager import OutputManager


def list_outputs():
    """列出所有保存的产物"""
    manager = OutputManager()
    outputs = manager.list_outputs()
    
    if not outputs:
        print("没有找到任何保存的产物")
        return
    
    print("=" * 80)
    print(f"已保存的产物 ({len(outputs)} 个):")
    print("=" * 80)
    
    for i, output in enumerate(outputs, 1):
        print(f"\n{i}. {output['title']}")
        print(f"   时间: {output['timestamp']}")
        print(f"   状态: {output['status']}")
        print(f"   路径: {output['path']}")


def show_output_detail(output_path: Path):
    """显示某个产物的详细信息"""
    manager = OutputManager()
    
    try:
        result = manager.load_result(output_path)
        
        print("\n" + "=" * 80)
        print(f"产物详情: {result['metadata'].get('problem_title', 'unnamed')}")
        print("=" * 80)
        
        # 元数据
        metadata = result['metadata']
        print(f"\n生成时间: {metadata.get('created_at', 'N/A')}")
        print(f"状态: {metadata.get('status', 'N/A')}")
        print(f"重试次数: {metadata.get('retry_count', 0)}")
        
        # 代码文件
        if result['codes']:
            print(f"\n代码文件 ({len(result['codes'])} 个):")
            for filename in result['codes'].keys():
                print(f"  - {filename}")
        
        # 测试数据
        if result['test_cases']:
            print(f"\n测试数据: {len(result['test_cases'])} 组")
        
        # 显示标答代码
        solution_files = [f for f in result['codes'].keys() if 'solution' in f]
        if solution_files:
            solution_file = solution_files[0]
            print(f"\n--- 标答代码 ({solution_file}) ---")
            print(result['codes'][solution_file][:500])  # 只显示前500字符
            if len(result['codes'][solution_file]) > 500:
                print("... (代码过长,已截断)")
        
    except Exception as e:
        print(f"加载产物失败: {e}")


def main():
    """主函数"""
    import sys
    
    if len(sys.argv) < 2:
        # 列出所有产物
        list_outputs()
        print("\n使用方法:")
        print("  python view_outputs.py list          # 列出所有产物")
        print("  python view_outputs.py show <path>   # 显示某个产物的详情")
    else:
        command = sys.argv[1]
        
        if command == "list":
            list_outputs()
        elif command == "show" and len(sys.argv) >= 3:
            output_path = Path(sys.argv[2])
            show_output_detail(output_path)
        else:
            print(f"未知命令: {command}")
            print("使用方法: python view_outputs.py list 或 python view_outputs.py show <path>")


if __name__ == "__main__":
    main()

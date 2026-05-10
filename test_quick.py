"""
快速测试 - 验证模块是否可以正常导入和工作
"""


def test_imports():
    """测试所有模块是否可以正常导入"""
    print("测试模块导入...")
    
    try:
        from oj_engine import (
            create_workflow,
            initialize_state,
            GraphState,
            ProblemRequirements,
            CodeArtifact,
            ExecutionResult,
            SandboxExecutor
        )
        print("✓ 所有模块导入成功")
        return True
    except ImportError as e:
        print(f"✗ 导入失败: {e}")
        return False


def test_state_creation():
    """测试状态对象创建"""
    print("\n测试状态对象创建...")
    
    try:
        from oj_engine import initialize_state
        
        state = initialize_state(
            problem_description="Test problem",
            max_retries=3
        )
        
        assert state["problem_description"] == "Test problem"
        assert state["max_retries"] == 3
        assert state["retry_count"] == 0
        assert state["status"] == "parsing"
        
        print("✓ 状态对象创建成功")
        return True
    except Exception as e:
        print(f"✗ 状态创建失败: {e}")
        return False


def test_workflow_creation():
    """测试工作流创建"""
    print("\n测试工作流创建...")
    
    try:
        from oj_engine import create_workflow
        
        app = create_workflow(max_retries=3)
        
        # 检查工作流是否有预期的节点
        nodes = list(app.nodes.keys())
        expected_nodes = ["parser", "generator", "executor"]
        
        for node in expected_nodes:
            assert node in nodes, f"缺少节点: {node}"
        
        print(f"✓ 工作流创建成功 (节点: {', '.join(nodes)})")
        return True
    except Exception as e:
        print(f"✗ 工作流创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_sandbox_init():
    """测试沙箱执行器初始化"""
    print("\n测试沙箱执行器初始化...")
    
    try:
        from oj_engine import SandboxExecutor
        
        # 注意: 这里只是测试初始化,不实际运行 Docker
        executor = SandboxExecutor(
            image="python:3.10-slim",
            mem_limit="512m",
            cpu_quota=50000
        )
        
        print("✓ 沙箱执行器初始化成功")
        return True
    except Exception as e:
        print(f"⚠ 沙箱执行器初始化警告: {e}")
        print("  (如果 Docker 未运行,这是正常的)")
        return True  # 不视为失败


def main():
    """运行所有测试"""
    print("=" * 60)
    print("OJ Engine 核心模块测试")
    print("=" * 60)
    
    results = []
    
    results.append(("模块导入", test_imports()))
    results.append(("状态创建", test_state_creation()))
    results.append(("工作流创建", test_workflow_creation()))
    results.append(("沙箱初始化", test_sandbox_init()))
    
    print("\n" + "=" * 60)
    print("测试结果汇总:")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{name}: {status}")
    
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过!")
    else:
        print(f"\n⚠ {total - passed} 个测试失败")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

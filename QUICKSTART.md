# OJ Engine 快速开始指南

## 前置要求

1. **Python 3.12+** - 已配置
2. **Docker Desktop** - 需要安装并运行
3. **OpenAI API Key** - 用于 LLM 调用

## 安装步骤

### 1. 安装依赖

```bash
# 在项目根目录执行
uv sync
```

### 2. 配置环境变量

#### Windows (PowerShell)
```powershell
$env:OPENAI_API_KEY="your-api-key-here"
```

#### Windows (CMD)
```cmd
set OPENAI_API_KEY=your-api-key-here
```

#### Linux/Mac
```bash
export OPENAI_API_KEY="your-api-key-here"
```

### 3. 验证安装

```bash
# 运行快速测试
uv run python test_quick.py
```

应该看到:
```
🎉 所有测试通过!
```

## 快速使用

### 方法 1: 使用示例脚本

编辑 `examples/basic_usage.py`,修改题目描述,然后运行:

```bash
uv run python examples/basic_usage.py
```

### 方法 2: 编程方式

创建一个新的 Python 文件:

```python
import asyncio
from oj_engine import create_workflow, initialize_state

async def generate_problem():
    # 你的题目描述
    problem = """
    A + B Problem
    
    给定两个整数 A 和 B,计算它们的和。
    
    输入格式:
    一行,包含两个整数 A 和 B,用空格分隔。
    
    输出格式:
    一行,包含 A + B 的结果。
    
    数据范围:
    -1000 <= A, B <= 1000
    """
    
    # 创建工作流
    app = create_workflow(max_retries=3)
    
    # 初始化状态
    state = initialize_state(
        problem_description=problem,
        max_retries=3
    )
    
    # 执行工作流
    print("开始生成...")
    result = await app.ainvoke(state)
    
    # 查看结果
    print(f"\n状态: {result['status']}")
    
    if result.get('codes'):
        print(f"\n标答代码:\n{result['codes'].solution_code}")
        print(f"\n数据生成器:\n{result['codes'].generator_code}")
    
    if result.get('execution_result'):
        print(f"\n执行结果: {result['execution_result'].status}")

if __name__ == "__main__":
    asyncio.run(generate_problem())
```

## 工作流说明

整个流程会自动执行以下步骤:

1. **Parser** - 解析题目需求
   - 提取时间/内存限制
   - 分析输入输出格式
   - 识别变量范围

2. **Generator** - 生成代码
   - 生成标答代码
   - 生成数据生成器
   - (可选)生成特殊判题器

3. **Executor** - 沙箱验证
   - 在 Docker 中运行生成器
   - 在 Docker 中运行标答
   - 监控资源使用

4. **Reflector** - 反思决策
   - 检查执行结果
   - 失败则重试(最多3次)
   - 成功则结束

## 常见问题

### Q: Docker 无法连接?

**A**: 确保 Docker Desktop 正在运行:
```bash
docker ps
```

### Q: OpenAI API 调用失败?

**A**: 检查:
1. API Key 是否正确设置
2. 网络连接是否正常
3. API 配额是否充足

### Q: 如何更改最大重试次数?

**A**: 
```python
app = create_workflow(max_retries=5)  # 改为5次
state = initialize_state(problem, max_retries=5)
```

### Q: 支持哪些编程语言?

**A**: 目前支持:
- Python (默认)
- C++ (需要 g++ 编译器)

可以在 Generator 节点中扩展其他语言。

## 下一步

- 查看 `oj_engine/README.md` 了解详细架构
- 查看 `IMPLEMENTATION_SUMMARY.md` 了解实现细节
- 根据需要添加 FastAPI 接口层
- 集成到更大的系统中

## 技术支持

如有问题,请检查:
1. 所有依赖是否正确安装 (`uv sync`)
2. Docker 是否正常运行
3. 环境变量是否正确设置
4. 查看控制台输出的错误信息

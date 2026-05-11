# oj problem import 快速开始指南

## 前置要求

1. **Python 3.12+** - 已配置
2. **Docker Desktop** - 需要安装并运行
3. **OpenAI API Key** - 用于 LLM 调用

## 配置步骤

### 1. 创建 .env 文件

复制 `.env.example` 为 `.env`:

```bash
cp .env.example .env
```

### 2. 配置环境变量

编辑 `.env` 文件,填入您的配置:

```ini
# OpenAI API Key (必填)
LLM_OPENAI_API_KEY=sk-your-api-key-here

# 或者使用标准环境变量 (也支持)
# OPENAI_API_KEY=sk-your-api-key-here

# 自定义模型 (可选)
LLM_PARSER_MODEL=gpt-4
LLM_GENERATOR_MODEL=gpt-4

# 其他配置...
```

**支持的配置项:**

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `LLM_OPENAI_API_KEY` | OpenAI API Key | - |
| `LLM_OPENAI_BASE_URL` | 自定义 API 端点 | - |
| `LLM_PARSER_MODEL` | Parser 使用的模型 | gpt-4 |
| `LLM_GENERATOR_MODEL` | Generator 使用的模型 | gpt-4 |
| `LLM_PARSER_TEMPERATURE` | Parser 温度参数 | 0.1 |
| `LLM_GENERATOR_TEMPERATURE` | Generator 温度参数 | 0.2 |
| `DOCKER_DEFAULT_IMAGE` | Docker 镜像 | python:3.10-slim |
| `DOCKER_DEFAULT_MEM_LIMIT` | 内存限制 | 512m |
| `WORKFLOW_MAX_RETRIES` | 最大重试次数 | 3 |

> **提示**: 也可以使用标准的 `OPENAI_API_KEY` 环境变量,系统会自动识别。

## 安装步骤

### 1. 安装依赖

```bash
# 在项目根目录执行
uv sync
```

### 2. 验证配置

```bash
# 运行配置测试
uv run python test_config.py
```

应该看到:
```
🎉 所有配置测试通过!
```

### 3. 运行工作流测试

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

### Q: 如何配置 API Key?

**A**: 有两种方式:

1. **使用 .env 文件 (推荐)**:
   ```ini
   # .env 文件
   LLM_OPENAI_API_KEY=sk-your-key-here
   ```

2. **使用环境变量**:
   ```bash
   export OPENAI_API_KEY=sk-your-key-here
   ```

### Q: 如何使用自定义模型或 API 端点?

**A**: 在 `.env` 文件中配置:
```ini
LLM_OPENAI_BASE_URL=https://your-custom-endpoint.com/v1
LLM_PARSER_MODEL=gpt-3.5-turbo
LLM_GENERATOR_MODEL=gpt-3.5-turbo
```

### Q: Docker 无法连接?

**A**: 确保 Docker Desktop 正在运行:
```bash
docker ps
```

如果仍然有问题,运行诊断脚本:
```bash
uv run python test_docker.py
```

常见解决方案:
1. 重启 Docker Desktop
2. 检查 Docker Daemon 是否启动
3. Windows 用户: 以管理员身份运行终端
4. 确保 `python:3.10-slim` 镜像已下载:
   ```bash
   docker pull python:3.10-slim
   ```

### Q: 沙箱执行失败?

**A**: 运行沙箱测试验证:
```bash
uv run python test_sandbox_execution.py
```

如果测试通过,说明沙箱正常工作。

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

## 产物管理

工作流执行完成后,所有生成的代码和测试数据会自动保存到 `outputs/` 目录。

### 查看已保存的产物

```bash
# 列出所有产物
uv run python view_outputs.py list

# 查看某个产物的详情
uv run python view_outputs.py show outputs/20260510_123456_A_B_Problem
```

### 产物目录结构

```
outputs/
└── 20260510_123456_A_B_Problem/
    ├── README.md              # 说明文档
    ├── metadata.json          # 元数据
    ├── codes/
    │   ├── solution.py        # 标答代码
    │   └── generator.py       # 数据生成器
    ├── test_cases.json        # 测试数据
    └── error_history.json     # 错误历史(如果有)
```

### 使用保存的产物

```python
from oj_engine import OutputManager
from pathlib import Path

# 加载之前保存的产物
manager = OutputManager()
result = manager.load_result(Path("outputs/20260510_123456_A_B_Problem"))

# 访问代码
print(result['codes']['solution.py'])

# 访问测试数据
print(result['test_cases'])
```

## 技术支持

如有问题,请检查:
1. 所有依赖是否正确安装 (`uv sync`)
2. `.env` 文件是否正确配置
3. Docker 是否正常运行
4. API Key 是否有效
5. 查看控制台输出的错误信息

**配置相关命令:**
```bash
# 测试配置
uv run python test_config.py

# 查看当前配置值
uv run python -c "from oj_engine import settings; print(settings.llm.model)"
```

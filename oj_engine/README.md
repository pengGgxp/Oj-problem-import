# oj problem import 核心模块说明

## 项目结构

```
oj_engine/
├── __init__.py              # 模块导出
├── state.py                 # 状态定义
├── sandbox.py               # Docker 沙箱执行器
├── workflow.py              # LangGraph 工作流编排
└── nodes/                   # 工作流节点
    ├── __init__.py
    ├── parser.py            # 题目解析节点
    ├── generator.py         # 代码生成节点
    ├── executor.py          # 沙箱执行节点
    └── reflector.py         # 反思路由节点
```

## 核心组件

### 1. 状态定义 (state.py)

定义了工作流中传递的所有数据结构:
- `ProblemRequirements`: 题目需求
- `CodeArtifact`: 生成的代码产物
- `ExecutionResult`: 执行结果
- `GraphState`: 完整的工作流状态

### 2. Docker 沙箱 (sandbox.py)

提供隔离的代码执行环境:
- 资源限制(CPU/内存)
- 文件挂载
- 命令序列执行
- 执行结果捕获

### 3. 工作流节点 (nodes/)

#### Parser 节点
- 解析题目描述
- 提取时间/内存限制、输入输出格式、变量范围等

#### Generator 节点
- 生成标答代码(solution)
- 生成数据生成器(generator)
- 可选生成特殊判题器(checker)
- 支持自修复(基于错误历史)

#### Executor 节点
- 在 Docker 沙箱中执行代码
- 运行生成器产生测试数据
- 运行标答处理数据
- 记录执行结果和资源使用

#### Reflector 节点
- 分析执行结果
- 决定是否重试
- 维护错误历史
- 实现自修复循环

### 4. 工作流编排 (workflow.py)

使用 LangGraph 编排整个流程:

```
START → Parser → Generator → Executor → Reflector
                                      ↓
                              (失败且可重试?)
                                      ↓
                                  Generator (重试)
                                      ↓
                              (成功或达到最大重试)
                                      ↓
                                     END
```

## 使用方法

### 基本用法

```python
import asyncio
from oj_engine import create_workflow, initialize_state

async def main():
    # 创建工作流
    app = create_workflow(max_retries=3)
    
    # 初始化状态
    initial_state = initialize_state(
        problem_description="你的题目描述...",
        max_retries=3
    )
    
    # 执行工作流
    result = await app.ainvoke(initial_state)
    
    # 检查结果
    print(f"状态: {result['status']}")
    if result.get('codes'):
        print(f"标答: {result['codes'].solution_code}")

asyncio.run(main())
```

### 环境变量配置

使用 `.env` 文件管理所有配置 (推荐):

```bash
# 复制示例文件
cp .env.example .env

# 编辑 .env 文件,填入您的配置
```

**主要配置项:**

```ini
# LLM 配置
LLM_OPENAI_API_KEY=sk-your-api-key-here
LLM_PARSER_MODEL=gpt-4
LLM_GENERATOR_MODEL=gpt-4
LLM_PARSER_TEMPERATURE=0.1
LLM_GENERATOR_TEMPERATURE=0.2

# Docker 配置
DOCKER_DEFAULT_IMAGE=python:3.10-slim
DOCKER_DEFAULT_MEM_LIMIT=512m

# 工作流配置
WORKFLOW_MAX_RETRIES=3
```

也可以使用标准环境变量:

```bash
export OPENAI_API_KEY="your-api-key"
```

### 运行示例

```bash
# 确保 Docker 正在运行
docker ps

# 运行示例
python examples/basic_usage.py
```

## 依赖说明

主要依赖包:
- `langgraph`: 工作流编排
- `langchain-openai`: LLM 集成
- `docker`: Docker SDK
- `pydantic`: 数据验证

所有依赖已在 `pyproject.toml` 中配置,使用 `uv sync` 安装。

## 注意事项

1. **Docker 权限**: 确保当前用户有 Docker 执行权限
2. **API Key**: 需要配置有效的 LLM API Key
3. **网络访问**: 需要能够访问 LLM API 服务
4. **资源限制**: Docker 容器有 CPU/内存限制,确保宿主机资源充足

## 扩展方向

根据架构方案,后续可以添加:

1. **数据强度校验**: 分析生成数据的质量
2. **SPJ 支持完善**: 完整的特殊判题器流程
3. **状态持久化**: 使用 LangGraph checkpointer
4. **FastAPI 接口**: RESTful API + SSE 实时追踪
5. **多语言支持**: C++ 编译器镜像等

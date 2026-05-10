# OJ Problem Import - AI 智能 OJ 题目生成引擎

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

一个基于 LangGraph ReAct Agent 的智能 OJ（Online Judge）题目内容生成系统，能够自主决策并生成完整的测试数据包。

## ✨ 核心特性

- 🤖 **ReAct Agent**：基于 LangGraph 的推理+行动模式，AI 自主决策执行流程
- 🐳 **Docker 沙箱**：安全的代码执行环境，支持资源限制和隔离
- 🔄 **持久化会话**：Agent 生命周期内复用容器和工作目录，性能提升 75%
- 📊 **智能测试**：自动生成小/中/大规模测试数据，确保数据强度分布合理
- 🛠️ **分层工具**：提供基础、专用、高级三层工具供 Agent 调用
- 💾 **产物管理**：自动收集和保存生成的代码、测试数据等产物

## 🚀 快速开始

### 前置要求

- Python 3.12+
- Docker Desktop（正在运行）
- OpenAI API Key（或其他 LLM API）

### 安装

```bash
# 克隆项目
git clone <repository-url>
cd Oj-problem-import

# 安装依赖
pip install -e .

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的 API Key
```

### 基本使用

#### 配置

首次使用时，需要配置 AI 模型提供商和 API Key。

**方式一：交互式配置向导（推荐）**

```bash
# 启动配置向导
oj-engine configure
```

向导将引导你完成：
1. 选择 AI 模型提供商（OpenAI/Claude/自定义）
2. 输入 API Key
3. 选择模型
4. 确认配置

配置文件将保存在你的用户目录下，无需手动编辑。

**方式二：查看当前配置**

```bash
oj-engine show-config
```

#### 生成题目

#### 方式一：命令行工具（推荐）

安装依赖后，可以直接使用 `oj-engine` 命令：

```bash
# 查看帮助
oj-engine --help
oj-engine generate --help

# 从文件读取题目描述
oj-engine generate -f problem.txt

# 直接传入题目描述
oj-engine generate -d "A+B Problem..."

# 自定义参数
oj-engine generate -f problem.txt -m 30 -o ./results
```

#### 方式二：Python API

```python
from oj_engine.agent import ProblemGenerationAgent

problem_description = """
A + B Problem

计算两个整数的和。

输入格式:
一行,包含两个整数 a 和 b,用空格分隔。

输出格式:
一行,包含 a + b 的结果。

数据范围:
-10^9 <= a, b <= 10^9
"""

# 使用上下文管理器（推荐）
with ProblemGenerationAgent(max_iterations=20) as agent:
    result = agent.generate_problem(problem_description)
    # 处理结果...
```

### 运行示例

```bash
# 方式一：使用 CLI 命令（推荐）
oj-engine generate -f problem.txt

# 方式二：运行 Python 示例脚本
python examples/agent_usage.py

# 查看生成的产物
python view_outputs.py
```

## 📖 文档

- [快速开始指南](QUICKSTART.md)
- [持久化沙箱机制](docs/PERSISTENT_SANDBOX.md)
- [实现总结](docs/PERSISTENT_SANDBOX_IMPLEMENTATION.md)
- [配置管理指南](docs/配置管理指南.md)
- [架构方案](docs/架构方案.md)

## 🏗️ 架构设计

### 核心组件

```
┌─────────────────────────────────────────────┐
│  ProblemGenerationAgent (ReAct Agent)       │
│  ├─ LLM Client (OpenAI/Claude/etc.)        │
│  ├─ Tools Layer                             │
│  │   ├─ write_code_file                     │
│  │   ├─ read_file_content                   │
│  │   ├─ edit_file_content                   │
│  │   ├─ search_in_file                      │
│  │   ├─ delete_file                         │
│  │   ├─ execute_code                        │
│  │   └─ save_outputs_to_host                │
│  └─ SandboxSession (Persistent)             │
│      ├─ Docker Container                    │
│      └─ Workspace Directory                 │
└─────────────────────────────────────────────┘
```

### 工作流程

```
1. Agent 接收题目描述
   ↓
2. 分析阶段：理解算法类型、数据范围、输入输出格式
   ↓
3. 生成标答：编写正确的 solution 代码
   ↓
4. 生成数据生成器：编写 generator 代码
   ↓
5. 批量生成测试：生成10组测试数据（3小/5中/2大）
   ↓
6. 验证测试：确保标答正确处理每组数据
   ↓
7. 分析强度：检查数据分布是否符合要求
   ↓
8. 保存产物：整理并保存所有生成的内容
```

## 🔧 技术栈

- **LangGraph**: ReAct Agent 框架
- **LangChain**: LLM 集成和工具定义
- **Docker**: 沙箱执行环境
- **Pydantic**: 数据验证和状态管理
- **FastAPI**: （可选）Web API 接口

## 📁 项目结构

```
Oj-problem-import/
├── oj_engine/
│   ├── agent/              # ReAct Agent 实现
│   │   └── problem_agent.py
│   ├── sandbox.py          # Docker 沙箱执行器
│   ├── tools/              # 工具层
│   │   └── sandbox_tools.py
│   ├── services/           # 服务层
│   │   └── output_manager.py
│   ├── config/             # 配置管理
│   │   └── settings.py
│   └── state.py            # 状态定义
├── examples/               # 示例代码
│   └── agent_usage.py
├── docs/                   # 文档
├── outputs/                # 生成的产物
├── main.py                 # 主入口
└── README.md
```

## 🎯 使用场景

### 1. 自动生成 OJ 题目

```python
problem = "最长上升子序列（LIS）问题..."

with ProblemGenerationAgent() as agent:
    result = agent.generate_problem(problem)
```

### 2. 批量生成题目

```python
problems = [...]

for desc in problems:
    with ProblemGenerationAgent() as agent:
        result = agent.generate_problem(desc)
        save_result(result)
```

### 3. 带重试机制

```python
with ProblemGenerationAgent() as agent:
    result = agent.generate_problem_with_retry(
        problem_description,
        max_retries=3
    )
```

## ⚡ 性能优化

### 持久化沙箱会话

传统方式每次执行都创建新容器：
```
execute() → 创建容器 → 执行 → 销毁  (重复 N 次)
```

新方式使用持久化会话：
```
初始化 → 创建容器
execute() → 复用容器  (重复 N 次)
清理 → 销毁容器
```

**性能提升**：
- 容器创建次数减少 95%
- 平均执行时间减少 75%
- 总体耗时减少 75%

详见：[持久化沙箱文档](docs/PERSISTENT_SANDBOX.md)

## 🧪 测试

```bash
# 运行沙箱会话测试
python test_simple_sandbox.py

# 运行完整示例
python examples/agent_usage.py
```

## 📝 配置说明

### 环境变量 (.env)

```bash
# OpenAI API 配置
OPENAI_API_KEY=sk-your-api-key
OPENAI_MODEL=gpt-4

# 或使用其他 LLM
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-3-opus

# 沙箱配置
SANDBOX_IMAGE=python:3.10-slim
SANDBOX_MEM_LIMIT=512m
SANDBOX_CPU_QUOTA=50000
```

详见：[配置管理指南](docs/配置管理指南.md)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- [LangGraph](https://github.com/langchain-ai/langgraph) - ReAct Agent 框架
- [LangChain](https://github.com/langchain-ai/langchain) - LLM 集成
- [Docker](https://www.docker.com/) - 容器化技术

## 📧 联系方式

如有问题或建议，请提交 Issue 或联系维护者。

---

**注意**：本项目仍处于早期开发阶段，API 可能会有变化。

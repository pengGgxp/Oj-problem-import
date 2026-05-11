# 配置简化说明

## 📋 变更概述

为了简化配置管理，我们将 LLM 配置从**分离的模型配置**改为**统一的模型配置**。

## 🔄 变更内容

### 变更前（复杂配置）

```python
class LLMSettings(BaseSettings):
    parser_model: str = "gpt-4"
    generator_model: str = "gpt-4"
    parser_temperature: float = 0.1
    generator_temperature: float = 0.2
```

**使用方式：**
```python
# 需要指定 model_type
llm_parser = settings.get_llm_client(model_type="parser")
llm_generator = settings.get_llm_client(model_type="generator")
```

### 变更后（简化配置）

```python
class LLMSettings(BaseSettings):
    model: str = "gpt-4"
    temperature: float = 0.2
```

**使用方式：**
```python
# 无需指定 model_type
llm = settings.get_llm_client()
```

## ✨ 优势

1. **配置更简单**：只需设置一个模型名称和一个温度值
2. **易于维护**：不需要为不同任务维护不同的配置
3. **减少错误**：避免配置不一致导致的问题
4. **更符合实际需求**：大多数场景下使用同一个模型即可

## 📝 迁移指南

### 1. 更新 .env 文件

**旧配置：**
```bash
LLM_PARSER_MODEL=gpt-4
LLM_GENERATOR_MODEL=gpt-4
LLM_PARSER_TEMPERATURE=0.1
LLM_GENERATOR_TEMPERATURE=0.2
```

**新配置：**
```bash
LLM_MODEL=gpt-4
LLM_TEMPERATURE=0.2
```

### 2. 更新代码调用

**旧代码：**
```python
from oj_engine.config import settings

# 获取 parser 客户端
llm_parser = settings.get_llm_client(model_type="parser")

# 获取 generator 客户端
llm_generator = settings.get_llm_client(model_type="generator")
```

**新代码：**
```python
from oj_engine.config import settings

# 获取 LLM 客户端（统一）
llm = settings.get_llm_client()
```

### 3. 更新用户配置文件（config.json）

**旧配置：**
```json
{
  "llm": {
    "provider": "openai",
    "api_key": "sk-xxx",
    "model": "gpt-4"
  }
}
```

**新配置（添加 temperature）：**
```json
{
  "llm": {
    "provider": "openai",
    "api_key": "sk-xxx",
    "model": "gpt-4",
    "temperature": 0.2
  }
}
```

## 🔧 受影响的文件

### 核心代码
- ✅ `oj_engine/config/settings.py` - 配置类定义
- ✅ `oj_engine/agent/problem_agent.py` - LLM 客户端调用
- ✅ `oj_engine/config_manager.py` - 默认配置模板

### 文档
- ✅ `docs/CONFIG_MIGRATION_SUMMARY.md` - 配置迁移总结
- ✅ `docs/配置管理指南.md` - 配置管理指南
- ✅ `QUICKSTART.md` - 快速开始指南
- ✅ `docs/PROJECT_STATUS.md` - 项目状态文档

## 🧪 验证配置

运行以下命令验证配置是否正确：

```bash
# 测试配置加载
uv run python -c "from oj_engine import settings; print(f'Model: {settings.llm.model}'); print(f'Temperature: {settings.llm.temperature}')"

# 预期输出：
# Model: gpt-4
# Temperature: 0.2
```

## ⚠️ 注意事项

1. **向后兼容性**：旧的配置字段（`parser_model`, `generator_model` 等）已移除，不再支持
2. **用户配置更新**：如果用户之前通过 `oj-problem-import configure` 配置过，需要重新配置以包含 `temperature` 字段
3. **环境变量优先级**：环境变量仍然优先于配置文件

## 📅 变更日期

- **变更日期**：2026-05-11
- **版本影响**：v0.1.1+

---

**总结**：这次简化使配置更加直观和易于管理，同时保持了所有核心功能。用户只需要关注一个模型名称和一个温度参数，大大降低了配置复杂度。

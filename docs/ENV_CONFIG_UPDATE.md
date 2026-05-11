# .env 配置更新说明

## ⚠️ 重要提示

如果您之前使用过本项目，需要更新 `.env` 文件的配置格式。

## 🔄 配置格式变更

### 旧格式（已废弃）

```bash
# Parser 节点使用的模型
LLM_PARSER_MODEL=gpt-4

# Generator 节点使用的模型
LLM_GENERATOR_MODEL=gpt-4

# Parser 温度参数
LLM_PARSER_TEMPERATURE=0.1

# Generator 温度参数
LLM_GENERATOR_TEMPERATURE=0.2
```

### 新格式（当前使用）

```bash
# LLM 模型名称（统一配置）
LLM_MODEL=gpt-4

# 温度参数
LLM_TEMPERATURE=0.2
```

## 📝 更新步骤

### 1. 备份旧配置（可选）

```bash
cp .env .env.backup
```

### 2. 更新配置文件

将 `.env` 文件中的以下变量：
- `LLM_PARSER_MODEL` → `LLM_MODEL`
- `LLM_GENERATOR_MODEL` → （删除，使用统一的 `LLM_MODEL`）
- `LLM_PARSER_TEMPERATURE` → `LLM_TEMPERATURE`
- `LLM_GENERATOR_TEMPERATURE` → （删除，使用统一的 `LLM_TEMPERATURE`）

### 3. 示例：DeepSeek API 配置

```bash
# OpenAI API Key
LLM_OPENAI_API_KEY=sk-your-api-key

# DeepSeek API Base URL
LLM_OPENAI_BASE_URL=https://api.deepseek.com

# 模型名称
LLM_MODEL=deepseek-v4-flash

# 温度参数
LLM_TEMPERATURE=0.2
```

### 4. 示例：OpenAI API 配置

```bash
# OpenAI API Key
LLM_OPENAI_API_KEY=sk-your-openai-key

# 模型名称
LLM_MODEL=gpt-4

# 温度参数
LLM_TEMPERATURE=0.2
```

## ✅ 验证配置

运行以下命令验证配置是否正确：

```bash
uv run python -c "from oj_engine import settings; print(f'Model: {settings.llm.model}'); print(f'Temperature: {settings.llm.temperature}')"
```

预期输出：
```
Model: deepseek-v4-flash  # 或您配置的模型
Temperature: 0.2
```

## ❓ 常见问题

### Q1: 为什么需要更新配置？

**答**：为了简化配置管理，我们将分离的模型配置合并为统一的配置。这样更容易维护，也减少了配置错误的可能性。

### Q2: 如果不更新会怎样？

**答**：系统会使用默认值 `gpt-4`，这可能导致与您实际使用的 API 不匹配，从而出现类似以下的错误：

```
Error code: 400 - {'error': {'message': 'The supported API model names are deepseek-v4-pro or deepseek-v4-flash, but you passed gpt-4.'}}
```

### Q3: 我可以为不同任务使用不同的模型吗？

**答**：当前版本不支持。所有任务都使用同一个模型。如果您确实需要不同的模型，可以通过修改代码实现，但这不是推荐的做法。

### Q4: 用户配置文件（config.json）也需要更新吗？

**答**：是的。如果您使用 `oj-problem-import configure` 配置过，建议重新运行配置向导：

```bash
oj-problem-import configure
```

或者手动编辑配置文件，确保包含 `model` 和 `temperature` 字段：

```json
{
  "llm": {
    "provider": "openai",
    "api_key": "sk-xxx",
    "model": "deepseek-v4-flash",
    "temperature": 0.2,
    "base_url": "https://api.deepseek.com"
  }
}
```

## 📅 变更日期

- **变更日期**：2026-05-11
- **影响版本**：v0.1.1+

---

**总结**：请将您的 `.env` 文件更新为新格式，以确保配置正确加载。

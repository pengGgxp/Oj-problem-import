# AI 驱动的测试数据生成 - 架构升级总结

## 🎯 核心改进

### 之前的问题 ❌
- 仅基于输入长度判断数据大小(不准确)
- 批量生成后简单校验,无法智能调整
- Executor 节点职责过重(既生成又执行)

### 现在的方案 ✅
- **专门的 AI 节点**智能生成和分类测试数据
- **逐个验证**每组数据的质量和类型
- **动态调整**直到达到目标分布
- **职责分离**: TestDataGenerator 负责生成,Executor 负责执行

## 📐 新架构

### 工作流结构

```
START 
  ↓
Parser (解析题目需求)
  ↓
Generator (生成标答代码和数据生成器)
  ↓
TestDataGenerator (AI 智能生成测试数据) ← 新增!
  ↓
Executor (运行标答生成输出)
  ↓
Reflector (决策重试或结束)
  ↓
Save Output (保存产物)
  ↓
END
```

### 节点职责

#### 1. TestDataGenerator 节点
**文件**: [test_data_generator.py](file://e:/project/Oj-problem-import/oj_engine/nodes/test_data_generator.py)

**功能**:
- ✅ 使用 AI 分析题目要求
- ✅ 智能决定下一个需要的数据类型(small/medium/large)
- ✅ 调用 LLM 生成符合要求的测试输入
- ✅ AI 分类和验证每组数据
- ✅ 确保达到目标分布(3小/5中/2大)
- ✅ 最多尝试50次,避免无限循环

**关键函数**:
```python
def generate_test_data_node(state):
    # 主流程:迭代生成直到满足目标
    
def decide_next_test_type(generated_tests, target_config):
    # 智能决策:优先补充不足的类别
    
def generate_test_input_with_ai(llm, requirements, test_type):
    # AI 生成:根据类型生成测试输入
    
def classify_and_validate_with_ai(llm, requirements, test_input):
    # AI 分类:判断数据类型并验证有效性
```

#### 2. Executor 节点 (简化版)
**文件**: [executor.py](file://e:/project/Oj-problem-import/oj_engine/nodes/executor.py)

**功能**:
- ✅ 读取 AI 生成的测试输入
- ✅ 对每组数据运行标答产生输出
- ✅ 记录执行结果(通过/失败)
- ✅ 不再负责数据生成和分类

## 🧠 AI 智能分类

### 分类标准

AI 综合考虑以下因素判断数据类型:

**小数据 (Small)**:
- 边界值、最小值
- 特殊情况(n=1, 空输入)
- 简单案例便于调试

**中等数据 (Medium)**:
- 常规规模的随机数据
- 典型的使用场景
- 适中的复杂度

**大数据 (Large)**:
- 接近上限的值(n=10^5)
- 最坏情况、极端场景
- 性能测试用例

### Prompt 示例

```python
# 生成数据的 Prompt
"""
你是一个专业的算法竞赛测试数据生成专家。

任务:根据题目要求生成一组测试输入数据。

要求:
1. 严格遵守题目的输入格式
2. 符合变量范围约束
3. 数据应该是有效的、有意义的
4. 只输出测试数据本身,不要任何解释

需要生成的数据类型: {test_type} ({type_desc})
"""

# 分类的 Prompt
"""
你是一个算法竞赛测试数据分析专家。

任务:分析给定的测试输入数据,判断它属于哪种规模类型。

类型定义:
- small: 小数据、边界情况、特殊案例
- medium: 中等规模的常规数据
- large: 大数据、极端情况、最坏情况

请以 JSON 格式返回:
{
  "type": "small" | "medium" | "large",
  "valid": true | false,
  "reason": "为什么这样分类的简短说明",
  "description": "这组数据的特征描述"
}
"""
```

## 📊 工作流程示例

### 生成过程

```
[TestDataGenerator] Target: 10 tests (small=3, medium=5, large=2)

Attempt 1: Generating small data...
  ✓ Generated small data: n=1, single element case

Attempt 2: Generating small data...
  ✓ Generated small data: minimum values boundary

Attempt 3: Generating small data...
  ✓ Generated small data: empty input edge case

Attempt 4: Generating medium data...
  ✓ Generated medium data: random array of size 100

Attempt 5: Generating medium data...
  ⚠ Validation failed: values out of range, retry...

Attempt 6: Generating medium data...
  ✓ Generated medium data: sorted array of size 500

... (继续直到满足目标)

[TestDataGenerator] Generated 10 test cases total
  - Small: 3
  - Medium: 5
  - Large: 2
```

### 执行过程

```
[Executor] Executing 10 test cases...

[Executor] Executing test case 1/10...
  ✓ Test case 1 passed

[Executor] Executing test case 2/10...
  ✓ Test case 2 passed

...

[Executor] Execution complete: 10/10 passed
```

## 💾 产物结构

```
outputs/20260510_143022_A_B_Problem/
├── README.md              # 包含测试数据统计
├── metadata.json
├── codes/
│   ├── solution.py
│   └── generator.py
├── tests/
│   ├── 1.in              # 小数据: n=1
│   ├── 1.out
│   ├── 2.in              # 小数据: 边界值
│   ├── 2.out
│   ├── 3.in              # 小数据: 空输入
│   ├── 3.out
│   ├── 4.in              # 中等数据: n=100
│   ├── 4.out
│   ├── ...
│   └── 10.in             # 大数据: n=100000
│   └── 10.out
└── test_cases.json        # 包含 AI 分类信息
```

### test_cases.json 示例

```json
[
  {
    "id": 1,
    "input": "1\n5",
    "output": "5",
    "type": "small",
    "description": "n=1, single element case",
    "status": "passed",
    "execution_time": 0.01,
    "memory_usage": 0.5
  },
  {
    "id": 10,
    "input": "100000\n...",
    "output": "...",
    "type": "large",
    "description": "Maximum size array, worst case",
    "status": "passed",
    "execution_time": 0.85,
    "memory_usage": 45.2
  }
]
```

### README 示例

```markdown
## 测试数据统计

- **总数**: 10 组
- **小数据**: 3 组 (边界值、特殊情况)
- **中等数据**: 5 组 (常规规模)
- **大数据**: 2 组 (极端情况、最坏情况)
- **AI 尝试次数**: 12

> 注: 数据分类由 AI 智能判断,综合考虑数值大小、问题复杂度等因素。
```

## ✨ 优势对比

| 特性 | 旧方案 | 新方案 |
|------|--------|--------|
| 分类依据 | 输入长度 | AI 智能分析 |
| 准确性 | 低(误判率高) | 高(语义理解) |
| 灵活性 | 固定规则 | 动态调整 |
| 质量保证 | 事后校验 | 事前验证 |
| 可解释性 | 无 | AI 提供描述 |
| 适应性 | 差 | 好(理解题意) |

## 🔧 配置选项

可以在 `test_data_generator.py` 中调整:

```python
target_config = {
    "total": 10,      # 总数量
    "small": 3,       # 小数据数量
    "medium": 5,      # 中等数据数量
    "large": 2,       # 大数据数量
}

max_attempts = 50     # 最大尝试次数
```

## 🚀 后续扩展

可以进一步增强的功能:

- [ ] 支持自定义数据分布策略
- [ ] 添加特殊数据类型(图论、字符串等)
- [ ] SPJ 验证(多解问题)
- [ ] 性能基准测试
- [ ] 数据去重和优化
- [ ] 可视化数据分布

---

**实现时间**: 2026-05-10  
**新增文件**: 1个 (test_data_generator.py)  
**修改文件**: 3个 (workflow.py, executor.py, output_manager.py)  
**总代码行数**: ~300 行

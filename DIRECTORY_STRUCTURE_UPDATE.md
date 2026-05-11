# 目录结构保持功能 - 更新说明

## 概述

已实现批量处理时保持原始目录结构的功能。当使用目录模式批量处理题目时，输出会自动保持与输入相同的目录层级。

## 功能说明

### 修改前（平铺模式）

```
输入:
  problems/easy/p1.txt
  problems/easy/p2.txt
  problems/hard/p3.txt

输出:
  outputs/20260511_120000_p1/
  outputs/20260511_120030_p2/
  outputs/20260511_120100_p3/
```

所有输出都平铺在 `outputs/` 目录下，无法区分原始的分类。

### 修改后（保持目录结构）

```
输入:
  problems/easy/p1.txt
  problems/easy/p2.txt
  problems/hard/p3.txt

输出:
  outputs/problems/easy/20260511_120000_p1/
  outputs/problems/easy/20260511_120030_p2/
  outputs/problems/hard/20260511_120100_p3/
```

输出的目录结构与输入保持一致，便于管理和查找。

## 实现细节

### 1. save_outputs_to_host 工具增强

**文件**: `oj_engine/tools/sandbox_tools.py`

**新增参数**:
```python
def save_outputs_to_host(problem_title: str = "unnamed", base_path: str = "") -> dict:
    """
    Args:
        problem_title: 题目标题
        base_path: 基础路径（可选），用于保持目录结构
    """
```

**使用示例**:
```python
# 基本用法（平铺）
save_outputs_to_host("A+B Problem")
# 输出: outputs/20260511_120000_A_B_Problem/

# 保持目录结构
save_outputs_to_host("A+B Problem", base_path="problems/easy")
# 输出: outputs/problems/easy/20260511_120000_A_B_Problem/
```

### 2. 新增路径清理函数

**文件**: `oj_engine/tools/sandbox_tools.py`

```python
def clean_path_separators(path: str) -> str:
    """
    清理路径分隔符，统一为正斜杠
    
    示例:
    - "problems\\easy" -> "problems/easy"
    - "//problems//easy//" -> "problems/easy"
    """
```

### 3. TaskItem 模型扩展

**文件**: `oj_engine/task_models.py`

**新增字段**:
```python
@dataclass
class TaskItem:
    # ... 其他字段 ...
    base_path: str = ""  # 用于保持目录结构的基础路径
```

### 4. ProblemGenerationAgent 支持 base_path

**文件**: `oj_engine/agent/problem_agent.py`

**修改**:
- `generate_problem()` 方法新增 `base_path` 参数
- 在 prompt 中动态添加 base_path 使用说明
- Agent 会自动在调用 `save_outputs_to_host` 时使用正确的 base_path

### 5. CLI batch 命令自动计算 base_path

**文件**: `oj_engine/cli.py`

**逻辑**:
```python
for file_path in files:
    if input_path.is_file():
        # 单个文件，base_path 为空
        base_path = ""
    elif input_path.is_dir():
        # 目录模式，计算相对路径的父目录
        rel_path = file_path.relative_to(input_path)
        if rel_path.parent != Path('.'):
            base_path = str(rel_path.parent)
        else:
            base_path = ""
```

**示例**:
- 输入: `problems/easy/p1.txt` (扫描目录 `problems/`)
- 相对路径: `easy/p1.txt`
- base_path: `easy`
- 输出: `outputs/easy/20260511_p1/`

## 使用示例

### 示例 1: 简单目录结构

```bash
# 目录结构
problems/
├── easy/
│   ├── p1.txt
│   └── p2.txt
└── hard/
    └── p3.txt

# 执行批量处理
oj-problem-import batch problems/

# 输出结构
outputs/
├── easy/
│   ├── 20260511_120000_p1/
│   │   ├── solution.py
│   │   ├── generator.py
│   │   └── tests/
│   └── 20260511_120030_p2/
└── hard/
    └── 20260511_120100_p3/
```

### 示例 2: 多层级目录

```bash
# 目录结构
problems/
├── 2024/
│   ├── spring/
│   │   └── p1.txt
│   └── fall/
│       └── p2.txt
└── 2025/
    └── spring/
        └── p3.txt

# 执行批量处理
oj-problem-import batch problems/

# 输出结构
outputs/
├── 2024/
│   ├── spring/
│   │   └── 20260511_120000_p1/
│   └── fall/
│       └── 20260511_120030_p2/
└── 2025/
    └── spring/
        └── 20260511_120100_p3/
```

### 示例 3: 混合模式

```bash
# 混合使用文件和目录
oj-problem-import batch single.txt problems/easy/

# 输出结构
outputs/
├── 20260511_120000_single/          # 单文件，无 base_path
└── easy/
    └── 20260511_120030_p1/          # 目录模式，有 base_path
```

## 兼容性

### 向后兼容

- ✅ 原有的 `generate` 命令不受影响
- ✅ 如果不提供 base_path，行为与之前相同（平铺模式）
- ✅ 单文件模式自动使用平铺模式

### 跨平台支持

- ✅ Windows: 自动转换 `\` 为 `/`
- ✅ Linux/macOS: 原生支持 `/`
- ✅ 路径清理函数处理各种边界情况

## 技术要点

### 1. 路径计算逻辑

```python
# 输入: problems/easy/p1.txt (扫描目录 problems/)
rel_path = file_path.relative_to(input_path)  
# rel_path = "easy/p1.txt"

base_path = str(rel_path.parent)
# base_path = "easy"

# 最终输出路径
output_path = output_base / base_path / f"{timestamp}_{title}"
# output_path = "outputs/easy/20260511_120000_p1/"
```

### 2. Agent Prompt 动态生成

当检测到 base_path 时，会在 prompt 中添加特殊说明：

```
**重要**: 调用 save_outputs_to_host 时，请使用 base_path 参数来保持目录结构：
```python
save_outputs_to_host(problem_title="A+B Problem", base_path="problems/easy")
```
这会将输出保存到: outputs/problems/easy/{timestamp}_{title}/
```

### 3. 路径清理

```python
clean_path_separators("problems\\easy\\hard")
# -> "problems/easy/hard"

clean_path_separators("//problems//easy//")
# -> "problems/easy"
```

## 注意事项

### 1. 目录深度

- 建议目录深度不超过 3-4 层
- 过深的目录会导致输出路径过长

### 2. 路径长度限制

- Windows: 最大路径长度 260 字符
- Linux/macOS: 通常 4096 字符
- 如果路径过长，可能导致创建失败

### 3. 特殊字符

- 目录名中的特殊字符会被 `_sanitize_filename` 清理
- 建议使用英文和数字命名目录

### 4. 空目录

- 如果文件直接在扫描根目录下，base_path 为空
- 输出会平铺在 `outputs/` 下

## 故障排查

### 问题 1: 输出没有保持目录结构

**可能原因**:
- 使用了单文件模式而非目录模式
- base_path 计算错误

**解决方案**:
```bash
# 错误：单文件模式
oj-problem-import batch problems/easy/p1.txt

# 正确：目录模式
oj-problem-import batch problems/easy/
```

### 问题 2: 路径包含反斜杠（Windows）

**说明**: 
- 这是正常的，`clean_path_separators` 会自动处理
- 最终输出路径会使用正斜杠

### 问题 3: 输出路径过长

**解决方案**:
- 缩短目录名称
- 减少目录层级
- 使用更短的题目标题

## 总结

✅ **功能完整**: 支持单文件、多文件、目录三种模式
✅ **智能计算**: 自动计算 base_path，无需手动指定
✅ **跨平台**: Windows/Linux/macOS 完全兼容
✅ **向后兼容**: 不影响现有功能
✅ **易于使用**: 用户无需关心实现细节

现在你可以放心地使用目录模式批量处理题目，输出会自动保持原始的目录结构！🎉

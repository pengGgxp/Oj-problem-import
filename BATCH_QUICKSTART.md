# 多任务处理系统 - 快速开始

## 5分钟上手

### 1. 准备题目文件

创建几个题目描述文件（.txt 或 .md）：

```text
# problem1.txt
A+B Problem

计算两个整数的和。

输入格式：
一行，两个整数 a 和 b (0 <= a, b <= 1000)

输出格式：
一行，一个整数，表示 a + b 的结果

样例输入：
3 5

样例输出：
8
```

```text
# problem2.txt
求最大值

给定 n 个整数，找出其中的最大值。

输入格式：
第一行一个整数 n (1 <= n <= 100)
第二行 n 个整数

输出格式：
一行，一个整数，表示最大值

样例输入：
5
3 7 2 9 1

样例输出：
9
```

### 2. 运行批量处理

#### 方式一：处理单个文件

```bash
oj-problem-import batch problem1.txt
```

#### 方式二：处理多个文件

```bash
oj-problem-import batch problem1.txt problem2.txt
```

#### 方式三：处理整个目录

```bash
# 将所有题目文件放在一个目录中
mkdir problems
mv problem1.txt problem2.txt problems/

# 批量处理
oj-problem-import batch problems/
```

### 3. 查看结果

执行完成后，会在 `outputs/` 目录下生成对应的输出文件夹：

```
outputs/
├── 20260511_120000_A_B_Problem/
│   ├── solution.py
│   ├── generator.py
│   └── tests/
│       ├── 1.in
│       ├── 1.out
│       ├── 2.in
│       ├── 2.out
│       └── ...
├── 20260511_120030_求最大值/
│   ├── solution.py
│   ├── generator.py
│   └── tests/
│       ├── 1.in
│       ├── 1.out
│       └── ...
```

## 常用命令

### 基本用法

```bash
# 处理单个文件
oj-problem-import batch problem.txt

# 处理多个文件
oj-problem-import batch p1.txt p2.txt p3.txt

# 处理目录
oj-problem-import batch ./problems/
```

### 高级用法

```bash
# 使用 8 个并行进程
oj-problem-import batch ./problems/ -w 8

# 增加重试次数到 3
oj-problem-import batch ./problems/ -r 3

# 增加迭代次数到 30
oj-problem-import batch ./problems/ -m 30

# 组合使用
oj-problem-import batch ./problems/ -w 4 -r 2 -m 25
```

## 理解输出

### 执行过程

```
================================================================================
批量任务执行
================================================================================
总任务数: 10
并行进程: 4
最大重试: 2
================================================================================

[1/10] ✓ A+B Problem (45.2s)
[2/10] ✓ 求最大值 (38.7s)
[3/10] ✗ 最短路径 - 错误: Timeout after 2 attempts
...
```

- `[x/total]`: 当前进度
- `✓`: 任务成功
- `✗`: 任务失败
- `(45.2s)`: 任务耗时

### 执行报告

```
================================================================================
详细报告
================================================================================

总体统计:
  总任务数: 10
  成功: 8
  失败: 2
  成功率: 80.0%
  平均耗时: 42.35s

成功任务 (8):
  ✓ A+B Problem
    文件: problems/problem1.txt
    输出: outputs/20260511_120000_A_B_Problem
    耗时: 45.23秒

失败任务 (2):
  ✗ 最短路径
    文件: problems/problem3.txt
    错误: All 2 attempts failed. Last error: Timeout
    耗时: 120.45秒
```

## 常见问题

### Q1: 如何调整并行进程数？

**A**: 使用 `-w` 参数：

```bash
# 小型机器（4-8核）
oj-problem-import batch ./problems/ -w 2

# 中型机器（8-16核）
oj-problem-import batch ./problems/ -w 4

# 大型机器（16+核）
oj-problem-import batch ./problems/ -w 8
```

### Q2: 任务失败了怎么办？

**A**: 
1. 查看详细报告中的错误信息
2. 增加重试次数：`-r 3`
3. 增加迭代次数：`-m 30`
4. 减少并行进程数：`-w 2`

```bash
oj-problem-import batch ./problems/ -w 2 -r 3 -m 30
```

### Q3: 如何提高成功率？

**A**:
- 确保题目描述清晰完整
- 提供样例输入输出
- 明确数据范围
- 适当增加迭代次数和重试次数

### Q4: 执行太慢怎么办？

**A**:
- 增加并行进程数：`-w 8`
- 减少迭代次数：`-m 15`
- 分批次处理大量任务

## 下一步

- 📖 阅读完整文档：[BATCH_USAGE.md](BATCH_USAGE.md)
- 🔧 了解架构设计：[MULTITASK_IMPLEMENTATION_SUMMARY.md](MULTITASK_IMPLEMENTATION_SUMMARY.md)
- 💡 查看示例：examples/ 目录

## 提示

1. **首次使用**：建议先用少量文件测试，确认配置正确
2. **大批量处理**：分批次执行，避免资源耗尽
3. **监控进度**：观察实时输出，及时发现问题
4. **检查结果**：执行完成后检查 outputs/ 目录

祝你使用愉快！🎉

# 多任务处理系统使用指南

## 概述

OJ Engine 现在支持批量处理多个题目文件，使用多进程并行执行，并提供任务调度器防止单个任务失败影响整体执行。

## 核心功能

### 1. 文件扫描器 (FileScanner)

支持三种输入模式：
- **单个文件**: `problem.txt`
- **多个文件**: `problem1.txt,problem2.txt,problem3.txt`
- **目录**: `./problems/` (自动扫描所有 .txt/.md 文件)

### 2. 任务工作器 (TaskWorker)

封装单个题目的生成逻辑：
- 读取题目描述
- 调用 ProblemGenerationAgent 生成完整产物
- 提取输出路径
- 记录执行时间和状态

### 3. 任务调度器 (TaskScheduler)

管理多任务并行执行：
- 控制并发进程数
- 提供失败隔离（单个任务失败不影响其他任务）
- 支持重试机制
- 生成详细执行报告

## CLI 使用

### 基本用法

```bash
# 单个文件
oj-problem-import batch problem1.txt

# 多个文件
oj-problem-import batch problem1.txt problem2.txt problem3.txt

# 目录（自动扫描所有 .txt/.md 文件）
oj-problem-import batch ./problems/

# 混合模式
oj-problem-import batch problem1.txt ./problems/ problem2.txt
```

### 高级选项

```bash
# 自定义并行进程数
oj-problem-import batch ./problems/ -w 8

# 自定义重试次数
oj-problem-import batch ./problems/ -r 3

# 自定义迭代次数
oj-problem-import batch ./problems/ -m 30

# 组合使用
oj-problem-import batch ./problems/ -w 4 -r 2 -m 25
```

### 参数说明

- `-w, --max-workers`: 最大并行工作进程数（默认: 4）
- `-m, --max-iterations`: 每个任务的最大迭代次数（默认: 20）
- `-r, --max-retries`: 每个任务的最大重试次数（默认: 2）
- `-o, --output-dir`: 输出目录（默认: outputs）

## 编程接口

### 使用 FileScanner

```python
from oj_engine.file_scanner import FileScanner

# 扫描单个文件
files = FileScanner.scan_input("problem.txt")

# 扫描多个文件
files = FileScanner.scan_input("problem1.txt,problem2.txt")

# 扫描目录
files = FileScanner.scan_input("./problems/")

# 验证文件
is_valid = FileScanner.validate_file(Path("problem.txt"))
```

### 使用 TaskScheduler

```python
from oj_engine.task_scheduler import TaskScheduler
from oj_engine.task_models import TaskItem
from pathlib import Path
import uuid

# 创建任务列表
tasks = [
    TaskItem(
        task_id=str(uuid.uuid4())[:8],
        file_path=Path("problem1.txt"),
        problem_title="Problem 1"
    ),
    TaskItem(
        task_id=str(uuid.uuid4())[:8],
        file_path=Path("problem2.txt"),
        problem_title="Problem 2"
    ),
]

# 创建调度器并执行
scheduler = TaskScheduler(max_workers=4, max_retries=2)
results = scheduler.run_batch(tasks)

# 查看结果摘要
summary = scheduler.get_summary()
print(f"成功: {summary['success']}")
print(f"失败: {summary['failed']}")
print(f"成功率: {summary['success_rate']}")

# 打印详细报告
scheduler.print_detailed_report()
```

## 输出说明

### 目录结构保持（新功能）

当使用目录模式批量处理时，系统会自动保持原始的目录结构：

**输入结构**:
```
problems/
├── easy/
│   ├── p1.txt
│   └── p2.txt
└── hard/
    └── p3.txt
```

**输出结构**:
```
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

这样便于管理和查找不同类别的题目。详见 [DIRECTORY_STRUCTURE_UPDATE.md](DIRECTORY_STRUCTURE_UPDATE.md)

### 执行过程输出

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

================================================================================
执行完成
================================================================================
成功: 8 ✓
失败: 2 ✗
总计: 10
成功率: 80.0%
================================================================================
```

### 详细报告

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
  ...

失败任务 (2):
  ✗ 最短路径
    文件: problems/problem3.txt
    错误: All 2 attempts failed. Last error: Timeout
    耗时: 120.45秒
  ...

================================================================================
```

## 架构设计要点

### 1. 进程隔离

每个任务在独立的进程中执行，避免共享状态导致的污染：
- 独立的 Docker 容器
- 独立的工作目录
- 独立的 Agent 实例

### 2. 失败隔离

单个任务失败不会影响其他任务：
- 异常捕获和隔离
- 独立的重试机制
- 失败任务的错误信息记录

### 3. 资源控制

通过 `max_workers` 控制并发度：
- 避免资源耗尽
- 平衡速度和稳定性
- 建议值：CPU 核心数的 1-2 倍

### 4. 结果追踪

每个任务都有完整的状态记录：
- 任务 ID
- 文件路径
- 题目标题
- 执行状态
- 错误信息
- 输出路径
- 开始/结束时间
- 执行时长

## 最佳实践

### 1. 并行进程数设置

- **小型机器** (4-8 核): `-w 2` 或 `-w 4`
- **中型机器** (8-16 核): `-w 4` 或 `-w 8`
- **大型机器** (16+ 核): `-w 8` 或 `-w 16`

注意：每个任务都会启动一个 Docker 容器，占用较多资源。

### 2. 重试次数设置

- **稳定环境**: `-r 1` (快速失败)
- **一般环境**: `-r 2` (默认，平衡)
- **不稳定环境**: `-r 3` (更多容错)

### 3. 目录组织

推荐的目录结构：
```
problems/
├── easy/
│   ├── problem1.txt
│   ├── problem2.txt
│   └── ...
├── medium/
│   ├── problem1.txt
│   └── ...
└── hard/
    ├── problem1.txt
    └── ...
```

批量处理：
```bash
oj-problem-import batch problems/easy/ problems/medium/
```

### 4. 监控执行

查看实时进度：
- 观察 `[x/total]` 进度指示
- 关注成功/失败图标 (✓/✗)
- 检查每个任务的耗时

## 故障排查

### 问题 1: 所有任务都失败

**可能原因**:
- Docker 未启动
- API 配置错误
- 网络连接问题

**解决方案**:
```bash
# 检查 Docker
docker ps

# 检查配置
oj-problem-import show-config

# 重新配置
oj-problem-import configure
```

### 问题 2: 部分任务失败

**可能原因**:
- 题目描述不清晰
- Agent 迭代次数不足
- 资源竞争

**解决方案**:
```bash
# 增加迭代次数
oj-problem-import batch problems/ -m 30

# 减少并行进程数
oj-problem-import batch problems/ -w 2

# 增加重试次数
oj-problem-import batch problems/ -r 3
```

### 问题 3: 执行速度慢

**优化建议**:
- 增加并行进程数 (`-w`)
- 减少迭代次数 (`-m`)
- 确保 Docker 资源充足

## 注意事项

1. **Docker 资源**: 每个任务都会启动一个 Docker 容器，确保系统有足够的内存和 CPU
2. **API 限流**: 大量并发请求可能触发 API 限流，适当调整 `-w` 参数
3. **磁盘空间**: 输出文件会占用磁盘空间，定期清理 `outputs/` 目录
4. **退出码**: 如果有任务失败，程序会以退出码 1 结束，便于 CI/CD 集成

## 示例场景

### 场景 1: 批量导入题库

```bash
# 扫描整个题库目录
oj-problem-import batch /path/to/question/bank/ -w 4 -r 2
```

### 场景 2: 快速验证少量题目

```bash
# 只处理几个文件，快速迭代
oj-problem-import batch p1.txt p2.txt p3.txt -w 3 -r 1
```

### 场景 3: 大规模处理

```bash
# 分批次处理，避免资源耗尽
oj-problem-import batch batch1/ -w 2 -r 3
oj-problem-import batch batch2/ -w 2 -r 3
```

## 总结

多任务处理系统提供了：
- ✓ 灵活的文件扫描（单文件/多文件/目录）
- ✓ 高效的并行执行（多进程）
- ✓ 可靠的失败隔离（任务级）
- ✓ 智能的重试机制（可配置）
- ✓ 详细的执行报告（统计+详情）

这使得批量处理 OJ 题目变得简单、高效且可靠。

# 多任务处理系统 - 项目结构

## 新增文件

### 核心模块

```
oj_engine/
├── task_models.py          # 任务模型定义
│   ├── TaskStatus          # 任务状态枚举
│   ├── TaskItem            # 单个任务项
│   └── TaskBatch           # 任务批次
│
├── file_scanner.py         # 文件扫描器
│   ├── scan_input()        # 扫描输入路径
│   ├── validate_file()     # 验证文件
│   └── scan_multiple_inputs()  # 扫描多个路径
│
├── task_worker.py          # 任务工作器
│   ├── execute_task()      # 执行单个任务
│   ├── _extract_title()    # 提取题目标题
│   ├── _sanitize_title()   # 清理标题
│   └── _get_output_path()  # 提取输出路径
│
└── task_scheduler.py       # 任务调度器
    ├── run_batch()         # 执行任务批次
    ├── _execute_with_retry()   # 带重试的执行
    ├── get_summary()       # 获取执行摘要
    └── print_detailed_report() # 打印详细报告
```

### CLI 扩展

```
oj_engine/
└── cli.py                  # 已更新
    └── batch()             # 新增 batch 命令
```

### 模块导出

```
oj_engine/
└── __init__.py             # 已更新
    └── 导出新模块:
        - TaskItem, TaskBatch, TaskStatus
        - TaskWorker, TaskScheduler
        - FileScanner
```

## 文档文件

```
项目根目录/
├── BATCH_USAGE.md                      # 详细使用指南
├── BATCH_QUICKSTART.md                 # 快速开始指南
├── MULTITASK_IMPLEMENTATION_SUMMARY.md # 实现总结
└── PROJECT_STRUCTURE_MULTI TASK.md     # 本文件
```

## 文件说明

### 1. task_models.py (47 行)

**职责**: 定义数据结构和状态枚举

**关键类**:
- `TaskStatus`: 任务状态枚举（PENDING, RUNNING, SUCCESS, FAILED, SKIPPED）
- `TaskItem`: 单个任务的完整信息
  - 属性: task_id, file_path, problem_title, status, error_message, output_path, start_time, end_time
  - 方法: duration() - 计算执行时长
- `TaskBatch`: 任务批次管理

**依赖**: 无外部依赖

---

### 2. file_scanner.py (118 行)

**职责**: 识别和扫描题目文件

**关键方法**:
- `scan_input()`: 扫描输入路径，支持单文件、多文件（逗号分隔）、目录
- `validate_file()`: 验证文件是否为有效的题目文件
- `scan_multiple_inputs()`: 扫描多个输入路径并合并结果（去重）

**支持的文件格式**: .txt, .md, .markdown

**依赖**: pathlib

---

### 3. task_worker.py (174 行)

**职责**: 执行单个题目生成任务

**关键方法**:
- `execute_task()`: 执行单个任务的主入口
  - 读取题目描述
  - 调用 ProblemGenerationAgent
  - 提取输出路径
  - 更新任务状态
- `_extract_title()`: 从文件或内容中提取题目标题
- `_sanitize_title()`: 清理标题中的非法字符
- `_get_output_path()`: 从 Agent 结果中提取输出路径

**依赖**: 
- ProblemGenerationAgent
- TaskItem, TaskStatus

---

### 4. task_scheduler.py (228 行)

**职责**: 管理多任务并行执行

**关键方法**:
- `run_batch()`: 执行任务批次
  - 创建进程池
  - 提交所有任务
  - 收集结果
  - 显示进度
- `_execute_with_retry()`: 带重试机制的任务执行（在独立进程中运行）
- `get_summary()`: 获取执行摘要统计
- `print_detailed_report()`: 打印详细的执行报告

**特性**:
- 多进程并行执行（ProcessPoolExecutor）
- 失败隔离
- 重试机制
- 实时进度显示
- 详细报告生成

**依赖**:
- concurrent.futures.ProcessPoolExecutor
- TaskItem, TaskStatus
- TaskWorker

---

### 5. cli.py (更新)

**新增命令**: `batch`

**功能**:
- 支持多个输入参数
- 文件扫描和验证
- 任务创建和执行
- 结果展示和报告

**命令行选项**:
- `-w, --max-workers`: 并行进程数（默认: 4）
- `-m, --max-iterations`: 迭代次数（默认: 20）
- `-r, --max-retries`: 重试次数（默认: 2）
- `-o, --output-dir`: 输出目录（默认: outputs）

---

### 6. __init__.py (更新)

**新增导出**:
```python
from .task_models import TaskItem, TaskBatch, TaskStatus
from .task_worker import TaskWorker
from .task_scheduler import TaskScheduler
from .file_scanner import FileScanner
```

---

## 数据流

### 批量处理流程

```
用户输入 (CLI)
    ↓
FileScanner.scan_input()
    ↓
[文件路径列表]
    ↓
创建 TaskItem 列表
    ↓
TaskScheduler.run_batch()
    ↓
ProcessPoolExecutor
    ↓
[并行执行]
    ↓
TaskWorker.execute_task() (每个任务)
    ↓
ProblemGenerationAgent.generate_problem()
    ↓
save_outputs_to_host()
    ↓
[输出到 outputs/ 目录]
    ↓
收集结果
    ↓
打印报告
```

### 单个任务执行流程

```
TaskItem (PENDING)
    ↓
TaskWorker.execute_task()
    ↓
TaskItem (RUNNING)
    ↓
读取题目文件
    ↓
ProblemGenerationAgent
    ↓
  ├─ write_code_file (solution.py)
  ├─ write_code_file (generator.py)
  ├─ execute_code (测试)
  ├─ write_code_file (tests/*.in, tests/*.out)
  └─ save_outputs_to_host()
    ↓
TaskItem (SUCCESS/FAILED)
    ↓
返回结果
```

---

## 依赖关系图

```
cli.py
  ├─→ file_scanner.py
  ├─→ task_scheduler.py
  │     ├─→ task_worker.py
  │     │     └─→ agent/problem_agent.py
  │     └─→ task_models.py
  └─→ task_models.py

task_worker.py
  ├─→ agent/problem_agent.py
  ├─→ task_models.py
  └─→ tools/sandbox_tools.py (间接)

file_scanner.py
  └─→ pathlib (标准库)

task_scheduler.py
  ├─→ task_worker.py
  ├─→ task_models.py
  └─→ concurrent.futures (标准库)
```

---

## 代码统计

| 文件 | 行数 | 主要功能 |
|------|------|----------|
| task_models.py | 47 | 数据模型定义 |
| file_scanner.py | 118 | 文件扫描 |
| task_worker.py | 174 | 任务执行 |
| task_scheduler.py | 228 | 任务调度 |
| cli.py (更新) | +97 | CLI 命令 |
| __init__.py (更新) | +14 | 模块导出 |
| **总计** | **678** | **新增代码** |

---

## 设计原则

### 1. 单一职责
每个模块只负责一个明确的功能：
- `task_models.py`: 数据定义
- `file_scanner.py`: 文件识别
- `task_worker.py`: 任务执行
- `task_scheduler.py`: 任务调度

### 2. 松耦合
模块之间通过清晰的接口交互：
- TaskScheduler → TaskWorker → ProblemGenerationAgent
- 每层都有明确的输入输出

### 3. 高内聚
相关功能集中在同一个模块：
- 所有任务状态管理在 TaskItem
- 所有文件扫描逻辑在 FileScanner
- 所有调度逻辑在 TaskScheduler

### 4. 可扩展性
易于添加新功能：
- 添加新的任务状态：修改 TaskStatus 枚举
- 添加新的文件格式：修改 FileScanner.SUPPORTED_EXTENSIONS
- 添加新的调度策略：扩展 TaskScheduler

---

## 测试覆盖

### 单元测试
- ✅ FileScanner.scan_input() - 单文件、多文件、目录
- ✅ FileScanner.validate_file() - 文件验证
- ✅ TaskItem 创建和状态转换
- ✅ TaskItem.duration() - 时长计算

### 集成测试
- ✅ CLI batch 命令帮助显示
- ✅ 模块导入测试
- ✅ 参数解析测试

### 手动测试
- ⏳ 实际批量执行测试（需要 API Key 和 Docker）

---

## 性能特征

### 时间复杂度
- 文件扫描: O(n)，n 为文件数量
- 任务调度: O(n)，n 为任务数量
- 并行执行: O(n/w)，w 为并行进程数

### 空间复杂度
- 内存: O(w × m)，w 为并行进程数，m 为单个任务内存占用
- 磁盘: O(n × s)，n 为任务数量，s 为单个任务输出大小

### 资源占用
- CPU: w 个进程并行
- 内存: 每个进程约 200-500MB（Docker 容器 + Python）
- 磁盘: 每个任务约 10-50KB（输出文件）

---

## 最佳实践

### 1. 并行度设置
- 小型机器: `-w 2`
- 中型机器: `-w 4`
- 大型机器: `-w 8`

### 2. 重试策略
- 稳定环境: `-r 1`
- 一般环境: `-r 2`（默认）
- 不稳定环境: `-r 3`

### 3. 分批处理
大量任务建议分批次：
```bash
oj-problem-import batch batch1/ -w 4
oj-problem-import batch batch2/ -w 4
```

### 4. 监控执行
- 观察实时进度
- 检查成功率
- 分析失败原因

---

## 未来扩展

### 短期
- [ ] 添加进度条（tqdm）
- [ ] 支持任务优先级
- [ ] 支持断点续传
- [ ] 添加任务队列持久化

### 中期
- [ ] 支持分布式执行
- [ ] 添加任务依赖关系
- [ ] 支持动态调整并行度
- [ ] 添加性能监控

### 长期
- [ ] 支持 GPU 加速
- [ ] 智能负载均衡
- [ ] 自适应重试策略
- [ ] 机器学习优化参数

---

## 总结

多任务处理系统采用模块化设计，清晰的分层架构，使得：
- ✅ 易于理解
- ✅ 易于维护
- ✅ 易于扩展
- ✅ 易于测试

总代码量约 678 行，实现了完整的多任务处理功能。

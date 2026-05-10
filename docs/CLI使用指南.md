# OJ Engine CLI 使用指南

## 概述

OJ Engine 提供了便捷的命令行工具，可以通过终端命令直接生成 OJ 题目测试数据包。

## 安装

```bash
# 克隆项目
git clone <repository-url>
cd Oj-problem-import

# 安装依赖
uv sync

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的 API Key
```

## 基本用法

### 查看帮助

```bash
# 查看主命令帮助
uv run oj-engine --help

# 查看 generate 子命令帮助
uv run oj-engine generate --help
```

### 生成题目

#### 方式一：从文件读取题目描述（推荐）

创建一个文本文件（例如 `problem.txt`），写入题目描述：

```
A + B Problem

计算两个整数的和。

输入格式:
一行,包含两个整数 a 和 b,用空格分隔。

输出格式:
一行,包含 a + b 的结果。

数据范围:
-10^9 <= a, b <= 10^9

样例输入:
3 5

样例输出:
8
```

然后运行：

```bash
uv run oj-engine generate -f problem.txt
```

#### 方式二：直接在命令行传入题目描述

```bash
uv run oj-engine generate -d "A+B Problem. Calculate the sum of two integers."
```

注意：对于较长的题目描述，建议使用文件方式。

#### 自定义参数

```bash
# 设置最大迭代次数为 30
uv run oj-engine generate -f problem.txt -m 30

# 指定输出目录
uv run oj-engine generate -f problem.txt -o ./my_outputs

# 组合使用
uv run oj-engine generate -f problem.txt -m 30 -o ./results
```

## 命令参数说明

### generate 命令

生成 OJ 题目测试数据包。

**选项：**

- `-f, --file PATH`: 题目描述文件路径（UTF-8 编码）
- `-d, --description TEXT`: 题目描述文本（直接传入）
- `-m, --max-iterations INTEGER`: Agent 最大迭代次数（默认: 20）
- `-o, --output-dir TEXT`: 输出目录（默认: outputs）

**注意：** 必须提供 `--file` 或 `--description` 其中之一。

## 输出说明

生成的产物会保存在 `outputs/` 目录下，每个任务会创建一个带时间戳的子目录：

```
outputs/
└── 20260510_193303_第k小的数/
    ├── solution.py          # 标答代码
    ├── generator.py         # 数据生成器
    └── tests/               # 测试数据目录
        ├── 1.in             # 第1组输入（样例）
        ├── 1.out            # 第1组输出（样例）
        ├── 2.in
        ├── 2.out
        ...
        └── 10.out
```

**产物结构：**
- `solution.py`: 正确的标答代码（Python）
- `generator.py`: 数据生成器代码（Python）
- `tests/`: 包含 10 组成对的 `.in` 和 `.out` 文件
  - 第 1 组是题目中的样例（如果有）
  - 其余 9 组由 generator 生成，符合 30%小 + 50%中 + 20%大/边缘 的分布

## 示例

### 示例 1：简单题目

```bash
# 创建题目文件
echo "A + B Problem

计算两个整数的和。

输入格式:
一行,包含两个整数 a 和 b。

输出格式:
一行,包含 a + b 的结果。

样例输入:
3 5

样例输出:
8" > ab_problem.txt

# 生成题目
uv run oj-engine generate -f ab_problem.txt
```

### 示例 2：复杂算法题

```bash
# 使用更长的迭代次数处理复杂题目
uv run oj-engine generate -f lis_problem.txt -m 40
```

### 示例 3：批量生成

```bash
# 编写脚本批量处理
for file in problems/*.txt; do
    uv run oj-engine generate -f "$file" -o ./batch_outputs
done
```

## 常见问题

### Q: 为什么需要使用 `uv run`？

A: 在开发环境中，使用 `uv run` 可以确保使用项目虚拟环境中的依赖。如果希望全局使用，可以安装到系统 Python：

```bash
pip install -e .
```

然后直接使用：

```bash
oj-engine generate -f problem.txt
```

### Q: 如何查看生成的产物？

A: 产物保存在 `outputs/` 目录下，可以使用提供的 `view_outputs.py` 工具查看：

```bash
uv run python view_outputs.py
```

### Q: 生成失败怎么办？

A: 检查以下几点：
1. 确认 `.env` 文件中配置了正确的 API Key
2. 确认 Docker Desktop 正在运行
3. 检查题目描述是否清晰完整
4. 尝试增加 `--max-iterations` 参数值

### Q: 如何清理旧的输出？

A: 手动删除 `outputs/` 目录下的旧文件夹，或使用系统命令：

```bash
# Linux/Mac
rm -rf outputs/*

# Windows PowerShell
Remove-Item outputs\* -Recurse
```

## 高级用法

### 结合其他工具

```bash
# 使用 curl 从网络获取题目描述并生成
curl -s https://example.com/problem.txt | \
    uv run oj-engine generate -d "$(cat)"

# 将生成的产物打包
uv run oj-engine generate -f problem.txt
tar -czf output.tar.gz outputs/latest/
```

### 自定义输出目录

```bash
# 按项目组织输出
uv run oj-engine generate -f problem.txt -o ./projects/sorting_algorithms

# 按日期组织输出
DATE=$(date +%Y%m%d)
uv run oj-engine generate -f problem.txt -o ./outputs/$DATE
```

## 技术支持

如有问题或建议，请提交 Issue 或联系维护者。

---

**提示**: CLI 工具仍在持续优化中，欢迎反馈使用体验！

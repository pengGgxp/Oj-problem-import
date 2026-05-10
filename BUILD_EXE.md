# OJ Engine Nuitka 打包指南

## 前置要求

### 1. 安装 Nuitka
```bash
pip install nuitka
```

### 2. 安装 C 编译器（Windows）
Nuitka 需要 C 编译器来编译代码，推荐使用：

**选项 A: Microsoft Visual Studio Build Tools（推荐）**
- 下载: https://visualstudio.microsoft.com/visual-cpp-build-tools/
- 安装时选择 "C++ build tools"
- 确保包含 "MSVC v14x - VS 20xx C++ x64/x86 build tools"

**选项 B: MinGW-w64**
```bash
# 使用 chocolatey 安装
choco install mingw
```

### 3. 验证安装
```bash
nuitka --version
```

## 打包命令

### 基础打包命令
```bash
nuitka --standalone ^
    --onefile ^
    --windows-disable-console ^
    --include-package=oj_engine ^
    --include-package=click ^
    --include-package=questionary ^
    --include-package=platformdirs ^
    --include-package=langgraph ^
    --include-package=langchain ^
    --include-package=langchain_openai ^
    --include-package=docker ^
    --include-package=pydantic ^
    --include-package=pydantic_settings ^
    --python-flag=no_site ^
    --output-dir=dist ^
    oj_engine/cli.py
```

### 优化后的打包命令（推荐）
```bash
nuitka --standalone ^
    --onefile ^
    --windows-icon-from-ico=icon.ico ^
    --include-package=oj_engine ^
    --include-package=click ^
    --include-package=questionary ^
    --include-package=platformdirs ^
    --include-package=langgraph ^
    --include-package=langchain ^
    --include-package=langchain_openai ^
    --include-package=langchain_community ^
    --include-package=langchain_classic ^
    --include-package=docker ^
    --include-package=pydantic ^
    --include-package=pydantic_settings ^
    --include-package=dotenv ^
    --include-data-dir=outputs=outputs ^
    --python-flag=no_site ^
    --assume-yes-for-downloads ^
    --output-dir=dist ^
    --output-filename=oj-engine.exe ^
    oj_engine/cli.py
```

## 参数说明

| 参数 | 说明 |
|------|------|
| `--standalone` | 创建独立可执行文件，包含所有依赖 |
| `--onefile` | 打包为单个 exe 文件 |
| `--windows-disable-console` | Windows 下不显示控制台窗口（GUI 应用） |
| `--windows-icon-from-ico` | 设置 exe 图标 |
| `--include-package` | 显式包含指定的 Python 包 |
| `--include-data-dir` | 包含数据目录 |
| `--python-flag=no_site` | 不使用 site-packages，减小体积 |
| `--assume-yes-for-downloads` | 自动确认下载 |
| `--output-dir` | 输出目录 |
| `--output-filename` | 输出文件名 |

## 注意事项

### 1. Docker 依赖
由于项目依赖 Docker，打包后的 exe 仍需要：
- Docker Desktop 已安装并运行
- 用户有 Docker 访问权限

### 2. 配置文件
打包后的 exe 会从用户配置目录读取配置：
- Windows: `%LOCALAPPDATA%\oj-engine\oj-engine\config.json`
- 首次运行时会自动启动配置向导

### 3. 环境变量
如果使用 .env 文件，需要将 .env 放在 exe 同目录下，或使用配置向导。

### 4. 体积优化
Nuitka 打包后的 exe 体积较大（约 100-200MB），因为包含了：
- Python 解释器
- 所有依赖库
- LangChain/LangGraph 等大型库

### 5. 首次运行
首次运行时可能需要较长时间解压（--onefile 模式）。

## 常见问题

### Q1: 编译失败，提示找不到编译器
**解决**: 安装 Visual Studio Build Tools 或 MinGW

### Q2: 运行时缺少模块
**解决**: 使用 `--include-package` 显式包含缺失的模块

### Q3: exe 体积过大
**解决**: 
- 移除不必要的 `--include-package`
- 使用 `--python-flag=no_site`
- 考虑使用 UPX 压缩（`--enable-plugin=upx`）

### Q4: Docker 无法连接
**解决**: 确保 Docker Desktop 正在运行

## 测试打包

### 1. 清理旧文件
```bash
rm -rf dist build
```

### 2. 执行打包
```bash
./build_exe.bat
```

### 3. 测试生成的 exe
```bash
cd dist
.\oj-engine.exe --help
.\oj-engine.exe configure
.\oj-engine.exe generate -f test_problem.txt
```

## 分发

打包完成后，分发以下内容：
1. `dist/oj-engine.exe` - 主程序
2. `README.md` - 使用说明
3. （可选）示例题目文件

用户只需：
1. 安装 Docker Desktop
2. 运行 `oj-engine.exe configure` 配置 API Key
3. 开始使用！

# 快速打包指南

## 一键打包

### Windows (推荐)

**方式 1: 使用 PowerShell 脚本（推荐）**
```powershell
.\build_exe.ps1
```

**方式 2: 使用批处理文件**
```cmd
build_exe.bat
```

### 手动打包

```bash
# 安装 Nuitka
pip install nuitka

# 执行打包
nuitka --standalone ^
    --onefile ^
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
    --output-filename=oj-engine.exe ^
    oj_engine/cli.py
```

## 前置要求

1. **Python 3.12+** 已安装
2. **Nuitka** 已安装: `pip install nuitka`
3. **C 编译器** (Windows):
   - Visual Studio Build Tools, 或
   - MinGW-w64

## 打包后

生成的文件位于: `dist/oj-engine.exe`

### 测试
```bash
cd dist
.\oj-engine.exe --help
.\oj-engine.exe configure
```

### 分发
将 `oj-engine.exe` 分发给用户，用户需要：
1. 安装 Docker Desktop
2. 运行 `oj-engine.exe configure` 配置 API Key
3. 开始使用！

## 常见问题

**Q: 编译很慢？**
A: 首次编译需要较长时间（5-15分钟），这是正常的。

**Q: exe 文件很大？**
A: Nuitka 打包包含 Python 解释器和所有依赖，约 100-200MB 是正常的。

**Q: 运行时提示缺少模块？**
A: 确保在打包命令中包含了所有必要的 `--include-package` 参数。

**Q: Docker 无法连接？**
A: 确保 Docker Desktop 正在运行。

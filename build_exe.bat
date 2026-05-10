@echo off
chcp 65001 >nul
echo ========================================
echo OJ Engine Nuitka 打包脚本
echo ========================================
echo.

REM 检查 Nuitka 是否安装
where nuitka >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] Nuitka 未安装，请先运行: pip install nuitka
    pause
    exit /b 1
)

echo [1/4] 清理旧的构建文件...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist oj-engine.build rmdir /s /q oj-engine.build
if exist oj-engine.dist rmdir /s /q oj-engine.dist
if exist oj-engine.onefile-build rmdir /s /q oj-engine.onefile-build
echo ✓ 清理完成
echo.

echo [2/4] 开始编译（这可能需要几分钟）...
echo.

nuitka --standalone ^
    --onefile ^
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
    --include-package=fastapi ^
    --python-flag=no_site ^
    --assume-yes-for-downloads ^
    --output-dir=dist ^
    --output-filename=oj-engine.exe ^
    oj_engine/cli.py

if %errorlevel% neq 0 (
    echo.
    echo [错误] 编译失败！
    pause
    exit /b 1
)

echo.
echo ✓ 编译完成
echo.

echo [3/4] 检查输出文件...
if exist dist\oj-engine.exe (
    echo ✓ 找到生成的 exe 文件
    for %%A in (dist\oj-engine.exe) do (
        echo   文件大小: %%~zA bytes
    )
) else (
    echo [错误] 未找到生成的 exe 文件
    pause
    exit /b 1
)
echo.

echo [4/4] 测试 exe 文件...
echo 运行: dist\oj-engine.exe --help
dist\oj-engine.exe --help

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo ✓ 打包成功！
    echo ========================================
    echo.
    echo 生成的文件: dist\oj-engine.exe
    echo.
    echo 使用说明:
    echo   1. 确保 Docker Desktop 已安装并运行
    echo   2. 首次运行请执行: oj-engine.exe configure
    echo   3. 然后可以开始生成题目
    echo.
) else (
    echo.
    echo [警告] exe 文件测试失败，但可能仍可正常使用
    echo.
)

pause

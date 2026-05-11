# OJ Engine Nuitka 打包脚本 (PowerShell)
# 使用方法: .\build_exe.ps1

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "OJ Engine Nuitka 打包脚本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Nuitka 是否安装
Write-Host "[检查] 验证 Nuitka 安装..." -ForegroundColor Yellow
try {
    $nuitkaVersion = & uv run nuitka --version 2>&1
    Write-Host "✓ Nuitka 已安装: $nuitkaVersion" -ForegroundColor Green
} catch {
    Write-Host "[错误] Nuitka 未安装，请先运行: uv pip install nuitka" -ForegroundColor Red
    Read-Host "按回车键退出"
    exit 1
}

Write-Host ""

# 清理旧的构建文件
Write-Host "[1/4] 清理旧的构建文件..." -ForegroundColor Yellow
$dirsToRemove = @("dist", "build", "oj-engine.build", "oj-engine.dist", "oj-engine.onefile-build")
foreach ($dir in $dirsToRemove) {
    if (Test-Path $dir) {
        Remove-Item -Recurse -Force $dir
        Write-Host "  已删除: $dir" -ForegroundColor Gray
    }
}
Write-Host "✓ 清理完成" -ForegroundColor Green
Write-Host ""

# 开始编译
Write-Host "[2/4] 开始编译（这可能需要几分钟）..." -ForegroundColor Yellow
Write-Host ""

$nuitkaArgs = @(
    "--standalone",
    "--onefile",
    "--include-package=oj_engine",
    "--include-package=click",
    "--include-package=questionary",
    "--include-package=platformdirs",
    "--include-package=langgraph",
    "--include-package=langchain",
    "--include-package=langchain_openai",
    "--include-package=langchain_community",
    "--include-package=langchain_classic",
    "--include-package=langchain_core",
    "--include-package=docker",
    "--include-package=pydantic",
    "--include-package=pydantic_settings",
    "--include-package=dotenv",
    "--include-package=fastapi",
    "--python-flag=no_site",
    "--jobs=4",
    "--assume-yes-for-downloads",
    "--output-dir=dist",
    "--output-filename=oj-engine.exe",
    "oj_engine/cli.py"
)

try {
    & uv run nuitka $nuitkaArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Nuitka 编译失败"
    }
} catch {
    Write-Host ""
    Write-Host "[错误] 编译失败！" -ForegroundColor Red
    Read-Host "按回车键退出"
    exit 1
}

Write-Host ""
Write-Host "✓ 编译完成" -ForegroundColor Green
Write-Host ""

# 检查输出文件
Write-Host "[3/4] 检查输出文件..." -ForegroundColor Yellow
$exePath = "dist\oj-engine.exe"
if (Test-Path $exePath) {
    $fileInfo = Get-Item $exePath
    $fileSizeMB = [math]::Round($fileInfo.Length / 1MB, 2)
    Write-Host "✓ 找到生成的 exe 文件" -ForegroundColor Green
    Write-Host "  文件路径: $exePath" -ForegroundColor Gray
    Write-Host "  文件大小: $fileSizeMB MB" -ForegroundColor Gray
} else {
    Write-Host "[错误] 未找到生成的 exe 文件" -ForegroundColor Red
    Read-Host "按回车键退出"
    exit 1
}
Write-Host ""

# 测试 exe 文件
Write-Host "[4/4] 测试 exe 文件..." -ForegroundColor Yellow
Write-Host "运行: dist\oj-engine.exe --help" -ForegroundColor Gray
try {
    & dist\oj-engine.exe --help
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "✓ 打包成功！" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "生成的文件: dist\oj-engine.exe" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "使用说明:" -ForegroundColor Yellow
        Write-Host "  1. 确保 Docker Desktop 已安装并运行" -ForegroundColor Gray
        Write-Host "  2. 首次运行请执行: oj-engine.exe configure" -ForegroundColor Gray
        Write-Host "  3. 然后可以开始生成题目" -ForegroundColor Gray
        Write-Host ""
    } else {
        Write-Host ""
        Write-Host "[警告] exe 文件测试失败，但可能仍可正常使用" -ForegroundColor Yellow
        Write-Host ""
    }
} catch {
    Write-Host ""
    Write-Host "[警告] 测试过程中出现异常" -ForegroundColor Yellow
    Write-Host $_.Exception.Message -ForegroundColor Gray
    Write-Host ""
}

Read-Host "按回车键退出"


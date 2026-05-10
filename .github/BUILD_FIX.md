# GitHub Actions 构建失败修复说明

## 问题描述

GitHub Actions 构建失败，错误信息：
```
FATAL: Error, failed to locate package 'questionary' you asked to include.
```

## 根本原因

在 GitHub Actions 环境中：
1. `uv sync` 将依赖安装到虚拟环境（`.venv`）
2. 但直接使用 `nuitka` 命令时，使用的是系统 Python，无法访问虚拟环境中的包
3. Nuitka 找不到通过 `uv` 安装的包（如 `questionary`、`click` 等）

## 解决方案

### 修改前 ❌
```yaml
- name: Install Nuitka
  run: |
    pip install nuitka
    
- name: Build EXE with Nuitka
  run: |
    nuitka --standalone --onefile ...
```

### 修改后 ✅
```yaml
- name: Install Nuitka with onefile support
  run: |
    # 使用 uv 安装 Nuitka 到虚拟环境
    uv pip install "nuitka[onefile]"
    
- name: Build EXE with Nuitka
  run: |
    uv run nuitka --standalone --onefile ...
```

## 关键改动

### 1. 使用 `uv pip install` 而非 `pip install`
```yaml
# 错误：安装到系统 Python
pip install nuitka

# 正确：安装到 uv 虚拟环境
uv pip install "nuitka[onefile]"
```

### 2. 使用 `uv run` 执行 Nuitka
```yaml
# 错误：使用系统 Python 的 Nuitka
nuitka --standalone ...

# 正确：使用虚拟环境中的 Nuitka
uv run nuitka --standalone ...
```

### 3. 添加 onefile 支持
```yaml
# 安装完整的 Nuitka（包含 zstandard 压缩支持）
uv pip install "nuitka[onefile]"
```

这解决了警告：
```
Nuitka-Onefile:WARNING: Onefile mode cannot compress without 'zstandard' package installed
```

## 验证步骤

### 本地测试
```bash
# 1. 确保使用 uv 安装
uv pip install "nuitka[onefile]"

# 2. 使用 uv run 执行
uv run nuitka --version

# 3. 执行打包
uv run nuitka --standalone --onefile ...
```

### GitHub Actions 测试
推送修改后的工作流文件，观察新的构建结果。

## 其他注意事项

### 1. 包验证步骤
添加了验证步骤，确保关键包已安装：
```yaml
- name: Verify installed packages
  run: |
    pip list | Select-String "questionary"
    pip list | Select-String "click"
    pip list | Select-String "platformdirs"
```

### 2. 为什么不用 `actions/setup-python` 的虚拟环境？
- `uv` 创建了自己的虚拟环境（`.venv`）
- 需要保持一致性，所有操作都通过 `uv` 进行

### 3. 为什么不使用 `pip install -e .`？
- 项目使用 `uv` 管理依赖
- `uv sync` 已经安装了所有依赖
- 保持工具链一致性

## 完整的工作流程

```yaml
1. Checkout code
2. Setup Python 3.12
3. Install dependencies (uv sync)
4. Install Nuitka (uv pip install "nuitka[onefile]")
5. Verify installation (uv run nuitka --version)
6. Verify packages (pip list)
7. Clean previous builds
8. Build EXE (uv run nuitka ...)
9. Verify output
10. Test EXE
11. Upload artifact
12. Create Release (if tag)
```

## 常见问题

### Q1: 为什么之前本地可以运行？
A: 本地环境中，你可能激活了虚拟环境，或者 Nuitka 安装在系统 Python 中。

### Q2: 可以直接用 `pip` 吗？
A: 可以，但需要确保所有包都用 `pip` 安装，不要混用 `uv` 和 `pip`。

### Q3: `nuitka[onefile]` 是什么？
A: Nuitka 的 extras，包含 onefile 模式所需的依赖（如 zstandard）。

## 参考链接

- [Nuitka Documentation](https://nuitka.net/)
- [uv Documentation](https://github.com/astral-sh/uv)
- [GitHub Actions](https://docs.github.com/en/actions)

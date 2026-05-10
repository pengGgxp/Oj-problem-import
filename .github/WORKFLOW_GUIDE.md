# GitHub Actions 自动打包指南

## 概述

本项目配置了 GitHub Actions 工作流，可以自动在 Windows x64 平台上使用 Nuitka 编译生成 exe 文件。

## 触发条件

工作流会在以下情况自动触发：

1. **推送到主分支**: `push` 到 `main` 或 `master` 分支
2. **创建标签**: 推送 `v*` 格式的标签（如 `v1.0.0`）
3. **Pull Request**: 向主分支提交 PR
4. **手动触发**: 在 GitHub Actions 页面手动运行

## 工作流程

### 1. 环境准备
- 使用 `windows-latest` runner（Windows Server 2022）
- 安装 Python 3.12
- 安装项目依赖（使用 uv）
- 安装 Nuitka

### 2. 编译打包
使用 Nuitka 编译为单个 exe 文件：
```bash
nuitka --standalone --onefile \
  --include-package=oj_engine \
  --include-package=click \
  ...
  --output-filename=oj-engine.exe \
  oj_engine/cli.py
```

### 3. 验证测试
- 检查生成的 exe 文件是否存在
- 显示文件大小
- 运行 `--help` 测试基本功能

### 4. 上传产物
- 将 exe 作为 artifact 上传（保留 30 天）
- 如果是 tag 推送，自动创建 GitHub Release

## 使用方法

### 方法 1: 推送到主分支

```bash
git add .
git commit -m "Update code"
git push origin main
```

GitHub Actions 会自动开始构建。

### 方法 2: 创建发布标签（推荐）

```bash
# 创建标签
git tag v1.0.0

# 推送标签
git push origin v1.0.0
```

这会触发构建并自动创建 GitHub Release。

### 方法 3: 手动触发

1. 进入 GitHub 仓库的 **Actions** 页面
2. 选择 **Build Windows EXE with Nuitka** 工作流
3. 点击 **Run workflow** 按钮
4. 选择分支（通常选 `main`）
5. 点击 **Run workflow**

## 查看构建结果

### 查看构建进度
1. 进入 **Actions** 页面
2. 点击正在运行的工作流
3. 查看实时日志

### 下载构建产物

#### 从 Artifact 下载（所有构建）
1. 进入工作流运行页面
2. 滚动到底部的 **Artifacts** 部分
3. 点击 `oj-engine-windows-x64` 下载

#### 从 Release 下载（仅标签构建）
1. 进入仓库的 **Releases** 页面
2. 找到对应的版本
3. 下载 `oj-engine.exe`

## 自定义配置

### 修改 Python 版本

编辑 `.github/workflows/build-windows-exe.yml`:
```yaml
- name: Set up Python
  uses: actions/setup-python@v5
  with:
    python-version: '3.12'  # 修改这里
```

### 添加更多包含的包

在 Build 步骤中添加：
```yaml
--include-package=your_package \
```

### 启用 UPX 压缩（减小体积）

添加参数：
```yaml
--enable-plugin=upx \
```

注意：需要在 runner 上安装 UPX。

### 修改保留时间

```yaml
- name: Upload artifact
  uses: actions/upload-artifact@v4
  with:
    retention-days: 90  # 改为 90 天
```

## 故障排查

### Q1: 构建失败，提示找不到模块

**解决**: 在 Nuitka 命令中添加缺失的包：
```yaml
--include-package=missing_package \
```

### Q2: 构建超时

Nuitka 编译可能需要较长时间（10-20 分钟）。如果超时：
- 检查是否有无限循环
- 考虑减少包含的包
- 联系 GitHub Support 增加超时限制

### Q3: exe 无法运行

**可能原因**:
1. 缺少运行时依赖
2. Docker Desktop 未安装

**解决**:
- 检查构建日志中的警告信息
- 确保用户已安装 Docker Desktop

### Q4: 文件大小过大

**优化建议**:
- 移除不必要的 `--include-package`
- 使用 `--python-flag=no_site`（已启用）
- 考虑使用 UPX 压缩

## 最佳实践

1. **使用标签发布**: 通过 `v*` 标签触发自动发布
2. **测试后再发布**: 先在 PR 中测试构建
3. **定期清理**: Artifact 会自动保留 30 天
4. **版本命名**: 使用语义化版本（如 `v1.0.0`, `v1.1.0`）

## 示例：完整发布流程

```bash
# 1. 确保代码已提交
git add .
git commit -m "Prepare for release v1.0.0"
git push origin main

# 2. 创建标签
git tag v1.0.0

# 3. 推送标签（触发自动构建和发布）
git push origin v1.0.0

# 4. 等待 GitHub Actions 完成
# 5. 在 Releases 页面下载发布的 exe
```

## 相关文档

- [BUILD_EXE.md](../BUILD_EXE.md) - 本地打包指南
- [QUICK_BUILD.md](../QUICK_BUILD.md) - 快速开始
- [build_exe.ps1](../build_exe.ps1) - 本地打包脚本

## 注意事项

⚠️ **重要提醒**:
- GitHub Actions 每月有免费分钟数限制
- Windows runner 消耗分钟数较快（约 2x）
- 大型项目编译可能需要 15-30 分钟
- 建议在本地测试成功后再推送到 CI

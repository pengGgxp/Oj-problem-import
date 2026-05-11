# 发布到 PyPI 指南

本文档说明如何将 OJ Problem Import 项目发布到 PyPI，以便用户可以通过 `uvx` 使用。

## 前置准备

### 1. 注册 PyPI 账号
- 访问 [PyPI](https://pypi.org/) 注册账号
- 验证邮箱地址

### 2. 生成 API Token
1. 登录 PyPI
2. 进入 **Account Settings** → **API tokens**
3. 点击 **Add API token**
4. 设置 token 名称（如 "OJ Problem Import"）
5. 选择范围：**Entire account** 或 **Specific project**（选择 `oj-problem-import`）
6. 点击 **Create token**
7. **复制并保存 token**（只会显示一次！）

## 发布步骤

### 方法 1: 使用环境变量（推荐）

```powershell
# Windows PowerShell
$env:TWINE_USERNAME = "__token__"
$env:TWINE_PASSWORD = "pypi-YourAPITokenHere"

# 上传到正式 PyPI
uv run twine upload dist/*
```

### 方法 2: 使用 .pypirc 文件

1. 在项目根目录创建 `.pypirc` 文件（已提供模板）
2. 在文件中填入您的 API token：
   ```ini
   [pypi]
   username = __token__
   password = pypi-YourAPITokenHere
   ```
3. 上传：
   ```bash
   uv run twine upload dist/*
   ```

### 方法 3: 交互式输入

```bash
uv run twine upload dist/*
# 系统会提示输入用户名和密码
# 用户名: __token__
# 密码: pypi-YourAPITokenHere
```

## 测试发布（可选但推荐）

在正式发布前，建议先发布到 TestPyPI 进行测试：

```powershell
# 设置 TestPyPI token
$env:TWINE_USERNAME = "__token__"
$env:TWINE_PASSWORD = "pypi-YourTestPyPITokenHere"

# 上传到 TestPyPI
uv run twine upload --repository testpypi dist/*
```

测试安装：
```bash
# 从 TestPyPI 安装测试
uv pip install --index-url https://test.pypi.org/simple/ oj-problem-import
```

## 构建新版本

每次发布前需要更新版本号：

1. 编辑 `pyproject.toml`：
   ```toml
   [project]
   version = "0.1.1"  # 更新版本号
   ```

2. 重新构建：
   ```bash
   uv build
   ```

3. 上传：
   ```bash
   uv run twine upload dist/*
   ```

## 用户使用

发布成功后，用户可以通过以下方式使用：

### 直接运行（无需安装）
```bash
uvx oj-problem-import generate -f problem.txt
```

### 安装后使用
```bash
# 安装
uv pip install oj-problem-import

# 使用
oj-engine generate -f problem.txt
```

## 常见问题

### Q1: 上传失败，提示 "File already exists"
**原因**: 该版本已存在  
**解决**: 更新 `pyproject.toml` 中的版本号，重新构建并发布

### Q2: 上传失败，提示 "Invalid credentials"
**原因**: API token 错误或过期  
**解决**: 
- 检查 token 是否正确
- 确保用户名是 `__token__`
- 重新生成 token

### Q3: 找不到包
**原因**: 包名可能已被占用  
**解决**: 
- 在 PyPI 搜索 `oj-problem-import`
- 如果已被占用，修改 `pyproject.toml` 中的 `name` 字段

### Q4: 构建失败
**原因**: 配置错误或依赖问题  
**解决**: 
- 检查 `pyproject.toml` 格式
- 运行 `uv build` 查看详细错误信息

## 版本命名规范

遵循[语义化版本](https://semver.org/)：

- **主版本号**.次版本号.修订号 (MAJOR.MINOR.PATCH)
- 例如: `0.1.0`, `0.1.1`, `0.2.0`, `1.0.0`

### 何时更新版本号：
- **PATCH** (0.1.0 → 0.1.1): Bug 修复
- **MINOR** (0.1.0 → 0.2.0): 新增功能（向后兼容）
- **MAJOR** (0.1.0 → 1.0.0): 重大变更（不向后兼容）

## 自动化发布（推荐）

项目已配置 GitHub Actions 自动发布，使用 **受信任发布（Trusted Publishing）**，无需管理 API Token。

### 配置步骤：

1. **在 PyPI 上配置受信任发布者**：
   - 访问 https://pypi.org/manage/account/publishing/
   - Publisher: `GitHub`
   - Owner: `pengGgxp`
   - Repository: `Oj-problem-import`
   - Workflow name: `publish.yml`
   - 点击 **Add publisher**

2. **推送标签触发发布**：
   ```bash
   # 更新版本号后
   git add .
   git commit -m "Release v0.1.0"
   git tag v0.1.0
   git push origin v0.1.0
   ```

3. **或者创建 GitHub Release**：
   - 在 GitHub 仓库页面点击 **Releases**
   - 点击 **Create a new release**
   - 选择标签（如 `v0.1.0`）
   - 填写发布说明
   - 点击 **Publish release**

工作流会自动构建并发布到 PyPI！

### 手动触发（可选）

如果需要手动触发发布：
1. 进入 GitHub 仓库的 **Actions** 页面
2. 选择 **Publish to PyPI** 工作流
3. 点击 **Run workflow**
4. 选择分支
5. 点击 **Run workflow**

## 相关资源

- [PyPI 官方文档](https://packaging.python.org/)
- [Twine 文档](https://twine.readthedocs.io/)
- [uv 文档](https://github.com/astral-sh/uv)
- [语义化版本规范](https://semver.org/)

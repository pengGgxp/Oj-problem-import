# 发布检查清单

在发布新版本到 PyPI 之前，请完成以下检查：

## 📋 发布前检查

### 1. 代码质量
- [ ] 所有测试通过
- [ ] 代码已格式化
- [ ] 没有调试代码或注释掉的代码
- [ ] 更新了版本号（`pyproject.toml`）

### 2. 文档更新
- [ ] README.md 已更新（如需要）
- [ ] CHANGELOG.md 已更新（如有）
- [ ] 文档中的示例代码已测试

### 3. 依赖检查
- [ ] `uv.lock` 已更新
- [ ] 所有依赖都正确声明在 `pyproject.toml` 中
- [ ] 没有不必要的依赖

### 4. 构建测试
- [ ] 本地构建成功：`uv build`
- [ ] 生成的包可以安装：`uv pip install dist/*.whl`
- [ ] CLI 命令正常工作：`oj-engine --help`

## 🚀 发布步骤

### 1. 提交代码
```bash
git add .
git commit -m "Release v0.1.0"
git push origin main
```

### 2. 创建标签
```bash
git tag v0.1.0
git push origin v0.1.0
```

### 3. 触发自动发布
推送标签后，GitHub Actions 会自动：
1. 构建包
2. 发布到 PyPI
3. 上传构建产物

### 4. 验证发布
```bash
# 等待几分钟后测试
uvx oj-problem-import --help

# 或从 PyPI 安装测试
uv pip install oj-problem-import
oj-engine --help
```

## 🔍 发布后验证

### 1. 检查 PyPI 页面
- 访问 https://pypi.org/project/oj-problem-import/
- 确认版本号正确
- 确认描述和元数据正确显示

### 2. 测试安装
```bash
# 在新环境中测试
uv pip install oj-problem-import
oj-engine configure
```

### 3. 测试 uvx
```bash
uvx oj-problem-import --help
```

## ⚠️ 常见问题

### 构建失败
- 检查 `pyproject.toml` 格式
- 运行 `uv build` 查看详细错误
- 确保所有必需文件都存在

### 发布失败
- 检查 GitHub Actions 日志
- 确认 PyPI 受信任发布者配置正确
- 确认标签格式正确（v*.*.*）

### 包名冲突
- 在 PyPI 搜索确认包名可用
- 如需修改，更新 `pyproject.toml` 中的 `name`

## 📝 版本命名

遵循语义化版本 (MAJOR.MINOR.PATCH)：

- **PATCH** (0.1.0 → 0.1.1): Bug 修复
- **MINOR** (0.1.0 → 0.2.0): 新增功能（向后兼容）
- **MAJOR** (0.1.0 → 1.0.0): 重大变更（不向后兼容）

## 🔗 相关链接

- PyPI 项目页面: https://pypi.org/project/oj-problem-import/
- GitHub Releases: https://github.com/pengGgxp/Oj-problem-import/releases
- GitHub Actions: https://github.com/pengGgxp/Oj-problem-import/actions

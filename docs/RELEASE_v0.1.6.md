# v0.1.6 Release Draft

> 范围：`v0.1.5..HEAD`  
> 目标标签：`v0.1.6`  
> 状态：release 草稿已生成，tag 尚未创建

## Highlights

- feat: 新增多语言沙箱执行能力，支持 Python、C++、C、Java、JavaScript、Go、Rust。
- feat: 批量任务输出支持按任务分组展示 AI 可见思考与执行日志，便于审查失败原因和生成过程。
- fix: 修复 `uv run oj_engine/cli.py batch ...` 脚本入口下相对导入失败的问题。
- fix: 移除旧的 `official_solution` / `solution_language` 参数链路，避免 `generate_problem()` 收到已删除参数。
- fix: 将 CLI/Worker 状态符号改为 `[OK]`、`[FAIL]`、`[WARN]`，避免 GBK/PowerShell 终端编码错误。
- feat(agent): 任务文件现在被视为完整提示词；如果任务文件包含标程、题解、语言要求或特殊生成要求，Agent 会整体理解并执行。
- feat(agent): 生成器语言不再强制为 Python，可使用 `generator.<ext>` 并按实际语言运行。

## Changes

### feat

- feat(sandbox): 支持多语言 Docker 运行时注册表。
  - 新增语言别名和文件扩展名推断。
  - `execute_code` 可按 `language` 参数或源文件扩展名选择镜像。
  - 支持每种语言独立容器，并共享同一个任务工作目录。
  - 默认支持：`python`、`cpp`、`c`、`java`、`javascript`、`go`、`rust`。

- feat(batch): 增强批量任务调度日志。
  - 新增 `--show-logs` 显示每个任务的完整分组日志。
  - 新增 `--log-lines` 控制失败任务默认展示的日志尾部行数。
  - 批量执行摘要展示任务队列、输出路径、耗时、成功率。
  - 并行任务日志不再直接交错刷屏，而是按任务聚合输出。

- feat(agent): 增加 AI 可见思考输出。
  - 捕获并展示 Agent 在关键阶段的可见总结。
  - 在递归步数达到上限时保留已产生的可见输出，错误信息更可读。

### fix

- fix(cli): 修复 batch 子命令在脚本方式运行时的相对导入错误。
  - `from .file_scanner` 等相对导入改为 `oj_engine.*` 绝对导入。
  - 真实入口 `uv run oj_engine/cli.py batch ...` 可正常执行。

- fix(cli): 移除旧官方题解独立参数链路。
  - 删除 `--solution-file`、`--solution-language` 入口参数。
  - `generate` 只把任务文件内容传给 `ProblemGenerationAgent.generate_problem()`。
  - 修复 `unexpected keyword argument 'official_solution'`。

- fix(cli): 修复部分 Windows/GBK 终端输出问题。
  - 状态符号从 `✓/✗/⚠` 改为 ASCII 风格的 `[OK]/[FAIL]/[WARN]`。
  - 避免成功提示输出失败时被误报为“无法读取文件”。

- fix(errors): 新增用户友好的 Docker 和文件扫描错误提示。
  - Docker 未安装、未启动、启动中、镜像缺失等场景会给出更明确的操作建议。
  - 文件扫描缺失路径等错误更易定位。

### feat(agent)

- feat(agent): 任务文件即完整提示词。
  - 不再把输入文件只当作题面。
  - 支持在任务文件里直接包含官方题解、标程、参考代码、语言要求和生成策略。

- feat(agent): 放宽生成器语言限制。
  - 从固定 `generator.py` 改为 `generator.<ext>`。
  - Python 作为默认推荐，不再是硬性要求。
  - 如果任务文件提供其他语言生成器，或其他语言更适合性能/类型处理，可保留并运行对应语言版本。

### docs

- docs: 更新 README、CLI 使用指南和批量使用文档。
  - 补充多语言标答、任务文件语义、批量日志参数和目录扫描说明。
  - 更新示例命令和输出结构描述。

### test

- test: 新增 CLI、Agent prompt、沙箱生命周期、用户友好错误相关回归测试。
  - 覆盖 `generate` 不再传旧参数。
  - 覆盖 prompt 不再强制 Python 生成器。
  - 覆盖多语言容器共享同一工作目录，且任务 cleanup 前不销毁容器。
  - 覆盖 Docker/语言/文件扫描错误信息。

### chore

- chore(release): 版本号更新为 `0.1.6`。
- chore(repo): 更新依赖锁文件和部分开发环境配置。

## Compatibility Notes

- `generate` 子命令已移除 `--solution-file` 和 `--solution-language`。
  - 迁移方式：把官方题解、标程或语言要求直接写进任务文件。
  - Agent 会把任务文件作为完整提示词处理。

- 多语言执行仍依赖 Docker 镜像。
  - 常用镜像包括 `python:3.10-slim`、`gcc:13`、`eclipse-temurin:17`、`node:20-slim`、`golang:1.22`、`rust:1`。
  - 如果镜像不存在，需要先 `docker pull <image>`。

## Commits Reviewed

非 merge 提交：

- `8f04966` chore(release): update pyproject version to 0.1.6
- `a81f425` feat(agent): relax generator language restrictions
- `2778e17` fix(cli): fix batch entrypoint and remove stale solution args
- `c3b7d27` feat(batch): add visible AI output and grouped batch logs
- `cea81ee` fix(errors): add friendly batch and Docker error messages
- `f13af91` feat(agent): treat task files as the full prompt
- `29be64b` feat(sandbox): add multi-language sandbox execution support
- `c8048d3` feat(sandbox): add multi-language sandbox execution support

说明：`29be64b` 与 `c8048d3` 为同名同内容的多语言沙箱变更，release notes 中按一项能力归并描述。

## Suggested Verification

发布前建议执行：

```powershell
uv run python -m unittest discover -s tests -p "test*.py"
uv run oj_engine/cli.py generate --file <task-file>
uv run oj_engine/cli.py batch <task-file-1> <task-file-2> --show-logs --max-workers 2
uv build
```

## Create Tag

确认 release 内容和构建结果后再创建标签：

```bash
git tag v0.1.6
git push origin v0.1.6
```

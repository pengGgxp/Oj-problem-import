# 持久化沙箱会话机制

## 问题背景

之前的实现中，每次调用沙箱工具（如 `execute_code`）都会：
1. 创建新的临时目录
2. 启动新的 Docker 容器
3. 写入所有文件
4. 执行命令
5. 清理容器和目录

这导致：
- **性能低下**：频繁创建/销毁容器开销大
- **文件重复写入**：相同的代码文件被反复写入
- **资源浪费**：短时间内创建大量容器

## 解决方案

引入 `SandboxSession` 类，在 Agent 生命周期内维护一个持久化的工作目录和容器。

### 核心组件

#### 1. SandboxSession 类

```python
class SandboxSession:
    """持久化沙箱会话"""
    
    def initialize(self):
        """初始化：创建容器和工作目录"""
        
    def cleanup(self):
        """清理：停止容器并删除工作目录"""
        
    def write_file(self, filename: str, content: str):
        """写入文件到工作目录"""
        
    def execute_command(self, cmd: str, timeout: int = 30) -> dict:
        """在容器中执行命令"""
        
    def read_file(self, filename: str) -> str:
        """从工作目录读取文件"""
```

#### 2. Agent 集成

```python
class ProblemGenerationAgent:
    def __init__(self):
        # 创建持久化沙箱会话
        self.sandbox_session = SandboxSession()
        
        # 设置全局会话（供工具使用）
        set_global_sandbox_session(self.sandbox_session)
    
    def __enter__(self):
        """上下文管理器入口"""
        self.sandbox_session.initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.sandbox_session.cleanup()
        return False
    
    def close(self):
        """手动关闭（如果不使用上下文管理器）"""
        self.sandbox_session.cleanup()
```

#### 3. 工具层适配

```python
# 全局沙箱会话
_global_sandbox_session: SandboxSession = None

def get_sandbox_session() -> SandboxSession:
    """获取当前沙箱会话"""
    if _global_sandbox_session is not None:
        return _global_sandbox_session
    return SandboxSession()  # 向后兼容

@tool
def execute_code(code: str, input_data: str = "", timeout: int = 5) -> dict:
    """使用持久化会话执行代码"""
    session = get_sandbox_session()
    
    # 写入文件（复用已有目录）
    session.write_file("main.py", code)
    
    # 执行命令（复用已有容器）
    result = session.execute_command("python3 main.py", timeout=timeout)
    
    return {...}
```

## 使用方式

### 方式一：上下文管理器（推荐）

```python
from oj_engine.agent import ProblemGenerationAgent

with ProblemGenerationAgent(max_iterations=20) as agent:
    result = agent.generate_problem(problem_description)
# 自动清理沙箱资源
```

### 方式二：手动管理

```python
agent = ProblemGenerationAgent(max_iterations=20)
try:
    result = agent.generate_problem(problem_description)
finally:
    agent.close()  # 手动清理
```

## 工作流程

```
Agent 启动
    ↓
创建 SandboxSession
    ↓
initialize(): 创建容器 + 工作目录
    ↓
┌─────────────────────────────┐
│  Agent 执行任务              │
│  ├─ write_code_file()       │
│  └─ execute_code()          │
│  （所有工具共享同一会话）     │
└─────────────────────────────┘
    ↓
cleanup(): 删除容器 + 工作目录
    ↓
Agent 结束
```

## 优势

### 1. 性能提升
- **容器复用**：整个 Agent 生命周期只创建一次容器
- **文件缓存**：已写入的文件无需重复写入
- **减少开销**：避免频繁的容器启动/停止

### 2. 资源优化
- **单一容器**：同时只有一个容器运行
- **工作目录复用**：所有文件在同一目录下
- **统一清理**：结束时一次性清理所有资源

### 3. 向后兼容
- 保留原有的 `SandboxExecutor` 类
- 工具层自动检测是否使用持久化会话
- 不影响现有代码（如果没有设置全局会话）

## 测试

运行测试脚本验证功能：

```bash
python test_sandbox_session.py
```

预期输出：
```
================================================================================
Testing SandboxSession - Persistent Workspace
================================================================================

[1] Initializing sandbox session...
✓ Session initialized
  Work directory: /tmp/oj_sandbox_xxxxxx
  Container ID: abc123def456

[2] Writing files...
✓ Files written

[3] Executing commands...
  Command 1 output: Hello from persistent session!
  Exit code: 0

[4] Reading files...
  File content: print('Hello from persistent session!')

[5] Multiple executions (testing persistence)...
  Execution 1: Hello from persistent session!
  Execution 2: Hello from persistent session!
  Execution 3: Hello from persistent session!

✓ All tests passed!

[6] Cleaning up...
✓ Session cleaned up
```

## 注意事项

1. **必须清理资源**：使用完 Agent 后务必调用 `close()` 或使用上下文管理器
2. **线程安全**：当前实现不是线程安全的，每个线程应使用独立的 Agent 实例
3. **异常处理**：即使发生异常，也要确保调用 `cleanup()` 清理资源
4. **文件冲突**：多次写入同名文件会覆盖，注意文件名管理

## 迁移指南

### 旧代码
```python
agent = ProblemGenerationAgent()
result = agent.generate_problem(description)
# 忘记清理资源！
```

### 新代码
```python
# 推荐：使用上下文管理器
with ProblemGenerationAgent() as agent:
    result = agent.generate_problem(description)

# 或者：手动管理
agent = ProblemGenerationAgent()
try:
    result = agent.generate_problem(description)
finally:
    agent.close()
```

## 技术细节

### 容器配置
- **镜像**: python:3.10-slim
- **内存限制**: 512MB
- **CPU 配额**: 50000 微秒（50% CPU）
- **网络**: 禁用（安全隔离）
- **工作目录**: /workspace（挂载到宿主机临时目录）

### 文件存储
- **位置**: `/tmp/oj_sandbox_<random>/`
- **权限**: 读写（rw）
- **临时文件系统**: /tmp（100MB，noexec）

### 清理策略
- **容器**: force remove（强制删除）
- **目录**: shutil.rmtree（递归删除）
- **异常容错**: 清理失败不抛出异常，仅打印警告

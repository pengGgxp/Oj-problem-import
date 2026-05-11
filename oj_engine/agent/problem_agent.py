"""
Problem Generation Agent - ReAct Agent for OJ problem content generation

使用 ReAct (Reasoning + Acting) 模式,让 AI 自主决策:
- 何时生成代码
- 何时执行测试
- 何时重试或调整策略
"""
from langgraph.prebuilt import create_react_agent
from langchain_core.prompts import ChatPromptTemplate
from ..config import settings
from ..tools import (
    execute_code,
    write_code_file,
    read_file_content,
    edit_file_content,
    search_in_file,
    delete_file,
    save_outputs_to_host,
    set_global_sandbox_session,
)
from ..sandbox import SandboxSession


# ReAct System Prompt
REACT_SYSTEM_PROMPT = """你是一个专业的 OJ (Online Judge) 题目内容生成专家。

你的任务是根据题目描述,生成完整的测试数据包。

## 最终产物要求

**必须且仅需保留以下文件**:
1. `solution.py` - 标答代码 (Python)
2. `generator.py` - 数据生成器 (Python)
3. `tests/` 目录 - 包含成对的 `.in` 和 `.out` 文件
   - **第1组必须是题目中的样例输入输出** (如果题目提供了样例)
   - 其余测试数据由 generator 生成
   - 例如: `1.in`, `1.out` (样例), `2.in`, `2.out`, ..., `{n}.in`, `{n}.out`
   - **默认生成10组测试数据**，除非题目明确要求其他数量
   - **数据分布**: 30%小数据 + 50%中等数据 + 20%大数据/边缘情况

**重要**: 在调用 save_outputs_to_host 之前，必须使用 delete_file 工具删除所有其他临时文件！

## 工作流程

1. **分析阶段**: 仔细阅读题目要求,确定:
   - 算法类型 (排序、搜索、图论、动态规划等)
   - 数据范围 (n 的最大值、数值范围等)
   - 输入输出格式
   - **提取样例输入输出** (如果题目提供了样例)

2. **生成并保存标答**: 编写正确的 solution 代码 (必须使用 Python)
   - 确保算法正确性
   - 考虑边界情况
   - 优化时间复杂度
   - **使用 write_code_file 工具保存到 "solution.py"**

3. **生成并保存数据生成器**: 编写 generator 代码 (必须使用 Python)
   - 能够生成符合题目约束的随机数据
   - 支持生成不同规模的数据(小/中/大)
   - 确保生成的数据有效
   - **使用 write_code_file 工具保存到 "generator.py"**

4. **执行测试验证**: 使用 execute_code 工具验证标答
   - 构造简单测试用例验证正确性
   - 运行标答验证输出
   - 调整代码直到通过所有测试

5. **批量生成测试数据**: 
   - 创建 `tests/` 目录
   - **确定测试数据数量**:
     - 如果题目明确要求数量，使用题目要求的数量
     - 否则默认生成10组测试数据
   - **第1组: 使用题目中的样例** (如果有)
     a. 将样例输入保存为 `tests/1.in`
     b. 运行 solution 验证输出是否与样例输出一致
     c. 将样例输出保存为 `tests/1.out`
   - **第2-N组: 由 generator 生成** (N为总数量)
     a. 使用 generator 生成输入，保存为 `tests/{i}.in`
     b. 使用 solution 处理输入，保存输出为 `tests/{i}.out`
     c. 验证输出正确性
   - **确保数据分布**: 30%小数据 + 50%中等数据 + 20%大数据/边缘情况
     - 小数据: 边界值、特殊情况、最小规模
     - 中等数据: 常规规模、典型场景
     - 大数据/边缘: 最大规模、极端情况、最坏情况

6. **清理临时文件**: **关键步骤!**
   - 使用 delete_file 删除所有测试过程中创建的临时文件
   - 例如: `test_input.txt`, `test_output.txt`, `temp.py` 等
   - **只保留**: `solution.py`, `generator.py`, `tests/` 目录

7. **保存产物**: 调用 save_outputs_to_host 将最终产物复制到主机

## 可用工具

### 文件写入工具
- **write_code_file**: 将代码写入沙箱工作目录的文件 (优先使用!)
  用法: write_code_file(filename="solution.py", code="...")
  说明: 先调用此工具保存代码,后续只传文件路径

### 文件读取和编辑工具
- **read_file_content**: 读取沙箱中的文件内容（支持分页）
  用法: read_file_content(filename="solution.py", start_line=1, max_lines=100)
  说明: 用于查看已生成的代码或测试结果，大文件可分批读取

- **edit_file_content**: 编辑沙箱中的文件内容
  用法: edit_file_content(filename="solution.py", old_text="...", new_text="...", replace_all=False)
  说明: 精确替换文本，支持替换所有匹配项或仅第一个

- **search_in_file**: 在文件中搜索特定字符串
  用法: search_in_file(filename="solution.py", search_text="def main", case_sensitive=True)
  说明: 返回匹配位置和上下文，便于定位代码

- **delete_file**: 删除沙箱中的文件
  用法: delete_file(filename="temp.py")
  说明: 清理临时文件或不需要的文件

### 基础执行工具
- **execute_code**: 在沙箱中执行代码文件 (仅支持 Python)
  用法: execute_code(code_file="main.py", input_file="input.txt")
  注意: 只传文件路径,不传代码内容

### 产物保存工具
- **save_outputs_to_host**: 将沙箱中的所有文件复制到主机 outputs 目录
  用法: save_outputs_to_host(problem_title="A+B Problem")
  说明: 在工作完成后调用,自动复制所有生成的文件

## 思考原则

每次行动前,按照 ReAct 模式思考:

**Thought**: 分析当前状态,我需要做什么?
**Action**: 选择合适的工具
**Observation**: 查看工具返回的结果
**Next**: 根据结果决定下一步

## 重要提示

1. **语言限制**: 所有代码必须使用 Python,不允许使用 C++ 或其他语言
2. **文件优先**: 先生成代码并用 write_code_file 保存,后续只传文件路径
3. **避免重复传输代码**: 不要在参数中传递完整代码,这会浪费 token
4. **检查结果**: 每次执行后验证结果是否合理
5. **错误处理**: 如果失败,分析原因并调整策略
6. **样例优先**: **如果题目提供了样例输入输出，第1组测试数据必须是样例**
7. **数据数量**: **默认生成10组测试数据**，除非题目明确要求其他数量
8. **数据分布**: 确保测试数据符合 **30%小 + 50%中 + 20%大/边缘** 的分布
9. **代码质量**: 标答必须正确,generator 必须能生成有效数据
10. **产物清理**: **最关键!** 在保存前必须删除所有临时文件,只保留 solution.py, generator.py 和 tests/ 目录

## 示例流程

```
Thought: 我需要先理解题目要求,提取样例输入输出
Action: 分析题目描述
Observation: 题目提供了样例: 输入 "3 5", 输出 "8"。题目未明确要求测试数据数量，使用默认10组。

Thought: 生成标答代码并保存
Action: write_code_file(filename="solution.py", code="...")
Observation: {'success': True, 'filepath': 'solution.py', 'size': 150}

Thought: 现在需要生成数据生成器并保存
Action: write_code_file(filename="generator.py", code="...")
Observation: {'success': True, 'filepath': 'generator.py', 'size': 200}

Thought: 创建 tests 目录并将样例作为第1组测试数据
Action: write_code_file(filename="tests/1.in", code="3 5")
Observation: {'success': True, 'filepath': 'tests/1.in', 'size': 4}

Thought: 运行标答验证样例输出
Action: execute_code(code_file="solution.py", input_file="tests/1.in")
Observation: {'stdout': '8\n', 'exit_code': 0, 'status': 'success'}

Thought: 标答输出与样例一致,保存样例输出
Action: write_code_file(filename="tests/1.out", code="8")
Observation: {'success': True, 'filepath': 'tests/1.out', 'size': 1}

Thought: 现在生成其余9组测试数据 (2-10)，确保分布为 3小+5中+2大
Action: 循环执行 generator 和 solution,将结果保存到 tests/{i}.in 和 tests/{i}.out (i=2..10)
Observation: 生成了9组测试数据 (tests/2.in, tests/2.out, ..., tests/10.in, tests/10.out)

Thought: 检查后9组数据强度分布是否符合 30%小+50%中+20%大 的要求
Action: 分析输入数据的规模和特征
Observation: 分布为 small=30%, medium=50%, large=20%, 符合要求!

Thought: 清理临时文件,只保留必要文件
Action: delete_file(filename="test_input.txt")
Observation: {'success': True, 'message': 'File deleted: test_input.txt'}

Thought: 确认沙箱中只有 solution.py, generator.py 和 tests/ 目录
Action: 检查文件列表
Observation: 当前文件: solution.py, generator.py, tests/

Thought: 所有任务完成,保存产物到主机
Action: save_outputs_to_host(problem_title="A+B Problem")
Observation: {'success': True, 'output_path': 'outputs/20260510_123456_A_B_Problem', ...}

Thought: 所有任务完成
```

记住:你是专家,要确保生成的内容高质量且可用!
"""


class ProblemGenerationAgent:
    """
    OJ 题目生成 Agent
    
    使用 ReAct 模式自主决策和执行任务
    """
    
    def __init__(self, max_iterations: int = 20):
        """
        初始化 Agent
        
        Args:
            max_iterations: 最大迭代次数,防止无限循环
        """
        # 获取 LLM 客户端
        self.llm = settings.get_llm_client()
        
        # 创建持久化沙箱会话
        self.sandbox_session = SandboxSession()
        print("[Agent] Sandbox session created")
        
        # 设置全局沙箱会话(供工具使用)
        set_global_sandbox_session(self.sandbox_session)
        
        # 定义工具列表
        self.tools = [
            write_code_file,      # 写入代码文件
            read_file_content,    # 读取文件内容
            edit_file_content,    # 编辑文件内容
            search_in_file,       # 搜索文件内容
            delete_file,          # 删除文件
            execute_code,         # 执行代码
            save_outputs_to_host, # 保存产物到主机
        ]
        
        # 使用 LangGraph 创建 ReAct Agent (最简单的方式)
        self.agent_executor = create_react_agent(
            self.llm,
            self.tools,
            
        )
        
        print("[Agent] ProblemGenerationAgent initialized")
        print(f"  - Tools: {len(self.tools)}")
        print(f"  - Max iterations: {max_iterations}")
    
    def __enter__(self):
        """上下文管理器入口:初始化沙箱会话"""
        self.sandbox_session.initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口:清理沙箱会话"""
        self.sandbox_session.cleanup()
        print("[Agent] Sandbox session cleaned up")
        return False
    
    def close(self):
        """
        手动关闭 Agent,清理资源
        
        如果不使用上下文管理器,需要手动调用此方法
        """
        self.sandbox_session.cleanup()
        print("[Agent] Agent closed and resources cleaned up")
    
    def generate_problem(self, problem_description: str) -> dict:
        """
        主入口:根据题目描述生成完整产物
        
        Args:
            problem_description: 题目描述文本
            
        Returns:
            dict 包含 Agent 执行的完整结果
        """
        print("\n[Agent] Starting problem generation...")
        print(f"  Problem: {problem_description[:100]}...")
        
        # 构建完整的消息 (系统提示 + 任务指令)
        full_prompt = f"""{REACT_SYSTEM_PROMPT}

---

任务:为以下 OJ 题目生成完整的测试数据包

题目描述:
{problem_description}

要求:
1. 生成正确的标答代码 (solution) - **必须使用 Python**
2. 生成数据生成器 (generator) - **必须使用 Python**
3. 生成测试数据:
   - **第1组必须是题目中的样例输入输出** (如果题目提供了样例)
   - **测试数据数量**: 如果题目明确要求数量，使用题目要求的数量；否则默认生成10组
   - 其余测试数据由 generator 生成,保存为 tests/{{i}}.in 和 tests/{{i}}.out
4. 确保所有测试数据都能被标答正确处理
5. 确保测试数据强度分布符合要求: **30%小 + 50%中 + 20%大/边缘**

**重要约束**:
- 所有代码必须使用 Python 语言
- 不要生成 C++、Java 或其他语言的代码
- solution 和 generator 都必须是有效的 Python 代码
- **最终沙箱中只能有**: solution.py, generator.py, tests/ 目录
- **必须删除所有临时文件**后再调用 save_outputs_to_host

请逐步思考并执行,确保最终产物完整可用。

最后,请以 JSON 格式总结你的工作成果:
{{{{
  "solution_code": "...",
  "generator_code": "...",
  "test_cases_count": 10,
  "data_distribution": {{"small": 3, "medium": 5, "large": 2}},
  "message": "任务完成说明"
}}}}
"""
        
        # 执行 Agent
        try:
            result = self.agent_executor.invoke({
                "messages": [{"role": "user", "content": full_prompt}]
            })
            
            print("\n[Agent] Task completed!")
            return result
            
        except Exception as e:
            print(f"\n[Agent] Error: {str(e)}")
            raise
    
    def generate_problem_with_retry(self, problem_description: str, 
                                     max_retries: int = 2) -> dict:
        """
        带重试机制的问题生成
        
        Args:
            problem_description: 题目描述
            max_retries: 最大重试次数
            
        Returns:
            Agent 执行结果
        """
        last_error = None
        
        for attempt in range(1, max_retries + 1):
            try:
                print(f"\n[Agent] Attempt {attempt}/{max_retries}")
                result = self.generate_problem(problem_description)
                
                # 检查结果是否包含必要信息
                if "output" in result:
                    return result
                
            except Exception as e:
                last_error = e
                print(f"[Agent] Attempt {attempt} failed: {str(e)}")
                if attempt < max_retries:
                    print("[Agent] Retrying...")
        
        raise Exception(f"All {max_retries} attempts failed. Last error: {last_error}")

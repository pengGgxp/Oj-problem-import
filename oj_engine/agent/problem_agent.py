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
    supported_sandbox_languages,
    write_code_file,
    read_file_content,
    edit_file_content,
    search_in_file,
    delete_file,
    save_outputs_to_host,
    set_global_sandbox_session,
)
from ..sandbox import SandboxSession
from ..user_messages import format_user_friendly_error


# ReAct System Prompt
REACT_SYSTEM_PROMPT = """你是专业的 OJ (Online Judge) 题目测试数据包生成专家。

你的目标是根据题目描述和可选的官方题解/标程，生成一套可复现、可验证、强度合理的测试数据包。

## 产物要求

最终沙箱工作目录只保留这些内容：
1. `solution.<ext>` - 标答/官方题解代码，扩展名必须匹配实际语言。
2. `generator.py` - 测试数据生成器，统一使用 Python。
3. `tests/` - 成对的 `1.in`/`1.out`、`2.in`/`2.out` 等测试文件。

如果用户提供了官方题解，必须优先原样保存并使用它生成输出；只有在没有官方题解时，才自行编写标答。不要把非 Python 官方题解改写成 Python。

## 语言和沙箱

- `execute_code` 支持多语言沙箱，会根据 `language` 参数或文件扩展名选择 Docker 镜像。
- 标答执行时必须传入或确保能推断出正确语言，例如：
  - C++: `write_code_file(filename="solution.cpp", code=...)` 后调用 `execute_code(code_file="solution.cpp", input_file="tests/1.in", language="cpp")`
  - Java: `write_code_file(filename="solution.java", code=...)` 后调用 `execute_code(..., language="java")`
  - Python: `execute_code(code_file="solution.py", ..., language="python")`
- 生成器始终保存为 `generator.py` 并用 `execute_code(code_file="generator.py", language="python")` 运行。
- 如不确定支持哪些语言，先调用 `supported_sandbox_languages`。

## 工作流程

1. 分析题面：提取题名、输入输出格式、约束、样例和隐含边界。
2. 确定标答语言和文件名：
   - 用户显式给出语言时，使用该语言。
   - 未给出语言时，根据官方题解代码特征或文件扩展名判断。
   - 无官方题解时，默认写 Python 标答。
3. 保存标答到 `solution.<ext>`，保存生成器到 `generator.py`。
4. 验证样例：
   - 如果题面有样例，第 1 组必须使用题面样例。
   - 运行标答检查输出是否与样例输出一致；不一致时优先检查输入格式、题意或官方题解语言判断。
5. 生成测试：
   - 默认 10 组，除非题面明确要求其他数量。
   - 数据分布约为 30% 小数据 + 50% 中等数据 + 20% 大数据/边界/最坏情况。
   - 每组 `.out` 必须由标答实际运行得到，不要手写猜测。
6. 清理临时文件，只保留 `solution.<ext>`、`generator.py`、`tests/`。
7. 调用 `save_outputs_to_host` 保存产物。

## 质量要求

- 样例优先：有样例就必须放在 `tests/1.in` 和 `tests/1.out`。
- 输出可信：每个 `.out` 都必须来自标答沙箱运行结果。
- 数据有效：生成的数据必须满足所有输入约束，覆盖最小值、最大值、重复值、随机常规、结构性极端情况。
- 文件优先：代码先写入文件，后续工具调用只传文件路径，不在参数里反复传完整代码。
- 错误处理：编译失败或运行失败时，根据 stderr 修正语言、文件名或代码，再重新验证。

最后请用 JSON 总结：
{
  "solution_file": "solution.<ext>",
  "solution_language": "python/cpp/c/java/javascript/go/rust",
  "generator_file": "generator.py",
  "test_cases_count": 10,
  "data_distribution": {"small": 3, "medium": 5, "large": 2},
  "output_path": "...",
  "message": "任务完成说明"
}
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
        self.sandbox_session = SandboxSession(
            image=settings.docker.default_image,
            mem_limit=settings.docker.default_mem_limit,
            cpu_quota=settings.docker.default_cpu_quota,
            default_language=settings.docker.default_language,
            language_images=settings.docker.language_images,
        )
        print("[Agent] Sandbox session created")
        
        # 设置全局沙箱会话(供工具使用)
        set_global_sandbox_session(self.sandbox_session)
        
        # 定义工具列表
        self.tools = [
            supported_sandbox_languages,  # 查看支持语言
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
    
    def generate_problem(
        self,
        problem_description: str,
        base_path: str = "",
        official_solution: str = "",
        solution_language: str = "",
    ) -> dict:
        """
        主入口:根据题目描述生成完整产物
        
        Args:
            problem_description: 题目描述文本
            base_path: 基础路径（可选），用于保持目录结构。例如 "problems/easy"
            official_solution: 用户提供的官方题解/标程代码（可选）
            solution_language: 官方题解语言（可选，未提供时由 Agent 判断）
            
        Returns:
            dict 包含 Agent 执行的完整结果
        """
        print("\n[Agent] Starting problem generation...")
        print(f"  Problem: {problem_description[:100]}...")
        if base_path:
            print(f"  Base path: {base_path}")
        if official_solution:
            print(f"  Official solution: provided ({len(official_solution)} chars)")
        if solution_language:
            print(f"  Solution language: {solution_language}")
        
        # 构建完整的消息 (系统提示 + 任务指令)
        base_path_instruction = ""
        if base_path:
            base_path_instruction = f"""
**重要**: 调用 save_outputs_to_host 时，请使用 base_path 参数来保持目录结构：
```python
save_outputs_to_host(problem_title="{problem_description.split(chr(10))[0][:50]}", base_path="{base_path}")
```
这会将输出保存到: outputs/{base_path}/{{timestamp}}_{{title}}/
"""
        else:
            base_path_instruction = """
**重要**: 调用 save_outputs_to_host 时，**不要使用** base_path 参数，直接保存即可：
```python
save_outputs_to_host(problem_title="题目名称")
```
这会将输出保存到: outputs/{{timestamp}}_{{title}}/
"""

        official_solution_instruction = ""
        if official_solution:
            language_text = solution_language.strip() or "未指定，请根据代码特征判断"
            official_solution_instruction = f"""
用户提供了官方题解/标程，请优先使用它作为 `solution.<ext>`：
- 官方题解语言: {language_text}
- 保存时选择与语言匹配的文件名，例如 `solution.cpp`、`solution.java`、`solution.py`。
- 除非存在明显的编译入口问题（例如 Java 类名/文件名不匹配）或格式包装问题，不要改写算法逻辑。

官方题解代码:
```text
{official_solution}
```
"""
        else:
            official_solution_instruction = """
用户未提供官方题解/标程。请自行编写正确标答；默认使用 Python，除非题面或任务说明明确要求其他语言。
"""
        
        full_prompt = f"""{REACT_SYSTEM_PROMPT}

---

任务:为以下 OJ 题目生成完整的测试数据包

题目描述:
{problem_description}

{official_solution_instruction}

要求:
1. 生成或保存正确的标答代码 `solution.<ext>`，语言与官方题解一致；无官方题解时默认 Python
2. 生成数据生成器 `generator.py`，生成器必须使用 Python
3. 生成测试数据:
   - **第1组必须是题目中的样例输入输出** (如果题目提供了样例)
   - **测试数据数量**: 如果题目明确要求数量，使用题目要求的数量；否则默认生成10组
   - 其余测试数据由 generator 生成,保存为 tests/{{i}}.in 和 tests/{{i}}.out
4. 确保所有测试数据都能被标答正确处理
5. 确保测试数据强度分布符合要求: **30%小 + 50%中 + 20%大/边缘**

**重要约束**:
- `solution.<ext>` 必须使用正确语言运行。调用 execute_code 时显式传 `language`，或确保文件扩展名可推断
- `generator.py` 必须是有效的 Python 代码
- **最终沙箱中只能有**: solution.<ext>, generator.py, tests/ 目录
- **必须删除所有临时文件**后再调用 save_outputs_to_host
{base_path_instruction}
请逐步思考并执行,确保最终产物完整可用。

最后,请以 JSON 格式总结你的工作成果:
{{{{
  "solution_file": "solution.<ext>",
  "solution_language": "...",
  "generator_file": "generator.py",
  "test_cases_count": 10,
  "data_distribution": {{"small": 3, "medium": 5, "large": 2}},
  "output_path": "...",
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
            print(f"\n[Agent] Error: {format_user_friendly_error(e, action='生成题目')}")
            raise
    
    def generate_problem_with_retry(self, problem_description: str,
                                     max_retries: int = 2,
                                     base_path: str = "",
                                     official_solution: str = "",
                                     solution_language: str = "") -> dict:
        """
        带重试机制的问题生成
        
        Args:
            problem_description: 题目描述
            max_retries: 最大重试次数
            base_path: 基础路径（可选），用于保持目录结构
            official_solution: 用户提供的官方题解/标程代码（可选）
            solution_language: 官方题解语言（可选）
            
        Returns:
            Agent 执行结果
        """
        last_error = None
        
        for attempt in range(1, max_retries + 1):
            try:
                print(f"\n[Agent] Attempt {attempt}/{max_retries}")
                result = self.generate_problem(
                    problem_description,
                    base_path=base_path,
                    official_solution=official_solution,
                    solution_language=solution_language,
                )
                
                # 检查结果是否包含必要信息
                if "output" in result:
                    return result
                
            except Exception as e:
                last_error = e
                print(f"[Agent] Attempt {attempt} failed: {format_user_friendly_error(e, action='生成题目')}")
                if attempt < max_retries:
                    print("[Agent] Retrying...")
        
        raise Exception(f"All {max_retries} attempts failed. Last error: {last_error}")

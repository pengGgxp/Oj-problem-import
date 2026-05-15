"""
Problem Generation Agent - ReAct Agent for OJ problem content generation

使用 ReAct (Reasoning + Acting) 模式,让 AI 自主决策:
- 何时生成代码
- 何时执行测试
- 何时重试或调整策略
"""
import ast
import json
import warnings
from typing import Any, Iterable

warnings.filterwarnings(
    "ignore",
    message=r"The default value of `allowed_objects` will change in a future version.*",
)

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.errors import GraphRecursionError
from langgraph.prebuilt import create_react_agent
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

你的目标是根据用户传入的任务文件内容，生成一套可复现、可验证、强度合理的测试数据包。任务文件就是用户的完整提示词：其中可能包含题面、额外要求、参考代码、官方题解或指定语言，请整体理解后执行。

## 产物要求

最终沙箱工作目录只保留这些内容：
1. `solution.<ext>` - 标答/官方题解代码，扩展名必须匹配实际语言。
2. `generator.py` - 测试数据生成器，统一使用 Python。
3. `tests/` - 成对的 `1.in`/`1.out`、`2.in`/`2.out` 等测试文件。

如果任务文件中包含官方题解、参考代码或标程，必须优先识别并原样保存为 `solution.<ext>` 后使用它生成输出；只有任务文件未提供可用标程时，才自行编写标答。不要把非 Python 标程改写成 Python。

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
   - 任务文件显式指定语言时，使用该语言。
   - 未指定语言时，根据任务文件中的标程代码特征或文件名提示判断。
   - 无可用标程时，默认写 Python 标答，除非任务文件要求其他语言。
3. 保存标答到 `solution.<ext>`，保存生成器到 `generator.py`。
4. 验证样例：
   - 如果题面有样例，第 1 组必须使用题面样例。
   - 运行标答检查输出是否与样例输出一致；不一致时优先检查输入格式、题意或标程语言判断。
5. 生成测试：
   - 默认 10 组，除非题面明确要求其他数量。
   - 数据分布约为 30% 小数据 + 50% 中等数据 + 20% 大数据/边界/最坏情况。
   - 每组 `.out` 必须由标答实际运行得到，不要手写猜测。
6. 清理临时文件，只保留 `solution.<ext>`、`generator.py`、`tests/`。
7. 调用 `save_outputs_to_host` 保存产物。

## 可见思考输出

- 在关键阶段输出 1-2 句中文“可见思考摘要”，说明你当前的判断、风险点和下一步动作。
- 这些内容面向用户阅读，应该具体、有信息量，不要只复述工具名或参数。
- 不要输出隐藏推理链或冗长逐字推导；保留高层次的题意分析、数据策略、验证结论和修正原因即可。
- 在重要工具调用前，先用自然语言说明为什么要执行这一步；工具返回后，如结果影响后续方案，也要简短说明。

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
        self.max_iterations = max_iterations

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
        print(f"  - LangGraph recursion limit: {self._get_graph_recursion_limit()}")
    
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
    ) -> dict:
        """
        主入口:根据题目描述生成完整产物
        
        Args:
            problem_description: 任务文件内容/题目描述文本。用户可以在其中写入题面、生成要求、标程或语言要求。
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

        full_prompt = f"""{REACT_SYSTEM_PROMPT}

---

任务:根据以下任务文件内容生成完整的 OJ 测试数据包。请把任务文件视为用户提示词本身，而不是只把它当作题面；如果其中包含官方题解、标程、参考代码、语言要求或特殊生成要求，都要一并理解并执行。

任务文件内容:
{problem_description}

{official_solution_instruction}

要求:
1. 生成或保存正确的标答代码 `solution.<ext>`；如果任务文件包含标程/参考代码，优先原样使用并根据内容自动判断语言；否则默认生成 Python 标答，除非任务文件明确要求其他语言
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
请按阶段给出可见思考摘要并执行，确保最终产物完整可用。

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
            result = self._run_agent_with_visible_output(
                full_prompt,
                problem_description=problem_description,
            )
            
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

    def _run_agent_with_visible_output(self, full_prompt: str, problem_description: str = "") -> dict:
        """
        流式执行 Agent，并将模型产生的自然语言内容打印出来。

        ReAct Agent 的很多步骤会直接进入 tool_calls，终端上看起来只剩工具日志。
        这里保留工具执行能力，同时捕捉 AIMessage.content 里的“可见思考摘要”，
        让 CLI 和调用方可以看到 LLM 的阶段性判断。
        """
        input_state = {"messages": [{"role": "user", "content": full_prompt}]}
        config = {"recursion_limit": self._get_graph_recursion_limit()}
        printed_signatures = set()
        final_state = None

        try:
            for state in self.agent_executor.stream(
                input_state,
                config=config,
                stream_mode="values",
            ):
                final_state = state
                self._print_new_visible_messages(
                    state.get("messages", []),
                    printed_signatures,
                )
        except GraphRecursionError as exc:
            if final_state is not None:
                partial_result = self._attach_visible_output(
                    final_state,
                    problem_description=problem_description,
                )
                output_path = partial_result.get("output_path", "")
                if output_path:
                    partial_result["warning"] = str(exc)
                    print(
                        "\n[Agent] 已达到图步数上限，但检测到产物已保存，"
                        f"输出目录: {output_path}"
                    )
                    return partial_result

            raise RuntimeError(
                "Agent 执行达到图步数上限。当前 --max-iterations "
                f"为 {self.max_iterations}，对应 LangGraph recursion_limit "
                f"为 {config['recursion_limit']}。请使用更大的值重试，"
                "例如 `-m 80`；如果持续出现，说明模型可能在某一步反复调用工具。"
            ) from exc

        if final_state is None:
            final_state = self.agent_executor.invoke(input_state, config=config)
            self._print_new_visible_messages(
                final_state.get("messages", []),
                printed_signatures,
            )

        return self._attach_visible_output(final_state, problem_description=problem_description)

    def _get_graph_recursion_limit(self) -> int:
        """
        将面向用户的 max_iterations 换算成 LangGraph 节点步数。

        一次 ReAct 工具轮次通常至少包含 assistant/tool 两个图节点；
        生成 OJ 数据包还会批量写入 tests/*.in、tests/*.out 并多次验证，
        所以默认 20 轮需要明显高于 45 的图步数。
        """
        return self.get_graph_recursion_limit(self.max_iterations)

    @staticmethod
    def get_graph_recursion_limit(max_iterations: int) -> int:
        """根据用户配置的 Agent 迭代轮次计算 LangGraph 图步数上限。"""
        return max(120, max_iterations * 6)

    def _print_new_visible_messages(
        self,
        messages: Iterable[Any],
        printed_signatures: set,
    ) -> None:
        """打印尚未展示过的 AI 自然语言消息。"""
        for message in messages:
            if not self._is_ai_message(message):
                continue

            content = self._message_content_to_text(getattr(message, "content", "")).strip()
            if not content:
                continue

            signature = (
                getattr(message, "id", None)
                or (getattr(message, "type", ""), content)
            )
            if signature in printed_signatures:
                continue

            printed_signatures.add(signature)
            print("\n[AI 可见思考]")
            print(content)

    def _attach_visible_output(self, result: dict, problem_description: str = "") -> dict:
        """把 AI 可见思考和最终总结汇总到 result['output']。"""
        if not isinstance(result, dict):
            return {"output": self._message_content_to_text(result)}

        messages = result.get("messages", [])
        visible_messages = self._collect_visible_ai_text(messages)

        if visible_messages and self._has_visible_narrative(visible_messages):
            result["output"] = "\n\n".join(visible_messages)
        else:
            summary = self._generate_execution_summary(
                messages,
                problem_description=problem_description,
            )
            if summary:
                print("\n[AI 可见思考]")
                print(summary)
            output_parts = []
            if summary:
                output_parts.append(summary)
            if visible_messages:
                output_parts.append("原始结果:\n" + "\n\n".join(visible_messages))

            result["output"] = "\n\n".join(output_parts) or (
                "AI 本次没有返回可见思考文本，仅产生了工具调用消息。"
                "请检查模型是否支持在工具调用前返回文本，或调整提示词后重试。"
            )

        output_path = self._extract_output_path(messages)
        if output_path:
            result["output_path"] = output_path

        return result

    def _collect_visible_ai_text(self, messages: Iterable[Any]) -> list[str]:
        """提取所有 AIMessage 中面向用户的自然语言内容。"""
        visible_messages = []

        for message in messages:
            if not self._is_ai_message(message):
                continue

            content = self._message_content_to_text(getattr(message, "content", "")).strip()
            if content:
                visible_messages.append(content)

        return visible_messages

    def _has_visible_narrative(self, visible_messages: list[str]) -> bool:
        """判断可见消息里是否包含 JSON 之外的自然语言说明。"""
        return any(
            not self._looks_like_structured_payload(message)
            for message in visible_messages
        )

    def _looks_like_structured_payload(self, text: str) -> bool:
        stripped = text.strip()
        if not stripped:
            return True

        if stripped.startswith("```"):
            lines = stripped.splitlines()
            if len(lines) >= 3 and lines[-1].strip() == "```":
                stripped = "\n".join(lines[1:-1]).strip()

        return stripped.startswith("{") and stripped.endswith("}") and bool(
            self._parse_dict_from_text(stripped)
        )

    def _extract_output_path(self, messages: Iterable[Any]) -> str:
        """从 AI 最终总结或 save_outputs_to_host 的工具结果中提取 output_path。"""
        for message in reversed(list(messages)):
            if not (self._is_ai_message(message) or self._is_tool_message(message)):
                continue

            content = getattr(message, "content", "")
            for data in self._iter_content_dicts(content):
                output_path = data.get("output_path")
                if output_path:
                    return str(output_path)

            text = self._message_content_to_text(content)
            parsed = self._parse_dict_from_text(text)
            if parsed and parsed.get("output_path"):
                return str(parsed["output_path"])

        return ""

    @staticmethod
    def _is_ai_message(message: Any) -> bool:
        message_type = getattr(message, "type", "") or getattr(message, "role", "")
        return message_type == "ai" or message.__class__.__name__ == "AIMessage"

    @staticmethod
    def _is_tool_message(message: Any) -> bool:
        message_type = getattr(message, "type", "") or getattr(message, "role", "")
        return message_type == "tool" or message.__class__.__name__ == "ToolMessage"

    @classmethod
    def _message_content_to_text(cls, content: Any) -> str:
        """兼容 LangChain 文本、分块列表和 dict 形式的消息内容。"""
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        if isinstance(content, dict):
            return json.dumps(content, ensure_ascii=False)
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    text = item.get("text") or item.get("content")
                    if text:
                        parts.append(cls._message_content_to_text(text))
                else:
                    parts.append(str(item))
            return "\n".join(part for part in parts if part)
        return str(content)

    @classmethod
    def _iter_content_dicts(cls, content: Any) -> Iterable[dict]:
        if isinstance(content, dict):
            yield content
            return

        if isinstance(content, list):
            for item in content:
                yield from cls._iter_content_dicts(item)

    @staticmethod
    def _parse_dict_from_text(text: str) -> dict:
        if not text or "{" not in text or "}" not in text:
            return {}

        snippet = text[text.find("{"):text.rfind("}") + 1]
        for loader in (json.loads, ast.literal_eval):
            try:
                data = loader(snippet)
                if isinstance(data, dict):
                    return data
            except Exception:
                continue

        return {}

    def _generate_execution_summary(self, messages: Iterable[Any], problem_description: str = "") -> str:
        """
        基于执行记录生成一段可展示给用户的中文总结。

        这是可见输出的兜底层，避免整个流程只剩工具日志。
        """
        execution_log = self._build_execution_log(messages)
        summary_prompt = [
            SystemMessage(
                content=(
                    "你是一个执行总结助手。"
                    "请根据题目描述和执行记录，用中文输出 3-5 句简短总结。"
                    "只写高层思路和结果，不要泄露隐藏推理链，不要复述工具原文。"
                    "必须包含：题意判断、执行/验证状态、产物结果或遗留风险。"
                )
            ),
            HumanMessage(
                content=(
                    f"题目描述摘要:\n{problem_description[:1200] or '(未提供)'}\n\n"
                    f"执行记录摘要:\n{execution_log or '(无可用记录)'}\n\n"
                    "请输出一段可直接展示给用户的“可见思考与总结”。"
                )
            ),
        ]

        try:
            response = self.llm.invoke(summary_prompt)
            summary = self._message_content_to_text(getattr(response, "content", response)).strip()
            if summary:
                return summary
        except Exception as exc:
            print(f"[Agent] Summary generation skipped: {exc}")

        return ""

    def _build_execution_log(self, messages: Iterable[Any]) -> str:
        """把消息压缩成适合二次总结的简短执行日志。"""
        entries = []

        for message in messages:
            role = getattr(message, "type", "") or getattr(message, "role", "") or message.__class__.__name__
            if self._is_tool_message(message):
                role = getattr(message, "name", "") or "tool"
            elif self._is_ai_message(message):
                role = "assistant"
            else:
                role = role.lower()

            content = self._message_content_to_text(getattr(message, "content", "")).strip()
            if not content:
                continue

            if len(content) > 700:
                content = content[:700] + "..."

            entries.append(f"{role}: {content}")

        return "\n".join(entries[-20:])

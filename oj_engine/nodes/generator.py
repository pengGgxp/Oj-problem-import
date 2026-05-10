"""
Generator 节点 - 生成标答代码和数据生成器
"""
from langchain_core.prompts import ChatPromptTemplate
from ..state import GraphState, CodeArtifact
from ..config import settings


def generate_code_node(state: GraphState) -> GraphState:
    """
    生成标答代码和数据生成器
    
    Args:
        state: 当前工作流状态
        
    Returns:
        更新后的状态(包含生成的代码)
    """
    print(f"[Generator] 开始生成代码 (第 {state['retry_count'] + 1} 次尝试)...")
    
    requirements = state["requirements"]
    error_history = state.get("error_history", [])
    
    # 构建错误上下文(如果有之前的失败记录)
    error_context = ""
    if error_history:
        last_error = error_history[-1]
        error_context = f"""
之前尝试的代码执行失败,错误信息如下:
- 错误类型: {last_error.get('error_type', 'unknown')}
- 错误详情: {last_error.get('error', '')}

请分析错误原因并修复代码。
"""
    
    # 构建生成提示词
    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一个专业的算法竞赛选手和 OJ 题目专家。

任务:根据题目需求生成两份代码:
1. **标答代码(solution)**: 最优解法,需要高效且正确
2. **数据生成器(generator)**: Python 脚本,用于生成符合题目要求的测试数据

要求:
- 标答代码可以使用 C++ 或 Python
- 数据生成器必须使用 Python,利用 random 模块
- 数据生成器应该能生成各种边界情况和极端情况
- 代码必须完整可运行,不要省略任何部分
- 如果需要特殊判题器(SPJ),也请生成 checker.cpp

请以 JSON 格式返回:
```json
{{
  "solution_code": "...",
  "solution_language": "cpp" 或 "python",
  "generator_code": "...",
  "checker_code": "..." (可选)
}}
```"""),
        ("user", """题目需求:
- 时间限制: {time_limit}s
- 内存限制: {memory_limit}MB
- 输入格式: {input_format}
- 输出格式: {output_format}
- 变量范围: {variable_ranges}
- 约束条件: {constraints}

{error_context}

请生成完整的代码。""")
    ])
    
    # 初始化 LLM (使用配置)
    llm = settings.get_llm_client(model_type="generator")
    
    try:
        # 调用 LLM
        chain = prompt | llm
        response = chain.invoke({
            "time_limit": requirements.time_limit,
            "memory_limit": requirements.memory_limit,
            "input_format": requirements.input_format,
            "output_format": requirements.output_format,
            "variable_ranges": str(requirements.variable_ranges),
            "constraints": ", ".join(requirements.constraints),
            "error_context": error_context
        })
        
        # 解析响应
        content = response.content
        
        # 提取 JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        import json
        code_dict = json.loads(content)
        
        # 创建 CodeArtifact
        codes = CodeArtifact(
            solution_code=code_dict.get("solution_code", ""),
            solution_language=code_dict.get("solution_language", "python"),
            generator_code=code_dict.get("generator_code", ""),
            checker_code=code_dict.get("checker_code")
        )
        
        print(f"[Generator] 代码生成完成:")
        print(f"  - 标答语言: {codes.solution_language}")
        print(f"  - 标答长度: {len(codes.solution_code)} 字符")
        print(f"  - 生成器长度: {len(codes.generator_code)} 字符")
        
        # 更新状态
        state["codes"] = codes
        state["current_step"] = "executing"
        state["status"] = "executing"
        
    except Exception as e:
        print(f"[Generator] 代码生成失败: {str(e)}")
        # 保留之前的代码(如果有)
        state["current_step"] = "reflecting"
        state["status"] = "failed"
    
    return state

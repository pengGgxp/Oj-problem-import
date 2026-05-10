"""
Parser 节点 - 解析题目需求
"""
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from ..state import GraphState, ProblemRequirements
import json


def parse_problem_node(state: GraphState) -> GraphState:
    """
    解析题目描述,提取关键需求
    
    Args:
        state: 当前工作流状态
        
    Returns:
        更新后的状态(包含解析后的需求)
    """
    print("[Parser] 开始解析题目需求...")
    
    problem_description = state["problem_description"]
    
    # 构建解析提示词
    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一个专业的 OJ 题目分析师。请从题目描述中提取以下信息:

1. 时间限制(秒)
2. 内存限制(MB)
3. 输入格式描述
4. 输出格式描述
5. 变量范围约束(如 n <= 10^5)
6. 其他约束条件

请以 JSON 格式返回,字段如下:
- time_limit: float
- memory_limit: int
- input_format: string
- output_format: string
- variable_ranges: object (键值对)
- constraints: array of strings

如果某些信息不明确,使用合理的默认值。"""),
        ("user", "题目描述:\n{problem_description}")
    ])
    
    # 初始化 LLM (这里使用占位符,实际使用时需要配置 API key)
    llm = ChatOpenAI(model="gpt-4", temperature=0.1)
    
    try:
        # 调用 LLM
        chain = prompt | llm
        response = chain.invoke({"problem_description": problem_description})
        
        # 解析 JSON 响应
        content = response.content
        # 尝试提取 JSON (处理可能的 markdown 代码块)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        requirements_dict = json.loads(content)
        
        # 创建 ProblemRequirements 对象
        requirements = ProblemRequirements(
            time_limit=requirements_dict.get("time_limit", 1.0),
            memory_limit=requirements_dict.get("memory_limit", 256),
            input_format=requirements_dict.get("input_format", ""),
            output_format=requirements_dict.get("output_format", ""),
            variable_ranges=requirements_dict.get("variable_ranges", {}),
            constraints=requirements_dict.get("constraints", [])
        )
        
        print(f"[Parser] 解析完成:")
        print(f"  - 时间限制: {requirements.time_limit}s")
        print(f"  - 内存限制: {requirements.memory_limit}MB")
        print(f"  - 约束条件: {len(requirements.constraints)} 条")
        
        # 更新状态
        state["requirements"] = requirements
        state["current_step"] = "generating"
        state["status"] = "generating"
        
    except Exception as e:
        print(f"[Parser] 解析失败: {str(e)}")
        # 使用默认值
        state["requirements"] = ProblemRequirements()
        state["current_step"] = "generating"
        state["status"] = "generating"
    
    return state

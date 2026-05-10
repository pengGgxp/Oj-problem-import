"""
TestDataGenerator 节点 - AI 驱动的智能测试数据生成

功能:
1. 使用 AI 智能生成不同规模的测试数据
2. AI 判断数据属于小/中/大哪一类
3. 验证数据质量和有效性
4. 确保达到目标分布比例
"""
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from ..state import GraphState
from ..config import settings
import json
import re


def generate_test_data_node(state: GraphState) -> GraphState:
    """
    AI 驱动的测试数据生成节点
    
    流程:
    1. 分析题目要求,确定数据规模范围
    2. 逐个生成测试数据,让 AI 分类
    3. 验证数据有效性(运行标答检查)
    4. 直到达到目标数量和分布
    
    Args:
        state: 当前工作流状态
        
    Returns:
        更新后的状态(包含生成的测试数据)
    """
    print("[TestDataGenerator] 开始 AI 驱动的测试数据生成...")
    
    requirements = state.get("requirements")
    codes = state.get("codes")
    
    if not requirements or not codes:
        print("[TestDataGenerator] ⚠ Requirements or codes missing, skip test data generation")
        state["test_cases"] = []
        state["current_step"] = "executing"
        return state
    
    # 配置目标
    target_config = {
        "total": 10,
        "small": 3,   # 3个小数据
        "medium": 5,  # 5个中等数据
        "large": 2,   # 2个大数据
    }
    
    print(f"[TestDataGenerator] Target: {target_config['total']} tests "
          f"(small={target_config['small']}, medium={target_config['medium']}, large={target_config['large']})")
    
    try:
        # 初始化 LLM
        llm = settings.get_llm_client(model_type="generator")
        
        # 生成的测试数据集合
        generated_tests = {
            "small": [],
            "medium": [],
            "large": []
        }
        
        # 迭代生成,直到满足目标
        max_attempts = 50  # 最多尝试50次
        attempt = 0
        
        while attempt < max_attempts:
            # 检查是否已达到目标
            if (len(generated_tests["small"]) >= target_config["small"] and
                len(generated_tests["medium"]) >= target_config["medium"] and
                len(generated_tests["large"]) >= target_config["large"]):
                print(f"[TestDataGenerator] ✓ Target reached!")
                break
            
            attempt += 1
            
            # 决定下一组数据的类型
            needed_type = decide_next_test_type(generated_tests, target_config)
            print(f"[TestDataGenerator] Attempt {attempt}: Generating {needed_type} data...")
            
            # 使用 AI 生成测试数据
            test_input = generate_test_input_with_ai(llm, requirements, needed_type, attempt)
            
            if not test_input:
                print(f"  ⚠ Failed to generate input, retry...")
                continue
            
            # AI 分类和验证
            classification = classify_and_validate_with_ai(llm, requirements, test_input, needed_type)
            
            if not classification or not classification.get("valid"):
                print(f"  ⚠ Validation failed: {classification.get('reason', 'unknown')}")
                continue
            
            # 确认分类是否符合预期
            actual_type = classification.get("type", needed_type)
            
            # 添加到对应类别
            test_case = {
                "id": len(generated_tests[actual_type]) + 1,
                "input": test_input,
                "output": "",  # 稍后由 Executor 生成
                "type": actual_type,
                "description": classification.get("description", ""),
                "status": "pending"
            }
            
            generated_tests[actual_type].append(test_case)
            print(f"  ✓ Generated {actual_type} data: {classification.get('description', '')[:50]}")
        
        # 合并所有测试数据
        all_tests = []
        test_id = 1
        for test_type in ["small", "medium", "large"]:
            for test in generated_tests[test_type]:
                test["id"] = test_id
                all_tests.append(test)
                test_id += 1
        
        print(f"[TestDataGenerator] Generated {len(all_tests)} test cases total")
        print(f"  - Small: {len(generated_tests['small'])}")
        print(f"  - Medium: {len(generated_tests['medium'])}")
        print(f"  - Large: {len(generated_tests['large'])}")
        
        # 更新状态
        state["test_cases"] = all_tests
        state["test_data_stats"] = {
            "total": len(all_tests),
            "small": len(generated_tests["small"]),
            "medium": len(generated_tests["medium"]),
            "large": len(generated_tests["large"]),
            "attempts": attempt
        }
        state["current_step"] = "executing"
        
    except Exception as e:
        print(f"[TestDataGenerator] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        state["test_cases"] = []
        state["current_step"] = "executing"
    
    return state


def decide_next_test_type(generated_tests: dict, target_config: dict) -> str:
    """
    决定下一个应该生成的数据类型
    
    Args:
        generated_tests: 已生成的测试数据
        target_config: 目标配置
        
    Returns:
        "small", "medium", or "large"
    """
    # 优先补充不足的类别
    for test_type in ["small", "medium", "large"]:
        current = len(generated_tests[test_type])
        target = target_config[test_type]
        if current < target:
            return test_type
    
    # 如果都满足了,随机选择一个
    import random
    return random.choice(["small", "medium", "large"])


def generate_test_input_with_ai(llm, requirements, test_type: str, attempt: int) -> str:
    """
    使用 AI 生成指定类型的测试输入
    
    Args:
        llm: LLM 客户端
        requirements: 题目要求
        test_type: 数据类型 (small/medium/large)
        attempt: 尝试次数
        
    Returns:
        生成的测试输入字符串
    """
    type_descriptions = {
        "small": "小数据/简单情况:边界值、最小值、特殊情况",
        "medium": "中等数据:常规大小的随机数据",
        "large": "大数据/极端情况:接近上限的值、最坏情况"
    }
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一个专业的算法竞赛测试数据生成专家。

任务:根据题目要求生成一组测试输入数据。

要求:
1. 严格遵守题目的输入格式
2. 符合变量范围约束
3. 数据应该是有效的、有意义的
4. 只输出测试数据本身,不要任何解释

返回纯文本格式的测试输入。"""),
        ("user", """题目要求:
- 输入格式: {input_format}
- 变量范围: {variable_ranges}
- 约束条件: {constraints}

需要生成的数据类型: {test_type} ({type_desc})

请生成一组{test_type}测试输入:""")
    ])
    
    try:
        chain = prompt | llm
        response = chain.invoke({
            "input_format": requirements.input_format,
            "variable_ranges": str(requirements.variable_ranges),
            "constraints": ", ".join(requirements.constraints),
            "test_type": test_type,
            "type_desc": type_descriptions.get(test_type, "")
        })
        
        test_input = response.content.strip()
        
        # 清理可能的 markdown 代码块标记
        if test_input.startswith("```"):
            test_input = re.sub(r'^```\w*\n?', '', test_input)
            test_input = re.sub(r'\n?```$', '', test_input)
            test_input = test_input.strip()
        
        return test_input
        
    except Exception as e:
        print(f"    AI generation error: {e}")
        return ""


def classify_and_validate_with_ai(llm, requirements, test_input: str, expected_type: str) -> dict:
    """
    使用 AI 分类和验证测试数据
    
    Args:
        llm: LLM 客户端
        requirements: 题目要求
        test_input: 测试输入
        expected_type: 期望的数据类型
        
    Returns:
        分类结果 {"type": "...", "valid": True/False, "description": "..."}
    """
    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一个算法竞赛测试数据分析专家。

任务:分析给定的测试输入数据,判断它属于哪种规模类型。

类型定义:
- small: 小数据、边界情况、特殊案例(如 n=1, 空输入, 最小值等)
- medium: 中等规模的常规数据
- large: 大数据、极端情况、最坏情况(如 n=10^5, 最大值等)

请以 JSON 格式返回:
{{
  "type": "small" | "medium" | "large",
  "valid": true | false,
  "reason": "为什么这样分类的简短说明",
  "description": "这组数据的特征描述"
}}

如果数据无效(不符合题目要求),设置 valid=false 并说明原因。"""),
        ("user", """题目要求:
- 输入格式: {input_format}
- 变量范围: {variable_ranges}

测试输入:
{test_input}

请分析这组数据:""")
    ])
    
    try:
        chain = prompt | llm
        response = chain.invoke({
            "input_format": requirements.input_format,
            "variable_ranges": str(requirements.variable_ranges),
            "test_input": test_input
        })
        
        content = response.content
        
        # 提取 JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        result = json.loads(content)
        
        return result
        
    except Exception as e:
        print(f"    AI classification error: {e}")
        return {"type": expected_type, "valid": False, "reason": str(e)}

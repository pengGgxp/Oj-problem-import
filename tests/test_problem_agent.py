import inspect
import unittest

from oj_engine.agent.problem_agent import ProblemGenerationAgent


class ProblemGenerationAgentApiTests(unittest.TestCase):
    def test_generate_problem_uses_current_signature_without_stale_solution_args(self):
        signature = inspect.signature(ProblemGenerationAgent.generate_problem)

        self.assertNotIn("official_solution", signature.parameters)
        self.assertNotIn("solution_language", signature.parameters)

        captured = {}

        def fake_run(full_prompt, problem_description=""):
            captured["full_prompt"] = full_prompt
            captured["problem_description"] = problem_description
            return {"output": "ok"}

        agent = ProblemGenerationAgent.__new__(ProblemGenerationAgent)
        agent._run_agent_with_visible_output = fake_run

        result = agent.generate_problem("A+B Problem")

        self.assertEqual(result, {"output": "ok"})
        self.assertEqual(captured["problem_description"], "A+B Problem")
        self.assertIn("A+B Problem", captured["full_prompt"])

    def test_generate_problem_prompt_does_not_force_python_generator(self):
        captured = {}

        def fake_run(full_prompt, problem_description=""):
            captured["full_prompt"] = full_prompt
            return {"output": "ok"}

        agent = ProblemGenerationAgent.__new__(ProblemGenerationAgent)
        agent._run_agent_with_visible_output = fake_run

        agent.generate_problem("Need strong tests")

        full_prompt = captured["full_prompt"]
        self.assertIn("generator.<ext>", full_prompt)
        self.assertIn("默认推荐 Python，但不要强制", full_prompt)
        self.assertNotIn("生成器必须使用 Python", full_prompt)
        self.assertNotIn("`generator.py` 必须是有效的 Python 代码", full_prompt)
        self.assertNotIn("生成器始终保存为 `generator.py`", full_prompt)


if __name__ == "__main__":
    unittest.main()

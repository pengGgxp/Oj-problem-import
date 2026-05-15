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


if __name__ == "__main__":
    unittest.main()

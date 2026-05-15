import unittest
from unittest.mock import patch

from click.testing import CliRunner

from oj_engine import cli


class FakeProblemGenerationAgent:
    calls = []

    def __init__(self, max_iterations=20):
        self.max_iterations = max_iterations

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    @staticmethod
    def get_graph_recursion_limit(max_iterations):
        return max_iterations * 6

    def generate_problem(self, problem_description):
        self.calls.append(
            {
                "problem_description": problem_description,
                "max_iterations": self.max_iterations,
            }
        )
        return {"output": "generated"}


class CliGenerateTests(unittest.TestCase):
    def setUp(self):
        FakeProblemGenerationAgent.calls = []

    def test_generate_passes_only_problem_description_to_agent(self):
        runner = CliRunner()

        with (
            patch("oj_engine.cli.is_configured", return_value=True),
            patch("oj_engine.cli.ProblemGenerationAgent", FakeProblemGenerationAgent),
        ):
            result = runner.invoke(cli.main, ["generate", "-d", "A+B Problem", "-m", "3"])

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(
            FakeProblemGenerationAgent.calls,
            [
                {
                    "problem_description": "A+B Problem",
                    "max_iterations": 3,
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()

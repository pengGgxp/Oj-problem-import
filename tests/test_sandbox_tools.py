import unittest
from unittest.mock import patch

from oj_engine.tools import sandbox_tools


class FakeSession:
    def execute_code_file(self, code_file, input_file="", timeout=5, language=""):
        return {
            "stdout": "ok\n",
            "stderr": "",
            "exit_code": 0,
            "language": language or "python",
            "image": "python:3.10-slim",
            "command": f"python3 {code_file}",
        }


class SandboxToolTests(unittest.TestCase):
    def test_execute_code_does_not_return_time_or_memory_metrics_to_agent(self):
        with patch("oj_engine.tools.sandbox_tools.get_sandbox_session", return_value=FakeSession()):
            result = sandbox_tools.execute_code.invoke({
                "code_file": "solution.py",
                "language": "python",
            })

        self.assertEqual(result["status"], "success")
        self.assertNotIn("execution_time", result)
        self.assertNotIn("memory_usage", result)


if __name__ == "__main__":
    unittest.main()

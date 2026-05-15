from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from oj_engine.file_scanner import FileScanner
from oj_engine.user_messages import format_user_friendly_error


class UserMessageTests(unittest.TestCase):
    def test_docker_connection_error_is_user_friendly(self):
        message = format_user_friendly_error(
            RuntimeError(
                "Error while fetching server API version: "
                "(2, 'CreateFile', 'The system cannot find the file specified.') docker_engine"
            ),
            action="连接 Docker",
        )

        self.assertIn("Docker 环境不可用", message)
        self.assertIn("Docker Desktop", message)
        self.assertIn("docker ps", message)
        self.assertNotIn("CreateFile", message)

    def test_unsupported_language_message_keeps_supported_languages(self):
        message = format_user_friendly_error(
            ValueError("Unsupported language 'ruby'. Supported languages: c, cpp, go")
        )

        self.assertEqual(
            message,
            "不支持的语言: ruby。支持的语言: python, cpp, c, java, javascript, go, rust",
        )

    def test_file_scanner_missing_path_message_is_actionable(self):
        with TemporaryDirectory() as tmpdir:
            missing_path = Path(tmpdir) / "missing"

            with self.assertRaises(FileNotFoundError) as context:
                FileScanner.scan_input(missing_path)

            message = format_user_friendly_error(context.exception, action="扫描输入")

        self.assertIn("找不到路径", message)
        self.assertIn(str(missing_path), message)


if __name__ == "__main__":
    unittest.main()

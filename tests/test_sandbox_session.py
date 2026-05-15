import unittest
from pathlib import Path
from unittest.mock import patch

from oj_engine.sandbox import SandboxSession


class FakeExecResult:
    exit_code = 0
    output = (b"", b"")


class FakeContainer:
    def __init__(self, image):
        self.image = image
        self.short_id = image.replace(":", "_")
        self.remove_calls = 0

    def exec_run(self, *args, **kwargs):
        return FakeExecResult()

    def remove(self, force=False):
        self.remove_calls += 1


class FakeContainerManager:
    def __init__(self):
        self.run_calls = []
        self.created = []

    def run(self, **kwargs):
        container = FakeContainer(kwargs["image"])
        self.run_calls.append(kwargs)
        self.created.append(container)
        return container


class FakeDockerClient:
    def __init__(self):
        self.containers = FakeContainerManager()

    def ping(self):
        return True


class SandboxSessionTests(unittest.TestCase):
    def test_language_containers_share_workspace_and_live_until_cleanup(self):
        fake_client = FakeDockerClient()

        workspace = str(Path.cwd() / ".fake_sandbox_workspace")

        with patch("tempfile.mkdtemp", return_value=workspace):
            with patch("oj_engine.sandbox.shutil.rmtree") as mock_rmtree:
                session = SandboxSession()
                session.client = fake_client

                session.initialize("python")
                session.initialize("cpp")
                session.execute_command("true", language="python")

                self.assertEqual(len(fake_client.containers.run_calls), 2)
                mounted_paths = {
                    next(iter(call["volumes"].keys()))
                    for call in fake_client.containers.run_calls
                }
                self.assertEqual(mounted_paths, {workspace})
                self.assertTrue(
                    all(
                        call["volumes"][workspace] == {"bind": "/workspace", "mode": "rw"}
                        for call in fake_client.containers.run_calls
                    )
                )
                self.assertTrue(
                    all(container.remove_calls == 0 for container in fake_client.containers.created)
                )

                session.cleanup()

                mock_rmtree.assert_called_once_with(workspace, ignore_errors=True)
                self.assertTrue(
                    all(container.remove_calls == 1 for container in fake_client.containers.created)
                )


if __name__ == "__main__":
    unittest.main()

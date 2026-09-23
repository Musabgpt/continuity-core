import unittest
from pathlib import Path


class CiRunnerContractTests(unittest.TestCase):
    def test_workflow_uses_explicit_runner_image(self):
        workflow = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
        text = workflow.read_text(encoding="utf-8")
        self.assertIn("runs-on: ubuntu-24.04", text)
        self.assertNotIn("runs-on: ubuntu-latest", text)


if __name__ == "__main__":
    unittest.main()

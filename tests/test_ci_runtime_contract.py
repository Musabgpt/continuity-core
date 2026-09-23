import unittest
from pathlib import Path


class CiRuntimeContractTests(unittest.TestCase):
    def test_workflow_uses_explicit_python_runtime_and_known_action_majors(self):
        workflow = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
        text = workflow.read_text(encoding="utf-8")
        self.assertIn('python-version: "3.12"', text)
        self.assertIn("uses: actions/checkout@v4", text)
        self.assertIn("uses: actions/setup-python@v5", text)
        self.assertNotIn("python-version: ${{", text)
        self.assertNotIn("uses: actions/checkout@main", text)
        self.assertNotIn("uses: actions/setup-python@main", text)


if __name__ == "__main__":
    unittest.main()

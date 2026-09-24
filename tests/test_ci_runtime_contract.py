import unittest
from pathlib import Path


class CiRuntimeContractTests(unittest.TestCase):
    def test_workflow_uses_explicit_python_runtime_and_known_action_majors(self):
        workflow = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
        text = workflow.read_text(encoding="utf-8")
        self.assertIn('python-version: "3.12.8"', text)
        self.assertIn("uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683", text)
        self.assertIn("uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065", text)
        self.assertNotIn("python-version: ${{", text)
        self.assertNotIn("uses: actions/checkout@main", text)
        self.assertNotIn("uses: actions/setup-python@main", text)


if __name__ == "__main__":
    unittest.main()

import unittest
from pathlib import Path


class CiRuntimeContractTests(unittest.TestCase):
    def test_workflow_uses_explicit_python_runtime_and_node24_action_pins(self):
        workflow = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
        text = workflow.read_text(encoding="utf-8")
        self.assertIn('python-version: "3.12.8"', text)
        self.assertIn("uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803", text)
        self.assertIn("uses: actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1", text)
        self.assertNotIn("python-version: ${{", text)
        self.assertNotIn("uses: actions/checkout@main", text)
        self.assertNotIn("uses: actions/setup-python@main", text)


if __name__ == "__main__":
    unittest.main()

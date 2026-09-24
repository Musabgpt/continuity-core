import unittest
from pathlib import Path


class CiActionPinContractTests(unittest.TestCase):
    def test_workflow_pins_actions_to_immutable_node24_commit_shas_with_version_comments(self):
        workflow = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
        text = workflow.read_text(encoding="utf-8")
        self.assertIn(
            "uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803 # v6",
            text,
        )
        self.assertIn(
            "uses: actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1 # v6",
            text,
        )
        self.assertNotIn("uses: actions/checkout@v4", text)
        self.assertNotIn("uses: actions/setup-python@v5", text)
        self.assertNotIn("uses: actions/checkout@main", text)
        self.assertNotIn("uses: actions/setup-python@main", text)


if __name__ == "__main__":
    unittest.main()

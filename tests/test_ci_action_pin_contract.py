import unittest
from pathlib import Path


class CiActionPinContractTests(unittest.TestCase):
    def test_workflow_pins_actions_to_immutable_commit_shas_with_version_comments(self):
        workflow = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
        text = workflow.read_text(encoding="utf-8")
        self.assertIn(
            "uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2",
            text,
        )
        self.assertIn(
            "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065 # v5.6.0",
            text,
        )
        self.assertNotIn("uses: actions/checkout@v4", text)
        self.assertNotIn("uses: actions/setup-python@v5", text)
        self.assertNotIn("uses: actions/checkout@main", text)
        self.assertNotIn("uses: actions/setup-python@main", text)


if __name__ == "__main__":
    unittest.main()

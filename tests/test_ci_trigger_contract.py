import pathlib
import unittest


class CiTriggerContractTests(unittest.TestCase):
    def test_ci_triggers_on_push_and_pull_request_with_read_only_permissions(self):
        workflow = pathlib.Path(__file__).parents[1] / ".github" / "workflows" / "ci.yml"
        text = workflow.read_text(encoding="utf-8")
        self.assertIn("push:", text)
        self.assertIn("pull_request:", text)
        self.assertIn("permissions:\n  contents: read", text)

    def test_ci_has_no_write_capable_token_configuration(self):
        workflow = pathlib.Path(__file__).parents[1] / ".github" / "workflows" / "ci.yml"
        text = workflow.read_text(encoding="utf-8")
        self.assertNotIn("contents: write", text)
        self.assertNotIn("permissions: write-all", text)


if __name__ == "__main__":
    unittest.main()

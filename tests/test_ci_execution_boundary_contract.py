import unittest
from pathlib import Path


class CiExecutionBoundaryContractTests(unittest.TestCase):
    def test_workflow_serializes_runs_and_has_bounded_runtime(self):
        workflow = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
        text = workflow.read_text(encoding="utf-8")
        self.assertIn("concurrency:", text)
        self.assertIn("group: continuity-ci-${{ github.ref }}", text)
        self.assertIn("cancel-in-progress: false", text)
        self.assertIn("timeout-minutes: 10", text)
        self.assertNotIn("cancel-in-progress: true", text)


if __name__ == "__main__":
    unittest.main()

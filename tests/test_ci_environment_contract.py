import pathlib
import unittest


WORKFLOW = pathlib.Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"


class CiEnvironmentContractTests(unittest.TestCase):
    def test_workflow_pins_process_environment_for_deterministic_output(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        required = [
            "PYTHONHASHSEED: \"0\"",
            "TZ: UTC",
            "LC_ALL: C.UTF-8",
        ]
        for marker in required:
            self.assertIn(marker, text)
        self.assertNotIn("PYTHONHASHSEED: random", text)


if __name__ == "__main__":
    unittest.main()

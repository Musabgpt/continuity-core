import pathlib
import unittest


class CiContractTests(unittest.TestCase):
    def test_ci_runs_all_required_validation_commands(self):
        workflow = pathlib.Path(__file__).parents[1] / ".github" / "workflows" / "ci.yml"
        text = workflow.read_text(encoding="utf-8")
        required = [
            "python -m unittest discover -s tests -v",
            "python continuity.py validate",
            "python continuity_validate_json.py --root .",
            "python continuity_integrity.py --audit-all --root .",
        ]
        positions = []
        for command in required:
            self.assertIn(command, text)
            positions.append(text.index(command))
        self.assertEqual(positions, sorted(positions))

    def test_ci_workflow_is_standard_library_only(self):
        workflow = pathlib.Path(__file__).parents[1] / ".github" / "workflows" / "ci.yml"
        text = workflow.read_text(encoding="utf-8")
        self.assertNotIn("pytest", text)
        self.assertNotIn("pip install", text)


if __name__ == "__main__":
    unittest.main()

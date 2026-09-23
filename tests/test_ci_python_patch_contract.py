import unittest
from pathlib import Path


class CIPythonPatchContractTests(unittest.TestCase):
    def test_ci_uses_exact_python_patch_version(self):
        workflow = (Path(__file__).parents[1] / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertIn('python-version: "3.12.8"', workflow)
        self.assertNotIn('python-version: "3.12"', workflow)
        self.assertNotIn('python-version: 3.12', workflow)


if __name__ == "__main__":
    unittest.main()

import pathlib
import unittest


class CiShellContractTests(unittest.TestCase):
    def test_ci_uses_explicit_fail_closed_bash_shell(self):
        workflow = pathlib.Path('.github/workflows/ci.yml').read_text(encoding='utf-8')
        self.assertIn('defaults:\n  run:\n    shell: bash --noprofile --norc -euo pipefail {0}', workflow)
        self.assertNotIn('shell: bash\n', workflow)


if __name__ == '__main__':
    unittest.main()

import re
import unittest
from pathlib import Path


class CICheckoutCredentialsContractTests(unittest.TestCase):
    def test_checkout_disables_persisted_credentials(self):
        workflow = Path('.github/workflows/ci.yml').read_text(encoding='utf-8')
        self.assertRegex(
            workflow,
            r"uses:\s*actions/checkout@[0-9a-f]{40}\s*#\s*v[0-9][^\n]*\n\s*with:\s*\n\s*persist-credentials:\s*false\b",
        )
        self.assertNotRegex(workflow, r"persist-credentials:\s*true\b")


if __name__ == '__main__':
    unittest.main()

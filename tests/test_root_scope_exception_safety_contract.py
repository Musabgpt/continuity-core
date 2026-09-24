import unittest
from pathlib import Path
from unittest.mock import Mock

from continuity_root import isolated_root


class RootScopeExceptionSafetyTests(unittest.TestCase):
    def test_restore_runs_when_binding_raises_after_mutating_root(self):
        original = Path("/original").resolve()
        rebound = Path("/rebound").resolve()
        module = Mock()
        module.ROOT = original

        def configure_root(root):
            module.ROOT = Path(root)
            raise RuntimeError("simulated binding failure")

        module.configure_root.side_effect = configure_root

        with self.assertRaisesRegex(RuntimeError, "simulated binding failure"):
            with isolated_root(module, rebound):
                self.fail("scope body must not execute after binding failure")

        self.assertEqual(module.ROOT, original)
        self.assertEqual(module.configure_root.call_count, 2)
        self.assertEqual(module.configure_root.call_args_list[-1].args[0], original)


if __name__ == "__main__":
    unittest.main()

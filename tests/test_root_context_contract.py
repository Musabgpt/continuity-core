import tempfile
import unittest
from pathlib import Path

import continuity
from continuity_root import isolated_root


class RootContextContractTests(unittest.TestCase):
    def test_isolated_root_restores_after_success(self):
        original = continuity.ROOT
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "project"
            with isolated_root(continuity, target):
                self.assertEqual(continuity.ROOT, target.resolve())
            self.assertEqual(continuity.ROOT, original)

    def test_isolated_root_restores_after_exception(self):
        original = continuity.ROOT
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "project"
            with self.assertRaisesRegex(RuntimeError, "sentinel"):
                with isolated_root(continuity, target):
                    self.assertEqual(continuity.ROOT, target.resolve())
                    raise RuntimeError("sentinel")
            self.assertEqual(continuity.ROOT, original)

    def test_isolated_root_supports_nested_scopes(self):
        original = continuity.ROOT
        with tempfile.TemporaryDirectory() as temp_dir:
            outer = Path(temp_dir) / "outer"
            inner = Path(temp_dir) / "inner"
            with isolated_root(continuity, outer):
                self.assertEqual(continuity.ROOT, outer.resolve())
                with isolated_root(continuity, inner):
                    self.assertEqual(continuity.ROOT, inner.resolve())
                self.assertEqual(continuity.ROOT, outer.resolve())
            self.assertEqual(continuity.ROOT, original)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
import tempfile
import unittest
from pathlib import Path

import continuity


class RootPathContractTests(unittest.TestCase):
    def test_configure_root_canonicalizes_relative_root_and_derives_all_paths(self):
        previous = continuity.ROOT
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "project"
            root.mkdir()
            relative = root.relative_to(Path.cwd()) if root.is_relative_to(Path.cwd()) else root
            try:
                continuity.configure_root(relative)
                self.assertEqual(continuity.ROOT, root.resolve())
                self.assertEqual(continuity.DIR, root.resolve() / "continuity")
                self.assertEqual(continuity.STATE, root.resolve() / "continuity" / "state.json")
                self.assertEqual(continuity.EVENTS, root.resolve() / "continuity" / "events.jsonl")
                self.assertEqual(continuity.TXN, root.resolve() / "continuity" / "transaction.json")
                self.assertEqual(continuity.LOCK, root.resolve() / "continuity" / ".lock")
            finally:
                continuity.configure_root(previous)


if __name__ == "__main__":
    unittest.main()

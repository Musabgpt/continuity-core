import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import continuity
from continuity_readonly import snapshot

SOURCE = Path(__file__).resolve().parents[1] / "continuity.py"
INTEGRITY_SOURCE = Path(__file__).resolve().parents[1] / "continuity_integrity.py"


class ReadonlyIntegrityTests(unittest.TestCase):
    def run_cli(self, root, *args):
        script = root / "continuity.py"
        return subprocess.run([sys.executable, str(script), *args], text=True, capture_output=True)

    def setup_cli(self, root):
        root.joinpath("continuity.py").write_text(SOURCE.read_text(encoding="utf-8"), encoding="utf-8")
        shutil.copy2(INTEGRITY_SOURCE, root / "continuity_integrity.py")

    def test_snapshot_refuses_hash_chain_corruption(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_cli(root)
            self.assertEqual(self.run_cli(root, "init", "--project", "A", "--goal", "B").returncode, 0)
            self.assertEqual(self.run_cli(root, "event", "note", "one").returncode, 0)
            path = root / "continuity/events.jsonl"
            rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]
            rows[-1]["chain_hash"] = "0" * 64
            path.write_text("\n".join(json.dumps(row, separators=(",", ":")) for row in rows) + "\n", encoding="utf-8")
            first = snapshot(root)
            second = snapshot(root)
            expected = {
                "schema_version": 1,
                "valid": False,
                "error": "continuity integrity invalid",
                "integrity": {"scope": "events", "line": 2, "reason": "event hash mismatch"},
            }
            self.assertEqual(first, expected)
            self.assertEqual(second, expected)

    def test_snapshot_preserves_valid_read_only_contract(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_cli(root)
            self.assertEqual(self.run_cli(root, "init", "--project", "A", "--goal", "B").returncode, 0)
            self.assertEqual(self.run_cli(root, "event", "note", "one").returncode, 0)
            result = snapshot(root)
            self.assertTrue(result["valid"])
            self.assertEqual(result["state"]["project"], "A")
            self.assertEqual(result["state"]["goal"], "B")
            self.assertEqual(result["event_count"], 2)
            self.assertFalse(result["pending_transaction"])


if __name__ == "__main__":
    unittest.main()

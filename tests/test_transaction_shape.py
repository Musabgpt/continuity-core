import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TransactionShapeTests(unittest.TestCase):
    def test_recovery_rejects_shape_before_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "continuity").mkdir()
            (root / "continuity.py").write_text((ROOT / "continuity.py").read_text(encoding="utf-8"), encoding="utf-8")
            shutil.copyfile(ROOT / "continuity_integrity.py", root / "continuity_integrity.py")
            init = subprocess.run(
                [sys.executable, str(root / "continuity.py"), "init", "--project", "A", "--goal", "B"],
                text=True, capture_output=True, cwd=root,
            )
            self.assertEqual(init.returncode, 0, init.stderr)
            state = root / "continuity" / "state.json"
            events = root / "continuity" / "events.jsonl"
            before_state = state.read_text(encoding="utf-8")
            before_events = events.read_text(encoding="utf-8")
            (root / "continuity" / "transaction.json").write_text(
                json.dumps({"txid": 7, "state": {}, "event": {"type": "note", "message": "x"}, "checksum": "ignored"}) + "\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(root / "continuity.py"), "handoff", "--format", "json"],
                text=True, capture_output=True, cwd=root,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Transaction journal shape invalid: txid must be str.", result.stderr + result.stdout)
            self.assertEqual(state.read_text(encoding="utf-8"), before_state)
            self.assertEqual(events.read_text(encoding="utf-8"), before_events)

    def test_integrity_reports_shape_deterministically(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "continuity").mkdir()
            verifier = ROOT / "continuity_integrity.py"
            (root / "continuity_integrity.py").write_text(verifier.read_text(encoding="utf-8"), encoding="utf-8")
            (root / "continuity" / "transaction.json").write_text(
                json.dumps({"checksum": "x", "txid": 7, "state": {}, "event": {}}) + "\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(root / "continuity_integrity.py"), "--audit-transaction", "--root", str(root)],
                text=True, capture_output=True,
            )
            self.assertNotEqual(result.returncode, 0)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["first_break"]["reason"], "transaction journal shape invalid: txid must be str")


if __name__ == "__main__":
    unittest.main()

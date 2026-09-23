import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "continuity.py"
INTEGRITY = ROOT / "continuity_integrity.py"


class RecoveryBoundaryTests(unittest.TestCase):
    def run_cli(self, root, *args):
        return subprocess.run(
            [sys.executable, str(root / "continuity.py"), *args],
            text=True,
            capture_output=True,
            cwd=root,
        )

    def test_malformed_transaction_is_fail_closed_without_state_or_event_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            shutil.copyfile(SOURCE, root / "continuity.py")
            shutil.copyfile(INTEGRITY, root / "continuity_integrity.py")
            self.assertEqual(
                self.run_cli(root, "init", "--project", "A", "--goal", "B").returncode,
                0,
            )
            state = root / "continuity" / "state.json"
            events = root / "continuity" / "events.jsonl"
            before_state = state.read_text(encoding="utf-8")
            before_events = events.read_text(encoding="utf-8")
            (root / "continuity" / "transaction.json").write_text(
                json.dumps({"checksum": 3}) + "\n", encoding="utf-8"
            )

            result = self.run_cli(root, "handoff", "--format", "json")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Transaction journal shape invalid", result.stderr + result.stdout)
            self.assertEqual(state.read_text(encoding="utf-8"), before_state)
            self.assertEqual(events.read_text(encoding="utf-8"), before_events)


if __name__ == "__main__":
    unittest.main()

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class HandoffReadOnlyTests(unittest.TestCase):
    def run_handoff(self, project):
        shutil.copy2(ROOT / "continuity.py", project / "continuity.py")
        shutil.copy2(ROOT / "continuity_integrity.py", project / "continuity_integrity.py")
        return subprocess.run(
            [sys.executable, "continuity.py", "handoff", "--format", "json"],
            cwd=project,
            text=True,
            capture_output=True,
        )

    def test_pending_transaction_is_rejected_without_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            continuity = project / "continuity"
            continuity.mkdir()
            state = {
                "schema_version": 2,
                "project": "demo",
                "goal": "test",
                "status": "active",
                "constraints": [],
                "decisions": [],
                "next_action": "recover",
                "updated_at": "2026-01-01T00:00:00Z",
                "revision": 1,
            }
            (continuity / "state.json").write_text(json.dumps(state) + "\n", encoding="utf-8")
            (continuity / "events.jsonl").write_text(
                '{"type":"success","message":"ok"}\n', encoding="utf-8"
            )
            txn = {
                "txid": "tx-1",
                "state": dict(state, revision=2),
                "event": {"type": "note", "message": "pending"},
            }
            txn_path = continuity / "transaction.json"
            txn_path.write_text(json.dumps(txn) + "\n", encoding="utf-8")
            before = {
                path.name: path.read_bytes()
                for path in (continuity / "state.json", continuity / "events.jsonl", txn_path)
            }

            result = self.run_handoff(project)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Pending transaction journal", result.stderr + result.stdout)
            for path in (continuity / "state.json", continuity / "events.jsonl", txn_path):
                self.assertEqual(before[path.name], path.read_bytes())


if __name__ == "__main__":
    unittest.main()

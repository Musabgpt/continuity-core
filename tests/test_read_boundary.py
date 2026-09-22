import json
import tempfile
import unittest
from pathlib import Path

import continuity


class ReadBoundaryTests(unittest.TestCase):
    def test_read_events_does_not_recover_pending_transaction(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            continuity.configure_root(project)
            directory = project / "continuity"
            directory.mkdir()
            (directory / "events.jsonl").write_text('{"type":"success","message":"ok"}\n', encoding="utf-8")
            (directory / "transaction.json").write_text(
                json.dumps({
                    "txid": "tx-1",
                    "state": {"schema_version": 2},
                    "event": {"type": "note", "message": "pending"},
                }) + "\n",
                encoding="utf-8",
            )

            rows = continuity.read_events_unlocked()

            self.assertEqual(rows[0]["message"], "ok")
            self.assertTrue((directory / "transaction.json").exists())
            self.assertEqual((directory / "events.jsonl").read_text(encoding="utf-8"), '{"type":"success","message":"ok"}\n')


if __name__ == "__main__":
    unittest.main()

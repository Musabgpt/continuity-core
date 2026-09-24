import json
import tempfile
import unittest
from pathlib import Path

import continuity


class HandoffDeterminismContractTests(unittest.TestCase):
    def test_handoff_json_excludes_volatile_and_transaction_fields(self):
        original_root = continuity.ROOT
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                directory = root / "continuity"
                directory.mkdir()
                (directory / "state.json").write_text(
                    json.dumps(
                        {
                            "schema_version": 2,
                            "project": "demo",
                            "goal": "deterministic continuity",
                            "status": "active",
                            "constraints": ["standard library"],
                            "decisions": ["prefer evidence"],
                            "next_action": "verify",
                            "revision": 7,
                            "updated_at": "2026-01-01T00:00:00Z",
                        },
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )
                (directory / "events.jsonl").write_text(
                    '{"ts":"2026-01-01T00:00:00Z","type":"success","message":"ok","txid":"volatile-tx"}\n',
                    encoding="utf-8",
                )

                continuity.configure_root(root)
                first = continuity.handoff_payload()
                first_json = continuity.canonical(first)

                (directory / "state.json").write_text(
                    json.dumps(
                        {
                            "schema_version": 2,
                            "project": "demo",
                            "goal": "deterministic continuity",
                            "status": "active",
                            "constraints": ["standard library"],
                            "decisions": ["prefer evidence"],
                            "next_action": "verify",
                            "revision": 7,
                            "updated_at": "2030-12-31T23:59:59Z",
                        },
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )
                (directory / "events.jsonl").write_text(
                    '{"ts":"2030-12-31T23:59:59Z","type":"success","message":"ok","txid":"different-tx"}\n',
                    encoding="utf-8",
                )
                second = continuity.handoff_payload()
                second_json = continuity.canonical(second)

                self.assertEqual(first_json, second_json)
                self.assertNotIn("updated_at", first)
                handoff_keys = set(first)
                self.assertNotIn("ts", handoff_keys)
                self.assertNotIn("txid", handoff_keys)
                self.assertNotIn("updated_at", handoff_keys)
                self.assertEqual(
                    first_json,
                    '{"constraints":["standard library"],"decisions":["prefer evidence"],"goal":"deterministic continuity","next_action":"verify","project":"demo","recent_failures":[],"revision":7,"schema_version":2,"status":"active"}',
                )
        finally:
            continuity.configure_root(original_root)


if __name__ == "__main__":
    unittest.main()

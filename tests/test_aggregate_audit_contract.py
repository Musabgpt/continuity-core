import tempfile
import unittest
from pathlib import Path

from continuity_integrity import audit_all, canonical, digest


class AggregateAuditContractTests(unittest.TestCase):
    def _write_valid_state(self, root):
        continuity = root / "continuity"
        state = {
            "schema_version": 2,
            "project": "A",
            "goal": "B",
            "status": "active",
            "constraints": ["c"],
            "decisions": ["d"],
            "next_action": None,
            "updated_at": "2026-09-25T00:00:00Z",
            "revision": 1,
        }
        (continuity / "state.json").write_text(canonical(state) + "\n", encoding="utf-8")

    def test_aggregate_audit_is_stable_and_selects_events_before_transaction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            continuity = root / "continuity"
            continuity.mkdir()
            self._write_valid_state(root)
            event = {"type": "set_next", "next_action": "x", "prev_hash": "GENESIS"}
            event["chain_hash"] = digest(event)
            (continuity / "events.jsonl").write_text(canonical(event) + "\n", encoding="utf-8")
            tx = {"txid": "tx-1", "state": {"revision": 1}, "event": {"type": "set_next"}}
            tx["checksum"] = "0" * 64
            (continuity / "transaction.json").write_text(canonical(tx), encoding="utf-8")

            result = audit_all(root)

            self.assertFalse(result["valid"])
            self.assertEqual(result["first_break"]["scope"], "transaction")
            self.assertEqual(result["first_break"]["line"], 1)
            self.assertEqual(result["first_break"]["reason"], "transaction journal checksum mismatch")
            self.assertEqual(list(result), ["schema_version", "valid", "first_break", "state", "events", "transaction"])

    def test_valid_aggregate_has_no_first_break_and_preserves_domain_diagnostics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            continuity = root / "continuity"
            continuity.mkdir()
            self._write_valid_state(root)
            event = {"type": "set_next", "next_action": "x", "prev_hash": "GENESIS"}
            event["chain_hash"] = digest(event)
            (continuity / "events.jsonl").write_text(canonical(event) + "\n", encoding="utf-8")

            result = audit_all(root)

            self.assertTrue(result["valid"])
            self.assertIsNone(result["first_break"])
            self.assertEqual(result["state"]["schema_version"], 1)
            self.assertEqual(result["events"]["schema_version"], 1)
            self.assertEqual(result["transaction"]["schema_version"], 1)


if __name__ == "__main__":
    unittest.main()

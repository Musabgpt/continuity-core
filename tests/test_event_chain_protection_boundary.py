import json
import tempfile
import unittest
from pathlib import Path

from continuity_integrity import audit_events, digest


class EventChainProtectionBoundaryTests(unittest.TestCase):
    def _protected(self, payload, previous):
        row = {"type": "note", "message": payload, "prev_hash": previous}
        row["chain_hash"] = digest(row)
        return row

    def test_unprotected_record_after_chain_start_is_rejected(self):
        first = self._protected("first", "GENESIS")
        injected = {"type": "note", "message": "unprotected insertion"}
        second = self._protected("second", first["chain_hash"])

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            path.write_text(
                "\n".join(json.dumps(row, separators=(",", ":")) for row in (first, injected, second)) + "\n",
                encoding="utf-8",
            )
            result = audit_events(path)

        self.assertFalse(result["valid"])
        self.assertEqual(result["checked"], 2)
        self.assertEqual(result["first_break"], {"line": 2, "reason": "event chain protection missing"})

    def test_legacy_unprotected_prefix_can_transition_to_protected_chain(self):
        legacy = {"type": "note", "message": "legacy"}
        first = self._protected("first", "GENESIS")

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            path.write_text(
                "\n".join(json.dumps(row, separators=(",", ":")) for row in (legacy, first)) + "\n",
                encoding="utf-8",
            )
            result = audit_events(path)

        self.assertTrue(result["valid"])
        self.assertEqual(result["checked"], 2)
        self.assertIsNone(result["first_break"])


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from continuity_integrity import audit_events, audit_transaction


class AuditReadFailureContractTests(unittest.TestCase):
    def test_event_audit_contains_invalid_utf8_with_stable_diagnostic(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            path.write_bytes(b"{\xff}\n")

            result = audit_events(path)

            self.assertFalse(result["valid"])
            self.assertEqual(result["checked"], 0)
            self.assertEqual(result["first_break"], {"line": 1, "reason": "events file encoding is invalid"})

    def test_transaction_audit_contains_invalid_utf8_with_stable_diagnostic(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "transaction.json"
            path.write_bytes(b"{\xff}")

            result = audit_transaction(path)

            self.assertFalse(result["valid"])
            self.assertEqual(result["checked"], 0)
            self.assertEqual(result["first_break"], {"line": 1, "reason": "transaction file encoding is invalid"})

    def test_event_audit_contains_os_read_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            path.write_text("{}\n", encoding="utf-8")
            with mock.patch.object(Path, "read_text", side_effect=OSError("host-specific")):
                result = audit_events(path)

            self.assertFalse(result["valid"])
            self.assertEqual(result["checked"], 0)
            self.assertEqual(result["first_break"], {"line": None, "reason": "events file could not be read"})

    def test_transaction_audit_contains_os_read_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "transaction.json"
            path.write_text("{}", encoding="utf-8")
            with mock.patch.object(Path, "read_text", side_effect=OSError("host-specific")):
                result = audit_transaction(path)

            self.assertFalse(result["valid"])
            self.assertEqual(result["checked"], 0)
            self.assertEqual(result["first_break"], {"line": None, "reason": "transaction file could not be read"})


if __name__ == "__main__":
    unittest.main()

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class ChecksumContractTests(unittest.TestCase):
    def run_audit(self, tx):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "continuity").mkdir()
            (root / "continuity" / "transaction.json").write_text(json.dumps(tx) + "\n", encoding="utf-8")
            before = (root / "continuity" / "transaction.json").read_bytes()
            proc = subprocess.run(
                [sys.executable, str(ROOT / "continuity_integrity.py"), "--audit-transaction", "--root", str(root)],
                capture_output=True, text=True, check=False,
            )
            after = (root / "continuity" / "transaction.json").read_bytes()
            return proc, json.loads(proc.stdout), before, after

    def test_non_string_checksum_has_stable_diagnostic_and_no_mutation(self):
        proc, result, before, after = self.run_audit({"txid": "t", "state": {}, "event": {}, "checksum": 7})
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(result["first_break"]["reason"], "transaction journal checksum invalid: checksum must be a string")
        self.assertEqual(before, after)

    def test_bad_checksum_format_has_stable_diagnostic_and_no_mutation(self):
        proc, result, before, after = self.run_audit({"txid": "t", "state": {}, "event": {}, "checksum": "ABC"})
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(result["first_break"]["reason"], "transaction journal checksum invalid: checksum must be 64 lowercase hex characters")
        self.assertEqual(before, after)

if __name__ == "__main__":
    unittest.main()

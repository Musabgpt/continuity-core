import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "continuity_integrity.py"


class LegacyTransactionShapeTests(unittest.TestCase):
    def run_audit(self, root):
        return subprocess.run(
            [sys.executable, str(root / "continuity_integrity.py"), "--root", str(root), "--audit-transaction"],
            text=True,
            capture_output=True,
        )

    def test_legacy_transaction_without_checksum_still_requires_shape(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            target = root / "continuity_integrity.py"
            target.write_text(SOURCE.read_text(encoding="utf-8"), encoding="utf-8")
            continuity = root / "continuity"
            continuity.mkdir()
            (continuity / "transaction.json").write_text(
                json.dumps({"checksum": None}) + "\n", encoding="utf-8"
            )

            result = self.run_audit(root)

            self.assertEqual(result.returncode, 1)
            payload = json.loads(result.stdout)
            self.assertFalse(payload["valid"])
            self.assertEqual(
                payload["first_break"]["reason"],
                "transaction journal shape invalid: txid must be str",
            )


if __name__ == "__main__":
    unittest.main()

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ValidateIntegrityBridgeTests(unittest.TestCase):
    def test_validate_fails_closed_on_tampered_protected_event_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            shutil.copy2(ROOT / "continuity.py", project / "continuity.py")
            shutil.copy2(ROOT / "continuity_integrity.py", project / "continuity_integrity.py")
            continuity = project / "continuity"
            continuity.mkdir()
            (continuity / "state.json").write_text(json.dumps({
                "schema_version": 2,
                "project": "Test",
                "goal": "Bridge",
                "status": "active",
                "constraints": [],
                "decisions": [],
                "next_action": None,
                "revision": 0,
                "updated_at": "2026-09-22T00:00:00Z",
            }) + "\n", encoding="utf-8")
            (continuity / "events.jsonl").write_text(
                json.dumps({"type": "success", "message": "tampered", "prev_hash": "GENESIS", "chain_hash": "0" * 64}) + "\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, "continuity.py", "validate"],
                cwd=project,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("integrity audit failed: events line 1: event hash mismatch", result.stdout)


if __name__ == "__main__":
    unittest.main()

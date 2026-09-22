import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ValidateJsonEntrypointTests(unittest.TestCase):
    def test_valid_project_emits_stable_json_and_zero_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "continuity").mkdir()
            (project / "continuity" / "state.json").write_text(
                json.dumps({
                    "schema_version": 2,
                    "project": "demo",
                    "goal": "test",
                    "status": "active",
                    "constraints": [],
                    "decisions": [],
                    "next_action": None,
                    "updated_at": "2026-01-01T00:00:00Z",
                    "revision": 0,
                }) + "\n",
                encoding="utf-8",
            )
            (project / "continuity" / "events.jsonl").write_text(
                '{"type":"success","message":"ok"}\n', encoding="utf-8"
            )
            script = ROOT / "continuity_validate_json.py"
            result = subprocess.run(
                [sys.executable, str(script)], cwd=project, text=True, capture_output=True
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(
                list(payload), ["errors", "integrity", "schema_version", "valid"]
            )
            self.assertTrue(payload["valid"])
            self.assertEqual(payload["schema_version"], 1)


if __name__ == "__main__":
    unittest.main()

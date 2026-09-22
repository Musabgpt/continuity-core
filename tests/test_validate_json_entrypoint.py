import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ValidateJsonEntrypointTests(unittest.TestCase):
    def make_project(self, tmp, state):
        project = Path(tmp)
        (project / "continuity").mkdir()
        (project / "continuity" / "state.json").write_text(
            json.dumps(state) + "\n", encoding="utf-8"
        )
        (project / "continuity" / "events.jsonl").write_text(
            '{"type":"success","message":"ok"}\n', encoding="utf-8"
        )
        return project

    def test_valid_project_emits_stable_json_and_zero_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = self.make_project(tmp, {
                "schema_version": 2,
                "project": "demo",
                "goal": "test",
                "status": "active",
                "constraints": [],
                "decisions": [],
                "next_action": None,
                "updated_at": "2026-01-01T00:00:00Z",
                "revision": 0,
            })
            script = ROOT / "continuity_validate_json.py"
            result = subprocess.run(
                [sys.executable, str(script), "--root", str(project)],
                cwd=ROOT, text=True, capture_output=True
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(
                list(payload), ["errors", "integrity", "schema_version", "valid"]
            )
            self.assertTrue(payload["valid"])
            self.assertEqual(payload["schema_version"], 1)

    def test_explicit_root_isolated_from_repository_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = self.make_project(tmp, {
                "schema_version": 2,
                "project": "",
                "goal": "test",
                "status": "active",
                "constraints": [],
                "decisions": [],
                "next_action": None,
                "updated_at": "2026-01-01T00:00:00Z",
                "revision": 0,
            })
            script = ROOT / "continuity_validate_json.py"
            result = subprocess.run(
                [sys.executable, str(script), "--root", str(project)],
                cwd=ROOT, text=True, capture_output=True
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertFalse(payload["valid"])
            self.assertIn("errors", payload)
            self.assertIn("wrong type for state field: project", payload["errors"])


if __name__ == "__main__":
    unittest.main()

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ExplicitRecoveryOutputContractTests(unittest.TestCase):
    def test_output_is_schema_versioned_and_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            continuity_dir = project / "continuity"
            continuity_dir.mkdir(parents=True)
            (continuity_dir / "state.json").write_text(
                json.dumps({
                    "schema_version": 2,
                    "project": "x",
                    "goal": "y",
                    "status": "active",
                    "constraints": [],
                    "decisions": [],
                    "next_action": None,
                    "revision": 0,
                    "updated_at": "2026-01-01T00:00:00Z",
                }) + "\n",
                encoding="utf-8",
            )
            (continuity_dir / "events.jsonl").write_text("", encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(ROOT / "continuity_recover.py"), "--root", str(project)],
                cwd=project,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                json.loads(result.stdout),
                {
                    "operation": "recover",
                    "recovered": False,
                    "root": str(project.resolve()),
                    "schema_version": 1,
                },
            )


if __name__ == "__main__":
    unittest.main()

import json
import subprocess
import sys
from pathlib import Path


def test_validate_and_handoff_contain_invalid_utf8(tmp_path):
    root = tmp_path
    continuity = root / "continuity"
    continuity.mkdir()
    (continuity / "state.json").write_text(
        json.dumps({
            "schema_version": 2,
            "project": "fixture",
            "goal": "test",
            "status": "active",
            "constraints": [],
            "decisions": [],
            "next_action": None,
            "revision": 0,
            "updated_at": "2026-01-01T00:00:00Z",
        }),
        encoding="utf-8",
    )
    (continuity / "events.jsonl").write_bytes(b"{\xff\n")
    repo_root = Path(__file__).resolve().parents[1]

    validate = subprocess.run(
        [sys.executable, str(repo_root / "continuity.py"), "validate"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert validate.returncode == 1
    assert "continuity file encoding invalid" in validate.stdout

    handoff = subprocess.run(
        [sys.executable, str(repo_root / "continuity.py"), "handoff", "--format", "json"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert handoff.returncode == 1
    assert handoff.stderr.strip() == "continuity file encoding invalid"

import json
import subprocess
import sys
from pathlib import Path


def test_explicit_recovery_reports_deterministic_error_without_mutation(tmp_path):
    root = tmp_path / "project"
    continuity_dir = root / "continuity"
    continuity_dir.mkdir(parents=True)
    state = {
        "schema_version": 2,
        "project": "x",
        "goal": "y",
        "status": "active",
        "constraints": [],
        "decisions": [],
        "next_action": None,
        "revision": 0,
        "updated_at": "2026-01-01T00:00:00Z",
    }
    state_path = continuity_dir / "state.json"
    events_path = continuity_dir / "events.jsonl"
    txn_path = continuity_dir / "transaction.json"
    state_path.write_text(json.dumps(state) + "\n", encoding="utf-8")
    events_path.write_text("", encoding="utf-8")
    txn_path.write_text("{not-json}\n", encoding="utf-8")
    before_state = state_path.read_bytes()
    before_events = events_path.read_bytes()
    before_txn = txn_path.read_bytes()

    script = Path(__file__).resolve().parents[1] / "continuity_recover.py"
    result = subprocess.run(
        [sys.executable, str(script), "--root", str(root)],
        text=True,
        capture_output=True,
    )

    assert result.returncode == 1
    assert result.stderr == ""
    assert json.loads(result.stdout) == {
        "schema_version": 1,
        "operation": "recover",
        "recovered": False,
        "error": "invalid JSON",
    }
    assert state_path.read_bytes() == before_state
    assert events_path.read_bytes() == before_events
    assert txn_path.read_bytes() == before_txn

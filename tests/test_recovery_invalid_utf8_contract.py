import json
import subprocess
import sys
from pathlib import Path


def test_recovery_invalid_utf8_is_stable_and_non_mutating(tmp_path):
    root = tmp_path
    continuity_dir = root / "continuity"
    continuity_dir.mkdir()
    state = {"schema_version": 2, "project": "fixture", "goal": "test", "status": "active", "constraints": [], "decisions": [], "next_action": None, "revision": 0, "updated_at": "2026-01-01T00:00:00Z"}
    (continuity_dir / "state.json").write_text(json.dumps(state), encoding="utf-8")
    (continuity_dir / "events.jsonl").write_text('{"type":"success","message":"ok"}\n', encoding="utf-8")
    txn = continuity_dir / "transaction.json"
    txn.write_bytes(b"{\"txid\":\"x\",\"state\":{}\n\xff")
    before = txn.read_bytes()

    result = subprocess.run([sys.executable, "continuity.py", "event", "note", "should-not-mutate"], cwd=Path(__file__).resolve().parents[1], env={**__import__('os').environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1])}, capture_output=True, text=True)
    assert result.returncode != 0
    assert "continuity file encoding invalid" in (result.stdout + result.stderr)
    assert txn.exists()
    assert txn.read_bytes() == before

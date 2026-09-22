import json
from pathlib import Path

import pytest

import continuity


def test_recovery_invalid_utf8_is_stable_and_non_mutating(tmp_path):
    continuity_dir = tmp_path / "continuity"
    continuity_dir.mkdir()
    state = {"schema_version": 2, "project": "fixture", "goal": "test", "status": "active", "constraints": [], "decisions": [], "next_action": None, "revision": 0, "updated_at": "2026-01-01T00:00:00Z"}
    (continuity_dir / "state.json").write_text(json.dumps(state), encoding="utf-8")
    (continuity_dir / "events.jsonl").write_text('{"type":"success","message":"ok"}\n', encoding="utf-8")
    txn = continuity_dir / "transaction.json"
    txn.write_bytes(b"{\"txid\":\"x\",\"state\":{}\n\xff")
    before = txn.read_bytes()

    continuity.configure_root(tmp_path)
    with pytest.raises(SystemExit, match="continuity file encoding invalid"):
        continuity.recover_unlocked()

    assert txn.exists()
    assert txn.read_bytes() == before

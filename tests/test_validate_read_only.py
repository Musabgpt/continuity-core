import json
import subprocess
import sys
from pathlib import Path


def test_validate_does_not_recover_pending_transaction(tmp_path):
    root = tmp_path / "project"
    continuity_dir = root / "continuity"
    continuity_dir.mkdir(parents=True)
    state = {
        "schema_version": 2,
        "project": "isolated",
        "goal": "test",
        "status": "active",
        "constraints": [],
        "decisions": [],
        "next_action": None,
        "revision": 1,
        "updated_at": "2026-01-01T00:00:00Z",
    }
    (continuity_dir / "state.json").write_text(json.dumps(state) + "\n", encoding="utf-8")
    (continuity_dir / "events.jsonl").write_text(
        json.dumps({"type": "success", "message": "ok"}) + "\n", encoding="utf-8"
    )
    txn = continuity_dir / "transaction.json"
    txn.write_text(json.dumps({"txid": "x", "state": state, "event": {"type": "note", "message": "pending"}}) + "\n", encoding="utf-8")
    before = {p: p.read_bytes() for p in (continuity_dir / "state.json", continuity_dir / "events.jsonl", txn)}

    repo_root = Path(__file__).resolve().parents[1]
    code = (
        "import continuity,sys; "
        "continuity.configure_root(sys.argv[1]); "
        "raise SystemExit(continuity.validate(None))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code, str(root)],
        cwd=repo_root,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    assert "pending transaction journal; recovery required" in result.stdout
    assert {p: p.read_bytes() for p in before} == before

import json
import subprocess
import sys
from pathlib import Path


def test_snapshot_is_explicit_root_and_non_mutating(tmp_path):
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
        "revision": 4,
        "updated_at": "2026-01-01T00:00:00Z",
    }
    (continuity_dir / "state.json").write_text(json.dumps(state) + "\n", encoding="utf-8")
    (continuity_dir / "events.jsonl").write_text(
        json.dumps({"type": "success", "message": "ok"}) + "\n", encoding="utf-8"
    )
    txn = continuity_dir / "transaction.json"
    txn.write_text('{"pending":true}\n', encoding="utf-8")
    before = {p: p.read_bytes() for p in (continuity_dir / "state.json", continuity_dir / "events.jsonl", txn)}

    repo_root = Path(__file__).resolve().parents[1]
    code = (
        "from continuity_readonly import snapshot; "
        "import json,sys; "
        "print(json.dumps(snapshot(sys.argv[1]), sort_keys=True))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code, str(root)],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["project"] == "isolated"
    assert payload["event_count"] == 1
    assert payload["pending_transaction"] is True
    assert {p: p.read_bytes() for p in before} == before

import json
import subprocess
import sys
from pathlib import Path


def test_explicit_recovery_entrypoint_recovers_only_when_transaction_exists(tmp_path):
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
    event = {"ts": "2026-01-01T00:00:00Z", "type": "note", "message": "pending", "txid": "tx-explicit"}
    tx = {"txid": "tx-explicit", "state": {**state, "next_action": "done"}, "event": event}
    (continuity_dir / "state.json").write_text(json.dumps(state) + "\n", encoding="utf-8")
    (continuity_dir / "events.jsonl").write_text("", encoding="utf-8")
    (continuity_dir / "transaction.json").write_text(json.dumps(tx) + "\n", encoding="utf-8")

    script = Path(__file__).resolve().parents[1] / "continuity_recover.py"
    first = subprocess.run([sys.executable, str(script), "--root", str(root)], text=True, capture_output=True)
    assert first.returncode == 0, first.stderr
    assert json.loads(first.stdout) == {"recovered": True, "root": str(root.resolve())}
    assert not (continuity_dir / "transaction.json").exists()
    assert json.loads((continuity_dir / "state.json").read_text(encoding="utf-8"))["next_action"] == "done"
    assert len((continuity_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()) == 1

    second = subprocess.run([sys.executable, str(script), "--root", str(root)], text=True, capture_output=True)
    assert second.returncode == 0, second.stderr
    assert json.loads(second.stdout) == {"recovered": False, "root": str(root.resolve())}
    assert len((continuity_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()) == 1

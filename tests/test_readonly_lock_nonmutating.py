import json
from pathlib import Path

from continuity_readonly import snapshot
from continuity_validate_json import validate_payload


def _seed(root: Path):
    continuity_dir = root / "continuity"
    continuity_dir.mkdir()
    state = {
        "schema_version": 2,
        "project": "test",
        "goal": "verify",
        "status": "active",
        "constraints": [],
        "decisions": [],
        "next_action": None,
        "revision": 0,
        "updated_at": "2026-01-01T00:00:00Z",
    }
    (continuity_dir / "state.json").write_text(json.dumps(state) + "\n", encoding="utf-8")
    (continuity_dir / "events.jsonl").write_text(
        json.dumps({"type": "success", "message": "seed"}) + "\n", encoding="utf-8"
    )


def test_read_only_paths_do_not_create_lock_file(tmp_path):
    _seed(tmp_path)
    lock_path = tmp_path / "continuity" / ".lock"

    payload = validate_payload(tmp_path)
    assert payload["valid"] is True
    assert not lock_path.exists()

    result = snapshot(tmp_path)
    assert result["valid"] is True
    assert not lock_path.exists()

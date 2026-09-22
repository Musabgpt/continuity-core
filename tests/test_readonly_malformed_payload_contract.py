import json
from pathlib import Path

from continuity_readonly import snapshot


def test_snapshot_contains_malformed_state_deterministically(tmp_path: Path):
    (tmp_path / "continuity").mkdir()
    (tmp_path / "continuity" / "state.json").write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")
    (tmp_path / "continuity" / "events.jsonl").write_text("", encoding="utf-8")

    result = snapshot(tmp_path)

    assert result == {
        "schema_version": 1,
        "valid": False,
        "error": "continuity validation failed",
    }

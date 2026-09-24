import json
from pathlib import Path

import continuity
from continuity_readonly import snapshot
from continuity_validate_json import validate_payload


def _make_project(root, name):
    continuity_dir = root / "continuity"
    continuity_dir.mkdir(parents=True)
    state = {
        "schema_version": 2,
        "project": name,
        "goal": "root isolation",
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


def test_readonly_helpers_restore_process_root_after_explicit_root(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    _make_project(first, "first")
    _make_project(second, "second")
    original = continuity.ROOT

    assert snapshot(first)["state"]["project"] == "first"
    assert continuity.ROOT == original

    payload = validate_payload(second)
    assert payload["valid"] is True
    assert continuity.ROOT == original

    assert snapshot(second)["state"]["project"] == "second"
    assert continuity.ROOT == original


def test_readonly_helpers_restore_process_root_after_validation_failure(tmp_path):
    broken = tmp_path / "broken"
    _make_project(broken, "broken")
    (broken / "continuity" / "state.json").write_text("{not-json\n", encoding="utf-8")
    original = continuity.ROOT

    snapshot_result = snapshot(broken)
    assert snapshot_result == {
        "schema_version": 1,
        "valid": False,
        "error": "invalid JSON",
    }
    assert continuity.ROOT == original

    payload = validate_payload(broken)
    assert payload["valid"] is False
    assert payload["errors"][0] == "invalid JSON"
    assert continuity.ROOT == original


if __name__ == "__main__":
    import unittest

    unittest.main()

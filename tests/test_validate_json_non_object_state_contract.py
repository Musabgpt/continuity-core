import json
from pathlib import Path

from continuity_validate_json import validate_payload


def test_structured_validation_contains_non_object_state_payload(tmp_path: Path):
    continuity_dir = tmp_path / "continuity"
    continuity_dir.mkdir()
    (continuity_dir / "state.json").write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")
    (continuity_dir / "events.jsonl").write_text("", encoding="utf-8")

    result = validate_payload(tmp_path)

    assert result == {
        "schema_version": 1,
        "valid": False,
        "errors": ["state payload must be an object"],
        "integrity": {
            "valid": True,
            "checked": {"events": 0, "transaction": 0},
            "first_break": None,
            "schema_version": 1,
        },
        "pending_transaction": {"present": False, "txid": None, "valid": True},
    }
    assert not (continuity_dir / "transaction.json").exists()

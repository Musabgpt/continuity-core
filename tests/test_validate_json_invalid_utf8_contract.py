from pathlib import Path

from continuity_validate_json import validate_payload


def test_structured_validation_contains_invalid_utf8_in_events(tmp_path: Path):
    continuity_dir = tmp_path / "continuity"
    continuity_dir.mkdir()
    (continuity_dir / "state.json").write_text(
        '{"schema_version": 2, "project": "p", "goal": "g", "status": "active", '
        '"constraints": [], "decisions": [], "next_action": null, "revision": 0, '
        '"updated_at": "2026-01-01T00:00:00Z"}',
        encoding="utf-8",
    )
    (continuity_dir / "events.jsonl").write_bytes(b"{\xff\n")

    result = validate_payload(tmp_path)

    assert result["valid"] is False
    assert result["errors"] == ["continuity file encoding invalid"]
    assert result["pending_transaction"] == {"present": False, "txid": None, "valid": True}
    assert not (continuity_dir / "transaction.json").exists()

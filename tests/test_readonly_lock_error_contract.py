from pathlib import Path
from unittest.mock import patch

from continuity_readonly import snapshot
from continuity_validate_json import validate_payload


def test_snapshot_contains_lock_failure_deterministically(tmp_path: Path):
    with patch("continuity_readonly.readonly_project_lock", side_effect=PermissionError("host-specific")):
        result = snapshot(tmp_path)
    assert result == {
        "schema_version": 1,
        "valid": False,
        "error": "continuity file permission denied",
    }


def test_structured_validation_contains_lock_failure_deterministically(tmp_path: Path):
    with patch("continuity_validate_json.readonly_project_lock", side_effect=OSError("host-specific")):
        result = validate_payload(tmp_path)
    assert result["schema_version"] == 1
    assert result["valid"] is False
    assert result["errors"] == ["continuity filesystem read failed"]
    assert result["pending_transaction"] is None

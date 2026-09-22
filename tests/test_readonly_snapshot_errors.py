import sys
from pathlib import Path


def test_snapshot_returns_structured_error_for_malformed_state(tmp_path):
    root = tmp_path / "project"
    continuity_dir = root / "continuity"
    continuity_dir.mkdir(parents=True)
    (continuity_dir / "state.json").write_text("{broken\n", encoding="utf-8")

    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))
    from continuity_readonly import snapshot

    payload = snapshot(root)
    assert payload == {
        "schema_version": 1,
        "valid": False,
        "error": "invalid JSON",
    }

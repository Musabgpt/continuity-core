import importlib.util
import json
import sys
from pathlib import Path


def load_module(root: Path):
    sys.path.insert(0, str(root))
    spec = importlib.util.spec_from_file_location("continuity", root / "continuity.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_event_contains_malformed_existing_journal_before_mutation(tmp_path, capsys):
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
    state_path = continuity_dir / "state.json"
    events_path = continuity_dir / "events.jsonl"
    state_path.write_text(json.dumps(state) + "\n", encoding="utf-8")
    events_path.write_bytes(b"{not-json}\n")

    module = load_module(root)
    module.configure_root(root)
    args = type("Args", (), {"kind": "note", "message": "new", "why": None, "expect_revision": 0})()

    try:
        module.event(args)
    except SystemExit as exc:
        assert str(exc) == "invalid JSON"
    else:
        raise AssertionError("mutation must fail closed")

    assert json.loads(state_path.read_text(encoding="utf-8")) == state
    assert events_path.read_bytes() == b"{not-json}\n"
    assert (continuity_dir / "transaction.json").exists()
    assert capsys.readouterr().out == ""

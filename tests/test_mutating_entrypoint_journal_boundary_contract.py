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


def make_fixture(tmp_path, schema_version=2):
    root = tmp_path / "project"
    continuity_dir = root / "continuity"
    continuity_dir.mkdir(parents=True)
    state = {
        "schema_version": schema_version,
        "project": "x",
        "goal": "y",
        "status": "active",
        "constraints": [],
        "decisions": [],
        "next_action": None,
        "revision": 0,
        "updated_at": "2026-01-01T00:00:00Z",
    }
    (continuity_dir / "state.json").write_text(json.dumps(state) + "\n", encoding="utf-8")
    (continuity_dir / "events.jsonl").write_bytes(b"{not-json}\n")
    return root, continuity_dir, state


def test_set_next_and_migrate_share_stable_malformed_event_boundary(tmp_path):
    for command in ("set_next", "migrate"):
        root, continuity_dir, state = make_fixture(tmp_path / command)
        module = load_module(root)
        module.configure_root(root)
        before_state = (continuity_dir / "state.json").read_bytes()
        before_events = (continuity_dir / "events.jsonl").read_bytes()
        if command == "set_next":
            args = type("Args", (), {"action": "later", "expect_revision": 0})()
            invoke = lambda: module.set_next(args)
        else:
            invoke = lambda: module.migrate(None)
        try:
            invoke()
        except SystemExit as exc:
            assert str(exc) == "invalid JSON"
        else:
            raise AssertionError(f"{command} must fail closed")
        assert (continuity_dir / "state.json").read_bytes() == before_state
        assert (continuity_dir / "events.jsonl").read_bytes() == before_events
        assert (continuity_dir / "transaction.json").exists() is False
        assert json.loads((continuity_dir / "state.json").read_text(encoding="utf-8")) == state

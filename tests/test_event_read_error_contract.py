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


def test_handoff_contains_event_permission_error(tmp_path, monkeypatch):
    root = tmp_path / "project"
    continuity = root / "continuity"
    continuity.mkdir(parents=True)
    (continuity / "state.json").write_text(json.dumps({
        "schema_version": 2,
        "project": "x",
        "goal": "y",
        "status": "active",
        "constraints": [],
        "decisions": [],
        "next_action": None,
        "revision": 0,
        "updated_at": "2026-01-01T00:00:00Z",
    }), encoding="utf-8")
    (continuity / "events.jsonl").write_text('{"type":"success","message":"ok"}\n', encoding="utf-8")
    module = load_module(root)
    module.configure_root(root)
    real_read_text = Path.read_text

    def denied(self, *args, **kwargs):
        if self == continuity / "events.jsonl":
            raise PermissionError("host-specific")
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", denied)
    try:
        module.handoff_payload()
    except SystemExit as exc:
        assert str(exc) == "continuity file permission denied"
    else:
        raise AssertionError("handoff must fail closed")


def test_validate_contains_event_os_error(tmp_path, monkeypatch, capsys):
    root = tmp_path / "project"
    continuity = root / "continuity"
    continuity.mkdir(parents=True)
    (continuity / "state.json").write_text(json.dumps({
        "schema_version": 2,
        "project": "x",
        "goal": "y",
        "status": "active",
        "constraints": [],
        "decisions": [],
        "next_action": None,
        "revision": 0,
        "updated_at": "2026-01-01T00:00:00Z",
    }), encoding="utf-8")
    (continuity / "events.jsonl").write_text('{"type":"success","message":"ok"}\n', encoding="utf-8")
    module = load_module(root)
    module.configure_root(root)
    real_read_text = Path.read_text

    def failed(self, *args, **kwargs):
        if self == continuity / "events.jsonl":
            raise OSError("host-specific")
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", failed)
    assert module.validate(None) == 1
    assert capsys.readouterr().out.strip() == "INVALID: continuity filesystem read failed"

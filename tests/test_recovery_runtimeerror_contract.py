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


def test_recovery_contains_unexpected_runtimeerror_without_mutation(tmp_path):
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
    event = {"ts": "2026-01-01T00:00:00Z", "type": "note", "message": "pending"}
    tx = {"txid": "tx-runtime", "state": state, "event": event}
    (continuity_dir / "state.json").write_text(json.dumps(state) + "\n", encoding="utf-8")
    (continuity_dir / "events.jsonl").write_text("", encoding="utf-8")
    txn_path = continuity_dir / "transaction.json"
    txn_path.write_text(json.dumps(tx) + "\n", encoding="utf-8")
    before_state = (continuity_dir / "state.json").read_bytes()
    before_events = (continuity_dir / "events.jsonl").read_bytes()
    before_txn = txn_path.read_bytes()

    module = load_module(root)
    module.configure_root(root)
    original_verify = module.verify_tx_shape

    def unexpected_failure(_):
        raise RuntimeError("host-specific runtime detail")

    module.verify_tx_shape = unexpected_failure
    try:
        module.recover_unlocked()
    except SystemExit as exc:
        assert str(exc) == "transaction recovery failed"
    else:
        raise AssertionError("recovery must fail closed")
    finally:
        module.verify_tx_shape = original_verify

    assert (continuity_dir / "state.json").read_bytes() == before_state
    assert (continuity_dir / "events.jsonl").read_bytes() == before_events
    assert txn_path.read_bytes() == before_txn

import importlib.util
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


def load_module(root: Path):
    sys.path.insert(0, str(root))
    spec = importlib.util.spec_from_file_location("continuity", root / "continuity.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RecoveryIdempotenceContractTests(unittest.TestCase):
    def test_recovery_replays_pending_transaction_once(self):
        repo_root = Path(__file__).resolve().parents[1]
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            continuity_dir = root / "continuity"
            continuity_dir.mkdir(parents=True)
            state = {
                "schema_version": 2,
                "project": "x",
                "goal": "y",
                "status": "active",
                "constraints": [],
                "decisions": [],
                "next_action": "resume",
                "revision": 1,
                "updated_at": "2026-01-01T00:00:00Z",
            }
            event = {
                "ts": "2026-01-01T00:00:00Z",
                "type": "note",
                "message": "replayed once",
                "txid": "tx-idempotent",
            }
            (continuity_dir / "state.json").write_text(json.dumps(state) + "\n", encoding="utf-8")
            (continuity_dir / "events.jsonl").write_text("", encoding="utf-8")

            module = load_module(repo_root)
            module.configure_root(root)
            material = {"txid": "tx-idempotent", "state": state, "event": event}
            transaction = {**material, "checksum": module.digest(material)}
            (continuity_dir / "transaction.json").write_text(
                json.dumps(transaction) + "\n", encoding="utf-8"
            )

            self.assertTrue(module.recover_unlocked())
            first_events = (continuity_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(first_events), 1)
            self.assertFalse((continuity_dir / "transaction.json").exists())

            self.assertFalse(module.recover_unlocked())
            second_events = (continuity_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(second_events, first_events)
            self.assertEqual(json.loads((continuity_dir / "state.json").read_text(encoding="utf-8")), state)


if __name__ == "__main__":
    unittest.main()

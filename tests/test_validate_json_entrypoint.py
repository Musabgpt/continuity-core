import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ValidateJsonEntrypointTests(unittest.TestCase):
    def make_project(self, tmp, state, events='{"type":"success","message":"ok"}\n'):
        project = Path(tmp)
        (project / "continuity").mkdir()
        (project / "continuity" / "state.json").write_text(
            json.dumps(state) + "\n", encoding="utf-8"
        )
        (project / "continuity" / "events.jsonl").write_text(
            events, encoding="utf-8"
        )
        return project

    def run_validator(self, project):
        script = ROOT / "continuity_validate_json.py"
        return subprocess.run(
            [sys.executable, str(script), "--root", str(project)],
            cwd=ROOT, text=True, capture_output=True
        )

    def valid_state(self, **overrides):
        state = {
            "schema_version": 2,
            "project": "demo",
            "goal": "test",
            "status": "active",
            "constraints": [],
            "decisions": [],
            "next_action": None,
            "updated_at": "2026-01-01T00:00:00Z",
            "revision": 0,
        }
        state.update(overrides)
        return state

    def test_valid_project_emits_stable_json_and_zero_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = self.make_project(tmp, self.valid_state())
            result = self.run_validator(project)
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(
                list(payload), ["errors", "integrity", "pending_transaction", "schema_version", "valid"]
            )
            self.assertTrue(payload["valid"])
            self.assertEqual(payload["schema_version"], 1)
            self.assertEqual(payload["pending_transaction"], {"present": False, "txid": None, "valid": True})

    def test_explicit_root_isolated_from_repository_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = self.make_project(tmp, self.valid_state(project=""))
            result = self.run_validator(project)
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertFalse(payload["valid"])
            self.assertIn("wrong type for state field: project", payload["errors"])

    def test_explicit_root_reads_events_from_target_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = self.make_project(
                tmp,
                self.valid_state(),
                events='{"type":"unknown","message":"bad"}\n',
            )
            result = self.run_validator(project)
            self.assertEqual(result.returncode, 1)
            payload = json.loads(result.stdout)
            self.assertFalse(payload["valid"])
            self.assertIn("invalid event type at line 1", payload["errors"])

    def test_pending_transaction_is_reported_without_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = self.make_project(tmp, self.valid_state())
            txn = {
                "txid": "tx-1",
                "state": self.valid_state(revision=1),
                "event": {"type": "note", "message": "pending"},
            }
            txn_path = project / "continuity" / "transaction.json"
            txn_path.write_text(json.dumps(txn) + "\n", encoding="utf-8")
            state_before = (project / "continuity" / "state.json").read_bytes()
            events_before = (project / "continuity" / "events.jsonl").read_bytes()
            result = self.run_validator(project)
            self.assertEqual(result.returncode, 1)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["pending_transaction"], {"present": True, "txid": "tx-1", "valid": True})
            self.assertIn("transaction journal pending; recovery required", payload["errors"])
            self.assertEqual(state_before, (project / "continuity" / "state.json").read_bytes())
            self.assertEqual(events_before, (project / "continuity" / "events.jsonl").read_bytes())
            self.assertTrue(txn_path.exists())

    def test_malformed_transaction_has_stable_diagnostic_without_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = self.make_project(tmp, self.valid_state())
            txn_path = project / "continuity" / "transaction.json"
            txn_path.write_text('{"txid": "broken"}\n', encoding="utf-8")
            state_before = (project / "continuity" / "state.json").read_bytes()
            events_before = (project / "continuity" / "events.jsonl").read_bytes()
            txn_before = txn_path.read_bytes()
            result = self.run_validator(project)
            self.assertEqual(result.returncode, 1)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["pending_transaction"], {
                "present": True,
                "txid": None,
                "valid": False,
                "error": "Transaction journal shape invalid: state must be dict.",
            })
            self.assertEqual(payload["errors"], [
                "transaction journal malformed: Transaction journal shape invalid: state must be dict."
            ])
            self.assertEqual(state_before, (project / "continuity" / "state.json").read_bytes())
            self.assertEqual(events_before, (project / "continuity" / "events.jsonl").read_bytes())
            self.assertEqual(txn_before, txn_path.read_bytes())

    def test_malformed_state_reports_category_not_parser_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "continuity").mkdir()
            (project / "continuity" / "state.json").write_text('{broken\n', encoding="utf-8")
            (project / "continuity" / "events.jsonl").write_text(
                '{"type":"success","message":"ok"}\n', encoding="utf-8"
            )
            result = self.run_validator(project)
            self.assertEqual(result.returncode, 1)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["errors"], ["invalid JSON"])


if __name__ == "__main__":
    unittest.main()

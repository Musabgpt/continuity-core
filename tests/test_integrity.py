import json, subprocess, sys, tempfile, unittest
from pathlib import Path

SOURCE=Path(__file__).resolve().parents[1]/"continuity_integrity.py"

class IntegrityTests(unittest.TestCase):
    def execute(self, root, *args):
        return subprocess.run([sys.executable, str(root/"continuity_integrity.py"), "--root", str(root), *args], text=True, capture_output=True)

    def setup(self, root):
        root.joinpath("continuity_integrity.py").write_text(SOURCE.read_text(encoding="utf-8"), encoding="utf-8")
        (root/"continuity").mkdir()
        (root/"continuity/events.jsonl").write_text(json.dumps({"type":"note","message":"legacy"})+"\n", encoding="utf-8")

    def test_legacy_events_remain_readable(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.setup(root)
            r=self.execute(root); self.assertEqual(r.returncode, 0, r.stdout+r.stderr)

    def test_pre_checksum_transaction_remains_readable(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.setup(root)
            tx={"txid":"legacy","state":{"revision":1},"event":{"type":"note","message":"ok"}}
            (root/"continuity/transaction.json").write_text(json.dumps(tx), encoding="utf-8")
            r=self.execute(root); self.assertEqual(r.returncode, 0, r.stdout+r.stderr)

    def test_clean_aggregate_audit_is_valid_and_non_mutating(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.setup(root)
            events=root/"continuity/events.jsonl"; before_events=events.read_text(encoding="utf-8")
            r=self.execute(root, "--audit-all")
            self.assertEqual(r.returncode, 0, r.stdout+r.stderr)
            self.assertEqual(json.loads(r.stdout), {
                "schema_version": 1,
                "valid": True,
                "first_break": None,
                "events": {"schema_version": 1, "valid": True, "checked": 1, "first_break": None},
                "transaction": {"schema_version": 1, "valid": True, "checked": 0, "first_break": None},
            })
            self.assertEqual(before_events, events.read_text(encoding="utf-8"))

    def test_aggregate_audit_first_break_summary_is_deterministic(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.setup(root)
            events=root/"continuity/events.jsonl"
            events.write_text(json.dumps({"type":"note","message":"ok","prev_hash":"GENESIS","chain_hash":"bad"})+"\n", encoding="utf-8")
            material={"txid":"x","state":{"revision":1},"event":{"type":"note","message":"ok"}}
            tx=dict(material); tx["checksum"]="0"*64
            (root/"continuity/transaction.json").write_text(json.dumps(tx), encoding="utf-8")
            r=self.execute(root, "--audit-all")
            payload=json.loads(r.stdout)
            self.assertEqual(payload["schema_version"], 1)
            self.assertEqual(payload["first_break"], {"scope":"events","line":1,"reason":"event hash mismatch"})

    def test_transaction_checksum_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.setup(root)
            material={"txid":"x","state":{"revision":1},"event":{"type":"note","message":"ok"}}
            tx=dict(material); tx["checksum"]="0"*64
            (root/"continuity/transaction.json").write_text(json.dumps(tx), encoding="utf-8")
            r=self.execute(root); self.assertNotEqual(r.returncode, 0); self.assertIn("checksum mismatch", r.stdout)

    def test_event_chain_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.setup(root)
            row={"type":"note","message":"ok","prev_hash":"GENESIS"}
            row["chain_hash"]="bad"
            (root/"continuity/events.jsonl").write_text(json.dumps(row)+"\n", encoding="utf-8")
            r=self.execute(root); self.assertNotEqual(r.returncode, 0); self.assertIn("hash mismatch", r.stdout)

    def test_orphaned_event_chain_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.setup(root)
            row={"type":"note","message":"ok","prev_hash":"orphan"}
            material=dict(row)
            row["chain_hash"] = __import__("hashlib").sha256(json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
            (root/"continuity/events.jsonl").write_text(json.dumps(row)+"\n", encoding="utf-8")
            r=self.execute(root, "--audit")
            self.assertNotEqual(r.returncode, 0)
            self.assertEqual(json.loads(r.stdout)["first_break"]["reason"], "event chain does not start at GENESIS")

    def test_audit_reports_first_broken_line_without_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.setup(root)
            row={"type":"note","message":"ok","prev_hash":"GENESIS"}
            row["chain_hash"]="bad"
            events=root/"continuity/events.jsonl"
            events.write_text(json.dumps(row)+"\n", encoding="utf-8")
            before=events.read_text(encoding="utf-8")
            r=self.execute(root, "--audit")
            self.assertEqual(json.loads(r.stdout)["valid"], False)
            self.assertIn('"line":1', r.stdout)
            self.assertEqual(before, events.read_text(encoding="utf-8"))

    def test_transaction_audit_reports_stable_checksum_error(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.setup(root)
            material={"txid":"x","state":{"revision":1},"event":{"type":"note","message":"ok"}}
            tx=dict(material); tx["checksum"]="0"*64
            journal=root/"continuity/transaction.json"
            journal.write_text(json.dumps(tx), encoding="utf-8")
            before=journal.read_text(encoding="utf-8")
            r=self.execute(root, "--audit-transaction")
            self.assertNotEqual(r.returncode, 0)
            self.assertEqual(json.loads(r.stdout), {"schema_version":1,"valid":False,"checked":1,"first_break":{"line":1,"reason":"transaction journal checksum mismatch"}})
            self.assertEqual(before, journal.read_text(encoding="utf-8"))

    def test_aggregate_audit_reports_both_domains_without_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.setup(root)
            row={"type":"note","message":"ok","prev_hash":"GENESIS","chain_hash":"bad"}
            events=root/"continuity/events.jsonl"; before_events=events.read_text(encoding="utf-8")
            material={"txid":"x","state":{"revision":1},"event":{"type":"note","message":"ok"}}
            tx=dict(material); tx["checksum"]="0"*64
            journal=root/"continuity/transaction.json"; journal.write_text(json.dumps(tx), encoding="utf-8"); before_tx=journal.read_text(encoding="utf-8")
            events.write_text(json.dumps(row)+"\n", encoding="utf-8")
            r=self.execute(root, "--audit-all")
            payload=json.loads(r.stdout)
            self.assertFalse(payload["valid"])
            self.assertEqual(payload["first_break"], {"scope":"events","line":1,"reason":"event hash mismatch"})
            self.assertEqual(payload["events"]["first_break"]["reason"], "event hash mismatch")
            self.assertEqual(payload["transaction"]["first_break"]["reason"], "transaction journal checksum mismatch")
            self.assertEqual(events.read_text(encoding="utf-8"), json.dumps(row)+"\n")
            self.assertEqual(journal.read_text(encoding="utf-8"), before_tx)

if __name__=="__main__": unittest.main()

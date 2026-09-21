import json, subprocess, sys, tempfile, unittest
from pathlib import Path

SOURCE=Path(__file__).resolve().parents[1]/"continuity_integrity.py"

class IntegrityTests(unittest.TestCase):
    def execute(self, root):
        return subprocess.run([sys.executable, str(root/"continuity_integrity.py"), "--root", str(root)], text=True, capture_output=True)

    def setup(self, root):
        root.joinpath("continuity_integrity.py").write_text(SOURCE.read_text(encoding="utf-8"), encoding="utf-8")
        (root/"continuity").mkdir()
        (root/"continuity/events.jsonl").write_text(json.dumps({"type":"note","message":"legacy"})+"\n", encoding="utf-8")

    def test_legacy_events_remain_readable(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.setup(root)
            r=self.execute(root); self.assertEqual(r.returncode, 0, r.stdout+r.stderr)

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

if __name__=="__main__": unittest.main()

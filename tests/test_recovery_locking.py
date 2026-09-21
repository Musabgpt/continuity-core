import json, subprocess, sys, tempfile, unittest, uuid
from pathlib import Path

SOURCE=Path(__file__).resolve().parents[1]/"continuity.py"

class RecoveryLockingTests(unittest.TestCase):
    def setup(self, root):
        root.joinpath("continuity.py").write_text(SOURCE.read_text(encoding="utf-8"),encoding="utf-8")
        r=subprocess.run([sys.executable,str(root/"continuity.py"),"init","--project","A","--goal","B"],text=True,capture_output=True)
        self.assertEqual(r.returncode,0,r.stderr)

    def test_recovers_crash_after_journal_before_event(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.setup(root); c=root/"continuity"
            state=json.loads((c/"state.json").read_text()); state["revision"]=1
            txid=str(uuid.uuid4()); row={"ts":"x","type":"note","message":"recovered","txid":txid}
            (c/"transaction.json").write_text(json.dumps({"txid":txid,"state":state,"event":row}))
            r=subprocess.run([sys.executable,str(root/"continuity.py"),"validate"],text=True,capture_output=True)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr); self.assertFalse((c/"transaction.json").exists())
            self.assertEqual(json.loads((c/"state.json").read_text())["revision"],1)
            rows=[json.loads(x) for x in (c/"events.jsonl").read_text().splitlines()]
            self.assertEqual(sum(x.get("txid")==txid for x in rows),1)

    def test_recovers_crash_after_event_without_duplicate(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.setup(root); c=root/"continuity"
            state=json.loads((c/"state.json").read_text()); state["revision"]=1
            txid=str(uuid.uuid4()); row={"ts":"x","type":"note","message":"once","txid":txid}
            with (c/"events.jsonl").open("a") as f: f.write(json.dumps(row)+"\n")
            (c/"transaction.json").write_text(json.dumps({"txid":txid,"state":state,"event":row}))
            r=subprocess.run([sys.executable,str(root/"continuity.py"),"handoff","--format","json"],text=True,capture_output=True)
            self.assertEqual(r.returncode,0,r.stderr); self.assertEqual(json.loads(r.stdout)["revision"],1)
            rows=[json.loads(x) for x in (c/"events.jsonl").read_text().splitlines()]
            self.assertEqual(sum(x.get("txid")==txid for x in rows),1)

    def test_concurrent_expected_revision_allows_exactly_one_writer(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.setup(root); cmd=[sys.executable,str(root/"continuity.py"),"event","note"]
            a=subprocess.Popen(cmd+["writer-a","--expect-revision","0"],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            b=subprocess.Popen(cmd+["writer-b","--expect-revision","0"],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            ar=a.communicate(); br=b.communicate(); codes=[a.returncode,b.returncode]
            self.assertEqual(sorted(codes),[0,1],(ar,br))
            state=json.loads((root/"continuity/state.json").read_text()); self.assertEqual(state["revision"],1)
            events=(root/"continuity/events.jsonl").read_text(); self.assertEqual(("writer-a" in events)+("writer-b" in events),1)
            loser=ar[1] if a.returncode else br[1]; self.assertIn("Revision conflict",loser)

if __name__=="__main__": unittest.main()

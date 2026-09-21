import json, subprocess, sys, tempfile, unittest
from pathlib import Path

SOURCE=Path(__file__).resolve().parents[1]/"continuity.py"

class ContinuityTests(unittest.TestCase):
    def run_cli(self, root, *args):
        script=root/"continuity.py"
        return subprocess.run([sys.executable,str(script),*args],text=True,capture_output=True)

    def setup_cli(self, root):
        root.joinpath("continuity.py").write_text(SOURCE.read_text(encoding="utf-8"),encoding="utf-8")

    def test_init_event_next_handoff(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.setup_cli(root)
            r=self.run_cli(root,"init","--project","Demo","--goal","Finish"); self.assertEqual(r.returncode,0,r.stderr)
            r=self.run_cli(root,"event","decision","Use tests","--why","Reliability"); self.assertEqual(r.returncode,0,r.stderr)
            r=self.run_cli(root,"next","Ship"); self.assertEqual(r.returncode,0,r.stderr)
            r=self.run_cli(root,"handoff"); self.assertEqual(r.returncode,0,r.stderr)
            self.assertIn("Goal: Finish",r.stdout); self.assertIn("Use tests",r.stdout); self.assertIn("Next action: Ship",r.stdout)
            s=json.loads((root/"continuity/state.json").read_text(encoding="utf-8")); self.assertEqual(s["decisions"],["Use tests"]); self.assertEqual(s["revision"],2)

    def test_init_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.setup_cli(root)
            self.assertEqual(self.run_cli(root,"init","--project","A","--goal","B").returncode,0)
            self.assertNotEqual(self.run_cli(root,"init","--project","X","--goal","Y").returncode,0)

    def test_force_resets_history(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.setup_cli(root)
            self.assertEqual(self.run_cli(root,"init","--project","A","--goal","B").returncode,0)
            self.assertEqual(self.run_cli(root,"event","failure","old failure").returncode,0)
            self.assertEqual(self.run_cli(root,"init","--project","X","--goal","Y","--force").returncode,0)
            history=(root/"continuity/events.jsonl").read_text(encoding="utf-8")
            self.assertNotIn("old failure",history); self.assertEqual(len(history.strip().splitlines()),1)

    def test_validate_detects_corruption(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.setup_cli(root)
            self.assertEqual(self.run_cli(root,"init","--project","A","--goal","B").returncode,0)
            self.assertEqual(self.run_cli(root,"validate").returncode,0)
            (root/"continuity/events.jsonl").write_text("{broken}\n",encoding="utf-8")
            r=self.run_cli(root,"validate"); self.assertNotEqual(r.returncode,0); self.assertIn("invalid event JSON",r.stdout)

    def test_json_handoff_is_deterministic_and_omits_timestamps(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.setup_cli(root)
            self.assertEqual(self.run_cli(root,"init","--project","A","--goal","B").returncode,0)
            self.assertEqual(self.run_cli(root,"event","failure","compile failed","--why","missing sdk").returncode,0)
            self.assertEqual(self.run_cli(root,"next","install sdk").returncode,0)
            a=self.run_cli(root,"handoff","--format","json"); b=self.run_cli(root,"handoff","--format","json")
            self.assertEqual(a.returncode,0,a.stderr); self.assertEqual(a.stdout,b.stdout)
            payload=json.loads(a.stdout); self.assertNotIn("updated_at",payload)
            self.assertEqual(payload["recent_failures"],[{"message":"compile failed","why":"missing sdk"}])
            self.assertEqual(payload["next_action"],"install sdk"); self.assertEqual(payload["revision"],2)

    def test_validate_rejects_unknown_schema(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.setup_cli(root)
            self.assertEqual(self.run_cli(root,"init","--project","A","--goal","B").returncode,0)
            path=root/"continuity/state.json"; state=json.loads(path.read_text(encoding="utf-8")); state["schema_version"]=999
            path.write_text(json.dumps(state),encoding="utf-8")
            r=self.run_cli(root,"validate"); self.assertNotEqual(r.returncode,0); self.assertIn("unsupported schema_version",r.stdout)

    def test_migrate_v1_to_v2_preserves_state(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.setup_cli(root); c=root/"continuity"; c.mkdir()
            old={"schema_version":1,"project":"Legacy","goal":"Keep data","status":"active","constraints":["c"],"decisions":["d"],"next_action":"n","updated_at":"2020-01-01T00:00:00Z"}
            (c/"state.json").write_text(json.dumps(old),encoding="utf-8"); (c/"events.jsonl").write_text(json.dumps({"ts":"x","type":"note","message":"legacy"})+"\n",encoding="utf-8")
            self.assertEqual(self.run_cli(root,"validate").returncode,0)
            self.assertNotEqual(self.run_cli(root,"next","blocked before migration").returncode,0)
            r=self.run_cli(root,"migrate"); self.assertEqual(r.returncode,0,r.stderr)
            new=json.loads((c/"state.json").read_text(encoding="utf-8")); self.assertEqual(new["schema_version"],2); self.assertEqual(new["revision"],0)
            for key in ("project","goal","status","constraints","decisions","next_action"): self.assertEqual(new[key],old[key])
            self.assertEqual(self.run_cli(root,"validate").returncode,0)

    def test_v2_requires_valid_revision(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.setup_cli(root)
            self.assertEqual(self.run_cli(root,"init","--project","A","--goal","B").returncode,0)
            path=root/"continuity/state.json"; state=json.loads(path.read_text(encoding="utf-8")); state["revision"]=-1; path.write_text(json.dumps(state),encoding="utf-8")
            r=self.run_cli(root,"validate"); self.assertNotEqual(r.returncode,0); self.assertIn("revision",r.stdout)

if __name__=="__main__": unittest.main()

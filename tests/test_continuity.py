import json, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

SOURCE=Path(__file__).resolve().parents[1]/"continuity.py"
INTEGRITY_SOURCE=Path(__file__).resolve().parents[1]/"continuity_integrity.py"

class ContinuityTests(unittest.TestCase):
    def run_cli(self, root, *args):
        script=root/"continuity.py"
        return subprocess.run([sys.executable,str(script),*args],text=True,capture_output=True)

    def setup_cli(self, root):
        root.joinpath("continuity.py").write_text(SOURCE.read_text(encoding="utf-8"),encoding="utf-8")
        shutil.copy2(INTEGRITY_SOURCE, root/"continuity_integrity.py")

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

    def test_handoff_refuses_hash_chain_corruption(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.setup_cli(root)
            self.assertEqual(self.run_cli(root,"init","--project","A","--goal","B").returncode,0)
            self.assertEqual(self.run_cli(root,"event","note","one").returncode,0)
            path=root/"continuity/events.jsonl"
            rows=[json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]
            rows[-1]["chain_hash"]="0"*64
            path.write_text("\n".join(json.dumps(row,separators=(",",":")) for row in rows)+"\n",encoding="utf-8")
            first=self.run_cli(root,"handoff","--format","json")
            second=self.run_cli(root,"handoff","--format","json")
            self.assertNotEqual(first.returncode,0); self.assertEqual(first.stdout,second.stdout)
            self.assertEqual(first.stderr,second.stderr)
            self.assertEqual(first.stderr,"Continuity integrity invalid: events line 2: event hash mismatch\n")

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

    def test_expected_revision_rejects_stale_writer_without_side_effects(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.setup_cli(root)
            self.assertEqual(self.run_cli(root,"init","--project","A","--goal","B").returncode,0)
            self.assertEqual(self.run_cli(root,"event","note","fresh","--expect-revision","0").returncode,0)
            state_before=(root/"continuity/state.json").read_text(encoding="utf-8")
            events_before=(root/"continuity/events.jsonl").read_text(encoding="utf-8")
            stale=self.run_cli(root,"event","failure","stale write","--expect-revision","0")
            self.assertNotEqual(stale.returncode,0); self.assertIn("Revision conflict",stale.stderr)
            self.assertEqual((root/"continuity/state.json").read_text(encoding="utf-8"),state_before)
            self.assertEqual((root/"continuity/events.jsonl").read_text(encoding="utf-8"),events_before)
            self.assertEqual(self.run_cli(root,"next","safe","--expect-revision","1").returncode,0)
            state=json.loads((root/"continuity/state.json").read_text(encoding="utf-8")); self.assertEqual(state["revision"],2); self.assertEqual(state["next_action"],"safe")

    def test_new_events_emit_verifiable_hash_chain(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.setup_cli(root)
            self.assertEqual(self.run_cli(root,"init","--project","A","--goal","B").returncode,0)
            self.assertEqual(self.run_cli(root,"event","note","one").returncode,0)
            self.assertEqual(self.run_cli(root,"event","note","two").returncode,0)
            rows=[json.loads(x) for x in (root/"continuity/events.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertTrue(all("chain_hash" in row and "prev_hash" in row for row in rows))
            self.assertEqual(rows[0]["prev_hash"],"GENESIS")
            self.assertEqual(rows[1]["prev_hash"],rows[0]["chain_hash"])
            verifier=root/"continuity_integrity.py"
            verifier.write_text(INTEGRITY_SOURCE.read_text(encoding="utf-8"),encoding="utf-8")
            r=subprocess.run([sys.executable,str(verifier),"--root",str(root)],text=True,capture_output=True)
            self.assertEqual(r.returncode,0,r.stderr)

if __name__=="__main__": unittest.main()
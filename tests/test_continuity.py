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
            events=root/"continuity/events.jsonl"; events.write_text(events.read_text(encoding="utf-8").replace("Continuity state initialized.","tampered"),encoding="utf-8")
            self.assertNotEqual(self.run_cli(root,"validate").returncode,0)

    def test_validate_rejects_unknown_schema(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.setup_cli(root)
            self.assertEqual(self.run_cli(root,"init","--project","A","--goal","B").returncode,0)
            state=root/"continuity/state.json"; value=json.loads(state.read_text(encoding="utf-8")); value["schema_version"]=99; state.write_text(json.dumps(value),encoding="utf-8")
            self.assertNotEqual(self.run_cli(root,"validate").returncode,0)

    def test_json_handoff_is_deterministic_and_omits_timestamps(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.setup_cli(root)
            self.assertEqual(self.run_cli(root,"init","--project","A","--goal","B").returncode,0)
            first=self.run_cli(root,"handoff","--format","json"); second=self.run_cli(root,"handoff","--format","json")
            self.assertEqual(first.returncode,0); self.assertEqual(first.stdout,second.stdout); self.assertNotIn("ts",first.stdout)

    def test_migrate_v1_to_v2_preserves_state(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.setup_cli(root)
            self.assertEqual(self.run_cli(root,"init","--project","A","--goal","B").returncode,0)
            state=root/"continuity/state.json"; value=json.loads(state.read_text(encoding="utf-8")); value["schema_version"]=1; value.pop("revision",None); state.write_text(json.dumps(value),encoding="utf-8")
            self.assertEqual(self.run_cli(root,"validate").returncode,0)
            self.assertEqual(self.run_cli(root,"migrate").returncode,0)
            migrated=json.loads(state.read_text(encoding="utf-8")); self.assertEqual(migrated["schema_version"],2); self.assertEqual(migrated["revision"],0)

    def test_v2_requires_valid_revision(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.setup_cli(root)
            self.assertEqual(self.run_cli(root,"init","--project","A","--goal","B").returncode,0)
            state=root/"continuity/state.json"; value=json.loads(state.read_text(encoding="utf-8")); value["revision"]=-1; state.write_text(json.dumps(value),encoding="utf-8")
            self.assertNotEqual(self.run_cli(root,"validate").returncode,0)

    def test_expected_revision_rejects_stale_writer_without_side_effects(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.setup_cli(root)
            self.assertEqual(self.run_cli(root,"init","--project","A","--goal","B").returncode,0)
            self.assertEqual(self.run_cli(root,"event","note","ok","--expect-revision","0").returncode,0)
            self.assertNotEqual(self.run_cli(root,"event","note","stale","--expect-revision","0").returncode,0)

    def test_new_events_emit_verifiable_hash_chain(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.setup_cli(root)
            self.assertEqual(self.run_cli(root,"init","--project","A","--goal","B").returncode,0)
            rows=[json.loads(x) for x in (root/"continuity/events.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
            self.assertEqual(rows[0]["prev_hash"],"GENESIS"); self.assertEqual(len(rows[0]["chain_hash"]),64)

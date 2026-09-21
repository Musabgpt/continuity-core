import json, subprocess, sys, tempfile, unittest
from pathlib import Path

SOURCE=Path(__file__).resolve().parents[1]/"continuity.py"

class ContinuityTests(unittest.TestCase):
    def run_cli(self, root, *args):
        script=root/"continuity.py"
        return subprocess.run([sys.executable,str(script),*args],text=True,capture_output=True)

    def test_init_event_next_handoff(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); root.joinpath("continuity.py").write_text(SOURCE.read_text(encoding="utf-8"),encoding="utf-8")
            r=self.run_cli(root,"init","--project","Demo","--goal","Finish"); self.assertEqual(r.returncode,0,r.stderr)
            r=self.run_cli(root,"event","decision","Use tests","--why","Reliability"); self.assertEqual(r.returncode,0,r.stderr)
            r=self.run_cli(root,"next","Ship"); self.assertEqual(r.returncode,0,r.stderr)
            r=self.run_cli(root,"handoff"); self.assertEqual(r.returncode,0,r.stderr)
            self.assertIn("Goal: Finish",r.stdout); self.assertIn("Use tests",r.stdout); self.assertIn("Next action: Ship",r.stdout)
            s=json.loads((root/"continuity/state.json").read_text(encoding="utf-8"))
            self.assertEqual(s["decisions"],["Use tests"])

    def test_init_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); root.joinpath("continuity.py").write_text(SOURCE.read_text(encoding="utf-8"),encoding="utf-8")
            self.assertEqual(self.run_cli(root,"init","--project","A","--goal","B").returncode,0)
            self.assertNotEqual(self.run_cli(root,"init","--project","X","--goal","Y").returncode,0)

    def test_force_resets_history(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); root.joinpath("continuity.py").write_text(SOURCE.read_text(encoding="utf-8"),encoding="utf-8")
            self.assertEqual(self.run_cli(root,"init","--project","A","--goal","B").returncode,0)
            self.assertEqual(self.run_cli(root,"event","failure","old failure").returncode,0)
            self.assertEqual(self.run_cli(root,"init","--project","X","--goal","Y","--force").returncode,0)
            history=(root/"continuity/events.jsonl").read_text(encoding="utf-8")
            self.assertNotIn("old failure",history)
            self.assertEqual(len(history.strip().splitlines()),1)

if __name__=="__main__": unittest.main()

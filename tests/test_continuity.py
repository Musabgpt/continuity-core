import json, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"continuity.py"

class ContinuityTests(unittest.TestCase):
    def run_cli(self,root,*args):
        return subprocess.run([sys.executable,str(SCRIPT),*args,"--root",str(root)],capture_output=True,text=True)

    def setup_cli(self,root):
        return

    def test_init_event_next_handoff(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            self.assertEqual(self.run_cli(root,"init","--project","A","--goal","B").returncode,0)
            self.assertEqual(self.run_cli(root,"event","note","one").returncode,0)
            self.assertEqual(self.run_cli(root,"next","install sdk").returncode,0)
            r=self.run_cli(root,"handoff","--format","json"); self.assertEqual(r.returncode,0,r.stderr)
            self.assertEqual(json.loads(r.stdout)["next_action"],"install sdk")

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
            self.assertNotEqual(first.returncode,0)
            self.assertEqual(first.stdout,second.stdout)
            self.assertEqual(first.stderr,second.stderr)
            self.assertEqual(first.stderr,"Continuity integrity invalid: events line 2: event hash mismatch\n")

if __name__=="__main__": unittest.main()

#!/usr/bin/env python3
import argparse, json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "continuity" / "state.json"
EVENTS = ROOT / "continuity" / "events.jsonl"

def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")

def load_state():
    if not STATE.exists():
        raise SystemExit("State not initialized. Run: python continuity.py init --project NAME --goal GOAL")
    return json.loads(STATE.read_text(encoding="utf-8"))

def save_state(s):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    s["updated_at"] = now()
    STATE.write_text(json.dumps(s, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def append_event(kind, message, why=None):
    EVENTS.parent.mkdir(parents=True, exist_ok=True)
    row={"ts":now(),"type":kind,"message":message}
    if why: row["why"]=why
    with EVENTS.open("a",encoding="utf-8") as f:
        f.write(json.dumps(row,ensure_ascii=False)+"\n")

def init(args):
    if STATE.exists() and not args.force:
        raise SystemExit("State already exists; use --force to replace it.")
    if args.force and EVENTS.exists():
        EVENTS.unlink()
    s={"schema_version":1,"project":args.project,"goal":args.goal,"status":"active",
       "constraints":[],"decisions":[],"next_action":None}
    save_state(s); append_event("success","Continuity state initialized.")

def event(args):
    s=load_state()
    append_event(args.kind,args.message,args.why)
    if args.kind=="decision" and args.message not in s["decisions"]:
        s["decisions"].append(args.message)
    save_state(s)

def set_next(args):
    s=load_state(); s["next_action"]=args.action; save_state(s)
    append_event("note","Next action set: "+args.action)

def validate(_):
    errors=[]
    try:
        s=load_state()
    except (SystemExit, json.JSONDecodeError) as exc:
        print("INVALID: "+str(exc)); return 1
    required={"schema_version":int,"project":str,"goal":str,"status":str,"constraints":list,"decisions":list,"next_action":(str,type(None)),"updated_at":str}
    for key,typ in required.items():
        if key not in s: errors.append("missing state field: "+key)
        elif not isinstance(s[key],typ): errors.append("wrong type for state field: "+key)
    if isinstance(s.get("project"),str) and not s["project"].strip(): errors.append("project is empty")
    if isinstance(s.get("goal"),str) and not s["goal"].strip(): errors.append("goal is empty")
    if isinstance(s.get("constraints"),list) and not all(isinstance(x,str) and x.strip() for x in s["constraints"]): errors.append("constraints must be non-empty strings")
    if isinstance(s.get("decisions"),list) and not all(isinstance(x,str) and x.strip() for x in s["decisions"]): errors.append("decisions must be non-empty strings")
    if EVENTS.exists():
        for n,line in enumerate(EVENTS.read_text(encoding="utf-8").splitlines(),1):
            try: row=json.loads(line)
            except json.JSONDecodeError: errors.append(f"invalid event JSON at line {n}"); continue
            if row.get("type") not in {"decision","success","failure","note"}: errors.append(f"invalid event type at line {n}")
            if not isinstance(row.get("message"),str) or not row["message"].strip(): errors.append(f"invalid event message at line {n}")
    else: errors.append("events file is missing")
    if errors:
        print("INVALID")
        for e in errors: print("- "+e)
        return 1
    print("VALID")
    return 0

def handoff(_):
    s=load_state()
    print(f"# {s['project']} — handoff")
    print(f"Goal: {s['goal']}")
    print(f"Status: {s['status']}")
    if s["constraints"]:
        print("Constraints: " + "; ".join(s["constraints"]))
    if s["decisions"]:
        print("Decisions:")
        for x in s["decisions"][-8:]: print("- "+x)
    print("Next action: " + (s.get("next_action") or "UNSET"))
    print("Updated: " + s["updated_at"])

def build_parser():
    p=argparse.ArgumentParser(description="Compact project continuity ledger")
    sp=p.add_subparsers(dest="cmd",required=True)
    i=sp.add_parser("init"); i.add_argument("--project",required=True); i.add_argument("--goal",required=True); i.add_argument("--force",action="store_true"); i.set_defaults(func=init)
    e=sp.add_parser("event"); e.add_argument("kind",choices=["decision","success","failure","note"]); e.add_argument("message"); e.add_argument("--why"); e.set_defaults(func=event)
    n=sp.add_parser("next"); n.add_argument("action"); n.set_defaults(func=set_next)
    h=sp.add_parser("handoff"); h.set_defaults(func=handoff)
    v=sp.add_parser("validate"); v.set_defaults(func=validate)
    return p

if __name__=="__main__":
    a=build_parser().parse_args(); result=a.func(a); raise SystemExit(result or 0)

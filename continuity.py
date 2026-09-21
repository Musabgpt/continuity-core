#!/usr/bin/env python3
import argparse, json, os, uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
DIR=ROOT/"continuity"; STATE=DIR/"state.json"; EVENTS=DIR/"events.jsonl"; TXN=DIR/"transaction.json"
LATEST_SCHEMA=2; SUPPORTED_SCHEMAS={1,2}

def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")

def atomic_text(path,text):
    path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_name(path.name+".tmp")
    with tmp.open("w",encoding="utf-8") as f: f.write(text); f.flush(); os.fsync(f.fileno())
    os.replace(tmp,path)

def raw_state():
    if not STATE.exists(): raise SystemExit("State not initialized. Run: python continuity.py init --project NAME --goal GOAL")
    return json.loads(STATE.read_text(encoding="utf-8"))

def event_ids():
    if not EVENTS.exists(): return set()
    ids=set()
    for line in EVENTS.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row=json.loads(line)
            if row.get("txid"): ids.add(row["txid"])
    return ids

def append_row(row):
    DIR.mkdir(parents=True,exist_ok=True)
    with EVENTS.open("a",encoding="utf-8") as f:
        f.write(json.dumps(row,ensure_ascii=False,separators=(",",":"))+"\n"); f.flush(); os.fsync(f.fileno())

def recover():
    if not TXN.exists(): return False
    tx=json.loads(TXN.read_text(encoding="utf-8")); txid=tx["txid"]
    if txid not in event_ids(): append_row(tx["event"])
    atomic_text(STATE,json.dumps(tx["state"],indent=2,ensure_ascii=False)+"\n")
    TXN.unlink(); return True

def load_state(): recover(); return raw_state()

def save_state(s):
    s["updated_at"]=now(); atomic_text(STATE,json.dumps(s,indent=2,ensure_ascii=False)+"\n")

def make_event(kind,message,why=None,txid=None):
    row={"ts":now(),"type":kind,"message":message}
    if why: row["why"]=why
    if txid: row["txid"]=txid
    return row

def append_event(kind,message,why=None): append_row(make_event(kind,message,why))

def transact(s,kind,message,why=None):
    txid=str(uuid.uuid4()); s["updated_at"]=now(); row=make_event(kind,message,why,txid)
    tx={"txid":txid,"state":s,"event":row}
    atomic_text(TXN,json.dumps(tx,ensure_ascii=False,separators=(",",":"))+"\n")
    recover()

def read_events():
    recover()
    if not EVENTS.exists(): return []
    return [json.loads(x) for x in EVENTS.read_text(encoding="utf-8").splitlines() if x.strip()]

def init(args):
    if STATE.exists() and not args.force: raise SystemExit("State already exists; use --force to replace it.")
    DIR.mkdir(parents=True,exist_ok=True)
    if args.force:
        for p in (EVENTS,TXN):
            if p.exists(): p.unlink()
    s={"schema_version":LATEST_SCHEMA,"project":args.project,"goal":args.goal,"status":"active","constraints":[],"decisions":[],"next_action":None,"revision":0}
    save_state(s); append_event("success","Continuity state initialized.")

def require_latest(s):
    v=s.get("schema_version")
    if v!=LATEST_SCHEMA: raise SystemExit(f"State schema {v} is read-compatible but not writable; run: python continuity.py migrate")

def require_revision(s,expected):
    if expected is not None and s["revision"]!=expected: raise SystemExit(f"Revision conflict: expected {expected}, current {s['revision']}. Reload state before writing.")

def event(args):
    s=load_state(); require_latest(s); require_revision(s,args.expect_revision)
    if args.kind=="decision" and args.message not in s["decisions"]: s["decisions"].append(args.message)
    s["revision"]+=1; transact(s,args.kind,args.message,args.why)

def set_next(args):
    s=load_state(); require_latest(s); require_revision(s,args.expect_revision)
    s["next_action"]=args.action; s["revision"]+=1; transact(s,"note","Next action set: "+args.action)

def validate(_):
    errors=[]
    try: recover(); s=raw_state()
    except (SystemExit,json.JSONDecodeError,KeyError) as exc: print("INVALID: "+str(exc)); return 1
    req={"schema_version":int,"project":str,"goal":str,"status":str,"constraints":list,"decisions":list,"next_action":(str,type(None)),"updated_at":str}
    for k,t in req.items():
        if k not in s: errors.append("missing state field: "+k)
        elif not isinstance(s[k],t): errors.append("wrong type for state field: "+k)
    if s.get("schema_version") not in SUPPORTED_SCHEMAS: errors.append("unsupported schema_version")
    if s.get("schema_version")==2 and (not isinstance(s.get("revision"),int) or isinstance(s.get("revision"),bool) or s.get("revision",-1)<0): errors.append("schema v2 requires non-negative integer revision")
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
        print("INVALID"); [print("- "+e) for e in errors]; return 1
    print("VALID"); return 0

def migrate(_):
    s=load_state(); v=s.get("schema_version")
    if v not in SUPPORTED_SCHEMAS: print(f"Cannot migrate unsupported schema_version {v}"); return 1
    if v==LATEST_SCHEMA: print(f"Already at schema_version {LATEST_SCHEMA}"); return 0
    if v==1:
        s["schema_version"]=2; s["revision"]=0; transact(s,"success","Migrated state schema from v1 to v2.","v2 adds a monotonic revision counter for stale-state detection.")
        print("Migrated schema_version 1 -> 2"); return 0
    return 1

def handoff_payload():
    s=load_state(); events=read_events(); failures=[{"message":e["message"],**({"why":e["why"]} if e.get("why") else {})} for e in events if e.get("type")=="failure"][-5:]
    p={"schema_version":s["schema_version"],"project":s["project"],"goal":s["goal"],"status":s["status"],"constraints":s["constraints"],"decisions":s["decisions"][-8:],"recent_failures":failures,"next_action":s.get("next_action")}
    if s["schema_version"]>=2: p["revision"]=s["revision"]
    return p

def handoff(args):
    p=handoff_payload()
    if args.format=="json": print(json.dumps(p,ensure_ascii=False,sort_keys=True,separators=(",",":"))); return 0
    print(f"# {p['project']} — handoff\nGoal: {p['goal']}\nStatus: {p['status']}")
    if "revision" in p: print(f"Revision: {p['revision']}")
    if p["constraints"]: print("Constraints: "+"; ".join(p["constraints"]))
    if p["decisions"]:
        print("Decisions:"); [print("- "+x) for x in p["decisions"]]
    if p["recent_failures"]:
        print("Recent failures:"); [print("- "+x["message"]+(" — "+x["why"] if x.get("why") else "")) for x in p["recent_failures"]]
    print("Next action: "+(p.get("next_action") or "UNSET")); return 0

def build_parser():
    p=argparse.ArgumentParser(description="Compact project continuity ledger"); sp=p.add_subparsers(dest="cmd",required=True)
    i=sp.add_parser("init"); i.add_argument("--project",required=True); i.add_argument("--goal",required=True); i.add_argument("--force",action="store_true"); i.set_defaults(func=init)
    e=sp.add_parser("event"); e.add_argument("kind",choices=["decision","success","failure","note"]); e.add_argument("message"); e.add_argument("--why"); e.add_argument("--expect-revision",type=int); e.set_defaults(func=event)
    n=sp.add_parser("next"); n.add_argument("action"); n.add_argument("--expect-revision",type=int); n.set_defaults(func=set_next)
    h=sp.add_parser("handoff"); h.add_argument("--format",choices=["text","json"],default="text"); h.set_defaults(func=handoff)
    v=sp.add_parser("validate"); v.set_defaults(func=validate); m=sp.add_parser("migrate"); m.set_defaults(func=migrate); return p

if __name__=="__main__":
    a=build_parser().parse_args(); result=a.func(a); raise SystemExit(result or 0)

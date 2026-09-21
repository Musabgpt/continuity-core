import argparse, hashlib, json
from pathlib import Path

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()

def audit_events(path):
    """Return structured, non-mutating diagnostics for the first broken hash link."""
    if not path.exists():
        return {"valid": False, "checked": 0, "first_break": {"line": None, "reason": "events file is missing"}}
    previous = None
    checked = 0
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        checked += 1
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            return {"valid": False, "checked": checked, "first_break": {"line": number, "reason": "invalid event JSON"}}
        protected = "chain_hash" in row or "prev_hash" in row
        if not protected:
            continue
        prev = row.get("prev_hash", "GENESIS")
        if previous is not None and prev != previous:
            return {"valid": False, "checked": checked, "first_break": {"line": number, "reason": "event chain break"}}
        material = dict(row)
        material.pop("chain_hash", None)
        if row.get("chain_hash") != digest(material):
            return {"valid": False, "checked": checked, "first_break": {"line": number, "reason": "event hash mismatch"}}
        previous = row.get("chain_hash")
    return {"valid": True, "checked": checked, "first_break": None}

def verify_events(path):
    audit = audit_events(path)
    return [] if audit["valid"] else [f"{audit['first_break']['reason']} at line {audit['first_break']['line']}"]

def verify_transaction(path):
    if not path.exists():
        return []
    try:
        tx=json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ["transaction journal is invalid JSON"]
    if "checksum" not in tx:
        return []
    material={"txid":tx.get("txid"),"state":tx.get("state"),"event":tx.get("event")}
    errors=[]
    if tx.get("checksum") != digest(material):
        errors.append("transaction journal checksum mismatch")
    if not isinstance(tx.get("txid"), str) or not isinstance(tx.get("state"), dict) or not isinstance(tx.get("event"), dict):
        errors.append("transaction journal shape is invalid")
    return errors

def main():
    p=argparse.ArgumentParser(); p.add_argument("--root", default="."); p.add_argument("--audit", action="store_true")
    args=p.parse_args(); root=Path(args.root)
    if args.audit:
        print(json.dumps(audit_events(root/"continuity/events.jsonl"), sort_keys=True, separators=(",", ":")))
        return 0 if audit_events(root/"continuity/events.jsonl")["valid"] else 1
    errors=verify_events(root/"continuity/events.jsonl")+verify_transaction(root/"continuity/transaction.json")
    if errors:
        print("INVALID")
        for error in errors: print("- "+error)
        return 1
    print("VALID"); return 0

if __name__=="__main__": raise SystemExit(main())

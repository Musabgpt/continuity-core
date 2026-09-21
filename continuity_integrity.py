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

def audit_transaction(path):
    """Return stable, non-mutating diagnostics for the transaction journal."""
    if not path.exists():
        return {"valid": True, "checked": 0, "first_break": None}
    try:
        tx = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"valid": False, "checked": 1, "first_break": {"line": 1, "reason": "invalid transaction JSON"}}
    if "checksum" not in tx:
        return {"valid": True, "checked": 1, "first_break": None}
    material = {"txid": tx.get("txid"), "state": tx.get("state"), "event": tx.get("event")}
    if tx.get("checksum") != digest(material):
        return {"valid": False, "checked": 1, "first_break": {"line": 1, "reason": "transaction journal checksum mismatch"}}
    if not isinstance(tx.get("txid"), str) or not isinstance(tx.get("state"), dict) or not isinstance(tx.get("event"), dict):
        return {"valid": False, "checked": 1, "first_break": {"line": 1, "reason": "transaction journal shape is invalid"}}
    return {"valid": True, "checked": 1, "first_break": None}

def audit_all(root):
    events = audit_events(root/"continuity/events.jsonl")
    transaction = audit_transaction(root/"continuity/transaction.json")
    return {"valid": events["valid"] and transaction["valid"], "events": events, "transaction": transaction}

def verify_events(path):
    audit = audit_events(path)
    return [] if audit["valid"] else [f"{audit['first_break']['reason']} at line {audit['first_break']['line']}"]

def verify_transaction(path):
    audit = audit_transaction(path)
    return [] if audit["valid"] else [f"{audit['first_break']['reason']} at line {audit['first_break']['line']}"]

def main():
    p=argparse.ArgumentParser(); p.add_argument("--root", default="."); p.add_argument("--audit", action="store_true"); p.add_argument("--audit-transaction", action="store_true"); p.add_argument("--audit-all", action="store_true")
    args=p.parse_args(); root=Path(args.root)
    if args.audit:
        result = audit_events(root/"continuity/events.jsonl")
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0 if result["valid"] else 1
    if args.audit_transaction:
        result = audit_transaction(root/"continuity/transaction.json")
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0 if result["valid"] else 1
    if args.audit_all:
        result = audit_all(root)
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0 if result["valid"] else 1
    errors=verify_events(root/"continuity/events.jsonl")+verify_transaction(root/"continuity/transaction.json")
    if errors:
        print("INVALID")
        for error in errors: print("- "+error)
        return 1
    print("VALID"); return 0

if __name__=="__main__": raise SystemExit(main())

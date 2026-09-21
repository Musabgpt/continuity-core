import argparse, hashlib, json
from pathlib import Path

AUDIT_SCHEMA_VERSION = 1

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()

def diagnostic(valid, checked, first_break):
    return {"schema_version": AUDIT_SCHEMA_VERSION, "valid": valid, "checked": checked, "first_break": first_break}

def audit_events(path):
    """Return structured, non-mutating diagnostics for the first broken hash link."""
    if not path.exists():
        return diagnostic(False, 0, {"line": None, "reason": "events file is missing"})
    previous = None
    checked = 0
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        checked += 1
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            return diagnostic(False, checked, {"line": number, "reason": "invalid event JSON"})
        protected = "chain_hash" in row or "prev_hash" in row
        if not protected:
            continue
        prev = row.get("prev_hash", "GENESIS")
        chain = row.get("chain_hash")
        if not isinstance(prev, str) or not isinstance(chain, str):
            return diagnostic(False, checked, {"line": number, "reason": "event hash fields must be strings"})
        if len(chain) != 64 or any(char not in "0123456789abcdef" for char in chain):
            return diagnostic(False, checked, {"line": number, "reason": "event chain_hash must be 64 lowercase hex characters"})
        if previous is None and prev != "GENESIS":
            return diagnostic(False, checked, {"line": number, "reason": "event chain does not start at GENESIS"})
        if previous is not None and prev != previous:
            return diagnostic(False, checked, {"line": number, "reason": "event chain break"})
        material = dict(row)
        material.pop("chain_hash", None)
        if row.get("chain_hash") != digest(material):
            return diagnostic(False, checked, {"line": number, "reason": "event hash mismatch"})
        previous = row.get("chain_hash")
    return diagnostic(True, checked, None)

def audit_transaction(path):
    """Return stable, non-mutating diagnostics for the transaction journal."""
    if not path.exists():
        return diagnostic(True, 0, None)
    try:
        tx = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return diagnostic(False, 1, {"line": 1, "reason": "invalid transaction JSON"})
    if "checksum" not in tx:
        return diagnostic(True, 1, None)
    required = {"txid": str, "state": dict, "event": dict}
    for key, expected in required.items():
        if key not in tx or not isinstance(tx[key], expected):
            return diagnostic(False, 1, {"line": 1, "reason": f"transaction journal shape invalid: {key} must be {expected.__name__}"})
    material = {"txid": tx.get("txid"), "state": tx.get("state"), "event": tx.get("event")}
    if tx.get("checksum") != digest(material):
        return diagnostic(False, 1, {"line": 1, "reason": "transaction journal checksum mismatch"})
    return diagnostic(True, 1, None)

def audit_all(root):
    events = audit_events(root/"continuity/events.jsonl")
    transaction = audit_transaction(root/"continuity/transaction.json")
    breaks = []
    if events["first_break"] is not None:
        breaks.append({"scope": "events", **events["first_break"]})
    if transaction["first_break"] is not None:
        breaks.append({"scope": "transaction", **transaction["first_break"]})
    first_break = breaks[0] if breaks else None
    return {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "valid": events["valid"] and transaction["valid"],
        "first_break": first_break,
        "events": events,
        "transaction": transaction,
    }

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

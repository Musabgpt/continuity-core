import argparse, hashlib, json
from pathlib import Path

AUDIT_SCHEMA_VERSION = 1
SUPPORTED_STATE_SCHEMAS = {1, 2}

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()

def diagnostic(valid, checked, first_break):
    return {"schema_version": AUDIT_SCHEMA_VERSION, "valid": valid, "checked": checked, "first_break": first_break}

def audit_state(path):
    """Return stable, non-mutating diagnostics for the persisted state shape."""
    if not path.exists(): return diagnostic(False, 0, {"line": None, "reason": "state file is missing"})
    try: content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError: return diagnostic(False, 0, {"line": 1, "reason": "state file encoding is invalid"})
    except OSError: return diagnostic(False, 0, {"line": None, "reason": "state file could not be read"})
    try: state = json.loads(content)
    except json.JSONDecodeError: return diagnostic(False, 1, {"line": 1, "reason": "invalid state JSON"})
    if not isinstance(state, dict): return diagnostic(False, 1, {"line": 1, "reason": "state payload must be an object"})
    required = {"schema_version": int, "project": str, "goal": str, "status": str, "constraints": list, "decisions": list, "next_action": (str, type(None)), "updated_at": str}
    for key, expected in required.items():
        if key not in state: return diagnostic(False, 1, {"line": 1, "reason": f"state field missing: {key}"})
        value = state[key]
        valid_type = isinstance(value, expected) if isinstance(expected, tuple) else isinstance(value, expected) and not (expected is int and isinstance(value, bool))
        if not valid_type:
            expected_name = "string or null" if key == "next_action" else expected.__name__
            return diagnostic(False, 1, {"line": 1, "reason": f"state field invalid: {key} must be {expected_name}"})
    if state["schema_version"] not in SUPPORTED_STATE_SCHEMAS: return diagnostic(False, 1, {"line": 1, "reason": "unsupported state schema_version"})
    if not state["project"].strip(): return diagnostic(False, 1, {"line": 1, "reason": "state project is empty"})
    if not state["goal"].strip(): return diagnostic(False, 1, {"line": 1, "reason": "state goal is empty"})
    if not all(isinstance(value, str) and value.strip() for value in state["constraints"]): return diagnostic(False, 1, {"line": 1, "reason": "state constraints must be non-empty strings"})
    if not all(isinstance(value, str) and value.strip() for value in state["decisions"]): return diagnostic(False, 1, {"line": 1, "reason": "state decisions must be non-empty strings"})
    if state["schema_version"] == 2:
        revision = state.get("revision")
        if not isinstance(revision, int) or isinstance(revision, bool) or revision < 0: return diagnostic(False, 1, {"line": 1, "reason": "state schema v2 requires non-negative integer revision"})
    return diagnostic(True, 1, None)

def audit_events(path):
    """Return structured, non-mutating diagnostics for the first broken hash link."""
    if not path.exists(): return diagnostic(False, 0, {"line": None, "reason": "events file is missing"})
    try: content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError: return diagnostic(False, 0, {"line": 1, "reason": "events file encoding is invalid"})
    except OSError: return diagnostic(False, 0, {"line": None, "reason": "events file could not be read"})
    previous = None; protected_chain_started = False; checked = 0
    for number, line in enumerate(content.splitlines(), 1):
        if not line.strip(): continue
        checked += 1
        try: row = json.loads(line)
        except json.JSONDecodeError: return diagnostic(False, checked, {"line": number, "reason": "invalid event JSON"})
        if not isinstance(row, dict): return diagnostic(False, checked, {"line": number, "reason": "event record must be an object"})
        protected = "chain_hash" in row or "prev_hash" in row
        if not protected:
            if protected_chain_started: return diagnostic(False, checked, {"line": number, "reason": "event chain protection missing"})
            continue
        protected_chain_started = True; prev = row.get("prev_hash", "GENESIS"); chain = row.get("chain_hash")
        if not isinstance(prev, str) or not isinstance(chain, str): return diagnostic(False, checked, {"line": number, "reason": "event hash fields must be strings"})
        if len(chain) != 64 or any(char not in "0123456789abcdef" for char in chain): return diagnostic(False, checked, {"line": number, "reason": "event chain_hash must be 64 lowercase hex characters"})
        if previous is None and prev != "GENESIS": return diagnostic(False, checked, {"line": number, "reason": "event chain does not start at GENESIS"})
        if previous is not None and prev != previous: return diagnostic(False, checked, {"line": number, "reason": "event chain break"})
        material = dict(row); material.pop("chain_hash", None)
        if row.get("chain_hash") != digest(material): return diagnostic(False, checked, {"line": number, "reason": "event hash mismatch"})
        previous = row.get("chain_hash")
    return diagnostic(True, checked, None)

def audit_transaction(path):
    """Return stable, non-mutating diagnostics for the transaction journal."""
    if not path.exists(): return diagnostic(True, 0, None)
    try: content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError: return diagnostic(False, 0, {"line": 1, "reason": "transaction file encoding is invalid"})
    except OSError: return diagnostic(False, 0, {"line": None, "reason": "transaction file could not be read"})
    try: tx = json.loads(content)
    except json.JSONDecodeError: return diagnostic(False, 1, {"line": 1, "reason": "invalid transaction JSON"})
    if not isinstance(tx, dict): return diagnostic(False, 1, {"line": 1, "reason": "transaction journal must be an object"})
    required = {"txid": str, "state": dict, "event": dict}
    for key, expected in required.items():
        if key not in tx or not isinstance(tx[key], expected): return diagnostic(False, 1, {"line": 1, "reason": f"transaction journal shape invalid: {key} must be {expected.__name__}"})
    if "checksum" in tx:
        checksum = tx.get("checksum")
        if not isinstance(checksum, str): return diagnostic(False, 1, {"line": 1, "reason": "transaction journal checksum invalid: checksum must be a string"})
        if len(checksum) != 64 or any(char not in "0123456789abcdef" for char in checksum): return diagnostic(False, 1, {"line": 1, "reason": "transaction journal checksum invalid: checksum must be 64 lowercase hex characters"})
        material = {"txid": tx.get("txid"), "state": tx.get("state"), "event": tx.get("event")}
        if checksum != digest(material): return diagnostic(False, 1, {"line": 1, "reason": "transaction journal checksum mismatch"})
    state = tx["state"]
    state_required = {"schema_version": int, "project": str, "goal": str, "status": str, "constraints": list, "decisions": list, "next_action": (str, type(None)), "updated_at": str}
    for key, expected in state_required.items():
        if key not in state: return diagnostic(False, 1, {"line": 1, "reason": f"transaction state field missing: {key}"})
        value = state[key]
        valid_type = isinstance(value, expected) if isinstance(expected, tuple) else isinstance(value, expected) and not (expected is int and isinstance(value, bool))
        if not valid_type:
            expected_name = "string or null" if key == "next_action" else expected.__name__
            return diagnostic(False, 1, {"line": 1, "reason": f"transaction state field invalid: {key} must be {expected_name}"})
    if state["schema_version"] not in SUPPORTED_STATE_SCHEMAS: return diagnostic(False, 1, {"line": 1, "reason": "unsupported transaction state schema_version"})
    if not state["project"].strip(): return diagnostic(False, 1, {"line": 1, "reason": "transaction state project is empty"})
    if not state["goal"].strip(): return diagnostic(False, 1, {"line": 1, "reason": "transaction state goal is empty"})
    if not all(isinstance(value, str) and value.strip() for value in state["constraints"]): return diagnostic(False, 1, {"line": 1, "reason": "transaction state constraints must be non-empty strings"})
    if not all(isinstance(value, str) and value.strip() for value in state["decisions"]): return diagnostic(False, 1, {"line": 1, "reason": "transaction state decisions must be non-empty strings"})
    if state["schema_version"] == 2:
        revision = state.get("revision")
        if not isinstance(revision, int) or isinstance(revision, bool) or revision < 0: return diagnostic(False, 1, {"line": 1, "reason": "transaction state schema v2 requires non-negative integer revision"})
    return diagnostic(True, 1, None)

def audit_all(root):
    state = audit_state(root/"continuity/state.json"); events = audit_events(root/"continuity/events.jsonl"); transaction = audit_transaction(root/"continuity/transaction.json")
    breaks = []
    if state["first_break"] is not None: breaks.append({"scope": "state", **state["first_break"]})
    if events["first_break"] is not None: breaks.append({"scope": "events", **events["first_break"]})
    if transaction["first_break"] is not None: breaks.append({"scope": "transaction", **transaction["first_break"]})
    first_break = breaks[0] if breaks else None
    return {"schema_version": AUDIT_SCHEMA_VERSION, "valid": state["valid"] and events["valid"] and transaction["valid"], "first_break": first_break, "state": state, "events": events, "transaction": transaction}

def verify_state(path):
    audit = audit_state(path); return [] if audit["valid"] else [f"{audit['first_break']['reason']} at line {audit['first_break']['line']}"]
def verify_events(path):
    audit = audit_events(path); return [] if audit["valid"] else [f"{audit['first_break']['reason']} at line {audit['first_break']['line']}"]
def verify_transaction(path):
    audit = audit_transaction(path); return [] if audit["valid"] else [f"{audit['first_break']['reason']} at line {audit['first_break']['line']}"]

def main():
    p=argparse.ArgumentParser(); p.add_argument("--root", default="."); p.add_argument("--audit", action="store_true"); p.add_argument("--audit-state", action="store_true"); p.add_argument("--audit-transaction", action="store_true"); p.add_argument("--audit-all", action="store_true")
    args=p.parse_args(); root=Path(args.root)
    if args.audit_state: result=audit_state(root/"continuity/state.json")
    elif args.audit: result=audit_events(root/"continuity/events.jsonl")
    elif args.audit_transaction: result=audit_transaction(root/"continuity/transaction.json")
    elif args.audit_all: result=audit_all(root)
    else:
        errors=verify_events(root/"continuity/events.jsonl")+verify_transaction(root/"continuity/transaction.json")
        if errors: print("INVALID"); [print("- "+e) for e in errors]; return 1
        print("VALID"); return 0
    print(json.dumps(result, sort_keys=True, separators=(",", ":"))); return 0 if result["valid"] else 1

if __name__=="__main__": raise SystemExit(main())

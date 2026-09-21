import argparse, hashlib, json
from pathlib import Path

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()

def verify_events(path):
    if not path.exists():
        return ["events file is missing"]
    errors=[]; previous=None
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row=json.loads(line)
        except json.JSONDecodeError:
            errors.append(f"invalid event JSON at line {number}")
            continue
        if "chain_hash" in row or "prev_hash" in row:
            prev=row.get("prev_hash", "GENESIS")
            if previous is not None and prev != previous:
                errors.append(f"event chain break at line {number}")
            material=dict(row); material.pop("chain_hash", None)
            if row.get("chain_hash") != digest(material):
                errors.append(f"event hash mismatch at line {number}")
            previous=row.get("chain_hash")
    return errors

def verify_transaction(path):
    if not path.exists():
        return []
    try:
        tx=json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ["transaction journal is invalid JSON"]
    material={"txid":tx.get("txid"),"state":tx.get("state"),"event":tx.get("event")}
    if tx.get("checksum") != digest(material):
        return ["transaction journal checksum mismatch"]
    if not isinstance(tx.get("txid"), str) or not isinstance(tx.get("state"), dict) or not isinstance(tx.get("event"), dict):
        return ["transaction journal shape is invalid"]
    return []

def main():
    p=argparse.ArgumentParser(); p.add_argument("--root", default="."); root=Path(p.parse_args().root)
    errors=verify_events(root/"continuity/events.jsonl")+verify_transaction(root/"continuity/transaction.json")
    if errors:
        print("INVALID")
        for error in errors: print("- "+error)
        return 1
    print("VALID"); return 0

if __name__=="__main__": raise SystemExit(main())

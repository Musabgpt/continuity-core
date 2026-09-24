#!/usr/bin/env python3
"""Non-mutating machine-readable validation for Continuity Core."""
import argparse
import json
from pathlib import Path

import continuity
from continuity import audit_all, raw_state, verify_tx_checksum, verify_tx_shape
from continuity_readonly_lock import readonly_project_lock
from continuity_root import isolated_root


def _stable_error(exc):
    """Return deterministic diagnostics without Python-version-specific text."""
    if isinstance(exc, json.JSONDecodeError):
        return "invalid JSON"
    if isinstance(exc, UnicodeDecodeError):
        return "continuity file encoding invalid"
    if isinstance(exc, FileNotFoundError):
        return "required continuity file missing"
    if isinstance(exc, PermissionError):
        return "continuity file permission denied"
    if isinstance(exc, OSError):
        return "continuity filesystem read failed"
    if isinstance(exc, SystemExit):
        return str(exc)
    if isinstance(exc, (TypeError, KeyError, AttributeError)):
        return "transaction journal shape invalid"
    return "continuity validation failed"


def _transaction_status():
    if not continuity.TXN.exists():
        return {"present": False, "txid": None, "valid": True}
    try:
        tx = json.loads(continuity.TXN.read_text(encoding="utf-8"))
        verify_tx_shape(tx)
        verify_tx_checksum(tx)
        return {"present": True, "txid": tx["txid"], "valid": True}
    except (SystemExit, json.JSONDecodeError, UnicodeDecodeError, OSError, TypeError, KeyError, AttributeError) as exc:
        return {"present": True, "txid": None, "valid": False, "error": _stable_error(exc)}


def _is_duplicate_transaction_diagnostic(message, pending_transaction):
    if not pending_transaction or pending_transaction.get("valid") is not False:
        return False
    return message.startswith("integrity audit failed: transaction line ")


def validate_payload(root=None):
    with isolated_root(continuity, continuity.ROOT if root is None else Path(root)):
        errors = []
        pending_transaction = None
        integrity = {"valid": True, "checked": {"events": 0, "transaction": 0}, "first_break": None, "schema_version": 1}
        try:
            try:
                with readonly_project_lock():
                    pending_transaction = _transaction_status()
                    if pending_transaction["present"] and pending_transaction["valid"]:
                        errors.append("transaction journal pending; recovery required")
                    elif pending_transaction["present"] and not pending_transaction["valid"]:
                        errors.append("transaction journal malformed: " + pending_transaction["error"])
                    try:
                        state = raw_state()
                    except (SystemExit, json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
                        return {
                            "schema_version": 1,
                            "valid": False,
                            "errors": [_stable_error(exc), *errors],
                            "integrity": integrity,
                            "pending_transaction": pending_transaction,
                        }
                    if not isinstance(state, dict):
                        return {
                            "schema_version": 1,
                            "valid": False,
                            "errors": ["state payload must be an object", *errors],
                            "integrity": integrity,
                            "pending_transaction": pending_transaction,
                        }
                    integrity = audit_all(continuity.ROOT)
                    if not integrity["valid"]:
                        first = integrity["first_break"]
                        diagnostic = f"integrity audit failed: {first['scope']} line {first['line']}: {first['reason']}"
                        if not _is_duplicate_transaction_diagnostic(diagnostic, pending_transaction):
                            errors.append(diagnostic)
                    required = {
                        "schema_version": int,
                        "project": str,
                        "goal": str,
                        "status": str,
                        "constraints": list,
                        "decisions": list,
                        "next_action": (str, type(None)),
                        "updated_at": str,
                    }
                    for key, expected in required.items():
                        if key not in state:
                            errors.append(f"missing state field: {key}")
                        elif not isinstance(state[key], expected):
                            errors.append(f"wrong type for state field: {key}")
                    if state.get("schema_version") not in {1, 2}:
                        errors.append("unsupported schema_version")
                    if state.get("schema_version") == 2 and (
                        not isinstance(state.get("revision"), int)
                        or isinstance(state.get("revision"), bool)
                        or state.get("revision", -1) < 0
                    ):
                        errors.append("schema v2 requires non-negative integer revision")
                    events_path = continuity.EVENTS
                    if events_path.exists():
                        try:
                            event_lines = events_path.read_text(encoding="utf-8").splitlines()
                        except (UnicodeDecodeError, OSError) as exc:
                            errors.append(_stable_error(exc))
                            event_lines = []
                        for number, line in enumerate(event_lines, 1):
                            try:
                                row = json.loads(line)
                            except json.JSONDecodeError:
                                errors.append(f"invalid event JSON at line {number}")
                                continue
                            if not isinstance(row, dict):
                                errors.append(f"event record must be an object at line {number}")
                                continue
                            if row.get("type") not in {"decision", "success", "failure", "note"}:
                                errors.append(f"invalid event type at line {number}")
                            if not isinstance(row.get("message"), str) or not row["message"].strip():
                                errors.append(f"invalid event message at line {number}")
            except (OSError, RuntimeError) as exc:
                return {
                    "schema_version": 1,
                    "valid": False,
                    "errors": [_stable_error(exc), *errors],
                    "integrity": integrity,
                    "pending_transaction": pending_transaction,
                }
            return {
                "schema_version": 1,
                "valid": not errors,
                "errors": errors,
                "integrity": integrity,
                "pending_transaction": pending_transaction,
            }
        finally:
            pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Structured non-mutating continuity validation")
    parser.add_argument("--root", type=Path, default=None, help="project root containing continuity/")
    args = parser.parse_args()
    payload = validate_payload(args.root)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    raise SystemExit(0 if payload["valid"] else 1)

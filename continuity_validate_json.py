#!/usr/bin/env python3
"""Non-mutating machine-readable validation for Continuity Core."""
import json
from continuity import EVENTS, ROOT, STATE, audit_all, project_lock, raw_state, recover_unlocked


def validate_payload():
    errors = []
    integrity = {"valid": True, "checked": {"events": 0, "transaction": 0}, "first_break": None, "schema_version": 1}
    with project_lock():
        try:
            recover_unlocked()
            state = raw_state()
        except Exception as exc:
            return {
                "schema_version": 1,
                "valid": False,
                "errors": [str(exc)],
                "integrity": integrity,
            }
        integrity = audit_all(ROOT)
        if not integrity["valid"]:
            first = integrity["first_break"]
            errors.append(f"integrity audit failed: {first['scope']} line {first['line']}: {first['reason']}")
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
        if EVENTS.exists():
            for number, line in enumerate(EVENTS.read_text(encoding="utf-8").splitlines(), 1):
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    errors.append(f"invalid event JSON at line {number}")
                    continue
                if row.get("type") not in {"decision", "success", "failure", "note"}:
                    errors.append(f"invalid event type at line {number}")
                if not isinstance(row.get("message"), str) or not row["message"].strip():
                    errors.append(f"invalid event message at line {number}")
        else:
            errors.append("events file is missing")
    return {
        "schema_version": 1,
        "valid": not errors,
        "errors": errors,
        "integrity": integrity,
    }


if __name__ == "__main__":
    payload = validate_payload()
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    raise SystemExit(0 if payload["valid"] else 1)

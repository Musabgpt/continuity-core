#!/usr/bin/env python3
"""Read-only continuity accessors with explicit root isolation.

This module deliberately never calls recovery. Callers that need recovery must
use an explicit mutating/recovery path from continuity.py.
"""
import json
from pathlib import Path

import continuity
from continuity_integrity import audit_all
from continuity_readonly_lock import readonly_project_lock
from continuity_root import isolated_root


def _stable_error(exc):
    """Return a deterministic, type-aware read-only failure diagnostic."""
    if isinstance(exc, json.JSONDecodeError):
        return "invalid JSON"
    if isinstance(exc, FileNotFoundError):
        return "required continuity file missing"
    if isinstance(exc, PermissionError):
        return "continuity file permission denied"
    if isinstance(exc, OSError):
        return "continuity filesystem read failed"
    if isinstance(exc, (SystemExit, ValueError, TypeError)):
        return "continuity validation failed"
    return "continuity read failed"


def snapshot(root):
    """Return a deterministic read-only snapshot or a structured failure."""
    with isolated_root(continuity, root):
        try:
            try:
                with readonly_project_lock():
                    integrity = audit_all(continuity.ROOT)
                    if not integrity["valid"]:
                        first = integrity["first_break"]
                        return {
                            "schema_version": 1,
                            "valid": False,
                            "error": "continuity integrity invalid",
                            "integrity": {
                                "scope": first["scope"],
                                "line": first["line"],
                                "reason": first["reason"],
                            },
                        }
                    try:
                        state = continuity.raw_state()
                        events = continuity.read_events_unlocked()
                    except (SystemExit, ValueError, TypeError, json.JSONDecodeError, OSError) as exc:
                        return {
                            "schema_version": 1,
                            "valid": False,
                            "error": _stable_error(exc),
                        }
            except (OSError, RuntimeError, ValueError, TypeError) as exc:
                return {
                    "schema_version": 1,
                    "valid": False,
                    "error": _stable_error(exc),
                }
            return {
                "schema_version": 1,
                "valid": True,
                "state": {
                    "schema_version": state.get("schema_version"),
                    "project": state.get("project"),
                    "goal": state.get("goal"),
                    "status": state.get("status"),
                    "revision": state.get("revision"),
                },
                "event_count": len(events),
                "pending_transaction": continuity.TXN.exists(),
            }
        finally:
            # Keep this finally as a local safety boundary: the shared context
            # manager owns restoration, while this scope remains explicit.
            pass

#!/usr/bin/env python3
"""Read-only continuity accessors with explicit root isolation.

This module deliberately never calls recovery. Callers that need recovery must
use an explicit mutating/recovery path from continuity.py.
"""
import json
from pathlib import Path

import continuity
from continuity_readonly_lock import readonly_project_lock


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
    if isinstance(exc, SystemExit):
        return "continuity validation failed"
    return "continuity read failed"


def snapshot(root):
    """Return a deterministic read-only snapshot or a structured failure."""
    continuity.configure_root(Path(root))
    try:
        with readonly_project_lock():
            try:
                state = continuity.raw_state()
                events = continuity.read_events_unlocked()
            except (SystemExit, json.JSONDecodeError, OSError) as exc:
                return {
                    "schema_version": 1,
                    "valid": False,
                    "error": _stable_error(exc),
                }
    except (OSError, RuntimeError) as exc:
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

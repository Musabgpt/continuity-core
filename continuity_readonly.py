#!/usr/bin/env python3
"""Read-only continuity accessors with explicit root isolation.

This module deliberately never calls recovery. Callers that need recovery must
use an explicit mutating/recovery path from continuity.py.
"""
import json
from pathlib import Path

import continuity


def snapshot(root):
    """Return a deterministic read-only snapshot or a structured failure."""
    continuity.configure_root(Path(root))
    with continuity.project_lock():
        try:
            state = continuity.raw_state()
            events = continuity.read_events_unlocked()
        except (SystemExit, json.JSONDecodeError, OSError) as exc:
            return {
                "schema_version": 1,
                "valid": False,
                "error": str(exc),
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

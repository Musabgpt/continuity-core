#!/usr/bin/env python3
"""Read-only continuity accessors with explicit root isolation.

This module deliberately never calls recovery. Callers that need recovery must
use an explicit mutating/recovery path from continuity.py.
"""
import json
from pathlib import Path

import continuity


def snapshot(root):
    """Return canonical state/events metadata without mutating project files."""
    continuity.configure_root(Path(root))
    with continuity.project_lock():
        state = continuity.raw_state()
        events = continuity.read_events_unlocked()
        pending = continuity.TXN.exists()
    return {
        "schema_version": state.get("schema_version"),
        "project": state.get("project"),
        "goal": state.get("goal"),
        "status": state.get("status"),
        "revision": state.get("revision"),
        "event_count": len(events),
        "pending_transaction": pending,
    }

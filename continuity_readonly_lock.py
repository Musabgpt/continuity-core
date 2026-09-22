#!/usr/bin/env python3
"""Non-mutating advisory lock acquisition for read-only commands.

Read-only callers use an existing lock only. If the lock is absent they proceed
without creating one, so a read does not leave a filesystem trace. This is an
advisory race boundary: callers must still treat a concurrent writer as an
external coordination concern and should retry if a stable snapshot is needed.
"""
from contextlib import contextmanager

import continuity


@contextmanager
def readonly_project_lock():
    """Acquire an existing project lock without creating any filesystem entry."""
    lock_path = continuity.LOCK
    if not lock_path.exists():
        yield
        return
    try:
        lock_file = lock_path.open("r+b")
    except FileNotFoundError:
        # The writer removed/replaced the lock between exists() and open().
        # Preserve the non-mutating contract instead of creating or failing on a
        # transient race; callers that need a stable snapshot should retry.
        yield
        return
    with lock_file as f:
        if __import__("os").name == "nt":
            import msvcrt
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

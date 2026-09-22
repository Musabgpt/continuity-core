#!/usr/bin/env python3
"""Non-mutating advisory lock acquisition for read-only commands."""
from contextlib import contextmanager

import continuity


@contextmanager
def readonly_project_lock():
    """Acquire an existing project lock without creating any filesystem entry.

    If no lock file exists, the caller proceeds without creating one. This keeps
    read-only commands byte-for-byte non-mutating while mutating commands still
    serialize through continuity.project_lock().
    """
    lock_path = continuity.LOCK
    if not lock_path.exists():
        yield
        return
    with lock_path.open("r+b") as f:
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

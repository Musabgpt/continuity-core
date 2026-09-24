#!/usr/bin/env python3
"""Scoped process-global continuity-root rebinding."""
from contextlib import contextmanager
from pathlib import Path
from threading import RLock


_ROOT_SCOPE_LOCK = RLock()


@contextmanager
def isolated_root(module, root):
    """Temporarily bind a continuity module to an explicit project root."""
    with _ROOT_SCOPE_LOCK:
        previous_root = module.ROOT
        module.configure_root(Path(root))
        try:
            yield
        finally:
            module.configure_root(previous_root)

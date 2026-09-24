#!/usr/bin/env python3
"""Scoped process-global continuity-root rebinding."""
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def isolated_root(module, root):
    """Temporarily bind a continuity module to an explicit project root."""
    previous_root = module.ROOT
    module.configure_root(Path(root))
    try:
        yield
    finally:
        module.configure_root(previous_root)

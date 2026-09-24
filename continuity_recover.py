#!/usr/bin/env python3
"""Explicit, mutating recovery entrypoint for a pending Continuity Core transaction."""
import argparse
import json
from pathlib import Path

import continuity
from continuity_root import isolated_root


OUTPUT_SCHEMA_VERSION = 1


def emit(payload):
    payload = {"schema_version": OUTPUT_SCHEMA_VERSION, "operation": "recover", **payload}
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Recover a pending Continuity Core transaction")
    parser.add_argument("--root", default=".", help="Project root containing the continuity/ directory")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    try:
        with isolated_root(continuity, root):
            with continuity.project_lock():
                recovered = continuity.recover_unlocked()
    except SystemExit as exc:
        emit({"recovered": False, "error": str(exc)})
        return 1
    emit({"recovered": bool(recovered), "root": str(root)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

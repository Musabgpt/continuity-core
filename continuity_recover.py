#!/usr/bin/env python3
"""Explicit, mutating recovery entrypoint for a pending Continuity Core transaction."""
import argparse
import json
from pathlib import Path

import continuity


def main(argv=None):
    parser = argparse.ArgumentParser(description="Recover a pending Continuity Core transaction")
    parser.add_argument("--root", default=".", help="Project root containing the continuity/ directory")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    continuity.configure_root(root)
    try:
        with continuity.project_lock():
            recovered = continuity.recover_unlocked()
    except SystemExit as exc:
        print(json.dumps({"recovered": False, "error": str(exc)}, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        return 1
    print(json.dumps({"recovered": bool(recovered), "root": str(root)}, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

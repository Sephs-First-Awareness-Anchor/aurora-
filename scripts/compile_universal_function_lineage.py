#!/usr/bin/env python3
"""Compile and verify Aurora's whole-function X/T/N/B/A ancestry."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aurora_internal.aurora_universal_function_lineage import UniversalFunctionLineage


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT), help="Aurora repository root")
    parser.add_argument("--verify-only", action="store_true", help="Load and verify without rebuilding")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print status")
    args = parser.parse_args()

    lineage = UniversalFunctionLineage(
        repo_root=os.path.abspath(args.root),
        auto_build=not args.verify_only,
        include_lambdas=True,
        persist=True,
    )
    if not args.verify_only:
        lineage.rebuild()
    result = {
        "status": lineage.status(),
        "verification": lineage.verify(),
    }
    print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if result["verification"].get("valid") else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Record PR264's actual new test/tool/CI files in Aurora's canonical map.

Never invents a cognitive owner or a dependency edge. It accepts only
known source categories, leaving composites/exercises to the existing
`render_module_ownership.py --update-derived` parser.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    import render_module_ownership as renderer

    path = ROOT / "docs" / "module_ownership.json"
    data = renderer.load_mapping(str(path))
    found = renderer.scan(str(ROOT), data["scope"])
    recorded = set(data["files"])
    missing = sorted(found - recorded)
    excess = sorted(recorded - found)
    if excess:
        raise RuntimeError("Unexpected missing source files, audit required: " + repr(excess))

    for file in missing:
        if file.startswith(".github/workflows/") and file.endswith((".yml", ".yaml")):
            domain, subsystem, language = "repo", "ci", "yaml"
        elif file.startswith("scripts/") and file.endswith(".py"):
            domain, subsystem, language = "desktop", "tooling", "python"
        elif file.startswith("tests/") and file.endswith(".py"):
            domain, subsystem, language = "desktop", "tests", "python"
        else:
            raise RuntimeError("Unknown source ownership, manual review required: " + file)

        row = {
            "domain": domain, "subsystem": subsystem, "also": [],
            "composite": None, "layer": None, "layer_role": None,
            "language": language, "basis": "location", "duties": None,
        }
        if subsystem == "tests":
            row["exercises"] = []
        data["files"][file] = row
    path.write_text(renderer.dump_mapping(data), encoding="utf-8")
    print("Explicitly classified new source files:", *missing, sep="\n - ")
    print("Next: render_module_ownership.py --update-derived")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

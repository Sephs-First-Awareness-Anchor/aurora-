#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
prune_recall_marker_nodes.py -- FIX-A128 clean-up of what the bug already wrote.

Before FIX-A128 the ontological web learned "[recalled:<concept>]" transport
markers as words.  Checked before writing this: no code reads those nodes, none
was ever used in her expression (times_used_in_expression == 0 for all 149), none
belongs to a cluster; the only things attached are their own co-occurrence
relations and a category listing.  This removes exactly those nodes, the
relations that touch them, and their category entries.  Nothing else changes.

Dry run by default.  --apply writes a ".pre_recall_prune_backup" copy first and
replaces the file atomically (same checksum and write-then-rename idiom as
aurora_vocabulary_seed_apply.py).  Safe to run again: a clean web is untouched.

    python scripts/prune_recall_marker_nodes.py --state-dir aurora_state          # report
    python scripts/prune_recall_marker_nodes.py --state-dir aurora_state --apply  # do it
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict


def is_recall_marker(word: str) -> bool:
    return "[recalled" in str(word)


def prune_web_dict(data: Dict[str, Any]) -> Dict[str, int]:
    """Remove marker nodes, relations touching them, and category entries, in place."""
    nodes = data.get("nodes") or {}
    marked = {w for w in nodes if is_recall_marker(w)}
    relations = data.get("relations") or {}
    doomed = [rid for rid, rel in relations.items()
              if rel.get("source_word") in marked or rel.get("target_word") in marked
              or is_recall_marker(rel.get("source_word", "")) or is_recall_marker(rel.get("target_word", ""))]
    for rid in doomed:
        del relations[rid]
    for w in marked:
        del nodes[w]
    cat_entries = 0
    for cat, words in (data.get("categories") or {}).items():
        keep = [w for w in words if not is_recall_marker(w)]
        cat_entries += len(words) - len(keep)
        data["categories"][cat] = keep
    return {"nodes": len(marked), "relations": len(doomed), "category_entries": cat_entries}


def _checksum(data: Dict[str, Any]) -> str:
    payload = {k: v for k, v in data.items() if k != "_checksum"}
    return hashlib.md5(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:12]


def run(state_dir: str, apply: bool) -> Dict[str, Any]:
    path = Path(state_dir) / "aurora_oets_web.json"
    if not path.exists():
        return {"status": "no_web_file", "path": str(path)}
    data = json.loads(path.read_text(encoding="utf-8"))
    before = {"nodes": len(data.get("nodes") or {}), "relations": len(data.get("relations") or {})}
    removed = prune_web_dict(data)
    report = {"status": "dry_run", "path": str(path), "before": before, "removed": removed}
    if not apply or not (removed["nodes"] or removed["relations"] or removed["category_entries"]):
        if apply:
            report["status"] = "nothing_to_prune"
        return report
    backup = path.with_suffix(".json.pre_recall_prune_backup")
    if not backup.exists():
        shutil.copy2(path, backup)
    data["timestamp"] = time.time()
    data["_checksum"] = _checksum(data)
    tmp = path.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)  # her own persistence writes indent=1
    os.replace(tmp, path)
    report.update({"status": "pruned", "backup": str(backup),
                   "after": {"nodes": len(data["nodes"]), "relations": len(data["relations"])}})
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--state-dir", default="aurora_state")
    ap.add_argument("--apply", action="store_true")
    print(json.dumps(run(**{"state_dir": ap.parse_args().state_dir, "apply": ap.parse_args().apply}), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

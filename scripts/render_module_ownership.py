"""Render docs/LAYER_MODULE_OWNERSHIP.md from docs/module_ownership.json.

docs/module_ownership.json is the one record of each covered module's layer
and function category. The markdown map is generated from it and never edited
by hand, so the two cannot disagree.

    python scripts/render_module_ownership.py          # rewrite the map
    python scripts/render_module_ownership.py --check  # exit 1 if it is stale

Reads and writes only those two files. Imports nothing from Aurora.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAPPING_PATH = os.path.join(ROOT, "docs", "module_ownership.json")
MAP_PATH = os.path.join(ROOT, "docs", "LAYER_MODULE_OWNERSHIP.md")


def _no_duplicate_keys(pairs):
    seen: Dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise ValueError("duplicate key in module_ownership.json: %s" % key)
        seen[key] = value
    return seen


def load_mapping(path: str = MAPPING_PATH) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh, object_pairs_hook=_no_duplicate_keys)


def render(mapping: Dict[str, Any]) -> str:
    cats = {c["id"]: c for c in mapping["categories"]}
    layer_names = {l["id"]: l["name"] for l in mapping["layers"]}
    modules = mapping["modules"]
    scope = mapping["scope"]
    out: List[str] = []
    add = out.append

    add("# Aurora Module Ownership Map (L1–L8)")
    add("")
    add("**Authors:** %s" % mapping["authors"])
    add("")
    add("<!-- Generated from docs/module_ownership.json by scripts/render_module_ownership.py. Do not edit by hand. -->")
    add("")
    add("This map gives each covered module its owning layer, where it has one, and a function category.")
    add("")
    add("The layers are the one architecture. The category is a second column over the same modules, for finding things; it never moves a file, changes an import or adds a package. Moving files would change the paths that her code lineage, function ids and fault records are keyed by, so modules stay where they are (decided 2026-11-18).")
    add("")
    add("The record is `docs/module_ownership.json`. Change a module's layer or category there, then run `python scripts/render_module_ownership.py`. The test `tests/test_layer_module_ownership_categories.py` fails if this file and the record disagree.")
    add("")

    add("## Coverage")
    add("")
    add("%s It lists %d modules." % (scope["statement"], len(modules)))
    add("")
    add("Covered: %s (skipping %s)." % (", ".join("`%s`" % g for g in scope["covers"]), ", ".join("`%s`" % s for s in scope["skips"])))
    add("")
    add("Not covered:")
    add("")
    add("| Path | What it holds |")
    add("|---|---|")
    for item in scope["not_covered"]:
        add("| `%s` | %s |" % (item["path"], item["what"]))
    add("")

    for layer in mapping["layers"]:
        lid = layer["id"]
        rows = [(p, m) for p, m in modules.items() if m["layer"] == lid]
        rows.sort(key=lambda r: (r[1]["layer_role"] not in ("layer file", "single runtime entrypoint"), r[0]))
        gone = [r for r in mapping["layer_records_without_file"] if r["layer"] == lid]
        if not rows and not gone:
            continue
        add("## %s" % ("Orchestrator" if lid == "orchestrator" else "%s (%s)" % (lid, layer_names[lid])))
        add("")
        add("| Module | Role | Category |")
        add("|---|---|---|")
        for path, m in rows:
            add("| `%s` | %s | %s |" % (path, m["layer_role"], cats[m["category"]]["name"]))
        for r in gone:
            add("| `%s` | %s | (file not on main) |" % (r["path"], r["layer_role"]))
        add("")
        if lid == "L8":
            add("State: `aurora_conversation_memory.json` and the state JSON artifacts are runtime persistence (L8).")
            add("")

    add("## Categories")
    add("")
    add("| Category | Holds | Modules |")
    add("|---|---|---|")
    for c in mapping["categories"]:
        n = sum(1 for m in modules.values() if m["category"] == c["id"])
        add("| %s | %s | %d |" % (c["name"], c["holds"], n))
    add("")

    reviewed = [(p, m) for p, m in sorted(modules.items()) if m["basis"] == "reviewed"]
    add("## Reviewed against what the code does")
    add("")
    add("Every module was screened for who imports it and whether it writes files. These %d were then read, because the screen showed duties beyond their name or because their name and their job differ. The rest keep the category their name and docstring gave them." % len(reviewed))
    add("")
    add("| Module | Category | Also | What it actually does |")
    add("|---|---|---|---|")
    for path, m in reviewed:
        also = ", ".join(cats[a]["name"] for a in m["also"]) or "–"
        add("| `%s` | %s | %s | %s |" % (path, cats[m["category"]]["name"], also, m["duties"]))
    add("")

    add("## Every module by category")
    add("")
    add("Layer is given where a layer section above names the module. Basis is `reviewed` or `name_and_docstring`.")
    add("")
    for c in mapping["categories"]:
        rows = sorted(p for p, m in modules.items() if m["category"] == c["id"])
        if not rows:
            continue
        add("### %s" % c["name"])
        add("")
        add("| Module | Layer | Basis |")
        add("|---|---|---|")
        for path in rows:
            m = modules[path]
            add("| `%s` | %s | %s |" % (path, m["layer"] or "", m["basis"]))
        add("")
    return "\n".join(out).rstrip("\n") + "\n"


def main(argv: List[str]) -> int:
    text = render(load_mapping())
    if "--check" in argv:
        with open(MAP_PATH, encoding="utf-8") as fh:
            if fh.read() != text:
                print("docs/LAYER_MODULE_OWNERSHIP.md is stale: run python scripts/render_module_ownership.py")
                return 1
        return 0
    with open(MAP_PATH, "w", encoding="utf-8") as fh:
        fh.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

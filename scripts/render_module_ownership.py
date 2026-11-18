"""Render docs/LAYER_MODULE_OWNERSHIP.md from docs/module_ownership.json.

docs/module_ownership.json is the one record of where every source file in
the repository sits. It is organised like her crystals:

    king quasi   the repository
    quasi        a domain (desktop Aurora, the phone app, the ACM, CI)
    higher order a subsystem inside a domain
    composite    files that import evidence joins inside one subsystem
    base         one source file

Domains, subsystems, layers and duties are declared by hand in the record.
Composites and the modules each test exercises are derived from the source
here, never declared, and the record stores what was derived so that the
knowledge graph can read it.

    python scripts/render_module_ownership.py                  # rewrite the map
    python scripts/render_module_ownership.py --update-derived # re-derive composites and exercises
    python scripts/render_module_ownership.py --check          # exit 1 if anything is stale

Reads source files as text and writes only the two docs files. Imports
nothing from Aurora.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

import ast
import json
import os
import re
import sys
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAPPING_PATH = os.path.join(ROOT, "docs", "module_ownership.json")
MAP_PATH = os.path.join(ROOT, "docs", "LAYER_MODULE_OWNERSHIP.md")

# A Python import of cv2 means the opencv package. The phone app's cv2.py is a
# shim that stands in for it on Android, so a bare `import cv2` is never read
# as an edge to that file.
_PY_NAMES_THAT_MEAN_A_PACKAGE = {"cv2"}


# ---------------------------------------------------------------- loading --

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


def dump_mapping(mapping: Dict[str, Any]) -> str:
    return json.dumps(mapping, indent=1, ensure_ascii=False) + "\n"


def scan(root: str, scope: Dict[str, Any]) -> Set[str]:
    """Every source file the scope covers, as repo-relative paths."""
    extensions = set(scope["source_extensions"])
    skip_dirs = set(scope["skip_dirs"])
    extra = tuple(scope["extra_files"])
    found: Set[str] = set()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in skip_dirs)
        for name in filenames:
            rel = os.path.relpath(os.path.join(dirpath, name), root).replace(os.sep, "/")
            if os.path.splitext(name)[1] in extensions or rel.startswith(extra):
                found.add(rel)
    return found


def _read(root: str, path: str) -> str:
    with open(os.path.join(root, path), encoding="utf-8", errors="replace") as fh:
        return fh.read()


# ------------------------------------------------------------ import edges --

def _py_dotted(path: str) -> str:
    name = path[:-3].replace("/", ".")
    return name[: -len(".__init__")] if name.endswith(".__init__") else name


def _py_imports(source: str, module: str, is_package: bool) -> List[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    pkg = module if is_package else (module.rsplit(".", 1)[0] if "." in module else "")
    names: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                parts = pkg.split(".") if pkg else []
                if node.level > 1:
                    parts = parts[: len(parts) - (node.level - 1)]
                base = ".".join(parts + ([base] if base else []))
            names.extend(base + "." + a.name if base else a.name for a in node.names)
            names.append(base)
    return [n for n in names if n]


def _resolver(names: Dict[str, str]):
    def resolve(name: str) -> Optional[str]:
        while name:
            if name in names:
                return names[name]
            name = name.rsplit(".", 1)[0] if "." in name else ""
        return None
    return resolve


def python_edges(root: str, files: Dict[str, Dict[str, Any]]) -> Dict[str, Set[str]]:
    """path -> paths it imports. Desktop files resolve by dotted path from the
    repo root; files in other domains resolve by module name inside their own
    folder, which is how Chaquopy and the ACM's native runner load them."""
    edges: Dict[str, Set[str]] = defaultdict(set)
    desktop = {_py_dotted(p): p for p, f in files.items() if p.endswith(".py") and f["domain"] == "desktop"}
    by_folder: Dict[str, Dict[str, str]] = defaultdict(dict)
    for p, f in files.items():
        stem = os.path.basename(p)[:-3]
        if p.endswith(".py") and f["domain"] != "desktop" and stem not in _PY_NAMES_THAT_MEAN_A_PACKAGE:
            by_folder[os.path.dirname(p)][stem] = p
    resolve_desktop = _resolver(desktop)
    # A desktop import that names no desktop module may name another domain's
    # module by its bare name (tests do this with the phone app's Python).
    stems: Dict[str, List[str]] = defaultdict(list)
    for folder in by_folder.values():
        for stem, p in folder.items():
            stems[stem].append(p)
    elsewhere = {stem: ps[0] for stem, ps in stems.items() if len(ps) == 1}
    for path, f in files.items():
        if not path.endswith(".py"):
            continue
        if f["domain"] == "desktop":
            resolve, module = resolve_desktop, _py_dotted(path)
        else:
            resolve, module = _resolver(by_folder[os.path.dirname(path)]), os.path.basename(path)[:-3]
        for name in _py_imports(_read(root, path), module, path.endswith("__init__.py")):
            hit = resolve(name)
            if hit is None and f["domain"] == "desktop":
                hit = elsewhere.get(name)
            if hit and hit != path:
                edges[path].add(hit)
    return edges


_DART_IMPORT = re.compile(r"""^\s*(?:import|export|part)\s+['"]([^'"]+)['"]""", re.M)


def dart_edges(root: str, files: Dict[str, Dict[str, Any]], package: str, lib_dir: str) -> Dict[str, Set[str]]:
    edges: Dict[str, Set[str]] = defaultdict(set)
    prefix = "package:%s/" % package
    for path in files:
        if not path.endswith(".dart"):
            continue
        for target in _DART_IMPORT.findall(_read(root, path)):
            if target.startswith(prefix):
                hit = "%s/%s" % (lib_dir, target[len(prefix):])
            elif ":" in target:
                continue
            else:
                hit = os.path.normpath(os.path.join(os.path.dirname(path), target)).replace(os.sep, "/")
            if hit in files and hit != path:
                edges[path].add(hit)
    return edges


_RUST_MOD = re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?mod\s+([A-Za-z_]\w*)\s*;", re.M)
_RUST_PATH = re.compile(r"\b(crate|super|self)((?:::[A-Za-z_]\w*)+)")


def _rust_crate_src(path: str) -> Optional[str]:
    parts = path.split("/")
    if "src" not in parts:
        return None
    i = len(parts) - 1 - parts[::-1].index("src")
    return "/".join(parts[: i + 1])


def _rust_children_dir(path: str) -> str:
    """The folder a Rust file's child modules live in."""
    d, base = os.path.dirname(path), os.path.basename(path)
    return d if base in ("main.rs", "lib.rs", "mod.rs") else "%s/%s" % (d, base[:-3])


def _rust_file_for(children_dir: str, segments: List[str], files: Dict[str, Any]) -> Optional[str]:
    """The deepest file that a path of module segments names, from children_dir."""
    best, d = None, children_dir
    for seg in segments:
        hit = next((c for c in ("%s/%s.rs" % (d, seg), "%s/%s/mod.rs" % (d, seg)) if c in files), None)
        if not hit:
            break
        best, d = hit, "%s/%s" % (d, seg)
    return best


def rust_edges(root: str, files: Dict[str, Dict[str, Any]]) -> Dict[str, Set[str]]:
    edges: Dict[str, Set[str]] = defaultdict(set)
    for path in files:
        if not path.endswith(".rs"):
            continue
        src = _rust_crate_src(path)
        if not src:
            continue
        text = _read(root, path)
        children = _rust_children_dir(path)
        for name in _RUST_MOD.findall(text):
            hit = _rust_file_for(children, [name], files)
            if hit:
                edges[path].add(hit)
        for anchor, tail in _RUST_PATH.findall(text):
            start = {"crate": src, "self": children}.get(anchor, os.path.dirname(children))
            hit = _rust_file_for(start, [s for s in tail.split("::") if s], files)
            if hit and hit != path:
                edges[path].add(hit)
    return edges


_IDENT = re.compile(r"\b[A-Z][A-Za-z0-9_]*\b")


def jvm_edges(root: str, files: Dict[str, Dict[str, Any]]) -> Dict[str, Set[str]]:
    """Kotlin and Java: a file that names another file's class (its file stem)
    in the same folder depends on it."""
    edges: Dict[str, Set[str]] = defaultdict(set)
    jvm = [p for p in files if p.endswith((".kt", ".java"))]
    by_stem = {(os.path.dirname(p), os.path.splitext(os.path.basename(p))[0]): p for p in jvm}
    for path in jvm:
        text = re.sub(r"//[^\n]*|/\*.*?\*/", "", _read(root, path), flags=re.S)
        for ident in set(_IDENT.findall(text)):
            hit = by_stem.get((os.path.dirname(path), ident))
            if hit and hit != path:
                edges[path].add(hit)
    return edges


def all_edges(root: str, mapping: Dict[str, Any]) -> Dict[str, Set[str]]:
    files = mapping["files"]
    dart = mapping["evidence_rules"]["dart_package"]
    merged: Dict[str, Set[str]] = defaultdict(set)
    for part in (
        python_edges(root, files),
        dart_edges(root, files, dart["name"], dart["lib_dir"]),
        rust_edges(root, files),
        jvm_edges(root, files),
    ):
        for a, bs in part.items():
            merged[a] |= bs
    return merged


# ---------------------------------------------------------------- derived --

def derive(root: str, mapping: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Optional[str]], Dict[str, List[str]]]:
    """Composites, each file's composite, and the files each test exercises.

    A composite is a connected group of two or more files in one subsystem,
    joined by import edges that stay inside that subsystem. A file with no
    such edge stays a base file. Nothing here is declared by hand.
    """
    files = mapping["files"]
    edges = all_edges(root, mapping)
    neighbours: Dict[str, Set[str]] = defaultdict(set)
    for a, bs in edges.items():
        for b in bs:
            if files[a]["subsystem"] == files[b]["subsystem"]:
                neighbours[a].add(b)
                neighbours[b].add(a)

    groups: List[List[str]] = []
    seen: Set[str] = set()
    for start in sorted(neighbours):
        if start in seen:
            continue
        group, stack = [], [start]
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            group.append(node)
            stack.extend(neighbours[node] - seen)
        groups.append(sorted(group))

    support = {
        frozenset(s["members"]): s["status"]
        for s in mapping.get("graph_evidence", {}).get("composite_support", [])
    }
    composites: Dict[str, Any] = {}
    candidates: Dict[str, Any] = {}
    membership: Dict[str, Optional[str]] = {p: None for p in files}
    by_subsystem: Dict[str, List[List[str]]] = defaultdict(list)
    for g in groups:
        by_subsystem[files[g[0]]["subsystem"]].append(g)
    order = [s["id"] for s in mapping["subsystems"]]
    for subsystem in sorted(by_subsystem, key=order.index):
        for i, g in enumerate(sorted(by_subsystem[subsystem], key=lambda g: (-len(g), g[0])), 1):
            cid = "%s.%d" % (subsystem, i)
            members = set(g)
            hub = sorted(g, key=lambda p: (-len(neighbours[p] & members), p))[0]
            entry = {
                "domain": files[g[0]]["domain"],
                "subsystem": subsystem,
                "hub": hub,
                "members": g,
                "links": sorted([a, b] for a in g for b in neighbours[a] if b in members and a < b),
                "support": support.get(frozenset(g), "unchecked"),
            }
            if entry["support"] == "import_only":
                candidates[cid] = entry
                continue
            composites[cid] = entry
            for p in g:
                membership[p] = cid

    exercises = {
        p: sorted(b for b in edges.get(p, ()) if files[b]["subsystem"] != "tests")
        for p, f in sorted(files.items()) if f["subsystem"] == "tests"
    }
    return composites, candidates, membership, exercises


def apply_derived(root: str, mapping: Dict[str, Any]) -> Dict[str, Any]:
    composites, candidates, membership, exercises = derive(root, mapping)
    mapping["composites"] = composites
    mapping["composite_candidates"] = candidates
    for p, f in mapping["files"].items():
        f["composite"] = membership[p]
        if f["subsystem"] == "tests":
            f["exercises"] = exercises[p]
        else:
            f.pop("exercises", None)
    return mapping


# ---------------------------------------------------------------- render --

def render(mapping: Dict[str, Any]) -> str:
    subs = {s["id"]: s for s in mapping["subsystems"]}
    layer_names = {l["id"]: l["name"] for l in mapping["layers"]}
    files = mapping["files"]
    composites = mapping["composites"]
    scope = mapping["scope"]
    out: List[str] = []
    add = out.append

    add("# Aurora Ownership Map")
    add("")
    add("**Authors:** %s" % mapping["authors"])
    add("")
    add("<!-- Generated from docs/module_ownership.json by scripts/render_module_ownership.py. Do not edit by hand. -->")
    add("")
    add("This map places every source file in the repository on one ladder, the way her crystals are built. The layers (L0 to L8) stay the one architecture of desktop Aurora; the ladder is a view over the files for finding things, and it never moves a file, changes an import or adds a package. Moving files would change the paths that her code lineage, function ids and fault records are keyed by, so files stay where they are (decided 2026-11-18).")
    add("")
    add("| Order | Holds |")
    add("|---|---|")
    for rung in mapping["ladder"]:
        add("| %s | %s |" % (rung["name"], rung["holds"]))
    add("")
    add("The record is `docs/module_ownership.json`. Change a domain, subsystem, layer or duty there, then run `python scripts/render_module_ownership.py --update-derived` and `python scripts/render_module_ownership.py`. Composites and the files each test exercises are derived from the source, never typed in. The test `tests/test_layer_module_ownership_categories.py` fails if this file, the record and the source disagree.")
    add("")

    add("## Coverage")
    add("")
    add("%s It lists %d files." % (scope["statement"], len(files)))
    add("")
    add("Covered: files ending in %s, and files under %s, skipping folders named %s." % (
        ", ".join("`%s`" % e for e in scope["source_extensions"]),
        ", ".join("`%s`" % e for e in scope["extra_files"]),
        ", ".join("`%s`" % s for s in scope["skip_dirs"])))
    add("")
    add("Not covered:")
    add("")
    add("| Path | What it holds |")
    add("|---|---|")
    for item in scope["not_covered"]:
        add("| `%s` | %s |" % (item["path"], item["what"]))
    add("")

    add("## King quasi: %s" % mapping["king_quasi"]["name"])
    add("")
    add("| Quasi (domain) | Holds | Subsystems | Composites | Files |")
    add("|---|---|---|---|---|")
    for d in mapping["domains"]:
        n_sub = sum(1 for s in mapping["subsystems"] if s["domain"] == d["id"])
        n_comp = sum(1 for c in composites.values() if c["domain"] == d["id"])
        n_files = sum(1 for f in files.values() if f["domain"] == d["id"])
        add("| %s | %s | %d | %d | %d |" % (d["name"], d["holds"], n_sub, n_comp, n_files))
    add("")

    for d in mapping["domains"]:
        add("## Quasi: %s" % d["name"])
        add("")
        add("| Higher order (subsystem) | Holds | Composites | Files in composites | Base files |")
        add("|---|---|---|---|---|")
        for s in mapping["subsystems"]:
            if s["domain"] != d["id"]:
                continue
            n_comp = sum(1 for c in composites.values() if c["subsystem"] == s["id"])
            in_comp = sum(1 for f in files.values() if f["subsystem"] == s["id"] and f["composite"])
            base = sum(1 for f in files.values() if f["subsystem"] == s["id"] and not f["composite"])
            add("| %s | %s | %d | %d | %d |" % (s["name"], s["holds"], n_comp, in_comp, base))
        add("")

    add("## Desktop layers (L0 to L8)")
    add("")
    for layer in mapping["layers"]:
        lid = layer["id"]
        rows = [(p, f) for p, f in files.items() if f["layer"] == lid]
        rows.sort(key=lambda r: (r[1]["layer_role"] not in ("layer file", "single runtime entrypoint"), r[0]))
        gone = [r for r in mapping["layer_records_without_file"] if r["layer"] == lid]
        if not rows and not gone:
            continue
        add("### %s" % ("Orchestrator" if lid == "orchestrator" else "%s (%s)" % (lid, layer_names[lid])))
        add("")
        add("| Module | Role | Subsystem |")
        add("|---|---|---|")
        for path, f in rows:
            add("| `%s` | %s | %s |" % (path, f["layer_role"], subs[f["subsystem"]]["name"]))
        for r in gone:
            add("| `%s` | %s | (file not on main) |" % (r["path"], r["layer_role"]))
        add("")
        if lid == "L8":
            add("State: `aurora_conversation_memory.json` and the state JSON artifacts are runtime persistence (L8).")
            add("")

    reviewed = [(p, f) for p, f in sorted(files.items()) if f["basis"] == "reviewed"]
    add("## Reviewed against what the code does")
    add("")
    add("Every Python module in desktop Aurora's runtime was screened for who imports it and whether it writes files. These %d files were then read, because the screen showed duties beyond their name or because their name and their job differ." % len(reviewed))
    add("")
    add("| File | Subsystem | Also | What it actually does |")
    add("|---|---|---|---|")
    for path, f in reviewed:
        also = ", ".join(subs[a]["name"] for a in f["also"]) or "–"
        add("| `%s` | %s | %s | %s |" % (path, subs[f["subsystem"]]["name"], also, f["duties"]))
    add("")

    add("## Composites")
    add("")
    add(mapping["evidence_rules"]["composite_rule"])
    add("")
    add("Support is the knowledge graph's verdict: `supported` and `partly_supported` mean calls, data flow, spawns or shared state join the files as well as imports; `unchecked` means the graph has not seen this group yet.")
    add("")
    add("| Composite | Subsystem | Hub | Files | Support |")
    add("|---|---|---|---|---|")
    for cid, c in composites.items():
        add("| `%s` | %s | `%s` | %d | %s |" % (cid, subs[c["subsystem"]]["name"], c["hub"], len(c["members"]), c["support"]))
    add("")
    candidates = mapping.get("composite_candidates", {})
    if candidates:
        add("### Not promoted: imports only")
        add("")
        add("Imports join these files, but the knowledge graph found no call, flow, spawn or shared state between them, so they stay base files.")
        add("")
        add("| Candidate | Subsystem | Files |")
        add("|---|---|---|")
        for cid, c in candidates.items():
            add("| `%s` | %s | %s |" % (cid, subs[c["subsystem"]]["name"], ", ".join("`%s`" % m for m in c["members"])))
        add("")

    evidence = mapping.get("graph_evidence")
    if evidence:
        add("## Cross-domain links (candidates, not promoted)")
        add("")
        add("%s %s" % (evidence["note"], evidence["source"]))
        add("")
        add("| Files | Domains | Edges the graph found |")
        add("|---|---|---|")
        for link in evidence["cross_domain_links"]:
            a, b = link["files"]
            kinds = ", ".join("%s %d" % (k, v) for k, v in sorted(link["kinds"].items()))
            add("| `%s` and `%s` | %s and %s | %s |" % (a, b, files[a]["domain"], files[b]["domain"], kinds))
        add("")

    add("## Every file by domain and subsystem")
    add("")
    add("Composite is blank for a base file that no import joins to another file in its subsystem. Layer is given for desktop modules a layer section names.")
    add("")
    for d in mapping["domains"]:
        for s in mapping["subsystems"]:
            if s["domain"] != d["id"]:
                continue
            rows = sorted(p for p, f in files.items() if f["subsystem"] == s["id"])
            if not rows:
                continue
            add("### %s / %s" % (d["name"], s["name"]))
            add("")
            add("| File | Composite | Layer | Basis |")
            add("|---|---|---|---|")
            for path in rows:
                f = files[path]
                add("| `%s` | %s | %s | %s |" % (path, f["composite"] or "", f["layer"] or "", f["basis"]))
            add("")
    return "\n".join(out).rstrip("\n") + "\n"


# ------------------------------------------------------------------ main --

def main(argv: List[str]) -> int:
    mapping = load_mapping()
    if "--update-derived" in argv:
        mapping = apply_derived(ROOT, mapping)
        with open(MAPPING_PATH, "w", encoding="utf-8") as fh:
            fh.write(dump_mapping(mapping))
        return 0
    if "--check" in argv:
        stale = []
        if apply_derived(ROOT, json.loads(json.dumps(mapping))) != mapping:
            stale.append("docs/module_ownership.json derived parts (run with --update-derived)")
        with open(MAP_PATH, encoding="utf-8") as fh:
            if fh.read() != render(mapping):
                stale.append("docs/LAYER_MODULE_OWNERSHIP.md (run with no flags)")
        for s in stale:
            print("stale: %s" % s)
        return 1 if stale else 0
    with open(MAP_PATH, "w", encoding="utf-8") as fh:
        fh.write(render(mapping))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

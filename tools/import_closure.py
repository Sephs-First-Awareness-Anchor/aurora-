# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Static import closure of Aurora modules, by size: what a boot of the given entry modules can load (stdlib only; reads source, runs nothing).

`python tools/import_closure.py aurora_bridge aurora_surface_daemon` prints, for the entry set: the modules reached through top-level imports (loaded at import
time) and those only reached through imports inside functions (loaded when that code runs), with their source bytes.
"""
from __future__ import annotations

import ast
import os
import sys
from typing import Dict, Iterable, Set, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def module_path(name: str):
    parts = name.split(".")
    for cand in (os.path.join(ROOT, *parts) + ".py", os.path.join(ROOT, *parts, "__init__.py")):
        if os.path.isfile(cand):
            return cand
    return None


def imports_of(path: str) -> Tuple[Set[str], Set[str]]:
    """(top-level imports, imports only inside functions/classes bodies' functions)."""
    try:
        tree = ast.parse(open(path, "r", encoding="utf-8").read())
    except (OSError, SyntaxError, ValueError):
        return set(), set()
    top: Set[str] = set()
    lazy: Set[str] = set()

    def visit(node, in_func):
        for ch in ast.iter_child_nodes(node):
            f = in_func or isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef))
            if isinstance(ch, ast.Import):
                (lazy if f else top).update(a.name for a in ch.names)
            elif isinstance(ch, ast.ImportFrom) and ch.module and ch.level == 0:
                tgt = lazy if f else top
                tgt.add(ch.module)
                tgt.update(f"{ch.module}.{a.name}" for a in ch.names)
            visit(ch, f)
    visit(tree, False)
    return top, lazy


def closure(entries: Iterable[str], lazy: bool = True) -> Dict[str, int]:
    seen: Dict[str, int] = {}
    todo = list(entries)
    while todo:
        name = todo.pop()
        p = module_path(name)
        if name in seen or p is None:
            continue
        seen[name] = os.path.getsize(p)
        top, lz = imports_of(p)
        for m in (top | lz if lazy else top):
            parent = m.rsplit(".", 1)[0] if "." in m else m
            for cand in {m, parent}:
                if cand not in seen and module_path(cand):
                    todo.append(cand)
        for i in range(1, len(name.split("."))):                       # a package's __init__ loads first
            pkg = ".".join(name.split(".")[:i])
            if pkg not in seen and module_path(pkg):
                todo.append(pkg)
    return seen


def main(argv=None) -> int:
    entries = list(argv if argv is not None else sys.argv[1:])
    if not entries:
        print(__doc__)
        return 2
    top = closure(entries, lazy=False)
    full = closure(entries, lazy=True)
    kb = lambda d: round(sum(d.values()) / 1e6, 2)
    print(f"entries: {', '.join(entries)}")
    print(f"loaded at import (top-level imports): {len(top)} modules, {kb(top)} MB")
    print(f"reachable including imports inside functions: {len(full)} modules, {kb(full)} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

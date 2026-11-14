# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Map what ConstraintGenealogyLogger.observe actually does, from the code, not from names.

For each method reached from `_observe_impl` (directly, one level deep through self-calls) it lists:
  * the `self.<attr>` it WRITES (assign / augassign / subscript-assign / .append/.update/.add/.pop/...)
  * the `self.<attr>` it READS
and then, for every written attribute, who OUTSIDE constraint_genealogy.py reads it (a grep for
`.attr` across the repo).  The output is the evidence for "does active cognition need this result now?":
an operation whose writes nothing outside reads is a candidate for deferral; one whose writes are read by
live-turn code is not, until a projection serves those consumers.

    python3 scripts/audit_genealogy.py [--json]
"""
from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GEN = ROOT / "aurora_internal" / "constraint_genealogy.py"
MUTATORS = {"append", "extend", "update", "add", "pop", "popitem", "clear", "setdefault", "remove", "discard",
            "insert", "appendleft", "popleft", "sort", "__setitem__"}


def _attr_of_self(node):
    """`self.x` -> "x" (also the root of self.x[...] / self.x.y)."""
    while isinstance(node, (ast.Subscript, ast.Attribute)):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "self":
            return node.attr
        node = node.value
    return None


def method_facts(fn: ast.FunctionDef):
    writes, reads, calls = set(), set(), set()
    for n in ast.walk(fn):
        if isinstance(n, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            targets = n.targets if isinstance(n, ast.Assign) else [n.target]
            for t in targets:
                for sub in ast.walk(t):
                    a = _attr_of_self(sub)
                    if a and isinstance(getattr(sub, "ctx", None), ast.Store):
                        writes.add(a)
        elif isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Attribute):
                if isinstance(f.value, ast.Name) and f.value.id == "self":
                    calls.add(f.attr)
                a = _attr_of_self(f.value)
                if a and f.attr in MUTATORS:
                    writes.add(a)
        elif isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == "self":
            if isinstance(n.ctx, ast.Load):
                reads.add(n.attr)
    return writes, reads, calls


def external_readers(attr: str):
    """Files other than constraint_genealogy.py that mention `.attr` (word-bounded)."""
    pat = r"\.%s\b" % re.escape(attr)
    out = subprocess.run(["grep", "-rlE", "--include=*.py", pat, str(ROOT)], capture_output=True, text=True).stdout
    files = sorted({Path(p).name for p in out.split() if Path(p) != GEN and "/tests/" not in p and "__pycache__" not in p})
    return files


def main(argv=None) -> int:
    tree = ast.parse(GEN.read_text(encoding="utf-8"))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ConstraintGenealogyLogger")
    methods = {n.name: n for n in cls.body if isinstance(n, ast.FunctionDef)}
    facts = {name: method_facts(fn) for name, fn in methods.items()}
    root = "_observe_impl"
    first = sorted(facts[root][2] & set(methods))
    report = []
    for name in first:
        w, r, c = facts[name]
        deeper = sorted(c & set(methods) - {name})
        dw = set(w)
        for d in deeper:
            dw |= facts[d][0]
        report.append({"method": name, "line": methods[name].lineno, "calls_inside": deeper,
                       "writes": sorted(dw), "reads": sorted(r)})
    seen = {}
    for item in report:
        for a in item["writes"]:
            if a not in seen:
                seen[a] = external_readers(a)
    for item in report:
        item["read_outside"] = {a: seen[a] for a in item["writes"] if seen[a]}
        item["private_only"] = [a for a in item["writes"] if not seen[a]]
    if "--json" in (argv or sys.argv[1:]):
        print(json.dumps(report, indent=1))
        return 0
    print(f"{GEN.name}: _observe_impl calls {len(first)} methods of its own class (writes include one level below)\n")
    for item in report:
        print(f"{item['method']}  (line {item['line']})")
        print(f"   writes   : {', '.join(item['writes']) or '-'}")
        ro = item["read_outside"]
        print("   read by other modules: " + (("; ".join(f"{a}: {','.join(v[:4])}{'...' if len(v) > 4 else ''}" for a, v in ro.items())) or "nothing (its writes are private to genealogy)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

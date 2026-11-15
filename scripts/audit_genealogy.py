# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Map what ConstraintGenealogyLogger.observe actually does, from the code, not from names.

For each method reached from `_observe_impl` (directly, one level deep through self-calls) it lists the
`self.<attr>` it WRITES.  For every written attribute it then finds who reads it OUTSIDE
constraint_genealogy.py, by walking every module's syntax tree (not a text search):

  * attribute loads           `<receiver>.attr`
  * string-named reads        `getattr(<receiver>, "attr")`
  * reads through the logger's own PUBLIC methods: a public method that reads (directly or through the
    private methods it calls) a written attribute, and every call to that method from another module

Each outside reference is reported as file:line with its receiver text, and classified:
    named      the receiver text names genealogy (`genealogy`, `self.genealogy`, `systems["genealogy"]`, ...)
    unnamed    the same attribute name on a receiver that does not say what it is -- unconfirmed: it may be
               another class's attribute of the same name, or genealogy under another variable name.  Read
               these by hand before deciding a result is safe to defer.

Stage 1 searched with `grep` for `.attr` (so a same-named attribute on any object matched, and the reads
through public methods and getattr strings were missed) and did not name aurora_runtime.py; this audit
covers every module and reports each reference's line.  What it still cannot see: reads through a variable
that was assigned from genealogy and passed through several calls, and files read by other processes
(`persisted_files` lists the files the logger writes so they can be searched for by name).

    python3 scripts/audit_genealogy.py [--json] [--only METHOD]
"""
from __future__ import annotations

import ast
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple

ROOT = Path(__file__).resolve().parent.parent
GEN = ROOT / "aurora_internal" / "constraint_genealogy.py"
MUTATORS = {"append", "extend", "update", "add", "pop", "popitem", "clear", "setdefault", "remove", "discard",
            "insert", "appendleft", "popleft", "sort", "__setitem__"}
SKIP_DIRS = {"__pycache__", "tests", ".git", "node_modules", "venv", ".venv", "aurora_state"}


def _attr_of_self(node):
    """`self.x` -> "x" (also the root of self.x[...] / self.x.y)."""
    while isinstance(node, (ast.Subscript, ast.Attribute)):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "self":
            return node.attr
        node = node.value
    return None


def method_facts(fn: ast.FunctionDef) -> Tuple[Set[str], Set[str], Set[str]]:
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


def reachable(name: str, facts: Dict[str, Tuple[Set[str], Set[str], Set[str]]]) -> Set[str]:
    """`name` and every method of the class it calls, transitively."""
    seen, stack = set(), [name]
    while stack:
        cur = stack.pop()
        if cur in seen or cur not in facts:
            continue
        seen.add(cur)
        stack.extend(facts[cur][2])
    return seen


def public_readers(attrs: Iterable[str], facts: Dict[str, Tuple[Set[str], Set[str], Set[str]]]) -> Dict[str, List[str]]:
    """{attr: [public methods that read it, directly or through the private methods they call]}

    A method from which `_observe_impl` is reachable (observe, the register_* entry points that call it) is
    the WRITE path reading its own state, not a consumer of the result: it is left out."""
    out: Dict[str, List[str]] = defaultdict(list)
    attrs = set(attrs)
    for name in facts:
        if name.startswith("_") or "_observe_impl" in reachable(name, facts):
            continue
        read: Set[str] = set()
        for m in reachable(name, facts):
            read |= facts[m][1]
        for a in attrs & read:
            out[a].append(name)
    return {a: sorted(v) for a, v in out.items()}


def _repo_modules() -> List[Path]:
    files = []
    for p in ROOT.rglob("*.py"):
        parts = set(p.relative_to(ROOT).parts)
        if parts & SKIP_DIRS or p == GEN:
            continue
        files.append(p)
    return sorted(files)


def _src(node: ast.AST) -> str:
    try:
        return ast.unparse(node)[:70]
    except Exception:
        return "?"


def classify(receiver: str) -> str:
    return "named" if "genealogy" in receiver.lower() else "unnamed"


def outside_references(attrs: Set[str], methods: Set[str]) -> Dict[str, List[Dict[str, Any]]]:
    """Every reference to a written attribute (attribute load / getattr string) or a public method call."""
    refs: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for path in _repo_modules():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        rel = str(path.relative_to(ROOT))
        for n in ast.walk(tree):
            if isinstance(n, ast.Attribute) and isinstance(n.ctx, ast.Load):
                if n.attr in attrs:
                    r = _src(n.value)
                    refs[n.attr].append({"file": rel, "line": n.lineno, "via": "attribute", "receiver": r,
                                         "class": classify(r)})
                elif n.attr in methods:
                    r = _src(n.value)
                    refs[n.attr].append({"file": rel, "line": n.lineno, "via": "method", "receiver": r,
                                         "class": classify(r)})
            elif (isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "getattr"
                  and len(n.args) >= 2 and isinstance(n.args[1], ast.Constant) and isinstance(n.args[1].value, str)
                  and n.args[1].value in attrs):
                r = _src(n.args[0])
                refs[n.args[1].value].append({"file": rel, "line": n.lineno, "via": "getattr", "receiver": r,
                                              "class": classify(r)})
    return refs


def persisted_files(tree: ast.AST) -> List[str]:
    """File names the logger writes (string constants ending .json / .jsonl)."""
    found = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)
             and re.fullmatch(r"[\w./-]+\.jsonl?", n.value)}
    return sorted(found)


def analyze() -> Dict[str, Any]:
    tree = ast.parse(GEN.read_text(encoding="utf-8"))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ConstraintGenealogyLogger")
    methods = {n.name: n for n in cls.body if isinstance(n, ast.FunctionDef)}
    facts = {name: method_facts(fn) for name, fn in methods.items()}
    root = "_observe_impl"
    first = sorted(facts[root][2] & set(methods))
    items = []
    all_written: Set[str] = set()
    for name in first:
        w, r, c = facts[name]
        deeper = sorted(c & set(methods) - {name})
        dw = set(w)
        for d in deeper:
            dw |= facts[d][0]
        items.append({"method": name, "line": methods[name].lineno, "calls_inside": deeper,
                      "writes": sorted(dw), "reads": sorted(r)})
        all_written |= dw
    pub = public_readers(all_written, facts)
    public_names = {m for ms in pub.values() for m in ms}
    refs = outside_references(all_written, public_names)
    for item in items:
        item["read_outside"] = {}
        item["read_through_public_methods"] = {}
        for a in item["writes"]:
            direct = [x for x in refs.get(a, []) if x["via"] in ("attribute", "getattr")]
            if direct:
                item["read_outside"][a] = direct
            via = {}
            for m in pub.get(a, []):
                calls = [x for x in refs.get(m, []) if x["via"] == "method"]
                if calls:
                    via[m] = calls
            if via:
                item["read_through_public_methods"][a] = via
        item["private_only"] = [a for a in item["writes"] if a not in item["read_outside"]
                                and a not in item["read_through_public_methods"]]
    return {"observe_calls": first, "methods": items, "persisted_files": persisted_files(tree),
            "modules_scanned": len(_repo_modules())}


def _summ(refs: List[Dict[str, Any]]) -> str:
    named = [x for x in refs if x["class"] == "named"]
    unnamed = [x for x in refs if x["class"] != "named"]
    files = lambda xs: sorted({x["file"] for x in xs})
    bits = []
    if named:
        bits.append(f"named in {', '.join(files(named)[:5])}{'...' if len(files(named)) > 5 else ''} ({len(named)} refs)")
    if unnamed:
        bits.append(f"{len(unnamed)} unconfirmed (same name, receiver unclear) in {len(files(unnamed))} files")
    return "; ".join(bits)


def main(argv=None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    report = analyze()
    if "--only" in args:
        want = args[args.index("--only") + 1]
        report["methods"] = [m for m in report["methods"] if m["method"] == want]
    if "--json" in args:
        print(json.dumps(report, indent=1))
        return 0
    print(f"{GEN.name}: _observe_impl calls {len(report['observe_calls'])} methods of its own class "
          f"(writes include one level below); {report['modules_scanned']} modules scanned by syntax tree\n")
    for item in report["methods"]:
        print(f"{item['method']}  (line {item['line']})")
        print(f"   writes   : {', '.join(item['writes']) or '-'}")
        for a, refs in item["read_outside"].items():
            print(f"   read outside, {a}: {_summ(refs)}")
        by_method: Dict[str, List[Any]] = defaultdict(lambda: [[], []])
        for a, via in item["read_through_public_methods"].items():
            for m, refs in via.items():
                by_method[m][0].append(a)
                by_method[m][1] = refs
        for m, (attrs_read, refs) in sorted(by_method.items()):
            print(f"   read through public {m}() (reads {', '.join(attrs_read)}): {_summ(refs)}")
        if item["private_only"]:
            print(f"   private to genealogy: {', '.join(item['private_only'])}")
    print("\nfiles the logger writes (search other processes for these names): " + ", ".join(report["persisted_files"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
# Usage: python3 scripts/map_phrase_routes.py aurora.py phrase_routes.json
"""Map top-level aurora.py functions that hold English phrase lists, and
whether each is reachable from _run_live_response_turn by name."""
import ast, sys, json, collections
src = open(sys.argv[1]).read()
tree = ast.parse(src)
funcs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
def phrase_literals(fn):
    lits = []
    for node in ast.walk(fn):
        if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
            strs = [e.value for e in node.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]
            # phrase list = >=3 lowercase word-ish strings, mostly letters/spaces
            words = [s for s in strs if s and s == s.lower() and sum(c.isalpha() or c in " '?" for c in s) >= 0.8*len(s)]
            if len(words) >= 3:
                lits.extend(words)
    return lits
def calls(fn):
    out = set()
    for node in ast.walk(fn):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in funcs:
            out.add(node.func.id)
    return out
graph = {name: calls(fn) for name, fn in funcs.items()}
# reachability from the live turn
seen, stack = set(), ["_run_live_response_turn"]
depth = {"_run_live_response_turn": 0}
while stack:
    cur = stack.pop()
    if cur in seen: continue
    seen.add(cur)
    for nxt in graph.get(cur, ()):
        if nxt not in depth: depth[nxt] = depth[cur] + 1
        stack.append(nxt)
callers = collections.defaultdict(set)
for a, bs in graph.items():
    for b in bs: callers[b].add(a)
rows = []
for name, fn in funcs.items():
    lits = phrase_literals(fn)
    if len(lits) < 8: continue
    rows.append({
        "function": name, "line": fn.lineno, "phrases": len(lits),
        "on_turn_path": name in seen, "depth": depth.get(name),
        "callers": len(callers[name]), "returns_bool": any(isinstance(n, ast.Return) and isinstance(getattr(n,'value',None), (ast.Call, ast.Compare, ast.BoolOp)) for n in ast.walk(fn)),
        "sample": lits[:6],
    })
rows.sort(key=lambda r: (not r["on_turn_path"], -r["phrases"]))
json.dump(rows, open(sys.argv[2], "w"), indent=1)
print(len(rows), "functions with >=8 phrase literals;", sum(r["on_turn_path"] for r in rows), "reachable from the live turn")
for r in rows:
    print(f'{r["function"]:55s} L{r["line"]:<6} n={r["phrases"]:<4} turn={str(r["on_turn_path"])[0]} d={r["depth"]} callers={r["callers"]}  {r["sample"][:4]}')

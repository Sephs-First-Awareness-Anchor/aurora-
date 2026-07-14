"""
aurora_flow_audit.py
====================
Toroidal Circulation Layer — empirical verdict audit.

Runs the three tests that decide whether Aurora's constraint space is
a torus (periodic, circulating) or a staircase (depth-ordered,
gradient-only), using only her real persisted data:

  TEST 1 — FOSSIL RECORD (aurora_genealogy/*.json)
    Directed axis transitions parsed from NC:u>v parent notation.
    Antisymmetric decomposition + directed cycle search.

  TEST 2 — BEDROCK (aurora_manifold_directory, all 125 noncomp grids)
    25×25 accountability_weight grids per manifold.
    Flow = G − Gᵀ; 3-cycle curl detection in the positive-flow digraph.

  TEST 3 — LIVED TIME (aurora_state/surface_pressure_log.jsonl)
    Timestamp-ordered surface pressure events (count grows with her
    lived history — see the generated header when this runs). Inter-axis
    flux from consecutive expected_axes activations, weighted by
    surface_score. Antisymmetric decomposition + DFS cycle search
    up to length 5 (the full X→…→A→X loop).

Numbers printed by past runs of this audit are history, not a fixed
result -- the tree and her lived record both keep moving. Run this
script directly for current values; do not cite old console output (or
any docstring elsewhere that quotes it) as present truth.

Circulation is the signature that matters: closed positive-flow loops
cannot be produced by any gradient (source/sink) field. If loops exist
only in TEST 3, the toroidal layer must be built on temporal deltas,
never on static grids.

Method note: detection is basis-free (antisymmetric decomposition of
observed flow). Harmonic modes h_mn = e^(i(mφ+nθ)) remain valid as a
*classifier* of flow shapes found here, but assuming periodicity in
the detector itself would manufacture seam energy at the A→X cost
cliff (SHIFT_COST A:150 → X:1).

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple

AXES = ("X", "T", "N", "B", "A")
DIMS = ("POLARITY", "MAGNITUDE", "OPERATOR", "COST", "DIFFERENCE")
IDX = {(a, d): i * 5 + j for i, a in enumerate(AXES) for j, d in enumerate(DIMS)}

ROOT = os.path.dirname(os.path.abspath(__file__))
GENEALOGY_DIR = os.path.join(ROOT, "aurora_genealogy")
MANIFOLD_DIR = os.path.join(ROOT, "aurora_manifold_directory")
SURFACE_LOG = os.path.join(ROOT, "aurora_state", "surface_pressure_log.jsonl")

_PAIR_RE = re.compile(r"NC:([XTNBA])>([XTNBA])")


# ── shared machinery ──────────────────────────────────────────────────────────

def antisymmetric(F: Dict[Tuple[str, str], float],
                  nodes: Tuple[str, ...]) -> Dict[Tuple[str, str], float]:
    """A[u→v] = F[u→v] − F[v→u]. Positive entries are net flow edges."""
    return {(u, v): F.get((u, v), 0.0) - F.get((v, u), 0.0)
            for u in nodes for v in nodes}


def find_cycles(A: Dict[Tuple[str, str], float], nodes: Tuple[str, ...],
                eps: float, max_len: int = 5) -> List[Tuple[Tuple[str, ...], float]]:
    """All directed cycles (length 3..max_len) in the positive-flow
    digraph, each scored by its bottleneck (min edge) flow. Rotationally
    deduped by canonical start node."""
    edges: Dict[str, Dict[str, float]] = defaultdict(dict)
    for (u, v), f in A.items():
        if f > eps:
            edges[u][v] = f
    out: List[Tuple[Tuple[str, ...], float]] = []

    def dfs(start: str, node: str, path: List[str], minw: float) -> None:
        if len(path) > max_len:
            return
        for nxt, w in edges.get(node, {}).items():
            if nxt == start and len(path) >= 3:
                out.append((tuple(path), min(minw, w)))
            elif nxt not in path:
                dfs(start, nxt, path + [nxt], min(minw, w))

    for s in list(edges):
        dfs(s, s, [s], float("inf"))
    deduped = [c for c in out if c[0][0] == min(c[0])]
    deduped.sort(key=lambda c: -c[1])
    return deduped


def flow_ratio(F: Dict[Tuple[str, str], float],
               A: Dict[Tuple[str, str], float],
               nodes: Tuple[str, ...]) -> Tuple[float, float, float]:
    order = {n: i for i, n in enumerate(nodes)}
    traffic = sum(v for (u, w), v in F.items() if u != w)
    net = sum(abs(f) for (u, v), f in A.items() if order[u] < order[v])
    return traffic, net, (net / traffic if traffic else 0.0)


def print_matrix(A: Dict[Tuple[str, str], float],
                 nodes: Tuple[str, ...], fmt: str = "8.2f") -> None:
    print("      " + "".join(f"{n:>8}" for n in nodes))
    for u in nodes:
        print(f"  {u} →" + "".join(f"{A[(u, v)]:>{fmt.split('.')[0][0:]}{'.'+fmt.split('.')[1] if '.' in fmt else ''}f}"
                                   if False else f"{A[(u, v)]:>8.2f}" for v in nodes))


# ── TEST 1: fossil record ─────────────────────────────────────────────────────

def test_fossil_record() -> None:
    print("=" * 68)
    print("TEST 1 — GENEALOGY FOSSIL RECORD (axis-level transitions)")
    print("=" * 68)
    trans: Counter = Counter()
    for fname in ("links.json", "abilities.json", "pair_stats.json"):
        path = os.path.join(GENEALOGY_DIR, fname)
        if not os.path.exists(path):
            print(f"  [missing] {path}")
            continue
        trans.update(_PAIR_RE.findall(json.dumps(json.load(open(path)))))
    F = {(u, v): float(n) for (u, v), n in trans.items()}
    A = antisymmetric(F, AXES)
    print(f"\n  observed transitions: {sum(trans.values())}")
    print(f"  A→X (torus seam):     {trans.get(('A', 'X'), 0)} occurrences")
    print("\n  NET FLOW (antisymmetric part):")
    print_matrix(A, AXES)
    cycles = find_cycles(A, AXES, eps=0.5)
    if cycles:
        for path, w in cycles[:5]:
            print(f"  ✓ loop: {' → '.join(path)} → {path[0]}  strength={w:.2f}")
    else:
        print("\n  no circulation — source/sink (gradient) flow only")
        srcs = [u for u in AXES if all(A[(u, v)] >= 0 for v in AXES)]
        snks = [u for u in AXES if all(A[(u, v)] <= 0 for v in AXES)]
        print(f"  sources: {srcs}   sinks: {snks}")
    t, n, r = flow_ratio(F, A, AXES)
    print(f"  traffic={t:.0f}  |net flow|={n:.0f}  flow/traffic={r:.3f}")


# ── TEST 2: bedrock grids ─────────────────────────────────────────────────────

def _load_grid(path: str) -> Tuple[str, List[List[float]]]:
    j = json.load(open(path))
    G = [[0.0] * 25 for _ in range(25)]
    for s in j.get("slots", []):
        r = IDX.get((s["sub_law_c"], s["sub_law_d"]))
        c = IDX.get((s["col_law_c"], s["col_law_d"]))
        if r is not None and c is not None:
            G[r][c] = float(s.get("accountability_weight", 0.0) or 0.0)
    return j["nc_name"], G


def test_bedrock() -> None:
    print("\n" + "=" * 68)
    print("TEST 2 — COMPILED BEDROCK (125 manifolds, 25×25 slot grids)")
    print("=" * 68)
    if not os.path.isdir(MANIFOLD_DIR):
        print(f"  [missing] {MANIFOLD_DIR}")
        return
    ratios: List[float] = []
    circulating = 0
    n = 0
    for ax in AXES:
        d = os.path.join(MANIFOLD_DIR, ax)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".json"):
                continue
            name, G = _load_grid(os.path.join(d, fn))
            n += 1
            slots = tuple(f"{AXES[i//5]}:{DIMS[i%5]}" for i in range(25))
            F = {(slots[i], slots[j]): G[i][j]
                 for i in range(25) for j in range(25)}
            A = antisymmetric(F, slots)
            t, nf, r = flow_ratio(F, A, slots)
            ratios.append(r)
            if find_cycles(A, slots, eps=0.02, max_len=3):
                circulating += 1
    if not n:
        print("  no manifolds found")
        return
    print(f"\n  manifolds analyzed: {n}")
    print(f"  mean flow/traffic:  {sum(ratios)/n:.4f}  "
          f"(min {min(ratios):.4f} / max {max(ratios):.4f})")
    print(f"  with 3-cycle circulation: {circulating}/{n}")
    if circulating == 0:
        print("  → bedrock is a potential field: structure, not motion")


# ── TEST 3: lived time ────────────────────────────────────────────────────────

def test_lived_time() -> None:
    print("\n" + "=" * 68)
    print("TEST 3 — LIVED TEMPORAL RECORD (surface_pressure_log.jsonl)")
    print("=" * 68)
    if not os.path.exists(SURFACE_LOG):
        print(f"  [missing] {SURFACE_LOG}")
        return
    lines = [json.loads(l) for l in open(SURFACE_LOG) if l.strip()]
    lines.sort(key=lambda x: x.get("timestamp", 0))
    seqs: List[Tuple[List[str], float]] = []
    for l in lines:
        axs = [a for a in (l.get("expected_axes") or []) if a in AXES]
        if axs:
            seqs.append((axs, float(l.get("surface_score", 1.0) or 1.0)))
    print(f"\n  timestamp-ordered events: {len(seqs)}")

    F: Counter = Counter()
    for (a_axes, _), (b_axes, w) in zip(seqs, seqs[1:]):
        share = w / (len(a_axes) * len(b_axes))
        for u in a_axes:
            for v in b_axes:
                F[(u, v)] += share
    A = antisymmetric(dict(F), AXES)
    print("\n  TEMPORAL NET FLOW:")
    print_matrix(A, AXES)
    cycles = find_cycles(A, AXES, eps=0.05)
    if cycles:
        print(f"\n  ✓ CIRCULATION LOOPS FOUND: {len(cycles)}")
        for path, w in cycles[:6]:
            print(f"     {' → '.join(path)} → {path[0]}   strength={w:.3f}")
        full = [c for c in cycles if len(c[0]) == 5]
        if full:
            print(f"  ✓ full 5-axis loop exists — the A→X seam carries "
                  f"real circulating flux in time")
    else:
        print("\n  no temporal circulation")
    t, n, r = flow_ratio(dict(F), A, AXES)
    print(f"\n  traffic={t:.1f}  |net flow|={n:.2f}  flow/traffic={r:.4f}")
    print("\n  caveat: single log source; event adjacency may carry logging-")
    print("  order autocorrelation. Validate on live CERS snapshot deltas")
    print("  before treating loop strengths as calibrated.")


# ── main ──────────────────────────────────────────────────────────────────────

def _generated_header() -> None:
    """Tree state at run time -- so console output is self-dating and
    never needs to be cross-checked against a docstring's stale numbers."""
    import datetime
    n_genealogy = sum(
        1 for fn in ("links.json", "abilities.json", "pair_stats.json")
        if os.path.exists(os.path.join(GENEALOGY_DIR, fn))
    )
    n_manifolds = 0
    if os.path.isdir(MANIFOLD_DIR):
        for ax in AXES:
            d = os.path.join(MANIFOLD_DIR, ax)
            if os.path.isdir(d):
                n_manifolds += sum(1 for fn in os.listdir(d) if fn.endswith(".json"))
    n_surface_events = 0
    if os.path.exists(SURFACE_LOG):
        with open(SURFACE_LOG) as f:
            n_surface_events = sum(1 for l in f if l.strip())
    print(f"run at:            {datetime.datetime.now().isoformat(timespec='seconds')}")
    print(f"genealogy files:   {n_genealogy}/3 present")
    print(f"manifolds found:   {n_manifolds}")
    print(f"surface log lines: {n_surface_events}")
    print()


if __name__ == "__main__":
    print("AURORA FLOW AUDIT — torus or staircase?")
    print("Authors: Sunni (Sir) Morningstar & Cael Devo\n")
    _generated_header()
    test_fossil_record()
    test_bedrock()
    test_lived_time()
    print("\nDone.")

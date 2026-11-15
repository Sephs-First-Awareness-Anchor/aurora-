#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Test 9, deterministic level: the same seeded observation sequence through the genealogy of two checkouts.

    python scripts/compare_genealogy_equivalence.py --root <checkout> --mode plain|identified --out result.json

`plain`: observations made with no input identity (what the original code could do).  `identified`: each group of observations is
made inside a received input (what the live path now does).  For a lived-only sequence the representation profiles, pair statistics,
promoted links and counters must not depend on the checkout or on whether identity was carried.  Reports a digest and the numbers.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
import tempfile
from pathlib import Path


def run(root, mode):
    sys.path.insert(0, str(root))
    os.chdir(root)
    from aurora_internal.constraint_genealogy import ConstraintGenealogyLogger, GenealogyConfig, PressureVec, TraceItem
    ident = None
    if mode in ("identified",):
        from aurora_internal import aurora_input_identity as ident
    g = ConstraintGenealogyLogger("equiv", config=GenealogyConfig(), output_dir=tempfile.mkdtemp(prefix="equiv_"))
    ids = sorted(g.abilities)[:12]
    rng = random.Random(20261114)
    for turn in range(150):
        token = ident.begin_input(f"turn_{turn}", f"text {turn}", loads={"X": 1.0}, t=turn + 1) if ident else None
        try:
            for _ in range(rng.randint(1, 4)):
                reps = rng.sample(ids, rng.randint(1, 4))
                b = PressureVec(**{a: rng.random() for a in "XTNBA"})
                a_ = PressureVec(**{a: max(0.0, getattr(b, a) - rng.random() * 0.6 + rng.random() * 0.1) for a in "XTNBA"})
                g.observe(b, [TraceItem("ABILITY", r) for r in reps], a_)
        finally:
            if ident:
                ident.end_input(token)
    # a repeatedly useful pair, until it promotes (relationship promotion on the same footing)
    for turn in range(150, 450):
        token = ident.begin_input(f"turn_{turn}", f"text {turn}", loads={"X": 1.0}, t=turn + 1) if ident else None
        try:
            g.observe(PressureVec(X=0.9, T=0.4, N=0.1, B=0.1, A=0.1), [TraceItem("ABILITY", ids[0]), TraceItem("ABILITY", ids[1])],
                      PressureVec(X=0.2 + (turn % 7) * 0.01, T=0.4, N=0.1, B=0.1, A=0.1))
        finally:
            if ident:
                ident.end_input(token)
    # dreams: distinct episodes (each its own result), which must be credited exactly as before; and, in `replay` mode only, one
    # episode replayed, which the new code credits once and the original credits every time (the intended difference)
    for k in range(60):
        g.observe(PressureVec(X=0.9, T=0.4, N=0.1, B=0.1, A=0.1), [TraceItem("ABILITY", ids[2]), TraceItem("ABILITY", ids[3])],
                  PressureVec(X=0.2 + (k % 9) * 0.01, T=0.4, N=0.1, B=0.1, A=0.1),
                  notes={"source": "dream_episode", "seed_lineage_id": f"ep{k}"})
    if mode == "replay":
        for _ in range(40):
            g.observe(PressureVec(X=0.9, T=0.4, N=0.1, B=0.1, A=0.1), [TraceItem("ABILITY", ids[4]), TraceItem("ABILITY", ids[5])],
                      PressureVec(X=0.2, T=0.4, N=0.1, B=0.1, A=0.1), notes={"source": "dream_episode", "seed_lineage_id": "same"})
    profiles = {k: a.consequence_profile for k, a in sorted(g.abilities.items()) if a.consequence_profile}
    pairs = {f"{l}|{r}": [v.count, {x: round(y, 9) for x, y in sorted(v.relief_sum.items())}] for (l, r), v in sorted(g._pair_stats.items())}
    links = sorted(g._links_by_parents.items())
    out = {"profiles": profiles, "pairs": pairs, "links": links, "relief_event_count": int(g.relief_event_count),
           "tick_count": int(g.tick_count), "skipped_no_relief": int(g.skipped_no_relief)}
    blob = json.dumps(out, sort_keys=True, default=str)
    return {"digest": hashlib.blake2b(blob.encode(), digest_size=12).hexdigest(), "profiles": len(profiles), "pairs": len(pairs),
            "links": len(links), "relief_event_count": out["relief_event_count"], "tick_count": out["tick_count"], "detail": out}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--mode", default="plain", choices=("plain", "identified", "replay"))
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    Path(a.out).write_text(json.dumps(run(Path(a.root).resolve(), a.mode), default=str))

#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Run the whole crystal pass FOR REAL on a COPY of her state and report what changed.  Never writes to the source state.

    python scripts/trial_crystal_writers.py --state-dir aurora_state --out /tmp/crystal_trial [--hub sunni]

Loads `dps_crystals.json` into the registry class itself (its own creation path), runs `crystal_runtime.run_pass` (every subsystem's store woven; word classes;
grammar; links, facets by kind, maturity; generalization crystals), saves the result in --out, and prints before/after, including how many crystals can
grow under the evidence compared with under the old count rule.  --out is refused if it is, or is inside, the source.
"""
import argparse
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from aurora_dimensional_systems import Crystal, CrystalProcessingSystem  # noqa: E402
from aurora_internal import crystal_runtime as R  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--hub", default="sunni")
    a = ap.parse_args()
    src, out = os.path.realpath(a.state_dir), os.path.realpath(a.out)
    if out == src or out.startswith(src + os.sep) or src.startswith(out + os.sep):
        sys.exit("refusing: --out must be a separate directory from the state it copies")
    os.makedirs(out, exist_ok=True)
    raw = json.load(open(os.path.join(src, "dps_crystals.json")))
    dps = object.__new__(CrystalProcessingSystem)             # the registry's own _get_or_create, without booting the rest of the system
    dps.crystals = {cid: Crystal.from_dict(d) for cid, d in raw["crystals"].items()}
    dps.concept_index = dict(raw["concept_index"])
    before = {cid: (len(c.facets), len(c.connections or {}), int(c.level), bool(c.can_evolve())) for cid, c in dps.crystals.items()}
    t0 = time.time()
    r = R.run_pass(dps, src, force=True)
    print("pass:", json.dumps(r, default=str))
    if not r.get("ok"):
        sys.exit(1)
    cs = dps.crystals
    after = {cid: (len(c.facets), len(c.connections or {}), int(c.level), bool(c.can_evolve())) for cid, c in cs.items() if cid in before}
    new = [c for cid, c in cs.items() if cid not in before]
    print(f"crystals: {len(before)} -> {len(cs)} (+{len(new)} generalizations: {[c.concept for c in new][:12]})")
    print(f"gained links: {sum(1 for c in before if after[c][1] > before[c][1])} | gained facets: {sum(1 for c in before if after[c][0] > before[c][0])} | "
          f"level raised: {sum(1 for c in before if after[c][2] > before[c][2])}")
    print(f"can grow under the old count rule: {sum(1 for v in before.values() if v[3])} | under the evidence: {sum(1 for v in after.values() if v[3])}")
    for c in new[:8]:
        print(f"   {c.concept:<28} level {int(c.level)}  links {len(c.connections)}  facets {len(c.facets)}")
    h = dps.concept_index.get(a.hub)
    if h in before:
        print(f"hub '{a.hub}': facets {before[h][0]} -> {after[h][0]}, links {before[h][1]} -> {after[h][1]}, level {before[h][2]} -> {after[h][2]}")
    raw["crystals"] = {cid: c.to_dict() for cid, c in cs.items()}
    raw["concept_index"] = dps.concept_index
    json.dump(raw, open(os.path.join(out, "dps_crystals.json"), "w"))
    print(f"saved to {out}/dps_crystals.json ({time.time() - t0:.1f}s total); source untouched")


if __name__ == "__main__":
    main()

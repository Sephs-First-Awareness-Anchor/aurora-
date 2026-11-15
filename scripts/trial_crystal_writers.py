#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Run the crystal writers FOR REAL on a COPY of her state and report what changed.  Never writes to the source state.

    python scripts/trial_crystal_writers.py --state-dir aurora_state --out /tmp/crystal_trial [--hub sunni]

Copies `dps_crystals.json` into --out (refused if --out is, or is inside, the source), weaves every store, applies the association links and the
facets to the copy's real `Crystal` objects, saves the result in --out, and prints before/after: links, facets, and whether `can_evolve` (a count of
facets and uses) changed for any crystal, since that is the one existing behaviour the facets could shift.
"""
import argparse
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from aurora_dimensional_systems import Crystal  # noqa: E402
from aurora_internal import crystal_associations as A, crystal_facets as F, crystal_weave as W  # noqa: E402


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
    idx = raw["concept_index"]
    crystals = {cid: Crystal.from_dict(d) for cid, d in raw["crystals"].items()}
    before = {cid: (len(c.facets), len(c.connections or {}), bool(c.can_evolve())) for cid, c in crystals.items()}
    r = W.weave(src)
    links = A.apply_to_crystals(r["store"], idx, crystals, dry_run=False)
    facets = F.apply_to_crystals(r["book"], idx, crystals, dry_run=False)
    after = {cid: (len(c.facets), len(c.connections or {}), bool(c.can_evolve())) for cid, c in crystals.items()}
    flips = [cid for cid in crystals if before[cid][2] != after[cid][2]]
    raw["crystals"] = {cid: c.to_dict() for cid, c in crystals.items()}
    json.dump(raw, open(os.path.join(out, "dps_crystals.json"), "w"))
    print("links:", links)
    print("facets:", facets)
    print(f"crystals: {len(crystals)} | gained links: {sum(1 for c in crystals if after[c][1] > before[c][1])} | "
          f"gained facets: {sum(1 for c in crystals if after[c][0] > before[c][0])} | can_evolve changed: {len(flips)}")
    h = idx.get(a.hub)
    if h in crystals:
        print(f"hub '{a.hub}': facets {before[h][0]} -> {after[h][0]}, links {before[h][1]} -> {after[h][1]}")
        for role, f in sorted(crystals[h].facets.items(), key=lambda kv: kv[1].role):
            if f.role.startswith("fk:"):
                print(f"   {f.role:<22} conf {float(f.confidence):.3f}  entries {len((f.content or {}).get('entries', []))}")
    print("flipped can_evolve (first 10):", [(crystals[c].concept, before[c][2], '->', after[c][2]) for c in flips[:10]])
    print("source untouched:", os.path.realpath(os.path.join(src, "dps_crystals.json")) != os.path.realpath(os.path.join(out, "dps_crystals.json")))


if __name__ == "__main__":
    main()

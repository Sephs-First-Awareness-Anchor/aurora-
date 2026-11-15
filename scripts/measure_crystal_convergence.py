#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""P2 measurement: graded convergence between concepts, from a state directory.  READ-ONLY.

    python scripts/measure_crystal_convergence.py --state-dir aurora_state [--hub sunni] [--top 12]

Builds the association store from the OETS web, then shows, for one hub: the field (what belongs to it, by degree), and which other
concepts converge most with it.  Nothing is cut off by a bar; --top only limits how many are printed.  Writes nothing.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aurora_internal.crystal_associations import project_oets  # noqa: E402
from aurora_internal.crystal_convergence import convergence, field_of  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state-dir", required=True)
    ap.add_argument("--hub", default="sunni")
    ap.add_argument("--top", type=int, default=12)
    a = ap.parse_args()
    web = json.load(open(os.path.join(a.state_dir, "aurora_oets_web.json")))
    store = project_oets(web["relations"])
    f = field_of(store, a.hub)
    print(f"field of '{a.hub}': {len(f)} concepts belong to some degree")
    vals = sorted(f.values(), reverse=True)
    if vals:
        n = len(vals)
        print("degree distribution (max / median / min):", round(vals[0], 3), round(vals[n // 2], 3), round(vals[-1], 4))
    for k, v in sorted(f.items(), key=lambda kv: -kv[1])[:a.top]:
        print(f"  {k:<24} {v:.3f}   (convergence {convergence(store, a.hub, k):.3f})")


if __name__ == "__main__":
    main()

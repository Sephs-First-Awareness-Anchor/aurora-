#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""P3 measurement: expected level per crystal from the evidence that exists in a state directory.  READ-ONLY.

    python scripts/measure_crystal_maturity.py --state-dir aurora_state

Only association (from the OETS web, counted evidence only) exists in a snapshot; the other points are unknown and leave the blend, so the numbers are an
upper bound on standing, not a verdict.  Writes nothing.
"""
import argparse
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aurora_internal import crystal_maturity as M  # noqa: E402
from aurora_internal.crystal_associations import project_oets  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state-dir", required=True)
    a = ap.parse_args()
    web = json.load(open(os.path.join(a.state_dir, "aurora_oets_web.json")))
    dps = json.load(open(os.path.join(a.state_dir, "dps_crystals.json")))
    store = project_oets(web["relations"])
    xs, stored = [], Counter()
    for concept, cid in dps["concept_index"].items():
        amount = M.points_from_evidence(association_strengths=store.connections_for(concept).values())["associative"]
        xs.append(M.expected_level({"associative": amount}))
        stored[dps["crystals"].get(cid, {}).get("level")] += 1
    xs.sort()
    n = len(xs)
    print("crystals:", n, "| stored levels today:", dict(stored))
    print("expected level, association only (min/median/p90/max):", *(round(xs[i], 2) for i in (0, n // 2, int(n * .9), n - 1)))
    print("crystals with any counted association:", sum(1 for x in xs if x > 1.0))


if __name__ == "__main__":
    main()

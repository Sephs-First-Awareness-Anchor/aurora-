#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Promotion measurement: which generalizations classify a group of crystals, and how far.  READ-ONLY.

    python scripts/measure_crystal_promotion.py --state-dir aurora_state [--top 15]

Builds the association store from the OETS web (counted evidence only), then ranks every concept that holds members as `is_a` by its promotion degree.
Nothing is cut off by a bar; --top only limits how many are printed.  Writes nothing.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aurora_internal.crystal_associations import project_oets  # noqa: E402
from aurora_internal.crystal_promotion import classification, promotion_candidates  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state-dir", required=True)
    ap.add_argument("--top", type=int, default=15)
    a = ap.parse_args()
    web = json.load(open(os.path.join(a.state_dir, "aurora_oets_web.json")))
    store = project_oets(web["relations"])
    concepts = {x for a_, b_, _ in store.records() for x in (a_, b_)}
    ranked = promotion_candidates(store, concepts)
    print(f"{len(ranked)} concepts classify a group to some degree (of {len(concepts)} seen)")
    for g, d in ranked[:a.top]:
        print(f"  {g:<24} degree {d:.3f}   classifies {len(classification(store, g))} crystals")


if __name__ == "__main__":
    main()

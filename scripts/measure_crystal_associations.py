#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""P1 measurement: what the recurrence-based associations would be, from a state directory.  READ-ONLY.

    python scripts/measure_crystal_associations.py --state-dir aurora_state [--concept sunni] [--out /tmp/associations.json]

Builds the association store from the OETS web's relations, reports how much of it counts, how much of it reaches crystals that exist
(a dry run: no crystal is changed), and shows the single view of one concept.  Writes nothing under --state-dir.
"""
import argparse
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aurora_internal.crystal_associations import AssociationStore, apply_to_crystals, project_oets  # noqa: E402


class _C:
    def __init__(self):
        self.connections = {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state-dir", required=True)
    ap.add_argument("--concept", default="sunni")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    web = json.load(open(os.path.join(a.state_dir, "aurora_oets_web.json")))
    dps = json.load(open(os.path.join(a.state_dir, "dps_crystals.json")))
    store = project_oets(web["relations"])
    print("OETS relations:", len(web["relations"]), "-> association records:", len(store))
    print("evidence by basis:", dict(Counter(store.basis_counts())) if False else store.basis_counts())
    counted = sum(1 for (x, y, t) in store._links if store.strength(x, y, t) > 0)
    print("records that count (recurrence-based):", counted, "| kept but not counted:", len(store) - counted)
    idx = dps["concept_index"]
    nodes = set(web["nodes"])
    have = [n for n in nodes if n in idx]
    print(f"OETS concepts: {len(nodes)} | with a crystal: {len(have)}")
    crystals = {cid: _C() for cid in dps["crystals"]}
    res = apply_to_crystals(store, idx, crystals, max_per_crystal=16, dry_run=True)
    print("dry run on the crystals that exist:", res)
    dist = Counter()
    for concept, cid in idx.items():
        n = len([o for o in store.connections_for(concept) if o in idx])
        dist[min(n, 16)] += 1
    print("crystals by number of counted associations to other crystals (0..16+):", dict(sorted(dist.items())))
    v = store.view(a.concept)
    print(f"view of '{a.concept}':", json.dumps({"types": {t: len(l) for t, l in v["counted"].items()},
                                                 "top": {t: l[:3] for t, l in v["counted"].items()},
                                                 "uncounted_evidence": v["uncounted_evidence"]})[:600])
    if a.out:
        store.save(a.out)
        print("store written to", a.out, os.path.getsize(a.out) // 1024, "KB (OETS web:", os.path.getsize(os.path.join(a.state_dir, "aurora_oets_web.json")) // 1024, "KB)")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Facet placement measurement: what the OETS web and RCRW snapshot would place into crystal facets, from a state directory.  READ-ONLY.

    python scripts/measure_crystal_facets.py --state-dir aurora_state [--concept sunni] [--out /tmp/facets.json]

Builds a FacetBook from every OETS node and relation (and the waveform cycle, if it has a developed relation), reports how much is held once
versus how many occasions are attached, how much is counted, and what the crystals would receive (a dry run).  Writes nothing under --state-dir.
"""
import argparse
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aurora_internal import crystal_facets as F  # noqa: E402
from aurora_internal.crystal_associations import project_assertions, project_oets  # noqa: E402


class _C:
    def __init__(self):
        self.facets = {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state-dir", required=True)
    ap.add_argument("--concept", default="sunni")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    web = json.load(open(os.path.join(a.state_dir, "aurora_oets_web.json")))
    dps = json.load(open(os.path.join(a.state_dir, "dps_crystals.json")))
    book = F.FacetBook()
    for node in web["nodes"].values():
        F.place_oets_node(book, node)
    store = project_assertions(web["relations"], project_oets(web["relations"]))
    F.place_associations(book, store)
    path = os.path.join(a.state_dir, "recursive_causal_reasoning_waveform.json")
    cyc = None
    if os.path.exists(path):
        d = json.load(open(path))
        cyc = F.place_cycle(book, d.get("active_cycle") or {}, occurrence_class="")
    t = book.totals()
    print("book:", t, f"| occasions per entry {t['occasions'] / max(1, t['entries']):.2f}")
    kinds, counted = Counter(), Counter()
    for c in book.concepts():
        for k, rows in book.facets_for(c, include_uncounted=True).items():
            kinds[k] += len(rows)
            counted[k] += sum(1 for r in rows if r["degree"] > 0)
    print("entries by kind (counted / all):", {k: f"{counted[k]}/{kinds[k]}" for k in sorted(kinds)})
    crystals = {cid: _C() for cid in dps["crystals"]}
    print("dry run on the crystals that exist:", F.apply_to_crystals(book, dps["concept_index"], crystals))
    print("waveform cycle placed:", cyc)
    v = book.facets_for(a.concept, top=3, include_uncounted=True)
    print(f"'{a.concept}':", json.dumps({k: [(r['key'], round(r['degree'], 3), r['contexts']) for r in rows] for k, rows in v.items()})[:700])
    if a.out:
        book.save(a.out)
        print("book written to", a.out, os.path.getsize(a.out) // 1024, "KB")


if __name__ == "__main__":
    main()

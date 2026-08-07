#!/usr/bin/env python3
"""
AURORA GENEALOGY ENVIRONMENT — SHADOW COMPARISON HARNESS
==========================================================
Authors: Sunni (Sir) Morningstar & Cael Devo

Read-only diagnostic script. Loads the real ConstraintLink fossil record at
aurora_state/genealogy/links.json, derives environment signatures for every
promoted link using aurora_genealogy_environment.py, and reports:

  - how many links produce a non-degenerate signature (node_count > 1)
  - the distribution of best-matching _CORE_CREST_PROFILES across all real
    genealogies in the fossil record
  - summary cosine-similarity statistics per authored profile

This performs NO writes anywhere, and never calls into WARP's trial/promotion
machinery. It is meant to be run manually (`python3
aurora_genealogy_environment_shadow.py`) and its output pasted into the
experiment report -- it is not imported by any live Aurora path.
"""
from __future__ import annotations

import json
import os
import statistics
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aurora_genealogy_environment import (
    link_from_dict,
    logger_from_links,
    derive_environment_signature,
    compare_against_core_crests,
)


def main() -> None:
    fossil_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "aurora_state", "genealogy", "links.json"
    )
    with open(fossil_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    links = {k: link_from_dict(v) for k, v in raw.items()}
    logger = logger_from_links(links)

    node_counts = []
    best_match_counter = Counter()
    per_crest_scores = defaultdict(list)
    dominant_axis_counter = Counter()
    insufficient = 0

    for link_id in links:
        sig = derive_environment_signature(logger, link_id)
        if sig.insufficient_genealogy:
            insufficient += 1
            continue
        node_counts.append(sig.node_count)
        scores = compare_against_core_crests(sig)
        if not scores:
            continue
        best_name = max(scores, key=lambda k: scores[k])
        best_match_counter[best_name] += 1
        for name, score in scores.items():
            per_crest_scores[name].append(score)
        top_axis = max(sig.axis_distribution, key=lambda a: sig.axis_distribution[a]) if sig.axis_distribution else "?"
        dominant_axis_counter[top_axis] += 1

    print(f"Total links in fossil record: {len(links)}")
    print(f"Insufficient/empty genealogies: {insufficient}")
    print(f"Derived signatures: {len(node_counts)}")
    if node_counts:
        print(f"node_count: min={min(node_counts)} max={max(node_counts)} mean={statistics.mean(node_counts):.2f}")
    print()
    print("Dominant axis_distribution axis across all derived signatures:")
    for axis, count in dominant_axis_counter.most_common():
        print(f"  {axis}: {count}")
    print()
    print("Best-matching authored crest profile (argmax cosine), across all real genealogies:")
    for name, count in best_match_counter.most_common():
        print(f"  {name}: {count}")
    print()
    print("Per-crest cosine similarity stats across all real genealogies:")
    for name in sorted(per_crest_scores):
        scores = per_crest_scores[name]
        print(
            f"  {name:12s} mean={statistics.mean(scores):+.4f} "
            f"stdev={statistics.pstdev(scores):.4f} "
            f"min={min(scores):+.4f} max={max(scores):+.4f}"
        )


if __name__ == "__main__":
    main()

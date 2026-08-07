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

    edge_counts = []
    self_edge_counts = []
    parent_child_edge_counts = []
    deduped_slot_counts = []
    leverage_grades = []
    formation_costs = []
    empty_root_slot_count = 0

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

        edge_counts.append(len(sig.edge_provenance))
        self_edge_counts.append(sum(1 for e in sig.edge_provenance if e["edge_type"] == "self"))
        parent_child_edge_counts.append(sum(1 for e in sig.edge_provenance if e["edge_type"] == "parent_child"))
        if not sig.chained_root_slot:
            empty_root_slot_count += 1
        if sig.closure_projection is not None:
            deduped_slot_counts.append(len(sig.closure_projection.active_slots))
            leverage_grades.append(sig.closure_projection.leverage_grade)
            formation_costs.append(sig.closure_projection.formation_cost)

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
    print()
    print("Edge-fidelity stats (Phase 1.1 -- real ConstraintLink.parents edges, not list adjacency):")
    if edge_counts:
        print(f"  edges per genealogy: min={min(edge_counts)} max={max(edge_counts)} mean={statistics.mean(edge_counts):.2f}")
        print(f"  self edges (leaf-rooted nodes): total={sum(self_edge_counts)} mean={statistics.mean(self_edge_counts):.2f}")
        print(f"  parent_child edges: total={sum(parent_child_edge_counts)} mean={statistics.mean(parent_child_edge_counts):.2f}")
    print(f"  chained_root_slot empty (no resolvable edges): {empty_root_slot_count}")
    print()
    print("closure_projection stats (derive_lineage() fed the real, Unicode-x-joined chain):")
    if deduped_slot_counts:
        print(f"  deduped active_slots per genealogy: min={min(deduped_slot_counts)} max={max(deduped_slot_counts)} mean={statistics.mean(deduped_slot_counts):.2f}")
        print(f"  leverage_grade: min={min(leverage_grades):.4f} max={max(leverage_grades):.4f} mean={statistics.mean(leverage_grades):.4f} stdev={statistics.pstdev(leverage_grades):.4f}")
        print(f"  formation_cost: min={min(formation_costs):.4f} max={max(formation_costs):.4f} mean={statistics.mean(formation_costs):.4f} stdev={statistics.pstdev(formation_costs):.4f}")


if __name__ == "__main__":
    main()

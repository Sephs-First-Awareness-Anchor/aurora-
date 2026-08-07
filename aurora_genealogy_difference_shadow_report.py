#!/usr/bin/env python3
"""
AURORA GENEALOGY DIFFERENCE SHADOW — REPORT RUN (Phase 3A)
================================================================
Authors: Sunni (Sir) Morningstar & Cael Devo

Read-only. Replays aurora_state/genealogy/events_recent.json through
aurora_genealogy_difference_shadow.replay_events(), runs every Phase 3A
measurement against the result plus aurora_state/genealogy/links.json, and
prints the findings. No writes anywhere; no promotion code touched.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aurora_genealogy_difference_shadow import (
    replay_events,
    measure_collision_differentiation,
    measure_information_beyond_axis_identity,
    measure_persistence_across_reused_links,
    find_pairs_with_divergent_difference,
)


def main() -> None:
    root = os.path.dirname(os.path.abspath(__file__))

    with open(os.path.join(root, "aurora_state", "genealogy", "links.json"), "r", encoding="utf-8") as f:
        links_index = json.load(f)

    events_path = os.path.join(root, "aurora_state", "genealogy", "events_recent.json")
    with open(events_path, "r", encoding="utf-8") as f:
        records = list(json.load(f).get("records") or [])

    pair_stats = replay_events(records, links_index)
    print(f"Replayed {len(records)} real events -> {len(pair_stats)} distinct pair-keys "
          f"({sum(ps.count for ps in pair_stats.values())} total pair-observations)")
    n_with_difference = sum(1 for ps in pair_stats.values() if ps.difference_participation_ticks)
    print(f"Pair-keys with ANY nonzero difference participation: {n_with_difference} / {len(pair_stats)}")
    print()

    print("=== Question 1: does DIFFERENCE differentiate signature-colliding pair-keys? ===")
    collisions = measure_collision_differentiation(pair_stats, links_index)
    colliding_groups = [c for c in collisions if c.collides]
    diverging_groups = [c for c in colliding_groups if c.difference_rates_diverge]
    print(f"  signature groups: {len(collisions)}; groups with >1 pair-key (collisions): {len(colliding_groups)}")
    print(f"  of those, groups where difference participation rate diverges: {len(diverging_groups)}")
    print()

    print("=== Question 6: does DIFFERENCE carry information beyond axis identity? ===")
    info_result = measure_information_beyond_axis_identity(records)
    print(f"  total nontrivial DIFFERENCE records analyzed: {info_result['total_nontrivial_records']}")
    print(f"  records where a NON-dominant axis also carried nonzero DIFFERENCE: "
          f"{info_result['records_with_nonzero_non_dominant_axis_value']}")
    for axis, stats in sorted(info_result["per_axis_spread"].items()):
        print(f"  axis {axis}: n={stats['n']}  own-axis value stdev={stats['dominant_axis_value_stdev']:.6f}  "
              f"range=[{stats['dominant_axis_value_min']:.6f}, {stats['dominant_axis_value_max']:.6f}]")
    print()

    print("=== Question 2/3/4: DAG structure / closure / recurrence / persistence, via reused links ===")
    persistence_result = measure_persistence_across_reused_links(pair_stats, records, links_index)
    print(f"  reused links with real DIFFERENCE-bearing replays: {len(persistence_result['links'])}")
    for link_id, stats in persistence_result["links"].items():
        print(f"  {link_id}: replays={stats['replay_count']} axis={stats['dominant_relief_axis']} "
              f"depth={stats['depth']} own_axis_mean={stats['own_axis_difference_mean']} "
              f"own_axis_stdev={stats['own_axis_difference_stdev']:.6f}")
    print(f"  mean within-link stdev (n_links={persistence_result['n_links_with_repeated_replay']}): "
          f"{persistence_result['mean_within_link_stdev']}")
    print()

    print("=== The killer experiment: near-identical-signature pairs with divergent DIFFERENCE ===")
    candidates = find_pairs_with_divergent_difference(pair_stats, links_index)
    print(f"  qualifying candidate pairs found in this corpus: {len(candidates)}")
    for c in candidates[:10]:
        print(f"  {c}")
    if not candidates:
        print("  (expected -- see module docstring: no pair-observation in this corpus ever carries")
        print("   real DIFFERENCE signal at all, since all 49 real DifferenceSnapshot-bearing records")
        print("   have trace length 1 and therefore never form a pair. This is the headline finding.)")


if __name__ == "__main__":
    main()

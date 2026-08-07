#!/usr/bin/env python3
"""
AURORA GENEALOGY PROMOTION DIMENSION OBSERVER — SHADOW RUN (Phase 2)
========================================================================
Authors: Sunni (Sir) Morningstar & Cael Devo

Read-only diagnostic script. Loads real, already-persisted ReliefRecord
corpora and runs aurora_genealogy_promotion_dimension_observer.summarize_corpus()
against them, to answer empirically: does live formation dynamics involve
NonComp dimensions the current OPERATOR x COST genealogy atoms cannot
preserve?

Two corpora, reported and interpreted SEPARATELY (not pooled), because they
differ in kind:

  1. aurora_state/genealogy/events_recent.json — real events from an actual
     interaction/bootstrap run (run_id "2026-07-29_050108"). This is the
     primary corpus for the question this phase asks.
  2. aurora_state/ability_lineages/**/events.jsonl — synthetic,
     artificial_seed=true lineage-materialization records. Reported for
     completeness but explicitly NOT used to answer the "live formation
     dynamics" question, since these are deliberately constructed seed
     records, not organic pressure/relief events.

This performs NO writes anywhere and never imports, calls, or touches
ConstraintGenealogyLogger, PairStats, or _try_promote — see
tests/test_genealogy_promotion_dimension_observer.py for the source-scan
test that verifies this.
"""
from __future__ import annotations

import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aurora_genealogy_promotion_dimension_observer import summarize_corpus


def _load_events_recent(path: str) -> list:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return list(data.get("records") or [])


def _load_jsonl(path: str) -> list:
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def _print_summary(label: str, records: list) -> None:
    summary = summarize_corpus(records).to_dict()
    print(f"=== {label} ===")
    print(f"  record_count: {summary['record_count']}")
    if summary["record_count"] == 0:
        print()
        return
    for key in (
        "difference_signal_present",
        "difference_values_nontrivial",
        "tensor_concept_reference_present",
        "non_operator_cost_tensor_reference",
        "any_non_operator_cost_signal",
    ):
        stat = summary[key]
        print(f"  {key}: {stat['count']} / {summary['record_count']}  ({stat['fraction']*100:.1f}%)")
    print(f"  non_operator_cost_dimension_counts: {summary['non_operator_cost_dimension_counts']}")
    print()


def main() -> None:
    root = os.path.dirname(os.path.abspath(__file__))

    events_recent_path = os.path.join(root, "aurora_state", "genealogy", "events_recent.json")
    if os.path.exists(events_recent_path):
        records = _load_events_recent(events_recent_path)
        _print_summary("PRIMARY: aurora_state/genealogy/events_recent.json (real run)", records)
    else:
        print("PRIMARY corpus not found -- nothing to report.\n")

    synthetic_pattern = os.path.join(root, "aurora_state", "ability_lineages", "**", "events.jsonl")
    synthetic_records = []
    for path in sorted(glob.glob(synthetic_pattern, recursive=True)):
        synthetic_records.extend(_load_jsonl(path))
    if synthetic_records:
        _print_summary(
            "SECONDARY (excluded from the live-dynamics conclusion, reported for "
            "completeness): synthetic artificial_seed lineage events",
            synthetic_records,
        )


if __name__ == "__main__":
    main()

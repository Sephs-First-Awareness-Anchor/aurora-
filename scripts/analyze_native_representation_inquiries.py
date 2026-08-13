#!/usr/bin/env python3
"""Read-only evaluation of native representational inquiry eligibility.

The supplied build predates live RI/RS experiment records.  This audit asks
which stored representations the new retrieval layer can legitimately expose;
it never records an inquiry, stages a trial, calls observe(), or writes state.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPTS_ROOT = os.path.dirname(os.path.abspath(__file__))
for _path in (_REPO_ROOT, _SCRIPTS_ROOT):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from analyze_cross_generational_representations import analyze as analyze_collisions
from analyze_cross_generational_representations import _load_logger
from aurora_internal.constraint_genealogy import TraceItem


def _load_json(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as handle:
        raw = json.load(handle)
    return dict(raw or {}) if isinstance(raw, dict) else {}


def _compact_operand(logger, item_id: str) -> Dict[str, Any]:
    record = dict(logger.representation_record(item_id) or {})
    effect = dict(record.get("operational_effect", {}) or {})
    identity = dict(record.get("semantic_identity", {}) or {})
    return {
        "representation_id": item_id,
        "kind": record.get("kind", ""),
        "depth": record.get("depth", 0),
        "generation": record.get("generation", 0),
        "constraint_signature": dict(record.get("constraint_basis", {}) or {}).get("signature", "0"),
        "purpose_lane": identity.get("purpose_lane", ""),
        "operator_action": identity.get("operator_action", ""),
        "dominant_axis": effect.get("dominant_axis", ""),
        "effect_tags": list(effect.get("effect_tags", []) or [])[:12],
        "mean_relief": dict(effect.get("mean_relief", {}) or {}),
    }


def _candidate_report(logger, candidate: Optional[Dict[str, Any]], category: str) -> Dict[str, Any]:
    if not candidate:
        return {
            "category": category,
            "eligible": False,
            "actual_experiment_occurred": False,
            "outcome": "no bounded candidate found in the inspected window",
        }
    operands = [str(x) for x in list(candidate.get("operand_ids", []) or []) if str(x)]
    return {
        "category": category,
        "eligible": True,
        "inquiry_id": str(candidate.get("inquiry_id", candidate.get("collision_id", "")) or ""),
        "inquiry_class": str(candidate.get("inquiry_class", "constraint_collision") or "constraint_collision"),
        "operand_order": operands,
        "operands": [_compact_operand(logger, item_id) for item_id in operands],
        "constraint_signatures": list(candidate.get("constraint_signatures", []) or []),
        "merged_constraint_basis": dict(candidate.get("merged_constraint_basis", {}) or {}),
        "generation_span": int(candidate.get("generation_span", 0) or 0),
        "pressure": float(candidate.get("pressure", 0.0) or 0.0),
        "eligibility_evidence": dict(candidate.get("evidence", {}) or {}),
        "actual_experiment_occurred": False,
        "observed_experiment_evidence": None,
        "outcome": "unresolved; candidate discovery is not evidence",
        "information_beyond_flattening": (
            "ordered stable operand identities, local semantic/effect state, depth, "
            "and separately retained primitive signatures are available without asserting a relation meaning"
        ),
    }


def _first_exact_collision(logger) -> Optional[Dict[str, Any]]:
    groups: Dict[str, List[str]] = defaultdict(list)
    for link_id in logger.links:
        groups[logger._collision_signature_for_item(link_id)].append(link_id)
    for _signature, ids in sorted(groups.items(), key=lambda row: (-len(row[1]), row[0])):
        if len(ids) < 2:
            continue
        for active_id in ids[:12]:
            candidates = logger.representation_collision_candidates([TraceItem("LINK", active_id)])
            if candidates:
                candidate = dict(candidates[0])
                candidate.setdefault("inquiry_id", candidate.get("collision_id", ""))
                candidate.setdefault("inquiry_class", "constraint_collision")
                candidate.setdefault("operand_ids", [
                    candidate.get("active_representation_id", ""),
                    candidate.get("counterpart_representation_id", ""),
                ])
                left, right = candidate["operand_ids"]
                candidate.setdefault("constraint_signatures", [
                    logger._collision_signature_for_item(left),
                    logger._collision_signature_for_item(right),
                ])
                candidate.setdefault("merged_constraint_basis", {
                    "signature": logger._canonical_coupling_signature(logger._merged_axis_counts_for_pair((left, right))),
                    "counts": logger._merged_axis_counts_for_pair((left, right)),
                })
                return candidate
    return None


def _first_gap(logger, ids: Iterable[str], kind: str, predicate=None) -> Optional[Dict[str, Any]]:
    for item_id in ids:
        candidates = logger.representation_gap_candidates([TraceItem(kind, str(item_id))])
        for candidate in candidates:
            if predicate is None or predicate(candidate):
                return dict(candidate)
    return None


def evaluate(state_dir: str) -> Dict[str, Any]:
    baseline = analyze_collisions(state_dir)
    logger = _load_logger(state_dir)
    couplings = _load_json(os.path.join(state_dir, "couplings.json"))
    logger._representation_relations = {
        str(k): dict(v) for k, v in dict(couplings.get("representation_relations", {}) or {}).items()
        if isinstance(v, dict)
    }
    logger._representation_collisions = {
        str(k): dict(v) for k, v in dict(couplings.get("representation_collisions", {}) or {}).items()
        if isinstance(v, dict)
    }

    start = time.perf_counter()
    exact = _first_exact_collision(logger)
    index_seconds = time.perf_counter() - start

    cross_family = _first_gap(
        logger,
        list(logger.links)[:160],
        "LINK",
        lambda c: len(set(c.get("constraint_signatures", []) or [])) == 2,
    )

    ancestor_current = None
    descendant_ids = sorted(logger.links, key=lambda item_id: int(logger.links[item_id].depth), reverse=True)
    for item_id in descendant_ids[:160]:
        ancestors = set(logger.representation_ancestors(item_id, limit=64))
        if not ancestors:
            continue
        candidate = _first_gap(
            logger,
            [item_id],
            "LINK",
            lambda c, ancestors=ancestors: str(c.get("counterpart_representation_id", "")) in ancestors,
        )
        if candidate:
            ancestor_current = candidate
            break

    native_abilities = [
        ability_id for ability_id in logger.abilities
        if ":CODE_" not in ability_id and ":LINK_" not in ability_id
    ]
    ability_pair = _first_gap(
        logger,
        native_abilities[:240],
        "ABILITY",
        lambda c: str(c.get("counterpart_representation_id", "")) in set(native_abilities),
    )

    persisted_runtime = dict(couplings.get("representation_inquiry_runtime", {}) or {})
    persisted_history = list(persisted_runtime.get("history", []) or [])
    persisted_stages = dict(persisted_runtime.get("active_stages", {}) or {})
    examples = [
        _candidate_report(logger, exact, "exact_signature_collision"),
        _candidate_report(logger, cross_family, "cross_family_native_relevance"),
        _candidate_report(logger, ancestor_current, "ancestor_current_relation"),
        _candidate_report(logger, ability_pair, "existing_ability_relation"),
    ]
    return {
        "state_dir": os.path.abspath(state_dir),
        "read_only": True,
        "persisted_state": {
            "links": len(logger.links),
            "abilities": len(logger.abilities),
            "persisted_relation_records": len(logger._representation_relations),
            "persisted_inquiry_records": len(logger._representation_collisions),
            "persisted_active_experiment_stages": len(persisted_stages),
            "persisted_experiment_outcomes": len(persisted_history),
        },
        "collision_baseline": {
            "links": baseline["links"],
            "cross_depth_link_offspring": baseline["cross_depth_link_offspring"],
            "native_abilities": baseline["native_abilities"],
        },
        "retrieval_runtime": {
            "cold_exact_index_and_candidate_seconds": round(index_seconds, 6),
            "last_bounded_search": dict(logger.representation_experiment_status().get("last_search", {}) or {}),
        },
        "candidate_examples": examples,
        "actual_outcome_boundary": (
            "No RI/RS runtime history exists in the supplied persisted state, so all four examples remain "
            "eligible unresolved inquiries. The audit does not manufacture a co-activation or promotion."
        ),
        "claim_boundary": (
            "The retrieval layer exposes evidence-bearing test candidates beyond exact flattened families; "
            "it does not establish that any candidate relation is meaningful."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-dir", default=os.path.join(_REPO_ROOT, "aurora_state", "genealogy"))
    parser.add_argument("--output", default="")
    args = parser.parse_args()
    payload = evaluate(args.state_dir)
    rendered = json.dumps(payload, indent=2, sort_keys=True)
    if args.output:
        # The optional output is for explicit audit artifact generation only;
        # state_dir itself is never touched.
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(rendered + "\n")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

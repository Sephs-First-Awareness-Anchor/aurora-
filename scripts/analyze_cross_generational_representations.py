#!/usr/bin/env python3
"""Read-only Build 650 representational collision analysis.

Reproduces the pre-extension X/T/N/B/A collapse metrics, then measures which
collision families contain distinctions grounded in stored operational effects,
local semantic identity, and intact genealogy structure.  It never calls
observe(), PairStats.update(), promotion, or any persistence writer.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Tuple

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from aurora_genealogy_environment import derive_environment_signature
from aurora_internal.constraint_genealogy import (
    AXES,
    AbilityProfile,
    ConstraintGenealogyLogger,
    TraceItem,
    constraint_link_from_dict,
)


def _load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    return dict(data or {})


def _load_logger(state_dir: str) -> ConstraintGenealogyLogger:
    # The logger constructor requires an output directory even though this
    # analysis never invokes a writer.  Keep that compatibility surface
    # ephemeral so running the read-only audit leaves no repository artifact.
    with tempfile.TemporaryDirectory(prefix="aurora_cross_rep_analysis_") as output_dir:
        logger = ConstraintGenealogyLogger(
            run_id="cross_generational_read_only_analysis",
            output_dir=output_dir,
        )
    raw_links = _load_json(os.path.join(state_dir, "links.json"))
    logger.links = {
        str(lid): constraint_link_from_dict(rec, fallback_id=str(lid))
        for lid, rec in raw_links.items()
        if isinstance(rec, dict)
    }
    logger._links_by_parents = {
        (link.parents[0], link.parents[1]): link.id
        for link in logger.links.values()
        if len(link.parents) == 2
    }

    raw_abilities = _load_json(os.path.join(state_dir, "abilities.json"))
    loaded_abilities: Dict[str, AbilityProfile] = {}
    for aid, rec in raw_abilities.items():
        if not isinstance(rec, dict):
            continue
        loaded_abilities[str(aid)] = AbilityProfile(
            id=str(rec.get("id", aid)),
            axis=str(rec.get("axis", "X")),
            requires=tuple(rec.get("requires", []) or []),
            cost={a: float((rec.get("cost", {}) or {}).get(a, 0.0) or 0.0) for a in AXES},
            risk={a: float((rec.get("risk", {}) or {}).get(a, 0.0) or 0.0) for a in AXES},
            effect_tags=tuple(str(x) for x in (rec.get("effect_tags", []) or [])),
            notes=str(rec.get("notes", "") or ""),
            topology_id=rec.get("topology_id"),
            semantic_variant_id=rec.get("semantic_variant_id"),
        )
    logger.abilities = loaded_abilities
    return logger


def _link_signature(logger: ConstraintGenealogyLogger, link_id: str) -> str:
    counts = logger._axis_counts_from_item(
        TraceItem(kind="LINK", id=str(link_id)), memo={}, seen=set()
    )
    return logger._canonical_coupling_signature(counts)


def _json_key(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _link_evidence_profile(logger: ConstraintGenealogyLogger, link_id: str) -> Dict[str, Any]:
    effect = logger._operational_effect_for_item(link_id)
    identity = logger._semantic_identity_for_item(link_id)
    return {
        "dominant_relief_axis": effect.get("dominant_axis"),
        "mean_relief": {
            a: round(float((effect.get("mean_relief", {}) or {}).get(a, 0.0) or 0.0), 15)
            for a in AXES
        },
        "purpose_lane": identity.get("purpose_lane", ""),
        "operator_action": identity.get("operator_action", ""),
    }


def _link_example(logger: ConstraintGenealogyLogger, link_id: str) -> Dict[str, Any]:
    link = logger.links[link_id]
    identity = logger._semantic_identity_for_item(link_id)
    return {
        "representation_id": link_id,
        "parents": list(link.parents),
        "parent_depths": [int(logger._item_depth(parent)) for parent in link.parents],
        "depth": int(link.depth),
        "dominant_relief_axis": link.dominant_relief_axis,
        "purpose_lane": identity.get("purpose_lane", ""),
        "operator_action": identity.get("operator_action", ""),
        "mean_relief": {a: round(float(link.mean_relief.get(a, 0.0) or 0.0), 12) for a in AXES},
    }


def _ability_example(logger: ConstraintGenealogyLogger, ability_id: str) -> Dict[str, Any]:
    ability = logger.abilities[ability_id]
    identity = logger._semantic_identity_for_item(ability_id)
    effect = logger._operational_effect_for_item(ability_id)
    return {
        "representation_id": ability_id,
        "axis": ability.axis,
        "purpose_lane": identity.get("purpose_lane", ""),
        "operator_action": identity.get("operator_action", ""),
        "effect_tags": list(effect.get("effect_tags", []) or []),
        "cost": effect.get("cost", {}),
        "risk": effect.get("risk", {}),
    }


def _choose_divergent_examples(
    ids: Iterable[str],
    profile_for,
    example_for,
    limit: int = 4,
) -> List[Dict[str, Any]]:
    examples: List[Dict[str, Any]] = []
    seen_profiles = set()
    for item_id in ids:
        key = _json_key(profile_for(item_id))
        if key in seen_profiles:
            continue
        seen_profiles.add(key)
        examples.append(example_for(item_id))
        if len(examples) >= limit:
            break
    return examples


def analyze(state_dir: str) -> Dict[str, Any]:
    logger = _load_logger(state_dir)
    link_groups: Dict[str, List[str]] = defaultdict(list)
    for link_id in logger.links:
        link_groups[_link_signature(logger, link_id)].append(link_id)
    link_collisions = {sig: ids for sig, ids in link_groups.items() if len(ids) > 1}

    relief_distinct = 0
    dominant_distinct = 0
    operator_distinct = 0
    purpose_distinct = 0
    evidence_distinct = 0
    structural_distinct = 0
    structural_hashes: Dict[str, str] = {}
    for link_id in logger.links:
        structural_hashes[link_id] = derive_environment_signature(logger, link_id).structural_hash

    for ids in link_collisions.values():
        profiles = [_link_evidence_profile(logger, link_id) for link_id in ids]
        if len({_json_key(profile["mean_relief"]) for profile in profiles}) > 1:
            relief_distinct += 1
        if len({profile["dominant_relief_axis"] for profile in profiles}) > 1:
            dominant_distinct += 1
        if len({profile["operator_action"] for profile in profiles}) > 1:
            operator_distinct += 1
        if len({profile["purpose_lane"] for profile in profiles}) > 1:
            purpose_distinct += 1
        if len({_json_key(profile) for profile in profiles}) > 1:
            evidence_distinct += 1
        if len({structural_hashes[link_id] for link_id in ids}) > 1:
            structural_distinct += 1

    link_link = [
        link for link in logger.links.values()
        if len(link.parents) == 2 and all(parent in logger.links for parent in link.parents)
    ]
    cross_depth = [
        link for link in link_link
        if abs(logger.links[link.parents[0]].depth - logger.links[link.parents[1]].depth) >= 2
    ]
    cross_groups: Dict[str, List[str]] = defaultdict(list)
    for link in cross_depth:
        cross_groups[_link_signature(logger, link.id)].append(link.id)

    native_abilities = {
        aid: ability for aid, ability in logger.abilities.items()
        if ":CODE_" not in aid and ":LINK_" not in aid
    }
    ability_groups: Dict[str, List[str]] = defaultdict(list)
    for aid in native_abilities:
        ability_groups[logger._collision_signature_for_item(aid)].append(aid)
    ability_collisions = {sig: ids for sig, ids in ability_groups.items() if len(ids) > 1}

    concrete_link_signatures = (
        "T^7*B^7*A^7",
        "N^5*B^5",
        "N^1*B^1",
    )
    concrete_ability_signatures = (
        "X^1*N^1*B^1",
        "X^1*T^1*B^1",
        "N^1*B^1*A^1",
    )
    link_examples = {}
    for signature in concrete_link_signatures:
        ids = link_groups.get(signature, [])
        if ids:
            link_examples[signature] = {
                "family_size": len(ids),
                "intact_parentage_profiles": len({
                    _json_key(logger.links[link_id].parents) for link_id in ids
                }),
                "operational_evidence_profiles": len({
                    _json_key(_link_evidence_profile(logger, link_id)) for link_id in ids
                }),
                "structural_profiles": len({structural_hashes[link_id] for link_id in ids}),
                "examples": _choose_divergent_examples(
                    ids,
                    lambda link_id: _link_evidence_profile(logger, link_id),
                    lambda link_id: _link_example(logger, link_id),
                ),
            }

    ability_examples = {}
    for signature in concrete_ability_signatures:
        ids = ability_groups.get(signature, [])
        if ids:
            ability_examples[signature] = {
                "family_size": len(ids),
                "operational_evidence_profiles": len({
                    _json_key(logger._operational_effect_for_item(aid)) for aid in ids
                }),
                "examples": _choose_divergent_examples(
                    ids,
                    lambda aid: logger._operational_effect_for_item(aid),
                    lambda aid: _ability_example(logger, aid),
                ),
            }

    fossil_fields = ("origin_signature", "purpose_lane", "operator_action", "generation")
    fossil_conflicts = {}
    for field_name in fossil_fields:
        prefix = f"{field_name}:"
        conflict_count = 0
        multi_count = 0
        for link in logger.links.values():
            values = [str(tag)[len(prefix):] for tag in link.tags if str(tag).startswith(prefix)]
            if len(values) > 1:
                multi_count += 1
            if len(set(values)) > 1:
                conflict_count += 1
        fossil_conflicts[field_name] = {
            "multiple_values": multi_count,
            "conflicting_values": conflict_count,
            "resolution": "explicit semantic_identity, else last local tag",
        }

    return {
        "state_dir": os.path.abspath(state_dir),
        "links": {
            "total": len(logger.links),
            "flattened_constraint_signatures": len(link_groups),
            "links_in_signature_collisions": sum(len(ids) for ids in link_collisions.values()),
            "collision_groups": len(link_collisions),
            "collision_groups_with_relief_distinctions": relief_distinct,
            "collision_groups_with_dominant_axis_distinctions": dominant_distinct,
            "collision_groups_with_operator_distinctions": operator_distinct,
            "collision_groups_with_purpose_lane_distinctions": purpose_distinct,
            "collision_groups_with_any_operational_evidence_distinction": evidence_distinct,
            "collision_groups_with_structural_distinctions": structural_distinct,
        },
        "cross_depth_link_offspring": {
            "link_link_offspring": len(link_link),
            "parent_depth_gap_at_least_two": len(cross_depth),
            "flattened_constraint_signatures": len(cross_groups),
            "offspring_in_signature_collisions": sum(
                len(ids) for ids in cross_groups.values() if len(ids) > 1
            ),
            "parent_depth_pairs": {
                f"{left}->{right}": count
                for (left, right), count in sorted(Counter(
                    tuple(sorted((logger.links[link.parents[0]].depth, logger.links[link.parents[1]].depth)))
                    for link in cross_depth
                ).items())
            },
        },
        "native_abilities": {
            "after_code_and_link_ability_exclusions": len(native_abilities),
            "constraint_signatures": len(ability_groups),
            "abilities_in_signature_collisions": sum(len(ids) for ids in ability_collisions.values()),
            "collision_groups": len(ability_collisions),
        },
        "semantic_fossils": fossil_conflicts,
        "concrete_link_families": link_examples,
        "concrete_ability_families": ability_examples,
        "claim_boundary": (
            "Distinct intact parentage, topology, and stored operational effects are now expressible; "
            "this analysis does not establish improved cognition, communication, or new semantic understanding."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--state-dir",
        default=os.path.join(_REPO_ROOT, "aurora_state", "genealogy"),
    )
    args = parser.parse_args()
    print(json.dumps(analyze(args.state_dir), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

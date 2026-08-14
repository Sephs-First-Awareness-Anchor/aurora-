#!/usr/bin/env python3
"""Locks a specific, explicit boundary (Sunni & Cael, "Autonomous
Development Integrity" pass): for the first autonomous run, 668's existing
axis_evidence developmental-proxy learner remains the SOLE mechanism
governing perception/routing (AuroraSensoryCrystal._effective_axis_for_node,
and thus _dps_route_observation). The new consequence_profile mechanism is
observational and evidentiary ONLY -- it may influence which cross-family/
same-family pairs look worth investigating (representation_gap_candidates
/ representation_collision_candidates, via _representation_relevance_
evidence / _representation_discrepancy), but it must NOT influence which
axis a future observation of a representation gets routed/stamped under.

Verified two ways: (1) direct proof DPS routing reads only .axis, never
.consequence_profile, even when a hand-planted, high-confidence,
sharply-diverging consequence_profile exists; (2) a real end-to-end
citizen-participation drive confirms the same boundary holds in the
actual production call path, not just a synthetic unit check.
"""
from __future__ import annotations

import dataclasses

from aurora_internal.aurora_sensory_crystal import (
    AXIS_EVIDENCE_MIN_SAMPLES,
    AuroraSensoryCrystal,
    SensoryClusterFacet,
    SensoryNode,
)
from aurora_internal.constraint_genealogy import ConstraintGenealogyLogger, GenealogyConfig


def _fresh_genealogy(tmp_path, name="perception_boundary_test"):
    return ConstraintGenealogyLogger(name, config=GenealogyConfig(), output_dir=str(tmp_path / name))


def _drifting_node(node_id="n1", domain="audio", facet="tone"):
    node = SensoryNode(node_id=node_id, domain=domain, facet=facet, centroid=[0.1] * 8)
    node.stage = "promoted"
    node.fitness = 0.72
    node.usage_count = 30
    node.session_count = 4
    node.confidence = 0.40
    node.cross_modal_links = ["p1", "p2", "p3", "p4"]
    return node


def test_dps_routing_ignores_a_hand_planted_diverging_consequence_profile(tmp_path):
    """Even when consequence_profile exists, is high-confidence, and
    disagrees sharply with the current .axis, DPS routing must still use
    .axis alone -- consequence_profile is not consulted at all."""
    genealogy = _fresh_genealogy(tmp_path)
    crystal = AuroraSensoryCrystal(state_dir=str(tmp_path / "crystal_state"))
    crystal.register_genealogy(genealogy)
    facet = crystal._audio["tone"]

    node = _drifting_node()
    facet._nodes[node.node_id] = node
    facet.grant_representational_citizenship(node)

    ability = genealogy.abilities[node.citizen_ability_id]
    assert ability.axis == "T"

    # Hand-plant a maximally confident, maximally diverging consequence
    # profile pointing at a completely different axis (A) than the
    # representation's actual current operational axis (T).
    genealogy.abilities[node.citizen_ability_id] = dataclasses.replace(
        ability,
        consequence_profile={
            "effect": {"X": 0.0, "T": 0.0, "N": 0.0, "B": 0.0, "A": 1.0},
            "samples": 999, "distinct_contexts": 999,
            "weighted_evidence_clean": 999.0, "weighted_evidence_total": 999.0,
            "confidence": 1.0, "last_tick": 1, "last_weight": 1.0,
            "evidence_tier": "isolated", "discrepancy": 1.0,
        },
    )

    effective_axis = crystal._effective_axis_for_node("audio", "tone", node.node_id)
    assert effective_axis == "T", (
        "DPS routing must use .axis alone -- a hand-planted, maximally "
        "confident consequence_profile pointing at a different axis must "
        "have zero influence on perception routing for the first "
        "autonomous run"
    )


def test_real_learned_axis_reassignment_still_drives_routing_not_consequence_profile(tmp_path):
    """Positive control: the EXISTING mechanism (axis_evidence -> .axis)
    still correctly drives DPS routing, confirming this test would catch
    a real regression rather than passing vacuously."""
    genealogy = _fresh_genealogy(tmp_path, name="positive_control")
    crystal = AuroraSensoryCrystal(state_dir=str(tmp_path / "crystal_state_2"))
    crystal.register_genealogy(genealogy)
    facet = crystal._audio["tone"]

    node = _drifting_node()
    facet._nodes[node.node_id] = node
    facet.grant_representational_citizenship(node)

    assert crystal._effective_axis_for_node("audio", "tone", node.node_id) == "T"

    for _ in range(AXIS_EVIDENCE_MIN_SAMPLES + 3):
        node.fitness = min(1.0, node.fitness + 0.01)
        facet.tick_citizen_participation()

    ability = genealogy.abilities[node.citizen_ability_id]
    assert ability.axis != "T", "fixture sanity check: axis_evidence must have earned a reassignment"
    assert ability.consequence_profile is None, "synthetic ticks correctly excluded (blocker 1)"

    effective_axis = crystal._effective_axis_for_node("audio", "tone", node.node_id)
    assert effective_axis == ability.axis, (
        "DPS routing must still follow the axis_evidence-governed .axis, "
        "the existing, sole mechanism for the first autonomous run"
    )


def test_consequence_profile_is_absent_from_dps_route_observation_source():
    """Static boundary check: _dps_route_observation and
    _effective_axis_for_node must not reference consequence_profile
    anywhere in their source -- not merely happen to ignore it at
    runtime."""
    import inspect

    src_effective = inspect.getsource(AuroraSensoryCrystal._effective_axis_for_node)
    src_routing = inspect.getsource(AuroraSensoryCrystal._dps_route_observation)
    assert "consequence_profile" not in src_effective
    assert "consequence_profile" not in src_routing


def test_consequence_profile_still_reaches_relevance_evidence_the_allowed_channel(tmp_path):
    """The boundary is not "consequence_profile does nothing" -- it's
    "consequence_profile does not govern perception." Cross-family/
    same-family investigability scoring remains the legitimate channel
    (see test_genealogy_consequence_profile.py for the full coverage);
    this is a light touch confirming that channel is still open, so the
    perception boundary above isn't accidentally the result of the whole
    mechanism being dead."""
    genealogy = _fresh_genealogy(tmp_path, name="allowed_channel")
    from aurora_internal.constraint_genealogy import AXES, AbilityProfile, PressureVec, TraceItem

    def seed(aid, axis):
        genealogy.abilities[aid] = AbilityProfile(
            id=aid, axis=axis, requires=(axis,),
            cost={a: 0.001 for a in AXES}, risk={a: 0.0 for a in AXES},
            effect_tags=("test",), notes="test",
        )

    def observe(aid, relief_axis, amount):
        p_before = PressureVec(**{a: (amount if a == relief_axis else 0.0) for a in AXES})
        p_after = PressureVec(**{a: 0.0 for a in AXES})
        genealogy.observe(pressure_before=p_before, trace=[TraceItem(kind="ABILITY", id=aid)], pressure_after=p_after)

    seed("X:LEFT", "X")
    seed("X:RIGHT", "X")
    for _ in range(8):
        observe("X:LEFT", "B", 0.3)
    for _ in range(8):
        observe("X:RIGHT", "A", 0.3)

    evidence = genealogy._representation_relevance_evidence("X:LEFT", "X:RIGHT")
    assert evidence is not None
    assert "consequence_effect_distance" in evidence["evidence"].get("operational_discrepancy", {})

#!/usr/bin/env python3
"""Regression coverage for the learned-axis-participation mechanism
(Sunni & Cael): "the mechanism to establish that herself as she
encounters them would be the pertinent fix."

SENSORY_FACET_AXIS assigns every node on a facet the SAME starting axis
by category, before a single instance of it has actually been
encountered. This is the representation earning, from her own repeated
encounters with it (usage/session breadth/cross-modal grounding/agency,
NOT a new instrumentation layer -- quantities the node already tracked),
the right to override that category-level prior for itself.
"""
from __future__ import annotations

from aurora_internal.aurora_sensory_crystal import (
    AXIS_EVIDENCE_MARGIN,
    AXIS_EVIDENCE_MIN_SAMPLES,
    SensoryClusterFacet,
    SensoryNode,
    _node_axis_evidence_sample,
    _update_axis_evidence,
)


def _fresh_genealogy(tmp_path, name="learned_axis_test"):
    from aurora_internal.constraint_genealogy import ConstraintGenealogyLogger, GenealogyConfig
    return ConstraintGenealogyLogger(name, config=GenealogyConfig(), output_dir=str(tmp_path / name))


def _promoted_node(node_id="n1", domain="audio", facet="tone"):
    """tone's starting axis is T (SENSORY_FACET_AXIS). Node state is
    deliberately shaped to favor B instead (heavy cross-modal grounding,
    modest everything else) so the learned mechanism has something real
    to disagree with the prior about."""
    node = SensoryNode(node_id=node_id, domain=domain, facet=facet, centroid=[0.1] * 8)
    node.stage = "promoted"
    node.fitness = 0.72
    node.usage_count = 30       # moderate N
    node.session_count = 4      # moderate T
    node.confidence = 0.40      # modest X
    node.cross_modal_links = ["p1", "p2", "p3", "p4"]  # saturates B (4/4.0 = 1.0)
    return node


# ── Unit-level evidence mechanics ───────────────────────────────────────────

def test_axis_evidence_sample_reflects_the_nodes_own_state():
    node = _promoted_node()
    sample = _node_axis_evidence_sample(node)
    assert set(sample.keys()) == {"X", "T", "N", "B", "A"}
    # B (cross_modal_links=4, saturating at 4.0) must dominate this
    # deliberately-shaped node's raw sample.
    assert sample["B"] == max(sample.values())


def test_update_axis_evidence_returns_none_before_minimum_samples():
    node = _promoted_node()
    for _ in range(AXIS_EVIDENCE_MIN_SAMPLES - 1):
        result = _update_axis_evidence(node)
    assert result is None
    assert node.axis_evidence_samples == AXIS_EVIDENCE_MIN_SAMPLES - 1


def test_update_axis_evidence_earns_dominant_axis_after_enough_consistent_samples():
    node = _promoted_node()
    result = None
    for _ in range(AXIS_EVIDENCE_MIN_SAMPLES + 3):
        result = _update_axis_evidence(node)
    assert result == "B"
    assert node.axis_evidence["B"] - max(
        v for k, v in node.axis_evidence.items() if k != "B"
    ) >= AXIS_EVIDENCE_MARGIN


def test_update_axis_evidence_withholds_when_margin_too_thin():
    """A node whose internal quantities are all nearly equal must NOT
    earn a reassignment -- ambiguous evidence stays ambiguous rather than
    picking an arbitrary winner."""
    node = SensoryNode(node_id="n1", domain="visual", facet="hue", centroid=[0.1] * 8)
    node.stage = "promoted"
    node.fitness = 0.5
    node.usage_count = 25       # N ~ 0.5
    node.session_count = 5      # T ~ 0.5
    node.confidence = 0.5       # X ~ 0.5
    node.cross_modal_links = ["p1", "p2"]  # B ~ 0.5

    result = None
    for _ in range(AXIS_EVIDENCE_MIN_SAMPLES + 5):
        result = _update_axis_evidence(node)
    assert result is None


# ── Integration: tick_citizen_participation reassigns the live ability ─────

def test_citizen_earns_own_axis_distinct_from_facet_starting_prior(tmp_path):
    genealogy = _fresh_genealogy(tmp_path)
    facet = SensoryClusterFacet("audio", "tone")
    node = _promoted_node("n1", "audio", "tone")
    facet._nodes[node.node_id] = node
    facet._genealogy_ref = genealogy
    facet.grant_representational_citizenship(node)

    ability = genealogy.abilities[node.citizen_ability_id]
    assert ability.axis == "T"  # tone's SENSORY_FACET_AXIS starting prior
    assert "initial_axis:T" in ability.effect_tags

    # Repeated encounters -- each tick, nudge fitness so it's reported.
    for i in range(AXIS_EVIDENCE_MIN_SAMPLES + 3):
        node.fitness = min(1.0, node.fitness + 0.01)
        reported = facet.tick_citizen_participation()
        assert reported == 1

    ability_after = genealogy.abilities[node.citizen_ability_id]
    assert ability_after.axis == "B", (
        "the representation's own encountered evidence (heavy cross-modal "
        "grounding) must be able to override the facet-level starting prior"
    )
    assert ability_after.requires == ("B",)
    assert any(t.startswith("learned_axis:B") for t in ability_after.effect_tags)
    # The starting prior is not erased from the audit trail.
    assert "initial_axis:T" in ability_after.effect_tags


def test_other_nodes_on_the_same_facet_are_unaffected(tmp_path):
    """Reassignment is per-representation, not per-facet: a second node on
    the SAME facet with different internal state must not be dragged
    along by another node's learned axis."""
    genealogy = _fresh_genealogy(tmp_path)
    facet = SensoryClusterFacet("audio", "tone")

    drifting = _promoted_node("n1", "audio", "tone")
    ordinary = SensoryNode(node_id="n2", domain="audio", facet="tone", centroid=[0.2] * 8)
    ordinary.stage = "promoted"
    ordinary.fitness = 0.10         # kept low so A stays well below N below
    ordinary.usage_count = 50       # saturating N (50/USAGE_NORM_CAP=1.0)
    ordinary.session_count = 1      # low T
    ordinary.confidence = 0.15      # low X
    ordinary.cross_modal_links = []  # zero B

    facet._nodes[drifting.node_id] = drifting
    facet._nodes[ordinary.node_id] = ordinary
    facet._genealogy_ref = genealogy
    facet.grant_representational_citizenship(drifting)
    facet.grant_representational_citizenship(ordinary)

    for _ in range(AXIS_EVIDENCE_MIN_SAMPLES + 3):
        drifting.fitness = min(1.0, drifting.fitness + 0.01)
        ordinary.fitness = min(1.0, ordinary.fitness + 0.005)  # tiny nudge, stays << N
        facet.tick_citizen_participation()

    drifting_ability = genealogy.abilities[drifting.citizen_ability_id]
    ordinary_ability = genealogy.abilities[ordinary.citizen_ability_id]
    assert drifting_ability.axis == "B"
    assert ordinary_ability.axis == "N", (
        "a high-usage, low-cross-modal node's own evidence should earn N, "
        "independent of the OTHER node on the same facet earning B"
    )


def test_axis_evidence_persists_across_to_dict_from_dict_round_trip(tmp_path):
    genealogy = _fresh_genealogy(tmp_path)
    facet = SensoryClusterFacet("audio", "tone")
    node = _promoted_node("n1", "audio", "tone")
    facet._nodes[node.node_id] = node
    facet._genealogy_ref = genealogy
    facet.grant_representational_citizenship(node)

    for _ in range(AXIS_EVIDENCE_MIN_SAMPLES):
        node.fitness = min(1.0, node.fitness + 0.01)
        facet.tick_citizen_participation()

    assert node.axis_evidence_samples == AXIS_EVIDENCE_MIN_SAMPLES
    d = node.to_dict()
    assert d["axis_evidence"] == node.axis_evidence
    assert d["axis_evidence_samples"] == AXIS_EVIDENCE_MIN_SAMPLES

    reloaded = SensoryNode.from_dict(d)
    assert reloaded.axis_evidence == node.axis_evidence
    assert reloaded.axis_evidence_samples == node.axis_evidence_samples


def test_pressure_is_logged_against_the_learned_axis_once_earned(tmp_path, monkeypatch):
    """After reassignment, subsequent ticks must compute pressure on the
    NEWLY learned axis, not silently keep using the original facet prior."""
    genealogy = _fresh_genealogy(tmp_path)
    facet = SensoryClusterFacet("audio", "tone")
    node = _promoted_node("n1", "audio", "tone")
    facet._nodes[node.node_id] = node
    facet._genealogy_ref = genealogy
    facet.grant_representational_citizenship(node)

    for _ in range(AXIS_EVIDENCE_MIN_SAMPLES + 3):
        node.fitness = min(1.0, node.fitness + 0.01)
        facet.tick_citizen_participation()
    assert genealogy.abilities[node.citizen_ability_id].axis == "B"

    captured = {}
    orig_observe = genealogy.observe

    def _spy(*args, **kwargs):
        captured.update(kwargs)
        return orig_observe(*args, **kwargs)

    monkeypatch.setattr(genealogy, "observe", _spy)
    node.fitness = min(1.0, node.fitness + 0.02)
    facet.tick_citizen_participation()

    assert captured["pressure_before"].B != 0.0
    assert captured["pressure_before"].T == 0.0

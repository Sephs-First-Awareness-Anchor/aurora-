#!/usr/bin/env python3
"""Regression coverage for consequence-derived representational self-
governance (Sunni & Cael, "the architecture pass"): genealogy's own
confidence-weighted, bounded EMA of the REAL, measured 5-axis relief a
representation was actually present for -- distinct from, and additive
to, sensory citizenship's developmental-proxy scalar-axis learner
(confidence/usage/session/cross-modal/fitness -> a single .axis label),
which this does NOT replace or govern.

Explicit scope, per direct instruction: this lives in genealogy itself
(not sensory-scoped), applies uniformly to AbilityProfile AND
ConstraintLink (full genealogy, not abilities only), and is built on top
of the activity registry's isolation_confidence() rather than duplicating
it.
"""
from __future__ import annotations

from aurora_internal.constraint_genealogy import (
    AXES,
    AbilityProfile,
    ConstraintGenealogyLogger,
    ConstraintLink,
    GenealogyConfig,
    PressureVec,
    TraceItem,
)


def _fresh_genealogy(tmp_path, name="consequence_profile_test", **cfg_overrides):
    cfg = GenealogyConfig(**cfg_overrides) if cfg_overrides else GenealogyConfig()
    return ConstraintGenealogyLogger(name, config=cfg, output_dir=str(tmp_path / name))


def _seed_ability(genealogy, aid, axis="X"):
    genealogy.abilities[aid] = AbilityProfile(
        id=aid, axis=axis, requires=(axis,),
        cost={a: 0.001 for a in AXES},
        risk={a: 0.0 for a in AXES},
        effect_tags=("test",), notes="test",
    )


def _seed_link(genealogy, lid, axis="X", parents=None):
    genealogy.links[lid] = ConstraintLink(
        id=lid, parents=list(parents or ["X:A", "T:B"]), depth=1, created_at_tick=0,
        count=1, mean_relief={a: 0.0 for a in AXES}, mean_cost={a: 0.0 for a in AXES},
        mean_x_risk=0.0, stdev_relief={a: 0.0 for a in AXES}, dominant_relief_axis=axis,
        tags=[],
    )


def _observe_relief_on(genealogy, *ids, relief_axis="B", relief_amount=0.2):
    p_before = PressureVec(**{a: (relief_amount if a == relief_axis else 0.0) for a in AXES})
    p_after = PressureVec(**{a: 0.0 for a in AXES})
    trace = [TraceItem(kind=("LINK" if i in genealogy.links else "ABILITY"), id=i) for i in ids]
    return genealogy.observe(pressure_before=p_before, trace=trace, pressure_after=p_after)


# ── Basic attribution ───────────────────────────────────────────────────────

def test_attribution_moves_effect_toward_real_measured_relief_not_declared_axis(tmp_path):
    genealogy = _fresh_genealogy(tmp_path)
    _seed_ability(genealogy, "X:A", axis="X")

    for _ in range(8):
        _observe_relief_on(genealogy, "X:A", relief_axis="B", relief_amount=0.2)

    profile = genealogy.abilities["X:A"].consequence_profile
    assert profile is not None
    assert profile["effect"]["B"] > 0.05, "measured relief on B must move the profile toward B"
    assert profile["effect"]["X"] == 0.0, "no relief was ever measured on the declared axis X"
    assert profile["samples"] == 8


def test_attribution_applies_to_links_too_not_only_abilities(tmp_path):
    """Full genealogy, not sensory/ability-scoped: a promoted ConstraintLink
    is exactly as much a representation as the ability that composed it."""
    genealogy = _fresh_genealogy(tmp_path)
    _seed_link(genealogy, "L:combo", axis="X")

    for _ in range(8):
        _observe_relief_on(genealogy, "L:combo", relief_axis="N", relief_amount=0.3)

    profile = genealogy.links["L:combo"].consequence_profile
    assert profile is not None
    assert profile["effect"]["N"] > 0.05


def test_non_relief_ticks_do_not_attribute_consequence(tmp_path):
    """There is no consequence to attribute when nothing measurably
    happened -- observe()'s noise filter already returns None for these."""
    genealogy = _fresh_genealogy(tmp_path)
    _seed_ability(genealogy, "X:A")
    zero = PressureVec(**{a: 0.0 for a in AXES})
    result = genealogy.observe(pressure_before=zero, trace=[TraceItem(kind="ABILITY", id="X:A")], pressure_after=zero)
    assert result is None
    assert genealogy.abilities["X:A"].consequence_profile is None


# ── Evidence weighting / hierarchy ──────────────────────────────────────────

def test_crowded_coactivation_moves_the_profile_less_than_isolated_activity(tmp_path):
    genealogy = _fresh_genealogy(tmp_path)
    for aid in ("X:A", "N:C", "B:D", "A:E"):
        _seed_ability(genealogy, aid, axis=aid[0])

    for other in ("N:C", "B:D", "A:E"):
        _observe_relief_on(genealogy, "X:A", other, relief_axis="B", relief_amount=0.2)
    crowded_effect_b = genealogy.abilities["X:A"].consequence_profile["effect"]["B"]

    genealogy2 = _fresh_genealogy(tmp_path, name="isolated_compare")
    _seed_ability(genealogy2, "X:A")
    for _ in range(3):
        _observe_relief_on(genealogy2, "X:A", relief_axis="B", relief_amount=0.2)
    isolated_effect_b = genealogy2.abilities["X:A"].consequence_profile["effect"]["B"]

    assert crowded_effect_b < isolated_effect_b


def test_repeated_isolated_evidence_reaches_full_confidence(tmp_path):
    """Regression for a real bug caught during implementation: the first
    confidence formula required BOTH sample volume AND distinct-context
    diversity unconditionally, which meant pure repeated isolation (always
    the same "alone" context, distinct_contexts stuck at 1) scored LOWER
    confidence than a handful of crowded, ever-different-partner
    co-activations -- exactly backwards, since isolated evidence carries
    no attribution ambiguity at all and should outrank any co-activated
    evidence in the hierarchy."""
    genealogy = _fresh_genealogy(tmp_path)
    _seed_ability(genealogy, "X:A")
    for _ in range(8):
        _observe_relief_on(genealogy, "X:A", relief_axis="B", relief_amount=0.2)
    assert genealogy.abilities["X:A"].consequence_profile["confidence"] == 1.0


def test_isolated_confidence_outranks_crowded_varied_confidence(tmp_path):
    genealogy_iso = _fresh_genealogy(tmp_path, name="iso")
    _seed_ability(genealogy_iso, "X:A")
    for _ in range(8):
        _observe_relief_on(genealogy_iso, "X:A", relief_axis="B", relief_amount=0.2)

    genealogy_crowd = _fresh_genealogy(tmp_path, name="crowd")
    for aid in ("X:A", "N:C", "B:D", "A:E"):
        _seed_ability(genealogy_crowd, aid, axis=aid[0])
    for other in ("N:C", "B:D", "A:E"):
        _observe_relief_on(genealogy_crowd, "X:A", other, relief_axis="B", relief_amount=0.2)

    c_iso = genealogy_iso.abilities["X:A"].consequence_profile["confidence"]
    c_crowd = genealogy_crowd.abilities["X:A"].consequence_profile["confidence"]
    assert c_iso > c_crowd


def test_pair_specific_repeated_coactivation_stays_capped_by_context_diversity(tmp_path):
    """Repeating with the SAME one other representation, no matter how many
    times, must not accumulate confidence the way genuinely varied
    co-activation does -- that would let a spurious pair-specific
    correlation masquerade as this representation's own effect."""
    genealogy = _fresh_genealogy(tmp_path)
    _seed_ability(genealogy, "X:A")
    _seed_ability(genealogy, "N:C", axis="N")
    for _ in range(20):
        _observe_relief_on(genealogy, "X:A", "N:C", relief_axis="B", relief_amount=0.2)

    profile = genealogy.abilities["X:A"].consequence_profile
    assert profile["distinct_contexts"] == 1
    assert profile["confidence"] < 0.5, "same-partner repetition alone should not earn strong confidence"


def test_distinct_contexts_is_bounded_by_config_cap(tmp_path):
    genealogy = _fresh_genealogy(tmp_path, name="capped", CONSEQUENCE_DISTINCT_CONTEXT_CAP=3)
    _seed_ability(genealogy, "X:A")
    for i in range(10):
        other = f"N:OTHER_{i}"
        _seed_ability(genealogy, other, axis="N")
        _observe_relief_on(genealogy, "X:A", other, relief_axis="B", relief_amount=0.2)
    assert genealogy.abilities["X:A"].consequence_profile["distinct_contexts"] <= 3


# ── Discrepancy ──────────────────────────────────────────────────────────────

def test_discrepancy_reflects_distance_between_declared_axis_and_measured_effect(tmp_path):
    genealogy = _fresh_genealogy(tmp_path)
    _seed_ability(genealogy, "X:A", axis="X")
    for _ in range(8):
        _observe_relief_on(genealogy, "X:A", relief_axis="B", relief_amount=0.2)
    profile = genealogy.abilities["X:A"].consequence_profile
    assert profile["discrepancy"] > 0.5, "measured effect entirely on B vs a declared X prior should show large discrepancy"


def test_discrepancy_is_low_when_measured_effect_matches_declared_axis(tmp_path):
    genealogy = _fresh_genealogy(tmp_path)
    _seed_ability(genealogy, "X:A", axis="B")
    for _ in range(8):
        _observe_relief_on(genealogy, "X:A", relief_axis="B", relief_amount=0.2)
    profile = genealogy.abilities["X:A"].consequence_profile
    assert profile["discrepancy"] < 0.1


# ── Relevance-index invalidation ────────────────────────────────────────────

def test_attribution_marks_the_representation_index_dirty(tmp_path):
    genealogy = _fresh_genealogy(tmp_path)
    _seed_ability(genealogy, "X:A")
    before = genealogy._representation_index_dirty_counter
    _observe_relief_on(genealogy, "X:A", relief_axis="B", relief_amount=0.2)
    assert genealogy._representation_index_dirty_counter > before


# ── Staged experiment tier (top of the evidence hierarchy) ─────────────────

def _experiment_config(**overrides):
    values = dict(
        K_MIN=4, RELIEF_EPS=0.000001, RELIEF_TOTAL_EPS=0.000001, RELIEF_PROMOTE_MIN=0.00001,
        POS_FRACTION_MIN=0.50, NET_MIN=0.00000001, X_RISK_MAX=1.0, COST_TO_RELIEF_SCALE=0.0,
        RELIEF_TOLERANCE_ENABLED=False, THRESHOLD_PRESSURE_ENABLED=False, STAGNATION_BOOTSTRAP_RATIO=0.0,
        REPRESENTATION_GAP_CANDIDATES_PER_ITEM=12, REPRESENTATION_GAP_MAX_PER_EVENT=24,
        REPRESENTATION_COLLISION_MAX_PER_EVENT=32, REPRESENTATION_INQUIRY_REFRACTORY_CYCLES=0,
    )
    values.update(overrides)
    return GenealogyConfig(**values)


def _experiment_link(link_id, parents, depth, axis="X", *, lane="meaning", operator="shared_operation"):
    mean_relief = {a: 0.0 for a in AXES}
    mean_relief[axis] = 0.05
    return ConstraintLink(
        id=link_id, parents=list(parents), depth=depth, created_at_tick=depth, count=12,
        mean_relief=mean_relief, mean_cost={a: 0.0 for a in AXES}, mean_x_risk=0.0,
        stdev_relief={a: 0.0 for a in AXES}, dominant_relief_axis=axis,
        tags=[f"purpose_lane:{lane}", f"operator_action:{operator}", f"generation:{depth}"],
    )


def test_staged_representation_experiment_is_attributed_at_full_weight_regardless_of_crowding(tmp_path):
    """complete_representation_experiment() calls the SAME observe() every
    other subsystem uses -- no second promotion authority, no feature-
    specific threshold. Its evidence must reach _attribute_consequence()
    through that same call, tagged as the top tier, not bypassed."""
    genealogy = ConstraintGenealogyLogger("staged", config=_experiment_config(), output_dir=str(tmp_path / "staged"))
    early = _experiment_link("L:inquiry_early", ["X:REJECT", "T:DEFER"], 1, "X")
    deep1 = _experiment_link("L:inquiry_deep1", ["N:SPEND", "B:SEPARATE"], 1, "N")
    deep2 = _experiment_link("L:inquiry_deep2", [deep1.id, "A:CHOOSE"], 2, "A")
    deep3 = _experiment_link("L:inquiry_deep3", [deep2.id, "B:ROUTE"], 3, "B")
    deep4 = _experiment_link("L:inquiry_deep4", [deep3.id, "T:BATCH"], 4, "T")
    deep5 = _experiment_link("L:inquiry_deep5", [deep4.id, "N:REDUCE_STATE"], 5, "N")
    genealogy.links.update({x.id: x for x in (early, deep1, deep2, deep3, deep4, deep5)})

    candidates = genealogy.representation_gap_candidates([TraceItem("LINK", early.id)])
    candidate = next(c for c in candidates if c["operand_ids"] == [early.id, deep5.id])
    genealogy._record_representation_inquiries([candidate])
    staged = genealogy.stage_representation_inquiry(
        "test_consumer", {"axis_activation": {a: 0.2 for a in AXES}},
        inquiry_id=candidate["inquiry_id"], limit=1,
    )
    assert len(staged) == 1
    stage = staged[0]

    result = genealogy.complete_representation_experiment(
        stage["stage_id"], consumer="test_consumer", coactivated_ids=stage["operand_ids"],
        pressure_before={a: 1.0 for a in AXES}, pressure_after={a: 0.2 for a in AXES},
        outcome={"actual_coactivation": True, "native_measurement": {"helpful": True}},
    )
    assert result["status"] == "helpful"

    early_profile = genealogy.links[early.id].consequence_profile
    assert early_profile is not None
    assert early_profile["evidence_tier"] == "staged_experiment"
    assert early_profile["last_weight"] == 1.0


# ── Cross-representation discrepancy feeds inquiry evidence ────────────────

def test_relevance_evidence_scores_measured_consequence_divergence(tmp_path):
    """_representation_relevance_evidence() (cross-family) already scores
    declared cost/risk/mean_relief divergence between two representations;
    genuinely MEASURED consequence divergence must now contribute too, so
    representations whose real observed effects disagree become more
    investigable -- closing the loop back into representational inquiry."""
    genealogy = _fresh_genealogy(tmp_path)
    _seed_ability(genealogy, "X:LEFT", axis="X")
    _seed_ability(genealogy, "X:RIGHT", axis="X")

    # LEFT is repeatedly, isolatedly observed with real relief on B.
    for _ in range(8):
        _observe_relief_on(genealogy, "X:LEFT", relief_axis="B", relief_amount=0.3)
    # RIGHT is repeatedly, isolatedly observed with real relief on A instead.
    for _ in range(8):
        _observe_relief_on(genealogy, "X:RIGHT", relief_axis="A", relief_amount=0.3)

    evidence = genealogy._representation_relevance_evidence("X:LEFT", "X:RIGHT")
    assert evidence is not None
    discrepancy = evidence["evidence"].get("operational_discrepancy", {})
    assert "consequence_effect_distance" in discrepancy


def test_collision_discrepancy_scores_measured_consequence_divergence_too(tmp_path):
    """Same wiring, for the SAME-family exact-signature collision path
    (_representation_discrepancy / representation_collision_candidates) --
    "two representations from the same family diverging becomes
    investigable" applies here too, not only cross-family."""
    genealogy = _fresh_genealogy(tmp_path)
    _seed_ability(genealogy, "X:LEFT", axis="X")
    _seed_ability(genealogy, "X:RIGHT", axis="X")
    for _ in range(8):
        _observe_relief_on(genealogy, "X:LEFT", relief_axis="B", relief_amount=0.3)
    for _ in range(8):
        _observe_relief_on(genealogy, "X:RIGHT", relief_axis="A", relief_amount=0.3)

    discrepancy = genealogy._representation_discrepancy("X:LEFT", "X:RIGHT")
    assert discrepancy is not None
    assert "consequence_effect_distance" in discrepancy["evidence"]


# ── Persistence ──────────────────────────────────────────────────────────────

def test_ability_consequence_profile_round_trips_through_to_dict(tmp_path):
    genealogy = _fresh_genealogy(tmp_path)
    _seed_ability(genealogy, "X:A")
    for _ in range(8):
        _observe_relief_on(genealogy, "X:A", relief_axis="B", relief_amount=0.2)
    ability = genealogy.abilities["X:A"]
    d = ability.to_dict()
    assert d["consequence_profile"]["effect"]["B"] > 0.0

    restored = AbilityProfile(
        id=d["id"], axis=d["axis"], requires=tuple(d["requires"]),
        cost=d["cost"], risk=d["risk"], effect_tags=tuple(d["effect_tags"]), notes=d["notes"],
        consequence_profile=dict(d["consequence_profile"]),
    )
    assert restored.consequence_profile == ability.consequence_profile


def test_link_consequence_profile_round_trips_through_constraint_link_from_dict(tmp_path):
    from aurora_internal.constraint_genealogy import constraint_link_from_dict

    genealogy = _fresh_genealogy(tmp_path)
    _seed_link(genealogy, "L:combo", axis="X")
    for _ in range(8):
        _observe_relief_on(genealogy, "L:combo", relief_axis="N", relief_amount=0.3)
    link = genealogy.links["L:combo"]
    d = link.to_dict()
    assert d["consequence_profile"]["effect"]["N"] > 0.0

    restored = constraint_link_from_dict(d, fallback_id=link.id)
    assert restored.consequence_profile == link.consequence_profile


def test_augment_ability_profile_with_origin_does_not_drop_consequence_profile(tmp_path):
    """Same field-dropping bug class already caught for structured_state/
    topology_id/semantic_variant_id in this function -- consequence_profile
    must survive every normalize_ability_origins() pass, including the one
    _restore_genealogy_state() runs automatically after loading abilities
    from disk."""
    from aurora_internal.constraint_genealogy import _augment_ability_profile_with_origin

    ability = AbilityProfile(
        id="X:A", axis="X", requires=("X",), cost={a: 0.0 for a in AXES}, risk={a: 0.0 for a in AXES},
        effect_tags=(), notes="",
        consequence_profile={"effect": {a: 0.1 for a in AXES}, "samples": 3, "confidence": 0.5},
    )
    augmented = _augment_ability_profile_with_origin(ability)
    assert augmented.consequence_profile == ability.consequence_profile


def test_aurora_runtime_restore_genealogy_state_preserves_consequence_profile(tmp_path):
    import json

    genealogy = _fresh_genealogy(tmp_path, name="restore_test")
    _seed_ability(genealogy, "X:A")
    for _ in range(8):
        _observe_relief_on(genealogy, "X:A", relief_axis="B", relief_amount=0.2)

    output_dir = str(tmp_path / "restore_test")
    abilities_path = f"{output_dir}/{genealogy.cfg.ABILITIES_FILE}"
    with open(abilities_path, "w", encoding="utf-8") as fh:
        json.dump({aid: ab.to_dict() for aid, ab in genealogy.abilities.items()}, fh)

    from aurora_runtime import _restore_genealogy_state

    fresh_genealogy = ConstraintGenealogyLogger("restore_test_2", config=GenealogyConfig(), output_dir=output_dir)
    _restore_genealogy_state(fresh_genealogy, output_dir=output_dir)
    restored_profile = fresh_genealogy.abilities["X:A"].consequence_profile
    assert restored_profile is not None
    assert restored_profile["effect"]["B"] > 0.0


# ── Real sensory citizenship integration ────────────────────────────────────

def test_sensory_citizen_accumulates_consequence_profile_alongside_axis_evidence(tmp_path):
    """Both mechanisms coexist on the SAME ability without interfering: the
    developmental-proxy axis_evidence learner (untouched) continues to
    govern .axis reassignment exactly as before; consequence_profile is a
    genuinely separate, additional field genealogy itself computes from
    real observe() ticks -- proven here through a REAL sensory citizen's
    own tick_citizen_participation() calls, not a synthetic trace."""
    from aurora_internal.aurora_sensory_crystal import SensoryClusterFacet, SensoryNode

    genealogy = _fresh_genealogy(tmp_path)
    facet = SensoryClusterFacet("audio", "tone")
    node = SensoryNode(node_id="n1", domain="audio", facet="tone", centroid=[0.1] * 8)
    node.stage = "promoted"
    node.fitness = 0.6
    node.usage_count = 10
    node.session_count = 2
    facet._nodes[node.node_id] = node
    facet._genealogy_ref = genealogy
    facet.grant_representational_citizenship(node)

    for i in range(6):
        node.fitness = min(1.0, node.fitness + 0.02)
        facet.tick_citizen_participation()

    ability = genealogy.abilities[node.citizen_ability_id]
    assert node.axis_evidence, "the pre-existing developmental-proxy axis_evidence learner must be untouched"
    # consequence_profile is genealogy's own, separate, additional measurement.
    assert ability.consequence_profile is not None, "real observe() ticks from citizen participation must feed the new mechanism too"
    assert ability.consequence_profile["samples"] >= 1

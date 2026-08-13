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


# ── Discrepancy weighted by confidence (Autonomous Development Integrity, ──
# ── blocker 3) ───────────────────────────────────────────────────────────

def test_low_confidence_consequence_divergence_scores_far_less_than_high_confidence(tmp_path):
    """A single crowded (near-zero-confidence) sample and a well-
    established (high-confidence) profile showing the IDENTICAL raw
    direction of divergence must NOT contribute the same discrepancy
    score -- weak evidence must not masquerade as established behavior."""
    genealogy_weak = _fresh_genealogy(tmp_path, name="weak")
    _seed_ability(genealogy_weak, "X:LEFT", axis="X")
    _seed_ability(genealogy_weak, "X:RIGHT", axis="X")
    for aid in ("N:C", "B:D", "A:E"):
        _seed_ability(genealogy_weak, aid, axis=aid[0])
    # One single, heavily crowded observation each -- minimal confidence.
    _observe_relief_on(genealogy_weak, "X:LEFT", "N:C", "B:D", "A:E", relief_axis="B", relief_amount=0.3)
    _observe_relief_on(genealogy_weak, "X:RIGHT", "N:C", "B:D", "A:E", relief_axis="A", relief_amount=0.3)
    weak_evidence = genealogy_weak._representation_relevance_evidence("X:LEFT", "X:RIGHT")
    weak_distance = (
        (weak_evidence["evidence"].get("operational_discrepancy", {}) or {}).get("consequence_effect_distance", 0.0)
        if weak_evidence else 0.0
    )

    genealogy_strong = _fresh_genealogy(tmp_path, name="strong")
    _seed_ability(genealogy_strong, "X:LEFT", axis="X")
    _seed_ability(genealogy_strong, "X:RIGHT", axis="X")
    for _ in range(8):
        _observe_relief_on(genealogy_strong, "X:LEFT", relief_axis="B", relief_amount=0.3)
    for _ in range(8):
        _observe_relief_on(genealogy_strong, "X:RIGHT", relief_axis="A", relief_amount=0.3)
    strong_evidence = genealogy_strong._representation_relevance_evidence("X:LEFT", "X:RIGHT")
    strong_distance = strong_evidence["evidence"]["operational_discrepancy"]["consequence_effect_distance"]

    assert weak_distance < strong_distance


def test_near_zero_confidence_pair_contributes_almost_nothing_to_discrepancy_score(tmp_path):
    """A single, heavily crowded sample earns near-zero confidence (not
    exactly zero -- the confidence formula is continuous, not a hard
    cutoff). Its contribution to the discrepancy score must be
    correspondingly tiny, nowhere near what a fully-established,
    high-confidence divergence would score."""
    genealogy = _fresh_genealogy(tmp_path)
    _seed_ability(genealogy, "X:LEFT", axis="X")
    _seed_ability(genealogy, "X:RIGHT", axis="X")
    for aid in ("N:C", "B:D", "A:E"):
        _seed_ability(genealogy, aid, axis=aid[0])
    # A single crowded sample -- confidence stays near zero for both sides.
    _observe_relief_on(genealogy, "X:LEFT", "N:C", "B:D", "A:E", relief_axis="B", relief_amount=0.3)
    _observe_relief_on(genealogy, "X:RIGHT", "N:C", "B:D", "A:E", relief_axis="A", relief_amount=0.3)

    left_confidence = genealogy.abilities["X:LEFT"].consequence_profile["confidence"]
    assert left_confidence < 0.05, "fixture sanity check: one crowded sample must earn near-zero confidence"

    discrepancy = genealogy._representation_discrepancy("X:LEFT", "X:RIGHT")
    operational = (discrepancy or {}).get("evidence", {}).get("operational_discrepancy", {})
    weak_distance = operational.get("consequence_effect_distance", 0.0)
    assert weak_distance < 0.05, "near-zero confidence must keep the score contribution correspondingly tiny"


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


# ── Context-diversity persistence across restart (Autonomous Development ──
# ── Integrity, blocker 4) ───────────────────────────────────────────────

def test_context_signatures_are_persisted_on_the_profile(tmp_path):
    genealogy = _fresh_genealogy(tmp_path)
    _seed_ability(genealogy, "X:A")
    _seed_ability(genealogy, "N:C", axis="N")
    _seed_ability(genealogy, "B:D", axis="B")
    _observe_relief_on(genealogy, "X:A", "N:C", relief_axis="B", relief_amount=0.2)
    _observe_relief_on(genealogy, "X:A", "B:D", relief_axis="B", relief_amount=0.2)

    profile = genealogy.abilities["X:A"].consequence_profile
    assert profile["distinct_contexts"] == 2
    sigs = profile["context_signatures"]
    assert sorted(sigs, key=str) == sorted([["N:C"], ["B:D"]], key=str)


def test_distinct_contexts_does_not_reset_or_double_count_after_restart(tmp_path):
    """The exact bug this blocker fixes: without persisting context
    signatures, a restarted process would re-treat an already-seen
    co-activation context as novel, inflating distinct_contexts (and
    therefore confidence) beyond what the accumulated evidence actually
    supports."""
    import json

    genealogy = _fresh_genealogy(tmp_path, name="restart_diversity")
    _seed_ability(genealogy, "X:A")
    _seed_ability(genealogy, "N:C", axis="N")
    _seed_ability(genealogy, "B:D", axis="B")
    _observe_relief_on(genealogy, "X:A", "N:C", relief_axis="B", relief_amount=0.2)
    _observe_relief_on(genealogy, "X:A", "B:D", relief_axis="B", relief_amount=0.2)
    assert genealogy.abilities["X:A"].consequence_profile["distinct_contexts"] == 2

    output_dir = str(tmp_path / "restart_diversity")
    abilities_path = f"{output_dir}/{genealogy.cfg.ABILITIES_FILE}"
    with open(abilities_path, "w", encoding="utf-8") as fh:
        json.dump({aid: ab.to_dict() for aid, ab in genealogy.abilities.items()}, fh)

    from aurora_runtime import _restore_genealogy_state

    restarted = ConstraintGenealogyLogger("restart_diversity_2", config=GenealogyConfig(), output_dir=output_dir)
    _restore_genealogy_state(restarted, output_dir=output_dir)
    assert restarted.abilities["X:A"].consequence_profile["distinct_contexts"] == 2
    assert restarted._consequence_contexts_seen["X:A"] == {frozenset(["N:C"]), frozenset(["B:D"])}

    # Re-observing the SAME two contexts post-restart must not grow the count.
    for aid in ("N:C", "B:D"):
        _seed_ability(restarted, aid, axis=aid[0])
    _observe_relief_on(restarted, "X:A", "N:C", relief_axis="B", relief_amount=0.2)
    _observe_relief_on(restarted, "X:A", "B:D", relief_axis="B", relief_amount=0.2)
    assert restarted.abilities["X:A"].consequence_profile["distinct_contexts"] == 2

    # A genuinely NEW context must still be recognized as new.
    _seed_ability(restarted, "A:E", axis="A")
    _observe_relief_on(restarted, "X:A", "A:E", relief_axis="B", relief_amount=0.2)
    assert restarted.abilities["X:A"].consequence_profile["distinct_contexts"] == 3


def test_rehydrate_consequence_contexts_covers_links_too(tmp_path):
    from aurora_internal.constraint_genealogy import constraint_link_from_dict

    genealogy = _fresh_genealogy(tmp_path)
    _seed_link(genealogy, "L:combo", axis="X")
    _seed_ability(genealogy, "N:C", axis="N")
    _observe_relief_on(genealogy, "L:combo", "N:C", relief_axis="B", relief_amount=0.2)
    link_dict = genealogy.links["L:combo"].to_dict()

    fresh = _fresh_genealogy(tmp_path, name="link_rehydrate")
    fresh.links["L:combo"] = constraint_link_from_dict(link_dict, fallback_id="L:combo")
    n = fresh.rehydrate_consequence_contexts()
    assert n >= 1
    assert fresh._consequence_contexts_seen["L:combo"] == genealogy._consequence_contexts_seen["L:combo"]


# ── R+S relational credit (Autonomous Development Integrity, blocker 2) ────

def test_unpromoted_pair_evidence_is_jointly_discounted_not_double_credited(tmp_path):
    """Two co-active abilities with no promoted relation yet must NOT each
    receive full individual credit for the SAME tick's relief -- that would
    double-spend a single joint measurement as if R alone and S alone had
    each independently produced the entire observed effect."""
    genealogy = _fresh_genealogy(tmp_path)
    _seed_ability(genealogy, "X:R")
    _seed_ability(genealogy, "X:S")
    for _ in range(8):
        _observe_relief_on(genealogy, "X:R", "X:S", relief_axis="B", relief_amount=0.2)
    paired_effect_b = genealogy.abilities["X:R"].consequence_profile["effect"]["B"]
    assert genealogy.abilities["X:S"].consequence_profile["effect"]["B"] == paired_effect_b

    genealogy_isolated = _fresh_genealogy(tmp_path, name="isolated_r")
    _seed_ability(genealogy_isolated, "X:R")
    for _ in range(8):
        _observe_relief_on(genealogy_isolated, "X:R", relief_axis="B", relief_amount=0.2)
    isolated_effect_b = genealogy_isolated.abilities["X:R"].consequence_profile["effect"]["B"]

    assert paired_effect_b < isolated_effect_b, (
        "un-promoted joint evidence must be discounted relative to a genuinely "
        "isolated single-item series, not credited at full individual weight"
    )


def test_promoted_relation_absorbs_pair_evidence_instead_of_individual_credit(tmp_path):
    """Once R+S are unified by a promoted ConstraintLink, their joint
    evidence must land on the RELATION -- the link already IS what "R+S
    jointly" means as a representation -- not be split/duplicated across
    the two abilities individually."""
    genealogy = _fresh_genealogy(tmp_path)
    _seed_ability(genealogy, "X:R")
    _seed_ability(genealogy, "X:S")
    _seed_link(genealogy, "L:rs", axis="X", parents=["X:R", "X:S"])
    genealogy._links_by_parents[("X:R", "X:S")] = "L:rs"

    for _ in range(8):
        _observe_relief_on(genealogy, "X:R", "X:S", relief_axis="B", relief_amount=0.2)

    assert genealogy.abilities["X:R"].consequence_profile is None
    assert genealogy.abilities["X:S"].consequence_profile is None
    link_profile = genealogy.links["L:rs"].consequence_profile
    assert link_profile is not None
    assert link_profile["effect"]["B"] > 0.0
    assert link_profile["samples"] == 8


def test_individual_isolated_trace_is_unaffected_by_the_relation_logic(tmp_path):
    """Sanity boundary: a single-item trace (the common case, and the
    majority of existing call sites) must behave exactly as before --
    joint_discount only applies when len(ids) > 1."""
    genealogy = _fresh_genealogy(tmp_path)
    _seed_ability(genealogy, "X:A")
    for _ in range(8):
        _observe_relief_on(genealogy, "X:A", relief_axis="B", relief_amount=0.2)
    assert genealogy.abilities["X:A"].consequence_profile["last_weight"] == 1.0


def test_overlapping_promoted_relations_do_not_each_get_full_credit(tmp_path):
    """Real bug caught in review (chatgpt-codex-connector, PR #149): when a
    trace's pairs match MORE THAN ONE promoted relation -- e.g. a 3-item
    trace where A+B, B+C, and A+C have all separately been promoted into
    links -- the relation loop credited EACH matched link independently at
    its own full weight, summing to 1.5x (isolated) or 3x (staged) a
    single relief event. Reproduced directly before this fix: three links
    each scored last_weight=0.5 for one isolated tick, summing to 1.5.
    Fixed by dividing by how many relations are claiming a share."""
    genealogy = _fresh_genealogy(tmp_path)
    for aid in ("A", "B", "C"):
        _seed_ability(genealogy, aid, axis="X")
    for lid, parents in (("L:AB", ("A", "B")), ("L:BC", ("B", "C")), ("L:AC", ("A", "C"))):
        _seed_link(genealogy, lid, axis="X", parents=list(parents))
        for i in range(len(parents)):
            for j in range(len(parents)):
                if i != j:
                    genealogy._links_by_parents[(parents[i], parents[j])] = lid

    _observe_relief_on(genealogy, "A", "B", "C", relief_axis="B", relief_amount=0.3)

    total_weight = sum(
        genealogy.links[lid].consequence_profile["last_weight"]
        for lid in ("L:AB", "L:BC", "L:AC")
    )
    assert total_weight <= 1.0001, (
        "the combined weight credited across all matched relations for a "
        "SINGLE relief event must not exceed 1.0"
    )


def test_single_matched_relation_is_unaffected_by_the_overlap_discount(tmp_path):
    """Sanity boundary: the common case (exactly one promoted relation
    matches) must be unaffected by the multi-relation discount -- it only
    applies when len(relation_targets) > 1."""
    genealogy = _fresh_genealogy(tmp_path)
    _seed_ability(genealogy, "X:R")
    _seed_ability(genealogy, "X:S")
    _seed_link(genealogy, "L:rs", axis="X", parents=["X:R", "X:S"])
    genealogy._links_by_parents[("X:R", "X:S")] = "L:rs"

    for _ in range(8):
        _observe_relief_on(genealogy, "X:R", "X:S", relief_axis="B", relief_amount=0.2)
    assert genealogy.links["L:rs"].consequence_profile["last_weight"] == 1.0


# ── Real sensory citizenship integration ────────────────────────────────────

def test_sensory_citizen_participation_does_not_feed_the_consequence_learner(tmp_path):
    """Autonomous Development Integrity pass, blocker 1: tick_citizen_
    participation()'s pressure is derived from the node's OWN fitness
    self-assessment, not a measured world/environment outcome. Crediting
    that to consequence_profile would let a representation improve its own
    confidence score by improving its own confidence score. The pre-
    existing developmental-proxy axis_evidence learner (untouched) must
    still accumulate from these ticks exactly as before -- only the NEW
    consequence learner must decline to treat them as measured
    consequence."""
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
    assert ability.consequence_profile is None, (
        "synthetic fitness-derived sensory ticks must NOT be credited to "
        "consequence_profile as if they were measured world consequences"
    )


def test_synthetic_self_assessment_flag_is_the_exact_mechanism_that_excludes_it(tmp_path):
    """Direct proof the exclusion is the notes flag, not an accident of
    the sensory fixture -- a synthetic-tagged observe() call is skipped
    regardless of caller, and an otherwise-identical untagged call is not."""
    genealogy = _fresh_genealogy(tmp_path)
    _seed_ability(genealogy, "X:A")

    p_before = PressureVec(**{a: (0.2 if a == "B" else 0.0) for a in AXES})
    p_after = PressureVec(**{a: 0.0 for a in AXES})
    genealogy.observe(
        pressure_before=p_before,
        trace=[TraceItem(kind="ABILITY", id="X:A")],
        pressure_after=p_after,
        notes={"synthetic_self_assessment": True},
    )
    assert genealogy.abilities["X:A"].consequence_profile is None

    genealogy.observe(
        pressure_before=p_before,
        trace=[TraceItem(kind="ABILITY", id="X:A")],
        pressure_after=p_after,
    )
    assert genealogy.abilities["X:A"].consequence_profile is not None

#!/usr/bin/env python3
"""Native inquiry-to-experiment regressions for Aurora build 650.

The tests assert routing, evidence boundaries, and boundedness.  They never
assert that a particular parent pair has a predetermined semantic answer.
"""
from __future__ import annotations

from aurora_internal.aurora_constraint_semantic_continuity import (
    derive_constraint_semantic_state,
    extract_relational_form,
)
from aurora_internal.aurora_recursive_causal_reasoning_waveform import (
    AuroraRecursiveCausalReasoningWaveform,
)
from aurora_internal.constraint_genealogy import (
    AXES,
    AbilityProfile,
    ConstraintGenealogyLogger,
    ConstraintLink,
    GenealogyConfig,
    PressureVec,
    TraceItem,
)


def _config(**overrides):
    values = dict(
        K_MIN=4,
        RELIEF_EPS=0.000001,
        RELIEF_TOTAL_EPS=0.000001,
        RELIEF_PROMOTE_MIN=0.00001,
        POS_FRACTION_MIN=0.50,
        NET_MIN=0.00000001,
        X_RISK_MAX=1.0,
        COST_TO_RELIEF_SCALE=0.0,
        RELIEF_TOLERANCE_ENABLED=False,
        THRESHOLD_PRESSURE_ENABLED=False,
        STAGNATION_BOOTSTRAP_RATIO=0.0,
        REPRESENTATION_GAP_CANDIDATES_PER_ITEM=12,
        REPRESENTATION_GAP_MAX_PER_EVENT=24,
        REPRESENTATION_COLLISION_MAX_PER_EVENT=32,
        REPRESENTATION_INQUIRY_REFRACTORY_CYCLES=0,
    )
    values.update(overrides)
    return GenealogyConfig(**values)


def _link(link_id, parents, depth, axis="X", *, lane="meaning", operator="shared_operation", relief=None):
    mean_relief = {a: 0.0 for a in AXES}
    mean_relief.update(relief or {axis: 0.05})
    return ConstraintLink(
        id=link_id,
        parents=list(parents),
        depth=depth,
        created_at_tick=depth,
        count=12,
        mean_relief=mean_relief,
        mean_cost={a: 0.0 for a in AXES},
        mean_x_risk=0.0,
        stdev_relief={a: 0.0 for a in AXES},
        dominant_relief_axis=axis,
        tags=[
            f"purpose_lane:{lane}",
            f"operator_action:{operator}",
            f"generation:{depth}",
        ],
    )


def _cross_family_fixture(tmp_path, **cfg):
    logger = ConstraintGenealogyLogger("native_inquiry", config=_config(**cfg), output_dir=str(tmp_path))
    early = _link("L:inquiry_early", ["X:REJECT", "T:DEFER"], 1, "X")
    deep1 = _link("L:inquiry_deep1", ["N:SPEND", "B:SEPARATE"], 1, "N")
    deep2 = _link("L:inquiry_deep2", [deep1.id, "A:CHOOSE"], 2, "A")
    deep3 = _link("L:inquiry_deep3", [deep2.id, "B:ROUTE"], 3, "B")
    deep4 = _link("L:inquiry_deep4", [deep3.id, "T:BATCH"], 4, "T")
    deep5 = _link("L:inquiry_deep5", [deep4.id, "N:REDUCE_STATE"], 5, "N")
    logger.links.update({x.id: x for x in (early, deep1, deep2, deep3, deep4, deep5)})
    return logger, early, deep5


def _gap_for(logger, left_id, right_id):
    candidates = logger.representation_gap_candidates([TraceItem("LINK", left_id)])
    return next(c for c in candidates if c["operand_ids"] == [left_id, right_id])


def _record_and_stage(logger, candidate, *, consumer="test_consumer"):
    logger._record_representation_inquiries([candidate])
    staged = logger.stage_representation_inquiry(
        consumer,
        {"axis_activation": {a: 0.2 for a in AXES}},
        inquiry_id=candidate["inquiry_id"],
        limit=1,
    )
    assert len(staged) == 1
    return staged[0]


def _complete(logger, stage, *, helpful=True, consumer="test_consumer"):
    before = {a: 1.0 for a in AXES}
    after = {a: (0.2 if helpful else 1.0) for a in AXES}
    return logger.complete_representation_experiment(
        stage["stage_id"],
        consumer=consumer,
        coactivated_ids=stage["operand_ids"],
        pressure_before=before,
        pressure_after=after,
        outcome={"actual_coactivation": True, "native_measurement": {"helpful": helpful}},
    )


def test_consumer_discovers_and_stages_without_creating_evidence(tmp_path):
    logger, early, deep = _cross_family_fixture(tmp_path)
    candidate = _gap_for(logger, early.id, deep.id)
    logger._record_representation_inquiries([candidate])
    pair_count = len(logger._pair_stats)
    relations = len(logger._representation_relations)

    stage = logger.stage_representation_inquiry(
        "recursive_causal_waveform",
        {"axis_activation": {a: 0.2 for a in AXES}},
        inquiry_id=candidate["inquiry_id"],
        limit=1,
    )[0]

    assert stage["operand_ids"] == [early.id, deep.id]
    assert stage["actual_coactivation_required"] is True
    assert stage["evidence_admitted"] is False
    assert len(logger._pair_stats) == pair_count
    assert len(logger._representation_relations) == relations


def test_only_actual_ordered_coactivation_can_enter_pair_stats(tmp_path):
    logger, early, deep = _cross_family_fixture(tmp_path)
    stage = _record_and_stage(logger, _gap_for(logger, early.id, deep.id))

    rejected = logger.complete_representation_experiment(
        stage["stage_id"],
        consumer="test_consumer",
        coactivated_ids=[deep.id, early.id],
        pressure_before={a: 1.0 for a in AXES},
        pressure_after={a: 0.0 for a in AXES},
        outcome={"actual_coactivation": True},
    )
    assert rejected["evidence_admitted"] is False
    assert (early.id, deep.id) not in logger._pair_stats

    completed = _complete(logger, stage)
    assert completed["evidence_admitted"] is True
    assert logger._pair_stats[(early.id, deep.id)].count == 1
    assert logger.representation_relation_for_pair(early.id, deep.id)["status"] == "candidate"


def test_cross_family_candidate_uses_native_relevance_not_equal_signature(tmp_path):
    logger, early, deep = _cross_family_fixture(tmp_path)
    candidate = _gap_for(logger, early.id, deep.id)

    assert candidate["inquiry_class"] == "complementary_gap"
    assert candidate["constraint_signatures"][0] != candidate["constraint_signatures"][1]
    assert candidate["evidence"]["shared_purpose_lane"] == "meaning"
    assert candidate["evidence"]["shared_operator_action"] == "shared_operation"
    assert "semantic_answer" not in candidate
    assert logger._pair_stats == {}


def test_cross_depth_cross_family_operands_are_eligible_together(tmp_path):
    logger, early, deep = _cross_family_fixture(tmp_path)
    stage = _record_and_stage(logger, _gap_for(logger, early.id, deep.id))

    assert stage["operands"][0]["depth"] == 1
    assert stage["operands"][1]["depth"] == 5
    assert stage["operands"][0]["constraint_basis"]["signature"] != stage["operands"][1]["constraint_basis"]["signature"]
    assert all(parent["eligible"] for parent in stage["operands"])


def test_staged_operand_surface_preserves_identity_semantics_effect_depth_and_basis(tmp_path):
    logger, early, deep = _cross_family_fixture(tmp_path)
    stage = _record_and_stage(logger, _gap_for(logger, early.id, deep.id))

    for expected_id, operand in zip([early.id, deep.id], stage["operands"]):
        assert operand["representation_id"] == expected_id
        assert operand["semantic_identity"]["operator_action"] == "shared_operation"
        assert operand["operational_effect"]
        assert operand["generation"] >= 1
        assert operand["depth"] >= 1
        assert operand["constraint_basis"]["counts"]
    expected = logger._merged_axis_counts_for_pair((early.id, deep.id))
    assert stage["constraint_basis"]["counts"] == expected


def test_same_flat_basis_different_intact_pairs_remain_separately_addressable(tmp_path):
    logger = ConstraintGenealogyLogger("distinct_pairs", config=_config(), output_dir=str(tmp_path))
    left_a = _link("L:left_a", ["X:REJECT", "T:DEFER"], 1)
    left_b = _link("L:left_b", ["X:RECLASSIFY", "T:SIM_TICK"], 1)
    right_a = _link("L:right_a", ["N:SPEND", "B:SEPARATE"], 1, "N")
    right_b = _link("L:right_b", ["N:CACHE", "B:ENCAPSULATE"], 1, "N")
    logger.links.update({x.id: x for x in (left_a, left_b, right_a, right_b)})

    for pair in ((left_a.id, right_a.id), (left_b.id, right_b.id)):
        logger.observe(
            PressureVec(X=1, T=1, N=1, B=1, A=1),
            [TraceItem("LINK", pair[0]), TraceItem("LINK", pair[1])],
            PressureVec(X=.5, T=.5, N=.5, B=.5, A=.5),
        )
    first = logger.representation_relation_for_pair(left_a.id, right_a.id)
    second = logger.representation_relation_for_pair(left_b.id, right_b.id)
    assert first["constraint_basis"]["signature"] == second["constraint_basis"]["signature"]
    assert first["relation_id"] != second["relation_id"]
    assert first["parent_ids"] != second["parent_ids"]


def test_directional_relations_keep_separate_identity_and_evidence(tmp_path):
    logger, early, deep = _cross_family_fixture(tmp_path)
    for trace in (
        [TraceItem("LINK", early.id), TraceItem("LINK", deep.id)],
        [TraceItem("LINK", deep.id), TraceItem("LINK", early.id)],
    ):
        logger.observe(
            PressureVec(X=1, T=1, N=1, B=1, A=1), trace,
            PressureVec(X=.5, T=.5, N=.5, B=.5, A=.5),
        )
    forward = logger.representation_relation_for_pair(early.id, deep.id)
    reverse = logger.representation_relation_for_pair(deep.id, early.id)
    assert forward["relation_id"] != reverse["relation_id"]
    assert forward["parent_ids"] == [early.id, deep.id]
    assert reverse["parent_ids"] == [deep.id, early.id]


def test_no_pair_meaning_is_assigned_during_staging_or_observation(tmp_path):
    logger, early, deep = _cross_family_fixture(tmp_path)
    stage = _record_and_stage(logger, _gap_for(logger, early.id, deep.id))
    result = _complete(logger, stage)
    relation = logger.representation_relation_for_pair(early.id, deep.id)

    assert result["evidence_admitted"] is True
    assert "semantic_answer" not in stage
    assert relation["semantic_sources"]["answer_key"] is False
    assert relation["semantic_sources"]["intact_relation_observations"] == 1
    assert relation["relational_evidence"]["actual_experiment_count"] == 1


def test_unhelpful_experiment_remains_unpromoted_and_does_not_harm_parents(tmp_path):
    logger, early, deep = _cross_family_fixture(tmp_path)
    stage = _record_and_stage(logger, _gap_for(logger, early.id, deep.id))
    before_parents = set(logger.links)
    result = _complete(logger, stage, helpful=False)

    assert result["status"] == "unhelpful"
    assert result["evidence_admitted"] is False
    assert (early.id, deep.id) not in logger._pair_stats
    assert set(logger.links) == before_parents
    inquiry = logger._representation_collisions[stage["inquiry_id"]]
    assert inquiry["status"] == "dormant"


def test_cross_family_search_scores_only_a_bounded_window(tmp_path):
    logger = ConstraintGenealogyLogger(
        "bounded_gap",
        config=_config(
            REPRESENTATION_RELEVANCE_BUCKET_SCAN=10,
            REPRESENTATION_RELEVANCE_MAX_BUCKETS=4,
            REPRESENTATION_GAP_CANDIDATES_PER_ITEM=3,
            REPRESENTATION_GAP_MAX_PER_EVENT=3,
        ),
        output_dir=str(tmp_path),
    )
    active = _link("L:bounded_active", ["X:REJECT", "T:DEFER"], 1)
    logger.links[active.id] = active
    for i in range(500):
        logger.links[f"L:bounded_{i}"] = _link(
            f"L:bounded_{i}",
            ["N:SPEND", "B:SEPARATE", "A:CHOOSE"][:2],
            1 + (i % 6),
            "N",
            relief={"N": 0.001 * (i + 1)},
        )
    candidates = logger.representation_gap_candidates([TraceItem("LINK", active.id)])
    diagnostics = logger.representation_experiment_status()["last_search"]
    assert len(candidates) <= 3
    assert diagnostics["bounded"] is True
    assert diagnostics["scanned"] <= 40
    assert logger._pair_stats == {}


def test_old_valid_ancestor_remains_retrievable_amid_new_descendants(tmp_path):
    logger = ConstraintGenealogyLogger(
        "ancestor_reachability",
        config=_config(REPRESENTATION_GAP_CANDIDATES_PER_ITEM=20, REPRESENTATION_GAP_MAX_PER_EVENT=20),
        output_dir=str(tmp_path),
    )
    root = _link("L:old_root", ["X:REJECT", "T:DEFER"], 1)
    logger.links[root.id] = root
    parent = root
    for i in range(1, 13):
        child = _link(f"L:new_{i}", [parent.id, "N:SPEND"], i + 1, "N")
        logger.links[child.id] = child
        parent = child
    candidates = logger.representation_gap_candidates([TraceItem("LINK", parent.id)])
    assert any(c["counterpart_representation_id"] == root.id for c in candidates)
    assert logger.representation_is_eligible(root.id) is True


def test_unresolved_inquiry_cannot_self_activate_repeatedly(tmp_path):
    logger, early, deep = _cross_family_fixture(
        tmp_path,
        REPRESENTATION_INQUIRY_REFRACTORY_CYCLES=4,
        REPRESENTATION_INQUIRY_MAX_ATTEMPTS=1,
    )
    candidate = _gap_for(logger, early.id, deep.id)
    stage = _record_and_stage(logger, candidate)
    assert logger.stage_representation_inquiry("test_consumer", {}, inquiry_id=candidate["inquiry_id"], limit=1) == []
    _complete(logger, stage, helpful=False)
    for _ in range(10):
        assert logger.stage_representation_inquiry("test_consumer", {}, inquiry_id=candidate["inquiry_id"], limit=1) == []
    assert (early.id, deep.id) not in logger._pair_stats


def test_repeated_independently_reobserved_outcomes_reach_existing_promotion_gates(tmp_path):
    logger, early, deep = _cross_family_fixture(
        tmp_path,
        K_MIN=3,
        REPRESENTATION_INQUIRY_MAX_ATTEMPTS=2,
    )
    candidate = _gap_for(logger, early.id, deep.id)
    promoted = ""
    for _ in range(12):
        logger._record_representation_inquiries([candidate])
        staged = logger.stage_representation_inquiry(
            "test_consumer", {}, inquiry_id=candidate["inquiry_id"], limit=1,
        )
        if not staged:
            continue
        result = _complete(logger, staged[0])
        promoted = result.get("promoted_link_id", "")
        if promoted:
            break
    assert promoted
    relation = logger.representation_relation_for_pair(early.id, deep.id)
    assert relation["status"] == "promoted"
    assert relation["admissibility"]["authority"] == "existing_genealogy_gates"


def test_existing_abilities_are_valid_cross_family_operands(tmp_path):
    logger = ConstraintGenealogyLogger("ability_operands", config=_config(), output_dir=str(tmp_path))
    left = AbilityProfile(
        "X:INQUIRY_ABILITY_LEFT", "X", ("X",),
        {a: 0.01 for a in AXES}, {a: 0.0 for a in AXES},
        ("shared_lived_target", "purpose_lane:meaning", "operator_action:ability_relation"),
    )
    right = AbilityProfile(
        "N:INQUIRY_ABILITY_RIGHT", "N", ("N", "B"),
        {a: 0.02 for a in AXES}, {a: 0.0 for a in AXES},
        ("shared_lived_target", "purpose_lane:meaning", "operator_action:ability_relation"),
    )
    logger.abilities[left.id] = left
    logger.abilities[right.id] = right
    candidates = logger.representation_gap_candidates([TraceItem("ABILITY", left.id)])
    candidate = next(c for c in candidates if c["counterpart_representation_id"] == right.id)
    stage = _record_and_stage(logger, candidate)
    assert [x["kind"] for x in stage["operands"]] == ["ABILITY", "ABILITY"]
    assert stage["constraint_basis"]["signature"] != "0"


def test_recursive_causal_cycle_is_the_native_consumer_and_actual_experiment(tmp_path):
    logger = ConstraintGenealogyLogger("rcrw_consumer", config=_config(), output_dir=str(tmp_path / "genealogy"))
    left = AbilityProfile(
        "X:RCRW_OPERAND_LEFT", "X", ("X",),
        {a: 0.01 for a in AXES}, {a: 0.0 for a in AXES},
        ("rcrw_unique_shared_target", "purpose_lane:meaning", "operator_action:rcrw_relation"),
    )
    right = AbilityProfile(
        "N:RCRW_OPERAND_RIGHT", "N", ("N", "B"),
        {a: 0.02 for a in AXES}, {a: 0.0 for a in AXES},
        ("rcrw_unique_shared_target", "purpose_lane:meaning", "operator_action:rcrw_relation"),
    )
    logger.abilities[left.id] = left
    logger.abilities[right.id] = right
    candidate = next(
        c for c in logger.representation_gap_candidates([TraceItem("ABILITY", left.id)])
        if c["counterpart_representation_id"] == right.id
    )
    logger._record_representation_inquiries([candidate])

    systems = {"genealogy": logger}
    bridge = AuroraRecursiveCausalReasoningWaveform(
        state_dir=str(tmp_path / "rcrw"), persist=False, genealogy=logger,
    )
    bridge.attach_systems(systems)
    state = derive_constraint_semantic_state(
        extract_relational_form("Why did that relation change?"),
        axis_activation={a: 0.2 for a in AXES},
    )
    state["completeness"] = 0.0
    bridge.prepare_semantic_state(
        state,
        raw_text="Why did that relation change?",
        systems=systems,
    )
    cycle = bridge.latest_cycle()
    stage = cycle["representation_experiment"]
    relation_waves = [w for w in cycle["wavelets"] if w["source"] == "representation_inquiry"]

    assert stage["operand_ids"] == [left.id, right.id]
    assert len(relation_waves) == 1
    assert relation_waves[0]["evidence"]["operand_states"] == stage["operands"]
    assert relation_waves[0]["evidence"]["constraint_basis"] == stage["constraint_basis"]
    assert logger._pair_stats == {}

    completed = bridge.complete_cycle(
        delivered_text="The relation changed because the earlier state no longer fit the later boundary.",
        response_source="constraint_semantic_derivation",
        confidence=0.9,
        systems=systems,
    )
    result = completed["representation_experiment_result"]
    assert result["actual_coactivation"] is True
    assert result["evidence_admitted"] is True
    assert logger._pair_stats[(left.id, right.id)].count == 1


def test_inquiry_experiment_runtime_round_trips_additively(tmp_path):
    from aurora_runtime import _restore_genealogy_state

    logger, early, deep = _cross_family_fixture(tmp_path)
    candidate = _gap_for(logger, early.id, deep.id)
    failed_stage = _record_and_stage(logger, candidate)
    _complete(logger, failed_stage, helpful=False)
    logger._record_representation_inquiries([candidate])
    active_stage = logger.stage_representation_inquiry(
        "persisted_consumer", {}, inquiry_id=candidate["inquiry_id"], limit=1,
    )[0]
    logger.flush_files()

    restored = ConstraintGenealogyLogger("restored_inquiry", config=_config(), output_dir=str(tmp_path))
    _restore_genealogy_state(restored, str(tmp_path))
    assert active_stage["stage_id"] in restored._representation_experiment_stages
    assert restored._representation_experiment_history
    assert candidate["inquiry_id"] in restored._representation_collisions
    assert restored._representation_relations == logger._representation_relations


#!/usr/bin/env python3
"""Build 650 cross-generational intact-representation regression suite.

These tests cover the additive relational genealogy without assigning a
human-authored meaning to any parent cross.  Promotion still belongs to the
existing ConstraintGenealogyLogger gates.
"""
import json

from aurora_constraint_stack import DifferenceSnapshot
from aurora_internal.aurora_constraint_manifold_patched import Constraint
from aurora_internal.constraint_genealogy import (
    AXES,
    ConstraintGenealogyLogger,
    ConstraintLink,
    GenealogyConfig,
    PressureVec,
    TraceItem,
    constraint_link_from_dict,
)


def _config(**overrides):
    base = dict(
        K_MIN=6,
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
    )
    base.update(overrides)
    return GenealogyConfig(**base)


def _link(link_id, parents, depth, axis="X", relief=None, tags=None):
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
        tags=list(tags or [
            f"purpose_lane:{'communication' if axis == 'B' else 'meaning'}",
            f"operator_action:observed_{axis.lower()}_operation",
            f"generation:{depth}",
        ]),
    )


def _cross_depth_fixture(tmp_path, **cfg_overrides):
    logger = ConstraintGenealogyLogger(
        run_id="intact_relation_test",
        config=_config(**cfg_overrides),
        output_dir=str(tmp_path),
    )
    a = _link("L:early", ["X:REJECT", "T:DEFER"], 1, axis="X")
    b1 = _link("L:late1", ["N:SPEND", "B:SEPARATE"], 1, axis="N")
    b2 = _link("L:late2", [b1.id, "T:BATCH"], 2, axis="T")
    b3 = _link("L:late3", [b2.id, "B:ROUTE"], 3, axis="B")
    b4 = _link("L:late4", [b3.id, "A:CHOOSE"], 4, axis="A")
    b5 = _link("L:late5", [b4.id, "N:REDUCE_STATE"], 5, axis="N")
    logger.links.update({link.id: link for link in (a, b1, b2, b3, b4, b5)})
    trace = [TraceItem(kind="LINK", id=a.id), TraceItem(kind="LINK", id=b5.id)]
    return logger, a, b5, trace


def _positive_tick(logger, trace, snapshot=None):
    return logger.observe(
        pressure_before=PressureVec(X=1.0, T=0.8, N=0.6, B=0.4, A=0.2),
        trace=trace,
        pressure_after=PressureVec(X=0.8, T=0.7, N=0.5, B=0.3, A=0.1),
        difference_snapshot=snapshot,
    )


def _promote(logger, trace, snapshot=None):
    for _ in range(12):
        _positive_tick(logger, trace, snapshot=snapshot)
        child = logger._links_by_parents.get((trace[0].id, trace[1].id))
        if child:
            return logger.links[child]
    raise AssertionError("existing promotion gates did not promote supported fixture")


def _difference_snapshot():
    values = {
        Constraint.X: 0.10,
        Constraint.T: -0.20,
        Constraint.N: 0.30,
        Constraint.B: 0.40,
        Constraint.A: -0.50,
    }
    refs = {constraint: 1.0 for constraint in values}
    return DifferenceSnapshot(tick=1, values=values, ref_magnitudes=refs)


def test_existing_constraint_reduction_is_unchanged_without_relational_use(tmp_path):
    logger, early, late, _trace = _cross_depth_fixture(tmp_path)
    before = logger._axis_counts_from_item(TraceItem(kind="LINK", id=late.id), memo={}, seen=set())
    logger._constraint_basis_for_item(early.id)
    logger._semantic_identity_for_item(late.id)
    after = logger._axis_counts_from_item(TraceItem(kind="LINK", id=late.id), memo={}, seen=set())
    assert before == after
    assert logger._canonical_coupling_signature(before) == logger._canonical_coupling_signature(after)


def test_legacy_link_schema_loads_with_additive_fields_absent():
    legacy = _link("L:legacy", ["X:REJECT", "B:SEPARATE"], 1).to_dict()
    legacy.pop("constraint_basis", None)
    legacy.pop("representation_relation", None)
    legacy.pop("semantic_identity", None)
    loaded = constraint_link_from_dict(legacy)
    assert loaded.id == "L:legacy"
    assert loaded.parents == ["X:REJECT", "B:SEPARATE"]
    assert loaded.constraint_basis is None
    assert loaded.representation_relation is None
    assert loaded.semantic_identity is None


def test_whole_representations_and_primitive_basis_survive_promotion(tmp_path):
    logger, early, late, trace = _cross_depth_fixture(tmp_path)
    child = _promote(logger, trace, snapshot=_difference_snapshot())
    relation = child.representation_relation

    assert relation["mode"] == "intact_operands"
    assert relation["parent_ids"] == [early.id, late.id]
    assert [parent["representation_id"] for parent in relation["parents"]] == [early.id, late.id]
    assert all(parent["participated_as"] == "intact_representation" for parent in relation["parents"])
    assert child.constraint_basis["signature"] == logger._canonical_coupling_signature(
        logger._merged_axis_counts_for_pair((early.id, late.id))
    )
    assert relation["evidence"]["difference"]["observation_count"] > 0
    assert relation["evidence"]["consequence_history"]
    assert relation["semantic_interpretation"]["translation"]
    assert relation["evidence"]["admissibility"]["authority"] == "existing_genealogy_gates"
    public_record = logger.representation_record(child.id)
    assert public_record["representation_id"] == child.id
    assert public_record["constraint_basis"] == child.constraint_basis
    assert public_record["representation_relation"]["parent_ids"] == [early.id, late.id]


def test_composition_and_intact_relation_coexist_as_distinct_structures(tmp_path):
    logger, early, late, trace = _cross_depth_fixture(tmp_path)
    child = _promote(logger, trace)
    signature = child.constraint_basis["signature"]

    assert signature in logger._coupling_roots
    assert logger._coupling_roots[signature]["signature"] == signature
    assert "parent_ids" not in logger._coupling_roots[signature]
    assert child.representation_relation["parent_ids"] == [early.id, late.id]
    assert child.representation_relation["relation_id"].startswith("RR:")


def test_cross_depth_pair_is_not_rejected_for_generation_distance(tmp_path):
    logger, early, late, trace = _cross_depth_fixture(tmp_path)
    child = _promote(logger, trace)
    parents = child.representation_relation["parents"]
    assert abs(parents[0]["depth"] - parents[1]["depth"]) >= 4
    assert child.representation_relation["parent_ids"] == [early.id, late.id]
    assert child.id in logger.links


def test_ancestor_can_recombine_with_distant_descendant(tmp_path):
    logger, _early, late, _trace = _cross_depth_fixture(tmp_path)
    ancestor = logger.links["L:late1"]
    assert late.id in logger.representation_descendants(ancestor.id)
    trace = [
        TraceItem(kind="LINK", id=ancestor.id),
        TraceItem(kind="LINK", id=late.id),
    ]
    child = _promote(logger, trace)
    assert ancestor.id in late.parents or ancestor.id in logger.links["L:late2"].parents
    assert child.representation_relation["parent_ids"] == [ancestor.id, late.id]
    assert child.representation_relation["parents"][0]["depth"] == 1
    assert child.representation_relation["parents"][1]["depth"] == 5


def test_ancestor_survives_after_descendant_exists(tmp_path):
    logger, early, _late, trace = _cross_depth_fixture(tmp_path)
    child = _promote(logger, trace)
    assert early.id in logger.links
    assert logger.representation_is_eligible(early.id) is True
    assert child.id in logger.representation_descendants(early.id)


def test_collision_detection_exposes_difference_without_answer_key(tmp_path):
    logger = ConstraintGenealogyLogger("collision", config=_config(), output_dir=str(tmp_path))
    active = [
        TraceItem(kind="ABILITY", id="X:REJECT"),
        TraceItem(kind="ABILITY", id="X:RECLASSIFY"),
    ]
    candidates = logger.representation_collision_candidates(active)
    assert candidates
    candidate = next(
        candidate for candidate in candidates
        if set(candidate["representation_ids"]) == {"X:REJECT", "X:RECLASSIFY"}
    )
    assert candidate["status"] == "unresolved"
    assert candidate["constraint_signature"] == logger._collision_signature_for_item("X:REJECT")
    assert set(candidate["representation_ids"]) == {"X:REJECT", "X:RECLASSIFY"}
    assert candidate["evidence"]
    assert "semantic_answer" not in candidate
    assert logger._representation_relations == {}
    logger._record_representation_collisions(candidates)
    pending = logger.pending_representation_inquiries(limit=12)
    assert candidate["collision_id"] in {item["collision_id"] for item in pending}
    assert logger._pair_stats == {}
    assert logger._representation_relations == {}


def test_dormant_persisted_ability_remains_reachable_without_prior_pair_stats(tmp_path):
    logger = ConstraintGenealogyLogger("dormant_ability", config=_config(), output_dir=str(tmp_path))
    assert logger._pair_stats == {}
    candidates = logger.representation_collision_candidates([
        TraceItem(kind="ABILITY", id="X:REJECT"),
    ])
    assert any(
        set(candidate["representation_ids"]) == {"X:REJECT", "X:RECLASSIFY"}
        for candidate in candidates
    )
    assert logger._pair_stats == {}
    assert logger._representation_relations == {}


def test_one_observation_is_not_promotion_but_repeated_outcomes_can_promote(tmp_path):
    logger = ConstraintGenealogyLogger("evidence", config=_config(), output_dir=str(tmp_path))
    trace = [
        TraceItem(kind="ABILITY", id="X:REJECT"),
        TraceItem(kind="ABILITY", id="X:RECLASSIFY"),
    ]
    _positive_tick(logger, trace)
    relation = logger.representation_relation_for_pair(trace[0].id, trace[1].id)
    assert relation["status"] == "candidate"
    assert (trace[0].id, trace[1].id) not in logger._links_by_parents

    child = _promote(logger, trace)
    relation = logger.representation_relation_for_pair(trace[0].id, trace[1].id)
    assert relation["status"] == "promoted"
    assert relation["promoted_link_id"] == child.id
    assert relation["admissibility"]["authority"] == "existing_genealogy_gates"


def test_collision_search_is_bounded_and_never_crosses_candidates(tmp_path):
    logger = ConstraintGenealogyLogger(
        "bounded",
        config=_config(
            REPRESENTATION_COLLISION_CANDIDATES_PER_ITEM=2,
            REPRESENTATION_COLLISION_MAX_PER_EVENT=2,
        ),
        output_dir=str(tmp_path),
    )
    links = []
    for i in range(10):
        link = _link(
            f"L:same{i}",
            ["X:REJECT", "T:DEFER"],
            1,
            axis="X" if i % 2 == 0 else "T",
            relief={"X": 0.01 * (i + 1), "T": 0.02 * i},
        )
        links.append(link)
        logger.links[link.id] = link

    candidates = logger.representation_collision_candidates(
        [TraceItem(kind="LINK", id=links[0].id)]
    )
    assert len(candidates) <= 2
    assert all(links[0].id in candidate["representation_ids"] for candidate in candidates)
    assert logger._pair_stats == {}
    assert logger._representation_relations == {}


def test_current_semantic_identity_wins_over_inherited_fossils():
    historical = _link(
        "L:fossil",
        ["X:REJECT", "B:SEPARATE"],
        2,
        tags=[
            "purpose_lane:meaning",
            "operator_action:ancestor_operation",
            "purpose_lane:communication",
            "operator_action:local_operation",
        ],
    )
    assert historical.current_semantic_value("purpose_lane") == "communication"
    assert historical.current_semantic_value("operator_action") == "local_operation"

    explicit = _link(
        "L:explicit",
        [historical.id, "A:CHOOSE"],
        3,
        tags=list(historical.tags),
    )
    explicit.semantic_identity = {
        "purpose_lane": "intelligence",
        "operator_action": "explicit_local_operation",
    }
    assert explicit.current_semantic_value("purpose_lane") == "intelligence"
    assert explicit.current_semantic_value("operator_action") == "explicit_local_operation"


def test_runtime_consumer_reads_local_semantics_not_first_fossil():
    from aurora_runtime import ChainSimBridge

    link = _link(
        "L:runtime_fossil",
        ["X:REJECT", "B:SEPARATE"],
        2,
        tags=["purpose_lane:meaning", "purpose_lane:communication"],
    )
    bridge = object.__new__(ChainSimBridge)
    assert bridge._link_tag_value(link, "purpose_lane:", cast=str) == "communication"


def test_link_and_relation_round_trip_persistence(tmp_path):
    logger, early, late, trace = _cross_depth_fixture(tmp_path)
    child = _promote(logger, trace, snapshot=_difference_snapshot())
    logger.flush_files()

    with open(tmp_path / "links.json", "r", encoding="utf-8") as fh:
        raw_links = json.load(fh)
    with open(tmp_path / "couplings.json", "r", encoding="utf-8") as fh:
        raw_couplings = json.load(fh)

    loaded_child = constraint_link_from_dict(raw_links[child.id])
    assert loaded_child.constraint_basis == child.constraint_basis
    assert loaded_child.representation_relation["parent_ids"] == [early.id, late.id]
    assert loaded_child.representation_relation["evidence"]["difference"]["observation_count"] > 0
    relation_id = child.representation_relation["relation_id"]
    assert raw_couplings["representation_relations"][relation_id]["status"] == "promoted"


def test_full_runtime_restore_keeps_both_genealogies(tmp_path):
    from aurora_runtime import _restore_genealogy_state

    logger, early, late, trace = _cross_depth_fixture(tmp_path)
    child = _promote(logger, trace, snapshot=_difference_snapshot())
    logger.flush_files()

    restored = ConstraintGenealogyLogger("restored", config=_config(), output_dir=str(tmp_path))
    result = _restore_genealogy_state(restored, str(tmp_path))
    loaded_child = restored.links[child.id]
    relation_id = loaded_child.representation_relation["relation_id"]

    assert result["links"] >= 1
    assert loaded_child.constraint_basis == child.constraint_basis
    assert loaded_child.representation_relation["parent_ids"] == [early.id, late.id]
    assert restored._representation_relations[relation_id]["status"] == "promoted"


def test_existing_semantic_translation_still_updates(tmp_path):
    logger = ConstraintGenealogyLogger("semantic", config=_config(), output_dir=str(tmp_path))
    trace = [
        TraceItem(kind="ABILITY", id="X:REJECT"),
        TraceItem(kind="ABILITY", id="B:SEPARATE"),
    ]
    _positive_tick(logger, trace)
    assert logger._coupling_roots
    flattened = next(iter(logger._coupling_roots.values()))
    relation = logger.representation_relation_for_pair(trace[0].id, trace[1].id)
    assert flattened["semantic_translation"]
    assert relation["semantic_translation"]

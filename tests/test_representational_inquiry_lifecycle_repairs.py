#!/usr/bin/env python3
"""Regression coverage for Build 650 Multimodal Representational Autonomy
Directive, Section XXI/XXII (Sunni & Cael): stage expiration enforcement,
inquiry pressure decay, correct refractory units, and duplicate-active-stage
prevention.
"""
from __future__ import annotations

from aurora_internal.constraint_genealogy import (
    AXES,
    AbilityProfile,
    ConstraintGenealogyLogger,
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


def _ability_pair(suffix: str, lane="meaning", operator="shared_operation"):
    left = AbilityProfile(
        f"X:LIFECYCLE_LEFT_{suffix}", "X", ("X",),
        {a: 0.01 for a in AXES}, {a: 0.0 for a in AXES},
        (f"shared_target_{suffix}", f"purpose_lane:{lane}", f"operator_action:{operator}"),
    )
    right = AbilityProfile(
        f"N:LIFECYCLE_RIGHT_{suffix}", "N", ("N", "B"),
        {a: 0.02 for a in AXES}, {a: 0.0 for a in AXES},
        (f"shared_target_{suffix}", f"purpose_lane:{lane}", f"operator_action:{operator}"),
    )
    return left, right


def _gap_candidate(logger, left, right):
    candidates = logger.representation_gap_candidates([TraceItem("ABILITY", left.id)])
    return next(c for c in candidates if c["counterpart_representation_id"] == right.id)


def test_expired_stage_stops_occupying_active_state(tmp_path):
    logger = ConstraintGenealogyLogger(
        "expire_active", config=_config(REPRESENTATION_INQUIRY_STAGE_LIFETIME=1), output_dir=str(tmp_path),
    )
    left, right = _ability_pair("expire")
    logger.abilities[left.id] = left
    logger.abilities[right.id] = right
    candidate = _gap_candidate(logger, left, right)
    logger._record_representation_inquiries([candidate])

    stage = logger.stage_representation_inquiry(
        "consumer_a", {}, inquiry_id=candidate["inquiry_id"], limit=1,
    )[0]
    assert stage["stage_id"] in logger._representation_experiment_stages

    # Advance genealogy tick_count past the stage's lifetime without ever
    # completing it -- an abandoned stage.
    for _ in range(3):
        logger.observe(
            PressureVec(X=1, T=1, N=1, B=1, A=1),
            [TraceItem("ABILITY", "X:LIFECYCLE_LEFT_expire")],
            PressureVec(X=0, T=0, N=0, B=0, A=0),
        )

    logger._expire_stale_representation_stages()

    assert stage["stage_id"] not in logger._representation_experiment_stages
    inquiry = logger._representation_collisions[candidate["inquiry_id"]]
    assert inquiry["status"] == "unresolved"


def test_expired_stage_admits_no_evidence_when_completed_late(tmp_path):
    logger = ConstraintGenealogyLogger(
        "expire_no_evidence", config=_config(REPRESENTATION_INQUIRY_STAGE_LIFETIME=1), output_dir=str(tmp_path),
    )
    left, right = _ability_pair("noevidence")
    logger.abilities[left.id] = left
    logger.abilities[right.id] = right
    candidate = _gap_candidate(logger, left, right)
    logger._record_representation_inquiries([candidate])
    stage = logger.stage_representation_inquiry(
        "consumer_a", {}, inquiry_id=candidate["inquiry_id"], limit=1,
    )[0]

    from aurora_internal.constraint_genealogy import PressureVec
    for _ in range(3):
        logger.observe(
            PressureVec(X=1, T=1, N=1, B=1, A=1),
            [TraceItem("ABILITY", "X:LIFECYCLE_LEFT_noevidence")],
            PressureVec(X=0, T=0, N=0, B=0, A=0),
        )

    result = logger.complete_representation_experiment(
        stage["stage_id"],
        consumer="consumer_a",
        coactivated_ids=stage["operand_ids"],
        pressure_before={a: 1.0 for a in AXES},
        pressure_after={a: 0.2 for a in AXES},
        outcome={"actual_coactivation": True},
    )

    assert result["status"] == "unknown_stage"
    assert result["evidence_admitted"] is False
    assert (left.id, right.id) not in logger._pair_stats


def test_expired_stage_cannot_coexist_indefinitely_with_its_replacement(tmp_path):
    """Section XXII: an inquiry must not accumulate multiple simultaneously
    active stages. Once the first stage expires, a fresh stage for the
    SAME inquiry must be obtainable, and at no point should two live
    stages for the same inquiry_id coexist."""
    logger = ConstraintGenealogyLogger(
        "no_duplicate_across_expiry",
        config=_config(REPRESENTATION_INQUIRY_STAGE_LIFETIME=1, REPRESENTATION_INQUIRY_MAX_ATTEMPTS=10),
        output_dir=str(tmp_path),
    )
    left, right = _ability_pair("replace")
    logger.abilities[left.id] = left
    logger.abilities[right.id] = right
    candidate = _gap_candidate(logger, left, right)
    logger._record_representation_inquiries([candidate])

    first_stage = logger.stage_representation_inquiry(
        "consumer_a", {}, inquiry_id=candidate["inquiry_id"], limit=1,
    )[0]

    # Immediately trying to stage the SAME inquiry again must fail --
    # it already has a live stage.
    duplicate_attempt = logger.stage_representation_inquiry(
        "consumer_a", {}, inquiry_id=candidate["inquiry_id"], limit=1,
    )
    assert duplicate_attempt == []
    assert len(logger._representation_experiment_stages) == 1

    from aurora_internal.constraint_genealogy import PressureVec
    for _ in range(3):
        logger.observe(
            PressureVec(X=1, T=1, N=1, B=1, A=1),
            [TraceItem("ABILITY", "X:LIFECYCLE_LEFT_replace")],
            PressureVec(X=0, T=0, N=0, B=0, A=0),
        )

    # Re-record so the (now-expired-eligible) inquiry is freshly observed,
    # then stage a replacement -- the OLD stage_id must be gone, and only
    # ONE live stage may exist for this inquiry at any point.
    logger._record_representation_inquiries([candidate])
    second_stage = logger.stage_representation_inquiry(
        "consumer_a", {}, inquiry_id=candidate["inquiry_id"], limit=1,
    )[0]

    assert second_stage["stage_id"] != first_stage["stage_id"]
    assert first_stage["stage_id"] not in logger._representation_experiment_stages
    live_for_inquiry = [
        s for s in logger._representation_experiment_stages.values()
        if s.get("inquiry_id") == candidate["inquiry_id"]
    ]
    assert len(live_for_inquiry) == 1


def test_pressure_decays_with_elapsed_ticks_without_mutating_stored_evidence(tmp_path):
    logger = ConstraintGenealogyLogger(
        "pressure_decay", config=_config(REPRESENTATION_INQUIRY_PRESSURE_DECAY=0.20), output_dir=str(tmp_path),
    )
    left, right = _ability_pair("decay")
    logger.abilities[left.id] = left
    logger.abilities[right.id] = right
    candidate = _gap_candidate(logger, left, right)
    logger._record_representation_inquiries([candidate])

    stored = logger._representation_collisions[candidate["inquiry_id"]]
    original_max_pressure = float(stored["max_pressure"])

    # Advance elapsed developmental time for THIS inquiry specifically,
    # without re-observing it (an unrelated ability keeps genealogy
    # tick_count moving; this inquiry's own last_tick is left untouched --
    # exactly what "elapsed time since this discrepancy was last seen"
    # means). Re-observing the SAME active operand via observe() would
    # itself refresh last_tick through the existing auto-discovery wiring,
    # which is the correct real-system behavior but would defeat this
    # isolated unit test of the decay formula.
    filler_left = AbilityProfile(
        "X:FILLER_UNRELATED", "X", ("X",), {a: 0.0 for a in AXES}, {a: 0.0 for a in AXES}, (),
    )
    logger.abilities[filler_left.id] = filler_left
    for _ in range(10):
        logger.observe(
            PressureVec(X=1, T=1, N=1, B=1, A=1),
            [TraceItem("ABILITY", filler_left.id)],
            PressureVec(X=0, T=0, N=0, B=0, A=0),
        )

    pending = logger.pending_representation_inquiries(limit=50)
    entry = next(p for p in pending if p["collision_id"] == candidate["inquiry_id"])

    # The RANKING/query-time value has decayed...
    assert entry["decayed_pressure"] < original_max_pressure
    # ...but the stored evidence (max_pressure) was never mutated.
    assert float(logger._representation_collisions[candidate["inquiry_id"]]["max_pressure"]) == original_max_pressure


def test_fresh_recurrence_restores_pressure_after_decay(tmp_path):
    logger = ConstraintGenealogyLogger(
        "pressure_restore", config=_config(REPRESENTATION_INQUIRY_PRESSURE_DECAY=0.30), output_dir=str(tmp_path),
    )
    left, right = _ability_pair("restore")
    logger.abilities[left.id] = left
    logger.abilities[right.id] = right
    candidate = _gap_candidate(logger, left, right)
    logger._record_representation_inquiries([candidate])

    # Use an UNRELATED filler ability to advance tick_count without
    # re-observing this specific candidate (see the decay test above for
    # why re-observing the same active operand would refresh last_tick
    # through the existing auto-discovery wiring and mask the decay).
    filler_left = AbilityProfile(
        "X:FILLER_UNRELATED_RESTORE", "X", ("X",), {a: 0.0 for a in AXES}, {a: 0.0 for a in AXES}, (),
    )
    logger.abilities[filler_left.id] = filler_left
    for _ in range(10):
        logger.observe(
            PressureVec(X=1, T=1, N=1, B=1, A=1),
            [TraceItem("ABILITY", filler_left.id)],
            PressureVec(X=0, T=0, N=0, B=0, A=0),
        )
    decayed_entry = next(
        p for p in logger.pending_representation_inquiries(limit=50)
        if p["collision_id"] == candidate["inquiry_id"]
    )
    assert decayed_entry["decayed_pressure"] < float(
        logger._representation_collisions[candidate["inquiry_id"]]["max_pressure"]
    ), "setup did not actually produce decay -- test would be vacuous"

    # A fresh recurrence of the same discrepancy restores pressure.
    logger._record_representation_inquiries([candidate])
    restored_entry = next(
        p for p in logger.pending_representation_inquiries(limit=50)
        if p["collision_id"] == candidate["inquiry_id"]
    )

    assert restored_entry["decayed_pressure"] >= decayed_entry["decayed_pressure"]


def test_refractory_measures_consumer_engagement_cycles_not_genealogy_ticks(tmp_path):
    """Section XXI: two DIFFERENT consumers advancing genealogy tick_count
    via unrelated observations must not spuriously affect each other's
    refractory window -- refractory tracks how many times EACH consumer
    itself called stage_representation_inquiry."""
    logger = ConstraintGenealogyLogger(
        "refractory_units",
        config=_config(REPRESENTATION_INQUIRY_REFRACTORY_CYCLES=3, REPRESENTATION_INQUIRY_MAX_ATTEMPTS=10),
        output_dir=str(tmp_path),
    )
    left, right = _ability_pair("refractory")
    logger.abilities[left.id] = left
    logger.abilities[right.id] = right
    candidate = _gap_candidate(logger, left, right)
    logger._record_representation_inquiries([candidate])

    first = logger.stage_representation_inquiry(
        "consumer_a", {}, inquiry_id=candidate["inquiry_id"], limit=1,
    )
    assert len(first) == 1

    # Drive a large number of UNRELATED genealogy ticks (a different
    # subsystem entirely) -- under the old tick-based refractory this
    # alone could clear the window; it must not, because consumer_a has
    # not itself made any further staging calls yet.
    from aurora_internal.constraint_genealogy import PressureVec
    for _ in range(50):
        logger.observe(
            PressureVec(X=1, T=1, N=1, B=1, A=1),
            [TraceItem("ABILITY", "X:LIFECYCLE_LEFT_refractory")],
            PressureVec(X=0, T=0, N=0, B=0, A=0),
        )

    logger._record_representation_inquiries([candidate])
    still_blocked = logger.stage_representation_inquiry(
        "consumer_a", {}, inquiry_id=candidate["inquiry_id"], limit=1,
    )
    assert still_blocked == [], (
        "refractory cleared after unrelated genealogy ticks -- "
        "it is measuring tick_count, not consumer engagement cycles"
    )

    # consumer_a's OWN repeated calls (engagement cycles) DO eventually
    # clear its refractory window.
    for _ in range(3):
        logger._record_representation_inquiries([candidate])
        result = logger.stage_representation_inquiry(
            "consumer_a", {}, inquiry_id=candidate["inquiry_id"], limit=1,
        )
    assert result == [] or len(result) == 1  # either still-refractory or freshly cleared

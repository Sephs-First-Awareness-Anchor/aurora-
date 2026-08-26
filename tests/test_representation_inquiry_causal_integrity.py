from __future__ import annotations

import json

from aurora_internal.aurora_constraint_semantic_continuity import (
    derive_constraint_semantic_state,
    extract_relational_form,
)
from aurora_internal.aurora_recursive_causal_reasoning_waveform import (
    AuroraRecursiveCausalReasoningWaveform,
    CausalWavelet,
)
from aurora_internal.constraint_genealogy import (
    AXES,
    AbilityProfile,
    ConstraintGenealogyLogger,
    GenealogyConfig,
    TraceItem,
)
from aurora_runtime import _restore_genealogy_state


def _cfg(**overrides):
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
        REPRESENTATION_INQUIRY_REFRACTORY_CYCLES=4,
        REPRESENTATION_INQUIRY_MAX_ATTEMPTS=20,
    )
    values.update(overrides)
    return GenealogyConfig(**values)


def _fixture(tmp_path):
    logger = ConstraintGenealogyLogger("causal_integrity", config=_cfg(), output_dir=str(tmp_path / "genealogy"))
    left = AbilityProfile(
        "X:CAUSAL_LEFT", "X", ("X",),
        {"X": 0.12, "T": 0.0, "N": 0.0, "B": 0.0, "A": 0.0},
        {a: 0.0 for a in AXES},
        ("shared_target", "purpose_lane:meaning", "operator_action:relation_probe"),
    )
    right = AbilityProfile(
        "N:CAUSAL_RIGHT", "N", ("N", "B"),
        {"X": 0.0, "T": 0.0, "N": 0.08, "B": 0.04, "A": 0.0},
        {a: 0.0 for a in AXES},
        ("shared_target", "purpose_lane:meaning", "operator_action:relation_probe"),
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
        axis_activation={"X": 0.42, "T": 0.08, "N": 0.22, "B": 0.18, "A": 0.10},
    )
    bridge.prepare_semantic_state(state, raw_text="Why did that relation change?", systems=systems)
    return logger, bridge, candidate


def test_axis_profile_changes_interference_not_just_metadata(tmp_path):
    bridge = AuroraRecursiveCausalReasoningWaveform(state_dir=str(tmp_path), persist=False)
    before = {a: 0.2 for a in AXES}
    x_wave = CausalWavelet(
        wavelet_id="x", primitive="recursive_backprojection", roots=list(AXES),
        amplitude=0.5, phase=0.0, polarity=1, target="representation_relation",
        source="representation_inquiry", axis_profile={"X": 1.0},
    )
    a_wave = CausalWavelet(
        wavelet_id="a", primitive="recursive_backprojection", roots=list(AXES),
        amplitude=0.5, phase=0.0, polarity=1, target="representation_relation",
        source="representation_inquiry", axis_profile={"A": 1.0},
    )
    x_result = bridge._interfere(before, [x_wave])
    a_result = bridge._interfere(before, [a_wave])
    assert x_result["axis_after"] != a_result["axis_after"]
    assert x_result["contributions"][0]["axis_effects"]["X"] == 0.5
    assert a_result["contributions"][0]["axis_effects"]["A"] == 0.5


def test_missing_lived_measurement_is_inconclusive_not_failure(tmp_path):
    logger, bridge, candidate = _fixture(tmp_path)
    stage = bridge.latest_cycle()["representation_experiment"]
    completed = bridge.complete_cycle(
        delivered_text="A coherent response.", response_source="test", confidence=0.95, systems={"genealogy": logger},
    )
    result = completed["representation_experiment_result"]
    assert result["status"] == "inconclusive_causal_measurement"
    assert result["evidence_admitted"] is False
    assert (stage["operand_ids"][0], stage["operand_ids"][1]) not in logger._pair_stats
    stored = logger._representation_collisions[candidate["inquiry_id"]]
    assert stored["status"] == "unresolved"


def test_measured_relief_is_filtered_through_controlled_marginal_effect(tmp_path):
    logger, bridge, _candidate = _fixture(tmp_path)
    cycle = bridge.latest_cycle()
    control = cycle["representation_experiment_control"]
    assert control["marginal_l1"] > 0.0
    stage = cycle["representation_experiment"]

    completed = bridge.complete_cycle(
        delivered_text="A coherent response.", response_source="test", confidence=0.95,
        systems={"genealogy": logger},
        pressure_before={"operator_gradients": {"X": 0.8, "T": 0.4, "N": 0.7, "B": 0.6, "A": 0.3}},
        pressure_after={"operator_gradients": {"X": 0.2, "T": 0.35, "N": 0.3, "B": 0.25, "A": 0.28}},
    )
    result = completed["representation_experiment_result"]
    assert result["evidence_admitted"] is True
    pair = (stage["operand_ids"][0], stage["operand_ids"][1])
    assert logger._pair_stats[pair].count == 1
    history = logger.representation_experiment_status()["recent_experiments"][-1]
    outcome = history["outcome"]
    assert outcome["causal_evidence_valid"] is True
    assert outcome["causal_evidence_mode"] == "controlled_rcrw_marginal_x_lived_operator_pressure"
    assert 0.0 < outcome["causal_confidence"] <= 1.0
    assert sum(outcome["attributable_relief"].values()) <= sum(outcome["observed_positive_relief"].values())


def test_engagement_clock_round_trips_with_last_stage_clock(tmp_path):
    logger = ConstraintGenealogyLogger("clock", config=_cfg(), output_dir=str(tmp_path))
    logger._representation_inquiry_consumer_cycle["recursive_causal_waveform"] = 248
    logger._representation_inquiry_consumer_cycle_engagements["recursive_causal_waveform"] = 250
    logger.flush_files()

    restored = ConstraintGenealogyLogger("clock_restored", config=_cfg(), output_dir=str(tmp_path))
    _restore_genealogy_state(restored, str(tmp_path))
    assert restored._representation_inquiry_consumer_cycle["recursive_causal_waveform"] == 248
    assert restored._representation_inquiry_consumer_cycle_engagements["recursive_causal_waveform"] == 250


def test_legacy_state_seeds_missing_engagement_clock_from_last_stage(tmp_path):
    logger = ConstraintGenealogyLogger("legacy_clock", config=_cfg(), output_dir=str(tmp_path))
    logger._representation_inquiry_consumer_cycle["recursive_causal_waveform"] = 248
    logger._representation_inquiry_consumer_cycle_engagements["recursive_causal_waveform"] = 250
    logger.flush_files()

    path = tmp_path / logger.cfg.COUPLINGS_FILE
    payload = json.loads(path.read_text())
    payload["representation_inquiry_runtime"].pop("consumer_engagement_cycles", None)
    path.write_text(json.dumps(payload))

    restored = ConstraintGenealogyLogger("legacy_clock_restored", config=_cfg(), output_dir=str(tmp_path))
    _restore_genealogy_state(restored, str(tmp_path))
    assert restored._representation_inquiry_consumer_cycle_engagements["recursive_causal_waveform"] == 248

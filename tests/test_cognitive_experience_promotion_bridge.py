# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Build 598: Recursive Causal Experience Chamber -- Stage 6 of 6.
Developmental Promotion Bridge, Governors & Shadow Persistence.

Covers: a fully-scored episode that clears every threshold reaches
submit_operational_experience() with correctly-shaped before/after
evidence; an episode that fails Stage 5's fidelity check does NOT reach
submission regardless of Stage 3/4 scores; each governor trips correctly
on a constructed scenario designed to trigger it, and logs to the
fail-dimension/study-topic path instead of silently dropping.
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import pytest

from aurora_internal.aurora_cognitive_experience_chamber import (  # noqa: E402
    ActionInvocation,
    CapturedInterpretation,
    ContradictionTracker,
    DevelopmentalGovernors,
    DevelopmentalPromotionBridge,
    Entity,
    EpisodeTrace,
    GovernorResult,
    WorldState,
    compute_transfer_comparison,
    route_tripped_governors_to_fail_pressure,
)


def _fully_scored_step(trace: EpisodeTrace) -> None:
    interp = CapturedInterpretation(
        raw_expression="Vessel 0's energy will increase.",
        predicted_consequence={"entity_id": "vessel_0", "property": "energy", "direction": "increase"},
        confidence=0.9,
    )
    trace.record_interpretation(0, "obs", ActionInvocation("add_energy", ("vessel_0",)), "act", interp)
    consequence = WorldState(
        tick=1,
        entities={"vessel_0": Entity("vessel_0", "vessel", {"energy": 2})},
        relationships=[],
        agents=("agent_a",),
    )
    trace.record_consequence(consequence)  # causal_scores are set directly below
    trace.steps[0].causal_scores = {
        "causal_state_accuracy": 1.0,
        "causal_prediction_accuracy": 1.0,
        "causal_discrimination": 1.0,
        "evidence_discipline": 1.0,
        "revision_quality": 1.0,
        "counterfactual_consistency": 1.0,
        "confidence_calibration": 0.9,
    }
    trace.steps[0].expression_fidelity = {"hesitation_fidelity": 1.0, "intervention_fidelity": None, "causal_claim_preservation": 1.0}


class _FakeDreamTrainer:
    def __init__(self):
        self.recorded = []

    def _record_fail_dimension(self, dim, severity, example=None):
        self.recorded.append((dim, severity, example))


class _FakeAutonomy:
    def __init__(self):
        self.topics = []

    def add_study_topic(self, topic):
        self.topics.append(topic)


class _FakeSubmitter:
    def __init__(self):
        self.calls = []

    def __call__(self, evidence):
        self.calls.append(evidence)
        return {"accepted": True, "task_id": evidence.get("task_id")}


# ---------------------------------------------------------------------------
# A fully-scored episode that clears every threshold reaches
# submit_operational_experience() with correctly-shaped before/after evidence.
# ---------------------------------------------------------------------------

def test_fully_scored_episode_reaches_submission_with_shaped_evidence():
    trace = EpisodeTrace(episode_id="promo_ep", world_seed=1, rule_family="direct_trigger", agent_id="agent_a")
    _fully_scored_step(trace)

    comparison = compute_transfer_comparison(
        {"causal_prediction_accuracy": 1.0}, {"causal_prediction_accuracy": 0.9},
    )
    submitter = _FakeSubmitter()
    systems = {"submit_operational_experience": submitter}
    bridge = DevelopmentalPromotionBridge()

    decision = bridge.evaluate_and_submit(
        systems, trace.steps[0], comparison, governor_results=[], episode_id="promo_ep",
    )

    assert decision.promoted is True
    assert decision.reason == "submitted"
    assert len(submitter.calls) == 1
    evidence = submitter.calls[0]
    assert "input_value" in evidence and "expected_output" in evidence
    assert evidence["input_value"]["observation"] == "obs"
    assert evidence["expected_output"]["dimension_scores"]["causal_state_accuracy"] == 1.0
    assert evidence["task_id"] == "RCEC:promo_ep"
    assert decision.submission_result["accepted"] is True


def test_missing_submission_seam_does_not_crash():
    trace = EpisodeTrace(episode_id="e", world_seed=1, rule_family="direct_trigger", agent_id="agent_a")
    _fully_scored_step(trace)
    comparison = compute_transfer_comparison({"causal_prediction_accuracy": 1.0}, {"causal_prediction_accuracy": 1.0})
    bridge = DevelopmentalPromotionBridge()
    decision = bridge.evaluate_and_submit({}, trace.steps[0], comparison, governor_results=[], episode_id="e")
    assert decision.promoted is False
    assert decision.reason == "no_submission_seam_available"


# ---------------------------------------------------------------------------
# An episode that fails Stage 5's fidelity check does NOT reach submission
# regardless of Stage 3/4 scores.
# ---------------------------------------------------------------------------

def test_fidelity_governor_blocks_submission_regardless_of_stage3_4_scores():
    trace = EpisodeTrace(episode_id="e", world_seed=1, rule_family="direct_trigger", agent_id="agent_a")
    _fully_scored_step(trace)
    # Stage 3/4 all perfect, but Stage 5 fidelity is bad.
    trace.steps[0].expression_fidelity = {"hesitation_fidelity": 0.0, "causal_claim_preservation": 0.0}

    comparison = compute_transfer_comparison({"causal_prediction_accuracy": 1.0}, {"causal_prediction_accuracy": 1.0})
    submitter = _FakeSubmitter()
    systems = {"submit_operational_experience": submitter}
    bridge = DevelopmentalPromotionBridge()

    fidelity_governor = DevelopmentalGovernors.meaning_expression_divergence(trace.steps[0].expression_fidelity)
    assert fidelity_governor.tripped is True

    trainer = _FakeDreamTrainer()
    autonomy = _FakeAutonomy()
    decision = bridge.evaluate_and_submit(
        systems, trace.steps[0], comparison, governor_results=[fidelity_governor],
        dream_trainer=trainer, autonomy=autonomy, episode_id="e",
    )

    assert decision.promoted is False
    assert decision.reason == "governor_tripped"
    assert "meaning_expression_divergence" in decision.tripped
    assert submitter.calls == []  # never reached submission
    assert any(dim == "meaning_expression_divergence" for dim, _sev, _ex in trainer.recorded)
    assert autonomy.topics  # routed to curiosity, not silently dropped


def test_below_threshold_dimension_blocks_submission():
    trace = EpisodeTrace(episode_id="e", world_seed=1, rule_family="direct_trigger", agent_id="agent_a")
    _fully_scored_step(trace)
    trace.steps[0].causal_scores["causal_state_accuracy"] = 0.4  # below 1.0 threshold

    comparison = compute_transfer_comparison({"causal_prediction_accuracy": 1.0}, {"causal_prediction_accuracy": 1.0})
    submitter = _FakeSubmitter()
    bridge = DevelopmentalPromotionBridge()
    decision = bridge.evaluate_and_submit(
        {"submit_operational_experience": submitter}, trace.steps[0], comparison, governor_results=[], episode_id="e",
    )
    assert decision.promoted is False
    assert decision.reason == "dimension_below_threshold"
    assert "causal_state_accuracy" in decision.tripped
    assert submitter.calls == []


def test_transfer_below_threshold_blocks_submission():
    trace = EpisodeTrace(episode_id="e", world_seed=1, rule_family="direct_trigger", agent_id="agent_a")
    _fully_scored_step(trace)
    comparison = compute_transfer_comparison({"causal_prediction_accuracy": 1.0}, {"causal_prediction_accuracy": 0.0})  # collapsed
    submitter = _FakeSubmitter()
    bridge = DevelopmentalPromotionBridge()
    decision = bridge.evaluate_and_submit(
        {"submit_operational_experience": submitter}, trace.steps[0], comparison, governor_results=[], episode_id="e",
    )
    assert decision.promoted is False
    assert decision.reason == "transfer_below_threshold"
    assert submitter.calls == []


# ---------------------------------------------------------------------------
# Each governor trips correctly on a constructed scenario, and logs instead
# of silently dropping.
# ---------------------------------------------------------------------------

def test_contradiction_accumulation_governor_trips_on_contradictory_evidence():
    tracker = ContradictionTracker()
    tracker.record("vessel_0.energy", "increase")
    result_before = DevelopmentalGovernors.contradiction_accumulation(tracker)
    assert result_before.tripped is False

    contradicted = tracker.record("vessel_0.energy", "decrease")
    assert contradicted is True
    result_after = DevelopmentalGovernors.contradiction_accumulation(tracker)
    assert result_after.tripped is True
    assert result_after.detail["conflict_count"] == 1


def test_confidence_rising_accuracy_falling_governor_trips():
    confidence_history = [0.2, 0.3, 0.4, 0.6, 0.9]
    accuracy_history = [0.9, 0.7, 0.5, 0.3, 0.1]
    result = DevelopmentalGovernors.confidence_rising_accuracy_falling(confidence_history, accuracy_history)
    assert result.tripped is True


def test_confidence_rising_accuracy_falling_governor_not_applicable_without_history():
    result = DevelopmentalGovernors.confidence_rising_accuracy_falling(None, None)
    assert result.tripped is False
    assert "not_applicable" in result.reason


def test_surface_fitness_without_transfer_governor_trips_the_hall_of_mirrors_case():
    result = DevelopmentalGovernors.surface_fitness_without_transfer(
        avatar_fitness_trend=0.25, transfer_score_trend=-0.4,
    )
    assert result.tripped is True


def test_surface_fitness_without_transfer_governor_does_not_trip_when_both_improve():
    result = DevelopmentalGovernors.surface_fitness_without_transfer(
        avatar_fitness_trend=0.1, transfer_score_trend=0.1,
    )
    assert result.tripped is False


def test_loss_of_stable_ability_governor_trips_on_regression():
    class _Ability:
        effect_tags = ("operational_synthesis", "synthesis_task:T1")

    class _FakeGenealogy:
        abilities = {"X:OP_SYNTH_abc": _Ability()}

    result = DevelopmentalGovernors.loss_of_stable_ability(
        _FakeGenealogy(), "synthesis_task:T1", regression_evidence_passed=False,
    )
    assert result.tripped is True


def test_loss_of_stable_ability_governor_does_not_trip_when_regression_passes():
    class _Ability:
        effect_tags = ("operational_synthesis", "synthesis_task:T1")

    class _FakeGenealogy:
        abilities = {"X:OP_SYNTH_abc": _Ability()}

    result = DevelopmentalGovernors.loss_of_stable_ability(
        _FakeGenealogy(), "synthesis_task:T1", regression_evidence_passed=True,
    )
    assert result.tripped is False


def test_runaway_complexity_governor_trips_using_the_real_ceiling():
    from aurora_internal.aurora_operational_synthesis import _MAX_PROGRAM_NODES

    # A right-nested chain of unary NOT nodes, one per level, exceeding the
    # ceiling -- constructed to actually walk _node_count()'s real recursion
    # (args-based), not a fake shortcut.
    tree = {"op": "INPUT"}
    for _ in range(_MAX_PROGRAM_NODES + 5):
        tree = {"op": "NOT", "args": [tree]}
    result = DevelopmentalGovernors.runaway_complexity(tree)
    assert result.tripped is True
    assert result.detail["node_count"] > _MAX_PROGRAM_NODES


def test_runaway_complexity_governor_not_applicable_without_tree():
    result = DevelopmentalGovernors.runaway_complexity(None)
    assert result.tripped is False
    assert "not_applicable" in result.reason


def test_meaning_expression_divergence_governor_trips_below_threshold():
    result = DevelopmentalGovernors.meaning_expression_divergence({"hesitation_fidelity": 0.0})
    assert result.tripped is True


def test_meaning_expression_divergence_governor_not_applicable_without_data():
    result = DevelopmentalGovernors.meaning_expression_divergence(None)
    assert result.tripped is False
    assert "not_applicable" in result.reason


def test_route_tripped_governors_logs_to_fail_dimension_and_study_topic_not_silently_dropped():
    tripped = [GovernorResult("runaway_complexity", True, "node_count=99 max=48")]
    trainer = _FakeDreamTrainer()
    autonomy = _FakeAutonomy()
    route_tripped_governors_to_fail_pressure(trainer, autonomy, tripped, "ep_x")
    assert trainer.recorded[0][0] == "runaway_complexity"
    assert any("ep_x" in topic for topic in autonomy.topics)

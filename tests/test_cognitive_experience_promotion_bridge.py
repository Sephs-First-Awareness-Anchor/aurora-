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
    ObservedEntity,
    ObservedWorldState,
    WorldState,
    compute_transfer_comparison,
    determine_admissibility_route,
    route_tripped_governors_to_fail_pressure,
)


def _fully_scored_step(trace: EpisodeTrace) -> None:
    # A second entity (conduit_0) whose property changes as the hidden
    # mechanism's effect, distinct from add_energy's own known direct
    # effect on vessel_0 itself -- Build 613 (K)'s role-normalized
    # evidence needs a genuine cross-entity signal to be meaningful.
    interp = CapturedInterpretation(
        raw_expression="Vessel 0's energy will increase, and Conduit 0's charge will change.",
        predicted_consequence={"entity_id": "conduit_0", "property": "charge", "direction": "change"},
        confidence=0.9,
    )
    trace.record_interpretation(0, "obs", ActionInvocation("add_energy", ("vessel_0",)), "act", interp)
    world_before = WorldState(
        tick=0,
        entities={
            "vessel_0": Entity("vessel_0", "vessel", {"energy": 1}),
            "conduit_0": Entity("conduit_0", "conduit", {"charge": "neutral"}),
        },
        relationships=[],
        agents=("agent_a",),
    )
    consequence = WorldState(
        tick=1,
        entities={
            "vessel_0": Entity("vessel_0", "vessel", {"energy": 2}),
            "conduit_0": Entity("conduit_0", "conduit", {"charge": "positive"}),
        },
        relationships=[],
        agents=("agent_a",),
    )
    trace.record_consequence(consequence)  # causal_scores are set directly below
    trace.steps[0].world_before = world_before
    trace.steps[0].observed_before = ObservedWorldState(
        tick=0, agent_id="agent_a",
        entities={
            "vessel_0": ObservedEntity("vessel_0", "vessel", {"energy": 1}),
            "conduit_0": ObservedEntity("conduit_0", "conduit", {"charge": "neutral"}),
        },
        relationships=(),
    )
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
        rule_family="direct_trigger",
    )

    assert decision.promoted is True
    assert decision.reason == "submitted"
    assert decision.route == "immediate_understanding"
    assert len(submitter.calls) == 1
    evidence = submitter.calls[0]
    assert "input_value" in evidence and "expected_output" in evidence
    # Build 608 (C): the narrow target operation, under a STABLE task id
    # (not unique per episode) so examples can accumulate under one WARP
    # task. Build 613 (K): role-normalized, fixed-schema shape -- the
    # action's own known direct effect on vessel_0 itself is excluded from
    # expected_output; only the hidden mechanism's effect on conduit_0
    # (the affected role) is reported.
    assert evidence["input_value"]["action_type"] == "add_energy"
    assert evidence["input_value"]["acting_entity_role"] == "vessel"
    assert evidence["input_value"]["visible_pre_state"]["entities"]["vessel_0"]["properties"]["energy"] == 1
    assert set(evidence["input_value"]["candidate_affected_roles"]) == {"vessel", "conduit"}
    assert evidence["expected_output"] == {
        "affected_entity_role": "conduit", "affected_property": "charge", "direction": "change", "delay": 0,
    }
    assert evidence["task_id"] == "RCEC:observed_state_plus_action_to_state_delta:direct_trigger"
    assert decision.submission_result["accepted"] is True


# ---------------------------------------------------------------------------
# Build 608 (B): two legitimate admissibility routes.
# ---------------------------------------------------------------------------

def test_immediate_understanding_route_admits_without_revision_quality():
    scores = {
        "causal_state_accuracy": 1.0,
        "causal_prediction_accuracy": 1.0,  # correct the first time
        "causal_discrimination": 1.0,
        "evidence_discipline": 1.0,
        "counterfactual_consistency": 1.0,
        "confidence_calibration": 0.85,
        # revision_quality deliberately absent -- not applicable, not required.
    }
    assert determine_admissibility_route(scores) == "immediate_understanding"


def test_successful_correction_route_admits_on_genuine_revision_improvement():
    scores = {
        "causal_state_accuracy": 1.0,
        "causal_prediction_accuracy": 0.0,  # wrong the first time
        "causal_discrimination": 1.0,
        "evidence_discipline": 1.0,
        "revision_quality": 1.0,           # but the revision fully corrected it
        "counterfactual_consistency": 1.0,
        "confidence_calibration": 0.85,
    }
    assert determine_admissibility_route(scores) == "successful_correction"


def test_no_admissible_route_when_wrong_and_never_corrected():
    scores = {
        "causal_state_accuracy": 1.0,
        "causal_prediction_accuracy": 0.0,
        # no revision_quality at all -- no backprojection ever ran, or it
        # ran but original was already correct (contradiction, so N/A here
        # too) -- either way, neither route's precondition is met.
    }
    assert determine_admissibility_route(scores) is None


def test_successful_correction_route_requires_full_revision_quality_threshold():
    trace = EpisodeTrace(episode_id="e", world_seed=1, rule_family="direct_trigger", agent_id="agent_a")
    _fully_scored_step(trace)
    # Wrong originally, only PARTIALLY improved by the revision.
    trace.steps[0].causal_scores["causal_prediction_accuracy"] = 0.0
    trace.steps[0].causal_scores["revision_quality"] = 0.5

    comparison = compute_transfer_comparison({"causal_prediction_accuracy": 1.0}, {"causal_prediction_accuracy": 1.0})
    submitter = _FakeSubmitter()
    bridge = DevelopmentalPromotionBridge()
    decision = bridge.evaluate_and_submit(
        {"submit_operational_experience": submitter}, trace.steps[0], comparison, governor_results=[],
        episode_id="e", rule_family="direct_trigger",
    )
    assert decision.promoted is False
    assert decision.route == "successful_correction"
    assert "revision_quality" in decision.tripped
    assert submitter.calls == []


# ---------------------------------------------------------------------------
# Build 608 (C): evidence is grouped under a stable task per rule family,
# not a fresh task per episode -- training and validation examples for the
# SAME operation must feed the SAME task_id.
# ---------------------------------------------------------------------------

def test_training_and_validation_episodes_share_the_same_stable_task_id():
    submitter = _FakeSubmitter()
    systems = {"submit_operational_experience": submitter}
    bridge = DevelopmentalPromotionBridge()

    training_trace = EpisodeTrace(episode_id="train_1", world_seed=1, rule_family="direct_trigger", agent_id="agent_a")
    _fully_scored_step(training_trace)
    bridge.evaluate_and_submit(
        systems, training_trace.steps[0],
        compute_transfer_comparison({"causal_prediction_accuracy": 1.0}, {"causal_prediction_accuracy": 0.9}),
        governor_results=[], episode_id="train_1", rule_family="direct_trigger", validation=False,
    )

    validation_trace = EpisodeTrace(episode_id="val_1", world_seed=2, rule_family="direct_trigger", agent_id="agent_a")
    _fully_scored_step(validation_trace)
    bridge.evaluate_and_submit(
        systems, validation_trace.steps[0],
        compute_transfer_comparison({"causal_prediction_accuracy": 1.0}, {"causal_prediction_accuracy": 0.9}),
        governor_results=[], episode_id="val_1", rule_family="direct_trigger", validation=True,
    )

    assert len(submitter.calls) == 2
    assert submitter.calls[0]["task_id"] == submitter.calls[1]["task_id"]
    assert submitter.calls[0]["validation"] is False
    assert submitter.calls[1]["validation"] is True


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

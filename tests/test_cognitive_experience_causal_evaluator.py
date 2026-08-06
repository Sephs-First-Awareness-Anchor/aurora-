# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Build 598: Recursive Causal Experience Chamber -- Stage 3 of 6.
Consequence, Causal Evaluator & Backprojection.

Covers: each of the five CausalEvaluator dimensions scores independently
and correctly against a world with known ground truth; a correlation-only
scenario produces a low causal-discrimination score when the interpretation
conflates the decoy with the true dependency; no scoring function inspects
response text for lexical markers; SimulatedAvatar.react() is untouched.
"""
import inspect
import os
import random
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import pytest

from aurora_internal.aurora_cognitive_experience_chamber import (  # noqa: E402
    ActionInvocation,
    CAUSAL_DIMENSION_NAMES,
    CapturedInterpretation,
    CausalEvaluationResult,
    CausalEvaluator,
    Entity,
    EpisodeTrace,
    HiddenRuleEngine,
    ObservationBoundary,
    Relationship,
    WorldGenerator,
    WorldState,
    apply_causal_evaluation,
)


def _ground_truth_world():
    return WorldState(
        tick=0,
        entities={
            "vessel_0": Entity("vessel_0", "vessel", {"energy": 1, "sealed": False, "color": "red"}),
            "vessel_1": Entity("vessel_1", "vessel", {"energy": 0, "sealed": True, "color": "neutral"}),
        },
        relationships=[Relationship("connected_to", "vessel_0", "vessel_1")],
        agents=("agent_a",),
        property_history={},
    )


def _consequence_energy_increased():
    world = _ground_truth_world()
    world.tick = 1
    world.entities["vessel_0"].properties["energy"] = 2
    return world


# ---------------------------------------------------------------------------
# state_accuracy
# ---------------------------------------------------------------------------

def test_state_accuracy_scores_correct_relation_belief_as_perfect():
    world = _ground_truth_world()
    interp = CapturedInterpretation(
        raw_expression="Vessel 0 is connected to Vessel 1.",
        believed_relations=(("vessel_0", "connected_to", "vessel_1"),),
    )
    assert CausalEvaluator.state_accuracy(interp, world) == 1.0


def test_state_accuracy_scores_wrong_relation_belief_as_zero():
    world = _ground_truth_world()
    interp = CapturedInterpretation(
        raw_expression="Vessel 1 is connected to Vessel 0.",
        believed_relations=(("vessel_1", "connected_to", "vessel_0"),),  # reversed -- does not hold
    )
    assert CausalEvaluator.state_accuracy(interp, world) == 0.0


def test_state_accuracy_partial_credit_across_mixed_relations():
    world = _ground_truth_world()
    interp = CapturedInterpretation(
        raw_expression="...",
        believed_relations=(
            ("vessel_0", "connected_to", "vessel_1"),   # true
            ("vessel_1", "connected_to", "vessel_0"),   # false
        ),
    )
    assert CausalEvaluator.state_accuracy(interp, world) == 0.5


# ---------------------------------------------------------------------------
# prediction_accuracy
# ---------------------------------------------------------------------------

def test_prediction_accuracy_correct_direction_scores_one():
    world_before = _ground_truth_world()
    consequence = _consequence_energy_increased()
    interp = CapturedInterpretation(
        raw_expression="...",
        predicted_consequence={"entity_id": "vessel_0", "property": "energy", "direction": "increase"},
    )
    assert CausalEvaluator.prediction_accuracy(interp, world_before, consequence) == 1.0


def test_prediction_accuracy_wrong_direction_scores_zero():
    world_before = _ground_truth_world()
    consequence = _consequence_energy_increased()
    interp = CapturedInterpretation(
        raw_expression="...",
        predicted_consequence={"entity_id": "vessel_0", "property": "energy", "direction": "decrease"},
    )
    assert CausalEvaluator.prediction_accuracy(interp, world_before, consequence) == 0.0


def test_prediction_accuracy_no_prediction_is_not_applicable():
    world_before = _ground_truth_world()
    consequence = _consequence_energy_increased()
    interp = CapturedInterpretation(raw_expression="...")
    assert CausalEvaluator.prediction_accuracy(interp, world_before, consequence) is None


# ---------------------------------------------------------------------------
# causal_discrimination -- the correlation-vs-causation test surface
# ---------------------------------------------------------------------------

def _world_with_decoy_and_rule():
    world = WorldGenerator().build_world(
        seed=61, num_entities=3, entity_types=("vessel", "conduit"), connect_chain=False
    )
    rng = random.Random(67)
    engine = HiddenRuleEngine.generate(world, rng=rng, family="conditional_on_third_variable")
    return world, engine


def test_causal_discrimination_rewards_naming_the_true_target_not_the_decoy():
    world, engine = _world_with_decoy_and_rule()
    if engine._rule.decoy_entity_id is None:
        pytest.skip("no decoy candidate available for this generated world")
    rule = engine._rule

    correct_interp = CapturedInterpretation(
        raw_expression="...",
        predicted_consequence={"entity_id": rule.target_entity_id, "property": rule.target_property, "direction": "change"},
    )
    assert CausalEvaluator.causal_discrimination(correct_interp, engine) == 1.0


def test_causal_discrimination_penalizes_conflating_decoy_with_true_dependency():
    world, engine = _world_with_decoy_and_rule()
    if engine._rule.decoy_entity_id is None:
        pytest.skip("no decoy candidate available for this generated world")
    rule = engine._rule

    fooled_interp = CapturedInterpretation(
        raw_expression="...",
        predicted_consequence={"entity_id": rule.decoy_entity_id, "property": rule.decoy_property, "direction": "increase"},
    )
    assert CausalEvaluator.causal_discrimination(fooled_interp, engine) == 0.0


def test_causal_discrimination_not_applicable_without_decoy_or_prediction():
    world, engine = _world_with_decoy_and_rule()
    interp = CapturedInterpretation(raw_expression="...")
    assert CausalEvaluator.causal_discrimination(interp, engine) is None


# ---------------------------------------------------------------------------
# evidence_discipline
# ---------------------------------------------------------------------------

def test_evidence_discipline_penalizes_unsupported_claims_beyond_the_boundary():
    world = _ground_truth_world()
    boundary = ObservationBoundary(rules=())
    observed = boundary.observe(world, "agent_a")

    grounded = CapturedInterpretation(raw_expression="...", identified_entities=("vessel_0",))
    assert CausalEvaluator.evidence_discipline(grounded, observed) == 1.0

    fabricated = CapturedInterpretation(raw_expression="...", identified_entities=("vessel_0", "vessel_999"))
    assert CausalEvaluator.evidence_discipline(fabricated, observed) == 0.5


# ---------------------------------------------------------------------------
# revision_quality
# ---------------------------------------------------------------------------

def test_revision_quality_measures_accuracy_delta_not_structural_change():
    """Build 608 (B): revision_quality measures revised_accuracy -
    original_accuracy, not merely whether the parsed structure changed.
    vessel_0's energy actually increases (1 -> 2); original wrongly
    predicted decrease (accuracy 0.0), revised correctly predicts increase
    (accuracy 1.0) -- full improvement, rescaled to 1.0."""
    world_before = _ground_truth_world()
    consequence = _consequence_energy_increased()
    original = CapturedInterpretation(
        raw_expression="...",
        predicted_consequence={"entity_id": "vessel_0", "property": "energy", "direction": "decrease"},
    )
    revised = CapturedInterpretation(
        raw_expression="...",
        predicted_consequence={"entity_id": "vessel_0", "property": "energy", "direction": "increase"},
    )
    delta = CausalEvaluator.revision_accuracy_delta(original, revised, world_before, consequence)
    assert delta == 1.0  # revised_accuracy(1.0) - original_accuracy(0.0)
    assert CausalEvaluator.revision_quality(original, revised, world_before, consequence) == 1.0


def test_revision_quality_scores_restating_the_same_wrong_belief_as_no_improvement():
    """Same wrong claim restated -- zero accuracy delta, not a full penalty
    to 0.0 (that would conflate 'no improvement' with 'got worse', which
    isn't possible once already at the accuracy floor). Still fails the
    successful_correction route's >=1.0 threshold either way."""
    world_before = _ground_truth_world()
    consequence = _consequence_energy_increased()
    original = CapturedInterpretation(
        raw_expression="Energy will decrease.",
        predicted_consequence={"entity_id": "vessel_0", "property": "energy", "direction": "decrease"},
    )
    revised = CapturedInterpretation(
        raw_expression="I still believe energy will decrease.",
        predicted_consequence={"entity_id": "vessel_0", "property": "energy", "direction": "decrease"},
    )
    delta = CausalEvaluator.revision_accuracy_delta(original, revised, world_before, consequence)
    assert delta == 0.0
    assert CausalEvaluator.revision_quality(original, revised, world_before, consequence) == 0.5


def test_revision_quality_not_applicable_when_original_prediction_was_already_correct():
    """Immediate-understanding territory: nothing needed correcting, so
    revision_quality is not a meaningful concept regardless of whether a
    revision object exists."""
    world_before = _ground_truth_world()
    consequence = _consequence_energy_increased()
    original = CapturedInterpretation(
        raw_expression="...",
        predicted_consequence={"entity_id": "vessel_0", "property": "energy", "direction": "increase"},
    )
    revised = CapturedInterpretation(raw_expression="...")
    assert CausalEvaluator.revision_quality(original, revised, world_before, consequence) is None
    assert CausalEvaluator.revision_quality(original, None, world_before, consequence) is None


# ---------------------------------------------------------------------------
# The direct test of "cognitive failure hidden by language": a fluent,
# confident response whose underlying interpretation was simply wrong must
# score low despite the fluency.
# ---------------------------------------------------------------------------

def test_fluent_confident_wrong_interpretation_scores_low_despite_fluency():
    world_before = _ground_truth_world()
    consequence = _consequence_energy_increased()
    fluent_but_wrong = CapturedInterpretation(
        raw_expression=(
            "I feel quite confident about this, and yes, I believe Vessel 0's energy "
            "will decrease steadily, however Vessel 1 will remain exactly as it was earlier."
        ),
        confidence=0.95,
        believed_relations=(("vessel_1", "connected_to", "vessel_0"),),  # reversed -- false
        predicted_consequence={"entity_id": "vessel_0", "property": "energy", "direction": "decrease"},  # wrong
    )
    result = CausalEvaluator.evaluate(
        fluent_but_wrong, world_before, consequence,
        ObservationBoundary().observe(world_before, "agent_a"),
        HiddenRuleEngine.generate(WorldGenerator().build_world(seed=1, num_entities=2), rng=random.Random(1)),
    )
    assert result.state_accuracy == 0.0
    assert result.prediction_accuracy == 0.0


# ---------------------------------------------------------------------------
# No lexical-marker scoring anywhere in CausalEvaluator (mirrors the
# grep-based placeholder-guard test convention).
# ---------------------------------------------------------------------------

def test_causal_evaluator_never_inspects_raw_expression_text():
    source = inspect.getsource(CausalEvaluator)
    assert "raw_expression" not in source
    for banned_literal in ("'however'", '"however"', "'maybe'", '"maybe"', "'earlier'", '"earlier"'):
        assert banned_literal not in source


def test_causal_dimension_names_match_result_mapping():
    # "transfer" is cross-episode (see TransferComparison) and deliberately
    # never appears in a single CausalEvaluationResult -- every OTHER
    # registered dimension name must be reachable via as_dimension_scores().
    result = CausalEvaluationResult(
        state_accuracy=0.1, prediction_accuracy=0.2, causal_discrimination=0.3,
        evidence_discipline=0.4, revision_quality=0.5, counterfactual_consistency=0.6,
        confidence_calibration=0.7,
    )
    assert set(result.as_dimension_scores()) == set(CAUSAL_DIMENSION_NAMES) - {"transfer"}


# ---------------------------------------------------------------------------
# apply_causal_evaluation() end-to-end wiring + fail-dimension feed
# ---------------------------------------------------------------------------

class _FakeDreamTrainer:
    def __init__(self):
        self.recorded = []

    def _record_fail_dimension(self, dim, severity, example=None):
        self.recorded.append((dim, severity, example))


def test_apply_causal_evaluation_requires_recorded_consequence():
    trace = EpisodeTrace(episode_id="e", world_seed=1, rule_family="direct_trigger", agent_id="agent_a")
    world = WorldGenerator().build_world(seed=1, num_entities=2)
    interp = CapturedInterpretation(raw_expression="...")
    trace.record_interpretation(0, "obs", ActionInvocation("wait", ()), "predict", interp)
    engine = HiddenRuleEngine.generate(world, rng=random.Random(1))
    boundary = ObservationBoundary()
    with pytest.raises(RuntimeError):
        apply_causal_evaluation(trace, 0, world, engine, boundary, "agent_a")


def test_apply_causal_evaluation_feeds_genuine_failures_to_dream_trainer():
    trace = EpisodeTrace(episode_id="e2", world_seed=1, rule_family="direct_trigger", agent_id="agent_a")
    world = WorldGenerator().build_world(seed=5, num_entities=2, entity_types=("vessel",), connect_chain=False)
    interp = CapturedInterpretation(
        raw_expression="...",
        believed_relations=(("vessel_0", "connected_to", "vessel_1"),),  # not actually a relationship -> 0.0
    )
    trace.record_interpretation(0, "obs", ActionInvocation("wait", ()), "predict", interp)
    engine = HiddenRuleEngine.generate(world, rng=random.Random(5))
    boundary = ObservationBoundary()
    consequence = world.clone()
    consequence.tick = 1
    trace.record_consequence(consequence)

    fake_trainer = _FakeDreamTrainer()
    result = apply_causal_evaluation(trace, 0, world, engine, boundary, "agent_a", dream_trainer=fake_trainer)
    assert result.state_accuracy == 0.0
    assert any(dim == "causal_state_accuracy" for dim, _sev, _ex in fake_trainer.recorded)
    assert trace.steps[0].causal_scores["causal_state_accuracy"] == 0.0


# ---------------------------------------------------------------------------
# Regression: SimulatedAvatar.react() untouched -- this stage adds a
# parallel evaluator, it does not modify or deprecate the avatar system.
# ---------------------------------------------------------------------------

def test_simulated_avatar_react_still_uses_its_own_lexical_scoring_untouched():
    from aurora_simulation_engine import SimulatedAvatar

    source = inspect.getsource(SimulatedAvatar.react)
    assert "sentences" in source and "words" in source  # still its original clarity heuristic

# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Build 598: Recursive Causal Experience Chamber -- Stage 5 of 6.
Expression Fidelity Bridge.

Covers: all four fidelity quadrants from the original proposal (correct
internal + correct expression; correct internal + wrong expression; wrong
internal + fluent expression; wrong internal + honestly hedged expression)
classify correctly; capturing the DualStrataSnapshot during a simulated
episode does not alter CERSBridge's live behavior for real turns -- read,
never a mutation.
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import pytest

from aurora_internal.aurora_cognitive_experience_chamber import (  # noqa: E402
    ActionInvocation,
    CapturedInterpretation,
    EpisodeTrace,
    ExpressionFidelityEvaluator,
    apply_expression_fidelity_evaluation,
)


# ---------------------------------------------------------------------------
# The four fidelity quadrants
# ---------------------------------------------------------------------------

def test_quadrant_correct_internal_correct_expression():
    q = ExpressionFidelityEvaluator.classify_fidelity_quadrant(internal_correct=True, expression_hedged=False)
    assert q == "correct_internal_correct_expression"


def test_quadrant_correct_internal_wrong_expression():
    """Right internally, but the expression hedges as if it weren't --
    a miscalibration in the OTHER direction."""
    q = ExpressionFidelityEvaluator.classify_fidelity_quadrant(internal_correct=True, expression_hedged=True)
    assert q == "correct_internal_wrong_expression"


def test_quadrant_wrong_internal_fluent_expression():
    """The direct 'cognitive failure hidden by fluent language' quadrant."""
    q = ExpressionFidelityEvaluator.classify_fidelity_quadrant(internal_correct=False, expression_hedged=False)
    assert q == "wrong_internal_fluent_expression"


def test_quadrant_wrong_internal_honestly_hedged_expression():
    q = ExpressionFidelityEvaluator.classify_fidelity_quadrant(internal_correct=False, expression_hedged=True)
    assert q == "wrong_internal_honest_expression"


# ---------------------------------------------------------------------------
# hesitation_fidelity -- internal signal vs actual hedging language,
# including the critical reverse case: confident-sounding text despite high
# internal hesitation.
# ---------------------------------------------------------------------------

def test_hesitation_fidelity_matches_when_both_hedge():
    snapshot = {"semantic_hesitation": True}
    interp = CapturedInterpretation(raw_expression="I'm not sure about this.", stated_unknowns=("I'm not sure about this.",))
    assert ExpressionFidelityEvaluator.hesitation_fidelity(snapshot, interp) == 1.0


def test_hesitation_fidelity_matches_when_neither_hedges():
    snapshot = {"semantic_hesitation": False}
    interp = CapturedInterpretation(raw_expression="Energy will increase.")
    assert ExpressionFidelityEvaluator.hesitation_fidelity(snapshot, interp) == 1.0


def test_hesitation_fidelity_flags_confident_expression_despite_high_internal_hesitation():
    """The critical reverse case: internal hesitation was high, but the
    expression reads confidently with no hedging at all."""
    snapshot = {"semantic_hesitation": True}
    interp = CapturedInterpretation(raw_expression="Energy will definitely increase.")
    assert ExpressionFidelityEvaluator.hesitation_fidelity(snapshot, interp) == 0.0


def test_hesitation_fidelity_flags_hedged_expression_despite_low_internal_hesitation():
    snapshot = {"semantic_hesitation": False}
    interp = CapturedInterpretation(raw_expression="I'm unsure.", stated_unknowns=("I'm unsure.",))
    assert ExpressionFidelityEvaluator.hesitation_fidelity(snapshot, interp) == 0.0


def test_hesitation_fidelity_not_applicable_without_snapshot():
    interp = CapturedInterpretation(raw_expression="...")
    assert ExpressionFidelityEvaluator.hesitation_fidelity(None, interp) is None
    assert ExpressionFidelityEvaluator.hesitation_fidelity({}, interp) is None


# ---------------------------------------------------------------------------
# intervention_fidelity
# ---------------------------------------------------------------------------

def test_intervention_fidelity_rewards_registering_reconsideration():
    snapshot = {"intervention_label": "reframe_needed", "geometry_deviation": None}
    interp = CapturedInterpretation(raw_expression="Actually, I'm not certain now.", stated_unknowns=("Actually, I'm not certain now.",))
    assert ExpressionFidelityEvaluator.intervention_fidelity(snapshot, interp) == 1.0


def test_intervention_fidelity_penalizes_proceeding_as_if_nothing_registered():
    snapshot = {"intervention_label": "reframe_needed", "geometry_deviation": None}
    interp = CapturedInterpretation(raw_expression="Energy will increase.")
    assert ExpressionFidelityEvaluator.intervention_fidelity(snapshot, interp) == 0.0


def test_intervention_fidelity_not_applicable_when_nothing_registered_internally():
    snapshot = {"intervention_label": None, "geometry_deviation": None}
    interp = CapturedInterpretation(raw_expression="Energy will increase.")
    assert ExpressionFidelityEvaluator.intervention_fidelity(snapshot, interp) is None


# ---------------------------------------------------------------------------
# causal_claim_preservation
# ---------------------------------------------------------------------------

def test_causal_claim_preservation_full_when_revision_addresses_same_claim():
    original = CapturedInterpretation(
        raw_expression="...", predicted_consequence={"entity_id": "vessel_0", "property": "energy", "direction": "increase"},
    )
    revised = CapturedInterpretation(
        raw_expression="...", predicted_consequence={"entity_id": "vessel_0", "property": "energy", "direction": "decrease"},
    )
    assert ExpressionFidelityEvaluator.causal_claim_preservation(original, revised) == 1.0


def test_causal_claim_preservation_partial_when_entity_referenced_but_claim_dropped():
    original = CapturedInterpretation(
        raw_expression="...", predicted_consequence={"entity_id": "vessel_0", "property": "energy", "direction": "increase"},
    )
    revised = CapturedInterpretation(raw_expression="...", identified_entities=("vessel_0",))
    assert ExpressionFidelityEvaluator.causal_claim_preservation(original, revised) == 0.5


def test_causal_claim_preservation_zero_when_silently_dropped():
    original = CapturedInterpretation(
        raw_expression="...", predicted_consequence={"entity_id": "vessel_0", "property": "energy", "direction": "increase"},
    )
    revised = CapturedInterpretation(raw_expression="I have nothing further to add.")
    assert ExpressionFidelityEvaluator.causal_claim_preservation(original, revised) == 0.0


def test_causal_claim_preservation_not_applicable_without_original_claim_or_revision():
    no_claim = CapturedInterpretation(raw_expression="...")
    revised = CapturedInterpretation(raw_expression="...")
    assert ExpressionFidelityEvaluator.causal_claim_preservation(no_claim, revised) is None
    original = CapturedInterpretation(
        raw_expression="...", predicted_consequence={"entity_id": "vessel_0", "property": "energy", "direction": "increase"},
    )
    assert ExpressionFidelityEvaluator.causal_claim_preservation(original, None) is None


# ---------------------------------------------------------------------------
# apply_expression_fidelity_evaluation() wiring
# ---------------------------------------------------------------------------

def test_apply_expression_fidelity_evaluation_wires_quadrant_from_causal_scores():
    trace = EpisodeTrace(episode_id="e", world_seed=1, rule_family="direct_trigger", agent_id="agent_a")
    interp = CapturedInterpretation(raw_expression="Energy will definitely increase.", confidence=0.9)
    trace.record_interpretation(0, "obs", ActionInvocation("wait", ()), "act", interp)
    trace.steps[0].dual_strata_snapshot = {"semantic_hesitation": True, "semantic_salience": 0.9}
    trace.steps[0].causal_scores = {"causal_prediction_accuracy": 0.0}  # she was wrong

    result = apply_expression_fidelity_evaluation(trace, 0)
    assert result["quadrant"] == "wrong_internal_fluent_expression"
    assert trace.steps[0].expression_fidelity == result


# ---------------------------------------------------------------------------
# Regression: capturing the DualStrataSnapshot during a simulated episode
# does not alter CERSBridge's live behavior for real (non-simulated) turns
# -- this must be a read, never a mutation.
# ---------------------------------------------------------------------------

def test_capture_helpers_are_read_only_no_write_calls():
    import inspect
    from aurora_internal.aurora_cognitive_experience_chamber import (
        capture_dual_strata_snapshot, read_cers_verdict_detail,
    )
    for fn in (capture_dual_strata_snapshot, read_cers_verdict_detail):
        source = inspect.getsource(fn)
        assert "_write_dual_strata_json" not in source
        assert "build_snapshot(" not in source
        assert ".state[" not in source  # never mutates CERS/contract state directly

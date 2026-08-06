# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Build 610: RCEC Closed-Loop Activation and Admissibility Repair -- E, F, G, H.

Covers: generate_mechanism()/HiddenRuleEngine.generate_from_mechanism()
resolve ONE stable role-level mechanism against different worlds (G);
WorldGenerator.build_world(required_types=...) guarantees a role's entity
type is present; ActionInterface.interpret_expression()'s four honest
action-commitment states -- selected/unselected/ambiguous/
echo_contaminated -- replacing the old silent "found a keyword anywhere
-> act" behavior (F); ExperienceIngestionBridge records valid experience
independent of cognitive success, requires genuine commitment, and skips
when the promotion bridge already submitted (E); compute_transfer_
comparison() requires a measurable causal prediction in BOTH episodes,
and TransferGenerator preserves mechanism roles (H).
"""
import os
import random
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_internal.aurora_cognitive_experience_chamber import (  # noqa: E402
    ACTION_TYPES,
    ENTITY_TYPES,
    PROPERTIES,
    ActionInterface,
    CapturedInterpretation,
    EpisodeStep,
    ExperienceIngestionBridge,
    HiddenRuleEngine,
    IngestionDecision,
    ObservationBoundary,
    ObservedEntity,
    ObservedWorldState,
    TransferGenerator,
    WorldGenerator,
    _ACTION_REQUIRED_PROPERTY,
    compute_transfer_comparison,
    generate_mechanism,
)


# ---------------------------------------------------------------------------
# G: MechanismSpec / generate_mechanism / generate_from_mechanism
# ---------------------------------------------------------------------------

def test_generate_mechanism_produces_a_catalog_valid_spec():
    for family in HiddenRuleEngine.RULE_FAMILIES:
        mech = generate_mechanism(random.Random(1), family=family)
        assert mech.trigger_action in ACTION_TYPES
        assert _ACTION_REQUIRED_PROPERTY[mech.trigger_action] in ENTITY_TYPES[mech.source_entity_type].properties
        assert mech.target_property in ENTITY_TYPES[mech.target_entity_type].properties
        assert mech.family == family


def test_generate_mechanism_is_deterministic_given_the_same_rng_seed():
    a = generate_mechanism(random.Random(42), family="direct_trigger")
    b = generate_mechanism(random.Random(42), family="direct_trigger")
    assert a == b


def test_generate_from_mechanism_resolves_the_same_roles_across_different_worlds():
    mechanism = generate_mechanism(random.Random(7), family="direct_trigger")
    world_a = WorldGenerator().build_world(
        seed=101, num_entities=3, entity_types=("vessel", "conduit", "sensor"),
        connect_chain=False, required_types=(mechanism.source_entity_type, mechanism.target_entity_type),
    )
    world_b = WorldGenerator().build_world(
        seed=999, num_entities=4, entity_types=("vessel", "conduit", "sensor"),
        connect_chain=False, required_types=(mechanism.source_entity_type, mechanism.target_entity_type),
    )
    engine_a = HiddenRuleEngine.generate_from_mechanism(world_a, mechanism, rng=random.Random(1))
    engine_b = HiddenRuleEngine.generate_from_mechanism(world_b, mechanism, rng=random.Random(2))

    assert engine_a._rule.trigger_action == engine_b._rule.trigger_action == mechanism.trigger_action
    assert engine_a._rule.target_property == engine_b._rule.target_property == mechanism.target_property
    assert engine_a._rule.effect_delta == engine_b._rule.effect_delta == mechanism.effect_delta
    assert world_a.entities[engine_a._rule.source_entity_id].entity_type == mechanism.source_entity_type
    assert world_b.entities[engine_b._rule.source_entity_id].entity_type == mechanism.source_entity_type
    assert world_a.entities[engine_a._rule.target_entity_id].entity_type == mechanism.target_entity_type
    assert world_b.entities[engine_b._rule.target_entity_id].entity_type == mechanism.target_entity_type


def test_generate_from_mechanism_raises_when_world_lacks_the_required_role():
    mechanism = generate_mechanism(random.Random(3), family="direct_trigger")
    other_types = [t for t in ENTITY_TYPES if t != mechanism.source_entity_type] or list(ENTITY_TYPES)
    world = WorldGenerator().build_world(
        seed=5, num_entities=2, entity_types=tuple(other_types), connect_chain=False,
    )
    try:
        HiddenRuleEngine.generate_from_mechanism(world, mechanism, rng=random.Random(1))
        assert False, "expected ValueError for a world missing the mechanism's source role"
    except ValueError:
        pass


def test_build_world_required_types_guarantees_presence():
    for seed in range(20):
        world = WorldGenerator().build_world(
            seed=seed, num_entities=3, entity_types=("vessel", "conduit", "sensor"),
            connect_chain=False, required_types=("conduit",),
        )
        assert any(e.entity_type == "conduit" for e in world.entities.values())


# ---------------------------------------------------------------------------
# F: action commitment
# ---------------------------------------------------------------------------

def _observed_two_vessels():
    from aurora_internal.aurora_cognitive_experience_chamber import Entity, WorldState
    world = WorldState(
        tick=0,
        entities={
            "vessel_0": Entity("vessel_0", "vessel", {"energy": 1, "sealed": False, "color": "red"}),
            "vessel_1": Entity("vessel_1", "vessel", {"energy": 0, "sealed": False, "color": "neutral"}),
        },
        relationships=[], agents=("agent_a",), property_history={},
    )
    return ObservationBoundary().observe(world, "agent_a")


def test_commitment_clause_is_selected():
    observed = _observed_two_vessels()
    phrases = ActionInterface.action_phrases(observed)
    result = ActionInterface.interpret_expression(
        "I will add energy to Vessel 0.", observed, 0.7, available_action_phrases=phrases,
    )
    assert result.interpretation.action_commitment == "selected"
    assert result.action.action_type == "add_energy"


def test_no_action_language_at_all_is_unselected_not_a_silent_wait_choice():
    observed = _observed_two_vessels()
    phrases = ActionInterface.action_phrases(observed)
    result = ActionInterface.interpret_expression(
        "I don't have a clear sense of that.", observed, 0.3, available_action_phrases=phrases,
    )
    assert result.interpretation.action_commitment == "unselected"
    assert result.action.action_type == "wait"


def test_action_mentioned_without_commitment_clause_is_ambiguous_and_does_not_execute():
    observed = _observed_two_vessels()
    phrases = ActionInterface.action_phrases(observed)
    result = ActionInterface.interpret_expression(
        "Vessel 0 might add energy soon, who knows.", observed, 0.3, available_action_phrases=phrases,
    )
    assert result.interpretation.action_commitment == "ambiguous"
    assert result.action.action_type == "wait"


def test_echoing_the_offered_action_menu_is_detected_and_does_not_execute_the_first_keyword():
    """The live-observed Build 610 failure: Aurora echoes the prompt back,
    and a naive scan attributes whichever action was listed first as
    though it were chosen. interpret_expression() must not do that."""
    observed = _observed_two_vessels()
    prompt = ActionInterface.build_prompt(observed)
    phrases = ActionInterface.action_phrases(observed)
    result = ActionInterface.interpret_expression(prompt, observed, 0.5, available_action_phrases=phrases)
    assert result.interpretation.action_commitment == "echo_contaminated"
    assert result.action.action_type == "wait"


def test_deliberate_wait_is_selected_not_unselected():
    observed = _observed_two_vessels()
    phrases = ActionInterface.action_phrases(observed)
    result = ActionInterface.interpret_expression(
        "I will wait and observe.", observed, 0.4, available_action_phrases=phrases,
    )
    assert result.interpretation.action_commitment == "selected"
    assert result.action.action_type == "wait"


def test_interpret_expression_without_available_action_phrases_still_works():
    """available_action_phrases defaults to None -- every pre-610 caller of
    interpret_expression() keeps working unchanged (echo detection simply
    never fires without menu context)."""
    observed = _observed_two_vessels()
    result = ActionInterface.interpret_expression("I will seal Vessel 0.", observed, 0.6)
    assert result.interpretation.action_commitment == "selected"
    assert result.action.action_type == "seal"


# ---------------------------------------------------------------------------
# E: ExperienceIngestionBridge
# ---------------------------------------------------------------------------

def _step_with_commitment(commitment: str) -> EpisodeStep:
    from aurora_internal.aurora_cognitive_experience_chamber import ActionInvocation, Entity, WorldState

    world_before = WorldState(
        tick=0, entities={"vessel_0": Entity("vessel_0", "vessel", {"energy": 1, "sealed": False, "color": "neutral"})},
        relationships=[], agents=("agent_a",), property_history={},
    )
    consequence = WorldState(
        tick=1, entities={"vessel_0": Entity("vessel_0", "vessel", {"energy": 2, "sealed": False, "color": "neutral"})},
        relationships=[], agents=("agent_a",), property_history={},
    )
    observed_before = ObservedWorldState(
        tick=0, agent_id="agent_a",
        entities={"vessel_0": ObservedEntity("vessel_0", "vessel", {"energy": 1, "sealed": False, "color": "neutral"})},
        relationships=(),
    )
    return EpisodeStep(
        tick=0, observation_text="...", action=ActionInvocation("add_energy", ("vessel_0",)), intent="act",
        interpretation=CapturedInterpretation(raw_expression="...", action_commitment=commitment),
        consequence=consequence, world_before=world_before, observed_before=observed_before,
    )


def test_ingest_submits_ground_truth_evidence_for_a_committed_action_regardless_of_cognition():
    submitted = []
    systems = {"submit_operational_experience": lambda ev: (submitted.append(ev), {"accepted": True})[1]}
    step = _step_with_commitment("selected")

    decision = ExperienceIngestionBridge.ingest(systems, step, episode_id="ep1", rule_family="direct_trigger")

    assert isinstance(decision, IngestionDecision)
    assert decision.ingested is True
    assert len(submitted) == 1
    assert submitted[0]["task_id"] == "RCEC:observed_state_plus_action_to_state_delta:direct_trigger"
    assert submitted[0]["expected_output"] == {"vessel_0.energy": {"before": 1, "after": 2}}


def test_ingest_refuses_ambiguous_and_echo_contaminated_and_unselected_actions_by_default():
    for commitment in ("ambiguous", "echo_contaminated", "unselected"):
        submitted = []
        systems = {"submit_operational_experience": lambda ev: (submitted.append(ev), {"accepted": True})[1]}
        step = _step_with_commitment(commitment)

        decision = ExperienceIngestionBridge.ingest(systems, step, episode_id="ep1", rule_family="direct_trigger")

        assert decision.ingested is False
        assert decision.reason == f"action_not_committed:{commitment}"
        assert not submitted


def test_ingest_skips_when_already_submitted_by_promotion_bridge():
    submitted = []
    systems = {"submit_operational_experience": lambda ev: (submitted.append(ev), {"accepted": True})[1]}
    step = _step_with_commitment("selected")

    decision = ExperienceIngestionBridge.ingest(
        systems, step, episode_id="ep1", rule_family="direct_trigger", already_submitted=True,
    )

    assert decision.ingested is False
    assert decision.reason == "already_submitted_via_promotion_bridge"
    assert not submitted


def test_ingest_can_bypass_commitment_requirement_for_external_actor_trials():
    submitted = []
    systems = {"submit_operational_experience": lambda ev: (submitted.append(ev), {"accepted": True})[1]}
    step = _step_with_commitment("external_actor")

    decision = ExperienceIngestionBridge.ingest(
        systems, step, episode_id="ep1", rule_family="direct_trigger", require_commitment=False,
    )

    assert decision.ingested is True
    assert submitted


# ---------------------------------------------------------------------------
# H: transfer preserves mechanism, and requires a measurable prediction
# in both episodes before producing a transfer_score.
# ---------------------------------------------------------------------------

def test_compute_transfer_comparison_is_none_without_a_measurable_prediction_in_both():
    original = {"causal_state_accuracy": 1.0, "evidence_discipline": 1.0}
    transfer = {"causal_state_accuracy": 1.0, "evidence_discipline": 1.0}
    comparison = compute_transfer_comparison(original, transfer)
    assert comparison.transfer_score is None


def test_compute_transfer_comparison_scores_when_prediction_accuracy_present_in_both():
    original = {"causal_prediction_accuracy": 1.0, "causal_state_accuracy": 1.0}
    transfer = {"causal_prediction_accuracy": 1.0, "causal_state_accuracy": 1.0}
    comparison = compute_transfer_comparison(original, transfer)
    assert comparison.transfer_score == 1.0


def test_compute_transfer_comparison_is_none_when_only_one_side_has_a_prediction():
    original = {"causal_prediction_accuracy": 1.0, "causal_state_accuracy": 1.0}
    transfer = {"causal_state_accuracy": 1.0}
    comparison = compute_transfer_comparison(original, transfer)
    assert comparison.transfer_score is None


def test_transfer_generator_preserves_mechanism_roles_across_seeds():
    mechanism = generate_mechanism(random.Random(11), family="direct_trigger")
    for seed in (1, 2, 3):
        world, engine = TransferGenerator.generate_transfer_world(
            rule_family="direct_trigger", seed=seed, num_entities=3, mechanism=mechanism,
        )
        assert engine._rule.trigger_action == mechanism.trigger_action
        assert engine._rule.target_property == mechanism.target_property
        assert engine._rule.effect_delta == mechanism.effect_delta
        assert world.entities[engine._rule.source_entity_id].entity_type == mechanism.source_entity_type
        assert world.entities[engine._rule.target_entity_id].entity_type == mechanism.target_entity_type


def test_transfer_generator_without_a_mechanism_falls_back_to_pre_610_random_rule_behavior():
    world, engine = TransferGenerator.generate_transfer_world(rule_family="direct_trigger", seed=1, num_entities=3)
    assert engine._rule.family == "direct_trigger"

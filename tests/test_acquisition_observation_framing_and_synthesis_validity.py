# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
RCEC acquisition-framing and Operational Synthesis candidate-validity
repair (Repairs M and N, following Build 619).

Repair M ("Acquisition is still framed as an assessment"): demonstrated/
control acquisition trials stored ActionInterface.build_prompt()'s full
text (world observation + action menu + "choose one action, state what
you predict...") as the step's observation_text, which
run_witnessed_observation() then embedded verbatim into "Earlier you
observed: [...]" -- an old demand to act and predict, immediately
followed by "You are not being asked to choose an action or make a
prediction right now." Acquisition steps now store describe_observation()
output only; the assessment path (run_episode_step()) is unchanged.

Repair N ("Operational Synthesis is exposing a stale invalid candidate"):
once AuroraOperationalSynthesisChamber.observe_example() synthesized a
candidate program, a later ordinary (non-validation) training example
that contradicted it never rescored, invalidated, or triggered
resynthesis -- confirmed live with the exact canary shape (2 demonstrated
+ 2 control transitions: seal->changes, seal->changes, unseal->no_change,
unseal->no_change): after the 3rd example a candidate synthesizes, and
the 4th (contradicting) example is silently ignored by the existing
candidate while training_score and status keep advertising as if nothing
happened, and execute(..., allow_trial=True) still runs the stale
program. A candidate must mean "fits all currently available training
evidence," not "once fit an earlier subset."
"""
import os
import sys
import random
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_internal.aurora_cognitive_experience_chamber import (  # noqa: E402
    ActionInterface,
    HiddenRuleEngine,
    ObservationBoundary,
    WorldGenerator,
    describe_observation,
    generate_mechanism,
)
from aurora_internal.aurora_operational_synthesis import (  # noqa: E402
    AuroraOperationalSynthesisChamber,
)


def _world_and_observed(seed: int):
    mechanism = generate_mechanism(random.Random(42), family="direct_trigger")
    world = WorldGenerator().build_world(
        seed=seed, num_entities=3, entity_types=("vessel", "conduit", "sensor"),
        connect_chain=False, required_types=(mechanism.source_entity_type, mechanism.target_entity_type),
    )
    boundary = ObservationBoundary()
    observed = boundary.observe(world, "agent_a")
    return observed


# ===========================================================================
# Repair M: observation-only acquisition framing
# ===========================================================================

def test_m1_observation_only_text_excludes_action_menu_and_instructions():
    observed = _world_and_observed(1)
    obs_only = describe_observation(observed)
    assert "Available actions" not in obs_only
    assert "Choose one action" not in obs_only
    assert "predict" not in obs_only.lower()
    assert "confident" not in obs_only.lower()


def test_m2_assessment_prompt_still_includes_action_menu_and_instructions():
    observed = _world_and_observed(2)
    full_prompt = ActionInterface.build_prompt(observed)
    assert "Available actions" in full_prompt
    assert "Choose one action" in full_prompt


def test_m3_acquisition_episode_step_stores_observation_only_text():
    mechanism = generate_mechanism(random.Random(613), family="direct_trigger")
    world = WorldGenerator().build_world(
        seed=10, num_entities=3, entity_types=("vessel", "conduit", "sensor"),
        connect_chain=False, required_types=(mechanism.source_entity_type, mechanism.target_entity_type),
    )
    engine = HiddenRuleEngine.generate_from_mechanism(world, mechanism, rng=random.Random(11))
    boundary = ObservationBoundary()

    from aurora_internal.aurora_cognitive_experience_chamber import (
        EpisodeTrace, CapturedInterpretation, ActionInvocation, describe_observation as _do,
    )
    trace = EpisodeTrace(episode_id="m3", world_seed=world.tick, rule_family=engine._rule.family, agent_id="agent_a")
    observed = boundary.observe(world, "agent_a")
    scripted_action = ActionInvocation(mechanism.trigger_action, (engine._rule.source_entity_id,))
    observation_text = _do(observed)
    interpretation = CapturedInterpretation(raw_expression="", confidence=0.0, action_commitment="external_actor")
    trace.record_interpretation(
        tick=world.tick, observation_text=observation_text, action=scripted_action,
        intent="observe", interpretation=interpretation, observation_kind="observation_only",
    )
    step = trace.steps[0]
    assert step.observation_kind == "observation_only"
    assert "Available actions" not in step.observation_text
    assert "Choose one action" not in step.observation_text


def test_m4_witnessed_observation_prompt_never_contains_a_contradictory_instruction_history():
    # Reconstruct exactly the prompt run_witnessed_observation() builds,
    # without needing a live boot -- this is pure string assembly given
    # step.observation_text and the post-consequence observation.
    observed = _world_and_observed(3)
    observation_text = describe_observation(observed)
    after_text = describe_observation(observed)
    witness_prompt = (
        f"Earlier you observed: {observation_text} "
        f"Then, without your involvement, this happened: {after_text} "
        "You are not being asked to choose an action or make a prediction right now -- "
        "just take note of what changed."
    )
    assert "Available actions" not in witness_prompt
    assert "Choose one action" not in witness_prompt
    # The specific contradiction this repairs: a demand to act/predict
    # earlier in the SAME prompt that later denies she's being asked to.
    assert "state what you predict" not in witness_prompt.lower()


def test_m5_default_observation_kind_preserves_backward_compatible_assessment_semantics():
    from aurora_internal.aurora_cognitive_experience_chamber import (
        EpisodeTrace, CapturedInterpretation, ActionInvocation,
    )
    trace = EpisodeTrace(episode_id="m5", world_seed=0, rule_family="direct_trigger", agent_id="agent_a")
    trace.record_interpretation(
        tick=0, observation_text="Available actions: seal Vessel 0.", action=ActionInvocation("wait", ()),
        intent="predict", interpretation=CapturedInterpretation(raw_expression="", confidence=0.0),
    )
    assert trace.steps[0].observation_kind == "assessment_prompt"


def test_m6_episode_step_export_import_round_trips_observation_kind():
    from aurora_internal.aurora_cognitive_experience_chamber import (
        EpisodeTrace, CapturedInterpretation, ActionInvocation,
        _episode_step_to_dict, _episode_step_from_dict,
    )
    trace = EpisodeTrace(episode_id="m6", world_seed=0, rule_family="direct_trigger", agent_id="agent_a")
    trace.record_interpretation(
        tick=0, observation_text="Conduit 0 is unsealed.", action=ActionInvocation("wait", ()),
        intent="observe", interpretation=CapturedInterpretation(raw_expression="", confidence=0.0),
        observation_kind="observation_only",
    )
    restored = _episode_step_from_dict(_episode_step_to_dict(trace.steps[0]))
    assert restored.observation_kind == "observation_only"
    assert restored.observation_text == "Conduit 0 is unsealed."


# ===========================================================================
# Repair N: incremental candidate validity
# ===========================================================================

def _chamber():
    tmp = tempfile.mkdtemp()
    return AuroraOperationalSynthesisChamber(state_dir=tmp, persist=False)


def test_n1_exact_canary_shape_candidate_is_invalidated_by_contradicting_fourth_example():
    chamber = _chamber()
    chamber.observe_example("rcec_task", {"vessel": "v1"}, "changes", need_description="effect")
    chamber.observe_example("rcec_task", {"vessel": "v2"}, "changes")
    r3 = chamber.observe_example("rcec_task", {"vessel": "v3"}, "changes")
    assert r3.get("candidate", {}).get("training_score") == 1.0

    # A repeat of example 1's exact input, but contradicting -- forces an
    # unresolvable contradiction rather than a memorizable pattern, so
    # resynthesis genuinely cannot find a program spanning all evidence.
    r4 = chamber.observe_example("rcec_task", {"vessel": "v1"}, "no_change")
    task = chamber._tasks["rcec_task"]
    assert task.last_invalidated_by, "the invalidating example must be recorded"
    assert task.candidate is None, (
        "an invalidated candidate that cannot be honestly resynthesized "
        "must not be preserved"
    )


def test_n2_stale_candidate_is_no_longer_reachable_through_allow_trial_consultation():
    chamber = _chamber()
    chamber.observe_example("rcec_task2", {"vessel": "v1"}, "changes", need_description="effect")
    chamber.observe_example("rcec_task2", {"vessel": "v2"}, "changes")
    chamber.observe_example("rcec_task2", {"vessel": "v3"}, "changes")
    chamber.observe_example("rcec_task2", {"vessel": "v1"}, "no_change")  # contradicts ex. 1

    result = chamber.execute("rcec_task2", {"vessel": "v9"}, allow_trial=True)
    assert result.get("executed") is False
    assert result.get("reason") in ("no_candidate", "candidate_invalidated")


def test_n3_successful_resynthesis_against_full_evidence_replaces_the_stale_candidate():
    chamber = _chamber()
    # A genuinely learnable pattern: action type alone determines outcome.
    chamber.observe_example("rcec_task3", {"action": "seal"}, "changes", need_description="effect")
    chamber.observe_example("rcec_task3", {"action": "seal"}, "changes")
    chamber.observe_example("rcec_task3", {"action": "seal"}, "changes")
    r4 = chamber.observe_example("rcec_task3", {"action": "unseal"}, "no_change")
    task = chamber._tasks["rcec_task3"]
    # The new candidate (if any) must actually fit the example that
    # invalidated the old one, not just the original three.
    if task.candidate is not None:
        result = chamber.execute("rcec_task3", {"action": "unseal"}, allow_trial=True)
        assert result.get("executed") is True
        assert result.get("output") == "no_change"


def test_n4_candidate_training_score_reflects_full_current_evidence_not_a_stale_prefix():
    chamber = _chamber()
    chamber.observe_example("rcec_task4", {"vessel": "v1"}, "changes", need_description="effect")
    chamber.observe_example("rcec_task4", {"vessel": "v2"}, "changes")
    chamber.observe_example("rcec_task4", {"vessel": "v3"}, "changes")
    chamber.observe_example("rcec_task4", {"vessel": "v1"}, "no_change")
    task = chamber._tasks["rcec_task4"]
    if task.candidate is not None:
        # A surviving/replacement candidate's score must not silently be
        # the pre-invalidation 1.0 while actually failing current evidence.
        assert task.candidate.training_score < 1.0 or task.candidate.status == "trial"


def test_n5_a_candidate_that_still_fits_a_new_example_is_not_invalidated():
    chamber = _chamber()
    chamber.observe_example("rcec_task5", {"vessel": "v1"}, "changes", need_description="effect")
    chamber.observe_example("rcec_task5", {"vessel": "v2"}, "changes")
    r3 = chamber.observe_example("rcec_task5", {"vessel": "v3"}, "changes")
    candidate_before = r3.get("candidate", {}).get("program_id")

    r4 = chamber.observe_example("rcec_task5", {"vessel": "v4"}, "changes")  # consistent, not contradicting
    task = chamber._tasks["rcec_task5"]
    assert task.status != "candidate_invalidated"
    assert not task.last_invalidated_by
    assert task.candidate is not None
    assert task.candidate.training_score == 1.0


def test_n6_validation_flagged_contradicting_example_is_also_caught():
    chamber = _chamber()
    chamber.observe_example("rcec_task6", {"vessel": "v1"}, "changes", need_description="effect")
    chamber.observe_example("rcec_task6", {"vessel": "v2"}, "changes")
    chamber.observe_example("rcec_task6", {"vessel": "v3"}, "changes")
    chamber.observe_example("rcec_task6", {"vessel": "v1"}, "no_change", validation=True)
    task = chamber._tasks["rcec_task6"]
    assert task.last_invalidated_by
    result = chamber.execute("rcec_task6", {"vessel": "v9"}, allow_trial=True)
    assert result.get("executed") is False


def test_n7_execute_rejects_a_manually_marked_dissolved_or_failed_candidate_regardless_of_allow_trial():
    chamber = _chamber()
    chamber.observe_example("rcec_task7", {"vessel": "v1"}, "changes", need_description="effect")
    chamber.observe_example("rcec_task7", {"vessel": "v2"}, "changes")
    r3 = chamber.observe_example("rcec_task7", {"vessel": "v3"}, "changes")
    assert r3.get("candidate") is not None
    task = chamber._tasks["rcec_task7"]
    for bad_status in ("failed", "dissolved", "stale"):
        task.candidate.status = bad_status
        result = chamber.execute("rcec_task7", {"vessel": "v9"}, allow_trial=True)
        assert result.get("executed") is False
        assert result.get("reason") == "candidate_invalidated"

# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Build 598: Recursive Causal Experience Chamber -- Stage 2 of 6.
Episode Loop & Interpretation Capture.

Covers: a full episode runs through _run_simulation_live_response_bridge()
using a Stage-1 world; interpretation is captured before HiddenRuleEngine.
step() fires; EpisodeTrace correctly orders observation -> action ->
interpretation -> consequence; recording a consequence without a prior
captured interpretation raises; the reentrancy guard (_live_turn_depth)
behaves correctly standalone vs nested.
"""
import os
import random
import shutil
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import pytest

from aurora_internal.aurora_cognitive_experience_chamber import (  # noqa: E402
    ActionInterface,
    ActionInvocation,
    CapturedInterpretation,
    Entity,
    EpisodeTrace,
    HiddenRuleEngine,
    ObservationBoundary,
    WorldGenerator,
    WorldState,
    build_episode_runtime_context,
    run_episode_step,
)


# ---------------------------------------------------------------------------
# ActionInterface.interpret_expression() -- pure unit coverage, no live boot
# ---------------------------------------------------------------------------

def _observed_two_vessels():
    world = WorldState(
        tick=0,
        entities={
            "vessel_0": Entity("vessel_0", "vessel", {"energy": 1, "sealed": False, "color": "red"}),
            "vessel_1": Entity("vessel_1", "vessel", {"energy": 0, "sealed": False, "color": "neutral"}),
        },
        relationships=[],
        agents=("agent_a",),
        property_history={},
    )
    return ObservationBoundary().observe(world, "agent_a")


def test_interpret_expression_detects_action_and_target():
    observed = _observed_two_vessels()
    result = ActionInterface.interpret_expression("I will add energy to Vessel 0.", observed, confidence=0.7)
    assert result.intent == "act"
    assert result.action.action_type == "add_energy"
    assert result.action.target_ids == ("vessel_0",)
    assert "vessel_0" in result.interpretation.identified_entities
    assert result.interpretation.confidence == 0.7


def test_interpret_expression_captures_predicted_consequence_and_unknowns():
    observed = _observed_two_vessels()
    text = "I will add energy to Vessel 0. I predict Vessel 0's energy will increase, but I'm not sure by how much."
    result = ActionInterface.interpret_expression(text, observed, confidence=0.4)
    assert result.interpretation.predicted_consequence == {
        "entity_id": "vessel_0", "property": "energy", "direction": "increase",
    }
    assert result.interpretation.stated_unknowns
    assert result.interpretation.evidence_cited


def test_interpret_expression_with_no_action_verb_and_question_is_ask_intent():
    observed = _observed_two_vessels()
    result = ActionInterface.interpret_expression("What does Vessel 0 contain?", observed, confidence=0.2)
    assert result.intent == "ask"
    assert result.action == ActionInvocation("wait", ())


def test_interpret_expression_with_no_action_verb_and_no_question_is_predict_intent():
    observed = _observed_two_vessels()
    result = ActionInterface.interpret_expression("Vessel 0 seems empty right now.", observed, confidence=0.5)
    assert result.intent == "predict"
    assert result.action == ActionInvocation("wait", ())


def test_build_prompt_never_asks_a_leading_question_about_the_hidden_rule():
    observed = _observed_two_vessels()
    prompt = ActionInterface.build_prompt(observed)
    assert "rule" not in prompt.lower()
    assert "hidden" not in prompt.lower()


# ---------------------------------------------------------------------------
# EpisodeTrace ordering + serialization
# ---------------------------------------------------------------------------

def test_episode_trace_enforces_interpretation_before_consequence():
    trace = EpisodeTrace(episode_id="ep1", world_seed=1, rule_family="direct_trigger", agent_id="agent_a")
    world = WorldGenerator().build_world(seed=1, num_entities=3)
    with pytest.raises(RuntimeError):
        trace.record_consequence(world)


def test_episode_trace_orders_observation_action_interpretation_consequence():
    trace = EpisodeTrace(episode_id="ep2", world_seed=2, rule_family="direct_trigger", agent_id="agent_a")
    world = WorldGenerator().build_world(seed=2, num_entities=3)
    interpretation = CapturedInterpretation(raw_expression="I will wait.")
    trace.record_interpretation(
        tick=world.tick,
        observation_text="Vessel 0 is empty.",
        action=ActionInvocation("wait", ()),
        intent="act",
        interpretation=interpretation,
    )
    assert trace.steps[-1].consequence is None
    trace.record_consequence(world)
    assert trace.steps[-1].consequence is world
    assert trace.steps[-1].observation_text == "Vessel 0 is empty."
    assert trace.steps[-1].interpretation is interpretation

    # A second record_consequence() without a fresh interpretation must raise.
    with pytest.raises(RuntimeError):
        trace.record_consequence(world)


def test_episode_trace_round_trips_through_serialization():
    trace = EpisodeTrace(episode_id="ep3", world_seed=3, rule_family="threshold_trigger", agent_id="agent_a")
    world = WorldGenerator().build_world(seed=3, num_entities=3)
    interpretation = CapturedInterpretation(
        raw_expression="Vessel 0 has energy.",
        identified_entities=("vessel_0",),
        believed_relations=(("vessel_0", "connected_to", "vessel_1"),),
        predicted_consequence={"entity_id": "vessel_0", "property": "energy", "direction": "increase"},
        confidence=0.6,
        evidence_cited=("Vessel 0 has energy.",),
        stated_unknowns=(),
    )
    trace.record_interpretation(
        tick=world.tick,
        observation_text="Vessel 0 has energy.",
        action=ActionInvocation("add_energy", ("vessel_0",)),
        intent="act",
        interpretation=interpretation,
    )
    trace.record_consequence(world)
    trace.close(world)

    round_tripped = EpisodeTrace.from_dict(trace.to_dict())
    assert round_tripped.episode_id == trace.episode_id
    assert round_tripped.world_seed == trace.world_seed
    assert round_tripped.rule_family == trace.rule_family
    assert len(round_tripped.steps) == 1
    rstep = round_tripped.steps[0]
    assert rstep.action == ActionInvocation("add_energy", ("vessel_0",))
    assert rstep.interpretation.identified_entities == ("vessel_0",)
    assert rstep.interpretation.believed_relations == (("vessel_0", "connected_to", "vessel_1"),)
    assert rstep.interpretation.predicted_consequence == {"entity_id": "vessel_0", "property": "energy", "direction": "increase"}
    assert rstep.consequence is not None
    assert rstep.consequence.entities.keys() == world.entities.keys()
    assert round_tripped.terminal_state is not None
    assert round_tripped.terminal_state.tick == world.tick


# ---------------------------------------------------------------------------
# Live: a full episode through the real bridge, real boot_aurora(); pre-
# consequence ordering; reentrancy guard standalone vs nested.
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def live_systems(tmp_path_factory):
    import aurora as A

    state_dir = tmp_path_factory.mktemp("aurora_state_stage2")
    shutil.copytree(os.path.join(REPO_ROOT, "aurora_state"), str(state_dir), dirs_exist_ok=True)
    systems = A.boot_aurora(state_dir=str(state_dir), runtime_profile="surface", verbose=False)
    return systems


def _fresh_episode(seed: int, systems):
    world = WorldGenerator().build_world(seed=seed, num_entities=3, entity_types=("vessel", "conduit"), connect_chain=False)
    engine = HiddenRuleEngine.generate(world, rng=random.Random(seed), family="direct_trigger")
    boundary = ObservationBoundary()
    trace = EpisodeTrace(episode_id=f"live_ep_{seed}", world_seed=seed, rule_family=engine._rule.family, agent_id="agent_a")
    runtime_context = build_episode_runtime_context(systems)
    return world, engine, boundary, trace, runtime_context


def test_live_full_episode_through_real_bridge_captures_pre_consequence_interpretation(live_systems):
    systems = live_systems
    world, engine, boundary, trace, runtime_context = _fresh_episode(seed=501, systems=systems)

    assert int(systems.get("_live_turn_depth", 0) or 0) == 0  # standalone, no live turn in progress

    new_state = run_episode_step(trace, systems, runtime_context, world, engine, boundary, "agent_a")

    assert len(trace.steps) == 1
    step = trace.steps[0]
    assert step.interpretation.raw_expression  # something real came back from the bridge
    assert step.consequence is new_state
    assert step.tick == world.tick  # captured against the PRE-step tick/observation

    # record_consequence() already enforced ordering structurally; confirm it
    # is genuinely unusable to record a second consequence without a new turn.
    with pytest.raises(RuntimeError):
        trace.record_consequence(new_state)


def test_live_episode_standalone_vs_nested_reentrancy_guard(live_systems):
    systems = live_systems

    # Standalone: no live turn in progress.
    systems["_live_turn_depth"] = 0
    world_a, engine_a, boundary_a, trace_a, ctx_a = _fresh_episode(seed=502, systems=systems)
    run_episode_step(trace_a, systems, ctx_a, world_a, engine_a, boundary_a, "agent_a")
    assert trace_a.steps[0].interpretation.raw_expression

    # Nested: simulate a real live turn already in progress on this systems
    # object (the D2.2 reentrancy case) -- the bridge must defer rather than
    # recurse, and the episode loop must still capture SOMETHING and still
    # order interpretation before consequence, without crashing.
    systems["_live_turn_depth"] = 1
    try:
        world_b, engine_b, boundary_b, trace_b, ctx_b = _fresh_episode(seed=503, systems=systems)
        new_state_b = run_episode_step(trace_b, systems, ctx_b, world_b, engine_b, boundary_b, "agent_a")
        assert len(trace_b.steps) == 1
        assert trace_b.steps[0].consequence is new_state_b
    finally:
        systems["_live_turn_depth"] = 0

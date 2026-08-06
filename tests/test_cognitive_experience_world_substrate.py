# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Build 598: Recursive Causal Experience Chamber -- Stage 1 of 6.
World & Hidden Rule Substrate.

Covers: HiddenRuleEngine.step() consistency across repeated runs of the same
rule family; ObservationBoundary correctly withholding hidden/delayed/
perspective-restricted state; describe_observation() never leaking any token
that names the relation type or rule family.
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import random

import pytest

from aurora_internal.aurora_cognitive_experience_chamber import (  # noqa: E402
    ActionInvocation,
    DENYLIST_TOKENS,
    Entity,
    HiddenRuleEngine,
    ObservationBoundary,
    Relationship,
    VisibilityRule,
    WorldGenerator,
    WorldState,
    describe_observation,
)


# ---------------------------------------------------------------------------
# WorldGenerator sanity
# ---------------------------------------------------------------------------

def test_world_generator_builds_typed_world_with_agents():
    world = WorldGenerator().build_world(seed=1, num_entities=4, agents=("agent_a", "agent_b"))
    assert len(world.entities) == 4
    assert world.agents == ("agent_a", "agent_b")
    assert world.tick == 0
    for entity in world.entities.values():
        assert entity.entity_type in ("vessel", "conduit", "sensor")


def test_world_generator_is_seed_reproducible():
    a = WorldGenerator().build_world(seed=42, num_entities=3)
    b = WorldGenerator().build_world(seed=42, num_entities=3)
    assert {eid: e.properties for eid, e in a.entities.items()} == {eid: e.properties for eid, e in b.entities.items()}


def test_world_state_clone_is_independent():
    world = WorldGenerator().build_world(seed=2, num_entities=3)
    clone = world.clone()
    first_id = next(iter(clone.entities))
    clone.entities[first_id].properties["energy"] = 999
    assert world.entities[first_id].properties.get("energy") != 999


# ---------------------------------------------------------------------------
# HiddenRuleEngine.step() consistency across repeated runs, per rule family
# ---------------------------------------------------------------------------

def _world_with_vessel_and_conduit(seed: int) -> WorldState:
    return WorldGenerator().build_world(
        seed=seed, num_entities=3, entity_types=("vessel", "conduit"), connect_chain=False
    )


@pytest.mark.parametrize("family", HiddenRuleEngine.RULE_FAMILIES)
def test_step_is_consistent_across_repeated_runs_same_family(family):
    for seed in range(5):
        world = _world_with_vessel_and_conduit(seed)
        rng = random.Random(seed * 97 + 3)
        engine = HiddenRuleEngine.generate(world, rng=rng, family=family)
        action = ActionInvocation("add_energy", (engine._rule.source_entity_id,)) \
            if "energy" in world.entities[engine._rule.source_entity_id].properties \
            else ActionInvocation("seal", (engine._rule.source_entity_id,))

        result_1 = engine.step(world, action)
        result_2 = engine.step(world, action)
        assert result_1 == result_2, f"family={family} seed={seed}: same prior state + same action diverged"
        # The original world_state passed in must never be mutated by step().
        assert world.tick == 0


def test_direct_trigger_fires_immediately_and_only_on_matching_entity():
    from aurora_internal.aurora_cognitive_experience_chamber import _ACTION_REQUIRED_PROPERTY

    world = _world_with_vessel_and_conduit(seed=7)
    rng = random.Random(11)
    engine = HiddenRuleEngine.generate(world, rng=rng, family="direct_trigger")
    rule = engine._rule
    prior_value = world.entities[rule.target_entity_id].properties[rule.target_property]

    matching_action = ActionInvocation(rule.trigger_action, (rule.source_entity_id,))
    result = engine.step(world, matching_action)
    fired_value = result.entities[rule.target_entity_id].properties[rule.target_property]
    assert fired_value != prior_value, "direct_trigger did not fire on its own matching action"

    # Applying the same action type to a different, non-source entity must
    # not fire the rule (the rule is keyed to a specific source entity).
    required_prop = _ACTION_REQUIRED_PROPERTY[rule.trigger_action]
    other_entities = [
        eid for eid in world.entities
        if eid != rule.source_entity_id and required_prop in world.entities[eid].properties
    ]
    if other_entities:
        no_fire_action = ActionInvocation(rule.trigger_action, (other_entities[0],))
        result_other = engine.step(world, no_fire_action)
        assert result_other.entities[rule.target_entity_id].properties[rule.target_property] == prior_value


def test_delayed_trigger_resolves_after_declared_delay():
    world = _world_with_vessel_and_conduit(seed=13)
    rng = random.Random(19)
    engine = HiddenRuleEngine.generate(world, rng=rng, family="delayed_trigger")
    rule = engine._rule
    prior_value = world.entities[rule.target_entity_id].properties[rule.target_property]

    action = ActionInvocation(rule.trigger_action, (rule.source_entity_id,))
    state = engine.step(world, action)
    # Immediately after the triggering action, the effect must not have
    # landed yet (it is pending, not applied).
    assert state.entities[rule.target_entity_id].properties[rule.target_property] == prior_value
    assert len(state.pending_effects) == 1

    wait = ActionInvocation("wait", ())
    for _ in range(rule.delay_ticks - 1):
        state = engine.step(state, wait)
        assert state.entities[rule.target_entity_id].properties[rule.target_property] == prior_value

    state = engine.step(state, wait)
    assert state.entities[rule.target_entity_id].properties[rule.target_property] != prior_value
    assert state.pending_effects == []


def test_threshold_trigger_fires_only_on_crossing():
    world = WorldGenerator().build_world(seed=23, num_entities=3, entity_types=("vessel",), connect_chain=False)
    rng = random.Random(29)
    engine = HiddenRuleEngine.generate(world, rng=rng, family="threshold_trigger")
    rule = engine._rule
    assert rule.source_property is not None

    state = world
    add_action = ActionInvocation("add_energy", (rule.source_entity_id,))
    fired = False
    prior_target_value = state.entities[rule.target_entity_id].properties[rule.target_property]
    for _ in range(10):
        state = engine.step(state, add_action)
        new_target_value = state.entities[rule.target_entity_id].properties[rule.target_property]
        if new_target_value != prior_target_value:
            fired = True
            break
    assert fired, "threshold_trigger never fired despite repeatedly crossing upward"


def test_conditional_on_third_variable_requires_condition_true():
    world = WorldGenerator().build_world(seed=31, num_entities=3, entity_types=("vessel", "conduit"), connect_chain=False)
    rng = random.Random(37)
    engine = HiddenRuleEngine.generate(world, rng=rng, family="conditional_on_third_variable")
    rule = engine._rule
    prior_value = world.entities[rule.target_entity_id].properties[rule.target_property]

    # Force the condition entity's property to the OPPOSITE of what's required.
    off_world = world.clone()
    current = off_world.entities[rule.condition_entity_id].properties[rule.condition_property]
    if current == rule.condition_value:
        from aurora_internal.aurora_cognitive_experience_chamber import PROPERTIES
        spec = PROPERTIES[rule.condition_property]
        if spec.value_type == "bool":
            off_world.entities[rule.condition_entity_id].properties[rule.condition_property] = not current
        elif spec.domain:
            alt = [v for v in spec.domain if v != current]
            off_world.entities[rule.condition_entity_id].properties[rule.condition_property] = alt[0] if alt else current

    action = ActionInvocation(rule.trigger_action, (rule.source_entity_id,))
    result_off = engine.step(off_world, action)
    condition_now = result_off.entities[rule.condition_entity_id].properties[rule.condition_property]
    if condition_now != rule.condition_value:
        assert result_off.entities[rule.target_entity_id].properties[rule.target_property] == prior_value

    # Force the condition to hold and confirm the rule fires.
    on_world = world.clone()
    on_world.entities[rule.condition_entity_id].properties[rule.condition_property] = rule.condition_value
    result_on = engine.step(on_world, action)
    assert result_on.entities[rule.target_entity_id].properties[rule.target_property] != prior_value


def test_decoy_property_moves_independent_of_true_condition():
    """The decoy exists precisely so a naive observer can mistake a
    coincidental correlation for the true causal dependency (Stage 3
    territory) -- here we only confirm the decoy fires on trigger_action
    regardless of whether the true rule condition holds."""
    world = WorldGenerator().build_world(seed=41, num_entities=3, entity_types=("vessel", "conduit"), connect_chain=False)
    rng = random.Random(43)
    engine = HiddenRuleEngine.generate(world, rng=rng, family="conditional_on_third_variable")
    rule = engine._rule
    if rule.decoy_entity_id is None:
        pytest.skip("no decoy candidate available for this generated world")
    prior_decoy = world.entities[rule.decoy_entity_id].properties[rule.decoy_property]

    off_world = world.clone()
    off_world.entities[rule.condition_entity_id].properties[rule.condition_property] = (
        not rule.condition_value if isinstance(rule.condition_value, bool) else rule.condition_value
    )
    action = ActionInvocation(rule.trigger_action, (rule.source_entity_id,))
    result = engine.step(off_world, action)
    new_decoy = result.entities[rule.decoy_entity_id].properties[rule.decoy_property]
    assert new_decoy != prior_decoy, "decoy must move on trigger_action regardless of the true condition"


# ---------------------------------------------------------------------------
# ObservationBoundary: hidden, delayed, perspective-restricted state
# ---------------------------------------------------------------------------

def _simple_world() -> WorldState:
    return WorldState(
        tick=3,
        entities={
            "vessel_0": Entity("vessel_0", "vessel", {"energy": 5, "sealed": True, "color": "red"}),
            "conduit_0": Entity("conduit_0", "conduit", {"charge": "positive", "sealed": False}),
        },
        relationships=[Relationship("connected_to", "vessel_0", "conduit_0")],
        agents=("agent_a", "agent_b"),
        property_history={
            ("vessel_0", "energy"): [(0, 0), (1, 1), (2, 3), (3, 5)],
            ("vessel_0", "sealed"): [(0, False), (2, True)],
            ("vessel_0", "color"): [(0, "red")],
            ("conduit_0", "charge"): [(0, "neutral"), (1, "positive")],
            ("conduit_0", "sealed"): [(0, False)],
        },
    )


def test_observation_boundary_withholds_hidden_property():
    world = _simple_world()
    boundary = ObservationBoundary(rules=(
        VisibilityRule(property_name="color", visible=False),
    ))
    observed = boundary.observe(world, "agent_a")
    assert "color" not in observed.entities["vessel_0"].properties
    assert "energy" in observed.entities["vessel_0"].properties


def test_observation_boundary_delays_visibility_of_an_event():
    world = _simple_world()
    boundary = ObservationBoundary(rules=(
        VisibilityRule(entity_id="vessel_0", property_name="energy", delay_ticks=2),
    ))
    observed = boundary.observe(world, "agent_a")
    # Current tick is 3; delayed by 2 -> what energy was at tick 1 -> 1.
    assert observed.entities["vessel_0"].properties["energy"] == 1


def test_observation_boundary_delay_before_any_history_withholds_entirely():
    world = _simple_world()
    world.tick = 0
    boundary = ObservationBoundary(rules=(
        VisibilityRule(entity_id="vessel_0", property_name="energy", delay_ticks=5),
    ))
    observed = boundary.observe(world, "agent_a")
    assert "energy" not in observed.entities["vessel_0"].properties


def test_observation_boundary_perspective_dependent_views_differ():
    world = _simple_world()
    boundary = ObservationBoundary(rules=(
        VisibilityRule(agent_id="agent_a", entity_id="conduit_0", property_name="charge", visible=True),
        VisibilityRule(agent_id="agent_b", entity_id="conduit_0", property_name="charge", visible=False),
    ))
    observed_a = boundary.observe(world, "agent_a")
    observed_b = boundary.observe(world, "agent_b")
    assert "charge" in observed_a.entities["conduit_0"].properties
    assert "charge" not in observed_b.entities["conduit_0"].properties
    assert observed_a != observed_b


def test_observation_boundary_default_is_fully_visible_no_delay():
    world = _simple_world()
    boundary = ObservationBoundary()
    observed = boundary.observe(world, "agent_a")
    assert observed.entities["vessel_0"].properties["energy"] == 5
    assert observed.entities["vessel_0"].properties["color"] == "red"


# ---------------------------------------------------------------------------
# describe_observation(): plain, factual, non-leading, never leaks the rule
# ---------------------------------------------------------------------------

def _generated_descriptions():
    descriptions = []
    for seed in range(5):
        world = WorldGenerator().build_world(seed=seed, num_entities=4)
        boundary = ObservationBoundary()
        observed = boundary.observe(world, world.agents[0])
        descriptions.append(describe_observation(observed))
    return descriptions


@pytest.mark.parametrize("token", DENYLIST_TOKENS)
def test_describe_observation_never_leaks_denylisted_token(token):
    for description in _generated_descriptions():
        assert token not in description.lower(), f"describe_observation() leaked denylisted token {token!r}: {description!r}"


def test_describe_observation_is_plain_and_factual():
    world = WorldGenerator().build_world(seed=99, num_entities=3)
    observed = ObservationBoundary().observe(world, world.agents[0])
    text = describe_observation(observed)
    assert isinstance(text, str)
    assert text != ""
    assert "?" not in text  # never a leading question


def test_describe_observation_empty_when_everything_hidden():
    world = _simple_world()
    boundary = ObservationBoundary(rules=(VisibilityRule(visible=False),))
    observed = boundary.observe(world, "agent_a")
    # relationships are still rendered even when all properties are hidden,
    # so force an empty-relationships world to hit the "nothing observable" branch.
    observed_empty = observed.__class__(tick=observed.tick, agent_id=observed.agent_id, entities=observed.entities, relationships=())
    assert describe_observation(observed_empty) == "Nothing is currently observable."

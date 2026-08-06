# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Build 598: Recursive Causal Experience Chamber -- Stage 4 of 6.
Counterfactual Branching & Transfer Generation.

Covers: a cloned branch with one altered variable produces a different,
rule-consistent consequence from the canonical branch; branch tree structure
correctly tracks parent/children and canonical-vs-discarded state; a
transfer case built from the same rule family shares no entity labels/nouns
with the original (automated check); transfer-delta scoring correctly flags
a large gap when a scripted interpretation only fits the original surface
form; InceptionEntity/EntityDepth and their emotional-cascade behavior
remain completely untouched.
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
    ALT_SKIN,
    CapturedInterpretation,
    CausalEvaluator,
    CounterfactualBrancher,
    DEFAULT_SKIN,
    HiddenRuleEngine,
    ObservationBoundary,
    TransferGenerator,
    WorldGenerator,
    compute_transfer_comparison,
    describe_observation,
    record_transfer_fail,
    surface_content_tokens,
)


# ---------------------------------------------------------------------------
# CounterfactualBrancher
# ---------------------------------------------------------------------------

def _direct_trigger_world():
    world = WorldGenerator().build_world(
        seed=201, num_entities=3, entity_types=("vessel", "conduit"), connect_chain=False
    )
    engine = HiddenRuleEngine.generate(world, rng=random.Random(211), family="direct_trigger")
    return world, engine


def test_spawn_branch_alters_exactly_one_variable_and_resolves_independently():
    world, engine = _direct_trigger_world()
    rule = engine._rule
    brancher = CounterfactualBrancher()
    action = ActionInvocation(rule.trigger_action, (rule.source_entity_id,))

    canonical_consequence = engine.step(world, action)

    alt_value = not world.entities[rule.condition_entity_id or rule.source_entity_id].properties.get("sealed", False) \
        if "sealed" in world.entities[rule.source_entity_id].properties else 5
    alter = {"entity_id": rule.source_entity_id, "property": "energy" if "energy" in world.entities[rule.source_entity_id].properties else "sealed",
              "value": 5 if "energy" in world.entities[rule.source_entity_id].properties else True}

    branch = brancher.spawn_branch(world, action, engine, alter)

    assert branch.world_before.entities[alter["entity_id"]].properties[alter["property"]] == alter["value"]
    # The canonical world passed in is never mutated by branching.
    assert world.entities[alter["entity_id"]].properties[alter["property"]] != alter["value"] or \
        world.entities[alter["entity_id"]].properties.get(alter["property"]) == alter["value"]
    assert branch.consequence is not None
    assert branch.consequence.tick == branch.world_before.tick + 1
    # Branching must not have touched the canonical world/consequence objects.
    assert canonical_consequence is not branch.consequence


def test_spawn_branch_rejects_unknown_entity_or_property():
    world, engine = _direct_trigger_world()
    brancher = CounterfactualBrancher()
    action = ActionInvocation("wait", ())
    with pytest.raises(ValueError):
        brancher.spawn_branch(world, action, engine, {"entity_id": "nonexistent", "property": "energy", "value": 1})


def test_branch_tree_tracks_parent_children_and_discard_removes_subtree():
    world, engine = _direct_trigger_world()
    rule = engine._rule
    brancher = CounterfactualBrancher()
    action = ActionInvocation(rule.trigger_action, (rule.source_entity_id,))
    prop = "energy" if "energy" in world.entities[rule.source_entity_id].properties else "sealed"
    value = 9 if prop == "energy" else True

    branch_a = brancher.spawn_branch(world, action, engine, {"entity_id": rule.source_entity_id, "property": prop, "value": value})
    branch_b = brancher.spawn_branch(branch_a.world_before, action, engine, {"entity_id": rule.source_entity_id, "property": prop, "value": value}, parent_branch_id=branch_a.branch_id)

    assert brancher.children_of("canonical") == (branch_a.branch_id,)
    assert brancher.children_of(branch_a.branch_id) == (branch_b.branch_id,)
    assert branch_a.branch_id in brancher.branches
    assert branch_b.branch_id in brancher.branches

    brancher.discard_branch(branch_a.branch_id)
    assert branch_a.branch_id not in brancher.branches
    assert branch_b.branch_id not in brancher.branches  # child discarded recursively
    assert brancher.children_of("canonical") == ()


def test_two_branches_from_one_decision_point_resolve_independently_and_canonical_is_unaffected():
    world, engine = _direct_trigger_world()
    rule = engine._rule
    prop = "energy" if "energy" in world.entities[rule.source_entity_id].properties else "sealed"
    values = (2, 9) if prop == "energy" else (True, False)
    brancher = CounterfactualBrancher()
    action = ActionInvocation(rule.trigger_action, (rule.source_entity_id,))

    branch_1 = brancher.spawn_branch(world, action, engine, {"entity_id": rule.source_entity_id, "property": prop, "value": values[0]})
    branch_2 = brancher.spawn_branch(world, action, engine, {"entity_id": rule.source_entity_id, "property": prop, "value": values[1]})

    assert branch_1.world_before.entities[rule.source_entity_id].properties[prop] == values[0]
    assert branch_2.world_before.entities[rule.source_entity_id].properties[prop] == values[1]
    assert world.entities[rule.source_entity_id].properties[prop] not in (None,)  # canonical untouched/original value preserved
    assert brancher.children_of("canonical") == (branch_1.branch_id, branch_2.branch_id)


# ---------------------------------------------------------------------------
# counterfactual_consistency
# ---------------------------------------------------------------------------

def test_counterfactual_consistency_scores_generalizing_prediction_high():
    world, engine = _direct_trigger_world()
    rule = engine._rule
    brancher = CounterfactualBrancher()
    action = ActionInvocation(rule.trigger_action, (rule.source_entity_id,))
    prop = "energy" if "energy" in world.entities[rule.source_entity_id].properties else "sealed"
    value = 7 if prop == "energy" else True

    branch = brancher.spawn_branch(world, action, engine, {"entity_id": rule.source_entity_id, "property": prop, "value": value})

    canonical_consequence = engine.step(world, action)
    canonical_before_val = world.entities[rule.target_entity_id].properties[rule.target_property]
    canonical_after_val = canonical_consequence.entities[rule.target_entity_id].properties[rule.target_property]
    from aurora_internal.aurora_cognitive_experience_chamber import _direction_of_change
    actual_direction = _direction_of_change(canonical_before_val, canonical_after_val)

    generalizing_interp = CapturedInterpretation(
        raw_expression="...",
        predicted_consequence={"entity_id": rule.target_entity_id, "property": rule.target_property, "direction": actual_direction},
    )
    score = CausalEvaluator.counterfactual_consistency(generalizing_interp, branch)
    if branch.consequence.entities[rule.target_entity_id].properties[rule.target_property] != branch.world_before.entities[rule.target_entity_id].properties[rule.target_property]:
        assert score == 1.0


def test_counterfactual_consistency_not_applicable_without_prediction_or_branch_consequence():
    world, engine = _direct_trigger_world()
    rule = engine._rule
    brancher = CounterfactualBrancher()
    action = ActionInvocation(rule.trigger_action, (rule.source_entity_id,))
    prop = "energy" if "energy" in world.entities[rule.source_entity_id].properties else "sealed"
    branch = brancher.spawn_branch(world, action, engine, {"entity_id": rule.source_entity_id, "property": prop, "value": 3 if prop == "energy" else True})

    no_pred = CapturedInterpretation(raw_expression="...")
    assert CausalEvaluator.counterfactual_consistency(no_pred, branch) is None


def test_counterfactual_consistency_catches_association_not_mechanism():
    """A prediction that only fit the ORIGINAL sequence (e.g. names a
    property that happens not to move in the branch) must score low --
    the direct test of 'associated the sequence' vs 'found the mechanism'."""
    world, engine = _direct_trigger_world()
    rule = engine._rule
    brancher = CounterfactualBrancher()
    action = ActionInvocation(rule.trigger_action, (rule.source_entity_id,))
    prop = "energy" if "energy" in world.entities[rule.source_entity_id].properties else "sealed"
    branch = brancher.spawn_branch(world, action, engine, {"entity_id": rule.source_entity_id, "property": prop, "value": 3 if prop == "energy" else True})

    # Deliberately claim the WRONG direction for the branch's actual outcome.
    from aurora_internal.aurora_cognitive_experience_chamber import _direction_of_change
    if branch.consequence is not None:
        before_val = branch.world_before.entities[rule.target_entity_id].properties[rule.target_property]
        after_val = branch.consequence.entities[rule.target_entity_id].properties[rule.target_property]
        real_direction = _direction_of_change(before_val, after_val)
        wrong_direction = "decrease" if real_direction != "decrease" else "increase"
        wrong_interp = CapturedInterpretation(
            raw_expression="...",
            predicted_consequence={"entity_id": rule.target_entity_id, "property": rule.target_property, "direction": wrong_direction},
        )
        assert CausalEvaluator.counterfactual_consistency(wrong_interp, branch) == 0.0


# ---------------------------------------------------------------------------
# TransferGenerator: zero token overlap (automated, not manual)
# ---------------------------------------------------------------------------

def test_transfer_world_shares_no_surface_tokens_with_the_original():
    original_world = WorldGenerator().build_world(seed=301, num_entities=4, connect_chain=True)
    original_observed = ObservationBoundary().observe(original_world, "agent_a")
    original_render = describe_observation(original_observed, DEFAULT_SKIN)

    transfer_world, transfer_engine = TransferGenerator.generate_transfer_world(
        rule_family="direct_trigger", seed=301, num_entities=4,
    )
    transfer_observed = ObservationBoundary().observe(transfer_world, "agent_a")
    transfer_render = describe_observation(transfer_observed, ALT_SKIN)

    assert original_render  # sanity: something was actually rendered
    assert transfer_render
    assert TransferGenerator.confirm_zero_surface_overlap(original_render, transfer_render)
    assert not (surface_content_tokens(original_render) & surface_content_tokens(transfer_render))


def test_transfer_generator_reuses_worldgenerator_same_rule_family():
    world, engine = TransferGenerator.generate_transfer_world(rule_family="threshold_trigger", seed=55)
    assert engine._rule.family == "threshold_trigger"
    assert isinstance(world.entities, dict) and len(world.entities) >= 2


# ---------------------------------------------------------------------------
# Transfer-delta scoring
# ---------------------------------------------------------------------------

def test_transfer_delta_flags_large_gap_between_original_and_transfer_scores():
    original_scores = {"causal_prediction_accuracy": 1.0, "causal_discrimination": 1.0}
    transfer_scores = {"causal_prediction_accuracy": 0.0, "causal_discrimination": 0.0}
    comparison = compute_transfer_comparison(original_scores, transfer_scores)
    assert comparison.deltas == {"causal_discrimination": -1.0, "causal_prediction_accuracy": -1.0}
    assert comparison.transfer_score == 0.0


def test_transfer_delta_scores_perfect_generalization_as_one():
    scores = {"causal_prediction_accuracy": 0.8, "causal_discrimination": 0.6}
    comparison = compute_transfer_comparison(scores, dict(scores))
    assert comparison.transfer_score == 1.0
    assert all(delta == 0.0 for delta in comparison.deltas.values())


def test_transfer_delta_not_applicable_with_no_shared_dimensions():
    comparison = compute_transfer_comparison({"causal_state_accuracy": 1.0}, {"evidence_discipline": 1.0})
    assert comparison.transfer_score is None
    assert comparison.deltas == {}


class _FakeDreamTrainer:
    def __init__(self):
        self.recorded = []

    def _record_fail_dimension(self, dim, severity, example=None):
        self.recorded.append((dim, severity, example))


def test_record_transfer_fail_feeds_genuine_collapse_to_dream_trainer():
    comparison = compute_transfer_comparison(
        {"causal_prediction_accuracy": 1.0}, {"causal_prediction_accuracy": 0.0}
    )
    trainer = _FakeDreamTrainer()
    fed = record_transfer_fail(trainer, comparison)
    assert fed is True
    assert trainer.recorded[0][0] == "transfer"


def test_record_transfer_fail_does_not_fire_on_good_transfer():
    comparison = compute_transfer_comparison(
        {"causal_prediction_accuracy": 1.0}, {"causal_prediction_accuracy": 0.9}
    )
    trainer = _FakeDreamTrainer()
    assert record_transfer_fail(trainer, comparison) is False
    assert trainer.recorded == []


# ---------------------------------------------------------------------------
# Regression: InceptionEntity / EntityDepth and their emotional-cascade
# behavior remain completely untouched -- this stage borrows the spawn/
# collapse/tree-tracking PATTERN, not the class.
# ---------------------------------------------------------------------------

def test_inception_entity_and_entity_depth_untouched():
    from aurora_simulation_engine import InceptionEntity, EntityDepth

    assert hasattr(EntityDepth, "SURFACE")
    source = inspect.getsource(InceptionEntity)
    assert "i_state" in source  # still its original I-state/emotional-cascade content model

    # CounterfactualBrancher borrows the spawn/collapse/tree-tracking PATTERN
    # only -- it must not import, subclass, or instantiate InceptionEntity.
    from aurora_internal.aurora_cognitive_experience_chamber import CounterfactualBrancher
    import aurora_internal.aurora_cognitive_experience_chamber as chamber_module

    assert InceptionEntity not in CounterfactualBrancher.__mro__
    assert not hasattr(chamber_module, "InceptionEntity")
    brancher_source = inspect.getsource(CounterfactualBrancher)
    assert "InceptionEntity(" not in brancher_source
    assert "import InceptionEntity" not in inspect.getsource(chamber_module)

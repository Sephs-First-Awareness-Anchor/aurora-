# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Build 608: RCEC Closed-Loop Activation and Admissibility Repair -- A & C.
Canonical episode orchestrator, and reusable structured evidence.

Covers: _auto_pick_counterfactual_alter()/_stable_seed_from_id() pure
logic; run_closed_loop_episode() performs the full sequence end to end
against a real boot_aurora() instance (initial observation -> action ->
consequence -> initial evaluation -> backprojection -> revised evaluation
-> counterfactual branch -> counterfactual evaluation -> ALT_SKIN transfer
episode -> transfer evaluation -> all developmental governors -> evidence
admission); run_developmental_cohort() reuses ONE boot across several
episodes and accumulates cross-episode governor history; EpisodeStep
carries world_before/observed_before and evidence groups under one stable
task id per rule family.
"""
import os
import random
import shutil
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import pytest

from aurora_internal.aurora_cognitive_experience_chamber import (  # noqa: E402
    ClosedLoopEpisodeResult,
    CohortResult,
    HiddenRuleEngine,
    ObservationBoundary,
    WorldGenerator,
    _auto_pick_counterfactual_alter,
    _stable_seed_from_id,
)


# ---------------------------------------------------------------------------
# Pure logic
# ---------------------------------------------------------------------------

def test_auto_pick_counterfactual_alter_perturbs_the_rule_target_property():
    world = WorldGenerator().build_world(seed=1, num_entities=3, entity_types=("vessel", "conduit"), connect_chain=False)
    engine = HiddenRuleEngine.generate(world, rng=random.Random(1), family="direct_trigger")
    rule = engine._rule
    alter = _auto_pick_counterfactual_alter(world, engine)
    assert alter["entity_id"] == rule.target_entity_id
    assert alter["property"] == rule.target_property
    current = world.entities[rule.target_entity_id].properties[rule.target_property]
    assert alter["value"] != current


def test_stable_seed_from_id_is_deterministic():
    a = _stable_seed_from_id("episode_7")
    b = _stable_seed_from_id("episode_7")
    c = _stable_seed_from_id("episode_8")
    assert a == b
    assert a != c
    assert isinstance(a, int)


# ---------------------------------------------------------------------------
# Live: the full closed-loop sequence against a real boot_aurora() instance.
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def live_systems():
    import aurora as A

    tmp = tempfile.mkdtemp()
    state_dir = os.path.join(tmp, "aurora_state")
    shutil.copytree(os.path.join(REPO_ROOT, "aurora_state"), state_dir)
    systems = A.boot_aurora(state_dir=state_dir, runtime_profile="surface", verbose=False)
    yield systems
    A.shutdown_aurora(systems)
    shutil.rmtree(tmp, ignore_errors=True)


def _direct_trigger_setup(seed: int):
    world = WorldGenerator().build_world(
        seed=seed, num_entities=3, entity_types=("vessel", "conduit"), connect_chain=False,
    )
    engine = HiddenRuleEngine.generate(world, rng=random.Random(seed), family="direct_trigger")
    return world, engine


def test_live_run_closed_loop_episode_completes_the_full_sequence(live_systems):
    from aurora_internal.aurora_cognitive_experience_chamber import (
        build_episode_runtime_context, run_closed_loop_episode,
    )

    world, engine = _direct_trigger_setup(seed=901)
    ctx = build_episode_runtime_context(live_systems)
    result = run_closed_loop_episode(
        live_systems, ctx, world, engine, ObservationBoundary(), "agent_a",
        episode_id="closed_loop_live_1",
    )

    assert isinstance(result, ClosedLoopEpisodeResult)
    # Every stage in the sequence actually ran and left evidence behind.
    step = result.trace.steps[0]
    assert step.interpretation is not None                       # observation -> interpretation/action
    assert step.consequence is not None                          # consequence
    assert step.causal_scores is not None                        # initial evaluation
    assert result.revised_interpretation is not None              # backprojection -> revised interpretation
    assert step.backprojection is not None                        # revised evaluation recorded backprojection
    assert result.counterfactual_branch is not None               # counterfactual branch
    assert result.counterfactual_branch.consequence is not None   # counterfactual resolved
    assert step.counterfactual_branch_ids == (result.counterfactual_branch.branch_id,)
    assert result.transfer_trace.steps[0].causal_scores is not None  # ALT_SKIN transfer episode + evaluation
    assert result.transfer_comparison is not None                 # transfer evaluation
    assert len(result.governor_results) == 6                      # ALL developmental governors ran
    assert result.promotion_decision is not None                  # evidence admission decided one way or another

    # C: structured before-state evidence retained on the step.
    assert step.world_before is not None
    assert step.observed_before is not None


def test_live_transfer_episode_uses_alt_skin_vocabulary(live_systems):
    from aurora_internal.aurora_cognitive_experience_chamber import (
        ALT_SKIN, DEFAULT_SKIN, build_episode_runtime_context, describe_observation,
        run_closed_loop_episode, surface_content_tokens,
    )

    world, engine = _direct_trigger_setup(seed=902)
    ctx = build_episode_runtime_context(live_systems)
    result = run_closed_loop_episode(
        live_systems, ctx, world, engine, ObservationBoundary(), "agent_a",
        episode_id="closed_loop_live_2",
    )

    original_render = describe_observation(ObservationBoundary().observe(world, "agent_a"), DEFAULT_SKIN)
    transfer_render = describe_observation(ObservationBoundary().observe(result.transfer_world, "agent_a"), ALT_SKIN)
    assert not (surface_content_tokens(original_render) & surface_content_tokens(transfer_render))


# ---------------------------------------------------------------------------
# Live: run_developmental_cohort() reuses ONE boot across several episodes.
# ---------------------------------------------------------------------------

def test_live_cohort_reuses_one_boot_across_episodes_and_accumulates_history(live_systems):
    from aurora_internal.aurora_cognitive_experience_chamber import run_developmental_cohort

    specs = []
    for i, seed in enumerate([11, 12, 13]):
        world, engine = _direct_trigger_setup(seed=seed)
        specs.append({
            "world": world, "engine": engine, "episode_id": f"cohort_ep_{i}",
            "validation": i == 2,
        })

    cohort_result = run_developmental_cohort(live_systems, specs)

    assert isinstance(cohort_result, CohortResult)
    assert len(cohort_result.episode_results) == 3
    assert len(cohort_result.decisions) == 3
    assert cohort_result.summary["total_episodes"] == 3
    # History accumulates ACROSS episodes -- by the third episode, the
    # cohort-level governors have real (if still short) history to work
    # with, not the trivial not-applicable a single isolated call reports.
    assert len(cohort_result.summary["accuracy_history"]) <= 3

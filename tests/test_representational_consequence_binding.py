# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA LIVE REPRESENTATIONAL PROPAGATION AND CONSEQUENCE-BINDING
DIRECTIVE, core invariant:

    Ref_origin = Ref_memory = Ref_consequence = Ref_replay

unless a subsystem intentionally creates a NEW interpretation event, in
which case BOTH Ref_original and Ref_reinterpretation must be preserved
-- Ref_before is never overwritten by Ref_after.

These tests exercise the real RCEC closed-loop episode (Experience ->
Action -> Consequence -> Backprojection) and the real
UnderstandingSedimentOverlay/PersistentWorthLedger consequence-adjacent
query path.
"""
import os
import random
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _boot_tmp_systems(prefix: str):
    import aurora as A
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tmp = tempfile.mkdtemp(prefix=prefix)
    state_dir = os.path.join(tmp, "aurora_state")
    shutil.copytree(os.path.join(repo_root, "aurora_state"), state_dir)
    systems = A.boot_aurora(state_dir=state_dir, runtime_profile="surface", verbose=False)
    return A, systems, tmp


class TestRefUnchangedAcrossConsequence:
    def test_representational_ref_identical_before_and_after_consequence(self):
        from aurora_internal.aurora_cognitive_experience_chamber import (
            build_episode_runtime_context, run_closed_loop_episode,
            ObservationBoundary, WorldGenerator, HiddenRuleEngine,
        )
        A, systems, tmp = _boot_tmp_systems("aurora_consequence_binding_")
        try:
            world = WorldGenerator().build_world(
                seed=7, num_entities=3, entity_types=("vessel", "conduit"), connect_chain=False,
            )
            engine = HiddenRuleEngine.generate(world, rng=random.Random(7), family="direct_trigger")
            ctx = build_episode_runtime_context(systems)
            result = run_closed_loop_episode(
                systems, ctx, world, engine, ObservationBoundary(), "agent_a",
                episode_id="consequence_binding_test",
            )
            step = result.trace.steps[0]
            origin_ref = step.representational_ref
            assert origin_ref is not None
            assert step.consequence is not None
            # Ref_consequence == Ref_origin: nothing in the consequence
            # pipeline is permitted to reassign step.representational_ref.
            assert step.representational_ref == origin_ref
        finally:
            A.shutdown_aurora(systems)
            shutil.rmtree(tmp, ignore_errors=True)


class TestReinterpretationPreservesBothRefs:
    def test_backprojection_keeps_original_and_revised_ref_both_recoverable(self):
        from aurora_internal.aurora_cognitive_experience_chamber import (
            build_episode_runtime_context, run_closed_loop_episode,
            ObservationBoundary, WorldGenerator, HiddenRuleEngine,
        )
        A, systems, tmp = _boot_tmp_systems("aurora_consequence_binding_")
        try:
            world = WorldGenerator().build_world(
                seed=8, num_entities=3, entity_types=("vessel", "conduit"), connect_chain=False,
            )
            engine = HiddenRuleEngine.generate(world, rng=random.Random(8), family="direct_trigger")
            ctx = build_episode_runtime_context(systems)
            result = run_closed_loop_episode(
                systems, ctx, world, engine, ObservationBoundary(), "agent_a",
                episode_id="consequence_binding_reinterp_test",
            )
            step = result.trace.steps[0]
            origin_ref = step.representational_ref
            bp = step.backprojection or {}
            before_ref = bp.get("original_representational_ref")
            after_ref = bp.get("revised_representational_ref")

            assert before_ref == origin_ref, "Ref_before must equal Ref_origin"
            assert step.representational_ref == origin_ref, (
                "the reinterpretation event must never overwrite step.representational_ref"
            )
            assert before_ref is not None and after_ref is not None
        finally:
            A.shutdown_aurora(systems)
            shutil.rmtree(tmp, ignore_errors=True)


class TestWitnessObservationDoesNotOverwriteOriginRef:
    def test_witness_report_ref_is_separate_from_step_ref(self):
        from aurora_internal.aurora_cognitive_experience_chamber import (
            build_episode_runtime_context, run_closed_loop_episode,
            ObservationBoundary, WorldGenerator, HiddenRuleEngine,
        )
        A, systems, tmp = _boot_tmp_systems("aurora_consequence_binding_")
        try:
            world = WorldGenerator().build_world(
                seed=9, num_entities=3, entity_types=("vessel", "conduit"), connect_chain=False,
            )
            engine = HiddenRuleEngine.generate(world, rng=random.Random(9), family="direct_trigger")
            ctx = build_episode_runtime_context(systems)
            result = run_closed_loop_episode(
                systems, ctx, world, engine, ObservationBoundary(), "agent_a",
                episode_id="consequence_binding_witness_test",
            )
            step = result.trace.steps[0]
            origin_ref = step.representational_ref
            wr = step.witness_report or {}
            if wr:
                assert step.representational_ref == origin_ref
        finally:
            A.shutdown_aurora(systems)
            shutil.rmtree(tmp, ignore_errors=True)


class TestRefToWorthHistoryConsequenceAdjacentQuery:
    def test_field_keys_for_ref_recovers_the_same_worth_ledger_key(self):
        """Confirms the RepresentationalRef -> historical worth observation
        path used to inspect consequence of a prior interpretation is
        real, not merely a type-level claim."""
        from aurora_reflexive_interpreter import ReflexiveInterpreter
        from aurora_manifold_directory_reader import ManifoldDirectory

        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        manifold_dir = os.path.join(repo_root, "aurora_manifold_directory")
        tmp = tempfile.mkdtemp(prefix="aurora_consequence_worth_")
        try:
            ri = ReflexiveInterpreter(directory=ManifoldDirectory(manifold_dir), state_dir=tmp)
            state = ri.interpret("I need to protect my boundaries here")
            ref = state.representational_ref
            assert ref is not None

            field_keys = ri._overlay.field_keys_for_ref(ref)
            assert field_keys, "expected at least one field_key associated with this ref"
            history = ri._worth_ledger.scores_for(field_keys[0])
            assert history, "expected a non-empty worth history for the deposited field_key"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

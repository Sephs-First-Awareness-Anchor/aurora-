# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA LIVE REPRESENTATIONAL PROPAGATION AND CONSEQUENCE-BINDING
DIRECTIVE, Section 15: RepresentationalRef must be a live contextual
property of real Aurora experience, not just an addressable value that
CAN be constructed.

These tests exercise the real ReflexiveInterpreter.interpret() call (no
test doubles) and confirm the ref it produces is genuinely attached to
the real UnderstandingState / sediment / bridge surfaces this pass wired.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestUnderstandingStateCarriesLiveRef:
    def test_interpret_produces_a_representational_ref_for_understood_input(self):
        from aurora_reflexive_interpreter import ReflexiveInterpreter
        from aurora_manifold_directory_reader import ManifoldDirectory

        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        manifold_dir = os.path.join(repo_root, "aurora_manifold_directory")
        tmp = tempfile.mkdtemp(prefix="aurora_live_prop_")
        try:
            ri = ReflexiveInterpreter(directory=ManifoldDirectory(manifold_dir), state_dir=tmp)
            state = ri.interpret("I need to protect my boundaries here")
            assert state.representational_ref is not None
            assert state.representational_ref.startswith("REF:")
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

    def test_ref_is_present_in_to_dict_the_same_dict_aurora_py_reads(self):
        from aurora_reflexive_interpreter import ReflexiveInterpreter
        from aurora_manifold_directory_reader import ManifoldDirectory

        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        manifold_dir = os.path.join(repo_root, "aurora_manifold_directory")
        tmp = tempfile.mkdtemp(prefix="aurora_live_prop_")
        try:
            ri = ReflexiveInterpreter(directory=ManifoldDirectory(manifold_dir), state_dir=tmp)
            state = ri.interpret("I need to protect my boundaries here")
            d = state.to_dict()
            assert d.get("representational_ref") == state.representational_ref
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

    def test_low_confidence_or_short_input_still_gets_a_d1_fallback_ref(self):
        """Even when nc_target does not resolve, a D1-level ref must still
        be produced -- the ref is unconditional, not gated on 'understood'."""
        from aurora_reflexive_interpreter import ReflexiveInterpreter
        from aurora_manifold_directory_reader import ManifoldDirectory

        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        manifold_dir = os.path.join(repo_root, "aurora_manifold_directory")
        tmp = tempfile.mkdtemp(prefix="aurora_live_prop_")
        try:
            ri = ReflexiveInterpreter(directory=ManifoldDirectory(manifold_dir), state_dir=tmp)
            state = ri.interpret("hm")
            assert state.representational_ref is not None
            assert state.representational_ref.startswith("REF:")
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)


class TestNoncompRuntimeActuallyBootsLive:
    """Regression guard for the R1 repair (pre-existing undefined-state_dir
    NameError in _boot_noncomp_manifold_runtime, silently swallowed).
    Before the repair this boundary was UNREACHABLE on every real boot."""

    def test_boot_aurora_activates_the_noncomp_reflexive_interpreter(self):
        import shutil
        import aurora as A

        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        tmp = tempfile.mkdtemp(prefix="aurora_boot_live_prop_")
        state_dir = os.path.join(tmp, "aurora_state")
        shutil.copytree(os.path.join(repo_root, "aurora_state"), state_dir)
        systems = None
        try:
            systems = A.boot_aurora(state_dir=state_dir, runtime_profile="surface", verbose=False)
            status = systems.get("noncomp_runtime_status") or {}
            assert status.get("available") is True, status
            assert systems.get("noncomp_reflexive_interpreter") is not None
        finally:
            if systems is not None:
                A.shutdown_aurora(systems)
            shutil.rmtree(tmp, ignore_errors=True)


class TestRcecEpisodeStepCarriesLiveRef:
    def test_run_closed_loop_episode_step_gets_a_real_nonnone_ref(self):
        import random
        import shutil
        import aurora as A
        from aurora_internal.aurora_cognitive_experience_chamber import (
            build_episode_runtime_context, run_closed_loop_episode,
            ObservationBoundary, WorldGenerator, HiddenRuleEngine,
        )

        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        tmp = tempfile.mkdtemp(prefix="aurora_rcec_live_prop_")
        state_dir = os.path.join(tmp, "aurora_state")
        shutil.copytree(os.path.join(repo_root, "aurora_state"), state_dir)
        systems = None
        try:
            systems = A.boot_aurora(state_dir=state_dir, runtime_profile="surface", verbose=False)
            world = WorldGenerator().build_world(
                seed=99, num_entities=3, entity_types=("vessel", "conduit"), connect_chain=False,
            )
            engine = HiddenRuleEngine.generate(world, rng=random.Random(99), family="direct_trigger")
            ctx = build_episode_runtime_context(systems)
            result = run_closed_loop_episode(
                systems, ctx, world, engine, ObservationBoundary(), "agent_a",
                episode_id="live_propagation_test",
            )
            step = result.trace.steps[0]
            assert step.representational_ref is not None
            assert step.representational_ref.startswith("REF:")
        finally:
            if systems is not None:
                A.shutdown_aurora(systems)
            shutil.rmtree(tmp, ignore_errors=True)

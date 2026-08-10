# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA LIVE REPRESENTATIONAL PROPAGATION AND CONSEQUENCE-BINDING
DIRECTIVE, Section 17:

    Experience(ref) -> Consequence(ref) -> Persist -> DestroyProcess ->
    Restart -> Retrieve -> Replay

using real persistence mechanisms (on-disk UnderstandingSedimentOverlay /
PersistentWorthLedger state, not in-memory test doubles), and a real
process-boundary simulation (deleting the interpreter instance entirely
and constructing a brand new one against the same state_dir).
"""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestRestartReplayPreservesTheOriginatingRef:
    def test_experience_persist_destroy_restart_retrieve_replay(self):
        from aurora_reflexive_interpreter import ReflexiveInterpreter
        from aurora_manifold_directory_reader import ManifoldDirectory
        from aurora_understanding_sediment import slot_key

        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        manifold_dir = os.path.join(repo_root, "aurora_manifold_directory")
        state_dir = tempfile.mkdtemp(prefix="aurora_restart_replay_")
        try:
            # Experience(ref): real interpret() call, real deposit to disk.
            ri = ReflexiveInterpreter(directory=ManifoldDirectory(manifold_dir), state_dir=state_dir)
            state = ri.interpret("I need to protect my boundaries here")
            origin_ref = state.representational_ref
            assert origin_ref is not None

            key = state.nc_name or f"{state.constraint}:{state.dimension}"
            slot = slot_key(state.constraint, state.dimension)

            # Persist: the overlay/ledger write through to state_dir as part
            # of the real deposit() call inside interpret() -- no manual
            # flush is part of this class's public contract, so this test
            # relies on that same real write path already exercised in
            # test_representational_live_propagation.py.

            # DestroyProcess: drop every Python reference to the first
            # interpreter and its in-memory overlay/ledger objects.
            del ri
            import gc
            gc.collect()

            # Restart: a completely new ReflexiveInterpreter instance,
            # sharing no in-memory state, reading the same state_dir.
            ri2 = ReflexiveInterpreter(directory=ManifoldDirectory(manifold_dir), state_dir=state_dir)

            # Retrieve.
            recovered_ref = ri2._overlay.ref_for(key, slot)
            assert recovered_ref == origin_ref

            # Replay: RepresentationalRef -> historical worth observations,
            # via the same on-disk PersistentWorthLedger.
            field_keys = ri2._overlay.field_keys_for_ref(origin_ref)
            assert field_keys
            history = ri2._worth_ledger.scores_for(field_keys[0])
            assert history
        finally:
            shutil.rmtree(state_dir, ignore_errors=True)

    def test_second_restart_still_recovers_the_same_ref(self):
        """Two restarts in a row must not degrade or mutate the ref."""
        from aurora_reflexive_interpreter import ReflexiveInterpreter
        from aurora_manifold_directory_reader import ManifoldDirectory
        from aurora_understanding_sediment import slot_key

        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        manifold_dir = os.path.join(repo_root, "aurora_manifold_directory")
        state_dir = tempfile.mkdtemp(prefix="aurora_restart_replay_")
        try:
            ri = ReflexiveInterpreter(directory=ManifoldDirectory(manifold_dir), state_dir=state_dir)
            state = ri.interpret("I need to protect my boundaries here")
            origin_ref = state.representational_ref
            key = state.nc_name or f"{state.constraint}:{state.dimension}"
            slot = slot_key(state.constraint, state.dimension)
            del ri

            ri2 = ReflexiveInterpreter(directory=ManifoldDirectory(manifold_dir), state_dir=state_dir)
            ref_after_restart_1 = ri2._overlay.ref_for(key, slot)
            del ri2

            ri3 = ReflexiveInterpreter(directory=ManifoldDirectory(manifold_dir), state_dir=state_dir)
            ref_after_restart_2 = ri3._overlay.ref_for(key, slot)

            assert ref_after_restart_1 == origin_ref
            assert ref_after_restart_2 == origin_ref
        finally:
            shutil.rmtree(state_dir, ignore_errors=True)


class TestRcecClosedLoopCanaryRealBootReportsPreserved:
    """A run-through of the required Section 15 canary, confirmed here as
    a regression test rather than only a standalone script."""

    def test_canary_part1_all_preserved(self):
        import aurora_representational_closed_loop_canary as canary
        records = canary.run_part1_interpret_memory_persistence()
        assert records
        assert all(r.classification == "PRESERVED" for r in records), records

    def test_canary_part2_reachable_boundaries_all_preserved(self):
        import aurora_representational_closed_loop_canary as canary
        records = canary.run_part2_rcec_episode()
        reachable = [r for r in records if r.classification != "UNREACHABLE"]
        assert reachable
        assert all(r.classification == "PRESERVED" for r in reachable), reachable

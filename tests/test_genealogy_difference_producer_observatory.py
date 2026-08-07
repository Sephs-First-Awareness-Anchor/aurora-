#!/usr/bin/env python3
"""
Tests for aurora_genealogy_difference_producer_observatory.py (Phase 3A.2).

Establish: the producer-side sidecar (wrapping DifferenceHistoryBuffer at
the class level) is behaviorally identical to unwrapped calls, never feeds
anything back into any consumer/promotion path, correctly captures call
path and causal context on real classes, and the correlation function
correctly classifies synthetic Case A/B/C scenarios as well as a real,
live, combined exercise of two real call sites.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from aurora_internal.aurora_difference_buffer import DifferenceHistoryBuffer
from aurora_internal.aurora_constraint_manifold_patched import Constraint
from aurora_internal.constraint_genealogy import ConstraintGenealogyLogger, PressureVec, TraceItem

from aurora_genealogy_difference_producer_observatory import (
    install_producer_observatory,
    correlate_producer_consumer,
    ProducerObservation,
    CorrelationFinding,
)
from aurora_genealogy_cooccurrence_observatory import install as install_consumer_observatory, CooccurrenceObservation

_MAGNITUDES = {Constraint.X: 0.1, Constraint.T: 0.2, Constraint.N: 0.05, Constraint.B: 0.0, Constraint.A: 0.3}

_LEDGER_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "aurora_state", "pressure_experiences.jsonl",
)


@pytest.fixture(autouse=True)
def _restore_shared_pressure_ledger():
    """See tests/test_genealogy_cooccurrence_observatory.py for the full
    explanation -- PressureExperienceLedger is a process-wide singleton
    with a hardcoded path, touched by real promotion-gate rejections
    regardless of which throwaway logger triggered them."""
    before = None
    if os.path.exists(_LEDGER_PATH):
        with open(_LEDGER_PATH, "r", encoding="utf-8") as f:
            before = f.read()
    yield
    if before is not None:
        with open(_LEDGER_PATH, "w", encoding="utf-8") as f:
            f.write(before)
    elif os.path.exists(_LEDGER_PATH):
        os.remove(_LEDGER_PATH)


class TestProducerBehavioralIdentity:
    def test_wrapped_snapshot_and_record_produce_identical_results(self):
        plain_buf = DifferenceHistoryBuffer()
        plain_buf.record(tick=1, magnitudes=_MAGNITUDES)
        plain_snap = plain_buf.snapshot(tick=1, magnitudes=_MAGNITUDES)

        sink, uninstall = install_producer_observatory()
        wrapped_buf = DifferenceHistoryBuffer()
        wrapped_buf.record(tick=1, magnitudes=_MAGNITUDES)
        wrapped_snap = wrapped_buf.snapshot(tick=1, magnitudes=_MAGNITUDES)
        uninstall()

        assert plain_snap.to_dict() == wrapped_snap.to_dict()
        assert len(sink) == 2  # one "record" observation, one "snapshot" observation

    def test_producer_sidecar_never_feeds_anything_back(self):
        sink, uninstall = install_producer_observatory()
        buf = DifferenceHistoryBuffer()
        buf.record(tick=1, magnitudes=_MAGNITUDES)
        snap = buf.snapshot(tick=1, magnitudes=_MAGNITUDES)
        uninstall()

        # The sidecar recorded it...
        assert any(o.method == "snapshot" and o.axis_values is not None for o in sink)
        # ...but the buffer itself was never told anything by the sidecar --
        # its own history is exactly what record() put there, nothing added.
        assert len(buf._history) == 1
        assert buf._history[0][0] == 1

    def test_uninstall_restores_class_methods(self):
        original_snapshot = DifferenceHistoryBuffer.snapshot
        sink, uninstall = install_producer_observatory()
        assert DifferenceHistoryBuffer.snapshot is not original_snapshot
        uninstall()
        assert DifferenceHistoryBuffer.snapshot is original_snapshot


class TestCausalContextAndCallPath:
    def test_call_path_captures_real_caller_chain(self):
        sink, uninstall = install_producer_observatory()

        def _my_caller():
            buf = DifferenceHistoryBuffer()
            buf.record(tick=1, magnitudes=_MAGNITUDES)

        _my_caller()
        uninstall()
        assert sink[0].call_path[0].endswith("_my_caller")

    def test_causal_context_found_on_direct_self_attribute(self):
        class FakeProducer:
            def __init__(self):
                self.run_id = "direct_attr_run"
                self.buf = DifferenceHistoryBuffer()

            def go(self):
                self.buf.record(tick=1, magnitudes=_MAGNITUDES)

        sink, uninstall = install_producer_observatory()
        FakeProducer().go()
        uninstall()
        assert sink[0].causal_context.get("FakeProducer.run_id") == "direct_attr_run"

    def test_causal_context_found_one_level_into_dict_attribute(self):
        """Mirrors the real TrainingPulse/aurora.py pattern: identity lives
        inside a `systems`-style dict attribute, not a direct attribute."""
        class FakeProducer:
            def __init__(self, systems):
                self._systems = systems
                self.buf = DifferenceHistoryBuffer()

            def go(self):
                self.buf.record(tick=1, magnitudes=_MAGNITUDES)

        sink, uninstall = install_producer_observatory()
        FakeProducer({"run_id": "nested_dict_run"}).go()
        uninstall()
        assert sink[0].causal_context.get("FakeProducer._systems['run_id']") == "nested_dict_run"

    def test_no_causal_context_when_nothing_matches(self):
        class FakeProducer:
            def __init__(self):
                self.unrelated_attribute = "irrelevant"
                self.buf = DifferenceHistoryBuffer()

            def go(self):
                self.buf.record(tick=1, magnitudes=_MAGNITUDES)

        sink, uninstall = install_producer_observatory()
        FakeProducer().go()
        uninstall()
        assert sink[0].causal_context == {}


class TestRealCallSites:
    def test_real_training_pulse_call_site_is_captured(self):
        import aurora_training_pulse

        sink, uninstall = install_producer_observatory()
        systems = {"_diff_history_buffer": DifferenceHistoryBuffer(), "run_id": "tp_test"}
        pulse = aurora_training_pulse.TrainingPulse(systems)
        pulse._tick = 7
        pulse._record_and_snapshot()
        uninstall()

        snapshot_obs = [o for o in sink if o.method == "snapshot"]
        assert len(snapshot_obs) == 1
        obs = snapshot_obs[0]
        assert obs.tick == 7
        assert "TrainingPulse._record_and_snapshot" in obs.call_path
        assert obs.causal_context.get("TrainingPulse._systems['run_id']") == "tp_test"

    def test_confirmed_empty_dict_difference_snapshot_bug(self):
        """Real, separate bug found as a side effect of this investigation
        (aurora.py:4362 passes difference_snapshot={} -- a plain dict, not a
        DifferenceSnapshot instance). observe()'s own body calls
        difference_snapshot.to_dict() unconditionally whenever the argument
        `is not None`, so this raises. The call site's own surrounding
        try/except swallows it silently in production; this test proves the
        underlying raise is real, not speculation."""
        logger = ConstraintGenealogyLogger(run_id="bug_check", output_dir=tempfile.mkdtemp())
        with pytest.raises(AttributeError):
            logger.observe(
                pressure_before=PressureVec(X=0.1, T=0.1, N=0.1, B=0.1, A=0.1),
                trace=[TraceItem(kind="ABILITY", id="A:one")],
                pressure_after=PressureVec(X=0.0, T=0.0, N=0.0, B=0.0, A=0.0),
                notes={"tag": "test"},
                difference_snapshot={},
            )


class TestCorrelation:
    def _consumer_obs(self, tick, pair_eligible=True, caller_class="X", caller_qualname="X.y"):
        return CooccurrenceObservation(
            tick=tick, pair_eligible=pair_eligible, trace_length=2 if pair_eligible else 1,
            caller_class=caller_class, caller_qualname=caller_qualname,
        )

    def _producer_obs(self, tick, causal_context=None):
        return ProducerObservation(
            method="snapshot", tick=tick, producer_class="DifferenceHistoryBuffer",
            producer_instance_id=1, causal_context=causal_context or {},
        )

    def test_case_a_no_proximity(self):
        producer = [self._producer_obs(tick=1000)]
        consumer = [self._consumer_obs(tick=1)]
        finding = correlate_producer_consumer(producer, consumer, tick_window=5)
        assert finding.case == "A_no_proximity"

    def test_case_b_same_tick_no_shared_context(self):
        producer = [self._producer_obs(tick=10, causal_context={"Foo.run_id": "abc"})]
        consumer = [self._consumer_obs(tick=10, caller_class="Bar", caller_qualname="Bar.baz")]
        finding = correlate_producer_consumer(producer, consumer, tick_window=2)
        assert finding.case == "B_same_tick_no_link"
        assert finding.detail["n_with_shared_causal_context"] == 0

    def test_case_c_consistent_temporal_offset(self):
        # Widely separated pairs (100-apart) so each consumer's nearest
        # producer is unambiguously its own intended pair, not a neighbor's.
        producer = [self._producer_obs(tick=100 + i * 100) for i in range(5)]
        consumer = [self._consumer_obs(tick=105 + i * 100) for i in range(5)]  # always +5
        finding = correlate_producer_consumer(producer, consumer, tick_window=10)
        assert finding.case == "C_temporal_offset"
        assert finding.detail["consistent_offset_ticks"] == 5

    def test_insufficient_data_when_either_side_empty(self):
        assert correlate_producer_consumer([], [self._consumer_obs(tick=1)]).case == "insufficient_data"
        assert correlate_producer_consumer([self._producer_obs(tick=1)], []).case == "insufficient_data"

    def test_non_pair_eligible_consumer_observations_are_ignored(self):
        producer = [self._producer_obs(tick=10)]
        consumer = [self._consumer_obs(tick=10, pair_eligible=False)]
        finding = correlate_producer_consumer(producer, consumer, tick_window=5)
        assert finding.case == "insufficient_data"


class TestLiveCombinedExercise:
    """The real, live, combined demonstration: two real call sites, driven
    together, both sidecars installed. See the report script's own
    docstring for the caveat on what this does and doesn't demonstrate."""

    def test_real_combined_exercise_shows_same_tick_no_shared_context(self):
        from aurora_genealogy_difference_producer_observatory_report import run_combined_live_exercise

        producer_sink, consumer_sink = run_combined_live_exercise(n_ticks=6)
        assert len(producer_sink) > 0
        assert len(consumer_sink) > 0

        finding = correlate_producer_consumer(producer_sink, consumer_sink, tick_window=2)
        assert finding.case == "B_same_tick_no_link"
        assert finding.detail["n_proximate_pairs"] > 0
        assert finding.detail["n_with_shared_causal_context"] == 0


class TestPurelyObservational:
    def test_producer_module_never_imports_promotion_authority(self):
        import aurora_genealogy_difference_producer_observatory as mod
        import ast
        import inspect

        tree = ast.parse(inspect.getsource(mod))
        imported_modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module)
        assert not any("constraint_genealogy" in m for m in imported_modules)

    def test_producer_observatory_is_pure(self):
        real_state_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aurora_state"
        )
        before = set(os.listdir(real_state_dir))
        sink, uninstall = install_producer_observatory()
        buf = DifferenceHistoryBuffer()
        buf.record(tick=1, magnitudes=_MAGNITUDES)
        buf.snapshot(tick=1, magnitudes=_MAGNITUDES)
        uninstall()
        after = set(os.listdir(real_state_dir))
        assert before == after


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))

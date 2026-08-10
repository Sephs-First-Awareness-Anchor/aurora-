#!/usr/bin/env python3
"""
Tests for aurora_genealogy_cooccurrence_observatory.py (Phase 3A.1).

Unlike Phase 3A (a parallel structure replaying static JSON), this module
wraps the REAL, live ConstraintGenealogyLogger.observe(). The safety bar is
therefore behavioral: the wrapped call must be provably identical to the
unwrapped call in every observable effect, and a sidecar failure must never
break the real call. These tests establish that directly, plus the
classification logic's correctness on real objects (real ConstraintLink
genealogy classes, real DifferenceHistoryBuffer/DifferenceSnapshot, and the
real, confirmed aurora_grammar_engine.py call site).

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from aurora_internal.constraint_genealogy import ConstraintGenealogyLogger, PressureVec, TraceItem
from aurora_internal.aurora_difference_buffer import DifferenceHistoryBuffer, DifferenceSnapshot
from aurora_internal.aurora_constraint_manifold_patched import Constraint

from aurora_genealogy_cooccurrence_observatory import install, CooccurrenceObservation

_MAGNITUDES = {Constraint.X: 0.1, Constraint.T: 0.2, Constraint.N: 0.05, Constraint.B: 0.0, Constraint.A: 0.3}

_LEDGER_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "aurora_state", "pressure_experiences.jsonl",
)


@pytest.fixture(autouse=True)
def _restore_shared_pressure_ledger():
    """PressureExperienceLedger (aurora_internal/aurora_pressure_ledger.py:114)
    is a process-wide singleton with a hardcoded path -- exercising real
    _try_promote() Gate 2/4/5 rejections (an unavoidable, expected
    consequence of calling the real observe() pipeline in this test file,
    even against throwaway loggers) appends to that real, shared file
    regardless of which logger triggered it. Snapshot and restore it around
    every test so this file never mutates the repo as a side effect of
    running the suite."""
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


def _new_logger(run_id="cooc_test"):
    return ConstraintGenealogyLogger(run_id=run_id, output_dir=tempfile.mkdtemp())


def _real_snapshot(tick):
    buf = DifferenceHistoryBuffer()
    buf.record(tick=tick, magnitudes=_MAGNITUDES)
    return buf.snapshot(tick=tick, magnitudes=_MAGNITUDES)


class TestBehavioralIdentity:
    def test_wrapped_observe_produces_identical_result_to_unwrapped(self):
        args = dict(
            pressure_before=PressureVec(X=0.5, T=0.5, N=0.5, B=0.5, A=0.5),
            trace=[TraceItem(kind="ABILITY", id="A:OUTLET_PUSH"), TraceItem(kind="ABILITY", id="B:INTERFACE_WEAKEN")],
            pressure_after=PressureVec(X=0.4, T=0.3, N=0.4, B=0.4, A=0.3),
            notes={"tag": "test"},
        )

        plain_logger = _new_logger("plain")
        plain_result = plain_logger.observe(**args)

        wrapped_logger = _new_logger("wrapped")
        sink, uninstall = install(wrapped_logger)
        wrapped_result = wrapped_logger.observe(**args)
        uninstall()

        assert (plain_result is None) == (wrapped_result is None)
        if plain_result is not None:
            assert plain_result.relief.to_dict() == wrapped_result.relief.to_dict()
            assert plain_result.trace_cost_total == wrapped_result.trace_cost_total
            assert plain_result.dominant_relief_axis == wrapped_result.dominant_relief_axis
        assert plain_logger.links_promoted == wrapped_logger.links_promoted
        assert set(plain_logger._pair_stats.keys()) == set(wrapped_logger._pair_stats.keys())
        assert len(sink) == 1

    def test_sidecar_failure_never_breaks_real_observe(self, monkeypatch):
        import aurora_genealogy_cooccurrence_observatory as mod

        def _boom(*args, **kwargs):
            raise RuntimeError("sidecar exploded")

        monkeypatch.setattr(mod, "_record_observation", _boom)

        logger = _new_logger()
        sink, uninstall = install(logger)
        result = logger.observe(
            pressure_before=PressureVec(X=0.5, T=0.5, N=0.5, B=0.5, A=0.5),
            trace=[TraceItem(kind="ABILITY", id="A:OUTLET_PUSH"), TraceItem(kind="ABILITY", id="B:INTERFACE_WEAKEN")],
            pressure_after=PressureVec(X=0.4, T=0.3, N=0.4, B=0.4, A=0.3),
        )
        uninstall()
        assert result is not None  # the real call still succeeded
        assert sink == []  # the broken sidecar recorded nothing, but didn't crash the call

    def test_sidecar_never_feeds_difference_back_into_pairstats(self):
        logger = _new_logger()
        sink, uninstall = install(logger)
        snap = _real_snapshot(tick=1)
        logger.observe(
            pressure_before=PressureVec(X=0.5, T=0.5, N=0.5, B=0.5, A=0.5),
            trace=[TraceItem(kind="ABILITY", id="A:OUTLET_PUSH"), TraceItem(kind="ABILITY", id="B:INTERFACE_WEAKEN")],
            pressure_after=PressureVec(X=0.4, T=0.3, N=0.4, B=0.4, A=0.3),
            difference_snapshot=snap,
        )
        uninstall()

        assert sink[0].difference_passed is True  # the sidecar DID see it
        # ...but PairStats itself is structurally incapable of holding it
        # (Phase 2 finding) -- confirm no PairStats instance exposes it.
        for ps in logger._pair_stats.values():
            assert not hasattr(ps, "difference_values")
            assert set(vars(ps).keys()) == {
                "left_id", "right_id", "count", "relief_sum", "relief_sq_sum",
                "relief_pos_sum", "pos_count", "cost_sum", "x_risk_sum", "last_seen_tick",
            }

    def test_uninstall_restores_plain_behavior(self):
        logger = _new_logger()
        sink, uninstall = install(logger)
        logger.observe(
            pressure_before=PressureVec(X=0.5, T=0.5, N=0.5, B=0.5, A=0.5),
            trace=[TraceItem(kind="ABILITY", id="A:OUTLET_PUSH"), TraceItem(kind="ABILITY", id="B:INTERFACE_WEAKEN")],
            pressure_after=PressureVec(X=0.4, T=0.3, N=0.4, B=0.4, A=0.3),
        )
        assert len(sink) == 1
        uninstall()
        logger.observe(
            pressure_before=PressureVec(X=0.5, T=0.5, N=0.5, B=0.5, A=0.5),
            trace=[TraceItem(kind="ABILITY", id="A:OUTLET_PUSH"), TraceItem(kind="ABILITY", id="B:INTERFACE_WEAKEN")],
            pressure_after=PressureVec(X=0.4, T=0.3, N=0.4, B=0.4, A=0.3),
        )
        assert len(sink) == 1  # unchanged -- no longer wrapped


class TestClassificationCorrectness:
    def test_pair_keys_match_adjacent_pair_rule(self):
        logger = _new_logger()
        sink, uninstall = install(logger)
        logger.observe(
            pressure_before=PressureVec(X=0.5, T=0.5, N=0.5, B=0.5, A=0.5),
            trace=[
                TraceItem(kind="ABILITY", id="A:one"),
                TraceItem(kind="ABILITY", id="B:two"),
                TraceItem(kind="ABILITY", id="T:three"),
            ],
            pressure_after=PressureVec(X=0.4, T=0.3, N=0.4, B=0.4, A=0.3),
        )
        uninstall()
        obs = sink[0]
        assert obs.trace_length == 3
        assert obs.pair_eligible is True
        assert obs.pair_keys == [("A:one", "B:two"), ("B:two", "T:three")]

    def test_single_item_trace_is_not_pair_eligible(self):
        logger = _new_logger()
        sink, uninstall = install(logger)
        logger.observe(
            pressure_before=PressureVec(X=0.5, T=0.5, N=0.5, B=0.5, A=0.5),
            trace=[TraceItem(kind="ABILITY", id="A:one")],
            pressure_after=PressureVec(X=0.4, T=0.3, N=0.4, B=0.4, A=0.3),
        )
        uninstall()
        obs = sink[0]
        assert obs.trace_length == 1
        assert obs.pair_eligible is False
        assert obs.pair_keys == []

    def test_difference_argument_captured_with_full_values(self):
        logger = _new_logger()
        sink, uninstall = install(logger)
        snap = _real_snapshot(tick=logger.tick_count + 1)
        logger.observe(
            pressure_before=PressureVec(X=0.5, T=0.5, N=0.5, B=0.5, A=0.5),
            trace=[TraceItem(kind="ABILITY", id="A:one"), TraceItem(kind="ABILITY", id="B:two")],
            pressure_after=PressureVec(X=0.4, T=0.3, N=0.4, B=0.4, A=0.3),
            difference_snapshot=snap,
        )
        uninstall()
        obs = sink[0]
        assert obs.difference_passed is True
        assert obs.difference_source == "argument"
        assert obs.difference_values is not None
        assert set(obs.difference_values.keys()) == {"X", "T", "N", "B", "A"}
        assert obs.difference_age_ticks is not None

    def test_reachable_buffer_on_caller_found_via_frame_introspection(self):
        logger = _new_logger()
        sink, uninstall = install(logger)

        class FakeChamberCaller:
            def __init__(self, logger):
                self._genealogy = logger
                self._diff_buffer = DifferenceHistoryBuffer()
                self._diff_buffer.record(tick=logger.tick_count, magnitudes=_MAGNITUDES)

            def do_tick(self):
                self._genealogy.observe(
                    pressure_before=PressureVec(X=0.5, T=0.5, N=0.5, B=0.5, A=0.5),
                    trace=[TraceItem(kind="ABILITY", id="A:one"), TraceItem(kind="ABILITY", id="B:two")],
                    pressure_after=PressureVec(X=0.4, T=0.3, N=0.4, B=0.4, A=0.3),
                    difference_snapshot=None,
                )

        FakeChamberCaller(logger).do_tick()
        uninstall()
        obs = sink[0]
        assert obs.difference_passed is False
        assert obs.difference_source == "caller_frame:FakeChamberCaller._diff_buffer"
        assert "not passed to this observe() call" in obs.difference_unavailable_reason
        assert obs.caller_class == "FakeChamberCaller"

    def test_no_signal_anywhere_reachable_reports_honest_reason(self):
        logger = _new_logger()
        sink, uninstall = install(logger)
        logger.observe(
            pressure_before=PressureVec(X=0.5, T=0.5, N=0.5, B=0.5, A=0.5),
            trace=[TraceItem(kind="ABILITY", id="A:one"), TraceItem(kind="ABILITY", id="B:two")],
            pressure_after=PressureVec(X=0.4, T=0.3, N=0.4, B=0.4, A=0.3),
        )
        uninstall()
        obs = sink[0]
        assert obs.difference_passed is False
        assert obs.difference_source is None
        assert "does not rule out one existing elsewhere" in obs.difference_unavailable_reason


class TestRealCallSite:
    def test_real_grammar_engine_call_site_shows_no_difference_signal(self):
        import aurora_grammar_engine

        logger = _new_logger()
        sink, uninstall = install(logger)
        engine = aurora_grammar_engine.GrammarEngine(state_dir=tempfile.mkdtemp())
        engine.set_genealogy(logger)
        engine._log_relief_to_genealogy(text_changed=True, clarity=0.8, motif=None)
        uninstall()

        assert len(sink) == 1
        obs = sink[0]
        assert obs.pair_eligible is True
        assert obs.difference_passed is False
        assert obs.caller_class == "GrammarEngine"


class TestLiveReplayAgainstRealCorpus:
    """Regression-lock the live-execution confirmation of Phase 3A's static
    finding: replaying the real corpus through the REAL observe() pipeline
    (not a parallel shadow structure) still shows zero genuine co-occurrence."""

    def test_live_replay_of_real_corpus_confirms_zero_cooccurrence(self):
        # Pinned to the committed snapshot, not the live aurora_state/genealogy/
        # path -- found, running the full suite, that some OTHER test boots a
        # real ConstraintGenealogyLogger against that live path and overwrites
        # events_recent.json (31259 lines -> 1), which made this regression
        # flaky depending on test order/full-suite-vs-isolated runs.
        events_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "fixtures", "genealogy_events_recent_snapshot.json",
        )
        if not os.path.exists(events_path):
            pytest.skip("tests/fixtures/genealogy_events_recent_snapshot.json not present in this checkout")

        from aurora_genealogy_cooccurrence_observatory_report import replay_real_corpus_live

        sink = replay_real_corpus_live(events_path=events_path)
        assert len(sink) > 0
        eligible_and_passed = [o for o in sink if o.pair_eligible and o.difference_passed]
        assert eligible_and_passed == []

    def test_live_grammar_engine_exercise_never_shows_difference_signal(self):
        from aurora_genealogy_cooccurrence_observatory_report import exercise_grammar_engine_live

        sink = exercise_grammar_engine_live(n_calls=5)
        assert len(sink) == 5
        assert all(o.difference_passed is False for o in sink)
        assert all(o.caller_class == "GrammarEngine" for o in sink)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))

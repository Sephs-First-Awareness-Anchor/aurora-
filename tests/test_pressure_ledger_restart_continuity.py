# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA BUILD 648 EVOLUTIONARY INFRASTRUCTURE CLOSURE DIRECTIVE, Phase 6:
PressureExperienceLedger persisted every experience to
aurora_state/pressure_experiences.jsonl, but a freshly constructed
ledger always started with an empty _buffer and never read that file
back -- recent()/outcome_variance()/conditioning_signal() only ever saw
experiences recorded since the current process started. This proves
that a real conditional history (same causal_action, different
outcomes -- the exact case outcome_variance()'s own docstring names as
the developmental signal) survives a clean process-level reconstruction
from persisted state, and that state_dir isolation (not always
"aurora_state" in the CWD) works as intended.

No new pressure semantics are introduced or asserted here -- only that
existing semantics survive restart.
"""
import os
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_internal.aurora_pressure_ledger import PressureExperienceLedger


class TestConditionalHistorySurvivesRestart:
    def test_same_action_different_outcomes_remains_conditional_after_reconstruction(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = PressureExperienceLedger(state_dir=tmp)
            ledger.record(
                anchor="concept_x", meaning="test", pursuing="goal_a",
                causal_action="attempt_resolution", consequence={"cost_signal": 0.3},
                outcome={"resolved": True}, source="test",
            )
            ledger.record(
                anchor="concept_x", meaning="test", pursuing="goal_a",
                causal_action="attempt_resolution", consequence={"cost_signal": 0.5},
                outcome={"resolved": False}, source="test",
            )
            variance_before = ledger.outcome_variance("concept_x")
            assert variance_before["is_conditional"] is True
            assert variance_before["sample_count"] == 2
            del ledger  # true restart: the object is gone, not just re-derived

            reloaded = PressureExperienceLedger(state_dir=tmp)
            assert len(reloaded.recent(n=20, anchor="concept_x")) == 2
            variance_after = reloaded.outcome_variance("concept_x")
            assert variance_after["is_conditional"] is True
            assert variance_after["sample_count"] == 2

            signal = reloaded.conditioning_signal("concept_x")
            assert signal["conditional"] is True
            assert "concept_x" in signal["note"]

    def test_consistent_single_outcome_history_remains_non_conditional_after_restart(self):
        """Contrast case: a reliable (non-conditional) anchor must not
        become falsely conditional merely from restart/reload."""
        with tempfile.TemporaryDirectory() as tmp:
            ledger = PressureExperienceLedger(state_dir=tmp)
            for _ in range(3):
                ledger.record(
                    anchor="concept_y", meaning="test", pursuing="goal_b",
                    causal_action="steady_action", consequence={"cost_signal": 0.1},
                    outcome={"resolved": True}, source="test",
                )
            del ledger

            reloaded = PressureExperienceLedger(state_dir=tmp)
            variance = reloaded.outcome_variance("concept_y")
            assert variance["is_conditional"] is False
            assert variance["sample_count"] == 3


class TestStateDirIsolation:
    def test_two_distinct_state_dirs_never_cross_contaminate(self):
        with tempfile.TemporaryDirectory() as tmp_a, tempfile.TemporaryDirectory() as tmp_b:
            ledger_a = PressureExperienceLedger(state_dir=tmp_a)
            ledger_a.record(
                anchor="only_in_a", meaning="", pursuing="", causal_action="act",
                consequence={}, outcome={"resolved": True}, source="test",
            )
            ledger_b = PressureExperienceLedger(state_dir=tmp_b)
            assert ledger_b.recent(n=20, anchor="only_in_a") == []
            assert os.path.exists(os.path.join(tmp_a, "pressure_experiences.jsonl"))
            assert not os.path.exists(os.path.join(tmp_b, "pressure_experiences.jsonl"))

    def test_no_explicit_state_dir_falls_back_to_active_state_dir_mechanism(self):
        with tempfile.TemporaryDirectory() as tmp:
            from aurora_internal.aurora_state_context import set_active_state_dir, clear_active_state_dir
            try:
                set_active_state_dir(tmp)
                ledger = PressureExperienceLedger()
                assert ledger.state_dir == tmp
            finally:
                clear_active_state_dir()


class TestMalformedPersistedLineIsSkippedNotFatal:
    def test_one_corrupt_line_does_not_prevent_loading_the_rest(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "pressure_experiences.jsonl")
            os.makedirs(tmp, exist_ok=True)
            import json
            valid_line = json.dumps({
                "experience_id": "abc123", "timestamp": 0.0, "source": "test",
                "anchor": "concept_z", "meaning": "", "pursuing": "", "causal_action": "act",
                "consequence": {}, "outcome": {"resolved": True},
            })
            with open(log_path, "w") as f:
                f.write(valid_line + "\n")
                f.write("{not valid json::\n")

            ledger = PressureExperienceLedger(state_dir=tmp)
            assert len(ledger.recent(n=20, anchor="concept_z")) == 1

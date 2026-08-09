# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA DREAM SUBSTRATE, FAIL-STREAM, POSITIVE-AFFECT, DEVELOPMENTAL
WRITEBACK, AND NATIVE INTERMEDIATE RESOLUTION DIRECTIVE, Sections 4-5,
46: pre-outcome pressure must be captured BEFORE the outcome is known,
and must remain distinguishable from whatever pressure exists once the
error is already recognized.
"""
import os
import sys
import tempfile
from types import SimpleNamespace

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)


def _contract(state_dir):
    from aurora_internal.aurora_understanding_contract import RuntimeUnderstandingContract
    return RuntimeUnderstandingContract(state_dir=state_dir)


class TestCommitApplicationCapturesPreOutcomePressure:
    def test_pending_validation_carries_a_pressure_snapshot(self):
        with tempfile.TemporaryDirectory() as state_dir:
            contract = _contract(state_dir)
            contract.commit_application(
                {}, "I need to protect my boundaries here", "Here is my response.",
                response_source="grounded_answer", confidence=0.7,
            )
            pending = contract.state.get("pending_validation", {})
            pop = pending.get("pre_outcome_pressure")
            assert isinstance(pop, dict)
            assert set(pop.keys()) == {"X", "T", "N", "B", "A"}
            assert all(isinstance(v, float) for v in pop.values())

    def test_snapshot_reflects_the_state_at_commit_time_not_a_constant(self):
        """Falsification check: mutate contract.state between two commits
        and confirm the captured pressure actually changes -- proving it's
        a real snapshot of before_state, not a hardcoded/default value."""
        with tempfile.TemporaryDirectory() as state_dir:
            contract = _contract(state_dir)
            contract.commit_application({}, "hello", "hi there", response_source="greeting")
            pop_1 = dict(contract.state["pending_validation"]["pre_outcome_pressure"])

            # Force a materially different X/A state before the next commit.
            contract.state["X"] = {"score": 0.05, "label": "low"}
            contract.state["A"] = {"score": 0.95, "label": "high", "delta": 0.0, "fit_reason": ""}
            contract.commit_application({}, "another turn", "another response", response_source="greeting")
            pop_2 = dict(contract.state["pending_validation"]["pre_outcome_pressure"])

            assert pop_1 != pop_2, "pre_outcome_pressure did not change despite a materially different before_state"


class TestPreOutcomePressureSurvivesToTheVerdict:
    def test_evaluate_previous_accuracy_surfaces_the_captured_pressure(self):
        with tempfile.TemporaryDirectory() as state_dir:
            contract = _contract(state_dir)
            contract.commit_application({}, "hello", "hi there", response_source="greeting")
            captured = dict(contract.state["pending_validation"]["pre_outcome_pressure"])

            accuracy = contract._evaluate_previous_accuracy({}, "that's wrong, you misunderstood", None)
            assert accuracy["label"] == "corrected"
            assert accuracy.get("pre_outcome_pressure") == captured

    def test_no_pending_validation_yields_no_fabricated_pressure(self):
        with tempfile.TemporaryDirectory() as state_dir:
            contract = _contract(state_dir)
            accuracy = contract._evaluate_previous_accuracy({}, "hello", None)
            assert accuracy["used"] is False
            assert accuracy.get("pre_outcome_pressure") is None


class TestPreErrorAndPostErrorPressureAreDistinguished:
    def test_post_error_pressure_is_not_substituted_for_pre_outcome_pressure(self):
        """The pressure captured before the mistake must not be silently
        replaced by whatever the contract's live X/T/N/B/A state looks
        like at the moment the correction is recognized."""
        with tempfile.TemporaryDirectory() as state_dir:
            contract = _contract(state_dir)
            contract.commit_application({}, "hello", "hi there", response_source="greeting")
            pre_outcome_pressure = dict(contract.state["pending_validation"]["pre_outcome_pressure"])

            # Simulate the contract's live state moving on before the
            # correction is recognized on the next turn.
            contract.state["X"] = {"score": 0.02, "label": "very_low"}
            contract.state["T"] = {"sequence_gap": 0.9}
            contract.state["N"] = {"total": 0.95}
            contract.state["B"] = {"ambiguity": 0.9}
            contract.state["A"] = {"score": 0.02, "label": "very_low", "delta": 0.0, "fit_reason": ""}
            post_error_pressure = contract._pressure_from_state(contract.state).to_dict()

            accuracy = contract._evaluate_previous_accuracy({}, "wrong, that's not it", None)
            assert accuracy["label"] == "corrected"
            assert accuracy["pre_outcome_pressure"] == pre_outcome_pressure
            assert accuracy["pre_outcome_pressure"] != post_error_pressure


class TestLiveCorrectionFeedsRichStreamNotTheAggregate:
    def test_ingest_observation_records_a_pre_outcome_event_on_correction(self):
        import aurora_dream_trainer as dt
        with tempfile.TemporaryDirectory() as ledger_dir, tempfile.TemporaryDirectory() as state_dir:
            ledger = dt.FailPointLedger(ledger_dir)
            systems = {"dream_trainer": SimpleNamespace(ledger=ledger)}

            contract = _contract(state_dir)
            contract.commit_application(
                systems, "I need to protect my boundaries here", "Here is my response.",
                response_source="grounded_answer",
            )
            expected_pressure = dict(contract.state["pending_validation"]["pre_outcome_pressure"])

            top_fails_before = ledger.get_top_fails(5)
            contract.ingest_observation(systems, "no, that's wrong", turn_tick=1)

            events = ledger.rich_stream.ordered()
            assert len(events) == 1
            event = events[0]
            assert event.source == "live_correction"
            assert event.outcome_label == "corrected"
            assert event.pre_outcome_pressure == expected_pressure

            # The corpus/rubric dimension aggregate must be completely
            # unaffected by a live conversational correction -- different
            # fail domain, per Section 8.
            assert ledger.get_top_fails(5) == top_fails_before
            assert ledger._total_fails == 0

    def test_agreement_does_not_record_a_fail_event(self):
        import aurora_dream_trainer as dt
        with tempfile.TemporaryDirectory() as ledger_dir, tempfile.TemporaryDirectory() as state_dir:
            ledger = dt.FailPointLedger(ledger_dir)
            systems = {"dream_trainer": SimpleNamespace(ledger=ledger)}

            contract = _contract(state_dir)
            contract.commit_application(systems, "hello", "hi there", response_source="greeting")
            contract.ingest_observation(systems, "exactly, thank you", turn_tick=1)

            assert ledger.rich_stream.ordered() == []

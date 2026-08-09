# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA DREAM SUBSTRATE... DIRECTIVE, Section 19, 52: under low failure
load, this pass's Dream substrate must not fabricate artificial fail
points solely to fill available simulation/curriculum capacity.
"""
import inspect
import os
import sys
from types import SimpleNamespace

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)


class TestGatheringIsPurelyReadOnly:
    def test_gather_dream_substrate_never_calls_record_fail_or_record_pre_outcome_event(self):
        import aurora_dream_substrate as ds
        for name in dir(ds):
            obj = getattr(ds, name)
            if inspect.isfunction(obj) and obj.__module__ == ds.__name__:
                src = inspect.getsource(obj)
                assert "record_fail(" not in src
                assert "record_pre_outcome_event(" not in src

    def test_gathering_with_zero_fails_produces_zero_fabricated_events(self):
        import aurora_dream_trainer as dt
        from aurora_dream_substrate import gather_dream_substrate

        ledger = dt.FailPointLedger.__new__(dt.FailPointLedger)
        ledger.__init__(state_dir="/tmp")
        systems = {"dimensional": None, "dream_trainer": SimpleNamespace(ledger=ledger)}

        substrate = gather_dream_substrate(systems)
        assert substrate.fail_pressure_stream == []
        assert substrate.historical_recurrence == []
        assert substrate.unresolved_fail_load == 0.0
        assert substrate.positive_opportunity_weight == 1.0

        # Gathering must not have mutated the ledger as a side effect.
        assert ledger._total_fails == 0
        assert ledger.rich_stream.ordered() == []

    def test_calling_gather_dream_substrate_repeatedly_does_not_accumulate_state(self):
        import aurora_dream_trainer as dt
        from aurora_dream_substrate import gather_dream_substrate

        ledger = dt.FailPointLedger.__new__(dt.FailPointLedger)
        ledger.__init__(state_dir="/tmp")
        systems = {"dimensional": None, "dream_trainer": SimpleNamespace(ledger=ledger)}

        for _ in range(5):
            gather_dream_substrate(systems)
        assert ledger.rich_stream.ordered() == []
        assert ledger._total_fails == 0


class TestUnderstandingContractDoesNotInventCorrectionsUnderLowFailure:
    def test_ordinary_agreement_never_records_a_pre_outcome_fail_event(self):
        """The wiring added by this pass only fires on a GENUINE detected
        correction/confusion label -- confirms it cannot spuriously invent
        a fail when the user is simply agreeing, regardless of how many
        turns pass."""
        import aurora_dream_trainer as dt
        from aurora_internal.aurora_understanding_contract import RuntimeUnderstandingContract
        import tempfile

        with tempfile.TemporaryDirectory() as ledger_dir, tempfile.TemporaryDirectory() as state_dir:
            ledger = dt.FailPointLedger(ledger_dir)
            systems = {"dream_trainer": SimpleNamespace(ledger=ledger)}
            contract = RuntimeUnderstandingContract(state_dir=state_dir)

            for i in range(5):
                contract.commit_application(systems, f"turn {i}", f"response {i}", response_source="greeting")
                contract.ingest_observation(systems, "thanks, that makes sense", turn_tick=i)

            assert ledger.rich_stream.ordered() == []

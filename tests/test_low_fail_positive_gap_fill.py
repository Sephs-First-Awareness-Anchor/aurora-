# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA DREAM SUBSTRATE... DIRECTIVE, Sections 16, 19, 39, 51: positive
Dream opportunity must be a continuous function of unresolved fail load
(derived from FailPointLedger's own existing top-fail score, not a
fabricated weighting), not a boolean happy-dream switch.
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)


class TestContinuousNotBinary:
    def test_zero_fails_gives_full_positive_opportunity(self):
        import aurora_dream_trainer as dt
        from aurora_dream_substrate import positive_opportunity_weight

        ledger = dt.FailPointLedger.__new__(dt.FailPointLedger)
        ledger.__init__(state_dir="/tmp")
        from types import SimpleNamespace
        dream_trainer = SimpleNamespace(ledger=ledger)
        assert positive_opportunity_weight(dream_trainer) == 1.0

    def test_opportunity_decreases_monotonically_as_fail_load_increases(self):
        """Period_A (high unresolved fail load) vs Period_B (low) --
        Section 51's comparison canary requirement."""
        import aurora_dream_trainer as dt
        from aurora_dream_substrate import positive_opportunity_weight, unresolved_fail_load
        from types import SimpleNamespace

        ledger_low = dt.FailPointLedger.__new__(dt.FailPointLedger)
        ledger_low.__init__(state_dir="/tmp")
        ledger_low.record_fail("context_carryover", severity=0.1)

        ledger_high = dt.FailPointLedger.__new__(dt.FailPointLedger)
        ledger_high.__init__(state_dir="/tmp")
        for _ in range(10):
            ledger_high.record_fail("context_carryover", severity=0.9)
            ledger_high.record_fail("contradiction_handling", severity=0.9)

        load_low = unresolved_fail_load(SimpleNamespace(ledger=ledger_low))
        load_high = unresolved_fail_load(SimpleNamespace(ledger=ledger_high))
        assert load_high > load_low

        opp_low = positive_opportunity_weight(SimpleNamespace(ledger=ledger_low))
        opp_high = positive_opportunity_weight(SimpleNamespace(ledger=ledger_high))
        assert opp_low > opp_high

    def test_no_boolean_threshold_step_function(self):
        """A small change in fail count must produce a small (not a
        cliff-edge binary) change in opportunity -- confirms this is a
        continuum, not an if/else switch."""
        import aurora_dream_trainer as dt
        from aurora_dream_substrate import positive_opportunity_weight
        from types import SimpleNamespace

        weights = []
        for n in range(0, 6):
            ledger = dt.FailPointLedger.__new__(dt.FailPointLedger)
            ledger.__init__(state_dir="/tmp")
            for _ in range(n):
                ledger.record_fail("context_carryover", severity=0.5)
            weights.append(positive_opportunity_weight(SimpleNamespace(ledger=ledger)))

        # Monotonic non-increasing as fail count rises, and no two adjacent
        # values are separated by a large discontinuous jump relative to
        # the total possible range (which would indicate a step function).
        assert all(weights[i] >= weights[i + 1] for i in range(len(weights) - 1))
        diffs = [weights[i] - weights[i + 1] for i in range(len(weights) - 1)]
        assert max(diffs) < 0.5  # no single step consumes half the entire [0,1] range

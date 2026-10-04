"""One finite recovery capacity, shared by recovery and consolidation in proportion to their need.

Authors: Sunni (Sir) Morningstar and Cael Devo

Sir's decision: rest creates ONE finite recovery capacity that both coherence recovery and consolidation draw from,
allocated dynamically by relative unresolved need. No debt: all of it restores. Recovery complete and debt left: all
of it goes to consolidation. Both owed: their current state sets the share. No arbitrary fixed percentage, nothing
free, no wake-up cost.
"""
import os
import random
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_internal import aurora_rest_ledger as L  # noqa: E402
from aurora_internal.aurora_rest_ledger import (  # noqa: E402
    DEFAULT_REST_RATE, RestLedger, allocate_rest, consolidation_share, core_step_cost, rest_gain, rest_rate,
    settle, wear_repaid,
)

R = DEFAULT_REST_RATE


# ---- the three cases, exactly as decided -------------------------------------------------------------------------

def test_with_no_consolidation_debt_all_of_the_capacity_restores_her():
    recovery, consolidation = allocate_rest(0.6, 0.0, 12.0)
    assert consolidation == 0.0
    assert recovery == pytest.approx(0.6 * (1 - (1 - R) ** 12))


def test_with_recovery_complete_all_of_the_capacity_goes_to_consolidation():
    recovery, consolidation = allocate_rest(0.0, 0.05, 12.0)
    assert recovery == 0.0
    assert consolidation == pytest.approx(0.05 * (1 - (1 - R) ** 12))


def test_with_both_owed_each_is_resolved_less_than_it_would_be_alone():
    """The capacity is finite: a debt DOES slow recovery, and recovery slows consolidation. Nothing is free."""
    recovery, consolidation = allocate_rest(0.6, 0.3, 12.0)
    assert 0.0 < recovery < allocate_rest(0.6, 0.0, 12.0)[0]
    assert 0.0 < consolidation < allocate_rest(0.0, 0.3, 12.0)[1]


def test_the_larger_need_takes_the_larger_part_of_the_capacity():
    big_wear = allocate_rest(0.8, 0.1, 3.0)
    big_debt = allocate_rest(0.1, 0.8, 3.0)
    assert big_wear[0] > big_wear[1] and big_debt[1] > big_debt[0]


def test_the_capacity_is_split_in_proportion_to_current_need_with_no_fixed_fraction():
    """One amount per tick (the resting rate on the largest need) is divided in proportion to what each need is
    NOW, so each receives a part proportional to its own size and both relax at the same rate. No constant."""
    for wear, debt in ((0.7, 0.1), (0.1, 0.7), (0.5, 0.2), (0.2, 0.5), (0.3, 0.3), (0.6, 0.3)):
        rec, con = allocate_rest(wear, debt, 1.0)
        assert rec / con == pytest.approx(wear / debt, rel=1e-9), "split in proportion to need"
        rho = R * max(wear, debt) / (wear + debt)
        assert rec == pytest.approx(wear * rho, rel=1e-9) and con == pytest.approx(debt * rho, rel=1e-9)


def test_competition_is_strongest_when_the_needs_are_equal_and_negligible_when_one_dominates():
    equal = allocate_rest(0.4, 0.4, 1.0)[0] / 0.4          # half the resting rate each
    assert equal == pytest.approx(R / 2)
    dominated = allocate_rest(0.614, 0.052, 12.0)
    alone_r, alone_c = allocate_rest(0.614, 0.0, 12.0)[0], allocate_rest(0.0, 0.052, 12.0)[1]
    assert dominated[0] > 0.95 * alone_r and dominated[1] > 0.95 * alone_c, "a small debt neither starves nor slows"
    contested = allocate_rest(0.6, 0.3, 12.0)
    assert contested[0] < 0.9 * allocate_rest(0.6, 0.0, 12.0)[0], "two substantial needs genuinely compete"


def test_both_needs_relax_at_the_same_rate_so_the_split_never_drifts():
    for n in (1, 3, 12, 40):
        rec, con = allocate_rest(0.6, 0.2, n)
        assert rec / 0.6 == pytest.approx(con / 0.2, rel=1e-9)


def test_resting_two_ticks_equals_resting_one_then_another_from_the_state_it_left():
    """The allocation is a function of her CURRENT state, so it composes exactly."""
    r1, c1 = allocate_rest(0.6, 0.3, 1.0)
    r2, c2 = allocate_rest(0.6 - r1, 0.3 - c1, 1.0)
    both = allocate_rest(0.6, 0.3, 2.0)
    assert r1 + r2 == pytest.approx(both[0]) and c1 + c2 == pytest.approx(both[1])


@pytest.mark.parametrize("n1,n2", [(1, 1), (3, 5), (12, 12), (2, 40)])
def test_two_rests_compose_into_one_longer_rest(n1, n2):
    r1, c1 = allocate_rest(0.5, 0.2, n1)
    r2, c2 = allocate_rest(0.5 - r1, 0.2 - c1, n2)
    whole = allocate_rest(0.5, 0.2, n1 + n2)
    assert r1 + r2 == pytest.approx(whole[0], abs=2e-6) and c1 + c2 == pytest.approx(whole[1], abs=2e-6)


def test_the_capacity_is_finite_so_a_night_cannot_resolve_more_than_is_owed():
    r, c = allocate_rest(0.6, 0.3, 10_000.0)
    assert r == pytest.approx(0.6) and c == pytest.approx(0.3)
    r, c = allocate_rest(0.6, 0.3, 96.0)
    assert 0.0 < r <= 0.6 and 0.0 < c <= 0.3


def test_neither_need_is_ever_resolved_beyond_its_own_size():
    rng = random.Random(9)
    for _ in range(500):
        w, d, n = rng.random(), rng.random() * 2, rng.choice([0.3, 1, 2.5, 12, 96, 1000])
        r, c = allocate_rest(w, d, n)
        assert -1e-12 <= r <= w + 1e-12 and -1e-12 <= c <= d + 1e-12


def test_more_rest_never_resolves_less():
    prev = (0.0, 0.0)
    for n in (0.0, 0.5, 1, 2, 4, 8, 16, 32, 96):
        cur = allocate_rest(0.6, 0.3, n)
        assert cur[0] >= prev[0] - 1e-12 and cur[1] >= prev[1] - 1e-12
        prev = cur


def test_with_both_owed_the_total_resolved_is_less_than_if_each_stood_alone():
    both = sum(allocate_rest(0.6, 0.3, 12.0))
    alone = allocate_rest(0.6, 0.0, 12.0)[0] + allocate_rest(0.0, 0.3, 12.0)[1]
    assert both < alone


def test_nothing_owed_or_no_time_or_no_rate_resolves_nothing():
    assert allocate_rest(0.0, 0.0, 12.0) == (0.0, 0.0)
    assert allocate_rest(0.6, 0.3, 0.0) == (0.0, 0.0)
    assert allocate_rest(0.6, 0.3, -5.0) == (0.0, 0.0)
    assert allocate_rest(0.6, 0.3, 12.0, rate=0.0) == (0.0, 0.0)
    assert allocate_rest(-1.0, -1.0, 12.0) == (0.0, 0.0)


def test_a_nearly_complete_relaxation_is_complete():
    """1 - 0.85 ** 96 falls short of 1 by 1.7e-7; that priced the last queued item out of a night's rest."""
    assert allocate_rest(0.0, 0.5, 96.0)[1] == 0.5
    assert allocate_rest(0.5, 0.0, 96.0)[0] == 0.5


def test_a_fractional_tick_is_geometric_in_its_length():
    half = allocate_rest(0.6, 0.0, 0.5)[0]
    assert half == pytest.approx(0.6 * (1 - (1 - R) ** 0.5))


def test_a_huge_rest_is_cheap_and_bounded():
    r, c = allocate_rest(0.6, 0.3, 1e9)
    assert (r, c) == (pytest.approx(0.6), pytest.approx(0.3))


def test_the_rate_sets_how_fast_capacity_resolves_need():
    slow, fast = allocate_rest(0.6, 0.3, 3.0, rate=0.05), allocate_rest(0.6, 0.3, 3.0, rate=0.5)
    assert fast[0] > slow[0] and fast[1] > slow[1]


# ---- the pure-recovery helpers are the no-debt case ----------------------------------------------------------------

def test_wear_repaid_is_the_no_debt_case_of_the_allocation():
    assert wear_repaid(0.6, 12.0) == pytest.approx(0.6 * (1 - (1 - R) ** 12))
    assert rest_gain(0.4, 12.0) == pytest.approx(wear_repaid(0.6, 12.0))
    assert rest_gain(1.0, 50.0) == 0.0 and rest_gain(1.4, 50.0) == 0.0


def test_the_resting_rate_is_the_regulators_dissipation_rate():
    from types import SimpleNamespace
    assert rest_rate({}) == DEFAULT_REST_RATE == 0.15
    assert rest_rate({"dimensional": SimpleNamespace(der=SimpleNamespace(base_decay_rate=0.3))}) == 0.3
    assert rest_rate({"dimensional": SimpleNamespace(der=SimpleNamespace(base_decay_rate="x"))}) == DEFAULT_REST_RATE


def test_the_reported_share_is_the_debts_part_of_the_total_owed():
    assert consolidation_share(0.0, 0.2) == 1.0 and consolidation_share(0.5, 0.0) == 0.0
    assert consolidation_share(0.6, 0.2) == pytest.approx(0.25) and consolidation_share(0.0, 0.0) == 0.0


def test_there_is_no_fixed_fraction_left_in_the_module():
    src = open(os.path.join(REPO_ROOT, "aurora_internal", "aurora_rest_ledger.py"), encoding="utf-8").read()
    for gone in ("KEEP_FRACTION", "keep=", "allowance", "pending_gain", "repay=", "repay_left", "PROVISIONAL"):
        assert gone not in src, gone


# ---- the ledger: what consolidation may spend ------------------------------------------------------------------------

def test_recovery_is_credited_in_full_so_there_is_no_charge_and_no_wake_up_cost():
    led = RestLedger(0.4, 0.2)
    led.spend(0.2)
    assert led.net == 0.4 and led.recovery == 0.4


def test_consolidation_may_spend_only_its_own_share_before_the_work_runs():
    led = RestLedger(0.4, 0.2)
    assert led.can_afford(0.2) and not led.can_afford(0.2001)
    assert led.spend(0.15) is True and led.spend(0.06) is False and led.spent == 0.15
    assert led.remaining() == pytest.approx(0.05)


def test_it_never_spends_from_recovery():
    led = RestLedger(10.0, 0.001)
    assert led.spend(0.002) is False and led.net == 10.0


def test_a_negative_cost_is_not_a_refund():
    led = RestLedger(0.0, 1.0)
    assert led.spend(-0.5) is False and led.spent == 0.0


def test_what_earlier_rests_apportioned_and_did_not_spend_is_carried_and_spendable():
    led = RestLedger(0.0, 0.001, carry=0.01)
    assert led.can_afford(0.011) and led.spend(0.011) is True and led.remaining() == pytest.approx(0.0, abs=1e-12)


def test_unspent_share_is_carried_out_and_nothing_else():
    led = RestLedger(0.5, 0.3, carry=0.1)
    led.spend(0.25)
    assert led.carry_out() == pytest.approx(0.15)


def test_capacity_is_everything_this_rest_apportioned():
    led = RestLedger(0.4, 0.2, carry=0.05)
    assert led.capacity == pytest.approx(0.6)      # carry was apportioned in an earlier rest


def test_how_many_units_are_affordable():
    assert RestLedger(0.0, 1.0).affordable_units(0.3) == 3
    assert RestLedger(0.0, 1.0).affordable_units(0.0) == 0 and RestLedger(0.0, 0.0).affordable_units(0.1) == 0


def test_she_received_recovery_only_when_recovery_was_apportioned():
    assert RestLedger(0.1, 0.0).rested is True and RestLedger(0.0, 0.2).rested is False


def test_negative_inputs_are_nothing():
    led = RestLedger(-1.0, -1.0, -1.0)
    assert led.recovery == led.consolidation == led.carry == 0.0


def test_the_report_names_what_was_apportioned_and_spent():
    led = RestLedger(0.4, 0.2, carry=0.1)
    led.spend(0.25)
    assert led.report() == {"recovery": 0.4, "consolidation": 0.2, "capacity": 0.6, "spent": 0.25,
                            "carry_in": 0.1, "carry_out": 0.05, "net": 0.4}


def test_spending_never_exceeds_what_was_apportioned_under_any_sequence():
    rng = random.Random(5)
    for _ in range(300):
        led = RestLedger(rng.random(), rng.random(), carry=rng.random() * 0.2)
        total = led.consolidation + led.carry
        for _ in range(40):
            led.spend(rng.random() * 0.3)
            assert led.spent <= total + 1e-9 and led.remaining() >= 0.0 and led.net == led.recovery


# ---- the cost of core time ---------------------------------------------------------------------------------------------

def test_core_costs_the_multiplier_times_surface():
    assert core_step_cost(300.0, 0.014, 32.0) == pytest.approx(32 * core_step_cost(300.0, 0.014, 1.0))


def test_a_tick_of_surface_lattice_time_costs_one_operating_ticks_wear():
    assert 300 * core_step_cost(300.0, 0.014, 1.0) == pytest.approx(0.014)


def test_no_heartbeat_means_no_affordable_step():
    assert core_step_cost(0.0, 0.014, 32.0) == float("inf")


# ---- funding within a millionth of everything owed is everything owed --------------------------------------------------

def test_settle_completes_a_nearly_complete_funding_and_leaves_the_rest_alone():
    assert settle(0.5, 0.5 * (1 - 1e-7)) == 0.5
    assert settle(0.5, 0.25) == 0.25 and settle(0.5, 0.0) == 0.0
    assert settle(0.0, 0.0) == 0.0 and settle(0.5, 9.0) == 0.5, "it never funds beyond what is owed"


def test_resting_a_tick_at_a_time_no_longer_takes_longer_than_one_long_rest_to_finish():
    """137 closes vs ~88: the snap applied to what is owed overall removes the difference."""
    import math
    from aurora_internal import aurora_rest_ledger as Lm
    owed, funded, ticks = 0.0045, 0.0, 0
    while ticks < 400:
        rec, con = allocate_rest(0.0, owed - funded, 1.0)
        funded = settle(owed, funded + con)
        ticks += 1
        if funded >= owed:
            break
    assert funded == owed and ticks <= math.ceil(math.log(Lm._SNAP) / math.log(1 - DEFAULT_REST_RATE)) + 1

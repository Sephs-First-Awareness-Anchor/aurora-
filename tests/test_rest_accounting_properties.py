"""Randomized histories through the REAL rest steps: the invariants that mean "she wakes rested".

Authors: Sunni (Sir) Morningstar and Cael Devo

These were first found by running 6,178 randomized closes: per-close net was negative in 27% of them (a carried
allowance charged to a gain that was not there) and one repayment exceeded what was owed (a carried leftover
repaid work the fresh repayment had already counted). Both are now impossible; this keeps them so.
"""
import os
import random
import sys
from types import SimpleNamespace

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_consciousness_engine import EntropicPressure  # noqa: E402
from aurora_internal import aurora_metabolic_steps as M  # noqa: E402


class _Clock:
    tick_seconds = 300.0

    def __init__(self):
        self.span = {}

    def should_yield(self):
        return False


class _Contract:
    CORE_QUEUE_MAX = 32

    def __init__(self):
        self.q = 0

    @property
    def core_pending(self):
        return self.q

    def process_core_queue(self, systems, passes=1, afford=None, pay=None, should_stop=None):
        done = 0
        while self.q:
            if afford and not afford(passes):
                break
            self.q -= 1
            if pay:
                pay(passes)
            done += 1
        return {"processed": done, "remaining": self.q, "passes": passes}


def _history(seed):
    rng = random.Random(seed)
    ent = EntropicPressure()
    ent.state.coherence = rng.random()
    s = {"consciousness": SimpleNamespace(entropy=ent), "metabolic_clock": _Clock(),
         "understanding_contract": _Contract(), "lattice": SimpleNamespace(tick=lambda **k: None)}
    for _ in range(rng.randint(5, 60)):
        op = rng.choice([0, 0, 1, 2, 3.5])
        rest = rng.choice([0, 0.5, 1, 1, 2, 12, 96]) if op == 0 else rng.choice([0, 0, 1, 4])
        s["metabolic_clock"].span = {"operating_ticks": op, "rest_ticks": rest, "delta_t": op + rest}
        if op > 0:
            s["understanding_contract"].q = min(32, s["understanding_contract"].q + rng.randint(0, 4))
            ent.erode(op)
        yield s, ent, op, rest


@pytest.mark.parametrize("seed", range(60))
def test_the_rest_invariants_hold_over_a_random_history(seed):
    from aurora_internal.aurora_rest_ledger import allocate_rest, rest_rate
    for s, ent, op, rest in _history(seed):
        before = ent.state.coherence
        M.step_rest_open(op + rest, s)
        led = s.get("_rest_ledger")
        wear, pending = M.recoverable_wear(s), M.pending_core_cost(s)
        carry_in = float(s.get("_rest_credit", 0.0) or 0.0)
        if led is not None:
            carry = min(carry_in, pending)
            debt = max(0.0, pending - carry)
            assert led.recovery <= wear + 1e-9 and led.consolidation <= debt + 1e-9, "never beyond its own need"
            solo_r, solo_c = allocate_rest(wear, 0.0, rest, rest_rate(s))[0], allocate_rest(0.0, debt, rest, rest_rate(s))[1]
            assert led.recovery <= solo_r + 1e-9 and led.consolidation <= solo_c + 1e-9, "one finite capacity"
        M.step_core_understanding(op + rest, s)
        M.step_lattice(op + rest, s)
        if led is not None:
            assert led.spent <= led.consolidation + led.carry + 1e-9, "paid out of consolidation's own share"
            assert led.net == led.recovery >= 0.0, "recovery is credited in full and never charged"
        M.step_rest_close(op + rest, s)
        if led is not None:
            assert s["_rest_credit"] <= M.pending_core_cost(s) + 1e-9, "carried capacity never exceeds what is still owed"
            assert ent.state.coherence == pytest.approx(min(1.0, before + led.recovery), abs=1e-9), "credited in full"
        if op == 0 and rest > 0:
            assert ent.state.coherence >= before - 1e-9, "a rest never leaves her less rested"
        assert ent.state.coherence <= 1.0 + 1e-9


def _full_coherence_system(queued):
    ent = EntropicPressure()
    ent.state.coherence = 1.0
    c = _Contract()
    c.q = queued
    return {"consciousness": SimpleNamespace(entropy=ent), "metabolic_clock": _Clock(), "understanding_contract": c,
            "lattice": SimpleNamespace(tick=lambda **k: None)}, c


def test_a_queue_is_never_starved_forever_at_full_coherence():
    """The exact starvation that was measured: 3 queued, 12 closes, 3 still queued. With only consolidation owed it
    relaxes at the resting rate, so it finishes within the number of ticks that rate needs to resolve to the snap."""
    import math
    from aurora_internal import aurora_rest_ledger as L
    s, c = _full_coherence_system(3)
    # The unfunded part shrinks by (1 - rate) per resting tick and "complete" is within `_SNAP` of what is owed.
    bound = math.ceil(math.log(L._SNAP / 3) / math.log(1.0 - L.DEFAULT_REST_RATE)) + 2
    closes = 0
    while c.q and closes < 4 * bound:
        s["metabolic_clock"].span = {"operating_ticks": 0.0, "rest_ticks": 1.0, "delta_t": 1.0}
        M.step_rest_open(1.0, s)
        M.step_core_understanding(1.0, s)
        M.step_rest_close(1.0, s)
        closes += 1
    assert c.q == 0 and closes <= bound, f"finished in {closes}, bound {bound}"


def test_a_night_consolidates_everything_in_one_close_when_only_consolidation_is_owed():
    s, c = _full_coherence_system(5)
    s["metabolic_clock"].span = {"operating_ticks": 0.0, "rest_ticks": 96.0, "delta_t": 96.0}
    M.step_rest_open(96.0, s)
    M.step_core_understanding(96.0, s)
    M.step_rest_close(96.0, s)
    assert c.q == 0


def test_nothing_owed_means_all_of_the_capacity_restores_her():
    ent = EntropicPressure()
    ent.state.coherence = 0.5
    s = {"consciousness": SimpleNamespace(entropy=ent), "metabolic_clock": _Clock(),
         "understanding_contract": _Contract(), "lattice": SimpleNamespace(tick=lambda **k: None)}
    s["metabolic_clock"].span = {"operating_ticks": 0.0, "rest_ticks": 8.0, "delta_t": 8.0}
    M.step_rest_open(8.0, s)
    led = s["_rest_ledger"]
    assert led.consolidation == 0.0 and led.recovery == pytest.approx(0.5 * (1 - 0.85 ** 8))
    M.step_core_understanding(8.0, s)
    M.step_rest_close(8.0, s)
    assert s["_last_rest"]["spent"] == 0.0 and s["_last_rest"]["net"] == pytest.approx(led.recovery)

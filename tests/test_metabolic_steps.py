"""What a tick does when it closes, and that the fast internal work never makes a turn wait.

Authors: Sunni (Sir) Morningstar and Cael Devo
"""
import os
import sys
import threading
import time
from types import SimpleNamespace

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_internal import aurora_metabolic_steps as M  # noqa: E402
from aurora_internal.aurora_metabolic_clock import MetabolicClock  # noqa: E402


class Clock:
    """Stands in for the clock a step reads: tick length, the span, and the yield request."""
    def __init__(self, tick_seconds=300.0, operating=1.0, rest=0.0, yield_after=None):
        self.tick_seconds = tick_seconds
        self.span = {"operating_ticks": operating, "rest_ticks": rest, "delta_t": operating + rest}
        self._yield_after, self.polls = yield_after, 0

    def should_yield(self):
        self.polls += 1
        return self._yield_after is not None and self.polls >= self._yield_after


class Lattice:
    def __init__(self):
        self.ticks, self.levels = 0, []

    def tick(self, dt=0.1, level=None):
        self.ticks += 1
        self.levels.append(level)


# ---- sediment ---------------------------------------------------------------------------------------

def test_sediment_ages_by_the_whole_elapsed_time_resting_or_not():
    got = []
    systems = {"sedimemory": SimpleNamespace(tick=lambda dt: got.append(dt)), "metabolic_clock": Clock(operating=0.0, rest=96.0)}
    M.step_sediment(96.0, systems)
    assert got == [96.0]


def test_no_sediment_is_not_an_error():
    M.step_sediment(1.0, {})


# ---- entropy ----------------------------------------------------------------------------------------

def _engine():
    calls = []
    ent = SimpleNamespace(erode=lambda n, current_alignment=None: calls.append((n, current_alignment)))
    dmm = SimpleNamespace(state=SimpleNamespace(alignment=0.7))
    return SimpleNamespace(entropy=ent, dimensional=SimpleNamespace(dmm=dmm)), calls


def test_entropy_erodes_per_operating_tick_not_per_elapsed_tick():
    eng, calls = _engine()
    M.step_entropy(96.0, {"consciousness": eng, "metabolic_clock": Clock(operating=1.0, rest=95.0)})
    assert calls == [(1.0, 0.7)]


def test_an_idle_span_does_not_erode_her():
    eng, calls = _engine()
    M.step_entropy(96.0, {"consciousness": eng, "metabolic_clock": Clock(operating=0.0, rest=96.0)})
    assert calls == [(0.0, 0.7)]


def test_entropy_without_an_engine_is_not_an_error():
    M.step_entropy(1.0, {"metabolic_clock": Clock()})


# ---- the Dimensional Energy Regulator ----------------------------------------------------------------

def test_the_der_dissipates_only_while_operating_in_the_same_unit_for_the_presence_monitor():
    got = []
    der = SimpleNamespace(tick=lambda dt, actual_dt=None: got.append((dt, actual_dt)))
    M.step_der(96.0, {"dimensional": SimpleNamespace(der=der), "metabolic_clock": Clock(operating=1.5, rest=94.5)})
    assert got == [(1.5, 1.5)]


def test_a_resting_span_does_not_tick_the_der_at_all():
    got = []
    der = SimpleNamespace(tick=lambda dt, actual_dt=None: got.append(dt))
    M.step_der(96.0, {"dimensional": SimpleNamespace(der=der), "metabolic_clock": Clock(operating=0.0, rest=96.0)})
    assert got == []


def test_a_real_der_survives_a_step_over_a_long_operating_span():
    from aurora_dimensional_systems import EnergyRegulatorSystem, EvolutionTracker
    der = EnergyRegulatorSystem(EvolutionTracker())
    der.facet_energy = {"a": 5.0, "b": 3.0}
    M.step_der(50.0, {"dimensional": SimpleNamespace(der=der), "metabolic_clock": Clock(operating=50.0)})
    assert all(e >= 0.0 for e in der.facet_energy.values())


# ---- rest: gain, consolidation paid out of it, and waking rested ---------------------------------------------

from aurora_consciousness_engine import EntropicPressure  # noqa: E402
from aurora_internal.aurora_rest_ledger import RestLedger, core_step_cost  # noqa: E402

COST = core_step_cost(300.0, EntropicPressure.COHERENCE_DECAY, 32.0)


def _rest_systems(rest=1.0, operating=0.0, gross=10.0, coherence=0.6, **extra):
    ent = EntropicPressure()
    ent.state.coherence = coherence
    systems = {"consciousness": SimpleNamespace(entropy=ent), "lattice": Lattice(),
               "metabolic_clock": Clock(tick_seconds=300.0, operating=operating, rest=rest)}
    systems.update(extra)
    return systems


def test_a_resting_span_opens_a_ledger_and_applies_nothing_to_her_yet():
    s = _rest_systems(rest=2.0, coherence=0.7)
    M.step_rest_open(2.0, s)
    led = s["_rest_ledger"]
    assert led.recovery == pytest.approx(0.3 * (1.0 - 0.85 ** 2)) and led.consolidation == 0.0
    assert s["consciousness"].entropy.state.coherence == 0.7, "credited only when the rest closes"


def test_no_rest_means_no_ledger_and_a_stale_one_is_cleared():
    s = _rest_systems(rest=0.0, operating=1.0)
    s["_rest_ledger"] = RestLedger(0.0, 5.0)
    M.step_rest_open(1.0, s)
    assert "_rest_ledger" not in s


def test_the_resting_rate_is_the_regulators_own_rate_when_it_has_one():
    s = _rest_systems(rest=1.0, coherence=0.5, dimensional=SimpleNamespace(der=SimpleNamespace(base_decay_rate=0.4)))
    M.step_rest_open(1.0, s)
    assert s["_rest_ledger"].recovery == pytest.approx(0.5 * 0.4)


def test_without_a_ledger_the_lattice_runs_no_fast_steps():
    s = _rest_systems()
    M.step_lattice(1.0, s)
    assert s["lattice"].ticks == 0 and s["_lattice_steps_last"] == 0


def test_with_a_ledger_a_resting_tick_is_a_tick_length_of_core_steps():
    s = _rest_systems(rest=1.0)
    s["_rest_ledger"] = RestLedger(0.0, 10.0)
    s["_lattice_step_debt"] = 300.0                    # one operating tick's worth of work is owed
    M.step_lattice(1.0, s)
    assert s["lattice"].ticks == 300 and s["_lattice_steps_last"] == 300
    assert s["_rest_ledger"].spent == pytest.approx(300 * COST)


def test_the_lattice_runs_at_the_core_level_where_it_is_priced_highest():
    from aurora_ivm import RecursionLevel
    s = _rest_systems(rest=0.05)
    s["_rest_ledger"] = RestLedger(0.0, 10.0)
    s["_lattice_step_debt"] = 15.0
    M.step_lattice(0.05, s)
    assert s["lattice"].levels and set(s["lattice"].levels) == {RecursionLevel.CORE}


def test_a_core_step_costs_thirty_two_surface_steps_from_constants_she_already_has():
    surface = core_step_cost(300.0, EntropicPressure.COHERENCE_DECAY, 1.0)
    assert COST == pytest.approx(32 * surface)
    assert 300 * surface == pytest.approx(EntropicPressure.COHERENCE_DECAY), "a tick of surface time = one operating tick's wear"


def test_the_lattice_only_runs_what_its_share_has_paid_for():
    s = _rest_systems(rest=1.0)
    s["_rest_ledger"] = RestLedger(0.0, 5.5 * COST)
    s["_lattice_step_debt"] = 300.0
    M.step_lattice(1.0, s)
    assert s["lattice"].ticks == 5
    assert s["_rest_ledger"].spent <= s["_rest_ledger"].consolidation
    assert s["_lattice_step_debt"] == 295.0, "what she could not afford waits for the next rest"


@pytest.mark.parametrize("share", [0.0, 1e-9, 0.01, 0.123, 0.5, 3.0])
def test_consolidation_never_spends_more_than_its_own_share_and_never_touches_recovery(share):
    s = _rest_systems(rest=4.0)
    s["_rest_ledger"] = RestLedger(0.7, share)
    s["_lattice_step_debt"] = 1200.0
    M.step_lattice(4.0, s)
    led = s["_rest_ledger"]
    assert led.spent <= share + 1e-12
    assert led.net == 0.7, "recovery is untouched by the work"


def test_one_close_is_bounded_and_the_rest_is_debt():
    s = _rest_systems(rest=96.0)
    s["_rest_ledger"] = RestLedger(0.0, 1e6)
    s["_lattice_step_debt"] = 5000.0
    M.step_lattice(96.0, s)
    assert s["lattice"].ticks == M.LATTICE_MAX_STEPS_PER_CLOSE
    assert s["_lattice_step_debt"] == 5000.0 - M.LATTICE_MAX_STEPS_PER_CLOSE


def test_the_debt_is_paid_at_the_next_rest():
    s = _rest_systems(rest=0.0)
    s["_rest_ledger"] = RestLedger(0.0, 10.0)
    s["_lattice_step_debt"] = 200.0
    M.step_lattice(0.0, s)
    assert s["lattice"].ticks == 200 and s["_lattice_step_debt"] == 0.0


def test_a_turn_arriving_stops_the_lattice_between_steps_and_what_was_spent_is_what_ran():
    s = _rest_systems(rest=1.0)
    s["metabolic_clock"] = Clock(tick_seconds=300.0, rest=1.0, yield_after=2)
    s["_rest_ledger"] = RestLedger(0.0, 10.0)
    s["_lattice_step_debt"] = 300.0
    M.step_lattice(1.0, s)
    ran = s["lattice"].ticks
    assert 0 < ran < 300 and ran % M._LATTICE_YIELD_CHECK_EVERY == 0
    assert s["_rest_ledger"].spent == pytest.approx(ran * COST), "never charged for work that did not run"
    assert s["_lattice_step_debt"] == pytest.approx(300 - ran)


def test_a_spent_time_budget_also_stops_it(monkeypatch):
    monkeypatch.setattr(M, "LATTICE_TIME_BUDGET_SECONDS", -1.0)
    s = _rest_systems(rest=1.0)
    s["_rest_ledger"] = RestLedger(0.0, 10.0)
    s["_lattice_step_debt"] = 300.0
    M.step_lattice(1.0, s)
    assert s["lattice"].ticks == M._LATTICE_YIELD_CHECK_EVERY and s["_lattice_step_debt"] > 0


def test_no_lattice_or_no_clock_is_not_an_error():
    s = _rest_systems()
    s["_rest_ledger"] = RestLedger(0.0, 1.0)
    M.step_lattice(1.0, {"metabolic_clock": s["metabolic_clock"], "_rest_ledger": RestLedger(0.0, 1.0)})
    M.step_lattice(1.0, {"lattice": Lattice(), "_rest_ledger": RestLedger(0.0, 1.0)})


def test_waking_credits_what_recovery_received_in_full_whatever_consolidation_spent():
    # Heavy wear and a small debt: consolidation holds only its small share while recovery dominates, then takes
    # over as the wear shrinks. A rest long enough for the shares to turn over funds the work.
    s = _rest_systems(rest=48.0, coherence=0.6)
    s["_lattice_step_debt"] = 300.0 / 32.0
    M.step_rest_open(48.0, s)
    recovery = s["_rest_ledger"].recovery
    M.step_lattice(48.0, s)
    spent = s["_rest_ledger"].spent
    M.step_rest_close(48.0, s)
    assert spent > 0.0, "the work ran, and was paid out of consolidation's own share"
    assert s["consciousness"].entropy.state.coherence == pytest.approx(0.6 + recovery)
    assert "_rest_ledger" not in s


def test_she_wakes_rested_and_already_consolidated():
    s = _rest_systems(rest=96.0, coherence=0.5)
    s["_lattice_step_debt"] = 40.0
    M.step_rest_open(96.0, s)
    M.step_lattice(96.0, s)
    M.step_rest_close(96.0, s)
    r = s["_last_rest"]
    assert r["rested"] is True and r["coherence_after"] > r["coherence_before"]
    assert r["steps"] > 0, "consolidation ran during the rest"
    assert r["spent"] <= r["consolidation"] + r["carry_in"] + 1e-12, "paid out of its own share, before it ran"


def test_a_rest_that_can_only_afford_part_of_the_work_still_leaves_her_no_worse():
    s = _rest_systems(rest=0.1, coherence=0.95)       # barely tired and barely rested: a small capacity
    s["_lattice_step_debt"] = 300.0
    M.step_rest_open(0.1, s)
    M.step_lattice(0.1, s)
    M.step_rest_close(0.1, s)
    r = s["_last_rest"]
    assert r["net"] >= 0.0 and r["spent"] <= r["consolidation"] + 1e-12
    assert r["coherence_after"] >= r["coherence_before"]


def test_a_rested_system_cannot_be_pushed_above_full():
    s = _rest_systems(rest=500.0, coherence=0.999)
    M.step_rest_open(500.0, s)
    M.step_rest_close(500.0, s)
    assert s["consciousness"].entropy.state.coherence <= 1.0


def test_stagnation_eases_over_a_rest():
    s = _rest_systems(rest=10.0)
    s["consciousness"].entropy.state.stagnation_score = 1.0
    M.step_rest_open(10.0, s)
    M.step_rest_close(10.0, s)
    assert s["consciousness"].entropy.state.stagnation_score < 1.0


def test_a_span_with_no_rest_credits_nothing():
    s = _rest_systems(rest=0.0, operating=1.0, coherence=0.6)
    M.step_rest_open(1.0, s)
    M.step_lattice(1.0, s)
    M.step_rest_close(1.0, s)
    assert s["consciousness"].entropy.state.coherence == 0.6 and "_last_rest" not in s


# ---- registration ---------------------------------------------------------------------------------------

def test_every_step_is_registered_in_order_and_entropy_is_handed_to_the_clock():
    clock = MetabolicClock()
    engine = SimpleNamespace(entropy_clock_driven=False)
    M.register_default_steps(clock, {"consciousness": engine})
    assert clock.step_names == ["sediment", "entropy", "der", "governor", "rest_open",
                                "core_understanding", "lattice", "rest_close"]
    assert engine.entropy_clock_driven is True


# ---- the yield request on the real clock ----------------------------------------------------------------

def test_a_turn_arriving_during_a_close_asks_a_preemptible_step_to_stop():
    t = [1000.0]
    clock = MetabolicClock(tick_seconds=300.0, time_source=lambda: t[0], background=True)
    started, saw_yield, done = threading.Event(), threading.Event(), threading.Event()

    def preemptible(dt, systems):
        started.set()
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            if clock.should_yield():
                saw_yield.set()
                break
            time.sleep(0.01)
        done.set()
    clock.register_step("preemptible", preemptible)
    t[0] += 400.0
    with clock.turn():
        pass                                    # starts the background close
    assert started.wait(timeout=3.0)
    th = threading.Thread(target=lambda: clock.turn().__enter__(), daemon=True)
    th.start()
    assert saw_yield.wait(timeout=3.0), "the step must be told a turn is waiting"
    assert done.wait(timeout=3.0)
    th.join(timeout=3.0)


def test_the_yield_request_clears_when_the_close_ends_and_for_the_next_one():
    t = [1000.0]
    clock = MetabolicClock(tick_seconds=300.0, time_source=lambda: t[0])
    clock._yield_requested = True
    t[0] += 400.0
    clock.close_if_due()
    assert clock.should_yield() is False


# ---- demand-driven: what she does, not how long she rests, sets what is owed ---------------------------------

def test_operating_adds_the_core_steps_one_ticks_experience_needs_to_the_backlog():
    s = _rest_systems(rest=0.0, operating=2.0)
    M.step_rest_open(2.0, s)
    assert s["_lattice_step_debt"] == pytest.approx(2.0 * 300.0 / 32.0)


def test_consolidating_a_tick_costs_exactly_what_operating_it_wore():
    """Core time is 32x denser, so a tick of experience needs 1/32 of the steps; each costs 32x. Wear and
    consolidation are priced the same: she pays for what she did, and can always afford it."""
    s = _rest_systems(rest=0.0, operating=1.0)
    M.step_rest_open(1.0, s)
    assert s["_lattice_step_debt"] * COST == pytest.approx(EntropicPressure.COHERENCE_DECAY)


def test_a_debt_slows_recovery_because_both_draw_on_one_finite_capacity():
    owing, free = _rest_systems(rest=12.0, coherence=0.4), _rest_systems(rest=12.0, coherence=0.4)
    owing["_lattice_step_debt"] = 10 * 300.0 / 32.0       # ten operating ticks of experience
    M.step_rest_open(12.0, owing)
    M.step_rest_open(12.0, free)
    assert 0.0 < owing["_rest_ledger"].recovery < free["_rest_ledger"].recovery
    assert owing["_rest_ledger"].consolidation > 0.0 and free["_rest_ledger"].consolidation == 0.0


def test_the_backlog_accumulates_across_operating_closes():
    s = _rest_systems(rest=0.0, operating=1.0)
    M.step_rest_open(1.0, s)
    M.step_rest_open(1.0, s)
    assert s["_lattice_step_debt"] == pytest.approx(2 * 300.0 / 32.0)


def test_resting_alone_adds_no_work():
    s = _rest_systems(rest=96.0, operating=0.0)
    M.step_rest_open(96.0, s)
    assert s.get("_lattice_step_debt", 0.0) == 0.0


def test_the_backlog_is_bounded():
    s = _rest_systems(rest=0.0, operating=1e6)
    M.step_rest_open(1e6, s)
    assert s["_lattice_step_debt"] == float(M.LATTICE_MAX_BACKLOG)


def test_consolidation_pays_the_backlog_down():
    s = _rest_systems(rest=4.0)
    s["_rest_ledger"] = RestLedger(0.0, 10.0)
    s["_lattice_step_debt"] = 250.0
    M.step_lattice(4.0, s)
    assert s["lattice"].ticks == 250 and s["_lattice_step_debt"] == 0.0


def test_with_nothing_to_consolidate_all_of_the_capacity_restores_her():
    s = _rest_systems(rest=8.0, coherence=0.5)
    M.step_rest_open(8.0, s)
    led = s["_rest_ledger"]
    assert led.consolidation == 0.0 and led.recovery == pytest.approx(0.5 * (1 - 0.85 ** 8))
    recovery = led.recovery
    M.step_lattice(8.0, s)
    M.step_rest_close(8.0, s)
    r = s["_last_rest"]
    assert r["spent"] == 0.0 and r["steps"] == 0 and r["net"] == pytest.approx(recovery)


def test_a_rest_with_a_big_backlog_still_leaves_her_rested():
    s = _rest_systems(rest=12.0, coherence=0.4, operating=0.0)
    s["_lattice_step_debt"] = float(M.LATTICE_MAX_BACKLOG)
    M.step_rest_open(12.0, s)
    M.step_lattice(12.0, s)
    M.step_rest_close(12.0, s)
    r = s["_last_rest"]
    assert r["rested"] and r["net"] > 0.0 and r["coherence_after"] > r["coherence_before"]

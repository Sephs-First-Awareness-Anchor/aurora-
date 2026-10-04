"""Three audits of the tick design: the two clocks, starvation at short ticks, and preemption.

Authors: Sunni (Sir) Morningstar and Cael Devo

1. Dual clock. Surface Understanding reacts with the exchange; core Understanding runs on its own cadence
   (rest, paid, governed). Neither secretly drives the other every turn. Found and fixed: a full core queue
   used to RUN its oldest entry on the turn path, so after the 32nd turn of a conversation with no rest every
   turn carried core work.
2. Starvation. A tick short enough that one core tick costs more than a single rest gains must not starve the
   core forever: carried repayment guarantees causal progress.
3. Preemption, not cancellation. When she is mid internal work and the user speaks, she yields at the next safe
   point, promptly, and what is unfinished stays owed and is done exactly once later.
"""
import os
import re
import sys
import threading
import time
from types import SimpleNamespace

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_consciousness_engine import EntropicPressure  # noqa: E402
from aurora_internal import aurora_metabolic_steps as M  # noqa: E402
from aurora_internal.aurora_metabolic_clock import MetabolicClock  # noqa: E402
from aurora_internal.aurora_rest_ledger import RestLedger  # noqa: E402
from aurora_internal.aurora_understanding_contract import RuntimeUnderstandingContract as C  # noqa: E402

UND = {"crystal_level": "understanding", "resolved_accuracy": 0.7, "resolved_cost": 0.1,
       "resolved_boundary_ambiguity": 0.2, "resolved_meaning_topic": "t", "tension_at_resolution": {"total": 0.05}}


def _contract():
    c = C.__new__(C)
    c.records = []
    c._history_append = lambda r: c.records.append(r)
    c.state = {"M": {"active_topic": "t"}, "time_index": 0, "core_queue": []}
    c.persist = False
    c.state_dir = "."
    c.storage_path = os.path.join(".", "x.json")
    c.save = lambda force=False: None
    c.core_deferred = True
    return c


class Spy:
    """Records every call made to it, in one shared log."""
    def __init__(self, log, name):
        self._log, self._name = log, name

    def __getattr__(self, method):
        def call(*a, **k):
            self._log.append(f"{self._name}.{method}")
        return call


class Clock:
    def __init__(self, tick_seconds=300.0, rest=1.0, operating=0.0, yield_after=None):
        self.tick_seconds = tick_seconds
        self.span = {"rest_ticks": rest, "operating_ticks": operating, "delta_t": rest + operating}
        self._yield_after, self.polls = yield_after, 0

    def should_yield(self):
        self.polls += 1
        return self._yield_after is not None and self.polls >= self._yield_after


class Lattice:
    def __init__(self, nap=0.0):
        self.ticks, self.nap = 0, nap

    def tick(self, dt=0.1, level=None):
        self.ticks += 1
        if self.nap:
            time.sleep(self.nap)


def _systems(clock, coherence=0.6, **extra):
    ent = EntropicPressure()
    ent.state.coherence = coherence
    s = {"consciousness": SimpleNamespace(entropy=ent), "metabolic_clock": clock}
    s.update(extra)
    return s


# ============ 1. the two clocks ===========================================================================

SURFACE = ("consciousness.reset_pressure_topology", "consciousness.recalibrate_salience",
           "tensor_expressions.recalibrate_salience", "tensor_expressions.receive_understanding",
           "tensor_expressions.reset_prediction_priors")
CORE = ("sedimemory.geological_write", "identity_field.accept_understanding_update")


def _spied(log):
    return {k: Spy(log, k) for k in ("consciousness", "tensor_expressions", "sedimemory", "identity_field")}


def test_ten_turns_run_the_surface_half_every_turn_and_the_core_half_never():
    log = []
    c = _contract()
    systems = _spied(log)
    for i in range(10):
        c._trigger_downward_cascade(systems, {**UND, "time_index": i})
    for call in SURFACE:
        assert log.count(call) == 10, f"{call} must react to every event"
    for call in CORE:
        assert log.count(call) == 0, f"{call} belongs to the core clock, not the exchange"
    assert c.core_pending == 10, "the surface only HANDED the work over"


def test_the_core_half_runs_in_a_rest_and_never_touches_the_surface_half():
    log = []
    c = _contract()
    systems = _spied(log)
    for i in range(6):
        c._trigger_downward_cascade(systems, {**UND, "time_index": i})
    log.clear()
    c.process_core_queue(systems, passes=1)
    assert log.count("sedimemory.geological_write") == 6
    assert not any(call in log for call in SURFACE), "core consolidation must not re-trigger the surface cascade"
    assert c.core_pending == 0


def test_core_and_surface_are_never_interleaved_while_she_operates():
    log = []
    c = _contract()
    systems = _spied(log)
    for i in range(40):                                  # past the queue limit, no rest at all
        c._trigger_downward_cascade(systems, {**UND, "time_index": i})
    assert not any(call in CORE for call in log), "not even after the queue is full"


def test_an_operating_close_runs_no_core_work_even_with_a_queue():
    c = _contract()
    for i in range(5):
        c._enqueue_core({}, {**UND, "time_index": i})
    s = _systems(Clock(rest=0.0, operating=1.0), understanding_contract=c, sedimemory=SimpleNamespace(),
                 identity_field=SimpleNamespace())
    M.step_rest_open(1.0, s)
    M.step_core_understanding(1.0, s)
    assert s["_core_understanding_last"]["processed"] == 0 and c.core_pending == 5


def test_the_surface_cascade_and_the_turn_path_never_call_the_core_processor():
    src = open(os.path.join(REPO_ROOT, "aurora_internal", "aurora_understanding_contract.py"), encoding="utf-8").read()
    for name in ("run_reflection_cycle", "_trigger_downward_cascade", "_enqueue_core"):
        body = src[src.index(f"def {name}("):]
        body = body[:re.search(r"\n    def ", body[10:]).start() + 10] if re.search(r"\n    def ", body[10:]) else body
        assert "process_core_queue(" not in body and "_run_core_variant(" not in body, name
    live = open(os.path.join(REPO_ROOT, "aurora.py"), encoding="utf-8").read()
    turn = live[live.index("def _run_live_response_turn("):]
    turn = turn[:turn.index("\ndef ", 10)]
    for forbidden in ("process_core_queue", "step_core_understanding", "step_lattice", "step_sediment_dilation"):
        assert forbidden not in turn, f"the turn path must not call {forbidden}"


def test_core_cadence_is_set_by_the_governor_not_by_how_fast_the_user_talks():
    """Same five turns, same rest: a faster core settles each item further (more passes), and only that."""
    def run(factor):
        from aurora_simulation_engine import TimeDilationGovernor
        g = TimeDilationGovernor()
        g.current_dilation = g.START_DILATION * factor
        c = _contract()
        for i in range(5):
            c._enqueue_core({}, {**UND, "time_index": i})
        s = _systems(Clock(), understanding_contract=c, sedimemory=SimpleNamespace(), identity_field=SimpleNamespace(),
                     time_dilation_governor=g, _rest_ledger=RestLedger(0.0, 10.0))
        M.step_core_understanding(1.0, s)
        return s["_core_understanding_last"], s["_rest_ledger"].spent
    slow, slow_cost = run(1.0)
    fast, fast_cost = run(4.0)
    assert slow["passes"] == 1 and fast["passes"] == 4 and slow["processed"] == fast["processed"] == 5
    assert fast_cost == pytest.approx(4 * slow_cost), "a faster core is paid for"


# ============ 2. short-tick starvation ====================================================================

def _drain(tick, coherence, items=5, debt=3.0, limit=400):
    c = _contract()
    for i in range(items):
        c._enqueue_core({}, {**UND, "time_index": i})
    c._run_core_variant = lambda systems, u, passes=1: None
    s = _systems(Clock(tick_seconds=tick, rest=1.0), coherence=coherence, understanding_contract=c,
                 lattice=Lattice(), _lattice_step_debt=debt)
    history = []
    for closes in range(1, limit + 1):
        M.step_rest_open(1.0, s)
        M.step_core_understanding(1.0, s)
        M.step_lattice(1.0, s)
        M.step_rest_close(1.0, s)
        history.append((c.core_pending, s["_lattice_step_debt"]))
        if c.core_pending == 0 and s["_lattice_step_debt"] < 1e-9:
            return closes, history
    return None, history


@pytest.mark.parametrize("tick", [0.5, 1.0, 6.0, 30.0, 300.0, 3600.0])
@pytest.mark.parametrize("coherence", [1.0, 0.6])
def test_the_core_always_makes_causal_progress_at_any_tick_length(tick, coherence):
    closes, history = _drain(tick, coherence)
    assert closes is not None, f"starved forever at tick={tick}s, coherence={coherence}"
    pend = [h[0] for h in history]
    debt = [h[1] for h in history]
    assert pend == sorted(pend, reverse=True) and debt == sorted(debt, reverse=True), "progress only ever moves forward"


def test_a_tick_so_short_that_one_core_tick_costs_more_than_a_rest_gains_still_finishes():
    """The measured failure: tick=6 s, 'steps 0, owed 1.0' on every close."""
    import math
    from aurora_internal import aurora_rest_ledger as Lm
    closes, _ = _drain(6.0, 1.0, items=0, debt=1.0)
    # With only consolidation owed it relaxes at the resting rate, so it finishes within the ticks that rate needs.
    bound = math.ceil(math.log(Lm._SNAP) / math.log(1.0 - Lm.DEFAULT_REST_RATE)) + 2
    assert closes is not None and closes <= bound, f"{closes} closes, bound {bound}"


def test_a_longer_tick_never_finishes_later_and_the_default_finishes_at_the_resting_rates_own_pace():
    """Both needs relax at a common rate between half the resting rate (equally contested) and the whole of it (one
    need alone), so a queue that shares a rest with real wear finishes within the ticks the HALF rate needs to
    resolve to the snap: that is the worst case, 'absorbed through the resting rate', and not a defect."""
    import math
    from aurora_internal import aurora_rest_ledger as Lm
    fast = _drain(300.0, 0.6)[0]
    slow = _drain(1.0, 0.6)[0]
    assert fast is not None and slow is not None and fast <= slow
    worst = math.ceil(math.log(Lm._SNAP) / math.log(1.0 - Lm.DEFAULT_REST_RATE / 2.0)) + 5
    assert fast <= worst, f"{fast} closes, worst-case bound {worst}"


def test_nothing_owed_never_spends_anything_however_short_the_tick():
    c = _contract()
    s = _systems(Clock(tick_seconds=0.5), coherence=1.0, understanding_contract=c, lattice=Lattice())
    for _ in range(20):
        M.step_rest_open(1.0, s)
        M.step_core_understanding(1.0, s)
        M.step_lattice(1.0, s)
        M.step_rest_close(1.0, s)
    assert s["_last_rest"]["spent"] == 0.0 and s["lattice"].ticks == 0


# ============ 3. preemption, not cancellation ===============================================================

def test_a_core_queue_preempted_between_items_is_finished_exactly_once_later():
    c = _contract()
    done = []
    c._run_core_variant = lambda systems, u, passes=1: done.append(u["time_index"])
    for i in range(10):
        c._enqueue_core({}, {**UND, "time_index": i})
    s = _systems(Clock(yield_after=4), understanding_contract=c, _rest_ledger=RestLedger(0.0, 100.0))
    M.step_core_understanding(1.0, s)
    assert 0 < len(done) < 10 and c.core_pending == 10 - len(done), "it stopped, and what is left stays queued"
    s["metabolic_clock"] = Clock(yield_after=None)
    s["_rest_ledger"] = RestLedger(0.0, 100.0)
    M.step_core_understanding(1.0, s)
    assert done == list(range(10)), "every item exactly once, in order: neither cancelled nor repeated"
    assert c.core_pending == 0


def test_an_item_is_never_stopped_halfway():
    c = _contract()
    seen = []

    def run(systems, u, passes=1):
        seen.append(("begin", u["time_index"]))
        seen.append(("end", u["time_index"]))
    c._run_core_variant = run
    for i in range(6):
        c._enqueue_core({}, {**UND, "time_index": i})
    s = _systems(Clock(yield_after=3), understanding_contract=c, _rest_ledger=RestLedger(0.0, 100.0))
    M.step_core_understanding(1.0, s)
    assert [k for k, _ in seen] == ["begin", "end"] * (len(seen) // 2)


def test_a_preempted_lattice_keeps_exactly_what_is_unfinished_even_mid_unit():
    from aurora_simulation_engine import TimeDilationGovernor
    g = TimeDilationGovernor()
    g.current_dilation = g.START_DILATION * 2.0                 # two core ticks per owed unit
    s = _systems(Clock(yield_after=7), lattice=Lattice(), time_dilation_governor=g,
                 _lattice_step_debt=10.0, _rest_ledger=RestLedger(0.0, 100.0))
    M.step_lattice(1.0, s)
    assert s["lattice"].ticks == 7 and s["_lattice_step_debt"] == pytest.approx(10.0 - 7 / 2), "a unit half done is half owed"
    s["metabolic_clock"] = Clock(yield_after=None)
    s["_rest_ledger"] = RestLedger(0.0, 100.0)
    M.step_lattice(1.0, s)
    assert s["lattice"].ticks == 20 and s["_lattice_step_debt"] == pytest.approx(0.0), "20 ticks in total, none twice"


def test_a_real_turn_arriving_during_real_internal_work_is_released_promptly_and_nothing_is_lost(tmp_path):
    t = [1_000_000.0]
    clock = MetabolicClock(tick_seconds=300.0, time_source=lambda: t[0], state_path=str(tmp_path / "c.json"))
    lattice = Lattice(nap=0.02)                                  # each lattice tick takes 20 ms
    systems = _systems(clock, coherence=0.5, lattice=lattice, _lattice_step_debt=60.0)
    clock.bind(systems)
    clock.register_step("rest_open", M.step_rest_open)
    clock.register_step("lattice", M.step_lattice)
    clock.register_step("rest_close", M.step_rest_close)

    t[0] += 12 * 300.0                                           # an hour of rest is due
    box = {}
    worker = threading.Thread(target=lambda: box.update(report=clock.close_if_due(systems)), daemon=True)
    worker.start()
    deadline = time.monotonic() + 3.0
    while lattice.ticks < 3 and time.monotonic() < deadline:
        time.sleep(0.005)
    assert lattice.ticks >= 3, "internal work is under way"

    arrived = time.monotonic()
    with clock.turn():                                           # the user speaks
        released = time.monotonic() - arrived
    worker.join(timeout=3.0)
    ran_when_released = lattice.ticks
    assert released < 0.25, f"the turn waited {released:.3f}s: it must be released at the next lattice tick, not after 60"
    assert ran_when_released < 60, "internal work yielded instead of running to completion"
    assert systems["_lattice_step_debt"] == pytest.approx(60.0 - ran_when_released)
    assert box["report"]["steps"]["lattice"]["ok"], "it was preempted, not killed"

    # the unfinished work is still owed and is done later, exactly once. (Wear and the debt share one finite
    # capacity, so it takes a long rest, not an hour, to fund all of it; the point is once, never repeated.)
    t[0] += 120 * 300.0
    clock.close_if_due(systems)
    expected = 60.0 + 1 * 300.0 / 32.0                           # what was owed + what the turn's operating produced
    assert lattice.ticks == pytest.approx(expected, abs=1.5)
    assert systems["_lattice_step_debt"] == pytest.approx(0.0, abs=1.0)


def test_the_yield_request_reaches_the_step_without_the_turn_waiting_for_a_whole_close():
    """The turn gate sets the request the moment a close is running; it does not wait for the close to end first."""
    clock = MetabolicClock(tick_seconds=300.0, time_source=lambda: 0.0)
    clock._closing = True
    waiter = threading.Thread(target=lambda: clock.turn().__enter__(), daemon=True)
    waiter.start()
    deadline = time.monotonic() + 2.0
    while not clock.should_yield() and time.monotonic() < deadline:
        time.sleep(0.005)
    assert clock.should_yield() is True
    with clock._cv:
        clock._closing = False
        clock._cv.notify_all()
    waiter.join(timeout=2.0)


def test_internal_work_is_the_subsystems_and_the_turn_is_the_surfaces():
    """A preempted close leaves the internal obligations IN the subsystems that own them (the contract's queue, the
    lattice's backlog); it does not convert them into surface work or drop them."""
    c = _contract()
    for i in range(4):
        c._enqueue_core({}, {**UND, "time_index": i})
    c._run_core_variant = lambda systems, u, passes=1: None
    s = _systems(Clock(yield_after=1), understanding_contract=c, lattice=Lattice(), _lattice_step_debt=8.0,
                 _rest_ledger=RestLedger(0.0, 100.0))
    M.step_core_understanding(1.0, s)
    M.step_lattice(1.0, s)
    assert c.core_pending == 4 and s["_lattice_step_debt"] == pytest.approx(8.0 - s["lattice"].ticks)
    assert "core_queue" in c.state and s["_lattice_step_debt"] > 0

"""Understanding on two clocks: the exchange (surface) and the core.

Authors: Sunni (Sir) Morningstar and Cael Devo

The deep half of the cascade (the geological write, then identity shaped by what the strata hold) runs on the
core clock during rest: faster than the exchange, paid out of the rest, stopped between items if a turn arrives.
Dilation speeds PROCESSING (passes of settling). It is not attached to sediment: that would fast-forward how
memory ages (measured below), a design decision left to Sunni.
"""
import os
import sys
from types import SimpleNamespace

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_internal import aurora_metabolic_steps as M  # noqa: E402
from aurora_internal.aurora_rest_ledger import RestLedger  # noqa: E402
from aurora_internal.aurora_understanding_contract import RuntimeUnderstandingContract as C  # noqa: E402
from aurora_manifold_directory.noncomp_field import NoncompField  # noqa: E402
from aurora_sedimemory import SediMemory  # noqa: E402

UND = {"crystal_level": "understanding", "resolved_accuracy": 0.7, "resolved_cost": 0.1,
       "resolved_boundary_ambiguity": 0.2, "resolved_meaning_topic": "photosynthesis",
       "tension_at_resolution": {"total": 0.05}, "time_index": 4}


def _contract(deferred=False, persist=False, state_dir=None):
    c = C.__new__(C)
    c.records = []
    c._history_append = lambda r: c.records.append(r)
    c.state = {"M": {"active_topic": "photosynthesis"}, "time_index": 4, "core_queue": []}
    c.persist = persist
    c.state_dir = state_dir or "."
    c.storage_path = os.path.join(c.state_dir, "understanding_contract_state.json")
    c.core_deferred = deferred
    return c


class Spy:
    """Records which of the cascade's receivers ran, in order."""
    def __init__(self, log, **names):
        self.log = log
        for name in names:
            setattr(self, name, self._make(name))

    def _make(self, name):
        def fn(*a, **k):
            self.log.append(name)
        return fn


def _surface_spy(log):
    return Spy(log, reset_pressure_topology=1, recalibrate_salience=1)


# ---- the cascade defers only the deep half ------------------------------------------------------------------

def test_a_deferred_cascade_queues_the_deep_half_and_writes_nothing_yet():
    c = _contract(deferred=True)
    mem, field = SediMemory(), NoncompField()
    before = dict(field._baseline)
    n0 = len(mem.get_all_fragments()) if hasattr(mem, "get_all_fragments") else None
    c._trigger_downward_cascade({"sedimemory": mem, "identity_field": field}, dict(UND))
    d = c.records[-1]["dispatches"]
    assert "core_variant:queued" in d
    assert not any("geological_write" in x for x in d) and not any("accept_understanding_update" in x for x in d)
    assert field._baseline == before, "identity is not shaped yet: it waits for the core clock"
    assert c.core_pending == 1


def test_the_immediate_half_still_runs_with_the_exchange():
    log = []
    c = _contract(deferred=True)
    c._trigger_downward_cascade({"consciousness": _surface_spy(log), "tensor_expressions": Spy(log, recalibrate_salience=1)}, dict(UND))
    assert "reset_pressure_topology" in log and "recalibrate_salience" in log
    assert c.core_pending == 1


def test_without_a_clock_both_halves_run_inline_exactly_as_before():
    c = _contract(deferred=False)
    mem, field = SediMemory(), NoncompField()
    c._trigger_downward_cascade({"sedimemory": mem, "identity_field": field}, dict(UND))
    d = c.records[-1]["dispatches"]
    assert "sedimemory.geological_write:ok" in d and "identity_field.accept_understanding_update:ok" in d
    assert c.core_pending == 0 and "core_variant:queued" not in d


def test_the_class_default_is_inline_so_nothing_changes_unless_a_clock_is_attached():
    assert C.core_deferred is False


# ---- the core variant ------------------------------------------------------------------------------------------

def test_the_core_variant_writes_memory_first_then_shapes_identity():
    log = []
    c = _contract(deferred=True)
    mem = SediMemory()
    orig = mem.geological_write
    mem.geological_write = lambda u: (log.append("write"), orig(u))[1]
    field = NoncompField()
    orig_id = field.accept_understanding_update
    field.accept_understanding_update = lambda u: (log.append("identity"), orig_id(u))[1]
    c._enqueue_core({}, dict(UND))
    c.process_core_queue({"sedimemory": mem, "identity_field": field})
    assert log == ["write", "identity"]


def test_identity_is_shaped_by_what_the_write_just_laid_down():
    c = _contract(deferred=True)
    mem, field = SediMemory(), NoncompField()
    seen = {}
    orig = field.accept_understanding_update
    field.accept_understanding_update = lambda u: (seen.update(deep=dict(u.get("deep_memory") or {})), orig(u))[1]
    before = mem.deep_axis_weights()
    c._enqueue_core({}, dict(UND))
    c.process_core_queue({"sedimemory": mem, "identity_field": field})
    assert seen["deep"] == mem.deep_axis_weights() and seen["deep"] != before


def test_the_geological_write_happens_once_however_many_passes():
    c = _contract(deferred=True)
    mem, field = SediMemory(), NoncompField()
    writes = []
    orig = mem.geological_write
    mem.geological_write = lambda u: (writes.append(1), orig(u))[1]
    c._enqueue_core({}, dict(UND))
    c.process_core_queue({"sedimemory": mem, "identity_field": field}, passes=6)
    assert len(writes) == 1, "extra passes settle identity; they must never deposit memory twice"


def test_more_passes_settle_identity_geometrically_further_toward_what_memory_weighs():
    def baseline_after(passes):
        c = _contract(deferred=True)
        mem, field = SediMemory(), NoncompField()
        c._enqueue_core({}, dict(UND))
        c.process_core_queue({"sedimemory": mem, "identity_field": field}, passes=passes)
        return dict(field._baseline), mem.deep_axis_weights()

    one, deep = baseline_after(1)
    four, _ = baseline_after(4)
    start = dict(NoncompField()._baseline)
    total = sum(deep.values())
    from aurora_manifold_directory.noncomp_field import REFERENCE_AXIS_PRESSURE
    axes = list(deep.keys())
    idx = {a: i for i, a in enumerate(["X", "T", "N", "B", "A"])}
    rate = 0.10 + 0.20 * 0.7
    for a in axes:
        i = idx.get(a)
        if i is None:
            continue
        target = REFERENCE_AXIS_PRESSURE * 5.0 * (deep[a] / total)
        assert abs(four[i] - target) <= abs(one[i] - target) + 1e-12
        assert abs(four[i] - target) == pytest.approx(abs(start[i] - target) * (1 - rate) ** 4, rel=1e-6)


def test_the_total_baseline_is_conserved_however_many_passes():
    c = _contract(deferred=True)
    mem, field = SediMemory(), NoncompField()
    total0 = sum(field._baseline.values())
    c._enqueue_core({}, dict(UND))
    c.process_core_queue({"sedimemory": mem, "identity_field": field}, passes=8)
    assert sum(field._baseline.values()) == pytest.approx(total0)


def test_a_system_under_two_keys_is_shaped_once_per_pass():
    c = _contract(deferred=True)
    mem, field = SediMemory(), NoncompField()
    calls = []
    orig = field.accept_understanding_update
    field.accept_understanding_update = lambda u: (calls.append(1), orig(u))[1]
    c._enqueue_core({}, dict(UND))
    c.process_core_queue({"sedimemory": mem, "identity_field": field, "behavioral_identity": field}, passes=3)
    assert len(calls) == 3


def test_a_receiver_that_raises_does_not_stop_the_rest_or_wedge_the_queue():
    c = _contract(deferred=True)
    mem = SediMemory()
    bad = SimpleNamespace(accept_understanding_update=lambda u: (_ for _ in ()).throw(RuntimeError("x")))
    c._enqueue_core({}, dict(UND))
    out = c.process_core_queue({"sedimemory": mem, "identity_field": bad})
    assert out["processed"] == 1 and c.core_pending == 0


def test_the_core_variant_with_nothing_attached_is_not_an_error():
    c = _contract(deferred=True)
    c._enqueue_core({}, dict(UND))
    assert c.process_core_queue({})["processed"] == 1


# ---- paid for, and preemptible ----------------------------------------------------------------------------------

def test_it_asks_before_each_item_and_pays_after_never_running_unpaid():
    events = []
    c = _contract(deferred=True)
    for _ in range(2):
        c._enqueue_core({}, dict(UND))
    c._run_core_variant = lambda s, u, passes=1: events.append("run")
    c.process_core_queue({}, passes=3, afford=lambda n: (events.append(f"afford{n}"), True)[1],
                         pay=lambda n: events.append(f"pay{n}"))
    assert events == ["afford3", "run", "pay3", "afford3", "run", "pay3"]


def test_what_she_cannot_afford_stays_queued_for_the_next_rest():
    c = _contract(deferred=True)
    for _ in range(3):
        c._enqueue_core({}, dict(UND))
    budget = [1]
    out = c.process_core_queue({"sedimemory": SediMemory()}, afford=lambda n: budget[0] > 0,
                               pay=lambda n: budget.__setitem__(0, budget[0] - 1))
    assert out == {"processed": 1, "remaining": 2, "passes": 1} and c.core_pending == 2


def test_a_turn_arriving_stops_it_between_items_never_mid_item():
    c = _contract(deferred=True)
    for _ in range(4):
        c._enqueue_core({}, dict(UND))
    ran, polls = [], [0]
    c._run_core_variant = lambda s, u, passes=1: ran.append(1)

    def stop():
        polls[0] += 1
        return polls[0] > 2
    out = c.process_core_queue({}, should_stop=stop)
    assert len(ran) == 2 and out["remaining"] == 2


# ---- the queue is bounded, persisted and never loses a memory -------------------------------------------------

def test_a_full_queue_coalesces_its_oldest_and_runs_nothing_on_the_turn_path():
    """It used to RUN the oldest here: after the thirty-second turn of a conversation with no rest, every turn
    carried a core variant on its own path (the surface secretly driving the core)."""
    c = _contract(deferred=True)
    mem = SediMemory()
    writes = []
    orig = mem.geological_write
    mem.geological_write = lambda u: (writes.append(u.get("time_index")), orig(u))[1]
    systems = {"sedimemory": mem}
    for i in range(C.CORE_QUEUE_MAX + 3):
        c._enqueue_core(systems, {**UND, "time_index": i})
    assert c.core_pending == C.CORE_QUEUE_MAX
    assert writes == [], "no core work ran while she was operating"
    assert c.state["core_coalesced"] == 3


def test_coalescing_conserves_how_many_turns_the_queue_stands_for():
    c = _contract(deferred=True)
    for i in range(C.CORE_QUEUE_MAX + 40):
        c._enqueue_core({}, {**UND, "time_index": i})
    assert sum(int(u.get("coalesced", 1)) for u in c.state["core_queue"]) == C.CORE_QUEUE_MAX + 40


def test_a_coalesced_item_is_the_weighted_blend_with_the_newest_index():
    older = {**UND, "resolved_accuracy": 0.2, "tension_at_resolution": {"total": 0.1}, "time_index": 1, "coalesced": 3}
    newer = {**UND, "resolved_accuracy": 0.6, "tension_at_resolution": {"total": 0.5}, "time_index": 9,
             "resolved_meaning_topic": "newer topic"}
    m = C._merge_understandings(older, newer)
    assert m["resolved_accuracy"] == pytest.approx((0.2 * 3 + 0.6 * 1) / 4)
    assert m["tension_at_resolution"]["total"] == pytest.approx((0.1 * 3 + 0.5 * 1) / 4)
    assert m["time_index"] == 9 and m["coalesced"] == 4 and m["resolved_meaning_topic"] == "newer topic"
    assert m["crystal_level"] == "understanding", "the justification the deep write needs survives the merge"


def test_merging_never_treats_a_flag_as_a_number_or_loses_a_key():
    m = C._merge_understandings({"a": True, "only_old": 1, "x": 1.0}, {"a": False, "only_new": 2, "x": 3.0})
    assert m["a"] is False and m["only_old"] == 1 and m["only_new"] == 2 and m["x"] == pytest.approx(2.0)


def test_a_coalesced_item_is_still_written_justified_when_the_core_gets_to_it():
    c = _contract(deferred=True)
    mem = SediMemory()
    systems = {"sedimemory": mem}
    for i in range(C.CORE_QUEUE_MAX + 5):
        c._enqueue_core(systems, {**UND, "time_index": i})
    before = mem.deep_axis_weights()
    c.process_core_queue(systems, passes=1)
    assert c.core_pending == 0 and mem.deep_axis_weights() != before


def test_two_hundred_turns_with_no_rest_run_zero_core_variants():
    c = _contract(deferred=True)
    calls = []
    c._run_core_variant = lambda systems, u, passes=1: calls.append(u)
    for i in range(200):
        c._enqueue_core({}, {**UND, "time_index": i})
    assert calls == [] and c.core_pending == C.CORE_QUEUE_MAX


def test_the_queue_survives_a_restart(tmp_path):
    a = C(state_dir=str(tmp_path), persist=True)
    a.core_deferred = True
    a._enqueue_core({}, {**UND, "time_index": 41})
    a.save(force=True)
    b = C(state_dir=str(tmp_path), persist=True)
    assert b.core_pending == 1 and b.state["core_queue"][0]["time_index"] == 41


def test_processing_saves_the_emptied_queue(tmp_path):
    a = C(state_dir=str(tmp_path), persist=True)
    a.core_deferred = True
    a._enqueue_core({}, dict(UND))
    a.save(force=True)
    a.process_core_queue({"sedimemory": SediMemory()})
    assert C(state_dir=str(tmp_path), persist=True).core_pending == 0


def test_a_fresh_contract_has_an_empty_queue():
    assert C(state_dir=".", persist=False).state["core_queue"] == []


# ---- the governor: fast when stable, slow when fragile ------------------------------------------------------------

def _gov():
    from aurora_simulation_engine import TimeDilationGovernor
    return TimeDilationGovernor()


def _sys(coherence=0.9, governor=None, last=None):
    ent = SimpleNamespace(state=SimpleNamespace(coherence=coherence), COHERENCE_DECAY=0.014)
    clock = SimpleNamespace(tick_seconds=300.0, last_report=last or {}, should_yield=lambda: False,
                            span={"rest_ticks": 1.0, "operating_ticks": 0.0})
    return {"consciousness": SimpleNamespace(entropy=ent), "metabolic_clock": clock,
            "time_dilation_governor": governor}


def test_the_governor_reads_her_coherence_as_fitness():
    g = _gov()
    m = M.stability_metrics(_sys(0.73, g), g)
    assert m.fitness_mean == pytest.approx(0.73) and m.coherence_score == pytest.approx(0.73)


def test_failed_steps_in_the_last_close_are_the_error_rate():
    g = _gov()
    last = {"steps": {"a": {"ok": True}, "b": {"ok": False}, "c": {"ok": True}, "d": {"ok": False}}}
    assert M.stability_metrics(_sys(0.9, g, last), g).error_rate == pytest.approx(0.5)
    assert M.stability_metrics(_sys(0.9, g, {}), g).error_rate == 0.0


def test_steady_coherence_has_no_variance():
    g = _gov()
    for _ in range(6):
        g.fitness_history.append(0.8)
    assert M.stability_metrics(_sys(0.8, g), g).fitness_variance == pytest.approx(0.0, abs=1e-12)


def test_sustained_health_lets_the_core_think_faster_and_only_then():
    s = _sys(0.9, _gov())
    assert M.dilation_factor(s) == 1.0 and M.core_passes(s) == 1
    for _ in range(12):
        M.step_governor(1.0, s)
    assert M.dilation_factor(s) > 1.5 and M.core_passes(s) > 1


def test_a_collapse_brakes_it_and_it_never_goes_below_baseline():
    s = _sys(0.9, _gov())
    for _ in range(12):
        M.step_governor(1.0, s)
    fast = M.dilation_factor(s)
    s["consciousness"].entropy.state.coherence = 0.05
    for _ in range(40):
        M.step_governor(1.0, s)
    assert M.dilation_factor(s) < fast and M.dilation_factor(s) == 1.0
    assert M.core_passes(s) == 1


def test_the_core_never_gets_more_than_the_pass_bound():
    s = _sys(0.9, _gov())
    s["time_dilation_governor"].current_dilation = s["time_dilation_governor"].MAX_DILATION
    assert M.core_passes(s) == M.CORE_MAX_PASSES


def test_no_governor_means_baseline_one_pass_and_no_error():
    s = _sys(0.9, None)
    M.step_governor(1.0, s)
    assert M.dilation_factor(s) == 1.0 and M.core_passes(s) == 1


# ---- dilation never touches how fast memory decays --------------------------------------------------------------

def test_registration_does_not_attach_the_governor_to_sediment():
    """Attached, SediMemory.tick scales memory's clock by the dilation and fast-forwards geological promotion
    (see the control below). Whether she should age memory faster is a design decision, so it stays off."""
    class Clock:
        def register_step(self, *a):
            pass
    sedi = SediMemory()
    systems = {"sedimemory": sedi, "consciousness": SimpleNamespace(), "understanding_contract": _contract()}
    M.register_default_steps(Clock(), systems)
    assert getattr(sedi, "_dilation", None) is None
    assert systems["time_dilation_governor"] is not None


def _aged(sedi):
    sedi.geological_write(dict(UND))
    sedi.tick(1.0)
    return sedi.deep_axis_weights()


def test_a_high_dilation_does_not_change_how_far_sediment_ages():
    class Clock:
        def register_step(self, *a):
            pass
    plain = _aged(SediMemory())
    registered = SediMemory()
    systems = {"sedimemory": registered, "consciousness": SimpleNamespace(), "understanding_contract": _contract()}
    M.register_default_steps(Clock(), systems)
    gov = systems["time_dilation_governor"]
    gov.current_dilation = gov.MAX_DILATION
    assert _aged(registered) == plain, "registration must leave memory's decay on real time"


def test_even_attaching_the_governor_at_maximum_dilation_does_not_fast_forward_deep_memory():
    """Sir's decision: sediment ages by elapsed time only. This used to be a control proving the old behavior could
    happen (three understandings' deep mass 30 at real time, 41 after ONE tick at maximum dilation, 47 over a night:
    depth she did not earn). Now the same attach changes nothing."""
    from aurora_simulation_engine import TimeDilationGovernor
    plain = _aged(SediMemory())
    gov = TimeDilationGovernor()
    gov.current_dilation = gov.MAX_DILATION
    attached = _aged(SediMemory(time_dilation=gov))
    assert attached == plain and sum(attached.values()) == sum(plain.values())


def test_registration_defers_the_deep_half_and_leaves_a_contract_without_a_queue_alone():
    class Clock:
        def register_step(self, *a):
            pass
    c = _contract()
    M.register_default_steps(Clock(), {"understanding_contract": c})
    assert c.core_deferred is True
    legacy = SimpleNamespace()
    M.register_default_steps(Clock(), {"understanding_contract": legacy})
    assert not hasattr(legacy, "core_deferred")


# ---- the core step, paid out of the rest ----------------------------------------------------------------------

def _core_sys(n_queued=3, gross=10.0, coherence=0.9, governor=None):
    s = _sys(coherence, governor)
    c = _contract(deferred=True)
    for i in range(n_queued):
        c._enqueue_core({}, {**UND, "time_index": i})
    s.update(understanding_contract=c, sedimemory=SediMemory(), identity_field=NoncompField(),
             _rest_ledger=RestLedger(0.0, gross))
    return s, c


def test_a_rest_runs_the_queued_core_variants_and_pays_for_them():
    s, c = _core_sys(3, gross=10.0)
    M.step_core_understanding(1.0, s)
    last = s["_core_understanding_last"]
    assert last["processed"] == 3 and last["remaining"] == 0 and c.core_pending == 0
    assert s["_rest_ledger"].spent == pytest.approx(3 * 1 * M.core_tick_cost(s))


def test_each_item_costs_its_passes_so_a_faster_core_is_paid_for():
    s, c = _core_sys(2, gross=10.0, governor=_gov())
    for _ in range(14):
        M.step_governor(1.0, s)
    passes = M.core_passes(s)
    assert passes > 1
    M.step_core_understanding(1.0, s)
    assert s["_rest_ledger"].spent == pytest.approx(2 * passes * M.core_tick_cost(s))
    assert s["_core_understanding_last"]["passes"] == passes


def test_it_runs_only_what_its_share_can_pay_and_never_touches_recovery():
    one_item = 1 * M.core_tick_cost(_sys(0.9))
    s, c = _core_sys(5, gross=2.5 * one_item)           # consolidation's share funds 2.5 items
    s["_rest_ledger"] = RestLedger(0.7, 2.5 * one_item)
    M.step_core_understanding(1.0, s)
    led = s["_rest_ledger"]
    assert s["_core_understanding_last"]["processed"] == 2 and c.core_pending == 3
    assert led.spent <= led.consolidation and led.net == 0.7, "recovery is untouched by the work"


def test_no_rest_means_no_core_understanding_and_the_queue_waits():
    s, c = _core_sys(2)
    s.pop("_rest_ledger")
    M.step_core_understanding(1.0, s)
    assert c.core_pending == 2 and s["_core_understanding_last"]["processed"] == 0


def test_a_turn_arriving_stops_the_core_step_between_items():
    s, c = _core_sys(4)
    polls = [0]
    s["metabolic_clock"].should_yield = lambda: (polls.__setitem__(0, polls[0] + 1), polls[0] > 1)[1]
    M.step_core_understanding(1.0, s)
    assert s["_core_understanding_last"]["processed"] == 1 and c.core_pending == 3


def test_a_contract_without_the_core_variant_is_skipped():
    s, _ = _core_sys(1)
    s["understanding_contract"] = SimpleNamespace()
    M.step_core_understanding(1.0, s)
    assert s["_core_understanding_last"]["processed"] == 0


def test_the_lattice_and_core_understanding_share_one_price():
    s, _ = _core_sys(1)
    from aurora_internal.aurora_rest_ledger import core_step_cost
    assert M.core_tick_cost(s) == pytest.approx(core_step_cost(300.0, 0.014, M.core_multiplier()))


# ---- she is not worn, but she still wakes consolidated ----------------------------------------------------------------

def _rest_close(s):
    M.step_rest_open(1.0, s)
    M.step_core_understanding(1.0, s)
    M.step_rest_close(1.0, s)


def _rested_sys(n_queued, coherence=1.0, rest=1.0):
    s, c = _core_sys(n_queued)
    s.pop("_rest_ledger")
    s["metabolic_clock"].span = {"rest_ticks": rest, "operating_ticks": 0.0, "delta_t": rest}
    s["consciousness"].entropy = __import__("aurora_consciousness_engine").EntropicPressure()
    s["consciousness"].entropy.state.coherence = coherence
    return s, c


def test_the_pending_consolidation_is_funded_even_when_she_is_already_full():
    """Measured: a short conversation left coherence at 1.000 (reconciled turns earn it back), so the rest had no
    wear to recover: 3 queued, 12 closes, 3 still queued. With recovery complete, all of the capacity goes to
    consolidation."""
    s, c = _rested_sys(3, coherence=1.0, rest=12.0)
    M.step_rest_open(12.0, s)
    expected = M.pending_core_cost(s) * (1 - 0.85 ** 12)
    ledger = s["_rest_ledger"]
    assert expected > 0
    assert ledger.recovery == 0.0, "full coherence: nothing to recover"
    assert ledger.consolidation == pytest.approx(expected), "all of the capacity goes to consolidation"
    assert ledger.remaining() == pytest.approx(expected)


def test_a_queue_is_fully_consolidated_over_idle_closes_even_at_full_coherence():
    """The exact starvation, reproduced as it was measured (nothing worn, heartbeat-sized rests). With only
    consolidation owed it relaxes at the resting rate, so it converges rather than finishing at once, within the
    number of ticks that rate needs to resolve to the snap."""
    import math
    from aurora_internal import aurora_rest_ledger as Lm
    bound = math.ceil(math.log(Lm._SNAP / 3) / math.log(1.0 - Lm.DEFAULT_REST_RATE)) + 2
    s, c = _rested_sys(3, coherence=1.0, rest=1.0)
    sizes = [c.core_pending]
    while c.core_pending and len(sizes) < 4 * bound:
        _rest_close(s)
        sizes.append(c.core_pending)
    assert c.core_pending == 0, "no queued understanding may be priced out forever"
    assert sizes == sorted(sizes, reverse=True), "the queue only ever shrinks"
    assert len(sizes) <= bound + 1


def test_one_long_idle_close_consolidates_the_whole_queue_at_once():
    s, c = _rested_sys(3, coherence=1.0, rest=96.0)
    _rest_close(s)
    assert c.core_pending == 0


def test_the_last_item_is_not_priced_out_by_its_own_size():
    s, c = _rested_sys(1, coherence=1.0, rest=1.0)
    closes = 0
    while c.core_pending and closes < 120:
        _rest_close(s)
        closes += 1
    assert c.core_pending == 0 and closes > 1, "it needed capacity carried across rests, which is the point"


def test_unspent_allowance_is_carried_to_the_next_rest_and_bounded():
    s, _ = _rested_sys(1, coherence=0.5, rest=50.0)         # something is owed, so consolidation has a share
    _rest_close(s)
    assert s["_rest_credit"] > 0
    assert s["_rest_credit"] <= M.credit_cap(s) + 1e-12
    s["_rest_credit"] = 1e9
    _rest_close(s)
    assert s["_rest_credit"] <= M.credit_cap(s) + 1e-12


def test_the_next_ledger_opens_with_the_carry_and_never_more_than_is_still_owed():
    s, _ = _rested_sys(1, coherence=0.9, rest=1.0)
    owed = M.pending_core_cost(s)
    s["_rest_credit"] = owed / 4
    M.step_rest_open(1.0, s)
    assert s["_rest_ledger"].carry == pytest.approx(owed / 4)
    s["_rest_credit"] = owed * 10                         # a stale credit larger than what is owed is clipped
    M.step_rest_open(1.0, s)
    assert s["_rest_ledger"].carry == pytest.approx(owed)
    empty, _ = _rested_sys(0, coherence=0.9, rest=1.0)
    empty["_rest_credit"] = 0.02
    M.step_rest_open(1.0, empty)
    assert empty["_rest_ledger"].carry == 0.0, "nothing owed: nothing to carry"


def test_across_many_rests_consolidation_never_spends_more_than_was_apportioned_to_it():
    """Cumulatively, even with carried capacity: what was spent never exceeds what consolidation was apportioned,
    and recovery is always credited in full."""
    import random
    rng = random.Random(11)
    s, c = _rested_sys(0, coherence=0.7, rest=1.0)
    apportioned = spent = 0.0
    for step in range(120):
        for _ in range(rng.randint(0, 2)):
            c._enqueue_core({}, {**UND, "time_index": step})
        s["metabolic_clock"].span = {"rest_ticks": rng.choice([0.5, 1.0, 3.0]), "operating_ticks": 0.0, "delta_t": 1.0}
        s["consciousness"].entropy.state.coherence = rng.choice([0.4, 0.8, 1.0])
        before = s["consciousness"].entropy.state.coherence
        M.step_rest_open(1.0, s)
        M.step_core_understanding(1.0, s)
        led = s["_rest_ledger"]
        apportioned += led.consolidation
        spent += led.spent
        M.step_rest_close(1.0, s)
        assert s["consciousness"].entropy.state.coherence == pytest.approx(min(1.0, before + led.recovery))
    assert spent <= apportioned + 1e-9


def test_pending_cost_is_the_queue_at_its_passes_plus_the_lattice_backlog():
    s, c = _core_sys(4)
    s["_lattice_step_debt"] = 10.0
    assert M.pending_core_cost(s) == pytest.approx((4 * M.core_passes(s) + 10.0) * M.core_tick_cost(s))
    assert M.pending_core_cost({}) == 0.0, "no clock to price it: zero, never nan"
    assert M.credit_cap({}) == 0.0

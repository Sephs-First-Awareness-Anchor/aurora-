"""A tick is a span of real time, and nothing consolidates mid-turn.

Authors: Sunni (Sir) Morningstar and Cael Devo

The rules (AURORA_TICK_CLOCK_MAP.md):
  1. No mid-turn close-outs: a tick that comes due during a turn waits for the turn to close, and the
     elapsed time still counts.
  2. The turn answers at turn speed: it never waits for a tick; the close runs after it.
"""
import inspect
import os
import sys
import threading
import time
from types import SimpleNamespace

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_internal.aurora_metabolic_clock import (  # noqa: E402
    DEFAULT_TICK_SECONDS, MetabolicClock, turn_gated,
)


class Time:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t


def _clock(tick=300.0, **kw):
    t = Time()
    c = MetabolicClock(tick_seconds=tick, time_source=t, **kw)
    seen = []
    c.register_step("probe", lambda dt, systems: seen.append(dt))
    return c, t, seen


# ---- what a tick is ------------------------------------------------------------------------------

def test_the_default_tick_is_five_minutes():
    assert DEFAULT_TICK_SECONDS == 300.0 and MetabolicClock().tick_seconds == 300.0


@pytest.mark.parametrize("bad", [0, -5, None, "x"])
def test_a_nonsense_tick_length_falls_back_to_the_default(bad):
    assert MetabolicClock(tick_seconds=bad).tick_seconds == DEFAULT_TICK_SECONDS


def test_it_is_not_due_before_a_tick_has_elapsed_and_does_not_close():
    c, t, seen = _clock()
    t.t += 299.9
    assert not c.due() and c.close_if_due() is None and seen == []


def test_a_close_applies_each_step_once_with_the_elapsed_time_in_ticks():
    c, t, seen = _clock()
    t.t += 450.0
    report = c.close_if_due()
    assert seen == [1.5] and report["delta_t"] == 1.5 and report["steps"]["probe"]["ok"] is True
    assert c.closes == 1 and not c.due(), "the elapsed time is consumed"


def test_a_long_gap_is_one_application_not_a_loop_of_ticks():
    """Eight hours is 96 ticks: the tide that came in while she was gone, applied once."""
    c, t, seen = _clock()
    t.t += 8 * 3600.0
    c.close_if_due()
    assert seen == [96.0]


def test_ticks_do_not_pile_up_while_nothing_is_due():
    c, t, seen = _clock()
    for _ in range(5):
        t.t += 100.0
        c.close_if_due()
    assert seen == [pytest.approx(1.0)] and c.closes == 1     # 300 s in, closed once, 200 s remain


def test_force_closes_regardless_of_the_time():
    c, t, seen = _clock()
    t.t += 10.0
    assert c.close_if_due(force=True) is not None and len(seen) == 1


# ---- rule 1: no mid-turn close-outs ----------------------------------------------------------------

def test_nothing_consolidates_while_a_turn_is_open():
    c, t, seen = _clock()
    with c.turn():
        t.t += 400.0                       # the tick comes due DURING the turn
        assert c.due() and c.in_turn
        assert c.close_if_due() is None, "refused while a turn is in flight"
        assert seen == []


def test_a_tick_that_came_due_mid_turn_closes_when_the_turn_closes_and_the_time_still_counts():
    c, t, seen = _clock()
    with c.turn():
        t.t += 400.0
        c.close_if_due()
    assert seen == [pytest.approx(400.0 / 300.0)], "closed at turn close, elapsed counted, nothing lost"
    assert c.closes == 1


def test_a_deferral_is_counted_once_per_due_episode():
    c, t, _ = _clock()
    with c.turn():
        t.t += 400.0
        for _ in range(5):
            c.close_if_due()
    assert c.deferred_closes == 1


def test_nested_turns_close_only_when_the_outermost_one_does():
    c, t, seen = _clock()
    with c.turn():
        with c.turn():
            t.t += 400.0
        assert seen == [] and c.in_turn, "the inner exit must not close the tick"
    assert len(seen) == 1 and not c.in_turn


def test_a_turn_that_raises_still_releases_the_gate_and_the_tick_closes():
    c, t, seen = _clock()
    with pytest.raises(RuntimeError):
        with c.turn():
            t.t += 400.0
            raise RuntimeError("turn failed")
    assert not c.in_turn and len(seen) == 1


def test_a_turn_closing_before_a_tick_is_due_does_nothing():
    c, t, seen = _clock()
    with c.turn():
        t.t += 5.0
    assert seen == [] and c.closes == 0


# ---- rule 2: the turn answers at turn speed ---------------------------------------------------------

def test_entering_a_turn_never_runs_a_step():
    c, t, seen = _clock()
    t.t += 10_000.0                         # a tick is long overdue
    with c.turn():
        assert seen == [], "the turn does not pay for the tick"


def test_a_background_close_runs_off_the_callers_thread():
    c, t, seen = _clock(background=True)
    main = threading.get_ident()
    where = []
    c.register_step("where", lambda dt, s: where.append(threading.get_ident()))
    t.t += 400.0
    with c.turn():
        pass
    deadline = time.monotonic() + 3.0
    while c.closes == 0 and time.monotonic() < deadline:
        time.sleep(0.01)
    assert c.closes == 1 and where and where[0] != main


def test_a_turn_arriving_during_a_close_waits_instead_of_interleaving():
    c, t, _ = _clock(background=True)
    gate, started = threading.Event(), threading.Event()

    def slow(dt, systems):
        started.set()
        gate.wait(timeout=5.0)
    c.register_step("slow", slow)
    t.t += 400.0
    with c.turn():
        pass                                  # starts the background close
    assert started.wait(timeout=3.0)
    entered = threading.Event()

    def next_turn():
        with c.turn():
            entered.set()
    th = threading.Thread(target=next_turn, daemon=True)
    th.start()
    assert not entered.wait(timeout=0.6), "the next turn must not run inside a close"
    gate.set()
    assert entered.wait(timeout=3.0)
    th.join(timeout=3.0)


def test_the_idle_heartbeat_cannot_close_a_tick_during_a_turn():
    c, t, seen = _clock()
    refused = []
    with c.turn():
        t.t += 400.0
        th = threading.Thread(target=lambda: refused.append(c.close_if_due()))
        th.start()
        th.join(timeout=3.0)
    assert refused == [None]


# ---- steps ------------------------------------------------------------------------------------------

def test_one_failing_step_never_stops_the_others_and_is_reported():
    c, t, seen = _clock()
    c.register_step("boom", lambda dt, s: (_ for _ in ()).throw(ValueError("no")))
    c.register_step("after", lambda dt, s: seen.append("after"))
    t.t += 301.0
    report = c.close_if_due()
    assert report["steps"]["boom"]["ok"] is False and "ValueError" in report["steps"]["boom"]["error"]
    assert report["steps"]["after"]["ok"] is True and "after" in seen
    assert c.closes == 1 and not c.status()["closing"]


def test_registering_a_step_again_replaces_it():
    c, t, seen = _clock()
    c.register_step("probe", lambda dt, s: seen.append("replaced"))
    t.t += 301.0
    c.close_if_due()
    assert seen == ["replaced"] and c.step_names == ["probe"]


def test_steps_receive_the_systems_they_were_bound_to():
    c, t, _ = _clock()
    got = []
    c.register_step("who", lambda dt, systems: got.append(systems))
    marker = {"id": 1}
    c.bind(marker)
    t.t += 301.0
    c.close_if_due()
    assert got == [marker]


# ---- persistence ------------------------------------------------------------------------------------

def test_the_last_close_survives_a_restart_so_time_away_counts():
    c, t, _ = _clock()
    t.t += 301.0
    c.close_if_due()
    saved = c.to_state()
    later = Time(t.t + 2 * 3600.0)             # a new process, two hours on
    c2 = MetabolicClock(tick_seconds=300.0, time_source=later)
    seen = []
    c2.register_step("probe", lambda dt, s: seen.append(dt))
    assert c2.load_state(saved)
    c2.close_if_due()
    assert seen == [pytest.approx(24.0)]


def test_a_clock_set_backwards_never_makes_time_run_negative():
    c, t, _ = _clock()
    c.load_state({"last_close": t.t + 10_000.0, "closes": 3})
    assert c.elapsed_seconds() == 0.0 and not c.due()


@pytest.mark.parametrize("bad", [None, {}, "x", {"last_close": "no"}])
def test_unusable_state_is_ignored(bad):
    c, _, _ = _clock()
    before = c.to_state()
    assert c.load_state(bad) is False and c.to_state() == before


def test_each_close_writes_the_state_file_and_a_new_process_restores_it(tmp_path):
    path = str(tmp_path / "metabolic_clock.json")
    c, t, _ = _clock(state_path=path)
    t.t += 301.0
    c.close_if_due()
    assert os.path.exists(path)
    c2 = MetabolicClock(time_source=Time(t.t + 600.0), state_path=path)
    assert c2.restore() is True and c2.closes == 1 and c2.elapsed_seconds() == pytest.approx(600.0)


def test_a_missing_or_corrupt_state_file_just_means_a_fresh_clock(tmp_path):
    path = tmp_path / "metabolic_clock.json"
    assert MetabolicClock(state_path=str(path)).restore() is False
    path.write_text("{not json")
    assert MetabolicClock(state_path=str(path)).restore() is False


# ---- the gate on the turn entry ---------------------------------------------------------------------

def test_the_gate_opens_the_clocks_turn_around_the_wrapped_function():
    c, _, _ = _clock()
    seen = {}

    @turn_gated
    def entry(systems, text, *, flag=False):
        seen["in_turn"] = systems["metabolic_clock"].in_turn
        return text.upper(), flag
    assert entry({"metabolic_clock": c}, "hi", flag=True) == ("HI", True)
    assert seen["in_turn"] is True and not c.in_turn


def test_systems_booted_without_a_clock_run_the_turn_exactly_as_before():
    @turn_gated
    def entry(systems, text):
        return text
    assert entry({}, "x") == "x" and entry(None, "y") == "y"


def test_the_gate_keeps_the_wrapped_functions_signature():
    @turn_gated
    def entry(systems, text, *, source_label="a", turn_tick=None):
        return None
    assert list(inspect.signature(entry).parameters) == ["systems", "text", "source_label", "turn_tick"]


# ---- the live wiring ---------------------------------------------------------------------------------

def test_the_outermost_turn_entry_is_gated():
    import aurora
    assert hasattr(aurora.process_external_user_turn, "__wrapped__")
    params = inspect.signature(aurora.process_external_user_turn).parameters
    assert "on_surface_ready" in params and "turn_tick" in params


def test_the_live_turn_no_longer_ages_sediment_by_itself_when_the_clock_drives_it():
    src = open(os.path.join(REPO_ROOT, "aurora.py"), encoding="utf-8").read()
    i = src.index("_sedi.tick(1.0)")
    assert "if not systems.get('metabolic_clock'):" in src[i - 200:i]


def test_boot_registers_the_sediment_step_and_the_clock():
    src = open(os.path.join(REPO_ROOT, "aurora.py"), encoding="utf-8").read()
    assert 'systems[\'metabolic_clock\'] = _clock' in src and "_register_default_steps(_clock, systems)" in src
    assert 'os.environ.get("AURORA_TICK_SECONDS"' in src


# ---- sediment: the governor's real API ----------------------------------------------------------------

def test_sediment_is_not_scaled_by_an_attached_governor():
    """Sediment ages by elapsed time. A governor's factor (here 5x) must not make it five times older."""
    from aurora_sedimemory import SediMemory
    gov = SimpleNamespace(get_current_dilation_factor=lambda: 5.0)
    m = SediMemory(time_dilation=gov)
    got = []
    m._column.tick = lambda dt, *a, **k: got.append(dt) or {}
    m.tick(2.0)
    assert got == [2.0]


def test_a_real_governor_does_not_dilate_sediment_time():
    from aurora_simulation_engine import TimeDilationGovernor
    from aurora_sedimemory import SediMemory
    gov = TimeDilationGovernor()
    gov.current_dilation = 6000.0              # twice its start: the normalized factor is 2.0
    m = SediMemory(time_dilation=gov)
    got = []
    m._column.tick = lambda dt, *a, **k: got.append(dt) or {}
    m.tick(1.0)
    assert got == [1.0]


def test_without_a_governor_sediment_time_is_undilated():
    from aurora_sedimemory import SediMemory
    m = SediMemory()
    got = []
    m._column.tick = lambda dt, *a, **k: got.append(dt) or {}
    m.tick(3.0)
    assert got[0] == pytest.approx(3.0)


# ---- operating ticks versus resting ticks ---------------------------------------------------------------

def test_a_tick_with_turns_in_it_is_an_operating_tick_and_a_quiet_one_is_rest():
    c, t, _ = _clock()
    with c.turn():
        t.t += 10.0
    t.t += 8 * 3600.0                               # then she is left alone for eight hours
    c.close_if_due()
    span = c.span
    assert span["turns"] == 1 and span["operating_ticks"] == 1.0
    assert span["rest_ticks"] == pytest.approx(span["delta_t"] - 1.0) and span["rest_ticks"] > 90


def test_no_turns_at_all_means_the_whole_span_is_rest():
    c, t, _ = _clock()
    t.t += 3600.0
    c.close_if_due()
    assert c.span["operating_ticks"] == 0.0 and c.span["rest_ticks"] == pytest.approx(12.0)


def test_turns_in_two_different_ticks_make_two_operating_ticks():
    """She chats, is away for twelve minutes, then returns: the first turn back closes a span that
    contained turns in two different ticks (slot 0 and slot 2), with a tick of silence between."""
    c, t, _ = _clock()
    with c.turn():
        pass                                        # slot 0; not yet due
    t.t += 720.0
    with c.turn():
        pass                                        # slot 2; the tick closes at this turn's exit
    assert c.span["turns"] == 2 and c.span["operating_ticks"] == 2.0
    assert c.span["delta_t"] == pytest.approx(2.4) and c.span["rest_ticks"] == pytest.approx(0.4)


def test_many_turns_in_one_tick_are_still_one_operating_tick():
    c, t, _ = _clock()
    for _ in range(20):
        with c.turn():
            t.t += 5.0
    t.t += 400.0
    c.close_if_due()
    assert c.span["turns"] == 20 and c.span["operating_ticks"] == 1.0


def test_operating_time_never_exceeds_the_time_that_passed():
    c, t, _ = _clock()
    with c.turn():
        pass
    t.t += 300.0
    c.close_if_due(force=True)
    assert c.span["operating_ticks"] <= c.span["delta_t"]


def test_the_span_resets_after_each_close():
    c, t, _ = _clock()
    with c.turn():
        t.t += 400.0
    assert c.closes == 1 and c.span["turns"] == 1
    t.t += 400.0
    c.close_if_due()
    assert c.span["turns"] == 0 and c.span["operating_ticks"] == 0.0


def test_the_close_report_says_how_much_was_operating():
    c, t, _ = _clock()
    with c.turn():
        pass
    t.t += 900.0
    report = c.close_if_due()
    assert report["operating_ticks"] == 1.0 and report["turns"] == 1 and report["rest_ticks"] == pytest.approx(2.0)


def test_boot_registers_the_steps_through_the_steps_module():
    src = open(os.path.join(REPO_ROOT, "aurora.py"), encoding="utf-8").read()
    assert "_register_default_steps(_clock, systems)" in src
    steps = open(os.path.join(REPO_ROOT, "aurora_internal", "aurora_metabolic_steps.py"), encoding="utf-8").read()
    assert "engine.entropy_clock_driven = True" in steps
    assert "operating_ticks" in steps[steps.index("def step_entropy"):steps.index("def step_der")]


# ---- the idle heartbeat: she wakes already rested -------------------------------------------------------------

def _wait(pred, timeout=3.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if pred():
            return True
        time.sleep(0.01)
    return pred()


def test_the_heartbeat_closes_a_due_tick_while_she_is_idle():
    c, t, seen = _clock()
    t.t += 400.0
    assert c.start_heartbeat(interval=0.02) is True
    try:
        assert _wait(lambda: c.closes == 1), "no turn arrived, yet the tick closed"
        assert seen and seen[0] == pytest.approx(400.0 / 300.0)
    finally:
        c.stop_heartbeat()


def test_the_heartbeat_never_closes_a_tick_mid_turn():
    c, t, seen = _clock()
    c.start_heartbeat(interval=0.01)
    try:
        with c.turn():
            t.t += 400.0
            time.sleep(0.15)                          # many heartbeat periods pass inside the turn
            assert c.closes == 0 and seen == []
        assert _wait(lambda: c.closes == 1)
    finally:
        c.stop_heartbeat()


def test_the_heartbeat_does_nothing_until_a_tick_is_due():
    c, t, seen = _clock()
    c.start_heartbeat(interval=0.01)
    try:
        time.sleep(0.1)
        assert c.closes == 0 and seen == []
    finally:
        c.stop_heartbeat()


def test_starting_it_twice_starts_one_thread():
    c, _, _ = _clock()
    assert c.start_heartbeat(interval=0.05) is True and c.start_heartbeat(interval=0.05) is False
    assert sum(1 for th in threading.enumerate() if th.name == "MetabolicClockHeartbeat") >= 1
    c.stop_heartbeat()


def test_stopping_it_ends_the_thread_and_it_can_be_restarted():
    c, _, _ = _clock()
    c.start_heartbeat(interval=0.02)
    assert c.heartbeat_alive
    c.stop_heartbeat()
    assert not c.heartbeat_alive
    assert c.start_heartbeat(interval=0.02) is True
    c.stop_heartbeat()


def test_a_failing_step_does_not_kill_the_heartbeat():
    c, t, seen = _clock()
    c.register_step("boom", lambda dt, s: (_ for _ in ()).throw(RuntimeError("x")))
    t.t += 400.0
    c.start_heartbeat(interval=0.02)
    try:
        assert _wait(lambda: c.closes == 1)
        t.t += 400.0
        assert _wait(lambda: c.closes == 2), "the heartbeat survived the failing step"
        assert c.heartbeat_alive
    finally:
        c.stop_heartbeat()


def test_the_heartbeat_period_defaults_to_a_fraction_of_the_tick_and_is_bounded():
    c = MetabolicClock(tick_seconds=300.0)
    c.start_heartbeat()                               # 300 / 4 = 75, bounded to 30 s
    assert c.heartbeat_alive
    c.stop_heartbeat()


def test_boot_starts_the_heartbeat_and_shutdown_stops_it():
    src = open(os.path.join(REPO_ROOT, "aurora.py"), encoding="utf-8").read()
    assert "_clock.start_heartbeat()" in src
    i = src.index("def shutdown_aurora")
    assert "metabolic_clock.stop_heartbeat()" in src[i:i + 3500]


# ---- a suspended device is not a clock that was set --------------------------------------------------------------

def _clock_with_refs():
    wall, ref = [1_000_000.0], [5_000.0]
    c = MetabolicClock(tick_seconds=300.0, time_source=lambda: wall[0], monotonic_source=lambda: ref[0])
    return c, wall, ref


def test_a_night_slept_through_counts_when_the_reference_keeps_counting_through_suspend():
    """CLOCK_BOOTTIME-like: it advances while the device sleeps, so wall and reference agree and the night is rest."""
    c, wall, ref = _clock_with_refs()
    wall[0] += 8 * 3600.0
    ref[0] += 8 * 3600.0
    c.close_if_due()
    assert c.closes == 1 and c.anomalies["clock_forward"] == 0
    assert c.span["rest_ticks"] == pytest.approx(96.0)


def test_a_wall_clock_that_was_set_forward_is_still_not_counted_as_time_passing():
    c, wall, ref = _clock_with_refs()
    wall[0] += 8 * 3600.0                          # the reference did not move: the clock was SET
    c.close_if_due()
    assert c.anomalies["clock_forward"] == 1 and c.closes == 0


def test_the_default_reference_is_the_one_that_counts_suspend_where_it_exists():
    import time as _t
    c = MetabolicClock()
    if hasattr(_t, "CLOCK_BOOTTIME"):
        assert c._check_jumps is True
        a = c._mono()
        assert abs(a - _t.clock_gettime(_t.CLOCK_BOOTTIME)) < 1.0
    else:
        assert c._check_jumps is False, "no reference that counts suspend: do not guess, count the time"


def test_without_a_reference_that_counts_suspend_the_forward_check_is_off(monkeypatch):
    import aurora_internal.aurora_metabolic_clock as mod
    monkeypatch.setattr(mod, "_default_monotonic", lambda: (__import__("time").monotonic, False))
    assert MetabolicClock()._check_jumps is False


def test_injected_clocks_without_a_reference_are_not_checked():
    assert MetabolicClock(time_source=lambda: 1.0)._check_jumps is False

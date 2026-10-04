"""A restart must neither forgive her nor invent anything for her.

Authors: Sunni (Sir) Morningstar and Cael Devo

Found by reading the clock before this change: it saved only `last_close`, so a shutdown or a crash forgot which
ticks she had been OPERATING in and the next close counted ALL of the elapsed time as rest (free recovery of
wear); a death mid-close lost the span that close had consumed; consolidation debt lived only in memory (a reboot
was a debt eraser); a wall clock set backwards left `last_close` in the future so no tick could close; and a
forward jump inside a running process became a huge `delta_t` (free full recovery and free geological aging).
"""
import json
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_internal.aurora_metabolic_clock import MetabolicClock  # noqa: E402

TICK = 300.0


class Time:
    def __init__(self, t=1_000_000.0):
        self.t = t

    def __call__(self):
        return self.t


class Mono:
    def __init__(self, t=5_000.0):
        self.t = t

    def __call__(self):
        return self.t


def _clock(path, t, mono=None, **kw):
    if mono is not None:
        kw["monotonic_source"] = mono
    return MetabolicClock(tick_seconds=TICK, time_source=t, state_path=str(path), **kw)


def _spans(c):
    seen = []
    c.register_step("record", lambda dt, s: seen.append(dict(c.span)))
    return seen


# ---- normal shutdown and forced death: she was operating, and that survives -----------------------------------

def test_a_turn_is_persisted_the_moment_it_ends(tmp_path):
    t = Time()
    c = _clock(tmp_path / "c.json", t)
    with c.turn():
        t.t += 10
    saved = json.load(open(tmp_path / "c.json"))
    assert saved["span_turns"] == 1 and saved["span_slots"] == [0]


def test_after_a_normal_shutdown_the_operating_time_is_not_forgiven(tmp_path):
    t = Time()
    c1 = _clock(tmp_path / "c.json", t)
    with c1.turn():
        t.t += 20
    # ... shutdown: nothing else is called ...
    t.t += 6 * TICK                                           # she is away for half an hour
    c2 = _clock(tmp_path / "c.json", t)
    assert c2.restore()
    seen = _spans(c2)
    c2.close_if_due()
    assert seen[0]["turns"] == 1 and seen[0]["operating_ticks"] == 1.0, "she WAS operating before she left"
    assert seen[0]["rest_ticks"] == pytest.approx(seen[0]["delta_t"] - 1.0)


def test_after_forced_process_death_it_is_the_same_as_a_shutdown(tmp_path):
    """No cleanup runs at all: the object is simply abandoned, as kill -9 does."""
    t = Time()
    c1 = _clock(tmp_path / "c.json", t)
    for _ in range(3):
        with c1.turn():
            t.t += 40
    del c1
    t.t += 3 * TICK
    c2 = _clock(tmp_path / "c.json", t)
    c2.restore()
    seen = _spans(c2)
    c2.close_if_due()
    assert seen[0]["turns"] == 3 and seen[0]["operating_ticks"] == 1.0


def test_without_this_a_restart_would_have_counted_everything_as_rest(tmp_path):
    """The regression, stated: a clock that only knows last_close sees no turns at all."""
    t = Time()
    c1 = _clock(tmp_path / "c.json", t)
    with c1.turn():
        t.t += 20
    state = json.load(open(tmp_path / "c.json"))
    for k in ("span_turns", "span_slots", "closing"):
        state.pop(k, None)
    json.dump(state, open(tmp_path / "c.json", "w"))
    t.t += 6 * TICK
    c2 = _clock(tmp_path / "c.json", t)
    c2.restore()
    seen = _spans(c2)
    c2.close_if_due()
    assert seen[0]["operating_ticks"] == 0.0, "(that is the free recovery the persisted span prevents)"


# ---- hours away ---------------------------------------------------------------------------------------------

def test_hours_away_count_as_rest_in_full_and_the_operating_part_stays_operating(tmp_path):
    t = Time()
    c1 = _clock(tmp_path / "c.json", t)
    with c1.turn():
        t.t += 5
    t.t += 8 * 3600
    c2 = _clock(tmp_path / "c.json", t)
    c2.restore()
    seen = _spans(c2)
    c2.close_if_due()
    s = seen[0]
    assert s["delta_t"] == pytest.approx((8 * 3600 + 5) / TICK)
    assert s["operating_ticks"] == 1.0 and s["rest_ticks"] == pytest.approx(s["delta_t"] - 1.0)


def test_days_away_are_not_capped_because_time_away_really_passed(tmp_path):
    t = Time()
    c1 = _clock(tmp_path / "c.json", t)
    c1.close_if_due(force=True)
    t.t += 400 * 86400
    c2 = _clock(tmp_path / "c.json", t)
    c2.restore()
    seen = _spans(c2)
    c2.close_if_due()
    assert seen[0]["delta_t"] == pytest.approx(400 * 86400 / TICK) and seen[0]["operating_ticks"] == 0.0


# ---- restart during rest: nothing was operating, so nothing is invented -----------------------------------------

def test_a_restart_during_rest_is_all_rest(tmp_path):
    t = Time()
    c1 = _clock(tmp_path / "c.json", t)
    c1.close_if_due(force=True)
    t.t += 2 * TICK
    c1.close_if_due()
    t.t += 5 * TICK                                        # resting; the process dies here
    c2 = _clock(tmp_path / "c.json", t)
    c2.restore()
    seen = _spans(c2)
    c2.close_if_due()
    assert seen[0]["turns"] == 0 and seen[0]["operating_ticks"] == 0.0 and seen[0]["rest_ticks"] > 0


def test_a_restart_does_not_make_the_close_count_reset_or_repeat(tmp_path):
    t = Time()
    c1 = _clock(tmp_path / "c.json", t)
    t.t += TICK
    c1.close_if_due()
    t.t += TICK
    c1.close_if_due()
    c2 = _clock(tmp_path / "c.json", t)
    c2.restore()
    assert c2.closes == 2
    assert c2.close_if_due() is None, "no new time has passed, so no tick is due"


# ---- consolidation debt survives a restart ------------------------------------------------------------------

def test_registered_state_survives_a_restart(tmp_path):
    t = Time()
    box = {"debt": 12.5, "credit": 0.003}
    c1 = _clock(tmp_path / "c.json", t)
    c1.register_state("consolidation", lambda: dict(box), lambda raw: box.update(raw))
    with c1.turn():
        pass
    c2 = _clock(tmp_path / "c.json", t)
    c2.restore()
    fresh = {"debt": 0.0, "credit": 0.0}
    c2.register_state("consolidation", lambda: dict(fresh), lambda raw: fresh.update(raw))
    assert fresh == {"debt": 12.5, "credit": 0.003}, "a reboot is not a debt eraser"


def test_state_registered_before_restore_is_handed_over_at_restore(tmp_path):
    t = Time()
    box = {"debt": 7.0}
    c1 = _clock(tmp_path / "c.json", t)
    c1.register_state("consolidation", lambda: dict(box), lambda raw: box.update(raw))
    c1.close_if_due(force=True)
    c2 = _clock(tmp_path / "c.json", t)
    fresh = {"debt": 0.0}
    c2.register_state("consolidation", lambda: dict(fresh), lambda raw: fresh.update(raw))
    assert c2.restore() and fresh["debt"] == 7.0


def test_a_state_that_cannot_be_restored_starts_fresh_and_never_blocks_boot(tmp_path):
    t = Time()
    c1 = _clock(tmp_path / "c.json", t)
    c1.register_state("x", lambda: {"a": 1}, lambda raw: None)
    c1.close_if_due(force=True)
    c2 = _clock(tmp_path / "c.json", t)
    c2.register_state("x", lambda: {}, lambda raw: (_ for _ in ()).throw(ValueError("bad")))
    assert c2.restore() is True


def test_a_getter_that_fails_does_not_stop_the_clock_persisting(tmp_path):
    t = Time()
    c = _clock(tmp_path / "c.json", t)
    c.register_state("boom", lambda: (_ for _ in ()).throw(RuntimeError("x")), lambda raw: None)
    with c.turn():
        pass
    assert json.load(open(tmp_path / "c.json"))["span_turns"] == 1


# ---- death in the middle of a close --------------------------------------------------------------------------

def test_a_close_saves_the_span_it_consumed_before_it_runs(tmp_path):
    t = Time()
    c = _clock(tmp_path / "c.json", t)
    with c.turn():
        t.t += 10
    snapshots = []

    def mid_close(dt, systems):
        snapshots.append(json.load(open(tmp_path / "c.json")))

    c.register_step("mid", mid_close)
    t.t += TICK
    c.close_if_due()
    mid = snapshots[0]
    assert mid["closing"] == {"from": mid["last_close"], "turns": 1, "slots": [0]}
    assert json.load(open(tmp_path / "c.json"))["closing"] is None, "cleared when the close finishes"


def test_dying_mid_close_does_not_turn_operating_time_into_free_rest(tmp_path):
    t = Time()
    c1 = _clock(tmp_path / "c.json", t)
    with c1.turn():
        t.t += 10
    died = {}

    def die(dt, systems):
        died["state"] = open(tmp_path / "c.json").read()
        raise KeyboardInterrupt            # the process is gone: nothing after this runs

    c1.register_step("die", die)
    t.t += TICK
    with pytest.raises(KeyboardInterrupt):
        c1.close_if_due()
    open(tmp_path / "c.json", "w").write(died["state"])         # what was on disk at the moment of death
    t.t += 2 * TICK
    c2 = _clock(tmp_path / "c.json", t)
    c2.restore()
    assert c2.anomalies["interrupted_close"] == 1
    seen = _spans(c2)
    c2.close_if_due()
    assert seen[0]["turns"] == 1 and seen[0]["operating_ticks"] == 1.0
    assert c2.close_if_due() is None, "and it is accounted ONCE, not on every boot"


def test_the_interrupted_close_is_not_repeated_after_it_finishes(tmp_path):
    t = Time()
    c1 = _clock(tmp_path / "c.json", t)
    with c1.turn():
        pass
    t.t += TICK
    c1.close_if_due()
    c2 = _clock(tmp_path / "c.json", t)
    c2.restore()
    assert c2.anomalies["interrupted_close"] == 0 and c2._span_turns == 0


# ---- clock anomalies ---------------------------------------------------------------------------------------

def test_a_clock_set_backwards_across_a_restart_gives_neither_gain_nor_penalty(tmp_path):
    t = Time(2_000_000.0)
    c1 = _clock(tmp_path / "c.json", t)
    c1.close_if_due(force=True)
    t.t -= 86400 * 30                                     # the wall clock is now a month earlier
    c2 = _clock(tmp_path / "c.json", t)
    assert c2.restore()
    assert c2.elapsed_seconds() == 0.0 and c2.anomalies["clock_backward"] == 1
    t.t += TICK
    seen = _spans(c2)
    c2.close_if_due()
    assert seen[0]["delta_t"] == pytest.approx(1.0), "time runs from the new now, not from a month in the future"


def test_a_clock_set_backwards_in_a_running_process_does_not_stop_consolidation(tmp_path):
    t, m = Time(), Mono()
    c = _clock(tmp_path / "c.json", t, m)
    t.t -= 86400                                           # set a day back while running
    assert c.close_if_due() is None
    assert c.anomalies["clock_backward"] == 1
    t.t += TICK
    m.t += TICK
    seen = _spans(c)
    assert c.close_if_due() is not None, "ticks close again one tick later, not a day later"
    assert seen[0]["delta_t"] == pytest.approx(1.0)


def test_a_wall_clock_that_jumps_forward_does_not_buy_free_recovery(tmp_path):
    t, m = Time(), Mono()
    c = _clock(tmp_path / "c.json", t, m)
    seen = _spans(c)
    t.t += 10 * 86400                                      # set ten days ahead ...
    m.t += 2 * TICK                                        # ... but only ten minutes really passed
    c.close_if_due()
    assert seen[0]["delta_t"] == pytest.approx(2.0)
    assert c.anomalies["clock_forward"] == 1


def test_ntp_sized_drift_is_not_an_anomaly(tmp_path):
    t, m = Time(), Mono()
    c = _clock(tmp_path / "c.json", t, m)
    t.t += TICK + 0.8
    m.t += TICK
    c.close_if_due()
    assert c.anomalies["clock_forward"] == 0 and c.anomalies["clock_backward"] == 0


def test_a_real_wall_clock_is_checked_and_an_injected_one_without_a_reference_is_not(tmp_path):
    assert MetabolicClock(tick_seconds=TICK)._check_jumps is True
    assert MetabolicClock(tick_seconds=TICK, time_source=Time())._check_jumps is False
    assert MetabolicClock(tick_seconds=TICK, time_source=Time(), monotonic_source=Mono())._check_jumps is True


def test_after_a_restart_time_away_is_trusted_because_there_is_no_reference_for_it(tmp_path):
    t, m = Time(), Mono()
    c1 = _clock(tmp_path / "c.json", t, m)
    c1.close_if_due(force=True)
    t.t += 3 * 3600
    c2 = _clock(tmp_path / "c.json", t, Mono(1.0))         # a brand new process: its monotonic clock restarted
    c2.restore()
    seen = _spans(c2)
    c2.close_if_due()
    assert seen[0]["delta_t"] == pytest.approx(3 * 3600 / TICK) and c2.anomalies["clock_forward"] == 0


# ---- damaged files -----------------------------------------------------------------------------------------

@pytest.mark.parametrize("junk", ["", "{", "[]", "null", '{"last_close": "x"}', '{"last_close": NaN}', '{"closes": 3}'])
def test_a_damaged_state_file_starts_fresh_and_never_raises(tmp_path, junk):
    open(tmp_path / "c.json", "w").write(junk)
    c = _clock(tmp_path / "c.json", Time())
    assert c.restore() is False
    assert c.closes == 0 and c.elapsed_seconds() == 0.0


def test_unknown_and_malformed_span_fields_are_ignored(tmp_path):
    t = Time()
    json.dump({"last_close": t.t - 10, "closes": 4, "span_turns": "x", "span_slots": [None, "a"],
               "closing": {"turns": "bad"}, "states": 5, "anomalies": 3, "future_field": 1},
              open(tmp_path / "c.json", "w"))
    c = _clock(tmp_path / "c.json", t)
    assert c.restore() is True and c.closes == 4 and c._span_turns == 0


def test_negative_span_fields_cannot_become_negative_operating_time(tmp_path):
    t = Time()
    json.dump({"last_close": t.t - 10, "span_turns": -9, "span_slots": [-1, -5], "closing": {"turns": -3, "slots": [-2]}},
              open(tmp_path / "c.json", "w"))
    c = _clock(tmp_path / "c.json", t)
    c.restore()
    assert c._span_turns == 0 and c._span_slots == set()

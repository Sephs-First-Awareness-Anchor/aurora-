#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Write-behind across turns (phone load, 2026-11-08): hot state is written
at most once per window, never lost, never written mid-turn."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import aurora_internal.aurora_turn_persistence as P  # noqa: E402


class Store:
    def __init__(self):
        self.value = 0
        self.disk = None
        self.writes = 0

    def change(self, v):
        self.value = v
        if not P.batch_defer(self):
            self.flush_write_batch()

    def flush_write_batch(self):
        self.disk = self.value
        self.writes += 1


class Clock:
    def __init__(self):
        self.t = 1_000_000.0

    def time(self):
        return self.t


def _turn(store, v):
    targets = [store]
    with P._LOCK:
        store._wb_depth = int(getattr(store, "_wb_depth", 0) or 0) + 1
    store.change(v)
    store.change(v + 0.5)
    P.end_write_batch(targets)


def test_written_once_per_window_and_latest_state_wins(monkeypatch):
    clock = Clock()
    monkeypatch.setattr(P.time, "time", clock.time)
    monkeypatch.setattr(P, "WRITE_BEHIND_S", 30.0)
    P._PENDING.clear(); P._LAST_FLUSH.clear()
    s = Store()
    _turn(s, 1)
    assert s.writes == 1 and s.disk == 1.5          # first turn is always written
    for i in range(2, 6):
        clock.t += 5
        _turn(s, i)
    assert s.writes == 1 and P.pending_count() == 1 # inside the window: pending
    assert not P.any_due()
    clock.t += 30
    assert P.any_due()
    assert P.flush_due() == 1
    assert s.writes == 2 and s.disk == 5.5          # newest in-memory state
    assert P.pending_count() == 0


def test_never_written_while_a_turn_holds_it(monkeypatch):
    clock = Clock()
    monkeypatch.setattr(P.time, "time", clock.time)
    monkeypatch.setattr(P, "WRITE_BEHIND_S", 30.0)
    P._PENDING.clear(); P._LAST_FLUSH.clear()
    s = Store()
    _turn(s, 1)
    clock.t += 5
    _turn(s, 2)
    clock.t += 60
    with P._LOCK:
        s._wb_depth = 1                              # a turn is running on it
    assert P.flush_due() == 1 and s.writes == 1      # due, but skipped
    with P._LOCK:
        s._wb_depth = 0
    P.flush_due()
    assert s.writes == 2 and s.disk == 2.5


def test_flush_all_writes_everything_and_zero_window_is_old_behaviour(monkeypatch):
    clock = Clock()
    monkeypatch.setattr(P.time, "time", clock.time)
    monkeypatch.setattr(P, "WRITE_BEHIND_S", 30.0)
    P._PENDING.clear(); P._LAST_FLUSH.clear()
    s = Store()
    _turn(s, 1); clock.t += 1; _turn(s, 2)
    assert P.flush_all() == 1 and s.disk == 2.5
    monkeypatch.setattr(P, "WRITE_BEHIND_S", 0.0)
    t = Store()
    for i in range(3):
        _turn(t, i)
    assert t.writes == 3

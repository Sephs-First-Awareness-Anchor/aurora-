#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
test_phone_load_pacing.py -- the phone overload fix (2026-11-07).

Background sources (historical replay, Praxis bridge, messenger and her
reach-outs, learning probe, proactive loop, evolution sim) all ran her full
pipeline back to back right after boot; Android killed the app.  These pin:
  * the field lock still behaves exactly like a lock, and records releases;
  * no background turn while she settles after boot;
  * quiet time after any turn before the next background turn;
  * wider spacing on low battery when not charging;
  * the shared idle predicate includes the breathing room.
"""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

import pytest

_APP = Path(__file__).resolve().parent.parent / "flutter_app/android/app/src/main/python"
if not (_APP / "aurora_bridge.py").exists():
    pytest.skip("app aurora_bridge.py not found", allow_module_level=True)
sys.path.insert(0, str(_APP))
ab = pytest.importorskip("aurora_bridge")


@pytest.fixture
def calm(monkeypatch):
    lock = ab._FieldLock()
    monkeypatch.setattr(ab, "_lock", lock)
    monkeypatch.setattr(ab, "_hardware_sensors", {})
    monkeypatch.setattr(ab, "_systems", {})
    monkeypatch.setattr(ab, "_last_output_time", 0.0)
    return lock


def test_field_lock_is_still_a_lock(calm):
    lock = calm
    assert lock.acquire(blocking=False) and lock.locked()
    assert not lock.acquire(blocking=False)
    before = time.time()
    lock.release()
    assert not lock.locked() and lock.last_released >= before
    with lock:
        assert lock.locked()
    assert not lock.locked()
    held = threading.Event()

    def other():
        with lock:
            held.set()
    t = threading.Thread(target=other)
    t.start()
    t.join(2)
    assert held.is_set()


def test_no_background_thinking_while_she_settles(calm, monkeypatch):
    now = 1_800_000_000.0
    monkeypatch.setattr(ab, "_boot_completed_at", 0.0)
    assert not ab._background_breathing_room(now), "not booted yet"
    monkeypatch.setattr(ab, "_boot_completed_at", now - 10)
    assert not ab._background_breathing_room(now)
    monkeypatch.setattr(ab, "_boot_completed_at", now - ab.BOOT_SETTLE_S - 1)
    assert ab._background_breathing_room(now)


def test_quiet_gap_after_any_turn(calm, monkeypatch):
    now = 1_800_000_000.0
    monkeypatch.setattr(ab, "_boot_completed_at", now - 3600)
    calm.last_released = now - 5
    assert not ab._background_breathing_room(now)
    calm.last_released = now - ab.BACKGROUND_GAP_S - 1
    assert ab._background_breathing_room(now)


def test_low_battery_widens_the_gap_unless_charging(calm, monkeypatch):
    now = 1_800_000_000.0
    monkeypatch.setattr(ab, "_boot_completed_at", now - 3600)
    calm.last_released = now - ab.BACKGROUND_GAP_S - 1
    monkeypatch.setattr(ab, "_hardware_sensors", {"battery_pct": 12, "charging": False})
    assert not ab._background_breathing_room(now)
    monkeypatch.setattr(ab, "_hardware_sensors", {"battery_pct": 12, "charging": True})
    assert ab._background_breathing_room(now)
    monkeypatch.setattr(ab, "_hardware_sensors", {"battery_pct": 12, "charging": False})
    calm.last_released = now - ab.LOW_BATTERY_GAP_S - 1
    assert ab._background_breathing_room(now)


def test_shared_idle_predicate_includes_breathing_room(calm, monkeypatch):
    monkeypatch.setattr(ab, "_boot_completed_at", time.time())     # just booted
    assert ab._historical_experience_live_idle() is False
    assert ab._praxis_live_idle() is False
    monkeypatch.setattr(ab, "_boot_completed_at", time.time() - 3600)
    calm.last_released = 0.0
    assert ab._historical_experience_live_idle() is True


def test_a_waiting_message_outranks_other_background_work(calm, monkeypatch):
    class Waiting:
        def __init__(self, w):
            self.w = w

        def waiting(self):
            return self.w

    monkeypatch.setattr(ab, "_boot_completed_at", time.time() - 3600)
    calm.last_released = 0.0
    monkeypatch.setattr(ab, "_systems", {"praxis_messenger": Waiting(True)})
    assert ab._historical_experience_live_idle() is False     # replay yields
    assert ab._praxis_live_idle() is False                    # world loop / probe yield
    assert ab._background_breathing_room() is False           # proactive / evo sim yield
    assert ab._messenger_live_idle() is True                  # the messenger goes
    monkeypatch.setattr(ab, "_systems", {"praxis_messenger": Waiting(False)})
    assert ab._historical_experience_live_idle() is True

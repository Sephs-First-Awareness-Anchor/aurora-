#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
test_surface_face_live_read.py -- her face reads her live state, and a live
turn is never queued behind a second background pass.

The bridge used to read ``dimensional.pressure_vec``, which does not exist,
then fell back to ``identity_field.axis_activation``, which does not exist
either, so between turns the face never moved.  These pin:
  * the live pressure comes from ``_current_pressure_vec()`` on each poll;
  * expressed activation (X/T/N/B/A) is not overwritten by pressure;
  * the identity field's per-axis pressure is the fallback;
  * a read that races a turn reshaping the crystals is skipped, not faulted;
  * get_axis_state() reads live at most once per interval;
  * the curiosity engine is handed the dimensional system itself;
  * while a live turn waits for the field, background sources hold back,
    and the field lock says who holds it.
"""
from __future__ import annotations

import json
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


class _PV:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


class _Dim:
    def __init__(self):
        self.calls = 0
        self.value = dict(X=0.2, T=0.3, N=0.4, B=0.5, A=0.6)
        self.raise_once = False

    def _current_pressure_vec(self):
        self.calls += 1
        if self.raise_once:
            self.raise_once = False
            raise RuntimeError("dictionary changed size during iteration")
        return _PV(**self.value)


class _Field:
    def axis_pressure(self, i):
        return 0.1 * (i + 1)


@pytest.fixture
def live(monkeypatch):
    dim = _Dim()
    systems = {"dimensional": dim}
    state = {"X": 0.5, "T": 0.5, "N": 0.5, "B": 0.5, "A": 0.5, "speaking": False}
    monkeypatch.setattr(ab, "_systems", systems)
    monkeypatch.setattr(ab, "_last_axis_state", state)
    monkeypatch.setattr(ab, "_axis_live_read_at", 0.0)
    return dim, systems, state


def test_live_pressure_is_read_from_the_method(live):
    dim, _systems, state = live
    ab._refresh_axis_state_from_systems()
    assert dim.calls == 1
    assert state["pressure"] == {"X": 0.2, "T": 0.3, "N": 0.4, "B": 0.5, "A": 0.6}
    dim.value["T"] = 0.9
    ab._refresh_axis_state_from_systems()
    assert state["pressure"]["T"] == 0.9


def test_expressed_activation_is_kept_apart_from_pressure(live):
    _dim, systems, state = live
    systems["_prev_axis_activation"] = {"X": 0.8, "T": 0.1, "N": 0.2, "B": 0.3, "A": 0.7}
    ab._refresh_axis_state_from_systems()
    assert (state["X"], state["A"]) == (0.8, 0.7)
    assert state["pressure"]["X"] == 0.2


def test_identity_field_pressure_is_the_fallback(live):
    _dim, systems, state = live
    systems.pop("dimensional")
    systems["identity_field"] = _Field()
    ab._refresh_axis_state_from_systems()
    assert state["pressure"] == {"X": 0.1, "T": 0.2, "N": 0.3, "B": 0.4, "A": 0.5}


def test_a_read_racing_a_turn_is_skipped_not_faulted(live, monkeypatch):
    dim, _systems, state = live
    faults = []
    monkeypatch.setattr(ab, "_aurora_record_exception_from_locals", lambda *a, **k: faults.append(k))
    dim.raise_once = True
    ab._refresh_axis_state_from_systems()
    assert "pressure" not in state and not faults
    ab._refresh_axis_state_from_systems()
    assert state["pressure"]["X"] == 0.2


def test_get_axis_state_reads_live_once_per_interval(live):
    dim, _systems, _state = live
    first = json.loads(ab.get_axis_state())
    second = json.loads(ab.get_axis_state())
    assert dim.calls == 1
    assert first["pressure"] == second["pressure"]
    ab._axis_live_read_at = time.time() - ab._AXIS_LIVE_MIN_INTERVAL_S - 0.1
    ab.get_axis_state()
    assert dim.calls == 2


def test_curiosity_engine_gets_the_dimensional_system():
    src = (_APP / "aurora_bridge.py").read_text(encoding="utf-8")
    assert 'getattr(dim, "pressure_vec"' not in src
    assert 'hasattr(dim, "_current_pressure_vec")' in src


@pytest.fixture
def calm(monkeypatch):
    lock = ab._FieldLock()
    monkeypatch.setattr(ab, "_lock", lock)
    monkeypatch.setattr(ab, "_hardware_sensors", {})
    monkeypatch.setattr(ab, "_systems", {})
    monkeypatch.setattr(ab, "_last_output_time", 0.0)
    monkeypatch.setattr(ab, "_boot_completed_at", time.time() - ab.BOOT_SETTLE_S - 1)
    monkeypatch.setattr(ab, "_present_waiting", 0)
    return lock


def test_background_holds_back_while_a_live_turn_waits(calm):
    lock = calm
    assert ab._background_breathing_room(time.time() + 3600)
    lock.acquire()
    entered = threading.Event()

    def turn():
        with ab._PresentClaim():
            entered.set()

    t = threading.Thread(target=turn, name="surface_turn:test")
    t.start()
    deadline = time.time() + 2
    while not ab._present_is_waiting() and time.time() < deadline:
        time.sleep(0.01)
    assert ab._present_is_waiting()
    assert not ab._background_breathing_room(time.time() + 3600)
    lock.release()
    t.join(2)
    assert entered.is_set() and not ab._present_is_waiting()
    assert not lock.locked()


def test_field_lock_names_its_holder(calm):
    lock = calm
    with lock:
        assert lock.holder == threading.current_thread().name
        assert lock.held_since > 0
    assert lock.holder == "" and lock.held_since == 0.0
    assert lock.acquire(blocking=False)
    assert lock.holder == threading.current_thread().name
    lock.release()

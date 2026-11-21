#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
test_surface_control_panel.py -- surface restructure 6 (2026-11-21).

The phone's control panel and growth-while-charging pacing.  These pin:
  * the panel's controls default on, change one at a time, persist in her
    state directory and come back on the next start;
  * an unknown control is refused and changes nothing;
  * growth waits for the charger only on an unpaired phone, with the control
    on, on an actual "not charging" reading -- never on a guess, never on a
    paired surface (which runs no growth here at all);
  * the sources Sir approved (history stream, Praxis and the learning probe,
    curiosity, dreams, evolution) wait; her messenger and the shared breathing
    room do not, so her conversations and her own initiative stay live;
  * curiosity and dreams respect may_run, and space a cycle rather than drop.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_APP = _ROOT / "flutter_app/android/app/src/main/python"
if not (_APP / "aurora_bridge.py").exists():
    pytest.skip("app aurora_bridge.py not found", allow_module_level=True)
sys.path.insert(0, str(_APP))
ab = pytest.importorskip("aurora_bridge")


@pytest.fixture
def phone(monkeypatch, tmp_path):
    monkeypatch.setattr(ab, "_strata_state_dir", str(tmp_path))
    monkeypatch.setattr(ab, "_surface_only", False)
    monkeypatch.setattr(ab, "_hardware_sensors", {})
    ab._load_surface_controls()
    yield tmp_path
    # Leave the module as other tests expect it: every control on.
    with ab._surface_controls_lock:
        ab._surface_controls.clear()
        ab._surface_controls.update(ab._SURFACE_CONTROL_DEFAULTS)


def test_controls_default_on(phone):
    answer = json.loads(ab.get_surface_controls())
    assert answer["controls"] == {k: True for k in ab._SURFACE_CONTROL_DEFAULTS}
    assert set(answer["growth"]) == {"waits_for_charging", "control_on", "charging", "paired_surface"}


def test_set_control_persists_and_reloads(phone):
    answer = json.loads(ab.set_surface_control("camera_sensing", False))
    assert answer["ok"] is True and answer["controls"]["camera_sensing"] is False
    stored = json.loads((phone / ab._SURFACE_CONTROLS_FILE).read_text(encoding="utf-8"))
    assert stored["camera_sensing"] is False and stored["voice"] is True
    # A fresh start reads the stored panel back.
    with ab._surface_controls_lock:
        ab._surface_controls.update(ab._SURFACE_CONTROL_DEFAULTS)
    ab._load_surface_controls()
    assert ab.surface_control("camera_sensing") is False
    assert ab.surface_control("listening") is True


def test_unknown_control_refused(phone):
    answer = json.loads(ab.set_surface_control("not_a_control", False))
    assert answer["ok"] is False
    assert not (phone / ab._SURFACE_CONTROLS_FILE).exists()


def test_cmd_form_for_kotlin(phone):
    assert json.loads(ab.set_surface_control_cmd("voice:off"))["controls"]["voice"] is False
    assert json.loads(ab.set_surface_control_cmd("voice:on"))["controls"]["voice"] is True


def test_unreadable_store_falls_back_to_defaults(phone):
    (phone / ab._SURFACE_CONTROLS_FILE).write_text("{not json", encoding="utf-8")
    ab._load_surface_controls()
    assert all(ab.surface_control(k) for k in ab._SURFACE_CONTROL_DEFAULTS)


def test_controls_file_stays_with_the_phone():
    # surface_sensory_* files are the phone's own; they never move with her.
    assert ab._SURFACE_CONTROLS_FILE.startswith("surface_sensory_")


@pytest.mark.parametrize("charging,expected", [(False, True), (True, False), (None, False)])
def test_gate_holds_only_on_a_not_charging_reading(phone, monkeypatch, charging, expected):
    sensors = {} if charging is None else {"charging": charging}
    monkeypatch.setattr(ab, "_hardware_sensors", sensors)
    assert ab._growth_waits_for_charging() is expected
    assert ab._growth_status()["charging"] == charging


def test_gate_off_on_a_paired_surface(phone, monkeypatch):
    monkeypatch.setattr(ab, "_hardware_sensors", {"charging": False})
    monkeypatch.setattr(ab, "_surface_only", True)
    assert ab._growth_waits_for_charging() is False
    assert ab._growth_status()["paired_surface"] is True


def test_gate_off_when_sir_turns_the_control_off(phone, monkeypatch):
    monkeypatch.setattr(ab, "_hardware_sensors", {"charging": False})
    ab.set_surface_control("growth_while_charging_only", False)
    assert ab._growth_waits_for_charging() is False


def test_growth_sources_wait_but_her_conversations_do_not(phone, monkeypatch):
    monkeypatch.setattr(ab, "_hardware_sensors", {"charging": False})
    calls = []

    def idle(yield_to_messenger: bool = True) -> bool:
        calls.append(yield_to_messenger)
        return True

    monkeypatch.setattr(ab, "_historical_experience_live_idle", idle)
    # Growth work waits for the charger.
    assert ab._history_stream_live_idle() is False
    assert ab._praxis_live_idle() is False
    # Her messenger keeps its own terms.
    assert ab._messenger_live_idle() is True
    # On the charger, growth goes back to the shared idle terms.
    monkeypatch.setattr(ab, "_hardware_sensors", {"charging": True})
    assert ab._history_stream_live_idle() is True
    assert ab._praxis_live_idle() is True


def test_breathing_room_ignores_the_charger(phone, monkeypatch):
    # The shared pacing also paces her own initiative, so it must not wait.
    monkeypatch.setattr(ab, "_hardware_sensors", {"charging": False})
    src = Path(ab.__file__).read_text(encoding="utf-8")
    start = src.index("def _background_breathing_room(")
    body = src[start:src.index("\ndef ", start + 10)]
    assert "_growth_waits_for_charging" not in body


def test_field_status_carries_growth(phone):
    status = json.loads(ab.get_field_status())
    assert "growth" in status and "waits_for_charging" in status["growth"]


def test_curiosity_respects_may_run(monkeypatch):
    sys.path.insert(0, str(_ROOT))
    ce = pytest.importorskip("aurora_curiosity_engine")
    # The failing may_run below is recorded as a fault; keep that record
    # out of her real fault log.
    monkeypatch.setattr(ce, "_aurora_fault", lambda *a, **k: None)

    class _Engine:
        systems: dict = {}

        def __init__(self) -> None:
            self.cycles = 0

        def reset_idle_counter(self) -> None:
            pass

        def run_curiosity_cycle(self) -> None:
            self.cycles += 1

    def run(may_run) -> int:
        ce._CURIOSITY_THREAD = None
        ce._CYCLE_INTERRUPTIBLE.clear()
        engine = _Engine()
        ce.start_curiosity_background(engine, tick_interval_s=0.05, may_run=may_run)
        time.sleep(0.3)
        ce._CURIOSITY_STOP.set()
        ce._CURIOSITY_THREAD.join(2)
        ce._CYCLE_INTERRUPTIBLE.clear()
        ce._CURIOSITY_THREAD = None
        return engine.cycles

    assert run(lambda: False) == 0
    assert run(lambda: True) > 0
    # A may_run that fails never stops her curiosity.
    assert run(lambda: 1 / 0) > 0


def test_dreams_respect_may_run(monkeypatch):
    sys.path.insert(0, str(_ROOT))
    qd = pytest.importorskip("aurora_quantum_dream_substrate")
    cycles = []

    class _Substrate:
        def run_dream_cycle(self, systems) -> None:
            cycles.append(1)

    monkeypatch.setattr(qd, "QuantumDreamSubstrate", _Substrate)
    real_sleep = time.sleep
    monkeypatch.setattr(qd.time, "sleep", lambda s: real_sleep(min(s, 0.01)))

    def run(may_run) -> int:
        cycles.clear()
        qd._dream_thread = None
        qd.start_dream_substrate({}, cycle_interval_s=60.0, may_run=may_run)
        real_sleep(0.3)
        qd.stop_dream_substrate()
        qd._dream_thread.join(2)
        qd._dream_thread = None
        return len(cycles)

    assert run(lambda: False) == 0
    assert run(lambda: True) == 1

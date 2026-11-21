#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
test_surface_control_panel.py -- surface restructure 6 (2026-11-21).

The phone's control panel and growth-while-charging pacing.  These pin:
  * the panel's sensing and voice controls default on and the charger
    switch defaults off (Sir, 2026-11-21); each changes one at a time, persists in her
    state directory and come back on the next start;
  * an unknown control is refused and changes nothing;
  * growth waits for the charger only on an unpaired phone, with the control
    on, on an actual "not charging" reading -- never on a guess, never on a
    paired surface (which runs no growth here at all);
  * the sources Sir approved (history stream, Praxis and the learning probe,
    curiosity, dreams, evolution) wait; her messenger and the shared breathing
    room do not, so her conversations and her own initiative stay live;
  * curiosity and dreams respect may_run, and space a cycle rather than drop;
  * while Sir is talking with her (a live turn waits or runs, or he wrote in
    the last CONVERSATION_QUIET_S), all her background work steps aside and
    carries on by itself afterwards; her own initiative is not held (his
    words: "when I'm interacting with her she isn't held up by other
    processes ... This shouldn't take away from her autonomy");
  * a live turn releases curiosity mid-cycle, and a dream holds between its
    steps and resumes from the same step.
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
    monkeypatch.setattr(ab, "_last_output_time", 0.0)
    monkeypatch.setattr(ab, "_present_active", 0)
    monkeypatch.setattr(ab, "_present_waiting", 0)
    ab._load_surface_controls()
    yield tmp_path
    # Leave the module as other tests expect it: the panel's defaults.
    with ab._surface_controls_lock:
        ab._surface_controls.clear()
        ab._surface_controls.update(ab._SURFACE_CONTROL_DEFAULTS)


def test_controls_defaults(phone):
    answer = json.loads(ab.get_surface_controls())
    expected = {k: True for k in ab._SURFACE_CONTROL_DEFAULTS}
    expected["growth_while_charging_only"] = False   # her growth runs on battery
    assert answer["controls"] == expected
    assert set(answer["growth"]) == {"waits_for_charging", "control_on", "charging",
                                     "paired_surface", "stepping_aside"}


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
    assert all(ab.surface_control(k) == v for k, v in ab._SURFACE_CONTROL_DEFAULTS.items())


def test_controls_file_stays_with_the_phone():
    # surface_sensory_* files are the phone's own; they never move with her.
    assert ab._SURFACE_CONTROLS_FILE.startswith("surface_sensory_")


@pytest.mark.parametrize("charging,expected", [(False, True), (True, False), (None, False)])
def test_gate_holds_only_on_a_not_charging_reading(phone, monkeypatch, charging, expected):
    ab.set_surface_control("growth_while_charging_only", True)
    sensors = {} if charging is None else {"charging": charging}
    monkeypatch.setattr(ab, "_hardware_sensors", sensors)
    assert ab._growth_waits_for_charging() is expected
    assert ab._growth_status()["charging"] == charging


def test_gate_off_on_a_paired_surface(phone, monkeypatch):
    ab.set_surface_control("growth_while_charging_only", True)
    monkeypatch.setattr(ab, "_hardware_sensors", {"charging": False})
    monkeypatch.setattr(ab, "_surface_only", True)
    assert ab._growth_waits_for_charging() is False
    assert ab._growth_status()["paired_surface"] is True


def test_gate_off_when_sir_turns_the_control_off(phone, monkeypatch):
    monkeypatch.setattr(ab, "_hardware_sensors", {"charging": False})
    ab.set_surface_control("growth_while_charging_only", True)
    assert ab._growth_waits_for_charging() is True
    ab.set_surface_control("growth_while_charging_only", False)
    assert ab._growth_waits_for_charging() is False


def test_growth_sources_wait_but_her_conversations_do_not(phone, monkeypatch):
    ab.set_surface_control("growth_while_charging_only", True)
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
        def run_dream_cycle(self, systems, may_continue=None) -> None:
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


# ── Stepping aside while Sir talks with her ───────────────────────────────────

def test_growth_runs_on_battery_by_default(phone, monkeypatch):
    monkeypatch.setattr(ab, "_hardware_sensors", {"charging": False})
    assert ab._growth_may_run() is True


def test_conversation_window(phone, monkeypatch):
    now = time.time()
    monkeypatch.setattr(ab, "_last_output_time", now - 5.0)
    assert ab._conversation_active(now) is True
    assert ab._growth_may_run() is False
    monkeypatch.setattr(ab, "_last_output_time", now - ab.CONVERSATION_QUIET_S - 1.0)
    assert ab._conversation_active(now) is False
    assert ab._growth_may_run() is True


def test_live_turn_marks_the_conversation(phone, monkeypatch):
    monkeypatch.setattr(ab, "_lock", ab._FieldLock())
    assert ab._conversation_active() is False
    with ab._PresentClaim():
        assert ab._present_active == 1
        assert ab._conversation_active() is True
        assert ab._growth_may_run() is False
    assert ab._present_active == 0
    assert ab._conversation_active() is False


def test_every_background_source_steps_aside(phone, monkeypatch):
    monkeypatch.setattr(ab, "_historical_experience_live_idle", lambda yield_to_messenger=True: True)
    monkeypatch.setattr(ab, "_background_breathing_room", lambda *a, **k: True)
    monkeypatch.setattr(ab, "_systems", {})
    assert ab._history_stream_live_idle() and ab._praxis_live_idle()
    assert ab._messenger_live_idle() and ab._clone_absorption_live_idle()
    monkeypatch.setattr(ab, "_last_output_time", time.time())
    assert not ab._history_stream_live_idle()
    assert not ab._praxis_live_idle()
    assert not ab._messenger_live_idle()
    assert not ab._clone_absorption_live_idle()
    assert ab._growth_status()["stepping_aside"] is True


def test_her_initiative_is_not_held_by_the_conversation():
    # The proactive loop is paced by the shared breathing room only; the
    # conversation window must not appear there.
    src = Path(ab.__file__).read_text(encoding="utf-8")
    start = src.index("def _background_breathing_room(")
    body = src[start:src.index("\ndef ", start + 10)]
    assert "_conversation_active" not in body


def test_live_turn_releases_curiosity_and_quiet_resumes_it(monkeypatch):
    sys.path.insert(0, str(_ROOT))
    ce = pytest.importorskip("aurora_curiosity_engine")
    ce.reset_curiosity_interrupt()
    monkeypatch.setattr(ab, "_lock", ab._FieldLock())
    monkeypatch.setattr(ab, "_present_active", 0)
    with ab._PresentClaim():
        assert ce._CYCLE_INTERRUPTIBLE.is_set()

    class _Engine:
        systems: dict = {}

        def __init__(self) -> None:
            self.cycles = 0

        def reset_idle_counter(self) -> None:
            pass

        def run_curiosity_cycle(self) -> None:
            self.cycles += 1

    # Once the owner says the present has gone quiet, her curiosity is
    # released by its own loop and carries on.
    engine = _Engine()
    ce._CURIOSITY_THREAD = None
    ce.start_curiosity_background(engine, tick_interval_s=0.05, may_run=lambda: True)
    time.sleep(0.3)
    ce._CURIOSITY_STOP.set()
    ce._CURIOSITY_THREAD.join(2)
    ce._CURIOSITY_THREAD = None
    ce.reset_curiosity_interrupt()
    assert engine.cycles > 0


def test_dream_holds_between_steps_and_resumes(monkeypatch):
    sys.path.insert(0, str(_ROOT))
    qd = pytest.importorskip("aurora_quantum_dream_substrate")
    steps = []
    for name in ("_temporal_feedback_pass", "_consciousness_fusion_cycle", "_dimensional_collapse"):
        monkeypatch.setattr(qd, name, lambda systems, _n=name: steps.append(_n))
    sub = qd.QuantumDreamSubstrate()
    monkeypatch.setattr(sub._entanglement, "auto_entangle_from_genealogy", lambda systems: steps.append("entangle") or 0)
    monkeypatch.setattr(sub._entanglement, "propagate", lambda systems: steps.append("propagate"))
    monkeypatch.setattr(sub, "_dream_encounter_with_selves", lambda systems: steps.append("encounter"))
    monkeypatch.setattr(sub, "_run_mtsl_perturbation_probe", lambda systems: steps.append("probe"))
    real_wait = qd._dream_stop.wait
    monkeypatch.setattr(qd._dream_stop, "wait", lambda t=None: real_wait(0.01))
    qd._dream_stop.clear()
    # Sir is talking for the first three checks between steps, then quiet.
    answers = iter([False, False, False])
    sub.run_dream_cycle({}, may_continue=lambda: next(answers, True))
    assert steps == ["entangle", "propagate", "_temporal_feedback_pass",
                     "_consciousness_fusion_cycle", "_dimensional_collapse",
                     "encounter", "probe"]


def test_dream_stops_cleanly_while_held(monkeypatch):
    sys.path.insert(0, str(_ROOT))
    qd = pytest.importorskip("aurora_quantum_dream_substrate")
    sub = qd.QuantumDreamSubstrate()
    steps = []
    monkeypatch.setattr(sub._entanglement, "auto_entangle_from_genealogy", lambda systems: steps.append(1) or 0)
    monkeypatch.setattr(sub._entanglement, "propagate", lambda systems: steps.append(2))
    qd._dream_stop.set()
    try:
        sub.run_dream_cycle({}, may_continue=lambda: False)
    finally:
        qd._dream_stop.clear()
    assert steps == [1]

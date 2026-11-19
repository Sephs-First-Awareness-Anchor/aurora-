#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
test_phone_field_not_held_at_boot.py -- her first turns on the phone are
not queued behind boot work (Sir, 2026-11-19, Build 980: "hey Aurora" sat
at surface_queued for three minutes).

These pin:
  * the clone harvest is absorbed in its own thread, in chunks, with the
    field lock and an idle gate -- never under one long hold of the field;
  * her history stream yields while the harvest absorbs, so it still
    follows the harvest as before;
  * the Hub can read who holds her field and for how long.
"""
from __future__ import annotations

import json
import os
import sys
import threading

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANDROID_PY_DIR = os.path.join(REPO_ROOT, "flutter_app", "android", "app", "src", "main", "python")


@pytest.fixture()
def bridge(tmp_path, monkeypatch):
    if ANDROID_PY_DIR not in sys.path:
        sys.path.insert(0, ANDROID_PY_DIR)
    import aurora_bridge
    monkeypatch.setattr(aurora_bridge, "_systems", {"state_dir": str(tmp_path)})
    return aurora_bridge


def test_clone_harvest_absorbs_in_chunks_off_the_field(bridge, monkeypatch, tmp_path):
    import aurora_internal.aurora_clone_harvest as harvest
    seen = {}
    started = threading.Event()
    release = threading.Event()

    def fake_absorb(systems, *, state_dir=None, field_lock=None, live_idle=None, **kw):
        seen["state_dir"] = state_dir
        seen["field_lock"] = field_lock
        seen["live_idle"] = live_idle
        # While it absorbs, the field is free for a live turn.
        seen["field_free_during_absorb"] = not bridge._lock.locked()
        started.set()
        release.wait(5)
        return {"status": "absorbed", "harvest_id": "h"}

    monkeypatch.setattr(harvest, "absorb_harvest", fake_absorb)
    bridge._start_clone_absorption(str(tmp_path))
    assert started.wait(5)
    assert seen["field_lock"] is bridge._lock
    assert callable(seen["live_idle"])
    assert seen["field_free_during_absorb"] is True
    # Her history stream waits for the harvest.
    assert bridge._clone_absorption_running.is_set()
    assert bridge._historical_experience_live_idle() is False
    release.set()
    for _ in range(100):
        if not bridge._clone_absorption_running.is_set():
            break
        threading.Event().wait(0.05)
    assert not bridge._clone_absorption_running.is_set()
    assert bridge._systems["_clone_harvest_absorb"]["status"] == "absorbed"


def test_harvest_takes_the_field_only_when_no_turn_waits(bridge, monkeypatch):
    monkeypatch.setattr(bridge, "_background_breathing_room", lambda *a, **k: True)
    monkeypatch.setattr(bridge, "_present_waiting", 1)
    assert bridge._clone_absorption_live_idle() is False
    monkeypatch.setattr(bridge, "_present_waiting", 0)
    assert bridge._clone_absorption_live_idle() is True


def test_boot_no_longer_absorbs_under_one_field_hold():
    src = open(os.path.join(ANDROID_PY_DIR, "aurora_bridge.py"), encoding="utf-8").read()
    assert "_clone_absorb = absorb_harvest(_systems, state_dir=" not in src
    assert "_start_clone_absorption(state_dir if state_dir else \"aurora_state\")" in src


def test_field_status_names_the_holder(bridge):
    status = json.loads(bridge.get_field_status())
    assert status["held"] is False
    with bridge._lock:
        threading.current_thread().name  # the holder is this thread
        status = json.loads(bridge.get_field_status())
    assert status["held"] is True
    assert status["holder"] == threading.current_thread().name
    assert status["held_s"] >= 0.0
    for key in ("present_waiting", "boot_stage", "boot_finished", "clone_harvest", "surface_only"):
        assert key in status

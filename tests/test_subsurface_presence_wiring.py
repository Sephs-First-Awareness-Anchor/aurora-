#!/usr/bin/env python3
"""
Regression coverage for the Subsurface Presence and Evidence Scout
spec's daemon-level wiring (Step 2/3, aurora_daemon.py) -- distinct
from tests/test_subsurface_live_presence.py, which only exercises the
underlying aurora_internal.dual_strata.subsurface_presence primitives
directly. This file tests the two new functions aurora_daemon.py's
run() loop actually calls:

- _consume_subsurface_turn_events(): reads pending turn_open events
  Surface deposited and publishes an updated presence frame.
- _start_subsurface_heartbeat_thread(): a dedicated thread proving
  Subsurface liveness independent of whatever the main loop happens to
  be blocked on.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aurora_daemon
from aurora_internal.dual_strata import subsurface_presence as sp


def test_consume_subsurface_turn_events_publishes_a_presence_frame(tmp_path, monkeypatch):
    monkeypatch.setattr(aurora_daemon, "_STATE_DIR", tmp_path, raising=False)

    sp.write_turn_open(tmp_path, turn_id="t1", raw_input="what time is it")
    aurora_daemon._consume_subsurface_turn_events({})

    frame = sp.read_presence_frame(tmp_path)
    assert frame is not None
    assert frame["turn_id"] == "t1"
    assert "what time is it" in frame["continuity_summary"]


def test_consume_subsurface_turn_events_is_a_noop_with_no_pending_events(tmp_path, monkeypatch):
    monkeypatch.setattr(aurora_daemon, "_STATE_DIR", tmp_path, raising=False)

    aurora_daemon._consume_subsurface_turn_events({})
    # No turn_open was ever written, so no frame should have been created.
    assert sp.read_presence_frame(tmp_path) is None


def test_consume_subsurface_turn_events_uses_the_most_recent_event(tmp_path, monkeypatch):
    monkeypatch.setattr(aurora_daemon, "_STATE_DIR", tmp_path, raising=False)

    sp.write_turn_open(tmp_path, turn_id="t1", raw_input="first")
    sp.write_turn_open(tmp_path, turn_id="t2", raw_input="second")
    aurora_daemon._consume_subsurface_turn_events({})

    frame = sp.read_presence_frame(tmp_path)
    assert frame["turn_id"] == "t2"


def test_consume_subsurface_turn_events_does_not_replay_already_consumed_events(tmp_path, monkeypatch):
    monkeypatch.setattr(aurora_daemon, "_STATE_DIR", tmp_path, raising=False)

    sp.write_turn_open(tmp_path, turn_id="t1", raw_input="first")
    aurora_daemon._consume_subsurface_turn_events({})
    first_seq = sp.read_presence_frame(tmp_path)["seq"]

    # Second cycle, nothing new deposited -- frame must not be rewritten
    # (rewriting on every idle cycle is exactly the "large status document
    # multiple times per second" behavior spec section 14 forbids).
    aurora_daemon._consume_subsurface_turn_events({})
    assert sp.read_presence_frame(tmp_path)["seq"] == first_seq


def test_heartbeat_thread_actually_writes_a_live_heartbeat(tmp_path, monkeypatch):
    monkeypatch.setattr(aurora_daemon, "_STATE_DIR", tmp_path, raising=False)

    assert sp.heartbeat_gap_ms(tmp_path) is None  # nothing written yet
    aurora_daemon._start_subsurface_heartbeat_thread()

    deadline = time.time() + 3.0
    gap = None
    while time.time() < deadline:
        gap = sp.heartbeat_gap_ms(tmp_path)
        if gap is not None:
            break
        time.sleep(0.05)

    assert gap is not None
    assert gap < 2000.0


def test_surface_daemon_imports_and_uses_write_turn_open():
    # Sunni & Cael: a direct static check that aurora_surface_daemon.py's
    # write_turn_open call site is really there -- catches the class of
    # regression where the import exists but the call site is later
    # deleted/refactored away without anyone noticing, since that
    # wouldn't show up as an import error.
    import inspect
    import aurora_surface_daemon
    source = inspect.getsource(aurora_surface_daemon)
    assert "write_turn_open(" in source
    assert "_presence_metrics.record_surface_turn_latency_ms(" in source

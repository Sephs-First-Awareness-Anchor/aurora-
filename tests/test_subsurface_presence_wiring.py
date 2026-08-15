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


def test_consume_subsurface_turn_events_processes_every_turn_open_in_order(tmp_path, monkeypatch):
    monkeypatch.setattr(aurora_daemon, "_STATE_DIR", tmp_path, raising=False)

    sp.write_turn_open(tmp_path, turn_id="t1", raw_input="first")
    sp.write_turn_open(tmp_path, turn_id="t2", raw_input="second")
    aurora_daemon._consume_subsurface_turn_events({})

    # Both events are processed in order -- the later turn's own frame
    # is what remains, same end state as before, but now because every
    # event in the batch was actually integrated, not because only
    # events[-1] was ever looked at.
    frame = sp.read_presence_frame(tmp_path)
    assert frame["turn_id"] == "t2"


def test_consume_subsurface_turn_events_integrates_turn_open_and_interpreted_turn_together(tmp_path, monkeypatch):
    # Build 694 step 3: the actual defect this step fixes. The old
    # events[-1] collapse either dropped interpreted_turn's fields
    # entirely (if turn_open happened to be the batch's last entry) or
    # mis-read an interpreted_turn event as though it were a turn_open
    # (interpreted_turn events have no "raw_input" field at all, so the
    # old code's f"turn open: {latest.get('raw_input', '')}" would
    # silently render as "turn open: " with nothing after the colon).
    # Both events, same turn_id, same batch -- both must land in the
    # resulting frame.
    monkeypatch.setattr(aurora_daemon, "_STATE_DIR", tmp_path, raising=False)

    sp.write_turn_open(tmp_path, turn_id="t1", raw_input="what is a guitar chord")
    sp.write_interpreted_turn(
        tmp_path,
        turn_id="t1",
        interpreted_meaning="asking about guitar chord theory",
        inferred_purpose="informational",
        interpretation_confidence=0.8,
        response_confidence=0.3,
        response_fit_pressure=0.7,
        resolved_referents=["it"],
        knowledge_gaps=["chord_theory"],
        representation_refs=["guitar_concept"],
    )
    aurora_daemon._consume_subsurface_turn_events({})

    frame = sp.read_presence_frame(tmp_path)
    assert frame["turn_id"] == "t1"
    assert frame["turn_open_at"] is not None
    assert frame["interpreted_at"] is not None
    assert "guitar chord theory" in frame["interpreted_meaning"]
    assert frame["inferred_purpose"] == "informational"
    assert frame["interpretation_confidence"] == 0.8
    assert frame["response_confidence"] == 0.3
    assert frame["response_fit_pressure"] == 0.7
    assert frame["resolved_referents"] == ["it"]
    assert frame["knowledge_gaps"] == ["chord_theory"]
    assert frame["representation_refs"] == ["guitar_concept"]


def test_consume_subsurface_turn_events_processes_reverse_order_batch_too(tmp_path, monkeypatch):
    # Same guarantee as above, but with interpreted_turn arriving BEFORE
    # turn_open in the read order (write_interpreted_turn() first) --
    # neither one may silently overwrite the other's fields regardless
    # of which lands first in the batch.
    monkeypatch.setattr(aurora_daemon, "_STATE_DIR", tmp_path, raising=False)

    sp.write_interpreted_turn(
        tmp_path, turn_id="t1", interpreted_meaning="a reordered-batch case",
        interpretation_confidence=0.9, response_confidence=0.5, response_fit_pressure=0.5,
    )
    sp.write_turn_open(tmp_path, turn_id="t1", raw_input="raw text arriving second in this batch")
    aurora_daemon._consume_subsurface_turn_events({})

    frame = sp.read_presence_frame(tmp_path)
    assert frame["interpreted_meaning"] == "a reordered-batch case"
    assert frame["turn_open_at"] is not None
    assert "raw text arriving second" in frame["continuity_summary"]


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


def test_process_external_user_turn_imports_and_uses_write_turn_open():
    # Build 694 step 2: the canonical write_turn_open() call site moved
    # from aurora_surface_daemon.py (only the desktop daemon path ever
    # runs it) into aurora.process_external_user_turn() itself, so the
    # Android bridge -- which calls process_external_user_turn() directly
    # and never goes through aurora_surface_daemon.py at all -- produces
    # a turn-open event too. Same static-check intent as before (catches
    # the call site being deleted/refactored away without anyone
    # noticing), just checking the new canonical location.
    import inspect
    import aurora
    source = inspect.getsource(aurora.process_external_user_turn)
    assert "write_turn_open" in source


def test_surface_daemon_no_longer_double_publishes_turn_open():
    # aurora_surface_daemon.py calls process_external_user_turn() (which
    # now publishes turn_open itself) -- it must not ALSO publish a
    # second, logically-identical turn_open event for the same turn_id.
    import inspect
    import aurora_surface_daemon
    source = inspect.getsource(aurora_surface_daemon)
    assert "write_turn_open(" not in source
    assert "_presence_metrics.record_surface_turn_latency_ms(" in source

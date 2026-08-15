#!/usr/bin/env python3
"""
Regression coverage for aurora_internal/dual_strata/subsurface_presence.py
(Subsurface Presence and Evidence Scout spec, sections 5, 13-14): the
live turn_open/presence_frame/heartbeat channel Subsurface uses to know
a conversational turn is happening NOW, independent of the heavy 60s
daemon_status.json / subsurface_projection.json diagnostic path.

Tested directly against a tmp_path state_dir, independent of any daemon
process actually running.
"""
from __future__ import annotations

import json
import time

import pytest

from aurora_internal.dual_strata import subsurface_presence as sp


def test_write_turn_open_creates_a_readable_pending_event(tmp_path):
    event_id = sp.write_turn_open(tmp_path, turn_id="t1", raw_input="hello")
    assert event_id

    pending = sp.read_and_clear_turn_events(tmp_path)
    assert len(pending) == 1
    assert pending[0]["event_id"] == event_id
    assert pending[0]["turn_id"] == "t1"
    assert pending[0]["kind"] == "turn_open"
    assert pending[0]["raw_input"] == "hello"


def test_read_and_clear_turn_events_does_not_return_the_same_event_twice(tmp_path):
    sp.write_turn_open(tmp_path, turn_id="t1", raw_input="hello")

    first = sp.read_and_clear_turn_events(tmp_path)
    second = sp.read_and_clear_turn_events(tmp_path)
    assert len(first) == 1
    assert second == []


def test_read_and_clear_turn_events_with_no_file_returns_empty(tmp_path):
    assert sp.read_and_clear_turn_events(tmp_path) == []


def test_multiple_turn_open_events_are_all_returned_in_order(tmp_path):
    sp.write_turn_open(tmp_path, turn_id="t1", raw_input="first")
    sp.write_turn_open(tmp_path, turn_id="t2", raw_input="second")

    pending = sp.read_and_clear_turn_events(tmp_path)
    assert [p["turn_id"] for p in pending] == ["t1", "t2"]


def test_write_presence_frame_then_read_round_trips(tmp_path):
    frame = sp.write_presence_frame(
        tmp_path,
        turn_id="t1",
        continuity_summary="settling into a new topic",
        unresolved_tensions=["ambiguous referent"],
        scout_requests_pending=1,
        response_fit_pressure=0.4,
    )
    assert frame["seq"] == 1
    assert frame["turn_id"] == "t1"

    read_back = sp.read_presence_frame(tmp_path)
    assert read_back is not None
    assert read_back["turn_id"] == "t1"
    assert read_back["unresolved_tensions"] == ["ambiguous referent"]
    assert read_back["scout_requests_pending"] == 1
    assert read_back["response_fit_pressure"] == pytest.approx(0.4)


def test_presence_frame_sequence_number_increments_across_writes(tmp_path):
    f1 = sp.write_presence_frame(tmp_path, turn_id="t1")
    f2 = sp.write_presence_frame(tmp_path, turn_id="t1")
    f3 = sp.write_presence_frame(tmp_path, turn_id="t2")
    assert (f1["seq"], f2["seq"], f3["seq"]) == (1, 2, 3)


def test_read_presence_frame_with_no_file_returns_none_not_raise(tmp_path):
    # Sunni & Cael: Surface must NEVER block waiting for a frame -- a
    # missing frame is a normal, expected state (daemon not started yet,
    # or hasn't emitted its first frame), not an error.
    assert sp.read_presence_frame(tmp_path) is None


def test_presence_frame_age_ms_reflects_real_elapsed_time(tmp_path):
    sp.write_presence_frame(tmp_path, turn_id="t1")
    time.sleep(0.05)
    age = sp.presence_frame_age_ms(tmp_path)
    assert age is not None
    assert age >= 40.0  # allow scheduler jitter under the 50ms sleep


def test_presence_frame_age_ms_with_no_frame_returns_none(tmp_path):
    assert sp.presence_frame_age_ms(tmp_path) is None


def test_heartbeat_gap_ms_with_no_heartbeat_ever_returns_none(tmp_path):
    assert sp.heartbeat_gap_ms(tmp_path) is None


def test_write_heartbeat_then_gap_is_small_immediately_after(tmp_path):
    sp.write_heartbeat(tmp_path)
    gap = sp.heartbeat_gap_ms(tmp_path)
    assert gap is not None
    assert gap < 500.0


def test_heartbeat_gap_grows_if_not_refreshed(tmp_path):
    sp.write_heartbeat(tmp_path)
    time.sleep(0.05)
    gap = sp.heartbeat_gap_ms(tmp_path)
    assert gap is not None
    assert gap >= 40.0


def test_heartbeat_is_independent_of_presence_frame_writes(tmp_path):
    # Sunni & Cael: the whole point of a separate heartbeat file (spec
    # section 14) is that it can be refreshed on every loop tick WITHOUT
    # rewriting the (potentially larger) presence frame -- proving
    # liveness even on ticks where nothing about the frame changed.
    sp.write_presence_frame(tmp_path, turn_id="t1")
    frame_before = json.loads((tmp_path / "subsurface_presence_frame.json").read_text())

    sp.write_heartbeat(tmp_path)
    sp.write_heartbeat(tmp_path)

    frame_after = json.loads((tmp_path / "subsurface_presence_frame.json").read_text())
    assert frame_before == frame_after


def test_turn_events_file_is_bounded(tmp_path):
    for i in range(sp._MAX_TURN_EVENTS + 10):
        sp.write_turn_open(tmp_path, turn_id=f"t{i}")
    raw = json.loads((tmp_path / sp._TURN_EVENTS_FILENAME).read_text())
    assert len(raw) == sp._MAX_TURN_EVENTS

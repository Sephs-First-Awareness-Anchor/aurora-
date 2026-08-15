#!/usr/bin/env python3
"""
Regression coverage for aurora._try_poedex_lookup(): it must never
block Surface waiting on a live Poedex/Room response. Bound lessons (a
local file read) remain instant and are unaffected.

Build 694 step 9 update: this no longer dispatches a ScoutRequest
directly (that crossed the Surface/Subsurface boundary the wrong way --
see subsurface_presence.write_evidence_need()'s docstring). Surface now
only publishes an evidence_need event on the turn-events channel;
Subsurface (integrate_evidence_need_event()) is the sole owner of the
actual ScoutRequest dispatch. These tests check the event Surface
writes, and separately confirm consuming it produces a real queued
ScoutRequest.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aurora
from aurora_internal.scouting.broker import ScoutBroker
from aurora_internal.dual_strata.subsurface_presence import (
    read_and_clear_turn_events,
    integrate_turn_event,
)


def test_lookup_with_no_bound_lesson_returns_immediately_not_after_a_wait(tmp_path):
    systems = {"state_dir": tmp_path, "_current_turn_id": "t1"}
    started = time.time()
    result = aurora._try_poedex_lookup("an unfamiliar topic", systems, timeout=5.0, use_researcher=True)
    elapsed = time.time() - started
    assert result == ""
    # The old blocking path polled for up to 35s (use_researcher=True) --
    # this must return essentially instantly instead.
    assert elapsed < 2.0


def test_lookup_publishes_an_evidence_need_event_not_a_direct_dispatch(tmp_path):
    systems = {"state_dir": tmp_path, "_current_turn_id": "t1"}
    aurora._try_poedex_lookup("guitar chord theory", systems, use_researcher=True)

    # Surface must not have touched the broker directly -- no queue
    # entry exists until Subsurface integrates the event below.
    broker = ScoutBroker(tmp_path)
    assert broker.queue_depth() == 0

    events = read_and_clear_turn_events(tmp_path)
    evidence_need_events = [e for e in events if e.get("kind") == "evidence_need"]
    assert len(evidence_need_events) == 1
    event = evidence_need_events[0]
    assert event["turn_id"] == "t1"
    assert event["request_kind"] == "knowledge_gap"
    assert event["inquiry"] == "guitar chord theory"


def test_integrating_the_evidence_need_event_actually_dispatches_a_scout_request(tmp_path):
    systems = {"state_dir": tmp_path, "_current_turn_id": "t1"}
    aurora._try_poedex_lookup("guitar chord theory", systems, use_researcher=True)

    events = read_and_clear_turn_events(tmp_path)
    evidence_need_events = [e for e in events if e.get("kind") == "evidence_need"]
    assert len(evidence_need_events) == 1
    integrated_kind = integrate_turn_event(tmp_path, evidence_need_events[0])
    assert integrated_kind == "evidence_need"

    broker = ScoutBroker(tmp_path)
    assert broker.queue_depth() == 1
    pending_files = list(broker.pending_dir.glob("*.json"))
    raw = json.loads(pending_files[0].read_text(encoding="utf-8"))
    assert raw["turn_id"] == "t1"
    assert raw["request_kind"] == "knowledge_gap"
    assert raw["inquiry"] == "guitar chord theory"


def test_lookup_still_returns_a_bound_lesson_instantly_without_dispatching(tmp_path):
    lessons_path = tmp_path / "poedex_lessons.json"
    lessons_path.write_text(json.dumps([
        {"question": "what is a guitar chord", "lesson": "A guitar chord is three or more notes played together."},
    ]), encoding="utf-8")

    systems = {"state_dir": tmp_path, "_current_turn_id": "t1"}
    result = aurora._try_poedex_lookup("what is a guitar chord", systems)
    assert "three or more notes" in result

    # A bound lesson satisfied the lookup -- no Scout request needed.
    broker = ScoutBroker(tmp_path)
    assert broker.queue_depth() == 0


def test_duplicate_topic_dispatches_do_not_flood_the_queue(tmp_path):
    systems = {"state_dir": tmp_path, "_current_turn_id": "t1"}
    for _ in range(3):
        aurora._try_poedex_lookup("the same recurring topic", systems, use_researcher=True)

    events = read_and_clear_turn_events(tmp_path)
    evidence_need_events = [e for e in events if e.get("kind") == "evidence_need"]
    for event in evidence_need_events:
        integrate_turn_event(tmp_path, event)

    broker = ScoutBroker(tmp_path)
    # ScoutBroker.dispatch() already collapses identical inquiry text --
    # three identical lookups must not produce three queued requests.
    assert broker.queue_depth() == 1


def test_lookup_never_raises_when_systems_is_malformed():
    result = aurora._try_poedex_lookup("some topic", {}, use_researcher=True)
    assert result == ""

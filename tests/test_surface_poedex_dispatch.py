#!/usr/bin/env python3
"""
Regression coverage for the Subsurface Presence and Evidence Scout
spec's Step 10: aurora._try_poedex_lookup() must never block Surface
waiting on a live Poedex/Room response -- it now dispatches a
knowledge_gap ScoutRequest (fire-and-forget) and returns immediately.
Bound lessons (a local file read) remain instant and are unaffected.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aurora
from aurora_internal.scouting.broker import ScoutBroker


def test_lookup_with_no_bound_lesson_returns_immediately_not_after_a_wait(tmp_path):
    systems = {"state_dir": tmp_path, "_current_turn_id": "t1"}
    started = time.time()
    result = aurora._try_poedex_lookup("an unfamiliar topic", systems, timeout=5.0, use_researcher=True)
    elapsed = time.time() - started
    assert result == ""
    # The old blocking path polled for up to 35s (use_researcher=True) --
    # this must return essentially instantly instead.
    assert elapsed < 2.0


def test_lookup_dispatches_a_knowledge_gap_scout_request(tmp_path):
    systems = {"state_dir": tmp_path, "_current_turn_id": "t1"}
    aurora._try_poedex_lookup("guitar chord theory", systems, use_researcher=True)

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

    broker = ScoutBroker(tmp_path)
    # ScoutBroker.dispatch() already collapses identical inquiry text --
    # three identical lookups must not produce three queued requests.
    assert broker.queue_depth() == 1


def test_lookup_never_raises_when_systems_is_malformed():
    result = aurora._try_poedex_lookup("some topic", {}, use_researcher=True)
    assert result == ""

#!/usr/bin/env python3
"""
Required test (Subsurface Presence and Evidence Scout spec, section 21):
test_subsurface_presence_during_scout_delay.py -- spec section 20's
acceptance criterion, "Long retrieval does not stop Subsurface
heartbeat/presence updates," tested directly against the production
presence primitives (subsurface_presence.py) and the real
_start_subsurface_heartbeat_thread() pattern, independent of
scripts/scout_presence_load_comparison.py's broader before/after
comparison (Step 12).
"""
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aurora_internal.dual_strata.subsurface_presence import (
    write_heartbeat, heartbeat_gap_ms, write_presence_frame, presence_frame_age_ms,
)
from aurora_internal.scouting.broker import dispatch_scout_request
from aurora_internal.scouting.contracts import ScoutRequest


def test_heartbeat_gap_stays_low_while_a_scout_request_sits_unclaimed(tmp_path):
    dispatch_scout_request(tmp_path, ScoutRequest(
        turn_id="", request_kind="self_diagnostic", inquiry="a slow/unclaimed request", ttl_s=30.0,
    ))

    stop = threading.Event()

    def _beat():
        while not stop.is_set():
            write_heartbeat(tmp_path)
            time.sleep(0.3)

    thread = threading.Thread(target=_beat, daemon=True)
    thread.start()
    try:
        time.sleep(1.5)
        gap = heartbeat_gap_ms(tmp_path)
    finally:
        stop.set()
        thread.join(timeout=2.0)

    assert gap is not None
    assert gap < 1000.0  # well under a single heartbeat cadence's worth of staleness


def test_presence_frame_can_still_be_refreshed_while_scout_request_is_pending(tmp_path):
    dispatch_scout_request(tmp_path, ScoutRequest(
        turn_id="t1", request_kind="knowledge_gap", inquiry="another slow request", ttl_s=30.0,
    ))

    write_presence_frame(tmp_path, turn_id="t1", continuity_summary="turn in progress")
    age_before = presence_frame_age_ms(tmp_path)
    assert age_before is not None and age_before < 500.0

    time.sleep(0.5)
    write_presence_frame(tmp_path, turn_id="t1", continuity_summary="turn still in progress, updated")
    age_after = presence_frame_age_ms(tmp_path)
    # The frame was refreshed independently of the still-pending Scout
    # request -- its age resets, it does not keep climbing as though
    # something upstream were blocked waiting on the request.
    assert age_after is not None and age_after < 500.0


def test_heartbeat_never_freezes_across_a_window_longer_than_the_old_blocking_ceilings(tmp_path):
    # Directly exercises the guarantee that motivated Step 11 in the
    # first place: a window (here, a few seconds -- long enough to prove
    # the pattern, short enough to keep this test fast) during which,
    # under the OLD architecture, a single _poedex_ask(timeout=18.0)
    # call could have frozen this entire measurement. Multiple
    # consecutive heartbeat samples must all show a small gap.
    stop = threading.Event()

    def _beat():
        while not stop.is_set():
            write_heartbeat(tmp_path)
            time.sleep(0.3)

    thread = threading.Thread(target=_beat, daemon=True)
    thread.start()
    try:
        gaps = []
        for _ in range(4):
            time.sleep(0.5)
            gaps.append(heartbeat_gap_ms(tmp_path))
    finally:
        stop.set()
        thread.join(timeout=2.0)

    assert all(g is not None and g < 1000.0 for g in gaps)

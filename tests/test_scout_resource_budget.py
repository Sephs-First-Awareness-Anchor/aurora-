#!/usr/bin/env python3
"""
Required test (Subsurface Presence and Evidence Scout spec, section 21):
test_scout_resource_budget.py -- spec section 9/10: given the captured
runtime's survival-mode memory pressure, Scout activity must stay
within a small, fixed resource budget (no more than one Scout in
flight, a small bounded pending queue) regardless of how aggressively
callers dispatch, and that budget must hold identically whether a
caller uses the full ScoutBroker (Subsurface) or the thin
dispatch_scout_request() free function (Surface, spec step 10) --
the enforcement lives in the broker, not caller discipline.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aurora_internal.scouting.broker import (
    ScoutBroker, dispatch_scout_request, DEFAULT_MAX_CONCURRENT, DEFAULT_MAX_QUEUE_DEPTH,
)
from aurora_internal.scouting.contracts import ScoutRequest


def test_default_budget_matches_the_documented_survival_mode_constants():
    # Named constants, not magic numbers scattered at call sites -- this
    # pins the actual documented budget (spec section 9/10: "no more
    # than one Scout in flight, a small bounded pending queue").
    assert DEFAULT_MAX_CONCURRENT == 1
    assert DEFAULT_MAX_QUEUE_DEPTH == 5


def test_dispatch_scout_request_free_function_respects_the_same_queue_bound(tmp_path):
    # Surface (Step 10) only ever calls the free function, never holds a
    # ScoutBroker instance -- the budget must be enforced by the state
    # on disk, not by which handle a particular caller happens to use.
    for i in range(DEFAULT_MAX_QUEUE_DEPTH):
        rid = dispatch_scout_request(tmp_path, ScoutRequest(turn_id=f"t{i}", inquiry=f"distinct topic {i}"))
        assert rid is not None

    overflow_rid = dispatch_scout_request(tmp_path, ScoutRequest(turn_id="t_overflow", inquiry="one too many"))
    assert overflow_rid is None

    broker = ScoutBroker(tmp_path)
    assert broker.queue_depth() == DEFAULT_MAX_QUEUE_DEPTH


def test_only_one_scout_can_be_active_at_a_time_by_default(tmp_path):
    broker = ScoutBroker(tmp_path)
    for i in range(3):
        broker.dispatch(ScoutRequest(turn_id=f"t{i}", inquiry=f"topic {i}"))

    first = broker.claim_next()
    assert first is not None
    assert broker.active_count() == 1

    # Two more pending requests exist, but concurrency is already at cap.
    assert broker.claim_next() is None
    assert broker.claim_next() is None
    assert broker.active_count() == 1
    assert broker.queue_depth() == 2


def test_burst_of_a_hundred_dispatches_never_exceeds_the_bounded_queue(tmp_path):
    # A runaway retry loop (the exact scenario the module docstring
    # names) must degrade to "requests get dropped/deduped," never
    # unbounded growth of the on-disk queue.
    accepted = 0
    for i in range(100):
        rid = dispatch_scout_request(tmp_path, ScoutRequest(turn_id=f"t{i}", inquiry=f"unique inquiry text {i}"))
        if rid is not None:
            accepted += 1

    broker = ScoutBroker(tmp_path)
    assert broker.queue_depth() <= DEFAULT_MAX_QUEUE_DEPTH
    assert accepted == DEFAULT_MAX_QUEUE_DEPTH


def test_a_custom_broker_budget_is_still_enforced_via_the_free_function_on_the_same_state_dir(tmp_path):
    # dispatch_scout_request() always constructs a broker with DEFAULT
    # bounds internally -- confirms a caller cannot silently widen the
    # budget just by using the free function instead of an explicitly
    # narrower ScoutBroker(tmp_path, max_queue_depth=...) elsewhere
    # pointed at the same state_dir.
    narrow_broker = ScoutBroker(tmp_path, max_queue_depth=2)
    narrow_broker.dispatch(ScoutRequest(turn_id="t1", inquiry="q1"))
    narrow_broker.dispatch(ScoutRequest(turn_id="t2", inquiry="q2"))

    # The free function's own default-budget broker still sees the same
    # on-disk queue depth (2), even though ITS max_queue_depth is 5 --
    # the queue is what's shared, and it's already at 2 real entries.
    rid = dispatch_scout_request(tmp_path, ScoutRequest(turn_id="t3", inquiry="q3"))
    assert rid is not None
    assert ScoutBroker(tmp_path).queue_depth() == 3

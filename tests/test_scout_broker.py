#!/usr/bin/env python3
"""
Regression coverage for aurora_internal/scouting/broker.py
(Subsurface Presence and Evidence Scout spec, section 10): bounded
queue, one-response-fit-Scout-per-turn, duplicate-inquiry collapse,
concurrency, TTL expiry, and the claim/submit round trip a Scout worker
(spec step 6) will drive.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aurora_internal.scouting.broker import ScoutBroker
from aurora_internal.scouting.contracts import ScoutRequest, ScoutReport


def test_dispatch_then_claim_then_submit_round_trip(tmp_path):
    broker = ScoutBroker(tmp_path)
    req = ScoutRequest(turn_id="t1", inquiry="chord theory")

    rid = broker.dispatch(req)
    assert rid == req.request_id
    assert broker.queue_depth() == 1

    claimed = broker.claim_next()
    assert claimed is not None
    assert claimed.request_id == req.request_id
    assert broker.queue_depth() == 0
    assert broker.active_count() == 1

    report = ScoutReport(request_id=req.request_id, turn_id="t1", status="ok", confidence=0.6)
    broker.submit_report(report)
    assert broker.active_count() == 0

    reports = broker.poll_reports()
    assert len(reports) == 1
    assert reports[0].request_id == req.request_id
    assert reports[0].confidence == 0.6

    # poll_reports() drains -- a second call returns nothing new.
    assert broker.poll_reports() == []


def test_only_one_response_fit_scout_per_turn(tmp_path):
    broker = ScoutBroker(tmp_path)
    req_a = ScoutRequest(turn_id="t1", request_kind="response_fit", inquiry="inquiry A")
    req_b = ScoutRequest(turn_id="t1", request_kind="response_fit", inquiry="inquiry B")

    rid_a = broker.dispatch(req_a)
    rid_b = broker.dispatch(req_b)

    # The second dispatch for the SAME turn+kind must return the
    # existing request's id, not create a second pending file.
    assert rid_b == rid_a
    assert broker.queue_depth() == 1


def test_response_fit_cap_is_per_turn_not_global(tmp_path):
    broker = ScoutBroker(tmp_path)
    rid_1 = broker.dispatch(ScoutRequest(turn_id="t1", request_kind="response_fit", inquiry="q1"))
    rid_2 = broker.dispatch(ScoutRequest(turn_id="t2", request_kind="response_fit", inquiry="q2"))
    assert rid_1 != rid_2
    assert broker.queue_depth() == 2


def test_duplicate_inquiry_text_is_collapsed_across_turns(tmp_path):
    broker = ScoutBroker(tmp_path)
    rid_1 = broker.dispatch(ScoutRequest(turn_id="t1", inquiry="what is a guitar chord"))
    rid_2 = broker.dispatch(ScoutRequest(turn_id="t2", inquiry="what is a guitar chord"))
    assert rid_1 == rid_2
    assert broker.queue_depth() == 1


def test_bounded_queue_rejects_dispatch_past_max_depth(tmp_path):
    broker = ScoutBroker(tmp_path, max_queue_depth=2)
    r1 = broker.dispatch(ScoutRequest(turn_id="t1", inquiry="q1"))
    r2 = broker.dispatch(ScoutRequest(turn_id="t2", inquiry="q2"))
    r3 = broker.dispatch(ScoutRequest(turn_id="t3", inquiry="q3"))
    assert r1 is not None and r2 is not None
    assert r3 is None
    assert broker.queue_depth() == 2


def test_claim_next_respects_max_concurrent(tmp_path):
    broker = ScoutBroker(tmp_path, max_concurrent=1, max_queue_depth=5)
    broker.dispatch(ScoutRequest(turn_id="t1", inquiry="q1"))
    broker.dispatch(ScoutRequest(turn_id="t2", inquiry="q2"))

    first = broker.claim_next()
    assert first is not None
    assert broker.active_count() == 1

    # Concurrency is already at the cap -- a second claim must return
    # None even though a second request is still pending.
    second = broker.claim_next()
    assert second is None
    assert broker.queue_depth() == 1


def test_claim_next_returns_none_when_queue_is_empty(tmp_path):
    broker = ScoutBroker(tmp_path)
    assert broker.claim_next() is None


def test_expired_pending_request_is_removed_and_never_claimable(tmp_path):
    broker = ScoutBroker(tmp_path)
    req = ScoutRequest(turn_id="t1", inquiry="q1", ttl_s=0.05)
    broker.dispatch(req)
    time.sleep(0.1)

    assert broker.claim_next() is None  # expired during claim attempt
    assert broker.queue_depth() == 0


def test_expire_stale_requests_sweeps_pending_and_claimed(tmp_path):
    broker = ScoutBroker(tmp_path, max_concurrent=2)
    req_a = ScoutRequest(turn_id="t1", inquiry="q1", ttl_s=0.05)
    req_b = ScoutRequest(turn_id="t2", inquiry="q2", ttl_s=0.05)
    broker.dispatch(req_a)
    broker.dispatch(req_b)
    broker.claim_next()  # claims req_a (oldest first)

    time.sleep(0.1)
    expired = broker.expire_stale_requests()
    assert expired == 2
    assert broker.queue_depth() == 0
    assert broker.active_count() == 0


def test_scout_failure_report_still_completes_the_round_trip(tmp_path):
    # spec section 10: "Scout failure must never block Aurora" -- a
    # failed/cancelled report is still a normal submit_report() call,
    # not a broker-level error state.
    broker = ScoutBroker(tmp_path)
    req = ScoutRequest(turn_id="t1", inquiry="q1")
    broker.dispatch(req)
    claimed = broker.claim_next()
    broker.submit_report(ScoutReport(request_id=claimed.request_id, turn_id="t1", status="failed"))

    reports = broker.poll_reports()
    assert len(reports) == 1
    assert reports[0].status == "failed"
    assert broker.active_count() == 0


def test_two_broker_instances_share_the_same_file_backed_queue(tmp_path):
    # Surface/Subsurface (dispatch/poll) and the Scout worker (claim/
    # submit) run in SEPARATE processes -- this is the actual contract
    # that has to hold, not just one object's in-memory state.
    dispatcher = ScoutBroker(tmp_path)
    worker = ScoutBroker(tmp_path)

    req = ScoutRequest(turn_id="t1", inquiry="q1")
    dispatcher.dispatch(req)

    claimed = worker.claim_next()
    assert claimed is not None
    worker.submit_report(ScoutReport(request_id=claimed.request_id, turn_id="t1", status="ok"))

    reports = dispatcher.poll_reports()
    assert len(reports) == 1

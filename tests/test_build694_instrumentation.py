#!/usr/bin/env python3
"""
Aurora Build 694 step 17 (Subsurface Presence and Evidence Scout spec,
section 30): "Add/verify" a named list of instrumentation fields, so the
implementation can empirically answer "did Subsurface become more
present?" and "did generic admissibility decrease because unresolved
pressure is now acted upon?"

Covers the new PresenceMetrics recorders/snapshot fields directly, and
the wiring of a `metrics` recorder through
subsurface_presence.integrate_turn_open_event/integrate_interpreted_turn_event/
integrate_evidence_need_event/integrate_turn_event and
dispatch_response_fit_scout -- all additive and optional (a caller that
doesn't pass `metrics` sees no behavior change), so this file also
confirms omitting `metrics` is still silently safe.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aurora_internal.dual_strata.presence_metrics import PresenceMetrics
from aurora_internal.dual_strata import subsurface_presence as sp
from aurora_internal.scouting.broker import ScoutBroker


# ── PresenceMetrics: new recorders/snapshot fields ──────────────────────────

def test_new_recorders_all_exist_and_are_callable():
    m = PresenceMetrics(role="test")
    m.record_turn_open_latency_ms(10.0)
    m.record_interpreted_turn_latency_ms(20.0)
    m.record_presence_processing_latency_ms(5.0)
    m.set_presence_event_queue_depth(3)
    m.record_response_fit_pressure(0.6)
    m.record_knowledge_gap_pressure(0.2)
    m.record_scout_dispatch_reason("trigger_a_pressure")
    m.record_scout_request_kind("response_fit")
    m.record_scout_backend("local_lessons")
    m.record_same_turn_wait_ms(1200.0)
    m.record_same_turn_binding_used(True)
    m.record_same_turn_binding_used(False)
    m.record_abstain_before_scout()
    m.record_abstain_after_scout()
    m.record_abstain_rescue_attempted()
    m.record_abstain_rescue_succeeded()


def test_snapshot_contains_every_new_field():
    m = PresenceMetrics(role="test")
    m.record_turn_open_latency_ms(10.0)
    m.record_interpreted_turn_latency_ms(20.0)
    m.record_presence_processing_latency_ms(5.0)
    m.set_presence_event_queue_depth(3)
    m.record_response_fit_pressure(0.6)
    m.record_knowledge_gap_pressure(0.2)
    m.record_scout_dispatch_reason("trigger_a_pressure")
    m.record_scout_request_kind("response_fit")
    m.record_scout_backend("local_lessons")
    m.record_same_turn_wait_ms(1200.0)
    m.record_same_turn_binding_used(True)
    m.record_abstain_before_scout()
    m.record_abstain_after_scout()
    m.record_abstain_rescue_attempted()
    m.record_abstain_rescue_succeeded()

    snap = m.snapshot()
    for key in (
        "turn_open_latency_ms", "interpreted_turn_latency_ms",
        "presence_processing_latency_ms", "presence_event_queue_depth",
        "response_fit_pressure", "knowledge_gap_pressure",
        "scout_dispatch_reason", "scout_request_kind", "scout_backend",
        "binding_integration_ms", "same_turn_wait_ms",
        "same_turn_binding_used_count", "same_turn_binding_unused_count",
        "abstain_before_scout_count", "abstain_after_scout_count",
        "abstain_rescue_attempted_count", "abstain_rescue_succeeded_count",
    ):
        assert key in snap, f"snapshot missing {key}"

    assert snap["turn_open_latency_ms"]["count"] == 1
    assert snap["turn_open_latency_ms"]["p50"] == 10.0
    assert snap["presence_event_queue_depth"] == 3
    assert snap["response_fit_pressure"]["max"] == 0.6
    assert snap["scout_dispatch_reason"] == {"trigger_a_pressure": 1}
    assert snap["scout_request_kind"] == {"response_fit": 1}
    assert snap["scout_backend"] == {"local_lessons": 1}
    assert snap["same_turn_binding_used_count"] == 1
    assert snap["abstain_before_scout_count"] == 1
    assert snap["abstain_rescue_succeeded_count"] == 1


def test_response_fit_pressure_is_clamped_to_0_1():
    m = PresenceMetrics(role="test")
    m.record_response_fit_pressure(5.0)
    m.record_response_fit_pressure(-1.0)
    snap = m.snapshot()
    assert snap["response_fit_pressure"]["max"] == 1.0


def test_write_snapshot_and_read_back(tmp_path):
    m = PresenceMetrics(tmp_path, role="test_role")
    m.record_abstain_rescue_attempted()
    m.write_snapshot()
    from aurora_internal.dual_strata.presence_metrics import read_all_snapshots
    all_snaps = read_all_snapshots(tmp_path)
    assert "test_role" in all_snaps
    assert all_snaps["test_role"]["abstain_rescue_attempted_count"] == 1


# ── subsurface_presence.py: optional `metrics` wiring ───────────────────────

def test_integrate_turn_open_event_records_latency_when_metrics_given(tmp_path):
    m = PresenceMetrics(tmp_path, role="test")
    event = {"kind": "turn_open", "turn_id": "t1", "created_at": time.time() - 0.05, "raw_input": "hi"}
    sp.integrate_turn_open_event(tmp_path, event, metrics=m)
    snap = m.snapshot()
    assert snap["turn_open_latency_ms"]["count"] == 1
    assert snap["turn_open_latency_ms"]["p50"] >= 0.0


def test_integrate_turn_open_event_is_safe_without_metrics(tmp_path):
    event = {"kind": "turn_open", "turn_id": "t1", "created_at": time.time(), "raw_input": "hi"}
    sp.integrate_turn_open_event(tmp_path, event)  # must not raise


def test_integrate_interpreted_turn_event_records_latency_and_pressure(tmp_path):
    m = PresenceMetrics(tmp_path, role="test")
    event = {
        "kind": "interpreted_turn", "turn_id": "t1", "created_at": time.time() - 0.05,
        "interpreted_meaning": "x", "response_fit_pressure": 0.1,  # below dispatch threshold -- no Trigger A noise
    }
    sp.integrate_interpreted_turn_event(tmp_path, event, metrics=m)
    snap = m.snapshot()
    assert snap["interpreted_turn_latency_ms"]["count"] == 1
    assert snap["response_fit_pressure"]["count"] == 1


def test_trigger_a_dispatch_records_scout_dispatch_reason_and_kind(tmp_path):
    m = PresenceMetrics(tmp_path, role="test")
    event = {
        "kind": "interpreted_turn", "turn_id": "t1", "created_at": time.time(),
        "interpreted_meaning": "a greeting", "response_fit_pressure": 0.9,  # clears the default threshold
    }
    sp.integrate_interpreted_turn_event(tmp_path, event, metrics=m)
    snap = m.snapshot()
    assert snap["scout_dispatch_reason"].get("trigger_a_pressure") == 1
    assert snap["scout_request_kind"].get("response_fit") == 1

    broker = ScoutBroker(tmp_path)
    assert broker.queue_depth() == 1


def test_evidence_need_integration_records_dispatch_reason_by_request_kind(tmp_path):
    m = PresenceMetrics(tmp_path, role="test")
    event = {
        "kind": "evidence_need", "turn_id": "t1", "request_kind": "knowledge_gap",
        "inquiry": "what is a chord", "evidence_needed": "chord definition",
    }
    kind = sp.integrate_turn_event(tmp_path, event, metrics=m)
    assert kind == "evidence_need"
    snap = m.snapshot()
    assert snap["scout_dispatch_reason"].get("evidence_need_knowledge_gap") == 1
    assert snap["scout_request_kind"].get("knowledge_gap") == 1


def test_integrate_turn_event_dispatcher_passes_metrics_through(tmp_path):
    m = PresenceMetrics(tmp_path, role="test")
    event = {"kind": "turn_open", "turn_id": "t1", "created_at": time.time(), "raw_input": "hi"}
    sp.integrate_turn_event(tmp_path, event, metrics=m)
    snap = m.snapshot()
    assert snap["turn_open_latency_ms"]["count"] == 1


def test_dispatch_response_fit_scout_records_reason_when_metrics_given(tmp_path):
    m = PresenceMetrics(tmp_path, role="test")
    sp.dispatch_response_fit_scout(
        tmp_path, turn_id="t1", interpreted_meaning="x", dispatch_reason="trigger_b_abstention_rescue", metrics=m,
    )
    snap = m.snapshot()
    assert snap["scout_dispatch_reason"].get("trigger_b_abstention_rescue") == 1


def test_dispatch_response_fit_scout_is_safe_without_metrics(tmp_path):
    result = sp.dispatch_response_fit_scout(tmp_path, turn_id="t1", interpreted_meaning="x")
    assert result is not None  # dispatch itself still works

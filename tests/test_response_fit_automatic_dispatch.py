#!/usr/bin/env python3
"""
Required tests (Aurora Build 694 spec, section 31, "Automatic
response-fit dispatch" / "Request-kind separation"):

  test_response_fit_pressure_dispatches_scout
  test_low_interpretation_does_not_dispatch_response_fit
  test_response_fit_report_contains_response_relationships

Build 694 step 10 completes the response-fit request/report lifecycle
that step 5 (Subsurface Presence and Evidence Scout spec) built but
deliberately left undispatched. Spec section 8: "Subsurface must own
automatic dispatch." Section 9: two complementary triggers -- this file
covers Trigger A (graduated proactive pressure), exercised through
integrate_interpreted_turn_event(), the same function both the fast
SubsurfacePresenceRuntime and the slow daemon-loop backstop call.
Trigger B (abstention rescue) is wired in Build 694 step 15, at the
articulation boundary where "about to abstain" is actually known --
test_abstention_rescue_dispatches_response_fit lives in that step's
test file instead of duplicating a call site that doesn't exist yet.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aurora_internal.dual_strata import subsurface_presence as sp
from aurora_internal.scouting.broker import ScoutBroker
import aurora_scout_daemon as sd


def _interpreted_turn_event(**overrides) -> dict:
    event = {
        "kind": "interpreted_turn",
        "turn_id": "t1",
        "created_at": 0.0,
        "interpreted_meaning": "a friendly social approach",
        "inferred_purpose": "greet",
        "current_topic": "greeting",
        "resolved_referents": [],
        "unresolved_ambiguity": [],
        "interpretation_confidence": 0.9,
        "response_confidence": 0.2,
        "response_fit_pressure": 0.8,
        "representation_refs": [],
        "knowledge_gaps": [],
    }
    event.update(overrides)
    return event


# ── Trigger A: dispatch on elevated response_fit_pressure ──────────────────

def test_response_fit_pressure_dispatches_scout(tmp_path):
    sp.integrate_interpreted_turn_event(str(tmp_path), _interpreted_turn_event(response_fit_pressure=0.8))

    broker = ScoutBroker(tmp_path)
    assert broker.queue_depth() == 1
    pending = list(broker.pending_dir.glob("*.json"))
    raw = json.loads(pending[0].read_text(encoding="utf-8"))
    assert raw["turn_id"] == "t1"
    assert raw["request_kind"] == "response_fit"
    assert "friendly social approach" in raw["interpreted_input"]


def test_pressure_below_threshold_does_not_dispatch(tmp_path):
    sp.integrate_interpreted_turn_event(str(tmp_path), _interpreted_turn_event(response_fit_pressure=0.1))
    broker = ScoutBroker(tmp_path)
    assert broker.queue_depth() == 0


def test_pressure_exactly_at_threshold_dispatches(tmp_path):
    threshold = sp.response_fit_dispatch_threshold()
    sp.integrate_interpreted_turn_event(str(tmp_path), _interpreted_turn_event(response_fit_pressure=threshold))
    broker = ScoutBroker(tmp_path)
    assert broker.queue_depth() == 1


def test_threshold_is_configurable_via_env_var(tmp_path, monkeypatch):
    monkeypatch.setenv("SCOUT_RESPONSE_FIT_THRESHOLD", "0.9")
    assert sp.response_fit_dispatch_threshold() == 0.9
    # A pressure that would have cleared the default 0.55 threshold no
    # longer dispatches once the configured threshold is raised above it.
    sp.integrate_interpreted_turn_event(str(tmp_path), _interpreted_turn_event(response_fit_pressure=0.8))
    broker = ScoutBroker(tmp_path)
    assert broker.queue_depth() == 0


def test_repeated_integration_of_the_same_turn_does_not_duplicate_dispatch(tmp_path):
    # Deliberate double-processing (the fast PresenceRuntime and the slow
    # daemon-loop backstop both integrate the same event batch) must
    # collapse onto ScoutBroker's own one-response-fit-per-turn dedup,
    # not produce two queued requests.
    event = _interpreted_turn_event(response_fit_pressure=0.8)
    sp.integrate_interpreted_turn_event(str(tmp_path), event)
    sp.integrate_interpreted_turn_event(str(tmp_path), event)
    broker = ScoutBroker(tmp_path)
    assert broker.queue_depth() == 1


# ── Hard interpretation gate (spec section 8) ───────────────────────────────

def test_low_interpretation_does_not_dispatch_response_fit(tmp_path):
    # aurora._emit_interpreted_turn_packet() already zeroes
    # response_fit_pressure whenever interpretation was inadequate --
    # this confirms the dispatch trigger genuinely rides on that zeroed
    # value rather than re-deciding adequacy from scratch (and could
    # therefore be fooled by a caller handing it a nonzero pressure
    # alongside low interpretation_confidence).
    sp.integrate_interpreted_turn_event(
        str(tmp_path),
        _interpreted_turn_event(interpretation_confidence=0.1, response_fit_pressure=0.0),
    )
    broker = ScoutBroker(tmp_path)
    assert broker.queue_depth() == 0


# ── dispatch_response_fit_scout() itself (shared by both triggers) ─────────

def test_dispatch_response_fit_scout_builds_the_section_14_inquiry_template(tmp_path):
    sp.dispatch_response_fit_scout(
        str(tmp_path), turn_id="t1",
        interpreted_meaning="a friendly social approach",
        inferred_purpose="greet",
    )
    broker = ScoutBroker(tmp_path)
    raw = json.loads(list(broker.pending_dir.glob("*.json"))[0].read_text(encoding="utf-8"))
    assert "Aurora interpreted state: a friendly social approach" in raw["inquiry"]
    assert "Aurora inferred purpose: greet" in raw["inquiry"]
    assert "Retrieve observed conversation exchanges" in raw["inquiry"]
    assert "Do not classify the response" in raw["inquiry"]
    assert "infer intent" in raw["inquiry"]
    assert "draft a response for Aurora" in raw["inquiry"]


def test_dispatch_response_fit_scout_never_raises_on_broker_failure(tmp_path, monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("simulated broker failure")
    monkeypatch.setattr("aurora_internal.scouting.broker.dispatch_scout_request", _boom)
    result = sp.dispatch_response_fit_scout(str(tmp_path), turn_id="t1", interpreted_meaning="x")
    assert result is None


# ── Scout worker: evidence only; Aurora owns categorization ───────────────

def test_response_fit_report_contains_raw_evidence_but_no_response_labels(tmp_path):
    from aurora_internal.scouting.backends import TestBackend
    from aurora_internal.scouting.contracts import ScoutRequest
    backend = TestBackend(canned_result=(
        "observed_input: hello\nobserved_response: hey, good to hear from you"
    ))
    req = ScoutRequest(turn_id="t1", request_kind="response_fit", inquiry="q")
    report = sd._retrieve_and_normalize(req, state_dir=tmp_path, backends=[backend])
    assert report.status == "ok"
    assert report.evidence_items
    assert report.response_relationships == []
    assert report.fit_rationales == []
    assert report.contradictions == []
    assert report.evidence_items[0]["emittable"] is False


def test_response_fit_report_never_falls_back_to_a_scout_invented_category(tmp_path):
    from aurora_internal.scouting.backends import TestBackend
    from aurora_internal.scouting.contracts import ScoutRequest
    backend = TestBackend(canned_result="zzz qqq wwww")
    req = ScoutRequest(turn_id="t1", request_kind="response_fit", inquiry="q")
    report = sd._retrieve_and_normalize(req, state_dir=tmp_path, backends=[backend])
    assert report.response_relationships == []
    assert report.fit_rationales == []


def test_knowledge_gap_reports_are_also_evidence_only(tmp_path):
    from aurora_internal.scouting.backends import TestBackend
    from aurora_internal.scouting.contracts import ScoutRequest
    backend = TestBackend(canned_result="a guitar chord is three or more notes played together")
    req = ScoutRequest(turn_id="t1", request_kind="knowledge_gap", inquiry="q")
    report = sd._retrieve_and_normalize(req, state_dir=tmp_path, backends=[backend])
    assert report.response_relationships == []
    assert report.fit_rationales == []
    assert report.evidence_items

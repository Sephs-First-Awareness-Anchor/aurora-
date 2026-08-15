#!/usr/bin/env python3
"""
Regression coverage for aurora_internal/scouting/contracts.py
(Subsurface Presence and Evidence Scout spec, sections 7-8).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aurora_internal.scouting.contracts import ScoutRequest, ScoutReport, RESPONSE_RELATIONSHIP_KINDS


def test_scout_request_round_trips_through_dict():
    req = ScoutRequest(turn_id="t1", interpreted_input="asking about guitars", inquiry="chord theory")
    d = req.to_dict()
    restored = ScoutRequest.from_dict(d)
    assert restored.turn_id == "t1"
    assert restored.interpreted_input == "asking about guitars"
    assert restored.inquiry == "chord theory"
    assert restored.request_id == req.request_id


def test_scout_request_deadline_is_created_at_plus_ttl():
    req = ScoutRequest(turn_id="t1", ttl_s=10.0)
    assert req.deadline == req.created_at + 10.0


def test_scout_request_defaults_to_response_fit_kind():
    req = ScoutRequest(turn_id="t1")
    assert req.request_kind == "response_fit"


def test_scout_report_has_no_final_response_field():
    # Architectural guard, not just documentation: the field must not
    # exist at all on the dataclass.
    report = ScoutReport(request_id="r1", turn_id="t1")
    assert "final_response" not in report.to_dict()
    assert not hasattr(report, "final_response")


def test_scout_report_strips_final_response_from_evidence_items():
    report = ScoutReport(
        request_id="r1",
        turn_id="t1",
        evidence_items=[{"text": "some fact", "final_response": "just say X"}],
    )
    assert "final_response" not in report.evidence_items[0]
    assert report.evidence_items[0]["emittable"] is False


def test_scout_report_filters_unknown_response_relationships():
    report = ScoutReport(
        request_id="r1",
        turn_id="t1",
        response_relationships=["explain", "made_up_category", "clarify"],
    )
    assert report.response_relationships == ["explain", "clarify"]


def test_scout_report_accepts_all_documented_relationship_kinds():
    report = ScoutReport(request_id="r1", turn_id="t1", response_relationships=list(RESPONSE_RELATIONSHIP_KINDS))
    assert report.response_relationships == list(RESPONSE_RELATIONSHIP_KINDS)


def test_scout_report_round_trips_through_dict():
    report = ScoutReport(
        request_id="r1", turn_id="t1", status="ok",
        evidence_items=[{"text": "fact"}],
        response_relationships=["explain"],
        fit_rationales=["explains the concept directly"],
        confidence=0.7,
    )
    restored = ScoutReport.from_dict(report.to_dict())
    assert restored.request_id == "r1"
    assert restored.confidence == 0.7
    assert restored.response_relationships == ["explain"]

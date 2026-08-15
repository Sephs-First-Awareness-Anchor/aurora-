#!/usr/bin/env python3
"""Model-free Scout wire-contract regression coverage."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aurora_internal.scouting.contracts import ScoutRequest, ScoutReport


def test_scout_request_round_trip_and_deadline():
    req = ScoutRequest(turn_id="t1", interpreted_input="asking about guitars", inquiry="chord theory", ttl_s=10)
    restored = ScoutRequest.from_dict(req.to_dict())
    assert restored.turn_id == "t1"
    assert restored.request_id == req.request_id
    assert req.deadline == req.created_at + 10.0


def test_scout_report_has_no_final_response_field_and_scrubs_items():
    report = ScoutReport(request_id="r1", turn_id="t1", evidence_items=[{"text": "fact", "final_response": "say this"}])
    assert "final_response" not in report.to_dict()
    assert "final_response" not in report.evidence_items[0]
    assert report.evidence_items[0]["emittable"] is False


def test_scout_report_forcibly_discards_interpretive_metadata():
    report = ScoutReport(
        request_id="r1", turn_id="t1",
        response_relationships=["explain", "clarify"],
        fit_rationales=["because"], contradictions=["conflict"],
    )
    assert report.response_relationships == []
    assert report.fit_rationales == []
    assert report.contradictions == []


def test_legacy_interpretive_fields_stay_empty_after_round_trip():
    report = ScoutReport(request_id="r1", turn_id="t1", evidence_items=[{"text": "fact"}],
                         response_relationships=["explain"], fit_rationales=["x"], confidence=.7)
    restored = ScoutReport.from_dict(report.to_dict())
    assert restored.confidence == .7
    assert restored.response_relationships == []
    assert restored.fit_rationales == []

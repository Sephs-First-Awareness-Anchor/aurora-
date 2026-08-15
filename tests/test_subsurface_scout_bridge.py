#!/usr/bin/env python3
"""Subsurface acceptance of raw Scout evidence, without auto-resolution credit."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aurora_internal.scouting.contracts import ScoutReport
from aurora_internal.scouting.broker import ScoutBroker
from aurora_internal.scouting.subsurface_scout_bridge import evaluate_report, record_binding, read_bindings_for_turn, consume_scout_reports
from aurora_internal.dual_strata.subsurface_presence import write_presence_frame, read_presence_frame


def _ok_report(turn_id="t1", confidence=.7, request_kind="response_fit"):
    return ScoutReport(request_id="r1", turn_id=turn_id, request_kind=request_kind, status="ok",
                       evidence_items=[{"text": "some evidence"}], confidence=confidence)


def test_current_raw_report_is_accepted_but_never_declares_pressure_relief():
    b = evaluate_report(_ok_report(confidence=.8), current_turn_id="t1")
    assert b.status == "accepted" and b.relevance == 1.0
    assert b.pressure_relief == 0.0


def test_non_ok_empty_stale_and_weak_reports_are_not_current_evidence():
    assert evaluate_report(ScoutReport(request_id="r", turn_id="t1", status="no_evidence"), current_turn_id="t1").status == "rejected"
    assert evaluate_report(ScoutReport(request_id="r", turn_id="t1", status="ok", evidence_items=[]), current_turn_id="t1").status == "rejected"
    assert evaluate_report(_ok_report(turn_id="old", confidence=.9), current_turn_id="new").status == "stale"
    assert evaluate_report(_ok_report(confidence=.05), current_turn_id="t1").status == "rejected"


def test_scout_cannot_supply_contradiction_judgment_to_subsurface():
    report = ScoutReport(request_id="r", turn_id="t1", status="ok", evidence_items=[{"text":"x"}],
                         contradictions=["Scout thinks this conflicts"], confidence=.5)
    b = evaluate_report(report, current_turn_id="t1")
    assert report.contradictions == []
    assert b.consistency == 1.0


def test_binding_storage_is_exact_turn_and_bounded(tmp_path):
    for _ in range(10):
        record_binding(tmp_path, evaluate_report(_ok_report(confidence=.6), current_turn_id="t1"))
    assert len(read_bindings_for_turn(tmp_path, "t1")) <= 6
    assert read_bindings_for_turn(tmp_path, "t2") == []


def test_consume_integrates_evidence_without_reducing_unresolved_pressure(tmp_path):
    write_presence_frame(tmp_path, turn_id="t1", response_fit_pressure=.8)
    broker = ScoutBroker(tmp_path); broker.reports_dir.mkdir(parents=True, exist_ok=True)
    report = _ok_report(confidence=.9)
    (broker.reports_dir / "r1.json").write_text(json.dumps(report.to_dict()), encoding="utf-8")
    bindings = consume_scout_reports(tmp_path, broker=broker)
    assert bindings[0].status == "accepted"
    frame = read_presence_frame(tmp_path)
    assert frame["evidence_bindings"]
    assert frame["response_fit_pressure"] == .8


def test_stale_report_never_enters_current_frame(tmp_path):
    write_presence_frame(tmp_path, turn_id="new", response_fit_pressure=.6)
    broker = ScoutBroker(tmp_path); broker.reports_dir.mkdir(parents=True, exist_ok=True)
    report = _ok_report(turn_id="old", confidence=.95)
    (broker.reports_dir / "r1.json").write_text(json.dumps(report.to_dict()), encoding="utf-8")
    bindings = consume_scout_reports(tmp_path, broker=broker)
    assert bindings[0].status == "stale"
    frame = read_presence_frame(tmp_path)
    assert frame["turn_id"] == "new" and frame["response_fit_pressure"] == .6
    assert frame["evidence_bindings"] == []

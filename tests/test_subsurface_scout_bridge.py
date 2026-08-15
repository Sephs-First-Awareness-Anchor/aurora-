#!/usr/bin/env python3
"""
Regression coverage for aurora_internal/scouting/subsurface_scout_bridge.py
(Subsurface Presence and Evidence Scout spec, sections 11-12): report
evaluation into EvidenceBinding, bounded per-turn storage, and the
consume_scout_reports() loop entry point that folds only current-turn
accepted evidence into the presence frame.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aurora_internal.scouting.contracts import ScoutReport
from aurora_internal.scouting.broker import ScoutBroker
from aurora_internal.scouting.subsurface_scout_bridge import (
    evaluate_report,
    record_binding,
    read_bindings_for_turn,
    consume_scout_reports,
)
from aurora_internal.dual_strata.subsurface_presence import write_presence_frame, read_presence_frame


def _ok_report(turn_id="t1", confidence=0.7, contradictions=None):
    return ScoutReport(
        request_id="r1", turn_id=turn_id, status="ok",
        evidence_items=[{"text": "some evidence"}],
        response_relationships=["explain"],
        confidence=confidence,
        contradictions=list(contradictions or []),
    )


def test_ok_report_for_current_turn_is_accepted():
    report = _ok_report(turn_id="t1", confidence=0.8)
    binding = evaluate_report(report, current_turn_id="t1")
    assert binding.status == "accepted"
    assert binding.relevance == 1.0
    assert binding.pressure_relief > 0.0
    assert binding.rejected_reason is None


def test_non_ok_status_is_rejected_with_reason():
    report = ScoutReport(request_id="r1", turn_id="t1", status="no_evidence")
    binding = evaluate_report(report, current_turn_id="t1")
    assert binding.status == "rejected"
    assert binding.pressure_relief == 0.0
    assert "no_evidence" in binding.rejected_reason


def test_ok_report_with_no_evidence_items_is_rejected():
    report = ScoutReport(request_id="r1", turn_id="t1", status="ok", evidence_items=[])
    binding = evaluate_report(report, current_turn_id="t1")
    assert binding.status == "rejected"
    assert binding.rejected_reason == "report has no evidence items"


def test_report_for_a_turn_that_is_no_longer_current_is_marked_stale():
    report = _ok_report(turn_id="t_old", confidence=0.9)
    binding = evaluate_report(report, current_turn_id="t_new")
    assert binding.status == "stale"
    assert binding.relevance < 1.0
    assert binding.pressure_relief == 0.0


def test_weak_confidence_report_for_current_turn_is_rejected_not_accepted():
    report = _ok_report(turn_id="t1", confidence=0.05)
    binding = evaluate_report(report, current_turn_id="t1")
    assert binding.status == "rejected"
    assert binding.pressure_relief == 0.0


def test_contradictions_reduce_consistency_and_can_flip_acceptance():
    clean = evaluate_report(_ok_report(turn_id="t1", confidence=0.5), current_turn_id="t1")
    contradicted = evaluate_report(
        _ok_report(turn_id="t1", confidence=0.5, contradictions=["conflicts with X"]),
        current_turn_id="t1",
    )
    assert contradicted.consistency < clean.consistency
    assert contradicted.pressure_relief < clean.pressure_relief


def test_pressure_relief_never_exceeds_relevance_times_consistency_times_strength():
    report = _ok_report(turn_id="t1", confidence=0.9)
    binding = evaluate_report(report, current_turn_id="t1")
    assert binding.pressure_relief <= binding.relevance * binding.consistency * binding.strength + 1e-9


def test_evaluated_binding_never_carries_a_final_response_field():
    report = _ok_report(turn_id="t1")
    binding = evaluate_report(report, current_turn_id="t1")
    assert "final_response" not in binding.to_dict()


def test_record_and_read_bindings_round_trip_by_exact_turn_id(tmp_path):
    binding = evaluate_report(_ok_report(turn_id="t1", confidence=0.6), current_turn_id="t1")
    record_binding(tmp_path, binding)

    assert len(read_bindings_for_turn(tmp_path, "t1")) == 1
    assert read_bindings_for_turn(tmp_path, "t1")[0]["binding_id"] == binding.binding_id
    # Different turn_id must see nothing -- this IS the other half of the
    # stale-report guard (storage keyed by exact turn_id).
    assert read_bindings_for_turn(tmp_path, "t2") == []


def test_bindings_per_turn_are_bounded(tmp_path):
    for i in range(10):
        b = evaluate_report(_ok_report(turn_id="t1", confidence=0.5), current_turn_id="t1")
        record_binding(tmp_path, b)
    assert len(read_bindings_for_turn(tmp_path, "t1")) <= 6


def test_consume_scout_reports_returns_empty_when_nothing_pending(tmp_path):
    assert consume_scout_reports(tmp_path) == []


def test_consume_scout_reports_folds_current_turn_acceptance_into_presence_frame(tmp_path):
    write_presence_frame(tmp_path, turn_id="t1", response_fit_pressure=0.8)

    broker = ScoutBroker(tmp_path)
    broker.reports_dir.mkdir(parents=True, exist_ok=True)
    (broker.reports_dir / "r1.json").write_text(
        __import__("json").dumps(_ok_report(turn_id="t1", confidence=0.9).to_dict()), encoding="utf-8"
    )

    bindings = consume_scout_reports(tmp_path, broker=broker)
    assert len(bindings) == 1
    assert bindings[0].status == "accepted"

    frame = read_presence_frame(tmp_path)
    assert frame["evidence_bindings"]
    assert frame["response_fit_pressure"] < 0.8  # pressure relieved


def test_consume_scout_reports_does_not_fold_stale_turn_report_into_current_frame(tmp_path):
    # Subsurface's live turn has already moved on to t_new by the time
    # this report (for t_old) arrives back.
    write_presence_frame(tmp_path, turn_id="t_new", response_fit_pressure=0.6)

    broker = ScoutBroker(tmp_path)
    broker.reports_dir.mkdir(parents=True, exist_ok=True)
    report = _ok_report(turn_id="t_old", confidence=0.95)
    (broker.reports_dir / f"{report.request_id}.json").write_text(
        __import__("json").dumps(report.to_dict()), encoding="utf-8"
    )

    bindings = consume_scout_reports(tmp_path, broker=broker)
    assert len(bindings) == 1
    assert bindings[0].status == "stale"

    frame = read_presence_frame(tmp_path)
    assert frame["turn_id"] == "t_new"
    assert frame["response_fit_pressure"] == 0.6  # unchanged -- old turn's evidence never touched it
    assert frame["evidence_bindings"] == []

    # But the stale binding was still recorded, just under its own turn.
    assert len(read_bindings_for_turn(tmp_path, "t_old")) == 1
    assert read_bindings_for_turn(tmp_path, "t_new") == []


def test_consume_scout_reports_leaves_frame_untouched_when_only_rejected_bindings(tmp_path):
    write_presence_frame(tmp_path, turn_id="t1", response_fit_pressure=0.5)
    broker = ScoutBroker(tmp_path)
    broker.reports_dir.mkdir(parents=True, exist_ok=True)
    failed = ScoutReport(request_id="r1", turn_id="t1", status="failed")
    (broker.reports_dir / "r1.json").write_text(__import__("json").dumps(failed.to_dict()), encoding="utf-8")

    bindings = consume_scout_reports(tmp_path, broker=broker)
    assert bindings[0].status == "rejected"

    frame = read_presence_frame(tmp_path)
    assert frame["response_fit_pressure"] == 0.5
    assert frame["evidence_bindings"] == []

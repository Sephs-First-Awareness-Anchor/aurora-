#!/usr/bin/env python3
"""
Required test (Aurora Build 694 spec, section 31, "Request-kind
separation"): test_knowledge_gap_does_not_directly_relieve_response_fit_pressure

Spec section 12: "Current EvidenceBinding evaluation must stop treating
every accepted Scout report as generic response-fit pressure relief. A
"knowledge_gap" Scout is not the same thing as a "response_fit" Scout."
Only a response_fit report may relieve response_fit_pressure; a
knowledge_gap report, even when accepted, becomes provisional semantic
evidence Aurora must reconsider interpretation with instead (build 694
step 12 wires that reconsideration path -- this file only covers the
evaluation-side boundary: knowledge_gap/self_diagnostic acceptance must
never itself move response_fit_pressure).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aurora_internal.scouting.contracts import ScoutReport
from aurora_internal.scouting.broker import ScoutBroker
from aurora_internal.scouting.subsurface_scout_bridge import evaluate_report, consume_scout_reports
from aurora_internal.dual_strata.subsurface_presence import write_presence_frame, read_presence_frame


def _ok_report(request_kind: str, turn_id: str = "t1", confidence: float = 0.9) -> ScoutReport:
    return ScoutReport(
        request_id="r1", turn_id=turn_id, request_kind=request_kind, status="ok",
        evidence_items=[{"text": "some evidence"}],
        response_relationships=["explain"],
        confidence=confidence,
    )


# ── evaluate_report(): pure function boundary ───────────────────────────────

def test_knowledge_gap_does_not_directly_relieve_response_fit_pressure():
    binding = evaluate_report(_ok_report("knowledge_gap"), current_turn_id="t1")
    assert binding.status == "accepted"
    assert binding.pressure_relief == 0.0


def test_response_fit_report_still_relieves_pressure_as_before():
    binding = evaluate_report(_ok_report("response_fit"), current_turn_id="t1")
    assert binding.status == "accepted"
    assert binding.pressure_relief > 0.0


def test_self_diagnostic_never_relieves_response_fit_pressure_even_when_accepted():
    binding = evaluate_report(_ok_report("self_diagnostic"), current_turn_id="t1")
    assert binding.status == "accepted"  # self_diagnostic is always "current" (spec step 11 of build 675)
    assert binding.pressure_relief == 0.0


def test_self_diagnostic_zeroed_pressure_relief_holds_even_if_turn_id_coincidentally_matches_live_turn():
    # Defensive: the zeroing must not depend on self_diagnostic's turn_id
    # happening to differ from the live turn -- it is request_kind that
    # decides this, not turn_id coincidence.
    binding = evaluate_report(_ok_report("self_diagnostic", turn_id="t1"), current_turn_id="t1")
    assert binding.pressure_relief == 0.0


def test_knowledge_gap_binding_is_still_accepted_and_carries_evidence():
    # Not relieving pressure is not the same as being discarded -- an
    # accepted knowledge_gap binding still carries its evidence_items,
    # ready to become provisional semantic evidence elsewhere.
    binding = evaluate_report(_ok_report("knowledge_gap"), current_turn_id="t1")
    assert binding.status == "accepted"
    assert binding.evidence_items


# ── consume_scout_reports(): the presence-frame folding boundary ───────────

def test_consume_scout_reports_does_not_reduce_pressure_for_accepted_knowledge_gap_report(tmp_path):
    write_presence_frame(tmp_path, turn_id="t1", response_fit_pressure=0.8)

    broker = ScoutBroker(tmp_path)
    broker.reports_dir.mkdir(parents=True, exist_ok=True)
    report = _ok_report("knowledge_gap", turn_id="t1", confidence=0.95)
    (broker.reports_dir / "r1.json").write_text(json.dumps(report.to_dict()), encoding="utf-8")

    bindings = consume_scout_reports(tmp_path, broker=broker)
    assert bindings[0].status == "accepted"

    frame = read_presence_frame(tmp_path)
    assert frame["response_fit_pressure"] == 0.8  # unchanged


def test_consume_scout_reports_reduces_pressure_for_accepted_response_fit_report(tmp_path):
    write_presence_frame(tmp_path, turn_id="t1", response_fit_pressure=0.8)

    broker = ScoutBroker(tmp_path)
    broker.reports_dir.mkdir(parents=True, exist_ok=True)
    report = _ok_report("response_fit", turn_id="t1", confidence=0.95)
    (broker.reports_dir / "r1.json").write_text(json.dumps(report.to_dict()), encoding="utf-8")

    bindings = consume_scout_reports(tmp_path, broker=broker)
    assert bindings[0].status == "accepted"

    frame = read_presence_frame(tmp_path)
    assert frame["response_fit_pressure"] < 0.8


def test_mixed_batch_only_response_fit_bindings_move_the_pressure_number(tmp_path):
    write_presence_frame(tmp_path, turn_id="t1", response_fit_pressure=0.9)

    broker = ScoutBroker(tmp_path)
    broker.reports_dir.mkdir(parents=True, exist_ok=True)
    kg = _ok_report("knowledge_gap", turn_id="t1", confidence=0.99)
    rf = _ok_report("response_fit", turn_id="t1", confidence=0.5)
    (broker.reports_dir / "kg.json").write_text(json.dumps({**kg.to_dict(), "request_id": "kg"}), encoding="utf-8")
    (broker.reports_dir / "rf.json").write_text(json.dumps({**rf.to_dict(), "request_id": "rf"}), encoding="utf-8")

    bindings = consume_scout_reports(tmp_path, broker=broker)
    assert len(bindings) == 2
    kg_binding = next(b for b in bindings if b.request_kind == "knowledge_gap")
    rf_binding = next(b for b in bindings if b.request_kind == "response_fit")
    assert kg_binding.pressure_relief == 0.0
    assert rf_binding.pressure_relief > 0.0

    frame = read_presence_frame(tmp_path)
    # The relief actually applied must equal exactly the response_fit
    # binding's own relief -- proof the knowledge_gap binding contributed
    # nothing to the arithmetic, not just that it happened to be small.
    assert round(0.9 - frame["response_fit_pressure"], 4) == rf_binding.pressure_relief

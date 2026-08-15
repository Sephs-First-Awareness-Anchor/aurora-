#!/usr/bin/env python3
"""All Scout kinds are evidence-only; retrieval never equals cognitive relief."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aurora_internal.scouting.contracts import ScoutReport
from aurora_internal.scouting.broker import ScoutBroker
from aurora_internal.scouting.subsurface_scout_bridge import evaluate_report, consume_scout_reports
from aurora_internal.dual_strata.subsurface_presence import write_presence_frame, read_presence_frame


def _ok(kind, turn_id="t1", confidence=.9):
    return ScoutReport(request_id="r", turn_id=turn_id, request_kind=kind, status="ok",
                       evidence_items=[{"text":"raw evidence"}], confidence=confidence)


def test_no_request_kind_gets_pressure_relief_merely_for_retrieval():
    for kind in ("knowledge_gap", "response_fit", "self_diagnostic"):
        b = evaluate_report(_ok(kind), current_turn_id="t1")
        assert b.status == "accepted"
        assert b.pressure_relief == 0.0
        assert b.evidence_items


def test_mixed_batch_integrates_without_moving_response_pressure(tmp_path):
    write_presence_frame(tmp_path, turn_id="t1", response_fit_pressure=.9)
    broker = ScoutBroker(tmp_path); broker.reports_dir.mkdir(parents=True, exist_ok=True)
    for rid, kind in (("kg", "knowledge_gap"), ("rf", "response_fit")):
        d = _ok(kind).to_dict(); d["request_id"] = rid
        (broker.reports_dir / f"{rid}.json").write_text(json.dumps(d), encoding="utf-8")
    bindings = consume_scout_reports(tmp_path, broker=broker)
    assert len(bindings) == 2
    assert all(b.pressure_relief == 0.0 for b in bindings)
    assert read_presence_frame(tmp_path)["response_fit_pressure"] == .9

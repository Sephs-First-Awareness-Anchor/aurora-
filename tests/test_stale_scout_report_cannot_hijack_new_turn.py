#!/usr/bin/env python3
"""
Required test (Subsurface Presence and Evidence Scout spec, section 21):
test_stale_scout_report_cannot_hijack_new_turn.py -- a full-stack
integration test (dispatch -> report -> evaluate/bind -> Surface
harvest) proving a late-arriving report from a turn Subsurface has
already moved on from can never be mistaken for evidence about the
NEW live turn, end to end through the real production modules (not
just the unit-level checks already covering pieces of this in
test_subsurface_scout_bridge.py and test_surface_scout_evidence_harvest.py).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aurora
from aurora_internal.scouting.broker import ScoutBroker
from aurora_internal.scouting.contracts import ScoutReport
from aurora_internal.scouting.subsurface_scout_bridge import consume_scout_reports
from aurora_internal.dual_strata.subsurface_presence import write_presence_frame


def test_full_pipeline_stale_report_never_reaches_new_turns_surface_harvest(tmp_path):
    # Turn 1 opens; Subsurface's live turn is t1.
    write_presence_frame(tmp_path, turn_id="t1", response_fit_pressure=0.9)

    broker = ScoutBroker(tmp_path)
    broker.reports_dir.mkdir(parents=True, exist_ok=True)
    # A report for t1 finishes late -- AFTER Subsurface has already
    # opened turn 2 (simulated below by advancing the presence frame's
    # turn_id before this report is ever consumed).
    late_report = ScoutReport(
        request_id="r_t1", turn_id="t1", status="ok",
        evidence_items=[{"text": "evidence that genuinely belongs to turn 1's question"}],
        response_relationships=["explain"], confidence=0.9,
    )
    (broker.reports_dir / "r_t1.json").write_text(json.dumps(late_report.to_dict()), encoding="utf-8")

    # Turn 2 opens before the report above is ever drained -- Subsurface's
    # live turn is now t2.
    write_presence_frame(tmp_path, turn_id="t2", response_fit_pressure=0.8)

    # Subsurface finally consumes the queue -- the report is for t1, but
    # the CURRENT live turn is t2.
    bindings = consume_scout_reports(tmp_path, broker=broker)
    assert len(bindings) == 1
    assert bindings[0].status == "stale"
    assert bindings[0].turn_id == "t1"

    # Turn 2's presence frame must be completely untouched by t1's evidence.
    frame_t2 = json.loads((tmp_path / "subsurface_presence_frame.json").read_text(encoding="utf-8"))
    assert frame_t2["turn_id"] == "t2"
    assert frame_t2["response_fit_pressure"] == 0.8
    assert frame_t2["evidence_bindings"] == []

    # Surface, harvesting for the NEW live turn (t2), sees nothing from
    # t1's late report.
    systems = {"state_dir": tmp_path}
    harvested_t2 = aurora._harvest_scout_evidence_for_expression(systems, turn_id="t2")
    assert harvested_t2 == []

    # The evidence was still recorded -- just correctly attributed to
    # its own turn, never silently dropped or silently misattributed.
    harvested_t1 = aurora._harvest_scout_evidence_for_expression(systems, turn_id="t1")
    assert len(harvested_t1) == 0  # "stale", not "accepted" -- t1 is no longer current either


def test_report_arriving_while_its_own_turn_is_still_current_is_accepted_normally(tmp_path):
    # Control case: the same report, but consumed BEFORE the turn moves
    # on, to confirm the "stale" outcome above is specifically about
    # turn transition timing, not some other defect in the pipeline.
    write_presence_frame(tmp_path, turn_id="t1", response_fit_pressure=0.9)

    broker = ScoutBroker(tmp_path)
    broker.reports_dir.mkdir(parents=True, exist_ok=True)
    report = ScoutReport(
        request_id="r_t1", turn_id="t1", status="ok",
        evidence_items=[{"text": "evidence for the still-current turn"}],
        response_relationships=["explain"], confidence=0.9,
    )
    (broker.reports_dir / "r_t1.json").write_text(json.dumps(report.to_dict()), encoding="utf-8")

    bindings = consume_scout_reports(tmp_path, broker=broker)
    assert bindings[0].status == "accepted"

    systems = {"state_dir": tmp_path}
    harvested = aurora._harvest_scout_evidence_for_expression(systems, turn_id="t1")
    assert len(harvested) == 1

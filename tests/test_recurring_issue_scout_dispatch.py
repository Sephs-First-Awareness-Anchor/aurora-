#!/usr/bin/env python3
"""
Regression coverage for the Subsurface Presence and Evidence Scout
spec's Step 11: aurora_daemon._maybe_research_recurring_issue() must
never block Subsurface's main loop waiting on Poedex -- it dispatches a
self_diagnostic ScoutRequest (turn_id="", never scoped to a live user
turn) and returns immediately, and a separate per-tick consumer
(_consume_recurring_issue_research()) completes the note/activity/
repair-proposal pipeline once the evidence actually comes back.

Imports aurora_daemon directly, same "pure data/control-flow boundary,
not a full boot" approach used by test_interpreted_turn_packet.py and
test_surface_scout_evidence_harvest.py for aurora.py.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aurora_daemon as ad
from aurora_internal.scouting.broker import ScoutBroker
from aurora_internal.scouting.contracts import ScoutReport
from aurora_internal.scouting.subsurface_scout_bridge import record_binding, evaluate_report


def _patch_state_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(ad, "_STATE_DIR", tmp_path)


def _make_status(tmp_path, *, avg_sev=0.6, fails=60, dim="comprehension_gap"):
    (tmp_path / "daemon_status.json").write_text(json.dumps({
        "fail_summary": [{"dim": dim, "avg_sev": avg_sev, "fails": fails}],
        "qao_recent_events": 3,
        "qao_top_issue": "?",
    }), encoding="utf-8")


def test_dispatch_returns_quickly_instead_of_blocking_for_18s(tmp_path, monkeypatch):
    _patch_state_dir(monkeypatch, tmp_path)
    _make_status(tmp_path)
    systems = {}

    started = time.time()
    fired = ad._maybe_research_recurring_issue(systems, "LOW")
    elapsed = time.time() - started

    assert fired is True
    assert elapsed < 2.0  # old blocking path could take up to 18s


def test_dispatch_enqueues_a_self_diagnostic_scout_request_with_no_turn(tmp_path, monkeypatch):
    _patch_state_dir(monkeypatch, tmp_path)
    _make_status(tmp_path)

    ad._maybe_research_recurring_issue({}, "LOW")

    broker = ScoutBroker(tmp_path)
    assert broker.queue_depth() == 1
    raw = json.loads(next(broker.pending_dir.glob("*.json")).read_text(encoding="utf-8"))
    assert raw["request_kind"] == "self_diagnostic"
    assert raw["turn_id"] == ""


def test_dispatch_records_a_pending_correlation_for_the_request(tmp_path, monkeypatch):
    _patch_state_dir(monkeypatch, tmp_path)
    _make_status(tmp_path)

    ad._maybe_research_recurring_issue({}, "LOW")

    pending = ad._load_pending_issue_research()
    assert len(pending) == 1
    correlation = next(iter(pending.values()))
    assert correlation["candidate_dim"] == "comprehension_gap"
    assert "dispatched_at" in correlation


def test_high_heat_never_dispatches_anything(tmp_path, monkeypatch):
    _patch_state_dir(monkeypatch, tmp_path)
    _make_status(tmp_path)

    assert ad._maybe_research_recurring_issue({}, "CRITICAL") is False
    assert ScoutBroker(tmp_path).queue_depth() == 0
    assert ad._load_pending_issue_research() == {}


def test_consume_completes_the_pipeline_once_evidence_is_accepted(tmp_path, monkeypatch):
    _patch_state_dir(monkeypatch, tmp_path)
    _make_status(tmp_path)
    ad._maybe_research_recurring_issue({}, "LOW")

    request_id = next(iter(ad._load_pending_issue_research().keys()))
    report = ScoutReport(
        request_id=request_id, turn_id="", request_kind="self_diagnostic",
        status="ok", evidence_items=[{"text": "check the referent_map schema at line 5615"}],
        confidence=0.8,
    )
    binding = evaluate_report(report, current_turn_id="some_live_turn")
    assert binding.status == "accepted"  # self_diagnostic must not be discounted as stale
    record_binding(tmp_path, binding)

    ad._consume_recurring_issue_research({})

    assert ad._load_pending_issue_research() == {}
    notes = json.loads((tmp_path / "aurora_room_notes.json").read_text(encoding="utf-8"))
    assert any("referent_map schema" in n.get("content", "") for n in notes)


def test_consume_leaves_pending_entry_untouched_while_evidence_has_not_arrived(tmp_path, monkeypatch):
    _patch_state_dir(monkeypatch, tmp_path)
    _make_status(tmp_path)
    ad._maybe_research_recurring_issue({}, "LOW")

    ad._consume_recurring_issue_research({})

    assert len(ad._load_pending_issue_research()) == 1
    assert not (tmp_path / "aurora_room_notes.json").exists()


def test_consume_drops_pending_entry_after_max_age_without_evidence(tmp_path, monkeypatch):
    _patch_state_dir(monkeypatch, tmp_path)
    _make_status(tmp_path)
    ad._maybe_research_recurring_issue({}, "LOW")

    request_id = next(iter(ad._load_pending_issue_research().keys()))
    stale_pending = ad._load_pending_issue_research()
    stale_pending[request_id]["dispatched_at"] = time.time() - 10_000
    ad._save_pending_issue_research(stale_pending)

    ad._consume_recurring_issue_research({})

    assert ad._load_pending_issue_research() == {}
    assert not (tmp_path / "aurora_room_notes.json").exists()


def test_consume_does_nothing_when_nothing_is_pending(tmp_path, monkeypatch):
    _patch_state_dir(monkeypatch, tmp_path)
    ad._consume_recurring_issue_research({})  # must not raise
    assert ad._load_pending_issue_research() == {}


def test_repeated_calls_within_cooldown_do_not_redispatch(tmp_path, monkeypatch):
    _patch_state_dir(monkeypatch, tmp_path)
    _make_status(tmp_path)

    assert ad._maybe_research_recurring_issue({}, "LOW") is True
    # Same issue, same status snapshot, well inside the 1200s cooldown.
    assert ad._maybe_research_recurring_issue({}, "LOW") is False
    assert ScoutBroker(tmp_path).queue_depth() == 1

#!/usr/bin/env python3
"""
Regression coverage for aurora_scout_daemon.py (Subsurface Presence
and Evidence Scout spec, section 9 and the "Computational isolation"
acceptance criteria in section 20): the lightweight Scout worker must
never load a full Aurora instance, must never author a final response,
and its claim/process/submit loop must actually round-trip through a
real ScoutBroker.
"""
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_importing_scout_daemon_never_pulls_in_aurora_or_aurora_daemon():
    # Sunni & Cael: the literal, checkable version of "no full Aurora
    # boot occurs in Scout workers" -- importing aurora.py or
    # aurora_daemon.py at all executes their module-level setup (which
    # constructs genealogy/Dream/consciousness-engine/etc. state), so
    # this has to hold at IMPORT time, not just "boot_aurora() is never
    # called."
    before = set(sys.modules.keys())
    import aurora_scout_daemon  # noqa: F401
    after = set(sys.modules.keys())
    newly_imported = after - before
    assert "aurora" not in newly_imported
    assert "aurora_daemon" not in newly_imported
    assert "aurora" not in sys.modules
    assert "aurora_daemon" not in sys.modules


def test_scout_report_from_worker_never_has_a_final_response_field():
    import aurora_scout_daemon as sd
    from aurora_internal.scouting.contracts import ScoutRequest

    req = ScoutRequest(turn_id="t1", inquiry="")  # empty inquiry -> no_evidence path
    report = sd._retrieve_and_normalize(req)
    assert "final_response" not in report.to_dict()


def test_empty_inquiry_short_circuits_to_no_evidence_without_checking_room(tmp_path, monkeypatch):
    import aurora_scout_daemon as sd
    from aurora_internal.scouting.contracts import ScoutRequest

    called = {"room_check": False}
    def _fake_room_check():
        called["room_check"] = True
        return True
    monkeypatch.setattr(sd, "_room_responder_available", _fake_room_check)

    req = ScoutRequest(turn_id="t1", inquiry="")
    report = sd._retrieve_and_normalize(req)
    assert report.status == "no_evidence"
    assert called["room_check"] is False


def test_retrieve_and_normalize_reports_no_evidence_when_room_is_not_running(monkeypatch):
    import aurora_scout_daemon as sd
    from aurora_internal.scouting.contracts import ScoutRequest

    monkeypatch.setattr(sd, "_room_responder_available", lambda: False)

    req = ScoutRequest(turn_id="t1", inquiry="what is a guitar chord")
    report = sd._retrieve_and_normalize(req)
    assert report.status == "no_evidence"
    assert report.fit_rationales  # honest, not silent


def test_retrieve_and_normalize_produces_evidence_when_room_answers(monkeypatch):
    import aurora_scout_daemon as sd
    from aurora_internal.scouting.contracts import ScoutRequest

    monkeypatch.setattr(sd, "_room_responder_available", lambda: True)
    monkeypatch.setattr(sd, "_poedex_ask_lightweight", lambda *a, **k: "a guitar chord is three or more notes played together")

    req = ScoutRequest(
        turn_id="t1",
        interpreted_input="asking what a guitar chord is",
        inquiry="what is a guitar chord",
    )
    report = sd._retrieve_and_normalize(req)
    assert report.status == "ok"
    assert report.evidence_items
    assert "guitar chord" in report.evidence_items[0]["text"]
    assert report.evidence_items[0]["emittable"] is False
    assert report.response_relationships == ["explain"]
    assert report.confidence > 0.0
    assert "final_response" not in report.to_dict()


def test_retrieve_and_normalize_truncates_to_max_result_chars(monkeypatch):
    import aurora_scout_daemon as sd
    from aurora_internal.scouting.contracts import ScoutRequest

    monkeypatch.setattr(sd, "_room_responder_available", lambda: True)
    monkeypatch.setattr(sd, "_poedex_ask_lightweight", lambda *a, **k: "x" * 5000)

    req = ScoutRequest(turn_id="t1", inquiry="q", max_result_chars=50)
    report = sd._retrieve_and_normalize(req)
    assert len(report.evidence_items[0]["text"]) <= 50


def test_scout_never_reinterprets_raw_input_it_only_receives_the_interpreted_packet(monkeypatch):
    # Sunni & Cael: the request itself carries interpreted_input as
    # CONTEXT the Scout is told about -- it never has its own separate
    # channel to the raw user utterance. This is a structural guarantee
    # (ScoutRequest simply has no raw_user_text field), verified here by
    # confirming the question sent downstream is built only from
    # request.inquiry/interpreted_input, nothing else.
    import aurora_scout_daemon as sd
    from aurora_internal.scouting.contracts import ScoutRequest

    monkeypatch.setattr(sd, "_room_responder_available", lambda: True)
    captured = {}
    def _fake_ask(question, **kwargs):
        captured["question"] = question
        return "evidence"
    monkeypatch.setattr(sd, "_poedex_ask_lightweight", _fake_ask)

    req = ScoutRequest(turn_id="t1", interpreted_input="Aurora's own reading of the input", inquiry="the actual inquiry")
    sd._retrieve_and_normalize(req)
    assert "the actual inquiry" in captured["question"]
    assert "Aurora's own reading of the input" in captured["question"]


def test_worker_loop_round_trips_a_dispatched_request(tmp_path, monkeypatch):
    import aurora_scout_daemon as sd
    from aurora_internal.scouting.broker import ScoutBroker
    from aurora_internal.scouting.contracts import ScoutRequest

    monkeypatch.setattr(sd, "_STATE_DIR", tmp_path)
    monkeypatch.setattr(sd, "_room_responder_available", lambda: True)
    monkeypatch.setattr(sd, "_poedex_ask_lightweight", lambda *a, **k: "evidence text")

    dispatcher = ScoutBroker(tmp_path)
    req = ScoutRequest(turn_id="t1", inquiry="q1")
    dispatcher.dispatch(req)

    sd.run(poll_interval_s=0.05, max_iterations=3)

    reports = dispatcher.poll_reports()
    assert len(reports) == 1
    assert reports[0].request_id == req.request_id
    assert reports[0].status == "ok"


def test_worker_loop_reports_failed_status_on_internal_exception(tmp_path, monkeypatch):
    import aurora_scout_daemon as sd
    from aurora_internal.scouting.broker import ScoutBroker
    from aurora_internal.scouting.contracts import ScoutRequest

    monkeypatch.setattr(sd, "_STATE_DIR", tmp_path)

    def _boom(request):
        raise RuntimeError("simulated retrieval failure")
    monkeypatch.setattr(sd, "_retrieve_and_normalize", _boom)

    dispatcher = ScoutBroker(tmp_path)
    dispatcher.dispatch(ScoutRequest(turn_id="t1", inquiry="q1"))

    sd.run(poll_interval_s=0.05, max_iterations=3)

    reports = dispatcher.poll_reports()
    assert len(reports) == 1
    assert reports[0].status == "failed"


def test_worker_loop_never_blocks_on_an_empty_queue(tmp_path, monkeypatch):
    import aurora_scout_daemon as sd

    monkeypatch.setattr(sd, "_STATE_DIR", tmp_path)
    started = time.time()
    sd.run(poll_interval_s=0.05, max_iterations=3)
    assert time.time() - started < 2.0

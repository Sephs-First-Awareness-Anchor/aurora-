#!/usr/bin/env python3
"""
Regression coverage for aurora_scout_daemon.py (Subsurface Presence
and Evidence Scout spec, section 9 and the "Computational isolation"
acceptance criteria in section 20): the lightweight Scout worker must
never load a full Aurora instance, must never author a final response,
and its claim/process/submit loop must actually round-trip through a
real ScoutBroker.

Aurora Build 694, step 7: retrieval now goes through the ScoutBackend
abstraction (aurora_internal/scouting/backends.py) instead of a
hardcoded Room-only path -- these tests inject deterministic
TestBackend instances via the backends= parameter rather than
monkeypatching module-private Room-specific functions that no longer
exist.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aurora_internal.scouting.backends import TestBackend


def test_importing_scout_daemon_never_pulls_in_aurora_or_aurora_daemon():
    # Sunni & Cael: the literal, checkable version of "no full Aurora
    # boot occurs in Scout workers" -- importing aurora.py or
    # aurora_daemon.py at all executes their module-level setup (which
    # constructs genealogy/Dream/consciousness-engine/etc. state), so
    # this has to hold at IMPORT time, not just "boot_aurora() is never
    # called."
    # Deliberately checks only what importing THIS module newly pulls in,
    # not global sys.modules -- other test files in the same pytest
    # session legitimately import aurora.py/aurora_daemon.py for their
    # own reasons, and that prior import must not make this test flaky
    # or order-dependent.
    before = set(sys.modules.keys())
    import aurora_scout_daemon  # noqa: F401
    after = set(sys.modules.keys())
    newly_imported = after - before
    assert "aurora" not in newly_imported
    assert "aurora_daemon" not in newly_imported


def test_scout_report_from_worker_never_has_a_final_response_field(tmp_path):
    import aurora_scout_daemon as sd
    from aurora_internal.scouting.contracts import ScoutRequest

    req = ScoutRequest(turn_id="t1", inquiry="")  # empty inquiry -> no_evidence path
    report = sd._retrieve_and_normalize(req, state_dir=tmp_path)
    assert "final_response" not in report.to_dict()


def test_empty_inquiry_short_circuits_to_no_evidence_without_trying_any_backend(tmp_path):
    import aurora_scout_daemon as sd
    from aurora_internal.scouting.contracts import ScoutRequest

    called = {"is_available": False}
    class _WatchedBackend(TestBackend):
        def is_available(self_inner):
            called["is_available"] = True
            return True
    backend = _WatchedBackend(canned_result="should never be reached")

    req = ScoutRequest(turn_id="t1", inquiry="")
    report = sd._retrieve_and_normalize(req, state_dir=tmp_path, backends=[backend])
    assert report.status == "no_evidence"
    assert called["is_available"] is False


def test_retrieve_and_normalize_reports_no_evidence_when_no_backend_is_available(tmp_path):
    import aurora_scout_daemon as sd
    from aurora_internal.scouting.contracts import ScoutRequest

    unavailable = TestBackend(canned_result="unreachable", available=False)

    req = ScoutRequest(turn_id="t1", inquiry="what is a guitar chord")
    report = sd._retrieve_and_normalize(req, state_dir=tmp_path, backends=[unavailable])
    assert report.status == "no_evidence"
    assert report.fit_rationales == []  # retrieval worker must not invent reasons
    assert report.response_relationships == []


def test_retrieve_and_normalize_produces_evidence_when_a_backend_answers(tmp_path):
    import aurora_scout_daemon as sd
    from aurora_internal.scouting.contracts import ScoutRequest

    backend = TestBackend(canned_result="a guitar chord is three or more notes played together")

    req = ScoutRequest(
        turn_id="t1",
        interpreted_input="asking what a guitar chord is",
        inquiry="what is a guitar chord",
    )
    report = sd._retrieve_and_normalize(req, state_dir=tmp_path, backends=[backend])
    assert report.status == "ok"
    assert report.evidence_items
    assert "guitar chord" in report.evidence_items[0]["text"]
    assert report.evidence_items[0]["emittable"] is False
    assert report.response_relationships == []
    assert report.fit_rationales == []
    assert report.confidence > 0.0
    assert report.provenance == ["test"]
    assert "final_response" not in report.to_dict()


def test_retrieve_and_normalize_truncates_to_max_result_chars(tmp_path):
    import aurora_scout_daemon as sd
    from aurora_internal.scouting.contracts import ScoutRequest

    backend = TestBackend(canned_result="x" * 5000)

    req = ScoutRequest(turn_id="t1", inquiry="q", max_result_chars=50)
    report = sd._retrieve_and_normalize(req, state_dir=tmp_path, backends=[backend])
    assert len(report.evidence_items[0]["text"]) <= 50


def test_retrieve_and_normalize_falls_through_to_the_next_backend_in_the_chain(tmp_path):
    import aurora_scout_daemon as sd
    from aurora_internal.scouting.contracts import ScoutRequest

    unavailable = TestBackend(canned_result="never used", available=False)
    empty_result = TestBackend(canned_result="", available=True)
    real_answer = TestBackend(canned_result="the second real answer")

    req = ScoutRequest(turn_id="t1", inquiry="q")
    report = sd._retrieve_and_normalize(req, state_dir=tmp_path, backends=[unavailable, empty_result, real_answer])
    assert report.status == "ok"
    assert report.evidence_items[0]["text"] == "the second real answer"


def test_scout_never_reinterprets_raw_input_it_only_receives_the_interpreted_packet(tmp_path):
    # Sunni & Cael: the request itself carries interpreted_input as
    # CONTEXT the Scout is told about -- it never has its own separate
    # channel to the raw user utterance. This is a structural guarantee
    # (ScoutRequest simply has no raw_user_text field), verified here by
    # confirming the backend only ever receives the request object
    # itself (inquiry/interpreted_input), nothing else.
    import aurora_scout_daemon as sd
    from aurora_internal.scouting.contracts import ScoutRequest

    captured = {}
    class _CapturingBackend(TestBackend):
        def retrieve(self_inner, request, *, state_dir):
            captured["inquiry"] = request.inquiry
            captured["interpreted_input"] = request.interpreted_input
            return "evidence"
    backend = _CapturingBackend()

    req = ScoutRequest(turn_id="t1", interpreted_input="Aurora's own reading of the input", inquiry="the actual inquiry")
    sd._retrieve_and_normalize(req, state_dir=tmp_path, backends=[backend])
    assert captured["inquiry"] == "the actual inquiry"
    assert captured["interpreted_input"] == "Aurora's own reading of the input"


def test_retrieve_and_normalize_uses_the_supplied_state_dir_not_the_module_default(tmp_path):
    # Build 694 step 6: the whole point of this refactor -- a caller-
    # supplied state_dir must actually be what the backend receives,
    # never the module's own repo-relative _STATE_DIR default.
    import aurora_scout_daemon as sd
    from aurora_internal.scouting.contracts import ScoutRequest

    captured = {}
    class _CapturingBackend(TestBackend):
        def retrieve(self_inner, request, *, state_dir):
            captured["state_dir"] = state_dir
            return "evidence"
    backend = _CapturingBackend()

    android_like_dir = tmp_path / "android_app_state"
    req = ScoutRequest(turn_id="t1", inquiry="q")
    sd._retrieve_and_normalize(req, state_dir=android_like_dir, backends=[backend])
    assert str(captured["state_dir"]) == str(android_like_dir)
    assert str(captured["state_dir"]) != str(sd._STATE_DIR)


def test_worker_loop_round_trips_a_dispatched_request(tmp_path, monkeypatch):
    import aurora_scout_daemon as sd
    from aurora_internal.scouting.broker import ScoutBroker
    from aurora_internal.scouting.contracts import ScoutRequest

    monkeypatch.setattr(sd, "_STATE_DIR", tmp_path)

    dispatcher = ScoutBroker(tmp_path)
    req = ScoutRequest(turn_id="t1", inquiry="q1")
    dispatcher.dispatch(req)

    sd.run(poll_interval_s=0.05, max_iterations=3, backends=[TestBackend(canned_result="evidence text")])

    reports = dispatcher.poll_reports()
    assert len(reports) == 1
    assert reports[0].request_id == req.request_id
    assert reports[0].status == "ok"


def test_worker_loop_reports_failed_status_on_internal_exception(tmp_path, monkeypatch):
    import aurora_scout_daemon as sd
    from aurora_internal.scouting.broker import ScoutBroker
    from aurora_internal.scouting.contracts import ScoutRequest

    monkeypatch.setattr(sd, "_STATE_DIR", tmp_path)

    def _boom(request, *, state_dir, backends=None):
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


def test_run_accepts_an_explicit_state_dir_without_touching_the_module_default(tmp_path):
    # Build 694 step 6: run(state_dir=...) is the real caller-facing
    # contract (Android passes its own writable state directory
    # explicitly, spec step 8) -- must work without ever needing to
    # monkeypatch sd._STATE_DIR at all, and must never write anything
    # under the module's own repo-relative default in the process.
    import aurora_scout_daemon as sd
    from aurora_internal.scouting.broker import ScoutBroker
    from aurora_internal.scouting.contracts import ScoutRequest

    android_like_dir = tmp_path / "android_app_state"
    dispatcher = ScoutBroker(android_like_dir)
    req = ScoutRequest(turn_id="t1", inquiry="q1")
    dispatcher.dispatch(req)

    sd.run(
        state_dir=android_like_dir, poll_interval_s=0.05, max_iterations=3,
        backends=[TestBackend(canned_result="evidence text")],
    )

    reports = dispatcher.poll_reports()
    assert len(reports) == 1
    assert reports[0].status == "ok"
    # The request/report round-trip happened entirely under the
    # explicitly-supplied dir -- a broker pointed at the module's own
    # default would see nothing at all for this request_id (precise
    # per-request check, not a global "the default dir is empty"
    # assertion, since other tests/tooling in the same session may have
    # already touched the real repo's default aurora_state directory for
    # unrelated reasons).
    default_broker = ScoutBroker(sd._STATE_DIR)
    assert not (default_broker.claimed_dir / f"{req.request_id}.json").exists()
    assert not (default_broker.reports_dir / f"{req.request_id}.json").exists()


def test_run_falls_back_to_module_default_state_dir_when_none_supplied(tmp_path, monkeypatch):
    # The desktop `python3 aurora_scout_daemon.py` (no arguments) path
    # must keep working unchanged.
    import aurora_scout_daemon as sd

    monkeypatch.setattr(sd, "_STATE_DIR", tmp_path)
    started = time.time()
    sd.run(poll_interval_s=0.05, max_iterations=2)  # state_dir=None, backends=None
    assert time.time() - started < 2.0


def test_run_defaults_to_resolve_backend_chain_when_none_supplied(tmp_path, monkeypatch):
    # The desktop default (no backends= argument at all) must actually
    # resolve a real chain, not silently end up with zero backends.
    import aurora_scout_daemon as sd

    captured_chains = []
    def _fake_retrieve(request, *, state_dir, backends=None):
        captured_chains.append(backends)
        from aurora_internal.scouting.contracts import ScoutReport
        return ScoutReport(request_id=request.request_id, turn_id=request.turn_id, status="no_evidence")
    monkeypatch.setattr(sd, "_retrieve_and_normalize", _fake_retrieve)

    from aurora_internal.scouting.broker import ScoutBroker
    from aurora_internal.scouting.contracts import ScoutRequest
    dispatcher = ScoutBroker(tmp_path)
    dispatcher.dispatch(ScoutRequest(turn_id="t1", inquiry="q1"))

    sd.run(state_dir=tmp_path, poll_interval_s=0.05, max_iterations=1)

    assert len(captured_chains) == 1
    assert captured_chains[0] is not None
    assert len(captured_chains[0]) >= 1


def test_run_stops_when_stop_event_is_set(tmp_path):
    # Build 694 step 8: "independently stoppable" -- run() must exit its
    # loop once stop_event is set, without needing max_iterations at all
    # (production callers, e.g. Android, never pass max_iterations).
    import threading
    import aurora_scout_daemon as sd

    stop_event = threading.Event()
    thread = threading.Thread(
        target=lambda: sd.run(state_dir=tmp_path, poll_interval_s=0.05, stop_event=stop_event),
        daemon=True,
    )
    thread.start()
    time.sleep(0.2)
    assert thread.is_alive()  # still running -- would loop forever without the stop signal

    stop_event.set()
    thread.join(timeout=2.0)
    assert not thread.is_alive()


def test_run_wakes_immediately_on_stop_event_rather_than_waiting_out_the_poll_interval(tmp_path):
    # The empty-queue wait uses stop_event.wait(poll_interval_s) rather
    # than a plain time.sleep(), so a long poll interval doesn't delay
    # shutdown.
    import threading
    import aurora_scout_daemon as sd

    stop_event = threading.Event()
    started = time.time()

    def _run_with_long_poll():
        sd.run(state_dir=tmp_path, poll_interval_s=10.0, stop_event=stop_event)

    thread = threading.Thread(target=_run_with_long_poll, daemon=True)
    thread.start()
    time.sleep(0.1)
    stop_event.set()
    thread.join(timeout=2.0)
    elapsed = time.time() - started
    assert not thread.is_alive()
    assert elapsed < 2.0  # nowhere near the 10s poll interval

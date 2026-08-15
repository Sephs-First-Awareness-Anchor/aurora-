#!/usr/bin/env python3
"""
Required tests (Aurora Build 694 spec, section 31) for
SubsurfacePresenceRuntime (step 4): a dedicated, independently-scheduled
presence loop that must integrate turn events promptly regardless of
whatever the heavy autonomous daemon's own governor.recommended_sleep()
cadence (15/20/30s) currently is.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aurora_internal.dual_strata.subsurface_presence_runtime import (
    SubsurfacePresenceRuntime, start_subsurface_presence_runtime, DEFAULT_POLL_INTERVAL_S,
)
from aurora_internal.dual_strata import subsurface_presence as sp
from aurora_internal.scouting.broker import ScoutBroker
from aurora_internal.scouting.contracts import ScoutReport


def _wait_until(predicate, *, timeout=2.0, interval=0.02):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False


def test_tick_integrates_a_turn_open_event_synchronously(tmp_path):
    rt = SubsurfacePresenceRuntime(tmp_path)
    sp.write_turn_open(tmp_path, turn_id="t1", raw_input="hello")
    result = rt.tick()
    assert "turn_open" in result["integrated_kinds"]
    frame = sp.read_presence_frame(tmp_path)
    assert frame["turn_id"] == "t1"


def test_tick_integrates_turn_open_and_interpreted_turn_together(tmp_path):
    rt = SubsurfacePresenceRuntime(tmp_path)
    sp.write_turn_open(tmp_path, turn_id="t1", raw_input="hello")
    sp.write_interpreted_turn(tmp_path, turn_id="t1", interpreted_meaning="greeting", interpretation_confidence=0.9)
    result = rt.tick()
    assert set(result["integrated_kinds"]) == {"turn_open", "interpreted_turn"}
    frame = sp.read_presence_frame(tmp_path)
    assert frame["interpreted_meaning"] == "greeting"


def test_tick_writes_a_heartbeat_even_with_no_pending_events(tmp_path):
    rt = SubsurfacePresenceRuntime(tmp_path)
    assert sp.heartbeat_gap_ms(tmp_path) is None
    rt.tick()
    assert sp.heartbeat_gap_ms(tmp_path) is not None


def test_start_stop_are_idempotent_and_thread_actually_runs(tmp_path):
    rt = SubsurfacePresenceRuntime(tmp_path, poll_interval_s=0.05)
    rt.start()
    rt.start()  # must not raise or spawn a second thread
    assert rt.is_running()
    assert _wait_until(lambda: rt.tick_count > 0)
    rt.stop()
    rt.stop()  # must not raise
    assert not rt.is_running()


def test_presence_runtime_independent_of_governor_sleep(tmp_path, monkeypatch):
    # Required test (spec section 31): force the autonomous daemon sleep
    # recommendation to 30 seconds and verify a new conversational event
    # still enters PresenceFrame promptly -- the runtime has no
    # relationship to RuntimeConstraintGovernor.recommended_sleep() at
    # all, so patching it to always return 30.0 (as it would under
    # severe host pressure) must have zero effect on how fast a turn_open
    # event actually gets integrated.
    from aurora_internal.aurora_runtime_constraint_governor import RuntimeConstraintGovernor
    monkeypatch.setattr(RuntimeConstraintGovernor, "recommended_sleep", lambda self, systems, **kw: 30.0)

    rt = SubsurfacePresenceRuntime(tmp_path, poll_interval_s=0.05)
    rt.start()
    try:
        started = time.time()
        sp.write_turn_open(tmp_path, turn_id="t_urgent", raw_input="are you there")
        assert _wait_until(lambda: (sp.read_presence_frame(tmp_path) or {}).get("turn_id") == "t_urgent", timeout=1.0)
        elapsed = time.time() - started
        assert elapsed < 1.0  # nowhere near the mocked 30s governor cadence
    finally:
        rt.stop()


def test_runtime_consumes_scout_reports_and_folds_accepted_evidence(tmp_path):
    sp.write_presence_frame(tmp_path, turn_id="t1", response_fit_pressure=0.8)
    broker = ScoutBroker(tmp_path)
    broker.reports_dir.mkdir(parents=True, exist_ok=True)
    report = ScoutReport(
        request_id="r1", turn_id="t1", status="ok",
        evidence_items=[{"text": "some evidence"}], confidence=0.9,
    )
    (broker.reports_dir / "r1.json").write_text(__import__("json").dumps(report.to_dict()), encoding="utf-8")

    rt = SubsurfacePresenceRuntime(tmp_path)
    result = rt.tick()
    assert len(result["accepted_bindings"]) == 1
    frame = sp.read_presence_frame(tmp_path)
    assert frame["response_fit_pressure"] == 0.8  # evidence arrival is not understanding
    from aurora_internal.scouting.subsurface_scout_bridge import read_bindings_for_turn
    bindings = read_bindings_for_turn(tmp_path, "t1")
    assert bindings and bindings[-1]["status"] == "accepted"


def test_on_binding_change_callback_fires_only_when_something_is_accepted(tmp_path):
    calls = []
    rt = SubsurfacePresenceRuntime(tmp_path, on_binding_change=lambda bindings: calls.append(bindings))

    rt.tick()  # nothing pending at all
    assert calls == []

    sp.write_presence_frame(tmp_path, turn_id="t1", response_fit_pressure=0.5)
    broker = ScoutBroker(tmp_path)
    broker.reports_dir.mkdir(parents=True, exist_ok=True)
    report = ScoutReport(request_id="r1", turn_id="t1", status="ok", evidence_items=[{"text": "x"}], confidence=0.9)
    (broker.reports_dir / "r1.json").write_text(__import__("json").dumps(report.to_dict()), encoding="utf-8")

    rt.tick()
    assert len(calls) == 1
    assert len(calls[0]) == 1


def test_runtime_never_imports_aurora_or_aurora_daemon():
    # Structural guarantee this module's own docstring makes: no Dream/
    # genealogy/corpus training/full cognitive boot is even reachable
    # from here, because it never imports either heavy module at all.
    import ast
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(repo_root, "aurora_internal", "dual_strata", "subsurface_presence_runtime.py")
    with open(path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=path)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
    assert "aurora" not in imported
    assert "aurora_daemon" not in imported


def test_start_subsurface_presence_runtime_stashes_itself_on_systems_without_touching_it(tmp_path):
    systems = {"some_existing_key": "unchanged"}
    runtime = start_subsurface_presence_runtime(systems, state_dir=tmp_path, poll_interval_s=0.05)
    try:
        assert systems["_presence_runtime"] is runtime
        assert systems["some_existing_key"] == "unchanged"
        assert runtime.is_running()
    finally:
        runtime.stop()


def test_default_poll_interval_is_well_under_the_250ms_responsiveness_target():
    assert DEFAULT_POLL_INTERVAL_S < 0.25


# ── Build 694 step 17: PresenceMetrics wiring ───────────────────────────────

def test_runtime_holds_its_own_presence_metrics_instance(tmp_path):
    rt = SubsurfacePresenceRuntime(tmp_path)
    assert rt.metrics is not None
    assert rt.metrics.role == "presence_runtime"


def test_tick_records_presence_event_queue_depth(tmp_path):
    rt = SubsurfacePresenceRuntime(tmp_path)
    sp.write_turn_open(tmp_path, turn_id="t1", raw_input="hello")
    sp.write_interpreted_turn(tmp_path, turn_id="t1", interpreted_meaning="x")
    rt.tick()
    snap = rt.metrics.snapshot()
    assert snap["presence_event_queue_depth"] == 2


def test_tick_records_presence_processing_latency(tmp_path):
    rt = SubsurfacePresenceRuntime(tmp_path)
    rt.tick()
    snap = rt.metrics.snapshot()
    assert snap["presence_processing_latency_ms"]["count"] == 1


def test_tick_records_turn_open_and_interpreted_turn_latency(tmp_path):
    rt = SubsurfacePresenceRuntime(tmp_path)
    sp.write_turn_open(tmp_path, turn_id="t1", raw_input="hello")
    sp.write_interpreted_turn(tmp_path, turn_id="t1", interpreted_meaning="x", response_fit_pressure=0.1)
    rt.tick()
    snap = rt.metrics.snapshot()
    assert snap["turn_open_latency_ms"]["count"] == 1
    assert snap["interpreted_turn_latency_ms"]["count"] == 1


def test_metrics_snapshot_write_is_throttled_not_written_every_tick(tmp_path):
    rt = SubsurfacePresenceRuntime(tmp_path, metrics_write_interval_s=100.0)
    rt.tick()
    rt.tick()
    rt.tick()
    from aurora_internal.dual_strata.presence_metrics import read_all_snapshots
    # With a 100s throttle, at most one write could have landed across
    # three back-to-back ticks -- confirms this isn't writing a file
    # every single tick (which at the 150ms default cadence would be
    # wasteful I/O, exactly what step 17 avoids).
    snaps = read_all_snapshots(tmp_path)
    if "presence_runtime" in snaps:
        assert snaps["presence_runtime"]["presence_processing_latency_ms"]["count"] <= 1

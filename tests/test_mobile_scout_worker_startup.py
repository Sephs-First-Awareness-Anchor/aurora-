#!/usr/bin/env python3
"""
Regression coverage for the Aurora Build 694 spec's step 8: Android
must actually start exactly one lightweight Scout worker during
initialization -- never boot_aurora(), never a full Aurora import,
concurrency 1, independently stoppable, survives individual failed
requests, and operates against the actual Android state_dir.
"""
import ast
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "flutter_app", "android", "app", "src", "main", "python",
))

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BRIDGE_PATH = os.path.join(
    _REPO_ROOT, "flutter_app", "android", "app", "src", "main", "python", "aurora_bridge.py",
)


def _bridge_source() -> str:
    with open(_BRIDGE_PATH, "r", encoding="utf-8") as f:
        return f.read()


def _initialize_source() -> str:
    tree = ast.parse(_bridge_source(), filename=_BRIDGE_PATH)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "initialize":
            return ast.get_source_segment(_bridge_source(), node) or ""
    raise AssertionError("aurora_bridge.py has no top-level initialize() function")


# ── Structural checks (static, no boot required) ────────────────────────────

def test_initialize_calls_start_scout_worker_after_boot_aurora():
    source = _initialize_source()
    boot_idx = source.find("boot_aurora(")
    scout_idx = source.find("_start_scout_worker(")
    assert boot_idx != -1 and scout_idx != -1
    assert scout_idx > boot_idx


def test_start_scout_worker_never_imports_aurora_or_aurora_daemon_directly():
    tree = ast.parse(_bridge_source(), filename=_BRIDGE_PATH)
    fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_start_scout_worker")
    imported = set()
    for node in ast.walk(fn):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
    assert imported == {"aurora_scout_daemon"}


def test_start_scout_worker_uses_a_daemon_thread_not_the_main_process():
    source = _bridge_source()
    tree = ast.parse(source, filename=_BRIDGE_PATH)
    fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_start_scout_worker")
    fn_source = ast.get_source_segment(source, fn) or ""
    assert "threading.Thread(" in fn_source
    assert "daemon=True" in fn_source


# ── Functional checks (real thread, real broker round trip) ────────────────

def test_start_scout_worker_actually_claims_and_processes_a_request(tmp_path):
    import aurora_bridge as ab
    try:
        ab._start_scout_worker(str(tmp_path))
        assert ab._scout_worker_thread is not None
        assert ab._scout_worker_thread.is_alive()

        from aurora_internal.scouting.broker import ScoutBroker
        from aurora_internal.scouting.contracts import ScoutRequest
        broker = ScoutBroker(tmp_path)
        req = ScoutRequest(turn_id="t1", inquiry="q1")
        broker.dispatch(req)

        deadline = time.time() + 5.0
        reports = []
        while time.time() < deadline:
            reports = broker.poll_reports()
            if reports:
                break
            time.sleep(0.1)

        assert len(reports) == 1
        assert reports[0].request_id == req.request_id
    finally:
        ab.stop_scout_worker()


def test_start_scout_worker_is_idempotent(tmp_path):
    import aurora_bridge as ab
    try:
        ab._start_scout_worker(str(tmp_path))
        first_thread = ab._scout_worker_thread
        ab._start_scout_worker(str(tmp_path))  # must not spawn a second thread
        assert ab._scout_worker_thread is first_thread
    finally:
        ab.stop_scout_worker()


def test_stop_scout_worker_actually_stops_the_thread(tmp_path):
    import aurora_bridge as ab
    ab._start_scout_worker(str(tmp_path))
    assert ab._scout_worker_thread is not None
    ab.stop_scout_worker(timeout=3.0)
    assert ab._scout_worker_thread is None


def test_scout_worker_survives_a_failed_request_and_keeps_processing(tmp_path, monkeypatch):
    import aurora_bridge as ab
    import aurora_scout_daemon as sd

    def _boom(request, *, state_dir, backends=None):
        raise RuntimeError("simulated failure")
    monkeypatch.setattr(sd, "_retrieve_and_normalize", _boom)

    try:
        ab._start_scout_worker(str(tmp_path))

        from aurora_internal.scouting.broker import ScoutBroker
        from aurora_internal.scouting.contracts import ScoutRequest
        broker = ScoutBroker(tmp_path)
        broker.dispatch(ScoutRequest(turn_id="t1", inquiry="q1"))

        deadline = time.time() + 5.0
        reports = []
        while time.time() < deadline:
            reports = broker.poll_reports()
            if reports:
                break
            time.sleep(0.1)

        assert len(reports) == 1
        assert reports[0].status == "failed"
        assert ab._scout_worker_thread.is_alive()  # one bad request never kills the thread
    finally:
        ab.stop_scout_worker()


def test_scout_worker_operates_against_the_supplied_state_dir(tmp_path):
    import aurora_bridge as ab
    android_like_dir = tmp_path / "android_app_state"
    try:
        ab._start_scout_worker(str(android_like_dir))

        from aurora_internal.scouting.broker import ScoutBroker
        from aurora_internal.scouting.contracts import ScoutRequest
        broker = ScoutBroker(android_like_dir)
        req = ScoutRequest(turn_id="t1", inquiry="q1")
        broker.dispatch(req)

        deadline = time.time() + 5.0
        reports = []
        while time.time() < deadline:
            reports = broker.poll_reports()
            if reports:
                break
            time.sleep(0.1)
        assert len(reports) == 1
    finally:
        ab.stop_scout_worker()

#!/usr/bin/env python3
"""
Aurora Build 694 step 16 (Subsurface Presence and Evidence Scout spec,
section 26): "Update scripts/strata_stack.sh to include the Scout worker
as an actual component. Add scout.pid, scout.log and support start,
stop, restart, status."

Text-level structural checks against the real script (not a shell test
runner) -- consistent with the rest of this repo's Python test suite,
and sufficient to confirm the four required actions all know about the
scout component without needing to actually launch a display-dependent
desktop stack in CI.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_STACK_SCRIPT = os.path.join(_REPO_ROOT, "scripts", "strata_stack.sh")
_SCOUT_LAUNCHER = os.path.join(_REPO_ROOT, "scripts", "run_scout_worker.sh")


def _stack_source() -> str:
    with open(_STACK_SCRIPT, "r", encoding="utf-8") as f:
        return f.read()


def test_run_scout_worker_script_exists_and_is_executable():
    assert os.path.isfile(_SCOUT_LAUNCHER)
    assert os.access(_SCOUT_LAUNCHER, os.X_OK)


def test_run_scout_worker_invokes_the_scout_daemon_with_a_state_dir():
    with open(_SCOUT_LAUNCHER, "r", encoding="utf-8") as f:
        source = f.read()
    assert "aurora_scout_daemon.py" in source
    assert "--state-dir=" in source


def test_strata_stack_launches_scout_on_start():
    source = _stack_source()
    assert 'launch_component "scout" "$SCRIPT_DIR/run_scout_worker.sh"' in source


def test_strata_stack_stops_scout_by_pidfile_and_pattern():
    source = _stack_source()
    assert 'stop_by_pidfile "scout"' in source
    assert 'stop_by_pattern "aurora_scout_daemon.py"' in source


def test_strata_stack_reports_scout_status():
    source = _stack_source()
    assert 'status_component "scout"' in source


def test_scout_component_is_wired_into_all_four_actions():
    # start (launch_component), stop (stop_by_pidfile/stop_by_pattern),
    # restart (reuses stop_stack + start_stack, already covered above),
    # status (status_component) -- confirm scout appears in each
    # relevant function body, not just anywhere in the file.
    source = _stack_source()

    def _function_body(name: str) -> str:
        start = source.index(f"{name}() {{")
        depth = 0
        i = source.index("{", start)
        j = i
        while True:
            if source[j] == "{":
                depth += 1
            elif source[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        return source[i:j]

    assert '"scout"' in _function_body("start_stack")
    assert '"scout"' in _function_body("stop_stack")
    assert '"scout"' in _function_body("show_status")


def test_strata_stack_script_is_syntactically_valid_bash():
    result = subprocess.run(
        ["bash", "-n", _STACK_SCRIPT], capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, result.stderr


def test_status_action_runs_cleanly_and_lists_scout():
    result = subprocess.run(
        ["bash", _STACK_SCRIPT, "status"], capture_output=True, text=True, timeout=15, cwd=_REPO_ROOT,
    )
    assert result.returncode == 0, result.stderr
    assert "scout" in result.stdout

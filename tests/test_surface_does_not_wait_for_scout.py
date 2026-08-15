#!/usr/bin/env python3
"""
Required test (Subsurface Presence and Evidence Scout spec, section 21):
test_surface_does_not_wait_for_scout.py -- Surface's two Scout-dispatch
call sites (Step 10: aurora._try_poedex_lookup, Step 11:
aurora_daemon._maybe_research_recurring_issue) must return in
essentially constant time regardless of how many times they're called
or whether anything ever answers -- no accumulating wait, no blocking
poll loop left anywhere in either path.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aurora
import aurora_daemon as ad
import json


def test_repeated_surface_lookups_do_not_accumulate_latency(tmp_path):
    systems = {"state_dir": tmp_path, "_current_turn_id": "t1"}
    elapsed_per_call = []
    for i in range(5):
        started = time.time()
        aurora._try_poedex_lookup(f"topic number {i}", systems, use_researcher=True)
        elapsed_per_call.append(time.time() - started)

    assert all(e < 1.0 for e in elapsed_per_call)
    # No call should be dramatically slower than the first -- there is
    # no blocking wait anywhere in this path to accumulate.
    assert max(elapsed_per_call) < elapsed_per_call[0] + 1.0


def test_surface_lookup_returns_the_same_speed_whether_or_not_a_worker_exists(tmp_path):
    # Surface's dispatch call sites have no knowledge of, and no
    # dependency on, whether a Scout worker process is even running --
    # dispatch-and-forget must behave identically either way.
    systems = {"state_dir": tmp_path, "_current_turn_id": "t1"}
    started = time.time()
    aurora._try_poedex_lookup("no worker will ever claim this", systems, use_researcher=True)
    elapsed = time.time() - started
    assert elapsed < 1.0


def test_recurring_issue_dispatch_also_does_not_wait(tmp_path, monkeypatch):
    monkeypatch.setattr(ad, "_STATE_DIR", tmp_path)
    (tmp_path / "daemon_status.json").write_text(json.dumps({
        "fail_summary": [{"dim": "no_wait_check", "avg_sev": 0.7, "fails": 80}],
        "qao_recent_events": 5, "qao_top_issue": "?",
    }), encoding="utf-8")

    started = time.time()
    ad._maybe_research_recurring_issue({}, "LOW")
    elapsed = time.time() - started
    assert elapsed < 1.0


def test_surface_modules_contain_no_sleep_based_polling_loop_around_scout_state():
    # A blocking wait re-introduced as a plain `while ...: time.sleep(...)`
    # loop polling scout_reports/broker state, rather than going back
    # through ScoutBroker.poll_reports() (which is separately banned for
    # Surface, see test_scout_report_routes_only_to_subsurface.py),
    # would still violate this guarantee. Confirm neither Surface module
    # contains a sleep call anywhere near scout/broker/report text.
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for rel in ("aurora.py", "aurora_surface_daemon.py"):
        with open(os.path.join(repo_root, rel), "r", encoding="utf-8") as f:
            lines = f.readlines()
        for i, line in enumerate(lines):
            if "scout" not in line.lower():
                continue
            window = "".join(lines[max(0, i - 3): i + 4]).lower()
            assert "time.sleep" not in window, (
                f"{rel}:{i+1} appears to combine a sleep with Scout-related code -- "
                "Surface must never poll/wait on Scout state"
            )

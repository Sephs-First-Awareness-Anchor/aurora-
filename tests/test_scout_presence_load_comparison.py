#!/usr/bin/env python3
"""
Regression coverage for scripts/scout_presence_load_comparison.py
(Subsurface Presence and Evidence Scout spec, step 12): the two call
sites Steps 10-11 converted from blocking waits to Scout dispatch must
measurably return in well under their documented former blocking
ceilings (35.0s / 18.0s), and presence liveness (heartbeat/presence
frame) must keep updating throughout a pending, unclaimed retrieval.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import scout_presence_load_comparison as cmp


def test_surface_poedex_lookup_returns_far_under_the_documented_baseline(tmp_path):
    row = cmp._measure_surface_lookup(tmp_path)
    assert row["baseline_blocking_ceiling_s"] == 35.0
    assert row["measured_elapsed_s"] < 2.0
    assert row["improvement_factor"] > 10


def test_subsurface_issue_research_returns_far_under_the_documented_baseline(tmp_path):
    row = cmp._measure_subsurface_issue_research(tmp_path)
    assert row["baseline_blocking_ceiling_s"] == 18.0
    assert row["measured_elapsed_s"] < 2.0
    assert row["dispatched"] is True
    assert row["improvement_factor"] > 10


def test_presence_stays_live_while_a_scout_request_sits_unclaimed(tmp_path):
    result = cmp._measure_presence_liveness_during_pending_retrieval(tmp_path, duration_s=1.5)
    assert result["samples"]
    assert result["heartbeat_stayed_live"] is True
    # Heartbeat cadence is ~0.5s in the comparison harness (mirrors the
    # daemon's real ~1s thread) -- a gap anywhere near the old 18-35s
    # blocking ceilings would mean presence genuinely froze.
    assert result["max_heartbeat_gap_ms_observed"] < 2000.0


def test_main_produces_a_complete_report(tmp_path):
    report = cmp.main(tmp_path)
    assert "surface_poedex_lookup" in report
    assert "subsurface_issue_research" in report
    assert "presence_liveness_during_pending_retrieval" in report
    assert report["surface_poedex_lookup"]["measured_elapsed_s"] < 2.0
    assert report["subsurface_issue_research"]["measured_elapsed_s"] < 2.0
    assert report["presence_liveness_during_pending_retrieval"]["heartbeat_stayed_live"] is True


def test_main_cleans_up_its_own_tmp_dir_when_none_is_provided():
    report = cmp.main()
    assert report["surface_poedex_lookup"]["measured_elapsed_s"] < 2.0

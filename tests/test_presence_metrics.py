#!/usr/bin/env python3
"""
Regression coverage for aurora_internal/dual_strata/presence_metrics.py
(Subsurface Presence and Evidence Scout spec, section 19): the baseline
instrumentation recorded BEFORE any of Steps 2-11's behavioral changes,
so there's a real before/after to compare (spec step 12).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aurora_internal.dual_strata.presence_metrics import PresenceMetrics, read_all_snapshots
from aurora_internal.dual_strata import subsurface_presence as sp


def test_snapshot_includes_all_spec_section_19_fields(tmp_path):
    m = PresenceMetrics(tmp_path, role="surface")
    snap = m.snapshot()

    for key in (
        "process_rss_mb", "mem_available_mb", "load_ratio",
        "subsurface_presence_frame_age_ms", "subsurface_heartbeat_gap_ms",
        "scout_queue_depth", "scout_active_count",
        "surface_direct_retrieval_count", "subsurface_direct_retrieval_count",
    ):
        assert key in snap, f"missing required metric: {key}"

    for key in (
        "surface_turn_latency_ms", "subsurface_main_loop_block_ms",
        "scout_dispatch_ms", "scout_roundtrip_ms", "scout_integration_ms",
    ):
        assert key in snap
        assert "count" in snap[key]


def test_snapshot_with_no_samples_reports_zero_counts_not_error(tmp_path):
    m = PresenceMetrics(tmp_path, role="surface")
    snap = m.snapshot()
    assert snap["surface_turn_latency_ms"]["count"] == 0
    assert snap["surface_turn_latency_ms"]["p50"] == 0.0


def test_recorded_latencies_show_up_in_percentiles(tmp_path):
    m = PresenceMetrics(tmp_path, role="surface")
    for ms in (100.0, 200.0, 300.0, 400.0, 500.0):
        m.record_surface_turn_latency_ms(ms)
    snap = m.snapshot()
    assert snap["surface_turn_latency_ms"]["count"] == 5
    assert snap["surface_turn_latency_ms"]["p50"] == 300.0
    assert snap["surface_turn_latency_ms"]["max"] == 500.0


def test_scout_queue_and_active_counts_reflect_last_set_value(tmp_path):
    m = PresenceMetrics(tmp_path, role="subsurface")
    m.set_scout_queue_depth(3)
    m.set_scout_active_count(1)
    snap = m.snapshot()
    assert snap["scout_queue_depth"] == 3
    assert snap["scout_active_count"] == 1


def test_direct_retrieval_counters_increment(tmp_path):
    m = PresenceMetrics(tmp_path, role="surface")
    m.record_surface_direct_retrieval()
    m.record_surface_direct_retrieval()
    m.record_subsurface_direct_retrieval()
    snap = m.snapshot()
    assert snap["surface_direct_retrieval_count"] == 2
    assert snap["subsurface_direct_retrieval_count"] == 1


def test_snapshot_reflects_real_presence_frame_age(tmp_path):
    sp.write_presence_frame(tmp_path, turn_id="t1")
    m = PresenceMetrics(tmp_path, role="surface")
    snap = m.snapshot()
    assert snap["subsurface_presence_frame_age_ms"] is not None
    assert snap["subsurface_presence_frame_age_ms"] >= 0.0


def test_snapshot_with_no_presence_frame_reports_none_age(tmp_path):
    m = PresenceMetrics(tmp_path, role="surface")
    snap = m.snapshot()
    assert snap["subsurface_presence_frame_age_ms"] is None


def test_write_snapshot_persists_and_is_readable_by_role(tmp_path):
    m_surface = PresenceMetrics(tmp_path, role="surface")
    m_surface.record_surface_turn_latency_ms(150.0)
    m_surface.write_snapshot()

    m_subsurface = PresenceMetrics(tmp_path, role="subsurface")
    m_subsurface.set_scout_active_count(2)
    m_subsurface.write_snapshot()

    all_snaps = read_all_snapshots(tmp_path)
    assert "surface" in all_snaps
    assert "subsurface" in all_snaps
    assert all_snaps["surface"]["surface_turn_latency_ms"]["count"] == 1
    assert all_snaps["subsurface"]["scout_active_count"] == 2


def test_read_all_snapshots_with_no_file_returns_empty_dict(tmp_path):
    assert read_all_snapshots(tmp_path) == {}


def test_write_snapshot_for_one_role_does_not_clobber_another_roles_snapshot(tmp_path):
    PresenceMetrics(tmp_path, role="surface").write_snapshot()
    PresenceMetrics(tmp_path, role="subsurface").write_snapshot()
    PresenceMetrics(tmp_path, role="surface").write_snapshot()

    all_snaps = read_all_snapshots(tmp_path)
    assert set(all_snaps.keys()) == {"surface", "subsurface"}

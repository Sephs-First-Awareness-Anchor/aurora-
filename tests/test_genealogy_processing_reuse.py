"""Evidence-preserving genealogy optimizations for phone response processing.

These checks assert that we eliminate redundant work, not the events or the
same underlying X/T/N/B/A measurements. In particular, a no-relief tick
still advances the governor and records participation in the activity log.
"""
from __future__ import annotations

from types import SimpleNamespace
import hashlib

from aurora_internal.constraint_genealogy import (
    AXES, ConstraintGenealogyLogger, GenealogyConfig, PressureVec, TraceItem,
    _aggregate_link_curve_stats, _bounded_collision_counterparts,
)


def _old_six_pass_reference(links):
    """The original global + five-axis comprehension logic."""
    all_links = list(links)
    global_mean = (
        sum(link.depth for link in all_links) / len(all_links)
        if all_links else 0.0
    )
    counts = {}
    means = {}
    for ax in AXES:
        matching = [
            link for link in all_links
            if (link.dominant_relief_axis or "X") == ax
        ]
        counts[ax] = len(matching)
        means[ax] = (
            sum(link.depth for link in matching) / len(matching)
            if matching else 0.0
        )
    return len(all_links), global_mean, counts, means


def test_single_pass_matches_all_six_previous_curve_statistics_exactly():
    for links in (
        [],
        [SimpleNamespace(depth=1, dominant_relief_axis=None)],
        [
            SimpleNamespace(depth=(index % 7) + 1,
                            dominant_relief_axis=("X", "T", "N", "B", "A", None, "Z")[index % 7])
            for index in range(407)
        ],
    ):
        assert _aggregate_link_curve_stats(links) == _old_six_pass_reference(links)


def test_single_pass_has_one_iteration_regardless_of_link_count():
    class OnePass:
        def __init__(self):
            self.iterations = 0

        def __iter__(self):
            self.iterations += 1
            assert self.iterations == 1, "global and per-axis curves must share one reading"
            for index in range(20_000):
                yield SimpleNamespace(depth=(index % 19) + 1,
                                      dominant_relief_axis=AXES[index % len(AXES)])

    links = OnePass()
    n, mean, counts, axis_means = _aggregate_link_curve_stats(links)
    assert n == 20_000
    assert sum(counts.values()) == 20_000
    assert mean > 0 and all(value > 0 for value in axis_means.values())


def test_no_relief_tick_still_records_activity_without_wasted_outlet_scan(tmp_path):
    genealogy = ConstraintGenealogyLogger(
        run_id="no_relief", config=GenealogyConfig(), output_dir=str(tmp_path)
    )
    outlet_reads = []
    genealogy._outlet_fraction = lambda: outlet_reads.append(1) or 0.0
    pressure = PressureVec(X=0.5, T=0.5, N=0.5, B=0.5, A=0.5)
    recorded = genealogy.observe(
        pressure,
        [TraceItem(kind="ABILITY", id="X:OBSERVE")],
        pressure,
    )
    assert recorded is None
    assert outlet_reads == [], "outlet baseline is unused on a no-relief tick"
    assert genealogy.tick_count == 1
    assert genealogy.skipped_no_relief == 1
    assert genealogy.activity_in_window(1).get("X:OBSERVE") == 1
    assert genealogy._last_observe_profile["tick"] == 1
    assert genealogy._last_observe_profile["compute_ms"] >= 0.0


def _old_candidate_selection(bucket, active_id, scan_budget, tick):
    all_counterparts = [iid for iid in bucket if iid != active_id]
    if len(all_counterparts) > scan_budget:
        head_count = max(1, scan_budget // 2)
        head = all_counterparts[:head_count]
        tail = all_counterparts[head_count:]
        rotating_count = scan_budget - len(head)
        seed = int(hashlib.sha1(active_id.encode()).hexdigest()[:8], 16)
        start = (int(tick) + seed) % len(tail)
        rotated = tail[start:] + tail[:start]
        all_counterparts = head + rotated[:rotating_count]
    return all_counterparts


def test_bounded_candidate_rotation_preserves_exact_membership_and_order():
    # No candidates may become permanently unreachable through this change.
    for size in (0, 1, 2, 3, 8, 31, 32, 33, 64, 65, 132, 1500):
        bucket = [f"R:{i}" for i in range(size)]
        for active_id in ("R:0", f"R:{size // 2}", f"R:{size - 1}", "R:absent"):
            for budget in (1, 2, 3, 16, 32, 64, 101):
                for tick in (0, 1, 13, 5032):
                    assert _bounded_collision_counterparts(bucket, active_id, budget, tick) == (
                        _old_candidate_selection(bucket, active_id, budget, tick)
                    )


def test_large_candidate_search_never_materializes_entire_rotated_tail():
    class NoSlices(list):
        def __getitem__(self, index):
            if isinstance(index, slice):
                raise AssertionError("expensive tail copy and rotation attempted")
            return super().__getitem__(index)

    bucket = NoSlices(f"R:{i}" for i in range(100_000))
    for tick in (0, 1, 193, 100_000):
        result = _bounded_collision_counterparts(bucket, "R:9", 64, tick)
        assert len(result) == 64
        assert "R:9" not in result
        assert result == _old_candidate_selection(list(bucket), "R:9", 64, tick)

"""Evidence-preserving genealogy optimizations for phone response processing.

These checks assert that we eliminate redundant work, not the events or the
same underlying X/T/N/B/A measurements. In particular, a no-relief tick
still advances the governor and records participation in the activity log.
"""
from __future__ import annotations

from types import SimpleNamespace

from aurora_internal.constraint_genealogy import (
    AXES, ConstraintGenealogyLogger, GenealogyConfig, PressureVec, TraceItem,
    _aggregate_link_curve_stats,
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

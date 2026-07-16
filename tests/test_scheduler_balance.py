# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
R1.5 Remediation Addendum (2026-07-15), scheduler-balance rule: within any
rolling window, no candidate dimension may fall more than
_SCHEDULER_BALANCE_TOLERANCE lessons behind the most-fed dimension in that
same window. select_curriculum() previously ranked purely by
fail_points.json fail_count -- with a small `n` (e.g. the daemon's n=4
cycles) a chronically-low-fail-count dimension could go starved for many
calls in a row, since nothing ever forced coverage of the dimensions that
never bubble to the top of that ranking.

These tests hold _balance_starved_dimensions_first() and
_recent_dimension_counts() to the addendum's own numbers (window=20,
tolerance=2) and confirm select_curriculum() actually applies the pull
in the case that mattered: a small n starving one dimension across
repeated calls.
"""
import json

from aurora_classroom import (
    _SCHEDULER_BALANCE_TOLERANCE,
    _SCHEDULER_BALANCE_WINDOW,
    _balance_starved_dimensions_first,
    _recent_dimension_counts,
    select_curriculum,
)


def _write_classroom_log(tmp_path, dimensions):
    log_path = tmp_path / "classroom_log.jsonl"
    with open(log_path, "a", encoding="utf-8") as f:
        for i, dim in enumerate(dimensions):
            f.write(json.dumps({"target_dimension": dim, "timestamp": 1000.0 + i, "divergence_score": 0.1}) + "\n")


def test_recent_dimension_counts_reflects_the_log(tmp_path):
    _write_classroom_log(tmp_path, ["a", "a", "b", "c"])
    counts = _recent_dimension_counts(tmp_path)
    assert counts == {"a": 2, "b": 1, "c": 1}


def test_recent_dimension_counts_only_looks_at_the_window(tmp_path):
    _write_classroom_log(tmp_path, ["old"] * 25 + ["new"] * 5)
    counts = _recent_dimension_counts(tmp_path, window=10)
    assert counts.get("old", 0) <= 5  # only the tail 10 lines are in-window
    assert counts.get("new", 0) == 5


def test_recent_dimension_counts_degrades_gracefully_on_missing_log(tmp_path):
    assert _recent_dimension_counts(tmp_path / "nowhere") == {}


def test_balance_pulls_starved_dimension_to_front():
    ranked = ["a", "b", "c"]  # fail_count order
    recent_counts = {"a": 5, "b": 5, "c": 0}  # c is 5 behind, tolerance is 2
    result = _balance_starved_dimensions_first(ranked, recent_counts, tolerance=2)
    assert result[0] == "c"


def test_balance_no_op_when_within_tolerance():
    ranked = ["a", "b", "c"]
    recent_counts = {"a": 3, "b": 2, "c": 2}  # max spread is 1, within tolerance
    assert _balance_starved_dimensions_first(ranked, recent_counts, tolerance=2) == ranked


def test_balance_no_op_with_empty_recent_counts():
    ranked = ["a", "b", "c"]
    assert _balance_starved_dimensions_first(ranked, {}, tolerance=2) == ranked


def test_balance_most_starved_goes_first_among_multiple_starved():
    ranked = ["a", "b", "c", "d"]
    recent_counts = {"a": 10, "b": 0, "c": 1, "d": 10}
    result = _balance_starved_dimensions_first(ranked, recent_counts, tolerance=2)
    assert result[0] == "b"  # most starved (count 0)
    assert result[1] == "c"  # next most starved (count 1)


def test_select_curriculum_prevents_starvation_across_repeated_small_n_calls(tmp_path):
    """The exact failure mode the addendum flags: a chronically-low
    fail_count dimension starved across many n=4-style calls. With the
    balance pass, once it falls _SCHEDULER_BALANCE_TOLERANCE behind, it
    must be pulled into the very next plan."""
    records = {
        "high_fail_a": {"fail_count": 50, "examples": []},
        "high_fail_b": {"fail_count": 40, "examples": []},
        "high_fail_c": {"fail_count": 30, "examples": []},
        "low_fail_starved": {"fail_count": 1, "examples": []},
    }
    (tmp_path / "fail_points.json").write_text(json.dumps({"records": records}))
    systems = {"state_dir": str(tmp_path)}

    # Simulate several n=4 calls all ranking the same way by fail_count --
    # without balancing, low_fail_starved would never appear.
    seen_dims = set()
    for _ in range(4):
        plan = select_curriculum(systems, n=3, state_dir=str(tmp_path))
        for dim, _seed, _source in plan:
            seen_dims.add(dim)
        _write_classroom_log(tmp_path, [d for d, _s, _c in plan])

    assert "low_fail_starved" in seen_dims, (
        "the balance pass must eventually force coverage of a "
        "chronically-low-fail-count dimension"
    )

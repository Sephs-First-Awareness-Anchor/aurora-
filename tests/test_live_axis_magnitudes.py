# Authors: Sunni (Sir) Morningstar & Cael Devo
"""The live feed into DifferenceHistoryBuffer carries real per-axis pressure.

Before this, aurora.py's per-turn tick looked up per-axis keys that the
conscious crest does not carry ({axis, intensity, label}), so every axis was
recorded as 0.5 every turn: zero drift, subsurface tension ~1e-4, and the
attention engine's salience could not follow anything the subsurface did.
"""
from aurora_internal.aurora_constraint_manifold_patched import Constraint
from aurora_internal.aurora_difference_buffer import (
    DifferenceHistoryBuffer, live_axis_magnitudes,
)


class _Field:
    def __init__(self, pressures):
        self.p = pressures

    def status(self):
        return {"axis_pressures": dict(self.p)}


def test_field_pressure_is_the_primary_source():
    m = live_axis_magnitudes({"identity_field": _Field(
        {"X": 0.2, "T": 0.3, "N": 0.4, "B": 0.1, "A": 0.9})})
    assert m[Constraint.X] == 0.2 and m[Constraint.A] == 0.9


def test_zero_pressure_is_zero_not_neutral():
    m = live_axis_magnitudes({"identity_field": _Field(
        {"X": 0.0, "T": 0.0, "N": 0.0, "B": 0.0, "A": 0.0})})
    assert all(v == 0.0 for v in m.values())


def test_crest_fills_only_the_axis_the_field_does_not_report():
    systems = {
        "identity_field": _Field({"X": 0.2}),
        "_live_conscious_crest": {"temporal": 0.7, "energy": 0.6},
    }
    m = live_axis_magnitudes(systems)
    assert m[Constraint.X] == 0.2          # field wins
    assert m[Constraint.T] == 0.7          # crest fills
    assert m[Constraint.N] == 0.6
    assert m[Constraint.B] == 0.5          # neither says anything -> neutral


def test_nothing_available_is_neutral_everywhere():
    m = live_axis_magnitudes({})
    assert all(v == 0.5 for v in m.values())


def test_moving_field_produces_drift_where_the_old_feed_could_not():
    buf = DifferenceHistoryBuffer()
    # The old feed: crest has no per-axis keys -> 0.5 on every axis every turn.
    for t in range(1, 4):
        buf.record(tick=t, magnitudes={c: 0.5 for c in Constraint})
    flat = buf.snapshot(tick=3)
    flat_drift = sum(abs(v) for v in flat.values.values()) / 5

    live = DifferenceHistoryBuffer()
    for t, level in enumerate((0.2, 0.2, 0.7), start=1):
        live.record(tick=t, magnitudes=live_axis_magnitudes({"identity_field": _Field(
            {"X": level, "T": level, "N": level, "B": level, "A": level})}))
    moved = live.snapshot(tick=3)
    moved_drift = sum(abs(v) for v in moved.values.values()) / 5
    assert moved_drift > flat_drift + 0.05


def test_live_turn_tick_uses_the_shared_feed():
    import pathlib
    src = pathlib.Path(__file__).resolve().parents[1].joinpath("aurora.py").read_text(encoding="utf-8")
    assert "live_axis_magnitudes as _live_axis_mags" in src
    assert "_cc_pt.get(_ckey_pt" not in src

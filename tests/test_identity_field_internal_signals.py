"""Her own state must be able to reach the identity field.

aurora.py's internal signal pump, the reflection cycle and the heartbeat all call
identity_field.ingest_internal_signal(kind, magnitude, source_axis) behind hasattr guards; the
method was defined nowhere, so every call was silently skipped and no internal state (coherence
deficit, novelty, stagnation, thermal load, valuation, tension) ever reached the field.

Authors: Sunni (Sir) Morningstar and Cael Devo
"""
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_manifold_directory.noncomp_field import NoncompField  # noqa: E402


def _p(field):
    return field.status()["axis_pressures"]


def test_the_method_exists_so_the_guarded_calls_stop_being_skipped():
    assert hasattr(NoncompField, "ingest_internal_signal")


@pytest.mark.parametrize("axis", ["X", "T", "N", "B", "A"])
def test_an_internal_signal_raises_pressure_on_its_axis(axis):
    f = NoncompField()
    before = _p(f)[axis]
    f.ingest_internal_signal("emotion", magnitude=0.8, source_axis=axis)
    assert _p(f)[axis] > before


def test_it_is_the_same_physics_as_an_external_input():
    a, b = NoncompField(), NoncompField()
    a.ingest_internal_signal("reasoning", magnitude=0.5, source_axis="B")
    b.ingest_external_input({"B": 1.0}, intensity=0.5, source="x")
    assert _p(a)["B"] == pytest.approx(_p(b)["B"])


def test_magnitude_scales_the_pressure_and_zero_does_nothing():
    f, g, h = NoncompField(), NoncompField(), NoncompField()
    f.ingest_internal_signal("memory", magnitude=0.2, source_axis="X")
    g.ingest_internal_signal("memory", magnitude=0.9, source_axis="X")
    h.ingest_internal_signal("memory", magnitude=0.0, source_axis="X")
    assert _p(g)["X"] > _p(f)["X"] > _p(h)["X"] == pytest.approx(_p(NoncompField())["X"])


@pytest.mark.parametrize("axis", ["", "Z", None, "x "])
def test_an_unknown_axis_is_ignored_not_a_crash(axis):
    f = NoncompField()
    before = dict(_p(f))
    f.ingest_internal_signal("emotion", magnitude=1.0, source_axis=axis)
    assert _p(f) == before


def test_internal_signals_are_recorded_with_their_kind():
    f = NoncompField()
    f.ingest_internal_signal("valuation", magnitude=0.6, source_axis="A")
    f.ingest_internal_signal("tension", magnitude=0.4, source_axis="N")
    assert f.recent_internal_signals() == [("valuation", "A", 0.6), ("tension", "N", 0.4)]


def test_pressure_stays_in_range_under_a_flood():
    f = NoncompField()
    for _ in range(200):
        f.ingest_internal_signal("tension", magnitude=1.0, source_axis="N")
    assert 0.0 <= _p(f)["N"] <= 1.0


# ---- the reflection's signals carry what was resolved, not constants ---------------------------

def test_valuation_strength_is_the_resolved_accuracy_not_a_constant():
    src = open(os.path.join(REPO_ROOT, "aurora.py"), encoding="utf-8").read()
    i = src.index("ingest_internal_signal('valuation'")
    block = src[i - 600:i + 200]
    assert "resolved_accuracy" in block and "magnitude=0.6" not in block


def test_a_failed_reconciliation_still_reports_its_tension():
    src = open(os.path.join(REPO_ROOT, "aurora_internal", "aurora_understanding_contract.py"), encoding="utf-8").read()
    i = src.index("tension = self._compute_tension(state_snapshot, reentry)")
    j = src.index("reconciled, flags = self._attempt_reconciliation(tension)")
    assert 'result["tension_total"]' in src[i:j], "must be recorded before the success/failure branch"

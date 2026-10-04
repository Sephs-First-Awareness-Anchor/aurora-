"""Her agency must be hers, and it must reach every consumer of the assembly.

The observed user turn is a PERSISTENT node: its agency axis is zero by MODE. The assembly
built from it was the only axis state selection, learning and the dual-strata predictor saw,
so her agency was 0.0 on every turn. Her state lives in the identity field (stateful,
history-dependent); the assembly is now filled from it at the source.

Authors: Sunni (Sir) Morningstar and Cael Devo
"""
import os
import sys
from types import SimpleNamespace

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_internal.aurora_sender_state import (  # noqa: E402
    fill_assembly_axes_from_sender, fill_inactive_axes, sender_axis_state,
)


class _Field:
    def __init__(self, pressures, ref=0.10):
        self._p = dict(pressures)
        self._ref = ref

    def status(self):
        return {"axis_pressures": dict(self._p)}

    def reference_axis_pressures(self):
        return {ax: self._ref for ax in "XTNBA"}


FIELD = _Field({"X": 0.82, "T": 0.82, "N": 0.82, "B": 0.82, "A": 0.55})
DCE = {"existence": 0.175, "temporal": 0.045, "energy": 0.03, "boundary": 0.105, "agency": 0.0}


# ---- her state -------------------------------------------------------------------------

def test_her_state_is_pressure_above_the_fields_own_reference():
    s = sender_axis_state(FIELD)
    assert s["A"] == pytest.approx(0.45) and s["X"] == pytest.approx(0.72)


def test_the_reference_comes_from_the_field_not_a_constant_here():
    s = sender_axis_state(_Field({ax: 0.5 for ax in "XTNBA"}, ref=0.4))
    assert all(v == pytest.approx(0.1) for v in s.values())


@pytest.mark.parametrize("field", [None, object(), _Field({ax: 0.1 for ax in "XTNBA"})])
def test_no_state_above_reference_means_no_sender_state(field):
    assert sender_axis_state(field) is None


def test_an_unreadable_field_is_no_state_not_a_crash():
    class Broken:
        def status(self):
            raise RuntimeError("field offline")
    assert sender_axis_state(Broken()) is None


def test_the_real_identity_field_gives_a_state():
    from aurora_manifold_directory.noncomp_field import NoncompField
    f = NoncompField()
    f.ingest_external_input({"A": 1.0}, intensity=1.0, source="test")
    s = sender_axis_state(f)
    assert s is not None and s["A"] > 0.0


# ---- the fill at the source ---------------------------------------------------------------

def test_the_assemblys_zero_agency_is_filled_in_place_under_the_dces_names():
    axes = dict(DCE)
    changed = fill_assembly_axes_from_sender(axes, FIELD)
    assert changed == ["A"]
    assert axes["agency"] > 0.0
    for k in ("existence", "temporal", "energy", "boundary"):
        assert axes[k] == DCE[k], "axes the assembly carries are never altered"


def test_the_fill_is_scale_matched_to_the_assembly():
    axes = dict(DCE)
    fill_assembly_axes_from_sender(axes, FIELD)
    active = [DCE[k] for k in ("existence", "temporal", "energy", "boundary")]
    # sender weight relative to the active axes, expressed in the assembly's own unit
    expected = 0.45 * (sum(active) / (4 * 0.72))
    assert axes["agency"] == pytest.approx(expected, abs=1e-3)
    assert axes["agency"] < 0.25, "must live in the assembly's 0..~0.25 range, not the field's"


def test_it_works_under_short_names_too():
    axes = {"X": 0.2, "T": 0.1, "N": 0.1, "B": 0.1, "A": 0.0}
    assert fill_assembly_axes_from_sender(axes, FIELD) == ["A"] and axes["A"] > 0.0


@pytest.mark.parametrize("axes", [{}, None, {"unrelated": 1.0}])
def test_nothing_to_fill(axes):
    assert fill_assembly_axes_from_sender(axes, FIELD) == []


def test_no_field_changes_nothing():
    axes = dict(DCE)
    assert fill_assembly_axes_from_sender(axes, None) == [] and axes == DCE


def test_agency_follows_the_fields_state_so_it_is_history_dependent():
    low, high = dict(DCE), dict(DCE)
    fill_assembly_axes_from_sender(low, _Field({"X": 0.82, "T": 0.82, "N": 0.82, "B": 0.82, "A": 0.30}))
    fill_assembly_axes_from_sender(high, _Field({"X": 0.82, "T": 0.82, "N": 0.82, "B": 0.82, "A": 0.86}))
    assert high["agency"] > low["agency"] > 0.0


def test_the_composers_fill_is_the_same_implementation():
    import aurora_expression_perception as ep
    assert ep.fill_inactive_axes is fill_inactive_axes


# ---- ordering: the dual-strata snapshot reads these axes, so the fill must precede it --------------

def test_the_fill_runs_before_the_dual_strata_snapshot_reads_the_axes():
    src = open(os.path.join(REPO_ROOT, "aurora_consciousness_engine.py"), encoding="utf-8").read()
    assert src.index("fill_assembly_axes_from_sender(result.adjusted_axes") < src.index(
        "result = self._attach_dual_strata_snapshot(")

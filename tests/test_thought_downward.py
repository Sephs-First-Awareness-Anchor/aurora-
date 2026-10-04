"""A completed Thought writes at its own depth and resolves the tension it converged from.

AURORA_COGNITIVE_PHYSICS section 7, Thought: "Writes to Memory at appropriate stratigraphic depth;
Resets Pressure topology (completed Thought resolves accumulated tension)", and "MAY NOT be
produced with any axis inactive -- partial convergence is not Thought".

Authors: Sunni (Sir) Morningstar and Cael Devo
"""
import os
import sys
from types import SimpleNamespace

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_consciousness_engine import (  # noqa: E402
    _thought_axes, _thought_constraint_vector, _thought_is_complete,
)
from aurora_internal.aurora_constraint_manifold_patched import ConstraintVector  # noqa: E402

FULL = {"existence": 0.175, "temporal": 0.045, "energy": 0.03, "boundary": 0.105, "agency": 0.06}


def _r(axes, killed=False):
    return SimpleNamespace(adjusted_axes=dict(axes), thought_killed=killed, coherence=0.8)


# ---- what makes a Thought complete -----------------------------------------------------------

def test_a_thought_with_every_axis_active_is_complete():
    assert _thought_is_complete(_r(FULL))


@pytest.mark.parametrize("axis", list(FULL))
def test_partial_convergence_is_not_thought(axis):
    assert not _thought_is_complete(_r({**FULL, axis: 0.0}))


def test_a_killed_thought_is_not_complete():
    assert not _thought_is_complete(_r(FULL, killed=True))


@pytest.mark.parametrize("axes", [{}, None, {"unrelated": 1.0}, {"existence": 0.2}])
def test_an_assembly_that_does_not_carry_all_five_is_not_complete(axes):
    assert not _thought_is_complete(_r(axes or {}))


def test_short_axis_names_work_too():
    assert _thought_is_complete(_r({"X": 0.2, "T": 0.1, "N": 0.1, "B": 0.1, "A": 0.1}))


# ---- the deposit's geometry is the thought's own ---------------------------------------------

LEGACY = ConstraintVector(X=1.0, T=0.0, N=0.0, B=0.5, A=0.4)


def test_the_deposit_is_the_thoughts_own_constraint_position_relative_to_its_strongest_axis():
    v = _thought_constraint_vector(ConstraintVector, FULL, LEGACY)
    assert v.X == 1.0, "the most-loaded axis is 1.0"
    assert v.B == pytest.approx(0.105 / 0.175) and v.T == pytest.approx(0.045 / 0.175)
    assert v.A == pytest.approx(0.06 / 0.175)


def test_two_different_thoughts_deposit_at_different_geometry():
    a = _thought_constraint_vector(ConstraintVector, FULL, LEGACY)
    b = _thought_constraint_vector(ConstraintVector, {**FULL, "boundary": 0.3, "existence": 0.05}, LEGACY)
    assert (a.X, a.B) != (b.X, b.B) and b.B == 1.0


def test_it_is_not_the_old_constants():
    v = _thought_constraint_vector(ConstraintVector, FULL, LEGACY)
    assert (v.B, v.A) != (0.5, 0.4)


def test_an_inactive_axis_stays_zero_so_it_cannot_reach_that_stratum():
    v = _thought_constraint_vector(ConstraintVector, {**FULL, "agency": 0.0}, LEGACY)
    assert v.A == 0.0


def test_x_stays_admissible():
    v = _thought_constraint_vector(ConstraintVector, {**FULL, "existence": 0.0}, LEGACY)
    assert v.X > 0.0


@pytest.mark.parametrize("axes", [{}, None, {"unrelated": 1.0}, {"existence": 0.0}])
def test_with_no_axes_the_callers_vector_is_used(axes):
    assert _thought_constraint_vector(ConstraintVector, axes, LEGACY) is LEGACY


# ---- ordering and wiring --------------------------------------------------------------------

def test_the_discharge_follows_the_agency_fill_so_the_thought_is_judged_complete():
    src = open(os.path.join(REPO_ROOT, "aurora_consciousness_engine.py"), encoding="utf-8").read()
    fill = src.index("fill_assembly_axes_from_sender(result.adjusted_axes")
    discharge = src.index("if _thought_is_complete(result):")
    snapshot = src.index("result = self._attach_dual_strata_snapshot(")
    assert fill < discharge < snapshot


def test_a_completed_thought_discharges_the_field_with_its_coherence():
    src = open(os.path.join(REPO_ROOT, "aurora_consciousness_engine.py"), encoding="utf-8").read()
    i = src.index("if _thought_is_complete(result):")
    assert 'self.reset_pressure_topology({"resolved_accuracy": float(result.coherence or 0.0)})' in src[i:i + 200]

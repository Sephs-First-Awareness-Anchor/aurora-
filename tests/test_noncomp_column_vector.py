"""Tests for the D2/625-cell independent-column follow-up:
aurora.py's _derive_noncomp_column_vector and its wiring into the
turn-pipeline SediMemory deposit.

Context: the 625-cell redesign (PR #223, aurora_sedimemory.py) built the
real 625-cell NCStrainFilter machinery but every real ingestion call site
left col_constraint_vector at its default None (an explicit diagonal pin,
never a fabricated relationship) because no non-arbitrary independent
column evidence existed. This closes that gap for the turn-pipeline's own
deposit (the one always-live ingestion path) using evidence that was
already being computed and simply discarded: state.noncomp_input_state,
set earlier in the same turn by _apply_noncomp_input_guidance calling
ReflexiveInterpreter.interpret() -- a subsystem structurally disjoint from
the deposit's own row vector (DimensionalSystems.get_constraint_aggregate,
a DPS crystal-signature mean). Both describe the same turn (the invariant)
through independently-computed mechanisms.
"""
from __future__ import annotations

import os
import sys
from types import SimpleNamespace

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import aurora as A  # noqa: E402
from aurora_crystal_ingestion import _AXIS_CV  # noqa: E402
from aurora_internal.aurora_constraint_manifold_patched import ConstraintVector  # noqa: E402


def test_returns_none_when_no_noncomp_state_attribute():
    assert A._derive_noncomp_column_vector(SimpleNamespace()) is None


def test_returns_none_when_noncomp_state_empty():
    assert A._derive_noncomp_column_vector(SimpleNamespace(noncomp_input_state={})) is None


def test_returns_none_when_noncomp_state_none():
    assert A._derive_noncomp_column_vector(SimpleNamespace(noncomp_input_state=None)) is None


def test_returns_none_for_unrecognized_constraint_value():
    state = SimpleNamespace(noncomp_input_state={"constraint": "not-an-axis"})
    assert A._derive_noncomp_column_vector(state) is None


def test_real_axis_produces_the_canonical_axis_vector_for_all_five_axes():
    for axis, expected in _AXIS_CV.items():
        state = SimpleNamespace(noncomp_input_state={"constraint": axis, "dimension": "OPERATOR"})
        cv = A._derive_noncomp_column_vector(state)
        assert cv is not None
        got = {"X": cv.X, "T": cv.T, "N": cv.N, "B": cv.B, "A": cv.A}
        assert got == expected, f"axis {axis}: {got} != {expected}"


def test_constraint_value_is_case_insensitive():
    state = SimpleNamespace(noncomp_input_state={"constraint": "b"})
    cv = A._derive_noncomp_column_vector(state)
    assert cv is not None
    assert (cv.X, cv.T, cv.N, cv.B, cv.A) == tuple(_AXIS_CV["B"][k] for k in "XTNBA")


def test_turn_pipeline_actually_wires_the_column_vector_into_ingest_event():
    """Source-level proof (same pattern as the integrity report's Repair-1
    test) that the deposit call site was not left calling the helper
    without ever passing its result through -- a future edit could
    otherwise silently compute _col_cv and drop it on the floor."""
    with open(os.path.join(REPO_ROOT, "aurora.py"), "r", encoding="utf-8") as f:
        src = f.read()
    assert "_col_cv = _derive_noncomp_column_vector(state)" in src
    assert "col_constraint_vector=_col_cv" in src


def test_wired_independent_evidence_produces_real_off_diagonal_fragments():
    """End-to-end through the real, unmodified NCStrainFilter: a row vector
    shaped like a genuine DPS crystal-aggregate (not matching any _AXIS_CV
    preset) paired with a column vector built the same way the turn
    pipeline now builds it, produces real off-diagonal (row != col) resonant
    cells -- the machinery the 625-cell PR built is genuinely reachable now,
    not just theoretically capable."""
    import aurora_sedimemory as sm

    row_cv = sm.ConstraintVector(X=0.62, T=0.18, N=0.41, B=0.27, A=0.09)  # arbitrary, non-preset shape
    state = SimpleNamespace(noncomp_input_state={"constraint": "B", "dimension": "OPERATOR"})
    col_cv_raw = A._derive_noncomp_column_vector(state)
    col_cv = sm.ConstraintVector(X=col_cv_raw.X, T=col_cv_raw.T, N=col_cv_raw.N, B=col_cv_raw.B, A=col_cv_raw.A)

    f = sm.NCStrainFilter()
    event = sm.MemoryEvent.create(
        content={"text": "real turn-pipeline-shaped test"},
        constraint_vector=row_cv,
        col_constraint_vector=col_cv,
    )
    frags = f.strain(event)
    assert frags, "expected at least one resonant cell"
    off_diagonal = [
        fr for fr in frags.values()
        if (fr.constraint, fr.dimension) != (fr.col_constraint, fr.col_dimension)
    ]
    assert off_diagonal, (
        "expected genuine off-diagonal (row != col) fragments once independent "
        "column evidence is supplied via the real turn-pipeline mechanism"
    )


def test_no_noncomp_classification_keeps_the_existing_diagonal_pin():
    """When ReflexiveInterpreter never ran for this turn (or the frame
    wasn't matched), the deposit must keep behaving exactly as every real
    ingestion path did before this change: col_constraint_vector=None,
    diagonal-only, zero behavior change."""
    import aurora_sedimemory as sm

    row_cv = sm.ConstraintVector(X=0.62, T=0.18, N=0.41, B=0.27, A=0.09)
    state = SimpleNamespace(noncomp_input_state={})
    col_cv = A._derive_noncomp_column_vector(state)
    assert col_cv is None

    f = sm.NCStrainFilter()
    event = sm.MemoryEvent.create(
        content={"text": "no noncomp classification this turn"},
        constraint_vector=row_cv,
        col_constraint_vector=col_cv,
    )
    frags = f.strain(event)
    assert frags
    assert all((fr.constraint, fr.dimension) == (fr.col_constraint, fr.col_dimension) for fr in frags.values())

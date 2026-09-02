"""Regression tests for item #6 of the Aurora Representational Conservation
and Native Computational Utilization Repair Directive: stop recomputing
depth_score, consume the already-computed slot value.

Two independent recomputations of the same quantity were found and fixed:

  A. aurora_constraint_manifold_compiler.py's _evo_grade() already computed
     depth = (_depth(sub_law_c) + _depth(col_law_c)) / 2.0 internally, used
     it, and discarded it -- compile_noncomp_manifold()'s one call site
     immediately recomputed the identical expression one line below to
     build the persisted depth_score field. _evo_grade() now returns
     (grade, depth) so the caller reuses the value it already paid for.
     Verified byte-identical compiled output across 4 real NCs (different
     axes, diagonal and non-diagonal) before/after this change.

  B. aurora_reflexive_interpreter.py's interpret() hand-recomputed a noncomp's
     anchor-slot depth_score via a locally-copied SHIFT_COST table and a
     hardcoded 150.0, even though the manifold (m) was already open in the
     same scope and NoncompManifold.get_anchor() already returns that exact
     slot with its depth_score pre-computed. interpret() now reads
     m.get_anchor().depth_score directly.
"""
from __future__ import annotations

import os
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from aurora_constraint_manifold_compiler import _evo_grade, _depth, SHIFT_COST
from aurora_reflexive_interpreter import ReflexiveInterpreter
from aurora_manifold_directory_reader import ManifoldDirectory

MANIFOLD_DIR = os.path.join(REPO_ROOT, "aurora_manifold_directory")


def test_evo_grade_returns_grade_and_depth_tuple():
    """Finding A, direct: _evo_grade() now returns (grade, depth) rather
    than a bare float, and depth matches the mean normalised shift cost
    for the given sub/col law_c pair -- the same value the caller's own
    depth_score field is built from."""
    result = _evo_grade("T", "OPERATOR", "N", "COST", "T", "OPERATOR", "X")
    assert isinstance(result, tuple) and len(result) == 2
    grade, depth = result
    assert isinstance(grade, float)
    assert 0.0 <= grade <= 1.0
    expected_depth = (_depth("T") + _depth("N")) / 2.0
    assert depth == expected_depth


def test_evo_grade_depth_matches_anchor_case():
    """The anchor case (sub == col == nc's own law_c) reduces depth to a
    single _depth() call -- confirms the tuple's depth field behaves
    correctly at the exact point ReflexiveInterpreter's fix (Finding B)
    relies on."""
    _, depth = _evo_grade("A", "OPERATOR", "A", "OPERATOR", "A", "OPERATOR", "A")
    assert depth == _depth("A")


def test_compiled_manifold_depth_score_matches_evo_grade_depth():
    """Cross-check against real, on-disk compiled data: a real slot's
    persisted depth_score must equal round(_evo_grade(...)'s depth, 4) for
    the same sub/col law_c pair -- proves the compiler's two computations
    (now one) never diverged."""
    directory = ManifoldDirectory(MANIFOLD_DIR)
    with directory.open("Temporal_Operator_of_Existence") as m:
        slot = m.get_anchor()
        assert slot is not None
        _, depth = _evo_grade(
            slot.sub_law_c, slot.sub_law_d, slot.col_law_c, slot.col_law_d,
            m.nc_law_c, m.nc_dim, m.nc_target,
        )
        assert slot.depth_score == round(depth, 4)


def test_interpret_depth_score_matches_anchor_slot():
    """Finding B, direct: for a real NC where idx_e resolves, interpret()'s
    resulting depth_score must equal that noncomp's own anchor slot's
    depth_score, read via the same directory this ReflexiveInterpreter
    holds -- proof the live per-turn value now comes from the persisted
    slot rather than a hand-rolled recomputation."""
    directory = ManifoldDirectory(MANIFOLD_DIR)
    state_dir = tempfile.mkdtemp(prefix="aurora_depth_score_reuse_")
    ri = ReflexiveInterpreter(directory=directory, state_dir=state_dir)

    state = ri.interpret("time keeps slipping away from me")
    assert state is not None

    idx_e = directory.get_index_entry(state.nc_name) if state.nc_name else None
    if idx_e is not None:
        with directory.open(state.nc_name) as m:
            anchor = m.get_anchor()
            assert anchor is not None
            basis = state.noncomp_state.get("basis") or {}
            assert basis.get("depth_score") == round(anchor.depth_score, 6)


def test_interpret_runs_cleanly_on_real_varied_input():
    """Real-boot-adjacent smoke test: the new depth_score read path must
    not crash on real, varied live input, and must always produce a sane
    float in [0, 1]."""
    directory = ManifoldDirectory(MANIFOLD_DIR)
    state_dir = tempfile.mkdtemp(prefix="aurora_depth_score_reuse_smoke_")
    ri = ReflexiveInterpreter(directory=directory, state_dir=state_dir)

    for expression in (
        "I need to protect my boundaries here",
        "existence itself feels uncertain right now",
        "time keeps slipping away from me",
        "I don't have the energy for this today",
        "I feel torn between two things I care about",
    ):
        state = ri.interpret(expression)
        assert state is not None
        basis = state.noncomp_state.get("basis") or {}
        depth_score = basis.get("depth_score")
        assert depth_score is not None
        assert 0.0 <= depth_score <= 1.0

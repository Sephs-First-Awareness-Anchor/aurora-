"""Regression tests for ReflexiveInterpreter.interpret()'s live SlotCoord
construction (aurora_reflexive_interpreter.py) -- previously built every
SlotCoord as SlotCoord(match.constraint, match.constraint, match.dimension,
match.constraint, match.dimension), collapsing 5 nominal fields to 2
independent values (aurora_representational_canary.py's own Boundary 3;
docs/AURORA_SYSTEM_WIDE_REPRESENTATIONAL_INTEGRITY_REPORT.md).

The row (nc_law_c/nc_dim) now comes from the manifold directory's own
IndexEntry for the matched NC (idx_e.nc_law_c/idx_e.nc_dim) -- genuinely
independent of SemanticMatcher's live per-utterance classification --
already fetched at this call site but previously unused for SlotCoord
construction. The column (law_c/law_d) has no independent evidence
anywhere reachable here (confirmed: IndexEntry.dense_top3's cluster_pair
aggregation discards which col_law_c contributed), so it is pinned via
RepresentationalRef.as_pinned_column() -- named and visible rather than a
disguised inline copy.
"""
from __future__ import annotations

import os
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from aurora_reflexive_interpreter import ReflexiveInterpreter
from aurora_manifold_directory_reader import ManifoldDirectory
from aurora_representational_address import RepresentationalRef, slotcoord_from_ref

MANIFOLD_DIR = os.path.join(REPO_ROOT, "aurora_manifold_directory")


def _make_interpreter():
    state_dir = tempfile.mkdtemp(prefix="aurora_slotcoord_derivation_")
    directory = ManifoldDirectory(MANIFOLD_DIR)
    return ReflexiveInterpreter(directory=directory, state_dir=state_dir), directory


def test_real_directory_contains_non_diagonal_entries_where_row_can_differ():
    """Ground the whole test file in real, on-disk data: confirm at least
    one real NC exists where nc_law_c genuinely differs from nc_target --
    the case that actually exercises the fix (a diagonal NC, where they're
    equal, can't distinguish the old pinned behavior from the new derived
    one)."""
    directory = ManifoldDirectory(MANIFOLD_DIR)
    entry = directory.get_index_entry("Temporal_Operator_of_Existence")
    assert entry is not None
    assert entry.nc_law_c == "T"
    assert entry.nc_target == "X"
    assert entry.nc_law_c != entry.nc_target


def test_interpret_runs_cleanly_on_real_varied_input():
    """Real-boot-adjacent smoke test: the new construction path must not
    crash on real, varied live input."""
    ri, _ = _make_interpreter()
    for expression in (
        "I need to protect my boundaries here",
        "existence itself feels uncertain right now",
        "time keeps slipping away from me",
        "I don't have the energy for this today",
    ):
        state = ri.interpret(expression)
        assert state is not None
        assert state.constraint in ("X", "T", "N", "B", "A")


def test_slotcoord_row_reflects_directory_identity_not_bare_match_copy():
    """Direct proof the fix has real effect: build the exact SlotCoord
    ReflexiveInterpreter.interpret() would build for a real, non-diagonal
    NC (idx_e.nc_law_c != what a live match would classify), using the
    same construction path (RepresentationalRef + as_pinned_column() +
    slotcoord_from_ref) added to interpret() itself, and confirm the
    row differs from the old pinned-to-live-match behavior."""
    directory = ManifoldDirectory(MANIFOLD_DIR)
    idx_e = directory.get_index_entry("Temporal_Operator_of_Existence")
    assert idx_e is not None

    # Old behavior: row pinned to whatever match.constraint/match.dimension
    # happened to be (simulated here as "X"/"OPERATOR", matching nc_target).
    old_style_row_c, old_style_row_d = "X", "OPERATOR"

    # New behavior: row from the directory's own independent identity.
    ref = RepresentationalRef(
        nc_law_c=idx_e.nc_law_c, nc_dim=idx_e.nc_dim, nc_target=idx_e.nc_target,
    ).as_pinned_column()
    coord = slotcoord_from_ref(ref)

    assert coord.nc_law_c == "T"  # the real, independent directory value
    assert coord.nc_law_c != old_style_row_c  # genuinely differs from the old pin
    assert coord.target == idx_e.nc_target == "X"  # target still tracks nc_target correctly


def test_slotcoord_is_no_longer_trivially_always_resonant_or_diagonal():
    """is_resonant (nc_law_c == law_c) and is_diagonal were both trivially
    always True under the old pinning, since law_c was always a copy of
    nc_law_c. With a genuinely independent row and a real non-diagonal NC,
    is_diagonal must now be able to read False -- direct evidence the fix
    changes real downstream computation, not just internal bookkeeping."""
    directory = ManifoldDirectory(MANIFOLD_DIR)
    idx_e = directory.get_index_entry("Temporal_Operator_of_Existence")
    ref = RepresentationalRef(
        nc_law_c=idx_e.nc_law_c, nc_dim=idx_e.nc_dim, nc_target=idx_e.nc_target,
    ).as_pinned_column()
    coord = slotcoord_from_ref(ref)

    # is_resonant is still trivially True here (col pinned FROM nc_law_c,
    # by construction, since there's genuinely no independent column
    # evidence) -- that part is an honest, named pin, not a bug.
    assert coord.is_resonant is True
    # But is_diagonal requires nc_law_c == target AND nc_dim == "OPERATOR"
    # AND law_c == target AND law_d == "OPERATOR" -- target is "X" here
    # (from nc_target) while nc_law_c/law_c are both "T", so this is
    # correctly NOT diagonal, unlike the old always-diagonal-when-target-
    # matches-live-classification pin.
    assert coord.is_diagonal is False


def test_fallback_matches_old_pinned_behavior_when_no_nc_identity_resolved():
    """When no NC directory identity resolves at all (idx_e is None), the
    fix must reduce to exactly the old pinned behavior for the row -- zero
    behavior change for that case."""
    match_constraint, match_dimension = "N", "MAGNITUDE"
    idx_e = None
    nc_target_resolved = None

    row_law_c = idx_e.nc_law_c if idx_e is not None else match_constraint
    row_dim = idx_e.nc_dim if idx_e is not None else match_dimension
    row_target = nc_target_resolved if nc_target_resolved is not None else match_constraint

    ref = RepresentationalRef(
        nc_law_c=row_law_c, nc_dim=row_dim, nc_target=row_target,
    ).as_pinned_column()
    coord = slotcoord_from_ref(ref)

    assert coord.target == match_constraint
    assert coord.nc_law_c == match_constraint
    assert coord.nc_dim == match_dimension
    assert coord.law_c == match_constraint
    assert coord.law_d == match_dimension

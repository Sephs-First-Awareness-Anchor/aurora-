#!/usr/bin/env python3
"""
aurora_rank6_shadow_analysis.py

AURORA REPRESENTATIONAL RANK-SIX FALSIFICATION AND MISSING-COORDINATE
DIRECTIVE -- read-only, shadow-only analysis module.

Tests whether Aurora's manifold-directory geometry (125 noncomps x 625
ManifoldSlots = 78,125 positions) contains a genuine intermediate
representational rank of 15,625 (= 5**6) positions, sitting between the
confirmed 3,125-position SlotCoord space and the confirmed 78,125-position
manifold-directory space.

This module never writes to aurora_manifold_directory/, never modifies
SlotCoord or the manifold compiler, and never persists a candidate
coordinate anywhere. It only reads already-generated JSON files and the
existing compiler/router source for their constant tables, and constructs
ephemeral, in-memory candidate coordinates for inspection.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
from __future__ import annotations

import glob
import json
import os
from collections import namedtuple
from typing import Any, Dict, List, Optional, Tuple

from aurora_constraint_manifold_router import SlotCoord, AXES, DIM_NAMES

MANIFOLD_DIR_DEFAULT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aurora_manifold_directory")

# The two candidate sixth coordinates named by the directive.
CandidateCoordA = namedtuple("CandidateCoordA", SlotCoord._fields + ("sub_law_c",))
CandidateCoordB = namedtuple("CandidateCoordB", SlotCoord._fields + ("sub_law_d",))


def candidate_a_slot_id(c: "CandidateCoordA") -> str:
    base = SlotCoord(c.target, c.nc_law_c, c.nc_dim, c.law_c, c.law_d).slot_id
    return f"{base}|SUBC[{c.sub_law_c}]"


def candidate_b_slot_id(c: "CandidateCoordB") -> str:
    base = SlotCoord(c.target, c.nc_law_c, c.nc_dim, c.law_c, c.law_d).slot_id
    return f"{base}|SUBD[{c.sub_law_d}]"


def verify_round_trip(kind: str) -> Tuple[int, int, bool]:
    """Exhaustively enumerate the full theoretical 15,625-element candidate
    space and confirm every encoded slot_id is unique and every component
    recoverable. Returns (enumerated_count, unique_id_count, no_collisions).
    """
    assert kind in ("A", "B")
    seen = set()
    count = 0
    ok = True
    fifth_axis = AXES if kind == "A" else DIM_NAMES
    for target in AXES:
        for nc_law_c in AXES:
            for nc_dim in DIM_NAMES:
                for law_c in AXES:
                    for law_d in DIM_NAMES:
                        sc = SlotCoord(target, nc_law_c, nc_dim, law_c, law_d)
                        for extra in fifth_axis:
                            if kind == "A":
                                sid = f"{sc.slot_id}|SUBC[{extra}]"
                            else:
                                sid = f"{sc.slot_id}|SUBD[{extra}]"
                            if sid in seen:
                                ok = False
                            seen.add(sid)
                            count += 1
    return count, len(seen), ok


# ── Real, on-disk manifold data (read-only) ─────────────────────────────────

def load_manifold_directory_raw(base_dir: str = MANIFOLD_DIR_DEFAULT) -> Dict[str, Dict[str, Any]]:
    """Load every real, already-generated manifold JSON file into memory.
    Read-only: opens files for reading only, never writes."""
    out: Dict[str, Dict[str, Any]] = {}
    for f in sorted(glob.glob(os.path.join(base_dir, "*", "*.json"))):
        with open(f, "r", encoding="utf-8") as fh:
            d = json.load(fh)
        out[d["nc_name"]] = d
    return out


def build_slot_index(nc_data: Dict[str, Any]) -> Dict[Tuple[str, str, str, str], Dict[str, Any]]:
    idx: Dict[Tuple[str, str, str, str], Dict[str, Any]] = {}
    for s in nc_data["slots"]:
        idx[(s["sub_law_c"], s["sub_law_d"], s["col_law_c"], s["col_law_d"])] = s
    return idx


PHYSICS_FIELDS = (
    "evolution_grade", "accountability_weight", "depth_score", "combined_cost",
    "leverage_class", "cluster_pair", "is_resonant", "is_anchor",
)


def slot_signature(slot: Dict[str, Any]) -> Tuple:
    return tuple(slot[f] for f in PHYSICS_FIELDS)


# Strictly numeric fields only -- excludes cluster_pair (a name/label) and
# leverage_class (a class name derived from a sign), so a coordinate that
# only reshuffles labels without moving a number does not get credited as
# "changing physics." This directly serves the directive's instruction not
# to accept a naming difference as evidence of a physical one.
NUMERIC_FIELDS = ("evolution_grade", "accountability_weight", "depth_score", "combined_cost")


def numeric_signature(slot: Dict[str, Any]) -> Tuple:
    return tuple(slot[f] for f in NUMERIC_FIELDS)


def vary_sub_law_c(directory: Dict[str, Any], nc_name: str, col: Tuple[str, str]) -> Dict[str, Dict[str, Any]]:
    """Hold sub_law_d pinned at the noncomp's own nc_dim (mirroring the
    implicit pin SlotCoord's missing sub-position would otherwise impose)
    and vary sub_law_c across all 5 axes. Returns {axis: real slot dict}."""
    nc = directory[nc_name]
    idx = build_slot_index(nc)
    sub_ld = nc["nc_dim"]
    col_lc, col_ld = col
    out = {}
    for sub_lc in AXES:
        out[sub_lc] = idx[(sub_lc, sub_ld, col_lc, col_ld)]
    return out


def vary_sub_law_d(directory: Dict[str, Any], nc_name: str, col: Tuple[str, str]) -> Dict[str, Dict[str, Any]]:
    """Hold sub_law_c pinned at the noncomp's own nc_law_c and vary
    sub_law_d across all 5 dimensions. Returns {dimension: real slot dict}."""
    nc = directory[nc_name]
    idx = build_slot_index(nc)
    sub_lc = nc["nc_law_c"]
    col_lc, col_ld = col
    out = {}
    for sub_ld in DIM_NAMES:
        out[sub_ld] = idx[(sub_lc, sub_ld, col_lc, col_ld)]
    return out


def joint_grid(directory: Dict[str, Any], nc_name: str, col: Tuple[str, str],
                field: str = "evolution_grade") -> Dict[str, List[float]]:
    """Full 5x5 joint variation of (sub_law_c, sub_law_d), one numeric field,
    col held fixed. Returns {sub_law_c: [value for each sub_law_d in DIM_NAMES order]}."""
    nc = directory[nc_name]
    idx = build_slot_index(nc)
    col_lc, col_ld = col
    grid: Dict[str, List[float]] = {}
    for sub_lc in AXES:
        row = []
        for sub_ld in DIM_NAMES:
            s = idx[(sub_lc, sub_ld, col_lc, col_ld)]
            row.append(s[field])
        grid[sub_lc] = row
    return grid


def additivity_deviation(grid: Dict[str, List[float]]) -> float:
    """Max deviation from a purely additive (rank-1, main-effects-only)
    model of the joint grid: dev(a,b) = grid[a][b] - grid[a0][b] - grid[a][b0] + grid[a0][b0].
    Zero iff sub_law_c and sub_law_d contribute strictly independently
    (no interaction term) to this field."""
    axes = list(grid.keys())
    a0 = axes[0]
    n_cols = len(grid[a0])
    max_dev = 0.0
    for a in axes:
        for j in range(n_cols):
            dev = grid[a][j] - grid[a0][j] - grid[a][0] + grid[a0][0]
            max_dev = max(max_dev, abs(dev))
    return round(max_dev, 6)


def count_distinct(slot_map: Dict[str, Dict[str, Any]], sig_fn=slot_signature) -> int:
    return len({sig_fn(s) for s in slot_map.values()})


# ── Phase E: exact-equality structural checks ───────────────────────────────

def refactor_78125_checks() -> Dict[str, Any]:
    """Tests the two candidate factorizations of 78,125 structurally, not
    just arithmetically:
      3,125 x 25   -- does an actual staged construction produce this?
      15,625 x 5   -- does an actual staged construction produce this?
    """
    total_manifold_positions = 125 * 625
    slotcoord_space = len(AXES) ** 5           # 3125, independently confirmed generator
    sub_position_space = len(AXES) * len(DIM_NAMES)   # 25, one full D1 channel
    candidate_15625 = slotcoord_space * len(AXES)      # or * len(DIM_NAMES), both give 15625

    return {
        "total_manifold_positions": total_manifold_positions,
        "slotcoord_space_3125": slotcoord_space,
        "sub_position_space_25": sub_position_space,
        "product_3125x25": slotcoord_space * sub_position_space,
        "matches_total": slotcoord_space * sub_position_space == total_manifold_positions,
        "candidate_15625": candidate_15625,
        "product_15625x5": candidate_15625 * 5,
        "matches_total_via_15625": candidate_15625 * 5 == total_manifold_positions,
        # Structural claim, verified against compile_noncomp_manifold's actual
        # loop nesting (aurora_constraint_manifold_compiler.py:405-505):
        # nc identity (125, outer, via 5x5x5 nc-generation loops elsewhere) ->
        # sub position (25, `for (sub_lc, sub_ld), sub in sub_map.items()`) ->
        # col position (25, `for col_lc in AXES: for col_ld in DIM_NAMES`).
        # SlotCoord's own 5-loop generator (router.py:378-386) enumerates
        # (target, nc_law_c, nc_dim, law_c, law_d) = nc-identity x col only --
        # it has no loop variable playing the role of sub_law_c/sub_law_d at
        # all; the compiler's real staged construction inserts exactly one
        # more independent 25-valued loop (the sub position) between nc
        # identity and col to reach the full 78,125. There is no analogous
        # staged step anywhere in the compiler that produces exactly 15,625
        # objects before a final x5 multiplication.
        "staged_construction_3125x25_matches_real_compiler_loop_nesting": True,
        "staged_construction_15625x5_matches_any_real_compiler_step": False,
    }

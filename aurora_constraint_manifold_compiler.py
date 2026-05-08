#!/usr/bin/env python3
"""
AURORA NONCOMP MANIFOLD COMPILER  (offline, run once)
=======================================================
Module: aurora_constraint_manifold_compiler.py
Layer: Constraint Ontology — Noncomp Individual Manifold Builder

Authors: Sunni (Sir) Morningstar and Cael Devo
Created: April 2026

PURPOSE
-------
Offline compiler. Run once. Never run at Aurora runtime.

Takes each of the 125 constraint-specific noncomps and treats it as
its own mini-constraint, building a full 625-slot manifold for it.

The Meaning Manifold (Boundary_Operator_of_Boundary's 625) is the
geometric field Sunni was designing — dense accountability clusters
where many law interactions converge, sparse underbound regions where
laws don't yet bind, and one diagonal identity anchor at the centre.

MANIFOLD STRUCTURE PER NONCOMP
--------------------------------
Each noncomp is treated as a mini-constraint domain.

Step 1 — 25 sub-positions:
    Apply the 25 global laws (5 constraints × 5 dimensions)
    TO the noncomp's domain.
    Same derivation logic as the constraint layer compiler.

Step 2 — 625 slots:
    Cross those 25 sub-positions × 25 global laws.
    = 625 interaction slots per noncomp.

Step 3 — Geometry:
    Dense cluster regions  = high accountability convergence
    Sparse regions         = underbound / not-yet-bound law space
    Diagonal               = noncomp's pure self-application (identity anchor)

OUTPUT DIRECTORY STRUCTURE
---------------------------
aurora_manifold_directory/
    _index.json          ← always-loaded lightweight map (125 entries)
    X/
        Existential_Operator_of_Existence.json   ← 625 slots
        Existential_Polarity_of_Existence.json
        ...  (25 files for X)
    T/  ...  (25 files)
    N/  ...  (25 files)
    B/
        Boundary_Operator_of_Boundary.json       ← THE MEANING MANIFOLD
        ...  (25 files)
    A/  ...  (25 files)

FILE SIZE (no semantics mode, default):
    ~100KB per noncomp × 125 = ~12MB total — small, fast to read

FILE SIZE (--with-semantics):
    ~380KB per noncomp × 125 = ~47MB total — rich but heavier

USAGE
-----
    # Default (no semantics — for runtime use):
    python3 aurora_constraint_manifold_compiler.py \\
        --semantics aurora_full_noncomp_rich_semantics.json \\
        --output    aurora_manifold_directory

    # With semantics (for inspection / offline analysis):
    python3 aurora_constraint_manifold_compiler.py \\
        --semantics aurora_full_noncomp_rich_semantics.json \\
        --output    aurora_manifold_directory \\
        --with-semantics

    # Single noncomp (for testing):
    python3 aurora_constraint_manifold_compiler.py \\
        --semantics aurora_full_noncomp_rich_semantics.json \\
        --output    aurora_manifold_directory \\
        --only      Boundary_Operator_of_Boundary
"""

from __future__ import annotations

import argparse
import json
import math
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from aurora_constraint_engine import (
    ConstraintVector as _ConstraintVector,
    ExistenceMode as _ExistenceMode,
    GovernorWeights as _GovernorWeights,
    FoundationalContract as _FoundationalContract,
)

_FC = _FoundationalContract()
_AXES_TUPLE = ("X", "T", "N", "B", "A")


class _SigDesc:
    def __init__(self, sig: str):
        u = "".join(dict.fromkeys(c for c in str(sig or "") if c in "XTNBA"))
        self._sig = u
        n = len(u)
        self.tier = "tier0" if n <= 1 else ("tier1" if n == 2 else ("tier2" if n == 3 else ("tier3" if n == 4 else "tier4")))
    def to_dict(self) -> Dict:
        return {"signature": self._sig, "tier": self.tier}


def describe_signature(sig: str) -> _SigDesc:
    return _SigDesc(sig)


def derive_runtime_regime(weights: Dict[str, float], sig: str) -> Dict:
    numeric = {ax: float(weights.get(ax, 0.0) or 0.0) for ax in _AXES_TUPLE}
    dominant = max(numeric, key=numeric.__getitem__) if any(numeric.values()) else "X"
    pressure = [ax for ax in _AXES_TUPLE if numeric.get(ax, 0.0) > 0.0]
    return {"dominant_axis": dominant, "governor_weight": _GovernorWeights.AS_DICT.get(dominant, 0.0), "axes": numeric, "pressure_axes": pressure}


def derive_language_projection(weights: Dict[str, float], _unused) -> Dict:
    return dict(_FC.language_projection(_ExistenceMode.AGENTIC))

# ── Constants ────────────────────────────────────────────────────────────────

AXES:     Tuple[str, ...] = ("X", "T", "N", "B", "A")
DIM_NAMES: Tuple[str, ...] = ("POLARITY", "MAGNITUDE", "OPERATOR", "COST", "DIFFERENCE")

SHIFT_COST: Dict[str, float] = {
    "X": 1.0, "T": 4.0, "N": 10.0, "B": 40.0, "A": 150.0
}
LEVERAGE_SIGN: Dict[str, int] = {
    "X": -1, "T": -1, "N": 0, "B": +1, "A": +1
}
LEVERAGE_LABEL: Dict[int, str] = {-1: "overhead", 0: "neutral", +1: "leverage"}
_MAX_K: float = 150.0

# Constraint full names
CONSTRAINT_NAME: Dict[str, str] = {
    "X": "Existence", "T": "Temporal",
    "N": "Energetic",  "B": "Boundary", "A": "Agency",
}

# Dimension action verbs for semantic composition
DIM_ACTION: Dict[str, str] = {
    "POLARITY":   "orients",
    "MAGNITUDE":  "scales",
    "OPERATOR":   "governs",
    "COST":       "prices",
    "DIFFERENCE": "contrasts",
}
DIM_QUESTION: Dict[str, str] = {
    "POLARITY":   "which way does this lean, and when does it flip?",
    "MAGNITUDE":  "how strongly does this law amplify or suppress this position?",
    "OPERATOR":   "what is the irreducible transformation the law imposes here?",
    "COST":       "what does it cost to activate this position under the law?",
    "DIFFERENCE": "how far does this deviate from its baseline under the law?",
}


# ── Data structures ──────────────────────────────────────────────────────────

@dataclass
class SubPosition:
    """
    One of the 25 sub-positions of a noncomp's own domain.
    Derived by applying NC[law_c][law_d] TO the noncomp as a mini-constraint.
    """
    sub_id:          str      # "SUB:{nc_name}:{law_c}:{law_d}"
    law_c:           str
    law_d:           str
    is_diagonal:     bool     # law_c == nc.law_constraint AND law_d == nc.dimension
    is_self_family:  bool     # law_c == nc.target_constraint
    cluster:         str      # IDENTITY / CROSS_RULE / ORIENTATION / INTENSITY / ECONOMY / CONTRAST
    depth_score:     float
    leverage_class:  str
    name:            str
    semantic:        Optional[str] = None


@dataclass
class ManifoldSlot:
    """One of the 625 slots in a noncomp's individual manifold."""
    slot_id:          str
    # Row: which sub-position
    sub_law_c:        str
    sub_law_d:        str
    sub_cluster:      str
    sub_is_diagonal:  bool
    # Column: which global law
    col_law_c:        str
    col_law_d:        str
    # Derived physics
    is_resonant:      bool     # sub_law_c == col_law_c
    is_anchor:        bool     # sub is diagonal AND col == nc's own operator
    cluster_pair:     str      # "{sub_cluster}:{col_law_d}"
    evolution_grade:  float
    leverage_class:   str      # from col_law_c's sign
    depth_score:      float
    combined_cost:    float
    accountability_weight: float  # how much this slot contributes to dense clusters
    semantic:         Optional[str] = None


# ── Physics helpers ──────────────────────────────────────────────────────────

def _depth(ax: str) -> float:
    return SHIFT_COST.get(ax, 1.0) / _MAX_K

def _evo_grade(
    sub_law_c: str,
    sub_law_d: str,
    col_law_c: str,
    col_law_d: str,
    nc_law_c:  str,
    nc_dim:    str,
    nc_target: str,
) -> float:
    """
    Evolution grade for one manifold slot.

    Factors:
        depth           — mean normalised shift cost
        cross_sub       — sub_law_c differs from nc_target (noncomp's home)
        cross_col       — col_law_c differs from nc_target
        operator_bonus  — col is OPERATOR dimension
        anchor_bonus    — sub is diagonal AND col is the noncomp's own operator
    """
    depth        = (_depth(sub_law_c) + _depth(col_law_c)) / 2.0
    cross_sub    = 1.0 if sub_law_c != nc_target else 0.0
    cross_col    = 1.0 if col_law_c != nc_target else 0.0
    op_bonus     = 0.15 if col_law_d == "OPERATOR" else 0.0
    anchor       = (sub_law_c == nc_law_c and sub_law_d == nc_dim and
                    col_law_c == nc_law_c and col_law_d == nc_dim)
    anchor_bonus = 0.10 if anchor else 0.0
    raw = (
        0.40 * depth +
        0.25 * cross_sub +
        0.20 * cross_col +
        op_bonus + anchor_bonus
    )
    return round(max(0.0, min(1.0, raw)), 4)


def _accountability_weight(
    sub_cluster: str,
    col_law_d:   str,
    is_resonant: bool,
    evo_grade:   float,
) -> float:
    """
    How much this slot contributes to dense accountability clusters
    in the geometric field.

    High accountability = many obligation lines crossing the same point.
    Factors:
        is_resonant:    self-reinforcing — raises weight
        OPERATOR col:   rule-level interaction — raises weight
        IDENTITY sub:   sub is the noncomp's own rule — raises weight
        evo_grade:      deeper = more accountable
    """
    base = evo_grade
    if is_resonant:        base += 0.10
    if col_law_d == "OPERATOR": base += 0.12
    if sub_cluster == "IDENTITY": base += 0.08
    return round(min(1.0, base), 4)


def _sub_cluster(law_c: str, law_d: str, nc_law_c: str, nc_dim: str) -> str:
    is_diag = (law_c == nc_law_c and law_d == nc_dim)
    if is_diag:
        return "IDENTITY"
    if law_d == "OPERATOR":
        return "CROSS_RULE"
    return {
        "POLARITY":   "ORIENTATION",
        "MAGNITUDE":  "INTENSITY",
        "COST":       "ECONOMY",
        "DIFFERENCE": "CONTRAST",
    }.get(law_d, "CROSS_RULE")


# ── Semantic composers ───────────────────────────────────────────────────────

def _sub_name(
    law_c: str, law_d: str,
    nc_name: str, nc_domain: str,
    nc_law_c: str, nc_dim: str,
) -> str:
    """Name for one sub-position."""
    is_diag = (law_c == nc_law_c and law_d == nc_dim)
    if is_diag:
        return f"{nc_name}__Self"
    c_name = CONSTRAINT_NAME.get(law_c, law_c)
    return f"{c_name}_{law_d.title()}_on_{nc_domain.replace(' ', '_')}"


def _sub_semantic(
    law_c: str, law_d: str,
    nc_name: str, nc_semantic: str, nc_domain: str,
    nc_law_c: str, nc_dim: str,
    write_semantics: bool,
) -> Optional[str]:
    if not write_semantics:
        return None
    nc_summary = nc_semantic.split(".")[0].strip() + "."
    is_diag    = (law_c == nc_law_c and law_d == nc_dim)
    c_name     = CONSTRAINT_NAME.get(law_c, law_c)

    if is_diag:
        return (
            f"The identity anchor of {nc_name}'s own field. "
            f"{nc_summary} "
            f"The noncomp's own invariant rule ({nc_dim}) from its own "
            f"constraint ({nc_law_c}) applied to itself: pure self-reference. "
            f"This is the centre of gravity of the {nc_domain} manifold."
        )
    return (
        f"{c_name}'s {law_d.lower()} law {DIM_ACTION.get(law_d, 'acts on')} "
        f"the domain of '{nc_name}'. {nc_summary} "
        f"Asks: {DIM_QUESTION.get(law_d, '')}"
    )


def _slot_semantic(
    sub: SubPosition,
    col_law_c: str, col_law_d: str,
    nc_name: str, nc_domain: str,
    is_resonant: bool, is_anchor: bool,
    write_semantics: bool,
) -> Optional[str]:
    if not write_semantics:
        return None
    c_name = CONSTRAINT_NAME.get(col_law_c, col_law_c)
    if is_anchor:
        return (
            f"The pure geometric anchor of the {nc_domain} manifold. "
            f"The noncomp's own sub-position '{sub.name}' (self-application) "
            f"is governed by its own operator law from {c_name}. "
            f"This is the densest accountability point in the field — "
            f"every obligation line in the manifold traces back here."
        )
    if is_resonant:
        return (
            f"{c_name}'s {col_law_d.lower()} law {DIM_ACTION.get(col_law_d, 'acts on')} "
            f"sub-position '{sub.name}' in a self-reinforcing interaction. "
            f"Same constraint family deepens the field rather than crossing it. "
            f"Asks: {DIM_QUESTION.get(col_law_d, '')}"
        )
    return (
        f"{c_name}'s {col_law_d.lower()} law {DIM_ACTION.get(col_law_d, 'acts on')} "
        f"sub-position '{sub.name}' [{sub.cluster}]. "
        f"Asks: {DIM_QUESTION.get(col_law_d, '')}"
    )


def _lineage_signature(nc_target: str, nc_law_c: str, nc_dim: str) -> str:
    dim_axis = {
        "POLARITY": "A",
        "MAGNITUDE": "B",
        "OPERATOR": "X",
        "COST": "N",
        "DIFFERENCE": "T",
    }.get(nc_dim, "")
    raw = "".join(token for token in (nc_target, nc_law_c, dim_axis) if token in AXES)
    return raw or nc_target


# ── Core compiler ────────────────────────────────────────────────────────────

def compile_noncomp_manifold(
    nc: Dict,
    write_semantics: bool = False,
) -> Dict:
    """
    Compile the full 625-slot manifold for one noncomp.

    nc: one entry from aurora_full_noncomp_rich_semantics.json

    Returns a dict ready to write to JSON.
    Memory: built slot-by-slot, never holds all 625 dicts simultaneously
            before writing. Peak ≈ one slot dict at a time.
    """
    nc_name    = nc["name"]
    nc_law_c   = nc["law_constraint"]
    nc_dim     = nc["dimension"]
    nc_target  = nc["target_constraint"]
    nc_domain  = nc["target_domain"]
    nc_sem     = nc["semantic"]
    nc_cluster = nc["cluster_family"]
    nc_is_diag = nc["is_diagonal"]
    nc_anchor  = nc.get("representational_anchor")
    lineage_signature = _lineage_signature(nc_target, nc_law_c, nc_dim)
    lineage_descriptor = describe_signature(lineage_signature)
    lineage_tier = lineage_descriptor.tier
    base_weights = {axis: 1.0 if axis in lineage_signature else 0.0 for axis in AXES}

    # ── Step 1: build 25 sub-positions ──────────────────────────────────────
    sub_positions: List[Dict] = []
    sub_map: Dict[Tuple[str,str], SubPosition] = {}

    for law_c in AXES:
        for law_d in DIM_NAMES:
            cluster  = _sub_cluster(law_c, law_d, nc_law_c, nc_dim)
            is_diag  = (law_c == nc_law_c and law_d == nc_dim)
            is_self  = (law_c == nc_target)
            depth    = _depth(law_c)
            lev      = LEVERAGE_LABEL[LEVERAGE_SIGN.get(law_c, 0)]
            name     = _sub_name(law_c, law_d, nc_name, nc_domain, nc_law_c, nc_dim)
            sem      = _sub_semantic(
                law_c, law_d, nc_name, nc_sem, nc_domain,
                nc_law_c, nc_dim, write_semantics,
            )
            sub = SubPosition(
                sub_id         = f"SUB:{nc_name}:{law_c}:{law_d}",
                law_c          = law_c,
                law_d          = law_d,
                is_diagonal    = is_diag,
                is_self_family = is_self,
                cluster        = cluster,
                depth_score    = round(depth, 4),
                leverage_class = lev,
                name           = name,
                semantic       = sem,
            )
            sub_map[(law_c, law_d)] = sub
            entry = {
                "sub_id":          sub.sub_id,
                "law_c":           law_c,
                "law_d":           law_d,
                "is_diagonal":     is_diag,
                "is_self_family":  is_self,
                "cluster":         cluster,
                "depth_score":     sub.depth_score,
                "leverage_class":  lev,
                "name":            name,
            }
            if write_semantics and sem:
                entry["semantic"] = sem
            sub_positions.append(entry)

    # ── Step 2: build 625 slots ──────────────────────────────────────────────
    slots: List[Dict] = []

    # Cluster density tracker — for geometric field stats
    cluster_pair_counts: Dict[str, int]   = {}
    accountability_sum:  Dict[str, float] = {}

    for (sub_lc, sub_ld), sub in sub_map.items():
        for col_lc in AXES:
            for col_ld in DIM_NAMES:

                is_resonant = (sub_lc == col_lc)
                is_anchor   = (
                    sub.is_diagonal and
                    col_lc == nc_law_c and
                    col_ld == nc_dim
                )
                cluster_pair = f"{sub.cluster}:{col_ld}"
                evo = _evo_grade(
                    sub_lc, sub_ld, col_lc, col_ld,
                    nc_law_c, nc_dim, nc_target,
                )
                lev          = LEVERAGE_LABEL[LEVERAGE_SIGN.get(col_lc, 0)]
                depth        = round((_depth(sub_lc) + _depth(col_lc)) / 2.0, 4)
                combined_k   = round(SHIFT_COST.get(sub_lc, 1.0) + SHIFT_COST.get(col_lc, 1.0), 2)
                acct_w       = _accountability_weight(sub.cluster, col_ld, is_resonant, evo)

                slot_id = (
                    f"NC_MANIFOLD:{nc_name}:"
                    f"SUB[{sub_lc}:{sub_ld}]x"
                    f"LAW[{col_lc}:{col_ld}]"
                )

                sem = _slot_semantic(
                    sub, col_lc, col_ld,
                    nc_name, nc_domain,
                    is_resonant, is_anchor,
                    write_semantics,
                )

                slot: Dict = {
                    "slot_id":           slot_id,
                    "sub_law_c":         sub_lc,
                    "sub_law_d":         sub_ld,
                    "sub_cluster":       sub.cluster,
                    "sub_is_diagonal":   sub.is_diagonal,
                    "col_law_c":         col_lc,
                    "col_law_d":         col_ld,
                    "is_resonant":       is_resonant,
                    "is_anchor":         is_anchor,
                    "cluster_pair":      cluster_pair,
                    "evolution_grade":   evo,
                    "leverage_class":    lev,
                    "depth_score":       depth,
                    "combined_cost":     combined_k,
                    "accountability_weight": acct_w,
                }
                if write_semantics and sem:
                    slot["semantic"] = sem

                slots.append(slot)

                # accumulate geometry stats
                cluster_pair_counts[cluster_pair] = (
                    cluster_pair_counts.get(cluster_pair, 0) + 1
                )
                accountability_sum[cluster_pair] = (
                    accountability_sum.get(cluster_pair, 0.0) + acct_w
                )

    # ── Geometric field summary ─────────────────────────────────────────────
    # Dense clusters = cluster_pairs with highest mean accountability weight
    dense_clusters = sorted(
        [
            {
                "cluster_pair": cp,
                "slot_count":   cluster_pair_counts[cp],
                "mean_acct":    round(accountability_sum[cp] / cluster_pair_counts[cp], 4),
                "total_acct":   round(accountability_sum[cp], 4),
            }
            for cp in cluster_pair_counts
        ],
        key=lambda x: x["total_acct"],
        reverse=True,
    )
    anchor_slot_id = (
        f"NC_MANIFOLD:{nc_name}:"
        f"SUB[{nc_law_c}:{nc_dim}]x"
        f"LAW[{nc_law_c}:{nc_dim}]"
    )
    top_evo = sorted(slots, key=lambda s: s["evolution_grade"], reverse=True)[:5]

    return {
        "nc_name":           nc_name,
        "nc_law_c":          nc_law_c,
        "nc_dim":            nc_dim,
        "nc_target":         nc_target,
        "lineage_signature": lineage_signature,
        "lineage_tier":      lineage_tier,
        "lineage_description": lineage_descriptor.to_dict(),
        "nc_domain":         nc_domain,
        "nc_cluster":        nc_cluster,
        "nc_is_diagonal":    nc_is_diag,
        "representational_anchor": nc_anchor,
        "nc_semantic_summary": nc_sem.split(".")[0].strip() + ".",
        "with_semantics":    write_semantics,
        "slot_count":        len(slots),
        "sub_position_count": len(sub_positions),
        "anchor_slot_id":    anchor_slot_id,
        "geometry": {
            "dense_clusters":    dense_clusters[:10],
            "sparse_threshold":  0.30,
            "top_evolved_slots": [
                {k: v for k, v in s.items() if k != "semantic"}
                for s in top_evo
            ],
        },
        "runtime_regime": derive_runtime_regime(base_weights, lineage_signature),
        "language_projection": derive_language_projection(base_weights, None),
        "sub_positions": sub_positions,
        "slots":         slots,
    }


# ── Directory compiler ───────────────────────────────────────────────────────

def compile_directory(
    semantics_path: str,
    output_dir:     str,
    write_semantics: bool = False,
    only:           Optional[str] = None,
    verbose:        bool = True,
) -> Dict:
    """
    Compile all 125 noncomp manifolds and write to the output directory.

    Returns the index dict (also written to _index.json).
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    with open(semantics_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    index_entries: List[Dict] = []
    total_compiled = 0
    t0 = time.time()

    for target_ax in AXES:
        axis_dir = out / target_ax
        axis_dir.mkdir(exist_ok=True)
        constraint_data = data["constraints"][target_ax]

        for nc in constraint_data["noncomps"]:
            nc_name = nc["name"]

            if only and nc_name != only:
                continue

            if verbose:
                print(f"  Compiling [{target_ax}] {nc_name} ...", end="", flush=True)

            t1 = time.time()
            manifold = compile_noncomp_manifold(nc, write_semantics=write_semantics)

            # Write manifold JSON
            file_path = axis_dir / f"{nc_name}.json"
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(manifold, f, separators=(",", ":"))   # compact, no indent

            elapsed = round(time.time() - t1, 3)
            file_kb  = round(file_path.stat().st_size / 1024, 1)

            if verbose:
                print(f" {file_kb}KB  ({elapsed}s)")

            # Index entry — lightweight, no slots
            index_entries.append({
                "nc_name":            nc_name,
                "nc_law_c":           nc["law_constraint"],
                "nc_dim":             nc["dimension"],
                "nc_target":          nc["target_constraint"],
                "lineage_signature":  manifold["lineage_signature"],
                "lineage_tier":       manifold["lineage_tier"],
                "nc_domain":          nc["target_domain"],
                "nc_cluster":         nc["cluster_family"],
                "nc_is_diagonal":     nc["is_diagonal"],
                "representational_anchor": nc.get("representational_anchor"),
                "file":               f"{target_ax}/{nc_name}.json",
                "slot_count":         625,
                "anchor_slot_id":     manifold["anchor_slot_id"],
                "with_semantics":     write_semantics,
                "dense_top3": [
                    d["cluster_pair"]
                    for d in manifold["geometry"]["dense_clusters"][:3]
                ],
            })
            total_compiled += 1

    # Write index
    index = {
        "version":          1,
        "total_noncomps":   total_compiled,
        "total_slots":      total_compiled * 625,
        "with_semantics":   write_semantics,
        "axes":             list(AXES),
        "entries":          index_entries,
    }
    index_path = out / "_index.json"
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)

    total_elapsed = round(time.time() - t0, 2)
    total_kb      = round(
        sum(
            (out / e["file"]).stat().st_size
            for e in index_entries
        ) / 1024
    )

    if verbose:
        print(f"\n{'─'*60}")
        print(f"Compiled:    {total_compiled} noncomps")
        print(f"Total slots: {total_compiled * 625:,}")
        print(f"Directory:   {output_dir}/")
        print(f"Index:       _index.json  ({index_path.stat().st_size//1024}KB)")
        print(f"Total size:  {total_kb}KB")
        print(f"Time:        {total_elapsed}s")

    return index


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Aurora noncomp manifold compiler — run once, offline."
    )
    parser.add_argument(
        "--semantics", required=True,
        help="Path to aurora_full_noncomp_rich_semantics.json"
    )
    parser.add_argument(
        "--output", required=True,
        help="Output directory for manifold files"
    )
    parser.add_argument(
        "--with-semantics", action="store_true",
        help="Include full semantic descriptions in slot files (~4× larger)"
    )
    parser.add_argument(
        "--only", default=None,
        help="Compile only this noncomp name (for testing)"
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress per-file output"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("AURORA NONCOMP MANIFOLD COMPILER")
    print("Authors: Sunni (Sir) Morningstar and Cael Devo")
    print("=" * 60)
    print(f"Semantics:      {args.semantics}")
    print(f"Output dir:     {args.output}")
    print(f"With semantics: {args.with_semantics}")
    if args.only:
        print(f"Only:           {args.only}")
    print()

    compile_directory(
        semantics_path  = args.semantics,
        output_dir      = args.output,
        write_semantics = args.with_semantics,
        only            = args.only,
        verbose         = not args.quiet,
    )
    print("\nDone. Directory is ready for aurora_manifold_directory_reader.py")


if __name__ == "__main__":
    main()

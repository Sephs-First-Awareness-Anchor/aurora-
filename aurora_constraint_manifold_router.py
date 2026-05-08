#!/usr/bin/env python3
"""
AURORA CONSTRAINT MANIFOLD ROUTER
====================================
Module: aurora_constraint_manifold_router.py
Layer: Constraint Ontology — Cross-Constraint Signal Routing

Authors: Sunni (Sir) Morningstar and Cael Devo
Created: April 2026

PURPOSE
-------
Routes signals between constraint manifolds without data-dumping the
full 3125-slot field into memory.

The core design principle: LAZY EVERYTHING.
    - Slot semantics are generated on demand, not pre-materialized
    - Routing works off coordinate indices and grade scores only
    - The leverage scalar is consumed as band_position (coarse) + PhaseNudges
      — the scalar itself is never read or stored here
    - Cross-constraint paths are streamed one signal at a time

SIGNAL ROUTING MODEL
---------------------
A RouteSignal carries:
    - source:    (target_manifold, nc_law_c, nc_dim, law_c, law_d)
    - payload:   semantic intent (what this signal is about)
    - strength:  evolution_grade of the source slot [0..1]
    - band_pos:  current BandPosition (INSIDE / LOW / HIGH)

Routing produces a RouteResult:
    - admitted:    bool — did the signal cross the constraint boundary?
    - gate_cost:   how much friction the crossing encountered
    - target_slots: list of (manifold, slot_coords) — where it landed
    - transit_via_N: whether N was used as mediator

PHYSICS OF CROSSING
--------------------
Crossing from constraint C_src to C_dst has a base gate cost derived from:
    1. Leverage class mismatch (overhead→leverage costs more than same-class)
    2. Depth gap (expensive constraints resist incoming signals more)
    3. Band position (LOW → overhead boundaries weaken; HIGH → leverage tightens)

N (Energetic, leverage_sign=0) is the natural transit layer:
    - Overhead (X,T) → N → Leverage (B,A) is the canonical crossing path
    - Direct overhead→leverage crossing carries a friction penalty
    - N→anything and anything→N costs least

EFFICIENCY DESIGN
------------------
    COORDINATE INDEX (always small, always live):
        RouteIndex stores only (constraint, nc_law_c, nc_dim, law_c, law_d,
        evolution_grade, cluster_pair, leverage_class) per slot.
        No semantics. 3125 entries × ~200 bytes = < 1MB.

    LAZY SEMANTIC RESOLUTION:
        Full slot semantics (the long descriptions) are only generated
        when explicitly requested via router.resolve_semantic(coords).
        The compiler's _compose_slot_semantic() is called on demand.

    STREAM ROUTING:
        route_signal() processes one signal at a time.
        No path tables are pre-computed.
        No cross-product of all possible routes is ever built.

    BAND GATE (from aurora_leverage_scalar):
        The router consumes only:
            engine.band_position  → coarse crossing modifier
            nudges[C].flip_threshold_delta → per-constraint gate bias
        The scalar itself never enters this module.

DIVISION OF LABOUR
------------------
    aurora_closure_basis.py                — global 25 channels + 625
    aurora_noncomp_layer_compiler.py       — 125 named noncomps
    aurora_constraint_manifold_compiler.py — per-constraint 625 manifolds
    aurora_leverage_scalar.py              — band position + phase nudges
    aurora_constraint_manifold_router.py   — cross-constraint routing (HERE)
"""

from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import (
    Dict, Generator, Iterable, Iterator,
    List, Optional, Tuple, NamedTuple,
)

@dataclass
class _RouterProfile:
    """Engine-native replacement for ConstraintProfile within this module."""
    X: float; T: float; N: float; B: float; A: float
    genealogy: str = "XTNBA"
    unit_kind: str = "manifold_slot"
    unit_id: str = ""
    operational_role: str = "routing_target"
    phase_state: str = "stable"
    lineage_pressure: float = 0.0

    @classmethod
    def from_coord(cls, coord: "SlotCoord", *, evolution_grade: float = 0.0, phase_state: str = "stable") -> "_RouterProfile":
        gen = _coord_genealogy(coord)
        counts = {ax: gen.count(ax) for ax in ("X","T","N","B","A")}
        total = float(sum(counts.values()) or 1.0)
        return cls(X=counts["X"]/total, T=counts["T"]/total, N=counts["N"]/total,
                   B=counts["B"]/total, A=counts["A"]/total,
                   genealogy=gen, unit_kind="manifold_slot",
                   unit_id=coord.slot_id, operational_role="routing_target",
                   phase_state=str(phase_state), lineage_pressure=float(evolution_grade))

    @classmethod
    def from_dict(cls, d: dict) -> "_RouterProfile":
        return cls(
            X=float(d.get("X_weight", d.get("X", 0.2))),
            T=float(d.get("T_weight", d.get("T", 0.2))),
            N=float(d.get("N_weight", d.get("N", 0.2))),
            B=float(d.get("B_weight", d.get("B", 0.2))),
            A=float(d.get("A_weight", d.get("A", 0.2))),
            genealogy=str(d.get("genealogy", "XTNBA")),
            unit_kind=str(d.get("unit_kind", "manifold_slot")),
            unit_id=str(d.get("unit_id", "")),
            operational_role=str(d.get("operational_role", "routing_target")),
            phase_state=str(d.get("phase_state", "stable")),
            lineage_pressure=float(d.get("lineage_pressure", 0.0)),
        )

    def _weights(self) -> Dict[str, float]:
        return {"X": self.X, "T": self.T, "N": self.N, "B": self.B, "A": self.A}

    def pressure_vector(self) -> Dict[str, float]:
        return self._weights()

    def weighted_signature(self) -> str:
        w = self._weights()
        _AX = ("X","T","N","B","A")
        ordered = [ax for ax in _AX if w.get(ax, 0.0) > 0.0]
        base = "".join(ordered) or "X"
        if ordered:
            dominant = max(ordered, key=lambda ax: w.get(ax, 0.0))
            if len(ordered) == 5 and w.get(dominant, 0.0) >= 0.30:
                return base + dominant
        return base

    def profile_similarity(self, other: "_RouterProfile") -> float:
        a, b = self._weights(), other._weights()
        dot = sum(a[ax]*b[ax] for ax in ("X","T","N","B","A"))
        mag_a = math.sqrt(sum(v*v for v in a.values()))
        mag_b = math.sqrt(sum(v*v for v in b.values()))
        if mag_a < 1e-9 or mag_b < 1e-9:
            return 0.0
        return max(0.0, min(1.0, dot / (mag_a * mag_b)))

    def lineage_affinity(self, other_sig: str) -> float:
        my = set(c for c in self.genealogy if c in "XTNBA")
        ot = set(c for c in (other_sig or "") if c in "XTNBA")
        if not my and not ot:
            return 1.0
        if not my or not ot:
            return 0.0
        return len(my & ot) / len(my | ot)

    def pressure_compatibility(self, pressure: Optional[Dict[str, float]]) -> float:
        if not pressure:
            return 0.5
        w = self._weights()
        p = {ax: float(pressure.get(ax, 0.0) or 0.0) for ax in ("X","T","N","B","A")}
        diff = sum(abs(w[ax] - p[ax]) for ax in ("X","T","N","B","A"))
        return max(0.0, 1.0 - diff / 5.0)

# ---------------------------------------------------------------------------
# Local leverage contract
# ---------------------------------------------------------------------------
# The router only needs band positions and nudge deltas. Importing the full
# leverage engine here can pull a large chunk of the runtime into every router
# import, so this module keeps the dependency boundary lightweight by design.
_LEVERAGE_AVAILABLE = False


class BandPosition:
    INSIDE = "inside"
    LOW = "low"
    HIGH = "high"


_BAND_LOW = -1.05
_BAND_HIGH = 3.40
_MAX_BIAS = 0.063

DIM_NAMES: Tuple[str, ...] = ("POLARITY", "MAGNITUDE", "OPERATOR", "COST", "DIFFERENCE")
_COMPILER_AVAILABLE = True

# Axis constants
AXES: Tuple[str, ...] = ("X", "T", "N", "B", "A")

# Leverage signs (mirrors aurora_leverage_scalar / aurora_noncomp_registry)
LEVERAGE_SIGN: Dict[str, int] = {
    "X": -1, "T": -1, "N": 0, "B": +1, "A": +1
}
LEVERAGE_LABEL: Dict[int, str] = {-1: "overhead", 0: "neutral", +1: "leverage"}

# Shift cost scaling (mirrors aurora_closure_basis)
SHIFT_COST: Dict[str, float] = {
    "X": 1.0, "T": 4.0, "N": 10.0, "B": 40.0, "A": 150.0
}
_MAX_K: float = 150.0

# N is the canonical transit mediator
TRANSIT_AXIS: str = "N"

_AXIS_NAME: Dict[str, str] = {
    "X": "Existence",
    "T": "Temporal",
    "N": "Energetic",
    "B": "Boundary",
    "A": "Agency",
}
_DIMENSION_NOTE: Dict[str, str] = {
    "POLARITY": "tracks directional lean and flip threshold",
    "MAGNITUDE": "tracks scale and intensity",
    "OPERATOR": "tracks the invariant rule being applied",
    "COST": "tracks energetic price and friction",
    "DIFFERENCE": "tracks contrast from baseline or peers",
}

_DIMENSION_TO_AXIS: Dict[str, str] = {
    "POLARITY": "A",
    "MAGNITUDE": "B",
    "OPERATOR": "X",
    "COST": "N",
    "DIFFERENCE": "T",
}


def _compose_slot_semantic_local(coord: "SlotCoord", nc_semantic: str) -> str:
    target_name = _AXIS_NAME.get(coord.target, coord.target)
    nc_name = _AXIS_NAME.get(coord.nc_law_c, coord.nc_law_c)
    law_name = _AXIS_NAME.get(coord.law_c, coord.law_c)
    resonance = "resonant" if coord.is_resonant else "cross-constraint"
    diagonal = "identity-anchor" if coord.is_diagonal else "non-diagonal"
    dim_note = _DIMENSION_NOTE.get(coord.law_d, "tracks manifold interaction")
    return (
        f"{coord.slot_id}\n"
        f"Target manifold: {target_name}\n"
        f"Noncomp law: {nc_name}:{coord.nc_dim}\n"
        f"Global law: {law_name}:{coord.law_d}\n"
        f"Coupling: {resonance}, {diagonal}\n"
        f"Law note: {dim_note}\n"
        f"NC semantic: {nc_semantic}"
    )


def _coord_genealogy(coord: "SlotCoord") -> str:
    tokens = [coord.target, coord.nc_law_c, coord.law_c]
    dim_axis = _DIMENSION_TO_AXIS.get(coord.nc_dim)
    law_axis = _DIMENSION_TO_AXIS.get(coord.law_d)
    if dim_axis:
        tokens.append(dim_axis)
    if law_axis:
        tokens.append(law_axis)
    if coord.is_resonant:
        tokens.append(coord.law_c)
    if coord.is_diagonal:
        tokens.append(coord.target)
    return "".join(token for token in tokens if token in AXES) or coord.target


def _coord_profile(
    coord: "SlotCoord",
    *,
    evolution_grade: float = 0.0,
    phase_state: str = "stable",
) -> _RouterProfile:
    return _RouterProfile.from_coord(coord, evolution_grade=evolution_grade, phase_state=str(phase_state))


# ============================================================================
# SECTION 1 — SLOT COORDINATE (the lightweight handle)
# ============================================================================

class SlotCoord(NamedTuple):
    """
    Lightweight coordinate for one manifold slot.
    This is the only thing routed between manifolds — semantics never travel.

    target:     Constraint manifold (X/T/N/B/A)
    nc_law_c:   Noncomp's law_constraint
    nc_dim:     Noncomp's dimension
    law_c:      Global law channel's constraint
    law_d:      Global law channel's dimension
    """
    target:   str
    nc_law_c: str
    nc_dim:   str
    law_c:    str
    law_d:    str

    @property
    def slot_id(self) -> str:
        return (
            f"MANIFOLD:{self.target}:"
            f"NC[{self.nc_law_c}:{self.nc_dim}]x"
            f"NC[{self.law_c}:{self.law_d}]"
        )

    @property
    def is_diagonal(self) -> bool:
        return (
            self.nc_law_c == self.target and
            self.nc_dim   == "OPERATOR"  and
            self.law_c    == self.target and
            self.law_d    == "OPERATOR"
        )

    @property
    def is_resonant(self) -> bool:
        return self.nc_law_c == self.law_c

    def to_dict(self) -> Dict:
        return {
            "target":   self.target,
            "nc_law_c": self.nc_law_c,
            "nc_dim":   self.nc_dim,
            "law_c":    self.law_c,
            "law_d":    self.law_d,
            "slot_id":  self.slot_id,
        }


# ============================================================================
# SECTION 2 — ROUTE INDEX (the small in-memory structure)
# ============================================================================

@dataclass(frozen=True)
class IndexEntry:
    """
    One row in the RouteIndex — coordinate + physics grades only.
    No semantics. Fits 3125 of these comfortably in memory.
    """
    coord:          SlotCoord
    evolution_grade: float
    cluster_pair:   Tuple[str, str]   # (nc_cluster_family, law_dim)
    leverage_class: str               # overhead / neutral / leverage
    depth_score:    float
    is_diagonal:    bool
    is_resonant:    bool

    @property
    def target(self) -> str:
        return self.coord.target


class RouteIndex:
    """
    Lightweight index over all 3125 manifold slots.

    Built from coordinate enumeration — no compiler call, no semantics.
    Used by the router for fast candidate lookup without loading slot objects.

    Memory: ~3125 entries × ~300 bytes ≈ ~1MB. Always acceptable.
    """

    def __init__(self, nc_cluster_map: Dict[str, Dict[str, str]]) -> None:
        """
        nc_cluster_map: {target → {f"{nc_law_c}:{nc_dim}" → cluster_family}}
        Built from the JSON, not from the compiled manifold objects.
        """
        self._entries: List[IndexEntry] = []
        self._by_target: Dict[str, List[IndexEntry]] = {ax: [] for ax in AXES}
        self._by_cluster_pair: Dict[str, List[IndexEntry]] = {}
        self._diagonals: Dict[str, IndexEntry] = {}

        for target in AXES:
            cluster_row = nc_cluster_map.get(target, {})
            for nc_law_c in AXES:
                for nc_dim in DIM_NAMES:
                    nc_key     = f"{nc_law_c}:{nc_dim}"
                    nc_cluster = cluster_row.get(nc_key, "UNKNOWN")
                    for law_c in AXES:
                        for law_d in DIM_NAMES:
                            coord = SlotCoord(target, nc_law_c, nc_dim, law_c, law_d)

                            # Compute evolution grade inline
                            is_cross_nc  = (nc_law_c != target)
                            is_cross_law = (law_c != target)
                            depth        = (
                                SHIFT_COST.get(nc_law_c, 1.0) / _MAX_K +
                                SHIFT_COST.get(law_c, 1.0) / _MAX_K
                            ) / 2.0
                            op_bonus  = 0.15 if law_d == "OPERATOR" else 0.0
                            diag_b    = 0.10 if coord.is_diagonal  else 0.0
                            evo       = min(1.0, max(0.0,
                                0.40 * depth +
                                0.25 * (1.0 if is_cross_nc  else 0.0) +
                                0.20 * (1.0 if is_cross_law else 0.0) +
                                op_bonus + diag_b
                            ))

                            sign = LEVERAGE_SIGN.get(law_c, 0)
                            lev  = LEVERAGE_LABEL[sign]

                            entry = IndexEntry(
                                coord           = coord,
                                evolution_grade = round(evo, 4),
                                cluster_pair    = (nc_cluster, law_d),
                                leverage_class  = lev,
                                depth_score     = round(depth, 4),
                                is_diagonal     = coord.is_diagonal,
                                is_resonant     = coord.is_resonant,
                            )
                            self._entries.append(entry)
                            self._by_target[target].append(entry)

                            cp_key = f"{nc_cluster}:{law_d}"
                            self._by_cluster_pair.setdefault(cp_key, []).append(entry)

                            if coord.is_diagonal:
                                self._diagonals[target] = entry

    def entries_for(self, target: str) -> List[IndexEntry]:
        return self._by_target.get(target, [])

    def diagonal(self, target: str) -> Optional[IndexEntry]:
        return self._diagonals.get(target)

    def top_evolved(self, target: str, n: int = 10) -> List[IndexEntry]:
        return sorted(
            self._by_target.get(target, []),
            key=lambda e: e.evolution_grade,
            reverse=True,
        )[:n]

    def by_cluster_pair(self, nc_cluster: str, law_d: str) -> List[IndexEntry]:
        return self._by_cluster_pair.get(f"{nc_cluster}:{law_d}", [])

    def stream_entries(
        self,
        target: Optional[str] = None,
        min_evo: float = 0.0,
        leverage_class: Optional[str] = None,
    ) -> Iterator[IndexEntry]:
        """Stream entries without materializing the full list."""
        pool = self._by_target[target] if target else self._entries
        for e in pool:
            if e.evolution_grade >= min_evo:
                if leverage_class is None or e.leverage_class == leverage_class:
                    yield e

    @property
    def total(self) -> int:
        return len(self._entries)


def build_route_index(semantics_path: str) -> RouteIndex:
    """
    Build a RouteIndex from the JSON file — no manifold compilation needed.
    Reads only the cluster_family for each noncomp (minimal data touch).
    """
    with open(semantics_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    nc_cluster_map: Dict[str, Dict[str, str]] = {}
    for target, constraint_data in data["constraints"].items():
        nc_cluster_map[target] = {}
        for nc in constraint_data["noncomps"]:
            key = f"{nc['law_constraint']}:{nc['dimension']}"
            nc_cluster_map[target][key] = nc["cluster_family"]

    return RouteIndex(nc_cluster_map)


# ============================================================================
# SECTION 3 — CROSSING GATE PHYSICS
# ============================================================================

class CrossingGate:
    """
    Computes gate cost and admission for one cross-constraint signal crossing.

    The gate never reads the leverage scalar.
    It consumes only:
        band_pos:  BandPosition.INSIDE / LOW / HIGH
        nudge:     flip_threshold_delta for the target constraint (if available)

    Gate cost is a float in [0, 1]:
        0.0  = free crossing (same constraint, or through N)
        1.0  = fully blocked
    Admission = gate_cost < threshold (threshold is nudge-modulated)
    """

    # Base crossing costs between leverage classes
    # same-class = 0.20, one-step = 0.40, overhead↔leverage direct = 0.70
    _CLASS_COST: Dict[Tuple[str, str], float] = {
        ("overhead",  "overhead"):  0.20,
        ("overhead",  "neutral"):   0.30,
        ("overhead",  "leverage"):  0.70,
        ("neutral",   "overhead"):  0.30,
        ("neutral",   "neutral"):   0.15,
        ("neutral",   "leverage"):  0.30,
        ("leverage",  "overhead"):  0.70,
        ("leverage",  "neutral"):   0.30,
        ("leverage",  "leverage"):  0.20,
    }

    # Band position modifiers — how band state shifts gate friction
    # LOW (overhead dominant) → overhead boundaries weaken, leverage tightens
    # HIGH (leverage dominant) → leverage boundaries weaken, overhead tightens
    _BAND_MOD: Dict[str, Dict[str, float]] = {
        BandPosition.INSIDE: {"overhead": 0.0,  "neutral": 0.0,  "leverage": 0.0},
        BandPosition.LOW:    {"overhead": -0.10, "neutral": 0.0,  "leverage": +0.10},
        BandPosition.HIGH:   {"overhead": +0.10, "neutral": 0.0,  "leverage": -0.10},
    }

    def __init__(
        self,
        band_pos: str = BandPosition.INSIDE,
        nudges: Optional[Dict[str, float]] = None,
        rng: Optional[random.Random] = None,
    ) -> None:
        """
        band_pos: current BandPosition string
        nudges:   {axis → flip_threshold_delta} — from PhaseNudge.apply_to()
                  Only used to modulate the admission threshold, never the scalar.
        rng:      optional seeded RNG for reproducible dither in tests
        """
        self._band_pos = band_pos
        self._nudges   = nudges or {}
        self._rng      = rng or random.Random()

    def gate_cost(
        self,
        src_axis: str,
        dst_axis: str,
        signal_strength: float,
        via_N: bool = False,
    ) -> float:
        """
        Compute the crossing gate cost for src_axis → dst_axis.

        via_N:  if True, the signal passes through N as mediator —
                replaces a direct overhead↔leverage crossing with two
                cheaper steps: src→N and N→dst.

        Returns a cost in [0.0, 1.0]. Lower = easier crossing.
        """
        if src_axis == dst_axis:
            return 0.0                          # same manifold, no cost

        src_class = LEVERAGE_LABEL[LEVERAGE_SIGN.get(src_axis, 0)]
        dst_class = LEVERAGE_LABEL[LEVERAGE_SIGN.get(dst_axis, 0)]

        if via_N:
            # Two-hop: src→N and N→dst
            cost_a = self._CLASS_COST.get((src_class, "neutral"), 0.30)
            cost_b = self._CLASS_COST.get(("neutral", dst_class), 0.30)
            base_cost = (cost_a + cost_b) * 0.6   # discount for N mediation
        else:
            base_cost = self._CLASS_COST.get((src_class, dst_class), 0.50)

        # Band modifier applied to the DESTINATION's leverage class
        band_mod = self._BAND_MOD.get(self._band_pos, {}).get(dst_class, 0.0)

        # Depth penalty: higher-cost destination axes resist incoming signals
        depth_penalty = (SHIFT_COST.get(dst_axis, 1.0) / _MAX_K) * 0.15

        # Signal strength discount: stronger signals punch through more
        strength_discount = signal_strength * 0.20

        raw = base_cost + band_mod + depth_penalty - strength_discount

        # Dithered small noise — mirrors leverage scalar's dither philosophy
        dither = self._rng.gauss(0.0, 0.008)

        return max(0.0, min(1.0, raw + dither))

    def admission_threshold(self, dst_axis: str) -> float:
        """
        The gate threshold for admission to dst_axis.

        Base = 0.60 (signals with gate_cost < 0.60 are admitted).
        Modulated by the PhaseNudge for dst_axis:
            positive nudge → threshold lowers (harder to cross in)
            negative nudge → threshold raises (easier to cross in)
        This mirrors aurora_leverage_scalar's flip_threshold logic.
        """
        base = 0.60
        nudge_delta = self._nudges.get(dst_axis, 0.0)
        # Nudge direction: positive delta = more stable = harder crossing in
        effective = base - nudge_delta * 0.5
        return max(0.10, min(0.90, effective))

    def is_admitted(
        self,
        src_axis: str,
        dst_axis: str,
        signal_strength: float,
        via_N: bool = False,
    ) -> Tuple[bool, float]:
        """
        Returns (admitted: bool, gate_cost: float).
        """
        cost      = self.gate_cost(src_axis, dst_axis, signal_strength, via_N)
        threshold = self.admission_threshold(dst_axis)
        return (cost < threshold), cost

    @staticmethod
    def should_use_N_transit(src_axis: str, dst_axis: str) -> bool:
        """
        Determines whether N (Energetic) should be used as transit mediator.

        True when crossing between overhead and leverage classes directly —
        the physics naturally routes through N in those cases.
        """
        src_class = LEVERAGE_LABEL[LEVERAGE_SIGN.get(src_axis, 0)]
        dst_class = LEVERAGE_LABEL[LEVERAGE_SIGN.get(dst_axis, 0)]
        return (
            (src_class == "overhead" and dst_class == "leverage") or
            (src_class == "leverage" and dst_class == "overhead")
        )


# ============================================================================
# SECTION 4 — ROUTE SIGNAL AND RESULT
# ============================================================================

@dataclass
class RouteSignal:
    """
    A signal to be routed from one manifold slot to target manifold(s).

    source:         SlotCoord of the originating slot
    strength:       evolution_grade of the source slot [0..1]
    intent:         short semantic label (not the full slot description)
    band_pos:       current BandPosition — the ONLY leverage info allowed here
    nudge_deltas:   {axis → flip_threshold_delta} from PhaseNudge objects
    target_axes:    which manifolds to route toward (default: all others)
    min_evo_target: minimum evolution_grade for candidate target slots
    max_targets:    cap on how many target slots to return (prevents flood)
    """
    source:         SlotCoord
    strength:       float
    intent:         str                        = ""
    band_pos:       str                        = BandPosition.INSIDE
    nudge_deltas:   Dict[str, float]           = field(default_factory=dict)
    target_axes:    Optional[List[str]]        = None
    min_evo_target: float                      = 0.30
    max_targets:    int                        = 12
    source_profile: Optional[_RouterProfile] = None
    pressure_vector: Optional[Dict[str, float]] = None
    lineage_signature: str                     = ""

    @property
    def src_axis(self) -> str:
        return self.source.target


@dataclass
class RoutedTarget:
    """One successfully routed target — coordinate + crossing metadata."""
    coord:        SlotCoord
    gate_cost:    float
    via_N:        bool
    evo_grade:    float
    cluster_pair: Tuple[str, str]
    routing_score: float = 0.0
    profile_similarity: float = 0.0
    pressure_compatibility: float = 0.0
    lineage_affinity: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "slot_id":    self.coord.slot_id,
            "gate_cost":  round(self.gate_cost, 4),
            "via_N":      self.via_N,
            "evo_grade":  round(self.evo_grade, 4),
            "cluster_pair": f"{self.cluster_pair[0]}:{self.cluster_pair[1]}",
            "routing_score": round(self.routing_score, 4),
            "profile_similarity": round(self.profile_similarity, 4),
            "pressure_compatibility": round(self.pressure_compatibility, 4),
            "lineage_affinity": round(self.lineage_affinity, 4),
        }


@dataclass
class RouteResult:
    """
    The outcome of routing one RouteSignal.

    admitted:       True if at least one target slot accepted the signal
    blocked_count:  how many candidate targets were blocked by the gate
    targets:        list of RoutedTarget — slots that admitted the signal
    transit_via_N:  whether N mediation was used for any crossing
    band_pos:       the band position at time of routing
    src_coord:      originating slot
    """
    admitted:      bool
    blocked_count: int
    targets:       List[RoutedTarget]
    transit_via_N: bool
    band_pos:      str
    src_coord:     SlotCoord

    def to_dict(self) -> Dict:
        return {
            "admitted":      self.admitted,
            "blocked_count": self.blocked_count,
            "target_count":  len(self.targets),
            "transit_via_N": self.transit_via_N,
            "band_pos":      self.band_pos,
            "src":           self.src_coord.to_dict(),
            "targets":       [t.to_dict() for t in self.targets],
        }


# ============================================================================
# SECTION 5 — MANIFOLD ROUTER
# ============================================================================

class ManifoldRouter:
    """
    Routes signals between constraint manifolds using the RouteIndex.

    Lazy by design:
        - Uses RouteIndex for all lookups (no full ManifoldSlot objects needed)
        - Semantics only resolved when explicitly requested
        - Routing is one-signal-at-a-time streaming

    Band-gated by design:
        - Consumes BandPosition and PhaseNudge deltas
        - Never reads or stores the leverage scalar
        - Gate dithered to prevent gaming

    Usage:
        index  = build_route_index("aurora_full_noncomp_rich_semantics.json")
        router = ManifoldRouter(index)

        # Update band state each tick from LeverageBiasEngine
        router.update_band(engine.band_position, nudge_deltas)

        # Route a signal
        signal = RouteSignal(
            source   = SlotCoord("B", "B", "OPERATOR", "B", "OPERATOR"),
            strength = 0.86,
            intent   = "meaning self-recognition",
        )
        result = router.route_signal(signal)
    """

    def __init__(
        self,
        index: RouteIndex,
        seed: Optional[int] = None,
    ) -> None:
        self._index   = index
        self._rng     = random.Random(seed)
        self._band_pos    = BandPosition.INSIDE
        self._nudge_deltas: Dict[str, float] = {ax: 0.0 for ax in AXES}

    # ------------------------------------------------------------------
    # BAND STATE UPDATE (called each tick from LeverageBiasEngine)
    # ------------------------------------------------------------------

    def update_band(
        self,
        band_pos: str,
        nudge_deltas: Optional[Dict[str, float]] = None,
    ) -> None:
        """
        Update the router's band state.

        Called each tick before routing.
        nudge_deltas: {axis → flip_threshold_delta} from PhaseNudge objects.
        The scalar is never passed — only its coarse derivative.
        """
        self._band_pos    = band_pos
        self._nudge_deltas = nudge_deltas or {ax: 0.0 for ax in AXES}

    # ------------------------------------------------------------------
    # CORE ROUTING
    # ------------------------------------------------------------------

    def route_signal(self, signal: RouteSignal) -> RouteResult:
        """
        Route one signal from its source slot to candidate target slots.

        Streaming candidate lookup → gate evaluation → collect admitted targets.
        No pre-computed path tables. Memory impact: O(max_targets).
        """
        band_pos     = signal.band_pos or self._band_pos
        nudge_deltas = signal.nudge_deltas or self._nudge_deltas
        target_axes  = signal.target_axes or [ax for ax in AXES if ax != signal.src_axis]
        source_profile = self._resolve_source_profile(signal)

        gate = CrossingGate(
            band_pos = band_pos,
            nudges   = nudge_deltas,
            rng      = random.Random(self._rng.randint(0, 2**31)),
        )

        admitted_targets: List[RoutedTarget] = []
        blocked = 0
        used_N  = False

        # Stream candidates — no materialisation of full target set
        for dst_axis in target_axes:
            via_N = CrossingGate.should_use_N_transit(signal.src_axis, dst_axis)
            if via_N:
                used_N = True

            admitted_here = 0
            # Stream index entries for this destination, best-evolved first
            for entry in self._stream_sorted_entries(
                dst_axis,
                source_profile=source_profile,
                signal=signal,
                min_evo   = signal.min_evo_target,
                max_items = signal.max_targets - len(admitted_targets),
            ):
                if len(admitted_targets) >= signal.max_targets:
                    break

                ok, cost = gate.is_admitted(
                    signal.src_axis, dst_axis, signal.strength, via_N
                )
                if ok:
                    metrics = self._score_candidate(entry, source_profile, signal)
                    admitted_targets.append(RoutedTarget(
                        coord        = entry.coord,
                        gate_cost    = cost,
                        via_N        = via_N,
                        evo_grade    = entry.evolution_grade,
                        cluster_pair = entry.cluster_pair,
                        routing_score = metrics["routing_score"],
                        profile_similarity = metrics["profile_similarity"],
                        pressure_compatibility = metrics["pressure_compatibility"],
                        lineage_affinity = metrics["lineage_affinity"],
                    ))
                    admitted_here += 1
                else:
                    blocked += 1

                # Don't flood a single destination
                if admitted_here >= max(1, signal.max_targets // len(target_axes)):
                    break

        return RouteResult(
            admitted      = len(admitted_targets) > 0,
            blocked_count = blocked,
            targets       = sorted(admitted_targets, key=lambda item: item.routing_score, reverse=True),
            transit_via_N = used_N,
            band_pos      = band_pos,
            src_coord     = signal.source,
        )

    def route_from_diagonal(
        self,
        target: str,
        strength: float = 0.80,
        intent: str     = "",
    ) -> RouteResult:
        """
        Convenience: route a signal from a constraint's identity anchor.
        The diagonal slot is the manifold's highest-gravity point.
        """
        diag = self._index.diagonal(target)
        if diag is None:
            raise ValueError(f"No diagonal found for target: {target!r}")
        signal = RouteSignal(
            source   = diag.coord,
            strength = strength,
            intent   = intent or f"{target}-diagonal",
            band_pos = self._band_pos,
            nudge_deltas = self._nudge_deltas,
        )
        return self.route_signal(signal)

    # ------------------------------------------------------------------
    # LAZY SEMANTIC RESOLUTION
    # ------------------------------------------------------------------

    def resolve_semantic(
        self,
        coord: SlotCoord,
        nc_semantic: str,
    ) -> str:
        """
        Lazily generate the full semantic description for one slot.

        nc_semantic: the rich semantic string for the noncomp (from JSON).
                     Caller fetches this on-demand rather than pre-loading all.

        This is the ONLY place where slot semantics are generated.
        The router itself never pre-materialises any semantic strings.
        """
        return _compose_slot_semantic_local(coord, nc_semantic)

    # ------------------------------------------------------------------
    # STREAMING ANALYSIS (no full materialisation)
    # ------------------------------------------------------------------

    def stream_route(
        self,
        signals: Iterable[RouteSignal],
    ) -> Generator[RouteResult, None, None]:
        """
        Route a stream of signals, yielding results one at a time.
        Never holds more than one result in memory at a time.
        """
        for signal in signals:
            yield self.route_signal(signal)

    def stream_top_targets(
        self,
        target: str,
        n: int = 20,
        min_evo: float = 0.50,
    ) -> Generator[IndexEntry, None, None]:
        """
        Stream the top-N highest-evolution entries for a target manifold.
        Does not materialise the full sorted list — uses a partial heap.
        """
        import heapq
        heap: List[Tuple[float, int, IndexEntry]] = []
        counter = 0
        for entry in self._index.stream_entries(target, min_evo=min_evo):
            heapq.heappush(heap, (entry.evolution_grade, counter, entry))
            counter += 1
            if len(heap) > n:
                heapq.heappop(heap)
        for _, _, entry in sorted(heap, key=lambda x: -x[0]):
            yield entry

    # ------------------------------------------------------------------
    # CROSS-MANIFOLD PATTERN DETECTION (streaming, no dumps)
    # ------------------------------------------------------------------

    def find_resonance_bridges(
        self,
        min_evo: float = 0.60,
    ) -> Generator[Tuple[str, str, IndexEntry, IndexEntry], None, None]:
        """
        Find pairs of entries across different manifolds that share the same
        cluster_pair — indicating structural resonance across constraint bounds.

        Yields (axis_a, axis_b, entry_a, entry_b) — streamed, not collected.
        Memory: O(entries per axis) for one axis buffer at a time.
        """
        axis_list = list(AXES)
        for i, ax_a in enumerate(axis_list):
            entries_a = {
                e.cluster_pair: e
                for e in self._index.stream_entries(ax_a, min_evo=min_evo)
            }
            for ax_b in axis_list[i+1:]:
                for entry_b in self._index.stream_entries(ax_b, min_evo=min_evo):
                    match = entries_a.get(entry_b.cluster_pair)
                    if match:
                        yield ax_a, ax_b, match, entry_b

    # ------------------------------------------------------------------
    # INTERNAL HELPERS
    # ------------------------------------------------------------------

    def _stream_sorted_entries(
        self,
        target: str,
        source_profile: _RouterProfile,
        signal: RouteSignal,
        min_evo: float,
        max_items: int,
    ) -> Iterator[IndexEntry]:
        """
        Stream entries for a target sorted by evolution_grade descending.
        Uses partial sort — only touches as many items as needed.
        """
        import heapq
        buf: List[Tuple[float, int, IndexEntry]] = []
        counter = 0
        for entry in self._index.stream_entries(target, min_evo=min_evo):
            # Use counter as tie-breaker so IndexEntry objects are never compared
            metrics = self._score_candidate(entry, source_profile, signal)
            heapq.heappush(buf, (-metrics["routing_score"], counter, entry))
            counter += 1
        yielded = 0
        while buf and yielded < max_items:
            _, _, entry = heapq.heappop(buf)
            yield entry
            yielded += 1

    def _resolve_source_profile(self, signal: RouteSignal) -> _RouterProfile:
        if isinstance(signal.source_profile, _RouterProfile):
            return signal.source_profile
        if isinstance(signal.source_profile, dict):
            try:
                return _RouterProfile.from_dict(signal.source_profile)
            except Exception:
                pass
        phase = getattr(signal.source_profile, "phase_state", "stable") if signal.source_profile else "stable"
        return _coord_profile(
            signal.source,
            evolution_grade=float(signal.strength or 0.0),
            phase_state=str(getattr(phase, "value", phase)),
        )

    def _score_candidate(
        self,
        entry: IndexEntry,
        source_profile: _RouterProfile,
        signal: RouteSignal,
    ) -> Dict[str, float]:
        candidate = _coord_profile(
            entry.coord,
            evolution_grade=float(entry.evolution_grade or 0.0),
            phase_state=source_profile.phase_state,
        )
        profile_similarity = source_profile.profile_similarity(candidate)
        lineage_source = signal.lineage_signature or source_profile.weighted_signature()
        lineage_affinity = candidate.lineage_affinity(lineage_source)
        pressure_payload = signal.pressure_vector or source_profile.pressure_vector()
        pressure_compatibility = candidate.pressure_compatibility(pressure_payload)
        routing_score = (
            0.35 * float(entry.evolution_grade) +
            0.25 * profile_similarity +
            0.20 * pressure_compatibility +
            0.20 * lineage_affinity
        )
        return {
            "routing_score": max(0.0, min(1.0, routing_score)),
            "profile_similarity": profile_similarity,
            "pressure_compatibility": pressure_compatibility,
            "lineage_affinity": lineage_affinity,
        }


# ============================================================================
# SECTION 6 — TICK INTEGRATOR
# ============================================================================

class RouterTick:
    """
    Single-tick integration point between LeverageBiasEngine and ManifoldRouter.

    At each system tick:
        1. LeverageBiasEngine computes nudges from the energy accountant
        2. RouterTick extracts band_pos + nudge_deltas (no scalar)
        3. ManifoldRouter is updated with the coarse band state
        4. Any pending RouteSignals are processed

    This is the cleanest integration pattern — the scalar never crosses
    the module boundary. The router sees only felt physics.
    """

    def __init__(self, router: ManifoldRouter) -> None:
        self._router = router

    def integrate_from_engine(
        self,
        engine_band_pos: str,
        nudge_objects: Optional[Dict] = None,
    ) -> None:
        """
        Update the router from LeverageBiasEngine outputs.

        engine_band_pos: engine.band_position (string, not scalar)
        nudge_objects:   dict of {Constraint → PhaseNudge} from engine.compute_nudges()
                         Converted to {axis_string → delta} here — scalar never touched.
        """
        deltas: Dict[str, float] = {}
        if nudge_objects:
            for constraint, nudge in nudge_objects.items():
                axis = constraint.name if hasattr(constraint, "name") else str(constraint)
                deltas[axis] = nudge.flip_threshold_delta

        self._router.update_band(engine_band_pos, deltas)

    def process_signals(
        self,
        signals: List[RouteSignal],
    ) -> List[RouteResult]:
        """Process a batch of signals this tick. Returns results list."""
        return list(self._router.stream_route(signals))


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import sys

    SEMANTICS_FILE = (
        sys.argv[1] if len(sys.argv) > 1
        else "aurora_full_noncomp_rich_semantics.json"
    )

    print("=" * 72)
    print("AURORA CONSTRAINT MANIFOLD ROUTER")
    print("Authors: Sunni (Sir) Morningstar and Cael Devo")
    print("=" * 72)
    print(f"\nPhysics available:   {_LEVERAGE_AVAILABLE}")
    print(f"Compiler available:  {_COMPILER_AVAILABLE}")

    print(f"\nBuilding route index from: {SEMANTICS_FILE}")
    index  = build_route_index(SEMANTICS_FILE)
    router = ManifoldRouter(index, seed=42)
    print(f"Index built: {index.total} entries ({index.total * 300 // 1024}KB est.)")

    print("\n--- Diagonal Anchors ---")
    for ax in AXES:
        diag = index.diagonal(ax)
        if diag:
            print(
                f"  {ax}  evo={diag.evolution_grade:.4f}"
                f"  cluster_pair={diag.cluster_pair[0]}:{diag.cluster_pair[1]}"
                f"  {diag.coord.slot_id}"
            )

    print("\n--- Band State: INSIDE (default) ---")
    router.update_band(BandPosition.INSIDE)

    print("\n--- Route from B diagonal (Meaning) → all other manifolds ---")
    result = router.route_from_diagonal("B", strength=0.86, intent="meaning self-recognition")
    print(f"  Admitted: {result.admitted}")
    print(f"  Targets:  {len(result.targets)}")
    print(f"  Blocked:  {result.blocked_count}")
    print(f"  Via N:    {result.transit_via_N}")
    print(f"  Band:     {result.band_pos}")
    for t in result.targets[:6]:
        print(
            f"    → {t.coord.slot_id[:60]}"
            f"  cost={t.gate_cost:.3f}  evo={t.evo_grade:.3f}"
            f"  via_N={t.via_N}"
        )

    print("\n--- Crossing gate costs: B → all axes (INSIDE band) ---")
    gate = CrossingGate(band_pos=BandPosition.INSIDE)
    for dst in AXES:
        via_N = CrossingGate.should_use_N_transit("B", dst)
        cost  = gate.gate_cost("B", dst, signal_strength=0.80, via_N=via_N)
        thresh = gate.admission_threshold(dst)
        ok    = cost < thresh
        print(
            f"  B → {dst}  cost={cost:.3f}  threshold={thresh:.3f}"
            f"  {'✓ admitted' if ok else '✗ blocked'}"
            f"  {'(via N)' if via_N else ''}"
        )

    print("\n--- Band state: LOW (overhead dominant) — tightens leverage side ---")
    router.update_band(BandPosition.LOW)
    gate_low = CrossingGate(band_pos=BandPosition.LOW)
    for dst in ["B", "A", "X", "T"]:
        via_N  = CrossingGate.should_use_N_transit("X", dst)
        cost   = gate_low.gate_cost("X", dst, signal_strength=0.60, via_N=via_N)
        thresh = gate_low.admission_threshold(dst)
        print(
            f"  X → {dst}  cost={cost:.3f}  threshold={thresh:.3f}"
            f"  {'✓' if cost < thresh else '✗'}"
        )

    print("\n--- Stream: top 5 evolved entries for A (Agency/Understanding) ---")
    for entry in router.stream_top_targets("A", n=5, min_evo=0.50):
        print(
            f"  {entry.coord.slot_id[:65]}"
            f"  evo={entry.evolution_grade:.4f}"
            f"  {entry.leverage_class}"
        )

    print("\n--- Resonance bridges (B↔A, min_evo=0.75) ---")
    count = 0
    for ax_a, ax_b, e_a, e_b in router.find_resonance_bridges(min_evo=0.75):
        if ax_a in ("B", "A") and ax_b in ("B", "A"):
            print(
                f"  {ax_a}↔{ax_b}  cluster={e_a.cluster_pair[0]}:{e_a.cluster_pair[1]}"
                f"  evo_a={e_a.evolution_grade:.3f}  evo_b={e_b.evolution_grade:.3f}"
            )
            count += 1
            if count >= 6:
                break

    print("\n--- RouterTick integration demo ---")
    tick = RouterTick(router)
    tick.integrate_from_engine(BandPosition.INSIDE)
    batch = [
        RouteSignal(
            source   = SlotCoord("B", "B", "OPERATOR", "A", "OPERATOR"),
            strength = 0.90,
            intent   = "accountability at boundary → agency",
        ),
        RouteSignal(
            source   = SlotCoord("A", "A", "OPERATOR", "B", "OPERATOR"),
            strength = 0.75,
            intent   = "understanding → meaning",
        ),
    ]
    results = tick.process_signals(batch)
    for r in results:
        print(
            f"  {r.src_coord.slot_id[:55]}"
            f"  admitted={r.admitted}  targets={len(r.targets)}"
        )

    print("\nDone.")

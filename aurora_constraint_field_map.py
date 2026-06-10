#!/usr/bin/env python3
"""
AURORA CONSTRAINT FIELD MAP
============================
Module: aurora_constraint_field_map.py
Layer: Between PressureVec (5-axis flat signal) and the 25 NC channels.

PURPOSE
-------
Defines all 31 non-empty subsets of {X, T, N, B, A} as named ConstraintField
objects. Each field represents a pressure configuration that requires ALL of its
constituent axes to be simultaneously active.

This is the power-set layer: rather than asking "which single axis is dominant?"
it asks "which multi-axis combinations are co-pressured right now?" — exposing
field interactions that the flat 5-vector cannot express.

ARCHITECTURE
------------
  PressureVec {X, T, N, B, A}
      ↓  (observer, read-only)
  ConstraintFieldAccumulator
      ↓  update(pv) on each _current_pressure_vec() call
  ConstraintFieldState — active_fields, field_pressures, dominant_field
      ↓  (read-only interface for crystal convergence, predictive frame)
  get_dominant_field(), get_active_fields()

FIELD ACTIVATION LAW
--------------------
A field activates when ALL of its axes carry pressure above threshold.
Field pressure = min(pv.axis for axis in subset) — this is the weakest-link
measure: the field can only be as strong as its least-pressured constituent.

DECAY
-----
reset_cycle() decays non-dominant fields each pass. The dominant field retains
its full accumulated pressure. All others decay by DECAY_FACTOR (default 0.7).

DEPTH NOTATION
--------------
  Depth 1: single-axis fields      {X}, {T}, {N}, {B}, {A}
  Depth 2: pair fields             {X,T}, {X,N}, …  (10 fields)
  Depth 3: triple fields           {X,T,N}, …       (10 fields)
  Depth 4: quad fields             {X,T,N,B}, …     (5 fields)
  Depth 5: full field              {X,T,N,B,A}      (1 field)
  Total: 5 + 10 + 10 + 5 + 1 = 31

AUTHORS
-------
Sunni (Sir) Morningstar and Cael Devo
Created: May 2026
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional, Tuple

# ---------------------------------------------------------------------------
# CANONICAL AXES
# ---------------------------------------------------------------------------

AXES: Tuple[str, ...] = ("X", "T", "N", "B", "A")
_AXIS_SET: FrozenSet[str] = frozenset(AXES)

# ---------------------------------------------------------------------------
# FIELD DEFINITIONS — all 31 non-empty subsets
# ---------------------------------------------------------------------------

# Human-readable names for each depth class
_DEPTH_LABELS: Dict[int, str] = {
    1: "",           # single axis: use axis letter directly
    2: "+",          # pair: "X+T"
    3: "+",          # triple: "X+T+N"
    4: "+",          # quad: "X+T+N+B"
    5: "XTNBA",      # full field has its own canonical name
}


def _field_name(axes_subset: Tuple[str, ...]) -> str:
    """Human-readable label for a field (e.g. 'X', 'X+T', 'X+T+N', 'XTNBA')."""
    depth = len(axes_subset)
    if depth == 5:
        return "XTNBA"
    if depth == 1:
        return axes_subset[0]
    return "+".join(axes_subset)


@dataclass(frozen=True)
class ConstraintField:
    """
    A named pressure field — one non-empty subset of {X, T, N, B, A}.

    Attributes
    ----------
    axes       : frozenset of axis symbols in this field
    name       : human-readable label (e.g. "X+T", "X+T+N", "XTNBA")
    field_id   : stable integer 1–31 (assigned by canonical generation order)
    depth      : cardinality of the subset (1 through 5)
    """
    axes:     FrozenSet[str]
    name:     str
    field_id: int
    depth:    int

    def __repr__(self) -> str:
        return f"<ConstraintField {self.field_id:02d} '{self.name}' depth={self.depth}>"

    def is_single_axis(self) -> bool:
        return self.depth == 1

    def is_full_field(self) -> bool:
        return self.depth == 5

    def contains(self, axis: str) -> bool:
        """True if this field includes the given axis."""
        return axis in self.axes

    def shares_axes_with(self, other: "ConstraintField") -> FrozenSet[str]:
        """Return the set of axes shared with another field."""
        return self.axes & other.axes


def _generate_all_fields() -> Tuple[List[ConstraintField], Dict[FrozenSet[str], ConstraintField]]:
    """
    Generate all 31 non-empty subsets of AXES in canonical order.

    Ordering: depth 1 → depth 5, within each depth by tuple index
    (i.e. the order itertools.combinations produces them from AXES).
    field_id runs 1–31.
    """
    fields: List[ConstraintField] = []
    by_axes: Dict[FrozenSet[str], ConstraintField] = {}
    fid = 1
    for depth in range(1, 6):
        for combo in itertools.combinations(AXES, depth):
            f = ConstraintField(
                axes=frozenset(combo),
                name=_field_name(combo),
                field_id=fid,
                depth=depth,
            )
            fields.append(f)
            by_axes[f.axes] = f
            fid += 1
    assert len(fields) == 31, f"Expected 31 fields, got {len(fields)}"
    return fields, by_axes


# Module-level singletons — stable for the process lifetime
ALL_FIELDS: List[ConstraintField] = []
FIELD_BY_AXES: Dict[FrozenSet[str], ConstraintField] = {}
FIELD_BY_ID: Dict[int, ConstraintField] = {}

_ALL_FIELDS, _FIELD_BY_AXES = _generate_all_fields()
ALL_FIELDS = _ALL_FIELDS
FIELD_BY_AXES = _FIELD_BY_AXES
FIELD_BY_ID = {f.field_id: f for f in ALL_FIELDS}


def get_field(axes: FrozenSet[str]) -> Optional[ConstraintField]:
    """Look up a field by its frozenset of axes. Returns None if not found."""
    return FIELD_BY_AXES.get(frozenset(axes))


def get_field_by_id(field_id: int) -> Optional[ConstraintField]:
    """Look up a field by its stable integer ID (1–31)."""
    return FIELD_BY_ID.get(field_id)


def fields_at_depth(depth: int) -> List[ConstraintField]:
    """Return all fields of a given cardinality (1–5)."""
    return [f for f in ALL_FIELDS if f.depth == depth]


# ---------------------------------------------------------------------------
# CONSTRAINT FIELD STATE
# ---------------------------------------------------------------------------

#: Minimum accumulated pressure for a field to be considered "active"
DEFAULT_ACTIVATION_THRESHOLD: float = 0.05


@dataclass
class ConstraintFieldState:
    """
    Snapshot of the pressure field layer at a given moment.

    Attributes
    ----------
    active_fields    : fields currently above the activation threshold
    field_pressures  : dict[field_id → float] — accumulated pressure per field
    dominant_field   : the highest-pressure active field (None if all silent)
    """
    active_fields:   List[ConstraintField]
    field_pressures: Dict[int, float]
    dominant_field:  Optional[ConstraintField]

    def pressure_of(self, axes: FrozenSet[str]) -> float:
        """Convenience: pressure for the field defined by a frozenset of axes."""
        f = get_field(axes)
        if f is None:
            return 0.0
        return self.field_pressures.get(f.field_id, 0.0)

    def is_active(self, axes: FrozenSet[str]) -> bool:
        """True if the field for this axis subset is currently active."""
        f = get_field(axes)
        if f is None:
            return False
        return f in self.active_fields

    def top_n(self, n: int = 5) -> List[Tuple[ConstraintField, float]]:
        """Return the n highest-pressure fields (active or not), sorted descending."""
        scored = [
            (f, self.field_pressures.get(f.field_id, 0.0))
            for f in ALL_FIELDS
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:n]

    def summary(self) -> Dict:
        """Compact dict for logging / status endpoints."""
        return {
            "dominant_field": self.dominant_field.name if self.dominant_field else None,
            "dominant_field_id": self.dominant_field.field_id if self.dominant_field else None,
            "dominant_depth": self.dominant_field.depth if self.dominant_field else None,
            "active_count": len(self.active_fields),
            "active_fields": [
                {"id": f.field_id, "name": f.name, "depth": f.depth,
                 "pressure": round(self.field_pressures.get(f.field_id, 0.0), 4)}
                for f in self.active_fields
            ],
        }


# ---------------------------------------------------------------------------
# CONSTRAINT FIELD ACCUMULATOR
# ---------------------------------------------------------------------------

#: Factor by which non-dominant fields decay on reset_cycle()
DECAY_FACTOR: float = 0.70


class ConstraintFieldAccumulator:
    """
    Observer layer that receives PressureVec updates from DimensionalSystems
    and accumulates pressure per field across passes.

    DESIGN CONTRACT
    ---------------
    - Read-only relative to the governor: the accumulator never writes back to
      DimensionalSystems or RuntimeConstraintGovernor.
    - Activation law: field pressure = min(pv.<axis> for axis in field.axes).
      A field is only as strong as its least-pressured axis.
    - Accumulation is additive (EMA): each update blends new signal with history.
    - reset_cycle() decays non-dominant fields each processing pass, preventing
      stale fields from dominating the state.
    - Thread safety: not provided. Call from a single driver thread.

    Parameters
    ----------
    activation_threshold : float
        Minimum accumulated pressure for a field to appear in active_fields.
    ema_rate : float
        Blending factor for exponential moving average. Higher = faster response.
    decay_factor : float
        Multiplier applied to non-dominant field pressures on reset_cycle().
    """

    def __init__(
        self,
        activation_threshold: float = DEFAULT_ACTIVATION_THRESHOLD,
        ema_rate: float = 0.25,
        decay_factor: float = DECAY_FACTOR,
    ) -> None:
        self._threshold = float(activation_threshold)
        self._ema_rate = max(0.0, min(1.0, float(ema_rate)))
        self._decay = max(0.0, min(1.0, float(decay_factor)))
        # field_id → accumulated pressure [0.0, 1.0]
        self._pressures: Dict[int, float] = {f.field_id: 0.0 for f in ALL_FIELDS}
        self._update_count: int = 0

    # ------------------------------------------------------------------
    # PRIMARY INTERFACE
    # ------------------------------------------------------------------

    def update(self, pressure_vec: object) -> None:
        """
        Receive a live PressureVec and update all 31 field pressures.

        The PressureVec object must expose attributes X, T, N, B, A as floats.
        Accepts both dataclass-style attribute access and dict-style .to_dict().

        Activation law: field pressure = min(axis values across the subset).
        This means a field is only as strong as its weakest constituent axis.
        Accumulation uses EMA so transient spikes don't dominate.
        """
        pv = self._extract_pv(pressure_vec)
        if pv is None:
            return

        for f in ALL_FIELDS:
            # Weakest-link measure: min pressure across all axes in the subset
            signal = min(pv.get(ax, 0.0) for ax in f.axes)
            # Clamp to [0, 1]
            signal = max(0.0, min(1.0, signal))
            # EMA accumulation
            prev = self._pressures[f.field_id]
            self._pressures[f.field_id] = (
                self._ema_rate * signal + (1.0 - self._ema_rate) * prev
            )

        self._update_count += 1

    def reset_cycle(self) -> None:
        """
        Decay non-dominant fields at the end of a processing pass.

        The dominant field (highest accumulated pressure) retains its value.
        All other fields are multiplied by decay_factor. This prevents pressure
        from stagnating at fields that were relevant in prior passes but are no
        longer active.
        """
        state = self.get_state()
        dominant = state.dominant_field
        dom_id = dominant.field_id if dominant is not None else -1

        for fid in self._pressures:
            if fid != dom_id:
                self._pressures[fid] = self._pressures[fid] * self._decay

    def get_state(self) -> ConstraintFieldState:
        """
        Return the current ConstraintFieldState snapshot.

        active_fields: all fields whose accumulated pressure >= threshold.
        dominant_field: the highest-pressure active field.
        """
        active: List[ConstraintField] = []
        for f in ALL_FIELDS:
            if self._pressures[f.field_id] >= self._threshold:
                active.append(f)

        dominant: Optional[ConstraintField] = None
        if active:
            dominant = max(active, key=lambda f: self._pressures[f.field_id])

        return ConstraintFieldState(
            active_fields=active,
            field_pressures=dict(self._pressures),
            dominant_field=dominant,
        )

    # ------------------------------------------------------------------
    # PRIMARY PUBLIC INTERFACE
    # ------------------------------------------------------------------

    def get_dominant_field(self) -> Optional[ConstraintField]:
        """
        Return the highest-pressure active field.

        Intended as the primary read point for crystal convergence logic
        and future predictive frame governors. Returns None if all fields
        are below activation threshold.
        """
        return self.get_state().dominant_field

    def get_active_fields(self) -> List[ConstraintField]:
        """
        Return all fields currently above activation threshold, sorted by
        pressure descending.

        Use this to drive any predictive frame or convergence logic that
        needs to know which multi-axis configurations are co-active.
        """
        state = self.get_state()
        return sorted(
            state.active_fields,
            key=lambda f: state.field_pressures[f.field_id],
            reverse=True,
        )

    def get_field_pressure(self, axes: FrozenSet[str]) -> float:
        """Convenience: current accumulated pressure for a field by its axis set."""
        f = get_field(axes)
        if f is None:
            return 0.0
        return self._pressures[f.field_id]

    def reset(self) -> None:
        """Full reset — zero all accumulated pressures."""
        for fid in self._pressures:
            self._pressures[fid] = 0.0
        self._update_count = 0

    @property
    def update_count(self) -> int:
        """Total number of update() calls since creation or last reset()."""
        return self._update_count

    # ------------------------------------------------------------------
    # INTERNAL
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_pv(pv_obj: object) -> Optional[Dict[str, float]]:
        """
        Extract a {X,T,N,B,A} float dict from whatever PressureVec object is passed.

        Supports:
          - Objects with .to_dict()
          - Objects with .X .T .N .B .A attributes
          - Plain dicts
          - None → returns None (silent skip, never raises)
        """
        if pv_obj is None:
            return None
        try:
            if hasattr(pv_obj, "to_dict"):
                d = pv_obj.to_dict()
                if isinstance(d, dict):
                    return {ax: float(d.get(ax, 0.0)) for ax in AXES}
            if hasattr(pv_obj, "X") and hasattr(pv_obj, "T"):
                return {ax: float(getattr(pv_obj, ax, 0.0)) for ax in AXES}
            if isinstance(pv_obj, dict):
                return {ax: float(pv_obj.get(ax, 0.0)) for ax in AXES}
        except Exception:
            pass
        return None

    def status(self) -> Dict:
        """Status dict for hub / diagnostic endpoints."""
        state = self.get_state()
        top5 = state.top_n(5)
        return {
            "update_count": self._update_count,
            "active_fields": len(state.active_fields),
            "dominant": state.dominant_field.name if state.dominant_field else None,
            "dominant_depth": state.dominant_field.depth if state.dominant_field else None,
            "top_5_fields": [
                {"name": f.name, "depth": f.depth, "pressure": round(p, 4)}
                for f, p in top5
            ],
            "params": {
                "activation_threshold": self._threshold,
                "ema_rate": self._ema_rate,
                "decay_factor": self._decay,
            },
        }


# ---------------------------------------------------------------------------
# MODULE-LEVEL SUMMARY HELPERS
# ---------------------------------------------------------------------------

def describe_all_fields() -> str:
    """
    Print a human-readable table of all 31 fields.
    Useful for diagnostics and documentation.
    """
    lines = [
        "=" * 60,
        "AURORA CONSTRAINT FIELD MAP — ALL 31 FIELDS",
        "Authors: Sunni (Sir) Morningstar and Cael Devo",
        "=" * 60,
        f"{'ID':>3}  {'NAME':<16}  {'DEPTH'}  {'AXES'}",
        "-" * 60,
    ]
    for f in ALL_FIELDS:
        axes_str = "{" + ", ".join(sorted(f.axes)) + "}"
        lines.append(f"{f.field_id:>3}  {f.name:<16}  {f.depth:>5}  {axes_str}")
    lines.append("=" * 60)
    return "\n".join(lines)

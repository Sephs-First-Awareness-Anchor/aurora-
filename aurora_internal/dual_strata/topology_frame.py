"""
aurora_internal/dual_strata/topology_frame.py
================================================
TopologyFrame — MTSL Phase 1 (2026-07-13), spec section 6.1.

Plain data only: no live system references, no methods with side
effects. One tick's constraint-space snapshot, built by a caller that
already has the real values (a coordinator, in Phase 3) -- this module
never reaches into `systems` itself. Round-trips through
to_dict()/from_dict() so frames can be persisted, replayed, and used to
reconstruct TopologyTracker state (TopologyTracker.from_frames()).

Precision note P1 (MTSL directive): manifold_slot_id refers to the
3,125-slot SlotCoord space (aurora_constraint_manifold_router.SlotCoord
-- target/nc_law_c/nc_dim/law_c/law_d, `.slot_id` property), never the
78,125-slot compiled-manifold-directory/sediment-overlay space (125
noncomp x 625 interaction grid). Comments and variable names in code that
builds a manifold_slot_id must say which space they mean.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

AXES: Tuple[str, ...] = ("X", "T", "N", "B", "A")

SCHEMA_VERSION = 1


@dataclass(frozen=True)
class TopologyFrame:
    """
    One tick's constraint-space snapshot.

    Field semantics not otherwise pinned down by the directive's field
    list are first-pass, documented choices (flagged below) grounded in
    existing codebase conventions -- not sourced from an external spec
    this implementation didn't have access to. Treat crest_axes/
    trough_axes/active_constraint_fields as the parts of this file most
    worth reviewing against the full MTSL spec when it's available.
    """
    schema_version: int
    turn_id: str
    timestamp: float
    constraint_vector: Dict[str, float]     # CV: current {X,T,N,B,A} -> pressure
    previous_vector: Dict[str, float]       # CV at the prior tick
    delta_vector: Dict[str, float]          # constraint_vector - previous_vector, per axis
    manifold_slot_id: Optional[str]         # MC: SlotCoord.slot_id (3,125-slot space) or None
    base_meaning_form: Optional[str]        # BMF: canonical_signature() output, or None
    crest_axes: Tuple[str, ...]             # axes at/above this tick's own mean pressure
    trough_axes: Tuple[str, ...]            # axes below this tick's own mean pressure
    active_constraint_fields: Tuple[str, ...]  # axes whose |delta| cleared the activation floor
    ivm_phase: Dict[str, float]             # per-axis IVM toroidal polarity, cos(phase) in [-1,1]
    context_family: Optional[str]           # caller-supplied topic/context tag; not derived here
    creation_residual: float                # max(0, sum(delta_vector)) -- net pressure with no donor axis
    dissipation_residual: float             # max(0, -sum(delta_vector)) -- net pressure with no receiving axis

    # ── serialization (replay support) ──

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "turn_id": self.turn_id,
            "timestamp": self.timestamp,
            "constraint_vector": dict(self.constraint_vector),
            "previous_vector": dict(self.previous_vector),
            "delta_vector": dict(self.delta_vector),
            "manifold_slot_id": self.manifold_slot_id,
            "base_meaning_form": self.base_meaning_form,
            "crest_axes": list(self.crest_axes),
            "trough_axes": list(self.trough_axes),
            "active_constraint_fields": list(self.active_constraint_fields),
            "ivm_phase": dict(self.ivm_phase),
            "context_family": self.context_family,
            "creation_residual": self.creation_residual,
            "dissipation_residual": self.dissipation_residual,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TopologyFrame":
        return cls(
            schema_version=int(data.get("schema_version", SCHEMA_VERSION) or SCHEMA_VERSION),
            turn_id=str(data.get("turn_id", "") or ""),
            timestamp=float(data.get("timestamp", 0.0) or 0.0),
            constraint_vector=dict(data.get("constraint_vector", {}) or {}),
            previous_vector=dict(data.get("previous_vector", {}) or {}),
            delta_vector=dict(data.get("delta_vector", {}) or {}),
            manifold_slot_id=data.get("manifold_slot_id"),
            base_meaning_form=data.get("base_meaning_form"),
            crest_axes=tuple(data.get("crest_axes", []) or []),
            trough_axes=tuple(data.get("trough_axes", []) or []),
            active_constraint_fields=tuple(data.get("active_constraint_fields", []) or []),
            ivm_phase=dict(data.get("ivm_phase", {}) or {}),
            context_family=data.get("context_family"),
            creation_residual=float(data.get("creation_residual", 0.0) or 0.0),
            dissipation_residual=float(data.get("dissipation_residual", 0.0) or 0.0),
        )

    # ── construction from raw values ──

    @classmethod
    def from_vectors(
        cls,
        *,
        turn_id: str,
        timestamp: float,
        constraint_vector: Dict[str, float],
        previous_vector: Optional[Dict[str, float]] = None,
        manifold_slot_id: Optional[str] = None,
        base_meaning_form: Optional[str] = None,
        ivm_phase: Optional[Dict[str, float]] = None,
        context_family: Optional[str] = None,
        active_floor: float = 0.05,
        schema_version: int = SCHEMA_VERSION,
    ) -> "TopologyFrame":
        """
        Build a frame from raw axis vectors. The fields derivable purely
        from constraint_vector/previous_vector (delta, crest/trough,
        active fields, creation/dissipation residual) are computed here
        honestly from real values. manifold_slot_id, base_meaning_form,
        ivm_phase, and context_family are supplied by the caller --
        this module deliberately never reaches into `systems` itself
        (SlotCoord resolution, canonical_signature(), lattice polarity,
        and topic/context tagging all live outside this plain-data layer).
        """
        cur = {a: float((constraint_vector or {}).get(a, 0.0) or 0.0) for a in AXES}
        prev = {a: float((previous_vector or {}).get(a, 0.0) or 0.0) for a in AXES}
        delta = {a: cur[a] - prev[a] for a in AXES}

        mean = sum(cur.values()) / len(AXES)
        crest = tuple(a for a in AXES if cur[a] >= mean)
        trough = tuple(a for a in AXES if cur[a] < mean)
        active = tuple(a for a in AXES if abs(delta[a]) >= active_floor)

        delta_total = sum(delta.values())
        creation = max(0.0, delta_total)
        dissipation = max(0.0, -delta_total)

        return cls(
            schema_version=schema_version,
            turn_id=str(turn_id),
            timestamp=float(timestamp),
            constraint_vector=cur,
            previous_vector=prev,
            delta_vector=delta,
            manifold_slot_id=manifold_slot_id,
            base_meaning_form=base_meaning_form,
            crest_axes=crest,
            trough_axes=trough,
            active_constraint_fields=active,
            ivm_phase=dict(ivm_phase or {}),
            context_family=context_family,
            creation_residual=creation,
            dissipation_residual=dissipation,
        )

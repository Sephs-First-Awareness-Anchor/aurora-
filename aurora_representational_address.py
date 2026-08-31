#!/usr/bin/env python3
"""
aurora_representational_address.py

AURORA ESTABLISHED REPRESENTATIONAL SUBSTRATE FULL INTEGRATION DIRECTIVE.

A single canonical address type spanning Aurora's confirmed representational
ladder:

    D1 (25)  -> C1 (125) -> D2 (625) -> M2,1 (3,125) -> M2,2 (15,625) -> C2 (78,125)

instead of six ad-hoc coordinate shapes (NonCompChannel id, ManifoldSlot id,
InteractionSlot id, SlotCoord, a Candidate-A tuple, and a bare manifold
directory lookup key). This module does not invent new ontology -- every
field name is adopted directly from the existing types it unifies:

  - nc_law_c, nc_dim, nc_target   <- ManifoldSlot / IndexEntry's own C1 identity
                                      fields (aurora_constraint_manifold_compiler.py,
                                      aurora_manifold_directory_reader.py)
  - sub_law_c, sub_law_d          <- ManifoldSlot's "row" (sub-position) fields
  - col_law_c, col_law_d          <- ManifoldSlot's "column" fields; identical in
                                      role to SlotCoord's law_c/law_d
                                      (aurora_constraint_manifold_router.py)

SlotCoord's own "target" field is nc_target under another name (established
directly, term-for-term, in the rank-six audit's Phase A correspondence
table) -- this module treats them as the same field rather than inventing a
parallel one.

CRITICAL, doctrine-mandated property: a field that has not been
independently determined is left as None ("unresolved"), never silently
defaulted, never silently aliased to another already-known field. Building
a RepresentationalRef at the 3,125 (M2,1) level, for example, populates
nc_law_c/nc_dim/nc_target/col_law_c/col_law_d and leaves sub_law_c/sub_law_d
explicitly None -- it does NOT set them equal to nc_law_c/nc_dim just
because that is what the live CERS/ReflexiveInterpreter pinning happens to
do. Call .as_pinned_anchor() explicitly if an anchor-row view is wanted;
that method is clearly named so the pin is visible, not disguised as
independent resolution.

Encoding is a stable, delimiter-safe string (never a bare recomputed hash
that would need a lookup table to invert) plus a JSON-serializable dict
form. Decode(Encode(ref)) == ref is exhaustively tested in
tests/test_representational_addressability.py.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
from __future__ import annotations

import os
from dataclasses import dataclass, replace
from typing import Any, Dict, FrozenSet, Optional, Tuple

AXES: Tuple[str, ...] = ("X", "T", "N", "B", "A")
DIM_NAMES: Tuple[str, ...] = ("POLARITY", "MAGNITUDE", "OPERATOR", "COST", "DIFFERENCE")

MANIFOLD_DIR_DEFAULT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aurora_manifold_directory")

_UNRESOLVED = "?"  # encoded-string placeholder for a None field; never a real axis/dim name

# The seven primitive fields spanning the entire ladder, in a fixed,
# canonical order used by both encode() and the field-name tuple below.
_FIELDS: Tuple[str, ...] = (
    "nc_law_c", "nc_dim", "nc_target", "sub_law_c", "sub_law_d", "col_law_c", "col_law_d",
)

LEVEL_D1 = "D1_25"
LEVEL_C1 = "C1_125"
LEVEL_D2 = "D2_625"
LEVEL_M21 = "M21_3125"
LEVEL_M22 = "M22_15625"
LEVEL_C2 = "C2_78125"
LEVEL_UNKNOWN = "UNKNOWN"


def _validate(name: str, value: Optional[str], domain: Tuple[str, ...]) -> None:
    if value is not None and value not in domain:
        raise ValueError(f"{name}={value!r} is not in the valid domain {domain}")


@dataclass(frozen=True)
class RepresentationalRef:
    """
    Every field is Optional[str]. None means "not independently determined
    yet" -- it is never coerced to a guessed value.

    nc_law_c, nc_dim, nc_target: the owning NonComp's identity (C1, 125 states).
    sub_law_c, sub_law_d:        the manifold "row" -- a D1 channel (25 states).
    col_law_c, col_law_d:        the manifold "column" -- a D1 channel (25 states).
    """
    nc_law_c: Optional[str] = None
    nc_dim: Optional[str] = None
    nc_target: Optional[str] = None
    sub_law_c: Optional[str] = None
    sub_law_d: Optional[str] = None
    col_law_c: Optional[str] = None
    col_law_d: Optional[str] = None

    def __post_init__(self) -> None:
        _validate("nc_law_c", self.nc_law_c, AXES)
        _validate("nc_target", self.nc_target, AXES)
        _validate("sub_law_c", self.sub_law_c, AXES)
        _validate("col_law_c", self.col_law_c, AXES)
        _validate("nc_dim", self.nc_dim, DIM_NAMES)
        _validate("sub_law_d", self.sub_law_d, DIM_NAMES)
        _validate("col_law_d", self.col_law_d, DIM_NAMES)

    # ── Resolution-state introspection (never silently assumed) ────────────

    def resolved_fields(self) -> Tuple[str, ...]:
        return tuple(f for f in _FIELDS if getattr(self, f) is not None)

    def unresolved_fields(self) -> Tuple[str, ...]:
        return tuple(f for f in _FIELDS if getattr(self, f) is None)

    def is_fully_resolved(self) -> bool:
        return len(self.unresolved_fields()) == 0

    def level(self) -> str:
        """Which named rung of the established ladder this ref's resolved
        fields correspond to. Returns LEVEL_UNKNOWN for any other pattern
        (e.g. partial/ad hoc combinations) rather than guessing the closest
        level -- an honest 'this isn't one of the six' rather than a
        forced classification."""
        r = set(self.resolved_fields())
        if r == {"nc_law_c", "nc_dim"}:
            return LEVEL_D1
        if r == {"nc_law_c", "nc_dim", "nc_target"}:
            return LEVEL_C1
        if r == {"nc_law_c", "nc_dim", "col_law_c", "col_law_d"}:
            return LEVEL_D2
        if r == {"nc_law_c", "nc_dim", "nc_target", "col_law_c", "col_law_d"}:
            return LEVEL_M21
        if r == {"nc_law_c", "nc_dim", "nc_target", "sub_law_c", "col_law_c", "col_law_d"}:
            return LEVEL_M22
        if r == set(_FIELDS):
            return LEVEL_C2
        return LEVEL_UNKNOWN

    # ── Level-specific constructors (each leaves everything else None) ─────

    @classmethod
    def for_d1(cls, constraint: str, dimension: str) -> "RepresentationalRef":
        """One of the 25 D1 channels."""
        return cls(nc_law_c=constraint, nc_dim=dimension)

    @classmethod
    def for_c1(cls, constraint: str, dimension: str, target: str) -> "RepresentationalRef":
        """One of the 125 C1 (NonComp identity) states."""
        return cls(nc_law_c=constraint, nc_dim=dimension, nc_target=target)

    @classmethod
    def for_d2(cls, row_constraint: str, row_dimension: str,
               col_constraint: str, col_dimension: str) -> "RepresentationalRef":
        """One of the 625 canonical D2 ordered relationships between two D1
        channels -- no C1/target context implied."""
        return cls(nc_law_c=row_constraint, nc_dim=row_dimension,
                    col_law_c=col_constraint, col_law_d=col_dimension)

    @classmethod
    def for_m21(cls, nc_law_c: str, nc_dim: str, nc_target: str,
                col_law_c: str, col_law_d: str) -> "RepresentationalRef":
        """One of the static 3,125 SlotCoord positions: a C1 identity
        crossed with a column D1 channel. sub_law_c/sub_law_d are left
        explicitly unresolved -- SlotCoord has no field for them; treating
        them as implicitly equal to nc_law_c/nc_dim is the anchor-pinning
        behavior this directive requires making visible, not default."""
        return cls(nc_law_c=nc_law_c, nc_dim=nc_dim, nc_target=nc_target,
                    col_law_c=col_law_c, col_law_d=col_law_d)

    @classmethod
    def for_m22(cls, nc_law_c: str, nc_dim: str, nc_target: str,
                sub_law_c: str, col_law_c: str, col_law_d: str) -> "RepresentationalRef":
        """One of the confirmed-independent 15,625 Candidate-A positions:
        M2,1 plus the freed sub_law_c coordinate. sub_law_d remains
        explicitly unresolved (Candidate A frees sub_law_c only -- sub_law_d
        was established as coupled, not independent, and is not promoted
        here)."""
        return cls(nc_law_c=nc_law_c, nc_dim=nc_dim, nc_target=nc_target,
                    sub_law_c=sub_law_c, col_law_c=col_law_c, col_law_d=col_law_d)

    @classmethod
    def for_c2(cls, nc_law_c: str, nc_dim: str, nc_target: str,
               sub_law_c: str, sub_law_d: str,
               col_law_c: str, col_law_d: str) -> "RepresentationalRef":
        """One of the full 78,125 C2 ManifoldSlot positions -- all seven
        primitive fields resolved."""
        return cls(nc_law_c=nc_law_c, nc_dim=nc_dim, nc_target=nc_target,
                    sub_law_c=sub_law_c, sub_law_d=sub_law_d,
                    col_law_c=col_law_c, col_law_d=col_law_d)

    def as_pinned_anchor(self) -> "RepresentationalRef":
        """Explicit, clearly-named opt-in to the anchor/self pin (sub :=
        nc's own identity) that live SlotCoord construction currently
        performs implicitly. Only defined starting from an M21/C1-shaped
        ref that already has nc_law_c/nc_dim; never called automatically."""
        if self.nc_law_c is None or self.nc_dim is None:
            raise ValueError("as_pinned_anchor() requires nc_law_c/nc_dim to already be resolved")
        return replace(self, sub_law_c=self.nc_law_c, sub_law_d=self.nc_dim)

    def as_pinned_column(self) -> "RepresentationalRef":
        """Explicit, clearly-named opt-in to pinning the column (col_law_c/
        col_law_d := this ref's own nc_law_c/nc_dim) for call sites with no
        independent column evidence -- e.g. ReflexiveInterpreter.interpret()'s
        live SlotCoord construction, where the only candidate
        (IndexEntry.dense_top3) was traced to
        aurora_constraint_manifold_compiler.py's dense_clusters computation
        and confirmed to aggregate across every col_law_c that ever produced
        a given (sub_cluster, col_law_d) pair, structurally discarding which
        one contributed -- not merely hard to parse out. Only defined
        starting from a ref that already has nc_law_c/nc_dim; never called
        automatically."""
        if self.nc_law_c is None or self.nc_dim is None:
            raise ValueError("as_pinned_column() requires nc_law_c/nc_dim to already be resolved")
        return replace(self, col_law_c=self.nc_law_c, col_law_d=self.nc_dim)

    # ── NonComp (C1) identity helpers ───────────────────────────────────────

    def nc_name_key(self) -> Optional[Tuple[str, str, str]]:
        """The (nc_law_c, nc_dim, nc_target) triple, or None if any of the
        three is unresolved. Does not guess a NonComp name string -- callers
        resolve the real name via ManifoldDirectory.get_index_entry-style
        lookup (see resolve_manifold_slot below)."""
        if self.nc_law_c is None or self.nc_dim is None or self.nc_target is None:
            return None
        return (self.nc_law_c, self.nc_dim, self.nc_target)

    # ── Serialization ────────────────────────────────────────────────────

    def encode(self) -> str:
        """Stable, delimiter-safe string. Unresolved fields are encoded as
        '?' explicitly -- never omitted (omission would be ambiguous with
        a future added field) and never filled with a guessed value."""
        parts = [(getattr(self, f) if getattr(self, f) is not None else _UNRESOLVED) for f in _FIELDS]
        return "REF:" + ":".join(parts)

    @classmethod
    def decode(cls, s: str) -> "RepresentationalRef":
        if not s.startswith("REF:"):
            raise ValueError(f"not a RepresentationalRef encoding: {s!r}")
        body = s[len("REF:"):]
        parts = body.split(":")
        if len(parts) != len(_FIELDS):
            raise ValueError(f"expected {len(_FIELDS)} fields, got {len(parts)}: {s!r}")
        kwargs = {
            f: (None if p == _UNRESOLVED else p)
            for f, p in zip(_FIELDS, parts)
        }
        return cls(**kwargs)

    def to_dict(self) -> Dict[str, Optional[str]]:
        return {f: getattr(self, f) for f in _FIELDS}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "RepresentationalRef":
        return cls(**{f: d.get(f) for f in _FIELDS})


# ── Resolution against the real, already-compiled manifold ─────────────────

def resolve_manifold_slot(ref: RepresentationalRef, manifold_dir: str = MANIFOLD_DIR_DEFAULT) -> Optional[Dict[str, Any]]:
    """Resolves a fully-resolved (C2-level) ref to its actual, real,
    already-compiled ManifoldSlot dict on disk. Returns None (never a
    fabricated slot) if any required field is unresolved or no matching
    file/slot exists. Read-only -- never writes anything."""
    if ref.nc_law_c is None or ref.nc_dim is None or ref.nc_target is None:
        return None
    if ref.sub_law_c is None or ref.sub_law_d is None or ref.col_law_c is None or ref.col_law_d is None:
        return None

    from aurora_manifold_directory_reader import ManifoldDirectory
    directory = ManifoldDirectory(manifold_dir)
    nc_name = None
    for entry in directory.entries_for_axis(ref.nc_target):
        if entry.nc_law_c == ref.nc_law_c and entry.nc_dim == ref.nc_dim:
            nc_name = entry.nc_name
            break
    if nc_name is None:
        return None

    with directory.open(nc_name) as m:
        for slot in m.stream_slots():
            if (slot.sub_law_c == ref.sub_law_c and slot.sub_law_d == ref.sub_law_d and
                    slot.col_law_c == ref.col_law_c and slot.col_law_d == ref.col_law_d):
                return {
                    "slot_id": slot.slot_id,
                    "nc_name": nc_name,
                    "evolution_grade": slot.evolution_grade,
                    "accountability_weight": slot.accountability_weight,
                    "depth_score": slot.depth_score,
                    "combined_cost": slot.combined_cost,
                    "cluster_pair": slot.cluster_pair,
                    "is_resonant": slot.is_resonant,
                    "is_anchor": slot.is_anchor,
                }
    return None


def slotcoord_from_ref(ref: RepresentationalRef):
    """Adapts a RepresentationalRef at (at least) the M21 level into a real
    aurora_constraint_manifold_router.SlotCoord -- the existing type this
    module's M2,1/M2,2 fields were named after. Raises if the required
    fields (nc_law_c, nc_dim, nc_target, col_law_c, col_law_d) aren't
    resolved; never guesses."""
    if any(getattr(ref, f) is None for f in ("nc_law_c", "nc_dim", "nc_target", "col_law_c", "col_law_d")):
        raise ValueError("ref does not have the fields required to build a SlotCoord (M2,1 level or above)")
    from aurora_constraint_manifold_router import SlotCoord
    return SlotCoord(target=ref.nc_target, nc_law_c=ref.nc_law_c, nc_dim=ref.nc_dim,
                      law_c=ref.col_law_c, law_d=ref.col_law_d)


def ref_from_slotcoord(coord) -> RepresentationalRef:
    """Inverse of slotcoord_from_ref -- the resulting ref explicitly leaves
    sub_law_c/sub_law_d unresolved (SlotCoord's real semantics, per the
    rank-six audit: no sub field exists in SlotCoord at all)."""
    return RepresentationalRef.for_m21(
        nc_law_c=coord.nc_law_c, nc_dim=coord.nc_dim, nc_target=coord.target,
        col_law_c=coord.law_c, col_law_d=coord.law_d,
    )

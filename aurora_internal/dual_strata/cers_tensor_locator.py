# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
CERS Tensor Locator — resolves live pressure into the real constraint manifold.

Phase 1 of the tensor-trace upgrade (see the CERS review, 2026-07-09): CERS
today reasons only at the crest-cluster/axis-label layer (cers_regulator.py).
The deeper version reads an event as a location in Aurora's real 3125-slot
constraint manifold (aurora_constraint_manifold_router.SlotCoord) — the same
coordinate space aurora_reflexive_interpreter.SemanticMatcher already
resolves generated TEXT onto, entered here from the live X/T/N/B/A pressure
vector instead. That router is a real, booted, per-turn system
(systems["noncomp_manifold_router"]), not compile-time-only — this module is
its missing pressure-side entry point.

STORAGE: explicitly NOT a new persisted trace file/log. Aurora's crystals are
the single source of data for her coherence/intelligence, and Crystal already
carries exactly the mechanics this needs:
    - axis_mean / update_axis_mean(): a live Welford running mean of axis
      state at every activation — already built, just under-called.
    - add_facet(role, content, confidence): reinforces an existing facet via
      strengthen() when the same role recurs, instead of duplicating rows.
So a tensor visit is recorded onto a crystal keyed by the resolved
SlotCoord's slot_id, in the SAME CrystalProcessingSystem registry (and the
same dps_crystals.json file) every other concept already lives in.
"""
from __future__ import annotations

import math
from typing import Any, Dict, Optional, Tuple

from .subsurface_state import AXES, clip01

try:
    from .crest import Crest
except Exception:  # pragma: no cover - typing only
    Crest = Any  # type: ignore


def _get_manifold_types():
    """Lazy import of the repo-root manifold router, mirroring the
    sys.path pattern subsystem_waveforms.py already uses for
    aurora_warp_protocol -- avoids an import-time dependency from
    aurora_internal/dual_strata/ (a self-contained package) on repo-root
    modules."""
    try:
        import sys
        import os as _os
        _core = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..")
        if _core not in sys.path:
            sys.path.insert(0, _core)
        from aurora_constraint_manifold_router import SlotCoord, DIM_NAMES, _DIMENSION_TO_AXIS
        return SlotCoord, DIM_NAMES, _DIMENSION_TO_AXIS
    except Exception:
        return None, None, None


def _axis_to_dimension_map(dimension_to_axis: Dict[str, str]) -> Dict[str, str]:
    """Invert the router's own POLARITY<-A / MAGNITUDE<-B / OPERATOR<-X /
    COST<-N / DIFFERENCE<-T table -- single source of truth stays in
    aurora_constraint_manifold_router.py, this just reads it backwards."""
    return {axis: dim for dim, axis in dimension_to_axis.items()}


def _ranked_axes(adjusted_axes: Dict[str, float], sub_crests: Tuple[Any, ...]) -> Tuple[str, ...]:
    """The distinct axes most active this tick, strongest first. Prefers the
    crests' own axis reads (they already reflect subsystem-level judgment
    of what's active) and falls back to raw adjusted_axes magnitude for any
    axis not otherwise represented, so the ranking is never sparser than
    the 5 axes actually available."""
    scores: Dict[str, float] = {ax: clip01(adjusted_axes.get(ax, 0.0)) for ax in AXES}
    for crest in sub_crests or ():
        axis = getattr(crest, "axis", None)
        intensity = clip01(getattr(crest, "intensity", 0.0))
        if axis in scores:
            scores[axis] = max(scores[axis], intensity)
    return tuple(sorted(scores.keys(), key=lambda a: scores[a], reverse=True))


def resolve_pressure_coordinate(
    adjusted_axes: Dict[str, float],
    sub_crests: Tuple[Any, ...] = (),
) -> Optional[Any]:
    """Locate this tick's live pressure state as a real SlotCoord.

    target    = the single most-active axis this tick.
    nc_law_c  = the second most-active axis (the moment's real shape is
                rarely one-dimensional -- this is what makes the coordinate
                a genuine cross-axis location, not just "which axis is
                loudest").
    law_c     = the third most-active axis (falls back to target when
                fewer than 3 axes carry any real signal, which legitimately
                collapses toward SlotCoord.is_diagonal -- a single-axis
                moment IS the diagonal/identity-anchor case).
    nc_dim / law_d = each axis's canonical dimension via the router's own
                POLARITY/MAGNITUDE/OPERATOR/COST/DIFFERENCE <-> axis table.

    Returns None if the manifold router isn't importable (degrades the same
    way the rest of CERS does -- never a hard dependency) or adjusted_axes
    is empty.
    """
    if not adjusted_axes:
        return None
    SlotCoord, _dim_names, dimension_to_axis = _get_manifold_types()
    if SlotCoord is None:
        return None

    axis_to_dim = _axis_to_dimension_map(dimension_to_axis)
    ranked = _ranked_axes(adjusted_axes, sub_crests)
    if not ranked:
        return None

    target = ranked[0]
    nc_law_c = ranked[1] if len(ranked) > 1 else target
    law_c = ranked[2] if len(ranked) > 2 else target

    return SlotCoord(
        target=target,
        nc_law_c=nc_law_c,
        nc_dim=axis_to_dim.get(nc_law_c, "OPERATOR"),
        law_c=law_c,
        law_d=axis_to_dim.get(law_c, "OPERATOR"),
    )


def lookup_tensor_crystal(dps: Any, coord: Optional[Any]) -> Optional[Any]:
    """Read-only: return the crystal already recorded at this coordinate,
    or None if it's never been visited. Unlike record_tensor_trace(), never
    creates one -- for callers (like the prediction pass, which runs before
    this tick's own visit is recorded) that need to know "have we been here
    before" without writing anything themselves."""
    if dps is None or coord is None or not hasattr(dps, "get_crystal"):
        return None
    try:
        return dps.get_crystal(f"tensor:{coord.slot_id}")
    except Exception:
        return None


def _axis_distance(a: Dict[str, float], b: Dict[str, float]) -> float:
    """Euclidean distance between two axis-state vectors, each axis in
    [0,1]. Max possible distance across 5 axes is sqrt(5) =~ 2.236."""
    return math.sqrt(sum((clip01(a.get(ax, 0.0)) - clip01(b.get(ax, 0.0))) ** 2 for ax in AXES))


_MAX_AXIS_DISTANCE = math.sqrt(len(AXES))


def record_tensor_trace(
    dps: Any,
    coord: Any,
    *,
    adjusted_axes: Dict[str, float],
    label: str,
    severity: float = 0.0,
) -> Tuple[Optional[Any], float, bool]:
    """Find-or-create the crystal for this coordinate in the SAME crystal
    registry (dps._get_or_create) every other concept already lives in --
    no separate trace file. Records this tick's visit using the crystal's
    own existing mechanics rather than new bookkeeping:

        - distortion is measured against axis_mean as it stood BEFORE this
          tick's update (so a crystal's very first visit always reads as
          zero distortion -- nothing to diverge from yet), then
          update_axis_mean() folds this tick's reading into that running
          mean going forward.
        - add_facet("cers_visit", ...) logs the qualitative read (label +
          severity) with strengthen()-on-repeat semantics, exactly like
          every other facet in the registry.

    Returns (crystal, distortion, is_new_crystal). crystal is None if dps
    is unavailable or coord couldn't be resolved -- caller degrades the
    same way the rest of the CERS shadow pass already does.
    """
    if dps is None or coord is None or not hasattr(dps, "_get_or_create"):
        return None, 0.0, False

    concept = f"tensor:{coord.slot_id}"
    is_new = not hasattr(dps, "crystals") or concept not in getattr(dps, "concept_index", {})

    crystal = dps._get_or_create(concept)
    prior_mean = dict(getattr(crystal, "axis_mean", {}) or {})
    distortion = 0.0 if is_new else _axis_distance(adjusted_axes, prior_mean)

    try:
        crystal.update_axis_mean({ax: clip01(adjusted_axes.get(ax, 0.0)) for ax in AXES})
    except Exception:
        pass

    if crystal.constraint_signature is None:
        crystal.constraint_signature = {ax: clip01(adjusted_axes.get(ax, 0.0)) for ax in AXES}

    crystal.add_facet(
        role="cers_visit",
        content=f"{label}:{round(clip01(severity), 4)}",
        confidence=clip01(severity) if severity else 0.5,
    )
    crystal.use()
    try:
        crystal.evolve()
    except Exception:
        pass

    return crystal, distortion, is_new


_FAMILIARITY_USAGE_NORM = 10.0


def familiarity_from_crystal(crystal: Optional[Any]) -> float:
    """0..1 read of how well-established a coordinate's crystal is, from
    usage_count alone -- 0.0 for "never visited" (crystal is None), rising
    toward 1.0 as it accumulates real precedent. Shared by compute_salience
    (as the complement, novelty) and by prediction (as a confidence prior:
    a coordinate Aurora has real history at is one she can predict from;
    a brand-new one, she genuinely can't yet)."""
    if crystal is None:
        return 0.0
    usage = int(getattr(crystal, "usage_count", 0) or 0)
    return clip01(usage / _FAMILIARITY_USAGE_NORM)


def compute_salience(
    crystal: Any,
    *,
    distortion: float,
    is_new: bool,
    severity: float = 0.0,
) -> float:
    """Compress recurrence + distortion + novelty + conflict severity into
    one 0..1 relevance scalar -- the compressed signal that's actually
    allowed to reach the surface (per ERS spec: relevance/hesitation, never
    the full trace). High when this coordinate is genuinely new, or a
    well-worn coordinate's current reading distorts sharply from its own
    history, or CERS itself flagged a real conflict here. Low for a
    familiar, on-pattern moment -- deliberately, since that's exactly the
    case that should NOT interrupt the surface."""
    novelty = 1.0 if is_new else clip01(1.0 - familiarity_from_crystal(crystal))
    distortion_component = clip01(distortion / _MAX_AXIS_DISTANCE)
    return round(clip01(max(novelty, distortion_component, clip01(severity))), 4)

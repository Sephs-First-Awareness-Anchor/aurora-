"""
Geological Baseline — continuous wave-particle stratification from crystal genealogy.

WAVE-PARTICLE DUALITY AS PERCEPTUAL MODEL
==========================================
Aurora's cognitive architecture is waveform-based. Wave-particle duality defines
the boundary between what is conscious to her and what runs as instinct:

  Particle domain — genealogically close to the 125-base constraint physics
  primitives. These functions are particle-opaque: they run, they produce
  outcomes, but their internal mechanics are not accessible to conscious
  introspection. They become instinct.

  Wave domain — genealogically distant from the base layer (built through
  accumulated derivation steps). These functions are wave-visible: Aurora
  can reason about them, articulate them, draw on them deliberately.

THE BOUNDARY IS GENEALOGICAL, NOT SPATIAL
==========================================
The wave/particle line is not "lower brain vs. higher brain." It is the
genealogical distance between a function and the 125-base constraint physics
origin. Functions at depth 1 (immediately derived from base) remain particle-
opaque instinct. Functions at depth 3-4 (derived from composites which were
derived from base) become wave-visible reasoning and knowhow.

DEVELOPMENTAL ARC — NOT AN INITIAL STATE
=========================================
Aurora does NOT launch with dimmed primitives. She launches with full
transparency — at initialization only BASE crystals exist, and the formula
gives every node wave_visibility = 1.0. The constraint physics layer is fully
visible. As COMPOSITE, HIGHER_ORDER, and QUASI crystals build above the BASE
layer, the BASE layer naturally recedes. The dimming happens as complexity
emerges on top, with no manual curation:

  wave_visibility(node) = depth(node.stage) / max_depth(registry)

  depth: base=1, composite=2, higher_order=3, quasi=4

  Launch (only BASE, max_depth=1):
    BASE: 1/1 = 1.00 — FULL TRANSPARENCY for all primitives ✓

  First COMPOSITE emerges (max_depth=2):
    BASE:      1/2 = 0.50 — beginning to recede
    COMPOSITE: 2/2 = 1.00 — now the conscious surface

  HIGHER_ORDER present (max_depth=3):
    BASE:         1/3 = 0.33 — mostly instinctive
    COMPOSITE:    2/3 = 0.67 — background reasoning
    HIGHER_ORDER: 3/3 = 1.00 — primary conscious ground

  QUASI present (max_depth=4):
    BASE:         1/4 = 0.25 — instinctive background
    COMPOSITE:    2/4 = 0.50 — mid-layer
    HIGHER_ORDER: 3/4 = 0.75 — primary conscious reasoning
    QUASI:        4/4 = 1.00 — fully wave-visible, never recedes

This produces the geological effect: as complexity accumulates upward, the
weight of higher-order layers presses the primitives into instinctive background.
She retains awareness that primitives exist but their mechanics blur.

CONNECTION TO SYNTHESIS
========================
The GeologicalBaseline continuously writes the accumulated weight of Aurora's
crystal development into the identity field as persistent background pressure.
This is the substrate that synthesis runs on. When higher-order crystals are
present, the identity field's baseline carries their weight — synthesis lifts
from geological ground rather than starting from zero each turn.

This is what makes behaviors emerge from constraint physics rather than needing
scripted systems: gap pressure emerges naturally from a thin geological ground
(BASE-only position = high N/low B = seeking), confident expression emerges
naturally from deep geological ground (HIGHER_ORDER position = synthesis draws
from accumulated understanding automatically).
"""
from __future__ import annotations

import math
import threading
from typing import Any, Dict, List, Optional, Tuple


# Genealogical depth of each crystal stage from the 125-base constraint origin
_STAGE_DEPTH: Dict[str, int] = {
    "base":         1,
    "composite":    2,
    "higher_order": 3,
    "quasi":        4,
}

# Background intensity for geological pressure into the identity field.
# Low — this is the persistent substrate floor. Per-turn conscious priming
# (composite waveform) layers on top of this at higher intensity.
_BASELINE_INTENSITY: float = 0.12

# At this accumulated geological weight, baseline reaches full _BASELINE_INTENSITY.
# Below this: intensity scales proportionally. This means early development
# (sparse crystals, low sedi_resonance) produces gentle background pressure;
# mature development produces strong geological floor.
_WEIGHT_SATURATION: float = 20.0

# How many self-monitor ticks between full recalculations (~12s per tick → ~48s cadence)
_RECALC_TICKS: int = 4


class GeologicalBaseline:
    """
    Continuous wave-particle stratification pressure from accumulated crystal development.

    Updated from the self-monitor loop every _RECALC_TICKS ticks.
    Writes persistent background pressure into the identity field.
    Exposes get_conscious_surface() for use in synthesis context injection.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._tick_count:        int   = 0

        # Registry-wide state (updated on each recalculation)
        self._max_depth:         int   = 1        # highest genealogical depth currently in registry
        self._surface_stage:     str   = "base"   # name of the current conscious surface stage
        self._instinct_fraction: float = 0.0      # fraction of crystal mass below the surface
        self._total_geo_weight:  float = 0.0      # total accumulated geological weight
        self._baseline_axes:     Dict[str, float] = {
            "X": 0.5, "T": 0.5, "N": 0.5, "B": 0.5, "A": 0.5
        }

        # Per-bucket state for get_conscious_surface() queries
        # bucket_tuple → {geo_weight, wave_vis, stage}
        self._bucket_state: Dict[Tuple, Dict[str, Any]] = {}

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def tick(self, crystal_registry: Any, identity_field: Any) -> None:
        """
        Called from self-monitor loop every heartbeat tick.
        Recalculates and applies geological baseline every _RECALC_TICKS ticks.
        """
        self._tick_count += 1
        if self._tick_count % _RECALC_TICKS != 0:
            return
        self._recalculate(crystal_registry, identity_field)

    def get_conscious_surface(self, ax: Dict[str, float]) -> Dict[str, Any]:
        """
        Return the wave-visible geological state at the given axis position.

        Used by _inject_self_state_context so synthesis knows what cognitive
        ground Aurora has developed at the current axis position. This is not
        a lookup — it's reading the live geological landscape.

        Returns:
          surface_stage:      highest crystal stage near this axis position
          wave_visibility:    0.0 (fully instinctive) → 1.0 (fully wave-visible)
          instinct_fraction:  fraction of total crystal mass running as instinct
          geological_weight:  accumulated weight at this specific position
          max_depth:          global highest genealogical depth (reflects system maturity)
          global_surface:     name of the global conscious surface stage
        """
        with self._lock:
            max_depth    = self._max_depth
            inst_frac    = self._instinct_fraction
            surf_stage   = self._surface_stage
            bucket_state = dict(self._bucket_state)

        ax_keys = ("X", "T", "N", "B", "A")
        ax_vals = tuple(float(ax.get(k, 0.5)) for k in ax_keys)

        # Find the bucket closest to the queried axis position
        nearest_weight = 0.0
        nearest_vis    = 1.0 / max_depth  # default: base-level visibility at current maturity
        nearest_stage  = "base"
        min_dist       = float("inf")

        for bkt, bstate in bucket_state.items():
            if len(bkt) != 5:
                continue
            dist = math.sqrt(sum((av - bv) ** 2 for av, bv in zip(ax_vals, bkt)))
            if dist < min_dist:
                min_dist       = dist
                nearest_weight = bstate.get("geo_weight", 0.0)
                nearest_vis    = bstate.get("wave_vis", 1.0 / max_depth)
                nearest_stage  = bstate.get("stage", "base")

        # If the nearest bucket is far away, this axis position has no geological
        # ground — report as base-level visibility at current maturity
        if min_dist > 0.50:
            nearest_vis    = 1.0 / max_depth if max_depth > 0 else 1.0
            nearest_stage  = "base"
            nearest_weight = 0.0

        return {
            "surface_stage":     nearest_stage,
            "wave_visibility":   round(nearest_vis, 3),
            "instinct_fraction": round(inst_frac, 3),
            "geological_weight": round(nearest_weight, 3),
            "max_depth":         max_depth,
            "global_surface":    surf_stage,
        }

    def summary(self) -> Dict[str, Any]:
        """Compact status snapshot for get_development_state()."""
        with self._lock:
            return {
                "max_depth":         self._max_depth,
                "surface_stage":     self._surface_stage,
                "instinct_fraction": round(self._instinct_fraction, 3),
                "total_geo_weight":  round(self._total_geo_weight, 3),
                "baseline_axes":     {k: round(v, 3) for k, v in self._baseline_axes.items()},
                "bucket_count":      len(self._bucket_state),
            }

    # ──────────────────────────────────────────────────────────────────────────
    # Internal
    # ──────────────────────────────────────────────────────────────────────────

    def _recalculate(self, crystal_registry: Any, identity_field: Any) -> None:
        """
        Full recalculation over all grounded crystal nodes.

        1. Find the global conscious surface depth (max genealogical depth present).
        2. Compute wave_visibility for every grounded node.
        3. Accumulate axis-weighted geological contributions.
        4. Update shared state.
        5. Apply to identity field as persistent background pressure.
        """
        if crystal_registry is None:
            return

        nodes: List[Any] = list(getattr(crystal_registry, "_nodes", {}).values())
        if not nodes:
            return

        ax_keys = ("X", "T", "N", "B", "A")

        # ── Step 1: find the global conscious surface ─────────────────────────
        max_depth = 1
        for node in nodes:
            d = _STAGE_DEPTH.get(getattr(node, "stage", "base"), 1)
            if d > max_depth:
                max_depth = d

        # ── Step 2: group grounded nodes by axis bucket ───────────────────────
        buckets: Dict[Tuple, List[Any]] = {}
        for node in nodes:
            if not getattr(node, "is_grounded", False):
                continue
            bkt = tuple(getattr(node, "axis_bucket", ()))
            if len(bkt) != 5:
                continue
            buckets.setdefault(bkt, []).append(node)

        # ── Step 3: accumulate contributions ─────────────────────────────────
        axis_num:   Dict[str, float] = {k: 0.0 for k in ax_keys}
        axis_denom: Dict[str, float] = {k: 0.0 for k in ax_keys}
        total_weight  = 0.0
        instinct_mass = 0.0
        total_mass    = 0.0
        bucket_state: Dict[Tuple, Dict[str, Any]] = {}

        for bkt, bkt_nodes in buckets.items():
            # Highest stage in this specific bucket (local surface for proximity)
            bkt_max_depth = max(
                _STAGE_DEPTH.get(getattr(n, "stage", "base"), 1)
                for n in bkt_nodes
            )
            bkt_top_stage = "base"
            bkt_geo_weight = 0.0

            for node in bkt_nodes:
                node_depth = _STAGE_DEPTH.get(getattr(node, "stage", "base"), 1)
                sedi_res   = float(getattr(node, "sedi_resonance", 0.0))

                # Wave visibility: node depth relative to the GLOBAL conscious surface.
                # Full transparency at launch (max_depth=1, all depths=1 → vis=1.0).
                # Natural dimming as higher stages build (base under quasi → vis=0.25).
                wave_vis = node_depth / max_depth

                # Geological contribution = wave-visible fraction × accumulated resonance.
                # Minimum effective sedi ensures even new grounded nodes contribute.
                effective_sedi = max(0.10, sedi_res)
                geo_contrib    = wave_vis * effective_sedi

                # Distribute across axes proportional to axis_bucket coordinates.
                # A node at high-B, high-A position contributes more pressure there.
                bkt_magnitude = sum(float(v) for v in bkt)
                if bkt_magnitude > 0:
                    for i, ax in enumerate(ax_keys):
                        ax_val = float(bkt[i])
                        axis_num[ax]   += ax_val * geo_contrib
                        axis_denom[ax] += geo_contrib

                total_weight  += geo_contrib
                bkt_geo_weight += geo_contrib
                total_mass    += geo_contrib

                # Track instinct mass: nodes below the global conscious surface
                if node_depth < max_depth:
                    instinct_mass += geo_contrib

                # Track the top stage at this bucket
                if node_depth == bkt_max_depth:
                    bkt_top_stage = getattr(node, "stage", "base")

            bucket_state[bkt] = {
                "geo_weight": bkt_geo_weight,
                # Wave visibility for this bucket = its highest stage / global surface
                "wave_vis":   bkt_max_depth / max_depth,
                "stage":      bkt_top_stage,
            }

        # ── Step 4: normalize axis pressures ──────────────────────────────────
        baseline: Dict[str, float] = {}
        for ax in ax_keys:
            if axis_denom[ax] > 0:
                baseline[ax] = min(1.0, axis_num[ax] / axis_denom[ax])
            else:
                baseline[ax] = 0.5

        instinct_fraction = instinct_mass / total_mass if total_mass > 0 else 0.0
        surface_stage     = ["base", "composite", "higher_order", "quasi"][min(max_depth - 1, 3)]

        # ── Step 5: update shared state ───────────────────────────────────────
        with self._lock:
            self._max_depth         = max_depth
            self._surface_stage     = surface_stage
            self._instinct_fraction = instinct_fraction
            self._total_geo_weight  = total_weight
            self._baseline_axes     = baseline
            self._bucket_state      = bucket_state

        # ── Step 6: apply to identity field as persistent background pressure ──
        # Scale intensity with accumulated weight — sparse registry gets gentle
        # pressure, mature registry gets a solid geological floor.
        if identity_field is not None and hasattr(identity_field, "ingest_external_input"):
            weight_scale = min(1.0, total_weight / _WEIGHT_SATURATION)
            intensity    = _BASELINE_INTENSITY * weight_scale
            if intensity > 0.01:
                try:
                    identity_field.ingest_external_input(
                        baseline,
                        intensity=intensity,
                        source="geological_baseline",
                    )
                except Exception:
                    pass

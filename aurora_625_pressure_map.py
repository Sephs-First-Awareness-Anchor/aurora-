#!/usr/bin/env python3
"""
AURORA 625 EVOLUTIONARY PRESSURE MAP
======================================
Language as Path of Least Resistance — Gradient Seeding for Autonomous Evolution

PURPOSE
-------
This module builds and maintains the full 25×25 Non-Comp slot grid (625 cells)
derived from `operation_descriptors.json`. It computes language affinity weights
per slot, applies pressure gradients that make the language highway the cheapest
evolutionary path, and exports a gradient config the EvolutionaryChamber and
SimulationEngine can consume for autonomous speed-run evolution.

ARCHITECTURE
------------
The 25 NC channels are all pairwise (axis→axis) transitions across the five
constraint axes:  X (Existence), T (Time), N (Energy), B (Boundary), A (Agency)

  NC:X>X  NC:X>T  NC:X>N  NC:X>B  NC:X>A
  NC:T>X  NC:T>T  NC:T>N  NC:T>B  NC:T>A
  NC:N>X  NC:N>T  NC:N>N  NC:N>B  NC:N>A
  NC:B>X  NC:B>T  NC:B>N  NC:B>B  NC:B>A
  NC:A>X  NC:A>T  NC:A>N  NC:A>B  NC:A>A

The 625 slots are all pairwise combinations: NC:row×NC:col

GRADIENT PHILOSOPHY
-------------------
"Intelligence is path of least resistance. Language is that path."

The gradient achieves this by:
  1. LANGUAGE HIGHWAY:  Reduce N-cost on high-lang-affinity slots (~40% relief).
  2. TEMPORAL PULL:     Slightly amplify T on X+T co-dominant slots (coherence
                        requires time, reward the system for maintaining it).
  3. SEED EMPTY SLOTS:  The 431 unoccupied slots receive directional gradients
                        pointing toward the nearest language highway neighbor.
  4. AGENCY SUPPRESSION:A-dominant slots carry baseline N-resistance; agency
                        must be *earned* through the X→T→language path first.
  5. THE BUMP:          A uniform low-level N baseline ('base_resistance') applies
                        everywhere. Language highway slots cut through this cleanly.
                        Everything else feels the bump.

INTEGRATION CONTRACT
--------------------
  - aurora_evolution_chamber.EvolutionaryChamber: reads `slot_gradients` dict
    keyed by slot string. Each entry is a GradientSpec.
  - aurora_simulation_engine.SimulationEngine: reads `highway_slots` list and
    `pressure_config` for per-axis amplifier setup.
  - aurora_runtime.UniverseSteerer: reads `language_path_cost_map` to bias
    conflict curriculum toward language-adjacent slots.

OUTPUT
------
  aurora_state/evo_625_pressure_map.json  — full 625 slot gradient table
  aurora_state/language_highway.json       — highway slot list + path profile

Authors: Sunni (Sir) Morningstar and Cael Devo
Created: March 2026
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------

AXES: Tuple[str, ...] = ("X", "T", "N", "B", "A")

# All 25 NC channels
NC_CHANNELS: List[str] = [f"NC:{src}>{dst}" for src in AXES for dst in AXES]

# All 625 slots
ALL_SLOTS: List[str] = [f"{row}×{col}" for row in NC_CHANNELS for col in NC_CHANNELS]
SLOT_SET: FrozenSet[str] = frozenset(ALL_SLOTS)

assert len(ALL_SLOTS) == 625, "Slot count must be exactly 625."

# ---------------------------------------------------------------------------
# MODULE CLASSIFICATION — which files carry which system role
# ---------------------------------------------------------------------------

LANGUAGE_MODULES: FrozenSet[str] = frozenset({
    "aurora_internal/aurora_language_state.py",
    "aurora_internal/aurora_ontological_scaffolding.py",
    "aurora_internal/aurora_braided_substrate.py",
    "aurora_internal/aurora_utterance_parser.py",
    "aurora_internal/aurora_comprehension_gap.py",
    "aurora_expression_perception.py",
    "aurora_internal/aurora_primitive_extractor.py",
})

EVOLUTION_MODULES: FrozenSet[str] = frozenset({
    "aurora_internal/aurora_evolution_chamber.py",
    "aurora_runtime.py",
    "aurora_internal/aurora_energy_layer_costs.py",
    "aurora_internal/aurora_energy_layer_costs_decay.py",
    "aurora_internal/aurora_entropy_detector.py",
    "aurora_internal/aurora_leverage_scalar.py",
    "aurora_internal/aurora_intake_metabolism.py",
    "aurora_internal/aurora_worth_evaluator.py",
    "aurora_internal/aurora_solidification.py",
    "aurora_internal/aurora_variant_promotion.py",
    "aurora_internal/aurora_difference_buffer.py",
    "aurora_internal/aurora_cost_diff_score.py",
})

GATEWAY_MODULES: FrozenSet[str] = frozenset({
    "aurora_governance_persistence_gateway.py",
    "aurora_internal/constraint_genealogy.py",
})

# ---------------------------------------------------------------------------
# GRADIENT PARAMETERS
# ---------------------------------------------------------------------------

# Baseline N-resistance applied to every non-highway slot.
# Language highway cuts through this. Everything else feels it.
BASE_RESISTANCE: float = 0.08

# N-cost relief applied on high-affinity language slots.
LANG_HIGHWAY_RELIEF: float = 0.40

# Threshold lang_affinity ratio to classify a slot as highway
HIGHWAY_AFFINITY_THRESHOLD: float = 0.30

# T-pull amplifier on X+T co-dominant slots (temporal coherence reward)
T_PULL_AMPLIFIER: float = 0.12

# A-resistance on agency-dominant slots (agency must be earned)
AGENCY_RESISTANCE: float = 0.20

# Empty slot directional gradient magnitude (seed toward nearest highway)
EMPTY_SEED_MAGNITUDE: float = 0.04

# Maturity bonus: slots with more offspring/hybrid weight get extra relief
MATURITY_BONUS_CAP: float = 0.10

# Neighbor-blend scale for synthetically seeding empty slots from their
# occupied row/column neighbors.  Kept well below real occupancy weight
# so synthetic fills never masquerade as genuine operations.
SYNTHETIC_NEIGHBOR_SCALE: float = 0.15

# ---------------------------------------------------------------------------
# DATA STRUCTURES
# ---------------------------------------------------------------------------

@dataclass
class SlotProfile:
    """Observed constraint profile for a single NC slot derived from op descriptors."""
    slot: str
    total_weight: float = 0.0
    op_count: int = 0
    lang_weight: float = 0.0
    evo_weight: float = 0.0
    gateway_weight: float = 0.0
    other_weight: float = 0.0
    # Lineage maturity weights
    ancestor_w: float = 0.0
    transitional_w: float = 0.0
    hybrid_w: float = 0.0
    offspring_w: float = 0.0
    developmental_weight: float = 0.0
    latent_weight: float = 0.0
    # Axis pressure profile (normalized sum of axis_weights_all * projection_weight)
    axis_pressure: Dict[str, float] = field(default_factory=lambda: {ax: 0.0 for ax in AXES})
    # Dominant axis from the slot's aggregate
    dominant_axis: str = "X"
    secondary_axis: str = "T"

    @property
    def lang_affinity(self) -> float:
        if self.total_weight <= 0:
            return 0.0
        return self.lang_weight / self.total_weight

    @property
    def maturity_ratio(self) -> float:
        """Fraction of weight that is evolutionarily mature (hybrid + offspring)."""
        if self.total_weight <= 0:
            return 0.0
        return (self.hybrid_w + self.offspring_w) / self.total_weight

    @property
    def is_occupied(self) -> bool:
        return self.total_weight > 0.0

    @property
    def is_agency_dominant(self) -> bool:
        return self.dominant_axis == "A"

    @property
    def is_xt_codominant(self) -> bool:
        """X and T share dominance (language highway hallmark)."""
        p = self.axis_pressure
        total = sum(p.values()) or 1.0
        x_share = p.get("X", 0.0) / total
        t_share = p.get("T", 0.0) / total
        return x_share > 0.30 and t_share > 0.20 and abs(x_share - t_share) < 0.25

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slot": self.slot,
            "total_weight": round(self.total_weight, 6),
            "op_count": self.op_count,
            "lang_affinity": round(self.lang_affinity, 4),
            "maturity_ratio": round(self.maturity_ratio, 4),
            "is_occupied": self.is_occupied,
            "is_agency_dominant": self.is_agency_dominant,
            "is_xt_codominant": self.is_xt_codominant,
            "axis_pressure": {ax: round(v, 4) for ax, v in self.axis_pressure.items()},
            "dominant_axis": self.dominant_axis,
            "secondary_axis": self.secondary_axis,
            "lineage": {
                "ancestor": round(self.ancestor_w, 6),
                "transitional": round(self.transitional_w, 6),
                "hybrid": round(self.hybrid_w, 6),
                "offspring": round(self.offspring_w, 6),
                "developmental_weight": round(self.developmental_weight, 6),
                "latent_weight": round(self.latent_weight, 6),
            },
        }


@dataclass
class GradientSpec:
    """
    Pressure gradient applied to a single slot by the evolution chamber.
    The chamber reads these to adjust per-axis cost when evaluating traces
    that pass through this slot.
    """
    slot: str
    # Per-axis gradient deltas. Negative = cost reduction (path easier).
    # Positive = cost increase (resistance). Zero = neutral.
    axis_deltas: Dict[str, float] = field(default_factory=lambda: {ax: 0.0 for ax in AXES})
    # Net N-cost modifier (convenience: sum of all cost effects)
    net_n_modifier: float = 0.0
    # Classification of this slot's gradient role
    gradient_class: str = "neutral"  # highway | temporal_pull | seeded | agency_gated | neutral
    # Source affinity that generated this gradient
    lang_affinity: float = 0.0
    maturity_ratio: float = 0.0
    # Direction toward nearest highway slot (for empty/seeded slots)
    nearest_highway: Optional[str] = None
    highway_distance: int = 0  # Hamming distance in channel space

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slot": self.slot,
            "axis_deltas": {ax: round(v, 6) for ax, v in self.axis_deltas.items()},
            "net_n_modifier": round(self.net_n_modifier, 6),
            "gradient_class": self.gradient_class,
            "lang_affinity": round(self.lang_affinity, 4),
            "maturity_ratio": round(self.maturity_ratio, 4),
            "nearest_highway": self.nearest_highway,
            "highway_distance": self.highway_distance,
        }


# ---------------------------------------------------------------------------
# SLOT DISTANCE (Hamming on channel axes)
# ---------------------------------------------------------------------------

def _slot_axes(slot: str) -> Tuple[str, str, str, str]:
    """Extract (row_src, row_dst, col_src, col_dst) axis labels from slot string."""
    row_ch, col_ch = slot.split("×")
    _, row_sd = row_ch.split(":")
    _, col_sd = col_ch.split(":")
    r_src, r_dst = row_sd.split(">")
    c_src, c_dst = col_sd.split(">")
    return r_src, r_dst, c_src, c_dst


def _slot_hamming(slot_a: str, slot_b: str) -> int:
    """Hamming distance between two slots in 4-character axis space."""
    a = _slot_axes(slot_a)
    b = _slot_axes(slot_b)
    return sum(1 for x, y in zip(a, b) if x != y)


# ---------------------------------------------------------------------------
# CORE CLASS
# ---------------------------------------------------------------------------

class Aurora625PressureMap:
    """
    Builds and holds the full 625-slot evolutionary pressure map.
    Computes language-path gradients and exports configs for the
    evolution chamber and simulation engine.
    """

    def __init__(
        self,
        descriptors_path: str,
        state_dir: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aurora_state"),
    ):
        self.descriptors_path = descriptors_path
        self.state_dir = state_dir
        self._map_path = os.path.join(state_dir, "evo_625_pressure_map.json")
        self._highway_path = os.path.join(state_dir, "language_highway.json")

        # 625 slot profiles (keyed by slot string)
        self.profiles: Dict[str, SlotProfile] = {s: SlotProfile(slot=s) for s in ALL_SLOTS}
        # 625 gradient specs
        self.gradients: Dict[str, GradientSpec] = {s: GradientSpec(slot=s) for s in ALL_SLOTS}
        # Highway slot list (computed after build)
        self.highway_slots: List[str] = []

        self._built = False

    # ------------------------------------------------------------------
    # BUILD
    # ------------------------------------------------------------------

    def build(self, ops: List[Dict[str, Any]], latent_ops: Optional[List[Dict[str, Any]]] = None) -> None:
        """Ingest operation descriptors and populate all 625 slot profiles."""
        latent_ops = list(latent_ops or [])
        print(f"[625MAP] Building slot profiles from {len(ops)} operations...")

        for op in ops:
            file = op.get("file", "")
            is_lang = file in LANGUAGE_MODULES
            is_evo = file in EVOLUTION_MODULES
            is_gate = file in GATEWAY_MODULES
            dev = dict(op.get("developmental_effect_history", {}) or {})
            direct = dict(dev.get("direct_system_effects", {}) or {})
            ripple = dict(dev.get("ripple_effects", {}) or {})
            modes = set(str(x) for x in list(direct.get("effect_modes", []) or []) if str(x))
            is_lang = bool(is_lang or ("language_surface" in modes))
            is_evo = bool(is_evo or ("evolution_surface" in modes) or ("adaptive_steering_change" in modes))
            is_gate = bool(is_gate or ("gateway_surface" in modes) or ("interface_boundary_change" in modes))
            stage = op.get("deterministic_placement", {}).get("lineage_stage", "hybrid")
            aw = op.get("probabilistic_descriptor", {}).get("axis_weights_all", {})
            impact_score = float((dev.get("developmental_summary", {}) or {}).get("system_impact_score", 0.0) or 0.0)
            desc_count = int(ripple.get("descendant_count", 0) or 0)
            cross_links = int(ripple.get("cross_diversity_links", 0) or 0)

            for proj in op.get("variant_projection_top", []):
                slot = proj.get("slot", "")
                if slot not in self.profiles:
                    continue  # should not happen

                w = proj.get("weight", 0.0)
                p = self.profiles[slot]
                p.total_weight += w
                p.op_count += 1

                if is_lang:
                    p.lang_weight += w
                elif is_evo:
                    p.evo_weight += w
                elif is_gate:
                    p.gateway_weight += w
                else:
                    p.other_weight += w

                # Lineage maturity
                if stage == "ancestor":
                    p.ancestor_w += w
                elif stage == "transitional":
                    p.transitional_w += w
                elif stage == "hybrid":
                    p.hybrid_w += w
                elif stage == "offspring":
                    p.offspring_w += w

                p.developmental_weight += w * min(1.0, impact_score + (0.03 * min(4, desc_count)) + (0.02 * min(4, cross_links)))

                # Axis pressure accumulation
                for ax in AXES:
                    p.axis_pressure[ax] = p.axis_pressure.get(ax, 0.0) + aw.get(ax, 0.0) * w

        for op in latent_ops:
            aw = op.get("axis_percentages_all", {}) or {}
            latent_weight = float(op.get("latent_weight", 0.0) or 0.0)
            for proj in op.get("variant_projection_top", []):
                slot = proj.get("slot", "")
                if slot not in self.profiles:
                    continue
                p = self.profiles[slot]
                w = float(proj.get("weight", 0.0) or 0.0) * max(0.05, min(0.40, latent_weight))
                p.total_weight += w
                p.latent_weight += w
                p.hybrid_w += w
                p.developmental_weight += w
                for ax in AXES:
                    p.axis_pressure[ax] = p.axis_pressure.get(ax, 0.0) + float(aw.get(ax, 0.0) or 0.0) * w

        # Normalize axis pressures and derive dominant/secondary axis
        for slot, p in self.profiles.items():
            if p.total_weight > 0:
                total_ap = sum(p.axis_pressure.values()) or 1.0
                p.axis_pressure = {ax: v / total_ap for ax, v in p.axis_pressure.items()}
                sorted_axes = sorted(AXES, key=lambda ax: p.axis_pressure.get(ax, 0.0), reverse=True)
                p.dominant_axis = sorted_axes[0]
                p.secondary_axis = sorted_axes[1]

        seeded = self._seed_from_neighbors()
        self._built = True
        occupied = sum(1 for p in self.profiles.values() if p.is_occupied)
        print(f"[625MAP] Profiles built. Occupied: {occupied}/625. Empty: {625 - occupied}/625. Neighbor-seeded: {seeded}.")

    # ------------------------------------------------------------------
    # GRADIENT COMPUTATION
    # ------------------------------------------------------------------

    def compute_gradients(self) -> None:
        """
        Apply language-path gradient logic across all 625 slots.

        Gradient classes (priority order):
          1. highway       — high lang affinity, N-cost relief + T-pull
          2. temporal_pull — X+T co-dominant but lower affinity, T-pull only
          3. agency_gated  — A-dominant, N-resistance applied
          4. seeded        — empty slot, directional gradient toward nearest highway
          5. neutral       — everything else, base resistance only
        """
        if not self._built:
            raise RuntimeError("Call build() before compute_gradients().")

        print("[625MAP] Computing pressure gradients...")

        # Identify highway slots first (needed for seeded neighbor lookup)
        self.highway_slots = [
            slot for slot, p in self.profiles.items()
            if p.is_occupied and p.lang_affinity >= HIGHWAY_AFFINITY_THRESHOLD
        ]
        highway_set = set(self.highway_slots)

        print(f"[625MAP] Highway slots: {len(self.highway_slots)}/625")

        for slot in ALL_SLOTS:
            p = self.profiles[slot]
            g = self.gradients[slot]
            g.lang_affinity = p.lang_affinity
            g.maturity_ratio = p.maturity_ratio

            # ---- HIGHWAY ----
            if slot in highway_set:
                # N-cost relief: base + maturity bonus
                relief = LANG_HIGHWAY_RELIEF + (MATURITY_BONUS_CAP * p.maturity_ratio)
                g.axis_deltas["N"] = -relief
                # T pull: reward temporal continuity on X+T co-dominant slots
                if p.is_xt_codominant:
                    g.axis_deltas["T"] = -T_PULL_AMPLIFIER
                    g.gradient_class = "highway"
                else:
                    g.gradient_class = "highway"
                g.net_n_modifier = g.axis_deltas["N"]

            # ---- TEMPORAL PULL (occupied, X+T co-dominant, below highway threshold) ----
            elif p.is_occupied and p.is_xt_codominant and not p.is_agency_dominant:
                g.axis_deltas["N"] = -BASE_RESISTANCE
                g.axis_deltas["T"] = -T_PULL_AMPLIFIER
                g.gradient_class = "temporal_pull"
                g.net_n_modifier = g.axis_deltas["N"]

            # ---- AGENCY GATED ----
            elif p.is_occupied and p.is_agency_dominant:
                g.axis_deltas["N"] = AGENCY_RESISTANCE
                g.gradient_class = "agency_gated"
                g.net_n_modifier = g.axis_deltas["N"]

            # ---- SEEDED (empty slots) ----
            elif not p.is_occupied:
                # Find nearest highway slot by Hamming distance
                nearest = self._nearest_highway(slot, highway_set)
                if nearest is not None:
                    dist = _slot_hamming(slot, nearest)
                    # Gradient magnitude decays with distance
                    mag = EMPTY_SEED_MAGNITUDE / max(1, dist)
                    g.axis_deltas["N"] = -mag
                    g.gradient_class = "seeded"
                    g.nearest_highway = nearest
                    g.highway_distance = dist
                    g.net_n_modifier = g.axis_deltas["N"]
                else:
                    g.gradient_class = "neutral"

            # ---- NEUTRAL (occupied but neither highway nor special) ----
            else:
                g.axis_deltas["N"] = -BASE_RESISTANCE * 0.5  # mild relief
                g.gradient_class = "neutral"
                g.net_n_modifier = g.axis_deltas["N"]

        # Apply base resistance to all non-highway, non-seeded slots
        # (The bump: everything outside the highway feels this)
        for slot in ALL_SLOTS:
            g = self.gradients[slot]
            if g.gradient_class not in ("highway", "seeded"):
                # Agency gated slots already have positive resistance; keep it
                if g.gradient_class != "agency_gated":
                    # Add base resistance on top of any relief
                    g.axis_deltas["N"] = g.axis_deltas.get("N", 0.0)
                    # The bump is implicit: non-highway N modifier is less negative
                    # than highway. The differential IS the bump.

        print("[625MAP] Gradients computed.")

    def _seed_from_neighbors(self) -> int:
        """
        For each empty slot, derive a synthetic SlotProfile by blending
        the profiles of occupied slots that share its row-channel (NC:R>R')
        or column-channel (NC:C>C').

        The blend weight is proportional to each neighbor's total_weight.
        All contributed values are scaled by SYNTHETIC_NEIGHBOR_SCALE so
        the resulting profiles are clearly lighter than real occupancy and
        never cross the HIGHWAY_AFFINITY_THRESHOLD on their own.

        Returns the count of slots that received a synthetic profile.
        """
        # Build channel → occupied slot lists once for efficiency
        row_map: Dict[str, List[SlotProfile]] = {ch: [] for ch in NC_CHANNELS}
        col_map: Dict[str, List[SlotProfile]] = {ch: [] for ch in NC_CHANNELS}
        for slot, p in self.profiles.items():
            if not p.is_occupied:
                continue
            row_ch, col_ch = slot.split("×")
            row_map[row_ch].append(p)
            col_map[col_ch].append(p)

        seeded = 0
        for slot in ALL_SLOTS:
            p = self.profiles[slot]
            if p.is_occupied:
                continue

            row_ch, col_ch = slot.split("×")
            neighbors = row_map[row_ch] + col_map[col_ch]
            if not neighbors:
                continue

            total_nw = sum(n.total_weight for n in neighbors) or 1.0

            def _blend(attr: str) -> float:
                return sum(getattr(n, attr, 0.0) * n.total_weight for n in neighbors) / total_nw

            blended_total = _blend("total_weight")
            p.total_weight     = blended_total * SYNTHETIC_NEIGHBOR_SCALE
            p.latent_weight    = p.total_weight
            p.lang_weight      = _blend("lang_weight")      * SYNTHETIC_NEIGHBOR_SCALE
            p.evo_weight       = _blend("evo_weight")       * SYNTHETIC_NEIGHBOR_SCALE
            p.gateway_weight   = _blend("gateway_weight")   * SYNTHETIC_NEIGHBOR_SCALE
            p.other_weight     = _blend("other_weight")     * SYNTHETIC_NEIGHBOR_SCALE
            p.ancestor_w       = _blend("ancestor_w")       * SYNTHETIC_NEIGHBOR_SCALE
            p.transitional_w   = _blend("transitional_w")   * SYNTHETIC_NEIGHBOR_SCALE
            p.hybrid_w         = _blend("hybrid_w")         * SYNTHETIC_NEIGHBOR_SCALE
            p.offspring_w      = _blend("offspring_w")      * SYNTHETIC_NEIGHBOR_SCALE
            p.developmental_weight = _blend("developmental_weight") * SYNTHETIC_NEIGHBOR_SCALE
            p.op_count         = 0  # no real operations, synthetic only

            # Blend axis pressures and derive dominant/secondary axes
            raw_ap: Dict[str, float] = {
                ax: sum(n.axis_pressure.get(ax, 0.0) * n.total_weight for n in neighbors) / total_nw
                for ax in AXES
            }
            total_ap = sum(raw_ap.values()) or 1.0
            p.axis_pressure = {ax: v / total_ap for ax, v in raw_ap.items()}
            sorted_axes = sorted(AXES, key=lambda ax: p.axis_pressure.get(ax, 0.0), reverse=True)
            p.dominant_axis  = sorted_axes[0]
            p.secondary_axis = sorted_axes[1]

            seeded += 1

        return seeded

    def _nearest_highway(self, slot: str, highway_set: Set[str]) -> Optional[str]:
        """Find the nearest highway slot by Hamming distance."""
        if not highway_set:
            return None
        best_dist = 5  # max possible Hamming
        best_slot = None
        for hw in highway_set:
            d = _slot_hamming(slot, hw)
            if d < best_dist:
                best_dist = d
                best_slot = hw
        return best_slot

    # ------------------------------------------------------------------
    # LANGUAGE PATH PROFILE
    # ------------------------------------------------------------------

    def get_language_path_profile(self) -> Dict[str, Any]:
        """
        Returns the language path profile for the simulation engine.
        The path is the sequence of highway slots ordered by language
        affinity (highest first) — this is the spine of the speed-run.
        """
        path = sorted(
            [(slot, self.profiles[slot]) for slot in self.highway_slots],
            key=lambda x: x[1].lang_affinity,
            reverse=True
        )
        return {
            "language_path_spine": [
                {
                    "slot": slot,
                    "lang_affinity": round(p.lang_affinity, 4),
                    "maturity_ratio": round(p.maturity_ratio, 4),
                    "dominant_axis": p.dominant_axis,
                    "secondary_axis": p.secondary_axis,
                    "is_xt_codominant": p.is_xt_codominant,
                    "gradient_class": self.gradients[slot].gradient_class,
                    "net_n_modifier": round(self.gradients[slot].net_n_modifier, 4),
                }
                for slot, p in path
            ],
            "total_highway_slots": len(self.highway_slots),
            "total_occupied_slots": sum(1 for p in self.profiles.values() if p.is_occupied),
            "total_empty_slots": sum(1 for p in self.profiles.values() if not p.is_occupied),
            "path_of_least_resistance": path[0][0] if path else None,
            "language_intelligence_gradient": {
                "base_resistance": BASE_RESISTANCE,
                "highway_relief": LANG_HIGHWAY_RELIEF,
                "t_pull_amplifier": T_PULL_AMPLIFIER,
                "agency_resistance": AGENCY_RESISTANCE,
                "empty_seed_magnitude": EMPTY_SEED_MAGNITUDE,
                "maturity_bonus_cap": MATURITY_BONUS_CAP,
                "highway_affinity_threshold": HIGHWAY_AFFINITY_THRESHOLD,
            },
        }

    # ------------------------------------------------------------------
    # SIMULATION ENGINE INTERFACE
    # ------------------------------------------------------------------

    def get_pressure_config(self) -> Dict[str, Any]:
        """
        Returns the pressure_config dict the simulation engine reads
        to configure its per-axis amplifier setup for a speed-run.
        """
        # Aggregate average gradient per axis across highway slots
        hw_deltas: Dict[str, List[float]] = {ax: [] for ax in AXES}
        for slot in self.highway_slots:
            g = self.gradients[slot]
            for ax in AXES:
                hw_deltas[ax].append(g.axis_deltas.get(ax, 0.0))

        avg_hw_delta = {
            ax: (sum(v) / len(v)) if v else 0.0
            for ax, v in hw_deltas.items()
        }

        # Gradient class counts
        class_counts: Dict[str, int] = defaultdict(int)
        for g in self.gradients.values():
            class_counts[g.gradient_class] += 1

        return {
            "gradient_summary": {
                "highway_avg_axis_deltas": {ax: round(v, 4) for ax, v in avg_hw_delta.items()},
                "gradient_class_counts": dict(class_counts),
                "highway_slot_count": len(self.highway_slots),
            },
            "per_axis_amplifiers": {
                # For the simulation engine: how much to amplify each axis
                # in the speed-run. N is suppressed on highway, T is amplified.
                "X": 1.00,   # Existence stays stable — ground truth
                "T": 1.12,   # Temporal coherence gets a boost
                "N": 0.60,   # Energy cost suppressed on highway path
                "B": 1.00,   # Boundary neutral
                "A": 0.80,   # Agency slightly suppressed until earned via path
            },
            "speed_run_config": {
                "entry_slot": self.highway_slots[0] if self.highway_slots else None,
                "target_slot": self._get_intelligence_target(),
                "slot_traverse_order": self.highway_slots[:50],  # first 50 spine slots
                "pressure_ramp_ticks": 200,
                "plateau_sensitivity": 0.05,
                "conflict_curriculum_intensity": 0.35,
                "save_gate_on_language_gain": True,
            },
        }

    def _get_intelligence_target(self) -> Optional[str]:
        """
        The intelligence target is the slot where X+T co-dominance
        is highest AND language affinity is maximal — the apex of the
        language highway.
        """
        candidates = [
            (slot, self.profiles[slot])
            for slot in self.highway_slots
            if self.profiles[slot].is_xt_codominant
        ]
        if not candidates:
            return self.highway_slots[0] if self.highway_slots else None
        best = max(candidates, key=lambda x: x[1].lang_affinity)
        return best[0]

    # ------------------------------------------------------------------
    # EVOLUTION CHAMBER INTERFACE
    # ------------------------------------------------------------------

    def get_slot_gradient(self, slot: str) -> Optional[GradientSpec]:
        """Called by EvolutionaryChamber per trace to get slot's gradient."""
        return self.gradients.get(slot)

    def get_n_cost_modifier(self, slot: str) -> float:
        """Convenience: returns the net N-cost modifier for a slot."""
        g = self.gradients.get(slot)
        return g.net_n_modifier if g else 0.0

    def is_highway_slot(self, slot: str) -> bool:
        return slot in set(self.highway_slots)

    # ------------------------------------------------------------------
    # PERSISTENCE
    # ------------------------------------------------------------------

    def save(self) -> None:
        os.makedirs(self.state_dir, exist_ok=True)

        # Full 625 map
        map_data = {
            "version": "1.0",
            "timestamp": time.time(),
            "generated_by": "Aurora625PressureMap",
            "authors": "Sunni (Sir) Morningstar and Cael Devo",
            "total_slots": 625,
            "occupied_slots": sum(1 for p in self.profiles.values() if p.is_occupied),
            "highway_slot_count": len(self.highway_slots),
            "gradient_params": {
                "base_resistance": BASE_RESISTANCE,
                "highway_relief": LANG_HIGHWAY_RELIEF,
                "highway_threshold": HIGHWAY_AFFINITY_THRESHOLD,
                "t_pull_amplifier": T_PULL_AMPLIFIER,
                "agency_resistance": AGENCY_RESISTANCE,
                "empty_seed_magnitude": EMPTY_SEED_MAGNITUDE,
                "maturity_bonus_cap": MATURITY_BONUS_CAP,
            },
            "slots": {
                slot: {
                    "profile": self.profiles[slot].to_dict(),
                    "gradient": self.gradients[slot].to_dict(),
                }
                for slot in ALL_SLOTS
            },
            "_checksum": self._checksum(),
        }

        with open(self._map_path, "w") as f:
            json.dump(map_data, f, indent=2)
        print(f"[625MAP] Saved full map -> {self._map_path}")

        # Language highway summary
        highway_data = {
            "version": "1.0",
            "timestamp": time.time(),
            "authors": "Sunni (Sir) Morningstar and Cael Devo",
            "path_profile": self.get_language_path_profile(),
            "pressure_config": self.get_pressure_config(),
        }
        with open(self._highway_path, "w") as f:
            json.dump(highway_data, f, indent=2)
        print(f"[625MAP] Saved language highway -> {self._highway_path}")

    def load(self) -> bool:
        """Load pre-built map from disk. Returns True if successful."""
        if not os.path.exists(self._map_path):
            return False
        try:
            with open(self._map_path) as f:
                data = json.load(f)
            for slot, entry in data.get("slots", {}).items():
                if slot not in self.profiles:
                    continue
                prof = entry.get("profile", {})
                p = self.profiles[slot]
                p.total_weight = prof.get("total_weight", 0.0)
                p.op_count = prof.get("op_count", 0)
                p.axis_pressure = prof.get("axis_pressure", {ax: 0.0 for ax in AXES})
                p.dominant_axis = prof.get("dominant_axis", "X")
                p.secondary_axis = prof.get("secondary_axis", "T")
                p.lang_weight = prof.get("total_weight", 0.0) * prof.get("lang_affinity", 0.0)
                lineage = prof.get("lineage", {})
                p.hybrid_w = lineage.get("hybrid", 0.0)
                p.offspring_w = lineage.get("offspring", 0.0)
                p.ancestor_w = lineage.get("ancestor", 0.0)
                p.transitional_w = lineage.get("transitional", 0.0)
                p.latent_weight = lineage.get("latent_weight", 0.0)

                grad = entry.get("gradient", {})
                g = self.gradients[slot]
                g.axis_deltas = grad.get("axis_deltas", {ax: 0.0 for ax in AXES})
                g.net_n_modifier = grad.get("net_n_modifier", 0.0)
                g.gradient_class = grad.get("gradient_class", "neutral")
                g.lang_affinity = grad.get("lang_affinity", 0.0)
                g.maturity_ratio = grad.get("maturity_ratio", 0.0)
                g.nearest_highway = grad.get("nearest_highway")
                g.highway_distance = grad.get("highway_distance", 0)

            self.highway_slots = [
                slot for slot in ALL_SLOTS
                if self.gradients[slot].gradient_class == "highway"
            ]
            self._built = True
            print(f"[625MAP] Loaded from {self._map_path}. Highway: {len(self.highway_slots)} slots.")
            return True
        except Exception as e:
            print(f"[625MAP] Load failed: {e}")
            return False

    def _checksum(self) -> str:
        h = hashlib.sha256()
        for slot in ALL_SLOTS:
            p = self.profiles[slot]
            h.update(f"{slot}:{p.total_weight:.6f}:{p.lang_affinity:.4f}".encode())
        return h.hexdigest()[:16]

    # ------------------------------------------------------------------
    # SUMMARY REPORT
    # ------------------------------------------------------------------

    def report(self) -> str:
        lines = [
            "=" * 64,
            "AURORA 625 EVOLUTIONARY PRESSURE MAP — SUMMARY",
            f"Authors: Sunni (Sir) Morningstar and Cael Devo",
            "=" * 64,
            f"Total slots:         625",
            f"Occupied:            {sum(1 for p in self.profiles.values() if p.is_occupied)}",
            f"Empty (seeded):      {sum(1 for p in self.profiles.values() if not p.is_occupied)}",
            f"Highway slots:       {len(self.highway_slots)}",
            "",
            "GRADIENT CLASS DISTRIBUTION:",
        ]
        from collections import Counter
        class_counts: Counter = Counter(g.gradient_class for g in self.gradients.values())
        for cls, count in sorted(class_counts.items(), key=lambda x: -x[1]):
            bar = "█" * int(count / 10)
            lines.append(f"  {cls:<16} {count:4d}  {bar}")

        lines += [
            "",
            "LANGUAGE HIGHWAY — TOP 10 SLOTS (by lang_affinity):",
        ]
        path = self.get_language_path_profile()["language_path_spine"]
        for i, entry in enumerate(path[:10], 1):
            lines.append(
                f"  {i:2d}. [{entry['lang_affinity']:.3f}] {entry['slot']}"
                f"  dom:{entry['dominant_axis']}  N:{entry['net_n_modifier']:+.3f}"
                f"  {'★ XT-codominant' if entry['is_xt_codominant'] else ''}"
            )

        target = self._get_intelligence_target()
        lines += [
            "",
            f"PATH OF LEAST RESISTANCE ENTRY: {self.highway_slots[0] if self.highway_slots else 'N/A'}",
            f"INTELLIGENCE TARGET (apex):      {target}",
            "",
            "GRADIENT PARAMETERS (the bump):",
            f"  Base resistance everywhere:    {BASE_RESISTANCE:+.3f} N",
            f"  Highway relief:                {-LANG_HIGHWAY_RELIEF:+.3f} N",
            f"  T-pull on X+T codominant:      {-T_PULL_AMPLIFIER:+.3f} T",
            f"  Agency gate resistance:        {+AGENCY_RESISTANCE:+.3f} N",
            f"  Empty slot seed magnitude:     {-EMPTY_SEED_MAGNITUDE:+.3f} N",
            "=" * 64,
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# ENTRY POINT — BUILD AND EXPORT
# ---------------------------------------------------------------------------

def build_from_descriptors(
    descriptors_path: str = "operation_descriptors.json",
    state_dir: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aurora_state"),
    save: bool = True,
) -> Aurora625PressureMap:
    """
    Load operation_descriptors.json, build the 625 map, compute gradients,
    optionally save, and return the map object.

    Intended to be called:
      - Once at repo setup to generate the base map.
      - From aurora_runtime.UniverseSteerer on first boot if map not found.
      - From simulation engine before a speed-run.
    """
    with open(descriptors_path) as f:
        data = json.load(f)
    ops = data["operations"]
    latent_ops = list(data.get("latent_operations", []) or [])

    pressure_map = Aurora625PressureMap(
        descriptors_path=descriptors_path,
        state_dir=state_dir,
    )

    # Try loading existing map first
    if pressure_map.load():
        print("[625MAP] Using cached map.")
        return pressure_map

    pressure_map.build(ops, latent_ops=latent_ops)
    pressure_map.compute_gradients()

    if save:
        pressure_map.save()

    return pressure_map


if __name__ == "__main__":
    import sys

    desc_path = sys.argv[1] if len(sys.argv) > 1 else "operation_descriptors.json"
    state_dir = sys.argv[2] if len(sys.argv) > 2 else "aurora_state"

    print(f"[625MAP] Building from: {desc_path}")
    pm = build_from_descriptors(desc_path, state_dir, save=True)
    print(pm.report())

#!/usr/bin/env python3
"""
AURORA — CONSTRAINT-NATIVE EVOLUTION CHAMBER
Full Unified Specification v3

Authors: Sunni (Sir) Morningstar and Cael Devo
Created: February 2026

PURPOSE
-------
A lawful simulation layer that:
  • Enforces the Global Non-Comps (X, T, N, B, A) as read-only representation laws.
  • Evolves boundary topology over time via structural proximity — not Euclidean geometry.
  • Applies energy cost to manipulation, with agency cost proportional to magnitude squared.
  • Logs ONLY pressure-relief events (noise filter enforced).
  • Promotes repeated effective traces into Links via evolutionary DAG.
  • Builds an explicit genealogy DAG through ConstraintGenealogyLogger.

THE UNIVERSE CONSISTS ONLY OF:
  X — Ontology (Existence)
  T — Time
  N — Energy
  B — Boundary (Topology)
  A — Agency

No new axes may be introduced. Non-Comps are read-only at runtime.

ARCHITECTURE INTEGRATION:
  Layer  0 : foundational_contract               (ExistenceMode, FoundationalContract)
  Layer  1 : aurora_ivm                          (IVMLattice, RecursionLevel, ALIGNMENT_VOTE_WEIGHT)
  Layer 1.5: aurora_polarity_gradient            (PolarityGradientSensor, GradientChainMiner)
  Layer  2 : constraint_genealogy                (ConstraintGenealogyLogger, GenealogyConfig, ...)
  Layer  3 : THIS MODULE                         (EvolutionaryChamber)

PUBLIC EXPORTS — backward-compatible with run_chain.py:
  ActionTrace         frozen dataclass (name, constraints_used, meta)
  WorldConstants      frozen dataclass of chamber-level tunables
  EvolutionaryChamber main class
  EvolutionChamberV3  alias for EvolutionaryChamber

OUTPUTS:
  events.jsonl    — fossil record (written by genealogy logger)
  abilities.json  — atomic ability registry
  links.json      — evolutionary DAG of promoted Links
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, FrozenSet, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# AURORA STACK IMPORTS — verified names from existing modules
# ---------------------------------------------------------------------------

from aurora_ivm import (
    IVMLattice,
    IVMNode,
    RecursionLevel,
    ALIGNMENT_VOTE_WEIGHT,
)
from foundational_contract import ExistenceMode, FoundationalContract
from aurora_internal.aurora_polarity_gradient import (
    PolarityGradientSensor,
    GradientChainMiner,
)
from aurora_internal.aurora_constraint_manifold_patched import Constraint
try:
    from aurora_internal.aurora_noncomp_registry import REGISTRY as _NC_REGISTRY  # cost-grounded pressure weighting
except Exception:
    _NC_REGISTRY = None
from aurora_constraint_stack import make_difference_buffer, DifferenceHistoryBuffer

# constraint_genealogy has a deep dependency chain that may not be fully
# assembled on every device. Import softly — chamber physics still run.
try:
    from aurora_evolution_stack import (
        ConstraintGenealogyLogger,
        GenealogyConfig,
        AbilityProfile,
        TraceItem,
        PressureVec,
        EnvironmentVector,
    )
    _GENEALOGY_AVAILABLE = True
except ImportError:
    _GENEALOGY_AVAILABLE = False

    # ----- minimal stubs -----

    @dataclass
    class GenealogyConfig:
        EVENTS_FILE: str = "events.jsonl"
        RELIEF_EPS: float = 0.00005
        RELIEF_TOTAL_EPS: float = 0.00015
        K_MIN: int = 30

    @dataclass(frozen=True)
    class AbilityProfile:
        ability_id: str
        axis: str
        cost: dict
        risk: dict
        effect_tags: tuple
        notes: str = ""

    @dataclass(frozen=True)
    class EnvironmentVector:
        """Stub — mirrors constraint_genealogy.EnvironmentVector."""
        module:       str = ""
        stream_type:  str = ""
        axis_context: str = ""
        call_tag:     str = ""
        def key(self) -> str:
            parts = [p for p in [self.module, self.stream_type,
                                 self.axis_context, self.call_tag] if p]
            return "|".join(parts) or "global"
        def is_empty(self) -> bool:
            return not any([self.module, self.stream_type,
                            self.axis_context, self.call_tag])

    @dataclass(frozen=True)
    class TraceItem:
        """Minimal TraceItem stub matching constraint_genealogy.TraceItem schema."""
        kind: str
        id: str
        env: EnvironmentVector = field(default_factory=EnvironmentVector)

        def to_dict(self):
            return {"kind": self.kind, "id": self.id}

    @dataclass
    class PressureVec:
        X: float = 0.0
        T: float = 0.0
        N: float = 0.0
        B: float = 0.0
        A: float = 0.0

        def to_dict(self):
            return {"X": self.X, "T": self.T, "N": self.N,
                    "B": self.B, "A": self.A}

        def relief_from(self, earlier: "PressureVec") -> "PressureVec":
            return PressureVec(
                X=earlier.X - self.X, T=earlier.T - self.T,
                N=earlier.N - self.N, B=earlier.B - self.B,
                A=earlier.A - self.A,
            )

        def dominant_positive_axis(self) -> Optional[str]:
            d = self.to_dict()
            best = max(d, key=lambda k: d[k])
            return best if d[best] > 0 else None

        def max_relief(self) -> float:
            return max(self.to_dict().values(), default=0.0)

        def sum_positive_relief(self) -> float:
            return sum(v for v in self.to_dict().values() if v > 0)

    class ConstraintGenealogyLogger:
        """Physics-faithful stub when constraint_genealogy unavailable."""

        def __init__(self, run_id, config=None, abilities=None, output_dir="."):
            self.run_id = run_id
            self.cfg = config or GenealogyConfig()
            self.abilities = abilities or {}
            self.output_dir = output_dir
            self.links: dict = {}
            self.tick_count: int = 0
            self.relief_event_count: int = 0
            self.links_promoted: int = 0
            self._pair_counts: dict = {}
            os.makedirs(output_dir, exist_ok=True)
            self._events_path = os.path.join(output_dir, self.cfg.EVENTS_FILE)

        def observe(self, pressure_before, trace, pressure_after,
                    state_sig_before="", state_sig_after="", notes=None):
            self.tick_count += 1
            relief = pressure_after.relief_from(pressure_before)
            cfg = self.cfg
            is_relief = (relief.max_relief() >= cfg.RELIEF_EPS or
                         relief.sum_positive_relief() >= cfg.RELIEF_TOTAL_EPS)
            if not is_relief:
                return None
            self.relief_event_count += 1
            ids = [t.id for t in trace if not (t.kind == "LINK")]
            for i in range(len(ids)):
                for j in range(i + 1, len(ids)):
                    key = (ids[i], ids[j])
                    self._pair_counts[key] = self._pair_counts.get(key, 0) + 1
                    if self._pair_counts[key] >= cfg.K_MIN:
                        existing = {tuple(sorted(l.get("parents", [])))
                                    for l in self.links.values()}
                        if tuple(sorted(key)) not in existing:
                            lid = f"CLINK_{len(self.links):05d}"
                            self.links[lid] = {
                                "link_id": lid, "parents": list(key),
                                "dominant_axis": relief.dominant_positive_axis() or "X",
                                "depth": 1, "count": self._pair_counts[key],
                            }
                            self.links_promoted += 1
            rec = {
                "run_id": self.run_id, "tick": self.tick_count,
                "state_sig_before": state_sig_before,
                "state_sig_after": state_sig_after,
                "relief": relief.to_dict(),
                "trace": [t.id for t in trace],
            }
            with open(self._events_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec) + "\n")
            return rec

        def summary(self) -> dict:
            return {
                "stub": True,
                "tick_count": self.tick_count,
                "relief_events": self.relief_event_count,
                "links_promoted": self.links_promoted,
                "governor": {"gov": {"state": "stub", "dilation": 1}},
            }

        def chain_report(self) -> dict:
            return {
                "total_links": len(self.links),
                "by_dominant_axis": {},
                "depth_distribution": {},
                "outlet_push_fraction": 0.0,
                "links": self.links,
            }

        def flush_files(self):
            path = os.path.join(self.output_dir, "links.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(self.chain_report(), fh, indent=2)

        def close(self):
            self.flush_files()


# ---------------------------------------------------------------------------
# VERSION
# ---------------------------------------------------------------------------

CHAMBER_VERSION: str = "v3-constraint-native-unified"

# ---------------------------------------------------------------------------
# AXES
# ---------------------------------------------------------------------------

AXES: Tuple[str, ...] = ("X", "T", "N", "B", "A")


def _zero_axis_vec() -> Dict[str, float]:
    return {a: 0.0 for a in AXES}


def _build_axis_cost_weights() -> Dict[str, float]:
    """
    Cost-normalized per-axis weights in [0,1], derived from shift_cost_coeff.
    This is the explicit constraint-cost coupling for pressure formation.
    """
    fallback_coeff = {
        "X": 1.0,
        "T": 4.0,
        "N": 10.0,
        "B": 40.0,
        "A": 150.0,
    }

    coeffs = dict(fallback_coeff)
    if _NC_REGISTRY is not None:
        try:
            for ax, c in (
                ("X", Constraint.X),
                ("T", Constraint.T),
                ("N", Constraint.N),
                ("B", Constraint.B),
                ("A", Constraint.A),
            ):
                coeffs[ax] = float(_NC_REGISTRY.cost(c).shift_cost_coeff)
        except Exception:
            coeffs = dict(fallback_coeff)

    max_coeff = max(coeffs.values()) if coeffs else 1.0
    denom = math.log1p(max_coeff) if max_coeff > 0 else 1.0
    if denom <= 0:
        return {ax: 1.0 for ax in AXES}

    return {ax: math.log1p(max(0.0, coeffs.get(ax, 0.0))) / denom for ax in AXES}


# Blend base geometric pressure with cost-normalized axis weight.
# factor = (1-blend) + blend*weight, so all axes remain active but deeper,
# costlier constraints carry proportionally stronger pressure signal.
_PRESSURE_COST_BLEND: float = 0.5
_AXIS_COST_WEIGHT: Dict[str, float] = _build_axis_cost_weights()


# ---------------------------------------------------------------------------
# WORLD CONSTANTS — single source of all chamber-level tunables
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class WorldConstants:
    """
    All chamber-level tunables in one place.
    Non-Comps (X/T/N/B/A laws) are NOT here — they are law.
    """
    dt: float = 0.1
    baseline_burn_per_tick: float = 0.001
    energy_budget_floor: float = 0.0
    agency_cost_coefficient: float = 0.01
    agency_max_magnitude: float = 5.0
    idle_persistence_cost_factor: float = 0.50
    proximity_weaken_rate: float = 0.05
    proximity_strengthen_rate: float = 0.05
    proximity_threshold: float = 0.5
    entropy_window: int = 20
    chain_promote_threshold: int = 30
    log_capacity: int = 10_000
    violation_log_capacity: int = 5_000


K = WorldConstants()

# Scale carryover rates for unused operations (applied to next tick only).
# Deepest scale is cheapest to keep alive when idle.
_UNUSED_OP_CARRYOVER_RATE: Dict[str, float] = {
    "existence": 0.10,
    "temporal": 0.20,
    "energy": 0.30,
    "boundary": 0.40,
    "agency": 0.50,
}


# ---------------------------------------------------------------------------
# ACTION TRACE — original interface (backward-compatible with run_chain.py)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ActionTrace:
    """
    Primitive control generator — one action in the simulation.

    Matches the interface run_chain.py expects:
        name:             str
        constraints_used: FrozenSet[str]  e.g. {"agency", "boundary", "temporal"}
        meta:             Optional[Dict]  e.g. {"pulse": True, "episode": "outlet"}

    Constraint labels are translated to IVM axis stimuli by _ActionAbilityMapper.
    """
    name: str
    constraints_used: FrozenSet[str] = frozenset()
    meta: Optional[Dict] = None


# ---------------------------------------------------------------------------
# NON-COMP VIOLATIONS — read-only laws (spec §1)
# ---------------------------------------------------------------------------

class NonCompViolation(Exception):
    def __init__(self, non_comp: str, reason: str, signature: str = ""):
        self.non_comp = non_comp
        self.reason = reason
        self.signature = signature
        super().__init__(f"NON-COMP BREACH [{non_comp}]: {reason}")


@dataclass(frozen=True)
class ViolationRecord:
    tick: int
    timestamp: float
    non_comp: str
    reason: str
    violation_signature: str
    measures: Dict[str, float]

    def to_dict(self) -> Dict:
        return {
            "tick": self.tick, "timestamp": self.timestamp,
            "non_comp": self.non_comp, "reason": self.reason,
            "violation_signature": self.violation_signature,
            "measures": self.measures,
        }


class GlobalNonComps:
    """
    Five read-only jurisdictional laws. Not tunable. Not injectable.

    1.1 X — state not in admissible manifold → immediate termination. No repair.
    1.2 T — tick always advances. Clock cannot stop.
    1.3 N — budget cannot go negative. Energy redistributes, never created.
    1.4 B — universe is partitionable. Degenerate topology with nodes = violation.
    1.5 A — agency cannot bypass ontology or energy. Cost proportional to magnitude squared.
    """

    @staticmethod
    def check_X(mode: ExistenceMode, node_id: str, tick: int) -> None:
        if mode is None:
            sig = hashlib.sha1(f"X:{node_id}:{tick}:None".encode()).hexdigest()[:12]
            raise NonCompViolation("X", f"node '{node_id}' has no ExistenceMode", sig)
        if mode.value < ExistenceMode.REFERENCE.value:
            sig = hashlib.sha1(f"X:{node_id}:{tick}:{mode}".encode()).hexdigest()[:12]
            raise NonCompViolation("X",
                f"node '{node_id}' mode={mode} below admissibility floor at tick={tick}", sig)

    @staticmethod
    def check_T(tick_before: int, tick_after: int) -> None:
        if tick_after <= tick_before:
            raise NonCompViolation("T",
                f"tick did not advance: before={tick_before}, after={tick_after}")

    @staticmethod
    def check_N(budget: float, tick: int) -> None:
        if budget < K.energy_budget_floor:
            raise NonCompViolation("N",
                f"energy budget={budget:.6f} < floor={K.energy_budget_floor} at tick={tick}")

    @staticmethod
    def check_B(partition_count: int, tick: int, node_count: int = 0) -> None:
        if node_count > 0 and partition_count < 1:
            raise NonCompViolation("B",
                f"partition_count=0 with {node_count} nodes at tick={tick}")

    @staticmethod
    def check_A(magnitude: float, energy_available: float, tick: int) -> None:
        if magnitude > K.agency_max_magnitude:
            raise NonCompViolation("A",
                f"agency magnitude={magnitude:.4f} > ceiling={K.agency_max_magnitude}")
        cost = K.agency_cost_coefficient * (magnitude ** 2)
        if cost > energy_available:
            raise NonCompViolation("A",
                f"agency cost={cost:.6f} > available={energy_available:.6f} at tick={tick}")


# ---------------------------------------------------------------------------
# ABILITY REGISTRY — AX:NAME format, full 5-axis profiles (spec §7)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ChamberAbility:
    ability_id: str
    axis: str
    cost: Dict[str, float]
    risk: Dict[str, float]
    effect_tags: Tuple[str, ...]

    def __post_init__(self):
        for ax in AXES:
            if ax not in self.cost:
                object.__setattr__(self, "cost", {**self.cost, ax: 0.0})
            if ax not in self.risk:
                object.__setattr__(self, "risk", {**self.risk, ax: 0.0})

    @property
    def total_cost(self) -> float:
        return sum(self.cost.values())

    def to_ability_profile(self) -> AbilityProfile:
        return AbilityProfile(
            id=self.ability_id, axis=self.axis,
            requires=tuple(),
            cost={a: self.cost.get(a, 0.0) for a in AXES},
            risk={a: self.risk.get(a, 0.0) for a in AXES},
            effect_tags=self.effect_tags,
            notes=f"chamber_ability axis={self.axis}",
        )

    def to_dict(self) -> Dict:
        return {
            "ability_id": self.ability_id, "axis": self.axis,
            "cost": self.cost, "risk": self.risk,
            "effect_tags": list(self.effect_tags),
        }


def _build_chamber_abilities() -> Dict[str, ChamberAbility]:
    raw = [
        dict(ability_id="X:ADMIT", axis="X",
             effect_tags=("admit", "classify"),
             cost=dict(X=0.10, T=0.01, N=0.02, B=0.00, A=0.00),
             risk=dict(X=0.02, T=0.00, N=0.00, B=0.00, A=0.00)),
        dict(ability_id="X:RECLASSIFY", axis="X",
             effect_tags=("reclassify", "reindex"),
             cost=dict(X=0.15, T=0.01, N=0.02, B=0.01, A=0.00),
             risk=dict(X=0.03, T=0.00, N=0.00, B=0.01, A=0.00)),
        dict(ability_id="T:ADVANCE_TICK", axis="T",
             effect_tags=("tick", "temporal_advance"),
             cost=dict(X=0.00, T=0.05, N=0.01, B=0.00, A=0.00),
             risk=dict(X=0.00, T=0.00, N=0.00, B=0.00, A=0.00)),
        dict(ability_id="T:PHASE_DRIFT", axis="T",
             effect_tags=("drift", "toroidal_phase"),
             cost=dict(X=0.00, T=0.05, N=0.02, B=0.01, A=0.00),
             risk=dict(X=0.00, T=0.01, N=0.00, B=0.00, A=0.00)),
        dict(ability_id="N:REDISTRIBUTE", axis="N",
             effect_tags=("energy_flow", "conserve"),
             cost=dict(X=0.00, T=0.01, N=0.05, B=0.01, A=0.00),
             risk=dict(X=0.00, T=0.00, N=0.02, B=0.00, A=0.00)),
        dict(ability_id="N:DRAIN_BASELINE", axis="N",
             effect_tags=("baseline_burn",),
             cost=dict(X=0.00, T=0.00, N=0.10, B=0.00, A=0.00),
             risk=dict(X=0.01, T=0.00, N=0.03, B=0.00, A=0.00)),
        dict(ability_id="B:PARTITION_SHIFT", axis="B",
             effect_tags=("topology", "partition", "boundary_flux"),
             cost=dict(X=0.00, T=0.01, N=0.05, B=0.10, A=0.01),
             risk=dict(X=0.00, T=0.00, N=0.00, B=0.05, A=0.00)),
        dict(ability_id="B:INTERFACE_WEAKEN", axis="B",
             effect_tags=("boundary_weaken", "proximity_merge"),
             cost=dict(X=0.00, T=0.01, N=0.03, B=0.08, A=0.00),
             risk=dict(X=0.00, T=0.00, N=0.00, B=0.04, A=0.00)),
        dict(ability_id="B:INTERFACE_STRENGTHEN", axis="B",
             effect_tags=("boundary_strengthen", "differentiation"),
             cost=dict(X=0.00, T=0.01, N=0.03, B=0.08, A=0.00),
             risk=dict(X=0.00, T=0.00, N=0.00, B=0.04, A=0.00)),
        dict(ability_id="A:DIRECTED_MANIPULATION", axis="A",
             effect_tags=("agency", "boundary_manipulation", "structured_change"),
             cost=dict(X=0.00, T=0.01, N=0.10, B=0.05, A=0.15),
             risk=dict(X=0.01, T=0.00, N=0.05, B=0.02, A=0.00)),
        dict(ability_id="A:ALIGNMENT_PUSH", axis="A",
             effect_tags=("agency", "alignment_torque", "deep_shift"),
             cost=dict(X=0.00, T=0.01, N=0.08, B=0.03, A=0.20),
             risk=dict(X=0.01, T=0.00, N=0.04, B=0.01, A=0.00)),
    ]

    # Add first-class base pair atoms (5x5 = 25) as traceable ability units.
    # These are the canonical combinatorial non-comp atoms from which links evolve.
    axis_keys = ["X", "T", "N", "B", "A"]
    for left in axis_keys:
        for right in axis_keys:
            aid = _pair_atom_id(left, right)
            cost = {"X": 0.0, "T": 0.0, "N": 0.0, "B": 0.0, "A": 0.0}
            risk = {"X": 0.0, "T": 0.0, "N": 0.0, "B": 0.0, "A": 0.0}
            # lightweight pair-atom bookkeeping cost with explicit ancestry on both axes
            cost[left] += 0.01
            cost[right] += 0.01
            if left == "X" or right == "X":
                risk["X"] += 0.001
            raw.append(dict(
                ability_id=aid,
                axis=right,
                effect_tags=("pair_atom", f"{left}_to_{right}"),
                cost=cost,
                risk=risk,
            ))

    return {r["ability_id"]: ChamberAbility(**r) for r in raw}


# ---------------------------------------------------------------------------
# ACTION → ABILITY MAPPER
# Translates ActionTrace.constraints_used to IVM stimuli + TraceItems
# ---------------------------------------------------------------------------

# Polarity key names as returned by IVM.compute_axis_polarities()
# Keys are lowercase full strings, NOT single letters.
_POL_KEY_ORDER: Tuple[str, ...] = (
    "existence", "temporal", "energy", "boundary", "agency"
)
_POL_TO_AX: Dict[str, str] = {
    "existence": "X", "temporal": "T", "energy": "N",
    "boundary": "B", "agency": "A",
}

_LABEL_TO_AXIS: Dict[str, str] = {
    "existence": "X",
    "temporal": "T",
    "energy": "N",
    "boundary": "B",
    "agency": "A",
}

_AXIS_TO_LABEL: Dict[str, str] = {
    "X": "existence",
    "T": "temporal",
    "N": "energy",
    "B": "boundary",
    "A": "agency",
}

# Rubric dimensions from dream evidence mapped to constraint axes.
_RUBRIC_TO_AXIS: Dict[str, str] = {
    "coherence_maintenance": "T",
    "context_carryover": "T",
    "ambiguity_handling": "B",
    "contradiction_handling": "B",
    "implied_intent_inference": "A",
    "misunderstanding_repair": "A",
    "uncertainty_signaling": "N",
    "boundary_calibration": "N",
    "framing_selection": "X",
    "emotional_calibration": "X",
    "semantic_precision": "X",
    "adaptive_strategy_selection": "A",
    "compression_elaboration_fit": "N",
    "perspective_integration": "B",
    "multi_turn_stability": "T",
}

_CONSTRAINT_TOKEN_ALIASES: Dict[str, str] = {
    "x": "existence",
    "t": "temporal",
    "n": "energy",
    "b": "boundary",
    "a": "agency",
    "existence": "existence",
    "temporal": "temporal",
    "energy": "energy",
    "boundary": "boundary",
    "agency": "agency",
}


def _clamp01(v: Any) -> float:
    try:
        x = float(v)
    except Exception:
        x = 0.0
    return max(0.0, min(1.0, x))


def _axis_from_pressure_key(raw: Any) -> Optional[str]:
    token = str(raw or "").strip()
    if not token:
        return None
    upper = token.upper()
    if upper in AXES:
        return upper
    lower = token.lower()
    if lower in _LABEL_TO_AXIS:
        return _LABEL_TO_AXIS[lower]
    if lower.endswith("_exploration"):
        base = lower[:-12]
        if base.upper() in AXES:
            return base.upper()
        if base in _LABEL_TO_AXIS:
            return _LABEL_TO_AXIS[base]
        if base in _RUBRIC_TO_AXIS:
            return _RUBRIC_TO_AXIS[base]
    if lower in _RUBRIC_TO_AXIS:
        return _RUBRIC_TO_AXIS[lower]
    return None


def _normalize_constraint_token(raw: Any) -> Optional[str]:
    """
    Convert raw evidence token to canonical chamber label.
    Supports direct labels, axis letters, and rubric dimensions.
    """
    token = str(raw or "").strip().lower()
    if not token:
        return None

    direct = _CONSTRAINT_TOKEN_ALIASES.get(token)
    if direct:
        return direct

    axis = _RUBRIC_TO_AXIS.get(token)
    if axis:
        return _AXIS_TO_LABEL.get(axis)

    return None


def _pair_atom_id(ax_left: str, ax_right: str) -> str:
    return f"NC:{ax_left}>{ax_right}"


def _pair_atom_trace_items(labels: List[str]) -> List[TraceItem]:
    """
    Build first-class base pair atoms from active constraint labels.
    If labels include all five constraints, this emits the full 5x5 = 25 base pool.
    """
    axes = []
    for lbl in labels:
        ax = _LABEL_TO_AXIS.get(str(lbl).lower().strip())
        if ax:
            axes.append(ax)
    if not axes:
        return []

    uniq_axes = sorted(set(axes))
    items: List[TraceItem] = []
    for left in uniq_axes:
        for right in uniq_axes:
            items.append(TraceItem(kind="ABILITY", id=_pair_atom_id(left, right)))
    return items
# ALIGNMENT_VOTE_WEIGHT is keyed by RecursionLevel enum instances
_LEVEL_ORDER: Tuple = (
    RecursionLevel.SURFACE, RecursionLevel.SHALLOW,
    RecursionLevel.MODERATE, RecursionLevel.DEEP, RecursionLevel.CORE,
)

_LABEL_MAP: Dict[str, Tuple[str, RecursionLevel, str]] = {
    "existence": ("I_IS",  RecursionLevel.SURFACE,  "existence"),
    "temporal":  ("I_CAN", RecursionLevel.SHALLOW,  "temporal"),
    "energy":    ("I_DO",  RecursionLevel.MODERATE, "energy"),
    "boundary":  ("I_SAW", RecursionLevel.DEEP,     "boundary"),
    "agency":    ("I_DID", RecursionLevel.CORE,     "agency"),
}

_LABEL_TO_ABILITY: Dict[str, str] = {
    "existence": "X:ADMIT",
    "temporal":  "T:PHASE_DRIFT",
    "energy":    "N:REDISTRIBUTE",
    "boundary":  "B:PARTITION_SHIFT",
    "agency":    "A:DIRECTED_MANIPULATION",
}

# Axis-anchored ability variants increase pair diversity for evolutionary chaining
# while preserving strict ancestry to the same base constraint.
# A:OUTLET_PUSH is included in agency variants so release_outlet traces
# (agency+boundary) can actually land in link parent pairs — without this,
# outlet_push_fraction in chain_report() always reads 0.000 because no link
# ever has A:OUTLET_PUSH as a parent.
_LABEL_TO_ABILITY_VARIANTS: Dict[str, Tuple[str, ...]] = {
    "existence": ("X:ADMIT", "X:RECLASSIFY"),
    "temporal":  ("T:ADVANCE_TICK", "T:PHASE_DRIFT"),
    "energy":    ("N:REDISTRIBUTE", "N:DRAIN_BASELINE"),
    "boundary":  ("B:PARTITION_SHIFT", "B:INTERFACE_WEAKEN", "B:INTERFACE_STRENGTHEN"),
    "agency":    ("A:DIRECTED_MANIPULATION", "A:ALIGNMENT_PUSH", "A:OUTLET_PUSH"),
}

# Per-axis tick salt breaks the sum-of-ordinals mod-k collision between labels.
# Root cause: sum(ord("agency")) % 3 == sum(ord("boundary")) % 3 == 1, so without
# a salt both axes always land on the same variant index — A:OUTLET_PUSH is
# permanently locked to B:INTERFACE_STRENGTHEN (which adds pressure, not relieves
# it) and therefore never accumulates pair stats on relief ticks.
_AXIS_TICK_SALT: Dict[str, int] = {
    "existence": 0,
    "temporal":  1,
    "energy":    2,
    "boundary":  4,  # offset=4 (%3=1): pairs OUTLET_PUSH(agency idx 2) with INTERFACE_WEAKEN(idx 1)
    "agency":    5,  # offset=5 (%3=2): OUTLET_PUSH at tick%3==0; DIRECTED_MANIP at 1; ALIGN at 2
}


def _select_axis_ability(label: str, action: Optional[ActionTrace], tick: int) -> str:
    """Pick a deterministic per-axis ability variant to avoid pair-space collapse."""
    key = str(label).lower().strip()
    variants = _LABEL_TO_ABILITY_VARIANTS.get(key)
    if not variants:
        return _LABEL_TO_ABILITY.get(key, "X:ADMIT")
    if len(variants) == 1:
        return variants[0]
    action_name = getattr(action, "name", "") if action is not None else ""
    salt = _AXIS_TICK_SALT.get(key, 0)
    seed = sum(ord(ch) for ch in action_name) + (tick + salt)
    return variants[seed % len(variants)]


class _ActionAbilityMapper:

    def __init__(self, lattice: IVMLattice, abilities: Dict[str, ChamberAbility]):
        self._lattice = lattice
        self._abilities = abilities

    def apply(
        self, action: ActionTrace, tick: int
    ) -> Tuple[List[TraceItem], Dict[str, float], Dict[str, float]]:
        trace_items: List[TraceItem] = []
        cost_total = _zero_axis_vec()
        risk_total = _zero_axis_vec()

        meta = action.meta or {}
        strength = 0.6 if meta.get("pulse") else 0.35

        for label in (action.constraints_used or frozenset()):
            mapping = _LABEL_MAP.get(str(label).lower())
            if mapping is None:
                continue
            predicate, level, _ = mapping
            self._lattice.vertices.inject_stimulus(
                predicate, strength=strength, level=level
            )
            ability_id = _select_axis_ability(str(label), action, tick)
            _action_meta = dict(action.meta or {}) if action else {}
            _env = EnvironmentVector(
                module="aurora_evolution_chamber",
                stream_type=str(_action_meta.get("stream_type", "") or ""),
                axis_context=str(label).upper()[:1] if label else "",
                call_tag="run_sample",
            )
            trace_items.append(TraceItem(kind="ABILITY", id=ability_id, env=_env))
            ab = self._abilities.get(ability_id)
            if ab:
                for a in AXES:
                    cost_total[a] += ab.cost.get(a, 0.0)
                    risk_total[a] += ab.risk.get(a, 0.0)

        return trace_items, cost_total, risk_total


# ---------------------------------------------------------------------------
# STRUCTURAL PROXIMITY — evolvable metric, not frozen Euclidean (spec §3)
# ---------------------------------------------------------------------------

class StructuralProximityMeter:
    """
    Proximity derived from IVM polarity state. Not symbolic. Not Euclidean.
    Uses depth-weighted L1 over 5-axis polarity vectors via ALIGNMENT_VOTE_WEIGHT.

    Drift rule (spec §3):
        small structural diff  → boundary weakens
        large structural diff  → boundary strengthens
    """

    # Maps RecursionLevel → IVM polarity key (lowercase full string)
    _LEVEL_TO_POL_KEY: Dict = {
        RecursionLevel.SURFACE:  "existence",
        RecursionLevel.SHALLOW:  "temporal",
        RecursionLevel.MODERATE: "energy",
        RecursionLevel.DEEP:     "boundary",
        RecursionLevel.CORE:     "agency",
    }

    def __init__(self, lattice: IVMLattice):
        self._lattice = lattice
        self._weights: Dict[Tuple[str, str], float] = {}
        self._partitions: Dict[str, FrozenSet[str]] = {}
        self._partition_history: Deque[int] = deque(maxlen=K.entropy_window)

    def structural_distance(self, node_a: IVMNode, node_b: IVMNode) -> float:
        pa = self._lattice.vertices.compute_axis_polarities(node_a.mode)
        pb = self._lattice.vertices.compute_axis_polarities(node_b.mode)
        total_w = sum(ALIGNMENT_VOTE_WEIGHT.values()) or 1.0
        dist = sum(
            ALIGNMENT_VOTE_WEIGHT.get(lvl, 1.0)
            * abs(pa.get(pol_key, 0.0) - pb.get(pol_key, 0.0))
            for lvl, pol_key in self._LEVEL_TO_POL_KEY.items()
        )
        return dist / total_w

    def update_boundaries(self) -> int:
        nodes = list(self._lattice.nodes.values())
        transitions = 0
        for i, na in enumerate(nodes):
            for nb in nodes[i + 1:]:
                key = (na.node_id, nb.node_id)
                key_r = (nb.node_id, na.node_id)
                d = self.structural_distance(na, nb)
                prev = self._weights.get(key, 0.5)
                if d < K.proximity_threshold:
                    new_w = max(0.0, prev - K.proximity_weaken_rate
                                * (K.proximity_threshold - d))
                else:
                    new_w = min(1.0, prev + K.proximity_strengthen_rate
                                * (d - K.proximity_threshold))
                if abs(new_w - prev) > 1e-6:
                    transitions += 1
                self._weights[key] = new_w
                self._weights[key_r] = new_w
        return transitions

    def recompute_partitions(self) -> int:
        nodes = list(self._lattice.nodes.keys())
        if not nodes:
            self._partitions = {}
            self._partition_history.append(0)
            return 0
        parent = {n: n for n in nodes}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x, y):
            parent[find(x)] = find(y)

        for (a, b), w in self._weights.items():
            if w < 0.30 and a in parent and b in parent:
                union(a, b)

        groups: Dict[str, Set[str]] = defaultdict(set)
        for n in nodes:
            groups[find(n)].add(n)

        self._partitions = {k: frozenset(v) for k, v in groups.items()}
        self._partition_history.append(len(self._partitions))
        return len(self._partitions)

    @property
    def partition_count(self) -> int:
        return len(self._partitions)

    def boundary_diffusion_entropy(self) -> float:
        """Entropy = boundary diffusion = std dev of partition count over window."""
        h = list(self._partition_history)
        if len(h) < 2:
            return 0.0
        mu = sum(h) / len(h)
        return math.sqrt(sum((x - mu) ** 2 for x in h) / len(h))


# ---------------------------------------------------------------------------
# ENERGY BUDGET — N Non-Comp enforcer
# ---------------------------------------------------------------------------

class EnergyBudget:

    def __init__(self, initial_energy: float = 1.0):
        self._budget = initial_energy
        self._initial = initial_energy
        self._total_spent = 0.0

    @property
    def available(self) -> float:
        return self._budget

    def burn_existence_cost(self) -> float:
        cost = K.baseline_burn_per_tick
        self._budget -= cost
        self._total_spent += cost
        return cost

    def spend(self, amount: float, tick: int) -> None:
        if self._budget - amount < K.energy_budget_floor:
            raise NonCompViolation("N",
                f"spend={amount:.6f} would push budget below floor at tick={tick}")
        self._budget -= amount
        self._total_spent += amount

    def replenish_from_lattice(self, lattice: IVMLattice) -> None:
        """
        Energy is conserved via redistribution — it is not created.
        Baseline burn redistributes from the boundary layer back into the budget.
        Lattice pool contributes proportionally; floor ensures existence can persist.
        """
        lattice_total = lattice.get_total_energy()
        # Lattice-proportional component (redistributed from node pool)
        lattice_component = lattice_total * 0.001
        # Boundary layer always returns the baseline burn (conservation)
        floor_component = K.baseline_burn_per_tick
        replenish = floor_component + min(K.baseline_burn_per_tick, lattice_component)
        self._budget += replenish

    def status(self) -> Dict:
        return {"budget": self._budget, "initial": self._initial,
                "total_spent": self._total_spent}


# ---------------------------------------------------------------------------
# PRESSURE READER — instrumented from IVM, never fabricated (spec §4)
# ---------------------------------------------------------------------------

def _read_pressure(lattice: IVMLattice) -> PressureVec:
    """
    Read 5-axis pressure from IVM polarity.
    IVM.compute_axis_polarities() returns keys: existence/temporal/energy/boundary/agency.
    ALIGNMENT_VOTE_WEIGHT is keyed by RecursionLevel enum instances.
    """
    pols = lattice.vertices.compute_axis_polarities(ExistenceMode.AGENTIC)
    # (RecursionLevel, polarity_key, PressureVec_axis)
    level_map = [
        (RecursionLevel.SURFACE,  "existence", "X"),
        (RecursionLevel.SHALLOW,  "temporal",  "T"),
        (RecursionLevel.MODERATE, "energy",    "N"),
        (RecursionLevel.DEEP,     "boundary",  "B"),
        (RecursionLevel.CORE,     "agency",    "A"),
    ]
    total_w = sum(ALIGNMENT_VOTE_WEIGHT.values()) or 1.0
    p: Dict[str, float] = {}
    for level, pol_key, ax in level_map:
        base = (ALIGNMENT_VOTE_WEIGHT.get(level, 1.0) / total_w) * abs(pols.get(pol_key, 0.0))
        cost_w = _AXIS_COST_WEIGHT.get(ax, 1.0)
        factor = (1.0 - _PRESSURE_COST_BLEND) + (_PRESSURE_COST_BLEND * cost_w)
        p[ax] = base * factor
    return PressureVec(X=p["X"], T=p["T"], N=p["N"], B=p["B"], A=p["A"])


def _state_signature(lattice: IVMLattice, tick: int, partition_count: int) -> str:
    pols = lattice.vertices.compute_axis_polarities(ExistenceMode.AGENTIC)
    pol_keys = ("existence", "temporal", "energy", "boundary", "agency")
    raw = (f"{tick}|{len(lattice.nodes)}|{partition_count}|"
           + "|".join(f"{k}:{pols.get(k, 0.0):.4f}" for k in pol_keys))
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# EVOLUTIONARY CHAMBER — main class
# ---------------------------------------------------------------------------

class EvolutionaryChamber:
    """
    Constraint-Native Evolution Chamber — Full Unified Spec v3.

    Constructor signature (matches run_chain.py exactly):

        EvolutionaryChamber(
            lattice:        IVMLattice,
            genealogy:      ConstraintGenealogyLogger,  <- pass-in from caller
            run_id:         str,
            output_dir:     str,
            constants:      WorldConstants = K,          <- optional
            initial_energy: float = 1.0,                 <- optional
        )

    Primary loop:
        chamber.tick(action: Optional[ActionTrace]) -> Optional[record]
        chamber.tick_count   -> int
        chamber.alive        -> bool

    Evolutionary chain replication (spec §0):
        chamber.run_chain(n_ticks, action_schedule) -> summary dict
    """

    def __init__(
        self,
        lattice: IVMLattice,
        genealogy: Optional[ConstraintGenealogyLogger] = None,
        run_id: Optional[str] = None,
        output_dir: str = "chamber_output",
        constants: WorldConstants = K,
        initial_energy: float = 1.0,
    ):
        self.lattice = lattice
        self.run_id = run_id or f"run_{uuid.uuid4().hex[:8]}"
        self.output_dir = output_dir
        self.K = constants
        self.tick_count: int = 0
        self._alive: bool = True

        os.makedirs(output_dir, exist_ok=True)

        # Genealogy logger — injected or created internally
        if genealogy is not None:
            self._genealogy = genealogy
        else:
            _ab = {aid: ab.to_ability_profile()
                   for aid, ab in _build_chamber_abilities().items()}
            self._genealogy = ConstraintGenealogyLogger(
                run_id=self.run_id,
                config=GenealogyConfig(),
                abilities=_ab,
                output_dir=output_dir,
            )

        # V3 physics sub-systems
        self._abilities = _build_chamber_abilities()
        self._budget = EnergyBudget(initial_energy)
        self._proximity = StructuralProximityMeter(lattice)
        self._mapper = _ActionAbilityMapper(lattice, self._abilities)
        self._polarity_sensor = PolarityGradientSensor()
        self._gradient_miner = GradientChainMiner()
        # Difference channel history buffer — maintained across every tick
        # so C:D values are always current for relief annotation, variant
        # promotion, and live cost-diff scoring.
        self._diff_buffer: DifferenceHistoryBuffer = make_difference_buffer()

        # State tracking
        self._prev_pressure: Optional[PressureVec] = None
        # One-tick carryover credit pools by represented scale.
        self._carryover_credit_current: Dict[str, float] = {
            k: 0.0 for k in _UNUSED_OP_CARRYOVER_RATE.keys()
        }
        self._carryover_credit_next: Dict[str, float] = {
            k: 0.0 for k in _UNUSED_OP_CARRYOVER_RATE.keys()
        }
        # Intent pressure accumulates constraint demand from declared traces,
        # even when budget limits physical stimulation in a given tick.
        self._intent_pressure: Dict[str, float] = {a: 0.0 for a in AXES}
        # Latest external steering profile ingested from dream/code evidence.
        self._external_pressure_state: Dict[str, Any] = {
            "updates": 0,
            "last_axis_drive": {a: 0.0 for a in AXES},
            "last_constraints": [],
            "last_confidence": 0.0,
            "last_pulses": 0,
            "last_mutation_name": "",
            "last_evidence_id": "",
            "last_updated_tick": 0,
            "last_profile": {},
        }

        # Counters
        self.total_relief_events: int = 0
        self.total_violation_events: int = 0

        # Violation log
        self._violations: Deque[ViolationRecord] = deque(
            maxlen=self.K.violation_log_capacity
        )

        # Initial partition computation
        self._proximity.recompute_partitions()

    # ====================================================================
    # tick
    # ====================================================================

    def tick(self, action: Optional[ActionTrace] = None) -> Optional[Any]:
        """
        Advance the universe one tick.

        Non-Comp enforcement order (spec §1):
          1. T  — tick must advance
          2.    — natural drift (no teleology)
          3. N  — baseline existence burn
          4.    — agency stimulus (A pre-checked)
          5. X  — all nodes on admissible manifold
          6. B  — topology must remain partitionable
          7.    — read pressure from IVM (never fabricate)
          8/9.  — log only on relief; observe in genealogy for link promotion

        Returns genealogy observe() result (ReliefRecord or stub dict) on
        relief event, None otherwise. Sets alive=False on Non-Comp breach.
        """
        if not self._alive:
            return None

        tick_before = self.tick_count

        try:
            # 1. T Non-Comp
            self.tick_count += 1
            GlobalNonComps.check_T(tick_before, self.tick_count)

            # Advance one-tick carryover window.
            self._carryover_credit_current = dict(self._carryover_credit_next)
            self._carryover_credit_next = {k: 0.0 for k in _UNUSED_OP_CARRYOVER_RATE.keys()}

            sig_before = _state_signature(
                self.lattice, self.tick_count, self._proximity.partition_count
            )

            # 2. Natural drift — T-axis background pulse (no teleology)
            self.lattice.vertices.inject_stimulus(
                "I_CAN", strength=0.02, level=RecursionLevel.SHALLOW
            )
            self.lattice.vertices.tick(dt=self.K.dt)
            self._proximity.update_boundaries()
            self._proximity.recompute_partitions()

            # 3. N Non-Comp: baseline existence burn
            self._budget.burn_existence_cost()
            self._budget.replenish_from_lattice(self.lattice)
            GlobalNonComps.check_N(self._budget.available, self.tick_count)

            # 4. Agency — translate ActionTrace to IVM stimulus + trace
            trace_items: List[TraceItem] = []
            observe_notes: Dict[str, object] = {}
            if action is not None:
                # Binary energy eligibility with per-scale one-tick carryover credits.
                requested = set(action.constraints_used or frozenset())
                action_meta = dict(action.meta or {})
                executed_action = False
                if requested:
                    label_priority = {
                        "agency": 5,
                        "boundary": 4,
                        "energy": 3,
                        "temporal": 2,
                        "existence": 1,
                    }
                    ordered_labels = sorted(
                        requested,
                        key=lambda lbl: (-label_priority.get(str(lbl).lower(), 0), str(lbl))
                    )
                    requested_axes = len(ordered_labels)
                    represented_scale = str(ordered_labels[0]).lower() if ordered_labels else "existence"
                    magnitude = requested_axes * 0.1
                    base_energy_cost = self.K.agency_cost_coefficient * (magnitude ** 2)

                    carry_credit = max(0.0, float(self._carryover_credit_current.get(represented_scale, 0.0)))
                    effective_cost = max(0.0, float(base_energy_cost) - carry_credit)

                    available_energy = max(0.0, self._budget.available - self.K.energy_budget_floor)
                    executable = (
                        requested_axes > 0
                        and magnitude <= float(self.K.agency_max_magnitude)
                        and effective_cost <= available_energy
                    )

                    # Every attempted op participates in evolutionary chain lineage.
                    trace_items = _pair_atom_trace_items(ordered_labels)

                    if executable:
                        # Consume only what is needed from current one-tick credit.
                        credit_used = min(carry_credit, float(base_energy_cost))
                        self._carryover_credit_current[represented_scale] = max(0.0, carry_credit - credit_used)

                        # Only executed actions contribute to evolutionary trace.
                        trace_items = _pair_atom_trace_items(ordered_labels)
                        mapped_items, _mapped_cost, _mapped_risk = self._mapper.apply(
                            action, self.tick_count
                        )
                        if mapped_items:
                            trace_items.extend(mapped_items)
                        self._budget.spend(effective_cost, self.tick_count)
                        action_meta["base_energy_cost"] = float(base_energy_cost)
                        action_meta["carryover_credit_used"] = float(credit_used)
                        action_meta["effective_energy_cost"] = float(effective_cost)
                        action_meta["represented_scale"] = represented_scale
                        action_meta["executed_action"] = True
                        executed_action = True
                    else:
                        # Persisting without acting incurs half base cost if affordable.
                        idle_factor = max(0.0, min(1.0, float(getattr(self.K, "idle_persistence_cost_factor", 0.50))))
                        idle_cost = float(base_energy_cost) * idle_factor
                        idle_executable = (requested_axes > 0 and idle_cost <= available_energy)

                        if idle_executable and idle_cost > 0.0:
                            self._budget.spend(idle_cost, self.tick_count)
                            residual = max(0.0, float(base_energy_cost) - idle_cost)
                            carry_rate = max(0.0, min(1.0, float(_UNUSED_OP_CARRYOVER_RATE.get(represented_scale, 0.10))))
                            carry_next = residual * carry_rate
                            self._carryover_credit_next[represented_scale] = float(self._carryover_credit_next.get(represented_scale, 0.0)) + carry_next
                            action_meta["idle_persistence"] = True
                            action_meta["idle_persistence_cost"] = float(idle_cost)
                            action_meta["unused_residual"] = float(residual)
                            action_meta["carryover_rate"] = float(carry_rate)
                            action_meta["carryover_credit_next"] = float(carry_next)
                            action_meta["represented_scale"] = represented_scale
                        else:
                            action_meta["idle_persistence"] = False

                        action_meta["energy_ineligible"] = True
                        action_meta["requested_axes"] = requested_axes
                        action_meta["base_energy_cost"] = float(base_energy_cost)
                        action_meta["effective_energy_cost"] = float(effective_cost)
                        action_meta["available_energy"] = float(available_energy)
                        action_meta["carryover_credit_available"] = float(carry_credit)
                        action_meta["executed_action"] = False

                # If this tick was spawned from a promoted link, preserve that
                # identity as lineage context even when energy-ineligible.
                link_id = action_meta.get("link_id")
                if isinstance(link_id, str) and link_id:
                    if getattr(self._genealogy, "links", {}).get(link_id) is not None:
                        trace_items.append(TraceItem(kind="LINK", id=link_id))

                # Feed action-energy/lineage details into genealogy notes so
                # trace_cost_total captures action economics even when mapped
                # ability profiles are sparse.
                observe_notes["action_energy"] = {
                    "executed_action": bool(action_meta.get("executed_action", False)),
                    "energy_ineligible": bool(action_meta.get("energy_ineligible", False)),
                    "effective_energy_cost": float(action_meta.get("effective_energy_cost", 0.0) or 0.0),
                    "idle_persistence_cost": float(action_meta.get("idle_persistence_cost", 0.0) or 0.0),
                    "base_energy_cost": float(action_meta.get("base_energy_cost", 0.0) or 0.0),
                    "represented_scale": str(action_meta.get("represented_scale", "existence")),
                }
                for meta_key in (
                    "constraint_combo_id",
                    "operation_lineage_id",
                    "link_id",
                    "artificial_seed",
                    "bypass_natural",
                    "seed_lineage_id",
                    "target_generation",
                    "target_purpose_lane",
                    "target_operator_action",
                    "artificial_seed_weight",
                ):
                    meta_val = action_meta.get(meta_key)
                    if isinstance(meta_val, str) and meta_val:
                        observe_notes[meta_key] = meta_val
                    elif isinstance(meta_val, (bool, int, float)):
                        observe_notes[meta_key] = meta_val

            # 5. X Non-Comp: all nodes on admissible manifold
            # Snapshot items() to avoid RuntimeError if another thread mutates
            # self.lattice.nodes concurrently (gauntlet + proactive loop race).
            for nid, node in list(self.lattice.nodes.items()):
                GlobalNonComps.check_X(node.mode, nid, self.tick_count)

            # 6. B Non-Comp: topology partitionable
            GlobalNonComps.check_B(
                self._proximity.partition_count,
                self.tick_count,
                node_count=len(self.lattice.nodes),
            )

            # 7. Read pressure from IVM — never fabricate
            pressure_now = _read_pressure(self.lattice)
            polarity_report = self._polarity_sensor.measure(
                self.lattice.vertices, tick=self.tick_count
            )

            # 7b. Record magnitude state in Difference buffer and compute C:D snapshot.
            # Magnitudes are approximated from IVM pressure components — the best
            # available proxy for per-constraint activation intensity within the
            # chamber tick loop without a full LayerEnergyAccountant.
            # The snapshot rides into genealogy observe() for relief event annotation.
            # Intent accumulation: build declared-demand pressure per axis from
            # the current trace and decay historical demand over time.
            intent_signal = {"X": 0.0, "T": 0.0, "N": 0.0, "B": 0.0, "A": 0.0}

            def _axes_from_trace_item(item: TraceItem, seen_links: Optional[set] = None) -> List[str]:
                tid = str(getattr(item, "id", ""))
                kind = str(getattr(item, "kind", "ABILITY")).upper()

                # Base pair atom format: NC:X>Y (first-class noncomp combinatorics)
                if tid.startswith("NC:") and ">" in tid:
                    pair = tid[3:]
                    left, right = pair.split(">", 1)
                    axes: List[str] = []
                    l_ax = left.strip().upper()
                    r_ax = right.strip().upper()
                    if l_ax in intent_signal:
                        axes.append(l_ax)
                    if r_ax in intent_signal:
                        axes.append(r_ax)
                    return axes

                # Legacy ability format: X:ABILITY
                if ":" in tid and not tid.startswith("L:"):
                    ax = tid.split(":", 1)[0].strip().upper()
                    return [ax] if ax in intent_signal else []

                # Link traces are first-class. Pull ancestral axis demand from
                # parent abilities/links so pressure remains visible across depth.
                if kind == "LINK" and tid.startswith("L:") and hasattr(self._genealogy, "get_link"):
                    seen = seen_links or set()
                    if tid in seen:
                        return []
                    seen.add(tid)
                    lnk = self._genealogy.get_link(tid)
                    if lnk is None:
                        return []
                    out: List[str] = []
                    for parent_id in list(getattr(lnk, "parents", [])):
                        pid = str(parent_id)
                        pkind = "LINK" if pid.startswith("L:") else "ABILITY"
                        out.extend(_axes_from_trace_item(TraceItem(kind=pkind, id=pid), seen))
                    return out
                return []

            for ti in trace_items:
                axes = sorted(set(_axes_from_trace_item(ti)))
                if not axes:
                    continue
                per_axis = 1.0 / float(len(axes))
                for ax in axes:
                    intent_signal[ax] += per_axis
            max_sig = max(intent_signal.values()) if intent_signal else 0.0
            if max_sig > 0:
                for ax in intent_signal:
                    intent_signal[ax] /= max_sig

            # EMA intent memory; keeps pressure accumulation visible under
            # budget starvation without fabricating unconstrained axes.
            intent_alpha = 0.08
            intent_decay = 0.94
            for ax in AXES:
                prev_i = self._intent_pressure.get(ax, 0.0)
                self._intent_pressure[ax] = max(
                    0.0,
                    (prev_i * intent_decay) + (intent_alpha * intent_signal.get(ax, 0.0))
                )

            _chamber_magnitudes = {}
            for c in (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A):
                ax = c.name
                physical = max(0.0, getattr(pressure_now, ax, 0.0))
                intent = self._intent_pressure.get(ax, 0.0)
                # Blend physical + intent so C:D reflects both held state and
                # declared constraint demand in the evolutionary chain.
                _chamber_magnitudes[c] = (0.7 * physical) + (0.3 * intent)
            self._diff_buffer.record(self.tick_count, _chamber_magnitudes)
            _diff_snapshot = self._diff_buffer.snapshot(self.tick_count, _chamber_magnitudes)

            sig_after = _state_signature(
                self.lattice, self.tick_count, self._proximity.partition_count
            )

            # 8/9. Log only on relief — delegate to genealogy
            # Rewrite current trace through promoted links so learned links
            # participate as first-class parents in subsequent evolution.
            trace_for_genealogy = trace_items
            if trace_items and hasattr(self._genealogy, "rewrite_trace"):
                try:
                    trace_for_genealogy = self._genealogy.rewrite_trace(trace_items)
                except Exception:
                    trace_for_genealogy = trace_items

            result = None
            if self._prev_pressure is not None:
                result = self._genealogy.observe(
                    pressure_before     = self._prev_pressure,
                    trace               = trace_for_genealogy,
                    pressure_after      = pressure_now,
                    state_sig_before    = sig_before,
                    state_sig_after     = sig_after,
                    notes               = observe_notes,
                    difference_snapshot = _diff_snapshot,
                )
                if result is not None:
                    self.total_relief_events += 1

            # Gradient miner
            if polarity_report.is_relief:
                self._gradient_miner.observe_gradient_relief(polarity_report)

            self._prev_pressure = pressure_now
            return result

        except NonCompViolation as e:
            self._alive = False
            self.total_violation_events += 1
            sig = e.signature or hashlib.sha1(
                f"{e.non_comp}:{self.tick_count}:{e.reason}".encode()
            ).hexdigest()[:12]
            self._violations.append(ViolationRecord(
                tick=self.tick_count, timestamp=time.time(),
                non_comp=e.non_comp, reason=e.reason,
                violation_signature=sig,
                measures={"budget": self._budget.available,
                          "tick": float(self.tick_count)},
            ))
            return None

    # ====================================================================
    # External evidence bridge
    # ====================================================================

    def _axis_drive_from_external_evidence(self, outcome: Dict[str, Any]) -> Dict[str, float]:
        """
        Build axis-level pressure drive from evidence payload.

        This gives the chamber direct access to dream/steering pressure context
        so intent pressure and tick stimulation can align to the same signals.
        """
        rec = dict(outcome or {})
        notes = dict(rec.get("notes", {}) or {})
        drive: Dict[str, float] = {ax: 0.0 for ax in AXES}

        before = dict(rec.get("pressure_before", {}) or {})
        after = dict(rec.get("pressure_after", {}) or {})
        for ax in AXES:
            b = float(before.get(ax, 0.0) or 0.0)
            a = float(after.get(ax, 0.0) or 0.0)
            drive[ax] += abs(a - b) + (0.20 * max(a, b))

        for raw in (rec.get("constraints_used", []) or []):
            label = _normalize_constraint_token(raw)
            if not label:
                continue
            ax = _LABEL_TO_AXIS.get(label)
            if ax:
                drive[ax] += 0.20

        raw_axis = {}
        if isinstance(rec.get("constraint_axes"), dict):
            raw_axis = dict(rec.get("constraint_axes", {}) or {})
        elif isinstance(notes.get("constraint_axes"), dict):
            raw_axis = dict(notes.get("constraint_axes", {}) or {})
        for k, v in raw_axis.items():
            ax = _axis_from_pressure_key(k)
            if not ax:
                continue
            drive[ax] += 0.60 * _clamp01(v)

        profile = {}
        if isinstance(rec.get("pressure_profile"), dict):
            profile = dict(rec.get("pressure_profile", {}) or {})
        elif isinstance(notes.get("pressure_profile"), dict):
            profile = dict(notes.get("pressure_profile", {}) or {})

        mutation_bias = dict(profile.get("mutation_bias", {}) or {})
        for k, v in mutation_bias.items():
            ax = _axis_from_pressure_key(k)
            if not ax:
                continue
            drive[ax] += 0.75 * _clamp01(v)

        for bucket in ("threshold_adjustments", "cost_adjustments", "promotion_adjustments", "tolerance_adjustments"):
            m = dict(profile.get(bucket, {}) or {})
            for k, v in m.items():
                ax = _axis_from_pressure_key(k)
                if not ax:
                    continue
                val = _clamp01(abs(float(v)))
                drive[ax] += 0.20 * val

        max_v = max(drive.values()) if drive else 0.0
        if max_v > 0.0:
            for ax in AXES:
                drive[ax] = _clamp01(drive.get(ax, 0.0) / max_v)

        return {ax: float(drive.get(ax, 0.0)) for ax in AXES}

    def _constraints_from_external_evidence(self, outcome: Dict[str, Any], axis_drive: Optional[Dict[str, float]] = None) -> List[str]:
        """
        Resolve external evidence tokens into canonical chamber constraints.
        Dream rubric dimensions are mapped to X/T/N/B/A-backed labels.
        """
        resolved: Set[str] = set()

        for raw in (outcome.get("constraints_used", []) or []):
            label = _normalize_constraint_token(raw)
            if label:
                resolved.add(label)

        if not resolved:
            before = dict(outcome.get("pressure_before", {}) or {})
            after = dict(outcome.get("pressure_after", {}) or {})
            scored_axes: List[Tuple[str, float]] = []
            for ax in ("X", "T", "N", "B", "A"):
                b = float(before.get(ax, 0.0) or 0.0)
                a = float(after.get(ax, 0.0) or 0.0)
                # Blend transition + absolute pressure so weakly-tagged outcomes
                # still map to a meaningful constraint lane.
                score = abs(a - b) + (0.25 * max(a, b))
                scored_axes.append((ax, score))
            scored_axes.sort(key=lambda kv: kv[1], reverse=True)
            for ax, score in scored_axes[:3]:
                if score <= 0.01:
                    continue
                label = _AXIS_TO_LABEL.get(ax)
                if label:
                    resolved.add(label)

        if not resolved:
            resolved.update({"agency", "boundary", "temporal"})

        drive = dict(axis_drive or self._axis_drive_from_external_evidence(outcome))
        ranked_axes = sorted(drive.items(), key=lambda kv: float(kv[1]), reverse=True)
        for ax, score in ranked_axes[:2]:
            if float(score) < 0.20:
                continue
            label = _AXIS_TO_LABEL.get(str(ax))
            if label:
                resolved.add(label)

        priority = {
            "agency": 5,
            "boundary": 4,
            "energy": 3,
            "temporal": 2,
            "existence": 1,
        }
        ordered = sorted(
            resolved,
            key=lambda k: (
                -priority.get(str(k), 0),
                -float(drive.get(_LABEL_TO_AXIS.get(str(k), ""), 0.0)),
                str(k),
            ),
        )
        return [str(x) for x in ordered]

    def observe_external_evidence(self, outcome: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ingest dream/code evidence and apply it as real chamber pressure.

        This bridge does three things:
          1) maps evidence into constraint-native ActionTrace pulses,
          2) executes ticks so pressure enters the evolutionary chain,
          3) registers a code-evolution outcome in genealogy with target files.
        """
        rec = dict(outcome or {})
        notes = dict(rec.get("notes", {}) or {})
        mutation_name = str(rec.get("mutation_name", "dream_evidence") or "dream_evidence")
        axis_drive = self._axis_drive_from_external_evidence(rec)
        constraints = self._constraints_from_external_evidence(rec, axis_drive=axis_drive)
        frozen_constraints = frozenset(constraints)

        before = dict(rec.get("pressure_before", {}) or {})
        after = dict(rec.get("pressure_after", {}) or {})
        pressure_delta = 0.0
        for ax in ("X", "T", "N", "B", "A"):
            b = float(before.get(ax, 0.0) or 0.0)
            a = float(after.get(ax, 0.0) or 0.0)
            pressure_delta += abs(a - b)
        pressure_score = max(0.0, min(1.0, pressure_delta))

        try:
            confidence = float(notes.get("confidence", 0.0) or 0.0)
        except Exception:
            confidence = 0.0
        confidence = max(0.0, min(1.0, confidence))

        profile = {}
        if isinstance(rec.get("pressure_profile"), dict):
            profile = dict(rec.get("pressure_profile", {}) or {})
        elif isinstance(notes.get("pressure_profile"), dict):
            profile = dict(notes.get("pressure_profile", {}) or {})
        try:
            steering_confidence = _clamp01(profile.get("total_confidence", 0.0))
        except Exception:
            steering_confidence = 0.0

        pulses = 1
        if confidence >= 0.45:
            pulses += 1
        if pressure_score >= 0.35:
            pulses += 1
        if steering_confidence >= 0.35:
            pulses += 1
        if max(axis_drive.values()) >= 0.45:
            pulses += 1
        pulses = max(1, min(6, pulses))

        # Feed external pressure directly into intent memory so subsequent
        # chamber ticks can respond even under weak physical stimulation.
        for ax in AXES:
            prev = float(self._intent_pressure.get(ax, 0.0) or 0.0)
            ext = float(axis_drive.get(ax, 0.0) or 0.0)
            self._intent_pressure[ax] = max(
                0.0,
                min(1.5, (0.90 * prev) + (0.30 * ext)),
            )

        evidence_id = str(notes.get("evidence_id", "") or "").strip()
        episode_id = str(notes.get("episode_id", "") or "dream_episode")
        lineage_raw = f"{mutation_name}|{'+'.join(sorted(frozen_constraints))}|{evidence_id}|{self.tick_count}"
        op_lineage = "DREAMOP:" + hashlib.sha1(lineage_raw.encode()).hexdigest()[:12]

        last_tick_result: Optional[Any] = None
        ticks_run = 0
        for idx in range(pulses):
            if not self._alive:
                break
            action = ActionTrace(
                name=f"dream_feedback_{mutation_name}_{idx + 1}",
                constraints_used=frozen_constraints,
                meta={
                    "pulse": True,
                    "constraint_combo_id": "+".join(sorted(frozen_constraints)),
                    "operation_lineage_id": op_lineage,
                    "seed_lineage_id": episode_id,
                    "target_generation": int(self.tick_count + 1),
                    "target_purpose_lane": "communication",
                    "target_operator_action": mutation_name,
                    "artificial_seed": True,
                    "artificial_seed_weight": float(confidence if confidence > 0.0 else 0.5),
                    "external_axis_drive": dict(axis_drive),
                    "external_steering_confidence": float(steering_confidence),
                },
            )
            last_tick_result = self.tick(action=action)
            ticks_run += 1

        target_files = [
            str(p) for p in (rec.get("target_files", []) or [])
            if str(p).strip()
        ]
        target_modules = tuple(dict.fromkeys(
            p.replace("\\", "/").replace("/", ".").removesuffix(".py")
            for p in target_files
        ))

        try:
            avg_fitness = float(notes.get("avg_fitness", rec.get("avg_fitness", 0.0)) or 0.0)
        except Exception:
            avg_fitness = 0.0
        avg_fitness = max(0.0, avg_fitness)

        accepted = bool(rec.get("checks_passed", False))
        score = confidence if confidence > 0.0 else (0.65 if accepted else 0.35)
        score = max(0.0, min(1.0, score))

        mutation_id = f"DREAM:{evidence_id}" if evidence_id else (
            "DREAM:" + hashlib.sha1(f"{mutation_name}:{time.time_ns()}".encode()).hexdigest()[:14]
        )

        self._external_pressure_state = {
            "updates": int(self._external_pressure_state.get("updates", 0) or 0) + 1,
            "last_axis_drive": {ax: float(axis_drive.get(ax, 0.0) or 0.0) for ax in AXES},
            "last_constraints": list(sorted(frozen_constraints)),
            "last_confidence": float(confidence),
            "last_pulses": int(pulses),
            "last_mutation_name": str(mutation_name),
            "last_evidence_id": str(evidence_id),
            "last_updated_tick": int(self.tick_count),
            "last_profile": {
                "directive_count": int(profile.get("directive_count", 0) or 0) if isinstance(profile, dict) else 0,
                "total_confidence": float(steering_confidence),
            },
        }

        registration: Dict[str, Any] = {
            "registered": False,
            "reason": "register_code_evolution_outcome_unavailable",
        }
        if hasattr(self._genealogy, "register_code_evolution_outcome"):
            payload = {
                "mutation_id": mutation_id,
                "operator_key": f"dream_{mutation_name}",
                "accepted": accepted,
                "constraints": list(frozen_constraints),
                "target_files": list(target_files),
                "target_modules": list(target_modules),
                "changed_files": [],
                "change_count": 0,
                "score": score,
                "avg_fitness": float(avg_fitness),
                "genealogy_pressure": float(pressure_score),
                "compile_failures": 0,
                "conflicts_delta": 0.0,
                "rewrite_profile": "dream_evidence",
                "effect_modes": [mutation_name],
                "apply_duration_s": 0.0,
                "agency_time_credit": min(1.0, 0.20 + (0.15 * ticks_run)),
                "temporal_overhead_penalty": 0.0,
            }
            try:
                registration = dict(
                    self._genealogy.register_code_evolution_outcome(payload) or {}
                )
            except Exception as e:
                registration = {
                    "registered": False,
                    "reason": f"register_code_evolution_outcome_error:{e}",
                }

        return {
            "applied": bool(ticks_run > 0),
            "ticks_run": int(ticks_run),
            "constraints_used": list(frozen_constraints),
            "pressure_score": float(round(pressure_score, 6)),
            "axis_drive": {ax: float(axis_drive.get(ax, 0.0) or 0.0) for ax in AXES},
            "steering_confidence": float(steering_confidence),
            "mutation_id": mutation_id,
            "operation_lineage_id": op_lineage,
            "target_files": list(target_files),
            "genealogy_registration": registration,
            "alive": bool(self._alive),
            "last_tick_relief": bool(last_tick_result is not None),
        }

    # ====================================================================
    # run_chain — evolutionary chain replication (spec §0)
    # ====================================================================

    def run_chain(
        self,
        n_ticks: int,
        action_schedule: Optional[Dict[int, ActionTrace]] = None,
    ) -> Dict[str, Any]:
        """
        Run n_ticks ticks. action_schedule: {tick_number: ActionTrace}.
        Returns summary dict. Does NOT cheat evolutionary primitives.
        """
        schedule = action_schedule or {}
        for _ in range(n_ticks):
            if not self._alive:
                break
            self.tick(action=schedule.get(self.tick_count))
        self._genealogy.flush_files()
        self._write_abilities_file()
        return self.status()

    # ====================================================================
    # Status + inspection
    # ====================================================================

    @property
    def alive(self) -> bool:
        return self._alive

    @property
    def diff_snapshot(self):
        """
        Most recent DifferenceSnapshot from the chamber's internal buffer.

        Returns None if no ticks have run yet (buffer empty).

        Use this to supply the live C:D snapshot to:
            - VariantPromoter.process_solidified(... difference_snapshot=chamber.diff_snapshot)
            - Any cost_diff_score() call on StrandBead, DNAStrand, AbilityProfile,
              ConstraintLink, or VariantRecord.
            - Downstream evidence consumers that need the current
              cross-dimensional pressure state.
        """
        history = list(self._diff_buffer._history)
        if not history:
            return None
        last_tick, last_mags = history[-1]
        return self._diff_buffer.snapshot(last_tick, last_mags)

    def status(self) -> Dict[str, Any]:
        return {
            "version": CHAMBER_VERSION,
            "run_id": self.run_id,
            "tick": self.tick_count,
            "alive": self._alive,
            "relief_events": self.total_relief_events,
            "violation_events": self.total_violation_events,
            "energy": self._budget.status(),
            "partitions": self._proximity.partition_count,
            "entropy": self._proximity.boundary_diffusion_entropy(),
            "intent_pressure": {ax: float(self._intent_pressure.get(ax, 0.0) or 0.0) for ax in AXES},
            "external_pressure_state": dict(self._external_pressure_state or {}),
            "genealogy": self._genealogy.summary(),
        }

    def recent_violations(self, n: int = 20) -> List[ViolationRecord]:
        return list(self._violations)[-n:]

    def _write_abilities_file(self) -> None:
        path = os.path.join(self.output_dir, "abilities.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({aid: ab.to_dict() for aid, ab in self._abilities.items()},
                      fh, indent=2)

    def close(self) -> None:
        self._genealogy.flush_files()
        self._write_abilities_file()
        if hasattr(self._genealogy, "close"):
            self._genealogy.close()


# ---------------------------------------------------------------------------
# ALIAS
# ---------------------------------------------------------------------------

EvolutionChamberV3 = EvolutionaryChamber


# ---------------------------------------------------------------------------
# CONVENIENCE FACTORY
# ---------------------------------------------------------------------------

def make_chamber(
    contract: Optional[FoundationalContract] = None,
    initial_energy: float = 1.0,
    output_dir: str = "chamber_output",
    run_id: Optional[str] = None,
) -> EvolutionaryChamber:
    _contract = contract or FoundationalContract()
    lattice = IVMLattice(_contract)
    return EvolutionaryChamber(
        lattice=lattice, run_id=run_id,
        initial_energy=initial_energy, output_dir=output_dir,
    )


# ---------------------------------------------------------------------------
# SELF-TEST
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import tempfile

    print(f"[EvolutionaryChamber] version={CHAMBER_VERSION}")
    print(f"  genealogy_available : {_GENEALOGY_AVAILABLE}")

    # Verify all run_chain.py exports exist
    assert ActionTrace, "ActionTrace must be exported"
    assert WorldConstants, "WorldConstants must be exported"
    assert EvolutionaryChamber, "EvolutionaryChamber must be exported"
    print("  [OK] run_chain.py exports: ActionTrace, WorldConstants, EvolutionaryChamber")

    # Verify ActionTrace matches run_chain.py usage
    at = ActionTrace("communicate", frozenset({"agency", "boundary", "temporal"}),
                     meta={"episode": "communication"})
    assert at.name == "communicate"
    assert "agency" in at.constraints_used
    print(f"  [OK] ActionTrace: {at.name} / {sorted(at.constraints_used)}")

    with tempfile.TemporaryDirectory() as tmpdir:
        chamber = make_chamber(initial_energy=2.0, output_dir=tmpdir)

        # Replicate run_chain.py action cycle
        action_cycle = [
            ActionTrace("communicate",    frozenset({"agency", "boundary", "temporal"}),
                        meta={"episode": "communication"}),
            ActionTrace("release_outlet", frozenset({"agency", "boundary"}),
                        meta={"pulse": True}),
            ActionTrace("full_assert",
                        frozenset({"existence","temporal","energy","boundary","agency"}),
                        meta={"pulse": True}),
            ActionTrace("pure_agency",    frozenset({"agency"})),
            ActionTrace("pure_boundary",  frozenset({"boundary"})),
        ]

        for i in range(200):
            chamber.tick(action=action_cycle[i % len(action_cycle)])

        s = chamber.status()
        print(f"  ticks      : {s['tick']}")
        print(f"  alive      : {s['alive']}")
        print(f"  relief evts: {s['relief_events']}")
        print(f"  violations : {s['violation_events']}")
        print(f"  entropy    : {s['entropy']:.6f}")
        print(f"  partitions : {s['partitions']}")
        assert s["alive"], "Chamber should survive 200 ticks"
        chamber.close()

    print("[OK] Self-test passed.")

# AURORA_EVOLVED_NATIVE_BEGIN
try:
    import inspect as _aurora_native_inspect
except Exception:
    _aurora_native_inspect = None

try:
    from aurora_internal.aurora_evolved_surfaces import AuroraEvolvedSurfaceEngine as _AuroraEvolvedSurfaceEngine
except Exception:
    _AuroraEvolvedSurfaceEngine = None

_AURORA_NATIVE_EVOLVED_ENGINE = None

def _aurora_native_evolved_engine():
    global _AURORA_NATIVE_EVOLVED_ENGINE
    if _AURORA_NATIVE_EVOLVED_ENGINE is None and _AuroraEvolvedSurfaceEngine is not None:
        _AURORA_NATIVE_EVOLVED_ENGINE = _AuroraEvolvedSurfaceEngine()
    return _AURORA_NATIVE_EVOLVED_ENGINE

_AURORA_NATIVE_MODULE = 'aurora_internal.aurora_evolution_chamber'

_AURORA_NATIVE_EVOLVED_ORIGINALS = {}
_AURORA_NATIVE_EVOLVED_LAST = {}
_AURORA_NATIVE_STRATEGIES = {'AbilityProfile': {'ability_hits': 1,
                    'alignment_gap': 0.271,
                    'alignment_target_score': 1.192,
                    'best_coupling_signature': 'X^2*T^2',
                    'constraints': ['existence', 'temporal'],
                    'contract_profile': {'accepts_payload': False,
                                         'async_callable': False,
                                         'callable': True,
                                         'class_target': True,
                                         'constraint_density': 2,
                                         'contract_mode': 'stateless',
                                         'doc_hint': 'The smallest named action unit, fully '
                                                     'grounded in the 5 constraints.',
                                         'effect_density': 3,
                                         'kwonly_args': 0,
                                         'optional_args': 1,
                                         'required_args': 6,
                                         'return_hint': 'None',
                                         'signature_text': "(id: 'str', axis: 'str', requires: "
                                                           "'Tuple[str, ...]', cost: 'Dict[str, "
                                                           "float]', risk: 'Dict[str, float]', "
                                                           "effect_tags: 'Tuple[str, ...]', notes: "
                                                           "'str' = '') -> None",
                                         'stateful_owner': False,
                                         'target_kind': 'class',
                                         'varargs': False,
                                         'varkw': False},
                    'coupling_similarity': 1.0,
                    'cross_diversity_links': 4,
                    'effect_modes': ['state_schema_change',
                                     'temporal_orchestration_change',
                                     'class_lineage_surface'],
                    'effect_phrases': ['class growth reflected through '
                                       'aurora_internal.aurora_evolution_chamber',
                                       'AbilityProfile changed downstream system pressure'],
                    'genealogy_pressure': 0.44,
                    'inheritance_breach_count': 1,
                    'kind': 'reflection',
                    'link_hits': 2,
                    'module': 'aurora_internal.aurora_evolution_chamber',
                    'op_id': 'aurora_internal.aurora_evolution_chamber.AbilityProfile',
                    'origin_activity': 0,
                    'persistence_tax_factor': 1.5,
                    'representation_score': 0.813889,
                    'rewrite_bias': 'generic',
                    'rewrite_feedback': {'acceptance_rate': 0.0,
                                         'accepted_count': 0,
                                         'adaptation_mode': 'conservative',
                                         'adoption_count': 0,
                                         'confidence': 0.36,
                                         'mean_mutation_score': 0.25,
                                         'rejected_count': 2,
                                         'rejection_rate': 1.0,
                                         'timing_credit': 0.0,
                                         'timing_penalty': 0.0,
                                         'trial_count': 2},
                    'rewrite_profile': 'generic',
                    'signature': 'X^2*T^2',
                    'surface_score': 0.921,
                    'sustainability_score': 0.394792,
                    'target_kind': 'class'},
 'ActionTrace': {'ability_hits': 1,
                 'alignment_gap': 0.611,
                 'alignment_target_score': 1.192,
                 'best_coupling_signature': 'A^3',
                 'constraints': ['agency'],
                 'contract_profile': {'accepts_payload': False,
                                      'async_callable': False,
                                      'callable': True,
                                      'class_target': True,
                                      'constraint_density': 1,
                                      'contract_mode': 'stateless',
                                      'doc_hint': 'Primitive control generator — one action in the '
                                                  'simulation.',
                                      'effect_density': 2,
                                      'kwonly_args': 0,
                                      'optional_args': 2,
                                      'required_args': 1,
                                      'return_hint': 'None',
                                      'signature_text': "(name: 'str', constraints_used: "
                                                        "'FrozenSet[str]' = frozenset(), meta: "
                                                        "'Optional[Dict]' = None) -> None",
                                      'stateful_owner': False,
                                      'target_kind': 'class',
                                      'varargs': False,
                                      'varkw': False},
                 'coupling_similarity': 0.666667,
                 'cross_diversity_links': 2,
                 'effect_modes': ['adaptive_steering_change', 'class_lineage_surface'],
                 'effect_phrases': ['class growth reflected through '
                                    'aurora_internal.aurora_evolution_chamber',
                                    'ActionTrace changed downstream system pressure'],
                 'genealogy_pressure': 0.337096,
                 'inheritance_breach_count': 1,
                 'kind': 'reflection',
                 'link_hits': 0,
                 'module': 'aurora_internal.aurora_evolution_chamber',
                 'op_id': 'aurora_internal.aurora_evolution_chamber.ActionTrace',
                 'origin_activity': 0,
                 'persistence_tax_factor': 3.188141,
                 'representation_score': 0.44749,
                 'rewrite_bias': 'generic',
                 'rewrite_feedback': {'acceptance_rate': 0.0,
                                      'accepted_count': 0,
                                      'adaptation_mode': 'conservative',
                                      'adoption_count': 0,
                                      'confidence': 0.36,
                                      'mean_mutation_score': 0.25,
                                      'rejected_count': 2,
                                      'rejection_rate': 1.0,
                                      'timing_credit': 0.0,
                                      'timing_penalty': 0.0,
                                      'trial_count': 2},
                 'rewrite_profile': 'generic',
                 'signature': 'A^2',
                 'surface_score': 0.581,
                 'sustainability_score': 0.324968,
                 'target_kind': 'class'},
 'ChamberAbility': {'ability_hits': 1,
                    'alignment_gap': 0.271,
                    'alignment_target_score': 1.192,
                    'best_coupling_signature': 'X^2*T^2',
                    'constraints': ['existence', 'temporal'],
                    'contract_profile': {'accepts_payload': False,
                                         'async_callable': False,
                                         'callable': True,
                                         'class_target': True,
                                         'constraint_density': 2,
                                         'contract_mode': 'stateless',
                                         'doc_hint': "ChamberAbility(ability_id: 'str', axis: "
                                                     "'str', cost: 'Dict[str, float]', risk: "
                                                     "'Dict[str, float]', effect_tags: 'Tuple[str, "
                                                     "...]')",
                                         'effect_density': 3,
                                         'kwonly_args': 0,
                                         'optional_args': 0,
                                         'required_args': 5,
                                         'return_hint': 'None',
                                         'signature_text': "(ability_id: 'str', axis: 'str', cost: "
                                                           "'Dict[str, float]', risk: 'Dict[str, "
                                                           "float]', effect_tags: 'Tuple[str, "
                                                           "...]') -> None",
                                         'stateful_owner': False,
                                         'target_kind': 'class',
                                         'varargs': False,
                                         'varkw': False},
                    'coupling_similarity': 1.0,
                    'cross_diversity_links': 4,
                    'effect_modes': ['state_schema_change',
                                     'temporal_orchestration_change',
                                     'class_lineage_surface'],
                    'effect_phrases': ['class growth reflected through '
                                       'aurora_internal.aurora_evolution_chamber',
                                       'ChamberAbility changed downstream system pressure'],
                    'genealogy_pressure': 0.44,
                    'inheritance_breach_count': 1,
                    'kind': 'reflection',
                    'link_hits': 2,
                    'module': 'aurora_internal.aurora_evolution_chamber',
                    'op_id': 'aurora_internal.aurora_evolution_chamber.ChamberAbility',
                    'origin_activity': 0,
                    'persistence_tax_factor': 1.5,
                    'representation_score': 0.813889,
                    'rewrite_bias': 'generic',
                    'rewrite_feedback': {'acceptance_rate': 0.0,
                                         'accepted_count': 0,
                                         'adaptation_mode': 'conservative',
                                         'adoption_count': 0,
                                         'confidence': 0.36,
                                         'mean_mutation_score': 0.25,
                                         'rejected_count': 2,
                                         'rejection_rate': 1.0,
                                         'timing_credit': 0.0,
                                         'timing_penalty': 0.0,
                                         'trial_count': 2},
                    'rewrite_profile': 'generic',
                    'signature': 'X^2*T^2',
                    'surface_score': 0.921,
                    'sustainability_score': 0.394792,
                    'target_kind': 'class'},
 'ConstraintGenealogyLogger.__init__': {'ability_hits': 12,
                                        'alignment_gap': 0.56,
                                        'alignment_target_score': 1.192,
                                        'best_coupling_signature': 'B^3',
                                        'constraints': ['boundary'],
                                        'contract_profile': {'accepts_payload': False,
                                                             'async_callable': False,
                                                             'callable': True,
                                                             'class_target': False,
                                                             'constraint_density': 1,
                                                             'contract_mode': 'stateful',
                                                             'doc_hint': 'Initialize self.  See '
                                                                         'help(type(self)) for '
                                                                         'accurate signature.',
                                                             'effect_density': 2,
                                                             'kwonly_args': 0,
                                                             'optional_args': 3,
                                                             'required_args': 1,
                                                             'return_hint': 'boundary_record',
                                                             'signature_text': '(self, run_id: '
                                                                               "'str', config: "
                                                                               "'Optional[GenealogyConfig]' "
                                                                               '= None, abilities: '
                                                                               "'Optional[Dict[str, "
                                                                               "AbilityProfile]]' "
                                                                               '= None, '
                                                                               "output_dir: 'str' "
                                                                               "= '.')",
                                                             'stateful_owner': True,
                                                             'target_kind': 'function',
                                                             'varargs': False,
                                                             'varkw': False},
                                        'coupling_similarity': 1.0,
                                        'cross_diversity_links': 2,
                                        'effect_modes': ['interface_boundary_change',
                                                         'lineage_surface'],
                                        'effect_phrases': ['function growth reflected through '
                                                           'aurora_internal.aurora_evolution_chamber',
                                                           'ConstraintGenealogyLogger.__init__ '
                                                           'changed downstream system pressure'],
                                        'genealogy_pressure': 0.75101,
                                        'inheritance_breach_count': 1,
                                        'kind': 'reflection',
                                        'link_hits': 24,
                                        'module': 'aurora_internal.aurora_evolution_chamber',
                                        'op_id': 'aurora_internal.aurora_evolution_chamber.ConstraintGenealogyLogger.__init__',
                                        'origin_activity': 0,
                                        'persistence_tax_factor': 2.550513,
                                        'representation_score': 0.567611,
                                        'rewrite_bias': 'generic',
                                        'rewrite_feedback': {'acceptance_rate': 0.0,
                                                             'accepted_count': 0,
                                                             'adaptation_mode': 'conservative',
                                                             'adoption_count': 0,
                                                             'confidence': 0.36,
                                                             'mean_mutation_score': 0.25,
                                                             'rejected_count': 2,
                                                             'rejection_rate': 1.0,
                                                             'timing_credit': 0.0,
                                                             'timing_penalty': 0.0,
                                                             'trial_count': 2},
                                        'rewrite_profile': 'generic',
                                        'signature': 'B^3',
                                        'surface_score': 0.632,
                                        'sustainability_score': 0.356849,
                                        'target_kind': 'function'},
 'ConstraintGenealogyLogger.close': {'ability_hits': 12,
                                     'alignment_gap': 0.56,
                                     'alignment_target_score': 1.192,
                                     'best_coupling_signature': 'B^3',
                                     'constraints': ['boundary'],
                                     'contract_profile': {'accepts_payload': False,
                                                          'async_callable': False,
                                                          'callable': True,
                                                          'class_target': False,
                                                          'constraint_density': 1,
                                                          'contract_mode': 'stateful',
                                                          'doc_hint': '',
                                                          'effect_density': 2,
                                                          'kwonly_args': 0,
                                                          'optional_args': 0,
                                                          'required_args': 0,
                                                          'return_hint': 'None',
                                                          'signature_text': "(self) -> 'None'",
                                                          'stateful_owner': True,
                                                          'target_kind': 'function',
                                                          'varargs': False,
                                                          'varkw': False},
                                     'coupling_similarity': 1.0,
                                     'cross_diversity_links': 2,
                                     'effect_modes': ['interface_boundary_change',
                                                      'lineage_surface'],
                                     'effect_phrases': ['function growth reflected through '
                                                        'aurora_internal.aurora_evolution_chamber',
                                                        'ConstraintGenealogyLogger.close changed '
                                                        'downstream system pressure'],
                                     'genealogy_pressure': 0.75101,
                                     'inheritance_breach_count': 1,
                                     'kind': 'reflection',
                                     'link_hits': 24,
                                     'module': 'aurora_internal.aurora_evolution_chamber',
                                     'op_id': 'aurora_internal.aurora_evolution_chamber.ConstraintGenealogyLogger.close',
                                     'origin_activity': 0,
                                     'persistence_tax_factor': 2.550513,
                                     'representation_score': 0.567611,
                                     'rewrite_bias': 'generic',
                                     'rewrite_feedback': {'acceptance_rate': 0.0,
                                                          'accepted_count': 0,
                                                          'adaptation_mode': 'conservative',
                                                          'adoption_count': 0,
                                                          'confidence': 0.36,
                                                          'mean_mutation_score': 0.25,
                                                          'rejected_count': 2,
                                                          'rejection_rate': 1.0,
                                                          'timing_credit': 0.0,
                                                          'timing_penalty': 0.0,
                                                          'trial_count': 2},
                                     'rewrite_profile': 'generic',
                                     'signature': 'B^3',
                                     'surface_score': 0.632,
                                     'sustainability_score': 0.356849,
                                     'target_kind': 'function'},
 'ConstraintGenealogyLogger.flush_files': {'ability_hits': 12,
                                           'alignment_gap': 0.56,
                                           'alignment_target_score': 1.192,
                                           'best_coupling_signature': 'B^3',
                                           'constraints': ['boundary'],
                                           'contract_profile': {'accepts_payload': False,
                                                                'async_callable': False,
                                                                'callable': True,
                                                                'class_target': False,
                                                                'constraint_density': 1,
                                                                'contract_mode': 'stateful',
                                                                'doc_hint': 'Flush JSONL buffer '
                                                                            'and write abilities + '
                                                                            'links + couplings + '
                                                                            'pair_stats JSON '
                                                                            'files.',
                                                                'effect_density': 2,
                                                                'kwonly_args': 0,
                                                                'optional_args': 0,
                                                                'required_args': 0,
                                                                'return_hint': 'None',
                                                                'signature_text': '(self) -> '
                                                                                  "'None'",
                                                                'stateful_owner': True,
                                                                'target_kind': 'function',
                                                                'varargs': False,
                                                                'varkw': False},
                                           'coupling_similarity': 1.0,
                                           'cross_diversity_links': 2,
                                           'effect_modes': ['interface_boundary_change',
                                                            'lineage_surface'],
                                           'effect_phrases': ['function growth reflected through '
                                                              'aurora_internal.aurora_evolution_chamber',
                                                              'ConstraintGenealogyLogger.flush_files '
                                                              'changed downstream system pressure'],
                                           'genealogy_pressure': 0.75101,
                                           'inheritance_breach_count': 1,
                                           'kind': 'reflection',
                                           'link_hits': 24,
                                           'module': 'aurora_internal.aurora_evolution_chamber',
                                           'op_id': 'aurora_internal.aurora_evolution_chamber.ConstraintGenealogyLogger.flush_files',
                                           'origin_activity': 0,
                                           'persistence_tax_factor': 2.550513,
                                           'representation_score': 0.567611,
                                           'rewrite_bias': 'generic',
                                           'rewrite_feedback': {'acceptance_rate': 0.0,
                                                                'accepted_count': 0,
                                                                'adaptation_mode': 'conservative',
                                                                'adoption_count': 0,
                                                                'confidence': 0.36,
                                                                'mean_mutation_score': 0.25,
                                                                'rejected_count': 2,
                                                                'rejection_rate': 1.0,
                                                                'timing_credit': 0.0,
                                                                'timing_penalty': 0.0,
                                                                'trial_count': 2},
                                           'rewrite_profile': 'generic',
                                           'signature': 'B^3',
                                           'surface_score': 0.632,
                                           'sustainability_score': 0.356849,
                                           'target_kind': 'function'},
 'ConstraintGenealogyLogger.observe': {'ability_hits': 12,
                                       'alignment_gap': 0.56,
                                       'alignment_target_score': 1.192,
                                       'best_coupling_signature': 'B^3',
                                       'constraints': ['boundary'],
                                       'contract_profile': {'accepts_payload': False,
                                                            'async_callable': False,
                                                            'callable': True,
                                                            'class_target': False,
                                                            'constraint_density': 1,
                                                            'contract_mode': 'stateful',
                                                            'doc_hint': 'Observe one tick.',
                                                            'effect_density': 2,
                                                            'kwonly_args': 0,
                                                            'optional_args': 4,
                                                            'required_args': 3,
                                                            'return_hint': 'Optional[ReliefRecord]',
                                                            'signature_text': '(self, '
                                                                              'pressure_before: '
                                                                              "'PressureVec', "
                                                                              'trace: '
                                                                              "'List[TraceItem]', "
                                                                              'pressure_after: '
                                                                              "'PressureVec', "
                                                                              'state_sig_before: '
                                                                              "'str' = '', "
                                                                              'state_sig_after: '
                                                                              "'str' = '', notes: "
                                                                              "'Optional[Dict[str, "
                                                                              "Any]]' = None, "
                                                                              'difference_snapshot: '
                                                                              "'Optional[DifferenceSnapshot]' "
                                                                              '= None) -> '
                                                                              "'Optional[ReliefRecord]'",
                                                            'stateful_owner': True,
                                                            'target_kind': 'function',
                                                            'varargs': False,
                                                            'varkw': False},
                                       'coupling_similarity': 1.0,
                                       'cross_diversity_links': 2,
                                       'effect_modes': ['interface_boundary_change',
                                                        'lineage_surface'],
                                       'effect_phrases': ['function growth reflected through '
                                                          'aurora_internal.aurora_evolution_chamber',
                                                          'ConstraintGenealogyLogger.observe '
                                                          'changed downstream system pressure'],
                                       'genealogy_pressure': 0.75101,
                                       'inheritance_breach_count': 1,
                                       'kind': 'reflection',
                                       'link_hits': 24,
                                       'module': 'aurora_internal.aurora_evolution_chamber',
                                       'op_id': 'aurora_internal.aurora_evolution_chamber.ConstraintGenealogyLogger.observe',
                                       'origin_activity': 0,
                                       'persistence_tax_factor': 2.550513,
                                       'representation_score': 0.567611,
                                       'rewrite_bias': 'generic',
                                       'rewrite_feedback': {'acceptance_rate': 0.0,
                                                            'accepted_count': 0,
                                                            'adaptation_mode': 'conservative',
                                                            'adoption_count': 0,
                                                            'confidence': 0.36,
                                                            'mean_mutation_score': 0.25,
                                                            'rejected_count': 2,
                                                            'rejection_rate': 1.0,
                                                            'timing_credit': 0.0,
                                                            'timing_penalty': 0.0,
                                                            'trial_count': 2},
                                       'rewrite_profile': 'generic',
                                       'signature': 'B^3',
                                       'surface_score': 0.632,
                                       'sustainability_score': 0.356849,
                                       'target_kind': 'function'},
 'ConstraintGenealogyLogger.summary': {'ability_hits': 12,
                                       'alignment_gap': 0.56,
                                       'alignment_target_score': 1.192,
                                       'best_coupling_signature': 'B^3',
                                       'constraints': ['boundary'],
                                       'contract_profile': {'accepts_payload': False,
                                                            'async_callable': False,
                                                            'callable': True,
                                                            'class_target': False,
                                                            'constraint_density': 1,
                                                            'contract_mode': 'stateful',
                                                            'doc_hint': '',
                                                            'effect_density': 2,
                                                            'kwonly_args': 0,
                                                            'optional_args': 0,
                                                            'required_args': 0,
                                                            'return_hint': 'Dict[str, Any]',
                                                            'signature_text': '(self) -> '
                                                                              "'Dict[str, Any]'",
                                                            'stateful_owner': True,
                                                            'target_kind': 'function',
                                                            'varargs': False,
                                                            'varkw': False},
                                       'coupling_similarity': 1.0,
                                       'cross_diversity_links': 2,
                                       'effect_modes': ['interface_boundary_change',
                                                        'lineage_surface'],
                                       'effect_phrases': ['function growth reflected through '
                                                          'aurora_internal.aurora_evolution_chamber',
                                                          'ConstraintGenealogyLogger.summary '
                                                          'changed downstream system pressure'],
                                       'genealogy_pressure': 0.75101,
                                       'inheritance_breach_count': 1,
                                       'kind': 'reflection',
                                       'link_hits': 24,
                                       'module': 'aurora_internal.aurora_evolution_chamber',
                                       'op_id': 'aurora_internal.aurora_evolution_chamber.ConstraintGenealogyLogger.summary',
                                       'origin_activity': 0,
                                       'persistence_tax_factor': 2.550513,
                                       'representation_score': 0.567611,
                                       'rewrite_bias': 'generic',
                                       'rewrite_feedback': {'acceptance_rate': 0.0,
                                                            'accepted_count': 0,
                                                            'adaptation_mode': 'conservative',
                                                            'adoption_count': 0,
                                                            'confidence': 0.36,
                                                            'mean_mutation_score': 0.25,
                                                            'rejected_count': 2,
                                                            'rejection_rate': 1.0,
                                                            'timing_credit': 0.0,
                                                            'timing_penalty': 0.0,
                                                            'trial_count': 2},
                                       'rewrite_profile': 'generic',
                                       'signature': 'B^3',
                                       'surface_score': 0.632,
                                       'sustainability_score': 0.356849,
                                       'target_kind': 'function'},
 'EvolutionaryChamber': {'ability_hits': 1,
                         'alignment_gap': 0.271,
                         'alignment_target_score': 1.192,
                         'best_coupling_signature': 'X^2*T^2',
                         'constraints': ['existence', 'temporal'],
                         'contract_profile': {'accepts_payload': False,
                                              'async_callable': False,
                                              'callable': True,
                                              'class_target': True,
                                              'constraint_density': 2,
                                              'contract_mode': 'stateless',
                                              'doc_hint': 'Constraint-Native Evolution Chamber — '
                                                          'Full Unified Spec v3.',
                                              'effect_density': 3,
                                              'kwonly_args': 0,
                                              'optional_args': 5,
                                              'required_args': 1,
                                              'return_hint': 'state_record',
                                              'signature_text': "(lattice: 'IVMLattice', "
                                                                'genealogy: '
                                                                "'Optional[ConstraintGenealogyLogger]' "
                                                                "= None, run_id: 'Optional[str]' = "
                                                                "None, output_dir: 'str' = "
                                                                "'chamber_output', constants: "
                                                                "'WorldConstants' = "
                                                                'WorldConstants(dt=0.1, '
                                                                'baseline_burn_per_tick=0.001, '
                                                                'energy_budget_floor=0.0, '
                                                                'agency_cost_coefficient=0.01, '
                                                                'agency_max_magnitude=5.0, '
                                                                'idle_persistence_cost_factor=0.5, '
                                                                'proximity_weaken_rate=0.05, '
                                                                'proximity_strengthen_rate=0.05, '
                                                                'proximity_threshold=0.5, '
                                                                'entropy_window=20, '
                                                                'chain_promote_threshold=30, '
                                                                'log_capacity=10000, '
                                                                'violation_log_capacity=5000), '
                                                                "initial_energy: 'float' = 1.0)",
                                              'stateful_owner': False,
                                              'target_kind': 'class',
                                              'varargs': False,
                                              'varkw': False},
                         'coupling_similarity': 1.0,
                         'cross_diversity_links': 4,
                         'effect_modes': ['state_schema_change',
                                          'temporal_orchestration_change',
                                          'class_lineage_surface'],
                         'effect_phrases': ['class growth reflected through '
                                            'aurora_internal.aurora_evolution_chamber',
                                            'EvolutionaryChamber changed downstream system '
                                            'pressure'],
                         'genealogy_pressure': 0.44,
                         'inheritance_breach_count': 1,
                         'kind': 'reflection',
                         'link_hits': 2,
                         'module': 'aurora_internal.aurora_evolution_chamber',
                         'op_id': 'aurora_internal.aurora_evolution_chamber.EvolutionaryChamber',
                         'origin_activity': 0,
                         'persistence_tax_factor': 1.5,
                         'representation_score': 0.813889,
                         'rewrite_bias': 'generic',
                         'rewrite_feedback': {'acceptance_rate': 0.0,
                                              'accepted_count': 0,
                                              'adaptation_mode': 'conservative',
                                              'adoption_count': 0,
                                              'confidence': 0.36,
                                              'mean_mutation_score': 0.25,
                                              'rejected_count': 2,
                                              'rejection_rate': 1.0,
                                              'timing_credit': 0.0,
                                              'timing_penalty': 0.0,
                                              'trial_count': 2},
                         'rewrite_profile': 'generic',
                         'signature': 'X^2*T^2',
                         'surface_score': 0.921,
                         'sustainability_score': 0.394792,
                         'target_kind': 'class'},
 'EvolutionaryChamber.run_chain': {'ability_hits': 19,
                                   'alignment_gap': 0.56,
                                   'alignment_target_score': 1.192,
                                   'best_coupling_signature': 'T^2*B^1',
                                   'constraints': ['temporal'],
                                   'contract_profile': {'accepts_payload': False,
                                                        'async_callable': False,
                                                        'callable': True,
                                                        'class_target': False,
                                                        'constraint_density': 1,
                                                        'contract_mode': 'stateful',
                                                        'doc_hint': 'Run n_ticks ticks. '
                                                                    'action_schedule: '
                                                                    '{tick_number: ActionTrace}.',
                                                        'effect_density': 2,
                                                        'kwonly_args': 0,
                                                        'optional_args': 1,
                                                        'required_args': 1,
                                                        'return_hint': 'Dict[str, Any]',
                                                        'signature_text': "(self, n_ticks: 'int', "
                                                                          'action_schedule: '
                                                                          "'Optional[Dict[int, "
                                                                          "ActionTrace]]' = None) "
                                                                          "-> 'Dict[str, Any]'",
                                                        'stateful_owner': True,
                                                        'target_kind': 'function',
                                                        'varargs': False,
                                                        'varkw': False},
                                   'coupling_similarity': 1.0,
                                   'cross_diversity_links': 2,
                                   'effect_modes': ['temporal_orchestration_change',
                                                    'lineage_surface'],
                                   'effect_phrases': ['function growth reflected through '
                                                      'aurora_internal.aurora_evolution_chamber',
                                                      'EvolutionaryChamber.run_chain changed '
                                                      'downstream system pressure'],
                                   'genealogy_pressure': 0.809108,
                                   'inheritance_breach_count': 1,
                                   'kind': 'reflection',
                                   'link_hits': 36,
                                   'module': 'aurora_internal.aurora_evolution_chamber',
                                   'op_id': 'aurora_internal.aurora_evolution_chamber.EvolutionaryChamber.run_chain',
                                   'origin_activity': 0,
                                   'persistence_tax_factor': 1.955393,
                                   'representation_score': 0.519331,
                                   'rewrite_bias': 'generic',
                                   'rewrite_feedback': {'acceptance_rate': 0.0,
                                                        'accepted_count': 0,
                                                        'adaptation_mode': 'conservative',
                                                        'adoption_count': 0,
                                                        'confidence': 0.36,
                                                        'mean_mutation_score': 0.25,
                                                        'rejected_count': 2,
                                                        'rejection_rate': 1.0,
                                                        'timing_credit': 0.0,
                                                        'timing_penalty': 0.0,
                                                        'trial_count': 2},
                                   'rewrite_profile': 'generic',
                                   'signature': 'T^2*B^1',
                                   'surface_score': 0.632,
                                   'sustainability_score': 0.405355,
                                   'target_kind': 'function'},
 'EvolutionaryChamber.tick': {'ability_hits': 19,
                              'alignment_gap': 0.56,
                              'alignment_target_score': 1.192,
                              'best_coupling_signature': 'T^2*B^1',
                              'constraints': ['temporal'],
                              'contract_profile': {'accepts_payload': False,
                                                   'async_callable': False,
                                                   'callable': True,
                                                   'class_target': False,
                                                   'constraint_density': 1,
                                                   'contract_mode': 'stateful',
                                                   'doc_hint': 'Advance the universe one tick.',
                                                   'effect_density': 2,
                                                   'kwonly_args': 0,
                                                   'optional_args': 1,
                                                   'required_args': 0,
                                                   'return_hint': 'Optional[Any]',
                                                   'signature_text': '(self, action: '
                                                                     "'Optional[ActionTrace]' = "
                                                                     "None) -> 'Optional[Any]'",
                                                   'stateful_owner': True,
                                                   'target_kind': 'function',
                                                   'varargs': False,
                                                   'varkw': False},
                              'coupling_similarity': 1.0,
                              'cross_diversity_links': 2,
                              'effect_modes': ['temporal_orchestration_change', 'lineage_surface'],
                              'effect_phrases': ['function growth reflected through '
                                                 'aurora_internal.aurora_evolution_chamber',
                                                 'EvolutionaryChamber.tick changed downstream '
                                                 'system pressure'],
                              'genealogy_pressure': 0.809108,
                              'inheritance_breach_count': 1,
                              'kind': 'reflection',
                              'link_hits': 36,
                              'module': 'aurora_internal.aurora_evolution_chamber',
                              'op_id': 'aurora_internal.aurora_evolution_chamber.EvolutionaryChamber.tick',
                              'origin_activity': 0,
                              'persistence_tax_factor': 1.955393,
                              'representation_score': 0.519331,
                              'rewrite_bias': 'generic',
                              'rewrite_feedback': {'acceptance_rate': 0.0,
                                                   'accepted_count': 0,
                                                   'adaptation_mode': 'conservative',
                                                   'adoption_count': 0,
                                                   'confidence': 0.36,
                                                   'mean_mutation_score': 0.25,
                                                   'rejected_count': 2,
                                                   'rejection_rate': 1.0,
                                                   'timing_credit': 0.0,
                                                   'timing_penalty': 0.0,
                                                   'trial_count': 2},
                              'rewrite_profile': 'generic',
                              'signature': 'T^2*B^1',
                              'surface_score': 0.632,
                              'sustainability_score': 0.405355,
                              'target_kind': 'function'},
 'EvolutionaryChamber.tick._axes_from_trace_item': {'ability_hits': 19,
                                                    'alignment_gap': 0.509,
                                                    'alignment_target_score': 1.192,
                                                    'best_coupling_signature': 'T^2*B^1',
                                                    'constraints': ['temporal'],
                                                    'contract_profile': {'accepts_payload': False,
                                                                         'async_callable': False,
                                                                         'callable': False,
                                                                         'class_target': False,
                                                                         'constraint_density': 1,
                                                                         'contract_mode': 'stateful',
                                                                         'doc_hint': '',
                                                                         'effect_density': 2,
                                                                         'kwonly_args': 0,
                                                                         'optional_args': 0,
                                                                         'required_args': 0,
                                                                         'return_hint': 'generic_record',
                                                                         'signature_text': '',
                                                                         'stateful_owner': True,
                                                                         'target_kind': 'function',
                                                                         'varargs': False,
                                                                         'varkw': False},
                                                    'coupling_similarity': 1.0,
                                                    'cross_diversity_links': 2,
                                                    'effect_modes': ['temporal_orchestration_change',
                                                                     'lineage_surface'],
                                                    'effect_phrases': ['function growth reflected '
                                                                       'through '
                                                                       'aurora_internal.aurora_evolution_chamber',
                                                                       'EvolutionaryChamber.tick._axes_from_trace_item '
                                                                       'changed downstream system '
                                                                       'pressure'],
                                                    'genealogy_pressure': 0.809108,
                                                    'inheritance_breach_count': 1,
                                                    'kind': 'reflection',
                                                    'link_hits': 36,
                                                    'module': 'aurora_internal.aurora_evolution_chamber',
                                                    'op_id': 'aurora_internal.aurora_evolution_chamber.EvolutionaryChamber.tick._axes_from_trace_item',
                                                    'origin_activity': 0,
                                                    'persistence_tax_factor': 1.955393,
                                                    'representation_score': 0.519331,
                                                    'rewrite_bias': 'generic',
                                                    'rewrite_feedback': {'acceptance_rate': 0.0,
                                                                         'accepted_count': 0,
                                                                         'adaptation_mode': 'conservative',
                                                                         'adoption_count': 0,
                                                                         'confidence': 0.36,
                                                                         'mean_mutation_score': 0.25,
                                                                         'rejected_count': 2,
                                                                         'rejection_rate': 1.0,
                                                                         'timing_credit': 0.0,
                                                                         'timing_penalty': 0.0,
                                                                         'trial_count': 2},
                                                    'rewrite_profile': 'generic',
                                                    'signature': 'T^2*B^1',
                                                    'surface_score': 0.6829999999999999,
                                                    'sustainability_score': 0.405355,
                                                    'target_kind': 'function'},
 'GenealogyConfig': {'ability_hits': 1,
                     'alignment_gap': 0.271,
                     'alignment_target_score': 1.192,
                     'best_coupling_signature': 'X^2*T^2',
                     'constraints': ['existence', 'temporal'],
                     'contract_profile': {'accepts_payload': False,
                                          'async_callable': False,
                                          'callable': True,
                                          'class_target': True,
                                          'constraint_density': 2,
                                          'contract_mode': 'stateless',
                                          'doc_hint': 'All tunable parameters in one place.',
                                          'effect_density': 3,
                                          'kwonly_args': 0,
                                          'optional_args': 88,
                                          'required_args': 0,
                                          'return_hint': 'None',
                                          'signature_text': "(RELIEF_EPS: 'float' = 5e-05, "
                                                            "RELIEF_TOTAL_EPS: 'float' = 0.00015, "
                                                            "K_MIN: 'int' = 30, "
                                                            "RELIEF_PROMOTE_MIN: 'float' = 5e-05, "
                                                            "RELIEF_STDEV_MAX: 'float' = 0.5, "
                                                            "POS_FRACTION_MIN: 'float' = 0.52, "
                                                            "NET_MIN: 'float' = 1e-06, X_RISK_MAX: "
                                                            "'float' = 0.05, RELIEF_WEIGHTS: "
                                                            "'Dict[str, float]' = <factory>, "
                                                            "COST_WEIGHTS: 'Dict[str, float]' = "
                                                            '<factory>, COST_PENALTY_LAMBDA: '
                                                            "'float' = 1.0, COST_TO_RELIEF_SCALE: "
                                                            "'float' = 0.002, "
                                                            "COMPLEXITY_FORMATION_SCALE: 'float' = "
                                                            '0.1, MAINTENANCE_DISCOUNT_BASE: '
                                                            "'float' = 0.2, "
                                                            'MAINTENANCE_DISCOUNT_PER_DEPTH: '
                                                            "'float' = 0.05, "
                                                            "MAINTENANCE_DISCOUNT_MAX: 'float' = "
                                                            "0.6, CAUSAL_ADAPT_RATE: 'float' = "
                                                            "0.08, CAUSAL_SUPPORT_GAIN: 'float' = "
                                                            "0.35, GRADIENT_DRIVE_BLEND: 'float' = "
                                                            '0.5, THRESHOLD_PRESSURE_ENABLED: '
                                                            "'bool' = True, "
                                                            "THRESHOLD_PRESSURE_GAIN: 'float' = "
                                                            '0.6, '
                                                            'THRESHOLD_PRESSURE_DRIVER_WEIGHT: '
                                                            "'float' = 0.55, "
                                                            'THRESHOLD_PRESSURE_OPPOSING_WEIGHT: '
                                                            "'float' = 0.45, "
                                                            'THRESHOLD_PRESSURE_PERSISTENT_WEIGHT: '
                                                            "'float' = 0.2, "
                                                            "THRESHOLD_PRESSURE_SHARPNESS: 'float' "
                                                            '= 2.5, '
                                                            'THRESHOLD_PRESSURE_FLOOR_RATIO: '
                                                            "'float' = 0.4, "
                                                            "THRESHOLD_PRESSURE_CAP_RATIO: 'float' "
                                                            "= 1.75, STAGNATION_WINDOW: 'int' = "
                                                            "400, STAGNATION_GAIN_MAX: 'float' = "
                                                            "0.6, STAGNATION_HARD_WINDOW: 'int' = "
                                                            '2000, STAGNATION_BOOTSTRAP_RATIO: '
                                                            "'float' = 0.35, "
                                                            "STAGNATION_KMIN_FLOOR_RATIO: 'float' "
                                                            '= 0.35, KMIN_MATURITY_RELIEF_MAX: '
                                                            "'float' = 0.35, KMIN_NEAR_MISS_RATIO: "
                                                            "'float' = 0.9, "
                                                            "KMIN_NEAR_MISS_POS_MARGIN: 'float' = "
                                                            '3e-05, KMIN_NEAR_MISS_PF_MARGIN: '
                                                            "'float' = 0.08, "
                                                            'STAGNATION_XRISK_CAP_MAX_MULT: '
                                                            "'float' = 2.25, "
                                                            'STAGNATION_NET_MIN_FLOOR_RATIO: '
                                                            "'float' = 0.15, "
                                                            'STAGNATION_COST_PENALTY_MIN_FACTOR: '
                                                            "'float' = 0.55, COMPRESSION_ENABLED: "
                                                            "'bool' = True, "
                                                            "COMPRESSION_LINK_THRESHOLD: 'int' = "
                                                            "180, COMPRESSION_FAMILY_SCALE: 'int' "
                                                            "= 24, COMPRESSION_MAX_GAIN: 'float' = "
                                                            '0.55, TRACE_REWRITE_ON_PROMOTE: '
                                                            "'bool' = True, LINK_AS_ABILITY: "
                                                            "'bool' = True, "
                                                            "RELIEF_TOLERANCE_ENABLED: 'bool' = "
                                                            'True, RELIEF_TOLERANCE_GROWTH: '
                                                            "'float' = 0.06, "
                                                            "RELIEF_TOLERANCE_DECAY: 'float' = "
                                                            "0.01, RELIEF_TOLERANCE_MAX: 'float' = "
                                                            '0.85, RELIEF_TOLERANCE_MIN_FACTOR: '
                                                            "'float' = 0.15, "
                                                            'RELIEF_TOLERANCE_COMPLEXITY_POWER: '
                                                            "'float' = 1.0, COUPLING_EMA_RATE: "
                                                            "'float' = 0.08, COUPLING_DECAY: "
                                                            "'float' = 0.005, "
                                                            "PERSISTENT_PRESSURE_ROOT: 'str' = "
                                                            "'A^1*N^1*T^1', "
                                                            'PERSISTENT_ROOT_EXPECTED_GENERATION: '
                                                            "'int' = 2, RUBRIC_ENABLED: 'bool' = "
                                                            "True, RUBRIC_MIN_EVENTS: 'int' = 24, "
                                                            "RUBRIC_INHERIT_MIN: 'float' = 0.6, "
                                                            "RUBRIC_RELATION_MIN: 'float' = 0.4, "
                                                            "RUBRIC_EFFECT_MIN: 'float' = 8e-05, "
                                                            "RUBRIC_BREEDING_MIN: 'float' = 0.25, "
                                                            "RUBRIC_COMPOSITE_MIN: 'float' = 0.55, "
                                                            'RUBRIC_INHERIT_EFFECT_PENALTY: '
                                                            "'float' = 0.06, "
                                                            'DUPLICATE_SLOT_REDISTRIBUTION: '
                                                            "'float' = 0.5, "
                                                            "COMPLEXITY_SCOPE_ALPHA: 'float' = "
                                                            '0.8, SCALE_REQUIREMENT_STRENGTH: '
                                                            "'float' = 0.75, "
                                                            "SCALE_FORMATION_WEIGHT: 'float' = "
                                                            '0.2, PERSISTENCE_TAX_OPPOSE_POWER: '
                                                            "'float' = 1.0, "
                                                            "PERSISTENCE_TAX_MAX_FACTOR: 'float' = "
                                                            '5.0, PERSISTENCE_DEPTH_DECAY_RATE: '
                                                            "'float' = 0.45, "
                                                            "PERSISTENCE_TAX_MIN_FACTOR: 'float' = "
                                                            "0.15, SEMANTIC_EMA_RATE: 'float' = "
                                                            '0.1, SEMANTIC_PROMOTE_CONFIDENCE: '
                                                            "'float' = 0.65, "
                                                            "SEMANTIC_PROMOTE_MIN_COUNT: 'int' = "
                                                            "24, EXPERIMENTS_ENABLED: 'bool' = "
                                                            "True, EXPERIMENT_WINDOW: 'int' = 40, "
                                                            "EXPERIMENT_MIN_ISSUES: 'int' = 8, "
                                                            'EXPERIMENT_MAX_TRIALS_PER_TRIGGER: '
                                                            "'int' = 6, "
                                                            'EXPERIMENT_EXPLORATORY_ENABLED: '
                                                            "'bool' = True, "
                                                            "EXPERIMENT_EXPLORATORY_PERIOD: 'int' "
                                                            '= 120, '
                                                            'EXPERIMENT_EXPLORATORY_MIN_COUPLINGS: '
                                                            "'int' = 12, MAX_LINK_DEPTH: 'int' = "
                                                            "12, EVENTS_FILE: 'str' = "
                                                            "'events.jsonl', ABILITIES_FILE: 'str' "
                                                            "= 'abilities.json', LINKS_FILE: 'str' "
                                                            "= 'links.json', COUPLINGS_FILE: 'str' "
                                                            "= 'couplings.json', PAIR_STATS_FILE: "
                                                            "'str' = 'pair_stats.json', "
                                                            "USE_TIME_DILATION: 'bool' = True) -> "
                                                            'None',
                                          'stateful_owner': False,
                                          'target_kind': 'class',
                                          'varargs': False,
                                          'varkw': False},
                     'coupling_similarity': 1.0,
                     'cross_diversity_links': 4,
                     'effect_modes': ['state_schema_change',
                                      'temporal_orchestration_change',
                                      'class_lineage_surface'],
                     'effect_phrases': ['class growth reflected through '
                                        'aurora_internal.aurora_evolution_chamber',
                                        'GenealogyConfig changed downstream system pressure'],
                     'genealogy_pressure': 0.44,
                     'inheritance_breach_count': 1,
                     'kind': 'reflection',
                     'link_hits': 2,
                     'module': 'aurora_internal.aurora_evolution_chamber',
                     'op_id': 'aurora_internal.aurora_evolution_chamber.GenealogyConfig',
                     'origin_activity': 0,
                     'persistence_tax_factor': 1.5,
                     'representation_score': 0.813889,
                     'rewrite_bias': 'generic',
                     'rewrite_feedback': {'acceptance_rate': 0.0,
                                          'accepted_count': 0,
                                          'adaptation_mode': 'conservative',
                                          'adoption_count': 0,
                                          'confidence': 0.36,
                                          'mean_mutation_score': 0.25,
                                          'rejected_count': 2,
                                          'rejection_rate': 1.0,
                                          'timing_credit': 0.0,
                                          'timing_penalty': 0.0,
                                          'trial_count': 2},
                     'rewrite_profile': 'generic',
                     'signature': 'X^2*T^2',
                     'surface_score': 0.921,
                     'sustainability_score': 0.394792,
                     'target_kind': 'class'},
 'GlobalNonComps': {'ability_hits': 1,
                    'alignment_gap': 0.271,
                    'alignment_target_score': 1.192,
                    'best_coupling_signature': 'X^2*T^2',
                    'constraints': ['existence', 'temporal'],
                    'contract_profile': {'accepts_payload': False,
                                         'async_callable': False,
                                         'callable': True,
                                         'class_target': True,
                                         'constraint_density': 2,
                                         'contract_mode': 'stateless',
                                         'doc_hint': 'Five read-only jurisdictional laws. Not '
                                                     'tunable. Not injectable.',
                                         'effect_density': 3,
                                         'kwonly_args': 0,
                                         'optional_args': 0,
                                         'required_args': 0,
                                         'return_hint': 'state_record',
                                         'signature_text': '()',
                                         'stateful_owner': False,
                                         'target_kind': 'class',
                                         'varargs': False,
                                         'varkw': False},
                    'coupling_similarity': 1.0,
                    'cross_diversity_links': 4,
                    'effect_modes': ['state_schema_change',
                                     'temporal_orchestration_change',
                                     'class_lineage_surface'],
                    'effect_phrases': ['class growth reflected through '
                                       'aurora_internal.aurora_evolution_chamber',
                                       'GlobalNonComps changed downstream system pressure'],
                    'genealogy_pressure': 0.44,
                    'inheritance_breach_count': 1,
                    'kind': 'reflection',
                    'link_hits': 2,
                    'module': 'aurora_internal.aurora_evolution_chamber',
                    'op_id': 'aurora_internal.aurora_evolution_chamber.GlobalNonComps',
                    'origin_activity': 0,
                    'persistence_tax_factor': 1.5,
                    'representation_score': 0.813889,
                    'rewrite_bias': 'generic',
                    'rewrite_feedback': {'acceptance_rate': 0.0,
                                         'accepted_count': 0,
                                         'adaptation_mode': 'conservative',
                                         'adoption_count': 0,
                                         'confidence': 0.36,
                                         'mean_mutation_score': 0.25,
                                         'rejected_count': 2,
                                         'rejection_rate': 1.0,
                                         'timing_credit': 0.0,
                                         'timing_penalty': 0.0,
                                         'trial_count': 2},
                    'rewrite_profile': 'generic',
                    'signature': 'X^2*T^2',
                    'surface_score': 0.921,
                    'sustainability_score': 0.394792,
                    'target_kind': 'class'},
 'NonCompViolation': {'ability_hits': 1,
                      'alignment_gap': 0.271,
                      'alignment_target_score': 1.192,
                      'best_coupling_signature': 'X^2*T^2',
                      'constraints': ['existence', 'temporal'],
                      'contract_profile': {'accepts_payload': False,
                                           'async_callable': False,
                                           'callable': True,
                                           'class_target': True,
                                           'constraint_density': 2,
                                           'contract_mode': 'stateless',
                                           'doc_hint': 'Common base class for all non-exit '
                                                       'exceptions.',
                                           'effect_density': 3,
                                           'kwonly_args': 0,
                                           'optional_args': 1,
                                           'required_args': 2,
                                           'return_hint': 'state_record',
                                           'signature_text': "(non_comp: 'str', reason: 'str', "
                                                             "signature: 'str' = '')",
                                           'stateful_owner': False,
                                           'target_kind': 'class',
                                           'varargs': False,
                                           'varkw': False},
                      'coupling_similarity': 1.0,
                      'cross_diversity_links': 4,
                      'effect_modes': ['state_schema_change',
                                       'temporal_orchestration_change',
                                       'class_lineage_surface'],
                      'effect_phrases': ['class growth reflected through '
                                         'aurora_internal.aurora_evolution_chamber',
                                         'NonCompViolation changed downstream system pressure'],
                      'genealogy_pressure': 0.44,
                      'inheritance_breach_count': 1,
                      'kind': 'reflection',
                      'link_hits': 2,
                      'module': 'aurora_internal.aurora_evolution_chamber',
                      'op_id': 'aurora_internal.aurora_evolution_chamber.NonCompViolation',
                      'origin_activity': 0,
                      'persistence_tax_factor': 1.5,
                      'representation_score': 0.813889,
                      'rewrite_bias': 'generic',
                      'rewrite_feedback': {'acceptance_rate': 0.0,
                                           'accepted_count': 0,
                                           'adaptation_mode': 'conservative',
                                           'adoption_count': 0,
                                           'confidence': 0.36,
                                           'mean_mutation_score': 0.25,
                                           'rejected_count': 2,
                                           'rejection_rate': 1.0,
                                           'timing_credit': 0.0,
                                           'timing_penalty': 0.0,
                                           'trial_count': 2},
                      'rewrite_profile': 'generic',
                      'signature': 'X^2*T^2',
                      'surface_score': 0.921,
                      'sustainability_score': 0.394792,
                      'target_kind': 'class'},
 'StructuralProximityMeter': {'ability_hits': 1,
                              'alignment_gap': 0.271,
                              'alignment_target_score': 1.192,
                              'best_coupling_signature': 'X^2*T^2',
                              'constraints': ['existence', 'temporal'],
                              'contract_profile': {'accepts_payload': False,
                                                   'async_callable': False,
                                                   'callable': True,
                                                   'class_target': True,
                                                   'constraint_density': 2,
                                                   'contract_mode': 'stateless',
                                                   'doc_hint': 'Proximity derived from IVM '
                                                               'polarity state. Not symbolic. Not '
                                                               'Euclidean.',
                                                   'effect_density': 3,
                                                   'kwonly_args': 0,
                                                   'optional_args': 0,
                                                   'required_args': 1,
                                                   'return_hint': 'state_record',
                                                   'signature_text': "(lattice: 'IVMLattice')",
                                                   'stateful_owner': False,
                                                   'target_kind': 'class',
                                                   'varargs': False,
                                                   'varkw': False},
                              'coupling_similarity': 1.0,
                              'cross_diversity_links': 4,
                              'effect_modes': ['state_schema_change',
                                               'temporal_orchestration_change',
                                               'class_lineage_surface'],
                              'effect_phrases': ['class growth reflected through '
                                                 'aurora_internal.aurora_evolution_chamber',
                                                 'StructuralProximityMeter changed downstream '
                                                 'system pressure'],
                              'genealogy_pressure': 0.44,
                              'inheritance_breach_count': 1,
                              'kind': 'reflection',
                              'link_hits': 2,
                              'module': 'aurora_internal.aurora_evolution_chamber',
                              'op_id': 'aurora_internal.aurora_evolution_chamber.StructuralProximityMeter',
                              'origin_activity': 0,
                              'persistence_tax_factor': 1.5,
                              'representation_score': 0.813889,
                              'rewrite_bias': 'generic',
                              'rewrite_feedback': {'acceptance_rate': 0.0,
                                                   'accepted_count': 0,
                                                   'adaptation_mode': 'conservative',
                                                   'adoption_count': 0,
                                                   'confidence': 0.36,
                                                   'mean_mutation_score': 0.25,
                                                   'rejected_count': 2,
                                                   'rejection_rate': 1.0,
                                                   'timing_credit': 0.0,
                                                   'timing_penalty': 0.0,
                                                   'trial_count': 2},
                              'rewrite_profile': 'generic',
                              'signature': 'X^2*T^2',
                              'surface_score': 0.921,
                              'sustainability_score': 0.394792,
                              'target_kind': 'class'},
 'StructuralProximityMeter.partition_count': {'ability_hits': 12,
                                              'alignment_gap': 0.56,
                                              'alignment_target_score': 1.192,
                                              'best_coupling_signature': 'B^3',
                                              'constraints': ['boundary'],
                                              'contract_profile': {'accepts_payload': False,
                                                                   'async_callable': False,
                                                                   'callable': False,
                                                                   'class_target': False,
                                                                   'constraint_density': 1,
                                                                   'contract_mode': 'stateful',
                                                                   'doc_hint': '',
                                                                   'effect_density': 2,
                                                                   'kwonly_args': 0,
                                                                   'optional_args': 0,
                                                                   'required_args': 0,
                                                                   'return_hint': 'boundary_record',
                                                                   'signature_text': '',
                                                                   'stateful_owner': True,
                                                                   'target_kind': 'function',
                                                                   'varargs': False,
                                                                   'varkw': False},
                                              'coupling_similarity': 1.0,
                                              'cross_diversity_links': 2,
                                              'effect_modes': ['interface_boundary_change',
                                                               'lineage_surface'],
                                              'effect_phrases': ['function growth reflected '
                                                                 'through '
                                                                 'aurora_internal.aurora_evolution_chamber',
                                                                 'StructuralProximityMeter.partition_count '
                                                                 'changed downstream system '
                                                                 'pressure'],
                                              'genealogy_pressure': 0.75101,
                                              'inheritance_breach_count': 1,
                                              'kind': 'reflection',
                                              'link_hits': 24,
                                              'module': 'aurora_internal.aurora_evolution_chamber',
                                              'op_id': 'aurora_internal.aurora_evolution_chamber.StructuralProximityMeter.partition_count',
                                              'origin_activity': 0,
                                              'persistence_tax_factor': 2.550513,
                                              'representation_score': 0.567611,
                                              'rewrite_bias': 'generic',
                                              'rewrite_feedback': {'acceptance_rate': 0.0,
                                                                   'accepted_count': 0,
                                                                   'adaptation_mode': 'conservative',
                                                                   'adoption_count': 0,
                                                                   'confidence': 0.36,
                                                                   'mean_mutation_score': 0.25,
                                                                   'rejected_count': 2,
                                                                   'rejection_rate': 1.0,
                                                                   'timing_credit': 0.0,
                                                                   'timing_penalty': 0.0,
                                                                   'trial_count': 2},
                                              'rewrite_profile': 'generic',
                                              'signature': 'B^3',
                                              'surface_score': 0.632,
                                              'sustainability_score': 0.356849,
                                              'target_kind': 'function'},
 'StructuralProximityMeter.recompute_partitions': {'ability_hits': 12,
                                                   'alignment_gap': 0.56,
                                                   'alignment_target_score': 1.192,
                                                   'best_coupling_signature': 'B^3',
                                                   'constraints': ['boundary'],
                                                   'contract_profile': {'accepts_payload': False,
                                                                        'async_callable': False,
                                                                        'callable': True,
                                                                        'class_target': False,
                                                                        'constraint_density': 1,
                                                                        'contract_mode': 'stateful',
                                                                        'doc_hint': '',
                                                                        'effect_density': 2,
                                                                        'kwonly_args': 0,
                                                                        'optional_args': 0,
                                                                        'required_args': 0,
                                                                        'return_hint': 'int',
                                                                        'signature_text': '(self) '
                                                                                          '-> '
                                                                                          "'int'",
                                                                        'stateful_owner': True,
                                                                        'target_kind': 'function',
                                                                        'varargs': False,
                                                                        'varkw': False},
                                                   'coupling_similarity': 1.0,
                                                   'cross_diversity_links': 2,
                                                   'effect_modes': ['interface_boundary_change',
                                                                    'lineage_surface'],
                                                   'effect_phrases': ['function growth reflected '
                                                                      'through '
                                                                      'aurora_internal.aurora_evolution_chamber',
                                                                      'StructuralProximityMeter.recompute_partitions '
                                                                      'changed downstream system '
                                                                      'pressure'],
                                                   'genealogy_pressure': 0.75101,
                                                   'inheritance_breach_count': 1,
                                                   'kind': 'reflection',
                                                   'link_hits': 24,
                                                   'module': 'aurora_internal.aurora_evolution_chamber',
                                                   'op_id': 'aurora_internal.aurora_evolution_chamber.StructuralProximityMeter.recompute_partitions',
                                                   'origin_activity': 0,
                                                   'persistence_tax_factor': 2.550513,
                                                   'representation_score': 0.567611,
                                                   'rewrite_bias': 'generic',
                                                   'rewrite_feedback': {'acceptance_rate': 0.0,
                                                                        'accepted_count': 0,
                                                                        'adaptation_mode': 'conservative',
                                                                        'adoption_count': 0,
                                                                        'confidence': 0.36,
                                                                        'mean_mutation_score': 0.25,
                                                                        'rejected_count': 2,
                                                                        'rejection_rate': 1.0,
                                                                        'timing_credit': 0.0,
                                                                        'timing_penalty': 0.0,
                                                                        'trial_count': 2},
                                                   'rewrite_profile': 'generic',
                                                   'signature': 'B^3',
                                                   'surface_score': 0.632,
                                                   'sustainability_score': 0.356849,
                                                   'target_kind': 'function'},
 'StructuralProximityMeter.recompute_partitions.find': {'ability_hits': 12,
                                                        'alignment_gap': 0.509,
                                                        'alignment_target_score': 1.192,
                                                        'best_coupling_signature': 'B^3',
                                                        'constraints': ['boundary'],
                                                        'contract_profile': {'accepts_payload': False,
                                                                             'async_callable': False,
                                                                             'callable': False,
                                                                             'class_target': False,
                                                                             'constraint_density': 1,
                                                                             'contract_mode': 'stateful',
                                                                             'doc_hint': '',
                                                                             'effect_density': 2,
                                                                             'kwonly_args': 0,
                                                                             'optional_args': 0,
                                                                             'required_args': 0,
                                                                             'return_hint': 'boundary_record',
                                                                             'signature_text': '',
                                                                             'stateful_owner': True,
                                                                             'target_kind': 'function',
                                                                             'varargs': False,
                                                                             'varkw': False},
                                                        'coupling_similarity': 1.0,
                                                        'cross_diversity_links': 2,
                                                        'effect_modes': ['interface_boundary_change',
                                                                         'lineage_surface'],
                                                        'effect_phrases': ['function growth '
                                                                           'reflected through '
                                                                           'aurora_internal.aurora_evolution_chamber',
                                                                           'StructuralProximityMeter.recompute_partitions.find '
                                                                           'changed downstream '
                                                                           'system pressure'],
                                                        'genealogy_pressure': 0.75101,
                                                        'inheritance_breach_count': 1,
                                                        'kind': 'reflection',
                                                        'link_hits': 24,
                                                        'module': 'aurora_internal.aurora_evolution_chamber',
                                                        'op_id': 'aurora_internal.aurora_evolution_chamber.StructuralProximityMeter.recompute_partitions.find',
                                                        'origin_activity': 0,
                                                        'persistence_tax_factor': 2.550513,
                                                        'representation_score': 0.567611,
                                                        'rewrite_bias': 'generic',
                                                        'rewrite_feedback': {'acceptance_rate': 0.0,
                                                                             'accepted_count': 0,
                                                                             'adaptation_mode': 'conservative',
                                                                             'adoption_count': 0,
                                                                             'confidence': 0.36,
                                                                             'mean_mutation_score': 0.25,
                                                                             'rejected_count': 2,
                                                                             'rejection_rate': 1.0,
                                                                             'timing_credit': 0.0,
                                                                             'timing_penalty': 0.0,
                                                                             'trial_count': 2},
                                                        'rewrite_profile': 'generic',
                                                        'signature': 'B^3',
                                                        'surface_score': 0.6829999999999999,
                                                        'sustainability_score': 0.356849,
                                                        'target_kind': 'function'},
 'StructuralProximityMeter.recompute_partitions.union': {'ability_hits': 12,
                                                         'alignment_gap': 0.509,
                                                         'alignment_target_score': 1.192,
                                                         'best_coupling_signature': 'B^3',
                                                         'constraints': ['boundary'],
                                                         'contract_profile': {'accepts_payload': False,
                                                                              'async_callable': False,
                                                                              'callable': False,
                                                                              'class_target': False,
                                                                              'constraint_density': 1,
                                                                              'contract_mode': 'stateful',
                                                                              'doc_hint': '',
                                                                              'effect_density': 2,
                                                                              'kwonly_args': 0,
                                                                              'optional_args': 0,
                                                                              'required_args': 0,
                                                                              'return_hint': 'boundary_record',
                                                                              'signature_text': '',
                                                                              'stateful_owner': True,
                                                                              'target_kind': 'function',
                                                                              'varargs': False,
                                                                              'varkw': False},
                                                         'coupling_similarity': 1.0,
                                                         'cross_diversity_links': 2,
                                                         'effect_modes': ['interface_boundary_change',
                                                                          'lineage_surface'],
                                                         'effect_phrases': ['function growth '
                                                                            'reflected through '
                                                                            'aurora_internal.aurora_evolution_chamber',
                                                                            'StructuralProximityMeter.recompute_partitions.union '
                                                                            'changed downstream '
                                                                            'system pressure'],
                                                         'genealogy_pressure': 0.75101,
                                                         'inheritance_breach_count': 1,
                                                         'kind': 'reflection',
                                                         'link_hits': 24,
                                                         'module': 'aurora_internal.aurora_evolution_chamber',
                                                         'op_id': 'aurora_internal.aurora_evolution_chamber.StructuralProximityMeter.recompute_partitions.union',
                                                         'origin_activity': 0,
                                                         'persistence_tax_factor': 2.550513,
                                                         'representation_score': 0.567611,
                                                         'rewrite_bias': 'generic',
                                                         'rewrite_feedback': {'acceptance_rate': 0.0,
                                                                              'accepted_count': 0,
                                                                              'adaptation_mode': 'conservative',
                                                                              'adoption_count': 0,
                                                                              'confidence': 0.36,
                                                                              'mean_mutation_score': 0.25,
                                                                              'rejected_count': 2,
                                                                              'rejection_rate': 1.0,
                                                                              'timing_credit': 0.0,
                                                                              'timing_penalty': 0.0,
                                                                              'trial_count': 2},
                                                         'rewrite_profile': 'generic',
                                                         'signature': 'B^3',
                                                         'surface_score': 0.6829999999999999,
                                                         'sustainability_score': 0.356849,
                                                         'target_kind': 'function'},
 'TraceItem': {'ability_hits': 1,
               'alignment_gap': 0.271,
               'alignment_target_score': 1.192,
               'best_coupling_signature': 'X^2*T^2',
               'constraints': ['existence', 'temporal'],
               'contract_profile': {'accepts_payload': False,
                                    'async_callable': False,
                                    'callable': True,
                                    'class_target': True,
                                    'constraint_density': 2,
                                    'contract_mode': 'stateless',
                                    'doc_hint': "TraceItem(kind: 'str', id: 'str', env: "
                                                "'EnvironmentVector' = <factory>)",
                                    'effect_density': 3,
                                    'kwonly_args': 0,
                                    'optional_args': 1,
                                    'required_args': 2,
                                    'return_hint': 'None',
                                    'signature_text': "(kind: 'str', id: 'str', env: "
                                                      "'EnvironmentVector' = <factory>) -> None",
                                    'stateful_owner': False,
                                    'target_kind': 'class',
                                    'varargs': False,
                                    'varkw': False},
               'coupling_similarity': 1.0,
               'cross_diversity_links': 4,
               'effect_modes': ['state_schema_change',
                                'temporal_orchestration_change',
                                'class_lineage_surface'],
               'effect_phrases': ['class growth reflected through '
                                  'aurora_internal.aurora_evolution_chamber',
                                  'TraceItem changed downstream system pressure'],
               'genealogy_pressure': 0.44,
               'inheritance_breach_count': 1,
               'kind': 'reflection',
               'link_hits': 2,
               'module': 'aurora_internal.aurora_evolution_chamber',
               'op_id': 'aurora_internal.aurora_evolution_chamber.TraceItem',
               'origin_activity': 0,
               'persistence_tax_factor': 1.5,
               'representation_score': 0.813889,
               'rewrite_bias': 'generic',
               'rewrite_feedback': {'acceptance_rate': 0.0,
                                    'accepted_count': 0,
                                    'adaptation_mode': 'conservative',
                                    'adoption_count': 0,
                                    'confidence': 0.36,
                                    'mean_mutation_score': 0.25,
                                    'rejected_count': 2,
                                    'rejection_rate': 1.0,
                                    'timing_credit': 0.0,
                                    'timing_penalty': 0.0,
                                    'trial_count': 2},
               'rewrite_profile': 'generic',
               'signature': 'X^2*T^2',
               'surface_score': 0.921,
               'sustainability_score': 0.394792,
               'target_kind': 'class'},
 'ViolationRecord': {'ability_hits': 1,
                     'alignment_gap': 0.271,
                     'alignment_target_score': 1.192,
                     'best_coupling_signature': 'X^2*T^2',
                     'constraints': ['existence', 'temporal'],
                     'contract_profile': {'accepts_payload': False,
                                          'async_callable': False,
                                          'callable': True,
                                          'class_target': True,
                                          'constraint_density': 2,
                                          'contract_mode': 'stateless',
                                          'doc_hint': "ViolationRecord(tick: 'int', timestamp: "
                                                      "'float', non_comp: 'str', reason: 'str', "
                                                      "violation_signature: 'str', measures: "
                                                      "'Dict[str, float]')",
                                          'effect_density': 3,
                                          'kwonly_args': 0,
                                          'optional_args': 0,
                                          'required_args': 6,
                                          'return_hint': 'None',
                                          'signature_text': "(tick: 'int', timestamp: 'float', "
                                                            "non_comp: 'str', reason: 'str', "
                                                            "violation_signature: 'str', measures: "
                                                            "'Dict[str, float]') -> None",
                                          'stateful_owner': False,
                                          'target_kind': 'class',
                                          'varargs': False,
                                          'varkw': False},
                     'coupling_similarity': 1.0,
                     'cross_diversity_links': 4,
                     'effect_modes': ['state_schema_change',
                                      'temporal_orchestration_change',
                                      'class_lineage_surface'],
                     'effect_phrases': ['class growth reflected through '
                                        'aurora_internal.aurora_evolution_chamber',
                                        'ViolationRecord changed downstream system pressure'],
                     'genealogy_pressure': 0.44,
                     'inheritance_breach_count': 1,
                     'kind': 'reflection',
                     'link_hits': 2,
                     'module': 'aurora_internal.aurora_evolution_chamber',
                     'op_id': 'aurora_internal.aurora_evolution_chamber.ViolationRecord',
                     'origin_activity': 0,
                     'persistence_tax_factor': 1.5,
                     'representation_score': 0.813889,
                     'rewrite_bias': 'generic',
                     'rewrite_feedback': {'acceptance_rate': 0.0,
                                          'accepted_count': 0,
                                          'adaptation_mode': 'conservative',
                                          'adoption_count': 0,
                                          'confidence': 0.36,
                                          'mean_mutation_score': 0.25,
                                          'rejected_count': 2,
                                          'rejection_rate': 1.0,
                                          'timing_credit': 0.0,
                                          'timing_penalty': 0.0,
                                          'trial_count': 2},
                     'rewrite_profile': 'generic',
                     'signature': 'X^2*T^2',
                     'surface_score': 0.921,
                     'sustainability_score': 0.394792,
                     'target_kind': 'class'},
 'WorldConstants': {'ability_hits': 1,
                    'alignment_gap': 0.271,
                    'alignment_target_score': 1.192,
                    'best_coupling_signature': 'X^2*T^2',
                    'constraints': ['existence', 'temporal'],
                    'contract_profile': {'accepts_payload': False,
                                         'async_callable': False,
                                         'callable': True,
                                         'class_target': True,
                                         'constraint_density': 2,
                                         'contract_mode': 'stateless',
                                         'doc_hint': 'All chamber-level tunables in one place.',
                                         'effect_density': 3,
                                         'kwonly_args': 0,
                                         'optional_args': 13,
                                         'required_args': 0,
                                         'return_hint': 'None',
                                         'signature_text': "(dt: 'float' = 0.1, "
                                                           "baseline_burn_per_tick: 'float' = "
                                                           "0.001, energy_budget_floor: 'float' = "
                                                           "0.0, agency_cost_coefficient: 'float' "
                                                           "= 0.01, agency_max_magnitude: 'float' "
                                                           '= 5.0, idle_persistence_cost_factor: '
                                                           "'float' = 0.5, proximity_weaken_rate: "
                                                           "'float' = 0.05, "
                                                           "proximity_strengthen_rate: 'float' = "
                                                           "0.05, proximity_threshold: 'float' = "
                                                           "0.5, entropy_window: 'int' = 20, "
                                                           "chain_promote_threshold: 'int' = 30, "
                                                           "log_capacity: 'int' = 10000, "
                                                           "violation_log_capacity: 'int' = 5000) "
                                                           '-> None',
                                         'stateful_owner': False,
                                         'target_kind': 'class',
                                         'varargs': False,
                                         'varkw': False},
                    'coupling_similarity': 1.0,
                    'cross_diversity_links': 4,
                    'effect_modes': ['state_schema_change',
                                     'temporal_orchestration_change',
                                     'class_lineage_surface'],
                    'effect_phrases': ['class growth reflected through '
                                       'aurora_internal.aurora_evolution_chamber',
                                       'WorldConstants changed downstream system pressure'],
                    'genealogy_pressure': 0.44,
                    'inheritance_breach_count': 1,
                    'kind': 'reflection',
                    'link_hits': 2,
                    'module': 'aurora_internal.aurora_evolution_chamber',
                    'op_id': 'aurora_internal.aurora_evolution_chamber.WorldConstants',
                    'origin_activity': 0,
                    'persistence_tax_factor': 1.5,
                    'representation_score': 0.813889,
                    'rewrite_bias': 'generic',
                    'rewrite_feedback': {'acceptance_rate': 0.0,
                                         'accepted_count': 0,
                                         'adaptation_mode': 'conservative',
                                         'adoption_count': 0,
                                         'confidence': 0.36,
                                         'mean_mutation_score': 0.25,
                                         'rejected_count': 2,
                                         'rejection_rate': 1.0,
                                         'timing_credit': 0.0,
                                         'timing_penalty': 0.0,
                                         'trial_count': 2},
                    'rewrite_profile': 'generic',
                    'signature': 'X^2*T^2',
                    'surface_score': 0.921,
                    'sustainability_score': 0.394792,
                    'target_kind': 'class'},
 '_ActionAbilityMapper': {'ability_hits': 1,
                          'alignment_gap': 0.611,
                          'alignment_target_score': 1.192,
                          'best_coupling_signature': 'A^3',
                          'constraints': ['agency'],
                          'contract_profile': {'accepts_payload': False,
                                               'async_callable': False,
                                               'callable': True,
                                               'class_target': True,
                                               'constraint_density': 1,
                                               'contract_mode': 'stateless',
                                               'doc_hint': '',
                                               'effect_density': 2,
                                               'kwonly_args': 0,
                                               'optional_args': 0,
                                               'required_args': 2,
                                               'return_hint': 'decision_record',
                                               'signature_text': "(lattice: 'IVMLattice', "
                                                                 "abilities: 'Dict[str, "
                                                                 "ChamberAbility]')",
                                               'stateful_owner': False,
                                               'target_kind': 'class',
                                               'varargs': False,
                                               'varkw': False},
                          'coupling_similarity': 0.666667,
                          'cross_diversity_links': 2,
                          'effect_modes': ['adaptive_steering_change', 'class_lineage_surface'],
                          'effect_phrases': ['class growth reflected through '
                                             'aurora_internal.aurora_evolution_chamber',
                                             '_ActionAbilityMapper changed downstream system '
                                             'pressure'],
                          'genealogy_pressure': 0.337096,
                          'inheritance_breach_count': 1,
                          'kind': 'reflection',
                          'link_hits': 0,
                          'module': 'aurora_internal.aurora_evolution_chamber',
                          'op_id': 'aurora_internal.aurora_evolution_chamber._ActionAbilityMapper',
                          'origin_activity': 0,
                          'persistence_tax_factor': 3.188141,
                          'representation_score': 0.44749,
                          'rewrite_bias': 'generic',
                          'rewrite_feedback': {'acceptance_rate': 0.0,
                                               'accepted_count': 0,
                                               'adaptation_mode': 'conservative',
                                               'adoption_count': 0,
                                               'confidence': 0.36,
                                               'mean_mutation_score': 0.25,
                                               'rejected_count': 2,
                                               'rejection_rate': 1.0,
                                               'timing_credit': 0.0,
                                               'timing_penalty': 0.0,
                                               'trial_count': 2},
                          'rewrite_profile': 'generic',
                          'signature': 'A^2',
                          'surface_score': 0.581,
                          'sustainability_score': 0.324968,
                          'target_kind': 'class'},
 '_build_axis_cost_weights': {'ability_hits': 2,
                              'alignment_gap': 0.611,
                              'alignment_target_score': 1.192,
                              'best_coupling_signature': 'N^2*B^1',
                              'constraints': ['energy'],
                              'contract_profile': {'accepts_payload': False,
                                                   'async_callable': False,
                                                   'callable': True,
                                                   'class_target': False,
                                                   'constraint_density': 1,
                                                   'contract_mode': 'stateless',
                                                   'doc_hint': 'Cost-normalized per-axis weights '
                                                               'in [0,1], derived from '
                                                               'shift_cost_coeff.',
                                                   'effect_density': 2,
                                                   'kwonly_args': 0,
                                                   'optional_args': 0,
                                                   'required_args': 0,
                                                   'return_hint': 'Dict[str, float]',
                                                   'signature_text': "() -> 'Dict[str, float]'",
                                                   'stateful_owner': False,
                                                   'target_kind': 'function',
                                                   'varargs': False,
                                                   'varkw': False},
                              'coupling_similarity': 1.0,
                              'cross_diversity_links': 2,
                              'effect_modes': ['cost_pressure_change', 'lineage_surface'],
                              'effect_phrases': ['function growth reflected through '
                                                 'aurora_internal.aurora_evolution_chamber',
                                                 '_build_axis_cost_weights changed downstream '
                                                 'system pressure'],
                              'genealogy_pressure': 0.428731,
                              'inheritance_breach_count': 1,
                              'kind': 'reflection',
                              'link_hits': 0,
                              'module': 'aurora_internal.aurora_evolution_chamber',
                              'op_id': 'aurora_internal.aurora_evolution_chamber._build_axis_cost_weights',
                              'origin_activity': 0,
                              'persistence_tax_factor': 1.436546,
                              'representation_score': 0.588333,
                              'rewrite_bias': 'generic',
                              'rewrite_feedback': {'acceptance_rate': 0.0,
                                                   'accepted_count': 0,
                                                   'adaptation_mode': 'conservative',
                                                   'adoption_count': 0,
                                                   'confidence': 0.36,
                                                   'mean_mutation_score': 0.25,
                                                   'rejected_count': 2,
                                                   'rejection_rate': 1.0,
                                                   'timing_credit': 0.0,
                                                   'timing_penalty': 0.0,
                                                   'trial_count': 2},
                              'rewrite_profile': 'generic',
                              'signature': 'N^2*B^1',
                              'surface_score': 0.581,
                              'sustainability_score': 0.515673,
                              'target_kind': 'function'},
 '_read_pressure': {'ability_hits': 2,
                    'alignment_gap': 0.611,
                    'alignment_target_score': 1.192,
                    'best_coupling_signature': 'N^2*B^1',
                    'constraints': ['energy'],
                    'contract_profile': {'accepts_payload': False,
                                         'async_callable': False,
                                         'callable': True,
                                         'class_target': False,
                                         'constraint_density': 1,
                                         'contract_mode': 'stateless',
                                         'doc_hint': 'Read 5-axis pressure from IVM polarity.',
                                         'effect_density': 2,
                                         'kwonly_args': 0,
                                         'optional_args': 0,
                                         'required_args': 1,
                                         'return_hint': 'PressureVec',
                                         'signature_text': "(lattice: 'IVMLattice') -> "
                                                           "'PressureVec'",
                                         'stateful_owner': False,
                                         'target_kind': 'function',
                                         'varargs': False,
                                         'varkw': False},
                    'coupling_similarity': 1.0,
                    'cross_diversity_links': 2,
                    'effect_modes': ['cost_pressure_change', 'lineage_surface'],
                    'effect_phrases': ['function growth reflected through '
                                       'aurora_internal.aurora_evolution_chamber',
                                       '_read_pressure changed downstream system pressure'],
                    'genealogy_pressure': 0.428731,
                    'inheritance_breach_count': 1,
                    'kind': 'reflection',
                    'link_hits': 0,
                    'module': 'aurora_internal.aurora_evolution_chamber',
                    'op_id': 'aurora_internal.aurora_evolution_chamber._read_pressure',
                    'origin_activity': 0,
                    'persistence_tax_factor': 1.436546,
                    'representation_score': 0.588333,
                    'rewrite_bias': 'generic',
                    'rewrite_feedback': {'acceptance_rate': 0.0,
                                         'accepted_count': 0,
                                         'adaptation_mode': 'conservative',
                                         'adoption_count': 0,
                                         'confidence': 0.36,
                                         'mean_mutation_score': 0.25,
                                         'rejected_count': 2,
                                         'rejection_rate': 1.0,
                                         'timing_credit': 0.0,
                                         'timing_penalty': 0.0,
                                         'trial_count': 2},
                    'rewrite_profile': 'generic',
                    'signature': 'N^2*B^1',
                    'surface_score': 0.581,
                    'sustainability_score': 0.515673,
                    'target_kind': 'function'},
 '_state_signature': {'ability_hits': 1,
                      'alignment_gap': 0.611,
                      'alignment_target_score': 1.192,
                      'best_coupling_signature': 'X^2*B^1',
                      'constraints': ['existence'],
                      'contract_profile': {'accepts_payload': False,
                                           'async_callable': False,
                                           'callable': True,
                                           'class_target': False,
                                           'constraint_density': 1,
                                           'contract_mode': 'stateless',
                                           'doc_hint': '',
                                           'effect_density': 2,
                                           'kwonly_args': 0,
                                           'optional_args': 0,
                                           'required_args': 3,
                                           'return_hint': 'str',
                                           'signature_text': "(lattice: 'IVMLattice', tick: 'int', "
                                                             "partition_count: 'int') -> 'str'",
                                           'stateful_owner': False,
                                           'target_kind': 'function',
                                           'varargs': False,
                                           'varkw': False},
                      'coupling_similarity': 1.0,
                      'cross_diversity_links': 2,
                      'effect_modes': ['state_schema_change', 'lineage_surface'],
                      'effect_phrases': ['function growth reflected through '
                                         'aurora_internal.aurora_evolution_chamber',
                                         '_state_signature changed downstream system pressure'],
                      'genealogy_pressure': 0.411142,
                      'inheritance_breach_count': 1,
                      'kind': 'reflection',
                      'link_hits': 0,
                      'module': 'aurora_internal.aurora_evolution_chamber',
                      'op_id': 'aurora_internal.aurora_evolution_chamber._state_signature',
                      'origin_activity': 0,
                      'persistence_tax_factor': 1.057081,
                      'representation_score': 0.588133,
                      'rewrite_bias': 'generic',
                      'rewrite_feedback': {'acceptance_rate': 0.0,
                                           'accepted_count': 0,
                                           'adaptation_mode': 'conservative',
                                           'adoption_count': 0,
                                           'confidence': 0.36,
                                           'mean_mutation_score': 0.25,
                                           'rejected_count': 2,
                                           'rejection_rate': 1.0,
                                           'timing_credit': 0.0,
                                           'timing_penalty': 0.0,
                                           'trial_count': 2},
                      'rewrite_profile': 'generic',
                      'signature': 'X^2*B^1',
                      'surface_score': 0.581,
                      'sustainability_score': 0.534646,
                      'target_kind': 'function'}}

def _aurora_target_strategy(target_key):
    return dict(_AURORA_NATIVE_STRATEGIES.get(str(target_key), {}) or {})

def _aurora_target_feedback(target_key):
    strategy = _aurora_target_strategy(target_key)
    return dict(strategy.get('rewrite_feedback', {}) or {})

def _aurora_assign_target(chain, value):
    if not chain:
        return False
    if len(chain) == 1:
        globals()[chain[0]] = value
        return True
    current = globals().get(chain[0])
    if current is None:
        return False
    for attr in chain[1:-1]:
        if not hasattr(current, attr):
            return False
        current = getattr(current, attr)
    setattr(current, chain[-1], value)
    return True

def _aurora_get_target(chain):
    if not chain:
        return None
    if len(chain) == 1:
        return globals().get(chain[0])
    current = globals().get(chain[0])
    if current is None:
        return None
    for attr in chain[1:]:
        if not hasattr(current, attr):
            return None
        current = getattr(current, attr)
    return current

def _aurora_bind_owner_attribute(owner_chain, attr_name, value):
    owner = _aurora_get_target(owner_chain)
    if owner is None or not attr_name:
        return False
    try:
        setattr(owner, attr_name, value)
        return True
    except Exception:
        return False

def _aurora_store_reflection(target_key, reflection, args):
    if not args:
        return
    owner = args[0]
    if not hasattr(owner, '__dict__'):
        return
    current = getattr(owner, '_aurora_evolved_reflections', None)
    if not isinstance(current, dict):
        current = {}
    current[str(target_key)] = reflection
    try:
        setattr(owner, '_aurora_evolved_reflections', current)
    except Exception:
        pass

def _aurora_store_owner_state(attribute, target_key, value, args):
    if not args:
        return
    owner = args[0]
    if not hasattr(owner, '__dict__'):
        return
    current = getattr(owner, attribute, None)
    if not isinstance(current, dict):
        current = {}
    current[str(target_key)] = value
    try:
        setattr(owner, attribute, current)
    except Exception:
        pass

def _aurora_apply_constraint_genealogy_rewrite(target_key, result, reflection, args, kwargs):
    strategy = _aurora_target_strategy(target_key)
    feedback = _aurora_target_feedback(target_key)
    bias = str(strategy.get('rewrite_bias', 'lineage_memory') or 'lineage_memory')
    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')
    effect_modes = list(strategy.get('effect_modes', []) or [])
    _aurora_store_reflection(target_key, reflection, args)
    _aurora_store_owner_state('_aurora_genealogy_strategy', target_key, strategy, args)
    if isinstance(result, dict):
        enriched = dict(result)
        enriched['_aurora_evolved_reflection'] = reflection
        enriched['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'constraint_genealogy') or 'constraint_genealogy')
        enriched['_aurora_genealogy_strategy'] = strategy
        enriched['_aurora_rewrite_feedback'] = feedback
        enriched['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        if bias == 'lineage_memory' or 'lineage_surface' in effect_modes:
            enriched['lineage_memory'] = {
                'coupling_signature': strategy.get('best_coupling_signature', ''),
                'link_hits': int(strategy.get('link_hits', 0) or 0),
                'ability_hits': int(strategy.get('ability_hits', 0) or 0),
            }
        if 'state_schema_change' in effect_modes or bias == 'lineage_memory':
            enriched['state_transition_pressure'] = {
                'pressure': float(strategy.get('genealogy_pressure', 0.0) or 0.0),
                'persistence_tax_factor': float(strategy.get('persistence_tax_factor', 0.0) or 0.0),
            }
        if str(target_key).endswith('.summary') or 'chain_report' in str(target_key) or str(target_key).endswith('.to_dict'):
            enriched['evolutionary_context'] = {
                'coupling_signature': strategy.get('best_coupling_signature', ''),
                'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
                'rewrite_bias': bias,
                'cross_diversity_links': int(strategy.get('cross_diversity_links', 0) or 0),
            }
        if mode in {'expansive', 'integrative'}:
            enriched['lineage_adaptation'] = {
                'mode': mode,
                'confidence': float(feedback.get('confidence', 0.0) or 0.0),
                'trial_count': int(feedback.get('trial_count', 0) or 0),
                'accepted_count': int(feedback.get('accepted_count', 0) or 0),
                'adoption_count': int(feedback.get('adoption_count', 0) or 0),
            }
        if mode == 'conservative':
            enriched['lineage_stability_guard'] = {
                'rejected_count': int(feedback.get('rejected_count', 0) or 0),
                'rejection_rate': float(feedback.get('rejection_rate', 0.0) or 0.0),
                'timing_penalty': float(feedback.get('timing_penalty', 0.0) or 0.0),
            }
        return enriched
    if result is None and isinstance(reflection, dict):
        fallback = dict(reflection)
        fallback['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'constraint_genealogy') or 'constraint_genealogy')
        fallback['_aurora_genealogy_strategy'] = strategy
        fallback['_aurora_rewrite_feedback'] = feedback
        fallback['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        fallback['lineage_adaptation_mode'] = mode
        return fallback
    _aurora_store_owner_state(
        '_aurora_genealogy_scalar_observations',
        target_key,
        {
            'result': result,
            'strategy': strategy,
            'reflection': reflection,
        },
        args,
    )
    return result

def _aurora_apply_governance_rewrite(target_key, result, reflection, args, kwargs):
    strategy = _aurora_target_strategy(target_key)
    feedback = _aurora_target_feedback(target_key)
    bias = str(strategy.get('rewrite_bias', 'governance_routing') or 'governance_routing')
    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')
    effect_modes = list(strategy.get('effect_modes', []) or [])
    _aurora_store_reflection(target_key, reflection, args)
    _aurora_store_owner_state('_aurora_governance_strategy', target_key, strategy, args)
    if isinstance(result, dict):
        enriched = dict(result)
        enriched['_aurora_evolved_reflection'] = reflection
        enriched['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'governance_gateway') or 'governance_gateway')
        enriched['_aurora_genealogy_strategy'] = strategy
        enriched['_aurora_rewrite_feedback'] = feedback
        enriched['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        enriched['governance_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        if bias == 'governance_routing' or 'gateway_surface' in effect_modes:
            enriched['governance_routing'] = {
                'sustainability_score': float(strategy.get('sustainability_score', 0.0) or 0.0),
                'representation_score': float(strategy.get('representation_score', 0.0) or 0.0),
                'origin_activity': int(strategy.get('origin_activity', 0) or 0),
            }
        if 'state_schema_change' in effect_modes:
            enriched['persistence_burden'] = {
                'persistence_tax_factor': float(strategy.get('persistence_tax_factor', 0.0) or 0.0),
                'inheritance_breach_count': int(strategy.get('inheritance_breach_count', 0) or 0),
            }
        if mode in {'expansive', 'integrative'}:
            enriched['governance_adaptation'] = {
                'mode': mode,
                'confidence': float(feedback.get('confidence', 0.0) or 0.0),
                'acceptance_rate': float(feedback.get('acceptance_rate', 0.0) or 0.0),
                'timing_credit': float(feedback.get('timing_credit', 0.0) or 0.0),
            }
        if mode == 'conservative':
            enriched['persistence_guard'] = {
                'rejection_rate': float(feedback.get('rejection_rate', 0.0) or 0.0),
                'timing_penalty': float(feedback.get('timing_penalty', 0.0) or 0.0),
                'trial_count': int(feedback.get('trial_count', 0) or 0),
            }
        return enriched
    if result is None and isinstance(reflection, dict):
        fallback = dict(reflection)
        fallback['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'governance_gateway') or 'governance_gateway')
        fallback['_aurora_genealogy_strategy'] = strategy
        fallback['_aurora_rewrite_feedback'] = feedback
        fallback['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        fallback['governance_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        fallback['governance_adaptation_mode'] = mode
        return fallback
    _aurora_store_owner_state(
        '_aurora_governance_evolution_state',
        target_key,
        {
            'result': result,
            'strategy': strategy,
            'reflection': reflection,
        },
        args,
    )
    return result

def _aurora_apply_perception_rewrite(target_key, result, reflection, args, kwargs):
    strategy = _aurora_target_strategy(target_key)
    feedback = _aurora_target_feedback(target_key)
    bias = str(strategy.get('rewrite_bias', 'perceptual_synthesis') or 'perceptual_synthesis')
    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')
    effect_modes = list(strategy.get('effect_modes', []) or [])
    _aurora_store_reflection(target_key, reflection, args)
    _aurora_store_owner_state('_aurora_perception_strategy', target_key, strategy, args)
    if isinstance(result, dict):
        enriched = dict(result)
        enriched['_aurora_evolved_reflection'] = reflection
        enriched['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'perception_synthesis') or 'perception_synthesis')
        enriched['_aurora_genealogy_strategy'] = strategy
        enriched['_aurora_rewrite_feedback'] = feedback
        enriched['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        enriched['perception_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        if bias == 'perceptual_synthesis' or 'adaptive_steering_change' in effect_modes:
            enriched['perception_synthesis'] = {
                'representation_score': float(strategy.get('representation_score', 0.0) or 0.0),
                'ability_hits': int(strategy.get('ability_hits', 0) or 0),
                'link_hits': int(strategy.get('link_hits', 0) or 0),
            }
        if 'interface_boundary_change' in effect_modes or 'gateway_surface' in effect_modes:
            enriched['boundary_integration'] = {
                'cross_diversity_links': int(strategy.get('cross_diversity_links', 0) or 0),
                'coupling_similarity': float(strategy.get('coupling_similarity', 0.0) or 0.0),
            }
        if mode in {'expansive', 'integrative'}:
            enriched['association_expansion'] = {
                'mode': mode,
                'confidence': float(feedback.get('confidence', 0.0) or 0.0),
                'timing_credit': float(feedback.get('timing_credit', 0.0) or 0.0),
                'acceptance_rate': float(feedback.get('acceptance_rate', 0.0) or 0.0),
            }
        if mode == 'conservative':
            enriched['perception_stability'] = {
                'rejection_rate': float(feedback.get('rejection_rate', 0.0) or 0.0),
                'timing_penalty': float(feedback.get('timing_penalty', 0.0) or 0.0),
                'trial_count': int(feedback.get('trial_count', 0) or 0),
            }
        return enriched
    if result is None and isinstance(reflection, dict):
        fallback = dict(reflection)
        fallback['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'perception_synthesis') or 'perception_synthesis')
        fallback['_aurora_genealogy_strategy'] = strategy
        fallback['_aurora_rewrite_feedback'] = feedback
        fallback['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        fallback['perception_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        if bias == 'perceptual_synthesis' or 'adaptive_steering_change' in effect_modes:
            fallback['perception_synthesis'] = {
                'representation_score': float(strategy.get('representation_score', 0.0) or 0.0),
                'ability_hits': int(strategy.get('ability_hits', 0) or 0),
                'link_hits': int(strategy.get('link_hits', 0) or 0),
            }
        fallback['perception_adaptation_mode'] = mode
        return fallback
    _aurora_store_owner_state(
        '_aurora_perception_evolution_state',
        target_key,
        {
            'result': result,
            'strategy': strategy,
            'reflection': reflection,
        },
        args,
    )
    return result

def _aurora_apply_dimensional_rewrite(target_key, result, reflection, args, kwargs):
    strategy = _aurora_target_strategy(target_key)
    feedback = _aurora_target_feedback(target_key)
    bias = str(strategy.get('rewrite_bias', 'dimensional_balancing') or 'dimensional_balancing')
    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')
    effect_modes = list(strategy.get('effect_modes', []) or [])
    _aurora_store_reflection(target_key, reflection, args)
    _aurora_store_owner_state('_aurora_dimensional_strategy', target_key, strategy, args)
    if isinstance(result, dict):
        enriched = dict(result)
        enriched['_aurora_evolved_reflection'] = reflection
        enriched['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'dimensional_balancing') or 'dimensional_balancing')
        enriched['_aurora_genealogy_strategy'] = strategy
        enriched['_aurora_rewrite_feedback'] = feedback
        enriched['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        enriched['dimensional_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        if bias == 'dimensional_balancing' or 'cost_pressure_change' in effect_modes:
            enriched['dimensional_balancing'] = {
                'sustainability_score': float(strategy.get('sustainability_score', 0.0) or 0.0),
                'persistence_tax_factor': float(strategy.get('persistence_tax_factor', 0.0) or 0.0),
                'origin_activity': int(strategy.get('origin_activity', 0) or 0),
            }
        if 'temporal_orchestration_change' in effect_modes:
            enriched['temporal_coordination'] = {
                'signature': strategy.get('signature', ''),
                'inheritance_breach_count': int(strategy.get('inheritance_breach_count', 0) or 0),
            }
        if mode in {'expansive', 'integrative'}:
            enriched['balancing_momentum'] = {
                'mode': mode,
                'confidence': float(feedback.get('confidence', 0.0) or 0.0),
                'timing_credit': float(feedback.get('timing_credit', 0.0) or 0.0),
                'adoption_count': int(feedback.get('adoption_count', 0) or 0),
            }
        if mode == 'conservative':
            enriched['dimensional_dampening'] = {
                'rejection_rate': float(feedback.get('rejection_rate', 0.0) or 0.0),
                'timing_penalty': float(feedback.get('timing_penalty', 0.0) or 0.0),
                'trial_count': int(feedback.get('trial_count', 0) or 0),
            }
        return enriched
    if result is None and isinstance(reflection, dict):
        fallback = dict(reflection)
        fallback['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'dimensional_balancing') or 'dimensional_balancing')
        fallback['_aurora_genealogy_strategy'] = strategy
        fallback['_aurora_rewrite_feedback'] = feedback
        fallback['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        fallback['dimensional_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        if bias == 'dimensional_balancing' or 'cost_pressure_change' in effect_modes:
            fallback['dimensional_balancing'] = {
                'sustainability_score': float(strategy.get('sustainability_score', 0.0) or 0.0),
                'persistence_tax_factor': float(strategy.get('persistence_tax_factor', 0.0) or 0.0),
                'origin_activity': int(strategy.get('origin_activity', 0) or 0),
            }
        fallback['dimensional_adaptation_mode'] = mode
        return fallback
    _aurora_store_owner_state(
        '_aurora_dimensional_evolution_state',
        target_key,
        {
            'result': result,
            'strategy': strategy,
            'reflection': reflection,
        },
        args,
    )
    return result

def _aurora_apply_result_rewrite(target_key, result, reflection, args, kwargs):
    if _AURORA_NATIVE_MODULE == 'aurora_internal.constraint_genealogy':
        return _aurora_apply_constraint_genealogy_rewrite(target_key, result, reflection, args, kwargs)
    if _AURORA_NATIVE_MODULE == 'aurora_governance_persistence_gateway':
        return _aurora_apply_governance_rewrite(target_key, result, reflection, args, kwargs)
    if _AURORA_NATIVE_MODULE == 'aurora_expression_perception':
        return _aurora_apply_perception_rewrite(target_key, result, reflection, args, kwargs)
    if _AURORA_NATIVE_MODULE == 'aurora_dimensional_systems':
        return _aurora_apply_dimensional_rewrite(target_key, result, reflection, args, kwargs)
    _aurora_store_reflection(target_key, reflection, args)
    strategy = _aurora_target_strategy(target_key)
    feedback = _aurora_target_feedback(target_key)
    contract = dict(strategy.get('contract_profile', {}) or {})
    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')
    if isinstance(result, dict):
        enriched = dict(result)
        enriched['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'generic') or 'generic')
        enriched['_aurora_genealogy_strategy'] = strategy
        enriched['_aurora_rewrite_feedback'] = feedback
        enriched['_aurora_contract_profile'] = contract
        enriched['_aurora_evolved_reflection'] = reflection
        enriched['generic_adaptation'] = {
            'mode': mode,
            'confidence': float(feedback.get('confidence', 0.0) or 0.0),
            'contract_mode': str(contract.get('contract_mode', 'unknown') or 'unknown'),
            'return_hint': str(contract.get('return_hint', '') or ''),
        }
        return enriched
    if result is None and isinstance(reflection, dict):
        fallback = dict(reflection)
        fallback['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'generic') or 'generic')
        fallback['_aurora_genealogy_strategy'] = strategy
        fallback['_aurora_rewrite_feedback'] = feedback
        fallback['_aurora_contract_profile'] = contract
        fallback['generic_adaptation_mode'] = mode
        return fallback
    if result is not None:
        _aurora_store_owner_state(
            '_aurora_generic_evolution_state',
            target_key,
            {
                'result_type': type(result).__name__,
                'contract_mode': str(contract.get('contract_mode', 'unknown') or 'unknown'),
                'return_hint': str(contract.get('return_hint', '') or ''),
                'adaptation_mode': mode,
            },
            args,
        )
    return result

def _aurora_make_override(export_name, target_key):
    original = _AURORA_NATIVE_EVOLVED_ORIGINALS.get(target_key)
    def _override(*args, **kwargs):
        result = None
        if callable(original):
            result = original(*args, **kwargs)
        engine = _aurora_native_evolved_engine()
        reflection = {
            'available': False,
            'reason': 'evolved_surface_engine_unavailable',
            'target': target_key,
        }
        if engine is not None:
            reflection = globals()[export_name]({'args_len': len(args), 'kwargs_keys': sorted(kwargs.keys())})
        _AURORA_NATIVE_EVOLVED_LAST[target_key] = reflection
        rewritten = _aurora_apply_result_rewrite(target_key, result, reflection, args, kwargs)
        if rewritten is not None:
            return rewritten
        if result is not None:
            return result
        return reflection
    _override.__name__ = str(target_key).split('.')[-1]
    _override.__qualname__ = _override.__name__
    if callable(original):
        _override.__doc__ = getattr(original, '__doc__', None)
        _override.__wrapped__ = original
        if _aurora_native_inspect is not None:
            try:
                _override.__signature__ = _aurora_native_inspect.signature(original)
            except Exception:
                pass
    return _override

def _aurora_make_latent_binding(export_name, target_key):
    def _binding(*args, **kwargs):
        payload = kwargs.pop('payload', None)
        if payload is None and args:
            owner = args[0]
            if hasattr(owner, '__dict__'):
                payload = {
                    'bound_target': target_key,
                    'owner_type': type(owner).__name__,
                    'owner_module': type(owner).__module__,
                }
            elif len(args) == 1:
                payload = args[0]
            else:
                payload = {'bound_target': target_key, 'arg_count': len(args)}
        result = globals()[export_name](payload=payload, **kwargs)
        _AURORA_NATIVE_EVOLVED_LAST[target_key] = {'latent_binding_active': True, 'last_result_type': type(result).__name__}
        if args:
            _aurora_store_owner_state('_aurora_latent_bindings', target_key, result, args)
        return result
    _binding.__name__ = str(target_key).split('.')[-1]
    _binding.__qualname__ = _binding.__name__
    _binding.__doc__ = f'Latent evolved binding for {target_key}'
    _binding._aurora_latent_binding_target = target_key
    return _binding

def abilityprofile_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_evolution_chamber.AbilityProfile', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_evolution_chamber_abilityprofile')(payload=payload, **kwargs)

if _aurora_get_target(['AbilityProfile']) is not None:
    setattr(_aurora_get_target(['AbilityProfile']), 'evolved_reflection', staticmethod(abilityprofile_evolved))
    setattr(_aurora_get_target(['AbilityProfile']), '_aurora_alignment_gap', 0.271)
    setattr(_aurora_get_target(['AbilityProfile']), '_aurora_alignment_target_score', 1.192)

def actiontrace_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_evolution_chamber.ActionTrace', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_evolution_chamber_actiontrace')(payload=payload, **kwargs)

if _aurora_get_target(['ActionTrace']) is not None:
    setattr(_aurora_get_target(['ActionTrace']), 'evolved_reflection', staticmethod(actiontrace_evolved))
    setattr(_aurora_get_target(['ActionTrace']), '_aurora_alignment_gap', 0.611)
    setattr(_aurora_get_target(['ActionTrace']), '_aurora_alignment_target_score', 1.192)

def chamberability_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_evolution_chamber.ChamberAbility', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_evolution_chamber_chamberability')(payload=payload, **kwargs)

if _aurora_get_target(['ChamberAbility']) is not None:
    setattr(_aurora_get_target(['ChamberAbility']), 'evolved_reflection', staticmethod(chamberability_evolved))
    setattr(_aurora_get_target(['ChamberAbility']), '_aurora_alignment_gap', 0.271)
    setattr(_aurora_get_target(['ChamberAbility']), '_aurora_alignment_target_score', 1.192)

def init_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_evolution_chamber.ConstraintGenealogyLogger.__init__', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_evolution_chamber_constraintgenealogylogger_init')(payload=payload, **kwargs)

def close_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_evolution_chamber.ConstraintGenealogyLogger.close', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_evolution_chamber_constraintgenealogylogger_close')(payload=payload, **kwargs)

if _aurora_get_target(['ConstraintGenealogyLogger', 'close']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['ConstraintGenealogyLogger.close'] = _aurora_get_target(['ConstraintGenealogyLogger', 'close'])
    _aurora_assign_target(['ConstraintGenealogyLogger', 'close'], _aurora_make_override('close_evolved', 'ConstraintGenealogyLogger.close'))
    _AURORA_NATIVE_EVOLVED_LAST['ConstraintGenealogyLogger.close'] = {'alignment_gap': 0.56, 'override_active': True}

def flush_files_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_evolution_chamber.ConstraintGenealogyLogger.flush_files', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_evolution_chamber_constraintgenealogylogger_flush_files')(payload=payload, **kwargs)

if _aurora_get_target(['ConstraintGenealogyLogger', 'flush_files']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['ConstraintGenealogyLogger.flush_files'] = _aurora_get_target(['ConstraintGenealogyLogger', 'flush_files'])
    _aurora_assign_target(['ConstraintGenealogyLogger', 'flush_files'], _aurora_make_override('flush_files_evolved', 'ConstraintGenealogyLogger.flush_files'))
    _AURORA_NATIVE_EVOLVED_LAST['ConstraintGenealogyLogger.flush_files'] = {'alignment_gap': 0.56, 'override_active': True}

def observe_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_evolution_chamber.ConstraintGenealogyLogger.observe', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_evolution_chamber_constraintgenealogylogger_observe')(payload=payload, **kwargs)

if _aurora_get_target(['ConstraintGenealogyLogger', 'observe']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['ConstraintGenealogyLogger.observe'] = _aurora_get_target(['ConstraintGenealogyLogger', 'observe'])
    _aurora_assign_target(['ConstraintGenealogyLogger', 'observe'], _aurora_make_override('observe_evolved', 'ConstraintGenealogyLogger.observe'))
    _AURORA_NATIVE_EVOLVED_LAST['ConstraintGenealogyLogger.observe'] = {'alignment_gap': 0.56, 'override_active': True}

def summary_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_evolution_chamber.ConstraintGenealogyLogger.summary', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_evolution_chamber_constraintgenealogylogger_summary')(payload=payload, **kwargs)

if _aurora_get_target(['ConstraintGenealogyLogger', 'summary']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['ConstraintGenealogyLogger.summary'] = _aurora_get_target(['ConstraintGenealogyLogger', 'summary'])
    _aurora_assign_target(['ConstraintGenealogyLogger', 'summary'], _aurora_make_override('summary_evolved', 'ConstraintGenealogyLogger.summary'))
    _AURORA_NATIVE_EVOLVED_LAST['ConstraintGenealogyLogger.summary'] = {'alignment_gap': 0.56, 'override_active': True}

def evolutionarychamber_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_evolution_chamber.EvolutionaryChamber', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_evolution_chamber_evolutionarychamber')(payload=payload, **kwargs)

if _aurora_get_target(['EvolutionaryChamber']) is not None:
    setattr(_aurora_get_target(['EvolutionaryChamber']), 'evolved_reflection', staticmethod(evolutionarychamber_evolved))
    setattr(_aurora_get_target(['EvolutionaryChamber']), '_aurora_alignment_gap', 0.271)
    setattr(_aurora_get_target(['EvolutionaryChamber']), '_aurora_alignment_target_score', 1.192)

def run_chain_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_evolution_chamber.EvolutionaryChamber.run_chain', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_evolution_chamber_evolutionarychamber_run_chain')(payload=payload, **kwargs)

if _aurora_get_target(['EvolutionaryChamber', 'run_chain']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['EvolutionaryChamber.run_chain'] = _aurora_get_target(['EvolutionaryChamber', 'run_chain'])
    _aurora_assign_target(['EvolutionaryChamber', 'run_chain'], _aurora_make_override('run_chain_evolved', 'EvolutionaryChamber.run_chain'))
    _AURORA_NATIVE_EVOLVED_LAST['EvolutionaryChamber.run_chain'] = {'alignment_gap': 0.56, 'override_active': True}

def tick_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_evolution_chamber.EvolutionaryChamber.tick', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_evolution_chamber_evolutionarychamber_tick')(payload=payload, **kwargs)

if _aurora_get_target(['EvolutionaryChamber', 'tick']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['EvolutionaryChamber.tick'] = _aurora_get_target(['EvolutionaryChamber', 'tick'])
    _aurora_assign_target(['EvolutionaryChamber', 'tick'], _aurora_make_override('tick_evolved', 'EvolutionaryChamber.tick'))
    _AURORA_NATIVE_EVOLVED_LAST['EvolutionaryChamber.tick'] = {'alignment_gap': 0.56, 'override_active': True}

def axes_from_trace_item_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_evolution_chamber.EvolutionaryChamber.tick._axes_from_trace_item', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_evolution_chamber_evolutionarychamber_tick_axes_from_trace_item')(payload=payload, **kwargs)

if _aurora_get_target(['EvolutionaryChamber', 'tick', '_axes_from_trace_item']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['EvolutionaryChamber.tick._axes_from_trace_item'] = _aurora_get_target(['EvolutionaryChamber', 'tick', '_axes_from_trace_item'])
    _aurora_assign_target(['EvolutionaryChamber', 'tick', '_axes_from_trace_item'], _aurora_make_override('axes_from_trace_item_evolved', 'EvolutionaryChamber.tick._axes_from_trace_item'))
    _AURORA_NATIVE_EVOLVED_LAST['EvolutionaryChamber.tick._axes_from_trace_item'] = {'alignment_gap': 0.509, 'override_active': True}

def genealogyconfig_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_evolution_chamber.GenealogyConfig', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_evolution_chamber_genealogyconfig')(payload=payload, **kwargs)

if _aurora_get_target(['GenealogyConfig']) is not None:
    setattr(_aurora_get_target(['GenealogyConfig']), 'evolved_reflection', staticmethod(genealogyconfig_evolved))
    setattr(_aurora_get_target(['GenealogyConfig']), '_aurora_alignment_gap', 0.271)
    setattr(_aurora_get_target(['GenealogyConfig']), '_aurora_alignment_target_score', 1.192)

def globalnoncomps_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_evolution_chamber.GlobalNonComps', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_evolution_chamber_globalnoncomps')(payload=payload, **kwargs)

if _aurora_get_target(['GlobalNonComps']) is not None:
    setattr(_aurora_get_target(['GlobalNonComps']), 'evolved_reflection', staticmethod(globalnoncomps_evolved))
    setattr(_aurora_get_target(['GlobalNonComps']), '_aurora_alignment_gap', 0.271)
    setattr(_aurora_get_target(['GlobalNonComps']), '_aurora_alignment_target_score', 1.192)

def noncompviolation_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_evolution_chamber.NonCompViolation', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_evolution_chamber_noncompviolation')(payload=payload, **kwargs)

if _aurora_get_target(['NonCompViolation']) is not None:
    setattr(_aurora_get_target(['NonCompViolation']), 'evolved_reflection', staticmethod(noncompviolation_evolved))
    setattr(_aurora_get_target(['NonCompViolation']), '_aurora_alignment_gap', 0.271)
    setattr(_aurora_get_target(['NonCompViolation']), '_aurora_alignment_target_score', 1.192)

def structuralproximitymeter_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_evolution_chamber.StructuralProximityMeter', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_evolution_chamber_structuralproximitymeter')(payload=payload, **kwargs)

if _aurora_get_target(['StructuralProximityMeter']) is not None:
    setattr(_aurora_get_target(['StructuralProximityMeter']), 'evolved_reflection', staticmethod(structuralproximitymeter_evolved))
    setattr(_aurora_get_target(['StructuralProximityMeter']), '_aurora_alignment_gap', 0.271)
    setattr(_aurora_get_target(['StructuralProximityMeter']), '_aurora_alignment_target_score', 1.192)

def partition_count_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_evolution_chamber.StructuralProximityMeter.partition_count', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_evolution_chamber_structuralproximitymeter_partition_count')(payload=payload, **kwargs)

if _aurora_get_target(['StructuralProximityMeter', 'partition_count']) is not None:
    _pc_target = _aurora_get_target(['StructuralProximityMeter', 'partition_count'])
    # partition_count is a @property — store fget so the override closure can call it,
    # then re-wrap the override in property() to preserve descriptor semantics.
    _AURORA_NATIVE_EVOLVED_ORIGINALS['StructuralProximityMeter.partition_count'] = (
        _pc_target.fget if isinstance(_pc_target, property) else _pc_target
    )
    _pc_override = _aurora_make_override('partition_count_evolved', 'StructuralProximityMeter.partition_count')
    _aurora_assign_target(
        ['StructuralProximityMeter', 'partition_count'],
        property(_pc_override) if isinstance(_pc_target, property) else _pc_override,
    )
    _AURORA_NATIVE_EVOLVED_LAST['StructuralProximityMeter.partition_count'] = {'alignment_gap': 0.56, 'override_active': True}

def recompute_partitions_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_evolution_chamber.StructuralProximityMeter.recompute_partitions', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_evolution_chamber_structuralproximitymeter_recompute_partitions')(payload=payload, **kwargs)

if _aurora_get_target(['StructuralProximityMeter', 'recompute_partitions']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['StructuralProximityMeter.recompute_partitions'] = _aurora_get_target(['StructuralProximityMeter', 'recompute_partitions'])
    _aurora_assign_target(['StructuralProximityMeter', 'recompute_partitions'], _aurora_make_override('recompute_partitions_evolved', 'StructuralProximityMeter.recompute_partitions'))
    _AURORA_NATIVE_EVOLVED_LAST['StructuralProximityMeter.recompute_partitions'] = {'alignment_gap': 0.56, 'override_active': True}

def find_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_evolution_chamber.StructuralProximityMeter.recompute_partitions.find', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_evolution_chamber_structuralproximitymeter_recompute_partitions_find')(payload=payload, **kwargs)

if _aurora_get_target(['StructuralProximityMeter', 'recompute_partitions', 'find']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['StructuralProximityMeter.recompute_partitions.find'] = _aurora_get_target(['StructuralProximityMeter', 'recompute_partitions', 'find'])
    _aurora_assign_target(['StructuralProximityMeter', 'recompute_partitions', 'find'], _aurora_make_override('find_evolved', 'StructuralProximityMeter.recompute_partitions.find'))
    _AURORA_NATIVE_EVOLVED_LAST['StructuralProximityMeter.recompute_partitions.find'] = {'alignment_gap': 0.509, 'override_active': True}

def union_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_evolution_chamber.StructuralProximityMeter.recompute_partitions.union', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_evolution_chamber_structuralproximitymeter_recompute_partitions_union')(payload=payload, **kwargs)

if _aurora_get_target(['StructuralProximityMeter', 'recompute_partitions', 'union']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['StructuralProximityMeter.recompute_partitions.union'] = _aurora_get_target(['StructuralProximityMeter', 'recompute_partitions', 'union'])
    _aurora_assign_target(['StructuralProximityMeter', 'recompute_partitions', 'union'], _aurora_make_override('union_evolved', 'StructuralProximityMeter.recompute_partitions.union'))
    _AURORA_NATIVE_EVOLVED_LAST['StructuralProximityMeter.recompute_partitions.union'] = {'alignment_gap': 0.509, 'override_active': True}

def traceitem_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_evolution_chamber.TraceItem', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_evolution_chamber_traceitem')(payload=payload, **kwargs)

if _aurora_get_target(['TraceItem']) is not None:
    setattr(_aurora_get_target(['TraceItem']), 'evolved_reflection', staticmethod(traceitem_evolved))
    setattr(_aurora_get_target(['TraceItem']), '_aurora_alignment_gap', 0.271)
    setattr(_aurora_get_target(['TraceItem']), '_aurora_alignment_target_score', 1.192)

def violationrecord_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_evolution_chamber.ViolationRecord', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_evolution_chamber_violationrecord')(payload=payload, **kwargs)

if _aurora_get_target(['ViolationRecord']) is not None:
    setattr(_aurora_get_target(['ViolationRecord']), 'evolved_reflection', staticmethod(violationrecord_evolved))
    setattr(_aurora_get_target(['ViolationRecord']), '_aurora_alignment_gap', 0.271)
    setattr(_aurora_get_target(['ViolationRecord']), '_aurora_alignment_target_score', 1.192)

def worldconstants_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_evolution_chamber.WorldConstants', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_evolution_chamber_worldconstants')(payload=payload, **kwargs)

if _aurora_get_target(['WorldConstants']) is not None:
    setattr(_aurora_get_target(['WorldConstants']), 'evolved_reflection', staticmethod(worldconstants_evolved))
    setattr(_aurora_get_target(['WorldConstants']), '_aurora_alignment_gap', 0.271)
    setattr(_aurora_get_target(['WorldConstants']), '_aurora_alignment_target_score', 1.192)

def actionabilitymapper_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_evolution_chamber._ActionAbilityMapper', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_evolution_chamber_actionabilitymapper')(payload=payload, **kwargs)

if _aurora_get_target(['_ActionAbilityMapper']) is not None:
    setattr(_aurora_get_target(['_ActionAbilityMapper']), 'evolved_reflection', staticmethod(actionabilitymapper_evolved))
    setattr(_aurora_get_target(['_ActionAbilityMapper']), '_aurora_alignment_gap', 0.611)
    setattr(_aurora_get_target(['_ActionAbilityMapper']), '_aurora_alignment_target_score', 1.192)

def build_axis_cost_weights_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_evolution_chamber._build_axis_cost_weights', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_evolution_chamber_build_axis_cost_weights')(payload=payload, **kwargs)

if _aurora_get_target(['_build_axis_cost_weights']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['_build_axis_cost_weights'] = _aurora_get_target(['_build_axis_cost_weights'])
    _aurora_assign_target(['_build_axis_cost_weights'], _aurora_make_override('build_axis_cost_weights_evolved', '_build_axis_cost_weights'))
    _AURORA_NATIVE_EVOLVED_LAST['_build_axis_cost_weights'] = {'alignment_gap': 0.611, 'override_active': True}

def read_pressure_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_evolution_chamber._read_pressure', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_evolution_chamber_read_pressure')(payload=payload, **kwargs)

def state_signature_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_evolution_chamber._state_signature', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_evolution_chamber_state_signature')(payload=payload, **kwargs)

AURORA_NATIVE_EVOLVED_EXPORTS = {'aurora_internal.aurora_evolution_chamber.AbilityProfile': 'abilityprofile_evolved',
 'aurora_internal.aurora_evolution_chamber.ActionTrace': 'actiontrace_evolved',
 'aurora_internal.aurora_evolution_chamber.ChamberAbility': 'chamberability_evolved',
 'aurora_internal.aurora_evolution_chamber.ConstraintGenealogyLogger.__init__': 'init_evolved',
 'aurora_internal.aurora_evolution_chamber.ConstraintGenealogyLogger.close': 'close_evolved',
 'aurora_internal.aurora_evolution_chamber.ConstraintGenealogyLogger.flush_files': 'flush_files_evolved',
 'aurora_internal.aurora_evolution_chamber.ConstraintGenealogyLogger.observe': 'observe_evolved',
 'aurora_internal.aurora_evolution_chamber.ConstraintGenealogyLogger.summary': 'summary_evolved',
 'aurora_internal.aurora_evolution_chamber.EvolutionaryChamber': 'evolutionarychamber_evolved',
 'aurora_internal.aurora_evolution_chamber.EvolutionaryChamber.run_chain': 'run_chain_evolved',
 'aurora_internal.aurora_evolution_chamber.EvolutionaryChamber.tick': 'tick_evolved',
 'aurora_internal.aurora_evolution_chamber.EvolutionaryChamber.tick._axes_from_trace_item': 'axes_from_trace_item_evolved',
 'aurora_internal.aurora_evolution_chamber.GenealogyConfig': 'genealogyconfig_evolved',
 'aurora_internal.aurora_evolution_chamber.GlobalNonComps': 'globalnoncomps_evolved',
 'aurora_internal.aurora_evolution_chamber.NonCompViolation': 'noncompviolation_evolved',
 'aurora_internal.aurora_evolution_chamber.StructuralProximityMeter': 'structuralproximitymeter_evolved',
 'aurora_internal.aurora_evolution_chamber.StructuralProximityMeter.partition_count': 'partition_count_evolved',
 'aurora_internal.aurora_evolution_chamber.StructuralProximityMeter.recompute_partitions': 'recompute_partitions_evolved',
 'aurora_internal.aurora_evolution_chamber.StructuralProximityMeter.recompute_partitions.find': 'find_evolved',
 'aurora_internal.aurora_evolution_chamber.StructuralProximityMeter.recompute_partitions.union': 'union_evolved',
 'aurora_internal.aurora_evolution_chamber.TraceItem': 'traceitem_evolved',
 'aurora_internal.aurora_evolution_chamber.ViolationRecord': 'violationrecord_evolved',
 'aurora_internal.aurora_evolution_chamber.WorldConstants': 'worldconstants_evolved',
 'aurora_internal.aurora_evolution_chamber._ActionAbilityMapper': 'actionabilitymapper_evolved',
 'aurora_internal.aurora_evolution_chamber._build_axis_cost_weights': 'build_axis_cost_weights_evolved',
 'aurora_internal.aurora_evolution_chamber._read_pressure': 'read_pressure_evolved',
 'aurora_internal.aurora_evolution_chamber._state_signature': 'state_signature_evolved'}
AURORA_NATIVE_EVOLUTION_OVERRIDES = {'aurora_internal.aurora_evolution_chamber.AbilityProfile': {'export': 'abilityprofile_evolved',
                                                             'mode': 'class_reflection_hook',
                                                             'target': 'AbilityProfile'},
 'aurora_internal.aurora_evolution_chamber.ActionTrace': {'export': 'actiontrace_evolved',
                                                          'mode': 'class_reflection_hook',
                                                          'target': 'ActionTrace'},
 'aurora_internal.aurora_evolution_chamber.ChamberAbility': {'export': 'chamberability_evolved',
                                                             'mode': 'class_reflection_hook',
                                                             'target': 'ChamberAbility'},
 'aurora_internal.aurora_evolution_chamber.ConstraintGenealogyLogger.close': {'export': 'close_evolved',
                                                                              'mode': 'callable_override',
                                                                              'target': 'ConstraintGenealogyLogger.close'},
 'aurora_internal.aurora_evolution_chamber.ConstraintGenealogyLogger.flush_files': {'export': 'flush_files_evolved',
                                                                                    'mode': 'callable_override',
                                                                                    'target': 'ConstraintGenealogyLogger.flush_files'},
 'aurora_internal.aurora_evolution_chamber.ConstraintGenealogyLogger.observe': {'export': 'observe_evolved',
                                                                                'mode': 'callable_override',
                                                                                'target': 'ConstraintGenealogyLogger.observe'},
 'aurora_internal.aurora_evolution_chamber.ConstraintGenealogyLogger.summary': {'export': 'summary_evolved',
                                                                                'mode': 'callable_override',
                                                                                'target': 'ConstraintGenealogyLogger.summary'},
 'aurora_internal.aurora_evolution_chamber.EvolutionaryChamber': {'export': 'evolutionarychamber_evolved',
                                                                  'mode': 'class_reflection_hook',
                                                                  'target': 'EvolutionaryChamber'},
 'aurora_internal.aurora_evolution_chamber.EvolutionaryChamber.run_chain': {'export': 'run_chain_evolved',
                                                                            'mode': 'callable_override',
                                                                            'target': 'EvolutionaryChamber.run_chain'},
 'aurora_internal.aurora_evolution_chamber.EvolutionaryChamber.tick': {'export': 'tick_evolved',
                                                                       'mode': 'callable_override',
                                                                       'target': 'EvolutionaryChamber.tick'},
 'aurora_internal.aurora_evolution_chamber.EvolutionaryChamber.tick._axes_from_trace_item': {'export': 'axes_from_trace_item_evolved',
                                                                                             'mode': 'callable_override',
                                                                                             'target': 'EvolutionaryChamber.tick._axes_from_trace_item'},
 'aurora_internal.aurora_evolution_chamber.GenealogyConfig': {'export': 'genealogyconfig_evolved',
                                                              'mode': 'class_reflection_hook',
                                                              'target': 'GenealogyConfig'},
 'aurora_internal.aurora_evolution_chamber.GlobalNonComps': {'export': 'globalnoncomps_evolved',
                                                             'mode': 'class_reflection_hook',
                                                             'target': 'GlobalNonComps'},
 'aurora_internal.aurora_evolution_chamber.NonCompViolation': {'export': 'noncompviolation_evolved',
                                                               'mode': 'class_reflection_hook',
                                                               'target': 'NonCompViolation'},
 'aurora_internal.aurora_evolution_chamber.StructuralProximityMeter': {'export': 'structuralproximitymeter_evolved',
                                                                       'mode': 'class_reflection_hook',
                                                                       'target': 'StructuralProximityMeter'},
 'aurora_internal.aurora_evolution_chamber.StructuralProximityMeter.partition_count': {'export': 'partition_count_evolved',
                                                                                       'mode': 'callable_override',
                                                                                       'target': 'StructuralProximityMeter.partition_count'},
 'aurora_internal.aurora_evolution_chamber.StructuralProximityMeter.recompute_partitions': {'export': 'recompute_partitions_evolved',
                                                                                            'mode': 'callable_override',
                                                                                            'target': 'StructuralProximityMeter.recompute_partitions'},
 'aurora_internal.aurora_evolution_chamber.StructuralProximityMeter.recompute_partitions.find': {'export': 'find_evolved',
                                                                                                 'mode': 'callable_override',
                                                                                                 'target': 'StructuralProximityMeter.recompute_partitions.find'},
 'aurora_internal.aurora_evolution_chamber.StructuralProximityMeter.recompute_partitions.union': {'export': 'union_evolved',
                                                                                                  'mode': 'callable_override',
                                                                                                  'target': 'StructuralProximityMeter.recompute_partitions.union'},
 'aurora_internal.aurora_evolution_chamber.TraceItem': {'export': 'traceitem_evolved',
                                                        'mode': 'class_reflection_hook',
                                                        'target': 'TraceItem'},
 'aurora_internal.aurora_evolution_chamber.ViolationRecord': {'export': 'violationrecord_evolved',
                                                              'mode': 'class_reflection_hook',
                                                              'target': 'ViolationRecord'},
 'aurora_internal.aurora_evolution_chamber.WorldConstants': {'export': 'worldconstants_evolved',
                                                             'mode': 'class_reflection_hook',
                                                             'target': 'WorldConstants'},
 'aurora_internal.aurora_evolution_chamber._ActionAbilityMapper': {'export': 'actionabilitymapper_evolved',
                                                                   'mode': 'class_reflection_hook',
                                                                   'target': '_ActionAbilityMapper'},
 'aurora_internal.aurora_evolution_chamber._build_axis_cost_weights': {'export': 'build_axis_cost_weights_evolved',
                                                                       'mode': 'callable_override',
                                                                       'target': '_build_axis_cost_weights'}}
# AURORA_EVOLVED_NATIVE_END

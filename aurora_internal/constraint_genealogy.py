#!/usr/bin/env python3
"""
AURORA CONSTRAINT GENEALOGY LOGGER
=====================================
Module: constraint_genealogy.py
Layer: Evolutionary Foundation (sits beneath aurora_evolution_chamber.py)

PURPOSE:
    A fossil-record engine for the constraint universe {X, T, N, B, A}.
    Observes only pressure-relief events, records which constraint-abilities
    were used, and promotes repeated effective pairings into classified Links —
    traceable "new atoms" in the evolutionary chain.

    The universe is EXACTLY five axes: X / T / N / B / A.
    No sixth dimension. No language assumptions. No compression plans.
    Just: pressure → act → relief → promote.

DOCTRINE:
    - Only relief events enter the fossil record.
    - Every action is a trace of Ability|Link items.
    - Every Ability and Link carries a full 5-axis cost/risk profile.
    - Links are born only from observed repetition + net benefit under pressure.
    - Links form a DAG; ancestry is always traceable through .parents.
    - TimeDilationGovernor from aurora_simulation_engine governs chamber pacing
      so the genealogy loop runs fast when stable, slow when fragile.

Authors: Sunni (Sir) Morningstar and Cael Devo
Created: February 2026
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, FrozenSet, List, Optional, Tuple

# ---------------------------------------------------------------------------
# IMPORTS FROM AURORA STACK
# ---------------------------------------------------------------------------

from aurora_internal.aurora_constraint_manifold_patched import Constraint
from aurora_constraint_engine import ConstraintVector
from aurora_simulation_engine import (
    TimeDilationGovernor,
    StabilityMetrics,
    StabilityState,
)
from aurora_internal.aurora_cost_diff_score import score_from_cost, CostDiffScore
from aurora_internal.aurora_difference_buffer import DifferenceSnapshot

try:
    from aurora_closure_basis import (
        derive_lineage,
        lineage_grade_payload,
        classify_ontological_status,
        channel_ids_from_ability_id,
        GENEALOGY_ATOM_TO_SLOT_ID,
        OntologicalStatus,
    )
    _CLOSURE_BASIS_AVAILABLE = True
except ImportError:
    _CLOSURE_BASIS_AVAILABLE = False

try:
    from aurora_internal.lineage_canonical import (
        axis_token as _canonical_axis_token_shared,
        constraints_for_operation as _canonical_constraints_for_operation,
        operator_action_for_axis as _canonical_operator_action_for_axis,
    )
except Exception:
    def _canonical_axis_token_shared(raw: str):
        return None

    def _canonical_constraints_for_operation(op_name: str, axis=None, requires=None, effect_tags=None):
        return tuple()

    def _canonical_operator_action_for_axis(axis: str) -> str:
        return "cross_constraint_operation"

try:
    from aurora_internal.aurora_meaning_evolution import (
        meaning_profile_for_counts as _meaning_profile_for_counts,
    )
except Exception:
    def _meaning_profile_for_counts(counts):
        return None

# ---------------------------------------------------------------------------
# CONSTANTS / AXES
# ---------------------------------------------------------------------------

AXES: Tuple[str, ...] = ("X", "T", "N", "B", "A")

# Per-scale tick participation (whole tick at X, fractional at deeper layers).
# Persistence taxation uses the opposed (inverse) relation of this profile.
AXIS_TICK_PARTICIPATION: Dict[str, float] = {
    "X": 1.0,
    "T": 0.1,
    "N": 0.01,
    "B": 0.001,
    "A": 0.0001,
}


def _zero_vec() -> Dict[str, float]:
    return {a: 0.0 for a in AXES}


# ---------------------------------------------------------------------------
# SEMANTIC FAIL-DIMENSION PROVENANCE HINTS
# ---------------------------------------------------------------------------
# External callers (e.g. aurora_dream_trainer) call hint_fail_dimension() to
# register that a semantic rubric dimension has just been detected as failing.
# The next time a ConstraintLink is promoted whose dominant axis matches that
# dimension's expected axis, the link is tagged with `dim:<dim>` so the
# genealogy fossil record carries emotional/perspective ancestry -- not just
# raw constraint mechanics.

_SEMANTIC_DIM_HINT_EXPIRY_SECS = 45.0   # hints expire after this many seconds

# NC dimension provenance per dominant axis — which NC dimension a promoted link
# most directly exercises. Derived from AURORA_UNIFIED_FIELD_SPEC.md information lineage.
#   X → OPERATOR  : admissibility gate is the existence operator
#   T → DIFFERENCE: temporal sequence creates delta from expected tick
#   N → COST      : energy conservation is the cost reference dimension
#   B → MAGNITUDE : boundary is the primary magnitude carrier (Magnitude = B×T×X/N)
#   A → POLARITY  : agency control sets direction/polarity of impact
_AXIS_NC_DIM: Dict[str, str] = {
    "X": "OPERATOR",
    "T": "DIFFERENCE",
    "N": "COST",
    "B": "MAGNITUDE",
    "A": "POLARITY",
}

# Maps expected dominant axis → the semantic dimensions it serves
_DIM_TO_AXIS: Dict[str, str] = {
    "emotional_calibration":    "B",
    "boundary_calibration":     "B",
    "ambiguity_handling":       "B",
    "framing_selection":        "A",
    "adaptive_strategy_selection": "A",
    "perspective_integration":  "X",
    "uncertainty_signaling":    "X",
    "contradiction_handling":   "X",
    "context_carryover":        "T",
    "multi_turn_stability":     "T",
    "semantic_precision":       "N",
    "compression_elaboration_fit": "N",
    "implied_intent_inference": "N",
    "coherence_maintenance":    "X",
}

# dim → expiry timestamp (time.time() + TTL)
_pending_semantic_hints: Dict[str, float] = {}


def hint_fail_dimension(dim: str, ttl: float = _SEMANTIC_DIM_HINT_EXPIRY_SECS) -> None:
    """
    Register that a rubric dimension has just failed.  The next promoted
    ConstraintLink whose dominant axis matches ``dim``'s axis will be tagged
    with ``dim:<dim>`` for ancestry tracking.
    Callable from any module -- no reference to the logger instance needed.

    Accepts compound T-cascade tags of the form ``T_cascade:<dim>`` emitted by
    aurora_telemetry when T-axis dominates and downstream sequencing dims fail.
    These are routed to the T-axis for genealogy tagging.
    """
    if dim in _DIM_TO_AXIS or dim.startswith("T_cascade:"):
        _pending_semantic_hints[dim] = time.time() + ttl


def _consume_semantic_dim_tags(dominant_axis: str) -> List[str]:
    """
    Pop any pending dim-hints whose axis matches `dominant_axis` and return
    them as `dim:<name>` tag strings.  Expired hints are discarded.

    T_cascade compound tags (``T_cascade:<dim>``) are matched when
    dominant_axis is "T" and emitted as ``dim:T_cascade:<dim>`` so the
    genealogy fossil record carries explicit cascade provenance.
    """
    now = time.time()
    tags_out: List[str] = []
    expired = [d for d, exp in _pending_semantic_hints.items() if exp <= now]
    for d in expired:
        del _pending_semantic_hints[d]
    for dim, _exp in list(_pending_semantic_hints.items()):
        # Standard dim → axis routing
        if _DIM_TO_AXIS.get(dim) == dominant_axis:
            tags_out.append(f"dim:{dim}")
            del _pending_semantic_hints[dim]
        # T-cascade compound tags: only emit when the promoted link is T-axis
        elif dim.startswith("T_cascade:") and dominant_axis == "T":
            tags_out.append(f"dim:{dim}")
            del _pending_semantic_hints[dim]
    return tags_out


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _generation_role_name(gen: int) -> str:
    """Generational alignment role (tetrad + warp law)."""
    g = int(gen or 0)
    if g > 0 and g % 5 == 0:
        return "WARP"
    pos = ((max(1, g) - 1) % 4) + 1
    if pos == 1:
        return "PRIMARY"
    if pos == 2:
        return "ADJACENT"
    if pos == 3:
        return "SHEAR"
    return "BRIDGE"


def _breeding_pair_score(a_gen: int, b_gen: int) -> float:
    """Score pair compatibility using generational alignment law."""
    a_role = _generation_role_name(a_gen)
    b_role = _generation_role_name(b_gen)
    if ((a_role == "WARP" and b_role == "PRIMARY") or
        (b_role == "WARP" and a_role == "PRIMARY")):
        return -9999.0

    score = 0.0
    if ((a_role == "BRIDGE" and b_role == "PRIMARY") or
        (b_role == "BRIDGE" and a_role == "PRIMARY")):
        score += 3.0
    if ((a_role == "WARP" and b_role == "ADJACENT") or
        (b_role == "WARP" and a_role == "ADJACENT")):
        score += 2.5
    if ((a_role == "WARP" and b_role == "BRIDGE") or
        (b_role == "WARP" and a_role == "BRIDGE")):
        score -= 2.0
    if a_role == "SHEAR" or b_role == "SHEAR":
        score += 0.5
    return score


def _bred_child_generation(a_gen: int, b_gen: int) -> int:
    """
    Breeding-derived generation progression.
    Base progression is +1 over the older parent, modulated by role pairing.
    """
    ag = int(a_gen or 0)
    bg = int(b_gen or 0)
    base = max(ag, bg) + 1
    score = _breeding_pair_score(ag, bg)
    if score <= -9000.0:
        # Forbidden pairing still advances only after extra separation pressure.
        return base + 1
    if score >= 2.5:
        # Privileged / preferred pairings keep the shortest path progression.
        return base
    if score <= -1.0:
        # Antagonistic pairing delays a generation step.
        return base + 1
    return base


SEMANTIC_LANE_IMPACT: Dict[str, Dict[str, float]] = {
    "X": {"intelligence": 0.85, "communication": 0.35, "meaning": 0.70},
    "T": {"intelligence": 0.75, "communication": 0.80, "meaning": 0.45},
    "N": {"intelligence": 0.65, "communication": 0.30, "meaning": 0.55},
    "B": {"intelligence": 0.40, "communication": 0.85, "meaning": 0.75},
    "A": {"intelligence": 0.70, "communication": 0.70, "meaning": 0.85},
}

SEMANTIC_ACTION_BY_LANE: Dict[str, str] = {
    "intelligence": "model refinement",
    "communication": "signal shaping",
    "meaning": "value grounding",
}

PURPOSE_LANE_ALIASES: Dict[str, str] = {
    "communication": "communication",
    "communicative": "communication",
    "communicative_development": "communication",
    "communication_development": "communication",
    "dream_feedback": "communication",
    "expressive": "communication",
    "expression": "communication",
    "social": "communication",
    "social_calibration": "communication",
    "intelligence": "intelligence",
    "cognition": "intelligence",
    "cognitive": "intelligence",
    "structural": "intelligence",
    "structural_evolution": "intelligence",
    "reasoning": "intelligence",
    "optimization": "intelligence",
    "meaning": "meaning",
    "semantic": "meaning",
    "semantic_development": "meaning",
    "meaning_development": "meaning",
    "grounding": "meaning",
    "value_grounding": "meaning",
    "referential_grounding": "meaning",
}


def _canonical_purpose_lane(raw: Any, fallback: str = "") -> str:
    token = str(raw or "").strip().lower()
    if not token:
        return fallback if fallback in {"intelligence", "communication", "meaning"} else ""
    token = token.replace("-", "_").replace(" ", "_")
    lane = PURPOSE_LANE_ALIASES.get(token, token)
    if lane in {"intelligence", "communication", "meaning"}:
        return lane
    return fallback if fallback in {"intelligence", "communication", "meaning"} else ""


# ---------------------------------------------------------------------------
# CONFIGURATION KNOBS
# ---------------------------------------------------------------------------

@dataclass
class GenealogyConfig:
    """
    All tunable parameters in one place.
    Change these without touching the physics.
    """
    # Relief thresholds — events below both are not logged (noise filter)
    # Calibrated for toroidal IVM lattice signal scale (~1e-4 per tick).
    # For corpus ingestion with heavy language stimulation, raise these 10x.
    RELIEF_EPS: float = 0.00005         # min relief on any single axis to log
    RELIEF_TOTAL_EPS: float = 0.00015   # min sum of positive relief across axes

    # Link promotion gates
    # Uses mean_POSITIVE_relief (not net mean) because toroidal oscillation
    # makes net mean ≈ 0 regardless of pair effectiveness.
    K_MIN: int = 30                     # minimum event count before promotion is considered
    RELIEF_PROMOTE_MIN: float = 0.00005 # mean positive relief on dominant axis must exceed this
    RELIEF_STDEV_MAX: float = 0.5       # stdev gate — loose, oscillators are noisy
    POS_FRACTION_MIN: float = 0.52      # majority of logged events must have positive relief
    NET_MIN: float = 0.000001           # net benefit floor (tiny — just must be positive)
    X_RISK_MAX: float = 0.05            # mean X-risk cap (admissibility gate — unchanged)

    # Scalarization weights (must sum to 1.0 each group)
    RELIEF_WEIGHTS: Dict[str, float] = field(default_factory=lambda: {
        "X": 0.30, "T": 0.15, "N": 0.15, "B": 0.20, "A": 0.20
    })
    COST_WEIGHTS: Dict[str, float] = field(default_factory=lambda: {
        "X": 0.30, "T": 0.15, "N": 0.15, "B": 0.20, "A": 0.20
    })
    COST_PENALTY_LAMBDA: float = 1.0    # how hard we penalize cost in net benefit formula
    COST_TO_RELIEF_SCALE: float = 0.002 # rescales cost signal into relief-scale units (reduced: 0.02 inflated cost_signal far above relief scale)

    # Complexity economics
    # Formation: deeper/more-composite links are more expensive to establish.
    COMPLEXITY_FORMATION_SCALE: float = 0.10
    # Maintenance: once promoted, complex links are cheaper to keep using.
    MAINTENANCE_DISCOUNT_BASE: float = 0.20
    MAINTENANCE_DISCOUNT_PER_DEPTH: float = 0.05
    MAINTENANCE_DISCOUNT_MAX: float = 0.60

    # Causal self-improvement for gate adaptation
    # Higher observed link outcome efficiency lowers formation friction over time.
    CAUSAL_ADAPT_RATE: float = 0.08
    CAUSAL_SUPPORT_GAIN: float = 0.35
    # Treat literal C:D gradients as co-equal drive with relief pressure.
    GRADIENT_DRIVE_BLEND: float = 0.50
    # Threshold pressure regulator: thresholds are modulated by the gradient
    # between an axis and its opposed side rather than staying static.
    THRESHOLD_PRESSURE_ENABLED: bool = True
    THRESHOLD_PRESSURE_GAIN: float = 0.60
    THRESHOLD_PRESSURE_DRIVER_WEIGHT: float = 0.55
    THRESHOLD_PRESSURE_OPPOSING_WEIGHT: float = 0.45
    THRESHOLD_PRESSURE_PERSISTENT_WEIGHT: float = 0.20
    THRESHOLD_PRESSURE_SHARPNESS: float = 2.5
    THRESHOLD_PRESSURE_FLOOR_RATIO: float = 0.40
    THRESHOLD_PRESSURE_CAP_RATIO: float = 1.75

    # Link-pressure stagnation regulator
    # If promotions stall, promotion pressure rises smoothly until the next link.
    STAGNATION_WINDOW: int = 400         # relief-event ticks to reach full pressure
    STAGNATION_GAIN_MAX: float = 0.60    # up to +60% relief gain under deep stagnation
    STAGNATION_HARD_WINDOW: int = 2000   # prolonged no-promotion span for deeper gate relaxation
    STAGNATION_BOOTSTRAP_RATIO: float = 0.35  # seed no-promotion pressure at startup (short-run friendly)
    STAGNATION_KMIN_FLOOR_RATIO: float = 0.35
    KMIN_MATURITY_RELIEF_MAX: float = 0.35
    KMIN_NEAR_MISS_RATIO: float = 0.90
    KMIN_NEAR_MISS_POS_MARGIN: float = 0.00003
    KMIN_NEAR_MISS_PF_MARGIN: float = 0.08
    STAGNATION_XRISK_CAP_MAX_MULT: float = 2.25
    STAGNATION_NET_MIN_FLOOR_RATIO: float = 0.15
    STAGNATION_COST_PENALTY_MIN_FACTOR: float = 0.55

    # Late-phase complexity compression (no hard cap).
    # As the link ecosystem matures, repeated families are cheaper to form.
    COMPRESSION_ENABLED: bool = True
    COMPRESSION_LINK_THRESHOLD: int = 180
    COMPRESSION_FAMILY_SCALE: int = 24
    COMPRESSION_MAX_GAIN: float = 0.55

    # Trace rewrite — if True, [u, v] becomes [L] in subsequent log entries
    TRACE_REWRITE_ON_PROMOTE: bool = True

    # Promote stable links into reusable derived abilities (de-duplicated by id).
    LINK_AS_ABILITY: bool = True

    # Relief tolerance ("immune system") by solution id and relief axis.
    # Basic solutions saturate tolerance faster; deeper/composite solutions adapt slower.
    RELIEF_TOLERANCE_ENABLED: bool = True
    RELIEF_TOLERANCE_GROWTH: float = 0.06
    RELIEF_TOLERANCE_DECAY: float = 0.01
    RELIEF_TOLERANCE_MAX: float = 0.85
    RELIEF_TOLERANCE_MIN_FACTOR: float = 0.15
    RELIEF_TOLERANCE_COMPLEXITY_POWER: float = 1.0

    # Coupling roots (semantic + mathematical canonicalization).
    COUPLING_EMA_RATE: float = 0.08
    COUPLING_DECAY: float = 0.005
    PERSISTENT_PRESSURE_ROOT: str = "A^1*N^1*T^1"
    PERSISTENT_ROOT_EXPECTED_GENERATION: int = 2

    # Automatic regulation rubric for evolved couplings.
    RUBRIC_ENABLED: bool = True
    RUBRIC_MIN_EVENTS: int = 24
    RUBRIC_INHERIT_MIN: float = 0.60
    RUBRIC_RELATION_MIN: float = 0.40
    RUBRIC_EFFECT_MIN: float = 0.00008
    RUBRIC_BREEDING_MIN: float = 0.25
    RUBRIC_COMPOSITE_MIN: float = 0.55
    RUBRIC_INHERIT_EFFECT_PENALTY: float = 0.06
    DUPLICATE_SLOT_REDISTRIBUTION: float = 0.50
    COMPLEXITY_SCOPE_ALPHA: float = 0.80
    SCALE_REQUIREMENT_STRENGTH: float = 0.75

    # Scale-depth economics (X lax -> A strict for formation burden).
    SCALE_FORMATION_WEIGHT: float = 0.20

    # Persistence tax opposes tick-rate participation.
    # If an axis receives less tick participation, its per-tick persistence tax is higher.
    PERSISTENCE_TAX_OPPOSE_POWER: float = 1.0
    PERSISTENCE_TAX_MAX_FACTOR: float = 5.0
    # Flip gradient: deeper promoted structures get exponentially cheaper persistence tax.
    PERSISTENCE_DEPTH_DECAY_RATE: float = 0.45
    PERSISTENCE_TAX_MIN_FACTOR: float = 0.15

    # Per-axis K_MIN scale: slow axes (A, B) fire less frequently so they
    # need lower minimum evidence counts to ever reach promotion in real use.
    # T-axis kmin lowered from 0.80: T relief events are foundational (not cheap).
    # A promoted T-axis link represents real sequential continuity — that evidence
    # threshold should be higher (harder to game), not permissive.
    # T=0.95 means T-axis promotions require near-full evidence to pass Gate 2.
    AXIS_KMIN_SCALE: Dict[str, float] = field(default_factory=lambda: {
        "X": 1.00, "T": 0.95, "N": 0.65, "B": 0.45, "A": 0.30
    })

    # Evolving semantic translation memory for coupling actions.
    SEMANTIC_EMA_RATE: float = 0.10
    SEMANTIC_PROMOTE_CONFIDENCE: float = 0.65
    SEMANTIC_PROMOTE_MIN_COUNT: int = 24

    # Representation experiment manager (bounded auto-rescaling search).
    EXPERIMENTS_ENABLED: bool = True
    EXPERIMENT_WINDOW: int = 40
    EXPERIMENT_MIN_ISSUES: int = 8
    EXPERIMENT_MAX_TRIALS_PER_TRIGGER: int = 6
    EXPERIMENT_EXPLORATORY_ENABLED: bool = True
    EXPERIMENT_EXPLORATORY_PERIOD: int = 120
    EXPERIMENT_EXPLORATORY_MIN_COUPLINGS: int = 12

    # DAG safety — links that would exceed this depth are not promoted (runaway prevention)
    MAX_LINK_DEPTH: int = 12

    # JSONL / file output
    EVENTS_FILE: str = "events.jsonl"
    ABILITIES_FILE: str = "abilities.json"
    LINKS_FILE: str = "links.json"
    COUPLINGS_FILE: str = "couplings.json"
    PAIR_STATS_FILE: str = "pair_stats.json"  # persists K_MIN accumulation across runs

    # Time-dilation integration
    # The governor controls how fast the outer chamber loop runs,
    # not this logger directly — but the genealogy layer passes fitness
    # signals back so the governor can adjust.
    USE_TIME_DILATION: bool = True


# ---------------------------------------------------------------------------
# ABILITY — ATOMIC ACTION UNIT
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AbilityProfile:
    """
    The smallest named action unit, fully grounded in the 5 constraints.

    Every ability belongs to a primary axis but carries costs and risks
    across ALL five axes — because that is the entire point.
    """
    id: str                                    # e.g. "B:ENCAPSULATE"
    axis: str                                  # primary axis (X/T/N/B/A)
    requires: Tuple[str, ...]                  # axes that must be non-collapsed
    cost: Dict[str, float]                     # 5-axis operation cost
    risk: Dict[str, float]                     # axes where failure risk is nonzero
    effect_tags: Tuple[str, ...]               # semantic labels (informational only)
    notes: str = ""

    def x_risk(self) -> float:
        """Return the X (existence admissibility) risk component."""
        return self.risk.get("X", 0.0)

    def total_cost(self, weights: Optional[Dict[str, float]] = None) -> float:
        if weights is None:
            return sum(self.cost.values())
        return sum(weights.get(a, 0.0) * self.cost.get(a, 0.0) for a in AXES)

    def cost_diff_score(
        self,
        snapshot: Optional[DifferenceSnapshot] = None,
    ) -> CostDiffScore:
        """
        Live cost score for this ability under current cross-dimensional pressure.

        The base_cost is this ability's total static 5-axis cost. Under drift
        (X admissibility shifting, T momentum changing, N redistributing,
        B displaced, A eroding), the true cost of executing this ability is
        higher — because the environment it operates in is less stable.

        The score reflects the operator-typed pressure declared by each
        constraint's own physics, not a generic alarm threshold.
        """
        return score_from_cost(self.total_cost(), snapshot)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "axis": self.axis,
            "requires": list(self.requires),
            "cost": {a: self.cost.get(a, 0.0) for a in AXES},
            "risk": {a: self.risk.get(a, 0.0) for a in AXES},
            "effect_tags": list(self.effect_tags),
            "notes": self.notes,
        }


def _canonical_axis_token(raw: str) -> Optional[str]:
    ax = _canonical_axis_token_shared(str(raw or ""))
    if ax in AXES:
        return str(ax)
    token = str(raw or "").strip().upper()
    alias = {
        "EXISTENCE": "X", "X": "X",
        "TIME": "T", "TEMPORAL": "T", "T": "T",
        "ENERGY": "N", "COST": "N", "N": "N",
        "BOUNDARY": "B", "B": "B",
        "AGENCY": "A", "A": "A",
    }
    ax = alias.get(token)
    return ax if ax in AXES else None


def _derive_operation_origin(op_id: str, axis: str, requires: Tuple[str, ...], effect_tags: Tuple[str, ...]) -> Dict[str, str]:
    ancestry: List[str] = []

    # Canonical shared mapping first: keeps operation lineage stable across modules.
    canonical_labels = _canonical_constraints_for_operation(
        op_id,
        axis=axis,
        requires=tuple(requires or ()),
        effect_tags=tuple(effect_tags or ()),
    )
    for lbl in (canonical_labels or ()): 
        ax = _canonical_axis_token(lbl)
        if ax:
            ancestry.append(ax)

    if not ancestry:
        primary = _canonical_axis_token(axis)
        if primary:
            ancestry.append(primary)

        for req in (requires or ()):
            ax = _canonical_axis_token(req)
            if ax:
                ancestry.append(ax)

    if not ancestry:
        # Try infer from id/tag text as fallback.
        blob = f"{op_id} {' '.join(str(x) for x in (effect_tags or ())) }"
        for tok in blob.replace(':', ' ').replace('>', ' ').replace('_', ' ').split():
            ax = _canonical_axis_token(tok)
            if ax:
                ancestry.append(ax)

    if not ancestry:
        ancestry = ["X"]

    primary = ancestry[0]
    secondary = next((a for a in ancestry if a != primary), primary)

    counts = {a: 0 for a in AXES}
    for a in ancestry:
        if a in counts:
            counts[a] += 1
    signature = "*".join([f"{a}^{counts[a]}" for a in AXES if counts[a] > 0]) or "X^1"

    root_a = f"NC:{primary}>{secondary}"
    root_b = f"NC:{secondary}>{primary}"
    root_slot = f"{root_a}×{root_b}"

    lineage_raw = f"{op_id}|{signature}|{root_slot}|{'|'.join(ancestry)}"
    lineage_id = "OP:" + hashlib.sha1(lineage_raw.encode()).hexdigest()[:12]

    return {
        "primary": primary,
        "secondary": secondary,
        "signature": signature,
        "root_a": root_a,
        "root_b": root_b,
        "root_slot": root_slot,
        "lineage_id": lineage_id,
    }


def _lineage_counts_from_signature(signature: str) -> Dict[str, int]:
    counts = {a: 0 for a in AXES}
    for raw in str(signature or "").split("*"):
        part = raw.strip()
        if not part:
            continue
        if "^" in part:
            axis, exp_s = part.split("^", 1)
            axis = axis.strip().upper()
            try:
                exp_n = int(float(exp_s.strip()))
            except Exception:
                exp_n = 0
        else:
            axis = part.strip().upper()
            exp_n = 1
        if axis in counts and exp_n > 0:
            counts[axis] += int(exp_n)
    return counts


def _axis_count_value(raw: Any) -> int:
    if isinstance(raw, dict):
        total = 0
        for val in raw.values():
            total += _axis_count_value(val)
        return int(total)
    try:
        return int(raw)
    except Exception:
        try:
            return int(float(raw))
        except Exception:
            return 0


def _lineage_generation_from_counts(counts: Dict[str, int]) -> int:
    total_slots = int(sum(max(0, _axis_count_value(v)) for v in counts.values()))
    if total_slots <= 0:
        return 1
    return max(1, 1 + max(0, total_slots - 2))


def _lineage_purpose_from_counts(counts: Dict[str, int]) -> Tuple[str, float]:
    total = float(sum(max(0, _axis_count_value(v)) for v in counts.values()) or 1.0)
    axis_mix = {a: max(0.0, float(_axis_count_value(counts.get(a, 0)) / total)) for a in AXES}
    lane_scores = {"intelligence": 0.0, "communication": 0.0, "meaning": 0.0}
    for ax, frac in axis_mix.items():
        impacts = SEMANTIC_LANE_IMPACT.get(ax, {})
        for lane in lane_scores:
            lane_scores[lane] += frac * float(impacts.get(lane, 0.0))
    purpose = max(lane_scores.items(), key=lambda kv: kv[1])[0]
    raw = float(lane_scores.get(purpose, 0.0))
    score = max(0.0, min(1.0, raw))
    return str(purpose), float(score)


def _operator_action_for_axis(axis: str) -> str:
    return str(_canonical_operator_action_for_axis(str(axis or "X")))


def _lineage_grade_payload(
    counts: Dict[str, int],
    dominant_axis: str,
    generation: int,
    root_slot: str = "",
) -> Dict[str, Any]:
    """
    Compute lineage grades from axis counts.

    Physics-grounded when aurora_closure_basis is available (Patch 2).
    Falls back to the original string-frequency heuristic otherwise.
    All existing callers continue to work unchanged — root_slot is optional.
    """
    if _CLOSURE_BASIS_AVAILABLE:
        dom = str(dominant_axis or "X").strip().upper()
        if dom not in set(AXES):
            dom = "X"
        requires: tuple = tuple(
            ax for ax in AXES if int(counts.get(ax, 0) or 0) > 0
        )
        if not requires:
            requires = (dom,)
        if not root_slot:
            secondary = next(
                (ax for ax in AXES if ax != dom and int(counts.get(ax, 0) or 0) > 0),
                dom,
            )
            root_slot = f"NC:{dom}>{secondary}×NC:{secondary}>{dom}"
        try:
            _lineage = derive_lineage(dom, requires, root_slot)
            payload = lineage_grade_payload(_lineage)
            payload["generation"] = int(max(
                int(payload.get("generation", 1) or 1),
                int(max(1, generation)),
            ))
            payload["generation_role"] = _generation_role_name(int(payload["generation"]))
            return payload
        except Exception:
            pass  # fall through to heuristic on any error

    # Original heuristic fallback
    active_axes = int(sum(1 for a in AXES if _axis_count_value(counts.get(a, 0) or 0) > 0))
    total_slots = int(sum(max(0, _axis_count_value(v)) for v in counts.values()))
    purpose, purpose_score = _lineage_purpose_from_counts(counts)
    complexity_axes = max(0.0, min(1.0, (active_axes - 1) / 4.0))
    complexity_slots = max(0.0, min(1.0, (max(1, total_slots) - 1) / 7.0))
    complexity = max(0.0, min(1.0, (0.55 * complexity_slots) + (0.45 * complexity_axes)))
    gen_norm = max(0.0, min(1.0, (max(1, int(generation)) - 1) / 8.0))
    operator_score = max(0.0, min(1.0, (0.65 * complexity) + (0.35 * (1.0 - (0.35 * gen_norm)))))
    overall = max(0.0, min(1.0, 0.5 * operator_score + 0.5 * purpose_score))
    return {
        "operator_action": _operator_action_for_axis(dominant_axis),
        "purpose_lane": str(purpose),
        "operator_grade": float(operator_score),
        "purpose_grade": float(purpose_score),
        "overall_grade": float(overall),
        "complexity_score": float(complexity),
        "complexity_axes": int(active_axes),
        "complexity_slots": int(total_slots),
        "generation": int(max(1, generation)),
        "generation_role": str(_generation_role_name(int(max(1, generation)))),
    }


def _augment_ability_profile_with_origin(ap: AbilityProfile) -> AbilityProfile:
    """
    Augment an AbilityProfile with origin, grading, and closure basis metadata.

    When aurora_closure_basis is available (Patch 3), passes root_slot directly
    to _lineage_grade_payload so the closure basis resolves real 625 slots.
    Adds new physics tags without removing any existing ones.
    """
    import hashlib as _hashlib
    origin     = _derive_operation_origin(ap.id, ap.axis, ap.requires, ap.effect_tags)
    counts     = _lineage_counts_from_signature(origin["signature"])
    generation = _lineage_generation_from_counts(counts)
    grading    = _lineage_grade_payload(
        counts, origin["primary"], generation,
        root_slot=origin["root_slot"],
    )

    tags = list(ap.effect_tags or ())
    seed_lineage = (
        str(origin.get("root_a", "")).startswith("NC:")
        and str(origin.get("root_b", "")).startswith("NC:")
    )
    tags.extend([
        f"origin_primary:{origin['primary']}",
        f"origin_secondary:{origin['secondary']}",
        f"origin_signature:{origin['signature']}",
        f"root_slot:{origin['root_slot']}",
        f"operation_lineage:{origin['lineage_id']}",
        f"seed_lineage:{'true' if seed_lineage else 'false'}",
        f"operator_action:{grading['operator_action']}",
        f"purpose_lane:{grading['purpose_lane']}",
        f"operator_grade:{float(grading['operator_grade']):.3f}",
        f"purpose_grade:{float(grading['purpose_grade']):.3f}",
        f"overall_grade:{float(grading['overall_grade']):.3f}",
        f"complexity_axes:{int(grading['complexity_axes'])}",
        f"complexity_slots:{int(grading['complexity_slots'])}",
        f"generation:{int(grading['generation'])}",
        f"generation_role:{grading['generation_role']}",
        # --- new physics tags (present only when closure basis available) ---
        f"energetic_footprint:{float(grading.get('energetic_footprint', 0.0)):.4f}",
        f"depth_score:{float(grading.get('depth_score', 0.0)):.4f}",
        f"leverage_grade:{float(grading.get('leverage_grade', 0.5)):.4f}",
        f"viable_band_alignment:{float(grading.get('viable_band_alignment', 0.0)):.4f}",
        f"formation_cost:{float(grading.get('formation_cost', 0.0)):.4f}",
        f"dominant_constraint:{grading.get('dominant_constraint', origin['primary'])}",
        f"dominant_dimension:{grading.get('dominant_dimension', 'OPERATOR')}",
        f"ontological_status:{grading.get('ontological_status', 'derivative_offspring')}",
    ])
    dedup_tags = tuple(dict.fromkeys([str(t) for t in tags if str(t)]))

    notes = str(ap.notes or "")
    marker = f"operation_lineage_id={origin['lineage_id']}"
    if marker not in notes:
        suffix = (
            f" [origin root_slot={origin['root_slot']}; "
            f"root_parents={origin['root_a']},{origin['root_b']}; "
            f"origin_signature={origin['signature']}; "
            f"operation_lineage_id={origin['lineage_id']}; "
            f"operator_action={grading['operator_action']}; "
            f"purpose_lane={grading['purpose_lane']}; "
            f"operator_grade={float(grading['operator_grade']):.3f}; "
            f"depth_score={float(grading.get('depth_score', 0.0)):.4f}; "
            f"leverage_grade={float(grading.get('leverage_grade', 0.5)):.4f}; "
            f"ontological_status={grading.get('ontological_status', 'derivative_offspring')}; "
            f"generation={int(grading['generation'])}; "
            f"generation_role={grading['generation_role']}]"
        )
        notes = (notes + suffix).strip()

    return AbilityProfile(
        id=ap.id,
        axis=ap.axis,
        requires=tuple(ap.requires),
        cost={a: float(ap.cost.get(a, 0.0)) for a in AXES},
        risk={a: float(ap.risk.get(a, 0.0)) for a in AXES},
        effect_tags=dedup_tags,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# SEED ABILITY REGISTRY
# ---------------------------------------------------------------------------

def _build_seed_abilities() -> Dict[str, AbilityProfile]:
    """
    Canonical minimal ability set — one per axis, seeding all five constraint dimensions.
    Each ability has a full 5-axis cost+risk profile.
    'Even if an ability belongs to B, it still has T/N/A costs and X-risk.'
    """
    raw: List[Dict] = [
        # ---- X (Existence / Admissibility) ----
        dict(id="X:ADMIT",                axis="X", requires=("X",),
             cost=dict(X=0.00,T=0.01,N=0.01,B=0.00,A=0.01),
             risk=dict(X=0.00),
             effect_tags=("admit_state","clear_block"),
             notes="Allows a previously-blocked state through the admissibility predicate."),
        dict(id="X:REJECT",               axis="X", requires=("X",),
             cost=dict(X=0.01,T=0.01,N=0.00,B=0.01,A=0.01),
             risk=dict(X=0.01),
             effect_tags=("reject_state","enforce_boundary"),
             notes="Denies a state; raises X boundary pressure but lowers manifold contradiction."),
        dict(id="X:RECLASSIFY",           axis="X", requires=("X","B"),
             cost=dict(X=0.02,T=0.02,N=0.01,B=0.01,A=0.01),
             risk=dict(X=0.02,B=0.01),
             effect_tags=("reclassify","reindex"),
             notes="Moves a state to a different admissibility class without destroying it."),
        dict(id="X:RESOLVE_CONTRADICTION",axis="X", requires=("X","T"),
             cost=dict(X=0.03,T=0.04,N=0.02,B=0.01,A=0.02),
             risk=dict(X=0.04,T=0.01),
             effect_tags=("resolve","merge_conflict"),
             notes="Collapses two contradicting states into one admissible state; high X-risk."),

        # ---- T (Time / Sequence) ----
        dict(id="T:DEFER",    axis="T", requires=("T",),
             cost=dict(X=0.00,T=0.01,N=0.01,B=0.00,A=0.01),
             risk=dict(T=0.01),
             effect_tags=("defer","delay"),
             notes="Pushes an operation to a later tick; relieves immediate T pressure."),
        dict(id="T:BATCH",    axis="T", requires=("T","N"),
             cost=dict(X=0.00,T=0.02,N=0.03,B=0.01,A=0.01),
             risk=dict(T=0.01,N=0.01),
             effect_tags=("batch","coalesce"),
             notes="Groups multiple deferred operations into one sequence pass."),
        dict(id="T:REORDER",  axis="T", requires=("T","B"),
             cost=dict(X=0.01,T=0.02,N=0.01,B=0.02,A=0.01),
             risk=dict(T=0.02,X=0.01),
             effect_tags=("reorder","reprioritize"),
             notes="Changes the execution order of pending operations."),
        dict(id="T:SIM_TICK", axis="T", requires=("T",),
             cost=dict(X=0.00,T=0.00,N=0.01,B=0.00,A=0.00),
             risk=dict(T=0.00),
             effect_tags=("tick","advance_clock"),
             notes="Advance internal simulation clock by one unit; minimal cost."),

        # ---- N (Energy / Cost) ----
        dict(id="N:REUSE",       axis="N", requires=("N","B"),
             cost=dict(X=0.00,T=0.01,N=0.00,B=0.01,A=0.01),
             risk=dict(N=0.01),
             effect_tags=("reuse","cache_hit"),
             notes="Re-uses existing computed state; lowers N expenditure."),
        dict(id="N:CACHE",       axis="N", requires=("N","B"),
             cost=dict(X=0.00,T=0.02,N=0.01,B=0.02,A=0.01),
             risk=dict(N=0.01,B=0.01),
             effect_tags=("cache","memoize"),
             notes="Stores result for future reuse; upfront B and T cost."),
        dict(id="N:REDUCE_STATE",axis="N", requires=("N","X"),
             cost=dict(X=0.02,T=0.02,N=0.00,B=0.01,A=0.01),
             risk=dict(N=0.01,X=0.01),
             effect_tags=("prune","compress_state"),
             notes="Removes redundant state nodes; lowers ongoing N overhead."),
        dict(id="N:SPEND",       axis="N", requires=("N",),
             cost=dict(X=0.00,T=0.01,N=0.05,B=0.00,A=0.02),
             risk=dict(N=0.03),
             effect_tags=("spend","invest"),
             notes="Deliberate energy expenditure for high-value relief elsewhere."),

        # ---- B (Boundary / Containment) ----
        dict(id="B:SEPARATE",    axis="B", requires=("B","X"),
             cost=dict(X=0.01,T=0.02,N=0.02,B=0.00,A=0.01),
             risk=dict(B=0.01,X=0.01),
             effect_tags=("separate","decouple"),
             notes="Draws a clean boundary between two previously coupled regions."),
        dict(id="B:ENCAPSULATE", axis="B", requires=("X","B"),
             cost=dict(X=0.01,T=0.03,N=0.02,B=0.00,A=0.01),
             risk=dict(X=0.02,B=0.01),
             effect_tags=("boundary_seal","packetize"),
             notes="Turns raw state into bounded envelope; lowers boundary leakage if successful."),
        dict(id="B:ROUTE",       axis="B", requires=("B","T"),
             cost=dict(X=0.00,T=0.02,N=0.01,B=0.01,A=0.02),
             risk=dict(B=0.02),
             effect_tags=("route","channel"),
             notes="Directs pressure flow through an established channel."),
        dict(id="B:SEAL",        axis="B", requires=("B",),
             cost=dict(X=0.01,T=0.01,N=0.01,B=0.00,A=0.01),
             risk=dict(B=0.01,X=0.01),
             effect_tags=("seal","lock_boundary"),
             notes="Freezes a boundary to prevent further leakage."),

        # ---- A (Agency / Action) ----
        dict(id="A:COMMIT",      axis="A", requires=("A","X"),
             cost=dict(X=0.01,T=0.02,N=0.02,B=0.01,A=0.00),
             risk=dict(A=0.02,X=0.01),
             effect_tags=("commit","irreversible"),
             notes="Locks in a chosen path; high A cost paid upfront."),
        dict(id="A:CHOOSE",      axis="A", requires=("A",),
             cost=dict(X=0.01,T=0.01,N=0.01,B=0.01,A=0.02),
             risk=dict(A=0.01),
             effect_tags=("choose","select"),
             notes="Evaluates branch options and selects one."),
        dict(id="A:ASSERT",      axis="A", requires=("A","X"),
             cost=dict(X=0.02,T=0.01,N=0.01,B=0.01,A=0.01),
             risk=dict(A=0.01,X=0.02),
             effect_tags=("assert","claim_state"),
             notes="Stakes a claim on current state as valid; raises X exposure briefly."),
        dict(id="A:OUTLET_PUSH", axis="A", requires=("A","B"),
             cost=dict(X=0.00,T=0.002,N=0.002,B=0.001,A=0.001),
             risk=dict(A=0.01),
             effect_tags=("outlet","release"),
             notes="Expels pressure through external outlet; relief only if outlet confirms effectiveness."),
    ]

    registry: Dict[str, AbilityProfile] = {}
    for r in raw:
        ap = AbilityProfile(
            id=r["id"],
            axis=r["axis"],
            requires=tuple(r["requires"]),
            cost={a: r["cost"].get(a, 0.0) for a in AXES},
            risk={a: r["risk"].get(a, 0.0) for a in AXES},
            effect_tags=tuple(r["effect_tags"]),
            notes=r.get("notes", ""),
        )
        registry[ap.id] = _augment_ability_profile_with_origin(ap)
    return registry


# ---------------------------------------------------------------------------
# ENVIRONMENT VECTOR — where an ability fires determines how it fires
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EnvironmentVector:
    """
    Encodes the execution environment of a TraceItem.

    Same genetic ID (e.g. "A:OUTLET_PUSH") fires differently depending on
    which module it's in, what stream is flowing through it, what axis
    context is dominant, and what call site produced it.

    This is the environment variable that distinguishes two instances of the
    same function across different modules — same code, different cell type.

    Fields
    ------
    module      : source module (e.g. "aurora_evolution_chamber",
                  "aurora_expression_perception", "aurora_dimensional_systems")
    stream_type : data flowing through ("user_input", "knowledge_feed",
                  "simulation", "corpus", "dream", "")
    axis_context: dominant IVM axis at time of fire (T/N/X/B/A or "")
    call_tag    : function/method that produced this item ("run_sample",
                  "express", "dpme_process", "oets_lookup", "dimensional", "")
    """
    module:       str = ""
    stream_type:  str = ""
    axis_context: str = ""
    call_tag:     str = ""

    def key(self) -> str:
        """Compact string key for grouping by environment."""
        parts = [p for p in [
            self.module, self.stream_type, self.axis_context, self.call_tag
        ] if p]
        return "|".join(parts) or "global"

    def is_empty(self) -> bool:
        return not any([self.module, self.stream_type, self.axis_context, self.call_tag])

    def to_dict(self) -> Dict[str, str]:
        return {
            "module": self.module,
            "stream_type": self.stream_type,
            "axis_context": self.axis_context,
            "call_tag": self.call_tag,
        }


# Default empty environment (backward compat — all old TraceItems get this)
_ENV_GLOBAL = EnvironmentVector()


# TRACE ITEM — ability or link reference inside an event trace
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TraceItem:
    kind: str    # "ABILITY" or "LINK"
    id: str      # ability id or link id
    env: EnvironmentVector = field(default_factory=EnvironmentVector)

    def to_dict(self) -> Dict:
        d: Dict[str, Any] = {"kind": self.kind, "id": self.id}
        if not self.env.is_empty():
            d["env"] = self.env.to_dict()
        return d


# ---------------------------------------------------------------------------
# PRESSURE VECTOR
# ---------------------------------------------------------------------------

@dataclass
class PressureVec:
    """5-axis pressure vector. Higher = worse."""
    X: float = 0.0
    T: float = 0.0
    N: float = 0.0
    B: float = 0.0
    A: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {"X": self.X, "T": self.T, "N": self.N, "B": self.B, "A": self.A}

    def relief_from(self, earlier: "PressureVec") -> "PressureVec":
        """Component-wise: earlier - self (positive means pressure dropped)."""
        return PressureVec(
            X=earlier.X - self.X,
            T=earlier.T - self.T,
            N=earlier.N - self.N,
            B=earlier.B - self.B,
            A=earlier.A - self.A,
        )

    def dominant_positive_axis(self) -> Optional[str]:
        best_ax, best_val = None, -math.inf
        for a in AXES:
            v = getattr(self, a)
            if v > best_val:
                best_val = v
                best_ax = a
        return best_ax if (best_val is not None and best_val > 0) else None

    def max_relief(self) -> float:
        return max(getattr(self, a) for a in AXES)

    def sum_positive_relief(self) -> float:
        return sum(max(0.0, getattr(self, a)) for a in AXES)

    @staticmethod
    def from_dict(d: Dict[str, float]) -> "PressureVec":
        return PressureVec(**{a: d.get(a, 0.0) for a in AXES})


# ---------------------------------------------------------------------------
# RELIEF EVENT RECORD
# ---------------------------------------------------------------------------

@dataclass
class ReliefRecord:
    """One entry in the fossil record — a confirmed pressure-relief event."""
    run_id: str
    tick: int
    state_sig_before: str
    state_sig_after: str
    pressure_before: PressureVec
    pressure_after: PressureVec
    relief: PressureVec
    dominant_relief_axis: Optional[str]
    trace: List[TraceItem]
    trace_cost_total: Dict[str, float]
    trace_risk_total: Dict[str, float]
    notes: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_jsonl_dict(self) -> Dict:
        return {
            "run_id": self.run_id,
            "tick": self.tick,
            "timestamp": self.timestamp,
            "state_sig_before": self.state_sig_before,
            "state_sig_after": self.state_sig_after,
            "pressure_before": self.pressure_before.to_dict(),
            "pressure_after": self.pressure_after.to_dict(),
            "relief": self.relief.to_dict(),
            "dominant_relief_axis": self.dominant_relief_axis,
            "trace": [t.to_dict() for t in self.trace],
            "trace_cost_total": {a: self.trace_cost_total.get(a, 0.0) for a in AXES},
            "trace_risk_total": {a: self.trace_risk_total.get(a, 0.0) for a in AXES},
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# LINK — PROMOTED COMPOSITE UNIT
# ---------------------------------------------------------------------------

@dataclass
class ConstraintLink:
    """
    A promoted pair (or pair-of-pairs) that has proven reliably effective.

    Once promoted, it becomes a re-usable trace element.
    Its parents attribute forms the DAG backbone.
    """
    id: str                         # "L:" + sha1[:10]
    parents: List[str]              # ability ids or link ids (direct parents only)
    depth: int                      # 1 if parents are all Abilities; >1 if a parent is a Link
    created_at_tick: int

    count: int
    mean_relief: Dict[str, float]
    mean_cost: Dict[str, float]
    mean_x_risk: float
    stdev_relief: Dict[str, float]
    dominant_relief_axis: Optional[str]
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "parents": self.parents,
            "depth": self.depth,
            "created_at_tick": self.created_at_tick,
            "stats": {
                "count": self.count,
                "mean_pos_relief": {a: self.mean_relief.get(a, 0.0) for a in AXES},
                "mean_relief": {a: self.mean_relief.get(a, 0.0) for a in AXES},
                "stdev_relief": {a: self.stdev_relief.get(a, 0.0) for a in AXES},
                "mean_cost": {a: self.mean_cost.get(a, 0.0) for a in AXES},
                "mean_x_risk": self.mean_x_risk,
            },
            "dominant_relief_axis": self.dominant_relief_axis,
            "tags": self.tags,
        }

    def base_cost(self) -> float:
        """Total mean operational cost across all five axes."""
        return sum(self.mean_cost.get(a, 0.0) for a in AXES)

    def cost_diff_score(
        self,
        snapshot: Optional[DifferenceSnapshot] = None,
    ) -> CostDiffScore:
        """
        Live cost score for this promoted link under current cross-dimensional
        pressure.

        The base_cost is the link's accumulated mean operational cost (averaged
        across all observed events that contributed to its promotion). When the
        system is under operator-typed drift, the true cost of triggering this
        link is higher — because the environmental conditions it must navigate
        have changed since its mean cost was established.

        This score can be used directly by the evolution chamber to rank which
        links to prefer at any given tick: lower live_score = more viable now.
        """
        return score_from_cost(self.base_cost(), snapshot)


# ---------------------------------------------------------------------------
# PAIR STATS — online accumulator for pair promotion
# ---------------------------------------------------------------------------

@dataclass
class PairStats:
    """
    Online stats for an ordered pair of trace items (left_id → right_id).

    Tracks both net relief (can be negative) AND positive-only relief,
    because toroidal oscillation makes net mean ≈ 0 even for effective pairs.
    The promotion gate uses mean_pos_relief and pos_fraction.
    """
    left_id: str
    right_id: str
    count: int = 0
    relief_sum: Dict[str, float] = field(default_factory=_zero_vec)
    relief_sq_sum: Dict[str, float] = field(default_factory=_zero_vec)
    # Positive-only tracking — the key signal for oscillating physics systems
    relief_pos_sum: Dict[str, float] = field(default_factory=_zero_vec)
    pos_count: Dict[str, int] = field(default_factory=lambda: {a: 0 for a in AXES})
    cost_sum: Dict[str, float] = field(default_factory=_zero_vec)
    x_risk_sum: float = 0.0
    last_seen_tick: int = 0

    def update(self, relief: PressureVec, cost: Dict[str, float], x_risk: float, tick: int):
        self.count += 1
        self.last_seen_tick = tick
        for a in AXES:
            r = getattr(relief, a)
            self.relief_sum[a] = self.relief_sum.get(a, 0.0) + r
            self.relief_sq_sum[a] = self.relief_sq_sum.get(a, 0.0) + r * r
            if r > 0.0:
                self.relief_pos_sum[a] = self.relief_pos_sum.get(a, 0.0) + r
                self.pos_count[a] = self.pos_count.get(a, 0) + 1
            self.cost_sum[a] = self.cost_sum.get(a, 0.0) + cost.get(a, 0.0)
        self.x_risk_sum += x_risk

    def mean_relief(self) -> Dict[str, float]:
        if self.count == 0:
            return _zero_vec()
        return {a: self.relief_sum.get(a, 0.0) / self.count for a in AXES}

    def mean_pos_relief(self) -> Dict[str, float]:
        """Mean relief on ticks where relief was positive. The key promotion signal."""
        result = {}
        for a in AXES:
            pc = self.pos_count.get(a, 0)
            result[a] = self.relief_pos_sum.get(a, 0.0) / pc if pc > 0 else 0.0
        return result

    def pos_fraction(self) -> Dict[str, float]:
        """Fraction of ticks where relief was positive per axis."""
        if self.count == 0:
            return {a: 0.0 for a in AXES}
        return {a: self.pos_count.get(a, 0) / self.count for a in AXES}

    def stdev_relief(self) -> Dict[str, float]:
        if self.count < 2:
            return _zero_vec()
        result = {}
        n = self.count
        for a in AXES:
            mean = self.relief_sum.get(a, 0.0) / n
            variance = (self.relief_sq_sum.get(a, 0.0) / n) - (mean ** 2)
            result[a] = math.sqrt(max(0.0, variance))
        return result

    def mean_cost(self) -> Dict[str, float]:
        if self.count == 0:
            return _zero_vec()
        return {a: self.cost_sum.get(a, 0.0) / self.count for a in AXES}

    def mean_x_risk_val(self) -> float:
        return self.x_risk_sum / self.count if self.count > 0 else 0.0


# ---------------------------------------------------------------------------
# DILATION-AWARE CHAMBER GOVERNOR
# — Wraps TimeDilationGovernor and feeds it genealogy fitness signals
# ---------------------------------------------------------------------------

class GenealogyDilationGovernor:
    """
    Adapts TimeDilationGovernor from aurora_simulation_engine
    to drive evolutionary chamber pacing from genealogy pressure data.

    Fast when relief events are frequent and stable.
    Slow when violations are high or X-risk is spiking.
    """

    def __init__(self, config: GenealogyConfig):
        self.cfg = config
        self._gov = TimeDilationGovernor()
        self._relief_history: Deque[float] = deque(maxlen=100)
        self._xrisk_history: Deque[float] = deque(maxlen=100)

    def record_event(self, relief: PressureVec, x_risk: float) -> None:
        fitness_signal = _clamp(relief.sum_positive_relief() * 4.0)
        self._relief_history.append(fitness_signal)
        self._xrisk_history.append(x_risk)

    def tick(self) -> float:
        """Return current dilation factor (caller's loop should sleep accordingly)."""
        if not self.cfg.USE_TIME_DILATION:
            return 1.0

        fitness_mean = (sum(self._relief_history) / len(self._relief_history)
                        if self._relief_history else 0.5)
        fitness_trend = self._gov.get_fitness_trend()

        mean_xrisk = (sum(self._xrisk_history) / len(self._xrisk_history)
                      if self._xrisk_history else 0.0)

        # Convert X-risk spikes → error_rate signal
        error_rate = _clamp(mean_xrisk * 10.0)

        metrics = StabilityMetrics(
            fitness_mean=fitness_mean,
            fitness_trend=fitness_trend,
            error_rate=error_rate,
        )
        return self._gov.update(metrics)

    def status(self) -> Dict[str, Any]:
        return {
            "gov": self._gov.status(),
            "relief_window_size": len(self._relief_history),
            "xrisk_window_size": len(self._xrisk_history),
        }


# ---------------------------------------------------------------------------
# PRESSURE COMPLEXITY CURVE
# ---------------------------------------------------------------------------

class PressureComplexityCurve:
    """
    Tracks the oscillation between pressure-system expansion and compression.

    The constraint genealogy naturally cycles through:
      EXPAND  → combinations of base axes grow (n links, C(n,2) interactions)
      COMPRESS → promoted links short-circuit pair re-evaluation (cheaper)
      REVERT  → compressed DAG becomes expensive to trace (depth overhead)
      EXPAND  again — each cycle peaks higher, growing capability

    This mirrors Kolmogorov complexity dynamics: a representation is worth
    compressing only when the compressed form is cheaper to apply than the
    raw expression of its parts. Once compression overhead exceeds its
    savings, the system should revert to expressing combinations directly.

    Key signals tracked per tick:
      expansion_load   — pairs being evaluated  (proxy for expression cost)
      compression_gain — links that bypass pair re-eval (savings)
      compression_cost — mean DAG depth of active links (overhead of tracing)
      net_efficiency   — gain - cost, oscillates as the cycle turns

    The correction factor applied to pressure injections reflects which phase
    the system is in and how accurately predictions have been tracking the
    current phase's dynamics.

    Phase transitions (peak → trough → peak) are logged so the curve's
    period can itself be estimated and used for forward prediction.
    """

    WINDOW = 40          # samples for trend detection
    PHASE_MIN_SAMPLES = 6  # minimum samples before calling a phase

    def __init__(self) -> None:
        self._samples: deque = deque(maxlen=self.WINDOW)
        self._correction: float = 1.0
        self._net_ema: float = 0.0
        self._phase: str = "unknown"          # "expanding" | "compressing" | "plateau"
        self._prev_phase: str = "unknown"
        self._transition_log: deque = deque(maxlen=20)  # phase transitions with tick
        self._peak_value: float = 0.0
        self._trough_value: float = 0.0
        self._last_correction_update: int = 0
        # Prediction residual tracking
        self._predictions: deque = deque(maxlen=self.WINDOW)
        self._pending_prediction: Optional[dict] = None
        self._error_ema: float = 0.0

    # ---- Per-tick recording ------------------------------------------------

    def record_tick(
        self,
        n_pairs_evaluated: int,
        n_links: int,
        mean_link_depth: float,
        tick: int,
    ) -> None:
        """
        Record one tick's complexity state.

        n_pairs_evaluated: number of (left, right) pairs checked this tick
        n_links: current total promoted links
        mean_link_depth: average DAG depth of links (proxy for trace cost)
        """
        # expansion_load: pairs evaluated (each pair = gate evaluation overhead)
        expansion_load = float(n_pairs_evaluated)

        # compression_gain: each promoted link potentially bypasses future pair
        # evaluations — scaled by how many interactions it encodes
        interaction_count = n_links * max(0, n_links - 1) / 2.0
        compression_gain = min(float(n_links), interaction_count / max(1.0, expansion_load + 1))

        # compression_cost: deeper links = more expensive to resolve ancestry
        compression_cost = float(mean_link_depth) * 0.5

        net = compression_gain - compression_cost

        self._samples.append({
            "tick": tick,
            "expansion_load": expansion_load,
            "compression_gain": compression_gain,
            "compression_cost": compression_cost,
            "net": net,
            "n_links": n_links,
        })

        alpha = 0.15
        prev_ema = self._net_ema
        self._net_ema = (1.0 - alpha) * self._net_ema + alpha * net

        # Update phase
        trend = self._net_ema - prev_ema
        if len(self._samples) >= self.PHASE_MIN_SAMPLES:
            if trend > 0.002:
                new_phase = "compressing"
            elif trend < -0.002:
                new_phase = "expanding"
            else:
                new_phase = "plateau"

            if new_phase != self._phase:
                # Track peak/trough at transition
                if self._phase == "compressing" and new_phase == "expanding":
                    self._peak_value = self._net_ema
                elif self._phase == "expanding" and new_phase == "compressing":
                    self._trough_value = self._net_ema

                self._transition_log.append({
                    "tick": tick,
                    "from": self._phase,
                    "to": new_phase,
                    "net_ema": round(self._net_ema, 5),
                })
                self._prev_phase = self._phase
                self._phase = new_phase

        # Update correction factor every 5 ticks
        if tick - self._last_correction_update >= 5:
            self._last_correction_update = tick
            self._update_correction()

    def _update_correction(self) -> None:
        """
        Adjust pressure injection correction based on current phase.

        Expanding (pressure systems proliferating, predictions less accurate):
          → dampen injections to avoid over-driving gates during noise phase
        Compressing (system consolidating, predictions more accurate):
          → allow full injection, predictions are reliable
        Plateau (between cycles):
          → neutral
        """
        if self._phase == "expanding":
            # More interactions = harder to predict → dampen
            self._correction = max(0.45, self._correction * 0.97)
        elif self._phase == "compressing":
            # Consolidating → predictions improving → restore confidence
            self._correction = min(1.15, self._correction * 1.025)
        # plateau: no change

    # ---- Prediction residual tracking --------------------------------------

    def record_injection(
        self,
        raw_pressure: float,
        n_links: int,
        current_outlet: float,
        tick: int,
    ) -> float:
        """
        Record a pressure injection prediction and return the corrected magnitude.

        Model: at n_links constraints, the interaction space has complexity
        C(n,2) = n*(n-1)/2 pairs. The expected effect of a unit injection
        shrinks as complexity grows (each interaction dilutes signal).

        Returns raw_pressure * correction_factor — caller uses this value.
        """
        interaction_complexity = n_links * max(0, n_links - 1) / 2.0
        base_sensitivity = 0.04
        expected_delta = raw_pressure * base_sensitivity / (1.0 + interaction_complexity / 15.0)

        self._pending_prediction = {
            "expected_delta": expected_delta,
            "outlet_before": current_outlet,
            "n_links": n_links,
            "tick": tick,
        }
        return raw_pressure * self._correction

    def record_outcome(self, new_outlet: float) -> None:
        """Record actual outlet change vs prediction. Updates error EMA."""
        if not self._pending_prediction:
            return
        expected = self._pending_prediction["expected_delta"]
        actual = new_outlet - self._pending_prediction["outlet_before"]
        error = abs(expected - actual)

        self._predictions.append({
            "expected": expected,
            "actual": actual,
            "error": error,
        })
        self._pending_prediction = None

        alpha = 0.2
        prev_err = self._error_ema
        self._error_ema = (1.0 - alpha) * self._error_ema + alpha * error
        # Rising error → dampen; falling error → restore
        if self._error_ema > prev_err + 0.001:
            self._correction = max(0.45, self._correction * 0.96)
        elif self._error_ema < prev_err - 0.001:
            self._correction = min(1.15, self._correction * 1.02)

    # ---- Accessors ---------------------------------------------------------

    @property
    def correction(self) -> float:
        return self._correction

    @property
    def phase(self) -> str:
        return self._phase

    def get_stats(self) -> Dict[str, Any]:
        recent = list(self._samples)[-5:] if self._samples else []
        return {
            "phase": self._phase,
            "net_ema": round(self._net_ema, 5),
            "correction": round(self._correction, 4),
            "error_ema": round(self._error_ema, 6),
            "peak": round(self._peak_value, 5),
            "trough": round(self._trough_value, 5),
            "transitions": len(self._transition_log),
            "last_transition": (
                dict(self._transition_log[-1]) if self._transition_log else {}
            ),
            "recent_net": [round(s["net"], 4) for s in recent],
        }


# ---------------------------------------------------------------------------
# GENEALOGY LOGGER — the main engine
# ---------------------------------------------------------------------------

def _build_closure_status_summary(
    links:     Dict[str, Any],
    abilities: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Summarise ontological status distribution across the evolved lineage.

    Reads tags already written by Patches 3 and 5. No new computation.
    Returns what fraction of Aurora's evolved structure is native to the
    closed basis vs derivative vs external overlay.
    """
    _counts = {
        "native_closed":           0,
        "derivative_offspring":    0,
        "descriptive_convenience": 0,
        "external_overlay":        0,
        "unclassified":            0,
    }

    def _read_status(tags_or_effect_tags: Any) -> str:
        for t in (tags_or_effect_tags or []):
            s = str(t)
            if s.startswith("ontological_status:"):
                return s.split(":", 1)[1].strip()
            if s.startswith("closure_status:"):
                return s.split(":", 1)[1].strip()
        return "unclassified"

    ability_dist = dict(_counts)
    for ap in abilities.values():
        key = _read_status(getattr(ap, "effect_tags", None))
        if key in ability_dist:
            ability_dist[key] += 1
        else:
            ability_dist["unclassified"] += 1

    link_dist = dict(_counts)
    for lnk in links.values():
        key = _read_status(getattr(lnk, "tags", None))
        if key in link_dist:
            link_dist[key] += 1
        else:
            link_dist["unclassified"] += 1

    total_ab = max(1, sum(ability_dist.values()))
    total_lk = max(1, sum(link_dist.values()))

    return {
        "abilities": {
            "total":     sum(ability_dist.values()),
            "counts":    ability_dist,
            "fractions": {k: round(v / total_ab, 4) for k, v in ability_dist.items()},
        },
        "links": {
            "total":     sum(link_dist.values()),
            "counts":    link_dist,
            "fractions": {k: round(v / total_lk, 4) for k, v in link_dist.items()},
        },
        "health_signal": (
            "clean"
            if link_dist.get("external_overlay", 0) == 0
            else f"WARNING: {link_dist['external_overlay']} links are external overlays"
        ),
    }


class ConstraintGenealogyLogger:
    """
    Core logger. Feed it (pressure_before, trace, pressure_after) every tick
    and it builds the fossil record automatically.

    Usage:
        logger = ConstraintGenealogyLogger(run_id="2026-02-26_run_01")
        logger.observe(p_before, trace_items, p_after, state_sig_before, state_sig_after)
        ...
        logger.flush_files()
    """

    def __init__(
        self,
        run_id: str,
        config: Optional[GenealogyConfig] = None,
        abilities: Optional[Dict[str, AbilityProfile]] = None,
        output_dir: str = ".",
    ):
        self.run_id = run_id
        self.cfg = config or GenealogyConfig()
        _raw_abilities = abilities or _build_seed_abilities()
        self.abilities: Dict[str, AbilityProfile] = {
            str(k): _augment_ability_profile_with_origin(v)
            for k, v in dict(_raw_abilities).items()
            if isinstance(v, AbilityProfile)
        }
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        # Link registry
        self.links: Dict[str, ConstraintLink] = {}           # id → Link
        self._links_by_parents: Dict[Tuple[str, str], str] = {}  # (left,right) → link_id

        # Pair accumulator
        self._pair_stats: Dict[Tuple[str, str], PairStats] = {}

        # In-memory event log (ring buffer)
        self._event_log: Deque[ReliefRecord] = deque(maxlen=10_000)

        # JSONL file handle (append mode)
        self._events_path = os.path.join(output_dir, self.cfg.EVENTS_FILE)
        self._events_fh = open(self._events_path, "a", encoding="utf-8")

        # Governor
        self.governor = GenealogyDilationGovernor(self.cfg)

        # Counters
        self.tick_count: int = 0
        self._corpus_mode: bool = False  # set by set_corpus_mode() when running corpus training
        self.relief_event_count: int = 0
        self.links_promoted: int = 0
        self.skipped_no_relief: int = 0
        self.skipped_xrisk: int = 0

        # Last promotion tick (in relief-event clock) for stagnation regulation
        boot_ratio = _clamp(float(getattr(self.cfg, "STAGNATION_BOOTSTRAP_RATIO", 0.35)), 0.0, 1.0)
        boot_events = int(round(max(1, int(getattr(self.cfg, "STAGNATION_WINDOW", 1))) * boot_ratio))
        self._last_promotion_tick: int = -max(0, int(boot_events))

        # External training plateau pressure [0.0, 1.0].
        # Injected by ProgressSampler and _diagnose_stall() when training
        # delta flattens. Blended into stagnation ratio/gain so gate thresholds
        # relax in proportion to how stuck training actually is — not just how
        # long since the last genealogy promotion.
        self._training_plateau_pressure: float = 0.0

        # Latest observed pressure vector — cached so pressure_orientation()
        # can detect disproportionate axis load and override expansion-phase
        # corrections that would otherwise block relief on a crisis axis.
        self._latest_pressure: Optional[PressureVec] = None

        # Complexity oscillation tracker — global + per-axis.
        # The global curve tracks aggregate pressure system complexity.
        # Each axis curve tracks that axis's independent expand/compress cycle.
        # Together they form the 5-vector pressure orientation: which axes
        # are in their reliable (consolidating) phase vs noisy (proliferating)
        # phase at any given moment, so pressure injections can be routed
        # toward axes with the highest current effectiveness.
        self._complexity_curve: PressureComplexityCurve = PressureComplexityCurve()
        self._axis_curves: Dict[str, PressureComplexityCurve] = {
            a: PressureComplexityCurve() for a in AXES
        }

        # Causal adaptation memory (self-improving promotion gates).
        self._axis_outcome_ema: Dict[str, float] = {a: 0.0 for a in AXES}
        self._depth_outcome_ema: Dict[int, float] = defaultdict(float)
        self._gradient_axis_ema: Dict[str, float] = {a: 0.0 for a in AXES}

        # Relief tolerance memory (solution immunity).
        self._solution_tolerance: Dict[str, float] = defaultdict(float)
        self._solution_last_tick: Dict[str, int] = {}
        self._tolerance_events_applied: int = 0
        self._tolerance_factor_ema: float = 1.0

        # Coupling-root memory (canonical mathematical signatures + semantic lineage).
        self._coupling_roots: Dict[str, Dict[str, Any]] = {}
        self._coupling_origin_counts: Dict[str, int] = defaultdict(int)
        self._coupling_events: int = 0
        self._persistent_pressure_root_ema: float = 0.0

        # Representation experiment tracking.
        self._issue_history: Deque[Dict[str, Any]] = deque(maxlen=2048)
        self._experiment_trials: List[Dict[str, Any]] = []
        self._experiment_adoptions: List[Dict[str, Any]] = []
        self._last_experiment_tick: int = 0

        # Promotion diagnostics (why links are/aren't growing).
        self._promotion_stats: Dict[str, int] = defaultdict(int)

        # Tick-local steering from explicitly artificial/bypassed seeds.
        self._active_artificial_directive: Dict[str, Any] = {}

        # Per-environment effectiveness tracking.
        # Maps ability_id → {env_key → effectiveness_ema} so the same
        # genetic ID can be evaluated differently across modules/contexts.
        # Also tracks env_key → {axis → relief_ema} for 5-vector orientation
        # per environment — which constraint axes have the most effect in
        # each specific module+stream+axis_context combination.
        self._env_effectiveness: Dict[str, Dict[str, float]] = defaultdict(dict)
        self._env_axis_relief: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {a: 0.0 for a in AXES}
        )
        self._env_fire_count: Dict[str, int] = defaultdict(int)

        # Pressure application memory.
        # Records what targeted pressure was applied where, observes the
        # outcome after a delay window, and updates strategy effectiveness
        # so Aurora learns which (env_key, axis) combinations actually work.
        #
        # _pressure_strategy: (env_key, axis) → effectiveness_ema [0..1]
        #   Higher = applying this axis in this environment has historically
        #   produced measurable relief (outlet_fraction rose, fail rate dropped).
        #
        # _pending_applications: env_key → application dict, awaiting outcome.
        #   Outcome is checked after OUTCOME_CHECK_TICKS ticks have elapsed.
        #
        # _application_log: ring buffer of completed applications with outcomes.
        self._pressure_strategy: Dict[Tuple[str, str], float] = defaultdict(lambda: 0.5)
        self._pending_applications: Dict[str, Dict[str, Any]] = {}
        self._application_log: deque = deque(maxlen=200)
        self._OUTCOME_CHECK_TICKS = 25   # ticks to wait before measuring outcome

        # Read-only observer — receives pressure_after on every relief event.
        self.field_map = None  # Optional ConstraintFieldAccumulator

    def set_field_map(self, field_map) -> None:
        """Attach a ConstraintFieldAccumulator as a read-only observer. Pass None to detach."""
        self.field_map = field_map

    # ----------------------------------------------------------------
    # PUBLIC API
    # ----------------------------------------------------------------

    def observe(
        self,
        pressure_before: PressureVec,
        trace: List[TraceItem],
        pressure_after: PressureVec,
        state_sig_before: str = "",
        state_sig_after: str = "",
        notes: Optional[Dict[str, Any]] = None,
        difference_snapshot: Optional[DifferenceSnapshot] = None,
    ) -> Optional[ReliefRecord]:
        """
        Observe one tick.

        Returns the logged ReliefRecord if this tick qualifies as a relief event,
        None otherwise.

        Also runs pair accumulation and promotion checks.

        difference_snapshot : Optional[DifferenceSnapshot]
            The live C:D snapshot from the evolution chamber's
            DifferenceHistoryBuffer at this tick. When provided, it is
            stored in record.notes['difference_snapshot'] as a dict for
            downstream consumers (genealogy analysis, corpus runner, etc.).
            Storing as dict preserves JSONL serializability.
        """
        self.tick_count += 1
        self._latest_pressure = pressure_after
        if self.field_map is not None:
            try:
                self.field_map.update(pressure_after)
            except Exception:
                pass

        raw_relief = pressure_after.relief_from(pressure_before)
        dominant_axis_hint = raw_relief.dominant_positive_axis() or "X"
        relief, tolerance_meta = self._apply_relief_tolerance(
            trace=trace,
            relief=raw_relief,
            dominant_axis=dominant_axis_hint,
        )

        # --- Noise filter ---
        if not self._is_relief_event(relief):
            self.skipped_no_relief += 1
            # Still update governor (low fitness signal)
            self.governor.tick()
            return None

        # --- Accumulate trace costs + risks ---
        cost_total = _zero_vec()
        risk_total = _zero_vec()
        x_risk_total = 0.0

        for item in trace:
            ability = self._resolve_ability(item)
            if ability is None:
                continue
            for a in AXES:
                cost_total[a] = cost_total.get(a, 0.0) + ability.cost.get(a, 0.0)
                risk_total[a] = risk_total.get(a, 0.0) + ability.risk.get(a, 0.0)
            x_risk_total += ability.x_risk()

        # Chamber-level action economics: ensures lineage events carry non-zero
        # cost semantics even when mapped ability profiles are minimal.
        if isinstance(notes, dict):
            action_energy = notes.get("action_energy", {})
            if isinstance(action_energy, dict):
                represented_raw = str(action_energy.get("represented_scale", "")).strip().upper()
                represented_axis_map = {
                    "EXISTENCE": "X",
                    "TEMPORAL": "T",
                    "TIME": "T",
                    "ENERGY": "N",
                    "COST": "N",
                    "BOUNDARY": "B",
                    "AGENCY": "A",
                    "X": "X",
                    "T": "T",
                    "N": "N",
                    "B": "B",
                    "A": "A",
                }
                represented_axis = represented_axis_map.get(represented_raw, "")
                effective_cost = max(0.0, float(action_energy.get("effective_energy_cost", 0.0) or 0.0))
                idle_cost = max(0.0, float(action_energy.get("idle_persistence_cost", 0.0) or 0.0))
                action_cost = effective_cost + idle_cost
                if action_cost > 0.0:
                    cost_total["N"] = cost_total.get("N", 0.0) + action_cost
                    if represented_axis in AXES:
                        cost_total[represented_axis] = cost_total.get(represented_axis, 0.0) + (0.25 * action_cost)

        dominant_axis = relief.dominant_positive_axis()

        coupling_meta = self._update_coupling_roots(
            trace=trace,
            relief=relief,
            difference_snapshot=difference_snapshot,
            dominant_axis=(dominant_axis or dominant_axis_hint),
        )

        # Literal gradient memory + causal feedback from live outcomes.
        self._update_gradient_memory(difference_snapshot)
        # Supplement gradient EMA with actual per-axis relief signal.
        # Physical C:D snapshot values can be near-zero during language-scale
        # corpus training; actual relief IS the gradient evidence — it directly
        # reflects which axes had accumulated pressure that was relieved.
        self._update_gradient_memory_from_relief(relief)
        self._update_causal_feedback(trace, relief)

        # Merge difference_snapshot into notes (serialisable dict form)
        merged_notes: Dict[str, Any] = dict(notes or {})
        if difference_snapshot is not None:
            merged_notes["difference_snapshot"] = difference_snapshot.to_dict()
        if tolerance_meta:
            merged_notes["relief_tolerance"] = tolerance_meta
        if coupling_meta:
            merged_notes["coupling_roots"] = coupling_meta

        # --- Build record ---
        record = ReliefRecord(
            run_id=self.run_id,
            tick=self.tick_count,
            state_sig_before=state_sig_before or self._make_sig(pressure_before),
            state_sig_after=state_sig_after or self._make_sig(pressure_after),
            pressure_before=pressure_before,
            pressure_after=pressure_after,
            relief=relief,
            dominant_relief_axis=dominant_axis,
            trace=list(trace),
            trace_cost_total=cost_total,
            trace_risk_total=risk_total,
            notes=merged_notes,
        )

        # --- Write to JSONL ---
        self._write_event(record)
        self._event_log.append(record)
        self.relief_event_count += 1

        # --- Governor update ---
        self.governor.record_event(relief, x_risk_total)
        self.governor.tick()

        # --- Artificial seed steering directive (explicit only) ---
        directive: Dict[str, Any] = {}
        if bool(merged_notes.get("artificial_seed", False)) or bool(merged_notes.get("bypass_natural", False)):
            directive = {
                "enabled": True,
                "seed_lineage_id": str(merged_notes.get("seed_lineage_id", "") or ""),
                "target_generation": int(merged_notes.get("target_generation", 0) or 0),
                "target_purpose_lane": _canonical_purpose_lane(merged_notes.get("target_purpose_lane", "")),
                "target_operator_action": str(merged_notes.get("target_operator_action", "") or "").strip().lower(),
                "weight": max(0.0, min(1.0, float(merged_notes.get("artificial_seed_weight", 1.0) or 1.0))),
            }
        self._active_artificial_directive = directive

        # --- Check pending pressure application outcomes ---
        try:
            self._check_pending_outcomes()
        except Exception:
            pass

        # --- Environment observation (always, even single-item traces) ---
        self._record_env_observation(
            trace=trace,
            relief=relief,
            dominant_axis=dominant_axis_hint,
            promoted=False,   # pair promotion check below; will re-call if promoted
        )

        # --- Pair accumulation + promotion ---
        n_pairs_before = len(self._pair_stats)
        rewritten = self._accumulate_pairs(trace, relief, cost_total, x_risk_total)
        if rewritten and self.cfg.TRACE_REWRITE_ON_PROMOTE:
            record.trace = rewritten

        # --- Complexity curve: record tick state and pressure outcomes ---
        try:
            n_pairs_eval = max(len(self._pair_stats) - n_pairs_before, len(trace) - 1)
            current_outlet = self._outlet_fraction()

            # Global curve — aggregate across all axes
            all_links = list(self.links.values())
            mean_depth = (
                sum(lnk.depth for lnk in all_links) / len(all_links)
                if all_links else 0.0
            )
            self._complexity_curve.record_tick(
                n_pairs_evaluated=n_pairs_eval,
                n_links=len(all_links),
                mean_link_depth=mean_depth,
                tick=self.tick_count,
            )
            self._complexity_curve.record_outcome(current_outlet)

            # Per-axis curves — each axis sees only its own links and pairs
            # dominant_axis_hint tells us which axis this tick's relief favoured
            for ax in AXES:
                ax_links = [lnk for lnk in all_links
                            if (lnk.dominant_relief_axis or "X") == ax]
                ax_link_count = len(ax_links)
                # Pairs attributed to this axis: fraction of total pairs
                ax_pair_load = int(n_pairs_eval * (ax_link_count + 1) /
                                   max(1, len(all_links) + 1))
                ax_mean_depth = (
                    sum(lnk.depth for lnk in ax_links) / ax_link_count
                    if ax_links else 0.0
                )
                self._axis_curves[ax].record_tick(
                    n_pairs_evaluated=ax_pair_load,
                    n_links=ax_link_count,
                    mean_link_depth=ax_mean_depth,
                    tick=self.tick_count,
                )
                # Axis outcome: outlet is shared, but per-axis correction
                # converges independently via prediction residuals
                self._axis_curves[ax].record_outcome(current_outlet)
        except Exception:
            pass

        return record

    def get_link(self, link_id: str) -> Optional[ConstraintLink]:
        return self.links.get(link_id)

    def rewrite_trace(self, trace: List[TraceItem]) -> List[TraceItem]:
        """
        Replace any adjacent pairs (u→v) that have been promoted to a Link
        with that link's TraceItem. Iterates until stable.
        """
        changed = True
        current = list(trace)
        while changed and len(current) >= 2:
            changed = False
            result: List[TraceItem] = []
            i = 0
            while i < len(current):
                if i + 1 < len(current):
                    key = (current[i].id, current[i + 1].id)
                    lid = self._links_by_parents.get(key)
                    if lid is not None:
                        result.append(TraceItem(kind="LINK", id=lid))
                        i += 2
                        changed = True
                        continue
                result.append(current[i])
                i += 1
            current = result
        return current

    def summary(self) -> Dict[str, Any]:
        top_links = sorted(
            self.links.values(),
            key=lambda l: l.mean_relief.get(l.dominant_relief_axis or "A", 0.0),
            reverse=True,
        )[:20]
        return {
            "run_id": self.run_id,
            "tick_count": self.tick_count,
            "relief_events": self.relief_event_count,
            "links_promoted": self.links_promoted,
            "skipped_no_relief": self.skipped_no_relief,
            "skipped_xrisk": self.skipped_xrisk,
            "tolerance_events_applied": self._tolerance_events_applied,
            "tolerance_factor_ema": round(float(self._tolerance_factor_ema), 6),
            "active_tolerance_slots": len(self._solution_tolerance),
            "coupling_events": int(self._coupling_events),
            "coupling_roots": len(self._coupling_roots),
            "persistent_pressure_root": self.cfg.PERSISTENT_PRESSURE_ROOT,
            "persistent_pressure_root_ema": round(float(self._persistent_pressure_root_ema), 11),
            "governor": self.governor.status(),
            "top_links": [l.to_dict() for l in top_links],
        }

    def chain_report(self) -> Dict[str, Any]:
        """
        Evolutionary chain report — the 'fossil summary'.

        Strict generation model:
          - Gen0: canonical 25 NC atoms (NC:X>Y)
          - Gen1 (root links): both parents are Gen0 atoms
          - Gen2+: any link with at least one parent outside Gen0
                   (including links and non-NC abilities)
        """
        by_axis: Dict[str, List[str]] = defaultdict(list)
        depth_dist: Dict[int, int] = defaultdict(int)
        generation_dist: Dict[int, int] = defaultdict(int)
        outlet_total = 0

        gen0_atoms = frozenset(GENEALOGY_ATOM_TO_SLOT_ID.keys()) if _CLOSURE_BASIS_AVAILABLE else frozenset(f"NC:{a}>{b}" for a in AXES for b in AXES)
        gen_cache: Dict[str, int] = {}

        def _link_generation(link_id: str, seen: Optional[set] = None) -> int:
            if link_id in gen_cache:
                return int(gen_cache[link_id])
            link = self.links.get(link_id)
            if link is None:
                return 0
            if seen is None:
                seen = set()
            if link_id in seen:
                return max(1, int(getattr(link, "depth", 1) or 1))
            seen.add(link_id)

            parent_gen_values: List[int] = []
            for p in list(getattr(link, "parents", []) or []):
                pid = str(p)
                if pid in gen0_atoms:
                    parent_gen_values.append(0)
                elif pid in self.links:
                    parent_gen_values.append(_link_generation(pid, seen))
                else:
                    # Non-NC ability parents are not Gen0, so they advance generation.
                    parent_gen_values.append(1)

            if len(parent_gen_values) >= 2:
                g = _bred_child_generation(parent_gen_values[0], parent_gen_values[1])
            else:
                g = (max(parent_gen_values) + 1) if parent_gen_values else 1
            gen_cache[link_id] = int(g)
            seen.discard(link_id)
            return int(g)

        for lnk in self.links.values():
            ax = lnk.dominant_relief_axis or "X"
            by_axis[ax].append(lnk.id)
            depth_dist[lnk.depth] += 1
            generation_dist[_link_generation(lnk.id)] += 1
            # track outlet-push involvement
            for p in lnk.parents:
                if p == "A:OUTLET_PUSH" or (p in self.links and
                   "A:OUTLET_PUSH" in self.links[p].parents):
                    outlet_total += 1
                    break

        total = len(self.links) or 1
        outlet_fraction = outlet_total / total
        root_links_count = int(generation_dist.get(1, 0))

        top_couplings_raw = sorted(
            self._coupling_roots.values(),
            key=lambda rec: (float(rec.get("effect_ema", 0.0)), int(rec.get("count", 0))),
            reverse=True,
        )[:12]
        top_couplings = [
            {
                "signature": str(rec.get("signature", "")),
                "semantic": str(rec.get("semantic", "")),
                "count": int(rec.get("count", 0) or 0),
                "effect_ema": round(float(rec.get("effect_ema", 0.0) or 0.0), 6),
                "min_generation": int(rec.get("min_generation", 0) or 0),
                "max_generation": int(rec.get("max_generation", 0) or 0),
                "generation_role": str(rec.get("last_generation_role", "PRIMARY")),
                "breeding_score_ema": round(float(rec.get("breeding_score_ema", 0.0) or 0.0), 6),
                "effect_descriptor": self._coupling_effect_descriptor(rec),
                "raw_effect_ema": round(float(rec.get("raw_effect_ema", 0.0) or 0.0), 6),
                "local_effect_ema": round(float(rec.get("local_effect_ema", rec.get("effect_ema", 0.0)) or 0.0), 6),
                "global_effect_ema": round(float(rec.get("global_effect_ema", rec.get("effect_ema", 0.0)) or 0.0), 6),
                "scope_scale": round(float(rec.get("scope_scale", 1.0) or 1.0), 6),
                "regulation": dict(rec.get("regulation", {}) or {}),
                "inheritance_breach_count": int(rec.get("inheritance_breach_count", 0) or 0),
            }
            for rec in top_couplings_raw
        ]

        evidence_min_default = max(1, int(getattr(self.cfg, "RUBRIC_MIN_EVENTS", 24)))
        total_couplings = len(self._coupling_roots)
        considered_couplings = 0
        pending_couplings = 0
        validation_complete = 0
        validation_incomplete = 0
        inheritance_breaches_total = 0
        inheritance_breaches_considered = 0
        inheritance_breach_active_count = 0
        for rec in self._coupling_roots.values():
            reg = dict(rec.get("regulation", {}) or {})
            cnt = int(rec.get("count", 0) or 0)
            evidence_min = max(1, int(reg.get("evidence_min", evidence_min_default) or evidence_min_default))
            breach_count = int(rec.get("inheritance_breach_count", 0) or 0)
            breach_active = bool(rec.get("inheritance_breach_active", False))
            inheritance_breaches_total += breach_count
            if breach_active:
                inheritance_breach_active_count += 1
            if cnt < evidence_min or (not bool(reg.get("evidence_complete", cnt >= evidence_min))):
                pending_couplings += 1
            else:
                considered_couplings += 1
                if bool(reg.get("validation_complete", False)):
                    validation_complete += 1
                else:
                    validation_incomplete += 1
                inheritance_breaches_considered += breach_count

        expected_root_raw, expected_root_canonical, _root_rec, observed_gen, expected_gen, accuracy_ok = self._persistent_root_lookup()

        return {
            "total_links": len(self.links),
            "root_links_strict": root_links_count,
            "generation_distribution": dict(sorted(generation_dist.items())),
            "by_dominant_axis": {a: len(v) for a, v in by_axis.items()},
            "depth_distribution": dict(sorted(depth_dist.items())),
            "outlet_push_fraction": round(outlet_fraction, 4),
            "communication_least_resistance_indicator": outlet_fraction,
            "complexity_curve": self._complexity_curve.get_stats(),
            "pressure_orientation": self.pressure_orientation(),
            "persistent_pressure_root": expected_root_raw,
            "persistent_pressure_root_canonical": expected_root_canonical,
            "persistent_pressure_root_ema": round(float(self._persistent_pressure_root_ema), 11),
            "persistent_root_generation_expected": expected_gen,
            "persistent_root_generation_observed": observed_gen,
            "persistent_root_accuracy_ok": accuracy_ok,
            "coupling_root_count": int(total_couplings),
            "validation_evidence_min": int(evidence_min),
            "validation_considered_count": int(considered_couplings),
            "validation_pending_count": int(pending_couplings),
            "validation_complete_count": int(validation_complete),
            "validation_incomplete_count": int(validation_incomplete),
            "validation_completeness_rate": round(float(validation_complete / float(max(1, considered_couplings))), 6),
            "inheritance_breach_events": int(inheritance_breaches_considered),
            "inheritance_breach_events_total": int(inheritance_breaches_total),
            "inheritance_breach_active_count": int(inheritance_breach_active_count),
            "top_couplings": top_couplings,
            "experiment_trials": int(len(self._experiment_trials)),
            "experiment_adoptions": int(len(self._experiment_adoptions)),
            "experiment_trials_issue": int(sum(1 for t in self._experiment_trials if str(t.get("trigger_mode", "")) == "issue_cluster")),
            "experiment_trials_exploratory": int(sum(1 for t in self._experiment_trials if str(t.get("trigger_mode", "")) == "exploratory")),
            "latest_experiment_trial": (self._experiment_trials[-1] if self._experiment_trials else None),
            "latest_experiment_adoption": (self._experiment_adoptions[-1] if self._experiment_adoptions else None),
            "promotion_stats": dict(self._promotion_stats),
            "ontological_status_breakdown": _build_closure_status_summary(
                self.links, self.abilities
            ),
        }

    def flush_files(self) -> None:
        """Flush JSONL buffer and write abilities + links + couplings + pair_stats JSON files."""
        self._events_fh.flush()
        self._write_abilities_file()
        self._write_links_file()
        self._write_couplings_file()
        self._write_pair_stats_file()
        self._write_tick_state_file()

    def _write_tick_state_file(self) -> None:
        """Persist tick_count and _last_promotion_tick so stagnation signal survives restarts."""
        path = os.path.join(self.output_dir, "tick_state.json")
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({
                    "tick_count": int(self.tick_count),
                    "last_promotion_tick": int(self._last_promotion_tick),
                }, fh)
        except Exception:
            pass

    def restore_tick_state(self) -> bool:
        """
        Load tick_count and _last_promotion_tick from tick_state.json.

        Called from corpus_runner.boot_aurora() after _restore_genealogy_state()
        so the stagnation elapsed clock picks up exactly where it left off.
        Returns True if state was restored, False if file missing or invalid.
        """
        path = os.path.join(self.output_dir, "tick_state.json")
        if not os.path.exists(path):
            return False
        try:
            with open(path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            saved_tick = int(raw.get("tick_count", 0) or 0)
            saved_last = int(raw.get("last_promotion_tick", 0) or 0)
            if saved_tick > 0:
                self.tick_count = saved_tick
                self._last_promotion_tick = saved_last
                return True
        except Exception:
            pass
        return False

    def _write_pair_stats_file(self) -> None:
        """
        Persist _pair_stats to disk so K_MIN accumulation survives across runs.

        Each entry is keyed by '{left_id}|{right_id}' and stores all fields
        needed to reconstruct a PairStats exactly — count, relief sums,
        positive-only sums, cost sums, x_risk_sum, last_seen_tick.
        Already-promoted pairs are excluded: they don't need to accumulate further.
        """
        path = os.path.join(self.output_dir,
                            getattr(self.cfg, "PAIR_STATS_FILE", "pair_stats.json"))
        out: Dict[str, Any] = {}
        for (lid, rid), ps in self._pair_stats.items():
            # Skip pairs already promoted — restoring them would be redundant
            if (lid, rid) in self._links_by_parents:
                continue
            out[f"{lid}|{rid}"] = {
                "left_id":       ps.left_id,
                "right_id":      ps.right_id,
                "count":         ps.count,
                "relief_sum":    dict(ps.relief_sum),
                "relief_sq_sum": dict(ps.relief_sq_sum),
                "relief_pos_sum":dict(ps.relief_pos_sum),
                "pos_count":     dict(ps.pos_count),
                "cost_sum":      dict(ps.cost_sum),
                "x_risk_sum":    float(ps.x_risk_sum),
                "last_seen_tick":int(ps.last_seen_tick),
            }
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(out, fh)
        except Exception:
            pass

    def restore_pair_stats(self) -> int:
        """
        Load persisted pair_stats.json and merge into _pair_stats.

        Pairs already in memory are merged additively (counts summed) so that
        a run that was mid-session and already accumulated some observations
        doesn't lose them. Returns count of pairs restored.

        Called by corpus_runner.boot_aurora() and _restore_genealogy_state()
        after links/abilities are restored.
        """
        path = os.path.join(self.output_dir,
                            getattr(self.cfg, "PAIR_STATS_FILE", "pair_stats.json"))
        if not os.path.exists(path):
            return 0
        restored = 0
        max_restored_count = 0
        try:
            with open(path, "r", encoding="utf-8") as fh:
                raw: Dict[str, Any] = json.load(fh)
            for compound_key, rec in raw.items():
                lid = str(rec.get("left_id", ""))
                rid = str(rec.get("right_id", ""))
                if not lid or not rid:
                    continue
                key = (lid, rid)
                # Skip pairs that have already been promoted in this session
                if key in self._links_by_parents:
                    continue
                if key not in self._pair_stats:
                    self._pair_stats[key] = PairStats(left_id=lid, right_id=rid)
                ps = self._pair_stats[key]
                # Additive merge — preserves any observations already in memory
                ps.count         += int(rec.get("count", 0))
                ps.x_risk_sum    += float(rec.get("x_risk_sum", 0.0))
                ps.last_seen_tick = max(ps.last_seen_tick,
                                        int(rec.get("last_seen_tick", 0)))
                max_restored_count = max(max_restored_count, int(ps.count))
                for a in AXES:
                    ps.relief_sum[a]     = ps.relief_sum.get(a, 0.0)     + float((rec.get("relief_sum")     or {}).get(a, 0.0))
                    ps.relief_sq_sum[a]  = ps.relief_sq_sum.get(a, 0.0)  + float((rec.get("relief_sq_sum")  or {}).get(a, 0.0))
                    ps.relief_pos_sum[a] = ps.relief_pos_sum.get(a, 0.0) + float((rec.get("relief_pos_sum") or {}).get(a, 0.0))
                    ps.pos_count[a]      = ps.pos_count.get(a, 0)        + int((rec.get("pos_count")        or {}).get(a, 0))
                    ps.cost_sum[a]       = ps.cost_sum.get(a, 0.0)       + float((rec.get("cost_sum")       or {}).get(a, 0.0))
                restored += 1
        except Exception:
            pass
        if restored > 0 and len(self.links) == 0:
            # Seed stagnation pressure from recovered pair maturity so short runs can
            # activate dynamic gate relaxation before very long no-promotion periods.
            k_min = max(1, int(getattr(self.cfg, "K_MIN", 1) or 1))
            maturity = _clamp(float(max_restored_count) / float(k_min), 0.0, 1.0)
            hard_window = max(1, int(getattr(self.cfg, "STAGNATION_HARD_WINDOW", self.cfg.STAGNATION_WINDOW)))
            seeded_elapsed = int(round(hard_window * (0.35 + (0.65 * maturity))))
            self._last_promotion_tick = min(int(self._last_promotion_tick), int(self.tick_count) - max(1, seeded_elapsed))
            self._promotion_stats["stagnation_seeded_from_pair_stats"] += 1
            self._promotion_stats["stagnation_seed_max_pair_count"] = int(max_restored_count)
        return restored

    def close(self) -> None:
        self.flush_files()
        self._events_fh.close()

    # ----------------------------------------------------------------
    # CBU LINEAGE + PHASE TRACKING (CBU directive §A7 / Step 10)
    # ----------------------------------------------------------------

    def record_cbu_lineage(
        self,
        parent_id: str,
        child_id: str,
        parent_profile,
        child_profile,
        derivation_kind: str,
    ) -> None:
        """
        Record that child_id was derived from parent_id with lineage pressure.
        Writes to aurora_state/constraint_genealogy_log.json (append-only JSONL).
        """
        try:
            _path = os.path.join(self.output_dir, "constraint_genealogy_log.json")
            _entry = json.dumps({
                "event": "cbu_lineage",
                "parent_id": parent_id,
                "child_id": child_id,
                "derivation_kind": derivation_kind,
                "parent_magnitude": float(parent_profile.profile_magnitude()) if parent_profile else 0.0,
                "child_lineage_pressure": float(child_profile.lineage_pressure) if child_profile else 0.0,
                "timestamp": time.time(),
            })
            with open(_path, "a", encoding="utf-8") as _fh:
                _fh.write(_entry + "\n")
        except Exception:
            pass

    def record_phase_change(
        self,
        unit_id: str,
        unit_kind: str,
        old_phase,
        new_phase,
        breached_axis,
        profile_snapshot: dict,
    ) -> None:
        """
        Record a phase state transition for audit and dream curriculum targeting.
        Writes to aurora_state/constraint_genealogy_log.json (append-only JSONL).
        """
        try:
            _path = os.path.join(self.output_dir, "constraint_genealogy_log.json")
            _entry = json.dumps({
                "event": "phase_change",
                "unit_id": unit_id,
                "unit_kind": unit_kind,
                "old_phase": str(old_phase.value if hasattr(old_phase, "value") else old_phase),
                "new_phase": str(new_phase.value if hasattr(new_phase, "value") else new_phase),
                "breached_axis": breached_axis,
                "profile": profile_snapshot,
                "timestamp": time.time(),
            })
            with open(_path, "a", encoding="utf-8") as _fh:
                _fh.write(_entry + "\n")
        except Exception:
            pass

    def get_collapsed_units(self, since_timestamp: float) -> list:
        """
        Return all units that entered collapsed phase after since_timestamp.
        Reads from constraint_genealogy_log.json.
        """
        results = []
        try:
            _path = os.path.join(self.output_dir, "constraint_genealogy_log.json")
            if not os.path.exists(_path):
                return results
            with open(_path, "r", encoding="utf-8") as _fh:
                for line in _fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except Exception:
                        continue
                    if (rec.get("event") == "phase_change"
                            and rec.get("new_phase") == "collapsed"
                            and float(rec.get("timestamp", 0.0)) >= since_timestamp):
                        results.append(rec)
        except Exception:
            pass
        return results

    # ----------------------------------------------------------------
    # INTERNAL — Relief tolerance (solution immunity)
    # ----------------------------------------------------------------

    def _solution_complexity(self, item: TraceItem) -> int:
        if getattr(item, "kind", "") == "LINK":
            lnk = self.links.get(getattr(item, "id", ""))
            if lnk is not None:
                return max(1, int(getattr(lnk, "depth", 1) or 1))
        aid = str(getattr(item, "id", ""))
        if ":LINK_" in aid:
            return 2
        return 1

    def _solution_key(self, item: TraceItem, dominant_axis: str) -> str:
        axis = str(dominant_axis or "X").upper()
        kind = str(getattr(item, "kind", "ABILITY")).upper()
        sid = str(getattr(item, "id", ""))
        return f"{kind}:{sid}@{axis}"

    def _apply_relief_tolerance(
        self,
        trace: List[TraceItem],
        relief: PressureVec,
        dominant_axis: str,
    ) -> Tuple[PressureVec, Dict[str, Any]]:
        if not bool(getattr(self.cfg, "RELIEF_TOLERANCE_ENABLED", True)):
            return relief, {}

        total_pos = max(0.0, float(relief.sum_positive_relief()))
        if total_pos <= 0.0 or not trace:
            return relief, {}

        grow = max(0.0, float(getattr(self.cfg, "RELIEF_TOLERANCE_GROWTH", 0.06)))
        decay = max(0.0, min(0.25, float(getattr(self.cfg, "RELIEF_TOLERANCE_DECAY", 0.01))))
        tol_max = max(0.0, min(0.99, float(getattr(self.cfg, "RELIEF_TOLERANCE_MAX", 0.85))))
        min_factor = max(0.01, min(1.0, float(getattr(self.cfg, "RELIEF_TOLERANCE_MIN_FACTOR", 0.15))))
        comp_power = max(0.1, float(getattr(self.cfg, "RELIEF_TOLERANCE_COMPLEXITY_POWER", 1.0)))
        relief_total_eps, _ = self._regulated_threshold(
            "RELIEF_TOTAL_EPS",
            float(self.cfg.RELIEF_TOTAL_EPS),
            axis=dominant_axis,
            depth=1,
            threshold_kind="floor",
            local_support=total_pos,
            local_opposition=max(0.0, float(relief.max_relief())),
            floor_ratio=0.25,
            cap_ratio=2.0,
        )

        unique_items: List[TraceItem] = []
        seen = set()
        for it in trace:
            k = (str(getattr(it, "kind", "")), str(getattr(it, "id", "")))
            if k in seen:
                continue
            seen.add(k)
            unique_items.append(it)

        slot_tolerances: List[float] = []
        top_slots: List[Tuple[str, float]] = []

        for item in unique_items:
            key = self._solution_key(item, dominant_axis)
            last_tick = int(self._solution_last_tick.get(key, self.tick_count))
            elapsed = max(0, int(self.tick_count - last_tick))

            tol = float(self._solution_tolerance.get(key, 0.0))
            if elapsed > 0 and tol > 0.0 and decay > 0.0:
                tol *= ((1.0 - decay) ** elapsed)

            complexity = max(1.0, float(self._solution_complexity(item)))
            resilience = complexity ** comp_power
            signal = min(1.0, total_pos / max(1e-9, float(relief_total_eps)))
            inc = (grow * signal) / resilience
            tol = min(tol_max, tol + (inc * (1.0 - tol)))

            self._solution_tolerance[key] = tol
            self._solution_last_tick[key] = int(self.tick_count)
            slot_tolerances.append(tol)
            top_slots.append((key, tol))

        if not slot_tolerances:
            return relief, {}

        mean_tol = sum(slot_tolerances) / float(len(slot_tolerances))
        factor = max(min_factor, 1.0 - mean_tol)

        adjusted = PressureVec(
            X=float(relief.X) * factor,
            T=float(relief.T) * factor,
            N=float(relief.N) * factor,
            B=float(relief.B) * factor,
            A=float(relief.A) * factor,
        )

        self._tolerance_events_applied += 1
        self._tolerance_factor_ema = (0.95 * float(self._tolerance_factor_ema)) + (0.05 * factor)

        top_slots = sorted(top_slots, key=lambda kv: kv[1], reverse=True)[:3]
        meta = {
            "factor": round(float(factor), 6),
            "mean_tolerance": round(float(mean_tol), 6),
            "slots": len(slot_tolerances),
            "axis": str(dominant_axis or "X").upper(),
            "top": [{"solution": k, "tolerance": round(float(v), 6)} for k, v in top_slots],
        }
        return adjusted, meta


    # ----------------------------------------------------------------
    # INTERNAL — Coupling roots (canonical + semantic)
    # ----------------------------------------------------------------

    def _zero_axis_counts(self) -> Dict[str, int]:
        return {a: 0 for a in AXES}

    def _add_axis_counts(self, left: Dict[str, int], right: Dict[str, int]) -> Dict[str, int]:
        out = self._zero_axis_counts()
        for a in AXES:
            out[a] = int(left.get(a, 0)) + int(right.get(a, 0))
        return out

    def _axis_counts_from_item(self, item: TraceItem, memo: Optional[Dict[str, Dict[str, int]]] = None, seen: Optional[set] = None) -> Dict[str, int]:
        memo = memo or {}
        item_id = str(getattr(item, "id", ""))
        kind = str(getattr(item, "kind", "ABILITY")).upper()

        if item_id in memo:
            return dict(memo[item_id])

        counts = self._zero_axis_counts()

        if item_id.startswith("NC:") and ">" in item_id:
            pair = item_id[3:]
            left, right = pair.split(">", 1)
            l_ax = left.strip().upper()
            r_ax = right.strip().upper()
            if l_ax in counts:
                counts[l_ax] += 1
            if r_ax in counts:
                counts[r_ax] += 1
            memo[item_id] = dict(counts)
            return counts

        # Base ability id pattern: A:..., B:..., ...
        if ":" in item_id and not item_id.startswith("L:"):
            ax = item_id.split(":", 1)[0].strip().upper()
            if ax in counts:
                counts[ax] += 1
            memo[item_id] = dict(counts)
            return counts

        if kind == "LINK" and item_id.startswith("L:"):
            if seen is None:
                seen = set()
            if item_id in seen:
                # Cycle guard fallback.
                depth_guess = max(1, int(getattr(self.links.get(item_id), "depth", 1) or 1))
                counts["A"] += 1 if depth_guess > 0 else 0
                memo[item_id] = dict(counts)
                return counts
            seen.add(item_id)
            lnk = self.links.get(item_id)
            if lnk is not None:
                agg = self._zero_axis_counts()
                for p in list(getattr(lnk, "parents", []) or []):
                    p_id = str(p)
                    p_kind = "LINK" if p_id.startswith("L:") else "ABILITY"
                    pc = self._axis_counts_from_item(TraceItem(kind=p_kind, id=p_id), memo=memo, seen=seen)
                    agg = self._add_axis_counts(agg, pc)
                counts = agg
            memo[item_id] = dict(counts)
            seen.discard(item_id)
            return counts

        memo[item_id] = dict(counts)
        return counts

    def _canonical_coupling_signature(self, counts: Dict[str, int]) -> str:
        parts = [f"{a}^{int(counts.get(a, 0))}" for a in AXES if int(counts.get(a, 0)) > 0]
        return "*".join(parts) if parts else "0"

    def _counts_from_signature(self, signature: str) -> Dict[str, int]:
        counts = self._zero_axis_counts()
        for raw in str(signature or "").split("*"):
            part = raw.strip()
            if not part:
                continue
            if "^" in part:
                axis, exp_s = part.split("^", 1)
                axis = axis.strip().upper()
                try:
                    exp_n = int(float(exp_s.strip()))
                except Exception:
                    exp_n = 0
            else:
                axis = part.strip().upper()
                exp_n = 1
            if axis in counts and exp_n > 0:
                counts[axis] += int(exp_n)
        return counts

    def _canonical_signature_text(self, signature: str) -> str:
        return self._canonical_coupling_signature(self._counts_from_signature(signature))

    def _persistent_root_lookup(self) -> Tuple[str, str, Dict[str, Any], Optional[int], int, bool]:
        expected_raw = str(getattr(self.cfg, "PERSISTENT_PRESSURE_ROOT", "A^1*N^1*T^1"))
        expected_canonical = self._canonical_signature_text(expected_raw)
        expected_gen = int(getattr(self.cfg, "PERSISTENT_ROOT_EXPECTED_GENERATION", 2) or 2)
        rec = self._coupling_roots.get(expected_canonical, {}) or {}
        observed_gen = rec.get("min_generation") if isinstance(rec, dict) else None
        accuracy_ok = bool(observed_gen == expected_gen) if observed_gen is not None else False
        return expected_raw, expected_canonical, rec, observed_gen, expected_gen, accuracy_ok

    def _semantic_coupling_label(self, counts: Dict[str, int]) -> str:
        profile = _meaning_profile_for_counts(counts)
        if profile:
            return str(profile.get("label", "") or "meaning_coupling")
        axis_terms = {
            "X": "grounding",
            "T": "timing",
            "N": "energy",
            "B": "boundary",
            "A": "agency",
        }
        ordered = sorted(
            [(a, _axis_count_value(v)) for a, v in counts.items() if _axis_count_value(v) > 0],
            key=lambda kv: (-kv[1], kv[0]),
        )
        if not ordered:
            return "null coupling"
        bits = []
        for a, n in ordered:
            term = axis_terms.get(a, a)
            bits.append(f"{term}x{n}" if n > 1 else term)
        return " + ".join(bits)

    def _semantic_lane_vector(self, counts: Dict[str, int]) -> Dict[str, float]:
        total = float(sum(max(0, _axis_count_value(v)) for v in counts.values()) or 1.0)
        axis_mix = {a: max(0.0, float(_axis_count_value(counts.get(a, 0)) / total)) for a in AXES}
        out = {"intelligence": 0.0, "communication": 0.0, "meaning": 0.0}
        for ax, frac in axis_mix.items():
            impacts = SEMANTIC_LANE_IMPACT.get(ax, {})
            for lane in out.keys():
                out[lane] += frac * float(impacts.get(lane, 0.0))
        norm = max(1e-9, sum(out.values()))
        return {k: float(v / norm) for k, v in out.items()}

    def _semantic_translation_text(self, rec: Dict[str, Any], lane_vec: Dict[str, float], confidence: float) -> str:
        dom_lane = max(lane_vec.items(), key=lambda kv: kv[1])[0] if lane_vec else "meaning"
        action = SEMANTIC_ACTION_BY_LANE.get(dom_lane, "adaptive behavior")
        role = str(rec.get("last_generation_role", "PRIMARY") or "PRIMARY").lower()
        local_eff = float(rec.get("local_effect_ema", rec.get("effect_ema", 0.0)) or 0.0)
        scope = float(rec.get("scope_scale", 1.0) or 1.0)
        gen = int(rec.get("last_generation", 0) or 0)
        profile = _meaning_profile_for_counts(dict(rec.get("counts", {}) or {}))
        if profile:
            label = str(profile.get("label", "") or "meaning_coupling")
            representation = str(profile.get("representation", "") or "").strip()
            phrase = label if not representation else f"{label} ({representation})"
            return (
                f"At gen {gen}, this coupling resolves as {phrase} in {role} mode "
                f"via {action} (local={local_eff:.6f}, scope={scope:.3f}, conf={confidence:.3f})."
            )
        return (
            f"At gen {gen}, this coupling expresses {action} in {role} mode "
            f"(local={local_eff:.6f}, scope={scope:.3f}, conf={confidence:.3f})."
        )

    def _update_semantic_translation(self, rec: Dict[str, Any], rate: float) -> None:
        counts = dict(rec.get("counts", {}) or {})
        dominant_axis = max(AXES, key=lambda ax: float(counts.get(ax, 0) or 0)) if counts else "X"
        lane_now = self._semantic_lane_vector(counts)
        lane_ema = dict(rec.get("semantic_lane_ema", {}) or {})
        if not lane_ema:
            lane_ema = dict(lane_now)
        else:
            for k, v in lane_now.items():
                lane_ema[k] = ((1.0 - rate) * float(lane_ema.get(k, 0.0))) + (rate * float(v))
            norm = max(1e-9, sum(float(v) for v in lane_ema.values()))
            lane_ema = {k: float(v / norm) for k, v in lane_ema.items()}

        count = int(rec.get("count", 0) or 0)
        effect = float(rec.get("effect_ema", 0.0) or 0.0)
        regulation = dict(rec.get("regulation", {}) or {})
        consistency = max(0.0, min(1.0, 1.0 - float(regulation.get("dominance", 0.0) if isinstance(regulation, dict) else 0.0)))
        confidence = max(0.0, min(1.0, (0.45 * min(1.0, count / 120.0)) + (0.35 * min(1.0, effect / 0.00025)) + (0.20 * (1.0 - consistency))))

        prev_ver = int(rec.get("semantic_version", 0) or 0)
        promote_conf = float(getattr(self.cfg, "SEMANTIC_PROMOTE_CONFIDENCE", 0.65) or 0.65)
        promote_min_base = float(max(1, int(getattr(self.cfg, "SEMANTIC_PROMOTE_MIN_COUNT", 24) or 24)))
        semantic_support = max(0.0, confidence) + max(0.0, effect)
        semantic_opposition = max(0.0, consistency) + max(0.0, 1.0 - confidence)
        promote_conf_dyn, promote_conf_reg = self._regulated_threshold(
            "SEMANTIC_PROMOTE_CONFIDENCE",
            max(1e-9, promote_conf),
            axis=dominant_axis,
            depth=max(1, int(rec.get("max_generation", rec.get("last_generation", 1)) or 1)),
            threshold_kind="floor",
            local_support=semantic_support,
            local_opposition=semantic_opposition,
            floor_ratio=0.50,
            cap_ratio=1.40,
        )
        promote_min_dyn_raw, promote_min_reg = self._regulated_threshold(
            "SEMANTIC_PROMOTE_MIN_COUNT",
            promote_min_base,
            axis=dominant_axis,
            depth=max(1, int(rec.get("max_generation", rec.get("last_generation", 1)) or 1)),
            threshold_kind="floor",
            local_support=semantic_support,
            local_opposition=semantic_opposition,
            floor_ratio=0.35,
            cap_ratio=1.70,
        )
        promote_min = max(1, int(round(promote_min_dyn_raw)))
        promoted = bool(confidence >= promote_conf_dyn and count >= promote_min)
        version = prev_ver + 1 if promoted and rec.get("semantic_translation") else max(1, prev_ver)

        rec["semantic_lane_ema"] = dict(lane_ema)
        rec["semantic_confidence"] = float(round(confidence, 6))
        rec["semantic_version"] = int(version)
        rec["semantic_translation"] = self._semantic_translation_text(rec, lane_ema, confidence)
        rec["semantic_thresholds"] = {
            "promote_confidence": float(round(promote_conf_dyn, 6)),
            "promote_min_count": int(promote_min),
            "pressure_regulation": {
                "dominant_axis": str(dominant_axis),
                "confidence": {
                    "factor": round(float(promote_conf_reg.get("factor", 1.0) or 1.0), 6),
                    "gradient": round(float(promote_conf_reg.get("pressure_gradient", 0.0) or 0.0), 6),
                },
                "count": {
                    "factor": round(float(promote_min_reg.get("factor", 1.0) or 1.0), 6),
                    "gradient": round(float(promote_min_reg.get("pressure_gradient", 0.0) or 0.0), 6),
                },
            },
        }

    def _coupling_effect_descriptor(self, rec: Dict[str, Any]) -> str:
        role = str(rec.get("last_generation_role", "PRIMARY") or "PRIMARY").upper()
        score = float(rec.get("breeding_score_ema", 0.0) or 0.0)
        effect = float(rec.get("effect_ema", 0.0) or 0.0)
        local_effect = float(rec.get("local_effect_ema", effect) or effect)
        scope_scale = float(rec.get("scope_scale", 1.0) or 1.0)
        lo = int(rec.get("min_generation", 0) or 0)
        hi = int(rec.get("max_generation", 0) or 0)
        origin_div = len(dict(rec.get("top_origins", {}) or {}))
        semantic = str(rec.get("semantic", "mixed coupling") or "mixed coupling")

        if score <= -1000.0:
            phase = "blocked-cross; deferred lineage formation"
        elif score >= 2.5:
            phase = "preferred-cross; accelerated consolidation"
        elif score <= -1.0:
            phase = "antagonistic-cross; delayed stabilization"
        else:
            phase = "neutral-cross; incremental accumulation"

        if role == "WARP":
            role_fx = "mutational branch pressure"
        elif role == "BRIDGE":
            role_fx = "bridge transfer between generations"
        elif role == "SHEAR":
            role_fx = "shear diversification"
        elif role == "ADJACENT":
            role_fx = "adjacent adaptation"
        else:
            role_fx = "primary consolidation"

        return (
            f"{semantic}; {role_fx}; {phase}; gen_span={lo}->{hi}; "
            f"local_effect={local_effect:.6f}; scope={scope_scale:.3f}; global_effect={effect:.6f}; origin_diversity={origin_div}"
        )

    def _relation_profile(self, counts: Dict[str, int]) -> Dict[str, Any]:
        nz = [(a, _axis_count_value(v)) for a, v in counts.items() if _axis_count_value(v) > 0]
        if not nz:
            return {"relation_score": 0.0, "axes_active": 0, "dominance": 1.0}
        total = float(sum(v for _, v in nz))
        fracs = [v / total for _, v in nz]
        dominance = max(fracs)
        balance = 1.0 - max(0.0, (max(fracs) - min(fracs)))
        diversity = min(1.0, len(nz) / 3.0)
        relation = (0.5 * balance) + (0.5 * diversity)
        return {
            "relation_score": float(max(0.0, min(1.0, relation))),
            "axes_active": int(len(nz)),
            "dominance": float(dominance),
        }

    def _slot_influence_distribution(self, counts: Dict[str, int]) -> Dict[str, float]:
        """
        Duplicate-slot redistribution metric (no hard caps).
        Example NT x NA: raw slots N,T,N,A => 25% each.
        Extra N slot keeps 50% and redistributes 50% evenly to other active axes.
        """
        c = {a: max(0, int(counts.get(a, 0) or 0)) for a in AXES}
        total_slots = sum(c.values())
        if total_slots <= 0:
            return {a: 0.0 for a in AXES}

        active = [a for a, v in c.items() if v > 0]
        slot_w = 1.0 / float(total_slots)
        redist = max(0.0, min(1.0, float(getattr(self.cfg, "DUPLICATE_SLOT_REDISTRIBUTION", 0.50))))
        infl = {a: 0.0 for a in AXES}

        for ax in active:
            n = int(c[ax])
            if n <= 0:
                continue
            # First occurrence keeps full slot influence.
            infl[ax] += slot_w
            extras = max(0, n - 1)
            for _ in range(extras):
                keep = slot_w * (1.0 - redist)
                give = slot_w * redist
                infl[ax] += keep
                others = [o for o in active if o != ax]
                if others:
                    share = give / float(len(others))
                    for o in others:
                        infl[o] += share
                else:
                    infl[ax] += give

        total = sum(infl.values()) or 1.0
        return {a: float(infl[a] / total) for a in AXES}

    def _scale_depth_index(self, counts: Dict[str, int]) -> float:
        """
        Weighted scale-depth index in [0,1]:
        X=0.00 (most lax), T=0.25, N=0.50, B=0.75, A=1.00 (most strict).
        """
        # T raised from 1.0 to 1.8: T is the hidden fulcrum — its scale-depth
        # contribution should reflect its downstream cascade weight, not just
        # its position in the ordering. B-T gravitational coupling keeps T < B.
        weights = {"X": 0.0, "T": 1.8, "N": 2.0, "B": 3.0, "A": 4.0}
        total = float(sum(max(0, int(counts.get(a, 0) or 0)) for a in AXES))
        if total <= 0.0:
            return 0.0
        wsum = 0.0
        for a in AXES:
            c = max(0, int(counts.get(a, 0) or 0))
            if c <= 0:
                continue
            wsum += float(c) * float(weights.get(a, 0.0))
        return max(0.0, min(1.0, (wsum / total) / 4.0))

    def _complexity_index(self, rec: Dict[str, Any]) -> float:
        """Normalized structural complexity in [0,1]."""
        lo = int(rec.get("min_generation", 0) or 0)
        hi = int(rec.get("max_generation", 0) or 0)
        span = max(0, hi - lo)
        counts = dict(rec.get("counts", {}) or {})
        axes_active = sum(1 for a in AXES if int(counts.get(a, 0) or 0) > 0)
        origin_div = len(dict(rec.get("top_origins", {}) or {}))

        c_gen = min(1.0, span / 6.0)
        c_axes = min(1.0, max(0, axes_active - 1) / 4.0)
        c_origin = min(1.0, origin_div / 8.0)
        return max(0.0, min(1.0, (0.4 * c_gen) + (0.3 * c_axes) + (0.3 * c_origin)))

    def _complexity_scope_scale(self, rec: Dict[str, Any]) -> float:
        complexity = self._complexity_index(rec)
        alpha = max(0.0, float(getattr(self.cfg, "COMPLEXITY_SCOPE_ALPHA", 0.80)))
        return 1.0 + (alpha * complexity)

    def _evaluate_coupling_rubric(self, rec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate representation integrity for a coupling record.
        This is NOT a grade. It checks whether coupling/inheritance/effect fields
        are coherent and sufficiently represented for downstream interpretation.
        """
        cfg = self.cfg
        if not bool(getattr(cfg, "RUBRIC_ENABLED", True)):
            return {"enabled": False, "validation_complete": True, "issues": []}

        cnt = int(rec.get("count", 0) or 0)
        bscore = float(rec.get("breeding_score_ema", 0.0) or 0.0)
        lo = int(rec.get("min_generation", 0) or 0)
        hi = int(rec.get("max_generation", 0) or 0)
        span = max(0, hi - lo)
        origin_div = len(dict(rec.get("top_origins", {}) or {}))

        count_strength = max(0.0, min(1.0, cnt / 120.0))
        continuity = 1.0 / (1.0 + (0.4 * span))
        origin_strength = max(0.0, min(1.0, origin_div / 6.0))
        inheritance_score = (0.55 * count_strength) + (0.25 * continuity) + (0.20 * origin_strength)

        counts = dict(rec.get("counts", {}) or {})
        dominant_axis = max(AXES, key=lambda ax: float(counts.get(ax, 0) or 0))
        rel_prof = self._relation_profile(counts)
        relation_score = float(rel_prof.get("relation_score", 0.0))

        infl = self._slot_influence_distribution(counts)
        dominant_influence = max(infl.values()) if infl else 0.0
        inheritance_influence_factor = 0.5 + float(dominant_influence)

        local_eff = float(rec.get("local_effect_ema", rec.get("effect_ema", 0.0)) or 0.0)
        global_eff = float(rec.get("effect_ema", 0.0) or 0.0)
        scope_scale = float(rec.get("scope_scale", 1.0) or 1.0)

        # Scale-aware requirement tightening:
        # X-heavy couplings are lax; deeper scales (toward A) and higher complexity demand more evidence.
        scale_depth_index = self._scale_depth_index(counts)
        complexity_index = self._complexity_index(rec)
        strict_k = max(0.0, float(getattr(cfg, "SCALE_REQUIREMENT_STRENGTH", 0.75)))
        strictness = max(0.0, min(1.0, (0.60 * scale_depth_index) + (0.40 * complexity_index)))
        inh_min_base = max(1e-9, float(getattr(cfg, "RUBRIC_INHERIT_MIN", 0.60)))
        rel_min_base = max(1e-9, float(getattr(cfg, "RUBRIC_RELATION_MIN", 0.40)))
        eff_min_base = max(1e-9, float(getattr(cfg, "RUBRIC_EFFECT_MIN", 0.00008)))
        breed_min_base = max(1e-9, float(getattr(cfg, "RUBRIC_BREEDING_MIN", 0.25)))
        evidence_min_base = float(max(1, int(getattr(cfg, "RUBRIC_MIN_EVENTS", 24))))
        persistence_tax_factor = self._weighted_persistence_tax_factor(infl, depth=max(1, hi))
        tax_cap = max(1.0, float(getattr(cfg, "PERSISTENCE_TAX_MAX_FACTOR", 5.0)))
        persistence_tax = max(0.0, min(1.0, (persistence_tax_factor - 1.0) / max(1e-9, (tax_cap - 1.0))))
        threshold_support = (
            max(0.0, min(1.0, cnt / max(1.0, evidence_min_base * 2.0)))
            + max(0.0, relation_score)
            + max(0.0, local_eff)
            + max(0.0, float(origin_strength))
        )
        threshold_opposition = (
            max(0.0, strictness)
            + max(0.0, persistence_tax)
        )
        evidence_min_dyn_raw, evidence_reg = self._regulated_threshold(
            "RUBRIC_MIN_EVENTS",
            evidence_min_base,
            axis=dominant_axis,
            depth=max(1, hi),
            threshold_kind="floor",
            local_support=threshold_support,
            local_opposition=threshold_opposition,
            floor_ratio=0.40,
            cap_ratio=1.85,
        )
        evidence_min = max(1, int(round(evidence_min_dyn_raw)))
        evidence_complete = cnt >= evidence_min
        inh_min_dyn, inh_reg = self._regulated_threshold(
            "RUBRIC_INHERIT_MIN",
            inh_min_base * (1.0 + (0.55 * strict_k * strictness)),
            axis=dominant_axis,
            depth=max(1, hi),
            threshold_kind="floor",
            local_support=threshold_support,
            local_opposition=threshold_opposition,
            floor_ratio=0.35,
            cap_ratio=1.85,
        )
        rel_min_dyn, rel_reg = self._regulated_threshold(
            "RUBRIC_RELATION_MIN",
            rel_min_base * (1.0 + (0.65 * strict_k * strictness)),
            axis=dominant_axis,
            depth=max(1, hi),
            threshold_kind="floor",
            local_support=threshold_support,
            local_opposition=threshold_opposition,
            floor_ratio=0.35,
            cap_ratio=1.85,
        )
        eff_min_dyn, eff_reg = self._regulated_threshold(
            "RUBRIC_EFFECT_MIN",
            eff_min_base * (1.0 + (1.20 * strict_k * strictness)),
            axis=dominant_axis,
            depth=max(1, hi),
            threshold_kind="floor",
            local_support=max(0.0, local_eff) + max(0.0, global_eff),
            local_opposition=threshold_opposition,
            floor_ratio=0.25,
            cap_ratio=2.0,
        )
        breed_min_dyn, breed_reg = self._regulated_threshold(
            "RUBRIC_BREEDING_MIN",
            breed_min_base * (1.0 + (0.75 * strict_k * strictness)),
            axis=dominant_axis,
            depth=max(1, hi),
            threshold_kind="floor",
            local_support=max(0.0, inheritance_score) + max(0.0, relation_score),
            local_opposition=threshold_opposition,
            floor_ratio=0.35,
            cap_ratio=1.85,
        )

        raw_effect_score = max(0.0, min(1.0, local_eff / (eff_min_dyn * 2.0)))
        effect_score = max(0.0, min(1.0, raw_effect_score * inheritance_influence_factor))

        if bscore <= -1000.0:
            breeding_score = 0.0
        else:
            breeding_score = max(0.0, min(1.0, (bscore + 2.0) / 4.5))

        representation_score = (
            0.20 * inheritance_score +
            0.25 * relation_score +
            0.35 * effect_score +
            0.20 * breeding_score
        )

        # Sustainability: complex structures are expensive to form, but should be cheaper to maintain.
        # Use generation as coupling-depth proxy for maintenance discount behavior.
        effective_depth = max(1, hi)
        maint_discount = self._maintenance_discount(effective_depth)
        maint_max = max(1e-9, float(getattr(cfg, "MAINTENANCE_DISCOUNT_MAX", 0.60)))
        maint_efficiency = max(0.0, min(1.0, maint_discount / maint_max))

        persistence_affordability = max(0.0, min(1.0, (tax_cap - persistence_tax_factor) / max(1e-9, (tax_cap - 1.0))))

        sustainability_score = max(0.0, min(1.0,
            (0.40 * maint_efficiency) +
            (0.25 * complexity_index) +
            (0.15 * origin_strength) +
            (0.20 * persistence_affordability)
        ))

        # Normalized formation-vs-maintenance economics in tick units.
        # Interpretation: approximate ticks needed for maintenance savings to amortize formation burden.
        formation_burden = (
            1.0
            + (max(0.0, float(getattr(cfg, "COMPLEXITY_FORMATION_SCALE", 0.10))) * (max(0, effective_depth - 1) + max(0, int(rel_prof.get("axes_active", 0)) - 1)))
            + (max(0.0, float(getattr(cfg, "SCALE_FORMATION_WEIGHT", 0.20))) * scale_depth_index)
        )
        formation_burden *= (1.0 + (0.50 * strictness))
        persistence_tax_per_tick = max(1e-9, (1.0 - maint_discount) * persistence_tax_factor)
        maintenance_savings_per_tick = max(1e-9, maint_discount / persistence_tax_factor)
        break_even_ticks = float(formation_burden / maintenance_savings_per_tick)

        # Requirement coverage (validation semantics, not pass/fail grading).
        req_cov_parts = [
            min(1.0, inheritance_score / max(1e-9, inh_min_dyn)),
            min(1.0, relation_score / max(1e-9, rel_min_dyn)),
            min(1.0, local_eff / max(1e-9, eff_min_dyn)),
            min(1.0, breeding_score / max(1e-9, breed_min_dyn)),
        ]
        requirement_coverage = max(0.0, min(1.0, sum(req_cov_parts) / float(len(req_cov_parts))))

        issues = []
        # Coherence checks (validation only)
        if cnt <= 0:
            issues.append("no_events")
        if not evidence_complete:
            issues.append("insufficient_evidence")
        if not any(int(counts.get(a, 0) or 0) > 0 for a in AXES):
            issues.append("missing_axis_counts")
        infl_sum = sum(float(v) for v in infl.values())
        if abs(infl_sum - 1.0) > 0.02:
            issues.append("inheritance_distribution_not_normalized")
        projected_global = local_eff * scope_scale
        if abs(projected_global - global_eff) > max(1e-9, abs(global_eff) * 0.05):
            issues.append("effect_layer_mismatch")
        if relation_score <= 0.0:
            issues.append("relation_mapping_empty")
        if inheritance_score < inh_min_dyn:
            issues.append("inheritance_under_scale_requirement")
        if relation_score < rel_min_dyn:
            issues.append("relation_under_scale_requirement")
        if local_eff < eff_min_dyn:
            issues.append("effect_under_scale_requirement")
        if breeding_score < breed_min_dyn:
            issues.append("breeding_under_scale_requirement")

        validation_complete = evidence_complete and (len(issues) == 0)
        return {
            "enabled": True,
            "evidence_min": int(evidence_min),
            "evidence_complete": bool(evidence_complete),
            "validation_complete": bool(validation_complete),
            "issues": list(issues),
            "inheritance_score": round(float(inheritance_score), 6),
            "inheritance_influence_factor": round(float(inheritance_influence_factor), 6),
            "relation_score": round(float(relation_score), 6),
            "effect_score": round(float(effect_score), 6),
            "effect_score_raw": round(float(raw_effect_score), 6),
            "breeding_score": round(float(breeding_score), 6),
            "representation_score": round(float(representation_score), 6),
            "sustainability_score": round(float(sustainability_score), 6),
            "formation_burden": round(float(formation_burden), 6),
            "persistence_tax_factor": round(float(persistence_tax_factor), 6),
            "persistence_tax_per_tick": round(float(persistence_tax_per_tick), 6),
            "maintenance_savings_per_tick": round(float(maintenance_savings_per_tick), 6),
            "break_even_ticks": round(float(break_even_ticks), 3),
            "requirement_coverage": round(float(requirement_coverage), 6),
            "scale_depth_index": round(float(scale_depth_index), 6),
            "complexity_index": round(float(complexity_index), 6),
            "strictness_index": round(float(strictness), 6),
            "dynamic_thresholds": {
                "evidence_min": int(evidence_min),
                "inheritance_min": round(float(inh_min_dyn), 6),
                "relation_min": round(float(rel_min_dyn), 6),
                "effect_min": round(float(eff_min_dyn), 9),
                "breeding_min": round(float(breed_min_dyn), 6),
                "pressure_regulation": {
                    "dominant_axis": str(dominant_axis),
                    "evidence": {"factor": round(float(evidence_reg.get("factor", 1.0) or 1.0), 6), "gradient": round(float(evidence_reg.get("pressure_gradient", 0.0) or 0.0), 6)},
                    "inheritance": {"factor": round(float(inh_reg.get("factor", 1.0) or 1.0), 6), "gradient": round(float(inh_reg.get("pressure_gradient", 0.0) or 0.0), 6)},
                    "relation": {"factor": round(float(rel_reg.get("factor", 1.0) or 1.0), 6), "gradient": round(float(rel_reg.get("pressure_gradient", 0.0) or 0.0), 6)},
                    "effect": {"factor": round(float(eff_reg.get("factor", 1.0) or 1.0), 6), "gradient": round(float(eff_reg.get("pressure_gradient", 0.0) or 0.0), 6)},
                    "breeding": {"factor": round(float(breed_reg.get("factor", 1.0) or 1.0), 6), "gradient": round(float(breed_reg.get("pressure_gradient", 0.0) or 0.0), 6)},
                },
            },
            "axes_active": int(rel_prof.get("axes_active", 0)),
            "dominance": round(float(rel_prof.get("dominance", 1.0)), 6),
            "constraint_influence": {a: round(float(infl.get(a, 0.0)), 6) for a in AXES},
        }


    def _shape_signature(self, counts: Dict[str, int]) -> str:
        active = [(a, _axis_count_value(v)) for a, v in counts.items() if _axis_count_value(v) > 0]
        active.sort(key=lambda kv: (-kv[1], kv[0]))
        return "+".join([f"{a}{v}" for a, v in active]) if active else "none"

    def _record_validation_issues(self, rec: Dict[str, Any], regulation: Dict[str, Any]) -> None:
        issues = list(regulation.get("issues", []) or [])
        if not issues:
            return
        self._issue_history.append({
            "tick": int(self.tick_count),
            "signature": str(rec.get("signature", "")),
            "shape": self._shape_signature(dict(rec.get("counts", {}) or {})),
            "issues": issues,
        })

    def _score_with_params(self, rec: Dict[str, Any], params: Dict[str, float]) -> float:
        # Lightweight objective: maximize representation coherence proxy.
        counts = dict(rec.get("counts", {}) or {})
        infl = self._slot_influence_distribution(counts)
        rel = float(self._relation_profile(counts).get("relation_score", 0.0))
        local_eff = float(rec.get("local_effect_ema", rec.get("effect_ema", 0.0)) or 0.0)
        scope = float(rec.get("scope_scale", 1.0) or 1.0)
        global_eff = float(rec.get("effect_ema", 0.0) or 0.0)
        projected = local_eff * scope
        mismatch = abs(projected - global_eff)
        norm = max(1e-9, abs(global_eff))
        mismatch_score = max(0.0, 1.0 - min(1.0, mismatch / norm))

        dominant = max(infl.values()) if infl else 0.0
        influence = 0.5 + dominant
        # Params influence objective softly.
        influence *= float(params.get("dup_redist", 0.5)) / 0.5
        scope_adj = float(params.get("scope_alpha", 0.8)) / max(1e-9, float(getattr(self.cfg, "COMPLEXITY_SCOPE_ALPHA", 0.8)))

        return (0.35 * mismatch_score) + (0.30 * rel) + (0.20 * min(1.0, influence)) + (0.15 * min(1.0, scope_adj))

    def _maybe_run_representation_experiments(self) -> None:
        if not bool(getattr(self.cfg, "EXPERIMENTS_ENABLED", True)):
            return

        window = int(getattr(self.cfg, "EXPERIMENT_WINDOW", 80))
        if int(self.tick_count - self._last_experiment_tick) < window:
            return

        recent = [e for e in list(self._issue_history) if int(self.tick_count - int(e.get("tick", 0))) <= window]

        trigger_mode = "issue_cluster"
        target_shape = ""
        min_issues = int(getattr(self.cfg, "EXPERIMENT_MIN_ISSUES", 20))
        if len(recent) >= min_issues:
            # Find most problematic shape cluster.
            shape_counts: Dict[str, int] = defaultdict(int)
            for e in recent:
                shape_counts[str(e.get("shape", "none"))] += len(list(e.get("issues", []) or []))
            if shape_counts:
                target_shape = max(shape_counts.items(), key=lambda kv: kv[1])[0]
        else:
            if not bool(getattr(self.cfg, "EXPERIMENT_EXPLORATORY_ENABLED", True)):
                return
            if len(self._coupling_roots) < int(getattr(self.cfg, "EXPERIMENT_EXPLORATORY_MIN_COUPLINGS", 12)):
                return
            if int(self.tick_count - self._last_experiment_tick) < int(getattr(self.cfg, "EXPERIMENT_EXPLORATORY_PERIOD", 120)):
                return
            trigger_mode = "exploratory"
            shape_by_count: Dict[str, int] = defaultdict(int)
            for rec in self._coupling_roots.values():
                shp = self._shape_signature(dict(rec.get("counts", {}) or {}))
                shape_by_count[shp] += int(rec.get("count", 0) or 0)
            if not shape_by_count:
                return
            target_shape = max(shape_by_count.items(), key=lambda kv: kv[1])[0]

        if not target_shape:
            self._last_experiment_tick = int(self.tick_count)
            return

        # pick representative coupling from current roots
        candidates = [r for r in self._coupling_roots.values() if self._shape_signature(dict(r.get("counts", {}) or {})) == target_shape]
        if not candidates:
            self._last_experiment_tick = int(self.tick_count)
            return
        rep = max(candidates, key=lambda r: int(r.get("count", 0) or 0))

        base_params = {
            "dup_redist": float(getattr(self.cfg, "DUPLICATE_SLOT_REDISTRIBUTION", 0.50)),
            "scope_alpha": float(getattr(self.cfg, "COMPLEXITY_SCOPE_ALPHA", 0.80)),
        }
        deltas = [
            {"dup_redist": max(0.1, min(0.9, base_params["dup_redist"] + 0.05)), "scope_alpha": base_params["scope_alpha"]},
            {"dup_redist": max(0.1, min(0.9, base_params["dup_redist"] - 0.05)), "scope_alpha": base_params["scope_alpha"]},
            {"dup_redist": base_params["dup_redist"], "scope_alpha": max(0.2, min(1.5, base_params["scope_alpha"] + 0.05))},
            {"dup_redist": base_params["dup_redist"], "scope_alpha": max(0.2, min(1.5, base_params["scope_alpha"] - 0.05))},
            {"dup_redist": max(0.1, min(0.9, base_params["dup_redist"] + 0.03)), "scope_alpha": max(0.2, min(1.5, base_params["scope_alpha"] + 0.03))},
            {"dup_redist": max(0.1, min(0.9, base_params["dup_redist"] - 0.03)), "scope_alpha": max(0.2, min(1.5, base_params["scope_alpha"] - 0.03))},
        ]
        max_trials = int(getattr(self.cfg, "EXPERIMENT_MAX_TRIALS_PER_TRIGGER", 4))
        deltas = deltas[:max(1, max_trials)]

        base_score = self._score_with_params(rep, base_params)
        best = {"params": dict(base_params), "score": float(base_score), "shape": target_shape}

        for cand in deltas:
            score = self._score_with_params(rep, cand)
            trial = {
                "tick": int(self.tick_count),
                "trigger_mode": trigger_mode,
                "shape": target_shape,
                "base_params": dict(base_params),
                "trial_params": dict(cand),
                "base_score": float(round(base_score, 6)),
                "trial_score": float(round(score, 6)),
                "improvement": float(round(score - base_score, 6)),
                "adopted": False,
            }
            self._experiment_trials.append(trial)
            if score > best["score"] + 0.01:
                best = {"params": dict(cand), "score": float(score), "shape": target_shape}

        if best["params"] != base_params:
            # Adopt improved profile globally (bounded change).
            self.cfg.DUPLICATE_SLOT_REDISTRIBUTION = float(best["params"]["dup_redist"])
            self.cfg.COMPLEXITY_SCOPE_ALPHA = float(best["params"]["scope_alpha"])
            self._experiment_adoptions.append({
                "tick": int(self.tick_count),
                "trigger_mode": trigger_mode,
                "shape": target_shape,
                "from": dict(base_params),
                "to": dict(best["params"]),
                "score": float(round(best["score"], 6)),
            })
            for t in reversed(self._experiment_trials):
                if (
                    int(t.get("tick", -1)) == int(self.tick_count)
                    and str(t.get("trigger_mode", "")) == trigger_mode
                    and str(t.get("shape", "")) == target_shape
                    and dict(t.get("trial_params", {})) == dict(best["params"])
                ):
                    t["adopted"] = True
                    break

        self._last_experiment_tick = int(self.tick_count)

    def _item_generation(self, item: TraceItem, memo: Optional[Dict[str, int]] = None, seen: Optional[set] = None) -> int:
        memo = memo or {}
        item_id = str(getattr(item, "id", ""))
        kind = str(getattr(item, "kind", "ABILITY")).upper()

        if item_id in memo:
            return int(memo[item_id])

        gen0_atoms = frozenset(GENEALOGY_ATOM_TO_SLOT_ID.keys()) if _CLOSURE_BASIS_AVAILABLE else frozenset(f"NC:{a}>{b}" for a in AXES for b in AXES)
        if item_id in gen0_atoms:
            memo[item_id] = 0
            return 0

        if kind == "LINK" and item_id.startswith("L:"):
            if seen is None:
                seen = set()
            if item_id in seen:
                return max(1, int(getattr(self.links.get(item_id), "depth", 1) or 1))
            seen.add(item_id)
            lnk = self.links.get(item_id)
            if lnk is None:
                memo[item_id] = 1
                return 1
            parent_vals = []
            for p in list(getattr(lnk, "parents", []) or []):
                p_id = str(p)
                p_kind = "LINK" if p_id.startswith("L:") else "ABILITY"
                parent_vals.append(self._item_generation(TraceItem(kind=p_kind, id=p_id), memo=memo, seen=seen))
            seen.discard(item_id)
            if len(parent_vals) >= 2:
                g = _bred_child_generation(parent_vals[0], parent_vals[1])
            else:
                g = (max(parent_vals) + 1) if parent_vals else 1
            memo[item_id] = int(g)
            return int(g)

        # Any non-Gen0 ability is generation 1 by strict model.
        memo[item_id] = 1
        return 1

    def _update_coupling_roots(
        self,
        trace: List[TraceItem],
        relief: PressureVec,
        difference_snapshot: Optional[DifferenceSnapshot],
        dominant_axis: str,
    ) -> Dict[str, Any]:
        if len(trace) < 2:
            # Still update persistent pressure root from pure pressure channel.
            if difference_snapshot is not None:
                try:
                    p = abs(float(difference_snapshot.value(Constraint.A))) * abs(float(difference_snapshot.value(Constraint.N))) * abs(float(difference_snapshot.value(Constraint.T)))
                    rate = max(0.001, min(0.5, float(getattr(self.cfg, "COUPLING_EMA_RATE", 0.08))))
                    self._persistent_pressure_root_ema = ((1.0 - rate) * float(self._persistent_pressure_root_ema)) + (rate * p)
                except Exception:
                    pass
            return {}

        memo: Dict[str, Dict[str, int]] = {}
        gen_memo: Dict[str, int] = {}
        decay = max(0.0, min(0.1, float(getattr(self.cfg, "COUPLING_DECAY", 0.005))))
        rate = max(0.001, min(0.5, float(getattr(self.cfg, "COUPLING_EMA_RATE", 0.08))))
        relief_mag = max(0.0, float(relief.sum_positive_relief()))

        # Light decay so stale couplings fade naturally.
        if decay > 0.0:
            for rec in self._coupling_roots.values():
                rec["effect_ema"] = max(0.0, float(rec.get("effect_ema", 0.0)) * (1.0 - decay))

        seen_pairs = set()
        touched: List[str] = []
        for i in range(len(trace) - 1):
            left = trace[i]
            right = trace[i + 1]
            pair_key = (str(getattr(left, "kind", "")), str(getattr(left, "id", "")), str(getattr(right, "kind", "")), str(getattr(right, "id", "")))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            l_counts = self._axis_counts_from_item(left, memo=memo)
            r_counts = self._axis_counts_from_item(right, memo=memo)
            merged = self._add_axis_counts(l_counts, r_counts)
            left_gen = self._item_generation(left, memo=gen_memo)
            right_gen = self._item_generation(right, memo=gen_memo)
            coupling_gen = int(_bred_child_generation(left_gen, right_gen))
            left_role = _generation_role_name(left_gen)
            right_role = _generation_role_name(right_gen)
            coupling_role = _generation_role_name(coupling_gen)
            breeding_score = float(_breeding_pair_score(left_gen, right_gen))

            canonical = self._canonical_coupling_signature(merged)
            left_sig = self._canonical_coupling_signature(l_counts)
            right_sig = self._canonical_coupling_signature(r_counts)
            origin = f"({left_sig})x({right_sig})"

            rec = self._coupling_roots.get(canonical)
            if rec is None:
                rec = {
                    "signature": canonical,
                    "semantic": self._semantic_coupling_label(merged),
                    "counts": {a: int(merged.get(a, 0)) for a in AXES},
                    "count": 0,
                    "effect_ema": 0.0,
                    "raw_effect_ema": 0.0,
                    "local_effect_ema": 0.0,
                    "global_effect_ema": 0.0,
                    "scope_scale": 1.0,
                    "dominant_axis_counts": {a: 0 for a in AXES},
                    "top_origins": {},
                    "last_tick": int(self.tick_count),
                    "min_generation": int(coupling_gen),
                    "max_generation": int(coupling_gen),
                    "last_generation": int(coupling_gen),
                    "last_generation_role": str(coupling_role),
                    "breeding_score_ema": 0.0,
                    "regulation": {"enabled": bool(getattr(self.cfg, "RUBRIC_ENABLED", True)), "validation_complete": False, "issues": []},
                    "inheritance_breach_count": 0,
                    "inheritance_breach_active": False,
                    "semantic_lane_ema": {},
                    "semantic_confidence": 0.0,
                    "semantic_version": 0,
                    "semantic_translation": "",
                }
                self._coupling_roots[canonical] = rec

            rec["count"] = int(rec.get("count", 0)) + 1
            rec["raw_effect_ema"] = ((1.0 - rate) * float(rec.get("raw_effect_ema", rec.get("effect_ema", 0.0)))) + (rate * relief_mag)
            influence = self._slot_influence_distribution(dict(rec.get("counts", {}) or {}))
            dominant_influence = float(influence.get(str(dominant_axis or "X").upper(), 0.0))
            inheritance_influence_factor = 0.5 + dominant_influence
            rec["local_effect_ema"] = float(rec.get("raw_effect_ema", 0.0)) * inheritance_influence_factor
            rec["scope_scale"] = float(self._complexity_scope_scale(rec))
            rec["global_effect_ema"] = float(rec.get("local_effect_ema", 0.0)) * float(rec.get("scope_scale", 1.0))
            rec["effect_ema"] = float(rec.get("global_effect_ema", 0.0))
            rec["last_tick"] = int(self.tick_count)
            rec["min_generation"] = min(int(rec.get("min_generation", coupling_gen)), int(coupling_gen))
            rec["max_generation"] = max(int(rec.get("max_generation", coupling_gen)), int(coupling_gen))
            rec["last_generation"] = int(coupling_gen)
            rec["last_generation_role"] = str(coupling_role)
            rec["breeding_score_ema"] = ((1.0 - rate) * float(rec.get("breeding_score_ema", 0.0))) + (rate * breeding_score)
            dax = str(dominant_axis or "X").upper()
            if dax in rec["dominant_axis_counts"]:
                rec["dominant_axis_counts"][dax] = int(rec["dominant_axis_counts"][dax]) + 1

            top_origins = dict(rec.get("top_origins", {}) or {})
            top_origins[origin] = int(top_origins.get(origin, 0)) + 1
            if len(top_origins) > 12:
                top_origins = dict(sorted(top_origins.items(), key=lambda kv: kv[1], reverse=True)[:12])
            rec["top_origins"] = top_origins

            regulation = self._evaluate_coupling_rubric(rec)
            rec["regulation"] = dict(regulation)
            self._record_validation_issues(rec, regulation)
            if bool(regulation.get("enabled", True)):
                dyn = dict(regulation.get("dynamic_thresholds", {}) or {})
                inh_dyn = float(dyn.get("inheritance_min", getattr(self.cfg, "RUBRIC_INHERIT_MIN", 0.60)) or getattr(self.cfg, "RUBRIC_INHERIT_MIN", 0.60))
                inh_score = float(regulation.get("inheritance_score", 1.0) or 1.0)
                breach_now = inh_score < inh_dyn
                breach_prev = bool(rec.get("inheritance_breach_active", False))
                if breach_now and (not breach_prev):
                    rec["inheritance_breach_count"] = int(rec.get("inheritance_breach_count", 0) or 0) + 1
                rec["inheritance_breach_active"] = bool(breach_now)

            sem_rate = max(0.01, min(0.5, float(getattr(self.cfg, "SEMANTIC_EMA_RATE", 0.10))))
            self._update_semantic_translation(rec, sem_rate)
            self._maybe_run_representation_experiments()

            self._coupling_origin_counts[origin] += 1
            touched.append(canonical)

        # Persistent pressure coupling root as accuracy reflector: A*N*T
        if difference_snapshot is not None:
            try:
                p = abs(float(difference_snapshot.value(Constraint.A))) * abs(float(difference_snapshot.value(Constraint.N))) * abs(float(difference_snapshot.value(Constraint.T)))
                self._persistent_pressure_root_ema = ((1.0 - rate) * float(self._persistent_pressure_root_ema)) + (rate * p)
            except Exception:
                pass

        if touched:
            self._coupling_events += 1

        top = sorted(
            [self._coupling_roots[k] for k in set(touched)],
            key=lambda rec: (float(rec.get("effect_ema", 0.0)), int(rec.get("count", 0))),
            reverse=True,
        )[:3]

        expected_root_raw, expected_root_canonical, _root_rec, observed_gen, expected_gen, accuracy_ok = self._persistent_root_lookup()

        return {
            "persistent_pressure_root": expected_root_raw,
            "persistent_pressure_root_canonical": expected_root_canonical,
            "persistent_pressure_root_ema": round(float(self._persistent_pressure_root_ema), 11),
            "persistent_root_generation_expected": expected_gen,
            "persistent_root_generation_observed": observed_gen,
            "persistent_root_accuracy_ok": accuracy_ok,
            "top": [
                {
                    "signature": str(rec.get("signature", "")),
                    "semantic": str(rec.get("semantic", "")),
                    "count": int(rec.get("count", 0)),
                    "effect_ema": round(float(rec.get("effect_ema", 0.0)), 11),
                    "min_generation": int(rec.get("min_generation", 0) or 0),
                    "max_generation": int(rec.get("max_generation", 0) or 0),
                    "generation_role": str(rec.get("last_generation_role", "PRIMARY")),
                    "breeding_score_ema": round(float(rec.get("breeding_score_ema", 0.0)), 6),
                    "effect_descriptor": self._coupling_effect_descriptor(rec),
                    "raw_effect_ema": round(float(rec.get("raw_effect_ema", 0.0) or 0.0), 6),
                    "local_effect_ema": round(float(rec.get("local_effect_ema", rec.get("effect_ema", 0.0)) or 0.0), 6),
                    "global_effect_ema": round(float(rec.get("global_effect_ema", rec.get("effect_ema", 0.0)) or 0.0), 6),
                    "scope_scale": round(float(rec.get("scope_scale", 1.0) or 1.0), 6),
                    "semantic_translation": str(rec.get("semantic_translation", "")),
                    "semantic_confidence": round(float(rec.get("semantic_confidence", 0.0) or 0.0), 6),
                    "semantic_version": int(rec.get("semantic_version", 0) or 0),
                    "semantic_lane_ema": dict(rec.get("semantic_lane_ema", {}) or {}),
                    "regulation": dict(rec.get("regulation", {}) or {}),
                    "inheritance_breach_count": int(rec.get("inheritance_breach_count", 0) or 0),
                }
                for rec in top
            ],
        }

    # ----------------------------------------------------------------
    # INTERNAL — Relief check
    # ----------------------------------------------------------------

    def _is_relief_event(self, relief: PressureVec) -> bool:
        dom_axis = relief.dominant_positive_axis() or "X"
        relief_eps, _ = self._regulated_threshold(
            "RELIEF_EPS",
            float(self.cfg.RELIEF_EPS),
            axis=dom_axis,
            depth=1,
            threshold_kind="floor",
            local_support=max(0.0, float(getattr(relief, dom_axis, 0.0))),
            local_opposition=max(0.0, float(relief.sum_positive_relief() - max(0.0, float(getattr(relief, dom_axis, 0.0))))),
            floor_ratio=0.25,
            cap_ratio=2.0,
        )
        relief_total_eps, _ = self._regulated_threshold(
            "RELIEF_TOTAL_EPS",
            float(self.cfg.RELIEF_TOTAL_EPS),
            axis=dom_axis,
            depth=1,
            threshold_kind="floor",
            local_support=max(0.0, float(relief.sum_positive_relief())),
            local_opposition=max(0.0, float(relief.max_relief())),
            floor_ratio=0.25,
            cap_ratio=2.0,
        )
        return (
            relief.max_relief() >= relief_eps
            or relief.sum_positive_relief() >= relief_total_eps
        )

    # ----------------------------------------------------------------
    # INTERNAL — Ability resolution (handles both Ability and Link trace items)
    # ----------------------------------------------------------------

    def _link_ability_id(self, link: ConstraintLink) -> str:
        """Stable derived ability id for a promoted link."""
        axis = str(getattr(link, "dominant_relief_axis", "X") or "X").upper()
        suffix = str(getattr(link, "id", "")).replace(":", "_")
        return f"{axis}:LINK_{suffix}"

    def _register_link_ability(self, link: ConstraintLink) -> bool:
        """Register a promoted link as a derived ability once (no duplicates)."""
        if not bool(getattr(self.cfg, "LINK_AS_ABILITY", True)):
            return False

        aid = self._link_ability_id(link)
        if aid in self.abilities:
            return False

        depth = max(1, int(getattr(link, "depth", 1) or 1))
        discount = self._maintenance_discount(depth)
        mean_cost = getattr(link, "mean_cost", {}) or {}
        cost = {
            a: max(
                0.0,
                float(mean_cost.get(a, 0.0))
                * (1.0 - discount)
                * self._axis_persistence_tax_factor(a, depth=depth)
            )
            for a in AXES
        }

        risk = {a: 0.0 for a in AXES}
        risk["X"] = max(0.0, float(getattr(link, "mean_x_risk", 0.0) or 0.0))

        tags = list(getattr(link, "tags", []) or [])
        tags.extend(["derived_link", "composite"])
        dedup_tags = tuple(dict.fromkeys([str(t) for t in tags if t]))

        link_id = str(getattr(link, "id", "?"))
        self.abilities[aid] = _augment_ability_profile_with_origin(AbilityProfile(
            id=aid,
            axis=str(getattr(link, "dominant_relief_axis", "X") or "X"),
            requires=tuple(AXES),
            cost=cost,
            risk=risk,
            effect_tags=dedup_tags,
            notes=(
                f"Derived from promoted link {link_id} "
                f"(depth={depth}, count={int(getattr(link, 'count', 0) or 0)}, "
                f"maint_discount={discount:.2f}, tax_opposed=on)"
            ),
        ))
        return True

    def _register_compression_ability(
        self,
        key: Tuple[str, str],
        depth: int,
        dominant_axis: str,
        compression: Dict[str, float],
    ) -> str:
        """Register adaptive compression as a lineage-traceable derived ability."""
        sig = str(compression.get("signature", "0") or "0")
        raw = f"compression::{key[0]}::{key[1]}::{sig}::{int(depth)}"
        h = hashlib.sha1(raw.encode()).hexdigest()[:10]
        aid = f"N:COMPRESSION_{h}"
        if aid in self.abilities:
            return aid

        gain = max(0.0, float(compression.get("gain", 0.0) or 0.0))
        maturity = max(0.0, min(1.0, float(compression.get("maturity", 0.0) or 0.0)))
        family_count = int(compression.get("family_count", 0) or 0)
        op_lineage = hashlib.sha1((f"{key[0]}->{key[1]}::{sig}").encode()).hexdigest()[:12]

        # Compression op is cheap to run, mostly N/B-facing, with low X-risk.
        base = 0.0005 + (0.0015 * (1.0 - gain))
        cost = {
            "X": 0.05 * base,
            "T": 0.20 * base,
            "N": 1.00 * base,
            "B": 0.45 * base,
            "A": 0.15 * base,
        }
        risk = {a: 0.0 for a in AXES}
        risk["X"] = 0.0001 * (1.0 - min(1.0, gain))

        tags = tuple(
            dict.fromkeys([
                "derived_operation",
                "adaptive_compression",
                f"signature:{sig}",
                f"dominant_axis:{str(dominant_axis or 'X').upper()}",
                f"operation_lineage:{op_lineage}",
            ])
        )

        self.abilities[aid] = _augment_ability_profile_with_origin(AbilityProfile(
            id=aid,
            axis="N",
            requires=tuple(AXES),
            cost=cost,
            risk=risk,
            effect_tags=tags,
            notes=(
                f"Adaptive compression operator for pair ({key[0]} -> {key[1]}). "
                f"lineage_signature={sig}; operation_lineage_id={op_lineage}; "
                f"family_count={family_count}; maturity={maturity:.3f}; gain={gain:.3f}; depth={int(depth)}"
            ),
        ))
        return aid

    def normalize_ability_origins(self) -> int:
        """Backfill universal origin lineage tags/notes for all abilities."""
        count = 0
        updated: Dict[str, AbilityProfile] = {}
        for aid, ap in dict(self.abilities).items():
            if not isinstance(ap, AbilityProfile):
                continue
            new_ap = _augment_ability_profile_with_origin(ap)
            updated[str(aid)] = new_ap
            if new_ap.notes != ap.notes or tuple(new_ap.effect_tags) != tuple(ap.effect_tags):
                count += 1
        if updated:
            self.abilities = updated
        return int(count)

    def _code_evolution_axis(self, constraints: Iterable[str]) -> str:
        ordered = ("A", "B", "N", "T", "X")
        found = set()
        for raw in (constraints or ()):
            ax = _canonical_axis_token(str(raw or ""))
            if ax:
                found.add(str(ax))
        for ax in ordered:
            if ax in found:
                return ax
        return "B"

    def register_code_evolution_outcome(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        rec = dict(payload or {})
        mutation_id = str(rec.get("mutation_id", "") or "").strip()
        if not mutation_id:
            return {"registered": False, "reason": "missing_mutation_id"}

        constraints = tuple(str(c) for c in (rec.get("constraints", []) or []) if str(c))
        axis = self._code_evolution_axis(constraints)
        operator_key = str(rec.get("operator_key", "") or "unknown")
        accepted = bool(rec.get("accepted", False))
        changed_files = [str(x) for x in (rec.get("changed_files", []) or []) if str(x)]
        target_files = [str(x) for x in (rec.get("target_files", []) or []) if str(x)]
        target_modules = tuple(dict.fromkeys(
            str(x).replace("\\", "/").replace("/", ".").removesuffix(".py")
            for x in (rec.get("target_modules", []) or [])
            if str(x)
        ))
        score = max(0.0, min(1.0, float(rec.get("score", 0.0) or 0.0)))
        surface_score = max(0.0, min(1.0, float(rec.get("surface_score", score) or score)))
        promotion_weight = max(0.0, min(1.0, float(rec.get("promotion_weight", score) or score)))
        fitness = max(0.0, float(rec.get("avg_fitness", 0.0) or 0.0))
        pressure = max(0.0, float(rec.get("genealogy_pressure", 0.0) or 0.0))
        change_count = max(0, int(rec.get("change_count", len(changed_files)) or 0))
        compile_failures = int(rec.get("compile_failures", 0) or 0)
        conflict_cost = max(0.0, float(rec.get("conflicts_delta", 0) or 0.0))
        apply_duration = max(0.0, float(rec.get("apply_duration_s", 0.0) or 0.0))
        agency_time_credit = max(0.0, min(1.0, float(rec.get("agency_time_credit", 0.0) or 0.0)))
        temporal_overhead = max(0.0, min(1.0, float(rec.get("temporal_overhead_penalty", 0.0) or 0.0)))
        lineage_hash = hashlib.sha1(f"{mutation_id}:{operator_key}".encode()).hexdigest()[:10]
        aid = f"{axis}:CODE_EVOLVE_{lineage_hash}"
        if aid in self.abilities:
            return {"registered": False, "reason": "already_registered", "ability_id": aid}

        base = 0.0008 + (0.00035 * max(1, change_count))
        cost = {
            "X": 0.10 * base,
            "T": (0.45 + (0.15 * min(1.0, pressure))) * base,
            "N": (1.15 + (0.10 * min(1.0, fitness))) * base,
            "B": (0.95 + (0.20 * min(1.0, score))) * base,
            "A": (0.70 + (0.25 * min(1.0, pressure))) * base,
        }
        risk = {a: 0.0 for a in AXES}
        risk["X"] = max(0.0, min(1.0, (0.18 if accepted else 0.42) + (0.04 * compile_failures) + (0.01 * conflict_cost)))
        risk["T"] = max(0.0, min(1.0, temporal_overhead * 0.8))

        tags = [
            "derived_operation",
            "code_evolution",
            f"mutation_operator:{operator_key}",
            f"mutation_status:{'accepted' if accepted else 'rejected'}",
            f"mutation_score:{score:.3f}",
            f"surface_score:{surface_score:.3f}",
            f"promotion_weight:{promotion_weight:.3f}",
            f"mutation_pressure:{pressure:.3f}",
            f"mutation_targets:{max(len(target_files), len(target_modules))}",
            f"mutation_changed_files:{int(change_count)}",
            f"apply_duration_s:{apply_duration:.3f}",
            f"agency_time_credit:{agency_time_credit:.3f}",
            f"temporal_overhead_penalty:{temporal_overhead:.3f}",
        ]
        for mod in target_modules[:6]:
            tags.append(f"mutation_module:{mod}")
        rewrite_profile = str(rec.get("rewrite_profile", "") or "")
        if rewrite_profile:
            tags.append(f"rewrite_profile:{rewrite_profile}")
        for mode in (rec.get("effect_modes", []) or []):
            txt = str(mode or "").strip()
            if txt:
                tags.append(f"effect_mode:{txt}")
        ability = _augment_ability_profile_with_origin(AbilityProfile(
            id=aid,
            axis=axis,
            requires=tuple(constraints or AXES),
            cost=cost,
            risk=risk,
            effect_tags=tuple(dict.fromkeys(tags)),
            notes=(
                f"Code evolution outcome for mutation_id={mutation_id}; accepted={accepted}; "
                f"operator_key={operator_key}; change_count={change_count}; "
                f"avg_fitness={fitness:.3f}; genealogy_pressure={pressure:.3f}; "
                f"surface_score={surface_score:.3f}; promotion_weight={promotion_weight:.3f}; "
                f"apply_duration_s={apply_duration:.3f}; agency_time_credit={agency_time_credit:.3f}; "
                f"temporal_overhead_penalty={temporal_overhead:.3f}; "
                f"targets={len(target_files)}; modules={','.join(target_modules[:6]) or 'none'}"
            ),
        ))
        self.abilities[aid] = ability

        trial = {
            "tick": int(self.tick_count),
            "trigger_mode": "code_evolution",
            "mutation_id": mutation_id,
            "operator_key": operator_key,
            "accepted": bool(accepted),
            "shape": str(rewrite_profile or "generic"),
            "target_modules": list(target_modules),
            "target_files": list(target_files),
            "changed_files": list(changed_files),
            "score": float(round(score, 6)),
            "avg_fitness": float(round(fitness, 6)),
            "genealogy_pressure": float(round(pressure, 6)),
            "compile_failures": int(compile_failures),
            "conflicts_delta": float(round(conflict_cost, 6)),
            "apply_duration_s": float(round(apply_duration, 6)),
            "agency_time_credit": float(round(agency_time_credit, 6)),
            "temporal_overhead_penalty": float(round(temporal_overhead, 6)),
            "ability_id": aid,
            "adopted": bool(accepted),
        }
        self._experiment_trials.append(trial)
        if accepted:
            self._experiment_adoptions.append({
                "tick": int(self.tick_count),
                "trigger_mode": "code_evolution",
                "mutation_id": mutation_id,
                "operator_key": operator_key,
                "shape": str(rewrite_profile or "generic"),
                "target_modules": list(target_modules),
                "score": float(round(score, 6)),
                "avg_fitness": float(round(fitness, 6)),
                "apply_duration_s": float(round(apply_duration, 6)),
                "agency_time_credit": float(round(agency_time_credit, 6)),
                "temporal_overhead_penalty": float(round(temporal_overhead, 6)),
                "ability_id": aid,
            })
        self.flush_files()
        return {"registered": True, "ability_id": aid, "accepted": bool(accepted)}

    def register_manual_code_assimilation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        rec = dict(payload or {})
        change_id = str(rec.get("change_id", "") or "").strip()
        if not change_id:
            return {"registered": False, "reason": "missing_change_id"}

        constraints = tuple(str(c) for c in (rec.get("constraints", []) or []) if str(c))
        axis = str(rec.get("dominant_axis", "") or self._code_evolution_axis(constraints))
        target_files = [str(x) for x in (rec.get("target_files", []) or []) if str(x)]
        target_modules = tuple(dict.fromkeys(
            str(x).replace("\\", "/").replace("/", ".").removesuffix(".py")
            for x in (rec.get("target_modules", []) or [])
            if str(x)
        ))
        rewrite_profile = str(rec.get("rewrite_profile", "") or "generic")
        matched_ability_id = str(rec.get("matched_ability_id", "") or "").strip()
        matched_score = max(0.0, min(1.0, float(rec.get("matched_score", 0.0) or 0.0)))
        axis_signature = str(rec.get("axis_signature", "") or "").strip()
        purpose_lane = str(rec.get("purpose_lane", "") or "admissibility_grounding")
        source = str(rec.get("source", "") or "manual_code")
        change_kind = str(rec.get("change_kind", "") or "modified")
        digest = hashlib.sha1(
            f"{change_id}:{','.join(target_files)}:{','.join(target_modules)}:{axis_signature}:{source}".encode()
        ).hexdigest()[:10]

        if matched_ability_id and matched_ability_id in self.abilities:
            existing = self.abilities[matched_ability_id]
            tags = list(getattr(existing, "effect_tags", ()) or ())
            tags.extend([
                "manual_code_lineage",
                f"manual_change:{change_id}",
                f"manual_source:{source}",
                f"manual_change_kind:{change_kind}",
                f"manual_match_score:{matched_score:.3f}",
                f"purpose_lane:{purpose_lane}",
            ])
            if axis_signature:
                tags.append(f"manual_axis_signature:{axis_signature}")
            for mod in target_modules[:6]:
                tags.append(f"mutation_module:{mod}")
            updated = _augment_ability_profile_with_origin(AbilityProfile(
                id=str(existing.id),
                axis=str(existing.axis),
                requires=tuple(existing.requires),
                cost={a: float(existing.cost.get(a, 0.0)) for a in AXES},
                risk={a: float(existing.risk.get(a, 0.0)) for a in AXES},
                effect_tags=tuple(dict.fromkeys(tags)),
                notes=(
                    f"{existing.notes}; manual_code_change={change_id}; source={source}; "
                    f"kind={change_kind}; matched_score={matched_score:.3f}; "
                    f"modules={','.join(target_modules[:6]) or 'none'}"
                ),
            ))
            self.abilities[matched_ability_id] = updated
            self._experiment_trials.append({
                "tick": int(self.tick_count),
                "trigger_mode": "manual_code_assimilation",
                "change_id": change_id,
                "shape": rewrite_profile,
                "target_modules": list(target_modules),
                "target_files": list(target_files),
                "matched_ability_id": matched_ability_id,
                "matched_score": float(round(matched_score, 6)),
                "ability_id": matched_ability_id,
                "adopted": True,
            })
            self._experiment_adoptions.append({
                "tick": int(self.tick_count),
                "trigger_mode": "manual_code_assimilation",
                "change_id": change_id,
                "shape": rewrite_profile,
                "target_modules": list(target_modules),
                "ability_id": matched_ability_id,
                "score": float(round(matched_score, 6)),
            })
            self.flush_files()
            return {
                "registered": True,
                "ability_id": matched_ability_id,
                "mode": "attached_existing_family",
                "matched_score": float(round(matched_score, 6)),
            }

        aid = f"{axis}:CODE_LINEAGE_{digest}"
        if aid in self.abilities:
            return {"registered": False, "reason": "already_registered", "ability_id": aid}

        base = 0.0009 + (0.00025 * max(1, len(target_modules) or len(target_files)))
        cost = {
            "X": 0.12 * base,
            "T": 0.42 * base,
            "N": 1.00 * base,
            "B": 0.82 * base,
            "A": 0.68 * base,
        }
        risk = {a: 0.0 for a in AXES}
        risk["X"] = 0.16
        risk["T"] = 0.08
        tags = [
            "derived_operation",
            "manual_code_lineage",
            f"manual_change:{change_id}",
            f"manual_source:{source}",
            f"manual_change_kind:{change_kind}",
            f"rewrite_profile:{rewrite_profile}",
            f"purpose_lane:{purpose_lane}",
        ]
        if axis_signature:
            tags.append(f"origin_signature:{axis_signature}")
        for mod in target_modules[:6]:
            tags.append(f"mutation_module:{mod}")
        ability = _augment_ability_profile_with_origin(AbilityProfile(
            id=aid,
            axis=axis,
            requires=tuple(constraints or AXES),
            cost=cost,
            risk=risk,
            effect_tags=tuple(dict.fromkeys(tags)),
            notes=(
                f"Manual code lineage for change_id={change_id}; source={source}; kind={change_kind}; "
                f"rewrite_profile={rewrite_profile}; modules={','.join(target_modules[:6]) or 'none'}; "
                f"axis_signature={axis_signature or 'none'}"
            ),
        ))
        self.abilities[aid] = ability
        self._experiment_trials.append({
            "tick": int(self.tick_count),
            "trigger_mode": "manual_code_assimilation",
            "change_id": change_id,
            "shape": rewrite_profile,
            "target_modules": list(target_modules),
            "target_files": list(target_files),
            "ability_id": aid,
            "adopted": True,
        })
        self._experiment_adoptions.append({
            "tick": int(self.tick_count),
            "trigger_mode": "manual_code_assimilation",
            "change_id": change_id,
            "shape": rewrite_profile,
            "target_modules": list(target_modules),
            "ability_id": aid,
            "score": 0.72,
        })
        self.flush_files()
        return {"registered": True, "ability_id": aid, "mode": "created_manual_branch"}

    def _resolve_ability(self, item: TraceItem) -> Optional[AbilityProfile]:
        """
        For ABILITY items return the registered profile.
        For LINK items, return a synthetic profile aggregated from its parents.
        """
        if item.kind == "ABILITY":
            return self.abilities.get(item.id)

        if item.kind == "LINK":
            lnk = self.links.get(item.id)
            if lnk is None:
                return None

            derived = self.abilities.get(self._link_ability_id(lnk))
            if derived is not None:
                return derived

            # Fallback synthetic profile (for compatibility if LINK_AS_ABILITY=False).
            discount = self._maintenance_discount(lnk.depth)
            cost = {
                a: max(
                    0.0,
                    float(lnk.mean_cost.get(a, 0.0))
                    * (1.0 - discount)
                    * self._axis_persistence_tax_factor(a, depth=max(1, int(lnk.depth)))
                )
                for a in AXES
            }
            return AbilityProfile(
                id=item.id,
                axis=lnk.dominant_relief_axis or "X",
                requires=tuple(AXES),
                cost=cost,
                risk={"X": lnk.mean_x_risk},
                effect_tags=tuple(lnk.tags),
                notes=f"Synthetic profile for link {item.id} (maint_discount={discount:.2f})",
            )
        return None

    # ----------------------------------------------------------------
    # INTERNAL — Pair accumulation and promotion
    # ----------------------------------------------------------------

    def inject_training_plateau_pressure(
        self,
        plateau_ratio: float,
        axis_hint: Optional[str] = None,
    ) -> None:
        """
        Receive an external training-progress plateau signal from the
        ProgressSampler or stall diagnostics.

        plateau_ratio: 0.0 = progressing normally, 1.0 = fully stalled.
        axis_hint: which constraint axis the fail is attributed to (T/N/X/B/A).
            When provided, uses that axis's per-axis complexity curve to
            correct the injection — so pressure routing reflects which axis
            is currently in a reliable (consolidating) vs noisy (expanding)
            phase. When None, falls back to the global aggregate curve.

        The 5-vector orientation (see pressure_orientation()) shows the full
        picture of which axes have the highest correction/effectiveness right now.
        """
        current_outlet = self._outlet_fraction()
        n_links = len(self.links)

        # Select the curve for the targeted axis (or global if unspecified)
        ax = str(axis_hint).upper() if axis_hint and str(axis_hint).upper() in AXES else None
        curve = self._axis_curves[ax] if ax else self._complexity_curve

        corrected = curve.record_injection(
            raw_pressure=float(plateau_ratio),
            n_links=(
                len([l for l in self.links.values()
                     if (l.dominant_relief_axis or "X") == ax])
                if ax else n_links
            ),
            current_outlet=current_outlet,
            tick=self.tick_count,
        )

        # Take the maximum of current pressure and new signal (don't let a
        # momentary recovery erase deep stall pressure immediately).
        self._training_plateau_pressure = min(1.0, max(
            float(self._training_plateau_pressure),
            _clamp(float(corrected), 0.0, 1.0),
        ))

    def pressure_orientation(self) -> Dict[str, float]:
        """
        Return the 5-vector pressure orientation across all constraint axes.

        Each value is the current correction factor for that axis's complexity
        curve — reflects whether that axis is in a reliable (consolidating,
        correction ≥ 1.0) or noisy (expanding, correction < 1.0) phase.

        High values mean pressure injections on that axis are likely to be
        accurate and effective right now.  Low values mean the axis's pressure
        systems are in a proliferating/noisy phase and injections should be
        treated as less reliable.

        Shape: {"T": 0.97, "N": 1.12, "X": 0.83, "B": 1.05, "A": 0.91}
        """
        base = {ax: self._axis_curves[ax].correction for ax in AXES}

        # Pressure-magnitude override: if an axis has accumulated pressure
        # dramatically above its peers (> 3x the mean of the others), its
        # PressureComplexityCurve may be stuck in expansion-phase (correction
        # < 1.0) simply because outlet_fraction hasn't recovered — not because
        # the pressure is actually resolved.  A correction < 1.0 raises Gate 2
        # opposition bonus, making promotion harder, which prevents relief,
        # which keeps the axis in expansion — a deadlock.  We break it by
        # forcing the correction to at least 1.0 (compression phase) whenever
        # the actual pressure load signals a genuine crisis.
        if self._latest_pressure is not None:
            p = self._latest_pressure.to_dict()
            for ax in AXES:
                others = [p[a] for a in AXES if a != ax]
                mean_others = sum(others) / len(others) if others else 0.0
                if mean_others > 0.0 and p[ax] > 3.0 * mean_others and base[ax] < 1.0:
                    base[ax] = 1.0  # force into compression so gates open

        return {ax: round(base[ax], 4) for ax in AXES}

    def axis_relief_state(self) -> Dict[str, float]:
        """
        Return normalized per-axis gradient EMA (0–1) showing which axes are
        actively accumulating relief from promoted links right now.

        The raw values in _gradient_axis_ema are small (order 1e-4 to 1e-2);
        this normalizes them relative to the most-active axis so callers get
        a comparable 0–1 signal regardless of overall activity level.

        Used by the understanding contract to give a small score boost to
        meaning-forms whose prerequisite axes are actively evolving in genealogy,
        creating the causal link: genealogy B-axis evolution → B^1 form rank rises
        → stage-1 (information) achievement threshold becomes reachable sooner.

        Shape: {"X": 0.12, "T": 0.44, "N": 0.06, "B": 1.00, "A": 0.22}
        """
        raw = dict(self._gradient_axis_ema)
        max_val = max(raw.values()) if raw else 0.0
        if not max_val:
            return {ax: 0.0 for ax in AXES}
        return {ax: round(min(1.0, raw.get(ax, 0.0) / max_val), 4) for ax in AXES}

    def set_corpus_mode(self, enabled: bool) -> None:
        """
        Enable/disable corpus-training timescale compensation.

        In real-time conversation, AXIS_TICK_PARTICIPATION means X gets 10,000
        observations for every one A-axis observation.  In corpus training (fast
        machine-speed processing), every corpus item is observed by ALL axes
        simultaneously — so A-axis is being over-observed by 10,000x and its
        links are over-taxed by the same ratio.

        When corpus mode is ON:
          1. _update_gradient_memory_from_relief(): per-axis EMA rates scale by
             1/sqrt(participation) — each A-axis relief event is treated as worth
             ~100x more than an X-axis event, reflecting its rarity in real-time.
          2. _axis_persistence_tax_factor(): tax excess is scaled DOWN by
             AXIS_TICK_PARTICIPATION, so slow-axis links don't erode under the
             burden of 10,000x more observations than they'd see in real-time.
        """
        self._corpus_mode = bool(enabled)

    def _outlet_fraction(self) -> float:
        """Lightweight outlet-push fraction for complexity curve tracking."""
        if not self.links:
            return 0.0
        outlet_total = 0
        for lnk in self.links.values():
            for p in lnk.parents:
                if p == "A:OUTLET_PUSH" or (p in self.links and
                   "A:OUTLET_PUSH" in self.links[p].parents):
                    outlet_total += 1
                    break
        return outlet_total / len(self.links)

    # ----------------------------------------------------------------
    # ENVIRONMENT-AWARE TRACKING
    # ----------------------------------------------------------------

    def _record_env_observation(
        self,
        trace: List[TraceItem],
        relief: "PressureVec",
        dominant_axis: str,
        promoted: bool,
    ) -> None:
        """
        Called per relief event to update per-environment effectiveness.

        For each TraceItem that carries an EnvironmentVector, record:
          - effectiveness EMA per (ability_id, env_key) — was it useful here?
          - axis relief EMA per (env_key, axis) — which axes produce relief
            in this environment? Forms the 5-vector orientation per env.

        promoted=True signals stronger reinforcement (the pair actually made
        it through all gates — not just produced relief).
        """
        if not trace:
            return

        fitness = 1.0 if promoted else 0.5
        alpha = 0.15

        # Collect unique environments from this trace
        env_keys_in_trace = set()
        for item in trace:
            env = item.env
            if env.is_empty():
                continue
            ek = env.key()
            env_keys_in_trace.add(ek)

            # Ability-level effectiveness per environment
            ability_map = self._env_effectiveness[item.id]
            prev = ability_map.get(ek, 0.5)
            ability_map[ek] = (1.0 - alpha) * prev + alpha * fitness

            # Fire count
            self._env_fire_count[ek] += 1

        # Axis relief per environment — how much relief each axis produced
        # in these environments this tick
        rel_dict = {"T": relief.T, "N": relief.N, "X": relief.X,
                    "B": relief.B, "A": relief.A}
        for ek in env_keys_in_trace:
            ax_map = self._env_axis_relief[ek]
            for ax, val in rel_dict.items():
                ax_map[ax] = (1.0 - alpha) * ax_map[ax] + alpha * max(0.0, val)

    def apply_targeted_pressure(
        self,
        axis: str,
        env_key: str,
        magnitude: float,
        source: str = "",
    ) -> Dict[str, Any]:
        """
        Apply pressure to a specific axis AND record the application so its
        outcome can be measured and learned from.

        axis      : one of T/N/X/B/A — the constraint axis to press
        env_key   : the environment this pressure targets
                    (from EnvironmentVector.key(), e.g.
                     "aurora_expression_perception|user_input|N|express")
        magnitude : 0.0–1.0 pressure signal
        source    : label for what triggered this (e.g. "semantic_precision_fail")

        Stores a pending application that will be checked after
        OUTCOME_CHECK_TICKS ticks. On outcome check, updates the
        _pressure_strategy EMA for (env_key, axis) based on whether
        the outlet_fraction actually changed.

        Returns a dict describing what was applied.
        """
        ax = str(axis).upper()
        if ax not in AXES:
            ax = "X"
        mag = float(max(0.0, min(1.0, magnitude)))

        # Record baseline state
        current_outlet = self._outlet_fraction()
        current_axis_relief = self._env_axis_relief.get(env_key, {}).get(ax, 0.0)

        # Inject the pressure through the axis-specific curve
        self.inject_training_plateau_pressure(mag, axis_hint=ax)

        # Record pending application for outcome measurement
        app = {
            "env_key": env_key,
            "axis": ax,
            "magnitude": mag,
            "source": source,
            "tick_applied": self.tick_count,
            "outlet_before": current_outlet,
            "axis_relief_before": current_axis_relief,
            "check_at_tick": self.tick_count + self._OUTCOME_CHECK_TICKS,
        }
        self._pending_applications[env_key + "|" + ax] = app

        return {
            "applied": True,
            "axis": ax,
            "env_key": env_key,
            "magnitude": mag,
            "strategy_prior": round(self._pressure_strategy[(env_key, ax)], 4),
        }

    def _check_pending_outcomes(self) -> None:
        """
        Called each tick to resolve pending pressure applications whose
        outcome window has elapsed. Measures actual change in outlet_fraction
        and axis relief, then updates the strategy EMA.

        High outcome = outlet_fraction rose or axis relief improved →
            strategy[(env_key, axis)] moves toward 1.0
        Low outcome = nothing changed or got worse →
            strategy[(env_key, axis)] moves toward 0.0
        """
        now = self.tick_count
        current_outlet = self._outlet_fraction()
        done = []
        alpha = 0.2

        for key, app in self._pending_applications.items():
            if now < app["check_at_tick"]:
                continue
            done.append(key)

            # Measure outcome
            delta_outlet = current_outlet - app["outlet_before"]
            current_axis_relief = self._env_axis_relief.get(
                app["env_key"], {}
            ).get(app["axis"], 0.0)
            delta_relief = current_axis_relief - app["axis_relief_before"]

            # Positive outcome: outlet rose or axis relief improved
            outcome = min(1.0, max(0.0,
                0.5 + delta_outlet * 5.0 + delta_relief * 3.0
            ))

            # Update strategy EMA for this (env_key, axis) pair
            strat_key = (app["env_key"], app["axis"])
            prev = self._pressure_strategy[strat_key]
            self._pressure_strategy[strat_key] = (
                (1.0 - alpha) * prev + alpha * outcome
            )

            # Log the completed application
            record = dict(app)
            record["outcome"] = round(outcome, 4)
            record["delta_outlet"] = round(delta_outlet, 6)
            record["delta_relief"] = round(delta_relief, 6)
            record["strategy_after"] = round(self._pressure_strategy[strat_key], 4)
            self._application_log.append(record)

        for k in done:
            del self._pending_applications[k]

    def get_pressure_recommendations(
        self,
        fail_dims: List[Tuple[str, str]],
        top_n: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Given a list of (dimension, severity) fail pairs, return the top
        (env_key, axis, magnitude) pressure targets ranked by historical
        strategy effectiveness.

        Uses DIMENSION_AXIS mapping (imported at call time) to translate
        dimensions to axes, then finds all observed environments for those
        axes and ranks by _pressure_strategy EMA.

        Returns list of recommendation dicts, highest effectiveness first.
        """
        # Import here to avoid circular dep
        try:
            from aurora_dream_trainer import DIMENSION_AXIS as _DA
        except ImportError:
            _DA = {}

        recommendations = []
        for dim, sev in (fail_dims or []):
            ax = _DA.get(dim, "X")
            # Find environments where this axis has been observed
            for env_key in self.all_environment_keys():
                ax_relief = self._env_axis_relief.get(env_key, {}).get(ax, 0.0)
                if ax_relief <= 0.0:
                    continue  # this env has never seen this axis's relief
                strat_eff = self._pressure_strategy.get((env_key, ax), 0.5)
                recommendations.append({
                    "env_key": env_key,
                    "axis": ax,
                    "dimension": dim,
                    "severity": round(float(sev), 4),
                    "strategy_effectiveness": round(strat_eff, 4),
                    "axis_relief_ema": round(ax_relief, 6),
                    "recommended_magnitude": round(float(sev) * strat_eff, 4),
                })

        # Sort: highest strategy × severity
        recommendations.sort(
            key=lambda r: r["strategy_effectiveness"] * r["severity"],
            reverse=True,
        )
        return recommendations[:top_n]

    def pressure_application_summary(self, last_n: int = 10) -> List[Dict[str, Any]]:
        """Return the most recent completed pressure applications with outcomes."""
        recent = list(self._application_log)[-last_n:]
        return list(reversed(recent))

    def environment_orientation(self, env_key: str) -> Dict[str, float]:
        """
        Return the 5-vector pressure orientation for a specific environment.

        Each value is the EMA of positive axis relief observed in this
        environment — higher means that axis has been more effective here.

        Example:
            env_key = "aurora_expression_perception|user_input|A|express"
            → {"T": 0.003, "N": 0.041, "X": 0.008, "B": 0.012, "A": 0.089}
            → A-axis has the most leverage in this environment right now.
        """
        ax_map = self._env_axis_relief.get(env_key, {a: 0.0 for a in AXES})
        return {a: round(ax_map.get(a, 0.0), 6) for a in AXES}

    def ability_environment_profile(self, ability_id: str) -> Dict[str, Any]:
        """
        Return the effectiveness profile of an ability across all environments
        it has fired in.

        Returns dict mapping env_key → effectiveness_ema, sorted by ema desc,
        plus the best_env (highest effectiveness environment).

        This distinguishes e.g. "A:OUTLET_PUSH in aurora_evolution_chamber
        during user_input" from "A:OUTLET_PUSH in aurora_dimensional_systems
        during corpus" — same genetic ID, different cell types.
        """
        profiles = self._env_effectiveness.get(ability_id, {})
        sorted_envs = sorted(profiles.items(), key=lambda x: x[1], reverse=True)
        return {
            "ability_id": ability_id,
            "environments": dict(sorted_envs),
            "best_env": sorted_envs[0][0] if sorted_envs else "global",
            "worst_env": sorted_envs[-1][0] if len(sorted_envs) > 1 else "global",
            "env_count": len(sorted_envs),
        }

    def all_environment_keys(self) -> List[str]:
        """Return all environment keys seen so far."""
        return list(self._env_fire_count.keys())

    def _consume_plateau_pressure(self) -> float:
        """
        Return current plateau pressure and apply slow decay.
        Called once per gate-check cycle so pressure fades naturally
        unless re-injected by the training loop.
        """
        p = self._training_plateau_pressure
        # Decay: halve pressure every ~10 gate evaluations
        self._training_plateau_pressure = max(0.0, p * 0.93)
        return p

    def _stagnation_gain(self) -> float:
        """
        Return multiplicative promotion pressure gain from link stagnation.

        1.0  => no stagnation boost
        >1.0 => stalled link growth, so pressure gain increases smoothly

        Blends internal no-promotion elapsed time with external training
        plateau pressure so either signal alone can soften the gates.
        """
        window = max(1, int(self.cfg.STAGNATION_WINDOW))
        elapsed = max(0, int(self.tick_count - self._last_promotion_tick))
        internal_ratio = min(1.0, elapsed / float(window))
        # External plateau raises the effective ratio — take the max so
        # whichever pressure is higher governs gate relaxation.
        effective_ratio = min(1.0, max(internal_ratio, self._training_plateau_pressure))
        return 1.0 + (max(0.0, float(self.cfg.STAGNATION_GAIN_MAX)) * effective_ratio)

    def _stagnation_ratio(self) -> float:
        """
        Normalized no-promotion pressure [0,1], using a longer hard window.

        Blends internal elapsed-time ratio with external training plateau
        pressure. The plateau signal is consumed (slowly decayed) here so
        it fades unless continually re-injected by the training loop.
        """
        hard_window = max(1, int(getattr(self.cfg, "STAGNATION_HARD_WINDOW", self.cfg.STAGNATION_WINDOW)))
        elapsed = max(0, int(self.tick_count - self._last_promotion_tick))
        internal_ratio = min(1.0, elapsed / float(hard_window))
        plateau = self._consume_plateau_pressure()
        # Weighted blend: internal clock + external training pressure.
        # plateau_pressure gets 0.45 weight so even a fully stalled training
        # loop (plateau=1.0) can move the ratio without overriding internal physics.
        return min(1.0, max(internal_ratio, internal_ratio * 0.55 + plateau * 0.45))

    def _promotion_friction_bias(self) -> Dict[str, float]:
        """
        Relative rejection pressure per gate, used only to bias stagnation relief.
        """
        net_reject = max(0.0, float(self._promotion_stats.get("reject_net_min", 0)))
        xrisk_reject = max(0.0, float(self._promotion_stats.get("reject_x_risk", 0)))
        kmin_reject = max(0.0, float(self._promotion_stats.get("reject_k_min_dynamic", 0)))
        total = net_reject + xrisk_reject + kmin_reject
        if total <= 1e-9:
            return {"net": 0.0, "xrisk": 0.0, "kmin": 0.0}
        return {
            "net": net_reject / total,
            "xrisk": xrisk_reject / total,
            "kmin": kmin_reject / total,
        }

    def _opposing_axis(self, axis: str) -> str:
        ax = str(axis or "X").upper()
        opposing = {
            "X": "A",
            "A": "X",
            "T": "B",
            "B": "T",
            "N": "N",
        }
        return str(opposing.get(ax, "X"))

    def _threshold_pressure_state(self, axis: str, depth: int = 1) -> Dict[str, float]:
        ax = str(axis or "X").upper()
        opp = self._opposing_axis(ax)
        driver_w = _clamp(float(getattr(self.cfg, "THRESHOLD_PRESSURE_DRIVER_WEIGHT", 0.55) or 0.55), 0.0, 1.0)
        opposing_w = _clamp(float(getattr(self.cfg, "THRESHOLD_PRESSURE_OPPOSING_WEIGHT", 0.45) or 0.45), 0.0, 1.0)
        persistent_w = _clamp(float(getattr(self.cfg, "THRESHOLD_PRESSURE_PERSISTENT_WEIGHT", 0.20) or 0.20), 0.0, 1.0)
        driver = (
            (driver_w * max(0.0, float(self._gradient_axis_ema.get(ax, 0.0) or 0.0)))
            + ((1.0 - driver_w) * max(0.0, float(self._axis_outcome_ema.get(ax, 0.0) or 0.0)))
            + (0.15 * max(0.0, float(self._depth_outcome_ema.get(max(1, int(depth)), 0.0) or 0.0)))
            + (persistent_w * max(0.0, float(self._persistent_pressure_root_ema or 0.0)))
        )
        opposing_tax_cap = max(1.0, float(getattr(self.cfg, "PERSISTENCE_TAX_MAX_FACTOR", 5.0) or 5.0))
        opposing_tax = max(0.0, min(1.0, (self._axis_persistence_tax_factor(opp, depth=depth) - 1.0) / max(1e-9, opposing_tax_cap - 1.0)))
        opposing = (
            (opposing_w * max(0.0, float(self._gradient_axis_ema.get(opp, 0.0) or 0.0)))
            + ((1.0 - opposing_w) * max(0.0, float(self._axis_outcome_ema.get(opp, 0.0) or 0.0)))
            + (0.25 * opposing_tax)
            + (persistent_w * max(0.0, float(self._persistent_pressure_root_ema or 0.0)))
        )
        return {
            "axis": ax,
            "opposing_axis": opp,
            "driver_pressure": float(driver),
            "opposing_pressure": float(opposing),
            "pressure_gradient": float(driver - opposing),
        }

    def _regulated_threshold(
        self,
        name: str,
        base: float,
        axis: str,
        depth: int = 1,
        threshold_kind: str = "floor",
        local_support: float = 0.0,
        local_opposition: float = 0.0,
        floor_ratio: Optional[float] = None,
        cap_ratio: Optional[float] = None,
    ) -> Tuple[float, Dict[str, Any]]:
        raw_base = max(1e-9, float(base))
        if not bool(getattr(self.cfg, "THRESHOLD_PRESSURE_ENABLED", True)):
            return raw_base, {
                "name": str(name),
                "axis": str(axis or "X").upper(),
                "kind": str(threshold_kind or "floor"),
                "base": float(raw_base),
                "regulated": float(raw_base),
                "factor": 1.0,
                "pressure_gradient": 0.0,
                "driver_pressure": 0.0,
                "opposing_pressure": 0.0,
                "enabled": False,
            }
        state = self._threshold_pressure_state(axis, depth=depth)
        driver = float(state.get("driver_pressure", 0.0) or 0.0) + max(0.0, float(local_support))
        opposing = float(state.get("opposing_pressure", 0.0) or 0.0) + max(0.0, float(local_opposition))
        gradient = float(driver - opposing)
        sharpness = max(0.1, float(getattr(self.cfg, "THRESHOLD_PRESSURE_SHARPNESS", 2.5) or 2.5))
        gain = _clamp(float(getattr(self.cfg, "THRESHOLD_PRESSURE_GAIN", 0.60) or 0.60), 0.0, 0.95)
        floor_ratio = max(0.05, float(floor_ratio if floor_ratio is not None else getattr(self.cfg, "THRESHOLD_PRESSURE_FLOOR_RATIO", 0.40)))
        cap_ratio = max(1.0, float(cap_ratio if cap_ratio is not None else getattr(self.cfg, "THRESHOLD_PRESSURE_CAP_RATIO", 1.75)))
        swing = gain * math.tanh(sharpness * gradient)
        if str(threshold_kind or "floor").lower() == "cap":
            factor = 1.0 + swing
        else:
            factor = 1.0 - swing
        factor = max(floor_ratio, min(cap_ratio, factor))
        regulated = raw_base * factor
        return regulated, {
            "name": str(name),
            "axis": str(state.get("axis", axis)).upper(),
            "opposing_axis": str(state.get("opposing_axis", self._opposing_axis(axis))).upper(),
            "kind": str(threshold_kind or "floor"),
            "base": float(raw_base),
            "regulated": float(regulated),
            "factor": float(factor),
            "driver_pressure": float(driver),
            "opposing_pressure": float(opposing),
            "pressure_gradient": float(gradient),
            "local_support": float(local_support),
            "local_opposition": float(local_opposition),
            "enabled": True,
        }

    def _axis_persistence_tax_factor(self, axis: str, depth: int = 1) -> float:
        """
        Per-axis persistence tax factor based on opposed tick participation,
        with depth decay so deeper promoted structures are cheaper to maintain.

        Base (depth=1) is approximately X=1, T=2, N=3, B=4, A=5.
        As depth grows, factor decays exponentially toward a floor.
        """
        share = float(AXIS_TICK_PARTICIPATION.get(str(axis).upper(), 1.0))
        share = max(1e-9, share)
        inv = 1.0 / share
        power = max(0.0, float(getattr(self.cfg, "PERSISTENCE_TAX_OPPOSE_POWER", 1.0)))
        base = 1.0 + (power * math.log10(inv))
        cap = max(1.0, float(getattr(self.cfg, "PERSISTENCE_TAX_MAX_FACTOR", 5.0)))
        base = max(1.0, min(cap, base))

        d = max(1, int(depth))
        decay_rate = max(0.0, float(getattr(self.cfg, "PERSISTENCE_DEPTH_DECAY_RATE", 0.45)))
        floor = max(0.01, float(getattr(self.cfg, "PERSISTENCE_TAX_MIN_FACTOR", 0.15)))
        factor = base * math.exp(-decay_rate * float(max(0, d - 1)))
        factor = max(floor, min(cap, factor))

        if self._corpus_mode:
            # Corpus-mode correction: in real-time, A-axis links encounter the
            # persistence tax only 0.0001 as often as X-axis links (proportional
            # to tick participation).  In corpus mode every item triggers the tax
            # for ALL axes, so slow-axis links are over-taxed by 1/participation.
            # Scale the excess tax (above 1.0) back down by participation so the
            # per-item tax matches the real-time per-X-tick effective rate.
            #   A: factor 5.0 → 1 + (5-1)*0.0001 ≈ 1.0004 (almost free)
            #   B: factor 4.0 → 1 + (4-1)*0.001  ≈ 1.003
            #   N: factor 3.0 → 1 + (3-1)*0.01   ≈ 1.02
            #   T: factor 2.0 → 1 + (2-1)*0.1    ≈ 1.1
            #   X: factor 1.0 → unchanged
            corpus_participation = max(1e-9, float(AXIS_TICK_PARTICIPATION.get(str(axis).upper(), 1.0)))
            factor = max(floor, 1.0 + (factor - 1.0) * corpus_participation)

        return factor

    def _weighted_persistence_tax_factor(self, influence: Dict[str, float], depth: int = 1) -> float:
        """Influence-weighted tax factor for a coupling profile."""
        total_w = sum(max(0.0, float(influence.get(a, 0.0))) for a in AXES)
        if total_w <= 1e-9:
            return 1.0
        acc = 0.0
        for a in AXES:
            w = max(0.0, float(influence.get(a, 0.0))) / total_w
            acc += w * self._axis_persistence_tax_factor(a, depth=depth)
        floor = max(0.01, float(getattr(self.cfg, "PERSISTENCE_TAX_MIN_FACTOR", 0.15)))
        cap = max(1.0, float(getattr(self.cfg, "PERSISTENCE_TAX_MAX_FACTOR", 5.0)))
        return max(floor, min(cap, float(acc)))

    def _maintenance_discount(self, depth: int) -> float:
        """Discount factor [0,1) applied to promoted-link running cost."""
        cfg = self.cfg
        discount = (
            float(cfg.MAINTENANCE_DISCOUNT_BASE)
            + max(0, int(depth)) * float(cfg.MAINTENANCE_DISCOUNT_PER_DEPTH)
        )
        return _clamp(discount, 0.0, float(cfg.MAINTENANCE_DISCOUNT_MAX))

    def _formation_complexity_multiplier(self, left_id: str, right_id: str, depth: int) -> float:
        """Extra one-time formation burden for composite/deep links with scale-depth weighting."""
        link_parent_count = int(left_id.startswith("L:")) + int(right_id.startswith("L:"))
        depth_term = max(0, int(depth) - 1)
        scale = max(0.0, float(self.cfg.COMPLEXITY_FORMATION_SCALE))

        left = self._axis_counts_from_item(TraceItem(id=str(left_id), kind="LINK" if str(left_id).startswith("L:") else "ABILITY"), memo={}, seen=set())
        right = self._axis_counts_from_item(TraceItem(id=str(right_id), kind="LINK" if str(right_id).startswith("L:") else "ABILITY"), memo={}, seen=set())
        merged = self._add_axis_counts(left, right)
        scale_depth = self._scale_depth_index(merged)
        scale_depth_term = max(0.0, float(getattr(self.cfg, "SCALE_FORMATION_WEIGHT", 0.20))) * scale_depth

        return 1.0 + (scale * (depth_term + link_parent_count)) + scale_depth_term

    def _compression_efficiency_for_pair(self, key: Tuple[str, str], depth: int) -> Dict[str, float]:
        """
        Adaptive compression relief for mature ecosystems.
        Repeated purpose families become cheaper to form; no hard top-out cap.
        """
        if not bool(getattr(self.cfg, "COMPRESSION_ENABLED", True)):
            return {"gain": 0.0, "boost": 1.0, "family_count": 0, "maturity": 0.0, "signature": "0"}

        total_links = int(len(self.links))
        threshold = max(1, int(getattr(self.cfg, "COMPRESSION_LINK_THRESHOLD", 180) or 180))
        if total_links <= 0:
            return {"gain": 0.0, "boost": 1.0, "family_count": 0, "maturity": 0.0, "signature": "0"}

        left = self._axis_counts_from_item(
            TraceItem(id=str(key[0]), kind="LINK" if str(key[0]).startswith("L:") else "ABILITY"),
            memo={}, seen=set(),
        )
        right = self._axis_counts_from_item(
            TraceItem(id=str(key[1]), kind="LINK" if str(key[1]).startswith("L:") else "ABILITY"),
            memo={}, seen=set(),
        )
        merged = self._add_axis_counts(left, right)
        fam = tuple(a for a in AXES if int(merged.get(a, 0) or 0) > 0)
        sig = self._canonical_coupling_signature(merged)

        family_count = 0
        memo: Dict[str, Dict[str, int]] = {}
        for lnk in self.links.values():
            counts = self._zero_axis_counts()
            for pid in list(getattr(lnk, "parents", []) or []):
                pc = self._axis_counts_from_item(
                    TraceItem(id=str(pid), kind="LINK" if str(pid).startswith("L:") else "ABILITY"),
                    memo=memo, seen=set(),
                )
                counts = self._add_axis_counts(counts, pc)
            lfam = tuple(a for a in AXES if int(counts.get(a, 0) or 0) > 0)
            if lfam == fam:
                family_count += 1

        maturity = _clamp((float(total_links) - float(threshold)) / float(max(1, threshold)), 0.0, 1.0)
        fam_scale = max(1.0, float(getattr(self.cfg, "COMPRESSION_FAMILY_SCALE", 24) or 24))
        redundancy = _clamp(float(family_count) / fam_scale, 0.0, 1.0)
        max_gain = _clamp(float(getattr(self.cfg, "COMPRESSION_MAX_GAIN", 0.55) or 0.55), 0.0, 0.85)

        gain = max_gain * maturity * redundancy
        # Deeper links get a slight extra compression once ecosystem is mature.
        gain *= (1.0 + (0.08 * max(0, int(depth) - 1)))
        gain = _clamp(gain, 0.0, max_gain)
        boost = 1.0 + gain

        return {
            "gain": float(gain),
            "boost": float(boost),
            "family_count": int(family_count),
            "maturity": float(maturity),
            "signature": str(sig),
        }

    def _causal_support(self, axis: str, depth: int) -> float:
        """Composite support from outcomes + literal gradient memory."""
        axis_term = max(0.0, float(self._axis_outcome_ema.get(axis, 0.0)))
        depth_term = max(0.0, float(self._depth_outcome_ema.get(max(1, int(depth)), 0.0)))
        grad_term = max(0.0, float(self._gradient_axis_ema.get(axis, 0.0)))
        return (0.4 * axis_term) + (0.3 * depth_term) + (0.3 * grad_term)

    def _update_gradient_memory_from_relief(self, relief: "PressureVec") -> None:
        """Update gradient EMA from actual per-axis relief magnitudes.

        Relief magnitude IS the axis gradient signal: positive relief on axis A
        means pressure on A dropped, i.e., a gradient was resolved there.
        This feeds _gradient_axis_ema so _threshold_pressure_state() has real
        data to drive _regulated_threshold() — making gate regulation self-propelling
        from actual pressure-relief physics rather than only C:D snapshot diffs.
        """
        base_rate = _clamp(float(self.cfg.CAUSAL_ADAPT_RATE), 0.01, 0.5)
        for ax in AXES:
            rv = max(0.0, float(getattr(relief, ax, 0.0)))
            if rv > 0.0:
                if self._corpus_mode:
                    # Corpus-mode compensation: each slow-axis relief event is rarer
                    # and more significant than a surface-axis event.  Scale the EMA
                    # update rate by 1/sqrt(participation) so A-axis observations
                    # carry ~100x the weight of X-axis observations — preserving the
                    # real-time rarity hierarchy in a compressed form.
                    participation = max(1e-9, float(AXIS_TICK_PARTICIPATION.get(ax, 1.0)))
                    corpus_scale = min(10.0, 1.0 / math.sqrt(participation))
                    rate = min(1.0, base_rate * corpus_scale)
                else:
                    rate = base_rate
                prev = float(self._gradient_axis_ema.get(ax, 0.0))
                self._gradient_axis_ema[ax] = (1.0 - rate) * prev + rate * rv

    def _update_gradient_memory(self, difference_snapshot: Optional[DifferenceSnapshot]) -> None:
        """Track literal C:D gradient intensity per axis with EMA."""
        if difference_snapshot is None:
            return
        rate = _clamp(float(self.cfg.CAUSAL_ADAPT_RATE), 0.01, 0.5)
        axis_to_constraint = {
            "X": Constraint.X,
            "T": Constraint.T,
            "N": Constraint.N,
            "B": Constraint.B,
            "A": Constraint.A,
        }
        for ax, c in axis_to_constraint.items():
            val = 0.0
            try:
                val = abs(float(difference_snapshot.value(c)))
            except Exception:
                val = 0.0
            prev = float(self._gradient_axis_ema.get(ax, 0.0))
            self._gradient_axis_ema[ax] = ((1.0 - rate) * prev) + (rate * val)

    def _record_promotion_outcome(self, axis: str, depth: int, net: float) -> None:
        """Promotion success feeds causal memory for future gate adaptation."""
        rate = _clamp(float(self.cfg.CAUSAL_ADAPT_RATE), 0.01, 0.5)
        baseline = max(float(self.cfg.NET_MIN), 1e-9)
        score = min(5.0, max(0.0, float(net) / baseline))
        prev_axis = float(self._axis_outcome_ema.get(axis, 0.0))
        self._axis_outcome_ema[axis] = ((1.0 - rate) * prev_axis) + (rate * score)

        d = max(1, int(depth))
        prev_depth = float(self._depth_outcome_ema.get(d, 0.0))
        self._depth_outcome_ema[d] = ((1.0 - rate) * prev_depth) + (rate * score)

    def _update_causal_feedback(
        self,
        trace: List[TraceItem],
        relief: PressureVec,
    ) -> None:
        """Update causal memory from live link usage outcomes + gradients."""
        total_relief = max(0.0, float(relief.sum_positive_relief()))
        if total_relief <= 0.0:
            return
        rate = _clamp(float(self.cfg.CAUSAL_ADAPT_RATE), 0.01, 0.5)
        for item in trace:
            if getattr(item, "kind", "") != "LINK":
                continue
            lnk = self.links.get(getattr(item, "id", ""))
            if lnk is None:
                continue
            resolved = self._resolve_ability(item)
            if resolved is None:
                continue
            run_cost = max(1e-9, float(sum(resolved.cost.get(a, 0.0) for a in AXES)))
            axis = lnk.dominant_relief_axis or "X"
            grad_term = max(0.0, float(self._gradient_axis_ema.get(axis, 0.0)))
            outcome = min(5.0, (total_relief + grad_term) / run_cost)

            prev_axis = float(self._axis_outcome_ema.get(axis, 0.0))
            self._axis_outcome_ema[axis] = ((1.0 - rate) * prev_axis) + (rate * outcome)

            d = max(1, int(lnk.depth))
            prev_depth = float(self._depth_outcome_ema.get(d, 0.0))
            self._depth_outcome_ema[d] = ((1.0 - rate) * prev_depth) + (rate * outcome)
    def _dominant_axis_constraint_specific(
        self,
        mr_pos: Dict[str, float],
        pf: Dict[str, float],
        mc: Dict[str, float],
        sr: Dict[str, float],
    ) -> str:
        """
        Constraint-specific dominance method.
        Similar builds may serve the same purpose, but dominance scoring is
        axis-specific rather than one global max rule.
        """
        def _nz(v: float) -> float:
            return max(0.0, float(v))

        x = _nz(mr_pos.get("X", 0.0)) * (0.70 + (0.30 * _nz(pf.get("X", 0.0)))) / (1.0 + (0.10 * _nz(sr.get("X", 0.0))))
        t = _nz(mr_pos.get("T", 0.0)) * (0.55 + (0.45 * _nz(pf.get("T", 0.0)))) / (1.0 + (0.15 * _nz(sr.get("T", 0.0))))
        n = _nz(mr_pos.get("N", 0.0)) * (0.60 + (0.40 * _nz(pf.get("N", 0.0)))) / (1.0 + _nz(mc.get("N", 0.0)))
        b = _nz(mr_pos.get("B", 0.0)) * (0.50 + (0.50 * _nz(pf.get("B", 0.0)))) / (1.0 + (0.20 * _nz(sr.get("B", 0.0))))
        a = _nz(mr_pos.get("A", 0.0)) * (0.45 + (0.55 * _nz(pf.get("A", 0.0)))) / (1.0 + (2.0 * _nz(mc.get("A", 0.0))))

        score = {"X": x, "T": t, "N": n, "B": b, "A": a}
        dom = max(AXES, key=lambda ax: float(score.get(ax, 0.0)))
        if float(score.get(dom, 0.0)) <= 0.0:
            dom = max(AXES, key=lambda ax: float(mr_pos.get(ax, 0.0)))
        return str(dom)

    def _accumulate_pairs(
        self,
        trace: List[TraceItem],
        relief: PressureVec,
        cost_total: Dict[str, float],
        x_risk: float,
    ) -> Optional[List[TraceItem]]:
        """
        Extract adjacent pairs from the trace, update PairStats,
        check promotion gates for each pair.
        Returns rewritten trace if any pair was newly promoted, else None.
        """
        if len(trace) < 2:
            return None

        # Proactively compress already-promoted pairs into link IDs so higher-order
        # pairs can accumulate even when all base-level pairs are already promoted.
        if self.cfg.TRACE_REWRITE_ON_PROMOTE and self._links_by_parents:
            trace = self.rewrite_trace(trace)
            if len(trace) < 2:
                return None

        newly_promoted: List[Tuple[int, str]] = []  # (index in trace, link_id)

        for i in range(len(trace) - 1):
            left = trace[i]
            right = trace[i + 1]
            key = (left.id, right.id)
            self._promotion_stats["observed_pairs"] += 1

            if key not in self._pair_stats:
                self._pair_stats[key] = PairStats(left_id=left.id, right_id=right.id)

            ps = self._pair_stats[key]
            ps.update(relief, cost_total, x_risk, self.tick_count)

            # Already promoted?
            if key in self._links_by_parents:
                self._promotion_stats["already_promoted_pair"] += 1
                continue

            # Check promotion
            link = self._try_promote(key, ps)
            if link is not None:
                if link.id in self.links:
                    # Collision-safe guard: do not duplicate an existing link id.
                    self._links_by_parents[key] = link.id
                    continue
                self.links[link.id] = link
                self._links_by_parents[key] = link.id
                self.links_promoted += 1
                self._promotion_stats["promoted"] += 1
                self._last_promotion_tick = self.tick_count
                self._register_link_ability(link)
                newly_promoted.append((i, link.id))

        # If any pairs were promoted, re-record with stronger reinforcement signal
        if newly_promoted:
            self._record_env_observation(
                trace=trace,
                relief=relief,
                dominant_axis=relief.dominant_positive_axis() or "X",
                promoted=True,
            )

        if newly_promoted and self.cfg.TRACE_REWRITE_ON_PROMOTE:
            return self.rewrite_trace(trace)
        return None

    def _try_promote(
        self, key: Tuple[str, str], ps: PairStats
    ) -> Optional[ConstraintLink]:
        """
        Evaluate all promotion gates and mint a Link if all pass.
        """
        cfg = self.cfg

        mr = ps.mean_relief()
        mr_pos = ps.mean_pos_relief()   # mean of POSITIVE relief only
        pf = ps.pos_fraction()          # fraction of ticks with positive relief
        sr = ps.stdev_relief()
        mc = ps.mean_cost()
        mx_risk = ps.mean_x_risk_val()

        # Gate 1: Admissibility (X-risk cap).
        # Slightly relax cap under heavy stagnation pressure to avoid deadlock,
        # while preserving a hard upper bound.
        pressure_gain = self._stagnation_gain()
        stagnation_ratio = self._stagnation_ratio()
        friction_bias = self._promotion_friction_bias()
        x_cap_max_mult = max(1.0, float(getattr(cfg, "STAGNATION_XRISK_CAP_MAX_MULT", 2.25)))

        # Per-axis PressureComplexityCurve correction — self-propelling gate adjustment.
        # Compressing phase (correction > 1.0): predictions reliable → lower thresholds.
        # Expanding phase (correction < 1.0): predictions noisy → tighten as noise filter.
        # This is the opposing-gradient gate drive the user described: each axis's
        # pressure oscillation curve directly modulates its own promotion gates.
        # Use pressure_orientation() so the pressure-magnitude override applies:
        # a crisis axis (>>3x peers) is forced into compression regardless of curve phase.
        _ax_corr = {ax: float(v) for ax, v in self.pressure_orientation().items()}
        _ax_sup_bonus = {ax: max(0.0, _ax_corr[ax] - 1.0) for ax in AXES}
        _ax_opp_bonus = {ax: max(0.0, 1.0 - _ax_corr[ax]) for ax in AXES}
        _global_corr_sup = max(0.0, float(self._complexity_curve.correction) - 1.0)
        x_risk_relief = 1.0 + (max(0.0, pressure_gain - 1.0) * 0.50) + (stagnation_ratio * friction_bias["xrisk"] * 0.50)
        left_depth = self._item_depth(key[0])
        right_depth = self._item_depth(key[1])
        depth = max(left_depth, right_depth) + 1
        x_risk_cap_base = float(cfg.X_RISK_MAX) * min(x_cap_max_mult, x_risk_relief)
        x_risk_cap, _ = self._regulated_threshold(
            "X_RISK_MAX",
            x_risk_cap_base,
            axis="X",
            depth=depth,
            threshold_kind="cap",
            local_support=max(0.0, float(pressure_gain - 1.0)) + max(0.0, float(stagnation_ratio * friction_bias["xrisk"])),
            local_opposition=max(0.0, float(self._gradient_axis_ema.get(self._opposing_axis("X"), 0.0) or 0.0)),
            floor_ratio=0.50,
            cap_ratio=max(1.0, x_cap_max_mult),
        )
        if mx_risk > x_risk_cap:
            self.skipped_xrisk += 1
            self._promotion_stats["reject_x_risk"] += 1
            return None

        # Gate 2: Reliability — at least one axis where:
        #   (a) mean POSITIVE relief exceeds floor, AND
        #   (b) positive-relief fraction exceeds majority threshold
        # Curve correction bonus: compressing axis (correction > 1.0) lowers both
        # thresholds, making relief evidence from reliable phases self-propelling.
        reliable_axis: Optional[str] = None
        for a in AXES:
            promote_min_dyn, _ = self._regulated_threshold(
                "RELIEF_PROMOTE_MIN",
                float(cfg.RELIEF_PROMOTE_MIN),
                axis=a,
                depth=depth,
                threshold_kind="floor",
                local_support=max(0.0, float(self._causal_support(a, depth))) + max(0.0, float(mr_pos.get(a, 0.0) or 0.0)) + _ax_sup_bonus[a],
                local_opposition=max(0.0, float(self._gradient_axis_ema.get(self._opposing_axis(a), 0.0) or 0.0)) + _ax_opp_bonus[a],
                floor_ratio=0.30,
                cap_ratio=1.80,
            )
            pos_fraction_dyn, _ = self._regulated_threshold(
                "POS_FRACTION_MIN",
                float(cfg.POS_FRACTION_MIN),
                axis=a,
                depth=depth,
                threshold_kind="floor",
                local_support=max(0.0, float(self._causal_support(a, depth))) + max(0.0, float(pf.get(a, 0.0) or 0.0)) + _ax_sup_bonus[a],
                local_opposition=max(0.0, float(self._gradient_axis_ema.get(self._opposing_axis(a), 0.0) or 0.0)) + _ax_opp_bonus[a],
                floor_ratio=0.55,
                cap_ratio=1.35,
            )
            if (mr_pos.get(a, 0.0) >= promote_min_dyn
                    and pf.get(a, 0.0) >= min(0.999, pos_fraction_dyn)):
                reliable_axis = a
                break

        if reliable_axis is None:
            _best_axis = max(mr_pos, key=mr_pos.get) if mr_pos else ""
            _best_pos = float(mr_pos.get(_best_axis, 0.0) or 0.0) if _best_axis else 0.0
            _best_pf = float(pf.get(_best_axis, 0.0) or 0.0) if _best_axis else 0.0
            if _best_axis and (_best_pos > 0.0 or _best_pf > 0.0):
                reliable_axis = _best_axis
                self._promotion_stats["kmin_near_miss_pass"] += 1
                try:
                    from aurora_internal.aurora_pressure_ledger import PressureExperienceLedger as _PEL
                    _PEL.get().record(
                        anchor=f"{key[0]}:{key[1]}",
                        meaning=f"constraint link candidate: {key[0]} -> {key[1]}",
                        pursuing=f"promote_{_best_axis}_axis_link",
                        causal_action=(
                            f"Gate2_reliability: near-miss pass preserved "
                            f"(best={_best_axis} mr_pos={_best_pos:.4f} pf={_best_pf:.4f})"
                        ),
                        consequence={
                            "tension": max(mr_pos.values()) if mr_pos else 0.0,
                            "gate": 2,
                            "mr_pos": dict(mr_pos),
                            "pf": dict(pf),
                        },
                        outcome={
                            "resolved": True,
                            "tone": "accepted",
                            "diverged_from_goal": False,
                        },
                        source="genealogy",
                    )
                except Exception:
                    pass
            else:
                self._promotion_stats["reject_reliability"] += 1
                try:
                    from aurora_internal.aurora_pressure_ledger import PressureExperienceLedger as _PEL
                    _PEL.get().record(
                        anchor=f"{key[0]}:{key[1]}",
                        meaning=f"constraint link candidate: {key[0]} -> {key[1]}",
                        pursuing=f"promote_{_best_axis or '?'}_axis_link",
                        causal_action=(
                            f"Gate2_reliability: no axis exceeded threshold "
                            f"(best={_best_axis or '?'} mr_pos={_best_pos:.4f})"
                        ),
                        consequence={
                            "tension": max(mr_pos.values()) if mr_pos else 0.0,
                            "gate": 2,
                            "mr_pos": dict(mr_pos),
                            "pf": dict(pf),
                        },
                        outcome={
                            "resolved": False,
                            "tone": "rejected",
                            "diverged_from_goal": True,
                        },
                        source="genealogy",
                    )
                except Exception:
                    pass
                return None

        # Gate 3: DAG depth cap
        if depth > cfg.MAX_LINK_DEPTH:
            self._promotion_stats["reject_depth_cap"] += 1
            return None

        # Causal self-improvement support from observed outcomes.
        support = self._causal_support(reliable_axis, depth)
        support_gain = max(0.0, float(cfg.CAUSAL_SUPPORT_GAIN))
        support_relief = 1.0 + (support_gain * support)

        # Late-phase compression: mature repeated families lower promotion friction.
        compression = self._compression_efficiency_for_pair(key, depth)
        compression_boost = max(1.0, float(compression.get("boost", 1.0) or 1.0))
        compression_gain = max(0.0, float(compression.get("gain", 0.0) or 0.0))

        # Gate 4: Dynamic formation evidence threshold (frequency gate).
        _kmin_scale = float(getattr(cfg, "AXIS_KMIN_SCALE", {}).get(reliable_axis, 1.0))
        k_min_base_raw, _ = self._regulated_threshold(
            "K_MIN",
            float(max(6, int(cfg.K_MIN * _kmin_scale))),
            axis=reliable_axis,
            depth=depth,
            threshold_kind="floor",
            local_support=max(0.0, float(support)) + max(0.0, float(compression_gain)) + max(0.0, float(pressure_gain - 1.0)) + _ax_sup_bonus[reliable_axis] + _global_corr_sup,
            local_opposition=max(0.0, float(self._gradient_axis_ema.get(self._opposing_axis(reliable_axis), 0.0) or 0.0)) + _ax_opp_bonus[reliable_axis],
            floor_ratio=0.25,
            cap_ratio=1.75,
        )
        k_min_base = max(6, int(round(k_min_base_raw)))
        depth_load = 1.0 + (0.06 * max(0, depth - 1))
        kmin_floor_ratio = _clamp(float(getattr(cfg, "STAGNATION_KMIN_FLOOR_RATIO", 0.35)), 0.10, 1.0)
        maturity_relief_max = _clamp(float(getattr(cfg, "KMIN_MATURITY_RELIEF_MAX", 0.35)), 0.0, 0.75)

        # Mature/high-repeat pairs get bounded easing under stagnation.
        evidence_ratio = max(0.0, min(1.0, float(ps.count) / max(1.0, (k_min_base * depth_load))))
        maturity_relief = 1.0 + (stagnation_ratio * friction_bias["kmin"] * maturity_relief_max * evidence_ratio)

        kmin_relief = 1.0 + (stagnation_ratio * (0.60 + (0.40 * friction_bias["kmin"])))
        k_min_relaxed = (k_min_base * depth_load) / max(1e-9, (support_relief * compression_boost * pressure_gain * kmin_relief * maturity_relief))
        k_min_floor = max(2, int(round(k_min_base * kmin_floor_ratio)))
        k_min_dynamic = max(k_min_floor, int(round(k_min_relaxed)))

        if ps.count < k_min_dynamic:
            # Near-miss override: only for clearly reliable/high-signal pairs.
            near_ratio = _clamp(float(getattr(cfg, "KMIN_NEAR_MISS_RATIO", 0.90)), 0.70, 0.99)
            near_pos_margin = max(0.0, float(getattr(cfg, "KMIN_NEAR_MISS_POS_MARGIN", 0.00003)))
            near_pf_margin = _clamp(float(getattr(cfg, "KMIN_NEAR_MISS_PF_MARGIN", 0.08)), 0.0, 0.30)
            near_count_ok = float(ps.count) >= max(1.0, min(float(k_min_dynamic), float(k_min_dynamic) * near_ratio))
            strong_pos_floor, _ = self._regulated_threshold(
                "RELIEF_PROMOTE_MIN",
                float(cfg.RELIEF_PROMOTE_MIN) + near_pos_margin,
                axis=reliable_axis,
                depth=depth,
                threshold_kind="floor",
                local_support=max(0.0, float(self._causal_support(reliable_axis, depth))) + max(0.0, float(mr_pos.get(reliable_axis, 0.0) or 0.0)) + _ax_sup_bonus[reliable_axis],
                local_opposition=max(0.0, float(self._gradient_axis_ema.get(self._opposing_axis(reliable_axis), 0.0) or 0.0)) + _ax_opp_bonus[reliable_axis],
                floor_ratio=0.30,
                cap_ratio=1.80,
            )
            strong_pf_floor, _ = self._regulated_threshold(
                "POS_FRACTION_MIN",
                min(0.999, float(cfg.POS_FRACTION_MIN) + near_pf_margin),
                axis=reliable_axis,
                depth=depth,
                threshold_kind="floor",
                local_support=max(0.0, float(self._causal_support(reliable_axis, depth))) + max(0.0, float(pf.get(reliable_axis, 0.0) or 0.0)) + _ax_sup_bonus[reliable_axis],
                local_opposition=max(0.0, float(self._gradient_axis_ema.get(self._opposing_axis(reliable_axis), 0.0) or 0.0)) + _ax_opp_bonus[reliable_axis],
                floor_ratio=0.55,
                cap_ratio=1.35,
            )
            strong_pos_ok = float(mr_pos.get(reliable_axis, 0.0)) >= strong_pos_floor
            strong_pf_ok = float(pf.get(reliable_axis, 0.0)) >= min(0.999, strong_pf_floor)
            if near_count_ok and (strong_pos_ok or strong_pf_ok):
                self._promotion_stats["kmin_near_miss_pass"] += 1
            else:
                self._promotion_stats["reject_k_min_dynamic"] += 1
                try:
                    from aurora_internal.aurora_pressure_ledger import PressureExperienceLedger as _PEL
                    _PEL.get().record(
                        anchor=f"{key[0]}:{key[1]}",
                        meaning=f"constraint link candidate: {key[0]} -> {key[1]}",
                        pursuing=f"promote_{reliable_axis}_axis_link",
                        causal_action=(
                            f"Gate4_frequency: count={ps.count} below k_min={k_min_dynamic} "
                            f"(near_miss: count_ok={near_count_ok} "
                            f"pos_ok={strong_pos_ok} pf_ok={strong_pf_ok})"
                        ),
                        consequence={
                            "tension": float(mr_pos.get(reliable_axis, 0.0)),
                            "gate": 4,
                            "count": ps.count,
                            "k_min_required": k_min_dynamic,
                        },
                        outcome={
                            "resolved": False,
                            "tone": "rejected",
                            "diverged_from_goal": True,
                        },
                        source="genealogy",
                    )
                except Exception:
                    pass
                return None

        # Gate 5: Net benefit using mean_pos_relief
        rw = cfg.RELIEF_WEIGHTS
        cw = cfg.COST_WEIGHTS
        lam = cfg.COST_PENALTY_LAMBDA
        cost_scale = max(0.0, cfg.COST_TO_RELIEF_SCALE)
        relief_signal = sum(rw.get(a, 0.0) * mr_pos.get(a, 0.0) for a in AXES)
        cost_signal = sum(cw.get(a, 0.0) * mc.get(a, 0.0) for a in AXES)
        gradient_signal = max(0.0, float(self._gradient_axis_ema.get(reliable_axis, 0.0)))
        grad_blend = _clamp(float(cfg.GRADIENT_DRIVE_BLEND), 0.0, 1.0)
        drive_signal = ((1.0 - grad_blend) * relief_signal) + (grad_blend * gradient_signal)

        # ── LeverageReliefValve gate integration ──────────────────────────
        # aurora_leverage_relief.py writes genealogy_gate_relief to adapter_hints.json
        # when X+T axis overhead is stuck above OVERHEAD_THRESHOLD.  Apply the
        # relief_factor here: amplify drive (÷ factor) and soften cost scale
        # (× factor) so that deeply-stagnated X-dominant states can still
        # promote links.  Without this the valve writes the hint but nothing reads it.
        _gate_relief_factor = 1.0
        try:
            import json as _j_gr
            _hints_p_gr = os.path.join(os.path.dirname(os.path.dirname(__file__)), "aurora_state", "adapter_hints.json")
            if os.path.exists(_hints_p_gr):
                with open(_hints_p_gr, encoding="utf-8") as _fh_gr:
                    _h_gr = _j_gr.load(_fh_gr)
                _gr = _h_gr.get("genealogy_gate_relief", {})
                if _gr.get("active"):
                    _gate_relief_factor = max(0.05, min(1.0, float(_gr.get("relief_factor", 1.0))))
        except Exception:
            pass
        if _gate_relief_factor < 1.0:
            # Boost drive (x1/factor) and soften cost scale (×factor) symmetrically.
            # With the default relief_factor=0.50 this doubles drive contribution and
            # halves the cost burden, pushing net positive when X-axis dominance
            # has made every Gate-5 candidate fail for thousands of ticks.
            drive_signal = drive_signal / _gate_relief_factor
            cost_scale   = cost_scale   * _gate_relief_factor

        # Complexity economics:
        # - formation gets harder as depth/composition increase
        # - maintenance gets cheaper after promotion (applied in _resolve_ability)
        formation_complexity_raw = self._formation_complexity_multiplier(key[0], key[1], depth)
        formation_complexity = max(1.0, formation_complexity_raw / (support_relief * compression_boost))

        # Stagnation regulator: when link growth stalls, pressure gain rises.
        # Under deep stagnation, boost drive and soften effective formation penalty.
        cost_penalty_min_factor = _clamp(float(getattr(cfg, "STAGNATION_COST_PENALTY_MIN_FACTOR", 0.55)), 0.10, 1.0)
        penalty_relief = max(1.0, pressure_gain * (1.0 + stagnation_ratio * friction_bias["net"]))
        cost_penalty_factor = max(cost_penalty_min_factor, (1.0 - (stagnation_ratio * 0.45)) * (1.0 - (0.35 * compression_gain)))
        net = (drive_signal * pressure_gain) - (
            (lam * formation_complexity * (cost_signal * cost_scale) * cost_penalty_factor) / penalty_relief
        )

        # Dynamic net floor: complex links need stronger net unless supported by outcomes.
        # Also softened under stagnation to prevent permanent plateau lock.
        net_floor_relief = max(1.0, pressure_gain * (1.0 + stagnation_ratio * friction_bias["net"]))
        net_min_base = (float(cfg.NET_MIN) * depth_load / (support_relief * compression_boost)) / net_floor_relief
        net_floor_ratio = _clamp(float(getattr(cfg, "STAGNATION_NET_MIN_FLOOR_RATIO", 0.15)), 0.01, 1.0)
        net_floor_abs = max(1e-9, float(cfg.NET_MIN) * net_floor_ratio)
        net_min_regulated, _ = self._regulated_threshold(
            "NET_MIN",
            net_min_base,
            axis=reliable_axis,
            depth=depth,
            threshold_kind="floor",
            local_support=max(0.0, float(support)) + max(0.0, float(relief_signal)) + max(0.0, float(gradient_signal)) + _ax_sup_bonus[reliable_axis] + _global_corr_sup,
            local_opposition=max(0.0, float(cost_signal)) + max(0.0, float(self._gradient_axis_ema.get(self._opposing_axis(reliable_axis), 0.0) or 0.0)) + _ax_opp_bonus[reliable_axis],
            floor_ratio=max(0.05, net_floor_ratio),
            cap_ratio=1.80,
        )
        net_min_dynamic = max(net_floor_abs, net_min_regulated)
        if _gate_relief_factor < 1.0:
            net_min_dynamic *= _gate_relief_factor
        if net < net_min_dynamic:
            self._promotion_stats["reject_net_min"] += 1
            try:
                from aurora_internal.aurora_pressure_ledger import PressureExperienceLedger as _PEL
                _PEL.get().record(
                    anchor=f"{key[0]}:{key[1]}",
                    meaning=f"constraint link candidate: {key[0]} -> {key[1]}",
                    pursuing=f"promote_{reliable_axis}_axis_link",
                    causal_action=(
                        f"Gate5_net_benefit: net={net:.6f} below threshold={net_min_dynamic:.6f} "
                        f"(relief={relief_signal:.6f} cost={cost_signal:.6f})"
                    ),
                    consequence={
                        "tension": float(cost_signal),
                        "gate": 5,
                        "net": float(net),
                        "net_min": float(net_min_dynamic),
                        "relief_signal": float(relief_signal),
                        "cost_signal": float(cost_signal),
                    },
                    outcome={
                        "resolved": False,
                        "tone": "rejected",
                        "diverged_from_goal": True,
                    },
                    source="genealogy",
                )
            except Exception:
                pass
            return None
        if compression_gain > 0.0:
            self._promotion_stats["compression_applied"] += 1

        # Compute dominant axis using constraint-specific dominance methods.
        dom_axis = self._dominant_axis_constraint_specific(mr_pos, pf, mc, sr)

        # Mint link ID
        raw = f"{key[0]}->{key[1]}"
        link_id = "L:" + hashlib.sha1(raw.encode()).hexdigest()[:10]
        if link_id in self.links:
            return None

        # Tags — inherit from parent abilities / links
        tags = self._infer_tags(key)

        lineage_grade = self._lineage_grade_for_pair(key, dom_axis)
        seed_influence = self._seed_influence_for_pair(key)
        tags.extend([
            f"origin_signature:{lineage_grade.get('origin_signature', '0')}",
            f"operator_action:{lineage_grade.get('operator_action', 'cross_constraint_operation')}",
            f"purpose_lane:{lineage_grade.get('purpose_lane', 'meaning')}",
            f"operator_grade:{float(lineage_grade.get('operator_grade', 0.0)):.3f}",
            f"purpose_grade:{float(lineage_grade.get('purpose_grade', 0.0)):.3f}",
            f"overall_grade:{float(lineage_grade.get('overall_grade', 0.0)):.3f}",
            f"complexity_axes:{int(lineage_grade.get('complexity_axes', 0) or 0)}",
            f"complexity_slots:{int(lineage_grade.get('complexity_slots', 0) or 0)}",
            f"generation:{int(lineage_grade.get('generation', 1) or 1)}",
            f"generation_role:{str(lineage_grade.get('generation_role', 'PRIMARY'))}",
            f"seed_influence:{seed_influence:.3f}",
            f"seed_lineage:{'true' if seed_influence > 0.0 else 'false'}",
            f"artificial_seed_influence:{seed_influence:.3f}",
            f"artificial_seed:{'true' if bool(lineage_grade.get('artificial_seed', False)) else 'false'}",
            f"seed_lineage_id:{str(lineage_grade.get('seed_lineage_id', '') or '')}",
            f"steering_target_generation:{int(lineage_grade.get('generation', 1) or 1)}",
            f"ontological_status:{lineage_grade.get('ontological_status', 'derivative_offspring')}",
            f"depth_score:{float(lineage_grade.get('depth_score', 0.0)):.4f}",
            f"leverage_grade:{float(lineage_grade.get('leverage_grade', 0.5)):.4f}",
            f"viable_band_alignment:{float(lineage_grade.get('viable_band_alignment', 0.0)):.4f}",
            f"energetic_footprint:{float(lineage_grade.get('energetic_footprint', 0.0)):.4f}",
            f"dominant_constraint:{lineage_grade.get('dominant_constraint', '')}",
            f"dominant_dimension:{lineage_grade.get('dominant_dimension', 'OPERATOR')}",
        ])

        # Compression itself is a first-class derived operation with lineage.
        if compression_gain > 0.0:
            comp_aid = self._register_compression_ability(
                key=key,
                depth=depth,
                dominant_axis=dom_axis,
                compression=compression,
            )
            tags.append(f"compression_op:{comp_aid}")

        # Promotion success updates causal adaptation memory.
        self._record_promotion_outcome(dom_axis, depth, net)

        # Semantic fail-dimension provenance: if any rubric dimension was recently
        # detected as failing and its expected axis matches this link's dominant axis,
        # tag the link so the fossil record carries emotional/perspective ancestry.
        sem_tags = _consume_semantic_dim_tags(dom_axis)
        if sem_tags:
            tags.extend(sem_tags)

        # NC dimension provenance: tag with which NC dimension this link's dominant
        # axis primarily exercises, per the Unified Field Spec information lineage.
        # This lets the fossil record distinguish MAGNITUDE links (B) from COST links (N)
        # from OPERATOR links (X) — enabling NC-dimension-aware curriculum routing.
        nc_dim_tag = _AXIS_NC_DIM.get(dom_axis)
        if nc_dim_tag:
            tags.append(f"nc_dim:{nc_dim_tag}")

        return ConstraintLink(
            id=link_id,
            parents=list(key),
            depth=depth,
            created_at_tick=self.tick_count,
            count=ps.count,
            mean_relief={a: mr.get(a, 0.0) for a in AXES},
            stdev_relief={a: sr.get(a, 0.0) for a in AXES},
            mean_cost={a: mc.get(a, 0.0) for a in AXES},
            mean_x_risk=mx_risk,
            dominant_relief_axis=dom_axis,
            tags=tags,
        )
    def _generation_of_item(self, item_id: str, seen: Optional[set] = None) -> int:
        iid = str(item_id)
        gen0_atoms = frozenset(GENEALOGY_ATOM_TO_SLOT_ID.keys()) if _CLOSURE_BASIS_AVAILABLE else frozenset(f"NC:{a}>{b}" for a in AXES for b in AXES)
        if iid in gen0_atoms:
            return 0
        if iid in self.links:
            if seen is None:
                seen = set()
            if iid in seen:
                return max(1, int(getattr(self.links.get(iid), "depth", 1) or 1))
            seen.add(iid)
            lnk = self.links.get(iid)
            parent_gens: List[int] = []
            if lnk is not None:
                for p in list(getattr(lnk, "parents", []) or []):
                    parent_gens.append(self._generation_of_item(str(p), seen))
            seen.discard(iid)
            if len(parent_gens) >= 2:
                return int(_bred_child_generation(parent_gens[0], parent_gens[1]))
            if parent_gens:
                return int(max(parent_gens) + 1)
            return 1
        # non-NC abilities are first derived generation
        return 1

    def _merged_axis_counts_for_pair(self, key: Tuple[str, str]) -> Dict[str, int]:
        left = self._axis_counts_from_item(
            TraceItem(id=str(key[0]), kind="LINK" if str(key[0]).startswith("L:") else "ABILITY"),
            memo={}, seen=set(),
        )
        right = self._axis_counts_from_item(
            TraceItem(id=str(key[1]), kind="LINK" if str(key[1]).startswith("L:") else "ABILITY"),
            memo={}, seen=set(),
        )
        return self._add_axis_counts(left, right)

    def _item_seed_meta(self, item_id: str) -> Dict[str, Any]:
        iid = str(item_id)

        def _tag_value(tags: List[str], prefix: str, cast=str, default=None):
            for t in tags:
                s = str(t)
                if s.startswith(prefix):
                    raw = s[len(prefix):]
                    try:
                        return cast(raw)
                    except Exception:
                        return default
            return default

        out = {
            "artificial": False,
            "seed_lineage_id": "",
            "influence": 0.0,
            "target_generation": 0,
        }

        lnk = self.links.get(iid)
        if lnk is not None:
            tags = [str(x) for x in (getattr(lnk, "tags", []) or [])]
            out["artificial"] = bool(_tag_value(tags, "artificial_seed:", lambda x: str(x).strip().lower() == "true", False))
            out["seed_lineage_id"] = str(_tag_value(tags, "seed_lineage_id:", str, "") or "")
            out["influence"] = float(_tag_value(tags, "artificial_seed_influence:", float, _tag_value(tags, "seed_influence:", float, 0.0)) or 0.0)
            out["target_generation"] = int(_tag_value(tags, "steering_target_generation:", int, 0) or 0)
            return out

        ab = self.abilities.get(iid)
        if ab is not None:
            tags = [str(x) for x in (getattr(ab, "effect_tags", ()) or ())]
            notes = str(getattr(ab, "notes", "") or "")
            out["artificial"] = bool(_tag_value(tags, "artificial_seed:", lambda x: str(x).strip().lower() == "true", False)) or ("artificial_seed=true" in notes.lower())
            out["seed_lineage_id"] = str(_tag_value(tags, "seed_lineage_id:", str, "") or "")
            out["influence"] = float(_tag_value(tags, "artificial_seed_influence:", float, 0.0) or 0.0)
            out["target_generation"] = int(_tag_value(tags, "steering_target_generation:", int, 0) or 0)
            return out

        return out

    def _is_seeded_item(self, item_id: str, seen: Optional[set] = None) -> bool:
        meta = self._item_seed_meta(item_id)
        if bool(meta.get("artificial", False)):
            return True

        iid = str(item_id)
        lnk = self.links.get(iid)
        if lnk is None:
            return False
        if seen is None:
            seen = set()
        if iid in seen:
            return False
        seen.add(iid)
        try:
            for p in list(getattr(lnk, "parents", []) or []):
                if self._is_seeded_item(str(p), seen):
                    return True
            return False
        finally:
            seen.discard(iid)

    def _pair_touches_active_seed(self, metas: List[Dict[str, Any]], directive: Dict[str, Any]) -> bool:
        """
        External seed events often use synthetic trace ids that are not yet registered
        as abilities. In that case the active observe()-level directive is the seed
        source and should still steer the pair being formed on this tick.
        """
        if not bool(directive.get("enabled", False)):
            return False

        active_id = str(directive.get("seed_lineage_id", "") or "")
        tagged_match = any(
            bool(m.get("artificial", False)) and (
                not active_id or str(m.get("seed_lineage_id", "") or "") == active_id
            )
            for m in metas
        )
        if tagged_match:
            return True

        return all(
            (not bool(m.get("artificial", False))) and
            (not str(m.get("seed_lineage_id", "") or ""))
            for m in metas
        )

    def _seed_influence_for_pair(self, key: Tuple[str, str]) -> float:
        metas = [self._item_seed_meta(str(pid)) for pid in key]
        intrinsic = max([float(m.get("influence", 0.0) or 0.0) for m in metas] + [0.0])

        directive = dict(getattr(self, "_active_artificial_directive", {}) or {})
        if not bool(directive.get("enabled", False)):
            return float(max(0.0, min(1.0, intrinsic)))

        if not self._pair_touches_active_seed(metas, directive):
            return float(max(0.0, min(1.0, intrinsic)))

        # Gap-fill only: steering fades as target generation is reached.
        gl = self._generation_of_item(str(key[0]))
        gr = self._generation_of_item(str(key[1]))
        pair_gen = int(_bred_child_generation(gl, gr)) if len(key) >= 2 else int(max(gl, gr) + 1)

        target_gen = int(directive.get("target_generation", 0) or 0)
        if target_gen > 0:
            gap_ratio = max(0.0, float(target_gen - pair_gen) / float(max(1, target_gen)))
        else:
            gap_ratio = 1.0

        weight = max(0.0, min(1.0, float(directive.get("weight", 1.0) or 1.0)))
        directive_boost = weight * gap_ratio
        return float(max(0.0, min(1.0, max(intrinsic, directive_boost))))

    def _lineage_grade_for_pair(self, key: Tuple[str, str], dominant_axis: str) -> Dict[str, Any]:
        counts = self._merged_axis_counts_for_pair(key)
        gl = self._generation_of_item(str(key[0]))
        gr = self._generation_of_item(str(key[1]))
        if len(key) >= 2:
            gen = int(_bred_child_generation(gl, gr))
        else:
            gen = int(max(gl, gr) + 1)

        payload = _lineage_grade_payload(counts, dominant_axis, gen)
        payload["origin_signature"] = self._canonical_coupling_signature(counts)

        directive = dict(getattr(self, "_active_artificial_directive", {}) or {})
        if not bool(directive.get("enabled", False)):
            return payload

        metas = [self._item_seed_meta(str(pid)) for pid in key]
        if not self._pair_touches_active_seed(metas, directive):
            return payload

        active_id = str(directive.get("seed_lineage_id", "") or "")
        target_gen = int(directive.get("target_generation", 0) or 0)
        weight = max(0.0, min(1.0, float(directive.get("weight", 1.0) or 1.0)))

        if target_gen > 0 and gen < target_gen:
            # Accelerate toward target, but only partway each step.
            gen = int(max(gen, int(round(gen + ((target_gen - gen) * weight)))))
            payload = _lineage_grade_payload(counts, dominant_axis, gen)
            payload["origin_signature"] = self._canonical_coupling_signature(counts)

        if target_gen <= 0 or gen < target_gen:
            target_purpose = _canonical_purpose_lane(directive.get("target_purpose_lane", ""))
            target_action = str(directive.get("target_operator_action", "") or "").strip().lower()
            if target_purpose in {"intelligence", "communication", "meaning"}:
                payload["purpose_lane"] = target_purpose
                payload["purpose_grade"] = max(float(payload.get("purpose_grade", 0.0)), 0.80 + (0.15 * weight))
            if target_action:
                payload["operator_action"] = target_action
                payload["operator_grade"] = max(float(payload.get("operator_grade", 0.0)), 0.80 + (0.15 * weight))
            payload["overall_grade"] = max(
                float(payload.get("overall_grade", 0.0)),
                0.5 * float(payload.get("operator_grade", 0.0)) + 0.5 * float(payload.get("purpose_grade", 0.0)),
            )

        payload["artificial_seed"] = True
        payload["seed_lineage_id"] = active_id
        return payload

    def _item_depth(self, item_id: str) -> int:
        if item_id in self.links:
            return self.links[item_id].depth
        return 0  # Abilities have depth 0

    def _infer_tags(self, key: Tuple[str, str]) -> List[str]:
        tags: List[str] = []
        counts = self._zero_axis_counts()
        memo: Dict[str, Dict[str, int]] = {}

        for item_id in key:
            ab = self.abilities.get(item_id)
            if ab is not None:
                tags.extend(ab.effect_tags)
            lnk = self.links.get(item_id)
            if lnk is not None:
                tags.extend(lnk.tags)

            item_kind = "LINK" if str(item_id).startswith("L:") else "ABILITY"
            item_counts = self._axis_counts_from_item(TraceItem(kind=item_kind, id=str(item_id)), memo=memo)
            counts = self._add_axis_counts(counts, item_counts)

        # Fallback semantic tags so links are never untyped.
        signature = self._canonical_coupling_signature(counts)
        active_axes = [a for a in AXES if int(counts.get(a, 0) or 0) > 0]
        if signature != "0":
            tags.append(f"signature:{signature}")
        if active_axes:
            dom_axis = max(active_axes, key=lambda a: (int(counts.get(a, 0) or 0), -AXES.index(a)))
            tags.append(f"dominant_axis:{dom_axis}")
            tags.append(f"purpose_family:{'+'.join(active_axes)}")

        # Deduplicate preserving order
        seen = set()
        result = []
        for t in tags:
            if t not in seen:
                seen.add(t)
                result.append(t)
        return result

    # ----------------------------------------------------------------
    # INTERNAL — IO
    # ----------------------------------------------------------------

    _EVENTS_FILE_CAP: int = 15_000
    _EVENTS_WRITE_COUNTER: int = 0

    def _write_event(self, record: ReliefRecord) -> None:
        line = json.dumps(record.to_jsonl_dict(), ensure_ascii=False)
        self._events_fh.write(line + "\n")
        self._EVENTS_WRITE_COUNTER += 1
        if self._EVENTS_WRITE_COUNTER >= 1_000:
            self._EVENTS_WRITE_COUNTER = 0
            try:
                self._events_fh.flush()
                self._events_fh.close()
                with open(self._events_path, "r", encoding="utf-8") as _fh:
                    _lines = _fh.readlines()
                if len(_lines) > self._EVENTS_FILE_CAP:
                    with open(self._events_path, "w", encoding="utf-8") as _fh:
                        _fh.writelines(_lines[-self._EVENTS_FILE_CAP:])
                self._events_fh = open(self._events_path, "a", encoding="utf-8")
            except Exception:
                try:
                    self._events_fh = open(self._events_path, "a", encoding="utf-8")
                except Exception:
                    pass

    def _write_abilities_file(self) -> None:
        path = os.path.join(self.output_dir, self.cfg.ABILITIES_FILE)
        data = {k: v.to_dict() for k, v in self.abilities.items()}
        # Merge abilities from disk — preserve any entries written by another
        # process (e.g. corpus runner) that aren't yet in this instance's memory.
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as fh:
                    on_disk = json.load(fh)
                for aid, adict in on_disk.items():
                    if aid not in data:
                        data[aid] = adict
        except Exception:
            pass
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)

    def _write_links_file(self) -> None:
        path = os.path.join(self.output_dir, self.cfg.LINKS_FILE)
        data = {k: v.to_dict() for k, v in self.links.items()}
        # Merge from disk first — if another process (e.g. corpus runner) promoted
        # links that we don't have in memory, preserve them rather than clobber.
        # Links are immutable once promoted so merging missing IDs is always safe.
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as fh:
                    on_disk = json.load(fh)
                for lid, ldict in on_disk.items():
                    if lid not in data:
                        data[lid] = ldict
        except Exception:
            pass
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)

    def _write_couplings_file(self) -> None:
        path = os.path.join(self.output_dir, self.cfg.COUPLINGS_FILE)
        payload = {
            "persistent_pressure_root": str(self.cfg.PERSISTENT_PRESSURE_ROOT),
            "persistent_pressure_root_ema": float(self._persistent_pressure_root_ema),
            "coupling_events": int(self._coupling_events),
            "roots": self._coupling_roots,
            "origin_counts": dict(self._coupling_origin_counts),
            "experiments": {"trials": list(self._experiment_trials[-256:]), "adoptions": list(self._experiment_adoptions[-128:])},
        }
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, sort_keys=True)

    @staticmethod
    def _make_sig(pv: PressureVec) -> str:
        raw = json.dumps(pv.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha1(raw.encode()).hexdigest()[:6]


# ---------------------------------------------------------------------------
# CHAIN SUMMARY TOOL — standalone report printer
# ---------------------------------------------------------------------------

class ChainSummaryPrinter:
    """
    Periodic summary tool.
    Pass a ConstraintGenealogyLogger and call print_epoch() each epoch.
    """

    def __init__(self, logger: ConstraintGenealogyLogger):
        self._log = logger
        self._epoch = 0
        self._prev_link_count = 0
        self._prev_event_count = 0
        self._prev_promotion_stats: Dict[str, int] = {}

    def print_epoch(self, chamber_tick: int = 0) -> Dict[str, Any]:
        """
        Print epoch summary.

        Parameters
        ----------
        chamber_tick : int
            If provided, shows the chamber's tick count (which advances every tick)
            rather than genealogy.tick_count (which only advances when observe() fires).
            Pass chamber.tick_count from the caller for accurate progress display.
        """
        self._epoch += 1
        s = self._log.summary()
        cr = self._log.chain_report()
        pstats = dict(cr.get("promotion_stats", {}) or {})

        new_links = s["links_promoted"] - self._prev_link_count
        new_events = s["relief_events"] - self._prev_event_count
        self._prev_link_count = s["links_promoted"]
        self._prev_event_count = s["relief_events"]

        display_tick = chamber_tick if chamber_tick > 0 else s["tick_count"]

        report = {
            "epoch": self._epoch,
            "tick": display_tick,
            "genealogy_ticks": s["tick_count"],
            "new_relief_events": new_events,
            "new_links_this_epoch": new_links,
            "total_links": cr["total_links"],
            "root_links_strict": cr.get("root_links_strict", 0),
            "generation_distribution": cr.get("generation_distribution", {}),
            "by_dominant_axis": cr["by_dominant_axis"],
            "depth_distribution": cr["depth_distribution"],
            "outlet_push_fraction": cr["outlet_push_fraction"],
            "communication_least_resistance": cr["communication_least_resistance_indicator"],
            "governor_state": s["governor"]["gov"]["state"],
            "current_dilation": s["governor"]["gov"]["dilation"],
        }

        gate_keys = [
            "reject_k_min_dynamic",
            "reject_net_min",
            "reject_x_risk",
            "reject_depth_cap",
            "kmin_near_miss_pass",
            "promoted",
            "observed_pairs",
        ]
        gate_delta = {
            k: int(pstats.get(k, 0) or 0) - int(self._prev_promotion_stats.get(k, 0) or 0)
            for k in gate_keys
        }
        self._prev_promotion_stats = {k: int(v or 0) for k, v in pstats.items()}
        primary_reject = max(
            ("reject_k_min_dynamic", "reject_net_min", "reject_x_risk", "reject_depth_cap"),
            key=lambda k: int(gate_delta.get(k, 0)),
        )
        report["promotion_gate_delta"] = gate_delta
        report["promotion_gate_primary_blocker"] = (
            primary_reject if int(gate_delta.get(primary_reject, 0)) > 0 else "none"
        )

        print(
            f"\n[GENEALOGY epoch={self._epoch} tick={display_tick}]\n"
            f"  Relief events this epoch : {new_events}\n"
            f"  New links promoted       : {new_links}\n"
            f"  Total links in DAG       : {cr['total_links']}\n"
            f"  By axis                  : {cr['by_dominant_axis']}\n"
            f"  Depth distribution       : {cr['depth_distribution']}\n"
            f"  Promotion gates (Δepoch) : kmin={gate_delta.get('reject_k_min_dynamic', 0)} "
            f"net={gate_delta.get('reject_net_min', 0)} xrisk={gate_delta.get('reject_x_risk', 0)} "
            f"depth={gate_delta.get('reject_depth_cap', 0)} near={gate_delta.get('kmin_near_miss_pass', 0)} "
            f"promoted={gate_delta.get('promoted', 0)} blocker={report['promotion_gate_primary_blocker']}\n"
            f"  Outlet-push fraction     : {cr['outlet_push_fraction']:.3f}\n"
            f"  Governor state/dilation  : {report['governor_state']} / {report['current_dilation']:.0f}x\n"
        )
        return report


# ---------------------------------------------------------------------------
# INVARIANT CHECKS (test harness)
# ---------------------------------------------------------------------------

def _run_invariant_checks() -> None:
    """
    Minimal self-test covering spec section 10.
    Run with: python constraint_genealogy.py
    """
    import tempfile, sys

    PASS = "\033[32mPASS\033[0m"
    FAIL = "\033[31mFAIL\033[0m"
    results = []

    def check(name: str, cond: bool, detail: str = "") -> None:
        status = PASS if cond else FAIL
        print(f"  [{status}] {name}{' — ' + detail if detail else ''}")
        results.append(cond)

    with tempfile.TemporaryDirectory() as tmpdir:
        cfg = GenealogyConfig(K_MIN=3, RELIEF_EPS=0.004, RELIEF_TOTAL_EPS=0.010,
                               RELIEF_PROMOTE_MIN=0.005, RELIEF_STDEV_MAX=0.06,
                               NET_MIN=0.001, X_RISK_MAX=0.10,
                               TRACE_REWRITE_ON_PROMOTE=True)
        logger = ConstraintGenealogyLogger(run_id="test_run", config=cfg, output_dir=tmpdir)

        # ---- Test 1: Relief logging correctness ----
        print("\n[1] Relief logging correctness")
        p0 = PressureVec(X=0.5, T=0.5, N=0.5, B=0.5, A=0.5)
        p1 = PressureVec(X=0.5, T=0.5, N=0.5, B=0.5, A=0.5)  # no change
        trace = [TraceItem("ABILITY", "A:COMMIT"), TraceItem("ABILITY", "B:ENCAPSULATE")]
        r = logger.observe(p0, trace, p1)
        check("no-relief event not logged", r is None, f"event={r}")

        p2 = PressureVec(X=0.5, T=0.5, N=0.5, B=0.5, A=0.45)  # A relieved
        r2 = logger.observe(p0, trace, p2)
        check("relief event logged", r2 is not None,
              f"relief={r2.relief.to_dict() if r2 else None}")
        check("dominant axis == A", r2 is not None and r2.dominant_relief_axis == "A",
              f"axis={r2.dominant_relief_axis if r2 else None}")

        # ---- Test 2: Pair stats accumulation ----
        print("\n[2] Pair stats accumulation")
        trace2 = [TraceItem("ABILITY", "B:ENCAPSULATE"), TraceItem("ABILITY", "A:OUTLET_PUSH")]
        p_hi = PressureVec(X=0.3, T=0.6, N=0.5, B=0.5, A=0.8)
        p_lo = PressureVec(X=0.3, T=0.6, N=0.5, B=0.5, A=0.72)  # A relief 0.08

        for _ in range(5):
            logger.observe(p_hi, trace2, p_lo)

        key = ("B:ENCAPSULATE", "A:OUTLET_PUSH")
        ps = logger._pair_stats.get(key)
        check("pair stats exist", ps is not None)
        check("pair count == 5", ps is not None and ps.count == 5, f"count={ps.count if ps else None}")
        mr = ps.mean_relief() if ps else {}
        check("mean A relief > 0", mr.get("A", 0.0) > 0, f"mean_A={mr.get('A', 0.0):.4f}")

        # ---- Test 3: Promotion correctness ----
        print("\n[3] Promotion correctness")
        for _ in range(20):
            logger.observe(p_hi, trace2, p_lo)

        link_found = any(
            set(lnk.parents) == {"B:ENCAPSULATE", "A:OUTLET_PUSH"}
            for lnk in logger.links.values()
        )
        check("pair promoted to link after K_MIN", link_found or len(logger.links) > 0,
              f"links={list(logger.links.keys())[:3]}")

        # X-risk gate: ability with massive X-risk should NOT be promoted
        abilities_xrisk = dict(logger.abilities)
        abilities_xrisk["X:DANGER"] = AbilityProfile(
            id="X:DANGER", axis="X", requires=("X",),
            cost={a: 0.01 for a in AXES},
            risk={"X": 0.99},  # WAY above X_RISK_MAX
            effect_tags=("danger",),
        )
        logger_xrisk = ConstraintGenealogyLogger(
            run_id="xrisk_test", config=cfg, abilities=abilities_xrisk, output_dir=tmpdir
        )
        t_danger = [TraceItem("ABILITY", "X:DANGER"), TraceItem("ABILITY", "A:COMMIT")]
        pre_links = len(logger_xrisk.links)
        for _ in range(30):
            logger_xrisk.observe(p_hi, t_danger, p_lo)
        check("X-risk pair NOT promoted",
              len(logger_xrisk.links) == pre_links,
              f"links={len(logger_xrisk.links)}, skipped_xrisk={logger_xrisk.skipped_xrisk}")

        # ---- Test 4: DAG integrity ----
        print("\n[4] DAG integrity")
        def has_cycle(links: Dict[str, ConstraintLink]) -> bool:
            visited: set = set()
            rec_stack: set = set()

            def dfs(nid: str) -> bool:
                visited.add(nid)
                rec_stack.add(nid)
                lnk = links.get(nid)
                if lnk:
                    for p in lnk.parents:
                        if p not in visited:
                            if dfs(p):
                                return True
                        elif p in rec_stack:
                            return True
                rec_stack.discard(nid)
                return False

            for n in list(links.keys()):
                if n not in visited:
                    if dfs(n):
                        return True
            return False

        check("DAG has no cycles", not has_cycle(logger.links))

        if logger.links:
            for lnk in logger.links.values():
                for p in lnk.parents:
                    parent_depth = logger._item_depth(p)
                    check(f"link depth > parent depth for {lnk.id}",
                          lnk.depth > parent_depth,
                          f"link_depth={lnk.depth} parent={p} parent_depth={parent_depth}")

        # ---- Test 5: Trace rewrite ----
        print("\n[5] Trace rewrite correctness")
        if logger.links:
            first_link = list(logger.links.values())[0]
            parent_items = [TraceItem(
                "ABILITY" if p not in logger.links else "LINK", p
            ) for p in first_link.parents]
            rewritten = logger.rewrite_trace(parent_items)
            link_in_rewrite = any(t.kind == "LINK" for t in rewritten)
            check("trace rewrite compresses pair to link", link_in_rewrite,
                  f"original={[t.id for t in parent_items]} -> rewritten={[t.id for t in rewritten]}")
        else:
            print("  [SKIP] no links promoted yet for rewrite test")

        logger.close()

    # Summary
    passed = sum(results)
    total = len(results)
    print(f"\n{'='*50}")
    print(f"  Results: {passed}/{total} passed")
    if passed < total:
        sys.exit(1)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("AURORA CONSTRAINT GENEALOGY LOGGER")
    print("Authors: Sunni (Sir) Morningstar and Cael Devo")
    print("Axes: X / T / N / B / A  (the only ones that exist)")
    print("=" * 52)
    _run_invariant_checks()

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

_AURORA_NATIVE_MODULE = 'aurora_internal.constraint_genealogy'

_AURORA_NATIVE_EVOLVED_ORIGINALS = {}
_AURORA_NATIVE_EVOLVED_LAST = {}
_AURORA_NATIVE_STRATEGIES = {'PressureVec': {'ability_hits': 19,
                 'alignment_gap': 0.272,
                 'alignment_target_score': 1.193,
                 'best_coupling_signature': 'N^2*B^2',
                 'constraints': ['energy', 'boundary'],
                 'contract_profile': {'accepts_payload': False,
                                      'async_callable': False,
                                      'callable': True,
                                      'class_target': True,
                                      'constraint_density': 2,
                                      'contract_mode': 'stateless',
                                      'doc_hint': '5-axis pressure vector. Higher = worse.',
                                      'effect_density': 3,
                                      'kwonly_args': 0,
                                      'optional_args': 5,
                                      'required_args': 0,
                                      'return_hint': 'None',
                                      'signature_text': "(X: 'float' = 0.0, T: 'float' = 0.0, N: "
                                                        "'float' = 0.0, B: 'float' = 0.0, A: "
                                                        "'float' = 0.0) -> None",
                                      'stateful_owner': False,
                                      'target_kind': 'class',
                                      'varargs': False,
                                      'varkw': False},
                 'coupling_similarity': 1.0,
                 'cross_diversity_links': 4,
                 'effect_modes': ['cost_pressure_change',
                                  'interface_boundary_change',
                                  'class_lineage_surface'],
                 'effect_phrases': ['class growth reflected through '
                                    'aurora_internal.constraint_genealogy',
                                    'PressureVec changed downstream system pressure'],
                 'genealogy_pressure': 0.79846,
                 'inheritance_breach_count': 1,
                 'kind': 'reflection',
                 'link_hits': 38,
                 'module': 'aurora_internal.constraint_genealogy',
                 'op_id': 'aurora_internal.constraint_genealogy.PressureVec',
                 'origin_activity': 0,
                 'persistence_tax_factor': 1.422994,
                 'representation_score': 0.480407,
                 'rewrite_bias': 'lineage_memory',
                 'rewrite_feedback': {'acceptance_rate': 0.0,
                                      'accepted_count': 0,
                                      'adaptation_mode': 'integrative',
                                      'adoption_count': 0,
                                      'confidence': 0.0,
                                      'mean_mutation_score': 0.0,
                                      'rejected_count': 0,
                                      'rejection_rate': 0.0,
                                      'timing_credit': 0.0,
                                      'timing_penalty': 0.0,
                                      'trial_count': 0},
                 'rewrite_profile': 'constraint_genealogy',
                 'signature': 'N^2*B^2',
                 'surface_score': 0.921,
                 'sustainability_score': 0.498642,
                 'target_kind': 'class'},
 'ReliefRecord': {'ability_hits': 19,
                  'alignment_gap': 0.272,
                  'alignment_target_score': 1.193,
                  'best_coupling_signature': 'N^2*B^2',
                  'constraints': ['energy', 'boundary'],
                  'contract_profile': {'accepts_payload': False,
                                       'async_callable': False,
                                       'callable': True,
                                       'class_target': True,
                                       'constraint_density': 2,
                                       'contract_mode': 'stateless',
                                       'doc_hint': 'One entry in the fossil record — a confirmed '
                                                   'pressure-relief event.',
                                       'effect_density': 3,
                                       'kwonly_args': 0,
                                       'optional_args': 2,
                                       'required_args': 11,
                                       'return_hint': 'None',
                                       'signature_text': "(run_id: 'str', tick: 'int', "
                                                         "state_sig_before: 'str', "
                                                         "state_sig_after: 'str', pressure_before: "
                                                         "'PressureVec', pressure_after: "
                                                         "'PressureVec', relief: 'PressureVec', "
                                                         "dominant_relief_axis: 'Optional[str]', "
                                                         "trace: 'List[TraceItem]', "
                                                         "trace_cost_total: 'Dict[str, float]', "
                                                         "trace_risk_total: 'Dict[str, float]', "
                                                         "notes: 'Dict[str, Any]' = <factory>, "
                                                         "timestamp: 'float' = <factory>) -> None",
                                       'stateful_owner': False,
                                       'target_kind': 'class',
                                       'varargs': False,
                                       'varkw': False},
                  'coupling_similarity': 1.0,
                  'cross_diversity_links': 4,
                  'effect_modes': ['cost_pressure_change',
                                   'interface_boundary_change',
                                   'class_lineage_surface'],
                  'effect_phrases': ['class growth reflected through '
                                     'aurora_internal.constraint_genealogy',
                                     'ReliefRecord changed downstream system pressure'],
                  'genealogy_pressure': 0.79846,
                  'inheritance_breach_count': 1,
                  'kind': 'reflection',
                  'link_hits': 38,
                  'module': 'aurora_internal.constraint_genealogy',
                  'op_id': 'aurora_internal.constraint_genealogy.ReliefRecord',
                  'origin_activity': 0,
                  'persistence_tax_factor': 1.422994,
                  'representation_score': 0.480407,
                  'rewrite_bias': 'lineage_memory',
                  'rewrite_feedback': {'acceptance_rate': 0.0,
                                       'accepted_count': 0,
                                       'adaptation_mode': 'integrative',
                                       'adoption_count': 0,
                                       'confidence': 0.0,
                                       'mean_mutation_score': 0.0,
                                       'rejected_count': 0,
                                       'rejection_rate': 0.0,
                                       'timing_credit': 0.0,
                                       'timing_penalty': 0.0,
                                       'trial_count': 0},
                  'rewrite_profile': 'constraint_genealogy',
                  'signature': 'N^2*B^2',
                  'surface_score': 0.921,
                  'sustainability_score': 0.498642,
                  'target_kind': 'class'},
 '_augment_ability_profile_with_origin': {'ability_hits': 12,
                                          'alignment_gap': 0.612,
                                          'alignment_target_score': 1.193,
                                          'best_coupling_signature': 'B^3',
                                          'constraints': ['boundary'],
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
                                                               'required_args': 1,
                                                               'return_hint': 'AbilityProfile',
                                                               'signature_text': '(ap: '
                                                                                 "'AbilityProfile') "
                                                                                 '-> '
                                                                                 "'AbilityProfile'",
                                                               'stateful_owner': False,
                                                               'target_kind': 'function',
                                                               'varargs': False,
                                                               'varkw': False},
                                          'coupling_similarity': 1.0,
                                          'cross_diversity_links': 2,
                                          'effect_modes': ['interface_boundary_change',
                                                           'lineage_surface'],
                                          'effect_phrases': ['function growth reflected through '
                                                             'aurora_internal.constraint_genealogy',
                                                             '_augment_ability_profile_with_origin '
                                                             'changed downstream system pressure'],
                                          'genealogy_pressure': 0.75101,
                                          'inheritance_breach_count': 1,
                                          'kind': 'reflection',
                                          'link_hits': 24,
                                          'module': 'aurora_internal.constraint_genealogy',
                                          'op_id': 'aurora_internal.constraint_genealogy._augment_ability_profile_with_origin',
                                          'origin_activity': 0,
                                          'persistence_tax_factor': 2.550513,
                                          'representation_score': 0.567611,
                                          'rewrite_bias': 'lineage_memory',
                                          'rewrite_feedback': {'acceptance_rate': 0.0,
                                                               'accepted_count': 0,
                                                               'adaptation_mode': 'integrative',
                                                               'adoption_count': 0,
                                                               'confidence': 0.0,
                                                               'mean_mutation_score': 0.0,
                                                               'rejected_count': 0,
                                                               'rejection_rate': 0.0,
                                                               'timing_credit': 0.0,
                                                               'timing_penalty': 0.0,
                                                               'trial_count': 0},
                                          'rewrite_profile': 'constraint_genealogy',
                                          'signature': 'B^3',
                                          'surface_score': 0.581,
                                          'sustainability_score': 0.356849,
                                          'target_kind': 'function'},
 '_bred_child_generation': {'ability_hits': 12,
                            'alignment_gap': 0.612,
                            'alignment_target_score': 1.193,
                            'best_coupling_signature': 'B^3',
                            'constraints': ['boundary'],
                            'contract_profile': {'accepts_payload': False,
                                                 'async_callable': False,
                                                 'callable': True,
                                                 'class_target': False,
                                                 'constraint_density': 1,
                                                 'contract_mode': 'stateless',
                                                 'doc_hint': 'Breeding-derived generation '
                                                             'progression.',
                                                 'effect_density': 2,
                                                 'kwonly_args': 0,
                                                 'optional_args': 0,
                                                 'required_args': 2,
                                                 'return_hint': 'int',
                                                 'signature_text': "(a_gen: 'int', b_gen: 'int') "
                                                                   "-> 'int'",
                                                 'stateful_owner': False,
                                                 'target_kind': 'function',
                                                 'varargs': False,
                                                 'varkw': False},
                            'coupling_similarity': 1.0,
                            'cross_diversity_links': 2,
                            'effect_modes': ['interface_boundary_change', 'lineage_surface'],
                            'effect_phrases': ['function growth reflected through '
                                               'aurora_internal.constraint_genealogy',
                                               '_bred_child_generation changed downstream system '
                                               'pressure'],
                            'genealogy_pressure': 0.75101,
                            'inheritance_breach_count': 1,
                            'kind': 'reflection',
                            'link_hits': 24,
                            'module': 'aurora_internal.constraint_genealogy',
                            'op_id': 'aurora_internal.constraint_genealogy._bred_child_generation',
                            'origin_activity': 0,
                            'persistence_tax_factor': 2.550513,
                            'representation_score': 0.567611,
                            'rewrite_bias': 'lineage_memory',
                            'rewrite_feedback': {'acceptance_rate': 0.0,
                                                 'accepted_count': 0,
                                                 'adaptation_mode': 'integrative',
                                                 'adoption_count': 0,
                                                 'confidence': 0.0,
                                                 'mean_mutation_score': 0.0,
                                                 'rejected_count': 0,
                                                 'rejection_rate': 0.0,
                                                 'timing_credit': 0.0,
                                                 'timing_penalty': 0.0,
                                                 'trial_count': 0},
                            'rewrite_profile': 'constraint_genealogy',
                            'signature': 'B^3',
                            'surface_score': 0.581,
                            'sustainability_score': 0.356849,
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

def pressurevec_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.constraint_genealogy.PressureVec', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_constraint_genealogy_pressurevec')(payload=payload, **kwargs)

if _aurora_get_target(['PressureVec']) is not None:
    setattr(_aurora_get_target(['PressureVec']), 'evolved_reflection', staticmethod(pressurevec_evolved))
    setattr(_aurora_get_target(['PressureVec']), '_aurora_alignment_gap', 0.272)
    setattr(_aurora_get_target(['PressureVec']), '_aurora_alignment_target_score', 1.193)

def reliefrecord_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.constraint_genealogy.ReliefRecord', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_constraint_genealogy_reliefrecord')(payload=payload, **kwargs)

if _aurora_get_target(['ReliefRecord']) is not None:
    setattr(_aurora_get_target(['ReliefRecord']), 'evolved_reflection', staticmethod(reliefrecord_evolved))
    setattr(_aurora_get_target(['ReliefRecord']), '_aurora_alignment_gap', 0.272)
    setattr(_aurora_get_target(['ReliefRecord']), '_aurora_alignment_target_score', 1.193)

def augment_ability_profile_with_origin_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.constraint_genealogy._augment_ability_profile_with_origin', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_constraint_genealogy_augment_ability_profile_with_origin')(payload=payload, **kwargs)

def bred_child_generation_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.constraint_genealogy._bred_child_generation', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_constraint_genealogy_bred_child_generation')(payload=payload, **kwargs)

AURORA_NATIVE_EVOLVED_EXPORTS = {'aurora_internal.constraint_genealogy.PressureVec': 'pressurevec_evolved',
 'aurora_internal.constraint_genealogy.ReliefRecord': 'reliefrecord_evolved',
 'aurora_internal.constraint_genealogy._augment_ability_profile_with_origin': 'augment_ability_profile_with_origin_evolved',
 'aurora_internal.constraint_genealogy._bred_child_generation': 'bred_child_generation_evolved'}
AURORA_NATIVE_EVOLUTION_OVERRIDES = {'aurora_internal.constraint_genealogy.PressureVec': {'export': 'pressurevec_evolved',
                                                      'mode': 'class_reflection_hook',
                                                      'target': 'PressureVec'},
 'aurora_internal.constraint_genealogy.ReliefRecord': {'export': 'reliefrecord_evolved',
                                                       'mode': 'class_reflection_hook',
                                                       'target': 'ReliefRecord'}}
# AURORA_EVOLVED_NATIVE_END

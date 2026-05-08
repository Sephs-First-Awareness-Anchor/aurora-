#!/usr/bin/env python3
"""
AURORA COST-DIFF SCORE — CROSS-DIMENSIONAL PRESSURE SCORING
=============================================================

Layer 1  (sits between DifferenceBuffer and all scored entities)

WHAT THIS MODULE IS:
    The unified scoring engine that fuses a structure's base energy cost
    with the live Difference channel to produce one authoritative number:
    the CostDiffScore. This score reflects both what something costs to
    operate AND how much cross-dimensional pressure the system is currently
    under — making it a live, context-sensitive measure rather than a
    static accounting entry.

THE PROBLEM THIS SOLVES:
    Base cost tells you what an ability, link, or variant costs in a
    calm system. But the system is not always calm. When the admissibility
    boundary is drifting (X:D), when temporal momentum is shifting (T:D),
    when energy is redistributing away from the field mean (N:D), when
    structural topology is displaced from rest (B:D), when agency is
    eroding (A:D) — these conditions change what it *actually costs* to
    operate any structure in that environment. The CostDiffScore captures
    this reality.

THE PHYSICS — OPERATOR-TYPED PRESSURE:
    Each constraint's Difference value is NOT a generic alarm — it is
    a TYPED pressure whose meaning is disclosed by that constraint's
    operator:

    X (existence gate, unsigned, prior_self 1t):
        C:D = admissibility boundary drift.
        When X is drifting, the predicate that governs what can be
        represented in the system is shifting. Everything that operates
        under X pays a hidden cost — the ground it stands on is moving.
        Pressure weight is the smallest (X costs least per unit shift)
        but its scope is global: even a small X:D affects every layer.

    T (time arrow, signed, prior_self 4t):
        C:D = temporal momentum change.
        Positive: tick cost is accelerating — persistence is becoming
        more expensive. Negative: decelerating — tick cost is easing.
        Only the magnitude matters for cost pressure (both directions
        increase operating cost). T has low time_constant (0.3) — it
        responds and recovers quickly.

    N (energy conservation, signed, peer_mean 4t):
        C:D = energy redistribution pressure.
        N is the conserved constraint: if N is significantly above or
        below the peer mean, redistribution is already happening. Any
        structure operating under significant N:D is paying an implicit
        tax — the energy field is not level. N's pressure weight is
        moderate (cost 10×) and its effect is field-wide.

    B (boundary topology, unsigned, background 8t):
        C:D = topological displacement pressure.
        When B is displaced from its architectural rest (0.45), structure
        is being built or dissolved. Structural change propagates through
        all layers below it. B has the second-highest pressure weight
        (cost 40×) — structural drift is expensive and slow to recover.

    A (agency control, signed, prior_self 8t):
        C:D = directional agency pressure.
        Positive: agency is growing — the system is investing in
        complexity and control, which cascades cost through T, N, B.
        Negative: agency is eroding — directional capacity is being
        lost, which may increase entropy pressure elsewhere.
        A has the highest pressure weight (cost 150×) and the longest
        drift window — agency shifts are the most consequential.

CROSS-DIMENSIONAL AMPLIFIER:
    amplifier = 1.0 + Σ_c (OP_PRESSURE_WEIGHT[c] × |C:D[c]|) / 5.0

    This is normalised by 5 (the constraint count) so that the amplifier
    ranges from 1.0 (no drift across any constraint) to approximately
    1.54 (maximum drift across all five simultaneously). The amplifier
    is a multiplier on base_cost — it never reduces it. The score is
    always ≥ base_cost.

    Maximum amplifier: 1 + mean(0.1382, 0.3208, 0.4779, 0.7402, 1.0000)
                     = 1 + 0.5354
                     = 1.5354

    This means even under maximum cross-dimensional pressure, the cost
    amplification is bounded at ~54%. Non-dominant. Meaningful.

COST-DIFF SCORE FORMULA:
    live_score = base_cost × amplifier

WHAT USES THIS:
    - StrandBead.cost_diff_score(snapshot)    → live bead cost
    - DNAStrand.cost_diff_score_total(snapshot) → live strand cost
    - AbilityProfile.cost_diff_score(snapshot)  → live ability cost
    - ConstraintLink.cost_diff_score(snapshot)  → live link cost
    - VariantPromoter (moral weight amplification on promotion)

AUTHORS: Sunni (Sir) Morningstar and Cael Devo
CREATED: February 2026
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from aurora_internal.aurora_constraint_manifold_patched import Constraint, ManifoldViolation
from aurora_internal.aurora_noncomp_registry import REGISTRY
from aurora_internal.aurora_difference_buffer import DifferenceSnapshot


# ===========================================================================
# SECTION 1 — OPERATOR PRESSURE WEIGHTS
# ===========================================================================

def _derive_pressure_weights() -> Dict[Constraint, float]:
    """
    Derive per-constraint operator pressure weights from registry physics.

    Formula: log1p(shift_cost_coeff[c]) / log1p(max_shift_cost_coeff)

    Rationale: the shift_cost_coeff is the registry's declaration of how
    much each constraint costs per unit magnitude change. This is the
    operator's own statement of inertia — deeper, more expensive constraints
    have more momentum and their drift carries more cross-dimensional weight.
    The log1p normalisation prevents runaway amplification from the A:150 gap.

    Result (derived, not chosen):
        X → 0.1382   (cheapest to shift — lowest pressure weight)
        T → 0.3208
        N → 0.4779
        B → 0.7402
        A → 1.0000   (most expensive — highest pressure weight)
    """
    max_coeff = max(
        REGISTRY.cost(c).shift_cost_coeff
        for c in (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A)
    )
    return {
        c: math.log1p(REGISTRY.cost(c).shift_cost_coeff) / math.log1p(max_coeff)
        for c in (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A)
    }


# The table — derived once at import time from registry physics.
# Key doctrinal property: these weights are NOT chosen. They are the
# registry's own shift_cost_coeff table, log-normalised. The operator of
# each constraint has already declared its weight through the physics.
OP_PRESSURE_WEIGHTS: Dict[Constraint, float] = _derive_pressure_weights()

# Maximum amplifier ceiling: 1 + mean(all weights)
# = 1 + 0.5354... ≈ 1.5354
# Used as a sanity bound in verification.
_MEAN_WEIGHT: float = sum(OP_PRESSURE_WEIGHTS.values()) / len(OP_PRESSURE_WEIGHTS)
MAX_AMPLIFIER: float = 1.0 + _MEAN_WEIGHT

# Constraint count (normalisation denominator)
_N_CONSTRAINTS: int = 5

# Opposed tier scaling for operator gradients.
# The total amplifier signal (amp-1.0) is distributed by decade tiers:
# A=1x, B=0.1x, N=0.01x, T=0.001x, X=0.0001x
OPPOSED_OPERATOR_SCALES: Dict[Constraint, float] = {
    Constraint.A: 1.0,
    Constraint.B: 0.1,
    Constraint.N: 0.01,
    Constraint.T: 0.001,
    Constraint.X: 0.000001,
}

# Per-tick participation share by depth/layer.
# X receives the full whole-tick influence; deeper layers receive fractional tick share.
TICK_PARTICIPATION_WEIGHTS: Dict[Constraint, float] = {
    # Time-scale scalars: deeper layers apply more persistent pressure per tick.
    Constraint.X: 1.0,    # full tick exposure
    Constraint.T: 2.0,    # twice per tick (0.5-tick interval)
    Constraint.N: 0.03,   # almost single-shot, minimal persistence
    Constraint.B: 3.0,    # structural pressure with sustained 0.5-tick cadence
    Constraint.A: 6.0,    # agency axes now fire every 0.1 tick and persist
}

# Upward transfer discount: failed holding at lower k may transfer upward,
# but transfer efficiency decays with receiving layer cost density (k).
UPWARD_TRANSFER_BASE_LOSS: float = 0.30
UPWARD_TRANSFER_BETA: float = 0.75

# Random polarity mutation state for pressure behavior.
# Scale-specific mutations: each constraint mutates independently.
_MUTATION_RNG = random.SystemRandom()
_MUTATION_BASE_PROB: float = 0.0025
_MUTATION_CAPACITY_RECOVER: float = 0.035
_MUTATION_AXIS_STATE: Dict[Constraint, Dict[str, object]] = {
    c: {
        "active": False,
        "polarity": 1.0,
        "last_tick": -1,
        "last_event": "none",
        "event_count": 0,
        "updated_at": 0.0,
    }
    for c in (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A)
}


def _update_pressure_mutation(snapshot: Optional[DifferenceSnapshot], signed_deltas: Dict[Constraint, float]) -> Dict[Constraint, float]:
    ordered = (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A)
    if snapshot is None:
        return {c: float(_MUTATION_AXIS_STATE[c].get("polarity", 1.0) or 1.0) for c in ordered}

    tick = int(getattr(snapshot, "tick", -1) or -1)
    out: Dict[Constraint, float] = {}

    for i, c in enumerate(ordered):
        st = _MUTATION_AXIS_STATE[c]
        if tick <= int(st.get("last_tick", -1) or -1):
            out[c] = float(st.get("polarity", 1.0) or 1.0)
            continue

        st["last_tick"] = tick
        own_cap = abs(float(signed_deltas.get(c, 0.0)))
        neigh = []
        if i > 0:
            neigh.append(abs(float(signed_deltas.get(ordered[i - 1], 0.0))))
        if i < len(ordered) - 1:
            neigh.append(abs(float(signed_deltas.get(ordered[i + 1], 0.0))))
        neigh_mean = (sum(neigh) / float(len(neigh))) if neigh else 0.0
        capacity = own_cap + (0.5 * neigh_mean)

        prob = max(1e-6, float(_MUTATION_BASE_PROB) + (0.02 * min(1.0, capacity)))
        r = float(_MUTATION_RNG.random())

        active = bool(st.get("active", False))
        polarity = float(st.get("polarity", 1.0) or 1.0)

        if active:
            if capacity >= float(_MUTATION_CAPACITY_RECOVER):
                active = False
                polarity = 1.0
                st["last_event"] = "capacity_recovery_flip"
                st["event_count"] = int(st.get("event_count", 0) or 0) + 1
            elif r < prob:
                polarity = -polarity
                active = (polarity < 0.0)
                st["last_event"] = "random_mutation_toggle"
                st["event_count"] = int(st.get("event_count", 0) or 0) + 1
        else:
            if r < prob:
                active = True
                polarity = -1.0
                st["last_event"] = "random_mutation_activate"
                st["event_count"] = int(st.get("event_count", 0) or 0) + 1

        st["active"] = bool(active)
        st["polarity"] = float(polarity)
        st["updated_at"] = float(time.time())
        out[c] = float(polarity)

    return out


def pressure_mutation_state() -> Dict[str, object]:
    out: Dict[str, object] = {}
    for c, st in _MUTATION_AXIS_STATE.items():
        out[c.name] = dict(st)
    return out


def _k_efficiency_ratio(lower: Constraint, upper: Constraint, beta: float = UPWARD_TRANSFER_BETA) -> float:
    k_low = max(1e-9, float(REGISTRY.cost(lower).shift_cost_coeff))
    k_up = max(1e-9, float(REGISTRY.cost(upper).shift_cost_coeff))
    ratio = k_low / k_up
    return max(0.0, min(1.0, ratio ** max(0.0, float(beta))))


# ===========================================================================
# SECTION 2 — CROSS-DIMENSIONAL AMPLIFIER
# ===========================================================================

def cross_dim_amplifier(snapshot: Optional[DifferenceSnapshot]) -> float:
    """
    Compute the cross-dimensional pressure amplifier from a DifferenceSnapshot.

    If snapshot is None (no C:D data available — system not yet warm),
    returns 1.0 — no amplification, base cost unchanged.

    Formula:
        amplifier = 1.0 + Σ_c (OP_PRESSURE_WEIGHT[c] × |C:D[c]|) / N_CONSTRAINTS

    Returns a float in [1.0, MAX_AMPLIFIER] ≈ [1.0, 1.54].
    """
    if snapshot is None:
        return 1.0

    total = sum(
        OP_PRESSURE_WEIGHTS[c] * abs(snapshot.value(c))
        for c in (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A)
    )
    return 1.0 + total / _N_CONSTRAINTS



def _reactive_pressure_score(snapshot: Optional[DifferenceSnapshot]) -> float:
    """
    Whole-number reactive pressure score for per-tick X responsiveness.

    Uses mean absolute cross-dimensional drift, scaled to an integer-like score
    so X can react even when X:D itself is near zero.
    """
    if snapshot is None:
        return 1.0
    mean_abs = sum(
        abs(float(snapshot.value(c)))
        for c in (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A)
    ) / float(_N_CONSTRAINTS)
    return max(1.0, float(int(round(mean_abs * 1000.0))))


def per_operator_pressure(snapshot: Optional[DifferenceSnapshot]) -> Dict[Constraint, float]:
    """
    Return per-operator effective pressure contributions from a DifferenceSnapshot.

    Uses signed C:D deltas (polarity-aware) with random mutation polarity flips,
    while preserving k-discounted upward transfer and cross-axis interaction terms.
    """
    if snapshot is None:
        return {
            Constraint.X: 0.0,
            Constraint.T: 0.0,
            Constraint.N: 0.0,
            Constraint.B: 0.0,
            Constraint.A: 0.0,
        }

    ordered = (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A)
    amp = cross_dim_amplifier(snapshot)
    reactive_tick = _reactive_pressure_score(snapshot)

    # Polarity channel from signed C:D
    signed_deltas = {c: float(snapshot.value(c)) for c in ordered}
    abs_deltas = {c: abs(v) for c, v in signed_deltas.items()}

    # Mutation can flip effective polarity until recovered or toggled.
    mutation_polarity = _update_pressure_mutation(snapshot, signed_deltas)

    base_loss = max(0.0, min(0.95, float(UPWARD_TRANSFER_BASE_LOSS)))
    transfer_in = {c: 0.0 for c in ordered}
    retained = dict(abs_deltas)

    for i in range(len(ordered) - 1):
        lower = ordered[i]
        upper = ordered[i + 1]
        own = max(0.0, float(retained.get(lower, 0.0)))
        hold_fail = max(0.0, min(1.0, own))
        spill = own * hold_fail
        if spill <= 0.0:
            continue
        eff = _k_efficiency_ratio(lower, upper, beta=UPWARD_TRANSFER_BETA)
        upward = spill * (1.0 - base_loss) * eff
        decay = spill - upward
        retained[lower] = max(0.0, own - (upward + decay))
        transfer_in[upper] = float(transfer_in.get(upper, 0.0)) + upward

    interaction_gain = 0.20

    out = {}
    for c in ordered:
        own = float(retained.get(c, 0.0))
        upward_in = float(transfer_in.get(c, 0.0))
        others = [float(retained.get(o, 0.0)) for o in ordered if o is not c]
        other_mean = (sum(others) / float(len(others))) if others else 0.0

        # signed polarity component from native C:D channel
        sign_native = 1.0 if float(signed_deltas.get(c, 0.0)) >= 0.0 else -1.0
        polarity = sign_native * float(mutation_polarity.get(c, 1.0))

        driver = (own + upward_in + (interaction_gain * other_mean)) * polarity

        # Preserve whole-tick sensitivity for X even under polarity mutation.
        if c is Constraint.X and abs(driver) < 1.0:
            driver = 1.0 * (1.0 if driver >= 0.0 else -1.0)

        out[c] = (
            amp
            * reactive_tick
            * float(TICK_PARTICIPATION_WEIGHTS.get(c, 0.0))
            * float(OPPOSED_OPERATOR_SCALES.get(c, 0.0))
            * float(driver)
        )

    return out


def dominant_pressure_axis(snapshot: Optional[DifferenceSnapshot]) -> Optional[Constraint]:
    """
    Return the constraint contributing the most operator pressure.

    Uses per_operator_pressure() so the dominant axis matches the active
    contribution model used by runtime pressure gradients.
    """
    if snapshot is None:
        return None

    pressures = per_operator_pressure(snapshot)
    dom_c, dom_p = max(pressures.items(), key=lambda kv: abs(float(kv[1])))
    return dom_c if abs(float(dom_p)) > 0.0 else None


# ===========================================================================
# SECTION 3 — COST-DIFF SCORE
# ===========================================================================

@dataclass(frozen=True)
class CostDiffScore:
    """
    A live, context-sensitive cost score for any Aurora structure.

    Fields
    ------
    base_cost       : the structure's static energy cost (from registry or
                      accumulated operation cost — caller-supplied)
    amplifier       : cross-dimensional pressure multiplier ∈ [1.0, ~1.54]
    live_score      : base_cost × amplifier — the actual cost under current
                      cross-dimensional conditions
    snapshot_tick   : tick of the DifferenceSnapshot used (None = no snapshot)
    dominant_axis   : Constraint with highest operator-weighted drift (None = calm)

    Doctrinal property:
        live_score ≥ base_cost always.
        When the system is calm (all C:D ≈ 0), live_score ≈ base_cost.
        When the system is under cross-dimensional pressure, live_score
        reflects the true cost of operating in that environment.
    """
    base_cost:     float
    amplifier:     float
    live_score:    float
    snapshot_tick: Optional[int]   = None
    dominant_axis: Optional[Constraint] = None

    def to_dict(self) -> Dict[str, object]:
        return {
            "base_cost":     round(self.base_cost,  6),
            "amplifier":     round(self.amplifier,  6),
            "live_score":    round(self.live_score,  6),
            "snapshot_tick": self.snapshot_tick,
            "dominant_axis": self.dominant_axis.name if self.dominant_axis else None,
        }

    def describe(self) -> str:
        dom = self.dominant_axis.name if self.dominant_axis else "none"
        tick_label = f"@t={self.snapshot_tick}" if self.snapshot_tick is not None else "@t=?"
        return (
            f"CostDiffScore[{tick_label}] "
            f"base={self.base_cost:.4f} × ×{self.amplifier:.4f} "
            f"= live={self.live_score:.4f}  "
            f"dominant_pressure={dom}"
        )


def score_from_cost(
    base_cost: float,
    snapshot:  Optional[DifferenceSnapshot],
) -> CostDiffScore:
    """
    Compute a CostDiffScore from a base cost and optional DifferenceSnapshot.

    This is the primary factory function — all Aurora structures that carry
    a live score call this.

    Parameters
    ----------
    base_cost : float
        The structure's static energy cost. For StrandBead: bead.cost().
        For AbilityProfile: ability.total_cost().
        For ConstraintLink: sum(mean_cost.values()).
        Always non-negative.
    snapshot : Optional[DifferenceSnapshot]
        The current system C:D snapshot from DifferenceHistoryBuffer.
        If None, amplifier = 1.0 and live_score = base_cost.

    Returns
    -------
    CostDiffScore (frozen, safe to attach to any structure)
    """
    amp    = cross_dim_amplifier(snapshot)
    dom    = dominant_pressure_axis(snapshot)
    live   = base_cost * amp
    tick   = snapshot.tick if snapshot is not None else None
    return CostDiffScore(
        base_cost     = base_cost,
        amplifier     = amp,
        live_score    = live,
        snapshot_tick = tick,
        dominant_axis = dom,
    )


def score_for_variant_moral_weight(
    raw_moral_weight: float,
    snapshot:         Optional[DifferenceSnapshot],
    moral_weight_max: float,
) -> Tuple[float, float]:
    """
    Compute the cross-dimensionally amplified moral weight for a variant.

    A variant that crystallized while the system was under operator-typed
    pressure across multiple constraint dimensions has proved itself in
    adversarial conditions. It earns stronger moral magnetism — proportional
    to the cross-dimensional pressure at the time of its crystallization.

    This is NOT a gate. It is a landscape amplifier. The physics still
    govern whether the path is taken. But the path left by a pressure-proven
    variant is carved more deeply.

    Parameters
    ----------
    raw_moral_weight : float
        The moral weight computed from recurrence count alone.
    snapshot : Optional[DifferenceSnapshot]
        The DifferenceSnapshot at the moment of variant promotion.
        If None, amplifier = 1.0 (no amplification).
    moral_weight_max : float
        The per-constraint cap on moral weight (from _MORAL_WEIGHT_MAX).

    Returns
    -------
    (amplified_moral_weight, amplifier_used) — both floats.
    amplified_moral_weight is capped at moral_weight_max.
    """
    amp        = cross_dim_amplifier(snapshot)
    amplified  = min(moral_weight_max, raw_moral_weight * amp)
    return amplified, amp


# ===========================================================================
# SECTION 4 — PER-CONSTRAINT PRESSURE DESCRIPTOR
# ===========================================================================

# Human-readable names for the pressure type each constraint discloses.
# These match the operator descriptions from the registry.
OPERATOR_PRESSURE_NAMES: Dict[Constraint, str] = {
    Constraint.X: "admissibility boundary drift",
    Constraint.T: "temporal momentum change",
    Constraint.N: "energy redistribution pressure",
    Constraint.B: "topological displacement",
    Constraint.A: "directional agency pressure",
}


def pressure_description(c: Constraint, cd_value: float) -> str:
    """
    Return a human-readable description of the cross-dimensional pressure
    that constraint c is currently exerting, given its C:D value.
    """
    dp       = DIFFERENCE_PARAMS_AT_IMPORT[c]
    name     = OPERATOR_PRESSURE_NAMES[c]
    weight   = OP_PRESSURE_WEIGHTS[c]
    mag      = abs(cd_value)
    contrib  = weight * mag / _N_CONSTRAINTS

    if dp.polarity_signed:
        direction = "rising" if cd_value > 0 else ("falling" if cd_value < 0 else "stable")
        return (
            f"{c.name}:D={cd_value:+.3f}  [{name} — {direction}]  "
            f"pressure_contrib={contrib:.4f}"
        )
    else:
        return (
            f"{c.name}:D={mag:.3f}  [{name}]  "
            f"pressure_contrib={contrib:.4f}"
        )


# Import needed at function call time — resolved lazily to avoid circular import
from aurora_internal.aurora_noncomp_registry import DIFFERENCE_PARAMS as DIFFERENCE_PARAMS_AT_IMPORT


# ===========================================================================
# SECTION 5 — SELF-VERIFICATION (14 checks)
# ===========================================================================

def verify_cost_diff_score() -> Dict[str, object]:
    """
    Checks:
         1.  OP_PRESSURE_WEIGHTS derived from registry (not chosen)
         2.  X weight < T weight < N weight < B weight < A weight (monotonic)
         3.  A weight = 1.0 (normalised anchor)
         4.  MAX_AMPLIFIER = 1 + mean(weights) ≈ 1.535
         5.  cross_dim_amplifier(None) = 1.0 (no snapshot = no amplification)
         6.  cross_dim_amplifier(all C:D=0) = 1.0 (calm system = no amplification)
         7.  cross_dim_amplifier(all C:D=1) = MAX_AMPLIFIER
         8.  live_score ≥ base_cost always (amplifier ≥ 1.0)
         9.  live_score = base_cost when snapshot is None
        10.  live_score > base_cost when snapshot has nonzero C:D
        11.  dominant_pressure_axis identifies highest op-weighted drift
        12.  score_for_variant_moral_weight caps at moral_weight_max
        13.  score_for_variant_moral_weight(snapshot=None) → amplifier = 1.0
        14.  pressure_description returns string for all five constraints
    """
    from aurora_internal.aurora_difference_buffer import DifferenceSnapshot

    results: Dict[str, object] = {"checks": [], "all_passed": True}

    def check(name: str, passed: bool, detail: str = "") -> None:
        results["checks"].append({"test": name, "passed": passed, "detail": detail})
        if not passed:
            results["all_passed"] = False

    constraints = (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A)

    # 1. Weights derived from registry
    for c in constraints:
        expected = math.log1p(REGISTRY.cost(c).shift_cost_coeff) / math.log1p(150.0)
        check(
            f"OP_PRESSURE_WEIGHTS[{c.name}] derived from registry",
            abs(OP_PRESSURE_WEIGHTS[c] - expected) < 1e-9,
            f"got={OP_PRESSURE_WEIGHTS[c]:.4f}  expected={expected:.4f}"
        )

    # 2. Monotonic order: X < T < N < B < A
    weights = [OP_PRESSURE_WEIGHTS[c] for c in constraints]
    check(
        "Weights monotonically increase X < T < N < B < A",
        weights == sorted(weights),
        str([f"{w:.4f}" for w in weights])
    )

    # 3. A weight = 1.0
    check("A weight = 1.0 (normalised anchor)", abs(OP_PRESSURE_WEIGHTS[Constraint.A] - 1.0) < 1e-9)

    # 4. MAX_AMPLIFIER
    expected_max = 1.0 + sum(OP_PRESSURE_WEIGHTS.values()) / 5.0
    check(
        "MAX_AMPLIFIER = 1 + mean(weights)",
        abs(MAX_AMPLIFIER - expected_max) < 1e-9,
        f"got={MAX_AMPLIFIER:.6f}  expected={expected_max:.6f}"
    )

    # 5. cross_dim_amplifier(None) = 1.0
    check("cross_dim_amplifier(None) = 1.0", abs(cross_dim_amplifier(None) - 1.0) < 1e-9)

    # 6. cross_dim_amplifier(all C:D = 0) = 1.0
    snap_calm = DifferenceSnapshot(
        tick=1,
        values={c: 0.0 for c in constraints},
        ref_magnitudes={c: 0.0 for c in constraints},
    )
    check("cross_dim_amplifier(all C:D=0) = 1.0",
          abs(cross_dim_amplifier(snap_calm) - 1.0) < 1e-9)

    # 7. cross_dim_amplifier(all C:D=1) = MAX_AMPLIFIER
    snap_max = DifferenceSnapshot(
        tick=2,
        values={c: 1.0 for c in constraints},
        ref_magnitudes={c: 0.0 for c in constraints},
    )
    check(
        "cross_dim_amplifier(all C:D=1.0) = MAX_AMPLIFIER",
        abs(cross_dim_amplifier(snap_max) - MAX_AMPLIFIER) < 1e-9,
        f"got={cross_dim_amplifier(snap_max):.6f}  max={MAX_AMPLIFIER:.6f}"
    )

    # 8. live_score ≥ base_cost (amplifier ≥ 1.0 always)
    for snap in [None, snap_calm, snap_max]:
        s = score_from_cost(1.0, snap)
        check(f"live_score ≥ base_cost (snap={snap})",
              s.live_score >= s.base_cost,
              f"live={s.live_score:.4f}  base={s.base_cost:.4f}")

    # 9. live_score = base_cost when snapshot is None
    s9 = score_from_cost(2.5, None)
    check("live_score = base_cost when snapshot=None",
          abs(s9.live_score - 2.5) < 1e-9, f"live={s9.live_score:.6f}")

    # 10. live_score > base_cost when nonzero C:D
    snap10 = DifferenceSnapshot(
        tick=3,
        values={c: 0.5 for c in constraints},
        ref_magnitudes={c: 0.0 for c in constraints},
    )
    s10 = score_from_cost(1.0, snap10)
    check("live_score > base_cost when C:D nonzero",
          s10.live_score > 1.0, f"live={s10.live_score:.4f}")

    # 11. dominant_pressure_axis — A should dominate when all equal (highest weight)
    dom11 = dominant_pressure_axis(snap10)  # all equal C:D=0.5 → A highest weight
    check(
        "dominant_pressure_axis = A when all C:D equal (A has max weight)",
        dom11 == Constraint.A,
        f"got={dom11}"
    )

    # 12. score_for_variant_moral_weight caps at moral_weight_max
    cap = 0.001
    aw, amp = score_for_variant_moral_weight(raw_moral_weight=1.0, snapshot=snap_max, moral_weight_max=cap)
    check("score_for_variant_moral_weight caps at moral_weight_max",
          aw <= cap + 1e-9, f"amplified={aw:.6f}  cap={cap}")

    # 13. score_for_variant_moral_weight(None) → amplifier = 1.0
    aw13, amp13 = score_for_variant_moral_weight(0.5, None, 10.0)
    check("score_for_variant_moral_weight(snapshot=None) → amplifier=1.0",
          abs(amp13 - 1.0) < 1e-9, f"amp={amp13:.4f}")

    # 14. pressure_description returns string for all five constraints
    snap14 = snap10
    for c in constraints:
        desc = pressure_description(c, snap14.value(c))
        check(
            f"pressure_description({c.name}) returns non-empty string",
            isinstance(desc, str) and len(desc) > 0,
            desc[:60]
        )

    return results


# ===========================================================================
# MAIN
# ===========================================================================

if __name__ == "__main__":
    from aurora_internal.aurora_difference_buffer import DifferenceSnapshot

    print("=" * 70)
    print("AURORA COST-DIFF SCORE — CROSS-DIMENSIONAL PRESSURE ENGINE")
    print("Authors: Sunni (Sir) Morningstar and Cael Devo")
    print("=" * 70)

    constraints = (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A)

    print("\nOperator pressure weights (derived from registry physics):")
    for c in constraints:
        k     = REGISTRY.cost(c).shift_cost_coeff
        w     = OP_PRESSURE_WEIGHTS[c]
        pname = OPERATOR_PRESSURE_NAMES[c]
        print(f"  {c.name}  shift_cost_coeff={k:5.1f}  weight={w:.4f}  "
              f"[{pname}]")

    print(f"\nMAX_AMPLIFIER = {MAX_AMPLIFIER:.4f}  "
          f"(max cost increase ~{(_MEAN_WEIGHT * 100):.1f}% under full drift)")

    print("\nSample scores:")
    snap_calm = DifferenceSnapshot(
        tick=10, values={c: 0.0 for c in constraints},
        ref_magnitudes={c: 0.5 for c in constraints})
    snap_mid  = DifferenceSnapshot(
        tick=11, values={c: 0.5 for c in constraints},
        ref_magnitudes={c: 0.5 for c in constraints})
    snap_max  = DifferenceSnapshot(
        tick=12, values={c: 1.0 for c in constraints},
        ref_magnitudes={c: 0.5 for c in constraints})

    for label, snap in [("calm", snap_calm), ("mid", snap_mid), ("max", snap_max)]:
        s = score_from_cost(1.0, snap)
        print(f"  [{label:4s}]  {s.describe()}")

    print("\nPressure description at mid C:D (0.5 each):")
    for c in constraints:
        print(f"  {pressure_description(c, 0.5)}")

    print("\nRunning verification...")
    results = verify_cost_diff_score()
    for item in results["checks"]:
        status = "✓" if item["passed"] else "✗"
        detail = f"  [{item['detail']}]" if item.get("detail") else ""
        print(f"  {status}  {item['test']}{detail}")
    print()
    total  = len(results["checks"])
    passed = sum(1 for c in results["checks"] if c["passed"])
    if results["all_passed"]:
        print(f"ALL {total} CHECKS PASSED ✓")
        print("Cost-Diff score engine is operational.")
    else:
        print(f"{passed}/{total} passed. FAILURES DETECTED ✗")

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

_AURORA_NATIVE_MODULE = 'aurora_internal.aurora_cost_diff_score'

_AURORA_NATIVE_EVOLVED_ORIGINALS = {}
_AURORA_NATIVE_EVOLVED_LAST = {}
_AURORA_NATIVE_STRATEGIES = {'_derive_pressure_weights': {'ability_hits': 2,
                              'alignment_gap': 0.61,
                              'alignment_target_score': 1.191,
                              'best_coupling_signature': 'N^2*B^1',
                              'constraints': ['energy'],
                              'contract_profile': {'accepts_payload': False,
                                                   'async_callable': False,
                                                   'callable': True,
                                                   'class_target': False,
                                                   'constraint_density': 1,
                                                   'contract_mode': 'stateless',
                                                   'doc_hint': 'Derive per-constraint operator '
                                                               'pressure weights from registry '
                                                               'physics.',
                                                   'effect_density': 2,
                                                   'kwonly_args': 0,
                                                   'optional_args': 0,
                                                   'required_args': 0,
                                                   'return_hint': 'Dict[Constraint, float]',
                                                   'signature_text': "() -> 'Dict[Constraint, "
                                                                     "float]'",
                                                   'stateful_owner': False,
                                                   'target_kind': 'function',
                                                   'varargs': False,
                                                   'varkw': False},
                              'coupling_similarity': 1.0,
                              'cross_diversity_links': 2,
                              'effect_modes': ['cost_pressure_change', 'lineage_surface'],
                              'effect_phrases': ['function growth reflected through '
                                                 'aurora_internal.aurora_cost_diff_score',
                                                 '_derive_pressure_weights changed downstream '
                                                 'system pressure'],
                              'genealogy_pressure': 0.428731,
                              'inheritance_breach_count': 1,
                              'kind': 'reflection',
                              'link_hits': 0,
                              'module': 'aurora_internal.aurora_cost_diff_score',
                              'op_id': 'aurora_internal.aurora_cost_diff_score._derive_pressure_weights',
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
 '_k_efficiency_ratio': {'ability_hits': 2,
                         'alignment_gap': 0.61,
                         'alignment_target_score': 1.191,
                         'best_coupling_signature': 'N^2*B^1',
                         'constraints': ['energy'],
                         'contract_profile': {'accepts_payload': False,
                                              'async_callable': False,
                                              'callable': True,
                                              'class_target': False,
                                              'constraint_density': 1,
                                              'contract_mode': 'stateless',
                                              'doc_hint': '',
                                              'effect_density': 2,
                                              'kwonly_args': 0,
                                              'optional_args': 1,
                                              'required_args': 2,
                                              'return_hint': 'float',
                                              'signature_text': "(lower: 'Constraint', upper: "
                                                                "'Constraint', beta: 'float' = "
                                                                "0.75) -> 'float'",
                                              'stateful_owner': False,
                                              'target_kind': 'function',
                                              'varargs': False,
                                              'varkw': False},
                         'coupling_similarity': 1.0,
                         'cross_diversity_links': 2,
                         'effect_modes': ['cost_pressure_change', 'lineage_surface'],
                         'effect_phrases': ['function growth reflected through '
                                            'aurora_internal.aurora_cost_diff_score',
                                            '_k_efficiency_ratio changed downstream system '
                                            'pressure'],
                         'genealogy_pressure': 0.428731,
                         'inheritance_breach_count': 1,
                         'kind': 'reflection',
                         'link_hits': 0,
                         'module': 'aurora_internal.aurora_cost_diff_score',
                         'op_id': 'aurora_internal.aurora_cost_diff_score._k_efficiency_ratio',
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
 '_reactive_pressure_score': {'ability_hits': 2,
                              'alignment_gap': 0.61,
                              'alignment_target_score': 1.191,
                              'best_coupling_signature': 'N^2*B^1',
                              'constraints': ['energy'],
                              'contract_profile': {'accepts_payload': False,
                                                   'async_callable': False,
                                                   'callable': True,
                                                   'class_target': False,
                                                   'constraint_density': 1,
                                                   'contract_mode': 'stateless',
                                                   'doc_hint': 'Whole-number reactive pressure '
                                                               'score for per-tick X '
                                                               'responsiveness.',
                                                   'effect_density': 2,
                                                   'kwonly_args': 0,
                                                   'optional_args': 0,
                                                   'required_args': 1,
                                                   'return_hint': 'float',
                                                   'signature_text': '(snapshot: '
                                                                     "'Optional[DifferenceSnapshot]') "
                                                                     "-> 'float'",
                                                   'stateful_owner': False,
                                                   'target_kind': 'function',
                                                   'varargs': False,
                                                   'varkw': False},
                              'coupling_similarity': 1.0,
                              'cross_diversity_links': 2,
                              'effect_modes': ['cost_pressure_change', 'lineage_surface'],
                              'effect_phrases': ['function growth reflected through '
                                                 'aurora_internal.aurora_cost_diff_score',
                                                 '_reactive_pressure_score changed downstream '
                                                 'system pressure'],
                              'genealogy_pressure': 0.428731,
                              'inheritance_breach_count': 1,
                              'kind': 'reflection',
                              'link_hits': 0,
                              'module': 'aurora_internal.aurora_cost_diff_score',
                              'op_id': 'aurora_internal.aurora_cost_diff_score._reactive_pressure_score',
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
 'cross_dim_amplifier': {'ability_hits': 2,
                         'alignment_gap': 0.61,
                         'alignment_target_score': 1.191,
                         'best_coupling_signature': 'N^2*B^1',
                         'constraints': ['energy'],
                         'contract_profile': {'accepts_payload': False,
                                              'async_callable': False,
                                              'callable': True,
                                              'class_target': False,
                                              'constraint_density': 1,
                                              'contract_mode': 'stateless',
                                              'doc_hint': 'Compute the cross-dimensional pressure '
                                                          'amplifier from a DifferenceSnapshot.',
                                              'effect_density': 2,
                                              'kwonly_args': 0,
                                              'optional_args': 0,
                                              'required_args': 1,
                                              'return_hint': 'float',
                                              'signature_text': '(snapshot: '
                                                                "'Optional[DifferenceSnapshot]') "
                                                                "-> 'float'",
                                              'stateful_owner': False,
                                              'target_kind': 'function',
                                              'varargs': False,
                                              'varkw': False},
                         'coupling_similarity': 1.0,
                         'cross_diversity_links': 2,
                         'effect_modes': ['cost_pressure_change', 'lineage_surface'],
                         'effect_phrases': ['function growth reflected through '
                                            'aurora_internal.aurora_cost_diff_score',
                                            'cross_dim_amplifier changed downstream system '
                                            'pressure'],
                         'genealogy_pressure': 0.428731,
                         'inheritance_breach_count': 1,
                         'kind': 'reflection',
                         'link_hits': 0,
                         'module': 'aurora_internal.aurora_cost_diff_score',
                         'op_id': 'aurora_internal.aurora_cost_diff_score.cross_dim_amplifier',
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
 'dominant_pressure_axis': {'ability_hits': 2,
                            'alignment_gap': 0.61,
                            'alignment_target_score': 1.191,
                            'best_coupling_signature': 'N^2*B^1',
                            'constraints': ['energy'],
                            'contract_profile': {'accepts_payload': False,
                                                 'async_callable': False,
                                                 'callable': True,
                                                 'class_target': False,
                                                 'constraint_density': 1,
                                                 'contract_mode': 'stateless',
                                                 'doc_hint': 'Return the constraint contributing '
                                                             'the most operator pressure.',
                                                 'effect_density': 2,
                                                 'kwonly_args': 0,
                                                 'optional_args': 0,
                                                 'required_args': 1,
                                                 'return_hint': 'Optional[Constraint]',
                                                 'signature_text': '(snapshot: '
                                                                   "'Optional[DifferenceSnapshot]') "
                                                                   "-> 'Optional[Constraint]'",
                                                 'stateful_owner': False,
                                                 'target_kind': 'function',
                                                 'varargs': False,
                                                 'varkw': False},
                            'coupling_similarity': 1.0,
                            'cross_diversity_links': 2,
                            'effect_modes': ['cost_pressure_change', 'lineage_surface'],
                            'effect_phrases': ['function growth reflected through '
                                               'aurora_internal.aurora_cost_diff_score',
                                               'dominant_pressure_axis changed downstream system '
                                               'pressure'],
                            'genealogy_pressure': 0.428731,
                            'inheritance_breach_count': 1,
                            'kind': 'reflection',
                            'link_hits': 0,
                            'module': 'aurora_internal.aurora_cost_diff_score',
                            'op_id': 'aurora_internal.aurora_cost_diff_score.dominant_pressure_axis',
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
 'per_operator_pressure': {'ability_hits': 2,
                           'alignment_gap': 0.61,
                           'alignment_target_score': 1.191,
                           'best_coupling_signature': 'N^2*B^1',
                           'constraints': ['energy'],
                           'contract_profile': {'accepts_payload': False,
                                                'async_callable': False,
                                                'callable': True,
                                                'class_target': False,
                                                'constraint_density': 1,
                                                'contract_mode': 'stateless',
                                                'doc_hint': 'Return per-operator effective '
                                                            'pressure contributions from a '
                                                            'DifferenceSnapshot.',
                                                'effect_density': 2,
                                                'kwonly_args': 0,
                                                'optional_args': 0,
                                                'required_args': 1,
                                                'return_hint': 'Dict[Constraint, float]',
                                                'signature_text': '(snapshot: '
                                                                  "'Optional[DifferenceSnapshot]') "
                                                                  "-> 'Dict[Constraint, float]'",
                                                'stateful_owner': False,
                                                'target_kind': 'function',
                                                'varargs': False,
                                                'varkw': False},
                           'coupling_similarity': 1.0,
                           'cross_diversity_links': 2,
                           'effect_modes': ['cost_pressure_change', 'lineage_surface'],
                           'effect_phrases': ['function growth reflected through '
                                              'aurora_internal.aurora_cost_diff_score',
                                              'per_operator_pressure changed downstream system '
                                              'pressure'],
                           'genealogy_pressure': 0.428731,
                           'inheritance_breach_count': 1,
                           'kind': 'reflection',
                           'link_hits': 0,
                           'module': 'aurora_internal.aurora_cost_diff_score',
                           'op_id': 'aurora_internal.aurora_cost_diff_score.per_operator_pressure',
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
 'pressure_description': {'ability_hits': 2,
                          'alignment_gap': 0.61,
                          'alignment_target_score': 1.191,
                          'best_coupling_signature': 'N^2*B^1',
                          'constraints': ['energy'],
                          'contract_profile': {'accepts_payload': False,
                                               'async_callable': False,
                                               'callable': True,
                                               'class_target': False,
                                               'constraint_density': 1,
                                               'contract_mode': 'stateless',
                                               'doc_hint': 'Return a human-readable description of '
                                                           'the cross-dimensional pressure',
                                               'effect_density': 2,
                                               'kwonly_args': 0,
                                               'optional_args': 0,
                                               'required_args': 2,
                                               'return_hint': 'str',
                                               'signature_text': "(c: 'Constraint', cd_value: "
                                                                 "'float') -> 'str'",
                                               'stateful_owner': False,
                                               'target_kind': 'function',
                                               'varargs': False,
                                               'varkw': False},
                          'coupling_similarity': 1.0,
                          'cross_diversity_links': 2,
                          'effect_modes': ['cost_pressure_change', 'lineage_surface'],
                          'effect_phrases': ['function growth reflected through '
                                             'aurora_internal.aurora_cost_diff_score',
                                             'pressure_description changed downstream system '
                                             'pressure'],
                          'genealogy_pressure': 0.428731,
                          'inheritance_breach_count': 1,
                          'kind': 'reflection',
                          'link_hits': 0,
                          'module': 'aurora_internal.aurora_cost_diff_score',
                          'op_id': 'aurora_internal.aurora_cost_diff_score.pressure_description',
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
 'score_for_variant_moral_weight': {'ability_hits': 2,
                                    'alignment_gap': 0.61,
                                    'alignment_target_score': 1.191,
                                    'best_coupling_signature': 'N^2*B^1',
                                    'constraints': ['energy'],
                                    'contract_profile': {'accepts_payload': False,
                                                         'async_callable': False,
                                                         'callable': True,
                                                         'class_target': False,
                                                         'constraint_density': 1,
                                                         'contract_mode': 'stateless',
                                                         'doc_hint': 'Compute the '
                                                                     'cross-dimensionally '
                                                                     'amplified moral weight for a '
                                                                     'variant.',
                                                         'effect_density': 2,
                                                         'kwonly_args': 0,
                                                         'optional_args': 0,
                                                         'required_args': 3,
                                                         'return_hint': 'Tuple[float, float]',
                                                         'signature_text': '(raw_moral_weight: '
                                                                           "'float', snapshot: "
                                                                           "'Optional[DifferenceSnapshot]', "
                                                                           'moral_weight_max: '
                                                                           "'float') -> "
                                                                           "'Tuple[float, float]'",
                                                         'stateful_owner': False,
                                                         'target_kind': 'function',
                                                         'varargs': False,
                                                         'varkw': False},
                                    'coupling_similarity': 1.0,
                                    'cross_diversity_links': 2,
                                    'effect_modes': ['cost_pressure_change', 'lineage_surface'],
                                    'effect_phrases': ['function growth reflected through '
                                                       'aurora_internal.aurora_cost_diff_score',
                                                       'score_for_variant_moral_weight changed '
                                                       'downstream system pressure'],
                                    'genealogy_pressure': 0.428731,
                                    'inheritance_breach_count': 1,
                                    'kind': 'reflection',
                                    'link_hits': 0,
                                    'module': 'aurora_internal.aurora_cost_diff_score',
                                    'op_id': 'aurora_internal.aurora_cost_diff_score.score_for_variant_moral_weight',
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
 'score_from_cost': {'ability_hits': 2,
                     'alignment_gap': 0.61,
                     'alignment_target_score': 1.191,
                     'best_coupling_signature': 'N^2*B^1',
                     'constraints': ['energy'],
                     'contract_profile': {'accepts_payload': False,
                                          'async_callable': False,
                                          'callable': True,
                                          'class_target': False,
                                          'constraint_density': 1,
                                          'contract_mode': 'stateless',
                                          'doc_hint': 'Compute a CostDiffScore from a base cost '
                                                      'and optional DifferenceSnapshot.',
                                          'effect_density': 2,
                                          'kwonly_args': 0,
                                          'optional_args': 0,
                                          'required_args': 2,
                                          'return_hint': 'CostDiffScore',
                                          'signature_text': "(base_cost: 'float', snapshot: "
                                                            "'Optional[DifferenceSnapshot]') -> "
                                                            "'CostDiffScore'",
                                          'stateful_owner': False,
                                          'target_kind': 'function',
                                          'varargs': False,
                                          'varkw': False},
                     'coupling_similarity': 1.0,
                     'cross_diversity_links': 2,
                     'effect_modes': ['cost_pressure_change', 'lineage_surface'],
                     'effect_phrases': ['function growth reflected through '
                                        'aurora_internal.aurora_cost_diff_score',
                                        'score_from_cost changed downstream system pressure'],
                     'genealogy_pressure': 0.428731,
                     'inheritance_breach_count': 1,
                     'kind': 'reflection',
                     'link_hits': 0,
                     'module': 'aurora_internal.aurora_cost_diff_score',
                     'op_id': 'aurora_internal.aurora_cost_diff_score.score_from_cost',
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
 'verify_cost_diff_score': {'ability_hits': 2,
                            'alignment_gap': 0.61,
                            'alignment_target_score': 1.191,
                            'best_coupling_signature': 'N^2*B^1',
                            'constraints': ['energy'],
                            'contract_profile': {'accepts_payload': False,
                                                 'async_callable': False,
                                                 'callable': True,
                                                 'class_target': False,
                                                 'constraint_density': 1,
                                                 'contract_mode': 'stateless',
                                                 'doc_hint': 'Checks:',
                                                 'effect_density': 2,
                                                 'kwonly_args': 0,
                                                 'optional_args': 0,
                                                 'required_args': 0,
                                                 'return_hint': 'Dict[str, object]',
                                                 'signature_text': "() -> 'Dict[str, object]'",
                                                 'stateful_owner': False,
                                                 'target_kind': 'function',
                                                 'varargs': False,
                                                 'varkw': False},
                            'coupling_similarity': 1.0,
                            'cross_diversity_links': 2,
                            'effect_modes': ['cost_pressure_change', 'lineage_surface'],
                            'effect_phrases': ['function growth reflected through '
                                               'aurora_internal.aurora_cost_diff_score',
                                               'verify_cost_diff_score changed downstream system '
                                               'pressure'],
                            'genealogy_pressure': 0.428731,
                            'inheritance_breach_count': 1,
                            'kind': 'reflection',
                            'link_hits': 0,
                            'module': 'aurora_internal.aurora_cost_diff_score',
                            'op_id': 'aurora_internal.aurora_cost_diff_score.verify_cost_diff_score',
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

def derive_pressure_weights_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_cost_diff_score._derive_pressure_weights', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_cost_diff_score_derive_pressure_weights')(payload=payload, **kwargs)

if _aurora_get_target(['_derive_pressure_weights']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['_derive_pressure_weights'] = _aurora_get_target(['_derive_pressure_weights'])
    _aurora_assign_target(['_derive_pressure_weights'], _aurora_make_override('derive_pressure_weights_evolved', '_derive_pressure_weights'))
    _AURORA_NATIVE_EVOLVED_LAST['_derive_pressure_weights'] = {'alignment_gap': 0.61, 'override_active': True}

def k_efficiency_ratio_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_cost_diff_score._k_efficiency_ratio', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_cost_diff_score_k_efficiency_ratio')(payload=payload, **kwargs)

def reactive_pressure_score_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_cost_diff_score._reactive_pressure_score', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_cost_diff_score_reactive_pressure_score')(payload=payload, **kwargs)

def cross_dim_amplifier_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_cost_diff_score.cross_dim_amplifier', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_cost_diff_score_cross_dim_amplifier')(payload=payload, **kwargs)

if _aurora_get_target(['cross_dim_amplifier']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['cross_dim_amplifier'] = _aurora_get_target(['cross_dim_amplifier'])
    _aurora_assign_target(['cross_dim_amplifier'], _aurora_make_override('cross_dim_amplifier_evolved', 'cross_dim_amplifier'))
    _AURORA_NATIVE_EVOLVED_LAST['cross_dim_amplifier'] = {'alignment_gap': 0.61, 'override_active': True}

def dominant_pressure_axis_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_cost_diff_score.dominant_pressure_axis', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_cost_diff_score_dominant_pressure_axis')(payload=payload, **kwargs)

if _aurora_get_target(['dominant_pressure_axis']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['dominant_pressure_axis'] = _aurora_get_target(['dominant_pressure_axis'])
    _aurora_assign_target(['dominant_pressure_axis'], _aurora_make_override('dominant_pressure_axis_evolved', 'dominant_pressure_axis'))
    _AURORA_NATIVE_EVOLVED_LAST['dominant_pressure_axis'] = {'alignment_gap': 0.61, 'override_active': True}

def per_operator_pressure_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_cost_diff_score.per_operator_pressure', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_cost_diff_score_per_operator_pressure')(payload=payload, **kwargs)

if _aurora_get_target(['per_operator_pressure']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['per_operator_pressure'] = _aurora_get_target(['per_operator_pressure'])
    _aurora_assign_target(['per_operator_pressure'], _aurora_make_override('per_operator_pressure_evolved', 'per_operator_pressure'))
    _AURORA_NATIVE_EVOLVED_LAST['per_operator_pressure'] = {'alignment_gap': 0.61, 'override_active': True}

def pressure_description_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_cost_diff_score.pressure_description', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_cost_diff_score_pressure_description')(payload=payload, **kwargs)

if _aurora_get_target(['pressure_description']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['pressure_description'] = _aurora_get_target(['pressure_description'])
    _aurora_assign_target(['pressure_description'], _aurora_make_override('pressure_description_evolved', 'pressure_description'))
    _AURORA_NATIVE_EVOLVED_LAST['pressure_description'] = {'alignment_gap': 0.61, 'override_active': True}

def score_for_variant_moral_weight_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_cost_diff_score.score_for_variant_moral_weight', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_cost_diff_score_score_for_variant_moral_weight')(payload=payload, **kwargs)

if _aurora_get_target(['score_for_variant_moral_weight']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['score_for_variant_moral_weight'] = _aurora_get_target(['score_for_variant_moral_weight'])
    _aurora_assign_target(['score_for_variant_moral_weight'], _aurora_make_override('score_for_variant_moral_weight_evolved', 'score_for_variant_moral_weight'))
    _AURORA_NATIVE_EVOLVED_LAST['score_for_variant_moral_weight'] = {'alignment_gap': 0.61, 'override_active': True}

def score_from_cost_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_cost_diff_score.score_from_cost', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_cost_diff_score_score_from_cost')(payload=payload, **kwargs)

if _aurora_get_target(['score_from_cost']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['score_from_cost'] = _aurora_get_target(['score_from_cost'])
    _aurora_assign_target(['score_from_cost'], _aurora_make_override('score_from_cost_evolved', 'score_from_cost'))
    _AURORA_NATIVE_EVOLVED_LAST['score_from_cost'] = {'alignment_gap': 0.61, 'override_active': True}

def verify_cost_diff_score_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_cost_diff_score.verify_cost_diff_score', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_cost_diff_score_verify_cost_diff_score')(payload=payload, **kwargs)

if _aurora_get_target(['verify_cost_diff_score']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['verify_cost_diff_score'] = _aurora_get_target(['verify_cost_diff_score'])
    _aurora_assign_target(['verify_cost_diff_score'], _aurora_make_override('verify_cost_diff_score_evolved', 'verify_cost_diff_score'))
    _AURORA_NATIVE_EVOLVED_LAST['verify_cost_diff_score'] = {'alignment_gap': 0.61, 'override_active': True}

AURORA_NATIVE_EVOLVED_EXPORTS = {'aurora_internal.aurora_cost_diff_score._derive_pressure_weights': 'derive_pressure_weights_evolved',
 'aurora_internal.aurora_cost_diff_score._k_efficiency_ratio': 'k_efficiency_ratio_evolved',
 'aurora_internal.aurora_cost_diff_score._reactive_pressure_score': 'reactive_pressure_score_evolved',
 'aurora_internal.aurora_cost_diff_score.cross_dim_amplifier': 'cross_dim_amplifier_evolved',
 'aurora_internal.aurora_cost_diff_score.dominant_pressure_axis': 'dominant_pressure_axis_evolved',
 'aurora_internal.aurora_cost_diff_score.per_operator_pressure': 'per_operator_pressure_evolved',
 'aurora_internal.aurora_cost_diff_score.pressure_description': 'pressure_description_evolved',
 'aurora_internal.aurora_cost_diff_score.score_for_variant_moral_weight': 'score_for_variant_moral_weight_evolved',
 'aurora_internal.aurora_cost_diff_score.score_from_cost': 'score_from_cost_evolved',
 'aurora_internal.aurora_cost_diff_score.verify_cost_diff_score': 'verify_cost_diff_score_evolved'}
AURORA_NATIVE_EVOLUTION_OVERRIDES = {'aurora_internal.aurora_cost_diff_score._derive_pressure_weights': {'export': 'derive_pressure_weights_evolved',
                                                                     'mode': 'callable_override',
                                                                     'target': '_derive_pressure_weights'},
 'aurora_internal.aurora_cost_diff_score.cross_dim_amplifier': {'export': 'cross_dim_amplifier_evolved',
                                                                'mode': 'callable_override',
                                                                'target': 'cross_dim_amplifier'},
 'aurora_internal.aurora_cost_diff_score.dominant_pressure_axis': {'export': 'dominant_pressure_axis_evolved',
                                                                   'mode': 'callable_override',
                                                                   'target': 'dominant_pressure_axis'},
 'aurora_internal.aurora_cost_diff_score.per_operator_pressure': {'export': 'per_operator_pressure_evolved',
                                                                  'mode': 'callable_override',
                                                                  'target': 'per_operator_pressure'},
 'aurora_internal.aurora_cost_diff_score.pressure_description': {'export': 'pressure_description_evolved',
                                                                 'mode': 'callable_override',
                                                                 'target': 'pressure_description'},
 'aurora_internal.aurora_cost_diff_score.score_for_variant_moral_weight': {'export': 'score_for_variant_moral_weight_evolved',
                                                                           'mode': 'callable_override',
                                                                           'target': 'score_for_variant_moral_weight'},
 'aurora_internal.aurora_cost_diff_score.score_from_cost': {'export': 'score_from_cost_evolved',
                                                            'mode': 'callable_override',
                                                            'target': 'score_from_cost'},
 'aurora_internal.aurora_cost_diff_score.verify_cost_diff_score': {'export': 'verify_cost_diff_score_evolved',
                                                                   'mode': 'callable_override',
                                                                   'target': 'verify_cost_diff_score'}}
# AURORA_EVOLVED_NATIVE_END

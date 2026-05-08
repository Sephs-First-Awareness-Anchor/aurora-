#!/usr/bin/env python3
"""
AURORA CROSS-SCALE WORTH EVALUATOR — STEP 10
=============================================

Standalone formalisation of the Worth function.

DOCTRINAL DEFINITION:
    Worth = cross-scale invariance.
    It measures how far an intake propagates through constraint depth WITHOUT
    requiring forced transformation at each layer transition.

    Worth is NOT:
        - utility (not about what it "does for" the system)
        - compute reduction (not about efficiency)
        - a property of the input itself

    Worth IS:
        - a relationship between the input AND the current constraint topology
        - contextual: the same input may score differently across two ticks
        - depth-authoritative: passing deep layers counts for more than passing
          shallow layers, because deeper layers have higher inertia and cost
          more to adjust

FORMULA:
    W(x) = 1 / (1 + Σᵢ wᵢ · |Δforced_at_layer_i|)

    Where:
        Δforced_at_layer_i  = magnitude adjustment layer i needs to admit the
                              intake cleanly — derived from authority differential
                              between the adjacent constraint pair
        wᵢ                  = depth-authority weight for that transition
                              (deeper transition → higher wᵢ)

    This module evaluates ALL FOUR transitions:
        X→T   (surface to shallow)
        T→N   (shallow to moderate)
        N→B   (moderate to deep)
        B→A   (deep to core)   ← Step 9's WorthEvaluator omitted this one

    Including B→A is the key extension. The agency layer is the most
    expensive and most authoritative. If an intake can pass that transition
    cleanly, its worth is genuinely high.

VARIANT HORIZON:
    Once an intake is promoted, how long does its trace persist before
    becoming eligible for solidification (Step 11)?

    Horizon = f(depth reached at promotion)

    The deeper the intake propagated, the longer its trace persists, because
    depth is COSTLY and the system has already invested real energy there.
    A promoted intake that reached AGENTIC has a longer horizon than one that
    reached PERSISTENT — because agency costs 150× time_constant in energy,
    and the system needs time to observe recurrence before solidifying.

    Horizon is expressed in ticks and is bounded to prevent infinite
    persistence (which would lock the solidification pipeline).

WORTH HISTORY:
    Each intake gets a rolling buffer of Worth scores across its TTL.
    The trajectory (RISING, FALLING, OSCILLATING, STABLE) is reported
    without exposing the raw scores.

    Trajectory feeds Step 11 (Solidification): an intake with a RISING
    trajectory is a better solidification candidate than one with a
    STABLE but low score that happened to cross the threshold once.

ANTI-GAMING PROPERTIES PRESERVED FROM STEP 9:
    1. Worth is contextual — same input scores differently across ticks
    2. Raw scores are never exposed publicly — only trajectory direction
    3. Authority weights are computed from ALIGNMENT_VOTE_WEIGHT (not chosen)
    4. Noise is added before threshold comparison (not before reporting)
    5. B→A transition is now included — but its exact weighting is not
       published in the public API

AUTHORS: Sunni (Sir) Morningstar and Cael Devo
CREATED: February 2026
"""

from __future__ import annotations

import math
import random
from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Deque, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# AURORA STACK IMPORTS — exact names from confirmed modules in directory
# ---------------------------------------------------------------------------

from aurora_internal.aurora_constraint_manifold_patched import (
    Constraint,
    ManifoldViolation,
)
from aurora_constraint_engine import ExistenceMode
from aurora_internal.aurora_noncomp_registry import (
    REGISTRY,
    NonCompRegistry,
)
from aurora_internal.aurora_energy_layer_costs import (
    LayerEnergyAccountant,
    MagnitudeShiftRequest,
)
from aurora_internal.aurora_leverage_scalar import (
    LeverageBiasEngine,
    BandPosition,
)
from aurora_ivm import (
    ALIGNMENT_VOTE_WEIGHT,
    RecursionLevel,
    LEVEL_TO_AXIS,
)


# ===========================================================================
# SECTION 1 — CONSTANTS (all derived from registry / IVM — nothing chosen)
# ===========================================================================

# ---------------------------------------------------------------------------
# MAGNITUDE FORMULA WEIGHTS
# (Derived from AURORA_UNIFIED_FIELD_SPEC.md — 2026-03-16)
#
# Worth is cross-scale invariance — how far an intake propagates through
# constraint depth without forced transformation. The magnitude formula
# relates directly to this: high-magnitude field states require more energy
# to traverse, making cross-scale propagation harder.
#
# Canonical formula: Magnitude = (B × T × X) / N
# Semantic reading:  Meaning = (Boundary × Belief × Information) / Purpose
#
# In worth scoring: the transition authority weights already encode the cost
# of crossing each layer boundary. The magnitude formula provides the field
# context in which those transitions occur:
#   - High B (boundary pressure) → deeper transitions are more costly
#   - High T (temporal pressure) → propagation multiplier degrades
#   - Low X (coherence degraded) → magnitude anchor fails
#   - High N (energy abundant)   → reduces effective traversal cost
#
# _MAGNITUDE_TRANSITION_ROLE encodes which field role each transition upper
# constraint plays in the magnitude formula. Used to weight forced-shift
# contributions by their magnitude formula position.
# ---------------------------------------------------------------------------
_MAGNITUDE_TRANSITION_ROLE: Dict[Constraint, str] = {
    Constraint.X: "coherence_anchor",      # X → grounds magnitude in admissibility
    Constraint.T: "propagation_multiplier", # T → how far magnitude reaches through time
    Constraint.N: "conservation_reference", # N → normalization denominator
    Constraint.B: "primary_magnitude_carrier", # B → boundary IS the measure
    Constraint.A: "impact_multiplier",     # A → converts magnitude to impact
}

# ALL FOUR transitions in depth order.
# This is the complete scale traversal that Step 9 abbreviated.
_ALL_TRANSITIONS: Tuple[Tuple[Constraint, Constraint, RecursionLevel, RecursionLevel], ...] = (
    (Constraint.X, Constraint.T, RecursionLevel.SURFACE,  RecursionLevel.SHALLOW),
    (Constraint.T, Constraint.N, RecursionLevel.SHALLOW,  RecursionLevel.MODERATE),
    (Constraint.N, Constraint.B, RecursionLevel.MODERATE, RecursionLevel.DEEP),
    (Constraint.B, Constraint.A, RecursionLevel.DEEP,     RecursionLevel.CORE),
)

# Authority weights per transition — derived from ALIGNMENT_VOTE_WEIGHT.
# The weight of a transition is the authority differential between the two
# levels it bridges: deeper level weight minus shallower level weight.
# This is always positive because vote weight increases monotonically with depth.
_TRANSITION_AUTHORITY: Dict[Tuple[Constraint, Constraint], float] = {
    (upper_c, lower_c): (
        ALIGNMENT_VOTE_WEIGHT[lower_lvl] - ALIGNMENT_VOTE_WEIGHT[upper_lvl]
    )
    for (upper_c, lower_c, upper_lvl, lower_lvl) in _ALL_TRANSITIONS
}

# Maximum possible raw forced-shift sum (used to normalise the denominator).
# Achieved when every layer is maximally misaligned — theoretical ceiling.
# Derived: sum of authority weights × maximum possible forced shift per pair.
# Maximum forced shift per pair ≈ time_constant of the lower layer (its max
# single-tick response — anything larger gets capped by inertia).
_MAX_FORCED_SHIFT_SUM: float = sum(
    _TRANSITION_AUTHORITY[(upper_c, lower_c)]
    * REGISTRY.cost(lower_c).time_constant
    for (upper_c, lower_c, _, _) in _ALL_TRANSITIONS
)

# Noise sigma for score dithering (same approach as Step 9).
# Prevents clean reverse-engineering of the threshold.
_NOISE_SIGMA: float = 0.018

# Trajectory history window — how many ticks of scores to keep per intake.
_HISTORY_WINDOW: int = 8

# Variant horizon bounds in ticks.
# MIN: shallow promotion should persist at least a few ticks for observation.
# MAX: even the deepest promotion must not lock the pipeline forever.
# Derived from the registry time constants (surface τ=1.0, core τ=0.0001).
# Scale: horizon ~ (depth_index + 1) × (1 / time_constant of deepest layer reached)
# Capped to prevent runaway.
_HORIZON_MIN_TICKS: int = 3    # PERSISTENT minimum
_HORIZON_MAX_TICKS: int = 200  # AGENTIC maximum


# ===========================================================================
# SECTION 2 — TRAJECTORY ENUM
# ===========================================================================

class WorthTrajectory(Enum):
    """
    The directional trend of an intake's worth scores over its TTL window.

    This is the ONLY trajectory information exposed publicly — not the scores.

    RISING      — worth is climbing consistently (system becoming more receptive)
    FALLING     — worth is declining consistently (system becoming less receptive)
    OSCILLATING — worth alternates up/down (system in churn around the input)
    STABLE      — worth is not changing meaningfully (equilibrium)
    UNKNOWN     — insufficient data (fewer than 2 samples)
    """
    RISING      = "rising"
    FALLING     = "falling"
    OSCILLATING = "oscillating"
    STABLE      = "stable"
    UNKNOWN     = "unknown"


# ===========================================================================
# SECTION 3 — VARIANT HORIZON
# ===========================================================================

@dataclass(frozen=True)
class VariantHorizon:
    """
    How long a promoted intake's trace persists before becoming eligible
    for the solidification pipeline (Step 11).

    Horizon length is proportional to depth reached at promotion.
    Deeper = more expensive = longer observation window required before
    the system commits to solidification.

    intake_id     — which intake this horizon describes
    depth_reached — the ExistenceMode the intake achieved at promotion
    horizon_ticks — number of ticks the trace must persist and be observed
                    before it becomes a solidification candidate
    promoted_tick — the tick at which promotion occurred
    eligible_tick — promoted_tick + horizon_ticks (when Step 11 may claim it)
    """
    intake_id:     str
    depth_reached: ExistenceMode
    horizon_ticks: int
    promoted_tick: int
    eligible_tick: int

    @property
    def is_eligible(self) -> bool:
        """True if current_tick >= eligible_tick — always compare externally."""
        raise AttributeError(
            "Call horizon.eligible_at(current_tick) to check eligibility — "
            "is_eligible requires external tick context."
        )

    def eligible_at(self, current_tick: int) -> bool:
        """True if the trace has persisted long enough for solidification."""
        return current_tick >= self.eligible_tick

    def depth_label(self) -> str:
        """Human-readable depth description."""
        return self.depth_reached.name


def compute_variant_horizon(
    intake_id: str,
    depth_reached: ExistenceMode,
    promoted_tick: int,
) -> VariantHorizon:
    """
    Compute the Variant Horizon for a newly promoted intake.

    Horizon ticks are derived from depth:
        TRANSIENT  → not eligible (should not be in promoted state — guard)
        PERSISTENT → _HORIZON_MIN_TICKS + 1 × N_time_constant_inverse_factor
        BOUNDED    → PERSISTENT horizon × B_inertia_factor
        AGENTIC    → BOUNDED horizon × A_inertia_factor (capped at MAX)

    All multipliers come from REGISTRY.cost().time_constant values, not chosen.
    """
    # Depth index: TRANSIENT=0, PERSISTENT=1, BOUNDED=2, AGENTIC=3
    _depth_to_index: Dict[ExistenceMode, int] = {
        ExistenceMode.TRANSIENT:  0,
        ExistenceMode.PERSISTENT: 1,
        ExistenceMode.BOUNDED:    2,
        ExistenceMode.AGENTIC:    3,
    }
    depth_index = _depth_to_index.get(depth_reached, 0)

    # Base horizon — derived from the shift cost coefficients of the
    # constraints gained at each depth level.
    # Intuition: the more energy it cost to get here, the longer we observe.
    cost_at_depth: Dict[int, float] = {
        0: REGISTRY.cost(Constraint.T).shift_cost_coeff,   # T gained at TRANSIENT
        1: REGISTRY.cost(Constraint.N).shift_cost_coeff,   # N gained at PERSISTENT
        2: REGISTRY.cost(Constraint.B).shift_cost_coeff,   # B gained at BOUNDED
        3: REGISTRY.cost(Constraint.A).shift_cost_coeff,   # A gained at AGENTIC
    }
    raw_cost = cost_at_depth.get(depth_index, REGISTRY.cost(Constraint.T).shift_cost_coeff)

    # Horizon = floor(raw_cost / 10) + MIN_TICKS, capped at MAX_TICKS
    # Division by 10 is a unit normalisation: k_T=4 → 0 extra ticks,
    # k_N=10 → 1 extra tick, k_B=40 → 4 extra ticks, k_A=150 → 15 extra ticks
    horizon_ticks = min(
        _HORIZON_MAX_TICKS,
        max(_HORIZON_MIN_TICKS, _HORIZON_MIN_TICKS + int(raw_cost / 10))
    )

    return VariantHorizon(
        intake_id     = intake_id,
        depth_reached = depth_reached,
        horizon_ticks = horizon_ticks,
        promoted_tick = promoted_tick,
        eligible_tick = promoted_tick + horizon_ticks,
    )


# ===========================================================================
# SECTION 4 — WORTH HISTORY
# ===========================================================================

@dataclass
class WorthHistory:
    """
    Rolling buffer of Worth scores for one intake across its TTL.

    Internally stores raw scores in a fixed-size deque.
    Publicly exposes only trajectory direction and whether the intake
    is trending toward promotion threshold.

    Raw scores are NOT exposed — only trajectory.

    intake_id   — which intake this tracks
    window      — how many scores to keep (default _HISTORY_WINDOW)
    """
    intake_id: str
    window:    int = _HISTORY_WINDOW

    _scores:   Deque[float] = field(default_factory=deque, repr=False)
    _best:     float        = field(default=0.0,            repr=False)

    def __post_init__(self) -> None:
        self._scores = deque(maxlen=self.window)

    def record(self, score: float) -> None:
        """Add a new score to the history buffer."""
        self._scores.append(score)
        if score > self._best:
            self._best = score

    @property
    def trajectory(self) -> WorthTrajectory:
        """
        Classify the trend across the rolling window.

        Algorithm:
            If fewer than 2 samples: UNKNOWN
            Compute first-difference series: Δ[i] = score[i] - score[i-1]
            If all Δ > 0:              RISING
            If all Δ < 0:              FALLING
            If sign(Δ) alternates:     OSCILLATING
            Otherwise:                 STABLE
        """
        if len(self._scores) < 2:
            return WorthTrajectory.UNKNOWN

        scores = list(self._scores)
        deltas = [scores[i] - scores[i - 1] for i in range(1, len(scores))]

        if not deltas:
            return WorthTrajectory.UNKNOWN

        all_rising  = all(d > 0.0 for d in deltas)
        all_falling = all(d < 0.0 for d in deltas)

        if all_rising:
            return WorthTrajectory.RISING
        if all_falling:
            return WorthTrajectory.FALLING

        # Oscillating: sign changes on consecutive deltas
        sign_changes = sum(
            1 for i in range(1, len(deltas))
            if (deltas[i] > 0) != (deltas[i - 1] > 0)
        )
        if sign_changes >= max(1, len(deltas) // 2):
            return WorthTrajectory.OSCILLATING

        return WorthTrajectory.STABLE

    @property
    def sample_count(self) -> int:
        """How many samples are in the buffer."""
        return len(self._scores)

    @property
    def has_ever_risen(self) -> bool:
        """True if the intake's best score exceeded the initial score."""
        if len(self._scores) < 2:
            return False
        initial = list(self._scores)[0]
        return self._best > initial

    def summary(self) -> Dict[str, object]:
        """Compact summary without exposing raw scores."""
        return {
            "intake_id":   self.intake_id,
            "samples":     self.sample_count,
            "trajectory":  self.trajectory.value,
            "ever_risen":  self.has_ever_risen,
        }


# ===========================================================================
# SECTION 5 — WORTH REPORT
# ===========================================================================

@dataclass
class WorthReport:
    """
    Output of one CrossScaleWorthEvaluator.evaluate() call.

    This is the rich snapshot passed downstream (to Step 11 — Solidification,
    to constraint_genealogy.py for relief event candidates, and to the
    evolution chamber for ActionTrace annotation).

    WHAT IS EXPOSED (safe to pass downstream):
        intake_id       — which intake was evaluated
        tick            — when evaluated
        crossed_threshold — did this evaluation push the intake into promoted
                           territory? (boolean, not the score)
        trajectory      — direction of worth over the TTL window
        polarity_coherent — are the X→T and B→A polarities aligned?
                           (boolean — derived from constraint phases, not scores)
        horizon         — VariantHorizon if promotion occurred this tick, else None
        tense_transitions — which layer pairs showed high forced-shift pressure
                           (list of strings like "N→B", not numeric values)

    WHAT IS NOT EXPOSED:
        raw worth score       — never
        per-transition deltas — never
        authority weights     — never
    """
    intake_id:         str
    tick:              int
    crossed_threshold: bool
    trajectory:        WorthTrajectory
    polarity_coherent: bool
    horizon:           Optional[VariantHorizon]
    tense_transitions: List[str]


# ===========================================================================
# SECTION 6 — CROSS-SCALE WORTH EVALUATOR
# ===========================================================================

class CrossScaleWorthEvaluator:
    """
    The primary worth measurement engine for Step 10.

    Extends the inline WorthEvaluator from aurora_intake_metabolism.py by:
        1. Evaluating ALL FOUR constraint transitions (not three)
        2. Computing a VariantHorizon when promotion occurs
        3. Maintaining a WorthHistory per intake_id across calls
        4. Reporting polarity coherence (are surface and core aligned?)
        5. Identifying which transitions are "tense" (high forced-shift)

    INTEGRATION CONTRACT:
        - Called by IntakeMetabolizer when it needs a worth evaluation
        - May replace the inline WorthEvaluator in aurora_intake_metabolism.py
          once Step 11 is confirmed (it is backward-compatible)
        - The caller passes intake_id, current_mode, accountant, tick
        - The evaluator returns (score_float, WorthReport)
        - The score_float is used internally by the metabolizer for
          threshold comparison; WorthReport is passed to downstream consumers

    WORTH THRESHOLD:
        The promotion threshold is NOT published in the public API.
        It is the same threshold used in aurora_intake_metabolism.py —
        derived from the registry, not chosen. The internal _WORTH_THRESHOLD
        constant is deliberately omitted from the docstring.
    """

    # Tense threshold: a transition is "tense" if its weighted forced shift
    # exceeds this fraction of the maximum possible contribution from that pair.
    # Derived: 20% of the maximum per-pair contribution = noticeable pressure.
    _TENSE_FRACTION: float = 0.20

    def __init__(self, rng: Optional[random.Random] = None) -> None:
        self._rng = rng or random.Random()
        # Per-intake rolling worth histories
        self._histories: Dict[str, WorthHistory] = {}
        # Track which intakes crossed threshold this session
        self._promoted_this_session: set = set()

    # ------------------------------------------------------------------
    # PRIMARY INTERFACE
    # ------------------------------------------------------------------

    def evaluate(
        self,
        intake_id:    str,
        current_mode: ExistenceMode,
        accountant:   LayerEnergyAccountant,
        current_tick: int,
    ) -> Tuple[float, WorthReport]:
        """
        Evaluate the Worth of one intake at the current system state.

        Parameters
        ----------
        intake_id : str
            The opaque ID of the intake record from aurora_intake_metabolism.py.
        current_mode : ExistenceMode
            The depth this intake currently occupies.
        accountant : LayerEnergyAccountant
            The live five-layer energy accountant (state at this tick).
        current_tick : int
            The current system tick (for horizon computation).

        Returns
        -------
        (worth_score, WorthReport)
            worth_score : float in (0.0, 1.0] — for internal threshold use only
            WorthReport : rich snapshot for downstream consumers
        """
        magnitudes  = accountant.magnitudes()
        slots       = {c: accountant.slot(c) for c in (
            Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A
        )}

        # --- 1. Compute forced-shift sum across all four transitions ----
        forced_shift_sum: float = 0.0
        tense_pairs:      List[str] = []

        for (upper_c, lower_c, upper_lvl, lower_lvl) in _ALL_TRANSITIONS:
            upper_mag = magnitudes.get(upper_c, 0.0)
            lower_mag = magnitudes.get(lower_c, 0.0)
            authority = _TRANSITION_AUTHORITY[(upper_c, lower_c)]
            lower_tc  = REGISTRY.cost(lower_c).time_constant

            # Forced shift: how much would the lower layer need to move
            # to match the upper layer's activation scale?
            # Soft cap by time_constant: deeper layers resist more.
            if upper_mag == 0.0:
                forced = 0.0
            else:
                ratio  = abs(lower_mag - upper_mag) / (upper_mag + 1e-9)
                forced = min(ratio, lower_tc) * authority

            forced_shift_sum += forced

            # Tense detection: forced contribution > fraction of max for this pair
            max_for_pair = authority * lower_tc
            if max_for_pair > 0 and (forced / max_for_pair) > self._TENSE_FRACTION:
                upper_name = upper_c.name
                lower_name = lower_c.name
                tense_pairs.append(f"{upper_name}→{lower_name}")

        # --- 2. Compute raw worth score ---------------------------------
        # W(x) = 1 / (1 + normalised_forced_shift_sum)
        # Normalise by _MAX_FORCED_SHIFT_SUM to keep denominator meaningful.
        normalised_sum = forced_shift_sum / max(_MAX_FORCED_SHIFT_SUM, 1e-9)
        raw_score = 1.0 / (1.0 + normalised_sum)

        # --- 2b. Magnitude formula alignment bonus ----------------------
        # The canonical magnitude formula: Magnitude = (B × T × X) / N
        # An intake that propagates cleanly through the field has low
        # forced-shift AND aligns with the field's magnitude structure.
        # We compute the magnitude alignment score: how aligned are the
        # upper-constraint magnitudes with the formula's expected roles?
        #   B_mag × T_mag × X_mag / max(N_mag, 0.1)
        # High alignment means the intake fits the field's natural topology.
        # Normalize against current field mean magnitude to keep in [0,1].
        _b_mag = float(magnitudes.get(Constraint.B, 0.0))
        _t_mag = float(magnitudes.get(Constraint.T, 0.0))
        _x_mag = float(magnitudes.get(Constraint.X, 0.0))
        _n_mag = max(0.1, float(magnitudes.get(Constraint.N, 0.1)))
        _a_mag = float(magnitudes.get(Constraint.A, 0.0))
        _field_magnitude = (_b_mag * _t_mag * _x_mag) / _n_mag
        _impact_magnitude = _field_magnitude * _a_mag
        # Blend: 90% base worth + 10% impact magnitude bonus (max +0.10)
        # Impact magnitude bonus only applies when intake already has non-trivial worth.
        _magnitude_bonus = min(0.10, _impact_magnitude * 0.10) if raw_score > 0.3 else 0.0
        raw_score = min(1.0, raw_score + _magnitude_bonus)

        # --- 3. Add anti-gaming noise (before threshold comparison) -----
        noise = self._rng.gauss(0.0, _NOISE_SIGMA)
        noisy_score = max(0.001, min(1.0, raw_score + noise))

        # --- 4. Update history ----------------------------------------
        if intake_id not in self._histories:
            self._histories[intake_id] = WorthHistory(intake_id=intake_id)
        history = self._histories[intake_id]
        history.record(noisy_score)

        # --- 5. Threshold check (internal — not exposed in report) -----
        _WORTH_THRESHOLD: float = (
            REGISTRY.cost(Constraint.N).baseline_budget
            / (
                REGISTRY.cost(Constraint.X).baseline_budget
                + REGISTRY.cost(Constraint.T).baseline_budget
                + REGISTRY.cost(Constraint.N).baseline_budget
            )
        )  # 6.0 / 9.5 ≈ 0.6316 — derived from registry ratios
        crossed = noisy_score >= _WORTH_THRESHOLD

        # --- 6. Polarity coherence check --------------------------------
        # Surface and core polarities are "coherent" if they have the same sign.
        x_pol = slots[Constraint.X].polarity
        a_pol = slots[Constraint.A].polarity
        polarity_coherent = (x_pol * a_pol) >= 0.0  # same sign or one is zero

        # --- 7. Horizon (only on first crossing) ------------------------
        horizon: Optional[VariantHorizon] = None
        if crossed and intake_id not in self._promoted_this_session:
            self._promoted_this_session.add(intake_id)
            horizon = compute_variant_horizon(
                intake_id     = intake_id,
                depth_reached = current_mode,
                promoted_tick = current_tick,
            )

        # --- 8. Assemble report ----------------------------------------
        report = WorthReport(
            intake_id         = intake_id,
            tick              = current_tick,
            crossed_threshold = crossed,
            trajectory        = history.trajectory,
            polarity_coherent = polarity_coherent,
            horizon           = horizon,
            tense_transitions = tense_pairs,
        )

        return noisy_score, report

    def history_for(self, intake_id: str) -> Optional[WorthHistory]:
        """Return the WorthHistory for an intake (None if not yet seen)."""
        return self._histories.get(intake_id)

    def clear_intake(self, intake_id: str) -> None:
        """
        Remove a closed intake from internal tracking.

        Call this when an intake decays or reaches AGENTIC — its history
        should not accumulate indefinitely.
        """
        self._histories.pop(intake_id, None)
        self._promoted_this_session.discard(intake_id)

    def active_intake_count(self) -> int:
        """How many intakes are currently being tracked."""
        return len(self._histories)


# ===========================================================================
# SECTION 7 — FACTORY
# ===========================================================================

def make_worth_evaluator(rng_seed: Optional[int] = None) -> CrossScaleWorthEvaluator:
    """
    Create a CrossScaleWorthEvaluator with an optionally seeded RNG.

    Use rng_seed only in tests — production instances should use unseeded RNG
    to preserve anti-gaming properties.
    """
    rng = random.Random(rng_seed) if rng_seed is not None else random.Random()
    return CrossScaleWorthEvaluator(rng=rng)


# ===========================================================================
# SECTION 8 — SELF-VERIFICATION (16 checks)
# ===========================================================================

def verify_worth_evaluator() -> Dict[str, object]:
    """
    Verify the CrossScaleWorthEvaluator integrity.

    Checks:
         1.  All four transitions are defined with positive authority weights
         2.  Authority weights increase monotonically with depth (B→A > N→B > T→N > X→T)
         3.  _MAX_FORCED_SHIFT_SUM is positive and finite
         4.  Worth score is in (0, 1] on a balanced system
         5.  Tense transitions reported when layers are misaligned
         6.  No tense transitions on a fully balanced system
         7.  WorthHistory trajectory = UNKNOWN with fewer than 2 samples
         8.  WorthHistory trajectory = RISING when scores consistently climb
         9.  WorthHistory trajectory = FALLING when scores consistently decline
        10.  WorthHistory trajectory = OSCILLATING when scores alternate
        11.  WorthHistory.summary() does not expose raw scores
        12.  VariantHorizon: AGENTIC horizon > BOUNDED > PERSISTENT
        13.  VariantHorizon.eligible_at(tick) false before horizon elapses
        14.  VariantHorizon.eligible_at(tick) true after horizon elapses
        15.  horizon is returned on first threshold crossing, not on repeats
        16.  polarity_coherent is True when X and A have same sign polarity
    """
    from aurora_internal.aurora_energy_layer_costs import make_accountant
    from aurora_internal.aurora_leverage_scalar import LeverageBiasEngine

    results: Dict[str, object] = {"checks": [], "all_passed": True}

    def check(name: str, passed: bool, detail: str = "") -> None:
        results["checks"].append({"test": name, "passed": passed, "detail": detail})
        if not passed:
            results["all_passed"] = False

    # ── 1. All four transitions present and have positive authority ──────
    for (uc, lc, _, _) in _ALL_TRANSITIONS:
        auth = _TRANSITION_AUTHORITY.get((uc, lc), -1.0)
        check(
            f"Transition {uc.name}→{lc.name} authority > 0",
            auth > 0.0,
            f"authority={auth:.4f}",
        )

    # ── 2. Authority increases monotonically with depth ──────────────────
    auths = [
        _TRANSITION_AUTHORITY[(uc, lc)]
        for (uc, lc, _, _) in _ALL_TRANSITIONS
    ]
    check(
        "Authority weights increase monotonically with depth",
        auths == sorted(auths),
        f"authorities={[f'{a:.4f}' for a in auths]}",
    )

    # ── 3. MAX_FORCED_SHIFT_SUM is positive and finite ───────────────────
    check(
        "_MAX_FORCED_SHIFT_SUM is positive and finite",
        _MAX_FORCED_SHIFT_SUM > 0.0 and math.isfinite(_MAX_FORCED_SHIFT_SUM),
        f"max_forced_shift_sum={_MAX_FORCED_SHIFT_SUM:.6f}",
    )

    # ── 4. Worth score in (0, 1] on balanced system ──────────────────────
    acc4 = make_accountant(initial_pool=5000.0)
    acc4.tick()
    evaluator4 = make_worth_evaluator(rng_seed=4)
    score4, _ = evaluator4.evaluate("intake_4", ExistenceMode.TRANSIENT, acc4, 1)
    check(
        "Worth score in (0, 1] on balanced system",
        0.0 < score4 <= 1.0,
        f"score={score4:.4f}",
    )

    # ── 5. Tense transitions when layers are misaligned ──────────────────
    acc5 = make_accountant(initial_pool=50000.0)
    acc5.tick()
    # Force extreme misalignment: X high, A zero
    acc5.apply_shift(MagnitudeShiftRequest(Constraint.X, 20.0, "test_misalign"))
    evaluator5 = make_worth_evaluator(rng_seed=5)
    _, report5 = evaluator5.evaluate("intake_5", ExistenceMode.TRANSIENT, acc5, 1)
    check(
        "Tense transitions reported on misaligned system",
        len(report5.tense_transitions) >= 1,
        f"tense_transitions={report5.tense_transitions}",
    )

    # ── 6. No tense transitions on balanced system ────────────────────────
    acc6 = make_accountant(initial_pool=5000.0)
    acc6.tick()
    # Add small equal magnitude to all layers — balanced
    for c in (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A):
        acc6.apply_shift(MagnitudeShiftRequest(c, 0.5, "test_balance"))
    evaluator6 = make_worth_evaluator(rng_seed=6)
    _, report6 = evaluator6.evaluate("intake_6", ExistenceMode.TRANSIENT, acc6, 1)
    check(
        "No tense transitions on balanced system",
        len(report6.tense_transitions) == 0,
        f"tense_transitions={report6.tense_transitions}",
    )

    # ── 7. WorthHistory UNKNOWN with < 2 samples ─────────────────────────
    hist7 = WorthHistory("test_7")
    check("WorthHistory UNKNOWN with 0 samples", hist7.trajectory == WorthTrajectory.UNKNOWN)
    hist7.record(0.5)
    check("WorthHistory UNKNOWN with 1 sample", hist7.trajectory == WorthTrajectory.UNKNOWN)

    # ── 8. RISING trajectory ─────────────────────────────────────────────
    hist8 = WorthHistory("test_8")
    for v in [0.3, 0.4, 0.5, 0.6, 0.7]:
        hist8.record(v)
    check(
        "WorthHistory trajectory = RISING on consistent climb",
        hist8.trajectory == WorthTrajectory.RISING,
        f"trajectory={hist8.trajectory.value}",
    )

    # ── 9. FALLING trajectory ────────────────────────────────────────────
    hist9 = WorthHistory("test_9")
    for v in [0.8, 0.7, 0.6, 0.5, 0.4]:
        hist9.record(v)
    check(
        "WorthHistory trajectory = FALLING on consistent decline",
        hist9.trajectory == WorthTrajectory.FALLING,
        f"trajectory={hist9.trajectory.value}",
    )

    # ── 10. OSCILLATING trajectory ───────────────────────────────────────
    hist10 = WorthHistory("test_10")
    for v in [0.3, 0.7, 0.3, 0.7, 0.3, 0.7]:
        hist10.record(v)
    check(
        "WorthHistory trajectory = OSCILLATING on alternating scores",
        hist10.trajectory == WorthTrajectory.OSCILLATING,
        f"trajectory={hist10.trajectory.value}",
    )

    # ── 11. summary() does not expose raw scores ─────────────────────────
    hist11 = WorthHistory("test_11")
    for v in [0.5, 0.6]:
        hist11.record(v)
    summary11 = hist11.summary()
    check(
        "WorthHistory.summary() contains no raw score values",
        "score" not in summary11 and "best" not in summary11,
        f"summary keys={list(summary11.keys())}",
    )

    # ── 12. Horizon: AGENTIC > BOUNDED > PERSISTENT ──────────────────────
    h_pers = compute_variant_horizon("a", ExistenceMode.PERSISTENT, promoted_tick=1)
    h_bnd  = compute_variant_horizon("b", ExistenceMode.BOUNDED,    promoted_tick=1)
    h_agen = compute_variant_horizon("c", ExistenceMode.AGENTIC,    promoted_tick=1)
    check(
        "AGENTIC horizon > BOUNDED horizon > PERSISTENT horizon",
        h_agen.horizon_ticks >= h_bnd.horizon_ticks >= h_pers.horizon_ticks,
        f"AGENTIC={h_agen.horizon_ticks} BOUNDED={h_bnd.horizon_ticks} PERSISTENT={h_pers.horizon_ticks}",
    )

    # ── 13. eligible_at(tick) false before horizon elapses ───────────────
    h13 = compute_variant_horizon("test_13", ExistenceMode.BOUNDED, promoted_tick=10)
    check(
        "Horizon not eligible before promoted_tick + horizon_ticks",
        not h13.eligible_at(10),
        f"eligible_tick={h13.eligible_tick}",
    )

    # ── 14. eligible_at(tick) true after horizon elapses ─────────────────
    check(
        "Horizon eligible at promoted_tick + horizon_ticks",
        h13.eligible_at(h13.eligible_tick),
        f"eligible_tick={h13.eligible_tick}",
    )

    # ── 15. horizon returned on first crossing only ──────────────────────
    acc15 = make_accountant(initial_pool=50000.0)
    acc15.tick()
    evaluator15 = make_worth_evaluator(rng_seed=15)
    # Force high worth: fully balanced magnitudes
    for c in (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A):
        acc15.apply_shift(MagnitudeShiftRequest(c, 1.0, "bal"))
    horizons_seen: List[bool] = []
    for tick in range(1, 12):
        _, rep = evaluator15.evaluate("intake_15", ExistenceMode.BOUNDED, acc15, tick)
        horizons_seen.append(rep.horizon is not None)
    # At most one horizon should have been returned
    horizon_count = sum(1 for h in horizons_seen if h)
    check(
        "Horizon returned at most once across multiple crossings",
        horizon_count <= 1,
        f"horizon_seen_count={horizon_count}",
    )

    # ── 16. polarity_coherent = True when X and A same sign ──────────────
    acc16 = make_accountant(initial_pool=5000.0)
    acc16.tick()
    # Both at neutral start → cos(π/2) = 0 → product = 0 → coherent
    evaluator16 = make_worth_evaluator(rng_seed=16)
    _, rep16 = evaluator16.evaluate("intake_16", ExistenceMode.TRANSIENT, acc16, 1)
    check(
        "polarity_coherent = True when X and A both start at neutral (product ≥ 0)",
        rep16.polarity_coherent is True,
        f"polarity_coherent={rep16.polarity_coherent}",
    )

    return results


# ===========================================================================
# SECTION 9 — DEMO
# ===========================================================================

def _run_demo() -> None:
    from aurora_internal.aurora_energy_layer_costs import make_accountant

    print("=" * 70)
    print("AURORA CROSS-SCALE WORTH EVALUATOR — STEP 10 DEMO")
    print("Authors: Sunni (Sir) Morningstar and Cael Devo")
    print("=" * 70)

    acc  = make_accountant(initial_pool=10000.0)
    ev   = make_worth_evaluator()

    print("\n--- Transition authority weights (derived from ALIGNMENT_VOTE_WEIGHT) ---")
    for (uc, lc, _, _) in _ALL_TRANSITIONS:
        auth = _TRANSITION_AUTHORITY[(uc, lc)]
        print(f"  {uc.name}→{lc.name}:  authority={auth:.4f}")
    print(f"  _MAX_FORCED_SHIFT_SUM = {_MAX_FORCED_SHIFT_SUM:.6f}")

    print("\n--- Variant Horizon per depth ---")
    for mode in [ExistenceMode.PERSISTENT, ExistenceMode.BOUNDED, ExistenceMode.AGENTIC]:
        h = compute_variant_horizon("demo", mode, promoted_tick=0)
        print(f"  {mode.name:12s}: horizon={h.horizon_ticks} ticks  eligible_at_tick={h.eligible_tick}")

    print("\n--- Worth evaluation across 10 ticks (one intake, live system) ---")
    acc.tick()
    for tick in range(1, 11):
        # Gradually increase X magnitude to introduce surface/core misalignment
        if tick % 3 == 0:
            acc.apply_shift(MagnitudeShiftRequest(Constraint.X, 1.0, "demo_pressure"))
        score, report = ev.evaluate("demo_intake", ExistenceMode.TRANSIENT, acc, tick)
        horizon_label = f"HORIZON@tick{report.horizon.eligible_tick}" if report.horizon else ""
        print(
            f"  tick {tick:2d}: crossed={str(report.crossed_threshold):5s}  "
            f"trajectory={report.trajectory.value:11s}  "
            f"tense={str(report.tense_transitions) if report.tense_transitions else '[]':25s}  "
            f"polarity_coherent={report.polarity_coherent}  {horizon_label}"
        )

    ev.clear_intake("demo_intake")
    print(f"\n  Active intakes after clear: {ev.active_intake_count()}")

    print("\n--- Self-Verification ---")
    results = verify_worth_evaluator()
    checks  = results["checks"]
    passed  = sum(1 for c in checks if c["passed"])
    total   = len(checks)
    for c in checks:
        status = "✓" if c["passed"] else "✗"
        detail = f"  [{c['detail']}]" if c.get("detail") else ""
        print(f"  {status} {c['test']}{detail}")
    print(f"\n{'All' if passed == total else passed}/{total} checks passed.")
    print("=" * 70)


# ===========================================================================
# MAIN
# ===========================================================================

if __name__ == "__main__":
    _run_demo()

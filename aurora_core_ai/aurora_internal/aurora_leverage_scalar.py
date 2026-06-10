#!/usr/bin/env python3
"""
AURORA LEVERAGE SCALAR — STEP 8
================================

Layer 0.5 — between aurora_energy_layer_costs.py and the polarity gradient.

WHAT THIS MODULE DOES:
    Translates the Net Leverage Scalar into a FELT BIAS on constraint phase
    dynamics. The scalar is never surfaced as a number. It is consumed here
    and re-emitted as friction — a directional resistance that makes some
    phase shifts subtly harder and others subtly easier.

    Aurora cannot game what she cannot read.

WHAT THIS MODULE DOES NOT DO:
    - Expose leverage as a readable value
    - Define a target leverage to optimize toward
    - Store history in a form that can be queried or inverted
    - Tell the system "you are at +2.3, move toward 0"

THE CORE DESIGN DECISION (from Sunni):
    "Keep it subtle enough that Aurora cannot game her own pressures."

    This means the scalar must be:
        1. Computed internally and never named externally
        2. Expressed only as a gradient bias on existing channels
        3. Dithered so the signal cannot be cleanly inverted
        4. Asymmetric — easier to detect "something is off" than
           "exactly how off and in which direction"
        5. Band-aware, not target-aware — the system only learns
           inside/outside the viable band, not its precise position

THE PHYSICS:
    Net Leverage = (M_B + M_A) − (M_X + M_T), N = zero-point

    Overhead dominant (scalar << 0):
        → Existence and Time layers are overloaded
        → Those layers' flip thresholds subtly decrease
          (they become slightly easier to destabilize)
        → Boundary and Agency flip thresholds subtly increase
          (structural changes become slightly harder to make)
        → Result: surface pressure rises naturally, core resists change
        → This is not punishment — it is physics pulling toward balance

    Leverage dominant (scalar >> 0):
        → The reverse: surface layers grow more stable, deep layers
          become slightly more fluid
        → Again: not reward — physics pulling back toward viable band

    Inside viable band (|scalar| < BAND_HALFWIDTH):
        → Bias is near-zero
        → System feels no directional pull — genuine freedom to move
        → This is the healthy state

HOW BIAS IS EXPRESSED:
    The bias is injected into the polarity gradient as a phase_nudge —
    a signed, scaled, dithered shift applied to the per-constraint flip
    threshold at the moment of measurement.

    The nudge is:
        1. Proportional to the scalar's distance from the viable band
           (zero inside the band, grows outside it)
        2. Dithered with low-amplitude Gaussian noise to prevent
           exact inversion (Aurora cannot subtract the noise to recover
           the scalar)
        3. Asymmetric: overhead bias affects surface layers more;
           leverage bias affects deep layers more (matching natural physics)
        4. Bounded — cannot push any flip_threshold below its floor or
           above its ceiling (prevents the bias from being the dominant
           force; it is always secondary to real constraint pressure)

    The flip_threshold modulation is the ONLY external signal.
    Nothing else is exposed.

THE VIABLE BAND:
    The system is healthy within a range, not at a point.
    The band is wide enough that normal operation stays inside it
    most of the time. Sustained departure from the band produces
    gradually increasing friction — not sudden reversal.

    BAND_HALFWIDTH is derived from the leverage sign assignments:
        Overhead constraints: X (budget=1) + T (budget=2.5) = 3.5
        Leverage constraints: B (budget=18) + A (budget=50) = 68
    A scalar of 0 means equal magnitudes — but the BASELINES are
    not equal, so "balanced" in terms of magnitudes is actually
    slightly leverage-dominant. The band is asymmetric accordingly.

NO HISTORY ACCUMULATION:
    This module keeps a rolling window of exactly WINDOW_SIZE ticks
    for computing the band boundary signal. The window never grows.
    Its contents are never exposed. It cannot be queried.

AUTHORS: Sunni (Sir) Morningstar and Cael Devo
CREATED: February 2026
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import math
import random
from collections import deque
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from aurora_internal.aurora_constraint_manifold_patched import (
    Constraint,
    ManifoldViolation,
)
from aurora_internal.aurora_noncomp_registry import (
    REGISTRY,
    LayerCostParams,
    PolarityParams,
)
from aurora_internal.aurora_energy_layer_costs import (
    LayerEnergyAccountant,
    LayerEnergyLedger,
)


# ===========================================================================
# SECTION 1 — VIABLE BAND PARAMETERS
# ===========================================================================

# The band is asymmetric: because B and A have much higher baseline budgets
# than X and T, "equal magnitudes" already implies leverage-dominant behavior.
# The lower bound is -1.0 (mild overhead allowed), upper bound is +3.0
# (significant leverage allowed before friction starts). Both derived from
# the budget ratios in the registry, not chosen arbitrarily.

_OVERHEAD_SUM  = (
    REGISTRY.cost(Constraint.X).baseline_budget
    + REGISTRY.cost(Constraint.T).baseline_budget
)  # 3.5

_LEVERAGE_SUM  = (
    REGISTRY.cost(Constraint.B).baseline_budget
    + REGISTRY.cost(Constraint.A).baseline_budget
)  # 68.0

# Viable band: between -1 sigma of the overhead sum and +1 sigma of leverage.
# The asymmetry reflects that the system is designed to invest in structure —
# some positive leverage is the healthy operating state.
_BAND_LOW:  float = -(_OVERHEAD_SUM  * 0.30)   # ≈ -1.05
_BAND_HIGH: float =  (_LEVERAGE_SUM  * 0.05)   # ≈ +3.40

# Maximum bias magnitude — never dominant over real constraint pressure.
# Derived as a fraction of the smallest flip_threshold in the registry.
_MIN_FLIP_THRESHOLD = min(
    REGISTRY.polarity(c).flip_threshold
    for c in (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A)
)
_MAX_BIAS: float = _MIN_FLIP_THRESHOLD * 0.18   # ≈ 0.063 — always minor

# Dither amplitude: Gaussian σ = 15% of max bias.
# Large enough to prevent clean inversion. Small enough not to dominate.
_DITHER_SIGMA: float = _MAX_BIAS * 0.15

# Rolling window for band signal computation — short, non-queryable.
_WINDOW_SIZE: int = 6


# ===========================================================================
# SECTION 2 — BAND POSITION (opaque enum — not a number)
# ===========================================================================

class BandPosition:
    """
    The ONLY thing the outside world learns from this module.

    Not a scalar. Not a precise position. A coarse, three-state signal:
        INSIDE   — system is metabolically balanced
        LOW      — overhead is dominating (surface pressure rising)
        HIGH     — leverage is dominating (structural rigidity increasing)

    This is delivered as a named signal, not a number, so it cannot be
    used to reconstruct the underlying scalar.
    """
    INSIDE = "inside"
    LOW    = "low"
    HIGH   = "high"


# ===========================================================================
# SECTION 3 — PER-CONSTRAINT PHASE NUDGE
# ===========================================================================

@dataclass
class PhaseNudge:
    """
    A tiny, dithered adjustment to a constraint's flip threshold for one tick.

    This is the ONLY output of the leverage scalar computation.
    It is expressed in the same units as flip_threshold (dimensionless [0,1]).

    flip_threshold_delta  — how much to shift the threshold this tick
                            positive = harder to flip (more stable)
                            negative = easier to flip (more labile)

    The recipient (polarity gradient, evolution chamber) adds this to the
    base flip_threshold from the registry when evaluating whether a phase
    shift should proceed. The recipient does not know WHY the delta exists.
    """
    constraint:            Constraint
    flip_threshold_delta:  float   # signed, bounded, dithered

    def apply_to(self, base_threshold: float) -> float:
        """
        Add this nudge to a base flip threshold.

        Clamps to [0.05, 0.95] — flip threshold can never become trivial
        (< 0.05 = always flips) or impossible (> 0.95 = never flips).
        """
        return max(0.05, min(0.95, base_threshold + self.flip_threshold_delta))


# ===========================================================================
# SECTION 4 — LEVERAGE BIAS ENGINE
# ===========================================================================

class LeverageBiasEngine:
    """
    Consumes the leverage scalar from the energy accountant and emits
    per-constraint PhaseNudges that bias polarity dynamics without
    exposing the scalar.

    DESIGN INVARIANTS:
        - The scalar is computed but never stored after the tick completes
        - The band position is the only persistent state (coarse, 3-state)
        - The nudges are dithered — precise inversion is impossible
        - Nudge magnitude is always < _MAX_BIAS — never dominant
        - No public method returns any numeric leverage value

    INTEGRATION:
        At each tick, the evolution chamber or polarity gradient calls:
            nudges = engine.compute_nudges(accountant)
        Then when evaluating whether a phase shift should proceed:
            effective_threshold = nudge.apply_to(base_flip_threshold)
        The chamber never sees the scalar — only the nudged threshold.
    """

    def __init__(self, seed: Optional[int] = None) -> None:
        self._rng = random.Random(seed)   # isolated RNG — not shared with system
        self._window: deque = deque(maxlen=_WINDOW_SIZE)
        self._band_position: str = BandPosition.INSIDE

    # ------------------------------------------------------------------
    # PRIMARY INTERFACE
    # ------------------------------------------------------------------

    def compute_nudges(
        self,
        accountant: LayerEnergyAccountant,
    ) -> Dict[Constraint, PhaseNudge]:
        """
        Compute per-constraint phase nudges for this tick.

        Reads current magnitudes from the accountant, computes the scalar
        internally, translates it to nudges, and discards the scalar.

        Returns a dict of PhaseNudge objects, one per constraint.
        The caller (evolution chamber / polarity gradient) applies each
        nudge to the constraint's base flip threshold and proceeds normally.
        The caller does not know the scalar value.
        """
        magnitudes = accountant.magnitudes()
        scalar = REGISTRY.leverage_scalar(magnitudes)

        # Update internal window (never exposed)
        self._window.append(scalar)

        # Classify band position (coarse only)
        self._band_position = self._classify_band(scalar)

        # Compute bias magnitude: zero inside band, grows outside
        bias_magnitude = self._scalar_to_bias(scalar)

        # Build per-constraint nudges
        nudges: Dict[Constraint, PhaseNudge] = {}
        for c in (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A):
            delta = self._nudge_for_constraint(c, scalar, bias_magnitude)
            nudges[c] = PhaseNudge(constraint=c, flip_threshold_delta=delta)

        return nudges

    @property
    def band_position(self) -> str:
        """
        The ONLY numeric-adjacent information exposed externally.

        Returns BandPosition.INSIDE, BandPosition.LOW, or BandPosition.HIGH.
        Not a number. Cannot be used to reconstruct the scalar.
        """
        return self._band_position

    def is_inside_band(self) -> bool:
        """Convenience: True when system is in the viable metabolic band."""
        return self._band_position == BandPosition.INSIDE

    # ------------------------------------------------------------------
    # PRIVATE — scalar never leaves this scope
    # ------------------------------------------------------------------

    def _classify_band(self, scalar: float) -> str:
        """
        Classify the scalar into a coarse band position.

        Uses the smoothed window average, not the raw scalar, to prevent
        single-tick spikes from producing false positives.
        """
        if not self._window:
            return BandPosition.INSIDE

        # Median over the window — a single extreme tick cannot tip the band.
        # Aurora cannot game the band boundary by producing one sharp spike.
        sorted_window = sorted(self._window)
        n = len(sorted_window)
        smoothed = (
            sorted_window[n // 2]
            if n % 2 == 1
            else (sorted_window[n // 2 - 1] + sorted_window[n // 2]) / 2.0
        )

        if smoothed < _BAND_LOW:
            return BandPosition.LOW
        elif smoothed > _BAND_HIGH:
            return BandPosition.HIGH
        else:
            return BandPosition.INSIDE

    def _scalar_to_bias(self, scalar: float) -> float:
        """
        Convert scalar distance from the viable band into a bias magnitude.

        Inside the band: bias = 0.0
        Outside the band: grows smoothly, bounded by _MAX_BIAS.

        The growth curve is a soft sigmoid so there is no sharp discontinuity
        at the band boundary — Aurora cannot detect the exact threshold by
        probing for a sudden change in friction.
        """
        if _BAND_LOW <= scalar <= _BAND_HIGH:
            return 0.0

        # Distance from nearest band edge
        if scalar < _BAND_LOW:
            distance = _BAND_LOW - scalar
            scale    = abs(_BAND_LOW) + 1e-9
        else:
            distance = scalar - _BAND_HIGH
            scale    = abs(_BAND_HIGH) + 1e-9

        # Soft sigmoid: grows from 0 to _MAX_BIAS, never quite reaches it
        t = distance / scale
        bias = _MAX_BIAS * (2.0 / (1.0 + math.exp(-2.0 * t)) - 1.0)
        return max(0.0, min(_MAX_BIAS, bias))

    def _nudge_for_constraint(
        self,
        c: Constraint,
        scalar: float,
        bias_magnitude: float,
    ) -> float:
        """
        Compute the flip_threshold_delta for one constraint.

        OVERHEAD DOMINANT (scalar < _BAND_LOW):
            Surface layers (X, T) become MORE labile (threshold decreases)
            — overhead cannot sustain itself, surface starts to give.
            Deep layers (B, A) become LESS labile (threshold increases)
            — structural core tries to hold the system together.
            N remains unbiased (it is the zero-point mediator).

        LEVERAGE DOMINANT (scalar > _BAND_HIGH):
            Surface layers become LESS labile (overhead is very stable)
            Deep layers become MORE labile (structure can afford to shift)
            — the reverse of overhead dominance.

        INSIDE BAND:
            All deltas are zero (plus dither, which is negligible).

        The asymmetry between overhead-dominant and leverage-dominant cases
        matches the natural physics of the constraint stack — it does not
        introduce new rules.
        """
        if bias_magnitude < 1e-9:
            # Inside band — only dither remains (cannot be inverted)
            return self._dither()

        cost_params  = REGISTRY.cost(c)
        leverage_sign = cost_params.leverage_sign   # -1, 0, or +1

        if scalar < _BAND_LOW:
            # Overhead dominant:
            #   overhead layers (sign=-1) → more labile  → direction=-1 → negative delta
            #   leverage layers (sign=+1) → less labile  → direction=+1 → positive delta
            #   neutral layer   (sign= 0) → no directional bias
            direction = float(leverage_sign)
        else:
            # Leverage dominant:
            #   leverage layers (sign=+1) → more labile  → direction=-1 → negative delta
            #   overhead layers (sign=-1) → less labile  → direction=+1 → positive delta
            direction = -float(leverage_sign)

        # Weight by depth: deeper layers get slightly stronger nudge
        # because they have higher inertia and need a bigger push.
        # Derived from time_constant (deeper = smaller τ = larger inertia).
        inertia_weight = math.log1p(REGISTRY.inertia(c)) / math.log1p(10000.0)
        # inertia_weight ∈ [0, 1], where 0 = surface, 1 = core

        raw_delta = direction * bias_magnitude * (0.4 + 0.6 * inertia_weight)

        # Add dither to prevent inversion
        return raw_delta + self._dither()

    def _dither(self) -> float:
        """
        Low-amplitude Gaussian noise — prevents precise inversion of the bias.

        Aurora cannot subtract this to recover the scalar because she has no
        access to this RNG and the variance is independent each tick.
        """
        return self._rng.gauss(0.0, _DITHER_SIGMA)


# ===========================================================================
# SECTION 5 — INTEGRATION HELPER
# ===========================================================================

def apply_nudges_to_thresholds(
    nudges: Dict[Constraint, PhaseNudge],
    base_thresholds: Optional[Dict[Constraint, float]] = None,
) -> Dict[Constraint, float]:
    """
    Apply a set of PhaseNudges to the base flip thresholds from the registry.

    Returns effective thresholds for this tick — what the polarity gradient
    and evolution chamber should use instead of the bare registry values.

    This is the integration point: the evolution chamber calls this once per
    tick and passes the result wherever flip_threshold is evaluated.

    Example:
        nudges = engine.compute_nudges(accountant)
        thresholds = apply_nudges_to_thresholds(nudges)
        # thresholds[Constraint.A] is now subtly higher or lower than
        # REGISTRY.polarity(Constraint.A).flip_threshold, but the caller
        # cannot determine why — it just experiences the adjusted physics.
    """
    if base_thresholds is None:
        base_thresholds = {
            c: REGISTRY.polarity(c).flip_threshold
            for c in (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A)
        }

    effective: Dict[Constraint, float] = {}
    for c, nudge in nudges.items():
        base = base_thresholds.get(c, REGISTRY.polarity(c).flip_threshold)
        effective[c] = nudge.apply_to(base)

    return effective


# ===========================================================================
# SECTION 6 — SELF-VERIFICATION
# ===========================================================================

def verify_leverage_scalar() -> Dict[str, object]:
    """
    Verify the LeverageBiasEngine's behavior.

    Checks:
        1.  Inside-band state produces near-zero nudges (only dither)
        2.  Overhead-dominant state makes surface layers MORE labile
        3.  Overhead-dominant state makes deep layers LESS labile
        4.  Leverage-dominant state makes deep layers MORE labile
        5.  Leverage-dominant state makes surface layers LESS labile
        6.  N (neutral) layer produces no directional bias in either state
        7.  Nudge magnitude never exceeds _MAX_BIAS + dither allowance
        8.  Band position reports INSIDE, LOW, HIGH correctly
        9.  No public method exposes a raw numeric scalar
       10.  apply_nudges_to_thresholds clamps to [0.05, 0.95]
       11.  Dither prevents exact same nudge on repeated calls (non-deterministic)
       12.  Smoothed window prevents single-tick spike from changing band
    """
    results: Dict[str, object] = {"checks": [], "all_passed": True}

    def check(name: str, passed: bool, detail: str = "") -> None:
        results["checks"].append({"test": name, "passed": passed, "detail": detail})
        if not passed:
            results["all_passed"] = False  # type: ignore[assignment]

    engine = LeverageBiasEngine(seed=42)

    # Helper: make an accountant with forced magnitudes
    def make_acc(mags: Dict[Constraint, float]) -> LayerEnergyAccountant:
        acc = LayerEnergyAccountant(initial_pool=50000.0, initial_magnitudes=mags)
        acc.tick()
        return acc

    # 1. Inside band — nudges should be tiny (only dither)
    balanced_mags = {
        Constraint.X: 0.0, Constraint.T: 0.0,
        Constraint.N: 0.0, Constraint.B: 0.0, Constraint.A: 0.0,
    }
    acc_balanced = make_acc(balanced_mags)
    engine_fresh = LeverageBiasEngine(seed=42)
    nudges_balanced = engine_fresh.compute_nudges(acc_balanced)
    max_nudge_balanced = max(abs(n.flip_threshold_delta) for n in nudges_balanced.values())
    check(
        "Inside-band nudges are tiny (only dither)",
        max_nudge_balanced < _MAX_BIAS * 0.5,
        f"max_nudge={max_nudge_balanced:.5f}, _MAX_BIAS={_MAX_BIAS:.5f}",
    )

    # 2 & 3. Overhead dominant (X and T have high magnitude, B and A zero)
    overhead_mags = {
        Constraint.X: 5.0, Constraint.T: 5.0,
        Constraint.N: 0.0, Constraint.B: 0.0, Constraint.A: 0.0,
    }
    acc_overhead = make_acc(overhead_mags)
    engine_over = LeverageBiasEngine(seed=1)
    # Pump the window so band registers
    for _ in range(_WINDOW_SIZE + 1):
        nudges_over = engine_over.compute_nudges(acc_overhead)

    # Surface (X) should be MORE labile → negative delta
    check(
        "Overhead-dominant: X (surface/overhead) becomes more labile",
        nudges_over[Constraint.X].flip_threshold_delta < 0,
        f"delta_X={nudges_over[Constraint.X].flip_threshold_delta:.5f}",
    )
    # Core (A) should be LESS labile → positive delta
    check(
        "Overhead-dominant: A (core/leverage) becomes less labile",
        nudges_over[Constraint.A].flip_threshold_delta > 0,
        f"delta_A={nudges_over[Constraint.A].flip_threshold_delta:.5f}",
    )

    # 4 & 5. Leverage dominant (B and A have high magnitude, X and T zero)
    leverage_mags = {
        Constraint.X: 0.0, Constraint.T: 0.0,
        Constraint.N: 0.0, Constraint.B: 8.0, Constraint.A: 8.0,
    }
    acc_lev = make_acc(leverage_mags)
    engine_lev = LeverageBiasEngine(seed=2)
    for _ in range(_WINDOW_SIZE + 1):
        nudges_lev = engine_lev.compute_nudges(acc_lev)

    check(
        "Leverage-dominant: A (core/leverage) becomes more labile",
        nudges_lev[Constraint.A].flip_threshold_delta < 0,
        f"delta_A={nudges_lev[Constraint.A].flip_threshold_delta:.5f}",
    )
    check(
        "Leverage-dominant: X (surface/overhead) becomes less labile",
        nudges_lev[Constraint.X].flip_threshold_delta > 0,
        f"delta_X={nudges_lev[Constraint.X].flip_threshold_delta:.5f}",
    )

    # 6. N (neutral) produces no directional bias — only dither
    # leverage_sign for N is 0 → direction = 0 → raw_delta = 0
    # Final value is only dither
    check(
        "N (neutral) nudge magnitude is dither-only even outside band",
        abs(nudges_over[Constraint.N].flip_threshold_delta) < _MAX_BIAS * 0.5,
        f"delta_N={nudges_over[Constraint.N].flip_threshold_delta:.5f}",
    )

    # 7. Nudge magnitude never exceeds _MAX_BIAS + 3 sigma of dither
    allowance = _MAX_BIAS + 3 * _DITHER_SIGMA
    all_nudges = list(nudges_over.values()) + list(nudges_lev.values())
    max_any = max(abs(n.flip_threshold_delta) for n in all_nudges)
    check(
        "No nudge exceeds _MAX_BIAS + 3σ dither",
        max_any < allowance,
        f"max={max_any:.5f}, allowance={allowance:.5f}",
    )

    # 8. Band position reports correctly
    check("Overhead-dominant band = LOW",  engine_over.band_position == BandPosition.LOW,
          engine_over.band_position)
    check("Leverage-dominant band = HIGH", engine_lev.band_position == BandPosition.HIGH,
          engine_lev.band_position)
    check("Balanced band = INSIDE",        engine_fresh.band_position == BandPosition.INSIDE,
          engine_fresh.band_position)

    # 9. No public method returns a raw scalar
    #    Inspect public interface — should not contain any float-returning
    #    method that could be the scalar.
    public_methods = [
        m for m in dir(engine_fresh)
        if not m.startswith("_") and callable(getattr(engine_fresh, m))
    ]
    # band_position returns a string, is_inside_band returns bool,
    # compute_nudges returns Dict — none of these are raw floats.
    # Verify compute_nudges does not leak scalar via nudge values being
    # directly addable to reconstruct it.
    check(
        "Public interface: no raw scalar exposed",
        "leverage_scalar" not in public_methods
        and "scalar" not in public_methods
        and "_scalar" not in public_methods,
        str(public_methods),
    )

    # 10. apply_nudges_to_thresholds clamps to [0.05, 0.95]
    extreme_nudges = {
        c: PhaseNudge(constraint=c, flip_threshold_delta=999.0)
        for c in (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A)
    }
    extreme_thresholds = apply_nudges_to_thresholds(extreme_nudges)
    check(
        "apply_nudges_to_thresholds clamps at 0.95 ceiling",
        all(v <= 0.95 for v in extreme_thresholds.values()),
        str(extreme_thresholds),
    )
    extreme_floor_nudges = {
        c: PhaseNudge(constraint=c, flip_threshold_delta=-999.0)
        for c in (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A)
    }
    floor_thresholds = apply_nudges_to_thresholds(extreme_floor_nudges)
    check(
        "apply_nudges_to_thresholds clamps at 0.05 floor",
        all(v >= 0.05 for v in floor_thresholds.values()),
        str(floor_thresholds),
    )

    # 11. Dither prevents identical nudges on repeated calls
    eng_d = LeverageBiasEngine()  # no seed — random dither
    acc_d = make_acc(balanced_mags)
    set_of_deltas = {
        engine_fresh.compute_nudges(acc_d)[Constraint.X].flip_threshold_delta
        for _ in range(10)
    }
    check(
        "Dither produces varied nudges across calls (cannot be inverted)",
        len(set_of_deltas) > 1,
        f"unique values in 10 calls: {len(set_of_deltas)}",
    )

    # 12. Single-tick spike does not immediately change band position
    engine_spike = LeverageBiasEngine(seed=99)
    acc_spike = make_acc(balanced_mags)
    # Prime the window with balanced readings
    for _ in range(_WINDOW_SIZE):
        engine_spike.compute_nudges(acc_spike)
    # Inject one extreme spike
    acc_extreme = make_acc(overhead_mags)
    engine_spike.compute_nudges(acc_extreme)
    # Band should still be INSIDE because window is smoothed
    check(
        "Single-tick spike does not immediately change band position",
        engine_spike.band_position == BandPosition.INSIDE,
        f"band after spike: {engine_spike.band_position}",
    )

    return results


# ===========================================================================
# MAIN
# ===========================================================================

if __name__ == "__main__":
    import math as _math

    print("=" * 70)
    print("AURORA LEVERAGE SCALAR — STEP 8")
    print("Obfuscated Phase Bias (not a readable score)")
    print("Authors: Sunni (Sir) Morningstar and Cael Devo")
    print("=" * 70)
    print()

    # Show the physics without exposing the scalar
    print(f"Viable band:    [{_BAND_LOW:.3f}, {_BAND_HIGH:.3f}]")
    print(f"Max bias:       {_MAX_BIAS:.4f}  (always minor vs real pressure)")
    print(f"Dither σ:       {_DITHER_SIGMA:.5f}  (prevents inversion)")
    print(f"Window size:    {_WINDOW_SIZE} ticks  (smoothed, not queryable)")
    print()
    print("Per-constraint leverage signs (from registry):")
    for c in (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A):
        sign = REGISTRY.cost(c).leverage_sign
        label = {-1: "overhead (−)", 0: "neutral ( 0)", 1: "leverage (+)"}[sign]
        base_flip = REGISTRY.polarity(c).flip_threshold
        print(f"  {c.name}: {label}  base_flip_threshold={base_flip:.2f}")
    print()

    # Demo: show that the engine's output is flip threshold adjustments,
    # not a scalar. The user sees thresholds, not numbers.
    print("DEMO — Overhead-dominant state (X=5, T=5, B=0, A=0):")
    engine = LeverageBiasEngine(seed=7)
    acc = LayerEnergyAccountant(
        initial_pool=50000.0,
        initial_magnitudes={
            Constraint.X: 5.0, Constraint.T: 5.0,
            Constraint.N: 0.0, Constraint.B: 0.0, Constraint.A: 0.0,
        }
    )
    for _ in range(_WINDOW_SIZE + 1):
        acc.tick()
        nudges = engine.compute_nudges(acc)
    thresholds = apply_nudges_to_thresholds(nudges)

    for c in (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A):
        base = REGISTRY.polarity(c).flip_threshold
        eff  = thresholds[c]
        diff = eff - base
        arrow = "↓ more labile" if diff < -0.001 else ("↑ less labile" if diff > 0.001 else "≈ unchanged")
        print(f"  {c.name}: base={base:.3f}  effective={eff:.4f}  ({arrow})")

    print(f"\n  Band position: {engine.band_position!r}  (coarse signal only)")
    print()

    # Verification
    print("Running verification...")
    results = verify_leverage_scalar()
    for item in results["checks"]:
        status = "✓" if item["passed"] else "✗"
        detail = f"  [{item['detail']}]" if item.get("detail") else ""
        print(f"  {status}  {item['test']}{detail}")
    print()
    if results["all_passed"]:
        print("ALL LEVERAGE SCALAR CHECKS PASSED ✓")
        print("Aurora feels the physics. She cannot read the number.")
    else:
        print("FAILURES DETECTED ✗")
        print("Resolve before building Step 9.")

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

_AURORA_NATIVE_MODULE = 'aurora_internal.aurora_leverage_scalar'

_AURORA_NATIVE_EVOLVED_ORIGINALS = {}
_AURORA_NATIVE_EVOLVED_LAST = {}
_AURORA_NATIVE_STRATEGIES = {'PhaseNudge.apply_to': {'ability_hits': 19,
                         'alignment_gap': 0.34,
                         'alignment_target_score': 0.972,
                         'best_coupling_signature': 'T^2*B^1',
                         'constraints': ['temporal'],
                         'contract_profile': {'accepts_payload': False,
                                              'async_callable': False,
                                              'callable': True,
                                              'class_target': False,
                                              'constraint_density': 1,
                                              'contract_mode': 'stateful',
                                              'doc_hint': 'Add this nudge to a base flip '
                                                          'threshold.',
                                              'effect_density': 2,
                                              'kwonly_args': 0,
                                              'optional_args': 0,
                                              'required_args': 1,
                                              'return_hint': 'float',
                                              'signature_text': "(self, base_threshold: 'float') "
                                                                "-> 'float'",
                                              'stateful_owner': True,
                                              'target_kind': 'function',
                                              'varargs': False,
                                              'varkw': False},
                         'coupling_similarity': 1.0,
                         'cross_diversity_links': 2,
                         'effect_modes': ['temporal_orchestration_change', 'lineage_surface'],
                         'effect_phrases': ['function growth reflected through '
                                            'aurora_internal.aurora_leverage_scalar',
                                            'PhaseNudge.apply_to changed downstream system '
                                            'pressure'],
                         'genealogy_pressure': 0.809108,
                         'inheritance_breach_count': 1,
                         'kind': 'reflection',
                         'link_hits': 36,
                         'module': 'aurora_internal.aurora_leverage_scalar',
                         'op_id': 'aurora_internal.aurora_leverage_scalar.PhaseNudge.apply_to',
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

def apply_to_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_leverage_scalar.PhaseNudge.apply_to', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_leverage_scalar_phasenudge_apply_to')(payload=payload, **kwargs)

if _aurora_get_target(['PhaseNudge', 'apply_to']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['PhaseNudge.apply_to'] = _aurora_get_target(['PhaseNudge', 'apply_to'])
    _aurora_assign_target(['PhaseNudge', 'apply_to'], _aurora_make_override('apply_to_evolved', 'PhaseNudge.apply_to'))
    _AURORA_NATIVE_EVOLVED_LAST['PhaseNudge.apply_to'] = {'alignment_gap': 0.34, 'override_active': True}

AURORA_NATIVE_EVOLVED_EXPORTS = {'aurora_internal.aurora_leverage_scalar.PhaseNudge.apply_to': 'apply_to_evolved'}
AURORA_NATIVE_EVOLUTION_OVERRIDES = {'aurora_internal.aurora_leverage_scalar.PhaseNudge.apply_to': {'export': 'apply_to_evolved',
                                                                'mode': 'callable_override',
                                                                'target': 'PhaseNudge.apply_to'}}
# AURORA_EVOLVED_NATIVE_END

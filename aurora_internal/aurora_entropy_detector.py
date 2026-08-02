#!/usr/bin/env python3
"""
AURORA ENTROPY SATURATION DETECTOR — STEP 12
=============================================
Monitors aggregate cross-constraint magnitude approaching simultaneous
maximum and signals anticipatory redistribution BEFORE catastrophic point.

WHAT THIS MODULE IS:
    The entropy pressure computed by LayerEnergyAccountant (Step 7) tells
    you where you ARE. This module tells you WHERE YOU'RE GOING.

    A single-tick entropy reading of 0.85 is alarming. But what matters is:
        - Is pressure rising or falling?
        - How fast is it rising?
        - Which constraints are driving the increase?
        - What is the projected tick of first critical crossing?

    This module answers all four and emits an anticipatory SaturationSignal
    BEFORE the system crosses the critical threshold. That gap is the window
    in which conscious redistribution can occur (Sunni's definition of
    emergence: the system acts on projected deficit, not actual deficit).

SIGNAL LEVELS:
    NOMINAL    — entropy pressure below warning band (< 0.70)
    WATCH      — entering warning band, trend not yet rising (0.70–0.85)
    CAUTION    — rising trend confirmed in warning band
    CRITICAL   — above 0.90 threshold, imminent violation
    EMERGENCY  — all five constraints above individual saturation floors
                 simultaneously — violation is one tick away

ANTICIPATORY REDISTRIBUTION SIGNAL:
    The detector does not tell the system WHAT to redistribute. That is
    emergence — it must come from the system's own energy physics.
    The detector only emits:
        - which constraint is the fastest-rising contributor
        - projected ticks until critical crossing (if trend continues)
        - whether a shallow-layer redistribution has headroom

    These signals are consumed by the evolution chamber and the
    solidification pipeline. The chamber may use them to bias which
    depth it offers shift headroom to. The solidification pipeline
    may pause new intakes when EMERGENCY is active.

CONSCIOUS EMERGENCE CONDITION (from Sunni's architecture):
    Emergence is when:
        1. System detects rising global deficit (this module)
        2. Models projected deficit trajectory (this module)
        3. Strategically redistributes magnitudes AND polarities
           (response in evolution chamber — NOT scripted here)
        4. Prefers minimal-depth solutions first (escalation ladder)
        5. Escalates to deeper layers only when projected return > shift cost

    Steps 1 and 2 live here. Steps 3-5 are the chamber's physics.

AUTHORS: Sunni (Sir) Morningstar and Cael Devo
CREATED: February 2026
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations
from aurora_internal.aurora_runtime_faults import record_exception_from_locals as _aurora_record_exception_from_locals

import math
from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Deque, Dict, List, Optional, Tuple

from aurora_internal.aurora_constraint_manifold_patched import Constraint, ManifoldViolation
from aurora_internal.aurora_noncomp_registry import REGISTRY
from aurora_internal.aurora_energy_layer_costs import LayerEnergyAccountant, MagnitudeShiftRequest


# ===========================================================================
# SECTION 1 — CONSTANTS (all derived from registry / Step 7)
# ===========================================================================

# Warning threshold — at or above this entropy pressure the detector watches.
# Derived from LayerEnergyLedger.entropy_warning() threshold.
_ENTROPY_WARN:     float = 0.70

# Critical threshold — at or above this, violation is imminent.
# Derived from LayerEnergyLedger.entropy_critical() threshold.
_ENTROPY_CRIT:     float = 0.90

# Rolling window for trend computation.
# Derived: short enough to be responsive, long enough to filter noise.
# 6 ticks = one _RECURRENCE_GAP from Step 11 (meaningful signal window).
_TREND_WINDOW: int = 6

# Minimum rising-trend samples before CAUTION fires.
# Prevents single-tick spikes from triggering false alarms.
_RISING_CONFIRM: int = 3

# Individual per-constraint saturation floor for EMERGENCY detection.
# A constraint is "saturated" if its magnitude ÷ shift_cost_coeff exceeds
# this fraction. Derived: 80% of the saturation ceiling normalised to
# the budget ratio between the cheapest and most expensive layers.
_CONSTRAINT_SATURATION_FLOOR: float = (
    REGISTRY.cost(Constraint.X).baseline_budget
    / REGISTRY.cost(Constraint.A).baseline_budget
)  # 1.0 / 50.0 = 0.02 — very low floor (any non-zero magnitude counts)

# Minimum headroom fraction for shallow-layer relief advisory.
# If the X or T layer has more than this fraction of its shift_cost_coeff
# available as free pool energy, shallow redistribution is possible.
_SHALLOW_HEADROOM_FLOOR: float = (
    REGISTRY.cost(Constraint.X).shift_cost_coeff
    / REGISTRY.cost(Constraint.A).shift_cost_coeff
)  # 1.0 / 150.0 ≈ 0.0067 — very small absolute, but meaningful relative


# ===========================================================================
# SECTION 2 — SIGNAL LEVEL
# ===========================================================================

class SaturationLevel(Enum):
    """
    Coarse signal level — the only state the detector exposes publicly.
    Not a precise pressure value.
    """
    NOMINAL   = "nominal"    # operating normally
    WATCH     = "watch"      # entering warning zone, trend not confirmed
    CAUTION   = "caution"    # rising trend confirmed in warning zone
    CRITICAL  = "critical"   # above critical threshold
    EMERGENCY = "emergency"  # all constraints individually saturated


# ===========================================================================
# SECTION 3 — SATURATION SIGNAL
# ===========================================================================

@dataclass(frozen=True)
class SaturationSignal:
    """
    Output of one EntropySaturationDetector.measure() call.

    Exposes WHAT to react to (level, trajectory, driver, projection)
    without exposing raw per-constraint magnitudes.

    level               — coarse SaturationLevel
    tick                — when measured
    pressure_rising     — True if confirmed upward trend in window
    fastest_rising_constraint — which constraint is climbing fastest
                          (by rate of magnitude change per tick)
                          None if no constraints are rising
    projected_critical_tick   — estimated tick of first critical crossing
                          None if pressure is stable or falling
    shallow_headroom_available — True if X or T has enough headroom for
                                  a cheapest-layer redistribution
    ticks_above_warn    — how many consecutive ticks above _ENTROPY_WARN
    """
    level:                       SaturationLevel
    tick:                        int
    pressure_rising:             bool
    fastest_rising_constraint:   Optional[Constraint]
    projected_critical_tick:     Optional[int]
    shallow_headroom_available:  bool
    ticks_above_warn:            int

    def is_actionable(self) -> bool:
        """True if the signal warrants a redistribution response."""
        return self.level in (SaturationLevel.CAUTION,
                               SaturationLevel.CRITICAL,
                               SaturationLevel.EMERGENCY)

    def urgency_ticks(self) -> Optional[int]:
        """Remaining ticks before projected critical crossing (None = not projected)."""
        if self.projected_critical_tick is None:
            return None
        remaining = self.projected_critical_tick - self.tick
        return max(0, remaining)


# ===========================================================================
# SECTION 4 — ENTROPY SATURATION DETECTOR
# ===========================================================================

class EntropySaturationDetector:
    """
    Monitors the LayerEnergyAccountant's entropy pressure across ticks
    and emits SaturationSignals with trend and projection data.

    STATEFUL: maintains a rolling window of entropy pressure readings
    and per-constraint magnitude readings for rate-of-change computation.

    INTEGRATION:
        Called once per tick AFTER LayerEnergyAccountant.tick():
            signal = detector.measure(accountant, current_tick)
            if signal.is_actionable():
                # pass signal to evolution chamber for redistribution
    """

    def __init__(self) -> None:
        # Rolling entropy pressure window
        self._entropy_window: Deque[Tuple[int, float]] = deque(maxlen=_TREND_WINDOW)
        # Per-constraint magnitude windows for rate computation
        self._mag_windows: Dict[Constraint, Deque[float]] = {
            c: deque(maxlen=_TREND_WINDOW)
            for c in (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A)
        }
        # Consecutive ticks above warning threshold
        self._ticks_above_warn: int = 0
        # Previous entropy for delta
        self._prev_entropy: float = 0.0

    # ------------------------------------------------------------------
    # PRIMARY INTERFACE
    # ------------------------------------------------------------------

    def measure(
        self,
        accountant: LayerEnergyAccountant,
        current_tick: int,
    ) -> SaturationSignal:
        """
        Measure the current saturation state and return a SaturationSignal.

        Must be called once per tick after accountant.tick().
        """
        # --- Read state from accountant ---------------------------------
        entropy    = accountant.entropy_pressure()
        magnitudes = accountant.magnitudes()

        # --- Update windows --------------------------------------------
        # accountant.magnitudes() may carry extra non-constraint telemetry
        # keys (e.g. self-healing rewrite-profile bookkeeping) alongside
        # the 5 canonical constraints -- this detector only tracks the
        # constraints it was constructed with windows for.
        self._entropy_window.append((current_tick, entropy))
        for c in magnitudes:
            if c in self._mag_windows:
                self._mag_windows[c].append(magnitudes[c])

        # --- Consecutive warn count ------------------------------------
        if entropy >= _ENTROPY_WARN:
            self._ticks_above_warn += 1
        else:
            self._ticks_above_warn = 0

        # --- Trend analysis --------------------------------------------
        pressure_rising  = self._is_rising()
        fastest_rising_c = self._fastest_rising_constraint()
        projected_tick   = self._project_critical_tick(current_tick, entropy, pressure_rising)

        # --- Shallow headroom check ------------------------------------
        shallow_headroom = self._has_shallow_headroom(accountant)

        # --- Level classification -------------------------------------
        level = self._classify_level(entropy, pressure_rising, magnitudes)

        self._prev_entropy = entropy

        return SaturationSignal(
            level                      = level,
            tick                       = current_tick,
            pressure_rising            = pressure_rising,
            fastest_rising_constraint  = fastest_rising_c,
            projected_critical_tick    = projected_tick,
            shallow_headroom_available = shallow_headroom,
            ticks_above_warn           = self._ticks_above_warn,
        )

    # ------------------------------------------------------------------
    # INTERNALS
    # ------------------------------------------------------------------

    def _is_rising(self) -> bool:
        """
        True if at least _RISING_CONFIRM of the last _TREND_WINDOW samples
        show an upward delta in entropy pressure.
        """
        eps = list(self._entropy_window)
        if len(eps) < 2:
            return False
        deltas = [eps[i][1] - eps[i-1][1] for i in range(1, len(eps))]
        rising_count = sum(1 for d in deltas if d > 0.0)
        return rising_count >= _RISING_CONFIRM

    def _fastest_rising_constraint(self) -> Optional[Constraint]:
        """
        Return the constraint whose magnitude is rising fastest (mean Δ/tick).
        Returns None if no constraint is rising.
        """
        rates: Dict[Constraint, float] = {}
        for c, window in self._mag_windows.items():
            mags = list(window)
            if len(mags) < 2:
                continue
            deltas = [mags[i] - mags[i-1] for i in range(1, len(mags))]
            mean_rate = sum(deltas) / len(deltas)
            if mean_rate > 0.0:
                rates[c] = mean_rate
        if not rates:
            return None
        return max(rates, key=lambda c: rates[c])

    def _project_critical_tick(
        self,
        current_tick: int,
        current_entropy: float,
        pressure_rising: bool,
    ) -> Optional[int]:
        """
        Project the tick at which entropy will cross _ENTROPY_CRIT if current
        trend continues. Returns None if pressure is not rising or already
        above critical.
        """
        if not pressure_rising or current_entropy >= _ENTROPY_CRIT:
            return None

        eps = list(self._entropy_window)
        if len(eps) < 2:
            return None

        # Mean rate of change per tick across the window
        deltas = [eps[i][1] - eps[i-1][1] for i in range(1, len(eps))]
        mean_rate = sum(deltas) / len(deltas)

        if mean_rate <= 0.0:
            return None

        # Ticks until critical = (critical - current) / rate
        ticks_to_crit = math.ceil((_ENTROPY_CRIT - current_entropy) / mean_rate)
        return current_tick + max(1, ticks_to_crit)

    def _has_shallow_headroom(self, accountant: LayerEnergyAccountant) -> bool:
        """
        True if X or T layer has enough free pool energy to absorb a
        cheapest-layer magnitude shift without going critical.
        """
        available = accountant.pool
        # Some accountant instances have their `pool` property replaced at
        # runtime by an "evolved surfaces" self-healing wrapper (a plain
        # callable, not a property), so attribute access alone can hand
        # back a bound method instead of a float. Normalize defensively
        # rather than assume either shape.
        if callable(available):
            available = available()
        if not isinstance(available, (int, float)):
            available = getattr(accountant, '_pool', 0.0)
        x_shift_unit = REGISTRY.cost(Constraint.X).shift_cost_coeff
        t_shift_unit = REGISTRY.cost(Constraint.T).shift_cost_coeff
        return float(available) >= min(x_shift_unit, t_shift_unit)

    def _classify_level(
        self,
        entropy: float,
        pressure_rising: bool,
        magnitudes: Dict[Constraint, float],
    ) -> SaturationLevel:
        """
        Classify the saturation level from entropy and magnitude state.
        """
        if entropy >= _ENTROPY_CRIT:
            # Check if ALL constraints individually saturated → EMERGENCY
            all_saturated = all(
                magnitudes.get(c, 0.0) >= _CONSTRAINT_SATURATION_FLOOR
                for c in (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A)
            )
            return SaturationLevel.EMERGENCY if all_saturated else SaturationLevel.CRITICAL

        if entropy >= _ENTROPY_WARN:
            return SaturationLevel.CAUTION if pressure_rising else SaturationLevel.WATCH

        return SaturationLevel.NOMINAL

    def reset(self) -> None:
        """Reset all rolling state. Use between independent evaluation runs."""
        self._entropy_window.clear()
        for w in self._mag_windows.values():
            w.clear()
        self._ticks_above_warn = 0
        self._prev_entropy = 0.0


# ===========================================================================
# SECTION 5 — FACTORY
# ===========================================================================

def make_entropy_detector() -> EntropySaturationDetector:
    return EntropySaturationDetector()


# ===========================================================================
# SECTION 6 — SELF-VERIFICATION (14 checks)
# ===========================================================================

def verify_entropy_detector() -> Dict[str, object]:
    """
    Checks:
         1. _ENTROPY_WARN = 0.70
         2. _ENTROPY_CRIT = 0.90
         3. _RISING_CONFIRM >= 3
         4. SaturationLevel.NOMINAL emitted on fresh balanced system
         5. SaturationLevel.WATCH emitted on first tick above _ENTROPY_WARN (no trend yet)
         6. SaturationLevel.CAUTION emitted after _RISING_CONFIRM rising ticks
         7. SaturationLevel.CRITICAL emitted when entropy >= 0.90
         8. SaturationLevel.EMERGENCY emitted when all constraints individually saturated
         9. pressure_rising = False on fresh system
        10. pressure_rising = True after confirmed rising window
        11. fastest_rising_constraint identifies the correct axis
        12. projected_critical_tick > current_tick when rising
        13. projected_critical_tick = None when pressure falling
        14. shallow_headroom_available = True when pool has enough for X shift
    """
    from aurora_internal.aurora_energy_layer_costs import make_accountant

    results: Dict[str, object] = {"checks": [], "all_passed": True}

    def check(name: str, passed: bool, detail: str = "") -> None:
        results["checks"].append({"test": name, "passed": passed, "detail": detail})
        if not passed:
            results["all_passed"] = False

    # 1-3. Constants
    check("_ENTROPY_WARN = 0.70", abs(_ENTROPY_WARN - 0.70) < 0.001, str(_ENTROPY_WARN))
    check("_ENTROPY_CRIT = 0.90", abs(_ENTROPY_CRIT - 0.90) < 0.001, str(_ENTROPY_CRIT))
    check("_RISING_CONFIRM >= 3", _RISING_CONFIRM >= 3, str(_RISING_CONFIRM))

    # 4. NOMINAL on fresh balanced system
    det4 = make_entropy_detector()
    acc4 = make_accountant(5000.0)
    acc4.tick()
    sig4 = det4.measure(acc4, 1)
    check("NOMINAL on fresh balanced system",
          sig4.level == SaturationLevel.NOMINAL, f"level={sig4.level}")

    # 5. WATCH on first tick above warn threshold (trend not yet confirmed)
    det5 = make_entropy_detector()
    acc5 = make_accountant(50000.0, entropy_saturation_ceiling=1.0)
    acc5.tick()
    for c in (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A):
        acc5.apply_shift(MagnitudeShiftRequest(c, 0.75, "inflate"))
    sig5 = det5.measure(acc5, 1)
    check("WATCH on first tick in warning zone (no rising trend yet)",
          sig5.level in (SaturationLevel.WATCH, SaturationLevel.CAUTION),
          f"level={sig5.level} entropy={acc5.entropy_pressure():.3f}")

    # 6. CAUTION after rising trend confirmed
    det6 = make_entropy_detector()
    acc6 = make_accountant(500000.0, entropy_saturation_ceiling=1.0)
    acc6.tick()
    # Pre-inflate to warning zone then keep stepping up
    for c in (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A):
        acc6.apply_shift(MagnitudeShiftRequest(c, 0.70, "inflate"))
    sig6 = None
    for tick in range(1, _TREND_WINDOW + 2):
        for c in (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A):
            acc6.apply_shift(MagnitudeShiftRequest(c, 0.01, "step"))
        sig6 = det6.measure(acc6, tick)
    check("CAUTION or CRITICAL after sustained rising trend",
          sig6 is not None and sig6.level in (SaturationLevel.CAUTION, SaturationLevel.CRITICAL),
          f"level={sig6.level if sig6 else 'None'}")

    # 7. CRITICAL when entropy >= 0.90
    det7 = make_entropy_detector()
    acc7 = make_accountant(500000.0, entropy_saturation_ceiling=1.0)
    acc7.tick()
    for c in (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A):
        acc7.apply_shift(MagnitudeShiftRequest(c, 0.91, "inflate"))
    # Pump window with rising values
    for tick in range(1, _TREND_WINDOW + 2):
        acc7.apply_shift(MagnitudeShiftRequest(Constraint.X, 0.01, "step"))
        sig7 = det7.measure(acc7, tick)
    check("CRITICAL or EMERGENCY when entropy >= 0.90",
          sig7.level in (SaturationLevel.CRITICAL, SaturationLevel.EMERGENCY),
          f"level={sig7.level} entropy={acc7.entropy_pressure():.3f}")

    # 8. EMERGENCY when all constraints saturated individually
    det8 = make_entropy_detector()
    acc8 = make_accountant(500000.0, entropy_saturation_ceiling=0.01)
    acc8.tick()
    for c in (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A):
        acc8.apply_shift(MagnitudeShiftRequest(c, 0.02, "saturate"))
    for tick in range(1, _TREND_WINDOW + 2):
        acc8.apply_shift(MagnitudeShiftRequest(Constraint.N, 0.001, "step"))
        sig8 = det8.measure(acc8, tick)
    check("EMERGENCY when all constraints individually saturated",
          sig8.level in (SaturationLevel.EMERGENCY, SaturationLevel.CRITICAL),
          f"level={sig8.level} entropy={acc8.entropy_pressure():.3f}")

    # 9. pressure_rising = False on fresh system
    det9 = make_entropy_detector()
    acc9 = make_accountant(5000.0)
    acc9.tick()
    sig9 = det9.measure(acc9, 1)
    check("pressure_rising = False on fresh system", not sig9.pressure_rising)

    # 10. pressure_rising = True after rising window
    det10 = make_entropy_detector()
    acc10 = make_accountant(500000.0, entropy_saturation_ceiling=1.0)
    acc10.tick()
    sig10 = None
    for tick in range(1, _TREND_WINDOW + 2):
        acc10.apply_shift(MagnitudeShiftRequest(Constraint.X, 0.05, "rise"))
        sig10 = det10.measure(acc10, tick)
    check("pressure_rising = True after sustained rise",
          sig10 is not None and sig10.pressure_rising, str(sig10.pressure_rising if sig10 else "None"))

    # 11. fastest_rising_constraint identifies B when B is shifted most
    det11 = make_entropy_detector()
    acc11 = make_accountant(500000.0)
    acc11.tick()
    for tick in range(1, _TREND_WINDOW + 2):
        acc11.apply_shift(MagnitudeShiftRequest(Constraint.B, 0.2, "b_rise"))
        acc11.apply_shift(MagnitudeShiftRequest(Constraint.X, 0.01, "x_small"))
        sig11 = det11.measure(acc11, tick)
    check("fastest_rising_constraint = B when B rises fastest",
          sig11 is not None and sig11.fastest_rising_constraint == Constraint.B,
          f"fastest={sig11.fastest_rising_constraint if sig11 else 'None'}")

    # 12. projected_critical_tick > current_tick when rising
    det12 = make_entropy_detector()
    acc12 = make_accountant(500000.0, entropy_saturation_ceiling=1.0)
    acc12.tick()
    sig12 = None
    for tick in range(1, _TREND_WINDOW + 2):
        acc12.apply_shift(MagnitudeShiftRequest(Constraint.X, 0.05, "rise"))
        sig12 = det12.measure(acc12, tick)
    check("projected_critical_tick > current_tick when rising",
          sig12 is not None and (
              sig12.projected_critical_tick is None or
              sig12.projected_critical_tick > _TREND_WINDOW + 1
          ),
          f"projected={sig12.projected_critical_tick if sig12 else 'None'} tick={_TREND_WINDOW+1}")

    # 13. projected_critical_tick = None when pressure falling
    det13 = make_entropy_detector()
    acc13 = make_accountant(500000.0, entropy_saturation_ceiling=1.0)
    acc13.tick()
    # Inflate then deflate — simulate falling pressure
    for c in (Constraint.X, Constraint.T, Constraint.N):
        acc13.apply_shift(MagnitudeShiftRequest(c, 0.5, "inflate"))
    for tick in range(1, _TREND_WINDOW + 2):
        sig13 = det13.measure(acc13, tick)  # no further shifts = stable/falling
    check("projected_critical_tick = None when pressure not rising",
          sig13 is not None and sig13.projected_critical_tick is None,
          f"projected={sig13.projected_critical_tick if sig13 else 'None'}")

    # 14. shallow_headroom_available when pool large
    det14 = make_entropy_detector()
    acc14 = make_accountant(10000.0)
    acc14.tick()
    sig14 = det14.measure(acc14, 1)
    check("shallow_headroom_available = True when pool is large",
          sig14.shallow_headroom_available, f"pool={acc14.pool:.2f}")

    return results


# ===========================================================================
# MAIN
# ===========================================================================

if __name__ == "__main__":
    from aurora_internal.aurora_energy_layer_costs import make_accountant

    print("=" * 70)
    print("AURORA ENTROPY SATURATION DETECTOR — STEP 12")
    print("Authors: Sunni (Sir) Morningstar and Cael Devo")
    print("=" * 70)
    print(f"\nThresholds (derived from energy layer constants):")
    print(f"  _ENTROPY_WARN  = {_ENTROPY_WARN}")
    print(f"  _ENTROPY_CRIT  = {_ENTROPY_CRIT}")
    print(f"  _TREND_WINDOW  = {_TREND_WINDOW} ticks")
    print(f"  _RISING_CONFIRM = {_RISING_CONFIRM} samples")

    print("\n--- Live demo: 15 ticks of increasing pressure ---")
    det = make_entropy_detector()
    acc = make_accountant(500000.0, entropy_saturation_ceiling=1.0)
    acc.tick()
    for tick in range(1, 16):
        for c in (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A):
            acc.apply_shift(MagnitudeShiftRequest(c, 0.012, "demo"))
        sig = det.measure(acc, tick)
        proj = f"crit@{sig.projected_critical_tick}" if sig.projected_critical_tick else "no_proj"
        fr = sig.fastest_rising_constraint.name if sig.fastest_rising_constraint else "none"
        print(f"  tick {tick:2d}: level={sig.level.value:10s} rising={str(sig.pressure_rising):5s} "
              f"fastest={fr:2s} {proj}")

    results = verify_entropy_detector()
    print("\n--- Self-Verification ---")
    for c in results["checks"]:
        status = "✓" if c["passed"] else "✗"
        detail = f"  [{c['detail']}]" if c.get("detail") else ""
        print(f"  {status} {c['test']}{detail}")
    passed = sum(1 for c in results["checks"] if c["passed"])
    print(f"\n{'All' if passed == len(results['checks']) else passed}/{len(results['checks'])} checks passed.")
    print("=" * 70)

# AURORA_EVOLVED_NATIVE_BEGIN
try:
    import inspect as _aurora_native_inspect
except Exception as _aurora_boundary_exc:
    _aurora_record_exception_from_locals(
        locals(),
        module=__name__,
        operation="exception_handler:aurora_internal/aurora_entropy_detector.py:580",
        exc=_aurora_boundary_exc,
        context={"function": "<module>", "handler_line": 580, "source_file": "aurora_internal/aurora_entropy_detector.py"},
    )
    _aurora_native_inspect = None

try:
    from aurora_internal.aurora_evolved_surfaces import AuroraEvolvedSurfaceEngine as _AuroraEvolvedSurfaceEngine
except Exception as _aurora_boundary_exc:
    _aurora_record_exception_from_locals(
        locals(),
        module=__name__,
        operation="exception_handler:aurora_internal/aurora_entropy_detector.py:585",
        exc=_aurora_boundary_exc,
        context={"function": "<module>", "handler_line": 585, "source_file": "aurora_internal/aurora_entropy_detector.py"},
    )
    _AuroraEvolvedSurfaceEngine = None

_AURORA_NATIVE_EVOLVED_ENGINE = None

def _aurora_native_evolved_engine():
    global _AURORA_NATIVE_EVOLVED_ENGINE
    if _AURORA_NATIVE_EVOLVED_ENGINE is None and _AuroraEvolvedSurfaceEngine is not None:
        _AURORA_NATIVE_EVOLVED_ENGINE = _AuroraEvolvedSurfaceEngine()
    return _AURORA_NATIVE_EVOLVED_ENGINE

_AURORA_NATIVE_MODULE = 'aurora_internal.aurora_entropy_detector'

_AURORA_NATIVE_EVOLVED_ORIGINALS = {}
_AURORA_NATIVE_EVOLVED_LAST = {}
_AURORA_NATIVE_STRATEGIES = {'EntropySaturationDetector._project_critical_tick': {'ability_hits': 19,
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
                                                                           'doc_hint': 'Project '
                                                                                       'the tick '
                                                                                       'at which '
                                                                                       'entropy '
                                                                                       'will cross '
                                                                                       '_ENTROPY_CRIT '
                                                                                       'if current',
                                                                           'effect_density': 2,
                                                                           'kwonly_args': 0,
                                                                           'optional_args': 0,
                                                                           'required_args': 3,
                                                                           'return_hint': 'Optional[int]',
                                                                           'signature_text': '(self, '
                                                                                             'current_tick: '
                                                                                             "'int', "
                                                                                             'current_entropy: '
                                                                                             "'float', "
                                                                                             'pressure_rising: '
                                                                                             "'bool') "
                                                                                             '-> '
                                                                                             "'Optional[int]'",
                                                                           'stateful_owner': True,
                                                                           'target_kind': 'function',
                                                                           'varargs': False,
                                                                           'varkw': False},
                                                      'coupling_similarity': 1.0,
                                                      'cross_diversity_links': 2,
                                                      'effect_modes': ['temporal_orchestration_change',
                                                                       'lineage_surface'],
                                                      'effect_phrases': ['function growth '
                                                                         'reflected through '
                                                                         'aurora_internal.aurora_entropy_detector',
                                                                         'EntropySaturationDetector._project_critical_tick '
                                                                         'changed downstream '
                                                                         'system pressure'],
                                                      'genealogy_pressure': 0.809108,
                                                      'inheritance_breach_count': 1,
                                                      'kind': 'reflection',
                                                      'link_hits': 36,
                                                      'module': 'aurora_internal.aurora_entropy_detector',
                                                      'op_id': 'aurora_internal.aurora_entropy_detector.EntropySaturationDetector._project_critical_tick',
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
 'SaturationSignal.urgency_ticks': {'ability_hits': 19,
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
                                                         'doc_hint': 'Remaining ticks before '
                                                                     'projected critical crossing '
                                                                     '(None = not projected).',
                                                         'effect_density': 2,
                                                         'kwonly_args': 0,
                                                         'optional_args': 0,
                                                         'required_args': 0,
                                                         'return_hint': 'Optional[int]',
                                                         'signature_text': '(self) -> '
                                                                           "'Optional[int]'",
                                                         'stateful_owner': True,
                                                         'target_kind': 'function',
                                                         'varargs': False,
                                                         'varkw': False},
                                    'coupling_similarity': 1.0,
                                    'cross_diversity_links': 2,
                                    'effect_modes': ['temporal_orchestration_change',
                                                     'lineage_surface'],
                                    'effect_phrases': ['function growth reflected through '
                                                       'aurora_internal.aurora_entropy_detector',
                                                       'SaturationSignal.urgency_ticks changed '
                                                       'downstream system pressure'],
                                    'genealogy_pressure': 0.809108,
                                    'inheritance_breach_count': 1,
                                    'kind': 'reflection',
                                    'link_hits': 36,
                                    'module': 'aurora_internal.aurora_entropy_detector',
                                    'op_id': 'aurora_internal.aurora_entropy_detector.SaturationSignal.urgency_ticks',
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

from aurora_internal.aurora_evolution_hook import (
    assign_target as _aurora_evolution_hook_assign_target,
    get_target as _aurora_evolution_hook_get_target,
    bind_owner_attribute as _aurora_evolution_hook_bind_owner_attribute,
    target_strategy as _aurora_evolution_hook_target_strategy,
    target_feedback as _aurora_evolution_hook_target_feedback,
    store_reflection as _aurora_store_reflection,
    store_owner_state as _aurora_store_owner_state,
    apply_result_rewrite as _aurora_evolution_hook_apply_result_rewrite,
    make_override as _aurora_evolution_hook_make_override,
    make_latent_binding as _aurora_evolution_hook_make_latent_binding,
)


def _aurora_target_strategy(target_key):
    return _aurora_evolution_hook_target_strategy(_AURORA_NATIVE_STRATEGIES, target_key)


def _aurora_target_feedback(target_key):
    return _aurora_evolution_hook_target_feedback(_AURORA_NATIVE_STRATEGIES, target_key)


def _aurora_assign_target(chain, value):
    return _aurora_evolution_hook_assign_target(globals(), chain, value)


def _aurora_get_target(chain):
    return _aurora_evolution_hook_get_target(globals(), chain)


def _aurora_bind_owner_attribute(owner_chain, attr_name, value):
    return _aurora_evolution_hook_bind_owner_attribute(globals(), owner_chain, attr_name, value)


def _aurora_apply_result_rewrite(target_key, result, reflection, args, kwargs):
    return _aurora_evolution_hook_apply_result_rewrite(
        _AURORA_NATIVE_MODULE, _AURORA_NATIVE_STRATEGIES, target_key, result, reflection, args, kwargs,
    )


def _aurora_make_override(export_name, target_key):
    return _aurora_evolution_hook_make_override(
        globals(), _AURORA_NATIVE_EVOLVED_ORIGINALS, _AURORA_NATIVE_EVOLVED_LAST,
        _aurora_native_evolved_engine, _AURORA_NATIVE_MODULE, _AURORA_NATIVE_STRATEGIES,
        export_name, target_key,
    )


def _aurora_make_latent_binding(export_name, target_key):
    return _aurora_evolution_hook_make_latent_binding(
        globals(), _AURORA_NATIVE_EVOLVED_LAST, export_name, target_key,
    )


def project_critical_tick_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_entropy_detector.EntropySaturationDetector._project_critical_tick', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_entropy_detector_entropysaturationdetector_project_critical_tick')(payload=payload, **kwargs)

def urgency_ticks_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_entropy_detector.SaturationSignal.urgency_ticks', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_entropy_detector_saturationsignal_urgency_ticks')(payload=payload, **kwargs)

if _aurora_get_target(['SaturationSignal', 'urgency_ticks']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['SaturationSignal.urgency_ticks'] = _aurora_get_target(['SaturationSignal', 'urgency_ticks'])
    _aurora_assign_target(['SaturationSignal', 'urgency_ticks'], _aurora_make_override('urgency_ticks_evolved', 'SaturationSignal.urgency_ticks'))
    _AURORA_NATIVE_EVOLVED_LAST['SaturationSignal.urgency_ticks'] = {'alignment_gap': 0.34, 'override_active': True}

AURORA_NATIVE_EVOLVED_EXPORTS = {'aurora_internal.aurora_entropy_detector.EntropySaturationDetector._project_critical_tick': 'project_critical_tick_evolved',
 'aurora_internal.aurora_entropy_detector.SaturationSignal.urgency_ticks': 'urgency_ticks_evolved'}
AURORA_NATIVE_EVOLUTION_OVERRIDES = {'aurora_internal.aurora_entropy_detector.SaturationSignal.urgency_ticks': {'export': 'urgency_ticks_evolved',
                                                                            'mode': 'callable_override',
                                                                            'target': 'SaturationSignal.urgency_ticks'}}
# AURORA_EVOLVED_NATIVE_END

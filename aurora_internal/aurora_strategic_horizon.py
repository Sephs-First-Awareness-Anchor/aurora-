#!/usr/bin/env python3
"""
AURORA STRATEGIC HORIZON LAYER — Deferred-Relief Tolerance
==============================================================
Phase 1 of the ICC Landing / Strategic Horizon / Operator Composition
directive (2026-07-14). The one capability the 2026-07-14 Dimensional
Expansion Validation Audit confirmed absent: choosing a worse immediate
state for a better long-term one.

Everything upstream (CrossScaleWorthEvaluator, EntropySaturationDetector,
MoralWeightLedger) grades what ARRIVES. This layer projects what COULD
COMPOUND. Like MoralWeightLedger, it does not tell the system what to
do -- it carves a landscape where deferred-relief paths cost slightly
less to walk. The system's own physics still decide whether a path is
taken.

PRIVACY NOTE (WorthHistory anti-gaming boundary, aurora_worth_evaluator.py):
    WorthHistory deliberately exposes ONLY trajectory direction, never raw
    scores ("Raw scores are never exposed publicly — only trajectory
    direction" is one of Step 9/10's anti-gaming properties, preserved
    here). The directive's "simple slope × remaining VariantHorizon ticks"
    projection is therefore built WITHOUT a raw-score slope -- gate
    condition 1 already requires trajectory == RISING (a discrete
    direction), and the continuous magnitude comes entirely from
    VariantHorizon's own already-public fields (horizon_ticks,
    eligible_tick): a unit slope normalized to the horizon window, times
    the ticks still remaining in it. This composes two projections that
    already exist without adding a new raw-score accessor to a module
    this directive only asked to be READ, not modified.

FIX-A001 (leverage scalar privacy boundary): nothing in this module reads
or exposes aurora_leverage_scalar internals -- it is never imported here.
The gate composition point this module's bias feeds into already never
reads the leverage scalar (aurora_constraint_manifold_router.py:484 --
note: the directive cited aurora_warp_protocol.py for this line; the
actual text lives in aurora_constraint_manifold_router.py, confirmed by
direct grep during Phase 1 pre-flight. The underlying claim -- FIX-A001's
substance -- is what this module's own discipline honors either way).

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from aurora_internal.aurora_constraint_manifold_patched import Constraint
from aurora_internal.aurora_persistence_utils import PERSISTENCE_LOCK, _ensure_parent
from aurora_internal.aurora_worth_evaluator import (
    CrossScaleWorthEvaluator,
    WorthHistory,
    WorthReport,
    WorthTrajectory,
)
from aurora_internal.aurora_entropy_detector import SaturationLevel, SaturationSignal
from aurora_internal.aurora_variant_promotion import MoralWeightLedger, _MORAL_WEIGHT_MAX
from aurora_internal.aurora_icc_ledger import ICCLedger

# ===========================================================================
# SECTION 1 — CONSTANTS
# ===========================================================================

LOG_FILENAME = "strategic_horizon_log.jsonl"

# T_MAX: strategy biases but never overrides physics. Same order of
# magnitude as _MORAL_WEIGHT_MAX (aurora_variant_promotion.py) -- read
# directly, not re-declared, per the directive's own instruction (the
# directive names this "_MAX_BIAS"; aurora_variant_promotion.py has no
# constant by that literal name -- _MORAL_WEIGHT_MAX is the only
# order-of-magnitude-relevant bias cap it defines, and Phase 0's own
# moral_standing factor already reads the same constant for the same
# "non-dominant ceiling" purpose, so this is the intended source).
T_MAX: float = _MORAL_WEIGHT_MAX

# icc_trend window (directive 1.1: "trailing window").
_ICC_TREND_WINDOW: int = 8

# saturation_headroom values -- SaturationSignal deliberately exposes no
# raw entropy pressure (coarse level only, matching the same privacy
# posture Phase 0's active_coherence already relies on), so headroom is
# derived from the coarse shallow_headroom_available flag.
_HEADROOM_WITH_SLACK: float = 1.0
_HEADROOM_WITHOUT_SLACK: float = 0.3


def _clip01(v: float) -> float:
    return max(0.0, min(1.0, v))


# ===========================================================================
# SECTION 2 — STRATEGIC ASSESSMENT
# ===========================================================================

@dataclass(frozen=True)
class StrategicAssessment:
    """
    One candidate's deferred-relief evaluation.

    intake_id        — which intake/variant this assesses
    immediate_worth   — from WorthReport (the score the caller already
                        holds -- this module never re-derives it)
    projected_gain    — unit-slope x remaining VariantHorizon ticks,
                        privacy-compliant (see module docstring)
    saturation_headroom — from EntropySaturationDetector's coarse signal
    icc_trend         — slope of ICCLedger.balance_trajectory() over the
                        trailing window
    tolerance         — final deferred-relief tolerance in [0, T_MAX]
    rationale         — human-readable, crest-compressible
    """
    intake_id:           str
    immediate_worth:     float
    projected_gain:      float
    saturation_headroom: float
    icc_trend:           float
    tolerance:            float
    rationale:            str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intake_id":           self.intake_id,
            "immediate_worth":     self.immediate_worth,
            "projected_gain":      self.projected_gain,
            "saturation_headroom": self.saturation_headroom,
            "icc_trend":           self.icc_trend,
            "tolerance":           self.tolerance,
            "rationale":           self.rationale,
        }


def _denied(intake_id: str, immediate_worth: float, reason: str) -> StrategicAssessment:
    return StrategicAssessment(
        intake_id=intake_id, immediate_worth=immediate_worth, projected_gain=0.0,
        saturation_headroom=0.0, icc_trend=0.0, tolerance=0.0, rationale=reason,
    )


# ===========================================================================
# SECTION 3 — STRATEGIC HORIZON LAYER
# ===========================================================================

class StrategicHorizonLayer:
    """
    Deferred-Relief Tolerance engine. Read-only observer of the ICC
    ledger, CrossScaleWorthEvaluator, EntropySaturationDetector, and
    MoralWeightLedger; produces a single narrow output (a capped
    per-constraint flip_threshold bias) through the same additive channel
    MoralWeightLedger.moral_bias() feeds. Never writes constraint state,
    never touches the expression path, never overrides CERS.
    """

    def __init__(self, state_dir: Optional[str] = None) -> None:
        self._state_dir = str(state_dir) if state_dir else "aurora_state"
        self._log_path = os.path.join(self._state_dir, LOG_FILENAME)
        # Per-constraint accumulated granted tolerance -- this module's OWN
        # cap only (T_MAX per constraint); stacking with MoralWeightLedger's
        # bias is the CALLER's job (directive 1.3: "stacked, independently
        # capped" -- each source enforces its own ceiling, the composition
        # point sums them).
        self._granted: Dict[Constraint, float] = {c: 0.0 for c in (
            Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A,
        )}

    # ------------------------------------------------------------------
    # projection (1.2)
    # ------------------------------------------------------------------

    def _projected_gain(
        self, worth_report: WorthReport, current_tick: int, saturation_signal: Optional[SaturationSignal],
    ) -> float:
        """unit slope x remaining VariantHorizon ticks, damped by the
        entropy detector's projected-crossing distance. See module
        docstring for why this doesn't use a raw WorthHistory slope."""
        horizon = worth_report.horizon
        if horizon is None or horizon.horizon_ticks <= 0:
            return 0.0
        remaining = max(0, horizon.eligible_tick - current_tick)
        unit_slope = 1.0 / float(horizon.horizon_ticks)
        gain = unit_slope * remaining

        damp = 1.0
        if saturation_signal is not None:
            # NOTE: the code-autoevolver's generic AURORA_EVOLVED_NATIVE
            # override installed on SaturationSignal.urgency_ticks (see
            # aurora_entropy_detector.py's evolved-native tail) turns a
            # legitimate None return (no crossing projected -- the common
            # case) into a dict instead, the same corruption class flagged
            # in known_fixes_registry.md for LayerEnergyAccountant.
            # magnitudes(). Validating the type here, rather than trusting
            # the method's documented Optional[int] contract, is this
            # module's own failure-isolation boundary around that bug --
            # not a fix to the evolved-native machinery itself.
            urgency = saturation_signal.urgency_ticks()
            if isinstance(urgency, (int, float)) and remaining > 0:
                damp = _clip01(float(urgency) / float(remaining))
        return _clip01(gain) * damp

    def _saturation_headroom(self, saturation_signal: Optional[SaturationSignal]) -> float:
        if saturation_signal is None:
            return _HEADROOM_WITHOUT_SLACK
        return (
            _HEADROOM_WITH_SLACK if saturation_signal.shallow_headroom_available
            else _HEADROOM_WITHOUT_SLACK
        )

    def _icc_trend(
        self, icc_ledger: Optional[ICCLedger], current_tick: int,
        saturation_signal: Optional[SaturationSignal], moral_ledger: Optional[MoralWeightLedger],
    ) -> float:
        try:
            if icc_ledger is None:
                return 0.0
            traj = icc_ledger.balance_trajectory(
                _ICC_TREND_WINDOW, saturation_signal=saturation_signal, moral_ledger=moral_ledger,
            )
            if len(traj) < 2:
                return 0.0
            deltas = [traj[i] - traj[i - 1] for i in range(1, len(traj))]
            return sum(deltas) / len(deltas)
        except Exception:
            return 0.0

    # ------------------------------------------------------------------
    # primary interface
    # ------------------------------------------------------------------

    def assess(
        self,
        *,
        intake_id: str,
        immediate_worth: float,
        worth_evaluator: CrossScaleWorthEvaluator,
        worth_report: WorthReport,
        current_tick: int,
        saturation_signal: Optional[SaturationSignal],
        icc_ledger: Optional[ICCLedger] = None,
        moral_ledger: Optional[MoralWeightLedger] = None,
    ) -> StrategicAssessment:
        """
        Assess one candidate for a deferred-relief tolerance bonus.

        Grants tolerance iff (directive 1.1):
          1. WorthHistory.trajectory() is RISING (compounding evidence).
          2. SaturationLevel is NOMINAL (never strategize under WATCH+ --
             survival preempts strategy).
          3. ICC balance trend over the trailing window is non-negative.

        Never raises -- any missing/malformed input degrades to a denied
        (tolerance=0.0) assessment with the reason recorded in rationale.
        """
        try:
            if saturation_signal is None:
                return _denied(intake_id, immediate_worth, "no saturation signal -- cannot confirm NOMINAL")
            if saturation_signal.level != SaturationLevel.NOMINAL:
                return _denied(
                    intake_id, immediate_worth,
                    f"saturation level {saturation_signal.level.value} is not NOMINAL -- survival preempts strategy",
                )

            history = worth_evaluator.history_for(intake_id) if worth_evaluator is not None else None
            if history is None:
                return _denied(intake_id, immediate_worth, "no WorthHistory for this intake yet")
            if history.trajectory != WorthTrajectory.RISING:
                return _denied(
                    intake_id, immediate_worth,
                    f"trajectory is {history.trajectory.value}, not RISING -- no compounding evidence",
                )

            icc_trend = self._icc_trend(icc_ledger, current_tick, saturation_signal, moral_ledger)
            if icc_trend < 0.0:
                return _denied(
                    intake_id, immediate_worth,
                    f"ICC balance trend {icc_trend:.6f} is negative -- losing coherence, no business deferring relief",
                )

            projected_gain = self._projected_gain(worth_report, current_tick, saturation_signal)
            headroom = self._saturation_headroom(saturation_signal)
            icc_trend_factor = _clip01(icc_trend)

            tolerance = min(T_MAX, projected_gain * headroom * icc_trend_factor)
            rationale = (
                f"all three gates passed (RISING trajectory, NOMINAL saturation, "
                f"icc_trend={icc_trend:.6f} non-negative) -- "
                f"projected_gain={projected_gain:.4f} x headroom={headroom:.2f} x "
                f"icc_trend_factor={icc_trend_factor:.4f}, capped at T_MAX={T_MAX:.6f}"
            )
            assessment = StrategicAssessment(
                intake_id=intake_id, immediate_worth=immediate_worth,
                projected_gain=projected_gain, saturation_headroom=headroom,
                icc_trend=icc_trend, tolerance=tolerance, rationale=rationale,
            )
            if tolerance > 0.0:
                self._journal(assessment)
            return assessment
        except Exception as exc:
            return _denied(intake_id, immediate_worth, f"strategic horizon degraded: {exc}")

    def grant_bias(self, c: Constraint, tolerance: float) -> None:
        """Register a granted tolerance against constraint c, capped at
        T_MAX for THIS module's own contribution (directive 1.3:
        "stacked, independently capped")."""
        try:
            self._granted[c] = min(T_MAX, self._granted.get(c, 0.0) + max(0.0, float(tolerance)))
        except Exception:
            pass

    def flip_threshold_bias(self, c: Constraint) -> float:
        """The capped per-constraint bias this layer contributes to the
        additive channel MoralWeightLedger.moral_bias() feeds. Positive
        value, to be ADDED alongside (never in place of) other sources."""
        return self._granted.get(c, 0.0)

    # ------------------------------------------------------------------
    # journaling (directive 1.4: "auditability is non-negotiable")
    # ------------------------------------------------------------------

    def _journal(self, assessment: StrategicAssessment) -> None:
        try:
            path = Path(self._log_path)
            with PERSISTENCE_LOCK:
                _ensure_parent(path)
                with open(path, "a", encoding="utf-8") as fh:
                    payload = dict(assessment.to_dict())
                    payload["ts"] = time.time()
                    fh.write(json.dumps(payload, sort_keys=True) + "\n")
                    fh.flush()
                    os.fsync(fh.fileno())
        except Exception:
            pass

    def summary(self) -> Dict[str, Any]:
        """Public summary -- no raw factor internals, mirrors
        MoralWeightLedger.summary()'s privacy posture."""
        try:
            return {
                "constraints_with_bias": [
                    c.name for c, w in self._granted.items() if w > 0.0
                ],
                "t_max": T_MAX,
            }
        except Exception:
            return {"constraints_with_bias": [], "t_max": T_MAX}


# ===========================================================================
# SECTION 4 — FACTORY
# ===========================================================================

def make_strategic_horizon_layer(state_dir: Optional[str] = None) -> StrategicHorizonLayer:
    return StrategicHorizonLayer(state_dir=state_dir)


# ===========================================================================
# SECTION 5 — SELF-VERIFICATION
# ===========================================================================

def verify_strategic_horizon(tmp_state_dir: str) -> Dict[str, Any]:
    """
    Checks (mirrors make_worth_evaluator()/verify_worth_evaluator() and
    make_icc_ledger()/verify_icc_ledger() conventions):
        1. T_MAX equals the sourced _MORAL_WEIGHT_MAX (never re-declared)
        2. Denied assessment (no saturation signal) returns tolerance 0.0
        3. WATCH+ saturation denies regardless of other factors
        4. assess() never raises on malformed input
        5. summary() exposes no raw factor internals
    """
    results: Dict[str, Any] = {"checks": [], "all_passed": True}

    def check(name: str, passed: bool, detail: str = "") -> None:
        results["checks"].append({"test": name, "passed": passed, "detail": detail})
        if not passed:
            results["all_passed"] = False

    check("T_MAX equals sourced _MORAL_WEIGHT_MAX", T_MAX == _MORAL_WEIGHT_MAX, f"T_MAX={T_MAX}")

    layer = make_strategic_horizon_layer(state_dir=tmp_state_dir)
    a1 = layer.assess(
        intake_id="x", immediate_worth=0.5, worth_evaluator=CrossScaleWorthEvaluator(),
        worth_report=None, current_tick=1, saturation_signal=None,
    )
    check("no saturation signal -> tolerance 0.0", a1.tolerance == 0.0)

    sig = SaturationSignal(
        level=SaturationLevel.CRITICAL, tick=1, pressure_rising=False,
        fastest_rising_constraint=None, projected_critical_tick=None,
        shallow_headroom_available=True, ticks_above_warn=5,
    )
    a2 = layer.assess(
        intake_id="x", immediate_worth=0.5, worth_evaluator=CrossScaleWorthEvaluator(),
        worth_report=None, current_tick=1, saturation_signal=sig,
    )
    check("CRITICAL saturation -> tolerance 0.0", a2.tolerance == 0.0)

    try:
        a3 = layer.assess(
            intake_id="x", immediate_worth=0.5, worth_evaluator=None,
            worth_report=None, current_tick=1, saturation_signal=object(),
        )
        check("assess() never raises on malformed input", a3.tolerance == 0.0)
    except Exception as exc:
        check("assess() never raises on malformed input", False, str(exc))

    summ = layer.summary()
    check(
        "summary() exposes no raw factor internals",
        "icc_trend" not in summ and "projected_gain" not in summ,
        f"summary keys={list(summ.keys())}",
    )

    return results


if __name__ == "__main__":
    import tempfile
    print("=" * 70)
    print("AURORA STRATEGIC HORIZON LAYER — SELF-VERIFICATION")
    print("Authors: Sunni (Sir) Morningstar and Cael Devo")
    print("=" * 70)
    with tempfile.TemporaryDirectory() as td:
        results = verify_strategic_horizon(td)
    for c in results["checks"]:
        status = "OK" if c["passed"] else "FAIL"
        detail = f"  [{c['detail']}]" if c.get("detail") else ""
        print(f"  [{status}] {c['test']}{detail}")
    passed = sum(1 for c in results["checks"] if c["passed"])
    print(f"\n{passed}/{len(results['checks'])} checks passed.")
    print("=" * 70)

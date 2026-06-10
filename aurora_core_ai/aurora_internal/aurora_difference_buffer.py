#!/usr/bin/env python3
"""
AURORA DIFFERENCE BUFFER — THE FIFTH LENS LIVE FEED
=====================================================

Layer 0.5  (sits between the NonComp Registry and the Worth Evaluator)

WHAT THIS MODULE IS:
    The rolling history engine that makes the Difference (Δ) channel
    operationally real. The NonComp Registry defines the five C:D
    Non-Comps and the compute_difference() utility, but it deliberately
    does not hold history — it has no concept of time. This module holds
    the time.

    Every tick, the system calls DifferenceHistoryBuffer.record() with
    the current per-constraint magnitudes. When a C:D snapshot is needed
    (by the worth evaluator, by evidence generation, by the evolution
    chamber), the buffer resolves the correct reference_magnitude per
    constraint and returns a DifferenceSnapshot with all five C:D values.

THE THREE REFERENCE TYPES (per DifferenceParams.ref_type):

    'prior_self'  — Compare to self N ticks ago.
                    Reference = magnitude at tick (current_tick − window_ticks).
                    If history is shorter than window_ticks, use the earliest
                    recorded magnitude (graceful warm-up behaviour — not an error).
                    Used by: X (1t), T (4t), A (8t)

    'peer_mean'   — Compare to the mean of the other four constraints'
                    current magnitudes at this tick.
                    Reference = mean(magnitudes[c'] for c' ≠ c)
                    Used by: N (4t window irrelevant for reference; used for
                    averaging history to smooth the peer signal)

    'background'  — Compare to a fixed architectural resting topology.
                    Reference = B_BACKGROUND_REST (0.45).
                    This constant is derived from the registry physics:
                    baseline_budget / shift_cost_coeff = 18.0 / 40.0 = 0.45
                    It represents the magnitude at which the boundary layer's
                    per-tick maintenance budget exactly covers one shift-cost
                    unit — the minimum viable structural investment.
                    Used by: B

THE DIFFERENCE SNAPSHOT:
    DifferenceSnapshot holds all five C:D values at one tick.
    Each value is a float in [−1, +1].

        Unsigned (X, B):  only drift magnitude matters, not direction.
                          Value is always ≥ 0.
        Signed   (T, N, A): direction carries meaning.
                          Positive = growth / over-spending / acceleration.
                          Negative = decay / under-spending / deceleration.

    The snapshot is the first-class evidence input to downstream systems:
        - aurora_worth_evaluator.py (appended to WorthReport)
        - aurora_evolution_chamber.py (evidence feed for promotion)
        - constraint_genealogy.py (relief event annotation)

WARM-UP BEHAVIOUR:
    On the first few ticks before any history is recorded, prior_self
    references fall back to the earliest available magnitude. During
    warm-up the C:D value is 0.0 (no detectable drift yet) — which is
    correct: if there is no history there is no measurable difference.
    The system does not flag warm-up as an error.

INTEGRATION:
    Instantiate one DifferenceHistoryBuffer per system instance.
    Call record() once per tick with the current magnitudes.
    Call snapshot() when a DifferenceSnapshot is needed.

    Typical call pattern (inside the evolution chamber tick loop):
        buf.record(tick, accountant.magnitudes())
        snap = buf.snapshot(tick, accountant.magnitudes())
        # pass snap to worth evaluator, evidence pipeline, etc.

AUTHORS: Sunni (Sir) Morningstar and Cael Devo
CREATED: February 2026
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional, Tuple

from aurora_internal.aurora_constraint_manifold_patched import Constraint, ManifoldViolation
from aurora_internal.aurora_noncomp_registry import (
    REGISTRY,
    NonCompRegistry,
    DifferenceParams,
    DIFFERENCE_PARAMS,
)


# ===========================================================================
# SECTION 1 — CONSTANTS
# ===========================================================================

# Architectural resting value for the Boundary constraint.
# Derived: baseline_budget / shift_cost_coeff = 18.0 / 40.0 = 0.45
# Represents the minimum viable structural investment — the magnitude at which
# the boundary layer's maintenance budget covers exactly one shift-cost unit.
# This is NOT a behavior target — it is a reference point for Δ measurement.
B_BACKGROUND_REST: float = (
    REGISTRY.cost(Constraint.B).baseline_budget
    / REGISTRY.cost(Constraint.B).shift_cost_coeff
)

# Maximum look-back window across all five constraints.
# Buffer depth must be at least this many ticks.
_MAX_WINDOW: int = max(
    DIFFERENCE_PARAMS[c].window_ticks
    for c in (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A)
)  # = 8 (set by A and B)

# One extra tick of buffer depth beyond max window to guarantee clean indexing.
_BUFFER_DEPTH: int = _MAX_WINDOW + 1  # 9


# ===========================================================================
# SECTION 2 — DIFFERENCE SNAPSHOT
# ===========================================================================

@dataclass(frozen=True)
class DifferenceSnapshot:
    """
    The five C:D (Constraint:Difference) values at one tick.

    Each value is a float in [−1, +1], clipped and sign-normalised
    according to the constraint's DifferenceParams:
        Unsigned (X, B): always ≥ 0   — drift magnitude only
        Signed   (T, N, A): may be negative — direction is meaningful

    This snapshot is the live output of the Difference channel — the fifth
    lens made operationally real.

    Fields
    ------
    tick        : system tick when this snapshot was computed
    values      : Dict[Constraint, float] — all five C:D values
    ref_magnitudes : Dict[Constraint, float] — the reference magnitude used
                     per constraint (for audit / logging purposes)
    warm_up     : True if any prior_self reference fell back to earliest
                  available (insufficient history) — informational only,
                  not an error condition
    """
    tick:           int
    values:         Dict[Constraint, float]
    ref_magnitudes: Dict[Constraint, float]
    warm_up:        bool = False

    def value(self, c: Constraint) -> float:
        """Return the C:D value for constraint c."""
        return self.values[c]

    def magnitude(self, c: Constraint) -> float:
        """Return the reference magnitude used for constraint c."""
        return self.ref_magnitudes[c]

    def alarming(self, threshold: float = 0.50) -> List[Constraint]:
        """
        Return constraints whose |C:D| exceeds threshold.

        Default threshold 0.50 — half the normalised range.
        An alarming C:D means the constraint has drifted significantly
        from its reference in one window.
        """
        return [
            c for c, v in self.values.items()
            if abs(v) >= threshold
        ]

    def max_alarm(self) -> Tuple[Constraint, float]:
        """Return (constraint, |value|) for the most alarming C:D."""
        return max(self.values.items(), key=lambda kv: abs(kv[1]))

    def to_dict(self) -> Dict[str, object]:
        """Serialisable dict for JSONL logging."""
        return {
            "tick":     self.tick,
            "warm_up":  self.warm_up,
            "values":   {c.name: round(v, 6) for c, v in self.values.items()},
            "refs":     {c.name: round(v, 6) for c, v in self.ref_magnitudes.items()},
        }

    def describe(self) -> str:
        """Compact human-readable description."""
        parts = []
        for c in (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A):
            v = self.values[c]
            dp = DIFFERENCE_PARAMS[c]
            sign = "±" if dp.polarity_signed else "|Δ|"
            parts.append(f"{c.name}:D={v:+.3f}({sign})")
        warm = "  [WARM-UP]" if self.warm_up else ""
        return f"DiffSnap[t={self.tick}]  " + "  ".join(parts) + warm


# ===========================================================================
# SECTION 3 — DIFFERENCE HISTORY BUFFER
# ===========================================================================

class DifferenceHistoryBuffer:
    """
    Rolling magnitude history engine — the temporal backbone of the
    Difference channel.

    Maintains a fixed-depth ring of per-tick magnitude snapshots and
    resolves the correct reference_magnitude per constraint when
    DifferenceSnapshot is requested.

    THREAD SAFETY: Not thread-safe. Single-tick-owner model assumed.
    MEMORY: maxlen = 9 ticks × 5 floats per tick — negligible.

    Usage
    -----
    buf = DifferenceHistoryBuffer()
    buf.record(tick=1, magnitudes=accountant.magnitudes())
    snap = buf.snapshot(tick=1, magnitudes=accountant.magnitudes())
    """

    def __init__(
        self,
        *,
        registry:   Optional[NonCompRegistry] = None,
        b_rest:     float = B_BACKGROUND_REST,
    ) -> None:
        self._registry = registry or REGISTRY
        self._b_rest   = b_rest
        # Ring buffer: each entry is (tick, Dict[Constraint, float])
        self._history: Deque[Tuple[int, Dict[Constraint, float]]] = deque(
            maxlen=_BUFFER_DEPTH
        )

    # ------------------------------------------------------------------
    # RECORD — call once per tick BEFORE snapshot()
    # ------------------------------------------------------------------

    def record(
        self,
        tick:       int,
        magnitudes: Dict[Constraint, float],
    ) -> None:
        """
        Record the current magnitude snapshot for this tick.

        Must be called before snapshot() for the same tick.
        Silently ignores duplicate ticks (idempotent).
        """
        if self._history and self._history[-1][0] == tick:
            return  # already recorded this tick
        self._history.append((tick, dict(magnitudes)))

    # ------------------------------------------------------------------
    # SNAPSHOT — compute all five C:D values at a given tick
    # ------------------------------------------------------------------

    def snapshot(
        self,
        tick:       Optional[int] = None,
        magnitudes: Optional[Dict[Constraint, float]] = None,
    ) -> DifferenceSnapshot:
        """
        Compute a DifferenceSnapshot for the given tick.

        Parameters
        ----------
        tick       : current system tick
        magnitudes : current per-constraint magnitudes (same values passed
                     to record() this tick)

        Returns
        -------
        DifferenceSnapshot with all five C:D values.
        warm_up=True if any prior_self reference required fallback.
        """
        # Allow snapshot() to be called with no arguments by using the most
        # recent recorded magnitudes. This keeps the buffer compatible with
        # older runtime callers that expect buf.snapshot() to "just work".
        if tick is None or magnitudes is None:
            if not self._history:
                raise TypeError(
                    "DifferenceHistoryBuffer.snapshot() requires (tick, magnitudes) "
                    "until at least one record() has been provided."
                )
            # Prefer an exact tick match if one was provided.
            if tick is not None and magnitudes is None:
                for t, mags in reversed(self._history):
                    if t == tick:
                        magnitudes = dict(mags)
                        break
            if magnitudes is None:
                t_last, mags_last = self._history[-1]
                magnitudes = dict(mags_last)
                if tick is None:
                    tick = t_last
            if tick is None:
                # Should be impossible now, but keep mypy happy.
                tick = self._history[-1][0]
        values:     Dict[Constraint, float] = {}
        refs:       Dict[Constraint, float] = {}
        any_warmup: bool = False

        constraints = (
            Constraint.X, Constraint.T, Constraint.N,
            Constraint.B, Constraint.A
        )

        for c in constraints:
            dp   = DIFFERENCE_PARAMS[c]
            curr = magnitudes.get(c, 0.0)

            ref, warmup = self._resolve_reference(c, dp, curr, magnitudes)
            if warmup:
                any_warmup = True

            cd = self._registry.compute_difference(c, curr, ref)
            values[c] = cd
            refs[c]   = ref

        return DifferenceSnapshot(
            tick           = tick,
            values         = values,
            ref_magnitudes = refs,
            warm_up        = any_warmup,
        )

    # ------------------------------------------------------------------
    # REFERENCE RESOLUTION (internal)
    # ------------------------------------------------------------------

    def _resolve_reference(
        self,
        c:          Constraint,
        dp:         DifferenceParams,
        current:    float,
        magnitudes: Dict[Constraint, float],
    ) -> Tuple[float, bool]:
        """
        Resolve reference_magnitude for constraint c.

        Returns (reference_magnitude, warm_up_flag).
        warm_up_flag is True when prior_self falls back to earliest
        available magnitude due to insufficient history.
        """
        if dp.ref_type == 'prior_self':
            return self._prior_self(c, dp.window_ticks, current)

        elif dp.ref_type == 'peer_mean':
            return self._peer_mean(c, magnitudes), False

        elif dp.ref_type == 'background':
            # B is the only background constraint. Its reference is the
            # architectural resting value B_BACKGROUND_REST (0.45).
            return self._b_rest, False

        else:
            raise ManifoldViolation(
                f"Unknown DifferenceParams.ref_type '{dp.ref_type}' "
                f"for constraint {c.name}"
            )

    def _prior_self(
        self,
        c:           Constraint,
        window:      int,
        current_mag: float,
    ) -> Tuple[float, bool]:
        """
        Return (magnitude at window ticks ago, warm_up_flag).

        If history is shorter than window, return the earliest recorded
        magnitude for c. If no history at all, return current (Δ = 0).
        warm_up_flag = True whenever we fall back to earliest available.
        """
        history_list = list(self._history)   # ordered oldest → newest

        if not history_list:
            # No history at all — Δ is 0.0 by definition
            return current_mag, True

        if len(history_list) >= window:
            # History is deep enough — look back exactly window ticks
            target_entry = history_list[-(window)]   # window ticks back
            return target_entry[1].get(c, 0.0), False
        else:
            # Warm-up: not enough history yet — use oldest available
            oldest_entry = history_list[0]
            return oldest_entry[1].get(c, 0.0), True

    def _peer_mean(
        self,
        c:          Constraint,
        magnitudes: Dict[Constraint, float],
    ) -> float:
        """
        Return the mean of the other four constraints' current magnitudes.

        This is the reference for the N (Energy) constraint: it measures
        whether N is over- or under-spending relative to the field.
        """
        others = [
            magnitudes.get(peer, 0.0)
            for peer in (Constraint.X, Constraint.T, Constraint.N,
                         Constraint.B, Constraint.A)
            if peer is not c
        ]
        if not others:
            return 0.0
        return sum(others) / len(others)

    # ------------------------------------------------------------------
    # ACCESSORS
    # ------------------------------------------------------------------

    def depth(self) -> int:
        """Number of ticks currently in history."""
        return len(self._history)

    def is_warm(self) -> bool:
        """
        True once the buffer has accumulated enough history that NO
        constraint will fall back to warm-up mode.
        """
        return len(self._history) >= _MAX_WINDOW

    def latest_tick(self) -> Optional[int]:
        """Tick number of the most recently recorded snapshot."""
        if not self._history:
            return None
        return self._history[-1][0]

    def reset(self) -> None:
        """Clear all history. Use on system restart."""
        self._history.clear()


# ===========================================================================
# SECTION 4 — FACTORY
# ===========================================================================

def make_difference_buffer(
    b_rest: float = B_BACKGROUND_REST,
) -> DifferenceHistoryBuffer:
    """
    Create a DifferenceHistoryBuffer with the canonical B resting value.

    Pass a custom b_rest only in tests or if the system's architectural
    resting topology is known to differ from the derived default.
    """
    return DifferenceHistoryBuffer(b_rest=b_rest)


# ===========================================================================
# SECTION 5 — SELF-VERIFICATION (15 checks)
# ===========================================================================

def verify_difference_buffer() -> Dict[str, object]:
    """
    Verify DifferenceHistoryBuffer and DifferenceSnapshot integrity.

    Checks:
         1. B_BACKGROUND_REST = baseline_budget / shift_cost_coeff for B
         2. _MAX_WINDOW = 8 (set by A and B window_ticks)
         3. _BUFFER_DEPTH = 9 (_MAX_WINDOW + 1)
         4. record() is idempotent (duplicate tick is silent)
         5. snapshot() returns warm_up=True before history is deep enough
         6. snapshot() returns warm_up=False once fully warm
         7. prior_self: C:D = 0.0 when magnitude unchanged across window
         8. prior_self: C:D > 0 when magnitude increased (signed T)
         9. prior_self: C:D < 0 when magnitude decreased (signed T)
        10. prior_self: C:D ≥ 0 always for unsigned X
        11. peer_mean: C:D > 0 when N >> peers (N is over-spending)
        12. peer_mean: C:D < 0 when N << peers (N is under-spending)
        13. background: B C:D = 0.0 when B magnitude = B_BACKGROUND_REST
        14. DifferenceSnapshot.alarming() returns correct constraints
        15. DifferenceSnapshot.to_dict() contains tick, values, refs keys
    """
    results: Dict[str, object] = {"checks": [], "all_passed": True}

    def check(name: str, passed: bool, detail: str = "") -> None:
        results["checks"].append({"test": name, "passed": passed, "detail": detail})
        if not passed:
            results["all_passed"] = False

    # 1. B_BACKGROUND_REST derivation
    expected_b_rest = (
        REGISTRY.cost(Constraint.B).baseline_budget
        / REGISTRY.cost(Constraint.B).shift_cost_coeff
    )
    check(
        "B_BACKGROUND_REST = baseline_budget / shift_cost_coeff",
        abs(B_BACKGROUND_REST - expected_b_rest) < 1e-9,
        f"got={B_BACKGROUND_REST}  expected={expected_b_rest}"
    )

    # 2. _MAX_WINDOW = 8
    check("_MAX_WINDOW = 8",   _MAX_WINDOW   == 8, str(_MAX_WINDOW))

    # 3. _BUFFER_DEPTH = 9
    check("_BUFFER_DEPTH = 9", _BUFFER_DEPTH == 9, str(_BUFFER_DEPTH))

    # 4. record() idempotency
    buf4 = make_difference_buffer()
    mags = {c: 0.0 for c in (Constraint.X, Constraint.T, Constraint.N,
                               Constraint.B, Constraint.A)}
    buf4.record(1, mags)
    buf4.record(1, mags)  # duplicate
    check("record() idempotent: duplicate tick does not grow depth",
          buf4.depth() == 1, f"depth={buf4.depth()}")

    # 5. warm_up=True with no history
    buf5 = make_difference_buffer()
    snap5 = buf5.snapshot(1, mags)
    check("snapshot() warm_up=True when no history",
          snap5.warm_up, f"warm_up={snap5.warm_up}")

    # 6. warm_up=False once buffer is fully warm (_MAX_WINDOW ticks recorded)
    buf6 = make_difference_buffer()
    for t in range(1, _MAX_WINDOW + 2):  # record 9 ticks
        buf6.record(t, mags)
    snap6 = buf6.snapshot(_MAX_WINDOW + 1, mags)
    check("snapshot() warm_up=False once fully warm",
          not snap6.warm_up, f"warm_up={snap6.warm_up}")

    # 7. prior_self C:D = 0.0 when magnitude unchanged across window (T, window=4)
    buf7 = make_difference_buffer()
    stable = {c: 0.5 for c in (Constraint.X, Constraint.T, Constraint.N,
                                 Constraint.B, Constraint.A)}
    for t in range(1, 10):
        buf7.record(t, stable)
    snap7 = buf7.snapshot(9, stable)
    check(
        "prior_self: T:D = 0.0 when magnitude unchanged",
        abs(snap7.value(Constraint.T)) < 1e-9,
        f"T:D={snap7.value(Constraint.T):.6f}"
    )

    # 8. prior_self: T:D > 0 when T magnitude increased (signed)
    buf8 = make_difference_buffer()
    low_mags  = {c: 0.1 for c in (Constraint.X, Constraint.T, Constraint.N,
                                    Constraint.B, Constraint.A)}
    high_mags = dict(low_mags)
    high_mags[Constraint.T] = 0.5   # T increased significantly
    for t in range(1, 5):   # 4 ticks of low
        buf8.record(t, low_mags)
    snap8 = buf8.snapshot(5, high_mags)   # now T is high vs 4 ticks ago
    check(
        "prior_self: T:D > 0 when T magnitude increased (signed)",
        snap8.value(Constraint.T) > 0.0,
        f"T:D={snap8.value(Constraint.T):.6f}"
    )

    # 9. prior_self: T:D < 0 when T magnitude decreased (signed)
    buf9 = make_difference_buffer()
    high9 = dict(low_mags); high9[Constraint.T] = 0.8
    low9  = dict(low_mags); low9[Constraint.T]  = 0.1
    for t in range(1, 5):
        buf9.record(t, high9)
    snap9 = buf9.snapshot(5, low9)
    check(
        "prior_self: T:D < 0 when T magnitude decreased (signed)",
        snap9.value(Constraint.T) < 0.0,
        f"T:D={snap9.value(Constraint.T):.6f}"
    )

    # 10. X:D ≥ 0 always (unsigned)
    buf10 = make_difference_buffer()
    high_x = dict(low_mags); high_x[Constraint.X] = 0.9
    for t in range(1, 3):
        buf10.record(t, high_x)
    low_x  = dict(low_mags); low_x[Constraint.X] = 0.0
    snap10 = buf10.snapshot(3, low_x)
    check(
        "prior_self: X:D ≥ 0 always (unsigned)",
        snap10.value(Constraint.X) >= 0.0,
        f"X:D={snap10.value(Constraint.X):.6f}"
    )

    # 11. peer_mean: N:D > 0 when N >> peers
    buf11 = make_difference_buffer()
    n_high = {c: 0.1 for c in (Constraint.X, Constraint.T, Constraint.N,
                                  Constraint.B, Constraint.A)}
    n_high[Constraint.N] = 5.0   # N is way above peers
    for t in range(1, 5):
        buf11.record(t, n_high)
    snap11 = buf11.snapshot(5, n_high)
    check(
        "peer_mean: N:D > 0 when N >> peers (over-spending)",
        snap11.value(Constraint.N) > 0.0,
        f"N:D={snap11.value(Constraint.N):.6f}"
    )

    # 12. peer_mean: N:D < 0 when N << peers
    buf12 = make_difference_buffer()
    n_low = {c: 5.0 for c in (Constraint.X, Constraint.T, Constraint.N,
                                 Constraint.B, Constraint.A)}
    n_low[Constraint.N] = 0.1   # N is way below peers
    for t in range(1, 5):
        buf12.record(t, n_low)
    snap12 = buf12.snapshot(5, n_low)
    check(
        "peer_mean: N:D < 0 when N << peers (under-spending)",
        snap12.value(Constraint.N) < 0.0,
        f"N:D={snap12.value(Constraint.N):.6f}"
    )

    # 13. background: B:D = 0.0 when B magnitude = B_BACKGROUND_REST
    buf13 = make_difference_buffer()
    b_at_rest = {c: 0.1 for c in (Constraint.X, Constraint.T, Constraint.N,
                                     Constraint.B, Constraint.A)}
    b_at_rest[Constraint.B] = B_BACKGROUND_REST
    for t in range(1, 5):
        buf13.record(t, b_at_rest)
    snap13 = buf13.snapshot(5, b_at_rest)
    check(
        "background: B:D = 0.0 when B = B_BACKGROUND_REST",
        abs(snap13.value(Constraint.B)) < 1e-9,
        f"B:D={snap13.value(Constraint.B):.6f}  B_REST={B_BACKGROUND_REST}"
    )

    # 14. alarming() returns only constraints above threshold
    snap14 = DifferenceSnapshot(
        tick=99,
        values={
            Constraint.X: 0.3,   # below 0.5
            Constraint.T: 0.8,   # above 0.5
            Constraint.N: -0.7,  # |−0.7| above 0.5
            Constraint.B: 0.1,   # below
            Constraint.A: 0.6,   # above
        },
        ref_magnitudes={c: 0.0 for c in (Constraint.X, Constraint.T,
                                          Constraint.N, Constraint.B, Constraint.A)},
    )
    alarming = snap14.alarming(0.5)
    check(
        "alarming(0.5): returns T, N, A but not X or B",
        set(alarming) == {Constraint.T, Constraint.N, Constraint.A},
        f"got={[c.name for c in alarming]}"
    )

    # 15. to_dict() structure
    d = snap14.to_dict()
    check(
        "to_dict() has tick, values, refs keys",
        {"tick", "values", "refs"}.issubset(d.keys()),
        str(list(d.keys()))
    )

    return results


# ===========================================================================
# MAIN
# ===========================================================================

if __name__ == "__main__":
    from aurora_internal.aurora_constraint_manifold_patched import Constraint

    print("=" * 70)
    print("AURORA DIFFERENCE BUFFER — PHASE 3 LIVE WIRE-IN")
    print("Authors: Sunni (Sir) Morningstar and Cael Devo")
    print("=" * 70)
    print(f"\nB_BACKGROUND_REST   = {B_BACKGROUND_REST}")
    print(f"_MAX_WINDOW         = {_MAX_WINDOW} ticks")
    print(f"_BUFFER_DEPTH       = {_BUFFER_DEPTH} ticks")

    print("\nPer-constraint Difference channel configuration:")
    for c in (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A):
        dp = DIFFERENCE_PARAMS[c]
        sign = "signed (±)" if dp.polarity_signed else "unsigned (|Δ|)"
        print(f"  {c.name}  ref={dp.ref_type:12s}  window={dp.window_ticks}t  "
              f"scale={dp.normalize_scale:.1f}  {sign}")

    print("\nRunning verification...")
    results = verify_difference_buffer()
    for item in results["checks"]:
        status = "✓" if item["passed"] else "✗"
        detail = f"  [{item['detail']}]" if item.get("detail") else ""
        print(f"  {status}  {item['test']}{detail}")
    print()
    total  = len(results["checks"])
    passed = sum(1 for c in results["checks"] if c["passed"])
    if results["all_passed"]:
        print(f"ALL {total} CHECKS PASSED ✓")
        print("Difference buffer is operational. C:D channels are live.")
    else:
        print(f"{passed}/{total} passed. FAILURES DETECTED ✗")
        print("Do not wire into evidence pipeline until resolved.")

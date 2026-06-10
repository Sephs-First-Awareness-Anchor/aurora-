"""
aurora_telemetry.py — Per-turn subsystem confidence telemetry.

Each major subsystem reports its confidence after contributing to a response.
DreamTrainer reads these mechanistic signals for precise fail attribution
instead of guessing from output text alone.

Usage:
    # In a subsystem:
    from aurora_telemetry import get_telemetry
    get_telemetry().report(
        source="DPME.process",
        module="aurora_consciousness_engine",
        confidence=0.3,
        dimension_hint="coherence_maintenance",
        detail="coherence=0.28 cat_processing=0.41",
    )

    # Before a response is generated (per-turn reset):
    get_telemetry().reset()

    # After generation, in fail classifier:
    weak = get_telemetry().mechanistic_fails(threshold=0.45)
    # → [("coherence_maintenance", 0.72), ("framing_selection", 0.55)]
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class SubsystemReport:
    """One confidence report from one subsystem."""
    source: str          # "DPME.process", "ExpressionEcology.select", ...
    module: str          # filename without .py
    confidence: float    # 0.0 (very low) → 1.0 (very high)
    dimension_hint: str  # fail dimension this maps to most directly
    detail: str = ""     # optional extra info for debugging


class TurnTelemetry:
    """
    Thread-safe accumulator of per-turn subsystem confidence reports.

    Lifecycle:
        reset()   — called once before each response is generated
        report()  — called by each subsystem after its contribution
        mechanistic_fails() — called by DreamTrainer after the turn
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._reports: List[SubsystemReport] = []
        self._turn_id: int = 0

    def reset(self, turn_id: int = 0) -> None:
        """Clear all reports. Call once at the start of each response turn."""
        with self._lock:
            self._reports.clear()
            self._turn_id = turn_id

    def report(
        self,
        source: str,
        module: str,
        confidence: float,
        dimension_hint: str,
        detail: str = "",
    ) -> None:
        """Record a subsystem's confidence after its contribution."""
        with self._lock:
            self._reports.append(SubsystemReport(
                source=source,
                module=module,
                confidence=max(0.0, min(1.0, float(confidence))),
                dimension_hint=dimension_hint,
                detail=detail,
            ))

    def get_all(self) -> List[SubsystemReport]:
        with self._lock:
            return list(self._reports)

    def get_weak_points(self, threshold: float = 0.45) -> List[SubsystemReport]:
        """Return reports where confidence was below threshold."""
        with self._lock:
            return [r for r in self._reports if r.confidence < threshold]

    def lowest(self) -> Optional[SubsystemReport]:
        """Return the lowest-confidence report, or None if empty."""
        with self._lock:
            if not self._reports:
                return None
            return min(self._reports, key=lambda r: r.confidence)

    def mechanistic_fails(
        self, threshold: float = 0.45
    ) -> List[Tuple[str, float]]:
        """
        Return (dimension_hint, severity) pairs from weak subsystems,
        sorted by severity descending.

        severity = 1.0 - confidence, so lower confidence = higher severity.
        Multiple reports for the same dimension are merged by taking the worst.
        """
        weak = self.get_weak_points(threshold)
        if not weak:
            return []

        by_dim: Dict[str, float] = {}
        for r in weak:
            severity = 1.0 - r.confidence
            if r.dimension_hint not in by_dim or severity > by_dim[r.dimension_hint]:
                by_dim[r.dimension_hint] = severity

        return sorted(by_dim.items(), key=lambda x: x[1], reverse=True)

    def set_axis_context(self, axis_activation: Dict[str, float]) -> None:
        """
        Store the current turn's constraint-axis activation vector so
        classify_fail_dimensions() can weight fail severities by the
        constraint geometry of the input that produced the failure.

        Called from aurora.py after _field_balancer.update().
        """
        with self._lock:
            self._axis_activation: Dict[str, float] = dict(axis_activation)

    def get_axis_context(self) -> Dict[str, float]:
        with self._lock:
            return dict(getattr(self, "_axis_activation", {}))

    def axis_weighted_fails(
        self,
        base_fails: List[Tuple[str, float]],
    ) -> List[Tuple[str, float]]:
        """
        Boost fail-dimension severities based on which constraint axis
        dominated this turn.  Axis → most-affected dimensions:
          A (agency/inner)  → emotional_calibration, perspective_integration
          X (existence)     → semantic_precision, coherence_maintenance
          T (temporal)      → context_carryover, coherence_maintenance
          B (boundary)      → perspective_integration, compression_elaboration_fit
          N (energy/cost)   → compression_elaboration_fit, semantic_precision
        """
        _AXIS_DIM_BOOST: Dict[str, Dict[str, float]] = {
            "A": {"emotional_calibration": 0.25, "perspective_integration": 0.15,
                  "uncertainty_signaling": 0.10},
            "X": {"semantic_precision": 0.20, "coherence_maintenance": 0.15},
            # T-axis cascade: T failure cascades into every dimension that
            # depends on sequencing. These are T-axis-derived failures, not
            # independent failures. The curriculum should target T-axis recovery
            # rather than treating each downstream dim as a separate root cause.
            "T": {
                "context_carryover": 0.30,      # primary T cascade
                "coherence_maintenance": 0.25,  # secondary T cascade
                "perspective_integration": 0.15,  # T cascade (can't hold perspectives without continuity)
                "multi_turn_stability": 0.20,   # direct T cascade
            },
            "B": {"emotional_calibration": 0.20, "perspective_integration": 0.15, "compression_elaboration_fit": 0.10},
            "N": {"compression_elaboration_fit": 0.20, "semantic_precision": 0.10},
        }

        # T-axis cascade dims — when T is dominant, downstream failures are
        # tagged as T-cascade-derived so lesson planning targets the root axis.
        _T_CASCADE_DIMS = frozenset({
            "context_carryover", "coherence_maintenance",
            "multi_turn_stability", "perspective_integration",
        })

        ax = self.get_axis_context()
        if not ax or not base_fails:
            return base_fails

        # Find dominant axis
        dominant = max(ax, key=lambda k: ax.get(k, 0.0))
        dom_strength = ax.get(dominant, 0.0)
        if dom_strength < 0.25:
            return base_fails   # Weak dominance — don't boost

        boosts = _AXIS_DIM_BOOST.get(dominant, {})
        merged = dict(base_fails)
        for dim, boost in boosts.items():
            if dim in merged:
                merged[dim] = min(1.0, merged[dim] + boost * dom_strength)
            elif dom_strength > 0.35:
                base_sev = max((v for v in merged.values()), default=0.5)
                merged[dim] = min(1.0, base_sev * boost * dom_strength * 2.0)

        # T-axis cascade annotation: mark downstream dims as T-derived so
        # the curriculum targets T recovery, not each dim independently.
        if dominant == "T" and dom_strength >= 0.30:
            for dim in list(merged.keys()):
                if dim in _T_CASCADE_DIMS:
                    # Store cascade marker via hint_fail_dimension provenance
                    try:
                        from aurora_internal.constraint_genealogy import hint_fail_dimension
                        hint_fail_dimension(f"T_cascade:{dim}", ttl=30.0)
                    except Exception:
                        pass

        return sorted(merged.items(), key=lambda x: x[1], reverse=True)

    def magnitude_weighted_severity(self) -> float:
        """
        Compute composite impact severity using the canonical magnitude formula:

            Impact = ((B × T × X) / N) × A

        where each axis value is its fail severity (1.0 - activation).

        N is treated as a denominator: high N activation (more energy available)
        reduces overall composite severity. N_denom is clamped to 0.1 to avoid /0.

        Returns a float in [0.0, 1.0+] indicating composite field impact severity.
        A value > 0.5 indicates significant multi-axis field degradation.

        Returns 0.0 when no axis context is available (call set_axis_context first).
        """
        ax = self.get_axis_context()
        if not ax:
            return 0.0
        # Severity = 1.0 - activation for each axis (low activation = high problem)
        b_sev = 1.0 - float(ax.get("B", 0.5))
        t_sev = 1.0 - float(ax.get("T", 0.5))
        x_sev = 1.0 - float(ax.get("X", 0.5))
        n_act = max(0.1, float(ax.get("N", 0.5)))   # N as denominator — high energy available = lower severity
        a_sev = 1.0 - float(ax.get("A", 0.5))
        magnitude = (b_sev * t_sev * x_sev) / n_act
        return float(magnitude * a_sev)

    def get_turn_id(self) -> int:
        """Return the turn_id set by the most recent reset() call."""
        with self._lock:
            return self._turn_id

    def has_data(self) -> bool:
        with self._lock:
            return bool(self._reports)


# ── Process-global singleton ──────────────────────────────────────────────────

_telemetry = TurnTelemetry()


def get_telemetry() -> TurnTelemetry:
    """Return the process-global TurnTelemetry singleton."""
    return _telemetry

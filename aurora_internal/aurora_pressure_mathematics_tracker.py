#!/usr/bin/env python3
"""
AURORA PRESSURE MATHEMATICS TRACKER
========================================
Lightweight instrumentation that taps into existing data streams to
track the core quantities from Aurora's pressure mathematics framework.

NOT a new system. This reads what's already flowing:
  - DPME drift metrics (consciousness engine)
  - Genealogy relief records and link stats (constraint genealogy)
  - Code evolution stagnation and mutation stats (code evolution chamber)
  - Dream evolution episode summaries (dream evolution orchestrator)

Computes:
  A. Gradient health — driver vs opposition balance across axes
  B. Pressure complexity — how many active pressure interactions exist
  C. Divergence — how far actual pressure topology drifts from origin model
  D. Flip indicators — signs of approaching pressure regime transitions
  E. Stagnation detection — where equilibrium is killing useful disequilibrium

Feeds these back through Aurora's own pressure channels (DPME guidance,
genealogy notes) so the system can self-regulate from them.

Authors: Sunni (Sir) Morningstar and Cael Devo
"""

from __future__ import annotations

import json
import logging
import math
import os
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional, Tuple

_STATE_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aurora_state")

logger = logging.getLogger("aurora.pressure_math")

# The five base constraint axes
AXES = ("X", "T", "N", "B", "A")


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


# ============================================================================
# SNAPSHOT — one point-in-time reading of all pressure streams
# ============================================================================

@dataclass
class PressureSnapshot:
    """Single timestamped capture of all trackable pressure metrics."""
    timestamp: float = field(default_factory=time.time)

    # From DPME detect_drift()
    coherence_delta: float = 0.0
    alignment_delta: float = 0.0
    stagnation: float = 0.0
    novelty: float = 0.0
    vitality_pressure: float = 0.0
    der_presence: float = 0.5
    der_total_energy: float = 0.0
    dmm_vitality: float = 0.5
    collective_balance: float = 0.5

    # From genealogy get_stats()
    total_links: int = 0
    link_promotion_rate: float = 0.0  # links promoted per observation
    dominant_axis_distribution: Dict[str, float] = field(default_factory=dict)
    coupling_validation_rate: float = 0.0

    # From code evolution chamber summary()
    code_stagnation_gain: float = 0.0
    code_acceptance_rate: float = 0.0
    code_deepest_generation: int = 0
    operator_gradients: Dict[str, float] = field(default_factory=dict)

    # From dream evolution (if active)
    dream_episode_fitness: float = 0.0
    dream_leverage_count: int = 0
    dream_persistent_weaknesses: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "coherence_delta": self.coherence_delta,
            "alignment_delta": self.alignment_delta,
            "stagnation": self.stagnation,
            "novelty": self.novelty,
            "vitality_pressure": self.vitality_pressure,
            "der_presence": self.der_presence,
            "der_total_energy": self.der_total_energy,
            "dmm_vitality": self.dmm_vitality,
            "collective_balance": self.collective_balance,
            "total_links": self.total_links,
            "link_promotion_rate": self.link_promotion_rate,
            "dominant_axis_distribution": dict(self.dominant_axis_distribution),
            "coupling_validation_rate": self.coupling_validation_rate,
            "code_stagnation_gain": self.code_stagnation_gain,
            "code_acceptance_rate": self.code_acceptance_rate,
            "code_deepest_generation": self.code_deepest_generation,
            "operator_gradients": dict(self.operator_gradients),
            "dream_episode_fitness": self.dream_episode_fitness,
            "dream_leverage_count": self.dream_leverage_count,
            "dream_persistent_weaknesses": self.dream_persistent_weaknesses,
        }


# ============================================================================
# COMPUTED METRICS — derived from snapshot history
# ============================================================================

@dataclass
class PressureMetrics:
    """Derived pressure mathematics metrics from snapshot history."""
    timestamp: float = field(default_factory=time.time)

    # A. Gradient health per axis (0 = dead equilibrium, 1 = strong gradient)
    gradient_health: Dict[str, float] = field(default_factory=dict)

    # B. Pressure complexity estimate
    active_pressure_interactions: int = 0
    complexity_ratio: float = 0.0  # actual / theoretical_max

    # C. Divergence from origin model
    divergence: float = 0.0
    divergence_trend: float = 0.0  # positive = diverging, negative = converging

    # D. Flip indicators
    flip_proximity: float = 0.0  # 0 = stable, 1 = flip imminent
    regime_age: int = 0  # snapshots since last detected regime change

    # E. Stagnation map
    stagnation_axes: Dict[str, float] = field(default_factory=dict)
    overall_stagnation: float = 0.0

    # F. Developmental velocity
    evolutionary_velocity: float = 0.0  # rate of structural change
    pressure_velocity: float = 0.0  # rate of pressure reorganization

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "gradient_health": dict(self.gradient_health),
            "active_pressure_interactions": self.active_pressure_interactions,
            "complexity_ratio": self.complexity_ratio,
            "divergence": self.divergence,
            "divergence_trend": self.divergence_trend,
            "flip_proximity": self.flip_proximity,
            "regime_age": self.regime_age,
            "stagnation_axes": dict(self.stagnation_axes),
            "overall_stagnation": self.overall_stagnation,
            "evolutionary_velocity": self.evolutionary_velocity,
            "pressure_velocity": self.pressure_velocity,
        }

    def to_feedback_summary(self) -> str:
        """Produce a compact string Aurora can ingest as context."""
        parts = []
        if self.overall_stagnation > 0.4:
            stag_axes = [a for a, v in self.stagnation_axes.items() if v > 0.4]
            parts.append(f"stagnation({','.join(stag_axes)}:{self.overall_stagnation:.2f})")
        if self.flip_proximity > 0.5:
            parts.append(f"flip_proximity:{self.flip_proximity:.2f}")
        if self.divergence_trend > 0.05:
            parts.append(f"diverging:{self.divergence:.2f}")
        elif self.divergence_trend < -0.05:
            parts.append(f"converging:{self.divergence:.2f}")
        weak = [a for a, v in self.gradient_health.items() if v < 0.3]
        if weak:
            parts.append(f"weak_gradients({','.join(weak)})")
        if self.complexity_ratio > 0:
            parts.append(f"complexity:{self.complexity_ratio:.2f}")
        return " | ".join(parts) if parts else "pressure_stable"


# ============================================================================
# ORIGIN MODEL — predicted pressure topology from five-constraint base
# ============================================================================

class OriginModel:
    """
    Predicted pressure topology from the five-constraint origin.

    Early in development, actual behavior should match this closely.
    Divergence from this model IS the developmental signal.
    """

    def __init__(self):
        # Base: each axis should have roughly equal gradient health
        self.expected_gradient_health = {a: 0.5 for a in AXES}

        # Expected: pressure interactions grow combinatorially
        # 5 axes × 5 representations = 25 base, plus C(5,2)=10 cross interactions
        self.expected_base_interactions = 25
        self.expected_cross_interactions = 10
        self.expected_total = self.expected_base_interactions + self.expected_cross_interactions

        # Expected: axis distribution should be roughly even early on
        self.expected_axis_distribution = {a: 1.0 / len(AXES) for a in AXES}

        # Expected: stagnation should be low early, rising slowly
        self.expected_stagnation_curve = 0.1  # baseline

    def compute_divergence(
        self,
        gradient_health: Dict[str, float],
        axis_distribution: Dict[str, float],
        stagnation: float,
        complexity_ratio: float,
    ) -> float:
        """
        Compute divergence between actual state and origin prediction.

        Returns 0.0 (perfect match) to 1.0+ (significant divergence).
        """
        div = 0.0

        # Gradient health divergence (per axis)
        for axis in AXES:
            actual = gradient_health.get(axis, 0.5)
            expected = self.expected_gradient_health[axis]
            div += abs(actual - expected) ** 2

        # Axis distribution divergence (entropy-like)
        for axis in AXES:
            actual = axis_distribution.get(axis, 0.2)
            expected = self.expected_axis_distribution[axis]
            if actual > 0 and expected > 0:
                div += abs(actual - expected) * 0.5

        # Stagnation divergence
        div += abs(stagnation - self.expected_stagnation_curve) * 0.3

        # Complexity divergence
        div += abs(complexity_ratio - 0.5) * 0.2

        return div


# ============================================================================
# MAIN TRACKER
# ============================================================================

class PressureMathematicsTracker:
    """
    Lightweight tracker that reads existing data streams, computes
    pressure mathematics metrics, and feeds them back to Aurora.

    Call capture() periodically (e.g., after each dream cycle or
    chain tick) to take a snapshot and update metrics.
    """

    # How many snapshots to retain
    HISTORY_SIZE = 200

    # Minimum snapshots before computing trend metrics
    MIN_HISTORY_FOR_TRENDS = 5

    # Flip detection: divergence must change by this much to signal a flip
    FLIP_DIVERGENCE_THRESHOLD = 0.15

    def __init__(self, storage_dir: str = os.path.join(_STATE_ROOT, "pressure_math")):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

        self.origin_model = OriginModel()
        self._history: Deque[PressureSnapshot] = deque(maxlen=self.HISTORY_SIZE)
        self._metrics_history: Deque[PressureMetrics] = deque(maxlen=self.HISTORY_SIZE)
        self._latest_metrics: Optional[PressureMetrics] = None
        self._regime_start_idx: int = 0  # snapshot index when current regime began
        self._flip_count: int = 0
        self._captures: int = 0

        self._load_state()

    # ================================================================
    # CAPTURE — read all available data streams
    # ================================================================

    def capture(self, systems: Dict[str, Any]) -> PressureMetrics:
        """
        Take a snapshot from all available data streams and compute metrics.

        Args:
            systems: The AutonomyEngine systems dict (or any dict with
                     'simulation', 'perception', etc.)

        Returns:
            Computed PressureMetrics for this capture.
        """
        snapshot = self._take_snapshot(systems)
        self._history.append(snapshot)
        self._captures += 1

        metrics = self._compute_metrics()
        self._metrics_history.append(metrics)
        self._latest_metrics = metrics

        # Persist periodically
        if self._captures % 10 == 0:
            self._save_state()

        return metrics

    def _take_snapshot(self, systems: Dict[str, Any]) -> PressureSnapshot:
        """Read all available data streams into a snapshot."""
        snap = PressureSnapshot()

        # ---- DPME drift metrics ----
        try:
            consciousness = systems.get('consciousness')
            if consciousness and hasattr(consciousness, 'dpme'):
                drift = consciousness.dpme.detect_drift()
                if isinstance(drift, dict):
                    snap.coherence_delta = drift.get('coherence_delta', 0.0)
                    snap.alignment_delta = drift.get('alignment_delta', 0.0)
                    snap.stagnation = drift.get('stagnation', 0.0)
                    snap.novelty = drift.get('novelty', 0.0)
                    snap.vitality_pressure = drift.get('vitality_pressure', 0.0)
                    snap.der_presence = drift.get('der_presence', 0.5)
                    snap.der_total_energy = drift.get('der_total_energy', 0.0)
                    snap.dmm_vitality = drift.get('dmm_vitality', 0.5)
                    snap.collective_balance = drift.get('collective_balance', 0.5)
        except Exception as e:
            logger.debug(f"[PRESSURE-MATH] DPME read: {e}")

        # ---- Genealogy stats ----
        try:
            genealogy = systems.get('genealogy')
            if not genealogy:
                # Try through runtime systems
                rt = systems.get('_runtime_systems')
                if rt and hasattr(rt, 'genealogy'):
                    genealogy = rt.genealogy

            if genealogy and hasattr(genealogy, 'get_stats'):
                stats = genealogy.get_stats()
                if isinstance(stats, dict):
                    snap.total_links = stats.get('total_links', 0)
                    tick = stats.get('tick_count', 1) or 1
                    snap.link_promotion_rate = snap.total_links / max(tick, 1)
                    snap.dominant_axis_distribution = {
                        a: stats.get('by_dominant_axis', {}).get(a, 0)
                        for a in AXES
                    }
                    # Normalize distribution
                    total_dom = sum(snap.dominant_axis_distribution.values()) or 1.0
                    snap.dominant_axis_distribution = {
                        a: v / total_dom
                        for a, v in snap.dominant_axis_distribution.items()
                    }
                    vr = stats.get('validation_completeness_rate', 0.0)
                    snap.coupling_validation_rate = vr
        except Exception as e:
            logger.debug(f"[PRESSURE-MATH] Genealogy read: {e}")

        # ---- Code evolution stats ----
        try:
            code_chamber = systems.get('code_chamber')
            if not code_chamber:
                rt = systems.get('_runtime_systems')
                if rt and hasattr(rt, 'chamber'):
                    code_chamber = rt.chamber

            if code_chamber:
                if hasattr(code_chamber, '_governor'):
                    snap.code_stagnation_gain = code_chamber._governor.stagnation_gain()
                if hasattr(code_chamber, 'summary'):
                    cs = code_chamber.summary()
                    if isinstance(cs, dict):
                        accepted = cs.get('accepted_count', 0)
                        rejected = cs.get('rejected_count', 0)
                        total = accepted + rejected
                        snap.code_acceptance_rate = accepted / max(total, 1)
                        snap.code_deepest_generation = cs.get(
                            'lineage_deepest_generation', 0
                        )
                        snap.operator_gradients = cs.get('operator_gradients', {})
        except Exception as e:
            logger.debug(f"[PRESSURE-MATH] Code evolution read: {e}")

        # ---- Dream evolution stats ----
        try:
            autonomy = systems.get('autonomy') or systems.get('_autonomy')
            if autonomy and hasattr(autonomy, '_dream_evo') and autonomy._dream_evo:
                evo_status = autonomy._dream_evo.get_status()
                snap.dream_episode_fitness = evo_status.get(
                    'last_episode_fitness', 0.0
                ) or 0.0
                snap.dream_leverage_count = evo_status.get(
                    'active_directives', 0
                )
                # Persistent weaknesses tracked indirectly through directives
                snap.dream_persistent_weaknesses = evo_status.get(
                    'total_directives_generated', 0
                )
        except Exception as e:
            logger.debug(f"[PRESSURE-MATH] Dream evolution read: {e}")

        return snap

    # ================================================================
    # COMPUTE — derive pressure mathematics metrics from history
    # ================================================================

    def _compute_metrics(self) -> PressureMetrics:
        """Compute derived metrics from snapshot history."""
        metrics = PressureMetrics()

        if not self._history:
            return metrics

        latest = self._history[-1]

        # ---- A. Gradient health per axis ----
        metrics.gradient_health = self._compute_gradient_health(latest)

        # ---- B. Pressure complexity ----
        metrics.active_pressure_interactions = self._estimate_active_interactions(latest)
        theoretical_max = self.origin_model.expected_total
        metrics.complexity_ratio = _clamp(
            metrics.active_pressure_interactions / max(theoretical_max, 1),
            0.0, 2.0,
        )

        # ---- C. Divergence from origin model ----
        metrics.divergence = self.origin_model.compute_divergence(
            gradient_health=metrics.gradient_health,
            axis_distribution=latest.dominant_axis_distribution,
            stagnation=latest.stagnation,
            complexity_ratio=metrics.complexity_ratio,
        )

        # Divergence trend (compare to previous)
        if len(self._metrics_history) >= self.MIN_HISTORY_FOR_TRENDS:
            prev_divs = [m.divergence for m in list(self._metrics_history)[-10:]]
            if len(prev_divs) >= 2:
                recent = sum(prev_divs[-3:]) / len(prev_divs[-3:])
                earlier = sum(prev_divs[:3]) / len(prev_divs[:3])
                metrics.divergence_trend = recent - earlier

        # ---- D. Flip indicators ----
        metrics.flip_proximity = self._detect_flip_proximity()
        metrics.regime_age = len(self._history) - self._regime_start_idx

        # Check for actual flip
        if metrics.flip_proximity > 0.7 and metrics.regime_age > 10:
            self._regime_start_idx = len(self._history) - 1
            self._flip_count += 1
            logger.info(
                f"[PRESSURE-MATH] Regime flip #{self._flip_count} detected "
                f"(divergence={metrics.divergence:.3f})"
            )

        # ---- E. Stagnation map ----
        metrics.stagnation_axes = self._compute_axis_stagnation()
        metrics.overall_stagnation = (
            sum(metrics.stagnation_axes.values()) /
            max(len(metrics.stagnation_axes), 1)
        )

        # ---- F. Developmental velocity ----
        if len(self._history) >= self.MIN_HISTORY_FOR_TRENDS:
            metrics.evolutionary_velocity = self._compute_evolutionary_velocity()
            metrics.pressure_velocity = self._compute_pressure_velocity()

        return metrics

    def _compute_gradient_health(self, snap: PressureSnapshot) -> Dict[str, float]:
        """
        Estimate gradient health per axis.

        Gradient health = degree of useful disequilibrium.
        0 = dead equilibrium (no gradient), 1 = strong active gradient.

        Uses operator gradients from code evolution + DPME drift signals
        to estimate whether each axis has active pressure dynamics.
        """
        health = {}
        for axis in AXES:
            signals = []

            # Operator gradient on this axis (from code evolution)
            op_grad = abs(snap.operator_gradients.get(axis, 0.0))
            signals.append(_clamp(op_grad * 5.0))  # Scale up small gradients

            # Axis distribution imbalance (from genealogy)
            dist = snap.dominant_axis_distribution.get(axis, 0.2)
            # Far from 0.2 (even) = more activity on this axis
            axis_activity = abs(dist - 0.2) * 3.0
            signals.append(_clamp(axis_activity + 0.3))

            # DPME-derived signals mapped to axes
            if axis == "X":
                signals.append(_clamp(snap.der_presence * 1.2))
            elif axis == "T":
                signals.append(_clamp(abs(snap.coherence_delta) * 10.0 + 0.2))
            elif axis == "N":
                signals.append(_clamp(snap.der_total_energy / 50.0))
            elif axis == "B":
                signals.append(_clamp(snap.dmm_vitality))
            elif axis == "A":
                signals.append(_clamp(snap.novelty))

            # Anti-stagnation: pure stagnation kills gradient health
            stag_penalty = snap.stagnation * 0.3
            raw_health = sum(signals) / max(len(signals), 1) - stag_penalty

            health[axis] = _clamp(raw_health, 0.0, 1.0)

        return health

    def _estimate_active_interactions(self, snap: PressureSnapshot) -> int:
        """
        Estimate how many pressure interactions are actively producing gradients.

        Uses link count + promotion rate + axis distribution as proxies.
        """
        # Base interactions: one per link that has a dominant axis
        base = snap.total_links

        # Cross-axis interactions: links that span multiple axes
        # Approximated by axis distribution evenness (more even = more cross-axis)
        dist_vals = list(snap.dominant_axis_distribution.values())
        if dist_vals:
            evenness = 1.0 - max(dist_vals) + min(dist_vals)
            cross = int(base * evenness * 0.5)
        else:
            cross = 0

        # Code evolution adds structural interactions
        code_interactions = snap.code_deepest_generation * 2

        return base + cross + code_interactions

    def _detect_flip_proximity(self) -> float:
        """
        Detect how close we are to a pressure regime flip.

        A flip is signaled by:
        - Rapid divergence acceleration
        - Stagnation rising while novelty drops
        - Multiple axes losing gradient health simultaneously
        """
        if len(self._history) < self.MIN_HISTORY_FOR_TRENDS:
            return 0.0

        recent = list(self._history)[-5:]
        earlier = list(self._history)[-10:-5] if len(self._history) >= 10 else []

        signals = []

        # Signal 1: Divergence acceleration
        if len(self._metrics_history) >= 5:
            recent_divs = [m.divergence for m in list(self._metrics_history)[-5:]]
            div_velocity = recent_divs[-1] - recent_divs[0] if recent_divs else 0.0
            signals.append(_clamp(div_velocity / self.FLIP_DIVERGENCE_THRESHOLD))

        # Signal 2: Stagnation rising while novelty drops
        if recent:
            stag_trend = recent[-1].stagnation - recent[0].stagnation
            novelty_trend = recent[-1].novelty - recent[0].novelty
            if stag_trend > 0 and novelty_trend < 0:
                signals.append(_clamp(stag_trend * 3.0 + abs(novelty_trend) * 2.0))
            else:
                signals.append(0.0)

        # Signal 3: Multiple axes weakening
        if self._latest_metrics and self._latest_metrics.gradient_health:
            weak_count = sum(
                1 for v in self._latest_metrics.gradient_health.values()
                if v < 0.3
            )
            signals.append(_clamp(weak_count / 3.0))

        # Signal 4: Code evolution stagnation spiking
        if recent:
            signals.append(_clamp(recent[-1].code_stagnation_gain * 1.5))

        return sum(signals) / max(len(signals), 1) if signals else 0.0

    def _compute_axis_stagnation(self) -> Dict[str, float]:
        """Compute per-axis stagnation from gradient health history."""
        if len(self._metrics_history) < self.MIN_HISTORY_FOR_TRENDS:
            return {a: 0.0 for a in AXES}

        stagnation = {}
        recent_metrics = list(self._metrics_history)[-10:]

        for axis in AXES:
            # Stagnation = low variance in gradient health over time
            values = [m.gradient_health.get(axis, 0.5) for m in recent_metrics]
            if len(values) < 3:
                stagnation[axis] = 0.0
                continue

            mean = sum(values) / len(values)
            variance = sum((v - mean) ** 2 for v in values) / len(values)

            # Low variance + low mean = stagnant axis
            # Low variance + high mean = stable but healthy
            stag = (1.0 - min(1.0, math.sqrt(variance) * 10.0)) * (1.0 - mean)
            stagnation[axis] = _clamp(stag)

        return stagnation

    def _compute_evolutionary_velocity(self) -> float:
        """Rate of structural change (links, generations)."""
        if len(self._history) < self.MIN_HISTORY_FOR_TRENDS:
            return 0.0
        recent = list(self._history)[-5:]
        link_delta = recent[-1].total_links - recent[0].total_links
        gen_delta = recent[-1].code_deepest_generation - recent[0].code_deepest_generation
        return _clamp((link_delta + gen_delta * 5) / 50.0)

    def _compute_pressure_velocity(self) -> float:
        """Rate of pressure reorganization."""
        if len(self._metrics_history) < self.MIN_HISTORY_FOR_TRENDS:
            return 0.0
        recent = list(self._metrics_history)[-5:]
        div_change = abs(recent[-1].divergence - recent[0].divergence)
        stag_change = abs(recent[-1].overall_stagnation - recent[0].overall_stagnation)
        return _clamp(div_change + stag_change)

    # ================================================================
    # FEEDBACK — feed metrics back into Aurora's pressure channels
    # ================================================================

    def generate_feedback(self) -> Dict[str, Any]:
        """
        Generate feedback that can be routed back into Aurora's systems.

        Returns dict with:
          - dpme_guidance: for set_external_pressure_guidance()
          - genealogy_notes: metadata to attach to future genealogy observations
          - summary_text: compact string for Aurora's awareness context
        """
        if not self._latest_metrics:
            return {}

        m = self._latest_metrics
        feedback: Dict[str, Any] = {}

        # ---- DPME guidance ----
        # If stagnation is high on specific axes, steer energy toward those axes
        if m.overall_stagnation > 0.3:
            worst_axis = max(m.stagnation_axes.items(), key=lambda kv: kv[1])
            axis_to_channel = {
                "X": "vitality",
                "T": "processing",
                "N": "memory",
                "B": "emotional",
                "A": "creative",
            }
            primary = axis_to_channel.get(worst_axis[0], "processing")

            # Find secondary: next most stagnant
            sorted_stag = sorted(
                m.stagnation_axes.items(), key=lambda kv: kv[1], reverse=True
            )
            secondary = None
            if len(sorted_stag) > 1 and sorted_stag[1][1] > 0.2:
                secondary = axis_to_channel.get(sorted_stag[1][0])

            feedback["dpme_guidance"] = {
                "score": _clamp(m.overall_stagnation, 0.0, 1.0),
                "compare_value": _clamp(m.overall_stagnation * 0.5),
                "primary_channel": primary,
                "secondary_channel": secondary,
            }

        # ---- Genealogy notes ----
        # Attach pressure math context to future genealogy observations
        feedback["genealogy_notes"] = {
            "pressure_math_divergence": m.divergence,
            "pressure_math_flip_proximity": m.flip_proximity,
            "pressure_math_stagnation": m.overall_stagnation,
            "pressure_math_regime_age": m.regime_age,
            "pressure_math_flip_count": self._flip_count,
        }

        # ---- Summary text for Aurora's context ----
        feedback["summary_text"] = m.to_feedback_summary()

        return feedback

    def apply_feedback(self, systems: Dict[str, Any]):
        """Apply generated feedback into live systems."""
        feedback = self.generate_feedback()
        if not feedback:
            return

        # Apply DPME guidance
        dpme_guidance = feedback.get("dpme_guidance")
        if dpme_guidance:
            try:
                from aurora_consciousness_engine import set_external_pressure_guidance
                set_external_pressure_guidance(dpme_guidance)
                logger.debug(
                    f"[PRESSURE-MATH] DPME feedback: "
                    f"channel={dpme_guidance.get('primary_channel')}, "
                    f"stagnation={dpme_guidance.get('score', 0):.2f}"
                )
            except Exception as e:
                logger.debug(f"[PRESSURE-MATH] DPME feedback skipped: {e}")

    # ================================================================
    # STATUS / PERSISTENCE
    # ================================================================

    def get_status(self) -> Dict[str, Any]:
        """Return current tracker status."""
        return {
            "captures": self._captures,
            "history_length": len(self._history),
            "flip_count": self._flip_count,
            "latest_metrics": (
                self._latest_metrics.to_dict()
                if self._latest_metrics else None
            ),
        }

    def _save_state(self):
        """Persist recent history and metrics."""
        path = os.path.join(self.storage_dir, "pressure_math_state.json")
        try:
            # Save last 50 snapshots and metrics
            data = {
                "captures": self._captures,
                "flip_count": self._flip_count,
                "regime_start_idx": self._regime_start_idx,
                "snapshots": [s.to_dict() for s in list(self._history)[-50:]],
                "metrics": [m.to_dict() for m in list(self._metrics_history)[-50:]],
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.debug(f"[PRESSURE-MATH] Save failed: {e}")

    def _load_state(self):
        """Restore persisted state."""
        path = os.path.join(self.storage_dir, "pressure_math_state.json")
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._captures = data.get("captures", 0)
            self._flip_count = data.get("flip_count", 0)
            self._regime_start_idx = data.get("regime_start_idx", 0)
            # Don't reload full history — it rebuilds from live data
        except Exception:
            pass
_STATE_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aurora_state")

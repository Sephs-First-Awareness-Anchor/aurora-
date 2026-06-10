"""
aurora_response_pressure_tuner.py
=================================
Reusable tuner for spontaneous-response pressure decisions.

It does not replace the response policy by itself. It records the signal,
counter-pressure, threshold, and decision margin for each emit/suppress event
so Aurora can inspect recurring pressure patterns and reuse them during
training and runtime tuning.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Tuple


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


RESPONSE_PRESSURE_DIMENSION_MAP: Dict[str, Dict[str, float]] = {
    "thought": {
        "boundary_calibration": 0.95,
        "framing_selection": 0.85,
        "adaptive_strategy_selection": 0.80,
        "compression_elaboration_fit": 0.65,
    },
    "dream": {
        "coherence_maintenance": 0.90,
        "multi_turn_stability": 0.85,
        "framing_selection": 0.75,
        "boundary_calibration": 0.70,
    },
    "study": {
        "semantic_precision": 0.80,
        "uncertainty_signaling": 0.70,
        "compression_elaboration_fit": 0.60,
    },
    "curiosity": {
        "ambiguity_handling": 0.80,
        "uncertainty_signaling": 0.85,
        "perspective_integration": 0.55,
    },
    "observation": {
        "boundary_calibration": 0.60,
        "adaptive_strategy_selection": 0.70,
        "context_carryover": 0.55,
    },
    "reply": {
        "framing_selection": 0.85,
        "semantic_precision": 0.80,
        "compression_elaboration_fit": 0.75,
        "adaptive_strategy_selection": 0.70,
    },
    "followup": {
        "context_carryover": 0.95,
        "multi_turn_stability": 0.85,
        "ambiguity_handling": 0.70,
        "framing_selection": 0.60,
    },
    "repair": {
        "contradiction_handling": 0.95,
        "misunderstanding_repair": 0.90,
        "boundary_calibration": 0.70,
        "uncertainty_signaling": 0.55,
    },
    "uncertainty": {
        "uncertainty_signaling": 0.95,
        "semantic_precision": 0.75,
        "compression_elaboration_fit": 0.70,
    },
}

RESPONSE_PRESSURE_AXIS_MAP: Dict[str, str] = {
    "coherence_maintenance": "T",
    "context_carryover": "T",
    "ambiguity_handling": "B",
    "contradiction_handling": "B",
    "implied_intent_inference": "A",
    "misunderstanding_repair": "A",
    "uncertainty_signaling": "N",
    "boundary_calibration": "B",
    "framing_selection": "A",
    "emotional_calibration": "B",
    "semantic_precision": "X",
    "adaptive_strategy_selection": "A",
    "compression_elaboration_fit": "N",
    "perspective_integration": "B",
    "multi_turn_stability": "T",
}


@dataclass
class PressureDecision:
    namespace: str
    kind: str
    content: str
    signal: float
    threshold: float
    counter_pressure: float
    emitted: bool
    margin: float
    factors: Dict[str, float] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "namespace": self.namespace,
            "kind": self.kind,
            "content": self.content,
            "signal": self.signal,
            "threshold": self.threshold,
            "counter_pressure": self.counter_pressure,
            "emitted": self.emitted,
            "margin": self.margin,
            "factors": dict(self.factors),
            "context": dict(self.context),
            "timestamp": self.timestamp,
        }


class ResponsePressureTuner:
    """
    Records response-pressure decisions and derives guidance from them.

    The tuner is intentionally lightweight: it observes the runtime policy and
    produces reusable guidance instead of silently mutating thresholds.
    """

    def __init__(self, namespace: str = "response_pressure", max_history: int = 256):
        self.namespace = namespace
        self.history: Deque[Dict[str, Any]] = deque(maxlen=max_history)

    def evaluate(
        self,
        kind: str,
        content: str,
        signal: float,
        threshold: float,
        counter_pressure: float = 0.0,
        factors: Dict[str, float] | None = None,
        context: Dict[str, Any] | None = None,
        emitted: bool | None = None,
    ) -> PressureDecision:
        signal = _clamp(float(signal))
        threshold = _clamp(float(threshold), 0.0, 1.2)
        counter_pressure = _clamp(float(counter_pressure), 0.0, 1.2)
        if emitted is None:
            emitted = signal >= threshold
        margin = float(signal - threshold)
        decision = PressureDecision(
            namespace=self.namespace,
            kind=str(kind or ""),
            content=str(content or ""),
            signal=signal,
            threshold=threshold,
            counter_pressure=counter_pressure,
            emitted=bool(emitted),
            margin=margin,
            factors=dict(factors or {}),
            context=dict(context or {}),
        )
        self.history.append(decision.to_dict())
        return decision

    def guidance(self, n: int = 64) -> Dict[str, Any]:
        recent = list(self.history)[-max(1, int(n)):]
        if not recent:
            return {
                "namespace": self.namespace,
                "decisions": 0,
                "by_kind": {},
                "recommendations": [],
            }

        by_kind: Dict[str, Dict[str, float]] = defaultdict(lambda: {
            "decisions": 0.0,
            "emitted": 0.0,
            "suppressed": 0.0,
            "avg_signal": 0.0,
            "avg_threshold": 0.0,
            "avg_counter_pressure": 0.0,
            "avg_margin": 0.0,
        })

        for rec in recent:
            bucket = by_kind[str(rec.get("kind", "") or "unknown")]
            bucket["decisions"] += 1.0
            bucket["emitted"] += 1.0 if rec.get("emitted") else 0.0
            bucket["suppressed"] += 0.0 if rec.get("emitted") else 1.0
            bucket["avg_signal"] += float(rec.get("signal", 0.0) or 0.0)
            bucket["avg_threshold"] += float(rec.get("threshold", 0.0) or 0.0)
            bucket["avg_counter_pressure"] += float(rec.get("counter_pressure", 0.0) or 0.0)
            bucket["avg_margin"] += float(rec.get("margin", 0.0) or 0.0)

        recommendations: List[str] = []
        out_by_kind: Dict[str, Dict[str, float]] = {}
        for kind, bucket in by_kind.items():
            count = max(1.0, bucket["decisions"])
            stats = {
                "decisions": int(bucket["decisions"]),
                "emitted": int(bucket["emitted"]),
                "suppressed": int(bucket["suppressed"]),
                "avg_signal": bucket["avg_signal"] / count,
                "avg_threshold": bucket["avg_threshold"] / count,
                "avg_counter_pressure": bucket["avg_counter_pressure"] / count,
                "avg_margin": bucket["avg_margin"] / count,
            }
            out_by_kind[kind] = stats

            if stats["suppressed"] >= 3 and stats["avg_margin"] > -0.05:
                recommendations.append(
                    f"{kind}: threshold may be slightly too high under current counter-pressure."
                )
            if stats["emitted"] >= 3 and stats["avg_margin"] > 0.12:
                recommendations.append(
                    f"{kind}: emitted with large positive margin; consider raising pressure before surfacing."
                )
            if stats["avg_counter_pressure"] > 0.20 and stats["suppressed"] > stats["emitted"]:
                recommendations.append(
                    f"{kind}: counter-factors are dominating; train on calmer contexts or reduce interruption frequency."
                )

        return {
            "namespace": self.namespace,
            "decisions": len(recent),
            "by_kind": out_by_kind,
            "recommendations": recommendations[:8],
        }

    def export_state(self) -> Dict[str, Any]:
        return {
            "namespace": self.namespace,
            "history": list(self.history),
        }

    def load_state(self, state: Dict[str, Any] | None) -> None:
        if not isinstance(state, dict):
            return
        history = state.get("history", [])
        self.history.clear()
        for item in list(history)[-self.history.maxlen:]:
            if isinstance(item, dict):
                self.history.append(dict(item))


def build_training_plan_from_guides(
    guides: List[Tuple[str, Dict[str, Any]]],
    phase: str = "train",
) -> Dict[str, Any]:
    plan: Dict[str, Any] = {
        "phase": phase,
        "pressure_targets": {},
        "behavior_modes": {},
        "constraint_axes": {},
        "avatar_overrides": {},
        "study_topics": [],
        "episodes_bonus": 0,
        "turns_bonus": 0,
        "queue_repeats": 0,
        "rationale": [],
        "guide_sources": [name for name, _ in guides],
    }
    pressure_targets: Dict[str, float] = {}
    behavior_modes: Dict[str, float] = {}
    rationale: List[str] = []

    phase_low = str(phase or "").lower()
    if "meaning" in phase_low or "coherence" in phase_low or "grounding" in phase_low:
        phase_focus = {
            "coherence_maintenance": 0.82,
            "context_carryover": 0.78,
            "semantic_precision": 0.76,
            "implied_intent_inference": 0.72,
        }
        if "grounding" in phase_low:
            phase_focus["semantic_precision"] = max(phase_focus["semantic_precision"], 0.82)
        pressure_targets.update(phase_focus)
        behavior_modes["test_cross_turn_memory"] = max(
            behavior_modes.get("test_cross_turn_memory", 0.0),
            0.72,
        )
        rationale.append(
            "phase_focus: meaning/coherence emphasis seeded into training plan"
        )

    if not guides and not pressure_targets:
        return plan

    for source_name, guide in guides:
        by_kind = dict(guide.get("by_kind", {}) or {})
        for kind, stats in by_kind.items():
            decisions = max(1, int(stats.get("decisions", 0) or 0))
            suppression_rate = float(stats.get("suppressed", 0) or 0) / float(decisions)
            avg_counter = float(stats.get("avg_counter_pressure", 0.0) or 0.0)
            avg_margin = float(stats.get("avg_margin", 0.0) or 0.0)
            need = max(
                0.0,
                min(1.0, 0.45 * suppression_rate + 0.35 * avg_counter + 0.20 * abs(avg_margin)),
            )
            if need < 0.18:
                continue

            for dim, weight in RESPONSE_PRESSURE_DIMENSION_MAP.get(kind, {}).items():
                pressure_targets[dim] = max(
                    pressure_targets.get(dim, 0.0),
                    max(0.0, min(0.95, need * float(weight))),
                )

            if kind in ("thought", "dream", "followup"):
                behavior_modes["test_cross_turn_memory"] = max(
                    behavior_modes.get("test_cross_turn_memory", 0.0),
                    max(0.0, min(0.95, need * (0.75 + suppression_rate * 0.25))),
                )
            if suppression_rate > 0.25 or kind in ("uncertainty", "repair"):
                behavior_modes["ask_about_confidence"] = max(
                    behavior_modes.get("ask_about_confidence", 0.0),
                    max(0.0, min(0.95, need * 0.65 + avg_counter * 0.35)),
                )
            if kind in ("dream", "observation", "thought", "repair") and avg_counter > 0.12:
                behavior_modes["present_conflicting_evidence"] = max(
                    behavior_modes.get("present_conflicting_evidence", 0.0),
                    max(0.0, min(0.95, need * 0.70 + avg_counter * 0.25)),
                )
            if kind in ("curiosity", "thought", "followup") and suppression_rate > 0.30:
                behavior_modes["use_vague_phrasing"] = max(
                    behavior_modes.get("use_vague_phrasing", 0.0),
                    max(0.0, min(0.85, need * 0.60)),
                )

            rationale.append(
                f"{source_name}:{kind} suppression={suppression_rate:.2f} "
                f"counter={avg_counter:.2f} margin={avg_margin:+.2f}"
            )

    if not pressure_targets:
        plan["rationale"] = rationale[:8]
        return plan

    ranked_targets = sorted(
        pressure_targets.items(),
        key=lambda kv: float(kv[1]),
        reverse=True,
    )[:4]
    pressure_targets = {dim: float(round(val, 4)) for dim, val in ranked_targets}

    axis_scores: Dict[str, float] = {}
    for dim, intensity in pressure_targets.items():
        axis = RESPONSE_PRESSURE_AXIS_MAP.get(dim, "")
        if axis:
            axis_scores[axis] = max(axis_scores.get(axis, 0.0), intensity)

    pressure_strength = max(float(v) for v in pressure_targets.values())
    turns_bonus = 1 if float(behavior_modes.get("test_cross_turn_memory", 0.0)) > 0.45 else 0
    if float(behavior_modes.get("present_conflicting_evidence", 0.0)) > 0.55:
        turns_bonus += 1

    avatar_overrides = {
        "patience_modifier": max(1.0, min(1.25, 1.04 + pressure_strength * 0.18)),
        "min_acceptable_fitness": max(0.40, min(0.82, 0.46 + pressure_strength * 0.22)),
        "weight_adjustments": {
            "clarity": 0.16 if any(dim in pressure_targets for dim in (
                "coherence_maintenance", "semantic_precision", "context_carryover"
            )) else 0.0,
            "relevance": 0.14 if any(dim in pressure_targets for dim in (
                "boundary_calibration", "framing_selection", "contradiction_handling"
            )) else 0.0,
            "tone_match": 0.10 if any(dim in pressure_targets for dim in (
                "emotional_calibration", "perspective_integration"
            )) else 0.0,
            "engagement": 0.10 if any(dim in pressure_targets for dim in (
                "adaptive_strategy_selection", "compression_elaboration_fit", "multi_turn_stability"
            )) else 0.0,
        },
    }

    plan.update({
        "pressure_targets": pressure_targets,
        "behavior_modes": {k: float(round(v, 4)) for k, v in behavior_modes.items() if v > 0.0},
        "constraint_axes": {k: float(round(v, 4)) for k, v in axis_scores.items()},
        "avatar_overrides": avatar_overrides,
        "study_topics": [dim.replace("_", " ") for dim, _ in ranked_targets[:2]],
        "episodes_bonus": 1 if pressure_strength > 0.42 else 0,
        "turns_bonus": min(2, turns_bonus),
        "queue_repeats": min(4, max(1, len(ranked_targets))),
        "rationale": rationale[:8],
    })
    return plan


def build_avatar_spec_from_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    phase = str(plan.get("phase", "train") or "train")
    return {
        "avatar_id": f"resp_pressure_{phase}_{int(time.time())}",
        "pressure_targets": dict(plan.get("pressure_targets", {}) or {}),
        "behavior_modes": dict(plan.get("behavior_modes", {}) or {}),
        "constraint_axes": dict(plan.get("constraint_axes", {}) or {}),
        "avatar_overrides": dict(plan.get("avatar_overrides", {}) or {}),
        "source_episode_ids": [f"response_pressure:{phase}"],
        "source_leverage_points": dict(plan.get("pressure_targets", {}) or {}),
    }


def queue_plan_on_session(
    session: Any,
    plan: Dict[str, Any],
    episode_budget: int = 1,
) -> int:
    if session is None or not plan or not plan.get("pressure_targets"):
        return 0

    queue_fn = getattr(session, "queue_avatar_specs", None)
    if not callable(queue_fn):
        return 0

    spec = build_avatar_spec_from_plan(plan)
    repeats = min(
        int(plan.get("queue_repeats", 1) or 1),
        max(1, int(episode_budget) or 1),
    )
    return int(queue_fn([spec] * repeats) or 0)

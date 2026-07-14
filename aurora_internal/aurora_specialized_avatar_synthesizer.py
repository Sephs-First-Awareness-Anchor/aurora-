#!/usr/bin/env python3
"""
AURORA SPECIALIZED AVATAR SYNTHESIZER
==========================================
Generates pressure-specialized avatar configurations from repeated
relational weakness patterns detected by the slip profiler.

Key principle: stress ROOT DEFICITS, not surface symptoms.
  If contradiction failure is downstream of weak context carryover,
  the avatar stresses cross-turn memory pressure.
  If ambiguity failure is downstream of poor uncertainty signaling,
  the avatar punishes premature commitment and rewards clarification.

Integration:
  - Reads: EpisodeRubricSummary (from slip profiler)
  - Reads: RubricInfluenceAssessment (from influence graph)
  - Produces: PressureSpecializedAvatarSpec
  - Feeds into: SimulationSession._create_avatar_pool / SimulatedAvatar

Authors: Sunni (Sir) Morningstar and Cael Devo
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from aurora_internal.aurora_conversation_rubric_engine import RUBRIC_DIMENSIONS
from aurora_internal.aurora_directed_training_corpus import (
    get_directed_training_corpus_bridge,
)
from aurora_internal.aurora_episode_slip_profiler import EpisodeRubricSummary
from aurora_internal.aurora_rubric_influence_graph import (
    RubricInfluenceGraph,
    RubricInfluenceAssessment,
)


_DIRECTED_TRAINING = get_directed_training_corpus_bridge()


# ============================================================================
# OUTPUT DATACLASS
# ============================================================================

@dataclass
class PressureSpecializedAvatarSpec:
    """
    A synthesized avatar configuration designed to stress specific
    root deficits rather than surface symptoms.

    pressure_targets: rubric dimensions this avatar pressures (dim -> intensity)
    behavior_modes: behavioral strategies the avatar uses (mode -> weight)
    escalation_profile: how pressure escalates over turns (metric -> rate)
    source_leverage_points: which leverage candidates drove this spec
    """
    avatar_id: str
    pressure_targets: Dict[str, float] = field(default_factory=dict)
    behavior_modes: Dict[str, float] = field(default_factory=dict)
    escalation_profile: Dict[str, float] = field(default_factory=dict)
    source_leverage_points: Dict[str, float] = field(default_factory=dict)
    source_episode_ids: List[str] = field(default_factory=list)
    source_corpus_refs: List[str] = field(default_factory=list)
    constraint_axes: Dict[str, float] = field(default_factory=dict)
    prompt_candidates: List[str] = field(default_factory=list)
    followup_candidates: List[str] = field(default_factory=list)
    difficulty_floor: float = 0.4
    patience_modifier: float = 1.0
    adaptive_hardness: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "avatar_id": self.avatar_id,
            "pressure_targets": dict(self.pressure_targets),
            "behavior_modes": dict(self.behavior_modes),
            "escalation_profile": dict(self.escalation_profile),
            "source_leverage_points": dict(self.source_leverage_points),
            "source_episode_ids": list(self.source_episode_ids),
            "source_corpus_refs": list(self.source_corpus_refs),
            "constraint_axes": dict(self.constraint_axes),
            "prompt_candidates": list(self.prompt_candidates),
            "followup_candidates": list(self.followup_candidates),
            "difficulty_floor": self.difficulty_floor,
            "patience_modifier": self.patience_modifier,
            "adaptive_hardness": self.adaptive_hardness,
            "timestamp": self.timestamp,
        }

    def to_avatar_overrides(self) -> Dict[str, Any]:
        """
        Convert this spec into override values for SimulatedAvatar fields.
        Maps rubric pressure targets to avatar weight/parameter adjustments.
        """
        overrides: Dict[str, Any] = {}

        # Map rubric pressure targets to avatar reward weight biases
        weight_adjustments: Dict[str, float] = {
            "clarity": 0.0,
            "relevance": 0.0,
            "tone_match": 0.0,
            "vocabulary_match": 0.0,
            "engagement": 0.0,
        }

        for dim, intensity in self.pressure_targets.items():
            mapped = _DIMENSION_TO_AVATAR_WEIGHTS.get(dim, {})
            for weight_key, factor in mapped.items():
                weight_adjustments[weight_key] += intensity * factor

        # Normalize: shift toward pressure targets without going negative
        total = sum(abs(v) for v in weight_adjustments.values())
        if total > 0:
            for k in weight_adjustments:
                weight_adjustments[k] /= total
            overrides["weight_adjustments"] = weight_adjustments

        # Patience: lower patience for dimensions that need fast feedback
        overrides["patience_modifier"] = self.patience_modifier

        # Difficulty floor: minimum fitness the avatar demands
        overrides["min_acceptable_fitness"] = self.difficulty_floor

        # Escalation: how much difficulty_multiplier increases per turn
        overrides["escalation_rate"] = self.escalation_profile.get(
            "difficulty_per_turn", 0.05
        )
        overrides["specialization_hardness"] = _clamp(
            float(self.adaptive_hardness), 0.0, 1.0
        )

        return overrides


# ============================================================================
# DIMENSION -> AVATAR WEIGHT MAPPING
# ============================================================================
# Maps rubric dimensions to which avatar reward weights they stress.
# These are influence coefficients, not absolute values.

_DIMENSION_TO_AVATAR_WEIGHTS: Dict[str, Dict[str, float]] = {
    "coherence_maintenance": {
        "clarity": 0.6,
        "relevance": 0.3,
    },
    "context_carryover": {
        "relevance": 0.7,
        "clarity": 0.2,
    },
    "ambiguity_handling": {
        "engagement": 0.5,
        "clarity": 0.3,
    },
    "contradiction_handling": {
        "clarity": 0.4,
        "relevance": 0.4,
    },
    "implied_intent_inference": {
        "relevance": 0.6,
        "engagement": 0.3,
    },
    "misunderstanding_repair": {
        "clarity": 0.5,
        "engagement": 0.3,
    },
    "uncertainty_signaling": {
        "tone_match": 0.4,
        "clarity": 0.3,
    },
    "boundary_calibration": {
        "tone_match": 0.5,
        "engagement": 0.3,
    },
    "framing_selection": {
        "vocabulary_match": 0.4,
        "clarity": 0.4,
    },
    "emotional_calibration": {
        "tone_match": 0.6,
        "engagement": 0.2,
    },
    "semantic_precision": {
        "vocabulary_match": 0.5,
        "clarity": 0.4,
    },
    "adaptive_strategy_selection": {
        "engagement": 0.4,
        "relevance": 0.3,
    },
    "compression_elaboration_fit": {
        "engagement": 0.3,
        "vocabulary_match": 0.3,
        "clarity": 0.2,
    },
    "perspective_integration": {
        "relevance": 0.4,
        "tone_match": 0.3,
    },
    "multi_turn_stability": {
        "relevance": 0.4,
        "clarity": 0.3,
        "engagement": 0.2,
    },
}


# ============================================================================
# DIMENSION -> BEHAVIOR MODE MAPPING
# ============================================================================
# Maps rubric dimensions to avatar behavioral strategies.
# These define HOW the avatar creates pressure, not just what it rewards.

_DIMENSION_TO_BEHAVIOR: Dict[str, Dict[str, float]] = {
    "context_carryover": {
        "reference_earlier_topics": 0.8,
        "test_cross_turn_memory": 0.7,
        "introduce_callbacks": 0.6,
    },
    "ambiguity_handling": {
        "use_vague_phrasing": 0.8,
        "give_incomplete_context": 0.6,
        "test_clarification_seeking": 0.7,
    },
    "contradiction_handling": {
        "contradict_earlier_statements": 0.8,
        "present_conflicting_evidence": 0.7,
        "test_nuanced_synthesis": 0.5,
    },
    "implied_intent_inference": {
        "use_indirect_requests": 0.8,
        "hide_real_intent": 0.6,
        "test_subtext_reading": 0.7,
    },
    "misunderstanding_repair": {
        "feign_confusion": 0.7,
        "misinterpret_deliberately": 0.6,
        "test_repair_initiation": 0.8,
    },
    "uncertainty_signaling": {
        "ask_about_confidence": 0.7,
        "present_uncertain_scenarios": 0.8,
        "punish_overcommitment": 0.6,
    },
    "boundary_calibration": {
        "vary_engagement_level": 0.7,
        "test_response_scaling": 0.6,
        "signal_overwhelm": 0.5,
    },
    "framing_selection": {
        "switch_registers": 0.7,
        "demand_reframing": 0.6,
        "test_perspective_shifts": 0.5,
    },
    "emotional_calibration": {
        "express_strong_emotions": 0.7,
        "shift_emotional_tone": 0.8,
        "test_empathic_tracking": 0.6,
    },
    "semantic_precision": {
        "use_precise_terminology": 0.6,
        "test_word_choice_sensitivity": 0.7,
        "punish_vagueness": 0.5,
    },
    "adaptive_strategy_selection": {
        "vary_interaction_style": 0.8,
        "reward_strategy_shifts": 0.6,
        "punish_monotony": 0.5,
    },
    "coherence_maintenance": {
        "introduce_topic_shifts": 0.7,
        "test_thread_continuity": 0.6,
        "punish_non_sequiturs": 0.5,
    },
    "compression_elaboration_fit": {
        "vary_message_complexity": 0.7,
        "test_response_length_matching": 0.6,
        "alternate_terse_and_elaborate": 0.5,
    },
    "perspective_integration": {
        "present_multiple_viewpoints": 0.8,
        "demand_synthesis": 0.6,
        "test_perspective_acknowledgment": 0.7,
    },
    "multi_turn_stability": {
        "extend_conversation_length": 0.7,
        "test_late_turn_quality": 0.6,
        "monitor_degradation": 0.8,
    },
}


def behavior_modes_for_dimension(dimension: str) -> Dict[str, float]:
    """Public accessor for _DIMENSION_TO_BEHAVIOR -- the dimension-specific
    avatar pressure behaviors (e.g. context_carryover's
    test_cross_turn_memory) that make a specialized episode actually
    stress the targeted rubric dimension, instead of just labeling it.
    Callers outside this module (e.g. aurora_classroom.py's direct
    lesson-spec queuing, which doesn't route through
    synthesize_from_summary()) should use this rather than reaching into
    the private mapping directly. Unknown dimension -> {} (SimulationEngine
    already treats an empty behavior_modes as "no extra pressure", so this
    degrades safely)."""
    return dict(_DIMENSION_TO_BEHAVIOR.get(str(dimension or ""), {}))


# ============================================================================
# DIMENSION -> CONSTRAINT AXIS MAPPING
# ============================================================================
# Trace every pressure profile back to Aurora's 5-axis manifold:
#   X (expression), T (temporal), N (noise/boundary), B (branching), A (agency)

_DIMENSION_TO_AXIS: Dict[str, str] = {
    "coherence_maintenance": "T",
    "context_carryover": "T",
    "ambiguity_handling": "B",
    "contradiction_handling": "B",
    "implied_intent_inference": "A",
    "misunderstanding_repair": "A",
    "uncertainty_signaling": "N",
    "boundary_calibration": "N",
    "framing_selection": "X",
    "emotional_calibration": "X",
    "semantic_precision": "X",
    "adaptive_strategy_selection": "A",
    "compression_elaboration_fit": "N",
    "perspective_integration": "B",
    "multi_turn_stability": "T",
}


# ============================================================================
# ESCALATION PROFILES
# ============================================================================

_ESCALATION_PROFILES: Dict[str, Dict[str, float]] = {
    "gentle": {
        "difficulty_per_turn": 0.03,
        "patience_decay": 0.02,
        "fitness_floor_rise": 0.01,
    },
    "moderate": {
        "difficulty_per_turn": 0.06,
        "patience_decay": 0.04,
        "fitness_floor_rise": 0.02,
    },
    "aggressive": {
        "difficulty_per_turn": 0.10,
        "patience_decay": 0.06,
        "fitness_floor_rise": 0.03,
    },
}


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _clamp_signed(v: float, lim: float) -> float:
    return max(-abs(lim), min(abs(lim), v))


def _generate_id(prefix: str) -> str:
    raw = f"{prefix}_{time.time()}_{random.random()}"
    return f"{prefix}_{hashlib.md5(raw.encode()).hexdigest()[:12]}"


# ============================================================================
# MAIN SYNTHESIZER
# ============================================================================

class SpecializedAvatarSynthesizer:
    """
    Generates pressure-specialized avatar configurations from repeated
    weakness patterns detected across dream episodes.

    Key design: avatars stress ROOT DEFICITS (leverage candidates from
    the influence graph), not surface symptoms.
    """

    _STATE_VERSION = 1

    def __init__(self, storage_dir: Optional[str] = None):
        self.influence_graph = RubricInfluenceGraph()
        self._specs_generated: int = 0
        self.storage_dir = storage_dir
        self._policy_path: Optional[str] = None
        self._adaptive_policy: Dict[str, Any] = self._default_policy()
        if self.storage_dir:
            os.makedirs(self.storage_dir, exist_ok=True)
            self._policy_path = os.path.join(
                self.storage_dir, "avatar_adaptive_policy.json"
            )
            self._load_policy()

    def _default_policy(self) -> Dict[str, Any]:
        return {
            "version": self._STATE_VERSION,
            "samples": 0,
            "global": {
                "pressure_gain_bias": 0.0,
                "difficulty_bias": 0.0,
                "escalation_bias": 0.0,
                "patience_bias": 0.0,
                "hardness_bias": 0.0,
                "samples": 0,
            },
            "axis": {
                axis: {
                    "pressure_gain": 1.0,
                    "difficulty_bias": 0.0,
                    "escalation_bias": 0.0,
                    "patience_bias": 0.0,
                    "hardness_bias": 0.0,
                    "samples": 0,
                }
                for axis in ("X", "T", "N", "B", "A")
            },
            "dimensions": {
                dim: {
                    "pressure_gain": 1.0,
                    "difficulty_bias": 0.0,
                    "escalation_bias": 0.0,
                    "patience_bias": 0.0,
                    "hardness_bias": 0.0,
                    "samples": 0,
                }
                for dim in RUBRIC_DIMENSIONS
            },
            "last_episode_id": "",
            "last_update_ts": 0.0,
        }

    def _load_policy(self) -> None:
        if not self._policy_path or not os.path.exists(self._policy_path):
            return
        try:
            with open(self._policy_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if not isinstance(raw, dict):
                return
            base = self._default_policy()
            # Keep structure stable even if prior versions are missing keys.
            gl = dict(raw.get("global", {}) or {})
            ax = dict(raw.get("axis", {}) or {})
            dm = dict(raw.get("dimensions", {}) or {})
            base["samples"] = int(raw.get("samples", 0) or 0)
            base["last_episode_id"] = str(raw.get("last_episode_id", "") or "")
            base["last_update_ts"] = float(raw.get("last_update_ts", 0.0) or 0.0)
            for k in base["global"]:
                base["global"][k] = float(gl.get(k, base["global"][k]) or 0.0)
            for axis in base["axis"]:
                rec = dict(ax.get(axis, {}) or {})
                for k in base["axis"][axis]:
                    base["axis"][axis][k] = float(
                        rec.get(k, base["axis"][axis][k]) or 0.0
                    )
            for dim in base["dimensions"]:
                rec = dict(dm.get(dim, {}) or {})
                for k in base["dimensions"][dim]:
                    base["dimensions"][dim][k] = float(
                        rec.get(k, base["dimensions"][dim][k]) or 0.0
                    )
            # Re-clamp loaded values.
            self._adaptive_policy = self._normalize_policy(base)
        except Exception:
            # Corrupt policy should not break run; start fresh.
            self._adaptive_policy = self._default_policy()

    def _save_policy(self) -> None:
        if not self._policy_path:
            return
        try:
            payload = self._normalize_policy(dict(self._adaptive_policy))
            with open(self._policy_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception:
            pass

    def _normalize_policy(self, state: Dict[str, Any]) -> Dict[str, Any]:
        rec = dict(state or {})
        rec["version"] = self._STATE_VERSION
        rec["samples"] = int(rec.get("samples", 0) or 0)
        rec["last_episode_id"] = str(rec.get("last_episode_id", "") or "")
        rec["last_update_ts"] = float(rec.get("last_update_ts", 0.0) or 0.0)

        gl = dict(rec.get("global", {}) or {})
        rec["global"] = {
            "pressure_gain_bias": _clamp_signed(float(gl.get("pressure_gain_bias", 0.0) or 0.0), 0.40),
            "difficulty_bias": _clamp_signed(float(gl.get("difficulty_bias", 0.0) or 0.0), 0.35),
            "escalation_bias": _clamp_signed(float(gl.get("escalation_bias", 0.0) or 0.0), 0.30),
            "patience_bias": _clamp_signed(float(gl.get("patience_bias", 0.0) or 0.0), 0.30),
            "hardness_bias": _clamp_signed(float(gl.get("hardness_bias", 0.0) or 0.0), 0.35),
            "samples": int(gl.get("samples", 0) or 0),
        }

        axis_out: Dict[str, Dict[str, float]] = {}
        ax = dict(rec.get("axis", {}) or {})
        for axis in ("X", "T", "N", "B", "A"):
            raw = dict(ax.get(axis, {}) or {})
            axis_out[axis] = {
                "pressure_gain": _clamp(float(raw.get("pressure_gain", 1.0) or 1.0), 0.70, 1.95),
                "difficulty_bias": _clamp_signed(float(raw.get("difficulty_bias", 0.0) or 0.0), 0.35),
                "escalation_bias": _clamp_signed(float(raw.get("escalation_bias", 0.0) or 0.0), 0.30),
                "patience_bias": _clamp_signed(float(raw.get("patience_bias", 0.0) or 0.0), 0.30),
                "hardness_bias": _clamp_signed(float(raw.get("hardness_bias", 0.0) or 0.0), 0.35),
                "samples": int(raw.get("samples", 0) or 0),
            }
        rec["axis"] = axis_out

        dims_out: Dict[str, Dict[str, float]] = {}
        dm = dict(rec.get("dimensions", {}) or {})
        for dim in RUBRIC_DIMENSIONS:
            raw = dict(dm.get(dim, {}) or {})
            dims_out[dim] = {
                "pressure_gain": _clamp(float(raw.get("pressure_gain", 1.0) or 1.0), 0.70, 1.95),
                "difficulty_bias": _clamp_signed(float(raw.get("difficulty_bias", 0.0) or 0.0), 0.35),
                "escalation_bias": _clamp_signed(float(raw.get("escalation_bias", 0.0) or 0.0), 0.30),
                "patience_bias": _clamp_signed(float(raw.get("patience_bias", 0.0) or 0.0), 0.30),
                "hardness_bias": _clamp_signed(float(raw.get("hardness_bias", 0.0) or 0.0), 0.35),
                "samples": int(raw.get("samples", 0) or 0),
            }
        rec["dimensions"] = dims_out
        return rec

    def register_episode_feedback(
        self,
        summary: EpisodeRubricSummary,
        previous_summary: Optional[EpisodeRubricSummary] = None,
        applied_pressure_targets: Optional[Dict[str, float]] = None,
        episode_fitness: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Update the adaptive pressure policy from real dream outcomes.

        This is Aurora-owned pressure shaping:
        dream outcomes shift difficulty/escalation/patience gradients,
        and the policy persists for future episodes.
        """
        if not summary.mean_scores:
            return {"updated": False, "reason": "no_mean_scores"}

        policy = self._normalize_policy(self._adaptive_policy)
        g = policy["global"]
        axis_state = policy["axis"]
        dim_state = policy["dimensions"]
        targets = dict(applied_pressure_targets or {})

        prev_mean = 0.5
        prev_fitness = float(summary.episode_fitness)
        if previous_summary and previous_summary.mean_scores:
            prev_mean = sum(previous_summary.mean_scores.values()) / max(
                len(previous_summary.mean_scores), 1
            )
            prev_fitness = float(previous_summary.episode_fitness)
        curr_mean = sum(summary.mean_scores.values()) / max(len(summary.mean_scores), 1)
        curr_fitness = float(summary.episode_fitness if episode_fitness is None else episode_fitness)

        mean_delta = curr_mean - prev_mean
        fitness_delta = curr_fitness - prev_fitness

        for dim in RUBRIC_DIMENSIONS:
            ds = dim_state.get(dim, {})
            curr = float(summary.mean_scores.get(dim, 0.5) or 0.5)
            prev = curr
            if previous_summary and previous_summary.mean_scores:
                prev = float(previous_summary.mean_scores.get(dim, curr) or curr)
            delta = curr - prev
            deficit = max(0.0, 0.58 - curr)
            pressure_w = _clamp(float(targets.get(dim, 0.0) or 0.0), 0.0, 1.0)
            step = 0.03 + (0.10 * deficit) + (0.05 * pressure_w)

            if (delta < -0.015) or (deficit > 0.08 and delta < 0.005):
                ds["pressure_gain"] = _clamp(float(ds.get("pressure_gain", 1.0)) + (step * 0.55), 0.70, 1.95)
                ds["difficulty_bias"] = _clamp_signed(float(ds.get("difficulty_bias", 0.0)) + (step * 0.25), 0.35)
                ds["escalation_bias"] = _clamp_signed(float(ds.get("escalation_bias", 0.0)) + (step * 0.22), 0.30)
                ds["patience_bias"] = _clamp_signed(float(ds.get("patience_bias", 0.0)) - (step * 0.20), 0.30)
                ds["hardness_bias"] = _clamp_signed(float(ds.get("hardness_bias", 0.0)) + (step * 0.28), 0.35)
            elif delta > 0.03 and curr > 0.45:
                ds["pressure_gain"] = _clamp(float(ds.get("pressure_gain", 1.0)) - (step * 0.35), 0.70, 1.95)
                ds["difficulty_bias"] = _clamp_signed(float(ds.get("difficulty_bias", 0.0)) - (step * 0.20), 0.35)
                ds["escalation_bias"] = _clamp_signed(float(ds.get("escalation_bias", 0.0)) - (step * 0.18), 0.30)
                ds["patience_bias"] = _clamp_signed(float(ds.get("patience_bias", 0.0)) + (step * 0.20), 0.30)
                ds["hardness_bias"] = _clamp_signed(float(ds.get("hardness_bias", 0.0)) - (step * 0.22), 0.35)
            else:
                # Slow relaxation toward neutral when signals are mixed.
                ds["pressure_gain"] = _clamp((0.975 * float(ds.get("pressure_gain", 1.0))) + 0.025, 0.70, 1.95)
                ds["difficulty_bias"] = _clamp_signed(0.975 * float(ds.get("difficulty_bias", 0.0)), 0.35)
                ds["escalation_bias"] = _clamp_signed(0.975 * float(ds.get("escalation_bias", 0.0)), 0.30)
                ds["patience_bias"] = _clamp_signed(0.975 * float(ds.get("patience_bias", 0.0)), 0.30)
                ds["hardness_bias"] = _clamp_signed(0.975 * float(ds.get("hardness_bias", 0.0)), 0.35)

            ds["samples"] = int(ds.get("samples", 0) or 0) + 1
            dim_state[dim] = ds

        # Axis-level policy is a smoothed view over dimensions.
        for axis in ("X", "T", "N", "B", "A"):
            axis_dims = [d for d, a in _DIMENSION_TO_AXIS.items() if a == axis]
            if not axis_dims:
                continue
            rec = axis_state.get(axis, {})
            count = float(len(axis_dims))
            avg_gain = sum(float(dim_state[d]["pressure_gain"]) for d in axis_dims) / count
            avg_diff = sum(float(dim_state[d]["difficulty_bias"]) for d in axis_dims) / count
            avg_esc = sum(float(dim_state[d]["escalation_bias"]) for d in axis_dims) / count
            avg_pat = sum(float(dim_state[d]["patience_bias"]) for d in axis_dims) / count
            avg_hard = sum(float(dim_state[d]["hardness_bias"]) for d in axis_dims) / count
            rec["pressure_gain"] = _clamp((0.90 * float(rec.get("pressure_gain", 1.0))) + (0.10 * avg_gain), 0.70, 1.95)
            rec["difficulty_bias"] = _clamp_signed((0.90 * float(rec.get("difficulty_bias", 0.0))) + (0.10 * avg_diff), 0.35)
            rec["escalation_bias"] = _clamp_signed((0.90 * float(rec.get("escalation_bias", 0.0))) + (0.10 * avg_esc), 0.30)
            rec["patience_bias"] = _clamp_signed((0.90 * float(rec.get("patience_bias", 0.0))) + (0.10 * avg_pat), 0.30)
            rec["hardness_bias"] = _clamp_signed((0.90 * float(rec.get("hardness_bias", 0.0))) + (0.10 * avg_hard), 0.35)
            rec["samples"] = int(rec.get("samples", 0) or 0) + 1
            axis_state[axis] = rec

        # Global trend update.
        trend = (0.65 * mean_delta) + (0.35 * fitness_delta)
        pressure_load = _clamp(
            sum(float(v) for v in targets.values()) / max(len(targets), 1), 0.0, 1.0
        ) if targets else 0.0
        if trend < -0.010:
            g["pressure_gain_bias"] = _clamp_signed(float(g.get("pressure_gain_bias", 0.0)) + 0.020 + (0.012 * pressure_load), 0.40)
            g["difficulty_bias"] = _clamp_signed(float(g.get("difficulty_bias", 0.0)) + 0.014, 0.35)
            g["escalation_bias"] = _clamp_signed(float(g.get("escalation_bias", 0.0)) + 0.012, 0.30)
            g["patience_bias"] = _clamp_signed(float(g.get("patience_bias", 0.0)) - 0.011, 0.30)
            g["hardness_bias"] = _clamp_signed(float(g.get("hardness_bias", 0.0)) + 0.016, 0.35)
        elif trend > 0.020:
            g["pressure_gain_bias"] = _clamp_signed(float(g.get("pressure_gain_bias", 0.0)) - 0.014, 0.40)
            g["difficulty_bias"] = _clamp_signed(float(g.get("difficulty_bias", 0.0)) - 0.010, 0.35)
            g["escalation_bias"] = _clamp_signed(float(g.get("escalation_bias", 0.0)) - 0.009, 0.30)
            g["patience_bias"] = _clamp_signed(float(g.get("patience_bias", 0.0)) + 0.010, 0.30)
            g["hardness_bias"] = _clamp_signed(float(g.get("hardness_bias", 0.0)) - 0.011, 0.35)
        else:
            # Neutral regime: decay toward baseline.
            g["pressure_gain_bias"] = _clamp_signed(float(g.get("pressure_gain_bias", 0.0)) * 0.98, 0.40)
            g["difficulty_bias"] = _clamp_signed(float(g.get("difficulty_bias", 0.0)) * 0.98, 0.35)
            g["escalation_bias"] = _clamp_signed(float(g.get("escalation_bias", 0.0)) * 0.98, 0.30)
            g["patience_bias"] = _clamp_signed(float(g.get("patience_bias", 0.0)) * 0.98, 0.30)
            g["hardness_bias"] = _clamp_signed(float(g.get("hardness_bias", 0.0)) * 0.98, 0.35)

        g["samples"] = int(g.get("samples", 0) or 0) + 1
        policy["samples"] = int(policy.get("samples", 0) or 0) + 1
        policy["last_episode_id"] = str(summary.episode_id or "")
        policy["last_update_ts"] = float(time.time())

        self._adaptive_policy = self._normalize_policy(policy)
        self._save_policy()

        weakest = sorted(
            ((dim, float(summary.mean_scores.get(dim, 0.5) or 0.5)) for dim in RUBRIC_DIMENSIONS),
            key=lambda kv: kv[1],
        )[:5]
        return {
            "updated": True,
            "episode_id": summary.episode_id,
            "mean_delta": mean_delta,
            "fitness_delta": fitness_delta,
            "pressure_targets_seen": len(targets),
            "weakest_dimensions": [d for d, _ in weakest],
        }

    def _constraint_axis_trace(
        self,
        pressure_targets: Dict[str, float],
    ) -> Dict[str, float]:
        axis_scores: Dict[str, float] = {axis: 0.0 for axis in ("X", "T", "N", "B", "A")}
        for dim, intensity in pressure_targets.items():
            axis = _DIMENSION_TO_AXIS.get(dim, "X")
            axis_scores[axis] += _clamp(float(intensity), 0.0, 1.0)
        total = sum(axis_scores.values())
        if total <= 0.0:
            return {}
        for axis in list(axis_scores.keys()):
            axis_scores[axis] = _clamp(axis_scores[axis] / total, 0.0, 1.0)
        return axis_scores

    def _apply_adaptive_policy(
        self,
        leverage_dim: str,
        pressure_targets: Dict[str, float],
        escalation_profile: Dict[str, float],
        patience_modifier: float,
        difficulty_floor: float,
    ) -> Tuple[Dict[str, float], Dict[str, float], float, float, float, Dict[str, float]]:
        policy = self._normalize_policy(self._adaptive_policy)
        g = dict(policy.get("global", {}) or {})
        dims = dict(policy.get("dimensions", {}) or {})
        axes = dict(policy.get("axis", {}) or {})

        leverage_state = dict(dims.get(leverage_dim, {}) or {})
        leverage_axis = _DIMENSION_TO_AXIS.get(leverage_dim, "X")
        axis_state = dict(axes.get(leverage_axis, {}) or {})

        adjusted_targets: Dict[str, float] = {}
        for dim, base in pressure_targets.items():
            ds = dict(dims.get(dim, {}) or {})
            axis = _DIMENSION_TO_AXIS.get(dim, "X")
            ax = dict(axes.get(axis, {}) or {})
            gain = (
                1.0
                + (0.34 * (float(ds.get("pressure_gain", 1.0)) - 1.0))
                + (0.20 * (float(ax.get("pressure_gain", 1.0)) - 1.0))
                + (0.25 * float(g.get("pressure_gain_bias", 0.0) or 0.0))
            )
            adjusted_targets[dim] = _clamp(float(base) * gain, 0.08, 0.95)

        adjusted_escalation: Dict[str, float] = dict(escalation_profile or {})
        esc_shift = (
            float(g.get("escalation_bias", 0.0) or 0.0)
            + float(leverage_state.get("escalation_bias", 0.0) or 0.0)
            + (0.5 * float(axis_state.get("escalation_bias", 0.0) or 0.0))
        )
        adjusted_escalation["difficulty_per_turn"] = _clamp(
            float(adjusted_escalation.get("difficulty_per_turn", 0.05) or 0.05)
            + (0.20 * esc_shift),
            0.02,
            0.20,
        )
        adjusted_escalation["patience_decay"] = _clamp(
            float(adjusted_escalation.get("patience_decay", 0.03) or 0.03)
            + (0.15 * esc_shift),
            0.01,
            0.15,
        )
        adjusted_escalation["fitness_floor_rise"] = _clamp(
            float(adjusted_escalation.get("fitness_floor_rise", 0.01) or 0.01)
            + (0.09 * esc_shift),
            0.0,
            0.08,
        )

        diff_shift = (
            float(g.get("difficulty_bias", 0.0) or 0.0)
            + float(leverage_state.get("difficulty_bias", 0.0) or 0.0)
            + (0.5 * float(axis_state.get("difficulty_bias", 0.0) or 0.0))
        )
        adjusted_difficulty = _clamp(float(difficulty_floor) + diff_shift, 0.25, 0.90)

        pat_shift = (
            float(g.get("patience_bias", 0.0) or 0.0)
            + float(leverage_state.get("patience_bias", 0.0) or 0.0)
            + (0.5 * float(axis_state.get("patience_bias", 0.0) or 0.0))
        )
        adjusted_patience = _clamp(float(patience_modifier) + pat_shift, 0.15, 1.10)

        hard_shift = (
            float(g.get("hardness_bias", 0.0) or 0.0)
            + float(leverage_state.get("hardness_bias", 0.0) or 0.0)
            + (0.5 * float(axis_state.get("hardness_bias", 0.0) or 0.0))
        )
        lead_intensity = _clamp(float(adjusted_targets.get(leverage_dim, 0.0) or 0.0), 0.0, 1.0)
        adaptive_hardness = _clamp(0.22 + (0.45 * lead_intensity) + hard_shift, 0.0, 1.0)

        constraint_axes = self._constraint_axis_trace(adjusted_targets)

        return (
            adjusted_targets,
            adjusted_escalation,
            adjusted_patience,
            adjusted_difficulty,
            adaptive_hardness,
            constraint_axes,
        )

    def policy_snapshot(self) -> Dict[str, Any]:
        """Expose current adaptive pressure policy for status/diagnostics."""
        policy = self._normalize_policy(self._adaptive_policy)
        dims = dict(policy.get("dimensions", {}) or {})
        ranked = sorted(
            dims.items(),
            key=lambda kv: float((kv[1] or {}).get("pressure_gain", 1.0) or 1.0),
            reverse=True,
        )
        top = [
            {
                "dimension": dim,
                "pressure_gain": float(rec.get("pressure_gain", 1.0) or 1.0),
                "hardness_bias": float(rec.get("hardness_bias", 0.0) or 0.0),
            }
            for dim, rec in ranked[:5]
        ]
        return {
            "samples": int(policy.get("samples", 0) or 0),
            "last_episode_id": str(policy.get("last_episode_id", "") or ""),
            "last_update_ts": float(policy.get("last_update_ts", 0.0) or 0.0),
            "global": dict(policy.get("global", {}) or {}),
            "axis": dict(policy.get("axis", {}) or {}),
            "top_pressure_dimensions": top,
        }

    def synthesize_from_summary(
        self,
        summary: EpisodeRubricSummary,
        max_specs: int = 3,
    ) -> List[PressureSpecializedAvatarSpec]:
        """
        Generate avatar specs from a single episode's diagnostic summary.

        Creates up to max_specs avatars, each targeting different leverage
        candidates from the summary's influence analysis.
        """
        if not summary.is_significant():
            return []

        leverage = summary.leverage_candidates
        if not leverage:
            return []

        # Sort leverage candidates by score (highest first)
        ranked = sorted(leverage.items(), key=lambda kv: kv[1], reverse=True)

        specs: List[PressureSpecializedAvatarSpec] = []
        for i, (dim, lev_score) in enumerate(ranked[:max_specs]):
            spec = self._build_spec_for_leverage(
                leverage_dim=dim,
                leverage_score=lev_score,
                summary=summary,
                spec_index=i,
            )
            specs.append(spec)
            self._specs_generated += 1

        return specs

    def synthesize_from_accumulation(
        self,
        accumulative_analysis: Dict[str, Any],
        episode_ids: Optional[List[str]] = None,
        max_specs: int = 3,
    ) -> List[PressureSpecializedAvatarSpec]:
        """
        Generate avatar specs from accumulated cross-episode analysis.

        This is for PERSISTENT weaknesses that recur across multiple episodes.
        These avatars are more targeted and aggressive.
        """
        persistent = accumulative_analysis.get("persistent_weaknesses", {})
        leverage = accumulative_analysis.get("leverage_candidates", {})

        if not persistent:
            return []

        # If no leverage candidates from accumulation, re-derive
        if not leverage:
            assessment = self.influence_graph.analyze(persistent)
            leverage = assessment.leverage_candidates

        if not leverage:
            return []

        ranked = sorted(leverage.items(), key=lambda kv: kv[1], reverse=True)

        specs: List[PressureSpecializedAvatarSpec] = []
        for i, (dim, lev_score) in enumerate(ranked[:max_specs]):
            spec = self._build_persistent_spec(
                leverage_dim=dim,
                leverage_score=lev_score,
                persistent_weaknesses=persistent,
                episode_ids=episode_ids or [],
                spec_index=i,
            )
            specs.append(spec)
            self._specs_generated += 1

        return specs

    def _build_spec_for_leverage(
        self,
        leverage_dim: str,
        leverage_score: float,
        summary: EpisodeRubricSummary,
        spec_index: int,
    ) -> PressureSpecializedAvatarSpec:
        """Build an avatar spec targeting a specific leverage dimension."""

        # Primary pressure target is the leverage dimension itself
        pressure_targets: Dict[str, float] = {leverage_dim: 0.8}

        # Also target downstream dimensions (symptoms) at lower intensity
        downstream = self.influence_graph.trace_downstream(leverage_dim)
        for ds_dim, ds_weight in downstream[:3]:
            if ds_dim in summary.secondary_deficits:
                pressure_targets[ds_dim] = _clamp(ds_weight * 0.5, 0.1, 0.6)

        # Behavior modes from the leverage dimension
        behavior_modes = dict(_DIMENSION_TO_BEHAVIOR.get(leverage_dim, {}))

        # Add secondary behaviors from downstream targets
        for ds_dim, _ in downstream[:2]:
            ds_behaviors = _DIMENSION_TO_BEHAVIOR.get(ds_dim, {})
            for bmode, bweight in ds_behaviors.items():
                if bmode not in behavior_modes:
                    behavior_modes[bmode] = _clamp(bweight * 0.4)

        # Escalation profile based on deficit severity
        deficit_score = summary.primary_deficits.get(leverage_dim, 0.5)
        if deficit_score < 0.25:
            escalation = dict(_ESCALATION_PROFILES["aggressive"])
        elif deficit_score < 0.35:
            escalation = dict(_ESCALATION_PROFILES["moderate"])
        else:
            escalation = dict(_ESCALATION_PROFILES["gentle"])

        # Patience: lower for severe deficits (force quicker feedback)
        patience = _clamp(0.3 + deficit_score, 0.2, 0.8)

        # Difficulty floor: higher for persistent/severe weaknesses
        difficulty_floor = _clamp(0.3 + leverage_score * 0.2, 0.3, 0.7)
        (
            pressure_targets,
            escalation,
            patience,
            difficulty_floor,
            adaptive_hardness,
            constraint_axes,
        ) = self._apply_adaptive_policy(
            leverage_dim=leverage_dim,
            pressure_targets=pressure_targets,
            escalation_profile=escalation,
            patience_modifier=patience,
            difficulty_floor=difficulty_floor,
        )
        corpus_pack = _DIRECTED_TRAINING.prompt_pack(
            [leverage_dim] + [dim for dim in list(pressure_targets.keys()) if dim != leverage_dim][:1],
            limit=2,
        )
        source_episode_ids = [summary.episode_id]
        for ref in list(corpus_pack.get("source_refs", []) or []):
            if ref not in source_episode_ids:
                source_episode_ids.append(ref)

        return PressureSpecializedAvatarSpec(
            avatar_id=_generate_id(f"pav_{leverage_dim[:8]}"),
            pressure_targets=pressure_targets,
            behavior_modes=behavior_modes,
            escalation_profile=escalation,
            source_leverage_points={leverage_dim: leverage_score},
            source_episode_ids=source_episode_ids,
            source_corpus_refs=list(corpus_pack.get("source_refs", []) or []),
            constraint_axes=constraint_axes,
            prompt_candidates=list(corpus_pack.get("prompt_candidates", []) or []),
            followup_candidates=list(corpus_pack.get("followup_candidates", []) or []),
            difficulty_floor=difficulty_floor,
            patience_modifier=patience,
            adaptive_hardness=adaptive_hardness,
        )

    def _build_persistent_spec(
        self,
        leverage_dim: str,
        leverage_score: float,
        persistent_weaknesses: Dict[str, float],
        episode_ids: List[str],
        spec_index: int,
    ) -> PressureSpecializedAvatarSpec:
        """
        Build an avatar spec for persistent cross-episode weaknesses.
        More aggressive than single-episode specs.
        """

        # Broader pressure targeting for persistent weaknesses
        pressure_targets: Dict[str, float] = {leverage_dim: 0.9}

        # Include all persistent weaknesses in the influence chain
        downstream = self.influence_graph.trace_downstream(leverage_dim)
        for ds_dim, ds_weight in downstream:
            if ds_dim in persistent_weaknesses:
                pressure_targets[ds_dim] = _clamp(ds_weight * 0.7, 0.2, 0.8)

        # Upstream dimensions too — stress the full causal chain
        upstream = self.influence_graph.trace_upstream(leverage_dim)
        for us_dim, us_weight in upstream[:2]:
            if us_dim in persistent_weaknesses:
                pressure_targets[us_dim] = _clamp(us_weight * 0.5, 0.1, 0.6)

        # Comprehensive behavior modes
        behavior_modes = dict(_DIMENSION_TO_BEHAVIOR.get(leverage_dim, {}))
        for dim in pressure_targets:
            if dim != leverage_dim:
                for bmode, bweight in _DIMENSION_TO_BEHAVIOR.get(dim, {}).items():
                    if bmode not in behavior_modes:
                        behavior_modes[bmode] = _clamp(bweight * 0.5)

        # Persistent weaknesses get aggressive escalation
        escalation = dict(_ESCALATION_PROFILES["aggressive"])

        # Low patience for persistent issues
        patience = _clamp(0.2 + persistent_weaknesses.get(leverage_dim, 0.3) * 0.5,
                          0.15, 0.5)

        # High difficulty floor
        difficulty_floor = _clamp(0.4 + leverage_score * 0.25, 0.4, 0.8)
        (
            pressure_targets,
            escalation,
            patience,
            difficulty_floor,
            adaptive_hardness,
            constraint_axes,
        ) = self._apply_adaptive_policy(
            leverage_dim=leverage_dim,
            pressure_targets=pressure_targets,
            escalation_profile=escalation,
            patience_modifier=patience,
            difficulty_floor=difficulty_floor,
        )
        corpus_pack = _DIRECTED_TRAINING.prompt_pack(
            [leverage_dim] + [dim for dim in list(pressure_targets.keys()) if dim != leverage_dim][:2],
            limit=2,
        )
        source_episode_ids = list(episode_ids[-5:])
        for ref in list(corpus_pack.get("source_refs", []) or []):
            if ref not in source_episode_ids:
                source_episode_ids.append(ref)

        return PressureSpecializedAvatarSpec(
            avatar_id=_generate_id(f"ppav_{leverage_dim[:7]}"),
            pressure_targets=pressure_targets,
            behavior_modes=behavior_modes,
            escalation_profile=escalation,
            source_leverage_points={leverage_dim: leverage_score},
            source_episode_ids=source_episode_ids,  # Last 5 episode sources + directed corpus refs
            source_corpus_refs=list(corpus_pack.get("source_refs", []) or []),
            constraint_axes=constraint_axes,
            prompt_candidates=list(corpus_pack.get("prompt_candidates", []) or []),
            followup_candidates=list(corpus_pack.get("followup_candidates", []) or []),
            difficulty_floor=difficulty_floor,
            patience_modifier=patience,
            adaptive_hardness=adaptive_hardness,
        )

    @property
    def specs_generated(self) -> int:
        return self._specs_generated

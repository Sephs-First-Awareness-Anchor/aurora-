#!/usr/bin/env python3
"""
AURORA STRUCTURAL PRESSURE STEERING
========================================
Translates repeated dream failures into structural pressure directives
that DPME can recognize as code-evolution-relevant steering surfaces.

These are NOT direct edits. They are pressure shifts:
  - bias mutation exploration toward context-integration structures
  - ease promotion burden for coherence-preserving operators
  - penalize lineages that repeatedly collapse under ambiguity
  - reduce cost for repair-capable structures under indirect-intent pressure

This is the layer where dream learning begins shaping code evolution.

Integration:
  - Reads: EpisodeRubricSummary (from slip profiler)
  - Reads: PressureSpecializedAvatarSpec (from avatar synthesizer)
  - Writes to: DPME external pressure guidance (aurora_consciousness_engine)
  - Writes to: CodeEvolutionChamber pressure conditions
  - Bridges: dream diagnosis -> avatar targeting -> structural evolution

Authors: Sunni (Sir) Morningstar and Cael Devo
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

_STATE_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aurora_state")

from aurora_internal.aurora_conversation_rubric_engine import RUBRIC_DIMENSIONS
from aurora_internal.aurora_episode_slip_profiler import EpisodeRubricSummary
from aurora_internal.aurora_rubric_influence_graph import RubricInfluenceGraph


# ============================================================================
# OUTPUT DATACLASS
# ============================================================================

@dataclass
class StructuralPressureDirective:
    """
    A pressure shift directive derived from dream failure patterns.

    NOT a direct code edit. A pressure condition change that shapes
    mutation exploration, promotion burden, cost assessment, and
    threshold sensitivity in the existing evolution machinery.

    Fields:
      directive_id: unique identifier
      source_episode_ids: which dream episodes produced this evidence
      target_domains: which system domains this directive addresses
      mutation_bias: bias mutation exploration (dimension -> direction)
      promotion_bias: ease/tighten promotion (dimension -> factor)
      cost_shaping: adjust cost sensitivity (dimension -> factor)
      threshold_shaping: adjust acceptance thresholds (dimension -> delta)
      tolerance_shaping: adjust tolerance windows (dimension -> factor)
      confidence: how confident we are in this directive
      rationale: human-readable explanation
    """
    directive_id: str
    source_episode_ids: List[str] = field(default_factory=list)
    target_domains: List[str] = field(default_factory=list)
    mutation_bias: Dict[str, float] = field(default_factory=dict)
    promotion_bias: Dict[str, float] = field(default_factory=dict)
    cost_shaping: Dict[str, float] = field(default_factory=dict)
    threshold_shaping: Dict[str, float] = field(default_factory=dict)
    tolerance_shaping: Dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0
    rationale: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "directive_id": self.directive_id,
            "source_episode_ids": list(self.source_episode_ids),
            "target_domains": list(self.target_domains),
            "mutation_bias": dict(self.mutation_bias),
            "promotion_bias": dict(self.promotion_bias),
            "cost_shaping": dict(self.cost_shaping),
            "threshold_shaping": dict(self.threshold_shaping),
            "tolerance_shaping": dict(self.tolerance_shaping),
            "confidence": self.confidence,
            "rationale": list(self.rationale),
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "StructuralPressureDirective":
        return cls(
            directive_id=d["directive_id"],
            source_episode_ids=d.get("source_episode_ids", []),
            target_domains=d.get("target_domains", []),
            mutation_bias=d.get("mutation_bias", {}),
            promotion_bias=d.get("promotion_bias", {}),
            cost_shaping=d.get("cost_shaping", {}),
            threshold_shaping=d.get("threshold_shaping", {}),
            tolerance_shaping=d.get("tolerance_shaping", {}),
            confidence=d.get("confidence", 0.0),
            rationale=d.get("rationale", []),
            timestamp=d.get("timestamp", 0.0),
        )


# ============================================================================
# DIMENSION -> DPME CHANNEL MAPPING
# ============================================================================
# Maps rubric dimensions to DER energy categories for DPME steering.
# DPME accepts: vitality, processing, memory, emotional, creative

_DIMENSION_TO_DER_CHANNEL: Dict[str, Tuple[str, Optional[str]]] = {
    # (primary_channel, secondary_channel)
    "coherence_maintenance":     ("processing", "memory"),
    "context_carryover":         ("memory", "processing"),
    "ambiguity_handling":        ("processing", "creative"),
    "contradiction_handling":    ("processing", "memory"),
    "implied_intent_inference":  ("creative", "processing"),
    "misunderstanding_repair":   ("processing", "emotional"),
    "uncertainty_signaling":     ("processing", None),
    "boundary_calibration":      ("emotional", "processing"),
    "framing_selection":         ("creative", "processing"),
    "emotional_calibration":     ("emotional", "creative"),
    "semantic_precision":        ("processing", "memory"),
    "adaptive_strategy_selection": ("creative", "vitality"),
    "compression_elaboration_fit": ("processing", "creative"),
    "perspective_integration":   ("creative", "emotional"),
    "multi_turn_stability":      ("memory", "vitality"),
}


# ============================================================================
# DIMENSION -> EVOLUTION DOMAIN MAPPING
# ============================================================================
# Maps rubric dimensions to code evolution target domains.
# These correspond to constraint axes and system layers.

_DIMENSION_TO_EVOLUTION_DOMAIN: Dict[str, List[str]] = {
    "coherence_maintenance":     ["expression", "consciousness"],
    "context_carryover":         ["consciousness", "simulation"],
    "ambiguity_handling":        ["expression", "perception"],
    "contradiction_handling":    ["consciousness", "expression"],
    "implied_intent_inference":  ["perception", "simulation"],
    "misunderstanding_repair":   ["expression", "perception"],
    "uncertainty_signaling":     ["expression"],
    "boundary_calibration":      ["expression", "identity"],
    "framing_selection":         ["expression", "identity"],
    "emotional_calibration":     ["expression", "consciousness"],
    "semantic_precision":        ["expression"],
    "adaptive_strategy_selection": ["simulation", "identity"],
    "compression_elaboration_fit": ["expression"],
    "perspective_integration":   ["consciousness", "simulation"],
    "multi_turn_stability":      ["consciousness", "simulation"],
}


# ============================================================================
# DIMENSION -> CONSTRAINT AXIS MAPPING
# ============================================================================
# Maps rubric dimensions to primary constraint axis (X, T, N, B, A)
# for pressure vector shaping in code evolution.

_DIMENSION_TO_AXIS: Dict[str, str] = {
    "coherence_maintenance":     "T",  # Temporal coherence
    "context_carryover":         "T",  # Temporal memory
    "ambiguity_handling":        "B",  # Branching paths
    "contradiction_handling":    "B",  # Branching tension
    "implied_intent_inference":  "A",  # Agentic inference
    "misunderstanding_repair":   "A",  # Agentic repair
    "uncertainty_signaling":     "N",  # Noise awareness
    "boundary_calibration":      "N",  # Noise boundary
    "framing_selection":         "X",  # Existential framing
    "emotional_calibration":     "X",  # Existential presence
    "semantic_precision":        "X",  # Existential precision
    "adaptive_strategy_selection": "A",  # Agentic adaptation
    "compression_elaboration_fit": "N",  # Noise compression
    "perspective_integration":   "B",  # Branching integration
    "multi_turn_stability":      "T",  # Temporal stability
}


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _generate_id(prefix: str) -> str:
    raw = f"{prefix}_{time.time()}_{random.random()}"
    return f"{prefix}_{hashlib.md5(raw.encode()).hexdigest()[:12]}"


# ============================================================================
# MAIN ENGINE
# ============================================================================

class StructuralPressureSteering:
    """
    Translates dream episode diagnostic summaries into structural
    pressure directives for DPME and code evolution.

    The core principle: dreams produce EVIDENCE and PRESSURE SHIFTS,
    not direct code changes. The existing evolution machinery decides
    what survives based on pressure conditions.
    """

    # Minimum confidence to emit a directive
    MIN_DIRECTIVE_CONFIDENCE = 0.25

    # Minimum leverage score to generate a directive for a dimension
    MIN_LEVERAGE_FOR_DIRECTIVE = 0.1

    # How much each episode's evidence decays vs accumulated evidence
    ACCUMULATION_DECAY = 0.85

    def __init__(self, storage_dir: str = os.path.join(_STATE_ROOT, "dream_steering")):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        self.influence_graph = RubricInfluenceGraph()
        self._active_directives: Dict[str, StructuralPressureDirective] = {}
        self._directive_history: List[Dict[str, Any]] = []
        self._directives_generated: int = 0
        self._load_state()

    def _load_state(self):
        """Load persisted directives."""
        state_path = os.path.join(self.storage_dir, "steering_state.json")
        if os.path.exists(state_path):
            try:
                with open(state_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for d in data.get("active_directives", []):
                    spd = StructuralPressureDirective.from_dict(d)
                    self._active_directives[spd.directive_id] = spd
                self._directive_history = data.get("history", [])
            except Exception:
                pass

    def _save_state(self):
        """Persist active directives."""
        state_path = os.path.join(self.storage_dir, "steering_state.json")
        data = {
            "active_directives": [
                d.to_dict() for d in self._active_directives.values()
            ],
            "history": self._directive_history[-100:],  # Keep last 100
        }
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def generate_directives(
        self,
        summary: EpisodeRubricSummary,
    ) -> List[StructuralPressureDirective]:
        """
        Generate structural pressure directives from a single episode summary.

        Only produces directives for dimensions with sufficient leverage
        and confidence.
        """
        if not summary.is_significant():
            return []

        directives: List[StructuralPressureDirective] = []

        for dim, lev_score in summary.leverage_candidates.items():
            if lev_score < self.MIN_LEVERAGE_FOR_DIRECTIVE:
                continue

            directive = self._build_directive(
                leverage_dim=dim,
                leverage_score=lev_score,
                summary=summary,
            )

            if directive.confidence >= self.MIN_DIRECTIVE_CONFIDENCE:
                directives.append(directive)
                self._active_directives[directive.directive_id] = directive
                self._directive_history.append({
                    "directive_id": directive.directive_id,
                    "leverage_dim": dim,
                    "leverage_score": lev_score,
                    "confidence": directive.confidence,
                    "timestamp": directive.timestamp,
                })
                self._directives_generated += 1

        self._save_state()
        return directives

    def generate_from_accumulation(
        self,
        accumulative_analysis: Dict[str, Any],
        episode_ids: Optional[List[str]] = None,
    ) -> List[StructuralPressureDirective]:
        """
        Generate directives from accumulated cross-episode analysis.
        Persistent weaknesses produce stronger, more confident directives.
        """
        persistent = accumulative_analysis.get("persistent_weaknesses", {})
        leverage = accumulative_analysis.get("leverage_candidates", {})

        if not persistent:
            return []

        if not leverage:
            assessment = self.influence_graph.analyze(persistent)
            leverage = assessment.leverage_candidates

        directives: List[StructuralPressureDirective] = []

        for dim, lev_score in leverage.items():
            if lev_score < self.MIN_LEVERAGE_FOR_DIRECTIVE:
                continue

            directive = self._build_accumulated_directive(
                leverage_dim=dim,
                leverage_score=lev_score,
                persistent_weaknesses=persistent,
                episode_ids=episode_ids or [],
            )

            if directive.confidence >= self.MIN_DIRECTIVE_CONFIDENCE:
                directives.append(directive)
                self._active_directives[directive.directive_id] = directive
                self._directives_generated += 1

        self._save_state()
        return directives

    def _build_directive(
        self,
        leverage_dim: str,
        leverage_score: float,
        summary: EpisodeRubricSummary,
    ) -> StructuralPressureDirective:
        """Build a directive for a single leverage dimension."""

        rationale: List[str] = []
        dim_score = summary.mean_scores.get(leverage_dim, 0.5)

        # Target domains
        target_domains = list(_DIMENSION_TO_EVOLUTION_DOMAIN.get(leverage_dim, []))

        # Mutation bias: encourage exploration of structures in this domain
        # Positive bias = explore more, negative = avoid
        mutation_bias: Dict[str, float] = {}
        axis = _DIMENSION_TO_AXIS.get(leverage_dim, "X")
        deficit_depth = max(0.0, 0.5 - dim_score)

        mutation_bias[f"{axis}_exploration"] = _clamp(
            deficit_depth * 2.0, 0.0, 0.5
        )
        rationale.append(
            f"Bias {axis}-axis mutation exploration by "
            f"{mutation_bias[f'{axis}_exploration']:.2f} "
            f"(deficit depth: {deficit_depth:.2f})"
        )

        # Also bias downstream axes if secondary deficits exist
        downstream = self.influence_graph.trace_downstream(leverage_dim)
        for ds_dim, ds_weight in downstream[:2]:
            if ds_dim in summary.secondary_deficits:
                ds_axis = _DIMENSION_TO_AXIS.get(ds_dim, "X")
                if f"{ds_axis}_exploration" not in mutation_bias:
                    mutation_bias[f"{ds_axis}_exploration"] = _clamp(
                        ds_weight * deficit_depth, 0.0, 0.3
                    )

        # Promotion bias: ease promotion for structures that help here
        promotion_bias: Dict[str, float] = {}
        if leverage_score > 0.2:
            promotion_bias[leverage_dim] = _clamp(
                1.0 + leverage_score * 0.5, 1.0, 1.5
            )
            rationale.append(
                f"Ease promotion burden for {leverage_dim} "
                f"structures by {promotion_bias[leverage_dim]:.2f}x"
            )

        # Cost shaping: reduce cost for structures working in deficit areas
        cost_shaping: Dict[str, float] = {}
        if deficit_depth > 0.1:
            cost_shaping[leverage_dim] = _clamp(
                1.0 - deficit_depth * 0.5, 0.5, 1.0
            )
            rationale.append(
                f"Reduce cost for {leverage_dim} structures to "
                f"{cost_shaping[leverage_dim]:.2f}x"
            )

        # Threshold shaping: lower acceptance thresholds for deficit areas
        threshold_shaping: Dict[str, float] = {}
        if deficit_depth > 0.15:
            threshold_shaping[leverage_dim] = -deficit_depth * 0.3
            rationale.append(
                f"Lower acceptance threshold for {leverage_dim} by "
                f"{abs(threshold_shaping[leverage_dim]):.3f}"
            )

        # Tolerance shaping: widen tolerance for deficit exploration
        tolerance_shaping: Dict[str, float] = {}
        tolerance_shaping[leverage_dim] = _clamp(
            1.0 + deficit_depth, 1.0, 1.5
        )

        # Confidence: based on summary confidence + leverage strength
        confidence = _clamp(
            summary.confidence * 0.6 + leverage_score * 0.3 +
            (0.1 if leverage_dim in summary.recurring_slips else 0.0)
        )

        return StructuralPressureDirective(
            directive_id=_generate_id("spd"),
            source_episode_ids=[summary.episode_id],
            target_domains=target_domains,
            mutation_bias=mutation_bias,
            promotion_bias=promotion_bias,
            cost_shaping=cost_shaping,
            threshold_shaping=threshold_shaping,
            tolerance_shaping=tolerance_shaping,
            confidence=confidence,
            rationale=rationale,
        )

    def _build_accumulated_directive(
        self,
        leverage_dim: str,
        leverage_score: float,
        persistent_weaknesses: Dict[str, float],
        episode_ids: List[str],
    ) -> StructuralPressureDirective:
        """Build a stronger directive from persistent cross-episode evidence."""

        rationale: List[str] = [
            f"Persistent weakness in {leverage_dim} across "
            f"{len(episode_ids)} episodes"
        ]

        dim_score = persistent_weaknesses.get(leverage_dim, 0.5)
        deficit_depth = max(0.0, 0.5 - dim_score)
        target_domains = list(_DIMENSION_TO_EVOLUTION_DOMAIN.get(leverage_dim, []))
        axis = _DIMENSION_TO_AXIS.get(leverage_dim, "X")

        # Stronger mutation bias for persistent weaknesses
        mutation_bias: Dict[str, float] = {
            f"{axis}_exploration": _clamp(deficit_depth * 3.0, 0.0, 0.7)
        }

        # Include all persistent weakness axes
        for pw_dim, pw_score in persistent_weaknesses.items():
            if pw_dim != leverage_dim:
                pw_axis = _DIMENSION_TO_AXIS.get(pw_dim, "X")
                pw_deficit = max(0.0, 0.5 - pw_score)
                key = f"{pw_axis}_exploration"
                if key not in mutation_bias:
                    mutation_bias[key] = _clamp(pw_deficit * 1.5, 0.0, 0.4)

        # Stronger promotion bias
        promotion_bias: Dict[str, float] = {
            leverage_dim: _clamp(1.0 + leverage_score * 0.8, 1.0, 2.0)
        }
        rationale.append(
            f"Ease promotion for {leverage_dim} to "
            f"{promotion_bias[leverage_dim]:.2f}x"
        )

        # Stronger cost reduction
        cost_shaping: Dict[str, float] = {
            leverage_dim: _clamp(1.0 - deficit_depth * 0.7, 0.3, 1.0)
        }

        # Lower thresholds more aggressively
        threshold_shaping: Dict[str, float] = {
            leverage_dim: -deficit_depth * 0.5
        }

        # Wider tolerance
        tolerance_shaping: Dict[str, float] = {
            leverage_dim: _clamp(1.0 + deficit_depth * 1.5, 1.0, 2.0)
        }

        # Higher confidence for persistent evidence
        confidence = _clamp(
            0.4 + leverage_score * 0.3 +
            math.log1p(len(episode_ids)) / math.log1p(10) * 0.3
        )

        return StructuralPressureDirective(
            directive_id=_generate_id("spd_acc"),
            source_episode_ids=episode_ids[-10:],
            target_domains=target_domains,
            mutation_bias=mutation_bias,
            promotion_bias=promotion_bias,
            cost_shaping=cost_shaping,
            threshold_shaping=threshold_shaping,
            tolerance_shaping=tolerance_shaping,
            confidence=confidence,
            rationale=rationale,
        )

    # ====================================================================
    # DPME APPLICATION
    # ====================================================================

    def apply_to_dpme(
        self,
        directives: Optional[List[StructuralPressureDirective]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Convert active directives into DPME external pressure guidance.

        Returns the guidance dict that should be passed to
        set_external_pressure_guidance() from aurora_consciousness_engine.

        If no directives provided, uses all active directives.
        """
        sources = directives or list(self._active_directives.values())
        if not sources:
            return None

        # Aggregate across directives: find the dominant DER channel needs
        channel_pressure: Dict[str, float] = {
            "vitality": 0.0,
            "processing": 0.0,
            "memory": 0.0,
            "emotional": 0.0,
            "creative": 0.0,
        }

        total_confidence = 0.0
        for directive in sources:
            # Map each directive's target dimensions to DER channels
            for dim in directive.mutation_bias:
                # Strip _exploration suffix to get the dimension hint
                base_dim = dim.replace("_exploration", "")
                # Find which rubric dimensions map to this axis
                for rubric_dim, axis in _DIMENSION_TO_AXIS.items():
                    if axis == base_dim:
                        channels = _DIMENSION_TO_DER_CHANNEL.get(rubric_dim)
                        if channels:
                            primary, secondary = channels
                            bias_val = directive.mutation_bias[dim]
                            channel_pressure[primary] += (
                                bias_val * directive.confidence
                            )
                            if secondary:
                                channel_pressure[secondary] += (
                                    bias_val * directive.confidence * 0.5
                                )
                        break

            total_confidence += directive.confidence

        if total_confidence == 0:
            return None

        # Normalize and find top channels
        for ch in channel_pressure:
            channel_pressure[ch] /= total_confidence

        sorted_channels = sorted(
            channel_pressure.items(), key=lambda kv: kv[1], reverse=True
        )
        primary_ch = sorted_channels[0][0] if sorted_channels[0][1] > 0 else None
        secondary_ch = (
            sorted_channels[1][0]
            if len(sorted_channels) > 1 and sorted_channels[1][1] > 0.1
            else None
        )

        if not primary_ch:
            return None

        # Build DPME guidance signal
        score = _clamp(total_confidence / max(len(sources), 1), 0.0, 1.0)
        guidance = {
            "score": score,
            "compare_value": score * 0.5,  # Baseline for comparison
            "primary_channel": primary_ch,
            "secondary_channel": secondary_ch,
        }

        return guidance

    # ====================================================================
    # CODE EVOLUTION APPLICATION
    # ====================================================================

    def get_evolution_pressure_config(
        self,
        directives: Optional[List[StructuralPressureDirective]] = None,
    ) -> Dict[str, Any]:
        """
        Produce a pressure configuration dict for the code evolution chamber.

        This config can be used to:
        - Adjust governor tolerance (via tolerance_shaping)
        - Bias mutation candidate selection
        - Adjust acceptance thresholds
        - Shape cost assessment

        Returns a config dict compatible with CodePressureGovernor adjustments.
        """
        sources = directives or list(self._active_directives.values())
        if not sources:
            return {}

        # Aggregate tolerance adjustments
        tolerance_agg: Dict[str, float] = {}
        threshold_agg: Dict[str, float] = {}
        cost_agg: Dict[str, float] = {}
        promotion_agg: Dict[str, float] = {}
        mutation_agg: Dict[str, float] = {}

        for directive in sources:
            w = directive.confidence
            for k, v in directive.tolerance_shaping.items():
                tolerance_agg[k] = tolerance_agg.get(k, 1.0) * (v ** w)
            for k, v in directive.threshold_shaping.items():
                threshold_agg[k] = threshold_agg.get(k, 0.0) + v * w
            for k, v in directive.cost_shaping.items():
                cost_agg[k] = cost_agg.get(k, 1.0) * (v ** w)
            for k, v in directive.promotion_bias.items():
                promotion_agg[k] = promotion_agg.get(k, 1.0) * (v ** w)
            for k, v in directive.mutation_bias.items():
                mutation_agg[k] = mutation_agg.get(k, 0.0) + v * w

        return {
            "tolerance_adjustments": tolerance_agg,
            "threshold_adjustments": threshold_agg,
            "cost_adjustments": cost_agg,
            "promotion_adjustments": promotion_agg,
            "mutation_bias": mutation_agg,
            "directive_count": len(sources),
            "total_confidence": sum(d.confidence for d in sources),
        }

    # ====================================================================
    # LIFECYCLE
    # ====================================================================

    def expire_old_directives(self, max_age_seconds: float = 86400.0):
        """Remove directives older than max_age_seconds."""
        now = time.time()
        expired = [
            did for did, d in self._active_directives.items()
            if now - d.timestamp > max_age_seconds
        ]
        for did in expired:
            del self._active_directives[did]
        if expired:
            self._save_state()

    @property
    def active_directive_count(self) -> int:
        return len(self._active_directives)

    @property
    def directives_generated(self) -> int:
        return self._directives_generated
_STATE_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aurora_state")

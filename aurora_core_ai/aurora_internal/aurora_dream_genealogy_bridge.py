#!/usr/bin/env python3
"""
AURORA DREAM GENEALOGY BRIDGE
==================================
Converts dream outcomes into genealogical evidence in the same style
as the rest of Aurora's evolution stack.

Dream experience becomes part of the SAME fossil record, not an
isolated side activity.

This bridge produces:
  - Trace items (ability/link references for genealogy)
  - Pressure deltas (before/after pressure vectors)
  - Cost/risk summaries
  - Origin tags marking simulation-derived evidence
  - Candidate operator/lineage evidence

Integration:
  - Reads: EpisodeRubricSummary (slip profiler)
  - Reads: StructuralPressureDirective (structural steering)
  - Reads: EpisodeResult (simulation engine)
  - Writes to: ConstraintGenealogyLogger.observe()
  - Writes to: register_code_evolution_outcome()
  - Writes to: ConsciousLearner.observe_outcome()
  - Writes to: ExpressionEcology / VoiceGenome (expression writeback)

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
from aurora_internal.aurora_structural_pressure_steering import (
    StructuralPressureDirective,
    _DIMENSION_TO_AXIS,
)


# ============================================================================
# DREAM EVIDENCE RECORD
# ============================================================================

@dataclass
class DreamEvidenceRecord:
    """
    A single piece of genealogical evidence derived from dream execution.

    This is the bridge format: produced by dream analysis, consumed by
    the genealogy logger and code evolution chamber.
    """
    evidence_id: str
    episode_id: str
    evidence_type: str  # "rubric_deficit", "improvement", "regression", "leverage_hit"
    source_dimensions: List[str] = field(default_factory=list)

    # Pressure vectors (5D: X, T, N, B, A)
    pressure_before: Dict[str, float] = field(default_factory=dict)
    pressure_after: Dict[str, float] = field(default_factory=dict)
    pressure_relief: Dict[str, float] = field(default_factory=dict)

    # Trace information for genealogy
    trace_abilities: List[str] = field(default_factory=list)
    trace_links: List[str] = field(default_factory=list)

    # Cost and risk
    cost_total: Dict[str, float] = field(default_factory=dict)
    risk_estimate: float = 0.0

    # Origin metadata
    origin_tags: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "episode_id": self.episode_id,
            "evidence_type": self.evidence_type,
            "source_dimensions": list(self.source_dimensions),
            "pressure_before": dict(self.pressure_before),
            "pressure_after": dict(self.pressure_after),
            "pressure_relief": dict(self.pressure_relief),
            "trace_abilities": list(self.trace_abilities),
            "trace_links": list(self.trace_links),
            "cost_total": dict(self.cost_total),
            "risk_estimate": self.risk_estimate,
            "origin_tags": dict(self.origin_tags),
            "confidence": self.confidence,
            "timestamp": self.timestamp,
        }


# ============================================================================
# EXPRESSION WRITEBACK RECORD
# ============================================================================

@dataclass
class ExpressionWritebackHint:
    """
    A hint for ExpressionEcology / VoiceGenome based on dream performance.

    Short-horizon behavioral effect (expression writeback) while code
    evolution handles the long-horizon structural effect.
    """
    hint_id: str
    dimension: str
    direction: str  # "reinforce" or "attenuate"
    strength: float = 0.0
    pattern_description: str = ""
    source_episode_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hint_id": self.hint_id,
            "dimension": self.dimension,
            "direction": self.direction,
            "strength": self.strength,
            "pattern_description": self.pattern_description,
            "source_episode_id": self.source_episode_id,
        }


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _generate_id(prefix: str) -> str:
    raw = f"{prefix}_{time.time()}_{random.random()}"
    return f"{prefix}_{hashlib.md5(raw.encode()).hexdigest()[:12]}"


# ============================================================================
# RUBRIC DIMENSION -> PRESSURE VECTOR CONVERSION
# ============================================================================

def _rubric_to_pressure_vec(
    dimension_scores: Dict[str, float],
    baseline: float = 0.5,
) -> Dict[str, float]:
    """
    Convert rubric dimension scores into a 5D pressure vector (X, T, N, B, A).

    Each rubric dimension maps to a primary axis. The deficit from baseline
    becomes pressure on that axis. More deficit = more pressure.
    """
    pressure = {"X": 0.0, "T": 0.0, "N": 0.0, "B": 0.0, "A": 0.0}
    axis_count = {"X": 0, "T": 0, "N": 0, "B": 0, "A": 0}

    for dim, score in dimension_scores.items():
        axis = _DIMENSION_TO_AXIS.get(dim)
        if axis:
            deficit = max(0.0, baseline - score)
            pressure[axis] += deficit
            axis_count[axis] += 1

    # Normalize per axis
    for axis in pressure:
        if axis_count[axis] > 0:
            pressure[axis] /= axis_count[axis]

    return pressure


def _compute_relief(
    before: Dict[str, float],
    after: Dict[str, float],
) -> Dict[str, float]:
    """Compute pressure relief: positive means pressure reduced."""
    return {
        axis: before.get(axis, 0.0) - after.get(axis, 0.0)
        for axis in ("X", "T", "N", "B", "A")
    }


# ============================================================================
# DIMENSION -> TRACE ABILITY MAPPING
# ============================================================================
# Maps rubric dimensions to synthetic "ability" identifiers for genealogy.
# These represent communicative competence abilities in the trace system.

_DIMENSION_TO_ABILITY: Dict[str, str] = {
    "coherence_maintenance":     "dream:coherence_maint",
    "context_carryover":         "dream:context_carry",
    "ambiguity_handling":        "dream:ambiguity_handle",
    "contradiction_handling":    "dream:contradiction_handle",
    "implied_intent_inference":  "dream:intent_inference",
    "misunderstanding_repair":   "dream:repair_initiate",
    "uncertainty_signaling":     "dream:uncertainty_signal",
    "boundary_calibration":      "dream:boundary_cal",
    "framing_selection":         "dream:framing_select",
    "emotional_calibration":     "dream:emotional_cal",
    "semantic_precision":        "dream:semantic_prec",
    "adaptive_strategy_selection": "dream:adaptive_strategy",
    "compression_elaboration_fit": "dream:compress_elab",
    "perspective_integration":   "dream:perspective_integ",
    "multi_turn_stability":      "dream:multi_turn_stab",
}

# Maps rubric dimensions to source files that carry the primary behavior surface.
# These are relative project paths consumed by genealogy/code-evolution tooling.
_DIMENSION_TO_TARGET_FILES: Dict[str, List[str]] = {
    "coherence_maintenance": [
        "aurora.py",
        "aurora_governance_persistence_gateway.py",
    ],
    "context_carryover": [
        "aurora.py",
        "aurora_governance_persistence_gateway.py",
    ],
    "ambiguity_handling": [
        "aurora.py",
        "aurora_expression_perception.py",
    ],
    "contradiction_handling": [
        "aurora.py",
        "aurora_consciousness_engine.py",
    ],
    "implied_intent_inference": [
        "aurora.py",
        "aurora_expression_perception.py",
    ],
    "misunderstanding_repair": [
        "aurora.py",
        "aurora_expression_perception.py",
    ],
    "uncertainty_signaling": [
        "aurora.py",
        "aurora_governance_persistence_gateway.py",
    ],
    "boundary_calibration": [
        "aurora_governance_persistence_gateway.py",
        "aurora_behavioral_identity.py",
    ],
    "framing_selection": [
        "aurora.py",
        "aurora_expression_perception.py",
    ],
    "emotional_calibration": [
        "aurora_expression_perception.py",
        "aurora_behavioral_identity.py",
    ],
    "semantic_precision": [
        "aurora.py",
        "aurora_expression_perception.py",
    ],
    "adaptive_strategy_selection": [
        "aurora_simulation_engine.py",
        "aurora_governance_persistence_gateway.py",
    ],
    "compression_elaboration_fit": [
        "aurora.py",
        "aurora_expression_perception.py",
    ],
    "perspective_integration": [
        "aurora.py",
        "aurora_simulation_engine.py",
    ],
    "multi_turn_stability": [
        "aurora.py",
        "aurora_simulation_engine.py",
    ],
}

_DIMENSION_TO_PURPOSE_LANE: Dict[str, str] = {
    "coherence_maintenance": "communication",
    "context_carryover": "communication",
    "ambiguity_handling": "meaning",
    "contradiction_handling": "intelligence",
    "implied_intent_inference": "meaning",
    "misunderstanding_repair": "communication",
    "uncertainty_signaling": "intelligence",
    "boundary_calibration": "communication",
    "framing_selection": "communication",
    "emotional_calibration": "communication",
    "semantic_precision": "meaning",
    "adaptive_strategy_selection": "intelligence",
    "compression_elaboration_fit": "communication",
    "perspective_integration": "meaning",
    "multi_turn_stability": "communication",
}


def _base_dimension_name(raw: str) -> str:
    return str(raw or "").strip().replace("_exploration", "")


def _infer_purpose_lane(dimensions: List[str], fallback: str = "communication") -> str:
    counts = {"intelligence": 0, "communication": 0, "meaning": 0}
    for raw in dimensions:
        lane = _DIMENSION_TO_PURPOSE_LANE.get(_base_dimension_name(raw))
        if lane in counts:
            counts[lane] += 1
    best_lane = max(counts.items(), key=lambda kv: (kv[1], kv[0]))[0]
    return best_lane if counts[best_lane] > 0 else fallback


def _build_trace_abilities(
    base_abilities: List[str],
    dimensions: List[str],
    fallback_lane: str = "communication",
) -> Tuple[str, List[str]]:
    lane = _infer_purpose_lane(dimensions, fallback=fallback_lane)
    ordered: List[str] = []
    seen: set[str] = set()

    def _push(token: str):
        tok = str(token or "").strip()
        if tok and tok not in seen:
            seen.add(tok)
            ordered.append(tok)

    for ability in base_abilities:
        _push(ability)
    _push(f"dream:purpose:{lane}")
    for raw in dimensions:
        axis = _DIMENSION_TO_AXIS.get(_base_dimension_name(raw))
        if axis:
            _push(f"dream:axis:{axis}")
    return lane, ordered


def _resolve_target_files(dimensions: List[str]) -> List[str]:
    """
    Resolve weak rubric dimensions to concrete source files.
    Ensures dream evidence can pressure specific code surfaces.
    """
    files: List[str] = []
    seen: set[str] = set()
    for dim in dimensions:
        for path in _DIMENSION_TO_TARGET_FILES.get(str(dim), []):
            p = str(path).strip()
            if not p or p in seen:
                continue
            seen.add(p)
            files.append(p)
    if files:
        return files
    # Safe default when dimensions are unknown
    return ["aurora.py"]


# ============================================================================
# MAIN BRIDGE
# ============================================================================

class DreamGenealogyBridge:
    """
    Converts dream outcomes into genealogical evidence compatible with
    Aurora's existing evolution stack.

    Produces:
    1. DreamEvidenceRecord — for ConstraintGenealogyLogger.observe()
    2. ExpressionWritebackHint — for ExpressionEcology / VoiceGenome
    3. Conscious learner observations — for ConsciousLearner.observe_outcome()
    4. Code evolution outcome data — for register_code_evolution_outcome()
    """

    def __init__(self, storage_dir: str = os.path.join(_STATE_ROOT, "dream_genealogy")):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        self._evidence_log: List[Dict[str, Any]] = []
        self._records_generated: int = 0

    # ====================================================================
    # EVIDENCE GENERATION
    # ====================================================================

    def generate_evidence(
        self,
        summary: EpisodeRubricSummary,
        directives: Optional[List[StructuralPressureDirective]] = None,
        previous_summary: Optional[EpisodeRubricSummary] = None,
    ) -> List[DreamEvidenceRecord]:
        """
        Generate genealogical evidence records from a dream episode summary.

        If previous_summary is provided, also generates improvement/regression
        evidence by comparing the two episodes.
        """
        records: List[DreamEvidenceRecord] = []

        # 1. Deficit evidence: each primary deficit becomes evidence
        for dim, score in summary.primary_deficits.items():
            record = self._build_deficit_evidence(
                episode_id=summary.episode_id,
                dimension=dim,
                score=score,
                summary=summary,
            )
            records.append(record)

        # 2. Leverage hit evidence: leverage candidates get special records
        for dim, lev_score in summary.leverage_candidates.items():
            record = self._build_leverage_evidence(
                episode_id=summary.episode_id,
                dimension=dim,
                leverage_score=lev_score,
                summary=summary,
            )
            records.append(record)

        # 3. Improvement/regression evidence (if comparing episodes)
        if previous_summary:
            for dim in RUBRIC_DIMENSIONS:
                prev_score = previous_summary.mean_scores.get(dim, 0.5)
                curr_score = summary.mean_scores.get(dim, 0.5)
                delta = curr_score - prev_score

                if abs(delta) > 0.05:  # Significant change
                    record = self._build_delta_evidence(
                        episode_id=summary.episode_id,
                        dimension=dim,
                        prev_score=prev_score,
                        curr_score=curr_score,
                        delta=delta,
                    )
                    records.append(record)

        # 4. Directive-linked evidence
        if directives:
            for directive in directives:
                record = self._build_directive_evidence(
                    episode_id=summary.episode_id,
                    directive=directive,
                    summary=summary,
                )
                records.append(record)

        # Persist evidence log
        for rec in records:
            self._evidence_log.append(rec.to_dict())
            self._records_generated += 1

        self._save_log()
        return records

    def _build_deficit_evidence(
        self,
        episode_id: str,
        dimension: str,
        score: float,
        summary: EpisodeRubricSummary,
    ) -> DreamEvidenceRecord:
        """Build evidence for a primary deficit."""
        # Compute pressure from deficit scores
        pressure_before = _rubric_to_pressure_vec(summary.mean_scores)
        # "After" is what ideal scores would look like
        ideal_scores = {d: max(s, 0.5) for d, s in summary.mean_scores.items()}
        pressure_after = _rubric_to_pressure_vec(ideal_scores)
        relief = _compute_relief(pressure_before, pressure_after)

        ability = _DIMENSION_TO_ABILITY.get(dimension, f"dream:{dimension}")
        axis = _DIMENSION_TO_AXIS.get(dimension, "X")
        lane, trace_abilities = _build_trace_abilities([ability], [dimension], fallback_lane="communication")

        return DreamEvidenceRecord(
            evidence_id=_generate_id("dev_def"),
            episode_id=episode_id,
            evidence_type="rubric_deficit",
            source_dimensions=[dimension],
            pressure_before=pressure_before,
            pressure_after=pressure_after,
            pressure_relief=relief,
            trace_abilities=trace_abilities,
            cost_total={axis: max(0.0, 0.5 - score) * 0.02},
            risk_estimate=_clamp((0.5 - score) * 0.1, 0.0, 0.05),
            origin_tags={
                "source": "dream_episode",
                "evidence_class": "deficit",
                "deficit_dimension": dimension,
                "deficit_score": score,
                "artificial_seed": True,
                "artificial_seed_weight": _clamp((0.5 - score) * 1.5, 0.1, 0.8),
                "seed_lineage_id": episode_id,
                "target_purpose_lane": lane,
            },
            confidence=summary.confidence * 0.8,
        )

    def _build_leverage_evidence(
        self,
        episode_id: str,
        dimension: str,
        leverage_score: float,
        summary: EpisodeRubricSummary,
    ) -> DreamEvidenceRecord:
        """Build evidence for a leverage candidate."""
        pressure_before = _rubric_to_pressure_vec(summary.mean_scores)
        # Leverage fix: project improvement in this dimension and downstream
        projected = dict(summary.mean_scores)
        projected[dimension] = min(1.0, projected.get(dimension, 0.5) + 0.2)
        pressure_after = _rubric_to_pressure_vec(projected)
        relief = _compute_relief(pressure_before, pressure_after)

        ability = _DIMENSION_TO_ABILITY.get(dimension, f"dream:{dimension}")
        lane, trace_abilities = _build_trace_abilities([ability], [dimension], fallback_lane="communication")

        return DreamEvidenceRecord(
            evidence_id=_generate_id("dev_lev"),
            episode_id=episode_id,
            evidence_type="leverage_hit",
            source_dimensions=[dimension],
            pressure_before=pressure_before,
            pressure_after=pressure_after,
            pressure_relief=relief,
            trace_abilities=trace_abilities,
            cost_total={},
            risk_estimate=0.0,
            origin_tags={
                "source": "dream_episode",
                "evidence_class": "leverage",
                "leverage_dimension": dimension,
                "leverage_score": leverage_score,
                "artificial_seed": True,
                "artificial_seed_weight": _clamp(leverage_score * 0.5),
                "seed_lineage_id": episode_id,
                "target_purpose_lane": lane,
            },
            confidence=summary.confidence * leverage_score,
        )

    def _build_delta_evidence(
        self,
        episode_id: str,
        dimension: str,
        prev_score: float,
        curr_score: float,
        delta: float,
    ) -> DreamEvidenceRecord:
        """Build evidence for improvement or regression."""
        evidence_type = "improvement" if delta > 0 else "regression"

        # Pressure from actual score change
        prev_vec = _rubric_to_pressure_vec({dimension: prev_score})
        curr_vec = _rubric_to_pressure_vec({dimension: curr_score})
        relief = _compute_relief(prev_vec, curr_vec)

        ability = _DIMENSION_TO_ABILITY.get(dimension, f"dream:{dimension}")
        lane, trace_abilities = _build_trace_abilities([ability], [dimension], fallback_lane="communication")

        return DreamEvidenceRecord(
            evidence_id=_generate_id(f"dev_{'imp' if delta > 0 else 'reg'}"),
            episode_id=episode_id,
            evidence_type=evidence_type,
            source_dimensions=[dimension],
            pressure_before=prev_vec,
            pressure_after=curr_vec,
            pressure_relief=relief,
            trace_abilities=trace_abilities,
            cost_total={},
            risk_estimate=0.0 if delta > 0 else _clamp(abs(delta) * 0.05, 0.0, 0.03),
            origin_tags={
                "source": "dream_episode",
                "evidence_class": evidence_type,
                "dimension": dimension,
                "delta": delta,
                "previous_score": prev_score,
                "current_score": curr_score,
                "artificial_seed": True,
                "artificial_seed_weight": _clamp(abs(delta), 0.1, 0.8),
                "seed_lineage_id": episode_id,
                "target_purpose_lane": lane,
            },
            confidence=_clamp(abs(delta) * 2.0, 0.1, 0.9),
        )

    def _build_directive_evidence(
        self,
        episode_id: str,
        directive: StructuralPressureDirective,
        summary: EpisodeRubricSummary,
    ) -> DreamEvidenceRecord:
        """Build evidence linking a directive's effect to dream outcomes."""
        pressure_before = _rubric_to_pressure_vec(summary.mean_scores)

        # Project what scores would look like if directive succeeded
        projected = dict(summary.mean_scores)
        for dim in directive.mutation_bias:
            base_dim = dim.replace("_exploration", "")
            for rubric_dim, axis in _DIMENSION_TO_AXIS.items():
                if axis == base_dim and rubric_dim in projected:
                    projected[rubric_dim] = min(
                        1.0,
                        projected[rubric_dim] + directive.mutation_bias[dim] * 0.3
                    )

        pressure_after = _rubric_to_pressure_vec(projected)
        relief = _compute_relief(pressure_before, pressure_after)

        # Trace: abilities from all dimensions the directive targets
        abilities = []
        for dim in directive.target_domains:
            abilities.append(f"dream:directive:{dim}")
        lane, trace_abilities = _build_trace_abilities(abilities, directive.target_domains, fallback_lane="communication")

        return DreamEvidenceRecord(
            evidence_id=_generate_id("dev_dir"),
            episode_id=episode_id,
            evidence_type="directive_projection",
            source_dimensions=directive.target_domains,
            pressure_before=pressure_before,
            pressure_after=pressure_after,
            pressure_relief=relief,
            trace_abilities=trace_abilities,
            cost_total={},
            risk_estimate=0.0,
            origin_tags={
                "source": "dream_episode",
                "evidence_class": "directive_projection",
                "directive_id": directive.directive_id,
                "directive_confidence": directive.confidence,
                "artificial_seed": True,
                "artificial_seed_weight": _clamp(directive.confidence * summary.confidence, 0.1, 0.9),
                "seed_lineage_id": directive.directive_id,
                "target_purpose_lane": lane,
            },
            confidence=directive.confidence * summary.confidence,
        )

    # ====================================================================
    # EXPRESSION WRITEBACK
    # ====================================================================

    def generate_expression_hints(
        self,
        summary: EpisodeRubricSummary,
    ) -> List[ExpressionWritebackHint]:
        """
        Generate expression-side hints from dream performance.

        Successful patterns get reinforced in ExpressionEcology.
        Failed patterns get attenuated.
        This is the SHORT-HORIZON behavioral effect.
        """
        hints: List[ExpressionWritebackHint] = []

        for dim in RUBRIC_DIMENSIONS:
            score = summary.mean_scores.get(dim, 0.5)

            if score > 0.65:
                # Strong dimension: reinforce
                hints.append(ExpressionWritebackHint(
                    hint_id=_generate_id("ewh_r"),
                    dimension=dim,
                    direction="reinforce",
                    strength=_clamp((score - 0.65) * 2.0, 0.1, 0.8),
                    pattern_description=(
                        f"Dream performance strong in {dim} "
                        f"(score={score:.2f}): reinforce patterns"
                    ),
                    source_episode_id=summary.episode_id,
                ))
            elif score < 0.35:
                # Weak dimension: attenuate current approach
                hints.append(ExpressionWritebackHint(
                    hint_id=_generate_id("ewh_a"),
                    dimension=dim,
                    direction="attenuate",
                    strength=_clamp((0.35 - score) * 2.0, 0.1, 0.8),
                    pattern_description=(
                        f"Dream performance weak in {dim} "
                        f"(score={score:.2f}): attenuate current patterns"
                    ),
                    source_episode_id=summary.episode_id,
                ))

        return hints

    # ====================================================================
    # CONSCIOUS LEARNER OBSERVATIONS
    # ====================================================================

    def generate_learner_observations(
        self,
        summary: EpisodeRubricSummary,
    ) -> List[Dict[str, Any]]:
        """
        Generate observation data compatible with ConsciousLearner.observe_outcome().

        Returns list of dicts with keys that map to ConversationObservation fields
        plus understanding text for shard creation.
        """
        observations: List[Dict[str, Any]] = []

        # Generate observations for significant dimensions
        for dim, score in sorted(
            summary.mean_scores.items(), key=lambda kv: kv[1]
        ):
            if score < 0.35 or score > 0.65:
                obs = {
                    "avatar_engaged": score > 0.5,
                    "conversation_deepened": score > 0.6,
                    "connection_felt_stronger": score > 0.65,
                    "tension_arose": score < 0.35,
                    "flow_maintained": score > 0.5,
                    "context_type": f"dream_{dim}",
                    "understanding_text": self._generate_understanding(dim, score),
                }
                observations.append(obs)

        # Leverage-based observations
        for dim, lev_score in summary.leverage_candidates.items():
            observations.append({
                "avatar_engaged": True,
                "conversation_deepened": lev_score > 0.3,
                "tension_arose": True,
                "flow_maintained": False,
                "context_type": f"dream_leverage_{dim}",
                "understanding_text": (
                    f"Leverage opportunity: improving {dim} "
                    f"(leverage={lev_score:.2f}) would improve downstream dimensions"
                ),
            })

        return observations

    def _generate_understanding(self, dimension: str, score: float) -> str:
        """Generate understanding text for a dimension's performance."""
        dim_label = dimension.replace("_", " ")
        if score > 0.65:
            return (
                f"Dream experience confirms strength in {dim_label} "
                f"(score={score:.2f}). Current approach works well here."
            )
        elif score < 0.35:
            return (
                f"Dream experience reveals weakness in {dim_label} "
                f"(score={score:.2f}). Current approach needs adjustment."
            )
        else:
            return (
                f"Dream experience shows moderate {dim_label} "
                f"(score={score:.2f}). Room for growth."
            )

    # ====================================================================
    # CODE EVOLUTION OUTCOME FORMAT
    # ====================================================================

    def format_for_code_evolution(
        self,
        records: List[DreamEvidenceRecord],
    ) -> List[Dict[str, Any]]:
        """
        Format evidence records for register_code_evolution_outcome().

        Returns data compatible with the code evolution stack's outcome format.
        """
        outcomes: List[Dict[str, Any]] = []

        for rec in records:
            # Only certain evidence types are relevant for code evolution
            if rec.evidence_type not in (
                "rubric_deficit", "leverage_hit", "improvement", "regression"
            ):
                continue

            outcome = {
                "mutation_name": f"dream_evidence:{rec.evidence_type}",
                "constraints_used": frozenset(rec.source_dimensions),
                "target_files": _resolve_target_files(rec.source_dimensions),
                "pressure_before": rec.pressure_before,
                "pressure_after": rec.pressure_after,
                "checks_passed": rec.evidence_type in ("improvement", "leverage_hit"),
                "notes": {
                    **rec.origin_tags,
                    "evidence_id": rec.evidence_id,
                    "episode_id": rec.episode_id,
                    "confidence": rec.confidence,
                    "action_energy": {
                        "represented_scale": list(rec.cost_total.keys())[0]
                        if rec.cost_total else "T",
                        "effective_energy_cost": sum(rec.cost_total.values()),
                        "idle_persistence_cost": 0.0,
                    },
                },
            }
            outcomes.append(outcome)

        return outcomes

    # ====================================================================
    # GENEALOGY TRACE FORMAT
    # ====================================================================

    def format_for_genealogy(
        self,
        records: List[DreamEvidenceRecord],
    ) -> List[Dict[str, Any]]:
        """
        Format evidence records for ConstraintGenealogyLogger.observe().

        Returns data with:
        - pressure_before/after as PressureVec-compatible dicts
        - trace as list of TraceItem-compatible dicts
        - notes with origin metadata
        """
        entries: List[Dict[str, Any]] = []

        for rec in records:
            trace_items = []
            for ability_id in rec.trace_abilities:
                trace_items.append({
                    "kind": "ABILITY",
                    "id": ability_id,
                })
            for link_id in rec.trace_links:
                trace_items.append({
                    "kind": "LINK",
                    "id": link_id,
                })

            entry = {
                "pressure_before": rec.pressure_before,
                "pressure_after": rec.pressure_after,
                "trace": trace_items,
                "notes": {
                    **rec.origin_tags,
                    "evidence_id": rec.evidence_id,
                    "evidence_type": rec.evidence_type,
                    "confidence": rec.confidence,
                    "cost_total": rec.cost_total,
                    "risk_estimate": rec.risk_estimate,
                    "action_energy": {
                        "represented_scale": list(rec.cost_total.keys())[0]
                        if rec.cost_total else "T",
                        "effective_energy_cost": sum(rec.cost_total.values()),
                        "idle_persistence_cost": 0.0,
                    },
                },
                "state_sig_before": f"dream_pre_{rec.episode_id}",
                "state_sig_after": f"dream_post_{rec.episode_id}",
            }
            entries.append(entry)

        return entries

    # ====================================================================
    # PERSISTENCE
    # ====================================================================

    def _save_log(self):
        """Persist evidence log to disk."""
        log_path = os.path.join(self.storage_dir, "evidence_log.json")
        # Keep log bounded
        trimmed = self._evidence_log[-500:]
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(trimmed, f, indent=2)

    def load_recent_evidence(self, count: int = 50) -> List[Dict[str, Any]]:
        """Load recent evidence records from disk."""
        log_path = os.path.join(self.storage_dir, "evidence_log.json")
        if not os.path.exists(log_path):
            return []
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data[-count:]
        except Exception:
            return []

    @property
    def records_generated(self) -> int:
        return self._records_generated
_STATE_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aurora_state")

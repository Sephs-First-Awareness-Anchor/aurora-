#!/usr/bin/env python3
"""
AURORA EPISODE SLIP PROFILER
================================
Produces a single structured summary from a 10-conversation dream episode.

Input:
  - EpisodeResult (from SimulationEngine)
  - Per-thread ConversationObservation
  - Per-thread ConversationRubricScore

Output:
  - EpisodeRubricSummary: mean scores, variance, recurring slips,
    primary/secondary deficits, leverage candidates

This summary is what the rest of the dream evolution system uses.
Not raw conversation chaos.

Authors: Sunni (Sir) Morningstar and Cael Devo
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from aurora_internal.aurora_conversation_rubric_engine import (
    ConversationRubricScore,
    RUBRIC_DIMENSIONS,
)
from aurora_internal.aurora_rubric_influence_graph import (
    RubricInfluenceGraph,
    RubricInfluenceAssessment,
)


# ============================================================================
# OUTPUT DATACLASS
# ============================================================================

@dataclass
class EpisodeRubricSummary:
    """
    Diagnostic summary of one dream episode (10 conversations).
    This is the bridge between raw dream experience and structural steering.
    """
    episode_id: str
    mean_scores: Dict[str, float] = field(default_factory=dict)
    variance_scores: Dict[str, float] = field(default_factory=dict)
    recurring_slips: Dict[str, float] = field(default_factory=dict)
    primary_deficits: Dict[str, float] = field(default_factory=dict)
    secondary_deficits: Dict[str, float] = field(default_factory=dict)
    leverage_candidates: Dict[str, float] = field(default_factory=dict)
    influence_rationale: List[str] = field(default_factory=list)
    episode_fitness: float = 0.0
    thread_count: int = 0
    confidence: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "mean_scores": dict(self.mean_scores),
            "variance_scores": dict(self.variance_scores),
            "recurring_slips": dict(self.recurring_slips),
            "primary_deficits": dict(self.primary_deficits),
            "secondary_deficits": dict(self.secondary_deficits),
            "leverage_candidates": dict(self.leverage_candidates),
            "influence_rationale": list(self.influence_rationale),
            "episode_fitness": self.episode_fitness,
            "thread_count": self.thread_count,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
        }

    def weakest_leverage(self, n: int = 3) -> List[Tuple[str, float]]:
        """Return top-n leverage candidates."""
        items = sorted(self.leverage_candidates.items(),
                      key=lambda kv: kv[1], reverse=True)
        return items[:n]

    def is_significant(self) -> bool:
        """Whether this summary has enough data to drive steering."""
        return self.thread_count >= 3 and self.confidence > 0.3


# ============================================================================
# SLIP DETECTION
# ============================================================================

# A slip is a dimension where multiple conversations show weakness
_SLIP_THRESHOLD = 0.4       # Score below this is considered a slip
_RECURRING_FRACTION = 0.3   # Slip must appear in 30%+ of threads to be recurring


# ============================================================================
# MAIN PROFILER
# ============================================================================

class EpisodeSlipProfiler:
    """
    Analyzes a dream episode's conversation rubric scores to produce
    a structured diagnostic summary.

    Uses RubricInfluenceGraph to distinguish root deficits from symptoms.
    """

    def __init__(self):
        self.influence_graph = RubricInfluenceGraph()
        self._profiles_generated: int = 0

    def profile(
        self,
        episode_id: str,
        rubric_scores: List[ConversationRubricScore],
        episode_fitness: float = 0.0,
        observation_summaries: Optional[List[str]] = None,
    ) -> EpisodeRubricSummary:
        """
        Generate an EpisodeRubricSummary from per-thread rubric scores.

        Args:
            episode_id: ID of the dream episode
            rubric_scores: Per-conversation rubric scores
            episode_fitness: Average fitness from SimulationEngine
            observation_summaries: Optional ConversationObservation descriptions
        """
        if not rubric_scores:
            return EpisodeRubricSummary(
                episode_id=episode_id,
                episode_fitness=episode_fitness,
            )

        thread_count = len(rubric_scores)

        # ---- Compute means ----
        mean_scores = {dim: 0.0 for dim in RUBRIC_DIMENSIONS}
        for rs in rubric_scores:
            for dim in RUBRIC_DIMENSIONS:
                mean_scores[dim] += rs.dimension_scores.get(dim, 0.5)
        for dim in RUBRIC_DIMENSIONS:
            mean_scores[dim] /= thread_count

        # ---- Compute variance ----
        variance_scores = {dim: 0.0 for dim in RUBRIC_DIMENSIONS}
        for rs in rubric_scores:
            for dim in RUBRIC_DIMENSIONS:
                diff = rs.dimension_scores.get(dim, 0.5) - mean_scores[dim]
                variance_scores[dim] += diff ** 2
        for dim in RUBRIC_DIMENSIONS:
            variance_scores[dim] /= thread_count

        # ---- Detect recurring slips ----
        slip_counts: Dict[str, int] = {dim: 0 for dim in RUBRIC_DIMENSIONS}
        for rs in rubric_scores:
            for dim in RUBRIC_DIMENSIONS:
                if rs.dimension_scores.get(dim, 0.5) < _SLIP_THRESHOLD:
                    slip_counts[dim] += 1

        recurring_slips: Dict[str, float] = {}
        min_occurrences = max(1, int(thread_count * _RECURRING_FRACTION))
        for dim, count in slip_counts.items():
            if count >= min_occurrences:
                recurring_slips[dim] = count / thread_count

        # ---- Influence analysis ----
        assessment = self.influence_graph.analyze(mean_scores)

        # ---- Confidence ----
        # More threads + more consistent scores = higher confidence
        avg_confidence = sum(rs.confidence for rs in rubric_scores) / thread_count
        score_consistency = 1.0 - (
            sum(variance_scores.values()) / max(len(variance_scores), 1)
        )
        confidence = min(1.0, avg_confidence * 0.5 + score_consistency * 0.3 +
                        math.log1p(thread_count) / math.log1p(10) * 0.2)

        self._profiles_generated += 1

        return EpisodeRubricSummary(
            episode_id=episode_id,
            mean_scores=mean_scores,
            variance_scores=variance_scores,
            recurring_slips=recurring_slips,
            primary_deficits=assessment.primary_dimensions,
            secondary_deficits=assessment.secondary_dimensions,
            leverage_candidates=assessment.leverage_candidates,
            influence_rationale=assessment.rationale,
            episode_fitness=episode_fitness,
            thread_count=thread_count,
            confidence=confidence,
        )

    def profile_accumulative(
        self,
        summaries: List[EpisodeRubricSummary],
    ) -> Dict[str, Any]:
        """
        Produce a meta-analysis across multiple episode summaries.
        Identifies PERSISTENT weaknesses that recur across episodes.
        """
        if not summaries:
            return {"persistent_weaknesses": {}, "improving_dimensions": {}}

        dim_history: Dict[str, List[float]] = {
            dim: [] for dim in RUBRIC_DIMENSIONS
        }
        for summary in summaries:
            for dim in RUBRIC_DIMENSIONS:
                dim_history[dim].append(summary.mean_scores.get(dim, 0.5))

        persistent_weaknesses: Dict[str, float] = {}
        improving_dimensions: Dict[str, float] = {}
        stable_strengths: Dict[str, float] = {}

        for dim, history in dim_history.items():
            if not history:
                continue
            mean = sum(history) / len(history)

            if mean < _SLIP_THRESHOLD:
                persistent_weaknesses[dim] = mean

            # Trend detection (simple: compare first half vs second half)
            if len(history) >= 4:
                first_half = sum(history[:len(history) // 2]) / (len(history) // 2)
                second_half = sum(history[len(history) // 2:]) / (len(history) - len(history) // 2)
                delta = second_half - first_half
                if delta > 0.05:
                    improving_dimensions[dim] = delta
            elif mean > 0.6:
                stable_strengths[dim] = mean

        # Re-run influence analysis on persistent weaknesses
        persistent_assessment = self.influence_graph.analyze(
            {dim: score for dim, score in persistent_weaknesses.items()}
        ) if persistent_weaknesses else None

        return {
            "persistent_weaknesses": persistent_weaknesses,
            "improving_dimensions": improving_dimensions,
            "stable_strengths": stable_strengths,
            "leverage_candidates": (
                persistent_assessment.leverage_candidates
                if persistent_assessment else {}
            ),
            "episode_count": len(summaries),
        }

    @property
    def profiles_generated(self) -> int:
        return self._profiles_generated

#!/usr/bin/env python3
"""
AURORA RUBRIC INFLUENCE GRAPH
=================================
Represents dependency relationships between rubric dimensions.

Failures are NOT flat bins. They form a relational pattern:
  - symptoms (what you see)
  - root deficits (what causes the symptoms)
  - downstream consequences (what the root deficit also breaks)

This graph lets the system distinguish between these and identify
LEVERAGE CANDIDATES — root deficits that, if fixed, would improve
multiple downstream dimensions.

Example relations:
  weak context_carryover -> weak implied_intent_inference
  weak uncertainty_signaling -> premature commitment (contradiction_handling)
  weak framing_selection -> coherence_maintenance drift
  weak boundary_calibration -> bad misunderstanding_repair timing
  weak perspective_integration -> ambiguity_handling collapse

Authors: Sunni (Sir) Morningstar and Cael Devo
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from aurora_internal.aurora_conversation_rubric_engine import RUBRIC_DIMENSIONS


# ============================================================================
# INFLUENCE EDGES — the hardcoded causal structure
# ============================================================================

# (source_dimension, target_dimension, influence_weight)
# Meaning: weakness in source CAUSES weakness in target.
# Weight: how strong the causal link is (0.0 to 1.0).

INFLUENCE_EDGES: List[Tuple[str, str, float]] = [
    # Context carryover failures cascade
    ("context_carryover", "implied_intent_inference", 0.8),
    ("context_carryover", "multi_turn_stability", 0.7),
    ("context_carryover", "coherence_maintenance", 0.6),

    # Uncertainty signaling failures cascade
    ("uncertainty_signaling", "contradiction_handling", 0.7),
    ("uncertainty_signaling", "ambiguity_handling", 0.5),
    ("uncertainty_signaling", "misunderstanding_repair", 0.4),

    # Framing selection failures cascade
    ("framing_selection", "coherence_maintenance", 0.6),
    ("framing_selection", "compression_elaboration_fit", 0.7),
    ("framing_selection", "adaptive_strategy_selection", 0.5),

    # Boundary calibration failures cascade
    ("boundary_calibration", "misunderstanding_repair", 0.6),
    ("boundary_calibration", "emotional_calibration", 0.5),
    ("boundary_calibration", "compression_elaboration_fit", 0.4),

    # Perspective integration failures cascade
    ("perspective_integration", "ambiguity_handling", 0.7),
    ("perspective_integration", "implied_intent_inference", 0.5),
    ("perspective_integration", "emotional_calibration", 0.4),

    # Semantic precision failures cascade
    ("semantic_precision", "coherence_maintenance", 0.5),
    ("semantic_precision", "framing_selection", 0.4),

    # Emotional calibration interactions
    ("emotional_calibration", "boundary_calibration", 0.3),
    ("emotional_calibration", "misunderstanding_repair", 0.4),

    # Adaptive strategy selection interactions
    ("adaptive_strategy_selection", "multi_turn_stability", 0.5),
    ("adaptive_strategy_selection", "compression_elaboration_fit", 0.4),

    # Coherence as a foundation
    ("coherence_maintenance", "multi_turn_stability", 0.6),
]


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


# ============================================================================
# OUTPUT DATACLASS
# ============================================================================

@dataclass
class RubricInfluenceAssessment:
    """
    Relational assessment of rubric dimension weaknesses.

    primary_dimensions: root deficits (causes)
    secondary_dimensions: downstream symptoms
    leverage_candidates: dimensions where intervention yields max improvement
    rationale: human-readable explanation of the analysis
    """
    primary_dimensions: Dict[str, float] = field(default_factory=dict)
    secondary_dimensions: Dict[str, float] = field(default_factory=dict)
    leverage_candidates: Dict[str, float] = field(default_factory=dict)
    rationale: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary_dimensions": dict(self.primary_dimensions),
            "secondary_dimensions": dict(self.secondary_dimensions),
            "leverage_candidates": dict(self.leverage_candidates),
            "rationale": list(self.rationale),
        }


# ============================================================================
# MAIN ENGINE
# ============================================================================

class RubricInfluenceGraph:
    """
    Analyzes rubric dimension scores through a causal influence graph.

    Given a set of dimension scores, identifies:
    1. Which dimensions are ROOT deficits (upstream causes)
    2. Which dimensions are SYMPTOMS (downstream of root deficits)
    3. Which dimensions are LEVERAGE CANDIDATES (fix these for max impact)
    """

    # Weakness threshold: dimensions below this are considered weak
    WEAKNESS_THRESHOLD: float = 0.45

    def __init__(self):
        # Build adjacency structures
        self._outgoing: Dict[str, List[Tuple[str, float]]] = {
            d: [] for d in RUBRIC_DIMENSIONS
        }
        self._incoming: Dict[str, List[Tuple[str, float]]] = {
            d: [] for d in RUBRIC_DIMENSIONS
        }
        for src, tgt, weight in INFLUENCE_EDGES:
            self._outgoing[src].append((tgt, weight))
            self._incoming[tgt].append((src, weight))

    def analyze(
        self,
        dimension_scores: Dict[str, float],
        weakness_threshold: Optional[float] = None,
    ) -> RubricInfluenceAssessment:
        """
        Analyze dimension scores to identify root deficits, symptoms,
        and leverage candidates.
        """
        threshold = weakness_threshold or self.WEAKNESS_THRESHOLD

        # Identify weak dimensions
        weak_dims: Dict[str, float] = {
            dim: score for dim, score in dimension_scores.items()
            if score < threshold and dim in set(RUBRIC_DIMENSIONS)
        }

        if not weak_dims:
            return RubricInfluenceAssessment(
                rationale=["No dimensions below weakness threshold."]
            )

        # Classify: primary (root) vs secondary (symptom)
        primary: Dict[str, float] = {}
        secondary: Dict[str, float] = {}
        rationale: List[str] = []

        for dim, score in weak_dims.items():
            # Is this dimension explained by an upstream weakness?
            upstream_explanation = 0.0
            upstream_sources: List[str] = []
            for src, weight in self._incoming.get(dim, []):
                if src in weak_dims:
                    upstream_explanation += weight * (threshold - weak_dims[src])
                    upstream_sources.append(src)

            if upstream_explanation > 0.15 and upstream_sources:
                # This weakness is at least partially explained by upstream weaknesses
                secondary[dim] = score
                rationale.append(
                    f"{dim} (score={score:.2f}) is downstream of "
                    f"{', '.join(upstream_sources)}"
                )
            else:
                # This weakness has no strong upstream explanation — it's a root deficit
                primary[dim] = score
                rationale.append(
                    f"{dim} (score={score:.2f}) is a root deficit"
                )

        # Compute leverage scores
        leverage: Dict[str, float] = {}
        for dim in primary:
            # How many downstream dimensions would improve if this gets fixed?
            downstream_impact = 0.0
            affected: List[str] = []
            for tgt, weight in self._outgoing.get(dim, []):
                tgt_score = dimension_scores.get(tgt, 0.5)
                if tgt_score < 0.6:  # Room for improvement
                    downstream_impact += weight * (0.6 - tgt_score)
                    affected.append(tgt)

            # Leverage = own weakness depth + downstream improvement potential
            own_depth = threshold - primary[dim]
            leverage[dim] = _clamp(own_depth + downstream_impact, 0.0, 2.0)

            if affected:
                rationale.append(
                    f"Fixing {dim} would improve: {', '.join(affected)} "
                    f"(leverage={leverage[dim]:.2f})"
                )

        # Sort leverage by score
        leverage = dict(sorted(leverage.items(), key=lambda kv: kv[1], reverse=True))

        return RubricInfluenceAssessment(
            primary_dimensions=primary,
            secondary_dimensions=secondary,
            leverage_candidates=leverage,
            rationale=rationale,
        )

    def trace_downstream(self, dimension: str, depth: int = 3) -> List[Tuple[str, float]]:
        """
        Trace all downstream dimensions affected by a given dimension.
        Returns (dimension, cumulative_weight) pairs.
        """
        visited: Set[str] = set()
        result: List[Tuple[str, float]] = []

        def _walk(dim: str, cumulative_weight: float, remaining_depth: int):
            if remaining_depth <= 0 or dim in visited:
                return
            visited.add(dim)
            for tgt, weight in self._outgoing.get(dim, []):
                effective = cumulative_weight * weight
                if effective > 0.05:  # Prune negligible paths
                    result.append((tgt, effective))
                    _walk(tgt, effective, remaining_depth - 1)

        _walk(dimension, 1.0, depth)
        return sorted(result, key=lambda x: x[1], reverse=True)

    def trace_upstream(self, dimension: str, depth: int = 3) -> List[Tuple[str, float]]:
        """
        Trace all upstream dimensions that influence a given dimension.
        Returns (dimension, cumulative_weight) pairs.
        """
        visited: Set[str] = set()
        result: List[Tuple[str, float]] = []

        def _walk(dim: str, cumulative_weight: float, remaining_depth: int):
            if remaining_depth <= 0 or dim in visited:
                return
            visited.add(dim)
            for src, weight in self._incoming.get(dim, []):
                effective = cumulative_weight * weight
                if effective > 0.05:
                    result.append((src, effective))
                    _walk(src, effective, remaining_depth - 1)

        _walk(dimension, 1.0, depth)
        return sorted(result, key=lambda x: x[1], reverse=True)

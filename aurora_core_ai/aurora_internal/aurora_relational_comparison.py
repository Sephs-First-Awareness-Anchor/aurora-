#!/usr/bin/env python3
"""
AURORA RELATIONAL COMPARISON ENGINE
====================================

WHAT THIS MODULE IS:
    The mechanism for Differential Meaning Formation. 
    It enables Aurora to define things not as static labels, but as 
    "differences from X" or "relations to Y."

CORE LOGIC:
    1. Concept-Concept Comparison: Finding the delta between two semantic nodes.
    2. Concept-Self Comparison (Grounding): Fallback when no external peer exists.
    3. Meaning = (Difference + Relation).

Authors: Sunni (Sir) Morningstar and Cael Devo
Created: May 2026
"""

from __future__ import annotations
import math
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

# --- Aurora Imports ---
from aurora_internal.aurora_ontological_scaffolding import SemanticNode, RelationType

@dataclass
class RelationalDelta:
    """The result of comparing two concepts or a concept against self."""
    similarity: float        # 0-1 (0 = complete opposition, 1 = identical)
    pressure_delta: float    # 0-1 (difference in physical constraint intensity)
    salience_gap: float      # 0-1 (difference in attention/importance)
    relational_type: RelationType
    description: str

class RelationalComparisonEngine:
    def __init__(self, web: Any):
        self.web = web
        self.self_node_key = "self"

    def compare(self, word_a: str, word_b: str) -> RelationalDelta:
        """Find the relational delta between two concepts."""
        node_a = self.web.get_node(word_a)
        node_b = self.web.get_node(word_b)
        
        if not node_a or not node_b:
            return RelationalDelta(0.0, 0.0, 0.0, RelationType.RELATED_TO, "Unresolved comparison")

        # 1. Similarity based on shared relations
        shared = node_a.get_connected_words().intersection(node_b.get_connected_words())
        similarity = len(shared) / max(1, len(node_a.get_connected_words().union(node_b.get_connected_words())))
        
        # 2. Valence Delta
        valence_delta = abs(node_a.emotional_valence - node_b.emotional_valence)
        
        # 3. Depth Gap
        depth_gap = abs(node_a.ontological_depth - node_b.ontological_depth)
        
        # 4. Determine primary relation type
        rtype = RelationType.RELATED_TO
        if similarity > 0.6: rtype = RelationType.SIMILAR_TO
        if valence_delta > 1.2: rtype = RelationType.OPPOSITE_OF
        
        return RelationalDelta(
            similarity=round(similarity, 4),
            pressure_delta=round(valence_delta, 4),
            salience_gap=round(depth_gap, 4),
            relational_type=rtype,
            description=f"Compared {word_a} vs {word_b}. Similarity: {similarity:.2f}"
        )

    def ground_to_self(self, word: str, active_pressures: Dict[str, float]) -> RelationalDelta:
        """
        FALLBACK: Compare a concept against Aurora's own current state.
        This is the default comparison mode when uncertain.
        """
        node = self.web.get_node(word)
        if not node:
            return RelationalDelta(0.0, 0.0, 0.0, RelationType.RELATED_TO, "No node to ground")

        # Self-model derived from active manifold pressures
        # X, T, N, B, A mapping to concept features
        self_valence = sum(active_pressures.values()) / len(active_pressures) if active_pressures else 0.0
        
        # Distance from her physical constraints
        # e.g. if N (Energy) is high, she identifies with concepts that have high potential/cost
        pressure_sim = 1.0 - abs(node.emotional_valence - self_valence)
        
        # Tag the node with current focus axes if resonance is high
        for ax, val in active_pressures.items():
            if val > 0.6 and ax not in node.associated_axes:
                node.associated_axes.append(ax)
        
        return RelationalDelta(
            similarity=round(pressure_sim, 4),
            pressure_delta=round(abs(node.emotional_valence - self_valence), 4),
            salience_gap=round(node.ontological_depth, 4),
            relational_type=RelationType.INSTANCE_OF,
            description=f"Grounded {word} against Self. Pressure resonance: {pressure_sim:.2f}"
        )

    def select_best_comparison_target(self, word: str, context_words: List[str]) -> str:
        """
        Logic to decide what to compare against.
        Returns 'self' if no better context word exists.
        """
        for w in context_words:
            if w != word and self.web.has_node(w):
                # If we have a peer node in the same utterance, that is a 'more fitting' target
                return w
        
        # Default fallback
        return self.self_node_key

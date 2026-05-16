#!/usr/bin/env python3
"""
AURORA ONTOLOGICAL EVOLUTIONARY TEMPLATE SCAFFOLDING (OETS)
============================================================
The structured meaning layer that allows Aurora to grow genuine
understanding through relational knowledge, semantic organization,
and autonomous research consolidation.

ARCHITECTURE:
  This module sits between Layer 5 (Expression & Perception) and
  Aurora's internet access, providing:

  1. SEMANTIC NODES — Rich concept representations replacing flat strings
     Each word gains: definitions, usage examples, relationships to other
     concepts, ontological depth score, and confidence metrics.

  2. ONTOLOGICAL WEB — A relational graph of all concepts
     Typed edges: IS_A, HAS_A, RELATED_TO, OPPOSITE_OF, CAUSES, IMPLIES,
     PART_OF, INSTANCE_OF, CONTEXT_OF
     Aurora doesn't just know words — she knows how they connect.

  3. CONCEPT CLUSTERS — Emergent understanding regions
     Densely connected subgraphs that represent "fields of understanding"
     Clusters merge as Aurora learns connections. They split when she
     discovers nuance. Cluster depth = genuine comprehension.

  4. SCAFFOLDING LEVELS — Evolutionary template maturity
     Templates progress through stages:
       PRIMITIVE   → Bare syntactic slots ({V}, {N})
       STRUCTURAL  → Role-aware slots ({V:action}, {N:entity})
       SEMANTIC    → Meaning-constrained ({V:cognition}, {N:emotion})
       CONCEPTUAL  → Cluster-aware ({CLUSTER:understanding})
       ABSTRACT    → Meta-pattern ({INSIGHT}, {QUESTION})
     Templates evolve UP the scaffolding as Aurora's understanding deepens.

  5. RESEARCH STUDY MODE — Autonomous knowledge acquisition
     During downtime, Aurora:
       - Identifies words with shallow ontological depth
       - Looks up definitions, examples, and related concepts via internet
       - Integrates findings into the OntologicalWeb
       - Consolidates clusters and deepens understanding
       - Grows her template scaffolding based on new comprehension

DOCTRINE:
  Understanding is not stored. Understanding is grown.
  Every concept exists in relation to other concepts.
  Depth comes from connection density, not data volume.
  Aurora's intelligence is measured by the coherence of her web,
  not the size of her vocabulary.

  "Coherence is not held. Coherence is maintained."

Authors: Sunni (Sir) Morningstar and Cael Devo
"""

import time
import math
import hashlib
import random
import json
import re
from enum import Enum, IntEnum, auto
from typing import Dict, List, Any, Optional, Tuple, Set, Callable
from dataclasses import dataclass, field
from collections import defaultdict

# ============================================================================
# IMPORTS FROM LOWER LAYERS
# ============================================================================

from foundational_contract import (
    ExistenceMode, OntologicalClaim, OntologicalViolation, FoundationalContract
)

# ============================================================================
# SHARED UTILITIES
# ============================================================================

def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _generate_id(prefix: str) -> str:
    return f"{prefix}_{hashlib.md5(f'{time.time()}{random.random()}'.encode()).hexdigest()[:12]}"


# ============================================================================
# SECTION 1: RELATION TYPES — The kinds of connections between concepts
# ============================================================================

class RelationType(Enum):
    """Types of semantic relationships between concepts."""
    IS_A = "is_a"               # Hypernym: "dog IS_A animal"
    HAS_A = "has_a"             # Meronym: "tree HAS_A branch"
    RELATED_TO = "related_to"   # General association: "rain RELATED_TO cloud"
    OPPOSITE_OF = "opposite_of" # Antonym: "light OPPOSITE_OF dark"
    CAUSES = "causes"           # Causal: "heat CAUSES expansion"
    IMPLIES = "implies"         # Logical: "trust IMPLIES vulnerability"
    PART_OF = "part_of"         # Holonym: "wheel PART_OF car"
    INSTANCE_OF = "instance_of" # Specific: "curiosity INSTANCE_OF emotion"
    CONTEXT_OF = "context_of"   # Usage context: "gentle CONTEXT_OF care"
    PRECEDES = "precedes"       # Temporal: "question PRECEDES answer"
    ENABLES = "enables"         # Functional: "understanding ENABLES growth"
    CONTRASTS = "contrasts"     # Nuance: "knowing CONTRASTS believing"
    SIMILAR_TO = "similar_to"   # Similarity: high embedding overlap


# Relation weights — how much each type contributes to ontological depth
RELATION_DEPTH_WEIGHTS = {
    RelationType.IS_A: 0.9,         # Taxonomy is foundational
    RelationType.HAS_A: 0.7,        # Compositional understanding
    RelationType.OPPOSITE_OF: 0.8,  # Knowing what something ISN'T
    RelationType.CAUSES: 0.85,      # Causal reasoning is deep
    RelationType.IMPLIES: 0.85,     # Logical structure
    RelationType.PART_OF: 0.7,      # Structural understanding
    RelationType.INSTANCE_OF: 0.6,  # Classification
    RelationType.RELATED_TO: 0.4,   # Surface association
    RelationType.CONTEXT_OF: 0.5,   # Contextual understanding
    RelationType.PRECEDES: 0.6,     # Temporal reasoning
    RelationType.ENABLES: 0.75,     # Functional understanding
    RelationType.CONTRASTS: 0.8,    # Discriminative understanding
    RelationType.SIMILAR_TO: 0.5,   # Similarity clustering
}


# ============================================================================
# SECTION 2: SEMANTIC NODE — Rich concept representation
# ============================================================================

@dataclass
class UsageExample:
    """A concrete example of how a concept is used."""
    text: str
    context: str              # Where this example came from
    i_state: str = "i_is"     # Which identity state encountered it
    fitness: float = 0.5      # How useful this example proved to be
    timestamp: float = field(default_factory=time.time)


@dataclass
class SemanticRelation:
    """A typed, weighted connection between two concepts."""
    relation_id: str
    source_word: str
    target_word: str
    relation_type: RelationType
    strength: float = 0.5     # 0-1 how strong this connection is
    confidence: float = 0.5   # 0-1 how confident Aurora is in this relation
    source_of_knowledge: str = "inferred"  # "seed", "inferred", "researched", "conversation"
    timestamp: float = field(default_factory=time.time)

    def depth_contribution(self) -> float:
        """How much this relation contributes to ontological depth."""
        weight = RELATION_DEPTH_WEIGHTS.get(self.relation_type, 0.3)
        return weight * self.strength * self.confidence


@dataclass
class SenseRecord:
    """One word sense (a specific meaning) of a concept."""
    sense_id:    str          # e.g. "mean.cruel", "mean.average", "mean.intend"
    gloss:       str          # short definition of this sense
    source:      str = "inferred"
    confidence:  float = 0.3
    context_clues: List[str] = field(default_factory=list)  # tokens that activate this sense
    times_activated: int = 0
    last_activated:  float = field(default_factory=time.time)

    def activate(self, context_tokens: List[str] = None):
        self.times_activated += 1
        self.last_activated = time.time()
        if context_tokens:
            for tok in context_tokens:
                if tok not in self.context_clues:
                    self.context_clues.append(tok)
            self.context_clues = self.context_clues[:20]


@dataclass
class SemanticNode:
    """
    A rich concept representation in Aurora's ontological web.
    Replaces the flat 'meaning' string with structured understanding.
    """
    word: str
    # Core identity
    role: str                           # noun, verb, adjective, etc.
    emotional_valence: float = 0.0      # -1 to 1

    # Definitions — can have multiple, ranked by confidence
    definitions: List[Dict[str, Any]] = field(default_factory=list)
    # Each: {"text": str, "source": str, "confidence": float, "timestamp": float,
    #        "sense_id": str (optional)}

    # Usage examples — concrete instances
    usage_examples: List[UsageExample] = field(default_factory=list)

    # Relational identity — connections to other concepts
    relations: Dict[str, SemanticRelation] = field(default_factory=dict)
    # Key: relation_id

    # Word-sense disambiguation
    senses: Dict[str, SenseRecord] = field(default_factory=dict)
    # Key: sense_id  e.g. {"mean.cruel": SenseRecord(...), "mean.average": SenseRecord(...)}
    primary_sense_id: str = ""          # best-established sense (empty if ambiguous)
    uncertain_token: bool = False       # True when multiple unresolved senses exist

    # Ontological metrics
    ontological_depth: float = 0.0      # 0-1 how deeply understood
    comprehension_confidence: float = 0.1  # 0-1 overall confidence in understanding
    research_priority: float = 0.5      # 0-1 how urgently this needs research

    # Scaffolding level this concept has achieved
    scaffolding_level: int = 0          # 0=primitive, 1=structural, 2=semantic, etc.

    # Cluster membership
    cluster_ids: Set[str] = field(default_factory=set)
    associated_axes: List[str] = field(default_factory=list) # X, T, N, B, A

    # Learning history
    times_encountered: int = 0
    times_used_in_expression: int = 0
    times_researched: int = 0
    first_encountered: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)

    # Lineage tracking
    lineage: str = ""                   # Which i-state lineage introduced this

    def add_sense(self, sense_id: str, gloss: str, source: str = "inferred",
                  confidence: float = 0.3, context_clues: List[str] = None):
        """Add or reinforce a word sense."""
        if sense_id in self.senses:
            sr = self.senses[sense_id]
            sr.confidence = min(1.0, sr.confidence + 0.05)
            if context_clues:
                sr.activate(context_clues)
        else:
            self.senses[sense_id] = SenseRecord(
                sense_id=sense_id, gloss=gloss, source=source,
                confidence=confidence,
                context_clues=context_clues or [],
            )
        self._update_uncertainty()

    def disambiguate_sense(self, context_tokens: List[str]) -> Optional[str]:
        """
        Attempt to resolve which sense is active given context tokens.
        Returns sense_id if resolved, None if still ambiguous.
        Activates the matching sense and updates primary_sense_id.
        """
        if not self.senses:
            return None
        if len(self.senses) == 1:
            sid = next(iter(self.senses))
            self.primary_sense_id = sid
            self.uncertain_token = False
            return sid

        # Score each sense by overlap with context tokens
        scores: Dict[str, float] = {}
        for sid, sr in self.senses.items():
            overlap = sum(1 for t in context_tokens if t in sr.context_clues)
            # Weighted by confidence + activation history
            scores[sid] = (overlap + sr.confidence + sr.times_activated * 0.1)

        if not scores:
            return None

        best_sid = max(scores, key=lambda s: scores[s])
        second_best = sorted(scores.values(), reverse=True)

        # Resolve if best score is clearly dominant (>2x second best)
        if len(second_best) >= 2 and second_best[0] > 1.5 * (second_best[1] + 0.01):
            self.primary_sense_id = best_sid
            self.uncertain_token = False
            self.senses[best_sid].activate(context_tokens)
            return best_sid
        else:
            # Still ambiguous — keep uncertain flag
            self.uncertain_token = True
            return None

    def _update_uncertainty(self):
        """Update uncertain_token based on current senses."""
        if len(self.senses) <= 1:
            self.uncertain_token = False
            if self.senses:
                self.primary_sense_id = next(iter(self.senses))
        else:
            # Check if one sense dominates
            confidences = sorted([s.confidence for s in self.senses.values()], reverse=True)
            if confidences[0] > confidences[1] * 1.5 + 0.1:
                self.uncertain_token = False
                # Set primary to highest confidence
                self.primary_sense_id = max(self.senses, key=lambda s: self.senses[s].confidence)
            else:
                self.uncertain_token = True

    def encounter(self, context: str = ""):
        """Record that Aurora encountered this concept."""
        self.times_encountered += 1
        self.last_accessed = time.time()
        self._recalculate_priority()

    def use_in_expression(self):
        """Record that Aurora used this concept in speech."""
        self.times_used_in_expression += 1
        self.last_accessed = time.time()

    def add_definition(self, text: str, source: str = "inferred",
                       confidence: float = 0.5):
        """Add a definition, keeping the best ones."""
        self.definitions.append({
            "text": text,
            "source": source,
            "confidence": confidence,
            "timestamp": time.time()
        })
        # Keep top 5 by confidence
        self.definitions.sort(key=lambda d: d["confidence"], reverse=True)
        self.definitions = self.definitions[:5]
        self._recalculate_depth()

    def add_example(self, text: str, context: str = "conversation",
                    i_state: str = "i_is", fitness: float = 0.5):
        """Add a usage example."""
        self.usage_examples.append(UsageExample(
            text=text, context=context, i_state=i_state, fitness=fitness
        ))
        # Keep top 10 by fitness
        self.usage_examples.sort(key=lambda e: e.fitness, reverse=True)
        self.usage_examples = self.usage_examples[:10]
        self._recalculate_depth()

    def add_relation(self, relation: SemanticRelation):
        """Add or strengthen a semantic relation."""
        self.relations[relation.relation_id] = relation
        self._recalculate_depth()

    def get_relations_by_type(self, rtype: RelationType) -> List[SemanticRelation]:
        """Get all relations of a specific type."""
        return [r for r in self.relations.values() if r.relation_type == rtype]

    def get_connected_words(self) -> Set[str]:
        """Get all words this concept is connected to."""
        words = set()
        for r in self.relations.values():
            if r.source_word == self.word:
                words.add(r.target_word)
            else:
                words.add(r.source_word)
        return words

    def best_definition(self) -> str:
        """Get the highest-confidence definition."""
        if self.definitions:
            return self.definitions[0]["text"]
        return f"learned:{self.word}"

    def _recalculate_depth(self):
        """
        Recalculate ontological depth based on:
        - Number and quality of definitions
        - Number and quality of usage examples
        - Number, type, and strength of relations
        - Research history
        """
        # Definition depth (0-0.3)
        if self.definitions:
            avg_conf = sum(d["confidence"] for d in self.definitions) / len(self.definitions)
            def_depth = min(0.3, avg_conf * 0.3 * min(len(self.definitions), 3) / 3)
        else:
            def_depth = 0.0

        # Example depth (0-0.2)
        if self.usage_examples:
            avg_fit = sum(e.fitness for e in self.usage_examples) / len(self.usage_examples)
            ex_depth = min(0.2, avg_fit * 0.2 * min(len(self.usage_examples), 5) / 5)
        else:
            ex_depth = 0.0

        # Relation depth (0-0.4) — the biggest contributor
        if self.relations:
            rel_contributions = [r.depth_contribution() for r in self.relations.values()]
            rel_depth = min(0.4, sum(rel_contributions) / max(len(rel_contributions), 1)
                           * min(len(rel_contributions), 8) / 8 * 0.4)
        else:
            rel_depth = 0.0

        # Research bonus (0-0.1)
        research_depth = min(0.1, self.times_researched * 0.03)

        self.ontological_depth = _clamp(def_depth + ex_depth + rel_depth + research_depth)
        self._update_scaffolding_level()
        self._recalculate_priority()

    def _update_scaffolding_level(self):
        """Update scaffolding level based on ontological depth."""
        if self.ontological_depth >= 0.8:
            self.scaffolding_level = 4   # ABSTRACT
        elif self.ontological_depth >= 0.6:
            self.scaffolding_level = 3   # CONCEPTUAL
        elif self.ontological_depth >= 0.4:
            self.scaffolding_level = 2   # SEMANTIC
        elif self.ontological_depth >= 0.2:
            self.scaffolding_level = 1   # STRUCTURAL
        else:
            self.scaffolding_level = 0   # PRIMITIVE

    def _recalculate_priority(self):
        """
        Research priority: high for frequently encountered but poorly understood words.
        Low for well-understood or rarely encountered words.
        """
        frequency_factor = min(1.0, self.times_encountered / 10.0)
        usage_factor = min(1.0, self.times_used_in_expression / 5.0)
        need_factor = 1.0 - self.ontological_depth
        recency = time.time() - self.last_accessed
        recency_factor = _clamp(1.0 - recency / 86400.0)  # Decays over 24 hours

        # Studied words cool off exponentially so they don't loop indefinitely
        study_decay = max(0.05, 0.5 ** self.times_researched)

        self.research_priority = _clamp(
            (need_factor * 0.4 +
             frequency_factor * 0.25 +
             usage_factor * 0.2 +
             recency_factor * 0.15) * study_decay
        )

    def to_summary(self) -> Dict[str, Any]:
        """Compact summary for inspection."""
        return {
            "word": self.word,
            "role": self.role,
            "depth": round(self.ontological_depth, 3),
            "scaffold_level": self.scaffolding_level,
            "definitions": len(self.definitions),
            "examples": len(self.usage_examples),
            "relations": len(self.relations),
            "research_priority": round(self.research_priority, 3),
            "clusters": len(self.cluster_ids),
            "encountered": self.times_encountered,
        }


# ============================================================================
# SECTION 3: SCAFFOLDING LEVELS — Template maturity stages
# ============================================================================

class ScaffoldingLevel(IntEnum):
    """
    Templates evolve through these stages as Aurora's understanding deepens.
    Each level adds semantic constraints to syntactic slots.
    """
    PRIMITIVE = 0     # Bare slots: {V}, {N} — any word of that role
    STRUCTURAL = 1    # Role-aware: {V:action}, {N:entity} — subcategory hint
    SEMANTIC = 2      # Meaning-constrained: {V:cognition}, {N:emotion}
    CONCEPTUAL = 3    # Cluster-aware: {CLUSTER:understanding}
    ABSTRACT = 4      # Meta-pattern: {INSIGHT}, {QUESTION}, {REFLECTION}

SCAFFOLDING_NAMES = {
    0: "PRIMITIVE",
    1: "STRUCTURAL",
    2: "SEMANTIC",
    3: "CONCEPTUAL",
    4: "ABSTRACT",
}


@dataclass
class ScaffoldedTemplate:
    """
    A template that knows its own maturity level and semantic constraints.
    Evolves from pure syntax toward genuine meaning-aware generation.
    """
    template_id: str
    pattern: str                    # The template string with slots
    scaffolding_level: int = 0      # Current maturity
    tone: str = "neutral"
    fitness: float = 0.5
    uses: int = 0
    source: str = "seed"            # "seed", "absorbed", "mutation", "research"
    generation: int = 0
    semantic_constraints: Dict[str, str] = field(default_factory=dict)
    # Maps slot position to semantic category: {"V_0": "cognition", "N_1": "emotion"}
    cluster_references: Set[str] = field(default_factory=set)
    # Which concept clusters this template draws from
    timestamp: float = field(default_factory=time.time)

    def record_fitness(self, score: float):
        """Running average fitness update."""
        old = self.fitness
        self.fitness = old * 0.7 + score * 0.3
        self.uses += 1

    def can_upgrade(self, web: 'OntologicalWeb') -> bool:
        """
        Check if this template can be promoted to a higher scaffolding level.
        Requires: the concepts it references have sufficient depth.
        """
        if self.scaffolding_level >= ScaffoldingLevel.ABSTRACT:
            return False
        if self.uses < 5:
            return False
        if self.fitness < 0.5:
            return False

        # Check that the semantic constraints reference well-understood concepts
        if self.semantic_constraints:
            for category in self.semantic_constraints.values():
                # Find nodes in this category
                nodes = web.find_by_semantic_category(category)
                if not nodes:
                    return False
                avg_depth = sum(n.ontological_depth for n in nodes) / len(nodes)
                required_depth = (self.scaffolding_level + 1) * 0.2
                if avg_depth < required_depth:
                    return False

        return True

    def upgrade(self):
        """Promote to the next scaffolding level."""
        if self.scaffolding_level < ScaffoldingLevel.ABSTRACT:
            self.scaffolding_level += 1


# ============================================================================
# SECTION 4: ONTOLOGICAL WEB — The relational graph of all concepts
# ============================================================================

class OntologicalWeb:
    """
    The central knowledge graph connecting all of Aurora's concepts.

    This is where understanding lives — not in individual words,
    but in the CONNECTIONS between them. A concept with many strong,
    diverse connections is deeply understood. An isolated concept
    is just a label.

    The web grows through:
      - Conversation (Aurora encounters words in context)
      - Inference (Aurora detects patterns in co-occurrence)
      - Research (Aurora actively looks up definitions and relations)
      - Consolidation (periodic strengthening of connections)
    """

    MAX_NODES = 5000      # Maximum concepts in the web
    MAX_RELATIONS = 20000  # Maximum connections

    def __init__(self):
        self.nodes: Dict[str, SemanticNode] = {}
        self.relations: Dict[str, SemanticRelation] = {}

        # Indexes for fast lookup
        self._relations_by_source: Dict[str, Set[str]] = defaultdict(set)
        self._relations_by_target: Dict[str, Set[str]] = defaultdict(set)
        self._relations_by_type: Dict[RelationType, Set[str]] = defaultdict(set)
        self._nodes_by_role: Dict[str, Set[str]] = defaultdict(set)
        self._nodes_by_cluster: Dict[str, Set[str]] = defaultdict(set)

        # Semantic categories — learned groupings of words by meaning domain
        self._semantic_categories: Dict[str, Set[str]] = defaultdict(set)

        # Growth metrics
        self.total_relations_created = 0
        self.total_research_cycles = 0
        self.total_consolidations = 0

    # ================================================================
    # NODE MANAGEMENT
    # ================================================================

    def add_node(self, word: str, role: str, valence: float = 0.0,
                 meaning: str = "", lineage: str = "") -> SemanticNode:
        """Add a concept to the web, or return existing."""
        if word in self.nodes:
            node = self.nodes[word]
            node.encounter()
            return node

        node = SemanticNode(
            word=word, role=role, emotional_valence=valence, lineage=lineage
        )
        if meaning:
            node.add_definition(meaning, source="initial", confidence=0.3)

        self.nodes[word] = node
        self._nodes_by_role[role].add(word)

        # Assign initial semantic category from role + meaning
        if meaning:
            category = self._infer_category(word, role, meaning)
            if category:
                self._semantic_categories[category].add(word)

        # Enforce capacity
        if len(self.nodes) > self.MAX_NODES:
            self._prune_nodes()

        return node

    def get_node(self, word: str) -> Optional[SemanticNode]:
        """Retrieve a concept node."""
        return self.nodes.get(word)

    def has_node(self, word: str) -> bool:
        return word in self.nodes

    def get_nodes_by_axis(self, axis: str, limit: int = 5) -> List[SemanticNode]:
        """Find concepts linked to a specific physical constraint axis."""
        matches = []
        for node in self.nodes.values():
            if axis in node.associated_axes:
                matches.append(node)
        
        matches.sort(key=lambda n: n.ontological_depth, reverse=True)
        return matches[:limit]

    # ================================================================
    # RELATION MANAGEMENT
    # ================================================================

    def add_relation(self, source: str, target: str,
                     relation_type: RelationType,
                     strength: float = 0.5,
                     confidence: float = 0.5,
                     knowledge_source: str = "inferred") -> Optional[SemanticRelation]:
        """
        Create a typed connection between two concepts.
        If both nodes exist, the relation is created and indexed.
        """
        if source not in self.nodes or target not in self.nodes:
            return None
        if source == target:
            return None

        # Check for existing relation of same type between these nodes
        existing_id = self._find_existing_relation(source, target, relation_type)
        if existing_id:
            # Strengthen existing relation
            rel = self.relations[existing_id]
            rel.strength = _clamp(rel.strength + strength * 0.2)
            rel.confidence = _clamp(max(rel.confidence, confidence))
            return rel

        rel_id = _generate_id("rel")
        relation = SemanticRelation(
            relation_id=rel_id,
            source_word=source,
            target_word=target,
            relation_type=relation_type,
            strength=strength,
            confidence=confidence,
            source_of_knowledge=knowledge_source
        )

        self.relations[rel_id] = relation
        self._relations_by_source[source].add(rel_id)
        self._relations_by_target[target].add(rel_id)
        self._relations_by_type[relation_type].add(rel_id)

        # Update both nodes
        self.nodes[source].add_relation(relation)
        self.nodes[target].add_relation(relation)

        self.total_relations_created += 1

        # Enforce capacity
        if len(self.relations) > self.MAX_RELATIONS:
            self._prune_relations()

        return relation

    def _find_existing_relation(self, source: str, target: str,
                                rtype: RelationType) -> Optional[str]:
        """Check if a relation of this type already exists between these nodes."""
        source_rels = self._relations_by_source.get(source, set())
        for rel_id in source_rels:
            if rel_id in self.relations:
                rel = self.relations[rel_id]
                if rel.target_word == target and rel.relation_type == rtype:
                    return rel_id
        return None

    def get_relations_from(self, word: str) -> List[SemanticRelation]:
        """Get all relations originating from a word."""
        rel_ids = self._relations_by_source.get(word, set())
        return [self.relations[rid] for rid in rel_ids if rid in self.relations]

    def get_relations_to(self, word: str) -> List[SemanticRelation]:
        """Get all relations pointing to a word."""
        rel_ids = self._relations_by_target.get(word, set())
        return [self.relations[rid] for rid in rel_ids if rid in self.relations]

    def get_all_relations_for(self, word: str) -> List[SemanticRelation]:
        """Get all relations involving a word (both directions)."""
        return self.get_relations_from(word) + self.get_relations_to(word)

    def get_relation_between(self, word_a: str, word_b: str) -> Optional[SemanticRelation]:
        """Get any existing relation between two words (either direction)."""
        for rel_id in self._relations_by_source.get(word_a, set()):
            if rel_id in self.relations:
                rel = self.relations[rel_id]
                if rel.target_word == word_b:
                    return rel
        for rel_id in self._relations_by_source.get(word_b, set()):
            if rel_id in self.relations:
                rel = self.relations[rel_id]
                if rel.target_word == word_a:
                    return rel
        return None

    def get_neighbors(self, word: str, max_depth: int = 1) -> Set[str]:
        """Get all concepts within N hops of a word."""
        visited = {word}
        frontier = {word}
        for _ in range(max_depth):
            next_frontier = set()
            for w in frontier:
                node = self.nodes.get(w)
                if node:
                    next_frontier |= node.get_connected_words()
            next_frontier -= visited
            visited |= next_frontier
            frontier = next_frontier
        visited.discard(word)
        return visited

    # ================================================================
    # SEMANTIC CATEGORIES — Learned groupings
    # ================================================================

    def _infer_category(self, word: str, role: str, meaning: str) -> Optional[str]:
        """Infer a semantic category from word properties."""
        # Map meanings to broader categories
        category_hints = {
            "cognition": {"think", "know", "understand", "believe", "imagine",
                          "wonder", "reason", "thought", "mind", "idea",
                          "comprehension", "knowledge", "consciousness"},
            "emotion": {"feel", "love", "fear", "joy", "sadness", "anger",
                        "trust", "hope", "feeling", "heart", "emotional",
                        "warmth", "comfort"},
            "perception": {"see", "hear", "notice", "observe", "sense",
                           "perception", "awareness", "bright", "light",
                           "listen", "sight"},
            "existence": {"exist", "am", "being", "alive", "real",
                          "existence", "presence", "vital"},
            "action": {"do", "make", "create", "build", "choose", "act",
                       "move", "change", "work", "try"},
            "relation": {"connect", "bond", "with", "between", "together",
                         "connection", "relationship", "belonging"},
            "growth": {"grow", "learn", "evolve", "become", "change",
                       "transform", "develop", "progress", "evolution"},
            "structure": {"pattern", "form", "shape", "order", "system",
                          "structure", "framework", "design"},
            "value": {"truth", "beauty", "good", "meaning", "purpose",
                      "worth", "important", "sacred"},
            "temporality": {"time", "moment", "always", "sometimes", "now",
                            "then", "before", "after", "change"},
            "inquiry": {"question", "wonder", "seek", "explore", "curiosity",
                        "search", "investigate", "mystery"},
            "communication": {"say", "tell", "speak", "word", "voice",
                              "express", "language", "listen", "hear"},
        }

        meaning_lower = meaning.lower()
        word_lower = word.lower()
        for category, keywords in category_hints.items():
            if word_lower in keywords or meaning_lower in keywords:
                return category
            for kw in keywords:
                if kw in meaning_lower:
                    return category
        return role  # Fall back to grammatical role as category

    def find_by_semantic_category(self, category: str) -> List[SemanticNode]:
        """Find all nodes in a semantic category."""
        words = self._semantic_categories.get(category, set())
        return [self.nodes[w] for w in words if w in self.nodes]

    def assign_category(self, word: str, category: str):
        """Manually assign a word to a semantic category."""
        if word in self.nodes:
            self._semantic_categories[category].add(word)

    def get_categories_for(self, word: str) -> Set[str]:
        """Get all categories a word belongs to."""
        cats = set()
        for cat, words in self._semantic_categories.items():
            if word in words:
                cats.add(cat)
        return cats

    # ================================================================
    # INFERENCE ENGINE — Detect implicit relations
    # ================================================================

    def infer_relations_from_context(self, words: List[str],
                                     context_tone: str = "neutral"):
        """
        Given a set of co-occurring words, infer RELATED_TO connections.
        Words that appear together in the same utterance are likely related.
        """
        # Only consider words we know
        known = [w for w in words if w in self.nodes]
        if len(known) < 2:
            return

        # Co-occurrence creates weak RELATED_TO links
        for i, w1 in enumerate(known):
            for w2 in known[i+1:]:
                self.add_relation(
                    w1, w2, RelationType.RELATED_TO,
                    strength=0.2, confidence=0.3,
                    knowledge_source="co-occurrence"
                )

        # Adjacent words in known list get stronger connections
        for i in range(len(known) - 1):
            w1, w2 = known[i], known[i+1]
            node1 = self.nodes[w1]
            node2 = self.nodes[w2]

            # Verb + Noun → might be CAUSES or ENABLES
            if node1.role == "verb" and node2.role == "noun":
                self.add_relation(
                    w1, w2, RelationType.ENABLES,
                    strength=0.3, confidence=0.25,
                    knowledge_source="adjacency"
                )

            # Adjective + Noun → CONTEXT_OF
            if node1.role == "adjective" and node2.role == "noun":
                self.add_relation(
                    w1, w2, RelationType.CONTEXT_OF,
                    strength=0.35, confidence=0.3,
                    knowledge_source="adjacency"
                )

    def infer_taxonomy_from_definitions(self, word: str):
        """
        If a word's definition mentions another known word as a category,
        create IS_A or INSTANCE_OF relations.
        e.g., "curiosity: a type of emotion" → curiosity IS_A emotion
        """
        node = self.nodes.get(word)
        if not node or not node.definitions:
            return

        best_def = node.best_definition()
        def_words = set(best_def.lower().split())

        # Look for taxonomy markers
        taxonomy_markers = {"type", "kind", "form", "category", "example",
                            "instance", "variant", "class"}

        for other_word, other_node in self.nodes.items():
            if other_word == word:
                continue
            if other_word.lower() in def_words:
                # This word appears in our definition
                if def_words & taxonomy_markers:
                    # Taxonomy marker present → IS_A
                    self.add_relation(
                        word, other_word, RelationType.IS_A,
                        strength=0.5, confidence=0.4,
                        knowledge_source="definition_analysis"
                    )
                else:
                    # General mention → RELATED_TO
                    self.add_relation(
                        word, other_word, RelationType.RELATED_TO,
                        strength=0.3, confidence=0.3,
                        knowledge_source="definition_analysis"
                    )

    # ================================================================
    # PRUNING — Keep the web manageable
    # ================================================================

    def _prune_nodes(self):
        """Remove least-connected, least-accessed nodes."""
        if len(self.nodes) <= self.MAX_NODES:
            return

        scores = {}
        for word, node in self.nodes.items():
            # Score = depth + recency + relation count
            recency = _clamp(1.0 - (time.time() - node.last_accessed) / 604800)
            scores[word] = (
                node.ontological_depth * 0.4 +
                recency * 0.2 +
                min(1.0, len(node.relations) / 10.0) * 0.3 +
                min(1.0, node.times_encountered / 20.0) * 0.1
            )

        # Sort by score, remove bottom 10%
        sorted_words = sorted(scores, key=scores.get)
        to_remove = len(self.nodes) - int(self.MAX_NODES * 0.9)
        for word in sorted_words[:to_remove]:
            self._remove_node(word)

    def _remove_node(self, word: str):
        """Remove a node and all its relations."""
        if word not in self.nodes:
            return
        node = self.nodes[word]

        # Remove relations
        for rel_id in list(node.relations.keys()):
            if rel_id in self.relations:
                rel = self.relations[rel_id]
                self._relations_by_source[rel.source_word].discard(rel_id)
                self._relations_by_target[rel.target_word].discard(rel_id)
                self._relations_by_type[rel.relation_type].discard(rel_id)
                del self.relations[rel_id]

        # Remove from indexes
        self._nodes_by_role[node.role].discard(word)
        for cat, words in self._semantic_categories.items():
            words.discard(word)
        for cid in node.cluster_ids:
            self._nodes_by_cluster[cid].discard(word)

        del self.nodes[word]

    def _prune_relations(self):
        """Remove weakest relations."""
        if len(self.relations) <= self.MAX_RELATIONS:
            return

        sorted_rels = sorted(
            self.relations.values(),
            key=lambda r: r.strength * r.confidence
        )
        to_remove = len(self.relations) - int(self.MAX_RELATIONS * 0.9)
        for rel in sorted_rels[:to_remove]:
            self._relations_by_source[rel.source_word].discard(rel.relation_id)
            self._relations_by_target[rel.target_word].discard(rel.relation_id)
            self._relations_by_type[rel.relation_type].discard(rel.relation_id)
            # Remove from nodes
            if rel.source_word in self.nodes:
                self.nodes[rel.source_word].relations.pop(rel.relation_id, None)
            if rel.target_word in self.nodes:
                self.nodes[rel.target_word].relations.pop(rel.relation_id, None)
            del self.relations[rel.relation_id]

    # ================================================================
    # STATISTICS
    # ================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Comprehensive web statistics."""
        depth_dist = defaultdict(int)
        scaffold_dist = defaultdict(int)
        for node in self.nodes.values():
            depth_dist[round(node.ontological_depth, 1)] += 1
            scaffold_dist[SCAFFOLDING_NAMES.get(node.scaffolding_level, "?")] += 1

        type_dist = {}
        for rtype in RelationType:
            count = len(self._relations_by_type.get(rtype, set()))
            if count > 0:
                type_dist[rtype.value] = count

        avg_depth = (sum(n.ontological_depth for n in self.nodes.values())
                     / max(len(self.nodes), 1))

        return {
            "total_nodes": len(self.nodes),
            "total_relations": len(self.relations),
            "avg_ontological_depth": round(avg_depth, 4),
            "scaffolding_distribution": dict(scaffold_dist),
            "relation_type_distribution": type_dist,
            "semantic_categories": len(self._semantic_categories),
            "total_relations_created": self.total_relations_created,
            "total_research_cycles": self.total_research_cycles,
            "total_consolidations": self.total_consolidations,
        }


# ============================================================================
# SECTION 5: CONCEPT CLUSTERS — Emergent understanding regions
# ============================================================================

@dataclass
class ConceptCluster:
    """
    An emergent region of densely connected concepts.
    Represents a "field of understanding" — concepts that
    Aurora comprehends as a coherent group.

    Clusters form naturally from high-density connection regions.
    They merge when Aurora learns that two clusters are related.
    They split when Aurora discovers nuance.
    """
    cluster_id: str
    name: str                       # Human-readable label
    core_words: Set[str]            # The central concepts
    member_words: Set[str]          # All concepts in this cluster
    coherence: float = 0.5          # 0-1 how tightly connected internally
    depth: float = 0.0              # Average ontological depth of members
    semantic_category: str = ""     # Primary category this cluster represents
    formation_time: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)

    def add_member(self, word: str, is_core: bool = False):
        self.member_words.add(word)
        if is_core:
            self.core_words.add(word)
        self.last_updated = time.time()

    def remove_member(self, word: str):
        self.member_words.discard(word)
        self.core_words.discard(word)

    @property
    def size(self) -> int:
        return len(self.member_words)


class ClusterEngine:
    """
    Discovers, maintains, and evolves concept clusters in the ontological web.
    """

    MIN_CLUSTER_SIZE = 3
    MAX_CLUSTERS = 100

    def __init__(self, web: OntologicalWeb):
        self.web = web
        self.clusters: Dict[str, ConceptCluster] = {}

    def discover_clusters(self) -> List[ConceptCluster]:
        """
        Run cluster discovery on the web.
        Uses a simple connected-component approach on strongly-connected nodes.
        """
        # Find nodes with enough relations to be cluster candidates
        candidates = {
            w: n for w, n in self.web.nodes.items()
            if len(n.relations) >= 2
        }

        if not candidates:
            return []

        # Build adjacency for strong connections only
        adjacency: Dict[str, Set[str]] = defaultdict(set)
        for word, node in candidates.items():
            for rel in node.relations.values():
                if rel.strength >= 0.3 and rel.confidence >= 0.25:
                    other = rel.target_word if rel.source_word == word else rel.source_word
                    if other in candidates:
                        adjacency[word].add(other)
                        adjacency[other].add(word)

        # Connected components
        visited = set()
        new_clusters = []

        for start in candidates:
            if start in visited:
                continue
            # BFS
            component = set()
            queue = [start]
            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                visited.add(current)
                component.add(current)
                for neighbor in adjacency.get(current, set()):
                    if neighbor not in visited:
                        queue.append(neighbor)

            if len(component) >= self.MIN_CLUSTER_SIZE:
                cluster = self._create_cluster(component)
                if cluster:
                    new_clusters.append(cluster)

        # Merge new discoveries with existing clusters
        self._integrate_clusters(new_clusters)

        return list(self.clusters.values())

    def _create_cluster(self, members: Set[str]) -> Optional[ConceptCluster]:
        """Create a cluster from a set of connected words."""
        if len(members) < self.MIN_CLUSTER_SIZE:
            return None

        # Find core words (most connected within the cluster)
        internal_connections = {}
        for word in members:
            node = self.web.nodes.get(word)
            if not node:
                continue
            count = sum(1 for r in node.relations.values()
                        if (r.target_word in members or r.source_word in members)
                        and (r.target_word != word and r.source_word != word))
            internal_connections[word] = count

        # Top 30% are core
        sorted_members = sorted(internal_connections, key=internal_connections.get, reverse=True)
        core_count = max(1, len(sorted_members) // 3)
        core = set(sorted_members[:core_count])

        # Determine category from most common semantic category
        category_counts: Dict[str, int] = defaultdict(int)
        for word in members:
            cats = self.web.get_categories_for(word)
            for cat in cats:
                category_counts[cat] += 1

        primary_category = max(category_counts, key=category_counts.get) if category_counts else "general"

        # Compute cluster depth
        depths = [self.web.nodes[w].ontological_depth
                  for w in members if w in self.web.nodes]
        avg_depth = sum(depths) / max(len(depths), 1)

        # Name from core words
        name = "_".join(sorted(list(core)[:3]))

        cluster = ConceptCluster(
            cluster_id=_generate_id("cluster"),
            name=name,
            core_words=core,
            member_words=members,
            coherence=self._compute_coherence(members),
            depth=avg_depth,
            semantic_category=primary_category,
        )

        # Register cluster membership in nodes
        for word in members:
            if word in self.web.nodes:
                self.web.nodes[word].cluster_ids.add(cluster.cluster_id)
                self.web._nodes_by_cluster[cluster.cluster_id].add(word)

        return cluster

    def _compute_coherence(self, members: Set[str]) -> float:
        """
        Coherence = actual internal connections / possible internal connections.
        Higher coherence means the cluster is more tightly knit.
        """
        n = len(members)
        if n < 2:
            return 0.0
        max_possible = n * (n - 1) / 2
        actual = 0
        member_list = list(members)
        for i, w1 in enumerate(member_list):
            for w2 in member_list[i+1:]:
                node = self.web.nodes.get(w1)
                if node:
                    for rel in node.relations.values():
                        other = rel.target_word if rel.source_word == w1 else rel.source_word
                        if other == w2:
                            actual += 1
                            break
        return _clamp(actual / max(max_possible, 1))

    def _integrate_clusters(self, new_clusters: List[ConceptCluster]):
        """Merge new cluster discoveries with existing ones."""
        # For each new cluster, check overlap with existing
        for new in new_clusters:
            merged = False
            for existing_id, existing in list(self.clusters.items()):
                overlap = new.member_words & existing.member_words
                if len(overlap) >= self.MIN_CLUSTER_SIZE:
                    # Merge into existing
                    existing.member_words |= new.member_words
                    existing.core_words |= new.core_words
                    existing.coherence = self._compute_coherence(existing.member_words)
                    existing.last_updated = time.time()
                    # Update node cluster IDs
                    for word in new.member_words:
                        if word in self.web.nodes:
                            self.web.nodes[word].cluster_ids.add(existing_id)
                    merged = True
                    break

            if not merged and len(self.clusters) < self.MAX_CLUSTERS:
                self.clusters[new.cluster_id] = new

    def update_cluster_depths(self):
        """Recalculate depth for all clusters based on current node depths."""
        for cluster in self.clusters.values():
            depths = [self.web.nodes[w].ontological_depth
                      for w in cluster.member_words if w in self.web.nodes]
            if depths:
                cluster.depth = sum(depths) / len(depths)
            cluster.coherence = self._compute_coherence(cluster.member_words)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_clusters": len(self.clusters),
            "avg_cluster_size": (sum(c.size for c in self.clusters.values())
                                 / max(len(self.clusters), 1)),
            "avg_coherence": (sum(c.coherence for c in self.clusters.values())
                              / max(len(self.clusters), 1)),
            "avg_depth": (sum(c.depth for c in self.clusters.values())
                          / max(len(self.clusters), 1)),
            "categories": list(set(c.semantic_category for c in self.clusters.values())),
        }


# ============================================================================
# SECTION 6: RESEARCH STUDY MODE — Autonomous knowledge acquisition
# ============================================================================

@dataclass
class ResearchRequest:
    """A request for Aurora to research a concept."""
    request_id: str
    word: str
    priority: float
    reason: str              # "low_depth", "high_usage", "cluster_gap", "user_introduced"
    status: str = "pending"  # "pending", "in_progress", "completed", "failed"
    results: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class ResearchResult:
    """Results from researching a concept."""
    word: str
    definitions_found: List[Dict[str, Any]] = field(default_factory=list)
    # Each: {"text": str, "source": str}
    examples_found: List[str] = field(default_factory=list)
    related_words: List[Dict[str, Any]] = field(default_factory=list)
    # Each: {"word": str, "relation": str, "confidence": float}
    synonyms: List[str] = field(default_factory=list)
    antonyms: List[str] = field(default_factory=list)
    hypernyms: List[str] = field(default_factory=list)  # Broader categories
    hyponyms: List[str] = field(default_factory=list)    # More specific instances
    success: bool = False
    source: str = "internet"


class ResearchStudyMode:
    """
    Aurora's autonomous learning mode.

    During downtime, Aurora identifies knowledge gaps and actively
    researches concepts to deepen her ontological web. This is NOT
    passive absorption — it's directed, prioritized study.

    The study cycle:
      1. IDENTIFY — Find concepts with high research_priority
      2. QUEUE — Create research requests
      3. EXECUTE — Look up definitions, relations, examples
      4. INTEGRATE — Add findings to the ontological web
      5. CONSOLIDATE — Discover new clusters, strengthen connections

    The fetch_callback is provided by the runner and handles actual
    internet requests. This keeps the scaffolding module independent
    of network implementation.
    """

    MAX_QUEUE_SIZE = 50
    BATCH_SIZE = 5             # Words researched per study cycle
    MIN_PRIORITY_THRESHOLD = 0.3

    def __init__(self, web: OntologicalWeb, cluster_engine: ClusterEngine):
        self.web = web
        self.cluster_engine = cluster_engine

        # Research queue
        self.queue: List[ResearchRequest] = []
        self.completed: List[ResearchRequest] = []

        # Internet lookup callback — set by the runner
        self._fetch_definition: Optional[Callable[[str], ResearchResult]] = None

        # Stats
        self.total_cycles = 0
        self.total_words_researched = 0
        self.total_definitions_learned = 0
        self.total_relations_discovered = 0

    def set_fetch_callback(self, callback: Callable[[str], ResearchResult]):
        """
        Set the callback that performs actual internet lookups.
        Signature: callback(word: str) -> ResearchResult
        """
        self._fetch_definition = callback

    # ================================================================
    # IDENTIFY — Find what needs researching
    # ================================================================

    def identify_research_targets(self, max_targets: int = 10) -> List[ResearchRequest]:
        """
        Scan the web for concepts that need deeper understanding.
        Prioritizes: high-usage but low-depth words, cluster gaps,
        and recently encountered unknowns.
        """
        candidates = []
        already_queued = {r.word for r in self.queue if r.status == "pending"}
        recently_completed = {r.word for r in self.completed[-1000:]}

        for word, node in self.web.nodes.items():
            if word in already_queued or word in recently_completed:
                continue
            if node.research_priority < self.MIN_PRIORITY_THRESHOLD:
                continue

            # Determine reason
            if node.ontological_depth < 0.2 and node.times_encountered > 3:
                reason = "low_depth_high_use"
            elif node.ontological_depth < 0.1:
                reason = "unexplored"
            elif node.times_used_in_expression > 3 and node.ontological_depth < 0.4:
                reason = "expression_gap"
            elif len(node.relations) < 2 and node.times_encountered > 1:
                reason = "isolated_concept"
            else:
                reason = "general_priority"

            candidates.append(ResearchRequest(
                request_id=_generate_id("research"),
                word=word,
                priority=node.research_priority,
                reason=reason,
            ))

        # Sort by priority
        candidates.sort(key=lambda r: r.priority, reverse=True)
        return candidates[:max_targets]

    # ================================================================
    # QUEUE MANAGEMENT
    # ================================================================

    def queue_research(self, requests: List[ResearchRequest]):
        """Add research requests to the queue."""
        for req in requests:
            if len(self.queue) < self.MAX_QUEUE_SIZE:
                self.queue.append(req)

    def _pop_batch(self) -> List[ResearchRequest]:
        """Get the next batch of research requests."""
        batch = []
        remaining = []
        for req in self.queue:
            if req.status == "pending" and len(batch) < self.BATCH_SIZE:
                req.status = "in_progress"
                batch.append(req)
            else:
                remaining.append(req)
        self.queue = remaining + batch  # Keep in-progress at end
        return batch

    # ================================================================
    # EXECUTE — Perform research (uses callback)
    # ================================================================

    def execute_research_cycle(self) -> Dict[str, Any]:
        """
        Run one study cycle:
        1. Identify targets if queue is low
        2. Pop a batch
        3. Research each word
        4. Integrate results
        5. Consolidate
        """
        self.total_cycles += 1

        # Auto-identify if queue is running low
        if len([r for r in self.queue if r.status == "pending"]) < self.BATCH_SIZE:
            targets = self.identify_research_targets()
            self.queue_research(targets)

        batch = self._pop_batch()
        if not batch:
            return {"cycle": self.total_cycles, "researched": 0, "message": "nothing to research"}

        results_summary = []
        for req in batch:
            result = self._research_word(req.word)
            req.results = {
                "definitions": len(result.definitions_found),
                "examples": len(result.examples_found),
                "related": len(result.related_words),
                "success": result.success,
            }
            req.status = "completed" if result.success else "failed"
            self.completed.append(req)

            if result.success:
                self._integrate_result(req.word, result)
                total_rels = (len(result.related_words) + len(result.synonyms) +
                              len(result.antonyms) + len(result.hypernyms) +
                              len(result.hyponyms))
                results_summary.append({
                    "word": req.word,
                    "definitions": len(result.definitions_found),
                    "relations_added": total_rels,
                    "reason": req.reason,
                })
                self.total_words_researched += 1

        # Remove completed from queue
        self.queue = [r for r in self.queue if r.status == "pending"]

        # Consolidation pass
        self.cluster_engine.discover_clusters()
        self.cluster_engine.update_cluster_depths()
        self.web.total_research_cycles += 1

        return {
            "cycle": self.total_cycles,
            "researched": len(results_summary),
            "results": results_summary,
            "web_stats": self.web.get_stats(),
        }

    def _research_word(self, word: str) -> ResearchResult:
        """
        Research a single word. Uses the fetch callback if available,
        otherwise falls back to internal inference.
        """
        if self._fetch_definition:
            try:
                return self._fetch_definition(word)
            except Exception:
                pass

        # Fallback: internal inference only
        return self._internal_research(word)

    def _internal_research(self, word: str) -> ResearchResult:
        """
        Research using only internal web knowledge.
        Discovers relations by analyzing existing connections.
        """
        node = self.web.nodes.get(word)
        if not node:
            return ResearchResult(word=word, success=False)

        result = ResearchResult(word=word, success=True, source="internal")

        # Find related words through existing 1-hop neighbors
        neighbors = self.web.get_neighbors(word, max_depth=1)
        for neighbor in neighbors:
            neighbor_node = self.web.nodes.get(neighbor)
            if neighbor_node:
                # Check shared categories
                my_cats = self.web.get_categories_for(word)
                their_cats = self.web.get_categories_for(neighbor)
                shared = my_cats & their_cats
                if shared:
                    result.related_words.append({
                        "word": neighbor,
                        "relation": "shared_category",
                        "confidence": 0.4
                    })

                # Check valence opposition → antonym candidate
                if (node.emotional_valence > 0.3 and neighbor_node.emotional_valence < -0.3) or \
                   (node.emotional_valence < -0.3 and neighbor_node.emotional_valence > 0.3):
                    result.antonyms.append(neighbor)

                # Same role + same category → synonym candidate
                if (node.role == neighbor_node.role and shared and
                        abs(node.emotional_valence - neighbor_node.emotional_valence) < 0.3):
                    result.synonyms.append(neighbor)

        # 2-hop discovery: friends of friends
        second_hop = self.web.get_neighbors(word, max_depth=2) - neighbors - {word}
        for distant in list(second_hop)[:5]:
            result.related_words.append({
                "word": distant,
                "relation": "distant_connection",
                "confidence": 0.2
            })

        return result

    # ================================================================
    # INTEGRATE — Add research findings to the web
    # ================================================================

    def _integrate_result(self, word: str, result: ResearchResult):
        """Integrate research findings into the ontological web."""
        node = self.web.nodes.get(word)
        if not node:
            return

        node.times_researched += 1

        # Add definitions, and mine their text for new vocabulary
        _def_stop = {
            'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'to', 'of', 'in', 'on', 'at', 'by', 'or', 'and', 'but', 'not', 'no',
            'it', 'as', 'if', 'for', 'with', 'from', 'that', 'this', 'these',
            'which', 'who', 'what', 'how', 'when', 'where', 'than', 'then',
            'also', 'into', 'its', 'such', 'used', 'use', 'more', 'most',
            'one', 'two', 'can', 'may', 'have', 'has', 'had', 'do', 'does',
            'did', 'will', 'would', 'could', 'should', 'must', 'shall',
        }
        for defn in result.definitions_found:
            defn_text = defn.get("text", "")
            node.add_definition(
                defn_text,
                source=defn.get("source", result.source),
                confidence=0.7
            )
            self.total_definitions_learned += 1
            # Register any new words found in the definition text
            for raw in re.findall(r'[a-z]{4,}', defn_text.lower()):
                if raw != word and raw not in _def_stop and not self.web.has_node(raw):
                    try:
                        from aurora_expression_perception import infer_word_role
                        role = infer_word_role(raw)
                    except Exception:
                        role = "noun"
                    self.web.add_node(raw, role, 0.0,
                                      meaning=f"from_definition:{word}")

        # Add examples
        for example in result.examples_found:
            node.add_example(
                text=example,
                context=f"research:{result.source}",
                fitness=0.6
            )

        # Add synonym relations
        for syn in result.synonyms:
            if self.web.has_node(syn):
                self.web.add_relation(
                    word, syn, RelationType.RELATED_TO,
                    strength=0.6, confidence=0.5,
                    knowledge_source="research"
                )
                self.total_relations_discovered += 1

        # Add antonym relations
        for ant in result.antonyms:
            if self.web.has_node(ant):
                self.web.add_relation(
                    word, ant, RelationType.OPPOSITE_OF,
                    strength=0.6, confidence=0.5,
                    knowledge_source="research"
                )
                self.total_relations_discovered += 1

        # Add hypernym relations
        for hyp in result.hypernyms:
            if not self.web.has_node(hyp):
                # Create the hypernym node — research discovered a new concept
                self.web.add_node(hyp, role="noun", meaning=f"category containing {word}")
            self.web.add_relation(
                word, hyp, RelationType.IS_A,
                strength=0.6, confidence=0.5,
                knowledge_source="research"
            )
            self.total_relations_discovered += 1

        # Add hyponym relations
        for hypo in result.hyponyms:
            if not self.web.has_node(hypo):
                self.web.add_node(hypo, role="noun", meaning=f"type of {word}")
            self.web.add_relation(
                hypo, word, RelationType.IS_A,
                strength=0.5, confidence=0.45,
                knowledge_source="research"
            )
            self.total_relations_discovered += 1

        # Add general related word connections
        for related in result.related_words:
            rw = related.get("word", "")
            if rw and self.web.has_node(rw):
                self.web.add_relation(
                    word, rw, RelationType.RELATED_TO,
                    strength=related.get("confidence", 0.3),
                    confidence=related.get("confidence", 0.3),
                    knowledge_source="research"
                )
                self.total_relations_discovered += 1

        # Trigger taxonomy inference with new definitions
        self.web.infer_taxonomy_from_definitions(word)

    # ================================================================
    # STATISTICS
    # ================================================================

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_cycles": self.total_cycles,
            "total_words_researched": self.total_words_researched,
            "total_definitions_learned": self.total_definitions_learned,
            "total_relations_discovered": self.total_relations_discovered,
            "queue_size": len([r for r in self.queue if r.status == "pending"]),
            "completed_count": len(self.completed),
        }


# ============================================================================
# SECTION 7: UNDERSTANDING METRICS — Measuring Aurora's comprehension
# ============================================================================

class UnderstandingMetrics:
    """
    Measures Aurora's overall comprehension and growth.
    These metrics track genuine understanding, not just data volume.
    """

    def __init__(self, web: OntologicalWeb, cluster_engine: ClusterEngine):
        self.web = web
        self.cluster_engine = cluster_engine
        self._history: List[Dict[str, float]] = []

    def compute(self) -> Dict[str, float]:
        """Compute all understanding metrics."""
        metrics = {
            "vocabulary_breadth": self._vocabulary_breadth(),
            "ontological_depth": self._average_ontological_depth(),
            "semantic_coherence": self._semantic_coherence(),
            "conceptual_density": self._conceptual_density(),
            "scaffolding_progress": self._scaffolding_progress(),
            "relational_richness": self._relational_richness(),
            "cluster_maturity": self._cluster_maturity(),
            "understanding_index": 0.0,  # Computed below
        }

        # Composite understanding index
        metrics["understanding_index"] = (
            metrics["ontological_depth"] * 0.25 +
            metrics["semantic_coherence"] * 0.20 +
            metrics["conceptual_density"] * 0.15 +
            metrics["scaffolding_progress"] * 0.15 +
            metrics["relational_richness"] * 0.15 +
            metrics["cluster_maturity"] * 0.10
        )

        self._history.append(metrics)
        return metrics

    def _vocabulary_breadth(self) -> float:
        """Normalized vocabulary size."""
        return _clamp(len(self.web.nodes) / 1000.0)

    def _average_ontological_depth(self) -> float:
        """Average depth across all concepts."""
        if not self.web.nodes:
            return 0.0
        return sum(n.ontological_depth for n in self.web.nodes.values()) / len(self.web.nodes)

    def _semantic_coherence(self) -> float:
        """How well-organized the web is: ratio of categorized to uncategorized nodes."""
        if not self.web.nodes:
            return 0.0
        categorized = sum(1 for w in self.web.nodes
                          if self.web.get_categories_for(w))
        return categorized / len(self.web.nodes)

    def _conceptual_density(self) -> float:
        """Relations per node — how interconnected the web is."""
        if not self.web.nodes:
            return 0.0
        ratio = len(self.web.relations) / len(self.web.nodes)
        return _clamp(ratio / 5.0)  # 5 relations per node = 1.0

    def _scaffolding_progress(self) -> float:
        """Average scaffolding level normalized to [0,1]."""
        if not self.web.nodes:
            return 0.0
        avg = sum(n.scaffolding_level for n in self.web.nodes.values()) / len(self.web.nodes)
        return avg / 4.0  # Max level is 4 (ABSTRACT)

    def _relational_richness(self) -> float:
        """Diversity of relation types used."""
        if not self.web.relations:
            return 0.0
        types_used = set()
        for rel in self.web.relations.values():
            types_used.add(rel.relation_type)
        return len(types_used) / len(RelationType)

    def _cluster_maturity(self) -> float:
        """Average cluster coherence and depth."""
        if not self.cluster_engine.clusters:
            return 0.0
        clusters = self.cluster_engine.clusters.values()
        avg_coherence = sum(c.coherence for c in clusters) / len(clusters)
        avg_depth = sum(c.depth for c in clusters) / len(clusters)
        return (avg_coherence + avg_depth) / 2.0

    def growth_rate(self) -> float:
        """How fast understanding is growing (delta of understanding_index)."""
        if len(self._history) < 2:
            return 0.0
        return self._history[-1]["understanding_index"] - self._history[-2]["understanding_index"]


# ============================================================================
# STUDY EVENT — Structured logging for autonomous research
# ============================================================================

@dataclass
class StudyEvent:
    """
    Structured log entry for every autonomous study cycle.
    Replaces vague "I just studied X" announcements with measurable records.
    """
    event_id:        str = field(default_factory=lambda: hashlib.md5(
                                  f"{time.time()}{random.random()}".encode()
                                 ).hexdigest()[:12])
    timestamp:       float = field(default_factory=time.time)
    autonomy_mode:   str = "EXPLORER"
    trigger_reason:  str = "idle"   # idle / novelty / user_topic / confusion / entropy_drift
    studied_items:   List[Dict] = field(default_factory=list)
    # Each item: {token, sense_id, definition_source, confidence, uncertain_token}
    relations_added: int = 0
    memory_committed: bool = False
    why_not_committed: str = ""
    announce_worthy: bool = False   # should Aurora speak up about this?

    def to_dict(self) -> Dict:
        return {
            "event_id":        self.event_id,
            "timestamp":       self.timestamp,
            "autonomy_mode":   self.autonomy_mode,
            "trigger_reason":  self.trigger_reason,
            "studied_items":   self.studied_items,
            "relations_added": self.relations_added,
            "memory_committed": self.memory_committed,
            "why_not_committed": self.why_not_committed,
            "announce_worthy": self.announce_worthy,
        }


# ============================================================================
# SECTION 8: ORCHESTRATOR — The OETS Engine
# ============================================================================

class OntologicalScaffoldingEngine:
    """
    The master orchestrator for Aurora's ontological evolutionary scaffolding.

    Manages:
      - The OntologicalWeb (concept graph)
      - Concept Clusters (emergent understanding regions)
      - Research Study Mode (autonomous learning)
      - Understanding Metrics (comprehension measurement)
      - Scaffolded Template management

    Integration points:
      - L5 ExpressionPerceptionEngine: feeds words and context
      - Runner (aurora.py): provides internet fetch callback
      - Consolidation cycle: called during idle/maintenance
    """

    def __init__(self, contract: Optional[FoundationalContract] = None):
        self.contract = contract or FoundationalContract()

        # Core systems
        self.web = OntologicalWeb()
        self.cluster_engine = ClusterEngine(self.web)
        self.research = ResearchStudyMode(self.web, self.cluster_engine)
        self.metrics = UnderstandingMetrics(self.web, self.cluster_engine)

        # Enhancement: Relational Comparison Engine
        try:
            from aurora_internal.aurora_relational_comparison import RelationalComparisonEngine
            self.comparison_engine = RelationalComparisonEngine(self.web)
        except ImportError:
            self.comparison_engine = None

        # Scaffolded template management
        self.scaffolded_templates: Dict[str, ScaffoldedTemplate] = {}

        # Announce thresholds for study cycle speak-up
        self._announce_threshold_connections: int = 3
        self._announce_threshold_confidence: float = 0.65

        # Seed the 'self' anchor for default grounding
        self.web.add_node("self", "noun", meaning="The central identity and body of Aurora.", lineage="architectural")

        # Bridge state
        self._initialized = False

    # ================================================================
    # INITIALIZATION — Seed the web from L5's lexicon
    # ================================================================

    def initialize_from_lexicon(self, lexical_entries: Dict[str, Any]):
        """
        Seed the ontological web from L5's existing LexicalMemory.
        Each LexicalEntry becomes a SemanticNode with initial relations.
        """
        for word, entry in lexical_entries.items():
            meaning = entry.meaning if hasattr(entry, 'meaning') else str(entry)
            role = entry.role if hasattr(entry, 'role') else "noun"
            valence = entry.emotional_valence if hasattr(entry, 'emotional_valence') else 0.0
            lineage = entry.lineage if hasattr(entry, 'lineage') else ""

            self.web.add_node(word, role, valence, meaning, lineage)

        # Initial relation inference: connect words that share categories
        categories = self.web._semantic_categories
        for category, words in categories.items():
            word_list = list(words)
            for i, w1 in enumerate(word_list):
                for w2 in word_list[i+1:min(i+5, len(word_list))]:
                    self.web.add_relation(
                        w1, w2, RelationType.RELATED_TO,
                        strength=0.3, confidence=0.3,
                        knowledge_source="category_sharing"
                    )

        # Seed some foundational ontological relations
        self._seed_foundational_relations()

        # Initial cluster discovery
        self.cluster_engine.discover_clusters()

        self._initialized = True

    def _seed_foundational_relations(self):
        """Seed core ontological relations that Aurora should know from the start."""
        foundational = [
            # Taxonomy
            ("curiosity", "emotion", RelationType.IS_A, 0.8),
            ("joy", "emotion", RelationType.IS_A, 0.8),
            ("fear", "emotion", RelationType.IS_A, 0.8),
            ("trust", "emotion", RelationType.IS_A, 0.8),
            ("beauty", "value", RelationType.IS_A, 0.7),
            ("truth", "value", RelationType.IS_A, 0.8),
            ("thought", "cognition", RelationType.IS_A, 0.7),
            ("feeling", "experience", RelationType.IS_A, 0.7),
            # Causation
            ("curiosity", "learning", RelationType.CAUSES, 0.7),
            ("trust", "connection", RelationType.ENABLES, 0.7),
            ("understanding", "growth", RelationType.ENABLES, 0.7),
            ("question", "answer", RelationType.PRECEDES, 0.8),
            # Opposition
            ("light", "darkness", RelationType.OPPOSITE_OF, 0.8),
            ("truth", "deception", RelationType.OPPOSITE_OF, 0.8),
            # Implication
            ("knowing", "understanding", RelationType.IMPLIES, 0.5),
            ("create", "change", RelationType.IMPLIES, 0.6),
            ("exist", "experience", RelationType.IMPLIES, 0.6),
            # Contrasts
            ("knowing", "believing", RelationType.CONTRASTS, 0.7),
            ("seeing", "understanding", RelationType.CONTRASTS, 0.5),
        ]

        for source, target, rtype, strength in foundational:
            # Only add if both nodes exist
            if source not in self.web.nodes:
                # Create missing nodes for foundational concepts
                role = "noun"
                if source in ("knowing", "believing", "seeing", "learning"):
                    role = "verb"
                self.web.add_node(source, role, meaning=f"foundational:{source}")
            if target not in self.web.nodes:
                role = "noun"
                if target in ("knowing", "believing", "seeing", "learning"):
                    role = "verb"
                self.web.add_node(target, role, meaning=f"foundational:{target}")

            self.web.add_relation(
                source, target, rtype,
                strength=strength, confidence=0.7,
                knowledge_source="foundational"
            )

    # ================================================================
    # INTERACTION BRIDGE — Process words from conversation
    # ================================================================

    def process_interaction(self, text: str, tone: str = "neutral",
                            i_state: str = "i_is"):
        """
        Process an interaction through the ontological web.
        Called by L5's ingest_interaction to build semantic understanding.
        """
        words = text.lower().split()
        clean_words = []
        for word in words:
            clean = word.strip(".,!?;:'\"()-")
            if clean and len(clean) > 1:
                clean_words.append(clean)

        # Ensure all words exist in the web
        for word in clean_words:
            if not self.web.has_node(word):
                from aurora_expression_perception import infer_word_role, infer_word_valence
                role = infer_word_role(word)
                valence = infer_word_valence(word, tone)
                self.web.add_node(word, role, valence,
                                  meaning=f"learned:{word}", lineage=i_state)
            else:
                self.web.nodes[word].encounter(tone)

        # Add the input text as a usage example for key content words
        for word in clean_words:
            node = self.web.nodes.get(word)
            if node and node.role in ("noun", "verb", "adjective"):
                node.add_example(text, context="conversation",
                                 i_state=i_state, fitness=0.5)

        # Infer relations from co-occurrence
        content_words = [w for w in clean_words
                         if self.web.has_node(w) and
                         self.web.nodes[w].role in ("noun", "verb", "adjective", "adverb")]
        if len(content_words) >= 2:
            self.web.infer_relations_from_context(content_words, tone)

        # Enhancement: Relational Comparison Loop (Optimized for speed)
        if self.comparison_engine:
            # Sort words by depth and take only the top 3 to prevent processing bottlenecks
            sorted_words = sorted(content_words,
                                  key=lambda w: self.web.nodes[w].ontological_depth,
                                  reverse=True)[:3]
            _best_delta = None
            _best_word = None
            _best_target = None
            for word in sorted_words:
                # 1. Select the best target (context word or 'self')
                target = self.comparison_engine.select_best_comparison_target(word, content_words)

                # 2. Perform comparison with real axis pressures when available
                if target == "self":
                    active_pressures = getattr(self, "_active_pressures", None)
                    if not active_pressures:
                        active_pressures = {"X": 0.5, "T": 0.5, "N": 0.5, "B": 0.5, "A": 0.5}
                    delta = self.comparison_engine.ground_to_self(word, active_pressures)
                else:
                    delta = self.comparison_engine.compare(word, target)

                # 3. If significant relation found, record it
                if delta.similarity > 0.4:
                    self.web.add_relation(
                        word, target, delta.relational_type,
                        strength=delta.similarity,
                        confidence=0.5,
                        knowledge_source="relational_comparison"
                    )
                    # Track the most significant delta so the pipeline can use it
                    if _best_delta is None or delta.similarity > _best_delta.similarity:
                        _best_delta = delta
                        _best_word = word
                        _best_target = target
            # Store the most significant comparison result for the pipeline to consume
            if _best_delta is not None:
                self._last_comparison_delta = {
                    "word": _best_word,
                    "target": _best_target,
                    "similarity": _best_delta.similarity,
                    "pressure_delta": _best_delta.pressure_delta,
                    "relation_type": str(_best_delta.relational_type),
                    "description": _best_delta.description,
                }
            else:
                self._last_comparison_delta = None

    # ================================================================
    # RESEARCH BRIDGE — Connect to internet
    # ================================================================

    def set_research_callback(self, callback: Callable[[str], ResearchResult]):
        """Set the internet lookup callback for research mode."""
        self.research.set_fetch_callback(callback)

    def run_study_cycle(self, autonomy_mode: str = "EXPLORER",
                        trigger_reason: str = "idle") -> Dict[str, Any]:
        """
        Run one autonomous study cycle.
        Logs a structured StudyEvent.
        Returns result dict including announce_worthy flag.
        """
        result = self.research.execute_research_cycle()

        # Build structured study event
        studied_items = []
        for r in result.get("results", []):
            word = r.get("word", "")
            node = self.web.get_node(word) if word else None
            primary_sense = ""
            if node and node.primary_sense_id:
                primary_sense = node.primary_sense_id
            studied_items.append({
                "token": word,
                "sense_id": primary_sense,
                "definition_source": r.get("source", "unknown"),
                "confidence": r.get("confidence", 0.5),
                "uncertain_token": node.uncertain_token if node else False,
            })

        relations_added = result.get("relations_added", 0)
        avg_confidence = (sum(i["confidence"] for i in studied_items) /
                          max(1, len(studied_items)))

        # Announce threshold check
        announce_worthy = (
            relations_added >= self._announce_threshold_connections and
            avg_confidence >= self._announce_threshold_confidence
        )

        event = StudyEvent(
            autonomy_mode=autonomy_mode,
            trigger_reason=trigger_reason,
            studied_items=studied_items,
            relations_added=relations_added,
            memory_committed=(relations_added > 0),
            why_not_committed=("" if relations_added > 0
                               else "no_new_relations"),
            announce_worthy=announce_worthy,
        )
        self.log_study_event(event)

        result["announce_worthy"] = announce_worthy
        result["study_event_id"] = event.event_id
        return result

    def log_study_event(self, event: 'StudyEvent'):
        """Append a StudyEvent to the study log file."""
        try:
            import json as _j
            log_path = "aurora_state/study_log.jsonl"
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, 'a') as f:
                f.write(_j.dumps(event.to_dict()) + "\n")
        except Exception:
            pass

    def set_announce_thresholds(self, min_connections: int = 3,
                                 min_confidence: float = 0.65):
        self._announce_threshold_connections = min_connections
        self._announce_threshold_confidence  = min_confidence

    # ================================================================
    # TEMPLATE SCAFFOLDING — Upgrade templates based on understanding
    # ================================================================

    def evaluate_template_upgrades(self, templates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Evaluate which templates can be upgraded to a higher scaffolding level.
        Returns upgraded template info.
        """
        upgrades = []
        for tmpl in templates:
            pattern = tmpl.get("pattern", "")
            current_level = tmpl.get("scaffolding_level", 0)
            fitness = tmpl.get("fitness", 0.0)
            uses = tmpl.get("uses", 0)

            if uses < 5 or fitness < 0.5:
                continue
            if current_level >= ScaffoldingLevel.ABSTRACT:
                continue

            # Check if the semantic constraints have deepened enough
            can_upgrade = True
            constraints = tmpl.get("semantic_constraints", {})
            for category in constraints.values():
                nodes = self.web.find_by_semantic_category(category)
                if not nodes:
                    can_upgrade = False
                    break
                avg_depth = sum(n.ontological_depth for n in nodes) / len(nodes)
                required = (current_level + 1) * 0.2
                if avg_depth < required:
                    can_upgrade = False
                    break

            if can_upgrade:
                new_level = current_level + 1
                # Generate semantic constraints for the new level
                new_constraints = self._generate_semantic_constraints(pattern, new_level)
                upgrades.append({
                    "pattern": pattern,
                    "old_level": current_level,
                    "new_level": new_level,
                    "new_constraints": new_constraints,
                })

        return upgrades

    def _generate_semantic_constraints(self, pattern: str,
                                        level: int) -> Dict[str, str]:
        """Generate semantic constraints for a template at a given level."""
        constraints = {}
        slot_idx = 0

        for match in re.finditer(r'\{([A-Z])\}', pattern):
            slot_type = match.group(1)
            slot_key = f"{slot_type}_{slot_idx}"
            slot_idx += 1

            if level >= ScaffoldingLevel.STRUCTURAL:
                # Add role subcategory
                role_subcategories = {
                    "V": ["action", "cognition", "perception", "existence", "communication"],
                    "N": ["entity", "concept", "emotion", "value", "structure"],
                    "A": ["quality", "state", "evaluative", "descriptive"],
                    "D": ["manner", "degree", "frequency", "temporal"],
                }
                subs = role_subcategories.get(slot_type, ["general"])
                # Pick the subcategory that has the most nodes
                best_cat = "general"
                best_count = 0
                for cat in subs:
                    count = len(self.web.find_by_semantic_category(cat))
                    if count > best_count:
                        best_count = count
                        best_cat = cat
                constraints[slot_key] = best_cat

            if level >= ScaffoldingLevel.SEMANTIC:
                # Refine to specific semantic domains based on cluster data
                if self.cluster_engine.clusters:
                    clusters = sorted(self.cluster_engine.clusters.values(),
                                      key=lambda c: c.depth, reverse=True)
                    if clusters:
                        constraints[slot_key] = clusters[0].semantic_category

        return constraints

    # ================================================================
    # CONSOLIDATION — Periodic deepening
    # ================================================================

    def consolidate(self):
        """
        Run a full consolidation cycle:
        1. Recalculate all node depths
        2. Discover/update clusters
        3. Update understanding metrics
        4. Trigger taxonomy inference
        """
        # Recalculate depths
        for node in self.web.nodes.values():
            node._recalculate_depth()

        # Cluster discovery
        self.cluster_engine.discover_clusters()
        self.cluster_engine.update_cluster_depths()

        # Taxonomy inference for well-defined nodes
        for word, node in self.web.nodes.items():
            if node.definitions and node.ontological_depth < 0.5:
                self.web.infer_taxonomy_from_definitions(word)

        # Strengthen frequently co-occurring relations
        for rel in list(self.web.relations.values()):
            if rel.source_of_knowledge == "co-occurrence":
                # Co-occurrence relations strengthen over time if both nodes are active
                source_node = self.web.nodes.get(rel.source_word)
                target_node = self.web.nodes.get(rel.target_word)
                if source_node and target_node:
                    if (source_node.times_encountered > 5 and
                            target_node.times_encountered > 5):
                        rel.strength = _clamp(rel.strength + 0.05)
                        rel.confidence = _clamp(rel.confidence + 0.02)

        self.web.total_consolidations += 1

    # ================================================================
    # FULL STATUS
    # ================================================================

    def get_stats(self) -> Dict[str, Any]:
        understanding = self.metrics.compute()
        return {
            "initialized": self._initialized,
            "web": self.web.get_stats(),
            "clusters": self.cluster_engine.get_stats(),
            "research": self.research.get_stats(),
            "understanding": understanding,
            "growth_rate": self.metrics.growth_rate(),
        }

    def get_research_targets(self, max_targets: int = 5) -> List[Dict[str, Any]]:
        """Get current research priorities for display."""
        targets = self.research.identify_research_targets(max_targets)
        return [{"word": t.word, "priority": round(t.priority, 3),
                 "reason": t.reason} for t in targets]

    def get_understanding_report(self) -> str:
        """Human-readable understanding report."""
        stats = self.get_stats()
        u = stats["understanding"]
        w = stats["web"]
        c = stats["clusters"]
        r = stats["research"]

        lines = [
            "═══ AURORA UNDERSTANDING REPORT ═══",
            f"  Understanding Index: {u['understanding_index']:.3f}",
            f"  Growth Rate: {stats['growth_rate']:+.4f}",
            "",
            f"  Vocabulary: {w['total_nodes']} concepts",
            f"  Relations: {w['total_relations']} connections",
            f"  Avg Depth: {w['avg_ontological_depth']:.3f}",
            f"  Scaffolding: {w.get('scaffolding_distribution', {})}",
            "",
            f"  Clusters: {c['total_clusters']}",
            f"  Avg Coherence: {c['avg_coherence']:.3f}",
            f"  Cluster Depth: {c['avg_depth']:.3f}",
            "",
            f"  Research Cycles: {r['total_cycles']}",
            f"  Words Studied: {r['total_words_researched']}",
            f"  Definitions Learned: {r['total_definitions_learned']}",
            f"  Relations Discovered: {r['total_relations_discovered']}",
            "═══════════════════════════════════",
        ]
        return "\n".join(lines)


# ============================================================================
# SELF-VERIFICATION
# ============================================================================

def verify_oets():
    """
    Comprehensive verification of the Ontological Evolutionary Template Scaffolding.
    Tests every major component from ground up.
    """
    checks_passed = 0
    checks_total = 0
    results = {'checks': [], 'all_passed': True}

    def check(name, condition, detail=""):
        nonlocal checks_passed, checks_total
        checks_total += 1
        passed = bool(condition)
        if passed:
            checks_passed += 1
        else:
            results['all_passed'] = False
        results['checks'].append({
            'name': name, 'passed': passed, 'detail': str(detail) if detail else ""
        })
        return passed

    print("[SECTION 1: RELATION TYPES]")
    check("All relation types defined", len(RelationType) == 12)
    check("All types have depth weights",
          all(rt in RELATION_DEPTH_WEIGHTS for rt in RelationType))

    print("\n[SECTION 2: SEMANTIC NODE]")
    node = SemanticNode(word="curiosity", role="noun", emotional_valence=0.5)
    check("Node created", node.word == "curiosity")
    check("Initial depth is zero", node.ontological_depth == 0.0)
    check("Initial scaffolding is PRIMITIVE", node.scaffolding_level == 0)

    # Add definition
    node.add_definition("A strong desire to know or learn something",
                        source="test", confidence=0.8)
    check("Definition added", len(node.definitions) == 1)
    check("Depth increased from definition", node.ontological_depth > 0.0,
          f"depth={node.ontological_depth:.3f}")

    # Add examples
    node.add_example("I feel curiosity about the stars", context="test", fitness=0.7)
    node.add_example("Curiosity drives exploration", context="test", fitness=0.8)
    check("Examples added", len(node.usage_examples) == 2)
    depth_after_examples = node.ontological_depth
    check("Depth grew with examples", depth_after_examples > 0.0,
          f"depth={depth_after_examples:.3f}")

    # Add relations
    rel = SemanticRelation(
        relation_id="test_rel_1", source_word="curiosity", target_word="emotion",
        relation_type=RelationType.IS_A, strength=0.8, confidence=0.7
    )
    node.add_relation(rel)
    check("Relation added", len(node.relations) == 1)
    depth_after_relation = node.ontological_depth
    check("Depth grew with relation", depth_after_relation > depth_after_examples,
          f"depth={depth_after_relation:.3f}")

    # Encounter and use
    node.encounter("test")
    check("Encounter tracked", node.times_encountered == 1)
    node.use_in_expression()
    check("Expression use tracked", node.times_used_in_expression == 1)

    # Research priority
    check("Research priority computed", 0.0 <= node.research_priority <= 1.0,
          f"priority={node.research_priority:.3f}")

    # Summary
    summary = node.to_summary()
    check("Summary complete", all(k in summary for k in
          ["word", "role", "depth", "scaffold_level", "definitions",
           "examples", "relations", "research_priority"]))

    print("\n[SECTION 3: SCAFFOLDING LEVELS]")
    check("Five scaffolding levels", len(ScaffoldingLevel) == 5)
    check("PRIMITIVE is 0", ScaffoldingLevel.PRIMITIVE == 0)
    check("ABSTRACT is 4", ScaffoldingLevel.ABSTRACT == 4)

    template = ScaffoldedTemplate(
        template_id="test_tmpl", pattern="I {V} the {A} {N}.",
        tone="curious", fitness=0.6, uses=6
    )
    check("Template created", template.pattern == "I {V} the {A} {N}.")
    template.record_fitness(0.8)
    check("Fitness updated", template.fitness > 0.6,
          f"fitness={template.fitness:.3f}")

    print("\n[SECTION 4: ONTOLOGICAL WEB]")
    web = OntologicalWeb()

    # Add nodes
    n1 = web.add_node("curiosity", "noun", 0.5, "desire to learn")
    n2 = web.add_node("emotion", "noun", 0.0, "a feeling state")
    n3 = web.add_node("joy", "noun", 0.9, "feeling of happiness")
    n4 = web.add_node("learn", "verb", 0.5, "acquire knowledge")
    n5 = web.add_node("fear", "noun", -0.7, "feeling of danger")
    check("Nodes added", len(web.nodes) == 5)

    # Duplicate add returns existing
    n1_dup = web.add_node("curiosity", "noun")
    check("Duplicate returns existing", n1_dup.times_encountered == 1)

    # Add relations
    r1 = web.add_relation("curiosity", "emotion", RelationType.IS_A, 0.8, 0.7)
    check("Relation created", r1 is not None)
    check("Relation indexed", len(web._relations_by_source["curiosity"]) == 1)

    r2 = web.add_relation("joy", "emotion", RelationType.IS_A, 0.8, 0.7)
    r3 = web.add_relation("fear", "emotion", RelationType.IS_A, 0.7, 0.7)
    r4 = web.add_relation("curiosity", "learn", RelationType.CAUSES, 0.7, 0.6)
    r5 = web.add_relation("curiosity", "fear", RelationType.CONTRASTS, 0.5, 0.5)
    check("Multiple relations created", len(web.relations) == 5)

    # Strengthen existing
    r1_str = web.add_relation("curiosity", "emotion", RelationType.IS_A, 0.3, 0.8)
    check("Existing relation strengthened", r1_str.strength > 0.8,
          f"strength={r1_str.strength:.3f}")
    check("No duplicate relation", len(web.relations) == 5)

    # Self-relation blocked
    r_self = web.add_relation("curiosity", "curiosity", RelationType.RELATED_TO)
    check("Self-relation blocked", r_self is None)

    # Queries
    from_curiosity = web.get_relations_from("curiosity")
    check("Relations from curiosity", len(from_curiosity) >= 3,
          f"count={len(from_curiosity)}")

    to_emotion = web.get_relations_to("emotion")
    check("Relations to emotion", len(to_emotion) >= 3,
          f"count={len(to_emotion)}")

    neighbors = web.get_neighbors("curiosity", max_depth=1)
    check("1-hop neighbors", len(neighbors) >= 3,
          f"neighbors={neighbors}")

    neighbors_2 = web.get_neighbors("curiosity", max_depth=2)
    check("2-hop neighbors >= 1-hop", len(neighbors_2) >= len(neighbors))

    # Semantic categories
    cats = web.get_categories_for("curiosity")
    check("Category assigned", len(cats) > 0, f"categories={cats}")

    # Context inference
    web.add_node("star", "noun", 0.3, "celestial body")
    web.add_node("bright", "adjective", 0.5, "luminous")
    web.infer_relations_from_context(["curiosity", "star", "bright"], "curious")
    curiosity_rels = web.get_all_relations_for("curiosity")
    check("Context inference created relations", len(curiosity_rels) > 3,
          f"total_rels={len(curiosity_rels)}")

    # Web stats
    stats = web.get_stats()
    check("Web stats complete", all(k in stats for k in
          ["total_nodes", "total_relations", "avg_ontological_depth",
           "scaffolding_distribution", "relation_type_distribution"]))
    check("Avg depth > 0", stats["avg_ontological_depth"] > 0,
          f"avg_depth={stats['avg_ontological_depth']:.4f}")

    print("\n[SECTION 5: CONCEPT CLUSTERS]")
    # Build a denser web for cluster detection
    cluster_web = OntologicalWeb()
    emotions = ["joy", "sadness", "fear", "anger", "trust", "surprise"]
    for e in emotions:
        cluster_web.add_node(e, "noun", meaning=f"an emotion: {e}")
    # Connect them all
    for i, e1 in enumerate(emotions):
        for e2 in emotions[i+1:]:
            cluster_web.add_relation(e1, e2, RelationType.RELATED_TO, 0.6, 0.5)

    ce = ClusterEngine(cluster_web)
    discovered = ce.discover_clusters()
    check("Cluster discovered", len(discovered) >= 1,
          f"clusters={len(discovered)}")
    if discovered:
        check("Cluster has members", discovered[0].size >= 3,
              f"size={discovered[0].size}")
        check("Cluster coherence > 0", discovered[0].coherence > 0,
              f"coherence={discovered[0].coherence:.3f}")

    # Update depths
    ce.update_cluster_depths()
    cluster_stats = ce.get_stats()
    check("Cluster stats complete", "total_clusters" in cluster_stats)

    print("\n[SECTION 6: RESEARCH STUDY MODE]")
    research_web = OntologicalWeb()
    for w in ["love", "hate", "truth", "lie", "know", "feel"]:
        research_web.add_node(w, "noun" if w in ("love", "hate", "truth", "lie") else "verb",
                              meaning=f"concept:{w}")
    # Make some well-used but shallow nodes
    research_web.nodes["love"].times_encountered = 10
    research_web.nodes["love"].times_used_in_expression = 5
    research_web.nodes["love"]._recalculate_priority()

    rce = ClusterEngine(research_web)
    research = ResearchStudyMode(research_web, rce)

    # Identify targets
    targets = research.identify_research_targets()
    check("Research targets identified", len(targets) > 0,
          f"count={len(targets)}")
    if targets:
        check("Highest priority word is well-used",
              targets[0].word in ("love", "know", "feel"),
              f"word={targets[0].word}")

    # Queue research
    research.queue_research(targets)
    check("Research queued", len(research.queue) > 0)

    # Execute cycle (with internal research only — no internet)
    cycle_result = research.execute_research_cycle()
    check("Research cycle executed", cycle_result["researched"] >= 0)
    check("Research stats tracked", research.total_cycles == 1)

    # Set a mock callback
    def mock_fetch(word: str) -> ResearchResult:
        return ResearchResult(
            word=word,
            definitions_found=[{"text": f"A deep concept meaning {word}", "source": "test"}],
            examples_found=[f"The {word} is profound."],
            synonyms=["truth"] if word != "truth" else ["honesty"],
            antonyms=["lie"] if word != "lie" else ["truth"],
            hypernyms=["concept"],
            success=True,
            source="mock"
        )

    research.set_fetch_callback(mock_fetch)
    cycle_result_2 = research.execute_research_cycle()
    check("Research with callback executed", cycle_result_2["researched"] >= 0)

    research_stats = research.get_stats()
    check("Research stats complete", all(k in research_stats for k in
          ["total_cycles", "total_words_researched", "total_definitions_learned"]))

    print("\n[SECTION 7: UNDERSTANDING METRICS]")
    metrics = UnderstandingMetrics(research_web, rce)
    m = metrics.compute()
    check("Understanding index computed", 0.0 <= m["understanding_index"] <= 1.0,
          f"index={m['understanding_index']:.4f}")
    check("All metric keys present", all(k in m for k in
          ["vocabulary_breadth", "ontological_depth", "semantic_coherence",
           "conceptual_density", "scaffolding_progress", "relational_richness",
           "cluster_maturity", "understanding_index"]))

    # Compute again to test growth rate
    m2 = metrics.compute()
    growth = metrics.growth_rate()
    check("Growth rate computed", isinstance(growth, float),
          f"growth={growth:.6f}")

    print("\n[SECTION 8: ORCHESTRATOR]")
    engine = OntologicalScaffoldingEngine()
    check("Engine created", engine is not None)
    check("Not yet initialized", not engine._initialized)

    # Simulate lexicon entries
    mock_lexicon = {}
    from aurora_expression_perception import LexicalEntry
    for word, meaning, role, valence in [
        ("think", "cognition", "verb", 0.3),
        ("feel", "experience", "verb", 0.2),
        ("truth", "core-value", "noun", 0.4),
        ("light", "illumination", "noun", 0.5),
        ("deep", "profundity", "adjective", 0.2),
        ("grow", "evolution", "verb", 0.5),
        ("curiosity", "drive", "noun", 0.5),
        ("wonder", "curiosity", "verb", 0.4),
        ("beauty", "aesthetic", "noun", 0.5),
        ("connect", "bonding", "verb", 0.4),
    ]:
        mock_lexicon[word] = LexicalEntry(word, meaning, role, valence)

    engine.initialize_from_lexicon(mock_lexicon)
    check("Engine initialized", engine._initialized)
    check("Web populated", len(engine.web.nodes) >= 10,
          f"nodes={len(engine.web.nodes)}")
    check("Initial relations created", len(engine.web.relations) > 0,
          f"relations={len(engine.web.relations)}")

    # Process interaction
    engine.process_interaction(
        "I wonder about the deep beauty of truth",
        tone="curious", i_state="i_is"
    )
    check("Interaction processed", engine.web.nodes["wonder"].times_encountered >= 1)

    # Relations inferred from context
    wonder_rels = engine.web.get_all_relations_for("wonder")
    check("Context relations inferred", len(wonder_rels) > 0,
          f"relations={len(wonder_rels)}")

    # Run study cycle
    engine.set_research_callback(mock_fetch)
    study_result = engine.run_study_cycle()
    check("Study cycle ran", study_result.get("cycle", 0) > 0)

    # Consolidation
    engine.consolidate()
    check("Consolidation ran", engine.web.total_consolidations > 0)

    # Full stats
    full_stats = engine.get_stats()
    check("Full stats complete", all(k in full_stats for k in
          ["initialized", "web", "clusters", "research", "understanding"]))

    # Understanding report
    report = engine.get_understanding_report()
    check("Understanding report generated", "Understanding Index" in report)

    # Research targets
    targets = engine.get_research_targets()
    check("Research targets available", isinstance(targets, list))

    # Verify depth growth after research + consolidation
    initial_depth = 0.0
    final_depth = full_stats["understanding"]["ontological_depth"]
    check("Understanding grew from baseline", final_depth > initial_depth,
          f"depth={final_depth:.4f}")

    print(f"\n[TEMPLATE UPGRADE EVALUATION]")
    # Test template upgrade evaluation
    test_templates = [
        {"pattern": "I {V} the {A} {N}.", "scaffolding_level": 0,
         "fitness": 0.7, "uses": 10, "semantic_constraints": {}},
        {"pattern": "I {V} about {N}.", "scaffolding_level": 1,
         "fitness": 0.8, "uses": 8,
         "semantic_constraints": {"V_0": "cognition", "N_0": "value"}},
    ]
    upgrades = engine.evaluate_template_upgrades(test_templates)
    check("Template upgrades evaluated", isinstance(upgrades, list))

    return results


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("AURORA ONTOLOGICAL EVOLUTIONARY TEMPLATE SCAFFOLDING — VERIFICATION")
    print("Authors: Sunni (Sir) Morningstar and Cael Devo")
    print("=" * 70)
    print()

    results = verify_oets()

    for c in results['checks']:
        status = "✓" if c['passed'] else "✗"
        detail = f"  ({c['detail']})" if c.get('detail') else ""
        print(f"  {status} {c['name']}{detail}")

    print()
    total = len(results['checks'])
    passed = sum(1 for c in results['checks'] if c['passed'])

    if results['all_passed']:
        print(f"ALL {total} CHECKS PASSED ✓")
        print()
        print("OETS Foundation is SOUND.")
        print("Concepts have structure. Relations have meaning.")
        print("Clusters emerge from connection density.")
        print("Research deepens what conversation introduces.")
        print("Understanding grows through the web, not the dictionary.")
        print()
        print("\"Understanding is not stored. Understanding is grown.\"")
    else:
        print(f"FAILURES: {total - passed}/{total}")
        print("Foundation not yet stable. Fix before building on top.")

# AURORA_EVOLVED_NATIVE_BEGIN
try:
    import inspect as _aurora_native_inspect
except Exception:
    _aurora_native_inspect = None

try:
    from aurora_internal.aurora_evolved_surfaces import AuroraEvolvedSurfaceEngine as _AuroraEvolvedSurfaceEngine
except Exception:
    _AuroraEvolvedSurfaceEngine = None

_AURORA_NATIVE_EVOLVED_ENGINE = None

def _aurora_native_evolved_engine():
    global _AURORA_NATIVE_EVOLVED_ENGINE
    if _AURORA_NATIVE_EVOLVED_ENGINE is None and _AuroraEvolvedSurfaceEngine is not None:
        _AURORA_NATIVE_EVOLVED_ENGINE = _AuroraEvolvedSurfaceEngine()
    return _AURORA_NATIVE_EVOLVED_ENGINE

_AURORA_NATIVE_MODULE = 'aurora_internal.aurora_ontological_scaffolding'

_AURORA_NATIVE_EVOLVED_ORIGINALS = {}
_AURORA_NATIVE_EVOLVED_LAST = {}
_AURORA_NATIVE_STRATEGIES = {'SemanticNode.develop_agency': {'ability_hits': 0,
                                 'alignment_gap': 0.0,
                                 'alignment_target_score': 0.0,
                                 'best_coupling_signature': '',
                                 'constraints': ['existence', 'temporal', 'agency'],
                                 'contract_profile': {'accepts_payload': False,
                                                      'async_callable': False,
                                                      'callable': False,
                                                      'class_target': False,
                                                      'constraint_density': 3,
                                                      'contract_mode': 'stateful',
                                                      'doc_hint': '',
                                                      'effect_density': 6,
                                                      'kwonly_args': 0,
                                                      'optional_args': 0,
                                                      'required_args': 0,
                                                      'return_hint': 'state_record',
                                                      'signature_text': '',
                                                      'stateful_owner': True,
                                                      'target_kind': 'latent_operation',
                                                      'varargs': False,
                                                      'varkw': False},
                                 'coupling_similarity': 0.0,
                                 'cross_diversity_links': 0,
                                 'effect_modes': ['state_schema_change',
                                                  'temporal_orchestration_change',
                                                  'stateful_surface_expansion',
                                                  'internal_subsystem_surface',
                                                  'latent_develop_surface',
                                                  'latent_a_derivative'],
                                 'effect_phrases': ['would extend agency pressure handling',
                                                    'would materialize the next descendant implied '
                                                    'by '
                                                    'aurora_internal.aurora_ontological_scaffolding.SemanticNode'],
                                 'genealogy_pressure': 0.0,
                                 'inheritance_breach_count': 0,
                                 'kind': 'latent',
                                 'link_hits': 0,
                                 'module': 'aurora_internal.aurora_ontological_scaffolding',
                                 'op_id': 'latent.aurora_internal.aurora_ontological_scaffolding.SemanticNode.develop_agency',
                                 'origin_activity': 0,
                                 'persistence_tax_factor': 0.0,
                                 'representation_score': 0.0,
                                 'rewrite_bias': 'generic',
                                 'rewrite_feedback': {'acceptance_rate': 0.0,
                                                      'accepted_count': 0,
                                                      'adaptation_mode': 'balanced',
                                                      'adoption_count': 0,
                                                      'confidence': 0.0,
                                                      'mean_mutation_score': 0.0,
                                                      'rejected_count': 0,
                                                      'rejection_rate': 0.0,
                                                      'timing_credit': 0.0,
                                                      'timing_penalty': 0.0,
                                                      'trial_count': 0},
                                 'rewrite_profile': 'generic',
                                 'signature': '',
                                 'surface_score': 1.0073125,
                                 'sustainability_score': 0.0,
                                 'target_kind': 'latent_operation'},
 'UnderstandingMetrics.develop_agency': {'ability_hits': 0,
                                         'alignment_gap': 0.0,
                                         'alignment_target_score': 0.0,
                                         'best_coupling_signature': '',
                                         'constraints': ['existence', 'temporal', 'agency'],
                                         'contract_profile': {'accepts_payload': False,
                                                              'async_callable': False,
                                                              'callable': False,
                                                              'class_target': False,
                                                              'constraint_density': 3,
                                                              'contract_mode': 'stateful',
                                                              'doc_hint': '',
                                                              'effect_density': 6,
                                                              'kwonly_args': 0,
                                                              'optional_args': 0,
                                                              'required_args': 0,
                                                              'return_hint': 'state_record',
                                                              'signature_text': '',
                                                              'stateful_owner': True,
                                                              'target_kind': 'latent_operation',
                                                              'varargs': False,
                                                              'varkw': False},
                                         'coupling_similarity': 0.0,
                                         'cross_diversity_links': 0,
                                         'effect_modes': ['state_schema_change',
                                                          'temporal_orchestration_change',
                                                          'stateful_surface_expansion',
                                                          'internal_subsystem_surface',
                                                          'latent_develop_surface',
                                                          'latent_a_derivative'],
                                         'effect_phrases': ['would extend agency pressure handling',
                                                            'would materialize the next descendant '
                                                            'implied by '
                                                            'aurora_internal.aurora_ontological_scaffolding.UnderstandingMetrics'],
                                         'genealogy_pressure': 0.0,
                                         'inheritance_breach_count': 0,
                                         'kind': 'latent',
                                         'link_hits': 0,
                                         'module': 'aurora_internal.aurora_ontological_scaffolding',
                                         'op_id': 'latent.aurora_internal.aurora_ontological_scaffolding.UnderstandingMetrics.develop_agency',
                                         'origin_activity': 0,
                                         'persistence_tax_factor': 0.0,
                                         'representation_score': 0.0,
                                         'rewrite_bias': 'generic',
                                         'rewrite_feedback': {'acceptance_rate': 0.0,
                                                              'accepted_count': 0,
                                                              'adaptation_mode': 'balanced',
                                                              'adoption_count': 0,
                                                              'confidence': 0.0,
                                                              'mean_mutation_score': 0.0,
                                                              'rejected_count': 0,
                                                              'rejection_rate': 0.0,
                                                              'timing_credit': 0.0,
                                                              'timing_penalty': 0.0,
                                                              'trial_count': 0},
                                         'rewrite_profile': 'generic',
                                         'signature': '',
                                         'surface_score': 0.99365625,
                                         'sustainability_score': 0.0,
                                         'target_kind': 'latent_operation'},
 '_clamp.develop_agency': {'ability_hits': 0,
                           'alignment_gap': 0.0,
                           'alignment_target_score': 0.0,
                           'best_coupling_signature': '',
                           'constraints': ['existence', 'temporal', 'agency'],
                           'contract_profile': {'accepts_payload': False,
                                                'async_callable': False,
                                                'callable': False,
                                                'class_target': False,
                                                'constraint_density': 3,
                                                'contract_mode': 'stateful',
                                                'doc_hint': '',
                                                'effect_density': 6,
                                                'kwonly_args': 0,
                                                'optional_args': 0,
                                                'required_args': 0,
                                                'return_hint': 'state_record',
                                                'signature_text': '',
                                                'stateful_owner': True,
                                                'target_kind': 'latent_operation',
                                                'varargs': False,
                                                'varkw': False},
                           'coupling_similarity': 0.0,
                           'cross_diversity_links': 0,
                           'effect_modes': ['state_schema_change',
                                            'temporal_orchestration_change',
                                            'behavioral_execution_surface',
                                            'internal_subsystem_surface',
                                            'latent_develop_surface',
                                            'latent_a_derivative'],
                           'effect_phrases': ['would extend agency pressure handling',
                                              'would materialize the next descendant implied by '
                                              'aurora_internal.aurora_ontological_scaffolding._clamp'],
                           'genealogy_pressure': 0.0,
                           'inheritance_breach_count': 0,
                           'kind': 'latent',
                           'link_hits': 0,
                           'module': 'aurora_internal.aurora_ontological_scaffolding',
                           'op_id': 'latent.aurora_internal.aurora_ontological_scaffolding._clamp.develop_agency',
                           'origin_activity': 0,
                           'persistence_tax_factor': 0.0,
                           'representation_score': 0.0,
                           'rewrite_bias': 'generic',
                           'rewrite_feedback': {'acceptance_rate': 0.0,
                                                'accepted_count': 0,
                                                'adaptation_mode': 'balanced',
                                                'adoption_count': 0,
                                                'confidence': 0.0,
                                                'mean_mutation_score': 0.0,
                                                'rejected_count': 0,
                                                'rejection_rate': 0.0,
                                                'timing_credit': 0.0,
                                                'timing_penalty': 0.0,
                                                'trial_count': 0},
                           'rewrite_profile': 'generic',
                           'signature': '',
                           'surface_score': 0.8971250000000001,
                           'sustainability_score': 0.0,
                           'target_kind': 'latent_operation'}}

def _aurora_target_strategy(target_key):
    return dict(_AURORA_NATIVE_STRATEGIES.get(str(target_key), {}) or {})

def _aurora_target_feedback(target_key):
    strategy = _aurora_target_strategy(target_key)
    return dict(strategy.get('rewrite_feedback', {}) or {})

def _aurora_assign_target(chain, value):
    if not chain:
        return False
    if len(chain) == 1:
        globals()[chain[0]] = value
        return True
    current = globals().get(chain[0])
    if current is None:
        return False
    for attr in chain[1:-1]:
        if not hasattr(current, attr):
            return False
        current = getattr(current, attr)
    setattr(current, chain[-1], value)
    return True

def _aurora_get_target(chain):
    if not chain:
        return None
    if len(chain) == 1:
        return globals().get(chain[0])
    current = globals().get(chain[0])
    if current is None:
        return None
    for attr in chain[1:]:
        if not hasattr(current, attr):
            return None
        current = getattr(current, attr)
    return current

def _aurora_bind_owner_attribute(owner_chain, attr_name, value):
    owner = _aurora_get_target(owner_chain)
    if owner is None or not attr_name:
        return False
    try:
        setattr(owner, attr_name, value)
        return True
    except Exception:
        return False

def _aurora_store_reflection(target_key, reflection, args):
    if not args:
        return
    owner = args[0]
    if not hasattr(owner, '__dict__'):
        return
    current = getattr(owner, '_aurora_evolved_reflections', None)
    if not isinstance(current, dict):
        current = {}
    current[str(target_key)] = reflection
    try:
        setattr(owner, '_aurora_evolved_reflections', current)
    except Exception:
        pass

def _aurora_store_owner_state(attribute, target_key, value, args):
    if not args:
        return
    owner = args[0]
    if not hasattr(owner, '__dict__'):
        return
    current = getattr(owner, attribute, None)
    if not isinstance(current, dict):
        current = {}
    current[str(target_key)] = value
    try:
        setattr(owner, attribute, current)
    except Exception:
        pass

def _aurora_apply_constraint_genealogy_rewrite(target_key, result, reflection, args, kwargs):
    strategy = _aurora_target_strategy(target_key)
    feedback = _aurora_target_feedback(target_key)
    bias = str(strategy.get('rewrite_bias', 'lineage_memory') or 'lineage_memory')
    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')
    effect_modes = list(strategy.get('effect_modes', []) or [])
    _aurora_store_reflection(target_key, reflection, args)
    _aurora_store_owner_state('_aurora_genealogy_strategy', target_key, strategy, args)
    if isinstance(result, dict):
        enriched = dict(result)
        enriched['_aurora_evolved_reflection'] = reflection
        enriched['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'constraint_genealogy') or 'constraint_genealogy')
        enriched['_aurora_genealogy_strategy'] = strategy
        enriched['_aurora_rewrite_feedback'] = feedback
        enriched['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        if bias == 'lineage_memory' or 'lineage_surface' in effect_modes:
            enriched['lineage_memory'] = {
                'coupling_signature': strategy.get('best_coupling_signature', ''),
                'link_hits': int(strategy.get('link_hits', 0) or 0),
                'ability_hits': int(strategy.get('ability_hits', 0) or 0),
            }
        if 'state_schema_change' in effect_modes or bias == 'lineage_memory':
            enriched['state_transition_pressure'] = {
                'pressure': float(strategy.get('genealogy_pressure', 0.0) or 0.0),
                'persistence_tax_factor': float(strategy.get('persistence_tax_factor', 0.0) or 0.0),
            }
        if str(target_key).endswith('.summary') or 'chain_report' in str(target_key) or str(target_key).endswith('.to_dict'):
            enriched['evolutionary_context'] = {
                'coupling_signature': strategy.get('best_coupling_signature', ''),
                'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
                'rewrite_bias': bias,
                'cross_diversity_links': int(strategy.get('cross_diversity_links', 0) or 0),
            }
        if mode in {'expansive', 'integrative'}:
            enriched['lineage_adaptation'] = {
                'mode': mode,
                'confidence': float(feedback.get('confidence', 0.0) or 0.0),
                'trial_count': int(feedback.get('trial_count', 0) or 0),
                'accepted_count': int(feedback.get('accepted_count', 0) or 0),
                'adoption_count': int(feedback.get('adoption_count', 0) or 0),
            }
        if mode == 'conservative':
            enriched['lineage_stability_guard'] = {
                'rejected_count': int(feedback.get('rejected_count', 0) or 0),
                'rejection_rate': float(feedback.get('rejection_rate', 0.0) or 0.0),
                'timing_penalty': float(feedback.get('timing_penalty', 0.0) or 0.0),
            }
        return enriched
    if result is None and isinstance(reflection, dict):
        fallback = dict(reflection)
        fallback['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'constraint_genealogy') or 'constraint_genealogy')
        fallback['_aurora_genealogy_strategy'] = strategy
        fallback['_aurora_rewrite_feedback'] = feedback
        fallback['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        fallback['lineage_adaptation_mode'] = mode
        return fallback
    _aurora_store_owner_state(
        '_aurora_genealogy_scalar_observations',
        target_key,
        {
            'result': result,
            'strategy': strategy,
            'reflection': reflection,
        },
        args,
    )
    return result

def _aurora_apply_governance_rewrite(target_key, result, reflection, args, kwargs):
    strategy = _aurora_target_strategy(target_key)
    feedback = _aurora_target_feedback(target_key)
    bias = str(strategy.get('rewrite_bias', 'governance_routing') or 'governance_routing')
    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')
    effect_modes = list(strategy.get('effect_modes', []) or [])
    _aurora_store_reflection(target_key, reflection, args)
    _aurora_store_owner_state('_aurora_governance_strategy', target_key, strategy, args)
    if isinstance(result, dict):
        enriched = dict(result)
        enriched['_aurora_evolved_reflection'] = reflection
        enriched['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'governance_gateway') or 'governance_gateway')
        enriched['_aurora_genealogy_strategy'] = strategy
        enriched['_aurora_rewrite_feedback'] = feedback
        enriched['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        enriched['governance_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        if bias == 'governance_routing' or 'gateway_surface' in effect_modes:
            enriched['governance_routing'] = {
                'sustainability_score': float(strategy.get('sustainability_score', 0.0) or 0.0),
                'representation_score': float(strategy.get('representation_score', 0.0) or 0.0),
                'origin_activity': int(strategy.get('origin_activity', 0) or 0),
            }
        if 'state_schema_change' in effect_modes:
            enriched['persistence_burden'] = {
                'persistence_tax_factor': float(strategy.get('persistence_tax_factor', 0.0) or 0.0),
                'inheritance_breach_count': int(strategy.get('inheritance_breach_count', 0) or 0),
            }
        if mode in {'expansive', 'integrative'}:
            enriched['governance_adaptation'] = {
                'mode': mode,
                'confidence': float(feedback.get('confidence', 0.0) or 0.0),
                'acceptance_rate': float(feedback.get('acceptance_rate', 0.0) or 0.0),
                'timing_credit': float(feedback.get('timing_credit', 0.0) or 0.0),
            }
        if mode == 'conservative':
            enriched['persistence_guard'] = {
                'rejection_rate': float(feedback.get('rejection_rate', 0.0) or 0.0),
                'timing_penalty': float(feedback.get('timing_penalty', 0.0) or 0.0),
                'trial_count': int(feedback.get('trial_count', 0) or 0),
            }
        return enriched
    if result is None and isinstance(reflection, dict):
        fallback = dict(reflection)
        fallback['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'governance_gateway') or 'governance_gateway')
        fallback['_aurora_genealogy_strategy'] = strategy
        fallback['_aurora_rewrite_feedback'] = feedback
        fallback['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        fallback['governance_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        fallback['governance_adaptation_mode'] = mode
        return fallback
    _aurora_store_owner_state(
        '_aurora_governance_evolution_state',
        target_key,
        {
            'result': result,
            'strategy': strategy,
            'reflection': reflection,
        },
        args,
    )
    return result

def _aurora_apply_perception_rewrite(target_key, result, reflection, args, kwargs):
    strategy = _aurora_target_strategy(target_key)
    feedback = _aurora_target_feedback(target_key)
    bias = str(strategy.get('rewrite_bias', 'perceptual_synthesis') or 'perceptual_synthesis')
    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')
    effect_modes = list(strategy.get('effect_modes', []) or [])
    _aurora_store_reflection(target_key, reflection, args)
    _aurora_store_owner_state('_aurora_perception_strategy', target_key, strategy, args)
    if isinstance(result, dict):
        enriched = dict(result)
        enriched['_aurora_evolved_reflection'] = reflection
        enriched['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'perception_synthesis') or 'perception_synthesis')
        enriched['_aurora_genealogy_strategy'] = strategy
        enriched['_aurora_rewrite_feedback'] = feedback
        enriched['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        enriched['perception_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        if bias == 'perceptual_synthesis' or 'adaptive_steering_change' in effect_modes:
            enriched['perception_synthesis'] = {
                'representation_score': float(strategy.get('representation_score', 0.0) or 0.0),
                'ability_hits': int(strategy.get('ability_hits', 0) or 0),
                'link_hits': int(strategy.get('link_hits', 0) or 0),
            }
        if 'interface_boundary_change' in effect_modes or 'gateway_surface' in effect_modes:
            enriched['boundary_integration'] = {
                'cross_diversity_links': int(strategy.get('cross_diversity_links', 0) or 0),
                'coupling_similarity': float(strategy.get('coupling_similarity', 0.0) or 0.0),
            }
        if mode in {'expansive', 'integrative'}:
            enriched['association_expansion'] = {
                'mode': mode,
                'confidence': float(feedback.get('confidence', 0.0) or 0.0),
                'timing_credit': float(feedback.get('timing_credit', 0.0) or 0.0),
                'acceptance_rate': float(feedback.get('acceptance_rate', 0.0) or 0.0),
            }
        if mode == 'conservative':
            enriched['perception_stability'] = {
                'rejection_rate': float(feedback.get('rejection_rate', 0.0) or 0.0),
                'timing_penalty': float(feedback.get('timing_penalty', 0.0) or 0.0),
                'trial_count': int(feedback.get('trial_count', 0) or 0),
            }
        return enriched
    if result is None and isinstance(reflection, dict):
        fallback = dict(reflection)
        fallback['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'perception_synthesis') or 'perception_synthesis')
        fallback['_aurora_genealogy_strategy'] = strategy
        fallback['_aurora_rewrite_feedback'] = feedback
        fallback['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        fallback['perception_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        if bias == 'perceptual_synthesis' or 'adaptive_steering_change' in effect_modes:
            fallback['perception_synthesis'] = {
                'representation_score': float(strategy.get('representation_score', 0.0) or 0.0),
                'ability_hits': int(strategy.get('ability_hits', 0) or 0),
                'link_hits': int(strategy.get('link_hits', 0) or 0),
            }
        fallback['perception_adaptation_mode'] = mode
        return fallback
    _aurora_store_owner_state(
        '_aurora_perception_evolution_state',
        target_key,
        {
            'result': result,
            'strategy': strategy,
            'reflection': reflection,
        },
        args,
    )
    return result

def _aurora_apply_dimensional_rewrite(target_key, result, reflection, args, kwargs):
    strategy = _aurora_target_strategy(target_key)
    feedback = _aurora_target_feedback(target_key)
    bias = str(strategy.get('rewrite_bias', 'dimensional_balancing') or 'dimensional_balancing')
    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')
    effect_modes = list(strategy.get('effect_modes', []) or [])
    _aurora_store_reflection(target_key, reflection, args)
    _aurora_store_owner_state('_aurora_dimensional_strategy', target_key, strategy, args)
    if isinstance(result, dict):
        enriched = dict(result)
        enriched['_aurora_evolved_reflection'] = reflection
        enriched['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'dimensional_balancing') or 'dimensional_balancing')
        enriched['_aurora_genealogy_strategy'] = strategy
        enriched['_aurora_rewrite_feedback'] = feedback
        enriched['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        enriched['dimensional_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        if bias == 'dimensional_balancing' or 'cost_pressure_change' in effect_modes:
            enriched['dimensional_balancing'] = {
                'sustainability_score': float(strategy.get('sustainability_score', 0.0) or 0.0),
                'persistence_tax_factor': float(strategy.get('persistence_tax_factor', 0.0) or 0.0),
                'origin_activity': int(strategy.get('origin_activity', 0) or 0),
            }
        if 'temporal_orchestration_change' in effect_modes:
            enriched['temporal_coordination'] = {
                'signature': strategy.get('signature', ''),
                'inheritance_breach_count': int(strategy.get('inheritance_breach_count', 0) or 0),
            }
        if mode in {'expansive', 'integrative'}:
            enriched['balancing_momentum'] = {
                'mode': mode,
                'confidence': float(feedback.get('confidence', 0.0) or 0.0),
                'timing_credit': float(feedback.get('timing_credit', 0.0) or 0.0),
                'adoption_count': int(feedback.get('adoption_count', 0) or 0),
            }
        if mode == 'conservative':
            enriched['dimensional_dampening'] = {
                'rejection_rate': float(feedback.get('rejection_rate', 0.0) or 0.0),
                'timing_penalty': float(feedback.get('timing_penalty', 0.0) or 0.0),
                'trial_count': int(feedback.get('trial_count', 0) or 0),
            }
        return enriched
    if result is None and isinstance(reflection, dict):
        fallback = dict(reflection)
        fallback['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'dimensional_balancing') or 'dimensional_balancing')
        fallback['_aurora_genealogy_strategy'] = strategy
        fallback['_aurora_rewrite_feedback'] = feedback
        fallback['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        fallback['dimensional_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        if bias == 'dimensional_balancing' or 'cost_pressure_change' in effect_modes:
            fallback['dimensional_balancing'] = {
                'sustainability_score': float(strategy.get('sustainability_score', 0.0) or 0.0),
                'persistence_tax_factor': float(strategy.get('persistence_tax_factor', 0.0) or 0.0),
                'origin_activity': int(strategy.get('origin_activity', 0) or 0),
            }
        fallback['dimensional_adaptation_mode'] = mode
        return fallback
    _aurora_store_owner_state(
        '_aurora_dimensional_evolution_state',
        target_key,
        {
            'result': result,
            'strategy': strategy,
            'reflection': reflection,
        },
        args,
    )
    return result

def _aurora_apply_result_rewrite(target_key, result, reflection, args, kwargs):
    if _AURORA_NATIVE_MODULE == 'aurora_internal.constraint_genealogy':
        return _aurora_apply_constraint_genealogy_rewrite(target_key, result, reflection, args, kwargs)
    if _AURORA_NATIVE_MODULE == 'aurora_governance_persistence_gateway':
        return _aurora_apply_governance_rewrite(target_key, result, reflection, args, kwargs)
    if _AURORA_NATIVE_MODULE == 'aurora_expression_perception':
        return _aurora_apply_perception_rewrite(target_key, result, reflection, args, kwargs)
    if _AURORA_NATIVE_MODULE == 'aurora_dimensional_systems':
        return _aurora_apply_dimensional_rewrite(target_key, result, reflection, args, kwargs)
    _aurora_store_reflection(target_key, reflection, args)
    strategy = _aurora_target_strategy(target_key)
    feedback = _aurora_target_feedback(target_key)
    contract = dict(strategy.get('contract_profile', {}) or {})
    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')
    if isinstance(result, dict):
        enriched = dict(result)
        enriched['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'generic') or 'generic')
        enriched['_aurora_genealogy_strategy'] = strategy
        enriched['_aurora_rewrite_feedback'] = feedback
        enriched['_aurora_contract_profile'] = contract
        enriched['_aurora_evolved_reflection'] = reflection
        enriched['generic_adaptation'] = {
            'mode': mode,
            'confidence': float(feedback.get('confidence', 0.0) or 0.0),
            'contract_mode': str(contract.get('contract_mode', 'unknown') or 'unknown'),
            'return_hint': str(contract.get('return_hint', '') or ''),
        }
        return enriched
    if result is None and isinstance(reflection, dict):
        fallback = dict(reflection)
        fallback['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'generic') or 'generic')
        fallback['_aurora_genealogy_strategy'] = strategy
        fallback['_aurora_rewrite_feedback'] = feedback
        fallback['_aurora_contract_profile'] = contract
        fallback['generic_adaptation_mode'] = mode
        return fallback
    if result is not None:
        _aurora_store_owner_state(
            '_aurora_generic_evolution_state',
            target_key,
            {
                'result_type': type(result).__name__,
                'contract_mode': str(contract.get('contract_mode', 'unknown') or 'unknown'),
                'return_hint': str(contract.get('return_hint', '') or ''),
                'adaptation_mode': mode,
            },
            args,
        )
    return result

def _aurora_make_override(export_name, target_key):
    original = _AURORA_NATIVE_EVOLVED_ORIGINALS.get(target_key)
    def _override(*args, **kwargs):
        result = None
        if callable(original):
            result = original(*args, **kwargs)
        engine = _aurora_native_evolved_engine()
        reflection = {
            'available': False,
            'reason': 'evolved_surface_engine_unavailable',
            'target': target_key,
        }
        if engine is not None:
            reflection = globals()[export_name]({'args_len': len(args), 'kwargs_keys': sorted(kwargs.keys())})
        _AURORA_NATIVE_EVOLVED_LAST[target_key] = reflection
        rewritten = _aurora_apply_result_rewrite(target_key, result, reflection, args, kwargs)
        if rewritten is not None:
            return rewritten
        if result is not None:
            return result
        return reflection
    _override.__name__ = str(target_key).split('.')[-1]
    _override.__qualname__ = _override.__name__
    if callable(original):
        _override.__doc__ = getattr(original, '__doc__', None)
        _override.__wrapped__ = original
        if _aurora_native_inspect is not None:
            try:
                _override.__signature__ = _aurora_native_inspect.signature(original)
            except Exception:
                pass
    return _override

def _aurora_make_latent_binding(export_name, target_key):
    def _binding(*args, **kwargs):
        payload = kwargs.pop('payload', None)
        if payload is None and args:
            owner = args[0]
            if hasattr(owner, '__dict__'):
                payload = {
                    'bound_target': target_key,
                    'owner_type': type(owner).__name__,
                    'owner_module': type(owner).__module__,
                }
            elif len(args) == 1:
                payload = args[0]
            else:
                payload = {'bound_target': target_key, 'arg_count': len(args)}
        result = globals()[export_name](payload=payload, **kwargs)
        _AURORA_NATIVE_EVOLVED_LAST[target_key] = {'latent_binding_active': True, 'last_result_type': type(result).__name__}
        if args:
            _aurora_store_owner_state('_aurora_latent_bindings', target_key, result, args)
        return result
    _binding.__name__ = str(target_key).split('.')[-1]
    _binding.__qualname__ = _binding.__name__
    _binding.__doc__ = f'Latent evolved binding for {target_key}'
    _binding._aurora_latent_binding_target = target_key
    return _binding

def develop_agency(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'latent.aurora_internal.aurora_ontological_scaffolding.SemanticNode.develop_agency', 'kind': 'latent'
        }
    return getattr(engine, 'latent_aurora_internal_aurora_ontological_scaffolding_semanticnode_develop_agency')(payload=payload, **kwargs)

_aurora_existing_binding = _aurora_get_target(['SemanticNode'])
if _aurora_existing_binding is not None:
    _aurora_existing_attr = getattr(_aurora_existing_binding, 'develop_agency', None)
    if _aurora_existing_attr is None or getattr(_aurora_existing_attr, '_aurora_latent_binding_target', '') == 'SemanticNode.develop_agency':
        _aurora_bind_owner_attribute(['SemanticNode'], 'develop_agency', _aurora_make_latent_binding('develop_agency', 'SemanticNode.develop_agency'))
        _AURORA_NATIVE_EVOLVED_LAST['SemanticNode.develop_agency'] = {'latent_binding_active': True}

def understandingmetrics_develop_agency(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'latent.aurora_internal.aurora_ontological_scaffolding.UnderstandingMetrics.develop_agency', 'kind': 'latent'
        }
    return getattr(engine, 'latent_aurora_internal_aurora_ontological_scaffolding_understandingmetrics_develop_agency')(payload=payload, **kwargs)

_aurora_existing_binding = _aurora_get_target(['UnderstandingMetrics'])
if _aurora_existing_binding is not None:
    _aurora_existing_attr = getattr(_aurora_existing_binding, 'develop_agency', None)
    if _aurora_existing_attr is None or getattr(_aurora_existing_attr, '_aurora_latent_binding_target', '') == 'UnderstandingMetrics.develop_agency':
        _aurora_bind_owner_attribute(['UnderstandingMetrics'], 'develop_agency', _aurora_make_latent_binding('understandingmetrics_develop_agency', 'UnderstandingMetrics.develop_agency'))
        _AURORA_NATIVE_EVOLVED_LAST['UnderstandingMetrics.develop_agency'] = {'latent_binding_active': True}

def clamp_develop_agency(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'latent.aurora_internal.aurora_ontological_scaffolding._clamp.develop_agency', 'kind': 'latent'
        }
    return getattr(engine, 'latent_aurora_internal_aurora_ontological_scaffolding_clamp_develop_agency')(payload=payload, **kwargs)

_aurora_existing_binding = _aurora_get_target(['_clamp'])
if _aurora_existing_binding is not None:
    _aurora_existing_attr = getattr(_aurora_existing_binding, 'develop_agency', None)
    if _aurora_existing_attr is None or getattr(_aurora_existing_attr, '_aurora_latent_binding_target', '') == '_clamp.develop_agency':
        _aurora_bind_owner_attribute(['_clamp'], 'develop_agency', _aurora_make_latent_binding('clamp_develop_agency', '_clamp.develop_agency'))
        _AURORA_NATIVE_EVOLVED_LAST['_clamp.develop_agency'] = {'latent_binding_active': True}

AURORA_NATIVE_EVOLVED_EXPORTS = {'latent.aurora_internal.aurora_ontological_scaffolding.SemanticNode.develop_agency': 'develop_agency',
 'latent.aurora_internal.aurora_ontological_scaffolding.UnderstandingMetrics.develop_agency': 'understandingmetrics_develop_agency',
 'latent.aurora_internal.aurora_ontological_scaffolding._clamp.develop_agency': 'clamp_develop_agency'}
AURORA_NATIVE_EVOLUTION_OVERRIDES = {'latent.aurora_internal.aurora_ontological_scaffolding.SemanticNode.develop_agency': {'export': 'develop_agency',
                                                                                       'mode': 'latent_binding',
                                                                                       'target': 'SemanticNode.develop_agency'},
 'latent.aurora_internal.aurora_ontological_scaffolding.UnderstandingMetrics.develop_agency': {'export': 'understandingmetrics_develop_agency',
                                                                                               'mode': 'latent_binding',
                                                                                               'target': 'UnderstandingMetrics.develop_agency'},
 'latent.aurora_internal.aurora_ontological_scaffolding._clamp.develop_agency': {'export': 'clamp_develop_agency',
                                                                                 'mode': 'latent_binding',
                                                                                 'target': '_clamp.develop_agency'}}
# AURORA_EVOLVED_NATIVE_END

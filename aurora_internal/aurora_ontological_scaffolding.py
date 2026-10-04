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
from aurora_internal.aurora_runtime_faults import record_exception_from_locals as _aurora_record_exception_from_locals
# Authors: Sunni (Sir) Morningstar & Cael Devo

import time
import math
import hashlib
import random
import json
import re
from enum import Enum, IntEnum, auto
from typing import Dict, List, Any, Optional, Tuple, Set, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque

# ============================================================================
# IMPORTS FROM LOWER LAYERS
# ============================================================================

from aurora_internal.aurora_noncomp_registry import AXIS_NC_DIM
# FIX-A010 (Sunni & Cael, comprehension pressure test follow-up, build 650):
# OntologicalWeb is the actual relation-typing surface and, until now, was
# the only major comprehension subsystem NOT WarpCapable -- ExpressionPerceptionEngine
# (representation discovery) and AuroraRecursiveCausalReasoningWaveform both
# have a real gap-detection/trial/promotion pathway; relation-typing had none
# at any layer. This import wires the SAME existing mixin onto this class.
# Plumbing only -- see class docstring below for what is and is not decided here.
from aurora_warp_protocol import WarpCapable, CoverageGap, WarpComponent

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


# Relation weights — how much each type contributes to ontological depth
class DiscoveredRelationKind:
    """A relation kind Aurora discovered, first-class beside the seed ``RelationType``.

    The seed enum is a starting vocabulary, not a ceiling.  A kind carries an axis
    profile and lineage (its component id), never a gloss.  It duck-types the enum
    wherever the web reads ``.value`` or uses a type as a key.
    """

    __slots__ = ("value", "axis_profile")

    def __init__(self, value: str, axis_profile: Optional[Dict[str, float]] = None) -> None:
        self.value = str(value)
        self.axis_profile = dict(axis_profile or {})

    @property
    def name(self) -> str:
        return self.value.upper()

    def __hash__(self) -> int:
        return hash(("discovered_relation_kind", self.value))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, DiscoveredRelationKind) and other.value == self.value

    def __repr__(self) -> str:
        return f"DiscoveredRelationKind({self.value!r})"


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
}


# FIX-A010: bridges the already-canonical X/T/N/B/A axis definitions
# (declared once in aurora_constraint_semantic_continuity.py: X=existence/
# admissibility, T=continuity/causality, N=pressure/purpose/change,
# B=boundary/structure, A=agency/selection/understanding) onto the
# already-existing RelationType vocabulary, using each type's own authored
# description comment above as the basis for which roots it occupies. This
# is a translation between two ontologies that already exist in the
# codebase, not a new interpretation of what any relation type means.
# RELATED_TO is deliberately flat/undifferentiated -- it is the generic
# catch-all, and staying weak on every axis is exactly why AxisCoverageChecker
# should be able to register a persistent gap when live data carries a
# strong signal RELATED_TO cannot structurally account for.
RELATION_TYPE_AXIS_PROFILES: Dict["RelationType", Dict[str, float]] = {
    RelationType.CAUSES:      {"X": 0.15, "T": 0.55, "N": 0.55, "B": 0.15, "A": 0.20},
    RelationType.IMPLIES:     {"X": 0.15, "T": 0.30, "N": 0.50, "B": 0.55, "A": 0.20},
    RelationType.PRECEDES:    {"X": 0.10, "T": 0.70, "N": 0.20, "B": 0.15, "A": 0.10},
    RelationType.ENABLES:     {"X": 0.15, "T": 0.20, "N": 0.55, "B": 0.15, "A": 0.50},
    RelationType.CONTRASTS:   {"X": 0.20, "T": 0.10, "N": 0.15, "B": 0.65, "A": 0.15},
    RelationType.OPPOSITE_OF: {"X": 0.20, "T": 0.10, "N": 0.10, "B": 0.70, "A": 0.10},
    RelationType.IS_A:        {"X": 0.55, "T": 0.10, "N": 0.10, "B": 0.50, "A": 0.10},
    RelationType.HAS_A:       {"X": 0.50, "T": 0.10, "N": 0.15, "B": 0.45, "A": 0.10},
    RelationType.PART_OF:     {"X": 0.50, "T": 0.10, "N": 0.15, "B": 0.50, "A": 0.10},
    RelationType.INSTANCE_OF: {"X": 0.55, "T": 0.10, "N": 0.10, "B": 0.40, "A": 0.10},
    RelationType.CONTEXT_OF:  {"X": 0.35, "T": 0.15, "N": 0.20, "B": 0.45, "A": 0.15},
    RelationType.RELATED_TO:  {"X": 0.20, "T": 0.20, "N": 0.20, "B": 0.20, "A": 0.20},
}

# FIX-A011: how close a role-pair's axis signal must be (cosine) to an
# existing relation type's profile to be SELECTED as that type, rather than
# falling through to RELATED_TO + a registered WARP gap. Set below the
# stricter COVERAGE_THRESHOLD (0.82, used elsewhere to decide whether a
# wholly NEW type is warranted) because role-pair signals are coarse by
# construction -- this bar only decides among the 12 types that already
# exist, it never blocks new-type discovery.
_RELATION_SELECTION_THRESHOLD = 0.70

# FIX-A013: how many times a (signature, type) pairing must have been
# selected before its failure rate is trusted enough to discount future
# selection or escalate to WARP pressure -- guards against one unlucky
# early reconciliation looking like a pattern.
_SELECTION_FAILURE_MIN_USES = 3
# FIX-A013: aggregated failure rate (failures / uses) for a (signature,
# type) pairing above which it counts as a genuine recurring gap, not
# noise -- deliberately below 1.0 since a pairing that's right most of the
# time but wrong sometimes shouldn't need to be perfect to keep being used.
_SELECTION_FAILURE_RATE_THRESHOLD = 0.5


def _role_pair_axis_signal(r1: str, r2: str) -> Dict[str, float]:
    """FIX-A010: the mechanical axis reading of a (role1, role2) pair for
    coverage-checking purposes. Same X=entity/existence, A=agency/action,
    B=boundary/distinction bridging RELATION_TYPE_AXIS_PROFILES already
    uses -- not a new mapping, the same one applied to the input side
    instead of the relation-type side.
    """
    weight = {"X": 0.2, "T": 0.2, "N": 0.2, "B": 0.2, "A": 0.2}
    for role in (r1, r2):
        if role == "noun":
            weight["X"] += 0.25
        elif role == "verb":
            weight["A"] += 0.25
            weight["N"] += 0.1
        elif role == "adjective":
            weight["B"] += 0.25
        elif role == "adverb":
            weight["N"] += 0.2
    total = sum(weight.values()) or 1.0
    return {k: v / total for k, v in weight.items()}


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
    # FIX-A013 (Sunni & Cael): which role-pair signature selected this
    # relation's type, so a later reconciliation (FIX-A012) can attribute a
    # failure back to the SELECTION PATTERN that produced it, not just this
    # one relation -- letting failures aggregate across every entity pair
    # that ever shared the same structural signature, which is the whole
    # point: a gap in understanding shows up as a pattern across many
    # different experiences, not as one bad relation.
    selection_signature: str = ""

    def depth_contribution(self) -> float:
        """How much this relation contributes to ontological depth."""
        weight = RELATION_DEPTH_WEIGHTS.get(self.relation_type, 0.3)
        return weight * self.strength * self.confidence


@dataclass
class SenseRecord:
    """One word sense (a specific meaning) of a concept.

    Build 771 (Constraint-Native Lexical Grounding): `gloss` is a literal
    English string, and every real caller of add_sense() today writes it
    from scaffolding (a hand-authored rule) or from a live user's own
    explanation -- never from Aurora's own consequence-derived evidence.
    `source` is the existing, already-real provenance record for that (no
    new field needed) -- confirmed live values in use: "use_expansion"
    (aurora.py, a live user teaching a new sense during conversation --
    genuine lived evidence, not scaffolding) and "test"/"mock" (test
    fixtures). Nothing here changes those. The one thing this build adds is
    a name for the previously-implicit "nobody said where this came from"
    case: the default is now "inherited_scaffold" rather than the vaguer
    "inferred", since an unattributed sense is exactly the "provisional
    evidence, not earned" case this directive is about. A future
    consequence-earned grounding (constraint_genealogy-registered, no gloss
    read by any selection logic) would write "constraint_earned" here --
    not built by this record alone; see aurora_lexical_grounding.py.
    """
    sense_id:    str          # e.g. "mean.cruel", "mean.average", "mean.intend"
    gloss:       str          # short definition of this sense
    source:      str = "inherited_scaffold"
    confidence:  float = 0.3
    context_clues: List[str] = field(default_factory=list)  # tokens that activate this sense
    times_activated: int = 0
    last_activated:  float = field(default_factory=time.time)
    # Build 771 PR 4: pointer to the constraint_genealogy AbilityProfile
    # this sense's consequence-earned grounding was registered under (via
    # aurora_lexical_grounding.py's register_emergent_lexical_grounding()),
    # set only when source == "constraint_earned". gloss itself is never
    # read by any selection/scoring logic -- this pointer is how a
    # consequence-earned sense's real ancestry is actually traced, not the
    # English string.
    grounded_ability_id: str = ""

    def activate(self, context_tokens: List[str] = None):
        self.times_activated += 1
        self.last_activated = time.time()
        if context_tokens:
            for tok in context_tokens:
                if tok not in self.context_clues:
                    self.context_clues.append(tok)
            self.context_clues = self.context_clues[:20]


# Directive NC1, ratified 2026-08-03 (Sunni & Cael). Role -> primary axis
# mapping for noncomp_id assignment. Grounded in X/T/N/B/A doctrine:
#   noun/determiner -> X (existence: what a thing IS)
#   verb            -> T (temporal: action unfolds across time)
#   adjective/preposition -> B (boundary: qualifies/bounds/relates)
#   adverb          -> N (energy: manner/intensity of expenditure)
#   pronoun         -> A (agency: self/other reference)
ROLE_TO_AXIS = {
    "noun": "X", "verb": "T", "adjective": "B",
    "adverb": "N", "pronoun": "A", "preposition": "B",
    "determiner": "X",
}


def _noncomp_id_for_role(role: str):
    axis = ROLE_TO_AXIS.get(role)
    return f"{axis}:{AXIS_NC_DIM[axis]}" if axis else None


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

    # Non-computational ID (for alignment)
    noncomp_id: Optional[str] = None

    # Learning history
    times_encountered: int = 0
    times_used_in_expression: int = 0
    times_researched: int = 0
    first_encountered: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)

    # Lineage tracking
    lineage: str = ""                   # Which i-state lineage introduced this

    # Perf (2026-08-20): running sum of depth_contribution() across every
    # relation on this node, maintained incrementally by add_relation()/
    # adjust_relation_contribution() instead of _recalculate_depth()
    # rescanning self.relations.values() on every call -- confirmed via
    # cProfile as a dominant cost on hub words (some carry hundreds of
    # relations from baseline seeding), compounding on every single
    # relation addition. Not part of equality/repr -- it's a derived
    # cache, not identity.
    _rel_contribution_sum: float = field(default=0.0, repr=False, compare=False)

    def add_sense(self, sense_id: str, gloss: str, source: str = "inferred",
                  confidence: float = 0.3, context_clues: List[str] = None,
                  grounded_ability_id: str = ""):
        """Add or reinforce a word sense.

        grounded_ability_id (Build 771 PR 4): optional pointer to the
        constraint_genealogy AbilityProfile this sense's grounding was
        registered under. Only aurora_lexical_grounding.py's promotion
        write-back passes this; every other existing caller omits it and
        gets the prior behavior unchanged.
        """
        if sense_id in self.senses:
            sr = self.senses[sense_id]
            sr.confidence = min(1.0, sr.confidence + 0.05)
            if context_clues:
                sr.activate(context_clues)
            if grounded_ability_id:
                sr.grounded_ability_id = grounded_ability_id
        else:
            self.senses[sense_id] = SenseRecord(
                sense_id=sense_id, gloss=gloss, source=source,
                confidence=confidence,
                context_clues=context_clues or [],
                grounded_ability_id=grounded_ability_id,
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
        self._update_comprehension_confidence()
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
        if relation.relation_id not in self.relations:
            self._rel_contribution_sum += relation.depth_contribution()
        self.relations[relation.relation_id] = relation
        self._recalculate_depth()

    def adjust_relation_contribution(self, delta: float) -> None:
        """Incrementally correct the cached relation-contribution sum when
        an already-attached relation's strength/confidence changes in
        place (the "strengthen existing relation" paths), instead of
        _recalculate_depth() rescanning every relation on this node.
        Callers compute delta as (new_contribution - old_contribution),
        captured via depth_contribution() immediately before and after
        the mutation. Clamped at 0 as a defensive floor only -- weight,
        strength, and confidence are all non-negative, so a correctly
        computed delta should never actually drive the sum negative."""
        self._rel_contribution_sum = max(0.0, self._rel_contribution_sum + delta)

    def remove_relation(self, relation_id: str) -> None:
        """Detach a relation (pruning) and correct the cached sum to
        match -- counterpart to add_relation()'s increment."""
        rel = self.relations.pop(relation_id, None)
        if rel is not None:
            self._rel_contribution_sum = max(
                0.0, self._rel_contribution_sum - rel.depth_contribution()
            )

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

        # Relation depth (0-0.4) — the biggest contributor.
        # Perf (2026-08-20): was `sum(r.depth_contribution() for r in
        # self.relations.values())`, rescanning every relation on this
        # node on every call -- confirmed via cProfile as a dominant cost
        # in ordinary message processing, worst on hub words with
        # hundreds of relations from baseline seeding. _rel_contribution_sum
        # is kept incrementally correct by add_relation()/
        # adjust_relation_contribution()/remove_relation(), so this is now
        # an O(1) read for the same value.
        if self.relations:
            rel_count = len(self.relations)
            rel_depth = min(0.4, self._rel_contribution_sum / rel_count
                           * min(rel_count, 8) / 8 * 0.4)
        else:
            rel_depth = 0.0

        # Research bonus (0-0.1)
        research_depth = min(0.1, self.times_researched * 0.03)

        self.ontological_depth = _clamp(def_depth + ex_depth + rel_depth + research_depth)
        self._update_scaffolding_level()
        self._update_comprehension_confidence()
        self._recalculate_priority()

    def _update_comprehension_confidence(self):
        """
        Update comprehension_confidence from real evidence of understanding:
        ontological depth (the same definitions/examples/relations/research
        signal driving scaffolding_level) plus accumulated exposure.

        Before this, the field only ever moved via its 0.1 dataclass default
        or a one-time manual boost for a handful of hand-seeded identity
        words (seed_identity_into_oets) -- nothing in the real study/
        consolidation pipeline touched it for ordinary vocabulary, so a word
        encountered thousands of times (verified: "am" at 1,614 encounters)
        stayed pinned at 0.1, well under the 0.5 threshold
        aurora_constraint_emission.py gates "what do you mean by X" on.
        Uses max() so it only ever grows toward what the evidence supports,
        never erodes an already-earned or seeded confidence.
        """
        encounter_component = min(0.3, math.log1p(self.times_encountered) * 0.05)
        self.comprehension_confidence = max(
            self.comprehension_confidence,
            _clamp(self.ontological_depth + encounter_component),
        )

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

class OntologicalWeb(WarpCapable):
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

    FIX-A010: WarpCapable as of build 650. This gives relation-typing the
    same gap-detection/trial/promotion organ ExpressionPerceptionEngine and
    AuroraRecursiveCausalReasoningWaveform already have. What this DOES:
    lets a persistent structural mismatch (live axis signal a generic
    RELATED_TO/ENABLES fallback can't account for) register as a real WARP
    gap and spawn a trial component. What this explicitly does NOT do:
    decide what a new relation type means, author a verb->RelationType
    lookup table, or pre-select which of the 12 existing types resolves a
    gap. That stays undecided by this change -- WarpGenerator's existing
    synthesis path handles it exactly as it does for every other
    WarpCapable level, with zero special-casing added here.
    """

    MAX_NODES = 5000      # Maximum concepts in the web
    MAX_RELATIONS = 20000  # Maximum connections

    def __init__(self):
        self._init_warp()
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
        # Inverted index: word → primary category (O(1) lookup for _analyze_pattern_depth)
        self._word_to_category: Dict[str, str] = {}

        # Growth metrics
        self.total_relations_created = 0
        self.total_research_cycles = 0
        self.total_consolidations = 0

        # FIX-A010: trial relation-type components, keyed by component_id.
        # Mechanical bookkeeping only -- what a trial IS (what axis profile,
        # what parentage) comes from WarpGenerator via the base class, not
        # authored here.
        self._relation_trial_usage: Dict[str, Dict[str, int]] = {}
        self._open_kinds: Dict[str, "DiscoveredRelationKind"] = {}
        # FIX-A013: signature -> type_value -> {"uses","failures"}. Aggregates
        # across every entity pair that has ever shared a given structural
        # signature, so a recurring selection mistake shows up as a pattern
        # the moment it recurs anywhere, not just on the entities that first
        # revealed it.
        self._selection_outcomes: Dict[str, Dict[str, Dict[str, int]]] = {}

        # Perf (2026-08-20): _select_relation_type() used to rebuild this
        # from RELATION_TYPE_AXIS_PROFILES (a fixed module-level constant)
        # on every single call -- confirmed live via cProfile as one of
        # the two dominant hotspots in ordinary message processing (96,111
        # calls for a 12-message corpus run). The table never changes at
        # runtime, so build it once and reuse it.
        self._relation_type_checker: Optional[Any] = None

        # Perf (2026-08-20): _select_relation_type()'s raw_scores (cosine
        # similarity per candidate relation type) depends only on the
        # (r1, r2) role-pair signature, never on the dynamic
        # self._selection_outcomes discount -- see that method's docstring
        # for the full reasoning. Unbounded only in theory; role values
        # come from a small closed vocabulary, so this stays tiny in
        # practice.
        self._raw_score_cache: Dict[str, Dict[str, float]] = {}

    # ================================================================
    # WARP SURFACE (FIX-A010) — plumbing only, see class docstring
    # ================================================================

    def _warp_level_name(self) -> str:
        return "ontological_relation_typing"

    def _get_axis_profiles(self) -> Dict[str, Dict[str, float]]:
        """Every currently-known relation type's axis profile, plus any
        already-promoted trial types. Mechanical translation table (see
        RELATION_TYPE_AXIS_PROFILES above) -- adds nothing beyond what's
        already declared there.
        """
        profiles: Dict[str, Dict[str, float]] = {
            f"RELTYPE:{rtype.value}": dict(profile)
            for rtype, profile in RELATION_TYPE_AXIS_PROFILES.items()
        }
        for comp_id, comp in self._warp_promoted.items():
            profiles[str(comp_id)] = dict(comp.axis_profile)
        return profiles

    def _integrate_warp(self, component: "WarpComponent") -> None:
        """Register a new trial relation-type-shaped component. Records
        that it exists and starts its usage counters at zero -- does not
        assign it meaning or wire it into add_relation()'s type choice;
        that connection is the next step, not this one.
        """
        self._relation_trial_usage[component.component_id] = {"uses": 0, "successes": 0}
        self._open_kinds[component.component_id] = DiscoveredRelationKind(component.component_id, component.axis_profile)

    def _score_trial(self, component: "WarpComponent") -> float:
        """Mirrors AuroraRecursiveCausalReasoningWaveform._score_trial's own
        shape: untested trials sit at a neutral floor rather than an
        assumed pass or fail; scored trials move on observed usage/success
        ratio only, once something downstream actually starts using them.
        """
        usage = self._relation_trial_usage.get(component.component_id) or {}
        uses = max(0, int(usage.get("uses", 0) or 0))
        if uses <= 0:
            return 0.25
        successes = max(0, int(usage.get("successes", 0) or 0))
        return max(0.0, min(1.0, 0.35 + 0.55 * (successes / max(1, uses))))

    def _dissolve_warp(self, component_id: str) -> None:
        self._relation_trial_usage.pop(str(component_id), None)
        self._open_kinds.pop(str(component_id), None)

    def _warp_params(self, gap: "CoverageGap", parent_ids: List[str]) -> Dict[str, Any]:
        return {
            "source": str(getattr(gap, "source", "") or ""),
            "parent_ids": list(parent_ids or []),
        }

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
        node.noncomp_id = _noncomp_id_for_role(role)
        if meaning:
            node.add_definition(meaning, source="initial", confidence=0.3)

        self.nodes[word] = node
        self._nodes_by_role[role].add(word)

        # Assign initial semantic category from role + meaning
        if meaning:
            category = self._infer_category(word, role, meaning)
            if category:
                self._semantic_categories[category].add(word)
                self._word_to_category[word] = category

        # Enforce capacity
        if len(self.nodes) > self.MAX_NODES:
            self._prune_nodes()

        return node

    def get_node(self, word: str) -> Optional[SemanticNode]:
        """Retrieve a concept node."""
        return self.nodes.get(word)

    def has_node(self, word: str) -> bool:
        return word in self.nodes

    # Build 598 (Relation-Typing Pressure Calibration): the two role-pair
    # combinations infer_relations_from_context() already types with
    # positive confidence -- verb+noun -> ENABLES, adjective+noun ->
    # CONTEXT_OF. Every other role pair still falls through that same
    # function to the generic RELATED_TO/"co-occurrence" label. This is
    # read-only lookup metadata, not a rule to encode a classifier from.
    _NC1_COVERED_ROLE_PAIRS = (frozenset({"verb", "noun"}), frozenset({"adjective", "noun"}))

    def record_relation_trial_use(self, component_id: str) -> None:
        """A trial/promoted kind was selected.  (Nothing used to increment this, which left
        every trial at its neutral floor forever.)"""
        usage = self._relation_trial_usage.setdefault(str(component_id), {"uses": 0, "successes": 0})
        usage["uses"] = int(usage.get("uses", 0) or 0) + 1

    def record_relation_trial_outcome(self, component_id: str, success: bool) -> None:
        """Consequence for a discovered kind, from any source that can judge it."""
        usage = self._relation_trial_usage.setdefault(str(component_id), {"uses": 0, "successes": 0})
        if success:
            usage["successes"] = int(usage.get("successes", 0) or 0) + 1
        else:
            usage["failures"] = int(usage.get("failures", 0) or 0) + 1

    def underworked_relation_type_pairs(self, limit: int = 10) -> List[Dict[str, str]]:
        """Read-only enumeration of RELATED_TO relations whose role-pair
        combination is NOT already covered by the two ratified NC1
        heuristics, and whose source_of_knowledge is the honestly-untyped
        generic co-occurrence pass (infer_relations_from_context()'s first
        loop). This is the population a relation-typing trial surface
        should prioritize stressing -- the existing heuristics already have
        positive evidence for their two covered role pairs, so probing
        those again would not add anything new. Returns dicts, never
        SemanticRelation/RelationType objects, and writes nothing."""
        candidates: List[Dict[str, str]] = []
        seen_pairs: Set[Tuple[str, str]] = set()
        for rel_id in self._relations_by_type.get(RelationType.RELATED_TO, set()):
            rel = self.relations.get(rel_id)
            if rel is None or rel.source_of_knowledge != "co-occurrence":
                continue
            source_node = self.nodes.get(rel.source_word)
            target_node = self.nodes.get(rel.target_word)
            if source_node is None or target_node is None:
                continue
            role_pair = frozenset({source_node.role, target_node.role})
            if role_pair in self._NC1_COVERED_ROLE_PAIRS:
                continue
            pair_key = tuple(sorted((rel.source_word, rel.target_word)))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)
            candidates.append({
                "left": rel.source_word,
                "right": rel.target_word,
                "left_role": source_node.role,
                "right_role": target_node.role,
                "relation_id": rel.relation_id,
            })
            if len(candidates) >= max(1, int(limit or 1)):
                break
        return candidates

    # ================================================================
    # RELATION MANAGEMENT
    # ================================================================

    def add_relation(self, source: str, target: str,
                     relation_type: RelationType,
                     strength: float = 0.5,
                     confidence: float = 0.5,
                     knowledge_source: str = "inferred",
                     selection_signature: str = "") -> Optional[SemanticRelation]:
        """
        Create a typed connection between two concepts.
        If both nodes exist, the relation is created and indexed.

        selection_signature (FIX-A013): optional role-pair signature that
        chose relation_type, if it came through _select_relation_type().
        Stored so a later reconciliation can attribute a failure back to
        the selection pattern, not just this one relation. Empty for
        relations created any other way (seed data, apply_correction,
        etc.) -- those simply aren't eligible for pattern-level feedback,
        by design, not by omission.
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
            # Perf (2026-08-20): capture depth_contribution() before/after
            # this in-place mutation so both endpoint nodes' cached
            # _rel_contribution_sum stays correct without a full rescan --
            # see SemanticNode.adjust_relation_contribution().
            _old_contribution = rel.depth_contribution()
            rel.strength = _clamp(rel.strength + strength * 0.2)
            rel.confidence = _clamp(max(rel.confidence, confidence))
            self._note_trial_reinforcement(rel)
            _delta = rel.depth_contribution() - _old_contribution
            if source in self.nodes:
                self.nodes[source].adjust_relation_contribution(_delta)
            if target in self.nodes:
                self.nodes[target].adjust_relation_contribution(_delta)
            # N2.1 (decision memo, 2026-07-16): this branch used to touch
            # only strength/confidence, silently no-opping knowledge_source
            # forever -- the exact bug N2's mini-acceptance found live
            # (apply_correction() returned True but zero web relations ever
            # carried source_of_knowledge=="correction"). A correction is a
            # deliberate, higher-authority signal than whatever produced the
            # relation before (inference, co-occurrence, adjacency, etc.) --
            # promote it. Never demotes: correcting an already-correction-
            # sourced relation stays "correction", it doesn't revert.
            if knowledge_source == "correction":
                rel.source_of_knowledge = "correction"
            if selection_signature and not rel.selection_signature:
                rel.selection_signature = selection_signature
            # Directive NC2, ratified 2026-08-03 (Sunni & Cael): a
            # strengthen-only pass must still cascade through both
            # endpoints' depth/priority recalculation, or
            # research_priority's study_decay never applies and an
            # already-well-studied word can never fall out of rotation.
            # Do NOT re-append the relation to node.relations here (it's
            # already there) -- call the recalculation directly.
            self.nodes[source]._recalculate_depth()
            self.nodes[target]._recalculate_depth()
            return rel

        rel_id = _generate_id("rel")
        relation = SemanticRelation(
            relation_id=rel_id,
            source_word=source,
            target_word=target,
            relation_type=relation_type,
            strength=strength,
            confidence=confidence,
            source_of_knowledge=knowledge_source,
            selection_signature=selection_signature,
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
            self._word_to_category.setdefault(word, category)

    def get_categories_for(self, word: str) -> Set[str]:
        """Get all categories a word belongs to."""
        primary = self._word_to_category.get(word)
        if primary:
            return {primary}
        # Fallback: scan (for words added before index existed)
        cats = set()
        for cat, words in self._semantic_categories.items():
            if word in words:
                cats.add(cat)
                self._word_to_category[word] = cat  # backfill
                break
        return cats

    # ================================================================
    # INFERENCE ENGINE — Detect implicit relations
    # ================================================================

    def _select_relation_type(
        self, r1: str, r2: str, *, source: str,
        outcomes: Optional[Dict[str, Dict[str, Dict[str, int]]]] = None,
        commit: bool = True,
    ) -> Tuple[RelationType, str]:
        """FIX-A011/FIX-A013 (Sunni & Cael): nearest-fit selection over
        RELATION_TYPE_AXIS_PROFILES, now discounted by accumulated
        real-world failure for this exact (role-pair signature, type)
        combination -- see register_selection_failure(). A type that keeps
        getting contradicted for a given structural signature, across
        however many different entity pairs that signature has ever shown
        up on, becomes progressively less likely to be picked again for
        that signature. This is aggregated evidence changing future
        selection, not a hand-picked replacement rule: nothing here decides
        what SHOULD be picked instead, only that this pairing has stopped
        earning trust. Returns (chosen_type, signature) -- callers pass the
        signature to add_relation() so a future failure can be attributed
        back to this exact selection pattern.

        AURORA DIRECTIVE (Phase 2) causal-generation fix: `outcomes` and
        `commit` let a batch caller (infer_relations_from_context(), which
        scores many word-pairs from the SAME occurrence) score every pair
        against one frozen `outcomes` snapshot and defer the real
        self._selection_outcomes "uses" mutation to a second pass, once per
        pending selection, after the whole batch has been scored. Without
        this, an earlier pair's synchronous "uses" bump (the previous
        single-pass behavior, still exactly what happens for a true
        single-item caller with commit=True/outcomes=None) shifts the
        failure-rate discount for a LATER pair in the same batch that
        happens to share its role-pair signature -- so which relation type
        got chosen depended on arrival order within one occurrence.
        """
        signature = "+".join(sorted((r1, r2)))
        if self._relation_type_checker is None:
            from aurora_warp_protocol import AxisCoverageChecker
            self._relation_type_checker = AxisCoverageChecker({
                f"RELTYPE:{rtype.value}": dict(profile)
                for rtype, profile in RELATION_TYPE_AXIS_PROFILES.items()
                if rtype is not RelationType.RELATED_TO
            })
        checker = self._relation_type_checker
        # Perf (2026-08-20): raw_scores depends only on (r1, r2) -- via the
        # pure, order-independent _role_pair_axis_signal() -- and the fixed
        # checker built above, never on self._selection_outcomes (that
        # discount is applied below, fresh every call, since it's the one
        # genuinely dynamic part). role values are drawn from a small
        # closed vocabulary (noun/verb/adjective/adverb/...), so the
        # number of distinct signatures is tiny -- confirmed via cProfile
        # as the single largest remaining hotspot after the
        # _rel_contribution_sum fix (1M+ cosine() calls for a 12-message
        # corpus run). Cache by the same `signature` already computed
        # above for outcome tracking.
        # signal is computed unconditionally (not only on a cache miss, as
        # before) -- it used to be scoped inside the `if raw_scores is
        # None:` cache-miss branch while also being read, unconditionally,
        # by the check_and_extend() call below, raising NameError on any
        # cache-hit call that fell through to the RELATED_TO fallback.
        # Found incidentally while restructuring this method for the fix
        # above; _role_pair_axis_signal() is cheap and pure, so computing
        # it unconditionally costs nothing on the cache-hit path.
        signal = _role_pair_axis_signal(r1, r2)
        raw_scores = self._raw_score_cache.get(signature)
        if raw_scores is None:
            d15 = checker._ensure_full_dims(signal)
            raw_scores = {cid: checker.cosine(profile, d15) for cid, profile in checker._components.items()}
            self._raw_score_cache[signature] = raw_scores

        source_outcomes = self._selection_outcomes if outcomes is None else outcomes
        stats_for_sig = source_outcomes.get(signature, {})
        adjusted_scores: Dict[str, float] = {}
        for cid, score in raw_scores.items():
            type_value = cid.split("RELTYPE:", 1)[-1]
            stats = stats_for_sig.get(type_value, {})
            uses = int(stats.get("uses", 0) or 0)
            failures = int(stats.get("failures", 0) or 0)
            if uses >= _SELECTION_FAILURE_MIN_USES:
                failure_rate = failures / max(1, uses)
                score = score * max(0.15, 1.0 - failure_rate)
            adjusted_scores[cid] = score

        best_id = max(adjusted_scores, key=lambda k: adjusted_scores[k]) if adjusted_scores else ""
        best_score = adjusted_scores.get(best_id, 0.0)

        if best_score >= _RELATION_SELECTION_THRESHOLD:
            picked_value = best_id.split("RELTYPE:", 1)[-1]
            for rtype in RelationType:
                if rtype.value == picked_value:
                    if commit:
                        bucket = self._selection_outcomes.setdefault(signature, {}).setdefault(
                            rtype.value, {"uses": 0, "failures": 0}
                        )
                        bucket["uses"] = int(bucket.get("uses", 0) or 0) + 1
                    return rtype, signature
            # A promoted discovered kind can win selection too: the seed enum is not a ceiling.
            promoted = self._warp_promoted.get(picked_value)
            if promoted is not None:
                kind = self._open_kinds.setdefault(
                    picked_value, DiscoveredRelationKind(picked_value, getattr(promoted, "axis_profile", {}))
                )
                self.record_relation_trial_use(picked_value)
                if commit:
                    bucket = self._selection_outcomes.setdefault(signature, {}).setdefault(
                        kind.value, {"uses": 0, "failures": 0}
                    )
                    bucket["uses"] = int(bucket.get("uses", 0) or 0) + 1
                return kind, signature

        # A trial kind is USED where the closed vocabulary had no answer (it would have been
        # RELATED_TO), which is how a trial earns the use and consequence it needs to be scored.
        try:
            d15 = checker._ensure_full_dims(signal)
            best_id_t, best_score_t = "", 0.0
            for trial_id, comp in self._warp_trials.items():
                if getattr(comp, "dissolved", False):
                    continue
                score_t = checker.cosine(dict(comp.axis_profile), d15)
                if score_t > best_score_t:
                    best_id_t, best_score_t = trial_id, score_t
            if best_id_t and best_score_t >= _RELATION_SELECTION_THRESHOLD:
                kind = self._open_kinds.setdefault(
                    best_id_t, DiscoveredRelationKind(best_id_t, self._warp_trials[best_id_t].axis_profile))
                self.record_relation_trial_use(best_id_t)
                if commit:
                    bucket = self._selection_outcomes.setdefault(signature, {}).setdefault(
                        kind.value, {"uses": 0, "failures": 0})
                    bucket["uses"] = int(bucket.get("uses", 0) or 0) + 1
                return kind, signature
        except Exception:
            pass
        try:
            self.check_and_extend(signal, source=source, tick=self.total_relations_created)
        except Exception:
            pass
        return RelationType.RELATED_TO, signature

    def commit_relation_type_usage(self, rtype: RelationType, signature: str) -> None:
        """AURORA DIRECTIVE (Phase 2): the deferred half of a commit=False
        _select_relation_type() call -- bumps self._selection_outcomes'
        real "uses" counter for (signature, rtype.value). Call once per
        pending selection, after a whole batch has been scored against a
        frozen snapshot (see infer_relations_from_context())."""
        bucket = self._selection_outcomes.setdefault(signature, {}).setdefault(
            rtype.value, {"uses": 0, "failures": 0}
        )
        bucket["uses"] = int(bucket.get("uses", 0) or 0) + 1

    def _note_trial_reinforcement(self, relation: Any) -> None:
        """A typed relation was independently observed again: its kind held up (consequence)."""
        value = str(getattr(getattr(relation, "relation_type", None), "value", "") or "")
        if value in self._relation_trial_usage:
            self.record_relation_trial_outcome(value, True)

    def register_selection_failure(self, relation: "SemanticRelation") -> None:
        try:
            _value = str(getattr(getattr(relation, "relation_type", None), "value", "") or "")
            if _value in self._relation_trial_usage:
                self.record_relation_trial_outcome(_value, False)      # contradicted: a use without success
        except Exception:
            pass
        """FIX-A013: called when a reconciliation (FIX-A012) contradicts a
        relation. Attributes the failure back to whatever (signature, type)
        pattern selected it -- not to the specific entities involved -- so
        the same underlying gap shows up as a pattern the moment it recurs
        on a DIFFERENT entity pair, not just this one. When a pattern's
        aggregated failure rate crosses the bar (and it has been tried
        enough times to mean something), registers real WARP pressure on
        that signature's own axis signal -- the same mechanism FIX-A010
        already wired, just fed by lived outcome instead of a static
        one-shot coverage check.
        """
        signature = str(getattr(relation, "selection_signature", "") or "")
        type_value = str(getattr(relation.relation_type, "value", "") or "")
        if not signature or not type_value:
            return
        bucket = self._selection_outcomes.setdefault(signature, {}).setdefault(
            type_value, {"uses": 0, "failures": 0}
        )
        bucket["failures"] = int(bucket.get("failures", 0) or 0) + 1
        uses = int(bucket.get("uses", 0) or 0)
        failures = int(bucket.get("failures", 0) or 0)
        if uses < _SELECTION_FAILURE_MIN_USES:
            return
        if (failures / max(1, uses)) < _SELECTION_FAILURE_RATE_THRESHOLD:
            return
        try:
            r1, r2 = (signature.split("+", 1) + [""])[:2]
            self.check_and_extend(
                _role_pair_axis_signal(r1, r2),
                source=f"register_selection_failure:{signature}:{type_value}",
                tick=self.total_relations_created,
            )
        except Exception:
            pass

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

        # AURORA DIRECTIVE (Phase 2) causal-generation fix: every pair below
        # is an independent reaction to this SAME occurrence (one
        # co-occurring word list) -- _select_relation_type()'s failure-rate
        # discount used to be committed synchronously per pair, so a later
        # pair sharing an earlier pair's role-pair signature, within this
        # SAME batch, saw a discount already shifted by that earlier pair's
        # own commit. Pass 1 scores every pair (both loops below) against
        # one outcomes snapshot frozen before this batch starts. Pass 2
        # commits each pending selection's "uses" usage exactly once,
        # after the whole batch is scored, then creates/strengthens every
        # relation -- so the committed relation types can no longer depend
        # on which pair happened to be scored first.
        outcomes_snapshot = {
            sig: {t: dict(v) for t, v in types.items()}
            for sig, types in self._selection_outcomes.items()
        }
        pending: List[Tuple[str, str, RelationType, str, float, float, str]] = []

        # Directive NC1, ratified 2026-08-03 (Sunni & Cael): this exhaustive
        # pairwise loop used to hardcode RELATED_TO for every pair -- the
        # role-pair heuristics below (verb+noun -> ENABLES, adjective+noun
        # -> CONTEXT_OF) already existed but were only ever applied to
        # adjacent-word pairs, leaving 99% of live relations generic.
        # Reuses those same two proven patterns here, order-independent
        # (this loop's pairs are unordered, unlike the adjacency loop
        # below) -- no new relation types invented.
        # FIX-A011 (Sunni & Cael): the hand-authored role-pair rule table
        # that lived here (verb+noun -> ENABLES, adjective+noun -> CONTEXT_OF,
        # everything else -> RELATED_TO, unconditionally) is replaced by
        # _select_relation_type()'s nearest-fit selection over the same
        # already-declared axis-profile table -- see that method's
        # docstring. No pair-specific case is decided in this loop anymore.
        for i, w1 in enumerate(known):
            for w2 in known[i+1:]:
                r1, r2 = self.nodes[w1].role, self.nodes[w2].role
                rtype, _rtype_sig = self._select_relation_type(
                    r1, r2, source=f"infer_relations_from_context:{r1}+{r2}",
                    outcomes=outcomes_snapshot, commit=False,
                )
                pending.append((w1, w2, rtype, _rtype_sig, 0.2, 0.3, "co-occurrence"))

        # Adjacent words in known list get stronger connections
        for i in range(len(known) - 1):
            w1, w2 = known[i], known[i+1]
            node1 = self.nodes[w1]
            node2 = self.nodes[w2]

            # FIX-A011: adjacency also routes through the same selector now
            # rather than only recognizing verb->noun / adjective->noun.
            if node1.role in ("verb", "adjective") or node2.role in ("verb", "adjective") or node1.role != node2.role:
                _adj_rtype, _adj_sig = self._select_relation_type(
                    node1.role, node2.role,
                    source=f"infer_relations_from_context:adjacency:{node1.role}+{node2.role}",
                    outcomes=outcomes_snapshot, commit=False,
                )
                pending.append((w1, w2, _adj_rtype, _adj_sig, 0.3, 0.25, "adjacency"))

        # Pass 2 -- commit usage once per pending selection, then create the
        # relations, now that every pair in this occurrence has been scored.
        for _, _, rtype, rtype_sig, _, _, _ in pending:
            self.commit_relation_type_usage(rtype, rtype_sig)
        for w1, w2, rtype, rtype_sig, strength, confidence, ksrc in pending:
            self.add_relation(
                w1, w2, rtype,
                strength=strength, confidence=confidence,
                knowledge_source=ksrc,
                selection_signature=rtype_sig,
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
        has_marker = bool(def_words & taxonomy_markers)

        # Perf (2026-08-20): was `for other_word, other_node in
        # self.nodes.items()` -- a full scan of every node in the web
        # (thousands) for every word this runs on, checking membership in
        # def_words (a handful of words from one definition). Confirmed
        # via cProfile as the top remaining hotspot after the relation-depth
        # and relation-type-selection fixes (10.1s of a 30.9s profiled run
        # over just 12 messages). Inverted to walk the small side and do
        # an O(1) dict lookup on the large side instead -- correct as long
        # as node keys are lowercase-normalized, which every node-creation
        # path in this codebase already guarantees (add_node() is only
        # ever called with words from re.findall(r'\b[a-z]+\b', text.lower())
        # -- GeometryExtractor.extract(), infer_relations_from_context(),
        # etc. -- never a raw/mixed-case token).
        for w in def_words:
            if w == word:
                continue
            other_node = self.nodes.get(w)
            if other_node is None:
                continue
            if has_marker:
                # Taxonomy marker present → IS_A
                self.add_relation(
                    word, w, RelationType.IS_A,
                    strength=0.5, confidence=0.4,
                    knowledge_source="definition_analysis"
                )
            else:
                # General mention → RELATED_TO
                self.add_relation(
                    word, w, RelationType.RELATED_TO,
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
        self._word_to_category.pop(word, None)
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
            # Remove from nodes -- remove_relation() also corrects the
            # node's cached _rel_contribution_sum (2026-08-20 perf fix);
            # a bare .relations.pop() here would silently leave it
            # over-counting this relation forever.
            if rel.source_word in self.nodes:
                self.nodes[rel.source_word].remove_relation(rel.relation_id)
            if rel.target_word in self.nodes:
                self.nodes[rel.target_word].remove_relation(rel.relation_id)
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

        Performance note (2026-08-20): this used to re-scan w1's entire
        relations dict for every single w2 in the cluster -- O(cluster_size^2
        * relations_per_node). Confirmed live via cProfile: on a real OETS
        (~2500 nodes / ~18000 relations from baseline seeding), this one
        function accounted for 72.6s of a 191s corpus-ingestion run over
        just 12 messages, and it fires on ordinary conversation turns too
        (called from consolidate() via the normal gateway.receive() path,
        not just corpus runs). get_connected_words() already builds a
        node's full connected-word set in one pass; computing it once per
        w1 and doing O(1) set-membership checks against it for every w2
        turns the relations-scan factor from "repeated n times" into
        "once" -- O(cluster_size * relations_per_node + cluster_size^2).
        """
        n = len(members)
        if n < 2:
            return 0.0
        max_possible = n * (n - 1) / 2
        actual = 0
        member_list = list(members)
        for i, w1 in enumerate(member_list):
            node = self.web.nodes.get(w1)
            if not node:
                continue
            connected = node.get_connected_words()
            for w2 in member_list[i+1:]:
                if w2 in connected:
                    actual += 1
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

    def teach_concept(self, word: str, definition: str,
                      synonyms: List[str] = None,
                      related: List[str] = None) -> bool:
        """Manually teach Aurora a concept (intentional learning)."""
        res = ResearchResult(
            word=word,
            definitions_found=[{"text": definition, "source": "user_teaching"}],
            synonyms=synonyms or [],
            related_words=[{"word": r, "relation": "user_taught", "confidence": 0.8} for r in (related or [])],
            success=True,
            source="user_teaching"
        )
        # Ensure node exists
        if not self.web.has_node(word):
            from aurora_expression_perception import infer_word_role
            try:
                role = infer_word_role(word)
            except Exception as _aurora_boundary_exc:
                _aurora_record_exception_from_locals(
                    locals(),
                    module=__name__,
                    operation="exception_handler:aurora_internal/aurora_ontological_scaffolding.py:1342",
                    exc=_aurora_boundary_exc,
                    context={"function": "teach_concept", "handler_line": 1342, "source_file": "aurora_internal/aurora_ontological_scaffolding.py"},
                )
                role = "noun"
            self.web.add_node(word, role, 0.0, meaning="waiting_for_teaching")

        self._integrate_result(word, res)
        self.cluster_engine.discover_clusters() # Re-cluster
        return True

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
            except Exception as _aurora_boundary_exc:
                _aurora_record_exception_from_locals(
                    locals(),
                    module=__name__,
                    operation="exception_handler:aurora_internal/aurora_ontological_scaffolding.py:1495",
                    exc=_aurora_boundary_exc,
                    context={"function": "_research_word", "handler_line": 1495, "source_file": "aurora_internal/aurora_ontological_scaffolding.py"},
                )
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
                    except Exception as _aurora_boundary_exc:
                        _aurora_record_exception_from_locals(
                            locals(),
                            module=__name__,
                            operation="exception_handler:aurora_internal/aurora_ontological_scaffolding.py:1585",
                            exc=_aurora_boundary_exc,
                            context={"function": "_integrate_result", "handler_line": 1585, "source_file": "aurora_internal/aurora_ontological_scaffolding.py"},
                        )
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
            "avg_relation_density": self._average_relation_density(),
            "avg_cluster_depth": self._average_cluster_depth(),
            "coherence_index": self._coherence_index(),
            "contradiction_rate": self._contradiction_rate(),
            "grounding_index": self._grounding_index(),
            "scaffolding_progress": self._scaffolding_progress(),
            "relational_richness": self._relational_richness(),
            "cluster_maturity": self._cluster_maturity(),
            "understanding_index": 0.0,  # Computed below
        }

        # Composite understanding index
        metrics["understanding_index"] = (
            metrics["ontological_depth"] * 0.22 +
            metrics["semantic_coherence"] * 0.16 +
            metrics["conceptual_density"] * 0.12 +
            metrics["grounding_index"] * 0.18 +
            metrics["scaffolding_progress"] * 0.12 +
            metrics["relational_richness"] * 0.10 +
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

    def _average_relation_density(self) -> float:
        """Raw relations-per-node density, used by language-state gates."""
        if not self.web.nodes:
            return 0.0
        return len(self.web.relations) / len(self.web.nodes)

    def _average_cluster_depth(self) -> float:
        """Average ontological depth of discovered clusters."""
        if not self.cluster_engine.clusters:
            return 0.0
        clusters = self.cluster_engine.clusters.values()
        return sum(c.depth for c in clusters) / len(self.cluster_engine.clusters)

    def _coherence_index(self) -> float:
        """
        A practical coherence proxy for downstream language evolution.
        Blends category organization, cluster tightness, and relation density.
        """
        semantic = self._semantic_coherence()
        cluster_coherence = semantic
        if self.cluster_engine.clusters:
            clusters = self.cluster_engine.clusters.values()
            cluster_coherence = sum(c.coherence for c in clusters) / len(self.cluster_engine.clusters)
        density_norm = _clamp(self._average_relation_density() / 4.0)
        return _clamp(0.55 * semantic + 0.30 * cluster_coherence + 0.15 * density_norm)

    def _contradiction_rate(self) -> float:
        """
        Proxy for unresolved semantic conflict.
        Ambiguous tokens matter most; explicit contrast relations contribute lightly.
        """
        if not self.web.nodes:
            return 0.0
        uncertain_ratio = (
            sum(1 for n in self.web.nodes.values() if n.uncertain_token)
            / len(self.web.nodes)
        )
        total_relations = len(self.web.relations)
        contrast_ratio = 0.0
        if total_relations > 0:
            contrast_count = (
                len(self.web._relations_by_type.get(RelationType.OPPOSITE_OF, set())) +
                len(self.web._relations_by_type.get(RelationType.CONTRASTS, set()))
            )
            contrast_ratio = contrast_count / total_relations
        return _clamp(0.75 * uncertain_ratio + 0.25 * contrast_ratio)

    def _grounding_index(self) -> float:
        """
        How much meaning is actually anchored rather than merely observed.
        """
        nodes = list(self.web.nodes.values())
        if not nodes:
            return 0.0

        definition_cov = sum(1 for n in nodes if n.definitions) / len(nodes)
        example_cov = sum(1 for n in nodes if n.usage_examples) / len(nodes)
        relation_cov = sum(1 for n in nodes if n.relations) / len(nodes)
        cluster_cov = sum(1 for n in nodes if n.cluster_ids) / len(nodes)

        sense_nodes = [n for n in nodes if n.senses]
        if sense_nodes:
            sense_resolved = sum(1 for n in sense_nodes if not n.uncertain_token) / len(sense_nodes)
        else:
            sense_resolved = definition_cov

        return _clamp(
            0.25 * definition_cov +
            0.20 * example_cov +
            0.20 * relation_cov +
            0.15 * cluster_cov +
            0.20 * sense_resolved
        )

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

        # Scaffolded template management
        self.scaffolded_templates: Dict[str, ScaffoldedTemplate] = {}

        # Announce thresholds for study cycle speak-up
        self._announce_threshold_connections: int = 3
        self._announce_threshold_confidence: float = 0.65

        # Bridge state
        self._initialized = False
        self._recent_interaction_contexts = deque(maxlen=24)

    def teach(self, word: str, definition: str,
              synonyms: List[str] = None,
              related: List[str] = None) -> bool:
        """Manually teach a concept (intentional learning)."""
        return self.research.teach_concept(word, definition, synonyms, related)

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
        if content_words:
            context_window = list(dict.fromkeys(content_words[:12]))
            self._recent_interaction_contexts.append(set(context_window))
            for word in context_window:
                node = self.web.nodes.get(word)
                if node is None:
                    continue
                other_context = [tok for tok in context_window if tok != word]
                if other_context:
                    node.disambiguate_sense(other_context)
        if len(content_words) >= 2:
            self.web.infer_relations_from_context(content_words, tone)

    def _topic_tracking_score(self) -> float:
        """
        Multi-turn topical continuity based on adjacent content-word overlap.
        """
        contexts = [ctx for ctx in self._recent_interaction_contexts if ctx]
        if len(contexts) < 2:
            return 0.0

        overlaps: List[float] = []
        for prev, curr in zip(contexts, contexts[1:]):
            union = prev | curr
            if not union:
                continue
            overlaps.append(len(prev & curr) / len(union))

        if not overlaps:
            return 0.0

        weighted_total = 0.0
        weight_sum = 0.0
        count = len(overlaps)
        for idx, overlap in enumerate(overlaps, start=1):
            weight = 0.5 + (0.5 * idx / count)
            weighted_total += overlap * weight
            weight_sum += weight
        return _clamp(weighted_total / max(weight_sum, 1e-9))

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
            import os
            # `os` was never imported in this module, so this raised NameError on
            # every call and study events were silently never logged. The path was
            # also cwd-relative, ignoring the boot's real state directory.
            try:
                from aurora_internal.aurora_state_context import get_active_state_dir
                _study_dir = get_active_state_dir() or "aurora_state"
            except Exception:
                _study_dir = "aurora_state"
            log_path = os.path.join(str(_study_dir), "study_log.jsonl")
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, 'a') as f:
                f.write(_j.dumps(event.to_dict()) + "\n")
        except Exception as _aurora_boundary_exc:
            _aurora_record_exception_from_locals(
                locals(),
                module=__name__,
                operation="exception_handler:aurora_internal/aurora_ontological_scaffolding.py:2165",
                exc=_aurora_boundary_exc,
                context={"function": "log_study_event", "handler_line": 2165, "source_file": "aurora_internal/aurora_ontological_scaffolding.py"},
            )
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
                        # Perf (2026-08-20): same cache-correction pattern
                        # as the strengthen-existing branch in
                        # OntologicalWeb.add_relation() -- this loop
                        # doesn't call _recalculate_depth() immediately
                        # (the unconditional full-node pass earlier in
                        # consolidate() already covers this cycle; the
                        # next cycle picks up this strengthening), but the
                        # cache must still track it now or it silently
                        # under-counts these boosts forever.
                        _old_contribution = rel.depth_contribution()
                        rel.strength = _clamp(rel.strength + 0.05)
                        rel.confidence = _clamp(rel.confidence + 0.02)
                        _delta = rel.depth_contribution() - _old_contribution
                        source_node.adjust_relation_contribution(_delta)
                        target_node.adjust_relation_contribution(_delta)

        self.web.total_consolidations += 1

    # ================================================================
    # FULL STATUS
    # ================================================================

    def get_stats(self) -> Dict[str, Any]:
        understanding = self.metrics.compute()
        understanding["topic_tracking"] = self._topic_tracking_score()
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

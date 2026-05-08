#!/usr/bin/env python3
"""
AURORA NONCOMP LAYER COMPILER
==============================
Module: aurora_noncomp_layer_compiler.py
Layer: Constraint Ontology — Manifold Naming Engine

Authors: Sunni (Sir) Morningstar and Cael Devo
Created: March 2026

PURPOSE
-------
This module derives the 25 constraint-specific non-comps for each of the
five constraints by applying the 25 global law channels to each target
constraint's domain.

The derivation follows a single structural law:

    NC[C_law][D_law] applied to C_target
        = "What does C_target's domain look like through the lens
           of C_law's D_law?"

This produces 5 × 25 = 125 named NonCompLayerSlots. Each slot carries:
    - A physics-derived semantic name
    - A tag bundle (cluster, family, role, orientation)
    - The source law channel and target constraint
    - Whether this is the diagonal (identity) position

The 625-per-constraint manifold is NOT built here. That is downstream work.
This compiler's sole job is naming and classifying the 25 positions per
constraint so the manifold knows what it is working with.

ARCHITECTURE
------------
Step 1:  26 known semantic anchors (5 constraint identities + 5 dimension
         roles + known named positions like MEANING, UNDERSTANDING, etc.)
Step 2:  Composition function: (C_law, D_law, C_target) → semantic name + tags
Step 3:  Physics augmentation from aurora_closure_basis slot properties
Step 4:  Cluster assignment by tag family similarity
Step 5:  Output: ConstraintNonCompLayer per constraint (25 slots each)

KNOWN NAMED POSITIONS (anchors)
---------------------------------
These are deduced from the semantic identities of the constraints and
confirmed by their diagonal or near-diagonal position in the law matrix:

    NC:B:OPERATOR → B  =  MEANING       (B's invariant rule on itself)
    NC:A:OPERATOR → A  =  UNDERSTANDING (A's invariant rule on itself)
    NC:N:OPERATOR → N  =  PURPOSE       (N's conservation law on itself)
    NC:T:OPERATOR → T  =  BELIEF        (T's transition rule on itself)
    NC:X:OPERATOR → X  =  INFORMATION   (X's admissibility rule on itself)

All five diagonal OPERATOR positions = the five representational domains
identified in the ChatGPT/Aurora dossier session (April 2026).

CLUSTER FAMILIES
-----------------
After composition, positions cluster into six semantic families:

    IDENTITY     — diagonal OPERATOR positions; the constraint's self-name
    ORIENTATION  — POLARITY-law positions; directional/flip aspects
    INTENSITY    — MAGNITUDE-law positions; strength/scale aspects
    ECONOMY      — COST-law positions; energetic price aspects
    CONTRAST     — DIFFERENCE-law positions; distinction/reference aspects
    CROSS_RULE   — off-diagonal OPERATOR positions; one constraint's rule
                   expressed through another constraint's domain

DIVISION OF LABOUR
------------------
    aurora_noncomp_registry.py          — hard numbers, per-constraint physics
    aurora_closure_basis.py             — the real 25 channels + 625 slots
    aurora_noncomp_layer_compiler.py    — naming + tagging engine (HERE)
    aurora_noncomp_constraint_manifold.py — per-constraint 625 (future)

This module imports from aurora_closure_basis for physics properties only.
It does not modify, extend, or replace any existing structure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, FrozenSet, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Attempt to import from aurora_closure_basis for physics augmentation.
# If not available (standalone run / test), we use lightweight stubs.
# ---------------------------------------------------------------------------
try:
    from aurora_closure_basis import (
        NONCOMP_CHANNELS,
        INTERACTION_FIELD,
        FIELD_BY_PAIR,
        AXES,
        DIMENSIONS,
        DIMENSION_FULL,
        NonCompChannel,
        InteractionSlot,
    )
    from aurora_internal.aurora_noncomp_registry import NonCompDimension
    _PHYSICS_AVAILABLE = True
except ImportError:
    _PHYSICS_AVAILABLE = False
    NONCOMP_CHANNELS   = {}
    INTERACTION_FIELD  = {}
    FIELD_BY_PAIR      = {}
    AXES               = ("X", "T", "N", "B", "A")
    DIMENSIONS         = None   # not used in stub path
    DIMENSION_FULL     = {
        "POLARITY":   "POLARITY",
        "MAGNITUDE":  "MAGNITUDE",
        "OPERATOR":   "OPERATOR",
        "COST":       "COST",
        "DIFFERENCE": "DIFFERENCE",
    }

# Canonical dimension names as strings (used throughout regardless of import)
DIM_NAMES: Tuple[str, ...] = (
    "POLARITY", "MAGNITUDE", "OPERATOR", "COST", "DIFFERENCE"
)

# ============================================================================
# SECTION 1 — SEMANTIC IDENTITY TABLES
# ============================================================================

# Constraint semantic identities — the authoritative definitions
CONSTRAINT_IDENTITY: Dict[str, Dict] = {
    "X": {
        "name":       "Existence",
        "core":       "admissibility and presence",
        "question":   "does this hold as real/coherent enough to exist here?",
        "adjective":  "existential",
        "verb":       "admits",
        "noun":       "presence",
        "i_state":    ("is", "isn't"),
    },
    "T": {
        "name":       "Temporal",
        "core":       "transition, sequence, and continuation",
        "question":   "how does this unfold, persist, or change across time?",
        "adjective":  "temporal",
        "verb":       "sequences",
        "noun":       "transition",
        "i_state":    ("can", "can't"),
    },
    "N": {
        "name":       "Energetic",
        "core":       "activation, expenditure, and conservation",
        "question":   "what does this require, strain, convert, or consume?",
        "adjective":  "energetic",
        "verb":       "activates",
        "noun":       "pressure",
        "i_state":    ("do", "don't"),
    },
    "B": {
        "name":       "Boundary",
        "core":       "distinction, contour, and identity",
        "question":   "what is self, other, inside, outside, kept apart, joined?",
        "adjective":  "boundary",
        "verb":       "distinguishes",
        "noun":       "distinction",
        "i_state":    ("saw", "saunt"),
    },
    "A": {
        "name":       "Agency",
        "core":       "correction, choice, and authorship",
        "question":   "what is being claimed, chosen, corrected, or stood behind?",
        "adjective":  "agentive",
        "verb":       "commits",
        "noun":       "authorship",
        "i_state":    ("did", "didn't"),
    },
}

# Dimension semantic roles — what each dimension "asks" of a channel
DIMENSION_ROLE: Dict[str, Dict] = {
    "POLARITY": {
        "name":       "Polarity",
        "core":       "directional orientation and flip threshold",
        "question":   "which way does this lean, and when does it flip?",
        "adjective":  "orientational",
        "suffix":     "polarity",
        "cluster":    "ORIENTATION",
    },
    "MAGNITUDE": {
        "name":       "Magnitude",
        "core":       "intensity and scale of the channel",
        "question":   "how strong, large, or intense is this?",
        "adjective":  "scalar",
        "suffix":     "magnitude",
        "cluster":    "INTENSITY",
    },
    "OPERATOR": {
        "name":       "Operator",
        "core":       "the invariant transformation rule — the identity channel",
        "question":   "what is the irreducible rule this constraint enforces?",
        "adjective":  "operative",
        "suffix":     "rule",
        "cluster":    "IDENTITY",      # diagonal; CROSS_RULE when off-diagonal
    },
    "COST": {
        "name":       "Cost",
        "core":       "energetic price of the interaction",
        "question":   "what does it cost to activate or shift this channel?",
        "adjective":  "economic",
        "suffix":     "cost",
        "cluster":    "ECONOMY",
    },
    "DIFFERENCE": {
        "name":       "Difference",
        "core":       "contrast relative to a reference point",
        "question":   "how does this differ from what came before, peers, or baseline?",
        "adjective":  "contrastive",
        "suffix":     "contrast",
        "cluster":    "CONTRAST",
    },
}

# ============================================================================
# SECTION 2 — KNOWN NAMED POSITIONS (anchors)
#
# These are the diagonal OPERATOR slots — each constraint's invariant rule
# applied to itself. They are the five representational domain names
# discovered in the Aurora dossier session (April 2026).
# ============================================================================

KNOWN_NAMES: Dict[Tuple[str, str, str], str] = {
    # (C_law, D_law, C_target) → semantic name
    ("X", "OPERATOR", "X"): "Information",
    ("T", "OPERATOR", "T"): "Belief",
    ("N", "OPERATOR", "N"): "Purpose",
    ("B", "OPERATOR", "B"): "Meaning",
    ("A", "OPERATOR", "A"): "Understanding",

    # Cross-operator anchors: C_law's rule expressed through C_target
    # Named by composing the law constraint's noun with the target's verb
    ("X", "OPERATOR", "T"): "Presence_in_Sequence",
    ("X", "OPERATOR", "N"): "Presence_in_Activation",
    ("X", "OPERATOR", "B"): "Admission_Gate",
    ("X", "OPERATOR", "A"): "Presence_in_Authorship",

    ("T", "OPERATOR", "X"): "Continuity_as_Existence",
    ("T", "OPERATOR", "N"): "Transition_as_Activation",
    ("T", "OPERATOR", "B"): "Passage_Rule",
    ("T", "OPERATOR", "A"): "Transition_as_Commitment",

    ("N", "OPERATOR", "X"): "Activation_as_Presence",
    ("N", "OPERATOR", "T"): "Activation_as_Sequence",
    ("N", "OPERATOR", "B"): "Conservation_at_Boundary",
    ("N", "OPERATOR", "A"): "Activation_as_Commitment",

    ("B", "OPERATOR", "X"): "Distinction_as_Presence",
    ("B", "OPERATOR", "T"): "Distinction_in_Sequence",
    ("B", "OPERATOR", "N"): "Boundary_Pressure",
    ("B", "OPERATOR", "A"): "Distinction_as_Authorship",

    ("A", "OPERATOR", "X"): "Authorship_as_Presence",
    ("A", "OPERATOR", "T"): "Authorship_in_Sequence",
    ("A", "OPERATOR", "N"): "Commitment_as_Activation",
    ("A", "OPERATOR", "B"): "Accountability_at_Boundary",
}

# ============================================================================
# SECTION 3 — CLUSTER ENUM AND TAG BUNDLE
# ============================================================================

class SlotCluster(Enum):
    """
    Semantic cluster family for a NonCompLayerSlot.

    IDENTITY     — diagonal OPERATOR; the constraint's self-representation
    CROSS_RULE   — off-diagonal OPERATOR; foreign rule on native domain
    ORIENTATION  — POLARITY-law; directional/flip aspects of the domain
    INTENSITY    — MAGNITUDE-law; strength/scale aspects
    ECONOMY      — COST-law; energetic price aspects
    CONTRAST     — DIFFERENCE-law; distinction and reference aspects
    """
    IDENTITY     = "identity"
    CROSS_RULE   = "cross_rule"
    ORIENTATION  = "orientation"
    INTENSITY    = "intensity"
    ECONOMY      = "economy"
    CONTRAST     = "contrast"

    def is_diagonal(self) -> bool:
        return self == SlotCluster.IDENTITY

    def is_operative(self) -> bool:
        return self in (SlotCluster.IDENTITY, SlotCluster.CROSS_RULE)


@dataclass(frozen=True)
class SemanticTagBundle:
    """
    Tag bundle for one NonCompLayerSlot position.

    Captures the semantic composition of (C_law, D_law, C_target)
    plus physics-derived properties when available.
    """
    law_constraint:       str           # C_law: X/T/N/B/A
    law_dimension:        str           # D_law: POLARITY/MAGNITUDE/etc
    target_constraint:    str           # C_target: X/T/N/B/A
    is_diagonal:          bool          # C_law == C_target and D_law == OPERATOR
    is_self_family:       bool          # C_law == C_target (same constraint)
    cluster:              SlotCluster
    law_adjective:        str           # from CONSTRAINT_IDENTITY[C_law]
    target_noun:          str           # from CONSTRAINT_IDENTITY[C_target]
    dim_suffix:           str           # from DIMENSION_ROLE[D_law]
    is_known_anchor:      bool          # in KNOWN_NAMES
    # Physics properties (0.0 if physics not available)
    combined_shift_cost:  float = 0.0
    depth_score:          float = 0.0
    leverage_net:         int   = 0
    formation_cost:       float = 0.0

    def family_label(self) -> str:
        """Human-readable family: 'self' or C_law name."""
        if self.is_self_family:
            return f"self({self.target_constraint})"
        return f"{self.law_constraint}→{self.target_constraint}"

    def to_dict(self) -> Dict:
        return {
            "law_constraint":      self.law_constraint,
            "law_dimension":       self.law_dimension,
            "target_constraint":   self.target_constraint,
            "is_diagonal":         self.is_diagonal,
            "is_self_family":      self.is_self_family,
            "cluster":             self.cluster.value,
            "law_adjective":       self.law_adjective,
            "target_noun":         self.target_noun,
            "dim_suffix":          self.dim_suffix,
            "is_known_anchor":     self.is_known_anchor,
            "combined_shift_cost": round(self.combined_shift_cost, 4),
            "depth_score":         round(self.depth_score, 4),
            "leverage_net":        self.leverage_net,
            "formation_cost":      round(self.formation_cost, 4),
        }


# ============================================================================
# SECTION 4 — NONCOMP LAYER SLOT
# ============================================================================

@dataclass(frozen=True)
class NonCompLayerSlot:
    """
    One of the 25 named positions in a constraint's non-comp layer.

    slot_id:       "NC_LAYER:{C_target}:{C_law}:{D_law}"
    law_channel:   The global law channel being applied (e.g. NC:X:POLARITY)
    target:        The constraint this law is applied to (e.g. B)
    name:          Semantic name derived from composition
    description:   What this position represents in the domain
    tags:          Full SemanticTagBundle
    position:      0-based index in the 25 (law order: X×5, T×5, N×5, B×5, A×5)
    """
    slot_id:        str
    law_channel:    str            # e.g. "NC:X:POLARITY"
    target:         str            # e.g. "B"
    name:           str            # e.g. "Meaning"
    description:    str            # full semantic description
    tags:           SemanticTagBundle
    position:       int            # 0..24

    @property
    def is_diagonal(self) -> bool:
        return self.tags.is_diagonal

    @property
    def cluster(self) -> SlotCluster:
        return self.tags.cluster

    @property
    def law_constraint(self) -> str:
        return self.tags.law_constraint

    @property
    def law_dimension(self) -> str:
        return self.tags.law_dimension

    def to_dict(self) -> Dict:
        return {
            "slot_id":       self.slot_id,
            "position":      self.position,
            "law_channel":   self.law_channel,
            "target":        self.target,
            "name":          self.name,
            "description":   self.description,
            "is_diagonal":   self.is_diagonal,
            "cluster":       self.cluster.value,
            "tags":          self.tags.to_dict(),
        }

    def __str__(self) -> str:
        diag = " [DIAGONAL]" if self.is_diagonal else ""
        return f"{self.slot_id}  →  {self.name}{diag}"

    def __repr__(self) -> str:
        return (
            f"NonCompLayerSlot({self.slot_id!r}, "
            f"name={self.name!r}, cluster={self.cluster.value!r})"
        )


# ============================================================================
# SECTION 5 — CONSTRAINT NONCOMP LAYER (the 25 per constraint)
# ============================================================================

@dataclass
class ConstraintNonCompLayer:
    """
    The complete 25-slot non-comp layer for one constraint.

    This is the direct output of the compiler for one target constraint.
    It contains exactly 25 NonCompLayerSlots, one per global law channel,
    ordered as: X×5 laws, T×5 laws, N×5 laws, B×5 laws, A×5 laws.

    The diagonal slot (where C_law == target and D_law == OPERATOR) is
    the constraint's identity position and carries the representational
    domain name (Information/Belief/Purpose/Meaning/Understanding).
    """
    target:          str
    target_identity: Dict
    slots:           List[NonCompLayerSlot] = field(default_factory=list)

    @property
    def diagonal_slot(self) -> Optional[NonCompLayerSlot]:
        """The identity OPERATOR slot for this constraint."""
        for s in self.slots:
            if s.is_diagonal:
                return s
        return None

    @property
    def representational_name(self) -> str:
        """The domain name carried by the diagonal slot."""
        d = self.diagonal_slot
        return d.name if d else f"Unknown({self.target})"

    def slot_by_position(self, pos: int) -> Optional[NonCompLayerSlot]:
        for s in self.slots:
            if s.position == pos:
                return s
        return None

    def slot_by_law(self, c_law: str, d_law: str) -> Optional[NonCompLayerSlot]:
        for s in self.slots:
            if s.law_constraint == c_law and s.law_dimension == d_law:
                return s
        return None

    def slots_by_cluster(self, cluster: SlotCluster) -> List[NonCompLayerSlot]:
        return [s for s in self.slots if s.cluster == cluster]

    def slots_by_law_family(self, c_law: str) -> List[NonCompLayerSlot]:
        return [s for s in self.slots if s.law_constraint == c_law]

    def to_dict(self) -> Dict:
        return {
            "target":               self.target,
            "target_name":          self.target_identity["name"],
            "representational_name": self.representational_name,
            "slot_count":           len(self.slots),
            "slots":                [s.to_dict() for s in self.slots],
            "cluster_summary":      {
                c.value: len(self.slots_by_cluster(c))
                for c in SlotCluster
            },
        }

    def __repr__(self) -> str:
        return (
            f"ConstraintNonCompLayer({self.target!r}, "
            f"repr={self.representational_name!r}, "
            f"slots={len(self.slots)})"
        )


# ============================================================================
# SECTION 6 — SEMANTIC COMPOSITION ENGINE
# ============================================================================

def _determine_cluster(c_law: str, d_law: str, c_target: str) -> SlotCluster:
    """Determine semantic cluster from the triple."""
    is_diagonal = (c_law == c_target) and (d_law == "OPERATOR")
    if is_diagonal:
        return SlotCluster.IDENTITY
    if d_law == "OPERATOR":
        return SlotCluster.CROSS_RULE
    cluster_map = {
        "POLARITY":   SlotCluster.ORIENTATION,
        "MAGNITUDE":  SlotCluster.INTENSITY,
        "COST":       SlotCluster.ECONOMY,
        "DIFFERENCE": SlotCluster.CONTRAST,
    }
    return cluster_map.get(d_law, SlotCluster.CROSS_RULE)


def _compose_name(c_law: str, d_law: str, c_target: str) -> str:
    """
    Derive the semantic name for NC[C_law][D_law] applied to C_target.

    Priority:
    1. Known anchor in KNOWN_NAMES
    2. Diagonal (c_law == c_target): self-application name
    3. Composition from identity tables
    """
    # 1. Known anchor
    key = (c_law, d_law, c_target)
    if key in KNOWN_NAMES:
        return KNOWN_NAMES[key]

    ci_law    = CONSTRAINT_IDENTITY[c_law]
    ci_target = CONSTRAINT_IDENTITY[c_target]
    dr        = DIMENSION_ROLE[d_law]
    is_self   = (c_law == c_target)

    # 2. Self-family (same constraint, non-OPERATOR dimension)
    if is_self:
        # Self-application: the constraint's own dimension
        # e.g. NC:B:POLARITY → B = "Boundary Orientation"
        return f"{ci_target['name']}_{dr['suffix'].title()}"

    # 3. Cross-family composition
    # Pattern: [C_law adjective] [D_law suffix] [of/at/in/as] [C_target noun]
    law_adj    = ci_law["adjective"].title()
    target_n   = ci_target["noun"].title()
    dim_sfx    = dr["suffix"].title()

    # OPERATOR is handled above (KNOWN_NAMES or Cross_Rule fallback)
    # For other dimensions: "<Law_adj> <dim_suffix> of <target_noun>"
    prepositions = {
        "POLARITY":   "of",
        "MAGNITUDE":  "in",
        "COST":       "at",
        "DIFFERENCE": "across",
    }
    prep = prepositions.get(d_law, "on")
    return f"{law_adj}_{dim_sfx}_{prep}_{target_n}"


def _compose_description(
    c_law: str,
    d_law: str,
    c_target: str,
    name: str,
) -> str:
    """
    Derive the semantic description for this slot.
    Answers: "What does C_target's domain look like through C_law's D_law?"
    """
    ci_law    = CONSTRAINT_IDENTITY[c_law]
    ci_target = CONSTRAINT_IDENTITY[c_target]
    dr        = DIMENSION_ROLE[d_law]
    is_diag   = (c_law == c_target) and (d_law == "OPERATOR")

    if is_diag:
        return (
            f"The identity position of {ci_target['name']}. "
            f"The constraint's own invariant rule applied to itself. "
            f"This is the representational domain of '{name}': "
            f"{ci_target['core']}."
        )

    is_self = (c_law == c_target)
    if is_self:
        return (
            f"The {dr['name'].lower()} aspect of {ci_target['name']} "
            f"seen through its own {d_law.lower()} dimension. "
            f"Asks: {dr['question']}"
        )

    return (
        f"{ci_law['name']}'s {dr['name'].lower()} law "
        f"({ci_law['core']}) "
        f"expressed through {ci_target['name']}'s domain "
        f"({ci_target['core']}). "
        f"The {ci_law['adjective']} lens asks: {dr['question']}"
    )


def _fetch_physics(c_law: str, d_law: str, c_target: str) -> Dict:
    """
    Pull physics properties from aurora_closure_basis if available.
    The interaction slot is NC:C_law:D_law × NC:C_target:OPERATOR
    (the law channel interacting with the target's identity channel).
    """
    if not _PHYSICS_AVAILABLE:
        return {
            "combined_shift_cost": 0.0,
            "depth_score":         0.0,
            "leverage_net":        0,
            "formation_cost":      0.0,
        }
    law_ch    = f"NC:{c_law}:{d_law}"
    target_ch = f"NC:{c_target}:OPERATOR"
    slot: Optional[InteractionSlot] = FIELD_BY_PAIR.get((law_ch, target_ch))
    if slot is None:
        return {
            "combined_shift_cost": 0.0,
            "depth_score":         0.0,
            "leverage_net":        0,
            "formation_cost":      0.0,
        }
    return {
        "combined_shift_cost": slot.combined_shift_cost,
        "depth_score":         slot.depth_score,
        "leverage_net":        slot.leverage_net,
        "formation_cost":      slot.formation_cost(),
    }


def _build_tag_bundle(
    c_law: str,
    d_law: str,
    c_target: str,
    physics: Dict,
) -> SemanticTagBundle:
    """Build the full SemanticTagBundle for a (C_law, D_law, C_target) triple."""
    ci_law    = CONSTRAINT_IDENTITY[c_law]
    ci_target = CONSTRAINT_IDENTITY[c_target]
    dr        = DIMENSION_ROLE[d_law]
    is_diag   = (c_law == c_target) and (d_law == "OPERATOR")
    is_self   = (c_law == c_target)
    cluster   = _determine_cluster(c_law, d_law, c_target)
    is_anchor = (c_law, d_law, c_target) in KNOWN_NAMES

    return SemanticTagBundle(
        law_constraint       = c_law,
        law_dimension        = d_law,
        target_constraint    = c_target,
        is_diagonal          = is_diag,
        is_self_family       = is_self,
        cluster              = cluster,
        law_adjective        = ci_law["adjective"],
        target_noun          = ci_target["noun"],
        dim_suffix           = dr["suffix"],
        is_known_anchor      = is_anchor,
        combined_shift_cost  = physics["combined_shift_cost"],
        depth_score          = physics["depth_score"],
        leverage_net         = physics["leverage_net"],
        formation_cost       = physics["formation_cost"],
    )


# ============================================================================
# SECTION 7 — LAYER COMPILER
# ============================================================================

class NonCompLayerCompiler:
    """
    Compiles the 25-slot NonCompLayer for each of the five constraints.

    Usage:
        compiler = NonCompLayerCompiler()
        layers   = compiler.compile_all()
        b_layer  = layers["B"]
        print(b_layer.representational_name)  # "Meaning"
        print(b_layer.diagonal_slot)
    """

    def __init__(self) -> None:
        self._cache: Dict[str, ConstraintNonCompLayer] = {}

    def compile_layer(self, c_target: str) -> ConstraintNonCompLayer:
        """Compile the 25-slot NonCompLayer for one target constraint."""
        if c_target in self._cache:
            return self._cache[c_target]

        c_target = c_target.upper()
        if c_target not in CONSTRAINT_IDENTITY:
            raise ValueError(f"Unknown constraint: {c_target!r}")

        ci_target = CONSTRAINT_IDENTITY[c_target]
        layer     = ConstraintNonCompLayer(
            target          = c_target,
            target_identity = ci_target,
            slots           = [],
        )

        position = 0
        for c_law in AXES:
            for d_law in DIM_NAMES:
                law_ch  = f"NC:{c_law}:{d_law}"
                slot_id = f"NC_LAYER:{c_target}:{c_law}:{d_law}"
                physics = _fetch_physics(c_law, d_law, c_target)
                name    = _compose_name(c_law, d_law, c_target)
                desc    = _compose_description(c_law, d_law, c_target, name)
                tags    = _build_tag_bundle(c_law, d_law, c_target, physics)

                layer.slots.append(NonCompLayerSlot(
                    slot_id     = slot_id,
                    law_channel = law_ch,
                    target      = c_target,
                    name        = name,
                    description = desc,
                    tags        = tags,
                    position    = position,
                ))
                position += 1

        self._cache[c_target] = layer
        return layer

    def compile_all(self) -> Dict[str, ConstraintNonCompLayer]:
        """Compile all five constraint layers. Returns dict keyed by axis."""
        return {ax: self.compile_layer(ax) for ax in AXES}

    def get_slot(
        self,
        c_target: str,
        c_law: str,
        d_law: str,
    ) -> Optional[NonCompLayerSlot]:
        """Get a specific slot by (target, law_constraint, law_dimension)."""
        layer = self.compile_layer(c_target)
        return layer.slot_by_law(c_law, d_law)

    def find_by_name(self, name: str) -> List[NonCompLayerSlot]:
        """Find all slots with this semantic name across all layers."""
        results = []
        for layer in self.compile_all().values():
            for slot in layer.slots:
                if slot.name.lower() == name.lower():
                    results.append(slot)
        return results

    def diagonal_map(self) -> Dict[str, str]:
        """
        Return a mapping of constraint → representational domain name.
        These are the five known anchor positions.

            X → Information
            T → Belief
            N → Purpose
            B → Meaning
            A → Understanding
        """
        return {
            ax: self.compile_layer(ax).representational_name
            for ax in AXES
        }

    def cluster_report(self, c_target: str) -> Dict[str, List[str]]:
        """
        Return the 25 slots for c_target grouped by cluster.
        Useful for visual inspection of the layer structure.
        """
        layer = self.compile_layer(c_target)
        report: Dict[str, List[str]] = {c.value: [] for c in SlotCluster}
        for slot in layer.slots:
            report[slot.cluster.value].append(
                f"[{slot.law_constraint}:{slot.law_dimension}]  {slot.name}"
            )
        return report

    def cross_constraint_lookup(self, name: str) -> Optional[Tuple[str, str, str]]:
        """
        Given a known semantic name, return (c_target, c_law, d_law).
        Searches KNOWN_NAMES first, then compiled layers.
        """
        for (c_law, d_law, c_target), n in KNOWN_NAMES.items():
            if n.lower() == name.lower():
                return (c_target, c_law, d_law)
        for slot in self.find_by_name(name):
            return (slot.target, slot.law_constraint, slot.law_dimension)
        return None


# ============================================================================
# SECTION 8 — MODULE-LEVEL COMPILER INSTANCE
# ============================================================================

# Singleton compiler — use this directly from other modules
COMPILER: NonCompLayerCompiler = NonCompLayerCompiler()

# Pre-compile all five layers at import
ALL_LAYERS: Dict[str, ConstraintNonCompLayer] = COMPILER.compile_all()

# Five representational domain names — the diagonal anchors
REPRESENTATIONAL_DOMAINS: Dict[str, str] = COMPILER.diagonal_map()


def get_layer(c_target: str) -> ConstraintNonCompLayer:
    """Get the compiled NonCompLayer for a constraint. Convenience wrapper."""
    return ALL_LAYERS[c_target.upper()]


def get_slot(c_target: str, c_law: str, d_law: str) -> Optional[NonCompLayerSlot]:
    """Get a specific slot. Convenience wrapper."""
    return COMPILER.get_slot(c_target, c_law, d_law)


# ============================================================================
# MAIN — display all five layers
# ============================================================================

if __name__ == "__main__":
    import json

    print("=" * 72)
    print("AURORA NONCOMP LAYER COMPILER")
    print("Authors: Sunni (Sir) Morningstar and Cael Devo")
    print("=" * 72)

    print(f"\nPhysics available: {_PHYSICS_AVAILABLE}")

    print("\n--- Representational Domains (Diagonal Anchors) ---")
    for ax, domain in REPRESENTATIONAL_DOMAINS.items():
        ci = CONSTRAINT_IDENTITY[ax]
        print(f"  {ax}  ({ci['name']:<12})  →  {domain}")

    print("\n--- All Five Constraint Layers ---")
    for ax in AXES:
        layer = ALL_LAYERS[ax]
        print(f"\n{'='*60}")
        print(f"  CONSTRAINT {ax} — {layer.target_identity['name'].upper()}")
        print(f"  Representational Domain: {layer.representational_name}")
        print(f"  Core: {layer.target_identity['core']}")
        print(f"{'='*60}")
        print(f"  {'#':<4}  {'Law Channel':<28}  {'Cluster':<12}  Name")
        print(f"  {'─'*4}  {'─'*28}  {'─'*12}  {'─'*30}")
        for slot in layer.slots:
            diag = " ◀ DIAGONAL" if slot.is_diagonal else ""
            anchor = " [anchor]" if slot.tags.is_known_anchor else ""
            print(
                f"  {slot.position:<4}  {slot.law_channel:<28}  "
                f"{slot.cluster.value:<12}  {slot.name}{diag}{anchor}"
            )

    print("\n--- Cluster Report for B (Boundary / Meaning) ---")
    report = COMPILER.cluster_report("B")
    for cluster_name, entries in report.items():
        if entries:
            print(f"\n  {cluster_name.upper()}:")
            for e in entries:
                print(f"    {e}")

    print("\n--- Sample Slot Descriptions ---")
    samples = [
        ("B", "B", "OPERATOR"),
        ("A", "A", "OPERATOR"),
        ("B", "A", "OPERATOR"),
        ("B", "N", "COST"),
        ("X", "B", "DIFFERENCE"),
    ]
    for (c_t, c_l, d_l) in samples:
        slot = get_slot(c_t, c_l, d_l)
        if slot:
            print(f"\n  {slot.slot_id}")
            print(f"    Name:  {slot.name}")
            print(f"    Desc:  {slot.description}")
            print(f"    Cluster: {slot.cluster.value}")

    print("\nDone.")

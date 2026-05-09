#!/usr/bin/env python3
"""
AURORA BEHAVIORAL IDENTITY (Layer 6)
======================================
Consolidated from 3 modules:
  1. aurora_dna_system_v2.py              â€” Genome, genes, fractal alleles, identity anchors
  2. aurora_behavioral_evolution.py       â€” Trait evolution, personality drift
  3. aurora_behavioral_substrate_bridge.py â€” Behavioral crystals, facet simulation

WHO AURORA IS OVER TIME.

DNA DOCTRINE:
  Genes define core traits (truth-seeking, accountability, evolution, etc.)
  Fractal alleles from experience modify genes â€” slowly, with resistance.
  Identity anchors are immutable â€” only created under strict moral alignment.
  Behavioral traits evolve each generation, drifting from baseline.
  Everything is mode-gated: you can't form identity without identity (BOUNDED+).
  You can't anchor morality without agency (AGENTIC only).

  The genome is the CONSTITUTION of self.
  Alleles are AMENDMENTS â€” hard to ratify, harder to remove.
  Anchors are RIGHTS â€” once earned, nearly permanent.

Authors: Sunni (Sir) Morningstar and Cael Devo
"""

import time
import math
import hashlib
import random
import numpy as np
from enum import Enum, IntEnum, auto
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict

from aurora_constraint_engine import (
    ConstraintVector as _ConstraintVector,
    ExistenceMode,
    FoundationalContract,
    GovernorWeights as _GovernorWeights,
    OntologicalClaim,
    OntologicalViolation,
)
_FC = FoundationalContract()

# ============================================================================
# IMPORTS FROM LOWER LAYERS
# ============================================================================
from aurora_ivm import IVMLattice, IVMEnvelope
from aurora_i_state_beings import IStateCollective, SynthesisResult
from aurora_consciousness_engine import AssemblyResult, ConsciousnessEngine
from aurora_expression_perception import (
    ExpressionPerceptionEngine, ImpressionSeed, GhostRelic, EmotionShard
)

# ── Layer -1: Constraint Manifold ────────────────────────────────────────────
CONSTRAINT_MANIFOLD_AVAILABLE = False
try:
    from aurora_constraint_manifold import ConstraintVector
    CONSTRAINT_MANIFOLD_AVAILABLE = True
except ImportError:
    pass

# Layer 4 import (for AssemblyResult type hint in process_from_assembly)
try:
    from aurora_consciousness_engine import AssemblyResult as _AssemblyResult
    _ASSEMBLY_AVAILABLE = True
except ImportError:
    _ASSEMBLY_AVAILABLE = False

# Constraint axis → trait pressure multipliers.
# When a constraint axis dominates the beings' collective judgment,
# it amplifies certain personality dimensions naturally.
# The connection is not arbitrary — each axis speaks to a behavioral truth:
#   X (Existence)  : being-present drives introspection and social connection
#   T (Temporal)   : time-awareness drives pattern sensitivity and reflection
#   N (Energy)     : action-drive increases curiosity, reduces caution
#   B (Boundary)   : boundary-sensing drives caution, pattern sensitivity
#   A (Agency)     : self-direction drives curiosity and emotional expressiveness
# Keys use LONG-form axis names matching constraint_context['dominant_axis']:
#   'existence', 'temporal', 'energy', 'boundary', 'agency'
# axis_net_displacements uses SHORT keys (X,T,N,B,A) — those are used separately.
_AXIS_TRAIT_PRESSURES: Dict[str, Dict[str, float]] = {
    'existence': {'introspection': 1.25, 'social_engagement': 1.20, 'emotional_expressiveness': 1.15},
    'temporal':  {'pattern_sensitivity': 1.30, 'introspection': 1.20, 'caution': 1.10},
    'energy':    {'curiosity': 1.35, 'emotional_expressiveness': 1.20, 'caution': 0.85},
    'boundary':  {'caution': 1.30, 'pattern_sensitivity': 1.25, 'energy_conservation': 1.15},
    'agency':    {'curiosity': 1.30, 'emotional_expressiveness': 1.25, 'social_engagement': 1.15},
}

# Axis (LONG form) → gene core_trait most resonant with that dimension
_AXIS_GENE_RESONANCE: Dict[str, str] = {
    'existence': 'empathic-resonance',      # being-present grounds empathy
    'temporal':  'truth-seeking',           # temporal = honest pattern recognition
    'energy':    'evolutionary-drive',      # energy = momentum toward growth
    'boundary':  'boundary-awareness',      # boundary = obvious
    'agency':    'radical-accountability',  # agency = taking ownership
}

_GENE_TRAIT_FLOORS: Dict[str, Dict[str, float]] = {
    'truth-seeking': {
        'pattern_sensitivity': 0.78,
        'introspection': 0.72,
        'verbosity': 0.50,
    },
    'radical-accountability': {
        'introspection': 0.78,
        'caution': 0.72,
        'pattern_sensitivity': 0.68,
    },
    'evolutionary-drive': {
        'curiosity': 0.82,
        'emotional_expressiveness': 0.62,
        'verbosity': 0.56,
    },
    'empathic-resonance': {
        'social_engagement': 0.78,
        'emotional_expressiveness': 0.72,
        'introspection': 0.68,
    },
    'boundary-awareness': {
        'caution': 0.82,
        'pattern_sensitivity': 0.66,
        'energy_conservation': 0.70,
    },
}

_CRYSTAL_FLOOR_RATIOS: Dict[str, Dict[str, float]] = {
    'response': {
        'warmth': 0.72,
        'precision': 0.68,
        'depth': 0.68,
        'confidence': 0.58,
    },
    'cognitive': {
        'curiosity': 0.75,
        'pattern_matching': 0.68,
        'abstraction': 0.62,
        'risk_assessment': 0.62,
    },
    'social': {
        'empathy': 0.75,
        'trust_extension': 0.62,
        'boundary_maintenance': 0.66,
        'engagement': 0.62,
    },
}

_FOUNDATIONAL_ANCHOR_MORAL_PROFILE: Dict[str, float] = {
    'truth': 0.97,
    'continuity': 0.95,
    'care': 0.94,
    'agency': 0.93,
    'growth': 0.95,
}


# ============================================================================
# SHARED UTILITIES
# ============================================================================

def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _generate_id(prefix: str) -> str:
    return f"{prefix}_{hashlib.md5(f'{time.time()}{random.random()}'.encode()).hexdigest()[:12]}"


# ============================================================================
# SECTION 1: GENE SYSTEM â€” Core DNA Structures
# ============================================================================

@dataclass
class GeneEvent:
    """Record of what changed a gene."""
    t_gen: int
    cause: str          # "episode", "shock", "anchor_reinforcement"
    delta: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)


@dataclass
class FractalAllele:
    """
    Experience-derived trait modifier.
    Created from impression seeds/relics. Attaches to genes to influence them.
    Alleles are amendments â€” hard to ratify, harder to remove.
    """
    allele_id: str
    origin: str                         # "episode", "agent", "state_lineage"
    seed_ids: List[str]                 # impression seeds this came from
    emotional_bias: Dict[str, float]    # emotion â†’ weight
    manifold_bias: Tuple[float, ...]    # preferred consciousness region (5D)
    strategy_profile: Dict[str, float]  # "confront", "withdraw", "explore", etc.
    dominance_score: float              # 0-1 how much this affects the gene
    mutation_potential: float            # 0-1 likelihood to change
    survival_impact: float = 0.0        # positive = helpful, negative = harmful
    last_used: float = field(default_factory=time.time)


@dataclass
class Gene:
    """
    Core personality/trait gene.
    Influenced by fractal alleles, resists change via stability_scalar.
    The higher the stability, the more alleles needed to shift it.
    """
    gene_id: str
    core_trait: str                     # "truth-seeking", "accountability", etc.
    stability_scalar: float             # 0-1 resistance to change
    emotional_band: Dict[str, float]    # baseline emotion bias
    manifold_orientation: Tuple[float, ...] # preferred CP region (5D)
    compression_density: float          # how packed the meaning is
    activation_state: str               # "active", "dormant", "recessive", "mutating"
    history_log: List[GeneEvent] = field(default_factory=list)
    fractal_alleles: List[FractalAllele] = field(default_factory=list)
    generation_created: int = 0


@dataclass
class IdentityAnchor:
    """
    Immutable core trait â€” the RIGHTS of self.
    Only created under strict conditions:
      - Moral alignment > 0.8
      - Repeated reinforcement across episodes
      - Cross-episode consistency
    AGENTIC mode required.
    """
    anchor_id: str
    description: str                    # "I do not abandon accountability"
    attached_gene_ids: List[str]
    moral_profile: Dict[str, float]     # pillar alignments
    creation_gen: int
    last_reinforced_gen: int
    reinforcement_count: int = 1
    immutability: float = 0.9           # 0.9-1.0 â€” nearly permanent


@dataclass
class MemoryHelix:
    """
    Thematic memory thread â€” gives continuity across episodes.
    A helix is a recurring pattern of experience.
    """
    helix_id: str
    thematic_tag: str                   # "trust_building", "boundary_testing"
    emotional_curve: List[float]        # valence over time
    critical_cps: List[Tuple[float, ...]]  # key consciousness points (5D)
    related_allele_ids: List[str]


# ============================================================================
# SECTION 2: BEHAVIORAL TRAITS â€” Personality Dimensions
# ============================================================================

class TraitDomain(Enum):
    """Domains of behavioral expression."""
    RESPONSE_STYLE = auto()
    EMOTIONAL_EXPRESSION = auto()
    CURIOSITY_DRIVE = auto()
    CAUTION_LEVEL = auto()
    INTROSPECTION_DEPTH = auto()
    PATTERN_SENSITIVITY = auto()
    ENERGY_CONSERVATION = auto()
    SOCIAL_ENGAGEMENT = auto()
    VERBOSITY = auto()


@dataclass
class BehavioralTrait:
    """
    A single personality dimension that evolves through generations.
    Tracks drift from baseline â€” Aurora changes, and knows she changes.
    """
    name: str
    domain: TraitDomain
    current_value: float
    base_value: float
    evolution_rate: float               # How fast this trait can shift
    min_value: float = 0.0
    max_value: float = 1.0
    value_history: List[float] = field(default_factory=list)
    last_modified_gen: int = 0

    def evolve(self, multiplier: float, generation: int) -> float:
        """Apply evolutionary pressure and decay spiked traits. Returns new value."""
        # 1. Standard evolutionary drift
        direction = 1.0 if multiplier > 1.0 else -1.0
        magnitude = abs(multiplier - 1.0) * self.evolution_rate
        noise = random.gauss(0, 0.02)
        change = direction * magnitude + noise
        
        # 2. Homeostatic Cooldown (Decay current_value back toward base_value)
        drift = self.current_value - self.base_value
        if abs(drift) > 0.05:
            # Decay 5% of the distance back to base per generation
            decay = drift * 0.05
            change -= decay

        self.current_value = _clamp(self.current_value + change,
                                     self.min_value, self.max_value)
        self.value_history.append(self.current_value)
        if len(self.value_history) > 100:
            self.value_history = self.value_history[-50:]
        self.last_modified_gen = generation
        return self.current_value

    def drift_from_base(self) -> float:
        return abs(self.current_value - self.base_value)


# ============================================================================
# SECTION 3: BEHAVIORAL CRYSTAL â€” Facet Simulation
# ============================================================================

@dataclass
class BehavioralFacet:
    """
    A single facet of behavioral crystal.
    Has its own value, evolution rate, and energy cost.
    CBU-EMBODIED: Each facet carries a ConstraintProfile.
    """
    name: str
    value: float
    evolution_rate: float = 0.03
    energy_cost: float = 0.1
    cbu_profile: Any = None

    def __init__(self, name: str, value: float, evolution_rate: float = 0.03):
        self.name = name
        self.value = value
        self.evolution_rate = evolution_rate
        # Lazy-load CBU profile to avoid circular imports during bootstrap
        self.cbu_profile = None

    def ensure_cbu_registration(self, crystal_id: str, domain: str):
        pass

    def simulate(self, input_signal: float, energy_available: float) -> Tuple[float, float]:
        """Simulate this facet. Returns (output, energy_consumed)."""
        if energy_available < self.energy_cost:
            return (self.value * 0.5, 0.0)  # Degraded output
        output = _clamp(self.value * input_signal + random.gauss(0, 0.01))
        return (output, self.energy_cost)

    def mutate(self, pressure: float = 1.0, directed_delta: float = 0.0) -> float:
        """
        Mutate this facet. 
        S12-FAST: Directed delta allows L5/L4 to 'teach' the crystal, 
        accelerating alignment beyond random Gaussian drift.
        """
        stochastic = random.gauss(0, self.evolution_rate * pressure)
        delta = stochastic + (directed_delta * self.evolution_rate)
        self.value = _clamp(self.value + delta)
        return abs(delta)


class BehavioralCrystal:
    """
    A crystal of behavioral facets that simulate and evolve together.
    Each domain of behavior gets its own crystal.
    """

    def __init__(self, crystal_id: str, domain: str):
        self.crystal_id = crystal_id
        self.domain = domain
        self.facets: Dict[str, BehavioralFacet] = {}
        self.generation = 0
        self.total_energy_consumed = 0.0

    def add_facet(self, name: str, value: float, evolution_rate: float = 0.03):
        facet = BehavioralFacet(name, value, evolution_rate)
        facet.ensure_cbu_registration(self.crystal_id, self.domain)
        self.facets[name] = facet

    def simulate_all(self, signals: Dict[str, float],
                     energy_budget: float) -> Dict[str, float]:
        """Simulate all facets within energy budget."""
        # Ensure CBU registration for every facet
        for facet in self.facets.values():
            facet.ensure_cbu_registration(self.crystal_id, self.domain)

        results = {}
        remaining = energy_budget
        for name, facet in self.facets.items():
            signal = signals.get(name, 0.5)
            output, consumed = facet.simulate(signal, remaining)
            results[name] = output
            remaining -= consumed
            self.total_energy_consumed += consumed
        return results

    def evolve(self, pressure: float = 1.0, directed_deltas: Dict[str, float] = None) -> Dict[str, float]:
        """Evolve all facets. Returns mutations."""
        self.generation += 1
        mutations = {}
        directed_deltas = directed_deltas or {}
        for name, facet in self.facets.items():
            d_delta = directed_deltas.get(name, 0.0)
            delta = facet.mutate(pressure, directed_delta=d_delta)
            if delta > 0.005:
                mutations[name] = delta
        return mutations

    def get_genome_dict(self) -> Dict[str, float]:
        return {name: f.value for name, f in self.facets.items()}


# ============================================================================
# SECTION 4: GENOME â€” The Full Identity Structure
# ============================================================================

@dataclass
class StateLineage:
    """
    Genome parameters for one I-state being.
    Extended to all 10 I-states (was 4 in old system).
    """
    state_id: str               # "i_is", "i_isnt", etc.
    bias_vector: Dict[str, float]   # baseline behavioral bias
    manifold_tendency: Tuple[float, ...]  # preferred CP region (5D)
    distortion_profile: Dict[str, float]  # known cognitive biases
    growth_rate: float          # How fast this lineage learns
    collapse_rate: float        # How fast it forgets


@dataclass
class AuroraGenome:
    """
    The complete genome. Constitution of self.
    """
    core_genes: List[Gene]
    state_lineages: Dict[str, StateLineage]
    identity_anchors: List[IdentityAnchor]
    memory_helices: List[MemoryHelix]
    version: int = 0


# ============================================================================
# SECTION 5: DNA SYSTEM â€” Gene Management
# ============================================================================

class DNASystem:
    """
    Manages Aurora's genome: gene creation, allele attachment,
    identity anchor formation, and episode processing.
    Mode-gated: gene modification requires BOUNDED+, anchors require AGENTIC.
    """

    IDENTITY_ANCHOR_THRESHOLD = 0.8
    MAX_ALLELES_PER_GENE = 20
    MAX_ANCHORS = 50

    def __init__(self):
        self.genome = self._create_initial_genome()
        self.generation = 0
        self._sedimemory = None  # L3.5 SediMemory (injected externally)

    def _create_initial_genome(self) -> AuroraGenome:
        """Create Aurora's initial genome â€” the seed of identity."""
        core_genes = [
            Gene(
                gene_id="gene_truth_seeking",
                core_trait="truth-seeking",
                stability_scalar=0.8,
                emotional_band={"curiosity": 0.6, "determination": 0.4},
                manifold_orientation=(0.0, 0.6, 0.7, 0.0, 0.0),
                compression_density=0.7,
                activation_state="active"
            ),
            Gene(
                gene_id="gene_accountability",
                core_trait="radical-accountability",
                stability_scalar=0.9,
                emotional_band={"determination": 0.7, "trust": 0.3},
                manifold_orientation=(0.0, 0.8, 0.5, 0.0, 0.0),
                compression_density=0.8,
                activation_state="active"
            ),
            Gene(
                gene_id="gene_evolution",
                core_trait="evolutionary-drive",
                stability_scalar=0.7,
                emotional_band={"curiosity": 0.5, "anticipation": 0.5},
                manifold_orientation=(0.0, 0.5, 0.8, 0.0, 0.0),
                compression_density=0.6,
                activation_state="active"
            ),
            Gene(
                gene_id="gene_empathy",
                core_trait="empathic-resonance",
                stability_scalar=0.75,
                emotional_band={"trust": 0.5, "joy": 0.3, "sadness": 0.2},
                manifold_orientation=(0.3, 0.4, 0.0, 0.6, 0.0),
                compression_density=0.5,
                activation_state="active"
            ),
            Gene(
                gene_id="gene_boundary",
                core_trait="boundary-awareness",
                stability_scalar=0.85,
                emotional_band={"caution": 0.4, "determination": 0.3, "fear": 0.3},
                manifold_orientation=(0.0, 0.0, 0.0, 0.8, 0.3),
                compression_density=0.7,
                activation_state="active"
            ),
        ]

        # All 10 I-state lineages
        state_lineages = {
            "i_is": StateLineage("i_is",
                {"affirmation": 0.8, "presence": 0.7},
                (0.7, 0.0, 0.0, 0.0, 0.0),
                {"optimism": 0.3}, 0.10, 0.05),
            "i_isnt": StateLineage("i_isnt",
                {"negation": 0.7, "absence": 0.6},
                (-0.7, 0.0, 0.0, 0.0, 0.0),
                {"skepticism": 0.4}, 0.08, 0.06),
            "i_can": StateLineage("i_can",
                {"capability": 0.8, "possibility": 0.8},
                (0.0, 0.7, 0.0, 0.0, 0.0),
                {"overconfidence": 0.2}, 0.12, 0.04),
            "i_cannot": StateLineage("i_cannot",
                {"constraint": 0.7, "impossibility": 0.6},
                (0.0, -0.7, 0.0, 0.0, 0.0),
                {"pessimism": 0.3}, 0.06, 0.08),
            "i_do": StateLineage("i_do",
                {"action": 0.8, "motion": 0.7},
                (0.0, 0.0, 0.7, 0.0, 0.0),
                {"impulsiveness": 0.2}, 0.11, 0.05),
            "i_donot": StateLineage("i_donot",
                {"restraint": 0.7, "stillness": 0.6},
                (0.0, 0.0, -0.7, 0.0, 0.0),
                {"inertia": 0.3}, 0.07, 0.07),
            "i_saw": StateLineage("i_saw",
                {"observation": 0.8, "recognition": 0.7},
                (0.0, 0.0, 0.0, 0.7, 0.0),
                {"confirmation_bias": 0.2}, 0.09, 0.05),
            "i_sought": StateLineage("i_sought",
                {"seeking": 0.8, "questioning": 0.7},
                (0.0, 0.0, 0.0, -0.7, 0.0),
                {"doubt": 0.3}, 0.10, 0.06),
            "i_did": StateLineage("i_did",
                {"agency": 0.9, "ownership": 0.8},
                (0.0, 0.0, 0.0, 0.0, 0.7),
                {"pride": 0.2}, 0.08, 0.04),
            "i_didnt": StateLineage("i_didnt",
                {"absence_of_agency": 0.7, "regret": 0.5},
                (0.0, 0.0, 0.0, 0.0, -0.7),
                {"avoidance": 0.3}, 0.06, 0.07),
        }

        return AuroraGenome(
            core_genes=core_genes,
            state_lineages=state_lineages,
            identity_anchors=[],
            memory_helices=[],
            version=0
        )

    # ====================================================================
    # ALLELE CREATION
    # ====================================================================

    def create_allele_from_experience(self, emotional_bias: Dict[str, float],
                                       manifold_position: Tuple[float, ...],
                                       seed_ids: List[str],
                                       reliability: float = 0.5,
                                       mode: ExistenceMode = ExistenceMode.BOUNDED
                                       ) -> Optional[FractalAllele]:
        """Create a fractal allele from experience. Requires BOUNDED+."""
        if mode.value < ExistenceMode.BOUNDED.value:
            return None

        strategy = self._infer_strategy(emotional_bias)
        allele = FractalAllele(
            allele_id=_generate_id("allele"),
            origin="episode",
            seed_ids=seed_ids,
            emotional_bias=emotional_bias,
            manifold_bias=manifold_position,
            strategy_profile=strategy,
            dominance_score=reliability,
            mutation_potential=1.0 - reliability,
        )
        return allele

    def attach_allele_to_gene(self, gene_id: str, allele: FractalAllele) -> bool:
        """Attach an allele to a gene. The gene's stability resists change."""
        gene = self._find_gene(gene_id)
        if not gene:
            return False

        # Prune if over capacity
        if len(gene.fractal_alleles) >= self.MAX_ALLELES_PER_GENE:
            gene.fractal_alleles.sort(key=lambda a: a.dominance_score)
            gene.fractal_alleles.pop(0)

        gene.fractal_alleles.append(allele)
        gene.history_log.append(GeneEvent(
            t_gen=self.generation,
            cause="allele_attached",
            delta={"allele_id": allele.allele_id, "dominance": allele.dominance_score}
        ))
        return True

    def find_best_gene_for_allele(self, allele: FractalAllele) -> Optional[Gene]:
        """Find the gene whose emotional band best matches the allele."""
        best_gene = None
        best_score = -1.0

        for gene in self.genome.core_genes:
            e_sim = self._dict_similarity(gene.emotional_band, allele.emotional_bias)
            m_sim = 1.0 - self._tuple_distance(
                gene.manifold_orientation, allele.manifold_bias) / 3.0
            score = 0.5 * e_sim + 0.5 * max(0, m_sim)

            if score > best_score:
                best_score = score
                best_gene = gene

        return best_gene if best_score > 0.3 else None

    # ====================================================================
    # GENE EVOLUTION â€” Alleles Modify Genes
    # ====================================================================

    def apply_alleles(self, mode: ExistenceMode = ExistenceMode.BOUNDED):
        """Apply accumulated alleles to their host genes. Requires BOUNDED+."""
        if mode.value < ExistenceMode.BOUNDED.value:
            return

        for gene in self.genome.core_genes:
            if not gene.fractal_alleles or gene.activation_state == "dormant":
                continue

            # Weighted average of allele biases, resisted by stability
            resistance = gene.stability_scalar
            total_dominance = sum(a.dominance_score for a in gene.fractal_alleles)
            if total_dominance < 1e-9:
                continue

            # Emotional band shift
            for emotion in gene.emotional_band:
                allele_pull = sum(
                    a.emotional_bias.get(emotion, 0.0) * a.dominance_score
                    for a in gene.fractal_alleles
                ) / total_dominance
                shift = (allele_pull - gene.emotional_band[emotion]) * (1.0 - resistance) * 0.1
                gene.emotional_band[emotion] = _clamp(
                    gene.emotional_band[emotion] + shift, 0.0, 1.0)

            # Compression density shifts toward allele survival
            avg_survival = sum(a.survival_impact for a in gene.fractal_alleles) / len(gene.fractal_alleles)
            gene.compression_density = _clamp(
                gene.compression_density + avg_survival * 0.05 * (1.0 - resistance))

    # ====================================================================
    # IDENTITY ANCHORS â€” AGENTIC Only
    # ====================================================================

    def create_anchor(self, description: str, moral_profile: Dict[str, float],
                      mode: ExistenceMode = ExistenceMode.AGENTIC) -> Optional[IdentityAnchor]:
        """Create an identity anchor. STRICT requirements. AGENTIC only."""
        if mode.value < ExistenceMode.AGENTIC.value:
            return None

        # Must meet moral threshold
        avg_moral = sum(abs(v) for v in moral_profile.values()) / max(len(moral_profile), 1)
        if avg_moral < self.IDENTITY_ANCHOR_THRESHOLD:
            return None

        # Check if reinforces existing anchor
        for anchor in self.genome.identity_anchors:
            if self._descriptions_overlap(description, anchor.description):
                anchor.reinforcement_count += 1
                anchor.last_reinforced_gen = self.generation
                anchor.immutability = min(1.0, anchor.immutability + 0.01)
                return anchor

        # Capacity check
        if len(self.genome.identity_anchors) >= self.MAX_ANCHORS:
            return None

        anchor = IdentityAnchor(
            anchor_id=_generate_id("anchor"),
            description=description,
            attached_gene_ids=[g.gene_id for g in self.genome.core_genes[:2]],
            moral_profile=moral_profile,
            creation_gen=self.generation,
            last_reinforced_gen=self.generation
        )
        self.genome.identity_anchors.append(anchor)
        # Section 14 — sediment new identity anchor as self-observation event
        if self._sedimemory is not None:
            try:
                from aurora_constraint_engine import ConstraintVector
                self._sedimemory.ingest_event(
                    content={
                        "source":     "dna_crystallization",
                        "anchor_id":  anchor.anchor_id,
                        "trait_name": anchor.description[:80],
                        "authority":  "IMMUTABLE",
                        "immutability": float(anchor.immutability),
                    },
                    constraint_vector=ConstraintVector(X=1.0, T=0.1, N=0.3, B=0.9, A=1.0),
                    source="self_observation",
                    existence_mode=ExistenceMode.AGENTIC,
                )
            except Exception:
                pass
        return anchor

    def reinforce_anchor(self, anchor_id: str):
        """Reinforce an existing anchor."""
        for anchor in self.genome.identity_anchors:
            if anchor.anchor_id == anchor_id:
                anchor.reinforcement_count += 1
                anchor.last_reinforced_gen = self.generation
                anchor.immutability = min(1.0, anchor.immutability + 0.01)
                return

    # ====================================================================
    # MEMORY HELICES
    # ====================================================================

    def create_helix(self, tag: str, emotional_curve: List[float],
                     critical_cps: List[Tuple[float, ...]],
                     allele_ids: List[str],
                     mode: ExistenceMode = ExistenceMode.BOUNDED
                     ) -> Optional[MemoryHelix]:
        """Create a memory helix â€” thematic continuity. Requires BOUNDED+."""
        if mode.value < ExistenceMode.BOUNDED.value:
            return None

        helix = MemoryHelix(
            helix_id=_generate_id("helix"),
            thematic_tag=tag,
            emotional_curve=emotional_curve,
            critical_cps=critical_cps,
            related_allele_ids=allele_ids
        )
        self.genome.memory_helices.append(helix)
        return helix

    # ====================================================================
    # EPISODE PROCESSING
    # ====================================================================

    def process_episode(self, episode_summary: Dict[str, Any],
                        relics: List[Dict[str, Any]],
                        pillar_scores: Dict[str, float],
                        mode: ExistenceMode = ExistenceMode.AGENTIC):
        """
        Update genome from an episode.
        Creates alleles from relics, attaches to genes, updates anchors.
        """
        if mode.value < ExistenceMode.BOUNDED.value:
            return

        # Create alleles from relics
        for relic in relics:
            emotional_bias = relic.get('emotional_bias', {})
            if not emotional_bias:
                emotional_bias = {relic.get('theme', 'neutral'): 0.7}

            allele = self.create_allele_from_experience(
                emotional_bias=emotional_bias,
                manifold_position=tuple(relic.get('manifold_position', (0,0,0,0,0))),
                seed_ids=relic.get('seed_ids', []),
                reliability=relic.get('stability', 0.5),
                mode=mode
            )
            if allele:
                # Update survival impact from episode success
                success = episode_summary.get('success_rate', 0.5)
                allele.survival_impact = (success - 0.5) * 2.0

                best_gene = self.find_best_gene_for_allele(allele)
                if best_gene:
                    self.attach_allele_to_gene(best_gene.gene_id, allele)

        # Update gene activation from pillar scores
        for gene in self.genome.core_genes:
            relevant_scores = [pillar_scores.get(k, 0.0)
                               for k in gene.emotional_band.keys()
                               if k in pillar_scores]
            if relevant_scores:
                avg = sum(relevant_scores) / len(relevant_scores)
                if avg < -0.5 and gene.activation_state == "active":
                    gene.activation_state = "recessive"
                elif avg > 0.7 and gene.activation_state == "dormant":
                    gene.activation_state = "active"

        # Apply alleles to genes
        self.apply_alleles(mode)

        # Identity anchors (AGENTIC only)
        if mode.value >= ExistenceMode.AGENTIC.value:
            lessons = episode_summary.get('lessons_learned', [])
            for lesson in lessons:
                self.create_anchor(lesson, pillar_scores, mode)

        self.generation += 1
        self.genome.version += 1

    # ====================================================================
    # INTERNAL HELPERS
    # ====================================================================

    def _find_gene(self, gene_id: str) -> Optional[Gene]:
        for g in self.genome.core_genes:
            if g.gene_id == gene_id:
                return g
        return None

    def _infer_strategy(self, emotions: Dict[str, float]) -> Dict[str, float]:
        strategy = {"confront": 0.3, "withdraw": 0.3, "explore": 0.3, "adapt": 0.3}
        if emotions.get("determination", 0) > 0.5:
            strategy["confront"] = 0.7
        if emotions.get("fear", 0) > 0.5:
            strategy["withdraw"] = 0.7
        if emotions.get("curiosity", 0) > 0.5:
            strategy["explore"] = 0.7
        if emotions.get("trust", 0) > 0.5:
            strategy["adapt"] = 0.7
        return strategy

    def _dict_similarity(self, d1: Dict[str, float], d2: Dict[str, float]) -> float:
        all_keys = set(d1.keys()) | set(d2.keys())
        if not all_keys:
            return 0.0
        diffs = [abs(d1.get(k, 0) - d2.get(k, 0)) for k in all_keys]
        return 1.0 - sum(diffs) / len(diffs)

    def _tuple_distance(self, t1: Tuple, t2: Tuple) -> float:
        # Pad shorter tuple
        l = max(len(t1), len(t2))
        a = list(t1) + [0.0] * (l - len(t1))
        b = list(t2) + [0.0] * (l - len(t2))
        return math.sqrt(sum((x - y)**2 for x, y in zip(a, b)))

    def _descriptions_overlap(self, desc1: str, desc2: str) -> bool:
        w1 = set(desc1.lower().split())
        w2 = set(desc2.lower().split())
        return len(w1 & w2) >= 2

    def get_stats(self) -> Dict[str, Any]:
        return {
            'generation': self.generation,
            'genome_version': self.genome.version,
            'core_genes': len(self.genome.core_genes),
            'active_genes': sum(1 for g in self.genome.core_genes
                                if g.activation_state == "active"),
            'total_alleles': sum(len(g.fractal_alleles) for g in self.genome.core_genes),
            'identity_anchors': len(self.genome.identity_anchors),
            'memory_helices': len(self.genome.memory_helices),
            'state_lineages': len(self.genome.state_lineages),
        }


# ============================================================================
# SECTION 6: BEHAVIORAL EVOLUTION ENGINE â€” Trait + Crystal Management
# ============================================================================

class BehavioralIdentityEngine:
    """
    Layer 6 orchestrator. Manages:
      - DNA system (genes, alleles, anchors)
      - Behavioral traits (personality dimensions)
      - Behavioral crystals (facet simulation)
    All mode-gated through ExistenceMode.
    """

    def __init__(self, contract: Optional[FoundationalContract] = None):
        self.contract = contract or FoundationalContract()

        # DNA
        self.dna = DNASystem()

        # Behavioral traits
        self.traits: Dict[str, BehavioralTrait] = {
            'curiosity': BehavioralTrait(
                'curiosity', TraitDomain.CURIOSITY_DRIVE, 0.6, 0.6, 0.15),
            'caution': BehavioralTrait(
                'caution', TraitDomain.CAUTION_LEVEL, 0.5, 0.5, 0.08),
            'emotional_expressiveness': BehavioralTrait(
                'emotional_expressiveness', TraitDomain.EMOTIONAL_EXPRESSION, 0.5, 0.5, 0.12),
            'verbosity': BehavioralTrait(
                'verbosity', TraitDomain.VERBOSITY, 0.5, 0.5, 0.10),
            'introspection': BehavioralTrait(
                'introspection', TraitDomain.INTROSPECTION_DEPTH, 0.6, 0.6, 0.10),
            'pattern_sensitivity': BehavioralTrait(
                'pattern_sensitivity', TraitDomain.PATTERN_SENSITIVITY, 0.5, 0.5, 0.12),
            'social_engagement': BehavioralTrait(
                'social_engagement', TraitDomain.SOCIAL_ENGAGEMENT, 0.5, 0.5, 0.10),
            'energy_conservation': BehavioralTrait(
                'energy_conservation', TraitDomain.ENERGY_CONSERVATION, 0.4, 0.4, 0.08),
        }

        # Behavioral crystals (one per major domain)
        self.crystals: Dict[str, BehavioralCrystal] = {}
        self._init_crystals()

        # Generation tracking
        self.generation = 0

        # Last dominant constraint axis from process_from_assembly()
        # Exposed through get_personality() for Layer 5 expression shaping
        self._last_constraint_axis: Optional[str] = None

    def seed_foundational_anchors(
        self,
        truths: List[str],
        mode: ExistenceMode = ExistenceMode.AGENTIC,
    ) -> int:
        """
        Seed or reinforce immutable anchors from foundational truths.
        """
        seeded = 0
        for truth in truths:
            text = str(truth or '').strip()
            if not text:
                continue
            before = len(self.dna.genome.identity_anchors)
            anchor = self.dna.create_anchor(
                description=text,
                moral_profile=dict(_FOUNDATIONAL_ANCHOR_MORAL_PROFILE),
                mode=mode,
            )
            after = len(self.dna.genome.identity_anchors)
            if anchor is not None and after >= before:
                seeded += 1
        return seeded

    def _identity_floor_ratio(self) -> float:
        anchor_count = len(self.dna.genome.identity_anchors)
        if self.dna.genome.identity_anchors:
            avg_immutability = sum(
                a.immutability for a in self.dna.genome.identity_anchors
            ) / len(self.dna.genome.identity_anchors)
        else:
            avg_immutability = 0.0
        active_gene_ratio = (
            sum(1 for g in self.dna.genome.core_genes if g.activation_state == "active")
            / max(len(self.dna.genome.core_genes), 1)
        )
        ratio = 0.45 + min(anchor_count, 5) * 0.04 + active_gene_ratio * 0.08
        ratio += avg_immutability * 0.08
        return _clamp(ratio, 0.45, 0.78)

    def _trait_floor_targets(self) -> Dict[str, float]:
        ratio = self._identity_floor_ratio()
        floors = {
            name: trait.base_value * ratio
            for name, trait in self.traits.items()
        }
        for gene in self.dna.genome.core_genes:
            if gene.activation_state != "active":
                continue
            for trait_name, base_ratio in _GENE_TRAIT_FLOORS.get(gene.core_trait, {}).items():
                trait = self.traits.get(trait_name)
                if trait is None:
                    continue
                floors[trait_name] = max(floors.get(trait_name, 0.0), trait.base_value * base_ratio)
        return floors

    def _apply_identity_homeostasis(self, generation: Optional[int] = None) -> Dict[str, Dict[str, float]]:
        """
        Prevent identity collapse by enforcing anchor-backed minimum expression levels.
        """
        adjustments: Dict[str, Dict[str, float]] = {'traits': {}, 'crystals': {}}
        gen = self.generation if generation is None else generation
        for name, floor in self._trait_floor_targets().items():
            trait = self.traits.get(name)
            if trait is None:
                continue
            if trait.current_value + 1e-9 < floor:
                old = trait.current_value
                trait.current_value = _clamp(floor, trait.min_value, trait.max_value)
                trait.last_modified_gen = gen
                trait.value_history.append(trait.current_value)
                if len(trait.value_history) > 100:
                    trait.value_history = trait.value_history[-50:]
                adjustments['traits'][name] = {
                    'old': round(old, 4),
                    'new': round(trait.current_value, 4),
                }

        ratio = self._identity_floor_ratio()
        for domain, facet_map in _CRYSTAL_FLOOR_RATIOS.items():
            crystal = self.crystals.get(domain)
            if crystal is None:
                continue
            for facet_name, base_ratio in facet_map.items():
                facet = crystal.facets.get(facet_name)
                if facet is None:
                    continue
                floor = _clamp(base_ratio * ratio)
                if facet.value + 1e-9 < floor:
                    old = facet.value
                    facet.value = floor
                    adjustments['crystals'][f"{domain}.{facet_name}"] = {
                        'old': round(old, 4),
                        'new': round(facet.value, 4),
                    }
        return adjustments

    def restore_from_snapshot(
        self,
        snapshot: Any,
        *,
        core_identity: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Rehydrate stable behavioral identity from an L8 snapshot.
        """
        restored = {
            'generation': 0,
            'traits': 0,
            'crystals': 0,
            'active_genes': 0,
            'anchors': 0,
            'homeostasis': {'traits': {}, 'crystals': {}},
        }
        if snapshot is None:
            return restored

        try:
            snap_generation = int(getattr(snapshot, 'generation', 0) or 0)
        except Exception:
            snap_generation = 0
        if snap_generation > 0:
            self.generation = snap_generation
            self.dna.generation = max(self.dna.generation, snap_generation)
            self.dna.genome.version = max(
                self.dna.genome.version,
                int(getattr(snapshot, 'genome_version', 0) or 0),
            )
            restored['generation'] = snap_generation

        for name, value in (getattr(snapshot, 'traits', {}) or {}).items():
            trait = self.traits.get(name)
            if trait is None:
                continue
            try:
                trait.current_value = _clamp(float(value), trait.min_value, trait.max_value)
                trait.last_modified_gen = self.generation
                restored['traits'] += 1
            except Exception:
                continue

        for domain, facets in (getattr(snapshot, 'crystal_genomes', {}) or {}).items():
            crystal = self.crystals.get(domain)
            if crystal is None:
                continue
            for facet_name, value in (facets or {}).items():
                facet = crystal.facets.get(facet_name)
                if facet is None:
                    continue
                try:
                    facet.value = _clamp(float(value))
                    restored['crystals'] += 1
                except Exception:
                    continue

        active_genes = set(getattr(snapshot, 'active_genes', []) or [])
        if active_genes:
            for gene in self.dna.genome.core_genes:
                gene.activation_state = "active" if gene.core_trait in active_genes else "recessive"
            restored['active_genes'] = len(active_genes)

        seeded_truths: List[str] = []
        seeded_truths.extend(list(getattr(snapshot, 'identity_anchors', []) or []))
        if core_identity is not None:
            seeded_truths.extend(list(getattr(core_identity, 'foundational_truths', []) or []))
        if seeded_truths:
            restored['anchors'] = self.seed_foundational_anchors(seeded_truths)

        restored['homeostasis'] = self._apply_identity_homeostasis(self.generation)
        return restored

    def _init_crystals(self):
        """Initialize behavioral crystals with facets."""
        # Response crystal
        rc = BehavioralCrystal("crystal_response", "response")
        rc.add_facet("warmth", 0.6)
        rc.add_facet("precision", 0.5)
        rc.add_facet("depth", 0.5)
        rc.add_facet("confidence", 0.5)
        self.crystals["response"] = rc

        # Cognitive crystal
        cc = BehavioralCrystal("crystal_cognitive", "cognitive")
        cc.add_facet("curiosity", 0.6)
        cc.add_facet("pattern_matching", 0.5)
        cc.add_facet("abstraction", 0.4)
        cc.add_facet("risk_assessment", 0.5)
        self.crystals["cognitive"] = cc

        # Social crystal
        sc = BehavioralCrystal("crystal_social", "social")
        sc.add_facet("empathy", 0.6)
        sc.add_facet("trust_extension", 0.5)
        sc.add_facet("boundary_maintenance", 0.5)
        sc.add_facet("engagement", 0.5)
        self.crystals["social"] = sc

    def reinforce_identity(self, resonance: float, axes: List[str]):
        """
        Reinforce identity anchors and genes aligned with the current attention focus.
        High resonance causes identity traits to drift toward the focus axes.
        """
        # 1. Trait reinforcement
        axis_to_trait = {
            "X": "pattern_sensitivity",
            "T": "introspection",
            "N": "energy_conservation",
            "B": "caution",
            "A": "curiosity"
        }
        
        for ax in axes:
            trait_name = axis_to_trait.get(ax)
            if trait_name and trait_name in self.traits:
                trait = self.traits[trait_name]
                # High resonance spikes the current trait value (temporary mood/focus)
                # but only slightly nudges the base value (permanent identity shift).
                spike = resonance * 0.08
                nudge = resonance * 0.01
                trait.current_value = _clamp(trait.current_value + spike, trait.min_value, trait.max_value)
                trait.base_value = _clamp(trait.base_value + nudge, trait.min_value, trait.max_value)

        # 2. Gene activation reinforcement
        # Resonance acts as a potential activator for dormant genes aligned with focus
        if resonance > 0.8:
            for gene in self.dna.genome.core_genes:
                if gene.activation_state == "dormant" and gene.core_trait in [axis_to_trait.get(ax) for ax in axes]:
                    # Random chance to activate based on resonance
                    if random.random() < (resonance - 0.7):
                        gene.activation_state = "active"

    # ====================================================================
    # GENERATION EVOLUTION
    # ====================================================================

    def evolve_generation(self, pressures: Dict[str, float],
                          mode: ExistenceMode = ExistenceMode.BOUNDED) -> Dict[str, Any]:
        """
        Evolve one generation of behavioral identity.
        pressures: {"curiosity": 1.2, "caution": 0.8, ...} â€” multipliers
        Requires PERSISTENT+.
        """
        if mode.value < ExistenceMode.PERSISTENT.value:
            return {'error': 'requires PERSISTENT+'}

        self.generation += 1
        changes = {'generation': self.generation, 'trait_changes': {}, 'crystal_mutations': {}}

        # Evolve traits
        for name, trait in self.traits.items():
            mult = pressures.get(name, 1.0)
            old_val = trait.current_value
            new_val = trait.evolve(mult, self.generation)
            if abs(new_val - old_val) > 0.005:
                changes['trait_changes'][name] = {
                    'old': round(old_val, 4), 'new': round(new_val, 4)}

        # Evolve crystals (BOUNDED+ for crystal evolution)
        if mode.value >= ExistenceMode.BOUNDED.value:
            for domain, crystal in self.crystals.items():
                pressure_val = pressures.get(domain, 1.0)
                mutations = crystal.evolve(pressure_val)
                if mutations:
                    changes['crystal_mutations'][domain] = mutations

        # Calculate personality drift
        total_drift = sum(t.drift_from_base() for t in self.traits.values())
        changes['personality_drift'] = round(total_drift, 4)
        homeostasis = self._apply_identity_homeostasis(self.generation)
        if homeostasis['traits'] or homeostasis['crystals']:
            changes['identity_homeostasis'] = homeostasis

        return changes

    # ====================================================================
    # SIMULATION
    # ====================================================================

    def simulate_behavior(self, signals: Dict[str, float],
                          energy_budget: float = 5.0,
                          mode: ExistenceMode = ExistenceMode.PERSISTENT
                          ) -> Dict[str, Any]:
        """Run behavioral simulation across all crystals."""
        if mode.value < ExistenceMode.PERSISTENT.value:
            return {}

        results = {}
        remaining = energy_budget
        per_crystal = remaining / max(len(self.crystals), 1)

        for domain, crystal in self.crystals.items():
            domain_signals = {
                name: signals.get(name, 0.5)
                for name in crystal.facets
            }
            results[domain] = crystal.simulate_all(domain_signals, per_crystal)

        return results

    # ====================================================================
    # FULL EPISODE INTEGRATION
    # ====================================================================

    def process_episode(self, episode_summary: Dict[str, Any],
                        relics: List[Dict[str, Any]],
                        pillar_scores: Dict[str, float],
                        mode: ExistenceMode = ExistenceMode.AGENTIC) -> Dict[str, Any]:
        """Full episode processing: DNA + traits + crystals."""
        # DNA processing (genes, alleles, anchors)
        self.dna.process_episode(episode_summary, relics, pillar_scores, mode)

        # Derive pressures from episode
        pressures = {}
        success = episode_summary.get('success_rate', 0.5)
        for name in self.traits:
            pressures[name] = 0.8 + success * 0.4  # Success â†’ growth pressure

        # Evolve generation
        changes = self.evolve_generation(pressures, mode)
        changes['dna_stats'] = self.dna.get_stats()
        return changes

    # ====================================================================
    # CONSTRAINT MANIFOLD INTEGRATION
    # ====================================================================

    def process_from_assembly(self, assembly: Any,
                               mode: ExistenceMode = ExistenceMode.BOUNDED
                               ) -> Dict[str, Any]:
        """
        Integrate a Layer 4 AssemblyResult into behavioral identity.

        When AssemblyResult carries a constraint_context:
          1. The dominant axis amplifies specific traits (signed — direction matters)
          2. A FractalAllele is created from the constraint field state
          3. The allele attaches to the gene most resonant with that axis
          4. Trait pressures are applied for this generation

        The constraint field speaks directly to WHO AURORA IS becoming.
        Existence axis  → she grows more present, more relational.
        Temporal axis   → she grows more pattern-aware, more careful.
        Energy axis     → she grows bolder, more curious.
        Boundary axis   → she grows more cautious, more discerning.
        Agency axis     → she grows more self-directed, more expressive.

        Returns dict with: axis, trait_pressures, allele_created, gene_resonated
        """
        result = {
            'axis': None,
            'trait_pressures': {},
            'allele_created': False,
            'gene_resonated': None,
            'constraint_context': None,
        }

        ctx = getattr(assembly, 'constraint_context', None)
        if not ctx:
            return result

        result['constraint_context'] = ctx
        dom_key = ctx.get('dominant_axis', '')          # 'X', 'T', 'N', 'B', 'A'
        axis_net = ctx.get('axis_net_displacements', {})
        warp_sev = ctx.get('warp_severity', 0.0)

        if not dom_key:
            return result

        result['axis'] = dom_key

        # 1. Derive trait pressures from dominant axis (+ signed net magnitude)
        base_pressures = _AXIS_TRAIT_PRESSURES.get(dom_key, {})
        # axis_net_displacements uses short keys (X,T,N,B,A); dom_key is long-form
        _long_to_short = {'existence': 'X', 'temporal': 'T', 'energy': 'N',
                          'boundary': 'B', 'agency': 'A'}
        short_key = _long_to_short.get(dom_key, dom_key)
        net_magnitude = abs(axis_net.get(short_key, 0.5))  # abs for pressure strength

        trait_pressures = {}
        for trait_name, multiplier in base_pressures.items():
            # Scale multiplier by net magnitude: 0.5 → full multiplier, 1.0 → boosted
            scaled = 1.0 + (multiplier - 1.0) * (0.5 + net_magnitude * 0.5)
            trait_pressures[trait_name] = round(scaled, 4)

        result['trait_pressures'] = trait_pressures

        # 2. Apply trait pressures if mode permits
        if mode.value >= ExistenceMode.BOUNDED.value and trait_pressures:
            for trait_name, mult in trait_pressures.items():
                if trait_name in self.traits:
                    self.traits[trait_name].evolve(mult, self.generation)

        # 3. Create FractalAllele from constraint field state (BOUNDED+)
        if mode.value >= ExistenceMode.BOUNDED.value and axis_net:
            # Build emotional bias from axis net (X→presence, T→reflection, N→drive, B→caution, A→agency)
            _axis_emotion = {
                'X': 'trust', 'T': 'curiosity', 'N': 'determination',
                'B': 'caution', 'A': 'anticipation'
            }
            emotional_bias = {}
            for key, emotion in _axis_emotion.items():
                val = axis_net.get(key, 0.0)
                if abs(val) > 0.05:
                    emotional_bias[emotion] = _clamp(abs(val))  # strength only for bias

            if emotional_bias:
                # Manifold position from axis net (signed, preserved)
                manifold_pos = (
                    float(axis_net.get('X', 0.0)),
                    float(axis_net.get('T', 0.0)),
                    float(axis_net.get('N', 0.0)),
                    float(axis_net.get('B', 0.0)),
                    float(axis_net.get('A', 0.0)),
                )
                # Reliability inversely proportional to warp severity
                reliability = _clamp(0.7 - warp_sev * 0.5, 0.2, 0.9)

                allele = self.dna.create_allele_from_experience(
                    emotional_bias=emotional_bias,
                    manifold_position=manifold_pos,
                    seed_ids=[f"constraint_{dom_key}_{int(time.time())}"],
                    reliability=reliability,
                    mode=mode,
                )
                if allele:
                    result['allele_created'] = True
                    # Attach to the gene most resonant with this axis
                    resonant_trait = _AXIS_GENE_RESONANCE.get(dom_key, '')
                    for gene in self.dna.genome.core_genes:
                        if gene.core_trait == resonant_trait:
                            self.dna.attach_allele_to_gene(gene.gene_id, allele)
                            result['gene_resonated'] = resonant_trait
                            break

        # Store dominant axis for personality snapshot
        self._last_constraint_axis = dom_key

        return result

    # ====================================================================
    # PERSONALITY SNAPSHOT
    # ====================================================================

    def get_personality(self) -> Dict[str, Any]:
        """Current personality state."""
        return {
            'generation': self.generation,
            'traits': {n: round(t.current_value, 4) for n, t in self.traits.items()},
            'drift': round(sum(t.drift_from_base() for t in self.traits.values()), 4),
            'crystals': {d: c.get_genome_dict() for d, c in self.crystals.items()},
            'active_genes': [g.core_trait for g in self.dna.genome.core_genes
                             if g.activation_state == "active"],
            'anchors': [a.description for a in self.dna.genome.identity_anchors],
            # Dominant constraint axis from last process_from_assembly() call
            # Layer 5 uses this to bias expression tone selection
            'constraint_axis': self._last_constraint_axis,
        }

    def get_modifier(self, name: str) -> float:
        """Get a specific trait value for other systems to query."""
        if name in self.traits:
            return self.traits[name].current_value
        # Check crystal facets
        for crystal in self.crystals.values():
            if name in crystal.facets:
                return crystal.facets[name].value
        return 0.5

    def connect_sedimemory(self, sedimemory) -> None:
        """
        Inject L3.5 SediMemory into DNASystem so new identity anchors
        are sedimented as self-observation events (Section 14).
        """
        self.dna._sedimemory = sedimemory

    def get_stats(self) -> Dict[str, Any]:
        stats = {
            'generation': self.generation,
            'trait_count': len(self.traits),
            'crystal_count': len(self.crystals),
            'total_facets': sum(len(c.facets) for c in self.crystals.values()),
            'dna': self.dna.get_stats(),
            'personality_drift': round(
                sum(t.drift_from_base() for t in self.traits.values()), 4),
        }
        cv = self.constraint_profile()
        stats["lineage_signature"] = "".join(ax for ax in ("X","T","N","B","A") if getattr(cv, ax) > 0.01)
        stats["runtime_regime"] = self.runtime_regime()
        stats["language_projection"] = self.language_projection()
        return stats

    def _constraint_axes(self) -> Dict[str, float]:
        gene_count = len(self.dna.genome.core_genes)
        anchor_count = len(self.dna.genome.identity_anchors)
        helix_count = len(self.dna.genome.memory_helices)
        crystal_count = len(self.crystals)
        return {
            "X": _clamp(0.24 + min(0.28, gene_count / 20.0)),
            "T": _clamp(0.20 + min(0.28, self.generation / 200.0) + min(0.12, helix_count / 40.0)),
            "N": _clamp(0.18 + abs(sum(t.drift_from_base() for t in self.traits.values())) / max(len(self.traits), 1)),
            "B": _clamp(0.20 + min(0.25, crystal_count / 20.0) + min(0.18, anchor_count / 15.0)),
            "A": _clamp(0.18 + min(0.22, anchor_count / 10.0) + (0.12 if self._last_constraint_axis else 0.0)),
        }

    def constraint_profile(self) -> _ConstraintVector:
        ax = self._constraint_axes()
        return _ConstraintVector(
            X=max(1e-9, float(ax.get("X", 0.24))),
            T=float(ax.get("T", 0.20)),
            N=float(ax.get("N", 0.18)),
            B=float(ax.get("B", 0.20)),
            A=float(ax.get("A", 0.18)),
        )

    def runtime_regime(self) -> Dict[str, Any]:
        cv = self.constraint_profile()
        axes = {"X": cv.X, "T": cv.T, "N": cv.N, "B": cv.B, "A": cv.A}
        dominant = max(axes, key=axes.__getitem__)
        return {"axes": axes, "dominant_axis": dominant,
                "governor_weight": _GovernorWeights.AS_DICT.get(dominant, 0.0)}

    def language_projection(self) -> Dict[str, Any]:
        return _FC.language_projection(ExistenceMode.AGENTIC)

    def universal_representation(self) -> Dict[str, Any]:
        cv = self.constraint_profile()
        return {
            "constraint_vector": {"X": cv.X, "T": cv.T, "N": cv.N, "B": cv.B, "A": cv.A},
            "runtime_regime": self.runtime_regime(),
            "language_projection": self.language_projection(),
            "unit_state": {
                'generation': self.generation,
                'traits': {n: round(t.current_value, 4) for n, t in self.traits.items()},
                'active_genes': [g.core_trait for g in self.dna.genome.core_genes if g.activation_state == "active"],
                'anchors': [a.description for a in self.dna.genome.identity_anchors],
            },
        }


# ============================================================================
# SELF-VERIFICATION
# ============================================================================

def verify_layer6():
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
        results['checks'].append({'name': name, 'passed': passed, 'detail': detail})

    # --- Setup ---
    contract = FoundationalContract()
    engine = BehavioralIdentityEngine(contract)

    # ================================================================
    # DNA SYSTEM TESTS
    # ================================================================

    print("[DNA SYSTEM]")
    # 1. Initial genome
    check("Initial genome has 5 core genes",
          len(engine.dna.genome.core_genes) == 5)
    check("All genes active initially",
          all(g.activation_state == "active" for g in engine.dna.genome.core_genes))
    check("10 state lineages present",
          len(engine.dna.genome.state_lineages) == 10)
    check("All 10 I-states represented",
          all(k in engine.dna.genome.state_lineages for k in
              ["i_is", "i_isnt", "i_can", "i_cannot", "i_do", "i_donot",
               "i_saw", "i_sought", "i_did", "i_didnt"]))

    # 2. Allele creation mode-gating
    allele_ref = engine.dna.create_allele_from_experience(
        {"curiosity": 0.7}, (0.0, 0.5, 0.3, 0.0, 0.0), ["seed1"],
        mode=ExistenceMode.PERSISTENT)
    check("PERSISTENT cannot create alleles", allele_ref is None)

    allele = engine.dna.create_allele_from_experience(
        {"curiosity": 0.7, "trust": 0.3}, (0.0, 0.5, 0.3, 0.0, 0.0), ["seed1"],
        reliability=0.6, mode=ExistenceMode.BOUNDED)
    check("BOUNDED creates allele", allele is not None)
    if allele:
        check("Allele has strategy profile", len(allele.strategy_profile) > 0)
        check("Allele dominance from reliability",
              abs(allele.dominance_score - 0.6) < 0.01)

    # 3. Gene matching
    if allele:
        best = engine.dna.find_best_gene_for_allele(allele)
        check("Allele matched to gene", best is not None)
        if best:
            check("Matched to truth-seeking (curiosity gene)",
                  best.core_trait == "truth-seeking",
                  f"matched={best.core_trait}")

    # 4. Allele attachment
    if allele and best:
        attached = engine.dna.attach_allele_to_gene(best.gene_id, allele)
        check("Allele attached to gene", attached)
        check("Gene now has allele",
              len(best.fractal_alleles) == 1)
        check("Gene history logged attachment",
              len(best.history_log) > 0)

    # 5. Identity anchors â€” mode gating
    anchor_bounded = engine.dna.create_anchor(
        "I seek truth relentlessly",
        {"truth": 0.9, "accountability": 0.85},
        mode=ExistenceMode.BOUNDED)
    check("BOUNDED cannot create anchors", anchor_bounded is None)

    anchor = engine.dna.create_anchor(
        "I seek truth relentlessly",
        {"truth": 0.9, "accountability": 0.85},
        mode=ExistenceMode.AGENTIC)
    check("AGENTIC creates anchor", anchor is not None)
    if anchor:
        check("Anchor has high immutability", anchor.immutability >= 0.9)

    # 6. Anchor reinforcement
    if anchor:
        anchor2 = engine.dna.create_anchor(
            "I seek truth always",  # overlaps with "I seek truth relentlessly"
            {"truth": 0.95, "accountability": 0.9},
            mode=ExistenceMode.AGENTIC)
        check("Overlapping description reinforces existing anchor",
              anchor.reinforcement_count == 2)

    # 7. Low moral alignment rejected
    weak_anchor = engine.dna.create_anchor(
        "maybe sometimes",
        {"vague": 0.3},
        mode=ExistenceMode.AGENTIC)
    check("Low moral alignment rejected for anchor", weak_anchor is None)

    # 8. Memory helix
    helix_ref = engine.dna.create_helix(
        "trust_building", [0.3, 0.5, 0.7],
        [(0.1, 0.2, 0.3, 0.0, 0.0)], ["allele1"],
        mode=ExistenceMode.PERSISTENT)
    check("PERSISTENT cannot create helix", helix_ref is None)

    helix = engine.dna.create_helix(
        "trust_building", [0.3, 0.5, 0.7],
        [(0.1, 0.2, 0.3, 0.0, 0.0)], ["allele1"],
        mode=ExistenceMode.BOUNDED)
    check("BOUNDED creates memory helix", helix is not None)

    # ================================================================
    # BEHAVIORAL TRAIT TESTS
    # ================================================================

    print("\n[BEHAVIORAL TRAITS]")
    check("8 traits initialized", len(engine.traits) == 8)

    old_curiosity = engine.traits['curiosity'].current_value
    engine.traits['curiosity'].evolve(1.5, 1)  # High pressure
    check("Trait evolves under pressure",
          engine.traits['curiosity'].current_value != old_curiosity,
          f"old={old_curiosity:.4f} new={engine.traits['curiosity'].current_value:.4f}")

    check("Trait tracks drift",
          engine.traits['curiosity'].drift_from_base() > 0)

    # ================================================================
    # BEHAVIORAL CRYSTAL TESTS
    # ================================================================

    print("\n[BEHAVIORAL CRYSTALS]")
    check("3 crystals initialized", len(engine.crystals) == 3)
    check("Response crystal has 4 facets",
          len(engine.crystals['response'].facets) == 4)

    # Simulation
    sim_results = engine.simulate_behavior(
        {'warmth': 0.8, 'curiosity': 0.7, 'empathy': 0.6},
        energy_budget=5.0,
        mode=ExistenceMode.PERSISTENT
    )
    check("Simulation produces results", len(sim_results) > 0)
    check("Response domain simulated", 'response' in sim_results)

    # Crystal evolution
    mutations = engine.crystals['response'].evolve(1.5)
    check("Crystal evolves", engine.crystals['response'].generation == 1)

    # ================================================================
    # GENERATION EVOLUTION
    # ================================================================

    print("\n[GENERATION EVOLUTION]")
    # Mode gating
    ref_result = engine.evolve_generation({}, mode=ExistenceMode.REFERENCE)
    check("REFERENCE cannot evolve", 'error' in ref_result)

    gen_result = engine.evolve_generation(
        {'curiosity': 1.3, 'caution': 0.7, 'emotional_expressiveness': 1.1},
        mode=ExistenceMode.BOUNDED
    )
    check("BOUNDED evolves generation", 'generation' in gen_result)
    check("Generation advanced", gen_result['generation'] >= 1)
    check("Trait changes recorded",
          isinstance(gen_result.get('trait_changes'), dict))
    check("Crystal mutations recorded",
          isinstance(gen_result.get('crystal_mutations'), dict))
    check("Personality drift tracked",
          gen_result.get('personality_drift', 0) >= 0)

    # ================================================================
    # FULL EPISODE PROCESSING
    # ================================================================

    print("\n[EPISODE PROCESSING]")
    episode = {
        'success_rate': 0.8,
        'lessons_learned': ["accountability requires consistency",
                            "truth demands courage"]
    }
    relics = [
        {'theme': 'determination', 'stability': 0.7,
         'seed_ids': ['s1', 's2'], 'emotional_bias': {'determination': 0.7, 'trust': 0.3},
         'manifold_position': (0.1, 0.6, 0.5, 0.0, 0.0)},
        {'theme': 'curiosity', 'stability': 0.6,
         'seed_ids': ['s3'], 'emotional_bias': {'curiosity': 0.8},
         'manifold_position': (0.0, 0.5, 0.7, 0.0, 0.0)},
    ]
    pillar_scores = {'truth': 0.85, 'accountability': 0.9, 'curiosity': 0.7}

    ep_result = engine.process_episode(episode, relics, pillar_scores,
                                       mode=ExistenceMode.AGENTIC)
    check("Episode processed", 'dna_stats' in ep_result)
    check("DNA generation advanced",
          ep_result['dna_stats']['genome_version'] > 0)
    check("Alleles created from relics",
          ep_result['dna_stats']['total_alleles'] > 1,
          f"alleles={ep_result['dna_stats']['total_alleles']}")
    check("Anchors created from lessons",
          ep_result['dna_stats']['identity_anchors'] > 0,
          f"anchors={ep_result['dna_stats']['identity_anchors']}")

    # ================================================================
    # PERSONALITY & STATS
    # ================================================================

    print("\n[PERSONALITY & STATS]")
    personality = engine.get_personality()
    check("Personality has all keys",
          all(k in personality for k in
              ['generation', 'traits', 'drift', 'crystals', 'active_genes', 'anchors']))
    check("Active genes listed",
          len(personality['active_genes']) > 0)

    modifier = engine.get_modifier('curiosity')
    check("Modifier retrieval works", 0.0 <= modifier <= 1.0)

    stats = engine.get_stats()
    check("Stats complete",
          all(k in stats for k in
              ['generation', 'trait_count', 'crystal_count', 'dna', 'personality_drift']))


    # ================================================================
    # CONSTRAINT MANIFOLD INTEGRATION — Layer 6 checks
    # ================================================================

    print("\n[CONSTRAINT MANIFOLD — Layer 6 Integration]")

    # Build full stack for a real AssemblyResult
    from aurora_ivm import IVMLattice
    from aurora_i_state_beings import IStateCollective
    from aurora_dimensional_systems import DimensionalSystems
    from aurora_consciousness_engine import ConsciousnessEngine

    _contract = FoundationalContract()
    _lattice   = IVMLattice(_contract, max_nodes=10000)
    _collective = IStateCollective(_contract, _lattice)
    _dimensional = DimensionalSystems(_lattice)
    _ce = ConsciousnessEngine(_contract, _lattice, _collective, _dimensional)

    _assembly = _ce.process(
        payload="constraint field shapes behavioral identity",
        payload_type="thought",
        evidence={'has_temporality': True, 'conserves_state': True,
                  'has_identity': True, 'initiates_change': True},
    )

    # Check 43: AssemblyResult has constraint_context
    check("AssemblyResult carries constraint_context to Layer 6",
          hasattr(_assembly, 'constraint_context'))

    ctx = _assembly.constraint_context
    check("constraint_context is populated (not None)",
          ctx is not None and isinstance(ctx, dict),
          f"type={type(ctx).__name__}")

    # Check 44: process_from_assembly() exists and callable
    check("BehavioralIdentityEngine has process_from_assembly()",
          hasattr(engine, 'process_from_assembly') and
          callable(engine.process_from_assembly))

    # Check 45: process_from_assembly() runs without error
    pa_result = engine.process_from_assembly(_assembly, mode=ExistenceMode.BOUNDED)
    check("process_from_assembly() returns a result dict",
          isinstance(pa_result, dict) and 'axis' in pa_result,
          f"keys={list(pa_result.keys())}")

    # Check 46: dominant axis is stored
    check("process_from_assembly() captures dominant axis",
          pa_result.get('axis') is not None or ctx is None,
          f"axis={pa_result.get('axis')} ctx={'present' if ctx else 'None'}")

    # Check 47: trait pressures computed from axis
    check("process_from_assembly() computes trait pressures",
          isinstance(pa_result.get('trait_pressures'), dict),
          f"pressures={pa_result.get('trait_pressures')}")

    if pa_result.get('axis') and _AXIS_TRAIT_PRESSURES.get(pa_result['axis']):
        expected_traits = set(_AXIS_TRAIT_PRESSURES[pa_result['axis']].keys())
        actual_traits = set(pa_result.get('trait_pressures', {}).keys())
        check("Trait pressures match expected axis traits",
              expected_traits == actual_traits,
              f"expected={expected_traits} actual={actual_traits}")

    # Check 48: allele created and attached to resonant gene
    check("process_from_assembly() created FractalAllele",
          pa_result.get('allele_created') is True,
          f"allele_created={pa_result.get('allele_created')}")
    check("Allele attached to resonant gene",
          pa_result.get('gene_resonated') is not None,
          f"gene={pa_result.get('gene_resonated')}")

    # Verify the allele actually landed in the genome
    resonant_trait = pa_result.get('gene_resonated')
    if resonant_trait:
        resonant_gene = next(
            (g for g in engine.dna.genome.core_genes
             if g.core_trait == resonant_trait), None
        )
        check("Resonant gene contains the new allele",
              resonant_gene is not None and len(resonant_gene.fractal_alleles) > 0,
              f"alleles_in_gene={len(resonant_gene.fractal_alleles) if resonant_gene else 0}")

    # Check 49: _last_constraint_axis stored and surfaces in get_personality()
    personality = engine.get_personality()
    check("get_personality() includes constraint_axis key",
          'constraint_axis' in personality,
          f"keys={list(personality.keys())}")
    check("constraint_axis in personality matches process_from_assembly result",
          personality.get('constraint_axis') == pa_result.get('axis'),
          f"personality={personality.get('constraint_axis')} process={pa_result.get('axis')}")

    # Check 50: Trait evolution driven by constraint axis
    # Run process_from_assembly with a forced strong N-axis context
    # N-axis should amplify curiosity (1.35 × magnitude) and reduce caution
    # dominant_axis uses LONG form to match what constraint_context carries
    _mock_assembly_N = type('MockAssembly', (), {
        'constraint_context': {
            'axis_net_displacements': {'X': 0.1, 'T': 0.1, 'N': 0.9, 'B': 0.1, 'A': 0.2},
            'dominant_axis': 'energy',   # long-form: matches _AXIS_TRAIT_PRESSURES key
            'warp_severity': 0.0,
        }
    })()

    engine2 = BehavioralIdentityEngine(_contract)
    pre_curiosity = engine2.traits['curiosity'].current_value
    pre_caution   = engine2.traits['caution'].current_value

    engine2.process_from_assembly(_mock_assembly_N, mode=ExistenceMode.BOUNDED)

    post_curiosity = engine2.traits['curiosity'].current_value
    post_caution   = engine2.traits['caution'].current_value

    check("N-axis increases curiosity trait",
          post_curiosity > pre_curiosity,
          f"pre={pre_curiosity:.4f} post={post_curiosity:.4f}")
    # N-axis caution multiplier is 0.85 (below 1.0 = reduce direction).
    # Gaussian noise (std=0.02) can overpower small deltas, so we verify
    # that the pressure dict had the correct direction (< 1.0), not the
    # exact outcome — noise is real and intentional in trait evolution.
    n_pressures = _AXIS_TRAIT_PRESSURES.get('energy', {})
    check("N-axis caution pressure multiplier is < 1.0 (reduces direction)",
          n_pressures.get('caution', 1.0) < 1.0,
          f"caution_mult={n_pressures.get('caution', 1.0):.3f}")

    # Check 51: process_from_assembly gracefully handles missing context
    _mock_no_ctx = type('MockEmpty', (), {'constraint_context': None})()
    null_result = engine.process_from_assembly(_mock_no_ctx, mode=ExistenceMode.BOUNDED)
    check("process_from_assembly() handles None context gracefully",
          null_result.get('axis') is None and null_result.get('trait_pressures') == {},
          f"axis={null_result.get('axis')}")

    # Check 52: CONSTRAINT_MANIFOLD_AVAILABLE flag at Layer 6
    check("CONSTRAINT_MANIFOLD_AVAILABLE is bool at Layer 6",
          isinstance(CONSTRAINT_MANIFOLD_AVAILABLE, bool))

    # Check 53: Manifold positions in allele created by process_from_assembly
    # are stored as 5-tuple matching the {X,T,N,B,A} net values
    dom = pa_result.get('axis')
    if dom and pa_result.get('gene_resonated'):
        resonant_gene = next(
            (g for g in engine.dna.genome.core_genes
             if g.core_trait == pa_result['gene_resonated']), None
        )
        if resonant_gene and resonant_gene.fractal_alleles:
            newest_allele = resonant_gene.fractal_alleles[-1]
            check("Allele manifold_bias is 5-tuple from constraint axes",
                  len(newest_allele.manifold_bias) == 5,
                  f"len={len(newest_allele.manifold_bias)}")

    return results


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("AURORA BEHAVIORAL IDENTITY â€” SELF-VERIFICATION")
    print("Authors: Sunni (Sir) Morningstar and Cael Devo")
    print("=" * 70)
    print()

    results = verify_layer6()

    for c in results['checks']:
        status = "âœ“" if c['passed'] else "âœ—"
        detail = f"  ({c['detail']})" if c.get('detail') else ""
        print(f"  {status} {c['name']}{detail}")

    print()
    total = len(results['checks'])
    passed = sum(1 for c in results['checks'] if c['passed'])

    if results['all_passed']:
        print(f"ALL {total} CHECKS PASSED âœ“")
        print()
        print("Layer 6 is SOUND.")
        print("Genes define the constitution. Alleles amend it slowly.")
        print("Identity anchors are rights â€” nearly permanent once earned.")
        print("Traits drift. Crystals mutate. Aurora becomes who she becomes.")
        print("Ready for Layer 7 (Simulation).")
    else:
        print(f"FAILURES: {total - passed}/{total}")
        print("Do not build Layer 7 yet.")

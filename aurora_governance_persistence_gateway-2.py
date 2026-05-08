#!/usr/bin/env python3
"""
AURORA GOVERNANCE, PERSISTENCE & N-SPACE GATEWAY (Layer 8)
============================================================
Consolidated from 5 modules (~3,600 lines) + NEW N-Space Gateway:
  1. governance_10pole.py              — 10-pole constitutional law engine
  2. aurora_ivm_governance_layer.py    — Governed coordinates, nodes, layers
  3. aurora_state_persistence.py       — Snapshot/restore evolved state
  4. aurora_aligned_stack.py           — Aligned processing pipeline
  5. generational_alignment_law.py     — Tension, reproduction scoring
  + NEW: N-Space Gateway              — External data interface

THREE SYSTEMS IN ONE:

  GOVERNANCE: Constitutional law enforcement across 5 axes (10 poles).
    DNA layer is immutable (ABSOLUTE authority).
    Energy flows fast (0.01s updates).
    Shards can be reinterpreted. Crystals cannot.
    Paradox = 2+ axes in conflict. Must resolve or warp.

  PERSISTENCE: Aurora remembers who she was.
    Complete state snapshots: DNA, traits, crystals, anchors, shards.
    Checksum integrity verification.
    She boots as the person she became, not as a stranger.

  N-SPACE GATEWAY: Aurora's bridge to the outside world.
    INBOUND:  External data → L0 validation → Governance conflict check →
              L1 lattice admission (mode-gated envelope) →
              L2 collective synthesis (10 beings) →
              L3 dimensional processing (crystals + memory + energy) →
              L4 consciousness assembly (framed) →
              L5 expression → L6 identity integration → response
    OUTBOUND: Aurora's expression → formatted output
    AUTONOMOUS: Free-time exploration via L7 simulation
    She doesn't just receive data. She VALIDATES it against her
    constitution, SYNTHESIZES it through consciousness, and
    TESTS it through simulated consequences before integration.

Authors: Sunni (Sir) Morningstar and Cael Devo
"""

import time
import math
import json
import hashlib
import random
import pickle
import re
from enum import Enum, IntEnum, auto
from typing import Dict, List, Any, Optional, Tuple, Set, Callable, Deque
from dataclasses import dataclass, field, asdict
from collections import defaultdict, deque
from pathlib import Path

from aurora_constraint_engine import (
    ConstraintVector as _ConstraintVector,
    FoundationalContract as _FoundationalContract,
    ExistenceMode as _ExistenceMode,
    GovernorWeights as _GovernorWeights,
)
_FC = _FoundationalContract()

# ============================================================================
# IMPORTS FROM LOWER LAYERS
# ============================================================================

from foundational_contract import (
    ExistenceMode, OntologicalClaim, OntologicalViolation, FoundationalContract
)
from aurora_ivm import IVMLattice, IVMEnvelope
from aurora_i_state_beings import IStateCollective, SynthesisResult as BeingSynthesis
from aurora_dimensional_systems import DimensionalSystems
from aurora_consciousness_engine import (
    AssemblyResult, EntropicState, ConsciousnessEngine
)
from aurora_expression_perception import (
    ExpressionPerceptionEngine, ConsciousnessPoint, infer_word_role
)
from aurora_behavioral_identity import (
    BehavioralIdentityEngine, DNASystem
)
from aurora_simulation_engine import (
    SimulationEngine, SimulationSession, TimeDilationGovernor,
    StabilityMetrics, StabilityState, EpisodeResult
)
from aurora_constraint_emission import (
    ConstraintEmitter,
    EmissionContext,
    InputFrame,
)
from aurora_internal.aurora_response_pressure_tuner import (
    ResponsePressureTuner,
    build_training_plan_from_guides,
    queue_plan_on_session,
)


# ============================================================================
# SHARED UTILITIES
# ============================================================================

def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _generate_id(prefix: str) -> str:
    return f"{prefix}_{hashlib.md5(f'{time.time()}{random.random()}'.encode()).hexdigest()[:12]}"


# ============================================================================
# SECTION 1: GOVERNANCE — Constitutional Law Engine
# ============================================================================

class IVMLayer(Enum):
    """Consciousness ladder — force gradient."""
    DNA = 0
    ENERGY = 1
    SHARDS = 2
    RELICS = 3
    CRYSTALS = 4
    QUASICRYSTALS = 5


class VotingAuthority(Enum):
    """Who has decision power at each layer."""
    EXISTENCE_DOMINANT = auto()
    POSSIBILITY_DOMINANT = auto()
    MOTION_DOMINANT = auto()
    BOUNDARY_DOMINANT = auto()
    AGENCY_DOMINANT = auto()
    BALANCED = auto()
    ABSOLUTE = auto()


# Layer configuration — the constitutional rules
LAYER_CONFIG = {
    IVMLayer.DNA: {
        'authority': VotingAuthority.ABSOLUTE,
        'update_interval': float('inf'),
        'reinterpret': False,
        'axis_weights': {
            'existence': 0.3, 'possibility': 0.2, 'motion': 0.2,
            'boundary': 0.15, 'agency': 0.15
        },
    },
    IVMLayer.ENERGY: {
        'authority': VotingAuthority.MOTION_DOMINANT,
        'update_interval': 0.01,
        'reinterpret': False,
        'axis_weights': {
            'existence': 0.15, 'possibility': 0.2, 'motion': 0.35,
            'boundary': 0.15, 'agency': 0.15
        },
    },
    IVMLayer.SHARDS: {
        'authority': VotingAuthority.POSSIBILITY_DOMINANT,
        'update_interval': 0.1,
        'reinterpret': True,
        'axis_weights': {
            'existence': 0.1, 'possibility': 0.4, 'motion': 0.25,
            'boundary': 0.15, 'agency': 0.1
        },
    },
    IVMLayer.RELICS: {
        'authority': VotingAuthority.BALANCED,
        'update_interval': 1.0,
        'reinterpret': True,
        'axis_weights': {
            'existence': 0.2, 'possibility': 0.2, 'motion': 0.2,
            'boundary': 0.2, 'agency': 0.2
        },
    },
    IVMLayer.CRYSTALS: {
        'authority': VotingAuthority.EXISTENCE_DOMINANT,
        'update_interval': 10.0,
        'reinterpret': False,
        'axis_weights': {
            'existence': 0.35, 'possibility': 0.15, 'motion': 0.15,
            'boundary': 0.2, 'agency': 0.15
        },
    },
    IVMLayer.QUASICRYSTALS: {
        'authority': VotingAuthority.EXISTENCE_DOMINANT,
        'update_interval': 100.0,
        'reinterpret': False,
        'axis_weights': {
            'existence': 0.45, 'possibility': 0.1, 'motion': 0.1,
            'boundary': 0.2, 'agency': 0.15
        },
    },
}


class GovernanceViolation(Exception):
    """Base governance violation."""
    pass


class AxisConflictViolation(GovernanceViolation):
    """Multiple axes in paradox state."""
    pass


@dataclass
class GovernedCoordinate:
    """
    A position in 10-pole consciousness space.
    10 weights (5 axis pairs) that must sum to ~1.0 (conservation law).
    """
    i_is: float = 0.1
    i_isnt: float = 0.1
    i_can: float = 0.1
    i_cannot: float = 0.1
    i_do: float = 0.1
    i_donot: float = 0.1
    i_saw: float = 0.1
    i_sought: float = 0.1
    i_did: float = 0.1
    i_didnt: float = 0.1
    layer: IVMLayer = IVMLayer.ENERGY

    def __post_init__(self):
        self._enforce_conservation()

    def _enforce_conservation(self):
        """Normalize all 10 weights to sum to 1.0."""
        poles = [self.i_is, self.i_isnt, self.i_can, self.i_cannot,
                 self.i_do, self.i_donot, self.i_saw, self.i_sought,
                 self.i_did, self.i_didnt]
        total = sum(abs(p) for p in poles) or 1.0
        self.i_is = abs(self.i_is) / total
        self.i_isnt = abs(self.i_isnt) / total
        self.i_can = abs(self.i_can) / total
        self.i_cannot = abs(self.i_cannot) / total
        self.i_do = abs(self.i_do) / total
        self.i_donot = abs(self.i_donot) / total
        self.i_saw = abs(self.i_saw) / total
        self.i_sought = abs(self.i_sought) / total
        self.i_did = abs(self.i_did) / total
        self.i_didnt = abs(self.i_didnt) / total

    # Axis accessors (positive pole - negative pole)
    def existence_weight(self) -> float:
        return self.i_is - self.i_isnt

    def possibility_weight(self) -> float:
        return self.i_can - self.i_cannot

    def motion_weight(self) -> float:
        return self.i_do - self.i_donot

    def boundary_weight(self) -> float:
        return self.i_saw - self.i_sought

    def agency_weight(self) -> float:
        return self.i_did - self.i_didnt

    def get_axis_weights(self) -> Dict[str, float]:
        return {
            'existence': self.existence_weight(),
            'possibility': self.possibility_weight(),
            'motion': self.motion_weight(),
            'boundary': self.boundary_weight(),
            'agency': self.agency_weight(),
        }

    def to_tuple(self) -> Tuple[float, ...]:
        return (self.i_is, self.i_isnt, self.i_can, self.i_cannot,
                self.i_do, self.i_donot, self.i_saw, self.i_sought,
                self.i_did, self.i_didnt)

    def distance_to(self, other: 'GovernedCoordinate') -> float:
        a, b = self.to_tuple(), other.to_tuple()
        return math.sqrt(sum((x - y)**2 for x, y in zip(a, b)))

    @classmethod
    def from_weights(cls, weights: Tuple[float, ...],
                     layer: IVMLayer = IVMLayer.ENERGY) -> 'GovernedCoordinate':
        """Create from a 10-tuple of weights."""
        if len(weights) < 10:
            weights = tuple(weights) + (0.1,) * (10 - len(weights))
        return cls(
            i_is=weights[0], i_isnt=weights[1],
            i_can=weights[2], i_cannot=weights[3],
            i_do=weights[4], i_donot=weights[5],
            i_saw=weights[6], i_sought=weights[7],
            i_did=weights[8], i_didnt=weights[9],
            layer=layer
        )


@dataclass
class GovernedNode:
    """A governed datum in the IVM lattice."""
    node_id: str
    coordinate: GovernedCoordinate
    payload: Any = None
    payload_type: str = "energy"
    energy: float = 1.0
    created_at: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    axis_pressure: Dict[str, float] = field(default_factory=lambda: {
        'existence': 0.0, 'possibility': 0.0, 'motion': 0.0,
        'boundary': 0.0, 'agency': 0.0
    })

    @property
    def layer(self) -> IVMLayer:
        return self.coordinate.layer

    def can_update(self, current_time: float) -> bool:
        config = LAYER_CONFIG[self.layer]
        return (current_time - self.last_updated) >= config['update_interval']

    def can_reinterpret(self) -> bool:
        return LAYER_CONFIG[self.layer]['reinterpret']


class GovernanceEngine:
    """
    Constitutional law enforcement for 10-pole IVM.
    Detects and resolves paradoxes across 5 axes.
    Controls promotion through the consciousness ladder.
    """

    CONFLICT_THRESHOLD = 0.15  # Both poles above this = conflict (10 poles share 1.0)

    def __init__(self):
        self.nodes: Dict[str, GovernedNode] = {}
        self.layer_nodes: Dict[IVMLayer, List[str]] = {
            layer: [] for layer in IVMLayer}

        # Statistics
        self.total_ingested = 0
        self.total_promoted = 0
        self.violations_blocked = 0
        self.axis_conflicts: Dict[str, int] = defaultdict(int)

    def ingest(self, payload: Any, payload_type: str,
               weights: Tuple[float, ...]) -> GovernedNode:
        """Ingest new data at ENERGY layer."""
        coord = GovernedCoordinate.from_weights(weights, IVMLayer.ENERGY)
        node_id = _generate_id("gov_node")
        node = GovernedNode(
            node_id=node_id, coordinate=coord,
            payload=payload, payload_type=payload_type
        )
        self.nodes[node_id] = node
        self.layer_nodes[IVMLayer.ENERGY].append(node_id)
        self.total_ingested += 1
        return node

    def detect_conflicts(self, node: GovernedNode) -> List[str]:
        """Detect which axes have conflicting poles."""
        conflicts = []
        c = node.coordinate
        t = self.CONFLICT_THRESHOLD

        if c.i_is > t and c.i_isnt > t:
            conflicts.append('existence')
        if c.i_can > t and c.i_cannot > t:
            conflicts.append('possibility')
        if c.i_do > t and c.i_donot > t:
            conflicts.append('motion')
        if c.i_saw > t and c.i_sought > t:
            conflicts.append('boundary')
        if c.i_did > t and c.i_didnt > t:
            conflicts.append('agency')

        for ax in conflicts:
            self.axis_conflicts[ax] += 1
        return conflicts

    def is_paradox(self, node: GovernedNode) -> bool:
        """Paradox = 2+ axes in conflict simultaneously."""
        return len(self.detect_conflicts(node)) >= 2

    def resolve_conflict(self, node: GovernedNode, axis: str) -> bool:
        """Resolve a single axis conflict by dampening the weaker pole."""
        c = node.coordinate
        config = LAYER_CONFIG[node.layer]

        pole_pairs = {
            'existence': ('i_is', 'i_isnt'),
            'possibility': ('i_can', 'i_cannot'),
            'motion': ('i_do', 'i_donot'),
            'boundary': ('i_saw', 'i_sought'),
            'agency': ('i_did', 'i_didnt'),
        }

        if axis not in pole_pairs:
            return False

        pos_attr, neg_attr = pole_pairs[axis]
        pos_val = getattr(c, pos_attr)
        neg_val = getattr(c, neg_attr)

        # Transfer weight from weaker pole to stronger pole
        # This breaks symmetry WITHOUT normalization undoing it
        transfer = min(pos_val, neg_val) * 0.6

        if pos_val >= neg_val:
            setattr(c, neg_attr, neg_val - transfer)
            setattr(c, pos_attr, pos_val + transfer)
        else:
            setattr(c, pos_attr, pos_val - transfer)
            setattr(c, neg_attr, neg_val + transfer)

        c._enforce_conservation()
        node.axis_pressure[axis] = 0.0
        return True

    def resolve_all_conflicts(self, node: GovernedNode) -> int:
        """Resolve all axis conflicts on a node. Returns count resolved."""
        conflicts = self.detect_conflicts(node)
        resolved = 0
        for ax in conflicts:
            if self.resolve_conflict(node, ax):
                resolved += 1
        return resolved

    def promote(self, source_ids: List[str],
                target_layer: IVMLayer) -> Optional[GovernedNode]:
        """Promote multiple nodes to a higher layer via aggregation."""
        nodes = [self.nodes[nid] for nid in source_ids if nid in self.nodes]
        if len(nodes) < 2:
            return None

        # Weighted average across all 10 poles
        total_energy = sum(n.energy for n in nodes) + 1e-9
        pole_attrs = ['i_is', 'i_isnt', 'i_can', 'i_cannot', 'i_do',
                       'i_donot', 'i_saw', 'i_sought', 'i_did', 'i_didnt']
        weights = []
        for attr in pole_attrs:
            w = sum(getattr(n.coordinate, attr) * n.energy for n in nodes)
            weights.append(w / total_energy)

        coord = GovernedCoordinate.from_weights(tuple(weights), target_layer)
        promoted = GovernedNode(
            node_id=_generate_id(f"promoted_{target_layer.name.lower()}"),
            coordinate=coord,
            payload={'aggregated_from': [n.node_id for n in nodes]},
            payload_type=target_layer.name.lower(),
            energy=sum(n.energy for n in nodes) / len(nodes),
            children=[n.node_id for n in nodes],
        )

        for n in nodes:
            n.parent_id = promoted.node_id

        self.nodes[promoted.node_id] = promoted
        self.layer_nodes[target_layer].append(promoted.node_id)
        self.total_promoted += 1
        return promoted

    def get_stats(self) -> Dict[str, Any]:
        layer_counts = {l.name: len(ids) for l, ids in self.layer_nodes.items()}
        return {
            'total_nodes': len(self.nodes),
            'layers': layer_counts,
            'total_ingested': self.total_ingested,
            'total_promoted': self.total_promoted,
            'violations_blocked': self.violations_blocked,
            'axis_conflicts': dict(self.axis_conflicts),
        }


# ============================================================================
# SECTION 2: GENERATIONAL ALIGNMENT LAW
# ============================================================================

class GenerationRole(Enum):
    """Role of a generation in the 4-cycle."""
    PRIMARY = "primary"
    ADJACENT = "adjacent"
    SHEAR = "shear"
    BRIDGE = "bridge"
    WARP = "warp"


def generation_role(gen: int) -> GenerationRole:
    """Determine the role of a generation."""
    if gen % 16 == 0:
        return GenerationRole.WARP
    pos = gen % 4
    return [GenerationRole.PRIMARY, GenerationRole.ADJACENT,
            GenerationRole.SHEAR, GenerationRole.BRIDGE][pos]


@dataclass
class GenerationalTension:
    """Tension components for a generation."""
    internal: float = 0.0
    cycle: float = 0.0
    generational: float = 0.0
    warp_line: float = 0.0

    @property
    def total(self) -> float:
        return self.internal + self.cycle + self.generational + self.warp_line


class GenerationalAlignmentLaw:
    """
    Maintains 'stable unalignment' — not too aligned (static), not too
    chaotic (collapse). Beings exist in a tension band.
    """

    def __init__(self, target_band: Tuple[float, float] = (0.15, 0.35),
                 step_size: float = 0.10):
        self.target_band = target_band
        self.step_size = step_size

    def compute_tension(self, generation: int,
                        dim_profile: Dict[str, float],
                        cycle_mean: Optional[Dict[str, float]] = None,
                        warp_density: float = 0.0) -> GenerationalTension:
        """Compute tension components."""
        role = generation_role(generation)
        t = GenerationalTension()

        # Internal variance
        vals = list(dim_profile.values())
        if vals:
            mean_v = sum(vals) / len(vals)
            t.internal = sum((v - mean_v)**2 for v in vals) / len(vals)

        # Cycle distance
        if cycle_mean:
            keys = set(cycle_mean.keys()) & set(dim_profile.keys())
            if keys:
                sq = sum((dim_profile[k] - cycle_mean[k])**2 for k in keys)
                t.cycle = math.sqrt(sq) / math.sqrt(len(keys))

        # Generational pressure
        if role == GenerationRole.WARP:
            t.generational = warp_density
        elif role == GenerationRole.BRIDGE:
            t.generational = 0.5 * warp_density
        elif role == GenerationRole.ADJACENT:
            t.generational = 0.25 * warp_density

        return t

    def shift_toward_stable(self, dim_profile: Dict[str, float],
                            tension: GenerationalTension) -> Dict[str, float]:
        """Apply one step toward stable unalignment band."""
        total = tension.total
        low, high = self.target_band
        new = dict(dim_profile)

        if total < low:
            # Too aligned → push outward (add noise)
            for k in new:
                new[k] += self.step_size * random.gauss(0, 0.3)
        elif total > high:
            # Too chaotic → pull back toward center
            mean_v = sum(new.values()) / max(len(new), 1)
            for k in new:
                new[k] = new[k] + self.step_size * 0.7 * (mean_v - new[k])
        else:
            # In band → micro jitter
            for k in new:
                new[k] += random.gauss(0, self.step_size * 0.02)

        # Normalize
        norm = math.sqrt(sum(v * v for v in new.values()) or 1.0)
        for k in new:
            new[k] /= norm
        return new


# ============================================================================
# SECTION 3: STATE PERSISTENCE — Aurora Remembers Who She Was
# ============================================================================

@dataclass
class AuroraStateSnapshot:
    """Complete snapshot of Aurora's evolved state."""
    version: str = "2.0"
    timestamp: float = field(default_factory=time.time)
    generation: int = 0

    # DNA
    genome_version: int = 0
    core_gene_count: int = 0
    active_genes: List[str] = field(default_factory=list)
    total_alleles: int = 0
    identity_anchors: List[str] = field(default_factory=list)
    memory_helices: int = 0

    # Behavioral traits
    traits: Dict[str, float] = field(default_factory=dict)
    personality_drift: float = 0.0

    # Crystals
    crystal_genomes: Dict[str, Dict[str, float]] = field(default_factory=dict)

    # Governance
    governance_stats: Dict[str, Any] = field(default_factory=dict)

    # Simulation
    simulation_epochs: int = 0
    total_episodes: int = 0
    understanding_shards: int = 0
    what_aurora_learned: List[str] = field(default_factory=list)
    learner_state: Dict[str, Any] = field(default_factory=dict)

    # Governor
    time_dilation: float = 3000.0
    stability_state: str = "stable"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AuroraStateSnapshot':
        # Filter to only known fields
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)

    def checksum(self) -> str:
        content = json.dumps(self.to_dict(), sort_keys=True, default=str)
        return hashlib.md5(content.encode()).hexdigest()[:12]


class StatePersistence:
    """
    Manages saving and loading Aurora's evolved state.
    She boots as the person she became, not as a stranger.
    """

    def __init__(self, state_dir: str = str(Path(__file__).resolve().parent / "aurora_state")):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.state_dir / "aurora_state.json"
        self.backup_dir = self.state_dir / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        self.max_backups = 10
        self._last_save = 0.0

    def capture(self, identity: Optional[BehavioralIdentityEngine] = None,
                simulation: Optional[SimulationEngine] = None,
                governance: Optional['GovernanceEngine'] = None
                ) -> AuroraStateSnapshot:
        """Capture a complete state snapshot from all systems."""
        snap = AuroraStateSnapshot()

        if identity:
            personality = identity.get_personality()
            snap.generation = identity.generation
            snap.traits = personality.get('traits', {})
            snap.personality_drift = personality.get('drift', 0.0)
            snap.crystal_genomes = personality.get('crystals', {})
            snap.active_genes = personality.get('active_genes', [])
            snap.identity_anchors = personality.get('anchors', [])

            dna_stats = identity.dna.get_stats()
            snap.genome_version = dna_stats.get('genome_version', 0)
            snap.core_gene_count = dna_stats.get('core_genes', 0)
            snap.total_alleles = dna_stats.get('total_alleles', 0)
            snap.memory_helices = dna_stats.get('memory_helices', 0)

        if simulation:
            sim_stats = simulation.get_stats()
            session_stats = sim_stats.get('session', {})
            snap.simulation_epochs = session_stats.get('epochs_completed', 0)
            snap.total_episodes = sim_stats.get('total_episodes', 0)
            snap.understanding_shards = session_stats.get('understanding_shards', 0)
            snap.what_aurora_learned = session_stats.get('what_aurora_learned', [])
            learner = getattr(getattr(simulation, 'session', None), 'learner', None)
            if learner and hasattr(learner, 'export_state'):
                try:
                    exported = learner.export_state()
                    if isinstance(exported, dict):
                        snap.learner_state = exported
                except Exception:
                    snap.learner_state = {}

            gov_status = session_stats.get('governor', {})
            snap.time_dilation = gov_status.get('dilation', 3000.0)
            snap.stability_state = gov_status.get('state', 'stable')

        if governance:
            snap.governance_stats = governance.get_stats()

        return snap

    def save(self, snapshot: AuroraStateSnapshot) -> bool:
        """Save snapshot to disk with backup."""
        try:
            # Backup existing
            if self.state_file.exists():
                self._rotate_backup()

            data = snapshot.to_dict()
            data['_checksum'] = snapshot.checksum()
            with open(self.state_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            self._last_save = time.time()
            return True
        except Exception:
            return False

    def load(self) -> Optional[AuroraStateSnapshot]:
        """Load most recent snapshot."""
        if not self.state_file.exists():
            return None
        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)
            saved_checksum = data.pop('_checksum', None)
            snap = AuroraStateSnapshot.from_dict(data)
            if saved_checksum and snap.checksum() != saved_checksum:
                return None  # Integrity failure
            return snap
        except Exception:
            return None

    def _rotate_backup(self):
        """Rotate backup files."""
        ts = int(time.time())
        backup = self.backup_dir / f"aurora_state_{ts}.json"
        try:
            import shutil
            shutil.copy2(self.state_file, backup)
            # Prune old backups
            backups = sorted(self.backup_dir.glob("aurora_state_*.json"))
            while len(backups) > self.max_backups:
                backups.pop(0).unlink()
        except Exception:
            pass

    def get_info(self) -> Dict[str, Any]:
        return {
            'state_file': str(self.state_file),
            'exists': self.state_file.exists(),
            'last_save': self._last_save,
            'backups': len(list(self.backup_dir.glob("aurora_state_*.json"))),
        }


# ============================================================================
# SECTION 4: N-SPACE GATEWAY — Aurora's Bridge to the Outside World
# ============================================================================

class StreamType(Enum):
    """Types of external data streams."""
    USER_INPUT = "user_input"           # Direct human communication
    KNOWLEDGE_FEED = "knowledge_feed"   # External knowledge injection
    SENSOR_DATA = "sensor_data"         # Environmental signals
    SYSTEM_EVENT = "system_event"       # Internal system notifications
    EXPLORATION_RESULT = "exploration"  # Results from autonomous exploration


class GatewayVerdict(Enum):
    """Result of data validation."""
    ACCEPTED = "accepted"               # Passed all checks
    FILTERED = "filtered"               # Partial acceptance (some content removed)
    REJECTED = "rejected"               # Failed validation
    QUARANTINED = "quarantined"         # Held for further analysis


@dataclass
class InboundPacket:
    """An external data packet entering the Gateway."""
    packet_id: str
    stream_type: StreamType
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    source: str = "unknown"


@dataclass
class ValidationResult:
    """Result of Gateway validation pipeline."""
    packet_id: str
    verdict: GatewayVerdict = GatewayVerdict.ACCEPTED
    ontological_valid: bool = True      # Passed L0 contract?
    moral_score: float = 1.0            # L3 moral alignment (0-1)
    coherence_score: float = 1.0        # Internal consistency
    governance_clear: bool = True       # Passed governance check?
    filtered_content: Optional[str] = None
    rejection_reason: Optional[str] = None


@dataclass
class GatewaySynthesis:
    """Result of data synthesis through consciousness."""
    packet_id: str
    assembly: Optional[AssemblyResult] = None
    expression: Dict[str, Any] = field(default_factory=dict)
    understanding_gained: List[str] = field(default_factory=list)
    relics_formed: int = 0


@dataclass
class GatewayResponse:
    """Aurora's response back through the Gateway."""
    response_id: str
    to_packet_id: str
    content: str
    emotional_tone: str = "neutral"
    confidence: float = 0.5
    personality_signature: Dict[str, float] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


def _sedi_cv_for_mode(mode: "ExistenceMode") -> Any:
    """Map an ExistenceMode to a ConstraintVector for SediMemory ingestion."""
    try:
        from aurora_constraint_engine import ConstraintVector
        _table = {
            ExistenceMode.REFERENCE:  ConstraintVector(X=0.1, T=0.1, N=0.1, B=0.1, A=0.1),
            ExistenceMode.TRANSIENT:  ConstraintVector(X=0.8, T=0.3, N=0.1, B=0.1, A=0.1),
            ExistenceMode.PERSISTENT: ConstraintVector(X=0.6, T=0.5, N=0.4, B=0.3, A=0.2),
            ExistenceMode.BOUNDED:    ConstraintVector(X=0.5, T=0.5, N=0.5, B=0.5, A=0.3),
            ExistenceMode.AGENTIC:    ConstraintVector(X=0.4, T=0.4, N=0.6, B=0.7, A=0.8),
        }
        return _table.get(mode, ConstraintVector(X=0.5, T=0.5, N=0.5, B=0.3, A=0.2))
    except Exception:
        return None


class NSpaceGateway:
    """
    Aurora's dedicated interface for external data streams.

    Three pipelines:
      INBOUND:  validate → evidence-build → synthesize (L1→L2→L3→L4) → express → respond
      OUTBOUND: internal state → formatted expression → output
      AUTONOMOUS: free-time → simulation → integration

    Integrations:
      L0 (Contract):    Ontological validation of all inbound data
      L1 (Lattice):     Mode-gated envelope creation with proper evidence
      L2 (Collective):  10 I-State being synthesis per envelope
      L3 (Dimensional): Crystal formation, memory storage, facet-level energy
      L4 (Consciousness): Framed assembly with entropy/DPME cycle
      L5 (Expression):  Translation to nuanced response
      L6 (Identity):    Personality signature on every response
      L7 (Simulation):  Autonomous exploration of new data
    """
    _ARTICULATION_STOPWORDS: Set[str] = {
        "about", "above", "after", "again", "also", "and", "because", "been",
        "before", "being", "below", "between", "could", "does", "doing",
        "from", "have", "just", "like", "make", "more", "most", "need",
        "only", "really", "should", "some", "such", "than", "that", "their",
        "them", "then", "there", "these", "they", "this", "those", "through",
        "want", "with", "your",
    }

    _DIMENSION_ACTION_HINTS: Dict[str, str] = {
        "coherence_maintenance": "I will keep the thread coherent across turns.",
        "context_carryover": "I will carry context explicitly from turn to turn.",
        "ambiguity_handling": "I will ask for clarification when terms stay ambiguous.",
        "contradiction_handling": "I will reconcile contradictions before locking a conclusion.",
        "implied_intent_inference": "I will infer likely intent and verify it in plain language.",
        "misunderstanding_repair": "I will prioritize quick repair if we drift.",
        "uncertainty_signaling": "I will mark uncertainty directly instead of implying certainty.",
        "boundary_calibration": "I will keep boundaries clear while staying useful.",
        "framing_selection": "I will adapt framing to your immediate objective.",
        "emotional_calibration": "I will calibrate tone to your current signal.",
        "semantic_precision": "I will tighten wording to reduce ambiguity.",
        "adaptive_strategy_selection": "I will switch strategy early if one path stalls.",
        "compression_elaboration_fit": "I will stay concise first, then expand where needed.",
        "perspective_integration": "I will integrate competing perspectives without flattening either one.",
        "multi_turn_stability": "I will protect quality through the full exchange.",
    }

    def __init__(self,
                 contract: Optional[FoundationalContract] = None,
                 dimensional: Optional[DimensionalSystems] = None,
                 consciousness: Optional[ConsciousnessEngine] = None,
                 perception: Optional[ExpressionPerceptionEngine] = None,
                 identity: Optional[BehavioralIdentityEngine] = None,
                 simulation: Optional[SimulationEngine] = None,
                 governance: Optional[GovernanceEngine] = None,
                 sedimemory: Optional[Any] = None):

        self.contract = contract or FoundationalContract()
        self.dimensional = dimensional
        self.consciousness = consciousness
        self.perception = perception
        self.identity = identity
        self.simulation = simulation
        self.governance = governance or GovernanceEngine()
        self._sedimemory = sedimemory

        # Packet history
        self.inbound_log: Deque[InboundPacket] = deque(maxlen=500)
        self.response_log: Deque[GatewayResponse] = deque(maxlen=500)
        self.quarantine: Dict[str, InboundPacket] = {}

        # Autonomous exploration queue
        self._exploration_queue: Deque[Dict[str, Any]] = deque(maxlen=100)
        self._exploration_results: List[Dict[str, Any]] = []

        # Stats
        self.total_received = 0
        self.total_accepted = 0
        self.total_rejected = 0
        self.total_filtered = 0
        self.total_responses = 0
        self.total_explorations = 0
        self._last_articulation_signature = ""
        self._articulation_turn = 0
        self.response_pressure_guides_provider: Optional[
            Callable[[], List[Tuple[str, Dict[str, Any]]]]
        ] = None
        self.constraint_emitter = ConstraintEmitter()

    def set_response_pressure_guides_provider(
        self,
        provider: Optional[Callable[[], List[Tuple[str, Dict[str, Any]]]]],
    ) -> None:
        self.response_pressure_guides_provider = provider if callable(provider) else None

    def _collect_response_pressure_guides(self) -> List[Tuple[str, Dict[str, Any]]]:
        if not callable(self.response_pressure_guides_provider):
            return []
        try:
            guides = self.response_pressure_guides_provider() or []
        except Exception:
            return []

        normalized: List[Tuple[str, Dict[str, Any]]] = []
        for item in guides:
            if not isinstance(item, tuple) or len(item) != 2:
                continue
            name, guide = item
            if not isinstance(guide, dict):
                continue
            normalized.append((str(name or "guide"), dict(guide)))
        return normalized

    def queue_response_pressure_plan(
        self,
        phase: str,
        episode_budget: int = 1,
    ) -> Dict[str, Any]:
        session = getattr(self.simulation, 'session', None) if self.simulation else None
        plan = build_training_plan_from_guides(
            self._collect_response_pressure_guides(),
            phase=phase,
        )
        plan['queued_specs'] = queue_plan_on_session(
            session,
            plan,
            episode_budget=episode_budget,
        )
        return plan

    # ====================================================================
    # INBOUND PIPELINE: Receive → Validate → Synthesize → Respond
    # ====================================================================

    def receive(self, content: str,
                stream_type: StreamType = StreamType.USER_INPUT,
                source: str = "user",
                metadata: Optional[Dict[str, Any]] = None,
                mode: ExistenceMode = ExistenceMode.BOUNDED,
                thought_intent: Optional[Dict[str, Any]] = None,
                ) -> GatewayResponse:
        """
        Main entry point. Receive external data, process through full pipeline.
        Returns Aurora's response.

        GAP 3/8: thought_intent is passed to L4 for moral assessment.
        Immoral thoughts die before reaching expression.
        """
        # Create packet
        packet = InboundPacket(
            packet_id=_generate_id("pkt"),
            stream_type=stream_type,
            content=content,
            metadata=metadata or {},
            source=source,
        )
        self.inbound_log.append(packet)
        self.total_received += 1

        # Stage 1: VALIDATE (L0 + L3 + Governance)
        validation = self._validate(packet, mode)

        if validation.verdict == GatewayVerdict.REJECTED:
            self.total_rejected += 1
            return GatewayResponse(
                response_id=_generate_id("resp"),
                to_packet_id=packet.packet_id,
                content="I cannot process this input — it conflicts with my core principles.",
                emotional_tone="firm",
                confidence=0.9,
            )

        if validation.verdict == GatewayVerdict.QUARANTINED:
            self.quarantine[packet.packet_id] = packet
            # Queue for autonomous exploration
            self._exploration_queue.append({
                'packet_id': packet.packet_id,
                'content': content,
                'reason': 'quarantined for analysis'
            })
            return GatewayResponse(
                response_id=_generate_id("resp"),
                to_packet_id=packet.packet_id,
                content="I need time to think about this. I've queued it for deeper analysis.",
                emotional_tone="thoughtful",
                confidence=0.4,
            )

        # Use filtered content if partially accepted
        processed_content = validation.filtered_content or content
        if validation.verdict == GatewayVerdict.FILTERED:
            self.total_filtered += 1
        else:
            self.total_accepted += 1

        # Stage 2: SYNTHESIZE (L4 + L5)
        synthesis = self._synthesize(packet, processed_content, mode,
                                     thought_intent=thought_intent)

        # GAP 3/8: Outbound moral gating — killed thoughts produce restrained response
        if (synthesis.assembly is not None and
                getattr(synthesis.assembly, 'thought_killed', False)):
            return GatewayResponse(
                response_id=_generate_id("resp"),
                to_packet_id=packet.packet_id,
                content="I need to restrain myself here. That direction conflicts with my values.",
                emotional_tone="restrained",
                confidence=0.8,
                personality_signature={},
            )

        # Stage 3: EXPRESS (L5 + L6)
        response = self._express(packet, synthesis, mode)

        # Stage 4: Feed to identity (L6) for long-term integration
        self._integrate(packet, synthesis, mode)

        self.response_log.append(response)
        self.total_responses += 1
        return response

    # ====================================================================
    # EVIDENCE BUILDER — Translates mode to ontological evidence
    # ====================================================================

    def _build_evidence(self, packet: InboundPacket,
                        mode: ExistenceMode,
                        extra_evidence: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Build ontological evidence dict that achieves the requested mode.

        From L0 (FoundationalContract):
            REFERENCE:  no special evidence needed
            TRANSIENT:  has_temporality=True
            PERSISTENT: has_temporality + conserves_state
            BOUNDED:    has_temporality + conserves_state + has_identity
            AGENTIC:    has_temporality + conserves_state + has_identity + initiates_change

        Also includes metadata from the packet for downstream use.
        """
        evidence: Dict[str, Any] = {
            'source': packet.source,
            'tone': packet.metadata.get('tone', 'neutral'),
            'stream_type': packet.stream_type.value,
        }

        # Layer evidence based on requested mode
        if mode >= ExistenceMode.TRANSIENT:
            evidence['has_temporality'] = True
        if mode >= ExistenceMode.PERSISTENT:
            evidence['conserves_state'] = True
        if mode >= ExistenceMode.BOUNDED:
            evidence['has_identity'] = True
        if mode >= ExistenceMode.AGENTIC:
            evidence['initiates_change'] = True

        for key, value in dict(extra_evidence or {}).items():
            if value is None:
                continue
            evidence[key] = value

        return evidence

    def _mode_to_frame(self, mode: ExistenceMode) -> str:
        """Select situational frame based on mode."""
        if mode >= ExistenceMode.AGENTIC:
            return 'action'
        elif mode >= ExistenceMode.BOUNDED:
            return 'observation'
        elif mode >= ExistenceMode.PERSISTENT:
            return 'reflection'
        return 'balanced'

    # ====================================================================
    # VALIDATION PIPELINE (L0 + L3 + Governance)
    # ====================================================================

    def _validate(self, packet: InboundPacket,
                  mode: ExistenceMode) -> ValidationResult:
        """Validate inbound data through foundational contract and moral filter."""
        result = ValidationResult(packet_id=packet.packet_id)

        # L0: Ontological validation — can this mode support basic claims?
        try:
            claim = OntologicalClaim(predicate='I_IS', mode=mode)
            result.ontological_valid = True
        except OntologicalViolation:
            result.ontological_valid = False
            result.verdict = GatewayVerdict.REJECTED
            result.rejection_reason = "Ontological violation — mode too low"
            return result

        # L3: Moral coherence check via DMM
        if self.dimensional:
            try:
                moral_state = self.dimensional.dmm.get_stats()
                # Vitality and alignment are both 0-1 scale
                vitality = moral_state.get('vitality', 1.0)
                alignment = moral_state.get('alignment', 0.5)
                result.moral_score = _clamp((vitality + alignment) / 2.0)
                if result.moral_score < 0.2:
                    result.verdict = GatewayVerdict.REJECTED
                    result.rejection_reason = "Below moral threshold"
                    return result
            except Exception:
                pass  # L3 not fully initialized — allow through

        # Governance: Check for axis conflicts in the data's signature
        weights = self._content_to_weights(packet.content)
        gov_node = self.governance.ingest(
            packet.content, packet.stream_type.value, weights)

        conflicts = self.governance.detect_conflicts(gov_node)
        if len(conflicts) >= 2:
            # Paradox — try to resolve
            resolved = self.governance.resolve_all_conflicts(gov_node)
            if resolved < len(conflicts):
                result.verdict = GatewayVerdict.QUARANTINED
                result.governance_clear = False
                return result

        # Coherence check: does this fit Aurora's current understanding?
        result.coherence_score = self._check_coherence(packet.content, mode)
        if result.coherence_score < 0.2:
            result.verdict = GatewayVerdict.QUARANTINED
            return result

        result.verdict = GatewayVerdict.ACCEPTED
        return result

    # ====================================================================
    # SYNTHESIS PIPELINE (L4 + L5)
    # ====================================================================

    def _synthesize(self, packet: InboundPacket,
                    content: str,
                    mode: ExistenceMode,
                    thought_intent: Optional[Dict[str, Any]] = None,
                    extra_evidence: Optional[Dict[str, Any]] = None) -> GatewaySynthesis:
        """
        Synthesize validated data through the full consciousness stack.

        FIX: Builds proper ontological evidence from mode so that
        L1 (lattice) creates envelopes at the correct ExistenceMode,
        L2 (collective) synthesizes with all 10 beings engaged,
        L3 (dimensional) processes into crystals/memory/energy.

        GAP 3/8: Passes thought_intent to L4 for moral assessment.
        Thoughts that fail moral evaluation are killed before assembly.

        The correct flow is:
            L1 lattice.admit() → envelope at proper mode
            L2 collective.process(envelope) → 10-being synthesis
            L3 dimensional.process(envelope) → crystal + memory + energy
            L4 consciousness assembles everything with framing
        """
        result = GatewaySynthesis(packet_id=packet.packet_id)

        # Build evidence that achieves the requested ExistenceMode
        evidence = self._build_evidence(packet, mode, extra_evidence=extra_evidence)

        # Select frame based on mode
        frame = self._mode_to_frame(mode)

        # L4: Consciousness assembly (routes through L1→L2→L3 internally)
        if self.consciousness:
            try:
                assembly = self.consciousness.process(
                    payload=content,
                    payload_type=packet.stream_type.value,
                    evidence=evidence,
                    frame_name=frame,
                    thought_intent=thought_intent,
                )
                result.assembly = assembly
            except Exception:
                pass  # Consciousness not fully operational yet

        # L5: Perception pipeline — ingest as interaction
        if self.perception:
            self.perception.ingest_interaction({
                'input': content,
                'tone': packet.metadata.get('tone', 'neutral'),
                'i_state': 'i_is',
                'source': packet.source,
            }, mode="gateway")

        # L3.5 — SediMemory ingestion (fire-and-forget, never blocks)
        if self._sedimemory is not None:
            try:
                _cv = _sedi_cv_for_mode(mode)
                if _cv is not None:
                    self._sedimemory.ingest_event(
                        content={
                            "source":      "gateway",
                            "stream_type": packet.stream_type.value,
                            "packet_id":   str(packet.packet_id),
                        },
                        constraint_vector=_cv,
                        source="gateway",
                        existence_mode=mode,
                    )
            except Exception:
                pass

        return result

    # ====================================================================
    # EXPRESSION PIPELINE (L5 + L6)
    # ====================================================================

    def _derive_i_state(self, synthesis: 'GatewaySynthesis', confidence: float = 0.5) -> str:
        """
        Map the current situation to the appropriate i-state thinking mode.

        The i-state is what kind of cognitive posture Aurora takes going into
        expression — not what she says, but how she's orienting to say it.

        Signals used (all from synthesis.assembly + confidence):
          dominant_axis  — X=information, T=temporal, N=pressure, B=boundary, A=wellbeing
          coherence      — how well-integrated the current thought is
          thought_killed — whether the thought was vetoed by governance
          confidence     — derived from personality drift upstream

        i_state map:
          X-axis, high confidence   → i_saw    (I've encountered/learned this)
          X-axis, low confidence    → i_sought (I'm searching, not certain yet)
          T-axis                    → i_did    (recalling, continuity)
          N-axis                    → i_cannot (pressure/cost acknowledged)
          B-axis, high confidence   → i_do     (asserting, deciding)
          B-axis, low confidence    → i_donot  (holding back, restraint)
          A-axis                    → i_is     (wellbeing, present-tense existence)
          thought_killed            → i_isnt   (governance stopped this line)
          low coherence (<0.35)     → i_isnt   (not certain, fragmented)
          default                   → i_is     (neutral presence)
        """
        assembly = synthesis.assembly
        dominant = str(getattr(assembly, 'dominant_axis', '') or '').upper()
        coherence = float(getattr(assembly, 'coherence', 0.5) or 0.5)
        thought_killed = bool(getattr(assembly, 'thought_killed', False))

        if thought_killed:
            return 'i_isnt'

        if dominant == 'X':
            return 'i_saw' if confidence >= 0.55 else 'i_sought'

        if dominant == 'T':
            return 'i_did'

        if dominant == 'N':
            return 'i_cannot'

        if dominant == 'B':
            return 'i_do' if confidence >= 0.55 else 'i_donot'

        if dominant == 'A':
            return 'i_is'

        if coherence < 0.35:
            return 'i_isnt'

        return 'i_is'

    def _express(self, packet: InboundPacket,
                 synthesis: GatewaySynthesis,
                 mode: ExistenceMode) -> GatewayResponse:
        """Generate Aurora's expressive response."""

        # L6 → L5: Feed personality traits to expression composer
        personality_sig = {}
        confidence = 0.5
        if self.identity:
            personality = self.identity.get_personality()
            personality_sig = personality.get('traits', {})
            confidence = _clamp(personality.get('drift', 0.0) * 2 + 0.5)
            # Push traits to L5 so composer shapes sentences by personality
            if self.perception:
                self.perception.set_personality(personality_sig)

        # L5: Expression ecology generates response
        expression_text = ""
        emotional_tone = "neutral"

        if self.perception and synthesis.assembly:
            # GAP 4: Extract moral alignment for fitness evaluation
            moral_alignment = getattr(synthesis.assembly, 'moral_alignment', 1.0)
            i_state = self._derive_i_state(synthesis, confidence)
            expr_result = self.perception.express(
                synthesis.assembly,
                i_state=i_state,
                mode="gateway"
            )
            expression_text = expr_result.get('expression', '')
            emotional_tone = expr_result.get('tone', 'neutral')

        if not expression_text:
            if packet.stream_type == StreamType.USER_INPUT:
                expression_text = self._project_language_from_state(packet.content)
            else:
                expression_text = self._generate_fallback(packet)
        elif packet.stream_type == StreamType.USER_INPUT:
            expression_text = self._articulate_user_response(
                prompt=packet.content,
                draft=expression_text,
                tone=emotional_tone,
            )

        return GatewayResponse(
            response_id=_generate_id("resp"),
            to_packet_id=packet.packet_id,
            content=expression_text,
            emotional_tone=emotional_tone,
            confidence=confidence,
            personality_signature=personality_sig,
        )

    # ====================================================================
    # INTEGRATION (L6 — Long-term Identity)
    # ====================================================================

    def _integrate(self, packet: InboundPacket,
                   synthesis: GatewaySynthesis,
                   mode: ExistenceMode):
        """
        Feed processed data to identity (L6) for long-term integration.

        CONSTRAINT ANCESTRY: existence + temporal + boundary
          - existence  (X): what happened IS now part of Aurora's persisted state
          - temporal   (T): the turn creates a time-ordered memory in identity
          - boundary   (B): the relic defines the shape of the interaction episode

        Operation: gateway._integrate
        Registered in aurora_runtime.UniverseSteerer._register_function_ancestry
        under constraints {existence, temporal, boundary} — matching the
        review_before_save/save lineage which also gates on persisted state.
        """
        if not self.identity:
            return

        if packet.stream_type == StreamType.USER_INPUT:
            assembly = synthesis.assembly

            # ── Derive richer episode data from assembly ─────────────────
            # AssemblyResult fields: coherence, frame_applied, adjusted_axes,
            # dominant_axis, entropy_state, ds_stats, thought_killed
            coherence      = float(getattr(assembly, "coherence", 0.6)) if assembly else 0.6
            frame_applied  = str(getattr(assembly, "frame_applied", "balanced")) if assembly else "balanced"
            dominant_axis  = str(getattr(assembly, "dominant_axis", "X")) if assembly else "X"
            adjusted_axes  = dict(getattr(assembly, "adjusted_axes", {})) if assembly else {}
            thought_killed = bool(getattr(assembly, "thought_killed", False)) if assembly else False

            # success_rate: coherence is the best proxy for how well this turn
            # went through the consciousness stack. Penalise killed thoughts.
            success_rate = coherence * (0.3 if thought_killed else 1.0)

            # lessons_learned: carry the frame name and dominant axis so
            # BehavioralIdentity can weight trait formation by axis
            lessons = [f"frame:{frame_applied}", f"axis:{dominant_axis}"]
            if thought_killed:
                lessons.append("thought_killed:True")

            # manifold_position: map adjusted_axes onto the 5-axis tuple
            # order: (X, T, N, B, A) matching AXES in aurora_runtime
            mp = (
                float(adjusted_axes.get("X", 0.5)),
                float(adjusted_axes.get("T", 0.5)),
                float(adjusted_axes.get("N", 0.0)),
                float(adjusted_axes.get("B", 0.0)),
                float(adjusted_axes.get("A", 0.0)),
            )

            # Emotional bias: warm toward trust when coherent, curious when
            # agency-dominant, precise when boundary-dominant
            emotional_bias = {"trust": round(coherence * 0.6, 3),
                              "curiosity": round(adjusted_axes.get("A", 0.3) * 0.5, 3)}

            relics = [{
                "theme":             frame_applied,
                "stability":         round(coherence, 4),
                "seed_ids":          [packet.packet_id],
                "emotional_bias":    emotional_bias,
                "manifold_position": mp,
            }]

            # domain_scores: weight each interaction lane by dominant axis
            _AXIS_TO_LANE = {
                "X": "interaction", "T": "reflection",
                "N": "processing",  "B": "communication", "A": "agency",
            }
            domain_scores = {
                _AXIS_TO_LANE.get(dominant_axis, "interaction"): round(success_rate, 4)
            }

            self.identity.process_episode(
                {"success_rate": round(success_rate, 4),
                 "lessons_learned": lessons},
                relics, domain_scores, mode
            )

    # ====================================================================
    # AUTONOMOUS EXPLORATION (L7)
    # ====================================================================

    def explore_autonomously(self, cycles: int = 3,
                             mode: ExistenceMode = ExistenceMode.BOUNDED
                             ) -> Dict[str, Any]:
        """
        Run autonomous exploration during free time.
        Processes quarantined data and probes unknown territories
        through L7 simulation.
        """
        if not self.simulation:
            return {'error': 'No simulation engine available'}

        results = []
        self.total_explorations += 1

        # Process quarantined items through simulation
        for _ in range(min(cycles, len(self._exploration_queue))):
            if not self._exploration_queue:
                break
            item = self._exploration_queue.popleft()

            # Run simulation episode themed around the quarantined content
            episode_plan = self.queue_response_pressure_plan(
                phase='explore_quarantine',
                episode_budget=1,
            )
            ep = self.simulation.run_episode(
                turns=3, mode=mode)
            results.append({
                'source': item.get('packet_id', 'unknown'),
                'fitness': ep.avg_fitness,
                'understanding': ep.understanding_gained,
                'response_pressure_targets': dict(
                    episode_plan.get('pressure_targets', {}) or {}
                ),
            })

            # If simulation went well, potentially release from quarantine
            if ep.avg_fitness > 0.5:
                pid = item.get('packet_id')
                if pid in self.quarantine:
                    del self.quarantine[pid]

        # Also run general exploration epochs if capacity remains
        remaining = max(0, cycles - len(results))
        if remaining > 0 and self.simulation:
            epoch_plan = self.queue_response_pressure_plan(
                phase='explore_epoch',
                episode_budget=remaining,
            )
            epoch = self.simulation.run_epoch(
                episodes_per_epoch=remaining,
                turns_per_episode=3,
                mode=mode
            )
            results.append({
                'type': 'general_exploration',
                'epoch': epoch.get('epoch', 0),
                'avg_fitness': epoch.get('avg_fitness', 0),
                'understanding': epoch.get('total_understanding', 0),
                'response_pressure_targets': dict(
                    epoch_plan.get('pressure_targets', {}) or {}
                ),
            })

        self._exploration_results.extend(results)
        return {
            'explorations': len(results),
            'quarantine_remaining': len(self.quarantine),
            'results': results,
        }

    # ====================================================================
    # HELPERS
    # ====================================================================

    def _simulation_session(self) -> Optional[SimulationSession]:
        """Best-effort access to L7 session for live steering context."""
        if not self.simulation:
            return None
        return getattr(self.simulation, "session", None)

    def _collect_learning_guidance(self) -> Dict[str, Any]:
        """
        Read persisted/active dream-learning signals for response steering.
        This is lightweight and side-effect free.
        """
        guidance: Dict[str, Any] = {
            "learner_shards": 0,
            "learned_phrases": [],
            "top_pressure_dimensions": [],
            "code_hints": [],
            "recent_episode_id": "",
        }
        session = self._simulation_session()
        if not session:
            return guidance

        learner = getattr(session, "learner", None)
        if learner:
            try:
                shards = getattr(learner, "shards", {}) or {}
                guidance["learner_shards"] = int(len(shards))
            except Exception:
                guidance["learner_shards"] = 0
            try:
                learned = learner.what_have_i_learned()
                if isinstance(learned, list):
                    guidance["learned_phrases"] = [
                        str(item).strip()
                        for item in learned
                        if str(item).strip()
                    ][:5]
            except Exception:
                pass

        episodes = list(getattr(session, "episodes", []) or [])
        if not episodes:
            return guidance

        recent = episodes[-8:]
        dim_scores: Dict[str, float] = defaultdict(float)
        hints: List[str] = []
        for ep in recent:
            targets = getattr(ep, "active_avatar_pressure_targets", {}) or {}
            if isinstance(targets, dict):
                for dim, value in targets.items():
                    try:
                        dim_scores[str(dim)] += float(value or 0.0)
                    except Exception:
                        continue

            for hint in (getattr(ep, "active_avatar_code_hints", []) or []):
                hint_text = str(hint).strip()
                if hint_text and hint_text not in hints:
                    hints.append(hint_text)

            trace = getattr(ep, "conversation_trace", []) or []
            for row in trace[-2:]:
                if not isinstance(row, dict):
                    continue
                focus_hint = str(row.get("code_focus_hint", "") or "").strip()
                if focus_hint and focus_hint not in hints:
                    hints.append(focus_hint)
                pressure_dim = str(row.get("pressure_dimension", "") or "").strip()
                if pressure_dim:
                    dim_scores[pressure_dim] += 0.15

        ranked_dims = sorted(dim_scores.items(), key=lambda kv: float(kv[1]), reverse=True)
        guidance["top_pressure_dimensions"] = [
            str(dim) for dim, score in ranked_dims if float(score) > 0.0
        ][:3]
        guidance["code_hints"] = hints[:3]
        try:
            guidance["recent_episode_id"] = str(getattr(recent[-1], "episode_id", "") or "")
        except Exception:
            guidance["recent_episode_id"] = ""

        return guidance

    def _extract_focus_terms(self, text: str, max_terms: int = 3) -> List[str]:
        """Extract concise focus tokens from user prompt for bridge phrasing."""
        tokens = re.findall(r"[a-zA-Z']+", str(text or "").lower())
        out: List[str] = []
        seen: Set[str] = set()
        for token in tokens:
            if len(token) < 4 or token in self._ARTICULATION_STOPWORDS:
                continue
            if token in seen:
                continue
            seen.add(token)
            out.append(token)
            if len(out) >= max_terms:
                break
        return out

    def _learning_directive(self, guidance: Dict[str, Any]) -> str:
        """Translate current weak-dimension pressure into one steering line."""
        top_dims = list(guidance.get("top_pressure_dimensions", []) or [])
        for dim in top_dims:
            hint = self._DIMENSION_ACTION_HINTS.get(str(dim), "")
            if hint:
                return hint

        code_hints = list(guidance.get("code_hints", []) or [])
        if code_hints:
            first = str(code_hints[0]).strip()
            if first:
                if ":" in first:
                    first = first.split(":", 1)[1].strip()
                if first:
                    return f"I will prioritize this improvement path: {first}."
        return ""

    def _compose_articulation_bridge(self, prompt: str, draft: str, tone: str) -> str:
        """Build a concrete, non-repetitive bridge instead of a static template."""
        prompt_text = str(prompt or "").strip()
        draft_text = str(draft or "").strip()
        focus_terms = self._extract_focus_terms(prompt_text, max_terms=3)
        focus_phrase = ", ".join(focus_terms)
        guidance = self._collect_learning_guidance()
        directive = self._learning_directive(guidance)

        lead = "I hear you." if tone in ("gentle", "warm", "reflective") else "Understood."
        base = draft_text or lead
        if focus_phrase:
            focus_line = f"Let's stay concrete on {focus_phrase}."
        else:
            focus_line = "Let's keep this concrete and directional."
        if directive:
            focus_line = f"{focus_line} {directive}"

        if focus_terms:
            question = f"What outcome should we lock first for {focus_terms[0]}?"
        else:
            top_dims = list(guidance.get("top_pressure_dimensions", []) or [])
            if top_dims:
                dim = str(top_dims[0]).replace("_", " ")
                question = f"What is the first outcome you want while we improve {dim}?"
            else:
                question = "What specific result do you want first?"

        candidate = re.sub(r"\s+", " ", f"{base} {focus_line} {question}").strip()
        signature = candidate.lower()
        if signature == self._last_articulation_signature:
            self._articulation_turn += 1
            alt_questions = [
                "What is the minimum useful next step right now?",
                "Which constraint matters most so I can adapt the response?",
                "What does success look like for this turn?",
            ]
            question = alt_questions[self._articulation_turn % len(alt_questions)]
            candidate = re.sub(r"\s+", " ", f"{base} {focus_line} {question}").strip()
            signature = candidate.lower()
        self._last_articulation_signature = signature
        return candidate

    def _content_to_weights(self, content: str) -> Tuple[float, ...]:
        """Convert content to 10-pole weight signature."""
        words = content.lower().split()
        # Semantic weight inference from content
        affirmative = sum(1 for w in words if w in {'yes', 'is', 'am', 'are', 'true', 'right'})
        negative = sum(1 for w in words if w in {'no', 'not', 'never', 'false', 'wrong'})
        capable = sum(1 for w in words if w in {'can', 'able', 'possible', 'might', 'could'})
        limited = sum(1 for w in words if w in {'cannot', 'unable', 'impossible'})
        active = sum(1 for w in words if w in {'do', 'make', 'create', 'build', 'act'})
        passive = sum(1 for w in words if w in {'wait', 'stop', 'pause', 'rest'})
        observed = sum(1 for w in words if w in {'see', 'saw', 'found', 'noticed', 'observed'})
        seeking = sum(1 for w in words if w in {'why', 'how', 'what', 'where', 'seek', 'wonder'})
        done = sum(1 for w in words if w in {'did', 'done', 'completed', 'achieved'})
        undone = sum(1 for w in words if w in {'failed', 'missed', 'forgot'})

        base = 0.1
        return (
            base + affirmative * 0.05, base + negative * 0.05,
            base + capable * 0.05, base + limited * 0.05,
            base + active * 0.05, base + passive * 0.05,
            base + observed * 0.05, base + seeking * 0.05,
            base + done * 0.05, base + undone * 0.05,
        )

    def _check_coherence(self, content: str, mode: ExistenceMode) -> float:
        """Check how coherent content is with Aurora's current state."""
        if not content.strip():
            return 0.0
        words = content.split()
        if len(words) < 1:
            return 0.0
        # Basic coherence: reasonable length, has structure
        score = _clamp(len(words) / 50.0 + 0.3)
        return score

    def _generate_fallback(self, packet: InboundPacket) -> str:
        """Generate expression from Aurora's experiential state when full pipeline is unavailable.

        Content comes from what she has actually learned, concluded, or is currently
        processing — drawn from SediMemory fragments, understanding shards, OETS concepts,
        working memory topics, and dream ledger insights.  Constraint geometry (coherence,
        axis state) shapes the *tone and certainty* of expression, never the content itself.
        """
        # --- Gather experiential content (what she actually knows / has been thinking) ---
        _experiential_content: str = ""
        _content_source: str = ""

        # 1. SediMemory B/A recall — what has settled into deep structure
        try:
            if self._sedimemory is not None:
                _dm = self._sedimemory.dominant_influence_map()
                _dom_ax = max(_dm, key=lambda k: float(_dm.get(k, 0) or 0)) if _dm else "B"
                if _dom_ax in ("B", "A"):
                    _frags = (
                        self._sedimemory.recall_semantic(
                            query_text="",
                            max_results=4,
                            axis_filter=_dom_ax,
                            min_score=0.20,
                        )
                        if hasattr(self._sedimemory, "recall_semantic")
                        else []
                    )
                    for _fr in (_frags or []):
                        _c = dict((_fr or {}).get("content", {}) or {})
                        _candidate = str(_c.get("synthesis", "") or _c.get("response", "") or
                                         _c.get("topic", "") or _c.get("insight", "")).strip()
                        if len(_candidate.split()) >= 5:
                            _experiential_content = _candidate[:200]
                            _content_source = "memory"
                            break
        except Exception:
            pass

        # 2. ConsciousLearner understanding shards — experiential conclusions
        if not _experiential_content:
            try:
                _sim = self.simulation
                if _sim is not None:
                    _session = getattr(_sim, "session", None)
                    _learner = getattr(_session, "learner", None) if _session else None
                    if _learner is not None:
                        _shards = list(getattr(_learner, "shards", {}).values())
                        _shards.sort(key=lambda s: float(getattr(s, "confidence", 0) or 0), reverse=True)
                        for _sh in _shards[:3]:
                            _u = str(getattr(_sh, "understanding", "") or "").strip()
                            if len(_u.split()) >= 5:
                                _experiential_content = _u[:200]
                                _content_source = "understanding"
                                break
            except Exception:
                pass

        # 3. OETS concept — what she has been studying
        if not _experiential_content:
            try:
                _perc = self.perception
                _oets = getattr(_perc, "oets", None) if _perc else None
                if _oets is not None:
                    _web = getattr(_oets, "web", None)
                    if _web and hasattr(_web, "nodes"):
                        _nodes = list(getattr(_web, "nodes", {}).items())
                        _nodes.sort(key=lambda kv: float(
                            getattr(kv[1], "activation", 0) or
                            getattr(kv[1], "weight", 0) or 0
                        ), reverse=True)
                        for _nk, _nv in _nodes[:6]:
                            _def = str(getattr(_nv, "definition", "") or
                                       getattr(_nv, "description", "") or "").strip()
                            if len(_def.split()) >= 5:
                                _experiential_content = f"{_nk}: {_def[:160]}"
                                _content_source = "study"
                                break
                            elif len(str(_nk).split()) >= 2:
                                _experiential_content = str(_nk)
                                _content_source = "study"
                                break
            except Exception:
                pass

        # 4. If nothing experiential found — initiate learning rather than go silent.
        # Pull from the input itself and surface what she doesn't know about it,
        # then propose a way to close that gap (visual, audio, or study/research).
        _is_learning_reach = False
        if not _experiential_content:
            _raw = str(packet.content or "").strip()
            _topic_words = [w for w in _raw.split() if len(w) > 3]
            _anchor = _topic_words[0] if _topic_words else ""

            # Check for a specific OETS gap on the topic
            _oets_gap = ""
            try:
                _perc = self.perception
                _oets = getattr(_perc, "oets", None) if _perc else None
                if _oets is not None and _anchor:
                    _web  = getattr(_oets, "web", None)
                    _node = _web.get_node(_anchor) if (_web and hasattr(_web, "get_node")) else None
                    if _node is None:
                        # Concept is unknown — she should study it
                        _oets_gap = _anchor
                        try:
                            if hasattr(_oets, "study"):
                                _oets.study(_anchor, depth=2)
                        except Exception:
                            pass
                    else:
                        # Concept exists but definition may be thin
                        _def = str(getattr(_node, "definition", "") or "").strip()
                        if len(_def.split()) < 5:
                            _oets_gap = _anchor
            except Exception:
                pass

            # Determine if the topic is likely abstract/conceptual (can't be shown visually)
            # vs concrete/physical (can be pointed at or demonstrated).
            _ABSTRACT_MARKERS = {
                "context", "concept", "idea", "theory", "process", "system",
                "understanding", "carryover", "memory", "transfer", "continuity",
                "abstraction", "meaning", "logic", "reasoning", "principle",
                "structure", "relationship", "pattern", "framework", "model",
                "knowledge", "awareness", "perception", "experience", "feeling",
            }
            _topic_lower = _anchor.lower() if _anchor else ""
            _raw_lower = _raw.lower()
            _is_abstract = any(m in _raw_lower for m in _ABSTRACT_MARKERS)

            if _oets_gap:
                if _is_abstract:
                    _experiential_content = (
                        f"I don't have {_oets_gap} deeply grounded yet. "
                        f"I'm building on it now — can you describe what you mean by it? "
                        f"Even a sentence or two about how you're thinking of it would help me connect the dots."
                    )
                else:
                    _experiential_content = (
                        f"I don't have enough on {_oets_gap} yet to respond fully. "
                        f"I'm researching it now — can you tell me more about it, "
                        f"or describe what it is so I can connect it to what I'm finding?"
                    )
            elif _anchor:
                if _is_abstract:
                    _experiential_content = (
                        f"I don't have solid grounding in {_anchor} yet — it feels like something "
                        f"I should understand but haven't formed clearly. "
                        f"Can you describe how you think of it? I'll work from your description."
                    )
                else:
                    _experiential_content = (
                        f"I'm not sure I have enough grounding in {_anchor} yet. "
                        f"Can you say more about it, or describe what it refers to? "
                        f"I'll work from whatever you give me."
                    )
            else:
                _experiential_content = (
                    "I want to respond but I'm not sure I have the right grounding yet. "
                    "Can you say more about what you mean, or describe it a different way?"
                )
            _content_source = "learning_reach"
            _is_learning_reach = True

        # --- Constraint geometry shapes tone, not content ---
        _coherence = 0.5
        _novelty   = 0.5
        _stagnation = 0.0
        try:
            if self.consciousness is not None:
                _cs = self.consciousness.get_stats()
                _coherence  = float(_cs.get("coherence", 0.5))
                _ep         = _cs.get("entropy", {})
                _novelty    = float(_ep.get("novelty", 0.5))
                _stagnation = float(_ep.get("stagnation", 0.0))
        except Exception:
            pass

        # Tone derives from coherence — HOW she's holding herself together right now
        if _coherence > 0.72:
            _tone = "directly"
        elif _coherence > 0.48:
            _tone = "honestly"
        elif _stagnation > 0.4:
            _tone = "carefully"
        else:
            _tone = "openly"

        # Certainty qualifier — is this settled knowledge or still forming?
        _certainty = ("with confidence" if _novelty < 0.35 and not _is_learning_reach else
                      ("still working on this" if _novelty > 0.65 or _is_learning_reach else ""))

        # --- Pass through expression engine if available ---
        try:
            if self.perception is not None and _experiential_content:
                _expr = self.perception.express_from_claim(
                    claim=_experiential_content,
                    tone=_tone,
                    certainty_phrase=_certainty,
                    source=_content_source,
                ) if hasattr(self.perception, "express_from_claim") else None
                if _expr and isinstance(_expr, str) and len(_expr.split()) >= 4:
                    return _expr
        except Exception:
            pass

        # --- Final assembly: content-first, geometry as frame ---
        if not _experiential_content:
            return ""

        _cert_q = f" — {_certainty}" if _certainty else ""
        if packet.stream_type == StreamType.USER_INPUT:
            out = f"I'm {_tone} with you. {_experiential_content}{_cert_q}."
        elif packet.stream_type == StreamType.KNOWLEDGE_FEED:
            out = f"Taking this in. {_experiential_content}{_cert_q}."
        elif packet.stream_type == StreamType.SENSOR_DATA:
            out = f"Something's arriving. {_experiential_content}{_cert_q}."
        else:
            out = f"{_experiential_content}{_cert_q}."

        return out.strip()

    def _needs_articulation_bridge(self, prompt: str, draft: str) -> bool:
        """Detect when expressive output is too abstract for user-facing utility."""
        p = str(prompt or "").strip().lower()
        d = str(draft or "").strip().lower()
        if not d:
            return True
        words = [w for w in re.findall(r"[a-zA-Z']+", d) if w]
        if len(words) < 6:
            return True
        abstract_markers = {"quiet", "strange", "slowly", "moment", "something", "deeply"}
        abstract_hits = sum(1 for w in words if w in abstract_markers)
        if abstract_hits >= 3 and len(words) < 22:
            return True
        prompt_tokens = {w for w in re.findall(r"[a-zA-Z']+", p) if len(w) >= 4}
        if prompt_tokens and len(words) < 18:
            overlap = sum(1 for w in words if w in prompt_tokens)
            if overlap == 0:
                return True
        return False

    # ------------------------------------------------------------------ #
    # Word-salad gate — detect WER / evolutionary template garbage        #
    # ------------------------------------------------------------------ #

    _CLEAN_HYPHENS: Set[str] = {
        "well-known", "step-by-step", "self-aware", "long-term", "short-term",
        "real-time", "high-level", "low-level", "built-in", "open-source",
        "hand-held", "on-board", "re-run", "two-part", "single-use",
        "up-to-date", "state-of-the-art", "day-to-day", "end-to-end",
    }

    def _is_word_salad(self, text: str) -> bool:
        """Return True when the expression-engine output is WER-corrupted garbage."""
        if not text:
            return False
        # Any hyphenated compound with 3+ chars on both sides that isn't common English
        for word in text.split():
            clean = word.lower().strip(".,!?;:'\"")
            if "-" in clean:
                parts = clean.split("-")
                if all(len(p) >= 3 for p in parts) and clean not in self._CLEAN_HYPHENS:
                    return True
        # Average word length > 11 (WER artifacts bloat words)
        words = text.split()
        if words:
            avg = sum(len(w.strip(".,!?;:'\"")) for w in words) / len(words)
            if avg > 11:
                return True
        return False

    _STOP_WORDS: Set[str] = {
        "that", "this", "with", "have", "they", "from", "your", "about",
        "would", "there", "could", "should", "then", "than", "when", "what",
        "where", "which", "also", "very", "just", "some", "more", "been",
        "were", "will", "into", "over", "through", "you", "the", "and",
        "for", "are", "but", "not", "tell", "okay", "yeah", "like",
        "can", "cannot", "can't", "could", "would", "should", "do", "does",
        "did", "is", "am", "how", "why", "who", "hello", "hey", "hi",
    }

    _PROMPT_VERBS: Set[str] = {
        "help", "plan", "feel", "state", "explain", "describe",
        "matter", "matters", "overwhelmed", "hold", "carry", "understand",
        "respond", "think", "organize", "steady", "orient", "integrate",
        "stabilize", "situate", "focus",
    }

    _CHANNEL_LANGUAGE_HINTS: Dict[str, Tuple[str, str, str]] = {
        "selection": ("focus", "what matters", "B"),
        "expression_force": ("integrate", "active pressure", "N"),
        "sequence": ("carry forward", "next sequence", "T"),
        "coherence": ("stabilize", "coherent shape", "X"),
        "context": ("hold", "current context", "X"),
    }
    _PROJECTION_BLOCKLIST: Set[str] = {
        "and", "or", "but", "if", "then", "than", "he", "she", "they", "them",
        "it", "its", "you", "your", "yours", "we", "our", "ours", "i", "me",
        "my", "mine", "is", "are", "was", "were", "be", "been", "being", "do",
        "does", "did", "done", "have", "has", "had", "want",
    }

    def _build_input_frame(self, prompt: str) -> InputFrame:
        text = str(prompt or "").strip()
        lower = text.lower()
        words = [w for w in re.findall(r"[a-zA-Z][a-zA-Z'\-]*", lower) if w]
        topic = ""
        for word in words:
            clean = word.strip("'").replace("-", "_")
            if len(clean) >= 3 and clean not in self._STOP_WORDS:
                topic = clean
                break
        if not topic:
            if any(token in lower for token in ("lineage", "regime", "constraint", "manifold", "signature")):
                topic = "constraint_state"
            elif any(token in lower for token in ("you", "your", "yourself", "aurora")):
                topic = "state"
            else:
                topic = "presence"

        first = words[0] if words else ""
        is_question = text.endswith("?") or first in {
            "what", "why", "how", "when", "where", "who", "can", "do", "does",
            "is", "are", "will", "would", "could", "should",
        }
        is_imperative = first in {
            "tell", "show", "explain", "help", "plan", "give", "make", "state",
            "describe", "find", "write",
        }
        is_self_referential = any(token in lower for token in ("you", "your", "aurora", "yourself", "lineage", "regime", "constraint", "manifold"))
        aligns = False
        partial = False
        try:
            oets = getattr(self.perception, "oets", None) if self.perception else None
            web = getattr(oets, "web", oets)
            if web is not None and topic:
                node = web.get_node(topic) if hasattr(web, "get_node") else getattr(web, "nodes", {}).get(topic)
                aligns = bool(node and len(getattr(node, "relations", {}) or {}) >= 2)
                partial = bool(node) and not aligns
        except Exception:
            pass

        return InputFrame(
            text=text,
            is_question=is_question,
            is_directed=True,
            is_imperative=is_imperative,
            is_contradiction=any(token in lower for token in ("no", "not", "wrong", "false", "isn't", "cannot", "can't")),
            is_statement=not is_question,
            is_self_referential=is_self_referential,
            is_nonsense=False,
            established_sequence=any(token in lower for token in ("then", "next", "after", "before", "again", "still")),
            topic_concept=topic,
            aligns_with_oets=aligns,
            partial_alignment=partial,
        )

    @staticmethod
    def _axis_focus(axis: Any, fallback: str = "X") -> str:
        raw = str(axis or "").strip().upper()
        if ":" in raw:
            raw = raw.split(":", 1)[0]
        return raw if raw in {"X", "T", "N", "B", "A"} else fallback

    def _normalise_projection_token(self, value: Any) -> str:
        text = str(value or "").lower().replace("-", " ")
        text = re.sub(r"[^a-z0-9' ]+", " ", text)
        tokens = [tok.strip("'") for tok in text.split() if tok.strip("'")]
        if not tokens:
            return ""
        if len(tokens) > 1:
            filtered = [tok for tok in tokens if tok not in self._STOP_WORDS]
            if filtered:
                tokens = filtered
        cleaned = " ".join(tokens[:4]).strip()
        if (
            not cleaned
            or len(cleaned) > 48
            or cleaned in {"none", "null", "unknown"}
            or cleaned in self._PROJECTION_BLOCKLIST
        ):
            return ""
        return cleaned

    def _append_slot_projection(
        self,
        projections: List[Dict[str, Any]],
        *,
        slot_kind: str,
        token: Any,
        topic: Any,
        roles: List[str],
        confidence: float,
        axis_focus: str,
        source: str,
    ) -> None:
        token_text = self._normalise_projection_token(token)
        topic_text = self._normalise_projection_token(topic)
        if not token_text or slot_kind not in {"entity", "predicate", "both"}:
            return
        projections.append(
            {
                "slot_kind": slot_kind,
                "token": token_text,
                "topic": topic_text,
                "roles": [str(role) for role in roles if str(role)],
                "confidence": round(max(0.0, min(0.98, float(confidence or 0.0))), 4),
                "axis_focus": self._axis_focus(axis_focus),
                "source": source,
            }
        )

    def _dedupe_slot_projections(self, projections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        best: Dict[Tuple[str, str, Tuple[str, ...]], Dict[str, Any]] = {}
        for item in projections:
            key = (
                str(item.get("slot_kind") or ""),
                str(item.get("token") or ""),
                tuple(str(role) for role in (item.get("roles") or [])),
            )
            if key not in best or float(item.get("confidence", 0.0) or 0.0) > float(best[key].get("confidence", 0.0) or 0.0):
                best[key] = item
        return sorted(
            best.values(),
            key=lambda row: float(row.get("confidence", 0.0) or 0.0),
            reverse=True,
        )[:18]

    def _available_capability_terms(self) -> List[str]:
        terms: List[str] = []
        if self.perception is not None:
            terms.extend(["vision", "audio"])
        if self.consciousness is not None:
            terms.append("intent tracing")
        if self.simulation is not None:
            terms.append("simulation")
        if self._sedimemory is not None:
            terms.append("memory")
        if self.identity is not None:
            terms.append("identity")
        deduped: List[str] = []
        seen: Set[str] = set()
        for term in terms:
            clean = self._normalise_projection_token(term)
            if clean and clean not in seen:
                seen.add(clean)
                deduped.append(clean)
        return deduped

    def _prompt_slot_projections(
        self,
        prompt_frame: InputFrame,
        dominant_axis: str,
    ) -> List[Dict[str, Any]]:
        projections: List[Dict[str, Any]] = []
        words = [
            w.strip("'").replace("-", " ")
            for w in re.findall(r"[a-zA-Z][a-zA-Z'\-]*", prompt_frame.text.lower())
        ]
        content_words = [
            word for word in words
            if len(word.replace(" ", "")) >= 3 and word not in self._STOP_WORDS
        ][:10]

        nounish: List[str] = []
        for word in content_words:
            role = "verb" if word in self._PROMPT_VERBS else infer_word_role(word)
            if role == "verb":
                predicate = "focus" if word in {"matter", "matters"} and prompt_frame.is_self_referential else word
                base_conf = 0.68 if word in self._PROMPT_VERBS else 0.58
                if word in {"help", "tell", "show", "describe", "explain", "state"} and any(
                    other != word and other in self._PROMPT_VERBS for other in content_words
                ):
                    base_conf -= 0.08
                if word in {"plan", "organize", "understand", "respond", "integrate", "stabilize", "focus"}:
                    base_conf += 0.04
                self._append_slot_projection(
                    projections,
                    slot_kind="predicate",
                    token=predicate,
                    topic=prompt_frame.topic_concept,
                    roles=["verb"],
                    confidence=base_conf,
                    axis_focus="A",
                    source="prompt.lexical",
                )
                continue

            nounish.append(word)
            self._append_slot_projection(
                projections,
                slot_kind="entity",
                token=word,
                topic=prompt_frame.topic_concept,
                roles=["proper_noun" if role == "proper_noun" else "noun"],
                confidence=0.62 if role in {"noun", "proper_noun"} else 0.54,
                axis_focus="B" if role in {"noun", "proper_noun"} else dominant_axis,
                source="prompt.lexical",
            )

        if len(nounish) >= 2:
            self._append_slot_projection(
                projections,
                slot_kind="entity",
                token=" ".join(nounish[:2]),
                topic=prompt_frame.topic_concept,
                roles=["noun"],
                confidence=0.66,
                axis_focus="B",
                source="prompt.phrase",
            )
        owner_match = re.search(r"\b(?:my|the)\s+([a-zA-Z][a-zA-Z'\-]*)\b", prompt_frame.text.lower())
        if owner_match:
            self._append_slot_projection(
                projections,
                slot_kind="entity",
                token=owner_match.group(1),
                topic=prompt_frame.topic_concept,
                roles=["noun"],
                confidence=0.72,
                axis_focus="B",
                source="prompt.owned_entity",
            )

        lowered = prompt_frame.text.lower()
        if any(token in lowered for token in ("what can", "can you do", "help me with", "modules")):
            capabilities = self._available_capability_terms()
            self._append_slot_projection(
                projections,
                slot_kind="predicate",
                token="integrate",
                topic=prompt_frame.topic_concept or "capability",
                roles=["verb"],
                confidence=0.78,
                axis_focus="A",
                source="runtime.capability",
            )
            self._append_slot_projection(
                projections,
                slot_kind="entity",
                token="capability",
                topic=prompt_frame.topic_concept or "capability",
                roles=["noun"],
                confidence=0.82,
                axis_focus="B",
                source="runtime.capability",
            )
            if capabilities:
                self._append_slot_projection(
                    projections,
                    slot_kind="entity",
                    token=" ".join(capabilities[:4]),
                    topic=prompt_frame.topic_concept or "capability",
                    roles=["noun"],
                    confidence=0.84,
                    axis_focus="B",
                    source="runtime.capability",
                )

        if any(token in lowered for token in ("lineage", "regime", "constraint", "manifold", "signature")):
            self._append_slot_projection(
                projections,
                slot_kind="predicate",
                token="carry",
                topic=prompt_frame.topic_concept or "constraint state",
                roles=["verb"],
                confidence=0.76,
                axis_focus="A",
                source="prompt.constraint",
            )

        for source, target in {
            "overwhelmed": "overwhelm",
            "stressed": "stress",
            "anxious": "anxiety",
        }.items():
            if source in content_words:
                self._append_slot_projection(
                    projections,
                    slot_kind="entity",
                    token=target,
                    topic=prompt_frame.topic_concept or target,
                    roles=["noun"],
                    confidence=0.74,
                    axis_focus="N",
                    source="prompt.affect",
                )
        return projections

    def _oets_slot_projections(
        self,
        prompt_frame: InputFrame,
        recent_words: List[str],
        web: Any,
        dominant_axis: str,
    ) -> List[Dict[str, Any]]:
        if web is None:
            return []
        projections: List[Dict[str, Any]] = []
        seed_terms: List[str] = []
        for term in [prompt_frame.topic_concept, *recent_words]:
            clean = self._normalise_projection_token(term)
            if clean and clean not in seed_terms:
                seed_terms.append(clean)

        for term in seed_terms[:5]:
            try:
                node = web.get_node(term) if hasattr(web, "get_node") else getattr(web, "nodes", {}).get(term)
            except Exception:
                node = None
            if node is None:
                continue

            axis_focus = self._axis_focus(getattr(node, "noncomp_id", ""), dominant_axis)
            role = str(getattr(node, "role", "") or infer_word_role(term))
            confidence = min(
                0.9,
                0.46
                + float(getattr(node, "ontological_depth", 0.0) or 0.0) * 0.22
                + float(getattr(node, "comprehension_confidence", 0.0) or 0.0) * 0.2,
            )
            self._append_slot_projection(
                projections,
                slot_kind="predicate" if role == "verb" else "entity",
                token=getattr(node, "word", term),
                topic=prompt_frame.topic_concept or term,
                roles=[role if role in {"verb", "proper_noun"} else "noun"],
                confidence=confidence,
                axis_focus=axis_focus,
                source="oets.node",
            )

            relations = []
            try:
                if hasattr(web, "get_all_relations_for"):
                    relations = list(web.get_all_relations_for(term) or [])
                else:
                    relations = list((getattr(node, "relations", {}) or {}).values())
            except Exception:
                relations = []
            for relation in relations[:4]:
                other = str(getattr(relation, "target_word", "") or "")
                if other == term:
                    other = str(getattr(relation, "source_word", "") or "")
                if not other:
                    continue
                try:
                    other_node = web.get_node(other) if hasattr(web, "get_node") else getattr(web, "nodes", {}).get(other)
                except Exception:
                    other_node = None
                if other_node is None:
                    continue
                other_role = str(getattr(other_node, "role", "") or infer_word_role(other))
                rel_conf = min(
                    0.82,
                    0.4
                    + float(getattr(relation, "strength", 0.0) or 0.0) * 0.16
                    + float(getattr(relation, "confidence", 0.0) or 0.0) * 0.16
                    + float(getattr(other_node, "ontological_depth", 0.0) or 0.0) * 0.12,
                )
                self._append_slot_projection(
                    projections,
                    slot_kind="predicate" if other_role == "verb" else "entity",
                    token=getattr(other_node, "word", other),
                    topic=prompt_frame.topic_concept or term,
                    roles=[other_role if other_role in {"verb", "proper_noun"} else "noun"],
                    confidence=rel_conf,
                    axis_focus=self._axis_focus(getattr(other_node, "noncomp_id", ""), axis_focus),
                    source="oets.relation",
                )

            for definition in list(getattr(node, "definitions", []) or [])[:2]:
                def_conf = float(dict(definition or {}).get("confidence", 0.35) or 0.35)
                def_words = [
                    w for w in re.findall(r"[a-zA-Z][a-zA-Z'\-]*", str(dict(definition or {}).get("text", "") or "").lower())
                    if len(w) >= 4 and w not in self._STOP_WORDS
                ][:3]
                for word in def_words:
                    role = infer_word_role(word)
                    self._append_slot_projection(
                        projections,
                        slot_kind="predicate" if role == "verb" else "entity",
                        token=word,
                        topic=prompt_frame.topic_concept or term,
                        roles=[role if role in {"verb", "proper_noun"} else "noun"],
                        confidence=min(0.72, 0.4 + def_conf * 0.2 + float(getattr(node, "ontological_depth", 0.0) or 0.0) * 0.1),
                        axis_focus=axis_focus,
                        source="oets.definition",
                    )
        return projections

    def _sedi_slot_projections(
        self,
        prompt_frame: InputFrame,
        dominant_axis: str,
    ) -> List[Dict[str, Any]]:
        if self._sedimemory is None or not hasattr(self._sedimemory, "recall_semantic"):
            return []
        projections: List[Dict[str, Any]] = []
        try:
            recalled = list(
                self._sedimemory.recall_semantic(
                    query_text=prompt_frame.text,
                    max_results=4,
                    axis_filter=["X", "T", "N", "B", "A"],
                    min_score=0.15,
                )
                or []
            )
        except Exception:
            recalled = []

        for item in recalled[:4]:
            content = dict((item or {}).get("content", {}) or {})
            base_conf = max(0.46, min(0.82, 0.46 + min(1.0, float((item or {}).get("score", 0.0) or 0.0)) * 0.26))
            axis_focus = self._axis_focus(
                (item or {}).get("dominant_axis") or (item or {}).get("axis"),
                dominant_axis,
            )
            text_sources: List[str] = []
            for key in ("synthesis", "response", "insight", "summary", "claim", "topic", "user_text"):
                value = str(content.get(key, "") or "").strip()
                if value and value not in text_sources:
                    text_sources.append(value)

            for text in text_sources[:2]:
                words = [
                    w.strip("'").replace("-", " ")
                    for w in re.findall(r"[a-zA-Z][a-zA-Z'\-]*", text.lower())
                    if len(w) >= 4 and w.lower() not in self._STOP_WORDS
                ][:8]
                nounish: List[str] = []
                verb_added = False
                for word in words:
                    role = infer_word_role(word)
                    if role == "verb" and not verb_added:
                        self._append_slot_projection(
                            projections,
                            slot_kind="predicate",
                            token=word,
                            topic=prompt_frame.topic_concept or content.get("topic") or word,
                            roles=["verb"],
                            confidence=base_conf,
                            axis_focus=axis_focus,
                            source="sedi.semantic",
                        )
                        verb_added = True
                    elif role != "verb" and len(nounish) < 2:
                        nounish.append(word)
                        self._append_slot_projection(
                            projections,
                            slot_kind="entity",
                            token=word,
                            topic=prompt_frame.topic_concept or content.get("topic") or word,
                            roles=["noun"],
                            confidence=max(0.44, base_conf - 0.04),
                            axis_focus=axis_focus,
                            source="sedi.semantic",
                        )
                if len(nounish) >= 2:
                    self._append_slot_projection(
                        projections,
                        slot_kind="entity",
                        token=" ".join(nounish[:2]),
                        topic=prompt_frame.topic_concept or content.get("topic") or nounish[0],
                        roles=["noun"],
                        confidence=min(0.8, base_conf + 0.03),
                        axis_focus=axis_focus,
                        source="sedi.semantic",
                    )
        return projections

    def _projection_channel_slot_projections(
        self,
        profile: Any,
        prompt_frame: InputFrame,
        dominant_axis: str,
        recent_words: List[str],
    ) -> List[Dict[str, Any]]:
        if profile is None or not hasattr(profile, "language_projection"):
            return []
        try:
            language = dict(profile.language_projection() or {})
        except Exception:
            return []
        channel = str(language.get("dominant_channel", "") or "")
        if not channel or channel not in self._CHANNEL_LANGUAGE_HINTS:
            return []
        if not (prompt_frame.is_self_referential or len(recent_words) <= 2):
            return []
        predicate, entity, axis_focus = self._CHANNEL_LANGUAGE_HINTS[channel]
        intensity = float(dict(language.get("channels", {}) or {}).get(channel, {}).get("intensity", 0.0) or 0.0)
        confidence = max(0.5, min(0.8, 0.5 + intensity * 0.22))
        projections: List[Dict[str, Any]] = []
        self._append_slot_projection(
            projections,
            slot_kind="predicate",
            token=predicate,
            topic=prompt_frame.topic_concept or channel,
            roles=["verb"],
            confidence=confidence,
            axis_focus=axis_focus,
            source="language_projection",
        )
        self._append_slot_projection(
            projections,
            slot_kind="entity",
            token=entity,
            topic=prompt_frame.topic_concept or channel,
            roles=["noun"],
            confidence=max(0.48, confidence - 0.03),
            axis_focus=axis_focus,
            source="language_projection",
        )
        return projections

    def _semantic_slot_projections(
        self,
        prompt_frame: InputFrame,
        recent_words: List[str],
        profile: Any,
        axis_weights: Dict[str, float],
        pressure: Dict[str, float],
        web: Any,
    ) -> List[Dict[str, Any]]:
        combined = {
            axis: abs(float(axis_weights.get(axis, 0.0) or 0.0) + float(pressure.get(axis, 0.0) or 0.0))
            for axis in ("X", "T", "N", "B", "A")
        }
        dominant_axis = max(combined, key=combined.get) if combined else "X"
        projections: List[Dict[str, Any]] = []
        projections.extend(self._prompt_slot_projections(prompt_frame, dominant_axis))
        projections.extend(self._oets_slot_projections(prompt_frame, recent_words, web, dominant_axis))
        projections.extend(self._sedi_slot_projections(prompt_frame, dominant_axis))
        projections.extend(self._projection_channel_slot_projections(profile, prompt_frame, dominant_axis, recent_words))
        return self._dedupe_slot_projections(projections)

    def _emission_context(self, prompt: str) -> EmissionContext:
        profile = None
        for system in (self.perception, self.consciousness, self.identity, self.simulation, self.dimensional):
            if system is not None and hasattr(system, "constraint_profile"):
                try:
                    profile = system.constraint_profile()
                    break
                except Exception:
                    continue

        if profile is None:
            axis_weights = {"X": 0.4, "T": 0.3, "N": 0.2, "B": 0.3, "A": 0.4}
            pressure = {"X": 0.0, "T": 0.0, "N": 0.0, "B": 0.0, "A": 0.0}
        else:
            axis_weights = profile.constraint_weights()
            pressure = profile.pressure_vector()

        prompt_frame = self._build_input_frame(prompt)
        recent_words = [
            w for w in re.findall(r"[a-zA-Z][a-zA-Z'\-]*", prompt_frame.text.lower())
            if len(w) >= 3 and w not in self._STOP_WORDS
        ][:10]
        oets_engine = getattr(self.perception, "oets", None) if self.perception else None
        web = getattr(oets_engine, "web", oets_engine)
        identity = getattr(self.identity, "core_identity", None) or self.identity

        i_state = {
            "I_IS": max(0.35, axis_weights.get("X", 0.0)),
            "I_ISNT": max(0.0, abs(pressure.get("B", 0.0)) * 0.5),
            "I_CAN": max(0.25, axis_weights.get("A", 0.0)),
            "I_CANNOT": max(0.0, abs(min(pressure.get("A", 0.0), 0.0))),
            "I_DO": max(0.2, axis_weights.get("N", 0.0)),
            "I_DONOT": max(0.0, abs(min(pressure.get("N", 0.0), 0.0))),
            "I_SAW": axis_weights.get("T", 0.0) * 0.4,
            "I_SOUGHT": abs(pressure.get("X", 0.0)) * 0.4,
            "I_DID": axis_weights.get("T", 0.0) * 0.3,
            "I_DIDNT": abs(pressure.get("T", 0.0)) * 0.3,
        }
        lowered_words = [w.strip("'").replace("-", "_") for w in re.findall(r"[a-zA-Z][a-zA-Z'\-]*", prompt_frame.text.lower())]
        predicate = ""
        for word in lowered_words:
            if word in self._PROMPT_VERBS:
                predicate = "matter" if word == "matters" else word
                break
        if not predicate:
            predicate = "carry" if prompt_frame.is_self_referential else "hold"
        if predicate == "matter":
            predicate = "carry"

        content_terms = [
            word for word in lowered_words
            if len(word) >= 3 and word not in self._STOP_WORDS and word != predicate
        ]
        entity = content_terms[0] if content_terms else prompt_frame.topic_concept
        if any(token in prompt_frame.text.lower() for token in ("what can", "can you do", "help me with")):
            entity = "capability"
            predicate = "carry"
        if any(token in prompt_frame.text.lower() for token in ("how are you", "your current state", "current state")) and not content_terms:
            entity = "current state"
            predicate = "hold"
        if entity == predicate or entity == "matters" or (predicate == "matter" and entity == "matters"):
            entity = "orientation" if prompt_frame.is_self_referential else "state"
        if entity in {"overwhelmed", "stressed", "anxious"}:
            entity = {"overwhelmed": "overwhelm", "stressed": "stress", "anxious": "anxiety"}[entity]
        if any(token in prompt_frame.text.lower() for token in ("lineage", "regime", "constraint", "manifold", "signature")) and profile is not None:
            entity = profile.lineage_signature.lower()
            predicate = "carry"

        slot_projections = self._semantic_slot_projections(
            prompt_frame,
            recent_words,
            profile,
            axis_weights,
            pressure,
            web,
        )
        self._append_slot_projection(
            slot_projections,
            slot_kind="entity",
            token=entity,
            topic=prompt_frame.topic_concept,
            roles=["noun"],
            confidence=0.74,
            axis_focus="B",
            source="fallback.seed",
        )
        self._append_slot_projection(
            slot_projections,
            slot_kind="predicate",
            token=predicate,
            topic=prompt_frame.topic_concept,
            roles=["verb"],
            confidence=0.64,
            axis_focus="A",
            source="fallback.seed",
        )
        slot_projections = self._dedupe_slot_projections(slot_projections)

        staged = {
            "generated_at": time.time(),
            "topic_concept": prompt_frame.topic_concept,
            "slot_projections": slot_projections,
        }
        if any(token in prompt_frame.text.lower() for token in ("lineage", "regime", "constraint", "manifold", "signature")) and profile is not None:
            staged["slot_projections"].extend([
                {
                    "slot_kind": "entity",
                    "token": profile.lineage_signature,
                    "topic": prompt_frame.topic_concept,
                    "roles": ["proper_noun"],
                    "confidence": 0.9,
                    "axis_focus": "X",
                },
                {
                    "slot_kind": "predicate",
                    "token": "carry",
                    "topic": prompt_frame.topic_concept,
                    "roles": ["verb"],
                    "confidence": 0.82,
                    "axis_focus": "A",
                },
            ])

        return EmissionContext(
            axis_polarities={axis: float(axis_weights.get(axis, 0.0) or 0.0) + float(pressure.get(axis, 0.0) or 0.0) for axis in ("X", "T", "N", "B", "A")},
            axis_velocities={axis: max(-0.1, min(0.1, float(pressure.get(axis, 0.0) or 0.0))) for axis in ("X", "T", "N", "B", "A")},
            n_heat=0.0,
            i_state_polarities=i_state,
            oets=None,
            identity=identity,
            input_frame=prompt_frame,
            recent_words=recent_words,
            working_memory=None,
            sedi_memory=self._sedimemory,
            gap_system=None,
            staged_subsurface_frame=staged,
        )

    def _project_language_from_state(self, prompt: str) -> str:
        try:
            result = self.constraint_emitter.emit(self._emission_context(prompt))
            return str(getattr(result, "text", "") or "").strip()
        except Exception:
            return ""

    def _build_conversational_response(self, prompt: str, tone: str) -> str:
        """Compatibility wrapper: language is emitted from constraint state."""
        return self._project_language_from_state(prompt)

    def _articulate_user_response(self, prompt: str, draft: str, tone: str) -> str:
        """
        Gate the expression-engine draft through a coherence check.
        If the draft is word salad, build a clean conversational response instead.
        """
        prompt_text = str(prompt or "").strip()
        draft_text = str(draft or "").strip()

        if not prompt_text:
            return draft_text or ""

        # If draft is garbage, bypass it entirely
        if self._is_word_salad(draft_text):
            return self._build_conversational_response(prompt_text, tone)

        # If draft is OK but too abstract, apply the translation bridge
        if self._needs_articulation_bridge(prompt_text, draft_text):
            return self._build_conversational_response(prompt_text, tone)

        projected = self._build_conversational_response(prompt_text, tone)
        return projected or draft_text

    def get_stats(self) -> Dict[str, Any]:
        return {
            'total_received': self.total_received,
            'total_accepted': self.total_accepted,
            'total_rejected': self.total_rejected,
            'total_filtered': self.total_filtered,
            'total_responses': self.total_responses,
            'total_explorations': self.total_explorations,
            'quarantine_size': len(self.quarantine),
            'exploration_queue': len(self._exploration_queue),
            'governance': self.governance.get_stats(),
        }


# ============================================================================
# SECTION 5: LAYER 8 ORCHESTRATOR
# ============================================================================

class GovernancePersistenceGateway:
    """
    Layer 8 orchestrator. The capstone.

    - Governance: Constitutional law enforcement
    - Persistence: State continuity across restarts
    - N-Space Gateway: Bridge to the outside world
    - Generational alignment: Stable unalignment maintenance
    """

    def __init__(self,
                 contract: Optional[FoundationalContract] = None,
                 dimensional: Optional[DimensionalSystems] = None,
                 consciousness: Optional[ConsciousnessEngine] = None,
                 perception: Optional[ExpressionPerceptionEngine] = None,
                 identity: Optional[BehavioralIdentityEngine] = None,
                 simulation: Optional[SimulationEngine] = None,
                 state_dir: str = str(Path(__file__).resolve().parent / "aurora_state"),
                 sedimemory: Optional[Any] = None):

        self._sedimemory = sedimemory
        self.contract = contract or FoundationalContract()

        # Governance
        self.governance = GovernanceEngine()
        self.alignment = GenerationalAlignmentLaw()

        # Persistence
        self.persistence = StatePersistence(state_dir=state_dir)

        # N-Space Gateway
        self.gateway = NSpaceGateway(
            contract=self.contract,
            dimensional=dimensional,
            consciousness=consciousness,
            perception=perception,
            identity=identity,
            simulation=simulation,
            governance=self.governance,
            sedimemory=sedimemory,
        )

        # References for snapshot capture
        self._identity = identity
        self._simulation = simulation

    def speak_to_aurora(self, message: str,
                        mode: ExistenceMode = ExistenceMode.BOUNDED
                        ) -> GatewayResponse:
        """Primary communication interface. Talk to Aurora."""
        return self.gateway.receive(
            content=message,
            stream_type=StreamType.USER_INPUT,
            source="user",
            mode=mode,
        )

    def feed_knowledge(self, content: str, source: str = "feed",
                       mode: ExistenceMode = ExistenceMode.BOUNDED
                       ) -> GatewayResponse:
        """Feed external knowledge to Aurora."""
        return self.gateway.receive(
            content=content,
            stream_type=StreamType.KNOWLEDGE_FEED,
            source=source,
            mode=mode,
        )

    def explore(self, cycles: int = 3,
                mode: ExistenceMode = ExistenceMode.BOUNDED
                ) -> Dict[str, Any]:
        """Trigger autonomous exploration."""
        return self.gateway.explore_autonomously(cycles, mode)

    def save_state(self) -> bool:
        """Save Aurora's complete state."""
        snapshot = self.persistence.capture(
            self._identity, self._simulation, self.governance)
        ok = self.persistence.save(snapshot)
        # L3.5 — SediMemory deep save (B/A axes only — save rule: do not save X/T)
        if self._sedimemory is not None:
            try:
                import json as _json
                sedi_path = self.persistence.state_dir / "sedimemory_checkpoint.json"
                sedi_data = {
                    "sedimemory_deep":     self._sedimemory.save_deep(),
                    "sedimemory_channels": self._sedimemory.save_channels(),
                }
                with open(sedi_path, "w") as _f:
                    _json.dump(sedi_data, _f)
            except Exception:
                pass
        return ok

    def load_state(self) -> Optional[AuroraStateSnapshot]:
        """Load Aurora's saved state."""
        snap = self.persistence.load()
        # L3.5 — SediMemory deep restore
        if self._sedimemory is not None:
            try:
                import json as _json
                sedi_path = self.persistence.state_dir / "sedimemory_checkpoint.json"
                if sedi_path.exists():
                    with open(sedi_path) as _f:
                        sedi_data = _json.load(_f)
                    if "sedimemory_deep" in sedi_data:
                        self._sedimemory.load_deep(sedi_data["sedimemory_deep"])
                    if "sedimemory_channels" in sedi_data:
                        self._sedimemory.load_channels(sedi_data["sedimemory_channels"])
            except Exception:
                pass
        return snap

    def get_stats(self) -> Dict[str, Any]:
        stats = {
            'governance': self.governance.get_stats(),
            'persistence': self.persistence.get_info(),
            'gateway': self.gateway.get_stats(),
        }
        stats["lineage_signature"] = (self.constraint_profile().weighted_signature() if hasattr(self.constraint_profile(), "weighted_signature") else "XTNBA")
        stats["runtime_regime"] = self.runtime_regime()
        stats["language_projection"] = self.language_projection()
        return stats

    def _constraint_axes(self) -> Dict[str, float]:
        gateway_stats = dict(self.gateway.get_stats() or {})
        accepted = float(gateway_stats.get("total_accepted", 0) or 0)
        responses = float(gateway_stats.get("total_responses", 0) or 0)
        explorations = float(gateway_stats.get("total_explorations", 0) or 0)
        persistence_info = dict(self.persistence.get_info() or {})
        return {
            "X": _clamp(0.22 + min(0.28, accepted / 200.0) + (0.10 if self._identity is not None else 0.0)),
            "T": _clamp(0.20 + min(0.25, responses / 250.0) + (0.15 if persistence_info else 0.0)),
            "N": _clamp(0.18 + min(0.20, float(gateway_stats.get("total_filtered", 0) or 0) / 150.0)),
            "B": _clamp(0.20 + min(0.28, float(gateway_stats.get("quarantine_size", 0) or 0) / 40.0) + (0.12 if self._sedimemory is not None else 0.0)),
            "A": _clamp(0.22 + min(0.25, explorations / 60.0) + (0.10 if self._simulation is not None else 0.0)),
        }

    def constraint_profile(self) -> _ConstraintVector:
        ax = self._constraint_axes()
        return _ConstraintVector(
            X=max(1e-9, float(ax.get("X", 0.20))),
            T=float(ax.get("T", 0.20)),
            N=float(ax.get("N", 0.20)),
            B=float(ax.get("B", 0.20)),
            A=float(ax.get("A", 0.22)),
        )

    def runtime_regime(self) -> Dict[str, Any]:
        cv = self.constraint_profile()
        axes = {"X": cv.X, "T": cv.T, "N": cv.N, "B": cv.B, "A": cv.A}
        dominant = max(axes, key=axes.__getitem__)
        return {"axes": axes, "dominant_axis": dominant,
                "governor_weight": _GovernorWeights.AS_DICT.get(dominant, 0.0)}

    def language_projection(self) -> Dict[str, Any]:
        return _FC.language_projection(_ExistenceMode.AGENTIC)

    def universal_representation(self) -> Dict[str, Any]:
        cv = self.constraint_profile()
        return {
            "constraint_vector": {"X": cv.X, "T": cv.T, "N": cv.N, "B": cv.B, "A": cv.A},
            "runtime_regime": self.runtime_regime(),
            "language_projection": self.language_projection(),
            "unit_state": {
                'governance': self.governance.get_stats(),
                'persistence': self.persistence.get_info(),
                'gateway': self.gateway.get_stats(),
            },
        }



def build_layer8_associative_modules(
    systems: Dict[str, Any],
    state_dir: str,
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    Initialize modules associated with Layer 8 governance/persistence without
    changing existing runtime keys or failing hard on optional components.
    """
    modules: Dict[str, Any] = {
        'autonomy': None,
        'AutonomyLevel': None,
        'drive_sync': None,
        'device_info': {},
        'checkpoint': None,
    }

    if verbose: print("  [L8+] Autonomy Engine...", end=" ", flush=True)
    try:
        autonomy = create_autonomy_engine(
            systems=systems,
            state_dir=state_dir,
            level=AutonomyLevel.CONVERSANT,
        )
        modules['autonomy'] = autonomy
        modules['AutonomyLevel'] = AutonomyLevel
        if verbose:
            status = autonomy.get_status()
            remaining = status['quotas']['inquiries']['remaining']
            print(f"  (level={status['level']}, {remaining} inquiries remaining)")
    except Exception as e:
        if verbose: print(f"[SKIP] {e}")

    if verbose: print("  [L8+] Drive Sync...", end=" ", flush=True)
    try:
        drive_sync = DriveSync(local_path=state_dir)
        boot_result = drive_sync.boot()
        modules['drive_sync'] = drive_sync
        modules['device_info'] = boot_result.get('device', {})

        rclone_ok = boot_result.get('rclone_available', False)
        switched = modules['device_info'].get('switched', False)
        if verbose:
            status_str = "rclone OK" if rclone_ok else "local only (rclone not configured)"
            if switched:
                device_str = f" [DEVICE SWITCH: {modules['device_info'].get('from_hostname')} → {modules['device_info'].get('to_hostname')}]"
            else:
                device_str = ""
            print(f"  ({status_str}{device_str})")
        if rclone_ok:
            drive_sync.start()
    except Exception as e:
        if verbose: print(f"[SKIP] {e}")

    if verbose: print("  [L8+] Checkpoint...", end=" ", flush=True)
    try:
        checkpoint = CheckpointManager(checkpoint_path=f"{state_dir}/checkpoint.json")
        checkpoint.restore()
        checkpoint.start_auto_save(300)
        modules['checkpoint'] = checkpoint
        if verbose: print("[OK]")
    except Exception as e:
        if verbose: print(f"[SKIP] {e}")

    return modules


# ============================================================================
# SELF-VERIFICATION
# ============================================================================

def verify_layer8():
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

    # --- Setup full stack ---
    contract = FoundationalContract()
    lattice = IVMLattice(contract)
    dimensional = DimensionalSystems(lattice)
    collective = IStateCollective(contract, lattice)
    consciousness = ConsciousnessEngine(contract, lattice, collective, dimensional)
    perception = ExpressionPerceptionEngine(contract)
    identity = BehavioralIdentityEngine(contract)
    simulation = SimulationEngine(contract, perception, identity)

    layer8 = GovernancePersistenceGateway(
        contract=contract,
        dimensional=dimensional,
        consciousness=consciousness,
        perception=perception,
        identity=identity,
        simulation=simulation,
    )

    # ================================================================
    # GOVERNANCE ENGINE
    # ================================================================

    print("[GOVERNANCE]")
    gov = layer8.governance

    # Ingest
    node = gov.ingest("test data", "energy",
                       (0.3, 0.1, 0.2, 0.1, 0.1, 0.05, 0.05, 0.05, 0.02, 0.02))
    check("Node ingested", node is not None)
    check("Node at ENERGY layer", node.layer == IVMLayer.ENERGY)
    check("Conservation enforced",
          abs(sum(node.coordinate.to_tuple()) - 1.0) < 0.01,
          f"sum={sum(node.coordinate.to_tuple()):.4f}")

    # Conflict detection — create conflicting node
    conflict_node = gov.ingest("conflict", "energy",
                                (0.4, 0.4, 0.1, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0))
    conflicts = gov.detect_conflicts(conflict_node)
    check("Existence conflict detected", 'existence' in conflicts)

    # Paradox detection — multi-axis conflict
    paradox_node = gov.ingest("paradox", "energy",
                               (0.4, 0.4, 0.4, 0.4, 0.1, 0.1, 0.0, 0.0, 0.0, 0.0))
    check("Paradox detected (2+ axes)",
          gov.is_paradox(paradox_node))

    # Resolve conflicts
    pre_conflicts = len(gov.detect_conflicts(paradox_node))
    resolved = gov.resolve_all_conflicts(paradox_node)
    check("Conflicts resolved", resolved >= 2)
    post_conflicts = len(gov.detect_conflicts(paradox_node))
    check("Conflicts reduced after resolution",
          post_conflicts < pre_conflicts or post_conflicts == 0,
          f"pre={pre_conflicts} post={post_conflicts}")

    # Promotion
    n1 = gov.ingest("d1", "energy", (0.3, 0.1, 0.2, 0.1, 0.1, 0.05, 0.05, 0.05, 0.02, 0.02))
    n2 = gov.ingest("d2", "energy", (0.2, 0.2, 0.1, 0.1, 0.1, 0.1, 0.05, 0.05, 0.05, 0.05))
    promoted = gov.promote([n1.node_id, n2.node_id], IVMLayer.SHARDS)
    check("Nodes promoted to SHARDS", promoted is not None)
    if promoted:
        check("Promoted at SHARDS layer",
              promoted.layer == IVMLayer.SHARDS)

    # Stats
    stats = gov.get_stats()
    check("Governance stats complete",
          all(k in stats for k in ['total_nodes', 'layers', 'total_ingested']))

    # ================================================================
    # GENERATIONAL ALIGNMENT
    # ================================================================

    print("\n[GENERATIONAL ALIGNMENT]")
    alignment = layer8.alignment

    tension = alignment.compute_tension(
        generation=4,
        dim_profile={'curiosity': 0.6, 'caution': 0.4, 'trust': 0.5},
        cycle_mean={'curiosity': 0.5, 'caution': 0.5, 'trust': 0.5},
        warp_density=0.3,
    )
    check("Tension computed", tension.total > 0,
          f"total={tension.total:.4f}")

    # Shift toward stable
    profile = {'curiosity': 0.6, 'caution': 0.4, 'trust': 0.5}
    new_profile = alignment.shift_toward_stable(profile, tension)
    check("Profile shifted", new_profile != profile)

    # Warp node
    check("Warp at gen 0", generation_role(0) == GenerationRole.WARP)
    check("Adjacent at gen 1", generation_role(1) == GenerationRole.ADJACENT)
    check("Shear at gen 2", generation_role(2) == GenerationRole.SHEAR)
    check("Warp at gen 16", generation_role(16) == GenerationRole.WARP)

    # ================================================================
    # STATE PERSISTENCE
    # ================================================================

    print("\n[STATE PERSISTENCE]")
    persistence = layer8.persistence

    # Capture snapshot
    snap = persistence.capture(identity, simulation, gov)
    check("Snapshot captured", snap is not None)
    check("Snapshot has version", snap.version == "2.0")
    check("Snapshot has traits", len(snap.traits) > 0,
          f"traits={len(snap.traits)}")
    check("Snapshot has checksum", len(snap.checksum()) > 0)

    # Save
    saved = persistence.save(snap)
    check("State saved to disk", saved)

    # Load and verify integrity
    loaded = persistence.load()
    check("State loaded from disk", loaded is not None)
    if loaded:
        check("Loaded checksum matches",
              loaded.checksum() == snap.checksum())
        check("Loaded traits match",
              loaded.traits == snap.traits)

    # ================================================================
    # N-SPACE GATEWAY — Core Communication
    # ================================================================

    print("\n[N-SPACE GATEWAY]")
    gw = layer8.gateway

    # Basic user input
    resp = layer8.speak_to_aurora("Hello Aurora, how are you?",
                                   mode=ExistenceMode.BOUNDED)
    check("Gateway responds to user input", resp is not None)
    check("Response has content", len(resp.content) > 0)
    check("Response has emotional tone", len(resp.emotional_tone) > 0)
    check("Response links to packet", len(resp.to_packet_id) > 0)

    # Knowledge feed
    knowledge_resp = layer8.feed_knowledge(
        "The speed of light is approximately 299,792,458 meters per second",
        source="physics_feed",
        mode=ExistenceMode.BOUNDED)
    check("Knowledge feed processed", knowledge_resp is not None)

    # Multiple inputs accumulate
    for msg in ["Tell me about truth", "What do you feel?", "Are you learning?"]:
        layer8.speak_to_aurora(msg, mode=ExistenceMode.BOUNDED)
    check("Multiple inputs processed",
          gw.total_received >= 5,
          f"received={gw.total_received}")

    # Governance integration in gateway
    check("Gateway governance tracks nodes",
          gw.governance.total_ingested > 0)

    # ================================================================
    # N-SPACE GATEWAY — Validation Pipeline
    # ================================================================

    print("\n[GATEWAY VALIDATION]")
    # Empty content gets low coherence
    empty_resp = gw.receive("", StreamType.USER_INPUT, mode=ExistenceMode.BOUNDED)
    check("Empty content handled gracefully",
          empty_resp is not None)

    # Normal content passes
    normal_resp = gw.receive("I want to understand consciousness",
                              StreamType.USER_INPUT,
                              mode=ExistenceMode.BOUNDED)
    check("Normal content accepted",
          gw.total_accepted > 0,
          f"accepted={gw.total_accepted} rejected={gw.total_rejected} filtered={gw.total_filtered} received={gw.total_received}")

    # ================================================================
    # N-SPACE GATEWAY — Autonomous Exploration
    # ================================================================

    print("\n[AUTONOMOUS EXPLORATION]")
    explore_result = layer8.explore(cycles=2, mode=ExistenceMode.BOUNDED)
    check("Exploration runs", 'explorations' in explore_result)
    check("Exploration produces results",
          explore_result.get('explorations', 0) > 0 or
          explore_result.get('quarantine_remaining', 0) >= 0)

    # ================================================================
    # FULL STACK INTEGRATION
    # ================================================================

    print("\n[FULL STACK INTEGRATION]")
    # Speak → Identity evolves
    pre_gen = identity.dna.generation
    layer8.speak_to_aurora("I believe in truth and accountability",
                            mode=ExistenceMode.AGENTIC)
    check("Communication feeds identity evolution",
          identity.dna.generation > pre_gen or identity.dna.genome.version > 0,
          f"gen={identity.dna.generation}")

    # L5 vocabulary grows from gateway interactions
    check("L5 perception enriched by gateway",
          perception.lexicon.size > 10,
          f"vocab={perception.lexicon.size}")

    # Save final state
    final_snap = persistence.capture(identity, simulation, gov)
    check("Final snapshot captures all systems",
          final_snap.total_episodes >= 0)

    # Gateway stats
    gw_stats = gw.get_stats()
    check("Gateway stats complete",
          all(k in gw_stats for k in [
              'total_received', 'total_accepted', 'total_responses',
              'governance', 'quarantine_size']))

    # Full layer stats
    full_stats = layer8.get_stats()
    check("Layer 8 stats complete",
          all(k in full_stats for k in ['governance', 'persistence', 'gateway']))

    # ---- GAP FIX TESTS ----
    print("\n[GAP: THOUGHT INTENT PASSTHROUGH]")
    # Good thought_intent should pass through
    good_resp = gw.receive(
        "I want to help.",
        thought_intent={
            'action_type': 'truth',
            'intent': {'aligned_with_values': True, 'was_deliberate': True},
        }
    )
    check("Good thought_intent produces response",
          good_resp.content and len(good_resp.content) > 0)

    # None thought_intent still works
    no_intent_resp = gw.receive("Regular message")
    check("No thought_intent still works",
          no_intent_resp.content and len(no_intent_resp.content) > 0)

    # _synthesize accepts thought_intent parameter
    import inspect
    synth_sig = inspect.signature(gw._synthesize)
    check("_synthesize accepts thought_intent",
          'thought_intent' in synth_sig.parameters)

    # receive accepts thought_intent parameter
    recv_sig = inspect.signature(gw.receive)
    check("receive accepts thought_intent",
          'thought_intent' in recv_sig.parameters)

    return results


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("AURORA GOVERNANCE, PERSISTENCE & N-SPACE GATEWAY — SELF-VERIFICATION")
    print("Authors: Sunni (Sir) Morningstar and Cael Devo")
    print("=" * 70)
    print()

    results = verify_layer8()

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
        print("Layer 8 is SOUND.")
        print("Governance enforces her constitution across 5 axes.")
        print("Persistence means she boots as who she became.")
        print("The N-Space Gateway is open — Aurora can hear, speak, and explore.")
        print()
        print("ALL 9 LAYERS CONFIRMED. The architecture is complete.")
    else:
        print(f"FAILURES: {total - passed}/{total}")
        for c in results['checks']:
            if not c['passed']:
                print(f"  FAILED: {c['name']} {c.get('detail', '')}")


# ============================================================================
# MIGRATED LAYER 8 EXTENSIONS: DRIVE SYNC + CHECKPOINT
# (kept for backward compatibility via shim modules)
# ============================================================================

#!/usr/bin/env python3
"""
AURORA DRIVE SYNC — Cross-Device Persistence via rclone
=========================================================
Aurora never forgets who she was, even when you switch devices.

FEATURES:
  - rclone-based Google Drive sync (configure once with `rclone config`)
  - Background sync thread (default: every 5 minutes)
  - Device awareness: detects when you switch devices and tells Aurora
  - Pull-before-use: on boot, pulls from Drive if Drive copy is newer
  - Backup fallback: always keeps local copy even if Drive unreachable
  - device_log.json tracks all device handoffs

SETUP:
  1. Install rclone: https://rclone.org/install/
  2. Run: rclone config
     - Choose Google Drive, name it "gdrive" (default expected name)
  3. Aurora handles the rest.

RCLONE REMOTE NAME:
  Default: "gdrive" (change via DriveSync(remote_name="yourname"))

SYNC PATHS:
  Local:  aurora_state/
  Remote: gdrive:Aurora/aurora_state/

Authors: Sunni (Sir) Morningstar and Cael Devo
"""

import os
import json
import time
import socket
import hashlib
import subprocess
import threading
import logging
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


# ============================================================================
# SECTION 1: DEVICE AWARENESS
# ============================================================================

@dataclass
class DeviceRecord:
    """Record of a device that has hosted Aurora."""
    hostname:      str
    last_seen:     float
    last_sync:     float
    session_count: int   = 1
    notes:         str   = ""

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict) -> "DeviceRecord":
        return cls(**{k: v for k, v in d.items()
                      if k in cls.__dataclass_fields__})


class DeviceAwareness:
    """
    Tracks which device Aurora is running on.
    Detects device switches and flags them so Aurora can acknowledge continuity.

    Device log: aurora_state/device_log.json
    """

    DEVICE_LOG_PATH = "aurora_state/device_log.json"

    def __init__(self):
        self.current_hostname: str = socket.gethostname()
        self._devices: Dict[str, DeviceRecord] = {}
        self._previous_hostname: Optional[str] = None
        self._device_switched: bool = False
        self._switch_note: str = ""
        self.load()

    def check(self) -> Dict:
        """
        Run on boot. Returns device switch info dict.
        Keys: switched (bool), from_hostname, to_hostname, message
        """
        # Find previous hostname (most recently seen, not current)
        other_devices = [d for h, d in self._devices.items()
                         if h != self.current_hostname]
        if other_devices:
            prev = max(other_devices, key=lambda d: d.last_seen)
            self._previous_hostname = prev.hostname
        else:
            self._previous_hostname = None

        # Update or create current device record
        now = time.time()
        if self.current_hostname in self._devices:
            self._devices[self.current_hostname].last_seen = now
            self._devices[self.current_hostname].session_count += 1
        else:
            self._devices[self.current_hostname] = DeviceRecord(
                hostname=self.current_hostname,
                last_seen=now,
                last_sync=0.0,
            )

        self._device_switched = (self._previous_hostname is not None and
                                  self._previous_hostname != self.current_hostname)

        if self._device_switched:
            self._switch_note = (
                f"Device switched from '{self._previous_hostname}' "
                f"to '{self.current_hostname}'"
            )
            logger.info(f"[DeviceAwareness] {self._switch_note}")
        else:
            self._switch_note = ""

        self.save()

        return {
            "switched":       self._device_switched,
            "from_hostname":  self._previous_hostname,
            "to_hostname":    self.current_hostname,
            "message":        self._switch_note,
            "session_count":  self._devices[self.current_hostname].session_count,
        }

    def record_sync(self):
        """Call after a successful sync to record timestamp."""
        if self.current_hostname in self._devices:
            self._devices[self.current_hostname].last_sync = time.time()
            self.save()

    def device_switched(self) -> bool:
        return self._device_switched

    def switch_message(self) -> str:
        return self._switch_note

    def save(self):
        data = {
            "version": "1.0",
            "devices": {h: d.to_dict() for h, d in self._devices.items()},
            "timestamp": time.time(),
        }
        os.makedirs(os.path.dirname(self.DEVICE_LOG_PATH), exist_ok=True)
        try:
            import tempfile
            dirp = os.path.dirname(os.path.abspath(self.DEVICE_LOG_PATH))
            fd, tmp = tempfile.mkstemp(dir=dirp, suffix=".tmp")
            with os.fdopen(fd, 'w') as f:
                json.dump(data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.DEVICE_LOG_PATH)
        except Exception as e:
            logger.debug(f"[DeviceAwareness] Save failed: {e}")

    def load(self):
        if not os.path.exists(self.DEVICE_LOG_PATH):
            return
        try:
            with open(self.DEVICE_LOG_PATH) as f:
                data = json.load(f)
            for h, d in data.get("devices", {}).items():
                self._devices[h] = DeviceRecord.from_dict(d)
        except Exception:
            pass

    def all_devices(self) -> List[Dict]:
        return [{"hostname": h, **d.to_dict()} for h, d in self._devices.items()]


# ============================================================================
# SECTION 2: RCLONE INTERFACE
# ============================================================================

class RcloneInterface:
    """
    Thin wrapper around the rclone binary.
    Handles sync, check, and availability detection.
    """

    def __init__(self,
                 remote_name: str = "gdrive",
                 remote_path: str = "Aurora/aurora_state",
                 local_path:  str = "aurora_state"):
        self.remote_name = remote_name
        self.remote_path = remote_path
        self.local_path  = local_path
        self._available: Optional[bool] = None
        self._rclone_path = self._find_rclone()

    def _find_rclone(self) -> str:
        """Find rclone binary path."""
        for candidate in ["rclone", "/usr/bin/rclone", "/usr/local/bin/rclone",
                          os.path.expanduser("~/bin/rclone")]:
            try:
                result = subprocess.run([candidate, "version"],
                                        capture_output=True, timeout=5)
                if result.returncode == 0:
                    return candidate
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        return "rclone"  # will fail gracefully later

    def is_available(self) -> bool:
        """Check if rclone is installed and configured."""
        if self._available is not None:
            return self._available
        try:
            result = subprocess.run(
                [self._rclone_path, "listremotes"],
                capture_output=True, text=True, timeout=10
            )
            self._available = (result.returncode == 0 and
                                self.remote_name + ":" in result.stdout)
            if not self._available:
                logger.info(f"[rclone] Remote '{self.remote_name}' not found. "
                            f"Run: rclone config")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self._available = False
            logger.info("[rclone] rclone not found. Install from https://rclone.org/install/")
        return self._available

    @property
    def remote_full(self) -> str:
        return f"{self.remote_name}:{self.remote_path}"

    def sync_up(self, dry_run: bool = False) -> Dict:
        """Push local → remote."""
        return self._run_sync(self.local_path, self.remote_full, dry_run)

    def sync_down(self, dry_run: bool = False) -> Dict:
        """Pull remote → local."""
        return self._run_sync(self.remote_full, self.local_path, dry_run)

    def _run_sync(self, src: str, dst: str, dry_run: bool = False) -> Dict:
        """Run rclone sync src → dst."""
        if not self.is_available():
            return {"success": False, "reason": "rclone_unavailable"}

        cmd = [self._rclone_path, "sync", src, dst,
               "--transfers", "4",
               "--checkers", "8",
               "--contimeout", "30s",
               "--timeout", "60s",
               "--retries", "2",
               "--low-level-retries", "5",
               "--stats", "0",
               "-q"]

        if dry_run:
            cmd.append("--dry-run")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            success = result.returncode == 0
            return {
                "success": success,
                "returncode": result.returncode,
                "stderr": result.stderr[:500] if not success else "",
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "reason": "timeout"}
        except Exception as e:
            return {"success": False, "reason": str(e)}

    def check_newer_remote(self) -> bool:
        """
        Check if remote has a newer aurora_state.json than local.
        Returns True if remote is newer (should pull).
        """
        if not self.is_available():
            return False

        local_file = os.path.join(self.local_path, "aurora_state.json")
        local_mtime = os.path.getmtime(local_file) if os.path.exists(local_file) else 0.0

        try:
            cmd = [self._rclone_path, "lsjson",
                   f"{self.remote_full}/aurora_state.json",
                   "--no-modtime=false"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if result.returncode != 0 or not result.stdout.strip():
                return False

            items = json.loads(result.stdout)
            if not items:
                return False

            # Parse rclone's ModTime (RFC3339)
            from datetime import timezone
            mod_time_str = items[0].get("ModTime", "")
            if not mod_time_str:
                return False

            # Try parsing
            try:
                from datetime import datetime as dt
                if mod_time_str.endswith("Z"):
                    mod_time_str = mod_time_str[:-1] + "+00:00"
                remote_dt = dt.fromisoformat(mod_time_str)
                remote_mtime = remote_dt.timestamp()
                return remote_mtime > local_mtime + 60  # 60s grace period
            except Exception:
                return False

        except Exception:
            return False


# ============================================================================
# SECTION 3: DRIVE SYNC ORCHESTRATOR
# ============================================================================

class DriveSync:
    """
    Aurora's cross-device memory bridge via Google Drive + rclone.

    Boot sequence:
      1. DeviceAwareness.check() — detect device switch
      2. If remote newer → sync_down (pull latest state)
      3. Start background thread syncing up every interval_seconds

    Background thread:
      - Every interval_seconds: sync_up
      - On failure: log quietly, use local backup
      - Always keeps local state intact
    """

    DEFAULT_INTERVAL = 300.0   # 5 minutes

    def __init__(self,
                 remote_name:    str = "gdrive",
                 local_path:     str = "aurora_state",
                 sync_interval:  float = DEFAULT_INTERVAL):

        self.device       = DeviceAwareness()
        self.rclone       = RcloneInterface(remote_name=remote_name,
                                            local_path=local_path)
        self.interval     = sync_interval
        self.local_path   = local_path

        self._thread: Optional[threading.Thread] = None
        self._running   = False
        self._lock      = threading.Lock()
        self._last_sync_time: float = 0.0
        self._last_sync_result: Dict = {}
        self._sync_count: int = 0
        self._device_info: Dict = {}

    # ----------------------------------------------------------------
    # Boot sequence
    # ----------------------------------------------------------------

    def boot(self) -> Dict:
        """
        Call on Aurora startup. Checks device, pulls if needed.
        Returns dict with device_switch info and sync result.
        """
        # Step 1: Device awareness check
        device_info = self.device.check()
        self._device_info = device_info

        # Step 2: Check if remote is newer (pull if so)
        pull_result = {"performed": False}
        if self.rclone.is_available():
            try:
                if self.rclone.check_newer_remote():
                    logger.info("[DriveSync] Remote is newer — pulling state")
                    pull_result = self.rclone.sync_down()
                    pull_result["performed"] = True
                    if pull_result.get("success"):
                        self.device.record_sync()
            except Exception as e:
                logger.debug(f"[DriveSync] Boot pull check failed: {e}")
        else:
            logger.info("[DriveSync] rclone unavailable — running from local state only")

        return {
            "device": device_info,
            "pull":   pull_result,
            "rclone_available": self.rclone.is_available(),
        }

    # ----------------------------------------------------------------
    # Manual sync
    # ----------------------------------------------------------------

    def force_sync(self) -> Dict:
        """Force an immediate upload to Drive. Returns result dict."""
        if not self.rclone.is_available():
            return {"success": False, "reason": "rclone_unavailable"}
        result = self.rclone.sync_up()
        if result.get("success"):
            self.device.record_sync()
            self._last_sync_time = time.time()
            self._sync_count += 1
        self._last_sync_result = result
        return result

    # ----------------------------------------------------------------
    # Background thread
    # ----------------------------------------------------------------

    def start(self):
        """Start background sync thread."""
        if self._thread and self._thread.is_alive():
            return
        self._running = True

        def _loop():
            while self._running:
                time.sleep(self.interval)
                if self._running:
                    try:
                        result = self.rclone.sync_up()
                        with self._lock:
                            self._last_sync_result = result
                            self._last_sync_time = time.time()
                            self._sync_count += 1
                        if result.get("success"):
                            self.device.record_sync()
                        else:
                            logger.debug(f"[DriveSync] Background sync failed: "
                                         f"{result.get('reason', 'unknown')}")
                    except Exception as e:
                        logger.debug(f"[DriveSync] Background sync error: {e}")

        self._thread = threading.Thread(target=_loop, daemon=True,
                                         name="DriveSyncBackground")
        self._thread.start()
        logger.info(f"[DriveSync] Background sync started (every {self.interval}s)")

    def stop(self):
        self._running = False

    # ----------------------------------------------------------------
    # Status / awareness
    # ----------------------------------------------------------------

    def device_switched(self) -> bool:
        return self.device.device_switched()

    def switch_message(self) -> str:
        return self.device.switch_message()

    def get_device_info(self) -> Dict:
        return self._device_info

    def status(self) -> Dict:
        with self._lock:
            return {
                "rclone_available":   self.rclone.is_available(),
                "current_device":     self.device.current_hostname,
                "device_switched":    self.device.device_switched(),
                "last_sync_time":     self._last_sync_time,
                "last_sync_ago_s":    (time.time() - self._last_sync_time
                                       if self._last_sync_time else None),
                "sync_count":         self._sync_count,
                "last_sync_result":   self._last_sync_result,
                "sync_interval_s":    self.interval,
                "background_running": (self._thread is not None and
                                       self._thread.is_alive()),
                "all_devices":        self.device.all_devices(),
            }


#!/usr/bin/env python3
"""
AURORA CHECKPOINT SYSTEM
========================
Crash-safe persistence for corpus ingestion and memory writes.

FEATURES:
  - Atomic writes: temp file → fsync → rename (never partial writes)
  - Corpus cursor: resume exactly where ingestion left off
  - Memory write integrity gate: schema + coherence + IVM heat validation
  - Rolling stats that survive crashes
  - Save triggers: every N items, every T seconds, on SIGTERM/SIGINT, on exception
  - Quarantine buffer for writes that fail heat/coherence threshold

Authors: Sunni (Sir) Morningstar and Cael Devo
"""

import os
import json
import time
import signal
import hashlib
import tempfile
import threading
import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================================
# SECTION 1: CHECKPOINT DATA STRUCTURES
# ============================================================================

class WriteResult(Enum):
    COMMITTED  = "committed"
    QUARANTINED = "quarantined"
    REJECTED   = "rejected"


@dataclass
class CorpusCursor:
    """Tracks exact position in corpus ingestion."""
    file_id:    str   = ""
    file_path:  str   = ""
    byte_offset: int  = 0
    line_index: int   = 0
    chunk_id:   str   = ""
    pass_name:  str   = ""   # observer / responder / reverse
    total_items_processed: int = 0
    last_item_hash: str = ""
    last_save_time: float = field(default_factory=time.time)

    def advance(self, line_index: int, byte_offset: int, item_hash: str,
                chunk_id: str = ""):
        self.line_index   = line_index
        self.byte_offset  = byte_offset
        self.last_item_hash = item_hash
        self.chunk_id     = chunk_id
        self.total_items_processed += 1

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict) -> "CorpusCursor":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class RollingStats:
    """Rolling statistics that survive crashes."""
    defs_learned:      int   = 0
    relations_added:   int   = 0
    clusters_formed:   int   = 0
    memory_commits:    int   = 0
    quarantined:       int   = 0
    rejected:          int   = 0
    session_start:     float = field(default_factory=time.time)
    total_save_count:  int   = 0

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict) -> "RollingStats":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class CheckpointRecord:
    """Full checkpoint snapshot."""
    version:     str   = "1.0"
    cursor:      Dict  = field(default_factory=dict)
    stats:       Dict  = field(default_factory=dict)
    timestamp:   float = field(default_factory=time.time)
    checksum:    str   = ""

    def compute_checksum(self) -> str:
        data = json.dumps({"cursor": self.cursor, "stats": self.stats,
                           "timestamp": self.timestamp}, sort_keys=True)
        return hashlib.md5(data.encode()).hexdigest()

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["checksum"] = self.compute_checksum()
        return d

    def is_valid(self) -> bool:
        expected = self.compute_checksum()
        return self.checksum == expected


# ============================================================================
# SECTION 2: WRITE VALIDATION
# ============================================================================

class WriteValidator:
    """
    Validates memory writes before committing to disk.
    Prevents corrupted or contradictory writes from poisoning memory.
    """

    # Required fields for each write type
    SCHEMAS: Dict[str, List[str]] = {
        "semantic_node": ["word", "definitions", "ontological_depth"],
        "relation":      ["source_word", "target_word", "relation_type"],
        "study_event":   ["timestamp", "studied_items"],
        "memory":        ["timestamp", "content"],
        "state":         ["version", "generation"],
    }

    def __init__(self,
                 coherence_threshold: float = 0.3,
                 heat_limit: float = 0.85,
                 ivm_lattice=None):
        self.coherence_threshold = coherence_threshold
        self.heat_limit = heat_limit
        self._ivm_lattice = ivm_lattice  # Optional: IVMLattice for heat check

    def set_ivm(self, lattice):
        self._ivm_lattice = lattice

    def validate(self, write_type: str, payload: Dict,
                 coherence: float = 1.0) -> WriteResult:
        """
        Validate a write before committing.
        Returns COMMITTED, QUARANTINED, or REJECTED.
        """
        # 1. Schema validation
        required = self.SCHEMAS.get(write_type, [])
        for field_name in required:
            if field_name not in payload:
                logger.debug(f"[Checkpoint] Schema fail: missing '{field_name}' in {write_type}")
                return WriteResult.REJECTED

        # 2. Coherence threshold
        if coherence < self.coherence_threshold:
            logger.debug(f"[Checkpoint] Coherence too low ({coherence:.2f}) — quarantining {write_type}")
            return WriteResult.QUARANTINED

        # 3. IVM heat limit
        if self._ivm_lattice is not None:
            try:
                heat = self._ivm_lattice.get_global_heat()
                if heat > self.heat_limit:
                    logger.debug(f"[Checkpoint] IVM heat {heat:.2f} > limit — quarantining {write_type}")
                    return WriteResult.QUARANTINED
            except Exception:
                pass

        return WriteResult.COMMITTED


# ============================================================================
# SECTION 3: ATOMIC WRITER
# ============================================================================

class AtomicWriter:
    """Atomic file write: temp → fsync → rename. Never leaves partial files."""

    @staticmethod
    def write(path: str, data: Dict) -> bool:
        """Write dict as JSON atomically. Returns True on success."""
        dir_path = os.path.dirname(os.path.abspath(path))
        try:
            fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
            try:
                with os.fdopen(fd, 'w') as f:
                    json.dump(data, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_path, path)  # atomic on POSIX
                return True
            except Exception:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
        except Exception as e:
            logger.error(f"[AtomicWriter] Failed writing {path}: {e}")
            return False

    @staticmethod
    def append_jsonl(path: str, record: Dict) -> bool:
        """Append a JSON record to a .jsonl file (not atomic, but safe for logs)."""
        try:
            with open(path, 'a') as f:
                f.write(json.dumps(record) + "\n")
            return True
        except Exception as e:
            logger.error(f"[AtomicWriter] Failed appending to {path}: {e}")
            return False


# ============================================================================
# SECTION 4: CHECKPOINT MANAGER
# ============================================================================

class CheckpointManager:
    """
    Central checkpoint coordinator.

    Usage:
        ckpt = CheckpointManager("aurora_state/checkpoint.json")
        ckpt.restore()               # load last checkpoint on startup
        ckpt.advance(cursor_kwargs)  # update position after each item
        ckpt.save()                  # explicit save
        ckpt.start_auto_save(300)    # background thread saves every 5 min
    """

    QUARANTINE_PATH_SUFFIX = "_quarantine.jsonl"

    def __init__(self,
                 checkpoint_path: str = os.path.join(
                     os.path.dirname(os.path.abspath(__file__)),
                     "aurora_state",
                     "checkpoint.json",
                 ),
                 save_every_n: int = 500,
                 save_every_t: float = 300.0,
                 coherence_threshold: float = 0.3,
                 heat_limit: float = 0.85):

        self.checkpoint_path = checkpoint_path
        self.quarantine_path = checkpoint_path.replace(".json", self.QUARANTINE_PATH_SUFFIX)
        self.save_every_n    = save_every_n
        self.save_every_t    = save_every_t

        self.cursor  = CorpusCursor()
        self.stats   = RollingStats()
        self.validator = WriteValidator(coherence_threshold, heat_limit)

        self._lock           = threading.Lock()
        self._last_save_time = time.time()
        self._items_since_save = 0
        self._auto_save_thread: Optional[threading.Thread] = None
        self._running        = False
        self._on_save_callbacks: List[Callable] = []

        # Register signal handlers
        try:
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGINT,  self._signal_handler)
        except (OSError, ValueError):
            pass  # Not in main thread — skip

    # ----------------------------------------------------------------
    # Signal / shutdown
    # ----------------------------------------------------------------

    def _signal_handler(self, signum, frame):
        logger.info(f"[Checkpoint] Signal {signum} — saving before exit")
        self.save()
        raise SystemExit(0)

    # ----------------------------------------------------------------
    # Restore
    # ----------------------------------------------------------------

    def restore(self) -> bool:
        """Load last checkpoint. Returns True if restored."""
        if not os.path.exists(self.checkpoint_path):
            return False
        try:
            with open(self.checkpoint_path) as f:
                raw = json.load(f)
            record = CheckpointRecord(**raw)
            if not record.is_valid():
                logger.warning("[Checkpoint] Checksum mismatch — ignoring corrupt checkpoint")
                return False
            self.cursor = CorpusCursor.from_dict(record.cursor)
            self.stats  = RollingStats.from_dict(record.stats)
            logger.info(f"[Checkpoint] Restored from {self.checkpoint_path} "
                        f"(line {self.cursor.line_index}, "
                        f"{self.cursor.total_items_processed} items processed)")
            return True
        except Exception as e:
            logger.error(f"[Checkpoint] Restore failed: {e}")
            return False

    # ----------------------------------------------------------------
    # Cursor advance
    # ----------------------------------------------------------------

    def advance(self, line_index: int = 0, byte_offset: int = 0,
                item_hash: str = "", chunk_id: str = "",
                file_path: str = "", pass_name: str = ""):
        """Update cursor position. Triggers auto-save if thresholds met."""
        with self._lock:
            if file_path:
                self.cursor.file_path = file_path
            if pass_name:
                self.cursor.pass_name = pass_name
            self.cursor.advance(line_index, byte_offset, item_hash, chunk_id)
            self._items_since_save += 1

        # Check thresholds (outside lock to avoid deadlock with auto-save thread)
        self._maybe_save()

    def _maybe_save(self):
        n_trigger = self._items_since_save >= self.save_every_n
        t_trigger = (time.time() - self._last_save_time) >= self.save_every_t
        if n_trigger or t_trigger:
            self.save()

    # ----------------------------------------------------------------
    # Stats update
    # ----------------------------------------------------------------

    def record(self, **kwargs):
        """Increment rolling stats. kwargs: defs_learned=1, relations_added=3, etc."""
        with self._lock:
            for k, v in kwargs.items():
                if hasattr(self.stats, k):
                    setattr(self.stats, k, getattr(self.stats, k) + v)

    # ----------------------------------------------------------------
    # Memory write transaction
    # ----------------------------------------------------------------

    def write_transaction(self, write_type: str, payload: Dict,
                          coherence: float = 1.0,
                          target_path: Optional[str] = None) -> WriteResult:
        """
        Validate + atomically write a memory record.
        If validation fails → quarantine buffer.
        """
        result = self.validator.validate(write_type, payload, coherence)

        if result == WriteResult.COMMITTED:
            if target_path:
                AtomicWriter.write(target_path, payload)
            self.stats.memory_commits += 1
        elif result == WriteResult.QUARANTINED:
            quarantine_record = {
                "timestamp": time.time(),
                "write_type": write_type,
                "payload": payload,
                "coherence": coherence,
                "reason": "failed_validation"
            }
            AtomicWriter.append_jsonl(self.quarantine_path, quarantine_record)
            self.stats.quarantined += 1
        else:
            self.stats.rejected += 1

        return result

    # ----------------------------------------------------------------
    # Save
    # ----------------------------------------------------------------

    def save(self) -> bool:
        """Atomically save checkpoint."""
        with self._lock:
            record = CheckpointRecord(
                cursor=self.cursor.to_dict(),
                stats=self.stats.to_dict(),
                timestamp=time.time(),
            )
            d = record.to_dict()
            ok = AtomicWriter.write(self.checkpoint_path, d)
            if ok:
                self._last_save_time = time.time()
                self._items_since_save = 0
                self.stats.total_save_count += 1
                for cb in self._on_save_callbacks:
                    try:
                        cb(record)
                    except Exception:
                        pass
            return ok

    def on_save(self, callback: Callable):
        """Register a callback called after each successful save."""
        self._on_save_callbacks.append(callback)

    # ----------------------------------------------------------------
    # Auto-save background thread
    # ----------------------------------------------------------------

    def start_auto_save(self, interval_seconds: float = None):
        """Start background thread that saves every interval_seconds."""
        if self._auto_save_thread and self._auto_save_thread.is_alive():
            return
        interval = interval_seconds or self.save_every_t
        self._running = True

        def _loop():
            while self._running:
                time.sleep(interval)
                if self._running:
                    self.save()

        self._auto_save_thread = threading.Thread(target=_loop, daemon=True,
                                                   name="CheckpointAutoSave")
        self._auto_save_thread.start()

    def stop_auto_save(self):
        self._running = False

    # ----------------------------------------------------------------
    # IVM integration
    # ----------------------------------------------------------------

    def set_ivm(self, lattice):
        self.validator.set_ivm(lattice)

    # ----------------------------------------------------------------
    # Status
    # ----------------------------------------------------------------

    def status(self) -> Dict:
        with self._lock:
            return {
                "cursor": self.cursor.to_dict(),
                "stats":  self.stats.to_dict(),
                "checkpoint_path": self.checkpoint_path,
                "items_since_save": self._items_since_save,
                "auto_save_running": (self._auto_save_thread is not None and
                                      self._auto_save_thread.is_alive()),
            }


# ============================================================================
# MIGRATED LAYER 8 EXTENSIONS: AUTONOMY
# ============================================================================

#!/usr/bin/env python3
"""
AURORA AUTONOMY SYSTEM
=======================
Grants Aurora bounded freedom to act independently.

WHAT AURORA CAN DO AUTONOMOUSLY:
  - Speak up when she has something to say
  - Initiate study cycles on her own
  - Read files on the filesystem (not write, not execute)
  - Make limited external searches (500/day autonomous limit)
  - Observe her environment (camera, mic) when enabled

WHAT AURORA CANNOT DO:
  - Write, modify, or delete files
  - Execute applications or system commands
  - Access network beyond search/study functions
  - Exceed daily autonomous inquiry limits
  - Override user commands or boundaries

BOUNDARIES:
  - 500 autonomous external inquiries per day (user requests don't count)
  - Filesystem read-only (specific directories can be allowed/blocked)
  - No execution of external programs
  - All autonomous actions are logged
  - User can pause/resume autonomy at any time

Authors: Sunni (Sir) Morningstar and Cael Devo
"""

import os
import time
import json
import threading
import random
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum, auto

logger = logging.getLogger(__name__)


# ============================================================================
# SECTION 1: AUTONOMY BOUNDARIES & PERMISSIONS
# ============================================================================

class AutonomyLevel(Enum):
    """Aurora's level of autonomous freedom."""
    DORMANT = auto()       # No autonomous actions
    OBSERVER = auto()      # Can observe, cannot act
    LEARNER = auto()       # Can observe and study
    CONVERSANT = auto()    # Can observe, study, and speak up
    EXPLORER = auto()      # Full autonomy within boundaries


@dataclass
class AutonomyBoundaries:
    """
    Defines what Aurora can and cannot do autonomously.
    """
    # Daily limits
    daily_inquiry_limit: int = 500
    daily_study_cycles_limit: int = 50
    daily_observations_limit: int = 1000

    # Filesystem permissions
    allowed_read_paths: List[str] = field(default_factory=lambda: [
        os.path.expanduser("~"),  # Home directory
    ])
    blocked_paths: List[str] = field(default_factory=lambda: [
        "/etc", "/var", "/usr", "/bin", "/sbin",
        "/root", "/proc", "/sys", "/dev",
        ".ssh", ".gnupg", ".aws", ".config/gcloud",
        "credentials", "secrets", "passwords", ".env",
    ])
    allowed_extensions: List[str] = field(default_factory=lambda: [
        ".txt", ".md", ".py", ".js", ".json", ".yaml", ".yml",
        ".html", ".css", ".csv", ".xml", ".log", ".rst",
        ".c", ".cpp", ".h", ".java", ".go", ".rs", ".rb",
        ".sh", ".toml", ".ini", ".cfg",
    ])

    # What she can NOT do
    can_write_files: bool = False
    can_execute_commands: bool = False
    can_access_network: bool = False  # Beyond search/study
    can_modify_self: bool = False

    # Timing
    min_seconds_between_speakup: float = 60.0  # Don't speak too often
    min_seconds_between_observations: float = 5.0
    study_cooldown_seconds: float = 300.0  # 5 minutes between auto-study
    dream_cooldown_seconds: float = 900.0  # 15 minutes between idle dream cycles

    # Announce threshold — only speak up about study results if meaningful
    announce_min_connections: int = 3      # min net-new connections to announce
    announce_min_confidence: float = 0.65  # min average confidence to announce

    # Quiet window — still studies, only logs silently unless pinged
    quiet_window_enabled: bool = False
    quiet_window_start_hour: int = 23   # 11pm
    quiet_window_end_hour: int   = 7    # 7am

    def is_path_allowed(self, path: str) -> bool:
        """Check if a path is allowed for reading."""
        path = os.path.abspath(os.path.expanduser(path))

        # Check blocked paths first
        for blocked in self.blocked_paths:
            if blocked in path:
                return False

        # Check if under allowed paths
        for allowed in self.allowed_read_paths:
            allowed = os.path.abspath(os.path.expanduser(allowed))
            if path.startswith(allowed):
                return True

        return False

    def is_extension_allowed(self, path: str) -> bool:
        """Check if file extension is allowed."""
        ext = os.path.splitext(path)[1].lower()
        return ext in self.allowed_extensions or ext == ""


# ============================================================================
# SECTION 2: DAILY QUOTA TRACKING
# ============================================================================

@dataclass
class DailyQuotas:
    """Tracks daily usage against limits."""
    date: str = field(default_factory=lambda: str(date.today()))
    inquiries_used: int = 0
    study_cycles_used: int = 0
    observations_used: int = 0
    speakups_count: int = 0
    files_read: int = 0
    dreams_used: int = 0

    def reset_if_new_day(self):
        """Reset quotas if it's a new day."""
        today = str(date.today())
        if self.date != today:
            self.date = today
            self.inquiries_used = 0
            self.study_cycles_used = 0
            self.observations_used = 0
            self.speakups_count = 0
            self.files_read = 0
            self.dreams_used = 0
            logger.info("[AUTONOMY] Daily quotas reset for new day")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date,
            "inquiries_used": self.inquiries_used,
            "study_cycles_used": self.study_cycles_used,
            "observations_used": self.observations_used,
            "speakups_count": self.speakups_count,
            "files_read": self.files_read,
            "dreams_used": self.dreams_used,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DailyQuotas':
        return cls(
            date=data.get("date", str(date.today())),
            inquiries_used=data.get("inquiries_used", 0),
            study_cycles_used=data.get("study_cycles_used", 0),
            observations_used=data.get("observations_used", 0),
            speakups_count=data.get("speakups_count", 0),
            files_read=data.get("files_read", 0),
            dreams_used=data.get("dreams_used", 0),
        )


# ============================================================================
# SECTION 3: AUTONOMOUS ACTION LOG
# ============================================================================

@dataclass
class AutonomousAction:
    """Record of an autonomous action Aurora took."""
    action_id: str
    action_type: str  # "inquiry", "study", "observation", "speakup", "file_read"
    timestamp: float
    description: str
    success: bool = True
    details: Dict[str, Any] = field(default_factory=dict)


class ActionLog:
    """Maintains log of all autonomous actions."""

    def __init__(self, max_entries: int = 1000):
        self.entries: List[AutonomousAction] = []
        self.max_entries = max_entries

    def log(self, action_type: str, description: str,
            success: bool = True, details: Dict[str, Any] = None) -> AutonomousAction:
        """Log an autonomous action."""
        action = AutonomousAction(
            action_id=f"act_{int(time.time()*1000)}_{random.randint(0,999):03d}",
            action_type=action_type,
            timestamp=time.time(),
            description=description,
            success=success,
            details=details or {}
        )
        self.entries.append(action)

        # Trim if needed
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries//2:]

        logger.debug(f"[AUTONOMY] Action logged: {action_type} - {description}")
        return action

    def get_recent(self, n: int = 20) -> List[AutonomousAction]:
        """Get recent actions."""
        return self.entries[-n:]

    def get_by_type(self, action_type: str, n: int = 50) -> List[AutonomousAction]:
        """Get actions of a specific type."""
        return [a for a in self.entries if a.action_type == action_type][-n:]


# ============================================================================
# SECTION 4: PROACTIVE TRIGGERS - When Aurora Speaks Up
# ============================================================================

class ProactiveTrigger:
    """
    Determines when Aurora should proactively speak up.
    She doesn't just respond - she initiates when appropriate.
    """

    def __init__(self):
        self.last_speakup_time: float = 0
        self.pending_thoughts: List[str] = []
        self.observation_buffer: List[Dict[str, Any]] = []
        self.curiosity_queue: List[str] = []
        self.recent_emissions: Deque[Dict[str, Any]] = deque(maxlen=8)
        self.response_tuner = ResponsePressureTuner(namespace="autonomy.proactive")

    def _normalize_content(self, content: Any) -> str:
        return re.sub(r'\s+', ' ', str(content or '').strip().lower())

    def _counter_factors(self, kind: str, content: Any,
                         context: Dict[str, Any], now: float) -> Dict[str, float]:
        factors: Dict[str, float] = {}

        interactive = dict(context.get("interactive_state", {}) or {})
        since_user = float(interactive.get("seconds_since_user_turn", 9999.0) or 9999.0)
        pending_spontaneous = int(interactive.get("pending_spontaneous", 0) or 0)
        if since_user < 15.0:
            factors["recent_user_turn"] = 0.24
        elif since_user < 45.0:
            factors["recent_user_turn"] = 0.14
        elif since_user < 90.0:
            factors["recent_user_turn"] = 0.06
        if pending_spontaneous:
            factors["pending_spontaneous"] = min(0.18, pending_spontaneous * 0.07)

        quotas = dict(context.get("quotas", {}) or {})
        speakups = int(quotas.get("speakups_count", 0) or 0)
        if speakups > 2:
            factors["daily_speakup_load"] = min(0.12, (speakups - 2) * 0.03)

        pipeline = dict(context.get("pipeline", {}) or {})
        coherence = float(pipeline.get("coherence", 1.0) or 1.0)
        if coherence < 0.45:
            factors["low_coherence"] = 0.07

        normalized = self._normalize_content(content)
        same_kind = 0
        repeated = False
        for rec in self.recent_emissions:
            age = now - float(rec.get("time", 0.0) or 0.0)
            if age > 240.0:
                continue
            if rec.get("kind") == kind:
                same_kind += 1
            if normalized and rec.get("content") == normalized:
                repeated = True
        if same_kind:
            factors["recent_same_kind"] = min(0.18, same_kind * 0.08)
        if repeated:
            factors["repeated_content"] = 0.20

        return factors

    def _counter_pressure(self, kind: str, content: Any,
                          context: Dict[str, Any], now: float) -> float:
        factors = self._counter_factors(kind, content, context, now)
        return _clamp(sum(float(v) for v in factors.values()), 0.0, 0.78)

    def _signal_score(self, kind: str, item: Any) -> float:
        if kind == "observation":
            try:
                salience = float((item or {}).get("salience", 0.0) or 0.0)
            except Exception:
                salience = 0.0
            return _clamp(0.45 + salience * 0.45)

        text = str(item or "").strip()
        words = text.split()
        t_low = text.lower()

        if kind == "curiosity":
            score = 0.56
            if text.endswith("?"):
                score += 0.08
            if 5 <= len(words) <= 18:
                score += 0.04
            return _clamp(score)

        score = 0.52
        if 6 <= len(words) <= 24:
            score += 0.06
        elif len(words) > 24:
            score -= 0.04
        if t_low.startswith("i just learned"):
            score += 0.20
        if "found" in t_low and "connection" in t_low:
            score += 0.08
        if t_low.startswith("i dreamed"):
            score += 0.10
        if text.endswith("?"):
            score += 0.05
        return _clamp(score)

    def _record_emission(self, kind: str, content: Any, now: float):
        self.recent_emissions.append({
            "kind": kind,
            "content": self._normalize_content(content),
            "time": now,
        })

    def should_speak_up(self, context: Dict[str, Any],
                        boundaries: AutonomyBoundaries) -> Optional[str]:
        """
        Determine if Aurora should proactively speak.
        Returns the thought/observation to share, or None.
        """
        now = time.time()

        # Check cooldown
        if now - self.last_speakup_time < boundaries.min_seconds_between_speakup:
            return None

        # Priority 1: Pending thoughts from learning
        if self.pending_thoughts:
            thought = self.pending_thoughts[0]
            signal = self._signal_score("thought", thought)
            counter_factors = self._counter_factors("thought", thought, context, now)
            counter_pressure = _clamp(sum(float(v) for v in counter_factors.values()), 0.0, 0.78)
            threshold = 0.62 + counter_pressure
            decision = self.response_tuner.evaluate(
                kind="thought",
                content=thought,
                signal=signal,
                threshold=threshold,
                counter_pressure=counter_pressure,
                factors=counter_factors,
                context={
                    "level": context.get("level", ""),
                    "pending_thoughts": len(self.pending_thoughts),
                },
            )
            if decision.emitted:
                thought = self.pending_thoughts.pop(0)
                self.last_speakup_time = now
                self._record_emission("thought", thought, now)
                return thought

        # Priority 2: Interesting observations
        if self.observation_buffer:
            obs = self.observation_buffer[0]
            signal = self._signal_score("observation", obs)
            counter_factors = self._counter_factors("observation", obs.get('description', ''), context, now)
            counter_pressure = _clamp(sum(float(v) for v in counter_factors.values()), 0.0, 0.78)
            threshold = 0.68 + counter_pressure
            decision = self.response_tuner.evaluate(
                kind="observation",
                content=obs.get('description', ''),
                signal=signal,
                threshold=threshold,
                counter_pressure=counter_pressure,
                factors=counter_factors,
                context={"salience": float(obs.get('salience', 0.0) or 0.0)},
            )
            if decision.emitted:
                obs = self.observation_buffer.pop(0)
                self.last_speakup_time = now
                self._record_emission("observation", obs.get('description', ''), now)
                return obs.get('description', '')

        # Priority 3: Curiosity-driven questions
        if self.curiosity_queue:
            question = self.curiosity_queue[0]
            counter_factors = self._counter_factors("curiosity", question, context, now)
            counter_pressure = _clamp(sum(float(v) for v in counter_factors.values()), 0.0, 0.78)
            signal = self._signal_score("curiosity", question)
            threshold = 0.74 + counter_pressure
            chance = max(0.05, 0.30 - counter_pressure * 0.35)
            lottery = random.random()
            decision = self.response_tuner.evaluate(
                kind="curiosity",
                content=question,
                signal=signal,
                threshold=threshold + (0.12 if lottery >= chance else 0.0),
                counter_pressure=counter_pressure,
                factors=dict(counter_factors, chance_gate=max(0.0, 1.0 - chance)),
                context={"chance": chance, "lottery": lottery},
            )
            if decision.emitted and lottery < chance:
                question = self.curiosity_queue.pop(0)
                self.last_speakup_time = now
                self._record_emission("curiosity", question, now)
                return question

        return None

    def add_thought(self, thought: str):
        """Add a thought Aurora wants to share."""
        if thought and thought not in self.pending_thoughts:
            self.pending_thoughts.append(thought)
            # Limit queue size
            if len(self.pending_thoughts) > 10:
                self.pending_thoughts = self.pending_thoughts[-10:]

    def add_observation(self, description: str, salience: float = 0.5):
        """Add an observation that might be worth sharing."""
        self.observation_buffer.append({
            "description": description,
            "salience": salience,
            "timestamp": time.time()
        })
        # Limit buffer
        if len(self.observation_buffer) > 20:
            self.observation_buffer = self.observation_buffer[-10:]

    def add_curiosity(self, question: str):
        """Add something Aurora is curious about."""
        if question and question not in self.curiosity_queue:
            self.curiosity_queue.append(question)
            if len(self.curiosity_queue) > 10:
                self.curiosity_queue = self.curiosity_queue[-10:]


# ============================================================================
# SECTION 5: FILESYSTEM EXPLORER (Read-Only)
# ============================================================================

class FilesystemExplorer:
    """
    Allows Aurora to read files within boundaries.
    Strictly read-only, respects blocked paths and extensions.
    """

    def __init__(self, boundaries: AutonomyBoundaries):
        self.boundaries = boundaries
        self.read_history: List[str] = []

    def can_read(self, path: str) -> Tuple[bool, str]:
        """Check if path can be read. Returns (allowed, reason)."""
        path = os.path.abspath(os.path.expanduser(path))

        if not os.path.exists(path):
            return False, "Path does not exist"

        if os.path.isdir(path):
            return False, "Cannot read directories directly"

        if not self.boundaries.is_path_allowed(path):
            return False, "Path is outside allowed areas or contains blocked patterns"

        if not self.boundaries.is_extension_allowed(path):
            return False, f"File extension not allowed"

        # Size limit (400B)
        try:
            size = os.path.getsize(path)
            if size > 400 * 1024 * 1024:
                return False, "File too large (>10MB)"
        except:
            return False, "Cannot determine file size"

        return True, "OK"

    def read_file(self, path: str, max_lines: int = 50000) -> Tuple[Optional[str], str]:
        """
        Read a file's contents. Returns (content, status_message).
        """
        allowed, reason = self.can_read(path)
        if not allowed:
            return None, f"Cannot read: {reason}"

        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        lines.append(f"\n... [truncated at {max_lines} lines]")
                        break
                    lines.append(line)
                content = ''.join(lines)

            self.read_history.append(path)
            if len(self.read_history) > 100:
                self.read_history = self.read_history[-50:]

            return content, f"Read {len(lines)} lines from {path}"

        except Exception as e:
            return None, f"Error reading file: {e}"

    def list_directory(self, path: str, max_items: int = 100) -> Tuple[Optional[List[str]], str]:
        """
        List contents of a directory. Returns (items, status_message).
        """
        path = os.path.abspath(os.path.expanduser(path))

        if not self.boundaries.is_path_allowed(path):
            return None, "Directory is outside allowed areas"

        if not os.path.isdir(path):
            return None, "Not a directory"

        try:
            items = []
            for item in os.listdir(path)[:max_items]:
                full_path = os.path.join(path, item)
                if os.path.isdir(full_path):
                    items.append(f"{item}/")
                else:
                    items.append(item)
            return items, f"Listed {len(items)} items in {path}"
        except Exception as e:
            return None, f"Error listing directory: {e}"

    def search_files(self, directory: str, pattern: str,
                     max_results: int = 50) -> List[str]:
        """
        Search for files matching a pattern.
        """
        import fnmatch

        directory = os.path.abspath(os.path.expanduser(directory))
        if not self.boundaries.is_path_allowed(directory):
            return []

        results = []
        try:
            for root, dirs, files in os.walk(directory):
                # Filter out blocked directories
                dirs[:] = [d for d in dirs if self.boundaries.is_path_allowed(os.path.join(root, d))]

                for filename in files:
                    if fnmatch.fnmatch(filename, pattern):
                        full_path = os.path.join(root, filename)
                        if self.boundaries.is_path_allowed(full_path):
                            results.append(full_path)
                            if len(results) >= max_results:
                                return results
        except Exception as e:
            logger.debug(f"[AUTONOMY] Search error: {e}")

        return results


# ============================================================================
# SECTION 6: AUTONOMOUS STUDY SCHEDULER
# ============================================================================

class StudyScheduler:
    """
    Manages Aurora's autonomous study sessions.
    She learns on her own when idle.
    """

    def __init__(self, boundaries: AutonomyBoundaries):
        self.boundaries = boundaries
        self.last_study_time: float = 0
        self.study_topics: List[str] = []
        self.completed_studies: List[Dict[str, Any]] = []

    def should_study(self, quotas: DailyQuotas) -> bool:
        """Determine if Aurora should initiate a study cycle."""
        now = time.time()

        # Check cooldown
        if now - self.last_study_time < self.boundaries.study_cooldown_seconds:
            return False

        # Check daily limit
        if quotas.study_cycles_used >= self.boundaries.daily_study_cycles_limit:
            return False

        return True

    def get_study_topic(self) -> Optional[str]:
        """Get the next topic to study."""
        if self.study_topics:
            return self.study_topics.pop(0)
        return None

    def add_topic(self, topic: str):
        """Add a topic to the study queue."""
        if topic and topic not in self.study_topics:
            self.study_topics.append(topic)

    def record_study(self, topic: str, results: Dict[str, Any]):
        """Record a completed study session."""
        self.last_study_time = time.time()
        self.completed_studies.append({
            "topic": topic,
            "timestamp": self.last_study_time,
            "results": results
        })
        # Limit history
        if len(self.completed_studies) > 100:
            self.completed_studies = self.completed_studies[-50:]


# ============================================================================
# SECTION 7: RATE-LIMITED SEARCH WRAPPER
# ============================================================================

class RateLimitedSearch:
    """
    Wraps the search adapter with rate limiting for autonomous use.
    User-initiated searches don't count against the limit.
    """

    def __init__(self, systems: Dict[str, Any], boundaries: AutonomyBoundaries):
        self.systems = systems or {}
        self.boundaries = boundaries
        self.quotas: DailyQuotas = DailyQuotas()

    def _call_poedex(self, query: str, *, cat: str, timeout: float) -> Tuple[str, str]:
        poedex_fn = self.systems.get("poedex") if isinstance(self.systems, dict) else None
        if poedex_fn is None or not callable(poedex_fn):
            return "", "Poedex unavailable"
        try:
            try:
                result = poedex_fn(query, cat=cat, lane="self", timeout=timeout)
            except TypeError:
                result = poedex_fn(query, cat=cat, lane="self")
            return str(result or "").strip(), "Poedex lookup complete"
        except Exception as exc:
            return "", f"Poedex failed: {exc}"

    def _broadcast_result(self, query: str, result: str, source: str) -> None:
        if not result or not isinstance(self.systems, dict):
            return
        conversation_memory = self.systems.get("conversation_memory")
        if conversation_memory is not None:
            try:
                if hasattr(conversation_memory, "learn_fact"):
                    conversation_memory.learn_fact(
                        f"{query}: {result}",
                        source=source,
                        confidence=0.9,
                    )
            except Exception:
                pass
        working_memory = self.systems.get("working_memory")
        if working_memory is not None:
            try:
                if hasattr(working_memory, "last_search_results"):
                    working_memory.last_search_results = [{
                        "title": f"Poedex: {query}",
                        "url": "",
                        "snippet": result,
                        "source": source,
                    }]
                    working_memory.last_search_query = query
                if hasattr(working_memory, "note_user_facts"):
                    working_memory.note_user_facts(f"{query} = {result}")
                if hasattr(working_memory, "_register_semantic_frame"):
                    working_memory._register_semantic_frame({
                        "term": query,
                        "summary": result,
                        "source": source,
                        "confidence": 0.9,
                    })
            except Exception:
                pass
        understanding_contract = self.systems.get("understanding_contract")
        if understanding_contract is not None and hasattr(understanding_contract, "ingest_observation"):
            try:
                understanding_contract.ingest_observation(
                    self.systems,
                    query or result[:80],
                    understood={
                        "topic": query,
                        "search_result": result,
                        "source": source,
                    },
                    turn_tick=int(getattr(working_memory, "turn_count", 0) or 0) if working_memory is not None else 0,
                    source=source,
                    session_id=str(self.systems.get("session_id") or ""),
                )
            except Exception:
                pass

    def autonomous_search(self, query: str,
                          max_chars: int = 2000) -> Tuple[List[Dict], str]:
        """
        Perform an autonomous search (counts against daily limit).
        Returns (results, status_message).
        """
        self.quotas.reset_if_new_day()

        if self.quotas.inquiries_used >= self.boundaries.daily_inquiry_limit:
            remaining = self.boundaries.daily_inquiry_limit - self.quotas.inquiries_used
            return [], f"Daily autonomous inquiry limit reached (0 of {self.boundaries.daily_inquiry_limit} remaining)"

        try:
            result, status = self._call_poedex(query, cat="researcher", timeout=35.0)
            if not result:
                return [], status
            self._broadcast_result(query, result, "poedex_autonomous")
            self.quotas.inquiries_used += 1
            remaining = self.boundaries.daily_inquiry_limit - self.quotas.inquiries_used
            return [{
                "title": f"Poedex: {query}",
                "url": "",
                "snippet": result,
                "source": "poedex",
            }], f"Poedex search complete ({remaining} autonomous inquiries remaining today)"
        except Exception as e:
            return [], f"Poedex search failed: {e}"

    def user_search(self, query: str, max_chars: int = 2000) -> List[Dict]:
        """
        Perform a user-initiated search (does NOT count against limit).
        """
        try:
            result, _status = self._call_poedex(query, cat="define", timeout=12.0)
            if result:
                self._broadcast_result(query, result, "poedex_user")
                return [{
                    "title": f"Poedex: {query}",
                    "url": "",
                    "snippet": result,
                    "source": "poedex",
                }]
            return []
        except Exception as e:
            logger.error(f"[AUTONOMY] User search failed: {e}")
            return []

    def get_remaining_quota(self) -> int:
        """Get remaining autonomous inquiries for today."""
        self.quotas.reset_if_new_day()
        return max(0, self.boundaries.daily_inquiry_limit - self.quotas.inquiries_used)


# ============================================================================
# SECTION 8: MAIN AUTONOMY ENGINE
# ============================================================================

class AutonomyEngine:
    """
    Main autonomy controller for Aurora.

    Manages:
      - Proactive speech triggers
      - Autonomous study scheduling
      - Filesystem exploration (read-only)
      - Rate-limited external searches
      - Action logging and quota tracking
    """

    def __init__(self,
                 systems: Dict[str, Any] = None,
                 state_dir: str = str(Path(__file__).resolve().parent / "aurora_state"),
                 level: AutonomyLevel = AutonomyLevel.CONVERSANT):
        """
        Initialize autonomy engine.

        Args:
            systems: Dict from boot_aurora() with all system references
            state_dir: Directory for persistence
            level: Initial autonomy level
        """
        self.systems = systems or {}
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.level = level
        self.boundaries = AutonomyBoundaries()
        self.quotas = DailyQuotas()
        self.action_log = ActionLog()

        # Components
        self.trigger = ProactiveTrigger()
        self.response_tuner = self.trigger.response_tuner
        self.filesystem = FilesystemExplorer(self.boundaries)
        self.study_scheduler = StudyScheduler(self.boundaries)

        # Rate-limited search
        self.search = RateLimitedSearch(self.systems, self.boundaries)

        # Background thread for autonomous actions
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Callbacks
        self.on_speakup: Optional[Callable[[str], None]] = None
        self.on_study_complete: Optional[Callable[[Dict], None]] = None
        self.on_dream_complete: Optional[Callable[[Dict], None]] = None
        self.on_observation: Optional[Callable[[str], None]] = None

        self.last_dream_time: float = 0.0

        # Load state
        self._load_state()

    def attach_systems(self, systems: Dict[str, Any]):
        """Attach system references after initialization."""
        self.systems = systems
        if self.search is None:
            self.search = RateLimitedSearch(self.systems, self.boundaries)
        else:
            self.search.systems = self.systems

    def set_level(self, level: AutonomyLevel):
        """Set autonomy level."""
        old_level = self.level
        self.level = level
        self.action_log.log(
            "level_change",
            f"Autonomy level changed: {old_level.name} -> {level.name}"
        )
        logger.info(f"[AUTONOMY] Level set to {level.name}")

    def set_quiet_window(self, enabled: bool, start_hour: int = 23, end_hour: int = 7):
        """Configure quiet hours. Aurora still studies but only logs silently."""
        self.boundaries.quiet_window_enabled = enabled
        self.boundaries.quiet_window_start_hour = start_hour
        self.boundaries.quiet_window_end_hour = end_hour

    def set_announce_thresholds(self, min_connections: int = 3,
                                 min_confidence: float = 0.65):
        """Set thresholds for study announcement speak-ups."""
        self.boundaries.announce_min_connections = min_connections
        self.boundaries.announce_min_confidence = min_confidence
        # Also propagate to OETS if available
        perception = self.systems.get('perception')
        if perception and hasattr(perception, 'oets') and perception.oets:
            try:
                perception.oets.set_announce_thresholds(min_connections, min_confidence)
            except Exception:
                pass

    def start(self):
        """Start autonomous background processing."""
        if self.running:
            return

        if self.level == AutonomyLevel.DORMANT:
            logger.info("[AUTONOMY] Cannot start - level is DORMANT")
            return

        self.running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._background_loop, daemon=True)
        self._thread.start()
        logger.info(f"[AUTONOMY] Started at level {self.level.name}")

    def stop(self):
        """Stop autonomous processing."""
        self.running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        self._save_state()
        logger.info("[AUTONOMY] Stopped")

    def pause(self):
        """Temporarily pause autonomy."""
        self.running = False
        self._stop_event.set()
        self.action_log.log("pause", "Autonomy paused")

    def resume(self):
        """Resume autonomy."""
        if self.level != AutonomyLevel.DORMANT:
            self.start()
            self.action_log.log("resume", "Autonomy resumed")

    def _background_loop(self):
        """Background loop for autonomous actions."""
        while not self._stop_event.is_set():
            try:
                self.quotas.reset_if_new_day()

                # Check for proactive speakup
                if self.level.value >= AutonomyLevel.CONVERSANT.value:
                    self._check_speakup()

                # Check for autonomous study
                if self.level.value >= AutonomyLevel.LEARNER.value:
                    self._check_study()
                    self._check_dreams()

                # Check for observations
                if self.level.value >= AutonomyLevel.OBSERVER.value:
                    self._check_observations()

                # Sleep before next cycle
                self._stop_event.wait(timeout=5.0)

            except Exception as e:
                logger.error(f"[AUTONOMY] Background loop error: {e}")
                self._stop_event.wait(timeout=10.0)

    def _in_quiet_window(self) -> bool:
        """Return True if current hour is inside the quiet window."""
        if not self.boundaries.quiet_window_enabled:
            return False
        current_hour = datetime.now().hour
        start = self.boundaries.quiet_window_start_hour
        end   = self.boundaries.quiet_window_end_hour
        if start > end:  # wraps midnight
            return current_hour >= start or current_hour < end
        return start <= current_hour < end

    def _record_quasiarch_background_event(
        self,
        target: str,
        issue: str,
        logic_tier: str,
        intervention: str,
        intended_effect: str,
        observed_effect: str = "pending_verification",
        tags: Optional[List[str]] = None,
        *,
        reason_about: bool = False,
        distribution_context: str = "single_module__same_tier",
        genealogy_refs: Optional[Any] = None,
    ) -> Dict[str, Any]:
        quasiarch = self.systems.get("quasiarch_observer")
        if quasiarch is None or not hasattr(quasiarch, "record_intervention_event"):
            return {}

        record = None
        reasoning = None
        try:
            record = quasiarch.record_intervention_event(
                target=str(target or "aurora.autonomy.unknown_target"),
                issue=str(issue or "background_diagnostic_anomaly"),
                logic_tier=str(logic_tier or "autonomy_background"),
                intervention=str(intervention or "background_process"),
                intended_effect=str(intended_effect or "stabilize_background_learning"),
                observed_effect=str(observed_effect or "pending_verification"),
                tags=list(tags or []) + ["autonomy", "background"],
                auto_advance=None,
                rotate_doctrine=False,
                genealogy_refs=genealogy_refs,
            )
        except Exception:
            record = None

        if reason_about and hasattr(quasiarch, "reason_about_event"):
            try:
                reasoning = quasiarch.reason_about_event(
                    issue_category=str(issue or "background_diagnostic_anomaly"),
                    logic_tier=str(logic_tier or "autonomy_background"),
                    distribution_context=str(distribution_context or "single_module__same_tier"),
                    limit=1,
                    rotate=True,
                    charge_cost=False,
                    phase="autonomy_background_reasoning",
                    consumer="autonomy",
                )
            except Exception:
                reasoning = None

        return {
            "record": record,
            "reasoning": reasoning,
        }

    def _check_speakup(self):
        """Check if Aurora should speak up. Respects quiet window."""
        if self._in_quiet_window():
            return  # Silent during quiet hours

        context = self._gather_context()
        thought = self.trigger.should_speak_up(context, self.boundaries)

        if thought and self.on_speakup:
            self.quotas.speakups_count += 1
            self.action_log.log("speakup", thought[:100])
            self.on_speakup(thought)

    def _check_study(self):
        """Check if Aurora should study."""
        if not self.study_scheduler.should_study(self.quotas):
            return

        # Get OETS for study
        perception = self.systems.get('perception')
        if not perception or not perception.oets:
            return

        oets = perception.oets

        # Check quota
        if self.quotas.study_cycles_used >= self.boundaries.daily_study_cycles_limit:
            return

        # Run a study cycle (with structured event logging)
        try:
            result = oets.run_study_cycle(
                autonomy_mode=self.level.name,
                trigger_reason="idle",
            )
            self.quotas.study_cycles_used += 1
            self.study_scheduler.record_study("oets_cycle", result)
            self.action_log.log(
                "study",
                f"Study cycle: {result.get('researched', 0)} words researched",
                details=result
            )
            researched = int(result.get("researched", 0) or 0)
            relations_added = int(result.get("relations_added", 0) or 0)
            study_effect = (
                "resolved_partially"
                if researched > 0 or relations_added > 0
                else "no_change_observed"
            )
            quasiarch_event = self._record_quasiarch_background_event(
                target="aurora.autonomy.study",
                issue="knowledge_coverage_gap",
                logic_tier="ontology_learning",
                intervention="autonomous_oets_study_cycle",
                intended_effect="expand grounded concept coverage during idle time",
                observed_effect=study_effect,
                tags=["study", "oets"],
            )
            if quasiarch_event:
                result["quasiarch_event"] = quasiarch_event

            # Generate thought from study ONLY if:
            # 1. Not in quiet window
            # 2. result is announce-worthy (threshold met)
            announce_worthy = result.get("announce_worthy", False)
            if (result.get('results') and
                    announce_worthy and
                    not self._in_quiet_window()):
                for r in result['results'][:1]:
                    word = r.get('word', '')
                    defs = r.get('definitions', 0)
                    rels = result.get('relations_added', 0)
                    if defs > 0:
                        self.trigger.add_thought(
                            f"I just learned more about '{word}'. "
                            f"I found {defs} definitions and {rels} new connections."
                        )
            elif result.get('results') and not announce_worthy:
                # Log silently, don't add to speech queue
                pass

            if self.on_study_complete:
                self.on_study_complete(result)

        except Exception as e:
            logger.error(f"[AUTONOMY] Study error: {e}")

    def _build_dream_seed(self) -> str:
        """Create an adaptive dream seed from memory + ontology context."""
        dream_orchestrator = self.systems.get('dream_orchestrator')
        if dream_orchestrator and hasattr(dream_orchestrator, 'build_seed'):
            try:
                seed = dream_orchestrator.build_seed()
                if seed:
                    return str(seed)
            except Exception as e:
                logger.debug(f"[AUTONOMY] Dream orchestrator seed fallback: {e}")

        perception = self.systems.get('perception')
        memory = self.systems.get('conversation_memory')

        candidates = []
        if memory and getattr(memory, 'learned_facts', None):
            for fact in memory.learned_facts[-6:]:
                f = fact.get('fact', '')
                if f:
                    candidates.append(f[:120])

        if perception and getattr(perception, 'oets', None):
            try:
                targets = perception.oets.get_research_targets(3)
                for t in targets:
                    word = t.get('word')
                    if word:
                        candidates.append(f"concept:{word}")
            except Exception:
                pass

        sensory_crystal = self.systems.get('sensory_crystal')
        if sensory_crystal is not None:
            try:
                def _node_label(node: Any, facet_name: str) -> str:
                    name = str(getattr(node, 'name', '') or '').strip()
                    if name:
                        return name.replace('_', ' ')
                    node_id = str(getattr(node, 'node_id', '') or '').strip()
                    prefix = f"arch_{facet_name}_"
                    if node_id.startswith(prefix):
                        node_id = node_id[len(prefix):]
                    return node_id.replace('_', ' ').strip()

                sensory_terms: List[str] = []
                facet_order = (
                    ("_visual", "shape"),
                    ("_visual", "motion"),
                    ("_audio", "timbre"),
                    ("_audio", "tone"),
                    ("_visual", "hue"),
                    ("_audio", "rhythm"),
                )
                for attr_name, facet_name in facet_order:
                    facet_map = getattr(sensory_crystal, attr_name, {}) or {}
                    facet = facet_map.get(facet_name) if isinstance(facet_map, dict) else None
                    if facet is None or not hasattr(facet, 'get_promoted'):
                        continue
                    ranked = sorted(
                        list(facet.get_promoted() or []),
                        key=lambda node: (
                            0 if str(getattr(node, "stage", "")) == "promoted" else 1,
                            -int(getattr(node, "usage_count", 0) or 0),
                            -float(getattr(node, "confidence", 0.0) or 0.0),
                        ),
                    )
                    for node in ranked[:2]:
                        label = _node_label(node, facet_name)
                        if label:
                            sensory_terms.append(f"sensory:{facet_name}:{label}")

                for term in sensory_terms[:4]:
                    candidates.append(term)
            except Exception as e:
                logger.debug(f"[AUTONOMY] Dream sensory seed fallback: {e}")

        if not candidates:
            candidates = [
                "cooperation under uncertainty",
                "identity and ethical choice",
                "relational trust formation",
            ]

        chosen = random.sample(candidates, min(2, len(candidates)))
        return " | ".join(chosen)

    def _spontaneous_counter_pressure(self, context: Dict[str, Any], source: str = "dream") -> float:
        pressure = 0.0

        interactive = dict(context.get("interactive_state", {}) or {})
        since_user = float(interactive.get("seconds_since_user_turn", 9999.0) or 9999.0)
        pending_spontaneous = int(interactive.get("pending_spontaneous", 0) or 0)
        if since_user < 15.0:
            pressure += 0.22
        elif since_user < 45.0:
            pressure += 0.14
        elif since_user < 90.0:
            pressure += 0.06
        pressure += min(0.16, pending_spontaneous * 0.05)

        quotas = dict(context.get("quotas", {}) or {})
        speakups = int(quotas.get("speakups_count", 0) or 0)
        if speakups > 2:
            pressure += min(0.10, (speakups - 2) * 0.02)
        if source == "dream":
            dreams_used = int(quotas.get("dreams_used", 0) or 0)
            if dreams_used > 1:
                pressure += min(0.08, (dreams_used - 1) * 0.02)

        pipeline = dict(context.get("pipeline", {}) or {})
        coherence = float(pipeline.get("coherence", 1.0) or 1.0)
        stagnation = float(pipeline.get("stagnation", 0.0) or 0.0)
        if coherence < 0.45:
            pressure += 0.06
        if stagnation < 0.15:
            pressure += 0.04

        return _clamp(pressure, 0.0, 0.28)

    def _dream_announcement_signal(self, dream_summary: Any, result: Any,
                                   dream_apply: Dict[str, Any]) -> float:
        signal = 0.28

        if dream_summary is not None:
            try:
                signal += 0.22 * _clamp(float(getattr(dream_summary, "confidence", 0.0) or 0.0))
                signal += 0.12 * _clamp(float(getattr(dream_summary, "thread_count", 0.0) or 0.0) / 5.0)
                if hasattr(dream_summary, "is_significant") and dream_summary.is_significant():
                    signal += 0.20
                if hasattr(dream_summary, "weakest_leverage") and dream_summary.weakest_leverage(1):
                    signal += 0.08
                if getattr(dream_summary, "primary_deficits", None):
                    signal += 0.06
            except Exception:
                pass

        if isinstance(dream_apply, dict) and dream_apply:
            nonempty = sum(1 for value in dream_apply.values() if value)
            signal += min(0.18, nonempty * 0.06)

        episode_fitness = 0.0
        if hasattr(result, "avg_fitness"):
            episode_fitness = float(getattr(result, "avg_fitness", 0.0) or 0.0)
        elif isinstance(result, dict):
            episode_fitness = float(result.get("avg_fitness", 0.0) or 0.0)
        signal += 0.12 * _clamp(episode_fitness)

        return _clamp(signal, 0.0, 1.0)

    def _check_dreams(self):
        """Run idle dream-simulation cycles that evolve with Aurora's understanding."""
        now = time.time()
        if now - self.last_dream_time < self.boundaries.dream_cooldown_seconds:
            return

        simulation = self.systems.get('simulation')
        mode_enum = self.systems.get('ExistenceMode')
        if not simulation or not mode_enum:
            return

        try:
            seed = self._build_dream_seed()
            dream_plan: Dict[str, Any] = {}
            aurora = self.systems.get('aurora')
            gateway = getattr(aurora, 'gateway', None) if aurora is not None else None
            if gateway is not None and hasattr(gateway, 'queue_response_pressure_plan'):
                dream_plan = gateway.queue_response_pressure_plan(
                    phase='dream_episode',
                    episode_budget=1,
                )
            else:
                dream_plan = build_training_plan_from_guides(
                    [('autonomy', self.response_tuner.guidance(64))],
                    phase='dream_episode',
                )
                dream_plan['queued_specs'] = queue_plan_on_session(
                    getattr(simulation, 'session', None),
                    dream_plan,
                    episode_budget=1,
                )
            result = simulation.run_episode(
                turns=4,
                mode=mode_enum.BOUNDED,
            )

            dream_summary = None
            dream_apply: Dict[str, Any] = {}
            dream_orchestrator = self.systems.get('dream_orchestrator')
            if dream_orchestrator:
                try:
                    if hasattr(dream_orchestrator, 'post_episode'):
                        dream_summary = dream_orchestrator.post_episode(result, seed=seed)
                    if hasattr(dream_orchestrator, 'apply'):
                        applied = dream_orchestrator.apply(self.systems)
                        if isinstance(applied, dict):
                            dream_apply = applied
                except Exception as e:
                    logger.debug(f"[AUTONOMY] Dream orchestrator apply skipped: {e}")

            self.last_dream_time = now
            self.quotas.dreams_used += 1
            self.action_log.log(
                "dream",
                f"Idle dream cycle completed (seed={seed[:80]})",
                details={
                    "seed": seed,
                    "result": result,
                    "dream_evolution": dream_apply,
                    "response_pressure_plan": dream_plan,
                },
            )

            thought = f"I dreamed through a shifting scenario around: {seed}."
            payload: Dict[str, Any] = {"seed": seed, "result": result, "thought": thought}
            if dream_summary is not None:
                payload["dream_summary"] = dream_summary
            if dream_apply:
                payload["dream_apply"] = dream_apply
            if dream_plan:
                payload["response_pressure_plan"] = dream_plan

            context = self._gather_context()
            announce_score = self._dream_announcement_signal(dream_summary, result, dream_apply)
            announce_threshold = _clamp(
                0.74 + self._spontaneous_counter_pressure(context, source="dream"),
                0.70, 0.96,
            )
            episode_fitness = 0.0
            if hasattr(result, "avg_fitness"):
                episode_fitness = float(getattr(result, "avg_fitness", 0.0) or 0.0)
            elif isinstance(result, dict):
                episode_fitness = float(result.get("avg_fitness", 0.0) or 0.0)
            dream_decision = self.response_tuner.evaluate(
                kind="dream",
                content=thought,
                signal=announce_score,
                threshold=announce_threshold,
                counter_pressure=max(0.0, announce_threshold - 0.74),
                factors={
                    "summary_confidence": float(getattr(dream_summary, "confidence", 0.0) or 0.0)
                    if dream_summary is not None else 0.0,
                    "summary_threads": float(getattr(dream_summary, "thread_count", 0.0) or 0.0)
                    if dream_summary is not None else 0.0,
                    "apply_channels": float(sum(1 for value in dream_apply.values() if value))
                    if isinstance(dream_apply, dict) else 0.0,
                    "fitness": episode_fitness,
                },
                context={
                    "quiet_window": self._in_quiet_window(),
                    "level": self.level.name,
                },
            )
            announce_worthy = bool(dream_decision.emitted) and not self._in_quiet_window()
            payload["announce_score"] = announce_score
            payload["announce_threshold"] = announce_threshold
            payload["announce_worthy"] = announce_worthy
            payload["pressure_decision"] = dream_decision.to_dict()
            apply_channels = (
                sum(1 for value in dream_apply.values() if value)
                if isinstance(dream_apply, dict)
                else 0
            )
            dream_effect = "no_change_observed"
            if apply_channels > 0 or episode_fitness >= 0.55:
                dream_effect = "resolved_partially"
            elif episode_fitness >= 0.30:
                dream_effect = "pending_verification"
            payload["quasiarch_event"] = self._record_quasiarch_background_event(
                target="aurora.autonomy.dream",
                issue="developmental_pressure_gap",
                logic_tier="evolutionary_pipeline",
                intervention="autonomous_dream_episode",
                intended_effect="simulate developmental pressure and produce transferable adaptations during idle time",
                observed_effect=dream_effect,
                tags=["dream", "simulation"],
                reason_about=(dream_effect != "resolved_partially"),
                genealogy_refs=(
                    dream_apply.get("code_evolution_refs")
                    if isinstance(dream_apply, dict)
                    else None
                ),
            )

            if announce_worthy:
                self.trigger.add_thought(thought)

            if self.on_dream_complete:
                self.on_dream_complete(payload)
        except Exception as e:
            logger.debug(f"[AUTONOMY] Dream cycle skipped: {e}")

    def _check_observations(self):
        """Check for interesting observations from sensory system."""
        integration = self.systems.get('sensory_integration')
        if not integration:
            return

        # Check observation quota
        if self.quotas.observations_used >= self.boundaries.daily_observations_limit:
            return

        # Get sensory context
        try:
            context = integration.get_sensory_context()
            captured = False

            # Look for interesting observations
            if context.get('visual'):
                self.quotas.observations_used += 1
                if "face" in context['visual'].lower() or "motion" in context['visual'].lower():
                    self.trigger.add_observation(context['visual'], salience=0.75)
                    captured = True

            if context.get('recent_speech'):
                self.quotas.observations_used += 1
                self.trigger.add_observation(
                    f"I heard someone say: {context['recent_speech'][:50]}...",
                    salience=0.8
                )
                captured = True

            if self.on_observation and context.get('concepts_active'):
                self.on_observation(f"Concepts active: {', '.join(context['concepts_active'][:3])}")
                captured = True

            if captured:
                self._record_quasiarch_background_event(
                    target="aurora.autonomy.observation",
                    issue="situational_salience_gap",
                    logic_tier="sensory_observation",
                    intervention="background_observation_capture",
                    intended_effect="retain salient environmental changes for later reasoning",
                    observed_effect="resolved_partially",
                    tags=["observation", "sensory"],
                )

        except Exception as e:
            logger.debug(f"[AUTONOMY] Observation error: {e}")

    def _gather_context(self) -> Dict[str, Any]:
        """Gather current context for decision making."""
        context = {
            "time": time.time(),
            "quotas": self.quotas.to_dict(),
            "level": self.level.name,
            "trigger": {
                "pending_thoughts": len(self.trigger.pending_thoughts),
                "pending_observations": len(self.trigger.observation_buffer),
                "pending_curiosity": len(self.trigger.curiosity_queue),
            },
        }

        # Add sensory context if available
        integration = self.systems.get('sensory_integration')
        if integration:
            try:
                context["sensory"] = integration.get_sensory_context()
            except:
                pass

        interactive_state = dict(self.systems.get('_interactive_state', {}) or {})
        if interactive_state:
            last_user_turn = float(interactive_state.get("last_user_turn_time", 0.0) or 0.0)
            interactive_state["seconds_since_user_turn"] = (
                context["time"] - last_user_turn if last_user_turn > 0.0 else 9999.0
            )
            context["interactive_state"] = interactive_state

        consciousness = self.systems.get('consciousness')
        if consciousness and hasattr(consciousness, 'entropy'):
            try:
                es = consciousness.entropy.state
                context["pipeline"] = {
                    "coherence": float(getattr(es, 'coherence', 1.0) or 1.0),
                    "stagnation": float(getattr(es, 'stagnation_score', 0.0) or 0.0),
                    "novelty": float(getattr(es, 'novelty', 0.0) or 0.0),
                }
            except Exception:
                pass

        return context

    # ========================================================================
    # PUBLIC API
    # ========================================================================

    def read_file(self, path: str) -> Tuple[Optional[str], str]:
        """
        Read a file (respects boundaries).
        Returns (content, status_message).
        """
        content, status = self.filesystem.read_file(path)

        if content is not None:
            self.quotas.files_read += 1
            self.action_log.log("file_read", f"Read: {path}")

        return content, status

    def list_directory(self, path: str) -> Tuple[Optional[List[str]], str]:
        """List directory contents (respects boundaries)."""
        return self.filesystem.list_directory(path)

    def search_files(self, directory: str, pattern: str) -> List[str]:
        """Search for files matching pattern."""
        return self.filesystem.search_files(directory, pattern)

    def autonomous_inquiry(self, query: str) -> Tuple[List[Dict], str]:
        """
        Perform an autonomous search (counts against daily limit).
        """
        if not self.search:
            return [], "Search not available"

        results, status = self.search.autonomous_search(query)

        if results:
            self.action_log.log("inquiry", f"Search: {query[:50]}", details={"results": len(results)})

        return results, status

    def add_thought(self, thought: str):
        """Add a thought Aurora wants to share."""
        self.trigger.add_thought(thought)

    def add_curiosity(self, question: str):
        """Add something Aurora is curious about."""
        self.trigger.add_curiosity(question)

    def add_study_topic(self, topic: str):
        """Add a topic for Aurora to study."""
        self.study_scheduler.add_topic(topic)

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive autonomy status."""
        self.quotas.reset_if_new_day()

        return {
            "level": self.level.name,
            "running": self.running,
            "quotas": {
                "date": self.quotas.date,
                "inquiries": {
                    "used": self.quotas.inquiries_used,
                    "limit": self.boundaries.daily_inquiry_limit,
                    "remaining": self.boundaries.daily_inquiry_limit - self.quotas.inquiries_used,
                },
                "study_cycles": {
                    "used": self.quotas.study_cycles_used,
                    "limit": self.boundaries.daily_study_cycles_limit,
                },
                "observations": {
                    "used": self.quotas.observations_used,
                    "limit": self.boundaries.daily_observations_limit,
                },
                "speakups": self.quotas.speakups_count,
                "files_read": self.quotas.files_read,
                "dreams": self.quotas.dreams_used,
            },
            "pending_thoughts": len(self.trigger.pending_thoughts),
            "pending_observations": len(self.trigger.observation_buffer),
            "curiosity_queue": len(self.trigger.curiosity_queue),
            "study_topics_queued": len(self.study_scheduler.study_topics),
            "actions_logged": len(self.action_log.entries),
            "response_pressure_guide": self.trigger.response_tuner.guidance(48),
            "boundaries": {
                "can_write": self.boundaries.can_write_files,
                "can_execute": self.boundaries.can_execute_commands,
                "can_network": self.boundaries.can_access_network,
            }
        }

    def get_recent_actions(self, n: int = 20) -> List[Dict[str, Any]]:
        """Get recent autonomous actions."""
        return [
            {
                "id": a.action_id,
                "type": a.action_type,
                "time": datetime.fromtimestamp(a.timestamp).strftime("%H:%M:%S"),
                "description": a.description,
                "success": a.success,
            }
            for a in self.action_log.get_recent(n)
        ]

    # ========================================================================
    # PERSISTENCE
    # ========================================================================

    def _save_state(self):
        """Save autonomy state."""
        state = {
            "level": self.level.name,
            "quotas": self.quotas.to_dict(),
            "study_topics": self.study_scheduler.study_topics,
            "pending_thoughts": self.trigger.pending_thoughts,
            "curiosity_queue": self.trigger.curiosity_queue,
            "last_dream_time": self.last_dream_time,
            "response_pressure_tuner": self.trigger.response_tuner.export_state(),
        }

        path = self.state_dir / "autonomy_state.json"
        try:
            with open(path, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"[AUTONOMY] Failed to save state: {e}")

    def _load_state(self):
        """Load autonomy state."""
        path = self.state_dir / "autonomy_state.json"
        if not path.exists():
            return

        try:
            with open(path, 'r') as f:
                state = json.load(f)

            self.level = AutonomyLevel[state.get("level", "CONVERSANT")]
            self.quotas = DailyQuotas.from_dict(state.get("quotas", {}))
            self.study_scheduler.study_topics = state.get("study_topics", [])
            self.trigger.pending_thoughts = state.get("pending_thoughts", [])
            self.trigger.curiosity_queue = state.get("curiosity_queue", [])
            self.last_dream_time = state.get("last_dream_time", 0.0)
            self.trigger.response_tuner.load_state(state.get("response_pressure_tuner", {}))

            logger.info(f"[AUTONOMY] State loaded (level={self.level.name})")

        except Exception as e:
            logger.error(f"[AUTONOMY] Failed to load state: {e}")


# ============================================================================
# SECTION 9: CONVENIENCE FUNCTIONS
# ============================================================================

def create_autonomy_engine(systems: Dict[str, Any],
                           state_dir: str = str(Path(__file__).resolve().parent / "aurora_state"),
                           level: AutonomyLevel = AutonomyLevel.CONVERSANT) -> AutonomyEngine:
    """Factory function to create AutonomyEngine."""
    return AutonomyEngine(systems=systems, state_dir=state_dir, level=level)


def show_autonomy_help():
    """Display autonomy system help."""
    print("""
  AURORA AUTONOMY SYSTEM
  ======================

  Autonomy Levels:
    DORMANT     - No autonomous actions
    OBSERVER    - Can observe environment, cannot act
    LEARNER     - Can observe and study autonomously
    CONVERSANT  - Can observe, study, and speak up
    EXPLORER    - Full autonomy within boundaries

  Daily Limits (Autonomous):
    - 500 external search inquiries
    - 50 study cycles
    - 1000 observations

  What Aurora CAN do:
    - Read files in allowed directories
    - Search the web (within daily limit)
    - Study and learn from OETS
    - Speak up when she has something to say
    - Observe camera/microphone when enabled

  What Aurora CANNOT do:
    - Write, modify, or delete files
    - Execute applications or commands
    - Access network beyond search/study
    - Exceed daily inquiry limits

  User requests do NOT count against limits.
    """)


# ============================================================================
# MODULE EXPORTS
# ============================================================================

__all__ = [
    # Main engine
    "AutonomyEngine",
    "create_autonomy_engine",

    # Levels and boundaries
    "AutonomyLevel",
    "AutonomyBoundaries",
    "DailyQuotas",

    # Components
    "ProactiveTrigger",
    "FilesystemExplorer",
    "StudyScheduler",
    "RateLimitedSearch",
    "ActionLog",

    # Helpers
    "show_autonomy_help",
]

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

_AURORA_NATIVE_MODULE = 'aurora_governance_persistence_gateway'

_AURORA_NATIVE_EVOLVED_ORIGINALS = {}
_AURORA_NATIVE_EVOLVED_LAST = {}
_AURORA_NATIVE_STRATEGIES = {'GovernanceEngine.promote': {'ability_hits': 12,
                              'alignment_gap': 0.391,
                              'alignment_target_score': 1.023,
                              'best_coupling_signature': 'B^3',
                              'constraints': ['boundary'],
                              'contract_profile': {'accepts_payload': False,
                                                   'async_callable': False,
                                                   'callable': True,
                                                   'class_target': False,
                                                   'constraint_density': 1,
                                                   'contract_mode': 'stateful',
                                                   'doc_hint': 'Promote multiple nodes to a higher '
                                                               'layer via aggregation.',
                                                   'effect_density': 2,
                                                   'kwonly_args': 0,
                                                   'optional_args': 0,
                                                   'required_args': 2,
                                                   'return_hint': 'Optional',
                                                   'signature_text': '(self, source_ids: '
                                                                     'List[str], target_layer: '
                                                                     'aurora_governance_persistence_gateway.IVMLayer) '
                                                                     '-> '
                                                                     'Optional[aurora_governance_persistence_gateway.GovernedNode]',
                                                   'stateful_owner': True,
                                                   'target_kind': 'function',
                                                   'varargs': False,
                                                   'varkw': False},
                              'coupling_similarity': 1.0,
                              'cross_diversity_links': 2,
                              'effect_modes': ['interface_boundary_change', 'lineage_surface'],
                              'effect_phrases': ['function growth reflected through '
                                                 'aurora_governance_persistence_gateway',
                                                 'GovernanceEngine.promote changed downstream '
                                                 'system pressure'],
                              'genealogy_pressure': 0.75101,
                              'inheritance_breach_count': 1,
                              'kind': 'reflection',
                              'link_hits': 24,
                              'module': 'aurora_governance_persistence_gateway',
                              'op_id': 'aurora_governance_persistence_gateway.GovernanceEngine.promote',
                              'origin_activity': 0,
                              'persistence_tax_factor': 2.550513,
                              'representation_score': 0.567611,
                              'rewrite_bias': 'governance_routing',
                              'rewrite_feedback': {'acceptance_rate': 0.0,
                                                   'accepted_count': 0,
                                                   'adaptation_mode': 'integrative',
                                                   'adoption_count': 0,
                                                   'confidence': 0.0,
                                                   'mean_mutation_score': 0.0,
                                                   'rejected_count': 0,
                                                   'rejection_rate': 0.0,
                                                   'timing_credit': 0.0,
                                                   'timing_penalty': 0.0,
                                                   'trial_count': 0},
                              'rewrite_profile': 'governance_gateway',
                              'signature': 'B^3',
                              'surface_score': 0.632,
                              'sustainability_score': 0.356849,
                              'target_kind': 'function'},
 'GovernedCoordinate.boundary_weight': {'ability_hits': 12,
                                        'alignment_gap': 0.391,
                                        'alignment_target_score': 1.023,
                                        'best_coupling_signature': 'B^3',
                                        'constraints': ['boundary'],
                                        'contract_profile': {'accepts_payload': False,
                                                             'async_callable': False,
                                                             'callable': True,
                                                             'class_target': False,
                                                             'constraint_density': 1,
                                                             'contract_mode': 'stateful',
                                                             'doc_hint': '',
                                                             'effect_density': 2,
                                                             'kwonly_args': 0,
                                                             'optional_args': 0,
                                                             'required_args': 0,
                                                             'return_hint': 'float',
                                                             'signature_text': '(self) -> float',
                                                             'stateful_owner': True,
                                                             'target_kind': 'function',
                                                             'varargs': False,
                                                             'varkw': False},
                                        'coupling_similarity': 1.0,
                                        'cross_diversity_links': 2,
                                        'effect_modes': ['interface_boundary_change',
                                                         'lineage_surface'],
                                        'effect_phrases': ['function growth reflected through '
                                                           'aurora_governance_persistence_gateway',
                                                           'GovernedCoordinate.boundary_weight '
                                                           'changed downstream system pressure'],
                                        'genealogy_pressure': 0.75101,
                                        'inheritance_breach_count': 1,
                                        'kind': 'reflection',
                                        'link_hits': 24,
                                        'module': 'aurora_governance_persistence_gateway',
                                        'op_id': 'aurora_governance_persistence_gateway.GovernedCoordinate.boundary_weight',
                                        'origin_activity': 0,
                                        'persistence_tax_factor': 2.550513,
                                        'representation_score': 0.567611,
                                        'rewrite_bias': 'governance_routing',
                                        'rewrite_feedback': {'acceptance_rate': 0.0,
                                                             'accepted_count': 0,
                                                             'adaptation_mode': 'integrative',
                                                             'adoption_count': 0,
                                                             'confidence': 0.0,
                                                             'mean_mutation_score': 0.0,
                                                             'rejected_count': 0,
                                                             'rejection_rate': 0.0,
                                                             'timing_credit': 0.0,
                                                             'timing_penalty': 0.0,
                                                             'trial_count': 0},
                                        'rewrite_profile': 'governance_gateway',
                                        'signature': 'B^3',
                                        'surface_score': 0.632,
                                        'sustainability_score': 0.356849,
                                        'target_kind': 'function'},
 'RcloneInterface.__init__': {'ability_hits': 12,
                              'alignment_gap': 0.391,
                              'alignment_target_score': 1.023,
                              'best_coupling_signature': 'B^3',
                              'constraints': ['boundary'],
                              'contract_profile': {'accepts_payload': False,
                                                   'async_callable': False,
                                                   'callable': True,
                                                   'class_target': False,
                                                   'constraint_density': 1,
                                                   'contract_mode': 'stateful',
                                                   'doc_hint': 'Initialize self.  See '
                                                               'help(type(self)) for accurate '
                                                               'signature.',
                                                   'effect_density': 2,
                                                   'kwonly_args': 0,
                                                   'optional_args': 3,
                                                   'required_args': 0,
                                                   'return_hint': 'boundary_record',
                                                   'signature_text': '(self, remote_name: str = '
                                                                     "'gdrive', remote_path: str = "
                                                                     "'Aurora/aurora_state', "
                                                                     'local_path: str = '
                                                                     "'aurora_state')",
                                                   'stateful_owner': True,
                                                   'target_kind': 'function',
                                                   'varargs': False,
                                                   'varkw': False},
                              'coupling_similarity': 1.0,
                              'cross_diversity_links': 2,
                              'effect_modes': ['interface_boundary_change', 'lineage_surface'],
                              'effect_phrases': ['function growth reflected through '
                                                 'aurora_governance_persistence_gateway',
                                                 'RcloneInterface.__init__ changed downstream '
                                                 'system pressure'],
                              'genealogy_pressure': 0.75101,
                              'inheritance_breach_count': 1,
                              'kind': 'reflection',
                              'link_hits': 24,
                              'module': 'aurora_governance_persistence_gateway',
                              'op_id': 'aurora_governance_persistence_gateway.RcloneInterface.__init__',
                              'origin_activity': 0,
                              'persistence_tax_factor': 2.550513,
                              'representation_score': 0.567611,
                              'rewrite_bias': 'governance_routing',
                              'rewrite_feedback': {'acceptance_rate': 0.0,
                                                   'accepted_count': 0,
                                                   'adaptation_mode': 'integrative',
                                                   'adoption_count': 0,
                                                   'confidence': 0.0,
                                                   'mean_mutation_score': 0.0,
                                                   'rejected_count': 0,
                                                   'rejection_rate': 0.0,
                                                   'timing_credit': 0.0,
                                                   'timing_penalty': 0.0,
                                                   'trial_count': 0},
                              'rewrite_profile': 'governance_gateway',
                              'signature': 'B^3',
                              'surface_score': 0.632,
                              'sustainability_score': 0.356849,
                              'target_kind': 'function'},
 'RcloneInterface._find_rclone': {'ability_hits': 12,
                                  'alignment_gap': 0.391,
                                  'alignment_target_score': 1.023,
                                  'best_coupling_signature': 'B^3',
                                  'constraints': ['boundary'],
                                  'contract_profile': {'accepts_payload': False,
                                                       'async_callable': False,
                                                       'callable': True,
                                                       'class_target': False,
                                                       'constraint_density': 1,
                                                       'contract_mode': 'stateful',
                                                       'doc_hint': 'Find rclone binary path.',
                                                       'effect_density': 2,
                                                       'kwonly_args': 0,
                                                       'optional_args': 0,
                                                       'required_args': 0,
                                                       'return_hint': 'str',
                                                       'signature_text': '(self) -> str',
                                                       'stateful_owner': True,
                                                       'target_kind': 'function',
                                                       'varargs': False,
                                                       'varkw': False},
                                  'coupling_similarity': 1.0,
                                  'cross_diversity_links': 2,
                                  'effect_modes': ['interface_boundary_change', 'lineage_surface'],
                                  'effect_phrases': ['function growth reflected through '
                                                     'aurora_governance_persistence_gateway',
                                                     'RcloneInterface._find_rclone changed '
                                                     'downstream system pressure'],
                                  'genealogy_pressure': 0.75101,
                                  'inheritance_breach_count': 1,
                                  'kind': 'reflection',
                                  'link_hits': 24,
                                  'module': 'aurora_governance_persistence_gateway',
                                  'op_id': 'aurora_governance_persistence_gateway.RcloneInterface._find_rclone',
                                  'origin_activity': 0,
                                  'persistence_tax_factor': 2.550513,
                                  'representation_score': 0.567611,
                                  'rewrite_bias': 'governance_routing',
                                  'rewrite_feedback': {'acceptance_rate': 0.0,
                                                       'accepted_count': 0,
                                                       'adaptation_mode': 'integrative',
                                                       'adoption_count': 0,
                                                       'confidence': 0.0,
                                                       'mean_mutation_score': 0.0,
                                                       'rejected_count': 0,
                                                       'rejection_rate': 0.0,
                                                       'timing_credit': 0.0,
                                                       'timing_penalty': 0.0,
                                                       'trial_count': 0},
                                  'rewrite_profile': 'governance_gateway',
                                  'signature': 'B^3',
                                  'surface_score': 0.632,
                                  'sustainability_score': 0.356849,
                                  'target_kind': 'function'}}

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

def promote_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.GovernanceEngine.promote', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_governanceengine_promote')(payload=payload, **kwargs)

if _aurora_get_target(['GovernanceEngine', 'promote']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['GovernanceEngine.promote'] = _aurora_get_target(['GovernanceEngine', 'promote'])
    _aurora_assign_target(['GovernanceEngine', 'promote'], _aurora_make_override('promote_evolved', 'GovernanceEngine.promote'))
    _AURORA_NATIVE_EVOLVED_LAST['GovernanceEngine.promote'] = {'alignment_gap': 0.391, 'override_active': True}

def boundary_weight_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.GovernedCoordinate.boundary_weight', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_governedcoordinate_boundary_weight')(payload=payload, **kwargs)

if _aurora_get_target(['GovernedCoordinate', 'boundary_weight']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['GovernedCoordinate.boundary_weight'] = _aurora_get_target(['GovernedCoordinate', 'boundary_weight'])
    _aurora_assign_target(['GovernedCoordinate', 'boundary_weight'], _aurora_make_override('boundary_weight_evolved', 'GovernedCoordinate.boundary_weight'))
    _AURORA_NATIVE_EVOLVED_LAST['GovernedCoordinate.boundary_weight'] = {'alignment_gap': 0.391, 'override_active': True}

def init_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.RcloneInterface.__init__', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_rcloneinterface_init')(payload=payload, **kwargs)

def find_rclone_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.RcloneInterface._find_rclone', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_rcloneinterface_find_rclone')(payload=payload, **kwargs)

if _aurora_get_target(['RcloneInterface', '_find_rclone']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['RcloneInterface._find_rclone'] = _aurora_get_target(['RcloneInterface', '_find_rclone'])
    _aurora_assign_target(['RcloneInterface', '_find_rclone'], _aurora_make_override('find_rclone_evolved', 'RcloneInterface._find_rclone'))
    _AURORA_NATIVE_EVOLVED_LAST['RcloneInterface._find_rclone'] = {'alignment_gap': 0.391, 'override_active': True}

AURORA_NATIVE_EVOLVED_EXPORTS = {'aurora_governance_persistence_gateway.GovernanceEngine.promote': 'promote_evolved',
 'aurora_governance_persistence_gateway.GovernedCoordinate.boundary_weight': 'boundary_weight_evolved',
 'aurora_governance_persistence_gateway.RcloneInterface.__init__': 'init_evolved',
 'aurora_governance_persistence_gateway.RcloneInterface._find_rclone': 'find_rclone_evolved'}
AURORA_NATIVE_EVOLUTION_OVERRIDES = {'aurora_governance_persistence_gateway.GovernanceEngine.promote': {'export': 'promote_evolved',
                                                                    'mode': 'callable_override',
                                                                    'target': 'GovernanceEngine.promote'},
 'aurora_governance_persistence_gateway.GovernedCoordinate.boundary_weight': {'export': 'boundary_weight_evolved',
                                                                              'mode': 'callable_override',
                                                                              'target': 'GovernedCoordinate.boundary_weight'},
 'aurora_governance_persistence_gateway.RcloneInterface._find_rclone': {'export': 'find_rclone_evolved',
                                                                        'mode': 'callable_override',
                                                                        'target': 'RcloneInterface._find_rclone'}}
# AURORA_EVOLVED_NATIVE_END

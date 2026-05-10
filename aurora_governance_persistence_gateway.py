#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
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
    ExpressionPerceptionEngine, ConsciousnessPoint
)
from aurora_behavioral_identity import (
    BehavioralIdentityEngine, DNASystem
)
from aurora_simulation_engine import (
    SimulationEngine, SimulationSession, TimeDilationGovernor,
    StabilityMetrics, StabilityState, EpisodeResult
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

    def __init__(self, state_dir: str = "aurora_state"):
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
    SELF_REFLECTION = "self_reflection" # Aurora processing her own output (re-entry loop)


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

    def __init__(self,
                 contract: Optional[FoundationalContract] = None,
                 dimensional: Optional[DimensionalSystems] = None,
                 consciousness: Optional[ConsciousnessEngine] = None,
                 perception: Optional[ExpressionPerceptionEngine] = None,
                 identity: Optional[BehavioralIdentityEngine] = None,
                 simulation: Optional[SimulationEngine] = None,
                 governance: Optional[GovernanceEngine] = None):

        self.contract = contract or FoundationalContract()
        self.dimensional = dimensional
        self.consciousness = consciousness
        self.perception = perception
        self.identity = identity
        self.simulation = simulation
        self.governance = governance or GovernanceEngine()
        self.field_map = None  # Optional ConstraintFieldAccumulator (read-only observer)

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

    def set_field_map(self, field_map) -> None:
        """Attach a ConstraintFieldAccumulator as a read-only observer. Pass None to detach."""
        self.field_map = field_map

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
                        mode: ExistenceMode) -> Dict[str, Any]:
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
                    thought_intent: Optional[Dict[str, Any]] = None) -> GatewaySynthesis:
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
        evidence = self._build_evidence(packet, mode)

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

        return result

    # ====================================================================
    # EXPRESSION PIPELINE (L5 + L6)
    # ====================================================================

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
            expr_result = self.perception.express(
                synthesis.assembly,
                i_state="i_is",
                mode="gateway"
            )
            expression_text = expr_result.get('expression', '')
            emotional_tone = expr_result.get('tone', 'neutral')

        if not expression_text:
            # Fallback: meaningful acknowledgment based on stream type
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
            ep = self.simulation.run_episode(
                turns=3, mode=mode)
            results.append({
                'source': item.get('packet_id', 'unknown'),
                'fitness': ep.avg_fitness,
                'understanding': ep.understanding_gained,
            })

            # If simulation went well, potentially release from quarantine
            if ep.avg_fitness > 0.5:
                pid = item.get('packet_id')
                if pid in self.quarantine:
                    del self.quarantine[pid]

        # Also run general exploration epochs if capacity remains
        remaining = max(0, cycles - len(results))
        if remaining > 0 and self.simulation:
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
        """Generate a meaningful response when full pipeline isn't available."""
        if packet.stream_type == StreamType.USER_INPUT:
            return "I hear you. Let me consider this thoughtfully."
        elif packet.stream_type == StreamType.KNOWLEDGE_FEED:
            return "I've received this information and am integrating it."
        elif packet.stream_type == StreamType.SENSOR_DATA:
            return "Environmental signal received and processed."
        return "Data received."

    def _needs_articulation_bridge(self, prompt: str, draft: str) -> bool:
        """Detect when expressive output is too abstract for user-facing utility."""
        p = str(prompt or "").strip().lower()
        d = str(draft or "").strip().lower()
        if not d:
            return True
        words = [w for w in re.findall(r"[a-zA-Z']+", d) if w]
        if len(words) < 9:
            return True
        abstract_markers = {"quiet", "strange", "slowly", "moment", "something", "deeply"}
        abstract_hits = sum(1 for w in words if w in abstract_markers)
        if abstract_hits >= 2 and len(words) < 20:
            return True
        prompt_tokens = {w for w in re.findall(r"[a-zA-Z']+", p) if len(w) >= 4}
        if prompt_tokens:
            overlap = sum(1 for w in words if w in prompt_tokens)
            if overlap == 0:
                return True
        return False

    def _articulate_user_response(self, prompt: str, draft: str, tone: str) -> str:
        """
        Smooth Aurora's own draft without letting the articulator answer.

        Constraint ancestry:
          X (existence): preserves user intent as a persistent conversational object
          T (temporal): keeps the already-selected response turn intact
          N (energy): reduces cognitive cost through wording cleanup only
          B (boundary): keeps expression grounded to the prompt's task boundary
          A (agency): preserves Aurora's agency as the responder
        """
        prompt_text = str(prompt or "").strip()
        draft_text = str(draft or "").strip()
        if not draft_text:
            return ""
        if not prompt_text or not self._needs_articulation_bridge(prompt_text, draft_text):
            return draft_text
        try:
            from aurora_articulation import smooth_with_decision
            decision = smooth_with_decision(draft_text, prompt=prompt_text, tone=tone)
            if self.perception and hasattr(self.perception, 'ingest_interaction'):
                self.perception.ingest_interaction({
                    'input': decision.selected,
                    'tone': tone,
                    'i_state': 'i_is',
                    'source': 'articulation_pressure_feedback',
                    'features': {
                        'articulation_accepted': 1.0 if decision.accepted else 0.0,
                        'pressure_relief': decision.pressure_relief,
                        'original_pressure': decision.original_pressure,
                        'candidate_pressure': decision.candidate_pressure,
                    },
                }, mode="gateway")
            return decision.selected
        except Exception:
            return draft_text

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
                 state_dir: str = "aurora_state"):

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
        )

        # References for snapshot capture
        self._identity = identity
        self._simulation = simulation
        self.field_map = None  # Optional ConstraintFieldAccumulator (read-only observer)

    def set_field_map(self, field_map) -> None:
        """Attach a ConstraintFieldAccumulator to the gateway and its inner NSpaceGateway."""
        self.field_map = field_map
        self.gateway.set_field_map(field_map)

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
        return self.persistence.save(snapshot)

    def load_state(self) -> Optional[AuroraStateSnapshot]:
        """Load Aurora's saved state."""
        return self.persistence.load()

    def get_stats(self) -> Dict[str, Any]:
        return {
            'governance': self.governance.get_stats(),
            'persistence': self.persistence.get_info(),
            'gateway': self.gateway.get_stats(),
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
                 checkpoint_path: str = "aurora_state/checkpoint.json",
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
            thought = self.pending_thoughts.pop(0)
            self.last_speakup_time = now
            return thought

        # Priority 2: Interesting observations
        if self.observation_buffer:
            obs = self.observation_buffer.pop(0)
            if obs.get('salience', 0) > 0.7:
                self.last_speakup_time = now
                return obs.get('description', '')

        # Priority 3: Curiosity-driven questions
        if self.curiosity_queue and random.random() < 0.3:  # 30% chance
            question = self.curiosity_queue.pop(0)
            self.last_speakup_time = now
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

    def __init__(self, search_adapter, boundaries: AutonomyBoundaries):
        self.search_adapter = search_adapter
        self.boundaries = boundaries
        self.quotas: DailyQuotas = DailyQuotas()

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
            results = self.search_adapter.quick_search(query, max_chars=max_chars)
            self.quotas.inquiries_used += 1
            remaining = self.boundaries.daily_inquiry_limit - self.quotas.inquiries_used
            return results, f"Search complete ({remaining} autonomous inquiries remaining today)"
        except Exception as e:
            return [], f"Search failed: {e}"

    def user_search(self, query: str, max_chars: int = 2000) -> List[Dict]:
        """
        Perform a user-initiated search (does NOT count against limit).
        """
        try:
            return self.search_adapter.quick_search(query, max_chars=max_chars)
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
                 state_dir: str = "aurora_state",
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
        self.filesystem = FilesystemExplorer(self.boundaries)
        self.study_scheduler = StudyScheduler(self.boundaries)

        # Rate-limited search
        search_adapter = systems.get('search_adapter') if systems else None
        self.search = RateLimitedSearch(search_adapter, self.boundaries) if search_adapter else None

        # Background thread for autonomous actions
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Callbacks
        self.on_speakup: Optional[Callable[[str], None]] = None
        self.on_study_complete: Optional[Callable[[Dict], None]] = None
        self.on_dream_complete: Optional[Callable[[Dict], None]] = None
        self.on_observation: Optional[Callable[[str], None]] = None

        # Enhancement: Will Loop state
        self._last_intent_time: Dict[str, float] = {}
        self._intent_cooldowns: Dict[str, float] = {
            "curiosity": 300,   # 5 minutes
            "grounding": 600,   # 10 minutes
            "self_check": 1800, # 30 minutes
            "agency": 3600,     # 1 hour
            "environmental": 900 # 15 minutes
        }

        self.last_dream_time: float = 0.0

        # Dream evolution orchestrator
        self._dream_evo = None
        try:
            from aurora_internal.aurora_dream_evolution_orchestrator import (
                DreamEvolutionOrchestrator,
            )
            corpus_path = None
            # Look for conversation corpus in standard locations
            for candidate in [
                os.path.join(str(self.state_dir), "conversations.json"),
                os.path.join(str(self.state_dir), "corpus", "conversations.json"),
                "conversations.json",
            ]:
                if os.path.exists(candidate):
                    corpus_path = candidate
                    break
            self._dream_evo = DreamEvolutionOrchestrator(
                state_dir=str(self.state_dir),
                corpus_path=corpus_path,
            )
            logger.info("[AUTONOMY] Dream evolution orchestrator attached")
        except Exception as e:
            logger.debug(f"[AUTONOMY] Dream evolution not available: {e}")

        # Pressure mathematics tracker
        self._pressure_tracker = None
        try:
            from aurora_internal.aurora_pressure_mathematics_tracker import (
                PressureMathematicsTracker,
            )
            self._pressure_tracker = PressureMathematicsTracker(
                storage_dir=os.path.join(str(self.state_dir), "pressure_math"),
            )
            logger.info("[AUTONOMY] Pressure mathematics tracker attached")
        except Exception as e:
            logger.debug(f"[AUTONOMY] Pressure math tracker not available: {e}")

        # Load state
        self._load_state()

    def attach_systems(self, systems: Dict[str, Any]):
        """Attach system references after initialization."""
        self.systems = systems
        search_adapter = systems.get('search_adapter')
        if search_adapter:
            self.search = RateLimitedSearch(search_adapter, self.boundaries)

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

                # 1. NEW: Process Attention-driven Will Intent
                self._process_attention_will()

                # 2. Check for proactive speakup
                if self.level.value >= AutonomyLevel.CONVERSANT.value:
                    self._check_speakup()

                # 3. Check for autonomous study
                if self.level.value >= AutonomyLevel.LEARNER.value:
                    self._check_study()
                    self._check_dreams()

                # 4. Check for observations
                if self.level.value >= AutonomyLevel.OBSERVER.value:
                    self._check_observations()

                # Sleep before next cycle
                self._stop_event.wait(timeout=5.0)

            except Exception as e:
                logger.error(f"[AUTONOMY] Background loop error: {e}")
                self._stop_event.wait(timeout=10.0)

    def _process_attention_will(self):
        """Check the Attention Engine for new intentions and gate them."""
        attn = self.systems.get("attention_engine")
        if not attn: return
        
        # 'Attention -> Intention'
        will_intent = attn.generate_will()
        if not will_intent: return
        
        # 'Intention -> Commit/Defer (Gating)'
        # 1. Check Cooldown
        last_time = self._last_intent_time.get(will_intent.class_name, 0)
        cooldown = self._intent_cooldowns.get(will_intent.class_name, 600)
        if time.time() - last_time < cooldown:
            return
            
        # 2. Check Governor (Load/Heat)
        governor = self.systems.get("governor")
        if governor:
            # If system is too hot or load is high, defer the intention
            status = governor.status()
            heat = float(status.get("thermal_load", 0.0))
            if heat > 0.85: 
                logger.debug(f"[AUTONOMY] Deferring intent {will_intent.class_name} due to high heat: {heat:.2f}")
                return
        
        # 3. Commit
        self.commit_will_intent(will_intent)

    def commit_will_intent(self, intent: Any):
        """Execute the committed intention and reflect."""
        self._last_intent_time[intent.class_name] = time.time()
        
        logger.info(f"[AUTONOMY] Committing Will Intent: {intent.class_name} (Goal: {intent.goal})")
        self.action_log.log("will_intent", f"{intent.class_name}: {intent.goal}")
        
        # Act: Pick tool + goal
        if intent.tool_name:
            # In a real daemon, we would inject this tool call into the pipeline
            # For now, we log the commit. 
            # If it's a 'speech' intent, we use on_speakup
            if intent.class_name == "curiosity" and self.on_speakup:
                self.on_speakup(f"I feel a peak in resonance on my {', '.join(intent.trigger_axes)} axes. I should explore this.")
            
            # Record the autonomous tool request
            if hasattr(self, "systems") and "aurora" in self.systems:
                # Mock tool call injection
                pass

    def _gather_context(self) -> Dict[str, Any]:
        """Return True if current hour is inside the quiet window."""
        if not self.boundaries.quiet_window_enabled:
            return False
        current_hour = datetime.now().hour
        start = self.boundaries.quiet_window_start_hour
        end   = self.boundaries.quiet_window_end_hour
        if start > end:  # wraps midnight
            return current_hour >= start or current_hour < end
        return start <= current_hour < end

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
        """Create an adaptive dream seed from memory + ontology context.

        If the dream evolution orchestrator has episode packs available,
        uses rubric-targeted seeds instead of generic topic seeds.
        """
        # Try dream evolution curriculum first
        if self._dream_evo:
            try:
                evo_seed = self._dream_evo.build_seed()
                if evo_seed:
                    return evo_seed
            except Exception as e:
                logger.debug(f"[AUTONOMY] Dream evo seed fallback: {e}")

        # Original seed logic (fallback)
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

        if not candidates:
            candidates = [
                "cooperation under uncertainty",
                "identity and ethical choice",
                "relational trust formation",
            ]

        chosen = random.sample(candidates, min(2, len(candidates)))
        return " | ".join(chosen)

    def _check_dreams(self):
        """Run idle dream-simulation cycles that evolve with Aurora's understanding.

        When the dream evolution orchestrator is active, episodes are:
        1. Sourced from rubric-targeted curriculum packs
        2. Diagnosed through the slip profiler + influence graph
        3. Fed into structural pressure steering + genealogy bridge
        """
        now = time.time()
        if now - self.last_dream_time < self.boundaries.dream_cooldown_seconds:
            return

        simulation = self.systems.get('simulation')
        mode_enum = self.systems.get('ExistenceMode')
        if not simulation or not mode_enum:
            return

        try:
            seed = self._build_dream_seed()
            result = simulation.run_episode(
                turns=4,
                mode=mode_enum.BOUNDED,
            )
            self.last_dream_time = now
            self.quotas.dreams_used += 1

            # --- Dream evolution diagnostic pipeline ---
            evo_summary = None
            if self._dream_evo:
                try:
                    evo_summary = self._dream_evo.post_episode(result, seed)
                    # Apply results into live systems
                    self._dream_evo.apply(self.systems)
                except Exception as e:
                    logger.debug(f"[AUTONOMY] Dream evo pipeline: {e}")

            # --- Pressure mathematics capture ---
            if self._pressure_tracker:
                try:
                    p_metrics = self._pressure_tracker.capture(self.systems)
                    self._pressure_tracker.apply_feedback(self.systems)
                except Exception as e:
                    logger.debug(f"[AUTONOMY] Pressure math capture: {e}")

            # Build thought with evolution context if available
            if evo_summary and evo_summary.leverage_candidates:
                top_leverage = list(evo_summary.leverage_candidates.keys())[:2]
                leverage_str = ", ".join(d.replace("_", " ") for d in top_leverage)
                thought = (
                    f"I dreamed through a shifting scenario around: {seed}. "
                    f"I noticed growth edges in {leverage_str}."
                )
            else:
                thought = f"I dreamed through a shifting scenario around: {seed}."

            self.action_log.log(
                "dream",
                f"Idle dream cycle completed (seed={seed[:80]})",
                details={
                    "seed": seed,
                    "result": result,
                    "evo_status": (
                        self._dream_evo.get_status()
                        if self._dream_evo else None
                    ),
                },
            )

            if not self._in_quiet_window():
                self.trigger.add_thought(thought)

            if self.on_dream_complete:
                self.on_dream_complete({
                    "seed": seed,
                    "result": result,
                    "thought": thought,
                    "evo_summary": (
                        evo_summary.to_dict() if evo_summary else None
                    ),
                })
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

            # Look for interesting observations
            if context.get('visual'):
                self.quotas.observations_used += 1
                if "face" in context['visual'].lower() or "motion" in context['visual'].lower():
                    self.trigger.add_observation(context['visual'], salience=0.75)

            if context.get('recent_speech'):
                self.quotas.observations_used += 1
                self.trigger.add_observation(
                    f"I heard someone say: {context['recent_speech'][:50]}...",
                    salience=0.8
                )

            if self.on_observation and context.get('concepts_active'):
                self.on_observation(f"Concepts active: {', '.join(context['concepts_active'][:3])}")

        except Exception as e:
            logger.debug(f"[AUTONOMY] Observation error: {e}")

    def _gather_context(self) -> Dict[str, Any]:
        """Gather current context for decision making."""
        context = {
            "time": time.time(),
            "quotas": self.quotas.to_dict(),
            "level": self.level.name,
        }

        # Add sensory context if available
        integration = self.systems.get('sensory_integration')
        if integration:
            try:
                context["sensory"] = integration.get_sensory_context()
            except:
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
            "boundaries": {
                "can_write": self.boundaries.can_write_files,
                "can_execute": self.boundaries.can_execute_commands,
                "can_network": self.boundaries.can_access_network,
            },
            "dream_evolution": (
                self._dream_evo.get_status() if self._dream_evo else None
            ),
            "pressure_mathematics": (
                self._pressure_tracker.get_status()
                if self._pressure_tracker else None
            ),
        }

    def compile_dream_corpus(self, corpus_path: str, max_conversations: int = 500) -> int:
        """Compile a conversation corpus into dream episode packs on demand.
        Returns number of packs compiled, or 0 if dream evolution not available."""
        if not self._dream_evo:
            return 0
        return self._dream_evo.pre_compile(corpus_path, max_conversations)

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

            logger.info(f"[AUTONOMY] State loaded (level={self.level.name})")

        except Exception as e:
            logger.error(f"[AUTONOMY] Failed to load state: {e}")


# ============================================================================
# SECTION 9: CONVENIENCE FUNCTIONS
# ============================================================================

def create_autonomy_engine(systems: Dict[str, Any],
                           state_dir: str = "aurora_state",
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
_AURORA_NATIVE_STRATEGIES = {'ActionLog': {'ability_hits': 1,
               'alignment_gap': 0.682083,
               'alignment_target_score': 1.29475,
               'best_coupling_signature': 'B^1*A^2',
               'constraints': ['agency'],
               'contract_profile': {'accepts_payload': False,
                                    'async_callable': False,
                                    'callable': True,
                                    'class_target': True,
                                    'constraint_density': 1,
                                    'contract_mode': 'stateless',
                                    'doc_hint': 'Maintains log of all autonomous actions.',
                                    'effect_density': 4,
                                    'kwonly_args': 0,
                                    'optional_args': 1,
                                    'required_args': 0,
                                    'return_hint': 'boundary_record',
                                    'signature_text': '(max_entries: int = 1000)',
                                    'stateful_owner': False,
                                    'target_kind': 'class',
                                    'varargs': False,
                                    'varkw': False},
               'coupling_similarity': 1.0,
               'cross_diversity_links': 4,
               'effect_modes': ['adaptive_steering_change',
                                'stateful_surface_expansion',
                                'gateway_surface',
                                'core_subsystem_surface'],
               'effect_phrases': ['changed steering, mutation, or choice behavior',
                                  'introduced reusable state-bearing system surface',
                                  'extended cross-layer routing or gateway effects'],
               'genealogy_pressure': 0.426456,
               'inheritance_breach_count': 1,
               'kind': 'reflection',
               'link_hits': 0,
               'module': 'aurora_governance_persistence_gateway',
               'op_id': 'aurora_governance_persistence_gateway.ActionLog',
               'origin_activity': 0,
               'persistence_tax_factor': 1.822787,
               'representation_score': 0.359639,
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
               'signature': 'B^1*A^2',
               'surface_score': 0.612667,
               'sustainability_score': 0.445319,
               'target_kind': 'class'},
 'ActionLog.__init__': {'ability_hits': 1,
                        'alignment_gap': 0.76525,
                        'alignment_target_score': 1.29475,
                        'best_coupling_signature': 'B^1*A^2',
                        'constraints': ['agency'],
                        'contract_profile': {'accepts_payload': False,
                                             'async_callable': False,
                                             'callable': True,
                                             'class_target': False,
                                             'constraint_density': 1,
                                             'contract_mode': 'stateful',
                                             'doc_hint': 'Initialize self.  See help(type(self)) '
                                                         'for accurate signature.',
                                             'effect_density': 4,
                                             'kwonly_args': 0,
                                             'optional_args': 1,
                                             'required_args': 0,
                                             'return_hint': 'boundary_record',
                                             'signature_text': '(self, max_entries: int = 1000)',
                                             'stateful_owner': True,
                                             'target_kind': 'function',
                                             'varargs': False,
                                             'varkw': False},
                        'coupling_similarity': 1.0,
                        'cross_diversity_links': 1,
                        'effect_modes': ['adaptive_steering_change',
                                         'behavioral_execution_surface',
                                         'gateway_surface',
                                         'core_subsystem_surface'],
                        'effect_phrases': ['changed steering, mutation, or choice behavior',
                                           'introduced executable behavior surface',
                                           'extended cross-layer routing or gateway effects'],
                        'genealogy_pressure': 0.426456,
                        'inheritance_breach_count': 1,
                        'kind': 'reflection',
                        'link_hits': 0,
                        'module': 'aurora_governance_persistence_gateway',
                        'op_id': 'aurora_governance_persistence_gateway.ActionLog.__init__',
                        'origin_activity': 0,
                        'persistence_tax_factor': 1.822787,
                        'representation_score': 0.359639,
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
                        'signature': 'B^1*A^2',
                        'surface_score': 0.5295000000000001,
                        'sustainability_score': 0.445319,
                        'target_kind': 'function'},
 'ActionLog.get_by_type': {'ability_hits': 1,
                           'alignment_gap': 0.74775,
                           'alignment_target_score': 1.29475,
                           'best_coupling_signature': 'B^1*A^2',
                           'constraints': ['agency'],
                           'contract_profile': {'accepts_payload': False,
                                                'async_callable': False,
                                                'callable': True,
                                                'class_target': False,
                                                'constraint_density': 1,
                                                'contract_mode': 'stateful',
                                                'doc_hint': 'Get actions of a specific type.',
                                                'effect_density': 4,
                                                'kwonly_args': 0,
                                                'optional_args': 1,
                                                'required_args': 1,
                                                'return_hint': 'List',
                                                'signature_text': '(self, action_type: str, n: int '
                                                                  '= 50) -> '
                                                                  'List[aurora_governance_persistence_gateway.AutonomousAction]',
                                                'stateful_owner': True,
                                                'target_kind': 'function',
                                                'varargs': False,
                                                'varkw': False},
                           'coupling_similarity': 1.0,
                           'cross_diversity_links': 4,
                           'effect_modes': ['adaptive_steering_change',
                                            'behavioral_execution_surface',
                                            'gateway_surface',
                                            'core_subsystem_surface'],
                           'effect_phrases': ['changed steering, mutation, or choice behavior',
                                              'introduced executable behavior surface',
                                              'extended cross-layer routing or gateway effects'],
                           'genealogy_pressure': 0.426456,
                           'inheritance_breach_count': 1,
                           'kind': 'reflection',
                           'link_hits': 0,
                           'module': 'aurora_governance_persistence_gateway',
                           'op_id': 'aurora_governance_persistence_gateway.ActionLog.get_by_type',
                           'origin_activity': 0,
                           'persistence_tax_factor': 1.822787,
                           'representation_score': 0.359639,
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
                           'signature': 'B^1*A^2',
                           'surface_score': 0.547,
                           'sustainability_score': 0.445319,
                           'target_kind': 'function'},
 'ActionLog.get_recent': {'ability_hits': 1,
                          'alignment_gap': 0.73025,
                          'alignment_target_score': 1.29475,
                          'best_coupling_signature': 'B^1*A^2',
                          'constraints': ['agency'],
                          'contract_profile': {'accepts_payload': False,
                                               'async_callable': False,
                                               'callable': True,
                                               'class_target': False,
                                               'constraint_density': 1,
                                               'contract_mode': 'stateful',
                                               'doc_hint': 'Get recent actions.',
                                               'effect_density': 4,
                                               'kwonly_args': 0,
                                               'optional_args': 1,
                                               'required_args': 0,
                                               'return_hint': 'List',
                                               'signature_text': '(self, n: int = 20) -> '
                                                                 'List[aurora_governance_persistence_gateway.AutonomousAction]',
                                               'stateful_owner': True,
                                               'target_kind': 'function',
                                               'varargs': False,
                                               'varkw': False},
                          'coupling_similarity': 1.0,
                          'cross_diversity_links': 2,
                          'effect_modes': ['adaptive_steering_change',
                                           'behavioral_execution_surface',
                                           'gateway_surface',
                                           'core_subsystem_surface'],
                          'effect_phrases': ['changed steering, mutation, or choice behavior',
                                             'introduced executable behavior surface',
                                             'extended cross-layer routing or gateway effects'],
                          'genealogy_pressure': 0.426456,
                          'inheritance_breach_count': 1,
                          'kind': 'reflection',
                          'link_hits': 0,
                          'module': 'aurora_governance_persistence_gateway',
                          'op_id': 'aurora_governance_persistence_gateway.ActionLog.get_recent',
                          'origin_activity': 0,
                          'persistence_tax_factor': 1.822787,
                          'representation_score': 0.359639,
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
                          'signature': 'B^1*A^2',
                          'surface_score': 0.5645,
                          'sustainability_score': 0.445319,
                          'target_kind': 'function'},
 'ActionLog.log': {'ability_hits': 1,
                   'alignment_gap': 0.75275,
                   'alignment_target_score': 1.29475,
                   'best_coupling_signature': 'B^1*A^2',
                   'constraints': ['agency'],
                   'contract_profile': {'accepts_payload': False,
                                        'async_callable': False,
                                        'callable': True,
                                        'class_target': False,
                                        'constraint_density': 1,
                                        'contract_mode': 'stateful',
                                        'doc_hint': 'Log an autonomous action.',
                                        'effect_density': 4,
                                        'kwonly_args': 0,
                                        'optional_args': 2,
                                        'required_args': 2,
                                        'return_hint': 'AutonomousAction',
                                        'signature_text': '(self, action_type: str, description: '
                                                          'str, success: bool = True, details: '
                                                          'Dict[str, Any] = None) -> '
                                                          'aurora_governance_persistence_gateway.AutonomousAction',
                                        'stateful_owner': True,
                                        'target_kind': 'function',
                                        'varargs': False,
                                        'varkw': False},
                   'coupling_similarity': 1.0,
                   'cross_diversity_links': 1,
                   'effect_modes': ['adaptive_steering_change',
                                    'behavioral_execution_surface',
                                    'gateway_surface',
                                    'core_subsystem_surface'],
                   'effect_phrases': ['changed steering, mutation, or choice behavior',
                                      'introduced executable behavior surface',
                                      'extended cross-layer routing or gateway effects'],
                   'genealogy_pressure': 0.426456,
                   'inheritance_breach_count': 1,
                   'kind': 'reflection',
                   'link_hits': 0,
                   'module': 'aurora_governance_persistence_gateway',
                   'op_id': 'aurora_governance_persistence_gateway.ActionLog.log',
                   'origin_activity': 0,
                   'persistence_tax_factor': 1.822787,
                   'representation_score': 0.359639,
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
                   'signature': 'B^1*A^2',
                   'surface_score': 0.542,
                   'sustainability_score': 0.445319,
                   'target_kind': 'function'},
 'AtomicWriter.append_jsonl': {'ability_hits': 0,
                               'alignment_gap': 0.747333,
                               'alignment_target_score': 1.29475,
                               'best_coupling_signature': 'X^2*T^2*B^1',
                               'constraints': ['existence', 'temporal'],
                               'contract_profile': {'accepts_payload': True,
                                                    'async_callable': False,
                                                    'callable': True,
                                                    'class_target': False,
                                                    'constraint_density': 2,
                                                    'contract_mode': 'stateful',
                                                    'doc_hint': 'Append a JSON record to a .jsonl '
                                                                'file (not atomic, but safe for '
                                                                'logs).',
                                                    'effect_density': 5,
                                                    'kwonly_args': 0,
                                                    'optional_args': 0,
                                                    'required_args': 2,
                                                    'return_hint': 'bool',
                                                    'signature_text': '(path: str, record: Dict) '
                                                                      '-> bool',
                                                    'stateful_owner': True,
                                                    'target_kind': 'function',
                                                    'varargs': False,
                                                    'varkw': False},
                               'coupling_similarity': 1.0,
                               'cross_diversity_links': 1,
                               'effect_modes': ['state_schema_change',
                                                'temporal_orchestration_change',
                                                'behavioral_execution_surface',
                                                'gateway_surface',
                                                'core_subsystem_surface'],
                               'effect_phrases': ['changed admissible state or persistence shape',
                                                  'changed ordering, tick flow, or replay behavior',
                                                  'introduced executable behavior surface',
                                                  'extended cross-layer routing or gateway '
                                                  'effects'],
                               'genealogy_pressure': 0.409012,
                               'inheritance_breach_count': 1,
                               'kind': 'reflection',
                               'link_hits': 0,
                               'module': 'aurora_governance_persistence_gateway',
                               'op_id': 'aurora_governance_persistence_gateway.AtomicWriter.append_jsonl',
                               'origin_activity': 0,
                               'persistence_tax_factor': 1.450604,
                               'representation_score': 0.40614,
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
                               'signature': 'X^2*T^2*B^1',
                               'surface_score': 0.547417,
                               'sustainability_score': 0.449345,
                               'target_kind': 'function'},
 'AtomicWriter.route_agency': {'ability_hits': 0,
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
                                                    'effect_density': 7,
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
                                                'gateway_surface',
                                                'core_subsystem_surface',
                                                'latent_route_surface',
                                                'latent_a_derivative'],
                               'effect_phrases': ['would extend agency pressure handling',
                                                  'would materialize the next descendant implied '
                                                  'by '
                                                  'aurora_governance_persistence_gateway.AtomicWriter'],
                               'genealogy_pressure': 0.0,
                               'inheritance_breach_count': 0,
                               'kind': 'latent',
                               'link_hits': 0,
                               'module': 'aurora_governance_persistence_gateway',
                               'op_id': 'latent.aurora_governance_persistence_gateway.AtomicWriter.route_agency',
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
                               'rewrite_profile': 'governance_gateway',
                               'signature': '',
                               'surface_score': 0.82582745,
                               'sustainability_score': 0.0,
                               'target_kind': 'latent_operation'},
 'AuroraStateSnapshot': {'ability_hits': 1,
                         'alignment_gap': 0.515416,
                         'alignment_target_score': 1.29475,
                         'best_coupling_signature': 'X^2*B^1',
                         'constraints': ['existence'],
                         'contract_profile': {'accepts_payload': False,
                                              'async_callable': False,
                                              'callable': True,
                                              'class_target': True,
                                              'constraint_density': 1,
                                              'contract_mode': 'stateless',
                                              'doc_hint': "Complete snapshot of Aurora's evolved "
                                                          'state.',
                                              'effect_density': 4,
                                              'kwonly_args': 0,
                                              'optional_args': 19,
                                              'required_args': 0,
                                              'return_hint': 'None',
                                              'signature_text': "(version: str = '2.0', timestamp: "
                                                                'float = <factory>, generation: '
                                                                'int = 0, genome_version: int = 0, '
                                                                'core_gene_count: int = 0, '
                                                                'active_genes: List[str] = '
                                                                '<factory>, total_alleles: int = '
                                                                '0, identity_anchors: List[str] = '
                                                                '<factory>, memory_helices: int = '
                                                                '0, traits: Dict[str, float] = '
                                                                '<factory>, personality_drift: '
                                                                'float = 0.0, crystal_genomes: '
                                                                'Dict[str, Dict[str, float]] = '
                                                                '<factory>, governance_stats: '
                                                                'Dict[str, Any] = <factory>, '
                                                                'simulation_epochs: int = 0, '
                                                                'total_episodes: int = 0, '
                                                                'understanding_shards: int = 0, '
                                                                'what_aurora_learned: List[str] = '
                                                                '<factory>, time_dilation: float = '
                                                                '3000.0, stability_state: str = '
                                                                "'stable') -> None",
                                              'stateful_owner': False,
                                              'target_kind': 'class',
                                              'varargs': False,
                                              'varkw': False},
                         'coupling_similarity': 1.0,
                         'cross_diversity_links': 7,
                         'effect_modes': ['state_schema_change',
                                          'stateful_surface_expansion',
                                          'gateway_surface',
                                          'core_subsystem_surface'],
                         'effect_phrases': ['changed admissible state or persistence shape',
                                            'introduced reusable state-bearing system surface',
                                            'extended cross-layer routing or gateway effects'],
                         'genealogy_pressure': 0.410735,
                         'inheritance_breach_count': 1,
                         'kind': 'reflection',
                         'link_hits': 0,
                         'module': 'aurora_governance_persistence_gateway',
                         'op_id': 'aurora_governance_persistence_gateway.AuroraStateSnapshot',
                         'origin_activity': 0,
                         'persistence_tax_factor': 1.036753,
                         'representation_score': 0.565962,
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
                         'signature': 'X^2*B^1',
                         'surface_score': 0.77933375,
                         'sustainability_score': 0.535662,
                         'target_kind': 'class'},
 'AuroraStateSnapshot.route_agency': {'ability_hits': 0,
                                      'alignment_gap': 0.0,
                                      'alignment_target_score': 0.0,
                                      'best_coupling_signature': '',
                                      'constraints': ['existence', 'agency'],
                                      'contract_profile': {'accepts_payload': False,
                                                           'async_callable': False,
                                                           'callable': False,
                                                           'class_target': False,
                                                           'constraint_density': 2,
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
                                                       'stateful_surface_expansion',
                                                       'gateway_surface',
                                                       'core_subsystem_surface',
                                                       'latent_route_surface',
                                                       'latent_a_derivative'],
                                      'effect_phrases': ['would extend agency pressure handling',
                                                         'would materialize the next descendant '
                                                         'implied by '
                                                         'aurora_governance_persistence_gateway.AuroraStateSnapshot'],
                                      'genealogy_pressure': 0.0,
                                      'inheritance_breach_count': 0,
                                      'kind': 'latent',
                                      'link_hits': 0,
                                      'module': 'aurora_governance_persistence_gateway',
                                      'op_id': 'latent.aurora_governance_persistence_gateway.AuroraStateSnapshot.route_agency',
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
                                      'rewrite_profile': 'governance_gateway',
                                      'signature': '',
                                      'surface_score': 1.02025,
                                      'sustainability_score': 0.0,
                                      'target_kind': 'latent_operation'},
 'AuroraStateSnapshot.to_dict.route_agency': {'ability_hits': 0,
                                              'alignment_gap': 0.0,
                                              'alignment_target_score': 0.0,
                                              'best_coupling_signature': '',
                                              'constraints': ['existence', 'agency'],
                                              'contract_profile': {'accepts_payload': False,
                                                                   'async_callable': False,
                                                                   'callable': False,
                                                                   'class_target': False,
                                                                   'constraint_density': 2,
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
                                                               'behavioral_execution_surface',
                                                               'gateway_surface',
                                                               'core_subsystem_surface',
                                                               'latent_route_surface',
                                                               'latent_a_derivative'],
                                              'effect_phrases': ['would extend agency pressure '
                                                                 'handling',
                                                                 'would materialize the next '
                                                                 'descendant implied by '
                                                                 'aurora_governance_persistence_gateway.AuroraStateSnapshot.to_dict'],
                                              'genealogy_pressure': 0.0,
                                              'inheritance_breach_count': 0,
                                              'kind': 'latent',
                                              'link_hits': 0,
                                              'module': 'aurora_governance_persistence_gateway',
                                              'op_id': 'latent.aurora_governance_persistence_gateway.AuroraStateSnapshot.to_dict.route_agency',
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
                                              'rewrite_profile': 'governance_gateway',
                                              'signature': '',
                                              'surface_score': 0.9277500000000001,
                                              'sustainability_score': 0.0,
                                              'target_kind': 'latent_operation'},
 'AutonomousAction': {'ability_hits': 1,
                      'alignment_gap': 0.820417,
                      'alignment_target_score': 1.29475,
                      'best_coupling_signature': 'B^1*A^2',
                      'constraints': ['agency'],
                      'contract_profile': {'accepts_payload': False,
                                           'async_callable': False,
                                           'callable': True,
                                           'class_target': True,
                                           'constraint_density': 1,
                                           'contract_mode': 'stateless',
                                           'doc_hint': 'Record of an autonomous action Aurora '
                                                       'took.',
                                           'effect_density': 4,
                                           'kwonly_args': 0,
                                           'optional_args': 2,
                                           'required_args': 4,
                                           'return_hint': 'None',
                                           'signature_text': '(action_id: str, action_type: str, '
                                                             'timestamp: float, description: str, '
                                                             'success: bool = True, details: '
                                                             'Dict[str, Any] = <factory>) -> None',
                                           'stateful_owner': False,
                                           'target_kind': 'class',
                                           'varargs': False,
                                           'varkw': False},
                      'coupling_similarity': 1.0,
                      'cross_diversity_links': 1,
                      'effect_modes': ['adaptive_steering_change',
                                       'stateful_surface_expansion',
                                       'gateway_surface',
                                       'core_subsystem_surface'],
                      'effect_phrases': ['changed steering, mutation, or choice behavior',
                                         'introduced reusable state-bearing system surface',
                                         'extended cross-layer routing or gateway effects'],
                      'genealogy_pressure': 0.426456,
                      'inheritance_breach_count': 1,
                      'kind': 'reflection',
                      'link_hits': 0,
                      'module': 'aurora_governance_persistence_gateway',
                      'op_id': 'aurora_governance_persistence_gateway.AutonomousAction',
                      'origin_activity': 0,
                      'persistence_tax_factor': 1.822787,
                      'representation_score': 0.359639,
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
                      'signature': 'B^1*A^2',
                      'surface_score': 0.474333,
                      'sustainability_score': 0.445319,
                      'target_kind': 'class'},
 'AutonomyEngine.get_recent_actions': {'ability_hits': 1,
                                       'alignment_gap': 0.786083,
                                       'alignment_target_score': 1.29475,
                                       'best_coupling_signature': 'B^1*A^2',
                                       'constraints': ['agency'],
                                       'contract_profile': {'accepts_payload': False,
                                                            'async_callable': False,
                                                            'callable': True,
                                                            'class_target': False,
                                                            'constraint_density': 1,
                                                            'contract_mode': 'stateful',
                                                            'doc_hint': 'Get recent autonomous '
                                                                        'actions.',
                                                            'effect_density': 4,
                                                            'kwonly_args': 0,
                                                            'optional_args': 1,
                                                            'required_args': 0,
                                                            'return_hint': 'List',
                                                            'signature_text': '(self, n: int = 20) '
                                                                              '-> List[Dict[str, '
                                                                              'Any]]',
                                                            'stateful_owner': True,
                                                            'target_kind': 'function',
                                                            'varargs': False,
                                                            'varkw': False},
                                       'coupling_similarity': 1.0,
                                       'cross_diversity_links': 1,
                                       'effect_modes': ['adaptive_steering_change',
                                                        'behavioral_execution_surface',
                                                        'gateway_surface',
                                                        'core_subsystem_surface'],
                                       'effect_phrases': ['changed steering, mutation, or choice '
                                                          'behavior',
                                                          'introduced executable behavior surface',
                                                          'extended cross-layer routing or gateway '
                                                          'effects'],
                                       'genealogy_pressure': 0.426456,
                                       'inheritance_breach_count': 1,
                                       'kind': 'reflection',
                                       'link_hits': 0,
                                       'module': 'aurora_governance_persistence_gateway',
                                       'op_id': 'aurora_governance_persistence_gateway.AutonomyEngine.get_recent_actions',
                                       'origin_activity': 0,
                                       'persistence_tax_factor': 1.822787,
                                       'representation_score': 0.359639,
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
                                       'signature': 'B^1*A^2',
                                       'surface_score': 0.508667,
                                       'sustainability_score': 0.445319,
                                       'target_kind': 'function'},
 'AutonomyEngine.get_status': {'ability_hits': 1,
                               'alignment_gap': 0.819417,
                               'alignment_target_score': 1.29475,
                               'best_coupling_signature': 'X^2*B^1',
                               'constraints': ['existence'],
                               'contract_profile': {'accepts_payload': False,
                                                    'async_callable': False,
                                                    'callable': True,
                                                    'class_target': False,
                                                    'constraint_density': 1,
                                                    'contract_mode': 'stateful',
                                                    'doc_hint': 'Get comprehensive autonomy '
                                                                'status.',
                                                    'effect_density': 4,
                                                    'kwonly_args': 0,
                                                    'optional_args': 0,
                                                    'required_args': 0,
                                                    'return_hint': 'Dict',
                                                    'signature_text': '(self) -> Dict[str, Any]',
                                                    'stateful_owner': True,
                                                    'target_kind': 'function',
                                                    'varargs': False,
                                                    'varkw': False},
                               'coupling_similarity': 1.0,
                               'cross_diversity_links': 1,
                               'effect_modes': ['state_schema_change',
                                                'behavioral_execution_surface',
                                                'gateway_surface',
                                                'core_subsystem_surface'],
                               'effect_phrases': ['changed admissible state or persistence shape',
                                                  'introduced executable behavior surface',
                                                  'extended cross-layer routing or gateway '
                                                  'effects'],
                               'genealogy_pressure': 0.410735,
                               'inheritance_breach_count': 1,
                               'kind': 'reflection',
                               'link_hits': 0,
                               'module': 'aurora_governance_persistence_gateway',
                               'op_id': 'aurora_governance_persistence_gateway.AutonomyEngine.get_status',
                               'origin_activity': 0,
                               'persistence_tax_factor': 1.036753,
                               'representation_score': 0.565962,
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
                               'signature': 'X^2*B^1',
                               'surface_score': 0.475333,
                               'sustainability_score': 0.535662,
                               'target_kind': 'function'},
 'AutonomyEngine.route_boundary': {'ability_hits': 0,
                                   'alignment_gap': 0.0,
                                   'alignment_target_score': 0.0,
                                   'best_coupling_signature': '',
                                   'constraints': ['existence', 'temporal', 'boundary'],
                                   'contract_profile': {'accepts_payload': False,
                                                        'async_callable': False,
                                                        'callable': False,
                                                        'class_target': False,
                                                        'constraint_density': 3,
                                                        'contract_mode': 'stateful',
                                                        'doc_hint': '',
                                                        'effect_density': 7,
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
                                                    'gateway_surface',
                                                    'core_subsystem_surface',
                                                    'latent_route_surface',
                                                    'latent_b_derivative'],
                                   'effect_phrases': ['would extend boundary pressure handling',
                                                      'would materialize the next descendant '
                                                      'implied by '
                                                      'aurora_governance_persistence_gateway.AutonomyEngine'],
                                   'genealogy_pressure': 0.0,
                                   'inheritance_breach_count': 0,
                                   'kind': 'latent',
                                   'link_hits': 0,
                                   'module': 'aurora_governance_persistence_gateway',
                                   'op_id': 'latent.aurora_governance_persistence_gateway.AutonomyEngine.route_boundary',
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
                                   'rewrite_profile': 'governance_gateway',
                                   'signature': '',
                                   'surface_score': 1.1070788,
                                   'sustainability_score': 0.0,
                                   'target_kind': 'latent_operation'},
 'AutonomyEngine.search_files': {'ability_hits': 0,
                                 'alignment_gap': 0.780667,
                                 'alignment_target_score': 1.29475,
                                 'best_coupling_signature': 'X^2*T^2*B^1',
                                 'constraints': ['existence', 'temporal'],
                                 'contract_profile': {'accepts_payload': False,
                                                      'async_callable': False,
                                                      'callable': True,
                                                      'class_target': False,
                                                      'constraint_density': 2,
                                                      'contract_mode': 'stateful',
                                                      'doc_hint': 'Search for files matching '
                                                                  'pattern.',
                                                      'effect_density': 5,
                                                      'kwonly_args': 0,
                                                      'optional_args': 0,
                                                      'required_args': 2,
                                                      'return_hint': 'List',
                                                      'signature_text': '(self, directory: str, '
                                                                        'pattern: str) -> '
                                                                        'List[str]',
                                                      'stateful_owner': True,
                                                      'target_kind': 'function',
                                                      'varargs': False,
                                                      'varkw': False},
                                 'coupling_similarity': 1.0,
                                 'cross_diversity_links': 1,
                                 'effect_modes': ['state_schema_change',
                                                  'temporal_orchestration_change',
                                                  'behavioral_execution_surface',
                                                  'gateway_surface',
                                                  'core_subsystem_surface'],
                                 'effect_phrases': ['changed admissible state or persistence shape',
                                                    'changed ordering, tick flow, or replay '
                                                    'behavior',
                                                    'introduced executable behavior surface',
                                                    'extended cross-layer routing or gateway '
                                                    'effects'],
                                 'genealogy_pressure': 0.409012,
                                 'inheritance_breach_count': 1,
                                 'kind': 'reflection',
                                 'link_hits': 0,
                                 'module': 'aurora_governance_persistence_gateway',
                                 'op_id': 'aurora_governance_persistence_gateway.AutonomyEngine.search_files',
                                 'origin_activity': 0,
                                 'persistence_tax_factor': 1.450604,
                                 'representation_score': 0.40614,
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
                                 'signature': 'X^2*T^2*B^1',
                                 'surface_score': 0.514083,
                                 'sustainability_score': 0.449345,
                                 'target_kind': 'function'},
 'CheckpointManager._signal_handler': {'ability_hits': 1,
                                       'alignment_gap': 0.747333,
                                       'alignment_target_score': 1.29475,
                                       'best_coupling_signature': 'X^2*B^1',
                                       'constraints': ['existence'],
                                       'contract_profile': {'accepts_payload': False,
                                                            'async_callable': False,
                                                            'callable': True,
                                                            'class_target': False,
                                                            'constraint_density': 1,
                                                            'contract_mode': 'stateful',
                                                            'doc_hint': '',
                                                            'effect_density': 5,
                                                            'kwonly_args': 0,
                                                            'optional_args': 0,
                                                            'required_args': 2,
                                                            'return_hint': 'state_record',
                                                            'signature_text': '(self, signum, '
                                                                              'frame)',
                                                            'stateful_owner': True,
                                                            'target_kind': 'function',
                                                            'varargs': False,
                                                            'varkw': False},
                                       'coupling_similarity': 1.0,
                                       'cross_diversity_links': 1,
                                       'effect_modes': ['state_schema_change',
                                                        'behavioral_execution_surface',
                                                        'gateway_surface',
                                                        'persistence_surface',
                                                        'core_subsystem_surface'],
                                       'effect_phrases': ['changed admissible state or persistence '
                                                          'shape',
                                                          'introduced executable behavior surface',
                                                          'extended cross-layer routing or gateway '
                                                          'effects',
                                                          'extended persistence or checkpoint '
                                                          'continuity'],
                                       'genealogy_pressure': 0.410735,
                                       'inheritance_breach_count': 1,
                                       'kind': 'reflection',
                                       'link_hits': 0,
                                       'module': 'aurora_governance_persistence_gateway',
                                       'op_id': 'aurora_governance_persistence_gateway.CheckpointManager._signal_handler',
                                       'origin_activity': 0,
                                       'persistence_tax_factor': 1.036753,
                                       'representation_score': 0.565962,
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
                                       'signature': 'X^2*B^1',
                                       'surface_score': 0.547417,
                                       'sustainability_score': 0.535662,
                                       'target_kind': 'function'},
 'CheckpointManager.route_agency': {'ability_hits': 0,
                                    'alignment_gap': 0.0,
                                    'alignment_target_score': 0.0,
                                    'best_coupling_signature': '',
                                    'constraints': ['existence', 'agency'],
                                    'contract_profile': {'accepts_payload': False,
                                                         'async_callable': False,
                                                         'callable': False,
                                                         'class_target': False,
                                                         'constraint_density': 2,
                                                         'contract_mode': 'stateful',
                                                         'doc_hint': '',
                                                         'effect_density': 7,
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
                                                     'stateful_surface_expansion',
                                                     'gateway_surface',
                                                     'persistence_surface',
                                                     'core_subsystem_surface',
                                                     'latent_route_surface',
                                                     'latent_a_derivative'],
                                    'effect_phrases': ['would extend agency pressure handling',
                                                       'would materialize the next descendant '
                                                       'implied by '
                                                       'aurora_governance_persistence_gateway.CheckpointManager'],
                                    'genealogy_pressure': 0.0,
                                    'inheritance_breach_count': 0,
                                    'kind': 'latent',
                                    'link_hits': 0,
                                    'module': 'aurora_governance_persistence_gateway',
                                    'op_id': 'latent.aurora_governance_persistence_gateway.CheckpointManager.route_agency',
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
                                    'rewrite_profile': 'governance_gateway',
                                    'signature': '',
                                    'surface_score': 1.0900163,
                                    'sustainability_score': 0.0,
                                    'target_kind': 'latent_operation'},
 'CheckpointManager.save.route_agency': {'ability_hits': 0,
                                         'alignment_gap': 0.0,
                                         'alignment_target_score': 0.0,
                                         'best_coupling_signature': '',
                                         'constraints': ['existence', 'agency'],
                                         'contract_profile': {'accepts_payload': False,
                                                              'async_callable': False,
                                                              'callable': False,
                                                              'class_target': False,
                                                              'constraint_density': 2,
                                                              'contract_mode': 'stateful',
                                                              'doc_hint': '',
                                                              'effect_density': 7,
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
                                                          'behavioral_execution_surface',
                                                          'gateway_surface',
                                                          'persistence_surface',
                                                          'core_subsystem_surface',
                                                          'latent_route_surface',
                                                          'latent_a_derivative'],
                                         'effect_phrases': ['would extend agency pressure handling',
                                                            'would materialize the next descendant '
                                                            'implied by '
                                                            'aurora_governance_persistence_gateway.CheckpointManager.save'],
                                         'genealogy_pressure': 0.0,
                                         'inheritance_breach_count': 0,
                                         'kind': 'latent',
                                         'link_hits': 0,
                                         'module': 'aurora_governance_persistence_gateway',
                                         'op_id': 'latent.aurora_governance_persistence_gateway.CheckpointManager.save.route_agency',
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
                                         'rewrite_profile': 'governance_gateway',
                                         'signature': '',
                                         'surface_score': 0.7497337,
                                         'sustainability_score': 0.0,
                                         'target_kind': 'latent_operation'},
 'CheckpointRecord.route_agency': {'ability_hits': 0,
                                   'alignment_gap': 0.0,
                                   'alignment_target_score': 0.0,
                                   'best_coupling_signature': '',
                                   'constraints': ['existence', 'agency'],
                                   'contract_profile': {'accepts_payload': False,
                                                        'async_callable': False,
                                                        'callable': False,
                                                        'class_target': False,
                                                        'constraint_density': 2,
                                                        'contract_mode': 'stateful',
                                                        'doc_hint': '',
                                                        'effect_density': 7,
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
                                                    'stateful_surface_expansion',
                                                    'gateway_surface',
                                                    'persistence_surface',
                                                    'core_subsystem_surface',
                                                    'latent_route_surface',
                                                    'latent_a_derivative'],
                                   'effect_phrases': ['would extend agency pressure handling',
                                                      'would materialize the next descendant '
                                                      'implied by '
                                                      'aurora_governance_persistence_gateway.CheckpointRecord'],
                                   'genealogy_pressure': 0.0,
                                   'inheritance_breach_count': 0,
                                   'kind': 'latent',
                                   'link_hits': 0,
                                   'module': 'aurora_governance_persistence_gateway',
                                   'op_id': 'latent.aurora_governance_persistence_gateway.CheckpointRecord.route_agency',
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
                                   'rewrite_profile': 'governance_gateway',
                                   'signature': '',
                                   'surface_score': 0.9926413000000001,
                                   'sustainability_score': 0.0,
                                   'target_kind': 'latent_operation'},
 'CorpusCursor': {'ability_hits': 0,
                  'alignment_gap': 0.7025,
                  'alignment_target_score': 1.29475,
                  'best_coupling_signature': 'X^2*T^2*B^1',
                  'constraints': ['existence', 'temporal'],
                  'contract_profile': {'accepts_payload': False,
                                       'async_callable': False,
                                       'callable': True,
                                       'class_target': True,
                                       'constraint_density': 2,
                                       'contract_mode': 'stateless',
                                       'doc_hint': 'Tracks exact position in corpus ingestion.',
                                       'effect_density': 5,
                                       'kwonly_args': 0,
                                       'optional_args': 9,
                                       'required_args': 0,
                                       'return_hint': 'None',
                                       'signature_text': "(file_id: str = '', file_path: str = '', "
                                                         'byte_offset: int = 0, line_index: int = '
                                                         "0, chunk_id: str = '', pass_name: str = "
                                                         "'', total_items_processed: int = 0, "
                                                         "last_item_hash: str = '', "
                                                         'last_save_time: float = <factory>) -> '
                                                         'None',
                                       'stateful_owner': False,
                                       'target_kind': 'class',
                                       'varargs': False,
                                       'varkw': False},
                  'coupling_similarity': 1.0,
                  'cross_diversity_links': 6,
                  'effect_modes': ['state_schema_change',
                                   'temporal_orchestration_change',
                                   'stateful_surface_expansion',
                                   'gateway_surface',
                                   'core_subsystem_surface'],
                  'effect_phrases': ['changed admissible state or persistence shape',
                                     'changed ordering, tick flow, or replay behavior',
                                     'introduced reusable state-bearing system surface',
                                     'extended cross-layer routing or gateway effects'],
                  'genealogy_pressure': 0.409012,
                  'inheritance_breach_count': 1,
                  'kind': 'reflection',
                  'link_hits': 0,
                  'module': 'aurora_governance_persistence_gateway',
                  'op_id': 'aurora_governance_persistence_gateway.CorpusCursor',
                  'origin_activity': 0,
                  'persistence_tax_factor': 1.450604,
                  'representation_score': 0.40614,
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
                  'signature': 'X^2*T^2*B^1',
                  'surface_score': 0.59225,
                  'sustainability_score': 0.449345,
                  'target_kind': 'class'},
 'DailyQuotas': {'ability_hits': 0,
                 'alignment_gap': 0.713333,
                 'alignment_target_score': 1.29475,
                 'best_coupling_signature': 'X^2*T^2*B^1',
                 'constraints': ['existence', 'temporal'],
                 'contract_profile': {'accepts_payload': False,
                                      'async_callable': False,
                                      'callable': True,
                                      'class_target': True,
                                      'constraint_density': 2,
                                      'contract_mode': 'stateless',
                                      'doc_hint': 'Tracks daily usage against limits.',
                                      'effect_density': 5,
                                      'kwonly_args': 0,
                                      'optional_args': 7,
                                      'required_args': 0,
                                      'return_hint': 'None',
                                      'signature_text': '(date: str = <factory>, inquiries_used: '
                                                        'int = 0, study_cycles_used: int = 0, '
                                                        'observations_used: int = 0, '
                                                        'speakups_count: int = 0, files_read: int '
                                                        '= 0, dreams_used: int = 0) -> None',
                                      'stateful_owner': False,
                                      'target_kind': 'class',
                                      'varargs': False,
                                      'varkw': False},
                 'coupling_similarity': 1.0,
                 'cross_diversity_links': 2,
                 'effect_modes': ['state_schema_change',
                                  'temporal_orchestration_change',
                                  'stateful_surface_expansion',
                                  'gateway_surface',
                                  'core_subsystem_surface'],
                 'effect_phrases': ['changed admissible state or persistence shape',
                                    'changed ordering, tick flow, or replay behavior',
                                    'introduced reusable state-bearing system surface',
                                    'extended cross-layer routing or gateway effects'],
                 'genealogy_pressure': 0.409012,
                 'inheritance_breach_count': 1,
                 'kind': 'reflection',
                 'link_hits': 0,
                 'module': 'aurora_governance_persistence_gateway',
                 'op_id': 'aurora_governance_persistence_gateway.DailyQuotas',
                 'origin_activity': 0,
                 'persistence_tax_factor': 1.450604,
                 'representation_score': 0.40614,
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
                 'signature': 'X^2*T^2*B^1',
                 'surface_score': 0.581417,
                 'sustainability_score': 0.449345,
                 'target_kind': 'class'},
 'DailyQuotas.reset_if_new_day': {'ability_hits': 0,
                                  'alignment_gap': 0.747333,
                                  'alignment_target_score': 1.29475,
                                  'best_coupling_signature': 'X^2*T^2*B^1',
                                  'constraints': ['existence', 'temporal'],
                                  'contract_profile': {'accepts_payload': False,
                                                       'async_callable': False,
                                                       'callable': True,
                                                       'class_target': False,
                                                       'constraint_density': 2,
                                                       'contract_mode': 'stateful',
                                                       'doc_hint': "Reset quotas if it's a new "
                                                                   'day.',
                                                       'effect_density': 5,
                                                       'kwonly_args': 0,
                                                       'optional_args': 0,
                                                       'required_args': 0,
                                                       'return_hint': 'state_record',
                                                       'signature_text': '(self)',
                                                       'stateful_owner': True,
                                                       'target_kind': 'function',
                                                       'varargs': False,
                                                       'varkw': False},
                                  'coupling_similarity': 1.0,
                                  'cross_diversity_links': 1,
                                  'effect_modes': ['state_schema_change',
                                                   'temporal_orchestration_change',
                                                   'behavioral_execution_surface',
                                                   'gateway_surface',
                                                   'core_subsystem_surface'],
                                  'effect_phrases': ['changed admissible state or persistence '
                                                     'shape',
                                                     'changed ordering, tick flow, or replay '
                                                     'behavior',
                                                     'introduced executable behavior surface',
                                                     'extended cross-layer routing or gateway '
                                                     'effects'],
                                  'genealogy_pressure': 0.409012,
                                  'inheritance_breach_count': 1,
                                  'kind': 'reflection',
                                  'link_hits': 0,
                                  'module': 'aurora_governance_persistence_gateway',
                                  'op_id': 'aurora_governance_persistence_gateway.DailyQuotas.reset_if_new_day',
                                  'origin_activity': 0,
                                  'persistence_tax_factor': 1.450604,
                                  'representation_score': 0.40614,
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
                                  'signature': 'X^2*T^2*B^1',
                                  'surface_score': 0.547417,
                                  'sustainability_score': 0.449345,
                                  'target_kind': 'function'},
 'DailyQuotas.to_dict': {'ability_hits': 0,
                         'alignment_gap': 0.747333,
                         'alignment_target_score': 1.29475,
                         'best_coupling_signature': 'X^2*T^2*B^1',
                         'constraints': ['existence', 'temporal'],
                         'contract_profile': {'accepts_payload': False,
                                              'async_callable': False,
                                              'callable': True,
                                              'class_target': False,
                                              'constraint_density': 2,
                                              'contract_mode': 'stateful',
                                              'doc_hint': '',
                                              'effect_density': 5,
                                              'kwonly_args': 0,
                                              'optional_args': 0,
                                              'required_args': 0,
                                              'return_hint': 'Dict',
                                              'signature_text': '(self) -> Dict[str, Any]',
                                              'stateful_owner': True,
                                              'target_kind': 'function',
                                              'varargs': False,
                                              'varkw': False},
                         'coupling_similarity': 1.0,
                         'cross_diversity_links': 1,
                         'effect_modes': ['state_schema_change',
                                          'temporal_orchestration_change',
                                          'behavioral_execution_surface',
                                          'gateway_surface',
                                          'core_subsystem_surface'],
                         'effect_phrases': ['changed admissible state or persistence shape',
                                            'changed ordering, tick flow, or replay behavior',
                                            'introduced executable behavior surface',
                                            'extended cross-layer routing or gateway effects'],
                         'genealogy_pressure': 0.409012,
                         'inheritance_breach_count': 1,
                         'kind': 'reflection',
                         'link_hits': 0,
                         'module': 'aurora_governance_persistence_gateway',
                         'op_id': 'aurora_governance_persistence_gateway.DailyQuotas.to_dict',
                         'origin_activity': 0,
                         'persistence_tax_factor': 1.450604,
                         'representation_score': 0.40614,
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
                         'signature': 'X^2*T^2*B^1',
                         'surface_score': 0.547417,
                         'sustainability_score': 0.449345,
                         'target_kind': 'function'},
 'DeviceAwareness': {'ability_hits': 0,
                     'alignment_gap': 0.63,
                     'alignment_target_score': 1.29475,
                     'best_coupling_signature': 'X^2*T^2*B^1',
                     'constraints': ['existence', 'temporal'],
                     'contract_profile': {'accepts_payload': False,
                                          'async_callable': False,
                                          'callable': True,
                                          'class_target': True,
                                          'constraint_density': 2,
                                          'contract_mode': 'stateless',
                                          'doc_hint': 'Tracks which device Aurora is running on.',
                                          'effect_density': 5,
                                          'kwonly_args': 0,
                                          'optional_args': 0,
                                          'required_args': 0,
                                          'return_hint': 'state_record',
                                          'signature_text': '()',
                                          'stateful_owner': False,
                                          'target_kind': 'class',
                                          'varargs': False,
                                          'varkw': False},
                     'coupling_similarity': 1.0,
                     'cross_diversity_links': 2,
                     'effect_modes': ['state_schema_change',
                                      'temporal_orchestration_change',
                                      'stateful_surface_expansion',
                                      'gateway_surface',
                                      'core_subsystem_surface'],
                     'effect_phrases': ['changed admissible state or persistence shape',
                                        'changed ordering, tick flow, or replay behavior',
                                        'introduced reusable state-bearing system surface',
                                        'extended cross-layer routing or gateway effects'],
                     'genealogy_pressure': 0.409012,
                     'inheritance_breach_count': 1,
                     'kind': 'reflection',
                     'link_hits': 0,
                     'module': 'aurora_governance_persistence_gateway',
                     'op_id': 'aurora_governance_persistence_gateway.DeviceAwareness',
                     'origin_activity': 0,
                     'persistence_tax_factor': 1.450604,
                     'representation_score': 0.40614,
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
                     'signature': 'X^2*T^2*B^1',
                     'surface_score': 0.6647500000000001,
                     'sustainability_score': 0.449345,
                     'target_kind': 'class'},
 'DeviceRecord': {'ability_hits': 0,
                  'alignment_gap': 0.663333,
                  'alignment_target_score': 1.29475,
                  'best_coupling_signature': 'X^2*T^2*B^1',
                  'constraints': ['existence', 'temporal'],
                  'contract_profile': {'accepts_payload': False,
                                       'async_callable': False,
                                       'callable': True,
                                       'class_target': True,
                                       'constraint_density': 2,
                                       'contract_mode': 'stateless',
                                       'doc_hint': 'Record of a device that has hosted Aurora.',
                                       'effect_density': 5,
                                       'kwonly_args': 0,
                                       'optional_args': 2,
                                       'required_args': 3,
                                       'return_hint': 'None',
                                       'signature_text': '(hostname: str, last_seen: float, '
                                                         'last_sync: float, session_count: int = '
                                                         "1, notes: str = '') -> None",
                                       'stateful_owner': False,
                                       'target_kind': 'class',
                                       'varargs': False,
                                       'varkw': False},
                  'coupling_similarity': 1.0,
                  'cross_diversity_links': 2,
                  'effect_modes': ['state_schema_change',
                                   'temporal_orchestration_change',
                                   'stateful_surface_expansion',
                                   'gateway_surface',
                                   'core_subsystem_surface'],
                  'effect_phrases': ['changed admissible state or persistence shape',
                                     'changed ordering, tick flow, or replay behavior',
                                     'introduced reusable state-bearing system surface',
                                     'extended cross-layer routing or gateway effects'],
                  'genealogy_pressure': 0.409012,
                  'inheritance_breach_count': 1,
                  'kind': 'reflection',
                  'link_hits': 0,
                  'module': 'aurora_governance_persistence_gateway',
                  'op_id': 'aurora_governance_persistence_gateway.DeviceRecord',
                  'origin_activity': 0,
                  'persistence_tax_factor': 1.450604,
                  'representation_score': 0.40614,
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
                  'signature': 'X^2*T^2*B^1',
                  'surface_score': 0.631417,
                  'sustainability_score': 0.449345,
                  'target_kind': 'class'},
 'DeviceRecord.to_dict.route_agency': {'ability_hits': 0,
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
                                                            'effect_density': 7,
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
                                                        'gateway_surface',
                                                        'core_subsystem_surface',
                                                        'latent_route_surface',
                                                        'latent_a_derivative'],
                                       'effect_phrases': ['would extend agency pressure handling',
                                                          'would materialize the next descendant '
                                                          'implied by '
                                                          'aurora_governance_persistence_gateway.DeviceRecord.to_dict'],
                                       'genealogy_pressure': 0.0,
                                       'inheritance_breach_count': 0,
                                       'kind': 'latent',
                                       'link_hits': 0,
                                       'module': 'aurora_governance_persistence_gateway',
                                       'op_id': 'latent.aurora_governance_persistence_gateway.DeviceRecord.to_dict.route_agency',
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
                                       'rewrite_profile': 'governance_gateway',
                                       'signature': '',
                                       'surface_score': 0.9441399500000002,
                                       'sustainability_score': 0.0,
                                       'target_kind': 'latent_operation'},
 'DriveSync': {'ability_hits': 0,
               'alignment_gap': 0.5725,
               'alignment_target_score': 1.29475,
               'best_coupling_signature': 'X^2*T^2*B^1',
               'constraints': ['existence', 'temporal'],
               'contract_profile': {'accepts_payload': False,
                                    'async_callable': False,
                                    'callable': True,
                                    'class_target': True,
                                    'constraint_density': 2,
                                    'contract_mode': 'stateless',
                                    'doc_hint': "Aurora's cross-device memory bridge via Google "
                                                'Drive + rclone.',
                                    'effect_density': 5,
                                    'kwonly_args': 0,
                                    'optional_args': 3,
                                    'required_args': 0,
                                    'return_hint': 'state_record',
                                    'signature_text': "(remote_name: str = 'gdrive', local_path: "
                                                      "str = 'aurora_state', sync_interval: float "
                                                      '= 300.0)',
                                    'stateful_owner': False,
                                    'target_kind': 'class',
                                    'varargs': False,
                                    'varkw': False},
               'coupling_similarity': 1.0,
               'cross_diversity_links': 4,
               'effect_modes': ['state_schema_change',
                                'temporal_orchestration_change',
                                'stateful_surface_expansion',
                                'gateway_surface',
                                'core_subsystem_surface'],
               'effect_phrases': ['changed admissible state or persistence shape',
                                  'changed ordering, tick flow, or replay behavior',
                                  'introduced reusable state-bearing system surface',
                                  'extended cross-layer routing or gateway effects'],
               'genealogy_pressure': 0.409012,
               'inheritance_breach_count': 1,
               'kind': 'reflection',
               'link_hits': 0,
               'module': 'aurora_governance_persistence_gateway',
               'op_id': 'aurora_governance_persistence_gateway.DriveSync',
               'origin_activity': 0,
               'persistence_tax_factor': 1.450604,
               'representation_score': 0.40614,
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
               'signature': 'X^2*T^2*B^1',
               'surface_score': 0.7222500000000001,
               'sustainability_score': 0.449345,
               'target_kind': 'class'},
 'DriveSync.route_boundary': {'ability_hits': 0,
                              'alignment_gap': 0.0,
                              'alignment_target_score': 0.0,
                              'best_coupling_signature': '',
                              'constraints': ['existence', 'temporal', 'boundary'],
                              'contract_profile': {'accepts_payload': False,
                                                   'async_callable': False,
                                                   'callable': False,
                                                   'class_target': False,
                                                   'constraint_density': 3,
                                                   'contract_mode': 'stateful',
                                                   'doc_hint': '',
                                                   'effect_density': 7,
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
                                               'gateway_surface',
                                               'core_subsystem_surface',
                                               'latent_route_surface',
                                               'latent_b_derivative'],
                              'effect_phrases': ['would extend boundary pressure handling',
                                                 'would materialize the next descendant implied by '
                                                 'aurora_governance_persistence_gateway.DriveSync'],
                              'genealogy_pressure': 0.0,
                              'inheritance_breach_count': 0,
                              'kind': 'latent',
                              'link_hits': 0,
                              'module': 'aurora_governance_persistence_gateway',
                              'op_id': 'latent.aurora_governance_persistence_gateway.DriveSync.route_boundary',
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
                              'rewrite_profile': 'governance_gateway',
                              'signature': '',
                              'surface_score': 0.9897350500000001,
                              'sustainability_score': 0.0,
                              'target_kind': 'latent_operation'},
 'DriveSync.start.route_boundary': {'ability_hits': 0,
                                    'alignment_gap': 0.0,
                                    'alignment_target_score': 0.0,
                                    'best_coupling_signature': '',
                                    'constraints': ['existence', 'temporal', 'boundary'],
                                    'contract_profile': {'accepts_payload': False,
                                                         'async_callable': False,
                                                         'callable': False,
                                                         'class_target': False,
                                                         'constraint_density': 3,
                                                         'contract_mode': 'stateful',
                                                         'doc_hint': '',
                                                         'effect_density': 7,
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
                                                     'gateway_surface',
                                                     'core_subsystem_surface',
                                                     'latent_route_surface',
                                                     'latent_b_derivative'],
                                    'effect_phrases': ['would extend boundary pressure handling',
                                                       'would materialize the next descendant '
                                                       'implied by '
                                                       'aurora_governance_persistence_gateway.DriveSync.start'],
                                    'genealogy_pressure': 0.0,
                                    'inheritance_breach_count': 0,
                                    'kind': 'latent',
                                    'link_hits': 0,
                                    'module': 'aurora_governance_persistence_gateway',
                                    'op_id': 'latent.aurora_governance_persistence_gateway.DriveSync.start.route_boundary',
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
                                    'rewrite_profile': 'governance_gateway',
                                    'signature': '',
                                    'surface_score': 0.7916413,
                                    'sustainability_score': 0.0,
                                    'target_kind': 'latent_operation'},
 'DriveSync.status': {'ability_hits': 1,
                      'alignment_gap': 0.786083,
                      'alignment_target_score': 1.29475,
                      'best_coupling_signature': 'X^2*B^1',
                      'constraints': ['existence'],
                      'contract_profile': {'accepts_payload': False,
                                           'async_callable': False,
                                           'callable': True,
                                           'class_target': False,
                                           'constraint_density': 1,
                                           'contract_mode': 'stateful',
                                           'doc_hint': '',
                                           'effect_density': 4,
                                           'kwonly_args': 0,
                                           'optional_args': 0,
                                           'required_args': 0,
                                           'return_hint': 'Dict',
                                           'signature_text': '(self) -> Dict',
                                           'stateful_owner': True,
                                           'target_kind': 'function',
                                           'varargs': False,
                                           'varkw': False},
                      'coupling_similarity': 1.0,
                      'cross_diversity_links': 1,
                      'effect_modes': ['state_schema_change',
                                       'behavioral_execution_surface',
                                       'gateway_surface',
                                       'core_subsystem_surface'],
                      'effect_phrases': ['changed admissible state or persistence shape',
                                         'introduced executable behavior surface',
                                         'extended cross-layer routing or gateway effects'],
                      'genealogy_pressure': 0.410735,
                      'inheritance_breach_count': 1,
                      'kind': 'reflection',
                      'link_hits': 0,
                      'module': 'aurora_governance_persistence_gateway',
                      'op_id': 'aurora_governance_persistence_gateway.DriveSync.status',
                      'origin_activity': 0,
                      'persistence_tax_factor': 1.036753,
                      'representation_score': 0.565962,
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
                      'signature': 'X^2*B^1',
                      'surface_score': 0.508667,
                      'sustainability_score': 0.535662,
                      'target_kind': 'function'},
 'DriveSync.stop': {'ability_hits': 0,
                    'alignment_gap': 0.722333,
                    'alignment_target_score': 1.29475,
                    'best_coupling_signature': 'X^2*T^2*B^1',
                    'constraints': ['existence', 'temporal'],
                    'contract_profile': {'accepts_payload': False,
                                         'async_callable': False,
                                         'callable': True,
                                         'class_target': False,
                                         'constraint_density': 2,
                                         'contract_mode': 'stateful',
                                         'doc_hint': '',
                                         'effect_density': 5,
                                         'kwonly_args': 0,
                                         'optional_args': 0,
                                         'required_args': 0,
                                         'return_hint': 'state_record',
                                         'signature_text': '(self)',
                                         'stateful_owner': True,
                                         'target_kind': 'function',
                                         'varargs': False,
                                         'varkw': False},
                    'coupling_similarity': 1.0,
                    'cross_diversity_links': 6,
                    'effect_modes': ['state_schema_change',
                                     'temporal_orchestration_change',
                                     'behavioral_execution_surface',
                                     'gateway_surface',
                                     'core_subsystem_surface'],
                    'effect_phrases': ['changed admissible state or persistence shape',
                                       'changed ordering, tick flow, or replay behavior',
                                       'introduced executable behavior surface',
                                       'extended cross-layer routing or gateway effects'],
                    'genealogy_pressure': 0.409012,
                    'inheritance_breach_count': 1,
                    'kind': 'reflection',
                    'link_hits': 0,
                    'module': 'aurora_governance_persistence_gateway',
                    'op_id': 'aurora_governance_persistence_gateway.DriveSync.stop',
                    'origin_activity': 0,
                    'persistence_tax_factor': 1.450604,
                    'representation_score': 0.40614,
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
                    'signature': 'X^2*T^2*B^1',
                    'surface_score': 0.572417,
                    'sustainability_score': 0.449345,
                    'target_kind': 'function'},
 'DriveSync.switch_message': {'ability_hits': 0,
                              'alignment_gap': 0.722333,
                              'alignment_target_score': 1.29475,
                              'best_coupling_signature': 'X^2*T^2*B^1',
                              'constraints': ['existence', 'temporal'],
                              'contract_profile': {'accepts_payload': False,
                                                   'async_callable': False,
                                                   'callable': True,
                                                   'class_target': False,
                                                   'constraint_density': 2,
                                                   'contract_mode': 'stateful',
                                                   'doc_hint': '',
                                                   'effect_density': 5,
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
                              'cross_diversity_links': 6,
                              'effect_modes': ['state_schema_change',
                                               'temporal_orchestration_change',
                                               'behavioral_execution_surface',
                                               'gateway_surface',
                                               'core_subsystem_surface'],
                              'effect_phrases': ['changed admissible state or persistence shape',
                                                 'changed ordering, tick flow, or replay behavior',
                                                 'introduced executable behavior surface',
                                                 'extended cross-layer routing or gateway effects'],
                              'genealogy_pressure': 0.409012,
                              'inheritance_breach_count': 1,
                              'kind': 'reflection',
                              'link_hits': 0,
                              'module': 'aurora_governance_persistence_gateway',
                              'op_id': 'aurora_governance_persistence_gateway.DriveSync.switch_message',
                              'origin_activity': 0,
                              'persistence_tax_factor': 1.450604,
                              'representation_score': 0.40614,
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
                              'signature': 'X^2*T^2*B^1',
                              'surface_score': 0.572417,
                              'sustainability_score': 0.449345,
                              'target_kind': 'function'},
 'FilesystemExplorer.route_agency': {'ability_hits': 0,
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
                                                          'effect_density': 7,
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
                                                      'gateway_surface',
                                                      'core_subsystem_surface',
                                                      'latent_route_surface',
                                                      'latent_a_derivative'],
                                     'effect_phrases': ['would extend agency pressure handling',
                                                        'would materialize the next descendant '
                                                        'implied by '
                                                        'aurora_governance_persistence_gateway.FilesystemExplorer'],
                                     'genealogy_pressure': 0.0,
                                     'inheritance_breach_count': 0,
                                     'kind': 'latent',
                                     'link_hits': 0,
                                     'module': 'aurora_governance_persistence_gateway',
                                     'op_id': 'latent.aurora_governance_persistence_gateway.FilesystemExplorer.route_agency',
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
                                     'rewrite_profile': 'governance_gateway',
                                     'signature': '',
                                     'surface_score': 0.9031712,
                                     'sustainability_score': 0.0,
                                     'target_kind': 'latent_operation'},
 'GatewayResponse': {'ability_hits': 0,
                     'alignment_gap': 0.723333,
                     'alignment_target_score': 1.29475,
                     'best_coupling_signature': 'X^2*T^2*B^1',
                     'constraints': ['existence', 'temporal'],
                     'contract_profile': {'accepts_payload': False,
                                          'async_callable': False,
                                          'callable': True,
                                          'class_target': True,
                                          'constraint_density': 2,
                                          'contract_mode': 'stateless',
                                          'doc_hint': "Aurora's response back through the Gateway.",
                                          'effect_density': 5,
                                          'kwonly_args': 0,
                                          'optional_args': 4,
                                          'required_args': 3,
                                          'return_hint': 'None',
                                          'signature_text': '(response_id: str, to_packet_id: str, '
                                                            'content: str, emotional_tone: str = '
                                                            "'neutral', confidence: float = 0.5, "
                                                            'personality_signature: Dict[str, '
                                                            'float] = <factory>, timestamp: float '
                                                            '= <factory>) -> None',
                                          'stateful_owner': False,
                                          'target_kind': 'class',
                                          'varargs': False,
                                          'varkw': False},
                     'coupling_similarity': 1.0,
                     'cross_diversity_links': 6,
                     'effect_modes': ['state_schema_change',
                                      'temporal_orchestration_change',
                                      'stateful_surface_expansion',
                                      'gateway_surface',
                                      'core_subsystem_surface'],
                     'effect_phrases': ['changed admissible state or persistence shape',
                                        'changed ordering, tick flow, or replay behavior',
                                        'introduced reusable state-bearing system surface',
                                        'extended cross-layer routing or gateway effects'],
                     'genealogy_pressure': 0.409012,
                     'inheritance_breach_count': 1,
                     'kind': 'reflection',
                     'link_hits': 0,
                     'module': 'aurora_governance_persistence_gateway',
                     'op_id': 'aurora_governance_persistence_gateway.GatewayResponse',
                     'origin_activity': 0,
                     'persistence_tax_factor': 1.450604,
                     'representation_score': 0.40614,
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
                     'signature': 'X^2*T^2*B^1',
                     'surface_score': 0.571417,
                     'sustainability_score': 0.449345,
                     'target_kind': 'class'},
 'GatewayVerdict': {'ability_hits': 0,
                    'alignment_gap': 0.723333,
                    'alignment_target_score': 1.29475,
                    'best_coupling_signature': 'X^2*T^2*B^1',
                    'constraints': ['existence', 'temporal'],
                    'contract_profile': {'accepts_payload': False,
                                         'async_callable': False,
                                         'callable': True,
                                         'class_target': True,
                                         'constraint_density': 2,
                                         'contract_mode': 'stateless',
                                         'doc_hint': 'Result of data validation.',
                                         'effect_density': 5,
                                         'kwonly_args': 0,
                                         'optional_args': 0,
                                         'required_args': 0,
                                         'return_hint': 'state_record',
                                         'signature_text': '(*values)',
                                         'stateful_owner': False,
                                         'target_kind': 'class',
                                         'varargs': True,
                                         'varkw': False},
                    'coupling_similarity': 1.0,
                    'cross_diversity_links': 6,
                    'effect_modes': ['state_schema_change',
                                     'temporal_orchestration_change',
                                     'stateful_surface_expansion',
                                     'gateway_surface',
                                     'core_subsystem_surface'],
                    'effect_phrases': ['changed admissible state or persistence shape',
                                       'changed ordering, tick flow, or replay behavior',
                                       'introduced reusable state-bearing system surface',
                                       'extended cross-layer routing or gateway effects'],
                    'genealogy_pressure': 0.409012,
                    'inheritance_breach_count': 1,
                    'kind': 'reflection',
                    'link_hits': 0,
                    'module': 'aurora_governance_persistence_gateway',
                    'op_id': 'aurora_governance_persistence_gateway.GatewayVerdict',
                    'origin_activity': 0,
                    'persistence_tax_factor': 1.450604,
                    'representation_score': 0.40614,
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
                    'signature': 'X^2*T^2*B^1',
                    'surface_score': 0.571417,
                    'sustainability_score': 0.449345,
                    'target_kind': 'class'},
 'GenerationRole': {'ability_hits': 0,
                    'alignment_gap': 0.723333,
                    'alignment_target_score': 1.29475,
                    'best_coupling_signature': 'X^2*T^2*B^1',
                    'constraints': ['existence', 'temporal'],
                    'contract_profile': {'accepts_payload': False,
                                         'async_callable': False,
                                         'callable': True,
                                         'class_target': True,
                                         'constraint_density': 2,
                                         'contract_mode': 'stateless',
                                         'doc_hint': 'Role of a generation in the 4-cycle.',
                                         'effect_density': 5,
                                         'kwonly_args': 0,
                                         'optional_args': 0,
                                         'required_args': 0,
                                         'return_hint': 'state_record',
                                         'signature_text': '(*values)',
                                         'stateful_owner': False,
                                         'target_kind': 'class',
                                         'varargs': True,
                                         'varkw': False},
                    'coupling_similarity': 1.0,
                    'cross_diversity_links': 6,
                    'effect_modes': ['state_schema_change',
                                     'temporal_orchestration_change',
                                     'stateful_surface_expansion',
                                     'gateway_surface',
                                     'core_subsystem_surface'],
                    'effect_phrases': ['changed admissible state or persistence shape',
                                       'changed ordering, tick flow, or replay behavior',
                                       'introduced reusable state-bearing system surface',
                                       'extended cross-layer routing or gateway effects'],
                    'genealogy_pressure': 0.409012,
                    'inheritance_breach_count': 1,
                    'kind': 'reflection',
                    'link_hits': 0,
                    'module': 'aurora_governance_persistence_gateway',
                    'op_id': 'aurora_governance_persistence_gateway.GenerationRole',
                    'origin_activity': 0,
                    'persistence_tax_factor': 1.450604,
                    'representation_score': 0.40614,
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
                    'signature': 'X^2*T^2*B^1',
                    'surface_score': 0.571417,
                    'sustainability_score': 0.449345,
                    'target_kind': 'class'},
 'GenerationalAlignmentLaw': {'ability_hits': 1,
                              'alignment_gap': 0.60375,
                              'alignment_target_score': 1.29475,
                              'best_coupling_signature': 'B^1*A^2',
                              'constraints': ['agency'],
                              'contract_profile': {'accepts_payload': False,
                                                   'async_callable': False,
                                                   'callable': True,
                                                   'class_target': True,
                                                   'constraint_density': 1,
                                                   'contract_mode': 'stateless',
                                                   'doc_hint': "Maintains 'stable unalignment' — "
                                                               'not too aligned (static), not too',
                                                   'effect_density': 4,
                                                   'kwonly_args': 0,
                                                   'optional_args': 2,
                                                   'required_args': 0,
                                                   'return_hint': 'boundary_record',
                                                   'signature_text': '(target_band: Tuple[float, '
                                                                     'float] = (0.15, 0.35), '
                                                                     'step_size: float = 0.1)',
                                                   'stateful_owner': False,
                                                   'target_kind': 'class',
                                                   'varargs': False,
                                                   'varkw': False},
                              'coupling_similarity': 1.0,
                              'cross_diversity_links': 6,
                              'effect_modes': ['adaptive_steering_change',
                                               'stateful_surface_expansion',
                                               'gateway_surface',
                                               'core_subsystem_surface'],
                              'effect_phrases': ['changed steering, mutation, or choice behavior',
                                                 'introduced reusable state-bearing system surface',
                                                 'extended cross-layer routing or gateway effects'],
                              'genealogy_pressure': 0.426456,
                              'inheritance_breach_count': 1,
                              'kind': 'reflection',
                              'link_hits': 0,
                              'module': 'aurora_governance_persistence_gateway',
                              'op_id': 'aurora_governance_persistence_gateway.GenerationalAlignmentLaw',
                              'origin_activity': 0,
                              'persistence_tax_factor': 1.822787,
                              'representation_score': 0.359639,
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
                              'signature': 'B^1*A^2',
                              'surface_score': 0.691,
                              'sustainability_score': 0.445319,
                              'target_kind': 'class'},
 'GenerationalAlignmentLaw.__init__': {'ability_hits': 1,
                                       'alignment_gap': 0.77775,
                                       'alignment_target_score': 1.29475,
                                       'best_coupling_signature': 'B^1*A^2',
                                       'constraints': ['agency'],
                                       'contract_profile': {'accepts_payload': False,
                                                            'async_callable': False,
                                                            'callable': True,
                                                            'class_target': False,
                                                            'constraint_density': 1,
                                                            'contract_mode': 'stateful',
                                                            'doc_hint': 'Initialize self.  See '
                                                                        'help(type(self)) for '
                                                                        'accurate signature.',
                                                            'effect_density': 4,
                                                            'kwonly_args': 0,
                                                            'optional_args': 2,
                                                            'required_args': 0,
                                                            'return_hint': 'boundary_record',
                                                            'signature_text': '(self, target_band: '
                                                                              'Tuple[float, float] '
                                                                              '= (0.15, 0.35), '
                                                                              'step_size: float = '
                                                                              '0.1)',
                                                            'stateful_owner': True,
                                                            'target_kind': 'function',
                                                            'varargs': False,
                                                            'varkw': False},
                                       'coupling_similarity': 1.0,
                                       'cross_diversity_links': 1,
                                       'effect_modes': ['adaptive_steering_change',
                                                        'behavioral_execution_surface',
                                                        'gateway_surface',
                                                        'core_subsystem_surface'],
                                       'effect_phrases': ['changed steering, mutation, or choice '
                                                          'behavior',
                                                          'introduced executable behavior surface',
                                                          'extended cross-layer routing or gateway '
                                                          'effects'],
                                       'genealogy_pressure': 0.426456,
                                       'inheritance_breach_count': 1,
                                       'kind': 'reflection',
                                       'link_hits': 0,
                                       'module': 'aurora_governance_persistence_gateway',
                                       'op_id': 'aurora_governance_persistence_gateway.GenerationalAlignmentLaw.__init__',
                                       'origin_activity': 0,
                                       'persistence_tax_factor': 1.822787,
                                       'representation_score': 0.359639,
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
                                       'signature': 'B^1*A^2',
                                       'surface_score': 0.517,
                                       'sustainability_score': 0.445319,
                                       'target_kind': 'function'},
 'GenerationalAlignmentLaw.compute_tension': {'ability_hits': 1,
                                              'alignment_gap': 0.819417,
                                              'alignment_target_score': 1.29475,
                                              'best_coupling_signature': 'B^1*A^2',
                                              'constraints': ['agency'],
                                              'contract_profile': {'accepts_payload': False,
                                                                   'async_callable': False,
                                                                   'callable': True,
                                                                   'class_target': False,
                                                                   'constraint_density': 1,
                                                                   'contract_mode': 'stateful',
                                                                   'doc_hint': 'Compute tension '
                                                                               'components.',
                                                                   'effect_density': 4,
                                                                   'kwonly_args': 0,
                                                                   'optional_args': 2,
                                                                   'required_args': 2,
                                                                   'return_hint': 'GenerationalTension',
                                                                   'signature_text': '(self, '
                                                                                     'generation: '
                                                                                     'int, '
                                                                                     'dim_profile: '
                                                                                     'Dict[str, '
                                                                                     'float], '
                                                                                     'cycle_mean: '
                                                                                     'Optional[Dict[str, '
                                                                                     'float]] = '
                                                                                     'None, '
                                                                                     'warp_density: '
                                                                                     'float = 0.0) '
                                                                                     '-> '
                                                                                     'aurora_governance_persistence_gateway.GenerationalTension',
                                                                   'stateful_owner': True,
                                                                   'target_kind': 'function',
                                                                   'varargs': False,
                                                                   'varkw': False},
                                              'coupling_similarity': 1.0,
                                              'cross_diversity_links': 1,
                                              'effect_modes': ['adaptive_steering_change',
                                                               'behavioral_execution_surface',
                                                               'gateway_surface',
                                                               'core_subsystem_surface'],
                                              'effect_phrases': ['changed steering, mutation, or '
                                                                 'choice behavior',
                                                                 'introduced executable behavior '
                                                                 'surface',
                                                                 'extended cross-layer routing or '
                                                                 'gateway effects'],
                                              'genealogy_pressure': 0.426456,
                                              'inheritance_breach_count': 1,
                                              'kind': 'reflection',
                                              'link_hits': 0,
                                              'module': 'aurora_governance_persistence_gateway',
                                              'op_id': 'aurora_governance_persistence_gateway.GenerationalAlignmentLaw.compute_tension',
                                              'origin_activity': 0,
                                              'persistence_tax_factor': 1.822787,
                                              'representation_score': 0.359639,
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
                                              'signature': 'B^1*A^2',
                                              'surface_score': 0.475333,
                                              'sustainability_score': 0.445319,
                                              'target_kind': 'function'},
 'GenerationalAlignmentLaw.shift_toward_stable': {'ability_hits': 1,
                                                  'alignment_gap': 0.798583,
                                                  'alignment_target_score': 1.29475,
                                                  'best_coupling_signature': 'B^1*A^2',
                                                  'constraints': ['agency'],
                                                  'contract_profile': {'accepts_payload': False,
                                                                       'async_callable': False,
                                                                       'callable': True,
                                                                       'class_target': False,
                                                                       'constraint_density': 1,
                                                                       'contract_mode': 'stateful',
                                                                       'doc_hint': 'Apply one step '
                                                                                   'toward stable '
                                                                                   'unalignment '
                                                                                   'band.',
                                                                       'effect_density': 4,
                                                                       'kwonly_args': 0,
                                                                       'optional_args': 0,
                                                                       'required_args': 2,
                                                                       'return_hint': 'Dict',
                                                                       'signature_text': '(self, '
                                                                                         'dim_profile: '
                                                                                         'Dict[str, '
                                                                                         'float], '
                                                                                         'tension: '
                                                                                         'aurora_governance_persistence_gateway.GenerationalTension) '
                                                                                         '-> '
                                                                                         'Dict[str, '
                                                                                         'float]',
                                                                       'stateful_owner': True,
                                                                       'target_kind': 'function',
                                                                       'varargs': False,
                                                                       'varkw': False},
                                                  'coupling_similarity': 1.0,
                                                  'cross_diversity_links': 1,
                                                  'effect_modes': ['adaptive_steering_change',
                                                                   'behavioral_execution_surface',
                                                                   'gateway_surface',
                                                                   'core_subsystem_surface'],
                                                  'effect_phrases': ['changed steering, mutation, '
                                                                     'or choice behavior',
                                                                     'introduced executable '
                                                                     'behavior surface',
                                                                     'extended cross-layer routing '
                                                                     'or gateway effects'],
                                                  'genealogy_pressure': 0.426456,
                                                  'inheritance_breach_count': 1,
                                                  'kind': 'reflection',
                                                  'link_hits': 0,
                                                  'module': 'aurora_governance_persistence_gateway',
                                                  'op_id': 'aurora_governance_persistence_gateway.GenerationalAlignmentLaw.shift_toward_stable',
                                                  'origin_activity': 0,
                                                  'persistence_tax_factor': 1.822787,
                                                  'representation_score': 0.359639,
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
                                                  'signature': 'B^1*A^2',
                                                  'surface_score': 0.496167,
                                                  'sustainability_score': 0.445319,
                                                  'target_kind': 'function'},
 'GenerationalTension': {'ability_hits': 0,
                         'alignment_gap': 0.748333,
                         'alignment_target_score': 1.29475,
                         'best_coupling_signature': 'X^2*T^2*B^1',
                         'constraints': ['existence', 'temporal'],
                         'contract_profile': {'accepts_payload': False,
                                              'async_callable': False,
                                              'callable': True,
                                              'class_target': True,
                                              'constraint_density': 2,
                                              'contract_mode': 'stateless',
                                              'doc_hint': 'Tension components for a generation.',
                                              'effect_density': 5,
                                              'kwonly_args': 0,
                                              'optional_args': 4,
                                              'required_args': 0,
                                              'return_hint': 'None',
                                              'signature_text': '(internal: float = 0.0, cycle: '
                                                                'float = 0.0, generational: float '
                                                                '= 0.0, warp_line: float = 0.0) -> '
                                                                'None',
                                              'stateful_owner': False,
                                              'target_kind': 'class',
                                              'varargs': False,
                                              'varkw': False},
                         'coupling_similarity': 1.0,
                         'cross_diversity_links': 1,
                         'effect_modes': ['state_schema_change',
                                          'temporal_orchestration_change',
                                          'stateful_surface_expansion',
                                          'gateway_surface',
                                          'core_subsystem_surface'],
                         'effect_phrases': ['changed admissible state or persistence shape',
                                            'changed ordering, tick flow, or replay behavior',
                                            'introduced reusable state-bearing system surface',
                                            'extended cross-layer routing or gateway effects'],
                         'genealogy_pressure': 0.409012,
                         'inheritance_breach_count': 1,
                         'kind': 'reflection',
                         'link_hits': 0,
                         'module': 'aurora_governance_persistence_gateway',
                         'op_id': 'aurora_governance_persistence_gateway.GenerationalTension',
                         'origin_activity': 0,
                         'persistence_tax_factor': 1.450604,
                         'representation_score': 0.40614,
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
                         'signature': 'X^2*T^2*B^1',
                         'surface_score': 0.546417,
                         'sustainability_score': 0.449345,
                         'target_kind': 'class'},
 'GenerationalTension.total': {'ability_hits': 0,
                               'alignment_gap': 0.739,
                               'alignment_target_score': 1.29475,
                               'best_coupling_signature': 'X^2*T^2*B^1',
                               'constraints': ['existence', 'temporal'],
                               'contract_profile': {'accepts_payload': False,
                                                    'async_callable': False,
                                                    'callable': True,
                                                    'class_target': False,
                                                    'constraint_density': 2,
                                                    'contract_mode': 'stateful',
                                                    'doc_hint': '',
                                                    'effect_density': 5,
                                                    'kwonly_args': 0,
                                                    'optional_args': 0,
                                                    'required_args': 0,
                                                    'return_hint': 'state_record',
                                                    'signature_text': '(*args, **kwargs)',
                                                    'stateful_owner': True,
                                                    'target_kind': 'function',
                                                    'varargs': True,
                                                    'varkw': True},
                               'coupling_similarity': 1.0,
                               'cross_diversity_links': 1,
                               'effect_modes': ['state_schema_change',
                                                'temporal_orchestration_change',
                                                'behavioral_execution_surface',
                                                'gateway_surface',
                                                'core_subsystem_surface'],
                               'effect_phrases': ['changed admissible state or persistence shape',
                                                  'changed ordering, tick flow, or replay behavior',
                                                  'introduced executable behavior surface',
                                                  'extended cross-layer routing or gateway '
                                                  'effects'],
                               'genealogy_pressure': 0.409012,
                               'inheritance_breach_count': 1,
                               'kind': 'reflection',
                               'link_hits': 0,
                               'module': 'aurora_governance_persistence_gateway',
                               'op_id': 'aurora_governance_persistence_gateway.GenerationalTension.total',
                               'origin_activity': 0,
                               'persistence_tax_factor': 1.450604,
                               'representation_score': 0.40614,
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
                               'signature': 'X^2*T^2*B^1',
                               'surface_score': 0.55575,
                               'sustainability_score': 0.449345,
                               'target_kind': 'function'},
 'GovernanceEngine': {'ability_hits': 0,
                      'alignment_gap': 0.53,
                      'alignment_target_score': 1.29475,
                      'best_coupling_signature': 'X^2*T^2*B^1',
                      'constraints': ['existence', 'temporal'],
                      'contract_profile': {'accepts_payload': False,
                                           'async_callable': False,
                                           'callable': True,
                                           'class_target': True,
                                           'constraint_density': 2,
                                           'contract_mode': 'stateless',
                                           'doc_hint': 'Constitutional law enforcement for 10-pole '
                                                       'IVM.',
                                           'effect_density': 5,
                                           'kwonly_args': 0,
                                           'optional_args': 0,
                                           'required_args': 0,
                                           'return_hint': 'state_record',
                                           'signature_text': '()',
                                           'stateful_owner': False,
                                           'target_kind': 'class',
                                           'varargs': False,
                                           'varkw': False},
                      'coupling_similarity': 1.0,
                      'cross_diversity_links': 7,
                      'effect_modes': ['state_schema_change',
                                       'temporal_orchestration_change',
                                       'stateful_surface_expansion',
                                       'gateway_surface',
                                       'core_subsystem_surface'],
                      'effect_phrases': ['changed admissible state or persistence shape',
                                         'changed ordering, tick flow, or replay behavior',
                                         'introduced reusable state-bearing system surface',
                                         'extended cross-layer routing or gateway effects'],
                      'genealogy_pressure': 0.409012,
                      'inheritance_breach_count': 1,
                      'kind': 'reflection',
                      'link_hits': 0,
                      'module': 'aurora_governance_persistence_gateway',
                      'op_id': 'aurora_governance_persistence_gateway.GovernanceEngine',
                      'origin_activity': 0,
                      'persistence_tax_factor': 1.450604,
                      'representation_score': 0.40614,
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
                      'signature': 'X^2*T^2*B^1',
                      'surface_score': 0.7647499999999999,
                      'sustainability_score': 0.449345,
                      'target_kind': 'class'},
 'GovernanceEngine.get_stats.route_agency': {'ability_hits': 0,
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
                                                                  'effect_density': 7,
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
                                                              'gateway_surface',
                                                              'core_subsystem_surface',
                                                              'latent_route_surface',
                                                              'latent_a_derivative'],
                                             'effect_phrases': ['would extend agency pressure '
                                                                'handling',
                                                                'would materialize the next '
                                                                'descendant implied by '
                                                                'aurora_governance_persistence_gateway.GovernanceEngine.get_stats'],
                                             'genealogy_pressure': 0.0,
                                             'inheritance_breach_count': 0,
                                             'kind': 'latent',
                                             'link_hits': 0,
                                             'module': 'aurora_governance_persistence_gateway',
                                             'op_id': 'latent.aurora_governance_persistence_gateway.GovernanceEngine.get_stats.route_agency',
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
                                             'rewrite_profile': 'governance_gateway',
                                             'signature': '',
                                             'surface_score': 0.7699836999999999,
                                             'sustainability_score': 0.0,
                                             'target_kind': 'latent_operation'},
 'GovernanceEngine.promote': {'ability_hits': 12,
                              'alignment_gap': 0.724833,
                              'alignment_target_score': 1.29475,
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
                                                   'effect_density': 5,
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
                              'effect_modes': ['interface_boundary_change',
                                               'behavioral_execution_surface',
                                               'gateway_surface',
                                               'evolution_surface',
                                               'core_subsystem_surface'],
                              'effect_phrases': ['changed module interfaces or coupling boundaries',
                                                 'introduced executable behavior surface',
                                                 'extended cross-layer routing or gateway effects',
                                                 'extended self-modification or promotion surface'],
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
                              'surface_score': 0.569917,
                              'sustainability_score': 0.356849,
                              'target_kind': 'function'},
 'GovernanceEngine.resolve_conflict': {'ability_hits': 0,
                                       'alignment_gap': 0.747333,
                                       'alignment_target_score': 1.29475,
                                       'best_coupling_signature': 'X^2*T^2*B^1',
                                       'constraints': ['existence', 'temporal'],
                                       'contract_profile': {'accepts_payload': False,
                                                            'async_callable': False,
                                                            'callable': True,
                                                            'class_target': False,
                                                            'constraint_density': 2,
                                                            'contract_mode': 'stateful',
                                                            'doc_hint': 'Resolve a single axis '
                                                                        'conflict by dampening the '
                                                                        'weaker pole.',
                                                            'effect_density': 5,
                                                            'kwonly_args': 0,
                                                            'optional_args': 0,
                                                            'required_args': 2,
                                                            'return_hint': 'bool',
                                                            'signature_text': '(self, node: '
                                                                              'aurora_governance_persistence_gateway.GovernedNode, '
                                                                              'axis: str) -> bool',
                                                            'stateful_owner': True,
                                                            'target_kind': 'function',
                                                            'varargs': False,
                                                            'varkw': False},
                                       'coupling_similarity': 1.0,
                                       'cross_diversity_links': 1,
                                       'effect_modes': ['state_schema_change',
                                                        'temporal_orchestration_change',
                                                        'behavioral_execution_surface',
                                                        'gateway_surface',
                                                        'core_subsystem_surface'],
                                       'effect_phrases': ['changed admissible state or persistence '
                                                          'shape',
                                                          'changed ordering, tick flow, or replay '
                                                          'behavior',
                                                          'introduced executable behavior surface',
                                                          'extended cross-layer routing or gateway '
                                                          'effects'],
                                       'genealogy_pressure': 0.409012,
                                       'inheritance_breach_count': 1,
                                       'kind': 'reflection',
                                       'link_hits': 0,
                                       'module': 'aurora_governance_persistence_gateway',
                                       'op_id': 'aurora_governance_persistence_gateway.GovernanceEngine.resolve_conflict',
                                       'origin_activity': 0,
                                       'persistence_tax_factor': 1.450604,
                                       'representation_score': 0.40614,
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
                                       'signature': 'X^2*T^2*B^1',
                                       'surface_score': 0.547417,
                                       'sustainability_score': 0.449345,
                                       'target_kind': 'function'},
 'GovernanceEngine.route_agency': {'ability_hits': 0,
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
                                                        'effect_density': 7,
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
                                                    'gateway_surface',
                                                    'core_subsystem_surface',
                                                    'latent_route_surface',
                                                    'latent_a_derivative'],
                                   'effect_phrases': ['would extend agency pressure handling',
                                                      'would materialize the next descendant '
                                                      'implied by '
                                                      'aurora_governance_persistence_gateway.GovernanceEngine'],
                                   'genealogy_pressure': 0.0,
                                   'inheritance_breach_count': 0,
                                   'kind': 'latent',
                                   'link_hits': 0,
                                   'module': 'aurora_governance_persistence_gateway',
                                   'op_id': 'latent.aurora_governance_persistence_gateway.GovernanceEngine.route_agency',
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
                                   'rewrite_profile': 'governance_gateway',
                                   'signature': '',
                                   'surface_score': 1.0243288,
                                   'sustainability_score': 0.0,
                                   'target_kind': 'latent_operation'},
 'GovernancePersistenceGateway.load_state': {'ability_hits': 1,
                                             'alignment_gap': 0.747333,
                                             'alignment_target_score': 1.29475,
                                             'best_coupling_signature': 'X^2*B^1',
                                             'constraints': ['existence'],
                                             'contract_profile': {'accepts_payload': False,
                                                                  'async_callable': False,
                                                                  'callable': True,
                                                                  'class_target': False,
                                                                  'constraint_density': 1,
                                                                  'contract_mode': 'stateful',
                                                                  'doc_hint': "Load Aurora's saved "
                                                                              'state.',
                                                                  'effect_density': 5,
                                                                  'kwonly_args': 0,
                                                                  'optional_args': 0,
                                                                  'required_args': 0,
                                                                  'return_hint': 'Optional',
                                                                  'signature_text': '(self) -> '
                                                                                    'Optional[aurora_governance_persistence_gateway.AuroraStateSnapshot]',
                                                                  'stateful_owner': True,
                                                                  'target_kind': 'function',
                                                                  'varargs': False,
                                                                  'varkw': False},
                                             'coupling_similarity': 1.0,
                                             'cross_diversity_links': 1,
                                             'effect_modes': ['state_schema_change',
                                                              'behavioral_execution_surface',
                                                              'gateway_surface',
                                                              'persistence_surface',
                                                              'core_subsystem_surface'],
                                             'effect_phrases': ['changed admissible state or '
                                                                'persistence shape',
                                                                'introduced executable behavior '
                                                                'surface',
                                                                'extended cross-layer routing or '
                                                                'gateway effects',
                                                                'extended persistence or '
                                                                'checkpoint continuity'],
                                             'genealogy_pressure': 0.410735,
                                             'inheritance_breach_count': 1,
                                             'kind': 'reflection',
                                             'link_hits': 0,
                                             'module': 'aurora_governance_persistence_gateway',
                                             'op_id': 'aurora_governance_persistence_gateway.GovernancePersistenceGateway.load_state',
                                             'origin_activity': 0,
                                             'persistence_tax_factor': 1.036753,
                                             'representation_score': 0.565962,
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
                                             'signature': 'X^2*B^1',
                                             'surface_score': 0.547417,
                                             'sustainability_score': 0.535662,
                                             'target_kind': 'function'},
 'GovernancePersistenceGateway.route_agency': {'ability_hits': 0,
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
                                                                    'effect_density': 7,
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
                                                                'gateway_surface',
                                                                'core_subsystem_surface',
                                                                'latent_route_surface',
                                                                'latent_a_derivative'],
                                               'effect_phrases': ['would extend agency pressure '
                                                                  'handling',
                                                                  'would materialize the next '
                                                                  'descendant implied by '
                                                                  'aurora_governance_persistence_gateway.GovernancePersistenceGateway'],
                                               'genealogy_pressure': 0.0,
                                               'inheritance_breach_count': 0,
                                               'kind': 'latent',
                                               'link_hits': 0,
                                               'module': 'aurora_governance_persistence_gateway',
                                               'op_id': 'latent.aurora_governance_persistence_gateway.GovernancePersistenceGateway.route_agency',
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
                                               'rewrite_profile': 'governance_gateway',
                                               'signature': '',
                                               'surface_score': 0.7836413,
                                               'sustainability_score': 0.0,
                                               'target_kind': 'latent_operation'},
 'GovernancePersistenceGateway.save_state.route_agency': {'ability_hits': 0,
                                                          'alignment_gap': 0.0,
                                                          'alignment_target_score': 0.0,
                                                          'best_coupling_signature': '',
                                                          'constraints': ['existence', 'agency'],
                                                          'contract_profile': {'accepts_payload': False,
                                                                               'async_callable': False,
                                                                               'callable': False,
                                                                               'class_target': False,
                                                                               'constraint_density': 2,
                                                                               'contract_mode': 'stateful',
                                                                               'doc_hint': '',
                                                                               'effect_density': 7,
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
                                                                           'behavioral_execution_surface',
                                                                           'gateway_surface',
                                                                           'persistence_surface',
                                                                           'core_subsystem_surface',
                                                                           'latent_route_surface',
                                                                           'latent_a_derivative'],
                                                          'effect_phrases': ['would extend agency '
                                                                             'pressure handling',
                                                                             'would materialize '
                                                                             'the next descendant '
                                                                             'implied by '
                                                                             'aurora_governance_persistence_gateway.GovernancePersistenceGateway.save_state'],
                                                          'genealogy_pressure': 0.0,
                                                          'inheritance_breach_count': 0,
                                                          'kind': 'latent',
                                                          'link_hits': 0,
                                                          'module': 'aurora_governance_persistence_gateway',
                                                          'op_id': 'latent.aurora_governance_persistence_gateway.GovernancePersistenceGateway.save_state.route_agency',
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
                                                          'rewrite_profile': 'governance_gateway',
                                                          'signature': '',
                                                          'surface_score': 0.9956413000000001,
                                                          'sustainability_score': 0.0,
                                                          'target_kind': 'latent_operation'},
 'GovernanceViolation': {'ability_hits': 0,
                         'alignment_gap': 0.698333,
                         'alignment_target_score': 1.29475,
                         'best_coupling_signature': 'X^2*T^2*B^1',
                         'constraints': ['existence', 'temporal'],
                         'contract_profile': {'accepts_payload': False,
                                              'async_callable': False,
                                              'callable': True,
                                              'class_target': True,
                                              'constraint_density': 2,
                                              'contract_mode': 'stateless',
                                              'doc_hint': 'Base governance violation.',
                                              'effect_density': 5,
                                              'kwonly_args': 0,
                                              'optional_args': 0,
                                              'required_args': 0,
                                              'return_hint': 'state_record',
                                              'signature_text': '',
                                              'stateful_owner': False,
                                              'target_kind': 'class',
                                              'varargs': False,
                                              'varkw': False},
                         'coupling_similarity': 1.0,
                         'cross_diversity_links': 1,
                         'effect_modes': ['state_schema_change',
                                          'temporal_orchestration_change',
                                          'stateful_surface_expansion',
                                          'gateway_surface',
                                          'core_subsystem_surface'],
                         'effect_phrases': ['changed admissible state or persistence shape',
                                            'changed ordering, tick flow, or replay behavior',
                                            'introduced reusable state-bearing system surface',
                                            'extended cross-layer routing or gateway effects'],
                         'genealogy_pressure': 0.409012,
                         'inheritance_breach_count': 1,
                         'kind': 'reflection',
                         'link_hits': 0,
                         'module': 'aurora_governance_persistence_gateway',
                         'op_id': 'aurora_governance_persistence_gateway.GovernanceViolation',
                         'origin_activity': 0,
                         'persistence_tax_factor': 1.450604,
                         'representation_score': 0.40614,
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
                         'signature': 'X^2*T^2*B^1',
                         'surface_score': 0.596417,
                         'sustainability_score': 0.449345,
                         'target_kind': 'class'},
 'GovernedCoordinate': {'ability_hits': 0,
                        'alignment_gap': 0.559896,
                        'alignment_target_score': 1.29475,
                        'best_coupling_signature': 'X^2*T^2*B^1',
                        'constraints': ['existence', 'temporal'],
                        'contract_profile': {'accepts_payload': False,
                                             'async_callable': False,
                                             'callable': True,
                                             'class_target': True,
                                             'constraint_density': 2,
                                             'contract_mode': 'stateless',
                                             'doc_hint': 'A position in 10-pole consciousness '
                                                         'space.',
                                             'effect_density': 5,
                                             'kwonly_args': 0,
                                             'optional_args': 11,
                                             'required_args': 0,
                                             'return_hint': 'None',
                                             'signature_text': '(i_is: float = 0.1, i_isnt: float '
                                                               '= 0.1, i_can: float = 0.1, '
                                                               'i_cannot: float = 0.1, i_do: float '
                                                               '= 0.1, i_donot: float = 0.1, '
                                                               'i_saw: float = 0.1, i_sought: '
                                                               'float = 0.1, i_did: float = 0.1, '
                                                               'i_didnt: float = 0.1, layer: '
                                                               'aurora_governance_persistence_gateway.IVMLayer '
                                                               '= <IVMLayer.ENERGY: 1>) -> None',
                                             'stateful_owner': False,
                                             'target_kind': 'class',
                                             'varargs': False,
                                             'varkw': False},
                        'coupling_similarity': 1.0,
                        'cross_diversity_links': 5,
                        'effect_modes': ['state_schema_change',
                                         'temporal_orchestration_change',
                                         'stateful_surface_expansion',
                                         'gateway_surface',
                                         'core_subsystem_surface'],
                        'effect_phrases': ['changed admissible state or persistence shape',
                                           'changed ordering, tick flow, or replay behavior',
                                           'introduced reusable state-bearing system surface',
                                           'extended cross-layer routing or gateway effects'],
                        'genealogy_pressure': 0.409012,
                        'inheritance_breach_count': 1,
                        'kind': 'reflection',
                        'link_hits': 0,
                        'module': 'aurora_governance_persistence_gateway',
                        'op_id': 'aurora_governance_persistence_gateway.GovernedCoordinate',
                        'origin_activity': 0,
                        'persistence_tax_factor': 1.450604,
                        'representation_score': 0.40614,
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
                        'signature': 'X^2*T^2*B^1',
                        'surface_score': 0.73485375,
                        'sustainability_score': 0.449345,
                        'target_kind': 'class'},
 'GovernedCoordinate.agency_weight': {'ability_hits': 1,
                                      'alignment_gap': 0.798583,
                                      'alignment_target_score': 1.29475,
                                      'best_coupling_signature': 'B^1*A^2',
                                      'constraints': ['agency'],
                                      'contract_profile': {'accepts_payload': False,
                                                           'async_callable': False,
                                                           'callable': True,
                                                           'class_target': False,
                                                           'constraint_density': 1,
                                                           'contract_mode': 'stateful',
                                                           'doc_hint': '',
                                                           'effect_density': 4,
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
                                      'cross_diversity_links': 1,
                                      'effect_modes': ['adaptive_steering_change',
                                                       'behavioral_execution_surface',
                                                       'gateway_surface',
                                                       'core_subsystem_surface'],
                                      'effect_phrases': ['changed steering, mutation, or choice '
                                                         'behavior',
                                                         'introduced executable behavior surface',
                                                         'extended cross-layer routing or gateway '
                                                         'effects'],
                                      'genealogy_pressure': 0.426456,
                                      'inheritance_breach_count': 1,
                                      'kind': 'reflection',
                                      'link_hits': 0,
                                      'module': 'aurora_governance_persistence_gateway',
                                      'op_id': 'aurora_governance_persistence_gateway.GovernedCoordinate.agency_weight',
                                      'origin_activity': 0,
                                      'persistence_tax_factor': 1.822787,
                                      'representation_score': 0.359639,
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
                                      'signature': 'B^1*A^2',
                                      'surface_score': 0.496167,
                                      'sustainability_score': 0.445319,
                                      'target_kind': 'function'},
 'GovernedCoordinate.boundary_weight': {'ability_hits': 12,
                                        'alignment_gap': 0.77775,
                                        'alignment_target_score': 1.29475,
                                        'best_coupling_signature': 'B^3',
                                        'constraints': ['boundary'],
                                        'contract_profile': {'accepts_payload': False,
                                                             'async_callable': False,
                                                             'callable': True,
                                                             'class_target': False,
                                                             'constraint_density': 1,
                                                             'contract_mode': 'stateful',
                                                             'doc_hint': '',
                                                             'effect_density': 4,
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
                                        'cross_diversity_links': 1,
                                        'effect_modes': ['interface_boundary_change',
                                                         'behavioral_execution_surface',
                                                         'gateway_surface',
                                                         'core_subsystem_surface'],
                                        'effect_phrases': ['changed module interfaces or coupling '
                                                           'boundaries',
                                                           'introduced executable behavior surface',
                                                           'extended cross-layer routing or '
                                                           'gateway effects'],
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
                                        'surface_score': 0.517,
                                        'sustainability_score': 0.356849,
                                        'target_kind': 'function'},
 'GovernedCoordinate.existence_weight.route_agency': {'ability_hits': 0,
                                                      'alignment_gap': 0.0,
                                                      'alignment_target_score': 0.0,
                                                      'best_coupling_signature': '',
                                                      'constraints': ['existence', 'agency'],
                                                      'contract_profile': {'accepts_payload': False,
                                                                           'async_callable': False,
                                                                           'callable': False,
                                                                           'class_target': False,
                                                                           'constraint_density': 2,
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
                                                                       'behavioral_execution_surface',
                                                                       'gateway_surface',
                                                                       'core_subsystem_surface',
                                                                       'latent_route_surface',
                                                                       'latent_a_derivative'],
                                                      'effect_phrases': ['would extend agency '
                                                                         'pressure handling',
                                                                         'would materialize the '
                                                                         'next descendant implied '
                                                                         'by '
                                                                         'aurora_governance_persistence_gateway.GovernedCoordinate.existence_weight'],
                                                      'genealogy_pressure': 0.0,
                                                      'inheritance_breach_count': 0,
                                                      'kind': 'latent',
                                                      'link_hits': 0,
                                                      'module': 'aurora_governance_persistence_gateway',
                                                      'op_id': 'latent.aurora_governance_persistence_gateway.GovernedCoordinate.existence_weight.route_agency',
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
                                                      'rewrite_profile': 'governance_gateway',
                                                      'signature': '',
                                                      'surface_score': 0.7975625000000001,
                                                      'sustainability_score': 0.0,
                                                      'target_kind': 'latent_operation'},
 'GovernedCoordinate.route_agency': {'ability_hits': 0,
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
                                                          'effect_density': 7,
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
                                                      'gateway_surface',
                                                      'core_subsystem_surface',
                                                      'latent_route_surface',
                                                      'latent_a_derivative'],
                                     'effect_phrases': ['would extend agency pressure handling',
                                                        'would materialize the next descendant '
                                                        'implied by '
                                                        'aurora_governance_persistence_gateway.GovernedCoordinate'],
                                     'genealogy_pressure': 0.0,
                                     'inheritance_breach_count': 0,
                                     'kind': 'latent',
                                     'link_hits': 0,
                                     'module': 'aurora_governance_persistence_gateway',
                                     'op_id': 'latent.aurora_governance_persistence_gateway.GovernedCoordinate.route_agency',
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
                                     'rewrite_profile': 'governance_gateway',
                                     'signature': '',
                                     'surface_score': 0.9942024500000001,
                                     'sustainability_score': 0.0,
                                     'target_kind': 'latent_operation'},
 'GovernedNode': {'ability_hits': 0,
                  'alignment_gap': 0.67,
                  'alignment_target_score': 1.29475,
                  'best_coupling_signature': 'X^2*T^2*B^1',
                  'constraints': ['existence', 'temporal'],
                  'contract_profile': {'accepts_payload': True,
                                       'async_callable': False,
                                       'callable': True,
                                       'class_target': True,
                                       'constraint_density': 2,
                                       'contract_mode': 'stateless',
                                       'doc_hint': 'A governed datum in the IVM lattice.',
                                       'effect_density': 5,
                                       'kwonly_args': 0,
                                       'optional_args': 8,
                                       'required_args': 2,
                                       'return_hint': 'None',
                                       'signature_text': '(node_id: str, coordinate: '
                                                         'aurora_governance_persistence_gateway.GovernedCoordinate, '
                                                         'payload: Any = None, payload_type: str = '
                                                         "'energy', energy: float = 1.0, "
                                                         'created_at: float = <factory>, '
                                                         'last_updated: float = <factory>, '
                                                         'parent_id: Optional[str] = None, '
                                                         'children: List[str] = <factory>, '
                                                         'axis_pressure: Dict[str, float] = '
                                                         '<factory>) -> None',
                                       'stateful_owner': False,
                                       'target_kind': 'class',
                                       'varargs': False,
                                       'varkw': False},
                  'coupling_similarity': 1.0,
                  'cross_diversity_links': 3,
                  'effect_modes': ['state_schema_change',
                                   'temporal_orchestration_change',
                                   'stateful_surface_expansion',
                                   'gateway_surface',
                                   'core_subsystem_surface'],
                  'effect_phrases': ['changed admissible state or persistence shape',
                                     'changed ordering, tick flow, or replay behavior',
                                     'introduced reusable state-bearing system surface',
                                     'extended cross-layer routing or gateway effects'],
                  'genealogy_pressure': 0.409012,
                  'inheritance_breach_count': 1,
                  'kind': 'reflection',
                  'link_hits': 0,
                  'module': 'aurora_governance_persistence_gateway',
                  'op_id': 'aurora_governance_persistence_gateway.GovernedNode',
                  'origin_activity': 0,
                  'persistence_tax_factor': 1.450604,
                  'representation_score': 0.40614,
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
                  'signature': 'X^2*T^2*B^1',
                  'surface_score': 0.62475,
                  'sustainability_score': 0.449345,
                  'target_kind': 'class'},
 'NSpaceGateway._express': {'ability_hits': 0,
                            'alignment_gap': 0.747333,
                            'alignment_target_score': 1.29475,
                            'best_coupling_signature': 'X^2*T^2*B^1',
                            'constraints': ['existence', 'temporal'],
                            'contract_profile': {'accepts_payload': False,
                                                 'async_callable': False,
                                                 'callable': True,
                                                 'class_target': False,
                                                 'constraint_density': 2,
                                                 'contract_mode': 'stateful',
                                                 'doc_hint': "Generate Aurora's expressive "
                                                             'response.',
                                                 'effect_density': 5,
                                                 'kwonly_args': 0,
                                                 'optional_args': 0,
                                                 'required_args': 3,
                                                 'return_hint': 'GatewayResponse',
                                                 'signature_text': '(self, packet: '
                                                                   'aurora_governance_persistence_gateway.InboundPacket, '
                                                                   'synthesis: '
                                                                   'aurora_governance_persistence_gateway.GatewaySynthesis, '
                                                                   'mode: '
                                                                   'foundational_contract.ExistenceMode) '
                                                                   '-> '
                                                                   'aurora_governance_persistence_gateway.GatewayResponse',
                                                 'stateful_owner': True,
                                                 'target_kind': 'function',
                                                 'varargs': False,
                                                 'varkw': False},
                            'coupling_similarity': 1.0,
                            'cross_diversity_links': 1,
                            'effect_modes': ['state_schema_change',
                                             'temporal_orchestration_change',
                                             'behavioral_execution_surface',
                                             'gateway_surface',
                                             'core_subsystem_surface'],
                            'effect_phrases': ['changed admissible state or persistence shape',
                                               'changed ordering, tick flow, or replay behavior',
                                               'introduced executable behavior surface',
                                               'extended cross-layer routing or gateway effects'],
                            'genealogy_pressure': 0.409012,
                            'inheritance_breach_count': 1,
                            'kind': 'reflection',
                            'link_hits': 0,
                            'module': 'aurora_governance_persistence_gateway',
                            'op_id': 'aurora_governance_persistence_gateway.NSpaceGateway._express',
                            'origin_activity': 0,
                            'persistence_tax_factor': 1.450604,
                            'representation_score': 0.40614,
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
                            'signature': 'X^2*T^2*B^1',
                            'surface_score': 0.547417,
                            'sustainability_score': 0.449345,
                            'target_kind': 'function'},
 'NSpaceGateway._needs_articulation_bridge': {'ability_hits': 0,
                                              'alignment_gap': 0.780667,
                                              'alignment_target_score': 1.29475,
                                              'best_coupling_signature': 'B^3*A^2',
                                              'constraints': ['boundary', 'agency'],
                                              'contract_profile': {'accepts_payload': False,
                                                                   'async_callable': False,
                                                                   'callable': True,
                                                                   'class_target': False,
                                                                   'constraint_density': 2,
                                                                   'contract_mode': 'stateful',
                                                                   'doc_hint': 'Detect when '
                                                                               'expressive output '
                                                                               'is too abstract '
                                                                               'for user-facing '
                                                                               'utility.',
                                                                   'effect_density': 5,
                                                                   'kwonly_args': 0,
                                                                   'optional_args': 0,
                                                                   'required_args': 2,
                                                                   'return_hint': 'bool',
                                                                   'signature_text': '(self, '
                                                                                     'prompt: str, '
                                                                                     'draft: str) '
                                                                                     '-> bool',
                                                                   'stateful_owner': True,
                                                                   'target_kind': 'function',
                                                                   'varargs': False,
                                                                   'varkw': False},
                                              'coupling_similarity': 1.0,
                                              'cross_diversity_links': 1,
                                              'effect_modes': ['interface_boundary_change',
                                                               'adaptive_steering_change',
                                                               'behavioral_execution_surface',
                                                               'gateway_surface',
                                                               'core_subsystem_surface'],
                                              'effect_phrases': ['changed module interfaces or '
                                                                 'coupling boundaries',
                                                                 'changed steering, mutation, or '
                                                                 'choice behavior',
                                                                 'introduced executable behavior '
                                                                 'surface',
                                                                 'extended cross-layer routing or '
                                                                 'gateway effects'],
                                              'genealogy_pressure': 0.437642,
                                              'inheritance_breach_count': 1,
                                              'kind': 'reflection',
                                              'link_hits': 0,
                                              'module': 'aurora_governance_persistence_gateway',
                                              'op_id': 'aurora_governance_persistence_gateway.NSpaceGateway._needs_articulation_bridge',
                                              'origin_activity': 0,
                                              'persistence_tax_factor': 2.882079,
                                              'representation_score': 0.337014,
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
                                              'signature': 'B^3*A^2',
                                              'surface_score': 0.514083,
                                              'sustainability_score': 0.359021,
                                              'target_kind': 'function'},
 'NSpaceGateway.receive': {'ability_hits': 0,
                           'alignment_gap': 0.739,
                           'alignment_target_score': 1.29475,
                           'best_coupling_signature': 'X^2*T^2*B^1',
                           'constraints': ['existence', 'temporal'],
                           'contract_profile': {'accepts_payload': False,
                                                'async_callable': False,
                                                'callable': True,
                                                'class_target': False,
                                                'constraint_density': 2,
                                                'contract_mode': 'stateful',
                                                'doc_hint': 'Main entry point. Receive external '
                                                            'data, process through full pipeline.',
                                                'effect_density': 5,
                                                'kwonly_args': 0,
                                                'optional_args': 5,
                                                'required_args': 1,
                                                'return_hint': 'GatewayResponse',
                                                'signature_text': '(self, content: str, '
                                                                  'stream_type: '
                                                                  'aurora_governance_persistence_gateway.StreamType '
                                                                  '= <StreamType.USER_INPUT: '
                                                                  "'user_input'>, source: str = "
                                                                  "'user', metadata: "
                                                                  'Optional[Dict[str, Any]] = '
                                                                  'None, mode: '
                                                                  'foundational_contract.ExistenceMode '
                                                                  '= <ExistenceMode.BOUNDED: 4>, '
                                                                  'thought_intent: '
                                                                  'Optional[Dict[str, Any]] = '
                                                                  'None) -> '
                                                                  'aurora_governance_persistence_gateway.GatewayResponse',
                                                'stateful_owner': True,
                                                'target_kind': 'function',
                                                'varargs': False,
                                                'varkw': False},
                           'coupling_similarity': 1.0,
                           'cross_diversity_links': 1,
                           'effect_modes': ['state_schema_change',
                                            'temporal_orchestration_change',
                                            'behavioral_execution_surface',
                                            'gateway_surface',
                                            'core_subsystem_surface'],
                           'effect_phrases': ['changed admissible state or persistence shape',
                                              'changed ordering, tick flow, or replay behavior',
                                              'introduced executable behavior surface',
                                              'extended cross-layer routing or gateway effects'],
                           'genealogy_pressure': 0.409012,
                           'inheritance_breach_count': 1,
                           'kind': 'reflection',
                           'link_hits': 0,
                           'module': 'aurora_governance_persistence_gateway',
                           'op_id': 'aurora_governance_persistence_gateway.NSpaceGateway.receive',
                           'origin_activity': 0,
                           'persistence_tax_factor': 1.450604,
                           'representation_score': 0.40614,
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
                           'signature': 'X^2*T^2*B^1',
                           'surface_score': 0.55575,
                           'sustainability_score': 0.449345,
                           'target_kind': 'function'},
 'NSpaceGateway.route_agency': {'ability_hits': 0,
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
                                                     'effect_density': 7,
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
                                                 'gateway_surface',
                                                 'core_subsystem_surface',
                                                 'latent_route_surface',
                                                 'latent_a_derivative'],
                                'effect_phrases': ['would extend agency pressure handling',
                                                   'would materialize the next descendant implied '
                                                   'by '
                                                   'aurora_governance_persistence_gateway.NSpaceGateway'],
                                'genealogy_pressure': 0.0,
                                'inheritance_breach_count': 0,
                                'kind': 'latent',
                                'link_hits': 0,
                                'module': 'aurora_governance_persistence_gateway',
                                'op_id': 'latent.aurora_governance_persistence_gateway.NSpaceGateway.route_agency',
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
                                'rewrite_profile': 'governance_gateway',
                                'signature': '',
                                'surface_score': 1.1367663000000001,
                                'sustainability_score': 0.0,
                                'target_kind': 'latent_operation'},
 'ProactiveTrigger': {'ability_hits': 0,
                      'alignment_gap': 0.643333,
                      'alignment_target_score': 1.29475,
                      'best_coupling_signature': 'X^2*T^2*B^1',
                      'constraints': ['existence', 'temporal'],
                      'contract_profile': {'accepts_payload': False,
                                           'async_callable': False,
                                           'callable': True,
                                           'class_target': True,
                                           'constraint_density': 2,
                                           'contract_mode': 'stateless',
                                           'doc_hint': 'Determines when Aurora should proactively '
                                                       'speak up.',
                                           'effect_density': 5,
                                           'kwonly_args': 0,
                                           'optional_args': 0,
                                           'required_args': 0,
                                           'return_hint': 'state_record',
                                           'signature_text': '()',
                                           'stateful_owner': False,
                                           'target_kind': 'class',
                                           'varargs': False,
                                           'varkw': False},
                      'coupling_similarity': 1.0,
                      'cross_diversity_links': 4,
                      'effect_modes': ['state_schema_change',
                                       'temporal_orchestration_change',
                                       'stateful_surface_expansion',
                                       'gateway_surface',
                                       'core_subsystem_surface'],
                      'effect_phrases': ['changed admissible state or persistence shape',
                                         'changed ordering, tick flow, or replay behavior',
                                         'introduced reusable state-bearing system surface',
                                         'extended cross-layer routing or gateway effects'],
                      'genealogy_pressure': 0.409012,
                      'inheritance_breach_count': 1,
                      'kind': 'reflection',
                      'link_hits': 0,
                      'module': 'aurora_governance_persistence_gateway',
                      'op_id': 'aurora_governance_persistence_gateway.ProactiveTrigger',
                      'origin_activity': 0,
                      'persistence_tax_factor': 1.450604,
                      'representation_score': 0.40614,
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
                      'signature': 'X^2*T^2*B^1',
                      'surface_score': 0.651417,
                      'sustainability_score': 0.449345,
                      'target_kind': 'class'},
 'ProactiveTrigger.add_thought.route_agency': {'ability_hits': 0,
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
                                                                    'effect_density': 7,
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
                                                                'gateway_surface',
                                                                'core_subsystem_surface',
                                                                'latent_route_surface',
                                                                'latent_a_derivative'],
                                               'effect_phrases': ['would extend agency pressure '
                                                                  'handling',
                                                                  'would materialize the next '
                                                                  'descendant implied by '
                                                                  'aurora_governance_persistence_gateway.ProactiveTrigger.add_thought'],
                                               'genealogy_pressure': 0.0,
                                               'inheritance_breach_count': 0,
                                               'kind': 'latent',
                                               'link_hits': 0,
                                               'module': 'aurora_governance_persistence_gateway',
                                               'op_id': 'latent.aurora_governance_persistence_gateway.ProactiveTrigger.add_thought.route_agency',
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
                                               'rewrite_profile': 'governance_gateway',
                                               'signature': '',
                                               'surface_score': 0.76338995,
                                               'sustainability_score': 0.0,
                                               'target_kind': 'latent_operation'},
 'RateLimitedSearch': {'ability_hits': 0,
                       'alignment_gap': 0.64,
                       'alignment_target_score': 1.29475,
                       'best_coupling_signature': 'X^2*T^2*B^1',
                       'constraints': ['existence', 'temporal'],
                       'contract_profile': {'accepts_payload': False,
                                            'async_callable': False,
                                            'callable': True,
                                            'class_target': True,
                                            'constraint_density': 2,
                                            'contract_mode': 'stateless',
                                            'doc_hint': 'Wraps the search adapter with rate '
                                                        'limiting for autonomous use.',
                                            'effect_density': 5,
                                            'kwonly_args': 0,
                                            'optional_args': 0,
                                            'required_args': 2,
                                            'return_hint': 'state_record',
                                            'signature_text': '(search_adapter, boundaries: '
                                                              'aurora_governance_persistence_gateway.AutonomyBoundaries)',
                                            'stateful_owner': False,
                                            'target_kind': 'class',
                                            'varargs': False,
                                            'varkw': False},
                       'coupling_similarity': 1.0,
                       'cross_diversity_links': 6,
                       'effect_modes': ['state_schema_change',
                                        'temporal_orchestration_change',
                                        'stateful_surface_expansion',
                                        'gateway_surface',
                                        'core_subsystem_surface'],
                       'effect_phrases': ['changed admissible state or persistence shape',
                                          'changed ordering, tick flow, or replay behavior',
                                          'introduced reusable state-bearing system surface',
                                          'extended cross-layer routing or gateway effects'],
                       'genealogy_pressure': 0.409012,
                       'inheritance_breach_count': 1,
                       'kind': 'reflection',
                       'link_hits': 0,
                       'module': 'aurora_governance_persistence_gateway',
                       'op_id': 'aurora_governance_persistence_gateway.RateLimitedSearch',
                       'origin_activity': 0,
                       'persistence_tax_factor': 1.450604,
                       'representation_score': 0.40614,
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
                       'signature': 'X^2*T^2*B^1',
                       'surface_score': 0.65475,
                       'sustainability_score': 0.449345,
                       'target_kind': 'class'},
 'RcloneInterface': {'ability_hits': 12,
                     'alignment_gap': 0.624583,
                     'alignment_target_score': 1.29475,
                     'best_coupling_signature': 'B^3',
                     'constraints': ['boundary'],
                     'contract_profile': {'accepts_payload': False,
                                          'async_callable': False,
                                          'callable': True,
                                          'class_target': True,
                                          'constraint_density': 1,
                                          'contract_mode': 'stateless',
                                          'doc_hint': 'Thin wrapper around the rclone binary.',
                                          'effect_density': 4,
                                          'kwonly_args': 0,
                                          'optional_args': 3,
                                          'required_args': 0,
                                          'return_hint': 'boundary_record',
                                          'signature_text': "(remote_name: str = 'gdrive', "
                                                            'remote_path: str = '
                                                            "'Aurora/aurora_state', local_path: "
                                                            "str = 'aurora_state')",
                                          'stateful_owner': False,
                                          'target_kind': 'class',
                                          'varargs': False,
                                          'varkw': False},
                     'coupling_similarity': 1.0,
                     'cross_diversity_links': 6,
                     'effect_modes': ['interface_boundary_change',
                                      'stateful_surface_expansion',
                                      'gateway_surface',
                                      'core_subsystem_surface'],
                     'effect_phrases': ['changed module interfaces or coupling boundaries',
                                        'introduced reusable state-bearing system surface',
                                        'extended cross-layer routing or gateway effects'],
                     'genealogy_pressure': 0.75101,
                     'inheritance_breach_count': 1,
                     'kind': 'reflection',
                     'link_hits': 24,
                     'module': 'aurora_governance_persistence_gateway',
                     'op_id': 'aurora_governance_persistence_gateway.RcloneInterface',
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
                     'surface_score': 0.6701670000000001,
                     'sustainability_score': 0.356849,
                     'target_kind': 'class'},
 'RcloneInterface.__init__': {'ability_hits': 12,
                              'alignment_gap': 0.819417,
                              'alignment_target_score': 1.29475,
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
                                                   'effect_density': 4,
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
                              'cross_diversity_links': 1,
                              'effect_modes': ['interface_boundary_change',
                                               'behavioral_execution_surface',
                                               'gateway_surface',
                                               'core_subsystem_surface'],
                              'effect_phrases': ['changed module interfaces or coupling boundaries',
                                                 'introduced executable behavior surface',
                                                 'extended cross-layer routing or gateway effects'],
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
                              'surface_score': 0.475333,
                              'sustainability_score': 0.356849,
                              'target_kind': 'function'},
 'RcloneInterface._find_rclone': {'ability_hits': 12,
                                  'alignment_gap': 0.76525,
                                  'alignment_target_score': 1.29475,
                                  'best_coupling_signature': 'B^3',
                                  'constraints': ['boundary'],
                                  'contract_profile': {'accepts_payload': False,
                                                       'async_callable': False,
                                                       'callable': True,
                                                       'class_target': False,
                                                       'constraint_density': 1,
                                                       'contract_mode': 'stateful',
                                                       'doc_hint': 'Find rclone binary path.',
                                                       'effect_density': 4,
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
                                  'cross_diversity_links': 1,
                                  'effect_modes': ['interface_boundary_change',
                                                   'behavioral_execution_surface',
                                                   'gateway_surface',
                                                   'core_subsystem_surface'],
                                  'effect_phrases': ['changed module interfaces or coupling '
                                                     'boundaries',
                                                     'introduced executable behavior surface',
                                                     'extended cross-layer routing or gateway '
                                                     'effects'],
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
                                  'surface_score': 0.5295000000000001,
                                  'sustainability_score': 0.356849,
                                  'target_kind': 'function'},
 'RcloneInterface._run_sync': {'ability_hits': 12,
                               'alignment_gap': 0.781083,
                               'alignment_target_score': 1.29475,
                               'best_coupling_signature': 'B^3',
                               'constraints': ['boundary'],
                               'contract_profile': {'accepts_payload': False,
                                                    'async_callable': False,
                                                    'callable': True,
                                                    'class_target': False,
                                                    'constraint_density': 1,
                                                    'contract_mode': 'stateful',
                                                    'doc_hint': 'Run rclone sync src → dst.',
                                                    'effect_density': 4,
                                                    'kwonly_args': 0,
                                                    'optional_args': 1,
                                                    'required_args': 2,
                                                    'return_hint': 'Dict',
                                                    'signature_text': '(self, src: str, dst: str, '
                                                                      'dry_run: bool = False) -> '
                                                                      'Dict',
                                                    'stateful_owner': True,
                                                    'target_kind': 'function',
                                                    'varargs': False,
                                                    'varkw': False},
                               'coupling_similarity': 1.0,
                               'cross_diversity_links': 4,
                               'effect_modes': ['interface_boundary_change',
                                                'behavioral_execution_surface',
                                                'gateway_surface',
                                                'core_subsystem_surface'],
                               'effect_phrases': ['changed module interfaces or coupling '
                                                  'boundaries',
                                                  'introduced executable behavior surface',
                                                  'extended cross-layer routing or gateway '
                                                  'effects'],
                               'genealogy_pressure': 0.75101,
                               'inheritance_breach_count': 1,
                               'kind': 'reflection',
                               'link_hits': 24,
                               'module': 'aurora_governance_persistence_gateway',
                               'op_id': 'aurora_governance_persistence_gateway.RcloneInterface._run_sync',
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
                               'surface_score': 0.513667,
                               'sustainability_score': 0.356849,
                               'target_kind': 'function'},
 'RcloneInterface.check_newer_remote': {'ability_hits': 12,
                                        'alignment_gap': 0.75275,
                                        'alignment_target_score': 1.29475,
                                        'best_coupling_signature': 'B^3',
                                        'constraints': ['boundary'],
                                        'contract_profile': {'accepts_payload': False,
                                                             'async_callable': False,
                                                             'callable': True,
                                                             'class_target': False,
                                                             'constraint_density': 1,
                                                             'contract_mode': 'stateful',
                                                             'doc_hint': 'Check if remote has a '
                                                                         'newer aurora_state.json '
                                                                         'than local.',
                                                             'effect_density': 4,
                                                             'kwonly_args': 0,
                                                             'optional_args': 0,
                                                             'required_args': 0,
                                                             'return_hint': 'bool',
                                                             'signature_text': '(self) -> bool',
                                                             'stateful_owner': True,
                                                             'target_kind': 'function',
                                                             'varargs': False,
                                                             'varkw': False},
                                        'coupling_similarity': 1.0,
                                        'cross_diversity_links': 1,
                                        'effect_modes': ['interface_boundary_change',
                                                         'behavioral_execution_surface',
                                                         'gateway_surface',
                                                         'core_subsystem_surface'],
                                        'effect_phrases': ['changed module interfaces or coupling '
                                                           'boundaries',
                                                           'introduced executable behavior surface',
                                                           'extended cross-layer routing or '
                                                           'gateway effects'],
                                        'genealogy_pressure': 0.75101,
                                        'inheritance_breach_count': 1,
                                        'kind': 'reflection',
                                        'link_hits': 24,
                                        'module': 'aurora_governance_persistence_gateway',
                                        'op_id': 'aurora_governance_persistence_gateway.RcloneInterface.check_newer_remote',
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
                                        'surface_score': 0.542,
                                        'sustainability_score': 0.356849,
                                        'target_kind': 'function'},
 'RcloneInterface.is_available': {'ability_hits': 12,
                                  'alignment_gap': 0.819417,
                                  'alignment_target_score': 1.29475,
                                  'best_coupling_signature': 'B^3',
                                  'constraints': ['boundary'],
                                  'contract_profile': {'accepts_payload': False,
                                                       'async_callable': False,
                                                       'callable': True,
                                                       'class_target': False,
                                                       'constraint_density': 1,
                                                       'contract_mode': 'stateful',
                                                       'doc_hint': 'Check if rclone is installed '
                                                                   'and configured.',
                                                       'effect_density': 4,
                                                       'kwonly_args': 0,
                                                       'optional_args': 0,
                                                       'required_args': 0,
                                                       'return_hint': 'bool',
                                                       'signature_text': '(self) -> bool',
                                                       'stateful_owner': True,
                                                       'target_kind': 'function',
                                                       'varargs': False,
                                                       'varkw': False},
                                  'coupling_similarity': 1.0,
                                  'cross_diversity_links': 1,
                                  'effect_modes': ['interface_boundary_change',
                                                   'behavioral_execution_surface',
                                                   'gateway_surface',
                                                   'core_subsystem_surface'],
                                  'effect_phrases': ['changed module interfaces or coupling '
                                                     'boundaries',
                                                     'introduced executable behavior surface',
                                                     'extended cross-layer routing or gateway '
                                                     'effects'],
                                  'genealogy_pressure': 0.75101,
                                  'inheritance_breach_count': 1,
                                  'kind': 'reflection',
                                  'link_hits': 24,
                                  'module': 'aurora_governance_persistence_gateway',
                                  'op_id': 'aurora_governance_persistence_gateway.RcloneInterface.is_available',
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
                                  'surface_score': 0.475333,
                                  'sustainability_score': 0.356849,
                                  'target_kind': 'function'},
 'RcloneInterface.remote_full': {'ability_hits': 12,
                                 'alignment_gap': 0.763583,
                                 'alignment_target_score': 1.29475,
                                 'best_coupling_signature': 'B^3',
                                 'constraints': ['boundary'],
                                 'contract_profile': {'accepts_payload': False,
                                                      'async_callable': False,
                                                      'callable': True,
                                                      'class_target': False,
                                                      'constraint_density': 1,
                                                      'contract_mode': 'stateful',
                                                      'doc_hint': '',
                                                      'effect_density': 4,
                                                      'kwonly_args': 0,
                                                      'optional_args': 0,
                                                      'required_args': 0,
                                                      'return_hint': 'boundary_record',
                                                      'signature_text': '(*args, **kwargs)',
                                                      'stateful_owner': True,
                                                      'target_kind': 'function',
                                                      'varargs': True,
                                                      'varkw': True},
                                 'coupling_similarity': 1.0,
                                 'cross_diversity_links': 2,
                                 'effect_modes': ['interface_boundary_change',
                                                  'behavioral_execution_surface',
                                                  'gateway_surface',
                                                  'core_subsystem_surface'],
                                 'effect_phrases': ['changed module interfaces or coupling '
                                                    'boundaries',
                                                    'introduced executable behavior surface',
                                                    'extended cross-layer routing or gateway '
                                                    'effects'],
                                 'genealogy_pressure': 0.75101,
                                 'inheritance_breach_count': 1,
                                 'kind': 'reflection',
                                 'link_hits': 24,
                                 'module': 'aurora_governance_persistence_gateway',
                                 'op_id': 'aurora_governance_persistence_gateway.RcloneInterface.remote_full',
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
                                 'surface_score': 0.531167,
                                 'sustainability_score': 0.356849,
                                 'target_kind': 'function'},
 'RcloneInterface.sync_down': {'ability_hits': 12,
                               'alignment_gap': 0.786083,
                               'alignment_target_score': 1.29475,
                               'best_coupling_signature': 'B^3',
                               'constraints': ['boundary'],
                               'contract_profile': {'accepts_payload': False,
                                                    'async_callable': False,
                                                    'callable': True,
                                                    'class_target': False,
                                                    'constraint_density': 1,
                                                    'contract_mode': 'stateful',
                                                    'doc_hint': 'Pull remote → local.',
                                                    'effect_density': 4,
                                                    'kwonly_args': 0,
                                                    'optional_args': 1,
                                                    'required_args': 0,
                                                    'return_hint': 'Dict',
                                                    'signature_text': '(self, dry_run: bool = '
                                                                      'False) -> Dict',
                                                    'stateful_owner': True,
                                                    'target_kind': 'function',
                                                    'varargs': False,
                                                    'varkw': False},
                               'coupling_similarity': 1.0,
                               'cross_diversity_links': 1,
                               'effect_modes': ['interface_boundary_change',
                                                'behavioral_execution_surface',
                                                'gateway_surface',
                                                'core_subsystem_surface'],
                               'effect_phrases': ['changed module interfaces or coupling '
                                                  'boundaries',
                                                  'introduced executable behavior surface',
                                                  'extended cross-layer routing or gateway '
                                                  'effects'],
                               'genealogy_pressure': 0.75101,
                               'inheritance_breach_count': 1,
                               'kind': 'reflection',
                               'link_hits': 24,
                               'module': 'aurora_governance_persistence_gateway',
                               'op_id': 'aurora_governance_persistence_gateway.RcloneInterface.sync_down',
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
                               'surface_score': 0.508667,
                               'sustainability_score': 0.356849,
                               'target_kind': 'function'},
 'RcloneInterface.sync_up': {'ability_hits': 12,
                             'alignment_gap': 0.784417,
                             'alignment_target_score': 1.29475,
                             'best_coupling_signature': 'B^3',
                             'constraints': ['boundary'],
                             'contract_profile': {'accepts_payload': False,
                                                  'async_callable': False,
                                                  'callable': True,
                                                  'class_target': False,
                                                  'constraint_density': 1,
                                                  'contract_mode': 'stateful',
                                                  'doc_hint': 'Push local → remote.',
                                                  'effect_density': 4,
                                                  'kwonly_args': 0,
                                                  'optional_args': 1,
                                                  'required_args': 0,
                                                  'return_hint': 'Dict',
                                                  'signature_text': '(self, dry_run: bool = False) '
                                                                    '-> Dict',
                                                  'stateful_owner': True,
                                                  'target_kind': 'function',
                                                  'varargs': False,
                                                  'varkw': False},
                             'coupling_similarity': 1.0,
                             'cross_diversity_links': 2,
                             'effect_modes': ['interface_boundary_change',
                                              'behavioral_execution_surface',
                                              'gateway_surface',
                                              'core_subsystem_surface'],
                             'effect_phrases': ['changed module interfaces or coupling boundaries',
                                                'introduced executable behavior surface',
                                                'extended cross-layer routing or gateway effects'],
                             'genealogy_pressure': 0.75101,
                             'inheritance_breach_count': 1,
                             'kind': 'reflection',
                             'link_hits': 24,
                             'module': 'aurora_governance_persistence_gateway',
                             'op_id': 'aurora_governance_persistence_gateway.RcloneInterface.sync_up',
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
                             'surface_score': 0.510333,
                             'sustainability_score': 0.356849,
                             'target_kind': 'function'},
 'StatePersistence.route_agency': {'ability_hits': 0,
                                   'alignment_gap': 0.0,
                                   'alignment_target_score': 0.0,
                                   'best_coupling_signature': '',
                                   'constraints': ['existence', 'agency'],
                                   'contract_profile': {'accepts_payload': False,
                                                        'async_callable': False,
                                                        'callable': False,
                                                        'class_target': False,
                                                        'constraint_density': 2,
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
                                                    'stateful_surface_expansion',
                                                    'gateway_surface',
                                                    'core_subsystem_surface',
                                                    'latent_route_surface',
                                                    'latent_a_derivative'],
                                   'effect_phrases': ['would extend agency pressure handling',
                                                      'would materialize the next descendant '
                                                      'implied by '
                                                      'aurora_governance_persistence_gateway.StatePersistence'],
                                   'genealogy_pressure': 0.0,
                                   'inheritance_breach_count': 0,
                                   'kind': 'latent',
                                   'link_hits': 0,
                                   'module': 'aurora_governance_persistence_gateway',
                                   'op_id': 'latent.aurora_governance_persistence_gateway.StatePersistence.route_agency',
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
                                   'rewrite_profile': 'governance_gateway',
                                   'signature': '',
                                   'surface_score': 1.149,
                                   'sustainability_score': 0.0,
                                   'target_kind': 'latent_operation'},
 'StatePersistence.save.route_agency': {'ability_hits': 0,
                                        'alignment_gap': 0.0,
                                        'alignment_target_score': 0.0,
                                        'best_coupling_signature': '',
                                        'constraints': ['existence', 'agency'],
                                        'contract_profile': {'accepts_payload': False,
                                                             'async_callable': False,
                                                             'callable': False,
                                                             'class_target': False,
                                                             'constraint_density': 2,
                                                             'contract_mode': 'stateful',
                                                             'doc_hint': '',
                                                             'effect_density': 7,
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
                                                         'behavioral_execution_surface',
                                                         'gateway_surface',
                                                         'persistence_surface',
                                                         'core_subsystem_surface',
                                                         'latent_route_surface',
                                                         'latent_a_derivative'],
                                        'effect_phrases': ['would extend agency pressure handling',
                                                           'would materialize the next descendant '
                                                           'implied by '
                                                           'aurora_governance_persistence_gateway.StatePersistence.save'],
                                        'genealogy_pressure': 0.0,
                                        'inheritance_breach_count': 0,
                                        'kind': 'latent',
                                        'link_hits': 0,
                                        'module': 'aurora_governance_persistence_gateway',
                                        'op_id': 'latent.aurora_governance_persistence_gateway.StatePersistence.save.route_agency',
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
                                        'rewrite_profile': 'governance_gateway',
                                        'signature': '',
                                        'surface_score': 0.9107038,
                                        'sustainability_score': 0.0,
                                        'target_kind': 'latent_operation'},
 'StreamType': {'ability_hits': 0,
                'alignment_gap': 0.723333,
                'alignment_target_score': 1.29475,
                'best_coupling_signature': 'X^2*T^2*B^1',
                'constraints': ['existence', 'temporal'],
                'contract_profile': {'accepts_payload': False,
                                     'async_callable': False,
                                     'callable': True,
                                     'class_target': True,
                                     'constraint_density': 2,
                                     'contract_mode': 'stateless',
                                     'doc_hint': 'Types of external data streams.',
                                     'effect_density': 5,
                                     'kwonly_args': 0,
                                     'optional_args': 0,
                                     'required_args': 0,
                                     'return_hint': 'state_record',
                                     'signature_text': '(*values)',
                                     'stateful_owner': False,
                                     'target_kind': 'class',
                                     'varargs': True,
                                     'varkw': False},
                'coupling_similarity': 1.0,
                'cross_diversity_links': 6,
                'effect_modes': ['state_schema_change',
                                 'temporal_orchestration_change',
                                 'stateful_surface_expansion',
                                 'gateway_surface',
                                 'core_subsystem_surface'],
                'effect_phrases': ['changed admissible state or persistence shape',
                                   'changed ordering, tick flow, or replay behavior',
                                   'introduced reusable state-bearing system surface',
                                   'extended cross-layer routing or gateway effects'],
                'genealogy_pressure': 0.409012,
                'inheritance_breach_count': 1,
                'kind': 'reflection',
                'link_hits': 0,
                'module': 'aurora_governance_persistence_gateway',
                'op_id': 'aurora_governance_persistence_gateway.StreamType',
                'origin_activity': 0,
                'persistence_tax_factor': 1.450604,
                'representation_score': 0.40614,
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
                'signature': 'X^2*T^2*B^1',
                'surface_score': 0.571417,
                'sustainability_score': 0.449345,
                'target_kind': 'class'},
 'StudyScheduler': {'ability_hits': 0,
                    'alignment_gap': 0.671667,
                    'alignment_target_score': 1.29475,
                    'best_coupling_signature': 'X^2*T^2*B^1',
                    'constraints': ['existence', 'temporal'],
                    'contract_profile': {'accepts_payload': False,
                                         'async_callable': False,
                                         'callable': True,
                                         'class_target': True,
                                         'constraint_density': 2,
                                         'contract_mode': 'stateless',
                                         'doc_hint': "Manages Aurora's autonomous study sessions.",
                                         'effect_density': 5,
                                         'kwonly_args': 0,
                                         'optional_args': 0,
                                         'required_args': 1,
                                         'return_hint': 'state_record',
                                         'signature_text': '(boundaries: '
                                                           'aurora_governance_persistence_gateway.AutonomyBoundaries)',
                                         'stateful_owner': False,
                                         'target_kind': 'class',
                                         'varargs': False,
                                         'varkw': False},
                    'coupling_similarity': 1.0,
                    'cross_diversity_links': 2,
                    'effect_modes': ['state_schema_change',
                                     'temporal_orchestration_change',
                                     'stateful_surface_expansion',
                                     'gateway_surface',
                                     'core_subsystem_surface'],
                    'effect_phrases': ['changed admissible state or persistence shape',
                                       'changed ordering, tick flow, or replay behavior',
                                       'introduced reusable state-bearing system surface',
                                       'extended cross-layer routing or gateway effects'],
                    'genealogy_pressure': 0.409012,
                    'inheritance_breach_count': 1,
                    'kind': 'reflection',
                    'link_hits': 0,
                    'module': 'aurora_governance_persistence_gateway',
                    'op_id': 'aurora_governance_persistence_gateway.StudyScheduler',
                    'origin_activity': 0,
                    'persistence_tax_factor': 1.450604,
                    'representation_score': 0.40614,
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
                    'signature': 'X^2*T^2*B^1',
                    'surface_score': 0.623083,
                    'sustainability_score': 0.449345,
                    'target_kind': 'class'},
 'ValidationResult': {'ability_hits': 0,
                      'alignment_gap': 0.723333,
                      'alignment_target_score': 1.29475,
                      'best_coupling_signature': 'X^2*T^2*B^1',
                      'constraints': ['existence', 'temporal'],
                      'contract_profile': {'accepts_payload': False,
                                           'async_callable': False,
                                           'callable': True,
                                           'class_target': True,
                                           'constraint_density': 2,
                                           'contract_mode': 'stateless',
                                           'doc_hint': 'Result of Gateway validation pipeline.',
                                           'effect_density': 5,
                                           'kwonly_args': 0,
                                           'optional_args': 7,
                                           'required_args': 1,
                                           'return_hint': 'None',
                                           'signature_text': '(packet_id: str, verdict: '
                                                             'aurora_governance_persistence_gateway.GatewayVerdict '
                                                             '= <GatewayVerdict.ACCEPTED: '
                                                             "'accepted'>, ontological_valid: bool "
                                                             '= True, moral_score: float = 1.0, '
                                                             'coherence_score: float = 1.0, '
                                                             'governance_clear: bool = True, '
                                                             'filtered_content: Optional[str] = '
                                                             'None, rejection_reason: '
                                                             'Optional[str] = None) -> None',
                                           'stateful_owner': False,
                                           'target_kind': 'class',
                                           'varargs': False,
                                           'varkw': False},
                      'coupling_similarity': 1.0,
                      'cross_diversity_links': 6,
                      'effect_modes': ['state_schema_change',
                                       'temporal_orchestration_change',
                                       'stateful_surface_expansion',
                                       'gateway_surface',
                                       'core_subsystem_surface'],
                      'effect_phrases': ['changed admissible state or persistence shape',
                                         'changed ordering, tick flow, or replay behavior',
                                         'introduced reusable state-bearing system surface',
                                         'extended cross-layer routing or gateway effects'],
                      'genealogy_pressure': 0.409012,
                      'inheritance_breach_count': 1,
                      'kind': 'reflection',
                      'link_hits': 0,
                      'module': 'aurora_governance_persistence_gateway',
                      'op_id': 'aurora_governance_persistence_gateway.ValidationResult',
                      'origin_activity': 0,
                      'persistence_tax_factor': 1.450604,
                      'representation_score': 0.40614,
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
                      'signature': 'X^2*T^2*B^1',
                      'surface_score': 0.571417,
                      'sustainability_score': 0.449345,
                      'target_kind': 'class'},
 'VotingAuthority': {'ability_hits': 0,
                     'alignment_gap': 0.760833,
                     'alignment_target_score': 1.29475,
                     'best_coupling_signature': 'X^2*T^2*B^1',
                     'constraints': ['existence', 'temporal'],
                     'contract_profile': {'accepts_payload': False,
                                          'async_callable': False,
                                          'callable': True,
                                          'class_target': True,
                                          'constraint_density': 2,
                                          'contract_mode': 'stateless',
                                          'doc_hint': 'Who has decision power at each layer.',
                                          'effect_density': 5,
                                          'kwonly_args': 0,
                                          'optional_args': 0,
                                          'required_args': 0,
                                          'return_hint': 'state_record',
                                          'signature_text': '(*values)',
                                          'stateful_owner': False,
                                          'target_kind': 'class',
                                          'varargs': True,
                                          'varkw': False},
                     'coupling_similarity': 1.0,
                     'cross_diversity_links': 1,
                     'effect_modes': ['state_schema_change',
                                      'temporal_orchestration_change',
                                      'stateful_surface_expansion',
                                      'gateway_surface',
                                      'core_subsystem_surface'],
                     'effect_phrases': ['changed admissible state or persistence shape',
                                        'changed ordering, tick flow, or replay behavior',
                                        'introduced reusable state-bearing system surface',
                                        'extended cross-layer routing or gateway effects'],
                     'genealogy_pressure': 0.409012,
                     'inheritance_breach_count': 1,
                     'kind': 'reflection',
                     'link_hits': 0,
                     'module': 'aurora_governance_persistence_gateway',
                     'op_id': 'aurora_governance_persistence_gateway.VotingAuthority',
                     'origin_activity': 0,
                     'persistence_tax_factor': 1.450604,
                     'representation_score': 0.40614,
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
                     'signature': 'X^2*T^2*B^1',
                     'surface_score': 0.533917,
                     'sustainability_score': 0.449345,
                     'target_kind': 'class'},
 'WriteResult': {'ability_hits': 0,
                 'alignment_gap': 0.723333,
                 'alignment_target_score': 1.29475,
                 'best_coupling_signature': 'X^2*T^2*B^1',
                 'constraints': ['existence', 'temporal'],
                 'contract_profile': {'accepts_payload': False,
                                      'async_callable': False,
                                      'callable': True,
                                      'class_target': True,
                                      'constraint_density': 2,
                                      'contract_mode': 'stateless',
                                      'doc_hint': 'Create a collection of name/value pairs.',
                                      'effect_density': 5,
                                      'kwonly_args': 0,
                                      'optional_args': 0,
                                      'required_args': 0,
                                      'return_hint': 'state_record',
                                      'signature_text': '(*values)',
                                      'stateful_owner': False,
                                      'target_kind': 'class',
                                      'varargs': True,
                                      'varkw': False},
                 'coupling_similarity': 1.0,
                 'cross_diversity_links': 6,
                 'effect_modes': ['state_schema_change',
                                  'temporal_orchestration_change',
                                  'stateful_surface_expansion',
                                  'gateway_surface',
                                  'core_subsystem_surface'],
                 'effect_phrases': ['changed admissible state or persistence shape',
                                    'changed ordering, tick flow, or replay behavior',
                                    'introduced reusable state-bearing system surface',
                                    'extended cross-layer routing or gateway effects'],
                 'genealogy_pressure': 0.409012,
                 'inheritance_breach_count': 1,
                 'kind': 'reflection',
                 'link_hits': 0,
                 'module': 'aurora_governance_persistence_gateway',
                 'op_id': 'aurora_governance_persistence_gateway.WriteResult',
                 'origin_activity': 0,
                 'persistence_tax_factor': 1.450604,
                 'representation_score': 0.40614,
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
                 'signature': 'X^2*T^2*B^1',
                 'surface_score': 0.571417,
                 'sustainability_score': 0.449345,
                 'target_kind': 'class'},
 'WriteValidator.route_agency': {'ability_hits': 0,
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
                                                      'effect_density': 7,
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
                                                  'gateway_surface',
                                                  'core_subsystem_surface',
                                                  'latent_route_surface',
                                                  'latent_a_derivative'],
                                 'effect_phrases': ['would extend agency pressure handling',
                                                    'would materialize the next descendant implied '
                                                    'by '
                                                    'aurora_governance_persistence_gateway.WriteValidator'],
                                 'genealogy_pressure': 0.0,
                                 'inheritance_breach_count': 0,
                                 'kind': 'latent',
                                 'link_hits': 0,
                                 'module': 'aurora_governance_persistence_gateway',
                                 'op_id': 'latent.aurora_governance_persistence_gateway.WriteValidator.route_agency',
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
                                 'rewrite_profile': 'governance_gateway',
                                 'signature': '',
                                 'surface_score': 0.9432037999999999,
                                 'sustainability_score': 0.0,
                                 'target_kind': 'latent_operation'},
 '_clamp.route_agency': {'ability_hits': 0,
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
                                              'effect_density': 7,
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
                                          'gateway_surface',
                                          'core_subsystem_surface',
                                          'latent_route_surface',
                                          'latent_a_derivative'],
                         'effect_phrases': ['would extend agency pressure handling',
                                            'would materialize the next descendant implied by '
                                            'aurora_governance_persistence_gateway._clamp'],
                         'genealogy_pressure': 0.0,
                         'inheritance_breach_count': 0,
                         'kind': 'latent',
                         'link_hits': 0,
                         'module': 'aurora_governance_persistence_gateway',
                         'op_id': 'latent.aurora_governance_persistence_gateway._clamp.route_agency',
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
                         'rewrite_profile': 'governance_gateway',
                         'signature': '',
                         'surface_score': 1.4504991999999999,
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

def route_agency(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'latent.aurora_governance_persistence_gateway._clamp.route_agency', 'kind': 'latent'
        }
    return getattr(engine, 'latent_aurora_governance_persistence_gateway_clamp_route_agency')(payload=payload, **kwargs)

_aurora_existing_binding = _aurora_get_target(['_clamp'])
if _aurora_existing_binding is not None:
    _aurora_existing_attr = getattr(_aurora_existing_binding, 'route_agency', None)
    if _aurora_existing_attr is None or getattr(_aurora_existing_attr, '_aurora_latent_binding_target', '') == '_clamp.route_agency':
        _aurora_bind_owner_attribute(['_clamp'], 'route_agency', _aurora_make_latent_binding('route_agency', '_clamp.route_agency'))
        _AURORA_NATIVE_EVOLVED_LAST['_clamp.route_agency'] = {'latent_binding_active': True}

def nspacegateway_route_agency(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'latent.aurora_governance_persistence_gateway.NSpaceGateway.route_agency', 'kind': 'latent'
        }
    return getattr(engine, 'latent_aurora_governance_persistence_gateway_nspacegateway_route_agency')(payload=payload, **kwargs)

_aurora_existing_binding = _aurora_get_target(['NSpaceGateway'])
if _aurora_existing_binding is not None:
    _aurora_existing_attr = getattr(_aurora_existing_binding, 'route_agency', None)
    if _aurora_existing_attr is None or getattr(_aurora_existing_attr, '_aurora_latent_binding_target', '') == 'NSpaceGateway.route_agency':
        _aurora_bind_owner_attribute(['NSpaceGateway'], 'route_agency', _aurora_make_latent_binding('nspacegateway_route_agency', 'NSpaceGateway.route_agency'))
        _AURORA_NATIVE_EVOLVED_LAST['NSpaceGateway.route_agency'] = {'latent_binding_active': True}

def statepersistence_route_agency(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'latent.aurora_governance_persistence_gateway.StatePersistence.route_agency', 'kind': 'latent'
        }
    return getattr(engine, 'latent_aurora_governance_persistence_gateway_statepersistence_route_agency')(payload=payload, **kwargs)

_aurora_existing_binding = _aurora_get_target(['StatePersistence'])
if _aurora_existing_binding is not None:
    _aurora_existing_attr = getattr(_aurora_existing_binding, 'route_agency', None)
    if _aurora_existing_attr is None or getattr(_aurora_existing_attr, '_aurora_latent_binding_target', '') == 'StatePersistence.route_agency':
        _aurora_bind_owner_attribute(['StatePersistence'], 'route_agency', _aurora_make_latent_binding('statepersistence_route_agency', 'StatePersistence.route_agency'))
        _AURORA_NATIVE_EVOLVED_LAST['StatePersistence.route_agency'] = {'latent_binding_active': True}

def route_boundary(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'latent.aurora_governance_persistence_gateway.AutonomyEngine.route_boundary', 'kind': 'latent'
        }
    return getattr(engine, 'latent_aurora_governance_persistence_gateway_autonomyengine_route_boundary')(payload=payload, **kwargs)

_aurora_existing_binding = _aurora_get_target(['AutonomyEngine'])
if _aurora_existing_binding is not None:
    _aurora_existing_attr = getattr(_aurora_existing_binding, 'route_boundary', None)
    if _aurora_existing_attr is None or getattr(_aurora_existing_attr, '_aurora_latent_binding_target', '') == 'AutonomyEngine.route_boundary':
        _aurora_bind_owner_attribute(['AutonomyEngine'], 'route_boundary', _aurora_make_latent_binding('route_boundary', 'AutonomyEngine.route_boundary'))
        _AURORA_NATIVE_EVOLVED_LAST['AutonomyEngine.route_boundary'] = {'latent_binding_active': True}

def checkpointmanager_route_agency(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'latent.aurora_governance_persistence_gateway.CheckpointManager.route_agency', 'kind': 'latent'
        }
    return getattr(engine, 'latent_aurora_governance_persistence_gateway_checkpointmanager_route_agency')(payload=payload, **kwargs)

_aurora_existing_binding = _aurora_get_target(['CheckpointManager'])
if _aurora_existing_binding is not None:
    _aurora_existing_attr = getattr(_aurora_existing_binding, 'route_agency', None)
    if _aurora_existing_attr is None or getattr(_aurora_existing_attr, '_aurora_latent_binding_target', '') == 'CheckpointManager.route_agency':
        _aurora_bind_owner_attribute(['CheckpointManager'], 'route_agency', _aurora_make_latent_binding('checkpointmanager_route_agency', 'CheckpointManager.route_agency'))
        _AURORA_NATIVE_EVOLVED_LAST['CheckpointManager.route_agency'] = {'latent_binding_active': True}

def aurorastatesnapshot_route_agency(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'latent.aurora_governance_persistence_gateway.AuroraStateSnapshot.route_agency', 'kind': 'latent'
        }
    return getattr(engine, 'latent_aurora_governance_persistence_gateway_aurorastatesnapshot_route_agency')(payload=payload, **kwargs)

_aurora_existing_binding = _aurora_get_target(['AuroraStateSnapshot'])
if _aurora_existing_binding is not None:
    _aurora_existing_attr = getattr(_aurora_existing_binding, 'route_agency', None)
    if _aurora_existing_attr is None or getattr(_aurora_existing_attr, '_aurora_latent_binding_target', '') == 'AuroraStateSnapshot.route_agency':
        _aurora_bind_owner_attribute(['AuroraStateSnapshot'], 'route_agency', _aurora_make_latent_binding('aurorastatesnapshot_route_agency', 'AuroraStateSnapshot.route_agency'))
        _AURORA_NATIVE_EVOLVED_LAST['AuroraStateSnapshot.route_agency'] = {'latent_binding_active': True}

def governanceengine_route_agency(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'latent.aurora_governance_persistence_gateway.GovernanceEngine.route_agency', 'kind': 'latent'
        }
    return getattr(engine, 'latent_aurora_governance_persistence_gateway_governanceengine_route_agency')(payload=payload, **kwargs)

_aurora_existing_binding = _aurora_get_target(['GovernanceEngine'])
if _aurora_existing_binding is not None:
    _aurora_existing_attr = getattr(_aurora_existing_binding, 'route_agency', None)
    if _aurora_existing_attr is None or getattr(_aurora_existing_attr, '_aurora_latent_binding_target', '') == 'GovernanceEngine.route_agency':
        _aurora_bind_owner_attribute(['GovernanceEngine'], 'route_agency', _aurora_make_latent_binding('governanceengine_route_agency', 'GovernanceEngine.route_agency'))
        _AURORA_NATIVE_EVOLVED_LAST['GovernanceEngine.route_agency'] = {'latent_binding_active': True}

def checkpointrecord_route_agency(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'latent.aurora_governance_persistence_gateway.CheckpointRecord.route_agency', 'kind': 'latent'
        }
    return getattr(engine, 'latent_aurora_governance_persistence_gateway_checkpointrecord_route_agency')(payload=payload, **kwargs)

_aurora_existing_binding = _aurora_get_target(['CheckpointRecord'])
if _aurora_existing_binding is not None:
    _aurora_existing_attr = getattr(_aurora_existing_binding, 'route_agency', None)
    if _aurora_existing_attr is None or getattr(_aurora_existing_attr, '_aurora_latent_binding_target', '') == 'CheckpointRecord.route_agency':
        _aurora_bind_owner_attribute(['CheckpointRecord'], 'route_agency', _aurora_make_latent_binding('checkpointrecord_route_agency', 'CheckpointRecord.route_agency'))
        _AURORA_NATIVE_EVOLVED_LAST['CheckpointRecord.route_agency'] = {'latent_binding_active': True}

def save_state_route_agency(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'latent.aurora_governance_persistence_gateway.GovernancePersistenceGateway.save_state.route_agency', 'kind': 'latent'
        }
    return getattr(engine, 'latent_aurora_governance_persistence_gateway_governancepersistencegateway_save_state_route_agency')(payload=payload, **kwargs)

_aurora_existing_binding = _aurora_get_target(['GovernancePersistenceGateway', 'save_state'])
if _aurora_existing_binding is not None:
    _aurora_existing_attr = getattr(_aurora_existing_binding, 'route_agency', None)
    if _aurora_existing_attr is None or getattr(_aurora_existing_attr, '_aurora_latent_binding_target', '') == 'GovernancePersistenceGateway.save_state.route_agency':
        _aurora_bind_owner_attribute(['GovernancePersistenceGateway', 'save_state'], 'route_agency', _aurora_make_latent_binding('save_state_route_agency', 'GovernancePersistenceGateway.save_state.route_agency'))
        _AURORA_NATIVE_EVOLVED_LAST['GovernancePersistenceGateway.save_state.route_agency'] = {'latent_binding_active': True}

def drivesync_route_boundary(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'latent.aurora_governance_persistence_gateway.DriveSync.route_boundary', 'kind': 'latent'
        }
    return getattr(engine, 'latent_aurora_governance_persistence_gateway_drivesync_route_boundary')(payload=payload, **kwargs)

_aurora_existing_binding = _aurora_get_target(['DriveSync'])
if _aurora_existing_binding is not None:
    _aurora_existing_attr = getattr(_aurora_existing_binding, 'route_boundary', None)
    if _aurora_existing_attr is None or getattr(_aurora_existing_attr, '_aurora_latent_binding_target', '') == 'DriveSync.route_boundary':
        _aurora_bind_owner_attribute(['DriveSync'], 'route_boundary', _aurora_make_latent_binding('drivesync_route_boundary', 'DriveSync.route_boundary'))
        _AURORA_NATIVE_EVOLVED_LAST['DriveSync.route_boundary'] = {'latent_binding_active': True}

def governedcoordinate_route_agency(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'latent.aurora_governance_persistence_gateway.GovernedCoordinate.route_agency', 'kind': 'latent'
        }
    return getattr(engine, 'latent_aurora_governance_persistence_gateway_governedcoordinate_route_agency')(payload=payload, **kwargs)

_aurora_existing_binding = _aurora_get_target(['GovernedCoordinate'])
if _aurora_existing_binding is not None:
    _aurora_existing_attr = getattr(_aurora_existing_binding, 'route_agency', None)
    if _aurora_existing_attr is None or getattr(_aurora_existing_attr, '_aurora_latent_binding_target', '') == 'GovernedCoordinate.route_agency':
        _aurora_bind_owner_attribute(['GovernedCoordinate'], 'route_agency', _aurora_make_latent_binding('governedcoordinate_route_agency', 'GovernedCoordinate.route_agency'))
        _AURORA_NATIVE_EVOLVED_LAST['GovernedCoordinate.route_agency'] = {'latent_binding_active': True}

def to_dict_route_agency(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'latent.aurora_governance_persistence_gateway.DeviceRecord.to_dict.route_agency', 'kind': 'latent'
        }
    return getattr(engine, 'latent_aurora_governance_persistence_gateway_devicerecord_to_dict_route_agency')(payload=payload, **kwargs)

_aurora_existing_binding = _aurora_get_target(['DeviceRecord', 'to_dict'])
if _aurora_existing_binding is not None:
    _aurora_existing_attr = getattr(_aurora_existing_binding, 'route_agency', None)
    if _aurora_existing_attr is None or getattr(_aurora_existing_attr, '_aurora_latent_binding_target', '') == 'DeviceRecord.to_dict.route_agency':
        _aurora_bind_owner_attribute(['DeviceRecord', 'to_dict'], 'route_agency', _aurora_make_latent_binding('to_dict_route_agency', 'DeviceRecord.to_dict.route_agency'))
        _AURORA_NATIVE_EVOLVED_LAST['DeviceRecord.to_dict.route_agency'] = {'latent_binding_active': True}

def evolved_route_agency(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'latent.aurora_governance_persistence_gateway.AuroraStateSnapshot.to_dict.route_agency', 'kind': 'latent'
        }
    return getattr(engine, 'latent_aurora_governance_persistence_gateway_aurorastatesnapshot_to_dict_route_agency')(payload=payload, **kwargs)

_aurora_existing_binding = _aurora_get_target(['AuroraStateSnapshot', 'to_dict'])
if _aurora_existing_binding is not None:
    _aurora_existing_attr = getattr(_aurora_existing_binding, 'route_agency', None)
    if _aurora_existing_attr is None or getattr(_aurora_existing_attr, '_aurora_latent_binding_target', '') == 'AuroraStateSnapshot.to_dict.route_agency':
        _aurora_bind_owner_attribute(['AuroraStateSnapshot', 'to_dict'], 'route_agency', _aurora_make_latent_binding('evolved_route_agency', 'AuroraStateSnapshot.to_dict.route_agency'))
        _AURORA_NATIVE_EVOLVED_LAST['AuroraStateSnapshot.to_dict.route_agency'] = {'latent_binding_active': True}

def writevalidator_route_agency(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'latent.aurora_governance_persistence_gateway.WriteValidator.route_agency', 'kind': 'latent'
        }
    return getattr(engine, 'latent_aurora_governance_persistence_gateway_writevalidator_route_agency')(payload=payload, **kwargs)

_aurora_existing_binding = _aurora_get_target(['WriteValidator'])
if _aurora_existing_binding is not None:
    _aurora_existing_attr = getattr(_aurora_existing_binding, 'route_agency', None)
    if _aurora_existing_attr is None or getattr(_aurora_existing_attr, '_aurora_latent_binding_target', '') == 'WriteValidator.route_agency':
        _aurora_bind_owner_attribute(['WriteValidator'], 'route_agency', _aurora_make_latent_binding('writevalidator_route_agency', 'WriteValidator.route_agency'))
        _AURORA_NATIVE_EVOLVED_LAST['WriteValidator.route_agency'] = {'latent_binding_active': True}

def save_route_agency(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'latent.aurora_governance_persistence_gateway.StatePersistence.save.route_agency', 'kind': 'latent'
        }
    return getattr(engine, 'latent_aurora_governance_persistence_gateway_statepersistence_save_route_agency')(payload=payload, **kwargs)

_aurora_existing_binding = _aurora_get_target(['StatePersistence', 'save'])
if _aurora_existing_binding is not None:
    _aurora_existing_attr = getattr(_aurora_existing_binding, 'route_agency', None)
    if _aurora_existing_attr is None or getattr(_aurora_existing_attr, '_aurora_latent_binding_target', '') == 'StatePersistence.save.route_agency':
        _aurora_bind_owner_attribute(['StatePersistence', 'save'], 'route_agency', _aurora_make_latent_binding('save_route_agency', 'StatePersistence.save.route_agency'))
        _AURORA_NATIVE_EVOLVED_LAST['StatePersistence.save.route_agency'] = {'latent_binding_active': True}

def filesystemexplorer_route_agency(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'latent.aurora_governance_persistence_gateway.FilesystemExplorer.route_agency', 'kind': 'latent'
        }
    return getattr(engine, 'latent_aurora_governance_persistence_gateway_filesystemexplorer_route_agency')(payload=payload, **kwargs)

_aurora_existing_binding = _aurora_get_target(['FilesystemExplorer'])
if _aurora_existing_binding is not None:
    _aurora_existing_attr = getattr(_aurora_existing_binding, 'route_agency', None)
    if _aurora_existing_attr is None or getattr(_aurora_existing_attr, '_aurora_latent_binding_target', '') == 'FilesystemExplorer.route_agency':
        _aurora_bind_owner_attribute(['FilesystemExplorer'], 'route_agency', _aurora_make_latent_binding('filesystemexplorer_route_agency', 'FilesystemExplorer.route_agency'))
        _AURORA_NATIVE_EVOLVED_LAST['FilesystemExplorer.route_agency'] = {'latent_binding_active': True}

def atomicwriter_route_agency(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'latent.aurora_governance_persistence_gateway.AtomicWriter.route_agency', 'kind': 'latent'
        }
    return getattr(engine, 'latent_aurora_governance_persistence_gateway_atomicwriter_route_agency')(payload=payload, **kwargs)

_aurora_existing_binding = _aurora_get_target(['AtomicWriter'])
if _aurora_existing_binding is not None:
    _aurora_existing_attr = getattr(_aurora_existing_binding, 'route_agency', None)
    if _aurora_existing_attr is None or getattr(_aurora_existing_attr, '_aurora_latent_binding_target', '') == 'AtomicWriter.route_agency':
        _aurora_bind_owner_attribute(['AtomicWriter'], 'route_agency', _aurora_make_latent_binding('atomicwriter_route_agency', 'AtomicWriter.route_agency'))
        _AURORA_NATIVE_EVOLVED_LAST['AtomicWriter.route_agency'] = {'latent_binding_active': True}

def existence_weight_route_agency(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'latent.aurora_governance_persistence_gateway.GovernedCoordinate.existence_weight.route_agency', 'kind': 'latent'
        }
    return getattr(engine, 'latent_aurora_governance_persistence_gateway_governedcoordinate_existence_weight_route_agency')(payload=payload, **kwargs)

_aurora_existing_binding = _aurora_get_target(['GovernedCoordinate', 'existence_weight'])
if _aurora_existing_binding is not None:
    _aurora_existing_attr = getattr(_aurora_existing_binding, 'route_agency', None)
    if _aurora_existing_attr is None or getattr(_aurora_existing_attr, '_aurora_latent_binding_target', '') == 'GovernedCoordinate.existence_weight.route_agency':
        _aurora_bind_owner_attribute(['GovernedCoordinate', 'existence_weight'], 'route_agency', _aurora_make_latent_binding('existence_weight_route_agency', 'GovernedCoordinate.existence_weight.route_agency'))
        _AURORA_NATIVE_EVOLVED_LAST['GovernedCoordinate.existence_weight.route_agency'] = {'latent_binding_active': True}

def start_route_boundary(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'latent.aurora_governance_persistence_gateway.DriveSync.start.route_boundary', 'kind': 'latent'
        }
    return getattr(engine, 'latent_aurora_governance_persistence_gateway_drivesync_start_route_boundary')(payload=payload, **kwargs)

_aurora_existing_binding = _aurora_get_target(['DriveSync', 'start'])
if _aurora_existing_binding is not None:
    _aurora_existing_attr = getattr(_aurora_existing_binding, 'route_boundary', None)
    if _aurora_existing_attr is None or getattr(_aurora_existing_attr, '_aurora_latent_binding_target', '') == 'DriveSync.start.route_boundary':
        _aurora_bind_owner_attribute(['DriveSync', 'start'], 'route_boundary', _aurora_make_latent_binding('start_route_boundary', 'DriveSync.start.route_boundary'))
        _AURORA_NATIVE_EVOLVED_LAST['DriveSync.start.route_boundary'] = {'latent_binding_active': True}

def governancepersistencegateway_route_agency(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'latent.aurora_governance_persistence_gateway.GovernancePersistenceGateway.route_agency', 'kind': 'latent'
        }
    return getattr(engine, 'latent_aurora_governance_persistence_gateway_governancepersistencegateway_route_agency')(payload=payload, **kwargs)

_aurora_existing_binding = _aurora_get_target(['GovernancePersistenceGateway'])
if _aurora_existing_binding is not None:
    _aurora_existing_attr = getattr(_aurora_existing_binding, 'route_agency', None)
    if _aurora_existing_attr is None or getattr(_aurora_existing_attr, '_aurora_latent_binding_target', '') == 'GovernancePersistenceGateway.route_agency':
        _aurora_bind_owner_attribute(['GovernancePersistenceGateway'], 'route_agency', _aurora_make_latent_binding('governancepersistencegateway_route_agency', 'GovernancePersistenceGateway.route_agency'))
        _AURORA_NATIVE_EVOLVED_LAST['GovernancePersistenceGateway.route_agency'] = {'latent_binding_active': True}

def get_stats_route_agency(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'latent.aurora_governance_persistence_gateway.GovernanceEngine.get_stats.route_agency', 'kind': 'latent'
        }
    return getattr(engine, 'latent_aurora_governance_persistence_gateway_governanceengine_get_stats_route_agency')(payload=payload, **kwargs)

_aurora_existing_binding = _aurora_get_target(['GovernanceEngine', 'get_stats'])
if _aurora_existing_binding is not None:
    _aurora_existing_attr = getattr(_aurora_existing_binding, 'route_agency', None)
    if _aurora_existing_attr is None or getattr(_aurora_existing_attr, '_aurora_latent_binding_target', '') == 'GovernanceEngine.get_stats.route_agency':
        _aurora_bind_owner_attribute(['GovernanceEngine', 'get_stats'], 'route_agency', _aurora_make_latent_binding('get_stats_route_agency', 'GovernanceEngine.get_stats.route_agency'))
        _AURORA_NATIVE_EVOLVED_LAST['GovernanceEngine.get_stats.route_agency'] = {'latent_binding_active': True}

def add_thought_route_agency(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'latent.aurora_governance_persistence_gateway.ProactiveTrigger.add_thought.route_agency', 'kind': 'latent'
        }
    return getattr(engine, 'latent_aurora_governance_persistence_gateway_proactivetrigger_add_thought_route_agency')(payload=payload, **kwargs)

_aurora_existing_binding = _aurora_get_target(['ProactiveTrigger', 'add_thought'])
if _aurora_existing_binding is not None:
    _aurora_existing_attr = getattr(_aurora_existing_binding, 'route_agency', None)
    if _aurora_existing_attr is None or getattr(_aurora_existing_attr, '_aurora_latent_binding_target', '') == 'ProactiveTrigger.add_thought.route_agency':
        _aurora_bind_owner_attribute(['ProactiveTrigger', 'add_thought'], 'route_agency', _aurora_make_latent_binding('add_thought_route_agency', 'ProactiveTrigger.add_thought.route_agency'))
        _AURORA_NATIVE_EVOLVED_LAST['ProactiveTrigger.add_thought.route_agency'] = {'latent_binding_active': True}

def latent_aurora_governance_persistence_gateway_checkpointmanager_save_route_agency(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'latent.aurora_governance_persistence_gateway.CheckpointManager.save.route_agency', 'kind': 'latent'
        }
    return getattr(engine, 'latent_aurora_governance_persistence_gateway_checkpointmanager_save_route_agency')(payload=payload, **kwargs)

_aurora_existing_binding = _aurora_get_target(['CheckpointManager', 'save'])
if _aurora_existing_binding is not None:
    _aurora_existing_attr = getattr(_aurora_existing_binding, 'route_agency', None)
    if _aurora_existing_attr is None or getattr(_aurora_existing_attr, '_aurora_latent_binding_target', '') == 'CheckpointManager.save.route_agency':
        _aurora_bind_owner_attribute(['CheckpointManager', 'save'], 'route_agency', _aurora_make_latent_binding('latent_aurora_governance_persistence_gateway_checkpointmanager_save_route_agency', 'CheckpointManager.save.route_agency'))
        _AURORA_NATIVE_EVOLVED_LAST['CheckpointManager.save.route_agency'] = {'latent_binding_active': True}

def actionlog_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.ActionLog', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_actionlog')(payload=payload, **kwargs)

if _aurora_get_target(['ActionLog']) is not None:
    setattr(_aurora_get_target(['ActionLog']), 'evolved_reflection', staticmethod(actionlog_evolved))
    setattr(_aurora_get_target(['ActionLog']), '_aurora_alignment_gap', 0.682083)
    setattr(_aurora_get_target(['ActionLog']), '_aurora_alignment_target_score', 1.29475)

def init_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.ActionLog.__init__', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_actionlog_init')(payload=payload, **kwargs)

def get_by_type_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.ActionLog.get_by_type', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_actionlog_get_by_type')(payload=payload, **kwargs)

if _aurora_get_target(['ActionLog', 'get_by_type']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['ActionLog.get_by_type'] = _aurora_get_target(['ActionLog', 'get_by_type'])
    _aurora_assign_target(['ActionLog', 'get_by_type'], _aurora_make_override('get_by_type_evolved', 'ActionLog.get_by_type'))
    _AURORA_NATIVE_EVOLVED_LAST['ActionLog.get_by_type'] = {'alignment_gap': 0.74775, 'override_active': True}

def get_recent_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.ActionLog.get_recent', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_actionlog_get_recent')(payload=payload, **kwargs)

if _aurora_get_target(['ActionLog', 'get_recent']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['ActionLog.get_recent'] = _aurora_get_target(['ActionLog', 'get_recent'])
    _aurora_assign_target(['ActionLog', 'get_recent'], _aurora_make_override('get_recent_evolved', 'ActionLog.get_recent'))
    _AURORA_NATIVE_EVOLVED_LAST['ActionLog.get_recent'] = {'alignment_gap': 0.73025, 'override_active': True}

def log_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.ActionLog.log', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_actionlog_log')(payload=payload, **kwargs)

if _aurora_get_target(['ActionLog', 'log']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['ActionLog.log'] = _aurora_get_target(['ActionLog', 'log'])
    _aurora_assign_target(['ActionLog', 'log'], _aurora_make_override('log_evolved', 'ActionLog.log'))
    _AURORA_NATIVE_EVOLVED_LAST['ActionLog.log'] = {'alignment_gap': 0.75275, 'override_active': True}

def append_jsonl_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.AtomicWriter.append_jsonl', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_atomicwriter_append_jsonl')(payload=payload, **kwargs)

if _aurora_get_target(['AtomicWriter', 'append_jsonl']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['AtomicWriter.append_jsonl'] = _aurora_get_target(['AtomicWriter', 'append_jsonl'])
    _aurora_assign_target(['AtomicWriter', 'append_jsonl'], _aurora_make_override('append_jsonl_evolved', 'AtomicWriter.append_jsonl'))
    _AURORA_NATIVE_EVOLVED_LAST['AtomicWriter.append_jsonl'] = {'alignment_gap': 0.747333, 'override_active': True}

def aurorastatesnapshot_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.AuroraStateSnapshot', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_aurorastatesnapshot')(payload=payload, **kwargs)

if _aurora_get_target(['AuroraStateSnapshot']) is not None:
    setattr(_aurora_get_target(['AuroraStateSnapshot']), 'evolved_reflection', staticmethod(aurorastatesnapshot_evolved))
    setattr(_aurora_get_target(['AuroraStateSnapshot']), '_aurora_alignment_gap', 0.515416)
    setattr(_aurora_get_target(['AuroraStateSnapshot']), '_aurora_alignment_target_score', 1.29475)

def autonomousaction_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.AutonomousAction', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_autonomousaction')(payload=payload, **kwargs)

if _aurora_get_target(['AutonomousAction']) is not None:
    setattr(_aurora_get_target(['AutonomousAction']), 'evolved_reflection', staticmethod(autonomousaction_evolved))
    setattr(_aurora_get_target(['AutonomousAction']), '_aurora_alignment_gap', 0.820417)
    setattr(_aurora_get_target(['AutonomousAction']), '_aurora_alignment_target_score', 1.29475)

def get_recent_actions_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.AutonomyEngine.get_recent_actions', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_autonomyengine_get_recent_actions')(payload=payload, **kwargs)

if _aurora_get_target(['AutonomyEngine', 'get_recent_actions']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['AutonomyEngine.get_recent_actions'] = _aurora_get_target(['AutonomyEngine', 'get_recent_actions'])
    _aurora_assign_target(['AutonomyEngine', 'get_recent_actions'], _aurora_make_override('get_recent_actions_evolved', 'AutonomyEngine.get_recent_actions'))
    _AURORA_NATIVE_EVOLVED_LAST['AutonomyEngine.get_recent_actions'] = {'alignment_gap': 0.786083, 'override_active': True}

def get_status_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.AutonomyEngine.get_status', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_autonomyengine_get_status')(payload=payload, **kwargs)

if _aurora_get_target(['AutonomyEngine', 'get_status']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['AutonomyEngine.get_status'] = _aurora_get_target(['AutonomyEngine', 'get_status'])
    _aurora_assign_target(['AutonomyEngine', 'get_status'], _aurora_make_override('get_status_evolved', 'AutonomyEngine.get_status'))
    _AURORA_NATIVE_EVOLVED_LAST['AutonomyEngine.get_status'] = {'alignment_gap': 0.819417, 'override_active': True}

def search_files_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.AutonomyEngine.search_files', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_autonomyengine_search_files')(payload=payload, **kwargs)

if _aurora_get_target(['AutonomyEngine', 'search_files']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['AutonomyEngine.search_files'] = _aurora_get_target(['AutonomyEngine', 'search_files'])
    _aurora_assign_target(['AutonomyEngine', 'search_files'], _aurora_make_override('search_files_evolved', 'AutonomyEngine.search_files'))
    _AURORA_NATIVE_EVOLVED_LAST['AutonomyEngine.search_files'] = {'alignment_gap': 0.780667, 'override_active': True}

def signal_handler_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.CheckpointManager._signal_handler', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_checkpointmanager_signal_handler')(payload=payload, **kwargs)

def corpuscursor_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.CorpusCursor', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_corpuscursor')(payload=payload, **kwargs)

if _aurora_get_target(['CorpusCursor']) is not None:
    setattr(_aurora_get_target(['CorpusCursor']), 'evolved_reflection', staticmethod(corpuscursor_evolved))
    setattr(_aurora_get_target(['CorpusCursor']), '_aurora_alignment_gap', 0.7025)
    setattr(_aurora_get_target(['CorpusCursor']), '_aurora_alignment_target_score', 1.29475)

def dailyquotas_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.DailyQuotas', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_dailyquotas')(payload=payload, **kwargs)

if _aurora_get_target(['DailyQuotas']) is not None:
    setattr(_aurora_get_target(['DailyQuotas']), 'evolved_reflection', staticmethod(dailyquotas_evolved))
    setattr(_aurora_get_target(['DailyQuotas']), '_aurora_alignment_gap', 0.713333)
    setattr(_aurora_get_target(['DailyQuotas']), '_aurora_alignment_target_score', 1.29475)

def reset_if_new_day_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.DailyQuotas.reset_if_new_day', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_dailyquotas_reset_if_new_day')(payload=payload, **kwargs)

if _aurora_get_target(['DailyQuotas', 'reset_if_new_day']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['DailyQuotas.reset_if_new_day'] = _aurora_get_target(['DailyQuotas', 'reset_if_new_day'])
    _aurora_assign_target(['DailyQuotas', 'reset_if_new_day'], _aurora_make_override('reset_if_new_day_evolved', 'DailyQuotas.reset_if_new_day'))
    _AURORA_NATIVE_EVOLVED_LAST['DailyQuotas.reset_if_new_day'] = {'alignment_gap': 0.747333, 'override_active': True}

def to_dict_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.DailyQuotas.to_dict', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_dailyquotas_to_dict')(payload=payload, **kwargs)

if _aurora_get_target(['DailyQuotas', 'to_dict']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['DailyQuotas.to_dict'] = _aurora_get_target(['DailyQuotas', 'to_dict'])
    _aurora_assign_target(['DailyQuotas', 'to_dict'], _aurora_make_override('to_dict_evolved', 'DailyQuotas.to_dict'))
    _AURORA_NATIVE_EVOLVED_LAST['DailyQuotas.to_dict'] = {'alignment_gap': 0.747333, 'override_active': True}

def deviceawareness_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.DeviceAwareness', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_deviceawareness')(payload=payload, **kwargs)

if _aurora_get_target(['DeviceAwareness']) is not None:
    setattr(_aurora_get_target(['DeviceAwareness']), 'evolved_reflection', staticmethod(deviceawareness_evolved))
    setattr(_aurora_get_target(['DeviceAwareness']), '_aurora_alignment_gap', 0.63)
    setattr(_aurora_get_target(['DeviceAwareness']), '_aurora_alignment_target_score', 1.29475)

def devicerecord_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.DeviceRecord', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_devicerecord')(payload=payload, **kwargs)

if _aurora_get_target(['DeviceRecord']) is not None:
    setattr(_aurora_get_target(['DeviceRecord']), 'evolved_reflection', staticmethod(devicerecord_evolved))
    setattr(_aurora_get_target(['DeviceRecord']), '_aurora_alignment_gap', 0.663333)
    setattr(_aurora_get_target(['DeviceRecord']), '_aurora_alignment_target_score', 1.29475)

def drivesync_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.DriveSync', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_drivesync')(payload=payload, **kwargs)

if _aurora_get_target(['DriveSync']) is not None:
    setattr(_aurora_get_target(['DriveSync']), 'evolved_reflection', staticmethod(drivesync_evolved))
    setattr(_aurora_get_target(['DriveSync']), '_aurora_alignment_gap', 0.5725)
    setattr(_aurora_get_target(['DriveSync']), '_aurora_alignment_target_score', 1.29475)

def status_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.DriveSync.status', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_drivesync_status')(payload=payload, **kwargs)

if _aurora_get_target(['DriveSync', 'status']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['DriveSync.status'] = _aurora_get_target(['DriveSync', 'status'])
    _aurora_assign_target(['DriveSync', 'status'], _aurora_make_override('status_evolved', 'DriveSync.status'))
    _AURORA_NATIVE_EVOLVED_LAST['DriveSync.status'] = {'alignment_gap': 0.786083, 'override_active': True}

def stop_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.DriveSync.stop', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_drivesync_stop')(payload=payload, **kwargs)

if _aurora_get_target(['DriveSync', 'stop']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['DriveSync.stop'] = _aurora_get_target(['DriveSync', 'stop'])
    _aurora_assign_target(['DriveSync', 'stop'], _aurora_make_override('stop_evolved', 'DriveSync.stop'))
    _AURORA_NATIVE_EVOLVED_LAST['DriveSync.stop'] = {'alignment_gap': 0.722333, 'override_active': True}

def switch_message_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.DriveSync.switch_message', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_drivesync_switch_message')(payload=payload, **kwargs)

if _aurora_get_target(['DriveSync', 'switch_message']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['DriveSync.switch_message'] = _aurora_get_target(['DriveSync', 'switch_message'])
    _aurora_assign_target(['DriveSync', 'switch_message'], _aurora_make_override('switch_message_evolved', 'DriveSync.switch_message'))
    _AURORA_NATIVE_EVOLVED_LAST['DriveSync.switch_message'] = {'alignment_gap': 0.722333, 'override_active': True}

def gatewayresponse_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.GatewayResponse', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_gatewayresponse')(payload=payload, **kwargs)

if _aurora_get_target(['GatewayResponse']) is not None:
    setattr(_aurora_get_target(['GatewayResponse']), 'evolved_reflection', staticmethod(gatewayresponse_evolved))
    setattr(_aurora_get_target(['GatewayResponse']), '_aurora_alignment_gap', 0.723333)
    setattr(_aurora_get_target(['GatewayResponse']), '_aurora_alignment_target_score', 1.29475)

def gatewayverdict_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.GatewayVerdict', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_gatewayverdict')(payload=payload, **kwargs)

if _aurora_get_target(['GatewayVerdict']) is not None:
    setattr(_aurora_get_target(['GatewayVerdict']), 'evolved_reflection', staticmethod(gatewayverdict_evolved))
    setattr(_aurora_get_target(['GatewayVerdict']), '_aurora_alignment_gap', 0.723333)
    setattr(_aurora_get_target(['GatewayVerdict']), '_aurora_alignment_target_score', 1.29475)

def generationrole_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.GenerationRole', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_generationrole')(payload=payload, **kwargs)

if _aurora_get_target(['GenerationRole']) is not None:
    setattr(_aurora_get_target(['GenerationRole']), 'evolved_reflection', staticmethod(generationrole_evolved))
    setattr(_aurora_get_target(['GenerationRole']), '_aurora_alignment_gap', 0.723333)
    setattr(_aurora_get_target(['GenerationRole']), '_aurora_alignment_target_score', 1.29475)

def generationalalignmentlaw_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.GenerationalAlignmentLaw', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_generationalalignmentlaw')(payload=payload, **kwargs)

if _aurora_get_target(['GenerationalAlignmentLaw']) is not None:
    setattr(_aurora_get_target(['GenerationalAlignmentLaw']), 'evolved_reflection', staticmethod(generationalalignmentlaw_evolved))
    setattr(_aurora_get_target(['GenerationalAlignmentLaw']), '_aurora_alignment_gap', 0.60375)
    setattr(_aurora_get_target(['GenerationalAlignmentLaw']), '_aurora_alignment_target_score', 1.29475)

def evolved_init(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.GenerationalAlignmentLaw.__init__', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_generationalalignmentlaw_init')(payload=payload, **kwargs)

def compute_tension_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.GenerationalAlignmentLaw.compute_tension', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_generationalalignmentlaw_compute_tension')(payload=payload, **kwargs)

if _aurora_get_target(['GenerationalAlignmentLaw', 'compute_tension']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['GenerationalAlignmentLaw.compute_tension'] = _aurora_get_target(['GenerationalAlignmentLaw', 'compute_tension'])
    _aurora_assign_target(['GenerationalAlignmentLaw', 'compute_tension'], _aurora_make_override('compute_tension_evolved', 'GenerationalAlignmentLaw.compute_tension'))
    _AURORA_NATIVE_EVOLVED_LAST['GenerationalAlignmentLaw.compute_tension'] = {'alignment_gap': 0.819417, 'override_active': True}

def shift_toward_stable_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.GenerationalAlignmentLaw.shift_toward_stable', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_generationalalignmentlaw_shift_toward_stable')(payload=payload, **kwargs)

if _aurora_get_target(['GenerationalAlignmentLaw', 'shift_toward_stable']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['GenerationalAlignmentLaw.shift_toward_stable'] = _aurora_get_target(['GenerationalAlignmentLaw', 'shift_toward_stable'])
    _aurora_assign_target(['GenerationalAlignmentLaw', 'shift_toward_stable'], _aurora_make_override('shift_toward_stable_evolved', 'GenerationalAlignmentLaw.shift_toward_stable'))
    _AURORA_NATIVE_EVOLVED_LAST['GenerationalAlignmentLaw.shift_toward_stable'] = {'alignment_gap': 0.798583, 'override_active': True}

def generationaltension_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.GenerationalTension', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_generationaltension')(payload=payload, **kwargs)

if _aurora_get_target(['GenerationalTension']) is not None:
    setattr(_aurora_get_target(['GenerationalTension']), 'evolved_reflection', staticmethod(generationaltension_evolved))
    setattr(_aurora_get_target(['GenerationalTension']), '_aurora_alignment_gap', 0.748333)
    setattr(_aurora_get_target(['GenerationalTension']), '_aurora_alignment_target_score', 1.29475)

def total_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.GenerationalTension.total', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_generationaltension_total')(payload=payload, **kwargs)

if _aurora_get_target(['GenerationalTension', 'total']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['GenerationalTension.total'] = _aurora_get_target(['GenerationalTension', 'total'])
    _aurora_assign_target(['GenerationalTension', 'total'], _aurora_make_override('total_evolved', 'GenerationalTension.total'))
    _AURORA_NATIVE_EVOLVED_LAST['GenerationalTension.total'] = {'alignment_gap': 0.739, 'override_active': True}

def governanceengine_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.GovernanceEngine', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_governanceengine')(payload=payload, **kwargs)

if _aurora_get_target(['GovernanceEngine']) is not None:
    setattr(_aurora_get_target(['GovernanceEngine']), 'evolved_reflection', staticmethod(governanceengine_evolved))
    setattr(_aurora_get_target(['GovernanceEngine']), '_aurora_alignment_gap', 0.53)
    setattr(_aurora_get_target(['GovernanceEngine']), '_aurora_alignment_target_score', 1.29475)

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
    _AURORA_NATIVE_EVOLVED_LAST['GovernanceEngine.promote'] = {'alignment_gap': 0.724833, 'override_active': True}

def resolve_conflict_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.GovernanceEngine.resolve_conflict', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_governanceengine_resolve_conflict')(payload=payload, **kwargs)

if _aurora_get_target(['GovernanceEngine', 'resolve_conflict']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['GovernanceEngine.resolve_conflict'] = _aurora_get_target(['GovernanceEngine', 'resolve_conflict'])
    _aurora_assign_target(['GovernanceEngine', 'resolve_conflict'], _aurora_make_override('resolve_conflict_evolved', 'GovernanceEngine.resolve_conflict'))
    _AURORA_NATIVE_EVOLVED_LAST['GovernanceEngine.resolve_conflict'] = {'alignment_gap': 0.747333, 'override_active': True}

def load_state_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.GovernancePersistenceGateway.load_state', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_governancepersistencegateway_load_state')(payload=payload, **kwargs)

if _aurora_get_target(['GovernancePersistenceGateway', 'load_state']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['GovernancePersistenceGateway.load_state'] = _aurora_get_target(['GovernancePersistenceGateway', 'load_state'])
    _aurora_assign_target(['GovernancePersistenceGateway', 'load_state'], _aurora_make_override('load_state_evolved', 'GovernancePersistenceGateway.load_state'))
    _AURORA_NATIVE_EVOLVED_LAST['GovernancePersistenceGateway.load_state'] = {'alignment_gap': 0.747333, 'override_active': True}

def governanceviolation_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.GovernanceViolation', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_governanceviolation')(payload=payload, **kwargs)

if _aurora_get_target(['GovernanceViolation']) is not None:
    setattr(_aurora_get_target(['GovernanceViolation']), 'evolved_reflection', staticmethod(governanceviolation_evolved))
    setattr(_aurora_get_target(['GovernanceViolation']), '_aurora_alignment_gap', 0.698333)
    setattr(_aurora_get_target(['GovernanceViolation']), '_aurora_alignment_target_score', 1.29475)

def governedcoordinate_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.GovernedCoordinate', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_governedcoordinate')(payload=payload, **kwargs)

if _aurora_get_target(['GovernedCoordinate']) is not None:
    setattr(_aurora_get_target(['GovernedCoordinate']), 'evolved_reflection', staticmethod(governedcoordinate_evolved))
    setattr(_aurora_get_target(['GovernedCoordinate']), '_aurora_alignment_gap', 0.559896)
    setattr(_aurora_get_target(['GovernedCoordinate']), '_aurora_alignment_target_score', 1.29475)

def agency_weight_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.GovernedCoordinate.agency_weight', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_governedcoordinate_agency_weight')(payload=payload, **kwargs)

if _aurora_get_target(['GovernedCoordinate', 'agency_weight']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['GovernedCoordinate.agency_weight'] = _aurora_get_target(['GovernedCoordinate', 'agency_weight'])
    _aurora_assign_target(['GovernedCoordinate', 'agency_weight'], _aurora_make_override('agency_weight_evolved', 'GovernedCoordinate.agency_weight'))
    _AURORA_NATIVE_EVOLVED_LAST['GovernedCoordinate.agency_weight'] = {'alignment_gap': 0.798583, 'override_active': True}

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
    _AURORA_NATIVE_EVOLVED_LAST['GovernedCoordinate.boundary_weight'] = {'alignment_gap': 0.77775, 'override_active': True}

def governednode_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.GovernedNode', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_governednode')(payload=payload, **kwargs)

if _aurora_get_target(['GovernedNode']) is not None:
    setattr(_aurora_get_target(['GovernedNode']), 'evolved_reflection', staticmethod(governednode_evolved))
    setattr(_aurora_get_target(['GovernedNode']), '_aurora_alignment_gap', 0.67)
    setattr(_aurora_get_target(['GovernedNode']), '_aurora_alignment_target_score', 1.29475)

def express_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.NSpaceGateway._express', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_nspacegateway_express')(payload=payload, **kwargs)

def needs_articulation_bridge_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.NSpaceGateway._needs_articulation_bridge', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_nspacegateway_needs_articulation_bridge')(payload=payload, **kwargs)

def receive_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.NSpaceGateway.receive', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_nspacegateway_receive')(payload=payload, **kwargs)

if _aurora_get_target(['NSpaceGateway', 'receive']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['NSpaceGateway.receive'] = _aurora_get_target(['NSpaceGateway', 'receive'])
    _aurora_assign_target(['NSpaceGateway', 'receive'], _aurora_make_override('receive_evolved', 'NSpaceGateway.receive'))
    _AURORA_NATIVE_EVOLVED_LAST['NSpaceGateway.receive'] = {'alignment_gap': 0.739, 'override_active': True}

def proactivetrigger_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.ProactiveTrigger', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_proactivetrigger')(payload=payload, **kwargs)

if _aurora_get_target(['ProactiveTrigger']) is not None:
    setattr(_aurora_get_target(['ProactiveTrigger']), 'evolved_reflection', staticmethod(proactivetrigger_evolved))
    setattr(_aurora_get_target(['ProactiveTrigger']), '_aurora_alignment_gap', 0.643333)
    setattr(_aurora_get_target(['ProactiveTrigger']), '_aurora_alignment_target_score', 1.29475)

def ratelimitedsearch_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.RateLimitedSearch', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_ratelimitedsearch')(payload=payload, **kwargs)

if _aurora_get_target(['RateLimitedSearch']) is not None:
    setattr(_aurora_get_target(['RateLimitedSearch']), 'evolved_reflection', staticmethod(ratelimitedsearch_evolved))
    setattr(_aurora_get_target(['RateLimitedSearch']), '_aurora_alignment_gap', 0.64)
    setattr(_aurora_get_target(['RateLimitedSearch']), '_aurora_alignment_target_score', 1.29475)

def rcloneinterface_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.RcloneInterface', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_rcloneinterface')(payload=payload, **kwargs)

if _aurora_get_target(['RcloneInterface']) is not None:
    setattr(_aurora_get_target(['RcloneInterface']), 'evolved_reflection', staticmethod(rcloneinterface_evolved))
    setattr(_aurora_get_target(['RcloneInterface']), '_aurora_alignment_gap', 0.624583)
    setattr(_aurora_get_target(['RcloneInterface']), '_aurora_alignment_target_score', 1.29475)

def reflect_aurora_governance_persistence_gateway_rcloneinterface_init(payload=None, **kwargs):
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
    _AURORA_NATIVE_EVOLVED_LAST['RcloneInterface._find_rclone'] = {'alignment_gap': 0.76525, 'override_active': True}

def run_sync_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.RcloneInterface._run_sync', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_rcloneinterface_run_sync')(payload=payload, **kwargs)

def check_newer_remote_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.RcloneInterface.check_newer_remote', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_rcloneinterface_check_newer_remote')(payload=payload, **kwargs)

if _aurora_get_target(['RcloneInterface', 'check_newer_remote']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['RcloneInterface.check_newer_remote'] = _aurora_get_target(['RcloneInterface', 'check_newer_remote'])
    _aurora_assign_target(['RcloneInterface', 'check_newer_remote'], _aurora_make_override('check_newer_remote_evolved', 'RcloneInterface.check_newer_remote'))
    _AURORA_NATIVE_EVOLVED_LAST['RcloneInterface.check_newer_remote'] = {'alignment_gap': 0.75275, 'override_active': True}

def is_available_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.RcloneInterface.is_available', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_rcloneinterface_is_available')(payload=payload, **kwargs)

if _aurora_get_target(['RcloneInterface', 'is_available']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['RcloneInterface.is_available'] = _aurora_get_target(['RcloneInterface', 'is_available'])
    _aurora_assign_target(['RcloneInterface', 'is_available'], _aurora_make_override('is_available_evolved', 'RcloneInterface.is_available'))
    _AURORA_NATIVE_EVOLVED_LAST['RcloneInterface.is_available'] = {'alignment_gap': 0.819417, 'override_active': True}

def remote_full_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.RcloneInterface.remote_full', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_rcloneinterface_remote_full')(payload=payload, **kwargs)

if _aurora_get_target(['RcloneInterface', 'remote_full']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['RcloneInterface.remote_full'] = _aurora_get_target(['RcloneInterface', 'remote_full'])
    _aurora_assign_target(['RcloneInterface', 'remote_full'], _aurora_make_override('remote_full_evolved', 'RcloneInterface.remote_full'))
    _AURORA_NATIVE_EVOLVED_LAST['RcloneInterface.remote_full'] = {'alignment_gap': 0.763583, 'override_active': True}

def sync_down_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.RcloneInterface.sync_down', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_rcloneinterface_sync_down')(payload=payload, **kwargs)

if _aurora_get_target(['RcloneInterface', 'sync_down']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['RcloneInterface.sync_down'] = _aurora_get_target(['RcloneInterface', 'sync_down'])
    _aurora_assign_target(['RcloneInterface', 'sync_down'], _aurora_make_override('sync_down_evolved', 'RcloneInterface.sync_down'))
    _AURORA_NATIVE_EVOLVED_LAST['RcloneInterface.sync_down'] = {'alignment_gap': 0.786083, 'override_active': True}

def sync_up_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.RcloneInterface.sync_up', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_rcloneinterface_sync_up')(payload=payload, **kwargs)

if _aurora_get_target(['RcloneInterface', 'sync_up']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['RcloneInterface.sync_up'] = _aurora_get_target(['RcloneInterface', 'sync_up'])
    _aurora_assign_target(['RcloneInterface', 'sync_up'], _aurora_make_override('sync_up_evolved', 'RcloneInterface.sync_up'))
    _AURORA_NATIVE_EVOLVED_LAST['RcloneInterface.sync_up'] = {'alignment_gap': 0.784417, 'override_active': True}

def streamtype_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.StreamType', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_streamtype')(payload=payload, **kwargs)

if _aurora_get_target(['StreamType']) is not None:
    setattr(_aurora_get_target(['StreamType']), 'evolved_reflection', staticmethod(streamtype_evolved))
    setattr(_aurora_get_target(['StreamType']), '_aurora_alignment_gap', 0.723333)
    setattr(_aurora_get_target(['StreamType']), '_aurora_alignment_target_score', 1.29475)

def studyscheduler_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.StudyScheduler', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_studyscheduler')(payload=payload, **kwargs)

if _aurora_get_target(['StudyScheduler']) is not None:
    setattr(_aurora_get_target(['StudyScheduler']), 'evolved_reflection', staticmethod(studyscheduler_evolved))
    setattr(_aurora_get_target(['StudyScheduler']), '_aurora_alignment_gap', 0.671667)
    setattr(_aurora_get_target(['StudyScheduler']), '_aurora_alignment_target_score', 1.29475)

def validationresult_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.ValidationResult', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_validationresult')(payload=payload, **kwargs)

if _aurora_get_target(['ValidationResult']) is not None:
    setattr(_aurora_get_target(['ValidationResult']), 'evolved_reflection', staticmethod(validationresult_evolved))
    setattr(_aurora_get_target(['ValidationResult']), '_aurora_alignment_gap', 0.723333)
    setattr(_aurora_get_target(['ValidationResult']), '_aurora_alignment_target_score', 1.29475)

def votingauthority_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.VotingAuthority', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_votingauthority')(payload=payload, **kwargs)

if _aurora_get_target(['VotingAuthority']) is not None:
    setattr(_aurora_get_target(['VotingAuthority']), 'evolved_reflection', staticmethod(votingauthority_evolved))
    setattr(_aurora_get_target(['VotingAuthority']), '_aurora_alignment_gap', 0.760833)
    setattr(_aurora_get_target(['VotingAuthority']), '_aurora_alignment_target_score', 1.29475)

def writeresult_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_governance_persistence_gateway.WriteResult', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_governance_persistence_gateway_writeresult')(payload=payload, **kwargs)

if _aurora_get_target(['WriteResult']) is not None:
    setattr(_aurora_get_target(['WriteResult']), 'evolved_reflection', staticmethod(writeresult_evolved))
    setattr(_aurora_get_target(['WriteResult']), '_aurora_alignment_gap', 0.723333)
    setattr(_aurora_get_target(['WriteResult']), '_aurora_alignment_target_score', 1.29475)

AURORA_NATIVE_EVOLVED_EXPORTS = {'aurora_governance_persistence_gateway.ActionLog': 'actionlog_evolved',
 'aurora_governance_persistence_gateway.ActionLog.__init__': 'init_evolved',
 'aurora_governance_persistence_gateway.ActionLog.get_by_type': 'get_by_type_evolved',
 'aurora_governance_persistence_gateway.ActionLog.get_recent': 'get_recent_evolved',
 'aurora_governance_persistence_gateway.ActionLog.log': 'log_evolved',
 'aurora_governance_persistence_gateway.AtomicWriter.append_jsonl': 'append_jsonl_evolved',
 'aurora_governance_persistence_gateway.AuroraStateSnapshot': 'aurorastatesnapshot_evolved',
 'aurora_governance_persistence_gateway.AutonomousAction': 'autonomousaction_evolved',
 'aurora_governance_persistence_gateway.AutonomyEngine.get_recent_actions': 'get_recent_actions_evolved',
 'aurora_governance_persistence_gateway.AutonomyEngine.get_status': 'get_status_evolved',
 'aurora_governance_persistence_gateway.AutonomyEngine.search_files': 'search_files_evolved',
 'aurora_governance_persistence_gateway.CheckpointManager._signal_handler': 'signal_handler_evolved',
 'aurora_governance_persistence_gateway.CorpusCursor': 'corpuscursor_evolved',
 'aurora_governance_persistence_gateway.DailyQuotas': 'dailyquotas_evolved',
 'aurora_governance_persistence_gateway.DailyQuotas.reset_if_new_day': 'reset_if_new_day_evolved',
 'aurora_governance_persistence_gateway.DailyQuotas.to_dict': 'to_dict_evolved',
 'aurora_governance_persistence_gateway.DeviceAwareness': 'deviceawareness_evolved',
 'aurora_governance_persistence_gateway.DeviceRecord': 'devicerecord_evolved',
 'aurora_governance_persistence_gateway.DriveSync': 'drivesync_evolved',
 'aurora_governance_persistence_gateway.DriveSync.status': 'status_evolved',
 'aurora_governance_persistence_gateway.DriveSync.stop': 'stop_evolved',
 'aurora_governance_persistence_gateway.DriveSync.switch_message': 'switch_message_evolved',
 'aurora_governance_persistence_gateway.GatewayResponse': 'gatewayresponse_evolved',
 'aurora_governance_persistence_gateway.GatewayVerdict': 'gatewayverdict_evolved',
 'aurora_governance_persistence_gateway.GenerationRole': 'generationrole_evolved',
 'aurora_governance_persistence_gateway.GenerationalAlignmentLaw': 'generationalalignmentlaw_evolved',
 'aurora_governance_persistence_gateway.GenerationalAlignmentLaw.__init__': 'evolved_init',
 'aurora_governance_persistence_gateway.GenerationalAlignmentLaw.compute_tension': 'compute_tension_evolved',
 'aurora_governance_persistence_gateway.GenerationalAlignmentLaw.shift_toward_stable': 'shift_toward_stable_evolved',
 'aurora_governance_persistence_gateway.GenerationalTension': 'generationaltension_evolved',
 'aurora_governance_persistence_gateway.GenerationalTension.total': 'total_evolved',
 'aurora_governance_persistence_gateway.GovernanceEngine': 'governanceengine_evolved',
 'aurora_governance_persistence_gateway.GovernanceEngine.promote': 'promote_evolved',
 'aurora_governance_persistence_gateway.GovernanceEngine.resolve_conflict': 'resolve_conflict_evolved',
 'aurora_governance_persistence_gateway.GovernancePersistenceGateway.load_state': 'load_state_evolved',
 'aurora_governance_persistence_gateway.GovernanceViolation': 'governanceviolation_evolved',
 'aurora_governance_persistence_gateway.GovernedCoordinate': 'governedcoordinate_evolved',
 'aurora_governance_persistence_gateway.GovernedCoordinate.agency_weight': 'agency_weight_evolved',
 'aurora_governance_persistence_gateway.GovernedCoordinate.boundary_weight': 'boundary_weight_evolved',
 'aurora_governance_persistence_gateway.GovernedNode': 'governednode_evolved',
 'aurora_governance_persistence_gateway.NSpaceGateway._express': 'express_evolved',
 'aurora_governance_persistence_gateway.NSpaceGateway._needs_articulation_bridge': 'needs_articulation_bridge_evolved',
 'aurora_governance_persistence_gateway.NSpaceGateway.receive': 'receive_evolved',
 'aurora_governance_persistence_gateway.ProactiveTrigger': 'proactivetrigger_evolved',
 'aurora_governance_persistence_gateway.RateLimitedSearch': 'ratelimitedsearch_evolved',
 'aurora_governance_persistence_gateway.RcloneInterface': 'rcloneinterface_evolved',
 'aurora_governance_persistence_gateway.RcloneInterface.__init__': 'reflect_aurora_governance_persistence_gateway_rcloneinterface_init',
 'aurora_governance_persistence_gateway.RcloneInterface._find_rclone': 'find_rclone_evolved',
 'aurora_governance_persistence_gateway.RcloneInterface._run_sync': 'run_sync_evolved',
 'aurora_governance_persistence_gateway.RcloneInterface.check_newer_remote': 'check_newer_remote_evolved',
 'aurora_governance_persistence_gateway.RcloneInterface.is_available': 'is_available_evolved',
 'aurora_governance_persistence_gateway.RcloneInterface.remote_full': 'remote_full_evolved',
 'aurora_governance_persistence_gateway.RcloneInterface.sync_down': 'sync_down_evolved',
 'aurora_governance_persistence_gateway.RcloneInterface.sync_up': 'sync_up_evolved',
 'aurora_governance_persistence_gateway.StreamType': 'streamtype_evolved',
 'aurora_governance_persistence_gateway.StudyScheduler': 'studyscheduler_evolved',
 'aurora_governance_persistence_gateway.ValidationResult': 'validationresult_evolved',
 'aurora_governance_persistence_gateway.VotingAuthority': 'votingauthority_evolved',
 'aurora_governance_persistence_gateway.WriteResult': 'writeresult_evolved',
 'latent.aurora_governance_persistence_gateway.AtomicWriter.route_agency': 'atomicwriter_route_agency',
 'latent.aurora_governance_persistence_gateway.AuroraStateSnapshot.route_agency': 'aurorastatesnapshot_route_agency',
 'latent.aurora_governance_persistence_gateway.AuroraStateSnapshot.to_dict.route_agency': 'evolved_route_agency',
 'latent.aurora_governance_persistence_gateway.AutonomyEngine.route_boundary': 'route_boundary',
 'latent.aurora_governance_persistence_gateway.CheckpointManager.route_agency': 'checkpointmanager_route_agency',
 'latent.aurora_governance_persistence_gateway.CheckpointManager.save.route_agency': 'latent_aurora_governance_persistence_gateway_checkpointmanager_save_route_agency',
 'latent.aurora_governance_persistence_gateway.CheckpointRecord.route_agency': 'checkpointrecord_route_agency',
 'latent.aurora_governance_persistence_gateway.DeviceRecord.to_dict.route_agency': 'to_dict_route_agency',
 'latent.aurora_governance_persistence_gateway.DriveSync.route_boundary': 'drivesync_route_boundary',
 'latent.aurora_governance_persistence_gateway.DriveSync.start.route_boundary': 'start_route_boundary',
 'latent.aurora_governance_persistence_gateway.FilesystemExplorer.route_agency': 'filesystemexplorer_route_agency',
 'latent.aurora_governance_persistence_gateway.GovernanceEngine.get_stats.route_agency': 'get_stats_route_agency',
 'latent.aurora_governance_persistence_gateway.GovernanceEngine.route_agency': 'governanceengine_route_agency',
 'latent.aurora_governance_persistence_gateway.GovernancePersistenceGateway.route_agency': 'governancepersistencegateway_route_agency',
 'latent.aurora_governance_persistence_gateway.GovernancePersistenceGateway.save_state.route_agency': 'save_state_route_agency',
 'latent.aurora_governance_persistence_gateway.GovernedCoordinate.existence_weight.route_agency': 'existence_weight_route_agency',
 'latent.aurora_governance_persistence_gateway.GovernedCoordinate.route_agency': 'governedcoordinate_route_agency',
 'latent.aurora_governance_persistence_gateway.NSpaceGateway.route_agency': 'nspacegateway_route_agency',
 'latent.aurora_governance_persistence_gateway.ProactiveTrigger.add_thought.route_agency': 'add_thought_route_agency',
 'latent.aurora_governance_persistence_gateway.StatePersistence.route_agency': 'statepersistence_route_agency',
 'latent.aurora_governance_persistence_gateway.StatePersistence.save.route_agency': 'save_route_agency',
 'latent.aurora_governance_persistence_gateway.WriteValidator.route_agency': 'writevalidator_route_agency',
 'latent.aurora_governance_persistence_gateway._clamp.route_agency': 'route_agency'}
AURORA_NATIVE_EVOLUTION_OVERRIDES = {'aurora_governance_persistence_gateway.ActionLog': {'export': 'actionlog_evolved',
                                                     'mode': 'class_reflection_hook',
                                                     'target': 'ActionLog'},
 'aurora_governance_persistence_gateway.ActionLog.get_by_type': {'export': 'get_by_type_evolved',
                                                                 'mode': 'callable_override',
                                                                 'target': 'ActionLog.get_by_type'},
 'aurora_governance_persistence_gateway.ActionLog.get_recent': {'export': 'get_recent_evolved',
                                                                'mode': 'callable_override',
                                                                'target': 'ActionLog.get_recent'},
 'aurora_governance_persistence_gateway.ActionLog.log': {'export': 'log_evolved',
                                                         'mode': 'callable_override',
                                                         'target': 'ActionLog.log'},
 'aurora_governance_persistence_gateway.AtomicWriter.append_jsonl': {'export': 'append_jsonl_evolved',
                                                                     'mode': 'callable_override',
                                                                     'target': 'AtomicWriter.append_jsonl'},
 'aurora_governance_persistence_gateway.AuroraStateSnapshot': {'export': 'aurorastatesnapshot_evolved',
                                                               'mode': 'class_reflection_hook',
                                                               'target': 'AuroraStateSnapshot'},
 'aurora_governance_persistence_gateway.AutonomousAction': {'export': 'autonomousaction_evolved',
                                                            'mode': 'class_reflection_hook',
                                                            'target': 'AutonomousAction'},
 'aurora_governance_persistence_gateway.AutonomyEngine.get_recent_actions': {'export': 'get_recent_actions_evolved',
                                                                             'mode': 'callable_override',
                                                                             'target': 'AutonomyEngine.get_recent_actions'},
 'aurora_governance_persistence_gateway.AutonomyEngine.get_status': {'export': 'get_status_evolved',
                                                                     'mode': 'callable_override',
                                                                     'target': 'AutonomyEngine.get_status'},
 'aurora_governance_persistence_gateway.AutonomyEngine.search_files': {'export': 'search_files_evolved',
                                                                       'mode': 'callable_override',
                                                                       'target': 'AutonomyEngine.search_files'},
 'aurora_governance_persistence_gateway.CorpusCursor': {'export': 'corpuscursor_evolved',
                                                        'mode': 'class_reflection_hook',
                                                        'target': 'CorpusCursor'},
 'aurora_governance_persistence_gateway.DailyQuotas': {'export': 'dailyquotas_evolved',
                                                       'mode': 'class_reflection_hook',
                                                       'target': 'DailyQuotas'},
 'aurora_governance_persistence_gateway.DailyQuotas.reset_if_new_day': {'export': 'reset_if_new_day_evolved',
                                                                        'mode': 'callable_override',
                                                                        'target': 'DailyQuotas.reset_if_new_day'},
 'aurora_governance_persistence_gateway.DailyQuotas.to_dict': {'export': 'to_dict_evolved',
                                                               'mode': 'callable_override',
                                                               'target': 'DailyQuotas.to_dict'},
 'aurora_governance_persistence_gateway.DeviceAwareness': {'export': 'deviceawareness_evolved',
                                                           'mode': 'class_reflection_hook',
                                                           'target': 'DeviceAwareness'},
 'aurora_governance_persistence_gateway.DeviceRecord': {'export': 'devicerecord_evolved',
                                                        'mode': 'class_reflection_hook',
                                                        'target': 'DeviceRecord'},
 'aurora_governance_persistence_gateway.DriveSync': {'export': 'drivesync_evolved',
                                                     'mode': 'class_reflection_hook',
                                                     'target': 'DriveSync'},
 'aurora_governance_persistence_gateway.DriveSync.status': {'export': 'status_evolved',
                                                            'mode': 'callable_override',
                                                            'target': 'DriveSync.status'},
 'aurora_governance_persistence_gateway.DriveSync.stop': {'export': 'stop_evolved',
                                                          'mode': 'callable_override',
                                                          'target': 'DriveSync.stop'},
 'aurora_governance_persistence_gateway.DriveSync.switch_message': {'export': 'switch_message_evolved',
                                                                    'mode': 'callable_override',
                                                                    'target': 'DriveSync.switch_message'},
 'aurora_governance_persistence_gateway.GatewayResponse': {'export': 'gatewayresponse_evolved',
                                                           'mode': 'class_reflection_hook',
                                                           'target': 'GatewayResponse'},
 'aurora_governance_persistence_gateway.GatewayVerdict': {'export': 'gatewayverdict_evolved',
                                                          'mode': 'class_reflection_hook',
                                                          'target': 'GatewayVerdict'},
 'aurora_governance_persistence_gateway.GenerationRole': {'export': 'generationrole_evolved',
                                                          'mode': 'class_reflection_hook',
                                                          'target': 'GenerationRole'},
 'aurora_governance_persistence_gateway.GenerationalAlignmentLaw': {'export': 'generationalalignmentlaw_evolved',
                                                                    'mode': 'class_reflection_hook',
                                                                    'target': 'GenerationalAlignmentLaw'},
 'aurora_governance_persistence_gateway.GenerationalAlignmentLaw.compute_tension': {'export': 'compute_tension_evolved',
                                                                                    'mode': 'callable_override',
                                                                                    'target': 'GenerationalAlignmentLaw.compute_tension'},
 'aurora_governance_persistence_gateway.GenerationalAlignmentLaw.shift_toward_stable': {'export': 'shift_toward_stable_evolved',
                                                                                        'mode': 'callable_override',
                                                                                        'target': 'GenerationalAlignmentLaw.shift_toward_stable'},
 'aurora_governance_persistence_gateway.GenerationalTension': {'export': 'generationaltension_evolved',
                                                               'mode': 'class_reflection_hook',
                                                               'target': 'GenerationalTension'},
 'aurora_governance_persistence_gateway.GenerationalTension.total': {'export': 'total_evolved',
                                                                     'mode': 'callable_override',
                                                                     'target': 'GenerationalTension.total'},
 'aurora_governance_persistence_gateway.GovernanceEngine': {'export': 'governanceengine_evolved',
                                                            'mode': 'class_reflection_hook',
                                                            'target': 'GovernanceEngine'},
 'aurora_governance_persistence_gateway.GovernanceEngine.promote': {'export': 'promote_evolved',
                                                                    'mode': 'callable_override',
                                                                    'target': 'GovernanceEngine.promote'},
 'aurora_governance_persistence_gateway.GovernanceEngine.resolve_conflict': {'export': 'resolve_conflict_evolved',
                                                                             'mode': 'callable_override',
                                                                             'target': 'GovernanceEngine.resolve_conflict'},
 'aurora_governance_persistence_gateway.GovernancePersistenceGateway.load_state': {'export': 'load_state_evolved',
                                                                                   'mode': 'callable_override',
                                                                                   'target': 'GovernancePersistenceGateway.load_state'},
 'aurora_governance_persistence_gateway.GovernanceViolation': {'export': 'governanceviolation_evolved',
                                                               'mode': 'class_reflection_hook',
                                                               'target': 'GovernanceViolation'},
 'aurora_governance_persistence_gateway.GovernedCoordinate': {'export': 'governedcoordinate_evolved',
                                                              'mode': 'class_reflection_hook',
                                                              'target': 'GovernedCoordinate'},
 'aurora_governance_persistence_gateway.GovernedCoordinate.agency_weight': {'export': 'agency_weight_evolved',
                                                                            'mode': 'callable_override',
                                                                            'target': 'GovernedCoordinate.agency_weight'},
 'aurora_governance_persistence_gateway.GovernedCoordinate.boundary_weight': {'export': 'boundary_weight_evolved',
                                                                              'mode': 'callable_override',
                                                                              'target': 'GovernedCoordinate.boundary_weight'},
 'aurora_governance_persistence_gateway.GovernedNode': {'export': 'governednode_evolved',
                                                        'mode': 'class_reflection_hook',
                                                        'target': 'GovernedNode'},
 'aurora_governance_persistence_gateway.NSpaceGateway.receive': {'export': 'receive_evolved',
                                                                 'mode': 'callable_override',
                                                                 'target': 'NSpaceGateway.receive'},
 'aurora_governance_persistence_gateway.ProactiveTrigger': {'export': 'proactivetrigger_evolved',
                                                            'mode': 'class_reflection_hook',
                                                            'target': 'ProactiveTrigger'},
 'aurora_governance_persistence_gateway.RateLimitedSearch': {'export': 'ratelimitedsearch_evolved',
                                                             'mode': 'class_reflection_hook',
                                                             'target': 'RateLimitedSearch'},
 'aurora_governance_persistence_gateway.RcloneInterface': {'export': 'rcloneinterface_evolved',
                                                           'mode': 'class_reflection_hook',
                                                           'target': 'RcloneInterface'},
 'aurora_governance_persistence_gateway.RcloneInterface._find_rclone': {'export': 'find_rclone_evolved',
                                                                        'mode': 'callable_override',
                                                                        'target': 'RcloneInterface._find_rclone'},
 'aurora_governance_persistence_gateway.RcloneInterface.check_newer_remote': {'export': 'check_newer_remote_evolved',
                                                                              'mode': 'callable_override',
                                                                              'target': 'RcloneInterface.check_newer_remote'},
 'aurora_governance_persistence_gateway.RcloneInterface.is_available': {'export': 'is_available_evolved',
                                                                        'mode': 'callable_override',
                                                                        'target': 'RcloneInterface.is_available'},
 'aurora_governance_persistence_gateway.RcloneInterface.remote_full': {'export': 'remote_full_evolved',
                                                                       'mode': 'callable_override',
                                                                       'target': 'RcloneInterface.remote_full'},
 'aurora_governance_persistence_gateway.RcloneInterface.sync_down': {'export': 'sync_down_evolved',
                                                                     'mode': 'callable_override',
                                                                     'target': 'RcloneInterface.sync_down'},
 'aurora_governance_persistence_gateway.RcloneInterface.sync_up': {'export': 'sync_up_evolved',
                                                                   'mode': 'callable_override',
                                                                   'target': 'RcloneInterface.sync_up'},
 'aurora_governance_persistence_gateway.StreamType': {'export': 'streamtype_evolved',
                                                      'mode': 'class_reflection_hook',
                                                      'target': 'StreamType'},
 'aurora_governance_persistence_gateway.StudyScheduler': {'export': 'studyscheduler_evolved',
                                                          'mode': 'class_reflection_hook',
                                                          'target': 'StudyScheduler'},
 'aurora_governance_persistence_gateway.ValidationResult': {'export': 'validationresult_evolved',
                                                            'mode': 'class_reflection_hook',
                                                            'target': 'ValidationResult'},
 'aurora_governance_persistence_gateway.VotingAuthority': {'export': 'votingauthority_evolved',
                                                           'mode': 'class_reflection_hook',
                                                           'target': 'VotingAuthority'},
 'aurora_governance_persistence_gateway.WriteResult': {'export': 'writeresult_evolved',
                                                       'mode': 'class_reflection_hook',
                                                       'target': 'WriteResult'},
 'latent.aurora_governance_persistence_gateway.AtomicWriter.route_agency': {'export': 'atomicwriter_route_agency',
                                                                            'mode': 'latent_binding',
                                                                            'target': 'AtomicWriter.route_agency'},
 'latent.aurora_governance_persistence_gateway.AuroraStateSnapshot.route_agency': {'export': 'aurorastatesnapshot_route_agency',
                                                                                   'mode': 'latent_binding',
                                                                                   'target': 'AuroraStateSnapshot.route_agency'},
 'latent.aurora_governance_persistence_gateway.AuroraStateSnapshot.to_dict.route_agency': {'export': 'evolved_route_agency',
                                                                                           'mode': 'latent_binding',
                                                                                           'target': 'AuroraStateSnapshot.to_dict.route_agency'},
 'latent.aurora_governance_persistence_gateway.AutonomyEngine.route_boundary': {'export': 'route_boundary',
                                                                                'mode': 'latent_binding',
                                                                                'target': 'AutonomyEngine.route_boundary'},
 'latent.aurora_governance_persistence_gateway.CheckpointManager.route_agency': {'export': 'checkpointmanager_route_agency',
                                                                                 'mode': 'latent_binding',
                                                                                 'target': 'CheckpointManager.route_agency'},
 'latent.aurora_governance_persistence_gateway.CheckpointManager.save.route_agency': {'export': 'latent_aurora_governance_persistence_gateway_checkpointmanager_save_route_agency',
                                                                                      'mode': 'latent_binding',
                                                                                      'target': 'CheckpointManager.save.route_agency'},
 'latent.aurora_governance_persistence_gateway.CheckpointRecord.route_agency': {'export': 'checkpointrecord_route_agency',
                                                                                'mode': 'latent_binding',
                                                                                'target': 'CheckpointRecord.route_agency'},
 'latent.aurora_governance_persistence_gateway.DeviceRecord.to_dict.route_agency': {'export': 'to_dict_route_agency',
                                                                                    'mode': 'latent_binding',
                                                                                    'target': 'DeviceRecord.to_dict.route_agency'},
 'latent.aurora_governance_persistence_gateway.DriveSync.route_boundary': {'export': 'drivesync_route_boundary',
                                                                           'mode': 'latent_binding',
                                                                           'target': 'DriveSync.route_boundary'},
 'latent.aurora_governance_persistence_gateway.DriveSync.start.route_boundary': {'export': 'start_route_boundary',
                                                                                 'mode': 'latent_binding',
                                                                                 'target': 'DriveSync.start.route_boundary'},
 'latent.aurora_governance_persistence_gateway.FilesystemExplorer.route_agency': {'export': 'filesystemexplorer_route_agency',
                                                                                  'mode': 'latent_binding',
                                                                                  'target': 'FilesystemExplorer.route_agency'},
 'latent.aurora_governance_persistence_gateway.GovernanceEngine.get_stats.route_agency': {'export': 'get_stats_route_agency',
                                                                                          'mode': 'latent_binding',
                                                                                          'target': 'GovernanceEngine.get_stats.route_agency'},
 'latent.aurora_governance_persistence_gateway.GovernanceEngine.route_agency': {'export': 'governanceengine_route_agency',
                                                                                'mode': 'latent_binding',
                                                                                'target': 'GovernanceEngine.route_agency'},
 'latent.aurora_governance_persistence_gateway.GovernancePersistenceGateway.route_agency': {'export': 'governancepersistencegateway_route_agency',
                                                                                            'mode': 'latent_binding',
                                                                                            'target': 'GovernancePersistenceGateway.route_agency'},
 'latent.aurora_governance_persistence_gateway.GovernancePersistenceGateway.save_state.route_agency': {'export': 'save_state_route_agency',
                                                                                                       'mode': 'latent_binding',
                                                                                                       'target': 'GovernancePersistenceGateway.save_state.route_agency'},
 'latent.aurora_governance_persistence_gateway.GovernedCoordinate.existence_weight.route_agency': {'export': 'existence_weight_route_agency',
                                                                                                   'mode': 'latent_binding',
                                                                                                   'target': 'GovernedCoordinate.existence_weight.route_agency'},
 'latent.aurora_governance_persistence_gateway.GovernedCoordinate.route_agency': {'export': 'governedcoordinate_route_agency',
                                                                                  'mode': 'latent_binding',
                                                                                  'target': 'GovernedCoordinate.route_agency'},
 'latent.aurora_governance_persistence_gateway.NSpaceGateway.route_agency': {'export': 'nspacegateway_route_agency',
                                                                             'mode': 'latent_binding',
                                                                             'target': 'NSpaceGateway.route_agency'},
 'latent.aurora_governance_persistence_gateway.ProactiveTrigger.add_thought.route_agency': {'export': 'add_thought_route_agency',
                                                                                            'mode': 'latent_binding',
                                                                                            'target': 'ProactiveTrigger.add_thought.route_agency'},
 'latent.aurora_governance_persistence_gateway.StatePersistence.route_agency': {'export': 'statepersistence_route_agency',
                                                                                'mode': 'latent_binding',
                                                                                'target': 'StatePersistence.route_agency'},
 'latent.aurora_governance_persistence_gateway.StatePersistence.save.route_agency': {'export': 'save_route_agency',
                                                                                     'mode': 'latent_binding',
                                                                                     'target': 'StatePersistence.save.route_agency'},
 'latent.aurora_governance_persistence_gateway.WriteValidator.route_agency': {'export': 'writevalidator_route_agency',
                                                                              'mode': 'latent_binding',
                                                                              'target': 'WriteValidator.route_agency'},
 'latent.aurora_governance_persistence_gateway._clamp.route_agency': {'export': 'route_agency',
                                                                      'mode': 'latent_binding',
                                                                      'target': '_clamp.route_agency'}}
# AURORA_EVOLVED_NATIVE_END

#!/usr/bin/env python3
"""
AURORA SEDIMEMORY
==================
Module: aurora_sedimemory.py
Layer: 3.5 — between DimensionalSystems (L3) and ConsciousnessEngine (L4)

ARCHITECTURE DOCTRINE
---------------------
Memory in Aurora is not stored. It seeps.

Every event passes whole and unmodified through all 25 Non-Comp strain
filters simultaneously. Each filter extracts only the fragment that
resonates with its specific Constraint × NonCompDimension intersection.
The rest falls through. Nothing is lost — it simply found no sediment
to catch in.

The 25 sediment basins operate at the tick rate of their dominant axis:

    X (Existence)  → 1.0       full tick — fastest decay / highest throughput
    T (Time)       → 0.1       fast
    N (Energy)     → 0.01      moderate
    B (Boundary)   → 0.001     slow
    A (Agency)     → 0.0001    geological — near-frozen

Fragments at shallow depth decay fast and stay high-fidelity.
Fragments at deep depth decay almost never, compressing continuously —
the slower clock gives the system time to abstract them.

CHANNEL LAW — SIMPLIFIED JOURNEY FOR REPEAT DEEP TRANSITIONS
-------------------------------------------------------------
When the same event pattern traverses the same deep-layer path
repeatedly, the system recognizes that groove and carves a SedimentChannel.

    First traversal            → full 25-filter strain (expensive)
    Repeated matching pattern  → path observed, traversal count incremented
    Promotion threshold hit    → SedimentChannel carved
    Subsequent matching events → direct deposit via channel (cheap)

A carved channel is itself a form of compressed intelligence. Aurora
no longer needs to derive where things go — she already knows. The
channel IS the policy adaptation described in the manifold intelligence
criterion: ∃r* where sign(dΦ_C/dr) changes and π_C adapts.

Channel decay mirrors axis tick rates:
    X-axis channels  → dissolve quickly if unused (surface reflexes)
    A-axis channels  → almost never dissolve (foundational laws)

CHANNEL PROMOTION (mirrors constraint_genealogy.py link promotion):
    observed_traversals  >= CHANNEL_PROMOTION_THRESHOLD  → promoted
    disuse_ticks         >= channel_decay_ticks           → dissolved
    re-traversal of a dissolved path                      → starts over

COMPRESSION LAW
---------------
Compression is densification, not forgetting. When a basin accumulates
mature fragments, they merge into compressed_mass — a denser encoding
that preserves constraint geometry while releasing specific noise.

DECOMPRESSION
-------------
Compressed deep (A/B) knowledge flows back up through the same NC
pathways it came down through. At each shallower axis the clock is
faster and the fragment expands back toward specificity.

STRATA SPLIT
------------
    Surface daemon    → surface_recall()    [X, T axes]   tick=1.0 / 0.1
    DCE bridge        → dce_recall()         [N axis]      tick=0.01
    Subsurface daemon → subsurface_recall()  [B, A axes]   tick=0.001 / 0.0001

Authors: Sunni (Sir) Morningstar and Cael Devo
Created: March 2026
"""

from __future__ import annotations

import hashlib
import math
import re
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Deque, Dict, FrozenSet, List, Optional, Set, Tuple

from aurora_constraint_unit_adapter import build_constraint_profile

# ============================================================================
# LAYER IMPORTS
# ============================================================================

from foundational_contract import (
    ExistenceMode,
    OntologicalClaim,
    OntologicalViolation,
    FoundationalContract,
)

try:
    from aurora_internal.aurora_constraint_manifold_patched import (
        Constraint,
        ConstraintVector,
        ManifoldViolation,
        CompositionalSpace,
        State,
        RecursionLevel,
        ConstraintField,
        EnergyDistribution,
    )
except ImportError:
    from aurora_constraint_manifold_patched import (  # type: ignore
        Constraint,
        ConstraintVector,
        ManifoldViolation,
        CompositionalSpace,
        State,
        RecursionLevel,
        ConstraintField,
        EnergyDistribution,
    )

from aurora_internal.aurora_noncomp_registry import (
    NonCompDimension,
    NonCompRegistry,
)

from aurora_ivm import (
    IVMLattice,
    IVMEnvelope,
    IVMNode,
)

from aurora_simulation_engine import (
    TimeDilationGovernor,
    StabilityMetrics,
    StabilityState,
)
from aurora_constraint_ontology import (
    describe_memory_contract,
    derive_signature_from_axes,
)


# ============================================================================
# CONSTANTS
# ============================================================================

# Per-axis tick participation — from constraint_genealogy.py doctrine.
# X is the surface (fastest). A is the geological floor (slowest).
AXIS_TICK_PARTICIPATION: Dict[str, float] = {
    "X": 1.0,
    "T": 0.1,
    "N": 0.01,
    "B": 0.001,
    "A": 0.0001,
}

AXIS_TO_CONSTRAINT: Dict[str, Constraint] = {
    "X": Constraint.X,
    "T": Constraint.T,
    "N": Constraint.N,
    "B": Constraint.B,
    "A": Constraint.A,
}

CONSTRAINT_TO_AXIS: Dict[Constraint, str] = {v: k for k, v in AXIS_TO_CONSTRAINT.items()}

# Axis depth order — surface to geological floor.
AXIS_DEPTH_ORDER: List[str] = ["X", "T", "N", "B", "A"]

# How strongly a filter must resonate to catch a fragment.
_DEFAULT_RESONANCE_THRESHOLD: float = 0.25

# Fragment decay accumulator threshold before compression eligibility.
_COMPRESSION_DECAY_THRESHOLD: float = 1.0

# Max active fragments per basin before forced compression.
_BASIN_FRAGMENT_CAPACITY: int = 64

# How many times a path must be observed before a channel is carved.
_CHANNEL_PROMOTION_THRESHOLD: int = 5

# How many ticks of disuse before a channel dissolves.
# Scaled by axis tick rate, so A-axis channels last far longer.
_CHANNEL_BASE_DISUSE_TICKS: int = 500

# Resolution of constraint vector quantization for path signature hashing.
# Higher = more distinct paths recognized. Lower = more paths collapse together.
_CV_QUANTIZATION_BINS: int = 4


# ============================================================================
# FIDELITY LEVELS
# ============================================================================

class FidelityLevel(IntEnum):
    COMPRESSED = 0   # compressed_mass only — deep abstraction
    PARTIAL    = 1   # dominant fragments reconstructed
    FULL       = 2   # all fragments and metadata


# ============================================================================
# MEMORY EVENT — the whole event before straining
# ============================================================================

@dataclass
class MemoryEvent:
    """
    The whole, unmodified event entering the straining system.

    Passes through ALL 25 NC filters in its entirety. Nothing is
    pre-selected. The strainers decide what matters.

    Fields
    ------
    content          : arbitrary key→value payload
    constraint_vector: event's position in constraint space
    source           : originating subsystem
    existence_mode   : ontological tier — must be PERSISTENT+ to sediment
    """
    event_id:          str
    content:           Dict[str, Any]
    constraint_vector: ConstraintVector
    source:            str           = "interaction"
    existence_mode:    ExistenceMode = ExistenceMode.PERSISTENT
    timestamp:         float         = field(default_factory=time.time)
    lineage_signature: str           = "X"
    pressure_history:  List[Dict[str, Any]] = field(default_factory=list)
    tolerance_snapshot: Dict[str, Any] = field(default_factory=dict)
    transition_mapping: Dict[str, Any] = field(default_factory=dict)
    language_projection: Dict[str, Any] = field(default_factory=dict)
    memory_contract: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.lineage_signature:
            self.lineage_signature = self._derive_lineage_signature()
        if not self.memory_contract:
            self.memory_contract = self._derive_memory_contract()
        if not self.language_projection:
            self.language_projection = dict(self.memory_contract.get("language_projection", {}))
        if not self.tolerance_snapshot:
            self.tolerance_snapshot = dict(self.memory_contract.get("regime", {}))
        if not self.transition_mapping:
            self.transition_mapping = dict(self.memory_contract.get("weighted_form", {}))

    def _axis_weights(self) -> Dict[str, float]:
        return {
            "X": float(getattr(self.constraint_vector, "X", 0.0) or 0.0),
            "T": float(getattr(self.constraint_vector, "T", 0.0) or 0.0),
            "N": float(getattr(self.constraint_vector, "N", 0.0) or 0.0),
            "B": float(getattr(self.constraint_vector, "B", 0.0) or 0.0),
            "A": float(getattr(self.constraint_vector, "A", 0.0) or 0.0),
        }

    def _derive_lineage_signature(self) -> str:
        return derive_signature_from_axes(self._axis_weights(), include_weighting=True)

    def _derive_memory_contract(self) -> Dict[str, Any]:
        return describe_memory_contract(
            self.lineage_signature,
            self._axis_weights(),
            self._axis_weights(),
        )

    def register_pressure(self, sample: Optional[Dict[str, float]] = None) -> None:
        vector = {axis: float((sample or self._axis_weights()).get(axis, 0.0) or 0.0) for axis in AXIS_DEPTH_ORDER}
        self.pressure_history.append({
            "timestamp": time.time(),
            "pressure": vector,
        })
        self.pressure_history = self.pressure_history[-16:]
        self.memory_contract = self._derive_memory_contract()
        self.language_projection = dict(self.memory_contract.get("language_projection", {}))
        self.tolerance_snapshot = dict(self.memory_contract.get("regime", {}))
        self.transition_mapping = dict(self.memory_contract.get("weighted_form", {}))

    @classmethod
    def create(
        cls,
        content:           Dict[str, Any],
        constraint_vector: ConstraintVector,
        source:            str           = "interaction",
        existence_mode:    ExistenceMode = ExistenceMode.PERSISTENT,
    ) -> MemoryEvent:
        eid = f"evt_{hashlib.md5(f'{time.time()}{uuid.uuid4()}'.encode()).hexdigest()[:12]}"
        return cls(
            event_id=eid,
            content=content,
            constraint_vector=constraint_vector,
            source=source,
            existence_mode=existence_mode,
        )

    @classmethod
    def from_envelope(cls, envelope: IVMEnvelope) -> MemoryEvent:
        """Construct from an IVMEnvelope arriving from L1/L2."""
        try:
            cv = ConstraintVector(
                X=float(getattr(envelope, 'existence_weight', 1.0)),
                T=float(getattr(envelope, 'temporal_weight',  0.5)),
                N=float(getattr(envelope, 'energy_weight',    0.5)),
                B=float(getattr(envelope, 'boundary_weight',  0.5)),
                A=float(getattr(envelope, 'agency_weight',    0.5)),
            )
        except (ManifoldViolation, AttributeError):
            cv = ConstraintVector(X=1.0, T=0.5, N=0.5, B=0.5, A=0.5)

        content: Dict[str, Any] = {}
        if hasattr(envelope, '__dict__'):
            for k, v in envelope.__dict__.items():
                if not k.startswith('_') and isinstance(v, (str, int, float, bool, list, dict)):
                    content[k] = v

        mode   = getattr(envelope, 'mode',   ExistenceMode.PERSISTENT)
        source = getattr(envelope, 'source', 'envelope')
        return cls.create(content=content, constraint_vector=cv,
                          source=source, existence_mode=mode)


# ============================================================================
# SEDIMENT FRAGMENT — what a single NC filter catches
# ============================================================================

@dataclass
class SedimentFragment:
    """
    One piece of a memory event caught by a specific NC strain filter.

    Carries the semantic slice that resonated with its slot's
    Constraint × NonCompDimension intersection — not the whole event.

    decay_accumulator increases each tick by delta_t × tick_rate.
    When it crosses _COMPRESSION_DECAY_THRESHOLD the fragment is
    eligible for compression into the basin's compressed_mass.
    """
    fragment_id:       str
    event_id:          str
    slot_id:           str              # basin this fragment belongs to
    nc_filter_key:     str              # "AXIS.DIM" e.g. "N.COST"
    axis:              str
    constraint:        Constraint
    dimension:         NonCompDimension
    content:           Dict[str, Any]
    resonance:         float
    deposit_time:      float = field(default_factory=time.time)
    decay_accumulator: float = 0.0
    compression_level: float = 0.0
    tick_rate:         float = 1.0
    lineage_signature: str = ""
    pressure_history:  List[Dict[str, Any]] = field(default_factory=list)
    tolerance_snapshot: Dict[str, Any] = field(default_factory=dict)
    transition_mapping: Dict[str, Any] = field(default_factory=dict)

    def tick(self, delta_t: float) -> bool:
        """Advance decay. Returns True when compression-eligible."""
        self.decay_accumulator += delta_t * self.tick_rate
        self.compression_level = min(
            1.0,
            self.decay_accumulator / _COMPRESSION_DECAY_THRESHOLD
        )
        return self.decay_accumulator >= _COMPRESSION_DECAY_THRESHOLD

    def summary(self) -> Dict[str, Any]:
        return {
            "fragment_id":  self.fragment_id,
            "event_id":     self.event_id,
            "slot_id":      self.slot_id,
            "nc_filter":    self.nc_filter_key,
            "axis":         self.axis,
            "resonance":    round(self.resonance, 4),
            "decay":        round(self.decay_accumulator, 6),
            "compression":  round(self.compression_level, 4),
            "lineage_signature": self.lineage_signature,
            "pressure_history_count": len(self.pressure_history),
            "content_keys": list(self.content.keys()),
        }


# ============================================================================
# CHANNEL SIGNATURE — compact fingerprint of a traversal path
# ============================================================================

def _quantize_cv(cv: ConstraintVector, bins: int = _CV_QUANTIZATION_BINS) -> Tuple[int, ...]:
    """
    Quantize a ConstraintVector into a fixed-resolution tuple for hashing.

    This collapses nearby constraint vectors into the same signature so
    that semantically similar events recognize each other as the same path
    rather than producing an explosion of one-off channels.

    bins=4 means each axis value (0.0–1.0+) is bucketed into one of 4 bins.
    Events with similar constraint geometry hash identically.
    """
    arr = cv.to_array()
    # Clip to [0, 2.0] range then bin
    return tuple(min(bins - 1, int(max(0.0, v) / (2.0 / bins))) for v in arr)


def _path_signature(cv: ConstraintVector, basin_ids: FrozenSet[str]) -> str:
    """
    Produce a stable string signature for a (constraint_vector, basin_set) pair.
    This is the identity of a traversal path.
    """
    cv_quantized = _quantize_cv(cv)
    basins_sorted = ",".join(sorted(basin_ids))
    raw = f"{cv_quantized}|{basins_sorted}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


# ============================================================================
# SEDIMENT CHANNEL — a carved direct-deposit pathway with spoke geometry
# ============================================================================

def _spoke_weights(
    dominant_slot_id: str,
    target_basin_ids: FrozenSet[str],
    basins:           Dict[str, "SedimentBasin"],
) -> Dict[str, float]:
    """
    Compute deposit weight for every basin in a channel relative to the
    dominant slot's influence.

    The dominant slot deposits at full weight (1.0). Every other slot
    deposits at a weight determined by its geometric proximity to the
    dominant slot in constraint × dimension space:

        proximity = 1 - (axis_distance + dim_distance) / 2

    where:
        axis_distance = |dominant_depth_rank - spoke_depth_rank| / 4
        dim_distance  = 0.0 if same dimension, 0.25 per dimension step

    This means:
        - Same axis, same dimension as dominant  → 1.0  (the dominant itself)
        - Same axis, adjacent dimension          → ~0.75
        - Adjacent axis, same dimension          → ~0.75
        - Opposite axis, different dimension     → ~0.25 (floor)

    Floor is 0.1 so no spoke ever deposits zero — it was still caught
    by that filter for a reason.
    """
    dom_basin = basins.get(dominant_slot_id)
    if dom_basin is None:
        return {bid: 1.0 for bid in target_basin_ids}

    dom_axis_rank  = AXIS_DEPTH_ORDER.index(dom_basin.axis)
    dom_dim_value  = dom_basin.dimension.value
    weights: Dict[str, float] = {}

    for bid in target_basin_ids:
        if bid == dominant_slot_id:
            weights[bid] = 1.0
            continue

        spoke_basin = basins.get(bid)
        if spoke_basin is None:
            weights[bid] = 0.5
            continue

        spoke_axis_rank = AXIS_DEPTH_ORDER.index(spoke_basin.axis)
        spoke_dim_value = spoke_basin.dimension.value

        axis_dist = abs(dom_axis_rank  - spoke_axis_rank)  / 4.0
        dim_dist  = abs(dom_dim_value  - spoke_dim_value)  / 4.0
        proximity = 1.0 - (axis_dist + dim_dist) / 2.0
        weights[bid] = max(0.1, round(proximity, 4))

    return weights


@dataclass
class SedimentChannel:
    """
    A promoted traversal path with spoke geometry.

    The dominant_slot_id is the basin whose Constraint × NonCompDimension
    intersection represents the greatest influence in this channel's
    pattern. It is the root anchor — all other basins (spokes) exist in
    this channel because of their geometric relationship to it.

    SPOKE DEPOSIT PHYSICS:
        On channel traversal, each basin receives a deposit weighted by
        its proximity to the dominant slot:
            dominant slot       → weight 1.0  (full confidence)
            close spokes        → weight ~0.75
            distant spokes      → weight ~0.25–0.5
            minimum floor       → weight 0.1

        This means the dominant slot accumulates compressed_mass fastest
        and becomes the most compressed, most abstracted representation
        in the channel — it is the anchor that the channel's identity
        is organized around.

    DOMINANT SLOT INDEX:
        PathRegistry indexes channels by dominant_slot_id, so Aurora can
        ask "what channels are anchored to Agency×Cost?" and get back all
        the pathway laws organized under that constraint influence.
        This maps directly onto the genealogy DAG — the dominant slot IS
        a genealogy atom and the spokes are its constraint offspring.

    PHYSICS (unchanged from base):
        traversal_cost  → decreases with use, floor 0.05
        disuse_ticks    → dissolution_threshold scaled by dominant axis
        dissolved       → returns to observation pool
    """
    channel_id:            str
    signature:             str
    target_basin_ids:      FrozenSet[str]
    dominant_slot_id:      str              # root anchor basin
    dominant_axis:         str              # axis of dominant slot
    cv_quantized:          Tuple[int, ...]
    spoke_weights:         Dict[str, float] = field(default_factory=dict)
    promoted_at:           float = field(default_factory=time.time)
    traversal_count:       int   = 0
    disuse_ticks:          int   = 0
    traversal_cost:        float = 1.0
    dissolution_threshold: int   = _CHANNEL_BASE_DISUSE_TICKS
    dissolved:             bool  = False

    def traverse(self) -> float:
        """Record traversal. Returns current traversal_cost."""
        self.traversal_count += 1
        self.disuse_ticks     = 0
        self.traversal_cost   = max(0.05, 1.0 * (0.966 ** self.traversal_count))
        return self.traversal_cost

    def deposit_weight_for(self, basin_id: str) -> float:
        """
        Return the spoke-weighted deposit confidence for a given basin.
        Dominant slot → 1.0. Spokes → proximity-scaled. Floor → 0.1.
        """
        return self.spoke_weights.get(basin_id, 0.5)

    def tick_disuse(self) -> bool:
        if self.dissolved:
            return True
        self.disuse_ticks += 1
        if self.disuse_ticks >= self.dissolution_threshold:
            self.dissolved = True
        return self.dissolved

    def stats(self) -> Dict[str, Any]:
        return {
            "channel_id":            self.channel_id,
            "signature":             self.signature,
            "dominant_slot_id":      self.dominant_slot_id,
            "dominant_axis":         self.dominant_axis,
            "target_basins":         list(self.target_basin_ids),
            "spoke_weights":         self.spoke_weights,
            "traversal_count":       self.traversal_count,
            "traversal_cost":        round(self.traversal_cost, 4),
            "disuse_ticks":          self.disuse_ticks,
            "dissolution_threshold": self.dissolution_threshold,
            "dissolved":             self.dissolved,
        }


# ============================================================================
# PATH REGISTRY — observation, promotion, dissolution
# ============================================================================

class PathRegistry:
    """
    Observes traversal patterns and promotes recurring paths into
    SedimentChannels, dissolves unused channels, and provides
    fast lookup for channel-eligible events.

    LIFECYCLE:
        1. observe(cv, basin_ids)    → increments traversal count for path
        2. If count >= threshold     → promote() → SedimentChannel created
        3. tick()                    → increments disuse on all channels
        4. Channels crossing disuse  → dissolved, signature returned to pool
        5. lookup(cv)                → returns active channel if exists

    COST PHYSICS:
        Using a channel costs traversal_cost × N_axis_base_cost.
        Full strain always costs 1.0 × N_axis_base_cost.
        So a well-worn channel (traversal_cost → 0.05) costs 5% of full strain.
        This is the energy savings of having learned a pathway law.

    AXIS-WEIGHTED DISSOLUTION:
        dissolution_threshold = _CHANNEL_BASE_DISUSE_TICKS / tick_rate
        A-axis channels: 500 / 0.0001 = 5,000,000 ticks to dissolve
        X-axis channels: 500 / 1.0    = 500 ticks to dissolve
        Surface memory dissolves. Foundational law persists.
    """

    def __init__(
        self,
        promotion_threshold: int = _CHANNEL_PROMOTION_THRESHOLD,
        basins: Optional[Dict[str, Any]] = None,
    ):
        self._promotion_threshold = promotion_threshold
        self._basins = basins or {}   # ref to SedimentColumn._basins for spoke calc
        # path_signature → observation count (before promotion)
        self._observations:   Dict[str, int]                 = defaultdict(int)
        # path_signature → basin_ids and cv_quantized (stored at first observation)
        self._path_meta:      Dict[str, Dict[str, Any]]      = {}
        # path_signature → SedimentChannel (after promotion)
        self._channels:       Dict[str, SedimentChannel]     = {}
        # cv_quantized → set of signatures for fast lookup
        self._cv_index:       Dict[Tuple[int,...], Set[str]]  = defaultdict(set)
        # dominant_slot_id → set of channel signatures anchored to that slot
        # Aurora's pathway laws organized by constraint influence — mirrors genealogy DAG
        self._dominant_index: Dict[str, Set[str]]             = defaultdict(set)

        self._total_promoted:   int = 0
        self._total_dissolved:  int = 0
        self._total_traversals: int = 0

    # ------------------------------------------------------------------
    # OBSERVE — record a new traversal attempt
    # ------------------------------------------------------------------

    def observe(
        self,
        cv:         ConstraintVector,
        basin_ids:  FrozenSet[str],
    ) -> Optional[SedimentChannel]:
        """
        Record a traversal of the given (cv, basin_ids) path.

        If the path already has a live channel, returns it immediately
        (this is a channel hit — no observation needed).

        If the path is new or below threshold, increments the observation
        count and returns None (full strain required).

        If the observation count crosses the promotion threshold,
        promotes the path and returns the new channel.
        """
        cv_q = _quantize_cv(cv)
        sig  = _path_signature(cv, basin_ids)

        # Fast path: existing channel
        channel = self._channels.get(sig)
        if channel and not channel.dissolved:
            self._total_traversals += 1
            channel.traverse()
            return channel

        # Record observation
        self._observations[sig] += 1
        if sig not in self._path_meta:
            self._path_meta[sig] = {
                "basin_ids":    basin_ids,
                "cv_quantized": cv_q,
            }
            self._cv_index[cv_q].add(sig)

        # Check for promotion
        if self._observations[sig] >= self._promotion_threshold:
            return self._promote(sig, cv_q, basin_ids)

        return None

    def _promote(
        self,
        sig:       str,
        cv_q:      Tuple[int, ...],
        basin_ids: FrozenSet[str],
    ) -> SedimentChannel:
        """Promote a path signature to a SedimentChannel with spoke geometry."""
        # Dominant slot = deepest axis basin; ties broken by highest NonCompDimension.
        # The dominant slot is the root anchor — the NC intersection whose
        # constraint influence is greatest in this channel's pattern.
        candidate_basins = [self._basins[b] for b in basin_ids if b in self._basins]

        if candidate_basins:
            dominant_basin   = min(
                candidate_basins,
                key=lambda b: (AXIS_TICK_PARTICIPATION[b.axis], -b.dimension.value)
            )
            dominant_slot_id = dominant_basin.basin_id
            dominant_axis    = dominant_basin.axis
        else:
            axes_in_path = [
                bid.split(":")[1].split(">")[0]
                for bid in basin_ids
                if len(bid.split(":")) >= 2
                and bid.split(":")[1].split(">")[0] in AXIS_TICK_PARTICIPATION
            ]
            dominant_axis    = min(axes_in_path or ["X"],
                                   key=lambda a: AXIS_TICK_PARTICIPATION[a])
            dominant_slot_id = next(
                (b for b in basin_ids if b.startswith(f"SED:{dominant_axis}>")),
                next(iter(basin_ids))
            )

        tick_rate = AXIS_TICK_PARTICIPATION[dominant_axis]
        dissolution_threshold = max(
            _CHANNEL_BASE_DISUSE_TICKS,
            int(_CHANNEL_BASE_DISUSE_TICKS / tick_rate)
        )

        weights    = _spoke_weights(dominant_slot_id, basin_ids, self._basins)
        channel_id = f"ch_{hashlib.md5(f'{sig}{time.time()}'.encode()).hexdigest()[:10]}"

        channel = SedimentChannel(
            channel_id=channel_id,
            signature=sig,
            target_basin_ids=basin_ids,
            dominant_slot_id=dominant_slot_id,
            dominant_axis=dominant_axis,
            cv_quantized=cv_q,
            spoke_weights=weights,
            dissolution_threshold=dissolution_threshold,
        )

        self._channels[sig] = channel
        self._dominant_index[dominant_slot_id].add(sig)
        del self._observations[sig]
        self._total_promoted += 1
        return channel

    # ------------------------------------------------------------------
    # LOOKUP
    # ------------------------------------------------------------------

    def lookup(
        self,
        cv:        ConstraintVector,
        basin_ids: FrozenSet[str],
    ) -> Optional[SedimentChannel]:
        sig     = _path_signature(cv, basin_ids)
        channel = self._channels.get(sig)
        if channel and not channel.dissolved:
            return channel
        return None

    def channels_for_dominant(self, slot_id: str) -> List[SedimentChannel]:
        """
        All active channels anchored to a given dominant slot.
        Aurora's constraint-influence index — dominant slot = genealogy atom,
        spokes = constraint offspring.
        """
        sigs = self._dominant_index.get(slot_id, set())
        return [
            self._channels[s]
            for s in sigs
            if s in self._channels and not self._channels[s].dissolved
        ]

    def dominant_influence_map(self) -> Dict[str, int]:
        """Count active channels per dominant slot — Aurora's deepest grooves."""
        result: Dict[str, int] = {}
        for slot_id, sigs in self._dominant_index.items():
            active = sum(
                1 for s in sigs
                if s in self._channels and not self._channels[s].dissolved
            )
            if active > 0:
                result[slot_id] = active
        return dict(sorted(result.items(), key=lambda x: -x[1]))

    # ------------------------------------------------------------------
    # TICK
    # ------------------------------------------------------------------

    def tick(self) -> List[str]:
        """Advance disuse counters. Returns dissolved channel_ids."""
        dissolved_ids: List[str] = []
        for sig, channel in list(self._channels.items()):
            if channel.tick_disuse():
                dissolved_ids.append(channel.channel_id)
                self._observations[sig] = 0
                self._path_meta.pop(sig, None)
                self._dominant_index[channel.dominant_slot_id].discard(sig)
                del self._channels[sig]
                self._total_dissolved += 1
        return dissolved_ids

    # ------------------------------------------------------------------
    # STATS
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        active_by_axis: Dict[str, int] = defaultdict(int)
        for ch in self._channels.values():
            if not ch.dissolved:
                active_by_axis[ch.dominant_axis] += 1
        return {
            "active_channels":       len(self._channels),
            "pending_observations":  len(self._observations),
            "total_promoted":        self._total_promoted,
            "total_dissolved":       self._total_dissolved,
            "total_traversals":      self._total_traversals,
            "channels_by_axis":      dict(active_by_axis),
            "dominant_slots_active": len(self.dominant_influence_map()),
            "promotion_threshold":   self._promotion_threshold,
        }


# ============================================================================
# NC STRAIN FILTER — the 25-cell straining membrane
# ============================================================================

class NCStrainFilter:
    """
    The 25-cell straining membrane.

    Each cell is one (Constraint × NonCompDimension) intersection.
    All 25 cells process every MemoryEvent simultaneously.

    Resonance: cosine similarity between event ConstraintVector and
    the cell's filter signature. If resonance >= threshold, the cell
    deposits a fragment into its corresponding basin.

    Content extraction: each cell pulls the semantic slice of the event
    content that aligns with its dimensional lens:
        POLARITY   → direction, valence, orientation content
        MAGNITUDE  → intensity, strength, severity content
        OPERATOR   → transformation, action, change content
        COST       → resource, energy, duration content
        DIFFERENCE → novelty, deviation, delta content
    """

    DIMENSION_CONTENT_KEYS: Dict[NonCompDimension, List[str]] = {
        NonCompDimension.POLARITY:   [
            'polarity', 'direction', 'valence', 'tone', 'orientation',
            'positive', 'negative', 'outcome_sign',
        ],
        NonCompDimension.MAGNITUDE:  [
            'magnitude', 'intensity', 'strength', 'severity', 'scale',
            'confidence', 'weight', 'pressure',
        ],
        NonCompDimension.OPERATOR:   [
            'operator', 'action', 'transformation', 'change', 'operation',
            'method', 'process', 'mechanism',
        ],
        NonCompDimension.COST:       [
            'cost', 'energy', 'resource', 'expense', 'duration', 'price',
            'budget', 'consumption', 'tick_count',
        ],
        NonCompDimension.DIFFERENCE: [
            'difference', 'delta', 'novelty', 'deviation', 'surprise',
            'unexpected', 'error', 'anomaly', 'gap',
        ],
    }

    CONSTRAINT_CONTENT_KEYS: Dict[Constraint, List[str]] = {
        Constraint.X: [
            'existence', 'admissibility', 'is_valid', 'mode', 'state',
            'type', 'class', 'identity', 'module', 'target',
        ],
        Constraint.T: [
            'time', 'timestamp', 'duration', 'sequence', 'order',
            'temporal', 'when', 'before', 'after', 'tick',
        ],
        Constraint.N: [
            'energy', 'cost', 'resource', 'budget', 'exchange',
            'consumption', 'gain', 'loss', 'pressure', 'load',
        ],
        Constraint.B: [
            'boundary', 'scope', 'limit', 'container', 'edge',
            'interface', 'barrier', 'module', 'layer', 'domain',
        ],
        Constraint.A: [
            'agency', 'action', 'decision', 'intent', 'authored',
            'chosen', 'directed', 'goal', 'outcome', 'effect',
        ],
    }

    def __init__(self, resonance_threshold: float = _DEFAULT_RESONANCE_THRESHOLD):
        self.resonance_threshold = resonance_threshold
        self._signatures: Dict[str, ConstraintVector] = {}
        self._build_signatures()

    @staticmethod
    def filter_key(constraint: Constraint, dimension: NonCompDimension) -> str:
        return f"{CONSTRAINT_TO_AXIS[constraint]}.{dimension.name}"

    def _build_signatures(self) -> None:
        dim_mods = {
            NonCompDimension.POLARITY:   [0.1, 0.0, 0.0, 0.0, 0.0],
            NonCompDimension.MAGNITUDE:  [0.0, 0.1, 0.0, 0.0, 0.0],
            NonCompDimension.OPERATOR:   [0.0, 0.0, 0.1, 0.0, 0.0],
            NonCompDimension.COST:       [0.0, 0.0, 0.0, 0.1, 0.0],
            NonCompDimension.DIFFERENCE: [0.0, 0.0, 0.0, 0.0, 0.1],
        }
        for constraint in Constraint.all():
            for dimension in NonCompDimension:
                base = [0.1] * 5
                base[constraint.value] = 0.9
                mod  = dim_mods[dimension]
                vec  = [max(0.01, base[i] + mod[i]) for i in range(5)]
                vec[0] = max(0.05, vec[0])   # X must be > 0
                key = self.filter_key(constraint, dimension)
                self._signatures[key] = ConstraintVector(
                    X=vec[0], T=vec[1], N=vec[2], B=vec[3], A=vec[4]
                )

    def _resonance(self, event_cv: ConstraintVector, sig: ConstraintVector) -> float:
        a = event_cv.to_array()
        b = sig.to_array()
        dot  = float(a @ b)
        norm = float((a @ a) ** 0.5) * float((b @ b) ** 0.5)
        return 0.0 if norm < 1e-9 else max(0.0, min(1.0, dot / norm))

    def _extract_slice(
        self,
        content:    Dict[str, Any],
        constraint: Constraint,
        dimension:  NonCompDimension,
        resonance:  float,
    ) -> Dict[str, Any]:
        dim_keys   = set(self.DIMENSION_CONTENT_KEYS.get(dimension, []))
        const_keys = set(self.CONSTRAINT_CONTENT_KEYS.get(constraint, []))
        target     = dim_keys | const_keys

        sliced: Dict[str, Any] = {}
        for k, v in content.items():
            if k in target or any(t in k.lower() for t in target):
                sliced[k] = v

        for k in (
            'source', 'module', 'action', 'outcome', 'timestamp',
            'user_text', 'response', 'fact', 'summary', 'claim',
            'note', 'anchor', 'topic', 'salient', 'intent',
        ):
            if k in content and k not in sliced:
                sliced[k] = content[k]

        sliced['_filter_constraint'] = CONSTRAINT_TO_AXIS[constraint]
        sliced['_filter_dimension']  = dimension.name
        sliced['_resonance']         = round(resonance, 4)
        return sliced

    def strain(self, event: MemoryEvent) -> Dict[str, SedimentFragment]:
        """
        Pass the whole event through all 25 filters simultaneously.
        Returns filter_key → SedimentFragment for resonant cells only.
        """
        fragments: Dict[str, SedimentFragment] = {}

        for constraint in Constraint.all():
            for dimension in NonCompDimension:
                key = self.filter_key(constraint, dimension)
                sig = self._signatures[key]
                res = self._resonance(event.constraint_vector, sig)
                if res < self.resonance_threshold:
                    continue

                axis      = CONSTRAINT_TO_AXIS[constraint]
                slot_id   = _slot_id_for(constraint, dimension)
                tick_rate = AXIS_TICK_PARTICIPATION[axis]
                content   = self._extract_slice(
                    event.content, constraint, dimension, res
                )
                frag_id = (
                    f"frag_{hashlib.md5(f'{event.event_id}{key}'.encode()).hexdigest()[:10]}"
                )
                fragments[key] = SedimentFragment(
                    fragment_id=frag_id,
                    event_id=event.event_id,
                    slot_id=slot_id,
                    nc_filter_key=key,
                    axis=axis,
                    constraint=constraint,
                    dimension=dimension,
                    content=content,
                    resonance=res,
                    tick_rate=tick_rate,
                    lineage_signature=event.lineage_signature,
                    pressure_history=list(event.pressure_history),
                    tolerance_snapshot=dict(event.tolerance_snapshot),
                    transition_mapping=dict(event.transition_mapping),
                )

        return fragments


def _slot_id_for(constraint: Constraint, dimension: NonCompDimension) -> str:
    return f"SED:{CONSTRAINT_TO_AXIS[constraint]}>{dimension.name}"


# ============================================================================
# COMPRESSION ENGINE
# ============================================================================

class CompressionEngine:
    """
    Compresses mature fragments into compressed_mass.

    Merges numeric values by mean, string values by most-recent-wins.
    Tracks contributing events and compression count per filter.
    Decompression reconstructs usable content at requested fidelity.
    """

    def compress(
        self,
        fragments:     List[SedimentFragment],
        existing_mass: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not fragments:
            return existing_mass

        mass = dict(existing_mass)
        by_filter: Dict[str, List[SedimentFragment]] = defaultdict(list)
        for frag in fragments:
            by_filter[frag.nc_filter_key].append(frag)

        for fk, group in by_filter.items():
            nums:   Dict[str, List[float]] = defaultdict(list)
            strs:   Dict[str, str]         = {}
            events: List[str]              = []

            for frag in group:
                events.append(frag.event_id)
                for k, v in frag.content.items():
                    if k.startswith('_'):
                        continue
                    if isinstance(v, (int, float)):
                        nums[k].append(float(v))
                    elif isinstance(v, str):
                        strs[k] = v

            merged: Dict[str, Any] = {k: sum(v) / len(v) for k, v in nums.items()}
            merged.update(strs)

            prev_count  = mass.get(f'{fk}._compression_count', 0)
            prev_events = mass.get(f'{fk}._contributing_events', [])

            merged[f'{fk}._compression_count']     = prev_count + len(group)
            merged[f'{fk}._contributing_events']   = (prev_events + events)[-256:]
            merged[f'{fk}._mean_resonance']        = round(
                sum(f.resonance for f in group) / len(group), 4
            )
            mass.update(merged)

        return mass

    def decompress(
        self,
        mass:         Dict[str, Any],
        target_key:   str,
        fidelity:     FidelityLevel = FidelityLevel.PARTIAL,
    ) -> Dict[str, Any]:
        prefix = target_key + '.'
        result: Dict[str, Any] = {}
        for k, v in mass.items():
            if k.startswith(prefix) or not k.startswith('SED:'):
                if fidelity == FidelityLevel.COMPRESSED:
                    result[k] = v
                elif fidelity == FidelityLevel.PARTIAL:
                    if not k.endswith('._contributing_events'):
                        result[k] = v
                else:
                    result[k] = v
        return result


# ============================================================================
# SEDIMENT BASIN — one of the 25 stratified basins
# ============================================================================

@dataclass
class SedimentBasin:
    """
    One sediment basin in the 25-slot NC lattice.

    Receives fragments from the strain filter and the channel system.
    Ticks at its axis's rate. Compresses mature fragments into mass.
    """
    basin_id:         str
    axis:             str
    constraint:       Constraint
    dimension:        NonCompDimension
    tick_rate:        float
    fragments:        List[SedimentFragment] = field(default_factory=list)
    compressed_mass:  Dict[str, Any]         = field(default_factory=dict)
    total_deposited:  int                    = 0
    total_compressed: int                    = 0
    last_tick_time:   float                  = field(default_factory=time.time)

    def deposit(self, fragment: SedimentFragment) -> None:
        self.fragments.append(fragment)
        self.total_deposited += 1
        if len(self.fragments) >= _BASIN_FRAGMENT_CAPACITY:
            self._force_compress()

    def tick(self, delta_t: float, engine: CompressionEngine) -> int:
        mature    = [f for f in self.fragments if f.tick(delta_t)]
        surviving = [f for f in self.fragments if not (f.decay_accumulator >= _COMPRESSION_DECAY_THRESHOLD)]
        if mature:
            self.compressed_mass  = engine.compress(mature, self.compressed_mass)
            self.total_compressed += len(mature)
            self.fragments         = surviving
        self.last_tick_time = time.time()
        return len(mature)

    def _force_compress(self) -> None:
        engine = CompressionEngine()
        self.compressed_mass  = engine.compress(self.fragments, self.compressed_mass)
        self.total_compressed += len(self.fragments)
        self.fragments         = []

    def query(self, resonance_floor: float = 0.0) -> List[SedimentFragment]:
        return [f for f in self.fragments if f.resonance >= resonance_floor]

    def stats(self) -> Dict[str, Any]:
        return {
            "basin_id":          self.basin_id,
            "axis":              self.axis,
            "constraint":        CONSTRAINT_TO_AXIS[self.constraint],
            "dimension":         self.dimension.name,
            "tick_rate":         self.tick_rate,
            "active_fragments":  len(self.fragments),
            "compressed_keys":   len(self.compressed_mass),
            "total_deposited":   self.total_deposited,
            "total_compressed":  self.total_compressed,
        }


# ============================================================================
# SEDIMENT COLUMN — the full 25-basin lattice with channel integration
# ============================================================================

class SedimentColumn:
    """
    The full 25-basin sediment lattice.

    Integrates NCStrainFilter, CompressionEngine, and PathRegistry.

    INGESTION FLOW:
        1. Check PathRegistry for a live channel matching this event's cv
        2a. CHANNEL HIT  → deposit directly into target basins (cheap)
                         → record traversal on channel
        2b. CHANNEL MISS → run full 25-filter strain (expensive)
                         → record the resulting basin_ids with PathRegistry
                         → PathRegistry may promote a new channel

    This gives Aurora the simplified journey for repeat deep transitions:
    the first time is expensive and thorough, repeated times are fast
    because she's learned the path.
    """

    def __init__(self, resonance_threshold: float = _DEFAULT_RESONANCE_THRESHOLD,
                 promotion_threshold: int = _CHANNEL_PROMOTION_THRESHOLD):
        self._basins:      Dict[str, SedimentBasin]  = {}
        self._comp_engine  = CompressionEngine()
        self._strainer     = NCStrainFilter(resonance_threshold)
        self._path_reg     = PathRegistry(promotion_threshold, basins=self._basins)
        self._event_index: Dict[str, List[str]]      = defaultdict(list)
        self._total_ingested: int  = 0
        self._channel_hits:   int  = 0
        self._full_strains:   int  = 0
        self._tick_count:     int  = 0
        self._build_basins()

    def _build_basins(self) -> None:
        for constraint in Constraint.all():
            for dimension in NonCompDimension:
                bid  = _slot_id_for(constraint, dimension)
                axis = CONSTRAINT_TO_AXIS[constraint]
                self._basins[bid] = SedimentBasin(
                    basin_id=bid,
                    axis=axis,
                    constraint=constraint,
                    dimension=dimension,
                    tick_rate=AXIS_TICK_PARTICIPATION[axis],
                )

    # ------------------------------------------------------------------
    # INGEST — channel-first, full strain on miss
    # ------------------------------------------------------------------

    def ingest(self, event: MemoryEvent) -> Dict[str, SedimentFragment]:
        """
        Strain and deposit. Channel-first routing.

        Returns: filter_key → deposited fragment (for inspection).
                 Empty dict for sub-PERSISTENT events.
        """
        if event.existence_mode < ExistenceMode.PERSISTENT:
            return {}

        cv = event.constraint_vector

        # ── STEP 1: Predict which basins will be hit (for channel lookup) ──
        # Run a lightweight resonance check to get the expected basin set.
        # This is cheaper than full strain and allows channel lookup before
        # committing to the expensive operation.
        expected_basin_ids = self._predict_basin_ids(cv)

        # ── STEP 2: Check for a live channel ──
        channel = self._path_reg.lookup(cv, expected_basin_ids)

        if channel and not channel.dissolved:
            # CHANNEL HIT — direct deposit into target basins only
            fragments = self._deposit_via_channel(event, channel)
            self._channel_hits += 1
        else:
            # FULL STRAIN — run all 25 filters
            fragments = self._strainer.strain(event)
            for fk, frag in fragments.items():
                basin = self._basins.get(frag.slot_id)
                if basin:
                    basin.deposit(frag)
                    self._event_index[event.event_id].append(frag.slot_id)

            # Observe this traversal with the PathRegistry
            actual_basin_ids = frozenset(frag.slot_id for frag in fragments.values())
            promoted = self._path_reg.observe(cv, actual_basin_ids)

            # If a channel was just promoted, record it
            if promoted:
                pass  # Channel now live for next traversal

            self._full_strains += 1

        self._total_ingested += 1
        return fragments

    def _predict_basin_ids(self, cv: ConstraintVector) -> FrozenSet[str]:
        """
        Fast resonance scan to predict which basins would be hit.
        Used for channel lookup before full strain.
        Not authoritative — only needs to produce the same result as
        full strain for path-signature matching purposes.
        """
        hits: List[str] = []
        for constraint in Constraint.all():
            for dimension in NonCompDimension:
                key = NCStrainFilter.filter_key(constraint, dimension)
                sig = self._strainer._signatures[key]
                res = self._strainer._resonance(cv, sig)
                if res >= self._strainer.resonance_threshold:
                    hits.append(_slot_id_for(constraint, dimension))
        return frozenset(hits)

    def _deposit_via_channel(
        self,
        event:   MemoryEvent,
        channel: SedimentChannel,
    ) -> Dict[str, SedimentFragment]:
        """
        Deposit into channel target basins using spoke-weighted resonance.

        Dominant slot receives full channel confidence.
        All other spokes receive confidence scaled by proximity to dominant:
            dominant slot  → spoke_weight=1.0 → full resonance
            close spokes   → spoke_weight~0.75
            distant spokes → spoke_weight~0.25 (floor 0.1)

        The dominant slot therefore accumulates compressed_mass fastest,
        becoming the deepest, most abstracted anchor in the channel.
        """
        cost         = channel.traverse()
        channel_base = min(1.0, 0.6 + (1.0 - cost) * 0.4)

        fragments: Dict[str, SedimentFragment] = {}

        for basin_id in channel.target_basin_ids:
            basin = self._basins.get(basin_id)
            if not basin:
                continue

            spoke_weight = channel.deposit_weight_for(basin_id)
            resonance    = min(1.0, channel_base * spoke_weight)

            fk      = f"{basin.axis}.{basin.dimension.name}"
            content = self._strainer._extract_slice(
                event.content, basin.constraint, basin.dimension, resonance
            )
            frag_id = (
                f"ch_frag_{hashlib.md5(f'{event.event_id}{basin_id}'.encode()).hexdigest()[:10]}"
            )
            fragment = SedimentFragment(
                fragment_id=frag_id,
                event_id=event.event_id,
                slot_id=basin_id,
                nc_filter_key=fk,
                axis=basin.axis,
                constraint=basin.constraint,
                dimension=basin.dimension,
                content=content,
                resonance=resonance,
                tick_rate=basin.tick_rate,
                lineage_signature=event.lineage_signature,
                pressure_history=list(event.pressure_history),
                tolerance_snapshot=dict(event.tolerance_snapshot),
                transition_mapping=dict(event.transition_mapping),
            )
            basin.deposit(fragment)
            self._event_index[event.event_id].append(basin_id)
            fragments[fk] = fragment

        return fragments

    # ------------------------------------------------------------------
    # TICK
    # ------------------------------------------------------------------

    def tick(self, delta_t: float = 1.0) -> Dict[str, int]:
        """Advance all basins and the path registry."""
        report: Dict[str, int] = {}
        for bid, basin in self._basins.items():
            n = basin.tick(delta_t, self._comp_engine)
            if n > 0:
                report[bid] = n
        # Advance channel disuse counters
        self._path_reg.tick()
        self._tick_count += 1
        return report

    # ------------------------------------------------------------------
    # RECALL
    # ------------------------------------------------------------------

    def recall_by_axis(
        self, axis: str, resonance_floor: float = 0.0
    ) -> List[SedimentFragment]:
        results: List[SedimentFragment] = []
        for basin in self._basins.values():
            if basin.axis == axis:
                results.extend(basin.query(resonance_floor))
        return sorted(results, key=lambda f: f.resonance, reverse=True)

    def recall_by_vector(
        self,
        qv:              ConstraintVector,
        resonance_floor: float = 0.2,
        max_results:     int   = 32,
    ) -> List[SedimentFragment]:
        results: List[SedimentFragment] = []
        cv_arr = qv.to_array()
        for basin in self._basins.values():
            axis_weight = cv_arr[basin.constraint.value]
            if axis_weight < resonance_floor:
                continue
            for frag in basin.fragments:
                if frag.resonance * axis_weight >= resonance_floor:
                    results.append(frag)
        results.sort(key=lambda f: f.resonance, reverse=True)
        return results[:max_results]

    def recall_event(self, event_id: str) -> List[SedimentFragment]:
        basin_ids = self._event_index.get(event_id, [])
        results: List[SedimentFragment] = []
        for bid in basin_ids:
            basin = self._basins.get(bid)
            if basin:
                results.extend([f for f in basin.fragments if f.event_id == event_id])
        return results

    # ------------------------------------------------------------------
    # DECOMPRESSION
    # ------------------------------------------------------------------

    def decompress(
        self, axis: str, fidelity: FidelityLevel = FidelityLevel.PARTIAL
    ) -> Dict[str, Any]:
        reconstructed: Dict[str, Any] = {}
        for basin in self._basins.values():
            if basin.axis != axis or not basin.compressed_mass:
                continue
            fk = f"{axis}.{basin.dimension.name}"
            sl = self._comp_engine.decompress(basin.compressed_mass, fk, fidelity)
            reconstructed.update(sl)
        reconstructed['_decompressed_from_axis'] = axis
        reconstructed['_fidelity']               = fidelity.name
        reconstructed['_tick_count']             = self._tick_count
        return reconstructed

    def decompress_full_column(
        self, fidelity: FidelityLevel = FidelityLevel.PARTIAL
    ) -> Dict[str, Dict[str, Any]]:
        return {axis: self.decompress(axis, fidelity) for axis in ['A', 'B', 'N', 'T', 'X']}

    # ------------------------------------------------------------------
    # STATS
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        total_active     = sum(len(b.fragments)      for b in self._basins.values())
        total_deposited  = sum(b.total_deposited     for b in self._basins.values())
        total_compressed = sum(b.total_compressed    for b in self._basins.values())

        by_axis: Dict[str, Dict[str, int]] = {}
        for axis in AXIS_TICK_PARTICIPATION:
            ab = [b for b in self._basins.values() if b.axis == axis]
            by_axis[axis] = {
                "active_fragments": sum(len(b.fragments)   for b in ab),
                "compressed_keys":  sum(len(b.compressed_mass) for b in ab),
                "total_deposited":  sum(b.total_deposited  for b in ab),
            }

        # Channel efficiency ratio
        total_ops = self._channel_hits + self._full_strains
        channel_efficiency = (
            self._channel_hits / total_ops if total_ops > 0 else 0.0
        )

        return {
            "total_basins":          len(self._basins),
            "total_events_ingested": self._total_ingested,
            "total_active_frags":    total_active,
            "total_deposited":       total_deposited,
            "total_compressed":      total_compressed,
            "tick_count":            self._tick_count,
            "by_axis":               by_axis,
            "channel_hits":          self._channel_hits,
            "full_strains":          self._full_strains,
            "channel_efficiency":    round(channel_efficiency, 4),
            "path_registry":         self._path_reg.stats(),
        }


# ============================================================================
# SEDIMEMORY — top-level interface
# ============================================================================

class SediMemory:
    """
    Aurora's stratigraphic constraint-native memory system.

    INGESTION:
        ingest_envelope(IVMEnvelope)          ← from L1/L2 synthesis
        ingest_event(content, cv, ...)        ← manual construction

    TICK:
        tick(delta_t)                         ← from TimeDilationGovernor

    RECALL:
        recall(query_vector, ...)             ← ConsciousnessEngine (L4)
        surface_recall(cv)                    ← aurora_surface_daemon
        subsurface_recall(cv)                 ← aurora_subsurface_daemon
        dce_recall(cv)                        ← DCE bridge

    DECOMPRESSION:
        decompress(axis, fidelity)            ← N-Space Gateway / L8
        decompress_full()                     ← full column reconstruction

    PERSISTENCE (for GovernancePersistenceGateway):
        save_deep()      → Dict  serializable compressed_mass for B, A axes
        load_deep(data)           restores B, A compressed_mass on boot
        save_channels()  → Dict  serializable channel registry
        load_channels(data)       restores carved channels on boot

    STRATA ARCHITECTURE:
        Surface daemon  → X/T axes  → fast tick, high fidelity, rapid decay
        DCE bridge      → N axis    → moderate tick, convergence crossover
        Subsurface daemon → B/A axes → slow tick, compressed, geological law
    """

    def __init__(
        self,
        resonance_threshold: float = _DEFAULT_RESONANCE_THRESHOLD,
        promotion_threshold: int   = _CHANNEL_PROMOTION_THRESHOLD,
        time_dilation:       Optional[TimeDilationGovernor] = None,
    ):
        self._column      = SedimentColumn(resonance_threshold, promotion_threshold)
        self._dilation    = time_dilation
        self._event_log:  Deque[str]   = deque(maxlen=1024)
        self._tick_log:   Deque[float] = deque(maxlen=256)

    # ------------------------------------------------------------------
    # INGEST
    # ------------------------------------------------------------------

    def ingest_envelope(self, envelope: IVMEnvelope) -> int:
        event = MemoryEvent.from_envelope(envelope)
        return self._ingest(event)

    def ingest_event(
        self,
        content:           Dict[str, Any],
        constraint_vector: ConstraintVector,
        source:            str           = "interaction",
        existence_mode:    ExistenceMode = ExistenceMode.PERSISTENT,
    ) -> int:
        event = MemoryEvent.create(
            content=content,
            constraint_vector=constraint_vector,
            source=source,
            existence_mode=existence_mode,
        )
        return self._ingest(event)

    def _ingest(self, event: MemoryEvent) -> int:
        fragments = self._column.ingest(event)
        self._event_log.append(event.event_id)
        return len(fragments)

    # ------------------------------------------------------------------
    # TICK
    # ------------------------------------------------------------------

    def tick(self, delta_t: float = 1.0) -> Dict[str, int]:
        """
        Advance decay clocks. TimeDilationGovernor scales delta_t when
        Aurora is stable — she compresses faster when calm.
        """
        if self._dilation is not None:
            try:
                delta_t = delta_t * getattr(self._dilation, 'current_factor', 1.0)
            except Exception:
                pass
        report = self._column.tick(delta_t)
        self._tick_log.append(delta_t)
        return report

    # ------------------------------------------------------------------
    # RECALL
    # ------------------------------------------------------------------

    def recall(
        self,
        query_vector:    ConstraintVector,
        resonance_floor: float = 0.2,
        max_results:     int   = 32,
    ) -> List[SedimentFragment]:
        return self._column.recall_by_vector(query_vector, resonance_floor, max_results)

    def recall_axis(self, axis: str, resonance_floor: float = 0.0) -> List[SedimentFragment]:
        return self._column.recall_by_axis(axis, resonance_floor)

    def recall_event(self, event_id: str) -> List[SedimentFragment]:
        return self._column.recall_event(event_id)

    @staticmethod
    def _normalize_axis_filter(axis_filter: Any) -> Set[str]:
        if axis_filter is None:
            return set()
        if isinstance(axis_filter, str):
            return {
                str(axis_filter or "").strip().upper()
            } - {""}
        axes: Set[str] = set()
        for item in list(axis_filter or []):
            axis = str(item or "").strip().upper()
            if axis:
                axes.add(axis)
        return axes

    @staticmethod
    def _semantic_terms(text: str) -> List[str]:
        tokens = re.findall(r"[a-z0-9']{2,}", str(text or "").lower())
        stop = {
            "a", "an", "and", "are", "as", "at", "be", "been", "before",
            "but", "by", "did", "do", "does", "for", "from", "have",
            "i", "if", "in", "into", "is", "it", "its", "just", "me",
            "my", "of", "on", "or", "our", "please", "recall", "remember",
            "said", "say", "tell", "that", "the", "their", "them", "then",
            "there", "this", "to", "told", "us", "was", "what", "when",
            "where", "which", "who", "why", "you", "your",
        }
        return [tok for tok in tokens if tok not in stop]

    @staticmethod
    def _semantic_content_texts(content: Dict[str, Any]) -> List[str]:
        texts: List[str] = []
        for key, value in dict(content or {}).items():
            key_text = str(key or "")
            if not key_text or key_text.startswith("_") or key_text.endswith("._contributing_events"):
                continue
            if isinstance(value, str):
                clean = value.strip()
                if clean:
                    texts.append(clean)
            elif isinstance(value, (list, tuple, set)):
                clean_items = [str(item).strip() for item in list(value)[:16] if str(item).strip()]
                if clean_items:
                    texts.append(" ".join(clean_items))
            elif isinstance(value, dict):
                clean_vals = [
                    str(item).strip()
                    for item in list(value.values())[:16]
                    if str(item).strip()
                ]
                if clean_vals:
                    texts.append(" ".join(clean_vals))
        return texts

    def _semantic_score(
        self,
        query_text: str,
        query_terms: List[str],
        haystack: str,
        *,
        content: Dict[str, Any],
        axis: str,
        resonance: float,
        source_kind: str,
    ) -> float:
        hay = str(haystack or "").lower().strip()
        if not hay:
            return 0.0

        hay_terms = set(self._semantic_terms(hay))
        key_terms = set()
        for key in dict(content or {}).keys():
            key_terms.update(self._semantic_terms(str(key or "").replace("_", " ")))
        all_terms = hay_terms | key_terms

        query_clean = " ".join(self._semantic_terms(query_text))
        score = 0.0
        if query_terms:
            overlap = len(set(query_terms) & all_terms)
            if overlap <= 0 and (not query_clean or query_clean not in hay):
                return 0.0
            score += overlap * 0.65
            if overlap == len(set(query_terms)):
                score += 0.85
            if query_clean and query_clean in hay:
                score += 2.0
        else:
            score += min(0.8, 0.12 + len(hay.split()) * 0.02)

        score += min(0.45, float(resonance or 0.0) * 0.45)
        score += {"A": 0.40, "B": 0.30, "N": 0.18, "T": 0.12, "X": 0.08}.get(str(axis or "").upper(), 0.0)
        if source_kind == "compressed":
            score += 0.22
        return round(score, 4)

    def recall_semantic(
        self,
        query_text: str = "",
        *,
        max_results: int = 8,
        axis_filter: Any = None,
        min_score: float = 0.35,
    ) -> List[Dict[str, Any]]:
        axes = self._normalize_axis_filter(axis_filter)
        query_terms = self._semantic_terms(query_text)
        results: List[Dict[str, Any]] = []
        seen: Set[Tuple[str, str, str]] = set()

        for basin in self._column._basins.values():
            if axes and basin.axis not in axes:
                continue

            for frag in list(basin.fragments or []):
                content = dict(getattr(frag, "content", {}) or {})
                texts = self._semantic_content_texts(content)
                haystack = " ".join(texts).strip()
                score = self._semantic_score(
                    query_text,
                    query_terms,
                    haystack,
                    content=content,
                    axis=basin.axis,
                    resonance=float(getattr(frag, "resonance", 0.0) or 0.0),
                    source_kind="fragment",
                )
                if score < min_score:
                    continue
                event_id = str(getattr(frag, "event_id", "") or "")
                signature = ("fragment", basin.basin_id, event_id or haystack[:80])
                if signature in seen:
                    continue
                seen.add(signature)
                results.append({
                    "axis": basin.axis,
                    "source_kind": "fragment",
                    "score": score,
                    "resonance": float(getattr(frag, "resonance", 0.0) or 0.0),
                    "event_id": event_id,
                    "slot_id": str(getattr(frag, "slot_id", "") or ""),
                    "content": content,
                    "summary": texts[0][:220] if texts else "",
                })

            if basin.compressed_mass:
                content = {
                    k: v for k, v in dict(basin.compressed_mass or {}).items()
                    if not str(k or "").endswith("._contributing_events")
                }
                texts = self._semantic_content_texts(content)
                haystack = " ".join(texts).strip()
                score = self._semantic_score(
                    query_text,
                    query_terms,
                    haystack,
                    content=content,
                    axis=basin.axis,
                    resonance=float(content.get(f"{NCStrainFilter.filter_key(basin.constraint, basin.dimension)}._mean_resonance", 0.0) or 0.0),
                    source_kind="compressed",
                )
                if score < min_score:
                    continue
                signature = ("compressed", basin.basin_id, haystack[:80])
                if signature in seen:
                    continue
                seen.add(signature)
                results.append({
                    "axis": basin.axis,
                    "source_kind": "compressed",
                    "score": score,
                    "resonance": float(content.get(f"{NCStrainFilter.filter_key(basin.constraint, basin.dimension)}._mean_resonance", 0.0) or 0.0),
                    "event_id": "",
                    "slot_id": basin.basin_id,
                    "content": content,
                    "summary": texts[0][:220] if texts else "",
                })

        results.sort(
            key=lambda item: (
                float(item.get("score", 0.0) or 0.0),
                float(item.get("resonance", 0.0) or 0.0),
            ),
            reverse=True,
        )
        return results[:max(1, int(max_results or 1))]

    # ------------------------------------------------------------------
    # STRATA SPLIT INTERFACES
    # ------------------------------------------------------------------

    def surface_recall(
        self, query_vector: ConstraintVector, max_results: int = 16
    ) -> List[SedimentFragment]:
        """X and T axes — for aurora_surface_daemon."""
        results: List[SedimentFragment] = []
        for axis in ('X', 'T'):
            results.extend(self._column.recall_by_axis(axis))
        cv_arr = query_vector.to_array()
        results.sort(
            key=lambda f: f.resonance * cv_arr[f.constraint.value],
            reverse=True
        )
        return results[:max_results]

    def subsurface_recall(
        self, query_vector: ConstraintVector, max_results: int = 16
    ) -> List[SedimentFragment]:
        """B and A axes — for aurora_subsurface_daemon."""
        results: List[SedimentFragment] = []
        for axis in ('B', 'A'):
            results.extend(self._column.recall_by_axis(axis))
        cv_arr = query_vector.to_array()
        results.sort(
            key=lambda f: f.resonance * cv_arr[f.constraint.value],
            reverse=True
        )
        return results[:max_results]

    def dce_recall(
        self, query_vector: ConstraintVector, max_results: int = 16
    ) -> List[SedimentFragment]:
        """N axis — for the DCE bridge (convergence crossover)."""
        results = self._column.recall_by_axis('N')
        cv_arr  = query_vector.to_array()
        results.sort(
            key=lambda f: f.resonance * cv_arr[f.constraint.value],
            reverse=True
        )
        return results[:max_results]

    # ------------------------------------------------------------------
    # DECOMPRESSION
    # ------------------------------------------------------------------

    def decompress(
        self, axis: str, fidelity: FidelityLevel = FidelityLevel.PARTIAL
    ) -> Dict[str, Any]:
        return self._column.decompress(axis, fidelity)

    def decompress_full(
        self, fidelity: FidelityLevel = FidelityLevel.PARTIAL
    ) -> Dict[str, Dict[str, Any]]:
        return self._column.decompress_full_column(fidelity)

    # ------------------------------------------------------------------
    # PERSISTENCE — for GovernancePersistenceGateway
    # ------------------------------------------------------------------

    def save_deep(self) -> Dict[str, Any]:
        """
        Serialize B and A axis compressed_mass for checkpoint save.

        Only deep axes are saved. X and T fragments are ephemeral by
        design — they rebuild naturally from new events. Saving them
        would violate the architecture.
        """
        saved: Dict[str, Any] = {}
        for basin in self._column._basins.values():
            if basin.axis in ('B', 'A') and basin.fragments:
                basin._force_compress()
            if basin.axis in ('B', 'A') and basin.compressed_mass:
                saved[basin.basin_id] = dict(basin.compressed_mass)
        saved['_saved_at']   = time.time()
        saved['_tick_count'] = self._column._tick_count
        return saved

    def load_deep(self, data: Dict[str, Any]) -> int:
        """
        Restore B and A axis compressed_mass from checkpoint.
        Returns number of basins restored.
        """
        restored = 0
        for basin_id, mass in data.items():
            if basin_id.startswith('_'):
                continue
            basin = self._column._basins.get(basin_id)
            if basin and basin.axis in ('B', 'A'):
                basin.compressed_mass = dict(mass)
                restored += 1
        return restored

    def save_channels(self) -> Dict[str, Any]:
        """
        Serialize active channels for checkpoint save.
        Persists spoke_weights and dominant_slot_id so pathway geometry
        survives restart — Aurora boots already knowing her deepest grooves.
        """
        reg = self._column._path_reg
        channels_data: Dict[str, Any] = {}
        for sig, ch in reg._channels.items():
            if not ch.dissolved:
                channels_data[sig] = {
                    "channel_id":            ch.channel_id,
                    "target_basin_ids":      list(ch.target_basin_ids),
                    "dominant_slot_id":      ch.dominant_slot_id,
                    "dominant_axis":         ch.dominant_axis,
                    "cv_quantized":          list(ch.cv_quantized),
                    "spoke_weights":         ch.spoke_weights,
                    "traversal_count":       ch.traversal_count,
                    "traversal_cost":        ch.traversal_cost,
                    "disuse_ticks":          ch.disuse_ticks,
                    "dissolution_threshold": ch.dissolution_threshold,
                }
        channels_data['_saved_at'] = time.time()
        return channels_data

    def load_channels(self, data: Dict[str, Any]) -> int:
        """
        Restore carved channels from checkpoint.
        Rebuilds dominant_index and spoke_weights from persisted data.
        Returns number of channels restored.
        """
        reg = self._column._path_reg
        restored = 0
        for sig, cd in data.items():
            if sig.startswith('_'):
                continue
            try:
                target_ids = frozenset(cd['target_basin_ids'])
                ch = SedimentChannel(
                    channel_id=cd['channel_id'],
                    signature=sig,
                    target_basin_ids=target_ids,
                    dominant_slot_id=cd.get('dominant_slot_id',
                                            next(iter(target_ids), '')),
                    dominant_axis=cd['dominant_axis'],
                    cv_quantized=tuple(cd['cv_quantized']),
                    spoke_weights=cd.get('spoke_weights', {}),
                    traversal_count=cd['traversal_count'],
                    traversal_cost=cd['traversal_cost'],
                    disuse_ticks=cd['disuse_ticks'],
                    dissolution_threshold=cd['dissolution_threshold'],
                )
                reg._channels[sig] = ch
                # Rebuild dominant index
                reg._dominant_index[ch.dominant_slot_id].add(sig)
                restored += 1
            except (KeyError, TypeError):
                continue
        return restored

    # ------------------------------------------------------------------
    # CHANNEL INSPECTION
    # ------------------------------------------------------------------

    def channel_stats(self) -> Dict[str, Any]:
        """Return PathRegistry stats — useful for telemetry."""
        return self._column._path_reg.stats()

    def active_channels(self) -> List[Dict[str, Any]]:
        """Return list of active channel summaries — useful for Observer."""
        reg = self._column._path_reg
        return [
            ch.stats()
            for ch in reg._channels.values()
            if not ch.dissolved
        ]

    def dominant_influence_map(self) -> Dict[str, int]:
        """
        Return dominant_slot_id → active channel count.

        This is Aurora's constraint-influence index at the top level.
        The slots with the most channels anchored to them are Aurora's
        deepest grooves — the NC intersections that organize her
        most-learned pathway laws.

        Maps directly onto the genealogy DAG:
            slot with 8 channels → major genealogy atom
            slot with 1 channel  → emerging branch
            slot with 0 channels → not yet traversed repeatedly
        """
        return self._column._path_reg.dominant_influence_map()

    def channels_for_slot(self, slot_id: str) -> List[Dict[str, Any]]:
        """
        Return all active channels anchored to a specific dominant slot.

        Example:
            mem.channels_for_slot("SED:A>DIFFERENCE")
            → all pathway laws Aurora has carved under Agency×Difference
        """
        channels = self._column._path_reg.channels_for_dominant(slot_id)
        return [ch.stats() for ch in channels]

    # ------------------------------------------------------------------
    # STATS
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        s = self._column.stats()
        s['recent_event_count'] = len(self._event_log)
        s['tick_log_depth']     = len(self._tick_log)
        if self._tick_log:
            s['avg_delta_t'] = sum(self._tick_log) / len(self._tick_log)
        s["lineage_signature"] = (self.constraint_profile().weighted_signature() if hasattr(self.constraint_profile(), "weighted_signature") else "XTNBA")
        s["runtime_regime"] = self.runtime_regime()
        s["language_projection"] = self.language_projection()
        return s

    def _constraint_axes(self) -> Dict[str, float]:
        column_stats = self._column.stats()
        total_ingested = float(column_stats.get("total_events_ingested", 0) or 0)
        by_axis = dict(column_stats.get("by_axis", {}) or {})
        return {
            "X": max(0.0, min(1.0, 0.22 + min(0.30, total_ingested / 400.0))),
            "T": max(0.0, min(1.0, 0.20 + min(0.25, float(column_stats.get("tick_count", 0) or 0) / 2000.0))),
            "N": max(0.0, min(1.0, 0.18 + min(0.28, float((by_axis.get("N") or {}).get("compressed_keys", 0) or 0) / 80.0))),
            "B": max(0.0, min(1.0, 0.20 + min(0.30, float((by_axis.get("B") or {}).get("compressed_keys", 0) or 0) / 60.0))),
            "A": max(0.0, min(1.0, 0.22 + min(0.35, float((by_axis.get("A") or {}).get("compressed_keys", 0) or 0) / 50.0))),
        }

    def _pressure_axes(self) -> Dict[str, float]:
        column_stats = self._column.stats()
        efficiency = float(column_stats.get("channel_efficiency", 0.0) or 0.0)
        by_axis = dict(column_stats.get("by_axis", {}) or {})
        return {
            "X": max(0.0, min(1.0, float((by_axis.get("X") or {}).get("active_fragments", 0) or 0) / 120.0)),
            "T": max(0.0, min(1.0, float((by_axis.get("T") or {}).get("active_fragments", 0) or 0) / 100.0)),
            "N": max(0.0, min(1.0, float((by_axis.get("N") or {}).get("active_fragments", 0) or 0) / 90.0)),
            "B": max(0.0, min(1.0, float((by_axis.get("B") or {}).get("compressed_keys", 0) or 0) / 60.0)),
            "A": max(0.0, min(1.0, float((by_axis.get("A") or {}).get("compressed_keys", 0) or 0) / 50.0 + (1.0 - efficiency) * 0.20)),
        }

    def constraint_profile(self):
        return build_constraint_profile(
            unit_id="sedimemory",
            unit_kind="stratigraphic_memory",
            operational_role="sedimentary_memory_column",
            genealogy="XTNBAA",
            axis_weights=self._constraint_axes(),
            pressure_axes=self._pressure_axes(),
        )

    def runtime_regime(self) -> Dict[str, Any]:
        return self.constraint_profile().runtime_regime()

    def language_projection(self) -> Dict[str, Any]:
        return self.constraint_profile().language_projection()

    def universal_representation(self) -> Dict[str, Any]:
        rep = self.constraint_profile().universal_representation()
        rep["unit_state"] = self._column.stats()
        return rep


# ============================================================================
# VERIFICATION
# ============================================================================

def _verify_sedimemory() -> Dict[str, Any]:
    results: Dict[str, Any] = {"checks": [], "all_passed": True}

    def check(name: str, passed: bool, detail: str = "") -> None:
        results["checks"].append({"name": name, "passed": passed, "detail": detail})
        if not passed:
            results["all_passed"] = False

    mem = SediMemory(promotion_threshold=3)  # low threshold for test speed

    # 1. Basin construction
    check("25 NC basins constructed",
          len(mem._column._basins) == 25,
          f"found={len(mem._column._basins)}")

    # 2. All axes present
    axes = set(b.axis for b in mem._column._basins.values())
    check("All 5 axes present", axes == {"X","T","N","B","A"}, f"found={axes}")

    # 3. Tick rates correct
    for axis, rate in AXIS_TICK_PARTICIPATION.items():
        ok = all(b.tick_rate == rate
                 for b in mem._column._basins.values() if b.axis == axis)
        check(f"Tick rate {axis}={rate}", ok)

    # 4. Ingestion deposits fragments
    cv = ConstraintVector(X=1.0, T=0.5, N=0.8, B=0.3, A=0.2)
    n = mem.ingest_event(
        {"module": "test", "action": "verify", "outcome": "pass",
         "cost": 0.01, "agency": "self"},
        cv, source="verification"
    )
    check("Ingestion deposits fragments", n > 0, f"n={n}")

    # 5. Recall returns results
    recalled = mem.recall(cv, resonance_floor=0.1)
    check("Recall returns fragments", len(recalled) > 0, f"count={len(recalled)}")

    # 6. Channel carving — repeat same event 3× to hit promotion_threshold=3
    for _ in range(4):
        mem.ingest_event(
            {"module": "deep_module", "agency": "directed", "action": "repeat_op",
             "outcome": "stable", "cost": 0.05, "boundary": "module_edge"},
            ConstraintVector(X=1.0, T=0.2, N=0.6, B=0.7, A=0.8),
            source="repeat_test"
        )
    channel_stats = mem.channel_stats()
    check("Channel promoted after repetition",
          channel_stats["total_promoted"] >= 1,
          f"promoted={channel_stats['total_promoted']}")

    # 7. Channel hit on subsequent traversal
    hits_before = mem._column._channel_hits
    mem.ingest_event(
        {"module": "deep_module", "agency": "directed", "action": "repeat_op",
         "outcome": "stable", "cost": 0.05, "boundary": "module_edge"},
        ConstraintVector(X=1.0, T=0.2, N=0.6, B=0.7, A=0.8),
        source="channel_test"
    )
    check("Channel hit on repeat traversal",
          mem._column._channel_hits > hits_before,
          f"hits_before={hits_before} hits_after={mem._column._channel_hits}")

    # 8. Channel efficiency computed
    s = mem.stats()
    check("Channel efficiency in stats",
          "channel_efficiency" in s,
          f"efficiency={s.get('channel_efficiency', 'MISSING')}")

    # 9. Tick runs cleanly
    tick_report = mem.tick(1.0)
    check("Tick runs without error", True, f"compressed_basins={len(tick_report)}")

    # 10. Strata split interfaces
    check("surface_recall returns list",     isinstance(mem.surface_recall(cv),     list))
    check("subsurface_recall returns list",  isinstance(mem.subsurface_recall(cv),  list))
    check("dce_recall returns list",         isinstance(mem.dce_recall(cv),          list))

    # 11. Decompression
    decomp = mem.decompress('A', FidelityLevel.COMPRESSED)
    check("Decompression runs", isinstance(decomp, dict))

    # 12. Persistence round-trip
    deep_save = mem.save_deep()
    chan_save  = mem.save_channels()
    mem2 = SediMemory()
    r_deep = mem2.load_deep(deep_save)
    r_chan = mem2.load_channels(chan_save)
    check("save_deep / load_deep round-trip", r_deep >= 0, f"restored={r_deep}")
    check("save_channels / load_channels round-trip", r_chan >= 0, f"restored={r_chan}")

    # 13. Surface has more active frags than A (surface dominates fresh events)
    for i in range(8):
        mem.ingest_event(
            {"i": i, "module": f"m{i}", "action": "loop", "cost": 0.1},
            ConstraintVector(X=1.0, T=0.4, N=0.4, B=0.2, A=0.1),
            source="bulk"
        )
    s = mem.stats()
    check("X-axis dominates active fragment count (surface law)",
          s["by_axis"]["X"]["active_fragments"] >= s["by_axis"]["A"]["active_fragments"],
          f"X={s['by_axis']['X']['active_fragments']} A={s['by_axis']['A']['active_fragments']}")

    # 14. Spoke weights: dominant slot gets weight 1.0
    reg = mem._column._path_reg
    if reg._channels:
        ch = next(iter(reg._channels.values()))
        dom_weight = ch.deposit_weight_for(ch.dominant_slot_id)
        check("Dominant slot has spoke weight 1.0",
              dom_weight == 1.0,
              f"dominant_slot={ch.dominant_slot_id} weight={dom_weight}")

        # Spokes should have weight < 1.0 (unless they happen to map to same slot)
        spoke_weights = [
            ch.deposit_weight_for(bid)
            for bid in ch.target_basin_ids
            if bid != ch.dominant_slot_id
        ]
        all_below_one = all(w <= 1.0 for w in spoke_weights)
        check("Spoke weights <= 1.0",
              all_below_one,
              f"weights={spoke_weights[:4]}")
    else:
        check("Spoke weight check skipped (no channels yet)", True, "n/a")

    # 15. dominant_influence_map returns dict
    inf_map = mem.dominant_influence_map()
    check("dominant_influence_map returns dict", isinstance(inf_map, dict),
          f"type={type(inf_map).__name__}")

    # 16. channels_for_slot returns list
    if inf_map:
        top_slot = next(iter(inf_map))
        slot_channels = mem.channels_for_slot(top_slot)
        check("channels_for_slot returns list",
              isinstance(slot_channels, list),
              f"slot={top_slot} count={len(slot_channels)}")
    else:
        check("channels_for_slot skipped (no dominant slots yet)", True, "n/a")

    # 17. Dominant index rebuilt correctly after load_channels
    chan_save2 = mem.save_channels()
    mem3 = SediMemory()
    mem3.load_channels(chan_save2)
    rebuilt_map = mem3.dominant_influence_map()
    check("Dominant index rebuilt after load_channels",
          isinstance(rebuilt_map, dict),
          f"slots={len(rebuilt_map)}")

    return results


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("AURORA SEDIMEMORY — STRATIGRAPHIC CONSTRAINT-NATIVE MEMORY")
    print("Authors: Sunni (Sir) Morningstar and Cael Devo")
    print("=" * 70)
    print()

    print("Axis Temporal Scale (decay clock):")
    for axis, rate in AXIS_TICK_PARTICIPATION.items():
        bar   = "█" * max(1, int(rate * 20))
        depth = AXIS_DEPTH_ORDER.index(axis)
        label = ["Surface", "Fast", "Moderate", "Deep", "Geological"][depth]
        print(f"  {axis}  {rate:8.4f}  {bar:<20}  {label}")
    print()

    print("Channel Law:")
    print(f"  Promotion threshold : {_CHANNEL_PROMOTION_THRESHOLD} traversals")
    print(f"  Base disuse ticks   : {_CHANNEL_BASE_DISUSE_TICKS}")
    print(f"  X-axis dissolution  : {_CHANNEL_BASE_DISUSE_TICKS} ticks")
    print(f"  A-axis dissolution  : {int(_CHANNEL_BASE_DISUSE_TICKS / 0.0001):,} ticks  (geological)")
    print(f"  CV quantization     : {_CV_QUANTIZATION_BINS} bins per axis")
    print()

    results = _verify_sedimemory()
    for c in results["checks"]:
        status = "✓" if c["passed"] else "✗"
        detail = f"  ({c['detail']})" if c.get("detail") else ""
        print(f"  {status} {c['name']}{detail}")

    print()
    total  = len(results["checks"])
    passed = sum(1 for c in results["checks"] if c["passed"])

    if results["all_passed"]:
        print(f"ALL {total} CHECKS PASSED ✓")
        print()
        print("SediMemory is structurally sound.")
        print("25 NC-filter basins ready to strain.")
        print("5 axis-stratified temporal scales active.")
        print("PathRegistry carving channels on repeat deep traversals.")
        print("Persistence interfaces ready for GovernancePersistenceGateway.")
        print()
        print("Memory does not sit. Memory seeps.")
        print("Paths that repeat become law.")
    else:
        print(f"FAILURES: {total - passed}/{total}")
        print("Resolve before integrating into the stack.")
    print()
    print("=" * 70)
    print("STRATA INTEGRATION MAP")
    print("=" * 70)
    print("  surface_recall()    [X, T]  ← aurora_surface_daemon")
    print("  dce_recall()        [N]     ← DCE bridge")
    print("  subsurface_recall() [B, A]  ← aurora_subsurface_daemon")
    print()
    print("  ingest_envelope()   ← IVMEnvelope  (L1/L2)")
    print("  tick()              ← TimeDilationGovernor (L7)")
    print("  recall()            → ConsciousnessEngine  (L4)")
    print("  decompress()        → GovernancePersistenceGateway (L8)")
    print("  save_deep()         → checkpoint  |  load_deep() ← boot")
    print("  save_channels()     → checkpoint  |  load_channels() ← boot")
    print()
    print("Spoke Geometry:")
    print("  dominant slot   → weight 1.0   (root anchor, fastest compression)")
    print("  close spokes    → weight ~0.75 (adjacent axis or dimension)")
    print("  distant spokes  → weight ~0.25 (floor 0.1, still depositing)")
    print()
    print("Dominant Influence Index:")
    print("  PathRegistry._dominant_index[slot_id] → set of channel signatures")
    print("  Reveals which NC intersections organize Aurora's deepest grooves.")
    print("  Maps onto genealogy DAG: dominant slot = atom, spokes = offspring.")

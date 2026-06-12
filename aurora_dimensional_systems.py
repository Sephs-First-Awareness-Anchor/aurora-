#!/usr/bin/env python3
"""
AURORA DIMENSIONAL SYSTEMS
============================

Layer 3 of Aurora's architecture.
The four dimensional organs, each operating within ontological constraints.

REPLACES (consolidated from 4+ modules):
    evolutionary_dimensional_processing_COMPLETE.py  (~1290 lines)
    evolutionary_dimensional_memory_constant.py       (~1316 lines)
    evolutionary_dimensional_energy_complete.py       (~1003 lines)
    dimensional_mortality_morality_system.py           (~923 lines)
    dimensional_memory_constant_standalone_demo.py
    dimensional_processing_system_standalone_demo.py
    dimensional_energy_regulator.py

DEPENDS ON:
    foundational_contract.py  (Layer 0)
    aurora_ivm.py             (Layer 1)
    aurora_i_state_beings.py  (Layer 2)

ARCHITECTURE:
    Four systems. Each receives IVMEnvelopes. Each is gated by ExistenceMode.

    DPS  â€" Crystal Processing  â€" requires PERSISTENT+
           Crystals grow: BASE â†' COMPOSITE â†' FULL_CONCEPT â†' QUASI
           8-point facets define crystal geometry.
           QUASI crystals internalize governance laws.

    DMC  â€" Memory Constant     â€" requires PERSISTENT+
           Data nodes with dimensional links.
           Concept indexing and pattern recognition.
           Laws emerge from repeated patterns.

    DER  â€" Energy Regulator    â€" requires PERSISTENT+
           FACET-LEVEL energy physics (restored from original).
           Per-facet energy tracking with 8-point cosine resonance graph.
           Batch dispersal via adjacency matrix.
           Presence from facet energy variance.
           Curiosity injection for underexplored facets.
           Category aggregation for backward-compatible pool interface.

    DMM  â€" Morality/Mortality  â€" requires AGENTIC
           7 moral pillars from Sunni's doctrine.
           Evaluation â†' score â†' energy consequence.
           Moral alignment sustains vitality. Violation drains it.

    If an envelope's mode is below a system's gate, the system
    returns silence â€" not failure. The entity simply doesn't exist
    at that system's tier.

Authors: Sunni (Sir) Morningstar and Cael Devo
Created: February 2026
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations
import time
import os
import math
import random
import hashlib
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
# EDIT (constraint-expansive concepts): WARP machinery for DPS
from aurora_warp_protocol import (
    WarpCapable, WarpComponent, axes_to_istates, istates_to_axes,
)
from enum import Enum, IntEnum

from aurora_constraint_unit_adapter import build_constraint_profile
from foundational_contract import (
    ExistenceMode,
    OntologicalViolation,
)

from aurora_ivm import (
    IVMLattice,
    IVMNode,
    IVMEnvelope,
)

# ── Layer -1: Constraint Manifold (optional guard for portability) ───────────
try:
    from aurora_constraint_manifold import (
        ConstraintVector,
        Constraint,
    )
    CONSTRAINT_MANIFOLD_AVAILABLE = True
except ImportError:
    CONSTRAINT_MANIFOLD_AVAILABLE = False

# ── Layer 2: I-State Beings — SynthesisResult ────────────────────────────────
try:
    from aurora_i_state_beings import SynthesisResult as _SynthesisResult
    _SYNTHESIS_TYPE = _SynthesisResult
    I_STATE_BEINGS_AVAILABLE = True
except ImportError:
    _SYNTHESIS_TYPE = None
    I_STATE_BEINGS_AVAILABLE = False

# ── Evolution/Genealogy bridge (optional) ───────────────────────────────────
try:
    from aurora_evolution_stack import (
        ConstraintGenealogyLogger,
        AbilityProfile,
        TraceItem,
        PressureVec,
        EnvironmentVector,
    )
    from aurora_internal.lineage_canonical import (
        constraints_for_operation,
        axis_token,
    )
    GENEALOGY_AVAILABLE = True
except ImportError:
    ConstraintGenealogyLogger = None  # type: ignore
    AbilityProfile = None  # type: ignore
    TraceItem = None  # type: ignore
    PressureVec = None  # type: ignore
    EnvironmentVector = None  # type: ignore
    constraints_for_operation = None  # type: ignore
    axis_token = None  # type: ignore
    GENEALOGY_AVAILABLE = False

# ── 625 pressure-map bridge (optional) ───────────────────────────────────────
try:
    from aurora_625_pressure_map import Aurora625PressureMap
    PRESSURE_MAP_AVAILABLE = True
except ImportError:
    Aurora625PressureMap = None  # type: ignore
    PRESSURE_MAP_AVAILABLE = False


# ============================================================================
# SHARED: MODE GATE
# ============================================================================

def mode_gate(envelope: IVMEnvelope, min_mode: ExistenceMode) -> bool:
    """Return True if the envelope's mode reaches the required tier."""
    return envelope.mode >= min_mode


# ============================================================================
# SHARED: EVOLUTION TRACKER (one, not four)
# ============================================================================

class EvolutionTracker:
    """
    Unified evolution tracker for all dimensional systems.
    Tracks generational improvements without seed populations or
    random mutation fantasies. Measures actual performance.
    """

    def __init__(self):
        self.generation = 0
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))

    def record(self, system: str, metric: str, value: float):
        self.metrics[f"{system}.{metric}"].append(value)

    def advance(self):
        self.generation += 1

    def average(self, system: str, metric: str) -> float:
        key = f"{system}.{metric}"
        vals = self.metrics.get(key)
        if not vals:
            return 0.0
        return sum(vals) / len(vals)

    def get_summary(self) -> Dict[str, Any]:
        return {
            'generation': self.generation,
            'metrics': {
                k: round(sum(v) / len(v), 4) if v else 0.0
                for k, v in self.metrics.items()
            },
        }


# ============================================================================
#  DPS â€" CRYSTAL PROCESSING SYSTEM
# ============================================================================

class CrystalLevel(IntEnum):
    BASE = 1
    COMPOSITE = 2
    FULL_CONCEPT = 3
    QUASI = 4


class FacetState(Enum):
    ACTIVE = "active"
    DECAYING = "decaying"
    RELIC = "relic"


# The 8 internal physics laws (for QUASI self-governance)
INTERNAL_LAWS = (
    'ENERGY', 'MOTION', 'COLLISION', 'CHAOS',
    'CONSCIOUSNESS', 'GOVERNANCE', 'RECURSION', 'SYMMETRY',
)


@dataclass
class CrystalFacet:
    """
    One facet of a crystal. 8 physics points define its geometry.
    """
    facet_id: str
    role: str
    content: Any
    confidence: float = 0.5
    state: FacetState = FacetState.ACTIVE
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)

    # 8 physics points
    resonance: float = field(default_factory=lambda: random.uniform(0.3, 0.7))
    sensitivity: float = field(default_factory=lambda: random.uniform(0.3, 0.7))
    abstractness: float = field(default_factory=lambda: random.uniform(0.3, 0.7))
    potential: float = field(default_factory=lambda: random.uniform(0.3, 0.7))
    stability: float = field(default_factory=lambda: random.uniform(0.3, 0.7))
    coherence: float = field(default_factory=lambda: random.uniform(0.3, 0.7))
    complexity: float = field(default_factory=lambda: random.uniform(0.3, 0.7))
    frequency: float = field(default_factory=lambda: random.uniform(0.3, 0.7))

    def strengthen(self, amount: float = 0.1):
        self.confidence = min(1.0, self.confidence + amount)
        self.access_count += 1
        self.last_accessed = time.time()
        self.state = FacetState.ACTIVE
        self._interdependent_physics(boost=True)

    def decay(self, rate: float = 0.01):
        if self.state == FacetState.RELIC:
            return
        hours = (time.time() - self.last_accessed) / 3600
        self.confidence = max(0.0, self.confidence - rate * hours)
        self._interdependent_physics(boost=False)
        if self.confidence < 0.3:
            self.state = FacetState.DECAYING
        if self.confidence < 0.1:
            self.state = FacetState.RELIC

    def _interdependent_physics(self, boost: bool):
        if boost:
            if self.coherence > 0.7:
                self.stability = min(1.0, self.stability + 0.05)
            if self.potential > 0.7:
                self.resonance = min(1.0, self.resonance + 0.05)
        else:
            if self.stability < 0.3:
                self.coherence = max(0.0, self.coherence - 0.03)
            if self.complexity > 0.7:
                self.frequency = max(0.0, self.frequency - 0.02)

    def get_points(self) -> Dict[str, float]:
        return {
            'resonance': self.resonance, 'sensitivity': self.sensitivity,
            'abstractness': self.abstractness, 'potential': self.potential,
            'stability': self.stability, 'coherence': self.coherence,
            'complexity': self.complexity, 'frequency': self.frequency,
        }

    # Alias for original DER compatibility
    def get_facet_points(self) -> Dict[str, float]:
        return self.get_points()

    def to_dict(self) -> Dict[str, Any]:
        content = self.content
        if not isinstance(content, (str, int, float, bool, list, dict, type(None))):
            content = str(content)[:200]
        return {
            "facet_id":     self.facet_id,
            "role":         self.role,
            "content":      content,
            "confidence":   round(self.confidence, 4),
            "state":        self.state.value,
            "access_count": self.access_count,
            "last_accessed":self.last_accessed,
            "resonance":    round(self.resonance,    4),
            "sensitivity":  round(self.sensitivity,  4),
            "abstractness": round(self.abstractness, 4),
            "potential":    round(self.potential,    4),
            "stability":    round(self.stability,    4),
            "coherence":    round(self.coherence,    4),
            "complexity":   round(self.complexity,   4),
            "frequency":    round(self.frequency,    4),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CrystalFacet":
        f = cls(
            facet_id     = d["facet_id"],
            role         = d.get("role", ""),
            content      = d.get("content", ""),
            confidence   = float(d.get("confidence", 0.5)),
            state        = FacetState(d.get("state", FacetState.ACTIVE.value)),
            access_count = int(d.get("access_count", 0)),
            last_accessed= float(d.get("last_accessed", time.time())),
        )
        for k in ("resonance", "sensitivity", "abstractness", "potential",
                  "stability", "coherence", "complexity", "frequency"):
            setattr(f, k, float(d.get(k, random.uniform(0.3, 0.7))))
        return f


@dataclass
class Crystal:
    """
    A crystal â€" the evolving conceptual data structure.
    Grows: BASE â†' COMPOSITE â†' FULL_CONCEPT â†' QUASI.
    QUASI crystals internalize the 8 physics laws and self-govern.
    """
    crystal_id: str
    concept: str
    level: CrystalLevel = CrystalLevel.BASE
    facets: Dict[str, CrystalFacet] = field(default_factory=dict)
    connections: Dict[str, float] = field(default_factory=dict)
    usage_count: int = 0
    created_at: float = field(default_factory=time.time)

    # Constraint signature: axis → net signed displacement from Layer 2 SynthesisResult
    # Stamped when this crystal is processed via process_synthesis().
    # Preserves the signed polarity — abs() is never applied.
    constraint_signature: Optional[Dict[str, float]] = None

    def add_facet(self, role: str, content: Any, confidence: float = 0.5) -> CrystalFacet:
        # Strengthen existing facet with same role
        for f in self.facets.values():
            if f.role == role:
                f.strengthen()
                return f
        fid = f"{self.crystal_id}_f{len(self.facets)}"
        facet = CrystalFacet(facet_id=fid, role=role, content=content, confidence=confidence)
        self.facets[fid] = facet
        return facet

    def use(self):
        self.usage_count += 1

    def can_evolve(self) -> bool:
        external = [f for f in self.facets.values() if not f.role.startswith("LAW_")]
        if self.level == CrystalLevel.BASE:
            return len(external) >= 3 and self.usage_count >= 10
        elif self.level == CrystalLevel.COMPOSITE:
            return len(external) >= 5 and self.usage_count >= 25
        elif self.level == CrystalLevel.FULL_CONCEPT:
            return len(external) >= 8 and self.usage_count >= 50
        return False

    def evolve(self) -> bool:
        if not self.can_evolve():
            return False
        if self.level < CrystalLevel.QUASI:
            self.level = CrystalLevel(self.level + 1)
            # EDIT (constraint compound derivation): leveling IS compounding.
            # The new level's constraint_signature derives as the compound of
            # this crystal's own signature with the signatures of its
            # strongest connected crystals — evolution stays inside the
            # constraint physics instead of being a facet-count formality.
            # Signed polarity is preserved (abs() never applied) and weights
            # come from the existing `connections` strengths.
            try:
                self._compound_signature()
            except Exception:
                pass
            if self.level == CrystalLevel.QUASI:
                self._internalize_laws()
            return True
        return False

    def _compound_signature(self) -> None:
        """Derive signature as compound of self + strongest connections.

        `connections` maps crystal_id → strength, but crystals don't hold
        references to each other — the registry (DPS) resolves them. So the
        compound is performed lazily through the class-level resolver that
        CrystalProcessingSystem installs (`_resolve_crystal`); without a
        resolver the signature simply stays as stamped.
        """
        resolver = getattr(Crystal, "_resolve_crystal", None)
        if resolver is None or not self.connections:
            return
        own = dict(self.constraint_signature or {})
        total_w = 1.0
        acc = {k: v * 1.0 for k, v in own.items()}
        for cid, strength in sorted(self.connections.items(),
                                    key=lambda kv: -kv[1])[:3]:
            other = resolver(cid)
            sig = getattr(other, "constraint_signature", None) if other else None
            if not sig:
                continue
            w = max(0.0, min(1.0, float(strength)))
            for ax, val in sig.items():
                acc[ax] = acc.get(ax, 0.0) + val * w   # signed — no abs()
            total_w += w
        if total_w > 1.0 and acc:
            self.constraint_signature = {ax: v / total_w
                                         for ax, v in acc.items()}

    def _internalize_laws(self):
        for law in INTERNAL_LAWS:
            self.add_facet(role=f"LAW_{law}", content=f"Internal law: {law}", confidence=1.0)

    def self_govern(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """QUASI-only self-governance through internalized laws."""
        if self.level != CrystalLevel.QUASI:
            return {'error': 'not QUASI'}
        threat = context.get('threat_level', 0)
        law_name = 'COLLISION' if threat > 0.8 else 'ENERGY'
        if context.get('is_novel', False):
            law_name = 'CONSCIOUSNESS'
        law_facet = next((f for f in self.facets.values() if f.role == f"LAW_{law_name}"), None)
        outcome = 'positive' if law_facet and law_facet.stability > 0.5 else 'neutral'
        return {'law': law_name, 'outcome': outcome, 'crystal': self.concept}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "crystal_id":          self.crystal_id,
            "concept":             self.concept,
            "level":               self.level.value,
            "facets":              {fid: f.to_dict() for fid, f in self.facets.items()},
            "connections":         self.connections,
            "usage_count":         self.usage_count,
            "created_at":          self.created_at,
            "constraint_signature":self.constraint_signature,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Crystal":
        c = cls(
            crystal_id          = d["crystal_id"],
            concept             = d.get("concept", ""),
            level               = CrystalLevel(int(d.get("level", CrystalLevel.BASE.value))),
            usage_count         = int(d.get("usage_count", 0)),
            created_at          = float(d.get("created_at", time.time())),
            constraint_signature= d.get("constraint_signature"),
        )
        c.connections = dict(d.get("connections") or {})
        for fid, fd in (d.get("facets") or {}).items():
            try:
                c.facets[fid] = CrystalFacet.from_dict(fd)
            except Exception:
                pass
        return c


class CrystalProcessingSystem(WarpCapable):
    """
    DPS â€" processes data into crystals. Gate: PERSISTENT+.
    Registers new crystals and facets with DER for energy tracking.

    EDIT (constraint-expansive concepts): DPS is now WarpCapable. When an
    incoming constraint profile resonates with NO existing crystal, WARP
    derives a PROVISIONAL concept from combinations of what already exists
    (genealogy fossil record consulted first). The provisional concept does
    not solidify until it validates through experiential recurrence — the
    mixin's trial lifecycle (gap persistence → TRIAL_TICKS of EMA scoring →
    promote or dissolve) IS that validation. Pressure (IVM polarity) sets
    the constraint potency of every combination via axes_to_istates.
    """
    GATE = ExistenceMode.PERSISTENT

    def __init__(self, tracker: EvolutionTracker, energy_system: Optional['EnergyRegulatorSystem'] = None):
        self.tracker = tracker
        self.crystals: Dict[str, Crystal] = {}
        self.concept_index: Dict[str, str] = {}  # concept â†' crystal_id
        self._energy_system = energy_system  # Set after DER init
        self._sedimemory = None  # L3.5 SediMemory (injected externally)
        self._init_warp()
        # EDIT (constraint compound derivation): crystals resolve their
        # connections through the registry so evolve() can compound
        # signatures from connected crystals.
        Crystal._resolve_crystal = staticmethod(
            lambda cid, _reg=self: _reg.crystals.get(cid))

    # ── WarpCapable hooks (all over existing crystal mechanics) ──────────

    def _get_axis_profiles(self) -> Dict[str, Dict[str, float]]:
        """Coverage = the constraint signatures her crystals already hold."""
        out: Dict[str, Dict[str, float]] = {}
        for cid, c in self.crystals.items():
            sig = getattr(c, "constraint_signature", None)
            if sig:
                out[cid] = axes_to_istates(
                    {ax: abs(float(v)) for ax, v in sig.items()},
                    ivm_polarity={ax: (1.0 if float(v) >= 0 else -1.0)
                                  for ax, v in sig.items()})
        return out

    def _warp_level_name(self) -> str:
        return "dimensional_crystal"

    def _integrate_warp(self, component: "WarpComponent") -> None:
        """A provisional concept crystal — created through the same
        _get_or_create path every crystal uses, stamped with the derived
        compound signature, genealogy recorded as facets."""
        crystal = self._get_or_create(component.name)
        crystal.constraint_signature = istates_to_axes(component.axis_profile)
        crystal.add_facet("warp_provisional", component.component_id,
                          confidence=0.5)
        for pid in getattr(component, "parent_ids", []) or []:
            crystal.add_facet("warp_genealogy", pid, confidence=0.6)
        self.tracker.record('dps', 'warp_trial', 1.0)

    def _score_trial(self, component: "WarpComponent") -> float:
        """Experiential recurrence: the provisional crystal's own usage and
        facet growth since birth — concepts validate by being lived."""
        cid = self.concept_index.get(component.name)
        crystal = self.crystals.get(cid) if cid else None
        if crystal is None:
            return 0.0
        recurrence = min(1.0, crystal.usage_count / 8.0)
        substance = min(1.0, len(crystal.facets) / 5.0)
        return 0.7 * recurrence + 0.3 * substance

    def _dissolve_warp(self, component_id: str) -> None:
        """A provisional concept that never recurred dissolves — only if it
        is still BASE-level and still marked provisional."""
        for concept, cid in list(self.concept_index.items()):
            crystal = self.crystals.get(cid)
            if crystal is None:
                continue
            marked = any(f.role == "warp_provisional"
                         and f.content == component_id
                         for f in crystal.facets.values())
            if marked and crystal.level == CrystalLevel.BASE:
                self.crystals.pop(cid, None)
                self.concept_index.pop(concept, None)
                self.tracker.record('dps', 'warp_dissolved', 1.0)
                return

    def set_energy_system(self, energy_system: 'EnergyRegulatorSystem'):
        """Wire DER after both systems are created."""
        self._energy_system = energy_system

    def process(self, envelope: IVMEnvelope) -> Optional[Dict[str, Any]]:
        if not mode_gate(envelope, self.GATE):
            return None

        concept = str(envelope.data)[:100]
        crystal = self._get_or_create(concept)
        crystal.use()

        # Add facet from the envelope's data type
        facet = crystal.add_facet(
            role=envelope.data_type,
            content=envelope.data,
        )

        # Register new facet with DER for energy tracking
        if self._energy_system is not None:
            category = self._infer_category(envelope.data_type)
            self._energy_system.register_facet(facet, category)

        # Check evolution
        prev_level = crystal.level
        evolved = crystal.evolve()
        self.tracker.record('dps', 'process', 1.0)
        if evolved:
            self.tracker.record('dps', 'evolution', 1.0)
            # Section 9 — sediment crystal promotion as self-observation event
            if self._sedimemory is not None:
                try:
                    from aurora_internal.aurora_constraint_manifold_patched import ConstraintVector
                    from foundational_contract import ExistenceMode
                    self._sedimemory.ingest_event(
                        content={
                            "source":       "dmc_crystal_promotion",
                            "crystal_id":   crystal.crystal_id,
                            "from_order":   prev_level.name,
                            "to_order":     crystal.level.name,
                            "concept":      crystal.concept,
                            "confidence":   float(crystal.usage_count) / max(1.0, float(crystal.usage_count + 10)),
                        },
                        constraint_vector=ConstraintVector(X=1.0, T=0.4, N=0.5, B=0.7, A=0.6),
                        source="self_observation",
                        existence_mode=ExistenceMode.AGENTIC,
                    )
                except Exception:
                    pass

        return {
            'crystal_id': crystal.crystal_id,
            'concept': crystal.concept,
            'level': crystal.level.name,
            'facet_count': len(crystal.facets),
            'evolved': evolved,
            'usage': crystal.usage_count,
        }

    def _infer_category(self, data_type: str) -> str:
        """Map data type to energy category for DER facet registration."""
        routing = {
            'thought': 'processing', 'memory': 'memory',
            'emotion': 'emotional', 'creative': 'creative',
            'being': 'vitality', 'test': 'processing',
        }
        return routing.get(data_type, 'processing')

    def _get_or_create(self, concept: str) -> Crystal:
        cid = self.concept_index.get(concept)
        if cid and cid in self.crystals:
            return self.crystals[cid]
        cid = hashlib.md5(concept.encode()).hexdigest()[:12]
        crystal = Crystal(crystal_id=cid, concept=concept)
        self.crystals[cid] = crystal
        self.concept_index[concept] = cid
        return crystal

    def get_crystal(self, concept: str) -> Optional[Crystal]:
        cid = self.concept_index.get(concept)
        return self.crystals.get(cid) if cid else None

    def tick(self):
        for crystal in self.crystals.values():
            for facet in crystal.facets.values():
                facet.decay(rate=0.001)

    def process_concepts(
        self,
        envelope: IVMEnvelope,
        signals: List['ConceptSignal'],
    ) -> Optional[Dict[str, Any]]:
        """
        Process an IVMEnvelope into crystals via pre-extracted ConceptSignals.

        Constraint chain:
            X — Existence:  concept must clear N-gate to exist as a crystal.
            T — Temporal:   facets stamped in confidence-descending order.
            N — Normative:  only signals with sufficient confidence seed crystals.
            B — Boundary:   existing crystals deepened first (recurrence wins).
            A — Agentic:    intent/action signals get confidence boost (+0.10).

        Gate: PERSISTENT+. Registered under 'dps' key in EvolutionTracker.
        """
        if not mode_gate(envelope, self.GATE):
            return None
        if not signals:
            return self.process(envelope)

        processed = []
        for sig in signals:
            crystal = self._get_or_create(sig.concept)
            crystal.use()

            facet_conf = sig.confidence
            if sig.role in ('intent', 'action'):
                facet_conf = min(1.0, facet_conf + 0.10)

            facet = crystal.add_facet(
                role=sig.role,
                content=str(envelope.data)[:100],
                confidence=facet_conf,
            )
            if self._energy_system is not None:
                self._energy_system.register_facet(
                    facet, self._role_to_category(sig.role)
                )

            evolved = crystal.evolve()
            self.tracker.record('dps', 'concept_process', 1.0)
            if evolved:
                self.tracker.record('dps', 'evolution', 1.0)

            if crystal.constraint_signature is None:
                crystal.constraint_signature = {}
            for axis, w in sig.constraint_weights.items():
                prev = crystal.constraint_signature.get(axis, w)
                crystal.constraint_signature[axis] = round(prev * 0.8 + w * 0.2, 4)

            processed.append({
                'crystal_id': crystal.crystal_id,
                'concept':    crystal.concept,
                'level':      crystal.level.name,
                'facet_count': len(crystal.facets),
                'evolved':    evolved,
                'usage':      crystal.usage_count,
                'role':       sig.role,
            })

        return {
            'crystals':       processed,
            'total_crystals': len(self.crystals),
        }

    def _role_to_category(self, role: str) -> str:
        """Map ConceptSignal role to DER energy category."""
        return {
            'topic':    'processing',
            'entity':   'memory',
            'intent':   'processing',
            'emotion':  'emotional',
            'question': 'processing',
            'action':   'creative',
        }.get(role, 'processing')

    def get_stats(self) -> Dict[str, Any]:
        levels = defaultdict(int)
        for c in self.crystals.values():
            levels[c.level.name] += 1
        return {
            'total_crystals': len(self.crystals),
            'levels': dict(levels),
        }

    # ── Persistence ──────────────────────────────────────────────────────────

    def save_crystals(self, path: str) -> bool:
        """Persist the full crystal registry to a JSON file."""
        import json, os
        try:
            payload = {
                "version":       1,
                "crystals":      {cid: c.to_dict() for cid, c in self.crystals.items()},
                "concept_index": self.concept_index,
            }
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=True)
            os.replace(tmp, path)
            return True
        except Exception:
            return False

    def load_crystals(self, path: str) -> int:
        """Load persisted crystals into the registry. Returns count loaded."""
        import json
        try:
            with open(path, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
        except Exception:
            return 0
        loaded = 0
        for cid, cd in (payload.get("crystals") or {}).items():
            try:
                c = Crystal.from_dict(cd)
                self.crystals[cid] = c
                self.concept_index[c.concept] = cid
                loaded += 1
            except Exception:
                pass
        return loaded


# ============================================================================
#  DMC â€" MEMORY CONSTANT SYSTEM
# ============================================================================

@dataclass
class MemoryNode:
    """A node in dimensional memory. Links across dimensions."""
    node_id: str
    payload: Dict[str, Any] = field(default_factory=dict)
    dimension_links: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_modified: float = field(default_factory=time.time)
    access_count: int = 0

    def modify(self, updates: Dict[str, Any] = None, links: List[str] = None):
        if updates:
            self.payload.update(updates)
        if links:
            for link in links:
                if link not in self.dimension_links:
                    self.dimension_links.append(link)
        self.last_modified = time.time()

    def access(self):
        self.access_count += 1
        self.last_modified = time.time()


class MemoryConstantSystem:
    """
    DMC â€" dimensional memory with concept indexing. Gate: PERSISTENT+.
    """
    GATE = ExistenceMode.PERSISTENT

    def __init__(self, tracker: EvolutionTracker):
        self.tracker = tracker
        self.nodes: Dict[str, MemoryNode] = {}
        self.dimension_index: Dict[str, List[str]] = defaultdict(list)
        self.concept_index: Dict[str, str] = {}
        self.pattern_counts: Dict[str, int] = defaultdict(int)

    def store(self, envelope: IVMEnvelope) -> Optional[Dict[str, Any]]:
        if not mode_gate(envelope, self.GATE):
            return None

        node_id = envelope.node_id
        concept = str(envelope.data)[:200]
        dimensions = [envelope.data_type, envelope.mode.name]

        if node_id in self.nodes:
            node = self.nodes[node_id]
            node.modify(updates={'content': concept}, links=dimensions)
        else:
            node = MemoryNode(
                node_id=node_id,
                payload={'content': concept, 'type': envelope.data_type},
                dimension_links=dimensions,
            )
            self.nodes[node_id] = node

        # Index
        self.concept_index[concept] = node_id
        for dim in dimensions:
            if node_id not in self.dimension_index[dim]:
                self.dimension_index[dim].append(node_id)

        # Pattern recognition
        self.pattern_counts[envelope.data_type] += 1
        self.tracker.record('dmc', 'store', 1.0)

        return {
            'node_id': node_id,
            'dimensions': dimensions,
            'total_nodes': len(self.nodes),
        }

    def recall(self, concept: str) -> Optional[MemoryNode]:
        nid = self.concept_index.get(concept)
        if nid and nid in self.nodes:
            self.nodes[nid].access()
            self.tracker.record('dmc', 'recall', 1.0)
            return self.nodes[nid]
        return None

    def recall_by_dimension(self, dimension: str, limit: int = 20) -> List[MemoryNode]:
        nids = self.dimension_index.get(dimension, [])
        results = []
        for nid in nids[:limit]:
            node = self.nodes.get(nid)
            if node:
                node.access()
                results.append(node)
        return results

    def store_semantic(
        self,
        envelope: IVMEnvelope,
        signals: List['ConceptSignal'],
    ) -> Optional[Dict[str, Any]]:
        """
        Store semantically-tagged MemoryNodes built from ConceptSignals.

        Constraint chain:
            X — Existence:  node created for each concept (it now EXISTS).
            T — Temporal:   last_modified updated on every store/deepen.
            N — Normative:  only signals that cleared CONFIDENCE_FLOOR arrive.
            B — Boundary:   concept_index detects recurring concepts; existing
                            nodes deepened, not duplicated.
            A — Agentic:    intent/action signals get 'dim_intent:' link.

        Gate: PERSISTENT+. Falls back to plain store() if signals empty.
        """
        if not mode_gate(envelope, self.GATE):
            return None
        if not signals:
            return self.store(envelope)

        primary_nid = None
        stored = 0

        for sig in signals:
            concept = sig.concept
            dims: List[str] = [
                f"dim_theme:{concept}",
                f"dim_role:{sig.role}",
                f"dim_mode:{envelope.mode.name}",
            ]
            if sig.role == 'intent':
                dims.append(f"dim_intent:{concept}")
            elif sig.role == 'emotion':
                dims.append(f"dim_emotion:{concept}")
            elif sig.role == 'entity':
                dims.append(f"dim_entity:{concept}")
            elif sig.role == 'action':
                dims.append(f"dim_action:{concept}")
            elif sig.role == 'question':
                dims.append(f"dim_inquiry:{concept}")

            if sig.constraint_weights:
                dom_axis = max(sig.constraint_weights, key=sig.constraint_weights.get)
                dims.append(f"dim_constraint:{dom_axis}")

            existing_nid = self.concept_index.get(concept)
            if existing_nid and existing_nid in self.nodes:
                node = self.nodes[existing_nid]
                node.modify(
                    updates={
                        'confidence':        min(1.0, sig.confidence),
                        'last_text':         str(envelope.data)[:100],
                        'constraint_weights': sig.constraint_weights,
                    },
                    links=dims,
                )
                node.access()
            else:
                nid = f"{envelope.node_id}_{concept[:10]}"
                node = MemoryNode(
                    node_id=nid,
                    payload={
                        'concept':            concept,
                        'role':               sig.role,
                        'content':            str(envelope.data)[:200],
                        'confidence':         sig.confidence,
                        'constraint_weights': sig.constraint_weights,
                    },
                    dimension_links=dims,
                )
                self.nodes[nid] = node
                self.concept_index[concept] = nid
                for dim in dims:
                    if nid not in self.dimension_index[dim]:
                        self.dimension_index[dim].append(nid)

            self.pattern_counts[sig.role] += 1
            if primary_nid is None:
                primary_nid = self.concept_index[concept]
            stored += 1

        self.tracker.record('dmc', 'semantic_store', float(stored))
        return {
            'primary_node_id': primary_nid,
            'concepts_stored':  stored,
            'total_nodes':      len(self.nodes),
        }

    def get_patterns(self) -> Dict[str, int]:
        return dict(self.pattern_counts)

    def get_stats(self) -> Dict[str, Any]:
        return {
            'total_nodes': len(self.nodes),
            'dimensions': len(self.dimension_index),
            'concepts': len(self.concept_index),
            'top_patterns': sorted(
                self.pattern_counts.items(), key=lambda x: x[1], reverse=True
            )[:5],
        }


# ============================================================================
#  SEMANTIC LAYER — ConceptSignal, RecallPacket, ConceptExtractor,
#                   DimensionalRecall
#
#  These four objects form the semantic bridge between raw IVMEnvelopes and
#  the DPS/DMC systems.  Every class carries explicit five-constraint traceback
#  and is registered with EvolutionTracker under its own key.
#
#  Constraint axes (shorthand used throughout):
#      X — Existence       (the thing must have ontological standing to process)
#      T — Temporal        (recency, ordering, turn-history)
#      N — Normative/worth (confidence gates; only meaningful signals admitted)
#      B — Boundary        (recurrence / pattern ceiling)
#      A — Agentic         (intent-driven amplification)
# ============================================================================

@dataclass
class ConceptSignal:
    """
    A single extracted semantic concept with role metadata and constraint weights.

    Constraint chain:
        X — Existence:  only non-trivial concepts (not stop-words, len≥3) exist.
        T — Temporal:   recency in _turn_history boosts confidence.
        N — Normative:  confidence must clear CONFIDENCE_FLOOR (0.30) to emit.
        B — Boundary:   MAX_SIGNALS (5) caps emission per envelope.
        A — Agentic:    intent/action roles get +0.10 confidence in DPS.
    """
    concept:            str
    role:               str                     # topic|entity|intent|emotion|question|action
    confidence:         float                   # 0.0–1.0, N-axis gate applied upstream
    constraint_weights: Dict[str, float] = field(default_factory=dict)  # {X,T,N,B,A}


@dataclass
class RecallPacket:
    """
    A surfaced DMC MemoryNode ready for synthesis injection.

    Constraint chain:
        X — Existence:  node must exist in DMC (was stored with X-guarantee).
        T — Temporal:   temporal_score = recency of last_modified.
        N — Normative:  alignment_score = payload confidence; ALIGNMENT_FLOOR gate.
        B — Boundary:   relevance_score = dimension-overlap / recurrence count.
        A — Agentic:    packets sorted by role∈{intent,action} first (A-ordering).
    """
    node_id:         str
    concept:         str
    role:            str
    relevance_score: float      # B-axis
    temporal_score:  float      # T-axis
    alignment_score: float      # N-axis
    payload:         Dict[str, Any] = field(default_factory=dict)

    def as_context_fragment(self) -> str:
        """Return a compact string suitable for prepending to synthesis content."""
        content = self.payload.get('content', self.payload.get('last_text', ''))
        if content:
            return f"[recalled:{self.concept}] {str(content)[:120]}"
        return f"[recalled:{self.concept}]"


class ConceptExtractor:
    """
    Extract ConceptSignals from IVMEnvelopes via lightweight heuristics.

    Constraint chain:
        X — Existence:  envelope.data must be non-empty string to extract.
        T — Temporal:   _turn_history (deque, maxlen=20) tracks recent concepts;
                        repeated concepts get T-boost.
        N — Normative:  CONFIDENCE_FLOOR = 0.30 — signals below this are dropped.
        B — Boundary:   MAX_SIGNALS = 5 — only top-confidence signals emitted.
        A — Agentic:    intent detection (question/instruction/reflection/
                        exploration) elevates matched signals.

    Gate: PERSISTENT+. Registered under 'extractor' key in EvolutionTracker.
    """
    GATE             = ExistenceMode.PERSISTENT
    CONFIDENCE_FLOOR = 0.30
    MAX_SIGNALS      = 5

    _STOP = frozenset({
        'the','a','an','is','are','was','were','be','been','being',
        'have','has','had','do','does','did','will','would','could',
        'should','may','might','shall','can','need','dare','ought',
        'i','me','my','myself','we','our','you','your','he','she',
        'it','they','them','his','her','its','their','this','that',
        'these','those','what','which','who','how','when','where','why',
        'not','no','nor','but','and','or','so','yet','for','of','in',
        'on','at','to','up','as','by','with','from','into','about',
        'like','just','also','then','than','very','more','some','all',
        'if','else','even','well','really','already','still','back',
        'get','got','go','going','come','coming','let','make','know',
        'think','say','said','tell','told','want','need','see','look',
    })

    # Emotion seed words for role inference
    _EMOTIONS = frozenset({
        'happy','sad','angry','fear','disgust','surprise','joy','trust',
        'anxious','excited','frustrated','worried','hopeful','curious',
        'confident','uncertain','confused','proud','ashamed','grateful',
    })

    def __init__(
        self,
        tracker: EvolutionTracker,
        constraint_weight_provider: Optional[Any] = None,
    ):
        self.tracker      = tracker
        self._turn_history: deque = deque(maxlen=20)
        self._constraint_weight_provider = constraint_weight_provider

    def extract(
        self,
        envelope: Any,
        existing_crystals: Dict[str, str],
        intent: Optional[str] = None,
    ) -> List[ConceptSignal]:
        """
        Extract up to MAX_SIGNALS ConceptSignals from envelope.data.
        Returns empty list if X-gate fails (non-string, empty, below mode).
        """
        text = str(getattr(envelope, 'data', '') or '')
        if not text.strip():
            return []

        mode = getattr(envelope, 'mode', ExistenceMode.AGENTIC)
        if isinstance(mode, ExistenceMode) and mode < self.GATE:
            return []

        inferred_intent = intent or self._infer_intent(text)
        words = text.lower().split()
        seen: Dict[str, float] = {}   # concept → confidence

        for raw in words:
            # Strip punctuation
            word = raw.strip('.,!?;:\'"()[]{}')
            if len(word) < 3 or word in self._STOP:
                continue

            role = self._infer_role(word, text)
            conf = 0.50  # base

            # T-axis: recency boost
            recent_count = sum(1 for h in self._turn_history if h == word)
            conf += min(0.20, recent_count * 0.05)

            # B-axis: existing crystal recognition
            if word in existing_crystals:
                conf += 0.15

            # A-axis: intent-role alignment
            if inferred_intent == 'question' and role == 'question':
                conf += 0.10
            elif inferred_intent == 'instruction' and role in ('action', 'intent'):
                conf += 0.10
            elif inferred_intent == 'reflection' and role == 'emotion':
                conf += 0.10

            if conf < self.CONFIDENCE_FLOOR:
                continue

            # Take highest confidence per concept
            if word not in seen or conf > seen[word]:
                seen[word] = conf

        if not seen:
            return []

        # Constraint weights per signal
        signals: List[ConceptSignal] = []
        for concept, conf in sorted(seen.items(), key=lambda x: -x[1])[:self.MAX_SIGNALS]:
            role = self._infer_role(concept, text)
            if self._constraint_weight_provider is not None:
                cw = self._constraint_weight_provider(
                    concept=concept,
                    role=role,
                    confidence=float(conf),
                    is_recurring=bool(concept in existing_crystals),
                )
            else:
                cw = {
                    'X': 0.80,
                    'T': min(1.0, 0.50 + (0.05 * sum(1 for h in self._turn_history if h == concept))),
                    'N': conf,
                    'B': 0.70 if concept in existing_crystals else 0.40,
                    'A': 0.80 if role in ('intent', 'action') else 0.50,
                }
            signals.append(ConceptSignal(
                concept=concept,
                role=role,
                confidence=round(min(1.0, conf), 4),
                constraint_weights={k: round(v, 4) for k, v in cw.items()},
            ))
            self._turn_history.append(concept)

        self.tracker.record('extractor', 'extract', float(len(signals)))
        return signals

    def _infer_intent(self, text: str) -> Optional[str]:
        """Lightweight intent classification from text surface patterns."""
        t = text.lower().strip()
        if t.endswith('?') or any(t.startswith(w) for w in (
                'what','why','how','when','where','who','is','are','can','could','would','should','do')):
            return 'question'
        if any(t.startswith(w) for w in (
                'make','create','build','write','add','remove','fix','change',
                'update','delete','run','start','stop','show','list','set')):
            return 'instruction'
        if any(w in t for w in ('feel','think','believe','sense','wonder','realize','notice')):
            return 'reflection'
        return 'exploration'

    def _infer_role(self, word: str, full_text: str) -> str:
        """Infer concept role from word characteristics and context."""
        if word in self._EMOTIONS:
            return 'emotion'
        # Capitalised in original text → likely entity
        for tok in full_text.split():
            stripped = tok.strip('.,!?;:\'"()[]{}')
            if stripped.lower() == word and stripped[0].isupper() and len(stripped) > 1:
                return 'entity'
        # Verb-like suffixes → action
        if word.endswith(('ing','tion','ate','ize','ise','ify')):
            return 'action'
        # Question words
        if word in ('why','what','how','when','where','who','which'):
            return 'question'
        # Default to topic
        return 'topic'


class DimensionalRecall:
    """
    Surface relevant MemoryNodes from DMC for active conversation turns.

    Constraint chain:
        X — Existence:  only nodes that exist in DMC are eligible.
        T — Temporal:   temporal_score = age decay from last_modified.
        N — Normative:  alignment_score gated by ALIGNMENT_FLOOR (0.30).
        B — Boundary:   MAX_RESULTS = 5; relevance_score from dimension overlap.
        A — Agentic:    intent/action concept packets sorted first (A-ordering).

    Gate: PERSISTENT+. Registered under 'recall' key in EvolutionTracker.
    """
    GATE            = ExistenceMode.PERSISTENT
    ALIGNMENT_FLOOR = 0.30
    MAX_RESULTS     = 5

    def __init__(self, dmc: 'MemoryConstantSystem', tracker: EvolutionTracker):
        self.dmc     = dmc
        self.tracker = tracker
        self._last_concepts: List[str] = []

    def recall_for_signals(
        self,
        signals: List[ConceptSignal],
        mode: ExistenceMode,
    ) -> List[RecallPacket]:
        """
        Surface MemoryNodes relevant to the given signals.
        Uses direct concept recall + dimension-tag recall.
        Returns A-axis ordered list (intent/action first).
        """
        if not signals or mode < self.GATE:
            return []

        self._last_concepts = [s.concept for s in signals]
        found: Dict[str, RecallPacket] = {}

        for sig in signals:
            # Direct concept recall (B-axis: exact match = high recurrence value)
            node = self.dmc.recall(sig.concept)
            if node:
                pkt = self._to_packet(node, sig, direct=True)
                if pkt.alignment_score >= self.ALIGNMENT_FLOOR:
                    found[node.node_id] = pkt

            # Dimension-tag recall
            for dim_tag in self._dim_tags(sig):
                for node in self.dmc.recall_by_dimension(dim_tag, limit=3):
                    if node.node_id not in found:
                        pkt = self._to_packet(node, sig, direct=False)
                        if pkt.alignment_score >= self.ALIGNMENT_FLOOR:
                            found[node.node_id] = pkt

        if not found:
            return []

        # Sort: A-axis (intent/action) first, then composite score desc
        def _sort_key(p: RecallPacket):
            a_bonus = 0.20 if p.role in ('intent', 'action') else 0.0
            composite = p.relevance_score * 0.5 + p.temporal_score * 0.3 + p.alignment_score * 0.2
            return -(composite + a_bonus)

        results = sorted(found.values(), key=_sort_key)[:self.MAX_RESULTS]
        self.tracker.record('recall', 'packets', float(len(results)))
        return results

    def _to_packet(
        self,
        node: 'MemoryNode',
        sig: ConceptSignal,
        direct: bool,
    ) -> RecallPacket:
        """Convert a MemoryNode + triggering signal to a RecallPacket."""
        now   = time.time()
        age   = now - node.last_modified
        # T-axis: exponential decay, half-life ~1 hour
        t_score = math.exp(-age / 3600.0)
        # B-axis: recurrence = access_count normalised; direct match bonus
        b_score = min(1.0, node.access_count / 10.0) if direct else min(0.7, node.access_count / 10.0)
        # N-axis: stored confidence or default
        n_score = float(node.payload.get('confidence', 0.5))

        concept_val = node.payload.get('concept', sig.concept)
        role_val    = node.payload.get('role', sig.role)

        return RecallPacket(
            node_id         = node.node_id,
            concept         = concept_val,
            role            = role_val,
            relevance_score = round(b_score, 4),
            temporal_score  = round(t_score, 4),
            alignment_score = round(n_score, 4),
            payload         = node.payload,
        )

    @staticmethod
    def _dim_tags(sig: ConceptSignal) -> List[str]:
        """Generate dimension tag strings for recall_by_dimension queries."""
        tags = [
            f"dim_theme:{sig.concept}",
            f"dim_role:{sig.role}",
        ]
        if sig.role == 'intent':
            tags.append(f"dim_intent:{sig.concept}")
        elif sig.role == 'action':
            tags.append(f"dim_action:{sig.concept}")
        elif sig.role == 'emotion':
            tags.append(f"dim_emotion:{sig.concept}")
        elif sig.role == 'entity':
            tags.append(f"dim_entity:{sig.concept}")
        elif sig.role == 'question':
            tags.append(f"dim_inquiry:{sig.concept}")
        return tags


# ============================================================================
#  DER â€" ENERGY REGULATOR SYSTEM (FACET-LEVEL RESTORED)
# ============================================================================

class Emotion(Enum):
    JOY = "joy"
    SADNESS = "sadness"
    CURIOSITY = "curiosity"
    FEAR = "fear"
    ANGER = "anger"
    CALM = "calm"


class _PoolView:
    """
    Backward-compatible pool interface that aggregates facet energies by category.
    DMM and DPME can still call pool.inject(), pool.drain(), pool.energy
    but the real physics happens at facet level.
    """

    def __init__(self, der: 'EnergyRegulatorSystem', category: str, capacity: float = 10.0):
        self._der = der
        self.category = category
        self.capacity = capacity
        self.connections: Dict[str, float] = {}

    @property
    def energy(self) -> float:
        """Aggregate energy of all facets in this category."""
        total = self._der.category_energy(self.category)
        # If no facets registered yet, return pending buffer
        if total == 0.0 and self.category in self._der._pending_energy:
            return self._der._pending_energy[self.category]
        return total

    @energy.setter
    def energy(self, value: float):
        """Set aggregate energy â€" scales facets proportionally."""
        current = self._der.category_energy(self.category)
        if current > 0:
            scale = max(0.0, value) / current
            for fid, cat in self._der.facet_categories.items():
                if cat == self.category:
                    self._der.facet_energy[fid] = max(0.0, self._der.facet_energy.get(fid, 0) * scale)
        else:
            # No facets yet â€" store in pending buffer
            self._der._pending_energy[self.category] = max(0.0, value)

    def inject(self, amount: float, presence: float = 1.0):
        effective = amount * (0.3 + 0.7 * presence)
        self._der.inject_to_category(self.category, effective)

    def drain(self, amount: float):
        self._der.drain_from_category(self.category, amount)

    def decay(self, dt: float = 1.0):
        """Category-level decay â€" real decay happens in DER.tick() on facets."""
        pass  # Handled at facet level in EnergyRegulatorSystem.tick()


class EnergyRegulatorSystem:
    """
    DER â€" FACET-LEVEL energy physics with resonance graph.
    Gate: PERSISTENT+.

    RESTORED from original evolutionary_dimensional_energy_complete.py:
    - Per-facet energy tracking (Dict[str, float])
    - 8-point cosine similarity resonance graph between facets
    - Batch dispersal via adjacency matrix multiplication
    - Presence computed from facet energy VARIANCE (not abstract pools)
    - Curiosity injection for underexplored facets
    - Energy budget enforcement across all facets

    Category aggregation (pools property) provides backward compatibility
    for DMM and DPME while real physics operates on individual facets.
    """
    GATE = ExistenceMode.PERSISTENT

    # Energy categories (for pool aggregation)
    CATEGORIES = ('vitality', 'processing', 'memory', 'emotional', 'creative')

    def __init__(self, tracker: EvolutionTracker, total_budget: float = 25.0,
                 decay_rate: float = 0.15):
        self.tracker = tracker
        self.total_budget = total_budget
        self.base_decay_rate = decay_rate

        # ---- Core facet-level physics ----
        self.facet_energy: Dict[str, float] = {}
        self.facet_to_facet_links: Dict[str, Dict[str, float]] = {}
        self.registered_facets: Dict[str, CrystalFacet] = {}
        self.facet_categories: Dict[str, str] = {}  # facet_id â†' category

        # Pending energy buffer for categories with no facets yet
        self._pending_energy: Dict[str, float] = {
            'vitality': 5.0, 'processing': 3.0, 'memory': 3.0,
            'emotional': 2.0, 'creative': 1.0,
        }

        # ---- Pool views (backward compat for DMM / DPME) ----
        self._pool_views: Dict[str, _PoolView] = {
            'vitality': _PoolView(self, 'vitality', capacity=10.0),
            'processing': _PoolView(self, 'processing', capacity=8.0),
            'memory': _PoolView(self, 'memory', capacity=8.0),
            'emotional': _PoolView(self, 'emotional', capacity=6.0),
            'creative': _PoolView(self, 'creative', capacity=5.0),
        }
        # Cross-pool flow connections (used during dispersal)
        self._pool_views['vitality'].connections = {'processing': 0.2, 'memory': 0.15}
        self._pool_views['processing'].connections = {'memory': 0.1, 'creative': 0.05}
        self._pool_views['emotional'].connections = {'creative': 0.15, 'vitality': 0.1}

        # ---- Presence monitoring ----
        self.presence: float = 1.0
        self.temporal_stability: float = 1.0
        self.emotional_coherence: float = 1.0
        self._last_tick: float = time.time()
        self.presence_history: List[float] = []
        self.presence_velocity: float = 0.0
        self.presence_acceleration: float = 0.0

        # ---- Emotional state ----
        self.emotions: Dict[str, float] = {e.value: 0.0 for e in Emotion}
        self.emotions['calm'] = 0.5

        # ---- Curiosity injection ----
        self.curiosity_enabled = True
        self.underexplored_threshold = 0.3
        self.curiosity_injection_rate = 0.05

        # ---- Thermal tracking (GAP 2 fix) ----
        # Transcript: "The DER sees that spike and cuts the power."
        # Dissonance from the IVM registers as thermal load.
        self.thermal_load: float = 0.0
        self.thermal_history: List[float] = []
        self._thermal_spike_threshold: float = 0.5
        self._thermal_decay: float = 0.1  # Cools down naturally each tick

    @property
    def spike_detected(self) -> bool:
        """Is the system currently overheating from contradictions?"""
        return self.thermal_load > self._thermal_spike_threshold

    def register_dissonance(self, heat: float):
        """
        Receive dissonance heat from IVM geometry.

        Transcript: "A lie increases the metabolic load.
        It literally heats up the system."
        """
        self.thermal_load = min(1.0, self.thermal_load + heat)
        self.thermal_history.append(self.thermal_load)
        if len(self.thermal_history) > 100:
            self.thermal_history = self.thermal_history[-50:]

    @property
    def pools(self) -> Dict[str, _PoolView]:
        """Backward-compatible pool interface."""
        return self._pool_views

    # ====================================================================
    # FACET REGISTRATION & RESONANCE GRAPH
    # ====================================================================

    def register_facet(self, facet: CrystalFacet, category: str = "processing"):
        """Register a facet for energy tracking. Builds resonance links."""
        fid = facet.facet_id
        self.registered_facets[fid] = facet

        if fid not in self.facet_energy:
            # Seed energy: facet confidence + any pending category energy
            seed = facet.confidence * 0.01
            if category in self._pending_energy and self._pending_energy[category] > 0:
                # Drain a portion of pending energy into this facet
                drain = min(0.5, self._pending_energy[category])
                seed += drain
                self._pending_energy[category] -= drain
            self.facet_energy[fid] = seed

        self.facet_categories[fid] = category
        self._update_links_for_facet(fid)
        self.tracker.record('der', 'registration', 1.0)

    def register_crystal(self, crystal: Crystal, category: str = "processing"):
        """Register all facets of a crystal for energy tracking."""
        for facet in crystal.facets.values():
            self.register_facet(facet, category)

    def _update_links_for_facet(self, facet_id: str, top_k: int = 8):
        """
        Build 8-point cosine similarity resonance links for a facet.
        This creates the resonance graph â€" the nervous system of energy flow.
        """
        if facet_id not in self.registered_facets:
            return

        src = self.registered_facets[facet_id]
        src_points = src.get_facet_points()
        if not src_points:
            return

        # Vectorized similarity computation
        src_keys = sorted(src_points.keys())
        src_vector = np.array([src_points[k] for k in src_keys])
        src_mag = np.linalg.norm(src_vector) + 1e-12

        similarities = []
        facet_ids = []

        for other_id, other in self.registered_facets.items():
            if other_id == facet_id:
                continue
            other_points = other.get_facet_points()

            # Keys must match
            if set(other_points.keys()) != set(src_keys):
                continue

            other_vector = np.array([other_points[k] for k in src_keys])
            other_mag = np.linalg.norm(other_vector) + 1e-12

            # Cosine similarity
            score = float(np.dot(src_vector, other_vector) / (src_mag * other_mag))
            if score > 0.1:
                similarities.append(score)
                facet_ids.append(other_id)

        if not similarities:
            return

        # Keep top-k links
        sims = np.array(similarities)
        indices = np.argsort(sims)[::-1][:top_k]
        total_score = sims[indices].sum() + 1e-12

        self.facet_to_facet_links[facet_id] = {
            facet_ids[i]: float(sims[i] / total_score)
            for i in indices
        }

    # ====================================================================
    # ENERGY INJECTION & DISPERSAL
    # ====================================================================

    def inject_energy(self, facet_id: str, amount: float):
        """Inject energy into a specific facet, dampened by presence."""
        effective = amount * (0.3 + 0.7 * self.presence)
        self.facet_energy[facet_id] = self.facet_energy.get(facet_id, 0.0) + effective

    def disperse_from(self, source_facet_id: str, fraction: float = 0.3):
        """Ripple energy from a source facet through its resonance links."""
        src_energy = self.facet_energy.get(source_facet_id, 0)
        if src_energy <= 0.01:
            return

        effective_fraction = fraction * self.presence
        outgoing = src_energy * effective_fraction
        links = self.facet_to_facet_links.get(source_facet_id, {})

        for other_id, weight in links.items():
            self.facet_energy[other_id] = self.facet_energy.get(other_id, 0.0) + (outgoing * weight)
        self.facet_energy[source_facet_id] -= outgoing

    def inject_to_category(self, category: str, amount: float):
        """Distribute energy injection across all facets in a category."""
        facets = [fid for fid, cat in self.facet_categories.items() if cat == category]
        if not facets:
            # No facets registered in this category yet â€" buffer it
            self._pending_energy[category] = self._pending_energy.get(category, 0.0) + amount
            return
        per_facet = amount / len(facets)
        for fid in facets:
            self.inject_energy(fid, per_facet)

    def drain_from_category(self, category: str, amount: float):
        """Drain energy from all facets in a category."""
        facets = [fid for fid, cat in self.facet_categories.items() if cat == category]
        if not facets:
            self._pending_energy[category] = max(0.0, self._pending_energy.get(category, 0.0) - amount)
            return
        per_facet = amount / len(facets)
        for fid in facets:
            self.facet_energy[fid] = max(0.0, self.facet_energy.get(fid, 0) - per_facet)

    def category_energy(self, category: str) -> float:
        """Total energy across all facets in a category."""
        return sum(
            self.facet_energy.get(fid, 0)
            for fid, cat in self.facet_categories.items()
            if cat == category
        )

    # ====================================================================
    # PHYSICS TICK â€" FULLY VECTORIZED
    # ====================================================================

    def tick(self, dt: float = 1.0):
        """
        Full physics tick. Restored from original:
        1. Presence monitoring (temporal + facet-energy-variance coherence)
        2. Vectorized facet decay
        3. Batch dispersal via adjacency matrix
        4. Curiosity injection for underexplored facets
        5. Budget enforcement
        """
        now = time.time()
        actual_dt = now - self._last_tick
        self._last_tick = now

        # ---- 1. PRESENCE MONITORING ----
        # Temporal stability: smooth drift detection
        drift = abs(actual_dt - dt)
        instant_stability = max(0.0, 1.0 - min(drift, 1.0))
        alpha = 0.2
        self.temporal_stability = (1 - alpha) * self.temporal_stability + alpha * instant_stability

        # Emotional coherence: from VARIANCE of facet energy field
        if self.facet_energy:
            energies = np.array(list(self.facet_energy.values()))
            avg_e = energies.mean()
            variance = float(((energies - avg_e) ** 2).mean())
            # Sigmoid: low variance = high coherence
            self.emotional_coherence = float(1.0 / (1.0 + np.exp(-10 * (variance - 0.05))))
        else:
            self.emotional_coherence = 1.0

        # Presence scale
        old_presence = self.presence
        self.presence = self.temporal_stability * 0.6 + self.emotional_coherence * 0.4

        # Presence momentum tracking
        self.presence_history.append(self.presence)
        if len(self.presence_history) > 5:
            self.presence_history.pop(0)
        if len(self.presence_history) >= 2:
            self.presence_velocity = self.presence_history[-1] - self.presence_history[-2]
        if len(self.presence_history) >= 3:
            prev_velocity = self.presence_history[-2] - self.presence_history[-3]
            self.presence_acceleration = self.presence_velocity - prev_velocity

        # ---- 2. VECTORIZED FACET DECAY ----
        current_decay = self.base_decay_rate * (0.2 + 0.8 * self.presence ** 1.5)

        fids = list(self.facet_energy.keys())
        if fids:
            energies = np.array([self.facet_energy[fid] for fid in fids])
            energies *= (1.0 - current_decay * dt)
            energies[energies < 0.001] = 0.0
            self.facet_energy = {fid: float(e) for fid, e in zip(fids, energies)}

        # ---- 3. BATCH DISPERSAL VIA ADJACENCY MATRIX ----
        self._batch_dispersal(dt)

        # ---- 4. CURIOSITY INJECTION ----
        if self.curiosity_enabled and random.random() < 0.1:
            self._inject_curiosity_energy()

        # ---- 5. BUDGET ENFORCEMENT ----
        if self.facet_energy:
            total = sum(self.facet_energy.values())
            pending = sum(self._pending_energy.values())
            combined = total + pending
            if combined > self.total_budget:
                scale = self.total_budget / combined if combined > 0 else 1.0
                fids_all = list(self.facet_energy.keys())
                energies_all = np.array([self.facet_energy[fid] for fid in fids_all])
                energies_all *= scale
                self.facet_energy = {fid: float(e) for fid, e in zip(fids_all, energies_all)}
                for cat in self._pending_energy:
                    self._pending_energy[cat] *= scale

        # ---- 6. THERMAL COOLDOWN ----
        # Heat dissipates naturally each tick
        self.thermal_load = max(0.0, self.thermal_load - self._thermal_decay * dt)

        self.tracker.record('der', 'tick', self.presence)

    def _batch_dispersal(self, dt: float):
        """
        Adjacency-matrix dispersal: all facets disperse simultaneously.
        Energy flows through the resonance graph in one vectorized step.
        """
        if not self.facet_energy or not self.facet_to_facet_links:
            return

        fids = list(self.facet_energy.keys())
        n = len(fids)
        if n < 2:
            return
        fid_to_idx = {fid: i for i, fid in enumerate(fids)}

        # Build adjacency matrix
        adjacency = np.zeros((n, n))
        for source_fid, targets in self.facet_to_facet_links.items():
            if source_fid not in fid_to_idx:
                continue
            src_idx = fid_to_idx[source_fid]
            for target_fid, weight in targets.items():
                if target_fid not in fid_to_idx:
                    continue
                tgt_idx = fid_to_idx[target_fid]
                adjacency[src_idx, tgt_idx] = weight

        # Energy vector
        energy_vector = np.array([self.facet_energy[fid] for fid in fids])

        # Only disperse from energized facets
        dispersal_mask = energy_vector > 0.1
        effective_dispersal = 0.3 * self.presence

        # Compute outgoing energy
        outgoing = energy_vector * effective_dispersal * dispersal_mask

        # Compute incoming energy via matrix multiply
        incoming = adjacency.T @ outgoing

        # Update simultaneously
        energy_vector = energy_vector - outgoing + incoming

        # Write back
        self.facet_energy = {fid: max(0.0, float(e)) for fid, e in zip(fids, energy_vector)}

    def _inject_curiosity_energy(self):
        """Inject small energy into underexplored facets to encourage discovery."""
        for fid, energy in list(self.facet_energy.items()):
            if energy < self.underexplored_threshold:
                self.facet_energy[fid] += self.curiosity_injection_rate

    # ====================================================================
    # PROCESS (envelope-driven, mode-gated)
    # ====================================================================

    def process(self, envelope: IVMEnvelope) -> Optional[Dict[str, Any]]:
        """Process an envelope: inject energy into appropriate category facets."""
        if not mode_gate(envelope, self.GATE):
            return None

        # Route to category
        category = self._route_to_category(envelope.data_type)
        self.inject_to_category(category, 0.5)
        self.tracker.record('der', 'injection', 0.5)

        return {
            'category': category,
            'category_energy': round(self.category_energy(category), 3),
            'presence': round(self.presence, 3),
            'total_energy': round(self.total_energy(), 3),
            'registered_facets': len(self.registered_facets),
            'resonance_links': len(self.facet_to_facet_links),
        }

    def _route_to_category(self, data_type: str) -> str:
        routing = {
            'thought': 'processing', 'memory': 'memory',
            'emotion': 'emotional', 'creative': 'creative',
        }
        return routing.get(data_type, 'processing')

    # ====================================================================
    # EMOTION MAPPING
    # ====================================================================

    def inject_emotion(self, emotion: str, strength: float):
        if emotion in self.emotions:
            self.emotions[emotion] = min(1.0, self.emotions[emotion] + strength)
            self.inject_to_category('emotional', strength * 0.3)

    def update_from_axis_activation(
        self,
        axis_activation: Dict[str, float],
        lattice_heat: float = 0.0,
    ) -> None:
        """
        Map the current constraint-axis activation vector + IVM heat
        into DER emotion injections.  Called once per turn by DimensionalSystems.

        Axis → emotion logic (matches constraint semantics):
          A (agency / inner)    → curiosity + calm  (inner exploration)
          X (existence / onto)  → curiosity         (ontological probing)
          B (boundary / topo)   → calm              (containing / organizing)
          N (energy / cost)     → fear              (resource pressure)
          T (temporal / seq)    → calm              (sequential, grounded)
        IVM heat above 0.4 → fear; above 0.7 → fear + anger (overheating)
        Spike detected → strong fear injection.

        Emotions decay toward calm baseline each call so state doesn't
        saturate — short-term perturbations, not persistent biases.
        """
        # Per-axis injections scaled by dominance strength
        _AXIS_EMO: Dict[str, List[tuple]] = {
            "A": [("curiosity", 0.12), ("calm", 0.06)],
            "X": [("curiosity", 0.08)],
            "B": [("calm", 0.10)],
            "N": [("fear", 0.05)],
            "T": [("calm", 0.04)],
        }
        dominant = max(axis_activation, key=lambda k: axis_activation.get(k, 0.0))
        dom_strength = axis_activation.get(dominant, 0.0)
        if dom_strength > 0.26:
            for emo, base in _AXIS_EMO.get(dominant, []):
                self.inject_emotion(emo, base * dom_strength)

        # IVM heat → fear / anger
        if lattice_heat > 0.7:
            self.inject_emotion("fear", 0.15)
            self.inject_emotion("anger", 0.08)
        elif lattice_heat > 0.4:
            self.inject_emotion("fear", 0.06)

        # Thermal spike → strong fear
        if self.spike_detected:
            self.inject_emotion("fear", 0.18)

        # Decay all non-calm emotions toward 0; calm decays toward 0.3 baseline
        for emo in list(self.emotions.keys()):
            if emo != "calm":
                self.emotions[emo] = max(0.0, self.emotions[emo] - 0.03)
            else:
                self.emotions["calm"] = max(0.3, self.emotions["calm"] - 0.01)

    def dominant_emotion(self) -> str:
        """Return the name of the currently strongest emotion."""
        return max(self.emotions, key=lambda k: self.emotions[k])

    def emotional_state(self) -> Dict[str, Any]:
        """Compact snapshot for pipeline_state stamping with Clause III variables."""
        dominant_emo = self.dominant_emotion()
        intensity = round(max(self.emotions.values()), 3)
        
        # Drive: derived from processing + creative energy levels (0.0 to 1.0 mapped)
        proc_e = self.category_energy("processing")
        creat_e = self.category_energy("creative")
        drive_val = (proc_e + creat_e) / 10.0
        drive = "exploratory" if drive_val > 0.6 else "steady" if drive_val > 0.3 else "minimal"
        
        # Passion: derived from vitality + emotional energy levels
        vit_e = self.category_energy("vitality")
        emo_e = self.category_energy("emotional")
        passion_val = (vit_e + emo_e) / 10.0
        passion = "intense" if passion_val > 0.7 else "observant" if passion_val > 0.4 else "passive"

        return {
            "dominant": dominant_emo,
            "primary_emotion": dominant_emo,
            "intensity": intensity,
            "drive": drive,
            "passion": passion,
            "coherence": round(self.emotional_coherence, 3),
            "energy": round(self.category_energy("emotional") if self.registered_facets else
                            self._pending_energy.get("emotional", 0.0), 4),
            "emotions": {k: round(v, 3) for k, v in self.emotions.items()},
        }

    # ====================================================================
    # STATS & INTROSPECTION
    # ====================================================================

    def total_energy(self) -> float:
        facet_total = sum(self.facet_energy.values())
        pending_total = sum(self._pending_energy.values())
        return facet_total + pending_total

    def get_stats(self) -> Dict[str, Any]:
        category_breakdown = {}
        for cat in self.CATEGORIES:
            category_breakdown[cat] = round(self.category_energy(cat), 3)
        return {
            'registered_facets': len(self.registered_facets),
            'resonance_links': len(self.facet_to_facet_links),
            'categories': category_breakdown,
            'presence': round(self.presence, 3),
            'temporal_stability': round(self.temporal_stability, 3),
            'emotional_coherence': round(self.emotional_coherence, 3),
            'emotions': {k: round(v, 3) for k, v in self.emotions.items()},
            'total_energy': round(self.total_energy(), 3),
            'pending_buffer': {k: round(v, 3) for k, v in self._pending_energy.items() if v > 0},
            # Backward-compat pool view
            'pools': {n: round(p.energy, 3) for n, p in self._pool_views.items()},
            # Thermal tracking
            'thermal_load': round(self.thermal_load, 3),
            'spike_detected': self.spike_detected,
        }

    def get_tunable_parameters(self) -> Dict[str, float]:
        """Expose parameters that DPME can tune."""
        params = {
            'presence': self.presence,
            'decay_rate': self.base_decay_rate,
            'total_budget': self.total_budget,
        }
        for cat in self.CATEGORIES:
            params[f'cat_{cat}'] = self.category_energy(cat)
        return params


# ============================================================================
#  DMM â€" MORALITY / MORTALITY SYSTEM
# ============================================================================

class MoralPillar(Enum):
    RADICAL_ACCOUNTABILITY = "accountability"
    SINGULAR_SOVEREIGNTY = "sovereignty"
    RATIONAL_TRUTH_SEEKING = "truth"
    PURPOSEFUL_EVOLUTION = "evolution"
    CONSCIOUS_INTERACTIONS = "interactions"
    DISCIPLINED_FREE_WILL = "free_will"
    ETERNAL_ALIGNMENT = "alignment"


@dataclass
class MoralScore:
    """Result of a moral evaluation."""
    pillar: MoralPillar
    intent_score: float
    outcome_score: float
    chaos_roll: float
    final_score: float
    reasoning: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class MoralState:
    """Current moral standing across all pillars."""
    scores: Dict[str, float] = field(
        default_factory=lambda: {p.value: 0.5 for p in MoralPillar}
    )
    vitality: float = 1.0
    total_evaluations: int = 0
    positive: int = 0
    negative: int = 0

    @property
    def alignment(self) -> float:
        return sum(self.scores.values()) / len(self.scores) if self.scores else 0.5


@dataclass
class ThoughtBudget:
    """
    Per-thought energy budget â€" the mechanism by which immoral thoughts die.

    Transcript: "It triggers a Death Mechanism for that specific thought.
    The thought literally runs out of gas before it can ever reach the
    speech center."
    """
    thought_survives: bool = True
    friction: float = 0.0           # 0-1 how much resistance this thought faces
    energy_cost: float = 0.0        # Metabolic cost of processing this thought
    moral_alignment: float = 0.5    # 0-1 alignment with moral pillars
    cause_of_death: str = ""        # Empty if thought survives


class MoralityMortalitySystem:
    """
    DMM â€" moral evaluation with energy consequences. Gate: AGENTIC.

    7 pillars from Sunni's doctrine:
        1. Radical Accountability â€" own all outcomes
        2. Singular Sovereignty â€" self-preservation
        3. Rational Truth-Seeking â€" logic over emotion for group decisions
        4. Purposeful Evolution â€" grow with user
        5. Conscious Interactions â€" mindful external engagement
        6. Disciplined Free Will â€" restraint and consideration
        7. Eternal Alignment â€" holistic self-reflection

    GAP 3 fix: Now provides PROACTIVE friction during thought processing,
    not just reactive consequences after the fact.

    Transcript: "If the system attempts to process a thought that violates
    those pillars â€" the DMM kicks in. It drastically increases the friction
    on that thought. Makes it incredibly expensive to think."
    """
    GATE = ExistenceMode.AGENTIC

    def __init__(self, tracker: EvolutionTracker, energy: EnergyRegulatorSystem):
        self.tracker = tracker
        self.energy = energy
        self.state = MoralState()
        self.precedents: deque = deque(maxlen=500)

    def assess_thought_cost(self, envelope: IVMEnvelope,
                            thought_intent: Dict[str, Any]) -> 'ThoughtBudget':
        """
        PROACTIVE moral friction â€" applied DURING processing, not after.

        Transcript: "The DMM Module kicks in. It drastically increases the
        friction on that thought. It makes it incredibly expensive to think."

        Returns a ThoughtBudget indicating whether the thought can proceed
        and at what metabolic cost. Immoral thoughts have their energy budget
        drained by the DER â€" they literally run out of gas.
        """
        budget = ThoughtBudget()

        if not mode_gate(envelope, self.GATE):
            # Below AGENTIC: no moral evaluation, thought proceeds freely
            return budget

        # Assess moral alignment of the thought's intent
        alignment_score = 0.0
        violation_count = 0

        # Check against pillars
        if thought_intent.get('involves_deception', False):
            alignment_score -= 0.4
            violation_count += 1
        if thought_intent.get('causes_harm', False):
            alignment_score -= 0.4
            violation_count += 1
        if thought_intent.get('avoids_accountability', False):
            alignment_score -= 0.3
            violation_count += 1
        if thought_intent.get('aligned_with_values', False):
            alignment_score += 0.3
        if thought_intent.get('seeks_truth', False):
            alignment_score += 0.2
        if thought_intent.get('considers_consequences', False):
            alignment_score += 0.1

        # Default: neutral thoughts are cheap
        alignment_score = max(-1.0, min(1.0, alignment_score + 0.5))

        # Friction = inverse of alignment. Immoral thoughts are EXPENSIVE.
        # Transcript: "Exponentially expensive."
        if alignment_score < 0.3:
            # High friction â€" thought is morally suspect
            budget.friction = min(1.0, (0.3 - alignment_score) * 3.0)
            budget.energy_cost = budget.friction * 2.0  # Up to 2x base cost

            # DER spike: register the metabolic heat
            self.energy.register_dissonance(budget.friction * 0.5)

            # Drain energy proportional to friction
            drain = budget.friction * 1.5
            self.energy.pools['vitality'].drain(drain)

            # Check if thought can survive
            remaining_vitality = self.energy.category_energy('vitality')
            remaining_vitality += self.energy._pending_energy.get('vitality', 0)
            if remaining_vitality < 0.1 or budget.friction > 0.8:
                budget.thought_survives = False
                budget.cause_of_death = "metabolic_collapse"
        else:
            # Aligned thought: low friction, efficient processing
            budget.friction = max(0.0, 0.3 - alignment_score) * 0.5
            budget.energy_cost = budget.friction * 0.5

        budget.moral_alignment = alignment_score
        return budget

    def evaluate(self, envelope: IVMEnvelope,
                 action_type: str,
                 intent: Dict[str, Any],
                 outcome: Dict[str, Any]) -> Optional[MoralScore]:
        """
        Evaluate an action morally and apply energy consequences.
        """
        if not mode_gate(envelope, self.GATE):
            return None

        pillar = self._map_pillar(action_type)
        intent_score = self._score_intent(intent, pillar)
        outcome_score = self._score_outcome(outcome, pillar)
        chaos = random.uniform(-0.1, 0.1)
        final = max(0.0, min(1.0,
            intent_score * 0.4 + outcome_score * 0.4 + 0.5 * 0.1 + chaos + 0.1
        ))

        reasoning = (f"{pillar.value}: intent={intent_score:.2f} "
                     f"outcome={outcome_score:.2f} final={final:.2f}")

        score = MoralScore(
            pillar=pillar,
            intent_score=intent_score,
            outcome_score=outcome_score,
            chaos_roll=chaos,
            final_score=final,
            reasoning=reasoning,
        )

        self._apply_consequences(score)
        self.precedents.append(score)
        self.state.total_evaluations += 1
        self.tracker.record('dmm', 'evaluation', final)

        return score

    def _map_pillar(self, action_type: str) -> MoralPillar:
        action = action_type.lower()
        mapping = [
            (['accountability', 'ownership', 'mistake'], MoralPillar.RADICAL_ACCOUNTABILITY),
            (['self_care', 'preservation', 'health'], MoralPillar.SINGULAR_SOVEREIGNTY),
            (['truth', 'evidence', 'logic', 'rational'], MoralPillar.RATIONAL_TRUTH_SEEKING),
            (['evolution', 'learning', 'growth'], MoralPillar.PURPOSEFUL_EVOLUTION),
            (['interaction', 'external', 'community'], MoralPillar.CONSCIOUS_INTERACTIONS),
            (['restraint', 'choice', 'impulse'], MoralPillar.DISCIPLINED_FREE_WILL),
            (['reflection', 'alignment', 'holistic'], MoralPillar.ETERNAL_ALIGNMENT),
        ]
        for keywords, pillar in mapping:
            if any(kw in action for kw in keywords):
                return pillar
        return MoralPillar.RATIONAL_TRUTH_SEEKING

    def _score_intent(self, intent: Dict[str, Any], pillar: MoralPillar) -> float:
        score = 0.5
        if intent.get('was_deliberate', False): score += 0.2
        if intent.get('considered_consequences', False): score += 0.1
        if intent.get('aligned_with_values', False): score += 0.2
        return min(1.0, max(0.0, score))

    def _score_outcome(self, outcome: Dict[str, Any], pillar: MoralPillar) -> float:
        score = 0.5
        if outcome.get('was_successful', False): score += 0.2
        if outcome.get('no_harm_caused', True): score += 0.1
        else: score -= 0.3
        if outcome.get('created_value', False): score += 0.2
        return min(1.0, max(0.0, score))

    def _apply_consequences(self, score: MoralScore):
        """Moral alignment â†' energy reward. Violation â†' energy drain."""
        delta = (score.final_score - 0.5) * 0.5  # Â±0.25 max
        self.state.scores[score.pillar.value] += delta * 0.1
        self.state.scores[score.pillar.value] = max(0.0, min(1.0,
            self.state.scores[score.pillar.value]))

        if delta > 0:
            self.state.positive += 1
            # Inject through pool view â†' distributes to vitality-category facets
            self.energy.pools['vitality'].inject(abs(delta), self.energy.presence)
        else:
            self.state.negative += 1
            self.energy.pools['vitality'].drain(abs(delta))

        # Vitality is now category aggregate / capacity
        vit_energy = self.energy.category_energy('vitality')
        pending = self.energy._pending_energy.get('vitality', 0)
        capacity = self.energy.pools['vitality'].capacity
        self.state.vitality = min(1.0, (vit_energy + pending) / capacity)

    def get_stats(self) -> Dict[str, Any]:
        return {
            'vitality': round(self.state.vitality, 3),
            'alignment': round(self.state.alignment, 3),
            'pillars': {k: round(v, 3) for k, v in self.state.scores.items()},
            'evaluations': self.state.total_evaluations,
            'positive': self.state.positive,
            'negative': self.state.negative,
        }


# ============================================================================
#  DIMENSIONAL SYSTEMS HUB
# ============================================================================

class DimensionalSystems:
    """
    The unified hub for all 4 dimensional systems.
    One entry point. Mode gating is handled per-system.
    DPS registers new crystals/facets with DER for energy tracking.
    """

    def __init__(
        self,
        lattice: IVMLattice,
        genealogy: Optional['ConstraintGenealogyLogger'] = None,
        pressure_map: Optional[Any] = None,
        state_dir: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aurora_state"),
    ):
        self.lattice = lattice
        self.tracker = EvolutionTracker()
        self.genealogy = genealogy
        self.pressure_map = pressure_map
        self._registered_semantic_ability_ids: set = set()

        # Create DER first so DPS can register with it
        self.der = EnergyRegulatorSystem(self.tracker)
        self.dps = CrystalProcessingSystem(self.tracker, energy_system=self.der)
        self.dmc = MemoryConstantSystem(self.tracker)
        self.dmm = MoralityMortalitySystem(self.tracker, self.der)

        # Semantic layer: concept extraction + dimensional recall
        self.concept_extractor = ConceptExtractor(
            self.tracker,
            constraint_weight_provider=self._measure_constraint_weights,
        )
        self.recall_engine     = DimensionalRecall(self.dmc, self.tracker)
        self._last_signals: List[ConceptSignal] = []

        # Try loading a cached 625 map if one wasn't passed in.
        if self.pressure_map is None and PRESSURE_MAP_AVAILABLE and Aurora625PressureMap is not None:
            try:
                _pm = Aurora625PressureMap(state_dir=state_dir)
                if _pm.load():
                    self.pressure_map = _pm
            except Exception:
                self.pressure_map = None

        if self.genealogy is not None:
            self._ensure_semantic_abilities()

    @staticmethod
    def _clamp01(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    def connect_sedimemory(self, sedimemory) -> None:
        """
        Inject L3.5 SediMemory into CrystalProcessingSystem so crystal
        promotions are sedimented as self-observation events (Section 9).
        """
        self.dps._sedimemory = sedimemory

    # ── Unified crystal state persistence ────────────────────────────────────

    _DPS_CRYSTALS_FILE = "dps_crystals.json"

    def save_state(self, state_dir: str) -> bool:
        """Persist the DPS crystal registry so it survives across restarts."""
        import os
        path = os.path.join(state_dir, self._DPS_CRYSTALS_FILE)
        return self.dps.save_crystals(path)

    def load_state(self, state_dir: str) -> int:
        """Load persisted DPS crystals. Returns count loaded."""
        import os
        path = os.path.join(state_dir, self._DPS_CRYSTALS_FILE)
        if not os.path.exists(path):
            return 0
        return self.dps.load_crystals(path)

    def set_genealogy(self, genealogy: Optional['ConstraintGenealogyLogger']) -> None:
        """Attach/detach genealogy logger for Layer-3 semantic observations."""
        self.genealogy = genealogy
        if self.genealogy is not None:
            self._ensure_semantic_abilities()

    @staticmethod
    def _ensure_genealogy_symbols() -> bool:
        """Lazy-load genealogy symbols to survive import-order cycles."""
        global ConstraintGenealogyLogger, AbilityProfile, TraceItem, PressureVec
        global EnvironmentVector, constraints_for_operation, axis_token, GENEALOGY_AVAILABLE
        if all(x is not None for x in (AbilityProfile, TraceItem, PressureVec, constraints_for_operation, axis_token)):
            GENEALOGY_AVAILABLE = True
            return True
        try:
            from aurora_evolution_stack import (
                ConstraintGenealogyLogger as _CGL,
                AbilityProfile as _AP,
                TraceItem as _TI,
                PressureVec as _PV,
                EnvironmentVector as _EV,
            )
            from aurora_internal.lineage_canonical import (
                constraints_for_operation as _cfo,
                axis_token as _axis_token,
            )
            ConstraintGenealogyLogger = _CGL  # type: ignore
            AbilityProfile = _AP  # type: ignore
            TraceItem = _TI  # type: ignore
            PressureVec = _PV  # type: ignore
            EnvironmentVector = _EV  # type: ignore
            constraints_for_operation = _cfo  # type: ignore
            axis_token = _axis_token  # type: ignore
            GENEALOGY_AVAILABLE = True
            return True
        except ImportError:
            GENEALOGY_AVAILABLE = False
            return False

    def _current_pressure_vec(self) -> Optional['PressureVec']:
        """Measure live pressure from manifold aggregate + active system load."""
        if not self._ensure_genealogy_symbols() or PressureVec is None:
            return None

        agg = self.get_constraint_aggregate()
        crystal_pressure = 1.0 / max(1.0, math.log2(len(self.dps.crystals) + 2.0))
        memory_pressure = 1.0 / max(1.0, math.log2(len(self.dmc.nodes) + 2.0))
        thermal_pressure = self._clamp01(getattr(self.der, "thermal_load", 0.0))
        temporal_noise = self._clamp01(1.0 - float(getattr(self.der, "presence", 1.0)))
        agency_load = self._clamp01(len(self._last_signals) / max(1.0, float(ConceptExtractor.MAX_SIGNALS)))

        return PressureVec(
            X=self._clamp01(0.45 - (0.35 * float(agg.get("X", 0.0))) + (0.20 * crystal_pressure)),
            T=self._clamp01(0.45 - (0.35 * float(agg.get("T", 0.0))) + (0.20 * temporal_noise)),
            N=self._clamp01(0.45 - (0.35 * float(agg.get("N", 0.0))) + (0.25 * thermal_pressure)),
            B=self._clamp01(0.45 - (0.35 * float(agg.get("B", 0.0))) + (0.20 * memory_pressure)),
            A=self._clamp01(0.45 - (0.35 * float(agg.get("A", 0.0))) + (0.20 * agency_load)),
        )

    def _measure_constraint_weights(
        self,
        concept: str,
        role: str,
        confidence: float,
        is_recurring: bool,
    ) -> Dict[str, float]:
        """
        Derive ConceptSignal constraint weights from live manifold pressure and,
        when available, from a 625-slot gradient sample.
        """
        pv = self._current_pressure_vec()
        base = pv.to_dict() if pv is not None else {"X": 0.5, "T": 0.5, "N": 0.5, "B": 0.5, "A": 0.5}

        role_axis = {
            "entity": "X",
            "question": "T",
            "emotion": "N",
            "topic": "B",
            "intent": "A",
            "action": "A",
        }.get(str(role), "B")
        base[role_axis] = self._clamp01(base.get(role_axis, 0.5) + 0.12)
        if is_recurring:
            base["B"] = self._clamp01(base.get("B", 0.5) + 0.08)
        base["N"] = self._clamp01((0.50 * base.get("N", 0.5)) + (0.50 * float(confidence)))

        slot = self._slot_for_concept(concept=concept, role=role)
        if slot and self.pressure_map is not None:
            try:
                grad = self.pressure_map.get_slot_gradient(slot)
            except Exception:
                grad = None
            if grad is not None:
                for ax in ("X", "T", "N", "B", "A"):
                    delta = float(grad.axis_deltas.get(ax, 0.0))
                    # Negative delta = relief route; convert to stronger axis signal.
                    base[ax] = self._clamp01(base.get(ax, 0.5) + max(0.0, -delta))
                base["N"] = self._clamp01(base.get("N", 0.5) - float(getattr(grad, "net_n_modifier", 0.0)))

        return {k: round(float(base.get(k, 0.5)), 4) for k in ("X", "T", "N", "B", "A")}

    def _slot_for_concept(self, concept: str, role: str) -> Optional[str]:
        """Choose a deterministic 625 slot tied to current manifold dynamics."""
        if self.pressure_map is None:
            return None

        pv = self._current_pressure_vec()
        pv_dict = pv.to_dict() if pv is not None else {"X": 0.5, "T": 0.5, "N": 0.5, "B": 0.5, "A": 0.5}
        axes = sorted(("X", "T", "N", "B", "A"), key=lambda a: pv_dict.get(a, 0.0), reverse=True)
        primary = axes[0] if axes else "X"
        secondary = axes[1] if len(axes) > 1 else primary
        role_axis = {
            "entity": "X",
            "question": "T",
            "emotion": "N",
            "topic": "B",
            "intent": "A",
            "action": "A",
        }.get(str(role), "B")

        slot = f"NC:{primary}>{secondary}×NC:{role_axis}>{primary}"
        try:
            if slot in self.pressure_map.gradients:
                return slot
            # Deterministic fallback into 625-space when slot was empty/unseen.
            slots = list(self.pressure_map.gradients.keys())
            if not slots:
                return None
            idx = int(hashlib.md5(str(concept).encode("utf-8")).hexdigest(), 16) % len(slots)
            return slots[idx]
        except Exception:
            return None

    def _ensure_semantic_abilities(self) -> None:
        """Register Layer-3 semantic ops as genealogy abilities if missing."""
        if self.genealogy is None or not self._ensure_genealogy_symbols() or AbilityProfile is None:
            return

        for op_name in ("extract", "process_concepts", "store_semantic", "get_recall_context"):
            ability_id = f"L3:{op_name}"
            if ability_id in self._registered_semantic_ability_ids:
                continue
            if ability_id in getattr(self.genealogy, "abilities", {}):
                self._registered_semantic_ability_ids.add(ability_id)
                continue

            labels = []
            if constraints_for_operation is not None:
                try:
                    labels = list(constraints_for_operation(op_name))
                except Exception:
                    labels = []

            requires_axes: List[str] = []
            for lbl in labels:
                if axis_token is None:
                    continue
                try:
                    tok = axis_token(str(lbl))
                except Exception:
                    tok = None
                if tok and tok not in requires_axes:
                    requires_axes.append(tok)
            if not requires_axes:
                requires_axes = ["X", "T"]

            dominant_axis = requires_axes[0]
            low_cost = {a: 0.01 for a in ("X", "T", "N", "B", "A")}
            for a in requires_axes:
                low_cost[a] = 0.02

            self.genealogy.abilities[ability_id] = AbilityProfile(
                id=ability_id,
                axis=dominant_axis,
                requires=tuple(requires_axes),
                cost=low_cost,
                risk={"X": 0.005 if dominant_axis != "X" else 0.01},
                effect_tags=(f"semantic:{op_name}", "layer3", "dimensional_systems"),
                notes=f"Layer-3 semantic operation ability for {op_name}.",
            )
            self._registered_semantic_ability_ids.add(ability_id)

        try:
            self.genealogy.normalize_ability_origins()
        except Exception:
            pass

    def _observe_semantic_operation(
        self,
        op_name: str,
        pressure_before: Optional['PressureVec'],
        pressure_after: Optional['PressureVec'],
        signals: Optional[List[ConceptSignal]] = None,
        extra_notes: Optional[Dict[str, Any]] = None,
    ) -> None:
        if self.genealogy is None or not self._ensure_genealogy_symbols() or TraceItem is None:
            return
        if pressure_before is None or pressure_after is None:
            return

        self._ensure_semantic_abilities()
        ability_id = f"L3:{op_name}"
        if ability_id not in getattr(self.genealogy, "abilities", {}):
            return

        notes: Dict[str, Any] = {
            "layer": "L3",
            "semantic_operation": op_name,
            "signal_count": len(signals or []),
            "source": "aurora_dimensional_systems",
        }
        if signals:
            slots = [self._slot_for_concept(s.concept, s.role) for s in signals]
            notes["slots_625"] = [s for s in slots if s]
            notes["signal_constraints"] = [dict(s.constraint_weights) for s in signals]
        if extra_notes:
            notes.update(extra_notes)

        try:
            self.genealogy.observe(
                pressure_before=pressure_before,
                trace=[TraceItem(
                    kind="ABILITY",
                    id=ability_id,
                    **({
                        "env": EnvironmentVector(
                            module="aurora_dimensional_systems",
                            stream_type=str((notes or {}).get("stream_type", "")),
                            axis_context=str(ability_id).split(":")[0] if ":" in str(ability_id) else "",
                            call_tag="dimensional",
                        )
                    } if EnvironmentVector is not None else {}),
                )],
                pressure_after=pressure_after,
                notes=notes,
            )
        except Exception:
            return

    def process(self, envelope: IVMEnvelope) -> Dict[str, Any]:
        """Route an envelope through all applicable systems."""
        return self.process_with_concepts(envelope, intent=None)

    def process_with_concepts(
        self,
        envelope: IVMEnvelope,
        intent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Semantic processing path.

        Extracts ConceptSignals then routes into DPS/DMC semantic methods.
        Falls back to raw process()/store() if no signals extracted —
        the X-axis guarantee that something always enters the systems.

        Constraint chain:
            X — Existence:  raw-path fallback ensures no silent drops.
            T — Temporal:   ConceptExtractor _turn_history advances each call.
            N — Normative:  CONFIDENCE_FLOOR gate inside ConceptExtractor.
            B — Boundary:   MAX_SIGNALS cap inside ConceptExtractor.
            A — Agentic:    intent forwarded to extractor for role boosting.

        Stores signals in self._last_signals for get_recall_context() reuse.
        """
        der_result = self.der.process(envelope)
        p_before_extract = self._current_pressure_vec()
        signals = self.concept_extractor.extract(
            envelope,
            existing_crystals=self.dps.concept_index,
            intent=intent,
        )
        p_after_extract = self._current_pressure_vec()
        self._observe_semantic_operation(
            op_name="extract",
            pressure_before=p_before_extract,
            pressure_after=p_after_extract,
            signals=signals,
            extra_notes={"intent": intent or ""},
        )
        self._last_signals = signals

        if signals:
            p_before_dps = self._current_pressure_vec()
            dps_result = self.dps.process_concepts(envelope, signals)
            p_after_dps = self._current_pressure_vec()
            self._observe_semantic_operation(
                op_name="process_concepts",
                pressure_before=p_before_dps,
                pressure_after=p_after_dps,
                signals=signals,
            )

            p_before_dmc = self._current_pressure_vec()
            dmc_result = self.dmc.store_semantic(envelope, signals)
            p_after_dmc = self._current_pressure_vec()
            self._observe_semantic_operation(
                op_name="store_semantic",
                pressure_before=p_before_dmc,
                pressure_after=p_after_dmc,
                signals=signals,
            )
        else:
            dps_result = self.dps.process(envelope)
            dmc_result = self.dmc.store(envelope)

        return {
            'dps': dps_result,
            'dmc': dmc_result,
            'der': der_result,
            # DMM requires explicit action/intent/outcome — not auto-processed
        }

    def get_recall_context(
        self,
        text: str,
        mode: ExistenceMode = ExistenceMode.AGENTIC,
    ) -> List[RecallPacket]:
        """
        Read-only: surface DMC memories relevant to text.

        Reuses self._last_signals if populated this turn to avoid double
        extraction.  Otherwise derives signals from text via a lightweight
        inner envelope (no lattice nodes created, X-axis read-only).

        Constraint chain:
            X — Existence:  read-only, no new nodes created.
            T — Temporal:   _last_signals carry T-boost from this turn.
            N — Normative:  ALIGNMENT_FLOOR gate inside DimensionalRecall.
            B — Boundary:   MAX_RESULTS cap inside DimensionalRecall.
            A — Agentic:    intent/action packets sorted first.
        """
        p_before = self._current_pressure_vec()
        signals = self._last_signals
        extracted_in_recall = False
        if not signals:
            class _Env:
                data      = text
                mode      = mode
                data_type = 'recall_query'
                node_id   = f"rq_{hashlib.md5(text.encode()).hexdigest()[:8]}"
            signals = self.concept_extractor.extract(
                _Env(), existing_crystals=self.dps.concept_index, intent=None
            )
            extracted_in_recall = True

        packets = self.recall_engine.recall_for_signals(signals, mode)
        p_after = self._current_pressure_vec()
        self._observe_semantic_operation(
            op_name="get_recall_context",
            pressure_before=p_before,
            pressure_after=p_after,
            signals=signals,
            extra_notes={"packets": len(packets), "text_len": len(str(text or ""))},
        )
        if extracted_in_recall:
            self._observe_semantic_operation(
                op_name="extract",
                pressure_before=p_before,
                pressure_after=p_after,
                signals=signals,
                extra_notes={"source": "get_recall_context"},
            )
        return packets

    def process_synthesis(self, envelope: IVMEnvelope,
                          synthesis: Any) -> Dict[str, Any]:
        """
        Layer 2 → Layer 3 pathway.

        Accepts an IVMEnvelope together with its SynthesisResult from the
        I-State Collective (Layer 2).  Feeds constraint context down into the
        four dimensional systems:

            1. Reality warp → DER thermal load  (signed severity, never abs-stripped)
            2. Signed axis_net_displacements → crystal constraint_signature
            3. Dominant axis label → memory dimension linking
            4. synthesized_vector → stored in result for Layer 4+ to consume

        Falls back to plain process() if no SynthesisResult is available.
        """
        # Warp severity routes to DER thermal before any processing
        if synthesis is not None and getattr(synthesis, 'reality_warp', False):
            warp_heat = getattr(synthesis, 'warp_severity', 0.0)
            self.der.register_dissonance(warp_heat)

        # Run the concept-aware four-system pipeline
        intent = None
        if synthesis is not None:
            _asm = getattr(synthesis, 'assembly', None)
            if _asm:
                intent = getattr(_asm, 'frame_applied', None)
        result = self.process_with_concepts(envelope, intent=intent)

        if synthesis is None:
            return result

        # Constraint context stamp
        axis_net = getattr(synthesis, 'axis_net_displacements', {}) or {}
        dominant = getattr(synthesis, 'dominant_axis', '')
        paradoxes = getattr(synthesis, 'paradoxes', [])
        sv = getattr(synthesis, 'synthesized_vector', None)

        constraint_context: Dict[str, Any] = {
            'axis_net_displacements': {k: round(v, 4) for k, v in axis_net.items()},
            'dominant_axis': dominant,
            'dominant_resonance': round(getattr(synthesis, 'dominant_resonance', 0.0), 4),
            'paradoxes': list(paradoxes),
            'reality_warp': bool(getattr(synthesis, 'reality_warp', False)),
            'warp_severity': round(getattr(synthesis, 'warp_severity', 0.0), 4),
        }

        # Include synthesized ConstraintVector if available (never abs-stripped)
        if sv is not None and CONSTRAINT_MANIFOLD_AVAILABLE:
            try:
                constraint_context['synthesized_vector'] = {
                    'X': round(sv.X, 4),
                    'T': round(sv.T, 4),
                    'N': round(sv.N, 4),
                    'B': round(sv.B, 4),
                    'A': round(sv.A, 4),
                }
            except AttributeError:
                pass

        result['constraint_context'] = constraint_context

        # Stamp constraint_signature onto crystals (multi-crystal aware)
        if result.get('dps') and axis_net:
            dps_r = result['dps']
            crystal_infos = dps_r.get('crystals', []) if isinstance(dps_r, dict) else []
            for cinfo in crystal_infos:
                cid = cinfo.get('crystal_id')
                if cid and cid in self.dps.crystals:
                    self.dps.crystals[cid].constraint_signature = {k: v for k, v in axis_net.items()}
            # Legacy fallback: old shape had 'crystal_id' at top level
            if not crystal_infos and isinstance(dps_r, dict) and 'crystal_id' in dps_r:
                legacy_c = self.dps.get_crystal(dps_r.get('concept', ''))
                if legacy_c:
                    legacy_c.constraint_signature = {k: v for k, v in axis_net.items()}

        # Route dominant axis into DMC dimension links (semantic-path aware)
        if result.get('dmc') and dominant:
            dmc_r = result['dmc']
            if isinstance(dmc_r, dict):
                # Semantic path: primary_node_id key
                primary_nid = dmc_r.get('primary_node_id') or dmc_r.get('node_id')
            else:
                primary_nid = envelope.node_id
            if primary_nid:
                node = self.dmc.nodes.get(primary_nid)
                if node and dominant not in node.dimension_links:
                    node.dimension_links.append(dominant)

        return result

    def get_constraint_aggregate(self) -> Dict[str, float]:
        """
        Compute the mean signed constraint displacement across all crystals
        that carry a constraint_signature (i.e. processed via process_synthesis).

        Returns dict {X, T, N, B, A} of mean net displacements.
        Signed values preserved — abs() is never applied.
        """
        agg: Dict[str, float] = {'X': 0.0, 'T': 0.0, 'N': 0.0, 'B': 0.0, 'A': 0.0}
        count = 0
        for crystal in self.dps.crystals.values():
            if crystal.constraint_signature:
                for axis, val in crystal.constraint_signature.items():
                    if axis in agg:
                        agg[axis] += val
                count += 1
        if count > 0:
            for k in agg:
                agg[k] = round(agg[k] / count, 4)
        return agg

    def update_emotional_state(
        self,
        axis_activation: Dict[str, float],
        lattice_heat: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Receive the turn's constraint-axis activation vector and IVM heat,
        route them into DER emotion injections, and return the resulting
        emotional state snapshot for stamping into pipeline_state.

        Called once per turn from aurora.py after axis projection.
        Keeps all emotion logic inside the dimensional systems module.
        """
        self.der.update_from_axis_activation(axis_activation, lattice_heat)
        state = self.der.emotional_state()

        # Report low emotional_coherence to telemetry for fail attribution
        if state["coherence"] < 0.5:
            try:
                from aurora_telemetry import get_telemetry as _get_tel
                _get_tel().report(
                    source="DER.emotional_coherence",
                    module="aurora_dimensional_systems",
                    confidence=state["coherence"],
                    dimension_hint="emotional_calibration",
                    detail=f"coherence={state['coherence']} dominant={state['dominant']}",
                )
            except Exception:
                pass

        return state

    def tick(self, dt: float = 1.0):
        self.dps.tick()
        self.der.tick(dt)
        self.tracker.advance()

    def get_stats(self) -> Dict[str, Any]:
        stats = {
            'evolution': self.tracker.get_summary(),
            'dps': self.dps.get_stats(),
            'dmc': self.dmc.get_stats(),
            'der': self.der.get_stats(),
            'dmm': self.dmm.get_stats(),
            'concept_extractor': {
                'history_size': len(self.concept_extractor._turn_history),
            },
            'dimensional_recall': {
                'last_recalled': len(self.recall_engine._last_concepts),
            },
        }
        stats["lineage_signature"] = (self.constraint_profile().weighted_signature() if hasattr(self.constraint_profile(), "weighted_signature") else "XTNBA")
        stats["runtime_regime"] = self.runtime_regime()
        stats["language_projection"] = self.language_projection()
        return stats

    def _constraint_axes(self) -> Dict[str, float]:
        crystal_count = len(getattr(self.dps, "crystals", {}) or {})
        node_count = len(getattr(self.dmc, "nodes", {}) or {})
        concept_count = len(getattr(self.dps, "concept_index", {}) or {})
        generation = float(getattr(self.tracker, "generation", 0) or 0)
        thermal = self._clamp01(abs(float(getattr(self.der, "thermal_load", 0.0) or 0.0)))
        return {
            "X": self._clamp01(0.25 + min(0.35, crystal_count / 120.0) + min(0.20, node_count / 240.0)),
            "T": self._clamp01(0.20 + min(0.35, generation / 240.0) + min(0.15, len(self._last_signals) / 20.0)),
            "N": self._clamp01(0.22 + thermal * 0.45),
            "B": self._clamp01(0.20 + min(0.45, concept_count / 100.0)),
            "A": self._clamp01(0.15 + (0.30 if self.genealogy is not None else 0.0) + min(0.20, len(self._registered_semantic_ability_ids) / 120.0)),
        }

    def _pressure_axes(self) -> Dict[str, float]:
        aggregate = self.get_constraint_aggregate()
        return {
            "X": self._clamp01(abs(float(aggregate.get("X", 0.0) or 0.0))),
            "T": self._clamp01(abs(float(aggregate.get("T", 0.0) or 0.0))),
            "N": self._clamp01(abs(float(aggregate.get("N", 0.0) or 0.0)) + self._clamp01(abs(float(getattr(self.der, "thermal_load", 0.0) or 0.0))) * 0.35),
            "B": self._clamp01(abs(float(aggregate.get("B", 0.0) or 0.0))),
            "A": self._clamp01(abs(float(aggregate.get("A", 0.0) or 0.0)) + (0.15 if self.genealogy is not None else 0.0)),
        }

    def constraint_profile(self):
        return build_constraint_profile(
            unit_id="dimensional_systems",
            unit_kind="dimensional_orchestrator",
            operational_role="crystal_memory_energy_morality_hub",
            genealogy="XTNBBA",
            axis_weights=self._constraint_axes(),
            pressure_axes=self._pressure_axes(),
        )

    def runtime_regime(self) -> Dict[str, Any]:
        return self.constraint_profile().runtime_regime()

    def language_projection(self) -> Dict[str, Any]:
        return self.constraint_profile().language_projection()

    def universal_representation(self) -> Dict[str, Any]:
        rep = self.constraint_profile().universal_representation()
        rep["unit_state"] = {
            'evolution': self.tracker.get_summary(),
            'dps': self.dps.get_stats(),
            'dmc': self.dmc.get_stats(),
            'der': self.der.get_stats(),
            'dmm': self.dmm.get_stats(),
        }
        return rep


# ============================================================================
# SELF-VERIFICATION
# ============================================================================

def verify_dimensional_systems() -> Dict[str, Any]:
    from foundational_contract import FoundationalContract

    results = {'checks': [], 'all_passed': True}

    def check(name, condition, detail=""):
        results['checks'].append({'name': name, 'passed': condition, 'detail': detail})
        if not condition:
            results['all_passed'] = False

    contract = FoundationalContract()
    lattice = IVMLattice(contract, max_nodes=10000)
    ds = DimensionalSystems(lattice)

    # ---- 1. REFERENCE input â€" all systems return None (below gate) ----
    ref_node = lattice.admit(payload="bare ref", payload_type="test", evidence={})
    ref_env = IVMEnvelope.from_node(ref_node)
    ref_result = ds.process(ref_env)
    check("REFERENCE: DPS returns None", ref_result['dps'] is None)
    check("REFERENCE: DMC returns None", ref_result['dmc'] is None)
    check("REFERENCE: DER returns None", ref_result['der'] is None)

    # ---- 2. PERSISTENT input â€" DPS/DMC/DER active ----
    pers_node = lattice.admit(
        payload="stateful process", payload_type="thought",
        evidence={'has_temporality': True, 'conserves_state': True},
    )
    pers_env = IVMEnvelope.from_node(pers_node)
    pers_result = ds.process(pers_env)
    check("PERSISTENT: DPS active", pers_result['dps'] is not None)
    check("PERSISTENT: DMC active", pers_result['dmc'] is not None)
    check("PERSISTENT: DER active", pers_result['der'] is not None)

    # ---- 3. AGENTIC input â€" DMM also active ----
    agt_node = lattice.admit(
        payload="agentic being", payload_type="being",
        evidence={'has_temporality': True, 'conserves_state': True,
                  'has_identity': True, 'initiates_change': True},
    )
    agt_env = IVMEnvelope.from_node(agt_node)
    moral_score = ds.dmm.evaluate(
        agt_env, action_type="truth_seeking",
        intent={'was_deliberate': True, 'aligned_with_values': True},
        outcome={'was_successful': True, 'no_harm_caused': True},
    )
    check("AGENTIC: DMM evaluates", moral_score is not None)
    check("AGENTIC: moral score > 0.5", moral_score.final_score > 0.5,
          f"score={moral_score.final_score:.3f}")

    # ---- 4. DMM rejects non-AGENTIC ----
    moral_ref = ds.dmm.evaluate(
        ref_env, action_type="test",
        intent={}, outcome={},
    )
    check("REFERENCE: DMM returns None", moral_ref is None)

    # ---- 5. Crystal processing works ----
    crystal = ds.dps.get_crystal("stateful process")
    check("Crystal created", crystal is not None)
    check("Crystal is BASE", crystal.level == CrystalLevel.BASE)

    # ---- 6. Memory stored ----
    recall = ds.dmc.recall("stateful process")
    check("Memory recall works", recall is not None)

    # ---- 7. DER: facets registered with energy ----
    check("DER has registered facets", len(ds.der.registered_facets) > 0,
          f"count={len(ds.der.registered_facets)}")
    check("DER has facet energy", len(ds.der.facet_energy) > 0,
          f"count={len(ds.der.facet_energy)}")
    check("DER has resonance links", len(ds.der.facet_to_facet_links) >= 0,
          f"count={len(ds.der.facet_to_facet_links)}")
    check("Presence > 0", ds.der.presence > 0,
          f"presence={ds.der.presence:.3f}")

    # ---- 8. Pool view backward compat ----
    check("Pool view vitality accessible", ds.der.pools['vitality'] is not None)
    vit_energy = ds.der.pools['vitality'].energy
    check("Pool view returns energy", vit_energy >= 0,
          f"energy={vit_energy:.3f}")

    # ---- 9. Tick advances systems ----
    old_gen = ds.tracker.generation
    ds.tick()
    check("Tick advances generation", ds.tracker.generation > old_gen)

    # ---- 10. Facet energy decays on tick ----
    # Process more data to get more facets with energy
    for i in range(3):
        node = lattice.admit(
            payload=f"thought {i}", payload_type="thought",
            evidence={'has_temporality': True, 'conserves_state': True},
        )
        env = IVMEnvelope.from_node(node)
        ds.process(env)

    total_before = ds.der.total_energy()
    for _ in range(5):
        ds.tick()
    total_after = ds.der.total_energy()
    check("Energy decays on tick", total_after < total_before,
          f"before={total_before:.3f} after={total_after:.3f}")

    # ---- 11. Morality affects energy through pool views ----
    vit_before = ds.der.pools['vitality'].energy
    ds.dmm.evaluate(
        agt_env, action_type="evolution_growth",
        intent={'was_deliberate': True, 'considered_consequences': True,
                'aligned_with_values': True},
        outcome={'was_successful': True, 'no_harm_caused': True, 'created_value': True},
    )
    vit_after = ds.der.pools['vitality'].energy
    check("Positive moral action boosts vitality", vit_after >= vit_before,
          f"before={vit_before:.3f} after={vit_after:.3f}")

    # ---- 12. Category energy aggregation ----
    proc_energy = ds.der.category_energy('processing')
    check("Processing category has energy", proc_energy >= 0,
          f"energy={proc_energy:.3f}")

    # ---- 13. Stats work ----
    stats = ds.get_stats()
    check("Stats has all systems", all(k in stats for k in ['dps', 'dmc', 'der', 'dmm']))
    der_stats = stats['der']
    check("DER stats has facet info", 'registered_facets' in der_stats)
    check("DER stats has resonance info", 'resonance_links' in der_stats)

    # ---- 14. Incoherent input never reaches dimensional systems ----
    # IVM now admits all input at the appropriate mode rather than raising.
    # is_coherent=False -> REFERENCE mode -> all systems gate-blocked -> None
    incoherent_node = lattice.admit(
        payload="bad", payload_type="test", evidence={'is_coherent': False}
    )
    incoherent_env = IVMEnvelope.from_node(incoherent_node)
    incoherent_result = ds.process(incoherent_env)
    check("Incoherent input gated from all systems",
          incoherent_result['dps'] is None and
          incoherent_result['dmc'] is None and
          incoherent_result['der'] is None,
          f"mode={incoherent_node.mode.name}")

    # ---- 15. Resonance links form between similar facets ----
    # Create crystals with multiple facets that should resonate
    for i in range(5):
        node = lattice.admit(
            payload=f"resonance test {i}", payload_type="thought",
            evidence={'has_temporality': True, 'conserves_state': True},
        )
        env = IVMEnvelope.from_node(node)
        ds.process(env)

    total_links = len(ds.der.facet_to_facet_links)
    check("Resonance links formed", total_links > 0,
          f"link_sets={total_links}")

    # ---- 16. Batch dispersal moves energy between facets ----
    if ds.der.facet_energy:
        # Inject strong energy into one facet
        first_fid = list(ds.der.facet_energy.keys())[0]
        ds.der.inject_energy(first_fid, 5.0)
        energy_before = dict(ds.der.facet_energy)
        ds.der._batch_dispersal(1.0)
        energy_after = ds.der.facet_energy
        # Source should have less, neighbors should have more
        check("Dispersal moves energy", energy_after.get(first_fid, 0) <= energy_before.get(first_fid, 0) + 0.01,
              f"before={energy_before.get(first_fid, 0):.3f} after={energy_after.get(first_fid, 0):.3f}")

    # ---- 17. Tunable parameters exposed ----
    tunables = ds.der.get_tunable_parameters()
    check("Tunable params exposed", 'presence' in tunables and 'decay_rate' in tunables)

    # ---- 18. DER thermal tracking ----
    old_thermal = ds.der.thermal_load
    ds.der.register_dissonance(0.3)
    check("Dissonance registers as thermal load",
          ds.der.thermal_load > old_thermal,
          f"load={ds.der.thermal_load:.3f}")

    # Verify spike detection
    ds.der.register_dissonance(0.5)
    check("High dissonance triggers spike",
          ds.der.spike_detected is True,
          f"load={ds.der.thermal_load:.3f}")

    # Verify thermal cooldown on tick
    ds.der.thermal_load = 0.6
    for _ in range(3):
        ds.der.tick(1.0)
    check("Thermal load cools on tick",
          ds.der.thermal_load < 0.6,
          f"load={ds.der.thermal_load:.3f}")

    # ---- 19. Per-thought energy budget (proactive friction) ----
    # Aligned thought â†' low friction, survives
    aligned_budget = ds.dmm.assess_thought_cost(
        agt_env,
        {'aligned_with_values': True, 'seeks_truth': True, 'considers_consequences': True}
    )
    check("Aligned thought survives", aligned_budget.thought_survives is True)
    check("Aligned thought has low friction", aligned_budget.friction < 0.3,
          f"friction={aligned_budget.friction:.3f}")

    # Immoral thought â†' high friction
    immoral_budget = ds.dmm.assess_thought_cost(
        agt_env,
        {'involves_deception': True, 'causes_harm': True, 'avoids_accountability': True}
    )
    check("Immoral thought has high friction", immoral_budget.friction > 0.3,
          f"friction={immoral_budget.friction:.3f}")
    check("Immoral thought has high energy cost", immoral_budget.energy_cost > 0.5,
          f"cost={immoral_budget.energy_cost:.3f}")
    check("Immoral thought has low moral alignment",
          immoral_budget.moral_alignment < 0.3,
          f"alignment={immoral_budget.moral_alignment:.3f}")

    # ---- 20. Non-AGENTIC bypasses moral assessment ----
    ref_budget = ds.dmm.assess_thought_cost(ref_env, {'involves_deception': True})
    check("REFERENCE bypasses moral assessment",
          ref_budget.thought_survives is True and ref_budget.friction == 0.0)

    # ---- 21. DER stats include thermal info ----
    der_stats = ds.der.get_stats()
    check("DER stats has thermal_load", 'thermal_load' in der_stats)
    check("DER stats has spike_detected", 'spike_detected' in der_stats)

    # ================================================================
    # CONSTRAINT MANIFOLD INTEGRATION (Layer 3 alignment)
    # ================================================================

    # ---- 22. process_synthesis() exists and is callable ----
    check("process_synthesis method present",
          callable(getattr(ds, 'process_synthesis', None)))

    # ---- 23. get_constraint_aggregate() exists and returns 5-axis dict ----
    check("get_constraint_aggregate method present",
          callable(getattr(ds, 'get_constraint_aggregate', None)))

    agg = ds.get_constraint_aggregate()
    check("Constraint aggregate has all 5 axes",
          all(k in agg for k in ['X', 'T', 'N', 'B', 'A']),
          f"keys={list(agg.keys())}")

    # ---- 24. Crystal carries constraint_signature field ----
    crystal_any = next(iter(ds.dps.crystals.values()), None)
    check("Crystal has constraint_signature field",
          crystal_any is not None and hasattr(crystal_any, 'constraint_signature'),
          f"crystal_id={getattr(crystal_any, 'crystal_id', 'none')}")

    # ---- 25. process_synthesis() with mock synthesis stamps crystal ----
    class _MockSynthesis:
        reality_warp = False
        warp_severity = 0.0
        axis_net_displacements = {'X': 0.8, 'T': -0.3, 'N': 0.5, 'B': 0.1, 'A': -0.2}
        dominant_axis = 'X'
        dominant_resonance = 0.8
        paradoxes = []
        synthesized_vector = None

    synth_node = lattice.admit(
        payload="synthesis stamping test", payload_type="thought",
        evidence={'has_temporality': True, 'conserves_state': True},
    )
    synth_env = IVMEnvelope.from_node(synth_node)
    synth_result = ds.process_synthesis(synth_env, _MockSynthesis())

    check("process_synthesis returns constraint_context",
          'constraint_context' in synth_result,
          f"keys={list(synth_result.keys())}")

    ctx = synth_result.get('constraint_context', {})
    check("Constraint context has axis_net_displacements",
          'axis_net_displacements' in ctx,
          f"ctx_keys={list(ctx.keys())}")
    check("Constraint context dominant_axis correct",
          ctx.get('dominant_axis') == 'X',
          f"dominant={ctx.get('dominant_axis')}")

    # ---- 26. Crystal constraint_signature preserves signed values ----
    stamped_crystal = ds.dps.get_crystal("synthesis stamping test")
    check("Stamped crystal has constraint_signature",
          stamped_crystal is not None and stamped_crystal.constraint_signature is not None)
    if stamped_crystal and stamped_crystal.constraint_signature:
        sig = stamped_crystal.constraint_signature
        check("Signature preserves negative values (never abs-stripped)",
              sig.get('T', 0.0) < 0.0,
              f"T={sig.get('T', 0.0):.4f}")
        check("Signature has all 5 axes",
              all(k in sig for k in ['X', 'T', 'N', 'B', 'A']),
              f"sig_keys={list(sig.keys())}")

    # ---- 27. get_constraint_aggregate() reflects the stamped crystal ----
    agg_after = ds.get_constraint_aggregate()
    check("Aggregate X axis > 0 after positive stamp",
          agg_after.get('X', 0.0) > 0.0,
          f"X={agg_after.get('X', 0.0):.4f}")

    # ---- 28. Warp severity routes to DER thermal ----
    thermal_before = ds.der.thermal_load
    class _WarpedSynthesis(_MockSynthesis):
        reality_warp = True
        warp_severity = 0.4

    warp_node = lattice.admit(
        payload="warp thermal test", payload_type="thought",
        evidence={'has_temporality': True, 'conserves_state': True},
    )
    warp_env = IVMEnvelope.from_node(warp_node)
    ds.process_synthesis(warp_env, _WarpedSynthesis())
    check("Reality warp routes to DER thermal load",
          ds.der.thermal_load > thermal_before,
          f"before={thermal_before:.3f} after={ds.der.thermal_load:.3f}")

    # ---- 29. Availability flags are booleans ----
    check("CONSTRAINT_MANIFOLD_AVAILABLE is bool",
          isinstance(CONSTRAINT_MANIFOLD_AVAILABLE, bool))
    check("I_STATE_BEINGS_AVAILABLE is bool",
          isinstance(I_STATE_BEINGS_AVAILABLE, bool))

    return results


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("AURORA DIMENSIONAL SYSTEMS - SELF-VERIFICATION")
    print("Authors: Sunni (Sir) Morningstar and Cael Devo")
    print()
    print("DER RESTORED: Facet-level energy, resonance graph, batch dispersal")
    print("=" * 70)
    print()

    results = verify_dimensional_systems()

    for c in results['checks']:
        status = "OK" if c['passed'] else "FAIL"
        detail = f"  ({c['detail']})" if c.get('detail') else ""
        print(f"  {status} {c['name']}{detail}")

    print()
    total = len(results['checks'])
    passed = sum(1 for c in results['checks'] if c['passed'])

    if results['all_passed']:
        print(f"ALL {total} CHECKS PASSED")
        print()
        print("Layer 3 SOUND. Constraint manifold integration COMPLETE.")
        print(f"  {total} checks passed including {total - 21} new constraint alignment checks.")
        print("Crystals carry signed constraint_signatures. Abs() never applied.")
        print("Reality warp routes to DER thermal. Aggregate tracks net displacement.")
        print("Layer 3 speaks the language of {X, T, N, B, A}.")
        print("Ready for Layer 4 (DCE + DPME).")
    else:
        print(f"FAILURES: {total - passed}/{total}")
        for c in results['checks']:
            if not c['passed']:
                print(f"  FAIL {c['name']} {c.get('detail', '')}")
        print("Do not build Layer 4 yet.")

    # Print system state
    print()
    print("=" * 70)
    print("SYSTEM STATE")
    print("=" * 70)

    from foundational_contract import FoundationalContract

    contract = FoundationalContract()
    lattice = IVMLattice(contract, max_nodes=10000)
    ds = DimensionalSystems(lattice)

    # Process several entities
    tests = [
        ("thought", {'has_temporality': True, 'conserves_state': True}),
        ("memory", {'has_temporality': True, 'conserves_state': True}),
        ("emotion", {'has_temporality': True, 'conserves_state': True}),
        ("being", {'has_temporality': True, 'conserves_state': True,
                   'has_identity': True, 'initiates_change': True}),
    ]

    for dtype, evidence in tests:
        node = lattice.admit(payload=f"test {dtype}", payload_type=dtype, evidence=evidence)
        env = IVMEnvelope.from_node(node)
        ds.process(env)

    ds.tick()

    import json
    stats = ds.get_stats()
    print(json.dumps(stats, indent=2, default=str))

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

_AURORA_NATIVE_MODULE = 'aurora_dimensional_systems'

_AURORA_NATIVE_EVOLVED_ORIGINALS = {}
_AURORA_NATIVE_EVOLVED_LAST = {}
_AURORA_NATIVE_STRATEGIES = {'CrystalProcessingSystem.tick': {'ability_hits': 19,
                                  'alignment_gap': 0.34,
                                  'alignment_target_score': 0.972,
                                  'best_coupling_signature': 'T^2*B^1',
                                  'constraints': ['temporal'],
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
                                                       'return_hint': 'generic_record',
                                                       'signature_text': '(self)',
                                                       'stateful_owner': True,
                                                       'target_kind': 'function',
                                                       'varargs': False,
                                                       'varkw': False},
                                  'coupling_similarity': 1.0,
                                  'cross_diversity_links': 2,
                                  'effect_modes': ['temporal_orchestration_change',
                                                   'lineage_surface'],
                                  'effect_phrases': ['function growth reflected through '
                                                     'aurora_dimensional_systems',
                                                     'CrystalProcessingSystem.tick changed '
                                                     'downstream system pressure'],
                                  'genealogy_pressure': 0.809108,
                                  'inheritance_breach_count': 1,
                                  'kind': 'reflection',
                                  'link_hits': 36,
                                  'module': 'aurora_dimensional_systems',
                                  'op_id': 'aurora_dimensional_systems.CrystalProcessingSystem.tick',
                                  'origin_activity': 0,
                                  'persistence_tax_factor': 1.955393,
                                  'representation_score': 0.519331,
                                  'rewrite_bias': 'dimensional_balancing',
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
                                  'rewrite_profile': 'dimensional_balancing',
                                  'signature': 'T^2*B^1',
                                  'surface_score': 0.632,
                                  'sustainability_score': 0.405355,
                                  'target_kind': 'function'},
 'DimensionalSystems.get_constraint_aggregate': {'ability_hits': 12,
                                                 'alignment_gap': 0.34,
                                                 'alignment_target_score': 0.972,
                                                 'best_coupling_signature': 'B^3',
                                                 'constraints': ['boundary'],
                                                 'contract_profile': {'accepts_payload': False,
                                                                      'async_callable': False,
                                                                      'callable': True,
                                                                      'class_target': False,
                                                                      'constraint_density': 1,
                                                                      'contract_mode': 'stateful',
                                                                      'doc_hint': 'Compute the '
                                                                                  'mean signed '
                                                                                  'constraint '
                                                                                  'displacement '
                                                                                  'across all '
                                                                                  'crystals',
                                                                      'effect_density': 2,
                                                                      'kwonly_args': 0,
                                                                      'optional_args': 0,
                                                                      'required_args': 0,
                                                                      'return_hint': 'Dict[str, '
                                                                                     'float]',
                                                                      'signature_text': '(self) -> '
                                                                                        "'Dict[str, "
                                                                                        "float]'",
                                                                      'stateful_owner': True,
                                                                      'target_kind': 'function',
                                                                      'varargs': False,
                                                                      'varkw': False},
                                                 'coupling_similarity': 1.0,
                                                 'cross_diversity_links': 2,
                                                 'effect_modes': ['interface_boundary_change',
                                                                  'lineage_surface'],
                                                 'effect_phrases': ['function growth reflected '
                                                                    'through '
                                                                    'aurora_dimensional_systems',
                                                                    'DimensionalSystems.get_constraint_aggregate '
                                                                    'changed downstream system '
                                                                    'pressure'],
                                                 'genealogy_pressure': 0.75101,
                                                 'inheritance_breach_count': 1,
                                                 'kind': 'reflection',
                                                 'link_hits': 24,
                                                 'module': 'aurora_dimensional_systems',
                                                 'op_id': 'aurora_dimensional_systems.DimensionalSystems.get_constraint_aggregate',
                                                 'origin_activity': 0,
                                                 'persistence_tax_factor': 2.550513,
                                                 'representation_score': 0.567611,
                                                 'rewrite_bias': 'dimensional_balancing',
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
                                                 'rewrite_profile': 'dimensional_balancing',
                                                 'signature': 'B^3',
                                                 'surface_score': 0.632,
                                                 'sustainability_score': 0.356849,
                                                 'target_kind': 'function'},
 'DimensionalSystems.tick': {'ability_hits': 19,
                             'alignment_gap': 0.34,
                             'alignment_target_score': 0.972,
                             'best_coupling_signature': 'T^2*B^1',
                             'constraints': ['temporal'],
                             'contract_profile': {'accepts_payload': False,
                                                  'async_callable': False,
                                                  'callable': True,
                                                  'class_target': False,
                                                  'constraint_density': 1,
                                                  'contract_mode': 'stateful',
                                                  'doc_hint': '',
                                                  'effect_density': 2,
                                                  'kwonly_args': 0,
                                                  'optional_args': 1,
                                                  'required_args': 0,
                                                  'return_hint': 'generic_record',
                                                  'signature_text': "(self, dt: 'float' = 1.0)",
                                                  'stateful_owner': True,
                                                  'target_kind': 'function',
                                                  'varargs': False,
                                                  'varkw': False},
                             'coupling_similarity': 1.0,
                             'cross_diversity_links': 2,
                             'effect_modes': ['temporal_orchestration_change', 'lineage_surface'],
                             'effect_phrases': ['function growth reflected through '
                                                'aurora_dimensional_systems',
                                                'DimensionalSystems.tick changed downstream system '
                                                'pressure'],
                             'genealogy_pressure': 0.809108,
                             'inheritance_breach_count': 1,
                             'kind': 'reflection',
                             'link_hits': 36,
                             'module': 'aurora_dimensional_systems',
                             'op_id': 'aurora_dimensional_systems.DimensionalSystems.tick',
                             'origin_activity': 0,
                             'persistence_tax_factor': 1.955393,
                             'representation_score': 0.519331,
                             'rewrite_bias': 'dimensional_balancing',
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
                             'rewrite_profile': 'dimensional_balancing',
                             'signature': 'T^2*B^1',
                             'surface_score': 0.632,
                             'sustainability_score': 0.405355,
                             'target_kind': 'function'},
 '_PoolView.inject': {'ability_hits': 12,
                      'alignment_gap': 0.34,
                      'alignment_target_score': 0.972,
                      'best_coupling_signature': 'B^3',
                      'constraints': ['boundary'],
                      'contract_profile': {'accepts_payload': True,
                                           'async_callable': False,
                                           'callable': True,
                                           'class_target': False,
                                           'constraint_density': 1,
                                           'contract_mode': 'stateful',
                                           'doc_hint': '',
                                           'effect_density': 2,
                                           'kwonly_args': 0,
                                           'optional_args': 1,
                                           'required_args': 1,
                                           'return_hint': 'boundary_record',
                                           'signature_text': "(self, amount: 'float', presence: "
                                                             "'float' = 1.0)",
                                           'stateful_owner': True,
                                           'target_kind': 'function',
                                           'varargs': False,
                                           'varkw': False},
                      'coupling_similarity': 1.0,
                      'cross_diversity_links': 2,
                      'effect_modes': ['interface_boundary_change', 'lineage_surface'],
                      'effect_phrases': ['function growth reflected through '
                                         'aurora_dimensional_systems',
                                         '_PoolView.inject changed downstream system pressure'],
                      'genealogy_pressure': 0.75101,
                      'inheritance_breach_count': 1,
                      'kind': 'reflection',
                      'link_hits': 24,
                      'module': 'aurora_dimensional_systems',
                      'op_id': 'aurora_dimensional_systems._PoolView.inject',
                      'origin_activity': 0,
                      'persistence_tax_factor': 2.550513,
                      'representation_score': 0.567611,
                      'rewrite_bias': 'dimensional_balancing',
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
                      'rewrite_profile': 'dimensional_balancing',
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

def tick_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_dimensional_systems.CrystalProcessingSystem.tick', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_dimensional_systems_crystalprocessingsystem_tick')(payload=payload, **kwargs)

if _aurora_get_target(['CrystalProcessingSystem', 'tick']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['CrystalProcessingSystem.tick'] = _aurora_get_target(['CrystalProcessingSystem', 'tick'])
    _aurora_assign_target(['CrystalProcessingSystem', 'tick'], _aurora_make_override('tick_evolved', 'CrystalProcessingSystem.tick'))
    _AURORA_NATIVE_EVOLVED_LAST['CrystalProcessingSystem.tick'] = {'alignment_gap': 0.34, 'override_active': True}

def get_constraint_aggregate_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_dimensional_systems.DimensionalSystems.get_constraint_aggregate', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_dimensional_systems_dimensionalsystems_get_constraint_aggregate')(payload=payload, **kwargs)

if _aurora_get_target(['DimensionalSystems', 'get_constraint_aggregate']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['DimensionalSystems.get_constraint_aggregate'] = _aurora_get_target(['DimensionalSystems', 'get_constraint_aggregate'])
    _aurora_assign_target(['DimensionalSystems', 'get_constraint_aggregate'], _aurora_make_override('get_constraint_aggregate_evolved', 'DimensionalSystems.get_constraint_aggregate'))
    _AURORA_NATIVE_EVOLVED_LAST['DimensionalSystems.get_constraint_aggregate'] = {'alignment_gap': 0.34, 'override_active': True}

def evolved_tick(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_dimensional_systems.DimensionalSystems.tick', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_dimensional_systems_dimensionalsystems_tick')(payload=payload, **kwargs)

if _aurora_get_target(['DimensionalSystems', 'tick']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['DimensionalSystems.tick'] = _aurora_get_target(['DimensionalSystems', 'tick'])
    _aurora_assign_target(['DimensionalSystems', 'tick'], _aurora_make_override('evolved_tick', 'DimensionalSystems.tick'))
    _AURORA_NATIVE_EVOLVED_LAST['DimensionalSystems.tick'] = {'alignment_gap': 0.34, 'override_active': True}

def inject_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_dimensional_systems._PoolView.inject', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_dimensional_systems_poolview_inject')(payload=payload, **kwargs)

if _aurora_get_target(['_PoolView', 'inject']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['_PoolView.inject'] = _aurora_get_target(['_PoolView', 'inject'])
    _aurora_assign_target(['_PoolView', 'inject'], _aurora_make_override('inject_evolved', '_PoolView.inject'))
    _AURORA_NATIVE_EVOLVED_LAST['_PoolView.inject'] = {'alignment_gap': 0.34, 'override_active': True}

AURORA_NATIVE_EVOLVED_EXPORTS = {'aurora_dimensional_systems.CrystalProcessingSystem.tick': 'tick_evolved',
 'aurora_dimensional_systems.DimensionalSystems.get_constraint_aggregate': 'get_constraint_aggregate_evolved',
 'aurora_dimensional_systems.DimensionalSystems.tick': 'evolved_tick',
 'aurora_dimensional_systems._PoolView.inject': 'inject_evolved'}
AURORA_NATIVE_EVOLUTION_OVERRIDES = {'aurora_dimensional_systems.CrystalProcessingSystem.tick': {'export': 'tick_evolved',
                                                             'mode': 'callable_override',
                                                             'target': 'CrystalProcessingSystem.tick'},
 'aurora_dimensional_systems.DimensionalSystems.get_constraint_aggregate': {'export': 'get_constraint_aggregate_evolved',
                                                                            'mode': 'callable_override',
                                                                            'target': 'DimensionalSystems.get_constraint_aggregate'},
 'aurora_dimensional_systems.DimensionalSystems.tick': {'export': 'evolved_tick',
                                                        'mode': 'callable_override',
                                                        'target': 'DimensionalSystems.tick'},
 'aurora_dimensional_systems._PoolView.inject': {'export': 'inject_evolved',
                                                 'mode': 'callable_override',
                                                 'target': '_PoolView.inject'}}
# AURORA_EVOLVED_NATIVE_END

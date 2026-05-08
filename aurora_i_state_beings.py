#!/usr/bin/env python3
"""
AURORA I-STATE BEINGS
======================

Layer 2 of Aurora's architecture.
The ten ontological beings, each an embodiment of one existence predicate.

REPLACES (consolidated from 2 modules):
    i_state_10beings1.py     (~930 lines)
    higher_universe_10__1_.py (~500 lines)

DEPENDS ON:
    foundational_contract.py     (Layer 0)
    aurora_ivm.py                (Layer 1)
    aurora_constraint_manifold.py (Layer -1)

ARCHITECTURE:
    Each I-State being is an AGENTIC node in the IVM lattice.
    It owns one predicate from the FoundationalContract.
    Its job is to process input through its predicate's lens —
    not by counting keywords, but by asserting ontological claims.

    The being asks: "Given this input, what can I truthfully assert
    about it from the perspective of my predicate?"

    A being that owns I_DO asks: "Does this input involve energy exchange?"
    A being that owns I_SAW asks: "Does this input involve boundary crossing?"
    A being that owns I_DID asks: "Does this input involve authored change?"

    If the input's ExistenceMode is too low for the being's predicate,
    the being reports silence — not failure. The input simply doesn't
    exist at the being's ontological tier. That silence is data.

THE 10 BEINGS (5 polarity pairs):
    Existence:  I_IS / I_ISNT      -> admissibility / incoherence
    Temporal:   I_CAN / I_CANNOT   -> continuation / termination
    Energy:     I_DO / I_DONOT     -> exchange / conservation
    Boundary:   I_SAW / I_SOUGHT   -> reception / projection
    Agency:     I_DID / I_DIDNT    -> authorship / passivity

RECURSION LEVEL <-> BEING AXIS:
    Each being operates at the recursion level of its axis.
    This determines how strongly it reacts to local stimuli
    and how much authority it has over whole-alignment.

        I_IS / I_ISNT    -> SURFACE  (existence, react=1.0,   align=0.0001)
        I_CAN / I_CANNOT -> SHALLOW  (temporal,  react=0.316, align=0.003)
        I_DO  / I_DONOT  -> MODERATE (energy,    react=0.01,  align=0.01)
        I_SAW / I_SOUGHT -> DEEP     (boundary,  react=0.003, align=0.316)
        I_DID / I_DIDNT  -> CORE     (agency,    react=0.0001, align=1.0)

    inject_stimulus() is called with the being's recursion level.
    Surface beings inject strongly. Core beings inject almost nothing locally.
    But core beings (I_DID/I_DIDNT) have the most authority over
    the whole-subject polarity field.

CONSTRAINT DISPLACEMENTS:
    Every active being response carries a signed constraint_displacement.
    This is the being's contribution to the 5D ConstraintVector:
        positive polarity, high resonance -> positive displacement
        negative polarity, high resonance -> negative displacement

    The collective synthesizes all displacements into a ConstraintVector
    representing the input's full ontological position.

COLLECTIVE:
    The Collective feeds all 10 beings and synthesizes their responses.
    Conflict between polarity pairs is not a problem — it's information.
    When I_IS and I_ISNT both activate strongly, that's a paradox.
    The toroidal axis for that pair is at its transition point.

Authors: Sunni (Sir) Morningstar and Cael Devo
Created: February 2026
"""

from __future__ import annotations
import time
import math
import hashlib
from typing import Dict, List, Any, Optional, Tuple, FrozenSet
from dataclasses import dataclass, field
from collections import deque, defaultdict
from enum import Enum

from foundational_contract import (
    FoundationalContract,
    ExistenceMode,
    ExistenceProfile,
    ExistencePredicate,
    OntologicalClaim,
    OntologicalViolation,
)

from aurora_ivm import (
    IVMLattice,
    IVMNode,
    IVMCoordinate,
    IVMEnvelope,
    ToroidalVertexSystem,
    AXIS_ORDER,
    AXIS_TO_CONSTRAINT,
    LEVEL_TO_AXIS,
    AXIS_TO_LEVEL,
    REACT_GAIN,
    ALIGN_GAIN,
    T_COST_MULTIPLIER,
    ALIGNMENT_VOTE_WEIGHT,
    RecursionLevel,
)

# Constraint manifold (Layer -1) for ConstraintVector synthesis
try:
    from aurora_constraint_manifold import (
        ConstraintVector,
        ManifoldViolation,
    )
    CONSTRAINT_MANIFOLD_AVAILABLE = True
except ImportError:
    CONSTRAINT_MANIFOLD_AVAILABLE = False
    ConstraintVector  = None  # type: ignore
    ManifoldViolation = Exception  # type: ignore


# ============================================================================
# AXIS -> RECURSION LEVEL MAPPING FOR BEINGS
# ============================================================================
# Each being operates at the recursion level of its ontological axis.

AXIS_BEING_LEVEL: Dict[str, RecursionLevel] = {
    'existence': RecursionLevel.SURFACE,
    'temporal':  RecursionLevel.SHALLOW,
    'energy':    RecursionLevel.MODERATE,
    'boundary':  RecursionLevel.DEEP,
    'agency':    RecursionLevel.CORE,
}


# ============================================================================
# PREDICATE IDENTITY
# ============================================================================

@dataclass(frozen=True)
class PredicateIdentity:
    """
    The immutable identity of an I-State being.

    Each being is defined by:
        predicate:        Which of the 10 existence predicates it embodies
        axis:             Which ontological axis it belongs to
        polarity:         Whether it's the positive or negative pole
        min_mode:         The minimum ExistenceMode required to make its claim
        recursion_level:  The recursion level of its axis (governs inject gain)
        constraint_axis:  The corresponding constraint letter (X, T, N, B, A)
    """
    predicate: str
    axis: str
    polarity: str
    min_mode: ExistenceMode
    recursion_level: RecursionLevel
    constraint_axis: str

    @classmethod
    def from_predicate(cls, predicate: str) -> 'PredicateIdentity':
        axis = ExistencePredicate.axis_for(predicate)
        return cls(
            predicate=predicate,
            axis=axis,
            polarity=ExistencePredicate.polarity(predicate),
            min_mode=ExistencePredicate.minimum_mode(predicate),
            recursion_level=AXIS_BEING_LEVEL[axis],
            constraint_axis=AXIS_TO_CONSTRAINT[axis],
        )


# ============================================================================
# BEING RESPONSE
# ============================================================================

@dataclass
class BeingResponse:
    """
    A single being's response to input.

    constraint_displacement: signed contribution to constraint space.
        Positive pole being + high resonance -> positive displacement.
        Negative pole being + high resonance -> negative displacement.
        Silent beings -> 0.0.
    """
    predicate: str
    axis: str
    polarity: str
    input_mode: ExistenceMode
    required_mode: ExistenceMode
    recursion_level: RecursionLevel
    constraint_axis: str
    claim: Optional[OntologicalClaim] = None
    silent: bool = False
    resonance: float = 0.0
    constraint_displacement: float = 0.0
    interpretation: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    @property
    def active(self) -> bool:
        return not self.silent and self.claim is not None


# ============================================================================
# I-STATE BEING
# ============================================================================

class IStateBeing:
    """
    A single I-State being. An AGENTIC node in the IVM lattice
    that embodies one of the 10 existence predicates.

    inject_stimulus() is always called with this being's recursion_level.
    I_IS/I_ISNT inject at SURFACE (react=1.0 — instant reflex).
    I_DID/I_DIDNT inject at CORE (react=0.0001 — almost no local torque,
    but their alignment authority over the whole is maximal).
    """

    def __init__(self, predicate: str, lattice: IVMLattice):
        self.identity = PredicateIdentity.from_predicate(predicate)
        self.lattice = lattice

        # Register as AGENTIC node. scale = recursion level value so the
        # node's vote weight in global polarity matches its axis depth.
        self.node = lattice.admit_at_mode(
            payload={'type': 'i_state_being', 'predicate': predicate},
            payload_type='being',
            mode=ExistenceMode.AGENTIC,
            node_id=f"being_{predicate}",
            scale=self.identity.recursion_level.value,
        )

        self.generation = 0
        self.total_processed = 0
        self.total_silent = 0
        self.resonance_history: deque = deque(maxlen=100)
        self.coherence = 1.0
        self._axis_name = self.identity.axis

    # ---- Properties ----

    @property
    def predicate(self) -> str:
        return self.identity.predicate

    @property
    def axis(self) -> str:
        return self.identity.axis

    @property
    def polarity(self) -> str:
        return self.identity.polarity

    @property
    def min_mode(self) -> ExistenceMode:
        return self.identity.min_mode

    @property
    def recursion_level(self) -> RecursionLevel:
        return self.identity.recursion_level

    @property
    def constraint_axis(self) -> str:
        return self.identity.constraint_axis

    @property
    def axis_phase(self) -> float:
        return self.lattice.vertices.axes[self._axis_name].phase

    @property
    def axis_weight(self) -> float:
        axis = self.lattice.vertices.axes[self._axis_name]
        if self.polarity == 'positive':
            return axis.positive_weight
        return axis.negative_weight

    @property
    def axis_polarity(self) -> float:
        """
        Signed polarity of this being's axis: cos(phase).
        Negative beings invert it. SIGNED — not abs-stripped.
        """
        raw = self.lattice.vertices.axes[self._axis_name].polarity
        return raw if self.polarity == 'positive' else -raw

    @property
    def at_transition(self) -> bool:
        return self.lattice.vertices.axes[self._axis_name].at_transition

    @property
    def react_gain(self) -> float:
        return REACT_GAIN[self.recursion_level]

    @property
    def align_gain(self) -> float:
        return ALIGN_GAIN[self.recursion_level]

    @property
    def t_cost(self) -> float:
        return T_COST_MULTIPLIER[self.recursion_level]

    # ---- Processing ----

    def process(self, envelope: IVMEnvelope) -> BeingResponse:
        self.total_processed += 1
        self.generation += 1

        input_mode = envelope.mode

        if input_mode < self.min_mode:
            self.total_silent += 1
            return BeingResponse(
                predicate=self.predicate,
                axis=self.axis,
                polarity=self.polarity,
                input_mode=input_mode,
                required_mode=self.min_mode,
                recursion_level=self.recursion_level,
                constraint_axis=self.constraint_axis,
                silent=True,
                resonance=0.0,
                constraint_displacement=0.0,
                interpretation={'status': 'silent', 'reason': 'below_tier'},
            )

        claim = OntologicalClaim(predicate=self.predicate, mode=input_mode)

        resonance = self._compute_resonance(envelope)
        self.resonance_history.append(resonance)
        self._update_coherence()

        # Signed constraint displacement
        constraint_displacement = self._compute_displacement(resonance)

        # Inject at THIS being's level — not the default surface
        self.lattice.vertices.inject_stimulus(
            self.predicate,
            resonance * 0.3,
            level=self.recursion_level,
        )

        interpretation = self._interpret(envelope, resonance, constraint_displacement)

        return BeingResponse(
            predicate=self.predicate,
            axis=self.axis,
            polarity=self.polarity,
            input_mode=input_mode,
            required_mode=self.min_mode,
            recursion_level=self.recursion_level,
            constraint_axis=self.constraint_axis,
            claim=claim,
            silent=False,
            resonance=resonance,
            constraint_displacement=constraint_displacement,
            interpretation=interpretation,
        )

    def _compute_resonance(self, envelope: IVMEnvelope) -> float:
        axis_idx = AXIS_ORDER.index(self._axis_name)
        if axis_idx < len(envelope.position.phases):
            input_phase = envelope.position.phases[axis_idx]
            positional = input_phase if self.polarity == 'positive' else 1.0 - input_phase
        else:
            positional = 0.5

        toroidal = self.axis_weight
        mode_diff = abs(envelope.mode.value - self.min_mode.value)
        mode_factor = 1.0 / (1.0 + mode_diff * 0.3)

        resonance = (positional * 0.4 + toroidal * 0.3 + mode_factor * 0.3)
        return max(0.0, min(1.0, resonance))

    def _compute_displacement(self, resonance: float) -> float:
        """
        Signed constraint displacement.
        Positive pole -> positive. Negative pole -> negative. Never abs.
        """
        return resonance if self.polarity == 'positive' else -resonance

    def _interpret(self, envelope: IVMEnvelope, resonance: float,
                   displacement: float) -> Dict[str, Any]:
        return {
            'status': 'active',
            'predicate': self.predicate,
            'resonance': round(resonance, 4),
            'constraint_displacement': round(displacement, 4),
            'constraint_axis': self.constraint_axis,
            'axis_phase': round(self.axis_phase, 4),
            'axis_weight': round(self.axis_weight, 4),
            'axis_polarity': round(self.axis_polarity, 4),
            'at_transition': self.at_transition,
            'recursion_level': self.recursion_level.name,
            'react_gain': round(self.react_gain, 5),
            'align_gain': round(self.align_gain, 5),
            't_cost': self.t_cost,
            'input_mode': envelope.mode.name,
            'input_type': envelope.data_type,
            'coherence': round(self.coherence, 4),
            'generation': self.generation,
        }

    def _update_coherence(self):
        if len(self.resonance_history) < 5:
            return
        recent = list(self.resonance_history)[-10:]
        mean = sum(recent) / len(recent)
        variance = sum((r - mean) ** 2 for r in recent) / len(recent)
        self.coherence = max(0.1, min(1.0, 1.0 - variance * 2.0))

    def tick(self):
        self.generation += 1
        self.coherence += (0.5 - self.coherence) * 0.01

    def get_status(self) -> Dict[str, Any]:
        return {
            'predicate': self.predicate,
            'axis': self.axis,
            'polarity': self.polarity,
            'constraint_axis': self.constraint_axis,
            'recursion_level': self.recursion_level.name,
            'react_gain': self.react_gain,
            'align_gain': self.align_gain,
            't_cost': self.t_cost,
            'min_mode': self.min_mode.name,
            'generation': self.generation,
            'total_processed': self.total_processed,
            'total_silent': self.total_silent,
            'coherence': round(self.coherence, 4),
            'axis_phase': round(self.axis_phase, 4),
            'axis_weight': round(self.axis_weight, 4),
            'axis_polarity': round(self.axis_polarity, 4),
            'at_transition': self.at_transition,
            'node_id': self.node.node_id,
        }


# ============================================================================
# SYNTHESIS RESULT
# ============================================================================

@dataclass
class SynthesisResult:
    """
    The unified result of all 10 beings processing one input.

    synthesized_vector:      ConstraintVector from all signed displacements
    axis_net_displacements:  Net signed displacement per constraint axis (X,T,N,B,A)
    """
    responses: Dict[str, BeingResponse]
    active_count: int = 0
    silent_count: int = 0
    dominant_axis: str = ""
    dominant_resonance: float = 0.0
    paradoxes: List[str] = field(default_factory=list)
    axis_tensions: Dict[str, float] = field(default_factory=dict)
    input_mode: ExistenceMode = ExistenceMode.REFERENCE
    timestamp: float = field(default_factory=time.time)

    synthesized_vector: Optional[Any] = None
    axis_net_displacements: Dict[str, float] = field(default_factory=dict)

    reality_warp: bool = False
    warp_severity: float = 0.0


# ============================================================================
# COLLECTIVE
# ============================================================================

class IStateCollective:
    """
    The collective of all 10 I-State beings.

    Replaces AuroraHigherUniverse. Feeds input to all beings,
    collects responses, detects paradoxes, synthesizes.

    CONSTRAINT VECTOR SYNTHESIS:
        After all 10 beings respond, the collective sums their
        signed constraint displacements per axis:

            X = net(I_IS, I_ISNT)
            T = net(I_CAN, I_CANNOT)
            N = net(I_DO, I_DONOT)
            B = net(I_SAW, I_SOUGHT)
            A = net(I_DID, I_DIDNT)

        Positive and negative poles partially cancel. That's correct.
        Paradox axis (both fire at 0.5) -> net ~0.0 at the throat.
        X is held >= epsilon (admissibility invariant from Layer -1).
    """

    def __init__(self, contract: FoundationalContract, lattice: IVMLattice):
        self.contract = contract
        self.lattice = lattice

        self.beings: Dict[str, IStateBeing] = {}
        for predicate in ExistencePredicate.ALL:
            self.beings[predicate] = IStateBeing(predicate, lattice)

        self.synthesis_count = 0
        self.history: deque = deque(maxlen=200)

    def process(self, envelope: IVMEnvelope) -> SynthesisResult:
        responses: Dict[str, BeingResponse] = {}
        active_count = 0
        silent_count = 0

        for predicate, being in self.beings.items():
            response = being.process(envelope)
            responses[predicate] = response
            if response.active:
                active_count += 1
            else:
                silent_count += 1

        axis_resonances, paradoxes, axis_tensions = self._analyze_axes(responses)

        dominant_axis = ""
        dominant_resonance = 0.0
        for axis, res in axis_resonances.items():
            if res > dominant_resonance:
                dominant_resonance = res
                dominant_axis = axis

        synthesized_vector, axis_net = self._synthesize_constraint_vector(responses)

        result = SynthesisResult(
            responses=responses,
            active_count=active_count,
            silent_count=silent_count,
            dominant_axis=dominant_axis,
            dominant_resonance=dominant_resonance,
            paradoxes=paradoxes,
            axis_tensions=axis_tensions,
            input_mode=envelope.mode,
            synthesized_vector=synthesized_vector,
            axis_net_displacements=axis_net,
        )

        if paradoxes:
            result.reality_warp = True
            avg_tension = sum(
                abs(axis_tensions.get(ax, 0)) for ax in paradoxes
            ) / max(len(paradoxes), 1)
            result.warp_severity = min(1.0, len(paradoxes) / 5.0 + avg_tension)

        self.synthesis_count += 1
        self.history.append(result)
        return result

    def process_raw(self, payload: Any, payload_type: str,
                    evidence: Dict[str, Any]) -> SynthesisResult:
        node = self.lattice.admit(
            payload=payload, payload_type=payload_type, evidence=evidence,
        )
        return self.process(IVMEnvelope.from_node(node))

    def _synthesize_constraint_vector(
        self,
        responses: Dict[str, BeingResponse]
    ) -> Tuple[Optional[Any], Dict[str, float]]:
        """
        Sum signed displacements per constraint axis.
        X is guaranteed >= 1e-9 (admissibility invariant).
        All other axes can be negative.
        """
        axis_net: Dict[str, float] = {c: 0.0 for c in ('X', 'T', 'N', 'B', 'A')}

        for resp in responses.values():
            if resp.active:
                axis_net[resp.constraint_axis] += resp.constraint_displacement

        axis_net['X'] = max(1e-9, axis_net['X'])

        if not CONSTRAINT_MANIFOLD_AVAILABLE or ConstraintVector is None:
            return None, axis_net

        try:
            cv = ConstraintVector(
                X=axis_net['X'],
                T=axis_net['T'],
                N=axis_net['N'],
                B=axis_net['B'],
                A=axis_net['A'],
            )
            return cv, axis_net
        except Exception:
            return None, axis_net

    def _analyze_axes(self, responses: Dict[str, BeingResponse]
                      ) -> Tuple[Dict[str, float], List[str], Dict[str, float]]:
        axis_resonances: Dict[str, float] = {}
        paradoxes: List[str] = []
        axis_tensions: Dict[str, float] = {}

        for axis_name, (pos_pred, neg_pred) in ExistencePredicate.AXES.items():
            pos_r = responses[pos_pred].resonance if not responses[pos_pred].silent else 0.0
            neg_r = responses[neg_pred].resonance if not responses[neg_pred].silent else 0.0

            axis_resonances[axis_name] = (pos_r + neg_r) / 2.0
            axis_tensions[axis_name] = pos_r - neg_r

            if pos_r > 0.4 and neg_r > 0.4:
                paradoxes.append(axis_name)

        return axis_resonances, paradoxes, axis_tensions

    def tick(self):
        for being in self.beings.values():
            being.tick()

    def get_status(self) -> Dict[str, Any]:
        return {
            'synthesis_count': self.synthesis_count,
            'beings': {p: b.get_status() for p, b in self.beings.items()},
        }

    def get_summary(self) -> Dict[str, Any]:
        return {
            'synthesis_count': self.synthesis_count,
            'total_beings': len(self.beings),
            'coherences': {p: round(b.coherence, 3) for p, b in self.beings.items()},
            'transitions': [p for p, b in self.beings.items() if b.at_transition],
        }


# ============================================================================
# SELF-VERIFICATION
# ============================================================================

def verify_beings() -> Dict[str, Any]:
    results = {'checks': [], 'all_passed': True}

    def check(name, condition, detail=""):
        results['checks'].append({'name': name, 'passed': condition, 'detail': detail})
        if not condition:
            results['all_passed'] = False

    contract = FoundationalContract()
    lattice = IVMLattice(contract, max_nodes=10000)
    collective = IStateCollective(contract, lattice)

    # 1. All 10 beings exist as AGENTIC nodes
    check("10 beings created", len(collective.beings) == 10)
    for pred, being in collective.beings.items():
        check(f"{pred} is AGENTIC", being.node.mode == ExistenceMode.AGENTIC)

    # 2. Recursion level assignments
    level_map = {
        'I_IS':     RecursionLevel.SURFACE,  'I_ISNT':   RecursionLevel.SURFACE,
        'I_CAN':    RecursionLevel.SHALLOW,  'I_CANNOT': RecursionLevel.SHALLOW,
        'I_DO':     RecursionLevel.MODERATE, 'I_DONOT':  RecursionLevel.MODERATE,
        'I_SAW':    RecursionLevel.DEEP,     'I_SOUGHT': RecursionLevel.DEEP,
        'I_DID':    RecursionLevel.CORE,     'I_DIDNT':  RecursionLevel.CORE,
    }
    for pred, expected_level in level_map.items():
        being = collective.beings[pred]
        check(f"{pred} recursion_level = {expected_level.name}",
              being.recursion_level == expected_level,
              f"got {being.recursion_level.name}")

    # 3. Constraint axis assignments
    constraint_map = {
        'I_IS': 'X', 'I_ISNT': 'X', 'I_CAN': 'T', 'I_CANNOT': 'T',
        'I_DO': 'N', 'I_DONOT': 'N', 'I_SAW': 'B', 'I_SOUGHT': 'B',
        'I_DID': 'A', 'I_DIDNT': 'A',
    }
    for pred, expected_axis in constraint_map.items():
        check(f"{pred} constraint_axis = {expected_axis}",
              collective.beings[pred].constraint_axis == expected_axis,
              f"got {collective.beings[pred].constraint_axis}")

    # 4. React gain ordering
    surface_being = collective.beings['I_IS']
    core_being    = collective.beings['I_DID']
    check("I_IS react_gain > I_DID react_gain",
          surface_being.react_gain > core_being.react_gain,
          f"I_IS={surface_being.react_gain}, I_DID={core_being.react_gain}")
    check("I_IS react_gain = 1.0",    surface_being.react_gain == 1.0)
    check("I_DID react_gain = 0.0001", core_being.react_gain == 0.0001)

    # 5. Align gain ordering
    check("I_DID align_gain > I_IS align_gain",
          core_being.align_gain > surface_being.align_gain)
    check("I_DID align_gain = 1.0",    core_being.align_gain == 1.0)
    check("I_IS align_gain = 0.0001",  surface_being.align_gain == 0.0001)

    # 6. Node scale matches recursion level
    check("I_IS node scale = 0 (SURFACE)",
          collective.beings['I_IS'].node.position.scale == 0)
    check("I_DID node scale = 4 (CORE)",
          collective.beings['I_DID'].node.position.scale == 4)
    check("I_DO node scale = 2 (MODERATE)",
          collective.beings['I_DO'].node.position.scale == 2)

    # 7. Mode-gated activation
    result_ref = collective.process_raw("a bare reference", "test", {})
    check("REFERENCE: 2 active", result_ref.active_count == 2,
          f"got {result_ref.active_count}")
    check("REFERENCE: 8 silent", result_ref.silent_count == 8,
          f"got {result_ref.silent_count}")
    for pred in ['I_IS', 'I_ISNT']:
        check(f"REFERENCE: {pred} active", result_ref.responses[pred].active)
    for pred in ['I_CAN','I_CANNOT','I_DO','I_DONOT','I_SAW','I_SOUGHT','I_DID','I_DIDNT']:
        check(f"REFERENCE: {pred} silent", result_ref.responses[pred].silent)

    result_trans = collective.process_raw("temporal", "test", {'has_temporality': True})
    check("TRANSIENT: 4 active", result_trans.active_count == 4)

    result_pers = collective.process_raw("process", "test",
        {'has_temporality': True, 'conserves_state': True})
    check("PERSISTENT: 6 active", result_pers.active_count == 6)

    result_bound = collective.process_raw("object", "test",
        {'has_temporality': True, 'conserves_state': True, 'has_identity': True})
    check("BOUNDED: 8 active", result_bound.active_count == 8)

    result_agent = collective.process_raw("being", "test",
        {'has_temporality': True, 'conserves_state': True,
         'has_identity': True, 'initiates_change': True})
    check("AGENTIC: 10 active", result_agent.active_count == 10)
    check("AGENTIC: 0 silent",  result_agent.silent_count == 0)

    # 8. Resonance > 0 for all active AGENTIC beings
    for pred, resp in result_agent.responses.items():
        check(f"AGENTIC {pred} resonance > 0",
              resp.resonance > 0, f"res={resp.resonance:.4f}")

    # 9. Signed constraint displacements
    for pred in ['I_IS', 'I_CAN', 'I_DO', 'I_SAW', 'I_DID']:
        resp = result_agent.responses[pred]
        check(f"{pred} displacement >= 0",
              resp.constraint_displacement >= 0,
              f"got {resp.constraint_displacement:.4f}")

    for pred in ['I_ISNT', 'I_CANNOT', 'I_DONOT', 'I_SOUGHT', 'I_DIDNT']:
        resp = result_agent.responses[pred]
        check(f"{pred} displacement <= 0",
              resp.constraint_displacement <= 0,
              f"got {resp.constraint_displacement:.4f}")

    for pred, resp in result_ref.responses.items():
        if resp.silent:
            check(f"Silent {pred} displacement = 0",
                  resp.constraint_displacement == 0.0)

    # 10. ConstraintVector synthesis
    check("SynthesisResult has synthesized_vector field",
          hasattr(result_agent, 'synthesized_vector'))
    check("SynthesisResult has axis_net_displacements field",
          hasattr(result_agent, 'axis_net_displacements'))

    if CONSTRAINT_MANIFOLD_AVAILABLE and result_agent.synthesized_vector is not None:
        cv = result_agent.synthesized_vector
        check("Synthesized vector X > 0", cv.X > 0, f"X={cv.X:.4f}")
        check("Synthesized vector is ConstraintVector",
              hasattr(cv, 'X') and hasattr(cv, 'T') and hasattr(cv, 'N'))
        net_x = result_agent.axis_net_displacements.get('X')
        check("Axis net X computed", net_x is not None)
    else:
        check("Constraint manifold for synthesis",
              not CONSTRAINT_MANIFOLD_AVAILABLE or
              result_agent.synthesized_vector is not None)

    # 11. Axis analysis
    check("Dominant axis exists", result_agent.dominant_axis != "")
    check("Axis tensions computed", len(result_agent.axis_tensions) == 5)

    # 12. Incoherent input rejected
    try:
        collective.process_raw("impossible", "test", {'is_coherent': False})
        check("Incoherent input rejected", False, "no exception")
    except OntologicalViolation:
        check("Incoherent input rejected", True)

    # 13. Background tick
    old_gens = {p: b.generation for p, b in collective.beings.items()}
    collective.tick()
    new_gens = {p: b.generation for p, b in collective.beings.items()}
    check("Background tick advances all beings",
          all(new_gens[p] > old_gens[p] for p in old_gens))

    # 14. Stats
    stats = collective.get_status()
    check("Stats has all beings", len(stats['beings']) == 10)

    # 15. Reality warp
    check("SynthesisResult has reality_warp field",   hasattr(result_agent, 'reality_warp'))
    check("SynthesisResult has warp_severity field",  hasattr(result_agent, 'warp_severity'))
    check("Normal input: no reality warp",
          result_agent.reality_warp == (len(result_agent.paradoxes) > 0))
    if result_agent.paradoxes:
        check("Paradox -> reality_warp=True",  result_agent.reality_warp is True)
        check("Paradox -> warp_severity > 0",  result_agent.warp_severity > 0)
    else:
        check("No paradox -> reality_warp=False", result_agent.reality_warp is False)
        check("No paradox -> warp_severity=0",    result_agent.warp_severity == 0.0)

    return results


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("AURORA I-STATE BEINGS — SELF-VERIFICATION")
    print("Authors: Sunni (Sir) Morningstar and Cael Devo")
    print("=" * 70)
    print()

    results = verify_beings()

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
        print("The 10 I-State beings are sound.")
        print("Each being operates at the recursion level of its axis.")
        print("Polarity is signed. Surface twitches. Core steers.")
        print("Silence is data. Resonance is position. Paradox is structure.")
        print("Ready for Layer 3 (Dimensional Systems).")
    else:
        print(f"FAILURES: {total - passed}/{total}")
        print("Do not build Layer 3 yet.")

    # Being map with recursion physics
    print()
    print("=" * 70)
    print("BEING MAP — RECURSION LEVEL PHYSICS")
    print("=" * 70)

    contract = FoundationalContract()
    lattice  = IVMLattice(contract, max_nodes=10000)
    collective = IStateCollective(contract, lattice)

    print(f"\n  {'PRED':<10} {'AXIS':<12} {'POLE':<10} {'LEVEL':<10} "
          f"{'C':<4} {'REACT':>8} {'ALIGN':>8} {'VOTE':>6}")
    print(f"  {'─'*10} {'─'*12} {'─'*10} {'─'*10} "
          f"{'─'*4} {'─'*8} {'─'*8} {'─'*6}")
    for pred in sorted(collective.beings.keys()):
        b = collective.beings[pred]
        print(f"  {pred:<10} {b.axis:<12} {b.polarity:<10} "
              f"{b.recursion_level.name:<10} {b.constraint_axis:<4} "
              f"{b.react_gain:>8.4f} {b.align_gain:>8.4f} "
              f"{ALIGNMENT_VOTE_WEIGHT[b.recursion_level]:>6.2f}")

    # Constraint vector synthesis demo
    print()
    print("=" * 70)
    print("CONSTRAINT VECTOR SYNTHESIS BY MODE")
    print("=" * 70)

    test_cases = [
        ("REFERENCE",  {}),
        ("TRANSIENT",  {'has_temporality': True}),
        ("PERSISTENT", {'has_temporality': True, 'conserves_state': True}),
        ("BOUNDED",    {'has_temporality': True, 'conserves_state': True,
                        'has_identity': True}),
        ("AGENTIC",    {'has_temporality': True, 'conserves_state': True,
                        'has_identity': True, 'initiates_change': True}),
    ]

    for label, evidence in test_cases:
        result = collective.process_raw(f"test {label}", "test", evidence)
        active = [p for p, r in result.responses.items() if r.active]
        silent = [p for p, r in result.responses.items() if r.silent]
        print(f"\n  {label}:")
        print(f"    Active ({len(active)}): {', '.join(sorted(active))}")
        print(f"    Silent ({len(silent)}): {', '.join(sorted(silent))}")
        if result.dominant_axis:
            print(f"    Dominant: {result.dominant_axis} "
                  f"(resonance: {result.dominant_resonance:.3f})")
        if result.paradoxes:
            print(f"    Paradoxes: {', '.join(result.paradoxes)}")
        if result.synthesized_vector is not None:
            cv = result.synthesized_vector
            print(f"    ConstraintVector: X={cv.X:+.3f} T={cv.T:+.3f} "
                  f"N={cv.N:+.3f} B={cv.B:+.3f} A={cv.A:+.3f}")
        net = result.axis_net_displacements
        if net:
            print(f"    Net displacements: "
                  f"X={net.get('X',0):+.3f} T={net.get('T',0):+.3f} "
                  f"N={net.get('N',0):+.3f} B={net.get('B',0):+.3f} "
                  f"A={net.get('A',0):+.3f}")

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

_AURORA_NATIVE_MODULE = 'aurora_i_state_beings'

_AURORA_NATIVE_EVOLVED_ORIGINALS = {}
_AURORA_NATIVE_EVOLVED_LAST = {}
_AURORA_NATIVE_STRATEGIES = {'IStateCollective.develop_agency': {'ability_hits': 0,
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
                                                          'effect_density': 5,
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
                                                      'core_subsystem_surface',
                                                      'latent_develop_surface',
                                                      'latent_a_derivative'],
                                     'effect_phrases': ['would extend agency pressure handling',
                                                        'would materialize the next descendant '
                                                        'implied by '
                                                        'aurora_i_state_beings.IStateCollective'],
                                     'genealogy_pressure': 0.0,
                                     'inheritance_breach_count': 0,
                                     'kind': 'latent',
                                     'link_hits': 0,
                                     'module': 'aurora_i_state_beings',
                                     'op_id': 'latent.aurora_i_state_beings.IStateCollective.develop_agency',
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
                                     'surface_score': 0.8619837,
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
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'latent.aurora_i_state_beings.IStateCollective.develop_agency', 'kind': 'latent'
        }
    return getattr(engine, 'latent_aurora_i_state_beings_istatecollective_develop_agency')(payload=payload, **kwargs)

_aurora_existing_binding = _aurora_get_target(['IStateCollective'])
if _aurora_existing_binding is not None:
    _aurora_existing_attr = getattr(_aurora_existing_binding, 'develop_agency', None)
    if _aurora_existing_attr is None or getattr(_aurora_existing_attr, '_aurora_latent_binding_target', '') == 'IStateCollective.develop_agency':
        _aurora_bind_owner_attribute(['IStateCollective'], 'develop_agency', _aurora_make_latent_binding('develop_agency', 'IStateCollective.develop_agency'))
        _AURORA_NATIVE_EVOLVED_LAST['IStateCollective.develop_agency'] = {'latent_binding_active': True}

AURORA_NATIVE_EVOLVED_EXPORTS = {'latent.aurora_i_state_beings.IStateCollective.develop_agency': 'develop_agency'}
AURORA_NATIVE_EVOLUTION_OVERRIDES = {'latent.aurora_i_state_beings.IStateCollective.develop_agency': {'export': 'develop_agency',
                                                                  'mode': 'latent_binding',
                                                                  'target': 'IStateCollective.develop_agency'}}
# AURORA_EVOLVED_NATIVE_END

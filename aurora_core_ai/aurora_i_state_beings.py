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
# Authors: Sunni (Sir) Morningstar & Cael Devo

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
# I-STATE AUTHORITY MATRIX
# (Derived from AURORA_UNIFIED_FIELD_SPEC.md — 2026-03-16)
# ============================================================================
# Full three-dimensional authority profile per I-State pair.
#
#   cost            — baseline energy cost of this axis (NC dim 3, COST)
#   magnitude_role  — role in the Magnitude = (B×T×X)/N formula (NC dim 1)
#   impact_role     — role in Impact = Magnitude×A formula (NC dim 1+OPERATOR[A])
#   nc_dim          — primary NC dimension this pair most directly exercises
#   cascade_on_fail — True if failure of this being cascades into other dims
#   physical_analog — the physics system this constraint mirrors
#
# Firing authority rule:
#   All ten I-State beings MUST fire collectively on every cognitive event.
#   No being is background. No being is negligible.
#   Underweighting any pair starves that field property from Aurora's cognition.
I_STATE_AUTHORITY: Dict[str, Dict[str, Any]] = {
    "IS/ISNT": {
        "axis":            "X",
        "cost":            1.0,
        "magnitude_role":  "coherence_anchor",         # grounds magnitude in admissibility
        "impact_role":     "gate",                     # widest collective reach; all impact flows through X
        "nc_dim":          "OPERATOR",                 # X is the existence gate operator
        "cascade_on_fail": False,
        "physical_analog": "weak/strong force",        # cheapest, smallest scale, holds field together
    },
    "CAN/CANT": {
        "axis":            "T",
        "cost":            2.5,
        "magnitude_role":  "propagation_multiplier",   # how far magnitude reaches through time
        "impact_role":     "hidden_fulcrum",           # cheap to perturb, cascade-catastrophic on failure
        "nc_dim":          "DIFFERENCE",               # temporal sequence creates delta from expected tick
        "cascade_on_fail": True,                       # T failure cascades: context, coherence, multi-turn
        "physical_analog": "general_relativity",       # B-T coupling mirrors mass-time warping
    },
    "DO/DONT": {
        "axis":            "N",
        "cost":            0.0,
        "magnitude_role":  "conservation_reference",   # normalization denominator in magnitude formula
        "impact_role":     "zero_point",               # normalizes all measurement; zero-cost reference
        "nc_dim":          "COST",                     # N is the cost dimension — all costs measured against it
        "cascade_on_fail": False,
        "physical_analog": "thermodynamics",           # energy neither created nor destroyed
    },
    "SAW/SAUNT": {
        "axis":            "B",
        "cost":            18.0,
        "magnitude_role":  "primary_magnitude_carrier", # boundary IS the measure; B drives the formula numerator
        "impact_role":     "stabilizing",              # expensive but stabilizing — gravitational analog
        "nc_dim":          "MAGNITUDE",                # B is the primary NC magnitude dimension
        "cascade_on_fail": False,
        "physical_analog": "gravity",                  # boundary maintenance costly but structurally essential
    },
    "DID/DIDNT": {
        "axis":            "A",
        "cost":            50.0,
        "magnitude_role":  "impact_multiplier",        # converts field potential (magnitude) into directed outcome
        "impact_role":     "corrective",               # closes understanding loop; agency without energy = incoherent
        "nc_dim":          "POLARITY",                 # agency sets direction/polarity of impact
        "cascade_on_fail": False,
        "physical_analog": "electromagnetism",         # precise, corrective, operates at sovereign scale
    },
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


#!/usr/bin/env python3
"""
FOUNDATIONAL CONTRACT — THE GRAMMAR OF EXISTENCE (Layer 0)
===========================================================

Layer 0 of Aurora's architecture.
Nothing processes, moves, stores, or thinks until this layer says it can exist.

This module is NOT a controller, evaluator, or processor.
It is a classifier of being.

PURPOSE:
    Define what kinds of things are allowed to exist at all,
    before any system routes, processes, or stores them.

ONTOLOGICAL PRINCIPLE:
    The I-States are not traversal semantics. They are existence predicates.
    Movement across the lattice is a consequence of being, not the definition.

FIVE ANCHORS:
    1. Only what can exist is allowed to appear.
       Validation is not a step — it is a condition of existence.
    2. Existence is layered, not binary.
       Possibility, existence, persistence, objecthood, and agency are
       different ontological tiers, not degrees of confidence.
    3. Possibility is permission, not state.
       Represented implicitly as the absence of contradiction, not as data.
    4. Constraints define admissible configurations, not evaluated states.
       Order is dependency-based, used only for fail-fast elimination.
    5. Speed comes from eliminating representational freedom, not faster computation.
       If something cannot exist, it never costs time.

EXISTENCE MODES (not types — ontological commitments):
    Reference   → Exists only as relation or description
    Transient   → Exists in time but has no guaranteed continuation
    Persistent  → Exists across time, may conserve state
    Bounded     → Persistent + form, has identity and separability
    Agentic     → Bounded + energy-bearing, can initiate transitions

DEPENDENCY IS DEFINITIONAL:
    Claiming a higher mode automatically implies all lower modes.
    If something is Agentic, it IS bounded, persistent, temporal, and existent.
    No checks. No conditionals. The claim carries its prerequisites.

CONSTRAINT MANIFOLD ALIGNMENT:
    Each ExistenceMode activates constraints hierarchically:
        REFERENCE:  X > 0, T=0, N=0, B=0, A=0  (existence only)
        TRANSIENT:  X > 0, T > 0, N=0, B=0, A=0  (+ time)
        PERSISTENT: X > 0, T > 0, N > 0, B=0, A=0  (+ energy)
        BOUNDED:    X > 0, T > 0, N > 0, B > 0, A=0  (+ boundary)
        AGENTIC:    X > 0, T > 0, N > 0, B > 0, A > 0  (all five)
    
    The 10 I-States map to constraint axes:
        I_IS/I_ISNT     → X axis (existence)
        I_CAN/I_CANNOT  → T axis (time)
        I_DO/I_DONOT    → N axis (energy)
        I_SAW/I_SOUGHT  → B axis (boundary)
        I_DID/I_DIDNT   → A axis (agency)

Authors: Sunni (Sir) Morningstar and Cael Devo
Created: February 2026
"""

from __future__ import annotations
from enum import IntEnum, auto
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple, FrozenSet, Set, List

# Import constraint manifold (Layer -1)
try:
    from aurora_constraint_manifold import (
        Constraint,
        ConstraintVector,
        ManifoldViolation,
    )
    CONSTRAINT_MANIFOLD_AVAILABLE = True
except ImportError:
    CONSTRAINT_MANIFOLD_AVAILABLE = False
    # Fallback if running standalone
    class Constraint:
        X, T, N, B, A = 0, 1, 2, 3, 4
    ConstraintVector = None
    ManifoldViolation = Exception


# ============================================================================
# EXISTENCE MODES — THE ONTOLOGICAL LADDER
# ============================================================================

class ExistenceMode(IntEnum):
    """
    The five modes of being, ordered by ontological commitment.

    These are NOT types to be assigned. They are claims about what
    something IS, and each claim carries all claims below it.

    The ordering is definitional:
        Reference < Transient < Persistent < Bounded < Agentic

    This means:
        - Everything Transient is also Reference-valid
        - Everything Persistent also has temporality
        - Everything Bounded also persists
        - Everything Agentic also has boundary, persistence, time, and existence
    
    CONSTRAINT ACTIVATION:
        Each mode activates one additional constraint:
        REFERENCE  → X active
        TRANSIENT  → X, T active
        PERSISTENT → X, T, N active
        BOUNDED    → X, T, N, B active
        AGENTIC    → X, T, N, B, A active (all five)
    """
    REFERENCE  = 1   # Exists only as relation/description. No time, energy, boundary, agency.
    TRANSIENT  = 2   # Exists in time. No guaranteed continuation. No energy, boundary, agency.
    PERSISTENT = 3   # Exists across time. May conserve state. No boundary, no agency.
    BOUNDED    = 4   # Persistent + form. Has identity and separability. No initiation of change.
    AGENTIC    = 5   # Bounded + energy-bearing. Can initiate transitions and author outcomes.

    def to_constraint_vector(self, magnitude: float = 1.0) -> Optional[ConstraintVector]:
        """
        Convert ExistenceMode to a ConstraintVector.
        
        Each mode activates constraints hierarchically:
            REFERENCE:  [X, 0, 0, 0, 0]
            TRANSIENT:  [X, T, 0, 0, 0]
            PERSISTENT: [X, T, N, 0, 0]
            BOUNDED:    [X, T, N, B, 0]
            AGENTIC:    [X, T, N, B, A]
        
        Args:
            magnitude: The activation strength (default 1.0)
        
        Returns:
            ConstraintVector if manifold available, None otherwise
        """
        if not CONSTRAINT_MANIFOLD_AVAILABLE or ConstraintVector is None:
            return None
        
        # Base existence magnitude (always positive)
        X = magnitude
        
        # Hierarchical activation
        if self == ExistenceMode.REFERENCE:
            return ConstraintVector(X=X, T=0, N=0, B=0, A=0)
        elif self == ExistenceMode.TRANSIENT:
            return ConstraintVector(X=X, T=magnitude, N=0, B=0, A=0)
        elif self == ExistenceMode.PERSISTENT:
            return ConstraintVector(X=X, T=magnitude, N=magnitude, B=0, A=0)
        elif self == ExistenceMode.BOUNDED:
            return ConstraintVector(X=X, T=magnitude, N=magnitude, B=magnitude, A=0)
        elif self == ExistenceMode.AGENTIC:
            return ConstraintVector(X=X, T=magnitude, N=magnitude, B=magnitude, A=magnitude)
        
        return None
    
    def active_constraints(self) -> List[str]:
        """
        Return which constraints are active at this mode.
        
        Returns list of constraint names: ['X', 'T', 'N', 'B', 'A']
        """
        if self == ExistenceMode.REFERENCE:
            return ['X']
        elif self == ExistenceMode.TRANSIENT:
            return ['X', 'T']
        elif self == ExistenceMode.PERSISTENT:
            return ['X', 'T', 'N']
        elif self == ExistenceMode.BOUNDED:
            return ['X', 'T', 'N', 'B']
        elif self == ExistenceMode.AGENTIC:
            return ['X', 'T', 'N', 'B', 'A']
        return []
    
    def constraint_count(self) -> int:
        """Return number of active constraints at this mode."""
        return len(self.active_constraints())


# ============================================================================
# I-STATE EXISTENCE PREDICATES
# ============================================================================

class ExistencePredicate:
    """
    The ten I-States rewritten as existence predicates.

    These are NOT flags, scores, or traversal directions.
    Each is a claim about what mode of existence something has,
    and what that mode permits.

    The five axes (each a polarity):
        Existence:  I_IS / I_ISNT      → Is this configuration ontologically admissible?
        Temporal:   I_CAN / I_CANNOT   → Does this mode admit lawful continuation?
        Energy:     I_DO / I_DONOT     → Is energy exchange permitted from this mode?
        Boundary:   I_SAW / I_SOUGHT   → Did interaction cross inward or project outward?
        Agency:     I_DID / I_DIDNT    → Is this transition authored or passive?

    CRITICAL MAPPING — Each polarity pair requires a minimum ExistenceMode:
        I_IS / I_ISNT       → Available at REFERENCE and above (existence itself)
        I_CAN / I_CANNOT    → Available at TRANSIENT and above (requires temporality)
        I_DO / I_DONOT      → Available at PERSISTENT and above (requires state conservation)
        I_SAW / I_SOUGHT    → Available at BOUNDED and above (requires boundary to cross)
        I_DID / I_DIDNT     → Available at AGENTIC only (requires agency to author)
    
    CONSTRAINT AXIS MAPPING:
        I_IS/I_ISNT     → X axis (Constraint.X)
        I_CAN/I_CANNOT  → T axis (Constraint.T)
        I_DO/I_DONOT    → N axis (Constraint.N)
        I_SAW/I_SOUGHT  → B axis (Constraint.B)
        I_DID/I_DIDNT   → A axis (Constraint.A)
    """

    # Minimum existence mode required to make each claim
    REQUIRED_MODE = {
        # Existence axis — the most fundamental claim
        'I_IS':     ExistenceMode.REFERENCE,
        'I_ISNT':   ExistenceMode.REFERENCE,

        # Temporal axis — requires being-in-time
        'I_CAN':    ExistenceMode.TRANSIENT,
        'I_CANNOT': ExistenceMode.TRANSIENT,

        # Energy axis — requires state that can be affected
        'I_DO':     ExistenceMode.PERSISTENT,
        'I_DONOT':  ExistenceMode.PERSISTENT,

        # Boundary axis — requires form that separates inside from outside
        'I_SAW':    ExistenceMode.BOUNDED,
        'I_SOUGHT': ExistenceMode.BOUNDED,

        # Agency axis — requires the capacity to initiate
        'I_DID':    ExistenceMode.AGENTIC,
        'I_DIDNT':  ExistenceMode.AGENTIC,
    }

    # Which predicates are the positive/negative poles of each axis
    AXES = {
        'existence': ('I_IS',     'I_ISNT'),
        'temporal':  ('I_CAN',    'I_CANNOT'),
        'energy':    ('I_DO',     'I_DONOT'),
        'boundary':  ('I_SAW',    'I_SOUGHT'),
        'agency':    ('I_DID',    'I_DIDNT'),
    }

    # Map I-State predicates to constraint axes
    CONSTRAINT_MAPPING = {
        'I_IS':     'X',
        'I_ISNT':   'X',
        'I_CAN':    'T',
        'I_CANNOT': 'T',
        'I_DO':     'N',
        'I_DONOT':  'N',
        'I_SAW':    'B',
        'I_SOUGHT': 'B',
        'I_DID':    'A',
        'I_DIDNT':  'A',
    }

    # All valid predicate names
    ALL = frozenset(REQUIRED_MODE.keys())

    @classmethod
    def axis_for(cls, predicate: str) -> Optional[str]:
        """Return which axis a predicate belongs to."""
        for axis_name, (pos, neg) in cls.AXES.items():
            if predicate in (pos, neg):
                return axis_name
        return None

    @classmethod
    def polarity(cls, predicate: str) -> Optional[str]:
        """Return whether a predicate is 'positive' or 'negative' on its axis."""
        for axis_name, (pos, neg) in cls.AXES.items():
            if predicate == pos:
                return 'positive'
            if predicate == neg:
                return 'negative'
        return None

    @classmethod
    def minimum_mode(cls, predicate: str) -> ExistenceMode:
        """Return the minimum ExistenceMode required to assert this predicate."""
        if predicate not in cls.REQUIRED_MODE:
            raise OntologicalViolation(
                f"'{predicate}' is not a recognized existence predicate."
            )
        return cls.REQUIRED_MODE[predicate]
    
    @classmethod
    def constraint_axis(cls, predicate: str) -> Optional[str]:
        """
        Return which constraint axis this predicate measures.
        
        Returns: 'X', 'T', 'N', 'B', or 'A'
        """
        return cls.CONSTRAINT_MAPPING.get(predicate)


# ============================================================================
# ONTOLOGICAL VIOLATION — NOT AN ERROR, A NON-STATE
# ============================================================================

class OntologicalViolation(Exception):
    """
    Raised when something attempts to exist in a way that is incoherent.

    This is NOT an error in the traditional sense. It means the configuration
    was never a valid state. It could not have been formed under the grammar.

    In a fully integrated system, this exception should never be caught
    and recovered from — it indicates a structural defect in the caller,
    not a runtime condition to handle.
    """

    def __init__(self, description: str, attempted_predicate: str = "",
                 actual_mode: ExistenceMode = ExistenceMode.REFERENCE,
                 required_mode: ExistenceMode = ExistenceMode.REFERENCE):
        self.description = description
        self.attempted_predicate = attempted_predicate
        self.actual_mode = actual_mode
        self.required_mode = required_mode
        super().__init__(self._format())

    def _format(self) -> str:
        parts = [f"OntologicalViolation: {self.description}"]
        if self.attempted_predicate:
            parts.append(
                f"  Attempted: '{self.attempted_predicate}' "
                f"(requires {self.required_mode.name})"
            )
            parts.append(
                f"  Actual mode: {self.actual_mode.name}"
            )
        return "\n".join(parts)


# ============================================================================
# ONTOLOGICAL CLAIM — A SINGLE ASSERTION ABOUT BEING
# ============================================================================

@dataclass(frozen=True)
class OntologicalClaim:
    """
    An immutable assertion that a predicate holds for a given entity.

    Claims are not created freely. They are validated at construction.
    If the entity's existence mode cannot support the claim, construction fails.

    This is the grammar enforcement point. If this object exists,
    the claim is lawful. If it cannot be constructed, the claim was never spoken.
    """
    predicate: str
    mode: ExistenceMode
    magnitude: float = 1.0  # Strength of the claim (default 1.0)

    def __post_init__(self):
        """Validate that this claim is ontologically coherent at construction time."""
        required = ExistencePredicate.minimum_mode(self.predicate)
        if self.mode < required:
            raise OntologicalViolation(
                description=(
                    f"Cannot assert '{self.predicate}' at existence mode "
                    f"{self.mode.name}. Requires at least {required.name}."
                ),
                attempted_predicate=self.predicate,
                actual_mode=self.mode,
                required_mode=required,
            )

    @property
    def axis(self) -> str:
        """Which ontological axis this claim addresses."""
        return ExistencePredicate.axis_for(self.predicate)

    @property
    def is_positive(self) -> bool:
        """Whether this is the affirmative pole of its axis."""
        return ExistencePredicate.polarity(self.predicate) == 'positive'
    
    @property
    def constraint_axis(self) -> Optional[str]:
        """
        Which constraint axis this claim measures.
        
        Returns: 'X', 'T', 'N', 'B', or 'A'
        """
        return ExistencePredicate.constraint_axis(self.predicate)
    
    def to_constraint_displacement(self) -> Tuple[str, float]:
        """
        Express this claim as a constraint displacement.
        
        Returns: (axis, displacement) where axis is 'X'/'T'/'N'/'B'/'A'
                 and displacement is magnitude with polarity
        """
        axis = self.constraint_axis
        if axis is None:
            return ('X', 0.0)  # Fallback to existence axis
        
        # Positive predicates contribute positive displacement
        # Negative predicates contribute negative displacement
        displacement = self.magnitude if self.is_positive else -self.magnitude
        
        return (axis, displacement)


# ============================================================================
# EXISTENCE PROFILE — COMPLETE CLASSIFICATION
# ============================================================================

@dataclass
class ExistenceProfile:
    """
    A complete ontological classification of an entity.

    This describes:
    - What existence mode something has
    - Which predicates can be asserted about it
    - What constraints it satisfies
    - How it can participate in the system

    This is not computed during processing. It is determined once
    at admission time and used as a gate for all downstream operations.
    """
    mode: ExistenceMode
    permitted_predicates: FrozenSet[str] = field(default_factory=frozenset)
    forbidden_predicates: FrozenSet[str] = field(default_factory=frozenset)

    @property
    def persists(self) -> bool:
        """True if this profile is at PERSISTENT mode or above."""
        return self.mode >= ExistenceMode.PERSISTENT

    @property
    def has_boundary(self) -> bool:
        """True if this profile is at BOUNDED mode or above."""
        return self.mode >= ExistenceMode.BOUNDED

    @property
    def has_agency(self) -> bool:
        """True if this profile is at AGENTIC mode or above."""
        return self.mode >= ExistenceMode.AGENTIC

    def can_assert(self, predicate: str) -> bool:
        """Check if this profile permits asserting a given predicate."""
        return predicate in self.permitted_predicates

    def must_reject(self, predicate: str) -> bool:
        """Check if this profile forbids a given predicate."""
        return predicate in self.forbidden_predicates

    def describe(self) -> Dict[str, Any]:
        """Return a human-readable description of this profile."""
        return {
            'mode': self.mode.name,
            'mode_value': self.mode.value,
            'permitted_predicates': sorted(self.permitted_predicates),
            'forbidden_predicates': sorted(self.forbidden_predicates),
            'constraint_count': self.mode.constraint_count(),
            'active_constraints': self.mode.active_constraints(),
        }
    
    def to_constraint_vector(self, magnitude: float = 1.0) -> Optional[ConstraintVector]:
        """
        Express this profile as a ConstraintVector.
        
        Uses the mode's constraint activation pattern.
        """
        return self.mode.to_constraint_vector(magnitude)
    
    def constraint_signature(self) -> str:
        """
        Return a string signature of active constraints.
        
        Examples:
            REFERENCE:  "X"
            TRANSIENT:  "XT"
            PERSISTENT: "XTN"
            BOUNDED:    "XTNB"
            AGENTIC:    "XTNBA"
        """
        return ''.join(self.mode.active_constraints())


# ============================================================================
# DEPENDENCY AXIOMS — STRUCTURAL INVARIANTS
# ============================================================================

class DependencyAxioms:
    """
    The dependency rules that make the ontology internally coherent.

    These are not validations to run. They are structural properties
    that must hold by construction. If they don't, the grammar is broken.
    """

    @staticmethod
    def implies_lower(mode: ExistenceMode) -> Set[ExistenceMode]:
        """
        Return all modes implied by claiming this mode.

        If something is BOUNDED, it is also PERSISTENT, TRANSIENT, and REFERENCE.
        """
        if mode == ExistenceMode.REFERENCE:
            return {ExistenceMode.REFERENCE}
        elif mode == ExistenceMode.TRANSIENT:
            return {ExistenceMode.REFERENCE, ExistenceMode.TRANSIENT}
        elif mode == ExistenceMode.PERSISTENT:
            return {
                ExistenceMode.REFERENCE,
                ExistenceMode.TRANSIENT,
                ExistenceMode.PERSISTENT,
            }
        elif mode == ExistenceMode.BOUNDED:
            return {
                ExistenceMode.REFERENCE,
                ExistenceMode.TRANSIENT,
                ExistenceMode.PERSISTENT,
                ExistenceMode.BOUNDED,
            }
        elif mode == ExistenceMode.AGENTIC:
            return {
                ExistenceMode.REFERENCE,
                ExistenceMode.TRANSIENT,
                ExistenceMode.PERSISTENT,
                ExistenceMode.BOUNDED,
                ExistenceMode.AGENTIC,
            }
        return set()

    @staticmethod
    def verify_mode_coherence(mode: ExistenceMode) -> bool:
        """
        Verify that a mode's implied modes form a proper chain.

        This should always pass. If it doesn't, the mode definitions are broken.
        """
        implied = DependencyAxioms.implies_lower(mode)
        expected_count = mode.value  # REFERENCE=1, TRANSIENT=2, etc.

        if len(implied) != expected_count:
            raise AssertionError(
                f"Mode {mode.name} should imply {expected_count} modes, "
                f"but implies {len(implied)}: {implied}"
            )

        # Verify ordering
        for lower_mode in implied:
            if lower_mode > mode:
                raise AssertionError(
                    f"Mode {mode.name} implies {lower_mode.name}, "
                    f"but {lower_mode.name} is higher in the hierarchy."
                )

        return True


# ============================================================================
# FOUNDATIONAL CONTRACT — THE CLASSIFIER
# ============================================================================

class FoundationalContract:
    """
    The classifier that determines what can exist.

    This is not a validator that accepts or rejects things.
    It is the grammar that defines what kinds of things there are.

    Everything else in the system depends on this classification.
    If something cannot be classified here, it does not exist.
    """

    def __init__(self):
        """Initialize the contract with its definitional structures."""
        # Build the permitted/forbidden predicate sets for each mode
        self._permitted_by_mode: Dict[ExistenceMode, FrozenSet[str]] = {}
        self._forbidden_by_mode: Dict[ExistenceMode, FrozenSet[str]] = {}

        for mode in ExistenceMode:
            permitted = set()
            forbidden = set()

            for predicate in ExistencePredicate.ALL:
                required = ExistencePredicate.minimum_mode(predicate)
                if mode >= required:
                    permitted.add(predicate)
                else:
                    forbidden.add(predicate)

            self._permitted_by_mode[mode] = frozenset(permitted)
            self._forbidden_by_mode[mode] = frozenset(forbidden)

    def classify(self, evidence: Dict[str, Any]) -> ExistenceProfile:
        """
        Classify an entity based on evidence about its properties.

        Evidence keys:
            has_temporality: bool    — Exists in time
            conserves_state: bool    — Persists across time
            has_identity: bool       — Has boundary and separability
            initiates_change: bool   — Can author transitions

        Returns an ExistenceProfile describing what mode the entity has
        and what predicates can be asserted about it.
        """
        # Determine mode from evidence (fail-fast, dependency-ordered)
        mode = ExistenceMode.REFERENCE  # Base assumption

        if evidence.get('has_temporality', False):
            mode = ExistenceMode.TRANSIENT

        if evidence.get('conserves_state', False):
            if mode < ExistenceMode.TRANSIENT:
                raise OntologicalViolation(
                    "Cannot conserve state without temporality. "
                    "State conservation requires being-in-time."
                )
            mode = ExistenceMode.PERSISTENT

        if evidence.get('has_identity', False):
            if mode < ExistenceMode.PERSISTENT:
                raise OntologicalViolation(
                    "Cannot have identity without state persistence. "
                    "Identity requires continuity across time."
                )
            mode = ExistenceMode.BOUNDED

        if evidence.get('initiates_change', False):
            if mode < ExistenceMode.BOUNDED:
                raise OntologicalViolation(
                    "Cannot initiate change without identity. "
                    "Agency requires bounded selfhood."
                )
            mode = ExistenceMode.AGENTIC

        return ExistenceProfile(
            mode=mode,
            permitted_predicates=self._permitted_by_mode[mode],
            forbidden_predicates=self._forbidden_by_mode[mode],
        )

    def can_assert(self, mode: ExistenceMode, predicate: str) -> bool:
        """
        Check if a predicate can be asserted at a given existence mode.

        This is a definitional query, not a validation.
        It asks: "In the grammar, is this combination meaningful?"
        """
        return predicate in self._permitted_by_mode.get(mode, frozenset())

    def make_claim(
        self, mode: ExistenceMode, predicate: str, magnitude: float = 1.0
    ) -> OntologicalClaim:
        """
        Construct an ontological claim.

        This validates the claim at construction time. If the claim is
        incoherent (wrong mode for predicate), construction fails.
        """
        return OntologicalClaim(predicate=predicate, mode=mode, magnitude=magnitude)

    def describe_mode(self, mode: ExistenceMode) -> Dict[str, Any]:
        """Return a description of what a mode permits and forbids."""
        permitted = sorted(self._permitted_by_mode[mode])
        forbidden = sorted(self._forbidden_by_mode[mode])

        # Derive properties from mode
        exists = mode >= ExistenceMode.REFERENCE
        has_temporality = mode >= ExistenceMode.TRANSIENT
        persists = mode >= ExistenceMode.PERSISTENT
        has_boundary = mode >= ExistenceMode.BOUNDED
        has_agency = mode >= ExistenceMode.AGENTIC

        # Determine which axes are available
        permitted_axes = set()
        for pred in permitted:
            axis = ExistencePredicate.axis_for(pred)
            if axis:
                permitted_axes.add(axis)

        return {
            'exists': exists,
            'has_temporality': has_temporality,
            'persists': persists,
            'has_boundary': has_boundary,
            'has_agency': has_agency,
            'permitted_predicates': permitted,
            'forbidden_predicates': forbidden,
            'permitted_axes': sorted(permitted_axes),
            'constraint_signature': mode.active_constraints(),
            'constraint_count': mode.constraint_count(),
        }


# ============================================================================
# VERIFICATION — PROVE INTERNAL CONSISTENCY
# ============================================================================

def verify_foundational_contract() -> Dict[str, Any]:
    """
    Run all structural verification tests.

    This function proves that the foundational contract is internally
    consistent. It should pass at import time and after any modification.

    Returns a report of all checks performed and their results.
    """
    results = {
        'axiom_checks': [],
        'predicate_checks': [],
        'classification_checks': [],
        'claim_checks': [],
        'constraint_alignment_checks': [],
        'all_passed': True,
    }

    contract = FoundationalContract()

    # ---- 1. Verify all modes satisfy dependency axioms ----
    for mode in ExistenceMode:
        try:
            DependencyAxioms.verify_mode_coherence(mode)
            results['axiom_checks'].append({
                'mode': mode.name, 'passed': True
            })
        except AssertionError as e:
            results['axiom_checks'].append({
                'mode': mode.name, 'passed': False, 'error': str(e)
            })
            results['all_passed'] = False

    # ---- 2. Verify predicate-mode mappings are consistent ----
    for predicate, required_mode in ExistencePredicate.REQUIRED_MODE.items():
        # At the required mode, the predicate should be assertable
        can = contract.can_assert(required_mode, predicate)
        results['predicate_checks'].append({
            'predicate': predicate,
            'required_mode': required_mode.name,
            'assertable_at_required': can,
            'passed': can,
        })
        if not can:
            results['all_passed'] = False

        # Below the required mode, it should NOT be assertable
        if required_mode > ExistenceMode.REFERENCE:
            below = ExistenceMode(required_mode.value - 1)
            should_fail = not contract.can_assert(below, predicate)
            results['predicate_checks'].append({
                'predicate': predicate,
                'below_mode': below.name,
                'correctly_forbidden': should_fail,
                'passed': should_fail,
            })
            if not should_fail:
                results['all_passed'] = False

    # ---- 3. Verify classification produces correct modes ----
    test_cases = [
        ({}, ExistenceMode.REFERENCE),
        ({'has_temporality': True}, ExistenceMode.TRANSIENT),
        ({'has_temporality': True, 'conserves_state': True}, ExistenceMode.PERSISTENT),
        ({'has_temporality': True, 'conserves_state': True, 'has_identity': True},
         ExistenceMode.BOUNDED),
        ({'has_temporality': True, 'conserves_state': True, 'has_identity': True,
          'initiates_change': True}, ExistenceMode.AGENTIC),
    ]
    for evidence, expected_mode in test_cases:
        profile = contract.classify(evidence)
        passed = profile.mode == expected_mode
        results['classification_checks'].append({
            'evidence': evidence,
            'expected': expected_mode.name,
            'actual': profile.mode.name,
            'passed': passed,
        })
        if not passed:
            results['all_passed'] = False

    # ---- 4. Verify claims fail correctly below required mode ----
    claim_tests = [
        # (predicate, mode, should_succeed)
        ('I_IS', ExistenceMode.REFERENCE, True),
        ('I_CAN', ExistenceMode.REFERENCE, False),
        ('I_CAN', ExistenceMode.TRANSIENT, True),
        ('I_DO', ExistenceMode.TRANSIENT, False),
        ('I_DO', ExistenceMode.PERSISTENT, True),
        ('I_SAW', ExistenceMode.PERSISTENT, False),
        ('I_SAW', ExistenceMode.BOUNDED, True),
        ('I_DID', ExistenceMode.BOUNDED, False),
        ('I_DID', ExistenceMode.AGENTIC, True),
    ]
    for predicate, mode, should_succeed in claim_tests:
        try:
            claim = contract.make_claim(mode, predicate)
            succeeded = True
        except OntologicalViolation:
            succeeded = False

        passed = succeeded == should_succeed
        results['claim_checks'].append({
            'predicate': predicate,
            'mode': mode.name,
            'should_succeed': should_succeed,
            'succeeded': succeeded,
            'passed': passed,
        })
        if not passed:
            results['all_passed'] = False
    
    # ---- 5. Verify constraint manifold alignment (if available) ----
    if CONSTRAINT_MANIFOLD_AVAILABLE and ConstraintVector is not None:
        # Check that each mode produces valid ConstraintVector
        for mode in ExistenceMode:
            try:
                vec = mode.to_constraint_vector()
                if vec is None:
                    results['constraint_alignment_checks'].append({
                        'mode': mode.name,
                        'check': 'ConstraintVector generation',
                        'passed': False,
                        'error': 'Returned None'
                    })
                    results['all_passed'] = False
                else:
                    # Verify X > 0 (admissibility)
                    admissible = vec.X > 0
                    results['constraint_alignment_checks'].append({
                        'mode': mode.name,
                        'check': 'Admissibility (X > 0)',
                        'X_value': vec.X,
                        'passed': admissible,
                    })
                    if not admissible:
                        results['all_passed'] = False
                    
                    # Verify hierarchical activation
                    active = mode.active_constraints()
                    expected_count = mode.value
                    actual_count = len(active)
                    count_match = expected_count == actual_count
                    results['constraint_alignment_checks'].append({
                        'mode': mode.name,
                        'check': 'Constraint count',
                        'expected': expected_count,
                        'actual': actual_count,
                        'active_constraints': active,
                        'passed': count_match,
                    })
                    if not count_match:
                        results['all_passed'] = False
            except Exception as e:
                results['constraint_alignment_checks'].append({
                    'mode': mode.name,
                    'check': 'ConstraintVector generation',
                    'passed': False,
                    'error': str(e)
                })
                results['all_passed'] = False
        
        # Check I-State to constraint axis mapping
        for predicate in ExistencePredicate.ALL:
            axis = ExistencePredicate.constraint_axis(predicate)
            expected_axes = {'X', 'T', 'N', 'B', 'A'}
            valid_axis = axis in expected_axes
            results['constraint_alignment_checks'].append({
                'predicate': predicate,
                'check': 'Maps to valid constraint axis',
                'constraint_axis': axis,
                'passed': valid_axis,
            })
            if not valid_axis:
                results['all_passed'] = False

    return results


# ============================================================================
# MAIN — VERIFY ON EXECUTION
# ============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("FOUNDATIONAL CONTRACT — LAYER 0")
    print("The Grammar of Existence (Aligned with Constraint Manifold)")
    print("Authors: Sunni (Sir) Morningstar and Cael Devo")
    print("=" * 70)
    print()
    
    if CONSTRAINT_MANIFOLD_AVAILABLE:
        print("✓ Constraint Manifold (Layer -1) is available")
    else:
        print("⚠ Constraint Manifold (Layer -1) not available (running standalone)")
    print()

    results = verify_foundational_contract()

    # Report axiom checks
    print("DEPENDENCY AXIOM CHECKS:")
    for check in results['axiom_checks']:
        status = "✓" if check['passed'] else "✗"
        print(f"  {status} {check['mode']}")
    print()

    # Report predicate checks
    print("PREDICATE-MODE CONSISTENCY:")
    for check in results['predicate_checks']:
        status = "✓" if check['passed'] else "✗"
        if 'assertable_at_required' in check:
            print(f"  {status} {check['predicate']} assertable at {check['required_mode']}")
        else:
            print(f"  {status} {check['predicate']} forbidden below {check.get('below_mode', '?')}")
    print()

    # Report classification checks
    print("CLASSIFICATION CHECKS:")
    for check in results['classification_checks']:
        status = "✓" if check['passed'] else "✗"
        print(f"  {status} {check['evidence']} → {check['actual']}")
    print()

    # Report claim checks
    print("CLAIM FORMATION CHECKS:")
    for check in results['claim_checks']:
        status = "✓" if check['passed'] else "✗"
        outcome = "accepted" if check['succeeded'] else "rejected"
        print(f"  {status} {check['predicate']} at {check['mode']} → {outcome}")
    print()
    
    # Report constraint alignment checks
    if results['constraint_alignment_checks']:
        print("CONSTRAINT MANIFOLD ALIGNMENT:")
        for check in results['constraint_alignment_checks']:
            status = "✓" if check['passed'] else "✗"
            if 'mode' in check:
                print(f"  {status} {check['mode']}: {check['check']}")
            elif 'predicate' in check:
                print(f"  {status} {check['predicate']}: {check['check']} → {check.get('constraint_axis', 'N/A')}")
        print()

    # Summary
    total = (len(results['axiom_checks']) + len(results['predicate_checks'])
             + len(results['classification_checks']) + len(results['claim_checks'])
             + len(results['constraint_alignment_checks']))
    passed = sum(1 for checks in [results['axiom_checks'], results['predicate_checks'],
                                   results['classification_checks'], results['claim_checks'],
                                   results['constraint_alignment_checks']]
                 for c in checks if c['passed'])

    if results['all_passed']:
        print(f"ALL {total} CHECKS PASSED ✓")
        print()
        print("The grammar of existence is sound and aligned with the constraint manifold.")
        print("Everything above this layer inherits a lawful universe.")
    else:
        print(f"FAILURES DETECTED: {total - passed}/{total} checks failed")
        print()
        print("The foundational contract has structural defects.")
        print("Nothing should be built on top of this until resolved.")

    # Print mode descriptions with constraint alignment
    print()
    print("=" * 70)
    print("EXISTENCE MODE REFERENCE (WITH CONSTRAINT ALIGNMENT)")
    print("=" * 70)
    contract = FoundationalContract()
    for mode in ExistenceMode:
        desc = contract.describe_mode(mode)
        print(f"\n  {mode.name} (level {mode.value}):")
        print(f"    Exists: {desc['exists']}")
        print(f"    Has temporality: {desc['has_temporality']}")
        print(f"    Persists: {desc['persists']}")
        print(f"    Has boundary: {desc['has_boundary']}")
        print(f"    Has agency: {desc['has_agency']}")
        print(f"    Constraint signature: {desc['constraint_signature']}")
        print(f"    Active constraints: {desc['constraint_count']} of 5")
        print(f"    Permitted axes: {desc['permitted_axes']}")
        
        if CONSTRAINT_MANIFOLD_AVAILABLE:
            vec = mode.to_constraint_vector()
            if vec:
                print(f"    ConstraintVector: {vec}")

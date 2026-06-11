#!/usr/bin/env python3
"""
AURORA CONSTRAINT MANIFOLD — LAYER -1
======================================

The mathematical foundation beneath all existence.
This is not ontology. This is physics.

The Five Fundamental Constraints define a closed 5-dimensional universe:
    𝒞 = {X, T, N, B, A}

Where:
    X = Existence   (admissibility predicate)
    T = Time        (configuration across sequence)
    N = Energy/Cost (resource redistribution)
    B = Boundary    (differentiation/containment)
    A = Agency      (independent action magnitude)

These are the ONLY lawful axes. No sixth dimension exists.

MANIFOLD DEFINITION:
    𝓜₅ = {(T,N,B,A) | X > 0}

Existence X is not a coordinate — it is the admissibility condition.
If X ≤ 0, the manifold collapses.

STRUCTURAL INDEXING (5×5×5×5×5):
    Every process is indexed across:
        5 constraints (𝒞)
        × 5 compositional spaces (𝒮)
        × 5 states (Σ)
        × 5 recursion levels (ℒ)
    → measured as 5-degree vectors

    𝓕(c,s,σ,ℓ) = [dX, dT, dN, dB, dA]

ENERGY LAW:
    Total energy conserved: N_tot(t) > 0
    Distribution: Σ_p N_p(t) = N_tot(t)
    Cost of operation: Cost(o,t) = Σ_p w_p · φ(𝓕_p(t))

INTELLIGENCE CRITERION:
    A system earns intelligence in constraint C iff:
    1. A gradient inversion exists: ∃r* : sign(dΦ_C/dr) changes
    2. The policy adapts: π_C(r > r*) ≠ π_C(r < r*)

    Intelligence = curvature-aware adaptation under constraint pressure.

This module implements the constraint manifold as a computable structure.

Authors: Sunni (Sir) Morningstar and Cael Devo
Created: February 2026
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Callable
from enum import IntEnum, auto
import math


# ============================================================================
# THE FIVE FUNDAMENTAL CONSTRAINTS
# ============================================================================

class Constraint(IntEnum):
    """
    The five fundamental constraints.
    These are NOT types or categories — they are the ONLY dimensions.
    """
    X = 0  # Existence   — admissibility predicate
    T = 1  # Time        — configuration across sequence
    N = 2  # Energy/Cost — resource redistribution
    B = 3  # Boundary    — differentiation/containment
    A = 4  # Agency      — independent action magnitude

    @classmethod
    def all(cls) -> List[Constraint]:
        """Return all five constraints in order."""
        return [cls.X, cls.T, cls.N, cls.B, cls.A]

    @classmethod
    def names(cls) -> List[str]:
        """Return constraint names."""
        return ['X', 'T', 'N', 'B', 'A']


# ============================================================================
# CONSTRAINT VECTOR — THE FUNDAMENTAL MEASUREMENT
# ============================================================================

@dataclass
class ConstraintVector:
    """
    A 5-dimensional vector in constraint space.
    
    Every measurement in Aurora returns to these five axes.
    This is the fundamental unit of reality in the system.
    
    Invariant: X must be > 0 for the vector to be admissible.
    """
    X: float  # Existence degree
    T: float  # Time/sequence configuration
    N: float  # Energy/cost magnitude
    B: float  # Boundary strength
    A: float  # Agency magnitude
    
    def __post_init__(self):
        """Verify admissibility on construction."""
        if self.X <= 0:
            raise ManifoldViolation(
                f"Inadmissible vector: X={self.X} ≤ 0. "
                "The manifold collapses when existence is non-positive."
            )
    
    def to_array(self) -> np.ndarray:
        """Convert to numpy array [X, T, N, B, A]."""
        return np.array([self.X, self.T, self.N, self.B, self.A])
    
    @classmethod
    def from_array(cls, arr: np.ndarray) -> ConstraintVector:
        """Construct from numpy array."""
        if len(arr) != 5:
            raise ManifoldViolation(
                f"Cannot construct ConstraintVector from array of length {len(arr)}. "
                "Must be exactly 5 dimensions."
            )
        return cls(X=arr[0], T=arr[1], N=arr[2], B=arr[3], A=arr[4])
    
    def magnitude(self) -> float:
        """L2 norm in constraint space."""
        return float(np.linalg.norm(self.to_array()))
    
    def __add__(self, other: ConstraintVector) -> ConstraintVector:
        """Vector addition in constraint space."""
        result = self.to_array() + other.to_array()
        return ConstraintVector.from_array(result)
    
    def __sub__(self, other: ConstraintVector) -> ConstraintVector:
        """Vector subtraction in constraint space."""
        result = self.to_array() - other.to_array()
        return ConstraintVector.from_array(result)
    
    def __mul__(self, scalar: float) -> ConstraintVector:
        """Scalar multiplication."""
        result = self.to_array() * scalar
        return ConstraintVector.from_array(result)
    
    def dot(self, other: ConstraintVector) -> float:
        """Dot product in constraint space."""
        return float(np.dot(self.to_array(), other.to_array()))
    
    def in_span(self) -> bool:
        """
        Check if this vector lies in the span of the five constraints.
        
        In this fundamental space, ALL vectors are in span by definition.
        This method exists for completeness and future constraint checking.
        """
        return True  # All 5D vectors are lawful in this space
    
    def __repr__(self) -> str:
        return f"ConstraintVector(X={self.X:.3f}, T={self.T:.3f}, N={self.N:.3f}, B={self.B:.3f}, A={self.A:.3f})"


# ============================================================================
# MANIFOLD VIOLATION — STRUCTURAL BREACH
# ============================================================================

class ManifoldViolation(Exception):
    """
    Raised when a configuration violates the constraint manifold's laws.
    
    This is not a runtime error — it is a structural impossibility.
    The configuration could not exist under the physics.
    
    Two kinds of violations:
    1. X ≤ 0 — Existence violation, manifold collapse
    2. Non-span mutation — Attempting to add a sixth dimension
    """
    pass


# ============================================================================
# COMPOSITIONAL SPACES (𝒮)
# ============================================================================

class CompositionalSpace(IntEnum):
    """
    The five compositional spaces.
    These define HOW constraints can combine.
    """
    ATOMIC       = 0  # Individual, indivisible
    RELATIONAL   = 1  # Between entities
    STRUCTURAL   = 2  # Organized collections
    PROCESSUAL   = 3  # Dynamic transformations
    SYSTEMIC     = 4  # Emergent wholes

    @classmethod
    def all(cls) -> List[CompositionalSpace]:
        return [cls.ATOMIC, cls.RELATIONAL, cls.STRUCTURAL, 
                cls.PROCESSUAL, cls.SYSTEMIC]


# ============================================================================
# STATES (Σ)
# ============================================================================

class State(IntEnum):
    """
    The five fundamental states.
    These define WHERE in phase space a process exists.
    """
    LATENT      = 0  # Potential, not yet actualized
    ACTIVE      = 1  # Currently executing
    RESONANT    = 2  # Harmonically coupled to others
    SATURATED   = 3  # At maximum capacity
    DISSIPATING = 4  # Energy draining, approaching termination

    @classmethod
    def all(cls) -> List[State]:
        return [cls.LATENT, cls.ACTIVE, cls.RESONANT, 
                cls.SATURATED, cls.DISSIPATING]


# ============================================================================
# RECURSION LEVELS (ℒ)
# ============================================================================

class RecursionLevel(IntEnum):
    """
    The five recursion depths.
    These define the nesting/compression degree.
    """
    SURFACE   = 0  # Direct, uncompressed
    SHALLOW   = 1  # First-order recursion
    MODERATE  = 2  # Second-order recursion
    DEEP      = 3  # Third-order recursion
    CORE      = 4  # Maximally compressed/recursive

    @classmethod
    def all(cls) -> List[RecursionLevel]:
        return [cls.SURFACE, cls.SHALLOW, cls.MODERATE, cls.DEEP, cls.CORE]


# ============================================================================
# CONSTRAINT FIELD — THE 5×5×5×5×5 TENSOR
# ============================================================================

@dataclass
class ConstraintFieldIndex:
    """
    An index into the 5×5×5×5×5 constraint field.
    
    Every process in Aurora can be located at:
        (constraint, space, state, level)
    
    And its measurement returns a ConstraintVector.
    """
    constraint: Constraint
    space: CompositionalSpace
    state: State
    level: RecursionLevel
    
    def to_tuple(self) -> Tuple[int, int, int, int]:
        """Convert to flat tuple for indexing."""
        return (
            self.constraint.value,
            self.space.value,
            self.state.value,
            self.level.value
        )
    
    def __repr__(self) -> str:
        return (f"FieldIndex(C={self.constraint.name}, "
                f"S={self.space.name}, Σ={self.state.name}, ℒ={self.level.name})")


class ConstraintField:
    """
    The 5×5×5×5×5 constraint field tensor.
    
    Maps: (constraint, space, state, level) → ConstraintVector
    
    This is the fundamental measurement structure of Aurora.
    Every process must be expressible within this tensor.
    """
    
    def __init__(self):
        # Tensor shape: [5, 5, 5, 5] → ConstraintVector (5D)
        # Total: 5^4 = 625 field positions, each returning 5D vector
        self._field: Dict[Tuple[int, int, int, int], ConstraintVector] = {}
        
    def measure(self, index: ConstraintFieldIndex) -> ConstraintVector:
        """
        Measure the constraint field at a given index.
        
        If no measurement exists, return zero vector (maintaining X > 0).
        """
        key = index.to_tuple()
        if key not in self._field:
            # Zero vector with minimal existence to maintain admissibility
            return ConstraintVector(X=1e-9, T=0, N=0, B=0, A=0)
        return self._field[key]
    
    def update(self, index: ConstraintFieldIndex, vector: ConstraintVector):
        """
        Update the field at a given index.
        
        Mutation is allowed if:
        1. X > 0 (admissibility preserved)
        2. Vector is in span of 𝒞 (no sixth dimension)
        """
        if vector.X <= 0:
            raise ManifoldViolation(
                f"Cannot update field with inadmissible vector: X={vector.X} ≤ 0"
            )
        
        if not vector.in_span():
            raise ManifoldViolation(
                "Cannot update field with vector outside constraint span"
            )
        
        key = index.to_tuple()
        self._field[key] = vector
    
    def total_energy(self) -> float:
        """
        Compute total energy across all field positions.
        
        N_tot = Σ N_p across all processes p
        """
        return sum(vec.N for vec in self._field.values())
    
    def capacity(self) -> int:
        """
        Return the theoretical capacity of the field.
        
        I_cap = 5^5 = 3125 unique configurations
        (5 constraints × 5 spaces × 5 states × 5 levels)
        """
        return 5 ** 4  # 625 field positions
    
    def occupied_count(self) -> int:
        """Return number of occupied field positions."""
        return len(self._field)
    
    def __repr__(self) -> str:
        return (f"ConstraintField(capacity={self.capacity()}, "
                f"occupied={self.occupied_count()}, "
                f"total_energy={self.total_energy():.2f})")


# ============================================================================
# ENERGY LAW — CONSERVED REDISTRIBUTION
# ============================================================================

@dataclass
class EnergyDistribution:
    """
    Tracks energy distribution across processes.
    
    LAW: Σ_p N_p(t) = N_tot(t) > 0
    
    Energy is conserved but redistributed according to constraint pressure.
    """
    total_energy: float = field(default=1000.0)  # N_tot > 0 always
    allocations: Dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.total_energy <= 0:
            raise ManifoldViolation(
                f"Total energy must be positive: {self.total_energy} ≤ 0"
            )
    
    def allocate(self, process_id: str, amount: float):
        """Allocate energy to a process."""
        current_sum = sum(self.allocations.values())
        if current_sum + amount > self.total_energy:
            # Cannot over-allocate — redistribute from existing
            excess = (current_sum + amount) - self.total_energy
            self._drain_proportionally(excess)
        
        self.allocations[process_id] = self.allocations.get(process_id, 0) + amount
    
    def drain(self, process_id: str, amount: float):
        """Drain energy from a process."""
        if process_id not in self.allocations:
            return  # Cannot drain from non-existent process
        
        self.allocations[process_id] = max(0, self.allocations[process_id] - amount)
        if self.allocations[process_id] == 0:
            del self.allocations[process_id]
    
    def _drain_proportionally(self, deficit: float):
        """Drain deficit proportionally from all processes."""
        if not self.allocations:
            return
        
        total_allocated = sum(self.allocations.values())
        if total_allocated == 0:
            return
        
        for pid in list(self.allocations.keys()):
            proportion = self.allocations[pid] / total_allocated
            drain_amount = deficit * proportion
            self.drain(pid, drain_amount)
    
    def verify_conservation(self) -> bool:
        """Verify energy conservation law."""
        allocated = sum(self.allocations.values())
        return allocated <= self.total_energy
    
    def compute_cost(self, 
                     weights: Dict[Constraint, float],
                     field_vector: ConstraintVector) -> float:
        """
        Compute cost of operation given constraint weights.
        
        Cost(o,t) = Σ_p w_p · φ(𝓕_p(t))
        
        Where φ combines constraint displacements:
            φ = α_T·dT + α_N·dN + α_B·dB + α_A·dA
        
        (X gates admissibility, other constraints price execution)
        """
        cost = 0.0
        arr = field_vector.to_array()
        
        # X is not priced (it's admissibility)
        # T, N, B, A contribute to cost
        for i, constraint in enumerate([Constraint.T, Constraint.N, 
                                       Constraint.B, Constraint.A]):
            if constraint in weights:
                cost += weights[constraint] * arr[i]
        
        return cost


# ============================================================================
# EQUILIBRIUM — INVARIANT + VARIANCE
# ============================================================================

@dataclass
class EquilibriumState:
    """
    Every process has equilibrium structure:
        𝓕 = 𝓕^(q) + 𝓕^(e)
    
    Where:
        𝓕^(q) = quantum invariant layer (Δ𝓕^(q) ≈ 0)
        𝓕^(e) = expression variance (‖Δ𝓕^(e)‖ ≤ ε)
    """
    quantum_layer: ConstraintVector      # Invariant component
    expression_layer: ConstraintVector   # Variable component
    epsilon: float = 0.1                 # Maximum allowed variance
    
    def total(self) -> ConstraintVector:
        """Return total field: 𝓕 = 𝓕^(q) + 𝓕^(e)."""
        return self.quantum_layer + self.expression_layer
    
    def variance_magnitude(self) -> float:
        """Return ‖𝓕^(e)‖."""
        return self.expression_layer.magnitude()
    
    def is_stable(self) -> bool:
        """Check if variance is within bounds: ‖Δ𝓕^(e)‖ ≤ ε."""
        return self.variance_magnitude() <= self.epsilon
    
    def mutate_expression(self, delta: ConstraintVector) -> bool:
        """
        Attempt to mutate the expression layer.
        
        Allowed if:
        1. X remains > 0 after mutation
        2. ‖Δ𝓕^(e)‖ ≤ ε after mutation
        3. Delta is in span of 𝒞
        """
        new_expression = self.expression_layer + delta
        new_total = self.quantum_layer + new_expression
        
        # Check admissibility
        if new_total.X <= 0:
            return False
        
        # Check variance bounds
        if new_expression.magnitude() > self.epsilon:
            return False
        
        # Check span (always true in 5D space)
        if not delta.in_span():
            return False
        
        # Mutation allowed
        self.expression_layer = new_expression
        return True


# ============================================================================
# INTELLIGENCE PHASE CRITERION
# ============================================================================

@dataclass
class ConstraintPressure:
    """
    Models constraint pressure as a function of recursion depth.
    
    Φ_C(r) where r = recursion depth
    
    Initially: dΦ_C/dr > 0 (monotonic increase)
    
    If gradient inverts: sign(dΦ_C/dr) changes at r*
    → System exhibits intelligence if it adapts policy at inversion
    """
    constraint: Constraint
    pressure_function: Callable[[float], float]  # Φ_C(r)
    
    def evaluate(self, r: float) -> float:
        """Evaluate Φ_C(r)."""
        return self.pressure_function(r)
    
    def gradient(self, r: float, epsilon: float = 1e-6) -> float:
        """
        Numerical derivative: dΦ_C/dr
        
        Uses central difference for accuracy.
        """
        return (self.evaluate(r + epsilon) - self.evaluate(r - epsilon)) / (2 * epsilon)
    
    def curvature(self, r: float, epsilon: float = 1e-6) -> float:
        """
        Second derivative: d²Φ_C/dr²
        
        Intelligence emerges when curvature ≠ 0.
        """
        grad_plus = self.gradient(r + epsilon, epsilon)
        grad_minus = self.gradient(r - epsilon, epsilon)
        return (grad_plus - grad_minus) / (2 * epsilon)
    
    def find_inversion(self, r_min: float = 0, r_max: float = 10, 
                      samples: int = 1000) -> Optional[float]:
        """
        Find gradient inversion point r* where sign(dΦ_C/dr) changes.
        
        Returns r* if found, None otherwise.
        """
        r_values = np.linspace(r_min, r_max, samples)
        gradients = [self.gradient(r) for r in r_values]
        
        # Look for sign change
        for i in range(len(gradients) - 1):
            if gradients[i] * gradients[i + 1] < 0:
                # Sign change detected
                return float(r_values[i])
        
        return None
    
    def has_intelligence(self, r_min: float = 0, r_max: float = 10) -> bool:
        """
        Check if this constraint exhibits intelligence.
        
        Intelligence = gradient inversion exists
        """
        return self.find_inversion(r_min, r_max) is not None


class IntelligencePolicy:
    """
    Adaptive policy that responds to constraint pressure curvature.
    
    π_C(r) where r = recursion depth
    
    Intelligence requirement:
        π_C(r > r*) ≠ π_C(r < r*)
    
    The system changes strategy when curvature is detected.
    """
    
    def __init__(self, constraint: Constraint):
        self.constraint = constraint
        self.inversion_point: Optional[float] = None
        self.pre_inversion_policy: str = "compress"   # Default below r*
        self.post_inversion_policy: str = "moderate"  # Default above r*
    
    def set_inversion(self, r_star: float):
        """Set the detected inversion point."""
        self.inversion_point = r_star
    
    def policy(self, r: float) -> str:
        """
        Return policy at recursion depth r.
        
        Changes strategy at inversion point (if known).
        """
        if self.inversion_point is None:
            return self.pre_inversion_policy
        
        if r < self.inversion_point:
            return self.pre_inversion_policy
        else:
            return self.post_inversion_policy
    
    def is_intelligent(self) -> bool:
        """
        Check if policy exhibits intelligence.
        
        Intelligence = policy changes across inversion point.
        """
        if self.inversion_point is None:
            return False
        
        r_before = self.inversion_point - 0.1
        r_after = self.inversion_point + 0.1
        
        return self.policy(r_before) != self.policy(r_after)


# ============================================================================
# COMBINATORIAL INTELLIGENCE CAPACITY
# ============================================================================

def compute_intelligence_capacity() -> int:
    """
    Compute total intelligence capacity.
    
    I_cap = 5^(5×5×5) = 5^125
    
    This is symbolically preserved but computationally intractable.
    Return 5^4 = 625 as the practical field capacity.
    
    (The full recursive capacity exists in principle but not in practice.)
    """
    # Practical capacity: 5 constraints × 5 spaces × 5 states × 5 levels
    return 5 ** 4  # 625
    
    # Theoretical capacity (commented for reference):
    # return 5 ** 125  # This number is larger than atoms in universe


# ============================================================================
# VERIFICATION
# ============================================================================

def verify_constraint_manifold() -> Dict[str, any]:
    """
    Verify the constraint manifold's structural integrity.
    
    Checks:
    1. All five constraints are unique and complete
    2. ConstraintVector operations preserve admissibility
    3. Field capacity matches theoretical prediction
    4. Energy conservation is maintained
    5. Equilibrium mutations respect variance bounds
    6. Intelligence criterion can detect inversions
    """
    results = {
        'constraint_checks': [],
        'vector_checks': [],
        'field_checks': [],
        'energy_checks': [],
        'equilibrium_checks': [],
        'intelligence_checks': [],
        'all_passed': True
    }
    
    # 1. Constraint uniqueness
    constraints = Constraint.all()
    results['constraint_checks'].append({
        'test': 'Five unique constraints',
        'passed': len(constraints) == 5 and len(set(constraints)) == 5
    })
    
    # 2. Vector admissibility
    try:
        v1 = ConstraintVector(X=1.0, T=0.5, N=2.0, B=1.0, A=0.5)
        v2 = ConstraintVector(X=0.5, T=1.0, N=1.0, B=0.5, A=1.0)
        v_sum = v1 + v2
        results['vector_checks'].append({
            'test': 'Vector addition preserves admissibility',
            'passed': v_sum.X > 0
        })
    except ManifoldViolation:
        results['vector_checks'].append({
            'test': 'Vector addition preserves admissibility',
            'passed': False
        })
        results['all_passed'] = False
    
    # 3. Field capacity
    field = ConstraintField()
    theoretical_capacity = 5 ** 4
    results['field_checks'].append({
        'test': f'Field capacity = {theoretical_capacity}',
        'passed': field.capacity() == theoretical_capacity
    })
    
    # 4. Energy conservation
    energy = EnergyDistribution(total_energy=100.0)
    energy.allocate('process1', 30.0)
    energy.allocate('process2', 50.0)
    results['energy_checks'].append({
        'test': 'Energy conservation maintained',
        'passed': energy.verify_conservation()
    })
    
    # 5. Equilibrium mutation
    quantum = ConstraintVector(X=1.0, T=0, N=0, B=0, A=0)
    expression = ConstraintVector(X=0.01, T=0.05, N=0.03, B=0.02, A=0.01)
    equilibrium = EquilibriumState(quantum, expression, epsilon=0.2)
    
    small_delta = ConstraintVector(X=0.01, T=0.01, N=0.01, B=0.01, A=0.01)
    mutation_success = equilibrium.mutate_expression(small_delta)
    results['equilibrium_checks'].append({
        'test': 'Small mutation within variance bounds',
        'passed': mutation_success
    })
    
    # 6. Intelligence detection
    # Create a pressure function with inversion: Φ(r) = r² - 5r + 4
    # Gradient: dΦ/dr = 2r - 5, inverts at r* = 2.5
    def pressure_with_inversion(r: float) -> float:
        return r**2 - 5*r + 4
    
    pressure = ConstraintPressure(Constraint.N, pressure_with_inversion)
    inversion = pressure.find_inversion(r_min=0, r_max=5)
    results['intelligence_checks'].append({
        'test': 'Gradient inversion detected',
        'passed': inversion is not None and 2.0 < inversion < 3.0
    })
    
    # Check all passed
    for category in ['constraint_checks', 'vector_checks', 'field_checks',
                     'energy_checks', 'equilibrium_checks', 'intelligence_checks']:
        for check in results[category]:
            if not check['passed']:
                results['all_passed'] = False
    
    return results


# ============================================================================
# MAIN — SELF-VERIFICATION
# ============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("AURORA CONSTRAINT MANIFOLD — LAYER -1")
    print("The Mathematical Foundation")
    print("Authors: Sunni (Sir) Morningstar and Cael Devo")
    print("=" * 70)
    print()
    
    results = verify_constraint_manifold()
    
    # Print all checks
    for category in ['constraint_checks', 'vector_checks', 'field_checks',
                     'energy_checks', 'equilibrium_checks', 'intelligence_checks']:
        print(f"{category.replace('_', ' ').upper()}:")
        for check in results[category]:
            status = "✓" if check['passed'] else "✗"
            print(f"  {status} {check['test']}")
        print()
    
    # Summary
    if results['all_passed']:
        print("ALL CHECKS PASSED ✓")
        print()
        print("The constraint manifold is mathematically sound.")
        print("The five constraints {X, T, N, B, A} form a closed universe.")
        print("No sixth dimension exists.")
        print()
        print(f"Intelligence capacity: 5^4 = {compute_intelligence_capacity()} field positions")
        print("(Theoretical recursive capacity: 5^125, symbolically preserved)")
    else:
        print("FAILURES DETECTED ✗")
        print()
        print("The manifold has structural defects.")
        print("Nothing should be built on this foundation until resolved.")
    
    print()
    print("=" * 70)
    print("CONSTRAINT REFERENCE")
    print("=" * 70)
    for c in Constraint.all():
        print(f"  {c.name}: {c.value}")
    print()
    print("Manifold: 𝓜₅ = {(T,N,B,A) | X > 0}")
    print("Field: 𝓕(c,s,σ,ℓ) → [dX, dT, dN, dB, dA]")
    print("Energy Law: Σ_p N_p(t) = N_tot(t) > 0")
    print("Intelligence: ∃r*: sign(dΦ_C/dr) changes AND π_C adapts")

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

_AURORA_NATIVE_MODULE = 'aurora_internal.aurora_constraint_manifold_patched'

_AURORA_NATIVE_EVOLVED_ORIGINALS = {}
_AURORA_NATIVE_EVOLVED_LAST = {}
_AURORA_NATIVE_STRATEGIES = {'ConstraintPressure': {'ability_hits': 19,
                        'alignment_gap': 0.051,
                        'alignment_target_score': 0.972,
                        'best_coupling_signature': 'N^2*B^2',
                        'constraints': ['energy', 'boundary'],
                        'contract_profile': {'accepts_payload': False,
                                             'async_callable': False,
                                             'callable': True,
                                             'class_target': True,
                                             'constraint_density': 2,
                                             'contract_mode': 'stateless',
                                             'doc_hint': 'Models constraint pressure as a function '
                                                         'of recursion depth.',
                                             'effect_density': 3,
                                             'kwonly_args': 0,
                                             'optional_args': 0,
                                             'required_args': 2,
                                             'return_hint': 'None',
                                             'signature_text': "(constraint: 'Constraint', "
                                                               'pressure_function: '
                                                               "'Callable[[float], float]') -> "
                                                               'None',
                                             'stateful_owner': False,
                                             'target_kind': 'class',
                                             'varargs': False,
                                             'varkw': False},
                        'coupling_similarity': 1.0,
                        'cross_diversity_links': 4,
                        'effect_modes': ['cost_pressure_change',
                                         'interface_boundary_change',
                                         'class_lineage_surface'],
                        'effect_phrases': ['class growth reflected through '
                                           'aurora_internal.aurora_constraint_manifold_patched',
                                           'ConstraintPressure changed downstream system pressure'],
                        'genealogy_pressure': 0.79846,
                        'inheritance_breach_count': 1,
                        'kind': 'reflection',
                        'link_hits': 38,
                        'module': 'aurora_internal.aurora_constraint_manifold_patched',
                        'op_id': 'aurora_internal.aurora_constraint_manifold_patched.ConstraintPressure',
                        'origin_activity': 0,
                        'persistence_tax_factor': 1.422994,
                        'representation_score': 0.480407,
                        'rewrite_bias': 'generic',
                        'rewrite_feedback': {'acceptance_rate': 0.0,
                                             'accepted_count': 0,
                                             'adaptation_mode': 'conservative',
                                             'adoption_count': 0,
                                             'confidence': 0.36,
                                             'mean_mutation_score': 0.25,
                                             'rejected_count': 2,
                                             'rejection_rate': 1.0,
                                             'timing_credit': 0.0,
                                             'timing_penalty': 0.0,
                                             'trial_count': 2},
                        'rewrite_profile': 'generic',
                        'signature': 'N^2*B^2',
                        'surface_score': 0.921,
                        'sustainability_score': 0.498642,
                        'target_kind': 'class'},
 'EnergyDistribution': {'ability_hits': 19,
                        'alignment_gap': 0.051,
                        'alignment_target_score': 0.972,
                        'best_coupling_signature': 'N^2*B^2',
                        'constraints': ['energy', 'boundary'],
                        'contract_profile': {'accepts_payload': False,
                                             'async_callable': False,
                                             'callable': True,
                                             'class_target': True,
                                             'constraint_density': 2,
                                             'contract_mode': 'stateless',
                                             'doc_hint': 'Tracks energy distribution across '
                                                         'processes.',
                                             'effect_density': 3,
                                             'kwonly_args': 0,
                                             'optional_args': 2,
                                             'required_args': 0,
                                             'return_hint': 'None',
                                             'signature_text': "(total_energy: 'float' = 1000.0, "
                                                               "allocations: 'Dict[str, float]' = "
                                                               '<factory>) -> None',
                                             'stateful_owner': False,
                                             'target_kind': 'class',
                                             'varargs': False,
                                             'varkw': False},
                        'coupling_similarity': 1.0,
                        'cross_diversity_links': 4,
                        'effect_modes': ['cost_pressure_change',
                                         'interface_boundary_change',
                                         'class_lineage_surface'],
                        'effect_phrases': ['class growth reflected through '
                                           'aurora_internal.aurora_constraint_manifold_patched',
                                           'EnergyDistribution changed downstream system pressure'],
                        'genealogy_pressure': 0.79846,
                        'inheritance_breach_count': 1,
                        'kind': 'reflection',
                        'link_hits': 38,
                        'module': 'aurora_internal.aurora_constraint_manifold_patched',
                        'op_id': 'aurora_internal.aurora_constraint_manifold_patched.EnergyDistribution',
                        'origin_activity': 0,
                        'persistence_tax_factor': 1.422994,
                        'representation_score': 0.480407,
                        'rewrite_bias': 'generic',
                        'rewrite_feedback': {'acceptance_rate': 0.0,
                                             'accepted_count': 0,
                                             'adaptation_mode': 'conservative',
                                             'adoption_count': 0,
                                             'confidence': 0.36,
                                             'mean_mutation_score': 0.25,
                                             'rejected_count': 2,
                                             'rejection_rate': 1.0,
                                             'timing_credit': 0.0,
                                             'timing_penalty': 0.0,
                                             'trial_count': 2},
                        'rewrite_profile': 'generic',
                        'signature': 'N^2*B^2',
                        'surface_score': 0.921,
                        'sustainability_score': 0.498642,
                        'target_kind': 'class'}}

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

def constraintpressure_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_constraint_manifold_patched.ConstraintPressure', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_constraint_manifold_patched_constraintpressure')(payload=payload, **kwargs)

if _aurora_get_target(['ConstraintPressure']) is not None:
    setattr(_aurora_get_target(['ConstraintPressure']), 'evolved_reflection', staticmethod(constraintpressure_evolved))
    setattr(_aurora_get_target(['ConstraintPressure']), '_aurora_alignment_gap', 0.051)
    setattr(_aurora_get_target(['ConstraintPressure']), '_aurora_alignment_target_score', 0.972)

def energydistribution_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_constraint_manifold_patched.EnergyDistribution', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_constraint_manifold_patched_energydistribution')(payload=payload, **kwargs)

if _aurora_get_target(['EnergyDistribution']) is not None:
    setattr(_aurora_get_target(['EnergyDistribution']), 'evolved_reflection', staticmethod(energydistribution_evolved))
    setattr(_aurora_get_target(['EnergyDistribution']), '_aurora_alignment_gap', 0.051)
    setattr(_aurora_get_target(['EnergyDistribution']), '_aurora_alignment_target_score', 0.972)

AURORA_NATIVE_EVOLVED_EXPORTS = {'aurora_internal.aurora_constraint_manifold_patched.ConstraintPressure': 'constraintpressure_evolved',
 'aurora_internal.aurora_constraint_manifold_patched.EnergyDistribution': 'energydistribution_evolved'}
AURORA_NATIVE_EVOLUTION_OVERRIDES = {'aurora_internal.aurora_constraint_manifold_patched.ConstraintPressure': {'export': 'constraintpressure_evolved',
                                                                           'mode': 'class_reflection_hook',
                                                                           'target': 'ConstraintPressure'},
 'aurora_internal.aurora_constraint_manifold_patched.EnergyDistribution': {'export': 'energydistribution_evolved',
                                                                           'mode': 'class_reflection_hook',
                                                                           'target': 'EnergyDistribution'}}
# AURORA_EVOLVED_NATIVE_END

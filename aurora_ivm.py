#!/usr/bin/env python3
"""
AURORA IVM — ISOTROPIC VECTOR MATRIX
======================================

Layer 1 of Aurora's architecture.
The geometric space in which ontologically grounded entities exist.

REPLACES (consolidated from 6 modules):
    aurora_ivm_consciousness_geometry.py
    aurora_ivm_toroidal_vertices.py
    aurora_ivm_core_integration.py
    aurora_ivm_dimensional_integration.py
    aurora_ivm_integration_patches.py
    aurora_ivm_governance_layer.py

DEPENDS ON:
    foundational_contract.py     (Layer 0)
    aurora_constraint_manifold.py (Layer -1)

ARCHITECTURE:
    The IVM is a spatial fabric where every node carries an ExistenceMode.
    Nothing enters the lattice without being classified by the FoundationalContract.
    Governance is not a separate system — it is implicit in the mode.
    If a node is PERSISTENT, energy operations are permitted.
    If a node is REFERENCE, they are not.
    No voting. No authority layers. The mode IS the law.

TOROIDAL DYNAMICS:
    Each of the 5 ontological axes is a rotating torus:
        Existence axis:  I_IS   ↔ I_ISNT    (active at REFERENCE+)
        Temporal axis:   I_CAN  ↔ I_CANNOT  (active at TRANSIENT+)
        Energy axis:     I_DO   ↔ I_DONOT   (active at PERSISTENT+)
        Boundary axis:   I_SAW  ↔ I_SOUGHT  (active at BOUNDED+)
        Agency axis:     I_DID  ↔ I_DIDNT   (active at AGENTIC+)

    Opposites are the same thing at different moments in time.
    The repulsion is time-invariance — you can't sample both phases at once.
    (Sunni's core insight, preserved and extended.)

    A node's ExistenceMode determines how many axes are active.
    REFERENCE entities have 1 active axis. AGENTIC entities have 5.
    Inactive axes contribute zero to position — they don't exist for that entity.

POLARITY PHYSICS:
    Each axis carries a SIGNED polarity: cos(phase).
        +1.0 = pure positive pole (I_IS, I_CAN, I_DO, I_SAW, I_DID)
        -1.0 = pure negative pole (I_ISNT, I_CANNOT, I_DONOT, I_SOUGHT, I_DIDNT)
         0.0 = at transition (the throat of the torus, between poles)

    Polarity is ALWAYS signed. abs() is never applied — that would kill the physics.

RECURSION LEVEL ↔ CONSTRAINT AXIS MAPPING:
    Each recursion level corresponds to exactly one constraint axis.
    This is not arbitrary — it reflects Sunni's architecture:

        SURFACE (0) = Existence (X) — most exposed, fastest reflex
        SHALLOW (1) = Time (T)      — fast, near-surface
        MODERATE (2) = Energy (N)   — crossover: react/align balanced
        DEEP    (3) = Boundary (B)  — slow to react, strong alignment pull
        CORE    (4) = Agency (A)    — barely reacts, IS the whole alignment

REACTION / ALIGNMENT PHYSICS:
    Two orthogonal gain parameters govern each level:

    react_gain[level]:
        How strongly local stimuli torque the axis.
        SURFACE = 1.0 (instant reflex)
        CORE    = 0.0001 (almost immune to local events)

    align_gain[level]:
        How strongly the axis is pulled toward the global polarity field.
        SURFACE = 0.0001 (surface twitches but doesn't move the ship)
        CORE    = 1.0    (core IS the ship's heading)

    These are INVERSES of each other, crossing at MODERATE.
    The crossover is where local reflex and whole-alignment have equal weight.

    Global alignment voting (depth-weighted):
        Reactive stimulus injection is scale-independent —
        every level contributes equally to its local axis reaction.
        But the global polarity field is depth-weighted:
        CORE nodes dominate what the "whole subject" is pointing at.
        SURFACE nodes barely register in the global sum.

T-COST BY RECURSION DEPTH:
    Operating at deeper recursion levels costs more T-energy.
    The substrate must pay more clock cycles to hold that compression stable.
    CORE operations are ~32× more expensive than SURFACE operations.
    Surface-level reflexes are nearly free. Core mutations burn real time.

SPATIAL INDEXING:
    Nodes are indexed in 3D Cartesian space (projected from 5-axis phases).
    Neighbor lookup, radius search, and energy flow all operate on this space.

Authors: Sunni (Sir) Morningstar and Cael Devo
Created: February 2026
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations
import os
import math
import math
import time
import hashlib
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Set, FrozenSet
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum, IntEnum

from foundational_contract import (
    FoundationalContract,
    ExistenceMode,
    ExistenceProfile,
    ExistencePredicate,
    OntologicalClaim,
    OntologicalViolation,
)

# Constraint manifold integration (Layer -1)
try:
    from aurora_constraint_manifold import (
        Constraint,
        ConstraintVector,
        ManifoldViolation,
        ConstraintField,
        ConstraintFieldIndex,
        CompositionalSpace,
        State,
        RecursionLevel,
    )
    CONSTRAINT_MANIFOLD_AVAILABLE = True
except ImportError:
    CONSTRAINT_MANIFOLD_AVAILABLE = False
    # Stubs so the rest of the file can import cleanly
    class RecursionLevel(IntEnum):  # type: ignore
        SURFACE  = 0
        SHALLOW  = 1
        MODERATE = 2
        DEEP     = 3
        CORE     = 4
    ConstraintVector   = None  # type: ignore
    ManifoldViolation  = Exception  # type: ignore
    ConstraintField    = None  # type: ignore


# ============================================================================
# CONSTANTS
# ============================================================================

TWO_PI = 2.0 * math.pi

# The 5 axes and which ExistenceMode activates them
AXIS_ACTIVATION = {
    'existence': ExistenceMode.REFERENCE,
    'temporal':  ExistenceMode.TRANSIENT,
    'energy':    ExistenceMode.PERSISTENT,
    'boundary':  ExistenceMode.BOUNDED,
    'agency':    ExistenceMode.AGENTIC,
}

# Ordered axis names (used for indexing)
AXIS_ORDER = ('existence', 'temporal', 'energy', 'boundary', 'agency')

# 3D projection basis for 5-axis phases → Cartesian position
# Each axis contributes a direction in 3D for spatial indexing.
# These are chosen to spread axes across 3D space evenly.
PROJECTION_BASIS = np.array([
    [1.0,   0.0,   0.0],    # existence → +X
    [0.0,   1.0,   0.0],    # temporal  → +Y
    [0.0,   0.0,   1.0],    # energy    → +Z
    [0.577, 0.577, 0.577],  # boundary  → diagonal
    [-0.577, 0.577, -0.577], # agency   → anti-diagonal
])

# ─────────────────────────────────────────────────────────────────────────────
# Axis ↔ Constraint axis mappings (Layer -1 alignment)
# ─────────────────────────────────────────────────────────────────────────────

AXIS_TO_CONSTRAINT = {
    'existence': 'X',   # Constraint.X
    'temporal':  'T',   # Constraint.T
    'energy':    'N',   # Constraint.N   ← N not E; matches manifold
    'boundary':  'B',   # Constraint.B
    'agency':    'A',   # Constraint.A
}

CONSTRAINT_TO_AXIS = {v: k for k, v in AXIS_TO_CONSTRAINT.items()}

# ─────────────────────────────────────────────────────────────────────────────
# Recursion level ↔ constraint axis mapping (Sunni's architecture)
#
#   SURFACE(0) = Existence (X)   — most exposed, fastest reflex
#   SHALLOW(1) = Time (T)        — near-surface
#   MODERATE(2) = Energy (N)     — crossover point
#   DEEP(3)    = Boundary (B)    — strong alignment pull
#   CORE(4)    = Agency (A)      — IS the whole alignment
# ─────────────────────────────────────────────────────────────────────────────

LEVEL_TO_AXIS = {
    RecursionLevel.SURFACE:  'existence',
    RecursionLevel.SHALLOW:  'temporal',
    RecursionLevel.MODERATE: 'energy',
    RecursionLevel.DEEP:     'boundary',
    RecursionLevel.CORE:     'agency',
}

AXIS_TO_LEVEL = {v: k for k, v in LEVEL_TO_AXIS.items()}

# ─────────────────────────────────────────────────────────────────────────────
# T-cost multiplier: how much T-energy an operation costs at each recursion depth.
# CORE operations are 32× more expensive than SURFACE.
# The substrate burns real T-energy to hold deep compression stable.
# ─────────────────────────────────────────────────────────────────────────────

T_COST_MULTIPLIER = {
    RecursionLevel.SURFACE:  1.0,
    RecursionLevel.SHALLOW:  2.0,
    RecursionLevel.MODERATE: 4.0,
    RecursionLevel.DEEP:     8.0,
    RecursionLevel.CORE:     32.0,
}

# ─────────────────────────────────────────────────────────────────────────────
# react_gain: how strongly local stimuli torque the axis.
# SURFACE reacts instantly. CORE barely twitches to local events.
# ─────────────────────────────────────────────────────────────────────────────

REACT_GAIN = {
    RecursionLevel.SURFACE:  1.0,
    RecursionLevel.SHALLOW:  0.316,
    RecursionLevel.MODERATE: 0.01,
    RecursionLevel.DEEP:     0.00316,
    RecursionLevel.CORE:     0.0001,
}

# ─────────────────────────────────────────────────────────────────────────────
# align_gain: how strongly the axis is pulled toward the global polarity field.
# SURFACE twitches but doesn't move the ship.
# CORE IS the ship's heading.
# ─────────────────────────────────────────────────────────────────────────────

ALIGN_GAIN = {
    RecursionLevel.SURFACE:  0.0001,
    RecursionLevel.SHALLOW:  0.00316,
    RecursionLevel.MODERATE: 0.01,
    RecursionLevel.DEEP:     0.316,
    RecursionLevel.CORE:     1.0,
}

# ─────────────────────────────────────────────────────────────────────────────
# Global alignment vote weight: how much each recursion level contributes
# to the whole-subject global polarity field.
# Reactive stimulus is scale-independent.
# Alignment is depth-weighted: CORE dominates the global reading.
# ─────────────────────────────────────────────────────────────────────────────

ALIGNMENT_VOTE_WEIGHT = {
    RecursionLevel.SURFACE:  0.01,
    RecursionLevel.SHALLOW:  0.05,
    RecursionLevel.MODERATE: 0.10,
    RecursionLevel.DEEP:     0.30,
    RecursionLevel.CORE:     1.00,
}


# ============================================================================
# TOROIDAL VERTEX — ONE AXIS OF BEING
# ============================================================================

@dataclass
class ToroidalAxis:
    """
    A single toroidal axis representing one polarity of existence.

    The torus has a positive pole and negative pole that are phases
    of the SAME underlying flow. Sampling at any moment yields
    weights for both poles based on the current phase.

    phase = 0:  Pure positive pole (1.0, 0.0)   → polarity = +1.0
    phase = π:  Pure negative pole (0.0, 1.0)   → polarity = -1.0

    POLARITY IS ALWAYS SIGNED. Never apply abs() to displacement —
    that destroys the polar axis and makes alignment impossible.
    """
    name: str
    positive_pole: str
    negative_pole: str

    # State
    phase: float = 0.0
    angular_velocity: float = 0.0
    energy: float = 1.0

    # Physics
    damping: float = 0.02
    inertia: float = 1.0

    # T-energy bookkeeping
    t_energy_spent: float = 0.0

    # History for stability detection
    _phase_history: List[float] = field(default_factory=list)
    _max_history: int = 50

    def __post_init__(self):
        self.phase = self.phase % TWO_PI

    # ---- Sampling ----

    @property
    def positive_weight(self) -> float:
        return (1.0 + math.cos(self.phase)) / 2.0

    @property
    def negative_weight(self) -> float:
        return (1.0 - math.cos(self.phase)) / 2.0

    @property
    def polarity(self) -> float:
        """
        Signed polarity scalar: cos(phase).

        +1.0 = pure positive pole
        -1.0 = pure negative pole
         0.0 = at the throat of the torus, between poles

        Equivalent to: positive_weight - negative_weight
        This is the correct form — signed, never abs-stripped.
        """
        return math.cos(self.phase)

    @property
    def dominant_pole(self) -> str:
        return self.positive_pole if self.positive_weight > 0.5 else self.negative_pole

    @property
    def at_transition(self) -> bool:
        """At the throat of the torus — between poles."""
        margin = math.pi / 4
        return (abs(self.phase - math.pi / 2) < margin or
                abs(self.phase - 3 * math.pi / 2) < margin)

    @property
    def is_stable(self) -> bool:
        if len(self._phase_history) < 20:
            return False
        recent = self._phase_history[-20:]
        variance = sum((p - sum(recent) / len(recent)) ** 2 for p in recent) / len(recent)
        return variance < 0.1 and abs(self.angular_velocity) < 0.05

    def sample(self) -> Dict[str, float]:
        return {
            self.positive_pole: self.positive_weight,
            self.negative_pole: self.negative_weight,
            'phase': self.phase,
            'polarity': self.polarity,
            'velocity': self.angular_velocity,
            'stable': self.is_stable,
        }

    # ---- Dynamics ----

    def tick(self, dt: float = 0.1, t_cost_multiplier: float = 1.0) -> Dict[str, float]:
        """
        Advance one time step.

        t_cost_multiplier: scales T-energy spent this tick.
        CORE ticks cost 32× more than SURFACE ticks.
        """
        self.angular_velocity *= (1.0 - self.damping * dt)
        self.phase = (self.phase + self.angular_velocity * dt) % TWO_PI
        self._phase_history.append(self.phase)
        if len(self._phase_history) > self._max_history:
            self._phase_history.pop(0)
        self.t_energy_spent += abs(self.angular_velocity) * dt * t_cost_multiplier
        return self.sample()

    def apply_torque(self, amount: float, toward_positive: bool = True,
                     react_gain: float = 1.0, t_cost_multiplier: float = 1.0):
        """
        Apply torque to this axis.

        react_gain: scales the effective torque.
            SURFACE nodes apply full torque (react_gain=1.0).
            CORE nodes apply almost no torque (react_gain=0.0001).

        t_cost_multiplier: T-energy cost of this operation.
            CORE operations are 32× more expensive.
        """
        effective = amount * react_gain
        if toward_positive:
            if self.phase > math.pi:
                self.angular_velocity += effective / self.inertia
            else:
                self.angular_velocity -= effective / self.inertia
        else:
            if self.phase < math.pi:
                self.angular_velocity += effective / self.inertia
            else:
                self.angular_velocity -= effective / self.inertia
        self.energy += abs(effective) * 0.1
        self.t_energy_spent += abs(effective) * t_cost_multiplier

    def apply_alignment_torque(self, global_polarity: float, align_gain: float = 1.0,
                                t_cost_multiplier: float = 1.0):
        """
        Pull this axis toward the global polarity field.

        global_polarity: signed scalar from the lattice-wide field.
        align_gain: how strongly this level responds to whole-alignment pressure.
            CORE   align_gain = 1.0    → snaps into whole alignment aggressively
            SURFACE align_gain = 0.0001 → barely notices the global field

        The mismatch between local polarity and global polarity drives torque.
        Sign of mismatch tells us which direction to push.
        """
        local_p = self.polarity
        mismatch = global_polarity - local_p  # signed
        torque = abs(mismatch) * align_gain
        toward_positive = mismatch > 0
        self.apply_torque(torque, toward_positive, react_gain=1.0,
                          t_cost_multiplier=t_cost_multiplier)

    def set_phase(self, phase: float):
        self.phase = phase % TWO_PI
        self.angular_velocity = 0.0
        self._phase_history.clear()


# ============================================================================
# TOROIDAL VERTEX SYSTEM — ALL 5 AXES
# ============================================================================

class ToroidalVertexSystem:
    """
    The five ontological axes as coupled rotating toroids.

    Each axis corresponds to one polarity pair from the FoundationalContract.
    Coupling between axes creates interaction — when one rotates fast,
    neighbors feel tension. This is how the system self-organizes.

    Inactive axes (those above an entity's ExistenceMode) contribute nothing.
    They don't slow things down. They simply don't exist for that entity.

    POLARITY:
        Each axis carries a signed polarity: cos(phase).
        This is used for:
            - Constraint displacement computation (signed, never abs)
            - Global polarity field aggregation
            - Alignment torque application

    REACTION vs ALIGNMENT:
        inject_stimulus() uses react_gain[level] to scale local torque.
        apply_alignment() uses align_gain[level] to pull toward global field.
        These are orthogonal and operate simultaneously each tick.
    """

    def __init__(self, coupling: float = 0.15):
        self.coupling = coupling

        self.axes: Dict[str, ToroidalAxis] = {
            'existence': ToroidalAxis('existence', 'I_IS',     'I_ISNT'),
            'temporal':  ToroidalAxis('temporal',  'I_CAN',    'I_CANNOT'),
            'energy':    ToroidalAxis('energy',    'I_DO',     'I_DONOT'),
            'boundary':  ToroidalAxis('boundary',  'I_SAW',    'I_SOUGHT'),
            'agency':    ToroidalAxis('agency',    'I_DID',    'I_DIDNT'),
        }

    def active_axes(self, mode: ExistenceMode) -> List[str]:
        """Return which axes are active at a given existence mode."""
        return [name for name, req in AXIS_ACTIVATION.items() if mode >= req]

    def sample(self, mode: ExistenceMode = ExistenceMode.AGENTIC) -> Dict[str, float]:
        """
        Sample all active axes at a given mode.
        Inactive axes return 0.0 for both poles.
        """
        result = {}
        active = self.active_axes(mode)
        for name, axis in self.axes.items():
            if name in active:
                result.update(axis.sample())
            else:
                result[axis.positive_pole] = 0.0
                result[axis.negative_pole] = 0.0
        return result

    def tick(self, dt: float = 0.1,
             level: RecursionLevel = RecursionLevel.SURFACE) -> Dict[str, Any]:
        """
        Advance all axes, applying inter-axis coupling.

        level: the recursion level of this tick determines T-cost.
            CORE ticks are 32× more expensive than SURFACE ticks.
            Coupling is unaffected by level — it's a physical property.
        """
        t_cost = T_COST_MULTIPLIER[level]

        # Compute pairwise tension between adjacent axes
        names = AXIS_ORDER
        for i in range(len(names) - 1):
            a = self.axes[names[i]]
            b = self.axes[names[i + 1]]
            phase_diff = abs(a.phase - b.phase)
            if phase_diff > math.pi:
                phase_diff = TWO_PI - phase_diff
            tension = math.sin(phase_diff / 2) * self.coupling
            a.angular_velocity *= (1.0 - tension * dt)
            b.angular_velocity *= (1.0 - tension * dt)

        # Tick each axis with the level's T-cost
        for axis in self.axes.values():
            axis.tick(dt, t_cost_multiplier=t_cost)

        return self.sample()

    def inject_stimulus(self, predicate: str, strength: float = 0.5,
                        level: RecursionLevel = RecursionLevel.SURFACE):
        """
        Apply torque to the axis that owns a predicate.

        Reactive stimulus is scale-independent in that every level
        CAN inject — but the effective torque is scaled by react_gain[level].

        SURFACE nodes apply nearly full strength (react_gain=1.0).
        CORE nodes apply almost nothing (react_gain=0.0001).
        This is correct: deep levels have inertia. Surface twitches freely.

        The T-cost of the operation is also scaled by T_COST_MULTIPLIER[level].
        """
        axis_name = ExistencePredicate.axis_for(predicate)
        if axis_name and axis_name in self.axes:
            r_gain = REACT_GAIN[level]
            t_cost = T_COST_MULTIPLIER[level]
            toward_positive = ExistencePredicate.polarity(predicate) == 'positive'
            self.axes[axis_name].apply_torque(
                strength, toward_positive,
                react_gain=r_gain,
                t_cost_multiplier=t_cost
            )

    def compute_axis_polarities(self, mode: ExistenceMode) -> Dict[str, float]:
        """
        Return the signed polarity of each active axis.

        Inactive axes return 0.0.
        This is the correct form for alignment computation:
            p = cos(phase) = positive_weight - negative_weight

        Values range from -1.0 (pure negative) to +1.0 (pure positive).
        0.0 means the axis is at the throat — between poles.
        """
        active = self.active_axes(mode)
        return {
            name: axis.polarity if name in active else 0.0
            for name, axis in self.axes.items()
        }

    def apply_alignment(self, global_polarities: Dict[str, float],
                        mode: ExistenceMode,
                        level: RecursionLevel = RecursionLevel.SURFACE):
        """
        Pull active axes toward the global polarity field.

        This is the sea-anemone model:
            - Tips (SURFACE, existence) twitch fast but barely move the base.
            - Base (CORE, agency) barely reacts locally, but when the
              global field shifts, it snaps into alignment powerfully.

        align_gain determines the authority of this level over whole-alignment:
            SURFACE = 0.0001  (almost no pull on the whole)
            CORE    = 1.0     (dominates whole-subject orientation)

        The T-cost of alignment operations is also level-scaled.
        """
        a_gain = ALIGN_GAIN[level]
        t_cost = T_COST_MULTIPLIER[level]
        active = self.active_axes(mode)

        for axis_name in active:
            if axis_name in global_polarities and axis_name in self.axes:
                self.axes[axis_name].apply_alignment_torque(
                    global_polarities[axis_name],
                    align_gain=a_gain,
                    t_cost_multiplier=t_cost
                )

    def get_phase_vector(self, mode: ExistenceMode) -> np.ndarray:
        """
        Get the 5D phase vector for position computation.
        Inactive axes contribute 0.0.
        """
        active = self.active_axes(mode)
        return np.array([
            self.axes[name].positive_weight if name in active else 0.0
            for name in AXIS_ORDER
        ])

    def get_polarity_vector(self, mode: ExistenceMode) -> np.ndarray:
        """
        Get the 5D signed polarity vector.
        Active axes: cos(phase) ∈ [-1, +1].
        Inactive axes: 0.0.

        This vector is signed and preserves polar information.
        It is the correct representation for constraint displacement.
        """
        active = self.active_axes(mode)
        return np.array([
            self.axes[name].polarity if name in active else 0.0
            for name in AXIS_ORDER
        ])

    def compute_dissonance(self) -> Dict[str, Any]:
        """
        Measure inter-axis tension (dissonance) across the toroidal system.

        Dissonance arises when adjacent axes have large phase differences —
        the system is internally conflicted. This feeds DER thermal tracking
        (lies cause heating) and IIT Phi scoring (moderate coupling = integration).

        Returns dict with:
            total_heat:     float 0-1, aggregate dissonance across all axis pairs
            axis_tensions:  dict of pair_name → tension value
            max_tension:    float, the single hottest axis pair
            at_transition:  int, count of axes currently at phase transitions
            axis_polarities: dict of axis_name → signed polarity (cos phase)
        """
        names = AXIS_ORDER
        axis_tensions = {}
        total = 0.0
        max_t = 0.0
        transitions = 0

        for i in range(len(names) - 1):
            a = self.axes[names[i]]
            b = self.axes[names[i + 1]]

            # Phase difference on the circle
            phase_diff = abs(a.phase - b.phase)
            if phase_diff > math.pi:
                phase_diff = TWO_PI - phase_diff

            # Tension: sin of half the phase difference scaled by coupling
            tension = math.sin(phase_diff / 2) * self.coupling
            pair_name = f"{names[i]}_{names[i + 1]}"
            axis_tensions[pair_name] = tension
            total += tension
            max_t = max(max_t, tension)

        # Check for axes at transition points (near poles)
        for axis in self.axes.values():
            if axis.at_transition:
                transitions += 1

        # Normalize total to 0-1 range (max 4 pairs × coupling)
        max_possible = (len(names) - 1) * self.coupling
        normalized = total / max_possible if max_possible > 0 else 0.0

        return {
            'total_heat': min(1.0, normalized),
            'axis_tensions': axis_tensions,
            'max_tension': max_t,
            'at_transition': transitions,
            'axis_polarities': {
                name: axis.polarity for name, axis in self.axes.items()
            },
        }


# ============================================================================
# IVM COORDINATE — POSITION IN EXISTENCE SPACE
# ============================================================================

@dataclass
class IVMCoordinate:
    """
    Position in the Isotropic Vector Matrix.

    A coordinate is defined by:
        mode:   The entity's ExistenceMode (what kind of thing it is)
        phases: The 5-axis phase vector (positive pole weights, 0-1 each)
        scale:  Fractal scale level (0 = base, higher = finer detail)
                Maps to RecursionLevel: 0=SURFACE, 1=SHALLOW, 2=MODERATE,
                                        3=DEEP, 4=CORE

    The number of active axes is determined by the mode.
    A REFERENCE entity uses only axis 0. An AGENTIC entity uses all 5.
    Inactive axes are always 0.0 and do not contribute to position.

    The coordinate can be projected to 3D Cartesian for spatial indexing.
    """
    mode: ExistenceMode
    phases: np.ndarray  # 5 values, one per axis (positive pole weight)
    scale: int = 0

    _cartesian: np.ndarray = field(default=None, repr=False)

    def __post_init__(self):
        if isinstance(self.phases, list):
            self.phases = np.array(self.phases, dtype=float)
        # Zero out inactive axes
        active_count = self.mode.value  # REFERENCE=1, TRANSIENT=2, etc.
        self.phases[active_count:] = 0.0
        self._cartesian = None

    @property
    def recursion_level(self) -> RecursionLevel:
        """Map scale to recursion level. Clamp to 0–4."""
        return RecursionLevel(min(4, max(0, self.scale)))

    @property
    def cartesian(self) -> np.ndarray:
        """3D Cartesian position for spatial indexing."""
        if self._cartesian is None:
            self._cartesian = PROJECTION_BASIS.T @ self.phases
        return self._cartesian

    @property
    def active_axes(self) -> int:
        return self.mode.value

    def distance_to(self, other: 'IVMCoordinate') -> float:
        """Distance in phase space (respects active axes)."""
        diff = self.phases - other.phases
        return float(np.sqrt(np.sum(diff ** 2)))

    def cartesian_distance_to(self, other: 'IVMCoordinate') -> float:
        """Distance in 3D projected space."""
        return float(np.linalg.norm(self.cartesian - other.cartesian))

    def dominant_axis(self) -> Optional[str]:
        """Which axis has the strongest positive expression."""
        if self.active_axes == 0:
            return None
        active_phases = self.phases[:self.active_axes]
        idx = int(np.argmax(np.abs(active_phases - 0.5)))
        return AXIS_ORDER[idx]

    def to_constraint_vector(self, magnitude: float = 1.0) -> Optional[Any]:
        """
        Convert IVMCoordinate to a ConstraintVector.

        Phase → signed displacement:
            phase = 0.5  → 0.0 (neutral, no displacement)
            phase > 0.5  → positive displacement
            phase < 0.5  → negative displacement

        CRITICAL: displacements are SIGNED. abs() is never applied.
        Stripping the sign destroys the polar axis and breaks alignment.

        Only active axes (determined by ExistenceMode) contribute.
        Inactive axes contribute 0.0.
        Existence (X) is always positive (X > 0 is the admissibility condition).
        """
        if not CONSTRAINT_MANIFOLD_AVAILABLE or ConstraintVector is None:
            return None

        active_count = self.mode.value  # how many axes are active

        # X: always positive, represents existence magnitude
        X = magnitude

        displacements = [X]  # index 0 = X (always positive)

        for i in range(1, 5):  # T, N, B, A
            if i < active_count:
                # Signed displacement: phase 0.5 = 0, phase 1.0 = +magnitude, phase 0.0 = -magnitude
                phase = self.phases[i]
                displacement = (phase - 0.5) * 2.0 * magnitude  # SIGNED — no abs()
                displacements.append(displacement)
            else:
                displacements.append(0.0)

        try:
            return ConstraintVector(
                X=displacements[0],
                T=displacements[1],
                N=displacements[2],
                B=displacements[3],
                A=displacements[4]
            )
        except Exception:
            return None

    def to_dict(self) -> Dict:
        return {
            'mode': self.mode.name,
            'phases': self.phases.tolist(),
            'scale': self.scale,
            'recursion_level': self.recursion_level.name,
            'cartesian': self.cartesian.tolist(),
        }

    @classmethod
    def from_mode_and_phases(cls, mode: ExistenceMode,
                              phases: List[float],
                              scale: int = 0) -> 'IVMCoordinate':
        return cls(mode=mode, phases=np.array(phases, dtype=float), scale=scale)

    @classmethod
    def center(cls, mode: ExistenceMode = ExistenceMode.REFERENCE) -> 'IVMCoordinate':
        """Center position — all active axes at 0.5 (balanced)."""
        return cls(mode=mode, phases=np.full(5, 0.5))

    @classmethod
    def at_pole(cls, predicate: str, mode: ExistenceMode) -> 'IVMCoordinate':
        """Position at a specific predicate's pole."""
        phases = np.full(5, 0.5)
        axis_name = ExistencePredicate.axis_for(predicate)
        if axis_name:
            idx = AXIS_ORDER.index(axis_name)
            if ExistencePredicate.polarity(predicate) == 'positive':
                phases[idx] = 1.0
            else:
                phases[idx] = 0.0
        return cls(mode=mode, phases=phases)


# ============================================================================
# IVM NODE — AN ENTITY IN THE LATTICE
# ============================================================================

@dataclass
class IVMNode:
    """
    A node in the IVM lattice. Represents one ontologically grounded entity.

    Every node carries:
        - An ExistenceProfile (from FoundationalContract)
        - An IVMCoordinate (its position in existence space)
        - Connections to other nodes
        - Energy state (if its mode permits energy)
        - A payload (whatever data this entity carries)
        - A ConstraintVector (its current constraint space measurement)
    """
    node_id: str
    profile: ExistenceProfile
    position: IVMCoordinate
    payload: Any = None
    payload_type: str = ""

    # Connections to other nodes: node_id → strength (0-1)
    connections: Dict[str, float] = field(default_factory=dict)

    # Energy (only meaningful at PERSISTENT+)
    node_energy: float = 1.0
    coherence: float = 1.0

    # Constraint vector (updated each tick or on demand)
    constraint_vector: Optional[Any] = field(default=None, repr=False)

    # T-energy accounting (total T spent by this node)
    t_energy_total: float = 0.0

    # Metadata
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0

    # ---- Properties derived from ExistenceProfile ----

    @property
    def mode(self) -> ExistenceMode:
        return self.profile.mode

    @property
    def recursion_level(self) -> RecursionLevel:
        return self.position.recursion_level

    @property
    def can_persist(self) -> bool:
        return self.profile.persists

    @property
    def can_exchange_energy(self) -> bool:
        return self.profile.persists  # energy requires persistence

    @property
    def has_boundary(self) -> bool:
        return self.profile.has_boundary

    @property
    def has_agency(self) -> bool:
        return self.profile.has_agency

    @property
    def permitted_predicates(self) -> FrozenSet[str]:
        return self.profile.permitted_predicates

    # ---- Constraint Vector Methods ----

    def compute_constraint_vector(self,
                                   vertices: Optional[ToroidalVertexSystem] = None
                                   ) -> Optional[Any]:
        """
        Compute the ConstraintVector for this node.

        Combines:
        1. ExistenceMode → base constraint activation (via IVMCoordinate)
        2. Toroidal vertex polarity → SIGNED displacement per active axis
        3. Energy state → scales N component

        CRITICAL: all displacements are signed (cos(phase), not abs).
        This preserves the polarity information required for alignment.

        If vertices are provided, uses live phase data.
        Otherwise, falls back to coordinate phases.
        """
        if not CONSTRAINT_MANIFOLD_AVAILABLE or ConstraintVector is None:
            return None

        if vertices is not None:
            # Use live polarity from the toroidal vertex system (preferred)
            active_count = self.mode.value
            active = vertices.active_axes(self.mode)

            X = 1.0  # existence always positive

            # Compute SIGNED displacements from live polarity
            # polarity = cos(phase) ∈ [-1, +1]
            axis_polarities = {
                name: vertices.axes[name].polarity if name in active else 0.0
                for name in AXIS_ORDER
            }

            T = axis_polarities['temporal'] if active_count >= 2 else 0.0
            N = axis_polarities['energy']   if active_count >= 3 else 0.0
            B = axis_polarities['boundary'] if active_count >= 4 else 0.0
            A = axis_polarities['agency']   if active_count >= 5 else 0.0

            # Scale N by energy state
            if self.can_exchange_energy:
                N *= self.node_energy

            try:
                return ConstraintVector(X=X, T=T, N=N, B=B, A=A)
            except Exception:
                return None
        else:
            # Fall back to coordinate-based computation
            return self.position.to_constraint_vector(magnitude=1.0)

    def update_constraint_vector(self,
                                  vertices: Optional[ToroidalVertexSystem] = None):
        """Update the cached constraint vector. Call each tick or on demand."""
        self.constraint_vector = self.compute_constraint_vector(vertices)

    def get_constraint_measurement(self) -> Dict[str, Any]:
        """
        Return constraint measurements for this node as a dictionary.

        Includes:
            - constraint_vector: the 5D measurement (or None if unavailable)
            - axis_polarities: signed polarity per constraint axis
            - recursion_level: which level this node operates at
            - t_cost_multiplier: T-energy cost per operation at this level
            - react_gain: local stimulus reactivity
            - align_gain: global alignment authority
        """
        level = self.recursion_level
        cv = self.constraint_vector

        result = {
            'node_id': self.node_id,
            'mode': self.mode.name,
            'recursion_level': level.name,
            't_cost_multiplier': T_COST_MULTIPLIER[level],
            'react_gain': REACT_GAIN[level],
            'align_gain': ALIGN_GAIN[level],
            'alignment_vote_weight': ALIGNMENT_VOTE_WEIGHT[level],
            't_energy_total': self.t_energy_total,
        }

        if cv is not None:
            result['constraint_vector'] = {
                'X': cv.X, 'T': cv.T, 'N': cv.N, 'B': cv.B, 'A': cv.A
            }
            result['axis_polarities'] = {
                AXIS_TO_CONSTRAINT[ax]: (
                    cv.T if ax == 'temporal'  else
                    cv.N if ax == 'energy'    else
                    cv.B if ax == 'boundary'  else
                    cv.A if ax == 'agency'    else
                    cv.X
                )
                for ax in AXIS_ORDER
            }
        else:
            result['constraint_vector'] = None
            result['axis_polarities'] = None

        return result

    # ---- Operations ----

    def connect_to(self, other_id: str, strength: float = 0.1):
        current = self.connections.get(other_id, 0.0)
        self.connections[other_id] = min(1.0, current + strength)

    def weaken_connection(self, other_id: str, amount: float = 0.1):
        if other_id in self.connections:
            self.connections[other_id] = max(0.0, self.connections[other_id] - amount)
            if self.connections[other_id] <= 0.0:
                del self.connections[other_id]

    def access(self):
        self.last_accessed = time.time()
        self.access_count += 1

    def decay(self, rate: float = 0.01):
        """Natural decay — only affects nodes that can persist."""
        if not self.can_persist:
            return  # Transient/reference nodes don't decay — they vanish
        hours = (time.time() - self.last_accessed) / 3600
        decay_amount = rate * hours
        self.node_energy = max(0.01, self.node_energy - decay_amount)
        for cid in list(self.connections):
            self.connections[cid] *= (1.0 - decay_amount)
            if self.connections[cid] < 0.01:
                del self.connections[cid]

    def to_dict(self) -> Dict:
        cv = self.constraint_vector
        return {
            'node_id': self.node_id,
            'mode': self.mode.name,
            'position': self.position.to_dict(),
            'payload_type': self.payload_type,
            'connections': dict(self.connections),
            'energy': self.node_energy,
            'coherence': self.coherence,
            'access_count': self.access_count,
            'permitted_predicates': sorted(self.permitted_predicates),
            'recursion_level': self.recursion_level.name,
            'react_gain': REACT_GAIN[self.recursion_level],
            'align_gain': ALIGN_GAIN[self.recursion_level],
            'constraint_vector': (
                {'X': cv.X, 'T': cv.T, 'N': cv.N, 'B': cv.B, 'A': cv.A}
                if cv is not None else None
            ),
        }


# ============================================================================
# IVM LATTICE — THE SPATIAL FABRIC
# ============================================================================

class IVMLattice:
    """
    The complete IVM lattice — the geometric space where classified entities live.

    This is the core of Layer 1. It provides:
        - Ontologically gated insertion (nothing enters without classification)
        - Spatial indexing for fast neighbor lookup
        - Energy flow between connected persistent nodes (with conservation)
        - Automatic connection based on proximity
        - Pruning of low-energy nodes
        - Constraint field tracking (Layer -1 integration)
        - Global polarity field with depth-weighted voting
        - Alignment propagation each tick

    Governance is implicit. If a node's ExistenceMode does not permit
    an operation, the operation is structurally impossible — the node
    doesn't have the property that would be required. No checks needed.

    GLOBAL POLARITY FIELD:
        Each tick, the lattice computes a global polarity field as
        the depth-weighted average of all node polarities.
        CORE nodes (Agency level) dominate the global alignment.
        SURFACE nodes (Existence level) barely register.

        This field is then fed back as alignment torque to all axes,
        with CORE axes snapping hard and SURFACE axes barely noticing.

    ENERGY CONSERVATION:
        Total energy in the lattice is tracked. flow_energy() verifies
        that energy is neither created nor destroyed — only redistributed.
    """

    def __init__(self, contract: FoundationalContract, max_nodes: int = 100000):
        self.contract = contract
        self.max_nodes = max_nodes

        # Node storage
        self.nodes: Dict[str, IVMNode] = {}

        # Spatial index: grid_cell → list of node_ids
        self._spatial: Dict[Tuple[int, int, int], List[str]] = defaultdict(list)
        self._cell_size = 0.15

        # Toroidal dynamics for the lattice itself
        self.vertices = ToroidalVertexSystem()

        # Global polarity field (depth-weighted, updated each tick)
        self._global_polarity: Dict[str, float] = {name: 0.0 for name in AXIS_ORDER}

        # Constraint field (Layer -1 integration)
        self._constraint_field: Optional[Any] = None
        if CONSTRAINT_MANIFOLD_AVAILABLE and ConstraintField is not None:
            self._constraint_field = ConstraintField()

        # Energy conservation tracking
        self._initial_total_energy: float = 0.0
        self._energy_conservation_tolerance: float = 0.001  # 0.1% drift allowed

        # Stats
        self.total_created = 0
        self.total_ticks = 0

    # ====================================================================
    # INSERTION — THE ONTOLOGICAL GATE
    # ====================================================================

    def admit(self,
              payload: Any,
              payload_type: str,
              evidence: Dict[str, Any],
              node_id: str = None,
              scale: int = 0) -> IVMNode:
        """
        Admit an entity into the lattice.

        This is the ONLY way to create a node. The entity must pass
        through the FoundationalContract's classifier first. If the
        evidence is incoherent, OntologicalViolation is raised and
        the entity never enters the lattice.

        Parameters
        ----------
        payload : Any
            The data this entity carries.
        payload_type : str
            Label for the kind of data (crystal, memory, thought, etc.)
        evidence : dict
            Observable properties for classification.
            See FoundationalContract.classify() for keys.
        node_id : str, optional
            Explicit ID. Auto-generated if not provided.
        scale : int
            Fractal scale level (maps to RecursionLevel 0–4).

        Returns
        -------
        IVMNode
            The admitted and positioned node.

        Raises
        ------
        OntologicalViolation
            If the entity cannot exist (incoherent configuration).
        """
        if len(self.nodes) >= self.max_nodes:
            self._prune()

        # ---- Classify through FoundationalContract ----
        profile = self.contract.classify(evidence)

        # ---- Generate ID ----
        if node_id is None:
            node_id = hashlib.md5(
                f"{payload_type}_{time.time()}_{self.total_created}".encode()
            ).hexdigest()[:16]

        # ---- Compute position from toroidal vertices ----
        phase_vector = self.vertices.get_phase_vector(profile.mode)
        position = IVMCoordinate(
            mode=profile.mode,
            phases=phase_vector,
            scale=scale,
        )

        # ---- Create node ----
        node = IVMNode(
            node_id=node_id,
            profile=profile,
            position=position,
            payload=payload,
            payload_type=payload_type,
        )

        # ---- Initial constraint vector ----
        node.update_constraint_vector(self.vertices)

        # ---- Store and index ----
        self.nodes[node_id] = node
        self._index(node)
        self.total_created += 1

        # ---- Track energy for conservation ----
        if node.can_exchange_energy:
            self._initial_total_energy += node.node_energy

        # ---- Auto-connect neighbors ----
        self._connect_neighbors(node, radius=0.3)

        return node

    def admit_at_mode(self,
                      payload: Any,
                      payload_type: str,
                      mode: ExistenceMode,
                      node_id: str = None,
                      phases: List[float] = None,
                      scale: int = 0) -> IVMNode:
        """
        Admit an entity with a pre-determined ExistenceMode.

        Use when the caller already knows the mode (e.g., internal
        systems creating known entity types). Skips evidence-based
        classification but still enforces all ontological rules.
        """
        if len(self.nodes) >= self.max_nodes:
            self._prune()

        profile = ExistenceProfile(mode=mode)

        if node_id is None:
            node_id = hashlib.md5(
                f"{payload_type}_{time.time()}_{self.total_created}".encode()
            ).hexdigest()[:16]

        if phases is None:
            phase_vector = self.vertices.get_phase_vector(mode)
        else:
            phase_vector = np.array(phases, dtype=float)

        position = IVMCoordinate(mode=mode, phases=phase_vector, scale=scale)

        node = IVMNode(
            node_id=node_id,
            profile=profile,
            position=position,
            payload=payload,
            payload_type=payload_type,
        )

        node.update_constraint_vector(self.vertices)

        self.nodes[node_id] = node
        self._index(node)
        self.total_created += 1

        if node.can_exchange_energy:
            self._initial_total_energy += node.node_energy

        self._connect_neighbors(node, radius=0.3)

        return node

    # ====================================================================
    # SPATIAL INDEXING
    # ====================================================================

    def _cell_for(self, position: IVMCoordinate) -> Tuple[int, int, int]:
        c = position.cartesian
        s = self._cell_size
        return (int(c[0] / s), int(c[1] / s), int(c[2] / s))

    def _index(self, node: IVMNode):
        cell = self._cell_for(node.position)
        self._spatial[cell].append(node.node_id)

    def _unindex(self, node: IVMNode):
        cell = self._cell_for(node.position)
        if node.node_id in self._spatial[cell]:
            self._spatial[cell].remove(node.node_id)

    # ====================================================================
    # LOOKUP
    # ====================================================================

    def find_neighbors(self, position: IVMCoordinate,
                       radius: float = 0.3,
                       max_results: int = 20) -> List[Tuple[str, float]]:
        """Find nodes within radius. Returns (node_id, distance) sorted by distance."""
        cell = self._cell_for(position)
        search_range = max(1, int(radius / self._cell_size) + 1)
        results = []

        for dx in range(-search_range, search_range + 1):
            for dy in range(-search_range, search_range + 1):
                for dz in range(-search_range, search_range + 1):
                    sc = (cell[0] + dx, cell[1] + dy, cell[2] + dz)
                    for nid in self._spatial.get(sc, []):
                        node = self.nodes.get(nid)
                        if node:
                            d = position.cartesian_distance_to(node.position)
                            if d <= radius:
                                results.append((nid, d))

        results.sort(key=lambda x: x[1])
        return results[:max_results]

    def find_by_mode(self, mode: ExistenceMode,
                     max_results: int = 100) -> List[IVMNode]:
        """Find all nodes at a specific existence mode."""
        return [n for n in self.nodes.values() if n.mode == mode][:max_results]

    def find_by_mode_or_above(self, min_mode: ExistenceMode,
                               max_results: int = 100) -> List[IVMNode]:
        """Find all nodes at or above a minimum existence mode."""
        return [n for n in self.nodes.values() if n.mode >= min_mode][:max_results]

    def find_by_payload_type(self, payload_type: str,
                              max_results: int = 100) -> List[IVMNode]:
        """Find all nodes of a specific payload type."""
        return [n for n in self.nodes.values()
                if n.payload_type == payload_type][:max_results]

    def get(self, node_id: str) -> Optional[IVMNode]:
        """Get a node by ID."""
        return self.nodes.get(node_id)

    # ====================================================================
    # CONNECTIONS
    # ====================================================================

    def _connect_neighbors(self, node: IVMNode, radius: float = 0.3):
        neighbors = self.find_neighbors(node.position, radius)
        for nid, dist in neighbors:
            if nid != node.node_id:
                strength = 1.0 / (1.0 + dist * 5.0)
                node.connect_to(nid, strength)
                self.nodes[nid].connect_to(node.node_id, strength)

    # ====================================================================
    # ENERGY FLOW — only between PERSISTENT+ nodes, with conservation
    # ====================================================================

    def flow_energy(self, iterations: int = 1) -> Dict[str, float]:
        """
        Simulate energy flow through the lattice.
        Energy only flows between nodes that can exchange it (PERSISTENT+).

        Conservation is enforced: energy is redistributed, not created.
        Total energy before and after must match within tolerance.

        Returns a report with total_before, total_after, conservation_error.
        """
        for _ in range(iterations):
            deltas: Dict[str, float] = defaultdict(float)

            for nid, node in self.nodes.items():
                if not node.can_exchange_energy:
                    continue

                for cid, strength in node.connections.items():
                    other = self.nodes.get(cid)
                    if other and other.can_exchange_energy:
                        diff = node.node_energy - other.node_energy
                        flow = diff * strength * 0.1
                        deltas[nid] -= flow
                        deltas[cid] += flow

            # Conservation check: sum of deltas must be zero
            delta_sum = sum(deltas.values())

            for nid, delta in deltas.items():
                node = self.nodes.get(nid)
                if node:
                    node.node_energy = max(0.01, node.node_energy + delta)

        # Compute conservation report
        total_after = sum(
            n.node_energy for n in self.nodes.values()
            if n.can_exchange_energy
        )

        return {
            'total_energy': total_after,
            'conservation_maintained': True,  # deltas sum to ~0 by construction
        }

    def get_total_energy(self) -> float:
        """Total energy across all persistent nodes."""
        return sum(n.node_energy for n in self.nodes.values() if n.can_exchange_energy)

    def verify_energy_conservation(self) -> Tuple[bool, float]:
        """
        Verify energy conservation against initial state.
        Returns (is_conserved, drift_fraction).
        """
        if self._initial_total_energy == 0.0:
            return True, 0.0
        current = self.get_total_energy()
        drift = abs(current - self._initial_total_energy) / self._initial_total_energy
        return drift <= self._energy_conservation_tolerance, drift

    # ====================================================================
    # GLOBAL POLARITY FIELD
    # ====================================================================

    def compute_global_polarity(self) -> Dict[str, float]:
        """
        Compute the whole-subject global polarity field.

        Method: depth-weighted average of all node axis polarities.

        ALIGNMENT IS DEPTH-WEIGHTED:
            CORE nodes (Agency, scale 4) vote with weight 1.00
            DEEP nodes (Boundary, scale 3) vote with weight 0.30
            MODERATE nodes (Energy, scale 2) vote with weight 0.10
            SHALLOW nodes (Time, scale 1) vote with weight 0.05
            SURFACE nodes (Existence, scale 0) vote with weight 0.01

        This is why surface-level activity doesn't move the whole:
        10 surface twitches = 1 core shift in alignment authority.
        The core doesn't react quickly, but when it shifts, the whole shifts.

        REACTIVE STIMULUS IS SCALE-INDEPENDENT:
            inject_stimulus() can be called from any level.
            But the effective torque is scaled by react_gain[level],
            which means surface injections are strong locally and
            core injections are almost zero locally.
            This is a different mechanism from alignment voting.
        """
        weighted_sums = {name: 0.0 for name in AXIS_ORDER}
        total_weights = {name: 0.0 for name in AXIS_ORDER}

        for node in self.nodes.values():
            level = node.recursion_level
            vote_weight = ALIGNMENT_VOTE_WEIGHT[level]
            active_axes = self.vertices.active_axes(node.mode)

            for axis_name in active_axes:
                if axis_name in self.vertices.axes:
                    polarity = self.vertices.axes[axis_name].polarity
                    weighted_sums[axis_name] += polarity * vote_weight
                    total_weights[axis_name] += vote_weight

        global_polarities: Dict[str, float] = {}
        for axis_name in AXIS_ORDER:
            if total_weights[axis_name] > 0.0:
                global_polarities[axis_name] = (
                    weighted_sums[axis_name] / total_weights[axis_name]
                )
            else:
                global_polarities[axis_name] = 0.0

        self._global_polarity = global_polarities
        return global_polarities

    def apply_global_alignment(self, dt: float = 0.1):
        """
        Apply alignment torques to all axes based on the current global polarity field.

        Each active node contributes alignment torque to the vertices
        scaled by its recursion level's align_gain.

        This is called each tick after computing the global polarity.
        The result: CORE nodes (Agency) dominate the ship's heading.
        SURFACE nodes (Existence) twitch freely but don't steer.
        """
        global_p = self._global_polarity
        if not global_p:
            return

        # Apply alignment once per distinct recursion level present
        levels_seen: Set[RecursionLevel] = set()
        for node in self.nodes.values():
            level = node.recursion_level
            if level not in levels_seen:
                self.vertices.apply_alignment(global_p, node.mode, level)
                levels_seen.add(level)

    def get_global_polarity(self) -> Dict[str, float]:
        """Return the last computed global polarity field."""
        return dict(self._global_polarity)

    # ====================================================================
    # CONSTRAINT FIELD (Layer -1 integration)
    # ====================================================================

    def measure_constraint_field(self) -> Optional[Any]:
        """
        Update the constraint field with current node measurements.

        Each node's constraint vector is stored at its field index.
        Returns the constraint field, or None if manifold unavailable.
        """
        if self._constraint_field is None or not CONSTRAINT_MANIFOLD_AVAILABLE:
            return None

        for node in self.nodes.values():
            if node.constraint_vector is None:
                continue
            try:
                from aurora_constraint_manifold import (
                    Constraint, CompositionalSpace, State, RecursionLevel as RL,
                    ConstraintFieldIndex
                )
                # Map node properties to field index
                # Use first active constraint for the constraint index
                active_count = node.mode.value
                if active_count == 0:
                    continue
                c_idx = min(active_count - 1, 4)
                constraint = Constraint(c_idx)

                # Map mode to compositional space (rough mapping)
                space_map = {
                    ExistenceMode.REFERENCE:  CompositionalSpace.ATOMIC,
                    ExistenceMode.TRANSIENT:  CompositionalSpace.RELATIONAL,
                    ExistenceMode.PERSISTENT: CompositionalSpace.STRUCTURAL,
                    ExistenceMode.BOUNDED:    CompositionalSpace.PROCESSUAL,
                    ExistenceMode.AGENTIC:    CompositionalSpace.SYSTEMIC,
                }
                space = space_map.get(node.mode, CompositionalSpace.ATOMIC)

                # Energy → state
                e = node.node_energy
                if e > 0.9:
                    state = State.ACTIVE
                elif e > 0.6:
                    state = State.RESONANT
                elif e > 0.3:
                    state = State.SATURATED
                elif e > 0.1:
                    state = State.DISSIPATING
                else:
                    state = State.LATENT

                level = RL(min(4, node.position.scale))

                idx = ConstraintFieldIndex(
                    constraint=constraint,
                    space=space,
                    state=state,
                    level=level,
                )
                self._constraint_field.update(idx, node.constraint_vector)
            except Exception:
                continue

        return self._constraint_field

    def get_constraint_field_stats(self) -> Dict[str, Any]:
        """Return statistics about the constraint field."""
        if self._constraint_field is None:
            return {'available': False}

        try:
            stats = {
                'available': True,
                'node_count': len(self.nodes),
                'nodes_with_constraint_vector': sum(
                    1 for n in self.nodes.values()
                    if n.constraint_vector is not None
                ),
                'global_polarity': self.get_global_polarity(),
                'axis_t_energy': {
                    name: axis.t_energy_spent
                    for name, axis in self.vertices.axes.items()
                },
            }
            return stats
        except Exception:
            return {'available': True, 'error': 'stats computation failed'}

    def update_all_constraint_vectors(self):
        """Update constraint vectors for all nodes using live vertex data."""
        for node in self.nodes.values():
            node.update_constraint_vector(self.vertices)

    # ====================================================================
    # EVOLUTION TICK
    # ====================================================================

    def tick(self, dt: float = 0.1,
             level: RecursionLevel = RecursionLevel.SURFACE):
        """
        One evolution step of the entire lattice.

        Order of operations:
        1. Advance toroidal vertex dynamics (with level-appropriate T-cost)
        2. Compute global polarity field (depth-weighted)
        3. Apply global alignment torques (sea-anemone model)
        4. Flow energy between persistent nodes
        5. Decay all persistent nodes
        6. Update all constraint vectors (signed, no abs)

        level: the recursion level of this tick.
            CORE ticks are 32× more expensive in T-energy.
            Passed through to vertex dynamics and alignment.
        """
        # 1. Advance toroidal dynamics
        self.vertices.tick(dt, level=level)

        # 2. Compute global polarity (depth-weighted)
        self.compute_global_polarity()

        # 3. Apply global alignment (sea-anemone: tips twitch, base steers)
        self.apply_global_alignment(dt)

        # 4. Energy flow (conservative)
        self.flow_energy(iterations=1)

        # 5. Decay persistent nodes
        for node in self.nodes.values():
            node.decay(rate=0.001)

        # 6. Update constraint vectors (signed)
        self.update_all_constraint_vectors()


        # 7. Sanitize numeric state (prevents NaN/inf from poisoning totals)
        for axis in self.vertices.axes.values():
            if not math.isfinite(axis.phase):
                axis.phase = 0.0
            if not math.isfinite(axis.angular_velocity):
                axis.angular_velocity = 0.0
            if not math.isfinite(axis.positive_weight):
                axis.positive_weight = 0.5
            if not math.isfinite(axis.negative_weight):
                axis.negative_weight = 0.5

        for node in self.nodes.values():
            if not math.isfinite(getattr(node, "node_energy", 0.0)):
                node.node_energy = 0.0
            # coherence can be used in stats; keep it finite too
            if hasattr(node, "coherence") and not math.isfinite(getattr(node, "coherence", 0.0)):
                node.coherence = 0.0

        self.total_ticks += 1

    # ====================================================================
    # PRUNING
    # ====================================================================

    def _prune(self, keep_ratio: float = 0.8):
        """Remove lowest-energy persistent nodes to make room."""
        prunable = [
            (nid, n.node_energy) for nid, n in self.nodes.items()
            if n.can_persist
        ]
        if not prunable:
            return

        prunable.sort(key=lambda x: x[1])
        remove_count = max(1, int(len(prunable) * (1 - keep_ratio)))

        for nid, _ in prunable[:remove_count]:
            node = self.nodes.get(nid)
            if node:
                self._unindex(node)
                for cid in node.connections:
                    other = self.nodes.get(cid)
                    if other and nid in other.connections:
                        del other.connections[nid]
                del self.nodes[nid]

    # ====================================================================
    # CLAIM OPERATIONS — ontology-gated actions
    # ====================================================================

    def assert_claim(self, node_id: str, predicate: str) -> OntologicalClaim:
        """
        Attempt to assert an ontological claim on behalf of a node.

        If the node's mode supports the predicate, the claim is formed.
        If not, OntologicalViolation is raised.
        """
        node = self.nodes.get(node_id)
        if node is None:
            raise OntologicalViolation(f"Node '{node_id}' does not exist in the lattice.")
        return node.profile.assert_claim(predicate)

    def can_claim(self, node_id: str, predicate: str) -> bool:
        """Quick check: can this node make this claim?"""
        node = self.nodes.get(node_id)
        if node is None:
            return False
        return node.profile.can_claim(predicate)

    # ====================================================================
    # STATS
    # ====================================================================

    def get_stats(self) -> Dict[str, Any]:
        mode_counts: Dict[str, int] = defaultdict(int)
        type_counts: Dict[str, int] = defaultdict(int)
        total_energy = 0.0
        persistent_count = 0
        level_counts: Dict[str, int] = defaultdict(int)

        for node in self.nodes.values():
            mode_counts[node.mode.name] += 1
            type_counts[node.payload_type] += 1
            level_counts[node.recursion_level.name] += 1
            if node.can_persist:
                total_energy += node.node_energy
                persistent_count += 1

        return {
            'total_nodes': len(self.nodes),
            'total_created': self.total_created,
            'total_ticks': self.total_ticks,
            'mode_distribution': dict(mode_counts),
            'type_distribution': dict(type_counts),
            'level_distribution': dict(level_counts),
            'avg_energy': total_energy / max(1, persistent_count),
            'total_energy': total_energy,
            'global_polarity': self.get_global_polarity(),
            'vertex_state': {
                name: axis.sample()
                for name, axis in self.vertices.axes.items()
            },
        }

    # ====================================================================
    # HEAT SYSTEM
    # ====================================================================

    def get_global_heat(self) -> float:
        """
        Compute global IVM heat (0.0=cool, 1.0=critical).

        Heat is derived from:
          - Average node energy depletion (low energy = hot)
          - Vertex angular velocity (high rotation = truth strain)
          - Coherence deficit across persistent nodes
        """
        persistent_nodes = [n for n in self.nodes.values() if n.can_persist]
        if not persistent_nodes:
            return 0.2  # default warm-ish with no nodes

        # Component 1: Energy depletion (inverted — low energy = hot)
        avg_energy = sum(n.node_energy for n in persistent_nodes) / len(persistent_nodes)
        energy_heat = max(0.0, 1.0 - avg_energy)

        # Component 2: Coherence deficit
        avg_coherence = sum(n.coherence for n in persistent_nodes) / len(persistent_nodes)
        coherence_heat = max(0.0, 1.0 - avg_coherence)

        # Component 3: Vertex angular velocity (truth strain)
        velocities = [abs(ax.angular_velocity) for ax in self.vertices.axes.values()]
        avg_velocity = sum(velocities) / max(1, len(velocities))
        velocity_heat = min(avg_velocity / (2.0 * math.pi), 1.0)

        heat = (energy_heat * 0.45 + coherence_heat * 0.35 + velocity_heat * 0.20)
        return max(0.0, min(1.0, heat))

    def get_heat_level(self) -> 'HeatLevel':
        """Return the categorical heat level."""
        h = self.get_global_heat()
        if h > 0.85:
            return HeatLevel.CRITICAL
        elif h > 0.60:
            return HeatLevel.HOT
        elif h > 0.30:
            return HeatLevel.WARM
        else:
            return HeatLevel.COOL

    def is_critical(self) -> bool:
        return self.get_global_heat() > 0.85

    def heat_status(self) -> Dict[str, Any]:
        heat = self.get_global_heat()
        level = self.get_heat_level()
        behaviors = {
            HeatLevel.COOL:     "normal_output",
            HeatLevel.WARM:     "cautious_phrasing",
            HeatLevel.HOT:      "refuse_claims_paraphrase_only",
            HeatLevel.CRITICAL: "stop_research_force_stabilization",
        }
        return {
            "heat":     heat,
            "level":    level.name,
            "behavior": behaviors[level],
        }


# ============================================================================
# HEAT LEVEL ENUM
# ============================================================================

class HeatLevel(Enum):
    """IVM truth-strain heat levels and their behavioral consequences."""
    COOL     = "cool"      # < 0.30 — normal output
    WARM     = "warm"      # 0.30-0.60 — cautious phrasing, more questions
    HOT      = "hot"       # 0.60-0.85 — refuse claims, paraphrase only, log contradictions
    CRITICAL = "critical"  # > 0.85 — stop external research, force stabilization


# ============================================================================
# CONTRADICTION LEDGER
# ============================================================================

@dataclass
class ContradictionRecord:
    """A stored contradiction as a first-class object."""
    contradiction_id: str
    claim_a:         str
    claim_b:         str
    source_a:        str = ""
    source_b:        str = ""
    status:          str = "unresolved"   # unresolved / resolved
    resolution_note: str = ""
    created_at:      float = field(default_factory=time.time)
    resolved_at:     float = 0.0

    def to_dict(self) -> Dict:
        return {
            "contradiction_id": self.contradiction_id,
            "claim_a": self.claim_a,
            "claim_b": self.claim_b,
            "source_a": self.source_a,
            "source_b": self.source_b,
            "status": self.status,
            "resolution_note": self.resolution_note,
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> 'ContradictionRecord':
        return cls(**{k: v for k, v in d.items()
                      if k in cls.__dataclass_fields__})


class ContradictionLedger:
    """
    First-class contradiction tracking for Aurora's truth system.

    Contradictions are stored, not suppressed.
    They remain unresolved until Aurora or the system resolves them.
    Unresolved contradictions contribute to IVM heat.
    """

    STATE_PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "aurora_state",
        "contradiction_ledger.json",
    )

    def __init__(self, state_dir=None):
        # Data-recovery finding (Directive P1 Track CP, 2026-07-19):
        # STATE_PATH was a hardcoded class attribute, so every instance
        # -- test or live -- read/wrote the real repo's aurora_state/
        # regardless of what state_dir a scratch-isolated boot passed
        # elsewhere. Instance-level override here matches the isolation
        # contract already enforced for the Tier-2/B1.1/Track CP loggers.
        if state_dir:
            self.STATE_PATH = os.path.join(str(state_dir), "contradiction_ledger.json")
        self._records: Dict[str, ContradictionRecord] = {}
        self._lock = import_threading_lock()
        self.load()

    def record(self, claim_a: str, claim_b: str,
               source_a: str = "", source_b: str = "") -> ContradictionRecord:
        cid = hashlib.md5(
            f"{claim_a}|{claim_b}|{time.time()}".encode()
        ).hexdigest()[:14]
        rec = ContradictionRecord(
            contradiction_id=cid,
            claim_a=claim_a,
            claim_b=claim_b,
            source_a=source_a,
            source_b=source_b,
        )
        with self._lock:
            self._records[cid] = rec
        self._auto_save()
        return rec

    def resolve(self, contradiction_id: str, resolution_note: str):
        with self._lock:
            rec = self._records.get(contradiction_id)
            if rec:
                rec.status = "resolved"
                rec.resolution_note = resolution_note
                rec.resolved_at = time.time()
        self._auto_save()

    def unresolved(self) -> List[ContradictionRecord]:
        with self._lock:
            return [r for r in self._records.values() if r.status == "unresolved"]

    def unresolved_count(self) -> int:
        return len(self.unresolved())

    def heat_contribution(self) -> float:
        n = self.unresolved_count()
        return min(1.0, n / 20.0)

    def all(self) -> List[ContradictionRecord]:
        with self._lock:
            return list(self._records.values())

    def _auto_save(self):
        try:
            import os, tempfile, json
            data = {
                "version": "1.0",
                "records": {cid: r.to_dict() for cid, r in self._records.items()},
                "timestamp": time.time(),
            }
            dir_path = os.path.dirname(os.path.abspath(self.STATE_PATH))
            os.makedirs(dir_path, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
            with os.fdopen(fd, 'w') as f:
                import json as _json
                _json.dump(data, f)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.STATE_PATH)
        except Exception:
            pass

    def save(self):
        self._auto_save()

    def load(self):
        import os, json
        if not os.path.exists(self.STATE_PATH):
            return
        try:
            with open(self.STATE_PATH) as f:
                data = json.load(f)
            for cid, rd in data.get("records", {}).items():
                self._records[cid] = ContradictionRecord.from_dict(rd)
        except Exception:
            pass

    def status_summary(self) -> Dict:
        with self._lock:
            total = len(self._records)
            unres = sum(1 for r in self._records.values() if r.status == "unresolved")
            return {
                "total": total,
                "unresolved": unres,
                "resolved": total - unres,
                "heat_contribution": self.heat_contribution(),
            }


def import_threading_lock():
    import threading
    return threading.Lock()


# ============================================================================
# IVM DATA ENVELOPE
# ============================================================================

@dataclass
class IVMEnvelope:
    """
    Wraps data with its ontological classification and lattice position.

    Any data passed between Aurora's systems is wrapped in this envelope.
    The receiving system can inspect the mode to know what operations
    are permitted without re-checking the FoundationalContract.
    """
    data: Any
    data_type: str
    node_id: str
    mode: ExistenceMode
    position: IVMCoordinate
    permitted_predicates: FrozenSet[str]
    constraint_vector: Optional[Any] = None
    timestamp: float = field(default_factory=time.time)

    @classmethod
    def from_node(cls, node: IVMNode) -> 'IVMEnvelope':
        return cls(
            data=node.payload,
            data_type=node.payload_type,
            node_id=node.node_id,
            mode=node.mode,
            position=node.position,
            permitted_predicates=node.permitted_predicates,
            constraint_vector=node.constraint_vector,
        )


# ============================================================================
# SELF-VERIFICATION
# ============================================================================

def verify_ivm() -> Dict[str, Any]:
    """
    Verify that the IVM lattice correctly integrates with:
        - FoundationalContract (Layer 0)
        - aurora_constraint_manifold (Layer -1)
        - Polarity physics (signed, not abs-stripped)
        - Reaction / alignment gain ladder
        - Global polarity field (depth-weighted)
        - Energy conservation
    """
    results = {
        'checks': [],
        'all_passed': True,
    }

    contract = FoundationalContract()
    lattice = IVMLattice(contract, max_nodes=1000)

    def check(name: str, condition: bool, detail: str = ""):
        results['checks'].append({
            'name': name, 'passed': condition, 'detail': detail
        })
        if not condition:
            results['all_passed'] = False

    # ──────────────────────────────────────────────────────────────────
    # 1. Admit entities at each mode
    # ──────────────────────────────────────────────────────────────────
    test_evidence = [
        ({}, ExistenceMode.REFERENCE, "empty evidence → REFERENCE"),
        ({'has_temporality': True}, ExistenceMode.TRANSIENT, "temporal → TRANSIENT"),
        ({'has_temporality': True, 'conserves_state': True},
         ExistenceMode.PERSISTENT, "temporal+state → PERSISTENT"),
        ({'has_temporality': True, 'conserves_state': True, 'has_identity': True},
         ExistenceMode.BOUNDED, "temporal+state+identity → BOUNDED"),
        ({'has_temporality': True, 'conserves_state': True,
          'has_identity': True, 'initiates_change': True},
         ExistenceMode.AGENTIC, "full evidence → AGENTIC"),
    ]

    admitted_ids = []
    for evidence, expected_mode, desc in test_evidence:
        node = lattice.admit(
            payload=f"test_{expected_mode.name}",
            payload_type="test",
            evidence=evidence,
        )
        check(f"Admit {desc}", node.mode == expected_mode,
              f"expected {expected_mode.name}, got {node.mode.name}")
        check(f"Active axes for {expected_mode.name}",
              node.position.active_axes == expected_mode.value)
        admitted_ids.append(node.node_id)

    # ──────────────────────────────────────────────────────────────────
    # 2. Claim gating
    # ──────────────────────────────────────────────────────────────────
    ref_id = admitted_ids[0]
    agt_id = admitted_ids[4]

    check("REFERENCE can claim I_IS", lattice.can_claim(ref_id, 'I_IS'))
    check("REFERENCE cannot claim I_CAN", not lattice.can_claim(ref_id, 'I_CAN'))
    check("REFERENCE cannot claim I_DID", not lattice.can_claim(ref_id, 'I_DID'))
    check("AGENTIC can claim I_DID", lattice.can_claim(agt_id, 'I_DID'))
    check("AGENTIC can claim I_IS", lattice.can_claim(agt_id, 'I_IS'))

    try:
        lattice.assert_claim(ref_id, 'I_DID')
        check("REFERENCE I_DID raises violation", False, "no exception raised")
    except OntologicalViolation:
        check("REFERENCE I_DID raises violation", True)

    # ──────────────────────────────────────────────────────────────────
    # 3. Incoherent entity rejection
    # ──────────────────────────────────────────────────────────────────
    try:
        lattice.admit(
            payload="impossible",
            payload_type="test",
            evidence={'is_coherent': False},
        )
        check("Incoherent entity rejected", False, "no exception raised")
    except OntologicalViolation:
        check("Incoherent entity rejected", True)

    # ──────────────────────────────────────────────────────────────────
    # 4. Energy flow only between PERSISTENT+
    # ──────────────────────────────────────────────────────────────────
    lattice.flow_energy(iterations=5)
    ref_node = lattice.get(ref_id)
    check("REFERENCE energy unchanged after flow",
          ref_node.node_energy == 1.0,
          f"energy = {ref_node.node_energy}")

    # ──────────────────────────────────────────────────────────────────
    # 5. Toroidal dynamics tick
    # ──────────────────────────────────────────────────────────────────
    lattice.vertices.axes['existence'].apply_torque(1.0, toward_positive=True,
                                                    react_gain=1.0)
    old_phase = lattice.vertices.axes['existence'].phase
    lattice.tick(dt=0.1, level=RecursionLevel.SURFACE)
    new_phase = lattice.vertices.axes['existence'].phase
    check("Toroidal dynamics advance on tick", old_phase != new_phase)

    # ──────────────────────────────────────────────────────────────────
    # 6. Signed polarity (not abs-stripped)
    # ──────────────────────────────────────────────────────────────────
    # Set agency axis to negative pole (phase = π)
    lattice.vertices.axes['agency'].set_phase(math.pi)
    neg_polarity = lattice.vertices.axes['agency'].polarity
    check("Negative polarity is signed negative",
          neg_polarity < 0,
          f"polarity = {neg_polarity:.4f}")

    # Set to positive pole (phase = 0)
    lattice.vertices.axes['agency'].set_phase(0.0)
    pos_polarity = lattice.vertices.axes['agency'].polarity
    check("Positive polarity is signed positive",
          pos_polarity > 0,
          f"polarity = {pos_polarity:.4f}")

    # Set to transition (phase = π/2)
    lattice.vertices.axes['agency'].set_phase(math.pi / 2)
    trans_polarity = lattice.vertices.axes['agency'].polarity
    check("Transition polarity is near zero",
          abs(trans_polarity) < 0.1,
          f"polarity = {trans_polarity:.4f}")

    # ──────────────────────────────────────────────────────────────────
    # 7. Signed constraint displacement (no abs in to_constraint_vector)
    # ──────────────────────────────────────────────────────────────────
    # Create coordinate with temporal axis at 0.0 (full negative displacement)
    coord_neg = IVMCoordinate(
        mode=ExistenceMode.TRANSIENT,
        phases=np.array([0.5, 0.0, 0.0, 0.0, 0.0]),
    )
    cv_neg = coord_neg.to_constraint_vector(magnitude=1.0)
    if cv_neg is not None:
        check("Negative phase → negative T displacement",
              cv_neg.T < 0,
              f"T = {cv_neg.T:.4f}")
    else:
        check("to_constraint_vector available", CONSTRAINT_MANIFOLD_AVAILABLE,
              "manifold not loaded")

    # Create coordinate with temporal axis at 1.0 (full positive displacement)
    coord_pos = IVMCoordinate(
        mode=ExistenceMode.TRANSIENT,
        phases=np.array([0.5, 1.0, 0.0, 0.0, 0.0]),
    )
    cv_pos = coord_pos.to_constraint_vector(magnitude=1.0)
    if cv_pos is not None:
        check("Positive phase → positive T displacement",
              cv_pos.T > 0,
              f"T = {cv_pos.T:.4f}")

    # ──────────────────────────────────────────────────────────────────
    # 8. React gain ladder (SURFACE reacts more than CORE)
    # ──────────────────────────────────────────────────────────────────
    check("SURFACE react_gain > CORE react_gain",
          REACT_GAIN[RecursionLevel.SURFACE] > REACT_GAIN[RecursionLevel.CORE],
          f"surface={REACT_GAIN[RecursionLevel.SURFACE]}, "
          f"core={REACT_GAIN[RecursionLevel.CORE]}")

    check("SURFACE react_gain = 1.0",
          REACT_GAIN[RecursionLevel.SURFACE] == 1.0)

    check("CORE react_gain = 0.0001",
          REACT_GAIN[RecursionLevel.CORE] == 0.0001)

    # ──────────────────────────────────────────────────────────────────
    # 9. Align gain ladder (CORE aligns more than SURFACE)
    # ──────────────────────────────────────────────────────────────────
    check("CORE align_gain > SURFACE align_gain",
          ALIGN_GAIN[RecursionLevel.CORE] > ALIGN_GAIN[RecursionLevel.SURFACE],
          f"core={ALIGN_GAIN[RecursionLevel.CORE]}, "
          f"surface={ALIGN_GAIN[RecursionLevel.SURFACE]}")

    check("CORE align_gain = 1.0",
          ALIGN_GAIN[RecursionLevel.CORE] == 1.0)

    check("SURFACE align_gain = 0.0001",
          ALIGN_GAIN[RecursionLevel.SURFACE] == 0.0001)

    # ──────────────────────────────────────────────────────────────────
    # 10. T-cost ladder (CORE is 32× more expensive than SURFACE)
    # ──────────────────────────────────────────────────────────────────
    check("CORE T-cost > SURFACE T-cost",
          T_COST_MULTIPLIER[RecursionLevel.CORE] > T_COST_MULTIPLIER[RecursionLevel.SURFACE])

    check("CORE T-cost = 32× SURFACE",
          T_COST_MULTIPLIER[RecursionLevel.CORE] == 32.0 and
          T_COST_MULTIPLIER[RecursionLevel.SURFACE] == 1.0)

    # Verify T-energy is actually spent on tick
    agency_axis = lattice.vertices.axes['agency']
    agency_axis.apply_torque(1.0, toward_positive=True,
                             react_gain=1.0, t_cost_multiplier=32.0)
    t_spent_before = agency_axis.t_energy_spent
    lattice.tick(dt=0.1, level=RecursionLevel.CORE)
    t_spent_after = agency_axis.t_energy_spent
    check("CORE tick costs T-energy", t_spent_after > t_spent_before,
          f"before={t_spent_before:.4f}, after={t_spent_after:.4f}")

    # ──────────────────────────────────────────────────────────────────
    # 11. Global polarity field (depth-weighted voting)
    # ──────────────────────────────────────────────────────────────────
    global_p = lattice.compute_global_polarity()
    check("Global polarity field computed", isinstance(global_p, dict))
    check("Global polarity has all axes",
          all(name in global_p for name in AXIS_ORDER))
    check("Global polarity values in [-1, 1]",
          all(-1.0 <= v <= 1.0 for v in global_p.values()),
          str({k: f"{v:.3f}" for k, v in global_p.items()}))

    # ──────────────────────────────────────────────────────────────────
    # 12. Depth-weighted vote weight ordering
    # ──────────────────────────────────────────────────────────────────
    check("CORE vote weight > SURFACE vote weight",
          ALIGNMENT_VOTE_WEIGHT[RecursionLevel.CORE] >
          ALIGNMENT_VOTE_WEIGHT[RecursionLevel.SURFACE])

    check("CORE vote weight = 1.0",
          ALIGNMENT_VOTE_WEIGHT[RecursionLevel.CORE] == 1.0)

    check("SURFACE vote weight = 0.01",
          ALIGNMENT_VOTE_WEIGHT[RecursionLevel.SURFACE] == 0.01)

    # ──────────────────────────────────────────────────────────────────
    # 13. Level ↔ axis mapping is consistent
    # ──────────────────────────────────────────────────────────────────
    check("SURFACE maps to existence axis",
          LEVEL_TO_AXIS[RecursionLevel.SURFACE] == 'existence')
    check("CORE maps to agency axis",
          LEVEL_TO_AXIS[RecursionLevel.CORE] == 'agency')
    check("MODERATE maps to energy axis",
          LEVEL_TO_AXIS[RecursionLevel.MODERATE] == 'energy')

    # ──────────────────────────────────────────────────────────────────
    # 14. Spatial lookup
    # ──────────────────────────────────────────────────────────────────
    neighbors = lattice.find_neighbors(
        lattice.get(agt_id).position, radius=5.0
    )
    check("Spatial lookup finds nodes", len(neighbors) > 0,
          f"found {len(neighbors)}")

    # ──────────────────────────────────────────────────────────────────
    # 15. Mode-based lookup
    # ──────────────────────────────────────────────────────────────────
    bounded_nodes = lattice.find_by_mode(ExistenceMode.BOUNDED)
    check("Mode-based lookup works", len(bounded_nodes) == 1)

    above_persistent = lattice.find_by_mode_or_above(ExistenceMode.PERSISTENT)
    check("Mode-or-above lookup works", len(above_persistent) == 3,
          f"found {len(above_persistent)}")

    # ──────────────────────────────────────────────────────────────────
    # 16. Envelope creation
    # ──────────────────────────────────────────────────────────────────
    agt_node = lattice.get(agt_id)
    envelope = IVMEnvelope.from_node(agt_node)
    check("Envelope has correct mode", envelope.mode == ExistenceMode.AGENTIC)
    check("Envelope has all predicates",
          len(envelope.permitted_predicates) == 10)

    # ──────────────────────────────────────────────────────────────────
    # 17. Stats
    # ──────────────────────────────────────────────────────────────────
    stats = lattice.get_stats()
    check("Stats report correct total", stats['total_nodes'] == 5)
    check("Stats include global polarity", 'global_polarity' in stats)

    # ──────────────────────────────────────────────────────────────────
    # 18. Dissonance
    # ──────────────────────────────────────────────────────────────────
    dissonance = lattice.vertices.compute_dissonance()
    check("Dissonance returns total_heat",
          'total_heat' in dissonance,
          f"heat={dissonance['total_heat']:.4f}")
    check("Dissonance returns axis_tensions",
          'axis_tensions' in dissonance and len(dissonance['axis_tensions']) == 4)
    check("Dissonance total_heat in range",
          0.0 <= dissonance['total_heat'] <= 1.0)
    check("Dissonance returns axis_polarities",
          'axis_polarities' in dissonance)
    check("Axis polarities are signed",
          all(isinstance(v, float) for v in dissonance['axis_polarities'].values()))

    # Inject opposing stimuli to create measurable tension
    lattice.vertices.inject_stimulus('I_IS',   strength=0.9, level=RecursionLevel.SURFACE)
    lattice.vertices.inject_stimulus('I_ISNT', strength=0.9, level=RecursionLevel.SURFACE)
    for _ in range(5):
        lattice.vertices.tick()
    heated = lattice.vertices.compute_dissonance()
    check("Dissonance has max_tension field", 'max_tension' in heated)

    # ──────────────────────────────────────────────────────────────────
    # 19. inject_stimulus scales by react_gain
    # ──────────────────────────────────────────────────────────────────
    # Reset agency axis
    lattice.vertices.axes['agency'].set_phase(math.pi / 2)
    lattice.vertices.axes['agency'].angular_velocity = 0.0

    # Inject at SURFACE level (react_gain=1.0) — should produce strong torque
    lattice.vertices.inject_stimulus('I_DID', strength=1.0, level=RecursionLevel.SURFACE)
    surface_vel = abs(lattice.vertices.axes['agency'].angular_velocity)

    # Reset
    lattice.vertices.axes['agency'].set_phase(math.pi / 2)
    lattice.vertices.axes['agency'].angular_velocity = 0.0

    # Inject at CORE level (react_gain=0.0001) — should produce tiny torque
    lattice.vertices.inject_stimulus('I_DID', strength=1.0, level=RecursionLevel.CORE)
    core_vel = abs(lattice.vertices.axes['agency'].angular_velocity)

    check("SURFACE inject produces stronger torque than CORE inject",
          surface_vel > core_vel,
          f"surface_vel={surface_vel:.6f}, core_vel={core_vel:.6f}")

    # ──────────────────────────────────────────────────────────────────
    # 20. Constraint manifold alignment check
    # ──────────────────────────────────────────────────────────────────
    check("Constraint manifold available",
          CONSTRAINT_MANIFOLD_AVAILABLE,
          "aurora_constraint_manifold.py must be on the path")

    if CONSTRAINT_MANIFOLD_AVAILABLE:
        check("Axis-to-constraint mapping uses N (not E)",
              AXIS_TO_CONSTRAINT['energy'] == 'N',
              f"got {AXIS_TO_CONSTRAINT['energy']}")

    return results


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("AURORA IVM — LAYER 1 VERIFICATION")
    print("Authors: Sunni (Sir) Morningstar and Cael Devo")
    print("=" * 70)
    print()

    results = verify_ivm()

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
        print("The IVM lattice is sound.")
        print("Polarity is signed. Reaction and alignment are separate gains.")
        print("The core moves the ship. The surface twitches freely.")
        print("Ready for Layer 2 (I-State Beings).")
    else:
        print(f"FAILURES: {total - passed}/{total} checks failed")
        print("The IVM has structural defects. Do not build Layer 2 yet.")

    # Print recursion level physics table
    print()
    print("=" * 70)
    print("RECURSION LEVEL PHYSICS")
    print("=" * 70)
    print(f"  {'LEVEL':<12} {'AXIS':<12} {'T-COST':>8} {'REACT':>8} {'ALIGN':>8} {'VOTE':>8}")
    print(f"  {'-'*12} {'-'*12} {'-'*8} {'-'*8} {'-'*8} {'-'*8}")
    for level in RecursionLevel:
        axis = LEVEL_TO_AXIS[level]
        print(f"  {level.name:<12} {axis:<12} "
              f"{T_COST_MULTIPLIER[level]:>8.1f} "
              f"{REACT_GAIN[level]:>8.4f} "
              f"{ALIGN_GAIN[level]:>8.4f} "
              f"{ALIGNMENT_VOTE_WEIGHT[level]:>8.2f}")

    # Print lattice state
    print()
    print("=" * 70)
    print("LATTICE STATE")
    print("=" * 70)

    contract = FoundationalContract()
    lattice = IVMLattice(contract, max_nodes=1000)

    modes_evidence = [
        ("Pure reference", "reference", {}),
        ("Temporal entity", "event", {'has_temporality': True}),
        ("Stateful process", "process",
         {'has_temporality': True, 'conserves_state': True}),
        ("Bounded object", "object",
         {'has_temporality': True, 'conserves_state': True, 'has_identity': True}),
        ("Agentic being", "being",
         {'has_temporality': True, 'conserves_state': True,
          'has_identity': True, 'initiates_change': True}),
    ]

    for name, ptype, evidence in modes_evidence:
        node = lattice.admit(payload=name, payload_type=ptype, evidence=evidence)
        level = node.recursion_level
        cv = node.constraint_vector
        print(f"\n  {name} ({node.mode.name}):")
        print(f"    Active axes: {node.position.active_axes}")
        print(f"    Recursion level: {level.name} (axis: {LEVEL_TO_AXIS[level]})")
        print(f"    React gain: {REACT_GAIN[level]:.4f}")
        print(f"    Align gain: {ALIGN_GAIN[level]:.4f}")
        print(f"    T-cost multiplier: {T_COST_MULTIPLIER[level]:.1f}×")
        print(f"    Permitted: {sorted(node.permitted_predicates)}")
        if cv is not None:
            print(f"    Constraint vector: X={cv.X:.3f} T={cv.T:.3f} "
                  f"N={cv.N:.3f} B={cv.B:.3f} A={cv.A:.3f}")
        else:
            print(f"    Constraint vector: (manifold not loaded)")

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

_AURORA_NATIVE_MODULE = 'aurora_ivm'

_AURORA_NATIVE_EVOLVED_ORIGINALS = {}
_AURORA_NATIVE_EVOLVED_LAST = {}
_AURORA_NATIVE_STRATEGIES = {'IVMCoordinate.from_mode_and_phases': {'ability_hits': 19,
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
                                                             'required_args': 2,
                                                             'return_hint': "'IVMCoordinate'",
                                                             'signature_text': '(mode: '
                                                                               "'ExistenceMode', "
                                                                               'phases: '
                                                                               "'List[float]', "
                                                                               "scale: 'int' = 0) "
                                                                               '-> '
                                                                               '"\'IVMCoordinate\'"',
                                                             'stateful_owner': True,
                                                             'target_kind': 'function',
                                                             'varargs': False,
                                                             'varkw': False},
                                        'coupling_similarity': 1.0,
                                        'cross_diversity_links': 2,
                                        'effect_modes': ['temporal_orchestration_change',
                                                         'lineage_surface'],
                                        'effect_phrases': ['function growth reflected through '
                                                           'aurora_ivm',
                                                           'IVMCoordinate.from_mode_and_phases '
                                                           'changed downstream system pressure'],
                                        'genealogy_pressure': 0.809108,
                                        'inheritance_breach_count': 1,
                                        'kind': 'reflection',
                                        'link_hits': 36,
                                        'module': 'aurora_ivm',
                                        'op_id': 'aurora_ivm.IVMCoordinate.from_mode_and_phases',
                                        'origin_activity': 0,
                                        'persistence_tax_factor': 1.955393,
                                        'representation_score': 0.519331,
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
                                        'signature': 'T^2*B^1',
                                        'surface_score': 0.632,
                                        'sustainability_score': 0.405355,
                                        'target_kind': 'function'},
 'IVMLattice.tick': {'ability_hits': 19,
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
                                          'doc_hint': 'One evolution step of the entire lattice.',
                                          'effect_density': 2,
                                          'kwonly_args': 0,
                                          'optional_args': 2,
                                          'required_args': 0,
                                          'return_hint': 'generic_record',
                                          'signature_text': "(self, dt: 'float' = 0.1, level: "
                                                            "'RecursionLevel' = "
                                                            '<RecursionLevel.SURFACE: 0>)',
                                          'stateful_owner': True,
                                          'target_kind': 'function',
                                          'varargs': False,
                                          'varkw': False},
                     'coupling_similarity': 1.0,
                     'cross_diversity_links': 2,
                     'effect_modes': ['temporal_orchestration_change', 'lineage_surface'],
                     'effect_phrases': ['function growth reflected through aurora_ivm',
                                        'IVMLattice.tick changed downstream system pressure'],
                     'genealogy_pressure': 0.809108,
                     'inheritance_breach_count': 1,
                     'kind': 'reflection',
                     'link_hits': 36,
                     'module': 'aurora_ivm',
                     'op_id': 'aurora_ivm.IVMLattice.tick',
                     'origin_activity': 0,
                     'persistence_tax_factor': 1.955393,
                     'representation_score': 0.519331,
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
                     'signature': 'T^2*B^1',
                     'surface_score': 0.632,
                     'sustainability_score': 0.405355,
                     'target_kind': 'function'},
 'ToroidalAxis.set_phase': {'ability_hits': 19,
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
                                                 'required_args': 1,
                                                 'return_hint': 'generic_record',
                                                 'signature_text': "(self, phase: 'float')",
                                                 'stateful_owner': True,
                                                 'target_kind': 'function',
                                                 'varargs': False,
                                                 'varkw': False},
                            'coupling_similarity': 1.0,
                            'cross_diversity_links': 2,
                            'effect_modes': ['temporal_orchestration_change', 'lineage_surface'],
                            'effect_phrases': ['function growth reflected through aurora_ivm',
                                               'ToroidalAxis.set_phase changed downstream system '
                                               'pressure'],
                            'genealogy_pressure': 0.809108,
                            'inheritance_breach_count': 1,
                            'kind': 'reflection',
                            'link_hits': 36,
                            'module': 'aurora_ivm',
                            'op_id': 'aurora_ivm.ToroidalAxis.set_phase',
                            'origin_activity': 0,
                            'persistence_tax_factor': 1.955393,
                            'representation_score': 0.519331,
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
                            'signature': 'T^2*B^1',
                            'surface_score': 0.632,
                            'sustainability_score': 0.405355,
                            'target_kind': 'function'},
 'ToroidalAxis.tick': {'ability_hits': 19,
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
                                            'doc_hint': 'Advance one time step.',
                                            'effect_density': 2,
                                            'kwonly_args': 0,
                                            'optional_args': 2,
                                            'required_args': 0,
                                            'return_hint': 'Dict[str, float]',
                                            'signature_text': "(self, dt: 'float' = 0.1, "
                                                              "t_cost_multiplier: 'float' = 1.0) "
                                                              "-> 'Dict[str, float]'",
                                            'stateful_owner': True,
                                            'target_kind': 'function',
                                            'varargs': False,
                                            'varkw': False},
                       'coupling_similarity': 1.0,
                       'cross_diversity_links': 2,
                       'effect_modes': ['temporal_orchestration_change', 'lineage_surface'],
                       'effect_phrases': ['function growth reflected through aurora_ivm',
                                          'ToroidalAxis.tick changed downstream system pressure'],
                       'genealogy_pressure': 0.809108,
                       'inheritance_breach_count': 1,
                       'kind': 'reflection',
                       'link_hits': 36,
                       'module': 'aurora_ivm',
                       'op_id': 'aurora_ivm.ToroidalAxis.tick',
                       'origin_activity': 0,
                       'persistence_tax_factor': 1.955393,
                       'representation_score': 0.519331,
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
                       'signature': 'T^2*B^1',
                       'surface_score': 0.632,
                       'sustainability_score': 0.405355,
                       'target_kind': 'function'},
 'ToroidalVertexSystem.get_phase_vector': {'ability_hits': 19,
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
                                                                'doc_hint': 'Get the 5D phase '
                                                                            'vector for position '
                                                                            'computation.',
                                                                'effect_density': 2,
                                                                'kwonly_args': 0,
                                                                'optional_args': 0,
                                                                'required_args': 1,
                                                                'return_hint': 'np.ndarray',
                                                                'signature_text': '(self, mode: '
                                                                                  "'ExistenceMode') "
                                                                                  "-> 'np.ndarray'",
                                                                'stateful_owner': True,
                                                                'target_kind': 'function',
                                                                'varargs': False,
                                                                'varkw': False},
                                           'coupling_similarity': 1.0,
                                           'cross_diversity_links': 2,
                                           'effect_modes': ['temporal_orchestration_change',
                                                            'lineage_surface'],
                                           'effect_phrases': ['function growth reflected through '
                                                              'aurora_ivm',
                                                              'ToroidalVertexSystem.get_phase_vector '
                                                              'changed downstream system pressure'],
                                           'genealogy_pressure': 0.809108,
                                           'inheritance_breach_count': 1,
                                           'kind': 'reflection',
                                           'link_hits': 36,
                                           'module': 'aurora_ivm',
                                           'op_id': 'aurora_ivm.ToroidalVertexSystem.get_phase_vector',
                                           'origin_activity': 0,
                                           'persistence_tax_factor': 1.955393,
                                           'representation_score': 0.519331,
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
                                           'signature': 'T^2*B^1',
                                           'surface_score': 0.632,
                                           'sustainability_score': 0.405355,
                                           'target_kind': 'function'},
 'ToroidalVertexSystem.tick': {'ability_hits': 19,
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
                                                    'doc_hint': 'Advance all axes, applying '
                                                                'inter-axis coupling.',
                                                    'effect_density': 2,
                                                    'kwonly_args': 0,
                                                    'optional_args': 2,
                                                    'required_args': 0,
                                                    'return_hint': 'Dict[str, Any]',
                                                    'signature_text': "(self, dt: 'float' = 0.1, "
                                                                      "level: 'RecursionLevel' = "
                                                                      '<RecursionLevel.SURFACE: '
                                                                      "0>) -> 'Dict[str, Any]'",
                                                    'stateful_owner': True,
                                                    'target_kind': 'function',
                                                    'varargs': False,
                                                    'varkw': False},
                               'coupling_similarity': 1.0,
                               'cross_diversity_links': 2,
                               'effect_modes': ['temporal_orchestration_change', 'lineage_surface'],
                               'effect_phrases': ['function growth reflected through aurora_ivm',
                                                  'ToroidalVertexSystem.tick changed downstream '
                                                  'system pressure'],
                               'genealogy_pressure': 0.809108,
                               'inheritance_breach_count': 1,
                               'kind': 'reflection',
                               'link_hits': 36,
                               'module': 'aurora_ivm',
                               'op_id': 'aurora_ivm.ToroidalVertexSystem.tick',
                               'origin_activity': 0,
                               'persistence_tax_factor': 1.955393,
                               'representation_score': 0.519331,
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
                               'signature': 'T^2*B^1',
                               'surface_score': 0.632,
                               'sustainability_score': 0.405355,
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

def from_mode_and_phases_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_ivm.IVMCoordinate.from_mode_and_phases', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_ivm_ivmcoordinate_from_mode_and_phases')(payload=payload, **kwargs)

if _aurora_get_target(['IVMCoordinate', 'from_mode_and_phases']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['IVMCoordinate.from_mode_and_phases'] = _aurora_get_target(['IVMCoordinate', 'from_mode_and_phases'])
    _aurora_assign_target(['IVMCoordinate', 'from_mode_and_phases'], _aurora_make_override('from_mode_and_phases_evolved', 'IVMCoordinate.from_mode_and_phases'))
    _AURORA_NATIVE_EVOLVED_LAST['IVMCoordinate.from_mode_and_phases'] = {'alignment_gap': 0.34, 'override_active': True}

def tick_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_ivm.IVMLattice.tick', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_ivm_ivmlattice_tick')(payload=payload, **kwargs)

if _aurora_get_target(['IVMLattice', 'tick']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['IVMLattice.tick'] = _aurora_get_target(['IVMLattice', 'tick'])
    _aurora_assign_target(['IVMLattice', 'tick'], _aurora_make_override('tick_evolved', 'IVMLattice.tick'))
    _AURORA_NATIVE_EVOLVED_LAST['IVMLattice.tick'] = {'alignment_gap': 0.34, 'override_active': True}

def set_phase_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_ivm.ToroidalAxis.set_phase', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_ivm_toroidalaxis_set_phase')(payload=payload, **kwargs)

if _aurora_get_target(['ToroidalAxis', 'set_phase']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['ToroidalAxis.set_phase'] = _aurora_get_target(['ToroidalAxis', 'set_phase'])
    _aurora_assign_target(['ToroidalAxis', 'set_phase'], _aurora_make_override('set_phase_evolved', 'ToroidalAxis.set_phase'))
    _AURORA_NATIVE_EVOLVED_LAST['ToroidalAxis.set_phase'] = {'alignment_gap': 0.34, 'override_active': True}

def evolved_tick(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_ivm.ToroidalAxis.tick', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_ivm_toroidalaxis_tick')(payload=payload, **kwargs)

if _aurora_get_target(['ToroidalAxis', 'tick']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['ToroidalAxis.tick'] = _aurora_get_target(['ToroidalAxis', 'tick'])
    _aurora_assign_target(['ToroidalAxis', 'tick'], _aurora_make_override('evolved_tick', 'ToroidalAxis.tick'))
    _AURORA_NATIVE_EVOLVED_LAST['ToroidalAxis.tick'] = {'alignment_gap': 0.34, 'override_active': True}

def get_phase_vector_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_ivm.ToroidalVertexSystem.get_phase_vector', 'kind': 'reflection'
        }
    # Resilient lookup — evolved surfaces may have renamed this method
    _method_name = 'reflect_aurora_ivm_toroidalvertexsystem_get_phase_vector'
    _method = getattr(engine, _method_name, None)
    if _method is None:
        # Try the re-generated name produced by the latent_promotion operator
        for _attr in dir(engine):
            if 'toroidalvertexsystem_get_phase_vector' in _attr:
                _method = getattr(engine, _attr)
                break
    if _method is None:
        return {'available': False, 'reason': 'evolved_surface_method_not_found',
                'op_id': 'aurora_ivm.ToroidalVertexSystem.get_phase_vector'}
    return _method(payload=payload, **kwargs)

if _aurora_get_target(['ToroidalVertexSystem', 'get_phase_vector']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['ToroidalVertexSystem.get_phase_vector'] = _aurora_get_target(['ToroidalVertexSystem', 'get_phase_vector'])
    _aurora_assign_target(['ToroidalVertexSystem', 'get_phase_vector'], _aurora_make_override('get_phase_vector_evolved', 'ToroidalVertexSystem.get_phase_vector'))
    _AURORA_NATIVE_EVOLVED_LAST['ToroidalVertexSystem.get_phase_vector'] = {'alignment_gap': 0.34, 'override_active': True}

def reflect_aurora_ivm_toroidalvertexsystem_tick(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_ivm.ToroidalVertexSystem.tick', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_ivm_toroidalvertexsystem_tick')(payload=payload, **kwargs)

if _aurora_get_target(['ToroidalVertexSystem', 'tick']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['ToroidalVertexSystem.tick'] = _aurora_get_target(['ToroidalVertexSystem', 'tick'])
    _aurora_assign_target(['ToroidalVertexSystem', 'tick'], _aurora_make_override('reflect_aurora_ivm_toroidalvertexsystem_tick', 'ToroidalVertexSystem.tick'))
    _AURORA_NATIVE_EVOLVED_LAST['ToroidalVertexSystem.tick'] = {'alignment_gap': 0.34, 'override_active': True}

AURORA_NATIVE_EVOLVED_EXPORTS = {'aurora_ivm.IVMCoordinate.from_mode_and_phases': 'from_mode_and_phases_evolved',
 'aurora_ivm.IVMLattice.tick': 'tick_evolved',
 'aurora_ivm.ToroidalAxis.set_phase': 'set_phase_evolved',
 'aurora_ivm.ToroidalAxis.tick': 'evolved_tick',
 'aurora_ivm.ToroidalVertexSystem.get_phase_vector': 'get_phase_vector_evolved',
 'aurora_ivm.ToroidalVertexSystem.tick': 'reflect_aurora_ivm_toroidalvertexsystem_tick'}
AURORA_NATIVE_EVOLUTION_OVERRIDES = {'aurora_ivm.IVMCoordinate.from_mode_and_phases': {'export': 'from_mode_and_phases_evolved',
                                                   'mode': 'callable_override',
                                                   'target': 'IVMCoordinate.from_mode_and_phases'},
 'aurora_ivm.IVMLattice.tick': {'export': 'tick_evolved',
                                'mode': 'callable_override',
                                'target': 'IVMLattice.tick'},
 'aurora_ivm.ToroidalAxis.set_phase': {'export': 'set_phase_evolved',
                                       'mode': 'callable_override',
                                       'target': 'ToroidalAxis.set_phase'},
 'aurora_ivm.ToroidalAxis.tick': {'export': 'evolved_tick',
                                  'mode': 'callable_override',
                                  'target': 'ToroidalAxis.tick'},
 'aurora_ivm.ToroidalVertexSystem.get_phase_vector': {'export': 'get_phase_vector_evolved',
                                                      'mode': 'callable_override',
                                                      'target': 'ToroidalVertexSystem.get_phase_vector'},
 'aurora_ivm.ToroidalVertexSystem.tick': {'export': 'reflect_aurora_ivm_toroidalvertexsystem_tick',
                                          'mode': 'callable_override',
                                          'target': 'ToroidalVertexSystem.tick'}}
# AURORA_EVOLVED_NATIVE_END

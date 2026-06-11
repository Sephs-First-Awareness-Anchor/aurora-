#!/usr/bin/env python3
"""
AURORA NON-COMP REGISTRY — THE CANONICAL SUBSTRATE
=====================================================

Layer -0.5  (sits above the Constraint Manifold, below the Foundational Contract)

This is the ONLY place where hard numbers exist.

Everything else in Aurora must be expressible as derived from these 25 values.
Behaviors, personalities, evolutionary patterns, conscious steering — none of
that is defined here. It emerges from the physics these 25 Non-Comps define.

PHYSICS LAW ALIGNMENT NOTE (AURORA_COGNITIVE_PHYSICS.md §2):
-------------------------------------------------------------
This module contains the 25 ATOMIC CHANNELS (5 axes × 5 representational dimensions).
In the physics document vocabulary, these are "atomic channels" — NOT the 125 noncomps.

The physics document defines three distinct structures:
  25  atomic channels     — 5 axes × 5 NonCompDimensions  ← THIS IS WHAT THIS MODULE HAS
  625 interaction slots   — 25 × 25 pairwise relationships (not yet implemented)
  125 constraint combinations (noncomps) — 5³ axis intersections (not yet implemented)

The full Identity field requires: 125 noncomps × 625 slots = 78,125 slots.
The module name "Non-Comp Registry" refers to the NonCompDimension structure (POLARITY,
MAGNITUDE, OPERATOR, COST, DIFFERENCE), not the 125 noncomp combinations. The naming
predates the physics document. Do not confuse these 25 entries with the 125 noncomps.

THE 25 ATOMIC CHANNELS: 5 Constraints × 5 Representational Dimensions
----------------------------------------------------------------------
Each of the five constraints is represented across exactly five dimensions:

    NC[C][POLARITY]    — Toroidal phase state (continuous gradient, NOT binary)
    NC[C][MAGNITUDE]   — Intensity/activation; costs energy proportionally to shift
    NC[C][OPERATOR]    — The invariant rule governing how this constraint transforms
    NC[C][COST]        — The layer-differentiated energy law (cheapest to most expensive)
    NC[C][DIFFERENCE]  — Δ channel: deviation of this constraint from its reference
                         point. The fifth lens. Computed from a per-constraint Δ rule
                         normalized to the same magnitude scale as the other four.

These are not behaviors. They are physics.

COST HIERARCHY (Sunni's Law):
    kX (existence, cheapest) < kT (time) < kN (energy, neutral) < kB (boundary) < kA (agency, most expensive)

    Existence is cheap because it is reference state — the carrier of representation.
    Agency is expensive because it is directed control — the most complex operation.
    Energy (N) is the neutral mediator — the accounting layer between overhead and leverage.

SIGNED LEVERAGE SCALAR:
    Net Leverage = (B_magnitude + A_magnitude) − (X_magnitude + T_magnitude)
    N is the zero-point (neutral). System seeks a viable band, not maximum positive.

    Negative → overhead dominant (maintenance bleed → drift toward decay)
    Near zero → balanced metabolism
    Positive → leverage investment (structure/control gain)

OPERATOR PRIMITIVES (I-State pairs per constraint):
    X (Existence)  → is   / isn't   (admissibility gate)
    T (Time)       → can  / can't   (continuation gate)
    N (Energy)     → do   / don't   (exchange gate)
    B (Boundary)   → saw  / saunt   (topology gate)
    A (Agency)     → did  / didn't  (authorship gate)

AUTHORS: Sunni (Sir) Morningstar and Cael Devo
CREATED: February 2026
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, NamedTuple, Optional, Tuple

# ---------------------------------------------------------------------------
# AURORA STACK IMPORTS — exact names from existing modules
# ---------------------------------------------------------------------------

from aurora_internal.aurora_constraint_manifold_patched import (
    Constraint,
    ConstraintVector,
    ManifoldViolation,
    RecursionLevel,
)
from aurora_ivm import (
    ALIGNMENT_VOTE_WEIGHT,
    REACT_GAIN,
    ALIGN_GAIN,
    LEVEL_TO_AXIS,
)


# ===========================================================================
# SECTION 1 — REPRESENTATIONAL DIMENSION ENUM
# ===========================================================================

class NonCompDimension(IntEnum):
    """
    The five representational dimensions of every Non-Comp.

    Every constraint is described across exactly these five axes.
    Together they form the 25 Non-Comps (5 × 5 = 25).

    The first four (POLARITY, MAGNITUDE, OPERATOR, COST) are the original
    physics substrate. DIFFERENCE is the fifth lens — a normalized Δ value
    expressing how each constraint deviates from its reference point.

    Reference type is per-constraint (prior_self / peer_mean / background)
    because the semantic meaning of 'difference' is not uniform across
    the constraint stack. See DifferenceParams for per-constraint rules.
    """
    POLARITY   = 0   # Toroidal phase gradient — direction of activation
    MAGNITUDE  = 1   # Intensity — how strongly the constraint is active
    OPERATOR   = 2   # Invariant transformation rule
    COST       = 3   # Energy law — what it costs to exist and to shift
    DIFFERENCE = 4   # Δ channel — deviation from reference; the fifth lens


# ===========================================================================
# SECTION 1b — UNIFIED FIELD CANONICAL CONSTANTS
# (Derived from AURORA_UNIFIED_FIELD_SPEC.md — 2026-03-16)
# Canonical representations of the five field operators and their derived
# semantic, lineage, magnitude, and impact relationships.
# These are read-only constants — do not modify at runtime.
# ===========================================================================

# Semantic polarity map per constraint axis.
# Maps axis letter → (positive_pole, negative_pole, human_semantic, i_state_pair)
SEMANTIC_POLARITY_MAP: Dict[str, Tuple[str, str, str, str]] = {
    "X": ("Admissible",  "Inadmissible", "Yes / No",             "IS / ISNT"),
    "T": ("Propagating", "Stalled",      "Maybe / Maybe not",    "CAN / CANT"),
    "N": ("Sufficient",  "Insufficient", "Enough / Not enough",  "DO / DONT"),
    "B": ("Contained",   "Dissolved",    "Mine / Yours",         "SAW / SAUNT"),
    "A": ("Corrective",  "Drifting",     "My life / Their life", "DID / DIDNT"),
}

# Information lineage map per constraint axis.
# Maps axis letter → (constraint_domain, information_lineage, cognitive_role)
# Communication = result of all five acting simultaneously:
#   Information admissible (X) × Belief temporally coherent (T) ×
#   Purpose energetically viable (N) × Meaning boundary defined (B) ×
#   Understanding agency confirmed (A)
INFORMATION_LINEAGE_MAP: Dict[str, Tuple[str, str, str]] = {
    "X": ("Existence", "Information",   "Field Foundation"),
    "T": ("Temporal",  "Belief",        "Field Propagation"),
    "N": ("Energy",    "Purpose",       "Field Cost"),
    "B": ("Boundary",  "Meaning",       "Field Magnitude"),
    "A": ("Agency",    "Understanding", "Field Impact"),
}

# Magnitude formula: Magnitude = (B × T × X) / N
# Semantic reading: Meaning = (Boundary × Belief × Information) / Purpose
#   B = primary magnitude carrier — boundary IS the measure
#   T = propagation multiplier — how far magnitude reaches through time
#   X = coherence anchor — grounds magnitude in admissibility
#   N = normalization denominator — cost of sustaining magnitude
#     (higher N activation = lower magnitude cost ratio = more efficient field)
# This is NC Registry Dimension 1 (MAGNITUDE) canonical formula.
MAGNITUDE_NUMERATOR_AXES: Tuple[str, str, str] = ("B", "T", "X")
MAGNITUDE_DENOMINATOR_AXIS: str = "N"

# Impact formula: Impact = Magnitude × A = ((B × T × X) / N) × A
# Semantic reading: Understanding = Meaning × Agency
#   A converts field potential (magnitude) into directed cognitive outcome.
#   Agency without magnitude is incoherent. Magnitude without agency is inert.
# This is the composite NC Dimension 1+2 (MAGNITUDE × OPERATOR[A]) formula.
IMPACT_NUMERATOR_AXES: Tuple[str, str, str, str] = ("B", "T", "X", "A")
IMPACT_DENOMINATOR_AXIS: str = "N"

# NC dimension provenance per axis — which NC dimension a link's dominant axis
# most directly exercises. Derived from the information lineage above.
#   X → OPERATOR  (admissibility gate is the existence operator)
#   T → DIFFERENCE (temporal sequence creates delta from expected tick)
#   N → COST      (energy conservation is the cost reference dimension)
#   B → MAGNITUDE (boundary is the primary magnitude carrier)
#   A → POLARITY  (agency control sets direction/polarity of impact)
AXIS_NC_DIM: Dict[str, str] = {
    "X": "OPERATOR",
    "T": "DIFFERENCE",
    "N": "COST",
    "B": "MAGNITUDE",
    "A": "POLARITY",
}


# ===========================================================================
# SECTION 2 — PER-LAYER COST PARAMETERS
# ===========================================================================

# Tick & Density Constants (upgrade — Apr 2026)
SUBSURFACE_TICK_MULTIPLIER = 100
SURFACE_TICK_INTERVAL_S = 0.5
SUBSURFACE_TICK_BASE_S = 15.0
LAYER_DENSITY_RATIO = {"X": 1.0, "T": 7.0, "N": 10.0, "B": 40.0, "A": 150.0}

@dataclass(frozen=True)
class LayerCostParams:
    """
    The energy cost structure for one constraint/layer.

    baseline_budget  — energy consumed per tick just to exist at this layer
    shift_cost_coeff — energy consumed per unit of magnitude shift at this layer
    time_constant    — how quickly this layer can respond (inverse of inertia)
    leverage_sign    — +1 (overhead/negative) or -1 (leverage/positive) on the
                       signed cost scalar.  X and T are overhead; B and A are
                       leverage; N is the neutral zero-point (sign = 0).
    """
    constraint:       Constraint
    baseline_budget:  float   # B_L — per-tick maintenance cost
    shift_cost_coeff: float   # k_L — energy per unit magnitude change
    time_constant:    float   # τ_L — response speed (1.0 = instant, 0.0 = frozen)
    leverage_sign:    int     # -1 = overhead, 0 = neutral, +1 = leverage


# Canonical layer cost table — the hard numbers that govern energy physics.
# All values are expressed relative to the X (existence) baseline = 1.0.
#
# Rule: kX < kT < kN (neutral) < kB < kA
#
# These ratios emerge from Sunni's architecture (cheap to exist, expensive to
# control) and must NOT be adjusted to produce desired behaviors. If the
# emergent behavior is wrong, re-examine the architecture, not these numbers.

LAYER_COST: Dict[Constraint, LayerCostParams] = {
    Constraint.X: LayerCostParams(
        constraint       = Constraint.X,
        baseline_budget  = 1.0,      # reference unit; cheapest
        shift_cost_coeff = 1.0,      # k_X
        time_constant    = 1.0,      # surface — instant response
        leverage_sign    = -1,       # overhead (costs without returning leverage)
    ),
    Constraint.T: LayerCostParams(
        constraint       = Constraint.T,
        baseline_budget  = 5.0,      # hidden fulcrum — cascade tax reflects downstream dependency count
        shift_cost_coeff = 7.0,      # k_T raised from 4.0 — T perturbation is cheap but cascade-catastrophic
        time_constant    = 0.316,    # shallow — fast but not instant
        leverage_sign    = -1,       # overhead (persistence tax); B-T coupling mirrors mass-time relativity
    ),
    Constraint.N: LayerCostParams(
        constraint       = Constraint.N,
        baseline_budget  = 6.0,      # mid-range
        shift_cost_coeff = 10.0,     # k_N — the accounting crossover
        time_constant    = 0.01,     # moderate — balanced react/align
        leverage_sign    = 0,        # NEUTRAL (zero-point of leverage scalar)
    ),
    Constraint.B: LayerCostParams(
        constraint       = Constraint.B,
        baseline_budget  = 18.0,     # expensive — topology is not free
        shift_cost_coeff = 40.0,     # k_B — structural changes cost significantly
        time_constant    = 0.00316,  # deep — slow to change, high alignment pull
        leverage_sign    = +1,       # leverage (generates structure / control space)
    ),
    Constraint.A: LayerCostParams(
        constraint       = Constraint.A,
        baseline_budget  = 50.0,     # most expensive — complexity costs
        shift_cost_coeff = 150.0,    # k_A — agency shifts are tectonic
        time_constant    = 0.0001,   # core — barely reactive locally
        leverage_sign    = +1,       # leverage (directed control reduces future cost)
    ),
}

# Ordering assertion (enforced at import time)
_COST_ORDER = [
    LAYER_COST[Constraint.X].shift_cost_coeff,
    LAYER_COST[Constraint.T].shift_cost_coeff,
    LAYER_COST[Constraint.N].shift_cost_coeff,
    LAYER_COST[Constraint.B].shift_cost_coeff,
    LAYER_COST[Constraint.A].shift_cost_coeff,
]
assert _COST_ORDER == sorted(_COST_ORDER), (
    "LAYER_COST ordering violated: kX < kT < kN < kB < kA must hold. "
    "Do not adjust these values to produce desired behaviors."
)


# ===========================================================================
# SECTION 2b — DIFFERENCE CHANNEL PARAMETERS (the fifth lens)
# ===========================================================================

@dataclass(frozen=True)
class DifferenceParams:
    """
    The Difference (Δ) Non-Comp for one constraint — the fifth lens.

    Encodes how this constraint's current magnitude deviates from a reference
    point. The reference type is per-constraint because the semantic meaning
    of 'difference' is not uniform across the constraint stack.

    ref_type        — what the reference point is:
                      'prior_self'  → compare to self N ticks ago (temporal Δ)
                      'peer_mean'   → compare to mean magnitude of other constraints
                      'background'  → compare to a fixed architectural resting value

    window_ticks    — how many ticks back to look ('prior_self'); averaging window
                      for 'peer_mean'; reserved for 'background' (future hybrid use)

    normalize_scale — divisor that maps Δ into the [-1, +1] operating range.
                      Set equal to shift_cost_coeff from LAYER_COST so the Δ
                      channel lives on the same magnitude scale as the other
                      four Non-Comp dimensions.

    polarity_signed — True  → sign of Δ carries directional meaning (growth vs decay)
                      False → only |Δ| is meaningful (deviation magnitude only)

    COMPUTED Δ (runtime, via NonCompRegistry.compute_difference):
        delta_raw = current_magnitude − reference_magnitude
        C:D       = delta_raw / normalize_scale
        if not polarity_signed: C:D = abs(C:D)
        C:D is clipped to [−1, +1] before use in any downstream channel.
    """
    constraint:      Constraint
    ref_type:        str    # 'prior_self' | 'peer_mean' | 'background'
    window_ticks:    int    # ticks to look back; or averaging window for peer_mean
    normalize_scale: float  # divisor; matches shift_cost_coeff of this constraint
    polarity_signed: bool   # whether sign of Δ carries directional meaning


DIFFERENCE_PARAMS: Dict[Constraint, DifferenceParams] = {
    #
    # X — Existence
    #   ref:  prior_self, 1 tick back
    #   why:  Existence is self-referential. What matters is whether the system
    #         is drifting from itself — direction is irrelevant, magnitude only.
    #   sign: unsigned — existence drift is a scalar alarm, not a vector.
    #
    Constraint.X: DifferenceParams(
        constraint      = Constraint.X,
        ref_type        = 'prior_self',
        window_ticks    = 1,
        normalize_scale = 1.0,      # matches k_X — surface, fast signal
        polarity_signed = False,    # drift magnitude only; direction immaterial
    ),
    #
    # T — Time / Sequence
    #   ref:  prior_self, 4-tick window
    #   why:  Temporal momentum — is the sequence accelerating or decelerating?
    #         Direction is meaningful: speeding up vs slowing down are different states.
    #   sign: signed — T:D captures temporal acceleration/deceleration direction.
    #
    Constraint.T: DifferenceParams(
        constraint      = Constraint.T,
        ref_type        = 'prior_self',
        window_ticks    = 4,
        normalize_scale = 4.0,      # matches k_T — momentum window
        polarity_signed = True,     # acceleration (+) vs deceleration (−) are distinct
    ),
    #
    # N — Energy
    #   ref:  peer_mean across other constraints, 4-tick window
    #   why:  Energy is inherently relational — over/under-spending relative to
    #         the field is the signal. N is the zero-point mediator; its Δ
    #         is only meaningful when compared to what everything else is doing.
    #   sign: signed — over-spending vs under-spending are asymmetric states.
    #
    Constraint.N: DifferenceParams(
        constraint      = Constraint.N,
        ref_type        = 'peer_mean',
        window_ticks    = 4,
        normalize_scale = 10.0,     # matches k_N — peer-relative energy scale
        polarity_signed = True,     # over-spending (+) vs under-spending (−)
    ),
    #
    # B — Boundary
    #   ref:  background (architectural resting topology)
    #   why:  Boundaries have a resting structure. Structural drift from that
    #         resting state is the signal — not direction, just displacement.
    #   sign: unsigned — boundary deviation is a magnitude-of-drift alarm.
    #
    Constraint.B: DifferenceParams(
        constraint      = Constraint.B,
        ref_type        = 'background',
        window_ticks    = 8,        # reserved; future hybrid background/prior use
        normalize_scale = 40.0,     # matches k_B — structural drift scale
        polarity_signed = False,    # drift magnitude only; topology has no preferred direction
    ),
    #
    # A — Agency
    #   ref:  prior_self, 8-tick window
    #   why:  Agency gain vs loss is asymmetrically costly and directionally
    #         meaningful. Gaining agency is investment; losing it is erosion.
    #         Slow window because agency shifts are tectonic.
    #   sign: signed — agency growth (+) vs erosion (−) are categorically different.
    #
    Constraint.A: DifferenceParams(
        constraint      = Constraint.A,
        ref_type        = 'prior_self',
        window_ticks    = 8,
        normalize_scale = 150.0,    # matches k_A — tectonic agency scale
        polarity_signed = True,     # growth (+) vs erosion (−) are asymmetric
    ),
}


# ===========================================================================
# SECTION 3 — POLARITY MANIFOLD PARAMETERS
# ===========================================================================

@dataclass(frozen=True)
class PolarityParams:
    """
    The polarity Non-Comp for one constraint.

    Polarity is a CONTINUOUS TOROIDAL GRADIENT — not a binary flag.
    The phase runs from 0.0 → 2π, where cos(phase) gives the signed value.

        +1.0 = pure positive pole (is, can, do, saw, did)
        -1.0 = pure negative pole (isn't, can't, don't, saunt, didn't)
         0.0 = transition point (throat of the torus)

    phase_neutral  — the phase angle corresponding to 0.0 polarity (π/2)
    flip_threshold — minimum gradient_pressure to begin phase inversion
    i_state_pos    — name of the positive I-State operator for this constraint
    i_state_neg    — name of the negative I-State operator for this constraint
    """
    constraint:      Constraint
    phase_neutral:   float   # radians — neutral point on the torus
    flip_threshold:  float   # gradient pressure required to begin polarity shift
    i_state_pos:     str     # e.g. "is", "can", "do", "saw", "did"
    i_state_neg:     str     # e.g. "isn't", "can't", "don't", "saunt", "didn't"


POLARITY_PARAMS: Dict[Constraint, PolarityParams] = {
    Constraint.X: PolarityParams(
        constraint     = Constraint.X,
        phase_neutral  = math.pi / 2,
        flip_threshold = 0.35,   # surface flips easily
        i_state_pos    = "is",
        i_state_neg    = "isn't",
    ),
    Constraint.T: PolarityParams(
        constraint     = Constraint.T,
        phase_neutral  = math.pi / 2,
        flip_threshold = 0.42,
        i_state_pos    = "can",
        i_state_neg    = "can't",
    ),
    Constraint.N: PolarityParams(
        constraint     = Constraint.N,
        phase_neutral  = math.pi / 2,
        flip_threshold = 0.50,   # mid — balanced
        i_state_pos    = "do",
        i_state_neg    = "don't",
    ),
    Constraint.B: PolarityParams(
        constraint     = Constraint.B,
        phase_neutral  = math.pi / 2,
        flip_threshold = 0.65,   # deep — resists flip
        i_state_pos    = "saw",
        i_state_neg    = "saunt",
    ),
    Constraint.A: PolarityParams(
        constraint     = Constraint.A,
        phase_neutral  = math.pi / 2,
        flip_threshold = 0.82,   # core — extremely resistant to polarity inversion
        i_state_pos    = "did",
        i_state_neg    = "didn't",
    ),
}


# ===========================================================================
# SECTION 4 — OPERATOR DEFINITIONS
# ===========================================================================

@dataclass(frozen=False)
class OperatorParams:
    """
    The operator Non-Comp for one constraint.

    The operator is the invariant TRANSFORMATION RULE that this constraint
    applies to whatever passes through it. It is not a behavior — it is a
    lawful gate.

    description   — human-readable rule statement
    scope         — 'global' means applied to all system processes, not just
                    those explicitly requesting it
    is_conserved  — True if this operator enforces a conservation law
    """
    constraint:   Constraint
    description:  str
    scope:        str   # 'global' | 'local'
    is_conserved: bool
    pressure_gradient: float = 0.0  # dynamic live estimate (EMA)

# Critical asymmetries (from AURORA_UNIFIED_FIELD_SPEC.md):
#   X, T, N — scope='global': apply universally to ALL processes
#   B, A    — scope='local' : apply per-entity, not universally
#   N       — scope='global_reference': the conservation law, zero-point for all cost
#   N alone has is_conserved=True — it is the only conserved operator
OPERATOR_PARAMS: Dict[Constraint, OperatorParams] = {
    Constraint.X: OperatorParams(
        constraint   = Constraint.X,
        description  = (
            "Existence gate: everything must pass the admissibility predicate "
            "before it can be represented in the system. If X ≤ 0 the manifold "
            "collapses and nothing can be processed."
        ),
        scope        = 'global',
        is_conserved = False,   # Existence is a gate, not a conserved quantity
    ),
    Constraint.T: OperatorParams(
        constraint   = Constraint.T,
        description  = (
            "Time tick operator: every sequence-step advances the system. "
            "Persistence costs accumulate. Nothing can un-tick. The operator "
            "enforces the arrow of time: consequences cannot be un-accumulated."
        ),
        scope        = 'global',
        is_conserved = False,   # Time is monotonically advancing
    ),
    Constraint.N: OperatorParams(
        constraint   = Constraint.N,
        description  = (
            "Energy conservation operator: total system energy is finite and "
            "neither created nor destroyed within a closed tick. Any magnitude "
            "increase in one constraint must be paid for by reduction elsewhere. "
            "External inputs carry an intrinsic energy payload equivalent to their "
            "internal generation cost. N is the zero-point reference for all cost "
            "measurement — the normalization denominator in the magnitude formula."
        ),
        scope        = 'global_reference',  # N is the conservation law — zero-point
        is_conserved = True,    # N is the one conserved quantity; all others measured against it
    ),
    Constraint.B: OperatorParams(
        constraint   = Constraint.B,
        description  = (
            "Boundary topology operator: things have limits, structure, and "
            "separability. Boundaries can expand or contract but not dissolve "
            "without cost. Structural changes propagate through the layer stack."
        ),
        scope        = 'local',  # Boundary applies per-entity, not globally
        is_conserved = False,
    ),
    Constraint.A: OperatorParams(
        constraint   = Constraint.A,
        description  = (
            "Agency control operator: the system can make directed choices "
            "that alter other constraints. Agency is the most expensive operation "
            "because it is the most complex — it requires modeling, prediction, "
            "and commitment. Agency without energy allocation is incoherent."
        ),
        scope        = 'local',
        is_conserved = False,
    ),
}


# ===========================================================================
# SECTION 5 — THE NONCOMP REGISTRY
# ===========================================================================

class NonCompRegistry:
    """
    The canonical home for all 25 Non-Comps.

    NC[C][R] where:
        C ∈ {X, T, N, B, A}
        R ∈ {POLARITY, MAGNITUDE, OPERATOR, COST, DIFFERENCE}

    This registry is READ-ONLY at runtime. Non-Comps are invariant laws,
    not configuration values. Nothing in the system may modify them after boot.

    Usage:
        registry = NonCompRegistry()
        params = registry.cost(Constraint.A)         # → LayerCostParams
        pol    = registry.polarity(Constraint.B)     # → PolarityParams
        op     = registry.operator(Constraint.N)     # → OperatorParams
        diff   = registry.difference(Constraint.T)   # → DifferenceParams

    Derived:
        scalar  = registry.leverage_scalar(magnitudes)         # → float
        budget  = registry.baseline_tick_cost()                # → float (total per tick)
        delta   = registry.compute_difference(c, cur, ref)     # → float in [-1, +1]
    """

    def __init__(self) -> None:
        # Freeze the tables at construction — no mutation allowed
        self._cost:       Dict[Constraint, LayerCostParams]   = dict(LAYER_COST)
        self._polarity:   Dict[Constraint, PolarityParams]    = dict(POLARITY_PARAMS)
        self._operator:   Dict[Constraint, OperatorParams]    = dict(OPERATOR_PARAMS)
        self._difference: Dict[Constraint, DifferenceParams]  = dict(DIFFERENCE_PARAMS)
        self._locked: bool = True

    # ------------------------------------------------------------------
    # ACCESSORS
    # ------------------------------------------------------------------

    def cost(self, c: Constraint) -> LayerCostParams:
        """Return the cost Non-Comp for constraint c."""
        return self._cost[c]

    def polarity(self, c: Constraint) -> PolarityParams:
        """Return the polarity Non-Comp for constraint c."""
        return self._polarity[c]

    def operator(self, c: Constraint) -> OperatorParams:
        """Return the operator Non-Comp for constraint c."""
        return self._operator[c]

    def difference(self, c: Constraint) -> DifferenceParams:
        """Return the Difference (Δ) Non-Comp for constraint c."""
        return self._difference[c]

    def all_constraints(self) -> Tuple[Constraint, ...]:
        """Return all five constraints in canonical order."""
        return (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A)

    # ------------------------------------------------------------------
    # DIFFERENCE CHANNEL — RUNTIME Δ COMPUTATION
    # ------------------------------------------------------------------

    def compute_difference(
        self,
        c: Constraint,
        current_magnitude: float,
        reference_magnitude: float,
    ) -> float:
        """
        Compute the normalized Δ value (C:D) for constraint c.

        Parameters
        ----------
        c                   : the constraint being measured
        current_magnitude   : magnitude reading at this tick
        reference_magnitude : the reference computed by the caller per DifferenceParams:
                              - 'prior_self'  → magnitude N ticks ago
                              - 'peer_mean'   → mean magnitude of the other four constraints
                              - 'background'  → architectural resting value for this constraint

        Returns
        -------
        float clipped to [−1, +1].
        Unsigned if DifferenceParams.polarity_signed is False (abs applied before clip).

        The caller is responsible for supplying the correct reference_magnitude
        according to the constraint's ref_type. This method applies only the
        normalization, sign rule, and clip — it does not fetch history.
        """
        params = self._difference[c]
        if params.normalize_scale <= 0.0:
            raise ManifoldViolation(
                f"DifferenceParams.normalize_scale must be positive for {c.name}"
            )
        raw = (current_magnitude - reference_magnitude) / params.normalize_scale
        if not params.polarity_signed:
            raw = abs(raw)
        return max(-1.0, min(1.0, raw))

    # ------------------------------------------------------------------
    # DERIVED COMPUTATIONS (read-only outputs derived from non-comps)
    # ------------------------------------------------------------------

    def baseline_tick_cost(self) -> float:
        """
        Total energy consumed per tick just by existing at all layers.

        This is the system's maintenance tax — the cost of being.
        It is non-negotiable and paid before any action occurs.
        If total available energy < baseline_tick_cost, the system decays.
        """
        return sum(p.baseline_budget for p in self._cost.values())

    def shift_cost(self, c: Constraint, delta_magnitude: float) -> float:
        """
        Energy consumed to shift the magnitude of constraint c by delta_magnitude.

        This is zero-sum: the energy comes from the system's total budget.
        Deeper layers cost proportionally more per unit shift.
        """
        return self._cost[c].shift_cost_coeff * abs(delta_magnitude)

    def leverage_scalar(
        self,
        magnitudes: Dict[Constraint, float],
    ) -> float:
        """
        Compute the Net Leverage Scalar from current constraint magnitudes.

        Formula:
            Net Leverage = (M_B + M_A) − (M_X + M_T)
            N is the zero-point (its magnitude is neither overhead nor leverage)

        Interpretation:
            < 0   → overhead dominant — system is bleeding maintenance cost
            ≈ 0   → balanced metabolism
            > 0   → leverage investment — structure/control is being built

        The system should seek a VIABLE BAND, not maximum positive leverage.
        Permanently positive leverage leads to rigidity.
        Permanently negative leads to decay.
        """
        m = magnitudes
        b = m.get(Constraint.B, 0.0)
        a = m.get(Constraint.A, 0.0)
        x = m.get(Constraint.X, 0.0)
        t = m.get(Constraint.T, 0.0)
        return (b + a) - (x + t)

    def entropy_pressure(
        self,
        magnitudes: Dict[Constraint, float],
        *,
        saturation_ceiling: float = 1.0,
    ) -> float:
        """
        Compute global entropy pressure — how close the system is to
        simultaneous constraint saturation (the violation condition).

        Returns a value in [0.0, 1.0]:
            0.0 = no saturation pressure
            1.0 = all constraints at maximum — imminent violation

        Violation condition: all five constraints at saturation_ceiling
        simultaneously → system must redistribute or decay.
        """
        if saturation_ceiling <= 0:
            raise ManifoldViolation(
                "saturation_ceiling must be positive"
            )
        total = sum(
            min(1.0, m / saturation_ceiling)
            for m in magnitudes.values()
        )
        return total / 5.0

    def polarity_signed(self, c: Constraint, phase: float) -> float:
        """
        Compute the signed polarity value for constraint c at the given phase.

            polarity = cos(phase)

        +1.0 = pure positive pole
        -1.0 = pure negative pole
         0.0 = transition (throat of torus)

        Phase should be in [0, 2π].
        """
        return math.cos(phase)

    def cost_ordering(self) -> Tuple[Constraint, ...]:
        """
        Return constraints sorted by shift_cost_coeff (cheapest first).

        Canonical order: X < T < N < B < A
        """
        return tuple(
            sorted(self._cost.keys(), key=lambda c: self._cost[c].shift_cost_coeff)
        )

    def inertia(self, c: Constraint) -> float:
        """
        Return the effective inertia for constraint c.

        Inertia = 1 / time_constant
        Higher inertia → slower to change → more expensive to shift

        X: lowest inertia (surface, fast)
        A: highest inertia (core, tectonic)
        """
        tc = self._cost[c].time_constant
        if tc <= 0:
            return float('inf')
        return 1.0 / tc

    def describe(self, c: Constraint) -> str:
        """Return a compact human-readable description of one constraint's Non-Comps."""
        cp = self._cost[c]
        pp = self._polarity[c]
        op = self._operator[c]
        dp = self._difference[c]
        sign_str = "signed (±)" if dp.polarity_signed else "unsigned (|Δ|)"
        return (
            f"Constraint {c.name}:\n"
            f"  I-State pair:     {pp.i_state_pos} / {pp.i_state_neg}\n"
            f"  Baseline budget:  {cp.baseline_budget:.1f} energy/tick\n"
            f"  Shift cost coeff: {cp.shift_cost_coeff:.1f} energy/unit\n"
            f"  Time constant:    {cp.time_constant:.5f}  (inertia={self.inertia(c):.1f})\n"
            f"  Leverage sign:    {'overhead (−)' if cp.leverage_sign < 0 else ('leverage (+)' if cp.leverage_sign > 0 else 'neutral (0)')}\n"
            f"  Polarity flip θ:  {pp.flip_threshold:.2f}\n"
            f"  Operator scope:   {op.scope}  conserved={op.is_conserved}\n"
            f"  Operator:         {op.description[:80]}...\n"
            f"  Δ ref_type:       {dp.ref_type}  window={dp.window_ticks}t  "
            f"scale={dp.normalize_scale:.1f}  {sign_str}"
        )

    def summarize(self) -> str:
        """Return a full registry summary."""
        lines = [
            "=" * 70,
            "AURORA NON-COMP REGISTRY — 25 CANONICAL NON-COMPS",
            "Authors: Sunni (Sir) Morningstar and Cael Devo",
            "=" * 70,
            "",
            f"Baseline tick cost (total maintenance tax): {self.baseline_tick_cost():.1f} energy/tick",
            f"Cost ordering (cheapest → most expensive):  {' < '.join(c.name for c in self.cost_ordering())}",
            "",
        ]
        for c in self.all_constraints():
            lines.append(self.describe(c))
            lines.append("")
        lines.append("=" * 70)
        return "\n".join(lines)


# ===========================================================================
# SECTION 6 — LIVE CONSTRAINT STATE (mutable, runtime object)
# ===========================================================================

@dataclass
class ConstraintState:
    """
    The mutable runtime state of one constraint at a given moment.

    This is NOT a Non-Comp — it is a derived, time-varying object
    whose physics are governed by the Non-Comps in the registry.

    phase     — current position on the toroidal manifold [0, 2π]
    magnitude — current activation intensity [0.0, ∞)
    """
    constraint: Constraint
    phase:      float = math.pi / 2   # start at neutral (polarity = 0)
    magnitude:  float = 0.0

    @property
    def polarity(self) -> float:
        """Signed polarity value: cos(phase) ∈ [-1, +1]."""
        return math.cos(self.phase)

    def is_positive(self) -> bool:
        return self.polarity > 0.0

    def is_negative(self) -> bool:
        return self.polarity < 0.0

    def is_at_transition(self) -> bool:
        return abs(self.polarity) < 0.05


@dataclass
class SystemConstraintStates:
    """
    Live state of all five constraints at a given tick.

    This is the mutable runtime snapshot that the evolution chamber,
    genealogy logger, and polarity gradient sensor all read from.

    It is NOT the registry — it does not contain Non-Comps.
    It contains current values whose physics are derived from Non-Comps.
    """
    states: Dict[Constraint, ConstraintState] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Ensure all five constraints are represented
        for c in (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A):
            if c not in self.states:
                self.states[c] = ConstraintState(constraint=c)

    def magnitudes(self) -> Dict[Constraint, float]:
        """Return current magnitude for each constraint."""
        return {c: s.magnitude for c, s in self.states.items()}

    def phases(self) -> Dict[Constraint, float]:
        """Return current phase for each constraint."""
        return {c: s.phase for c, s in self.states.items()}

    def polarities(self) -> Dict[Constraint, float]:
        """Return signed polarity (cos(phase)) for each constraint."""
        return {c: s.polarity for c, s in self.states.items()}

    def leverage_scalar(self, registry: NonCompRegistry) -> float:
        """Compute Net Leverage Scalar from current magnitudes."""
        return registry.leverage_scalar(self.magnitudes())

    def entropy_pressure(self, registry: NonCompRegistry) -> float:
        """Compute global entropy pressure from current magnitudes."""
        return registry.entropy_pressure(self.magnitudes())

    def to_constraint_vector(self) -> ConstraintVector:
        """
        Convert to a ConstraintVector for compatibility with the manifold stack.

        Uses magnitude as the vector value per axis.
        Ensures X > 0 (existence admissibility) by flooring to 1e-9.
        """
        m = self.magnitudes()
        return ConstraintVector(
            X=max(1e-9, m.get(Constraint.X, 1e-9)),
            T=m.get(Constraint.T, 0.0),
            N=m.get(Constraint.N, 0.0),
            B=m.get(Constraint.B, 0.0),
            A=m.get(Constraint.A, 0.0),
        )


# ===========================================================================
# SECTION 7 — MODULE-LEVEL SINGLETON
# ===========================================================================

# The one canonical registry. Import this — do not construct a second one.
REGISTRY: NonCompRegistry = NonCompRegistry()


# ===========================================================================
# SECTION 8 — SELF-VERIFICATION
# ===========================================================================

def verify_noncomp_registry() -> Dict[str, object]:
    """
    Verify the Non-Comp Registry's structural integrity.

    All 25 Non-Comps must be present and internally consistent.
    The cost ordering law must hold.
    The leverage scalar must correctly classify overhead vs leverage.
    The Difference channel must normalize into [-1, +1] correctly.
    """
    results = {"checks": [], "all_passed": True}

    def check(name: str, passed: bool, detail: str = "") -> None:
        results["checks"].append({"test": name, "passed": passed, "detail": detail})
        if not passed:
            results["all_passed"] = False

    r = REGISTRY

    # 1. All 25 Non-Comps present (5 constraints × 5 dimensions)
    for c in r.all_constraints():
        check(f"cost NC present: {c.name}",       c in LAYER_COST)
        check(f"polarity NC present: {c.name}",   c in POLARITY_PARAMS)
        check(f"operator NC present: {c.name}",   c in OPERATOR_PARAMS)
        check(f"difference NC present: {c.name}", c in DIFFERENCE_PARAMS)

    # 2. Cost ordering: kX < kT < kN < kB < kA
    ordering = r.cost_ordering()
    check(
        "Cost ordering: X < T < N < B < A",
        ordering == (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A),
        str([r.cost(c).shift_cost_coeff for c in ordering])
    )

    # 3. Inertia increases with depth
    inertias = [r.inertia(c) for c in ordering]
    check(
        "Inertia increases with depth",
        inertias == sorted(inertias),
        str(inertias)
    )

    # 4. Leverage signs correct
    check("X is overhead (−1)", r.cost(Constraint.X).leverage_sign == -1)
    check("T is overhead (−1)", r.cost(Constraint.T).leverage_sign == -1)
    check("N is neutral  ( 0)", r.cost(Constraint.N).leverage_sign ==  0)
    check("B is leverage (+1)", r.cost(Constraint.B).leverage_sign == +1)
    check("A is leverage (+1)", r.cost(Constraint.A).leverage_sign == +1)

    # 5. Leverage scalar computes correctly
    # Max overhead: X=1, T=1, B=0, A=0 → scalar = -2
    s_neg = r.leverage_scalar({
        Constraint.X: 1.0, Constraint.T: 1.0,
        Constraint.N: 0.0, Constraint.B: 0.0, Constraint.A: 0.0
    })
    check("Leverage scalar negative when overhead dominant", s_neg < 0, str(s_neg))

    # Max leverage: X=0, T=0, B=1, A=1 → scalar = +2
    s_pos = r.leverage_scalar({
        Constraint.X: 0.0, Constraint.T: 0.0,
        Constraint.N: 0.0, Constraint.B: 1.0, Constraint.A: 1.0
    })
    check("Leverage scalar positive when leverage dominant", s_pos > 0, str(s_pos))

    # Balanced: symmetric → scalar = 0
    s_zero = r.leverage_scalar({
        Constraint.X: 1.0, Constraint.T: 1.0,
        Constraint.N: 0.0, Constraint.B: 1.0, Constraint.A: 1.0
    })
    check("Leverage scalar zero at symmetric balance", abs(s_zero) < 1e-9, str(s_zero))

    # 6. Polarity is continuous gradient
    import math as _math
    for c in r.all_constraints():
        pp = r.polarity(c)
        pol_pos  = r.polarity_signed(c, 0.0)
        pol_neg  = r.polarity_signed(c, _math.pi)
        pol_neut = r.polarity_signed(c, pp.phase_neutral)
        check(f"Polarity positive pole = +1.0: {c.name}", abs(pol_pos  - 1.0) < 1e-9)
        check(f"Polarity negative pole = −1.0: {c.name}", abs(pol_neg  + 1.0) < 1e-9)
        check(f"Polarity neutral ≈ 0.0: {c.name}",        abs(pol_neut)       < 0.01)

    # 7. Flip thresholds increase with depth
    flip_thresholds = [r.polarity(c).flip_threshold for c in ordering]
    check(
        "Flip thresholds increase with depth (surface flips easiest)",
        flip_thresholds == sorted(flip_thresholds),
        str(flip_thresholds)
    )

    # 8. SystemConstraintStates round-trip
    scs = SystemConstraintStates()
    scs.states[Constraint.X].magnitude = 1.0
    cv = scs.to_constraint_vector()
    check("SystemConstraintStates → ConstraintVector: X admissible", cv.X > 0)

    # 9. Difference channel: normalize_scale matches shift_cost_coeff
    for c in r.all_constraints():
        dp = r.difference(c)
        cp = r.cost(c)
        check(
            f"Difference normalize_scale matches shift_cost_coeff: {c.name}",
            abs(dp.normalize_scale - cp.shift_cost_coeff) < 1e-9,
            f"diff_scale={dp.normalize_scale}  k={cp.shift_cost_coeff}"
        )

    # 10. compute_difference: zero delta → 0.0
    for c in r.all_constraints():
        val = r.compute_difference(c, 0.5, 0.5)
        check(f"compute_difference: zero delta → 0.0: {c.name}", val == 0.0, str(val))

    # 11. compute_difference: clipped to [-1, +1]
    val_hi = r.compute_difference(Constraint.A, 9999.0, 0.0)
    val_lo = r.compute_difference(Constraint.T, 0.0, 9999.0)
    check("compute_difference: large positive clipped to +1.0", val_hi == 1.0, str(val_hi))
    check("compute_difference: large negative clipped to -1.0 or 0.0",
          val_lo <= 0.0, str(val_lo))  # T is signed, so -1.0; X/B would be 1.0 (unsigned)

    # 12. unsigned constraints return non-negative Δ
    for c in (Constraint.X, Constraint.B):
        val_neg = r.compute_difference(c, 0.0, 9999.0)
        check(
            f"compute_difference: unsigned constraint returns ≥ 0: {c.name}",
            val_neg >= 0.0,
            str(val_neg)
        )

    return results


# ===========================================================================
# MAIN
# ===========================================================================

if __name__ == "__main__":
    print(REGISTRY.summarize())
    print()
    print("Running verification...")
    results = verify_noncomp_registry()
    for item in results["checks"]:
        status = "✓" if item["passed"] else "✗"
        detail = f"  [{item['detail']}]" if item.get("detail") else ""
        print(f"  {status}  {item['test']}{detail}")
    print()
    if results["all_passed"]:
        print("ALL 25 NON-COMPS VERIFIED ✓")
        print("The substrate is sound. Build upward.")
    else:
        print("FAILURES DETECTED ✗")
        print("Do not build above this layer until resolved.")

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

_AURORA_NATIVE_MODULE = 'aurora_internal.aurora_noncomp_registry'

_AURORA_NATIVE_EVOLVED_ORIGINALS = {}
_AURORA_NATIVE_EVOLVED_LAST = {}
_AURORA_NATIVE_STRATEGIES = {'ConstraintState': {'ability_hits': 0,
                     'alignment_gap': 0.271,
                     'alignment_target_score': 1.192,
                     'best_coupling_signature': 'X^2*B^2',
                     'constraints': ['existence', 'boundary'],
                     'contract_profile': {'accepts_payload': False,
                                          'async_callable': False,
                                          'callable': True,
                                          'class_target': True,
                                          'constraint_density': 2,
                                          'contract_mode': 'stateless',
                                          'doc_hint': 'The mutable runtime state of one constraint '
                                                      'at a given moment.',
                                          'effect_density': 3,
                                          'kwonly_args': 0,
                                          'optional_args': 2,
                                          'required_args': 1,
                                          'return_hint': 'None',
                                          'signature_text': "(constraint: 'Constraint', phase: "
                                                            "'float' = 1.5707963267948966, "
                                                            "magnitude: 'float' = 0.0) -> None",
                                          'stateful_owner': False,
                                          'target_kind': 'class',
                                          'varargs': False,
                                          'varkw': False},
                     'coupling_similarity': 1.0,
                     'cross_diversity_links': 4,
                     'effect_modes': ['state_schema_change',
                                      'interface_boundary_change',
                                      'class_lineage_surface'],
                     'effect_phrases': ['class growth reflected through '
                                        'aurora_internal.aurora_noncomp_registry',
                                        'ConstraintState changed downstream system pressure'],
                     'genealogy_pressure': 0.400328,
                     'inheritance_breach_count': 1,
                     'kind': 'reflection',
                     'link_hits': 0,
                     'module': 'aurora_internal.aurora_noncomp_registry',
                     'op_id': 'aurora_internal.aurora_noncomp_registry.ConstraintState',
                     'origin_activity': 0,
                     'persistence_tax_factor': 1.016424,
                     'representation_score': 0.638409,
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
                     'signature': 'X^2*B^2',
                     'surface_score': 0.921,
                     'sustainability_score': 0.51897,
                     'target_kind': 'class'},
 'NonCompDimension': {'ability_hits': 1,
                      'alignment_gap': 0.271,
                      'alignment_target_score': 1.192,
                      'best_coupling_signature': 'X^2*T^2',
                      'constraints': ['existence', 'temporal'],
                      'contract_profile': {'accepts_payload': True,
                                           'async_callable': False,
                                           'callable': True,
                                           'class_target': True,
                                           'constraint_density': 2,
                                           'contract_mode': 'stateless',
                                           'doc_hint': 'The five representational dimensions of '
                                                       'every Non-Comp.',
                                           'effect_density': 3,
                                           'kwonly_args': 4,
                                           'optional_args': 5,
                                           'required_args': 1,
                                           'return_hint': 'state_record',
                                           'signature_text': '(value, names=None, *, module=None, '
                                                             'qualname=None, type=None, start=1)',
                                           'stateful_owner': False,
                                           'target_kind': 'class',
                                           'varargs': False,
                                           'varkw': False},
                      'coupling_similarity': 1.0,
                      'cross_diversity_links': 4,
                      'effect_modes': ['state_schema_change',
                                       'temporal_orchestration_change',
                                       'class_lineage_surface'],
                      'effect_phrases': ['class growth reflected through '
                                         'aurora_internal.aurora_noncomp_registry',
                                         'NonCompDimension changed downstream system pressure'],
                      'genealogy_pressure': 0.44,
                      'inheritance_breach_count': 1,
                      'kind': 'reflection',
                      'link_hits': 2,
                      'module': 'aurora_internal.aurora_noncomp_registry',
                      'op_id': 'aurora_internal.aurora_noncomp_registry.NonCompDimension',
                      'origin_activity': 0,
                      'persistence_tax_factor': 1.5,
                      'representation_score': 0.813889,
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
                      'signature': 'X^2*T^2',
                      'surface_score': 0.921,
                      'sustainability_score': 0.394792,
                      'target_kind': 'class'},
 'NonCompRegistry': {'ability_hits': 1,
                     'alignment_gap': 0.271,
                     'alignment_target_score': 1.192,
                     'best_coupling_signature': 'X^2*T^2',
                     'constraints': ['existence', 'temporal'],
                     'contract_profile': {'accepts_payload': False,
                                          'async_callable': False,
                                          'callable': True,
                                          'class_target': True,
                                          'constraint_density': 2,
                                          'contract_mode': 'stateless',
                                          'doc_hint': 'The canonical home for all 25 Non-Comps.',
                                          'effect_density': 3,
                                          'kwonly_args': 0,
                                          'optional_args': 0,
                                          'required_args': 0,
                                          'return_hint': 'None',
                                          'signature_text': "() -> 'None'",
                                          'stateful_owner': False,
                                          'target_kind': 'class',
                                          'varargs': False,
                                          'varkw': False},
                     'coupling_similarity': 1.0,
                     'cross_diversity_links': 4,
                     'effect_modes': ['state_schema_change',
                                      'temporal_orchestration_change',
                                      'class_lineage_surface'],
                     'effect_phrases': ['class growth reflected through '
                                        'aurora_internal.aurora_noncomp_registry',
                                        'NonCompRegistry changed downstream system pressure'],
                     'genealogy_pressure': 0.44,
                     'inheritance_breach_count': 1,
                     'kind': 'reflection',
                     'link_hits': 2,
                     'module': 'aurora_internal.aurora_noncomp_registry',
                     'op_id': 'aurora_internal.aurora_noncomp_registry.NonCompRegistry',
                     'origin_activity': 0,
                     'persistence_tax_factor': 1.5,
                     'representation_score': 0.813889,
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
                     'signature': 'X^2*T^2',
                     'surface_score': 0.921,
                     'sustainability_score': 0.394792,
                     'target_kind': 'class'},
 'NonCompRegistry.all_constraints': {'ability_hits': 12,
                                     'alignment_gap': 0.56,
                                     'alignment_target_score': 1.192,
                                     'best_coupling_signature': 'B^3',
                                     'constraints': ['boundary'],
                                     'contract_profile': {'accepts_payload': False,
                                                          'async_callable': False,
                                                          'callable': True,
                                                          'class_target': False,
                                                          'constraint_density': 1,
                                                          'contract_mode': 'stateful',
                                                          'doc_hint': 'Return all five constraints '
                                                                      'in canonical order.',
                                                          'effect_density': 2,
                                                          'kwonly_args': 0,
                                                          'optional_args': 0,
                                                          'required_args': 0,
                                                          'return_hint': 'Tuple[Constraint, ...]',
                                                          'signature_text': '(self) -> '
                                                                            "'Tuple[Constraint, "
                                                                            "...]'",
                                                          'stateful_owner': True,
                                                          'target_kind': 'function',
                                                          'varargs': False,
                                                          'varkw': False},
                                     'coupling_similarity': 1.0,
                                     'cross_diversity_links': 2,
                                     'effect_modes': ['interface_boundary_change',
                                                      'lineage_surface'],
                                     'effect_phrases': ['function growth reflected through '
                                                        'aurora_internal.aurora_noncomp_registry',
                                                        'NonCompRegistry.all_constraints changed '
                                                        'downstream system pressure'],
                                     'genealogy_pressure': 0.75101,
                                     'inheritance_breach_count': 1,
                                     'kind': 'reflection',
                                     'link_hits': 24,
                                     'module': 'aurora_internal.aurora_noncomp_registry',
                                     'op_id': 'aurora_internal.aurora_noncomp_registry.NonCompRegistry.all_constraints',
                                     'origin_activity': 0,
                                     'persistence_tax_factor': 2.550513,
                                     'representation_score': 0.567611,
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
                                     'signature': 'B^3',
                                     'surface_score': 0.632,
                                     'sustainability_score': 0.356849,
                                     'target_kind': 'function'},
 'OperatorParams': {'ability_hits': 1,
                    'alignment_gap': 0.271,
                    'alignment_target_score': 1.192,
                    'best_coupling_signature': 'X^2*T^2',
                    'constraints': ['existence', 'temporal'],
                    'contract_profile': {'accepts_payload': False,
                                         'async_callable': False,
                                         'callable': True,
                                         'class_target': True,
                                         'constraint_density': 2,
                                         'contract_mode': 'stateless',
                                         'doc_hint': 'The operator Non-Comp for one constraint.',
                                         'effect_density': 3,
                                         'kwonly_args': 0,
                                         'optional_args': 1,
                                         'required_args': 4,
                                         'return_hint': 'None',
                                         'signature_text': "(constraint: 'Constraint', "
                                                           "description: 'str', scope: 'str', "
                                                           "is_conserved: 'bool', "
                                                           "pressure_gradient: 'float' = 0.0) -> "
                                                           'None',
                                         'stateful_owner': False,
                                         'target_kind': 'class',
                                         'varargs': False,
                                         'varkw': False},
                    'coupling_similarity': 1.0,
                    'cross_diversity_links': 4,
                    'effect_modes': ['state_schema_change',
                                     'temporal_orchestration_change',
                                     'class_lineage_surface'],
                    'effect_phrases': ['class growth reflected through '
                                       'aurora_internal.aurora_noncomp_registry',
                                       'OperatorParams changed downstream system pressure'],
                    'genealogy_pressure': 0.44,
                    'inheritance_breach_count': 1,
                    'kind': 'reflection',
                    'link_hits': 2,
                    'module': 'aurora_internal.aurora_noncomp_registry',
                    'op_id': 'aurora_internal.aurora_noncomp_registry.OperatorParams',
                    'origin_activity': 0,
                    'persistence_tax_factor': 1.5,
                    'representation_score': 0.813889,
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
                    'signature': 'X^2*T^2',
                    'surface_score': 0.921,
                    'sustainability_score': 0.394792,
                    'target_kind': 'class'},
 'PolarityParams': {'ability_hits': 1,
                    'alignment_gap': 0.271,
                    'alignment_target_score': 1.192,
                    'best_coupling_signature': 'X^2*T^2',
                    'constraints': ['existence', 'temporal'],
                    'contract_profile': {'accepts_payload': False,
                                         'async_callable': False,
                                         'callable': True,
                                         'class_target': True,
                                         'constraint_density': 2,
                                         'contract_mode': 'stateless',
                                         'doc_hint': 'The polarity Non-Comp for one constraint.',
                                         'effect_density': 3,
                                         'kwonly_args': 0,
                                         'optional_args': 0,
                                         'required_args': 5,
                                         'return_hint': 'None',
                                         'signature_text': "(constraint: 'Constraint', "
                                                           "phase_neutral: 'float', "
                                                           "flip_threshold: 'float', i_state_pos: "
                                                           "'str', i_state_neg: 'str') -> None",
                                         'stateful_owner': False,
                                         'target_kind': 'class',
                                         'varargs': False,
                                         'varkw': False},
                    'coupling_similarity': 1.0,
                    'cross_diversity_links': 4,
                    'effect_modes': ['state_schema_change',
                                     'temporal_orchestration_change',
                                     'class_lineage_surface'],
                    'effect_phrases': ['class growth reflected through '
                                       'aurora_internal.aurora_noncomp_registry',
                                       'PolarityParams changed downstream system pressure'],
                    'genealogy_pressure': 0.44,
                    'inheritance_breach_count': 1,
                    'kind': 'reflection',
                    'link_hits': 2,
                    'module': 'aurora_internal.aurora_noncomp_registry',
                    'op_id': 'aurora_internal.aurora_noncomp_registry.PolarityParams',
                    'origin_activity': 0,
                    'persistence_tax_factor': 1.5,
                    'representation_score': 0.813889,
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
                    'signature': 'X^2*T^2',
                    'surface_score': 0.921,
                    'sustainability_score': 0.394792,
                    'target_kind': 'class'},
 'SystemConstraintStates': {'ability_hits': 0,
                            'alignment_gap': 0.271,
                            'alignment_target_score': 1.192,
                            'best_coupling_signature': 'X^2*B^2',
                            'constraints': ['existence', 'boundary'],
                            'contract_profile': {'accepts_payload': False,
                                                 'async_callable': False,
                                                 'callable': True,
                                                 'class_target': True,
                                                 'constraint_density': 2,
                                                 'contract_mode': 'stateless',
                                                 'doc_hint': 'Live state of all five constraints '
                                                             'at a given tick.',
                                                 'effect_density': 3,
                                                 'kwonly_args': 0,
                                                 'optional_args': 1,
                                                 'required_args': 0,
                                                 'return_hint': 'None',
                                                 'signature_text': "(states: 'Dict[Constraint, "
                                                                   "ConstraintState]' = <factory>) "
                                                                   '-> None',
                                                 'stateful_owner': False,
                                                 'target_kind': 'class',
                                                 'varargs': False,
                                                 'varkw': False},
                            'coupling_similarity': 1.0,
                            'cross_diversity_links': 4,
                            'effect_modes': ['state_schema_change',
                                             'interface_boundary_change',
                                             'class_lineage_surface'],
                            'effect_phrases': ['class growth reflected through '
                                               'aurora_internal.aurora_noncomp_registry',
                                               'SystemConstraintStates changed downstream system '
                                               'pressure'],
                            'genealogy_pressure': 0.400328,
                            'inheritance_breach_count': 1,
                            'kind': 'reflection',
                            'link_hits': 0,
                            'module': 'aurora_internal.aurora_noncomp_registry',
                            'op_id': 'aurora_internal.aurora_noncomp_registry.SystemConstraintStates',
                            'origin_activity': 0,
                            'persistence_tax_factor': 1.016424,
                            'representation_score': 0.638409,
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
                            'signature': 'X^2*B^2',
                            'surface_score': 0.921,
                            'sustainability_score': 0.51897,
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

def constraintstate_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_noncomp_registry.ConstraintState', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_noncomp_registry_constraintstate')(payload=payload, **kwargs)

if _aurora_get_target(['ConstraintState']) is not None:
    setattr(_aurora_get_target(['ConstraintState']), 'evolved_reflection', staticmethod(constraintstate_evolved))
    setattr(_aurora_get_target(['ConstraintState']), '_aurora_alignment_gap', 0.271)
    setattr(_aurora_get_target(['ConstraintState']), '_aurora_alignment_target_score', 1.192)

def noncompdimension_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_noncomp_registry.NonCompDimension', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_noncomp_registry_noncompdimension')(payload=payload, **kwargs)

if _aurora_get_target(['NonCompDimension']) is not None:
    setattr(_aurora_get_target(['NonCompDimension']), 'evolved_reflection', staticmethod(noncompdimension_evolved))
    setattr(_aurora_get_target(['NonCompDimension']), '_aurora_alignment_gap', 0.271)
    setattr(_aurora_get_target(['NonCompDimension']), '_aurora_alignment_target_score', 1.192)

def noncompregistry_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_noncomp_registry.NonCompRegistry', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_noncomp_registry_noncompregistry')(payload=payload, **kwargs)

if _aurora_get_target(['NonCompRegistry']) is not None:
    setattr(_aurora_get_target(['NonCompRegistry']), 'evolved_reflection', staticmethod(noncompregistry_evolved))
    setattr(_aurora_get_target(['NonCompRegistry']), '_aurora_alignment_gap', 0.271)
    setattr(_aurora_get_target(['NonCompRegistry']), '_aurora_alignment_target_score', 1.192)

def all_constraints_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_noncomp_registry.NonCompRegistry.all_constraints', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_noncomp_registry_noncompregistry_all_constraints')(payload=payload, **kwargs)

if _aurora_get_target(['NonCompRegistry', 'all_constraints']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['NonCompRegistry.all_constraints'] = _aurora_get_target(['NonCompRegistry', 'all_constraints'])
    _aurora_assign_target(['NonCompRegistry', 'all_constraints'], _aurora_make_override('all_constraints_evolved', 'NonCompRegistry.all_constraints'))
    _AURORA_NATIVE_EVOLVED_LAST['NonCompRegistry.all_constraints'] = {'alignment_gap': 0.56, 'override_active': True}

def operatorparams_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_noncomp_registry.OperatorParams', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_noncomp_registry_operatorparams')(payload=payload, **kwargs)

if _aurora_get_target(['OperatorParams']) is not None:
    setattr(_aurora_get_target(['OperatorParams']), 'evolved_reflection', staticmethod(operatorparams_evolved))
    setattr(_aurora_get_target(['OperatorParams']), '_aurora_alignment_gap', 0.271)
    setattr(_aurora_get_target(['OperatorParams']), '_aurora_alignment_target_score', 1.192)

def polarityparams_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_noncomp_registry.PolarityParams', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_noncomp_registry_polarityparams')(payload=payload, **kwargs)

if _aurora_get_target(['PolarityParams']) is not None:
    setattr(_aurora_get_target(['PolarityParams']), 'evolved_reflection', staticmethod(polarityparams_evolved))
    setattr(_aurora_get_target(['PolarityParams']), '_aurora_alignment_gap', 0.271)
    setattr(_aurora_get_target(['PolarityParams']), '_aurora_alignment_target_score', 1.192)

def systemconstraintstates_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_noncomp_registry.SystemConstraintStates', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_noncomp_registry_systemconstraintstates')(payload=payload, **kwargs)

if _aurora_get_target(['SystemConstraintStates']) is not None:
    setattr(_aurora_get_target(['SystemConstraintStates']), 'evolved_reflection', staticmethod(systemconstraintstates_evolved))
    setattr(_aurora_get_target(['SystemConstraintStates']), '_aurora_alignment_gap', 0.271)
    setattr(_aurora_get_target(['SystemConstraintStates']), '_aurora_alignment_target_score', 1.192)

AURORA_NATIVE_EVOLVED_EXPORTS = {'aurora_internal.aurora_noncomp_registry.ConstraintState': 'constraintstate_evolved',
 'aurora_internal.aurora_noncomp_registry.NonCompDimension': 'noncompdimension_evolved',
 'aurora_internal.aurora_noncomp_registry.NonCompRegistry': 'noncompregistry_evolved',
 'aurora_internal.aurora_noncomp_registry.NonCompRegistry.all_constraints': 'all_constraints_evolved',
 'aurora_internal.aurora_noncomp_registry.OperatorParams': 'operatorparams_evolved',
 'aurora_internal.aurora_noncomp_registry.PolarityParams': 'polarityparams_evolved',
 'aurora_internal.aurora_noncomp_registry.SystemConstraintStates': 'systemconstraintstates_evolved'}
AURORA_NATIVE_EVOLUTION_OVERRIDES = {'aurora_internal.aurora_noncomp_registry.ConstraintState': {'export': 'constraintstate_evolved',
                                                             'mode': 'class_reflection_hook',
                                                             'target': 'ConstraintState'},
 'aurora_internal.aurora_noncomp_registry.NonCompDimension': {'export': 'noncompdimension_evolved',
                                                              'mode': 'class_reflection_hook',
                                                              'target': 'NonCompDimension'},
 'aurora_internal.aurora_noncomp_registry.NonCompRegistry': {'export': 'noncompregistry_evolved',
                                                             'mode': 'class_reflection_hook',
                                                             'target': 'NonCompRegistry'},
 'aurora_internal.aurora_noncomp_registry.NonCompRegistry.all_constraints': {'export': 'all_constraints_evolved',
                                                                             'mode': 'callable_override',
                                                                             'target': 'NonCompRegistry.all_constraints'},
 'aurora_internal.aurora_noncomp_registry.OperatorParams': {'export': 'operatorparams_evolved',
                                                            'mode': 'class_reflection_hook',
                                                            'target': 'OperatorParams'},
 'aurora_internal.aurora_noncomp_registry.PolarityParams': {'export': 'polarityparams_evolved',
                                                            'mode': 'class_reflection_hook',
                                                            'target': 'PolarityParams'},
 'aurora_internal.aurora_noncomp_registry.SystemConstraintStates': {'export': 'systemconstraintstates_evolved',
                                                                    'mode': 'class_reflection_hook',
                                                                    'target': 'SystemConstraintStates'}}
# AURORA_EVOLVED_NATIVE_END

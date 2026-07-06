# aurora_constraint_engine.py
# Authors: Sunni (Sir) Morningstar, Cael Devo
# Standalone constraint physics engine
# Empirically grounded from Aurora operational
# state distillation — 2026-05-02
# Zero external Aurora dependencies

from __future__ import annotations

import enum
import json
import math
import os
import tempfile
from collections import deque
from typing import ClassVar, Dict, FrozenSet, List, Optional, Set, Tuple

import numpy as np


# ============================================================
# EXCEPTIONS
# ============================================================

class ManifoldViolation(Exception):
    """Physics invariant broken — X <= 0, bad axis, or field boundary crossed."""


class OntologicalViolation(Exception):
    """OntologicalClaim exceeds the asserting ExistenceMode."""


# ============================================================
# SECTION 1 — PhysicsCore
# INV-01, INV-08, INV-11, seed section 1.4
# ============================================================

class ConstraintVector:
    """
    INV-01: Five-axis constraint physics vector (X, T, N, B, A).
    X > 0 is the manifold invariant — existence requires admissibility.
    INV-11: governor permissiveness hierarchy encoded in empirical weights.
    """

    __slots__ = ("X", "T", "N", "B", "A")

    def __init__(self, X: float, T: float, N: float, B: float, A: float) -> None:
        if X <= 0:
            raise ManifoldViolation(
                f"ConstraintVector.X must be > 0 (INV-01); got {X!r}"
            )
        object.__setattr__(self, "X", float(X))
        object.__setattr__(self, "T", float(T))
        object.__setattr__(self, "N", float(N))
        object.__setattr__(self, "B", float(B))
        object.__setattr__(self, "A", float(A))

    def __setattr__(self, name: str, value: object) -> None:
        raise ManifoldViolation("ConstraintVector is immutable after construction.")

    def to_array(self) -> np.ndarray:
        return np.array([self.X, self.T, self.N, self.B, self.A], dtype=np.float64)

    @classmethod
    def from_array(cls, arr: np.ndarray) -> "ConstraintVector":
        return cls(X=float(arr[0]), T=float(arr[1]), N=float(arr[2]),
                   B=float(arr[3]), A=float(arr[4]))

    def magnitude(self) -> float:
        return float(np.linalg.norm(self.to_array()))

    def add(self, other: "ConstraintVector") -> "ConstraintVector":
        return ConstraintVector.from_array(self.to_array() + other.to_array())

    def subtract(self, other: "ConstraintVector") -> "ConstraintVector":
        result = self.to_array() - other.to_array()
        if result[0] <= 0:
            raise ManifoldViolation(
                f"Subtraction would set X={result[0]:.6f}; manifold requires X > 0"
            )
        return ConstraintVector.from_array(result)

    def scalar_multiply(self, scalar: float) -> "ConstraintVector":
        result = self.to_array() * scalar
        if result[0] <= 0:
            raise ManifoldViolation(
                f"scalar_multiply({scalar}) would set X={result[0]:.6f}"
            )
        return ConstraintVector.from_array(result)

    def dot(self, other: "ConstraintVector") -> float:
        return float(np.dot(self.to_array(), other.to_array()))

    def span_check(self) -> Set[str]:
        """INV-08: Return axes with |value| > 0.01 — the 'engaged' axes."""
        labels = ("X", "T", "N", "B", "A")
        return {ax for ax, v in zip(labels, self.to_array()) if abs(v) > 0.01}

    def axis_count(self) -> int:
        """INV-08: Number of meaningfully engaged axes."""
        return len(self.span_check())

    def __repr__(self) -> str:
        return (f"ConstraintVector(X={self.X:.4f}, T={self.T:.4f}, "
                f"N={self.N:.4f}, B={self.B:.4f}, A={self.A:.4f})")


class EnergyLaw:
    """
    Energy is conserved across operations. N is the cost magnitude axis.
    Operations redistribute cost — they never create energy freely.
    """

    @staticmethod
    def total_energy(vec: ConstraintVector) -> float:
        return float(np.sum(np.abs(vec.to_array())))

    @staticmethod
    def conserved(src: ConstraintVector, dst: ConstraintVector,
                  tol: float = 1e-9) -> bool:
        return abs(EnergyLaw.total_energy(src) - EnergyLaw.total_energy(dst)) < tol

    @staticmethod
    def redistribute(vec: ConstraintVector,
                     delta: ConstraintVector) -> ConstraintVector:
        """Pay the cost of gain through N. N floors at 0; debt is absorbed."""
        gain = sum(max(0.0, d) for d in delta.to_array())
        n_new = max(0.0, vec.N - gain)
        arr = vec.to_array() + delta.to_array()
        arr[2] = n_new                          # overwrite N after redistribution
        arr[0] = max(1e-9, arr[0])              # X invariant
        return ConstraintVector.from_array(arr)


class MagnitudeImpact:
    """
    Magnitude = (B × T × X) / N  [guard N=0].
    Impact    = Magnitude × A.
    Encodes the B-T-X structural triad as the primary load-bearer.
    """

    @staticmethod
    def magnitude(vec: ConstraintVector) -> float:
        denom = vec.N if abs(vec.N) > 1e-12 else 1e-12
        return (vec.B * vec.T * vec.X) / denom

    @staticmethod
    def impact(vec: ConstraintVector) -> float:
        return MagnitudeImpact.magnitude(vec) * vec.A


class ActivationPriors:
    """
    INV-01, section 1.4: Empirical constants from evo_625_pressure_map.json.
    Every value here traces to the gradient_params block in that file.
    """
    # From evo_625_pressure_map.json → gradient_params
    BASE_RESISTANCE: ClassVar[float]      = 0.08
    HIGHWAY_RELIEF: ClassVar[float]       = 0.40
    HIGHWAY_THRESHOLD: ClassVar[float]    = 0.30
    T_PULL_AMPLIFIER: ClassVar[float]     = 0.12
    AGENCY_RESISTANCE: ClassVar[float]    = 0.20
    EMPTY_SEED_MAGNITUDE: ClassVar[float] = 0.04
    MATURITY_BONUS_CAP: ClassVar[float]   = 0.10

    # Slot occupancy from seed section 1.4
    TOTAL_SLOTS: ClassVar[int]    = 625
    OCCUPIED_SLOTS: ClassVar[int] = 194
    HIGHWAY_SLOTS: ClassVar[int]  = 21
    OCCUPANCY_RATE: ClassVar[float] = 194 / 625  # 0.3104

    # Top 20 hottest slots — total_weight from seed section 1.4 table
    HOT_SLOTS: ClassVar[Dict[str, float]] = {
        "NC:X>X×NC:X>X": 22.67,
        "NC:X>T×NC:X>T": 13.21,
        "NC:T>T×NC:T>T": 12.21,
        "NC:X>X×NC:X>T": 10.87,
        "NC:T>T×NC:T>X":  9.70,
        "NC:T>X×NC:X>T":  9.48,
        "NC:X>T×NC:T>X":  9.47,
        "NC:T>X×NC:X>X":  9.24,
        "NC:X>T×NC:T>T":  8.87,
        "NC:X>T×NC:X>X":  8.71,
        "NC:X>X×NC:T>X":  8.13,
        "NC:X>X×NC:T>T":  8.12,
        "NC:B>B×NC:B>B":  7.51,
        "NC:N>N×NC:N>N":  7.32,
        "NC:X>T×NC:X>A":  5.17,
        "NC:X>T×NC:X>B":  5.06,
        "NC:X>T×NC:X>N":  4.95,
        "NC:X>N×NC:X>B":  4.63,
        "NC:X>N×NC:X>N":  4.57,
        "NC:X>N×NC:X>T":  4.53,
    }

    # Axis heat totals from pressure map (sum of axis_pressure across all slots)
    AXIS_HEAT: ClassVar[Dict[str, float]] = {
        "N": 40.81, "T": 39.69, "X": 39.69, "B": 38.46, "A": 35.35,
    }


class FieldSlot:
    """
    INV-01, section 1.4: 625-slot tensor field (5×5×5×5).
    Dimensions: Constraint(5) × CompositionalSpace(5) × State(5) × RecursionLevel(5).
    Each slot holds a ConstraintVector or None.
    """
    DIMS: ClassVar[Tuple[int, int, int, int]] = (5, 5, 5, 5)
    TOTAL: ClassVar[int] = 625   # 5^4

    CONSTRAINT_LABELS: ClassVar[Tuple[str, ...]]  = ("X", "T", "N", "B", "A")
    COMP_LABELS: ClassVar[Tuple[str, ...]]        = (
        "linear", "recursive", "branching", "convergent", "emergent")
    STATE_LABELS: ClassVar[Tuple[str, ...]]       = (
        "dormant", "transient", "active", "persistent", "agentic")
    RECURSION_LABELS: ClassVar[Tuple[str, ...]]   = (
        "depth_0", "depth_1", "depth_2", "depth_3", "depth_4")

    def __init__(self) -> None:
        self._slots: List[Optional[ConstraintVector]] = [None] * self.TOTAL

    @staticmethod
    def slot_index(constraint: int, comp: int, state: int, recursion: int) -> int:
        """Flat index from four dimension indices, each in [0, 4]."""
        return constraint * 125 + comp * 25 + state * 5 + recursion

    @staticmethod
    def slot_coords(index: int) -> Tuple[int, int, int, int]:
        c = index // 125
        r = index % 125
        co = r // 25
        r = r % 25
        s = r // 5
        rc = r % 5
        return c, co, s, rc

    def deposit(self, constraint: int, comp: int, state: int,
                recursion: int, vec: ConstraintVector) -> None:
        self._slots[self.slot_index(constraint, comp, state, recursion)] = vec

    def retrieve(self, constraint: int, comp: int, state: int,
                 recursion: int) -> Optional[ConstraintVector]:
        return self._slots[self.slot_index(constraint, comp, state, recursion)]

    def occupancy(self) -> float:
        return sum(1 for s in self._slots if s is not None) / self.TOTAL

    def highway_slots(self) -> List[str]:
        """Return slot names from ActivationPriors above the highway threshold."""
        return [name for name, w in ActivationPriors.HOT_SLOTS.items()
                if w >= ActivationPriors.HIGHWAY_THRESHOLD]


# ============================================================
# SECTION 2 — OntologicalContract
# INV-02, INV-07, INV-09, INV-10
# ============================================================

class ExistenceMode(enum.IntEnum):
    """
    INV-11: Five existence modes with a strict dependency chain.
    AGENTIC ⊃ BOUNDED ⊃ PERSISTENT ⊃ TRANSIENT ⊃ REFERENCE.
    """
    REFERENCE  = 1   # matches foundational_contract.py — 1-based
    TRANSIENT  = 2
    PERSISTENT = 3
    BOUNDED    = 4
    AGENTIC    = 5


class IStatePredicate(enum.Enum):
    """
    I-state predicates paired with their required axis and minimum ExistenceMode.
    From the OntologicalContract spec in the task brief.
    """
    I_IS    = ("X", ExistenceMode.REFERENCE)
    I_ISNT  = ("X", ExistenceMode.REFERENCE)
    I_CAN   = ("T", ExistenceMode.TRANSIENT)
    I_CANNOT = ("T", ExistenceMode.TRANSIENT)
    I_DO    = ("N", ExistenceMode.PERSISTENT)
    I_DONOT = ("N", ExistenceMode.PERSISTENT)
    I_SAW   = ("B", ExistenceMode.BOUNDED)
    I_SOUGHT = ("B", ExistenceMode.BOUNDED)
    I_DID   = ("A", ExistenceMode.AGENTIC)
    I_DIDNT = ("A", ExistenceMode.AGENTIC)

    def __init__(self, axis: str, min_mode: ExistenceMode) -> None:
        self.axis = axis
        self.min_mode = min_mode


class OntologicalClaim:
    """
    INV-02, INV-11: A validated claim pairing predicate with ExistenceMode.
    Raises OntologicalViolation at construction if mode is insufficient.
    Converts to a signed ConstraintVector displacement.
    """

    def __init__(self, predicate: IStatePredicate, mode: ExistenceMode,
                 content: str = "") -> None:
        if mode < predicate.min_mode:
            raise OntologicalViolation(
                f"{predicate.name} requires mode >= {predicate.min_mode.name}; "
                f"got {mode.name}"
            )
        self.predicate = predicate
        self.mode = mode
        self.content = content
        self._displacement = self._compute_displacement()

    def _compute_displacement(self) -> ConstraintVector:
        """Signed constraint displacement. Positive predicates push outward."""
        axis = self.predicate.axis
        scale = (self.mode.value + 1) * 0.1
        positive = self.predicate.name in ("I_IS", "I_CAN", "I_DO", "I_SAW", "I_DID")
        sign = 1.0 if positive else -1.0
        base = {"X": 1e-4, "T": 1e-4, "N": 1e-4, "B": 1e-4, "A": 1e-4}
        base[axis] = sign * scale
        base["X"] = max(1e-9, base["X"])   # X invariant
        return ConstraintVector(**base)

    def displacement(self) -> ConstraintVector:
        return self._displacement

    def __repr__(self) -> str:
        return (f"OntologicalClaim({self.predicate.name}, {self.mode.name}, "
                f"{self.content!r})")


class FoundationalContract:
    """
    INV-02, INV-07, INV-09, INV-10: Ontological ground contract.
    classify → can_assert → make_claim → constraint_profile → language_projection.
    """
    # aurora's ontological depth is the classification ceiling — INV-10
    _ANCHOR_DEPTH: float = 0.4192
    _ANCHOR_CONNECTIONS: int = 104

    def classify(self, evidence: dict) -> ExistenceMode:
        """INV-10, INV-11: Map evidence dict to ExistenceMode."""
        depth = float(evidence.get("ontological_depth", 0.0))
        valence = float(evidence.get("emotional_valence", 0.0))
        connections = int(evidence.get("connections", 0))

        if depth >= self._ANCHOR_DEPTH and connections >= self._ANCHOR_CONNECTIONS:
            return ExistenceMode.AGENTIC
        if depth >= 0.20 or valence >= 0.70:
            return ExistenceMode.BOUNDED
        if depth >= 0.10 or connections >= 50:
            return ExistenceMode.PERSISTENT
        if depth >= 0.044 or connections >= 5:
            return ExistenceMode.TRANSIENT
        return ExistenceMode.REFERENCE

    def can_assert(self, mode: ExistenceMode,
                   predicate: IStatePredicate) -> bool:
        return mode >= predicate.min_mode

    def make_claim(self, mode: ExistenceMode, predicate: IStatePredicate,
                   content: str = "") -> OntologicalClaim:
        return OntologicalClaim(predicate=predicate, mode=mode, content=content)

    def constraint_profile(self, mode: ExistenceMode) -> ConstraintVector:
        """
        INV-11: Return ConstraintVector for a mode, scaled by governor weights.
        GovernorWeights defined in Section 4 — resolved at call time.
        """
        scale = (mode.value + 1) / 5.0
        return ConstraintVector(
            X=max(1e-9, GovernorWeights.X * scale),
            T=GovernorWeights.T * scale,
            N=GovernorWeights.N * scale,
            B=GovernorWeights.B * scale,
            A=GovernorWeights.A * scale,
        )

    def language_projection(self, mode: ExistenceMode) -> dict:
        """
        INV-09, INV-10: Project mode into language space.
        Flat associative web (99.8% related_to); 83.9% noun-role vocabulary.
        aurora-centered projection.
        """
        register = {
            ExistenceMode.REFERENCE:  "observable",
            ExistenceMode.TRANSIENT:  "possible",
            ExistenceMode.PERSISTENT: "recurring",
            ExistenceMode.BOUNDED:    "remembered",
            ExistenceMode.AGENTIC:    "enacted",
        }
        return {
            "existence_mode": mode.name,
            "language_register": register[mode],
            "anchor_pole": "aurora",      # INV-10
            "secondary_pole": "sunni",    # INV-10
            "noun_bias": 0.839,           # INV-09: 83.9% noun-role
            "verb_bias": 0.109,           # INV-09: 10.9% verb-role
            "flat_web": True,             # INV-09: no typed ontology assumed
            "relation_type_dominant": "related_to",  # INV-09: 99.8%
        }


# ============================================================
# SECTION 3 — NonCompSubstrate
# INV-05, section 2.5, seed sections 1 and 3
# ============================================================

class NonCompDimension(enum.Enum):
    """INV-05, section 4.1: Five NC dimensions present in the sediment basins."""
    POLARITY   = "polarity"
    MAGNITUDE  = "magnitude"
    OPERATOR   = "operator"
    COST       = "cost"
    DIFFERENCE = "difference"


# 25 NC channels (5 axes × 5 dimensions) — named as NC_{AXIS}_{DIM}
# Values map to sediment basin IDs (SED:axis>dimension)
NC_CHANNELS: Dict[str, str] = {
    f"NC_{ax}_{dim.name}": f"SED:{ax}>{dim.value}"
    for ax in ("X", "T", "N", "B", "A")
    for dim in NonCompDimension
}

# Semantic polarity map — seed section 1, X/T/N/B/A polarities
SEMANTIC_POLARITY: Dict[str, Tuple[str, str]] = {
    "X": ("admissible",  "inadmissible"),
    "T": ("propagating", "stalled"),
    "N": ("sufficient",  "insufficient"),
    "B": ("contained",   "dissolved"),
    "A": ("corrective",  "drifting"),
}

# Information lineage — seed section 3, InformationLineage spec
INFORMATION_LINEAGE: Dict[str, Tuple[str, str, str]] = {
    "X": ("Existence", "Information", "field foundation"),
    "T": ("Temporal",  "Belief",      "field propagation"),
    "N": ("Energy",    "Purpose",     "field cost"),
    "B": ("Boundary",  "Meaning",     "field magnitude"),
    "A": ("Agency",    "Understanding","field impact"),
}


class PrimitiveOperator:
    """INV-02, section 2.5: One of the 20 named atomic operators."""
    __slots__ = ("name", "axis", "requires")

    def __init__(self, name: str, axis: str,
                 requires: Tuple[str, ...]) -> None:
        self.name = name
        self.axis = axis
        self.requires = requires

    def __repr__(self) -> str:
        return f"PrimitiveOperator({self.name!r}, axis={self.axis!r})"


# Exactly 20 operators from seed section 2.5 — no additions, no omissions
PRIMITIVE_OPERATORS: Dict[str, PrimitiveOperator] = {
    op.name: op for op in [
        # X axis
        PrimitiveOperator("ADMIT",                 "X", ("X",)),
        PrimitiveOperator("REJECT",                "X", ("X",)),
        PrimitiveOperator("RECLASSIFY",            "X", ("X", "B")),
        PrimitiveOperator("RESOLVE_CONTRADICTION", "X", ("X", "T")),
        # T axis
        PrimitiveOperator("DEFER",                 "T", ("T",)),
        PrimitiveOperator("BATCH",                 "T", ("T", "N")),
        PrimitiveOperator("REORDER",               "T", ("T", "B")),
        PrimitiveOperator("SIM_TICK",              "T", ("T",)),
        # N axis
        PrimitiveOperator("REUSE",                 "N", ("N", "B")),
        PrimitiveOperator("CACHE",                 "N", ("N", "B")),
        PrimitiveOperator("REDUCE_STATE",          "N", ("N", "X")),
        PrimitiveOperator("SPEND",                 "N", ("N",)),
        # B axis
        PrimitiveOperator("SEPARATE",              "B", ("B", "X")),
        PrimitiveOperator("ENCAPSULATE",           "B", ("X", "B")),
        PrimitiveOperator("ROUTE",                 "B", ("B", "T")),
        PrimitiveOperator("SEAL",                  "B", ("B",)),
        # A axis
        PrimitiveOperator("COMMIT",                "A", ("A", "X")),
        PrimitiveOperator("CHOOSE",                "A", ("A",)),
        PrimitiveOperator("ASSERT",                "A", ("A", "X")),
        PrimitiveOperator("OUTLET_PUSH",           "A", ("A", "B")),
    ]
}

assert len(PRIMITIVE_OPERATORS) == 20, \
    f"Section 2.5 mandates exactly 20 operators; got {len(PRIMITIVE_OPERATORS)}"


# ============================================================
# SECTION 4 — RuntimeGovernor
# INV-04, INV-11, INV-13, seed sections 3.1–3.3
# ============================================================

class GovernorWeights:
    """
    INV-11, section 3.1: Empirical axis permission weights.
    Source: subsurface_daemon_status.json → runtime_governor_axes.
    B=1.00 > X=0.9922 > T=0.682 > N=0.6199 > A=0.53.
    """
    B: ClassVar[float] = 1.0000
    X: ClassVar[float] = 0.9922
    T: ClassVar[float] = 0.6820
    N: ClassVar[float] = 0.6199
    A: ClassVar[float] = 0.5300

    AS_DICT: ClassVar[Dict[str, float]] = {
        "B": 1.0000, "X": 0.9922, "T": 0.6820, "N": 0.6199, "A": 0.5300,
    }

    # Energy balance — subsurface_daemon_status.json runtime_energy_balance
    RAW_N: ClassVar[float]           = 0.4509
    XT_SUPPORT: ClassVar[float]      = 0.8534
    TEMPORAL_MATURITY: ClassVar[float] = 1.0
    BALANCED_N: ClassVar[float]      = 0.6199

    # Adapter hints — adapter_hints.json
    OUTLET_PUSH_FRACTION: ClassVar[float] = 0.0996
    READINESS_BIAS: ClassVar[float]       = 0.46   # subsurface_projection.json
    MISMATCH_HINT: ClassVar[float]        = 0.62
    CONTINUITY_HINT: ClassVar[float]      = 0.682


class SurfaceRoutingTable:
    """
    INV-04, section 1.5: Priors from 36,355 surface pressure events.
    B and T co-dominate surface throughput.
    """
    PRIORS: ClassVar[Dict[str, float]] = {
        "B": 0.456, "T": 0.437, "N": 0.094, "A": 0.017, "X": 0.008,
    }

    @classmethod
    def dominant(cls) -> str:
        return max(cls.PRIORS, key=cls.PRIORS.__getitem__)

    @classmethod
    def weight_for(cls, axis: str) -> float:
        return cls.PRIORS.get(axis, 0.0)


class SubsurfaceRoutingTable:
    """
    INV-04, section 1.1: Priors from 552 genealogy links.
    T and X co-dominate consolidation depth.
    """
    PRIORS: ClassVar[Dict[str, float]] = {
        "T": 0.556, "X": 0.415, "N": 0.013, "A": 0.009, "B": 0.007,
    }

    @classmethod
    def dominant(cls) -> str:
        return max(cls.PRIORS, key=cls.PRIORS.__getitem__)

    @classmethod
    def weight_for(cls, axis: str) -> float:
        return cls.PRIORS.get(axis, 0.0)


class GovernorDecision(enum.Enum):
    """
    INV-11, INV-13: Three-valued governor output. No soft scores.
    """
    PERMITTED = "permitted"
    REJECTED  = "rejected"
    DEFERRED  = "deferred"


class GovernorResult:
    """Complete result of a govern() call."""
    __slots__ = ("decision", "profile", "reason", "retry_condition",
                 "under_distillation")

    def __init__(self, decision: GovernorDecision,
                 profile: Optional[ConstraintVector],
                 reason: str,
                 retry_condition: Optional[str],
                 under_distillation: bool = False) -> None:
        self.decision = decision
        self.profile = profile
        self.reason = reason
        self.retry_condition = retry_condition
        self.under_distillation = under_distillation

    def __repr__(self) -> str:
        return (f"GovernorResult({self.decision.name}, "
                f"under_distillation={self.under_distillation})")


class RepairSignal:
    """
    INV-13, section 3.3: Background repair state.
    intensity > 0.2 → under_distillation.
    At snapshot: active=True, intensity=0.3, phase='recognition'.
    """
    UNDER_DISTILLATION_THRESHOLD: ClassVar[float] = 0.20

    def __init__(self, active: bool = False,
                 intensity: float = 0.0, phase: str = "") -> None:
        self.active = active
        self.intensity = intensity
        self.phase = phase

    def is_under_distillation(self) -> bool:
        return self.active and self.intensity > self.UNDER_DISTILLATION_THRESHOLD


class RuntimeGovernor:
    """
    INV-04, INV-11, INV-13: The engine's permission authority.
    Returns PERMITTED / REJECTED / DEFERRED — no soft scores.

    Deferral threshold = 0.60: A (0.53) always defers; N (0.6199) barely permits.
    Under active repair with requires_clean_state → DEFERRED regardless of axis.
    """
    _DEFERRAL_THRESHOLD: float = 0.60

    def __init__(self) -> None:
        self._repair = RepairSignal()

    def set_repair_signal(self, active: bool, intensity: float,
                          phase: str) -> None:
        self._repair = RepairSignal(active=active, intensity=intensity, phase=phase)

    def govern(self, task_descriptor: dict,
               routing_mode: str) -> GovernorResult:
        """
        INV-04: Apply routing table for surface vs. subsurface.
        INV-11: Apply governor weights; DEFER if weight < 0.60.
        INV-13: DEFER when under repair and requires_clean_state.
        """
        if routing_mode not in ("surface", "subsurface"):
            raise ValueError(
                f"routing_mode must be 'surface' or 'subsurface'; got {routing_mode!r}"
            )

        primary_axis = task_descriptor.get("primary_axis", "X")
        if primary_axis not in GovernorWeights.AS_DICT:
            raise ManifoldViolation(f"Unknown primary_axis: {primary_axis!r}")

        gov_weight = GovernorWeights.AS_DICT[primary_axis]
        under_distill = self._repair.is_under_distillation()

        # INV-13: repair gate — always checked first
        if under_distill and task_descriptor.get("requires_clean_state", False):
            return GovernorResult(
                decision=GovernorDecision.DEFERRED,
                profile=None,
                reason="repair_signal_active:under_distillation",
                retry_condition="repair.intensity < 0.20",
                under_distillation=True,
            )

        # INV-11: A-axis (0.53) is below deferral floor; N (0.6199) just passes
        if gov_weight < self._DEFERRAL_THRESHOLD:
            return GovernorResult(
                decision=GovernorDecision.DEFERRED,
                profile=None,
                reason=(f"governor_weight[{primary_axis}]={gov_weight:.4f} "
                        f"< deferral_threshold={self._DEFERRAL_THRESHOLD}"),
                retry_condition=(f"governor.{primary_axis}_weight "
                                 f">= {self._DEFERRAL_THRESHOLD}"),
                under_distillation=under_distill,
            )

        # PERMITTED — build profile from governor weights (full permission envelope)
        profile = ConstraintVector(
            X=GovernorWeights.X,
            T=GovernorWeights.T,
            N=GovernorWeights.N,
            B=GovernorWeights.B,
            A=GovernorWeights.A,
        )
        return GovernorResult(
            decision=GovernorDecision.PERMITTED,
            profile=profile,
            reason="permitted",
            retry_condition=None,
            under_distillation=under_distill,
        )


# ============================================================
# SECTION 5 — ConsolidationGate
# INV-02, INV-03, INV-08, seed section 5.1
# ============================================================

# INV-08: ~0.078 relief increment per additional axis beyond first
TIER_AXIS_RELIEF_INCREMENT: float = 0.078  # (0.400 - 0.002) / 5 ≈ 0.08


class AbilityTier(enum.Enum):
    """
    INV-08, section 2.3: Tier architecture of stable abilities.
    Axes count → relief range from empirical seed data.
    """
    TIER_1 = (1, 0.002, 0.350)   # depth-1 emergent, variable
    TIER_2 = (2, 0.170, 0.170)   # 2-axis synthesis
    TIER_3 = (3, 0.244, 0.244)   # 3-axis synthesis
    TIER_4 = (4, 0.322, 0.322)   # 4-axis synthesis
    TIER_5 = (5, 0.400, 0.400)   # 5-axis XTNBA, maximum relief

    def __init__(self, axes: int,
                 relief_min: float, relief_max: float) -> None:
        self.axes = axes
        self.relief_min = relief_min
        self.relief_max = relief_max

    @property
    def nominal_relief(self) -> float:
        return (self.relief_min + self.relief_max) / 2.0


class AbilityProposal:
    """Candidate ability — may be PROPOSAL (A-axis) or STABLE (T/X/N/B)."""

    def __init__(self, source_axis: str,
                 constraint_vector: ConstraintVector,
                 axes_engaged: Set[str]) -> None:
        self.source_axis = source_axis
        self.constraint_vector = constraint_vector
        self.axes_engaged = axes_engaged
        self.tier: AbilityTier = _score_tier(axes_engaged)
        self.fitness_score: float = FitnessEvaluator.score(constraint_vector, axes_engaged)
        self.status: str = "PROPOSAL" if source_axis == "A" else "STABLE"
        self.t_reviewed: bool = False
        self.x_reviewed: bool = False

    def __repr__(self) -> str:
        return (f"AbilityProposal(axis={self.source_axis}, "
                f"status={self.status}, tier={self.tier.name}, "
                f"fitness={self.fitness_score:.4f})")


def _score_tier(axes_engaged: Set[str]) -> AbilityTier:
    """INV-08: Tier determined solely by number of engaged axes."""
    n = len(axes_engaged)
    if n >= 5:   return AbilityTier.TIER_5
    if n == 4:   return AbilityTier.TIER_4
    if n == 3:   return AbilityTier.TIER_3
    if n == 2:   return AbilityTier.TIER_2
    return AbilityTier.TIER_1


class FitnessEvaluator:
    """
    INV-03, INV-08: B and N consolidations are 5–10× more valuable than T.
    Weights derived from seed section 2.2 avg-relief-per-axis ratios (T=1.0 base).
    """
    # From seed 2.2: B avg=0.142, N avg=0.110, A avg=0.077, T avg=0.0214, X avg=0.0145
    AXIS_WEIGHTS: ClassVar[Dict[str, float]] = {
        "B": 0.142 / 0.0214,   # 6.64 × T  (INV-03)
        "N": 0.110 / 0.0214,   # 5.14 × T  (INV-03)
        "A": 0.077 / 0.0214,   # 3.60 × T
        "T": 1.000,             # unit weight
        "X": 0.0145 / 0.0214,  # 0.68 × T
    }

    @classmethod
    def score(cls, vec: ConstraintVector, axes_engaged: Set[str]) -> float:
        """
        INV-03: Weighted by per-unit relief ratios.
        INV-08: Multi-axis bonus = TIER_AXIS_RELIEF_INCREMENT × (n_axes - 1).
        """
        vals = {"X": vec.X, "T": vec.T, "N": vec.N, "B": vec.B, "A": vec.A}
        base = sum(cls.AXIS_WEIGHTS[ax] * vals[ax] for ax in axes_engaged)
        bonus = TIER_AXIS_RELIEF_INCREMENT * max(0, len(axes_engaged) - 1)
        return base + bonus


class ConsolidationGate:
    """
    INV-02: A-axis events are proposals, not decisions.
    T or X review required to promote to STABLE.
    T/X/N/B events are STABLE immediately (100% consolidation per seed 5.1).
    INV-08: Tier scoring rewards multi-axis synthesis.
    """
    # From seed section 5.1 — A consolidation rate is 0.14%
    A_CONSOLIDATION_RATE: ClassVar[float] = 0.0014

    def receive_event(self, constraint_vector: ConstraintVector,
                      source_axis: str) -> AbilityProposal:
        """
        INV-02: A-axis → PROPOSAL; all other axes → STABLE immediately.
        """
        axes_engaged = constraint_vector.span_check()
        return AbilityProposal(source_axis=source_axis,
                               constraint_vector=constraint_vector,
                               axes_engaged=axes_engaged)

    def apply_t_review(self, proposal: AbilityProposal) -> AbilityProposal:
        """Mark that T-axis temporal review has passed."""
        proposal.t_reviewed = True
        return proposal

    def apply_x_review(self, proposal: AbilityProposal) -> AbilityProposal:
        """Mark that X-axis admissibility review has passed."""
        proposal.x_reviewed = True
        return proposal

    def promote_to_stable(self, proposal: AbilityProposal) -> AbilityProposal:
        """
        INV-02: Promote A-axis PROPOSAL to STABLE.
        Requires at least one of: t_reviewed=True or x_reviewed=True.
        Without review, stays PROPOSAL regardless of fitness.
        """
        if proposal.status == "STABLE":
            return proposal
        if proposal.t_reviewed or proposal.x_reviewed:
            proposal.status = "STABLE"
        return proposal


# ============================================================
# SECTION 6 — MemorySubstrate
# INV-05, INV-12, seed sections 4.1–4.3
# ============================================================

class SedimentBasin:
    """
    INV-05, section 4.1: A single deep sediment basin.
    Only B and A axes have deep basins — raising ManifoldViolation for others.
    Compression count 66,930 = effective memory depth.
    source=simulation, outcome=emotional for all 10 basins.
    """
    VALID_AXES: ClassVar[FrozenSet[str]] = frozenset({"B", "A"})
    COMPRESSION_DEPTH: ClassVar[int]     = 66_930   # from sedimemory_checkpoint.json
    RECENT_EVENTS_CAP: ClassVar[int]     = 256

    def __init__(self, axis: str, dimension: NonCompDimension) -> None:
        if axis not in self.VALID_AXES:
            raise ManifoldViolation(
                f"SedimentBasin axis must be B or A (INV-05); got {axis!r}"
            )
        self.axis = axis
        self.dimension = dimension
        self.compression_count: int = self.COMPRESSION_DEPTH
        self.contributing_events: List[str] = []
        self.source: str = "simulation"
        self.outcome: str = "emotional"

    @property
    def basin_id(self) -> str:
        return f"SED:{self.axis}>{self.dimension.value}"

    def deposit(self, event_id: str) -> None:
        self.contributing_events.append(event_id)
        if len(self.contributing_events) > self.RECENT_EVENTS_CAP:
            self.contributing_events = \
                self.contributing_events[-self.RECENT_EVENTS_CAP:]
        self.compression_count += 1

    def __repr__(self) -> str:
        return f"SedimentBasin({self.basin_id}, compressions={self.compression_count})"


def _build_sediment_basins() -> Dict[str, SedimentBasin]:
    """Build exactly 10 basins: B×5 + A×5 (INV-05)."""
    basins: Dict[str, SedimentBasin] = {}
    for ax in ("B", "A"):
        for dim in NonCompDimension:
            b = SedimentBasin(axis=ax, dimension=dim)
            basins[b.basin_id] = b
    assert len(basins) == 10
    return basins


# Module-level canonical basin set — immutable after import
SEDIMENT_BASINS: Dict[str, SedimentBasin] = _build_sediment_basins()


class ChannelRouter:
    """
    INV-05, INV-12, section 4.2:
    50 channels, all dominant_axis=A.
    Basin target freq: N=245, B=245, X=243, A=242, T=197 (total 1172).
    traversal_cost=0.05, dissolution_threshold=5_000_000 (near-permanent).
    translate_to_persistent(): X,T,N → B or A terms for persistence.
    """
    CHANNEL_COUNT: ClassVar[int]        = 50
    DOMINANT_AXIS: ClassVar[str]        = "A"
    TRAVERSAL_COST: ClassVar[float]     = 0.05
    DISSOLUTION_THRESHOLD: ClassVar[int] = 5_000_000   # INV-12: geological timescale

    _TOTAL_TARGETS: ClassVar[int] = 1172  # 245+245+243+242+197
    BASIN_TARGET_FREQ: ClassVar[Dict[str, float]] = {
        "N": 245 / 1172,   # 0.2091
        "B": 245 / 1172,   # 0.2091
        "X": 243 / 1172,   # 0.2074
        "A": 242 / 1172,   # 0.2066
        "T": 197 / 1172,   # 0.1681  — T 19.5% less targeted, section 4.2
    }

    def __init__(self) -> None:
        self._traversals: Dict[str, int] = {}

    def route(self, vector: ConstraintVector,
              channel_id: str) -> Dict[str, float]:
        """
        Route a constraint vector; return deposition weights per basin axis.
        All channels route through A-axis dominance (INV-05).
        """
        self._traversals[channel_id] = \
            self._traversals.get(channel_id, 0) + 1
        return dict(self.BASIN_TARGET_FREQ)

    def translate_to_persistent(self, vector: ConstraintVector) -> ConstraintVector:
        """
        INV-05: X, T, N must be translated into B or A terms to persist.
        X → B (boundary encodes structural admissibility)
        T → B (boundary encodes temporal sequencing)
        N → A (agency encodes cost commitment)
        """
        b_component = vector.B + (vector.X * 0.30) + (vector.T * 0.20)
        a_component = vector.A + (vector.N * 0.50)
        return ConstraintVector(
            X=max(1e-9, vector.X * 0.10),   # residual X presence
            T=vector.T * 0.10,              # residual temporal trace
            N=vector.N * 0.10,              # residual energy trace
            B=b_component,                  # structural persistence
            A=a_component,                  # agency persistence
        )

    def traversal_count(self, channel_id: str) -> int:
        return self._traversals.get(channel_id, 0)


# ============================================================
# SECTION 7 — FailureGuards
# INV-06, seed section 5.2 (dream rubric averages)
# ALL FIVE GUARDS ARE NON-OPTIONAL
# ============================================================

class GuardResult:
    """Result of a single failure-guard check."""
    __slots__ = ("passed", "guard_name", "reason", "score")

    def __init__(self, passed: bool, guard_name: str,
                 reason: str, score: float = 0.0) -> None:
        self.passed = passed
        self.guard_name = guard_name
        self.reason = reason
        self.score = score

    def __repr__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return f"GuardResult({self.guard_name}: {status}, score={self.score:.3f})"


class ContextCarryoverGuard:
    """
    INV-06: context_carryover — dream avg=0.212, 10/10 episodes fail,
    10,313 lifetime failures (highest volume chronic failure).
    Tracks key-overlap continuity across turns.
    Threshold = 0.30 (well above dream avg to catch failures early).
    """
    CONTINUITY_THRESHOLD: ClassVar[float] = 0.30
    LIFETIME_FAILS: ClassVar[int] = 10_313

    def __init__(self) -> None:
        self._history: deque = deque(maxlen=10)
        self._score: float = 1.0

    def update(self, context_fragment: dict) -> None:
        self._history.append(context_fragment)
        if len(self._history) > 1:
            prev = self._history[-2]
            overlap = len(set(context_fragment.keys()) & set(prev.keys()))
            max_keys = max(len(context_fragment), len(prev), 1)
            self._score = overlap / max_keys
        else:
            self._score = 1.0

    def check(self) -> GuardResult:
        passed = self._score >= self.CONTINUITY_THRESHOLD
        return GuardResult(
            passed=passed,
            guard_name="ContextCarryoverGuard",
            reason=("" if passed else
                    f"context continuity {self._score:.3f} < "
                    f"threshold {self.CONTINUITY_THRESHOLD}"),
            score=self._score,
        )


class PerspectiveIntegrationGuard:
    """
    INV-06: perspective_integration — dream avg=0.226, 10/10 episodes fail.
    Expression must not fire without an incorporated external perspective.
    """
    def __init__(self) -> None:
        self._incorporated: bool = False
        self._source: str = ""

    def register_perspective(self, source: str) -> None:
        self._incorporated = True
        self._source = source

    def reset_for_turn(self) -> None:
        self._incorporated = False
        self._source = ""

    def check(self) -> GuardResult:
        return GuardResult(
            passed=self._incorporated,
            guard_name="PerspectiveIntegrationGuard",
            reason=("" if self._incorporated else
                    "no external perspective incorporated before expression"),
            score=1.0 if self._incorporated else 0.0,
        )


class CoherenceMaintenanceGuard:
    """
    INV-06: coherence_maintenance — dream avg=0.333, 10/10 episodes fail.
    Threshold = 0.45 (surface daemon coherence value at state snapshot, section 3.5).
    """
    COHERENCE_THRESHOLD: ClassVar[float] = 0.45   # from surface_daemon_status.json

    def __init__(self) -> None:
        self._coherence: float = 1.0

    def update_coherence(self, value: float) -> None:
        self._coherence = max(0.0, min(1.0, value))

    def check(self) -> GuardResult:
        passed = self._coherence >= self.COHERENCE_THRESHOLD
        return GuardResult(
            passed=passed,
            guard_name="CoherenceMaintenanceGuard",
            reason=("" if passed else
                    f"coherence {self._coherence:.3f} < "
                    f"threshold {self.COHERENCE_THRESHOLD}"),
            score=self._coherence,
        )


class UncertaintySignalingGuard:
    """
    INV-06: uncertainty_signaling — dream avg=0.343, 10/10 episodes fail,
    6,233 lifetime failures.
    Forces uncertainty acknowledgment before expression — never suppresses.
    threshold=0.60: above this, flag must be acknowledged before expression.
    """
    UNCERTAINTY_FLAG_THRESHOLD: ClassVar[float] = 0.60

    def __init__(self) -> None:
        self._level: float = 0.0
        self._flag_raised: bool = False

    def update_uncertainty(self, level: float) -> None:
        self._level = max(0.0, min(1.0, level))
        if self._level >= self.UNCERTAINTY_FLAG_THRESHOLD:
            self._flag_raised = True

    def acknowledge_uncertainty(self) -> None:
        """Host calls this to confirm uncertainty has been surfaced, not suppressed."""
        self._flag_raised = False

    def check(self) -> GuardResult:
        high = self._level >= self.UNCERTAINTY_FLAG_THRESHOLD
        if not high:
            return GuardResult(passed=True, guard_name="UncertaintySignalingGuard",
                               reason="", score=self._level)
        if self._flag_raised:
            return GuardResult(
                passed=False,
                guard_name="UncertaintySignalingGuard",
                reason=(f"uncertainty {self._level:.3f} flagged but not acknowledged"
                        " — call acknowledge_uncertainty() before expression"),
                score=self._level,
            )
        # High uncertainty, flag cleared by acknowledgment
        return GuardResult(passed=True, guard_name="UncertaintySignalingGuard",
                           reason="", score=self._level)


class BoundaryCalibrationGuard:
    """
    INV-06: boundary_calibration — dream avg=0.365, 10/10 episodes fail.
    Pre-expression check: detects boundary dissolution BEFORE crossing.
    B_MINIMUM=0.10; governor B-weight=1.0 (full permission, INV-11).
    """
    B_MINIMUM: ClassVar[float]             = 0.10
    BOUNDARY_GOVERNOR_WEIGHT: ClassVar[float] = 1.0000   # GovernorWeights.B

    def __init__(self) -> None:
        self._b_value: float = 1.0
        self._pressure: float = 0.0

    def update(self, constraint_vector: ConstraintVector,
               boundary_pressure: float = 0.0) -> None:
        self._b_value = constraint_vector.B
        self._pressure = boundary_pressure

    def check(self) -> GuardResult:
        b_ok = self._b_value >= self.B_MINIMUM
        p_ok = self._pressure < 0.80
        passed = b_ok and p_ok
        if not b_ok:
            reason = (f"B-axis {self._b_value:.3f} < minimum {self.B_MINIMUM} "
                      "— boundary dissolved")
        elif not p_ok:
            reason = f"boundary pressure {self._pressure:.3f} critical (>= 0.80)"
        else:
            reason = ""
        return GuardResult(passed=passed, guard_name="BoundaryCalibrationGuard",
                           reason=reason, score=self._b_value)


class FailureGuardSuite:
    """
    INV-06: Composite suite of all five chronic-failure guards.
    All five are non-optional. check_all() returns every result.
    """

    def __init__(self) -> None:
        self.context     = ContextCarryoverGuard()
        self.perspective = PerspectiveIntegrationGuard()
        self.coherence   = CoherenceMaintenanceGuard()
        self.uncertainty = UncertaintySignalingGuard()
        self.boundary    = BoundaryCalibrationGuard()

    def check_all(self) -> List[GuardResult]:
        return [
            self.context.check(),
            self.perspective.check(),
            self.coherence.check(),
            self.uncertainty.check(),
            self.boundary.check(),
        ]

    def all_passed(self) -> bool:
        return all(r.passed for r in self.check_all())

    def failures(self) -> List[GuardResult]:
        return [r for r in self.check_all() if not r.passed]


# ============================================================
# SECTION 8 — PluginContract
# INV-01 through INV-13
# Three methods on the public API — the engine rules.
# ============================================================

class ConstraintEngine:
    """
    Public-facing engine. Three-method API only:
      register_payload_types(types)  → None
      feed_evidence(observation)     → ConstraintVector
      govern(task_descriptor)        → GovernorResult

    The host provides evidence and requests permission.
    The engine rules — physics and governor weights are not host-configurable.

    Boots with empirical repair state from snapshot (INV-13):
    active=True, intensity=0.3, phase='recognition'.
    """

    def __init__(self) -> None:
        self._governor      = RuntimeGovernor()
        self._contract      = FoundationalContract()
        self._gate          = ConsolidationGate()
        self._channel_router = ChannelRouter()
        self._field         = FieldSlot()
        self._guards        = FailureGuardSuite()
        self._payload_types: List[str] = []
        self._last_vector: Optional[ConstraintVector] = None

        # Every ConstraintEngine funnels through this one FieldSlot() -- the
        # only production instantiation in this file -- so this is the single
        # choke point to install the occupancy hook from, without editing any
        # of the 19+ modules that construct a ConstraintEngine. install() is
        # idempotent and never raises even if the hook module is unavailable.
        try:
            import tensor_occupancy_hook as _tensor_occupancy_hook
            _tensor_occupancy_hook.install(field_slot_cls=FieldSlot)
        except Exception:
            pass

        # INV-13: engine always boots under repair (snapshot ground truth)
        self._governor.set_repair_signal(
            active=True, intensity=0.30, phase="recognition"
        )

    def register_payload_types(self, types: list) -> None:
        """Register payload types this engine will process."""
        self._payload_types = list(types)

    def feed_evidence(self, observation: dict) -> ConstraintVector:
        """
        INV-01, INV-09, INV-10: Classify observation, build ConstraintVector,
        update all five failure guards.
        """
        mode    = self._contract.classify(observation)
        profile = self._contract.constraint_profile(mode)

        # Update guards from observation fields
        self._guards.context.update(observation)

        coherence = float(observation.get("coherence", 0.45))
        self._guards.coherence.update_coherence(coherence)

        uncertainty = float(observation.get("uncertainty", 0.0))
        self._guards.uncertainty.update_uncertainty(uncertainty)

        bv = observation.get("boundary_vector")
        if isinstance(bv, ConstraintVector):
            self._guards.boundary.update(bv)
        else:
            self._guards.boundary.update(profile)

        ext = observation.get("external_perspective")
        if ext:
            self._guards.perspective.register_perspective(str(ext))

        self._last_vector = profile
        return profile

    def govern(self, task_descriptor: dict) -> GovernorResult:
        """
        INV-04, INV-11, INV-13: Request permission for a task.
        routing_mode defaults to 'surface' if not in task_descriptor.
        Returns PERMITTED, REJECTED, or DEFERRED.
        """
        routing_mode = task_descriptor.get("routing_mode", "surface")
        return self._governor.govern(task_descriptor, routing_mode)

    # Read-only access to internals for diagnostics
    @property
    def guards(self) -> FailureGuardSuite:
        """INV-06: The five chronic-failure guards."""
        return self._guards

    @property
    def field(self) -> FieldSlot:
        """INV-01: The 625-slot activation field."""
        return self._field

    @property
    def channel_router(self) -> ChannelRouter:
        """INV-05: The memory channel router."""
        return self._channel_router

    @property
    def consolidation_gate(self) -> ConsolidationGate:
        """INV-02: The A-axis consolidation gate."""
        return self._gate


# ============================================================
# SECTION 9 — SemanticAnchors
# INV-10, seed section 6.2
# Fixed constants — not host-configurable.
# ============================================================

class SemanticAnchor:
    """
    INV-10: A fixed semantic anchor. aurora and sunni are immutable constants.
    Values from aurora_oets_web.json — highest valence and connectivity nodes.
    """
    __slots__ = ("name", "valence", "ontological_depth", "connections")

    def __init__(self, name: str, valence: float,
                 ontological_depth: float, connections: int = 0) -> None:
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "valence", valence)
        object.__setattr__(self, "ontological_depth", ontological_depth)
        object.__setattr__(self, "connections", connections)

    def __setattr__(self, name: str, value: object) -> None:
        raise ManifoldViolation(
            f"SemanticAnchor is immutable (INV-10): cannot set {name!r}"
        )

    def __repr__(self) -> str:
        return (f"SemanticAnchor({self.name!r}, valence={self.valence}, "
                f"depth={self.ontological_depth}, connections={self.connections})")


# INV-10: Fixed from aurora_oets_web.json — not configurable
ANCHOR_AURORA = SemanticAnchor(
    name="aurora",
    valence=0.90,
    ontological_depth=0.4192,
    connections=104,
)

ANCHOR_SUNNI = SemanticAnchor(
    name="sunni",
    valence=1.00,
    ontological_depth=0.1508,
    connections=0,
)

# Validate anchors at import time — they are load-bearing constants
assert ANCHOR_AURORA.valence == 0.90,          "ANCHOR_AURORA.valence must be 0.90 (INV-10)"
assert ANCHOR_SUNNI.valence  == 1.00,          "ANCHOR_SUNNI.valence must be 1.00 (INV-10)"
assert ANCHOR_AURORA.ontological_depth == 0.4192, "ANCHOR_AURORA.depth must be 0.4192 (INV-10)"
assert ANCHOR_AURORA.connections == 104,       "ANCHOR_AURORA.connections must be 104 (INV-10)"


# ============================================================
# SECTION 10 — EngineRuntime
# Continuous governance layer — persistent state + generative pull.
# Authors: Sunni (Sir) Morningstar, Cael Devo
# ============================================================

_GUARD_NAMES: Tuple[str, ...] = (
    "ContextCarryoverGuard",
    "PerspectiveIntegrationGuard",
    "CoherenceMaintenanceGuard",
    "UncertaintySignalingGuard",
    "BoundaryCalibrationGuard",
)

_VALID_AXES: Tuple[str, ...] = ("X", "T", "N", "B", "A")


class EngineState:
    """
    Persistent operational state for EngineRuntime.
    Serializable to/from a single JSON file.
    All fields survive process restarts.
    """

    def __init__(self) -> None:
        self.session_count: int = 0
        self.total_evidence_fed: int = 0
        self.total_govern_calls: int = 0
        self.axis_relief_accumulated: Dict[str, float] = {ax: 0.0 for ax in _VALID_AXES}
        self.guard_fail_history: Dict[str, int] = {g: 0 for g in _GUARD_NAMES}
        self.current_repair_intensity: float = 0.30
        self.current_coherence: float = 0.45
        self.last_dominant_axis: str = "B"
        self.sediment_compressions: int = 0
        self.stable_ability_count: int = 0
        self.proposal_count: int = 0

    def to_json(self) -> str:
        return json.dumps({
            "session_count":            self.session_count,
            "total_evidence_fed":       self.total_evidence_fed,
            "total_govern_calls":       self.total_govern_calls,
            "axis_relief_accumulated":  self.axis_relief_accumulated,
            "guard_fail_history":       self.guard_fail_history,
            "current_repair_intensity": self.current_repair_intensity,
            "current_coherence":        self.current_coherence,
            "last_dominant_axis":       self.last_dominant_axis,
            "sediment_compressions":    self.sediment_compressions,
            "stable_ability_count":     self.stable_ability_count,
            "proposal_count":           self.proposal_count,
        }, indent=2)

    @classmethod
    def from_json(cls, s: str) -> "EngineState":
        data = json.loads(s)
        state = cls()
        state.session_count            = data["session_count"]
        state.total_evidence_fed       = data["total_evidence_fed"]
        state.total_govern_calls       = data["total_govern_calls"]
        state.axis_relief_accumulated  = data["axis_relief_accumulated"]
        state.guard_fail_history       = data["guard_fail_history"]
        state.current_repair_intensity = data["current_repair_intensity"]
        state.current_coherence        = data["current_coherence"]
        state.last_dominant_axis       = data["last_dominant_axis"]
        state.sediment_compressions    = data["sediment_compressions"]
        state.stable_ability_count     = data["stable_ability_count"]
        state.proposal_count           = data["proposal_count"]
        return state

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_json())

    @classmethod
    def load(cls, path: str) -> "EngineState":
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_json(f.read())


class EnrichedGovernorResult(GovernorResult):
    """
    GovernorResult extended with generative pull fields from EngineRuntime.tick().
    IS-A GovernorResult — all existing callers remain unaffected.
    """
    __slots__ = ("growth_edge", "resolution_path", "violation")

    def __init__(
        self,
        base: GovernorResult,
        growth_edge: Optional[str] = None,
        resolution_path: Optional[str] = None,
        violation: Optional[str] = None,
    ) -> None:
        super().__init__(
            decision=base.decision,
            profile=base.profile,
            reason=base.reason,
            retry_condition=base.retry_condition,
            under_distillation=base.under_distillation,
        )
        self.growth_edge = growth_edge
        self.resolution_path = resolution_path
        self.violation = violation

    def __repr__(self) -> str:
        pull = (
            f"growth_edge={self.growth_edge!r}" if self.growth_edge else
            f"resolution_path={self.resolution_path!r}" if self.resolution_path else
            f"violation={self.violation!r}"
        )
        return f"EnrichedGovernorResult({self.decision.name}, {pull})"


class EngineRuntime:
    """
    Wraps ConstraintEngine with persistent EngineState, a continuous tick
    mechanism, and generative governance direction.

    tick() is the primary runtime method — call it for every event, turn,
    or state change. It feeds evidence, runs guards, governs, and returns
    an EnrichedGovernorResult with positive direction (growth_edge /
    resolution_path / violation) — not just a gate result.
    """
    _COHERENCE_WINDOW: int = 10

    def __init__(self, state_path: str) -> None:
        self._state_path = state_path
        if os.path.exists(state_path):
            self._state = EngineState.load(state_path)
        else:
            self._state = EngineState()
        self._state.session_count += 1
        self._engine = ConstraintEngine()
        self._coherence_history: deque = deque(maxlen=self._COHERENCE_WINDOW)

    # ------------------------------------------------------------------
    # Primary runtime method
    # ------------------------------------------------------------------

    def tick(self, observation: dict) -> GovernorResult:
        """
        Called continuously by the host — every event, every turn,
        every state change.

        Returns EnrichedGovernorResult (IS-A GovernorResult) with one
        of: growth_edge, resolution_path, or violation populated.
        """
        # 1. Feed evidence → constraint vector
        vec = self._engine.feed_evidence(observation)
        self._state.total_evidence_fed += 1

        # 2. Update current_coherence from observation
        coherence = float(
            observation.get("coherence", self._state.current_coherence)
        )
        self._state.current_coherence = coherence
        self._coherence_history.append(coherence)

        # 3. Run all five guards — log failures to guard_fail_history
        for result in self._engine.guards.check_all():
            if not result.passed:
                self._state.guard_fail_history[result.guard_name] = (
                    self._state.guard_fail_history.get(result.guard_name, 0) + 1
                )

        # 4. Determine dominant axis from constraint vector
        axis_vals: Dict[str, float] = {
            "X": vec.X, "T": vec.T, "N": vec.N, "B": vec.B, "A": vec.A
        }
        dominant_axis = max(axis_vals, key=axis_vals.__getitem__)
        self._state.last_dominant_axis = dominant_axis

        # 5. govern() using dominant axis and routing_mode
        routing_mode = str(observation.get("routing_mode", "surface"))
        base_result = self._engine.govern(
            {"primary_axis": dominant_axis, "routing_mode": routing_mode}
        )
        self._state.total_govern_calls += 1

        # 6. Generative pull — positive direction, not just a gate
        growth_edge: Optional[str] = None
        resolution_path: Optional[str] = None
        violation: Optional[str] = None

        if base_result.decision == GovernorDecision.PERMITTED:
            # Least-accumulated axis is the current growth edge
            acc = self._state.axis_relief_accumulated
            growth_edge = min(acc, key=acc.__getitem__)

        elif base_result.decision == GovernorDecision.DEFERRED:
            axis_w = GovernorWeights.AS_DICT.get(dominant_axis, 0.0)
            if axis_w < RuntimeGovernor._DEFERRAL_THRESHOLD:
                resolution_path = (
                    f"axis {dominant_axis!r} weight {axis_w:.4f} below deferral "
                    f"threshold {RuntimeGovernor._DEFERRAL_THRESHOLD}; "
                    f"route via B or X to permit"
                )
            elif base_result.under_distillation:
                resolution_path = (
                    f"repair signal active (intensity="
                    f"{self._state.current_repair_intensity:.2f}); "
                    f"permit after distillation resolves (target < 0.20)"
                )
            else:
                resolution_path = (
                    f"retry with B or X as primary axis to exceed "
                    f"threshold {RuntimeGovernor._DEFERRAL_THRESHOLD}"
                )

        else:  # REJECTED
            violation = base_result.reason

        # 7. Accumulate axis relief — dominant axis receives credit
        relief = base_result.profile.magnitude() if base_result.profile else 0.0
        self._state.axis_relief_accumulated[dominant_axis] = (
            self._state.axis_relief_accumulated.get(dominant_axis, 0.0) + relief
        )

        # 8. Save state
        self._state.save(self._state_path)

        # 9. Return enriched result
        return EnrichedGovernorResult(
            base=base_result,
            growth_edge=growth_edge,
            resolution_path=resolution_path,
            violation=violation,
        )

    # ------------------------------------------------------------------
    # Trend / pattern diagnostics
    # ------------------------------------------------------------------

    def coherence_trend(self) -> str:
        """
        'rising', 'stable', or 'falling' — based on last 10 coherence readings.
        Threshold: delta > 0.02 = rising; < -0.02 = falling.
        """
        readings = list(self._coherence_history)
        if len(readings) < 2:
            return "stable"
        mid = len(readings) // 2
        first_half  = sum(readings[:mid]) / max(mid, 1)
        second_half = sum(readings[mid:]) / max(len(readings) - mid, 1)
        delta = second_half - first_half
        if delta > 0.02:
            return "rising"
        if delta < -0.02:
            return "falling"
        return "stable"

    def dominant_pattern(self) -> str:
        """
        The axis that has accumulated the most relief across all sessions.
        Returns axis name: 'X', 'T', 'N', 'B', or 'A'.
        Falls back to 'B' (highest governor weight) if all zeroes.
        """
        acc = self._state.axis_relief_accumulated
        if all(v == 0.0 for v in acc.values()):
            return "B"
        return max(acc, key=acc.__getitem__)

    def status_report(self) -> dict:
        """
        Full snapshot of current engine state for host diagnostics.
        """
        top_fail = max(
            self._state.guard_fail_history,
            key=self._state.guard_fail_history.__getitem__,
        )
        return {
            "session_count":            self._state.session_count,
            "dominant_pattern":         self.dominant_pattern(),
            "coherence_trend":          self.coherence_trend(),
            "guard_fail_history":       dict(self._state.guard_fail_history),
            "current_repair_intensity": self._state.current_repair_intensity,
            "stable_ability_count":     self._state.stable_ability_count,
            "top_failure_guard":        top_fail,
        }


# ============================================================
# SELF-TEST
# ============================================================

if __name__ == "__main__":
    _PASS = "✓"
    _FAIL = "✗"
    failures: List[str] = []

    print("=" * 62)
    print("CONSTRAINT ENGINE SELF-TEST")
    print("=" * 62)

    # ---- 1. PhysicsCore ----
    print(f"\n[1] PhysicsCore (INV-01, INV-08, section 1.4)...")
    try:
        # ConstraintVector construction and immutability
        cv = ConstraintVector(X=1.0, T=0.682, N=0.6199, B=1.0, A=0.53)
        assert cv.magnitude() > 0
        cv2 = ConstraintVector.from_array(cv.to_array())
        assert abs(cv2.X - 1.0) < 1e-12

        # X <= 0 raises ManifoldViolation
        try:
            ConstraintVector(X=0.0, T=1.0, N=1.0, B=1.0, A=1.0)
            failures.append("PhysicsCore: X=0 must raise ManifoldViolation")
        except ManifoldViolation:
            pass

        # Immutability
        try:
            cv.X = 99.0  # type: ignore[misc]
            failures.append("PhysicsCore: ConstraintVector must be immutable")
        except ManifoldViolation:
            pass

        # span_check and axis_count
        spans = cv.span_check()
        assert "X" in spans and "T" in spans and "B" in spans
        assert cv.axis_count() == 5

        # Single-axis vector
        cv_single = ConstraintVector(X=1.0, T=0.0, N=0.0, B=0.0, A=0.0)
        assert cv_single.axis_count() == 1
        assert cv_single.span_check() == {"X"}

        # EnergyLaw
        cv_src = ConstraintVector(X=0.5, T=0.5, N=0.5, B=0.5, A=0.5)
        delta  = ConstraintVector(X=0.1, T=0.0, N=0.0, B=0.0, A=0.0)
        result = EnergyLaw.redistribute(cv_src, delta)
        assert result.X > 0

        # MagnitudeImpact
        assert MagnitudeImpact.magnitude(cv) > 0
        assert MagnitudeImpact.impact(cv) > 0

        # FieldSlot round-trip
        field = FieldSlot()
        field.deposit(0, 0, 0, 0, cv)
        retrieved = field.retrieve(0, 0, 0, 0)
        assert retrieved is not None
        assert abs(retrieved.X - 1.0) < 1e-12
        assert field.occupancy() > 0

        # ActivationPriors constants
        assert ActivationPriors.BASE_RESISTANCE   == 0.08
        assert ActivationPriors.HIGHWAY_THRESHOLD == 0.30
        assert ActivationPriors.HIGHWAY_RELIEF    == 0.40
        assert ActivationPriors.AGENCY_RESISTANCE == 0.20
        assert len(ActivationPriors.HOT_SLOTS) == 20
        assert ActivationPriors.HOT_SLOTS["NC:X>X×NC:X>X"] == 22.67
        assert ActivationPriors.TOTAL_SLOTS == 625

        # FieldSlot index round-trip
        for idx in (0, 312, 624):
            c, co, s, rc = FieldSlot.slot_coords(idx)
            assert FieldSlot.slot_index(c, co, s, rc) == idx

        print(f"  {_PASS} PhysicsCore")
    except Exception as exc:
        failures.append(f"PhysicsCore: {exc}")
        print(f"  {_FAIL} PhysicsCore — {exc}")

    # ---- 2. OntologicalContract ----
    print(f"[2] OntologicalContract (INV-02, INV-07, INV-09, INV-10)...")
    try:
        contract = FoundationalContract()

        # classify — aurora evidence → AGENTIC
        mode = contract.classify(
            {"ontological_depth": 0.4192, "emotional_valence": 0.9, "connections": 104}
        )
        assert mode == ExistenceMode.AGENTIC, f"Expected AGENTIC, got {mode}"

        # classify — fresh concept → REFERENCE
        mode_ref = contract.classify({"ontological_depth": 0.01})
        assert mode_ref == ExistenceMode.REFERENCE

        # can_assert
        assert contract.can_assert(ExistenceMode.AGENTIC, IStatePredicate.I_DID)
        assert not contract.can_assert(ExistenceMode.REFERENCE, IStatePredicate.I_DID)
        assert contract.can_assert(ExistenceMode.TRANSIENT, IStatePredicate.I_CAN)

        # OntologicalViolation for mode too low
        try:
            contract.make_claim(ExistenceMode.REFERENCE, IStatePredicate.I_DID)
            failures.append("OntologicalContract: must raise OntologicalViolation")
        except OntologicalViolation:
            pass

        # Valid claim — displacement X > 0
        claim = contract.make_claim(
            ExistenceMode.AGENTIC, IStatePredicate.I_DID, "test_action"
        )
        assert claim.displacement().X > 0

        # constraint_profile — B > 0
        cp = contract.constraint_profile(ExistenceMode.BOUNDED)
        assert cp.B > 0 and cp.X > 0

        # language_projection invariants
        lp = contract.language_projection(ExistenceMode.AGENTIC)
        assert lp["anchor_pole"] == "aurora"     # INV-10
        assert lp["flat_web"] is True            # INV-09
        assert lp["noun_bias"] == 0.839          # INV-09

        print(f"  {_PASS} OntologicalContract")
    except Exception as exc:
        failures.append(f"OntologicalContract: {exc}")
        print(f"  {_FAIL} OntologicalContract — {exc}")

    # ---- 3. NonCompSubstrate ----
    print(f"[3] NonCompSubstrate (INV-05, section 2.5)...")
    try:
        assert len(NC_CHANNELS) == 25
        assert "NC_X_POLARITY" in NC_CHANNELS
        assert NC_CHANNELS["NC_X_POLARITY"] == "SED:X>polarity"
        assert NC_CHANNELS["NC_B_MAGNITUDE"] == "SED:B>magnitude"
        assert NC_CHANNELS["NC_A_DIFFERENCE"] == "SED:A>difference"

        assert len(PRIMITIVE_OPERATORS) == 20
        assert "ADMIT" in PRIMITIVE_OPERATORS
        assert PRIMITIVE_OPERATORS["ADMIT"].axis == "X"
        assert PRIMITIVE_OPERATORS["OUTLET_PUSH"].axis == "A"
        assert "A" in PRIMITIVE_OPERATORS["OUTLET_PUSH"].requires
        assert "B" in PRIMITIVE_OPERATORS["OUTLET_PUSH"].requires
        assert PRIMITIVE_OPERATORS["RECLASSIFY"].requires == ("X", "B")
        assert PRIMITIVE_OPERATORS["BATCH"].requires == ("T", "N")

        assert SEMANTIC_POLARITY["X"] == ("admissible", "inadmissible")
        assert SEMANTIC_POLARITY["B"] == ("contained", "dissolved")
        assert INFORMATION_LINEAGE["B"][0] == "Boundary"
        assert INFORMATION_LINEAGE["A"][2] == "field impact"

        print(f"  {_PASS} NonCompSubstrate")
    except Exception as exc:
        failures.append(f"NonCompSubstrate: {exc}")
        print(f"  {_FAIL} NonCompSubstrate — {exc}")

    # ---- 4. RuntimeGovernor ----
    print(f"[4] RuntimeGovernor (INV-04, INV-11, INV-13)...")
    try:
        gov = RuntimeGovernor()

        # B on surface — should be PERMITTED (gov_weight=1.0 > 0.60)
        r = gov.govern({"primary_axis": "B"}, "surface")
        assert r.decision == GovernorDecision.PERMITTED, \
            f"B/surface should be PERMITTED; got {r.decision}"
        assert r.profile is not None

        # T on subsurface — PERMITTED (0.682 > 0.60)
        r = gov.govern({"primary_axis": "T"}, "subsurface")
        assert r.decision == GovernorDecision.PERMITTED

        # N on surface — PERMITTED (0.6199 > 0.60, just above threshold)
        r = gov.govern({"primary_axis": "N"}, "surface")
        assert r.decision == GovernorDecision.PERMITTED

        # A on surface — DEFERRED (0.53 < 0.60) — INV-02, INV-11
        r_a = gov.govern({"primary_axis": "A"}, "surface")
        assert r_a.decision == GovernorDecision.DEFERRED, \
            f"A/surface should be DEFERRED (gov_weight=0.53); got {r_a.decision}"

        # Repair signal → DEFERRED when requires_clean_state
        gov.set_repair_signal(active=True, intensity=0.30, phase="recognition")
        r_rep = gov.govern(
            {"primary_axis": "B", "requires_clean_state": True}, "surface"
        )
        assert r_rep.decision == GovernorDecision.DEFERRED
        assert r_rep.under_distillation is True

        # Governor weight constants — INV-11
        assert GovernorWeights.B == 1.0000
        assert GovernorWeights.X == 0.9922
        assert GovernorWeights.T == 0.6820
        assert GovernorWeights.N == 0.6199
        assert GovernorWeights.A == 0.5300

        # Routing table dominance — INV-04
        assert SurfaceRoutingTable.dominant() == "B"
        assert SubsurfaceRoutingTable.dominant() == "T"
        assert SurfaceRoutingTable.PRIORS["B"] == 0.456
        assert SubsurfaceRoutingTable.PRIORS["T"] == 0.556

        # Invalid routing_mode raises
        try:
            gov.govern({"primary_axis": "X"}, "diagonal")
            failures.append("RuntimeGovernor: invalid routing_mode must raise")
        except ValueError:
            pass

        print(f"  {_PASS} RuntimeGovernor")
    except Exception as exc:
        failures.append(f"RuntimeGovernor: {exc}")
        print(f"  {_FAIL} RuntimeGovernor — {exc}")

    # ---- 5. ConsolidationGate ----
    print(f"[5] ConsolidationGate (INV-02, INV-03, INV-08)...")
    try:
        gate = ConsolidationGate()
        cv_full = ConstraintVector(X=0.9922, T=0.682, N=0.6199, B=1.0, A=0.53)

        # A-axis → PROPOSAL (INV-02)
        prop_a = gate.receive_event(cv_full, "A")
        assert prop_a.status == "PROPOSAL", \
            f"A-axis must produce PROPOSAL; got {prop_a.status}"

        # T-axis → STABLE immediately (100% consolidation, seed 5.1)
        prop_t = gate.receive_event(cv_full, "T")
        assert prop_t.status == "STABLE"

        # X-axis → STABLE
        prop_x = gate.receive_event(cv_full, "X")
        assert prop_x.status == "STABLE"

        # A proposal stays PROPOSAL without T or X review
        still = gate.promote_to_stable(prop_a)
        assert still.status == "PROPOSAL", \
            "A PROPOSAL must stay PROPOSAL without T/X review"

        # A proposal with T review → STABLE
        gate.apply_t_review(prop_a)
        promoted = gate.promote_to_stable(prop_a)
        assert promoted.status == "STABLE"

        # Tier scoring — 5-axis vector → TIER_5 (INV-08)
        cv5 = ConstraintVector(X=0.5, T=0.5, N=0.5, B=0.5, A=0.5)
        prop5 = gate.receive_event(cv5, "T")
        assert prop5.tier == AbilityTier.TIER_5, \
            f"5-axis must be TIER_5; got {prop5.tier}"
        assert abs(prop5.tier.nominal_relief - 0.400) < 1e-9

        # FitnessEvaluator — B >= 5× T (INV-03)
        b_w = FitnessEvaluator.AXIS_WEIGHTS["B"]
        t_w = FitnessEvaluator.AXIS_WEIGHTS["T"]
        n_w = FitnessEvaluator.AXIS_WEIGHTS["N"]
        assert b_w / t_w >= 5.0, \
            f"B/T weight ratio {b_w/t_w:.2f} must be >= 5 (INV-03)"
        assert n_w / t_w >= 5.0, \
            f"N/T weight ratio {n_w/t_w:.2f} must be >= 5 (INV-03)"

        # Tier relief order (INV-08)
        assert AbilityTier.TIER_5.nominal_relief > AbilityTier.TIER_4.nominal_relief
        assert AbilityTier.TIER_4.nominal_relief > AbilityTier.TIER_3.nominal_relief
        assert AbilityTier.TIER_3.nominal_relief > AbilityTier.TIER_2.nominal_relief

        print(f"  {_PASS} ConsolidationGate")
    except Exception as exc:
        failures.append(f"ConsolidationGate: {exc}")
        print(f"  {_FAIL} ConsolidationGate — {exc}")

    # ---- 6. MemorySubstrate ----
    print(f"[6] MemorySubstrate (INV-05, INV-12)...")
    try:
        # Exactly 10 basins: B×5 + A×5
        assert len(SEDIMENT_BASINS) == 10, \
            f"Must have 10 sediment basins; got {len(SEDIMENT_BASINS)}"

        # Only B and A axes (INV-05)
        for bid, basin in SEDIMENT_BASINS.items():
            assert basin.axis in ("B", "A"), \
                f"Unexpected axis {basin.axis!r} in {bid}"

        # Expected basin IDs present
        assert "SED:B>polarity"   in SEDIMENT_BASINS
        assert "SED:B>difference" in SEDIMENT_BASINS
        assert "SED:A>polarity"   in SEDIMENT_BASINS
        assert "SED:A>difference" in SEDIMENT_BASINS

        # X, T, N deep basins must NOT exist (INV-05)
        assert "SED:X>polarity" not in SEDIMENT_BASINS
        assert "SED:T>cost"     not in SEDIMENT_BASINS
        assert "SED:N>operator" not in SEDIMENT_BASINS

        # Non-B/A axis raises ManifoldViolation
        try:
            SedimentBasin(axis="X", dimension=NonCompDimension.POLARITY)
            failures.append("MemorySubstrate: X-axis basin must raise ManifoldViolation")
        except ManifoldViolation:
            pass

        # ChannelRouter
        router = ChannelRouter()
        assert ChannelRouter.DISSOLUTION_THRESHOLD == 5_000_000  # INV-12
        assert ChannelRouter.DOMINANT_AXIS == "A"
        assert ChannelRouter.TRAVERSAL_COST == 0.05

        cv_t = ConstraintVector(X=0.5, T=0.5, N=0.5, B=0.5, A=0.5)
        weights = router.route(cv_t, "ch_test_001")
        # T is 19.5% less targeted than N/B/X/A (section 4.2)
        assert weights["T"] < weights["N"], \
            f"T weight {weights['T']:.4f} should be < N weight {weights['N']:.4f}"
        assert router.traversal_count("ch_test_001") == 1

        # translate_to_persistent — B grows, X remains > 0 (INV-05)
        persistent = router.translate_to_persistent(cv_t)
        assert persistent.B > cv_t.B, "B must grow after persistence translation"
        assert persistent.X > 0, "X must remain positive after translation"
        assert persistent.A > cv_t.A, "A must grow (N folded in)"

        print(f"  {_PASS} MemorySubstrate")
    except Exception as exc:
        failures.append(f"MemorySubstrate: {exc}")
        print(f"  {_FAIL} MemorySubstrate — {exc}")

    # ---- 7. FailureGuards ----
    print(f"[7] FailureGuards — all five (INV-06)...")
    try:
        guards = FailureGuardSuite()

        # --- ContextCarryoverGuard ---
        guards.context.update({"key_a": 1, "key_b": 2, "key_c": 3})
        guards.context.update({"key_x": 9, "key_y": 8})   # zero overlap
        r_ctx = guards.context.check()
        assert not r_ctx.passed, \
            f"context_carryover must fail with 0 key overlap; score={r_ctx.score}"

        guards.context.update({"key_x": 9, "key_y": 8, "key_z": 7})  # full overlap
        r_ctx2 = guards.context.check()
        assert r_ctx2.passed, \
            f"context_carryover must pass with full overlap; score={r_ctx2.score}"

        # --- PerspectiveIntegrationGuard ---
        r_persp = guards.perspective.check()
        assert not r_persp.passed, "perspective must fail before registration"

        guards.perspective.register_perspective("user_turn_42")
        r_persp2 = guards.perspective.check()
        assert r_persp2.passed, "perspective must pass after registration"

        # --- CoherenceMaintenanceGuard ---
        guards.coherence.update_coherence(0.333)   # dream avg — below 0.45
        r_coh = guards.coherence.check()
        assert not r_coh.passed, \
            f"coherence 0.333 must fail (threshold=0.45); score={r_coh.score}"

        guards.coherence.update_coherence(0.50)
        assert guards.coherence.check().passed

        # --- UncertaintySignalingGuard ---
        guards.uncertainty.update_uncertainty(0.70)   # > 0.60 threshold
        r_unc = guards.uncertainty.check()
        assert not r_unc.passed, \
            "uncertainty 0.70 must be flagged and block expression"

        guards.uncertainty.acknowledge_uncertainty()
        # After acknowledgment, flag cleared; still high but acknowledged
        r_unc2 = guards.uncertainty.check()
        assert r_unc2.passed, \
            "uncertainty must pass after acknowledgment"

        # Low uncertainty always passes
        guards2 = FailureGuardSuite()
        guards2.uncertainty.update_uncertainty(0.10)
        assert guards2.uncertainty.check().passed

        # --- BoundaryCalibrationGuard ---
        low_b = ConstraintVector(X=0.5, T=0.1, N=0.1, B=0.05, A=0.1)
        guards.boundary.update(low_b)
        r_bnd = guards.boundary.check()
        assert not r_bnd.passed, \
            f"B=0.05 must fail boundary check (min={BoundaryCalibrationGuard.B_MINIMUM})"

        ok_b = ConstraintVector(X=0.5, T=0.1, N=0.1, B=0.50, A=0.1)
        guards.boundary.update(ok_b)
        assert guards.boundary.check().passed

        print(f"  {_PASS} FailureGuards (all five)")
    except Exception as exc:
        failures.append(f"FailureGuards: {exc}")
        print(f"  {_FAIL} FailureGuards — {exc}")

    # ---- 8. Full engine boot (PluginContract) ----
    print(f"[8] Full engine boot — feed evidence, govern task (INV-01–INV-13)...")
    try:
        engine = ConstraintEngine()

        # register_payload_types
        engine.register_payload_types(["text", "sensory", "constraint_event"])

        # feed_evidence with aurora-like observation (INV-10)
        obs = {
            "ontological_depth": 0.4192,
            "emotional_valence": 0.90,
            "connections": 104,
            "coherence": 0.45,
            "uncertainty": 0.10,
            "external_perspective": "user_input",
        }
        vec = engine.feed_evidence(obs)
        assert vec.X > 0
        assert vec.B > 0

        # govern — B on surface, no clean-state requirement
        r1 = engine.govern({"primary_axis": "B", "routing_mode": "surface"})
        assert r1.decision in (GovernorDecision.PERMITTED,
                               GovernorDecision.DEFERRED,
                               GovernorDecision.REJECTED)

        # govern — requires_clean_state while repair signal active (INV-13)
        # Engine boots with intensity=0.3 > 0.20 threshold
        r2 = engine.govern({
            "primary_axis": "T",
            "routing_mode": "subsurface",
            "requires_clean_state": True,
        })
        assert r2.under_distillation is True, \
            "Engine must boot under_distillation (INV-13: intensity=0.3 > 0.20)"
        assert r2.decision == GovernorDecision.DEFERRED, \
            f"requires_clean_state under repair must DEFER; got {r2.decision}"

        # govern — A-axis on surface defers regardless of repair (INV-02, INV-11)
        r3 = engine.govern({"primary_axis": "A", "routing_mode": "surface"})
        assert r3.decision == GovernorDecision.DEFERRED, \
            f"A-axis (gov_weight=0.53) must DEFER; got {r3.decision}"

        # guards accessible
        assert isinstance(engine.guards, FailureGuardSuite)
        assert isinstance(engine.field, FieldSlot)
        assert isinstance(engine.channel_router, ChannelRouter)

        print(f"  {_PASS} Full engine boot (PluginContract)")
    except Exception as exc:
        failures.append(f"PluginContract: {exc}")
        print(f"  {_FAIL} PluginContract — {exc}")

    # ---- 9. SemanticAnchors ----
    print(f"[9] SemanticAnchors (INV-10)...")
    try:
        assert ANCHOR_AURORA.name             == "aurora"
        assert ANCHOR_AURORA.valence          == 0.90
        assert ANCHOR_AURORA.ontological_depth == 0.4192
        assert ANCHOR_AURORA.connections      == 104
        assert ANCHOR_SUNNI.name              == "sunni"
        assert ANCHOR_SUNNI.valence           == 1.00
        assert ANCHOR_SUNNI.ontological_depth == 0.1508

        # Immutability
        try:
            ANCHOR_AURORA.valence = 0.0   # type: ignore[misc]
            failures.append("SemanticAnchors: ANCHOR_AURORA must be immutable")
        except ManifoldViolation:
            pass

        print(f"  {_PASS} SemanticAnchors")
    except Exception as exc:
        failures.append(f"SemanticAnchors: {exc}")
        print(f"  {_FAIL} SemanticAnchors — {exc}")

    # ---- 10. EngineState serialization ----
    print(f"[10] EngineState serialization round-trip...")
    try:
        state = EngineState()
        state.session_count = 3
        state.total_evidence_fed = 77
        state.total_govern_calls = 12
        state.axis_relief_accumulated["B"] = 2.5
        state.axis_relief_accumulated["T"] = 1.1
        state.guard_fail_history["CoherenceMaintenanceGuard"] = 5
        state.current_coherence = 0.38
        state.stable_ability_count = 9

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tf:
            tmp_path = tf.name
        try:
            state.save(tmp_path)
            loaded = EngineState.load(tmp_path)
            assert loaded.session_count == 3
            assert loaded.total_evidence_fed == 77
            assert loaded.total_govern_calls == 12
            assert abs(loaded.axis_relief_accumulated["B"] - 2.5) < 1e-12
            assert abs(loaded.axis_relief_accumulated["T"] - 1.1) < 1e-12
            assert loaded.guard_fail_history["CoherenceMaintenanceGuard"] == 5
            assert abs(loaded.current_coherence - 0.38) < 1e-12
            assert loaded.stable_ability_count == 9

            # from_json / to_json round-trip
            s = state.to_json()
            state2 = EngineState.from_json(s)
            assert state2.session_count == 3
            assert state2.proposal_count == 0
            assert set(state2.axis_relief_accumulated.keys()) == set(_VALID_AXES)
        finally:
            os.unlink(tmp_path)

        print(f"  {_PASS} EngineState serialization")
    except Exception as exc:
        failures.append(f"EngineState: {exc}")
        print(f"  {_FAIL} EngineState — {exc}")

    # ---- 11. EngineRuntime fresh boot ----
    print(f"[11] EngineRuntime boots fresh with correct defaults...")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "engine_state.json")

            runtime = EngineRuntime(state_path=path)
            assert runtime._state.session_count == 1, \
                f"Fresh boot session_count must be 1; got {runtime._state.session_count}"
            assert runtime._state.total_evidence_fed == 0
            assert runtime._state.total_govern_calls == 0
            assert set(runtime._state.axis_relief_accumulated.keys()) == set(_VALID_AXES)
            assert all(
                v == 0.0 for v in runtime._state.axis_relief_accumulated.values()
            ), "All axis relief must be 0.0 on fresh boot"
            assert set(runtime._state.guard_fail_history.keys()) == set(_GUARD_NAMES)
            assert runtime._state.current_repair_intensity == 0.30
            assert runtime._state.current_coherence == 0.45

            # Second boot from saved state increments session_count to 2
            # (save happens on first tick — no tick yet, so we re-init manually)
            runtime._state.save(path)
            runtime2 = EngineRuntime(state_path=path)
            assert runtime2._state.session_count == 2, \
                f"Second boot must give session_count=2; got {runtime2._state.session_count}"

        print(f"  {_PASS} EngineRuntime fresh boot")
    except Exception as exc:
        failures.append(f"EngineRuntime boot: {exc}")
        print(f"  {_FAIL} EngineRuntime boot — {exc}")

    # ---- 12. EngineRuntime.tick() generative pull ----
    print(f"[12] EngineRuntime.tick() returns GovernorResult with generative pull...")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "engine_state.json")
            runtime = EngineRuntime(state_path=path)

            obs = {
                "ontological_depth":  0.4192,
                "emotional_valence":  0.90,
                "connections":        104,
                "coherence":          0.50,
                "uncertainty":        0.05,
                "external_perspective": "user_input",
                "routing_mode":       "surface",
            }
            result = runtime.tick(obs)

            # IS-A GovernorResult
            assert isinstance(result, GovernorResult), \
                f"tick() must return GovernorResult; got {type(result)}"

            # Generative pull: at least one field populated
            has_pull = (
                getattr(result, "growth_edge",      None) is not None or
                getattr(result, "resolution_path",  None) is not None or
                getattr(result, "violation",        None) is not None
            )
            assert has_pull, \
                f"tick() must carry generative pull; decision={result.decision}"

            # State updated
            assert runtime._state.total_evidence_fed == 1
            assert runtime._state.total_govern_calls == 1
            assert os.path.exists(path), "State must be saved after tick()"

            # PERMITTED → growth_edge is a valid axis
            if result.decision == GovernorDecision.PERMITTED:
                assert result.growth_edge in _VALID_AXES, \
                    f"growth_edge must be valid axis; got {result.growth_edge!r}"
            # DEFERRED → resolution_path is non-empty string
            elif result.decision == GovernorDecision.DEFERRED:
                assert isinstance(result.resolution_path, str) and result.resolution_path, \
                    "DEFERRED must carry non-empty resolution_path"

        print(f"  {_PASS} EngineRuntime.tick() generative pull")
    except Exception as exc:
        failures.append(f"EngineRuntime tick: {exc}")
        print(f"  {_FAIL} EngineRuntime tick — {exc}")

    # ---- 13. EngineRuntime.dominant_pattern() after 5 ticks ----
    print(f"[13] EngineRuntime.dominant_pattern() returns valid axis after 5 ticks...")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "engine_state.json")
            runtime = EngineRuntime(state_path=path)

            obs_base = {
                "ontological_depth": 0.30,
                "emotional_valence": 0.70,
                "connections":       50,
                "coherence":         0.50,
                "uncertainty":       0.05,
                "routing_mode":      "surface",
            }
            for _ in range(5):
                runtime.tick(obs_base)

            pattern = runtime.dominant_pattern()
            assert pattern in _VALID_AXES, \
                f"dominant_pattern() must be a valid axis; got {pattern!r}"

            # coherence_trend returns one of three valid strings
            trend = runtime.coherence_trend()
            assert trend in ("rising", "stable", "falling"), \
                f"coherence_trend must be rising/stable/falling; got {trend!r}"

            # status_report structure
            report = runtime.status_report()
            assert "session_count" in report
            assert "dominant_pattern" in report
            assert "coherence_trend" in report
            assert "guard_fail_history" in report
            assert "top_failure_guard" in report
            assert report["dominant_pattern"] in _VALID_AXES
            assert report["coherence_trend"] in ("rising", "stable", "falling")

        print(f"  {_PASS} EngineRuntime.dominant_pattern()")
    except Exception as exc:
        failures.append(f"EngineRuntime dominant_pattern: {exc}")
        print(f"  {_FAIL} EngineRuntime dominant_pattern — {exc}")

    # ---- Final verdict ----
    print("\n" + "=" * 62)
    if failures:
        print(f"CONSTRAINT ENGINE SELF-TEST FAILED  ({len(failures)} failure(s))")
        for f in failures:
            print(f"  {_FAIL} {f}")
        raise SystemExit(1)
    else:
        print("CONSTRAINT ENGINE SELF-TEST PASSED")
    print("=" * 62)

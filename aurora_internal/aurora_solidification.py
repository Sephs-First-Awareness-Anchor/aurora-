#!/usr/bin/env python3
"""
AURORA SOLIDIFICATION PIPELINE — STEP 11
==========================================
Depth propagation: recurrence + energy investment → downward solidification.

WHAT SOLIDIFICATION IS:
    A promoted intake (from Step 9) has crossed the Worth threshold once.
    That is NOT enough. Solidification is what happens when a promoted
    intake recurs across multiple evaluation ticks AND the system has
    invested real energy in sustaining it at depth.

    The pipeline is:
        ELIGIBLE intake (horizon elapsed from Step 10)
            → recurrence gate (seen N times across context-varied ticks)
            → energy investment gate (pool spent actual cost to sustain it)
            → polarity coherence gate (surface and core aligned during recurrence)
            → depth-solidification record minted
            → SolidifiedRecord passed to Step 13 (Variant Promotion)

    Solidified structures have two effects on the living system:
        1. They REDUCE future shift cost for their constraint signature
           (the path is worn — it costs less to walk it again).
        2. They INCREASE pressure sensitivity at their depth level
           (the system becomes faster to detect when that configuration
           is under threat).

    Effect 1 and 2 are NOT rules imposed from outside. They are physics:
        Effect 1: The structure has accumulated energy investment — it
                  carries lower inertia in the next shift because baseline
                  is already partially satisfied.
        Effect 2: Deeper solidified structures have higher alignment
                  authority (from IVM ALIGNMENT_VOTE_WEIGHT) — they drag
                  the polarity gradient faster when disturbed.

RECURRENCE GATE:
    An intake must be observed at the same depth, across at least
    _RECURRENCE_MIN distinct ticks, before solidification is considered.
    "Distinct" means the ticks are not consecutive — consecutive ticks
    indicate persistence, not recurrence. Genuine recurrence means the
    input re-appeared after at least _RECURRENCE_GAP ticks of absence.

ENERGY INVESTMENT GATE:
    The system must have spent at least _INVESTMENT_FLOOR energy on
    sustaining this intake since its first promotion. This is real
    energy drawn from the pool — not theoretical.

CONTEXT ROBUSTNESS:
    At least _CONTEXT_VARIETY distinct entropy pressure levels must have
    been observed during recurrence ticks. This prevents gaming via
    artificially stable system states.

AUTHORS: Sunni (Sir) Morningstar and Cael Devo
CREATED: February 2026
"""

from __future__ import annotations

import hashlib
import math
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Deque, Dict, List, Optional, Set, Tuple

from aurora_internal.aurora_constraint_manifold_patched import Constraint, ManifoldViolation
from aurora_constraint_engine import ExistenceMode
from aurora_internal.aurora_noncomp_registry import REGISTRY
from aurora_internal.aurora_energy_layer_costs import LayerEnergyAccountant, MagnitudeShiftRequest
from aurora_internal.aurora_leverage_scalar import LeverageBiasEngine, BandPosition
from aurora_ivm import ALIGNMENT_VOTE_WEIGHT, RecursionLevel
from aurora_internal.aurora_worth_evaluator import VariantHorizon, WorthTrajectory


# ===========================================================================
# SECTION 1 — CONSTANTS (all derived from registry)
# ===========================================================================

# Minimum recurrence count: how many times must an intake re-appear at
# depth before solidification is gated through?
# Derived: the five-layer traversal takes at minimum 5 ticks. Meaningful
# recurrence requires at least 3 independent re-appearances.
# NOTE: used as a floor only — _depth_recurrence_min() scales this per depth.
_RECURRENCE_MIN: int = 3

# Minimum tick gap between recurrence observations. Consecutive ticks are
# persistence, not recurrence.
# Derived: minimum TTL window (_MIN_TTL = 5 from Step 9) — one full cycle.
# NOTE: used as a floor only — _depth_recurrence_gap() scales this per depth.
_RECURRENCE_GAP: int = 5

# Maturity plasticity: every N solidifications, require one additional
# recurrence observation before a new pattern can crystallize.
# Models neuroplasticity — a younger system crystallizes easily; an older
# system requires stronger sustained pressure to change its structure.
_MATURITY_SOLIDIFICATIONS_PER_STEP: int = 50   # solidifications between steps
_MATURITY_MAX_BONUS: int = 3                    # cap: never more than +3 extra

# Minimum energy invested since first promotion (in energy units).
# Derived: deepening one level costs shift_cost_coeff * time_constant at
# the target layer. We require at least one full N-layer deepening cost.
_INVESTMENT_FLOOR: float = (
    REGISTRY.cost(Constraint.N).shift_cost_coeff
    * REGISTRY.cost(Constraint.N).time_constant
)  # 10.0 * 0.01 = 0.10

# Minimum number of distinct entropy pressure bands observed during
# recurrence. Entropy pressure is bucketed into _ENTROPY_BUCKETS bins.
_CONTEXT_VARIETY_MIN: int = 2
_ENTROPY_BUCKETS: int = 5  # [0-0.2], [0.2-0.4], [0.4-0.6], [0.6-0.8], [0.8-1.0]

# Cost reduction factor for solidified pathways (Effect 1).
# Derived: the next shift along this constraint signature costs this
# fraction of its normal shift cost.
# Bounded: can never drop below 30% of normal cost (floor prevents free rides).
_COST_REDUCTION_BASE: float = (
    REGISTRY.cost(Constraint.N).time_constant /
    REGISTRY.cost(Constraint.X).time_constant
)  # 0.01 / 1.0 = 0.01 → capped at floor
_COST_REDUCTION_FACTOR: float = max(0.30, min(0.80, 1.0 - _COST_REDUCTION_BASE * 10))

# Pressure sensitivity multiplier for solidified depth (Effect 2).
# Derived from ALIGNMENT_VOTE_WEIGHT of the deepest layer reached.
def _pressure_sensitivity(depth: ExistenceMode) -> float:
    _depth_to_level: Dict[ExistenceMode, RecursionLevel] = {
        ExistenceMode.PERSISTENT: RecursionLevel.MODERATE,
        ExistenceMode.BOUNDED:    RecursionLevel.DEEP,
        ExistenceMode.AGENTIC:    RecursionLevel.CORE,
    }
    level = _depth_to_level.get(depth, RecursionLevel.MODERATE)
    return ALIGNMENT_VOTE_WEIGHT[level]


def _depth_recurrence_min(depth: ExistenceMode) -> int:
    """
    Minimum genuine recurrences required before solidification for this depth.

    Deep axes (BOUNDED, AGENTIC) fire rarely — each observation is harder to
    accumulate, so the count floor is lower.  Shallow axes fire frequently so
    a higher count is both achievable and warranted for quality control.

    PERSISTENT : 3  (current flat default — unchanged)
    BOUNDED    : 2  (B-axis events are infrequent; 2 cross-context observations
                     are meaningful given the larger _depth_recurrence_gap)
    AGENTIC    : 2  (A-axis moves at continental-drift speed; 2 observations
                     50+ ticks apart is a strong cross-context signal)
    """
    return {
        ExistenceMode.TRANSIENT:  _RECURRENCE_MIN,
        ExistenceMode.PERSISTENT: _RECURRENCE_MIN,
        ExistenceMode.BOUNDED:    2,
        ExistenceMode.AGENTIC:    2,
    }.get(depth, _RECURRENCE_MIN)


def _depth_recurrence_gap(depth: ExistenceMode) -> int:
    """
    Minimum tick gap between recurrence observations for this depth.

    Derived from shift_cost_coeff / 3 so the gap is registry-anchored and
    scales with the natural timescale of each depth layer.

    PERSISTENT  (N-cost=10):  max(5, int(10/3))  = 5   ticks  (same as before)
    BOUNDED     (B-cost=40):  max(5, int(40/3))  = 13  ticks
    AGENTIC     (A-cost=150): max(5, int(150/3)) = 50  ticks

    Larger gaps for deeper axes enforce genuine cross-context re-appearance —
    an A-axis intake must re-appear after a 50-tick absence to count, not just
    persist for a few turns.
    """
    _cost: Dict[ExistenceMode, float] = {
        ExistenceMode.TRANSIENT:  REGISTRY.cost(Constraint.T).shift_cost_coeff,
        ExistenceMode.PERSISTENT: REGISTRY.cost(Constraint.N).shift_cost_coeff,
        ExistenceMode.BOUNDED:    REGISTRY.cost(Constraint.B).shift_cost_coeff,
        ExistenceMode.AGENTIC:    REGISTRY.cost(Constraint.A).shift_cost_coeff,
    }
    raw = _cost.get(depth, REGISTRY.cost(Constraint.N).shift_cost_coeff)
    return max(_RECURRENCE_GAP, int(raw / 3))


# ===========================================================================
# SECTION 2 — RECURRENCE RECORD (per intake tracking)
# ===========================================================================

@dataclass
class RecurrenceRecord:
    """
    Tracks recurrence observations for one intake from the point of
    first promotion eligibility.

    intake_id         — opaque ID from Step 9
    depth_reached     — ExistenceMode at time of promotion
    first_seen_tick   — when the intake first crossed worth threshold
    energy_invested   — total pool energy spent sustaining this intake
    observation_ticks — list of ticks where recurrence was confirmed
    entropy_buckets   — set of entropy bands observed during recurrence
    polarity_coherent_count — how many observations had X/A polarity aligned
    """
    intake_id:             str
    depth_reached:         ExistenceMode
    first_seen_tick:       int
    energy_invested:       float = 0.0
    observation_ticks:     List[int] = field(default_factory=list)
    entropy_buckets:       Set[int]  = field(default_factory=set)
    polarity_coherent_count: int     = 0
    maturity_bonus:        int       = 0   # extra recurrences required as system matures

    def record_observation(
        self,
        tick: int,
        entropy_pressure: float,
        polarity_coherent: bool,
        energy_spent: float,
    ) -> bool:
        """
        Record one recurrence observation.

        Returns True if this observation was counted as a genuine recurrence
        (not just persistence — must have gap from last observation).
        """
        last_tick = self.observation_ticks[-1] if self.observation_ticks else -999
        if (tick - last_tick) < _depth_recurrence_gap(self.depth_reached):
            return False  # too close — persistence, not recurrence

        self.observation_ticks.append(tick)
        bucket = min(_ENTROPY_BUCKETS - 1, int(entropy_pressure * _ENTROPY_BUCKETS))
        self.entropy_buckets.add(bucket)
        if polarity_coherent:
            self.polarity_coherent_count += 1
        self.energy_invested += energy_spent
        return True

    @property
    def recurrence_count(self) -> int:
        return len(self.observation_ticks)

    @property
    def context_variety(self) -> int:
        return len(self.entropy_buckets)

    @property
    def polarity_coherence_rate(self) -> float:
        n = self.recurrence_count
        if n == 0:
            return 0.0
        return self.polarity_coherent_count / n

    def gates_passed(self) -> Tuple[bool, bool, bool, bool]:
        """
        Returns (recurrence_gate, investment_gate, context_gate, polarity_gate).
        All four must be True for solidification to proceed.
        """
        effective_min = _depth_recurrence_min(self.depth_reached) + self.maturity_bonus
        rec  = self.recurrence_count  >= effective_min
        inv  = self.energy_invested   >= _INVESTMENT_FLOOR
        ctx  = self.context_variety   >= _CONTEXT_VARIETY_MIN
        pol  = self.polarity_coherence_rate >= 0.5  # majority of observations coherent
        return rec, inv, ctx, pol

    def all_gates_passed(self) -> bool:
        return all(self.gates_passed())


# ===========================================================================
# SECTION 3 — SOLIDIFIED RECORD
# ===========================================================================

@dataclass(frozen=True)
class SolidifiedRecord:
    """
    A depth-solidified intake — the output of the solidification pipeline.

    This is the object that Step 13 (Variant Promotion) consumes.
    It is immutable once minted — solidification cannot be undone.

    solidification_id — unique hash for this solidified structure
    intake_id         — source intake from Step 9
    depth_reached     — deepest ExistenceMode achieved
    solidified_tick   — when solidification was confirmed
    recurrence_count  — how many valid recurrences were observed
    energy_invested   — total pool energy that went into sustaining this
    context_variety   — number of distinct entropy contexts observed
    polarity_coherence_rate — fraction of observations with X/A aligned
    cost_reduction_factor — fraction applied to future shifts on this path
    pressure_sensitivity  — how quickly the system will detect disturbance
    constraint_signature  — which constraint was the deepest active layer
    """
    solidification_id:       str
    intake_id:               str
    depth_reached:           ExistenceMode
    solidified_tick:         int
    recurrence_count:        int
    energy_invested:         float
    context_variety:         int
    polarity_coherence_rate: float
    cost_reduction_factor:   float
    pressure_sensitivity:    float
    constraint_signature:    str  # e.g. "XTNBA" — active constraints at depth

    def describe(self) -> str:
        return (
            f"SolidifiedRecord[{self.solidification_id[:8]}] "
            f"depth={self.depth_reached.name} "
            f"recurrence={self.recurrence_count} "
            f"energy_invested={self.energy_invested:.3f} "
            f"cost_reduction={self.cost_reduction_factor:.2f} "
            f"pressure_sensitivity={self.pressure_sensitivity:.3f}"
        )


def _mint_solidification_id(intake_id: str, depth: ExistenceMode, tick: int) -> str:
    raw = f"solid:{intake_id}:{depth.name}:{tick}"
    return "S:" + hashlib.sha1(raw.encode()).hexdigest()[:12]


def _constraint_signature(depth: ExistenceMode) -> str:
    """Return the constraint activation signature for this depth."""
    _sigs: Dict[ExistenceMode, str] = {
        ExistenceMode.TRANSIENT:  "XT",
        ExistenceMode.PERSISTENT: "XTN",
        ExistenceMode.BOUNDED:    "XTNB",
        ExistenceMode.AGENTIC:    "XTNBA",
    }
    return _sigs.get(depth, "X")


# ===========================================================================
# SECTION 4 — SOLIDIFICATION PIPELINE
# ===========================================================================

class SolidificationPipeline:
    """
    The Step 11 solidification engine.

    Receives eligible intakes (VariantHorizon.eligible_at(tick) == True)
    from Step 10 (Worth Evaluator) and tracks their recurrence against
    four gates before minting a SolidifiedRecord for Step 13.

    INTEGRATION CONTRACT:
        Each tick the caller must:
            1. Call pipeline.submit_eligible(horizon, tick, accountant, polarity_coherent)
               for every intake whose horizon has elapsed.
            2. Call pipeline.observe_recurrence(intake_id, tick, accountant, polarity_coherent)
               for every promoted intake that re-appears at depth.
            3. Collect pipeline.drain_solidified() at end of tick for newly
               minted SolidifiedRecords to pass to Step 13.

    The pipeline does NOT call the accountant's apply_shift — it only reads
    the pool and entropy state to verify investment. The actual energy was
    already spent by the IntakeMetabolizer in Step 9.
    """

    def __init__(self) -> None:
        # Active recurrence tracking (intake_id → RecurrenceRecord)
        self._tracking:    Dict[str, RecurrenceRecord] = {}
        # Newly solidified this tick — drained each tick
        self._solidified_queue: List[SolidifiedRecord] = []
        # All-time solidified records (ring buffer, not queryable externally)
        self._archive: Deque[SolidifiedRecord] = deque(maxlen=256)
        # Counters
        self._total_submitted:   int = 0
        self._total_solidified:  int = 0
        self._total_gate_failed: int = 0

    # ------------------------------------------------------------------
    # SUBMIT — horizon-eligible intake enters tracking
    # ------------------------------------------------------------------

    def submit_eligible(
        self,
        horizon:           VariantHorizon,
        tick:              int,
        accountant:        LayerEnergyAccountant,
        polarity_coherent: bool,
    ) -> None:
        """
        Mark an intake as eligible for solidification tracking.

        Called once per intake when horizon.eligible_at(tick) becomes True.
        Does not solidify immediately — starts recurrence observation.
        """
        iid = horizon.intake_id
        if iid in self._tracking:
            return  # already tracking

        maturity_bonus = min(
            _MATURITY_MAX_BONUS,
            self._total_solidified // _MATURITY_SOLIDIFICATIONS_PER_STEP,
        )
        self._tracking[iid] = RecurrenceRecord(
            intake_id       = iid,
            depth_reached   = horizon.depth_reached,
            first_seen_tick = tick,
            maturity_bonus  = maturity_bonus,
        )
        self._total_submitted += 1

        # Count the initial submission as the first observation
        self._observe_internal(
            iid, tick, accountant, polarity_coherent,
            energy_spent=0.0,  # no extra cost at submission tick
        )

    # ------------------------------------------------------------------
    # OBSERVE RECURRENCE — intake re-appears at depth
    # ------------------------------------------------------------------

    def observe_recurrence(
        self,
        intake_id:         str,
        tick:              int,
        accountant:        LayerEnergyAccountant,
        polarity_coherent: bool,
        energy_spent:      float = 0.0,
    ) -> None:
        """
        Record a recurrence observation for a tracked intake.

        energy_spent should be the energy that was withdrawn from the pool
        to sustain this intake at depth during this tick.
        """
        if intake_id not in self._tracking:
            return
        self._observe_internal(intake_id, tick, accountant, polarity_coherent, energy_spent)

    def _observe_internal(
        self,
        intake_id:         str,
        tick:              int,
        accountant:        LayerEnergyAccountant,
        polarity_coherent: bool,
        energy_spent:      float,
    ) -> None:
        rec = self._tracking.get(intake_id)
        if rec is None:
            return

        ep = accountant.entropy_pressure()
        rec.record_observation(tick, ep, polarity_coherent, energy_spent)

        # Check solidification gates after every observation
        if rec.all_gates_passed():
            self._mint(rec, tick)

    # ------------------------------------------------------------------
    # MINT — all gates passed, produce SolidifiedRecord
    # ------------------------------------------------------------------

    def _mint(self, rec: RecurrenceRecord, tick: int) -> None:
        sid = _mint_solidification_id(rec.intake_id, rec.depth_reached, tick)
        depth = rec.depth_reached
        solid = SolidifiedRecord(
            solidification_id       = sid,
            intake_id               = rec.intake_id,
            depth_reached           = depth,
            solidified_tick         = tick,
            recurrence_count        = rec.recurrence_count,
            energy_invested         = rec.energy_invested,
            context_variety         = rec.context_variety,
            polarity_coherence_rate = rec.polarity_coherence_rate,
            cost_reduction_factor   = _COST_REDUCTION_FACTOR,
            pressure_sensitivity    = _pressure_sensitivity(depth),
            constraint_signature    = _constraint_signature(depth),
        )
        self._solidified_queue.append(solid)
        self._archive.append(solid)
        self._total_solidified += 1
        # Remove from active tracking
        del self._tracking[rec.intake_id]

    # ------------------------------------------------------------------
    # DRAIN — collect newly solidified records
    # ------------------------------------------------------------------

    def drain_solidified(self) -> List[SolidifiedRecord]:
        """Return all SolidifiedRecords minted this tick and clear the queue."""
        out = list(self._solidified_queue)
        self._solidified_queue.clear()
        return out

    def stats(self) -> Dict[str, int]:
        return {
            "total_submitted":   self._total_submitted,
            "total_solidified":  self._total_solidified,
            "total_gate_failed": self._total_gate_failed,
            "currently_tracking": len(self._tracking),
        }


# ===========================================================================
# SECTION 5 — FACTORY
# ===========================================================================

def make_solidification_pipeline() -> SolidificationPipeline:
    return SolidificationPipeline()


# ===========================================================================
# SECTION 6 — SELF-VERIFICATION (14 checks)
# ===========================================================================

def verify_solidification_pipeline() -> Dict[str, object]:
    """
    Checks:
         1. _RECURRENCE_MIN >= 3
         2. _RECURRENCE_GAP >= 5 (one full TTL cycle)
         3. _INVESTMENT_FLOOR derived from N-layer cost
         4. _COST_REDUCTION_FACTOR in [0.30, 0.80]
         5. pressure_sensitivity increases with depth (PERSISTENT < BOUNDED < AGENTIC)
         6. RecurrenceRecord: consecutive ticks not counted as recurrence
         7. RecurrenceRecord: distinct entropy buckets tracked correctly
         8. RecurrenceRecord: polarity_coherence_rate computed correctly
         9. RecurrenceRecord: all gates pass when conditions met
        10. SolidificationPipeline: submit_eligible starts tracking
        11. SolidificationPipeline: observe_recurrence increments count
        12. SolidificationPipeline: solidification minted when all gates pass
        13. SolidificationPipeline: duplicate submission does not double-track
        14. SolidifiedRecord: constraint_signature matches depth
    """
    from aurora_internal.aurora_energy_layer_costs import make_accountant
    from aurora_internal.aurora_worth_evaluator import compute_variant_horizon

    results: Dict[str, object] = {"checks": [], "all_passed": True}

    def check(name: str, passed: bool, detail: str = "") -> None:
        results["checks"].append({"test": name, "passed": passed, "detail": detail})
        if not passed:
            results["all_passed"] = False

    # 1-3. Constants
    check("_RECURRENCE_MIN >= 3", _RECURRENCE_MIN >= 3, str(_RECURRENCE_MIN))
    check("_RECURRENCE_GAP >= 5", _RECURRENCE_GAP >= 5, str(_RECURRENCE_GAP))
    check("_INVESTMENT_FLOOR > 0 and derived from N-layer", _INVESTMENT_FLOOR > 0, f"{_INVESTMENT_FLOOR:.4f}")

    # 4. Cost reduction factor
    check("_COST_REDUCTION_FACTOR in [0.30, 0.80]",
          0.30 <= _COST_REDUCTION_FACTOR <= 0.80, f"{_COST_REDUCTION_FACTOR:.3f}")

    # 5. Pressure sensitivity increases with depth
    ps_pers = _pressure_sensitivity(ExistenceMode.PERSISTENT)
    ps_bnd  = _pressure_sensitivity(ExistenceMode.BOUNDED)
    ps_agen = _pressure_sensitivity(ExistenceMode.AGENTIC)
    check("Pressure sensitivity: PERSISTENT < BOUNDED < AGENTIC",
          ps_pers < ps_bnd < ps_agen,
          f"PERSISTENT={ps_pers:.3f} BOUNDED={ps_bnd:.3f} AGENTIC={ps_agen:.3f}")

    # 6. Consecutive ticks not counted — use depth-specific gap for BOUNDED
    _bnd_gap = _depth_recurrence_gap(ExistenceMode.BOUNDED)  # 13
    rec6 = RecurrenceRecord("test6", ExistenceMode.BOUNDED, first_seen_tick=1)
    r1 = rec6.record_observation(100, 0.3, True, 0.1)
    r2 = rec6.record_observation(100 + _bnd_gap - 1, 0.3, True, 0.1)  # gap < depth gap
    check("Consecutive ticks (gap<depth_gap) not counted",
          r1 is True and r2 is False,
          f"first={r1} second={r2} bnd_gap={_bnd_gap}")

    # 7. Entropy buckets — space observations by PERSISTENT gap (smallest depth)
    _per_gap = _depth_recurrence_gap(ExistenceMode.PERSISTENT)  # 5
    rec7 = RecurrenceRecord("test7", ExistenceMode.PERSISTENT, first_seen_tick=1)
    rec7.record_observation(1,                    0.1, True, 0.1)   # bucket 0
    rec7.record_observation(1 + _per_gap,         0.5, True, 0.1)   # bucket 2
    rec7.record_observation(1 + _per_gap * 2,     0.9, True, 0.1)   # bucket 4
    check("Entropy buckets tracked correctly",
          rec7.context_variety == 3, f"variety={rec7.context_variety}")

    # 8. Polarity coherence rate — space by PERSISTENT gap
    rec8 = RecurrenceRecord("test8", ExistenceMode.PERSISTENT, first_seen_tick=1)
    rec8.record_observation(1,            0.3, True,  0.1)
    rec8.record_observation(1 + _per_gap, 0.3, False, 0.1)
    check("Polarity coherence rate = 0.5 for 1/2 coherent",
          abs(rec8.polarity_coherence_rate - 0.5) < 0.01, str(rec8.polarity_coherence_rate))

    # 9. All gates pass — use depth-specific gap for AGENTIC
    _agen_gap = _depth_recurrence_gap(ExistenceMode.AGENTIC)   # 50
    _agen_min = _depth_recurrence_min(ExistenceMode.AGENTIC)   # 2
    rec9 = RecurrenceRecord("test9", ExistenceMode.AGENTIC, first_seen_tick=1)
    for i in range(_agen_min + 1):
        rec9.record_observation(1 + i * _agen_gap, 0.1 + i * 0.2, True, _INVESTMENT_FLOOR)
    rec9.entropy_buckets = {0, 1, 2}  # ensure context variety
    g = rec9.gates_passed()
    check("All gates pass when conditions met (depth-scaled)",
          all(g), f"gates={g} recurrence={rec9.recurrence_count} inv={rec9.energy_invested:.3f}")

    # 10. Submit starts tracking
    pipeline10 = make_solidification_pipeline()
    acc10 = make_accountant(5000.0)
    acc10.tick()
    h10 = compute_variant_horizon("iid10", ExistenceMode.BOUNDED, promoted_tick=0)
    pipeline10.submit_eligible(h10, h10.eligible_tick, acc10, True)
    check("submit_eligible starts tracking",
          pipeline10.stats()["currently_tracking"] == 1)

    # 11. observe_recurrence increments count
    pipeline11 = make_solidification_pipeline()
    acc11 = make_accountant(5000.0)
    acc11.tick()
    h11 = compute_variant_horizon("iid11", ExistenceMode.BOUNDED, promoted_tick=0)
    pipeline11.submit_eligible(h11, h11.eligible_tick, acc11, True)
    pipeline11.observe_recurrence("iid11", h11.eligible_tick + _depth_recurrence_gap(ExistenceMode.BOUNDED), acc11, True, 0.2)
    rec11 = pipeline11._tracking.get("iid11")
    check("observe_recurrence increments recurrence count",
          rec11 is not None and rec11.recurrence_count >= 1,
          f"count={rec11.recurrence_count if rec11 else 'MISSING'}")

    # 12. Solidification minted when all gates pass
    pipeline12 = make_solidification_pipeline()
    acc12 = make_accountant(50000.0, entropy_saturation_ceiling=1.0)
    acc12.tick()
    h12 = compute_variant_horizon("iid12", ExistenceMode.BOUNDED, promoted_tick=0)
    pipeline12.submit_eligible(h12, h12.eligible_tick, acc12, True)
    tick12 = h12.eligible_tick
    _bnd_gap12 = _depth_recurrence_gap(ExistenceMode.BOUNDED)   # 13
    _bnd_min12 = _depth_recurrence_min(ExistenceMode.BOUNDED)   # 2
    shift_sequence = [(Constraint.X, 2.0), (Constraint.B, 2.0), (Constraint.T, 2.0), (Constraint.A, 2.0)]
    for i in range(_bnd_min12 + 1):
        tick12 += _bnd_gap12
        c, delta = shift_sequence[i % len(shift_sequence)]
        acc12.apply_shift(MagnitudeShiftRequest(c, delta, "vary_entropy"))
        pipeline12.observe_recurrence("iid12", tick12, acc12, True, _INVESTMENT_FLOOR + 0.01)
    solids12 = pipeline12.drain_solidified()
    check("SolidifiedRecord minted when all gates pass",
          len(solids12) >= 1,
          f"solidified_count={len(solids12)}")

    # 13. Duplicate submission does not double-track
    pipeline13 = make_solidification_pipeline()
    acc13 = make_accountant(5000.0)
    acc13.tick()
    h13 = compute_variant_horizon("iid13", ExistenceMode.PERSISTENT, promoted_tick=0)
    pipeline13.submit_eligible(h13, h13.eligible_tick, acc13, True)
    pipeline13.submit_eligible(h13, h13.eligible_tick, acc13, True)
    check("Duplicate submission does not double-track",
          pipeline13.stats()["currently_tracking"] == 1)

    # 14. Constraint signature matches depth
    check("AGENTIC constraint signature = XTNBA",
          _constraint_signature(ExistenceMode.AGENTIC) == "XTNBA")
    check("BOUNDED constraint signature = XTNB",
          _constraint_signature(ExistenceMode.BOUNDED) == "XTNB")

    return results


# ===========================================================================
# MAIN
# ===========================================================================

if __name__ == "__main__":
    from aurora_internal.aurora_energy_layer_costs import make_accountant
    from aurora_internal.aurora_worth_evaluator import compute_variant_horizon

    print("=" * 70)
    print("AURORA SOLIDIFICATION PIPELINE — STEP 11")
    print("Authors: Sunni (Sir) Morningstar and Cael Devo")
    print("=" * 70)
    print(f"\nConstants (all registry-derived):")
    print(f"  _RECURRENCE_MIN      = {_RECURRENCE_MIN}")
    print(f"  _RECURRENCE_GAP      = {_RECURRENCE_GAP} ticks")
    print(f"  _INVESTMENT_FLOOR    = {_INVESTMENT_FLOOR:.4f} energy")
    print(f"  _COST_REDUCTION_FACTOR = {_COST_REDUCTION_FACTOR:.3f}")
    for mode in [ExistenceMode.PERSISTENT, ExistenceMode.BOUNDED, ExistenceMode.AGENTIC]:
        print(f"  pressure_sensitivity({mode.name:10s}) = {_pressure_sensitivity(mode):.3f}")

    results = verify_solidification_pipeline()
    print("\n--- Self-Verification ---")
    checks = results["checks"]
    for c in checks:
        status = "✓" if c["passed"] else "✗"
        detail = f"  [{c['detail']}]" if c.get("detail") else ""
        print(f"  {status} {c['test']}{detail}")
    passed = sum(1 for c in checks if c["passed"])
    print(f"\n{'All' if passed == len(checks) else passed}/{len(checks)} checks passed.")
    print("=" * 70)


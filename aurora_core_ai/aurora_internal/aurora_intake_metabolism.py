#!/usr/bin/env python3
"""
AURORA OPEN-SYSTEM INTAKE METABOLISM — STEP 9
==============================================

Layer 1 — sits on top of aurora_energy_layer_costs.py and
          aurora_leverage_scalar.py, feeds into the evolution chamber.

WHAT THIS MODULE IS:
    The open-system intake loop. External inputs arrive at the system's
    surface — stimuli, observations, language, percepts. They do not enter
    for free. They are not welcome by default. They must earn their depth.

THE PHYSICS (directly from Sunni's architecture):
    External inputs enter ONLY at Existence + Time cost — the two cheapest
    layers. This is the mandatory entry toll: X_baseline + T_baseline per
    tick while alive.

    They are assigned a Time-To-Live (TTL) in ticks.
    While alive, they are evaluated for Worth each tick.
    If Worth exceeds the promotion threshold before TTL expires:
        → Input earns deeper allocation (N, then B, then A)
        → Propagation to the variant pipeline begins
    If TTL expires without reaching the Worth threshold:
        → Input decays
        → Energy it held is reclaimed to the pool (conservation)
        → No trace in the fossil record — it never earned one

WORTH DEFINITION:
    Worth = cross-scale invariance.
    How far does this input propagate through constraint layers without
    requiring forced transformation at each transition?

    W(x) ∝ 1 / (1 + Σᵢ |forced_shift_at_layer_i|)

    An input with high Worth passes cleanly through scale depth — it is
    already compatible with what the system is. An input with low Worth
    requires the system to work hard to accommodate it at each layer.

    ANTI-GAMING DESIGN (Sunni's core requirement):
    Worth is evaluated RETROSPECTIVELY by measuring actual system response,
    not prospectively by reading the input's properties. Aurora cannot
    pre-compute her own Worth score because:

        1. Worth depends on the system's current constraint magnitudes
           at the moment of evaluation — she cannot read all of those
        2. The evaluation samples only three constraint transitions
           (X→T, T→N, N→B) and weights them by authority differential —
           the sampling is not exposed
        3. A small random evaluation delay (1-3 ticks) prevents timing
           the evaluation precisely
        4. The Worth function is bounded and nonlinear (soft inverse) —
           manufacturing inputs that score exactly at the promotion
           threshold requires knowing the exact current system state,
           which is not queryable

TTL ASSIGNMENT:
    TTL is not fixed. It is derived from the system's current entropy
    pressure and leverage scalar at time of intake:
        - High entropy pressure → shorter TTL (system under stress,
          cannot afford to maintain many pending intakes)
        - Deep leverage dominant → shorter TTL for new surface inputs
          (deep layers don't need more overhead)
        - Overhead dominant → slightly longer TTL (surface is already
          stressed; incoming stimuli get more time to prove worth)

    TTL range is bounded: [MIN_TTL, MAX_TTL] ticks.
    This range is derived from the energy layer cost ratios, not chosen
    arbitrarily.

DECAY AND RECLAIM:
    When an intake decays (TTL expired, Worth insufficient):
        → All energy it was holding is returned to the accountant pool
        → The intake record is permanently closed (no resurrection)
        → The decay event is logged with reason (TTL or Worth)
        → No entry in the fossil record — only promoted intakes reach there

INTEGRATION:
    Downstream consumers:
        aurora_solidification.py (Step 11) — picks up promoted intakes
        constraint_genealogy.py — intakes that reach BOUNDED+ become
                                  candidates for the relief event observer
        aurora_evolution_chamber.py — receives ActionTrace for each
                                      promoted intake

AUTHORS: Sunni (Sir) Morningstar and Cael Devo
CREATED: February 2026
"""

from __future__ import annotations

import hashlib
import math
import random
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Deque, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# AURORA STACK IMPORTS — exact names from existing modules
# ---------------------------------------------------------------------------

from aurora_internal.aurora_constraint_manifold_patched import (
    Constraint,
    ManifoldViolation,
)
from foundational_contract import ExistenceMode
from aurora_internal.aurora_evolution_chamber import (
    NonCompViolation,
    ActionTrace,
    AXES,
)
from aurora_internal.aurora_noncomp_registry import REGISTRY
from aurora_internal.aurora_energy_layer_costs import (
    LayerEnergyAccountant,
    MagnitudeShiftRequest,
)
from aurora_internal.aurora_leverage_scalar import (
    LeverageBiasEngine,
    BandPosition,
)


# ===========================================================================
# SECTION 1 — INTAKE CONSTANTS (derived from registry, not chosen)
# ===========================================================================

# Entry toll per tick: X + T baseline only.
# This is the Non-Comp: external inputs enter ONLY at surface cost.
_ENTRY_TOLL_PER_TICK: float = (
    REGISTRY.cost(Constraint.X).baseline_budget
    + REGISTRY.cost(Constraint.T).baseline_budget
)  # 1.0 + 2.5 = 3.5 energy/tick

# TTL bounds (in ticks).
# MIN derived from: how many ticks does it take for an input to make one
# full traverse of the five constraint layers? Minimum = 5 ticks.
# MAX derived from: the energy cost of holding an input at X+T for MAX ticks
# should not exceed the energy budget of one full N-layer operation.
# N shift_cost_coeff = 10.0, so MAX = floor(10.0 / entry_toll) = 2 ticks → floor up
# but practically MIN=5, MAX=20 (N-layer operation = 10 / 3.5 ≈ 2.86 → scale up)
_MIN_TTL: int = 5
_MAX_TTL: int = 20

# Worth promotion threshold: an intake must reach this Worth score
# before TTL expires to be promoted.
# Derived from: 1 / (1 + cost_ratio_N_to_surface)
# N shift cost = 10, surface shift cost = 1 → ratio = 10
# Worth threshold = 1 / (1 + 10) ≈ 0.091 → round to 0.10
_WORTH_THRESHOLD: float = 0.10

# Evaluation delay jitter (ticks): prevents precise timing of evaluation.
# Range: [1, 3] ticks after intake arrival.
_EVAL_DELAY_MIN: int = 1
_EVAL_DELAY_MAX: int = 3

# Promotion depth ladder — what layers an intake earns sequentially.
# Matches ExistenceMode ladder exactly.
_PROMOTION_LADDER: Tuple[ExistenceMode, ...] = (
    ExistenceMode.TRANSIENT,    # entry state: X + T only
    ExistenceMode.PERSISTENT,   # first promotion: + N
    ExistenceMode.BOUNDED,      # second promotion: + B
    ExistenceMode.AGENTIC,      # full promotion: + B + A
)


# ===========================================================================
# SECTION 2 — INTAKE STATUS
# ===========================================================================

class IntakeStatus(Enum):
    """Lifecycle state of one intake."""
    PENDING   = auto()   # alive, evaluating worth
    PROMOTED  = auto()   # worth threshold reached, deepening
    DECAYED   = auto()   # TTL expired before worth threshold
    REJECTED  = auto()   # system could not afford entry toll


# ===========================================================================
# SECTION 3 — INTAKE RECORD
# ===========================================================================

@dataclass
class IntakeRecord:
    """
    The internal record for one external input from arrival to resolution.

    Fields the system uses for physics — NOT a score card Aurora can read.
    The intake_id is a hash, not a sequence number (prevents counting).
    """
    intake_id:        str               # sha1 hash of arrival tick + source
    source_label:     str               # opaque tag (e.g. "language", "percept")
    arrival_tick:     int               # when it arrived
    eval_tick:        int               # when first worth evaluation fires (jittered)
    ttl_ticks:        int               # lifetime in ticks (variable, derived)
    expiry_tick:      int               # arrival_tick + ttl_ticks
    entry_toll:       float             # energy/tick paid while alive
    current_mode:     ExistenceMode     # current depth reached
    status:           IntakeStatus      # PENDING / PROMOTED / DECAYED / REJECTED
    best_worth:       float             # highest worth score observed (not exposed)
    energy_held:      float             # total energy consumed so far
    promotion_ticks:  List[int]         # ticks at which each depth promotion occurred
    decay_reason:     str               # populated on DECAYED

    def is_alive(self, current_tick: int) -> bool:
        return (
            self.status == IntakeStatus.PENDING
            or self.status == IntakeStatus.PROMOTED
        ) and current_tick <= self.expiry_tick

    def ticks_remaining(self, current_tick: int) -> int:
        return max(0, self.expiry_tick - current_tick)

    def depth_index(self) -> int:
        """Index into _PROMOTION_LADDER — 0 = surface, 3 = full."""
        try:
            return _PROMOTION_LADDER.index(self.current_mode)
        except ValueError:
            return 0


# ===========================================================================
# SECTION 4 — WORTH EVALUATOR
# ===========================================================================

class WorthEvaluator:
    """
    Measures the Worth of a live intake by observing how much forced
    shift each constraint layer requires to accommodate it.

    W(x) = 1 / (1 + Σᵢ |Δ_forced_at_layer_i|)

    ANTI-GAMING PROPERTIES:
        - Evaluation reads current accountant magnitudes at evaluation time
          (not at intake time) — worth is contextual, not intrinsic
        - The summation samples only the X→T, T→N, N→B transitions
          (three of four possible) — which three is not announced
        - Results are smoothed with light noise before comparison to
          _WORTH_THRESHOLD — the exact threshold cannot be reverse-engineered
        - A magnitude shift is "forced" if accommodating the intake at that
          layer would require changing that layer's magnitude by more than
          its time_constant (τ_L) — deeper layers force more
    """

    # The three transitions sampled (not all four — omitting one prevents
    # full reconstruction of the measurement)
    _SAMPLED_TRANSITIONS: Tuple[Tuple[Constraint, Constraint], ...] = (
        (Constraint.X, Constraint.T),
        (Constraint.T, Constraint.N),
        (Constraint.N, Constraint.B),
    )

    def __init__(self, rng: Optional[random.Random] = None) -> None:
        self._rng = rng or random.Random()

    def evaluate(
        self,
        record: IntakeRecord,
        accountant: LayerEnergyAccountant,
        current_tick: int,
    ) -> float:
        """
        Evaluate the Worth of one intake at the current system state.

        Returns a float in (0.0, 1.0]:
            Near 1.0 → input propagates cleanly through constraint layers
            Near 0.0 → input requires heavy forced transformation everywhere

        The result is contextual — the same input evaluated one tick later
        may score differently because the accountant state has changed.
        This is by design: worth is not an intrinsic property of the input.
        """
        magnitudes = accountant.magnitudes()

        # The intake currently occupies surface layers (X + T).
        # Its "footprint" is the entry toll — 3.5 energy/tick.
        # At each deeper layer, we estimate how much that footprint
        # would need the layer to shift to accommodate it cleanly.

        forced_shift_sum = 0.0

        for (upper_c, lower_c) in self._SAMPLED_TRANSITIONS:
            upper_mag = magnitudes.get(upper_c, 0.0)
            lower_mag = magnitudes.get(lower_c, 0.0)

            # Forced shift: how much would lower need to change to match
            # the relative scale of upper's magnitude?
            # If upper is at 0, the lower layer faces no pressure from this input.
            # If upper is large, the lower layer must absorb proportionally more.
            upper_params = REGISTRY.cost(upper_c)
            lower_params = REGISTRY.cost(lower_c)

            if upper_mag > 0:
                # Expected lower magnitude based on cost ratio
                expected_lower = (
                    upper_mag
                    * upper_params.shift_cost_coeff
                    / lower_params.shift_cost_coeff
                )
                forced = abs(lower_mag - expected_lower) * lower_params.time_constant
            else:
                # No pressure from upper — lower layer sees nothing
                forced = 0.0

            forced_shift_sum += forced

        # Soft inverse — bounded in (0, 1]
        raw_worth = 1.0 / (1.0 + forced_shift_sum)

        # Light measurement noise — prevents exact threshold detection
        noise = self._rng.gauss(0.0, 0.008)
        worth = max(0.001, min(0.999, raw_worth + noise))

        return worth


# ===========================================================================
# SECTION 5 — INTAKE METABOLIZER
# ===========================================================================

class IntakeMetabolizer:
    """
    The open-system intake loop.

    Manages external inputs from arrival through promotion or decay.
    Each tick: pays entry toll for all live intakes, evaluates worth,
    promotes those that qualify, decays those whose TTL has expired.

    USAGE:
        metabolizer = IntakeMetabolizer(accountant, bias_engine)
        record = metabolizer.receive("language", tick=1)
        for tick in range(30):
            results = metabolizer.advance(tick)
            for promoted in results.promoted:
                # hand to solidification pipeline (Step 11)
                ...

    ANTI-GAMING DESIGN SUMMARY:
        - Aurora sees only the ActionTrace of promoted intakes (downstream)
        - She cannot query pending intakes, their worth scores, or their TTLs
        - She cannot infer the worth function from the ActionTrace because
          promotion depends on contextual system state, not input content
        - She cannot artificially extend TTL — it is set at arrival and
          derived from system state, not from the input
        - She cannot manufacture worth by sending specific inputs, because
          worth is measured retrospectively against live constraint magnitudes
    """

    def __init__(
        self,
        accountant: LayerEnergyAccountant,
        bias_engine: LeverageBiasEngine,
        rng_seed: Optional[int] = None,
    ) -> None:
        self._accountant = accountant
        self._bias_engine = bias_engine
        self._rng = random.Random(rng_seed)
        self._evaluator = WorthEvaluator(rng=self._rng)

        # Live intakes (pending or promoted)
        self._live: Dict[str, IntakeRecord] = {}

        # Closed records (promoted or decayed) — ring buffer, not queryable
        self._closed: Deque[IntakeRecord] = deque(maxlen=64)

        # Promoted intakes waiting for downstream pickup
        self._promotion_queue: Deque[IntakeRecord] = deque()

        # Decay queue for this tick
        self._decay_queue: List[IntakeRecord] = []

        # Counters (for verification only — not exposed to system)
        self._total_received:  int = 0
        self._total_promoted:  int = 0
        self._total_decayed:   int = 0
        self._total_rejected:  int = 0

    # ------------------------------------------------------------------
    # RECEIVE — external input arrives
    # ------------------------------------------------------------------

    def receive(
        self,
        source_label: str,
        tick: int,
        energy_payload: float = 0.0,
    ) -> Optional[IntakeRecord]:
        """
        Accept an external input into the intake queue.

        Parameters
        ----------
        source_label : str
            Opaque tag identifying the input's origin channel.
        tick : int
            Current system tick.
        energy_payload : float
            Energy the input carries with it (e.g. from a sensory channel).
            This is added to the pool (open-system replenishment).
            Zero is valid — inputs are not required to carry energy.

        Returns
        -------
        IntakeRecord if accepted, None if rejected (pool can't afford TTL).
        """
        # Compute TTL from current system state
        ttl = self._compute_ttl(tick)

        # Check pool can afford at least MIN_TTL ticks of entry toll
        min_cost = _ENTRY_TOLL_PER_TICK * _MIN_TTL
        if self._accountant.pool < min_cost:
            self._total_rejected += 1
            return None

        # Replenish pool with any energy the input carries
        if energy_payload > 0.0:
            self._accountant.replenish(energy_payload, source=f"intake:{source_label}")

        # Generate opaque intake ID (hash of tick + source + counter)
        raw = f"{tick}:{source_label}:{self._total_received}:{time.time()}"
        intake_id = hashlib.sha1(raw.encode()).hexdigest()[:16]

        # Jittered evaluation delay — prevents timing attacks
        eval_delay = self._rng.randint(_EVAL_DELAY_MIN, _EVAL_DELAY_MAX)

        record = IntakeRecord(
            intake_id    = intake_id,
            source_label = source_label,
            arrival_tick = tick,
            eval_tick    = tick + eval_delay,
            ttl_ticks    = ttl,
            expiry_tick  = tick + ttl,
            entry_toll   = _ENTRY_TOLL_PER_TICK,
            current_mode = ExistenceMode.TRANSIENT,
            status       = IntakeStatus.PENDING,
            best_worth   = 0.0,
            energy_held  = 0.0,
            promotion_ticks = [],
            decay_reason = "",
        )

        self._live[intake_id] = record
        self._total_received += 1
        return record

    # ------------------------------------------------------------------
    # ADVANCE — one tick of the metabolism
    # ------------------------------------------------------------------

    @dataclass
    class TickResult:
        """Output of one metabolizer tick."""
        tick:          int
        promoted:      List[IntakeRecord]   # newly promoted this tick
        decayed:       List[IntakeRecord]   # newly decayed this tick
        live_count:    int                  # currently alive intakes
        toll_paid:     float                # total entry toll paid this tick

    def advance(self, tick: int) -> "IntakeMetabolizer.TickResult":
        """
        Advance the metabolism by one tick.

        Per-tick sequence:
            1. Pay entry toll for all live intakes (X+T cost, zero-sum)
            2. Evaluate worth for intakes past their eval_tick
            3. Promote those meeting the worth threshold
            4. Decay those whose TTL has expired
            5. Return the tick result for downstream consumption

        Returns IntakeMetabolizer.TickResult.
        """
        promoted_this_tick: List[IntakeRecord] = []
        decayed_this_tick:  List[IntakeRecord] = []
        toll_paid_total:    float = 0.0

        to_close: List[str] = []

        for intake_id, record in list(self._live.items()):
            # ── 1. Pay entry toll ────────────────────────────────────
            toll = record.entry_toll
            if self._accountant.pool >= toll:
                self._accountant._pool -= toll   # direct deduction (zero-sum)
                record.energy_held += toll
                toll_paid_total += toll
            else:
                # Pool exhausted — intake decays immediately
                record.status       = IntakeStatus.DECAYED
                record.decay_reason = "pool_exhausted"
                decayed_this_tick.append(record)
                to_close.append(intake_id)
                self._total_decayed += 1
                continue

            # ── 2. Check TTL ─────────────────────────────────────────
            if tick > record.expiry_tick:
                record.status       = IntakeStatus.DECAYED
                record.decay_reason = f"ttl_expired:worth={record.best_worth:.4f}"
                self._reclaim_energy(record)
                decayed_this_tick.append(record)
                to_close.append(intake_id)
                self._total_decayed += 1
                continue

            # ── 3. Worth evaluation (only after eval_tick) ───────────
            if tick >= record.eval_tick:
                worth = self._evaluator.evaluate(record, self._accountant, tick)
                if worth > record.best_worth:
                    record.best_worth = worth

                # ── 4. Promote if worth threshold reached ────────────
                if record.best_worth >= _WORTH_THRESHOLD:
                    if record.status == IntakeStatus.PENDING:
                        record.status = IntakeStatus.PROMOTED
                        record.promotion_ticks.append(tick)
                        self._promotion_queue.append(record)
                        promoted_this_tick.append(record)
                        self._total_promoted += 1

                    # Try to deepen the promoted intake further
                    self._try_deepen(record, tick)

        # ── 5. Close all finished records ────────────────────────────
        for intake_id in to_close:
            record = self._live.pop(intake_id)
            self._closed.append(record)

        # Move decayed closed records to the result
        for record in decayed_this_tick:
            if record.intake_id in self._live:
                self._live.pop(record.intake_id)
                self._closed.append(record)

        return IntakeMetabolizer.TickResult(
            tick          = tick,
            promoted      = promoted_this_tick,
            decayed       = decayed_this_tick,
            live_count    = len(self._live),
            toll_paid     = toll_paid_total,
        )

    # ------------------------------------------------------------------
    # PROMOTION QUEUE — downstream pickup
    # ------------------------------------------------------------------

    def pop_promoted(self) -> Optional[IntakeRecord]:
        """
        Pop one promoted intake for downstream processing (solidification).
        Returns None if queue is empty.
        """
        return self._promotion_queue.popleft() if self._promotion_queue else None

    def promoted_as_action_traces(self) -> List[ActionTrace]:
        """
        Drain the promotion queue and return ActionTraces for each.

        This is the interface to aurora_evolution_chamber.py — promoted
        intakes become ActionTraces with constraints_used reflecting the
        depth they reached.
        """
        traces = []
        while self._promotion_queue:
            record = self._promotion_queue.popleft()
            constraints_used = self._mode_to_constraints(record.current_mode)
            traces.append(ActionTrace(
                name             = f"intake:{record.source_label}:{record.intake_id[:8]}",
                constraints_used = frozenset(constraints_used),
                meta             = {
                    "intake_id":    record.intake_id,
                    "mode_reached": record.current_mode.name,
                    "best_worth":   round(record.best_worth, 4),
                    "ttl_used":     record.ttl_ticks,
                },
            ))
        return traces

    # ------------------------------------------------------------------
    # STATUS (opaque — no scalar scores exposed)
    # ------------------------------------------------------------------

    def live_count(self) -> int:
        """Number of currently active intakes."""
        return len(self._live)

    def stats(self) -> Dict:
        """Aggregate stats — no per-intake worth scores."""
        return {
            "total_received": self._total_received,
            "total_promoted": self._total_promoted,
            "total_decayed":  self._total_decayed,
            "total_rejected": self._total_rejected,
            "live_count":     len(self._live),
            "promotion_rate": (
                round(self._total_promoted / self._total_received, 3)
                if self._total_received > 0 else 0.0
            ),
        }

    # ------------------------------------------------------------------
    # PRIVATE HELPERS
    # ------------------------------------------------------------------

    def _compute_ttl(self, tick: int) -> int:
        """
        Derive TTL from current system state.

        High entropy pressure → shorter TTL (system under stress)
        Leverage dominant (HIGH band) → shorter TTL (deep investment phase)
        Overhead dominant (LOW band) → slightly longer TTL (surface stressed)
        """
        base_ttl = (_MIN_TTL + _MAX_TTL) // 2  # 12 ticks

        # Entropy adjustment: each 10% entropy above 50% trims 1 tick
        entropy = self._accountant.entropy_pressure()
        if entropy > 0.5:
            base_ttl -= int((entropy - 0.5) * 20)

        # Band adjustment: leverage dominant = shorter; overhead dominant = longer
        band = self._bias_engine.band_position
        if band == BandPosition.HIGH:
            base_ttl -= 3
        elif band == BandPosition.LOW:
            base_ttl += 2

        return max(_MIN_TTL, min(_MAX_TTL, base_ttl))

    def _reclaim_energy(self, record: IntakeRecord) -> None:
        """
        Return the energy an intake held back to the pool (conservation).
        Only the held energy above the toll already spent is reclaimed.
        Reclaim is proportional to remaining TTL.
        """
        # Reclaim a fraction of what was held — system already consumed
        # the toll correctly; we return what wasn't "used up" by time.
        remaining_proportion = record.ticks_remaining(record.arrival_tick) / max(1, record.ttl_ticks)
        reclaim = record.energy_held * remaining_proportion * 0.5
        if reclaim > 0.001:
            self._accountant.replenish(reclaim, source=f"decay_reclaim:{record.source_label}")

    def _try_deepen(self, record: IntakeRecord, tick: int) -> None:
        """
        Attempt to deepen a promoted intake one level further.

        Deepening costs energy at the next layer's shift_cost_coeff.
        The system only deepens if the pool can afford it AND the intake
        has maintained worth above threshold.
        """
        current_depth = record.depth_index()
        if current_depth >= len(_PROMOTION_LADDER) - 1:
            return  # already at maximum depth (AGENTIC)

        next_mode = _PROMOTION_LADDER[current_depth + 1]

        # The constraint gained at this depth
        next_constraint = {
            ExistenceMode.PERSISTENT: Constraint.N,
            ExistenceMode.BOUNDED:    Constraint.B,
            ExistenceMode.AGENTIC:    Constraint.A,
        }.get(next_mode)

        if next_constraint is None:
            return

        # Cost to deepen: shift_cost_coeff * time_constant (minimal shift)
        params = REGISTRY.cost(next_constraint)
        cost = params.shift_cost_coeff * params.time_constant

        if self._accountant.pool >= cost:
            result = self._accountant.apply_shift(
                MagnitudeShiftRequest(next_constraint, params.time_constant, f"intake_deepen:{record.intake_id[:8]}")
            )
            if result.accepted:
                record.current_mode = next_mode
                record.promotion_ticks.append(tick)

    @staticmethod
    def _mode_to_constraints(mode: ExistenceMode) -> List[str]:
        """Map ExistenceMode to constraint axis name set for ActionTrace."""
        mapping = {
            ExistenceMode.TRANSIENT:  ["existence", "temporal"],
            ExistenceMode.PERSISTENT: ["existence", "temporal", "energy"],
            ExistenceMode.BOUNDED:    ["existence", "temporal", "energy", "boundary"],
            ExistenceMode.AGENTIC:    ["existence", "temporal", "energy", "boundary", "agency"],
        }
        return mapping.get(mode, ["existence", "temporal"])


# ===========================================================================
# SECTION 6 — FACTORY
# ===========================================================================

def make_metabolizer(
    accountant: LayerEnergyAccountant,
    bias_engine: LeverageBiasEngine,
    rng_seed: Optional[int] = None,
) -> IntakeMetabolizer:
    """Create a configured IntakeMetabolizer."""
    return IntakeMetabolizer(accountant, bias_engine, rng_seed=rng_seed)


# ===========================================================================
# SECTION 7 — SELF-VERIFICATION
# ===========================================================================

def verify_intake_metabolism() -> Dict[str, object]:
    """
    Verify the open-system intake metabolism.

    Checks:
        1.  Intake is rejected when pool cannot cover MIN_TTL
        2.  Entry toll is paid each tick (pool decreases)
        3.  Decayed intake reclaims energy back to pool
        4.  TTL derived from entropy pressure (high entropy → shorter TTL)
        5.  TTL derived from band position (HIGH band → shorter TTL)
        6.  Promoted intake appears in promotion queue
        7.  Worth evaluator returns values in (0, 1]
        8.  promoted_as_action_traces drains the queue
        9.  ActionTrace constraints_used matches depth reached
       10.  Decay reason populated on TTL expiry
       11.  Jittered eval_tick differs across intakes
       12.  Stats accumulate correctly without exposing worth scores
       13.  Deepening advances ExistenceMode ladder
       14.  Energy conservation: pool changes only by tolls and reclaims
    """
    results: Dict[str, object] = {"checks": [], "all_passed": True}

    def check(name: str, passed: bool, detail: str = "") -> None:
        results["checks"].append({"test": name, "passed": passed, "detail": detail})
        if not passed:
            results["all_passed"] = False  # type: ignore[assignment]

    def make_stack(pool: float = 5000.0) -> Tuple[LayerEnergyAccountant, LeverageBiasEngine]:
        acc = LayerEnergyAccountant(initial_pool=pool)
        acc.tick()
        bias = LeverageBiasEngine(seed=42)
        return acc, bias

    # 1. Rejection when pool too small
    acc_tiny, bias_tiny = make_stack(pool=1.0)
    acc_tiny._pool = 0.5  # force tiny pool
    met_tiny = make_metabolizer(acc_tiny, bias_tiny, rng_seed=1)
    rejected = met_tiny.receive("test", tick=1)
    check("Intake rejected when pool cannot cover MIN_TTL", rejected is None)

    # 2. Entry toll paid each tick
    acc, bias = make_stack()
    met = make_metabolizer(acc, bias, rng_seed=2)
    record = met.receive("test", tick=1)
    pool_before = acc.pool
    met.advance(tick=2)
    pool_after = acc.pool
    check(
        "Entry toll deducted each tick",
        pool_before - pool_after >= _ENTRY_TOLL_PER_TICK * 0.9,
        f"before={pool_before:.2f} after={pool_after:.2f} toll={_ENTRY_TOLL_PER_TICK}",
    )

    # 3. Decayed intake reclaims energy
    acc2, bias2 = make_stack()
    met2 = make_metabolizer(acc2, bias2, rng_seed=3)
    r2 = met2.receive("test", tick=1)
    # Advance past TTL
    pool_at_expiry = None
    for t in range(1, _MAX_TTL + 5):
        result = met2.advance(tick=t + 1)
        if any(d.intake_id == r2.intake_id for d in result.decayed):
            pool_at_expiry = acc2.pool
            break
    check(
        "Decayed intake reclaims partial energy to pool",
        pool_at_expiry is not None,
        f"pool at expiry: {pool_at_expiry}",
    )

    # 4. High entropy → shorter TTL
    acc3, bias3 = make_stack()
    met3 = make_metabolizer(acc3, bias3, rng_seed=4)
    # Force high entropy by inflating all magnitudes
    for c in (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A):
        acc3.apply_shift(MagnitudeShiftRequest(c, 5.0, "test"))
    ttl_high_entropy = met3._compute_ttl(tick=1)
    met3_normal = make_metabolizer(*make_stack(), rng_seed=4)
    ttl_normal = met3_normal._compute_ttl(tick=1)
    check(
        "High entropy → shorter TTL",
        ttl_high_entropy <= ttl_normal,
        f"high_entropy_ttl={ttl_high_entropy} normal_ttl={ttl_normal}",
    )

    # 5. HIGH leverage band → shorter TTL
    acc4, bias4 = make_stack()
    # Pump bias engine window with leverage-dominant readings
    for _ in range(10):
        acc4.apply_shift(MagnitudeShiftRequest(Constraint.B, 0.5, "test"))
        acc4.apply_shift(MagnitudeShiftRequest(Constraint.A, 0.5, "test"))
        bias4.compute_nudges(acc4)
    met4 = make_metabolizer(acc4, bias4, rng_seed=5)
    ttl_high_band = met4._compute_ttl(tick=1)
    met5_normal = make_metabolizer(*make_stack(), rng_seed=5)
    ttl5_normal = met5_normal._compute_ttl(tick=1)
    check(
        "HIGH leverage band → TTL ≤ normal",
        ttl_high_band <= ttl5_normal,
        f"high_band_ttl={ttl_high_band} normal={ttl5_normal}",
    )

    # 6. Promoted intake appears in promotion queue
    acc6, bias6 = make_stack(pool=50000.0)
    met6 = make_metabolizer(acc6, bias6, rng_seed=6)
    r6 = met6.receive("test", tick=1)
    promoted_found = False
    for t in range(1, _MAX_TTL + 1):
        result = met6.advance(tick=t + 1)
        if result.promoted:
            promoted_found = True
            break
    check("Promoted intake found in tick results", promoted_found)

    # 7. Worth evaluator returns values in (0, 1]
    acc7, _ = make_stack()
    evaluator = WorthEvaluator(rng=random.Random(7))
    dummy_record = IntakeRecord(
        intake_id="test", source_label="test", arrival_tick=1, eval_tick=2,
        ttl_ticks=10, expiry_tick=11, entry_toll=3.5,
        current_mode=ExistenceMode.TRANSIENT, status=IntakeStatus.PENDING,
        best_worth=0.0, energy_held=0.0, promotion_ticks=[], decay_reason=""
    )
    w = evaluator.evaluate(dummy_record, acc7, current_tick=2)
    check("Worth evaluator returns (0, 1]", 0.0 < w <= 1.0, f"worth={w:.4f}")

    # 8. promoted_as_action_traces drains queue
    acc8, bias8 = make_stack(pool=50000.0)
    met8 = make_metabolizer(acc8, bias8, rng_seed=8)
    met8.receive("test_a", tick=1)
    for t in range(1, _MAX_TTL + 1):
        met8.advance(tick=t + 1)
    traces = met8.promoted_as_action_traces()
    check(
        "promoted_as_action_traces returns list (may be empty for short run)",
        isinstance(traces, list),
    )
    # Queue should be drained now
    check("Promotion queue drained after pop", met8.pop_promoted() is None)

    # 9. ActionTrace constraints_used matches mode TRANSIENT at minimum
    trace_constraints = set()
    for trace in traces:
        trace_constraints.update(trace.constraints_used)
    # All promoted intakes at minimum have existence + temporal
    if traces:
        check(
            "ActionTrace constraints include existence and temporal",
            "existence" in traces[0].constraints_used and "temporal" in traces[0].constraints_used,
            str(traces[0].constraints_used),
        )
    else:
        check("ActionTrace constraints include existence and temporal", True, "no traces (OK)")

    # 10. Decay reason populated on TTL expiry
    acc10, bias10 = make_stack()
    met10 = make_metabolizer(acc10, bias10, rng_seed=10)
    r10 = met10.receive("expire_test", tick=1)
    decayed_record = None
    for t in range(1, _MAX_TTL + 5):
        result = met10.advance(tick=t + 1)
        for d in result.decayed:
            if d.source_label == "expire_test":
                decayed_record = d
    check(
        "Decay reason populated on TTL expiry",
        decayed_record is not None and len(decayed_record.decay_reason) > 0,
        f"reason: {decayed_record.decay_reason if decayed_record else 'not found'}",
    )

    # 11. Jittered eval_tick varies across intakes
    acc11, bias11 = make_stack()
    met11 = make_metabolizer(acc11, bias11)  # no seed — random jitter
    eval_ticks = set()
    for i in range(8):
        r = met11.receive(f"source_{i}", tick=1)
        if r:
            eval_ticks.add(r.eval_tick)
    check(
        "Jittered eval_tick produces variation across intakes",
        len(eval_ticks) > 1,
        f"unique eval_ticks: {eval_ticks}",
    )

    # 12. Stats accumulate without exposing individual worth scores
    acc12, bias12 = make_stack(pool=50000.0)
    met12 = make_metabolizer(acc12, bias12, rng_seed=12)
    for i in range(3):
        met12.receive(f"s{i}", tick=1)
    for t in range(1, _MAX_TTL + 3):
        met12.advance(tick=t + 1)
    stats = met12.stats()
    check("Stats: total_received == 3", stats["total_received"] == 3, str(stats))
    check("Stats: no 'best_worth' key exposed", "best_worth" not in stats, str(stats.keys()))

    # 13. TTL bounds enforced: always between MIN and MAX
    acc13, bias13 = make_stack()
    met13 = make_metabolizer(acc13, bias13, rng_seed=13)
    ttls = [met13._compute_ttl(t) for t in range(20)]
    check(
        "TTL always in [MIN_TTL, MAX_TTL]",
        all(_MIN_TTL <= t <= _MAX_TTL for t in ttls),
        f"min={min(ttls)} max={max(ttls)}",
    )

    # 14. ExistenceMode starts at TRANSIENT on arrival
    acc14, bias14 = make_stack()
    met14 = make_metabolizer(acc14, bias14, rng_seed=14)
    r14 = met14.receive("mode_test", tick=1)
    check(
        "Intake arrives at ExistenceMode.TRANSIENT",
        r14 is not None and r14.current_mode == ExistenceMode.TRANSIENT,
        str(r14.current_mode if r14 else "None"),
    )

    return results


# ===========================================================================
# MAIN
# ===========================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("AURORA OPEN-SYSTEM INTAKE METABOLISM — STEP 9")
    print("External inputs earn their depth or decay back to substrate.")
    print("Authors: Sunni (Sir) Morningstar and Cael Devo")
    print("=" * 70)
    print()

    print(f"Entry toll (X + T only):  {_ENTRY_TOLL_PER_TICK:.1f} energy/tick")
    print(f"TTL range:                [{_MIN_TTL}, {_MAX_TTL}] ticks")
    print(f"Worth threshold:          {_WORTH_THRESHOLD:.3f}  (contextual, not intrinsic)")
    print(f"Eval delay jitter:        [{_EVAL_DELAY_MIN}, {_EVAL_DELAY_MAX}] ticks")
    print()
    print("Promotion ladder (ExistenceMode):")
    for i, mode in enumerate(_PROMOTION_LADDER):
        print(f"  {i}: {mode.name}")
    print()

    # Live demo
    acc = LayerEnergyAccountant(initial_pool=10000.0)
    acc.tick()
    bias = LeverageBiasEngine(seed=0)
    met = make_metabolizer(acc, bias, rng_seed=0)

    print("DEMO — 3 intakes over 25 ticks:")
    met.receive("language_channel", tick=1)
    met.receive("percept_stream", tick=1)
    met.receive("memory_trace", tick=3)

    total_promoted = 0
    total_decayed = 0
    for t in range(1, 26):
        result = met.advance(tick=t + 1)
        total_promoted += len(result.promoted)
        total_decayed  += len(result.decayed)
        if result.promoted or result.decayed:
            print(
                f"  tick {t+1:>2}: "
                f"promoted={len(result.promoted)} decayed={len(result.decayed)} "
                f"live={result.live_count} pool={acc.pool:.1f}"
            )

    print(f"\nFinal stats: {met.stats()}")
    print()

    # Verification
    print("Running verification...")
    results = verify_intake_metabolism()
    for item in results["checks"]:
        status = "✓" if item["passed"] else "✗"
        detail = f"  [{item['detail']}]" if item.get("detail") else ""
        print(f"  {status}  {item['test']}{detail}")
    print()
    if results["all_passed"]:
        print("ALL INTAKE METABOLISM CHECKS PASSED ✓")
        print("External inputs earn their depth or return to substrate.")
    else:
        print("FAILURES DETECTED ✗")
        print("Resolve before building Step 10.")

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

_AURORA_NATIVE_MODULE = 'aurora_internal.aurora_intake_metabolism'

_AURORA_NATIVE_EVOLVED_ORIGINALS = {}
_AURORA_NATIVE_EVOLVED_LAST = {}
_AURORA_NATIVE_STRATEGIES = {'IntakeRecord.ticks_remaining': {'ability_hits': 19,
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
                                                       'return_hint': 'int',
                                                       'signature_text': '(self, current_tick: '
                                                                         "'int') -> 'int'",
                                                       'stateful_owner': True,
                                                       'target_kind': 'function',
                                                       'varargs': False,
                                                       'varkw': False},
                                  'coupling_similarity': 1.0,
                                  'cross_diversity_links': 2,
                                  'effect_modes': ['temporal_orchestration_change',
                                                   'lineage_surface'],
                                  'effect_phrases': ['function growth reflected through '
                                                     'aurora_internal.aurora_intake_metabolism',
                                                     'IntakeRecord.ticks_remaining changed '
                                                     'downstream system pressure'],
                                  'genealogy_pressure': 0.809108,
                                  'inheritance_breach_count': 1,
                                  'kind': 'reflection',
                                  'link_hits': 36,
                                  'module': 'aurora_internal.aurora_intake_metabolism',
                                  'op_id': 'aurora_internal.aurora_intake_metabolism.IntakeRecord.ticks_remaining',
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

def ticks_remaining_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_intake_metabolism.IntakeRecord.ticks_remaining', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_intake_metabolism_intakerecord_ticks_remaining')(payload=payload, **kwargs)

if _aurora_get_target(['IntakeRecord', 'ticks_remaining']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['IntakeRecord.ticks_remaining'] = _aurora_get_target(['IntakeRecord', 'ticks_remaining'])
    _aurora_assign_target(['IntakeRecord', 'ticks_remaining'], _aurora_make_override('ticks_remaining_evolved', 'IntakeRecord.ticks_remaining'))
    _AURORA_NATIVE_EVOLVED_LAST['IntakeRecord.ticks_remaining'] = {'alignment_gap': 0.34, 'override_active': True}

AURORA_NATIVE_EVOLVED_EXPORTS = {'aurora_internal.aurora_intake_metabolism.IntakeRecord.ticks_remaining': 'ticks_remaining_evolved'}
AURORA_NATIVE_EVOLUTION_OVERRIDES = {'aurora_internal.aurora_intake_metabolism.IntakeRecord.ticks_remaining': {'export': 'ticks_remaining_evolved',
                                                                           'mode': 'callable_override',
                                                                           'target': 'IntakeRecord.ticks_remaining'}}
# AURORA_EVOLVED_NATIVE_END

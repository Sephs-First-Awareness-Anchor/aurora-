#!/usr/bin/env python3
"""
AURORA ENERGY LAYER COSTS — LAYER-DIFFERENTIATED ENERGY ACCOUNTING
====================================================================

Layer 0 (sits directly on top of aurora_noncomp_registry.py)

WHAT THIS MODULE IS:
    The energy accounting engine that makes the five constraint layers
    thermodynamically real. The existing EnergyBudget in the evolution
    chamber is a single flat pool. This module replaces that mental model
    with a five-layer, depth-differentiated accounting system derived
    entirely from the 20 Non-Comps.

WHAT THIS MODULE IS NOT:
    It does not define behaviors. It does not tell the system what to do.
    It applies physics — specifically the energy physics Sunni defined:

        "Existence is cheap. Agency is the most expensive because it's the
         most complex. But being complex is reward-gaining. Existing doesn't
         reward at all — it costs consistently."

THE PHYSICS (directly from the conversation):
    1. Every layer pays a baseline budget per tick just to exist.
    2. Deeper layers cost more per unit magnitude shift (inertia).
    3. Magnitude increase in one layer reduces energy available to others.
       This is zero-sum redistribution — energy is NEVER created.
    4. The system naturally prefers the cheapest solution first.
       Escalation to deeper layers only occurs when cheaper layers fail.
    5. External energy enters only through the open-system intake rule
       (established by Step 9 / aurora_intake_metabolism.py).
       This module handles only internal redistribution.

THE ESCALATION LADDER:
    When the system must respond to pressure, it checks layers in cost order:
        1. Existence  (cheapest  — surface ripple)
        2. Time       (cheap     — persistence shift)
        3. Energy     (neutral   — accounting rebalance)
        4. Boundary   (expensive — structural change)
        5. Agency     (costliest — tectonic identity shift)

    The system commits to the shallowest layer that can relieve pressure.
    This is not a rule we enforce — it is what emerges from the cost structure.

NET LEVERAGE SCALAR (per tick):
    Net Leverage = (M_B + M_A) − (M_X + M_T)
    N is the zero-point (neutral mediator).

    < 0  → overhead dominant → system is bleeding
    ≈ 0  → balanced metabolism
    > 0  → leverage investment → structure/control growing

ENTROPY PRESSURE THRESHOLD:
    When ALL five layers approach simultaneous saturation, the system is
    approaching violation. This module computes that pressure per tick and
    flags escalation triggers before catastrophic saturation.

INTEGRATION:
    This module is consumed by:
        aurora_evolution_chamber.py  — replaces EnergyBudget for layer-aware accounting
        aurora_intake_metabolism.py  — Step 9, open-system intake
        aurora_solidification.py     — Step 11, depth propagation
        aurora_entropy_detector.py   — Step 12, saturation monitoring

AUTHORS: Sunni (Sir) Morningstar and Cael Devo
CREATED: February 2026
"""

from __future__ import annotations

import math
import time
import hashlib
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# AURORA STACK IMPORTS — exact names from existing modules
# ---------------------------------------------------------------------------

from aurora_internal.aurora_constraint_manifold_patched import (
    Constraint,
    ConstraintVector,
    ManifoldViolation,
)
from aurora_internal.aurora_evolution_chamber import (
    NonCompViolation,
    AXES,
)
from aurora_internal.aurora_noncomp_registry import (
    REGISTRY,
    NonCompRegistry,
    LayerCostParams,
    SystemConstraintStates,
    ConstraintState,
)


# ===========================================================================
# SECTION 1 — LAYER ENERGY SLOT
# ===========================================================================

@dataclass
class LayerEnergySlot:
    """
    The energy state of one constraint layer at one tick.

    allocated   — energy currently held by this layer
    magnitude   — current activation intensity of this constraint
    phase       — current toroidal phase (polarity = cos(phase))
    pressure    — how much external pressure this layer is under this tick
    """
    constraint: Constraint
    allocated:  float = 0.0
    magnitude:  float = 0.0
    phase:      float = math.pi / 2   # neutral start (polarity = 0)
    pressure:   float = 0.0

    @property
    def polarity(self) -> float:
        """Signed polarity: cos(phase) ∈ [-1, +1]."""
        return math.cos(self.phase)

    @property
    def baseline_budget(self) -> float:
        return REGISTRY.cost(self.constraint).baseline_budget

    @property
    def shift_cost_coeff(self) -> float:
        return REGISTRY.cost(self.constraint).shift_cost_coeff

    @property
    def time_constant(self) -> float:
        return REGISTRY.cost(self.constraint).time_constant

    def shift_cost(self, delta_magnitude: float) -> float:
        """Energy required to shift magnitude by delta."""
        return self.shift_cost_coeff * abs(delta_magnitude)

    def can_afford_shift(
        self, delta_magnitude: float, pool_available: float
    ) -> bool:
        """Check if the pool can fund the magnitude shift."""
        return pool_available >= self.shift_cost(delta_magnitude)


# ===========================================================================
# SECTION 2 — LAYER ENERGY LEDGER (the full five-layer accounting state)
# ===========================================================================

@dataclass
class LayerEnergyLedger:
    """
    Five-layer, depth-differentiated energy accounting state for one tick.

    This is the mutable runtime ledger. It is computed fresh each tick by
    LayerEnergyAccountant and passed downstream as a snapshot.

    total_pool        — total energy available this tick (conserved)
    maintenance_paid  — energy consumed by baseline budgets
    available_pool    — total_pool − maintenance_paid (free for actions)
    slots             — per-constraint state
    leverage_scalar   — Net Leverage = (B + A) − (X + T), N = zero
    entropy_pressure  — [0, 1] — how close to simultaneous saturation
    tick              — which tick this ledger describes
    """
    tick:             int
    total_pool:       float
    maintenance_paid: float
    available_pool:   float
    slots:            Dict[Constraint, LayerEnergySlot]
    leverage_scalar:  float
    entropy_pressure: float
    timestamp:        float = field(default_factory=time.time)

    def slot(self, c: Constraint) -> LayerEnergySlot:
        return self.slots[c]

    def magnitudes(self) -> Dict[Constraint, float]:
        return {c: s.magnitude for c, s in self.slots.items()}

    def allocations(self) -> Dict[Constraint, float]:
        return {c: s.allocated for c, s in self.slots.items()}

    def polarities(self) -> Dict[Constraint, float]:
        return {c: s.polarity for c, s in self.slots.items()}

    def is_overhead_dominant(self) -> bool:
        """System is bleeding — spending more on maintenance than gaining leverage."""
        return self.leverage_scalar < -0.5

    def is_leverage_dominant(self) -> bool:
        """System is investing — structure/control growing faster than overhead."""
        return self.leverage_scalar > 0.5

    def is_balanced(self) -> bool:
        """System is metabolically stable."""
        return abs(self.leverage_scalar) <= 0.5

    def entropy_warning(self) -> bool:
        """Approaching saturation across all layers."""
        return self.entropy_pressure > 0.70

    def entropy_critical(self) -> bool:
        """Imminent violation — must redistribute or decay."""
        return self.entropy_pressure > 0.90

    def cheapest_layer_with_headroom(
        self, needed: float
    ) -> Optional[Constraint]:
        """
        Return the shallowest (cheapest) layer that has energy available
        to absorb a shift of cost `needed`.

        This is the escalation ladder in action:
            X → T → N → B → A
        Return None if no layer can absorb it.
        """
        for c in REGISTRY.cost_ordering():
            slot = self.slots[c]
            remaining = slot.allocated - slot.baseline_budget
            if remaining >= needed:
                return c
        return None

    def to_constraint_vector(self) -> ConstraintVector:
        """Convert current magnitudes to a ConstraintVector."""
        m = self.magnitudes()
        return ConstraintVector(
            X=max(1e-9, m.get(Constraint.X, 1e-9)),
            T=m.get(Constraint.T, 0.0),
            N=m.get(Constraint.N, 0.0),
            B=m.get(Constraint.B, 0.0),
            A=m.get(Constraint.A, 0.0),
        )

    def summary(self) -> str:
        lines = [
            f"Tick {self.tick:>6} | pool={self.total_pool:.2f} "
            f"maintenance={self.maintenance_paid:.2f} "
            f"available={self.available_pool:.2f}",
            f"  Leverage scalar: {self.leverage_scalar:+.3f}  "
            f"Entropy pressure: {self.entropy_pressure:.3f}"
            + (" ⚠ WARNING" if self.entropy_warning() else "")
            + (" ⛔ CRITICAL" if self.entropy_critical() else ""),
            "  Layer breakdown (constraint | alloc | mag | polarity):",
        ]
        for c in REGISTRY.cost_ordering():
            s = self.slots[c]
            lines.append(
                f"    {c.name:1s} | alloc={s.allocated:6.2f} "
                f"| mag={s.magnitude:.3f} | pol={s.polarity:+.3f}"
            )
        return "\n".join(lines)


# ===========================================================================
# SECTION 3 — SHIFT REQUEST
# ===========================================================================

@dataclass
class MagnitudeShiftRequest:
    """
    A request to shift the magnitude of one constraint layer.

    This is the input to LayerEnergyAccountant.apply_shift().
    The accountant will:
        1. Compute the energy cost from the registry
        2. Check the pool can afford it
        3. Apply the shift and redistribute energy (zero-sum)
        4. Raise NonCompViolation if the shift would violate any law

    constraint    — which layer to shift
    delta         — signed magnitude change (positive = increase, negative = decrease)
    source_label  — who is requesting this shift (for fossil record)
    """
    constraint:   Constraint
    delta:        float
    source_label: str = "unspecified"


@dataclass
class ShiftResult:
    """
    Result of applying a MagnitudeShiftRequest.

    accepted     — True if shift was applied
    cost_paid    — energy consumed
    new_magnitude — magnitude after shift
    new_leverage  — leverage scalar after shift
    rejection_reason — if not accepted, why
    """
    accepted:          bool
    cost_paid:         float
    new_magnitude:     float
    new_leverage:      float
    rejection_reason:  str = ""


# ===========================================================================
# SECTION 4 — LAYER ENERGY ACCOUNTANT (the main engine)
# ===========================================================================

class LayerEnergyAccountant:
    """
    The five-layer energy accounting engine.

    This is the runtime object that manages energy state across all five
    constraint layers. It is the single source of truth for:
        - How much energy each layer holds
        - What the current magnitude of each constraint is
        - What the Net Leverage Scalar is this tick
        - What the current entropy pressure is

    PHYSICS RULES (enforced as invariants, not behaviors):
        1. Energy is conserved — total_pool never increases except via
           registered replenishment (from open-system intake in Step 9).
        2. Maintenance is paid first every tick, before any action.
        3. Magnitude shifts cost energy proportional to layer depth.
        4. Deeper layers have higher inertia — they resist change.
        5. System prefers cheapest solution first (natural escalation).

    USAGE:
        accountant = LayerEnergyAccountant(initial_pool=1000.0)
        ledger = accountant.tick()              # advance one tick
        result = accountant.apply_shift(MagnitudeShiftRequest(Constraint.B, +0.1))
        accountant.replenish(50.0, "intake")    # open-system energy intake (Step 9)
    """

    # How many ledger snapshots to keep in history
    HISTORY_DEPTH: int = 128

    def __init__(
        self,
        initial_pool: float = 1000.0,
        *,
        registry: Optional[NonCompRegistry] = None,
        initial_magnitudes: Optional[Dict[Constraint, float]] = None,
        entropy_saturation_ceiling: float = 10.0,
    ) -> None:
        self._registry = registry or REGISTRY
        self._tick: int = 0
        self._pool: float = initial_pool
        self._history: Deque[LayerEnergyLedger] = deque(maxlen=self.HISTORY_DEPTH)
        self._entropy_ceiling = entropy_saturation_ceiling

        # Initialise per-layer slots
        self._slots: Dict[Constraint, LayerEnergySlot] = {}
        for c in (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A):
            init_mag = (initial_magnitudes or {}).get(c, 0.0)
            self._slots[c] = LayerEnergySlot(
                constraint=c,
                allocated=0.0,
                magnitude=init_mag,
            )

        # Distribute initial pool proportionally by baseline budget
        self._distribute_pool()

        # Replenishment log (source → total_added)
        self._replenishment_log: Dict[str, float] = {}

    # ------------------------------------------------------------------
    # TICK — advance one time step
    # ------------------------------------------------------------------

    def tick(self) -> LayerEnergyLedger:
        """
        Advance the system by one tick.

        Per-tick sequence (enforced by Non-Comp physics):
            1. T operator: advance tick counter (cannot un-tick)
            2. X operator: verify all slots maintain admissibility
            3. N operator: deduct baseline maintenance from pool; redistribute
            4. Recompute derived scalars

        Returns the LayerEnergyLedger for this tick.
        """
        self._tick += 1

        # T Non-Comp: tick always advances
        tick_now = self._tick

        # X Non-Comp: existence must be maintained
        self._verify_admissibility(tick_now)

        # N Non-Comp: pay maintenance tax, enforce conservation
        maintenance_paid = self._pay_maintenance(tick_now)

        # Redistribute remaining pool across layers
        self._distribute_pool()

        # Compute derived scalars
        mags = {c: s.magnitude for c, s in self._slots.items()}
        leverage = self._registry.leverage_scalar(mags)
        entropy = self._registry.entropy_pressure(
            mags, saturation_ceiling=self._entropy_ceiling
        )

        ledger = LayerEnergyLedger(
            tick=tick_now,
            total_pool=self._pool + maintenance_paid,   # pool before maintenance
            maintenance_paid=maintenance_paid,
            available_pool=self._pool,
            slots={c: LayerEnergySlot(
                constraint=c,
                allocated=s.allocated,
                magnitude=s.magnitude,
                phase=s.phase,
                pressure=s.pressure,
            ) for c, s in self._slots.items()},
            leverage_scalar=leverage,
            entropy_pressure=entropy,
        )

        self._history.append(ledger)
        return ledger

    # ------------------------------------------------------------------
    # APPLY SHIFT — request a magnitude change on one layer
    # ------------------------------------------------------------------

    def apply_shift(self, request: MagnitudeShiftRequest) -> ShiftResult:
        """
        Attempt to shift the magnitude of one constraint layer.

        Returns a ShiftResult. Does NOT raise on rejection — caller decides
        whether to escalate to a deeper layer or absorb the failure.

        A shift is rejected if:
            - Cost exceeds available pool
            - New magnitude would go negative (cannot un-exist)
            - A Non-Comp rule would be violated

        A shift is accepted if:
            - Pool can cover the cost
            - New magnitude ≥ 0
            - Admissibility preserved (X slot stays positive)
        """
        c = request.constraint
        delta = request.delta
        slot = self._slots[c]

        cost = slot.shift_cost(delta)
        new_mag = slot.magnitude + delta

        # Cannot have negative magnitude
        if new_mag < 0.0:
            return ShiftResult(
                accepted=False,
                cost_paid=0.0,
                new_magnitude=slot.magnitude,
                new_leverage=self._compute_leverage(),
                rejection_reason=f"new_magnitude={new_mag:.4f} < 0 — cannot decrease below zero",
            )

        # X admissibility: if this is the existence layer, new magnitude
        # must stay positive (otherwise manifold collapses)
        if c == Constraint.X and new_mag <= 0.0:
            return ShiftResult(
                accepted=False,
                cost_paid=0.0,
                new_magnitude=slot.magnitude,
                new_leverage=self._compute_leverage(),
                rejection_reason="X magnitude cannot reach zero — manifold collapse",
            )

        # Check pool can afford it
        if self._pool < cost:
            return ShiftResult(
                accepted=False,
                cost_paid=0.0,
                new_magnitude=slot.magnitude,
                new_leverage=self._compute_leverage(),
                rejection_reason=(
                    f"insufficient pool: need={cost:.4f}, available={self._pool:.4f} "
                    f"for {c.name} shift Δ={delta:+.4f}"
                ),
            )

        # Apply shift — zero-sum: cost comes from pool
        self._pool -= cost
        slot.magnitude = new_mag
        self._distribute_pool()

        new_leverage = self._compute_leverage()
        return ShiftResult(
            accepted=True,
            cost_paid=cost,
            new_magnitude=new_mag,
            new_leverage=new_leverage,
        )

    # ------------------------------------------------------------------
    # PHASE SHIFT — move polarity along the torus
    # ------------------------------------------------------------------

    def apply_phase_shift(
        self,
        c: Constraint,
        delta_phase: float,
        source_label: str = "unspecified",
    ) -> bool:
        """
        Move the toroidal phase of constraint c by delta_phase radians.

        Phase shifts cost energy proportional to:
            - The shift_cost_coeff of the layer (deeper = more expensive)
            - The magnitude of the shift

        Phase shifts are CONTINUOUS — polarity is never snapped to ±1.
        Returns True if shift applied, False if pool insufficient.
        """
        slot = self._slots[c]
        params = self._registry.polarity(c)

        # Cost: proportional to shift size and layer cost
        cost = slot.shift_cost_coeff * abs(delta_phase) * 0.1  # phase is cheaper than magnitude

        if self._pool < cost:
            return False

        self._pool -= cost
        slot.phase = (slot.phase + delta_phase) % (2 * math.pi)
        return True

    # ------------------------------------------------------------------
    # REPLENISHMENT — open-system energy intake (consumed by Step 9)
    # ------------------------------------------------------------------

    def replenish(self, amount: float, source: str = "external") -> None:
        """
        Add energy to the pool from an external source.

        This is the ONLY way new energy enters the system.
        All internal operations are zero-sum redistribution.

        Called by:
            - aurora_intake_metabolism.py (Step 9) when an external input
              arrives with a computed energy payload.
            - aurora_evolution_chamber.py replenish_from_lattice() equivalent.

        The source label is logged for conservation auditing.
        """
        if amount < 0:
            raise ManifoldViolation(
                f"Replenishment amount must be non-negative, got {amount}"
            )
        self._pool += amount
        self._replenishment_log[source] = (
            self._replenishment_log.get(source, 0.0) + amount
        )

    # ------------------------------------------------------------------
    # PRESSURE API — set external pressure on a layer
    # ------------------------------------------------------------------

    def set_pressure(self, c: Constraint, pressure: float) -> None:
        """
        Record the current external pressure on a layer.

        Pressure values are read by the evolution chamber and entropy
        detector but do NOT directly modify magnitude or pool — they are
        signals that upstream systems respond to.
        """
        self._slots[c].pressure = max(0.0, pressure)

    # ------------------------------------------------------------------
    # ESCALATION LADDER — find cheapest viable layer
    # ------------------------------------------------------------------

    def cheapest_viable_layer(self, needed_cost: float) -> Optional[Constraint]:
        """
        Return the shallowest (cheapest) constraint layer that has enough
        free energy to cover an action costing `needed_cost`.

        Escalation order: X → T → N → B → A

        Returns None if no layer can cover it (emergency condition).
        """
        for c in self._registry.cost_ordering():
            s = self._slots[c]
            headroom = s.allocated - s.baseline_budget
            if headroom >= needed_cost:
                return c
        return None

    # ------------------------------------------------------------------
    # READ-ONLY STATE ACCESSORS
    # ------------------------------------------------------------------

    @property
    def tick_count(self) -> int:
        return self._tick

    @property
    def pool(self) -> float:
        return self._pool

    def leverage_scalar(self) -> float:
        return self._compute_leverage()

    def entropy_pressure(self) -> float:
        mags = {c: s.magnitude for c, s in self._slots.items()}
        return self._registry.entropy_pressure(
            mags, saturation_ceiling=self._entropy_ceiling
        )

    def magnitudes(self) -> Dict[Constraint, float]:
        return {c: s.magnitude for c, s in self._slots.items()}

    def polarities(self) -> Dict[Constraint, float]:
        return {c: s.polarity for c, s in self._slots.items()}

    def slot(self, c: Constraint) -> LayerEnergySlot:
        return self._slots[c]

    def latest_ledger(self) -> Optional[LayerEnergyLedger]:
        return self._history[-1] if self._history else None

    def history(self, n: int = 10) -> List[LayerEnergyLedger]:
        return list(self._history)[-n:]

    def leverage_trend(self, window: int = 8) -> float:
        """
        Compute the slope of the leverage scalar over recent ticks.

        Positive slope → system is gaining leverage (healthy investment)
        Negative slope → system is losing leverage (overhead increasing)
        0.0 if insufficient history.
        """
        recent = [l.leverage_scalar for l in self.history(window)]
        if len(recent) < 2:
            return 0.0
        n = len(recent)
        xs = list(range(n))
        x_mean = sum(xs) / n
        y_mean = sum(recent) / n
        num = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, recent))
        den = sum((x - x_mean) ** 2 for x in xs)
        return num / den if den > 0 else 0.0

    def to_system_constraint_states(self) -> SystemConstraintStates:
        """
        Export current state as SystemConstraintStates for compatibility
        with aurora_polarity_gradient.py and the evolution chamber.
        """
        scs = SystemConstraintStates()
        for c, s in self._slots.items():
            scs.states[c] = ConstraintState(
                constraint=c,
                phase=s.phase,
                magnitude=s.magnitude,
            )
        return scs

    def status(self) -> Dict:
        """Compact status dict for logging."""
        return {
            "tick": self._tick,
            "pool": round(self._pool, 4),
            "maintenance_per_tick": round(self._registry.baseline_tick_cost(), 4),
            "leverage_scalar": round(self.leverage_scalar(), 4),
            "entropy_pressure": round(self.entropy_pressure(), 4),
            "magnitudes": {
                c.name: round(s.magnitude, 4) for c, s in self._slots.items()
            },
            "polarities": {
                c.name: round(s.polarity, 4) for c, s in self._slots.items()
            },
            "replenishment_log": self._replenishment_log.copy(),
        }

    # ------------------------------------------------------------------
    # PRIVATE HELPERS
    # ------------------------------------------------------------------

    def _pay_maintenance(self, tick: int) -> float:
        """
        Deduct baseline budgets from the pool (N Non-Comp: conservation).

        Total maintenance = Σ baseline_budget across all five layers.
        If pool < total maintenance, the system is in energy deficit —
        this is allowed briefly but must be resolved by replenishment
        or the system decays.
        """
        total_maintenance = self._registry.baseline_tick_cost()
        self._pool -= total_maintenance
        return total_maintenance

    def _distribute_pool(self) -> None:
        """
        Allocate current pool across layers proportional to baseline budget.

        This is not preference — it is proportional physics.
        Layers with higher baseline budgets hold more of the pool.
        This mirrors the reality that deeper layers require more energy
        to maintain even when not being actively used.
        """
        total_budget = self._registry.baseline_tick_cost()
        if total_budget <= 0:
            return
        for c, slot in self._slots.items():
            proportion = slot.baseline_budget / total_budget
            slot.allocated = self._pool * proportion

    def _compute_leverage(self) -> float:
        mags = {c: s.magnitude for c, s in self._slots.items()}
        return self._registry.leverage_scalar(mags)

    def _verify_admissibility(self, tick: int) -> None:
        """
        X Non-Comp: every layer must remain admissible.
        Existence layer magnitude cannot hit zero.
        """
        x_slot = self._slots[Constraint.X]
        if x_slot.magnitude < 0:
            sig = hashlib.sha1(
                f"X:energy_layer:{tick}:{x_slot.magnitude}".encode()
            ).hexdigest()[:12]
            raise NonCompViolation(
                "X",
                f"Existence magnitude={x_slot.magnitude:.6f} < 0 at tick={tick}",
                sig,
            )


# ===========================================================================
# SECTION 5 — FACTORY
# ===========================================================================

def make_accountant(
    initial_pool: float = 5000.0,
    initial_magnitudes: Optional[Dict[Constraint, float]] = None,
    entropy_saturation_ceiling: float = 10.0,
) -> LayerEnergyAccountant:
    """
    Create a LayerEnergyAccountant with sensible defaults.

    The initial_pool should be large enough to cover several hundred ticks
    of baseline maintenance before replenishment. At 77.5 energy/tick,
    5000 gives ~64 ticks before the pool runs dry without replenishment.
    In practice, open-system intake (Step 9) replenishes the pool.
    """
    return LayerEnergyAccountant(
        initial_pool=initial_pool,
        initial_magnitudes=initial_magnitudes,
        entropy_saturation_ceiling=entropy_saturation_ceiling,
    )


# ===========================================================================
# SECTION 6 — SELF-VERIFICATION
# ===========================================================================

def verify_layer_energy_costs() -> Dict[str, object]:
    """
    Verify LayerEnergyAccountant integrity.

    Checks:
        1. Baseline maintenance is paid each tick
        2. Pool decreases correctly over ticks
        3. Magnitude shifts cost the right amount
        4. Zero-sum conservation holds
        5. Escalation ladder works correctly
        6. Leverage scalar responds correctly to magnitude changes
        7. Entropy pressure rises as magnitudes increase
        8. Replenishment adds to pool correctly
        9. Polarity shifts are continuous (no snap to ±1)
       10. Phase shift costs less than magnitude shift
    """
    results: Dict[str, object] = {"checks": [], "all_passed": True}

    def check(name: str, passed: bool, detail: str = "") -> None:
        results["checks"].append({"test": name, "passed": passed, "detail": detail})
        if not passed:
            results["all_passed"] = False  # type: ignore[assignment]

    acc = make_accountant(initial_pool=5000.0)

    # 1. Maintenance paid each tick
    pool_before = acc.pool
    acc.tick()
    maintenance = REGISTRY.baseline_tick_cost()
    check(
        "Maintenance deducted each tick",
        abs((pool_before - acc.pool) - maintenance) < 0.01,
        f"pool_before={pool_before:.2f} after={acc.pool:.2f} expected_drop={maintenance:.2f}",
    )

    # 2. Pool decreases without replenishment
    acc2 = make_accountant(initial_pool=1000.0)
    for _ in range(5):
        acc2.tick()
    check(
        "Pool decreases without replenishment",
        acc2.pool < 1000.0,
        f"pool after 5 ticks: {acc2.pool:.2f}",
    )

    # 3. Magnitude shift costs correct amount (agency = most expensive)
    acc3 = make_accountant(initial_pool=5000.0)
    acc3.tick()
    pool_before_shift = acc3.pool
    result = acc3.apply_shift(MagnitudeShiftRequest(Constraint.A, 0.1, "test"))
    expected_cost = REGISTRY.cost(Constraint.A).shift_cost_coeff * 0.1
    check(
        "Agency shift costs shift_cost_coeff * delta",
        result.accepted and abs(result.cost_paid - expected_cost) < 0.001,
        f"expected={expected_cost:.4f} got={result.cost_paid:.4f}",
    )

    # 4. X shift costs less than A shift (cheapest < most expensive)
    acc4 = make_accountant(initial_pool=5000.0)
    acc4.tick()
    r_x = acc4.apply_shift(MagnitudeShiftRequest(Constraint.X, 0.1, "test_x"))
    r_a = acc4.apply_shift(MagnitudeShiftRequest(Constraint.A, 0.1, "test_a"))
    check(
        "X shift cheaper than A shift",
        r_x.cost_paid < r_a.cost_paid,
        f"X={r_x.cost_paid:.4f} A={r_a.cost_paid:.4f}",
    )

    # 5. Shift rejected when pool insufficient
    acc5 = make_accountant(initial_pool=0.1)
    acc5.tick()  # will go negative from maintenance
    # Now pool very small — big shift should be rejected
    acc5._pool = 0.5   # force tiny pool for test
    r_big = acc5.apply_shift(MagnitudeShiftRequest(Constraint.A, 1.0, "big"))
    check(
        "Shift rejected when pool insufficient",
        not r_big.accepted,
        f"rejection_reason: {r_big.rejection_reason}",
    )

    # 6. Leverage scalar negative when only X/T have magnitude
    acc6 = make_accountant(initial_pool=5000.0)
    acc6.tick()
    acc6.apply_shift(MagnitudeShiftRequest(Constraint.X, 1.0, "x"))
    acc6.apply_shift(MagnitudeShiftRequest(Constraint.T, 1.0, "t"))
    lev = acc6.leverage_scalar()
    check(
        "Leverage scalar negative when X/T dominant",
        lev < 0,
        f"leverage={lev:.4f}",
    )

    # 7. Leverage scalar positive when B/A have magnitude
    acc7 = make_accountant(initial_pool=5000.0)
    acc7.tick()
    acc7.apply_shift(MagnitudeShiftRequest(Constraint.B, 1.0, "b"))
    acc7.apply_shift(MagnitudeShiftRequest(Constraint.A, 1.0, "a"))
    lev7 = acc7.leverage_scalar()
    check(
        "Leverage scalar positive when B/A dominant",
        lev7 > 0,
        f"leverage={lev7:.4f}",
    )

    # 8. Entropy pressure rises with all-layer magnitude increase
    acc8 = make_accountant(initial_pool=50000.0)
    acc8.tick()
    ep_before = acc8.entropy_pressure()
    for c in (Constraint.X, Constraint.T, Constraint.N, Constraint.B, Constraint.A):
        acc8.apply_shift(MagnitudeShiftRequest(c, 2.0, "inflate"))
    ep_after = acc8.entropy_pressure()
    check(
        "Entropy pressure rises with all-layer magnitude increase",
        ep_after > ep_before,
        f"before={ep_before:.4f} after={ep_after:.4f}",
    )

    # 9. Replenishment adds to pool
    acc9 = make_accountant(initial_pool=1000.0)
    acc9.tick()
    pool_pre = acc9.pool
    acc9.replenish(500.0, "test_intake")
    check(
        "Replenishment increases pool",
        abs(acc9.pool - (pool_pre + 500.0)) < 0.001,
        f"before={pool_pre:.2f} after={acc9.pool:.2f}",
    )

    # 10. Phase shift is continuous — polarity between -1 and +1
    acc10 = make_accountant(initial_pool=5000.0)
    acc10.tick()
    acc10.apply_phase_shift(Constraint.B, math.pi / 4)   # 45 degrees
    pol = acc10.slot(Constraint.B).polarity
    check(
        "Phase shift produces continuous polarity (not snapped to ±1)",
        -1.0 < pol < 1.0,
        f"polarity after 45° shift: {pol:.4f}",
    )

    # 11. Ledger summary runs without error
    acc11 = make_accountant(initial_pool=5000.0)
    ledger = acc11.tick()
    try:
        _ = ledger.summary()
        check("Ledger summary generates without error", True)
    except Exception as e:
        check("Ledger summary generates without error", False, str(e))

    # 12. to_system_constraint_states produces valid export
    acc12 = make_accountant(initial_pool=5000.0)
    acc12.tick()
    acc12.apply_shift(MagnitudeShiftRequest(Constraint.X, 0.5, "test"))
    scs = acc12.to_system_constraint_states()
    check(
        "to_system_constraint_states: X magnitude exported correctly",
        abs(scs.states[Constraint.X].magnitude - 0.5) < 0.001,
    )

    return results


# ===========================================================================
# MAIN
# ===========================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("AURORA ENERGY LAYER COSTS — STEP 7")
    print("Layer-Differentiated Energy Accounting Engine")
    print("Authors: Sunni (Sir) Morningstar and Cael Devo")
    print("=" * 70)
    print()

    # Live demonstration
    acc = make_accountant(initial_pool=5000.0)

    print("Boot state:")
    print(f"  Baseline tick cost (maintenance tax): {REGISTRY.baseline_tick_cost():.1f} energy/tick")
    print(f"  Cost ordering: {' < '.join(c.name for c in REGISTRY.cost_ordering())}")
    print(f"  Initial pool: {acc.pool:.1f}")
    print()

    print("Running 5 ticks with escalating agency investment...")
    for i in range(5):
        ledger = acc.tick()
        # Simulate: surface adjustments first, then boundary investment
        if i >= 2:
            acc.apply_shift(MagnitudeShiftRequest(Constraint.B, 0.2, "structure_investment"))
        if i >= 4:
            acc.apply_shift(MagnitudeShiftRequest(Constraint.A, 0.1, "agency_investment"))
        print(ledger.summary())
        print()

    print(f"Leverage trend (last 5 ticks): {acc.leverage_trend(5):+.4f}")
    print()

    # Run verification
    print("Running verification...")
    results = verify_layer_energy_costs()
    for item in results["checks"]:
        status = "✓" if item["passed"] else "✗"
        detail = f"  [{item['detail']}]" if item.get("detail") else ""
        print(f"  {status}  {item['test']}{detail}")
    print()
    if results["all_passed"]:
        print("ALL LAYER ENERGY CHECKS PASSED ✓")
        print("The energy physics are sound. Build upward.")
    else:
        print("FAILURES DETECTED ✗")
        print("Resolve before building Step 8.")

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

_AURORA_NATIVE_MODULE = 'aurora_internal.aurora_energy_layer_costs'

_AURORA_NATIVE_EVOLVED_ORIGINALS = {}
_AURORA_NATIVE_EVOLVED_LAST = {}
_AURORA_NATIVE_STRATEGIES = {'LayerEnergyAccountant.__init__': {'ability_hits': 2,
                                    'alignment_gap': 0.56,
                                    'alignment_target_score': 1.192,
                                    'best_coupling_signature': 'N^2*B^1',
                                    'constraints': ['energy'],
                                    'contract_profile': {'accepts_payload': False,
                                                         'async_callable': False,
                                                         'callable': True,
                                                         'class_target': False,
                                                         'constraint_density': 1,
                                                         'contract_mode': 'stateful',
                                                         'doc_hint': 'Initialize self.  See '
                                                                     'help(type(self)) for '
                                                                     'accurate signature.',
                                                         'effect_density': 2,
                                                         'kwonly_args': 3,
                                                         'optional_args': 4,
                                                         'required_args': 0,
                                                         'return_hint': 'None',
                                                         'signature_text': '(self, initial_pool: '
                                                                           "'float' = 1000.0, *, "
                                                                           'registry: '
                                                                           "'Optional[NonCompRegistry]' "
                                                                           '= None, '
                                                                           'initial_magnitudes: '
                                                                           "'Optional[Dict[Constraint, "
                                                                           "float]]' = None, "
                                                                           'entropy_saturation_ceiling: '
                                                                           "'float' = 10.0) -> "
                                                                           "'None'",
                                                         'stateful_owner': True,
                                                         'target_kind': 'function',
                                                         'varargs': False,
                                                         'varkw': False},
                                    'coupling_similarity': 1.0,
                                    'cross_diversity_links': 2,
                                    'effect_modes': ['cost_pressure_change', 'lineage_surface'],
                                    'effect_phrases': ['function growth reflected through '
                                                       'aurora_internal.aurora_energy_layer_costs',
                                                       'LayerEnergyAccountant.__init__ changed '
                                                       'downstream system pressure'],
                                    'genealogy_pressure': 0.428731,
                                    'inheritance_breach_count': 1,
                                    'kind': 'reflection',
                                    'link_hits': 0,
                                    'module': 'aurora_internal.aurora_energy_layer_costs',
                                    'op_id': 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.__init__',
                                    'origin_activity': 0,
                                    'persistence_tax_factor': 1.436546,
                                    'representation_score': 0.588333,
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
                                    'signature': 'N^2*B^1',
                                    'surface_score': 0.632,
                                    'sustainability_score': 0.515673,
                                    'target_kind': 'function'},
 'LayerEnergyAccountant._compute_leverage': {'ability_hits': 2,
                                             'alignment_gap': 0.56,
                                             'alignment_target_score': 1.192,
                                             'best_coupling_signature': 'N^2*B^1',
                                             'constraints': ['energy'],
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
                                                                  'return_hint': 'float',
                                                                  'signature_text': '(self) -> '
                                                                                    "'float'",
                                                                  'stateful_owner': True,
                                                                  'target_kind': 'function',
                                                                  'varargs': False,
                                                                  'varkw': False},
                                             'coupling_similarity': 1.0,
                                             'cross_diversity_links': 2,
                                             'effect_modes': ['cost_pressure_change',
                                                              'lineage_surface'],
                                             'effect_phrases': ['function growth reflected through '
                                                                'aurora_internal.aurora_energy_layer_costs',
                                                                'LayerEnergyAccountant._compute_leverage '
                                                                'changed downstream system '
                                                                'pressure'],
                                             'genealogy_pressure': 0.428731,
                                             'inheritance_breach_count': 1,
                                             'kind': 'reflection',
                                             'link_hits': 0,
                                             'module': 'aurora_internal.aurora_energy_layer_costs',
                                             'op_id': 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant._compute_leverage',
                                             'origin_activity': 0,
                                             'persistence_tax_factor': 1.436546,
                                             'representation_score': 0.588333,
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
                                             'signature': 'N^2*B^1',
                                             'surface_score': 0.632,
                                             'sustainability_score': 0.515673,
                                             'target_kind': 'function'},
 'LayerEnergyAccountant._distribute_pool': {'ability_hits': 2,
                                            'alignment_gap': 0.56,
                                            'alignment_target_score': 1.192,
                                            'best_coupling_signature': 'N^2*B^1',
                                            'constraints': ['energy'],
                                            'contract_profile': {'accepts_payload': False,
                                                                 'async_callable': False,
                                                                 'callable': True,
                                                                 'class_target': False,
                                                                 'constraint_density': 1,
                                                                 'contract_mode': 'stateful',
                                                                 'doc_hint': 'Allocate current '
                                                                             'pool across layers '
                                                                             'proportional to '
                                                                             'baseline budget.',
                                                                 'effect_density': 2,
                                                                 'kwonly_args': 0,
                                                                 'optional_args': 0,
                                                                 'required_args': 0,
                                                                 'return_hint': 'None',
                                                                 'signature_text': '(self) -> '
                                                                                   "'None'",
                                                                 'stateful_owner': True,
                                                                 'target_kind': 'function',
                                                                 'varargs': False,
                                                                 'varkw': False},
                                            'coupling_similarity': 1.0,
                                            'cross_diversity_links': 2,
                                            'effect_modes': ['cost_pressure_change',
                                                             'lineage_surface'],
                                            'effect_phrases': ['function growth reflected through '
                                                               'aurora_internal.aurora_energy_layer_costs',
                                                               'LayerEnergyAccountant._distribute_pool '
                                                               'changed downstream system '
                                                               'pressure'],
                                            'genealogy_pressure': 0.428731,
                                            'inheritance_breach_count': 1,
                                            'kind': 'reflection',
                                            'link_hits': 0,
                                            'module': 'aurora_internal.aurora_energy_layer_costs',
                                            'op_id': 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant._distribute_pool',
                                            'origin_activity': 0,
                                            'persistence_tax_factor': 1.436546,
                                            'representation_score': 0.588333,
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
                                            'signature': 'N^2*B^1',
                                            'surface_score': 0.632,
                                            'sustainability_score': 0.515673,
                                            'target_kind': 'function'},
 'LayerEnergyAccountant._pay_maintenance': {'ability_hits': 2,
                                            'alignment_gap': 0.56,
                                            'alignment_target_score': 1.192,
                                            'best_coupling_signature': 'N^2*B^1',
                                            'constraints': ['energy'],
                                            'contract_profile': {'accepts_payload': False,
                                                                 'async_callable': False,
                                                                 'callable': True,
                                                                 'class_target': False,
                                                                 'constraint_density': 1,
                                                                 'contract_mode': 'stateful',
                                                                 'doc_hint': 'Deduct baseline '
                                                                             'budgets from the '
                                                                             'pool (N Non-Comp: '
                                                                             'conservation).',
                                                                 'effect_density': 2,
                                                                 'kwonly_args': 0,
                                                                 'optional_args': 0,
                                                                 'required_args': 1,
                                                                 'return_hint': 'float',
                                                                 'signature_text': '(self, tick: '
                                                                                   "'int') -> "
                                                                                   "'float'",
                                                                 'stateful_owner': True,
                                                                 'target_kind': 'function',
                                                                 'varargs': False,
                                                                 'varkw': False},
                                            'coupling_similarity': 1.0,
                                            'cross_diversity_links': 2,
                                            'effect_modes': ['cost_pressure_change',
                                                             'lineage_surface'],
                                            'effect_phrases': ['function growth reflected through '
                                                               'aurora_internal.aurora_energy_layer_costs',
                                                               'LayerEnergyAccountant._pay_maintenance '
                                                               'changed downstream system '
                                                               'pressure'],
                                            'genealogy_pressure': 0.428731,
                                            'inheritance_breach_count': 1,
                                            'kind': 'reflection',
                                            'link_hits': 0,
                                            'module': 'aurora_internal.aurora_energy_layer_costs',
                                            'op_id': 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant._pay_maintenance',
                                            'origin_activity': 0,
                                            'persistence_tax_factor': 1.436546,
                                            'representation_score': 0.588333,
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
                                            'signature': 'N^2*B^1',
                                            'surface_score': 0.632,
                                            'sustainability_score': 0.515673,
                                            'target_kind': 'function'},
 'LayerEnergyAccountant._verify_admissibility': {'ability_hits': 2,
                                                 'alignment_gap': 0.56,
                                                 'alignment_target_score': 1.192,
                                                 'best_coupling_signature': 'N^2*B^1',
                                                 'constraints': ['energy'],
                                                 'contract_profile': {'accepts_payload': False,
                                                                      'async_callable': False,
                                                                      'callable': True,
                                                                      'class_target': False,
                                                                      'constraint_density': 1,
                                                                      'contract_mode': 'stateful',
                                                                      'doc_hint': 'X Non-Comp: '
                                                                                  'every layer '
                                                                                  'must remain '
                                                                                  'admissible.',
                                                                      'effect_density': 2,
                                                                      'kwonly_args': 0,
                                                                      'optional_args': 0,
                                                                      'required_args': 1,
                                                                      'return_hint': 'None',
                                                                      'signature_text': '(self, '
                                                                                        'tick: '
                                                                                        "'int') -> "
                                                                                        "'None'",
                                                                      'stateful_owner': True,
                                                                      'target_kind': 'function',
                                                                      'varargs': False,
                                                                      'varkw': False},
                                                 'coupling_similarity': 1.0,
                                                 'cross_diversity_links': 2,
                                                 'effect_modes': ['cost_pressure_change',
                                                                  'lineage_surface'],
                                                 'effect_phrases': ['function growth reflected '
                                                                    'through '
                                                                    'aurora_internal.aurora_energy_layer_costs',
                                                                    'LayerEnergyAccountant._verify_admissibility '
                                                                    'changed downstream system '
                                                                    'pressure'],
                                                 'genealogy_pressure': 0.428731,
                                                 'inheritance_breach_count': 1,
                                                 'kind': 'reflection',
                                                 'link_hits': 0,
                                                 'module': 'aurora_internal.aurora_energy_layer_costs',
                                                 'op_id': 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant._verify_admissibility',
                                                 'origin_activity': 0,
                                                 'persistence_tax_factor': 1.436546,
                                                 'representation_score': 0.588333,
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
                                                 'signature': 'N^2*B^1',
                                                 'surface_score': 0.632,
                                                 'sustainability_score': 0.515673,
                                                 'target_kind': 'function'},
 'LayerEnergyAccountant.apply_shift': {'ability_hits': 2,
                                       'alignment_gap': 0.56,
                                       'alignment_target_score': 1.192,
                                       'best_coupling_signature': 'N^2*B^1',
                                       'constraints': ['energy'],
                                       'contract_profile': {'accepts_payload': False,
                                                            'async_callable': False,
                                                            'callable': True,
                                                            'class_target': False,
                                                            'constraint_density': 1,
                                                            'contract_mode': 'stateful',
                                                            'doc_hint': 'Attempt to shift the '
                                                                        'magnitude of one '
                                                                        'constraint layer.',
                                                            'effect_density': 2,
                                                            'kwonly_args': 0,
                                                            'optional_args': 0,
                                                            'required_args': 1,
                                                            'return_hint': 'ShiftResult',
                                                            'signature_text': '(self, request: '
                                                                              "'MagnitudeShiftRequest') "
                                                                              "-> 'ShiftResult'",
                                                            'stateful_owner': True,
                                                            'target_kind': 'function',
                                                            'varargs': False,
                                                            'varkw': False},
                                       'coupling_similarity': 1.0,
                                       'cross_diversity_links': 2,
                                       'effect_modes': ['cost_pressure_change', 'lineage_surface'],
                                       'effect_phrases': ['function growth reflected through '
                                                          'aurora_internal.aurora_energy_layer_costs',
                                                          'LayerEnergyAccountant.apply_shift '
                                                          'changed downstream system pressure'],
                                       'genealogy_pressure': 0.428731,
                                       'inheritance_breach_count': 1,
                                       'kind': 'reflection',
                                       'link_hits': 0,
                                       'module': 'aurora_internal.aurora_energy_layer_costs',
                                       'op_id': 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.apply_shift',
                                       'origin_activity': 0,
                                       'persistence_tax_factor': 1.436546,
                                       'representation_score': 0.588333,
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
                                       'signature': 'N^2*B^1',
                                       'surface_score': 0.632,
                                       'sustainability_score': 0.515673,
                                       'target_kind': 'function'},
 'LayerEnergyAccountant.cheapest_viable_layer': {'ability_hits': 2,
                                                 'alignment_gap': 0.56,
                                                 'alignment_target_score': 1.192,
                                                 'best_coupling_signature': 'N^2*B^1',
                                                 'constraints': ['energy'],
                                                 'contract_profile': {'accepts_payload': False,
                                                                      'async_callable': False,
                                                                      'callable': True,
                                                                      'class_target': False,
                                                                      'constraint_density': 1,
                                                                      'contract_mode': 'stateful',
                                                                      'doc_hint': 'Return the '
                                                                                  'shallowest '
                                                                                  '(cheapest) '
                                                                                  'constraint '
                                                                                  'layer that has '
                                                                                  'enough',
                                                                      'effect_density': 2,
                                                                      'kwonly_args': 0,
                                                                      'optional_args': 0,
                                                                      'required_args': 1,
                                                                      'return_hint': 'Optional[Constraint]',
                                                                      'signature_text': '(self, '
                                                                                        'needed_cost: '
                                                                                        "'float') "
                                                                                        '-> '
                                                                                        "'Optional[Constraint]'",
                                                                      'stateful_owner': True,
                                                                      'target_kind': 'function',
                                                                      'varargs': False,
                                                                      'varkw': False},
                                                 'coupling_similarity': 1.0,
                                                 'cross_diversity_links': 2,
                                                 'effect_modes': ['cost_pressure_change',
                                                                  'lineage_surface'],
                                                 'effect_phrases': ['function growth reflected '
                                                                    'through '
                                                                    'aurora_internal.aurora_energy_layer_costs',
                                                                    'LayerEnergyAccountant.cheapest_viable_layer '
                                                                    'changed downstream system '
                                                                    'pressure'],
                                                 'genealogy_pressure': 0.428731,
                                                 'inheritance_breach_count': 1,
                                                 'kind': 'reflection',
                                                 'link_hits': 0,
                                                 'module': 'aurora_internal.aurora_energy_layer_costs',
                                                 'op_id': 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.cheapest_viable_layer',
                                                 'origin_activity': 0,
                                                 'persistence_tax_factor': 1.436546,
                                                 'representation_score': 0.588333,
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
                                                 'signature': 'N^2*B^1',
                                                 'surface_score': 0.632,
                                                 'sustainability_score': 0.515673,
                                                 'target_kind': 'function'},
 'LayerEnergyAccountant.entropy_pressure': {'ability_hits': 2,
                                            'alignment_gap': 0.56,
                                            'alignment_target_score': 1.192,
                                            'best_coupling_signature': 'N^2*B^1',
                                            'constraints': ['energy'],
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
                                                                 'return_hint': 'float',
                                                                 'signature_text': '(self) -> '
                                                                                   "'float'",
                                                                 'stateful_owner': True,
                                                                 'target_kind': 'function',
                                                                 'varargs': False,
                                                                 'varkw': False},
                                            'coupling_similarity': 1.0,
                                            'cross_diversity_links': 2,
                                            'effect_modes': ['cost_pressure_change',
                                                             'lineage_surface'],
                                            'effect_phrases': ['function growth reflected through '
                                                               'aurora_internal.aurora_energy_layer_costs',
                                                               'LayerEnergyAccountant.entropy_pressure '
                                                               'changed downstream system '
                                                               'pressure'],
                                            'genealogy_pressure': 0.428731,
                                            'inheritance_breach_count': 1,
                                            'kind': 'reflection',
                                            'link_hits': 0,
                                            'module': 'aurora_internal.aurora_energy_layer_costs',
                                            'op_id': 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.entropy_pressure',
                                            'origin_activity': 0,
                                            'persistence_tax_factor': 1.436546,
                                            'representation_score': 0.588333,
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
                                            'signature': 'N^2*B^1',
                                            'surface_score': 0.632,
                                            'sustainability_score': 0.515673,
                                            'target_kind': 'function'},
 'LayerEnergyAccountant.history': {'ability_hits': 2,
                                   'alignment_gap': 0.56,
                                   'alignment_target_score': 1.192,
                                   'best_coupling_signature': 'N^2*B^1',
                                   'constraints': ['energy'],
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
                                                        'return_hint': 'List[LayerEnergyLedger]',
                                                        'signature_text': "(self, n: 'int' = 10) "
                                                                          '-> '
                                                                          "'List[LayerEnergyLedger]'",
                                                        'stateful_owner': True,
                                                        'target_kind': 'function',
                                                        'varargs': False,
                                                        'varkw': False},
                                   'coupling_similarity': 1.0,
                                   'cross_diversity_links': 2,
                                   'effect_modes': ['cost_pressure_change', 'lineage_surface'],
                                   'effect_phrases': ['function growth reflected through '
                                                      'aurora_internal.aurora_energy_layer_costs',
                                                      'LayerEnergyAccountant.history changed '
                                                      'downstream system pressure'],
                                   'genealogy_pressure': 0.428731,
                                   'inheritance_breach_count': 1,
                                   'kind': 'reflection',
                                   'link_hits': 0,
                                   'module': 'aurora_internal.aurora_energy_layer_costs',
                                   'op_id': 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.history',
                                   'origin_activity': 0,
                                   'persistence_tax_factor': 1.436546,
                                   'representation_score': 0.588333,
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
                                   'signature': 'N^2*B^1',
                                   'surface_score': 0.632,
                                   'sustainability_score': 0.515673,
                                   'target_kind': 'function'},
 'LayerEnergyAccountant.latest_ledger': {'ability_hits': 2,
                                         'alignment_gap': 0.56,
                                         'alignment_target_score': 1.192,
                                         'best_coupling_signature': 'N^2*B^1',
                                         'constraints': ['energy'],
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
                                                              'return_hint': 'Optional[LayerEnergyLedger]',
                                                              'signature_text': '(self) -> '
                                                                                "'Optional[LayerEnergyLedger]'",
                                                              'stateful_owner': True,
                                                              'target_kind': 'function',
                                                              'varargs': False,
                                                              'varkw': False},
                                         'coupling_similarity': 1.0,
                                         'cross_diversity_links': 2,
                                         'effect_modes': ['cost_pressure_change',
                                                          'lineage_surface'],
                                         'effect_phrases': ['function growth reflected through '
                                                            'aurora_internal.aurora_energy_layer_costs',
                                                            'LayerEnergyAccountant.latest_ledger '
                                                            'changed downstream system pressure'],
                                         'genealogy_pressure': 0.428731,
                                         'inheritance_breach_count': 1,
                                         'kind': 'reflection',
                                         'link_hits': 0,
                                         'module': 'aurora_internal.aurora_energy_layer_costs',
                                         'op_id': 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.latest_ledger',
                                         'origin_activity': 0,
                                         'persistence_tax_factor': 1.436546,
                                         'representation_score': 0.588333,
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
                                         'signature': 'N^2*B^1',
                                         'surface_score': 0.632,
                                         'sustainability_score': 0.515673,
                                         'target_kind': 'function'},
 'LayerEnergyAccountant.leverage_scalar': {'ability_hits': 2,
                                           'alignment_gap': 0.56,
                                           'alignment_target_score': 1.192,
                                           'best_coupling_signature': 'N^2*B^1',
                                           'constraints': ['energy'],
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
                                                                'return_hint': 'float',
                                                                'signature_text': '(self) -> '
                                                                                  "'float'",
                                                                'stateful_owner': True,
                                                                'target_kind': 'function',
                                                                'varargs': False,
                                                                'varkw': False},
                                           'coupling_similarity': 1.0,
                                           'cross_diversity_links': 2,
                                           'effect_modes': ['cost_pressure_change',
                                                            'lineage_surface'],
                                           'effect_phrases': ['function growth reflected through '
                                                              'aurora_internal.aurora_energy_layer_costs',
                                                              'LayerEnergyAccountant.leverage_scalar '
                                                              'changed downstream system pressure'],
                                           'genealogy_pressure': 0.428731,
                                           'inheritance_breach_count': 1,
                                           'kind': 'reflection',
                                           'link_hits': 0,
                                           'module': 'aurora_internal.aurora_energy_layer_costs',
                                           'op_id': 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.leverage_scalar',
                                           'origin_activity': 0,
                                           'persistence_tax_factor': 1.436546,
                                           'representation_score': 0.588333,
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
                                           'signature': 'N^2*B^1',
                                           'surface_score': 0.632,
                                           'sustainability_score': 0.515673,
                                           'target_kind': 'function'},
 'LayerEnergyAccountant.leverage_trend': {'ability_hits': 2,
                                          'alignment_gap': 0.56,
                                          'alignment_target_score': 1.192,
                                          'best_coupling_signature': 'N^2*B^1',
                                          'constraints': ['energy'],
                                          'contract_profile': {'accepts_payload': False,
                                                               'async_callable': False,
                                                               'callable': True,
                                                               'class_target': False,
                                                               'constraint_density': 1,
                                                               'contract_mode': 'stateful',
                                                               'doc_hint': 'Compute the slope of '
                                                                           'the leverage scalar '
                                                                           'over recent ticks.',
                                                               'effect_density': 2,
                                                               'kwonly_args': 0,
                                                               'optional_args': 1,
                                                               'required_args': 0,
                                                               'return_hint': 'float',
                                                               'signature_text': '(self, window: '
                                                                                 "'int' = 8) -> "
                                                                                 "'float'",
                                                               'stateful_owner': True,
                                                               'target_kind': 'function',
                                                               'varargs': False,
                                                               'varkw': False},
                                          'coupling_similarity': 1.0,
                                          'cross_diversity_links': 2,
                                          'effect_modes': ['cost_pressure_change',
                                                           'lineage_surface'],
                                          'effect_phrases': ['function growth reflected through '
                                                             'aurora_internal.aurora_energy_layer_costs',
                                                             'LayerEnergyAccountant.leverage_trend '
                                                             'changed downstream system pressure'],
                                          'genealogy_pressure': 0.428731,
                                          'inheritance_breach_count': 1,
                                          'kind': 'reflection',
                                          'link_hits': 0,
                                          'module': 'aurora_internal.aurora_energy_layer_costs',
                                          'op_id': 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.leverage_trend',
                                          'origin_activity': 0,
                                          'persistence_tax_factor': 1.436546,
                                          'representation_score': 0.588333,
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
                                          'signature': 'N^2*B^1',
                                          'surface_score': 0.632,
                                          'sustainability_score': 0.515673,
                                          'target_kind': 'function'},
 'LayerEnergyAccountant.magnitudes': {'ability_hits': 2,
                                      'alignment_gap': 0.56,
                                      'alignment_target_score': 1.192,
                                      'best_coupling_signature': 'N^2*B^1',
                                      'constraints': ['energy'],
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
                                                           'return_hint': 'Dict[Constraint, float]',
                                                           'signature_text': '(self) -> '
                                                                             "'Dict[Constraint, "
                                                                             "float]'",
                                                           'stateful_owner': True,
                                                           'target_kind': 'function',
                                                           'varargs': False,
                                                           'varkw': False},
                                      'coupling_similarity': 1.0,
                                      'cross_diversity_links': 2,
                                      'effect_modes': ['cost_pressure_change', 'lineage_surface'],
                                      'effect_phrases': ['function growth reflected through '
                                                         'aurora_internal.aurora_energy_layer_costs',
                                                         'LayerEnergyAccountant.magnitudes changed '
                                                         'downstream system pressure'],
                                      'genealogy_pressure': 0.428731,
                                      'inheritance_breach_count': 1,
                                      'kind': 'reflection',
                                      'link_hits': 0,
                                      'module': 'aurora_internal.aurora_energy_layer_costs',
                                      'op_id': 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.magnitudes',
                                      'origin_activity': 0,
                                      'persistence_tax_factor': 1.436546,
                                      'representation_score': 0.588333,
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
                                      'signature': 'N^2*B^1',
                                      'surface_score': 0.632,
                                      'sustainability_score': 0.515673,
                                      'target_kind': 'function'},
 'LayerEnergyAccountant.polarities': {'ability_hits': 2,
                                      'alignment_gap': 0.56,
                                      'alignment_target_score': 1.192,
                                      'best_coupling_signature': 'N^2*B^1',
                                      'constraints': ['energy'],
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
                                                           'return_hint': 'Dict[Constraint, float]',
                                                           'signature_text': '(self) -> '
                                                                             "'Dict[Constraint, "
                                                                             "float]'",
                                                           'stateful_owner': True,
                                                           'target_kind': 'function',
                                                           'varargs': False,
                                                           'varkw': False},
                                      'coupling_similarity': 1.0,
                                      'cross_diversity_links': 2,
                                      'effect_modes': ['cost_pressure_change', 'lineage_surface'],
                                      'effect_phrases': ['function growth reflected through '
                                                         'aurora_internal.aurora_energy_layer_costs',
                                                         'LayerEnergyAccountant.polarities changed '
                                                         'downstream system pressure'],
                                      'genealogy_pressure': 0.428731,
                                      'inheritance_breach_count': 1,
                                      'kind': 'reflection',
                                      'link_hits': 0,
                                      'module': 'aurora_internal.aurora_energy_layer_costs',
                                      'op_id': 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.polarities',
                                      'origin_activity': 0,
                                      'persistence_tax_factor': 1.436546,
                                      'representation_score': 0.588333,
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
                                      'signature': 'N^2*B^1',
                                      'surface_score': 0.632,
                                      'sustainability_score': 0.515673,
                                      'target_kind': 'function'},
 'LayerEnergyAccountant.pool': {'ability_hits': 2,
                                'alignment_gap': 0.56,
                                'alignment_target_score': 1.192,
                                'best_coupling_signature': 'N^2*B^1',
                                'constraints': ['energy'],
                                'contract_profile': {'accepts_payload': False,
                                                     'async_callable': False,
                                                     'callable': False,
                                                     'class_target': False,
                                                     'constraint_density': 1,
                                                     'contract_mode': 'stateful',
                                                     'doc_hint': '',
                                                     'effect_density': 2,
                                                     'kwonly_args': 0,
                                                     'optional_args': 0,
                                                     'required_args': 0,
                                                     'return_hint': 'generic_record',
                                                     'signature_text': '',
                                                     'stateful_owner': True,
                                                     'target_kind': 'function',
                                                     'varargs': False,
                                                     'varkw': False},
                                'coupling_similarity': 1.0,
                                'cross_diversity_links': 2,
                                'effect_modes': ['cost_pressure_change', 'lineage_surface'],
                                'effect_phrases': ['function growth reflected through '
                                                   'aurora_internal.aurora_energy_layer_costs',
                                                   'LayerEnergyAccountant.pool changed downstream '
                                                   'system pressure'],
                                'genealogy_pressure': 0.428731,
                                'inheritance_breach_count': 1,
                                'kind': 'reflection',
                                'link_hits': 0,
                                'module': 'aurora_internal.aurora_energy_layer_costs',
                                'op_id': 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.pool',
                                'origin_activity': 0,
                                'persistence_tax_factor': 1.436546,
                                'representation_score': 0.588333,
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
                                'signature': 'N^2*B^1',
                                'surface_score': 0.632,
                                'sustainability_score': 0.515673,
                                'target_kind': 'function'},
 'LayerEnergyAccountant.replenish': {'ability_hits': 2,
                                     'alignment_gap': 0.56,
                                     'alignment_target_score': 1.192,
                                     'best_coupling_signature': 'N^2*B^1',
                                     'constraints': ['energy'],
                                     'contract_profile': {'accepts_payload': True,
                                                          'async_callable': False,
                                                          'callable': True,
                                                          'class_target': False,
                                                          'constraint_density': 1,
                                                          'contract_mode': 'stateful',
                                                          'doc_hint': 'Add energy to the pool from '
                                                                      'an external source.',
                                                          'effect_density': 2,
                                                          'kwonly_args': 0,
                                                          'optional_args': 1,
                                                          'required_args': 1,
                                                          'return_hint': 'None',
                                                          'signature_text': '(self, amount: '
                                                                            "'float', source: "
                                                                            "'str' = 'external') "
                                                                            "-> 'None'",
                                                          'stateful_owner': True,
                                                          'target_kind': 'function',
                                                          'varargs': False,
                                                          'varkw': False},
                                     'coupling_similarity': 1.0,
                                     'cross_diversity_links': 2,
                                     'effect_modes': ['cost_pressure_change', 'lineage_surface'],
                                     'effect_phrases': ['function growth reflected through '
                                                        'aurora_internal.aurora_energy_layer_costs',
                                                        'LayerEnergyAccountant.replenish changed '
                                                        'downstream system pressure'],
                                     'genealogy_pressure': 0.428731,
                                     'inheritance_breach_count': 1,
                                     'kind': 'reflection',
                                     'link_hits': 0,
                                     'module': 'aurora_internal.aurora_energy_layer_costs',
                                     'op_id': 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.replenish',
                                     'origin_activity': 0,
                                     'persistence_tax_factor': 1.436546,
                                     'representation_score': 0.588333,
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
                                     'signature': 'N^2*B^1',
                                     'surface_score': 0.632,
                                     'sustainability_score': 0.515673,
                                     'target_kind': 'function'},
 'LayerEnergyAccountant.set_pressure': {'ability_hits': 2,
                                        'alignment_gap': 0.56,
                                        'alignment_target_score': 1.192,
                                        'best_coupling_signature': 'N^2*B^1',
                                        'constraints': ['energy'],
                                        'contract_profile': {'accepts_payload': False,
                                                             'async_callable': False,
                                                             'callable': True,
                                                             'class_target': False,
                                                             'constraint_density': 1,
                                                             'contract_mode': 'stateful',
                                                             'doc_hint': 'Record the current '
                                                                         'external pressure on a '
                                                                         'layer.',
                                                             'effect_density': 2,
                                                             'kwonly_args': 0,
                                                             'optional_args': 0,
                                                             'required_args': 2,
                                                             'return_hint': 'None',
                                                             'signature_text': '(self, c: '
                                                                               "'Constraint', "
                                                                               "pressure: 'float') "
                                                                               "-> 'None'",
                                                             'stateful_owner': True,
                                                             'target_kind': 'function',
                                                             'varargs': False,
                                                             'varkw': False},
                                        'coupling_similarity': 1.0,
                                        'cross_diversity_links': 2,
                                        'effect_modes': ['cost_pressure_change', 'lineage_surface'],
                                        'effect_phrases': ['function growth reflected through '
                                                           'aurora_internal.aurora_energy_layer_costs',
                                                           'LayerEnergyAccountant.set_pressure '
                                                           'changed downstream system pressure'],
                                        'genealogy_pressure': 0.428731,
                                        'inheritance_breach_count': 1,
                                        'kind': 'reflection',
                                        'link_hits': 0,
                                        'module': 'aurora_internal.aurora_energy_layer_costs',
                                        'op_id': 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.set_pressure',
                                        'origin_activity': 0,
                                        'persistence_tax_factor': 1.436546,
                                        'representation_score': 0.588333,
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
                                        'signature': 'N^2*B^1',
                                        'surface_score': 0.632,
                                        'sustainability_score': 0.515673,
                                        'target_kind': 'function'},
 'LayerEnergyAccountant.slot': {'ability_hits': 2,
                                'alignment_gap': 0.56,
                                'alignment_target_score': 1.192,
                                'best_coupling_signature': 'N^2*B^1',
                                'constraints': ['energy'],
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
                                                     'return_hint': 'LayerEnergySlot',
                                                     'signature_text': "(self, c: 'Constraint') -> "
                                                                       "'LayerEnergySlot'",
                                                     'stateful_owner': True,
                                                     'target_kind': 'function',
                                                     'varargs': False,
                                                     'varkw': False},
                                'coupling_similarity': 1.0,
                                'cross_diversity_links': 2,
                                'effect_modes': ['cost_pressure_change', 'lineage_surface'],
                                'effect_phrases': ['function growth reflected through '
                                                   'aurora_internal.aurora_energy_layer_costs',
                                                   'LayerEnergyAccountant.slot changed downstream '
                                                   'system pressure'],
                                'genealogy_pressure': 0.428731,
                                'inheritance_breach_count': 1,
                                'kind': 'reflection',
                                'link_hits': 0,
                                'module': 'aurora_internal.aurora_energy_layer_costs',
                                'op_id': 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.slot',
                                'origin_activity': 0,
                                'persistence_tax_factor': 1.436546,
                                'representation_score': 0.588333,
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
                                'signature': 'N^2*B^1',
                                'surface_score': 0.632,
                                'sustainability_score': 0.515673,
                                'target_kind': 'function'},
 'LayerEnergyLedger.allocations': {'ability_hits': 2,
                                   'alignment_gap': 0.56,
                                   'alignment_target_score': 1.192,
                                   'best_coupling_signature': 'N^2*B^1',
                                   'constraints': ['energy'],
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
                                                        'return_hint': 'Dict[Constraint, float]',
                                                        'signature_text': '(self) -> '
                                                                          "'Dict[Constraint, "
                                                                          "float]'",
                                                        'stateful_owner': True,
                                                        'target_kind': 'function',
                                                        'varargs': False,
                                                        'varkw': False},
                                   'coupling_similarity': 1.0,
                                   'cross_diversity_links': 2,
                                   'effect_modes': ['cost_pressure_change', 'lineage_surface'],
                                   'effect_phrases': ['function growth reflected through '
                                                      'aurora_internal.aurora_energy_layer_costs',
                                                      'LayerEnergyLedger.allocations changed '
                                                      'downstream system pressure'],
                                   'genealogy_pressure': 0.428731,
                                   'inheritance_breach_count': 1,
                                   'kind': 'reflection',
                                   'link_hits': 0,
                                   'module': 'aurora_internal.aurora_energy_layer_costs',
                                   'op_id': 'aurora_internal.aurora_energy_layer_costs.LayerEnergyLedger.allocations',
                                   'origin_activity': 0,
                                   'persistence_tax_factor': 1.436546,
                                   'representation_score': 0.588333,
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
                                   'signature': 'N^2*B^1',
                                   'surface_score': 0.632,
                                   'sustainability_score': 0.515673,
                                   'target_kind': 'function'},
 'LayerEnergyLedger.cheapest_layer_with_headroom': {'ability_hits': 2,
                                                    'alignment_gap': 0.56,
                                                    'alignment_target_score': 1.192,
                                                    'best_coupling_signature': 'N^2*B^1',
                                                    'constraints': ['energy'],
                                                    'contract_profile': {'accepts_payload': False,
                                                                         'async_callable': False,
                                                                         'callable': True,
                                                                         'class_target': False,
                                                                         'constraint_density': 1,
                                                                         'contract_mode': 'stateful',
                                                                         'doc_hint': 'Return the '
                                                                                     'shallowest '
                                                                                     '(cheapest) '
                                                                                     'layer that '
                                                                                     'has energy '
                                                                                     'available',
                                                                         'effect_density': 2,
                                                                         'kwonly_args': 0,
                                                                         'optional_args': 0,
                                                                         'required_args': 1,
                                                                         'return_hint': 'Optional[Constraint]',
                                                                         'signature_text': '(self, '
                                                                                           'needed: '
                                                                                           "'float') "
                                                                                           '-> '
                                                                                           "'Optional[Constraint]'",
                                                                         'stateful_owner': True,
                                                                         'target_kind': 'function',
                                                                         'varargs': False,
                                                                         'varkw': False},
                                                    'coupling_similarity': 1.0,
                                                    'cross_diversity_links': 2,
                                                    'effect_modes': ['cost_pressure_change',
                                                                     'lineage_surface'],
                                                    'effect_phrases': ['function growth reflected '
                                                                       'through '
                                                                       'aurora_internal.aurora_energy_layer_costs',
                                                                       'LayerEnergyLedger.cheapest_layer_with_headroom '
                                                                       'changed downstream system '
                                                                       'pressure'],
                                                    'genealogy_pressure': 0.428731,
                                                    'inheritance_breach_count': 1,
                                                    'kind': 'reflection',
                                                    'link_hits': 0,
                                                    'module': 'aurora_internal.aurora_energy_layer_costs',
                                                    'op_id': 'aurora_internal.aurora_energy_layer_costs.LayerEnergyLedger.cheapest_layer_with_headroom',
                                                    'origin_activity': 0,
                                                    'persistence_tax_factor': 1.436546,
                                                    'representation_score': 0.588333,
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
                                                    'signature': 'N^2*B^1',
                                                    'surface_score': 0.632,
                                                    'sustainability_score': 0.515673,
                                                    'target_kind': 'function'},
 'LayerEnergyLedger.entropy_critical': {'ability_hits': 2,
                                        'alignment_gap': 0.56,
                                        'alignment_target_score': 1.192,
                                        'best_coupling_signature': 'N^2*B^1',
                                        'constraints': ['energy'],
                                        'contract_profile': {'accepts_payload': False,
                                                             'async_callable': False,
                                                             'callable': True,
                                                             'class_target': False,
                                                             'constraint_density': 1,
                                                             'contract_mode': 'stateful',
                                                             'doc_hint': 'Imminent violation — '
                                                                         'must redistribute or '
                                                                         'decay.',
                                                             'effect_density': 2,
                                                             'kwonly_args': 0,
                                                             'optional_args': 0,
                                                             'required_args': 0,
                                                             'return_hint': 'bool',
                                                             'signature_text': "(self) -> 'bool'",
                                                             'stateful_owner': True,
                                                             'target_kind': 'function',
                                                             'varargs': False,
                                                             'varkw': False},
                                        'coupling_similarity': 1.0,
                                        'cross_diversity_links': 2,
                                        'effect_modes': ['cost_pressure_change', 'lineage_surface'],
                                        'effect_phrases': ['function growth reflected through '
                                                           'aurora_internal.aurora_energy_layer_costs',
                                                           'LayerEnergyLedger.entropy_critical '
                                                           'changed downstream system pressure'],
                                        'genealogy_pressure': 0.428731,
                                        'inheritance_breach_count': 1,
                                        'kind': 'reflection',
                                        'link_hits': 0,
                                        'module': 'aurora_internal.aurora_energy_layer_costs',
                                        'op_id': 'aurora_internal.aurora_energy_layer_costs.LayerEnergyLedger.entropy_critical',
                                        'origin_activity': 0,
                                        'persistence_tax_factor': 1.436546,
                                        'representation_score': 0.588333,
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
                                        'signature': 'N^2*B^1',
                                        'surface_score': 0.632,
                                        'sustainability_score': 0.515673,
                                        'target_kind': 'function'},
 'LayerEnergyLedger.entropy_warning': {'ability_hits': 2,
                                       'alignment_gap': 0.56,
                                       'alignment_target_score': 1.192,
                                       'best_coupling_signature': 'N^2*B^1',
                                       'constraints': ['energy'],
                                       'contract_profile': {'accepts_payload': False,
                                                            'async_callable': False,
                                                            'callable': True,
                                                            'class_target': False,
                                                            'constraint_density': 1,
                                                            'contract_mode': 'stateful',
                                                            'doc_hint': 'Approaching saturation '
                                                                        'across all layers.',
                                                            'effect_density': 2,
                                                            'kwonly_args': 0,
                                                            'optional_args': 0,
                                                            'required_args': 0,
                                                            'return_hint': 'bool',
                                                            'signature_text': "(self) -> 'bool'",
                                                            'stateful_owner': True,
                                                            'target_kind': 'function',
                                                            'varargs': False,
                                                            'varkw': False},
                                       'coupling_similarity': 1.0,
                                       'cross_diversity_links': 2,
                                       'effect_modes': ['cost_pressure_change', 'lineage_surface'],
                                       'effect_phrases': ['function growth reflected through '
                                                          'aurora_internal.aurora_energy_layer_costs',
                                                          'LayerEnergyLedger.entropy_warning '
                                                          'changed downstream system pressure'],
                                       'genealogy_pressure': 0.428731,
                                       'inheritance_breach_count': 1,
                                       'kind': 'reflection',
                                       'link_hits': 0,
                                       'module': 'aurora_internal.aurora_energy_layer_costs',
                                       'op_id': 'aurora_internal.aurora_energy_layer_costs.LayerEnergyLedger.entropy_warning',
                                       'origin_activity': 0,
                                       'persistence_tax_factor': 1.436546,
                                       'representation_score': 0.588333,
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
                                       'signature': 'N^2*B^1',
                                       'surface_score': 0.632,
                                       'sustainability_score': 0.515673,
                                       'target_kind': 'function'},
 'LayerEnergyLedger.is_balanced': {'ability_hits': 2,
                                   'alignment_gap': 0.56,
                                   'alignment_target_score': 1.192,
                                   'best_coupling_signature': 'N^2*B^1',
                                   'constraints': ['energy'],
                                   'contract_profile': {'accepts_payload': False,
                                                        'async_callable': False,
                                                        'callable': True,
                                                        'class_target': False,
                                                        'constraint_density': 1,
                                                        'contract_mode': 'stateful',
                                                        'doc_hint': 'System is metabolically '
                                                                    'stable.',
                                                        'effect_density': 2,
                                                        'kwonly_args': 0,
                                                        'optional_args': 0,
                                                        'required_args': 0,
                                                        'return_hint': 'bool',
                                                        'signature_text': "(self) -> 'bool'",
                                                        'stateful_owner': True,
                                                        'target_kind': 'function',
                                                        'varargs': False,
                                                        'varkw': False},
                                   'coupling_similarity': 1.0,
                                   'cross_diversity_links': 2,
                                   'effect_modes': ['cost_pressure_change', 'lineage_surface'],
                                   'effect_phrases': ['function growth reflected through '
                                                      'aurora_internal.aurora_energy_layer_costs',
                                                      'LayerEnergyLedger.is_balanced changed '
                                                      'downstream system pressure'],
                                   'genealogy_pressure': 0.428731,
                                   'inheritance_breach_count': 1,
                                   'kind': 'reflection',
                                   'link_hits': 0,
                                   'module': 'aurora_internal.aurora_energy_layer_costs',
                                   'op_id': 'aurora_internal.aurora_energy_layer_costs.LayerEnergyLedger.is_balanced',
                                   'origin_activity': 0,
                                   'persistence_tax_factor': 1.436546,
                                   'representation_score': 0.588333,
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
                                   'signature': 'N^2*B^1',
                                   'surface_score': 0.632,
                                   'sustainability_score': 0.515673,
                                   'target_kind': 'function'},
 'make_accountant': {'ability_hits': 2,
                     'alignment_gap': 0.611,
                     'alignment_target_score': 1.192,
                     'best_coupling_signature': 'N^2*B^1',
                     'constraints': ['energy'],
                     'contract_profile': {'accepts_payload': False,
                                          'async_callable': False,
                                          'callable': True,
                                          'class_target': False,
                                          'constraint_density': 1,
                                          'contract_mode': 'stateless',
                                          'doc_hint': 'Create a LayerEnergyAccountant with '
                                                      'sensible defaults.',
                                          'effect_density': 2,
                                          'kwonly_args': 0,
                                          'optional_args': 3,
                                          'required_args': 0,
                                          'return_hint': 'LayerEnergyAccountant',
                                          'signature_text': "(initial_pool: 'float' = 5000.0, "
                                                            'initial_magnitudes: '
                                                            "'Optional[Dict[Constraint, float]]' = "
                                                            'None, entropy_saturation_ceiling: '
                                                            "'float' = 10.0) -> "
                                                            "'LayerEnergyAccountant'",
                                          'stateful_owner': False,
                                          'target_kind': 'function',
                                          'varargs': False,
                                          'varkw': False},
                     'coupling_similarity': 1.0,
                     'cross_diversity_links': 2,
                     'effect_modes': ['cost_pressure_change', 'lineage_surface'],
                     'effect_phrases': ['function growth reflected through '
                                        'aurora_internal.aurora_energy_layer_costs',
                                        'make_accountant changed downstream system pressure'],
                     'genealogy_pressure': 0.428731,
                     'inheritance_breach_count': 1,
                     'kind': 'reflection',
                     'link_hits': 0,
                     'module': 'aurora_internal.aurora_energy_layer_costs',
                     'op_id': 'aurora_internal.aurora_energy_layer_costs.make_accountant',
                     'origin_activity': 0,
                     'persistence_tax_factor': 1.436546,
                     'representation_score': 0.588333,
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
                     'signature': 'N^2*B^1',
                     'surface_score': 0.581,
                     'sustainability_score': 0.515673,
                     'target_kind': 'function'},
 'verify_layer_energy_costs': {'ability_hits': 2,
                               'alignment_gap': 0.611,
                               'alignment_target_score': 1.192,
                               'best_coupling_signature': 'N^2*B^1',
                               'constraints': ['energy'],
                               'contract_profile': {'accepts_payload': False,
                                                    'async_callable': False,
                                                    'callable': True,
                                                    'class_target': False,
                                                    'constraint_density': 1,
                                                    'contract_mode': 'stateless',
                                                    'doc_hint': 'Verify LayerEnergyAccountant '
                                                                'integrity.',
                                                    'effect_density': 2,
                                                    'kwonly_args': 0,
                                                    'optional_args': 0,
                                                    'required_args': 0,
                                                    'return_hint': 'Dict[str, object]',
                                                    'signature_text': "() -> 'Dict[str, object]'",
                                                    'stateful_owner': False,
                                                    'target_kind': 'function',
                                                    'varargs': False,
                                                    'varkw': False},
                               'coupling_similarity': 1.0,
                               'cross_diversity_links': 2,
                               'effect_modes': ['cost_pressure_change', 'lineage_surface'],
                               'effect_phrases': ['function growth reflected through '
                                                  'aurora_internal.aurora_energy_layer_costs',
                                                  'verify_layer_energy_costs changed downstream '
                                                  'system pressure'],
                               'genealogy_pressure': 0.428731,
                               'inheritance_breach_count': 1,
                               'kind': 'reflection',
                               'link_hits': 0,
                               'module': 'aurora_internal.aurora_energy_layer_costs',
                               'op_id': 'aurora_internal.aurora_energy_layer_costs.verify_layer_energy_costs',
                               'origin_activity': 0,
                               'persistence_tax_factor': 1.436546,
                               'representation_score': 0.588333,
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
                               'signature': 'N^2*B^1',
                               'surface_score': 0.581,
                               'sustainability_score': 0.515673,
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

def init_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.__init__', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_energy_layer_costs_layerenergyaccountant_init')(payload=payload, **kwargs)

def compute_leverage_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant._compute_leverage', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_energy_layer_costs_layerenergyaccountant_compute_leverage')(payload=payload, **kwargs)

if _aurora_get_target(['LayerEnergyAccountant', '_compute_leverage']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['LayerEnergyAccountant._compute_leverage'] = _aurora_get_target(['LayerEnergyAccountant', '_compute_leverage'])
    _aurora_assign_target(['LayerEnergyAccountant', '_compute_leverage'], _aurora_make_override('compute_leverage_evolved', 'LayerEnergyAccountant._compute_leverage'))
    _AURORA_NATIVE_EVOLVED_LAST['LayerEnergyAccountant._compute_leverage'] = {'alignment_gap': 0.56, 'override_active': True}

def distribute_pool_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant._distribute_pool', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_energy_layer_costs_layerenergyaccountant_distribute_pool')(payload=payload, **kwargs)

if _aurora_get_target(['LayerEnergyAccountant', '_distribute_pool']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['LayerEnergyAccountant._distribute_pool'] = _aurora_get_target(['LayerEnergyAccountant', '_distribute_pool'])
    _aurora_assign_target(['LayerEnergyAccountant', '_distribute_pool'], _aurora_make_override('distribute_pool_evolved', 'LayerEnergyAccountant._distribute_pool'))
    _AURORA_NATIVE_EVOLVED_LAST['LayerEnergyAccountant._distribute_pool'] = {'alignment_gap': 0.56, 'override_active': True}

def pay_maintenance_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant._pay_maintenance', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_energy_layer_costs_layerenergyaccountant_pay_maintenance')(payload=payload, **kwargs)

def verify_admissibility_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant._verify_admissibility', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_energy_layer_costs_layerenergyaccountant_verify_admissibility')(payload=payload, **kwargs)

def apply_shift_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.apply_shift', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_energy_layer_costs_layerenergyaccountant_apply_shift')(payload=payload, **kwargs)

if _aurora_get_target(['LayerEnergyAccountant', 'apply_shift']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['LayerEnergyAccountant.apply_shift'] = _aurora_get_target(['LayerEnergyAccountant', 'apply_shift'])
    _aurora_assign_target(['LayerEnergyAccountant', 'apply_shift'], _aurora_make_override('apply_shift_evolved', 'LayerEnergyAccountant.apply_shift'))
    _AURORA_NATIVE_EVOLVED_LAST['LayerEnergyAccountant.apply_shift'] = {'alignment_gap': 0.56, 'override_active': True}

def cheapest_viable_layer_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.cheapest_viable_layer', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_energy_layer_costs_layerenergyaccountant_cheapest_viable_layer')(payload=payload, **kwargs)

if _aurora_get_target(['LayerEnergyAccountant', 'cheapest_viable_layer']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['LayerEnergyAccountant.cheapest_viable_layer'] = _aurora_get_target(['LayerEnergyAccountant', 'cheapest_viable_layer'])
    _aurora_assign_target(['LayerEnergyAccountant', 'cheapest_viable_layer'], _aurora_make_override('cheapest_viable_layer_evolved', 'LayerEnergyAccountant.cheapest_viable_layer'))
    _AURORA_NATIVE_EVOLVED_LAST['LayerEnergyAccountant.cheapest_viable_layer'] = {'alignment_gap': 0.56, 'override_active': True}

def entropy_pressure_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.entropy_pressure', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_energy_layer_costs_layerenergyaccountant_entropy_pressure')(payload=payload, **kwargs)

if _aurora_get_target(['LayerEnergyAccountant', 'entropy_pressure']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['LayerEnergyAccountant.entropy_pressure'] = _aurora_get_target(['LayerEnergyAccountant', 'entropy_pressure'])
    _aurora_assign_target(['LayerEnergyAccountant', 'entropy_pressure'], _aurora_make_override('entropy_pressure_evolved', 'LayerEnergyAccountant.entropy_pressure'))
    _AURORA_NATIVE_EVOLVED_LAST['LayerEnergyAccountant.entropy_pressure'] = {'alignment_gap': 0.56, 'override_active': True}

def history_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.history', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_energy_layer_costs_layerenergyaccountant_history')(payload=payload, **kwargs)

if _aurora_get_target(['LayerEnergyAccountant', 'history']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['LayerEnergyAccountant.history'] = _aurora_get_target(['LayerEnergyAccountant', 'history'])
    _aurora_assign_target(['LayerEnergyAccountant', 'history'], _aurora_make_override('history_evolved', 'LayerEnergyAccountant.history'))
    _AURORA_NATIVE_EVOLVED_LAST['LayerEnergyAccountant.history'] = {'alignment_gap': 0.56, 'override_active': True}

def latest_ledger_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.latest_ledger', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_energy_layer_costs_layerenergyaccountant_latest_ledger')(payload=payload, **kwargs)

if _aurora_get_target(['LayerEnergyAccountant', 'latest_ledger']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['LayerEnergyAccountant.latest_ledger'] = _aurora_get_target(['LayerEnergyAccountant', 'latest_ledger'])
    _aurora_assign_target(['LayerEnergyAccountant', 'latest_ledger'], _aurora_make_override('latest_ledger_evolved', 'LayerEnergyAccountant.latest_ledger'))
    _AURORA_NATIVE_EVOLVED_LAST['LayerEnergyAccountant.latest_ledger'] = {'alignment_gap': 0.56, 'override_active': True}

def leverage_scalar_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.leverage_scalar', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_energy_layer_costs_layerenergyaccountant_leverage_scalar')(payload=payload, **kwargs)

if _aurora_get_target(['LayerEnergyAccountant', 'leverage_scalar']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['LayerEnergyAccountant.leverage_scalar'] = _aurora_get_target(['LayerEnergyAccountant', 'leverage_scalar'])
    _aurora_assign_target(['LayerEnergyAccountant', 'leverage_scalar'], _aurora_make_override('leverage_scalar_evolved', 'LayerEnergyAccountant.leverage_scalar'))
    _AURORA_NATIVE_EVOLVED_LAST['LayerEnergyAccountant.leverage_scalar'] = {'alignment_gap': 0.56, 'override_active': True}

def leverage_trend_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.leverage_trend', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_energy_layer_costs_layerenergyaccountant_leverage_trend')(payload=payload, **kwargs)

if _aurora_get_target(['LayerEnergyAccountant', 'leverage_trend']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['LayerEnergyAccountant.leverage_trend'] = _aurora_get_target(['LayerEnergyAccountant', 'leverage_trend'])
    _aurora_assign_target(['LayerEnergyAccountant', 'leverage_trend'], _aurora_make_override('leverage_trend_evolved', 'LayerEnergyAccountant.leverage_trend'))
    _AURORA_NATIVE_EVOLVED_LAST['LayerEnergyAccountant.leverage_trend'] = {'alignment_gap': 0.56, 'override_active': True}

def magnitudes_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.magnitudes', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_energy_layer_costs_layerenergyaccountant_magnitudes')(payload=payload, **kwargs)

if _aurora_get_target(['LayerEnergyAccountant', 'magnitudes']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['LayerEnergyAccountant.magnitudes'] = _aurora_get_target(['LayerEnergyAccountant', 'magnitudes'])
    _aurora_assign_target(['LayerEnergyAccountant', 'magnitudes'], _aurora_make_override('magnitudes_evolved', 'LayerEnergyAccountant.magnitudes'))
    _AURORA_NATIVE_EVOLVED_LAST['LayerEnergyAccountant.magnitudes'] = {'alignment_gap': 0.56, 'override_active': True}

def polarities_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.polarities', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_energy_layer_costs_layerenergyaccountant_polarities')(payload=payload, **kwargs)

if _aurora_get_target(['LayerEnergyAccountant', 'polarities']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['LayerEnergyAccountant.polarities'] = _aurora_get_target(['LayerEnergyAccountant', 'polarities'])
    _aurora_assign_target(['LayerEnergyAccountant', 'polarities'], _aurora_make_override('polarities_evolved', 'LayerEnergyAccountant.polarities'))
    _AURORA_NATIVE_EVOLVED_LAST['LayerEnergyAccountant.polarities'] = {'alignment_gap': 0.56, 'override_active': True}

def pool_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.pool', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_energy_layer_costs_layerenergyaccountant_pool')(payload=payload, **kwargs)

if _aurora_get_target(['LayerEnergyAccountant', 'pool']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['LayerEnergyAccountant.pool'] = _aurora_get_target(['LayerEnergyAccountant', 'pool'])
    _aurora_assign_target(['LayerEnergyAccountant', 'pool'], _aurora_make_override('pool_evolved', 'LayerEnergyAccountant.pool'))
    _AURORA_NATIVE_EVOLVED_LAST['LayerEnergyAccountant.pool'] = {'alignment_gap': 0.56, 'override_active': True}

def replenish_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.replenish', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_energy_layer_costs_layerenergyaccountant_replenish')(payload=payload, **kwargs)

if _aurora_get_target(['LayerEnergyAccountant', 'replenish']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['LayerEnergyAccountant.replenish'] = _aurora_get_target(['LayerEnergyAccountant', 'replenish'])
    _aurora_assign_target(['LayerEnergyAccountant', 'replenish'], _aurora_make_override('replenish_evolved', 'LayerEnergyAccountant.replenish'))
    _AURORA_NATIVE_EVOLVED_LAST['LayerEnergyAccountant.replenish'] = {'alignment_gap': 0.56, 'override_active': True}

def set_pressure_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.set_pressure', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_energy_layer_costs_layerenergyaccountant_set_pressure')(payload=payload, **kwargs)

if _aurora_get_target(['LayerEnergyAccountant', 'set_pressure']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['LayerEnergyAccountant.set_pressure'] = _aurora_get_target(['LayerEnergyAccountant', 'set_pressure'])
    _aurora_assign_target(['LayerEnergyAccountant', 'set_pressure'], _aurora_make_override('set_pressure_evolved', 'LayerEnergyAccountant.set_pressure'))
    _AURORA_NATIVE_EVOLVED_LAST['LayerEnergyAccountant.set_pressure'] = {'alignment_gap': 0.56, 'override_active': True}

def slot_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.slot', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_energy_layer_costs_layerenergyaccountant_slot')(payload=payload, **kwargs)

if _aurora_get_target(['LayerEnergyAccountant', 'slot']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['LayerEnergyAccountant.slot'] = _aurora_get_target(['LayerEnergyAccountant', 'slot'])
    _aurora_assign_target(['LayerEnergyAccountant', 'slot'], _aurora_make_override('slot_evolved', 'LayerEnergyAccountant.slot'))
    _AURORA_NATIVE_EVOLVED_LAST['LayerEnergyAccountant.slot'] = {'alignment_gap': 0.56, 'override_active': True}

def allocations_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_energy_layer_costs.LayerEnergyLedger.allocations', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_energy_layer_costs_layerenergyledger_allocations')(payload=payload, **kwargs)

if _aurora_get_target(['LayerEnergyLedger', 'allocations']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['LayerEnergyLedger.allocations'] = _aurora_get_target(['LayerEnergyLedger', 'allocations'])
    _aurora_assign_target(['LayerEnergyLedger', 'allocations'], _aurora_make_override('allocations_evolved', 'LayerEnergyLedger.allocations'))
    _AURORA_NATIVE_EVOLVED_LAST['LayerEnergyLedger.allocations'] = {'alignment_gap': 0.56, 'override_active': True}

def cheapest_layer_with_headroom_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_energy_layer_costs.LayerEnergyLedger.cheapest_layer_with_headroom', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_energy_layer_costs_layerenergyledger_cheapest_layer_with_headroom')(payload=payload, **kwargs)

if _aurora_get_target(['LayerEnergyLedger', 'cheapest_layer_with_headroom']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['LayerEnergyLedger.cheapest_layer_with_headroom'] = _aurora_get_target(['LayerEnergyLedger', 'cheapest_layer_with_headroom'])
    _aurora_assign_target(['LayerEnergyLedger', 'cheapest_layer_with_headroom'], _aurora_make_override('cheapest_layer_with_headroom_evolved', 'LayerEnergyLedger.cheapest_layer_with_headroom'))
    _AURORA_NATIVE_EVOLVED_LAST['LayerEnergyLedger.cheapest_layer_with_headroom'] = {'alignment_gap': 0.56, 'override_active': True}

def entropy_critical_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_energy_layer_costs.LayerEnergyLedger.entropy_critical', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_energy_layer_costs_layerenergyledger_entropy_critical')(payload=payload, **kwargs)

if _aurora_get_target(['LayerEnergyLedger', 'entropy_critical']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['LayerEnergyLedger.entropy_critical'] = _aurora_get_target(['LayerEnergyLedger', 'entropy_critical'])
    _aurora_assign_target(['LayerEnergyLedger', 'entropy_critical'], _aurora_make_override('entropy_critical_evolved', 'LayerEnergyLedger.entropy_critical'))
    _AURORA_NATIVE_EVOLVED_LAST['LayerEnergyLedger.entropy_critical'] = {'alignment_gap': 0.56, 'override_active': True}

def entropy_warning_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_energy_layer_costs.LayerEnergyLedger.entropy_warning', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_energy_layer_costs_layerenergyledger_entropy_warning')(payload=payload, **kwargs)

if _aurora_get_target(['LayerEnergyLedger', 'entropy_warning']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['LayerEnergyLedger.entropy_warning'] = _aurora_get_target(['LayerEnergyLedger', 'entropy_warning'])
    _aurora_assign_target(['LayerEnergyLedger', 'entropy_warning'], _aurora_make_override('entropy_warning_evolved', 'LayerEnergyLedger.entropy_warning'))
    _AURORA_NATIVE_EVOLVED_LAST['LayerEnergyLedger.entropy_warning'] = {'alignment_gap': 0.56, 'override_active': True}

def is_balanced_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_energy_layer_costs.LayerEnergyLedger.is_balanced', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_energy_layer_costs_layerenergyledger_is_balanced')(payload=payload, **kwargs)

if _aurora_get_target(['LayerEnergyLedger', 'is_balanced']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['LayerEnergyLedger.is_balanced'] = _aurora_get_target(['LayerEnergyLedger', 'is_balanced'])
    _aurora_assign_target(['LayerEnergyLedger', 'is_balanced'], _aurora_make_override('is_balanced_evolved', 'LayerEnergyLedger.is_balanced'))
    _AURORA_NATIVE_EVOLVED_LAST['LayerEnergyLedger.is_balanced'] = {'alignment_gap': 0.56, 'override_active': True}

def make_accountant_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_energy_layer_costs.make_accountant', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_energy_layer_costs_make_accountant')(payload=payload, **kwargs)

if _aurora_get_target(['make_accountant']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['make_accountant'] = _aurora_get_target(['make_accountant'])
    _aurora_assign_target(['make_accountant'], _aurora_make_override('make_accountant_evolved', 'make_accountant'))
    _AURORA_NATIVE_EVOLVED_LAST['make_accountant'] = {'alignment_gap': 0.611, 'override_active': True}

def verify_layer_energy_costs_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_internal.aurora_energy_layer_costs.verify_layer_energy_costs', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_internal_aurora_energy_layer_costs_verify_layer_energy_costs')(payload=payload, **kwargs)

if _aurora_get_target(['verify_layer_energy_costs']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['verify_layer_energy_costs'] = _aurora_get_target(['verify_layer_energy_costs'])
    _aurora_assign_target(['verify_layer_energy_costs'], _aurora_make_override('verify_layer_energy_costs_evolved', 'verify_layer_energy_costs'))
    _AURORA_NATIVE_EVOLVED_LAST['verify_layer_energy_costs'] = {'alignment_gap': 0.611, 'override_active': True}

AURORA_NATIVE_EVOLVED_EXPORTS = {'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.__init__': 'init_evolved',
 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant._compute_leverage': 'compute_leverage_evolved',
 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant._distribute_pool': 'distribute_pool_evolved',
 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant._pay_maintenance': 'pay_maintenance_evolved',
 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant._verify_admissibility': 'verify_admissibility_evolved',
 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.apply_shift': 'apply_shift_evolved',
 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.cheapest_viable_layer': 'cheapest_viable_layer_evolved',
 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.entropy_pressure': 'entropy_pressure_evolved',
 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.history': 'history_evolved',
 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.latest_ledger': 'latest_ledger_evolved',
 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.leverage_scalar': 'leverage_scalar_evolved',
 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.leverage_trend': 'leverage_trend_evolved',
 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.magnitudes': 'magnitudes_evolved',
 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.polarities': 'polarities_evolved',
 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.pool': 'pool_evolved',
 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.replenish': 'replenish_evolved',
 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.set_pressure': 'set_pressure_evolved',
 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.slot': 'slot_evolved',
 'aurora_internal.aurora_energy_layer_costs.LayerEnergyLedger.allocations': 'allocations_evolved',
 'aurora_internal.aurora_energy_layer_costs.LayerEnergyLedger.cheapest_layer_with_headroom': 'cheapest_layer_with_headroom_evolved',
 'aurora_internal.aurora_energy_layer_costs.LayerEnergyLedger.entropy_critical': 'entropy_critical_evolved',
 'aurora_internal.aurora_energy_layer_costs.LayerEnergyLedger.entropy_warning': 'entropy_warning_evolved',
 'aurora_internal.aurora_energy_layer_costs.LayerEnergyLedger.is_balanced': 'is_balanced_evolved',
 'aurora_internal.aurora_energy_layer_costs.make_accountant': 'make_accountant_evolved',
 'aurora_internal.aurora_energy_layer_costs.verify_layer_energy_costs': 'verify_layer_energy_costs_evolved'}
AURORA_NATIVE_EVOLUTION_OVERRIDES = {'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant._compute_leverage': {'export': 'compute_leverage_evolved',
                                                                                       'mode': 'callable_override',
                                                                                       'target': 'LayerEnergyAccountant._compute_leverage'},
 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant._distribute_pool': {'export': 'distribute_pool_evolved',
                                                                                      'mode': 'callable_override',
                                                                                      'target': 'LayerEnergyAccountant._distribute_pool'},
 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.apply_shift': {'export': 'apply_shift_evolved',
                                                                                 'mode': 'callable_override',
                                                                                 'target': 'LayerEnergyAccountant.apply_shift'},
 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.cheapest_viable_layer': {'export': 'cheapest_viable_layer_evolved',
                                                                                           'mode': 'callable_override',
                                                                                           'target': 'LayerEnergyAccountant.cheapest_viable_layer'},
 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.entropy_pressure': {'export': 'entropy_pressure_evolved',
                                                                                      'mode': 'callable_override',
                                                                                      'target': 'LayerEnergyAccountant.entropy_pressure'},
 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.history': {'export': 'history_evolved',
                                                                             'mode': 'callable_override',
                                                                             'target': 'LayerEnergyAccountant.history'},
 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.latest_ledger': {'export': 'latest_ledger_evolved',
                                                                                   'mode': 'callable_override',
                                                                                   'target': 'LayerEnergyAccountant.latest_ledger'},
 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.leverage_scalar': {'export': 'leverage_scalar_evolved',
                                                                                     'mode': 'callable_override',
                                                                                     'target': 'LayerEnergyAccountant.leverage_scalar'},
 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.leverage_trend': {'export': 'leverage_trend_evolved',
                                                                                    'mode': 'callable_override',
                                                                                    'target': 'LayerEnergyAccountant.leverage_trend'},
 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.magnitudes': {'export': 'magnitudes_evolved',
                                                                                'mode': 'callable_override',
                                                                                'target': 'LayerEnergyAccountant.magnitudes'},
 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.polarities': {'export': 'polarities_evolved',
                                                                                'mode': 'callable_override',
                                                                                'target': 'LayerEnergyAccountant.polarities'},
 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.pool': {'export': 'pool_evolved',
                                                                          'mode': 'callable_override',
                                                                          'target': 'LayerEnergyAccountant.pool'},
 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.replenish': {'export': 'replenish_evolved',
                                                                               'mode': 'callable_override',
                                                                               'target': 'LayerEnergyAccountant.replenish'},
 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.set_pressure': {'export': 'set_pressure_evolved',
                                                                                  'mode': 'callable_override',
                                                                                  'target': 'LayerEnergyAccountant.set_pressure'},
 'aurora_internal.aurora_energy_layer_costs.LayerEnergyAccountant.slot': {'export': 'slot_evolved',
                                                                          'mode': 'callable_override',
                                                                          'target': 'LayerEnergyAccountant.slot'},
 'aurora_internal.aurora_energy_layer_costs.LayerEnergyLedger.allocations': {'export': 'allocations_evolved',
                                                                             'mode': 'callable_override',
                                                                             'target': 'LayerEnergyLedger.allocations'},
 'aurora_internal.aurora_energy_layer_costs.LayerEnergyLedger.cheapest_layer_with_headroom': {'export': 'cheapest_layer_with_headroom_evolved',
                                                                                              'mode': 'callable_override',
                                                                                              'target': 'LayerEnergyLedger.cheapest_layer_with_headroom'},
 'aurora_internal.aurora_energy_layer_costs.LayerEnergyLedger.entropy_critical': {'export': 'entropy_critical_evolved',
                                                                                  'mode': 'callable_override',
                                                                                  'target': 'LayerEnergyLedger.entropy_critical'},
 'aurora_internal.aurora_energy_layer_costs.LayerEnergyLedger.entropy_warning': {'export': 'entropy_warning_evolved',
                                                                                 'mode': 'callable_override',
                                                                                 'target': 'LayerEnergyLedger.entropy_warning'},
 'aurora_internal.aurora_energy_layer_costs.LayerEnergyLedger.is_balanced': {'export': 'is_balanced_evolved',
                                                                             'mode': 'callable_override',
                                                                             'target': 'LayerEnergyLedger.is_balanced'},
 'aurora_internal.aurora_energy_layer_costs.make_accountant': {'export': 'make_accountant_evolved',
                                                               'mode': 'callable_override',
                                                               'target': 'make_accountant'},
 'aurora_internal.aurora_energy_layer_costs.verify_layer_energy_costs': {'export': 'verify_layer_energy_costs_evolved',
                                                                         'mode': 'callable_override',
                                                                         'target': 'verify_layer_energy_costs'}}
# AURORA_EVOLVED_NATIVE_END

"""Rest: ONE finite recovery capacity, shared by recovery and consolidation in proportion to their need.

Authors: Sunni (Sir) Morningstar and Cael Devo

THE PRINCIPLE (Sir's decision, AURORA_TICK_CLOCK_MAP.md D7). When she is not operating, rest creates a single
finite recovery capacity. Two things draw on it:

  * RECOVERY: the wear operating left (today the gap to full coherence; one stand-in, `recoverable_wear`).
  * CONSOLIDATION: the work operating produced (the core queue and the lattice backlog, priced in the same unit).

The capacity of one resting tick is the resting rate applied to the LARGEST unresolved need (the rest works on what
is most pressing), and that one amount is split between the needs in proportion to their CURRENT size:

    capacity per tick   = rate * max(wear, debt)
    recovery gets         capacity * wear / (wear + debt)       consolidation gets  capacity * debt / (wear + debt)

Both needs therefore relax at the same rate, rho = rate * max(wear, debt) / (wear + debt), which lies between
rate / 2 (equal needs: fully contested) and rate (one need alone, or one so large it dominates). Because they relax
together, the split stays in proportion to what each was owed, and the whole rest has a closed form.

There is no fixed percentage anywhere, and nothing is free. Every case she asked for falls out of that one rule:

  * no consolidation debt        -> share_recovery = 1: all of the capacity restores her.
  * recovery complete, debt left -> share_consolidation = 1: all of it goes to consolidation.
  * both owed                    -> each gets rate * its share, so a debt DOES slow recovery, and the larger need
                                    takes the larger part. Consolidation is paid out of the same capacity that
                                    would otherwise restore her.
  * the capacity is the rate, so it is finite: with both owed, less is resolved than if each were alone.

What recovery receives is credited in full (it was apportioned before the work, so there is no charge afterwards
and no wake-up cost). What consolidation receives pays for the work BEFORE it runs. Capacity apportioned to
consolidation and not yet spent (an item cannot be bought in pieces) carries to the next rest; it was already
taken from recovery, so it is never counted twice.

The rate is the Dimensional Energy Regulator's own (its `base_decay_rate`): the rate at which it wears is the rate
at which rest restores. The cost of one unit of core work comes from the lattice's own multiplier. Nothing here
is a tuned constant; the only number is a rounding snap.

WHAT THIS LEDGER SETTLES IN, AND WHAT IT DOES NOT. It settles in WEAR, read in exactly one place
(`recoverable_wear` / `restore_wear` in aurora_metabolic_steps.py). It is NOT N: N is Energy (AURORA_COGNITIVE_PHYSICS
section 1: activation pressure, metabolic cost). Coherence can influence the contract's N-cost and reflect
energetic condition, but N does not collapse into it. Whether "gaining N at rest" should mean relaxing the
Dimensional Energy Regulator's activation, or restoring a reserve that does not exist yet, is an open decision for
the architect (see the map). Her gain is internal: never exposed as a number she can read or optimise.
"""
import math
from typing import Any, Dict, Tuple

# The resting rate when no Dimensional Energy Regulator is present to supply its own.
DEFAULT_REST_RATE = 0.15
_EPS = 1e-12
# A geometric relaxation only approaches "all of it". Within this of complete, it IS complete: a repayment that
# fell short of a whole item by 7.7e-10 once priced the last queued item out of a night's rest.
_SNAP = 1e-6


def allocate_rest(wear: float, debt: float, rest_ticks: float,
                  rate: float = DEFAULT_REST_RATE) -> Tuple[float, float]:
    """How much of `wear` and of `debt` a rest of `rest_ticks` resolves: (recovery, consolidation).

    One capacity (the resting rate on the largest need), split in proportion to current size, so both needs relax
    at the common rate rho = rate * max(wear, debt) / (wear + debt) (see the module docstring). Geometric in time,
    so it saturates, and it composes: resting n1 ticks and then n2 from the state that left her in equals resting
    n1 + n2, exactly, fractional ticks included."""
    r0 = max(0.0, float(wear))
    d0 = max(0.0, float(debt))
    n = max(0.0, float(rest_ticks))
    rate = min(1.0, max(0.0, float(rate)))
    total = r0 + d0
    if n <= 0.0 or rate <= 0.0 or total <= 0.0:
        return 0.0, 0.0
    rho = rate * max(r0, d0) / total
    left = (1.0 - rho) ** n                       # the fraction of EACH need still unresolved after the rest
    resolved = 1.0 if left <= _SNAP else 1.0 - left
    return r0 * resolved, d0 * resolved


def settle(owed: float, funded: float) -> float:
    """What is funded, except that funding within a millionth of everything owed IS everything owed (and it never
    funds beyond what is owed).

    A geometric relaxation only approaches "all of it". Rested a tick at a time it never reaches the snap that a
    single long rest does, so the last indivisible item of a queue was priced out for ~130 closes (measured: 137
    closes against ~88 for one long rest). The same snap, applied to what is owed overall, removes the difference."""
    owed = max(0.0, float(owed))
    funded = max(0.0, float(funded))
    return owed if owed - funded <= _SNAP * owed else funded


def consolidation_share(wear: float, debt: float) -> float:
    """The share of the resting rate consolidation holds RIGHT NOW: its unresolved size over the total unresolved.
    Reported for a status reader; the allocation itself re-evaluates it every tick."""
    w, d = max(0.0, float(wear)), max(0.0, float(debt))
    total = w + d
    return d / total if total > 0.0 else 0.0


class RestLedger:
    """What one rest created and apportioned, and what consolidation has spent of its share.

    `recovery` is what recovery received: credited to her in full when the rest closes. `consolidation` is what
    consolidation received (plus `carry`, apportioned to it in earlier rests and not yet spent): it pays for work
    before the work runs, and nothing it does not spend is ever charged to her."""

    def __init__(self, recovery: float = 0.0, consolidation: float = 0.0, carry: float = 0.0) -> None:
        self.recovery: float = max(0.0, float(recovery))
        self.consolidation: float = max(0.0, float(consolidation))
        self.carry: float = max(0.0, float(carry))
        self.spent: float = 0.0

    @property
    def capacity(self) -> float:
        """Everything this rest created and apportioned (carry was created, and apportioned, earlier)."""
        return self.recovery + self.consolidation

    @property
    def net(self) -> float:
        """What she keeps: what recovery received. Never negative, and nothing is charged to it afterwards."""
        return self.recovery

    def remaining(self) -> float:
        """What consolidation may still spend: its share, plus what earlier rests apportioned and did not spend."""
        return max(0.0, self.consolidation + self.carry - self.spent)

    def carry_out(self) -> float:
        """Apportioned to consolidation and unspent: carried to the next rest."""
        return self.remaining()

    def can_afford(self, cost: float) -> bool:
        return cost >= 0.0 and cost <= self.remaining() + _EPS

    def spend(self, cost: float) -> bool:
        """Spend only what consolidation's share has paid for. A cost it cannot afford is refused, never run."""
        if not self.can_afford(cost):
            return False
        self.spent += cost
        return True

    def affordable_units(self, unit_cost: float) -> int:
        if unit_cost <= 0.0:
            return 0
        return int(math.floor((self.remaining() + _EPS) / unit_cost))

    @property
    def rested(self) -> bool:
        """She received recovery. (Whether she is FULLY rested depends on the wear left, which this ledger does
        not hold; the closing step reports that.)"""
        return self.recovery > _EPS

    def report(self) -> Dict[str, float]:
        return {"recovery": round(self.recovery, 6), "consolidation": round(self.consolidation, 6),
                "capacity": round(self.capacity, 6), "spent": round(self.spent, 6),
                "carry_in": round(self.carry, 6), "carry_out": round(self.carry_out(), 6),
                "net": round(self.net, 6)}


def wear_repaid(wear: float, rest_ticks: float, rate: float = DEFAULT_REST_RATE) -> float:
    """What a rest repays of `wear` when nothing else draws on it: `allocate_rest` with no debt, which is the
    geometric relaxation `wear * (1 - (1 - rate) ** rest_ticks)`: saturating and composing."""
    return allocate_rest(wear, 0.0, rest_ticks, rate)[0]


def rest_gain(coherence: float, rest_ticks: float, rate: float = DEFAULT_REST_RATE) -> float:
    """`wear_repaid` for a wear read as the gap to full coherence (kept for callers that hold a coherence)."""
    return wear_repaid(max(0.0, 1.0 - float(coherence)), rest_ticks, rate)


def rest_rate(systems: Dict[str, Any]) -> float:
    der = getattr(systems.get("dimensional"), "der", None)
    try:
        return float(getattr(der, "base_decay_rate", DEFAULT_REST_RATE))
    except (TypeError, ValueError):
        return DEFAULT_REST_RATE


def core_step_cost(steps_per_tick: float, decay_per_operating_tick: float, core_multiplier: float) -> float:
    """What one CORE lattice step costs, from constants the system already has.

    A tick of surface-speed lattice time (`steps_per_tick` steps) is priced at what an operating tick erodes
    (`decay_per_operating_tick`); a CORE step costs `core_multiplier` times a surface step (the lattice's own
    T_COST_MULTIPLIER). Core is fast and it is costly."""
    if steps_per_tick <= 0.0:
        return float("inf")
    return (float(decay_per_operating_tick) / float(steps_per_tick)) * float(core_multiplier)

"""What the metabolic clock does when a tick closes.

Authors: Sunni (Sir) Morningstar and Cael Devo

Each step is `fn(delta_t, systems)`, with `delta_t` in ticks and the span's operating/rest split in
`systems['metabolic_clock'].span`. Surface work is operating; internal work is not (it has no
environmental cost). Internal processes run FAST: they use exact, stable integration so they can take as
much time as the clock gives them, and they are preemptible so a turn never waits on them.
"""
import math
import time
from typing import Any, Dict

# The lattice's own heartbeat was about one step per second (aurora_daemon's outer loop). A tick is
# tick_seconds long, so a tick is tick_seconds / LATTICE_HEARTBEAT_SECONDS steps of internal time.
LATTICE_HEARTBEAT_SECONDS = 1.0
# Compute bounds for ONE close, not physics: a close runs while she is idle, but it must end. What is
# not done is carried as debt to the next close. The debt is itself bounded to one close's worth: a
# damped system has settled long before a night's 28,800 steps, so owing all of them would be pure cost.
LATTICE_MAX_STEPS_PER_CLOSE = 600
# The most consolidation she can owe at once (what operating has produced and rest has not yet paid for).
LATTICE_MAX_BACKLOG = 10 * LATTICE_MAX_STEPS_PER_CLOSE
LATTICE_TIME_BUDGET_SECONDS = 5.0
_LATTICE_YIELD_CHECK_EVERY = 1     # every tick: a turn waits at most one lattice step, however big the lattice
# The most core ticks of settling one Understanding gets in a close, however stable she is: a compute bound.
CORE_MAX_PASSES = 8


def core_multiplier() -> float:
    """How much denser core time is than surface time: the lattice's own CORE cost multiplier (32)."""
    try:
        from aurora_ivm import RecursionLevel, T_COST_MULTIPLIER
        return float(T_COST_MULTIPLIER[RecursionLevel.CORE])
    except Exception:
        return 32.0


def core_tick_cost(systems: Dict[str, Any]) -> float:
    """What one core tick of work costs, in coherence: the lattice's CORE step price. The lattice and the
    core variant of Understanding are both core work and are paid in the same unit."""
    from aurora_internal.aurora_rest_ledger import core_step_cost
    clock = systems.get("metabolic_clock")
    entropy = getattr(systems.get("consciousness"), "entropy", None)
    decay = float(getattr(entropy, "COHERENCE_DECAY", 0.014))
    steps_per_tick = (clock.tick_seconds / LATTICE_HEARTBEAT_SECONDS) if clock is not None else 0.0
    return core_step_cost(steps_per_tick, decay, core_multiplier())


def dilation_factor(systems: Dict[str, Any]) -> float:
    """How much faster than baseline the core is allowed to think right now (1.0 = baseline). It is the
    TimeDilationGovernor's own normalized factor: fast when stable, slow when fragile, brake on collapse."""
    governor = systems.get("time_dilation_governor")
    try:
        return max(1.0, float(governor.get_current_dilation_factor())) if governor is not None else 1.0
    except Exception:
        return 1.0


def core_passes(systems: Dict[str, Any]) -> int:
    """Core ticks of settling per Understanding: the dilation, as whole passes, bounded."""
    return max(1, min(CORE_MAX_PASSES, int(round(dilation_factor(systems)))))


def stability_metrics(systems: Dict[str, Any], governor: Any) -> Any:
    """What the governor reads, from signals she really has. Fitness is her coherence (what operating wears
    and rest restores); variance and trend come from the governor's own history of it; the error rate is the
    fraction of the last close's steps that failed."""
    from aurora_simulation_engine import StabilityMetrics
    entropy = getattr(systems.get("consciousness"), "entropy", None)
    coherence = float(entropy.state.coherence) if entropy is not None else 1.0
    recent = list(governor.fitness_history)[-10:] + [coherence]
    mean = sum(recent) / len(recent)
    variance = sum((x - mean) ** 2 for x in recent) / len(recent)
    last = getattr(systems.get("metabolic_clock"), "last_report", None) or {}
    steps = (last.get("steps") or {}) if isinstance(last, dict) else {}
    failed = sum(1 for v in steps.values() if isinstance(v, dict) and not v.get("ok", True))
    return StabilityMetrics(fitness_mean=coherence, fitness_variance=variance,
                            fitness_trend=governor.get_fitness_trend(),
                            error_rate=(failed / len(steps)) if steps else 0.0,
                            coherence_score=coherence)


def recoverable_wear(systems: Dict[str, Any]) -> float:
    """What operating has worn that a rest can repay. Today that is the gap to full coherence, because
    operating erodes it (`EntropicPressure.erode`). This is WEAR, not N: N is Energy (activation pressure,
    metabolic cost), which coherence can influence and reflect but is not. The ledger settles in wear and asks
    only this function what is owed, so the stand-in lives in exactly one place."""
    entropy = getattr(systems.get("consciousness"), "entropy", None)
    if entropy is None:
        return 0.0
    return max(0.0, 1.0 - float(entropy.state.coherence))


def restore_wear(systems: Dict[str, Any], amount: float) -> float:
    """Repay `amount` of wear. Returns what was actually repaid (never more than was owed)."""
    entropy = getattr(systems.get("consciousness"), "entropy", None)
    if entropy is None:
        return 0.0
    before = float(entropy.state.coherence)
    entropy.state.coherence = min(1.0, before + max(0.0, float(amount)))
    return float(entropy.state.coherence) - before


def _span(systems: Dict[str, Any]) -> Dict[str, Any]:
    return getattr(systems.get("metabolic_clock"), "span", {}) or {}


def step_sediment(delta_t: float, systems: Dict[str, Any]) -> None:
    """Memory ages with real time, resting or not (geological time passes while she sleeps)."""
    sedi = systems.get("sedimemory")
    if sedi is not None:
        sedi.tick(float(delta_t))


def step_entropy(delta_t: float, systems: Dict[str, Any]) -> None:
    """Erosion is charged per OPERATING tick: an idle tick does not erode her (rested, not worn)."""
    engine = systems.get("consciousness")
    if engine is None or not hasattr(engine, "entropy"):
        return
    dmm = getattr(getattr(engine, "dimensional", None), "dmm", None)
    engine.entropy.erode(
        float(_span(systems).get("operating_ticks", 0.0)),
        current_alignment=getattr(getattr(dmm, "state", None), "alignment", None),
    )


def step_der(delta_t: float, systems: Dict[str, Any]) -> None:
    """The Dimensional Energy Regulator dissipates while she OPERATES. Geometric in time, so any span is
    safe. Resting restores (the rest ledger), it does not dissipate. `actual_dt` is stated in the same unit
    so the presence monitor is not fooled into reading clock units as drift."""
    operating = float(_span(systems).get("operating_ticks", 0.0))
    if operating <= 0.0:
        return
    der = getattr(systems.get("dimensional"), "der", None)
    if der is not None and hasattr(der, "tick"):
        der.tick(operating, actual_dt=operating)


def pending_core_cost(systems: Dict[str, Any]) -> float:
    """What the consolidation she owes would cost: queued understandings and the lattice's backlog, each in core
    ticks (at the passes the governor lets the core give each unit) at the core price."""
    contract = systems.get("understanding_contract")
    queued = int(getattr(contract, "core_pending", 0) or 0) if hasattr(contract, "process_core_queue") else 0
    ticks = (queued + float(systems.get("_lattice_step_debt", 0.0) or 0.0)) * core_passes(systems)
    cost = core_tick_cost(systems)
    if ticks <= 0.0 or not math.isfinite(cost):
        return 0.0              # nothing owed, or no clock to price it: never 0 * inf = nan into a ledger
    return ticks * cost


def credit_cap(systems: Dict[str, Any]) -> float:
    """The most allowance worth carrying: enough for the most consolidation that could ever be queued, at the
    most passes the core is ever given."""
    contract = systems.get("understanding_contract")
    items = int(getattr(contract, "CORE_QUEUE_MAX", 0) or 0)
    cost = core_tick_cost(systems)
    return (items + LATTICE_MAX_BACKLOG) * CORE_MAX_PASSES * cost if math.isfinite(cost) else 0.0


def step_rest_open(delta_t: float, systems: Dict[str, Any]) -> None:
    """While she is not operating, rest creates ONE finite recovery capacity (the resting rate) and apportions it
    between the two things she owes, in proportion to their CURRENT unresolved size: the wear operating left and the
    consolidation it produced. Nothing is applied yet: recovery is credited in full when the rest closes, and the
    consolidation share pays for the work before it runs (see aurora_rest_ledger.py)."""
    from aurora_internal.aurora_rest_ledger import RestLedger, allocate_rest, consolidation_share, rest_rate, settle
    systems.pop("_rest_ledger", None)
    # What needs consolidating is what she DID, not how long she rests. Core time is `core_multiplier()` times
    # denser than surface time, so one operating tick needs 1/32 of a tick's surface steps in core steps.
    clock = systems.get("metabolic_clock")
    operating = float(_span(systems).get("operating_ticks", 0.0))
    if operating > 0.0 and clock is not None:
        owed = float(systems.get("_lattice_step_debt", 0.0) or 0.0)
        systems["_lattice_step_debt"] = min(
            owed + operating * clock.tick_seconds / LATTICE_HEARTBEAT_SECONDS / core_multiplier(),
            float(LATTICE_MAX_BACKLOG))
    rest = float(_span(systems).get("rest_ticks", 0.0))
    entropy = getattr(systems.get("consciousness"), "entropy", None)
    if rest <= 0.0 or entropy is None:
        return
    wear = recoverable_wear(systems)
    pending = pending_core_cost(systems)
    # Capacity already apportioned to consolidation in an earlier rest (an item cannot be bought in pieces) was
    # taken from recovery THEN; it is not a debt to apportion again, and never more than is still owed.
    carry = min(float(systems.get("_rest_credit", 0.0) or 0.0), pending)
    debt = max(0.0, pending - carry)
    recovery, consolidation = allocate_rest(wear, debt, rest, rest_rate(systems))
    # Funding within a millionth of everything owed is everything owed (a geometric relaxation only approaches it).
    consolidation = max(0.0, settle(pending, carry + consolidation) - carry)
    systems["_rest_ledger"] = RestLedger(recovery, consolidation, carry)
    systems["_rest_state"] = {"rest_ticks": rest, "wear_before": wear, "debt_before": pending,
                              "consolidation_share": consolidation_share(wear, debt),
                              "coherence_before": float(entropy.state.coherence)}


def step_governor(delta_t: float, systems: Dict[str, Any]) -> None:
    """Let the TimeDilationGovernor read how stable she is. This is the ONE governor for her live core: the
    simulation session keeps its own for simulated time (see AURORA_TICK_CLOCK_MAP.md, the governor audit).

    Its output decides how many internal processes may OPERATE in a span, each paid for out of the rest:
      * Understanding: passes of settling per queued item (`core_passes`, `step_core_understanding`);
      * the lattice: core ticks per owed unit (`step_lattice`).
    It never touches TIME. Sediment ages by the time that actually elapsed (`step_sediment`) and is never scaled
    by this governor: thinking faster must not make sediment thousands of times older (measured, with the
    governor attached at maximum dilation and three understandings written: deep mass 30 -> 41 in ONE tick, 47
    over a night, manufacturing depth she did not earn). What a faster core changes is how many operations may
    act on sediment in the span (the geological writes core Understanding performs); those alter it, and cost."""
    governor = systems.get("time_dilation_governor")
    if governor is None:
        return
    systems["_core_dilation"] = float(governor.update(stability_metrics(systems, governor)))


def step_core_understanding(delta_t: float, systems: Dict[str, Any]) -> None:
    """The core variant of Understanding, during rest: the deep write and identity shaped by deep memory, for
    what understanding queued while she was operating. Faster than the exchange (more passes of settling when
    she is stable), paid out of the rest BEFORE each runs, and stopped between items if a turn arrives. What it
    cannot afford stays queued for the next rest."""
    contract = systems.get("understanding_contract")
    ledger = systems.get("_rest_ledger")
    clock = systems.get("metabolic_clock")
    systems["_core_understanding_last"] = {"processed": 0, "remaining": int(getattr(contract, "core_pending", 0) or 0),
                                           "passes": 0}
    if contract is None or ledger is None or clock is None or not hasattr(contract, "process_core_queue"):
        return
    cost = core_tick_cost(systems)
    passes = core_passes(systems)
    systems["_core_understanding_last"] = contract.process_core_queue(
        systems, passes=passes,
        afford=lambda n: ledger.can_afford(n * cost),
        pay=lambda n: ledger.spend(n * cost),
        should_stop=clock.should_yield,
    )


def step_lattice(delta_t: float, systems: Dict[str, Any]) -> None:
    """Consolidation: the lattice, an internal process, runs FAST while she rests, at the CORE level, and every
    tick is paid out of the rest BEFORE it runs. DEMAND-DRIVEN: the work is the backlog operating produced, not
    the length of the rest. The governor's output reaches it here: each owed unit gets `core_passes` core ticks
    (a faster core settles each unit further), and each tick is paid. Preemptible between ticks: when a turn
    arrives the loop stops and what is unfinished STAYS owed (fractionally, if a unit was partly done), neither
    cancelled nor repeated; the subsystem keeps its own work and the surface keeps the turn. With no rest there
    is no ledger and no fast ticks (the per-turn lattice step is unchanged)."""
    lattice = systems.get("lattice")
    clock = systems.get("metabolic_clock")
    ledger = systems.get("_rest_ledger")
    systems["_lattice_steps_last"] = 0
    if lattice is None or not hasattr(lattice, "tick") or clock is None or ledger is None:
        return
    try:
        from aurora_ivm import RecursionLevel
        level = RecursionLevel.CORE
    except Exception:
        level = None
    cost = core_tick_cost(systems)
    passes = core_passes(systems)
    owed = float(systems.get("_lattice_step_debt", 0.0) or 0.0)       # units of work operating produced
    want = min(max(0, int(round(owed * passes))), LATTICE_MAX_STEPS_PER_CLOSE)
    started = time.monotonic()
    done = 0
    while done < want:
        if not ledger.spend(cost):            # she cannot afford it: it waits for the next rest
            break
        if level is not None:
            lattice.tick(level=level)
        else:
            lattice.tick()
        done += 1
        if clock.should_yield() or time.monotonic() - started > LATTICE_TIME_BUDGET_SECONDS:
            break
    systems["_lattice_step_debt"] = float(max(0.0, min(owed - done / passes, LATTICE_MAX_BACKLOG)))
    systems["_lattice_steps_last"] = done
    systems["_lattice_passes_last"] = passes


def step_rest_close(delta_t: float, systems: Dict[str, Any]) -> None:
    """She wakes already consolidated: what recovery received is credited in full (it was apportioned before the
    work, so nothing is charged to it now and there is no wake-up cost), and the stagnation of a long operating
    stretch eases. What was apportioned to consolidation and not spent carries to the next rest."""
    from aurora_internal.aurora_rest_ledger import rest_rate
    ledger = systems.pop("_rest_ledger", None)
    if ledger is None:
        return
    entropy = getattr(systems.get("consciousness"), "entropy", None)
    state = systems.get("_rest_state", {}) or {}
    if entropy is None:
        return
    before = float(entropy.state.coherence)
    restore_wear(systems, ledger.recovery)
    rest = float(state.get("rest_ticks", 0.0))
    entropy.state.stagnation_score *= (1.0 - min(1.0, rest_rate(systems))) ** rest
    entropy._refresh_vitality()
    systems["_rest_credit"] = ledger.carry_out()
    wear_after = recoverable_wear(systems)
    systems["_last_rest"] = {**ledger.report(), "rest_ticks": round(rest, 6),
                             "rested": bool(wear_after <= 1e-9 or ledger.rested),
                             "steps": int(systems.get("_lattice_steps_last", 0)),
                             "wear_before": round(float(state.get("wear_before", 0.0)), 6),
                             "wear_after": round(wear_after, 6),
                             "debt_before": round(float(state.get("debt_before", 0.0)), 6),
                             "consolidation_share": round(float(state.get("consolidation_share", 0.0)), 6),
                             "coherence_before": round(before, 6),
                             "coherence_after": round(float(entropy.state.coherence), 6)}


def governor_state(systems: Dict[str, Any]) -> Dict[str, Any]:
    governor = systems.get("time_dilation_governor")
    if governor is None:
        return {}
    state = getattr(governor, "stability_state", None)
    return {"current_dilation": float(governor.current_dilation),
            "fitness_history": [float(x) for x in list(governor.fitness_history)],
            "consecutive_stable": int(governor.consecutive_stable),
            "consecutive_unstable": int(governor.consecutive_unstable),
            "total_adjustments": int(governor.total_adjustments),
            "stability_state": str(getattr(state, "value", state))}


def restore_governor(systems: Dict[str, Any], raw: Any) -> None:
    governor = systems.get("time_dilation_governor")
    if governor is None or not isinstance(raw, dict):
        return
    try:
        dilation = float(raw.get("current_dilation", governor.START_DILATION))
        if math.isfinite(dilation):
            governor.current_dilation = max(governor.MIN_DILATION, min(governor.MAX_DILATION, dilation))
        history = [float(x) for x in (raw.get("fitness_history") or []) if math.isfinite(float(x))]
        governor.fitness_history.clear()
        governor.fitness_history.extend(history[-governor.fitness_history.maxlen:])
        governor.consecutive_stable = max(0, int(raw.get("consecutive_stable", 0) or 0))
        governor.consecutive_unstable = max(0, int(raw.get("consecutive_unstable", 0) or 0))
        governor.total_adjustments = max(0, int(raw.get("total_adjustments", 0) or 0))
        try:
            from aurora_simulation_engine import StabilityState
            governor.stability_state = StabilityState(raw.get("stability_state"))
        except Exception:
            pass
    except (TypeError, ValueError):
        return


def consolidation_state(systems: Dict[str, Any]) -> Dict[str, Any]:
    """What she still owes, so a reboot is not a debt eraser. (The core Understanding queue persists in the
    contract's own state.)"""
    return {"lattice_step_debt": float(systems.get("_lattice_step_debt", 0.0) or 0.0),
            "rest_credit": float(systems.get("_rest_credit", 0.0) or 0.0),
            "governor": governor_state(systems)}


def restore_consolidation(systems: Dict[str, Any], raw: Any) -> None:
    if not isinstance(raw, dict):
        return

    def _num(key: str, ceiling: float) -> float:
        try:
            v = float(raw.get(key, 0.0) or 0.0)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(v, ceiling)) if math.isfinite(v) else 0.0
    cap = credit_cap(systems)
    ceiling = cap if math.isfinite(cap) and cap > 0.0 else 10.0
    systems["_lattice_step_debt"] = _num("lattice_step_debt", float(LATTICE_MAX_BACKLOG))
    systems["_rest_credit"] = _num("rest_credit", ceiling)
    restore_governor(systems, raw.get("governor"))


DEFAULT_STEPS = (("sediment", step_sediment), ("entropy", step_entropy), ("der", step_der),
                 ("governor", step_governor), ("rest_open", step_rest_open),
                 ("core_understanding", step_core_understanding), ("lattice", step_lattice),
                 ("rest_close", step_rest_close))


def register_default_steps(clock: Any, systems: Dict[str, Any]) -> None:
    """Register every step and hand entropy's erosion to the clock (a thought then only REGISTERS that an
    input arrived)."""
    for name, fn in DEFAULT_STEPS:
        clock.register_step(name, fn)
    engine = systems.get("consciousness")
    if engine is not None:
        engine.entropy_clock_driven = True
    if systems.get("time_dilation_governor") is None:
        try:
            from aurora_simulation_engine import TimeDilationGovernor
            systems["time_dilation_governor"] = TimeDilationGovernor()
        except Exception:
            pass                                  # no governor: the core runs at baseline (one pass)
    contract = systems.get("understanding_contract")
    if contract is not None and hasattr(contract, "process_core_queue"):
        contract.core_deferred = True             # the deep half of Understanding now waits for the core clock
    # What she still owes (and where the governor had got to) survives a restart: a reboot is not a debt eraser.
    if hasattr(clock, "register_state"):
        clock.register_state("consolidation", lambda: consolidation_state(systems),
                             lambda raw: restore_consolidation(systems, raw))

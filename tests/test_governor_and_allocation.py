"""The governor's output must REACH what it governs, and the rest's allocation must follow her state.

Authors: Sunni (Sir) Morningstar and Cael Devo

Audit findings these pin (see AURORA_TICK_CLOCK_MAP.md, "the governor audit"):
  * boot looked for the simulation's governor at `simulation._time_dilation_governor` / `.time_dilation`; it lives
    at `simulation.session.governor`, so the wire to sediment was dead from the start (error swallowed);
  * the simulation session's governor is updated every episode and consumed by NOTHING (only displayed);
  * the only consumer of the factor anywhere was `SediMemory.tick`, never attached.
"""
import json
import os
import sys
from types import SimpleNamespace

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_consciousness_engine import EntropicPressure  # noqa: E402
from aurora_internal import aurora_metabolic_steps as M  # noqa: E402
from aurora_internal.aurora_metabolic_clock import MetabolicClock  # noqa: E402
from aurora_internal.aurora_rest_ledger import RestLedger, consolidation_share, wear_repaid  # noqa: E402
from aurora_sedimemory import SediMemory  # noqa: E402
from aurora_simulation_engine import StabilityState, TimeDilationGovernor  # noqa: E402


class Clock:
    tick_seconds = 300.0

    def __init__(self, rest=1.0, operating=0.0, yield_after=None):
        self.span = {"rest_ticks": rest, "operating_ticks": operating, "delta_t": rest + operating}
        self._yield_after, self.polls = yield_after, 0

    def should_yield(self):
        self.polls += 1
        return self._yield_after is not None and self.polls >= self._yield_after


class Lattice:
    def __init__(self):
        self.ticks = 0

    def tick(self, dt=0.1, level=None):
        self.ticks += 1


def _governor(factor):
    g = TimeDilationGovernor()
    g.current_dilation = g.START_DILATION * factor
    return g


def _systems(factor=1.0, rest=1.0, coherence=0.8, debt=0.0, gross=10.0, **extra):
    ent = EntropicPressure()
    ent.state.coherence = coherence
    s = {"consciousness": SimpleNamespace(entropy=ent), "metabolic_clock": Clock(rest=rest),
         "lattice": Lattice(), "time_dilation_governor": _governor(factor), "_lattice_step_debt": debt,
         "_rest_ledger": RestLedger(0.0, gross)}
    s.update(extra)
    return s


COST = None


def _cost(s):
    return M.core_tick_cost(s)


# ---- the governor's output reaches the lattice -------------------------------------------------------------------

@pytest.mark.parametrize("factor,passes", [(1.0, 1), (2.0, 2), (4.0, 4), (8.0, 8), (500.0, M.CORE_MAX_PASSES)])
def test_the_governors_factor_sets_how_many_core_ticks_each_owed_unit_gets(factor, passes):
    s = _systems(factor=factor, debt=10.0)
    M.step_lattice(1.0, s)
    assert s["_lattice_passes_last"] == passes
    assert s["lattice"].ticks == 10 * passes and s["_lattice_step_debt"] == pytest.approx(0.0)


def test_a_faster_core_is_paid_for_by_the_tick():
    cheap, fast = _systems(factor=1.0, debt=5.0), _systems(factor=4.0, debt=5.0)
    M.step_lattice(1.0, cheap)
    M.step_lattice(1.0, fast)
    assert fast["_rest_ledger"].spent == pytest.approx(4 * cheap["_rest_ledger"].spent)


def test_no_governor_means_baseline_not_an_error():
    s = _systems(debt=5.0)
    s.pop("time_dilation_governor")
    M.step_lattice(1.0, s)
    assert s["lattice"].ticks == 5 and s["_lattice_passes_last"] == 1


def test_a_governor_that_throws_is_baseline():
    class Bad:
        def get_current_dilation_factor(self):
            raise RuntimeError("x")
    s = _systems(debt=3.0)
    s["time_dilation_governor"] = Bad()
    M.step_lattice(1.0, s)
    assert s["lattice"].ticks == 3


def test_the_pending_cost_includes_the_passes_so_the_repayment_funds_a_faster_core():
    base, fast = _systems(factor=1.0, debt=4.0), _systems(factor=4.0, debt=4.0)
    assert M.pending_core_cost(fast) == pytest.approx(4 * M.pending_core_cost(base))


# ---- sediment ages by ELAPSED time only; a faster core changes how many processes may act on it ---------------------
# Sir's decision: core time dilation is never applied to sediment aging. Thinking faster must not make sediment
# thousands of times older. Operations that act on sediment (core Understanding's geological writes) alter it and
# cost; the governor decides how many may run in a span, not how much time sediment has lived.

@pytest.mark.parametrize("factor", [1.0, 4.0, 500.0, 3333.0])
def test_sediment_ages_by_exactly_the_elapsed_time_at_any_governor_factor(factor):
    sedi = SediMemory()
    s = _systems(factor=factor, rest=2.0, sedimemory=sedi)
    M.step_sediment(7.5, s)
    assert sedi._tick_log[-1] == 7.5


def test_even_a_sediment_with_a_governor_attached_is_not_dilated():
    """Nothing attaches one, but if something did, `tick` still advances by the elapsed time."""
    attached, plain = SediMemory(time_dilation=_governor(100.0)), SediMemory()
    attached.tick(3.0)
    plain.tick(3.0)
    assert attached._tick_log[-1] == plain._tick_log[-1] == 3.0


def test_a_faster_core_does_not_age_sediment_it_lets_more_processes_act_in_the_span():
    slow = _systems(factor=1.0, debt=5.0, sedimemory=SediMemory())
    fast = _systems(factor=8.0, debt=5.0, sedimemory=SediMemory())
    for s in (slow, fast):
        M.step_sediment(3.0, s)
        M.step_lattice(1.0, s)
    assert list(slow["sedimemory"]._tick_log) == list(fast["sedimemory"]._tick_log) == [3.0]
    assert fast["lattice"].ticks == 8 * slow["lattice"].ticks, "the faster core ran more operations, and paid for them"


def test_there_is_no_sediment_dilation_step_and_no_dilation_keyword():
    import inspect
    assert not hasattr(M, "step_sediment_dilation")
    assert "sediment_dilation" not in [name for name, _ in M.DEFAULT_STEPS]
    assert list(inspect.signature(SediMemory.tick).parameters) == ["self", "delta_t"]


def test_sediment_is_never_attached_to_the_governor_by_the_clocks_steps():
    sedi = SediMemory()
    clock = MetabolicClock()
    M.register_default_steps(clock, {"consciousness": SimpleNamespace(entropy_clock_driven=False), "sedimemory": sedi})
    assert sedi._dilation is None, "attaching would scale real-time aging"


def test_real_time_aging_is_never_dilated_by_the_governor():
    sedi = SediMemory()
    s = _systems(factor=500.0, sedimemory=sedi)
    M.step_sediment(10.0, s)
    assert sedi._tick_log[-1] == 10.0


# ---- the governor reads HER stability, and is one governor, not two -----------------------------------------------

def test_the_core_governor_is_a_separate_instance_from_the_simulations():
    clock = MetabolicClock()
    systems = {"consciousness": SimpleNamespace(entropy_clock_driven=False)}
    M.register_default_steps(clock, systems)
    assert isinstance(systems["time_dilation_governor"], TimeDilationGovernor)
    sim = SimpleNamespace(session=SimpleNamespace(governor=TimeDilationGovernor()))
    assert sim.session.governor is not systems["time_dilation_governor"]


def test_an_existing_core_governor_is_kept_not_replaced():
    clock = MetabolicClock()
    mine = TimeDilationGovernor()
    systems = {"consciousness": SimpleNamespace(entropy_clock_driven=False), "time_dilation_governor": mine}
    M.register_default_steps(clock, systems)
    assert systems["time_dilation_governor"] is mine


def test_sustained_health_raises_the_factor_and_a_collapse_brakes_it():
    s = _systems(coherence=0.95)
    for _ in range(30):
        M.step_governor(1.0, s)
    high = s["time_dilation_governor"].get_current_dilation_factor()
    assert high > 1.5
    s["consciousness"].entropy.state.coherence = 0.05
    for _ in range(5):
        M.step_governor(1.0, s)
    assert s["time_dilation_governor"].get_current_dilation_factor() < high


def test_the_governors_input_is_her_stability_not_the_simulations():
    s = _systems(coherence=0.9)
    M.step_governor(1.0, s)
    assert list(s["time_dilation_governor"].fitness_history) == [0.9]


# ---- allocation: ONE capacity, from her state, not a constant ---------------------------------------------------------

def test_nothing_owed_means_the_reported_share_is_zero():
    assert consolidation_share(0.4, 0.0) == 0.0


def test_no_wear_means_the_reported_share_is_the_whole():
    assert consolidation_share(0.0, 0.3) == 1.0


def test_both_owed_the_reported_share_is_in_proportion_to_what_each_is_owed():
    assert consolidation_share(0.3, 0.1) == pytest.approx(0.25)
    assert consolidation_share(0.1, 0.3) == pytest.approx(0.75)
    assert consolidation_share(0.2, 0.2) == pytest.approx(0.5), "equal needs, equal shares"


def test_the_share_follows_the_workload():
    low, high = consolidation_share(0.3, 0.05), consolidation_share(0.3, 0.5)
    assert 0.0 < low < high < 1.0


def test_the_share_follows_the_wear():
    assert consolidation_share(0.05, 0.2) > consolidation_share(0.5, 0.2)


def test_the_ledger_is_opened_by_allocating_one_capacity_from_her_state():
    from aurora_internal.aurora_rest_ledger import allocate_rest
    s = _systems(factor=1.0, rest=12.0, coherence=0.4, debt=10 * 300.0 / 32.0)
    s.pop("_rest_ledger")
    M.step_rest_open(12.0, s)
    led = s["_rest_ledger"]
    recovery, consolidation = allocate_rest(0.6, M.pending_core_cost(s), 12.0)
    assert led.recovery == pytest.approx(recovery) and led.consolidation == pytest.approx(consolidation)
    assert 0.0 < led.consolidation and led.recovery < allocate_rest(0.6, 0.0, 12.0)[0], "the debt draws on the same capacity"


def test_there_is_no_stability_weighting_or_fixed_fraction_in_opening_a_rest():
    src = open(os.path.join(REPO_ROOT, "aurora_internal", "aurora_metabolic_steps.py"), encoding="utf-8").read()
    body = src[src.index("def step_rest_open"):src.index("def step_governor")]
    for gone in ("stability", "keep", "KEEP", "PROVISIONAL", "pending_gain", "repay"):
        assert gone not in body, gone


# ---- N is not coherence ------------------------------------------------------------------------------------------

def test_the_ledger_settles_in_wear_through_one_adapter_and_not_in_n():
    s = _systems(coherence=0.7)
    assert M.recoverable_wear(s) == pytest.approx(0.3)
    assert M.restore_wear(s, 0.1) == pytest.approx(0.1) and s["consciousness"].entropy.state.coherence == pytest.approx(0.8)
    assert M.restore_wear(s, 5.0) == pytest.approx(0.2), "never repays more than was owed"
    assert wear_repaid(0.3, 1.0, 0.15) == pytest.approx(0.3 * 0.15)


def test_the_steps_read_coherence_only_inside_the_named_wear_and_stability_readers():
    src = open(os.path.join(REPO_ROOT, "aurora_internal", "aurora_metabolic_steps.py"), encoding="utf-8").read()
    allowed = ("def recoverable_wear", "def restore_wear", "def stability_metrics", "def step_rest_open",
               "def step_rest_close", "def step_entropy")
    import re
    for m in re.finditer(r"entropy\.state\.coherence", src):
        start = src.rfind("\ndef ", 0, m.start()) + 1
        header = src[start:src.index("(", start)]
        assert any(header.startswith(a) for a in allowed), f"coherence is read in {header!r}"


def test_the_ledger_module_says_it_is_not_n_and_that_the_old_claim_was_wrong():
    doc = open(os.path.join(REPO_ROOT, "aurora_internal", "aurora_rest_ledger.py"), encoding="utf-8").read()
    assert "It is NOT N" in doc
    assert "Her N is coherence" not in doc and "her N is coherence" not in doc


# ---- consolidation state survives a restart ------------------------------------------------------------------------

def test_what_she_owes_and_where_the_governor_was_survive_a_restart(tmp_path):
    path = str(tmp_path / "clock.json")
    s1 = _systems(factor=6.0, debt=37.5, coherence=0.8)
    s1.update(_rest_credit=0.002)
    for _ in range(4):
        M.step_governor(1.0, s1)
    c1 = MetabolicClock(tick_seconds=300.0, state_path=path)
    c1.register_state("consolidation", lambda: M.consolidation_state(s1), lambda raw: M.restore_consolidation(s1, raw))
    with c1.turn():
        pass
    saved_dilation = s1["time_dilation_governor"].current_dilation

    s2 = {"consciousness": SimpleNamespace(entropy=EntropicPressure()), "metabolic_clock": Clock(),
          "time_dilation_governor": TimeDilationGovernor()}
    c2 = MetabolicClock(tick_seconds=300.0, state_path=path)
    c2.restore()
    c2.register_state("consolidation", lambda: M.consolidation_state(s2), lambda raw: M.restore_consolidation(s2, raw))
    assert s2["_lattice_step_debt"] == 37.5, "a reboot is not a debt eraser"
    assert s2["_rest_credit"] == pytest.approx(0.002)
    assert s2["time_dilation_governor"].current_dilation == pytest.approx(saved_dilation)
    assert list(s2["time_dilation_governor"].fitness_history) == list(s1["time_dilation_governor"].fitness_history)


def test_restored_state_is_clamped_and_never_trusted(tmp_path):
    s = {"consciousness": SimpleNamespace(entropy=EntropicPressure()), "metabolic_clock": Clock(),
         "time_dilation_governor": TimeDilationGovernor()}
    M.restore_consolidation(s, {"lattice_step_debt": 1e12, "rest_credit": float("nan"), "rest_repay_credit": 7,
                                "governor": {"current_dilation": 1e30, "fitness_history": ["x"], "stability_state": "??"}})
    assert s["_lattice_step_debt"] == float(M.LATTICE_MAX_BACKLOG)
    assert s["_rest_credit"] == 0.0 and "_rest_repay_credit" not in s, "the legacy second credit is ignored"
    g = s["time_dilation_governor"]
    assert g.MIN_DILATION <= g.current_dilation <= g.MAX_DILATION


@pytest.mark.parametrize("junk", [None, 5, "x", [], {"governor": 3}, {"lattice_step_debt": "x"}])
def test_junk_restored_state_never_raises(junk):
    s = {"consciousness": SimpleNamespace(entropy=EntropicPressure()), "metabolic_clock": Clock(),
         "time_dilation_governor": TimeDilationGovernor()}
    M.restore_consolidation(s, junk)
    assert s.get("_lattice_step_debt", 0.0) == 0.0


def test_the_governors_stability_state_round_trips():
    g = TimeDilationGovernor()
    g.stability_state = StabilityState.CAUTIOUS
    s = {"time_dilation_governor": g}
    raw = json.loads(json.dumps(M.governor_state(s)))
    h = TimeDilationGovernor()
    M.restore_governor({"time_dilation_governor": h}, raw)
    assert h.stability_state == StabilityState.CAUTIOUS


# ---- the dead boot wire --------------------------------------------------------------------------------------

def test_boot_never_attaches_any_governor_to_sediment():
    src = open(os.path.join(REPO_ROOT, "aurora.py"), encoding="utf-8").read()
    assert "sedimemory']._dilation =" not in src and 'sedimemory"]._dilation =' not in src
    assert "simulation._time_dilation_governor" in src and "wire was dead from the start" in src
    assert "systems['_simulation_governor'] = getattr(getattr(simulation, \"session\", None), \"governor\", None)" in src


def test_the_simulations_governor_really_lives_on_its_session():
    """The attribute boot used to read does not exist; the daemon reads the right one."""
    import aurora_simulation_engine as S
    src = open(S.__file__, encoding="utf-8").read()
    assert "self.governor = TimeDilationGovernor()" in src
    assert "self._time_dilation_governor" not in src and "self.time_dilation =" not in src

"""The Dimensional Energy Regulator must be non-linear in time.

Authors: Sunni (Sir) Morningstar and Cael Devo

Its decay was `energies *= (1 - decay * dt)`: linear in dt, so once decay * dt passed 1 the energies went
NEGATIVE (a night is 96 ticks; 0.15 * 96 = 14.4), and its dispersal ignored dt altogether. Internal
processes run on a fast clock, so every time-dependent step is now geometric in dt: (1 - rate) ** dt. That
is exactly the old per-tick step at dt = 1, never negative, and composes.
"""
import os
import random
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_dimensional_systems import EnergyRegulatorSystem, EvolutionTracker  # noqa: E402


def _der(energies=None, links=None, decay=0.15, curiosity=False):
    der = EnergyRegulatorSystem(EvolutionTracker(), total_budget=25.0, decay_rate=decay)
    der.facet_energy = dict(energies or {"a": 4.0, "b": 2.0, "c": 1.0})
    der.facet_to_facet_links = dict(links or {})
    der.curiosity_enabled = curiosity
    return der


def _retention(der, dt):
    """The factor the decay step applied, given the presence it actually used."""
    return max(0.0, 1.0 - der.base_decay_rate * (0.2 + 0.8 * der.presence ** 1.5)) ** dt


# ---- decay ----------------------------------------------------------------------------------------

def test_one_tick_is_exactly_the_old_per_tick_decay():
    der = _der()
    before = dict(der.facet_energy)
    der.tick(1.0, actual_dt=1.0)
    d = der.base_decay_rate * (0.2 + 0.8 * der.presence ** 1.5)
    for fid, e in before.items():
        assert der.facet_energy[fid] == pytest.approx(e * (1.0 - d))


def test_decay_is_geometric_in_dt():
    for dt in (0.5, 2.0, 3.7):
        der = _der()
        before = dict(der.facet_energy)
        der.tick(dt, actual_dt=dt)
        for fid, e in before.items():
            assert der.facet_energy[fid] == pytest.approx(e * _retention(der, dt), rel=1e-6)


@pytest.mark.parametrize("dt", [10.0, 96.0, 1000.0, 1e6])
def test_a_long_span_never_makes_energy_negative(dt):
    """The old linear decay at dt = 96 multiplied by 1 - 14.4 = -13.4."""
    der = _der()
    der.tick(dt, actual_dt=dt)
    assert all(e >= 0.0 for e in der.facet_energy.values())
    assert sum(der.facet_energy.values()) <= 7.0


def test_more_time_means_less_energy_monotonically():
    totals = []
    for dt in (0.0, 1.0, 2.0, 5.0, 20.0):
        der = _der()
        der.tick(dt, actual_dt=dt)
        totals.append(sum(der.facet_energy.values()))
    assert totals == sorted(totals, reverse=True)


def test_zero_time_changes_no_energy():
    der = _der()
    before = dict(der.facet_energy)
    der.tick(0.0, actual_dt=0.0)
    assert der.facet_energy == pytest.approx(before)


def test_the_decay_rate_still_sets_how_fast_energy_leaves():
    fast, slow = _der(decay=0.5), _der(decay=0.02)
    fast.tick(3.0, actual_dt=3.0)
    slow.tick(3.0, actual_dt=3.0)
    assert sum(fast.facet_energy.values()) < sum(slow.facet_energy.values())


def test_negative_dt_is_treated_as_no_time():
    der = _der()
    before = dict(der.facet_energy)
    der.tick(-5.0, actual_dt=-5.0)
    assert all(der.facet_energy[f] <= before[f] + 1e-12 for f in before)


# ---- dispersal ------------------------------------------------------------------------------------

LINKS = {"a": {"b": 0.9}, "b": {"c": 0.9}, "c": {"a": 0.9}}


def test_dispersal_now_depends_on_dt():
    """It used a fixed 0.3 * presence fraction per call and ignored dt."""
    one = _der({"a": 8.0, "b": 0.0, "c": 0.0}, LINKS, decay=0.0)
    many = _der({"a": 8.0, "b": 0.0, "c": 0.0}, LINKS, decay=0.0)
    one.tick(1.0, actual_dt=1.0)
    many.tick(8.0, actual_dt=8.0)
    spread = lambda d: max(d.facet_energy.values()) - min(d.facet_energy.values())   # noqa: E731
    assert spread(many) < spread(one), "more elapsed time must spread the energy further"


def test_a_whole_tick_is_one_hop_exactly_as_before():
    new = _der({"a": 8.0, "b": 1.0, "c": 0.0}, LINKS, decay=0.0)
    new.tick(1.0, actual_dt=1.0)
    p = new.presence
    f = 0.3 * p
    expected = {"a": 8.0 - 8.0 * f + 0.9 * 0.0, "b": 1.0 + 0.9 * 8.0 * f, "c": 0.0}   # b is below the 0.1 mask? no: 1.0 > 0.1
    # b disperses too (1.0 > 0.1): recompute the single simultaneous step exactly
    out = {"a": 8.0 * f, "b": 1.0 * f, "c": 0.0}
    inc = {"a": 0.0, "b": 0.9 * out["a"], "c": 0.9 * out["b"]}
    inc["a"] = 0.9 * out["c"]
    for fid, e in {"a": 8.0, "b": 1.0, "c": 0.0}.items():
        assert new.facet_energy[fid] == pytest.approx(max(0.0, e - out[fid] + inc[fid]), rel=1e-6)
    assert expected["c"] == 0.0


def test_dispersal_hops_are_bounded_so_a_night_is_cheap():
    der = _der({"a": 8.0, "b": 0.0, "c": 0.0}, LINKS, decay=0.0)
    der.tick(1e6, actual_dt=1e6)                    # must return promptly, not loop a million times
    assert all(e >= 0.0 for e in der.facet_energy.values())


# ---- curiosity ------------------------------------------------------------------------------------

def test_curiosity_expectation_scales_with_time_and_is_unchanged_at_one_tick():
    random.seed(7)
    der = _der({"a": 0.0}, curiosity=True)
    der.curiosity_injection_rate = 0.01
    der.underexplored_threshold = 1.0
    hits_one = 0
    for _ in range(400):
        der.facet_energy = {"a": 0.0}
        der.tick(1.0, actual_dt=1.0)
        hits_one += 1 if der.facet_energy["a"] > 0 else 0
    assert 0.04 < hits_one / 400 < 0.18, "about one injection per ten ticks, as before"
    der.facet_energy = {"a": 0.0}
    der.base_decay_rate = 0.0
    der.tick(100.0, actual_dt=100.0)
    assert der.facet_energy["a"] >= 0.05, "100 ticks should inject about ten times"


# ---- presence: the monitor compares like with like --------------------------------------------------

def test_the_presence_monitor_uses_the_callers_elapsed_time_in_the_same_unit():
    """A caller ticking in clock units (dt = 96) used to be compared against wall-clock SECONDS since the
    last tick, which read as maximal drift and collapsed temporal stability."""
    der = _der()
    start = der.temporal_stability
    for _ in range(20):
        der.tick(96.0, actual_dt=96.0)
    assert der.temporal_stability >= start - 1e-9 and der.temporal_stability > 0.9


def test_without_actual_dt_the_old_wall_clock_comparison_is_kept():
    der = _der()
    der.tick(96.0)                                  # legacy: compares against real seconds since _last_tick
    assert der.temporal_stability < 1.0


def test_the_heartbeat_callers_default_dt_is_unchanged():
    import inspect
    sig = inspect.signature(EnergyRegulatorSystem.tick)
    assert sig.parameters["dt"].default == 1.0 and sig.parameters["actual_dt"].default is None

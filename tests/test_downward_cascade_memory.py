"""The downward pass must reach Memory and Identity, in the order the physics gives.

AURORA_COGNITIVE_PHYSICS section 8: a failed RECONCILIATION flags the tension AND makes a volatile
Surface Memory write; an Understanding makes the geological write, and (section 6) Memory "updates
Identity field configuration after each write" and "shifts Pressure baselines (deep Memory shapes
what feels heavy now)". Identity may not be authored by a single turn (sections 2, 9).

Authors: Sunni (Sir) Morningstar and Cael Devo
"""
import collections
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_manifold_directory.noncomp_field import NoncompField  # noqa: E402
from aurora_sedimemory import SediMemory  # noqa: E402


def _axes(mem, key):
    return collections.Counter(f.axis for f in mem.get_recent_fragments(500) if key(f))


# ---- surface write: unresolved tension is remembered, volatilely ------------------------------

def test_unresolved_tension_lands_only_in_the_volatile_strata():
    m = SediMemory()
    assert m.surface_write({"flags": ["boundary_tension_unresolved"], "tension": {"total": 0.4}, "topic": "x"}) > 0
    axes = set(_axes(m, lambda f: True))
    assert axes <= {"X", "N"}, "T/B/A stay zero so it never reaches the slow strata"
    assert "X" in axes


def test_the_tension_sets_how_much_it_weighs():
    def n_mass(total):
        m = SediMemory()
        m.surface_write({"tension": {"total": total}})
        return sum(f.resonance for f in m.get_recent_fragments(100) if f.axis == "N")
    assert n_mass(0.9) > n_mass(0.1)


def test_the_flag_and_topic_are_kept():
    """Each strain filter keeps the slice in its own vocabulary: the topic everywhere, the
    magnitude as `pressure` (N / MAGNITUDE), the flag as `anomaly` (DIFFERENCE)."""
    m = SediMemory()
    m.surface_write({"flags": ["boundary_tension_unresolved"], "tension": {"total": 0.3}, "topic": "photosynthesis"})
    kept = [f.content for f in m.get_recent_fragments(100)]
    assert all(c.get("topic") == "photosynthesis" for c in kept)
    assert any(c.get("pressure") == 0.3 for c in kept)
    assert any("boundary_tension_unresolved" in str(c.get("anomaly", "")) for c in kept)


@pytest.mark.parametrize("bad", [None, {}, {"tension": "oops"}, {"tension": {"total": None}}, {"flags": None}])
def test_garbage_is_a_write_not_a_crash(bad):
    assert isinstance(SediMemory().surface_write(bad), int)


def test_geological_and_surface_writes_reach_different_strata():
    m = SediMemory()
    m.geological_write({"crystal_level": "understanding", "resolved_accuracy": 0.8, "resolved_boundary_ambiguity": 0.2})
    deep = set(_axes(m, lambda f: True))
    s = SediMemory()
    s.surface_write({"tension": {"total": 0.5}})
    assert deep == {"A", "B"} and set(_axes(s, lambda f: True)) <= {"X", "N"}


# ---- what the strata weigh --------------------------------------------------------------------

def test_deep_axis_weights_follow_what_is_deposited():
    m = SediMemory()
    assert sum(m.deep_axis_weights().values()) == 0
    m.geological_write({"crystal_level": "understanding", "resolved_accuracy": 0.8, "resolved_boundary_ambiguity": 0.2})
    w = m.deep_axis_weights()
    assert w["A"] > 0 and w["B"] > 0 and w["X"] == w["T"] == w["N"] == 0


# ---- the identity field: baseline shaped by deep memory ---------------------------------------

U = {"resolved_accuracy": 0.5, "deep_memory": {"X": 1, "T": 0, "N": 1, "B": 5, "A": 5}}


def test_the_baseline_is_born_at_the_fixed_equilibrium():
    from aurora_manifold_directory.noncomp_field import REFERENCE_AXIS_PRESSURE
    assert set(NoncompField().reference_axis_pressures().values()) == {REFERENCE_AXIS_PRESSURE}


def test_deep_memory_moves_the_baseline_toward_its_shares_gradually():
    f = NoncompField()
    f.accept_understanding_update(U)
    r1 = f.reference_axis_pressures()
    assert r1["A"] > 0.1 > r1["T"]
    for _ in range(40):
        f.accept_understanding_update(U)
    r = f.reference_axis_pressures()
    assert r["A"] > r1["A"], "one turn must only move it a fraction of the way"
    assert r["A"] == pytest.approx(r["B"]) and r["X"] == pytest.approx(r["N"])
    assert r["T"] < 0.01


def test_memory_redistributes_what_feels_heavy_and_never_inflates_the_field():
    f = NoncompField()
    for _ in range(10):
        f.accept_understanding_update(U)
    assert sum(f.reference_axis_pressures().values()) == pytest.approx(0.5)


def test_a_more_accurate_understanding_moves_it_further():
    lo, hi = NoncompField(), NoncompField()
    lo.accept_understanding_update({**U, "resolved_accuracy": 0.0})
    hi.accept_understanding_update({**U, "resolved_accuracy": 1.0})
    assert hi.reference_axis_pressures()["A"] > lo.reference_axis_pressures()["A"]


@pytest.mark.parametrize("u", [None, {}, {"deep_memory": {}}, {"deep_memory": {"X": 0, "T": 0}},
                               {"deep_memory": "oops"}, {"deep_memory": {"Z": 5}}])
def test_no_deep_memory_changes_nothing(u):
    f = NoncompField()
    before = dict(f.reference_axis_pressures())
    f.accept_understanding_update(u)
    assert f.reference_axis_pressures() == before


def test_the_discharge_relaxes_toward_the_baseline_and_the_default_is_unchanged():
    f = NoncompField()
    for _ in range(60):
        f.ingest_internal_signal("tension", 1.0, "N")
    for _ in range(80):
        f.reset_pressure_topology({"resolved_accuracy": 1.0})
    assert f.status()["axis_pressures"]["N"] == pytest.approx(0.05), "0.5 x the 0.10 birth reference, as before"


# ---- the cascade: order and no double dispatch --------------------------------------------------

class _Salience:
    def __init__(self):
        self.calls = 0

    def recalibrate_salience(self, understanding):
        self.calls += 1


def _contract():
    from aurora_internal.aurora_understanding_contract import RuntimeUnderstandingContract as C
    c = C.__new__(C)
    c.records = []
    c._history_append = lambda r: c.records.append(r)
    c.state = {"M": {"active_topic": "photosynthesis"}, "time_index": 4}
    return c


UNDERSTANDING = {"crystal_level": "understanding", "resolved_accuracy": 0.7, "resolved_cost": 0.1,
                 "resolved_boundary_ambiguity": 0.2, "resolved_meaning_topic": "photosynthesis",
                 "tension_at_resolution": {"total": 0.05}, "time_index": 4}


def test_memory_writes_first_and_identity_is_shaped_by_what_it_wrote():
    c = _contract()
    mem, field = SediMemory(), NoncompField()
    c._trigger_downward_cascade({"sedimemory": mem, "identity_field": field}, dict(UNDERSTANDING))
    d = c.records[-1]["dispatches"]
    assert d.index("sedimemory.geological_write:ok") < d.index("identity_field.accept_understanding_update:ok")
    r = field.reference_axis_pressures()
    assert r["A"] > r["X"], "deep strata (A/B) now weigh more than the fast ones, so the baseline followed"


def test_a_system_reachable_under_two_keys_is_dispatched_once():
    c = _contract()
    field, sal = NoncompField(), _Salience()
    c._trigger_downward_cascade({"sedimemory": SediMemory(), "identity_field": field,
                                 "behavioral_identity": field, "consciousness": sal,
                                 "consciousness_engine": sal}, dict(UNDERSTANDING))
    d = c.records[-1]["dispatches"]
    assert sal.calls == 1, "recalibrate_salience adds earned coherence: twice would double-count"
    assert "behavioral_identity.accept_understanding_update:duplicate_target" in d
    assert "consciousness_engine.recalibrate_salience:duplicate_target" in d


def test_without_sedimemory_identity_simply_is_not_reshaped():
    c = _contract()
    field = NoncompField()
    before = dict(field.reference_axis_pressures())
    c._trigger_downward_cascade({"identity_field": field}, dict(UNDERSTANDING))
    assert field.reference_axis_pressures() == before


# ---- the failure branch remembers what it flags -------------------------------------------------

def test_a_failed_reconciliation_flags_and_remembers():
    c = _contract()
    mem = SediMemory()
    c._flag_tension({"sedimemory": mem}, ["boundary_tension_unresolved"], {"time_index": 4},
                    session_id="s", tension={"total": 0.2})
    assert c.records[-1]["phase"] == "reflection_tension", "the flag is still recorded"
    assert mem.get_recent_fragments(50), "and now it is remembered too"
    assert set(_axes(mem, lambda f: True)) <= {"X", "N"}


def test_flagging_without_a_memory_still_flags():
    c = _contract()
    c._flag_tension({}, ["boundary_tension_unresolved"], {"time_index": 4})
    assert c.records[-1]["flags"] == ["boundary_tension_unresolved"]


# ---- genealogy records the Understanding ----------------------------------------------------------

class _Genealogy:
    def __init__(self):
        self.calls = []

    def observe(self, **kw):
        self.calls.append(kw)

    def register_pair(self, *a, **k):
        pass


def test_the_cascade_no_longer_calls_a_genealogy_method_that_exists_nowhere():
    import inspect
    from aurora_internal.aurora_understanding_contract import RuntimeUnderstandingContract as C
    src = inspect.getsource(C._trigger_downward_cascade)
    assert '_soft("genealogy", "accept_understanding_update"' not in src
    assert '_soft("constraint_genealogy", "accept_understanding_update"' not in src


def test_run_reflection_cycle_records_the_understanding_before_the_cascade():
    import inspect
    from aurora_internal.aurora_understanding_contract import RuntimeUnderstandingContract as C
    src = inspect.getsource(C.run_reflection_cycle)
    assert 'phase="understanding"' in src
    assert src.index('phase="understanding"') < src.index("self._trigger_downward_cascade(systems, understanding)")


def test_the_understanding_event_carries_the_resolved_pressure_as_its_after_state():
    c = _contract()
    g = _Genealogy()
    c.register_genealogy = lambda gen: None
    before = {"X": {"score": 0.5}, "T": {"sequence_gap": 0.4}, "N": {"total": 0.6},
              "B": {"ambiguity": 0.545}, "A": {"score": 0.3}, "time_index": 4}
    import copy
    resolved = copy.deepcopy(before)
    resolved["N"]["total"], resolved["B"]["ambiguity"], resolved["A"]["score"] = 0.1, 0.2, 0.7
    c._record_genealogy_event({"genealogy": g}, phase="understanding", before_state=before,
                              after_state=resolved, notes={"resolved_meaning_topic": "x"})
    assert len(g.calls) == 1
    call = g.calls[0]
    # relief: the turn carried more pressure into reflection than it resolved to
    assert call["pressure_before"].B > call["pressure_after"].B
    assert call["pressure_before"].N > call["pressure_after"].N
    assert call["pressure_before"].A > call["pressure_after"].A     # A pressure is 1 - accuracy
    assert call["notes"]["resolved_meaning_topic"] == "x"

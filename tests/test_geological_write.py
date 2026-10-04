"""Resolved understanding must reach deep sediment.

The downward cascade dispatches "Memory: geological stratum write (deepest -> near-immutable)"
to sedimemory.geological_write, which did not exist: _soft() swallowed it as not_found on every
turn, so understanding never reached the geological (B/A) strata.

Authors: Sunni (Sir) Morningstar and Cael Devo
"""
import collections
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_sedimemory import SediMemory  # noqa: E402

U = {"resolved_accuracy": 0.16, "resolved_cost": 0.17, "resolved_boundary_ambiguity": 0.295,
     "resolved_meaning_topic": "wrong", "time_index": 6, "crystal_level": "understanding"}


def _axes(mem):
    return collections.Counter(f.axis for f in mem.get_recent_fragments(500))


def test_the_cascades_dispatch_target_exists():
    assert callable(getattr(SediMemory, "geological_write", None))
    src = open(os.path.join(REPO_ROOT, "aurora_internal", "aurora_understanding_contract.py"), encoding="utf-8").read()
    assert '_soft("sedimemory", "geological_write", understanding)' in src


J = {"crystal_level": "understanding"}   # the justification: this IS an Understanding


@pytest.mark.parametrize("u", [U, {**J, "resolved_accuracy": 0.9, "resolved_boundary_ambiguity": 0.05},
                               {**J, "resolved_accuracy": 0.5, "resolved_boundary_ambiguity": 0.5}])
def test_only_the_geological_basins_catch_it(u):
    m = SediMemory()
    assert m.geological_write(u) > 0
    assert set(_axes(m)) == {"A", "B"}, "T=N=0 and X at the floor: the fast basins must let it fall through"


def test_the_deposit_records_what_was_understood():
    """Each strain filter keeps only the slice that resonates plus a provenance whitelist: every
    fragment keeps the topic, and the COST-dimension filter keeps the resolved cost."""
    m = SediMemory()
    m.geological_write(U)
    frags = m.get_recent_fragments(50)
    assert frags and all(f.content.get("topic") == "wrong" for f in frags)
    assert any(f.content.get("resolved_cost") == 0.17 for f in frags)


def _a_resonance(u):
    m = SediMemory()
    m.geological_write(u)
    return sum(f.resonance for f in m.get_recent_fragments(50) if f.axis == "A")


def test_how_strongly_it_lands_follows_the_understanding_not_a_constant():
    weak = _a_resonance({**J, "resolved_accuracy": 0.1, "resolved_boundary_ambiguity": 0.5})
    strong = _a_resonance({**J, "resolved_accuracy": 0.9, "resolved_boundary_ambiguity": 0.5})
    assert strong > weak


@pytest.mark.parametrize("bad", [None, {}, {**J, "resolved_accuracy": "oops"}, {**J, "resolved_boundary_ambiguity": None},
                                 {**J, "resolved_accuracy": 7, "resolved_boundary_ambiguity": -3}])
def test_garbage_in_is_a_deposit_not_a_crash(bad):
    assert isinstance(SediMemory().geological_write(bad), int)


# ---- the law: no geological write without constraint significance justification ----------------

@pytest.mark.parametrize("u", [None, {}, {"resolved_accuracy": 0.9, "resolved_boundary_ambiguity": 0.05},
                               {"crystal_level": "thought", "resolved_accuracy": 0.9}])
def test_an_unjustified_write_is_refused_and_leaves_no_trace(u):
    """AURORA_COGNITIVE_PHYSICS sections 6, 9, 11: "No write may skip to geological depth without
    constraint significance justification." Enforced by the method, not trusted to the caller."""
    m = SediMemory()
    assert m.geological_write(u) == 0
    assert not m.get_recent_fragments(50)


def test_a_reconciled_understanding_is_justified_by_its_resolution_tension_too():
    m = SediMemory()
    assert m.geological_write({"tension_at_resolution": {"total": 0.07}, "resolved_accuracy": 0.5}) > 0

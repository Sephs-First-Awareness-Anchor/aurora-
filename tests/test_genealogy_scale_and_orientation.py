"""Genealogy must stay cheap as it grows, and its orientation must be per-axis.

Two defects found live on the full profile (13,262 abilities, 356 links): the relevance index was
rebuilt over every ability on nearly every observation (527,538 feature computations in three
turns; 5-18s turns), and pressure_orientation() -- the grammar engine's designed orientation
source -- came back as one number repeated on all five axes, because the per-axis prediction
channel was only ever armed by a training-time path.

Authors: Sunni (Sir) Morningstar and Cael Devo
"""
import os
import random
import sys
import tempfile

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_evolution_stack import ConstraintGenealogyLogger, GenealogyConfig, PressureVec, TraceItem  # noqa: E402


def _logger():
    return ConstraintGenealogyLogger(run_id="t", config=GenealogyConfig(), output_dir=tempfile.mkdtemp())


def _feed(g, n, seed=3, start=0):
    rng = random.Random(seed)
    base = {"X": 0.9, "T": 0.1, "N": 0.5, "B": 0.7, "A": 0.3}
    for i in range(start, start + n):
        b = {k: min(1.0, max(0.0, v + rng.uniform(-0.05, 0.05))) for k, v in base.items()}
        a = {k: max(0.0, v - 0.15) for k, v in b.items()}
        trace = [TraceItem(kind="ABILITY", id=f"ability_{j}") for j in range(1 + i % 3)]
        g.observe(PressureVec(**b), trace, PressureVec(**a), notes={})


# ---- orientation ------------------------------------------------------------------------------

def test_orientation_is_not_one_number_repeated_on_every_axis():
    g = _logger()
    _feed(g, 300)
    o = g.pressure_orientation()
    assert len({round(v, 4) for v in o.values()}) >= 4, o


def test_the_axis_carrying_the_most_injected_pressure_is_the_most_dampened():
    g = _logger()
    _feed(g, 300)
    o = g.pressure_orientation()
    assert o["X"] < o["T"], "X carries 0.9 of injected pressure, T carries 0.1"


def test_orientation_stays_inside_the_curves_own_bounds():
    g = _logger()
    _feed(g, 300)
    assert all(0.45 <= v <= 1.15 for v in g.pressure_orientation().values())


def test_every_axis_curve_is_armed_by_a_live_observation():
    g = _logger()
    _feed(g, 40)
    assert all(len(g._axis_curves[ax]._predictions) > 0 for ax in "XTNBA"), \
        "record_outcome returned at once on every axis: nothing was predicted before it"


# ---- the relevance index ------------------------------------------------------------------------

def _full_rebuild(g):
    g._representation_relevance_stamp = None
    g._representation_relevance_ids = None
    return {k: list(v) for k, v in g._representation_relevance_index().items()}


def test_adding_items_indexes_only_the_new_ones():
    g = _logger()
    _feed(g, 80)
    g._representation_relevance_index()
    calls = []
    orig = g._relevance_features_for_item
    g._relevance_features_for_item = lambda iid: (calls.append(iid), orig(iid))[1]
    _feed(g, 6, start=80)
    g._representation_relevance_index()
    n_items = len(set(g.links) | set(g.abilities))
    assert len(calls) < n_items // 2, f"{len(calls)} feature computations for {n_items} items: a full rebuild"


def test_the_incremental_index_equals_a_full_rebuild():
    g = _logger()
    _feed(g, 60)
    g._representation_relevance_index()
    _feed(g, 40, seed=9, start=60)
    incremental = {k: list(v) for k, v in g._representation_relevance_index().items()}
    assert incremental == _full_rebuild(g)


def test_buckets_stay_sorted_after_incremental_additions():
    g = _logger()
    for step in range(5):
        _feed(g, 20, seed=step, start=step * 20)
        for ids in g._representation_relevance_index().values():
            assert ids == sorted(ids)


def test_a_change_to_what_features_read_forces_a_full_rebuild():
    g = _logger()
    _feed(g, 40)
    g._representation_relevance_index()
    calls = []
    orig = g._relevance_features_for_item
    g._relevance_features_for_item = lambda iid: (calls.append(iid), orig(iid))[1]
    g.mark_representation_identity_dirty()
    g._representation_relevance_index()
    assert len(calls) == len(set(g.links) | set(g.abilities)), "identity changed: everything must be re-read"


def test_consequence_only_updates_no_longer_rebuild_the_index():
    g = _logger()
    _feed(g, 40)
    g._representation_relevance_index()
    calls = []
    orig = g._relevance_features_for_item
    g._relevance_features_for_item = lambda iid: (calls.append(iid), orig(iid))[1]
    for _ in range(34):                       # "34 calls in a single real turn"
        g.mark_representation_index_dirty()
    g._representation_relevance_index()
    assert calls == []

# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA DIRECTIVE -- Causal-Generation Correction, Phase 3 regression suite.

Tests CausalGeneration (aurora_internal/aurora_causal_generation.py) as a
standalone primitive: the structural guarantee it exists to provide is
"no joint_fn call happens before every touch() call for this generation has
completed" -- these tests exercise that guarantee directly, independent of
any one subsystem.

The equivalence test at the bottom validates the abstraction is faithful to
a real, already-fixed production instance (EnergyRegulatorSystem.
register_facets_batch(), aurora_dimensional_systems.py) by reimplementing
its exact semantics with CausalGeneration and asserting byte-identical
resulting state against the real method -- documentation-by-example that
this module actually fits real Aurora code, without modifying that
already-tested production call site itself (Phase 3 is meant to make
*future* fixes easier, not to mandate retrofitting past ones).
"""
import itertools
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_internal.aurora_causal_generation import CausalGeneration  # noqa: E402
from aurora_dimensional_systems import (  # noqa: E402
    CrystalFacet,
    EnergyRegulatorSystem,
    EvolutionTracker,
)


# ---- CausalGeneration: structural guarantees ----

def test_touch_then_reconcile_runs_joint_fn_once_per_distinct_key():
    gen = CausalGeneration()
    gen.touch("a")
    gen.touch("b")
    gen.touch("a")  # same key touched twice -- still one reconcile call

    calls = []
    gen.reconcile(lambda key, results: calls.append(key))

    assert sorted(calls) == ["a", "b"]
    assert len(calls) == 2


def test_reconcile_sees_every_touch_regardless_of_when_it_happened():
    """The core guarantee: a key's joint_fn call must see results from
    EVERY touch() this generation received, not just the ones that
    happened before some other key was touched."""
    gen = CausalGeneration()
    gen.touch("shared", result=1)
    gen.touch("other", result="x")
    gen.touch("shared", result=2)
    gen.touch("shared", result=3)

    captured = {}
    gen.reconcile(lambda key, results: captured.__setitem__(key, list(results)))

    assert captured["shared"] == [1, 2, 3]
    assert captured["other"] == ["x"]


def test_reconcile_order_independent_of_touch_order_for_final_key_set():
    """Shuffling the order items are touched in must not change WHICH
    keys get reconciled or what results each key carries -- only the
    order reconcile() itself visits keys in (first-touched) may differ,
    and joint_fn is responsible for being order-independent across keys
    the same way any Phase 0/2 fix's Pass 2 must be."""
    items = [("a", 1), ("b", 2), ("a", 3), ("c", 4), ("b", 5)]

    def run(order):
        gen = CausalGeneration()
        for key, val in order:
            gen.touch(key, result=val)
        out = {}
        gen.reconcile(lambda k, rs: out.__setitem__(k, sorted(rs)))
        return out

    forward = run(items)
    reversed_order = run(list(reversed(items)))
    shuffled = run([items[2], items[0], items[4], items[1], items[3]])

    assert forward == reversed_order == shuffled == {
        "a": [1, 3], "b": [2, 5], "c": [4],
    }


def test_touch_without_result_still_registers_the_key():
    gen = CausalGeneration()
    gen.touch("k")
    assert gen.touched_keys == ["k"]
    assert gen.results_for("k") == []


def test_read_snapshot_is_a_copy_not_a_live_reference():
    """A generation's read_snapshot must be frozen at construction --
    mutating the source dict afterward must not leak into the snapshot,
    or a caller relying on it for Pass 1 isolation (per the docstring's
    infer_relations_from_context() example) would be silently exposed to
    the exact same-batch leak this class exists to prevent."""
    source = {"sig": {"TYPE": {"uses": 1, "failures": 0}}}
    gen = CausalGeneration(read_snapshot=source)
    source["sig"]["TYPE"]["uses"] = 999
    assert gen.read_snapshot["sig"]["TYPE"]["uses"] == 1


def test_empty_generation_reconciles_to_nothing():
    gen = CausalGeneration()
    calls = []
    gen.reconcile(lambda k, rs: calls.append(k))
    assert calls == []


# ---- Equivalence: faithful to a real, already-fixed production instance ----

def _facets():
    """All 8 physics points pinned explicitly -- see
    tests/test_causal_generation_batch_order.py's identical helper for why
    (CrystalFacet defaults unset points to random.uniform per construction
    call)."""
    return [
        CrystalFacet(facet_id="f1", role="topic", content="a", confidence=0.9,
                     resonance=0.9, sensitivity=0.1, abstractness=0.2,
                     potential=0.5, stability=0.5, coherence=0.5,
                     complexity=0.5, frequency=0.5),
        CrystalFacet(facet_id="f2", role="entity", content="b", confidence=0.8,
                     resonance=0.8, sensitivity=0.2, abstractness=0.3,
                     potential=0.5, stability=0.5, coherence=0.5,
                     complexity=0.5, frequency=0.5),
        CrystalFacet(facet_id="f3", role="intent", content="c", confidence=0.7,
                     resonance=0.7, sensitivity=0.3, abstractness=0.4,
                     potential=0.5, stability=0.5, coherence=0.5,
                     complexity=0.5, frequency=0.5),
        CrystalFacet(facet_id="f4", role="emotion", content="d", confidence=0.6,
                     resonance=0.6, sensitivity=0.4, abstractness=0.5,
                     potential=0.5, stability=0.5, coherence=0.5,
                     complexity=0.5, frequency=0.5),
    ]


def _reimplemented_register_facets_batch(der: EnergyRegulatorSystem, items):
    """Reimplements EnergyRegulatorSystem.register_facets_batch()'s exact
    Pass-1/Pass-2 split using CausalGeneration, instead of its hand-rolled
    touched_ids list + two loops."""
    gen: CausalGeneration = CausalGeneration()
    for facet, category in items:
        der._seed_facet(facet, category)  # Pass 1: independent per-item work
        gen.touch(facet.facet_id)
    gen.reconcile(lambda fid, _results: der._update_links_for_facet(fid))


def test_causal_generation_reproduces_register_facets_batch_exactly():
    items = [(f, "processing") for f in _facets()]

    real = EnergyRegulatorSystem(EvolutionTracker())
    real.register_facets_batch(list(items))

    reimplemented = EnergyRegulatorSystem(EvolutionTracker())
    _reimplemented_register_facets_batch(reimplemented, list(items))

    assert real.facet_to_facet_links == reimplemented.facet_to_facet_links
    assert real.facet_energy == reimplemented.facet_energy
    assert real.registered_facets.keys() == reimplemented.registered_facets.keys()


def test_causal_generation_reimplementation_all_permutations_agree():
    """The reimplementation must itself be order-independent across every
    permutation of one batch, same as the real register_facets_batch()
    (already proven in test_causal_generation_batch_order.py) -- this
    confirms the INFRASTRUCTURE carries the guarantee, not just this one
    hand-written call site."""
    facets = _facets()[:3]
    reference = None
    for perm in itertools.permutations(facets):
        der = EnergyRegulatorSystem(EvolutionTracker())
        _reimplemented_register_facets_batch(
            der, [(f, "processing") for f in perm]
        )
        snapshot = dict(der.facet_to_facet_links)
        if reference is None:
            reference = snapshot
        else:
            assert snapshot == reference

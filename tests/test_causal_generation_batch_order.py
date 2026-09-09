# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA DIRECTIVE -- Causal-Generation Correction, Phase 0 regression suite.

Governing principle under test: computations that are independent reactions
to the SAME occurrence must produce the same committed state regardless of
the physical order the runtime happens to process them in. If shuffling a
batch's arrival order changes the resulting crystal_links, facet_to_facet_
links, or constraint_signature, that's hidden procedural causality -- a bug.

Confirmed instances fixed here (live production code, not a parallel copy):
  1. CrystalProcessingSystem.process_concepts() -- was calling
     _update_crystal_links() per-signal, mid-loop, so an earlier signal's
     resonance links were built against a world missing the batch's later
     signals.
  2. EnergyRegulatorSystem.register_facet() -- was calling
     _update_links_for_facet() per-facet, same defect one layer down.
  3. EnergyRegulatorSystem.register_crystal() -- was dead code (never
     called in the live build) still carrying the old single-item-
     registration assumption; rebuilt on the two-pass pattern (see
     register_facets_batch() below). NOT wired into
     CrystalProcessingSystem.load_crystals() (boot rehydration) -- that
     was tried and reverted after live measurement showed it made full
     boot O(n^2) in the persisted facet count (didn't complete in 5
     minutes against this repo's actual 13,622-facet aurora_state); see
     the comment above test_load_crystals_does_not_register_facets_
     with_energy_system() below for the full account.

Fix shape (Phase 0's reference pattern, reused everywhere in this file):
  Pass 1 (per-item, independent) -- create/seed, no relational computation.
  Pass 2 (joint, once per distinct touched entity) -- run only after the
  full batch has landed.

Note: no IVMEnvelope fixture exists anywhere in this test suite to reuse
(see tests/test_warp_phase1_resonance_graph.py's docstring) -- process_
concepts() only reads envelope.data and envelope.mode (via mode_gate), so
a minimal stand-in with just those two attributes is used here, matching
the existing suite's convention of exercising the real methods directly
rather than building an unrelated envelope-construction fixture.
"""
import itertools
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_dimensional_systems import (  # noqa: E402
    CrystalProcessingSystem,
    Crystal,
    CrystalFacet,
    ConceptSignal,
    EnergyRegulatorSystem,
    EvolutionTracker,
)
from foundational_contract import ExistenceMode  # noqa: E402


class _FakeEnvelope:
    """Minimal stand-in: process_concepts() reads only .data and .mode."""

    def __init__(self, data="some occurrence"):
        self.data = data
        self.mode = ExistenceMode.PERSISTENT


def _dps_with_der():
    tracker = EvolutionTracker()
    der = EnergyRegulatorSystem(tracker)
    dps = CrystalProcessingSystem(tracker, energy_system=der)
    return dps, der


def _signals():
    """Five distinct concepts, one occurrence -- deliberately varied
    confidence/weights so their relational computations are not
    accidentally symmetric (a symmetric fixture could pass by coincidence
    even with the bug present)."""
    return [
        ConceptSignal("alpha", "topic", 0.9, {"X": 1.0, "N": 0.0}),
        ConceptSignal("beta", "entity", 0.8, {"X": 0.9, "N": 0.1}),
        ConceptSignal("gamma", "intent", 0.7, {"X": 0.8, "N": 0.2}),
        ConceptSignal("delta", "emotion", 0.6, {"X": 0.7, "N": 0.3}),
        ConceptSignal("epsilon", "action", 0.5, {"X": 0.6, "N": 0.4}),
    ]


def _committed_snapshot(dps, der):
    """The part of committed state that must not depend on arrival order.
    Deliberately excludes facet_to_facet_links here: crystal.add_facet()
    seeds each CrystalFacet's physics points (potential/stability/
    coherence/complexity/frequency) from random.uniform() when not given
    explicitly, so two independently-constructed DPS instances would never
    match on facet-level resonance regardless of signal order -- that
    randomness is orthogonal to the causal-generation defect this test
    targets. register_facets_batch()'s own order-independence is covered
    directly below with facets whose physics points are pinned."""
    return {
        "crystal_links": {
            cid: dict(links) for cid, links in dps.crystal_links.items()
        },
        "constraint_signatures": {
            c.crystal_id: dict(c.constraint_signature or {})
            for c in dps.crystals.values()
        },
        "registered_facet_ids": sorted(der.registered_facets.keys()),
    }


# ---- process_concepts(): shuffle-order regression (Phase 0 template) ----

def test_process_concepts_batch_order_independent():
    """Reference regression test: run the SAME batch of signals from the
    SAME occurrence through process_concepts() under multiple physical
    orderings and confirm the committed crystal_links, constraint
    signatures, and facet-to-facet links are identical every time."""
    base_signals = _signals()
    envelope = _FakeEnvelope()

    orderings = [
        base_signals,
        list(reversed(base_signals)),
        [base_signals[2], base_signals[0], base_signals[4], base_signals[1], base_signals[3]],
        [base_signals[4], base_signals[3], base_signals[2], base_signals[1], base_signals[0]],
    ]

    snapshots = []
    for ordering in orderings:
        dps, der = _dps_with_der()
        dps.process_concepts(envelope, ordering)
        snapshots.append(_committed_snapshot(dps, der))

    reference = snapshots[0]
    for i, snap in enumerate(snapshots[1:], start=1):
        assert snap == reference, (
            f"process_concepts() ordering #{i} diverged from ordering #0 -- "
            "committed state depends on arrival order (Phase 0 defect)."
        )


def test_process_concepts_all_permutations_agree():
    """Exhaustive version for a smaller batch: every permutation of 4
    signals from one occurrence must commit to the same state."""
    signals = _signals()[:4]
    envelope = _FakeEnvelope()

    reference = None
    for perm in itertools.permutations(signals):
        dps, der = _dps_with_der()
        dps.process_concepts(envelope, list(perm))
        snap = _committed_snapshot(dps, der)
        if reference is None:
            reference = snap
        else:
            assert snap == reference, (
                "process_concepts() committed state differs across "
                "permutations of the same one-occurrence batch."
            )


def test_process_concepts_without_energy_system_still_order_independent():
    """The crystal_links half of the fix must hold even when no
    EnergyRegulatorSystem is wired in (energy tracking is optional)."""
    tracker = EvolutionTracker()
    dps = CrystalProcessingSystem(tracker, energy_system=None)
    envelope = _FakeEnvelope()

    signals = _signals()
    dps.process_concepts(envelope, signals)
    forward_links = {cid: dict(l) for cid, l in dps.crystal_links.items()}

    tracker2 = EvolutionTracker()
    dps2 = CrystalProcessingSystem(tracker2, energy_system=None)
    dps2.process_concepts(envelope, list(reversed(signals)))
    reversed_links = {cid: dict(l) for cid, l in dps2.crystal_links.items()}

    assert forward_links == reversed_links


# ---- EnergyRegulatorSystem.register_facets_batch(): same pattern ----

def _facets():
    """All 8 physics points pinned explicitly -- CrystalFacet defaults
    unset points to random.uniform(0.3, 0.7) per construction call, which
    would make two separate calls to this helper compare noise to noise
    and falsely look order-dependent. Determinism here is a fixture
    requirement, not a claim about production facets."""
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
    ]


def test_register_facets_batch_order_independent():
    forward = EnergyRegulatorSystem(EvolutionTracker())
    forward.register_facets_batch([(f, "processing") for f in _facets()])

    backward = EnergyRegulatorSystem(EvolutionTracker())
    backward.register_facets_batch([(f, "processing") for f in reversed(_facets())])

    assert forward.facet_to_facet_links == backward.facet_to_facet_links


def test_register_facets_batch_matches_fully_converged_single_calls():
    """The batch result must equal what you'd get from calling
    register_facet() one at a time AFTER every facet already exists --
    i.e. the batch reaches the same fixed point as full convergence, it
    just gets there without an arrival-order-dependent partial view along
    the way."""
    batched = EnergyRegulatorSystem(EvolutionTracker())
    batched.register_facets_batch([(f, "processing") for f in _facets()])

    converged = EnergyRegulatorSystem(EvolutionTracker())
    for f in _facets():
        converged._seed_facet(f, "processing")
    for f in _facets():
        converged._update_links_for_facet(f.facet_id)

    assert batched.facet_to_facet_links == converged.facet_to_facet_links


# ---- register_crystal(): rebuilt two-pass, no longer dead code ----

def test_register_crystal_is_order_independent_across_its_own_facets():
    der = EnergyRegulatorSystem(EvolutionTracker())
    crystal = Crystal(crystal_id="c1", concept="alpha")
    for f in _facets():
        crystal.facets[f.facet_id] = f

    der.register_crystal(crystal, category="processing")
    single_call_links = dict(der.facet_to_facet_links)

    der2 = EnergyRegulatorSystem(EvolutionTracker())
    der2.register_facets_batch([(f, "processing") for f in reversed(_facets())])

    assert single_call_links == der2.facet_to_facet_links


# ---- load_crystals(): boot rehydration stays deliberately unbatched ----
#
# An earlier version of this fix wired load_crystals() to register every
# loaded crystal's facets through register_facets_batch() as one joint
# boot-time batch. Reverted: _update_links_for_facet()/_update_crystal_
# links() are each an O(n) scan per facet/crystal, so registering the full
# boot batch is O(n^2) -- measured against this repo's actual
# aurora_state/dps_crystals.json (5,977 crystals, 13,622 facets), it did
# not complete in 5 minutes and timed out several live "boot the real
# state dir" tests. Fixing that algorithmic cost is Phase 4 territory
# (hardware-adaptive/multi-scale execution), not this directive's scope
# (order-independence of committed outcome). register_crystal()/
# register_facets_batch() remain correct, tested two-pass primitives
# above -- available for a caller with a smaller batch -- just not
# auto-wired into full boot rehydration.

def test_load_crystals_does_not_register_facets_with_energy_system(tmp_path):
    """Documents the current, deliberate boot behavior: loading crystals
    populates self.crystals/concept_index only. A rehydrated facet has no
    energy/resonance state until a later live turn touches its crystal
    again -- the same limitation this module had before this directive,
    now measured and documented rather than silently dead code."""
    tracker = EvolutionTracker()
    der = EnergyRegulatorSystem(tracker)
    dps = CrystalProcessingSystem(tracker, energy_system=der)

    c1 = dps._get_or_create("alpha")
    c1.add_facet(role="topic", content="a", confidence=0.9)
    c2 = dps._get_or_create("beta")
    c2.add_facet(role="entity", content="b", confidence=0.8)

    path = str(tmp_path / "crystals.json")
    assert dps.save_crystals(path)

    tracker2 = EvolutionTracker()
    der2 = EnergyRegulatorSystem(tracker2)
    dps2 = CrystalProcessingSystem(tracker2, energy_system=der2)
    loaded = dps2.load_crystals(path)

    assert loaded == 2
    all_facet_ids = {
        fid for c in dps2.crystals.values() for fid in c.facets.keys()
    }
    assert all_facet_ids, "fixture produced no facets to check"
    assert der2.registered_facets == {}
    assert der2.facet_energy == {}

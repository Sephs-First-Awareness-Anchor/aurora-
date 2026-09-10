# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA DIRECTIVE -- Causal-Generation Correction, Phase 5 acceptance suite.

Whole-system validation at the scope actually corrected by Phases 0-2:
CrystalProcessingSystem.process_concepts()/EnergyRegulatorSystem.
register_facet() (aurora_dimensional_systems.py, Phase 0);
OntologicalWeb._select_relation_type()/infer_relations_from_context()
(aurora_internal/aurora_ontological_scaffolding.py, Phase 2);
build_relevance_anchor_set() (aurora_constraint_emission.py, Phase 2);
physics_absorb_truth() (corpus_runner.py, Phase 2).

The four acceptance categories from the source directive, applied here:

1. CRITICAL REGRESSION TEST -- for every corrected causal generation, vary
   physical execution order and confirm committed state is semantically
   equivalent. Phase 0's own instance already has a dedicated suite
   (tests/test_causal_generation_batch_order.py); this file adds the same
   pattern for Phase 2's three fixes, one test class per fix.

2. SINGLE-CORE TEST -- force serial execution of a same-generation batch;
   confirm results match the multi-order test above, proving order-
   independence isn't an accidental byproduct of concurrency that happens
   not to have been exercised. Not a separate test here: this whole
   directive introduced ZERO concurrency (per its own explicit instruction
   not to -- "Do not introduce physical concurrency merely to correct
   causal semantics"). Every fixed call site, and everything in
   CausalGeneration (Phase 3), runs single-threaded, synchronous Python --
   so every test in category 1 already IS a single-core test; there is no
   separate multi-threaded version to compare it against yet. This
   category is trivially satisfied by construction, not by a dedicated
   test, and stays that way until Phase 4 machinery is actually justified
   (see the note at the bottom of this file).

3. PARALLEL-CAPACITY TEST -- where hardware supports it and workload
   justifies it, confirm independent same-generation work CAN physically
   overlap without changing the result. N/A at this scope: no concurrency
   exists to test. Per the directive, "do not treat a failure to overlap
   as a defect unless it also changes output" -- there is no overlap here
   to evaluate either way. See the Phase 4 note below for why introducing
   it now would be premature rather than merely untested.

4. SELF-EXTENSION TEST -- introduce a new participant with a genuine
   structural relationship to some occurrence, without modifying the
   original producer of that occurrence, and confirm it becomes a valid
   participant in the appropriate generation without disrupting existing
   participants, and that an unrelated participant does NOT get processed
   just because it exists. See test_self_extension_* below.
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_internal.aurora_ontological_scaffolding import (  # noqa: E402
    OntologicalScaffoldingEngine,
)
from aurora_constraint_emission import build_relevance_anchor_set  # noqa: E402
from corpus_runner import AbsorptionField, physics_absorb_truth  # noqa: E402
from aurora_dimensional_systems import (  # noqa: E402
    CrystalProcessingSystem,
    ConceptSignal,
    EvolutionTracker,
)
from foundational_contract import ExistenceMode  # noqa: E402


class _FakeEnvelope:
    """Minimal stand-in: process_concepts() reads only .data and .mode
    (see tests/test_causal_generation_batch_order.py's identical helper)."""

    def __init__(self, data="occurrence"):
        self.data = data
        self.mode = ExistenceMode.PERSISTENT


# ============================================================================
# 1a. Critical regression -- OntologicalWeb relation-type selection
# ============================================================================

def _relation_types_by_pair(engine):
    """word-pair (order-normalized) -> relation_type.value, plus the
    committed self._selection_outcomes usage count for the one signature
    this scenario exercises -- both must be identical across orderings."""
    types = {
        frozenset((rel.source_word, rel.target_word)): rel.relation_type.value
        for rel in engine.web.relations.values()
    }
    uses = (
        engine.web._selection_outcomes.get("noun+noun", {})
        .get("instance_of", {})
        .get("uses")
    )
    return types, uses


def _run_relation_typing_batch(word_order):
    """One occurrence: 4 co-occurring nouns (adjacency loop never fires for
    same-role non-verb/adjective pairs, isolating the pairwise co-occurrence
    loop this fix targets). Pre-seeds failure history for signature
    "noun+noun"/instance_of right where MIN_USES(3) matters: pre-fix, the
    first pair scored bumps live uses from 2 to 3, so a LATER same-batch
    pair sees the discount engage and gets pushed to a different type
    entirely -- confirmed by direct reproduction against the pre-fix
    commit (e98d121) during this suite's development: pre-fix diverged
    (first pair "instance_of", rest "has_a", differing by word order);
    post-fix all pairs agree regardless of order."""
    engine = OntologicalScaffoldingEngine()
    for w in ("a", "b", "c", "d"):
        engine.web.add_node(w, "noun")
    engine.web._selection_outcomes["noun+noun"] = {
        "instance_of": {"uses": 2, "failures": 2}
    }
    engine.web.infer_relations_from_context(list(word_order))
    return _relation_types_by_pair(engine)


def test_relation_typing_batch_order_independent():
    forward = _run_relation_typing_batch(["a", "b", "c", "d"])
    backward = _run_relation_typing_batch(["d", "c", "b", "a"])
    shuffled = _run_relation_typing_batch(["c", "a", "d", "b"])

    assert forward == backward == shuffled
    # Not a vacuous pass: every pair actually agrees on a real type, and
    # the discount genuinely didn't engage (uses stayed below the live
    # 3-per-signature threshold within this batch, same as scoring against
    # a frozen pre-batch snapshot would give).
    types, uses = forward
    assert types, "fixture produced no relations to compare"
    assert all(t == "instance_of" for t in types.values())
    assert uses == 8  # 2 seeded + 6 pairs (C(4,2)) scored once each


# ============================================================================
# 1b. Critical regression -- relevance anchor-set one-hop folding
# ============================================================================

class _FakeRelation:
    def __init__(self, source_word, target_word, strength,
                 source_of_knowledge="research"):
        self.source_word = source_word
        self.target_word = target_word
        self.strength = strength
        self.source_of_knowledge = source_of_knowledge


class _FakeOETS:
    def __init__(self, nodes, relations_by_word):
        self.nodes = nodes
        self._relations_by_word = relations_by_word

    def get_all_relations_for(self, word):
        return self._relations_by_word.get(word, [])


def _run_anchor_set(alpha_strength, beta_strength):
    """Two direct anchors from one turn ("alpha", "beta") share a one-hop
    neighbor ("gamma") at two different relation strengths. Python's set
    iteration order for these exact strings is NOT controlled by which
    word appears first in the input text (direct_from_text is a `set()`)
    -- confirmed live during this suite's development that "alpha" always
    iterates before "beta" in this interpreter regardless of text order,
    which is exactly why the pre-fix bug needs BOTH strength assignments
    tested here (varying which one is the max) rather than varying word
    order in the text: pre-fix, gamma's score deterministically came from
    whichever anchor's hash happened to iterate first, not from whichever
    contributed the higher strength."""
    nodes = {"alpha": True, "beta": True, "gamma": True}
    relations = {
        "alpha": [_FakeRelation("alpha", "gamma", alpha_strength)],
        "beta": [_FakeRelation("beta", "gamma", beta_strength)],
    }
    oets = _FakeOETS(nodes, relations)
    return build_relevance_anchor_set("alpha beta", None, oets)


def test_anchor_set_one_hop_score_is_true_max_regardless_of_which_anchor_is_larger():
    higher_first = _run_anchor_set(0.9, 0.3)
    higher_second = _run_anchor_set(0.3, 0.9)

    assert higher_first["gamma"] == 0.9
    assert higher_second["gamma"] == 0.9  # not 0.3 -- the pre-fix failure mode


# ============================================================================
# 1c. Critical regression -- corpus absorption WARP gap-persistence check
# ============================================================================

class _FakeLexicon:
    def add_word(self, word, meaning="", role="", valence=0.0, lineage=""):
        pass

    def associate(self, word, channel, strength=0.0):
        pass


class _FakePerception:
    def __init__(self):
        self.lexicon = _FakeLexicon()


class _SpyDPS:
    """Stands in for CrystalProcessingSystem here -- only check_and_extend
    is exercised by physics_absorb_truth()'s SURFACE-depth branch."""

    def __init__(self):
        self.calls = []

    def check_and_extend(self, profile, source=""):
        self.calls.append(dict(profile))
        return None


class _FakeDimensional:
    def __init__(self, dps):
        self.dps = dps


class _FakeIdentityField:
    def status(self):
        return {"axis_pressures": {"X": 0.5, "T": 0.5, "N": 0.5, "B": 0.5, "A": 0.5}}


def _run_absorption(text):
    dps = _SpyDPS()
    systems = {
        "perception": _FakePerception(),
        "dimensional": _FakeDimensional(dps),
        "identity_field": _FakeIdentityField(),
    }
    geom = physics_absorb_truth(systems, AbsorptionField(), text, context_hash="ctx")
    return geom, dps.calls


def test_absorb_truth_checks_coverage_gap_once_per_occurrence_not_per_word():
    """This sentence has >=10 non-stopword words and clears the >0.05 axis
    activation gate (confirmed live: X~0.29, N~0.59), so pre-fix this
    called check_and_extend() once per word -- up to 10 times -- against
    check_and_extend()'s own shared, self-clearing gap_counter, letting one
    sentence satisfy the "persist across separate occurrences" requirement
    check_and_extend() itself documents. Post-fix: exactly once."""
    text = "this is absolutely the most urgent critical emergency situation possible"
    geom, calls = _run_absorption(text)

    from corpus_runner import StratigraphicDepth
    assert geom.depth == StratigraphicDepth.SURFACE, (
        "fixture must land in the per-word SURFACE branch to be meaningful"
    )
    assert len(calls) == 1, (
        f"expected exactly one occurrence-level coverage check, got {len(calls)}"
    )


def test_absorb_truth_gap_check_count_is_stable_across_word_order():
    """The same words in a different order must still produce exactly one
    check -- the fix hoists the check out of the per-word loop entirely,
    so it cannot depend on how many words happen to be in the batch."""
    forward = "this is absolutely the most urgent critical emergency situation"
    reordered = "situation emergency critical urgent most the absolutely is this"

    _, calls_forward = _run_absorption(forward)
    _, calls_reordered = _run_absorption(reordered)

    assert len(calls_forward) == len(calls_reordered) == 1


# ============================================================================
# 4. Self-extension -- new participant joins a generation without modifying
#    the producer; an unrelated participant is left alone.
# ============================================================================

def test_self_extension_new_participant_joins_without_modifying_process_concepts():
    """Occurrence 1 seeds three crystals: alpha/beta (structurally related
    to each other) and an unrelated third crystal on unrelated axes.
    Occurrence 2 introduces a brand-new concept ("gamma", structurally
    related to alpha/beta) through the SAME, unmodified process_concepts()
    -- no new code path, no special-casing of gamma. Confirms: (a) gamma
    becomes a real participant in the resonance graph (its own joint
    reconciliation runs), (b) existing participants alpha/beta are not
    disrupted (their own joint reconciliation does NOT re-run just because
    a related concept arrived later), and (c) the unrelated crystal is
    never touched just because it exists in the registry."""
    dps = CrystalProcessingSystem(EvolutionTracker())

    occurrence_1 = [
        ConceptSignal("alpha", "topic", 0.9, {"X": 1.0, "N": 0.0}),
        ConceptSignal("beta", "entity", 0.8, {"X": 0.9, "N": 0.1}),
        ConceptSignal("unrelated", "topic", 0.5, {"B": 1.0, "A": 0.0}),
    ]
    dps.process_concepts(_FakeEnvelope(), occurrence_1)
    alpha_id = dps.concept_index["alpha"]
    beta_id = dps.concept_index["beta"]
    unrelated_id = dps.concept_index["unrelated"]

    joint_calls = []
    real_update_links = dps._update_crystal_links

    def _spy(crystal_id, *args, **kwargs):
        joint_calls.append(crystal_id)
        return real_update_links(crystal_id, *args, **kwargs)

    dps._update_crystal_links = _spy  # observe Pass 2 without changing it

    occurrence_2 = [
        ConceptSignal("gamma", "topic", 0.85, {"X": 0.95, "N": 0.05}),
    ]
    dps.process_concepts(_FakeEnvelope(), occurrence_2)
    gamma_id = dps.concept_index["gamma"]

    # (a) the new participant is valid: it exists and has resonance links.
    assert gamma_id in dps.crystals
    assert dps.crystal_links.get(gamma_id), (
        "new participant should have found structurally related neighbors"
    )

    # (b) existing participants are not disrupted by the later occurrence.
    assert alpha_id not in joint_calls
    assert beta_id not in joint_calls

    # (c) an unrelated participant is not processed just because it exists.
    assert unrelated_id not in joint_calls

    # Only the new participant's own generation was reconciled.
    assert joint_calls == [gamma_id]


# ============================================================================
# Phase 4 note (not a test): why categories 2/3 stay N/A rather than built
# ============================================================================
#
# Phase 1's full-codebase sweep (see the commit history on this branch)
# found exactly five confirmed causal-generation defects total, across
# every keyword-triaged candidate file in the repository -- all five fully
# contained within a single function's own batch loop, in a single
# subsystem, using the batch's own existing list as the causal-generation
# boundary. None required cross-subsystem wavefront propagation, none
# needed a generalized-applicability router, and none showed any measured
# benefit from concurrent execution (none of the fixes introduced
# threading -- the directive explicitly forbids that "merely to correct
# causal semantics"). Per the directive, Phase 4 "completes only the
# machinery justified by the dependency map and repaired production
# cases" -- the evidence gathered across Phases 0-2 does not justify
# building wavefront/applicability/hardware-adaptive machinery now.
# Building it speculatively would be exactly the "giant scheduler
# prematurely" the directive repeatedly warns against. If a future Phase 2
# batch finds a genuinely cross-subsystem instance, or real measurement
# shows overlap would benefit the phone runtime, that evidence is what
# would justify extending CausalGeneration (Phase 3) rather than starting
# from here.

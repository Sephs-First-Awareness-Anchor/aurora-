# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Directive NC1: noncomp_id population + honest relation-type completion.

Covers:
  - Fix A: noncomp_id round-trips through OETSPersistence.save_web()/
    load_web() (regression guard for the persistence gap that silently
    dropped it every save/load cycle -- 0/1104 live nodes carried one).
  - Fix B: OntologicalWeb.add_node() assigns the ratified role->axis
    noncomp_id for each of the 7 mapped roles, and None for an unmapped
    role (e.g. "training_gap") -- never fabricated.
  - Fix C: infer_relations_from_context()'s exhaustive pairwise loop
    assigns ENABLES for a verb/noun pair, CONTEXT_OF for an adjective/
    noun pair, and RELATED_TO for any other role combination, for both
    orderings of each pair (the loop is order-independent).
"""
import os
import shutil
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_internal.aurora_identity_persistence import OETSPersistence  # noqa: E402
from aurora_internal.aurora_ontological_scaffolding import (  # noqa: E402
    OntologicalScaffoldingEngine,
    ROLE_TO_AXIS,
    RelationType,
    _noncomp_id_for_role,
)
from aurora_internal.aurora_noncomp_registry import AXIS_NC_DIM  # noqa: E402


def _persist(scratch):
    """Same isolated-fixture pattern as test_ps1_2_persistence_arbitration.py:
    redirect primary_web_file into the scratch dir so this test never
    touches the real repo-root file."""
    state_dir = os.path.join(scratch, "aurora_state")
    os.makedirs(state_dir, exist_ok=True)
    persist = OETSPersistence(state_dir=state_dir)
    fake_primary = os.path.join(scratch, "primary_aurora_oets_web.json")
    persist.primary_web_file = type(persist.primary_web_file)(fake_primary)
    persist.web_file = persist.primary_web_file
    persist._isolated = False
    return persist


# ---- Fix A: persistence round-trip ----------------------------------------

def test_noncomp_id_round_trips_through_save_load():
    scratch = tempfile.mkdtemp(prefix="nc1_persist_")
    try:
        persist = _persist(scratch)

        engine = OntologicalScaffoldingEngine()
        node = engine.web.add_node("grow", "verb")
        assert node.noncomp_id == "T:DIFFERENCE"

        assert persist.save_web(engine)

        engine2 = OntologicalScaffoldingEngine()
        assert persist.load_web(engine2)
        assert "grow" in engine2.web.nodes
        assert engine2.web.nodes["grow"].noncomp_id == "T:DIFFERENCE"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_noncomp_id_none_round_trips_as_none():
    scratch = tempfile.mkdtemp(prefix="nc1_persist_none_")
    try:
        persist = _persist(scratch)

        engine = OntologicalScaffoldingEngine()
        node = engine.web.add_node("hmm", "training_gap")
        assert node.noncomp_id is None

        assert persist.save_web(engine)

        engine2 = OntologicalScaffoldingEngine()
        assert persist.load_web(engine2)
        assert engine2.web.nodes["hmm"].noncomp_id is None
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


# ---- Fix B: add_node() role -> noncomp_id ----------------------------------

def test_add_node_assigns_correct_noncomp_id_per_mapped_role():
    engine = OntologicalScaffoldingEngine()
    for role, axis in ROLE_TO_AXIS.items():
        word = f"probe_{role}"
        node = engine.web.add_node(word, role)
        assert node.noncomp_id == f"{axis}:{AXIS_NC_DIM[axis]}", role


def test_add_node_leaves_noncomp_id_none_for_unmapped_role():
    engine = OntologicalScaffoldingEngine()
    node = engine.web.add_node("probe_unmapped", "training_gap")
    assert node.noncomp_id is None


def test_noncomp_id_for_role_helper_matches_add_node():
    for role in ROLE_TO_AXIS:
        assert _noncomp_id_for_role(role) is not None
    assert _noncomp_id_for_role("training_gap") is None
    assert _noncomp_id_for_role("") is None


# ---- Fix C: infer_relations_from_context() role-pair typing ---------------

def test_verb_noun_pair_becomes_enables_both_orderings():
    engine = OntologicalScaffoldingEngine()
    engine.web.add_node("grow", "verb")
    engine.web.add_node("garden", "noun")
    engine.web.infer_relations_from_context(["grow", "garden"])
    rel_id = engine.web._find_existing_relation("grow", "garden", RelationType.ENABLES)
    assert rel_id is not None
    assert engine.web.relations[rel_id].relation_type == RelationType.ENABLES

    engine2 = OntologicalScaffoldingEngine()
    engine2.web.add_node("garden", "noun")
    engine2.web.add_node("grow", "verb")
    engine2.web.infer_relations_from_context(["garden", "grow"])
    rel_id2 = engine2.web._find_existing_relation("garden", "grow", RelationType.ENABLES)
    assert rel_id2 is not None
    assert engine2.web.relations[rel_id2].relation_type == RelationType.ENABLES


def test_adjective_noun_pair_becomes_context_of_both_orderings():
    engine = OntologicalScaffoldingEngine()
    engine.web.add_node("gentle", "adjective")
    engine.web.add_node("care", "noun")
    engine.web.infer_relations_from_context(["gentle", "care"])
    rel_id = engine.web._find_existing_relation("gentle", "care", RelationType.CONTEXT_OF)
    assert rel_id is not None
    assert engine.web.relations[rel_id].relation_type == RelationType.CONTEXT_OF

    engine2 = OntologicalScaffoldingEngine()
    engine2.web.add_node("care", "noun")
    engine2.web.add_node("gentle", "adjective")
    engine2.web.infer_relations_from_context(["care", "gentle"])
    rel_id2 = engine2.web._find_existing_relation("care", "gentle", RelationType.CONTEXT_OF)
    assert rel_id2 is not None
    assert engine2.web.relations[rel_id2].relation_type == RelationType.CONTEXT_OF


def test_other_role_combination_stays_related_to():
    engine = OntologicalScaffoldingEngine()
    engine.web.add_node("rain", "noun")
    engine.web.add_node("cloud", "noun")
    engine.web.infer_relations_from_context(["rain", "cloud"])
    rel_id = engine.web._find_existing_relation("rain", "cloud", RelationType.RELATED_TO)
    assert rel_id is not None
    assert engine.web.relations[rel_id].relation_type == RelationType.RELATED_TO


def test_adjacency_loop_still_runs_after_pairwise_loop():
    """The pairwise loop above (Fix C) must not replace the existing
    adjacency loop below it -- both still run, and add_relation's
    existing-relation-strengthen path means a pair caught by both loops
    just strengthens the same relation rather than erroring."""
    engine = OntologicalScaffoldingEngine()
    engine.web.add_node("grow", "verb")
    engine.web.add_node("garden", "noun")
    engine.web.infer_relations_from_context(["grow", "garden"])
    rel_id = engine.web._find_existing_relation("grow", "garden", RelationType.ENABLES)
    assert rel_id is not None
    # The pairwise loop (Fix C) creates this ENABLES relation at its base
    # strength (0.2); the adjacency loop below it then finds it already
    # exists and strengthens it via add_relation's existing-relation path
    # (rel.strength + 0.3*0.2 = 0.26) rather than erroring or being
    # skipped -- confirming both loops actually ran on this pair.
    assert engine.web.relations[rel_id].strength > 0.2

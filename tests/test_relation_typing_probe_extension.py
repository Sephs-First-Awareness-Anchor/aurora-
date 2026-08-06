# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Build 598: Relation-Typing Pressure Calibration (Relational Probe
Extension). Doctrine Level 7 (Provide a Trial Surface), depending on the
Build 598 Categorical Branch Primitive directive landing first (the
chamber can't compose a categorical rule from role-pair evidence until it
has the IFELSE vocabulary to express one).

DreamTrainer's existing relational-probe trial surface
(_build_relational_probe_specs / record_relational_probe_outcomes) was
scoped to conversational cause/effect demonstration, not to
OntologicalWeb's RelationType classification. This extends it to also
serve that purpose rather than building a second, parallel scenario
engine:

1. Dual-mode pair sourcing -- OntologicalWeb.underworked_relation_type_
   pairs() surfaces role-pair combinations the two ratified NC1
   heuristics (verb+noun, adjective+noun) don't already cover.
2. A new relation_typing_precision fail dimension, same pattern as the
   existing two.
3. Evidence submission -- when a probe's own reply is specific enough to
   confirm one RelationType (not just generic relational engagement),
   that (role_pair -> type) example is submitted to
   systems["operational_synthesis"].observe_example(). This is the
   evidence pipeline, not the rule -- the rule is hers to synthesize once
   fed enough varied, honest evidence.
"""
import os
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_dream_trainer import DIMENSION_AXIS, DreamTrainer
from aurora_internal.aurora_ontological_scaffolding import OntologicalWeb, RelationType


def _trainer():
    tmp = tempfile.mkdtemp(prefix="aurora_dream_trainer_relation_typing_test_")
    return DreamTrainer(state_dir=tmp)


def _web_with_pairs():
    web = OntologicalWeb()
    for word, role in (
        ("plans", "verb"), ("project", "noun"),      # NC1-covered: verb+noun
        ("careful", "adjective"), ("driver", "noun"), # NC1-covered: adjective+noun
        ("system", "noun"), ("outcome", "noun"),      # NOT covered: noun+noun
        ("quickly", "adverb"), ("moves", "verb"),     # NOT covered: adverb+verb
    ):
        web.add_node(word, role=role)
    web.add_relation("plans", "project", RelationType.ENABLES, knowledge_source="co-occurrence")
    web.add_relation("careful", "driver", RelationType.CONTEXT_OF, knowledge_source="co-occurrence")
    web.add_relation("system", "outcome", RelationType.RELATED_TO, knowledge_source="co-occurrence")
    web.add_relation("quickly", "moves", RelationType.RELATED_TO, knowledge_source="co-occurrence")
    return web


# ---------------------------------------------------------------------------
# OntologicalWeb.underworked_relation_type_pairs() -- read-only hook
# ---------------------------------------------------------------------------

def test_underworked_pairs_excludes_nc1_covered_role_combinations():
    web = _web_with_pairs()
    pairs = web.underworked_relation_type_pairs(limit=10)
    words = {(p["left"], p["right"]) for p in pairs}
    assert ("system", "outcome") in words
    assert ("quickly", "moves") in words
    assert ("plans", "project") not in words
    assert ("careful", "driver") not in words


def test_underworked_pairs_only_considers_related_to_co_occurrence():
    web = _web_with_pairs()
    # A non-co-occurrence RELATED_TO relation (e.g. from definition_analysis)
    # must not be treated as the honestly-untyped population this directive
    # targets -- it already has a deliberate knowledge source.
    web.add_node("gravity", "noun")
    web.add_node("mass", "noun")
    web.add_relation("gravity", "mass", RelationType.RELATED_TO, knowledge_source="definition_analysis")
    pairs = web.underworked_relation_type_pairs(limit=10)
    words = {(p["left"], p["right"]) for p in pairs}
    assert ("gravity", "mass") not in words


def test_underworked_pairs_reports_roles():
    web = _web_with_pairs()
    pairs = web.underworked_relation_type_pairs(limit=10)
    found = next(p for p in pairs if {p["left"], p["right"]} == {"system", "outcome"})
    assert {found["left_role"], found["right_role"]} == {"noun"}


# ---------------------------------------------------------------------------
# Dimension registry
# ---------------------------------------------------------------------------

def test_relation_typing_precision_dimension_registered_same_pattern_as_existing():
    assert "relation_typing_precision" in DIMENSION_AXIS
    assert DIMENSION_AXIS["relation_typing_precision"] in {"X", "T", "N", "B", "A"}


# ---------------------------------------------------------------------------
# Dual-mode pair sourcing in _build_relational_probe_specs()
# ---------------------------------------------------------------------------

def test_build_relational_probe_specs_draws_from_ontology_when_fail_dims_empty():
    trainer = _trainer()
    trainer._systems = {"perception": type("P", (), {"oets": type("O", (), {"web": _web_with_pairs()})()})()}
    specs = trainer._build_relational_probe_specs([], limit=2)
    assert specs
    assert all(spec["avatar_id"].startswith("rel_probe_") for spec in specs)
    assert all(spec["pressure_targets"].get("relation_typing_precision") for spec in specs)
    pair_words = set()
    for spec in specs:
        hint = next(h for h in spec["code_hints"] if h.startswith("[REL_PROBE] "))
        import json
        payload = json.loads(hint[len("[REL_PROBE] "):])
        pair_words.add((payload["left"], payload["right"]))
    assert pair_words <= {("system", "outcome"), ("quickly", "moves")}


def test_build_relational_probe_specs_fail_dim_pairs_still_take_priority():
    """Dual-mode is additive -- an existing fail-dimension-mined pair must
    still be produced exactly as before; the ontology source only fills in
    once that source is exhausted."""
    trainer = _trainer()
    trainer._systems = {"perception": type("P", (), {"oets": type("O", (), {"web": _web_with_pairs()})()})()}
    trainer.ledger.record_fail("semantic_precision", 0.8, example={
        "conversation_id": "conv1",
        "user_turns": ["Tell me about wolves and forests."],
        "assistant_turns": ["Wolves shape forests through predation pressure."],
    })
    specs = trainer._build_relational_probe_specs([("semantic_precision", 0.8)], limit=1)
    assert len(specs) == 1
    assert specs[0]["pressure_targets"].get("semantic_precision")


# ---------------------------------------------------------------------------
# _relation_type_probe_success(): confirms a SPECIFIC type from the reply,
# not just generic relational engagement.
# ---------------------------------------------------------------------------

def test_relation_type_probe_success_identifies_a_specific_type():
    trainer = _trainer()
    reply = (
        "System failures cause outcome delays because the pipeline "
        "triggers a cascading shutdown across every dependent stage."
    )
    result = trainer._relation_type_probe_success(
        reply, left="system", right="outcome", avg_fitness=0.8,
    )
    assert result == "causes"


def test_relation_type_probe_success_returns_none_without_a_specific_cue():
    trainer = _trainer()
    # Passes the generic _relational_probe_success bar (relates/connects
    # cues, both terms present, long enough, fit high enough) but uses no
    # cue specific to any one RelationType.
    reply = (
        "The system relates to the outcome and connects through several "
        "linked pathways that track together across the process."
    )
    assert trainer._relational_probe_success(reply, left="system", right="outcome", avg_fitness=0.8)
    result = trainer._relation_type_probe_success(
        reply, left="system", right="outcome", avg_fitness=0.8,
    )
    assert result is None


def test_relation_type_probe_success_returns_none_when_base_success_fails():
    trainer = _trainer()
    result = trainer._relation_type_probe_success(
        "too short", left="system", right="outcome", avg_fitness=0.8,
    )
    assert result is None


# ---------------------------------------------------------------------------
# record_relational_probe_outcomes(): evidence submission end to end, and
# the explicit non-write guarantee.
# ---------------------------------------------------------------------------

class _FakeOperationalSynthesis:
    def __init__(self):
        self.calls = []

    def observe_example(self, task_id, input_value, expected_output, **kwargs):
        self.calls.append({
            "task_id": task_id,
            "input_value": dict(input_value),
            "expected_output": expected_output,
            "kwargs": kwargs,
        })
        return {"accepted": True}


def _episode(spec_id, left, right, assistant_text, avg_fitness=0.8):
    from aurora_dream_trainer import _pack_relational_probe_hint
    return {
        "active_avatar_spec_id": spec_id,
        "active_avatar_code_hints": [_pack_relational_probe_hint(left, right, "conv1")],
        "conversation_trace": [
            {"user_text": f"How does {left} relate to {right}?", "assistant_text": assistant_text},
        ],
        "avg_fitness": avg_fitness,
    }


def test_record_relational_probe_outcomes_submits_typed_evidence():
    trainer = _trainer()
    web = _web_with_pairs()
    op_synth = _FakeOperationalSynthesis()
    systems = {
        "perception": type("P", (), {"oets": type("O", (), {"web": web})()})(),
        "operational_synthesis": op_synth,
    }
    episode = _episode(
        "rel_probe_system_outcome_0", "system", "outcome",
        "System failures cause outcome delays because the pipeline "
        "triggers a cascading shutdown across every dependent stage.",
    )
    trainer.record_relational_probe_outcomes(systems, [episode])

    assert len(op_synth.calls) == 1
    call = op_synth.calls[0]
    assert call["task_id"] == "relation_type_from_role_pair"
    assert call["input_value"] == {"source_role": "noun", "target_role": "noun"}
    assert call["expected_output"] == "causes"


def test_record_relational_probe_outcomes_does_not_submit_evidence_without_a_specific_type():
    trainer = _trainer()
    web = _web_with_pairs()
    op_synth = _FakeOperationalSynthesis()
    systems = {
        "perception": type("P", (), {"oets": type("O", (), {"web": web})()})(),
        "operational_synthesis": op_synth,
    }
    episode = _episode(
        "rel_probe_system_outcome_0", "system", "outcome",
        "The system relates to the outcome and connects through several "
        "linked pathways that track together across the process.",
    )
    trainer.record_relational_probe_outcomes(systems, [episode])
    assert op_synth.calls == []


def test_record_relational_probe_outcomes_never_writes_relation_type_or_noncomp_id():
    """Explicit non-bypass check per the directive: this pipeline only
    feeds evidence to the chamber, it never assigns a relation type or
    noncomp_id itself -- that would be a Level 10 violation smuggled into
    a Level 7 directive."""
    trainer = _trainer()
    web = _web_with_pairs()
    relation_count_before = len(web.relations)
    noncomp_ids_before = {w: n.noncomp_id for w, n in web.nodes.items()}
    op_synth = _FakeOperationalSynthesis()
    systems = {
        "perception": type("P", (), {"oets": type("O", (), {"web": web})()})(),
        "operational_synthesis": op_synth,
    }
    episode = _episode(
        "rel_probe_system_outcome_0", "system", "outcome",
        "System failures cause outcome delays because the pipeline "
        "triggers a cascading shutdown across every dependent stage.",
    )
    trainer.record_relational_probe_outcomes(systems, [episode])

    assert len(web.relations) == relation_count_before
    assert {w: n.noncomp_id for w, n in web.nodes.items()} == noncomp_ids_before


def test_record_relational_probe_outcomes_skips_evidence_when_role_unresolvable():
    """Roles are looked up from the live web at evidence time -- an
    unresolvable word (not in the web) must not submit malformed evidence."""
    trainer = _trainer()
    op_synth = _FakeOperationalSynthesis()
    systems = {
        "perception": type("P", (), {"oets": type("O", (), {"web": OntologicalWeb()})()})(),
        "operational_synthesis": op_synth,
    }
    episode = _episode(
        "rel_probe_ghost_word_0", "ghostword", "phantomword",
        "Ghostword causes phantomword delays because the pipeline "
        "triggers a cascading shutdown across every dependent stage.",
    )
    trainer.record_relational_probe_outcomes(systems, [episode])
    assert op_synth.calls == []

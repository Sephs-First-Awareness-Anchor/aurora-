# Authors: Sunni (Sir) Morningstar & Cael Devo
"""FIX-A143: an example stays an example on EVERY path she reads from, not only in the fact-question handler.

PR #251 review findings:
  P1  after "Suppose that Mara likes tea." the ordinary knowledge path (confluence.knowledge ->
      lexicalize_assertion) still voiced "mara likes tea" as an unqualified affirmative.
  P2  "Suppose that blorp is a noun." still re-roled the word (apply_kind ran for a supposed statement).

Both are tested through the paths she actually reads (confluence.knowledge, the learned-rule derive, the
shared lexicalizer, the integrate_turn entry) and by a before/after state diff around a supposition, so a
third leak of the same kind fails here too.
"""
from __future__ import annotations

import copy

import pytest

from aurora_internal import aurora_confluence as C
from aurora_internal import aurora_learned_rules as R
from aurora_internal import aurora_propositional_understanding as P
from aurora_internal.aurora_ontological_scaffolding import OntologicalWeb


def _web(lines=()):
    web = OntologicalWeb()
    for line in lines:
        for st in P.statements_in(line):
            P.integrate_form(web, st, heard=line, speaker="sunni", listener="aurora", profile={})
    return web


def _suppose(web, line, profile=None):
    m = P._SUPPOSE.match(line)
    assert m, line
    rest = line[m.end():]
    for st in P.statements_in(rest):
        P.integrate_form(web, st, heard=rest, speaker="sunni", listener="aurora", profile=profile or {},
                         basis="supposed")


def _systems(web):
    return {"oets": type("O", (), {"web": web})(), "perception": None}


def _known(web, concepts, question, reach=3):
    return C.knowledge(_systems(web), concepts, question, reach=reach, session_id="x")


def _spoken(items):
    return [(i["lex"]["agent"], i["lex"]["action"], i["lex"]["object"]) for i in items]


# -- P1: the shared lexicalizer and the ordinary knowledge path -----------------------------------

def test_the_shared_lexicalizer_never_voices_a_supposed_predicate_as_a_plain_fact():
    web = _web()
    _suppose(web, "Suppose that Mara likes tea.")
    rel = next(r for r in web.relations.values() if r.source_word == "mara")
    lex = P.lexicalize_assertion(rel, speaker_now="sunni", self_now="aurora")
    assert (lex["agent"], lex["action"], lex["object"]) == ("I", "only suppose", "that mara likes tea")
    assert lex["basis"] == "supposed"


def test_a_supposed_denial_is_voiced_as_a_supposed_denial():
    web = _web()
    _suppose(web, "Imagine that Teo does not like tea.")
    rel = next(r for r in web.relations.values() if r.source_word == "teo")
    lex = P.lexicalize_assertion(rel, speaker_now="sunni", self_now="aurora")
    assert (lex["action"], lex["object"]) == ("only suppose", "that teo does not like tea")


def test_the_ordinary_knowledge_path_qualifies_an_example_when_the_predicate_is_asked():
    web = _web()
    _suppose(web, "Suppose that Mara likes tea.")
    got = _known(web, ["mara"], "What does Mara like?")
    assert _spoken(got) == [("I", "only suppose", "that mara likes tea")]
    assert got[0]["basis"] == "supposed"
    assert got[0]["learned_from"] == "assertion"


def test_an_example_is_not_pulled_in_by_merely_naming_its_subject_or_object():
    web = _web()
    _suppose(web, "Suppose that Mara likes tea.")
    assert _known(web, ["mara"], "Who is Mara?") == []          # the predicate was not asked
    assert _known(web, ["tea"], "What is tea?") == []


def test_a_held_statement_beats_an_example_about_the_same_relation_and_both_stay_apart():
    web = _web(["Mara likes rain."])
    _suppose(web, "Suppose that Mara does not like rain.")
    got = _known(web, ["mara"], "What does Mara like?")
    assert _spoken(got) == [("mara", "likes", "rain")]           # the example does not even sit beside it
    assert "supposed" not in {i.get("basis") for i in got}


def test_the_example_about_another_predicate_does_not_borrow_the_held_ones_standing():
    web = _web(["Mara likes rain."])
    _suppose(web, "Suppose that Mara hates rain.")
    got = _known(web, ["mara"], "What does Mara hate?")
    assert _spoken(got)[0] == ("I", "only suppose", "that mara hates rain")     # what was asked, as an example
    assert ("mara", "likes", "rain") in _spoken(got)                              # what she holds is still held
    assert [i.get("basis") for i in got].count("supposed") == 1
    like = _known(web, ["mara"], "What does Mara like?")
    assert _spoken(like)[0] == ("mara", "likes", "rain")


def test_the_fact_question_handler_and_the_ordinary_path_agree():
    web = _web()
    _suppose(web, "Suppose that Mara likes tea.")
    via_rules = _spoken(R.derive(web, "Does Mara like tea?", speaker_now="sunni", self_now="aurora"))
    assert via_rules == [("I", "only suppose", "that mara likes tea")]


def test_the_integrate_turn_entry_keeps_a_cued_turn_supposed_end_to_end():
    web = _web()
    systems = _systems(web)
    systems["_last_pipeline_state"] = {}
    P.integrate_turn(systems, "Suppose that Mara likes tea.", session_id="x")
    rel = next(r for r in web.relations.values() if r.source_word == "mara")
    assert P.standing(rel, "like")["verdict"] == "supposed"
    got = C.knowledge(systems, ["mara"], "What does Mara like?", reach=3, session_id="x")
    assert _spoken(got) == [("I", "only suppose", "that mara likes tea")]


# -- P2: a supposed kind does not change what a word is ---------------------------------------------

def test_a_supposed_classification_does_not_change_a_words_role():
    web = _web(["Blorp is a verb."])
    node = web.nodes["blorp"]
    assert node.role == "verb"
    _suppose(web, "Suppose that blorp is a noun.")
    assert web.nodes["blorp"].role == "verb"
    assert "blorp" in web._nodes_by_role["verb"] and "blorp" not in web._nodes_by_role["noun"]
    assert R.kind_edges(web).get(("blorp", "noun")) is None


def test_a_told_classification_still_changes_the_role():
    web = _web(["Blorp is a verb."])
    assert web.nodes["blorp"].role == "verb"
    web2 = _web(["Blorp is a noun."])
    assert web2.nodes["blorp"].role == "noun"


# -- the state diff: nothing she HOLDS moves when an example is heard --------------------------------

def _held_snapshot(web, relation_pairs):
    """Everything a held statement could move, for the relations that existed before."""
    out = {"roles": {w: n.role for w, n in web.nodes.items()},
           "role_index": {r: sorted(ws) for r, ws in web._nodes_by_role.items()}}
    out["_words"] = set(web.nodes)
    for pair in relation_pairs:
        rel = next(r for r in web.relations.values() if (r.source_word, r.target_word) == pair)
        a = copy.deepcopy(dict(rel.assertion or {}))
        out[pair] = {"strength": rel.strength, "confidence": rel.confidence,
                     "source": rel.source_of_knowledge, "assertion": a}
    return out


def test_hearing_an_example_about_a_held_relation_moves_nothing_she_holds():
    web = _web(["Mara likes rain.", "Blorp is a verb."])
    node_before = {w: (n.axis_samples, dict(n.axis_profile or {})) for w, n in web.nodes.items()}
    before = _held_snapshot(web, [("mara", "rain"), ("blorp", "verb")])
    _suppose(web, "Suppose that Mara does not like rain.", profile={"X": 0.9, "T": 0.1})
    _suppose(web, "Suppose that blorp is a noun.", profile={"X": 0.9, "T": 0.1})
    after = _held_snapshot(web, [("mara", "rain"), ("blorp", "verb")])
    for pair in (("mara", "rain"), ("blorp", "verb")):
        b, a = before[pair], after[pair]
        assert a["strength"] == b["strength"] and a["confidence"] == b["confidence"]
        assert a["source"] == b["source"]
        # relation-level counters and the held predicate's own counts are untouched
        for key in ("n", "by", "times", "profile", "contexts"):
            assert a["assertion"].get(key) == b["assertion"].get(key), key
        for pred, p in b["assertion"]["predicates"].items():
            q = a["assertion"]["predicates"][pred]
            for key in ("n", "denied", "modal", "settled", "history", "basis"):
                assert q.get(key) == p.get(key), (pred, key)
    # a word that existed keeps its role and its place in the role index (a new word an example names
    # exists as any heard word does; it is not what is being compared)
    existed = before["_words"]
    assert {w: r for w, r in after["roles"].items() if w in existed} == before["roles"]
    assert {r: [w for w in ws if w in existed] for r, ws in after["role_index"].items()} == \
           {r: [w for w in ws if w in existed] for r, ws in before["role_index"].items()}
    # where a concept lives in her space is moved by what she holds, not by an example
    for w, (samples, prof) in node_before.items():
        assert (web.nodes[w].axis_samples, dict(web.nodes[w].axis_profile or {})) == (samples, prof), w


def test_an_example_that_creates_a_relation_creates_only_the_honest_weak_link():
    web = _web()
    _suppose(web, "Suppose that Mara likes tea.")
    rel = next(r for r in web.relations.values() if r.source_word == "mara")
    assert rel.source_of_knowledge == "co-occurrence"           # not "assertion": nothing was asserted
    a = dict(rel.assertion)
    assert a.get("n", 0) == 0 and not a.get("by") and not a.get("contexts")
    p = a["predicates"]["like"]
    assert p["n"] == 0 and p["supposed"] == 1
    assert P.standing(rel, "like")["held"] is False


def test_an_example_gives_the_learned_rules_nothing_to_reason_from():
    web = _web()
    _suppose(web, "Suppose that the letter b comes after a.")
    _suppose(web, "Suppose that b is a letter.")
    assert R.order_edges(web) == {}
    assert R.kind_edges(web) == {}
    assert R.contradictions(web) == []
    assert R.rules(web) == []

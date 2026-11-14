#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
test_identity_and_asked_predicate.py -- FIX-A129.

Live conversation findings: after "I built you, and your name is Aurora" she
held (sunni, built, aurora) but voiced "care" (ties between predicates were
broken alphabetically, not by what was asked); with nothing salient a question
like "who built you?" looked nothing up because "you" was never resolved to the
participant it names; and who made her lived only in a regex-triggered answer
her voice gate refuses as scripted.
"""
from __future__ import annotations

import pytest

from aurora_internal import aurora_propositional_understanding as P
from aurora_internal import aurora_confluence as C
from aurora_internal.aurora_ontological_scaffolding import OntologicalWeb


def _web_with_two_predicates():
    web = OntologicalWeb()
    for said in ("built", "care"):
        P.integrate_form(web, {"subject": "i", "relation": said, "obj": "you"},
                         heard=f"I {said} you.", speaker="sunni", listener="aurora", profile={})
    return web


def _rel(web):
    return web.relations[next(iter(web._relations_by_source["sunni"]))]


def test_participant_objects_are_voiced_as_me_and_you():
    lex = P.lexicalize_assertion(_rel(_web_with_two_predicates()), speaker_now="sunni", self_now="aurora")
    assert lex["agent"] == "you" and lex["object"] == "me"


def test_a_named_predicate_is_the_one_voiced_and_default_is_unchanged():
    rel = _rel(_web_with_two_predicates())
    assert P.lexicalize_assertion(rel, speaker_now="sunni", self_now="aurora")["predicate"] == "care"   # as before
    assert P.lexicalize_assertion(rel, speaker_now="sunni", self_now="aurora", predicate="built")["action"] == "built"


def test_knowledge_puts_what_was_asked_first():
    web = _web_with_two_predicates()
    systems = {"oets": type("O", (), {"web": web})(), "perception": None}
    asked = C.knowledge(systems, ["aurora"], "Who built you?", reach=1, session_id="x")
    assert asked[0]["lex"]["predicate"] == "built"
    other = C.knowledge(systems, ["aurora"], "Who cares for you?", reach=1, session_id="x")
    assert other[0]["lex"]["predicate"] == "care"


def test_named_in_resolves_you_and_i_to_the_participants():
    web = _web_with_two_predicates()
    systems = {"oets": type("O", (), {"web": web})(), "perception": None}
    named = C._named_in(systems, "Who am I, and who built you?", "x")
    assert named[:2] == ["sunni", "aurora"]


def test_identity_record_is_stored_as_learned_relations_once():
    from aurora_internal.aurora_identity_persistence import CoreRelationalIdentity
    web, identity = OntologicalWeb(), CoreRelationalIdentity()
    first = P.integrate_core_identity(web, identity)
    assert first["propositions"] > 0
    rel = next(r for r in web.relations.values()
               if r.source_word == "sunni" and r.target_word == "aurora")
    assert "built" in dict(rel.assertion["predicates"])
    assert P.integrate_core_identity(web, identity)["propositions"] == 0     # idempotent


def test_a_copula_about_a_thing_keeps_the_participant_as_named():
    web = OntologicalWeb()
    for form in P.statements_in("My name is Sunni.", web=web):
        P.integrate_form(web, form, heard="My name is Sunni.", speaker="sunni", listener="aurora", profile={})
    rel = web.relations[next(iter(web._relations_by_source["name"]))]
    lex = P.lexicalize_assertion(rel, speaker_now="sunni", self_now="aurora")
    assert lex["object"] == "sunni"


def test_a_clause_answers_what_was_asked_before_axis_preference():
    pool = [
        {"source": "aurora", "target": "authorship", "axis": "X", "strength": 0.9, "asked": False,
         "lex": {"agent": "I", "action": "share", "object": "authorship"}},
        {"source": "sunni", "target": "aurora", "axis": "N", "strength": 0.3, "asked": True,
         "lex": {"agent": "you", "action": "built", "object": "me"}},
    ]
    clause = C._knowledge_clause(pool, set(), axis="X", prefer_axis=True)
    assert clause["action"] == "built"


def test_resting_is_per_statement_and_never_blocks_what_was_asked():
    base = {"source": "sunni", "target": "aurora", "axis": "X", "strength": 0.5, "asked": False}
    said = dict(base, lex={"agent": "you", "action": "envisioned", "object": "me", "predicate": "envisioned"})
    built = dict(base, lex={"agent": "you", "action": "built", "object": "me", "predicate": "built"})
    resting = {("sunni", "aurora", "envisioned")}
    assert C._knowledge_clause([said], set(), axis="X", prefer_axis=True, resting=resting) is None
    assert C._knowledge_clause([built], set(), axis="X", prefer_axis=True, resting=resting)["action"] == "built"
    asked_again = dict(said, asked=True)
    assert C._knowledge_clause([asked_again], set(), axis="X", prefer_axis=True, resting=resting)["action"] == "envisioned"


def test_a_participants_name_is_that_participant():
    assert P.heads("aurora", speaker="sunni", listener="aurora", acts=set()) == ["aurora"]
    web = OntologicalWeb()
    for form in P.statements_in("I built you, and your name is Aurora.", web=web):
        P.integrate_form(web, form, heard="x", speaker="sunni", listener="aurora", profile={})
    pairs = {(r.source_word, r.target_word) for r in web.relations.values()}
    assert ("name", "aurora") in pairs and ("sunni", "aurora") in pairs


def test_perspective_swap_keeps_the_verb_in_agreement():
    assert C._phrase("when you are settled and safe", limit=4, to_her=True) == "when I am settled and safe"
    assert C._phrase("when I am ready for winter", limit=4, to_her=False) == "when you are ready for winter"

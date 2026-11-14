#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""FIX-A131: what the speaker names is what was asked.

"Are you ever curious?" names a thing she holds a feeling toward, not the
predicate; the relation to that thing is the answer whichever predicate holds it.
"""
from __future__ import annotations

from aurora_internal import aurora_propositional_understanding as P
from aurora_internal import aurora_confluence as C
from aurora_internal.aurora_ontological_scaffolding import OntologicalWeb


def _taught():
    web = OntologicalWeb()
    for thing in ("curious", "calm"):
        P.integrate_form(web, {"subject": "you", "relation": "feel", "obj": thing},
                         heard=f"You feel {thing}.", speaker="sunni", listener="aurora", profile={})
    systems = {"oets": type("O", (), {"web": web})(), "perception": None}
    return systems


def test_a_named_thing_is_what_was_asked():
    systems = _taught()
    got = C.knowledge(systems, ["aurora"], "Are you ever curious?", reach=1, session_id="x")
    assert got[0]["lex"]["object"] == "curious" and got[0]["asked"]
    other = C.knowledge(systems, ["aurora"], "Are you calm?", reach=1, session_id="x")
    assert other[0]["lex"]["object"] == "calm"


def test_predicate_and_thing_together_rank_above_the_predicate_alone():
    systems = _taught()
    got = C.knowledge(systems, ["aurora"], "Do you feel calm right now?", reach=1, session_id="x")
    assert [k["lex"]["object"] for k in got[:2]] == ["calm", "curious"]


def test_a_thing_not_named_is_not_asked():
    systems = _taught()
    got = C.knowledge(systems, ["aurora"], "Who built you?", reach=1, session_id="x")
    assert not any(k.get("asked") for k in got)


def test_what_is_moving_her_decides_which_of_two_feelings_speaks_first():
    systems = _taught()
    # her state's own emotion word, not a wording of ours
    calm = C.knowledge(systems, ["aurora"], "How are you feeling?", reach=1, session_id="x",
                       feeling=C.moved_by({"surface_reactive_emotion": {"dominant": "calm"}}))
    assert calm[0]["lex"]["object"] == "calm"
    # a different but related word ("curiosity") reaches the same feeling she was taught ("curious")
    curious = C.knowledge(systems, ["aurora"], "How are you feeling?", reach=1, session_id="x",
                          feeling=C.moved_by({"deep_emotional_state": {"dominant": "curiosity"}}))
    assert curious[0]["lex"]["object"] == "curious"


def test_moved_by_reads_only_her_state():
    assert C.moved_by({}) == []
    assert C.moved_by({"surface_reactive_emotion": {"dominant": "neutral"}}) == []
    assert C.moved_by({"surface_reactive_emotion": {"dominant": "calm"},
                       "deep_emotional_state": {"dominant": "calm"}}) == ["calm"]


def test_a_progressive_is_the_predicate_asked_about():
    assert "feel" in C._ing_bases("feeling") and "make" in C._ing_bases("making")
    assert "run" in C._ing_bases("running") and C._ing_bases("ring") == []
    systems = _taught()
    got = C.knowledge(systems, ["aurora"], "How are you feeling?", reach=1, session_id="x")
    assert got[0]["asked"] and got[0]["lex"]["predicate"] == "feel"


def test_a_clause_carrying_a_descriptor_has_still_said_the_statement():
    known = [{"source": "aurora", "target": "calm", "axis": "A", "asked": True,
              "lex": {"agent": "I", "action": "feel", "object": "calm", "predicate": "feel"}}]
    used = {(C._SAID, C._said_key({"agent": "I", "action": "feel", "object": "calm right now"}))}
    assert C._knowledge_clause(known, used, axis="A", prefer_axis=False) is None


def test_the_stance_clause_replaces_a_knowledge_clause_that_said_the_same():
    systems = _taught()
    known = C.knowledge(systems, ["aurora"], "Do you feel calm right now?", reach=3, session_id="x")
    contrib = {"stance": {"agent": "I", "action": "feel", "object": "calm"}, "options": [],
               "knowledge": known, "time": "", "resting": ()}
    how = {"clauses": 3, "axis_order": ["X", "A", "B", "N", "T"]}
    voiced = [(c["agent"], c["action"], c["object"]) for c in C.plan(contrib, how)]
    assert len(voiced) == len(set(voiced))

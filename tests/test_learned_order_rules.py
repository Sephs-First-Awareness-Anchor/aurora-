# Authors: Sunni (Sir) Morningstar & Cael Devo
"""FIX-A133 (phase 1, letters): a learned statement takes effect in what she can work out.

Everything here is taught the way she learns: as sentences through her own
statement parser.  The module under test reads only her learned relations.
"""
from __future__ import annotations

import pytest

from aurora_internal import aurora_confluence as C
from aurora_internal import aurora_learned_rules as R
from aurora_internal import aurora_propositional_understanding as P
from aurora_internal.aurora_ontological_scaffolding import OntologicalWeb

LESSON = ["The letter b comes after the letter a.", "The letter c comes after the letter b.",
          "The letter d follows the letter c."]


def _taught(lines=LESSON):
    web = OntologicalWeb()
    for line in lines:
        for st in P.statements_in(line):
            P.integrate_form(web, st, heard=line, speaker="sunni", listener="aurora", profile={})
    return web


def test_letters_and_order_phrases_are_read_as_statements():
    assert P.statements_in("B follows A.")[0]["relation"] == "follows"
    st = P.statements_in("The letter b comes after the letter a.")[0]
    assert (st["subject"], st["obj"], st["particle"]) == ("the letter b", "the letter a", "after")
    # the verb forms of her tagger can be the act of a statement
    assert P.statements_in("Rain causes growth.")[0]["relation"] == "causes"
    # "after" in front of its own clause is still a clause
    assert [s["subject"] for s in P.statements_in("I left after he cried.")] == ["i", "he"]


def test_the_letter_is_what_the_statement_is_about():
    web = _taught(LESSON[:1])
    rels = [(r.source_word, r.target_word) for r in web.relations.values() if getattr(r, "assertion", None)]
    assert rels == [("b", "a")]
    assert dict(next(iter(web.relations.values())).assertion["predicates"]).keys() == {"come after"}


def test_order_is_chained_from_what_she_was_told():
    web = _taught()
    reach = R.later_than(R.order_edges(web), "a")
    assert list(reach) == ["b", "c", "d"] and reach["d"] == ["a", "b", "c", "d"]


@pytest.mark.parametrize("question,agent,action,obj", [
    ("What comes after b?", "c", "comes after", "b"),
    ("What follows c?", "d", "comes after", "c"),
    ("What letter comes before d?", "c", "comes before", "d"),
    ("Is d after a?", "d", "is after", "a"),
    ("Does c follow b?", "c", "is after", "b"),
    ("Is a after d?", "a", "is not after", "d"),
])
def test_questions_are_answered_from_chained_order(question, agent, action, obj):
    got = R.derive(_taught(), question)
    assert [(i["lex"]["agent"], i["lex"]["action"], i["lex"]["object"]) for i in got] == [(agent, action, obj)]
    assert got[0]["derived"] and got[0]["learned_from"] == "inference"


def test_she_says_nothing_about_order_she_was_not_told():
    web = _taught()
    assert R.derive(web, "Is c after z?") == [] and R.derive(web, "What comes after d?") == []
    assert R.derive(OntologicalWeb(), "What comes after b?") == []
    assert R.derive(web, "What is a letter?") == []


def test_a_denied_order_is_not_held():
    web = OntologicalWeb()
    for line in ("The letter b comes after the letter a.", "The letter b does not come after the letter a."):
        for st in P.statements_in(line):
            P.integrate_form(web, st, heard=line, speaker="sunni", listener="aurora", profile={})
    assert R.order_edges(web) == {}


def test_the_confluence_composes_the_answer_in_her_own_composer(monkeypatch):
    web = _taught()
    systems = {"oets": type("O", (), {"web": web})(), "perception": None}
    known = C.knowledge(systems, ["aurora"], "What comes after b?", reach=2, session_id="x")
    assert known[0]["derived"] and known[0]["lex"]["agent"] == "c"


def test_a_new_letter_in_the_answer_is_not_an_echo():
    import aurora_voice_gate as G
    assert G.parrot_reason("C comes after b.", "What comes after b?") == ""
    assert G.parrot_reason("You feel calm when you are settled.", "You feel calm when you are settled.") == "echo"

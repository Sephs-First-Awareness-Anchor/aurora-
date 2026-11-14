# Authors: Sunni (Sir) Morningstar & Cael Devo
"""FIX-A134: a word she was taught that names a capability she owns is answered by using it.

Taught as sentences through her own parser; the module reads only what she holds
and her own tool registry.  A question may run read-only capabilities only.
"""
from __future__ import annotations

import pytest

from aurora_internal import aurora_capability_binding as B
from aurora_internal import aurora_confluence as C
from aurora_internal import aurora_propositional_understanding as P
from aurora_internal import tool_registry as T
from aurora_internal.aurora_ontological_scaffolding import OntologicalWeb

SEE = "You see with your visual analysis."
HEAR = "You hear through your audio analysis."


def _told(*lines):
    web = OntologicalWeb()
    for line in lines:
        for st in P.statements_in(line):
            P.integrate_form(web, st, heard=line, speaker="sunni", listener="aurora", profile={})
    return web


class _Camera:
    def capture_visual(self):
        return {"brightness": 0.5, "objects": ["cup", "lamp"], "faces": [], "motion_detected": False}

    def capture_audio(self, duration=0.5):
        return {"category": "speech", "volume": 0.4}


def _out(items):
    return [(i["lex"]["action"], i["lex"]["object"], i["lex"]["denied"]) for i in items]


def test_nothing_is_bound_until_she_is_taught():
    assert B.bindings(_told("You feel curious.")) == {}
    assert B.derive({"hardware": _Camera()}, _told("You feel curious."), "What can you see?") == []


def test_a_taught_word_reaches_the_capability_its_words_name():
    web = _told(SEE, HEAR)
    assert B.bindings(web) == {"see": ["visual_analysis"], "hear": ["audio_analysis"]}


def test_a_second_predicate_said_along_an_old_pair_is_still_heard():
    web = _told(SEE, HEAR)                      # "analysis" was already a word when the second was said
    rel = next(r for r in web.relations.values() if r.target_word == "analysis")
    assert "see" in rel.assertion["predicates"]
    assert "analysis" in web.relations[next(k for k, r in web.relations.items() if r.target_word == "audio")] \
        .assertion["predicates"]["hear"]["said_with"]


@pytest.mark.parametrize("q", ["What can you see?", "Can you see?", "What do you see?", "Are you seeing anything?"])
def test_a_question_to_her_runs_the_sense_and_she_says_what_it_found(q):
    got = B.derive({"hardware": _Camera()}, _told(SEE), q)
    assert _out(got) == [("see", "cup", "False"), ("see", "lamp", "False")]
    assert all(i["learned_from"] == "capability" for i in got)


def test_when_the_sense_has_nothing_she_says_she_does_not_see():
    assert _out(B.derive({"hardware": None}, _told(SEE), "What can you see?")) == [("do not see", "", "True")]


def test_the_lesson_is_not_a_question_and_a_question_not_to_her_is_not_either():
    web = _told(SEE)
    assert B.derive({"hardware": _Camera()}, web, SEE) == []
    assert B.derive({"hardware": _Camera()}, web, "What does he see?") == []
    assert B.derive({"hardware": _Camera()}, web, "What can you hear?") == []        # hear was never taught


def test_hearing_is_a_different_capability():
    assert _out(B.derive({"hardware": _Camera()}, _told(SEE, HEAR), "Can you hear?")) == [("hear", "speech", "False")]


def test_a_question_never_runs_something_that_acts_on_the_world(monkeypatch):
    ran = []
    real = T.call
    monkeypatch.setattr(T, "call", lambda name, **kw: (ran.append(name), real(name, **kw))[1])
    web = _told("You text with your mobile send sms.", "You run with your desktop shell command.")
    held = B.bindings(web)
    assert "mobile_send_sms" in held.get("text", []) and "desktop_shell_command" in held.get("run", [])
    assert B.derive({}, web, "Can you text?") == []
    assert B.derive({}, web, "Can you run?") == []
    assert ran == []
    assert not B.allowed("mobile_send_sms") and not B.allowed("desktop_shell_command")
    assert B.allowed("visual_analysis") and B.allowed("query_crystal_state")


def test_it_reaches_the_voice_through_her_knowledge():
    web = _told(SEE)
    systems = {"hardware": _Camera(), "oets": type("O", (), {"web": web})(), "perception": None}
    known = C.knowledge(systems, ["aurora"], "What can you see?", reach=2, session_id="x")
    assert [k["lex"]["object"] for k in known if k.get("learned_from") == "capability"] == ["cup", "lamp"]


def test_the_gate_knows_when_what_she_was_taught_can_answer():
    import aurora_voice_gate as G
    web = _told(SEE, "When I greet you, you say hello.")
    systems = {"oets": type("O", (), {"web": web})(), "perception": None}
    assert G._worked_out(systems, "What can you see?") and G._worked_out(systems, "I greet you today.")
    assert not G._worked_out(systems, "It rained.")
    assert not G._worked_out({"oets": type("O", (), {"web": _told("You feel curious.")})()}, "What can you see?")

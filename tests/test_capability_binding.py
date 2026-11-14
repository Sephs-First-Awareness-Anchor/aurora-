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


def test_no_feed_an_empty_look_and_a_failed_attempt_are_three_different_things(monkeypatch):
    web = _told(SEE)
    ask = lambda hw: B.derive({"hardware": hw}, web, "What can you see?")
    assert [(i["lex"]["action"], i["lex"]["object"], i["outcome"]) for i in ask(None)] == [("cannot see", "", "unavailable")]
    class Empty:
        def capture_visual(self):
            return {"brightness": 0.5, "objects": [], "faces": [], "motion_detected": False}
    assert [(i["lex"]["action"], i["lex"]["object"], i["outcome"]) for i in ask(Empty())] == [("see", "nothing", "empty")]
    monkeypatch.setattr(T, "call", lambda name, **kw: T.ToolResult(name, "", False, "camera driver crashed"))
    assert [(i["lex"]["action"], i["outcome"]) for i in ask(_Camera())] == [("could not see", "failed")]


def test_how_her_sensing_has_gone_is_kept():
    systems = {"hardware": None}
    B.derive(systems, _told(SEE), "What can you see?")
    assert systems["_capability_outcomes"][-1]["outcome"] == "unavailable"


def test_one_observation_serves_every_question_in_the_same_moment(monkeypatch):
    calls = []
    real = T.call
    monkeypatch.setattr(T, "call", lambda name, **kw: (calls.append(name), real(name, **kw))[1])
    systems = {"hardware": _Camera()}
    web = _told(SEE)
    B.derive(systems, web, "What can you see?")
    B.derive(systems, web, "Can you see anything?")
    assert calls == ["visual_analysis"]


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
    assert G._worked_out(systems, "What can you see?")
    assert G._worked_out(systems, "I greet you today.", "sunni")
    assert not G._worked_out(systems, "It rained.")
    assert not G._worked_out({"oets": type("O", (), {"web": _told("You feel curious.")})()}, "What can you see?")


# -- the other capabilities she can be taught to name (FIX-A134, part 2) ------------

def _fake(monkeypatch, data, ok=True):
    monkeypatch.setattr(T, "call", lambda name, **kw: T.ToolResult(name, data, ok))


@pytest.mark.parametrize("teach,question,data,expected", [
    ("You feel with your self state.", "What do you feel?",
     "heat: 0.20; coherence: 0.62; stagnation: 0.10; camera: active", ["coherence", "stagnation", "heat", "camera"]),
    ("You remember with your memory read.", "What do you remember?",
     "active oets concepts: rain, rig", ["rain", "rig"]),
    ("You tell time with your time.", "Can you tell the time?",
     "Current date and time: Saturday, November 14 2026 — 06:36 AM", ["saturday", "november"]),
])
def test_what_a_report_says_is_voiced_in_her_taught_word(monkeypatch, teach, question, data, expected):
    _fake(monkeypatch, data)
    got = B.derive({}, _told(teach), question)
    assert sorted(i["lex"]["object"] for i in got) == sorted(expected[:len(got)]) and got
    assert {i["lex"]["action"] for i in got} == {teach.split()[1]}


def test_a_report_with_nothing_in_it_is_a_do_not(monkeypatch):
    _fake(monkeypatch, "", ok=False)
    assert _out(B.derive({}, _told("You feel with your self state."), "What do you feel?")) == [("cannot feel", "", "True")]


# -- one resolution, many consumers (FIX-A135) -------------------------------------

def test_what_she_was_told_is_resolved_once_and_shared():
    from aurora_internal import aurora_learned_index as X
    from aurora_internal import aurora_learned_rules as R
    web = _told(SEE, "When I greet you, you say hello.", "B comes after a.")
    for _ in range(3):
        B.bindings(web); R.rules(web); R.order_edges(web)
    base = dict(X.STATS)
    for _ in range(25):                                   # gate check, knowledge, answer ... all the same resolution
        B.bindings(web); B.answerable(web, "What can you see?"); R.rules(web); R.order_edges(web)
        R.derive(web, "What comes after a?", speaker_now="sunni", self_now="aurora")
    assert X.STATS["built"] - base["built"] <= 1          # only the one new question, built once
    assert X.STATS["reused"] - base["reused"] >= 25 * 4


def test_the_resolution_is_rebuilt_only_when_what_she_knows_changes():
    from aurora_internal import aurora_learned_rules as R
    web = _told("B comes after a.")
    assert R.later_than(R.order_edges(web), "a") == {"b": ["a", "b"]} or "b" in R.later_than(R.order_edges(web), "a")
    before = R.order_edges(web)
    assert R.order_edges(web) is before                   # same object: nothing rebuilt
    for st in P.statements_in("C comes after b."):
        P.integrate_form(web, st, heard="C comes after b.", speaker="sunni", listener="aurora", profile={})
    after = R.order_edges(web)
    assert after is not before and ("b", "c") in after    # a new statement was recorded: refreshed


def test_a_derived_answer_cannot_be_changed_by_a_consumer():
    from aurora_internal import aurora_learned_rules as R
    web = _told("B comes after a.")
    first = R.derive(web, "What comes after a?", speaker_now="sunni", self_now="aurora")
    first[0]["lex"]["object"] = "corrupted"
    again = R.derive(web, "What comes after a?", speaker_now="sunni", self_now="aurora")
    assert again[0]["lex"]["object"] == "a"


def test_what_she_saw_is_kept_as_observed_where_she_keeps_what_she_was_told():
    web = _told(SEE)
    B.derive({"hardware": _Camera()}, web, "What can you see?")
    cup = next(r for r in web.relations.values() if r.source_word == "aurora" and r.target_word == "cup")
    assert dict(cup.assertion["predicates"]["see"]["basis"]) == {"observed": 1}
    B.derive({"hardware": None}, web, "What can you see?")                   # nothing seen: nothing is recorded
    assert dict(cup.assertion["predicates"]["see"]["basis"]) == {"observed": 1}

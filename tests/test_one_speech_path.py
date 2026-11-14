# Authors: Sunni (Sir) Morningstar & Cael Devo
"""FIX-A130: the generative reply and the confluence are one speech path.

The confluence composes first, from everything that touched the turn, whenever
she would speak at all; the reasoning pipeline's reply (or her composer's draft)
stands only when the confluence has nothing.  Nothing here supplies words: the
confluence is stubbed to return whatever the test says it composed.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import aurora_voice_gate as G  # noqa: E402
from aurora_internal import aurora_confluence as C  # noqa: E402

HEARD = "How are you feeling?"


def _reply(text="I am energy. I understand cost.", src="generative"):
    return SimpleNamespace(content=text, src=src, emotional_tone="curious", confidence=0.6)


def _stub_confluence(monkeypatch, text, calls=None):
    def compose(systems, heard, *, session_id=""):
        if calls is not None:
            calls.append(heard)
        return text, {"why": "" if text else "nothing", "how": {"abilities": []}}
    monkeypatch.setattr(C, "compose", compose)
    monkeypatch.setattr(C, "put_on_grammar_trace", lambda systems, rec: None)


def test_a_standing_generative_reply_gives_way_to_the_confluence(monkeypatch):
    _stub_confluence(monkeypatch, "I feel calm when I am settled and safe.")
    systems = {}
    out = G.apply_voice_gate(systems, _reply(), HEARD, session_id="phone")
    assert out.src == "confluence" and out.content.startswith("I feel calm")
    assert systems["_last_voice_gate"]["outcome"] == "confluence"


def test_no_pressure_threshold_stands_between_a_standing_reply_and_its_composition(monkeypatch):
    # pressure decides whether she speaks, not what an outgoing reply is made of
    _stub_confluence(monkeypatch, "I feel calm.")
    systems = {}
    out = G.apply_voice_gate(systems, _reply(), "Hello", session_id="phone")
    assert systems["_last_voice_gate"]["pressure"] < G.ARTICULATION_THRESHOLD
    assert out.src == "confluence"


def test_generative_reply_stands_when_the_confluence_has_nothing(monkeypatch):
    calls = []
    _stub_confluence(monkeypatch, "", calls)
    reply = _reply()
    systems = {}
    out = G.apply_voice_gate(systems, reply, HEARD, session_id="phone")
    assert out is reply and systems["_last_voice_gate"]["outcome"] == "own_voice"
    assert calls == [HEARD]                      # tried once, not twice


def test_confluence_goes_before_her_composer_draft_when_the_reply_is_blocked(monkeypatch):
    _stub_confluence(monkeypatch, "You built me.")
    heard = "Who built you?"
    systems = {"_turn_composer_candidate": {"text": "I feel built you. You create built you.",
                                            "heard": heard, "confidence": 0.8, "tone": "curious"}}
    out = G.apply_voice_gate(systems, _reply("What do you mean by 'built'?", "constraint_seek"),
                             heard, session_id="phone", render=lambda *a, **k: "")
    assert out.src == "confluence" and out.content == "You built me."
    assert systems["_last_voice_gate"]["blocked"].startswith("scripted_source")


def test_composer_draft_stands_when_the_confluence_has_nothing(monkeypatch):
    calls = []
    _stub_confluence(monkeypatch, "", calls)
    heard = "Do you like music?"
    systems = {"_turn_composer_candidate": {"text": "You do music. I understand music.",
                                            "heard": heard, "confidence": 0.8, "tone": "curious"}}
    out = G.apply_voice_gate(systems, _reply("What do you mean by 'music'?", "constraint_seek"),
                             heard, session_id="phone", render=lambda *a, **k: "")
    assert out.src == "composer_unified" and calls == [heard]


def test_flag_off_restores_generative_first(monkeypatch):
    _stub_confluence(monkeypatch, "I feel calm.")
    monkeypatch.setattr(G, "CONFLUENCE_FIRST", False)
    reply = _reply()
    out = G.apply_voice_gate({}, reply, HEARD, session_id="phone")
    assert out is reply


def test_a_statement_already_voiced_is_not_voiced_twice():
    known = [{"source": "aurora", "target": "curious", "axis": "A", "asked": True,
              "lex": {"agent": "I", "action": "feel", "object": "curious", "predicate": "feel"}},
             {"source": "aurora", "target": "calm", "axis": "A", "asked": True,
              "lex": {"agent": "I", "action": "feel", "object": "calm", "predicate": "feel"}}]
    used = {(C._SAID, C._said_key({"agent": "I", "action": "feel", "object": "curious"}))}
    clause = C._knowledge_clause(known, used, axis="A", prefer_axis=False)
    assert clause["object"] == "calm"
    # and what a knowledge clause voices is remembered the same way
    again = C._knowledge_clause(known, used, axis="A", prefer_axis=False)
    assert again is None

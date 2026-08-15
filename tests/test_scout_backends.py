#!/usr/bin/env python3
"""Build 711 model-free, human-observation Scout backend regression coverage."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aurora_internal.scouting.backends import (
    ScoutBackend,
    LocalHumanDialogueBackend,
    PublicHumanDialogueBackend,
    LocalLessonsBackend,
    PublicWebBackend,
    TestBackend,
    resolve_backend_chain,
    DEFAULT_BACKEND_NAMES,
)
from aurora_internal.scouting.contracts import ScoutRequest


def test_default_chain_is_model_free_and_retrieval_only():
    assert DEFAULT_BACKEND_NAMES == (
        "public_human_dialogue", "local_human_dialogue", "public_web", "local_lessons"
    )
    assert [b.name for b in resolve_backend_chain()] == list(DEFAULT_BACKEND_NAMES)


def test_local_lessons_backend_is_available_and_knowledge_only(tmp_path):
    (tmp_path / "poedex_lessons.json").write_text(json.dumps([
        {"question": "define chord theory basics", "lesson": "Chord theory studies how notes combine into harmony."},
    ]), encoding="utf-8")
    backend = LocalLessonsBackend()
    assert backend.is_available() is True
    kreq = ScoutRequest(turn_id="t1", request_kind="knowledge_gap", inquiry="chord theory basics explained")
    assert "harmony" in backend.retrieve(kreq, state_dir=tmp_path)
    rreq = ScoutRequest(turn_id="t1", request_kind="response_fit", inquiry="friendly greeting", interpreted_input="friendly greeting")
    assert backend.retrieve(rreq, state_dir=tmp_path) == ""


def test_local_human_dialogue_backend_requires_explicit_human_provenance(tmp_path):
    (tmp_path / "human_dialogue_pairs.json").write_text(json.dumps([
        {"user": "hey there", "assistant": "AI-looking legacy pair"},
        {"human_observed": True, "observed_input": "hey there", "observed_response": "Hey! Good to see you."},
    ]), encoding="utf-8")
    backend = LocalHumanDialogueBackend()
    req = ScoutRequest(turn_id="t1", request_kind="response_fit", interpreted_input="hey there", inquiry="response evidence")
    text = backend.retrieve(req, state_dir=tmp_path)
    assert "observed_input: hey there" in text
    assert "observed_response: Hey! Good to see you." in text
    assert "AI-looking legacy pair" not in text
    assert "acknowledge" not in text.lower()
    assert "why_fit" not in text.lower()


def test_public_human_dialogue_backend_returns_raw_public_reply_pairs(monkeypatch, tmp_path):
    search_payload = {
        "data": {"children": [{"data": {
            "title": "A friendly social approach",
            "selftext": "Someone said hello to me.",
            "permalink": "/r/test/comments/abc/example/",
            "subreddit": "test",
        }}]}
    }
    thread_payload = [
        {"data": {"children": []}},
        {"data": {"children": [{"data": {"author": "ordinary_human", "body": "I said hi back."}}]}},
    ]
    calls = []
    def fake_fetch(url, timeout=6.0):
        calls.append(url)
        return search_payload if "search.json" in url else thread_payload
    monkeypatch.setattr(PublicHumanDialogueBackend, "_fetch_json", staticmethod(fake_fetch))
    backend = PublicHumanDialogueBackend()
    req = ScoutRequest(
        turn_id="t1", request_kind="response_fit",
        interpreted_input="friendly social approach", inquiry="retrieve comparable observations",
    )
    text = backend.retrieve(req, state_dir=tmp_path)
    assert "RETRIEVED PUBLIC HUMAN DIALOGUE" in text
    assert "observed_input: A friendly social approach" in text
    assert "observed_response: I said hi back." in text
    assert "source=reddit/test" in text
    assert calls


def test_public_human_dialogue_backend_filters_obvious_bots(monkeypatch, tmp_path):
    search_payload = {"data": {"children": [{"data": {
        "title": "hello", "selftext": "", "permalink": "/r/test/comments/abc/example/", "subreddit": "test",
    }}]}}
    thread_payload = [
        {"data": {"children": []}},
        {"data": {"children": [
            {"data": {"author": "AutoModerator", "body": "automated"}},
            {"data": {"author": "helpful_bot", "body": "automated too"}},
            {"data": {"author": "person123", "body": "hello there"}},
        ]}},
    ]
    monkeypatch.setattr(
        PublicHumanDialogueBackend, "_fetch_json",
        staticmethod(lambda url, timeout=6.0: search_payload if "search.json" in url else thread_payload),
    )
    text = PublicHumanDialogueBackend().retrieve(
        ScoutRequest(turn_id="t1", request_kind="response_fit", interpreted_input="hello"),
        state_dir=tmp_path,
    )
    assert "hello there" in text
    assert "automated" not in text


def test_public_web_backend_rejects_response_fit(tmp_path):
    backend = PublicWebBackend()
    req = ScoutRequest(turn_id="t1", request_kind="response_fit", interpreted_input="friendly greeting", inquiry="response evidence")
    assert backend.retrieve(req, state_dir=tmp_path) == ""


def test_public_web_backend_can_retrieve_knowledge(monkeypatch, tmp_path):
    calls = []
    def fake_fetch(url, timeout=6.0):
        calls.append(url)
        return [{"meanings": [{"partOfSpeech": "noun", "definitions": [{"definition": "a greeting used when meeting someone"}]}]}]
    monkeypatch.setattr(PublicWebBackend, "_fetch_json", staticmethod(fake_fetch))
    backend = PublicWebBackend()
    req = ScoutRequest(turn_id="t1", request_kind="knowledge_gap", inquiry="hello", evidence_needed="hello")
    assert "greeting" in backend.retrieve(req, state_dir=tmp_path)
    assert calls


def test_test_backend_is_deterministic_fixture_only(tmp_path):
    backend = TestBackend(canned_result="raw observation")
    assert backend.retrieve(ScoutRequest(turn_id="t1", inquiry="anything"), state_dir=tmp_path) == "raw observation"
    assert backend.is_available()


def test_resolve_backend_chain_respects_explicit_names(monkeypatch):
    chain = resolve_backend_chain(["local_lessons"])
    assert len(chain) == 1 and isinstance(chain[0], LocalLessonsBackend)
    monkeypatch.setenv("SCOUT_BACKENDS", "public_human_dialogue,local_human_dialogue,local_lessons,test")
    assert [b.name for b in resolve_backend_chain()] == [
        "public_human_dialogue", "local_human_dialogue", "local_lessons", "test"
    ]


def test_unknown_backend_names_cannot_enable_a_model():
    names = [b.name for b in resolve_backend_chain(["gemini_rest", "remote_model", "openai", "local_lessons"])]
    assert names == ["local_lessons"]


def test_scout_backend_base_methods_are_abstract():
    import pytest
    backend = ScoutBackend()
    with pytest.raises(NotImplementedError):
        backend.is_available()
    with pytest.raises(NotImplementedError):
        backend.retrieve(ScoutRequest(turn_id="t1"), state_dir="/tmp")

#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Rehearsal of her history (Sunni, 2026-11-08): on each of Sunni's historical
messages she takes a real turn; the real reply is compared with hers and the
result enters the same verdict fan-out a live receiver's verdict does."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "flutter_app/android/app/src/main/python"))

import aurora_historical_experience_environment as H  # noqa: E402


class Contract:
    def __init__(self):
        self.state = {"pending_validation": {}, "pending_validation_by_session": {}}
        self.activated = []

    def snapshot(self):
        return {"pending_validation": dict(self.state["pending_validation"])}

    def _activate_session_pending(self, session):
        self.activated.append(session)


class FakeAurora:
    def __init__(self, systems, replies):
        self.systems, self.replies, self.turns, self.finalized = systems, list(replies), [], []

    def process_external_user_turn(self, systems, text, **kw):
        self.turns.append((text, kw))
        reply = self.replies.pop(0)
        systems["understanding_contract"].state["pending_validation"] = (
            {"response_id": f"U:{len(self.turns)}", "session_id": kw["session_id"], "contributors": {}}
            if reply else {})
        systems["_last_pipeline_state"] = {"relational_form": {"subject": "you", "relation": "like",
                                                               "obj": "music", "raw_text": text}}
        return {"resp_A": SimpleNamespace(content=reply)}

    def _finalize_validated_communication(self, systems, observation, user_text, *, session_id=""):
        self.finalized.append((observation, session_id))
        label = observation["accuracy"]["label"]
        return {"outcome_kind": "positive" if label == "rehearsal_match" else "negative"}


def env_with(replies):
    systems = {"understanding_contract": Contract()}
    fake = FakeAurora(systems, replies)
    systems["aurora_module"] = fake
    env = object.__new__(H.HistoricalExperienceEnvironment)
    env.systems = systems
    env.rehearse = True
    env._rehearsal = None
    env.rehearsal_counters = {"rehearsed": 0, "silent": 0, "compared": 0, "match": 0,
                              "partial": 0, "mismatch": 0, "fanned_out": 0, "errors": 0}
    env.last_rehearsal = {}
    return env, fake, systems


def ev(actor, text, episode="E1", eid="e"):
    return {"actor": actor, "text": text, "episode_id": episode, "event_id": eid}


def test_she_rehearses_then_learns_from_the_real_reply():
    env, fake, systems = env_with(["I like music. Music moves me."])
    env._rehearse(ev("historical_other_assistant", "Do you like music?"), "historical_other_assistant", "E1", True)
    assert fake.turns[0][0] == "Do you like music?"
    kw = fake.turns[0][1]
    assert kw["session_id"] == "rehearsal_E1" and kw["record_exchange"] is False
    out = env._rehearse(ev("historical_user", "I love music, it moves me deeply."),
                        "historical_user", "E1", False)
    assert out["label"] == "rehearsal_match" and out["outcome"] == "positive"
    observation, session = fake.finalized[0]
    assert observation["validated_response"]["response_id"] == "U:1"
    assert observation["accuracy"]["score"] >= 0.80 and session == "rehearsal_E1"
    assert systems["understanding_contract"].state["pending_validation"] == {}
    assert env.rehearsal_counters["fanned_out"] == 1


def test_a_reply_that_goes_somewhere_else_is_a_mismatch():
    env, fake, _ = env_with(["Rain falls on stones."])
    env._rehearse(ev("historical_other_assistant", "Can you help me plan a birthday gift for my dad?"), "historical_other_assistant", "E1", True)
    out = env._rehearse(ev("historical_user", "Sure! How about a personalized fishing book?"),
                        "historical_user", "E1", False)
    assert out["label"] == "rehearsal_mismatch" and fake.finalized[0][0]["accuracy"]["label"] == "rehearsal_mismatch"


def test_silence_and_partial_never_reach_the_fan_out():
    env, fake, _ = env_with(["", "I like rivers and light."])
    env._rehearse(ev("historical_other_assistant", "Do you like music?"), "historical_other_assistant", "E1", True)
    env._rehearse(ev("historical_user", "Yes."), "historical_user", "E1", False)
    assert env.rehearsal_counters["silent"] == 1 and fake.finalized == []
    env._rehearse(ev("historical_other_assistant", "Do you like music?"), "historical_other_assistant", "E1", False)
    out = env._rehearse(ev("historical_user", "Light on rivers is lovely, though music is my thing."),
                        "historical_user", "E1", False)
    if out["label"] == "rehearsal_partial":
        assert fake.finalized == []


def test_the_next_historical_message_never_judges_her_rehearsed_reply():
    env, fake, systems = env_with(["I like music.", "I like rain."])
    env._rehearse(ev("historical_other_assistant", "Do you like music?"), "historical_other_assistant", "E1", True)
    # no assistant reply recorded before Sunni's next message: retire, never judge
    env._rehearse(ev("historical_other_assistant", "Do you like rain?"), "historical_other_assistant", "E1", False)
    assert "rehearsal_E1" in systems["understanding_contract"].activated
    assert fake.finalized == []
    # a new episode also retires a waiting rehearsal
    env._rehearsal = {"session": "rehearsal_E1", "reply": "r", "pending": {"response_id": "U:9"}}
    env._rehearse(ev("historical_user", "hello", episode="E2"), "historical_user", "E2", True)
    assert env._rehearsal is None and fake.finalized == []


def test_comparison_uses_words_and_uptake():
    form = {"subject": "you", "relation": "like", "obj": "music"}
    close = H.rehearsal_comparison("I like music.", "I really like music a lot!", form)
    far = H.rehearsal_comparison("Clouds drift.", "I really like music a lot!", form)
    assert close["score"] > far["score"] and "music" in close["shared"]
    assert far["label"] == "rehearsal_mismatch"


def test_silence_is_retired_at_once_and_zero_overlap_is_apart():
    env, fake, systems = env_with(["", "Clouds drift slowly."])
    env._rehearse(ev("historical_other_assistant", "Do you like music?"), "historical_other_assistant", "E1", True)
    assert systems["understanding_contract"].activated == ["rehearsal_E1"]
    assert systems["understanding_contract"].state["pending_validation"] == {}
    form = {"subject": "you", "relation": "like", "obj": "music"}
    assert H.rehearsal_comparison("I, like. music.", "Absolutely! Here is a fishing book idea.", form)["label"] \
        == "rehearsal_mismatch"


def test_she_rehearses_sunnis_side_not_the_other_assistants():
    assert H.REHEARSAL_HEARD_SIDE == "historical_other_assistant"
    assert H.REHEARSAL_REAL_SIDE == "historical_user"
    env, fake, systems = env_with(["I, like. music."])
    out = env._rehearse(ev("historical_user", "Do you like music?"), "historical_user", "E1", True)
    assert out == {} and fake.turns == []

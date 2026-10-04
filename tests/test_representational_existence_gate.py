"""Which doctrine governs which state of representational existence.

D2 Condition 2 (abstain when there is nothing to ground) and Build 769/770 (the
communicative baseline floor) govern different rungs of foundational_contract's
ExistenceMode ladder. Content that is off the ladder (no lexical description, no
ontological node -- WarpTrigger.MISSING_REPRESENTATION) gets the honest abstain;
content on the ladder keeps the baseline floor. These tests pin the classification;
test_d2_condition2_abstain_sanity pins the end-to-end abstain.
"""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import aurora as A  # noqa: E402


def _systems(unknown):
    det = SimpleNamespace(detect=lambda text, lexicon=None, oets=None: {"unknown_words": list(unknown)})
    return {"comprehension_gap_system": SimpleNamespace(detector=det), "perception": None}


def _state(topic, entities=()):
    return SimpleNamespace(parsed={"topic_words": list(topic), "entities": list(entities)})


def test_all_content_off_the_ladder_is_missing_representation():
    r = A._utterance_representational_state(
        _systems(["asdf", "qwerty", "zxcv"]), _state(["asdf", "qwerty", "zxcv"]), "asdf qwerty zxcv")
    assert r["state"] == "missing_representation" and r["off_ladder_ratio"] == 1.0


def test_mostly_invented_tokens_with_one_real_word_is_still_missing_representation():
    topic = ["zqxvornmal", "threbicultan", "fost", "yendrical", "mip"]
    r = A._utterance_representational_state(
        _systems(["zqxvornmal", "threbicultan", "fost", "yendrical"]), _state(topic, ["Zqxvornmal"]),
        "Zqxvornmal threbicultan fost yendrical mip?")
    assert r["state"] == "missing_representation" and r["off_ladder_ratio"] == 0.8


def test_one_coined_word_inside_grounded_content_stays_represented():
    r = A._utterance_representational_state(
        _systems(["zqxvornmal"]), _state(["friend", "zqxvornmal", "likes", "pizza"]),
        "My friend Zqxvornmal likes pizza")
    assert r["state"] == "represented" and r["off_ladder"] == ["zqxvornmal"]


def test_exactly_half_off_the_ladder_keeps_the_baseline():
    r = A._utterance_representational_state(_systems(["blorf"]), _state(["stable", "blorf"]), "stable blorf")
    assert r["state"] == "represented"  # the gate is strictly "more than half"


def test_known_content_and_bare_greeting_are_represented():
    assert A._utterance_representational_state(
        _systems([]), _state(["photosynthesis"]), "What is photosynthesis?")["state"] == "represented"
    assert A._utterance_representational_state(
        _systems([]), _state([], ["Hello"]), "Hello")["state"] == "represented"


def test_gate_fails_open_when_the_detector_is_unavailable():
    for systems in ({}, {"comprehension_gap_system": SimpleNamespace(detector=None)}, None):
        r = A._utterance_representational_state(systems, _state(["asdf"]), "asdf")
        assert r["state"] == "unmeasured"  # caller must behave exactly as before the gate existed


def test_gate_fails_open_when_the_detector_raises():
    def boom(*a, **k):
        raise RuntimeError("detector down")
    systems = {"comprehension_gap_system": SimpleNamespace(detector=SimpleNamespace(detect=boom)), "perception": None}
    assert A._utterance_representational_state(systems, _state(["asdf"]), "asdf")["state"] == "unmeasured"

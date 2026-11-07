#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""test_social_corroboration.py -- knowing by triangulation."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import aurora_social_corroboration as C  # noqa: E402
from aurora_internal.aurora_identity_persistence import ConversationMemory  # noqa: E402


class Ledger:
    def __init__(self):
        self.records = []

    def record(self, claim_a, claim_b, source_a="", source_b=""):
        self.records.append((claim_a, claim_b, source_a, source_b))


def form(subject, relation, obj, question=False):
    return {"subject": subject, "relation": relation, "obj": obj, "question": question}


@pytest.fixture()
def world(tmp_path):
    systems = {"conversation_memory": ConversationMemory(), "contradiction_ledger": Ledger()}
    return systems, C.SocialCorroboration(str(tmp_path))


def test_two_contacts_agreeing_makes_it_her_fact(world):
    systems, social = world
    first = social.observe(systems, "gemini", "Gemini", form("rain", "is", "water"), "Rain is water.")
    assert not first["corroborated"]
    second = social.observe(systems, "gemma", "Gemma", form("Rain", "is", "water"), "rain is water!")
    assert second["corroborated"]
    fact = systems["conversation_memory"].learned_facts[-1]
    assert fact["fact"] == "rain is water" and fact["source"] == "corroborated:Gemini, Gemma"
    assert fact["confidence"] == C.CORROBORATED_CONFIDENCE


def test_one_contact_repeating_itself_is_not_corroboration(world):
    systems, social = world
    for _ in range(3):
        out = social.observe(systems, "gemini", "Gemini", form("rain", "is", "water"), "Rain is water.")
    assert not out["corroborated"] and systems["conversation_memory"].learned_facts == []


def test_opposite_polarity_goes_to_the_contradiction_ledger(world):
    systems, social = world
    social.observe(systems, "gemini", "Gemini", form("the moon", "is", "made of rock"), "The moon is made of rock.")
    out = social.observe(systems, "gemma", "Gemma", form("the moon", "is not", "made of rock"),
                         "The moon is not made of rock.")
    assert out["contradiction"]
    claim_a, claim_b, src_a, src_b = systems["contradiction_ledger"].records[0]
    assert claim_a == "moon is made of rock" and claim_b == "moon is not made of rock"
    assert src_a.startswith("dm:gemini") and src_b.startswith("dm:gemma")
    # recorded once, not on every repeat
    social.observe(systems, "gptoss", "GPT-OSS", form("the moon", "is not", "made of rock"), "The moon isn't made of rock.")
    assert len(systems["contradiction_ledger"].records) == 1


def test_different_objects_are_not_a_contradiction(world):
    systems, social = world
    social.observe(systems, "gemini", "Gemini", form("rain", "is", "water"), "Rain is water.")
    social.observe(systems, "gemma", "Gemma", form("rain", "is", "wet"), "Rain is wet.")
    assert systems["contradiction_ledger"].records == []


@pytest.mark.parametrize("f,text", [
    (form("I", "like", "music"), "I like music."),
    (form("you", "are", "curious"), "You are curious."),
    (form("rain", "is", "water", question=True), "Is rain water?"),
    (form("", "is", "water"), "is water"),
])
def test_personal_statements_and_questions_are_not_world_claims(world, f, text):
    systems, social = world
    assert social.observe(systems, "gemini", "Gemini", f, text) == {"claim": None}


def test_survives_restart(tmp_path):
    systems = {"conversation_memory": ConversationMemory(), "contradiction_ledger": Ledger()}
    C.SocialCorroboration(str(tmp_path)).observe(systems, "gemini", "Gemini", form("rain", "is", "water"), "Rain is water.")
    again = C.SocialCorroboration(str(tmp_path))
    assert again.observe(systems, "gemma", "Gemma", form("rain", "is", "water"), "Rain is water.")["corroborated"]


def test_reads_every_sentence_with_her_own_parser(world):
    systems, social = world
    social.observe_message(systems, "gemini", "Gemini",
                           "So you mean real want music? The moon is made of rock.")
    out = social.observe_message(systems, "gemma", "Gemma",
                                 "Ha, good question! The moon is not made of rock.")
    assert any(o["contradiction"] for o in out)
    social.observe_message(systems, "gemini", "Gemini", "Lovely. Rain is water that falls from clouds.")
    out = social.observe_message(systems, "gemma", "Gemma", "Rain is water that falls from clouds, you know.")
    assert any(o["corroborated"] for o in out)

#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
test_relation_slot_evidence.py -- FIX-A122.

Which word holds the relation slot is the first thing Aurora binds about a
sentence; her stance, her obligation, her grounding gaps and what she records
as asserted all inherit it.  A suffix alone must not make a noun the relation.
"""
from __future__ import annotations

import pytest

from aurora_internal import aurora_constraint_semantic_continuity as csc
from aurora_internal.aurora_constraint_semantic_continuity import extract_relational_form


@pytest.mark.parametrize("sentence, subject, relation", [
    # a plural subject beside a listed verb is the subject
    ("The posts were rotten.", "posts", "were"),
    ("Dogs are so smart for sure!", "Dogs", "are"),
    ("Humans have done a lot of damage to the planet.", "Humans", "have"),
    # a word after an article or possessive stands where a noun stands
    ("My name is Sunni.", "My name", "is"),
    ("The dogs chased the cat.", "dogs", "chased"),
    ("The morning light fell on the wall.", "morning light", "fell"),
    # a bare -ing form is not finite: the slot after the subject pronoun holds
    ("I spent the morning fixing the fence behind the house.", "I", "spent"),
    ("I love building things.", "I", "love"),
    ("We met this evening near the river.", "We", "met"),
    ("I bought something at the store.", "I", "bought"),
])
def test_position_outranks_a_suffix_guess(sentence, subject, relation):
    form = extract_relational_form(sentence)
    assert (form["subject"], form["relation"]) == (subject, relation)


@pytest.mark.parametrize("sentence, relation", [
    # the first real verb of the main clause still wins over a later one
    ("I also learned that the guest house is bigger.", "learned"),
    ("It says Runtime Error and does not seem to be initialized.", "says"),
    ("Just feeling out some small forms of independence.", "feeling"),
    ("I really liked the building.", "liked"),
    # a demonstrative standing alone is a pronoun, not a noun introducer
    ("Does that mean he would call it a game?", "mean"),
    ("Glorp is blue.", "is"),
    ("Do you like music?", "like"),
    ("What makes rain fall?", "makes"),
])
def test_what_was_bound_correctly_stays_bound(sentence, relation):
    assert extract_relational_form(sentence)["relation"] == relation


def test_a_relation_she_earned_is_consulted_when_only_a_noun_guess_competes(monkeypatch):
    """Before FIX-A122 "keys" (a suffix guess in a nominal slot) counted as
    the scaffold having found a verb, so her own promoted role for "took" was
    never asked.  Her earned knowledge now decides."""
    assert extract_relational_form("She took the keys from the kitchen.")["relation"] == "keys"
    monkeypatch.setattr(csc, "_has_promoted_relation_role", lambda word: word == "took")
    # (a different sentence: relational forms are memoised per text within a turn)
    form = extract_relational_form("She took the keys from the hallway.")
    assert (form["subject"], form["relation"]) == ("She", "took")


def test_a_promoted_word_still_never_outranks_a_real_verb(monkeypatch):
    monkeypatch.setattr(csc, "_has_promoted_relation_role", lambda word: word == "glorp")
    assert extract_relational_form("Glorp is blue.")["relation"] == "is"


def test_no_sentence_loses_its_relation():
    """Sentences with no positional evidence fall back to the previous choice."""
    assert extract_relational_form("The birds sang before the storm.")["relation"] == "birds"

#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
test_produced_ingest_not_heard.py -- FIX-A126.

Her own articulation candidates (accepted or not) were ingested through
ingest_interaction as if the speaker had said them: vocabulary, expression
context, sentence-structure absorption and OETS examples/relations all learned
from her own drafts.  An interaction flagged produced=True keeps the perceive()
feedback channel and skips every learning-from-the-world step.  No wording,
class or rule is added; the only change is which events count as heard.
"""
from __future__ import annotations

import inspect

import pytest


class _Composer:
    def __init__(self):
        self.absorbed, self.contexts = [], []

    def absorb(self, text, tone="neutral"):
        self.absorbed.append(text)

    def set_context(self, words):
        self.contexts.append(list(words))


class _Oets:
    def __init__(self):
        self.seen = []

    def process_interaction(self, text, tone="neutral", i_state="i_is"):
        self.seen.append(text)


@pytest.fixture(scope="module")
def perception(tmp_path_factory):
    from aurora_expression_perception import ExpressionPerceptionEngine
    return ExpressionPerceptionEngine(state_dir=str(tmp_path_factory.mktemp("perception")))


def _wire(perception, monkeypatch):
    composer, oets = _Composer(), _Oets()
    monkeypatch.setattr(perception, "composer", composer)
    monkeypatch.setattr(perception, "oets", oets)
    return composer, oets


SPOKEN = "The posts were completely rotten behind the barn."


def test_heard_text_still_teaches_everything(perception, monkeypatch):
    composer, oets = _wire(perception, monkeypatch)
    perception.ingest_interaction({"input": SPOKEN}, mode="gateway")
    assert composer.absorbed == [SPOKEN]
    assert composer.contexts
    assert oets.seen == [SPOKEN]


def test_her_own_candidate_is_perceived_but_not_learned_from(perception, monkeypatch):
    composer, oets = _wire(perception, monkeypatch)
    lexicon_before = perception.lexicon.size
    perceived_before = perception.total_perceptions
    result = perception.ingest_interaction(
        {"input": "I am having consciousness. Zymurgical flibbertigibbets wander.",
         "produced": True,
         "features": {"articulation_accepted": 0.0, "pressure_relief": 0.1}},
        mode="gateway")
    assert perception.total_perceptions == perceived_before + 1   # feedback channel still runs
    assert composer.absorbed == [] and composer.contexts == []
    assert oets.seen == []
    assert perception.lexicon.size == lexicon_before
    assert "zymurgical" not in perception.lexicon.entries


def test_gateway_marks_its_articulation_feedback_as_produced():
    import aurora_governance_persistence_gateway as gateway
    source = inspect.getsource(gateway)
    start = source.index("'source': 'articulation_pressure_feedback'")
    assert "'produced': True" in source[start:start + 300]

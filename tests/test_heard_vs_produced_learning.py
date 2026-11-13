#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
test_heard_vs_produced_learning.py -- FIX-A123.

Hearing a sentence is not the same event as producing one.  Measured on live
turns before this fix: the speaker's sentence, recalled memories appended to
it, and Aurora's own unspoken drafts were each logged to her genealogy as
"expression completed", crediting the last motif SHE had used; and one
utterance was absorbed two or three times per turn.
"""
from __future__ import annotations

import pytest

from aurora_grammar_engine import GrammarEngine


class _Genealogy:
    """Records observe() calls; answers the few reads GrammarEngine makes."""

    def __init__(self):
        self.observed = []

    def observe(self, **kwargs):
        self.observed.append(kwargs)

    def __getattr__(self, name):          # pressure/orientation reads: nothing to report
        raise AttributeError(name)


def _engine(tmp_path):
    engine = GrammarEngine(str(tmp_path))
    genealogy = _Genealogy()
    engine.set_genealogy(genealogy)
    return engine, genealogy


def test_heard_language_teaches_structure_but_logs_no_production_relief(tmp_path):
    engine, genealogy = _engine(tmp_path)
    engine.observe_exchange("", "The dog runs very fast today.", success=True, produced=False)
    assert genealogy.observed == []                       # nobody's expression completed
    assert engine._lineage._motifs, "the heard structure still enters the motif lineage"


def test_her_own_production_still_logs_relief(tmp_path):
    engine, genealogy = _engine(tmp_path)
    engine.observe_exchange("what is the dog doing", "The dog runs very fast today.", success=True)
    assert len(genealogy.observed) == 1
    assert genealogy.observed[0]["notes"]["tag"] == "grammar_clarity"


def test_absorb_marks_text_as_heard(tmp_path):
    from aurora_expression_perception import LexicalMemory, SentenceComposer, VoiceGenome

    engine, genealogy = _engine(tmp_path)
    composer = SentenceComposer(LexicalMemory(), VoiceGenome())
    composer.grammar_engine = engine
    composer.absorb("I spent the morning fixing the fence behind the house.")
    assert engine._lineage._motifs
    assert genealogy.observed == []


class _Composer:
    def __init__(self):
        self.absorbed = []

    def absorb(self, text, tone="neutral"):
        self.absorbed.append(text)

    def set_context(self, words):
        pass


@pytest.fixture(scope="module")
def perception(tmp_path_factory):
    from aurora_expression_perception import ExpressionPerceptionEngine
    return ExpressionPerceptionEngine(state_dir=str(tmp_path_factory.mktemp("perception")))


def test_the_same_utterance_is_not_heard_twice_in_a_turn(perception, monkeypatch):
    spy = _Composer()
    monkeypatch.setattr(perception, "composer", spy)
    said = "I spent the morning fixing the fence behind the house."
    perception.ingest_interaction({"input": said}, mode="gateway")
    # the recall-enriched re-synthesis of the SAME turn input
    perception.ingest_interaction(
        {"input": said + "\n[recalled:fixing] I spent the morning fixing the fence behind the house.",
         "input_already_registered": True}, mode="gateway")
    # the post-reply persistent ingest of the same words
    perception.ingest_interaction({"input": said, "input_already_registered": True}, mode="persistent")
    assert spy.absorbed == [said]
    assert not any("[recalled:" in text for text in spy.absorbed)


def test_a_new_utterance_is_still_heard(perception, monkeypatch):
    spy = _Composer()
    monkeypatch.setattr(perception, "composer", spy)
    perception.ingest_interaction({"input": "The posts were completely rotten."}, mode="gateway")
    perception.ingest_interaction({"input": "It took longer than I expected."}, mode="gateway")
    assert len(spy.absorbed) == 2


def test_gateway_passes_the_callers_already_registered_contract():
    """Static: _synthesize hands perception the same flag the entropy stage reads."""
    import inspect
    import aurora_governance_persistence_gateway as gateway
    source = inspect.getsource(gateway)
    start = source.index("# L5: Perception pipeline")
    block = source[start:start + 900]
    assert "'input_already_registered'" in block
    assert 'extra_evidence.get("input_already_registered")' in block

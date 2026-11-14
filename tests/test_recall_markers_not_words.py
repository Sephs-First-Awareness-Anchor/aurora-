#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
test_recall_markers_not_words.py -- FIX-A128.

Measured on a live conversation: her ontological web held 149 distinct
"[recalled:<concept>]" tokens (nested forms too) as if they were words, each
related to every word it co-occurred with; five turns added four more.  The
marker is transport, not speech.
"""
from __future__ import annotations

import pytest

from aurora_expression_perception import strip_recall_markers


def test_marker_is_removed_and_the_remembered_content_stays():
    assert strip_recall_markers("It took long. [recalled:fence] The posts were rotten.") \
        == "It took long. The posts were rotten."


def test_nested_markers_are_removed():
    assert strip_recall_markers("[recalled:recalled:recalled:meaning] what it means") == "what it means"


def test_text_without_markers_is_returned_unchanged():
    said = "I read [the manual] and recalled nothing."
    assert strip_recall_markers(said) == said
    assert strip_recall_markers("") == ""


@pytest.fixture(scope="module")
def perception(tmp_path_factory):
    from aurora_expression_perception import ExpressionPerceptionEngine
    return ExpressionPerceptionEngine(state_dir=str(tmp_path_factory.mktemp("perception")))


def test_ingest_never_creates_a_word_from_a_marker(perception):
    perception.ingest_interaction(
        {"input": "The fence needs mending.\n[recalled:fence] I spent the morning fixing the fence."},
        mode="gateway")
    names = list(getattr(perception.oets.web, "nodes", {}) or {})
    assert not any("[recalled" in n or "recalled:" in n for n in names)
    assert not any("[recalled" in n for n in perception.lexicon.entries)

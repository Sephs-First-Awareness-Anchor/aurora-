# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Directive P1 Track ST -- stance lexicon (aurora_internal/aurora_stance_
lexicon.py).

The general lexicon.json mistags hedge words like "maybe"/"think" as
role=noun (a pre-existing, separately-tracked legacy-ingestion gap), so
stance-word selection cannot reuse lexicon.find_by_role(). This module
is a small, dedicated stance lexicon sourced from aurora_grammar_
engine.py's own RoleTagger._CONTEXT_UNIGRAMS/_CONTEXT_BIGRAMS -- the
same vocabulary already used to perceive/tag epistemic framing, so
generation and perception share one real word list.
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_internal.aurora_stance_lexicon import (  # noqa: E402
    AFFIRMATIVE_MARKERS,
    MILD_HEDGES,
    MODERATE_HEDGES,
    STRONG_HEDGES,
    affirmative_marker,
    all_stance_words,
    hedge_for_strength,
)


def test_stance_words_are_sourced_from_the_real_grammar_engine_vocabulary():
    """Every word here must exist in RoleTagger's own tagging vocabulary
    -- generation must draw from the same real list perception already
    uses to recognize epistemic framing, not an independently invented
    one."""
    from aurora_grammar_engine import RoleTagger

    tagger_vocab = set(RoleTagger._CONTEXT_UNIGRAMS) | set(RoleTagger._CONTEXT_BIGRAMS)
    for word in all_stance_words():
        assert word.lower() in tagger_vocab, (
            f"stance word {word!r} is not in RoleTagger's tagged vocabulary"
        )


def test_hedge_for_strength_scales_low_strength_to_mild_band():
    word = hedge_for_strength(0.1, [])
    assert word in MILD_HEDGES


def test_hedge_for_strength_scales_high_strength_to_strong_band():
    word = hedge_for_strength(0.95, [])
    assert word in STRONG_HEDGES


def test_hedge_for_strength_scales_mid_strength_to_moderate_band():
    word = hedge_for_strength(0.5, [])
    assert word in MODERATE_HEDGES


def test_hedge_for_strength_respects_exclude_and_falls_back_to_adjacent_band():
    excluded = list(MILD_HEDGES)
    word = hedge_for_strength(0.1, excluded)
    assert word, "must fall back to an adjacent band rather than return empty"
    assert word not in excluded


def test_hedge_for_strength_fails_quiet_when_lexicon_exhausted():
    assert hedge_for_strength(0.1, list(all_stance_words())) == ""


def test_hedge_for_strength_clamps_out_of_range_strength():
    # Must not raise on out-of-[0,1] input -- clamp rather than crash.
    assert hedge_for_strength(-5.0, []) in MILD_HEDGES
    assert hedge_for_strength(50.0, []) in STRONG_HEDGES


def test_affirmative_marker_returns_unused_marker():
    word = affirmative_marker([])
    assert word in AFFIRMATIVE_MARKERS
    word2 = affirmative_marker([word])
    assert word2 != word
    assert word2 in AFFIRMATIVE_MARKERS


def test_affirmative_marker_fails_quiet_when_exhausted():
    assert affirmative_marker(list(AFFIRMATIVE_MARKERS)) == ""


def test_all_stance_words_has_no_duplicates():
    words = all_stance_words()
    assert len(words) == len(set(w.lower() for w in words))

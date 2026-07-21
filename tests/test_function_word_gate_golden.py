# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
R1.9.4 Step 1: two-direction golden guard for the refined _parseable
predicate.

The R1.7 predicate required >=1 strong function word (article/
preposition/conjunction/wh-word) per sentence. That correctly caught
word salad but also rejected every valid article-less/telegraphic
sentence equally -- "She sings well." has zero strong words and is
perfectly grammatical. R1.9.4 refines the check to a real clause-
structure assessment (subject + single verb + complement/modifier, via
L2's POS categories) with strong-word presence demoted to one path to
pass rather than the only one, plus a new missing-determiner check for
the "I need answer to question." class this could otherwise miss.

Two-direction golden rule (no loosening ratchet): a predicate refinement
is only live once BOTH directions separate cleanly --
  1. every case that used to correctly fail still fails
     (tests/test_generation_collapse_regression.py, unchanged, plus the
     4 grammar micro-regression cases from R1.9.2/R1.9.3's diagnosis)
  2. new, previously-wrongly-failing valid cases now pass, AND new
     malformed cases (that the OLD predicate would have wrongly let
     through on strong-word presence alone) now correctly fail.
"""
from aurora_internal.aurora_semantic_probe_battery import _parseable

# R1.9.2/R1.9.3 diagnosis's own verbatim failures -- confirmed absent from
# live delivered output, but the PREDICATE must still recognize them as
# not parseable (these are static string checks on the instrument, not
# claims about what the composer currently generates).
GRAMMAR_MICRO_REGRESSION = [
    "I energy.",
    "I cost.",
    "I is.",
    "Photosynthesis expressed weight terms need defensive.",
]

# New golden set (15 hand-authored): telegraphic/article-less sentences
# that are fully grammatical and must PASS under the refined predicate.
GOLDEN_TELEGRAPHIC_PASS = [
    "She sings well.",
    "Photosynthesis needs light energy.",
    "I am glad.",
    "Trust matters deeply.",
    "I feel curious.",
    "She seems tired today.",
    "Silence grows heavy.",
    "I understand completely.",
    "Growth takes time.",
    "Wonder never fades.",
]

# Article-dependent malformed sentences (missing a determiner where clause
# structure demands one) that must FAIL -- the class the OLD predicate
# could accidentally miss whenever some unrelated strong word appeared
# elsewhere in the sentence (e.g. "to" in "I need answer to question.").
GOLDEN_ARTICLE_MALFORMED_FAIL = [
    "I need answer to question.",
    "She wants answer now.",
    "He found solution.",
    "I made mistake yesterday.",
    "We have problem.",
]


def test_grammar_micro_regression_cases_still_fail():
    failures = [s for s in GRAMMAR_MICRO_REGRESSION if _parseable(s)]
    assert not failures, f"grammar micro-regression wrongly passed: {failures}"


def test_each_grammar_micro_regression_case_individually():
    for i, s in enumerate(GRAMMAR_MICRO_REGRESSION):
        assert not _parseable(s), f"regression at index {i}: {s!r}"


def test_golden_telegraphic_sentences_pass():
    failures = [s for s in GOLDEN_TELEGRAPHIC_PASS if not _parseable(s)]
    assert not failures, f"valid telegraphic sentence(s) wrongly rejected: {failures}"
    assert len(GOLDEN_TELEGRAPHIC_PASS) == 10


def test_each_golden_telegraphic_sentence_individually():
    for i, s in enumerate(GOLDEN_TELEGRAPHIC_PASS):
        assert _parseable(s), f"regression at index {i}: {s!r}"


def test_golden_article_malformed_sentences_fail():
    failures = [s for s in GOLDEN_ARTICLE_MALFORMED_FAIL if _parseable(s)]
    assert not failures, f"article-malformed sentence(s) wrongly accepted: {failures}"
    assert len(GOLDEN_ARTICLE_MALFORMED_FAIL) == 5


def test_each_golden_article_malformed_sentence_individually():
    for i, s in enumerate(GOLDEN_ARTICLE_MALFORMED_FAIL):
        assert not _parseable(s), f"regression at index {i}: {s!r}"


def test_golden_set_size_is_fifteen():
    """R1.9.4 Step 1 spec: "~15 hand-authored" cases covering both
    directions."""
    assert len(GOLDEN_TELEGRAPHIC_PASS) + len(GOLDEN_ARTICLE_MALFORMED_FAIL) == 15


def test_two_direction_separation_is_clean():
    """The golden-pair rule this directive names: the refined predicate
    is live only when both directions separate cleanly -- not one
    sentence from either golden list may land on the wrong side."""
    for s in GOLDEN_TELEGRAPHIC_PASS:
        assert _parseable(s) is True
    for s in GOLDEN_ARTICLE_MALFORMED_FAIL:
        assert _parseable(s) is False

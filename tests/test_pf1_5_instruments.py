# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Directive PF1.5: instrument re-derivation. adequacy_score (relevance +
predicate-argument term) and role_coherent/wellformed_and_coherent
(wellformedness + finite-clause check), both purely additive to the
existing scorer/_parseable -- neither pre-existing function is
touched.
"""
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_internal.aurora_pf1_5_instruments import (  # noqa: E402
    adequacy_score, role_coherent, wellformed_and_coherent,
)
from aurora_internal.aurora_semantic_probe_battery import _parseable  # noqa: E402
from tests.test_generation_collapse_regression import (  # noqa: E402
    GARBLED_RESPONSES, GOOD_SENTENCES, ORIGINAL_AUDIT_GARBLE,
)

# The EXACT same anchor-token regex the existing relevance scorer uses
# (run_probe_battery.py's _make_relevance_scorer) -- used here only to
# independently cross-check adequacy_score's base term, so these tests
# fail loudly if adequacy's tokenization ever drifts from relevance's
# again (this drift is exactly what PF1.5's own live revalidation run
# caught before shipping: mean adequacy came out BELOW mean relevance,
# which is impossible if adequacy really is "relevance base + a
# non-negative bonus").
_OLD_RELEVANCE_RE = re.compile(r"[a-zA-Z][a-zA-Z']{2,}")


def _old_relevance(text: str, anchor: dict) -> float:
    words = _OLD_RELEVANCE_RE.findall(text.lower())
    hits = sum(1 for w in words if w in anchor)
    return hits / len(words)


# ── adequacy_score ────────────────────────────────────────────────

def test_adequacy_none_on_empty_response():
    assert adequacy_score("", {"water": 1.0}) is None


def test_adequacy_base_matches_plain_hit_fraction_with_no_predicate_pair():
    # "clear" is the only anchor word here and it's an adjective, not a
    # verb -- no predicate-argument bonus should apply.
    anchor = {"clear": 1.0}
    text = "I feel very clear today"
    score = adequacy_score(text, anchor)
    assert score == _old_relevance(text, anchor)


def test_adequacy_rewards_a_real_predicate_argument_pair():
    """'need' (verb) and 'water' (noun) are both anchor-relevant and
    adjacent -- adequacy must exceed the bare hit-fraction relevance
    score for the same text."""
    anchor = {"need": 1.0, "water": 1.0}
    text = "I need water now"
    plain = _old_relevance(text, anchor)
    score = adequacy_score(text, anchor)
    assert score > plain
    assert score == min(1.0, plain + 0.15)


def test_adequacy_no_bonus_when_verb_and_noun_are_not_both_anchored():
    """'need' is anchored but 'chair' (the nearby noun) is not -- no
    real on-topic predicate-argument pair exists, no bonus."""
    anchor = {"need": 1.0}
    text = "I need a chair"
    score = adequacy_score(text, anchor)
    assert score == _old_relevance(text, anchor)


def test_adequacy_bonus_applies_only_once():
    anchor = {"need": 1.0, "want": 1.0, "water": 1.0, "food": 1.0}
    text = "I need water and want food"
    plain = _old_relevance(text, anchor)
    score = adequacy_score(text, anchor)
    assert score <= 1.0
    assert score == min(1.0, plain + 0.15)


def test_adequacy_base_term_is_never_lower_than_old_relevance_on_real_probe_shaped_text():
    """Direct regression guard for the exact bug PF1.5's own live
    revalidation run caught: adequacy's base arithmetic must always
    equal (never merely approximate) old relevance's, across a spread
    of realistic response shapes, not just one hand-picked sentence."""
    anchor = {"clear": 1.0, "real": 1.0, "water": 1.0, "planning": 1.0}
    samples = [
        "I planning before clear.",
        "I did dinner real.",
        "I am not sure about that.",
        "You knowing this changes things.",
        "Water is real and clear to me.",
    ]
    for text in samples:
        assert adequacy_score(text, anchor) >= _old_relevance(text, anchor)


# ── role_coherent ────────────────────────────────────────────────

def test_role_coherent_rejects_bare_gerund_as_finite_verb():
    """Real observed PF1.3/PF1.4 output shapes -- the exact defect
    class this instrument exists to catch."""
    assert role_coherent("I planning before real.") is False
    assert role_coherent("I knowing or always.") is False
    assert role_coherent("I seeing prioritize clear.") is False


def test_role_coherent_accepts_auxiliary_plus_gerund():
    assert role_coherent("I am planning a trip.") is True
    assert role_coherent("I was knowing that already.") is True
    assert role_coherent("I keep seeing this pattern.") is True


def test_role_coherent_does_not_flag_ing_nouns():
    assert role_coherent("I attended the meeting.") is True
    assert role_coherent("I like the morning light.") is True


def test_role_coherent_ignores_contractions():
    """"I'm planning" tokenizes as "i'm", never equal to the bare
    pronoun "i" -- must not false-positive."""
    assert role_coherent("I'm planning a trip.") is True


def test_role_coherent_true_on_empty_and_non_ing_text():
    assert role_coherent("") is False
    assert role_coherent("I can help with that.") is True


def test_role_coherent_checks_you_subject_too():
    assert role_coherent("You knowing this changes things.") is False


# ── wellformed_and_coherent: combined gate ──────────────────────────

def test_wellformed_and_coherent_rejects_all_24_traced_garbled_responses():
    failures = [r for r in GARBLED_RESPONSES if wellformed_and_coherent(r)]
    assert not failures, f"{len(failures)} garbled response(s) wrongly passed: {failures}"


def test_wellformed_and_coherent_rejects_original_audit_garble():
    assert wellformed_and_coherent(ORIGINAL_AUDIT_GARBLE) is False


def test_wellformed_and_coherent_accepts_all_24_good_sentences():
    """The R1.9.3 golden good-sentence set contains no bare-gerund-as-
    finite-verb construction -- role_coherent must not introduce any
    new false negatives against it."""
    failures = [s for s in GOOD_SENTENCES if not wellformed_and_coherent(s)]
    assert not failures, f"{len(failures)} good sentence(s) wrongly failed: {failures}"


def test_wellformed_and_coherent_rejects_the_real_pf1_bare_gerund_cases_even_though_parseable():
    """The whole point of PF1.5: these sentences DO pass the existing
    _parseable() (they have a plausible clause shape) but must fail
    the new combined gate."""
    cases = [
        "I planning before real.",
        "I knowing or always.",
        "I seeing prioritize clear.",
    ]
    for c in cases:
        assert _parseable(c) is True, f"expected {c!r} to still pass old _parseable()"
        assert wellformed_and_coherent(c) is False, f"expected {c!r} to fail the new gate"

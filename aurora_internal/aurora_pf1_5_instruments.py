"""
Directive PF1.5 -- instrument re-derivation.

PF1.3/PF1.4 changed WHAT gets selected and HOW slots get filled;
PF1.5's job is to make sure the instruments measuring the result are
still measuring the right thing. Two additions, both purely additive
(neither touches the existing functions they extend -- R1.9.3's
24-case golden set and every prior directive's own acceptance numbers
stay pinned to exactly what they always measured):

1. **Adequacy** (relevance -> adequacy): the existing relevance scorer
   (run_probe_battery.py's _make_relevance_scorer, aurora_expression_
   perception.py's _score_composer_candidate) counts isolated word
   hits against the turn's anchor set -- a response can score high by
   having several anchor-relevant words scattered through it with no
   relationship to each other. `adequacy_score()` adds a predicate-
   argument term on top of that same base score: a bonus specifically
   for a verb and a noun that are BOTH anchor-relevant AND sit near
   each other (a real predicate taking a real, on-topic argument),
   not just present somewhere in the response. PF1.6 residue W3
   (2026-07-21) added a second correction, confidence damping: a
   response with very few countable words can trivially hit adequacy
   1.0 off a single lucky anchor word ("I am bit." scored 1.0) -- the
   base term is now scaled down when there's too little text to trust
   hits/len's statistics, undamped (identical to the original
   arithmetic) for any response of ordinary length.

2. **Role-coherence** (wellformedness extension): aurora_internal.
   aurora_semantic_probe_battery._parseable() catches word salad but
   was never designed to catch a specific, real failure class PF1.3/
   PF1.4's own live-boot runs produced -- a bare present-participle
   used as a finite main verb with no auxiliary ("I planning before
   real.", "I knowing or always."). `role_coherent()` catches exactly
   that shape. `wellformed_and_coherent()` is `_parseable() AND
   role_coherent()` -- the new, stronger combined gate for PF1.6's
   acceptance measurement.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
import re
from typing import Dict, Optional

from aurora_expression_perception import infer_word_role
from aurora_internal.aurora_semantic_probe_battery import (
    _parseable, _WORD_RE, _SENTENCE_SPLIT_RE,
)

# The SAME anchor-token regex the existing relevance scorer uses
# (run_probe_battery.py's _make_relevance_scorer / aurora_constraint_
# emission.build_relevance_anchor_set's own tokenization) -- minimum
# 3 characters, so short function words ("I", "a", "is") never inflate
# the denominator. _WORD_RE (aurora_semantic_probe_battery.py) is a
# DIFFERENT regex built for _parseable()'s word-shape checks (min
# length 1) -- using it here silently changed adequacy's "base" term
# out from under the relevance arithmetic it's documented to match.
# Caught live: PF1.5's own two-direction revalidation run showed mean
# adequacy BELOW mean relevance, which is impossible if adequacy is
# truly "relevance base + a non-negative bonus" -- traced to this
# mismatch before shipping.
_ANCHOR_TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z']{2,}")

# How much a genuine on-topic predicate-argument pair is worth on top
# of the existing hits/len base score. Small enough that adequacy can
# never rank a response with zero relevant words above one with real
# relevant content -- it only breaks ties/rewards structure among
# already-relevant responses.
_PREDICATE_ARGUMENT_BONUS = 0.15
# How many tokens ahead of a relevant verb to look for its argument --
# generous enough to span a determiner/descriptor ("need the water"),
# tight enough to stay "near", not "anywhere in the response".
_ARGUMENT_SEARCH_WINDOW = 4

# PF1.6 residue W3 (2026-07-21): a response with very few countable
# (3+ char) tokens can trivially score adequacy 1.0 off a single lucky
# anchor hit -- confirmed live, "I am bit." (PropositionFrame's own
# anchor rung rendering a bare copula plus the anchor word, no real
# relation) scored 1.0 against an anchor containing "bit", because "I"
# and "am" are both under the 3-char counting threshold and "bit" was
# the only word left to average over. hits/len's statistical
# confidence scales with how many words it's actually averaged across;
# below this many countable words, the base term is damped
# proportionally rather than trusted at full strength. This is the
# report's own "minimum-content check" option (the other option,
# frame-relation-presence, would need a `frame` parameter threaded
# through every call site -- this is self-contained). Deliberately
# breaks the "adequacy >= old relevance" guarantee for pathologically
# short responses ONLY -- that guarantee was never meant to bless a
# single-word coincidence as high-confidence adequacy; it still holds
# for any response of ordinary length (see tests).
_MIN_COUNTABLE_WORDS_FOR_FULL_CONFIDENCE = 3


def adequacy_score(response_text: str, anchor: Dict[str, float]) -> Optional[float]:
    """hits/len base (identical arithmetic to the existing relevance
    scorer, damped for very short responses -- see
    _MIN_COUNTABLE_WORDS_FOR_FULL_CONFIDENCE) plus a predicate-argument
    bonus. Returns None (not 0.0) on an empty response, matching the
    existing scorer's own failure contract -- a scoring non-result
    must stay distinguishable from a genuinely zero-adequacy response."""
    words = _ANCHOR_TOKEN_RE.findall(str(response_text or "").lower())
    if not words:
        return None
    lower_words = words
    hits = sum(1 for w in lower_words if w in anchor)
    base = hits / len(lower_words)
    confidence = min(1.0, len(lower_words) / _MIN_COUNTABLE_WORDS_FOR_FULL_CONFIDENCE)
    base *= confidence

    tagged = [(w, infer_word_role(w)) for w in lower_words]
    pa_bonus = 0.0
    for i, (w, role) in enumerate(tagged):
        if role != "verb" or w not in anchor:
            continue
        for j in range(i + 1, min(i + 1 + _ARGUMENT_SEARCH_WINDOW, len(tagged))):
            w2, role2 = tagged[j]
            if role2 == "noun" and w2 in anchor:
                pa_bonus = _PREDICATE_ARGUMENT_BONUS
                break
        if pa_bonus:
            break

    return min(1.0, base + pa_bonus)


# Words that legitimately precede a present-participle in a finite
# clause ("I am planning", "I have been knowing" [rare but valid],
# "I keep seeing") -- a subject pronoun directly followed by one of
# these is fine; directly followed by a bare -ing word with none of
# these between them is the defect this catches.
_ING_AUXILIARIES = {
    "am", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "will", "would", "shall", "should",
    "can", "could", "may", "might", "must",
    "keep", "keeps", "kept", "start", "starts", "started",
    "stop", "stops", "stopped",
}
_SUBJECT_PRONOUNS = {"i", "you"}
# Words that end in "ing" but are established as ordinary nouns, not
# gerund/participle verb forms -- reuse the same override list
# aurora_expression_perception.infer_word_role already ships (its
# _ROLE_HINTS table exists for exactly this reason), rather than
# inventing a second one here.
_ING_NOUN_OVERRIDES = {
    "morning", "evening", "ceiling", "building", "meeting", "setting",
    "blessing", "wedding", "clothing", "crossing", "ending", "beginning",
    "opening", "gathering", "thing", "anything", "spring", "king",
    "ring", "wing", "string",
}


def role_coherent(text: str) -> bool:
    """A subject pronoun ("I"/"you") immediately followed by a bare
    present-participle, with no recognized auxiliary in between and no
    -ing-as-noun override, is not a finite clause -- fails. Per
    sentence, same split as _parseable() uses."""
    text = str(text or "").strip()
    if not text:
        return False
    for sentence in _SENTENCE_SPLIT_RE.split(text):
        words = [w.lower() for w in _WORD_RE.findall(sentence)]
        for i, w in enumerate(words):
            if w not in _SUBJECT_PRONOUNS or i + 1 >= len(words):
                continue
            nxt = words[i + 1]
            if (nxt.endswith("ing") and len(nxt) > 4
                    and nxt not in _ING_AUXILIARIES
                    and nxt not in _ING_NOUN_OVERRIDES):
                return False
    return True


def wellformed_and_coherent(text: str, pos_lookup=None) -> bool:
    """PF1.6's acceptance gate: the existing _parseable() (unchanged)
    AND role_coherent() (new)."""
    return _parseable(text, pos_lookup) and role_coherent(text)

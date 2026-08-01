#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Directive P1 Track ST -- the stance lexicon.

The general word lexicon (`aurora_state/lexicon.json`) tags hedge words
like "maybe" and "think" as `role: noun` -- a legacy-unverified
mistagging artifact from blind word ingestion (a known, separately
tracked pre-existing gap; see the "blind-origin entries missing the
legacy-unverified tag" test finding). Selecting stance words through
`lexicon.find_by_role("context")` would inherit that mistagging and
return nothing usable. This module is a small, dedicated stance
lexicon instead -- sourced directly from `aurora_grammar_engine.py`'s
`RoleTagger._CONTEXT_UNIGRAMS`/`_CONTEXT_BIGRAMS` (the same vocabulary
already used to TAG epistemic framing during parsing, S1.2's seeded
"hedge"/"uncertain"/"guarantee" OETS concepts giving it semantic
grounding) so the generation side and the perception side draw from
the same real vocabulary, not two independently-invented lists.

Doctrine (registry): content relevance must never gate STANCE. These
words are selected by internal confidence-signal strength alone, never
by anchor/topic competition -- affect never picks content, content
never picks stance.
"""
from __future__ import annotations

from typing import List, Tuple

# Sourced from aurora_grammar_engine.py's RoleTagger._CONTEXT_UNIGRAMS/
# _CONTEXT_BIGRAMS (the live perception-side tagging vocabulary) --
# split into three signal-strength bands, weakest hedge to strongest,
# so a stance slot can scale word choice to how far below threshold
# the confidence signal actually is (directive: "fills from stance
# lexicon scaled by signal strength").
MILD_HEDGES: Tuple[str, ...] = (
    "probably", "likely", "it seems", "i believe",
)

MODERATE_HEDGES: Tuple[str, ...] = (
    "maybe", "perhaps", "possibly", "i think", "i suppose", "i suspect",
    "it appears",
)

STRONG_HEDGES: Tuple[str, ...] = (
    "unlikely", "i'm not", "not sure", "i wonder", "apparently",
    "seemingly", "reportedly", "supposedly",
)

# Affirmative stance markers -- the directive's "confident -> slot empty
# OR affirmative" branch. Voiced occasionally when confidence is high
# but the stance slot is still eligible (e.g. serious register), never
# as a default filler.
AFFIRMATIVE_MARKERS: Tuple[str, ...] = (
    "clearly", "honestly", "frankly", "truthfully",
)

_ALL_BANDS: Tuple[Tuple[str, ...], ...] = (MILD_HEDGES, MODERATE_HEDGES, STRONG_HEDGES)


def hedge_for_strength(signal_strength: float, exclude: List[str]) -> str:
    """Return one hedge word/phrase scaled to `signal_strength` (0.0 =
    barely below threshold, 1.0 = maximally uncertain), skipping any
    word already in `exclude` (case-insensitive) -- cross-sentence
    diversity, same discipline as every other slot's `already`/`seen`
    handling. Falls back to an adjacent band if the chosen band is
    fully exhausted by `exclude`; returns "" only if the entire
    lexicon is exhausted (fail-quiet, matching this feature family's
    established posture)."""
    strength = max(0.0, min(1.0, float(signal_strength or 0.0)))
    seen = {w.lower() for w in (exclude or [])}

    if strength < 0.34:
        band_order = (MILD_HEDGES, MODERATE_HEDGES, STRONG_HEDGES)
    elif strength < 0.67:
        band_order = (MODERATE_HEDGES, MILD_HEDGES, STRONG_HEDGES)
    else:
        band_order = (STRONG_HEDGES, MODERATE_HEDGES, MILD_HEDGES)

    for band in band_order:
        for word in band:
            if word.lower() not in seen:
                return word
    return ""


def affirmative_marker(exclude: List[str]) -> str:
    """Return one affirmative stance marker not already used this
    response, or "" if the pool is exhausted."""
    seen = {w.lower() for w in (exclude or [])}
    for word in AFFIRMATIVE_MARKERS:
        if word.lower() not in seen:
            return word
    return ""


def all_stance_words() -> Tuple[str, ...]:
    """The full stance vocabulary (hedges + affirmative markers), for
    callers that need to check membership rather than select one."""
    return tuple(w for band in _ALL_BANDS for w in band) + AFFIRMATIVE_MARKERS

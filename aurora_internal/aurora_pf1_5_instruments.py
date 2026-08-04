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


# Live user report (2026-08-03): "What should I use for the right
# reference for just?" -- delivered from aurora_working_memory.py's
# _render_from_comprehension_intent(), a composer call site independent
# of the main resp_A/resp_B pipeline. Neither _parseable() nor
# role_coherent() catch it: "for just" scans as preposition+word with
# nothing structurally wrong at the coarse-POS level this module already
# uses. The actual defect is that a preposition's "object" was a bare
# degree/focus adverb ("just", "really", "very") with nothing left for
# it to modify -- prepositions take noun phrases as objects, and these
# adverbs are never that.
#
# An allowlist-the-good-adverbs version of this check was tried first
# and produced a real false positive against the existing R1.9.3 golden
# set: "...think it through carefully." -- "through" is a phrasal-verb
# particle here ("think X through"), not a preposition taking
# "carefully" as its object, and infer_word_role has no way to tell
# particle-"through" apart from preposition-"through". Trying to
# enumerate every legitimate preposition-like-word + adverb combination
# risks the same false-positive class repeating for other phrasal verbs
# (see through, work through, get by, look on, come around, ...).
# Inverted to a small, deliberately narrow DENYLIST of degree/focus
# adverbs that are essentially never a genuine preposition's object in
# real English, instead -- a false negative here (missing some other
# real defect) is far safer than blocking a legitimate sentence.
_PREP_ADVERB_OBJECT_DENYLIST = frozenset({
    "just", "really", "very", "quite", "rather", "only", "even",
    "also", "too", "actually", "basically", "literally", "simply",
    "truly", "honestly", "seriously", "certainly", "probably",
    "definitely", "totally", "completely", "absolutely",
})


def preposition_object_coherent(text: str) -> bool:
    """A preposition immediately followed by a denylisted degree/focus
    adverb, with that adverb ending its sentence (nothing following for
    it to modify), fails -- there is no noun phrase serving as the
    preposition's object. Per sentence, same split as _parseable() uses."""
    text = str(text or "").strip()
    if not text:
        return False
    for sentence in _SENTENCE_SPLIT_RE.split(text):
        words = [w.lower() for w in _WORD_RE.findall(sentence)]
        for i, w in enumerate(words):
            if infer_word_role(w) != "preposition" or i + 1 >= len(words):
                continue
            nxt = words[i + 1]
            if i + 2 == len(words) and nxt in _PREP_ADVERB_OBJECT_DENYLIST:
                return False
    return True


_WH_WORDS = frozenset({"who", "whom", "whose", "what", "where", "why", "which"})
# A wh-word is only coherent mid-response when what follows it can
# actually continue it into a real embedded/relative clause -- another
# pronoun as the clause's own subject ("who you are", "who I am") or a
# verb/copula continuing a fronted embedded question ("who made you",
# "what happened"). Anything else (nothing, an adjective, a bare noun)
# leaves the wh-word answering nothing.
_WH_CONTINUATION_ROLES = frozenset({"pronoun", "verb"})
_SENTENCE_WITH_TERMINATOR_RE = re.compile(r"([^.!?]+)([.!?]+)?")


def _sentences_with_terminators(text: str):
    for m in _SENTENCE_WITH_TERMINATOR_RE.finditer(text):
        content = m.group(1)
        if content and content.strip():
            yield content, (m.group(2) or "")


def interrogative_object_coherent(text: str) -> bool:
    """Communication Integrity Repair (2026-08-04): live user report --
    identity-question turns ("Who made you?") were reaching the device as
    "I understand who. I made who." / "I did who clear. I understand who
    good." -- a wh-word standing in for the answer it was supposed to
    introduce, not part of one. Neither _parseable() nor role_coherent()
    catch this: each individual sentence is short but not word-salad by
    their measures ("who" scans as an ordinary noun-shaped token to the
    coarse tagger). A genuine question ("Who is going to be there
    tonight?") is exempt -- it terminates in "?" and IS the wh-word's
    own clause, nothing to continue. A declarative sentence's wh-word
    must be followed by a real clause continuation; if it ends the
    sentence, or is followed only by something that can't extend it
    into a clause (an adjective, a bare noun, nothing), the sentence
    has no recoverable proposition."""
    text = str(text or "").strip()
    if not text:
        return False
    for content, terminator in _sentences_with_terminators(text):
        if "?" in terminator:
            continue
        words = [w.lower() for w in _WORD_RE.findall(content)]
        for i, w in enumerate(words):
            if w not in _WH_WORDS:
                continue
            if i + 1 >= len(words):
                return False
            if infer_word_role(words[i + 1]) not in _WH_CONTINUATION_ROLES:
                return False
    return True


# Communication Integrity Repair (2026-08-04): live user report -- an
# identity-question turn reached the device as "I exist sunni." A
# handful of verbs are grammatically existential/intransitive in
# English -- they never take a following bare noun as a direct object
# (you cannot "exist" a thing) -- so a bare noun immediately after one
# is always a dropped preposition/copula, not a valid complement. Kept
# to the small set of verbs with essentially no legitimate bare-noun
# continuation, rather than every intransitive verb, to keep the false-
# positive surface small (see _BARE_ADVERBIAL_NOUNS below for the
# temporal/locative exception these verbs DO take validly).
_INTRANSITIVE_VERBS = frozenset({
    "exist", "exists", "existed", "existing",
    "live", "lives", "lived", "living",
    "occur", "occurs", "occurred",
    "happen", "happens", "happened",
    "remain", "remains", "remained",
    "persist", "persists", "persisted",
})
# Bare temporal/locative adverbials ("happened yesterday", "remains
# here") are grammatical without a preposition and would otherwise
# false-positive against infer_word_role's noun default for words not
# in its hint table.
_BARE_ADVERBIAL_NOUNS = frozenset({
    "today", "yesterday", "tomorrow", "here", "there", "now", "then",
    "home", "abroad", "outside", "inside", "upstairs", "downstairs",
})


def existential_complement_coherent(text: str) -> bool:
    """A bare noun-role word directly after an existential/intransitive
    verb, with no preposition or copula between them, has no valid
    complement -- generalizes past the one live-reported name ("I exist
    sunni.") to any bare noun after any of these verbs."""
    text = str(text or "").strip()
    if not text:
        return False
    for sentence in _SENTENCE_SPLIT_RE.split(text):
        words = [w.lower() for w in _WORD_RE.findall(sentence)]
        for i, w in enumerate(words):
            if w not in _INTRANSITIVE_VERBS or i + 1 >= len(words):
                continue
            nxt = words[i + 1]
            if nxt in _BARE_ADVERBIAL_NOUNS:
                continue
            if infer_word_role(nxt) == "noun":
                return False
    return True


# CIR audit follow-up (2026-08-04): "I understand enter beautiful. I
# did enter clear." was documented at ship time as a known-uncaught
# case (a bare verb the shared role table doesn't recognize -- "enter"
# -- adjacent to another bare verb), deliberately left to arbitration's
# meaning-preservation check as the second line of defense. A follow-up
# audit both confirmed that gap AND found the SAME general failure
# shape in it doesn't require verb-verb detection at all: "enter
# beautiful" and "enter clear" are a bare noun-defaulted word directly
# followed by a bare adjective, with nothing linking them -- and the
# audit's own new counter-examples ("I am form real.", "I change form
# real.") are the identical shape. English attributive adjectives
# precede the noun they modify, not follow it, except in a small closed
# class of resultative/object-complement constructions ("makes it
# simple", "keep the process simple") -- exempted below by checking for
# a determiner or a known resultative verb immediately before the noun.
_RESULTATIVE_VERBS = frozenset({
    "make", "makes", "made", "making",
    "keep", "keeps", "kept", "keeping",
    "find", "finds", "found", "finding",
    "leave", "leaves", "left", "leaving",
    "call", "calls", "called", "calling",
    "consider", "considers", "considered", "considering",
    "get", "gets", "got", "getting",
    "render", "renders", "rendered", "rendering",
    "deem", "deems", "deemed", "deeming",
    "judge", "judges", "judged", "judging",
    "want", "wants", "wanted", "wanting",
    "declare", "declares", "declared", "declaring",
    "paint", "paints", "painted", "painting",
    "drive", "drives", "drove", "driving",
    # CIR audit follow-up 2 (2026-08-04): the transitive/object-
    # complement verbs above ("makes it simple") are one resultative
    # shape; INTRANSITIVE change-of-state verbs taking a subject
    # complement adjective directly ("The system became stable.",
    # "The door swung open.") are a distinct, equally common one a
    # live audit found this check rejecting. Same exemption mechanism
    # (word immediately before the noun), different verb class.
    "become", "became", "becomes", "becoming",
    "grow", "grew", "grows", "growing", "grown",
    "turn", "turned", "turns", "turning",
    "fall", "fell", "falls", "falling", "fallen",
    "go", "went", "goes", "going", "gone",
    "come", "came", "comes", "coming",
    "run", "ran", "runs", "running",
    "swing", "swung", "swings", "swinging",
    "break", "broke", "breaks", "breaking", "broken",
    "burst", "bursts", "bursting",
    "blow", "blew", "blows", "blowing", "blown",
    "prove", "proved", "proves", "proving", "proven",
    "seem", "seemed", "seems", "seeming",
    "stay", "stayed", "stays", "staying",
    "remain", "remains", "remained",
})
# CIR audit follow-up 2 (2026-08-04): a live audit found these
# adjectives disproportionately appear in legitimate POSTPOSITIVE
# position -- directly after the noun/pronoun they modify, with no
# copula between them ("the option available", "anyone capable",
# "everyone present") -- a standard, if less common, English adjective
# position this check's core "adjective follows noun" rule otherwise
# treats as backwards. Exempted unconditionally as the adjective half
# of a pair, rather than trying to detect postpositive position
# structurally.
_POSTPOSITIVE_ADJECTIVES = frozenset({
    "available", "possible", "present", "capable", "responsible",
    "concerned", "involved", "aware",
})
# A comma/dash/semicolon/colon is a real syntactic boundary -- two
# words on opposite sides of one are never "immediately adjacent" in
# the sense this check cares about ("Hey, good to hear from you."
# must not be misread as "hey good" bumping into each other).
_CLAUSE_SPLIT_RE = re.compile(r"[.!?,;:]+|--")


def noun_adjective_order_coherent(text: str) -> bool:
    """A bare noun-role word directly followed by a bare adjective-role
    word, with no comma/other clause boundary, no determiner, and no
    resultative verb governing it, has no valid English reading --
    catches "enter beautiful"/"enter clear"/"form real" generally, not
    as a blacklist of those literal strings."""
    text = str(text or "").strip()
    if not text:
        return False
    for sentence in _SENTENCE_SPLIT_RE.split(text):
        for clause in _CLAUSE_SPLIT_RE.split(sentence):
            words = [w.lower() for w in _WORD_RE.findall(clause)]
            for i, w in enumerate(words):
                if infer_word_role(w) != "noun" or i + 1 >= len(words):
                    continue
                nxt = words[i + 1]
                if infer_word_role(nxt) != "adjective":
                    continue
                if nxt in _POSTPOSITIVE_ADJECTIVES:
                    continue
                preceding = words[i - 1] if i > 0 else ""
                if infer_word_role(preceding) == "determiner":
                    continue
                if preceding in _RESULTATIVE_VERBS:
                    continue
                return False
    return True


def wellformed_and_coherent(text: str, pos_lookup=None) -> bool:
    """PF1.6's acceptance gate, extended by Communication Integrity
    Repair (2026-08-04) with three more general structural checks:
    interrogative_object_coherent(), existential_complement_coherent(),
    and noun_adjective_order_coherent()."""
    return (
        _parseable(text, pos_lookup)
        and role_coherent(text)
        and preposition_object_coherent(text)
        and interrogative_object_coherent(text)
        and existential_complement_coherent(text)
        and noun_adjective_order_coherent(text)
    )

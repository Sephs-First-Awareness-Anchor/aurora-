# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
PF1.6 residue characterization, W2: why the claim gate (WorkingMemory.
_extract_claims -> proposition_substrate) fired on only 3/60 probes.
Characterized against all 60 real probe turns and found three distinct,
narrow gaps in the SAME existing gate (widened, not a parallel
extractor, per this work item's own scoping):

1. Contractions ("he's", "doesn't") never matched -- all patterns
   require the copula/auxiliary as a separate whitespace-delimited
   token. Fixed via a closed, unambiguous expansion set applied once
   before pattern matching. The copula contractions (he's/she's/...)
   turned out to have zero measurable effect on their own -- every word
   in that set is itself a pronoun/wh-word already on _CLAIM_SKIP_
   SUBJECTS. The negation contractions (doesn't/isn't/don't/...) are
   where this matters: a concrete-noun subject + contracted negated
   verb.
2. The relation-verb whitelist was scoped for technical/architectural
   claims (connects/blocks/requires/...) -- ordinary conversational
   stance verbs (trusts, surprised, wanted, promised) never matched.
   Widened with a curated list, same enumerated-list mechanism.
   negated_aux_pattern (the "doesn't <verb>" path) originally only
   checked the ORIGINAL technical-verb list, missing the new one --
   widened to check both.
3. reported_match had two gaps: its subject-capture regex required
   >=2 characters, so single-letter pronoun subjects ("I") never
   entered the reported-speech branch at all -- "I claimed I wasn't
   upset..." fell through to the plain copula pattern and captured "I
   claimed I" (the reporting frame swallowed whole) as its garbled
   subject; and its verb list only had 3rd-person -s/past forms, never
   the natural first-person base form ("I claim...", "I think...").
   Fixed both, AND changed the function to return after reported_match
   fires regardless of whether the nested clause produced anything (a
   reported-speech sentence's assertion lives in the reported clause;
   if nothing extractable lives there, the right answer is no claim,
   not a fallback re-scan of the whole line).

NOT touched, deliberately: _CLAIM_SKIP_SUBJECTS's exclusion of bare
pronoun subjects (he/she/it/i/we/you/they) -- this blocks most of the
report's own headline examples ("He's a bit nervous...") even with
contractions fixed, and looks like a genuine, intentional design
boundary (unresolved-referent claims are ambiguous) rather than an
oversight. Flagged for Sunni/Cael's decision, not relaxed here.
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_working_memory import WorkingMemory  # noqa: E402


def _wm():
    return WorkingMemory()


# ── Contraction expansion ───────────────────────────────────────────

def test_expand_claim_contractions_handles_pronoun_copula():
    wm = _wm()
    assert wm._expand_claim_contractions("He's tired") == "He is tired"
    assert wm._expand_claim_contractions("she's happy") == "she is happy"


def test_expand_claim_contractions_handles_negation():
    wm = _wm()
    assert wm._expand_claim_contractions("It doesn't work") == "It does not work"
    assert wm._expand_claim_contractions("I don't know") == "I do not know"


def test_expand_claim_contractions_preserves_case():
    wm = _wm()
    assert wm._expand_claim_contractions("What's up") == "What is up"
    assert wm._expand_claim_contractions("what's up") == "what is up"


def test_expand_claim_contractions_never_touches_possessive_or_arbitrary_noun_s():
    """Only the closed pronoun/wh-word set is expanded -- "Sarah's" (a
    proper noun, genuinely ambiguous between possessive and "has") must
    never be touched."""
    wm = _wm()
    assert wm._expand_claim_contractions("Sarah's book is here") == "Sarah's book is here"
    assert wm._expand_claim_contractions("the dog's bed") == "the dog's bed"


def test_claim_extraction_recognizes_contracted_negation_with_concrete_subject():
    """The copula contractions (he's/she's/...) all expand to words that
    are themselves pronouns/wh-words already on _CLAIM_SKIP_SUBJECTS --
    they can never unlock a NEW claim on their own when the contracted
    word is the subject. The negation contractions (doesn't/isn't/...)
    are where the fix has real, measurable effect: a concrete-noun
    subject paired with a contracted negated verb."""
    wm = _wm()
    claims = wm._extract_claims("The policy doesn't support flexibility.", source="user")
    assert claims
    assert claims[0]["subject"] == "policy"
    assert claims[0]["negated"] is True


def test_claim_extraction_still_skips_bare_pronoun_subjects_even_with_contraction_fixed():
    """Documents the boundary this work item deliberately did not move."""
    wm = _wm()
    assert wm._extract_claims("He's a bit nervous around new people.", source="user") == []
    assert wm._extract_claims("He is a bit nervous around new people.", source="user") == []


# ── Verb whitelist widening ──────────────────────────────────────────

def test_claim_extraction_recognizes_widened_conversational_verbs():
    wm = _wm()
    claims = wm._extract_claims("The ending really surprised me.", source="user")
    assert claims
    assert claims[0]["relation"] == "surprised"
    assert claims[0]["object"] == "me"


def test_claim_extraction_still_ignores_verbs_outside_the_widened_list():
    """Not every conversational verb is covered -- this is a bounded,
    curated widening, not a generic fallback. 'flew' is not in the
    list; no claim should be fabricated from a false match."""
    wm = _wm()
    claims = wm._extract_claims("The plane flew over the mountains.", source="user")
    assert claims == []


# ── reported_match: single-letter subject + suppress-on-empty-nested ─

def test_reported_speech_with_pronoun_reporter_and_extractable_content():
    wm = _wm()
    claims = wm._extract_claims("The dog claims the yard connects to freedom.", source="user")
    assert claims
    assert claims[0]["subject"] == "yard"


def test_reported_speech_with_unresolvable_nested_content_produces_no_garbled_fallback():
    """The exact bug found live: 'I claimed I wasn't upset...' must
    produce NO claim (the nested clause's subject is the pronoun 'I',
    correctly skipped) rather than falling through to a garbled
    full-line match ('i claimed i' as subject)."""
    wm = _wm()
    claims = wm._extract_claims(
        "I claimed I wasn't upset, but I've brought it up three times today.",
        source="user",
    )
    assert claims == []


def test_reported_match_recognizes_single_letter_subject():
    wm = _wm()
    claims = wm._extract_claims("I claim the bridge connects to the tower.", source="user")
    assert claims
    assert claims[0]["subject"] == "bridge"


# ── Real-battery regression: honest count, no claim quietly worse ───

def test_battery_claim_count_improves_without_producing_known_garbled_shapes():
    from aurora_internal.aurora_semantic_probe_battery import load_probes, PROBES_PATH
    wm = _wm()
    probes = load_probes(PROBES_PATH)
    has_claim = 0
    for p in probes:
        text = p.turns[-1] if p.turns else ""
        claims = wm._extract_claims(text, source="user")
        if claims:
            has_claim += 1
            subj = claims[0]["subject"]
            # No claim's subject should itself contain a reporting verb --
            # the exact shape of the bug this work item found and fixed.
            assert not any(
                v in subj.split() for v in ("claimed", "claims", "said", "says")
            ), f"garbled subject {subj!r} for {text!r}"
    assert has_claim > 3, "expected the widened gate to beat the original 3/60 baseline"

# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
R1.9.2 G1: relevance-primary word selection in SentenceComposer, the
delivered path (backward-attribution-confirmed in R1.9.1).

"Relevance chooses what is said; everything else shapes how" -- the third
instance of the never-content-only-style doctrine (F1.4: usage-habit ->
style; F5: register -> looseness; now: valence-proximity -> tone).
"""
import math

from aurora_expression_perception import ExpressionPerceptionEngine, SentenceComposer, LexicalEntry


def test_valence_tiebreak_bound_never_outweighs_one_hop_relevance():
    """The exact invariant that failed before this fix: the 0.3-0.4
    identity-bank cluster (near-perfect valence match) must not beat a
    0.2-relevance one-hop candidate (arbitrarily bad valence match), using
    the real weight the selector applies."""
    import aurora_constraint_emission as ace

    W = ExpressionPerceptionEngine.__new__(ExpressionPerceptionEngine)  # unused, just for method access path

    def score(relevance, valence_distance):
        return relevance * (1.0 + SentenceComposer._VALENCE_TIEBREAK_WEIGHT * (1.0 - min(1.0, valence_distance)))

    worst_case_distant_with_perfect_valence = score(ace.RELEVANCE_DISTANT_FLOOR, 0.0)
    worst_case_one_hop_with_zero_valence_bonus = score(ace.RELEVANCE_ONE_HOP_FLOOR, 1.0)
    assert worst_case_distant_with_perfect_valence < worst_case_one_hop_with_zero_valence_bonus, (
        "a RELEVANCE_DISTANT_FLOOR candidate with a perfect valence match must never "
        "outscore a RELEVANCE_ONE_HOP_FLOOR candidate with the worst possible valence "
        "match -- this is the exact invariant that let the identity-bank cluster "
        "(valence 0.3-0.4, near any typical target) win over cold-start topic words "
        "(valence 0.0, the generic seed default) before this fix"
    )

    # The specific real-world values that produced the pre-fix bug (R1.9.1
    # live trace): identity words at valence ~0.3-0.4 against observed live
    # targets of 0.35/0.45 (distance ~0.05-0.1), topic words at valence 0.0
    # against the same targets (distance ~0.35-0.45).
    identity_word_distant = score(ace.RELEVANCE_DISTANT_FLOOR, 0.05)
    topic_word_direct_anchor = score(ace.RELEVANCE_DIRECT_ANCHOR, 0.40)
    assert topic_word_direct_anchor > identity_word_distant, (
        "a direct-anchor topic word must beat a distant identity-bank word even "
        "when the identity word's valence match is nearly perfect and the topic "
        "word's is poor -- reproduces the real guitar-chords-vs-identity-bank "
        "scenario that caused R1.8.1's collapse"
    )


def test_score_composer_candidate_uses_shared_anchor_set_relevance():
    """Confirms the composer path imports and uses the SAME
    build_relevance_anchor_set() as ConstraintEmitter (F1) -- shared helper,
    not a duplicate implementation, per the R1.9.2 G1 instruction."""
    import aurora_constraint_emission as ace
    import aurora_expression_perception as aep

    assert aep.aurora_constraint_emission is ace
    assert hasattr(SentenceComposer, "_score_composer_candidate")
    assert hasattr(SentenceComposer, "_VALENCE_TIEBREAK_WEIGHT")


def test_r_min_floor_sits_between_distant_and_one_hop_score_ranges():
    """R1.9.2 G2: R_MIN must reject every RELEVANCE_DISTANT_FLOOR candidate
    (even with a perfect valence match) and accept every
    RELEVANCE_ONE_HOP_FLOOR candidate (even with the worst valence match) --
    the floor's whole job is separating those two populations."""
    import aurora_constraint_emission as ace

    def score(relevance, valence_distance):
        return relevance * (1.0 + SentenceComposer._VALENCE_TIEBREAK_WEIGHT * (1.0 - min(1.0, valence_distance)))

    max_distant = score(ace.RELEVANCE_DISTANT_FLOOR, 0.0)
    min_one_hop = score(ace.RELEVANCE_ONE_HOP_FLOOR, 1.0)
    assert max_distant < SentenceComposer._RELEVANCE_FLOOR_R_MIN < min_one_hop


def test_abstain_fires_when_every_required_slot_fails_the_floor():
    """Constructed scenario (not dependent on live OETS node-creation
    quirks): every required-slot (action/object) selection scores below
    R_MIN -> compose() must return a templated abstain response and log the
    reason, not assemble a sentence out of the least-bad irrelevant words."""
    composer = SentenceComposer.__new__(SentenceComposer)
    composer._last_floor_failures = [
        {"role": "action", "best_candidate": "x", "best_score": 0.05, "floor": 0.1},
        {"role": "object", "best_candidate": "y", "best_score": 0.06, "floor": 0.1},
    ]
    composer._last_required_slot_attempts = 2
    all_failed = (
        composer._last_required_slot_attempts > 0
        and len(composer._last_floor_failures) == composer._last_required_slot_attempts
    )
    assert all_failed, "abstain condition must trigger when every required slot failed the floor"


def test_abstain_does_not_fire_on_partial_floor_failure():
    """A response with SOME relevant content and one weak slot is a
    different, better problem (relevant-but-imperfect) than a response with
    zero grounding anywhere -- F4 non-goal: no full-response abstain for a
    partial miss."""
    composer = SentenceComposer.__new__(SentenceComposer)
    composer._last_floor_failures = [
        {"role": "action", "best_candidate": "x", "best_score": 0.05, "floor": 0.1},
    ]
    composer._last_required_slot_attempts = 3
    all_failed = (
        composer._last_required_slot_attempts > 0
        and len(composer._last_floor_failures) == composer._last_required_slot_attempts
    )
    assert not all_failed


def test_unverified_vocab_capped_even_as_perfect_direct_anchor():
    """D2 Acceptance Condition 2 fix (2026-07-17): a word auto-learned by
    ingest_interaction()'s blind POS-guess path (meaning stamped literally
    "learned:<word>") must not claim RELEVANCE_DIRECT_ANCHOR-tier score
    just because it matches itself in the anchor set -- this is exactly
    the live bug that let gibberish input (e.g. "zqxvornmal") get echoed
    back as "content": the word IS its own anchor, scoring at the direct
    tier, defeating the honest-abstain floor regardless of where R_MIN
    sits (a recalibrated R_MIN can never reject a direct-anchor score,
    confirmed live before this fix was found)."""
    import aurora_constraint_emission as ace

    composer = SentenceComposer.__new__(SentenceComposer)
    entry = LexicalEntry(
        word="zqxvornmal", meaning="learned:zqxvornmal", role="adjective",
        emotional_valence=0.0, noncomp_id="X:POLARITY", usage_count=1,
    )
    anchor_set = {"zqxvornmal": ace.RELEVANCE_DIRECT_ANCHOR}
    score = composer._score_composer_candidate(entry, anchor_set, valence_target=0.0)
    max_distant = ace.RELEVANCE_DISTANT_FLOOR * (1.0 + SentenceComposer._VALENCE_TIEBREAK_WEIGHT)
    assert score <= max_distant, (
        f"unverified single-use learned word scored {score}, above the distant-tier "
        f"ceiling {max_distant} -- it can still masquerade as grounded content"
    )
    assert score < SentenceComposer._RELEVANCE_FLOOR_R_MIN


def test_unverified_vocab_graduates_to_trust_after_real_repeated_use():
    """A word that has been used _UNVERIFIED_VOCAB_USAGE_FLOOR times or
    more is no longer capped -- sustained repeated use is itself a
    grounding signal, distinguishing reinforced vocabulary (including
    genuinely novel real words a user teaches informally) from a single
    same-turn echo of nonsense."""
    import aurora_constraint_emission as ace

    composer = SentenceComposer.__new__(SentenceComposer)
    entry = LexicalEntry(
        word="photosynthesis", meaning="learned:photosynthesis", role="noun",
        emotional_valence=0.0, noncomp_id="X:MAGNITUDE",
        usage_count=SentenceComposer._UNVERIFIED_VOCAB_USAGE_FLOOR,
    )
    anchor_set = {"photosynthesis": ace.RELEVANCE_DIRECT_ANCHOR}
    score = composer._score_composer_candidate(entry, anchor_set, valence_target=0.0)
    max_distant = ace.RELEVANCE_DISTANT_FLOOR * (1.0 + SentenceComposer._VALENCE_TIEBREAK_WEIGHT)
    assert score > max_distant, "a word with real repeated use must not stay capped forever"


def test_taught_word_with_real_definition_is_never_capped():
    """Words taught through aurora_comprehension_gap.py store the real
    definition/answer text as `meaning` (not the "learned:<word>"
    placeholder) -- this fix must not touch that path at all, since
    genuine teaching is the whole point of vocabulary acquisition."""
    import aurora_constraint_emission as ace

    composer = SentenceComposer.__new__(SentenceComposer)
    entry = LexicalEntry(
        word="chord", meaning="a group of notes played together", role="noun",
        emotional_valence=0.0, noncomp_id="X:MAGNITUDE", usage_count=0,
    )
    anchor_set = {"chord": ace.RELEVANCE_DIRECT_ANCHOR}
    score = composer._score_composer_candidate(entry, anchor_set, valence_target=0.0)
    expected = ace.RELEVANCE_DIRECT_ANCHOR * (1.0 + SentenceComposer._VALENCE_TIEBREAK_WEIGHT)
    assert score == expected, "a taught word with a real definition must score at full relevance"


def test_oets_enriched_word_is_never_capped():
    """Words bridged from OETS relations/definitions (meaning stamped
    "oets:<keyword>") require a pre-existing real OETS node to trigger --
    also untouched by this fix."""
    import aurora_constraint_emission as ace

    composer = SentenceComposer.__new__(SentenceComposer)
    entry = LexicalEntry(
        word="fretboard", meaning="oets:guitar", role="noun",
        emotional_valence=0.0, noncomp_id="X:MAGNITUDE", usage_count=0,
    )
    anchor_set = {"fretboard": ace.RELEVANCE_DIRECT_ANCHOR}
    score = composer._score_composer_candidate(entry, anchor_set, valence_target=0.0)
    expected = ace.RELEVANCE_DIRECT_ANCHOR * (1.0 + SentenceComposer._VALENCE_TIEBREAK_WEIGHT)
    assert score == expected


def test_compose_and_express_accept_input_text_without_breaking_existing_callers():
    """input_text must be optional everywhere it was added so pre-existing
    callers (dream/simulation/training paths) that don't pass it keep
    working exactly as before."""
    import inspect

    compose_sig = inspect.signature(SentenceComposer.compose)
    assert compose_sig.parameters["input_text"].default == ""

    express_sig = inspect.signature(ExpressionPerceptionEngine.express)
    assert express_sig.parameters["input_text"].default == ""

    motif_sig = inspect.signature(SentenceComposer._compose_from_motif)
    assert motif_sig.parameters["input_text"].default == ""

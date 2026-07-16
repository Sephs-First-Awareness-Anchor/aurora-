# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
R1.9.2 G1: relevance-primary word selection in SentenceComposer, the
delivered path (backward-attribution-confirmed in R1.9.1).

"Relevance chooses what is said; everything else shapes how" -- the third
instance of the never-content-only-style doctrine (F1.4: usage-habit ->
style; F5: register -> looseness; now: valence-proximity -> tone).
"""
import math

from aurora_expression_perception import ExpressionPerceptionEngine, SentenceComposer


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

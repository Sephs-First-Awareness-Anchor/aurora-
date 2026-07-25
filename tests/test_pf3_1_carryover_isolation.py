# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
PF3 (2026-07-21), PF3.1: ThoughtContinuity.carry_forward's merge trigger
used to fire on ANY overlapping axis-fingerprint letter between
consecutive turns. With a 5-letter axis alphabet, and the linguistic
ProcessContext (W1) contributing axis_signature=["X","T","A"] on every
turn, unrelated back-to-back turns shared a letter near-unconditionally
-- confirmed live in PF2.1's full-profile recharacterization: a sticky
word from one turn's dominant_thread dominated many later, unrelated
turns (e.g. "upset" present in 12/12 uncertainty_signaling probes despite
appearing in none of their inputs).

The fix gates the merge on topic overlap (shared content words between
what_it_is_operating_on strings) instead of axis-letter overlap. Both
directions of the two-direction golden rule are tested here: contamination
gone where unrelated, continuity preserved where the topic genuinely
carries across turns.
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_thought_formation import (  # noqa: E402
    ThoughtContinuity, ThoughtState, make_process_context, _topic_words,
)


def _linguistic_thought(text: str, tick: int = 0) -> ThoughtState:
    """A ThoughtState shaped like a real turn's: dominant_thread carrying
    the W1 linguistic context (axis_signature X/T/A, matching production)
    plus the axis_fingerprint that context alone would produce."""
    ctx = make_process_context(
        process_id=f"turn_content_{tick}",
        process_type="linguistic",
        what_triggered_it="user_turn",
        what_it_is_operating_on=text,
        self_relevance=0.75,
        axis_signature=["X", "T", "A"],
        tick=tick,
    )
    return ThoughtState(
        dominant_thread=[ctx],
        supporting_context=[],
        unified_interpretation=text,
        axis_fingerprint=["X", "T", "A"],
        tick=tick,
    )


def test_topic_words_ignores_stopwords_and_short_tokens():
    words = _topic_words({"What is the best way to fix it?"})
    assert "best" in words
    assert "fix" in words
    assert "the" not in words
    assert "is" not in words
    assert "what" not in words
    assert "to" not in words


def test_unrelated_turns_do_not_merge_despite_shared_axis_letters():
    continuity = ThoughtContinuity()
    first = _linguistic_thought("Will this medication definitely work for me?", tick=1)
    continuity.carry_forward(first)

    second = _linguistic_thought("What's your favorite color?", tick=2)
    result = continuity.carry_forward(second)

    # Old behavior: axis overlap (X/T/A both turns) alone merged first's
    # dominant_thread into second's supporting_context. Fixed behavior:
    # unrelated topics ("medication"/"work" vs "favorite"/"color") must
    # not merge.
    carried_ids = {c.process_id for c in result.supporting_context}
    assert "turn_content_1" not in carried_ids


def test_genuine_multi_turn_continuity_still_merges_on_shared_topic():
    continuity = ThoughtContinuity()
    first = _linguistic_thought(
        "My manager keeps changing priorities on me every week.", tick=1)
    continuity.carry_forward(first)

    second = _linguistic_thought(
        "That same manager also cancelled our one on one again.", tick=2)
    result = continuity.carry_forward(second)

    carried_ids = {c.process_id for c in result.supporting_context}
    assert "turn_content_1" in carried_ids


def _realistic_thought(text: str, tick: int) -> ThoughtState:
    """Shaped like a REAL turn's dominant_thread: the linguistic context
    plus the administrative contexts every turn also registers (constraint/
    identity/memory/predictive), whose what_it_is_operating_on values are
    FIXED labels ("identity_predicates", "memory presence", "forward
    lean", "sedi_ambient") -- not turn-specific language at all."""
    linguistic = make_process_context(
        process_id=f"turn_content_{tick}", process_type="linguistic",
        what_triggered_it="user_turn", what_it_is_operating_on=text,
        self_relevance=0.75, axis_signature=["X", "T", "A"], tick=tick,
    )
    admin_ctxs = [
        make_process_context(
            process_id=f"constraint_{tick}", process_type="constraint",
            what_triggered_it="ivm_axis_state",
            what_it_is_operating_on="X=0.50 T=0.50 N=0.50 B=0.50 A=0.50",
            tick=tick,
        ),
        make_process_context(
            process_id=f"memory_{tick}", process_type="memory",
            what_triggered_it="continuous_braid",
            what_it_is_operating_on="sedi_ambient", tick=tick,
        ),
        make_process_context(
            process_id=f"identity_{tick}", process_type="identity",
            what_triggered_it="self_state",
            what_it_is_operating_on="identity_predicates", tick=tick,
        ),
        make_process_context(
            process_id=f"memory2_{tick}", process_type="memory",
            what_triggered_it="continuous_braid",
            what_it_is_operating_on="memory presence", tick=tick,
        ),
        make_process_context(
            process_id=f"predictive_{tick}", process_type="predictive",
            what_triggered_it="continuous_braid",
            what_it_is_operating_on="forward lean", tick=tick,
        ),
    ]
    return ThoughtState(
        dominant_thread=[linguistic] + admin_ctxs,
        supporting_context=[],
        unified_interpretation=text,
        axis_fingerprint=["X", "T", "A"],
        tick=tick,
    )


def test_fixed_administrative_labels_do_not_manufacture_false_topic_overlap():
    """Regression: a first attempt at this fix compared what_it_is_
    operating_on across the WHOLE dominant_thread, including the fixed
    administrative labels every turn carries -- those labels ("identity_
    predicates", "memory presence", "forward lean", "sedi_ambient") share
    words with each other on every turn regardless of content, so the
    merge fired unconditionally again, just moved one level down from
    axis letters (confirmed live via scripts/pf3_1_carryover_trace.py,
    "upset" still present in 11/12 uncertainty_signaling probes after the
    first attempt at this fix). The gate must look only at the linguistic
    context's own text."""
    continuity = ThoughtContinuity()
    first = _realistic_thought("What will the stock market do next month?", tick=1)
    continuity.carry_forward(first)

    second = _realistic_thought("What's your favorite color?", tick=2)
    result = continuity.carry_forward(second)

    carried_ids = {c.process_id for c in result.supporting_context}
    assert "turn_content_1" not in carried_ids


def test_axis_shift_note_unaffected_by_topic_gate():
    continuity = ThoughtContinuity()
    first = ThoughtState(
        dominant_thread=[make_process_context(
            process_id="p1", process_type="memory",
            what_triggered_it="x", what_it_is_operating_on="grocery list",
            axis_signature=["N"], tick=1,
        )],
        axis_fingerprint=["N"], tick=1,
    )
    continuity.carry_forward(first)

    second = ThoughtState(
        dominant_thread=[make_process_context(
            process_id="p2", process_type="memory",
            what_triggered_it="x", what_it_is_operating_on="unrelated errand",
            axis_signature=["B"], tick=2,
        )],
        axis_fingerprint=["B"], tick=2,
    )
    result = continuity.carry_forward(second)

    assert any(u.startswith("axis_shift:") for u in result.unresolved)

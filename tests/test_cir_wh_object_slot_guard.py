"""Regression coverage for bare interrogatives leaking into OBJECT slots.

A bare question marker may identify information requested by the user, but it
is not itself the answer-bearing object of a declarative proposition.  The
final slot-binding boundary must reject it regardless of which frame producer
supplied it.  Embedded clauses remain valid content.
"""
from types import SimpleNamespace

import pytest

from aurora_expression_perception import (
    LexicalEntry,
    LexicalMemory,
    SentenceComposer,
    VoiceGenome,
    infer_word_role,
)
from aurora_internal.aurora_proposition_frame import (
    PropositionFrame,
    _frame_from_anchor,
    _frame_from_claims,
    _frame_from_turn_local_claims,
)


BARE_INTERROGATIVES = (
    "who", "whom", "whose", "what", "which", "where", "when", "why", "how",
)


def _composer():
    return SentenceComposer(LexicalMemory(), VoiceGenome())


@pytest.mark.parametrize("word", BARE_INTERROGATIVES)
def test_bare_interrogative_never_infers_as_noun(word):
    assert infer_word_role(word) != "noun"
    assert infer_word_role(f"{word}?") != "noun"


@pytest.mark.parametrize("word", BARE_INTERROGATIVES)
def test_object_slot_rejects_bare_interrogative_from_direct_frame(word):
    frame = PropositionFrame(subject="Aurora", relation="make", obj=word, source="probe")
    result = _composer()._bind_slot_from_frame(
        "object", frame, ["agent", "action"], ["I", "make"]
    )
    assert result is None


def test_object_slot_preserves_embedded_interrogative_clause():
    frame = PropositionFrame(
        subject="I", relation="know", obj="who made Aurora", source="probe"
    )
    result = _composer()._bind_slot_from_frame(
        "object", frame, ["agent", "action"], ["I", "know"]
    )
    assert result == "who made aurora"


class _Substrate:
    def __init__(self, obj):
        self.nodes = {
            "claim": {
                "turn": 1,
                "subject": "Aurora",
                "relation": "make",
                "object": obj,
                "confidence": 0.9,
            }
        }

    @staticmethod
    def score_claim(node):
        return float(node.get("confidence", 0.0))


@pytest.mark.parametrize("word", BARE_INTERROGATIVES)
def test_claim_frame_route_cannot_bind_bare_interrogative(word):
    working_memory = SimpleNamespace(turn_count=1, proposition_substrate=_Substrate(word))
    frame = _frame_from_claims({"working_memory": working_memory})
    assert frame is not None
    assert frame.obj == ""
    result = _composer()._bind_slot_from_frame(
        "object", frame, ["agent", "action"], ["I", "make"]
    )
    assert result is None


@pytest.mark.parametrize("word", BARE_INTERROGATIVES)
def test_turn_local_claim_route_cannot_bind_bare_interrogative(word):
    working_memory = SimpleNamespace(
        turn_count=1,
        _turn_local_claims=[{
            "turn": 1,
            "subject": "Aurora",
            "relation": "make",
            "object": word,
        }],
    )
    frame = _frame_from_turn_local_claims({"working_memory": working_memory})
    assert frame is not None
    assert frame.obj == ""
    result = _composer()._bind_slot_from_frame(
        "object", frame, ["agent", "action"], ["I", "make"]
    )
    assert result is None


@pytest.mark.parametrize("word", BARE_INTERROGATIVES)
def test_anchor_frame_route_cannot_bind_bare_interrogative(word):
    state = SimpleNamespace(noncomp_input_state={"anchor": word})
    frame = _frame_from_anchor({}, state)
    assert frame is not None
    assert frame.obj == ""
    assert frame.topic == word
    result = _composer()._bind_slot_from_frame(
        "object", frame, ["agent", "action"], ["I", "consider"]
    )
    assert result is None


@pytest.mark.parametrize("word", BARE_INTERROGATIVES)
def test_stale_lexicon_noun_entry_cannot_reenter_through_fallback(word):
    composer = _composer()
    stale = LexicalEntry(
        word=word,
        meaning=f"legacy:{word}",
        role="noun",
        emotional_valence=0.0,
    )
    assert composer._pos_ok(stale, "object") is False
    assert composer._pos_ok(stale, "agent") is False
    assert composer._pos_ok(stale, "descriptor") is False


@pytest.mark.parametrize("word", BARE_INTERROGATIVES)
def test_legacy_primitive_template_filler_rejects_stale_interrogative(word):
    composer = _composer()
    stale = LexicalEntry(
        word=word,
        meaning=f"legacy:{word}",
        role="noun",
        emotional_valence=0.0,
    )
    composer.lexicon.entries = {word: stale}
    composer.lexicon._rebuild_role_index()
    chosen = composer._fill_primitive_slot(
        "N", ["noun"], "neutral", 0.5, -1.0, 1.0
    )
    assert chosen == ""

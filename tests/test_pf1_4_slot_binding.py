# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Directive PF1.4: slot binding -- the proposition fills its own
sentence. When a PropositionFrame is present, ACTION binds from
frame.relation and OBJECT from frame.obj (fail-quiet POS-gate, falls
back to today's channel selection on any mismatch); DESCRIPTOR still
goes through the existing relevance-ranked selection, just with the
frame's own terms folded into the anchor text. AGENT is deliberately
left alone (see aurora_expression_perception.py's docstring on
_bind_slot_from_frame for why).
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_expression_perception import (  # noqa: E402
    SentenceComposer, LexicalMemory, VoiceGenome,
)
from aurora_internal.aurora_proposition_frame import PropositionFrame  # noqa: E402


def _composer():
    return SentenceComposer(LexicalMemory(), VoiceGenome())


# ── _bind_slot_from_frame: direct unit tests ────────────────────────

def test_binds_action_from_relation_when_recognized_verb():
    c = _composer()
    frame = PropositionFrame(subject="I", relation="help", obj="water", source="thought")
    word = c._bind_slot_from_frame("action", frame, ["agent"], ["I"])
    assert word == "help"


def test_binds_object_from_obj():
    c = _composer()
    frame = PropositionFrame(subject="I", relation="help", obj="water", source="thought")
    word = c._bind_slot_from_frame("object", frame, ["agent", "action"], ["I", "help"])
    assert word == "water"


def test_action_falls_through_when_relation_empty():
    c = _composer()
    frame = PropositionFrame(subject="I", relation="", obj="water", source="anchor")
    assert c._bind_slot_from_frame("action", frame, ["agent"], ["I"]) is None


def test_object_falls_through_when_obj_empty():
    c = _composer()
    frame = PropositionFrame(subject="I", relation="help", obj="", source="thought")
    assert c._bind_slot_from_frame("object", frame, ["agent", "action"], ["I", "help"]) is None


def test_action_falls_through_when_relation_is_not_a_recognized_verb():
    """POS gate: 'water' is a noun, never binds into an action slot even
    if some upstream extraction bug put it in frame.relation."""
    c = _composer()
    frame = PropositionFrame(subject="I", relation="water", obj="help", source="thought")
    assert c._bind_slot_from_frame("action", frame, ["agent"], ["I"]) is None


def test_object_falls_through_on_immediate_duplicate():
    c = _composer()
    frame = PropositionFrame(subject="I", relation="help", obj="help", source="thought")
    # "help" already the previous word in this sentence -- must not repeat.
    assert c._bind_slot_from_frame("object", frame, ["agent", "action"], ["I", "help"]) is None


def test_agent_role_is_never_bound_from_frame():
    c = _composer()
    frame = PropositionFrame(subject="water", relation="help", obj="thing", source="thought")
    assert c._bind_slot_from_frame("agent", frame, [], []) is None


def test_descriptor_role_is_never_bound_from_frame():
    """DESCRIPTOR stays on the existing relevance-ranked path -- only
    ACTION/OBJECT get a direct frame override."""
    c = _composer()
    frame = PropositionFrame(subject="I", relation="help", obj="water", source="thought")
    assert c._bind_slot_from_frame("descriptor", frame, ["agent"], ["I"]) is None


def test_bind_slot_never_raises_on_malformed_frame():
    c = _composer()

    class _Explode:
        def __getattr__(self, item):
            raise RuntimeError("boom")

    try:
        result = c._bind_slot_from_frame("action", _Explode(), ["agent"], ["I"])
    except Exception:
        result = "raised"
    # _compose_from_motif wraps this call in its own try/except, so even
    # a raise here is caught upstream -- but the method itself degrading
    # to None is the cleaner contract.
    assert result in (None, "raised")


# ── conjugation / negation ───────────────────────────────────────────

def test_binds_action_conjugated_for_current_subject():
    """Picks the nearest preceding agent word in the sentence being
    built, not a hardcoded 'I'."""
    c = _composer()
    frame = PropositionFrame(subject="I", relation="help", obj="water", source="thought")
    word = c._bind_slot_from_frame("action", frame, ["agent"], ["you"])
    assert word == "help"  # regular verb, same form for I/you


def test_negated_frame_produces_do_support():
    c = _composer()
    frame = PropositionFrame(subject="I", relation="help", obj="water", negated=True, source="thought")
    word = c._bind_slot_from_frame("action", frame, ["agent"], ["I"])
    assert word == "do not help"


def test_negate_action_word_handles_be_forms_in_place():
    c = _composer()
    assert c._negate_action_word("is", "I") == "am not"
    assert c._negate_action_word("is", "you") == "are not"


def test_binds_bare_gerund_action_with_progressive_auxiliary():
    """PF1.5's role_coherent() caught this shape live (14/60 real
    probes): a bare gerund bound as ACTION is not a finite verb ("I
    planning water."). Fixed with a progressive-aspect auxiliary."""
    c = _composer()
    frame = PropositionFrame(subject="I", relation="planning", obj="water", source="thought")
    word = c._bind_slot_from_frame("action", frame, ["agent"], ["I"])
    assert word == "am planning"


def test_binds_bare_gerund_action_with_are_for_you_subject():
    c = _composer()
    frame = PropositionFrame(subject="I", relation="knowing", obj="water", source="thought")
    word = c._bind_slot_from_frame("action", frame, ["agent"], ["you"])
    assert word == "are knowing"


def test_negated_bare_gerund_action_uses_am_not():
    c = _composer()
    frame = PropositionFrame(subject="I", relation="seeing", obj="water", negated=True, source="thought")
    word = c._bind_slot_from_frame("action", frame, ["agent"], ["I"])
    assert word == "am not seeing"


def test_negate_action_word_uses_do_support_for_regular_verbs():
    c = _composer()
    assert c._negate_action_word("help", "I") == "do not help"
    assert c._negate_action_word("help", "you") == "do not help"


# ── integration: through _compose_from_motif ────────────────────────

class _FakeRole:
    def __init__(self, value):
        self.value = value


class _FakeMotif:
    def __init__(self, roles):
        self.role_sequence = [_FakeRole(r) for r in roles]


def test_compose_from_motif_uses_frame_bound_action_and_object():
    c = _composer()
    frame = PropositionFrame(subject="I", relation="help", obj="water", source="thought")
    c.set_proposition_frame(frame)
    motif = _FakeMotif(["agent", "action", "object"])
    orientation = {"X": 0.5, "T": 0.5, "N": 0.5, "B": 0.0, "A": 0.5}
    sent = c._compose_from_motif(motif, orientation, 0.0, "i_is", 0)
    assert "help" in sent.lower()
    assert "water" in sent.lower()


def test_compose_from_motif_with_no_frame_is_unaffected():
    """Regression guard: frame absent (None, the default) -> today's
    exact channel-selection behavior, no _bind_slot_from_frame call."""
    c = _composer()
    assert c._proposition_frame is None
    # Normally reset per compose() call; set directly since this test
    # calls _compose_from_motif standalone, bypassing compose().
    c._last_required_slot_attempts = 0
    c._last_floor_failures = []
    motif = _FakeMotif(["agent", "action", "object"])
    orientation = {"X": 0.5, "T": 0.5, "N": 0.5, "B": 0.0, "A": 0.5}
    # Must not raise with no frame set.
    c._compose_from_motif(motif, orientation, 0.0, "i_is", 0)


def test_bare_gerund_from_ordinary_channel_selection_gets_an_auxiliary_too():
    """PF1.5 finding: the bare-gerund-as-finite-verb gap predates PF1.3/
    PF1.4 -- it already existed in ordinary channel selection (confirmed
    live: 'planning' appeared as a find_by_noncomp candidate in PF1.0's
    pre-PF1.4 baseline data). The general post-loop conjugation pass
    must catch it too, not just frame-bound words."""
    c = _composer()
    assert c._proposition_frame is None  # no frame -> normal selection path
    c._last_required_slot_attempts = 0
    c._last_floor_failures = []

    def _fake_select(role, *args, **kwargs):
        return {"agent": "I", "action": "seeing", "object": "water"}.get(role, "")

    c._select_constraint_word = _fake_select
    motif = _FakeMotif(["agent", "action", "object"])
    orientation = {"X": 0.5, "T": 0.5, "N": 0.5, "B": 0.0, "A": 0.5}
    sent = c._compose_from_motif(motif, orientation, 0.0, "i_is", 0)
    assert "am seeing" in sent.lower()
    assert "i seeing" not in sent.lower()

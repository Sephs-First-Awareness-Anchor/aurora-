# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Directive PF1.2: transport the PropositionFrame (PF1.1) and the
already-produced-but-orphaned ExpressionGuidance (audit finding F1)
onto the composer via the existing begin_expression() wire. Pure
transport -- compose() must not read either field yet, so delivered
text stays byte-identical this phase.
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_expression_perception import (  # noqa: E402
    SentenceComposer, LexicalMemory, VoiceGenome,
)
from aurora_braid_wiring import begin_expression  # noqa: E402
from aurora_thought_formation import ThoughtState  # noqa: E402


def _real_composer():
    return SentenceComposer(LexicalMemory(), VoiceGenome())


# ── SentenceComposer: defaults + setters ────────────────────────────

def test_composer_defaults_frame_and_guidance_to_none():
    c = _real_composer()
    assert c._proposition_frame is None
    assert c._expression_guidance is None


def test_set_proposition_frame_stores_value():
    c = _real_composer()
    sentinel = object()
    c.set_proposition_frame(sentinel)
    assert c._proposition_frame is sentinel


def test_set_expression_guidance_stores_value():
    c = _real_composer()
    sentinel = object()
    c.set_expression_guidance(sentinel)
    assert c._expression_guidance is sentinel


def test_set_proposition_frame_accepts_none():
    c = _real_composer()
    c.set_proposition_frame(object())
    c.set_proposition_frame(None)
    assert c._proposition_frame is None


# NOTE: this file previously carried a structural test asserting
# compose() referenced neither `_proposition_frame` nor
# `_expression_guidance` -- PF1.2's own "transport only, zero
# consumption" gate. PF1.3 (aurora_grammar_engine.py's
# best_for_proposition, wired into compose()'s motif-selection call)
# intentionally begins consuming `_proposition_frame`, superseding
# that gate by design. Removed rather than left to fail; PF1.3's own
# tests (tests/test_pf1_3_motif_selection.py) now cover consumption.


# ── begin_expression(): wiring through fakes ────────────────────────

class _FakePerception:
    def __init__(self, composer):
        self.composer = composer


def test_begin_expression_wires_anchor_frame_when_thought_has_no_triple():
    composer = _real_composer()
    thought = ThoughtState(unified_interpretation="", self_application="", confidence=0.5)
    systems = {
        "_current_thought_state": thought,
        "perception": _FakePerception(composer),
        "_last_noncomp_input": {"anchor": "guitar"},
    }
    begin_expression(systems)
    frame = systems.get("_proposition_frame")
    assert frame is not None
    assert frame.source == "anchor"
    assert frame.obj == "guitar"
    assert composer._proposition_frame is frame
    assert composer._expression_guidance is systems.get("_expression_guidance")


def test_begin_expression_wires_thought_frame_when_available():
    composer = _real_composer()
    thought = ThoughtState(
        unified_interpretation="I need to help with the water project",
        self_application="",
        confidence=0.72,
        dominant_thread=[],
    )
    systems = {
        "_current_thought_state": thought,
        "perception": _FakePerception(composer),
        "_last_noncomp_input": {"anchor": "should_not_win"},
    }
    begin_expression(systems)
    frame = systems.get("_proposition_frame")
    assert frame is not None
    assert frame.source == "thought"
    assert composer._proposition_frame is frame


def test_begin_expression_sets_none_frame_when_no_rung_available():
    composer = _real_composer()
    thought = ThoughtState(unified_interpretation="", self_application="", confidence=0.5)
    systems = {
        "_current_thought_state": thought,
        "perception": _FakePerception(composer),
    }
    begin_expression(systems)
    assert systems.get("_proposition_frame") is None
    assert composer._proposition_frame is None


def test_begin_expression_degrades_gracefully_with_no_composer():
    thought = ThoughtState(unified_interpretation="", self_application="", confidence=0.5)
    systems = {"_current_thought_state": thought, "perception": None}
    # Must not raise, must not crash the expression-layer wiring above it.
    begin_expression(systems)
    assert "_proposition_frame" not in systems


def test_begin_expression_degrades_gracefully_with_no_thought_state():
    systems = {"_current_thought_state": None}
    begin_expression(systems)
    assert systems.get("_expression_layer") is None
    assert "_proposition_frame" not in systems

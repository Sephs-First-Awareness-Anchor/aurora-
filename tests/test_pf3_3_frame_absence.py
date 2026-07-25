# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
PF3.3 scope extension (2026-07-21, at Sunni's explicit direction after a
3-pass live measurement showed the descriptor-neighborhood fix itself
was correct but the "material drop" gate genuinely wasn't met -- 9.22%
baseline vs a 9.98% 3-pass average, every single pass above baseline,
ruling out noise as the explanation).

Traced why (scripts/pf3_3_frame_absence_trace.py): begin_expression()
(aurora_braid_wiring.py) -- the only place composer._proposition_frame
gets built -- is gated in aurora.py behind `_perc_a5 and _resp_draft`,
and is SKIPPED whenever state.response_content is still empty at that
point in _run_reasoning_pipeline (heavily correlated with question-
shaped input: confirmed live, ALL 4 traced uncertainty_signaling-style
questions never called begin_expression at all). Those turns still
produce real delivered text, generated later via a SEPARATE call
(dual_question_pipeline -> gw._express() -> perception.express() ->
_build_expression() -> compose(), using the SAME composer instance
begin_expression targets -- gw.perception IS systems['perception'],
wired once at boot) -- but composer._proposition_frame was never
populated for it. 67% of surviving "clear"/"real" descriptor-repetition
instances traced directly to this gap; every frame-consuming fix in
this whole PF1-PF3 arc silently never applied to them.

ensure_proposition_frame_for_turn() is the extracted, reusable fix:
the frame-building portion of begin_expression(), callable
independently (and safely more than once per turn) wherever a
composer.compose() call is about to happen without begin_expression
having already run first.
"""
import os
import sys
import types

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_braid_wiring import (  # noqa: E402
    ensure_proposition_frame_for_turn, begin_expression,
)
from aurora_thought_formation import ThoughtState, make_process_context  # noqa: E402
from aurora_working_memory import WorkingMemory  # noqa: E402


class _FakeComposer:
    def __init__(self):
        self._proposition_frame = None
        self.set_calls = []
        self._expression_guidance = None

    def set_proposition_frame(self, frame):
        self.set_calls.append(frame)
        self._proposition_frame = frame

    def set_expression_guidance(self, guidance):
        self._expression_guidance = guidance


def _linguistic_thought_state(text: str) -> ThoughtState:
    ctx = make_process_context(
        process_id="turn_content_1", process_type="linguistic",
        what_triggered_it="user_turn", what_it_is_operating_on=text,
        self_relevance=0.75, axis_signature=["X", "T", "A"], tick=1,
    )
    return ThoughtState(dominant_thread=[ctx], axis_fingerprint=["X", "T", "A"], tick=1)


def test_builds_and_sets_frame_from_thought_state():
    composer = _FakeComposer()
    working_memory = WorkingMemory()
    working_memory.turn_count = 1
    systems = {
        "_current_thought_state": _linguistic_thought_state(
            "He's a bit nervous around new people."),
        "perception": types.SimpleNamespace(composer=composer),
        "working_memory": working_memory,
    }
    ensure_proposition_frame_for_turn(systems)
    assert composer._proposition_frame is not None
    assert composer._proposition_frame.source == "thought"
    assert systems["_proposition_frame"] is composer._proposition_frame


def test_safe_to_call_more_than_once_per_turn():
    """The whole point: this must be callable a second time in the SAME
    turn (once from begin_expression's normal flow if it runs, once
    from the dual_question_pipeline call site) without error or
    duplicated side effects beyond a fresh build_frame() call."""
    composer = _FakeComposer()
    systems = {
        "_current_thought_state": _linguistic_thought_state("What's your favorite color?"),
        "perception": types.SimpleNamespace(composer=composer),
        "working_memory": WorkingMemory(),
    }
    ensure_proposition_frame_for_turn(systems)
    first_frame = composer._proposition_frame
    ensure_proposition_frame_for_turn(systems)
    second_frame = composer._proposition_frame
    assert first_frame is not None
    assert second_frame is not None
    assert first_frame.subject == second_frame.subject
    assert len(composer.set_calls) == 2


def test_degrades_gracefully_with_no_thought_state():
    composer = _FakeComposer()
    systems = {"_current_thought_state": None, "perception": types.SimpleNamespace(composer=composer)}
    ensure_proposition_frame_for_turn(systems)  # must not raise
    assert systems["_proposition_frame"] is None


def test_degrades_gracefully_with_no_perception():
    systems = {"_current_thought_state": None}
    ensure_proposition_frame_for_turn(systems)  # must not raise


def test_begin_expression_still_sets_frame_via_the_shared_helper():
    """Regression: begin_expression() itself must still populate the
    frame exactly as before this refactor (extracted into a shared
    helper, not duplicated)."""
    composer = _FakeComposer()
    systems = {
        "_current_thought_state": _linguistic_thought_state(
            "He's a bit nervous around new people."),
        "perception": types.SimpleNamespace(composer=composer),
        "working_memory": WorkingMemory(),
    }
    begin_expression(systems)
    assert composer._proposition_frame is not None
    assert composer._proposition_frame.source == "thought"

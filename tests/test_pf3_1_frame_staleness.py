# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
PF3 (2026-07-21), PF3.1 (third finding): fixing the co-occurrence-relation
hub leak (context_keywords enrichment) still left "upset" persisting
across unrelated turns, and unlike "planning" it never appeared in
word_sources at all -- ruling out the ordinary candidate-scoring paths
entirely. Tracing begin_expression() (aurora_braid_wiring.py) directly
(scripts/pf3_1_frame_staleness_trace.py) found composer._proposition_frame
is only ever refreshed inside begin_expression(), which aurora.py's own
caller skips on some turns (empty response_content, a preserved/cached
literal response, etc.) -- confirmed live: build_frame() was reached on
only 2 of 6 traced turns; the other 4 silently reused whichever turn last
built a frame. _bind_slot_from_frame (aurora_expression_perception.py)
then binds that stale frame's .obj/.relation directly into slot-filling,
bypassing word_sources entirely (that instrumentation only wraps the
ordinary candidate-scoring paths, never _bind_slot_from_frame's own
binds) -- exactly matching "upset" being invisible there.

reset_proposition_frame_for_turn() is the fix: called unconditionally at
the start of every turn (aurora.py's _run_reasoning_pipeline), before
begin_expression may or may not run.
"""
import os
import sys
from types import SimpleNamespace

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_braid_wiring import reset_proposition_frame_for_turn  # noqa: E402


class _FakeComposer:
    def __init__(self, frame):
        self._proposition_frame = frame
        self.set_calls = []

    def set_proposition_frame(self, frame):
        self.set_calls.append(frame)
        self._proposition_frame = frame


def test_clears_systems_proposition_frame():
    systems = {"_proposition_frame": "stale_frame_object"}
    reset_proposition_frame_for_turn(systems)
    assert systems["_proposition_frame"] is None


def test_clears_composer_proposition_frame_when_composer_present():
    composer = _FakeComposer(frame="stale_frame_object")
    systems = {"_proposition_frame": "stale", "perception": SimpleNamespace(composer=composer)}
    reset_proposition_frame_for_turn(systems)
    assert composer._proposition_frame is None
    assert composer.set_calls == [None]


def test_degrades_gracefully_with_no_perception_key():
    systems = {}
    reset_proposition_frame_for_turn(systems)  # must not raise
    assert systems["_proposition_frame"] is None


def test_degrades_gracefully_when_composer_is_none():
    systems = {"perception": SimpleNamespace(composer=None)}
    reset_proposition_frame_for_turn(systems)  # must not raise
    assert systems["_proposition_frame"] is None


def test_degrades_gracefully_when_perception_has_no_composer_attr():
    systems = {"perception": SimpleNamespace()}
    reset_proposition_frame_for_turn(systems)  # must not raise
    assert systems["_proposition_frame"] is None

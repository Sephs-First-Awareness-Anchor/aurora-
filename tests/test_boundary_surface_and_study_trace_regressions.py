"""Regression tests for two real bugs found from a live device report
(2026-08-29): Aurora going silent on ordinary conversational input, and
her boundary-surface replies echoing a fabricated word ("be") the user
never said.

Both bugs were traced using Build 774's new on-device Live Turn
Diagnostics panel (pre_sanitize_content), which showed exactly what
aurora.py produced before Android's cleanup ran.
"""
from __future__ import annotations

import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANDROID_PY_DIR = os.path.join(REPO_ROOT, "flutter_app", "android", "app", "src", "main", "python")

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if ANDROID_PY_DIR not in sys.path:
    sys.path.insert(0, ANDROID_PY_DIR)

from aurora_internal.aurora_constraint_semantic_continuity import _question_boundary_surface


def test_question_boundary_surface_echoes_the_word_actually_used():
    """_base_relation() correctly normalizes is/are/was/were to 'be' for
    internal matching (the same irregular-verb table it already uses for
    has->have, does->do, etc.) -- but that normalized lemma must never be
    read back to the user verbatim as if it were their own word. The
    live device trace: "when I say Aurora that is me saying your name"
    -> relation="is" -> displayed as "...described as be." -- the user
    never said "be"."""
    form = {"subject": "that", "relation": "is", "obj": "", "unknown_role": "manner"}
    result = _question_boundary_surface(form)
    assert "described as be" not in result
    assert "described as is" in result


def test_question_boundary_surface_still_normalizes_for_internal_paths():
    """The fix must not touch _base_relation()'s own normalization --
    only which value the final 'described as X' sentence displays. A verb
    that maps to a distinct internal comparison target (e.g. "requires"
    -> "require", used by the unknown=="cause"/relation_as_process path)
    must still resolve through the same relation the rest of the function
    was already built around."""
    form = {"subject": "the plan", "relation": "requires", "obj": "budget", "unknown_role": "cause"}
    result = _question_boundary_surface(form)
    assert "requiring" in result  # relation_as_process still derives from the base form


def test_study_trace_regex_preserves_ordinary_sentences():
    """Aurora's real reply to "okay your name is Aurora" -- "I understand
    what you are saying about okay your." -- was being deleted whole by
    _STUDY_TRACE_RE because its trailing [^.!?\\n]*[.!?]? swallowed
    everything up to the next sentence boundary, however far away. A
    real sentence that happens to open the same way as the internal-leak
    shape it targets must survive."""
    pattern = re.compile(
        r'\bI\s+understand\s+(?:what|who|where|when|how)\s+\w+\s+(?:means?|is|are|here)\b'
        r'\s*[.!?]?\s*\Z',
        re.IGNORECASE,
    )
    real_sentences = [
        "I understand what you are saying about okay your.",
        "I understand how this is important to consider.",
        "I understand who you are talking about today.",
        "I understand what you are talking about",
    ]
    for text in real_sentences:
        assert pattern.sub('', text).strip(), f"real sentence wrongly wiped: {text!r}"


def test_study_trace_regex_still_strips_genuine_leaked_traces():
    """The narrow, self-contained internal-trace shape this regex exists
    to catch must still be caught -- the fix only removes the false
    positives, not the original detection."""
    pattern = re.compile(
        r'\bI\s+understand\s+(?:what|who|where|when|how)\s+\w+\s+(?:means?|is|are|here)\b'
        r'\s*[.!?]?\s*\Z',
        re.IGNORECASE,
    )
    leaked_traces = [
        "I understand what glorp means.",
        "I understand what glorp means",
        "I understand what glorp is.",
        "I understand who X is.",
    ]
    for text in leaked_traces:
        assert pattern.sub('', text).strip() == "", f"genuine leak no longer stripped: {text!r}"

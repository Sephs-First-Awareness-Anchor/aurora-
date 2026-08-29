"""Regression tests for the two behavior changes requested after the
suppression/"be"-echo bugs were fixed: Aurora should attempt a real,
checkable interpretation at an unresolved boundary instead of a bare
admission of failure ("try, fail, correct course" -- an existing
standing direction already applied to referent/pronoun resolution in
aurora_referent_hypothesis.py, now extended to the question/directive
boundary-surface fallback), and a direct greeting prefix ("hey Aurora,")
should not derail parsing of the real question underneath it.
"""
from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import aurora
from aurora_internal.aurora_constraint_semantic_continuity import (
    _directive_boundary_surface,
    _question_boundary_surface,
    extract_relational_form,
)
from aurora_boundary_hypothesis import check_and_resolve_pending_boundary_hypothesis


def test_question_boundary_unchanged_without_systems():
    """Every existing caller that doesn't pass systems (e.g.
    aurora_communication_emergence.py) must see byte-for-byte identical
    behavior to before this change."""
    form = {"subject": "that", "relation": "is", "obj": "", "unknown_role": "manner"}
    result = _question_boundary_surface(form)
    assert "I do not yet have enough grounded information" in result


def test_question_boundary_attempts_and_registers_with_systems():
    systems = {}
    form = {"subject": "that", "relation": "is", "obj": "", "unknown_role": "manner"}
    result = _question_boundary_surface(form, systems=systems)
    assert "I do not yet have enough grounded information" not in result
    assert '"is"' in result
    pending = systems.get("_pending_boundary_hypothesis")
    assert pending and pending["relation"] == "is"


def test_directive_boundary_attempts_and_registers_with_systems():
    systems = {}
    form = {"relation": "tell", "obj": "me", "complement": "about yourself"}
    result = _directive_boundary_surface(form, systems=systems)
    assert "I do not yet have enough grounded information" not in result
    assert systems.get("_pending_boundary_hypothesis") is not None


def test_boundary_hypothesis_correction_is_logged_and_cleared():
    systems = {}
    form = {"subject": "the plan", "relation": "requires", "obj": "budget"}
    _question_boundary_surface(form, systems=systems)
    assert systems.get("_pending_boundary_hypothesis") is not None

    outcome = check_and_resolve_pending_boundary_hypothesis(systems, "no, that's not what I meant")
    assert outcome["corrected"] is True
    assert systems.get("_pending_boundary_hypothesis") is None


def test_boundary_hypothesis_confirmation_is_logged():
    systems = {}
    form = {"subject": "the plan", "relation": "requires", "obj": "budget"}
    _question_boundary_surface(form, systems=systems)

    outcome = check_and_resolve_pending_boundary_hypothesis(systems, "yes exactly")
    assert outcome["corrected"] is False


def test_vocative_prefix_stripped_leaving_real_question():
    assert aurora._strip_vocative_address("Hey Aurora, what's up?") == "what's up?"
    assert aurora._strip_vocative_address("well hey Aurora how are you") == "how are you"


def test_vocative_stripping_leaves_pure_greetings_and_unrelated_text_alone():
    """No real content remains after stripping -> leave untouched (there
    is nothing to hand off to). No vocative present -> leave untouched."""
    assert aurora._strip_vocative_address("hey aurora") == "hey aurora"
    assert aurora._strip_vocative_address("okay your name is Aurora") == "okay your name is Aurora"
    assert aurora._strip_vocative_address("Aurora is a great name") == "Aurora is a great name"


def test_vocative_stripping_fixes_the_live_device_parse():
    """The exact live-device failure: "Hey Aurora, what's up?" parsed
    with subject="Hey Aurora" -- the address itself swallowed into the
    subject slot, and "well hey Aurora how are you" swallowed the WH-word
    "how" into the subject too, losing wellbeing_query's own
    self_subject/state_relation/manner shape entirely."""
    before = extract_relational_form("well hey Aurora how are you", feed_lexical_grounding=False)
    assert before["subject"] != "you"

    stripped = aurora._strip_vocative_address("well hey Aurora how are you")
    after = extract_relational_form(stripped, feed_lexical_grounding=False)
    assert after["subject"] == "you"
    assert after["relation"] == "are"
    assert after["unknown_role"] == "manner"

#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
test_receiver_loop.py -- the receiver verdict that every learning loop waits on.

2026-11-07 audit: communication emergence (13 trials), lexical grounding (49
trials) and grammar motifs (3,616) had ZERO promotions.  All of them are
gated on the next-turn receiver verdict, which (a) used one global pending
reply, so with several conversations the verdict landed on the wrong reply,
and (b) counted almost every natural reply as indeterminate.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from aurora_internal.aurora_understanding_contract import (  # noqa: E402
    RuntimeUnderstandingContract, _receiver_reconstructed)
import aurora  # noqa: E402


# -- uptake ------------------------------------------------------------------------

@pytest.mark.parametrize("summary,heard,receiver,expected", [
    # she contributed "want"/"did"; the receiver says them back
    ("I want music. I did music.", "Do you like music?", "Oh, you want music? What kind?", True),
    # receiver only repeats words that were already in the question
    ("I want music. I did music.", "Do you like music?", "Music is great! Do you like it?", False),
    # rich reconstruction
    ("I am boiling rain. I am clouds.", "Rain is water from clouds.", "Ha, boiling? Rain is cool, not boiling.", True),
    # silence: nothing contributed
    ("", "Do you like music?", "Do you like music?", False),
    # unrelated polite reply
    ("I, favorite. color.", "What's your favorite color?", "That sounds lovely! What's new?", False),
])
def test_uptake_is_her_contribution_said_back(summary, heard, receiver, expected):
    pending = {"summary": summary, "heard_text": heard}
    assert _receiver_reconstructed(pending, receiver.lower()) is expected


def test_reconstructed_is_a_positive_verdict():
    systems = {}
    outcome = aurora._classify_validated_communication(
        systems, {"accuracy": {"label": "reconstructed", "score": 0.86}}, "so you want music?")
    assert outcome["outcome_kind"] == "positive"


# -- per-conversation pending ---------------------------------------------------------

def _pending(session, summary, heard="hi"):
    return {"response_id": f"R:{session}", "session_id": session, "summary": summary,
            "heard_text": heard, "action_type": "", "expected_observation": "",
            "expected_topic": "", "expected_affect": "neutral", "contributors": {}}


def test_a_reply_waits_for_its_own_conversation(tmp_path):
    contract = RuntimeUnderstandingContract(state_dir=str(tmp_path), persist=False)
    contract.state["pending_validation"] = _pending("praxis_dm_gemini", "I want music. I did music.",
                                                    "Do you like music?")
    # Gemma speaks first: Gemini's pending reply must not be scored by her.
    contract._activate_session_pending("praxis_dm_gemma")
    assert contract.state["pending_validation"] == {}
    assert "praxis_dm_gemini" in contract.state["pending_validation_by_session"]
    # Gemini answers: her reply to Gemini comes back to be validated.
    contract._activate_session_pending("praxis_dm_gemini")
    assert contract.state["pending_validation"]["response_id"] == "R:praxis_dm_gemini"
    assert "praxis_dm_gemini" not in contract.state["pending_validation_by_session"]


def test_parked_conversations_are_bounded(tmp_path):
    contract = RuntimeUnderstandingContract(state_dir=str(tmp_path), persist=False)
    for i in range(contract.MAX_PARKED_SESSIONS + 10):
        contract.state["pending_validation"] = _pending(f"s{i}", "x y")
        contract._activate_session_pending(f"other{i}")
    assert len(contract.state["pending_validation_by_session"]) <= contract.MAX_PARKED_SESSIONS


def test_validation_end_to_end_through_the_contract(tmp_path):
    contract = RuntimeUnderstandingContract(state_dir=str(tmp_path), persist=False)
    contract.state["pending_validation"] = _pending("praxis_dm_gemini", "I want music. I did music.",
                                                    "Do you like music?")
    contract._activate_session_pending("praxis_dm_gemini")
    accuracy = contract._evaluate_previous_accuracy({}, "Oh, you want music? What kind?", {})
    assert accuracy["label"] == "reconstructed" and accuracy["score"] >= 0.80

# Authors: Sunni (Sir) Morningstar & Cael Devo
"""A recalled utterance informs her; it is never handed back whole as her answer."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("AURORA_SKIP_DEP_INSTALL", "1")

import aurora  # noqa: E402
from types import SimpleNamespace  # noqa: E402

CHATGPT = "Ha! That's exactly the spirit. Spoken like a true sovereign of chaos and clarity."


def _item(text, summary=""):
    return {"source": "historical_experience:historical_other_assistant",
            "summary": summary or text,
            "content": {"user_text": text}}


def _identity(monkeypatch):
    monkeypatch.setattr(aurora, "_render_runtime_intent", lambda systems, text, **kw: text)


def test_witnessed_utterance_is_not_returned_as_her_answer(monkeypatch):
    _identity(monkeypatch)
    out = aurora._answer_from_sedimemory_context("do you remember the spirit of that?", [_item(CHATGPT)], systems={})
    assert CHATGPT[:40] not in str(out or "")


def test_explicit_quote_request_still_quotes(monkeypatch):
    _identity(monkeypatch)
    out = aurora._answer_from_sedimemory_context("what did i say earlier?", [_item("I love fishing with my dad")], systems={})
    assert "fishing" in str(out or "").lower()


def test_full_text_summary_over_a_truncated_stored_utterance_is_not_returned(monkeypatch):
    _identity(monkeypatch)
    item = {"summary": CHATGPT, "content": {"user_text": CHATGPT[:60], "response": "Got it."}}
    out = aurora._answer_from_sedimemory_context("so what is the vibe you are going for?", [item], systems={})
    assert CHATGPT[:40] not in str(out or "")


def test_her_own_consolidated_summary_still_answers(monkeypatch):
    _identity(monkeypatch)
    item = {"summary": "fishing trips with his dad matter to him", "content": {"user_text": "I love fishing with my dad"}}
    out = aurora._answer_from_sedimemory_context("do you remember what matters to me?", [item], systems={})
    assert "fishing trips" in str(out or "")


# ---- FIX-A111: recent-utterance recall quotes only when asked -------------

from aurora_working_memory import is_quote_request  # noqa: E402


def _wm():
    wm = aurora.WorkingMemory.__new__(aurora.WorkingMemory)
    wm.recent_user_utterances = [{"text": "There he is. Good lad, still sharp even when the work gets grimy.",
                                  "terms": ["good", "lad", "sharp", "work"]}]
    wm._utterance_terms = lambda t, u: t.lower().split()
    wm._extract_context_targets = lambda t, u: {"target_terms": t.lower().split()}
    wm._render_from_comprehension_intent = lambda systems, core_claim, **kw: core_claim
    return wm


def test_the_other_speakers_recent_line_is_not_her_answer():
    out = _wm().answer_from_recent_utterance_recall("good lad, the work is sharp today", systems={})
    assert out == ""


def test_asked_what_was_said_she_still_quotes_it():
    out = _wm().answer_from_recent_utterance_recall("what did i just say about the work", systems={})
    assert "Good lad" in out


def test_quote_requests_are_the_natural_forms_of_asking():
    for text in ("what did I just say?", "what did you say", "Repeat that", "say that again", "what was that"):
        assert is_quote_request(text), text
    for text in ("what do you think about work", "I said hello", "good lad"):
        assert not is_quote_request(text), text


def test_conversation_memory_fallback_does_not_revoice_a_stored_line(monkeypatch):
    _identity(monkeypatch)
    wm = _wm()
    wm.recent_user_utterances = []
    wm.answer_from_speaker_owned_facts = lambda *a, **k: ""
    wm._extract_context_targets = lambda t, u: {"targets": ["king"], "target_terms": ["king"]}
    line = "Exactly. That's how a king handles the unknown, you don't hedge your bet."
    systems = {"conversation_memory": SimpleNamespace(recall_about=lambda target: [line])}
    monkeypatch.setattr(aurora, "_recall_semantic_sedimemory", lambda *a, **k: [])
    out = wm.answer_from_context_carryover("so the king handles it", systems=systems)
    assert line[:30] not in str(out or "")
    asked = wm.answer_from_context_carryover("what did you say about the king", systems=systems)
    assert line[:30] in str(asked or "")

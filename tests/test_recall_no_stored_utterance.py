# Authors: Sunni (Sir) Morningstar & Cael Devo
"""A recalled utterance informs her; it is never handed back whole as her answer."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("AURORA_SKIP_DEP_INSTALL", "1")

import aurora  # noqa: E402

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

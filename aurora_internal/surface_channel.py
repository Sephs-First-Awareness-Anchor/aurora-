#!/usr/bin/env python3
"""
aurora_internal.dual_strata.surface_channel

Compatibility bridge for Aurora surface turns.

Public API:
    request_surface_turn(user_text, systems=None, source="interactive", timeout_s=45.0)

This keeps the LLM out of authority. It simply tries Aurora's native gateway/
response paths and returns text. If a richer surface daemon exists later, it can
replace this module without changing aurora.py.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

_STATE_DIR = Path(os.environ.get("AURORA_STATE_DIR", "aurora_state"))
_LOG = _STATE_DIR / "dual_strata_surface_channel.jsonl"


def _log(record: Dict[str, Any]) -> None:
    try:
        _STATE_DIR.mkdir(parents=True, exist_ok=True)
        with _LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, sort_keys=True, ensure_ascii=True) + "\n")
    except Exception:
        pass


def _text_from_response(resp: Any) -> str:
    if resp is None:
        return ""
    for attr in ("content", "text", "response", "message"):
        value = getattr(resp, attr, None)
        if value:
            return str(value)
    if isinstance(resp, dict):
        for key in ("content", "text", "response", "message", "response_text"):
            if resp.get(key):
                return str(resp[key])
    return str(resp)


def _fallback_reply(user_text: str) -> str:
    text = str(user_text or "").strip()
    if not text:
        return "I did not receive a clear signal."
    if "state" in text.lower() or "status" in text.lower():
        return "Surface channel is active. Subsurface bridge is available."
    return "I received the turn through the surface channel, but the deeper response path did not return text."


def request_surface_turn(
    user_text: str,
    systems: Optional[Dict[str, Any]] = None,
    *,
    source: str = "interactive",
    timeout_s: float = 45.0,
    **kwargs: Any,
) -> str:
    """Route one user turn through Aurora's available native response path."""
    systems = systems or {}
    user_text = str(user_text or "").strip()
    started = time.time()

    # Optional local LLM candidate parse. This is only attached as context.
    llm_hint: Dict[str, Any] = {}
    if os.environ.get("AURORA_USE_LOCAL_LLM_SEAM", "0").lower() in {"1", "true", "yes", "on"}:
        try:
            from aurora_internal.aurora_local_llm_bridge import interpret_input  # type: ignore
            llm_hint = dict(interpret_input(user_text) or {})
            systems["_llm_input_hint"] = llm_hint
        except Exception as exc:
            llm_hint = {"error": str(exc), "confidence": 0.0}

    reply = ""

    # Preferred: Aurora governance gateway, if the runtime object exists.
    try:
        aurora_obj = systems.get("aurora") if isinstance(systems, dict) else None
        gw = getattr(aurora_obj, "gateway", None)
        if gw is not None:
            try:
                from aurora_governance_persistence_gateway import StreamType
                from foundational_contract import ExistenceMode
                resp = gw.receive(
                    content=user_text,
                    stream_type=StreamType.USER_INPUT,
                    source=source,
                    mode=ExistenceMode.BOUNDED,
                )
                reply = _text_from_response(resp)
            except Exception:
                resp = gw.receive(user_text)
                reply = _text_from_response(resp)
    except Exception:
        reply = ""

    # Secondary: callable response hooks if present.
    if not reply:
        for key in ("respond", "chat", "process_turn", "handle_turn"):
            fn = systems.get(key) if isinstance(systems, dict) else None
            if callable(fn):
                try:
                    reply = _text_from_response(fn(user_text))
                    if reply:
                        break
                except Exception:
                    continue

    if not reply:
        reply = _fallback_reply(user_text)

    # Optional local LLM output formatting. Aurora's text remains source.
    if os.environ.get("AURORA_USE_LOCAL_LLM_FORMATTER", "0").lower() in {"1", "true", "yes", "on"}:
        try:
            from aurora_internal.aurora_local_llm_bridge import format_output  # type: ignore
            formatted = dict(format_output(reply, {"source": "surface_channel"}) or {})
            candidate = str(formatted.get("message", "") or "").strip()
            if candidate and float(formatted.get("confidence", 0.0) or 0.0) >= 0.5:
                reply = candidate
        except Exception:
            pass

    _log({
        "ts": time.time(),
        "source": source,
        "input": user_text,
        "reply_len": len(reply),
        "elapsed_s": round(time.time() - started, 4),
        "llm_hint": llm_hint,
    })
    return reply

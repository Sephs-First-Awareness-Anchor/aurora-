#!/usr/bin/env python3
"""
Optional isolated llama.cpp boundary language adapter.

This module is not Aurora's cognition. It only offers input interpretation
candidates and final wording polish candidates. The llama.cpp work runs in a
child process so native crashes cannot terminate Aurora.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional


ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "aurora_llama_worker.py"


def _enabled() -> bool:
    return os.environ.get("AURORA_USE_LOCAL_LLM", "1").strip().lower() not in {"0", "false", "no", "off"}


def _timeout() -> float:
    try:
        return max(3.0, float(os.environ.get("AURORA_LOCAL_LLM_TIMEOUT", "45") or 45))
    except Exception:
        return 45.0


def _server_url() -> str:
    return os.environ.get("AURORA_LOCAL_LLM_SERVER_URL", "").strip().rstrip("/")


def _server_enabled() -> bool:
    return bool(_server_url())


def _worker_enabled() -> bool:
    return os.environ.get("AURORA_LOCAL_LLM_WORKER_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}


def _chat_server(messages: list, max_tokens: int, temperature: float = 0.0) -> str:
    url = _server_url()
    if not url:
        return ""
    payload = json.dumps({
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }, ensure_ascii=True).encode()
    req = urllib.request.Request(
        f"{url}/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=_timeout()) as resp:
        data = json.loads(resp.read().decode() or "{}")
    try:
        return str(data["choices"][0]["message"]["content"] or "").strip()
    except Exception:
        return ""


def _parse_json(text: str) -> Dict[str, Any]:
    try:
        data = json.loads(str(text or "").strip())
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _fallback_interpret(text: str = "", reason: str = "disabled") -> Dict[str, Any]:
    return {
        "enabled": _enabled(),
        "available": False,
        "ok": False,
        "role": "input_interpretation_candidate",
        "intent_hint": "",
        "topic_hint": "",
        "entities": [],
        "confidence": 0.0,
        "notes": "",
        "error": reason,
    }


def _fallback_format(message: str = "", reason: str = "disabled") -> Dict[str, Any]:
    return {
        "enabled": _enabled(),
        "available": False,
        "ok": False,
        "role": "output_polish_candidate",
        "message": "",
        "changed": False,
        "confidence": 0.0,
        "error": reason,
        "original": message or "",
    }


def _call_worker(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not _enabled():
        return {"ok": False, "error": "disabled"}
    if not _worker_enabled():
        return {"ok": False, "error": "worker_disabled"}
    if not WORKER.exists():
        return {"ok": False, "error": "worker_missing"}
    try:
        proc = subprocess.run(
            [sys.executable, str(WORKER)],
            input=json.dumps(payload, ensure_ascii=True),
            capture_output=True,
            text=True,
            timeout=_timeout(),
            cwd=str(ROOT),
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout"}
    except Exception as exc:
        return {"ok": False, "error": f"exception:{type(exc).__name__}"}
    if proc.returncode != 0:
        return {
            "ok": False,
            "error": f"worker_exit:{proc.returncode}",
            "stderr": str(proc.stderr or "")[-500:],
        }
    try:
        data = json.loads((proc.stdout or "").strip())
        return data if isinstance(data, dict) else {"ok": False, "error": "invalid_json"}
    except Exception:
        return {"ok": False, "error": "invalid_json", "raw": str(proc.stdout or "")[:240]}


def interpret_input(text: str) -> Dict[str, Any]:
    """Return a candidate interpretation only. Never replaces user text."""
    raw = str(text or "")
    if _server_enabled() and _enabled():
        try:
            content = _chat_server(
                [
                    {
                        "role": "system",
                        "content": (
                            "You are a boundary language adapter for Aurora. "
                            "Do not answer the user. Do not reason for Aurora. Return JSON only."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps({
                            "task": "candidate_input_interpretation",
                            "text": raw[:600],
                            "schema": {
                                "intent_hint": "short string",
                                "topic_hint": "short string",
                                "entities": ["strings"],
                                "confidence": "0..1",
                                "notes": "short string",
                            },
                        }, ensure_ascii=True),
                    },
                ],
                max_tokens=int(os.environ.get("AURORA_LOCAL_LLM_INTERPRET_TOKENS", "96") or 96),
                temperature=0.0,
            )
            data = _parse_json(content)
            if data:
                return {
                    "enabled": True,
                    "available": True,
                    "ok": True,
                    "role": "input_interpretation_candidate",
                    "intent_hint": str(data.get("intent_hint", "") or "")[:120],
                    "topic_hint": str(data.get("topic_hint", "") or "")[:120],
                    "entities": [str(x)[:120] for x in list(data.get("entities", []) or [])[:8]],
                    "confidence": float(data.get("confidence", 0.0) or 0.0),
                    "notes": str(data.get("notes", "") or "")[:240],
                    "error": "",
                    "source": "llama_server",
                }
        except Exception as exc:
            return _fallback_interpret(raw, f"server:{type(exc).__name__}")
    data = _call_worker({"task": "interpret", "text": raw})
    if not data.get("ok"):
        return _fallback_interpret(raw, str(data.get("error", "unavailable") or "unavailable"))
    return {
        "enabled": True,
        "available": True,
        "ok": True,
        "role": "input_interpretation_candidate",
        "intent_hint": str(data.get("intent_hint", "") or "")[:120],
        "topic_hint": str(data.get("topic_hint", "") or "")[:120],
        "entities": [str(x)[:120] for x in list(data.get("entities", []) or [])[:8]],
        "confidence": float(data.get("confidence", 0.0) or 0.0),
        "notes": str(data.get("notes", "") or "")[:240],
        "error": "",
    }


def format_output(message: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return a candidate wording polish only. Aurora's message remains source."""
    original = str(message or "")
    if not original.strip():
        return _fallback_format(original, "empty")
    if _server_enabled() and _enabled():
        try:
            content = _chat_server(
                [
                    {
                        "role": "system",
                        "content": (
                            "You are Aurora's boundary wording adapter. Do not add facts. "
                            "Do not answer independently. Only lightly polish the supplied Aurora message. "
                            "Return JSON only."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps({
                            "task": "polish_aurora_output",
                            "aurora_message": original[:900],
                            "payload": dict(payload or {}),
                            "schema": {
                                "message": "polished message or empty string",
                                "changed": "boolean",
                                "confidence": "0..1",
                            },
                        }, ensure_ascii=True),
                    },
                ],
                max_tokens=int(os.environ.get("AURORA_LOCAL_LLM_FORMAT_TOKENS", "128") or 128),
                temperature=0.0,
            )
            data = _parse_json(content)
            if data:
                return {
                    "enabled": True,
                    "available": True,
                    "ok": True,
                    "role": "output_polish_candidate",
                    "message": str(data.get("message", "") or "").strip(),
                    "changed": bool(data.get("changed", False)),
                    "confidence": float(data.get("confidence", 0.0) or 0.0),
                    "error": "",
                    "original": original,
                    "source": "llama_server",
                }
        except Exception as exc:
            return _fallback_format(original, f"server:{type(exc).__name__}")
    data = _call_worker({"task": "format", "message": original, "payload": dict(payload or {})})
    if not data.get("ok"):
        return _fallback_format(original, str(data.get("error", "unavailable") or "unavailable"))
    return {
        "enabled": True,
        "available": True,
        "ok": True,
        "role": "output_polish_candidate",
        "message": str(data.get("message", "") or "").strip(),
        "changed": bool(data.get("changed", False)),
        "confidence": float(data.get("confidence", 0.0) or 0.0),
        "error": "",
        "original": original,
    }

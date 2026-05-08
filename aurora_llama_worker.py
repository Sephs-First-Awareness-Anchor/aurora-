#!/usr/bin/env python3
"""Isolated local llama.cpp worker for Aurora boundary-language tasks.

The parent process calls this script with JSON on stdin. If llama.cpp aborts,
only this worker process dies; Aurora can continue and treat it as no candidate.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict


DEFAULT_MODEL = "/storage/emulated/0/aurora_strata/Models/qwen2.5-1.5b-instruct-q4_k_m.gguf"


def _model_path() -> str:
    return os.environ.get("AURORA_ARTICULATOR_MODEL") or os.environ.get("AURORA_LOCAL_LLM_MODEL") or DEFAULT_MODEL


def _load_llm():
    from llama_cpp import Llama

    return Llama(
        model_path=_model_path(),
        n_ctx=int(os.environ.get("AURORA_LOCAL_LLM_CTX", "512") or 512),
        n_threads=int(os.environ.get("AURORA_LOCAL_LLM_THREADS", "1") or 1),
        verbose=False,
        logits_all=True,
    )


def _content(resp: Any) -> str:
    try:
        return str(resp["choices"][0]["message"]["content"] or "").strip()
    except Exception:
        return ""


def _parse_json(text: str) -> Dict[str, Any]:
    try:
        data = json.loads(text.strip())
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _chat(llm, messages, max_tokens: int, temperature: float = 0.0) -> str:
    return _content(llm.create_chat_completion(
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    ))


def _interpret(llm, text: str) -> Dict[str, Any]:
    content = _chat(
        llm,
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
                    "text": text[:600],
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
    if not data:
        return {"ok": False, "error": "invalid_json", "raw": content[:240]}
    return {
        "ok": True,
        "intent_hint": str(data.get("intent_hint", "") or "")[:120],
        "topic_hint": str(data.get("topic_hint", "") or "")[:120],
        "entities": [str(x)[:120] for x in list(data.get("entities", []) or [])[:8]],
        "confidence": float(data.get("confidence", 0.0) or 0.0),
        "notes": str(data.get("notes", "") or "")[:240],
    }


def _format(llm, message: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    content = _chat(
        llm,
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
                    "aurora_message": message[:900],
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
    if not data:
        return {"ok": False, "error": "invalid_json", "raw": content[:240]}
    return {
        "ok": True,
        "message": str(data.get("message", "") or "").strip(),
        "changed": bool(data.get("changed", False)),
        "confidence": float(data.get("confidence", 0.0) or 0.0),
    }


def _articulate(llm, draft: str, prompt: str, tone: str) -> Dict[str, Any]:
    content = _chat(
        llm,
        [
            {
                "role": "system",
                "content": (
                    "You are Aurora's local articulation layer only. Do not answer the user. "
                    "Do not add facts, examples, questions, or advice. Only lightly smooth "
                    "Aurora's draft while preserving meaning. Return only the revised message."
                ),
            },
            {
                "role": "user",
                "content": json.dumps({
                    "tone": tone,
                    "user_prompt_context": str(prompt or "")[:300],
                    "aurora_draft": draft[:900],
                }, ensure_ascii=True),
            },
        ],
        max_tokens=int(os.environ.get("AURORA_ARTICULATOR_PY_TOKENS", "48") or 48),
        temperature=float(os.environ.get("AURORA_ARTICULATOR_TEMP", "0.15") or 0.15),
    )
    return {"ok": bool(content), "message": content}


def main() -> int:
    request = _parse_json(sys.stdin.read())
    task = str(request.get("task", "") or "")
    llm = _load_llm()
    if task == "interpret":
        result = _interpret(llm, str(request.get("text", "") or ""))
    elif task == "format":
        result = _format(llm, str(request.get("message", "") or ""), dict(request.get("payload", {}) or {}))
    elif task == "articulate":
        result = _articulate(
            llm,
            str(request.get("draft", "") or ""),
            str(request.get("prompt", "") or ""),
            str(request.get("tone", "") or "neutral"),
        )
    else:
        result = {"ok": False, "error": "unknown_task"}
    print(json.dumps(result, ensure_ascii=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

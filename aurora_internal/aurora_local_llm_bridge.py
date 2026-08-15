#!/usr/bin/env python3
"""Aurora model-free architecture guard.

Build 711 permanently retires the former optional llama.cpp boundary adapter.
The compatibility functions remain so stale imports fail closed instead of
crashing, but there is no model invocation path and no environment variable can
turn one on.
"""
from __future__ import annotations
from typing import Any, Dict, Optional

MODEL_FREE_ARCHITECTURE = True

def _enabled() -> bool:
    return False

def interpret_input(text: str) -> Dict[str, Any]:
    return {
        "enabled": False, "available": False, "ok": False,
        "role": "input_interpretation_candidate", "intent_hint": "",
        "topic_hint": "", "entities": [], "confidence": 0.0, "notes": "",
        "error": "model_use_forbidden_by_architecture",
    }

def format_output(message: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "enabled": False, "available": False, "ok": False,
        "role": "output_polish_candidate", "message": "", "changed": False,
        "confidence": 0.0, "error": "model_use_forbidden_by_architecture",
        "original": str(message or ""),
    }

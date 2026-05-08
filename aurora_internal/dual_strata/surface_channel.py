# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
surface_channel.py

Safe surface-channel compatibility layer.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

_language_faculty: Any = None


def set_language_faculty(language_faculty: Any) -> None:
    """Attach the live Language Faculty module/object for surface realization."""
    global _language_faculty
    _language_faculty = language_faculty


def _extract_prompt(*args: Any, **kwargs: Any) -> str:
    for key in ("prompt", "user_input", "text", "message"):
        if key in kwargs and kwargs[key] is not None:
            return str(kwargs[key])
    if args:
        return str(args[0] or "")
    return ""


def _candidate_score(candidate: Any) -> float:
    if isinstance(candidate, dict):
        for key in ("confidence", "score", "weight"):
            if key in candidate:
                try:
                    return float(candidate[key])
                except Exception:
                    return 0.0
        return 0.0
    for key in ("confidence", "score", "weight"):
        if hasattr(candidate, key):
            try:
                return float(getattr(candidate, key))
            except Exception:
                return 0.0
    return 0.0


def _candidate_text(candidate: Any) -> str:
    if isinstance(candidate, dict):
        for key in ("draft", "content", "text", "message", "response"):
            value = candidate.get(key)
            if value:
                return str(value)
        return ""
    for key in ("content", "draft", "text", "message", "response"):
        value = getattr(candidate, key, None)
        if value:
            return str(value)
    return str(candidate or "")


def _iter_candidates(systems: Dict[str, Any], kwargs: Dict[str, Any]) -> Iterable[Any]:
    for key in ("candidate", "best_candidate"):
        if kwargs.get(key) is not None:
            yield kwargs[key]
    for key in ("candidates", "pipeline_candidates", "responses"):
        values = kwargs.get(key)
        if values:
            yield from values
    for key in ("_last_surface_candidates", "surface_candidates", "pipeline_candidates"):
        values = systems.get(key) if isinstance(systems, dict) else None
        if values:
            yield from values


def _select_best_candidate(systems: Dict[str, Any], kwargs: Dict[str, Any], prompt: str) -> Dict[str, Any]:
    candidates = list(_iter_candidates(systems, kwargs))
    if candidates:
        best = max(candidates, key=_candidate_score)
        if isinstance(best, dict):
            packet = dict(best)
            packet.setdefault("draft", _candidate_text(best))
            return packet
        return {
            "draft": _candidate_text(best),
            "tone": getattr(best, "emotional_tone", "attentive"),
            "confidence": _candidate_score(best),
            "src": getattr(best, "src", "surface"),
        }
    return {"draft": prompt, "tone": "attentive", "confidence": 0.0, "src": "surface"}


def _get_language_faculty(systems: Dict[str, Any]) -> Optional[Any]:
    if _language_faculty is not None:
        return _language_faculty
    if isinstance(systems, dict):
        faculty = systems.get("language_faculty")
        if faculty is not None:
            return faculty
    try:
        from aurora_internal import aurora_language_faculty as faculty
        return faculty
    except Exception:
        return None


def request_surface_turn(*args: Any, **kwargs: Any) -> str:
    """
    Realize the highest-scoring live pipeline candidate through Language Faculty.
    """
    prompt = _extract_prompt(*args, **kwargs)
    systems = kwargs.get("systems") or kwargs.get("runtime") or {}

    if isinstance(systems, dict):
        faculty = _get_language_faculty(systems)
        candidate = _select_best_candidate(systems, kwargs, prompt)
        draft = str(candidate.get("draft") or "").strip()
        if faculty is not None and hasattr(faculty, "realize_output"):
            try:
                realized = faculty.realize_output(candidate, {
                    "source": kwargs.get("source", "surface_channel"),
                    "session_id": kwargs.get("session_id"),
                    "tone": candidate.get("tone", "attentive"),
                    "routing_classification": kwargs.get("routing_classification", ""),
                })
                if isinstance(realized, dict):
                    text = str(realized.get("candidate_text") or "").strip()
                    if text:
                        return text
            except Exception:
                pass
        if draft:
            return draft

    return prompt if prompt else "Surface channel active."

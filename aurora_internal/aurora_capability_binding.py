# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
aurora_capability_binding.py  (FIX-A134)
========================================

A word she was taught can name something she DOES.

"You see with your visual analysis."  The statement is stored like any other
(aurora -see-> visual, aurora -see-> analysis).  What was missing is the other
end: "visual analysis" is a capability she already owns (her tool registry has
it, with a name and a description in words), and "see" had no way to reach it.

This module reads that link from what she was told, never from a list of mine:

    BIND    a predicate she holds (see, hear, ...) is bound to a capability when
            the words it was said with cover the capability's name ("visual
            analysis" -> visual_analysis), or at least two words of its own
            description ("visual scene").
    ASK     "What can you see?" / "Can you hear?" / "What do you see?": a question
            to her, whose predicate she holds bound to a capability.
    USE     only READ-ONLY capabilities answer a question (sensing, her own state,
            memory, time).  Anything that acts on the world (texts, calls, shell,
            files, processes) is never run because someone asked a question.
    SAY     what the capability returned, as statements in the confluence's own
            shape ("I see cup", "I do not see"), so her own composer voices them.

Nothing is placed: with no teaching, no word is bound.  The allow-list below is a
SAFETY boundary on what a question may run, not vocabulary.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set

# What a question may run.  Sensing and reading her own state only.
READ_ONLY = frozenset({"time", "self_state", "schedule_read", "memory_read", "visual_analysis",
                       "audio_analysis", "calculator"})
READ_ONLY_PREFIXES = ("query_",)

_QUESTION_OPENERS = frozenset({"what", "can", "could", "do", "does", "did", "are", "is", "will",
                               "would", "which", "how", "who", "have", "tell"})
_WORD = re.compile(r"[A-Za-z][A-Za-z']*")

# How a sense reports what it found, in its own report (key patterns, not words).
_SENSED = (
    re.compile(r"objects:\s*([^.\n]+)", re.I),
    re.compile(r"category=([A-Za-z_]+)", re.I),
    re.compile(r"activity=([A-Za-z_]+)", re.I),
    re.compile(r"Environment:\s*([A-Za-z]+)", re.I),
)
_NONE_SAID = ("no recognized objects", "unavailable", "no screen", "not available")


def allowed(name: str) -> bool:
    name = str(name or "")
    return name in READ_ONLY or any(name.startswith(p) for p in READ_ONLY_PREFIXES)


def _registry() -> Mapping[str, Any]:
    try:
        from aurora_internal import tool_registry
        return dict(getattr(tool_registry, "_REGISTRY", {}) or {})
    except Exception:
        return {}


def _forms(words: Iterable[str]) -> Set[str]:
    from aurora_internal.aurora_learned_rules import _content_forms
    return _content_forms(words)


def capabilities() -> Dict[str, Dict[str, Set[str]]]:
    """Her own capabilities as words: name parts and description words."""
    out: Dict[str, Dict[str, Set[str]]] = {}
    for name, td in _registry().items():
        parts = {p for p in str(name).lower().split("_") if p}
        desc = {w.lower() for w in _WORD.findall(str(getattr(td, "description", "") or ""))}
        out[str(name)] = {"name": _forms(parts), "desc": _forms(desc) - _forms(parts)}
    return out


def _told_with(web: Any) -> Dict[str, Set[str]]:
    """predicate -> the words it was said with (targets of what she was told)."""
    said: Dict[str, Set[str]] = {}
    for rel in list(getattr(web, "relations", {}).values()):
        a = getattr(rel, "assertion", None)
        if not a:
            continue
        for pred, p in dict(dict(a).get("predicates") or {}).items():
            n, denied = int(dict(p).get("n", 0) or 0), int(dict(p).get("denied", 0) or 0)
            if n <= 0 or denied * 2 >= n or " " in str(pred):
                continue
            said.setdefault(str(pred), set()).update(
                _forms([getattr(rel, "target_word", "")] + list(dict(p).get("said_with") or [])))
    return said


def bindings(web: Any) -> Dict[str, List[str]]:
    """predicate -> capabilities its teaching reaches."""
    if web is None:
        return {}
    caps = capabilities()
    out: Dict[str, List[str]] = {}
    for pred, words in _told_with(web).items():
        for name, c in caps.items():
            full = bool(c["name"]) and c["name"] <= words
            partial = len(words & c["desc"]) >= 2
            if full or partial:
                out.setdefault(pred, []).append(name)
    return out


def asked_predicates(heard: str, held: Iterable[str]) -> List[str]:
    """The bound predicates a question to her is about."""
    toks = [t.lower() for t in _WORD.findall(str(heard or ""))]
    if not toks or "you" not in toks and "your" not in toks and "you're" not in toks:
        return []
    if "?" not in str(heard) and toks[0] not in _QUESTION_OPENERS:
        return []
    forms = _forms(toks)
    return [p for p in held if _forms([p]) & forms]


def _sensed_words(text: str) -> List[str]:
    block = str(text or "")
    obs = re.search(r"observation:\s*(.+)", block, re.I)
    body = obs.group(1) if obs else block
    if any(s in body.lower() for s in _NONE_SAID) and "objects:" not in body.lower():
        return []
    found: List[str] = []
    for pat in _SENSED:
        m = pat.search(body)
        if m:
            found += [w.lower() for w in re.split(r"[,\s]+", m.group(1)) if w.isalpha() and len(w) > 1]
        if found:
            break
    out: List[str] = []
    for w in found:
        if w not in out:
            out.append(w)
    return out[:3]


def answerable(web: Any, heard: str) -> bool:
    """Would a taught word bound to a read-only capability answer this question?  Runs nothing."""
    held = bindings(web)
    return any(allowed(n) for p in asked_predicates(heard, held) for n in held.get(p, []))


def derive(systems: Mapping[str, Any], web: Any, heard: str, *, self_now: str = "") -> List[Dict[str, Any]]:
    """Statements from running the capability a question names, in the shape the
    confluence voices.  Empty when no taught word is asked about."""
    held = bindings(web)
    if not held:
        return []
    asked = asked_predicates(heard, held)
    if not asked:
        return []
    try:
        from aurora_internal import tool_registry
    except Exception:
        return []
    items: List[Dict[str, Any]] = []
    for pred in asked:
        sensed: List[str] = []
        ran: List[str] = []
        for name in held[pred]:
            if not allowed(name):
                continue
            result = tool_registry.call(name, systems=dict(systems or {}))
            ran.append(name)
            if getattr(result, "success", False):
                sensed += _sensed_words(getattr(result, "data", ""))
        if not ran:
            continue                                  # bound, but only to things a question may not run
        base = {"source": "aurora", "kind": "related_to", "strength": 1.6, "axis": "X",
                "learned_from": "capability", "asked": True, "derived": [pred] + ran}
        if sensed:
            for w in dict.fromkeys(sensed):
                items.append({**base, "target": w, "lex": {"agent": "I", "action": pred, "object": w,
                                                           "predicate": pred, "n": "1", "denied": "False"}})
        else:
            items.append({**base, "target": pred, "lex": {"agent": "I", "action": f"do not {pred}", "object": "",
                                                          "predicate": pred, "n": "1", "denied": "True"}})
    return items

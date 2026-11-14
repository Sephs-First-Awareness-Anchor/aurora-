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
import time
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set

from aurora_internal.aurora_propositional_understanding import verdict as _verdict

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


_CAPS: Dict[int, Dict[str, Dict[str, Set[str]]]] = {}
_RUN_TTL = 2.0           # one observation serves every question in the same moment


def capabilities() -> Dict[str, Dict[str, Set[str]]]:
    """Her own capabilities as words: name parts and description words (read once per registry)."""
    reg = _registry()
    if len(reg) not in _CAPS:
        _CAPS.clear()
        _CAPS[len(reg)] = _capabilities_scan(reg)
    return _CAPS[len(reg)]


def _capabilities_scan(reg: Mapping[str, Any]) -> Dict[str, Dict[str, Set[str]]]:
    out: Dict[str, Dict[str, Set[str]]] = {}
    for name, td in reg.items():
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
            if _verdict(p) != "held" or " " in str(pred):
                continue
            said.setdefault(str(pred), set()).update(
                _forms([getattr(rel, "target_word", "")] + list(dict(p).get("said_with") or [])))
    return said


def bindings(web: Any) -> Dict[str, List[str]]:
    """predicate -> capabilities its teaching reaches: resolved once per state of what she
    knows (FIX-A135), shared by the gate's check and the answer."""
    if web is None:
        return {}
    from aurora_internal.aurora_learned_index import memo
    return memo(web, ("bindings", len(_registry())), lambda: _bindings_scan(web))


def _bindings_scan(web: Any) -> Dict[str, List[str]]:
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
    if not found:
        found = _from_report(body if obs else block)
    out: List[str] = []
    for w in found:
        if w not in out:
            out.append(w)
    return out[:4]


_STATUS = frozenset({"active", "inactive", "on", "off", "true", "false", "none", "unknown"})
_REPORT_WORDS = frozenset({"current", "date", "and", "the", "last", "ago", "unreadable", "status", "daemon"})


def _from_report(text: str) -> List[str]:
    """A plain "key: value; key: value" report (her state, memory, the time): the
    value's words when it is words ("active oets concepts: rain, rig"), else the key
    it measured ("coherence: 0.62" -> coherence)."""
    out: List[str] = []
    for seg in re.split(r"[;\n|]", str(text or "")):
        if ":" not in seg:
            continue
        key, _, value = seg.partition(":")
        key_words = [w.lower() for w in _WORD.findall(key)]
        words = [w.lower() for w in _WORD.findall(value) if len(w) >= 3 and w.lower() not in ("and", "the")]
        if words and not set(words) <= _STATUS:
            out += [w for w in words if w not in _REPORT_WORDS][:3]
        elif key_words:
            out.append(key_words[-1])
        if len(out) >= 4:
            break
    return [w for w in out if len(w) >= 3]


def answerable(web: Any, heard: str) -> bool:
    """Would a taught word bound to a read-only capability answer this question?  Runs nothing."""
    held = bindings(web)
    return any(allowed(n) for p in asked_predicates(heard, held) for n in held.get(p, []))


_UNAVAILABLE_NOTES = ("not registered", "no state", "no memory", "unavailable", "not available")


def outcome(result: Any) -> tuple:
    """What a sense gave back, as three different things she can know about her own sensing:
        ("seen", words)       it observed, and found these
        ("empty", [])         it observed, and found nothing (an observation, not a failure)
        ("unavailable", [])   there was no feed to observe with (no camera, no microphone)
        ("failed", [])        the attempt itself went wrong, or could not be read
    """
    data = str(getattr(result, "data", "") or "")
    note = str(getattr(result, "note", "") or "").lower()
    if not getattr(result, "success", False):
        if not note or any(m in note for m in _UNAVAILABLE_NOTES):
            return ("unavailable", [])
        return ("failed", [])
    low = data.lower()
    if "feed unavailable" in low or re.search(r"source:\s*none", low) or "no screen" in low:
        return ("unavailable", [])
    words = _sensed_words(data)
    if words:
        return ("seen", words)
    if "no recognized objects" in low or not data.strip():
        return ("empty", [])
    return ("failed", [])            # it answered, but not in anything she can read


_SAYING = {"unavailable": "cannot {p}", "failed": "could not {p}"}


def _run(systems: Mapping[str, Any], name: str) -> Any:
    """Run a read-only capability, once per moment: later questions in the same turn reuse it."""
    from aurora_internal import tool_registry
    cache = systems.get("_capability_runs") if isinstance(systems, dict) else None
    now = time.time()
    if isinstance(cache, dict) and name in cache and now - cache[name][0] < _RUN_TTL:
        return cache[name][1]
    result = tool_registry.call(name, systems=dict(systems or {}))
    if isinstance(systems, dict):
        systems.setdefault("_capability_runs", {})[name] = (now, result)
    return result


def _remember(systems: Mapping[str, Any], pred: str, ran: List[str], kind: str) -> None:
    """Her own record of how her sensing has gone, so the difference between the cases stays knowable."""
    if isinstance(systems, dict):
        log = systems.setdefault("_capability_outcomes", [])
        log.append({"predicate": pred, "tools": list(ran), "outcome": kind, "t": round(time.time(), 1)})
        del log[:-32]


def derive(systems: Mapping[str, Any], web: Any, heard: str, *, self_now: str = "") -> List[Dict[str, Any]]:
    """Statements from running the capability a question names, in the shape the
    confluence voices.  Empty when no taught word is asked about."""
    held = bindings(web)
    if not held:
        return []
    asked = asked_predicates(heard, held)
    if not asked:
        return []
    items: List[Dict[str, Any]] = []
    for pred in asked:
        sensed: List[str] = []
        kinds: List[str] = []
        ran: List[str] = []
        for name in held[pred]:
            if not allowed(name):
                continue
            ran.append(name)
            kind, words = outcome(_run(systems, name))
            kinds.append(kind)
            sensed += words
        if not ran:
            continue                                  # bound, but only to things a question may not run
        # seen anywhere is seen; else observed-and-empty; else the attempt went wrong; else no feed
        kind = ("seen" if sensed else "empty" if "empty" in kinds else
                "failed" if "failed" in kinds else "unavailable")
        _remember(systems, pred, ran, kind)
        if kind == "seen":                                # what she herself saw is held as OBSERVED (FIX-A137)
            try:
                from aurora_internal.aurora_propositional_understanding import SELF, observe
                for w in dict.fromkeys(sensed):
                    observe(web, SELF, pred, w)
            except Exception:
                pass
        base = {"source": "aurora", "kind": "related_to", "strength": 1.6, "axis": "X",
                "learned_from": "capability", "asked": True, "derived": [pred] + ran}
        base["outcome"] = kind
        if kind == "seen":
            for w in dict.fromkeys(sensed):
                items.append({**base, "target": w, "lex": {"agent": "I", "action": pred, "object": w,
                                                           "predicate": pred, "n": "1", "denied": "False"}})
        elif kind == "empty":                          # she looked, and there was nothing to find
            items.append({**base, "target": "nothing", "lex": {"agent": "I", "action": pred, "object": "nothing",
                                                               "predicate": pred, "n": "1", "denied": "False"}})
        else:                                          # she could not: no feed, or the attempt went wrong
            items.append({**base, "target": pred, "lex": {"agent": "I", "action": _SAYING[kind].format(p=pred),
                                                          "object": "", "predicate": pred, "n": "1",
                                                          "denied": "True"}})
    return items

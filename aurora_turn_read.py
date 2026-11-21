#!/usr/bin/env python3
"""
aurora_turn_read.py -- her own NonComp read of a message chooses the turn's path

Authors: Sunni (Sir) Morningstar and Cael Devo

WHAT THIS IS
------------
Until now the front door of a turn was decided by English phrase lists in
aurora.py: whether a message is a question (_looks_like_question, 29
prefixes), whether it is about her (_is_aurora_self_question, 112 phrases,
including any message that merely contains "sunni" or "aurora"), whether it
asks about her inner state (_looks_like_inner_state_query, 41 phrases),
whether she should answer from her own perspective
(_should_prefer_live_perspective) and the recall step of
_classify_input_intent (21 phrases).

Her NonComp reflexive interpreter already reads every message once per turn:
the UtteranceParser's relational form (who does what to whom, what is open,
whether it is asked or directed), the frame and stance, and the 25-channel
projection onto the five axes (X, T, N, B, A) with its dominant target.  This
module forms that read ONCE, at the top of the turn, and lets it answer the
routing questions.  The phrase lists keep running quietly beside it: every
routing call records what the list would have said and what her read said,
so the lists can be retired once the comparison shows they add nothing.

Nothing here writes a word she says or picks a reply.  It only lets her own
perception of a message decide which path the message takes; the paths
themselves are unchanged.

HOW THE READ ANSWERS
--------------------
  is_question        the relation is asked (open slot / inverted auxiliary)
                     or directed at her (a request): relational_form.question
                     or .directive, or the parse's utterance_type.  A modal
                     question ("can you explain gravity?") is a request: she
                     is asked to act on its object, not asked about herself.
  about_her          asked or directed, and she is a participant of the asked
                     relation (subject, object or owner resolves to the second
                     person or to her own name), or a participant she already
                     holds in her core identity is named, or the speaker asks
                     her to recall; and the open slot is not an embedded
                     question about something else ("do you know what X is").
  inner_state        asked, and she is the experiencer (the subject) of the
                     asked relation, with no embedded outside question.
  prefer_perspective about_her or inner_state, unless the message is recall or
                     her read itself places it on a clarification of meaning
                     (the interpreter's own semantic override).
  recall             her read's temporal_recall override, a callback, or a
                     question whose participants are the speaker (and what
                     passed to her), not her own state.

The person words used to resolve participants ("you", "your", "yourself",
"I", "me", "my") are grammar, not routing phrases: they say who a slot refers
to, never what the message is about.

The interpreter's own matcher still carries a few patterns of its own
(_semantic_override in aurora_reflexive_interpreter.py).  Those are part of
her read today and are listed in docs/TURN_ROUTING_PHRASE_LIST_MAP.md as the
next place to bring into the channels.

SWITCH
------
ROUTE_BY_TURN_READ = True   her read routes; lists in shadow (default)
ROUTE_BY_TURN_READ = False  the lists route; her read in shadow (baseline)
Either way both verdicts are recorded.

ONE STATE
---------
The comparison is a journal (turn_read_shadow.jsonl in her state directory,
gitignored like every other aurora_state/*.jsonl).  It is appended only
through the store-ownership gate, so a surface-only device keeps its own
record and never forks a developmental store.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import json
import os
import re
import threading
from contextvars import ContextVar
from functools import wraps
import time
from collections import deque
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Deque, Dict, List, Optional

from aurora_internal.aurora_runtime_faults import bind_fault_recorder as _bind_fault_recorder

_aurora_fault = _bind_fault_recorder(__name__, "aurora_turn_read.py")

ROUTE_BY_TURN_READ = True

SHADOW_JOURNAL_NAME = "turn_read_shadow.jsonl"
_RECENT_LIMIT = 400

# Person resolution (grammar): which words in a relational slot refer to the
# one being addressed, and which to the one speaking.
_SECOND_PERSON = frozenset({"you", "your", "yours", "yourself", "u", "ur"})
_FIRST_PERSON = frozenset({"i", "me", "my", "mine", "myself"})
# A modal auxiliary that opens a question addressed to her ("can you ...",
# "would you ...") is the grammar of a request: she is asked to act on the
# object, not asked about herself (unless the object is her, or her read
# places the message on experience).
_MODALS = frozenset({"can", "could", "would", "will", "should", "shall", "may", "might", "must"})
# Wh-determiners that open an embedded question inside a slot.
_WH = frozenset({"what", "who", "whom", "whose", "which", "where", "when", "why", "how", "whether", "if"})
# The interpreter's own semantic overrides that place a message on a
# clarification of meaning or on recall rather than on her perspective.
_NOT_PERSPECTIVE_OVERRIDES = frozenset({"agency_clarification", "boundary_meaning", "temporal_recall"})

_WORD = re.compile(r"[a-z][a-z']*")


def text_key(text: Any) -> str:
    return " ".join(str(text or "").lower().split())


def _words(value: Any) -> List[str]:
    return _WORD.findall(str(value or "").lower())


@dataclass
class TurnRead:
    text: str
    key: str
    formed_at: float
    source: str                     # "noncomp" | "parse_only"
    # what her read saw
    frame: str = ""
    stance: str = ""
    utterance_type: str = ""
    constraint: str = ""
    dimension: str = ""
    dominant_target: str = ""
    basis_channel: str = ""
    semantic_override: str = ""
    is_understood: bool = False
    relation: str = ""
    asked: bool = False
    directed: bool = False
    she_participates: bool = False
    she_experiences: bool = False
    speaker_participates: bool = False   # the speaker is the relation's source
    held_participants: List[str] = field(default_factory=list)
    embedded_question: bool = False
    callback: bool = False
    # the routing answers
    is_question: bool = False
    about_her: bool = False
    inner_state: bool = False
    prefer_perspective: bool = False
    recall: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Forming the read
# ---------------------------------------------------------------------------

def _slot_refs(rel: Dict[str, Any], slot: str) -> List[str]:
    return _words(rel.get(slot, ""))


def _relation_parts(rel: Dict[str, Any]) -> List[Dict[str, Any]]:
    parts = [rel] if rel else []
    for clause in list(rel.get("clauses") or []):
        if isinstance(clause, dict):
            parts.append(clause)
    return parts


def _known_participants(systems: Optional[Dict[str, Any]], parsed: Dict[str, Any]) -> List[str]:
    core = (systems or {}).get("core_identity") if isinstance(systems, dict) else None
    if core is None or not hasattr(core, "get_entity"):
        return []
    held: List[str] = []
    names = [str(n) for n in list(parsed.get("entities") or []) if str(n or "").strip()]
    for name in names:
        try:
            if core.get_entity(name.lower()) is not None and name.lower() not in held:
                held.append(name.lower())
        except Exception as _aurora_boundary_exc:
            _aurora_fault(locals(), _aurora_boundary_exc, "_known_participants", 0)
    return held


def _self_names(systems: Optional[Dict[str, Any]]) -> frozenset:
    core = (systems or {}).get("core_identity") if isinstance(systems, dict) else None
    name = str(getattr(core, "self_name", "") or "").strip().lower()
    return frozenset({name}) if name else frozenset()


def read_from(
    text: str,
    parsed: Dict[str, Any],
    noncomp: Optional[Dict[str, Any]] = None,
    *,
    systems: Optional[Dict[str, Any]] = None,
) -> TurnRead:
    """Derive the routing answers from her read of ``text``.  Pure: no
    interpreter call, no side effects.  ``noncomp`` is the interpreter's
    UnderstandingState.to_dict() for the same text, when she has one."""
    parsed = dict(parsed or {})
    noncomp = dict(noncomp or {})
    rel = dict(parsed.get("relational_form") or {})
    nc_state = dict(noncomp.get("noncomp_state") or {})
    her = _SECOND_PERSON | _self_names(systems)

    read = TurnRead(
        text=str(text or "")[:200],
        key=text_key(text),
        formed_at=time.time(),
        source="noncomp" if noncomp else "parse_only",
        frame=str(noncomp.get("frame") or parsed.get("frame") or ""),
        stance=str(parsed.get("stance") or ""),
        utterance_type=str(parsed.get("utterance_type") or ""),
        constraint=str(noncomp.get("constraint") or ""),
        dimension=str(noncomp.get("dimension") or ""),
        dominant_target=str(nc_state.get("dominant_target") or ""),
        basis_channel=str(nc_state.get("basis_channel") or ""),
        semantic_override=str(noncomp.get("semantic_override") or ""),
        is_understood=bool(noncomp.get("is_understood")),
        relation=str(rel.get("relation") or ""),
        callback=bool(parsed.get("is_callback")),
    )

    utype = read.utterance_type.lower()
    read.asked = bool(rel.get("question")) or utype in {"question", "experience_question"}
    read.directed = bool(rel.get("directive")) or bool(parsed.get("is_imperative"))

    for part in _relation_parts(rel):
        directive = bool(part.get("directive"))
        subj = _slot_refs(part, "subject")
        objs = _slot_refs(part, "obj") + _slot_refs(part, "complement") + _slot_refs(part, "owner")
        # An imperative's subject is the implied listener, not a participant
        # of what is asked about.
        her_in_objects = any(w in her for w in objs)
        modal_request = (
            str(part.get("modality") or "").strip().lower() in _MODALS and
            bool(subj) and subj[0] in her and
            bool(objs) and not her_in_objects and
            read.frame.lower() != "experiential"
        )
        if modal_request:
            read.directed = True
        elif not directive and subj and subj[0] in her:
            read.she_experiences = True
            read.she_participates = True
        if her_in_objects:
            read.she_participates = True
        # The speaker as the source of the relation (its subject or owner:
        # "what did I tell you", "what is my name"), not as a recipient
        # ("could you tell me the time").
        if any(w in _FIRST_PERSON for w in subj + _slot_refs(part, "owner")):
            read.speaker_participates = True
        obj_words = _slot_refs(part, "obj") + _slot_refs(part, "complement")
        if obj_words and obj_words[0] in _WH:
            read.embedded_question = True

    read.held_participants = _known_participants(systems, parsed)
    # Recall: her read's own temporal override, a callback, or a question
    # whose participants are the speaker and what passed to her (the speaker
    # asks about what was said or held between them, not about her state).
    read.recall = (
        read.semantic_override == "temporal_recall" or
        read.callback or
        (read.asked and read.speaker_participates and not read.she_experiences)
    )

    read.is_question = read.asked or read.directed
    reaches_her = (
        read.she_participates or
        bool(read.held_participants) or
        (read.speaker_participates and read.recall)
    )
    read.about_her = read.is_question and reaches_her and not read.embedded_question
    read.inner_state = read.asked and read.she_experiences and not read.embedded_question
    read.prefer_perspective = (
        (read.about_her or read.inner_state) and
        not read.recall and
        read.semantic_override not in _NOT_PERSPECTIVE_OVERRIDES
    )
    return read


# ---------------------------------------------------------------------------
# The turn's one read
# ---------------------------------------------------------------------------

_lock = threading.RLock()
# The desktop, phone and experimental organisms may evaluate overlapping turns.
# Bind the read and its journal destination to the execution context that formed it.
_active = ContextVar("aurora_turn_read", default=None)
_recent: Deque[Dict[str, Any]] = deque(maxlen=_RECENT_LIMIT)
_totals: Dict[str, Dict[str, int]] = {}


def scoped_turn(function):
    """Flush even on early return or failure, then restore any outer turn."""
    @wraps(function)
    def call(*args, **kwargs):
        token = _active.set(None)
        try:
            return function(*args, **kwargs)
        finally:
            try:
                _flush()
            finally:
                _active.reset(token)
    return call


def form_turn_read(
    systems: Optional[Dict[str, Any]],
    text: str,
    *,
    parse: Optional[Callable[[str], Dict[str, Any]]] = None,
) -> Optional[TurnRead]:
    """Called once at the top of a live turn.  Reads the message through her
    NonComp interpreter (the turn's only interpret call for this text; the
    later input guidance reuses it) and makes that read the turn's router."""
    _flush()
    if not str(text or "").strip():
        return None
    try:
        parsed: Dict[str, Any] = {}
        if parse is not None:
            parsed = dict(parse(text) or {})
        else:
            from aurora_internal.aurora_utterance_parser import UtteranceParser
            parsed = dict(UtteranceParser().parse(text) or {})
    except Exception as _aurora_boundary_exc:
        _aurora_fault(locals(), _aurora_boundary_exc, "form_turn_read", 0)
        parsed = {}

    noncomp: Dict[str, Any] = {}
    interpreter = systems.get("noncomp_reflexive_interpreter") if isinstance(systems, dict) else None
    if interpreter is not None and hasattr(interpreter, "interpret"):
        try:
            noncomp = dict(interpreter.interpret(text).to_dict() or {})
        except Exception as _aurora_boundary_exc:
            _aurora_fault(locals(), _aurora_boundary_exc, "form_turn_read", 0)
            noncomp = {}

    read = read_from(text, parsed, noncomp, systems=systems)
    record = {"at": read.formed_at, "key": read.key, "read": read.to_dict(), "calls": []}
    _active.set((read, systems, noncomp, record))
    if isinstance(systems, dict):
        systems["_turn_read"] = read
        systems["_turn_read_interpretation"] = {"key": read.key, "summary": dict(noncomp)} if noncomp else {}
    return read


def current_read(text: Any = None) -> Optional[TurnRead]:
    """The turn's read, if it is the read of ``text`` (or any text when None)."""
    active = _active.get()
    if active is None:
        return None
    read = active[0]
    if text is not None and text_key(text) != read.key:
        return None
    return read


def reuse_interpretation(systems: Optional[Dict[str, Any]], text: Any) -> Optional[Dict[str, Any]]:
    """The interpreter summary formed for this turn's text, so the input
    guidance does not interpret the same message twice (interpret lays
    sediment and records worth; twice would double both)."""
    if not isinstance(systems, dict):
        return None
    active = _active.get()
    if active and active[1] is systems and active[0].key == text_key(text) and active[2]:
        return dict(active[2])
    return None


def route(kind: str, text: Any, lexical: Any, from_read: Callable[[TurnRead], Any]) -> Any:
    """Answer one routing question.  Records both verdicts; returns her read's
    verdict when the switch is on and she has read this text, else the list's."""
    read = current_read(text)
    if read is None:
        _note(kind, text, lexical, None, used="lexical_no_read")
        return lexical
    try:
        mine = from_read(read)
    except Exception as _aurora_boundary_exc:
        _aurora_fault(locals(), _aurora_boundary_exc, "route", 0)
        _note(kind, text, lexical, None, used="lexical_read_failed")
        return lexical
    used = "read" if ROUTE_BY_TURN_READ else "lexical"
    _note(kind, text, lexical, mine, used=used)
    return mine if ROUTE_BY_TURN_READ else lexical


def _note(kind: str, text: Any, lexical: Any, mine: Any, *, used: str) -> None:
    agree = None if mine is None else (mine == lexical)
    entry = {"kind": kind, "lexical": lexical, "read": mine, "agree": agree, "used": used}
    with _lock:
        tot = _totals.setdefault(kind, {"calls": 0, "agree": 0, "disagree": 0, "no_read": 0})
        tot["calls"] += 1
        if agree is None:
            tot["no_read"] += 1
        elif agree:
            tot["agree"] += 1
        else:
            tot["disagree"] += 1
        active = _active.get()
        if mine is not None and active is not None and text_key(text) == active[0].key:
            _turn_record = active[3]
            # one line per routing question per turn (callers ask repeatedly)
            seen = {(c["kind"]) for c in _turn_record.get("calls", [])}
            if kind not in seen:
                _turn_record.setdefault("calls", []).append(entry)
        if agree is False:
            _recent.append(dict(entry, text=str(text or "")[:160], at=time.time()))


def shadow_report() -> Dict[str, Any]:
    """Totals per routing question, and the latest disagreements."""
    with _lock:
        return {
            "route_by_turn_read": ROUTE_BY_TURN_READ,
            "totals": {k: dict(v) for k, v in _totals.items()},
            "recent_disagreements": list(_recent)[-40:],
        }


def reset_shadow() -> None:
    with _lock:
        _totals.clear()
        _recent.clear()
        _active.set(None)


def _flush() -> None:
    """Append this turn to the state that originally supplied the read."""
    active = _active.get()
    _active.set(None)
    if active is None:
        return
    _, systems, _, record = active
    if not record["calls"] or not isinstance(systems, dict):
        return
    state_dir = systems.get("state_dir")
    if not state_dir:
        return
    path = Path(str(state_dir)) / SHADOW_JOURNAL_NAME
    try:
        from aurora_internal.aurora_store_ownership import store_write_allowed
        if not store_write_allowed(path):
            return
        record["route_by_turn_read"] = ROUTE_BY_TURN_READ
        record["disagreements"] = sum(1 for c in record.get("calls", []) if c.get("agree") is False)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, default=str) + "\n")
    except Exception as _aurora_boundary_exc:
        _aurora_fault(locals(), _aurora_boundary_exc, "_flush", 0)


def flush_turn(systems: Optional[Dict[str, Any]]) -> None:
    """Public end-of-turn flush (the next form_turn_read also flushes)."""
    _flush()

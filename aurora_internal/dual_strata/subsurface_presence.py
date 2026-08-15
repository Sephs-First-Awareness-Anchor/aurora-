"""
Live Subsurface presence -- Surface <-> Subsurface, in the moment.

Core architectural law (Subsurface Presence and Evidence Scout spec,
sections 5 and 13):
    Subsurface must know a live user turn is happening NOW, not learn
    about it after Surface has already answered.

surface_continuity_feed.py (a sibling module) already carries the
POST-response handoff -- what Surface absorbed after a turn completed.
This module is the layer underneath that: a lightweight channel Surface
writes to the INSTANT it accepts a turn (turn_open) and again once it
has interpreted that turn (interpreted_turn, via
_run_reasoning_pipeline() after _chain_down3_purpose() -- see
aurora_scouting_hooks.py), plus the live PresenceFrame Subsurface keeps
current in response, which Surface samples (non-blocking, newest-valid)
at three points: turn opening, after interpretation, and before final
expression.

Three files, deliberately separate so a slow write to one never blocks
reads of another, and so the live channel is never confused with the
diagnostic-only 60s daemon_status.json / subsurface_projection.json:

    subsurface_turn_events.json      Surface -> Subsurface (small, FIFO)
    subsurface_presence_frame.json   Subsurface -> Surface (event-driven)
    subsurface_heartbeat.json        Subsurface liveness only (~1/s touch)

The heartbeat file exists specifically so a long-running retrieval or
autonomous task inside the Subsurface main loop can be PROVEN not to
have frozen presence, even on ticks where nothing about the frame's
content actually changed.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations
from aurora_internal.aurora_runtime_faults import record_exception_from_locals as _aurora_record_exception_from_locals

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

_TURN_EVENTS_FILENAME = "subsurface_turn_events.json"
_PRESENCE_FRAME_FILENAME = "subsurface_presence_frame.json"
_HEARTBEAT_FILENAME = "subsurface_heartbeat.json"
_MAX_TURN_EVENTS = 20


def _resolve(state_dir: Any) -> Path:
    if state_dir is not None:
        return Path(str(state_dir))
    return Path(__file__).resolve().parents[2] / "aurora_state"


def _atomic_write(path: Path, payload: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)


# ── A. Turn open event (Surface -> Subsurface, "something is happening now") ──

def _append_turn_event(state_dir: Any, event: Dict[str, Any], *, caller: str) -> None:
    root = _resolve(state_dir)
    path = root / _TURN_EVENTS_FILENAME
    try:
        existing: List[Dict[str, Any]] = []
        if path.exists():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(raw, list):
                    existing = raw
            except Exception as _aurora_boundary_exc:
                _aurora_record_exception_from_locals(
                    locals(), module=__name__,
                    operation=f"exception_handler:aurora_internal/dual_strata/subsurface_presence.py:{caller}:read",
                    exc=_aurora_boundary_exc,
                    context={"function": caller, "source_file": "aurora_internal/dual_strata/subsurface_presence.py"},
                )
                existing = []
        existing.append(event)
        existing = existing[-_MAX_TURN_EVENTS:]
        _atomic_write(path, existing)
    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(), module=__name__,
            operation=f"exception_handler:aurora_internal/dual_strata/subsurface_presence.py:{caller}:write",
            exc=_aurora_boundary_exc,
            context={"function": caller, "source_file": "aurora_internal/dual_strata/subsurface_presence.py"},
        )


def write_turn_open(
    state_dir: Any,
    *,
    turn_id: str,
    raw_input: str = "",
    sensory_ref: Optional[str] = None,
    session_id: Optional[str] = None,
    prior_frame_ref: Optional[str] = None,
    source_label: Optional[str] = None,
) -> str:
    """Surface calls this the instant a turn is accepted, BEFORE the full
    response pipeline runs. Does not trigger a Scout -- purely a presence
    signal. Returns the event_id.

    Build 694: the canonical call site is now
    aurora.process_external_user_turn() itself (every genuine external
    interactive turn goes through it -- desktop daemon AND the Android
    bridge alike), not aurora_surface_daemon.py, which only the desktop
    daemon path ever runs. [source_label] carries process_external_user_
    turn()'s own source_label through (e.g. "flutter_ui" vs
    "external_user_turn"), so a turn-open event visibly identifies which
    entry path produced it."""
    event_id = uuid.uuid4().hex
    event: Dict[str, Any] = {
        "event_id": event_id,
        "kind": "turn_open",
        "turn_id": str(turn_id or ""),
        "created_at": time.time(),
        "raw_input": str(raw_input or "")[:500],
        "sensory_ref": str(sensory_ref or "") or None,
        "session_id": str(session_id or "") or None,
        "prior_frame_ref": str(prior_frame_ref or "") or None,
        "source_label": str(source_label or "") or None,
        "consumed": False,
    }
    _append_turn_event(state_dir, event, caller="write_turn_open")
    return event_id


def write_interpreted_turn(
    state_dir: Any,
    *,
    turn_id: str,
    interpreted_meaning: str = "",
    inferred_purpose: str = "",
    current_topic: str = "",
    resolved_referents: Optional[List[str]] = None,
    unresolved_ambiguity: Optional[List[str]] = None,
    interpretation_confidence: float = 0.0,
    response_confidence: float = 0.0,
    dominant_constraints: Optional[Dict[str, float]] = None,
    representation_refs: Optional[List[str]] = None,
    knowledge_gaps: Optional[List[str]] = None,
    response_fit_pressure: float = 0.0,
) -> str:
    """Surface calls this once, in _run_reasoning_pipeline() right after
    _chain_down3_purpose() -- at that point Aurora has been through
    understanding -> meaning -> purpose (both the upward AND downward
    passes for those three stages) but belief/information have not yet
    refined the response, so this packet genuinely captures "how well
    she understood the input" before "how she'll respond" has been
    decided. The Scout, if one is later dispatched for this turn (spec
    section 6), receives THIS interpretation as authoritative input --
    never the raw_input from write_turn_open() above."""
    event_id = uuid.uuid4().hex
    event: Dict[str, Any] = {
        "event_id": event_id,
        "kind": "interpreted_turn",
        "turn_id": str(turn_id or ""),
        "created_at": time.time(),
        "interpreted_meaning": str(interpreted_meaning or "")[:400],
        "inferred_purpose": str(inferred_purpose or "")[:200],
        "current_topic": str(current_topic or "")[:120],
        "resolved_referents": [str(r) for r in list(resolved_referents or [])][:12],
        "unresolved_ambiguity": [str(a) for a in list(unresolved_ambiguity or [])][:12],
        "interpretation_confidence": round(max(0.0, min(1.0, float(interpretation_confidence or 0.0))), 4),
        "response_confidence": round(max(0.0, min(1.0, float(response_confidence or 0.0))), 4),
        "dominant_constraints": dict(dominant_constraints or {}),
        "representation_refs": [str(r) for r in list(representation_refs or [])][:16],
        "knowledge_gaps": [str(g) for g in list(knowledge_gaps or [])][:8],
        "response_fit_pressure": round(max(0.0, min(1.0, float(response_fit_pressure or 0.0))), 4),
        "consumed": False,
    }
    _append_turn_event(state_dir, event, caller="write_interpreted_turn")
    return event_id


def write_evidence_need(
    state_dir: Any,
    *,
    turn_id: str,
    request_kind: str = "knowledge_gap",
    target: str = "",
    inquiry: str = "",
    evidence_needed: str = "",
    representation_refs: Optional[List[str]] = None,
    priority: float = 0.5,
    max_result_chars: int = 1200,
    ttl_s: float = 30.0,
) -> str:
    """Surface calls this whenever it needs external evidence -- knowledge
    gaps (spec section 6/10) and response-fit pressure (section 10/11)
    alike -- instead of dispatching a ScoutRequest itself (Build 694 step
    9 reverses that part of Build 675 step 10's design). Surface no
    longer holds a ScoutBroker or imports dispatch_scout_request() at
    all: it only ever describes the need. Subsurface (via
    integrate_evidence_need_event() below) is the sole owner of turning
    a described need into an actual dispatched ScoutRequest -- the same
    turn_open/interpreted_turn channel just gains a third event kind.
    Returns the event_id."""
    event_id = uuid.uuid4().hex
    event: Dict[str, Any] = {
        "event_id": event_id,
        "kind": "evidence_need",
        "turn_id": str(turn_id or ""),
        "created_at": time.time(),
        "request_kind": str(request_kind or "knowledge_gap"),
        "target": str(target or "")[:120],
        "inquiry": str(inquiry or "")[:500],
        "evidence_needed": str(evidence_needed or "")[:500],
        "representation_refs": [str(r) for r in list(representation_refs or [])][:16],
        "priority": round(max(0.0, min(1.0, float(priority or 0.0))), 4),
        "max_result_chars": max(1, int(max_result_chars or 1200)),
        "ttl_s": max(1.0, float(ttl_s or 30.0)),
        "consumed": False,
    }
    _append_turn_event(state_dir, event, caller="write_evidence_need")
    return event_id


def read_and_clear_turn_events(state_dir: Any) -> List[Dict[str, Any]]:
    """Subsurface calls this each loop cycle. Returns unconsumed turn_open
    (and interpreted_turn, once InterpretedTurnPacket lands) events and
    marks them consumed -- same read-and-clear contract as
    surface_continuity_feed.read_and_clear_continuity_packets()."""
    root = _resolve(state_dir)
    path = root / _TURN_EVENTS_FILENAME
    if not path.exists():
        return []

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            return []
    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(), module=__name__,
            operation="exception_handler:aurora_internal/dual_strata/subsurface_presence.py:read_and_clear_turn_events:read",
            exc=_aurora_boundary_exc,
            context={"function": "read_and_clear_turn_events", "source_file": "aurora_internal/dual_strata/subsurface_presence.py"},
        )
        return []

    pending = [e for e in raw if isinstance(e, dict) and not bool(e.get("consumed", False))]
    if not pending:
        return []

    for e in raw:
        if isinstance(e, dict) and not bool(e.get("consumed", False)):
            e["consumed"] = True

    raw = raw[-_MAX_TURN_EVENTS:]
    try:
        _atomic_write(path, raw)
    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(), module=__name__,
            operation="exception_handler:aurora_internal/dual_strata/subsurface_presence.py:read_and_clear_turn_events:write",
            exc=_aurora_boundary_exc,
            context={"function": "read_and_clear_turn_events", "source_file": "aurora_internal/dual_strata/subsurface_presence.py"},
        )

    return pending


# ── B/C. Presence frame (Subsurface -> Surface, event-driven) ──────────────

# Build 694 section 19: "Do not erase populated fields every time a
# partial update is written. Updates must merge with the current frame
# for the same turn." A plain default (None/0/"") can't distinguish "the
# caller explicitly wants this cleared" from "the caller didn't touch
# this field at all" -- this sentinel lets write_presence_frame() tell
# those apart, so e.g. integrate_turn_open() (which only knows turn_id/
# raw_input) and integrate_interpreted_turn() (which only knows the
# interpretation fields) can each update their own slice of the SAME
# frame without wiping out what the other already wrote for this turn.
_UNSET = object()


def write_presence_frame(
    state_dir: Any,
    *,
    turn_id: str = "",
    crest: Any = _UNSET,
    active_pressure: Any = _UNSET,
    continuity_summary: Any = _UNSET,
    unresolved_tensions: Any = _UNSET,
    scout_requests_pending: Any = _UNSET,
    scout_evidence_integrated: Any = _UNSET,
    response_fit_pressure: Any = _UNSET,
    evidence_bindings: Any = _UNSET,
    knowledge_gap_pressure: Any = _UNSET,
    turn_open_at: Any = _UNSET,
    interpreted_at: Any = _UNSET,
    interpreted_meaning: Any = _UNSET,
    inferred_purpose: Any = _UNSET,
    current_topic: Any = _UNSET,
    interpretation_confidence: Any = _UNSET,
    response_confidence: Any = _UNSET,
    resolved_referents: Any = _UNSET,
    unresolved_ambiguity: Any = _UNSET,
    knowledge_gaps: Any = _UNSET,
    representation_refs: Any = _UNSET,
) -> Dict[str, Any]:
    """Subsurface calls this whenever turn state or Scout evidence
    actually changes -- NOT on a fixed interval. Deliberately not the
    60s daemon_status.json write path (see module docstring, section 14
    of the spec). Returns the frame written, including its own
    sequence number.

    A NEW turn_id resets every field to that turn's own fresh defaults
    (a new turn's presence frame must not inherit the previous turn's
    interpreted_meaning, etc.) -- merging only applies WITHIN the same
    turn_id, across the separate partial updates spec section 19
    describes (turn_open first, interpreted_turn shortly after, Scout
    evidence sometime after that).
    """
    root = _resolve(state_dir)
    path = root / _PRESENCE_FRAME_FILENAME

    prev: Dict[str, Any] = {}
    prev_seq = 0
    try:
        if path.exists():
            raw_prev = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw_prev, dict):
                prev = raw_prev
                prev_seq = int(prev.get("seq", 0) or 0)
    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(), module=__name__,
            operation="exception_handler:aurora_internal/dual_strata/subsurface_presence.py:write_presence_frame:read_prev",
            exc=_aurora_boundary_exc,
            context={"function": "write_presence_frame", "source_file": "aurora_internal/dual_strata/subsurface_presence.py"},
        )
        prev = {}
        prev_seq = 0

    same_turn = bool(prev) and str(prev.get("turn_id", "") or "") == str(turn_id or "")
    carry = prev if same_turn else {}

    def merged(value: Any, key: str, default: Any):
        return value if value is not _UNSET else carry.get(key, default)

    frame: Dict[str, Any] = {
        "seq": prev_seq + 1,
        "generated_at": time.time(),
        "turn_id": str(turn_id or ""),
        "crest": merged(crest, "crest", None),
        "active_pressure": merged(active_pressure, "active_pressure", None),
        "continuity_summary": str(merged(continuity_summary, "continuity_summary", "") or "")[:400],
        "unresolved_tensions": [
            str(t) for t in list(merged(unresolved_tensions, "unresolved_tensions", []) or []) if str(t).strip()
        ][:6],
        "scout_requests_pending": max(0, int(merged(scout_requests_pending, "scout_requests_pending", 0) or 0)),
        "scout_evidence_integrated": [
            str(e) for e in list(merged(scout_evidence_integrated, "scout_evidence_integrated", []) or [])
        ][:12],
        "response_fit_pressure": round(
            max(0.0, min(1.0, float(merged(response_fit_pressure, "response_fit_pressure", 0.0) or 0.0))), 4
        ),
        "evidence_bindings": list(merged(evidence_bindings, "evidence_bindings", []) or [])[:8],
        # Build 694 section 19 additions -- all merge-capable the same way.
        "knowledge_gap_pressure": round(
            max(0.0, min(1.0, float(merged(knowledge_gap_pressure, "knowledge_gap_pressure", 0.0) or 0.0))), 4
        ),
        "turn_open_at": merged(turn_open_at, "turn_open_at", None),
        "interpreted_at": merged(interpreted_at, "interpreted_at", None),
        "interpreted_meaning": str(merged(interpreted_meaning, "interpreted_meaning", "") or "")[:400],
        "inferred_purpose": str(merged(inferred_purpose, "inferred_purpose", "") or "")[:200],
        "current_topic": str(merged(current_topic, "current_topic", "") or "")[:120],
        "interpretation_confidence": round(
            max(0.0, min(1.0, float(merged(interpretation_confidence, "interpretation_confidence", 0.0) or 0.0))), 4
        ),
        "response_confidence": round(
            max(0.0, min(1.0, float(merged(response_confidence, "response_confidence", 0.0) or 0.0))), 4
        ),
        "resolved_referents": [str(r) for r in list(merged(resolved_referents, "resolved_referents", []) or [])][:12],
        "unresolved_ambiguity": [str(a) for a in list(merged(unresolved_ambiguity, "unresolved_ambiguity", []) or [])][:12],
        "knowledge_gaps": [str(g) for g in list(merged(knowledge_gaps, "knowledge_gaps", []) or [])][:8],
        "representation_refs": [str(r) for r in list(merged(representation_refs, "representation_refs", []) or [])][:16],
    }

    try:
        _atomic_write(path, frame)
    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(), module=__name__,
            operation="exception_handler:aurora_internal/dual_strata/subsurface_presence.py:write_presence_frame:write",
            exc=_aurora_boundary_exc,
            context={"function": "write_presence_frame", "source_file": "aurora_internal/dual_strata/subsurface_presence.py"},
        )

    return frame


# ── Event -> PresenceFrame integration (Build 694 step 3/4) ────────────────
#
# Shared by both consumers of the turn-events channel: aurora_daemon.py's
# main loop (_consume_subsurface_turn_events, the slow ~15-30s-cadence
# backstop) and SubsurfacePresenceRuntime (subsurface_presence_runtime.py,
# the fast dedicated thread step 4 adds) -- one implementation, so the two
# consumers can never quietly drift apart on what "integrating an event"
# actually means.

def integrate_turn_open_event(state_dir: Any, event: Dict[str, Any]) -> None:
    """A turn_open event only ever tells Subsurface that SOMETHING is
    happening now -- it must not stomp interpretation fields an
    interpreted_turn event for the same turn may already have written
    this cycle (write_presence_frame()'s same-turn merge is what makes
    that safe)."""
    write_presence_frame(
        state_dir,
        turn_id=str(event.get("turn_id", "") or ""),
        continuity_summary=f"turn open: {str(event.get('raw_input', ''))[:120]}",
        turn_open_at=float(event.get("created_at", 0.0) or 0.0),
    )


def integrate_interpreted_turn_event(state_dir: Any, event: Dict[str, Any]) -> None:
    """An interpreted_turn event carries the actual substance
    aurora._emit_interpreted_turn_packet() computed -- interpreted_meaning/
    inferred_purpose/confidence/response_fit_pressure/etc. Merged onto
    whatever turn_open already established for the same turn_id, never
    collapsing/overwriting it."""
    write_presence_frame(
        state_dir,
        turn_id=str(event.get("turn_id", "") or ""),
        interpreted_at=float(event.get("created_at", 0.0) or 0.0),
        interpreted_meaning=str(event.get("interpreted_meaning", "") or ""),
        inferred_purpose=str(event.get("inferred_purpose", "") or ""),
        current_topic=str(event.get("current_topic", "") or ""),
        interpretation_confidence=float(event.get("interpretation_confidence", 0.0) or 0.0),
        response_confidence=float(event.get("response_confidence", 0.0) or 0.0),
        resolved_referents=list(event.get("resolved_referents", []) or []),
        unresolved_ambiguity=list(event.get("unresolved_ambiguity", []) or []),
        knowledge_gaps=list(event.get("knowledge_gaps", []) or []),
        representation_refs=list(event.get("representation_refs", []) or []),
        response_fit_pressure=float(event.get("response_fit_pressure", 0.0) or 0.0),
        continuity_summary=(str(event.get("interpreted_meaning", "") or "")[:120] or None),
    )


def integrate_evidence_need_event(state_dir: Any, event: Dict[str, Any]) -> Optional[str]:
    """Build 694 step 9: the sole conversion point from "Surface described
    a need" to "a ScoutRequest actually got dispatched." Local/lazy
    imports (not module-level) because this is the one function in this
    module that reaches into aurora_internal.scouting -- keeping that
    reach as narrow and visible as possible, and avoiding paying that
    import cost for every other event kind this module integrates.

    Failure here must never propagate into the turn-events consumption
    loop (a dispatch failure is not fatal to presence-frame integration
    generally) -- caught and swallowed the same way every other write in
    this module already treats its own I/O failures."""
    try:
        from aurora_internal.scouting.broker import dispatch_scout_request
        from aurora_internal.scouting.contracts import ScoutRequest
        dispatch_scout_request(state_dir, ScoutRequest(
            turn_id=str(event.get("turn_id", "") or ""),
            request_kind=str(event.get("request_kind", "") or "knowledge_gap"),
            interpreted_input=str(event.get("target", "") or ""),
            inquiry=str(event.get("inquiry", "") or ""),
            evidence_needed=str(event.get("evidence_needed", "") or ""),
            representation_refs=list(event.get("representation_refs", []) or []),
            priority=float(event.get("priority", 0.5) or 0.5),
            max_result_chars=int(event.get("max_result_chars", 1200) or 1200),
            ttl_s=float(event.get("ttl_s", 30.0) or 30.0),
        ))
    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(), module=__name__,
            operation="exception_handler:aurora_internal/dual_strata/subsurface_presence.py:integrate_evidence_need_event",
            exc=_aurora_boundary_exc,
            context={"function": "integrate_evidence_need_event", "source_file": "aurora_internal/dual_strata/subsurface_presence.py"},
        )
        return None
    return "evidence_need"


def integrate_turn_event(state_dir: Any, event: Dict[str, Any]) -> Optional[str]:
    """Dispatch one event by kind (Build 694 step 3's required shape).
    Returns the kind actually integrated, or None if this event's kind
    has no handler yet (turn_outcome has no producer at this point in
    the implementation order)."""
    if not isinstance(event, dict):
        return None
    kind = str(event.get("kind", "") or "")
    if kind == "turn_open":
        integrate_turn_open_event(state_dir, event)
        return kind
    if kind == "interpreted_turn":
        integrate_interpreted_turn_event(state_dir, event)
        return kind
    if kind == "evidence_need":
        return integrate_evidence_need_event(state_dir, event)
    return None


def read_presence_frame(state_dir: Any) -> Optional[Dict[str, Any]]:
    """Surface calls this to sample the freshest presence frame --
    NEVER blocks waiting for a new one; a missing/unreadable frame
    simply returns None so the caller falls back to internal state."""
    root = _resolve(state_dir)
    path = root / _PRESENCE_FRAME_FILENAME
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else None
    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(), module=__name__,
            operation="exception_handler:aurora_internal/dual_strata/subsurface_presence.py:read_presence_frame",
            exc=_aurora_boundary_exc,
            context={"function": "read_presence_frame", "source_file": "aurora_internal/dual_strata/subsurface_presence.py"},
        )
        return None


def presence_frame_age_ms(state_dir: Any) -> Optional[float]:
    """subsurface_presence_frame_age_ms -- None if no frame has ever
    been written yet."""
    frame = read_presence_frame(state_dir)
    if not frame:
        return None
    try:
        return max(0.0, (time.time() - float(frame.get("generated_at", 0.0) or 0.0)) * 1000.0)
    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(), module=__name__,
            operation="exception_handler:aurora_internal/dual_strata/subsurface_presence.py:presence_frame_age_ms",
            exc=_aurora_boundary_exc,
            context={"function": "presence_frame_age_ms", "source_file": "aurora_internal/dual_strata/subsurface_presence.py"},
        )
        return None


# ── Heartbeat (Subsurface liveness, independent of frame content) ──────────

def write_heartbeat(state_dir: Any) -> None:
    """Subsurface's main loop calls this roughly once per second,
    regardless of whether the presence frame's CONTENT changed --
    proves the loop is alive even when nothing else did. Deliberately
    the cheapest possible write: one small file, one field."""
    root = _resolve(state_dir)
    path = root / _HEARTBEAT_FILENAME
    try:
        _atomic_write(path, {"ts": time.time()})
    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(), module=__name__,
            operation="exception_handler:aurora_internal/dual_strata/subsurface_presence.py:write_heartbeat",
            exc=_aurora_boundary_exc,
            context={"function": "write_heartbeat", "source_file": "aurora_internal/dual_strata/subsurface_presence.py"},
        )


def heartbeat_gap_ms(state_dir: Any) -> Optional[float]:
    """subsurface_heartbeat_gap_ms -- None if Subsurface has never
    heartbeat at all (e.g. daemon not running)."""
    root = _resolve(state_dir)
    path = root / _HEARTBEAT_FILENAME
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        ts = float(raw.get("ts", 0.0) or 0.0) if isinstance(raw, dict) else 0.0
        if ts <= 0.0:
            return None
        return max(0.0, (time.time() - ts) * 1000.0)
    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(), module=__name__,
            operation="exception_handler:aurora_internal/dual_strata/subsurface_presence.py:heartbeat_gap_ms",
            exc=_aurora_boundary_exc,
            context={"function": "heartbeat_gap_ms", "source_file": "aurora_internal/dual_strata/subsurface_presence.py"},
        )
        return None

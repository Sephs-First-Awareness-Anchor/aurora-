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
) -> str:
    """Surface calls this the instant a turn is accepted, BEFORE the full
    response pipeline runs. Does not trigger a Scout -- purely a presence
    signal. Returns the event_id."""
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

def write_presence_frame(
    state_dir: Any,
    *,
    turn_id: str = "",
    crest: Optional[Dict[str, Any]] = None,
    active_pressure: Optional[Dict[str, Any]] = None,
    continuity_summary: str = "",
    unresolved_tensions: Optional[List[str]] = None,
    scout_requests_pending: int = 0,
    scout_evidence_integrated: Optional[List[str]] = None,
    response_fit_pressure: float = 0.0,
    evidence_bindings: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Subsurface calls this whenever turn state or Scout evidence
    actually changes -- NOT on a fixed interval. Deliberately not the
    60s daemon_status.json write path (see module docstring, section 14
    of the spec). Returns the frame written, including its own
    sequence number."""
    root = _resolve(state_dir)
    path = root / _PRESENCE_FRAME_FILENAME

    prev_seq = 0
    try:
        if path.exists():
            prev = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(prev, dict):
                prev_seq = int(prev.get("seq", 0) or 0)
    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(), module=__name__,
            operation="exception_handler:aurora_internal/dual_strata/subsurface_presence.py:write_presence_frame:read_prev",
            exc=_aurora_boundary_exc,
            context={"function": "write_presence_frame", "source_file": "aurora_internal/dual_strata/subsurface_presence.py"},
        )
        prev_seq = 0

    frame: Dict[str, Any] = {
        "seq": prev_seq + 1,
        "generated_at": time.time(),
        "turn_id": str(turn_id or ""),
        "crest": crest if isinstance(crest, dict) else None,
        "active_pressure": active_pressure if isinstance(active_pressure, dict) else None,
        "continuity_summary": str(continuity_summary or "")[:400],
        "unresolved_tensions": [str(t) for t in list(unresolved_tensions or []) if str(t).strip()][:6],
        "scout_requests_pending": max(0, int(scout_requests_pending or 0)),
        "scout_evidence_integrated": [str(e) for e in list(scout_evidence_integrated or [])][:12],
        "response_fit_pressure": round(max(0.0, min(1.0, float(response_fit_pressure or 0.0))), 4),
        "evidence_bindings": list(evidence_bindings or [])[:8],
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

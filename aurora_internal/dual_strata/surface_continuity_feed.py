"""
Surface → Subsurface continuity handoff.

Core architectural law:
    Surface translates present experience into subsurface continuity.

Surface calls write_continuity_packet() after each turn.
Subsurface calls read_and_clear_continuity_packets() each loop cycle
and integrates the result into its continuity state.

Without this handoff, Surface is theatrical: it sees, hears, and talks
but the organism does not absorb the moment.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations
from aurora_internal.aurora_runtime_faults import record_exception_from_locals as _aurora_record_exception_from_locals

import functools
import json
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

_FEED_FILENAME = "surface_continuity_feed.json"
_MAX_PACKETS = 20

# FIX-A118: every function here is a read-modify-write of one file.  Atomic
# replace prevents torn JSON but not lost updates between threads of one
# process (the phone's turn thread vs the strata link; the subsurface loop vs
# the link server it hosts).  One in-process lock covers all of them.
_FEED_LOCK = threading.RLock()


def _feed_locked(fn):
    @functools.wraps(fn)
    def _wrapper(*args, **kwargs):
        with _FEED_LOCK:
            return fn(*args, **kwargs)
    return _wrapper


def _resolve(state_dir: Any) -> Path:
    if state_dir is not None:
        return Path(str(state_dir))
    return Path(__file__).resolve().parents[2] / "aurora_state"


@_feed_locked
def write_continuity_packet(
    state_dir: Any,
    *,
    user_input: str = "",
    aurora_response: str = "",
    response_tone: str = "attentive",
    concepts_activated: List[str] = (),
    visual_description: str = "",
    audio_description: str = "",
    recent_speech: str = "",
    dominant_axis: str = "",
    coherence: float = 0.0,
    felt_wrong: bool = False,
    wrong_reason: str = "",
    unresolved_tensions: List[str] = (),
    resolved_bindings: List[str] = (),
    source: str = "surface_turn",
) -> str:
    """
    Write a present-state continuity packet to the feed.

    Called by Surface after each turn. Returns the packet_id.
    Each packet represents one awake moment that must accumulate
    into subsurface continuity — not just be logged and forgotten.
    """
    root = _resolve(state_dir)
    feed_path = root / _FEED_FILENAME

    packet_id = uuid.uuid4().hex
    packet: Dict[str, Any] = {
        "packet_id": packet_id,
        "created_at": time.time(),
        "source": str(source or "surface_turn"),
        # Live present-contact content (what Surface gathered)
        "user_input": str(user_input or "")[:500],
        "aurora_response": str(aurora_response or "")[:800],
        "response_tone": str(response_tone or "attentive"),
        # Sensory context Surface owned during this moment
        "concepts_activated": [str(c) for c in list(concepts_activated or []) if str(c).strip()][:12],
        "visual_description": str(visual_description or "")[:240],
        "audio_description": str(audio_description or "")[:240],
        "recent_speech": str(recent_speech or "")[:200],
        # Present frame state Surface derived
        "dominant_axis": str(dominant_axis or ""),
        "coherence": round(max(0.0, min(1.0, float(coherence or 0.0))), 4),
        "felt_wrong": bool(felt_wrong),
        "wrong_reason": str(wrong_reason or "")[:220],
        # What changed in this moment — the continuity-relevant delta
        "unresolved_tensions": [str(t) for t in list(unresolved_tensions or []) if str(t).strip()][:6],
        "resolved_bindings": [str(b) for b in list(resolved_bindings or []) if str(b).strip()][:6],
        # Consumption tracking
        "consumed": False,
        "consumed_at": None,
    }

    try:
        existing: List[Dict[str, Any]] = []
        if feed_path.exists():
            try:
                raw = json.loads(feed_path.read_text(encoding="utf-8"))
                if isinstance(raw, list):
                    existing = raw
            except Exception as _aurora_boundary_exc:
                _aurora_record_exception_from_locals(
                    locals(),
                    module=__name__,
                    operation="exception_handler:aurora_internal/dual_strata/surface_continuity_feed.py:95",
                    exc=_aurora_boundary_exc,
                    context={"function": "write_continuity_packet", "handler_line": 95, "source_file": "aurora_internal/dual_strata/surface_continuity_feed.py"},
                )
                existing = []
        existing.append(packet)
        existing = existing[-_MAX_PACKETS:]
        tmp = feed_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(existing, indent=2), encoding="utf-8")
        tmp.replace(feed_path)
    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(),
            module=__name__,
            operation="exception_handler:aurora_internal/dual_strata/surface_continuity_feed.py:102",
            exc=_aurora_boundary_exc,
            context={"function": "write_continuity_packet", "handler_line": 102, "source_file": "aurora_internal/dual_strata/surface_continuity_feed.py"},
        )
        pass

    return packet_id


@_feed_locked
def read_and_clear_continuity_packets(state_dir: Any) -> List[Dict[str, Any]]:
    """
    Atomically read all unconsumed continuity packets and mark them consumed.

    Called by Subsurface each loop cycle. Returns the pending packets.
    After this call, those packets are marked consumed and will not be
    returned again — Subsurface owns the integration from this point.
    """
    root = _resolve(state_dir)
    feed_path = root / _FEED_FILENAME
    if not feed_path.exists():
        return []

    try:
        raw = json.loads(feed_path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            return []
    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(),
            module=__name__,
            operation="exception_handler:aurora_internal/dual_strata/surface_continuity_feed.py:125",
            exc=_aurora_boundary_exc,
            context={"function": "read_and_clear_continuity_packets", "handler_line": 125, "source_file": "aurora_internal/dual_strata/surface_continuity_feed.py"},
        )
        return []

    pending = [p for p in raw if isinstance(p, dict) and not bool(p.get("consumed", False))]
    if not pending:
        return []

    now = time.time()
    for p in raw:
        if isinstance(p, dict) and not bool(p.get("consumed", False)):
            p["consumed"] = True
            p["consumed_at"] = now

    raw = raw[-_MAX_PACKETS:]
    try:
        tmp = feed_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(raw, indent=2), encoding="utf-8")
        tmp.replace(feed_path)
    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(),
            module=__name__,
            operation="exception_handler:aurora_internal/dual_strata/surface_continuity_feed.py:143",
            exc=_aurora_boundary_exc,
            context={"function": "read_and_clear_continuity_packets", "handler_line": 143, "source_file": "aurora_internal/dual_strata/surface_continuity_feed.py"},
        )
        pass

    return pending


@_feed_locked
def peek_continuity_packets(state_dir: Any) -> List[Dict[str, Any]]:
    """Unconsumed packets, without consuming them (FIX-A118).

    The strata link copies these into its durable outbox BEFORE consuming,
    so a crash between the two steps repeats a packet rather than losing it
    (the receiving side de-duplicates by packet_id).
    """
    feed_path = _resolve(state_dir) / _FEED_FILENAME
    if not feed_path.exists():
        return []
    try:
        raw = json.loads(feed_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(raw, list):
        return []
    return [dict(p) for p in raw if isinstance(p, dict) and not bool(p.get("consumed", False))]


@_feed_locked
def deposit_continuity_packet(state_dir: Any, packet: Dict[str, Any]) -> bool:
    """Deposit a packet a Surface on ANOTHER device already wrote (FIX-A118).

    The packet keeps its own packet_id, created_at and content exactly as the
    originating Surface recorded them; only consumption tracking is reset, so
    this Subsurface's read_and_clear_continuity_packets() receives it like any
    locally written packet.  A packet_id already in the feed is not deposited
    twice.  Unlike write_continuity_packet, no unconsumed packet is ever
    trimmed here: a backlog arriving after a long disconnect must all reach
    the Subsurface.  Returns True when the packet was added.
    """
    if not isinstance(packet, dict):
        return False
    packet_id = str(packet.get("packet_id") or "")
    if not packet_id:
        return False
    root = _resolve(state_dir)
    root.mkdir(parents=True, exist_ok=True)
    feed_path = root / _FEED_FILENAME
    existing: List[Dict[str, Any]] = []
    if feed_path.exists():
        try:
            raw = json.loads(feed_path.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                existing = [p for p in raw if isinstance(p, dict)]
        except Exception as _aurora_boundary_exc:
            _aurora_record_exception_from_locals(
                locals(),
                module=__name__,
                operation="exception_handler:aurora_internal/dual_strata/surface_continuity_feed.py:deposit_continuity_packet:read",
                exc=_aurora_boundary_exc,
                context={"function": "deposit_continuity_packet", "source_file": "aurora_internal/dual_strata/surface_continuity_feed.py"},
            )
            existing = []
    if any(str(p.get("packet_id") or "") == packet_id for p in existing):
        return False
    deposited = dict(packet)
    deposited["consumed"] = False
    deposited["consumed_at"] = None
    existing.append(deposited)
    consumed = [p for p in existing if bool(p.get("consumed", False))][-_MAX_PACKETS:]
    unconsumed = [p for p in existing if not bool(p.get("consumed", False))]
    tmp = feed_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(consumed + unconsumed, indent=2), encoding="utf-8")
    tmp.replace(feed_path)
    return True

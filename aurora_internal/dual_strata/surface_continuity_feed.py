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
from aurora_internal.aurora_runtime_faults import bind_fault_recorder as _bind_fault_recorder
_aurora_fault = _bind_fault_recorder(__name__, 'aurora_internal/dual_strata/surface_continuity_feed.py')

import functools
import json
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List

_FEED_FILENAME = "surface_continuity_feed.json"
_MAX_PACKETS = 20
# Home's durable record of every lived moment it has integrated (surface
# restructure 3e): seqs as ranges per (device, epoch), plus recent packet ids
# for packets that carry no numbering.  A redelivery is recognised however
# late it comes, not only while it is still in the feed.
_LEDGER_FILENAME = "surface_continuity_ledger.json"
_LEDGER_RECENT_IDS = 5000

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
        **_lived_stamp(root),
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
                _aurora_fault(locals(), _aurora_boundary_exc, 'write_continuity_packet', 95)
                existing = []
        existing.append(packet)
        # Only consumed packets are trimmed: an unconsumed lived moment waits
        # for whoever integrates or carries it, however many follow it.
        consumed = [p for p in existing if isinstance(p, dict) and bool(p.get("consumed", False))]
        unconsumed = [p for p in existing if isinstance(p, dict) and not bool(p.get("consumed", False))]
        existing = consumed[-_MAX_PACKETS:] + unconsumed
        tmp = feed_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(existing, indent=2), encoding="utf-8")
        tmp.replace(feed_path)
    except Exception as _aurora_boundary_exc:
        _aurora_fault(locals(), _aurora_boundary_exc, 'write_continuity_packet', 102)
        pass

    return packet_id


def _lived_stamp(root: Path) -> Dict[str, Any]:
    """(surface_id, epoch, seq) for this lived moment, from the strata link's
    numbering.  A device that cannot number it still writes the packet; it
    is then recognised by packet_id alone."""
    try:
        from aurora_internal.dual_strata.strata_link import stamp_lived_moment
        return dict(stamp_lived_moment(root))
    except Exception as _aurora_boundary_exc:
        _aurora_fault(locals(), _aurora_boundary_exc, '_lived_stamp', 0)
        return {}


def _ledger_load(root: Path) -> Dict[str, Any]:
    try:
        raw = json.loads((root / _LEDGER_FILENAME).read_text(encoding="utf-8"))
    except Exception:
        raw = {}
    raw = raw if isinstance(raw, dict) else {}
    return {"ranges": {str(k): [[int(a), int(b)] for a, b in v]
                       for k, v in dict(raw.get("ranges") or {}).items()},
            "recent_ids": [str(i) for i in (raw.get("recent_ids") or [])][-_LEDGER_RECENT_IDS:],
            "late": int(raw.get("late", 0) or 0),
            "duplicates": int(raw.get("duplicates", 0) or 0)}


def _ledger_save(root: Path, ledger: Dict[str, Any]) -> None:
    tmp = (root / _LEDGER_FILENAME).with_suffix(".json.tmp")
    tmp.write_text(json.dumps(ledger), encoding="utf-8")
    tmp.replace(root / _LEDGER_FILENAME)


def _ledger_key(packet: Dict[str, Any]) -> str:
    if packet.get("surface_id") and packet.get("epoch") is not None and packet.get("seq"):
        return f"{packet['surface_id']}:{int(packet['epoch'])}"
    return ""


def _in_ranges(ranges: List[List[int]], seq: int) -> bool:
    return any(a <= seq <= b for a, b in ranges)


def _add_to_ranges(ranges: List[List[int]], seq: int) -> List[List[int]]:
    merged: List[List[int]] = []
    for a, b in sorted(ranges + [[seq, seq]]):
        if merged and a <= merged[-1][1] + 1:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return merged


@_feed_locked
def integrated_ledger_status(state_dir: Any) -> Dict[str, Any]:
    """What home has integrated: high-water seq per (device, epoch), gaps
    (lived moments not yet arrived), late arrivals and refused duplicates."""
    ledger = _ledger_load(_resolve(state_dir))
    devices = {}
    for key, ranges in ledger["ranges"].items():
        devices[key] = {"high_water": ranges[-1][1] if ranges else 0,
                        "missing": sum(max(0, ranges[i + 1][0] - ranges[i][1] - 1)
                                       for i in range(len(ranges) - 1)) + (ranges[0][0] - 1 if ranges else 0)}
    return {"devices": devices, "late": ledger["late"], "duplicates_refused": ledger["duplicates"]}


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
        _aurora_fault(locals(), _aurora_boundary_exc, 'read_and_clear_continuity_packets', 125)
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
        _aurora_fault(locals(), _aurora_boundary_exc, 'read_and_clear_continuity_packets', 143)
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
def deposit_continuity_packet(state_dir: Any, packet: Dict[str, Any], *, late: bool = False) -> bool:
    """Deposit a packet a Surface on ANOTHER device already wrote (FIX-A118).

    The packet keeps its own packet_id, created_at and content exactly as the
    originating Surface recorded them; only consumption tracking is reset, so
    this Subsurface's read_and_clear_continuity_packets() receives it like any
    locally written packet.  A packet_id already in the feed is not deposited
    twice.  Unlike write_continuity_packet, no unconsumed packet is ever
    trimmed here: a backlog arriving after a long disconnect must all reach
    the Subsurface.  Returns True when the packet was added.

    Home's integrated ledger (surface restructure 3e) recognises a packet it
    has already integrated by its (device, epoch, seq) or its packet_id, even
    long after it left the feed, so a duplicate delivery never becomes a
    duplicate experience.  ``late`` tags a packet a superseded device
    delivered after the role moved on; it is integrated all the same.
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
    ledger = _ledger_load(root)
    key = _ledger_key(packet)
    seq = int(packet.get("seq", 0) or 0) if key else 0
    if (key and _in_ranges(ledger["ranges"].get(key, []), seq)) or packet_id in ledger["recent_ids"] \
            or any(str(p.get("packet_id") or "") == packet_id for p in existing):
        ledger["duplicates"] += 1
        _ledger_save(root, ledger)
        return False
    deposited = dict(packet)
    deposited["consumed"] = False
    deposited["consumed_at"] = None
    if late:
        deposited["arrived_late"] = True
    existing.append(deposited)
    consumed = [p for p in existing if bool(p.get("consumed", False))][-_MAX_PACKETS:]
    unconsumed = [p for p in existing if not bool(p.get("consumed", False))]
    tmp = feed_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(consumed + unconsumed, indent=2), encoding="utf-8")
    tmp.replace(feed_path)
    # Recorded after the feed holds it: a crash between the two repeats the
    # deposit attempt, which the feed check above still recognises.
    if key:
        ledger["ranges"][key] = _add_to_ranges(ledger["ranges"].get(key, []), seq)
    ledger["recent_ids"] = (ledger["recent_ids"] + [packet_id])[-_LEDGER_RECENT_IDS:]
    if late:
        ledger["late"] += 1
    _ledger_save(root, ledger)
    return True

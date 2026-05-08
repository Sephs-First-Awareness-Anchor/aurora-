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
from __future__ import annotations

import json
import time
import uuid
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional

_FEED_FILENAME = "surface_continuity_feed.json"
_MAX_PACKETS = 20


def _resolve(state_dir: Any) -> Path:
    if state_dir is not None:
        return Path(str(state_dir))
    return Path(__file__).resolve().parents[2] / "aurora_state"


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
    root = _resolve(state_dir)
    feed_path = root / _FEED_FILENAME

    packet_id = uuid.uuid4().hex
    packet: Dict[str, Any] = {
        "packet_id": packet_id,
        "created_at": time.time(),
        "source": str(source or "surface_turn"),
        "user_input": str(user_input or "")[:500],
        "aurora_response": str(aurora_response or "")[:800],
        "response_tone": str(response_tone or "attentive"),
        "concepts_activated": [str(c) for c in list(concepts_activated or []) if str(c).strip()][:12],
        "visual_description": str(visual_description or "")[:240],
        "audio_description": str(audio_description or "")[:240],
        "recent_speech": str(recent_speech or "")[:200],
        "dominant_axis": str(dominant_axis or ""),
        "coherence": round(max(0.0, min(1.0, float(coherence or 0.0))), 4),
        "felt_wrong": bool(felt_wrong),
        "wrong_reason": str(wrong_reason or "")[:220],
        "unresolved_tensions": [str(t) for t in list(unresolved_tensions or []) if str(t).strip()][:6],
        "resolved_bindings": [str(b) for b in list(resolved_bindings or []) if str(b).strip()][:6],
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
            except Exception:
                existing = []
        existing.append(packet)
        existing = existing[-_MAX_PACKETS:]
        tmp = feed_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(existing, indent=2), encoding="utf-8")
        tmp.replace(feed_path)
    except Exception:
        pass

    return packet_id


def read_and_clear_continuity_packets(state_dir: Any) -> List[Dict[str, Any]]:
    root = _resolve(state_dir)
    feed_path = root / _FEED_FILENAME
    if not feed_path.exists():
        return []

    try:
        raw = json.loads(feed_path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            return []
    except Exception:
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
    except Exception:
        pass

    return pending


class SurfaceContinuityFeed:
    def __init__(self, max_events: int = 240, *args: Any, **kwargs: Any) -> None:
        self.max_events = int(max_events or 240)
        self.events = deque(maxlen=self.max_events)
        self.created_at = time.time()

    def record(self, event: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Dict[str, Any]:
        payload = dict(event or {})
        payload.update(kwargs)
        payload.setdefault("ts", time.time())
        self.events.append(payload)
        return {"recorded": True, "count": len(self.events)}

    def recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        limit = max(1, int(limit or 20))
        return list(self.events)[-limit:]

    def drain(self, limit: int = 20) -> List[Dict[str, Any]]:
        out = []
        limit = max(1, int(limit or 20))
        while self.events and len(out) < limit:
            out.append(self.events.popleft())
        return out

    def status(self) -> Dict[str, Any]:
        return {
            "available": True,
            "created_at": self.created_at,
            "count": len(self.events),
            "max_events": self.max_events,
        }

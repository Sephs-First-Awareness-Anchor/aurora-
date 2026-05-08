"""
aurora_internal.dual_strata

Compatibility bridge for Aurora's surface/subsurface split.

This exports DualStrataBridge directly, satisfying:

    from aurora_internal.dual_strata import DualStrataBridge

It also exposes request_surface_turn for:

    from aurora_internal.dual_strata.surface_channel import request_surface_turn
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

try:
    from .surface_channel import request_surface_turn
except Exception:
    def request_surface_turn(*args: Any, **kwargs: Any) -> str:
        prompt = str(kwargs.get("prompt", "") or (args[0] if args else "") or "")
        return prompt or "Surface channel active."

try:
    from .surface_continuity_feed import SurfaceContinuityFeed
except Exception:
    class SurfaceContinuityFeed:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.events = []
        def record(self, event: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Dict[str, Any]:
            payload = dict(event or {})
            payload.update(kwargs)
            self.events.append(payload)
            return {"recorded": True, "count": len(self.events)}
        def recent(self, limit: int = 20):
            return self.events[-int(limit or 20):]
        def status(self) -> Dict[str, Any]:
            return {"available": True, "count": len(self.events)}

try:
    from .sleep_cycle import SleepCycleManager
except Exception:
    class SleepCycleManager:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.last_tick = 0.0
        def tick(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
            self.last_tick = time.time()
            return {"slept": False, "reason": "compatibility_noop"}
        def status(self) -> Dict[str, Any]:
            return {"available": True, "last_tick": self.last_tick}


class DualStrataBridge:
    """
    Minimal bridge object expected by Aurora's consciousness/runtime stack.

    Surface = interactive communication layer.
    Subsurface = background continuity, study, dream, pressure, sediment.

    This compatibility version is safe: it logs/passes events and degrades
    gracefully instead of forcing behavior.
    """

    def __init__(self, systems: Optional[Dict[str, Any]] = None, state_dir: str = "", **kwargs: Any) -> None:
        self.systems = systems or {}
        self.state_dir = state_dir
        self.kwargs = dict(kwargs)
        self.created_at = time.time()
        self.surface_feed = SurfaceContinuityFeed()
        self.sleep_cycle = SleepCycleManager()
        self.surface_events = []
        self.subsurface_events = []

    def surface_turn(self, prompt: str = "", **kwargs: Any) -> str:
        event = {
            "ts": time.time(),
            "kind": "surface_turn",
            "prompt": str(prompt or ""),
            "kwargs": dict(kwargs),
        }
        self.surface_events.append(event)
        try:
            self.surface_feed.record(event)
        except Exception:
            pass

        try:
            return request_surface_turn(prompt, systems=self.systems, **kwargs)
        except TypeError:
            try:
                return request_surface_turn(prompt, **kwargs)
            except Exception:
                return str(prompt or "")
        except Exception:
            return str(prompt or "")

    def request_surface_turn(self, prompt: str = "", **kwargs: Any) -> str:
        return self.surface_turn(prompt, **kwargs)

    def record_surface_event(self, event: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Dict[str, Any]:
        payload = dict(event or {})
        payload.update(kwargs)
        payload.setdefault("ts", time.time())
        payload.setdefault("kind", "surface_event")
        self.surface_events.append(payload)
        try:
            self.surface_feed.record(payload)
        except Exception:
            pass
        return {"recorded": True, "surface_events": len(self.surface_events)}

    def record_subsurface_event(self, event: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Dict[str, Any]:
        payload = dict(event or {})
        payload.update(kwargs)
        payload.setdefault("ts", time.time())
        payload.setdefault("kind", "subsurface_event")
        self.subsurface_events.append(payload)
        return {"recorded": True, "subsurface_events": len(self.subsurface_events)}

    def handoff_to_subsurface(self, payload: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Dict[str, Any]:
        event = dict(payload or {})
        event.update(kwargs)
        event.setdefault("handoff", True)
        return self.record_subsurface_event(event)

    def pull_surface_continuity(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        return {
            "available": True,
            "surface_events": list(self.surface_events[-20:]),
            "subsurface_events": list(self.subsurface_events[-20:]),
        }

    def tick(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        try:
            sleep = self.sleep_cycle.tick(*args, **kwargs)
        except Exception:
            sleep = {"slept": False}
        return {
            "available": True,
            "sleep": sleep,
            "surface_events": len(self.surface_events),
            "subsurface_events": len(self.subsurface_events),
        }

    def status(self) -> Dict[str, Any]:
        return {
            "available": True,
            "created_at": self.created_at,
            "surface_events": len(self.surface_events),
            "subsurface_events": len(self.subsurface_events),
            "surface_feed": self.surface_feed.status() if hasattr(self.surface_feed, "status") else {},
            "sleep_cycle": self.sleep_cycle.status() if hasattr(self.sleep_cycle, "status") else {},
        }

    def get_status(self) -> Dict[str, Any]:
        return self.status()


__all__ = [
    "DualStrataBridge",
    "request_surface_turn",
    "SurfaceContinuityFeed",
    "SleepCycleManager",
]

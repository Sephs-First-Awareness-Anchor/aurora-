"""
Dual-strata cognition primitives for the experimental Aurora strata tree.
"""

from .crest import Crest, CrestBundle
from .conscious_frame import ConsciousFrame
from .contextual_overlay import ContextualOverlay
from .dce_bridge import DualStrataBridge, DualStrataSnapshot
from .downward_traversal import expand_crest
from .micro_reasoning import MicroReasoningHypothesis, generate_micro_reasoning
from .prediction_field import PredictionPayload, PredictionSignal, build_prediction_signal
from .subsurface_state import SubsurfaceState
from .subsystem_waveforms import emit_subsystem_crests

try:
    from .surface_channel import request_surface_turn
except Exception:
    from typing import Any as _Any
    def request_surface_turn(*args: _Any, **kwargs: _Any) -> str:
        prompt = str(kwargs.get("prompt", "") or (args[0] if args else "") or "")
        return prompt or "Surface channel active."

try:
    from .surface_continuity_feed import SurfaceContinuityFeed
except Exception:
    import time as _time
    from typing import Any as _Any, Dict as _Dict, Optional as _Optional
    class SurfaceContinuityFeed:
        def __init__(self, *args: _Any, **kwargs: _Any) -> None:
            self.events = []
        def record(self, event: _Optional[_Dict[str, _Any]] = None, **kwargs: _Any) -> _Dict[str, _Any]:
            payload = dict(event or {})
            payload.update(kwargs)
            self.events.append(payload)
            return {"recorded": True, "count": len(self.events)}
        def recent(self, limit: int = 20):
            return self.events[-int(limit or 20):]
        def status(self) -> _Dict[str, _Any]:
            return {"available": True, "count": len(self.events)}

try:
    from .sleep_cycle import SleepCycleManager
except Exception:
    import time as _time
    from typing import Any as _Any, Dict as _Dict
    class SleepCycleManager:
        def __init__(self, *args: _Any, **kwargs: _Any) -> None:
            self.last_tick = 0.0
        def tick(self, *args: _Any, **kwargs: _Any) -> _Dict[str, _Any]:
            self.last_tick = _time.time()
            return {"slept": False, "reason": "compatibility_noop"}
        def status(self) -> _Dict[str, _Any]:
            return {"available": True, "last_tick": self.last_tick}

__all__ = [
    "Crest",
    "CrestBundle",
    "ConsciousFrame",
    "ContextualOverlay",
    "DualStrataBridge",
    "DualStrataSnapshot",
    "MicroReasoningHypothesis",
    "PredictionPayload",
    "PredictionSignal",
    "SubsurfaceState",
    "SurfaceContinuityFeed",
    "SleepCycleManager",
    "build_prediction_signal",
    "emit_subsystem_crests",
    "expand_crest",
    "generate_micro_reasoning",
    "request_surface_turn",
]

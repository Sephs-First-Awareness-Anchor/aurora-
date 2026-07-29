# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations
from aurora_internal.aurora_runtime_faults import record_exception_from_locals as _aurora_record_exception_from_locals

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Tuple

# Keep AXES, clip01, normalize_axis_map as-is for backward compat
AXES = ("X", "T", "N", "B", "A")

def clip01(value, default=0.0):
    try:
        return max(0.0, min(1.0, float(value or 0.0)))
    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(),
            module=__name__,
            operation="exception_handler:aurora_internal/dual_strata/subsurface_state.py:14",
            exc=_aurora_boundary_exc,
            context={"function": "clip01", "handler_line": 14, "source_file": "aurora_internal/dual_strata/subsurface_state.py"},
        )
        return max(0.0, min(1.0, float(default or 0.0)))

def normalize_axis_map(values):
    raw = {}
    for axis in AXES:
        raw[axis] = max(0.0, float(values.get(axis, 0.0) or 0.0))
    total = sum(raw.values())
    if total <= 1e-9:
        return {axis: 0.0 for axis in AXES}
    return {axis: round(raw[axis] / total, 4) for axis in AXES}


@dataclass
class SubsurfaceState:
    """Recursively generalized subsurface meaning-state. Holds ONLY crests
    and the converged subsurface crest — no raw subsystem mechanism."""

    subsurface_crest: "Crest"                   # the converged crest
    sub_crests: Tuple["Crest", ...]             # the eight micro-crests (frozen)
    dominant_axis: str                          # routing only
    frame_request: str                          # carry through
    overlay: "ContextualOverlay"                # present-moment overlay
    # Kept for downward traversal ONLY — MUST NOT be read by surface consumers.
    _subsurface_detail: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Public upward stream — no _subsurface_detail."""
        return {
            "subsurface_crest": self.subsurface_crest.to_dict(),
            "sub_crests": [c.to_dict() for c in (self.sub_crests or ())],
            "dominant_axis": str(self.dominant_axis or "X"),
            "frame_request": str(self.frame_request or "balanced"),
            "overlay": self.overlay.to_dict() if self.overlay else {},
        }

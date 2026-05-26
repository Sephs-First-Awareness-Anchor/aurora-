# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Crest primitive — the only object that may propagate upward through Aurora's
strata. Implements the Recursive Crest Propagation Law.

A Crest is the minimal generalized semantic abstraction produced by a
subsystem waveform. It is intentionally lossy: rationale, mechanism, raw
numeric state, and intermediate scaffolding remain in the subsystem and are
reachable only via downward traversal.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Tuple

from .subsurface_state import AXES, clip01


@dataclass(frozen=True)
class Crest:
    label: str
    intensity: float
    axis: str = "X"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": str(self.label or "").strip().lower() or "steady",
            "intensity": round(clip01(self.intensity), 4),
            "axis": self.axis if self.axis in AXES else "X",
        }


@dataclass
class CrestBundle:
    """A collection of micro-crests from subsystem waveforms, plus the converged
    parent crest that summarizes them. Only ``converged`` propagates upward.
    Sub-crests are retained behind the bundle for downward traversal only."""

    converged: Crest
    sub_crests: Tuple[Crest, ...] = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "converged": self.converged.to_dict(),
            "sub_crests": [c.to_dict() for c in self.sub_crests],
        }

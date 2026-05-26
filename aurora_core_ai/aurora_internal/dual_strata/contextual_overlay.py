# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
ContextualOverlay — transient present-state projection onto activated crystals.
Never permanent. Only fields satisfying embedding_condition are eligible for
inward crystallization elsewhere.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ContextualOverlay:
    """Transient present-state projection onto activated crystals.
    NEVER permanent. Only fields here that satisfy the
    `embedding_condition` check (emotional significance, recursive
    reinforcement, continuity importance, symbolic weight, or novelty
    pressure) are eligible for inward crystallization elsewhere."""

    present_anchor: str = ""           # the input fragment being held
    active_crystals: List[str] = field(default_factory=list)   # crystal ids
    present_sensory: Dict[str, Any] = field(default_factory=dict)  # mic/cam/snap
    present_tone: str = "neutral"
    interaction_state: str = "present"  # present | followup | recall
    reinforcement_hint: float = 0.0     # 0..1 — likelihood of inward crystallization

    def to_dict(self) -> Dict[str, Any]:
        return {
            "present_anchor": str(self.present_anchor or ""),
            "active_crystals": list(self.active_crystals or []),
            "present_sensory": dict(self.present_sensory or {}),
            "present_tone": str(self.present_tone or "neutral"),
            "interaction_state": str(self.interaction_state or "present"),
            "reinforcement_hint": round(max(0.0, min(1.0, float(self.reinforcement_hint or 0.0))), 4),
        }

    def embedding_eligible(self) -> bool:
        """True iff this overlay should be considered for inward crystallization.
        Inward crystallization itself is performed elsewhere (sedimemory /
        sensory_crystal); this method only signals eligibility upward."""
        return self.reinforcement_hint >= 0.55

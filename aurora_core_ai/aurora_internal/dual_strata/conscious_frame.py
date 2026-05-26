# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
ConsciousFrame — the conscious crest plus the overlay it navigates.
Nothing else. All raw mechanism lives in SubsurfaceState._subsurface_detail.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict

from .subsurface_state import clip01

if TYPE_CHECKING:
    from .crest import Crest
    from .contextual_overlay import ContextualOverlay

# Crest label → natural language fragment for summary_for_language()
_CREST_SUMMARIES: Dict[str, str] = {
    "explain": "ready to explain clearly",
    "clarify": "needs clarification before proceeding",
    "comfort": "responding with care and warmth",
    "hold": "holding the current moment",
    "contextualize": "contextualizing within the active thread",
    "reframe": "reframing to find better footing",
    "attend": "attentive and present",
    "familiar": "this feels familiar and grounded",
    "uncertain": "navigating some uncertainty",
    "novel": "encountering something new",
    "safe": "in a steady and safe frame",
    "hesitation": "pausing with gentle hesitation",
    "reframe_needed": "a reframe seems needed here",
    "continuity_pull": "feeling a pull toward the thread",
    "comfort_bias": "biased toward warmth and comfort",
    "steady": "holding steady",
    "caution": "proceeding with care",
    "warmth": "responding with warmth",
}


@dataclass
class ConsciousFrame:
    """The conscious crest plus the overlay it navigates. Nothing else."""

    conscious_crest: "Crest"          # converged conscious crest = response orientation
    subsurface_crest: "Crest"         # carry-up from below for stance/action selection
    overlay: "ContextualOverlay"      # present-moment contextualization
    stance: str                       # derived from conscious_crest.label
    selected_action: str              # derived from conscious_crest.label
    should_speak: bool                # derived from conscious_crest.intensity + overlay
    readiness: float                  # surface-visible readiness (clip01)
    coherence: float                  # surface-visible coherence (clip01)
    dominant_axis: str                # routing
    processing_mode: str = "deliberative"  # deliberative | reactive | blended | holding
    timestamp: float = field(default_factory=time.time)

    def summary_for_language(self) -> str:
        """ONE human-natural sentence summarizing the crest+overlay.
        This is what the language generator consumes."""
        label = str(self.conscious_crest.label or "steady").strip().lower()
        fragment = _CREST_SUMMARIES.get(label, f"oriented toward {label}")
        anchor = str(getattr(self.overlay, "present_anchor", "") or "").strip()
        tone = str(getattr(self.overlay, "present_tone", "") or "neutral").strip()
        if anchor and tone and tone not in {"neutral", "calm"}:
            return f"Aurora is {fragment}, anchored in '{anchor}' with a {tone} tone."
        if anchor:
            return f"Aurora is {fragment}, anchored in '{anchor}'."
        if tone and tone not in {"neutral", "calm"}:
            return f"Aurora is {fragment} with a {tone} tone."
        return f"Aurora is {fragment}."

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conscious_crest": self.conscious_crest.to_dict(),
            "subsurface_crest": self.subsurface_crest.to_dict(),
            "overlay": self.overlay.to_dict() if self.overlay else {},
            "stance": str(self.stance or "attend"),
            "selected_action": str(self.selected_action or "hold"),
            "should_speak": bool(self.should_speak),
            "readiness": round(clip01(self.readiness), 4),
            "coherence": round(clip01(self.coherence), 4),
            "dominant_axis": str(self.dominant_axis or "X"),
            "processing_mode": str(self.processing_mode or "deliberative"),
            "timestamp": float(self.timestamp or 0.0),
        }

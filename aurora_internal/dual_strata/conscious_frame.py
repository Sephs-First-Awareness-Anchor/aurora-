from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

from .subsurface_state import clip01


@dataclass
class ConsciousFrame:
    """The explicit frame the surface stratum can inhabit for one moment."""

    frame_name: str
    stance: str
    interpretation: str
    selected_action: str
    should_speak: bool
    readiness: float
    coherence: float
    dominant_axis: str
    processing_mode: str = "deliberative"
    root_thought: Dict[str, Any] = field(default_factory=dict)
    reactive_signal: Dict[str, Any] = field(default_factory=dict)
    unresolved_conflicts: List[str] = field(default_factory=list)
    salient_hypotheses: List[Dict[str, Any]] = field(default_factory=list)
    sensory_summary: Dict[str, Any] = field(default_factory=dict)
    prediction: Dict[str, Any] = field(default_factory=dict)
    contract_signals: Dict[str, Any] = field(default_factory=dict)
    explicit_notes: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["readiness"] = round(clip01(self.readiness), 4)
        data["coherence"] = round(clip01(self.coherence), 4)
        return data

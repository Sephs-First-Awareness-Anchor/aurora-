from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

AXES = ("X", "T", "N", "B", "A")


def clip01(value: Any, default: float = 0.0) -> float:
    try:
        return max(0.0, min(1.0, float(value or 0.0)))
    except Exception:
        return max(0.0, min(1.0, float(default or 0.0)))


def normalize_axis_map(values: Dict[str, Any]) -> Dict[str, float]:
    raw: Dict[str, float] = {}
    for axis in AXES:
        raw[axis] = max(0.0, float(values.get(axis, 0.0) or 0.0))
    total = sum(raw.values())
    if total <= 1e-9:
        return {axis: 0.0 for axis in AXES}
    return {axis: round(raw[axis] / total, 4) for axis in AXES}


@dataclass
class SubsurfaceState:
    """Continuous, pre-symbolic state prepared ahead of explicit interpretation."""

    dominant_axis: str
    frame_request: str
    coherence: float
    salience_weights: Dict[str, float]
    pressure_map: Dict[str, float]
    readiness: float
    sensory_summary: Dict[str, Any] = field(default_factory=dict)
    native_meaning: Dict[str, Any] = field(default_factory=dict)
    native_meaning_bundle: Dict[str, Any] = field(default_factory=dict)
    recalled_fragments: List[str] = field(default_factory=list)
    candidate_interpretations: List[Dict[str, Any]] = field(default_factory=list)
    instability_markers: List[Dict[str, Any]] = field(default_factory=list)
    action_bias_candidates: List[Dict[str, Any]] = field(default_factory=list)
    contract_signals: Dict[str, Any] = field(default_factory=dict)
    prediction: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def dominant_candidates(self, limit: int = 3) -> List[Dict[str, Any]]:
        ranked = sorted(
            (dict(item) for item in self.candidate_interpretations if isinstance(item, dict)),
            key=lambda item: float(item.get("confidence", 0.0) or 0.0),
            reverse=True,
        )
        return ranked[: max(1, int(limit or 1))]

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["coherence"] = round(clip01(self.coherence), 4)
        data["readiness"] = round(clip01(self.readiness), 4)
        data["salience_weights"] = normalize_axis_map(self.salience_weights)
        data["pressure_map"] = normalize_axis_map(self.pressure_map)
        data["candidate_interpretations"] = self.dominant_candidates()
        return data

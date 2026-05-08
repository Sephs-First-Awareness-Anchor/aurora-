from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from .subsurface_state import SubsurfaceState, clip01


@dataclass
class MicroReasoningHypothesis:
    label: str
    confidence: float
    rationale: str
    source: str
    urgency: float = 0.0
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["confidence"] = round(clip01(self.confidence), 4)
        data["urgency"] = round(clip01(self.urgency), 4)
        return data


def generate_micro_reasoning(
    subsurface: SubsurfaceState,
    *,
    assembly_result: Optional[Any] = None,
    evidence: Optional[Dict[str, Any]] = None,
    contract_snapshot: Optional[Dict[str, Any]] = None,
) -> List[MicroReasoningHypothesis]:
    evidence = dict(evidence or {})
    contract_snapshot = dict(contract_snapshot or {})
    contract_b = dict(contract_snapshot.get("B", {}) or {})
    contract_m = dict(contract_snapshot.get("M", {}) or {})
    prediction = dict(subsurface.prediction or {})

    hypotheses: List[MicroReasoningHypothesis] = []
    mismatch = clip01(prediction.get("mismatch", 0.0))
    ambiguity = clip01(contract_b.get("ambiguity", 0.0))
    coherence = clip01(subsurface.coherence)
    dominant_axis = str(subsurface.dominant_axis or "").upper()
    tracked_surface_emotion = str(
        subsurface.contract_signals.get("dominant_emotion")
        or subsurface.contract_signals.get("tracked_surface_emotion")
        or evidence.get("tone")
        or "neutral"
    ).lower()
    deep_emotion = str(
        subsurface.contract_signals.get("interpreted_deep_emotion")
        or tracked_surface_emotion
        or "neutral"
    ).lower()
    deep_passion = str(subsurface.contract_signals.get("interpreted_deep_passion") or "").lower()

    if mismatch >= 0.45:
        hypotheses.append(
            MicroReasoningHypothesis(
                label="prediction_mismatch",
                confidence=mismatch,
                urgency=max(mismatch, 1.0 - coherence),
                rationale="Observed input diverged from the currently primed continuation.",
                source="prediction",
                tags=["reframe", "surprise"],
            )
        )

    if ambiguity >= 0.55 or dominant_axis == "B":
        hypotheses.append(
            MicroReasoningHypothesis(
                label="clarification_pressure",
                confidence=max(ambiguity, clip01(subsurface.salience_weights.get("B", 0.0))),
                urgency=max(ambiguity, 0.35),
                rationale="Boundary clarity is weak enough that surface interpretation should stay careful.",
                source="boundary",
                tags=["clarify", "frame_guard"],
            )
        )

    if clip01(contract_m.get("frame_continuity", 0.0)) >= 0.55 or bool(contract_snapshot.get("O", {}).get("callback", False)):
        hypotheses.append(
            MicroReasoningHypothesis(
                label="callback_pressure",
                confidence=max(
                    clip01(contract_m.get("frame_continuity", 0.0)),
                    clip01(subsurface.salience_weights.get("T", 0.0)),
                ),
                urgency=0.45,
                rationale="Prior context is exerting enough pull to bias the next conscious frame.",
                source="memory_resonance",
                tags=["continuity", "context"],
            )
        )

    if (
        deep_emotion in {"sad", "hurt", "fear", "afraid", "anxious", "upset"}
        or deep_passion in {"protective_commitment", "concerned_hold"}
    ):
        hypotheses.append(
            MicroReasoningHypothesis(
                label="comfort_bias",
                confidence=max(0.5, clip01(subsurface.salience_weights.get("A", 0.0))),
                urgency=0.55,
                rationale="Deeper affective pressure suggests comfort or care may matter more than pure explanation.",
                source="affect",
                tags=["care", "attunement"],
            )
        )

    if getattr(assembly_result, "paradoxes", None):
        hypotheses.append(
            MicroReasoningHypothesis(
                label="conflict_exposure",
                confidence=max(0.6, clip01(1.0 - coherence)),
                urgency=max(0.6, clip01(1.0 - coherence)),
                rationale="The active assembly still contains paradox or unresolved conflict.",
                source="assembly",
                tags=["conflict", "stability"],
            )
        )

    _novelty = clip01(
        getattr(assembly_result, "entropy_state", {}).get("novelty", 0.0)
        if assembly_result else 0.0
    )
    if _novelty >= 0.65:
        hypotheses.append(
            MicroReasoningHypothesis(
                label="novelty_attention",
                confidence=_novelty,
                urgency=0.4,
                rationale="Novelty is high enough that the frame should stay exploratory.",
                source="entropy",
                tags=["novelty", "exploration"],
            )
        )

    # --- Tool selection ---
    # Fires when subsurface geometry signals that external data grounding is needed.
    # Tags carry the specific tool hint downstream (e.g. tool:weather, tool:time).
    source_text = str(
        evidence.get("source_text") or evidence.get("user_text") or ""
    ).lower()
    intent_type = str(prediction.get("intent_type") or "").lower()

    _tool_conf = 0.0
    _tool_tags: List[str] = []
    _tool_rationale = ""

    if intent_type == "lookup_offer":
        # Prediction field already flagged a lookup — strongest subsurface signal
        _tool_conf = 0.85
        _tool_tags = ["tool:lookup"]
        _tool_rationale = "Prediction field signals lookup_offer — external data retrieval is anticipated."

    elif dominant_axis == "T" and any(
        w in source_text for w in {
            "time", "date", "day", "hour", "today", "when",
            "morning", "tonight", "schedule", "clock",
        }
    ):
        _tool_conf = 0.78
        _tool_tags = ["tool:time"]
        _tool_rationale = "T-axis dominant with temporal vocabulary — time grounding needed."

    elif dominant_axis in ("T", "X") and any(
        w in source_text for w in {
            "weather", "temperature", "rain", "snow", "wind",
            "forecast", "hot outside", "cold outside", "warm outside", "humid",
        }
    ):
        _tool_conf = 0.80
        _tool_tags = ["tool:weather"]
        _tool_rationale = f"{dominant_axis}-axis with weather vocabulary — weather grounding needed."

    elif dominant_axis == "N" and (
        any(w in source_text for w in {
            "calculate", "compute", "plus", "minus", "times", "divided", "percent",
            "how many", "how much",
        })
        or bool(re.search(r'\d+\s*[+\-*/]\s*\d+', source_text))
    ):
        _tool_conf = 0.75
        _tool_tags = ["tool:calculator"]
        _tool_rationale = "N-axis dominant with numeric expression — calculation grounding needed."

    elif dominant_axis == "A" and any(
        w in source_text for w in {
            "camera", "mic", "heat", "coherence", "systems",
            "sensor", "running", "schedule", "thermal", "status",
        }
    ):
        _tool_conf = 0.72
        _tool_tags = ["tool:self_state"]
        _tool_rationale = "A-axis dominant with self-referential vocabulary — introspective state read needed."

    elif _novelty >= 0.65 and any(
        w in source_text for w in {
            "time", "date", "schedule", "when", "how long", "what time",
        }
    ):
        _tool_conf = 0.62
        _tool_tags = ["tool:time", "tool:schedule"]
        _tool_rationale = "High novelty with schedule vocabulary — time/schedule grounding may resolve uncertainty."

    if _tool_conf >= 0.60:
        hypotheses.append(
            MicroReasoningHypothesis(
                label="tool_selection",
                confidence=_tool_conf,
                urgency=round(_tool_conf * 0.85, 4),
                rationale=_tool_rationale,
                source="subsurface_axis",
                tags=_tool_tags,
            )
        )

    ranked = sorted(hypotheses, key=lambda item: (item.urgency, item.confidence), reverse=True)
    return ranked[:6]

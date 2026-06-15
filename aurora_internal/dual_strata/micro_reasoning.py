# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

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
    # NOTE (FIX-A009): SubsurfaceState no longer carries prediction/coherence/
    # contract_signals/salience_weights as top-level attributes -- the
    # Recursive Crest Propagation Law moved all of that into
    # subsurface._subsurface_detail. dominant_axis is the one attribute that
    # still exists directly on SubsurfaceState.
    _detail = subsurface._subsurface_detail or {}
    prediction = dict(_detail.get("prediction_signal") or {})
    _contract_signals = dict(_detail.get("contract_signals") or {})
    _salience_weights = dict(_detail.get("salience_weights") or {})

    hypotheses: List[MicroReasoningHypothesis] = []
    mismatch = clip01(prediction.get("mismatch", 0.0))
    ambiguity = clip01(contract_b.get("ambiguity", 0.0))
    coherence = clip01(_detail.get("coherence", 0.0))
    dominant_axis = str(subsurface.dominant_axis or "").upper()
    tracked_surface_emotion = str(
        _contract_signals.get("dominant_emotion")
        or _contract_signals.get("tracked_surface_emotion")
        or evidence.get("tone")
        or "neutral"
    ).lower()
    deep_emotion = str(
        _contract_signals.get("interpreted_deep_emotion")
        or tracked_surface_emotion
        or "neutral"
    ).lower()
    deep_passion = str(_contract_signals.get("interpreted_deep_passion") or "").lower()

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
                confidence=max(ambiguity, clip01(_salience_weights.get("B", 0.0))),
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
                    clip01(_salience_weights.get("T", 0.0)),
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
                confidence=max(0.5, clip01(_salience_weights.get("A", 0.0))),
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

    if clip01(getattr(assembly_result, "entropy_state", {}).get("novelty", 0.0)) >= 0.65:
        hypotheses.append(
            MicroReasoningHypothesis(
                label="novelty_attention",
                confidence=clip01(getattr(assembly_result, "entropy_state", {}).get("novelty", 0.0)),
                urgency=0.4,
                rationale="Novelty is high enough that the frame should stay exploratory.",
                source="entropy",
                tags=["novelty", "exploration"],
            )
        )

    ranked = sorted(hypotheses, key=lambda item: (item.urgency, item.confidence), reverse=True)
    return ranked[:5]

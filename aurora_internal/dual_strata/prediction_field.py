# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from .subsurface_state import clip01


# ---------------------------------------------------------------------------
# Structured prediction payload
# ---------------------------------------------------------------------------

@dataclass
class PredictionPayload:
    """Structured description of what Aurora expects to observe next.

    Replaces the old flat ``expected_observation: str`` field, which was a
    single token like "clarification" or "followup" compared against observed
    text via Jaccard overlap — a comparison that was always near-zero for
    short intent tokens.
    """
    topic: str = ""
    """Active conversation topic at prediction time."""

    affect: str = "neutral"
    """Expected dominant emotion in the next user turn."""

    intent_type: str = "followup"
    """Expected response type: clarification | selection | confirmation |
    followup | grounded_response | grounded_answer | meaning_reasoning |
    contradiction_surfacing | lookup_offer"""

    certainty_band: str = "medium"
    """Derived from projected_accuracy: low (<0.40) | medium | high (>0.70)."""

    axis_signature: str = ""
    """Dominant IVM axis at prediction time (X/T/N/B/A)."""


def _certainty_band(accuracy: float) -> str:
    if accuracy < 0.40:
        return "low"
    if accuracy > 0.70:
        return "high"
    return "medium"


# ---------------------------------------------------------------------------
# Intent-type matching
# ---------------------------------------------------------------------------

_CLARIFICATION_SIGNALS = frozenset({
    "what do", "what is", "what are", "i mean", "by that", "how does",
    "can you explain", "what exactly", "not sure", "clarify", "rephrase",
})
_CONFIRMATION_SIGNALS = frozenset({
    "yes", "yep", "yeah", "correct", "exactly", "right", "that works",
    "makes sense", "thank you", "thanks", "ok", "okay", "got it",
})
_SELECTION_SIGNALS = frozenset({
    "keep", "drop", "use", "choose", "pick", "go with", "this one", "that one",
    "prefer", "rather",
})


def _match_intent_type(intent_type: str, obs_low: str) -> float:
    """Return 0.0..1.0 match score for the expected intent type vs observed text.

    A score of 1.0 means the observed text is clearly consistent with the
    predicted intent; 0.0 means clearly inconsistent.
    """
    is_question = obs_low.rstrip().endswith("?")
    has_clarification = is_question or any(s in obs_low for s in _CLARIFICATION_SIGNALS)
    has_confirmation = any(s in obs_low for s in _CONFIRMATION_SIGNALS)
    has_selection = any(s in obs_low for s in _SELECTION_SIGNALS)

    if intent_type == "clarification":
        if has_clarification:
            return 1.0
        if has_confirmation:
            return 0.25
        return 0.20

    if intent_type == "confirmation":
        if has_confirmation:
            return 1.0
        if has_clarification:
            return 0.25
        return 0.20

    if intent_type == "selection":
        if has_selection:
            return 1.0
        if has_confirmation:
            return 0.55  # accepting without explicit selection word is close
        return 0.20

    if intent_type in (
        "followup", "grounded_response", "grounded_answer",
        "meaning_reasoning", "contradiction_surfacing", "lookup_offer",
    ):
        # These are soft expectations — most continued input qualifies.
        # Penalise only clearly off-track cases (abrupt topic change, silence).
        if has_clarification and not is_question:
            return 0.60  # clarification mid-followup is plausible
        return 0.75

    # Unknown intent type — neutral
    return 0.50


# ---------------------------------------------------------------------------
# Multi-dimensional mismatch
# ---------------------------------------------------------------------------

def _structured_mismatch(
    payload: PredictionPayload,
    observed_text: str,
    observed_tone: str = "",
) -> float:
    """Compute prediction mismatch from structured dimensions.

    Weights:
      intent_type    45 %  — was the kind of response we expected actually given?
      topic          30 %  — does the observed input still reference the topic?
      affect         25 %  — is the emotional register consistent?
    """
    obs_low = str(observed_text or "").lower()

    # --- intent type ---
    intent_score = _match_intent_type(payload.intent_type, obs_low)
    intent_miss = 1.0 - intent_score

    # --- topic continuity ---
    topic_miss = 0.0
    if payload.topic:
        topic_words = set(re.findall(r"[a-z]{3,}", payload.topic.lower()))
        obs_words = set(re.findall(r"[a-z]{3,}", obs_low))
        stop = {"the", "and", "for", "are", "was", "has", "but", "not",
                "you", "that", "this", "with", "from", "they", "have"}
        topic_words -= stop
        if topic_words and not (topic_words & obs_words):
            topic_miss = 0.55  # topic diverged
        elif not topic_words:
            topic_miss = 0.0   # no topic to compare

    # --- affect ---
    affect_miss = 0.0
    exp_affect = str(payload.affect or "neutral").lower()
    if exp_affect and exp_affect != "neutral":
        obs_tone = str(observed_tone or "").lower()
        affect_miss = 0.0 if exp_affect in obs_tone else 0.45

    return clip01(
        intent_miss * 0.45 + topic_miss * 0.30 + affect_miss * 0.25
    )


# ---------------------------------------------------------------------------
# PredictionSignal
# ---------------------------------------------------------------------------

@dataclass
class PredictionSignal:
    # Structured payload (replaces plain expected_observation string)
    prediction_payload: PredictionPayload = field(default_factory=PredictionPayload)

    # Kept for backward-compat read paths (dce_bridge line 526 note generation)
    # Populated from payload.intent_type so existing consumers still work.
    expected_observation: str = ""

    expected_user_continuation: str = ""
    likely_affect_shift: str = ""
    confidence: float = 0.0
    mismatch: float = 0.0
    readiness_bias: float = 0.0
    source: str = ""
    alerts: List[str] = field(default_factory=list)
    preload_context: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["confidence"] = round(clip01(self.confidence), 4)
        data["mismatch"] = round(clip01(self.mismatch), 4)
        data["readiness_bias"] = round(max(-1.0, min(1.0, float(self.readiness_bias or 0.0))), 4)
        return data


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

def build_prediction_signal(
    *,
    payload: Any,
    evidence: Optional[Dict[str, Any]] = None,
    contract_snapshot: Optional[Dict[str, Any]] = None,
    sensory_context: Optional[Dict[str, Any]] = None,
    entropy_state: Optional[Dict[str, Any]] = None,
    manifold_axis: Optional[str] = None,
    manifold_familiarity: Optional[float] = None,
) -> PredictionSignal:
    """
    manifold_axis / manifold_familiarity: read from the SAME constraint
    manifold CERS's tensor-trace pass resolves the current moment onto
    (cers_tensor_locator.py) -- entered here as plain values, not a SlotCoord
    or Crystal, so this module stays decoupled from CERS/crystal internals.
    manifold_axis backstops axis_signature when no contract/evidence axis is
    present (previously this was very often blank). manifold_familiarity
    (0..1, from how many times Aurora's real experience has actually visited
    this coordinate -- 0.0 for a coordinate she's never been at) blends into
    projected_accuracy: real precedent at this coordinate is legitimate
    grounds for more confident prediction; a coordinate with no precedent
    yet is legitimate grounds for less. Both optional and additive -- when
    absent (the caller has no dps / the pressure vector wasn't available),
    behavior is identical to before this parameter existed.
    """
    evidence = dict(evidence or {})
    contract_snapshot = dict(contract_snapshot or {})
    sensory_context = dict(sensory_context or {})
    entropy_state = dict(entropy_state or {})

    contract_pi = dict(contract_snapshot.get("Pi", {}) or {})
    contract_a = dict(contract_snapshot.get("A", {}) or {})
    contract_p = dict(contract_snapshot.get("P", {}) or {})
    contract_m = dict(contract_snapshot.get("M", {}) or {})
    contract_b = dict(contract_snapshot.get("B", {}) or {})
    surface_reactive = dict(contract_p.get("surface_reactive_emotion", {}) or {})

    # --- Build structured payload ---
    # The Pi section stores a token like "clarification" / "followup" / etc.
    # as expected_observation — that token IS the intent_type.
    raw_intent_token = str(
        evidence.get("expected_observation")
        or contract_pi.get("expected_observation")
        or "followup"
    ).strip() or "followup"

    topic = str(
        evidence.get("active_topic")
        or contract_m.get("active_topic")
        or ""
    ).strip()

    affect = str(
        evidence.get("affect_shift")
        or surface_reactive.get("dominant")
        or contract_p.get("dominant_emotion")
        or evidence.get("tone")
        or "neutral"
    ).strip() or "neutral"

    projected_accuracy = clip01(
        contract_pi.get("projected_accuracy", contract_a.get("projected_next", 0.5)),
        default=0.5,
    )
    used_manifold_confidence = False
    if manifold_familiarity is not None:
        projected_accuracy = clip01(0.65 * projected_accuracy + 0.35 * clip01(manifold_familiarity))
        used_manifold_confidence = True

    axis_sig = str(
        contract_p.get("dominant_axis")
        or evidence.get("dominant_axis")
        or (manifold_axis or "")
    ).strip()

    pred_payload = PredictionPayload(
        topic=topic,
        affect=affect,
        intent_type=raw_intent_token,
        certainty_band=_certainty_band(projected_accuracy),
        axis_signature=axis_sig,
    )

    # --- Build observed text for mismatch comparison ---
    observed_text = " ".join(
        part
        for part in (
            str(payload or ""),
            str(evidence.get("source_text", "") or ""),
            str(sensory_context.get("summary", "") or ""),
        )
        if part
    )
    observed_tone = str(evidence.get("tone", "") or "").lower()

    # --- Multi-dimensional mismatch ---
    mismatch = _structured_mismatch(pred_payload, observed_text, observed_tone)

    novelty = clip01(entropy_state.get("novelty", 0.0))
    if novelty >= 0.7:
        mismatch = clip01(mismatch + 0.1)

    confidence = clip01(projected_accuracy * 0.65 + (1.0 - mismatch) * 0.35, default=0.35)

    # --- Continuation hint (used as context preload) ---
    expected_continuation = str(
        evidence.get("expected_user_continuation")
        or topic
        or contract_m.get("active_topic")
        or ""
    ).strip()

    # --- Alerts ---
    alerts: List[str] = []
    if mismatch >= 0.45:
        alerts.append("prediction_mismatch")
    if clip01(contract_b.get("ambiguity", 0.0)) >= 0.55:
        alerts.append("boundary_uncertainty")
    if novelty >= 0.7:
        alerts.append("novelty_shift")

    # --- Preload context ---
    preload_context: List[str] = []
    for value in (
        topic,
        raw_intent_token,
        sensory_context.get("dominant_facet"),
    ):
        text = str(value or "").strip()
        if text and text not in preload_context:
            preload_context.append(text)

    readiness_bias = round(
        (1.0 - mismatch) * 0.5
        + confidence * 0.3
        - clip01(contract_b.get("ambiguity", 0.0)) * 0.2,
        4,
    )

    base_source = "understanding_contract" if contract_snapshot else "runtime_evidence"
    return PredictionSignal(
        prediction_payload=pred_payload,
        expected_observation=raw_intent_token,   # backward-compat note generation
        expected_user_continuation=expected_continuation,
        likely_affect_shift=affect,
        confidence=confidence,
        mismatch=mismatch,
        readiness_bias=readiness_bias,
        source=base_source + ("+manifold" if used_manifold_confidence else ""),
        alerts=alerts,
        preload_context=preload_context,
    )

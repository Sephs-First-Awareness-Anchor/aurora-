# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Subsystem waveforms — eight pure functions, each compressing one subsystem's
evidence slice into exactly ONE Crest.  No subsystem returns a dict, packet,
list of hypotheses, rationale string, or numeric map.

Only the orchestrator `emit_subsystem_crests` is the entry point for the
dce_bridge. Anything new must be added here, never inlined into the bridge.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from .crest import Crest
from .subsurface_state import AXES, clip01


# ---------------------------------------------------------------------------
# 1. Sensory waveform
# ---------------------------------------------------------------------------

def sensory_waveform(evidence: Dict[str, Any], sensory_context: Dict[str, Any]) -> Crest:
    # Authors: Sunni (Sir) Morningstar & Cael Devo
    tone = str(evidence.get("tone", "") or sensory_context.get("dominant_facet", "") or "").lower()
    maturity = clip01(sensory_context.get("maturity", 0.5))
    total_frames = int(sensory_context.get("total_frames", 0) or 0)

    if tone in {"hostile", "aggressive", "angry", "confrontational"}:
        return Crest(label="hostile_tone", intensity=0.85, axis="A")
    if tone in {"warm", "friendly", "supportive", "caring", "kind"}:
        return Crest(label="warm_tone", intensity=0.75, axis="A")
    if total_frames > 0 and maturity < 0.3:
        return Crest(label="sensory_irregularity", intensity=round(1.0 - maturity, 4), axis="X")
    if tone in {"urgent", "alert", "alarmed"}:
        return Crest(label="alert", intensity=0.80, axis="X")
    if maturity >= 0.7 and total_frames > 0:
        return Crest(label="perceptually_steady", intensity=round(maturity, 4), axis="X")
    if maturity > 0 and maturity < 0.55:
        return Crest(label="attentional_drift", intensity=round(1.0 - maturity, 4), axis="X")
    return Crest(label="perceptually_steady", intensity=0.6, axis="X")


# ---------------------------------------------------------------------------
# 2. Memory waveform
# ---------------------------------------------------------------------------

def memory_waveform(evidence: Dict[str, Any], contract_snapshot: Dict[str, Any]) -> Crest:
    # Authors: Sunni (Sir) Morningstar & Cael Devo
    contract_m = dict(contract_snapshot.get("M", {}) or {})
    working_memory = dict(evidence.get("working_memory_snapshot", {}) or {})
    conversation_memory = dict(evidence.get("conversation_memory", {}) or {})
    continuity_recall = list(evidence.get("continuity_recall", []) or [])

    frame_continuity = clip01(contract_m.get("frame_continuity", 0.0))
    active_topic = str(contract_m.get("active_topic", "") or "").strip()
    has_recall = bool(continuity_recall or conversation_memory.get("summary"))

    if has_recall and frame_continuity >= 0.65:
        return Crest(label="resonant_recall", intensity=round(frame_continuity, 4), axis="T")
    if active_topic and frame_continuity >= 0.45:
        return Crest(label="continuity_pull", intensity=round(frame_continuity, 4), axis="T")
    if active_topic and frame_continuity >= 0.25:
        return Crest(label="familiar", intensity=round(max(0.4, frame_continuity), 4), axis="T")
    if has_recall and frame_continuity < 0.25:
        return Crest(label="continuity_stable", intensity=0.55, axis="T")
    if not active_topic and not has_recall:
        return Crest(label="unfamiliar", intensity=0.65, axis="T")
    return Crest(label="familiar", intensity=0.5, axis="T")


# ---------------------------------------------------------------------------
# 3. Emotional waveform
# ---------------------------------------------------------------------------

def emotional_waveform(evidence: Dict[str, Any], contract_snapshot: Dict[str, Any]) -> Crest:
    # Authors: Sunni (Sir) Morningstar & Cael Devo
    contract_p = dict(contract_snapshot.get("P", {}) or {})
    established_turn = dict(evidence.get("established_turn_state", {}) or {})
    surface_reactive = dict(
        contract_p.get("surface_reactive_emotion")
        or established_turn.get("surface_reactive_emotion")
        or {}
    )
    deep_emotional = dict(
        contract_p.get("deep_emotional_state")
        or established_turn.get("deep_emotional_state")
        or {}
    )
    emotion_bridge = dict(
        contract_p.get("emotion_bridge")
        or established_turn.get("emotion_bridge")
        or {}
    )

    surface_emotion = str(
        surface_reactive.get("dominant", "")
        or contract_p.get("dominant_emotion", "")
        or evidence.get("tone", "")
        or "neutral"
    ).lower()
    surface_intensity = clip01(surface_reactive.get("intensity", 0.0))
    deep_emotion = str(
        deep_emotional.get("dominant", "")
        or contract_p.get("deep_dominant_emotion", "")
        or surface_emotion
    ).lower()
    surface_bias = str(surface_reactive.get("behavior_bias", "") or "").strip()

    if surface_emotion in {"sad", "hurt", "fear", "afraid", "anxious", "upset", "vulnerable"}:
        return Crest(label="comfort_bias", intensity=max(0.65, surface_intensity), axis="A")
    if surface_emotion in {"angry", "hostile", "confrontational"}:
        return Crest(label="caution", intensity=max(0.7, surface_intensity), axis="A")
    if deep_emotion in {"warm", "friendly", "caring", "affectionate"} or surface_bias == "lean_in":
        return Crest(label="warmth", intensity=max(0.55, surface_intensity), axis="A")
    if surface_bias in {"slow_down", "probe"} or deep_emotion in {"hesitant", "uncertain", "cautious"}:
        return Crest(label="hesitation", intensity=max(0.45, surface_intensity), axis="A")
    if surface_emotion in {"neutral", "calm"} and deep_emotion in {"neutral", "calm"}:
        return Crest(label="neutral_affect", intensity=0.5, axis="A")
    return Crest(label="neutral_affect", intensity=0.4, axis="A")


# ---------------------------------------------------------------------------
# 4. Prediction waveform
# ---------------------------------------------------------------------------

def prediction_waveform(prediction_signal_obj: Any) -> Crest:
    # Authors: Sunni (Sir) Morningstar & Cael Devo
    # Compresses an existing PredictionSignal to a single crest.
    # Does NOT delete PredictionSignal — it stays subsurface-only.
    if prediction_signal_obj is None:
        return Crest(label="steady_continuation", intensity=0.5, axis="X")

    pred = prediction_signal_obj.to_dict() if hasattr(prediction_signal_obj, "to_dict") else dict(prediction_signal_obj or {})
    mismatch = clip01(pred.get("mismatch", 0.0))
    certainty_band = str(pred.get("certainty_band", "") or pred.get("prediction_payload", {}) and pred["prediction_payload"].get("certainty_band", "") or "medium")
    expected_obs = str(pred.get("expected_observation", "") or "").lower()

    if mismatch >= 0.65:
        return Crest(label="reframe_needed", intensity=round(mismatch, 4), axis="X")
    if mismatch >= 0.45:
        return Crest(label="surprise", intensity=round(mismatch, 4), axis="X")
    if certainty_band == "low" or mismatch >= 0.3:
        return Crest(label="low_certainty", intensity=round(max(0.45, mismatch), 4), axis="X")
    if "clarif" in expected_obs or "question" in expected_obs:
        return Crest(label="expectation", intensity=0.65, axis="X")
    if mismatch < 0.25 and certainty_band in {"medium", "high"}:
        return Crest(label="steady_continuation", intensity=round(1.0 - mismatch, 4), axis="X")
    return Crest(label="expectation", intensity=0.55, axis="X")


# ---------------------------------------------------------------------------
# 5. Symbolic waveform
# ---------------------------------------------------------------------------

def symbolic_waveform(assembly_result: Any, sensory_context: Dict[str, Any]) -> Crest:
    # Authors: Sunni (Sir) Morningstar & Cael Devo
    law_bindings = list(getattr(assembly_result, "law_bindings", []) or [])
    paradoxes = list(getattr(assembly_result, "paradoxes", []) or [])
    entropy_state = dict(getattr(assembly_result, "entropy_state", {}) or {})
    novelty = clip01(entropy_state.get("novelty", 0.0))
    coherence = clip01(getattr(assembly_result, "coherence", 0.5) or 0.5)

    if paradoxes:
        return Crest(label="contradiction", intensity=min(0.9, 0.5 + len(paradoxes) * 0.15), axis="B")
    if novelty >= 0.65:
        return Crest(label="novelty", intensity=round(novelty, 4), axis="N")
    if law_bindings and coherence >= 0.6:
        return Crest(label="resonance", intensity=round(coherence, 4), axis="X")
    if law_bindings and coherence >= 0.4:
        return Crest(label="alignment", intensity=round(coherence, 4), axis="X")
    if novelty >= 0.35:
        return Crest(label="novelty", intensity=round(novelty, 4), axis="N")
    return Crest(label="alignment", intensity=round(max(0.35, coherence), 4), axis="X")


# ---------------------------------------------------------------------------
# 6. Continuity waveform
# ---------------------------------------------------------------------------

def continuity_waveform(evidence: Dict[str, Any], contract_snapshot: Dict[str, Any]) -> Crest:
    # Authors: Sunni (Sir) Morningstar & Cael Devo
    contract_m = dict(contract_snapshot.get("M", {}) or {})
    frame_continuity = clip01(contract_m.get("frame_continuity", 0.0))
    active_topic = str(contract_m.get("active_topic", "") or "").strip()
    continuity_bundle = dict(evidence.get("subsurface_continuity_bundle", {}) or {})
    conversation_memory = dict(evidence.get("conversation_memory", {}) or {})
    continuity_recall = list(evidence.get("continuity_recall", []) or [])
    surface_frame = dict(evidence.get("surface_conversation_frame", {}) or {})
    current_topic = str(surface_frame.get("current_topic", "") or active_topic or "").strip()

    has_continuity = bool(continuity_bundle or conversation_memory.get("summary") or continuity_recall)

    if not current_topic and not has_continuity:
        return Crest(label="new_thread", intensity=0.7, axis="T")
    if frame_continuity < 0.25 and has_continuity:
        return Crest(label="thread_slipping", intensity=round(1.0 - frame_continuity, 4), axis="T")
    if frame_continuity >= 0.6 and current_topic:
        return Crest(label="thread_holds", intensity=round(frame_continuity, 4), axis="T")
    if has_continuity and frame_continuity < 0.5:
        return Crest(label="context_drag", intensity=round(max(0.35, 1.0 - frame_continuity), 4), axis="T")
    return Crest(label="thread_holds", intensity=round(max(0.4, frame_continuity), 4), axis="T")


# ---------------------------------------------------------------------------
# 7. Constraint waveform
# ---------------------------------------------------------------------------

def constraint_waveform(evidence: Dict[str, Any], projection: Dict[str, Any]) -> Crest:
    # Authors: Sunni (Sir) Morningstar & Cael Devo
    # Most common leak source — MUST compress to a single crest label,
    # never propagate raw numbers or governor strings.
    pressure_snapshot = dict(evidence.get("pressure_snapshot", {}) or {})
    governor_mode = str(pressure_snapshot.get("governor_mode", "") or "").lower()
    blocked_tasks = list(pressure_snapshot.get("blocked_tasks", []) or [])
    mem_available = float(pressure_snapshot.get("mem_available_mb", 9999.0) or 9999.0)
    axis_pressure = dict(pressure_snapshot.get("axis_pressure", {}) or pressure_snapshot.get("axes", {}) or {})
    max_pressure = max((clip01(v) for v in axis_pressure.values()), default=0.0)

    if governor_mode in {"critical", "emergency"} or bool(blocked_tasks):
        return Crest(label="strain", intensity=min(0.95, 0.7 + len(blocked_tasks) * 0.05), axis="N")
    if mem_available < 512 or governor_mode == "restricted":
        return Crest(label="limitation", intensity=0.75, axis="N")
    if max_pressure >= 0.75:
        return Crest(label="capacity", intensity=round(max_pressure, 4), axis="N")
    if max_pressure >= 0.45 or governor_mode in {"elevated", "watchful"}:
        return Crest(label="capacity", intensity=round(max(0.5, max_pressure), 4), axis="N")
    return Crest(label="steady_envelope", intensity=round(1.0 - max_pressure, 4), axis="N")


# ---------------------------------------------------------------------------
# 8. Pressure waveform
# ---------------------------------------------------------------------------

def pressure_waveform(adjusted_axes: Dict[str, float], pressure_snapshot: Dict[str, Any]) -> Crest:
    # Authors: Sunni (Sir) Morningstar & Cael Devo
    # Reduces the entire axis pressure map to one crest.
    # DO NOT propagate the pressure_map dict upward anymore.
    if not isinstance(pressure_snapshot, dict):
        pressure_snapshot = {}

    axis_vals = {
        axis: max(
            clip01(adjusted_axes.get(axis, 0.0)),
            clip01(pressure_snapshot.get(axis, 0.0)),
        )
        for axis in AXES
    }
    peak = max(axis_vals.values()) if axis_vals else 0.0
    peak_axis = max(axis_vals, key=axis_vals.get) if axis_vals else "X"

    if peak >= 0.78:
        label = "urgency" if peak_axis in {"X", "T"} else "discomfort"
        return Crest(label=label, intensity=round(peak, 4), axis=peak_axis)
    if peak >= 0.55:
        label = "tension" if peak_axis in {"B", "A"} else "discomfort"
        return Crest(label=label, intensity=round(peak, 4), axis=peak_axis)
    if peak >= 0.3:
        return Crest(label="tension", intensity=round(peak, 4), axis=peak_axis)
    return Crest(label="calm", intensity=round(1.0 - peak, 4), axis=peak_axis)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def emit_subsystem_crests(
    *,
    assembly_result: Any,
    payload: Any,
    evidence: Dict[str, Any],
    contract_snapshot: Dict[str, Any],
    prediction_signal: Any,
    projection: Dict[str, Any],
    sensory_context: Dict[str, Any],
    adjusted_axes: Dict[str, float],
    pressure_snapshot: Dict[str, Any],
) -> Tuple[Crest, ...]:
    """Run all eight subsystem waveforms and return their crests in canonical
    order. This is the ONLY entry point dce_bridge may use."""
    return (
        sensory_waveform(evidence, sensory_context),
        memory_waveform(evidence, contract_snapshot),
        emotional_waveform(evidence, contract_snapshot),
        prediction_waveform(prediction_signal),
        symbolic_waveform(assembly_result, sensory_context),
        continuity_waveform(evidence, contract_snapshot),
        constraint_waveform(evidence, projection),
        pressure_waveform(adjusted_axes, pressure_snapshot),
    )

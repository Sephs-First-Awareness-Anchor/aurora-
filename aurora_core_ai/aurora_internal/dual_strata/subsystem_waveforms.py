# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Subsystem waveforms — eight pure functions, each compressing one subsystem's
evidence slice into exactly ONE Crest.  No subsystem returns a dict, packet,
list of hypotheses, rationale string, or numeric map.

Only the orchestrator `emit_subsystem_crests` is the entry point for the
dce_bridge. Anything new must be added here, never inlined into the bridge.

CrestRegistry (WarpCapable):
    The eight core waveforms are registered with their 15D axis+recursion profiles.
    When the current I-state+recursion vector falls outside their coverage,
    WARP derives a new crest and appends it to future emit_subsystem_crests()
    calls. Warp crests compute their intensity directly from axis alignment rather
    than evidence-field parsing — they parametrise what they are, not how to read
    specific evidence keys.
"""
from __future__ import annotations

import math
import sys
import os as _os

from typing import Any, Callable, Dict, List, Optional, Tuple

from .crest import Crest
from .subsurface_state import AXES, clip01

# Lazy import of WarpCapable to avoid import-time circular deps
def _get_warp_capable():
    try:
        _core = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..")
        if _core not in sys.path:
            sys.path.insert(0, _core)
        from aurora_warp_protocol import (
            WarpCapable, WarpComponent, CoverageGap,
            AxisCoverageChecker, axes_to_istates,
            _ALL_ISTATES, _RECURSION_DIMS, _ALL_DIMS,
        )
        return WarpCapable, WarpComponent, CoverageGap, AxisCoverageChecker, axes_to_istates, _ALL_DIMS
    except Exception:
        return None, None, None, None, None, None


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
# CrestRegistry — WarpCapable registry for structural extensibility
# ---------------------------------------------------------------------------

# 15D I-state + recursion profiles for each core waveform.
# These describe WHICH region of the coverage space each waveform operates in.
# When the current axis state lands outside all 8 profiles' coverage, WARP
# derives a new crest that fills the gap.
_CORE_CREST_PROFILES: Dict[str, Dict[str, float]] = {
    "sensory": {
        # Boundary-finding and energy expression — immediate perception
        "I_IS": 0.40, "I_ISNT": 0.35, "I_CAN": 0.20, "I_CANNOT": 0.15,
        "I_DO": 0.65, "I_DONOT": 0.20, "I_SAW": 0.80, "I_SOUGHT": 0.40,
        "I_DID": 0.20, "I_DIDNT": 0.10,
        "REC_SURFACE": 0.75, "REC_SHALLOW": 0.20, "REC_MODERATE": 0.05,
        "REC_DEEP": 0.0, "REC_CORE": 0.0,
    },
    "memory": {
        # Existence + continuity — what can be recalled
        "I_IS": 0.80, "I_ISNT": 0.15, "I_CAN": 0.70, "I_CANNOT": 0.10,
        "I_DO": 0.20, "I_DONOT": 0.05, "I_SAW": 0.20, "I_SOUGHT": 0.05,
        "I_DID": 0.15, "I_DIDNT": 0.05,
        "REC_SURFACE": 0.25, "REC_SHALLOW": 0.45, "REC_MODERATE": 0.15,
        "REC_DEEP": 0.05, "REC_CORE": 0.20,
    },
    "emotional": {
        # Agency and energy — full polarity, embedded deep
        "I_IS": 0.10, "I_ISNT": 0.10, "I_CAN": 0.15, "I_CANNOT": 0.15,
        "I_DO": 0.70, "I_DONOT": 0.70, "I_SAW": 0.25, "I_SOUGHT": 0.25,
        "I_DID": 0.80, "I_DIDNT": 0.80,
        "REC_SURFACE": 0.05, "REC_SHALLOW": 0.10, "REC_MODERATE": 0.20,
        "REC_DEEP": 0.40, "REC_CORE": 0.30,
    },
    "prediction": {
        # Existence mismatch — what was expected vs what is
        "I_IS": 0.55, "I_ISNT": 0.55, "I_CAN": 0.40, "I_CANNOT": 0.35,
        "I_DO": 0.25, "I_DONOT": 0.20, "I_SAW": 0.30, "I_SOUGHT": 0.30,
        "I_DID": 0.50, "I_DIDNT": 0.50,
        "REC_SURFACE": 0.10, "REC_SHALLOW": 0.30, "REC_MODERATE": 0.40,
        "REC_DEEP": 0.15, "REC_CORE": 0.05,
    },
    "symbolic": {
        # Energy novelty and boundary coherence
        "I_IS": 0.35, "I_ISNT": 0.20, "I_CAN": 0.20, "I_CANNOT": 0.15,
        "I_DO": 0.65, "I_DONOT": 0.20, "I_SAW": 0.60, "I_SOUGHT": 0.25,
        "I_DID": 0.25, "I_DIDNT": 0.15,
        "REC_SURFACE": 0.10, "REC_SHALLOW": 0.20, "REC_MODERATE": 0.45,
        "REC_DEEP": 0.20, "REC_CORE": 0.05,
    },
    "continuity": {
        # Temporal threading — what holds across time
        "I_IS": 0.30, "I_ISNT": 0.20, "I_CAN": 0.75, "I_CANNOT": 0.60,
        "I_DO": 0.15, "I_DONOT": 0.10, "I_SAW": 0.25, "I_SOUGHT": 0.15,
        "I_DID": 0.40, "I_DIDNT": 0.35,
        "REC_SURFACE": 0.10, "REC_SHALLOW": 0.40, "REC_MODERATE": 0.30,
        "REC_DEEP": 0.15, "REC_CORE": 0.10,
    },
    "constraint": {
        # Energy/capacity — what the system can sustain
        "I_IS": 0.20, "I_ISNT": 0.15, "I_CAN": 0.30, "I_CANNOT": 0.50,
        "I_DO": 0.75, "I_DONOT": 0.65, "I_SAW": 0.20, "I_SOUGHT": 0.15,
        "I_DID": 0.25, "I_DIDNT": 0.30,
        "REC_SURFACE": 0.15, "REC_SHALLOW": 0.25, "REC_MODERATE": 0.40,
        "REC_DEEP": 0.15, "REC_CORE": 0.05,
    },
    "pressure": {
        # Peak-axis urgency — surface-level reflex, immediate
        "I_IS": 0.50, "I_ISNT": 0.50, "I_CAN": 0.40, "I_CANNOT": 0.40,
        "I_DO": 0.50, "I_DONOT": 0.50, "I_SAW": 0.40, "I_SOUGHT": 0.40,
        "I_DID": 0.40, "I_DIDNT": 0.40,
        "REC_SURFACE": 0.65, "REC_SHALLOW": 0.25, "REC_MODERATE": 0.10,
        "REC_DEEP": 0.0, "REC_CORE": 0.0,
    },
}


class CrestRegistry:
    """
    Manages the extensible crest space. The eight core waveforms are fixed;
    WARP-derived crests join them when the coverage space has a genuine gap.

    A warp crest computes its intensity directly from cosine alignment with the
    current axis+recursion state — it doesn't parse specific evidence keys.
    This is correct: warp crests represent structural phenomenal regions that
    the core 8 don't cover, not specific subsystem readings.

    Usage: CrestRegistry is a module-level singleton. emit_subsystem_crests()
    calls registry.check_coverage() after building the 8 core crests, and
    appends any activated warp crests to the returned tuple.
    """

    def __init__(self) -> None:
        self._warp_profiles: Dict[str, Dict[str, float]] = {}    # id → profile
        self._warp_crests:   Dict[str, Dict[str, Any]] = {}      # id → params
        self._warp_trials:   Dict[str, Any] = {}                 # id → WarpComponent
        self._warp_promoted: Dict[str, Any] = {}                 # id → WarpComponent
        self._gap_counter:   Dict[str, int] = {}
        self._activation_counts: Dict[str, int] = {}
        self._warp_ready = False
        self._try_init_warp()

    def _try_init_warp(self) -> None:
        """Late-bind WarpCapable infrastructure to avoid import-time circular deps."""
        (WarpCapable, WarpComponent, CoverageGap,
         AxisCoverageChecker, axes_to_istates, _ALL_DIMS) = _get_warp_capable()
        if WarpCapable is None:
            return
        self._WarpCapable = WarpCapable
        self._WarpComponent = WarpComponent
        self._CoverageGap = CoverageGap
        self._Checker = AxisCoverageChecker
        self._axes_to_istates = axes_to_istates
        self._ALL_DIMS = _ALL_DIMS
        try:
            from aurora_warp_protocol import WarpGenerator, GAP_PERSISTENCE_REQUIRED, COVERAGE_THRESHOLD
            self._generator = WarpGenerator()
            self._GAP_PERSIST = GAP_PERSISTENCE_REQUIRED
            self._COV_THRESH = COVERAGE_THRESHOLD
        except Exception:
            self._generator = None
            self._GAP_PERSIST = 3
            self._COV_THRESH = 0.82
        self._warp_ready = True

    def check_coverage(
        self,
        adjusted_axes: Dict[str, float],
        recursion_weights: Optional[Dict[str, float]] = None,
    ) -> List[Crest]:
        """
        Check whether the current axis+recursion state is covered by the 8
        core waveforms + any promoted warp crests. If a persistent gap exists,
        derive a new warp crest.

        Returns a list of activated warp crests (intensity > 0.30) to append
        to the core tuple. Returns [] if WARP infrastructure isn't available
        or no gap exists.
        """
        if not self._warp_ready or self._generator is None:
            return []

        # Build 15D query vector from axes + recursion
        axis_profile = {ax: clip01(float(adjusted_axes.get(ax, 0.3))) for ax in AXES}
        istate_vec = self._axes_to_istates(axis_profile, ivm_polarity=None)
        if recursion_weights:
            for k, v in recursion_weights.items():
                istate_vec[k] = float(v)

        # Build component map (core 8 + promoted warps)
        all_profiles = dict(_CORE_CREST_PROFILES)
        for cid, comp in self._warp_promoted.items():
            all_profiles[cid] = getattr(comp, "axis_profile", {})

        checker = self._Checker(all_profiles)
        gap = checker.check(istate_vec, source="crest_coverage", tick=0)

        if gap is None:
            self._gap_counter.clear()
            return self._activated_warp_crests(istate_vec)

        sig = ":".join(
            k for k in (self._ALL_DIMS or [])
            if gap.axis_profile.get(k, 0.0) > 0.40
        )
        self._gap_counter[sig] = self._gap_counter.get(sig, 0) + 1

        if self._gap_counter[sig] >= self._GAP_PERSIST:
            self._gap_counter[sig] = 0
            new_comp = self._generator.generate(
                gap=gap,
                level="crest",
                level_params_fn=lambda g, pids: {
                    "gap_coverage": round(g.best_coverage, 4),
                    "dominant_axis": self._dominant_axis_from_profile(g.axis_profile),
                },
            )
            if new_comp is not None:
                cid = new_comp.component_id
                if cid not in self._warp_trials and cid not in self._warp_promoted:
                    self._warp_trials[cid] = new_comp
                    self._warp_profiles[cid] = new_comp.axis_profile

        # Score and promote/dissolve trials
        self._evaluate_trials(istate_vec)

        return self._activated_warp_crests(istate_vec)

    def _activated_warp_crests(self, istate_vec: Dict[str, float]) -> List[Crest]:
        """Return Crest objects for each promoted warp component that is meaningfully activated."""
        result = []
        for cid, comp in self._warp_promoted.items():
            profile = getattr(comp, "axis_profile", {})
            if not profile:
                continue
            activation = self._cosine_activation(istate_vec, profile)
            if activation > 0.30:
                dom_axis = self._dominant_axis_from_profile(profile)
                self._activation_counts[cid] = self._activation_counts.get(cid, 0) + 1
                result.append(Crest(
                    label=str(getattr(comp, "name", cid) or cid),
                    intensity=round(activation, 4),
                    axis=dom_axis,
                ))
        return result

    def _evaluate_trials(self, istate_vec: Dict[str, float]) -> None:
        """Score trial crests and promote or dissolve after sufficient ticks."""
        from aurora_warp_protocol import TRIAL_TICKS, PROMOTION_SCORE
        for cid in list(self._warp_trials):
            comp = self._warp_trials[cid]
            profile = getattr(comp, "axis_profile", {})
            score = self._cosine_activation(istate_vec, profile)
            ema = 0.7 * comp.trial_score_ema + 0.3 * abs(score - 0.5) * 2.0
            comp.trial_score_ema = ema
            comp.trial_tick += 1
            if comp.trial_tick >= TRIAL_TICKS:
                if ema >= PROMOTION_SCORE:
                    comp.promoted = True
                    self._warp_promoted[cid] = comp
                else:
                    comp.dissolved = True
                del self._warp_trials[cid]

    @staticmethod
    def _cosine_activation(a: Dict[str, float], b: Dict[str, float]) -> float:
        _DIMS = tuple(a.keys() | b.keys())
        dot   = sum(a.get(d, 0.0) * b.get(d, 0.0) for d in _DIMS)
        ma    = math.sqrt(sum(a.get(d, 0.0) ** 2 for d in _DIMS))
        mb    = math.sqrt(sum(b.get(d, 0.0) ** 2 for d in _DIMS))
        if ma < 1e-9 or mb < 1e-9:
            return 0.0
        return dot / (ma * mb)

    @staticmethod
    def _dominant_axis_from_profile(profile: Dict[str, float]) -> str:
        _AXIS_TO_ISTATE = {
            "X": ["I_IS", "I_ISNT"],
            "T": ["I_CAN", "I_CANNOT"],
            "N": ["I_DO", "I_DONOT"],
            "B": ["I_SAW", "I_SOUGHT"],
            "A": ["I_DID", "I_DIDNT"],
        }
        best_ax, best_v = "X", 0.0
        for ax, istates in _AXIS_TO_ISTATE.items():
            v = max(profile.get(ist, 0.0) for ist in istates)
            if v > best_v:
                best_v, best_ax = v, ax
        return best_ax

    def warp_status(self) -> Dict[str, Any]:
        return {
            "trials":   len(self._warp_trials),
            "promoted": len(self._warp_promoted),
            "promoted_crests": [
                {"id": cid, "name": getattr(c, "name", cid),
                 "activations": self._activation_counts.get(cid, 0)}
                for cid, c in self._warp_promoted.items()
            ],
        }


# Module-level singleton — persists across emit_subsystem_crests() calls
_CREST_REGISTRY = CrestRegistry()


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
    recursion_weights: Optional[Dict[str, float]] = None,
) -> Tuple[Crest, ...]:
    """
    Run all eight subsystem waveforms and return their crests in canonical order,
    followed by any activated WARP-derived crests.

    recursion_weights: optional {REC_SURFACE, REC_SHALLOW, ...} dict from IVM
    lattice depth distribution. When provided, coverage checking includes the
    full 15D space. When absent, only 10D I-state coverage is checked.

    This is the ONLY entry point dce_bridge may use.
    """
    core_crests = (
        sensory_waveform(evidence, sensory_context),
        memory_waveform(evidence, contract_snapshot),
        emotional_waveform(evidence, contract_snapshot),
        prediction_waveform(prediction_signal),
        symbolic_waveform(assembly_result, sensory_context),
        continuity_waveform(evidence, contract_snapshot),
        constraint_waveform(evidence, projection),
        pressure_waveform(adjusted_axes, pressure_snapshot),
    )
    warp_crests = _CREST_REGISTRY.check_coverage(adjusted_axes, recursion_weights)
    return core_crests + tuple(warp_crests)

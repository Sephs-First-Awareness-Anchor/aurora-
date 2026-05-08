from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .conscious_frame import ConsciousFrame
from .micro_reasoning import generate_micro_reasoning
from .prediction_field import build_prediction_signal
from .subsurface_state import AXES, SubsurfaceState, clip01, normalize_axis_map


def _stringify_fragment(value: Any) -> str:
    text = str(value or "").strip()
    if len(text) > 140:
        return text[:137].rstrip() + "..."
    return text


def _dedupe_strings(values: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out


def _poedex_context_usable(value: Any) -> bool:
    text = str(value or "").strip().lower()
    if not text:
        return False
    failure_markers = (
        "http error 429",
        "too many requests",
        "query timeout",
        "lookup failed",
        "researcher lookup failed",
        "timed out",
    )
    return not any(marker in text for marker in failure_markers)


def _extract_pressure_snapshot(snapshot: Dict[str, Any]) -> Dict[str, float]:
    if not isinstance(snapshot, dict):
        return {axis: 0.0 for axis in AXES}

    result = {axis: 0.0 for axis in AXES}
    direct = dict(snapshot.get("axis_pressure") or snapshot.get("axes") or {})
    for axis in AXES:
        result[axis] = max(result[axis], clip01(direct.get(axis, 0.0)))

    for key in ("dominant_axis", "peak_axis"):
        axis = str(snapshot.get(key, "") or "").upper()
        if axis in result:
            result[axis] = max(result[axis], 0.65)

    return result


@dataclass
class DualStrataSnapshot:
    subsurface_state: Dict[str, Any]
    conscious_frame: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DualStrataBridge:
    """Builds explicit strata objects around the copied DCE assembly."""

    def __init__(self, state_dir: Optional[str] = None):
        base = Path(state_dir) if state_dir else (Path(__file__).resolve().parents[2] / "aurora_state")
        self.state_dir = Path(base)

    def build_snapshot(
        self,
        assembly_result: Any,
        *,
        payload: Any,
        payload_type: str,
        evidence: Optional[Dict[str, Any]] = None,
        contract_snapshot: Optional[Dict[str, Any]] = None,
        requested_frame: str = "balanced",
        thought_intent: Optional[Dict[str, Any]] = None,
    ) -> DualStrataSnapshot:
        evidence = dict(evidence or {})
        contract_snapshot = dict(contract_snapshot or {})
        prediction = build_prediction_signal(
            payload=payload,
            evidence=evidence,
            contract_snapshot=contract_snapshot,
            sensory_context=getattr(assembly_result, "sensory_context", None),
            entropy_state=getattr(assembly_result, "entropy_state", None),
        ).to_dict()
        subsurface = self._build_subsurface_state(
            assembly_result,
            payload=payload,
            payload_type=payload_type,
            evidence=evidence,
            contract_snapshot=contract_snapshot,
            requested_frame=requested_frame,
            thought_intent=thought_intent,
            prediction=prediction,
        )
        conscious = self._build_conscious_frame(
            assembly_result,
            subsurface=subsurface,
            evidence=evidence,
            contract_snapshot=contract_snapshot,
            requested_frame=requested_frame,
            payload=payload,
        )
        snapshot = DualStrataSnapshot(
            subsurface_state=subsurface.to_dict(),
            conscious_frame=conscious.to_dict(),
        )
        self.persist(snapshot)
        return snapshot

    def _build_subsurface_state(
        self,
        assembly_result: Any,
        *,
        payload: Any,
        payload_type: str,
        evidence: Dict[str, Any],
        contract_snapshot: Dict[str, Any],
        requested_frame: str,
        thought_intent: Optional[Dict[str, Any]],
        prediction: Dict[str, Any],
    ) -> SubsurfaceState:
        adjusted_axes = normalize_axis_map(getattr(assembly_result, "adjusted_axes", {}) or {})
        pressure_snapshot = _extract_pressure_snapshot(dict(evidence.get("pressure_snapshot") or {}))
        projection = dict(evidence.get("subsurface_projection") or {})
        pressure_map = normalize_axis_map(
            {
                axis: adjusted_axes.get(axis, 0.0) * 0.7 + pressure_snapshot.get(axis, 0.0) * 0.3
                for axis in AXES
            }
        )

        contract_p = dict(contract_snapshot.get("P", {}) or {})
        contract_m = dict(contract_snapshot.get("M", {}) or {})
        contract_b = dict(contract_snapshot.get("B", {}) or {})
        contract_n = dict(contract_snapshot.get("N", {}) or {})
        established_turn = dict(evidence.get("established_turn_state") or {})
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
        tracked_surface_emotion = str(
            surface_reactive.get("dominant", "")
            or contract_p.get("dominant_emotion", "")
            or evidence.get("tone", "")
            or "neutral"
        ).lower()
        tracked_surface_intensity = clip01(
            surface_reactive.get("intensity", established_turn.get("surface_reactive_intensity", 0.0))
        )
        tracked_surface_bias = str(
            surface_reactive.get("behavior_bias", "")
            or established_turn.get("surface_reactive_bias", "")
            or ""
        ).strip()
        deep_emotion = str(
            deep_emotional.get("dominant", "")
            or contract_p.get("deep_dominant_emotion", "")
            or established_turn.get("deep_dominant_emotion", "")
            or tracked_surface_emotion
            or "neutral"
        ).lower()
        deep_passion = str(
            deep_emotional.get("passion", "")
            or contract_p.get("deep_passion_state", "")
            or established_turn.get("deep_passion_state", "")
            or ""
        ).strip()
        poedex_prefetch = dict(evidence.get("poedex_prefetch") or {})
        poedex_prefetch_result = _stringify_fragment(poedex_prefetch.get("result"))
        poedex_prefetch_concept = _stringify_fragment(poedex_prefetch.get("concept"))
        poedex_learning = dict(evidence.get("poedex_learning") or {})
        poedex_learning_result = _stringify_fragment(poedex_learning.get("result"))
        poedex_learning_concept = _stringify_fragment(poedex_learning.get("concept"))
        poedex_learning_note = _stringify_fragment(poedex_learning.get("note"))
        poedex_representation = dict(evidence.get("poedex_representation") or {})
        poedex_representation_result = _stringify_fragment(poedex_representation.get("result"))
        poedex_representation_concept = _stringify_fragment(poedex_representation.get("concept"))
        poedex_representation_variants = list(poedex_representation.get("variants") or [])[:6]
        projection_axis = str(projection.get("dominant_axis_hint", "") or "").upper()
        dominant_axis = str(
            contract_p.get("dominant_axis")
            or projection_axis
            or getattr(assembly_result, "dominant_axis", "")
            or max(pressure_map, key=pressure_map.get)
        ).upper()
        if dominant_axis not in AXES:
            dominant_axis = max(pressure_map, key=pressure_map.get) if pressure_map else "X"

        salience_seed = dict(pressure_map)
        salience_seed[dominant_axis] = salience_seed.get(dominant_axis, 0.0) + 0.12
        salience_seed["B"] = salience_seed.get("B", 0.0) + clip01(contract_b.get("ambiguity", 0.0)) * 0.25
        salience_seed["N"] = salience_seed.get("N", 0.0) + clip01(contract_n.get("total", 0.0)) * 0.2
        salience_seed["T"] = salience_seed.get("T", 0.0) + clip01(contract_m.get("frame_continuity", 0.0)) * 0.2
        if projection_axis in AXES:
            salience_seed[projection_axis] = salience_seed.get(projection_axis, 0.0) + 0.1
        salience_weights = normalize_axis_map(salience_seed)

        sensory_context = dict(getattr(assembly_result, "sensory_context", {}) or {})
        sensory_summary = {
            "maturity": round(clip01(sensory_context.get("maturity", 0.0)), 4),
            "total_frames": int(sensory_context.get("total_frames", 0) or 0),
            "dominant_facet": str(sensory_context.get("dominant_facet", "") or ""),
            "summary": _stringify_fragment(
                sensory_context.get("summary")
                or sensory_context.get("dominant_facet")
                or ""
            ),
        }
        native_meaning_bundle = dict(
            evidence.get("native_meaning_bundle")
            or sensory_context.get("native_meaning_bundle")
            or {}
        )
        native_meaning = dict(
            evidence.get("native_meaning")
            or sensory_context.get("native_meaning")
            or native_meaning_bundle.get("primary")
            or {}
        )

        recalled_fragments: List[str] = []
        for value in (
            contract_m.get("active_topic"),
            dict(contract_m.get("focus_claim", {}) or {}).get("summary"),
            payload,
        ):
            fragment = _stringify_fragment(value)
            if fragment and fragment not in recalled_fragments:
                recalled_fragments.append(fragment)

        # Read coherence from assembly. Use a warm floor (0.45) instead of 0.0 so that
        # a stale or missing value doesn't lock the system permanently into hold_for_coherence.
        _raw_coherence = getattr(assembly_result, "coherence", None)
        if _raw_coherence is None:
            # Also check entropy_state dict in case coherence lives there
            _es = getattr(assembly_result, "entropy_state", {}) or {}
            _raw_coherence = float(_es.get("coherence", 0.45))
        _assembly_coherence = clip01(float(_raw_coherence or 0.45))

        instability_markers: List[Dict[str, Any]] = []
        if _assembly_coherence < 0.45:
            instability_markers.append({"label": "low_coherence", "severity": round(1.0 - _assembly_coherence, 4)})
        if getattr(assembly_result, "paradoxes", None):
            instability_markers.append({"label": "paradox_active", "severity": 0.8, "detail": list(getattr(assembly_result, "paradoxes", []) or [])[:3]})
        if clip01(prediction.get("mismatch", 0.0)) >= 0.45:
            instability_markers.append({"label": "prediction_mismatch", "severity": round(clip01(prediction.get("mismatch", 0.0)), 4)})
        if clip01(contract_b.get("ambiguity", 0.0)) >= 0.55:
            instability_markers.append({"label": "boundary_blur", "severity": round(clip01(contract_b.get("ambiguity", 0.0)), 4)})
        if list(projection.get("active_effects") or []):
            instability_markers.append(
                {
                    "label": "subsurface_effects",
                    "severity": round(max(0.25, clip01(projection.get("prediction_bias", {}).get("mismatch_hint", 0.0))), 4),
                    "detail": list(projection.get("active_effects") or [])[:3],
                }
            )

        candidate_interpretations: List[Dict[str, Any]] = []
        active_topic = _stringify_fragment(contract_m.get("active_topic"))
        tone = tracked_surface_emotion
        if active_topic:
            candidate_interpretations.append(
                {
                    "label": "topic_continuation",
                    "confidence": round(max(0.35, clip01(contract_m.get("frame_continuity", 0.0))), 4),
                    "summary": f"Current meaning likely still turns around {active_topic}.",
                }
            )
        if tone not in {"", "neutral", "calm"}:
            candidate_interpretations.append(
                {
                    "label": "affective_attention",
                    "confidence": round(max(0.35, clip01(salience_weights.get("A", 0.0))), 4),
                    "summary": f"The next conscious frame should account for {tone} affective pressure.",
                }
            )
        if deep_emotion not in {"", "neutral", "calm"} or deep_passion:
            deep_summary = f"The live input may be carrying {deep_emotion} below the surface."
            if deep_passion:
                deep_summary = deep_summary.rstrip(".") + f" Underneath it reads as {deep_passion}."
            candidate_interpretations.append(
                {
                    "label": "deep_affective_read",
                    "confidence": round(
                        max(
                            0.38,
                            clip01(deep_emotional.get("intensity", 0.0)),
                            clip01(salience_weights.get("A", 0.0)),
                        ),
                        4,
                    ),
                    "summary": deep_summary,
                }
            )
        if projection.get("surface_guidance"):
            candidate_interpretations.append(
                {
                    "label": "subsurface_guidance",
                    "confidence": round(max(0.35, clip01(projection.get("readiness_bias", 0.0))), 4),
                    "summary": _stringify_fragment(projection.get("surface_guidance")),
                }
            )
        if _poedex_context_usable(poedex_prefetch_result):
            candidate_interpretations.append(
                {
                    "label": "prefetched_lookup_context",
                    "confidence": 0.52,
                    "summary": (
                        f"Poedex staged context for {poedex_prefetch_concept}: {poedex_prefetch_result}"
                        if poedex_prefetch_concept else
                        f"Poedex staged context: {poedex_prefetch_result}"
                    ),
                }
            )
        if _poedex_context_usable(poedex_learning_result) or _poedex_context_usable(poedex_learning_note):
            candidate_interpretations.append(
                {
                    "label": "poedex_learning_context",
                    "confidence": 0.56,
                    "summary": (
                        f"Poedex learning for {poedex_learning_concept}: {poedex_learning_note or poedex_learning_result}"
                        if poedex_learning_concept else
                        f"Poedex learning: {poedex_learning_note or poedex_learning_result}"
                    ),
                }
            )
        _usable_representation_variants = [
            item for item in list(poedex_representation_variants or [])
            if _poedex_context_usable(item)
        ]
        if _poedex_context_usable(poedex_representation_result) or _usable_representation_variants:
            candidate_interpretations.append(
                {
                    "label": "poedex_representation_context",
                    "confidence": 0.57,
                    "summary": (
                        f"Poedex representation for {poedex_representation_concept}: {_usable_representation_variants[0]}"
                        if poedex_representation_concept and _usable_representation_variants else
                        f"Poedex representation: {poedex_representation_result}"
                    ),
                }
            )
        candidate_interpretations.append(
            {
                "label": "axis_bias",
                "confidence": round(max(0.3, clip01(salience_weights.get(dominant_axis, 0.0))), 4),
                "summary": f"{dominant_axis}-axis pressure is shaping the next conscious frame.",
            }
        )

        action_bias_candidates: List[Dict[str, Any]] = []
        if clip01(contract_b.get("ambiguity", 0.0)) >= 0.55:
            action_bias_candidates.append({"action": "clarify", "weight": round(clip01(contract_b.get("ambiguity", 0.0)), 4)})
        if deep_emotion in {"sad", "hurt", "fear", "afraid", "anxious", "upset"}:
            action_bias_candidates.append({"action": "comfort", "weight": round(max(0.45, clip01(salience_weights.get("A", 0.0))), 4)})
        if tracked_surface_bias in {"slow_down", "lean_in", "probe", "steady"}:
            action_bias_candidates.append(
                {
                    "action": tracked_surface_bias,
                    "weight": round(max(0.25, tracked_surface_intensity or clip01(salience_weights.get("N", 0.0))), 4),
                }
            )
        if dominant_axis == "X" and _assembly_coherence >= 0.5:
            action_bias_candidates.append({"action": "explain", "weight": round(clip01(salience_weights.get("X", 0.0)), 4)})
        if dominant_axis == "T":
            action_bias_candidates.append({"action": "contextualize", "weight": round(clip01(salience_weights.get("T", 0.0)), 4)})
        if dominant_axis == "N":
            action_bias_candidates.append({"action": "slow_down", "weight": round(clip01(salience_weights.get("N", 0.0)), 4)})
        for signal in list(projection.get("intuition_signals") or [])[:3]:
            action = str(signal.get("label", "") or "").strip().replace("hold_structural_change_below_surface", "hold")
            if action:
                action_bias_candidates.append(
                    {
                        "action": action,
                        "weight": round(max(0.25, clip01(signal.get("weight", 0.0))), 4),
                    }
                )

        instability_weight = sum(float(item.get("severity", 0.0) or 0.0) for item in instability_markers[:3]) / max(1, min(3, len(instability_markers)))
        readiness = clip01(
            _assembly_coherence * 0.5
            + (1.0 - clip01(prediction.get("mismatch", 0.0))) * 0.3
            + (1.0 - instability_weight) * 0.1
            + clip01(projection.get("readiness_bias", 0.0)) * 0.1
        )

        contract_signals = {
            "active_topic": active_topic,
            "dominant_emotion": tracked_surface_emotion,
            "tracked_surface_emotion": tracked_surface_emotion,
            "tracked_surface_intensity": round(tracked_surface_intensity, 4),
            "tracked_surface_bias": tracked_surface_bias,
            "interpreted_deep_emotion": deep_emotion,
            "interpreted_deep_passion": deep_passion,
            "emotion_bridge": emotion_bridge,
            "ambiguity": round(clip01(contract_b.get("ambiguity", 0.0)), 4),
            "cost_total": round(clip01(contract_n.get("total", 0.0)), 4),
            "frame_continuity": round(clip01(contract_m.get("frame_continuity", 0.0)), 4),
        }

        established_sources = list(evidence.get("established_stack_sources") or []) or [
            "WorkingMemory",
            "UnderstandingContract",
            "DimensionalSystems.process_synthesis",
            "DCEAssembly",
            "SensoryCrystal",
        ]
        if "SensoryCrystal" not in established_sources:
            established_sources.append("SensoryCrystal")
        metadata = {
            "payload_type": str(payload_type or ""),
            "requested_frame": str(requested_frame or "balanced"),
            "thought_intent_present": bool(thought_intent),
            "prediction_source": str(prediction.get("source", "") or ""),
            "projection_source": str(projection.get("source", "") or ""),
            "established_stack_sources": established_sources,
            "activation_field": dict(evidence.get("activation_field") or {}),
        }

        return SubsurfaceState(
            dominant_axis=dominant_axis,
            frame_request=str(requested_frame or "balanced"),
            coherence=_assembly_coherence,
            salience_weights=salience_weights,
            pressure_map=pressure_map,
            readiness=readiness,
            sensory_summary=sensory_summary,
            native_meaning=native_meaning,
            native_meaning_bundle=native_meaning_bundle,
            recalled_fragments=recalled_fragments,
            candidate_interpretations=candidate_interpretations,
            instability_markers=instability_markers,
            action_bias_candidates=action_bias_candidates,
            contract_signals=contract_signals,
            prediction=prediction,
            metadata=metadata,
        )

    def _build_conscious_frame(
        self,
        assembly_result: Any,
        *,
        subsurface: SubsurfaceState,
        evidence: Dict[str, Any],
        contract_snapshot: Dict[str, Any],
        requested_frame: str,
        payload: Any,
    ) -> ConsciousFrame:
        projection = dict(evidence.get("subsurface_projection") or {})
        surface_input = dict(evidence.get("surface_input") or {})
        hypotheses = [
            hypothesis.to_dict()
            for hypothesis in generate_micro_reasoning(
                subsurface,
                assembly_result=assembly_result,
                evidence=evidence,
                contract_snapshot=contract_snapshot,
            )
        ]
        prediction = dict(subsurface.prediction or {})

        unresolved_conflicts = [
            str(item.get("label", "") or "")
            for item in list(subsurface.instability_markers or [])
            if str(item.get("label", "") or "")
        ]

        _assembly_coherence = float(subsurface.coherence or 0.0)

        stance = "attend"
        action = "hold"
        if any(item.get("label") == "clarification_pressure" for item in hypotheses):
            stance = "careful_clarification"
            action = "clarify"
        elif any(item.get("label") == "comfort_bias" for item in hypotheses):
            stance = "supportive_attention"
            action = "comfort"
        elif any(item.get("label") == "prediction_mismatch" for item in hypotheses):
            stance = "reframe"
            action = "re-evaluate"
        elif subsurface.dominant_axis == "X" and subsurface.readiness >= 0.5:
            stance = "interpretive_explanation"
            action = "explain"
        elif subsurface.dominant_axis == "T":
            stance = "contextual_continuity"
            action = "contextualize"
        elif subsurface.dominant_axis == "N":
            stance = "cautious_load_management"
            action = "slow_down"

        should_speak = subsurface.readiness >= 0.42 and "paradox_active" not in unresolved_conflicts
        if _assembly_coherence < 0.28:
            should_speak = False
            stance = "hold_for_coherence"
            action = "wait"
        user_turn_present = bool(
            str(surface_input.get("raw_text", "") or "").strip()
            or str(surface_input.get("full_phrase", "") or "").strip()
            or str(surface_input.get("source_text", "") or "").strip()
        )
        if user_turn_present and "paradox_active" not in unresolved_conflicts:
            should_speak = True
            if action == "wait":
                action = "clarify" if subsurface.readiness < 0.5 else "explain"
            if stance == "hold_for_coherence":
                stance = "careful_clarification" if subsurface.readiness < 0.5 else "interpretive_explanation"

        active_topic = str(subsurface.contract_signals.get("active_topic", "") or "").strip()
        tracked_surface_emotion = str(
            subsurface.contract_signals.get("tracked_surface_emotion", "")
            or subsurface.contract_signals.get("dominant_emotion", "")
            or "neutral"
        ).strip()
        tracked_surface_bias = str(subsurface.contract_signals.get("tracked_surface_bias", "") or "").strip()
        deep_tone = str(
            subsurface.contract_signals.get("interpreted_deep_emotion", "")
            or tracked_surface_emotion
            or "neutral"
        ).strip()
        deep_passion = str(subsurface.contract_signals.get("interpreted_deep_passion", "") or "").strip()
        tone = deep_tone
        payload_fragment = _stringify_fragment(payload)
        repair_phase = str(dict(projection.get("subsurface_owned") or {}).get("repair_phase", "") or "")
        repair_reason = str(dict(projection.get("subsurface_owned") or {}).get("repair_reason", "") or "")
        established_turn = dict(evidence.get("established_turn_state") or {})
        working_memory_snapshot = dict(evidence.get("working_memory_snapshot") or {})
        conversation_memory = dict(evidence.get("conversation_memory") or {})
        continuity_recall = list(evidence.get("continuity_recall") or [])
        surface_conversation_frame = dict(evidence.get("surface_conversation_frame") or {})
        continuity_bundle = dict(evidence.get("subsurface_continuity_bundle") or {})
        oets_context = dict(evidence.get("oets_context") or {})
        poedex_prefetch = dict(evidence.get("poedex_prefetch") or {})
        surface_input = dict(evidence.get("surface_input") or {})
        meaning_form = dict(established_turn.get("dominant_meaning_form", {}) or {})
        understanding_observation = dict(established_turn.get("understanding_observation", {}) or {})
        understanding_a = dict(understanding_observation.get("A", {}) or {})
        understanding_m = dict(understanding_observation.get("M", {}) or {})
        poedex_prefetch_result = _stringify_fragment(poedex_prefetch.get("result"))
        poedex_prefetch_concept = _stringify_fragment(poedex_prefetch.get("concept"))
        poedex_learning = dict(evidence.get("poedex_learning") or {})
        poedex_learning_result = _stringify_fragment(poedex_learning.get("result"))
        poedex_learning_note = _stringify_fragment(poedex_learning.get("note"))
        poedex_learning_concept = _stringify_fragment(poedex_learning.get("concept"))
        poedex_representation = dict(evidence.get("poedex_representation") or {})
        poedex_representation_result = _stringify_fragment(poedex_representation.get("result"))
        poedex_representation_variants = list(poedex_representation.get("variants") or [])
        poedex_representation_concept = _stringify_fragment(poedex_representation.get("concept"))
        working_topic = str(
            surface_conversation_frame.get("current_topic")
            or working_memory_snapshot.get("current_topic")
            or established_turn.get("meaning_focus")
            or active_topic
            or ""
        ).strip()
        meaning_label = str(
            meaning_form.get("label")
            or meaning_form.get("form")
            or established_turn.get("meaning_summary")
            or understanding_m.get("meaning_summary")
            or ""
        ).strip()
        fit_reason = str(
            established_turn.get("understanding_fit_reason")
            or understanding_a.get("fit_reason")
            or ""
        ).strip()
        continuity_summary = str(
            dict(continuity_bundle.get("conversation_summary", {}) or {}).get("summary")
            or conversation_memory.get("summary", "")
            or ""
        ).strip()
        oets_concepts = _dedupe_strings(list(oets_context.get("active_concepts") or []))
        learned_hints = _dedupe_strings(list(established_turn.get("learned_hints") or []))
        input_anchor = payload_fragment or _stringify_fragment(
            surface_input.get("full_phrase")
            or surface_input.get("raw_text")
            or payload
        )
        if deep_passion:
            input_affective_seed = f"The live input feels {deep_tone} with an underlying {deep_passion} pull."
        elif deep_tone and deep_tone not in {"neutral", "calm"}:
            input_affective_seed = f"The live input feels {deep_tone}."
        else:
            input_affective_seed = ""
        reactive_intensity = 0.0
        reactive_reason = ""
        if prediction.get("mismatch", 0.0) >= 0.55:
            reactive_intensity = max(reactive_intensity, clip01(prediction.get("mismatch", 0.0)))
            reactive_reason = reactive_reason or "prediction mismatch is high"
        if tracked_surface_emotion.lower() in {"sad", "hurt", "fear", "afraid", "anxious", "upset", "angry", "urgent"}:
            reactive_intensity = max(
                reactive_intensity,
                max(
                    clip01(subsurface.contract_signals.get("tracked_surface_intensity", 0.0)),
                    clip01(subsurface.salience_weights.get("A", 0.0)) * 0.95,
                ),
            )
            reactive_reason = reactive_reason or f"tracked surface affect is {tracked_surface_emotion.lower()}"
        if repair_phase in {"recognition", "observation"}:
            reactive_intensity = max(reactive_intensity, 0.58)
            reactive_reason = reactive_reason or f"subsurface is in {repair_phase}"
        elif repair_phase == "research":
            reactive_intensity = max(reactive_intensity, 0.42)
            reactive_reason = reactive_reason or "subsurface is still researching the issue"

        processing_mode = "deliberative"
        if reactive_intensity >= 0.68 and should_speak:
            processing_mode = "reactive"
        elif reactive_intensity >= 0.38 or bool(unresolved_conflicts):
            processing_mode = "blended"
        if not should_speak:
            processing_mode = "holding"

        interpretation = f"{subsurface.dominant_axis}-axis pressure is most salient."
        if working_topic:
            interpretation = f"{subsurface.dominant_axis}-axis pressure is shaping how Aurora interprets {working_topic}."
        elif active_topic:
            interpretation = f"{subsurface.dominant_axis}-axis pressure is shaping how Aurora interprets {active_topic}."
        if meaning_label:
            interpretation = interpretation.rstrip(".") + f" The active meaning surface is {meaning_label}."
        if tone and tone not in {"neutral", "calm"}:
            interpretation = interpretation.rstrip(".") + f" Deeper input affect reads as {tone}."
        if deep_passion:
            interpretation = interpretation.rstrip(".") + f" Underlying passion reads as {deep_passion}."

        meaning_seed = ""
        if meaning_label and working_topic:
            meaning_seed = f"{working_topic} is being held through {meaning_label}."
        elif meaning_label:
            meaning_seed = f"Active meaning surface: {meaning_label}."
        _usable_prefetch = _poedex_context_usable(poedex_prefetch_result)
        _usable_learning = (
            _poedex_context_usable(poedex_learning_result)
            or _poedex_context_usable(poedex_learning_note)
        )
        _usable_representation_variants = [
            item for item in list(poedex_representation_variants or [])
            if _poedex_context_usable(item)
        ]
        _usable_representation = (
            _poedex_context_usable(poedex_representation_result)
            or bool(_usable_representation_variants)
        )

        root_seed_candidates = [
            input_affective_seed,
            meaning_seed,
            fit_reason,
            f"The live conversational thread is {working_topic}." if working_topic else "",
            continuity_summary,
            (
                f"Poedex context for {poedex_prefetch_concept}: {poedex_prefetch_result}"
                if _usable_prefetch and poedex_prefetch_concept else
                f"Poedex context: {poedex_prefetch_result}"
                if _usable_prefetch else
                ""
            ),
            learned_hints[0] if learned_hints else "",
            projection.get("surface_guidance"),
            hypotheses[0].get("rationale") if hypotheses else "",
            interpretation,
        ]
        root_seed = _stringify_fragment(
            next((item for item in root_seed_candidates if str(item or "").strip()), interpretation)
        )
        root_summary_parts = [root_seed]
        if input_anchor:
            root_summary_parts.append(f"Input anchor: {input_anchor}.")
        if working_topic and working_topic.lower() not in root_seed.lower():
            root_summary_parts.append(f"Current thread: {working_topic}.")
        if meaning_label and meaning_label.lower() not in root_seed.lower():
            root_summary_parts.append(f"Meaning form: {meaning_label}.")
        if continuity_recall and not continuity_summary:
            root_summary_parts.append(
                f"Continuity remains active around {continuity_recall[0].get('anchor', 'the current thread')}."
            )
        if oets_concepts:
            root_summary_parts.append(f"Grounding concepts: {', '.join(oets_concepts[:2])}.")
        if _usable_prefetch:
            if poedex_prefetch_concept:
                root_summary_parts.append(f"Poedex context for {poedex_prefetch_concept}: {poedex_prefetch_result}.")
            else:
                root_summary_parts.append(f"Poedex context: {poedex_prefetch_result}.")
        if _usable_learning:
            if poedex_learning_concept:
                root_summary_parts.append(
                    f"Poedex learning for {poedex_learning_concept}: {poedex_learning_note or poedex_learning_result}."
                )
            else:
                root_summary_parts.append(f"Poedex learning: {poedex_learning_note or poedex_learning_result}.")
        if _usable_representation:
            if poedex_representation_concept:
                root_summary_parts.append(
                    f"Poedex representation for {poedex_representation_concept}: {_usable_representation_variants[0] if _usable_representation_variants else poedex_representation_result}."
                )
            else:
                root_summary_parts.append(f"Poedex representation: {poedex_representation_result}.")
        root_summary = _stringify_fragment(" ".join(root_summary_parts))

        comparison_channels = ["incoming_input", "present_sensory"]
        if surface_conversation_frame or working_memory_snapshot:
            comparison_channels.append("surface_conversation_frame")
        if continuity_bundle or conversation_memory or continuity_recall:
            comparison_channels.append("subsurface_continuity_memory")
        if oets_context:
            comparison_channels.append("OETS_grounding")
        if contract_snapshot or understanding_observation:
            comparison_channels.append("understanding_contract")
        if projection:
            comparison_channels.append("subsurface_stream")
        if _usable_prefetch:
            comparison_channels.append("poedex_prefetch")
        if _usable_learning:
            comparison_channels.append("poedex_learning")
        if _usable_representation:
            comparison_channels.append("poedex_representation")
        comparison_channels.append("DCE_root")

        origin_systems = ["incoming_input"]
        if surface_conversation_frame or working_memory_snapshot:
            origin_systems.append("WorkingMemory")
        if continuity_bundle or conversation_memory or continuity_recall:
            origin_systems.append("ConversationMemory")
        if oets_context:
            origin_systems.append("ExpressionPerception/OETS")
        if contract_snapshot or understanding_observation:
            origin_systems.append("UnderstandingContract")
        if _usable_prefetch:
            origin_systems.append("Poedex")
        if _usable_learning:
            origin_systems.append("PoedexLearning")
        if _usable_representation:
            origin_systems.append("PoedexRepresentation")
        origin_systems.append("DimensionalSystems.process_synthesis")
        origin_systems.append("DCEAssembly")
        root_thought = {
            "law_bindings": getattr(assembly_result, "law_bindings", []),
            "diagonal_anchor": getattr(assembly_result, "diagonal_anchor", ""),
            "input_anchor": input_anchor,
            "mode": processing_mode,
            "primary_tension": (
                repair_reason
                or fit_reason
                or meaning_label
                or (unresolved_conflicts[0] if unresolved_conflicts else subsurface.dominant_axis)
            ),
            "comparison_channels": comparison_channels,
            "origin_systems": origin_systems,
        }
        reactive_signal = {
            "active": (
                clip01(reactive_intensity) >= 0.38
                or processing_mode in {"reactive", "blended"}
                or repair_phase in {"recognition", "observation", "research", "enforce"}
            ),
            "intensity": round(clip01(reactive_intensity), 4),
            "reason": reactive_reason,
            "repair_phase": repair_phase,
            "tracked_surface_emotion": tracked_surface_emotion,
            "tracked_surface_bias": tracked_surface_bias,
            "deep_emotion": deep_tone,
            "deep_passion": deep_passion,
        }

        explicit_notes: List[str] = []
        _pred_payload = dict(prediction.get("prediction_payload") or {})
        if _pred_payload:
            _pt = str(_pred_payload.get("topic", "") or "").strip()
            _pi = str(_pred_payload.get("intent_type", "") or "followup").strip()
            _pa = str(_pred_payload.get("affect", "") or "neutral").strip()
            _pc = str(_pred_payload.get("certainty_band", "") or "medium").strip()
            _pax = str(_pred_payload.get("axis_signature", "") or "").strip()
            _note_parts = [f"intent={_pi}"]
            if _pt:
                _note_parts.append(f"topic={_pt}")
            if _pa and _pa != "neutral":
                _note_parts.append(f"affect={_pa}")
            if _pax:
                _note_parts.append(f"axis={_pax}")
            _note_parts.append(f"certainty={_pc}")
            explicit_notes.append(f"Predicted continuation: {', '.join(_note_parts)}")
        elif prediction.get("expected_observation"):
            explicit_notes.append(f"Predicted continuation: {prediction.get('expected_observation')}")
        if prediction.get("mismatch", 0.0) >= 0.45:
            explicit_notes.append("Observed input diverged from the primed continuation.")
        explicit_notes.append(f"Root thought: {root_summary}")
        if working_topic:
            explicit_notes.append(f"Working-memory thread: {working_topic}")
        if continuity_summary:
            explicit_notes.append(f"Continuity memory: {continuity_summary}")
        if surface_conversation_frame.get("recent_context"):
            _surface_recent_mode = str(
                surface_conversation_frame.get("recent_context_mode")
                or surface_input.get("recent_context_mode")
                or "present"
            ).strip()
            if _surface_recent_mode and _surface_recent_mode not in {"present", "none"}:
                explicit_notes.append(
                    f"Surface conversation frame is carrying recent live context in {_surface_recent_mode} mode."
                )
            else:
                explicit_notes.append("Surface conversation frame is carrying recent live context.")
        if continuity_recall:
            explicit_notes.append(
                f"Continuity recall anchor: {continuity_recall[0].get('anchor', 'current thread')}"
            )
        question_alignment = dict(
            surface_input.get("question_alignment")
            or established_turn.get("question_alignment")
            or {}
        )
        if question_alignment:
            _actual_question = str(question_alignment.get("actual_question", "") or "").strip()
            _answered_question = str(question_alignment.get("answered_question", "") or "").strip()
            if _actual_question:
                explicit_notes.append(f"Surface target question: {_actual_question}")
            if _answered_question:
                explicit_notes.append(f"Surface draft answers: {_answered_question}")
            if not bool(question_alignment.get("aligned", True)):
                explicit_notes.append("Surface/question alignment still needs repair.")
        if oets_concepts:
            explicit_notes.append(f"OETS grounding: {', '.join(oets_concepts[:3])}")
        if tracked_surface_emotion and tracked_surface_emotion not in {"neutral", "calm"}:
            explicit_notes.append(f"Tracked surface affect: {tracked_surface_emotion}")
        if deep_tone and deep_tone not in {"neutral", "calm"}:
            if deep_passion:
                explicit_notes.append(f"Deeper input affect: {deep_tone} via {deep_passion}")
            else:
                explicit_notes.append(f"Deeper input affect: {deep_tone}")
        if _poedex_context_usable(poedex_prefetch_result):
            if poedex_prefetch_concept:
                explicit_notes.append(f"Poedex prefetch: {poedex_prefetch_concept} -> {poedex_prefetch_result}")
            else:
                explicit_notes.append(f"Poedex prefetch: {poedex_prefetch_result}")
        if _poedex_context_usable(poedex_learning_result) or _poedex_context_usable(poedex_learning_note):
            if poedex_learning_concept:
                explicit_notes.append(
                    f"Poedex learning: {poedex_learning_concept} -> {poedex_learning_note or poedex_learning_result}"
                )
            else:
                explicit_notes.append(f"Poedex learning: {poedex_learning_note or poedex_learning_result}")
        _usable_representation_variants = [
            item for item in list(poedex_representation_variants or [])
            if _poedex_context_usable(item)
        ]
        if _poedex_context_usable(poedex_representation_result) or _usable_representation_variants:
            if poedex_representation_concept:
                explicit_notes.append(
                    f"Poedex representation: {poedex_representation_concept} -> {_usable_representation_variants[0] if _usable_representation_variants else poedex_representation_result}"
                )
            else:
                explicit_notes.append(f"Poedex representation: {poedex_representation_result}")
        if subsurface.sensory_summary.get("summary"):
            explicit_notes.append(f"Sensory context: {subsurface.sensory_summary.get('summary')}")
        if projection.get("surface_guidance"):
            explicit_notes.append(f"Subsurface guidance: {projection.get('surface_guidance')}")
        sensory_perspective = dict(projection.get("present_sensory_perspective") or {})
        if sensory_perspective.get("summary"):
            explicit_notes.append(f"Present sensory perspective: {sensory_perspective.get('summary')}")

        return ConsciousFrame(
            frame_name=str(requested_frame or "balanced"),
            stance=stance,
            interpretation=interpretation,
            selected_action=action,
            should_speak=should_speak,
            readiness=subsurface.readiness,
            coherence=_assembly_coherence,
            dominant_axis=subsurface.dominant_axis,
            processing_mode=processing_mode,
            root_thought=root_thought,
            reactive_signal=reactive_signal,
            unresolved_conflicts=unresolved_conflicts,
            salient_hypotheses=hypotheses[:4],
            sensory_summary=dict(subsurface.sensory_summary or {}),
            prediction=prediction,
            contract_signals=dict(subsurface.contract_signals or {}),
            explicit_notes=explicit_notes,
        )

    def persist(self, snapshot: DualStrataSnapshot) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        payload = snapshot.to_dict()
        payload["saved_at"] = time.time()

        snapshot_path = self.state_dir / "dual_strata_snapshot.json"
        snapshot_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True), encoding="utf-8")

        log_entry = {
            "ts": payload["saved_at"],
            "frame_name": payload.get("conscious_frame", {}).get("frame_name", ""),
            "stance": payload.get("conscious_frame", {}).get("stance", ""),
            "selected_action": payload.get("conscious_frame", {}).get("selected_action", ""),
            "should_speak": bool(payload.get("conscious_frame", {}).get("should_speak", False)),
            "processing_mode": payload.get("conscious_frame", {}).get("processing_mode", ""),
            "root_thought": dict(payload.get("conscious_frame", {}).get("root_thought", {}) or {}).get("summary", ""),
            "dominant_axis": payload.get("subsurface_state", {}).get("dominant_axis", ""),
            "readiness": payload.get("subsurface_state", {}).get("readiness", 0.0),
            "mismatch": payload.get("subsurface_state", {}).get("prediction", {}).get("mismatch", 0.0),
        }
        with (self.state_dir / "dual_strata_frame_log.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(log_entry, ensure_ascii=True) + "\n")

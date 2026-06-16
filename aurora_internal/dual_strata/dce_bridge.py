# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
DualStrataBridge — crest convergence orchestrator.
Replaces the old packet-aggregator design with recursive crest propagation.
"""
from __future__ import annotations

import json
import time
from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .crest import Crest, CrestBundle
from .conscious_frame import ConsciousFrame
from .contextual_overlay import ContextualOverlay
from .micro_reasoning import generate_micro_reasoning
from .prediction_field import build_prediction_signal
from .subsurface_state import AXES, SubsurfaceState, clip01, normalize_axis_map
from .subsystem_waveforms import emit_subsystem_crests


def _extract_pressure_snapshot(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(snapshot, dict):
        return {}
    return dict(snapshot)


def _extract_adjusted_axes(assembly_result: Any) -> Dict[str, float]:
    return normalize_axis_map(getattr(assembly_result, "adjusted_axes", {}) or {})


@dataclass
class DualStrataSnapshot:
    subsurface_state: Dict[str, Any]
    conscious_frame: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Crest convergence helpers
# ---------------------------------------------------------------------------

_CONVERGENCE_GROUPS = {
    # label → semantic cluster
    "comfort_bias": "comfort", "warmth": "comfort", "comfort": "comfort",
    "caution": "caution", "hesitation": "caution", "low_certainty": "caution",
    "reframe_needed": "reframe", "reframe": "reframe", "surprise": "reframe",
    "familiar": "continuity", "continuity_pull": "continuity", "continuity_stable": "continuity",
    "thread_holds": "continuity", "resonant_recall": "continuity",
    "unfamiliar": "novelty", "novelty": "novelty", "new_thread": "novelty",
    "strain": "constraint", "limitation": "constraint", "capacity": "constraint",
    "steady_envelope": "steady", "steady_continuation": "steady", "calm": "steady",
    "perceptually_steady": "steady", "neutral_affect": "steady",
    "urgency": "urgency", "tension": "urgency", "discomfort": "urgency",
    "thread_slipping": "urgency", "context_drag": "urgency",
    "resonance": "alignment", "alignment": "alignment",
    "contradiction": "constraint", "hostile_tone": "urgency",
    "warm_tone": "comfort", "alert": "urgency",
    "attentional_drift": "novelty", "sensory_irregularity": "novelty",
    "expectation": "steady", "explain": "alignment",
    "clarify": "caution", "contextualize": "continuity",
    "hold": "steady", "attend": "steady",
}

_CLUSTER_LABELS = {
    "comfort": "comfort",
    "caution": "caution",
    "reframe": "reframe_needed",
    "continuity": "continuity_pull",
    "novelty": "novel",
    "constraint": "strain",
    "steady": "steady",
    "urgency": "urgency",
    "alignment": "resonance",
}

_SURFACE_LABEL_MAP = {
    "comfort": "comfort",
    "caution": "clarify",
    "reframe": "reframe",
    "continuity": "contextualize",
    "novelty": "explain",
    "constraint": "hold",
    "steady": "explain",
    "urgency": "attend",
    "alignment": "explain",
}


def converge_crests(sub_crests: Tuple[Crest, ...], mode: str = "subsurface") -> Crest:
    """Converge N sub-crests into ONE higher-order crest.
    Picks the dominant cluster or builds a mixed generalized label."""
    if not sub_crests:
        return Crest(label="steady", intensity=0.5, axis="X")

    cluster_scores: Dict[str, float] = {}
    cluster_axis: Dict[str, str] = {}
    for crest in sub_crests:
        cluster = _CONVERGENCE_GROUPS.get(crest.label, "steady")
        cluster_scores[cluster] = cluster_scores.get(cluster, 0.0) + crest.intensity
        if cluster not in cluster_axis or crest.intensity > cluster_scores.get(cluster + "_peak", 0.0):
            cluster_axis[cluster] = crest.axis
            cluster_scores[cluster + "_peak"] = crest.intensity

    dominant_cluster = max(
        (c for c in cluster_scores if not c.endswith("_peak")),
        key=lambda c: cluster_scores[c],
    )
    total = sum(v for k, v in cluster_scores.items() if not k.endswith("_peak"))
    dominant_score = cluster_scores[dominant_cluster]
    dominance_ratio = dominant_score / max(total, 1e-9)

    sorted_clusters = sorted(
        [c for c in cluster_scores if not c.endswith("_peak")],
        key=lambda c: cluster_scores[c],
        reverse=True,
    )

    if dominance_ratio >= 0.55 or len(sorted_clusters) == 1:
        label = _CLUSTER_LABELS.get(dominant_cluster, dominant_cluster)
        intensity = clip01(dominant_score / max(len(sub_crests), 1))
        axis = cluster_axis.get(dominant_cluster, "X")
        return Crest(label=label, intensity=round(intensity, 4), axis=axis)

    top_two = sorted_clusters[:2]
    c1, c2 = top_two[0], top_two[1]
    mixed_labels = {
        frozenset({"comfort", "caution"}): "warmth",
        frozenset({"continuity", "novelty"}): "unfamiliar",
        frozenset({"caution", "constraint"}): "caution",
        frozenset({"comfort", "continuity"}): "familiar",
        frozenset({"novelty", "alignment"}): "resonance",
        frozenset({"urgency", "caution"}): "hesitation",
        frozenset({"steady", "continuity"}): "continuity_stable",
        frozenset({"urgency", "constraint"}): "strain",
    }
    label = mixed_labels.get(frozenset({c1, c2}), _CLUSTER_LABELS.get(c1, c1))
    intensity = clip01((cluster_scores[c1] + cluster_scores[c2]) / max(len(sub_crests), 1))
    axis = cluster_axis.get(c1, "X")
    return Crest(label=label, intensity=round(intensity, 4), axis=axis)


def converge_for_surface(
    subsurface_crest: Crest,
    overlay: ContextualOverlay,
    coherence: float,
    user_turn_present: bool,
) -> Crest:
    """Surface compression pass: subconscious meaning + live context → one conscious crest."""
    base_label = subsurface_crest.label
    cluster = _CONVERGENCE_GROUPS.get(base_label, "steady")
    surface_label = _SURFACE_LABEL_MAP.get(cluster, "explain")

    if not user_turn_present:
        if base_label in {"strain", "limitation", "urgency", "thread_slipping"}:
            return Crest(label="hold", intensity=0.65, axis=subsurface_crest.axis)
        return Crest(label="hold", intensity=0.5, axis=subsurface_crest.axis)

    if coherence < 0.28:
        return Crest(label="hold", intensity=0.45, axis=subsurface_crest.axis)

    tone = str(getattr(overlay, "present_tone", "") or "").lower()
    if tone in {"hostile", "angry", "aggressive"}:
        return Crest(label="attend", intensity=min(0.9, subsurface_crest.intensity + 0.1), axis="A")
    if tone in {"sad", "hurt", "anxious", "afraid"}:
        return Crest(label="comfort", intensity=min(0.9, subsurface_crest.intensity + 0.1), axis="A")

    intensity = clip01(subsurface_crest.intensity * 0.7 + coherence * 0.3)
    return Crest(label=surface_label, intensity=round(intensity, 4), axis=subsurface_crest.axis)


def derive_surface_behavior(
    conscious_crest: Crest,
    subsurface_crest: Crest,
    overlay: ContextualOverlay,
    coherence: float,
) -> Tuple[str, str, bool, str]:
    """Pure label → stance/action/should_speak/processing_mode lookup.
    No mechanism inspection."""
    label = conscious_crest.label
    intensity = conscious_crest.intensity

    stance_map = {
        "explain": ("interpretive_explanation", "explain"),
        "clarify": ("careful_clarification", "clarify"),
        "comfort": ("supportive_attention", "comfort"),
        "hold": ("hold_for_coherence", "wait"),
        "contextualize": ("contextual_continuity", "contextualize"),
        "reframe": ("reframe", "re-evaluate"),
        "reframe_needed": ("reframe", "re-evaluate"),
        "attend": ("attend", "attend"),
        "comfort_bias": ("supportive_attention", "comfort"),
        "caution": ("careful_clarification", "clarify"),
        "warmth": ("supportive_attention", "comfort"),
        "hesitation": ("careful_clarification", "clarify"),
        "steady": ("attend", "explain"),
        "steady_continuation": ("interpretive_explanation", "explain"),
        "familiar": ("contextual_continuity", "contextualize"),
        "continuity_pull": ("contextual_continuity", "contextualize"),
        "novelty": ("interpretive_explanation", "explain"),
        "novel": ("interpretive_explanation", "explain"),
        "strain": ("cautious_load_management", "slow_down"),
        "limitation": ("cautious_load_management", "slow_down"),
        "urgency": ("attend", "attend"),
        "resonance": ("interpretive_explanation", "explain"),
        "alignment": ("interpretive_explanation", "explain"),
        "surprise": ("reframe", "re-evaluate"),
        "low_certainty": ("careful_clarification", "clarify"),
        "tension": ("attend", "attend"),
    }
    stance, action = stance_map.get(label, ("attend", "hold"))

    should_speak = intensity >= 0.42 and coherence >= 0.28
    if label == "hold":
        should_speak = False
    if getattr(overlay, "interaction_state", "present") == "present" and intensity >= 0.4:
        should_speak = True

    if intensity >= 0.68 and should_speak:
        processing_mode = "reactive"
    elif intensity >= 0.38:
        processing_mode = "blended"
    elif not should_speak:
        processing_mode = "holding"
    else:
        processing_mode = "deliberative"

    return stance, action, should_speak, processing_mode


def build_contextual_overlay(
    payload: Any,
    evidence: Dict[str, Any],
    contract_snapshot: Dict[str, Any],
    sensory_context: Dict[str, Any],
) -> ContextualOverlay:
    """Build the transient present-state overlay for this turn."""
    contract_p = dict(contract_snapshot.get("P", {}) or {})
    contract_m = dict(contract_snapshot.get("M", {}) or {})
    established_turn = dict(evidence.get("established_turn_state", {}) or {})
    surface_input = dict(evidence.get("surface_input", {}) or {})
    surface_frame = dict(evidence.get("surface_conversation_frame", {}) or {})

    payload_str = str(payload or "").strip()
    if len(payload_str) > 140:
        payload_str = payload_str[:137].rstrip() + "..."

    present_anchor = (
        payload_str
        or str(surface_input.get("full_phrase", "") or "").strip()
        or str(surface_input.get("raw_text", "") or "").strip()
    )

    active_topic = str(
        contract_m.get("active_topic", "")
        or surface_frame.get("current_topic", "")
        or ""
    ).strip()
    active_crystals = [t for t in [active_topic] if t]

    surface_reactive = dict(contract_p.get("surface_reactive_emotion", {}) or established_turn.get("surface_reactive_emotion", {}) or {})
    tone = str(
        surface_reactive.get("dominant", "")
        or contract_p.get("dominant_emotion", "")
        or evidence.get("tone", "")
        or "neutral"
    ).lower()

    interaction_state = "present"
    if surface_frame.get("mode") == "followup" or evidence.get("continuation_mode"):
        interaction_state = "followup"
    elif evidence.get("recall_mode"):
        interaction_state = "recall"

    frame_continuity = clip01(contract_m.get("frame_continuity", 0.0))
    emotional_intensity = clip01(surface_reactive.get("intensity", 0.0))
    reinforcement_hint = clip01(
        frame_continuity * 0.4
        + emotional_intensity * 0.35
        + clip01(sensory_context.get("maturity", 0.0)) * 0.25
    )

    return ContextualOverlay(
        present_anchor=present_anchor,
        active_crystals=active_crystals,
        present_sensory={
            "maturity": round(clip01(sensory_context.get("maturity", 0.0)), 4),
            "dominant_facet": str(sensory_context.get("dominant_facet", "") or ""),
        },
        present_tone=tone,
        interaction_state=interaction_state,
        reinforcement_hint=round(reinforcement_hint, 4),
    )


def recursion_weights_from_lattice(lattice: Any) -> Optional[Dict[str, float]]:
    """Derive the {REC_SURFACE, REC_SHALLOW, REC_MODERATE, REC_DEEP, REC_CORE}
    weight dict from the live IVM lattice's node depth distribution, for
    emit_subsystem_crests()'s optional recursion_weights param (15D coverage).

    Duck-typed: reads node.recursion_level.name off each IVMNode in
    lattice.nodes, normalizes to fractions summing to ~1.0. No aurora_ivm
    import required.

    Returns None if lattice is unavailable or has no admitted nodes — callers
    then fall back to the prior 10D I-state-only coverage check, unchanged.
    """
    nodes = getattr(lattice, "nodes", None)
    if not nodes:
        return None
    try:
        node_values = list(nodes.values()) if hasattr(nodes, "values") else list(nodes)
    except Exception:
        return None
    if not node_values:
        return None

    counts: Dict[str, int] = {}
    for node in node_values:
        try:
            level_name = str(node.recursion_level.name)
        except Exception:
            continue
        counts[level_name] = counts.get(level_name, 0) + 1

    total = sum(counts.values())
    if total <= 0:
        return None

    return {
        f"REC_{level}": counts.get(level, 0) / total
        for level in ("SURFACE", "SHALLOW", "MODERATE", "DEEP", "CORE")
    }


class DualStrataBridge:
    """Crest convergence orchestrator — recursive waveform-crest ecology."""

    def __init__(self, state_dir: Optional[str] = None):
        base = Path(state_dir) if state_dir else (Path(__file__).resolve().parents[2] / "aurora_state")
        self.state_dir = Path(base)
        # Bounded in-memory frame log (replaces dual_strata_frame_log.jsonl on disk)
        self._frame_log: deque = deque(maxlen=50)

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
        recursion_weights: Optional[Dict[str, float]] = None,
    ) -> DualStrataSnapshot:
        evidence = dict(evidence or {})
        contract_snapshot = dict(contract_snapshot or {})

        # 1. Build the present overlay (transient)
        sensory_context = dict(getattr(assembly_result, "sensory_context", {}) or {})
        overlay = build_contextual_overlay(payload, evidence, contract_snapshot, sensory_context)

        # 2. Build the prediction detail object (SUBSURFACE-ONLY)
        prediction_signal = build_prediction_signal(
            payload=payload,
            evidence=evidence,
            contract_snapshot=contract_snapshot,
            sensory_context=sensory_context,
            entropy_state=getattr(assembly_result, "entropy_state", None),
        )

        # 3. Emit subsystem crests — all eight waveforms
        adjusted_axes = _extract_adjusted_axes(assembly_result)
        pressure_snapshot = _extract_pressure_snapshot(dict(evidence.get("pressure_snapshot") or {}))
        projection = dict(evidence.get("subsurface_projection") or {})

        sub_crests = emit_subsystem_crests(
            assembly_result=assembly_result,
            payload=payload,
            evidence=evidence,
            contract_snapshot=contract_snapshot,
            prediction_signal=prediction_signal,
            projection=projection,
            sensory_context=sensory_context,
            adjusted_axes=adjusted_axes,
            pressure_snapshot=pressure_snapshot,
            recursion_weights=recursion_weights,
        )

        # 4. Subsurface convergence — converge 8 sub-crests into ONE
        subsurface_crest = converge_crests(sub_crests, mode="subsurface")

        # 5. Build raw mechanism detail for downward traversal only
        _raw_coherence = getattr(assembly_result, "coherence", None)
        if _raw_coherence is None:
            _es = getattr(assembly_result, "entropy_state", {}) or {}
            _raw_coherence = float(_es.get("coherence", 0.45))
        _assembly_coherence = clip01(float(_raw_coherence or 0.45))

        contract_p = dict(contract_snapshot.get("P", {}) or {})
        contract_m = dict(contract_snapshot.get("M", {}) or {})
        contract_b = dict(contract_snapshot.get("B", {}) or {})
        contract_n = dict(contract_snapshot.get("N", {}) or {})
        established_turn = dict(evidence.get("established_turn_state") or {})
        surface_reactive = dict(contract_p.get("surface_reactive_emotion") or established_turn.get("surface_reactive_emotion") or {})

        prediction_dict = prediction_signal.to_dict()
        pressure_map_raw = normalize_axis_map({
            axis: adjusted_axes.get(axis, 0.0) * 0.7 + clip01(pressure_snapshot.get(axis, 0.0) if isinstance(pressure_snapshot, dict) else 0.0) * 0.3
            for axis in AXES
        })
        salience_seed = dict(pressure_map_raw)
        dominant_axis = subsurface_crest.axis
        salience_seed[dominant_axis] = salience_seed.get(dominant_axis, 0.0) + 0.12
        salience_seed["B"] = salience_seed.get("B", 0.0) + clip01(contract_b.get("ambiguity", 0.0)) * 0.25
        salience_seed["N"] = salience_seed.get("N", 0.0) + clip01(contract_n.get("total", 0.0)) * 0.2
        salience_seed["T"] = salience_seed.get("T", 0.0) + clip01(contract_m.get("frame_continuity", 0.0)) * 0.2
        salience_weights = normalize_axis_map(salience_seed)

        active_topic = str(contract_m.get("active_topic", "") or "").strip()
        tracked_surface_emotion = str(surface_reactive.get("dominant", "") or contract_p.get("dominant_emotion", "") or evidence.get("tone", "") or "neutral").lower()
        tracked_surface_intensity = clip01(surface_reactive.get("intensity", 0.0))
        deep_emotional = dict(contract_p.get("deep_emotional_state") or established_turn.get("deep_emotional_state") or {})
        deep_emotion = str(deep_emotional.get("dominant", "") or tracked_surface_emotion).lower()
        deep_passion = str(deep_emotional.get("passion", "") or "").strip()

        recalled_fragments: List[str] = []
        for val in (contract_m.get("active_topic"), dict(contract_m.get("focus_claim", {}) or {}).get("summary"), payload):
            frag = str(val or "").strip()
            if len(frag) > 140:
                frag = frag[:137] + "..."
            if frag and frag not in recalled_fragments:
                recalled_fragments.append(frag)

        instability_markers: List[Dict[str, Any]] = []
        if _assembly_coherence < 0.45:
            instability_markers.append({"label": "low_coherence", "severity": round(1.0 - _assembly_coherence, 4)})
        if getattr(assembly_result, "paradoxes", None):
            instability_markers.append({"label": "paradox_active", "severity": 0.8})
        if clip01(prediction_dict.get("mismatch", 0.0)) >= 0.45:
            instability_markers.append({"label": "prediction_mismatch", "severity": round(clip01(prediction_dict.get("mismatch", 0.0)), 4)})
        if clip01(contract_b.get("ambiguity", 0.0)) >= 0.55:
            instability_markers.append({"label": "boundary_blur", "severity": round(clip01(contract_b.get("ambiguity", 0.0)), 4)})

        candidate_interpretations: List[Dict[str, Any]] = []
        if active_topic:
            candidate_interpretations.append({"label": "topic_continuation", "confidence": round(max(0.35, clip01(contract_m.get("frame_continuity", 0.0))), 4)})
        if tracked_surface_emotion not in {"", "neutral", "calm"}:
            candidate_interpretations.append({"label": "affective_attention", "confidence": round(max(0.35, clip01(salience_weights.get("A", 0.0))), 4)})

        action_bias_candidates: List[Dict[str, Any]] = []
        if clip01(contract_b.get("ambiguity", 0.0)) >= 0.55:
            action_bias_candidates.append({"action": "clarify", "weight": round(clip01(contract_b.get("ambiguity", 0.0)), 4)})

        instability_weight = sum(float(item.get("severity", 0.0) or 0.0) for item in instability_markers[:3]) / max(1, min(3, len(instability_markers)))
        readiness = clip01(
            _assembly_coherence * 0.5
            + (1.0 - clip01(prediction_dict.get("mismatch", 0.0))) * 0.3
            + (1.0 - instability_weight) * 0.1
            + clip01(projection.get("readiness_bias", 0.0)) * 0.1
        )

        contract_signals = {
            "active_topic": active_topic,
            "dominant_emotion": tracked_surface_emotion,
            "tracked_surface_emotion": tracked_surface_emotion,
            "tracked_surface_intensity": round(tracked_surface_intensity, 4),
            "interpreted_deep_emotion": deep_emotion,
            "interpreted_deep_passion": deep_passion,
            "ambiguity": round(clip01(contract_b.get("ambiguity", 0.0)), 4),
            "cost_total": round(clip01(contract_n.get("total", 0.0)), 4),
            "frame_continuity": round(clip01(contract_m.get("frame_continuity", 0.0)), 4),
        }

        _subsurface_detail = {
            "prediction_signal": prediction_dict,
            "pressure_map": pressure_map_raw,
            "salience_weights": salience_weights,
            "candidate_interpretations": candidate_interpretations,
            "instability_markers": instability_markers,
            "action_bias_candidates": action_bias_candidates,
            "contract_signals": contract_signals,
            "recalled_fragments": recalled_fragments,
            "law_bindings": getattr(assembly_result, "law_bindings", []),
            "comparison_channels": ["incoming_input", "present_sensory", "DCE_root"],
            "origin_systems": ["incoming_input", "DimensionalSystems.process_synthesis", "DCEAssembly"],
            "sub_crests": [c.to_dict() for c in sub_crests],
            "coherence": round(_assembly_coherence, 4),
            "readiness": round(readiness, 4),
        }

        # 5. Build SubsurfaceState (crest-only public, detail private)
        subsurface = SubsurfaceState(
            subsurface_crest=subsurface_crest,
            sub_crests=sub_crests,
            dominant_axis=subsurface_crest.axis,
            frame_request=str(requested_frame or "balanced"),
            overlay=overlay,
            _subsurface_detail=_subsurface_detail,
        )

        # 5b. Micro-reasoning hypotheses (FIX-A009: generate_micro_reasoning
        # now reads prediction/coherence/contract_signals/salience_weights
        # from subsurface._subsurface_detail, which is populated above).
        # Folded back into the same dict object so persist_subsurface_detail()
        # and expand_crest() both see it.
        _mr_hypotheses = generate_micro_reasoning(
            subsurface,
            assembly_result=assembly_result,
            evidence=evidence,
            contract_snapshot=contract_snapshot,
        )
        _subsurface_detail["micro_reasoning"] = [h.to_dict() for h in _mr_hypotheses]

        # 6. Surface convergence — consume only subsurface_crest + overlay + coherence
        surface_input = dict(evidence.get("surface_input") or {})
        user_turn_present = bool(
            str(surface_input.get("raw_text", "") or "").strip()
            or str(surface_input.get("full_phrase", "") or "").strip()
            or str(surface_input.get("source_text", "") or "").strip()
            or str(payload or "").strip()
        )
        conscious_crest = converge_for_surface(
            subsurface_crest=subsurface_crest,
            overlay=overlay,
            coherence=_assembly_coherence,
            user_turn_present=user_turn_present,
        )

        # 7. Derive stance/action/should_speak FROM the conscious_crest label
        stance, action, should_speak, processing_mode = derive_surface_behavior(
            conscious_crest, subsurface_crest, overlay, coherence=_assembly_coherence
        )

        conscious = ConsciousFrame(
            conscious_crest=conscious_crest,
            subsurface_crest=subsurface_crest,
            overlay=overlay,
            stance=stance,
            selected_action=action,
            should_speak=should_speak,
            readiness=round(readiness, 4),
            coherence=round(_assembly_coherence, 4),
            dominant_axis=conscious_crest.axis,
            processing_mode=processing_mode,
        )

        snapshot = DualStrataSnapshot(
            subsurface_state=subsurface.to_dict(),
            conscious_frame=conscious.to_dict(),
        )
        self.persist(snapshot)
        self.persist_subsurface_detail(_subsurface_detail)
        return snapshot

    def persist(self, snapshot: DualStrataSnapshot) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        payload = snapshot.to_dict()
        payload["saved_at"] = time.time()
        snapshot_path = self.state_dir / "dual_strata_snapshot.json"
        snapshot_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True), encoding="utf-8")

        log_entry = {
            "ts": payload["saved_at"],
            "conscious_crest": payload.get("conscious_frame", {}).get("conscious_crest", {}).get("label", ""),
            "stance": payload.get("conscious_frame", {}).get("stance", ""),
            "selected_action": payload.get("conscious_frame", {}).get("selected_action", ""),
            "should_speak": bool(payload.get("conscious_frame", {}).get("should_speak", False)),
            "processing_mode": payload.get("conscious_frame", {}).get("processing_mode", ""),
            "dominant_axis": payload.get("conscious_frame", {}).get("dominant_axis", ""),
            "readiness": payload.get("conscious_frame", {}).get("readiness", 0.0),
        }
        # Keep last 50 frames in bounded in-memory deque (no disk write).
        self._frame_log.append(log_entry)

        # Sediment high-coherence frames into geological memory
        _sedi = getattr(self, "_sedimemory_ref", None)
        if _sedi is not None:
            try:
                from aurora_crystal_ingestion import maybe_sediment_frame
                cf = payload.get("conscious_frame", {})
                frame_for_sedi = dict(log_entry)
                frame_for_sedi["coherence"] = float(cf.get("coherence", 0.0))
                frame_for_sedi["conscious_crest"] = log_entry["conscious_crest"]
                maybe_sediment_frame(frame_for_sedi, _sedi)
            except Exception:
                pass

    def persist_subsurface_detail(self, detail: Dict[str, Any]) -> None:
        """Write subsurface detail to a private file for downward traversal only.
        The surface daemon never reads this file inline."""
        self.state_dir.mkdir(parents=True, exist_ok=True)
        detail_path = self.state_dir / "subsurface_detail.json"
        detail["saved_at"] = time.time()
        detail_path.write_text(json.dumps(detail, indent=2, ensure_ascii=True, sort_keys=True, default=str), encoding="utf-8")

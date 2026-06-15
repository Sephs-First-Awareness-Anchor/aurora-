# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _clip_text(value: Any, *, limit: int = 420) -> str:
    text = " ".join(str(value or "").split()).strip()
    if len(text) > limit:
        text = text[: limit - 1].rstrip() + "..."
    return text


def _string_list(values: Any, *, limit: int = 10) -> List[str]:
    out: List[str] = []
    for item in list(values or []):
        text = _clip_text(item, limit=160)
        if text and text not in out:
            out.append(text)
        if len(out) >= limit:
            break
    return out


def _vector_signal(values: Any) -> float:
    try:
        vec = [abs(float(v or 0.0)) for v in list(values or [])]
    except Exception:
        vec = []
    if not vec:
        return 0.0
    return min(1.0, sum(vec) / max(1.0, len(vec)))


@dataclass
class SensoryObservationPacket:
    observation_id: str
    created_at: float
    source: str
    modality: str
    confidence: float
    novelty: float
    summary: str
    visual_description: str = ""
    audio_description: str = ""
    recent_speech: str = ""
    recognitions: List[str] = field(default_factory=list)
    concepts_active: List[str] = field(default_factory=list)
    mic_live: bool = False
    camera_live: bool = False
    has_audio_vector: bool = False
    has_visual_vector: bool = False
    native_meaning: Dict[str, Any] = field(default_factory=dict)
    evidence_hash: str = ""
    speakable: bool = False
    gate_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _evidence_hash(fields: Dict[str, Any]) -> str:
    stable = json.dumps(fields, sort_keys=True, ensure_ascii=True)
    return hashlib.sha1(stable.encode("utf-8", errors="replace")).hexdigest()[:16]


def build_sensory_observation_packet(
    snapshot: Dict[str, Any],
    *,
    previous: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    snapshot = dict(snapshot or {})
    previous = dict(previous or {})
    vectors = dict(snapshot.get("sensory_vectors") or {})
    sensory_state = dict(snapshot.get("sensory_state") or {})
    recognitions = _string_list(dict(sensory_state.get("recognitions") or {}).get("recent"), limit=8)
    concepts = _string_list(snapshot.get("concepts_active"), limit=10)
    visual_description = _clip_text(snapshot.get("visual_description"), limit=320)
    audio_description = _clip_text(snapshot.get("audio_description"), limit=320)
    recent_speech = _clip_text(snapshot.get("recent_speech"), limit=320)
    summary = _clip_text(snapshot.get("summary"), limit=500)
    has_audio_vector = _vector_signal(vectors.get("audio_20d")) > 0.0001
    has_visual_vector = _vector_signal(vectors.get("vision_57d")) > 0.0001
    modality_parts = []
    if visual_description or has_visual_vector or bool(snapshot.get("camera_live", False)):
        modality_parts.append("visual")
    if audio_description or recent_speech or recognitions or has_audio_vector or bool(snapshot.get("mic_live", False)):
        modality_parts.append("auditory")
    modality = "+".join(modality_parts) if modality_parts else "sensory"

    evidence_fields = {
        "visual_description": visual_description,
        "audio_description": audio_description,
        "recent_speech": recent_speech,
        "recognitions": recognitions,
        "concepts_active": concepts,
        "has_audio_vector": has_audio_vector,
        "has_visual_vector": has_visual_vector,
    }
    evidence = _evidence_hash(evidence_fields)
    previous_hash = str(previous.get("last_evidence_hash", "") or "")
    age_since_spoken = time.time() - float(previous.get("last_spoken_at", 0.0) or 0.0)

    direct_content = bool(visual_description or audio_description or recent_speech)
    learned_content = bool(recognitions or concepts)
    vector_content = bool(has_audio_vector or has_visual_vector)
    novelty = 0.0
    if direct_content:
        novelty += 0.44
    if learned_content:
        novelty += 0.24
    if vector_content:
        novelty += 0.18
    if evidence and evidence != previous_hash:
        novelty += 0.24
    novelty = min(1.0, novelty)

    confidence = 0.0
    if direct_content:
        confidence += 0.42
    if vector_content:
        confidence += 0.24
    if learned_content:
        confidence += 0.18
    if bool(snapshot.get("mic_live", False)) or bool(snapshot.get("camera_live", False)):
        confidence += 0.10
    confidence = min(1.0, confidence)

    speakable = (
        age_since_spoken >= 90.0
        and confidence >= 0.38
        and novelty >= 0.48
        and bool(direct_content or recent_speech or vector_content or learned_content)
    )
    if not speakable:
        if age_since_spoken < 90.0:
            gate_reason = "cooldown"
        elif confidence < 0.38:
            gate_reason = "low_confidence"
        elif novelty < 0.48:
            gate_reason = "low_novelty"
        else:
            gate_reason = "empty_observation"
    else:
        gate_reason = "fresh_observation"

    packet = SensoryObservationPacket(
        observation_id=f"sensory-{int(float(snapshot.get('updated_at', 0.0) or time.time()) * 1000)}-{evidence}",
        created_at=float(snapshot.get("updated_at", 0.0) or time.time()),
        source="surface_sensory_snapshot",
        modality=modality,
        confidence=round(confidence, 4),
        novelty=round(novelty, 4),
        summary=summary,
        visual_description=visual_description,
        audio_description=audio_description,
        recent_speech=recent_speech,
        recognitions=recognitions,
        concepts_active=concepts,
        mic_live=bool(snapshot.get("mic_live", False)),
        camera_live=bool(snapshot.get("camera_live", False)),
        has_audio_vector=has_audio_vector,
        has_visual_vector=has_visual_vector,
        native_meaning=dict(snapshot.get("native_meaning") or {}),
        evidence_hash=evidence,
        speakable=speakable,
        gate_reason=gate_reason,
    )
    return packet.to_dict()


def observation_to_unified_turn(packet: Dict[str, Any]) -> str:
    packet = dict(packet or {})
    payload = {
        "source": "sensory_autonomy",
        "modality": packet.get("modality", ""),
        "confidence": packet.get("confidence", 0.0),
        "novelty": packet.get("novelty", 0.0),
        "summary": packet.get("summary", ""),
        "visual_description": packet.get("visual_description", ""),
        "audio_description": packet.get("audio_description", ""),
        "recent_speech": packet.get("recent_speech", ""),
        "recognitions": packet.get("recognitions", []),
        "concepts_active": packet.get("concepts_active", []),
        "native_meaning": packet.get("native_meaning", {}),
    }
    return "[PRESENT_SENSORY_OBSERVATION]\n" + json.dumps(payload, ensure_ascii=True, sort_keys=True)


def sensory_gate_state_update(packet: Dict[str, Any], previous: Dict[str, Any] | None = None) -> Tuple[Dict[str, Any], bool]:
    previous = dict(previous or {})
    packet = dict(packet or {})
    spoken = bool(packet.get("speakable", False))
    state = dict(previous)
    state["last_checked_at"] = time.time()
    state["last_observation_id"] = str(packet.get("observation_id", "") or "")
    state["last_gate_reason"] = str(packet.get("gate_reason", "") or "")
    state["last_evidence_hash"] = str(packet.get("evidence_hash", "") or state.get("last_evidence_hash", "") or "")
    if spoken:
        state["last_spoken_at"] = time.time()
        state["last_spoken_observation_id"] = str(packet.get("observation_id", "") or "")
    return state, spoken


# ------------------------------------------------------------------ #
#  Per-tick orchestration
# ------------------------------------------------------------------ #

_BASE_DIR = Path(__file__).parent.parent.parent  # aurora repo root
_STATE_DIR_DEFAULT = _BASE_DIR / "aurora_state"
_GATE_FILENAME = "sensory_observation_gate.json"
_PENDING_FILENAME = "sensory_observation_pending.json"


def _resolve_state_dir(systems: Dict[str, Any]) -> Path:
    """Mirror the state_dir resolution used elsewhere in dual_strata."""
    return Path(str(systems.get("state_dir") or _STATE_DIR_DEFAULT))


def _load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            data = json.loads(path.read_text())
            if data is not None:
                return data
    except Exception:
        pass
    return default


def _save_json(path: Path, data: Any) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = str(path) + ".tmp"
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, str(path))
    except Exception:
        pass


def run_sensory_observation_cycle(systems: Dict[str, Any]) -> Dict[str, Any]:
    """Subsurface per-tick cycle: "accelerated sim leaves a message for self".

    Reads the live surface sensory snapshot (surface_sensory_snapshot.json,
    written every cycle by write_surface_snapshot), builds an observation
    packet against persisted gate-state, and applies the novelty/confidence/
    cooldown gate from sensory_gate_state_update.

    Gate-state (cooldown + evidence-hash tracking) is persisted to
    aurora_state/sensory_observation_gate.json so it survives across ticks
    and processes. When the gate says `speakable`, the packet is staged as
    "the message the surface-self reads next cycle": written to both
    systems["_sensory_observation_pending"] (Tier 1) and
    aurora_state/sensory_observation_pending.json (Tier 2). The
    _chain_down4_meaning consumer injects it into law_bindings and clears
    both tiers so it is surfaced exactly once.

    Best-effort: any failure returns {} and leaves systems untouched.
    """
    try:
        from .sensory_snapshot_channel import read_surface_snapshot

        state_dir = _resolve_state_dir(systems)
        snapshot = read_surface_snapshot(state_dir)
        gate_state = _load_json(state_dir / _GATE_FILENAME, {})

        packet = build_sensory_observation_packet(snapshot, previous=gate_state)
        new_gate_state, spoken = sensory_gate_state_update(packet, previous=gate_state)
        _save_json(state_dir / _GATE_FILENAME, new_gate_state)

        if spoken:
            _save_json(state_dir / _PENDING_FILENAME, packet)
            systems["_sensory_observation_pending"] = packet

        return {"packet": packet, "spoken": spoken, "gate_state": new_gate_state}
    except Exception:
        return {}

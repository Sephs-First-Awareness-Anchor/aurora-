from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional


def snapshot_path(state_dir: str | Path) -> Path:
    return Path(state_dir) / "surface_sensory_snapshot.json"


def guidance_path(state_dir: str | Path) -> Path:
    return Path(state_dir) / "surface_sensory_guidance_queue.json"


def _read_json(path: Path, default: Any) -> Any:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)


def read_surface_snapshot(state_dir: str | Path) -> Dict[str, Any]:
    data = _read_json(snapshot_path(state_dir), {})
    return data if isinstance(data, dict) else {}


def read_surface_guidance_queue(state_dir: str | Path) -> list[Dict[str, Any]]:
    data = _read_json(guidance_path(state_dir), [])
    return list(data) if isinstance(data, list) else []


def append_surface_guidance(state_dir: str | Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    path = guidance_path(state_dir)
    queue = read_surface_guidance_queue(state_dir)
    event = dict(payload or {})
    event.setdefault("event_id", f"guidance-{int(time.time() * 1000)}")
    event.setdefault("created_at", time.time())
    queue.append(event)
    queue = queue[-64:]
    _write_json(path, queue)
    return event


def _default_summary(mic_live: bool, camera_live: bool, sensory_state: Dict[str, Any]) -> str:
    if mic_live and camera_live:
        lead = "Surface is tracking audio and vision live."
    elif mic_live:
        lead = "Surface is tracking live audio."
    elif camera_live:
        lead = "Surface is tracking live vision."
    else:
        lead = "Surface sensory feed is quiet."
    frames = int(sensory_state.get("total_frames", 0) or 0)
    maturity = float(sensory_state.get("maturity", 0.0) or 0.0)
    if frames > 0:
        lead += f" Current frame-load={frames}, maturity={maturity:.2f}."
    recent = list(dict(sensory_state.get("recognitions") or {}).get("recent") or [])
    if recent:
        lead += " Recognitions: " + ", ".join(str(item) for item in recent[:3]) + "."
    return lead


def _compact_text(value: Any, *, limit: int = 240) -> str:
    text = " ".join(str(value or "").split()).strip()
    if len(text) > limit:
        text = text[: limit - 1].rstrip() + "..."
    return text


def _build_sensory_native_bundle(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    snapshot = dict(snapshot or {})
    sensory_state = dict(snapshot.get("sensory_state") or {})
    sensory_context = dict(snapshot.get("sensory_context") or {})
    visual_description = _compact_text(snapshot.get("visual_description") or sensory_context.get("visual"))
    audio_description = _compact_text(snapshot.get("audio_description") or sensory_context.get("audio"))
    recent_speech = _compact_text(snapshot.get("recent_speech") or sensory_context.get("recent_speech"))
    roots = [
        str(snapshot.get("summary", "") or "").strip(),
        str(sensory_context.get("scene_type", "") or "").strip(),
        visual_description,
        audio_description,
        recent_speech,
    ]
    roots.extend(
        str(item).strip()
        for item in list(snapshot.get("concepts_active") or sensory_context.get("concepts_active") or [])
        if str(item).strip()
    )
    roots.extend(
        str(item).strip()
        for item in list(dict(sensory_state.get("recognitions") or {}).get("recent") or [])
        if str(item).strip()
    )
    roots = [root for root in roots if root]
    bundle = {
        "primary": {
            "meaning_id": str(snapshot.get("meaning_id") or f"sensory-{int(float(snapshot.get('updated_at', 0.0) or time.time()) * 1000)}"),
            "created_at": float(snapshot.get("updated_at", time.time()) or time.time()),
            "semantic_roots": list(dict.fromkeys(roots[:12])),
            "diagonal_anchor": "Boundary_Operator_of_Meaning",
            "source_origin": "sensory_multimodal",
            "modality_origin": "visual_auditory" if visual_description and audio_description else ("visual" if visual_description else ("auditory" if audio_description else "sensory")),
            "source_semantic_stage": "processed_sensory",
            "sensory_lineage_tags": [
                f"scene:{snapshot.get('trigger', '') or 'interval'}",
                f"visual:{visual_description[:48]}" if visual_description else "",
                f"audio:{audio_description[:48]}" if audio_description else "",
            ],
            "context_refs": [
                "sensory_scene",
                "sensory_crystal",
                "surface_snapshot",
            ],
            "memory_refs": [],
            "law_bindings": [
                {
                    "domain_letter": "B",
                    "domain_name": "Meaning",
                    "family": "Boundary",
                    "dimension": "OPERATOR",
                    "score": 0.82,
                    "nc_name": "boundary",
                    "summary": "what frames, contains, or separates sensory meaning",
                },
                {
                    "domain_letter": "X",
                    "domain_name": "Information",
                    "family": "Existential",
                    "dimension": "POLARITY",
                    "score": 0.71,
                    "nc_name": "existence",
                    "summary": "what is actually present in sensory reality",
                },
            ],
        }
    }
    return bundle


def present_sensory_perspective_from_snapshot(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    snapshot = dict(snapshot or {})
    sensory_context = dict(snapshot.get("sensory_context") or {})
    latest_guidance = dict(snapshot.get("latest_guidance") or sensory_context.get("latest_guidance") or {})
    native_bundle = snapshot.get("native_meaning_bundle") or _build_sensory_native_bundle(snapshot)
    return {
        "summary": str(snapshot.get("summary", "") or "Present sensory perspective is stable."),
        "mic_live": bool(snapshot.get("mic_live", False)),
        "camera_live": bool(snapshot.get("camera_live", False)),
        "scope": "constant_surface_feed",
        "trigger": str(snapshot.get("trigger", "") or "interval"),
        "flagged": bool(snapshot.get("flagged", False)),
        "recognitions": dict(snapshot.get("sensory_state", {}) or {}).get("recognitions", {}),
        "visual_description": _compact_text(snapshot.get("visual_description") or sensory_context.get("visual")),
        "audio_description": _compact_text(snapshot.get("audio_description") or sensory_context.get("audio")),
        "recent_speech": _compact_text(snapshot.get("recent_speech") or sensory_context.get("recent_speech")),
        "latest_guidance": latest_guidance,
        "guidance_summary": _compact_text(snapshot.get("guidance_summary") or latest_guidance.get("summary")),
        "pending_visual_question": _compact_text(snapshot.get("pending_visual_question"), limit=320),
        "visual_uncertainty_streak": int(snapshot.get("visual_uncertainty_streak", 0) or 0),
        "native_meaning_bundle": native_bundle,
        "native_meaning": dict((native_bundle or {}).get("primary") or {}),
        "concepts_active": [
            str(item).strip()
            for item in list(snapshot.get("concepts_active") or sensory_context.get("concepts_active") or [])
            if str(item).strip()
        ][:10],
    }


def write_surface_snapshot(
    state_dir: str | Path,
    sensory_state: Dict[str, Any],
    *,
    mic_live: bool,
    camera_live: bool,
    sensory_vectors: Optional[Dict[str, Any]] = None,
    sensory_context: Optional[Dict[str, Any]] = None,
    visual_description: str = "",
    audio_description: str = "",
    recent_speech: str = "",
    latest_guidance: Optional[Dict[str, Any]] = None,
    guidance_summary: str = "",
    pending_visual_question: str = "",
    visual_uncertainty_streak: int = 0,
    concepts_active: Optional[list[Any]] = None,
    native_meaning_bundle: Optional[Dict[str, Any]] = None,
    trigger: str = "interval",
    flagged: bool = False,
    reason: str = "",
    summary: Optional[str] = None,
) -> Dict[str, Any]:
    sensory_state = dict(sensory_state or {})
    sensory_context = dict(sensory_context or {})
    latest_guidance = dict(latest_guidance or sensory_context.get("latest_guidance") or {})
    visual_description = _compact_text(visual_description or sensory_context.get("visual"))
    audio_description = _compact_text(audio_description or sensory_context.get("audio"))
    recent_speech = _compact_text(recent_speech or sensory_context.get("recent_speech"))
    guidance_summary = _compact_text(guidance_summary or latest_guidance.get("summary"))
    pending_visual_question = _compact_text(pending_visual_question, limit=320)
    concepts = [
        str(item).strip()
        for item in list(concepts_active or sensory_context.get("concepts_active") or [])
        if str(item).strip()
    ][:10]
    summary_text = str(summary or _default_summary(bool(mic_live), bool(camera_live), sensory_state))
    detail_lines = []
    if visual_description:
        detail_lines.append(f"Seeing: {visual_description}")
    if audio_description:
        detail_lines.append(f"Hearing: {audio_description}")
    if pending_visual_question:
        detail_lines.append(f"Question: {pending_visual_question}")
    if detail_lines:
        summary_text = _compact_text(summary_text + " " + " ".join(detail_lines[:2]), limit=420)
    payload = {
        "updated_at": time.time(),
        "updated": time.strftime("%H:%M:%S"),
        "source": "surface_daemon",
        "trigger": str(trigger or "interval"),
        "flagged": bool(flagged),
        "reason": str(reason or ""),
        "mic_live": bool(mic_live),
        "camera_live": bool(camera_live),
        "summary": summary_text,
        "sensory_state": sensory_state,
        "sensory_vectors": dict(sensory_vectors or {}),
        "sensory_context": sensory_context,
        "visual_description": visual_description,
        "audio_description": audio_description,
        "recent_speech": recent_speech,
        "latest_guidance": latest_guidance,
        "guidance_summary": guidance_summary,
        "pending_visual_question": pending_visual_question,
        "visual_uncertainty_streak": int(visual_uncertainty_streak or 0),
        "concepts_active": concepts,
    }
    if native_meaning_bundle:
        payload["native_meaning_bundle"] = dict(native_meaning_bundle or {})
        payload["native_meaning"] = dict((native_meaning_bundle or {}).get("primary") or {})
    elif concepts or visual_description or audio_description or recent_speech:
        payload["native_meaning_bundle"] = _build_sensory_native_bundle(payload)
        payload["native_meaning"] = dict((payload["native_meaning_bundle"] or {}).get("primary") or {})
    payload["present_sensory_perspective"] = present_sensory_perspective_from_snapshot(payload)
    _write_json(snapshot_path(state_dir), payload)
    return payload

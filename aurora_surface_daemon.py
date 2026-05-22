#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import signal
import threading
import time
import traceback
from pathlib import Path
from typing import Any, Dict, Optional

from aurora import boot_aurora, process_external_user_turn
from aurora_daemon import _start_ambient_response_listener, _start_voice_listener
from aurora_internal.dual_strata.sensory_control_channel import camera_enabled as sensory_camera_enabled
from aurora_internal.dual_strata.sensory_snapshot_channel import (
    present_sensory_perspective_from_snapshot,
    read_surface_snapshot,
    write_surface_snapshot,
)
from aurora_internal.dual_strata.surface_continuity_feed import write_continuity_packet


_BASE_DIR = Path(__file__).parent
_STATE_DIR = _BASE_DIR / "aurora_state"
_QUEUE_FILE = _STATE_DIR / "surface_turn_queue.json"
_RESULT_FILE = _STATE_DIR / "surface_turn_result.json"
_STATUS_FILE = _STATE_DIR / "surface_daemon_status.json"
_LOG_FILE = _STATE_DIR / "surface_daemon.log"
_SNAPSHOT_FILE = _STATE_DIR / "dual_strata_snapshot.json"
_PROJECTION_FILE = _STATE_DIR / "subsurface_projection.json"


def _surface_mic_live(systems: Dict[str, Any]) -> bool:
    integration = systems.get("sensory_integration")
    return bool(
        integration is not None
        and getattr(integration, "listening_enabled", False)
        and getattr(getattr(integration, "_listen_thread", None), "is_alive", lambda: False)()
    )


def _surface_camera_live() -> bool:
    if not sensory_camera_enabled(_STATE_DIR):
        return False
    frame_path = _STATE_DIR / "vision_seeds" / "camera" / "frame_latest.png"
    if frame_path.exists() and (time.time() - frame_path.stat().st_mtime) < 30:
        return True
    fallback = _STATE_DIR / "vision_snapshots" / "sight_latest.jpg"
    return bool(fallback.exists() and (time.time() - fallback.stat().st_mtime) < 30)


def _surface_sensory_owner(systems: Dict[str, Any]) -> Any:
    integration = systems.get("sensory_integration")
    hardware = systems.get("hardware")
    candidates = [
        systems.get("sensory_crystal"),
        getattr(integration, "sensory_crystal", None) if integration is not None else None,
        getattr(hardware, "sensory_crystal", None) if hardware is not None else None,
    ]
    for candidate in candidates:
        if candidate is not None and hasattr(candidate, "get_state"):
            return candidate
    return None


def _surface_sensory_vectors(systems: Dict[str, Any]) -> Dict[str, Any]:
    integration = systems.get("sensory_integration")
    hardware = systems.get("hardware")
    perception = systems.get("perception")
    audio_vec = []
    visual_vec = []
    for owner in (integration, hardware, perception):
        if owner is None:
            continue
        cand_audio = list(getattr(owner, "_crystal_last_audio", []) or [])
        cand_visual = list(getattr(owner, "_crystal_last_visual", []) or [])
        if not cand_audio and hasattr(owner, "_current_audio_vector"):
            try:
                cand_audio = list(owner._current_audio_vector() or [])
            except Exception:
                cand_audio = []
        if not cand_visual and hasattr(owner, "_current_visual_vector"):
            try:
                cand_visual = list(owner._current_visual_vector() or [])
            except Exception:
                cand_visual = []
        if any(cand_audio) or any(cand_visual):
            audio_vec = cand_audio
            visual_vec = cand_visual
            break
    return {
        "audio_20d": audio_vec[:20],
        "vision_57d": visual_vec[:57] if sensory_camera_enabled(_STATE_DIR) else [],
    }


def _surface_text(value: Any, *, limit: int = 280) -> str:
    text = " ".join(str(value or "").split()).strip()
    if len(text) > limit:
        text = text[: limit - 1].rstrip() + "..."
    return text


def _normalize_visual_payload(visual: Any) -> Dict[str, Any]:
    if isinstance(visual, dict):
        payload = dict(visual)
    elif hasattr(visual, "to_dict"):
        try:
            payload = dict(visual.to_dict() or {})
        except Exception:
            payload = {}
    elif hasattr(visual, "__dict__"):
        payload = dict(getattr(visual, "__dict__", {}) or {})
    else:
        payload = {}

    payload.setdefault("label", "camera")
    payload.setdefault("features", {})
    payload.setdefault("faces", [])
    payload.setdefault("objects", [])
    if not isinstance(payload.get("features"), dict):
        payload["features"] = {}
    if not isinstance(payload.get("faces"), list):
        payload["faces"] = list(payload.get("faces") or [])
    if not isinstance(payload.get("objects"), list):
        payload["objects"] = list(payload.get("objects") or [])
    return payload


def _write_latest_camera_frame(frame: Any) -> None:
    frame_path = _STATE_DIR / "vision_seeds" / "camera" / "frame_latest.png"
    fallback_path = _STATE_DIR / "vision_snapshots" / "sight_latest.jpg"
    frame_path.parent.mkdir(parents=True, exist_ok=True)
    fallback_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        import cv2  # type: ignore
        if frame is None:
            return
        png_tmp = frame_path.with_suffix(frame_path.suffix + ".tmp")
        jpg_tmp = fallback_path.with_suffix(fallback_path.suffix + ".tmp")
        if cv2.imwrite(str(png_tmp), frame):
            png_tmp.replace(frame_path)
        if cv2.imwrite(str(jpg_tmp), frame):
            jpg_tmp.replace(fallback_path)
        return
    except Exception:
        pass


def _write_latest_camera_path(src: Path) -> None:
    frame_path = _STATE_DIR / "vision_seeds" / "camera" / "frame_latest.png"
    fallback_path = _STATE_DIR / "vision_snapshots" / "sight_latest.jpg"
    frame_path.parent.mkdir(parents=True, exist_ok=True)
    fallback_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copyfile(src, fallback_path)
        shutil.copyfile(src, frame_path)
    except Exception:
        try:
            shutil.copyfile(src, fallback_path)
        except Exception:
            pass

    try:
        from PIL import Image as PILImage  # type: ignore
        if frame is None:
            return
        image = PILImage.fromarray(frame)
        image.save(frame_path)
        image.save(fallback_path)
    except Exception:
        pass


def _surface_event_recent(event: Any, *, max_age_s: float = 45.0) -> bool:
    try:
        return event is not None and (time.time() - float(getattr(event, "timestamp", 0.0) or 0.0)) <= max_age_s
    except Exception:
        return False


def _ambient_audio_observation() -> str:
    live_path = _STATE_DIR / "ambient_audio_latest.json"
    if not live_path.exists():
        return ""
    try:
        if (time.time() - live_path.stat().st_mtime) > 20.0:
            return ""
        payload = json.loads(live_path.read_text())
    except Exception:
        return ""

    activity = str(payload.get("activity", "ambient") or "ambient").strip().lower()
    rms_db = float(payload.get("rms_db", -60.0) or -60.0)
    if rms_db > -20.0:
        loudness = "strong"
    elif rms_db > -35.0:
        loudness = "moderate"
    elif rms_db > -50.0:
        loudness = "light"
    else:
        loudness = "faint"

    if activity == "speech":
        return f"I can hear {loudness} speech-like audio in the environment."
    if activity == "noise":
        return f"I can hear {loudness} background noise."
    if activity == "active":
        return f"I can hear {loudness} active ambient sound."
    return f"I can hear {loudness} ambient sound."


def _surface_present_sensory_details(systems: Dict[str, Any]) -> Dict[str, Any]:
    integration = systems.get("sensory_integration")
    previous_snapshot = read_surface_snapshot(_STATE_DIR)
    details: Dict[str, Any] = {
        "sensory_context": {},
        "visual_description": "",
        "audio_description": "",
        "recent_speech": "",
        "latest_guidance": {},
        "guidance_summary": "",
        "concepts_active": [],
    }

    context: Dict[str, Any] = {}
    if integration is not None and hasattr(integration, "get_sensory_context"):
        try:
            context = dict(integration.get_sensory_context() or {})
        except Exception:
            context = {}
    details["sensory_context"] = context

    latest_visual = getattr(integration, "_latest_visual_event", None) if integration is not None else None
    latest_audio = getattr(integration, "_latest_audio_event", None) if integration is not None else None

    details["visual_description"] = _surface_text(
        context.get("visual")
        or (getattr(latest_visual, "linguistic_description", "") if _surface_event_recent(latest_visual) else "")
    )
    details["audio_description"] = _surface_text(
        context.get("audio")
        or (getattr(latest_audio, "linguistic_description", "") if _surface_event_recent(latest_audio) else "")
        or _ambient_audio_observation()
    )
    if not details["visual_description"]:
        previous_visual = _surface_text(previous_snapshot.get("visual_description", ""))
        previous_updated_at = float(previous_snapshot.get("updated_at", 0.0) or 0.0)
        if previous_visual and (time.time() - previous_updated_at) <= 20.0:
            details["visual_description"] = previous_visual
    if not details["audio_description"]:
        previous_audio = _surface_text(previous_snapshot.get("audio_description", ""))
        previous_updated_at = float(previous_snapshot.get("updated_at", 0.0) or 0.0)
        if previous_audio and (time.time() - previous_updated_at) <= 20.0:
            details["audio_description"] = previous_audio

    recent_speech = context.get("recent_speech")
    if not recent_speech and _surface_event_recent(latest_audio):
        recent_speech = dict(getattr(latest_audio, "data", {}) or {}).get("transcription", "")
    details["recent_speech"] = _surface_text(recent_speech)

    latest_guidance = dict(context.get("latest_guidance") or getattr(integration, "_latest_guidance", {}) or {})
    details["latest_guidance"] = latest_guidance
    details["guidance_summary"] = _surface_text(
        latest_guidance.get("summary")
        or latest_guidance.get("label")
        or latest_guidance.get("source_text")
    )

    concepts_active = []
    for item in list(context.get("concepts_active") or []):
        item_s = str(item).strip()
        if item_s and item_s not in concepts_active:
            concepts_active.append(item_s)
    for event in (latest_visual, latest_audio):
        if not _surface_event_recent(event):
            continue
        for item in list(getattr(event, "concepts_activated", []) or []):
            item_s = str(item).strip()
            if item_s and item_s not in concepts_active:
                concepts_active.append(item_s)
    details["concepts_active"] = concepts_active[:10]
    return details


def _derive_surface_visual_question(
    *,
    visual_description: str,
    concepts_active: list[str],
    sensory_state: Dict[str, Any],
    camera_live: bool,
    previous_snapshot: Dict[str, Any],
) -> tuple[str, int]:
    if not camera_live:
        return "", 0

    description = _surface_text(visual_description, limit=240)
    if not description:
        return "", 0

    recognitions = [
        str(item).strip()
        for item in list(dict(sensory_state.get("recognitions") or {}).get("recent") or [])
        if str(item).strip()
    ]
    has_live_binding = bool(concepts_active) or any(
        item.lower().startswith(("visual:", "guided:", "cross-modal:")) or "saw" in item.lower()
        for item in recognitions
    )

    desc_low = description.lower()
    uncertain = (not has_live_binding) and (
        "not sure" in desc_low
        or "cannot" in desc_low
        or "can't" in desc_low
        or "couldn't" in desc_low
        or "something" in desc_low
        or "i see someone" in desc_low
        or "person is present" in desc_low
        or desc_low.startswith("the scene is")
    )
    if not uncertain:
        return "", 0

    prev_streak = int(previous_snapshot.get("visual_uncertainty_streak", 0) or 0)
    streak = prev_streak + 1
    if streak < 2:
        return "", streak

    if "i see someone" in desc_low or "person is present" in desc_low:
        question = "I can see a person, but I do not know who they are yet. Who am I looking at?"
    else:
        question = f"{description} I still do not know what I am looking at yet. What am I looking at?"
    return _surface_text(question, limit=320), streak


def _clear_camera_frame_cache() -> None:
    for stale_path in (
        _STATE_DIR / "vision_seeds" / "camera" / "frame_latest.png",
        _STATE_DIR / "vision_snapshots" / "sight_latest.jpg",
    ):
        try:
            stale_path.unlink(missing_ok=True)
        except Exception:
            pass


def _release_surface_camera(systems: Dict[str, Any]) -> None:
    hardware = systems.get("hardware")
    camera = getattr(hardware, "camera", None) if hardware is not None else None
    if camera is None:
        return
    try:
        if getattr(camera, "running", False) or getattr(camera, "cap", None) is not None:
            camera.close()
    except Exception:
        pass


def _write_surface_snapshot(systems: Dict[str, Any], *, trigger: str, flagged: bool = False, reason: str = "") -> Dict[str, Any]:
    sc = _surface_sensory_owner(systems)
    state = {}
    if sc is not None and hasattr(sc, "get_state"):
        try:
            state = dict(sc.get_state() or {})
        except Exception:
            state = {}
    if not state:
        try:
            persisted = json.loads((_STATE_DIR / "sensory_crystal_state.json").read_text())
            if isinstance(persisted, dict):
                state = persisted
        except Exception:
            state = {}
    details = _surface_present_sensory_details(systems)
    previous_snapshot = read_surface_snapshot(_STATE_DIR)
    camera_live = _surface_camera_live()
    pending_visual_question, visual_uncertainty_streak = _derive_surface_visual_question(
        visual_description=str(details.get("visual_description", "") or ""),
        concepts_active=[str(item) for item in list(details.get("concepts_active") or []) if str(item).strip()],
        sensory_state=state,
        camera_live=camera_live,
        previous_snapshot=previous_snapshot,
    )
    return write_surface_snapshot(
        _STATE_DIR,
        state,
        mic_live=_surface_mic_live(systems),
        camera_live=camera_live,
        sensory_vectors=_surface_sensory_vectors(systems),
        sensory_context=dict(details.get("sensory_context") or {}),
        visual_description=str(details.get("visual_description", "") or ""),
        audio_description=str(details.get("audio_description", "") or ""),
        recent_speech=str(details.get("recent_speech", "") or ""),
        latest_guidance=dict(details.get("latest_guidance") or {}),
        guidance_summary=str(details.get("guidance_summary", "") or ""),
        pending_visual_question=pending_visual_question,
        visual_uncertainty_streak=visual_uncertainty_streak,
        concepts_active=list(details.get("concepts_active") or []),
        trigger=trigger,
        flagged=flagged,
        reason=reason,
    )


def _infer_surface_wrong_signal(
    snapshot: Dict[str, Any],
    projection: Dict[str, Any],
    *,
    user_text: str = "",
) -> tuple[bool, str]:
    frame = dict(snapshot.get("conscious_frame") or {}) if isinstance(snapshot, dict) else {}
    root_thought = dict(frame.get("root_thought") or {})
    reactive_signal = dict(frame.get("reactive_signal") or {})
    prediction = dict(frame.get("prediction") or {})
    unresolved = [str(item) for item in (frame.get("unresolved_conflicts") or []) if str(item)]
    stance = str(frame.get("stance", "") or "")
    action = str(frame.get("selected_action", "") or "")
    mismatch = float(prediction.get("mismatch", 0.0) or 0.0)
    effects = [str(item).strip() for item in (projection.get("active_effects") or []) if str(item).strip()]

    reasons = []
    if mismatch >= 0.42:
        reasons.append("prediction mismatch is elevated")
    if unresolved:
        reasons.append(unresolved[0].replace("_", " "))
    if action in {"clarify", "re-evaluate", "wait", "slow_down"}:
        reasons.append(f"surface wants to {action.replace('_', ' ')}")
    if stance in {"careful_clarification", "reframe", "hold_for_coherence", "cautious_load_management"}:
        reasons.append(stance.replace("_", " "))
    if any(("feels off" in item.lower()) or ("wrong" in item.lower()) or ("repair" in item.lower()) for item in effects):
        reasons.append(effects[0])
    if bool(reactive_signal.get("active", False)) and float(reactive_signal.get("intensity", 0.0) or 0.0) >= 0.55:
        reasons.append(str(reactive_signal.get("reason", "") or "surface is in reactive caution"))
    if root_thought.get("primary_tension"):
        reasons.append(str(root_thought.get("primary_tension", "") or ""))

    text_low = str(user_text or "").lower()
    if any(phrase in text_low for phrase in ("feels wrong", "something is off", "not right", "this seems wrong", "repair this")):
        reasons.append("user surfaced a wrong-feeling moment")

    reasons = [item for idx, item in enumerate(reasons) if item and item not in reasons[:idx]]
    return (bool(reasons), "; ".join(reasons[:2])[:220])


def _compose_surface_stream(snapshot: Dict[str, Any], projection: Dict[str, Any]) -> tuple[Dict[str, Any], str, Dict[str, Any]]:
    frame = dict(snapshot.get("conscious_frame") or {}) if isinstance(snapshot, dict) else {}
    root_thought = dict(frame.get("root_thought") or {})
    reactive_signal = dict(frame.get("reactive_signal") or {})
    processing_mode = str(frame.get("processing_mode", "") or root_thought.get("mode", "") or "deliberative")

    interpretation = str(frame.get("interpretation", "") or "")
    guidance = str(projection.get("surface_guidance", "") or "")
    input_anchor = str(root_thought.get("input_anchor", "") or "")

    if not root_thought:
        root_thought = {
            "summary": guidance or interpretation or "Surface is holding the present converged frame.",
            "seed": guidance or interpretation or "",
            "input_anchor": input_anchor,
            "mode": processing_mode,
            "comparison_channels": ["incoming_input", "subsurface_stream", "present_sensory"],
        }
    else:
        root_thought["summary"] = str(root_thought.get("summary", "") or guidance or interpretation or "")
        root_thought["comparison_channels"] = list(root_thought.get("comparison_channels") or ["incoming_input", "subsurface_stream", "present_sensory"])

    if not reactive_signal:
        reactive_signal = {
            "active": processing_mode in {"reactive", "blended"},
            "intensity": 0.0,
            "reason": "",
        }

    return root_thought, processing_mode, reactive_signal


def _log(message: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {message}"
    print(line, flush=True)
    try:
        with _LOG_FILE.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except Exception:
        pass


def _read_json(path: Path, default: Any) -> Any:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return default


def _write_json(path: Path, payload: Any) -> None:
    import os as _os
    tmp = path.with_suffix(path.suffix + f".{_os.getpid()}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(path)
    except Exception:
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass
        raise


def _queue_state() -> Dict[str, Any]:
    data = _read_json(_QUEUE_FILE, {"pending": []})
    return data if isinstance(data, dict) else {"pending": []}


def _next_turn() -> Optional[Dict[str, Any]]:
    state = _queue_state()
    pending = list(state.get("pending") or [])
    for item in pending:
        if str(item.get("status", "queued") or "queued") != "queued":
            continue
        item["status"] = "processing"
        item["started_at"] = time.time()
        _write_json(_QUEUE_FILE, state)
        return dict(item)
    return None


def _finish_turn(turn_id: str, *, result: Dict[str, Any]) -> None:
    state = _queue_state()
    pending = []
    for item in list(state.get("pending") or []):
        if str(item.get("id", "")) == str(turn_id):
            continue
        pending.append(item)
    state["pending"] = pending
    state["last_completed"] = {
        "id": str(turn_id),
        "completed_at": time.time(),
        "status": str(result.get("status", "ok") or "ok"),
    }
    _write_json(_QUEUE_FILE, state)
    _write_json(_RESULT_FILE, result)


def _build_status(*, state_name: str, active_turn: Optional[Dict[str, Any]] = None, last_error: str = "") -> Dict[str, Any]:
    snapshot = _read_json(_SNAPSHOT_FILE, {})
    frame = dict(snapshot.get("conscious_frame") or {}) if isinstance(snapshot, dict) else {}
    projection = _read_json(_PROJECTION_FILE, {})
    last_result = _read_json(_RESULT_FILE, {})
    sensory_snapshot = read_surface_snapshot(_STATE_DIR)
    present_sensory = present_sensory_perspective_from_snapshot(sensory_snapshot)
    root_thought, processing_mode, reactive_signal = _compose_surface_stream(snapshot, projection)
    feels_wrong, wrong_reason = _infer_surface_wrong_signal(snapshot, projection)
    queue_state = _queue_state()
    pending = list(queue_state.get("pending") or [])
    return {
        "updated_at": time.time(),
        "updated": time.strftime("%H:%M:%S"),
        "runtime_profile": "surface",
        "stratum_role": "surface",
        "state": state_name,
        "queue_depth": len(pending),
        "active_turn_id": str((active_turn or {}).get("id", "") or ""),
        "frame_name": str(frame.get("frame_name", "") or ""),
        "stance": str(frame.get("stance", "") or ""),
        "selected_action": str(frame.get("selected_action", "") or ""),
        "should_speak": bool(frame.get("should_speak", False)),
        "readiness": float(frame.get("readiness", 0.0) or 0.0),
        "coherence": float(frame.get("coherence", 0.0) or 0.0),
        "processing_mode": processing_mode,
        "root_thought": root_thought,
        "reactive_signal": reactive_signal,
        "dominant_axis": str(frame.get("dominant_axis") or projection.get("dominant_axis_hint", "") or ""),
        "present_sensory_perspective": present_sensory,
        "surface_guidance": str(projection.get("surface_guidance", "") or ""),
        "surface_feels_wrong": feels_wrong,
        "surface_feels_wrong_reason": wrong_reason,
        "active_effects": list(projection.get("active_effects") or [])[:4],
        "noncomp_input": dict(last_result.get("noncomp_input") or {}),
        "noncomp_output": dict(last_result.get("noncomp_output") or {}),
        "poedex_prefetch": dict(last_result.get("poedex_prefetch") or {}),
        "last_error": last_error,
    }


def _result_payload(turn: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    resp = result.get("resp_A")
    snapshot = _read_json(_SNAPSHOT_FILE, {})
    projection = _read_json(_PROJECTION_FILE, {})
    sensory_snapshot = read_surface_snapshot(_STATE_DIR)
    root_thought, processing_mode, reactive_signal = _compose_surface_stream(snapshot, projection)
    feels_wrong, wrong_reason = _infer_surface_wrong_signal(
        snapshot,
        projection,
        user_text=str(turn.get("content", "") or ""),
    )
    return {
        "status": "ok",
        "id": str(turn.get("id", "") or ""),
        "source": str(turn.get("source", "surface_queue") or "surface_queue"),
        "processed_at": time.time(),
        "input": str(turn.get("content", "") or ""),
        "response_text": str(getattr(resp, "content", "") or ""),
        "response_tone": str(getattr(resp, "emotional_tone", "attentive") or "attentive"),
        "response_confidence": float(getattr(resp, "confidence", 0.0) or 0.0),
        "response_source": str(getattr(resp, "src", "") or ""),
        "runtime_contract": dict(result.get("runtime_contract") or {}),
        "conscious_frame": dict((snapshot or {}).get("conscious_frame") or {}),
        "root_thought": root_thought,
        "processing_mode": processing_mode,
        "reactive_signal": reactive_signal,
        "present_sensory_perspective": present_sensory_perspective_from_snapshot(sensory_snapshot),
        "surface_guidance": str(projection.get("surface_guidance", "") or ""),
        "surface_feels_wrong": feels_wrong,
        "surface_feels_wrong_reason": wrong_reason,
        "noncomp_input": dict(result.get("noncomp_input") or {}),
        "noncomp_output": dict(result.get("noncomp_output") or {}),
        "poedex_prefetch": dict(result.get("poedex_prefetch") or {}),
        "poedex_learning": dict(result.get("poedex_learning") or {}),
        "current_turn_answer_seek": dict(result.get("current_turn_answer_seek") or {}),
        "question_alignment_audit": dict(result.get("question_alignment_audit") or {}),
    }


def _emit_continuity_packet(turn: Dict[str, Any], payload: Dict[str, Any], snapshot: Dict[str, Any]) -> None:
    """
    After each Surface turn completes, hand present experience down to Subsurface.

    This is the architectural handoff: Surface gathered the present moment —
    now Subsurface must receive it so the organism actually absorbs what happened,
    rather than Surface being theatrical and the moment evaporating.
    """
    try:
        frame = dict(snapshot.get("conscious_frame") or {}) if isinstance(snapshot, dict) else {}
        unresolved = [str(item) for item in list(frame.get("unresolved_conflicts") or []) if str(item).strip()]
        root_thought = dict(frame.get("root_thought") or {})
        resolved_bindings: list = []
        resolved_raw = root_thought.get("resolved_bindings") or frame.get("resolved_bindings") or []
        for item in list(resolved_raw or []):
            s = str(item).strip()
            if s:
                resolved_bindings.append(s)

        sensory_snap = read_surface_snapshot(_STATE_DIR)
        concepts = list(payload.get("conscious_frame", {}).get("salient_hypotheses") or [])
        concept_labels = [
            str(c.get("label", "") or c.get("concept", "") or c).strip()
            for c in concepts
            if isinstance(c, dict) or str(c).strip()
        ]
        concept_labels = [c for c in concept_labels if c][:12]
        if not concept_labels:
            concept_labels = list(sensory_snap.get("concepts_active") or [])[:8]

        write_continuity_packet(
            _STATE_DIR,
            user_input=str(turn.get("content", "") or ""),
            aurora_response=str(payload.get("response_text", "") or ""),
            response_tone=str(payload.get("response_tone", "attentive") or "attentive"),
            concepts_activated=concept_labels,
            visual_description=str(sensory_snap.get("visual_description", "") or ""),
            audio_description=str(sensory_snap.get("audio_description", "") or ""),
            recent_speech=str(sensory_snap.get("recent_speech", "") or ""),
            dominant_axis=str(payload.get("conscious_frame", {}).get("dominant_axis", "") or ""),
            coherence=float(payload.get("conscious_frame", {}).get("coherence", 0.0) or 0.0),
            felt_wrong=bool(payload.get("surface_feels_wrong", False)),
            wrong_reason=str(payload.get("surface_feels_wrong_reason", "") or ""),
            unresolved_tensions=unresolved,
            resolved_bindings=resolved_bindings,
            source=str(turn.get("source", "surface_turn") or "surface_turn"),
        )
    except Exception:
        pass


def run() -> None:
    _STATE_DIR.mkdir(exist_ok=True)
    _log("Booting Aurora surface daemon...")

    systems = boot_aurora(
        state_dir=str(_STATE_DIR),
        verbose=False,
        use_quasiarch=False,
        runtime_profile="surface",
    )

    shutdown = False

    def _handle_signal(sig, _frame) -> None:
        nonlocal shutdown
        _log(f"Shutdown signal received ({sig}).")
        shutdown = True

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    # Surface owns the live sensory feed.
    _sc_boot = systems.get("sensory_crystal")
    if _sc_boot is not None and hasattr(_sc_boot, "start_session"):
        try:
            _sc_boot.start_session(f"surface_{int(time.time())}")
            _log("Surface sensory session started.")
        except Exception as exc:
            _log(f"Surface sensory session start failed: {exc}")

    _sie_boot = systems.get("sensory_integration")
    if _sie_boot is not None and hasattr(_sie_boot, "start_listening"):
        try:
            if getattr(_sie_boot, "sensory_crystal", None) is None:
                _sie_boot.sensory_crystal = systems.get("sensory_crystal")
            if getattr(_sie_boot, "hardware", None) is None:
                _sie_boot.hardware = systems.get("hardware")
            if _sie_boot.start_listening():
                _log("Surface mic listener started.")
            else:
                _log("Surface mic listener unavailable.")
        except Exception as exc:
            _log(f"Surface mic listener start failed: {exc}")

    _hw_boot = systems.get("hardware")
    if _hw_boot is not None and hasattr(_hw_boot, "start"):
        try:
            if hasattr(_hw_boot, "on_visual_frame"):
                def _surface_camera_frame_hook(frame: Any, _features: Any) -> None:
                    _write_latest_camera_frame(frame)

                _hw_boot.on_visual_frame = _surface_camera_frame_hook
            _hw_boot.start()
            _caps = _hw_boot.get_capabilities() if hasattr(_hw_boot, "get_capabilities") else {}
            _log(
                "Surface hardware started "
                f"(camera={'on' if _caps.get('camera') else 'off'}, "
                f"mic={'on' if _caps.get('microphone_raw') or _caps.get('microphone_speech') else 'off'})."
            )
        except Exception as exc:
            _log(f"Surface hardware start failed: {exc}")

    def _camera_capture_loop() -> None:
        integration = systems.get("sensory_integration")
        perception = systems.get("perception")
        hardware = systems.get("hardware")
        if (
            (integration is None or not hasattr(integration, "see")) and
            perception is None and
            (hardware is None or not hasattr(hardware, "capture_visual"))
        ):
            return
        last_error = ""
        empty_reads = 0
        last_enabled = None
        while not shutdown:
            camera_is_enabled = sensory_camera_enabled(_STATE_DIR)
            if camera_is_enabled != last_enabled:
                if not camera_is_enabled:
                    _release_surface_camera(systems)
                    _clear_camera_frame_cache()
                    _log("Surface camera disabled by control toggle.")
                elif last_enabled is not None:
                    _log("Surface camera enabled by control toggle.")
                last_enabled = camera_is_enabled
            if not camera_is_enabled:
                time.sleep(1.0)
                continue
            try:
                visual = None
                desc = ""
                if hardware is not None and hasattr(hardware, "capture_visual"):
                    visual = hardware.capture_visual()
                    desc = "hardware capture"
                    if isinstance(visual, str) and visual:
                        src = Path(visual)
                        if src.exists():
                            _write_latest_camera_path(src)
                    elif isinstance(visual, dict) and str(visual.get("image_path", "") or ""):
                        src = Path(str(visual.get("image_path", "") or ""))
                        if src.exists():
                            _write_latest_camera_path(src)
                    elif visual is not None and hasattr(hardware, "process_visual"):
                        try:
                            from foundational_contract import ExistenceMode
                            mode = ExistenceMode.BOUNDED
                        except Exception:
                            mode = getattr(hardware, "default_mode", None)
                        if mode is not None:
                            hardware.process_visual(_normalize_visual_payload(visual), mode)
                elif integration is not None and hasattr(integration, "see"):
                    desc, visual = integration.see()
                elif perception is not None and hasattr(perception, "see"):
                    desc, visual = perception.see()

                if visual:
                    empty_reads = 0
                else:
                    empty_reads += 1
                    if empty_reads in (1, 5, 15):
                        _log(f"Surface camera read empty ({desc or 'hardware returned no frame'})")
            except Exception as exc:
                msg = str(exc) or exc.__class__.__name__
                if msg != last_error:
                    tb = traceback.format_exc()
                    _log(f"Surface camera loop error: {msg}")
                    _log(tb.strip())
                    last_error = msg
            time.sleep(6.0)

    camera_thread = threading.Thread(target=_camera_capture_loop, daemon=True, name="surface-sensory-camera")
    camera_thread.start()

    # Surface owns live conversational input: wake-word / push-to-talk / ambient.
    voice_listener = _start_voice_listener(systems, log_fn=_log)
    _start_ambient_response_listener(systems, log_fn=_log)

    next_snapshot = 0.0

    while not shutdown:
        now = time.time()

        # Dormancy check — Subsurface owns the sleep/wake clock.
        # User turns are allowed to wake Surface; otherwise queued mobile input
        # can sit forever while the mobile runner times out.
        try:
            from aurora_internal.dual_strata.sleep_cycle import exit_sleep, is_sleeping
            if is_sleeping(_STATE_DIR):
                queue_state = _queue_state()
                pending_turns = [
                    item for item in list(queue_state.get("pending") or [])
                    if str(item.get("status", "queued") or "queued") == "queued"
                ]
                if pending_turns:
                    exit_sleep(_STATE_DIR)
                    _log("Surface woke for queued user turn.")
                else:
                    _write_json(_STATUS_FILE, _build_status(state_name="sleeping"))
                    time.sleep(5.0)
                    continue
        except Exception:
            pass

        if now >= next_snapshot:
            _write_surface_snapshot(systems, trigger="interval")
            next_snapshot = now + 5.0

        turn = _next_turn()
        if turn is None:
            _write_json(_STATUS_FILE, _build_status(state_name="idle"))
            time.sleep(1.0)
            continue

        _write_json(_STATUS_FILE, _build_status(state_name="processing", active_turn=turn))
        try:
            systems["_subsurface_projection"] = _read_json(_PROJECTION_FILE, {})

            # L3.5 — SediMemory surface recall (read-only; surface never ticks or ingests)
            _sedi = systems.get("sedimemory")
            if _sedi is not None:
                try:
                    from aurora_constraint_engine import ConstraintVector
                    _surface_cv = ConstraintVector(X=0.8, T=0.4, N=0.2, B=0.1, A=0.05)
                    systems["_sedi_surface_frags"] = _sedi.surface_recall(_surface_cv, max_results=16)
                except Exception:
                    systems["_sedi_surface_frags"] = []

            result = process_external_user_turn(
                systems,
                str(turn.get("content", "") or ""),
                source_label=str(turn.get("source", "surface_queue") or "surface_queue"),
                session_id=str(turn.get("session_id", "surface_daemon") or "surface_daemon"),
                auto_search_enabled=bool(turn.get("auto_search_enabled", True)),
                record_exchange=bool(turn.get("record_exchange", True)),
                update_interactive_state=bool(turn.get("update_interactive_state", True)),
                track_evolutionary_trace=bool(turn.get("track_evolutionary_trace", True)),
                run_periodic_maintenance=bool(turn.get("run_periodic_maintenance", True)),
                mode_name=str(turn.get("mode_name", "BOUNDED") or "BOUNDED"),
            )
            payload = _result_payload(turn, result)
            snapshot = _read_json(_SNAPSHOT_FILE, {})
            _write_surface_snapshot(
                systems,
                trigger="surface_turn",
                flagged=bool(payload.get("surface_feels_wrong", False)),
                reason=str(payload.get("surface_feels_wrong_reason", "") or payload.get("input", "") or "surface_turn")[:220],
            )
            # Hand present experience down to Subsurface — the continuity handoff.
            # Without this, each awake moment is theatrical: seen and spoken but
            # not absorbed into the organism.
            _emit_continuity_packet(turn, payload, snapshot)
            _finish_turn(str(turn.get("id", "") or ""), result=payload)
            _write_json(_STATUS_FILE, _build_status(state_name="idle"))
        except Exception as exc:
            payload = {
                "status": "error",
                "id": str(turn.get("id", "") or ""),
                "processed_at": time.time(),
                "input": str(turn.get("content", "") or ""),
                "error": str(exc),
            }
            _finish_turn(str(turn.get("id", "") or ""), result=payload)
            _write_json(_STATUS_FILE, _build_status(state_name="idle", last_error=str(exc)))
            _log(f"Surface turn failed: {exc}")

    if voice_listener:
        try:
            voice_listener.stop()
        except Exception:
            pass
    _write_json(_STATUS_FILE, _build_status(state_name="stopped"))
    _log("Aurora surface daemon stopped.")


if __name__ == "__main__":
    run()

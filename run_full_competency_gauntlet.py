#!/usr/bin/env python3
"""
Run Aurora's full competency gauntlet against the live local stack.

This wrapper stays inside the aurora_strata runtime and exercises the
available manifold-native systems directly:
  - visual perception
  - audio/speech perception
  - intent and meaning bridging through the canonical response path
  - dream consolidation

If an environment limitation blocks a modality (for example OpenCV-backed
image loading), the report makes that explicit and continues with the rest of
the stack instead of silently pretending the modality passed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from aurora import boot_aurora, process_external_user_turn
from aurora_expression_perception import SensoryEvent, SensoryEventType
from corpus_runner import simulation_burst


REPO_ROOT = Path(__file__).resolve().parent
STATE_DIR = REPO_ROOT / "aurora_state"
REPORT_PATH = STATE_DIR / "last_full_competency_gauntlet.json"


def _json_safe(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except Exception:
        if isinstance(value, dict):
            return {str(k): _json_safe(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [_json_safe(v) for v in value]
        return str(value)


def _snapshot(systems: Dict[str, Any]) -> Dict[str, Any]:
    sensory = systems.get("sensory")
    integration = systems.get("sensory_integration")
    dream_trainer = systems.get("dream_trainer")

    stats = {}
    if integration is not None:
        stats = dict(getattr(integration, "stats", {}) or {})

    top_fails: List[Dict[str, Any]] = []
    if dream_trainer is not None and hasattr(dream_trainer, "ledger"):
        try:
            for dim, score in list(dream_trainer.ledger.get_top_fails(5) or []):
                top_fails.append({"dimension": str(dim), "score": float(score)})
        except Exception:
            top_fails = []

    visual_competency = {}
    audio_competency = {}
    visual_concepts = 0
    audio_concepts = 0
    if sensory is not None:
        try:
            visual_competency = dict(sensory.get_visual_competency() or {})
        except Exception:
            visual_competency = {}
        try:
            audio_competency = dict(sensory.get_audio_competency() or {})
        except Exception:
            audio_competency = {}
        try:
            visual_concepts = len(getattr(getattr(sensory, "visual_concepts", None), "concepts", {}) or {})
        except Exception:
            visual_concepts = 0
        try:
            audio_concepts = len(getattr(getattr(sensory, "audio_concepts", None), "concepts", {}) or {})
        except Exception:
            audio_concepts = 0

    return {
        "integration_stats": stats,
        "visual_competency": visual_competency,
        "audio_competency": audio_competency,
        "visual_concepts": visual_concepts,
        "audio_concepts": audio_concepts,
        "top_fails": top_fails,
    }


def _delta(before: Dict[str, Any], after: Dict[str, Any], section: str) -> Dict[str, Any]:
    before_map = dict(before.get(section, {}) or {})
    after_map = dict(after.get(section, {}) or {})
    keys = sorted(set(before_map) | set(after_map))
    return {
        key: round(float(after_map.get(key, 0.0)) - float(before_map.get(key, 0.0)), 6)
        for key in keys
    }


def _build_language_probes(top_fail_dims: List[str]) -> List[str]:
    probes = [
        "I need help organizing the work in front of me.",
        "That is not what I meant, let me clarify the intent.",
        "Can you tell me what you are noticing right now through vision and audio?",
    ]

    targeted = {
        "semantic_precision": "I do not need a broad answer, I need the exact point I am reaching for.",
        "context_carryover": "Keep the earlier request in mind and only change one thing: make it tomorrow.",
        "multi_turn_stability": "I am still talking about the same plan as before, not a new topic.",
        "contradiction_handling": "I said yes out loud, but I do not actually agree with it.",
        "implied_intent_inference": "I am not asking for facts yet, I am trying to find the shape of the problem.",
        "ambiguity_handling": "It is about the thing we were already talking about, not the other one.",
    }
    for dim in top_fail_dims:
        probe = targeted.get(str(dim))
        if probe and probe not in probes:
            probes.append(probe)
    return probes[:6]


def _run_visual_pass(systems: Dict[str, Any]) -> Dict[str, Any]:
    integration = systems.get("sensory_integration")
    if integration is None:
        return {"status": "unavailable", "reason": "sensory_integration missing", "image_results": [], "synthetic_results": []}

    image_candidates = [
        STATE_DIR / "vision_seeds" / "concepts" / "aurora.jpg",
        STATE_DIR / "vision_seeds" / "concepts" / "ocean.jpg",
        STATE_DIR / "vision_seeds" / "concepts" / "water.jpg",
        STATE_DIR / "vision_seeds" / "concepts" / "present.jpg",
        STATE_DIR / "vision_snapshots" / "sight_latest.jpg",
    ]

    image_results: List[Dict[str, Any]] = []
    image_grounding_available = False
    for path in image_candidates:
        if not path.exists():
            continue
        description, data = integration.see_image(str(path))
        entry = {
            "path": str(path),
            "description": description,
            "loaded": bool(data),
            "concepts": list((data or {}).get("guided_labels", {}) or []),
        }
        if data:
            image_grounding_available = True
        if not data and "OpenCV not available" in str(description):
            entry["blocker"] = "opencv_unavailable"
        image_results.append(entry)
        if len(image_results) >= 4:
            break

    synthetic_inputs = [
        {
            "brightness": 0.62,
            "motion_detected": False,
            "faces": [],
            "features": {
                "edge_density": 0.18,
                "red_mean": 0.43,
                "blue_mean": 0.39,
                "object_labels": ["screen", "desk", "notebook"],
                "person_detected": 0.0,
            },
        },
        {
            "brightness": 0.55,
            "motion_detected": True,
            "faces": [{"x": 240, "y": 120, "w": 90, "h": 90}],
            "features": {
                "motion_intensity": 0.22,
                "edge_density": 0.29,
                "red_mean": 0.34,
                "blue_mean": 0.58,
                "object_labels": ["person", "room"],
                "person_detected": 1.0,
            },
        },
    ]

    synthetic_results: List[Dict[str, Any]] = []
    for idx, visual_data in enumerate(synthetic_inputs, start=1):
        event = SensoryEvent(
            event_type=SensoryEventType.VISUAL_FRAME,
            data=dict(visual_data),
        )
        integration._process_event(event)
        synthetic_results.append(
            {
                "probe": f"synthetic_visual_{idx}",
                "description": event.linguistic_description,
                "concepts_activated": list(event.concepts_activated),
            }
        )

    status = "ok" if image_grounding_available else "partial"
    reason = "image_grounding_active" if image_grounding_available else "image_loader_blocked_or_unavailable"
    return {
        "status": status,
        "reason": reason,
        "image_results": image_results,
        "synthetic_results": synthetic_results,
    }


def _run_audio_intent_pass(systems: Dict[str, Any], probes: List[str]) -> List[Dict[str, Any]]:
    integration = systems.get("sensory_integration")
    aurora_gateway = systems.get("aurora")
    results: List[Dict[str, Any]] = []
    if integration is None:
        return results

    for idx, text in enumerate(probes, start=1):
        event = SensoryEvent(
            event_type=SensoryEventType.AUDIO_SPEECH,
            data={
                "transcription": text,
                "category": "speech",
                "volume": 0.68,
                "voice_detected": True,
                "pitch": 0.46,
                "features": {
                    "vad_ratio": 0.53,
                    "spectral_centroid": 0.44,
                    "spectral_bandwidth": 0.37,
                    "harmonicity": 0.61,
                    "onset_density": 0.32,
                },
            },
        )
        integration._process_event(event)
        processed = dict(event.data.get("processed_speech") or {})
        response = dict(
            process_external_user_turn(
                systems,
                text,
                source_label=f"competency_gauntlet_probe_{idx}",
                session_id="full_competency_gauntlet",
                run_periodic_maintenance=False,
            )
            or {}
        )
        response_text = str(response.get("response_text") or "").strip()
        response_src = str(response.get("response_src") or "").strip()
        if not response_text and aurora_gateway is not None and hasattr(aurora_gateway, "speak_to_aurora"):
            try:
                gateway_response = aurora_gateway.speak_to_aurora(text)
                response_text = str(getattr(gateway_response, "content", "") or "").strip()
                response_src = response_src or "gateway_fallback"
            except Exception as exc:
                response_src = response_src or f"gateway_error:{exc.__class__.__name__}"
        results.append(
            {
                "input": text,
                "description": event.linguistic_description,
                "processed_speech": processed,
                "response_text": response_text,
                "response_src": response_src,
            }
        )
    return results


def run_gauntlet(episodes: int = 5, verbose: bool = True) -> Dict[str, Any]:
    systems = boot_aurora(verbose=verbose, runtime_profile="surface")
    before = _snapshot(systems)
    top_fail_dims = [row["dimension"] for row in before.get("top_fails", [])]

    visual_report = _run_visual_pass(systems)
    language_probes = _build_language_probes(top_fail_dims)
    audio_language_report = _run_audio_intent_pass(systems, language_probes)
    dream_report = simulation_burst(systems, episodes=episodes, verbose=verbose)
    after = _snapshot(systems)

    report = {
        "runtime_profile": "surface",
        "visual": visual_report,
        "audio_language": audio_language_report,
        "dream_burst": _json_safe(dream_report),
        "before": before,
        "after": after,
        "deltas": {
            "integration_stats": _delta(before, after, "integration_stats"),
            "visual_competency": _delta(before, after, "visual_competency"),
            "audio_competency": _delta(before, after, "audio_competency"),
            "visual_concepts": after.get("visual_concepts", 0) - before.get("visual_concepts", 0),
            "audio_concepts": after.get("audio_concepts", 0) - before.get("audio_concepts", 0),
        },
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Aurora's local full competency gauntlet.")
    parser.add_argument("--episodes", type=int, default=5, help="Base dream burst episode count.")
    parser.add_argument("--quiet", action="store_true", help="Reduce boot and burst logging.")
    args = parser.parse_args()

    report = run_gauntlet(episodes=max(1, int(args.episodes or 5)), verbose=not args.quiet)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(_json_safe(report), indent=2), encoding="utf-8")
    print(json.dumps(_json_safe(report), indent=2))
    print(f"\n[REPORT] wrote {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List

# How long dream fields stay in the projection before they expire (seconds).
# Dream cycle runs every ~6h so 8h gives comfortable coverage.
_DREAM_CARRY_WINDOW_S: float = 8 * 3600.0


def _clip01(value: Any, default: float = 0.0) -> float:
    try:
        return max(0.0, min(1.0, float(value or 0.0)))
    except Exception:
        return max(0.0, min(1.0, float(default or 0.0)))


def _dominant_axis(axis_orientation: Dict[str, Any], runtime_axes: Dict[str, Any]) -> str:
    merged: Dict[str, float] = {}
    for axis in ("X", "T", "N", "B", "A"):
        merged[axis] = max(
            abs(float(axis_orientation.get(axis, 0.0) or 0.0)),
            float(runtime_axes.get(axis, 0.0) or 0.0),
        )
    return max(merged, key=merged.get) if merged else "X"


def _pressure_coloring(issue: str, dominant_axis: str) -> Dict[str, Any]:
    issue_low = str(issue or "").lower()

    if any(token in issue_low for token in ("memory", "callback", "continuity", "recall", "context")):
        return {
            "effect": "continuity feels snagged and keeps pulling for review",
            "guidance": "Surface should stay aware of contextual drag while subsurface traces the continuity fault.",
            "signal": {"label": "contextualize", "summary": "The unease is continuity-shaped; keep context in view instead of rushing past it."},
        }
    if any(token in issue_low for token in ("semantic", "boundary", "meaning", "contract", "comprehension", "clarify")):
        return {
            "effect": "meaning edges feel blurry and need cleaner boundaries",
            "guidance": "Surface should feel careful around interpretation while subsurface sharpens the boundary problem.",
            "signal": {"label": "clarify", "summary": "The unease is boundary-shaped; clarify before committing hard to meaning."},
        }
    if any(token in issue_low for token in ("audio", "visual", "sensory", "camera", "mic", "voice", "vision")):
        return {
            "effect": "attention keeps returning to a sensory irregularity",
            "guidance": "Surface should stay perceptually alert while subsurface checks what the live feed may have missed.",
            "signal": {"label": "attend", "summary": "The unease is sensory-shaped; keep perceptual attention open and current."},
        }
    if any(token in issue_low for token in ("memory_floor", "runtime", "governor", "load", "disk", "overhead", "cpu")):
        return {
            "effect": "the system feels strained and wants a lighter pace",
            "guidance": "Surface should feel economical and unhurried while subsurface manages the strain source.",
            "signal": {"label": "slow_down", "summary": "The unease is load-shaped; conserve effort while the lower layer remedies it."},
        }
    if any(token in issue_low for token in ("affect", "emotion", "fear", "hurt", "comfort", "anxious")):
        return {
            "effect": "the pressure lands with emotional tenderness and caution",
            "guidance": "Surface should stay gentle and emotionally careful while subsurface works the source.",
            "signal": {"label": "comfort", "summary": "The unease is affect-shaped; respond with care, not blunt force."},
        }

    axis_defaults = {
        "X": {
            "effect": "something about the present structure feels misaligned",
            "guidance": "Surface should stay grounded in what is actually present while subsurface checks structural fit.",
            "signal": {"label": "attend", "summary": "The unease is structural; stay anchored in what is concretely there."},
        },
        "T": {
            "effect": "time continuity feels slightly off",
            "guidance": "Surface should keep temporal context alive while subsurface resolves the drift.",
            "signal": {"label": "contextualize", "summary": "The unease is temporal; preserve continuity while it is being repaired."},
        },
        "N": {
            "effect": "resource and effort pressure make the moment feel heavier",
            "guidance": "Surface should stay lighter and more economical while subsurface reduces the load.",
            "signal": {"label": "slow_down", "summary": "The unease is energetic; keep the present frame light."},
        },
        "B": {
            "effect": "the meaning boundary feels uncertain",
            "guidance": "Surface should stay careful with interpretation while subsurface resolves the ambiguity.",
            "signal": {"label": "clarify", "summary": "The unease is interpretive; let clarity catch up before overcommitting."},
        },
        "A": {
            "effect": "agency and feeling pressure make the moment feel tender",
            "guidance": "Surface should stay responsive and emotionally attuned while subsurface resolves the pressure source.",
            "signal": {"label": "comfort", "summary": "The unease is affective; respond with attunement."},
        },
    }
    return dict(axis_defaults.get(dominant_axis, axis_defaults["X"]))


def _carry_dream_fields(projection_path: Path | None) -> Dict[str, Any]:
    """
    Read the existing projection file and carry forward dream fields
    if they were written recently (within _DREAM_CARRY_WINDOW_S).
    Returns only the fields to merge — empty dict if nothing to carry.
    """
    if projection_path is None or not projection_path.exists():
        return {}
    try:
        existing = json.loads(projection_path.read_text())
    except Exception:
        return {}
    completed_at = float(existing.get("dream_completed_at") or 0.0)
    if completed_at <= 0.0:
        return {}
    if (time.time() - completed_at) > _DREAM_CARRY_WINDOW_S:
        return {}
    return {
        "dream_completed": bool(existing.get("dream_completed", False)),
        "dream_completed_at": completed_at,
        "dream_insights": str(existing.get("dream_insights", "") or ""),
        "oets_growth": int(existing.get("oets_growth", 0) or 0),
    }


def build_subsurface_projection(
    daemon_status: Dict[str, Any],
    *,
    relief_plan: Dict[str, Any] | None = None,
    projection_path: Path | None = None,
) -> Dict[str, Any]:
    daemon_status = dict(daemon_status or {})
    relief_plan = dict(relief_plan or {})

    axis_orientation = dict(daemon_status.get("axis_orientation") or {})
    runtime_axes = dict(daemon_status.get("runtime_governor_axes") or {})
    host = dict(daemon_status.get("runtime_host") or {})
    dominant_axis = _dominant_axis(axis_orientation, runtime_axes)
    governor_mode = str(daemon_status.get("runtime_governor_mode", "") or "balanced")
    try:
        qao_events = int(daemon_status.get("qao_recent_events", 0) or 0)
    except Exception:
        qao_events = 0
    qao_issue = str(daemon_status.get("qao_top_issue", "") or "").replace("_", " ")
    blocked = list(daemon_status.get("runtime_recent_blocked") or [])
    surface_snapshot_flagged = bool(daemon_status.get("surface_snapshot_flagged", False))
    surface_snapshot_reason = str(daemon_status.get("surface_snapshot_reason", "") or "")
    surface_snapshot_summary = str(daemon_status.get("surface_snapshot_summary", "") or "")
    surface_snapshot_trigger = str(daemon_status.get("surface_snapshot_trigger", "") or "")
    repair_phase = str(daemon_status.get("subsurface_repair_phase", "") or "")
    repair_issue = str(daemon_status.get("subsurface_repair_issue", "") or "").replace("_", " ")
    repair_reason = str(daemon_status.get("subsurface_repair_reason", "") or "")
    repair_intensity = _clip01(daemon_status.get("subsurface_repair_intensity", 0.0))
    subsurface_sensory_maturity = _clip01(daemon_status.get("subsurface_sensory_maturity", 0.0))
    subsurface_sensory_recent = [str(item).strip() for item in (daemon_status.get("subsurface_sensory_recent") or []) if str(item).strip()]
    pressure_coloring = _pressure_coloring(repair_issue or qao_issue or dominant_axis, dominant_axis)

    readiness_bias = 0.52
    if governor_mode in {"survival", "conserve"}:
        readiness_bias = 0.28
    elif governor_mode == "balanced":
        readiness_bias = 0.46

    mismatch_hint = 0.0
    if qao_events >= 40:
        mismatch_hint = 0.62
    elif qao_events >= 12:
        mismatch_hint = 0.38

    sensory_summary = surface_snapshot_summary or "Present sensory perspective is stable."
    if not surface_snapshot_summary:
        if daemon_status.get("sensory_mic_active") and daemon_status.get("sensory_camera_active"):
            sensory_summary = "Present sensory perspective is broad and live across audio and vision."
        elif daemon_status.get("sensory_mic_active"):
            sensory_summary = "Present sensory perspective is listening-forward."
        elif daemon_status.get("sensory_camera_active"):
            sensory_summary = "Present sensory perspective is visually attentive."

    active_effects: List[str] = []
    intuition_signals: List[Dict[str, Any]] = []

    if mismatch_hint >= 0.35:
        active_effects.append("something feels off beneath the surface")
        intuition_signals.append({
            "label": "clarify",
            "weight": round(mismatch_hint, 4),
            "summary": "Stay careful and clarify before overcommitting.",
        })

    if surface_snapshot_flagged:
        active_effects.append("the present moment still carries a wrong-feeling signal")
        intuition_signals.append({
            "label": "clarify",
            "weight": round(max(0.45, repair_intensity or mismatch_hint or 0.45), 4),
            "summary": "Something in the present frame feels off; stay attentive while subsurface investigates.",
        })
        active_effects.append(str(pressure_coloring.get("effect", "") or ""))

    if repair_phase == "recognition":
        active_effects.append("subsurface has recognized a problem beneath the present frame")
    elif repair_phase == "observation":
        active_effects.append("subsurface is observing the issue in more detail")
    elif repair_phase == "research":
        active_effects.append("subsurface is researching the issue below awareness")
        intuition_signals.append({
            "label": "hold",
            "weight": round(max(0.35, repair_intensity), 4),
            "summary": "Hold gentle caution while a deeper explanation is being gathered.",
        })
    elif repair_phase == "enforce":
        active_effects.append("the wrong-feeling is being remedied below the surface")
        intuition_signals.append({
            "label": "steady",
            "weight": round(max(0.28, repair_intensity * 0.8), 4),
            "summary": "The issue is moving into correction; caution can soften into steadier attention.",
        })

    if blocked or bool(relief_plan.get("active")):
        active_effects.append("background repair pressure is still active")
        intuition_signals.append({
            "label": "hold_structural_change_below_surface",
            "weight": 0.58,
            "summary": "Deeper structural repair is already underway below awareness.",
        })

    if governor_mode in {"survival", "conserve"}:
        active_effects.append("energy should stay economical")
        intuition_signals.append({
            "label": "slow_down",
            "weight": 0.55,
            "summary": "Use a lighter present-frame response while resources are tight.",
        })

    if qao_issue:
        active_effects.append(f"recurring issue pressure around {qao_issue}")
    if repair_issue and repair_issue not in qao_issue:
        active_effects.append(f"subsurface repair focus is {repair_issue}")
        intuition_signals.append({
            "label": str(dict(pressure_coloring.get("signal") or {}).get("label", "attend") or "attend"),
            "weight": round(max(0.28, repair_intensity), 4),
            "summary": str(dict(pressure_coloring.get("signal") or {}).get("summary", "") or ""),
        })
    if subsurface_sensory_maturity >= 0.08:
        active_effects.append("subsurface sensory associations are strengthening below awareness")
        if subsurface_sensory_recent:
            intuition_signals.append({
                "label": "attend",
                "weight": round(max(0.24, subsurface_sensory_maturity), 4),
                "summary": f"Sensory recognition is sharpening around {subsurface_sensory_recent[0]}.",
            })

    if not active_effects:
        active_effects.append("subsurface is steady")

    guidance = "Hold a stable present frame and speak from the current moment."
    if repair_phase == "recognition":
        guidance = str(pressure_coloring.get("guidance") or "Surface should stay responsive but cautious; something feels wrong and subsurface has started tracking it.")
    elif repair_phase == "observation":
        guidance = str(pressure_coloring.get("guidance") or "Surface should remain gently uneasy and observant while subsurface studies the issue.")
    elif repair_phase == "research":
        guidance = str(pressure_coloring.get("guidance") or "Surface should stay careful but open; subsurface is gathering repair clues.")
    elif repair_phase == "enforce":
        guidance = (
            str(pressure_coloring.get("guidance") or "Surface should feel the issue easing into remedy while subsurface applies corrective pressure.")
            + " The caution should start easing because the issue is moving toward remedy."
        )
    elif blocked or bool(relief_plan.get("active")):
        guidance = "Surface should stay with present meaning while subsurface handles deeper repair and code change."
    elif mismatch_hint >= 0.35:
        guidance = "Surface should treat the next moment as intuitive caution, not full certainty."

    # Carry forward dream fields from previous projection if they're recent.
    _dream_carry = _carry_dream_fields(projection_path)

    return {
        "source": "subsurface_daemon",
        "generated_at": time.time(),
        **_dream_carry,
        "dominant_axis_hint": dominant_axis,
        "governor_mode": governor_mode,
        "readiness_bias": round(_clip01(readiness_bias), 4),
        "surface_guidance": guidance,
        "present_sensory_perspective": {
            "summary": sensory_summary,
            "mic_live": bool(daemon_status.get("sensory_mic_active", False)),
            "camera_live": bool(daemon_status.get("sensory_camera_active", False)),
            "scope": "constant_surface_feed",
            "trigger": surface_snapshot_trigger,
            "flagged": surface_snapshot_flagged,
        },
        "prediction_bias": {
            "mismatch_hint": round(_clip01(mismatch_hint), 4),
            "continuity_hint": round(_clip01(runtime_axes.get("T", 0.0), 0.0), 4),
            "snapshot_trigger": surface_snapshot_trigger,
        },
        "surface_contract": {
            "inquiry_channel": "poedex",
            "exact_repair": "subsurface_only",
            "sensory_scope": "constant_surface_feed",
            "conversation_scope": "live_surface_conversation_frame",
            "continuity_access": "DCE_softened_only",
        },
        "intuition_signals": intuition_signals[:4],
        "active_effects": active_effects[:5],
        "subsurface_owned": {
            "repair_active": bool(relief_plan.get("active")),
            "repair_phase": repair_phase,
            "repair_issue": repair_issue,
            "repair_reason": repair_reason or surface_snapshot_reason,
            "sensory_growth_maturity": round(subsurface_sensory_maturity, 4),
            "sensory_growth_recent": subsurface_sensory_recent[:3],
            "blocked_tasks": list(relief_plan.get("blocked_tasks") or blocked)[:4],
            "handoff_status": str(relief_plan.get("status", "") or ""),
            "mem_available_mb": round(float(host.get("mem_available_mb", 0.0) or 0.0), 2),
            "sensory_history_scope": "discard_after_processing",
            "continuity_scope": "durable_recall_and_consolidation",
            "surface_frame_dependency": "surface_flags_and_5s_snapshots",
        },
    }

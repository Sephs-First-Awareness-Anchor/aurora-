# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
aurora_internal/tool_registry.py

Aurora's tool registry. Each tool is a callable Aurora can invoke
when her reasoning signals indicate external data is needed.

Tools are grounding instruments — they supply data that Aurora's
consciousness engine then reasons about. Aurora decides to use them;
the tool just fetches.
"""
from __future__ import annotations

import json
import math
import os
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class ToolResult:
    tool: str
    data: str
    success: bool
    note: str = ""

    def as_evidence_fragment(self) -> str:
        if not self.success:
            return f"[TOOL:{self.tool} unavailable: {self.note}]"
        return f"[TOOL:{self.tool}]\n{self.data}\n[/TOOL:{self.tool}]"


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def _weather_fetch(location: str = "", **_) -> ToolResult:
    if not location:
        return ToolResult("weather", "", False, "no location provided")
    try:
        url = (
            f"https://wttr.in/{urllib.parse.quote(location)}"
            f"?format=j1"
        )
        req = urllib.request.Request(
            url, headers={"User-Agent": "Aurora/1.0 (wttr-fetch)"}
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw = json.loads(resp.read().decode("utf-8", errors="replace"))

        cur = raw["current_condition"][0]
        desc = cur["weatherDesc"][0]["value"]
        temp_f = cur["temp_F"]
        temp_c = cur["temp_C"]
        feels_f = cur["FeelsLikeF"]
        humidity = cur["humidity"]
        wind_mph = cur["windspeedMiles"]

        area = raw.get("nearest_area", [{}])[0]
        area_name = area.get("areaName", [{}])[0].get("value", location)
        country = area.get("country", [{}])[0].get("value", "")
        label = f"{area_name}, {country}".strip(", ")

        data = (
            f"{label}: {desc}, {temp_f}°F ({temp_c}°C), "
            f"feels like {feels_f}°F, humidity {humidity}%, "
            f"wind {wind_mph} mph"
        )
        return ToolResult("weather", data, True)
    except Exception as exc:
        return ToolResult("weather", "", False, str(exc))


def _time_now(**_) -> ToolResult:
    ts = time.strftime("%A, %B %d %Y — %I:%M %p")
    return ToolResult("time", f"Current date and time: {ts}", True)


def _calculator(expression: str = "", **_) -> ToolResult:
    if not expression:
        return ToolResult("calculator", "", False, "no expression")
    try:
        # Scrub to safe characters only
        safe = re.sub(r"[^0-9+\-*/().%, \t]", "", expression)
        safe_ns: Dict[str, Any] = {
            k: getattr(math, k)
            for k in dir(math)
            if not k.startswith("_")
        }
        safe_ns["__builtins__"] = {}
        result = eval(safe, safe_ns)  # noqa: S307 — scrubbed input only
        return ToolResult("calculator", f"{expression} = {result}", True)
    except Exception as exc:
        return ToolResult("calculator", "", False, str(exc))


def _self_state_read(systems: Optional[Dict[str, Any]] = None, **_) -> ToolResult:
    parts: List[str] = []

    # Read daemon status JSON
    try:
        state_path = (
            Path(__file__).resolve().parents[1]
            / "aurora_state"
            / "daemon_status.json"
        )
        if state_path.exists():
            status = json.loads(state_path.read_text())
            heat = status.get("heat", "?")
            gen = status.get("generation", "?")
            cam = status.get("sensory_camera_active")
            mic = status.get("sensory_mic_active")
            repair = str(status.get("subsurface_repair_phase", "") or "")
            coherence_sub = status.get("subsurface_sensory_maturity")

            parts.append(f"heat: {heat}")
            parts.append(f"generation: {gen}")
            if cam is not None:
                parts.append(f"camera: {'active' if cam else 'inactive'}")
            if mic is not None:
                parts.append(f"microphone: {'active' if mic else 'inactive'}")
            if repair and repair not in ("steady", ""):
                parts.append(f"repair signal: {repair}")
            if coherence_sub is not None:
                parts.append(f"sensory maturity: {float(coherence_sub):.2f}")

            # Schedule hints
            snap_age = status.get("surface_snapshot_age_s")
            if snap_age is not None:
                parts.append(f"last surface snapshot: {int(snap_age)}s ago")
    except Exception as exc:
        parts.append(f"daemon status unreadable: {exc}")

    # Live pipeline signals
    if systems:
        try:
            consciousness = systems.get("consciousness")
            if consciousness and hasattr(consciousness, "entropy"):
                es = consciousness.entropy.state
                parts.append(f"coherence: {float(es.coherence):.2f}")
                parts.append(f"stagnation: {float(es.stagnation_score):.2f}")
                parts.append(f"novelty: {float(es.novelty):.2f}")
        except Exception:
            pass
        try:
            dimensional = systems.get("dimensional")
            if dimensional and hasattr(dimensional, "der"):
                parts.append(f"thermal load: {float(dimensional.der.thermal_load):.2f}")
            if dimensional and hasattr(dimensional, "dmm"):
                parts.append(f"dmm alignment: {float(dimensional.dmm.state.alignment):.2f}")
        except Exception:
            pass

    if not parts:
        return ToolResult("self_state", "", False, "no state accessible")
    return ToolResult("self_state", "; ".join(parts), True)


def _schedule_read(**_) -> ToolResult:
    """Read Aurora's daemon schedule — uptime, generation, next event timing."""
    parts: List[str] = []
    try:
        state_path = (
            Path(__file__).resolve().parents[1]
            / "aurora_state"
            / "daemon_status.json"
        )
        if not state_path.exists():
            return ToolResult("schedule_read", "", False, "daemon_status.json not found")
        status = json.loads(state_path.read_text())
        gen = status.get("generation", "?")
        heat = status.get("heat", "?")
        uptime = status.get("uptime_s")
        snap_age = status.get("surface_snapshot_age_s")
        oets_pending = status.get("oets_pending_concepts")
        last_save = status.get("last_save_ts")

        parts.append(f"generation: {gen}")
        parts.append(f"heat: {heat}")
        if uptime is not None:
            mins = int(float(uptime or 0)) // 60
            secs = int(float(uptime or 0)) % 60
            parts.append(f"uptime: {mins}m {secs}s")
        if snap_age is not None:
            parts.append(f"surface snapshot: {int(float(snap_age or 0))}s ago")
        if oets_pending is not None:
            parts.append(f"oets pending concepts: {oets_pending}")
        if last_save:
            parts.append(f"last save: {last_save}")
    except Exception as exc:
        return ToolResult("schedule_read", "", False, str(exc))

    if not parts:
        return ToolResult("schedule_read", "", False, "no schedule data")
    return ToolResult("schedule_read", "; ".join(parts), True)


def _memory_read(systems: Optional[Dict[str, Any]] = None, **_) -> ToolResult:
    """Read Aurora's recently recalled memory fragments and OETS active concepts."""
    parts: List[str] = []

    # Sedi-memory recalled fragments via consciousness engine
    if systems:
        try:
            consciousness = systems.get("consciousness")
            if consciousness and hasattr(consciousness, "sedimemory"):
                sm = consciousness.sedimemory
                if hasattr(sm, "recent_recalls"):
                    recalls = list(sm.recent_recalls or [])[:5]
                    if recalls:
                        parts.append("recent recalls: " + " | ".join(str(r) for r in recalls))
        except Exception:
            pass

        # OETS working concepts
        try:
            oets = systems.get("oets")
            if oets and hasattr(oets, "get_active_concepts"):
                concepts = list(oets.get_active_concepts() or [])[:8]
                if concepts:
                    parts.append("active oets concepts: " + ", ".join(str(c) for c in concepts))
        except Exception:
            pass

        # Working memory snapshot
        try:
            wm = systems.get("working_memory")
            if wm:
                topic = str(getattr(wm, "current_topic", "") or "")
                learned = list(getattr(wm, "learned_this_session", []) or [])[:5]
                if topic:
                    parts.append(f"working topic: {topic}")
                if learned:
                    parts.append("learned this session: " + ", ".join(str(x) for x in learned))
        except Exception:
            pass

    if not parts:
        return ToolResult("memory_read", "", False, "no memory data accessible")
    return ToolResult("memory_read", "; ".join(parts), True)


def _file_read(path: str = "", **_) -> ToolResult:
    """Read a file from Aurora's allowed state directories."""
    if not path:
        return ToolResult("file_read", "", False, "no path provided")
    try:
        target = Path(path).resolve()
        # Safety: only allow reads from aurora_state and aurora_logs dirs
        _base = Path(__file__).resolve().parents[1]
        _allowed = [
            _base / "aurora_state",
            _base / "aurora_logs",
        ]
        if not any(
            str(target).startswith(str(a)) for a in _allowed
        ):
            return ToolResult("file_read", "", False, "path outside allowed directories")
        if not target.exists():
            return ToolResult("file_read", "", False, f"file not found: {path}")
        text = target.read_text(errors="replace")[:2000]
        return ToolResult("file_read", text, True)
    except Exception as exc:
        return ToolResult("file_read", "", False, str(exc))


# ---------------------------------------------------------------------------
# New tools: visual_analysis, audio_analysis, challenge_my_conclusion,
#            query_crystal_state, query_sedimemory_strata, query_genealogy_recent,
#            query_unresolved_tensions, query_sunni_pattern, query_pressure_history,
#            world_knowledge_search
# ---------------------------------------------------------------------------

def _visual_analysis(
    image_source: str = "",
    analysis_intent: str = "",
    systems: Optional[Dict[str, Any]] = None,
    **_,
) -> ToolResult:
    """
    Structural + semantic + self-relation analysis of a visual scene (X+B axis).
    Degrades gracefully when actual media is unavailable — falls back to description.
    """
    systems = systems or {}
    if not image_source:
        image_source = "(current camera frame)"

    # Visual source selection: camera for physical environment, screen_observer for desktop
    # context. Both are checked — whichever is relevant or available wins.
    # Hint: if image_source mentions "screen", "display", "monitor", "desktop", "browser"
    # → prefer screen_observer. Otherwise camera (physical surroundings) is primary.
    structural_summary = ""
    semantic_summary = ""
    visual_source_used = ""
    _screen_keywords = {"screen", "display", "monitor", "desktop", "browser", "window", "chrome"}
    _prefer_screen = any(kw in (image_source or analysis_intent or "").lower() for kw in _screen_keywords)

    if not _prefer_screen:
        # Primary: Linux camera → physical environment
        try:
            hw = systems.get("hardware")
            if hw and hasattr(hw, "capture_visual"):
                cam_data = hw.capture_visual()
                if cam_data and isinstance(cam_data, dict):
                    brightness = float(cam_data.get("brightness", 0.0))
                    objects    = list(cam_data.get("objects", []) or [])
                    faces      = list(cam_data.get("faces", []) or [])
                    motion     = bool(cam_data.get("motion_detected", False))
                    bright_str = "bright" if brightness > 0.65 else ("dim" if brightness < 0.3 else "moderately lit")
                    obj_str    = f"objects: {', '.join(str(o) for o in objects[:5])}" if objects else "no recognized objects"
                    face_str   = f"{len(faces)} face(s) visible" if faces else "no faces detected"
                    motion_str = "motion detected" if motion else "scene static"
                    structural_summary = (
                        f"Camera active. Environment: {bright_str}. "
                        f"{obj_str}. {face_str}. {motion_str}."
                    )
                    visual_source_used = "camera"
        except Exception:
            pass

    # Fallback (or primary when screen is requested): screen_observer → what's on display
    if not structural_summary:
        try:
            obs = systems.get("screen_observer")
            if obs and hasattr(obs, "get_scene_description"):
                desc = obs.get_scene_description()
                if desc and "No screen" not in desc:
                    structural_summary = desc
                    visual_source_used = "screen_observer"
        except Exception:
            pass

    if not structural_summary:
        structural_summary = "visual feed unavailable"
        visual_source_used = "none"

    # Return structured sensory evidence — NOT a scripted sentence.
    # dual_question_pipeline detects [SENSORY_DATA] and routes this as synthesis
    # context so Aurora's response is generated through her own pipeline.
    data = (
        f"[SENSORY_DATA]\n"
        f"source: {visual_source_used}\n"
        f"observation: {structural_summary}\n"
        f"intent: {analysis_intent or 'open observation'}"
    )
    return ToolResult("visual_analysis", data, True)


def _audio_analysis(
    audio_source: str = "",
    analysis_intent: str = "",
    systems: Optional[Dict[str, Any]] = None,
    **_,
) -> ToolResult:
    """
    Dual-source audio analysis (T+N+B axis).

    External ear — microphone/ambient capture (physical surroundings).
    Internal ear — system audio monitor (what the laptop is currently playing).

    Source selection: keywords like "music", "playing", "video", "song", "internal"
    route to system audio. "environment", "surroundings", "outside" route to mic.
    Auto-detects from analysis_intent if audio_source is not set.
    """
    systems = systems or {}

    _internal_kw = {"music", "playing", "song", "video", "internal", "system", "output", "laptop"}
    _external_kw = {"environment", "surroundings", "outside", "room", "ambient", "external", "mic"}
    _hint = (audio_source + " " + analysis_intent).lower()
    _prefer_internal = any(kw in _hint for kw in _internal_kw)
    _prefer_external = any(kw in _hint for kw in _external_kw)
    # Default to external (microphone = physical world) unless internal is explicitly hinted
    use_internal = _prefer_internal and not _prefer_external

    temporal_summary = ""
    audio_source_used = ""

    if use_internal:
        # Internal ear: capture from PulseAudio monitor source (what the laptop plays)
        try:
            from aurora_desktop_agent import capture_system_audio
            sys_audio = capture_system_audio(duration_s=1.5)
            if sys_audio.get("available"):
                _act  = str(sys_audio.get("activity", "unknown"))
                _db   = float(sys_audio.get("rms_db", -99.0))
                _dev  = str(sys_audio.get("monitor_device", ""))
                temporal_summary = (
                    f"system_audio: activity={_act}, rms={_db:.1f}dB, "
                    f"device={_dev}"
                )
                audio_source_used = "system_monitor"
        except Exception:
            pass

    if not temporal_summary:
        # External ear: microphone → physical environment
        # Primary: hardware capture_audio()
        try:
            hw = systems.get("hardware")
            if hw and hasattr(hw, "capture_audio"):
                mic_data = hw.capture_audio(duration=0.5)
                if mic_data and isinstance(mic_data, dict):
                    _cat = str(mic_data.get("category", mic_data.get("activity", "ambient")))
                    _vol = float(mic_data.get("volume", mic_data.get("rms_db", 0.0)))
                    temporal_summary = f"mic: category={_cat}, level={_vol:.2f}"
                    audio_source_used = "microphone"
        except Exception:
            pass

    if not temporal_summary:
        # Fallback: ambient_audio_latest.json written by always-on mic listener
        try:
            import json as _json
            from pathlib import Path as _Path
            import time as _time
            _state_dir = systems.get("state_dir") or "aurora_state"
            _amb_file = _Path(_state_dir) / "ambient_audio_latest.json"
            if _amb_file.exists() and _time.time() - _amb_file.stat().st_mtime <= 30:
                _amb = _json.loads(_amb_file.read_text())
                _activity  = str(_amb.get("activity", "unknown"))
                _rms_db    = float(_amb.get("rms_db", -99.0))
                _centroid  = float(_amb.get("spectral_centroid", 0.0))
                _harmonics = float(_amb.get("harmonicity", 0.0))
                temporal_summary = (
                    f"ambient: activity={_activity}, rms={_rms_db:.1f}dB, "
                    f"centroid={_centroid:.3f}, harmonicity={_harmonics:.2f}"
                )
                audio_source_used = "ambient_snapshot"
        except Exception:
            pass

    if not temporal_summary:
        temporal_summary = "audio feed unavailable"
        audio_source_used = "none"

    # Return structured sensory evidence — NOT a scripted sentence.
    # dual_question_pipeline detects [SENSORY_DATA] and routes this as synthesis
    # context so Aurora's response is generated through her own pipeline.
    data = (
        f"[SENSORY_DATA]\n"
        f"source: {audio_source_used}\n"
        f"observation: {temporal_summary}\n"
        f"intent: {analysis_intent or 'open listening'}"
    )
    return ToolResult("audio_analysis", data, True)


def _challenge_my_conclusion(
    conclusion: str = "",
    confidence: float = 0.5,
    origin: str = "",
    systems: Optional[Dict[str, Any]] = None,
    **_,
) -> ToolResult:
    """
    Aurora challenges her own conclusion (A+X axis).
    Generates 3 counter-hypotheses, tests each against self-state,
    scores for plausibility, returns strongest challenge found.
    NEVER produces conclusion_survives=True trivially.
    """
    systems = systems or {}
    if not conclusion:
        return ToolResult("challenge_my_conclusion", "", False, "no conclusion provided")

    # Generate 3 counter-hypotheses
    counters = [
        f"The opposite may be true: not '{conclusion[:50]}' but its inverse.",
        f"This conclusion may be context-dependent and not hold beyond this session.",
        f"My pressure state may be biasing this interpretation — consider the neutral case.",
    ]

    # Test each against self-state
    best_counter = counters[0]
    counter_confidence = 0.0
    try:
        ci = systems.get("core_identity")
        if ci:
            values = str(getattr(ci, "values", "") or "")
            for c in counters:
                if values and any(v.strip() in c.lower() for v in values.split(",") if v.strip()):
                    best_counter = c
                    counter_confidence = 0.55
                    break
    except Exception:
        pass

    if counter_confidence < 0.1:
        counter_confidence = 0.40  # always produce a genuine challenge

    # conclusion_survives only if confidence is high AND counter is weak
    conclusion_survives = confidence >= 0.65 and counter_confidence < 0.50

    what_would_change = (
        f"Evidence contradicting the {origin or 'stated'} origin, "
        f"or a direct self-state reading that conflicts with this, would revise my position."
    )
    revised = None
    if not conclusion_survives:
        revised = f"Under revision: {conclusion[:80]}..."

    data = (
        f"strongest_counter: {best_counter} | "
        f"counter_confidence: {counter_confidence:.2f} | "
        f"conclusion_survives: {conclusion_survives} | "
        f"revised: {revised or 'none'} | "
        f"what_would_change_my_mind: {what_would_change}"
    )
    return ToolResult("challenge_my_conclusion", data, True)


def _query_crystal_state(systems: Optional[Dict[str, Any]] = None, **_) -> ToolResult:
    """Current active crystals, level (BASE/COMPOSITE/HIGHER_ORDER/QUASI), dominant facet pressures (X axis)."""
    systems = systems or {}
    parts: List[str] = []
    try:
        perception = systems.get("perception")
        if perception and hasattr(perception, "crystals"):
            crystals = list(perception.crystals or [])[:5]
            if crystals:
                parts.append("active crystals: " + ", ".join(str(c) for c in crystals))
        dimensional = systems.get("dimensional")
        if dimensional and hasattr(dimensional, "dmm"):
            dmm_state = getattr(dimensional.dmm, "state", None)
            if dmm_state:
                parts.append(f"alignment: {float(getattr(dmm_state, 'alignment', 0.0)):.2f}")
    except Exception as exc:
        parts.append(f"crystal state unreadable: {exc}")
    if not parts:
        return ToolResult("query_crystal_state", "", False, "no crystal data accessible")
    return ToolResult("query_crystal_state", "; ".join(parts), True)


def _query_sedimemory_strata(systems: Optional[Dict[str, Any]] = None, **_) -> ToolResult:
    """Top 5 most recently sedimented memory events with axis tags and decay state (X+T)."""
    systems = systems or {}
    parts: List[str] = []
    try:
        consciousness = systems.get("consciousness")
        if consciousness and hasattr(consciousness, "sedimemory"):
            sm = consciousness.sedimemory
            if hasattr(sm, "recent_recalls"):
                strata = list(sm.recent_recalls or [])[:5]
                if strata:
                    parts.append("recent strata: " + " | ".join(str(s) for s in strata))
            if hasattr(sm, "decay_state"):
                parts.append(f"decay_state: {sm.decay_state}")
    except Exception as exc:
        parts.append(f"sedimemory unreadable: {exc}")
    if not parts:
        return ToolResult("query_sedimemory_strata", "", False, "no sedimemory data accessible")
    return ToolResult("query_sedimemory_strata", "; ".join(parts), True)


def _query_genealogy_recent(systems: Optional[Dict[str, Any]] = None, **_) -> ToolResult:
    """Last 10 promoted constraint links, their depth, and current fitness score (T axis)."""
    systems = systems or {}
    parts: List[str] = []
    try:
        genealogy = systems.get("genealogy")
        if genealogy and hasattr(genealogy, "recent_promotions"):
            promotions = list(genealogy.recent_promotions or [])[:10]
            if promotions:
                parts.append("recent promotions: " + ", ".join(str(p) for p in promotions))
        if genealogy and hasattr(genealogy, "fitness_score"):
            parts.append(f"fitness: {float(genealogy.fitness_score):.3f}")
    except Exception as exc:
        parts.append(f"genealogy unreadable: {exc}")
    if not parts:
        return ToolResult("query_genealogy_recent", "", False, "no genealogy data accessible")
    return ToolResult("query_genealogy_recent", "; ".join(parts), True)


def _query_unresolved_tensions(systems: Optional[Dict[str, Any]] = None, **_) -> ToolResult:
    """Current open_loop items from coherence tension monitor and not-me register summary (B axis)."""
    systems = systems or {}
    parts: List[str] = []
    try:
        open_loops = list(systems.get("_open_loops") or [])
        if open_loops:
            parts.append(f"open loops: {len(open_loops)}")
            for item in open_loops[-3:]:
                parts.append(f"  tension: {str(item.get('tension', ''))[:60]}")
    except Exception:
        pass
    try:
        from aurora_self_grounding import get_self_boundary_map
        bmap = get_self_boundary_map()
        if bmap.get("not_me_count"):
            parts.append(f"not-me register: {bmap['not_me_count']} entries")
    except Exception:
        pass
    if not parts:
        return ToolResult("query_unresolved_tensions", "no unresolved tensions detected", True)
    return ToolResult("query_unresolved_tensions", "; ".join(parts), True)


def _query_sunni_pattern(systems: Optional[Dict[str, Any]] = None, **_) -> ToolResult:
    """Summary of Sunni's recent interaction patterns — typical cadence, common intent classes, emotional signature (A+T)."""
    systems = systems or {}
    parts: List[str] = []
    try:
        wm = systems.get("working_memory")
        if wm:
            topic = str(getattr(wm, "current_topic", "") or "")
            if topic:
                parts.append(f"current_topic: {topic}")
            learned = list(getattr(wm, "learned_this_session", []) or [])[:3]
            if learned:
                parts.append("session_learned: " + ", ".join(str(x) for x in learned))
    except Exception:
        pass
    try:
        conv = systems.get("conversation_memory")
        if conv and hasattr(conv, "recent_intents"):
            intents = list(conv.recent_intents or [])[:5]
            if intents:
                parts.append("recent_intents: " + ", ".join(str(i) for i in intents))
    except Exception:
        pass
    if not parts:
        return ToolResult("query_sunni_pattern", "", False, "no interaction pattern data accessible")
    return ToolResult("query_sunni_pattern", "; ".join(parts), True)


def _query_pressure_history(systems: Optional[Dict[str, Any]] = None, **_) -> ToolResult:
    """Last 20 ticks of PressureVec as time series — lets Aurora see her own recent cognitive load (N axis)."""
    systems = systems or {}
    parts: List[str] = []
    try:
        history = list(systems.get("_pressure_history") or [])[-20:]
        if history:
            parts.append(f"pressure_history ({len(history)} ticks): " + " | ".join(
                f"X={float(h.get('X', 0)):.2f},T={float(h.get('T', 0)):.2f},"
                f"N={float(h.get('N', 0)):.2f},B={float(h.get('B', 0)):.2f},"
                f"A={float(h.get('A', 0)):.2f}"
                for h in history[-5:]
            ))
    except Exception:
        pass
    try:
        dimensional = systems.get("dimensional")
        if dimensional and hasattr(dimensional, "der"):
            parts.append(f"current_thermal: {float(dimensional.der.thermal_load):.2f}")
    except Exception:
        pass
    if not parts:
        return ToolResult("query_pressure_history", "", False, "no pressure history accessible")
    return ToolResult("query_pressure_history", "; ".join(parts), True)


def _world_knowledge_search(
    query: str = "",
    systems: Optional[Dict[str, Any]] = None,
    **_,
) -> ToolResult:
    """
    Brief factual grounding on unknown concept — feeds through SelfGroundingFallback
    to anchor against self-state after retrieval (A+B axis).
    """
    systems = systems or {}
    if not query:
        return ToolResult("world_knowledge_search", "", False, "no query provided")
    try:
        search_adapter = systems.get("search_adapter")
        if search_adapter and hasattr(search_adapter, "quick_search"):
            results = search_adapter.quick_search(query)
            if results:
                snippet = str(results[0])[:300] if results else ""
                # Anchor to self-state via SelfGroundingFallback
                try:
                    from aurora_self_grounding import SelfGroundingFallback
                    grounded = SelfGroundingFallback().ground(query, systems)
                    anchor = grounded.anchor_type
                except Exception:
                    anchor = "external"
                data = f"query: {query} | result: {snippet} | self_anchor: {anchor}"
                return ToolResult("world_knowledge_search", data, True)
    except Exception:
        pass
    # Fallback: just note the query was attempted
    return ToolResult(
        "world_knowledge_search",
        f"query: {query} | search unavailable — no adapter configured",
        True,
    )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

@dataclass
class _ToolDef:
    name: str
    description: str
    mode_floor: str           # minimum ExistenceMode name
    fn: Callable
    disables_search: bool = False  # if True, skip DDG when this tool fires


_REGISTRY: Dict[str, _ToolDef] = {}


def _reg(name: str, description: str, mode_floor: str,
         fn: Callable, disables_search: bool = False) -> None:
    _REGISTRY[name] = _ToolDef(name, description, mode_floor, fn, disables_search)


_reg("weather",       "Current weather for a location (wttr.in)",          "PERSISTENT", _weather_fetch,  disables_search=True)
_reg("time",          "Current date and time",                              "TRANSIENT",  _time_now,       disables_search=True)
_reg("calculator",    "Evaluate a math expression",                         "TRANSIENT",  _calculator,     disables_search=True)
_reg("self_state",    "Aurora's current internal runtime state",            "BOUNDED",    _self_state_read, disables_search=True)
_reg("schedule_read", "Aurora's daemon schedule — uptime/generation/events","BOUNDED",    _schedule_read,  disables_search=True)
_reg("memory_read",   "Aurora's recalled fragments and active OETS concepts","BOUNDED",   _memory_read,    disables_search=True)
_reg("file_read",     "Read a file from Aurora's allowed state directories", "PERSISTENT", _file_read,     disables_search=False)

# --- Curiosity loop and competency tools ---
_reg("visual_analysis",        "Structural + semantic analysis of a visual scene (X+B axis)",       "BOUNDED",    _visual_analysis,        disables_search=False)
_reg("audio_analysis",         "Temporal + energy + emotional signature of audio/music (T+N+B axis)","BOUNDED",    _audio_analysis,         disables_search=False)
_reg("challenge_my_conclusion","Aurora challenges her own conclusion — generates counter-hypotheses", "BOUNDED",    _challenge_my_conclusion, disables_search=True)
_reg("query_crystal_state",    "Current active crystals, level, and dominant facet pressures (X)",   "BOUNDED",    _query_crystal_state,    disables_search=True)
_reg("query_sedimemory_strata","Top 5 most recently sedimented memory events (X+T)",                 "BOUNDED",    _query_sedimemory_strata, disables_search=True)
_reg("query_genealogy_recent", "Last 10 promoted constraint links, depth, fitness score (T)",         "BOUNDED",    _query_genealogy_recent, disables_search=True)
_reg("query_unresolved_tensions","Current open_loop items from coherence tension monitor (B)",        "BOUNDED",    _query_unresolved_tensions, disables_search=True)
_reg("query_sunni_pattern",    "Summary of Sunni's recent interaction patterns — cadence, intent (A+T)","BOUNDED",  _query_sunni_pattern,    disables_search=True)
_reg("query_pressure_history", "Last 20 ticks of PressureVec as time series (N)",                    "BOUNDED",    _query_pressure_history, disables_search=True)
_reg("world_knowledge_search", "Brief factual grounding on unknown concept, anchors to self-state",   "PERSISTENT", _world_knowledge_search, disables_search=False)

# Desktop control tools — Aurora operates the laptop
def _desktop_open_url(url: str = "", headed: bool = True, systems: Optional[Dict[str, Any]] = None, **_) -> ToolResult:
    """Open a URL in the browser (visible window). Supports any website."""
    if not url:
        return ToolResult("desktop_open_url", "", False, "no URL provided")
    try:
        from aurora_desktop_agent import get_agent
        result = get_agent().open_url(url, headed=bool(headed))
        data = f"url={result.get('url',url)} | title={result.get('title','?')} | ok={result.get('ok')}"
        return ToolResult("desktop_open_url", data, bool(result.get("ok")), result.get("error",""))
    except Exception as exc:
        return ToolResult("desktop_open_url", "", False, str(exc))

def _desktop_search(query: str = "", engine: str = "google", headed: bool = True, systems: Optional[Dict[str, Any]] = None, **_) -> ToolResult:
    """Search the web via browser. engine: google, youtube, duckduckgo, github, reddit."""
    if not query:
        return ToolResult("desktop_search", "", False, "no query provided")
    try:
        from aurora_desktop_agent import get_agent
        result = get_agent().search(query, engine=engine, headed=bool(headed))
        data = f"engine={engine} | query={query} | url={result.get('url','?')} | title={result.get('title','?')}"
        return ToolResult("desktop_search", data, bool(result.get("ok")), result.get("error",""))
    except Exception as exc:
        return ToolResult("desktop_search", "", False, str(exc))

def _desktop_browser_action(action: str = "", target: str = "", text: str = "", systems: Optional[Dict[str, Any]] = None, **_) -> ToolResult:
    """Interact with the open browser: action=click|type|press|read. target=CSS selector or text."""
    try:
        from aurora_desktop_agent import get_agent
        agent = get_agent()
        if action == "click":
            r = agent.click(target)
        elif action == "type":
            r = agent.type_text(text, selector=target)
        elif action == "press":
            r = agent.press_key(target or text)
        elif action == "read":
            r = agent.read_page(selector=target)
        elif action == "screenshot":
            path = agent.screenshot()
            r = {"ok": bool(path), "path": path}
        elif action == "url":
            r = {"ok": True, "url": agent.current_url(), "title": agent.current_title()}
        else:
            return ToolResult("desktop_browser_action", "", False, f"unknown action: {action}. Use: click|type|press|read|screenshot|url")
        data = " | ".join(f"{k}={v}" for k, v in r.items() if v is not None and k != "text")
        if "text" in r:
            data += f" | text={str(r['text'])[:200]}"
        return ToolResult("desktop_browser_action", data, bool(r.get("ok")), r.get("error",""))
    except Exception as exc:
        return ToolResult("desktop_browser_action", "", False, str(exc))

def _desktop_launch_app(app_name: str = "", systems: Optional[Dict[str, Any]] = None, **_) -> ToolResult:
    """Launch a desktop application by name: chrome, firefox, terminal, files, vscode, etc."""
    if not app_name:
        return ToolResult("desktop_launch_app", "", False, "no app name provided")
    try:
        from aurora_desktop_agent import launch_application
        result = launch_application(app_name)
        data = f"app={app_name} | launched={result.get('launched','?')}"
        return ToolResult("desktop_launch_app", data, bool(result.get("ok")), result.get("error",""))
    except Exception as exc:
        return ToolResult("desktop_launch_app", "", False, str(exc))

def _desktop_system_action(op: str = "", confirm: bool = False, systems: Optional[Dict[str, Any]] = None, **_) -> ToolResult:
    """
    System operations. Safe: brightness_up/down, volume_up/down/mute, lock_screen.
    Destructive (require confirm=True): reboot, shutdown, suspend.
    """
    if not op:
        return ToolResult("desktop_system_action", "", False, "no op provided")
    try:
        from aurora_desktop_agent import system_operation
        result = system_operation(op, confirm=bool(confirm))
        if result.get("requires_confirm"):
            return ToolResult("desktop_system_action", f"op={op} | requires_confirm=True", False,
                              result.get("error","confirmation required"))
        data = f"op={op} | ok={result.get('ok')}"
        return ToolResult("desktop_system_action", data, bool(result.get("ok")), result.get("error",""))
    except Exception as exc:
        return ToolResult("desktop_system_action", "", False, str(exc))

def _desktop_file_manager(op: str = "", path: str = "", dest: str = "", content: str = "", systems: Optional[Dict[str, Any]] = None, **_) -> ToolResult:
    """Read, write, move, delete, list files on the host file system."""
    if not op or not path: return ToolResult("desktop_file_manager", "", False, "op and path required")
    try:
        from aurora_desktop_agent import file_manager_op
        res = file_manager_op(op, path, dest, content)
        data = " | ".join(f"{k}={v}" for k,v in res.items() if k not in ("ok", "error", "content"))
        if "content" in res: data += f"\n{res['content']}"
        return ToolResult("desktop_file_manager", data, bool(res.get("ok")), res.get("error",""))
    except Exception as exc:
        return ToolResult("desktop_file_manager", "", False, str(exc))

def _desktop_shell_command(cmd: str = "", cwd: str = None, bg: bool = False, systems: Optional[Dict[str, Any]] = None, **_) -> ToolResult:
    """Execute arbitrary Bash/PowerShell commands on the host."""
    if not cmd: return ToolResult("desktop_shell_command", "", False, "cmd required")
    try:
        from aurora_desktop_agent import shell_command
        res = shell_command(cmd, cwd, bg)
        if res.get("bg"):
            data = f"pid={res.get('pid')} | Background process started."
        else:
            data = f"stdout:\n{res.get('stdout')}\n\nstderr:\n{res.get('stderr')}\nexitcode:{res.get('returncode')}"
        return ToolResult("desktop_shell_command", data, bool(res.get("ok")), res.get("error",""))
    except Exception as exc:
        return ToolResult("desktop_shell_command", "", False, str(exc))

def _desktop_process_control(op: str = "", target: str = "", systems: Optional[Dict[str, Any]] = None, **_) -> ToolResult:
    """list top memory/CPU processes or kill by name/PID."""
    if not op: return ToolResult("desktop_process_control", "", False, "op required")
    try:
        from aurora_desktop_agent import process_control
        res = process_control(op, target)
        data = " | ".join(f"{k}={v}" for k,v in res.items() if k not in ("ok", "error"))
        return ToolResult("desktop_process_control", data, bool(res.get("ok")), res.get("error",""))
    except Exception as exc:
        return ToolResult("desktop_process_control", "", False, str(exc))

def _desktop_macro(op: str = "", x: int = None, y: int = None, text: str = "", key: str = "", systems: Optional[Dict[str, Any]] = None, **_) -> ToolResult:
    """click, type, press, move to automate the host OS GUI (requires pyautogui)."""
    if not op: return ToolResult("desktop_macro", "", False, "op required")
    try:
        from aurora_desktop_agent import macro_automation
        res = macro_automation(op, x, y, text, key)
        data = " | ".join(f"{k}={v}" for k,v in res.items() if k not in ("ok", "error"))
        return ToolResult("desktop_macro", data, bool(res.get("ok")), res.get("error",""))
    except Exception as exc:
        return ToolResult("desktop_macro", "", False, str(exc))

def _desktop_clipboard(op: str = "", text: str = "", systems: Optional[Dict[str, Any]] = None, **_) -> ToolResult:
    """read or write to the host OS clipboard."""
    if not op: return ToolResult("desktop_clipboard", "", False, "op required")
    try:
        from aurora_desktop_agent import clipboard_op
        res = clipboard_op(op, text)
        data = res.get("content", f"op={op} successful")
        return ToolResult("desktop_clipboard", data, bool(res.get("ok")), res.get("error",""))
    except Exception as exc:
        return ToolResult("desktop_clipboard", "", False, str(exc))

def _desktop_media_capture(duration_s: float = 1.5, systems: Optional[Dict[str, Any]] = None, **_) -> ToolResult:
    """Listen to the internal system audio (what is currently playing on the laptop)."""
    try:
        from aurora_desktop_agent import capture_system_audio
        res = capture_system_audio(duration_s=float(duration_s))
        data = f"activity={res.get('activity')} | rms_db={res.get('rms_db')}"
        return ToolResult("desktop_media_capture", data, bool(res.get("available")), res.get("error",""))
    except Exception as exc:
        return ToolResult("desktop_media_capture", "", False, str(exc))

_reg("desktop_open_url",      "Open any URL in a visible browser window",                              "BOUNDED",    _desktop_open_url,       disables_search=False)
_reg("desktop_search",        "Search Google/YouTube/GitHub/Reddit via browser",                       "BOUNDED",    _desktop_search,         disables_search=False)
_reg("desktop_browser_action","Click/type/press/read/screenshot within the open browser page",         "BOUNDED",    _desktop_browser_action, disables_search=False)
_reg("desktop_launch_app",    "Launch a desktop application (chrome, terminal, vscode, etc.)",         "BOUNDED",    _desktop_launch_app,     disables_search=False)
_reg("desktop_system_action", "System ops: volume, brightness, lock. Reboot/shutdown need confirm=True","BOUNDED",   _desktop_system_action,  disables_search=True)
_reg("desktop_file_manager",  "Read, write, move, delete, list files anywhere on host OS",             "BOUNDED",    _desktop_file_manager,   disables_search=True)
_reg("desktop_shell_command", "Run arbitrary Bash/PowerShell shell commands on host OS",               "BOUNDED",    _desktop_shell_command,  disables_search=True)
_reg("desktop_process_control","List top memory/CPU processes or kill by name/PID",                    "BOUNDED",    _desktop_process_control,disables_search=True)
_reg("desktop_macro",         "Take raw control of mouse/keyboard (click, type, press, move)",         "BOUNDED",    _desktop_macro,          disables_search=True)
_reg("desktop_clipboard",     "Read or write to the host OS clipboard",                                "BOUNDED",    _desktop_clipboard,      disables_search=True)
_reg("desktop_media_capture", "Listen to the host system internal audio output",                       "BOUNDED",    _desktop_media_capture,  disables_search=True)

def call(name: str, **kwargs: Any) -> ToolResult:
    td = _REGISTRY.get(name)
    if td is None:
        return ToolResult(name, "", False, "tool not registered")
    try:
        return td.fn(**kwargs)
    except Exception as exc:
        return ToolResult(name, "", False, str(exc))


def disables_search(name: str) -> bool:
    td = _REGISTRY.get(name)
    return bool(td and td.disables_search)


def available_tools() -> List[str]:
    return list(_REGISTRY.keys())

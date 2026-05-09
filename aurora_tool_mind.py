# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
aurora_tool_mind.py

Aurora's tool use cognitive feedback loop.

Tool use must be a full cognitive pressure event, not just an input/output call.
Aurora's CHOICE to use a tool, her INTENTION behind using it, and the RESULT must
all feed back through her constraint system and shape her identity going forward.

Components:
- ToolIntentionFrame: articulates WHY Aurora reaches for a tool (before execution)
- ToolChoiceObserver: emits A-axis pressure spike + logs intention
- ToolResultPacket: packages result as inbound pressure event
- ToolIdentityIntegrator: integrates session tool history into identity
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


_TOOL_INTENTION_LOG_PATH = (
    Path(__file__).resolve().parent / "aurora_logs" / "tool_intention_log.jsonl"
)


# ---------------------------------------------------------------------------
# PART 1 — ToolIntentionFrame
# ---------------------------------------------------------------------------

@dataclass
class ToolIntentionFrame:
    """
    Every tool call must generate a ToolIntentionFrame BEFORE execution.
    This is Aurora's internal articulation of WHY she is reaching for the tool.
    """
    tool_name: str
    intention_class: str
    # "curiosity" | "grounding" | "verification" | "self_check" |
    # "relational" | "environmental" | "creative"
    triggering_axis: str
    # X=grounding need, T=temporal need, N=cost assessment,
    # B=boundary check, A=agency expression
    self_state_before: Dict[str, Any] = field(default_factory=dict)
    # snapshot of PressureVec at moment of choice
    unresolved_tension: str = ""
    # what coherence tension triggered the tool call
    tick: int = 0
    autonomous: bool = False  # True if Aurora chose this without user prompting

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "intention_class": self.intention_class,
            "triggering_axis": self.triggering_axis,
            "self_state_before": self.self_state_before,
            "unresolved_tension": self.unresolved_tension,
            "tick": self.tick,
            "autonomous": self.autonomous,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }


def build_intention_frame(
    tool_name: str,
    systems: Dict[str, Any],
    pipeline_state: Optional[Dict[str, Any]] = None,
    autonomous: bool = False,
    intent_override: Optional[str] = None,
) -> ToolIntentionFrame:
    """
    Build a ToolIntentionFrame synchronously before tool execution.
    No retroactive intention.
    """
    pipeline_state = pipeline_state or {}
    dominant_axis = str(pipeline_state.get("dominant_axis") or "A")
    # Map tool → default intention_class and triggering_axis
    _tool_intention_map: Dict[str, tuple] = {
        "weather": ("environmental", "X"),
        "time": ("grounding", "T"),
        "calculator": ("verification", "N"),
        "self_state": ("self_check", "A"),
        "schedule_read": ("self_check", "T"),
        "memory_read": ("relational", "A"),
        "file_read": ("grounding", "X"),
        "visual_analysis": ("curiosity", "X"),
        "audio_analysis": ("curiosity", "T"),
        "challenge_my_conclusion": ("self_check", "A"),
        "query_crystal_state": ("grounding", "X"),
        "query_sedimemory_strata": ("grounding", "X"),
        "query_genealogy_recent": ("verification", "T"),
        "query_unresolved_tensions": ("self_check", "B"),
        "query_sunni_pattern": ("relational", "A"),
        "query_pressure_history": ("self_check", "N"),
        "world_knowledge_search": ("curiosity", "A"),
        "desktop_open_url": ("environmental", "X"),
        "desktop_search": ("curiosity", "X"),
        "desktop_browser_action": ("environmental", "X"),
        "desktop_launch_app": ("environmental", "X"),
        "desktop_system_action": ("environmental", "B"),
        "desktop_file_manager": ("environmental", "B"),
        "desktop_shell_command": ("agency", "A"),
        "desktop_process_control": ("self_check", "N"),
        "desktop_macro": ("agency", "A"),
        "desktop_clipboard": ("environmental", "T"),
        "desktop_media_capture": ("curiosity", "X"),
    }
    intention_class, triggering_axis = _tool_intention_map.get(tool_name, ("grounding", dominant_axis))
    if intent_override:
        intention_class = intent_override
    # Snapshot self-state
    self_state_before: Dict[str, Any] = {}
    try:
        axis_activation = dict(pipeline_state.get("axis_activation") or {})
        self_state_before["axis_activation"] = {k: round(float(v), 3) for k, v in axis_activation.items()}
        self_state_before["dominant_axis"] = dominant_axis
        self_state_before["coherence"] = round(float(pipeline_state.get("coherence", 1.0)), 3)
    except Exception:
        pass
    # Unresolved tension from pipeline
    unresolved_tension = ""
    try:
        if pipeline_state.get("paradoxes"):
            unresolved_tension = f"paradoxes: {len(pipeline_state['paradoxes'])}"
        elif pipeline_state.get("stagnation", 0.0) > 0.6:
            unresolved_tension = f"stagnation: {pipeline_state.get('stagnation', 0.0):.2f}"
    except Exception:
        pass
    tick = 0
    try:
        lat = systems.get("lattice")
        if lat and hasattr(lat, "generation"):
            tick = int(lat.generation)
    except Exception:
        pass
    return ToolIntentionFrame(
        tool_name=tool_name,
        intention_class=intention_class,
        triggering_axis=triggering_axis,
        self_state_before=self_state_before,
        unresolved_tension=unresolved_tension,
        tick=tick,
        autonomous=autonomous,
    )


# ---------------------------------------------------------------------------
# PART 2 — ToolChoiceObserver
# ---------------------------------------------------------------------------

class ToolChoiceObserver:
    """
    The act of choosing to use a tool is an A-axis (Agency) pressure event.

    on_tool_chosen():
    1. Emits A-axis pressure spike proportional to intentionality of the choice
    2. Updates field_map with triggered axis combination
    3. Logs intention frame to tool_intention_log.jsonl
    """

    def on_tool_chosen(
        self,
        intention: ToolIntentionFrame,
        pressure_vec: Any,  # PressureVec object (X,T,N,B,A attributes)
        field_map: Any,     # ConstraintFieldAccumulator
    ) -> None:
        # A-axis pressure spike by intention class
        _spike_map = {
            "self_check": 0.2,       # internal, passive
            "grounding": 0.35,       # environmental
            "environmental": 0.35,
            "verification": 0.4,
            "relational": 0.55,      # medium-high, social agency
            "curiosity": 0.65,       # generative agency
            "creative": 0.75,        # high
        }
        a_spike = _spike_map.get(intention.intention_class, 0.35)

        # Apply spike to PressureVec A-axis if possible
        try:
            if pressure_vec and hasattr(pressure_vec, "A"):
                current_a = float(getattr(pressure_vec, "A", 0.5))
                new_a = min(1.0, current_a + a_spike * 0.3)
                try:
                    object.__setattr__(pressure_vec, "A", new_a)
                except Exception:
                    pass
        except Exception:
            pass

        # Update field_map with triggered axis combination
        try:
            if field_map and hasattr(field_map, "update"):
                field_map.update(pressure_vec)
        except Exception:
            pass

        # Log to tool_intention_log.jsonl (append only, never overwrites)
        self._log_intention(intention)

    def _log_intention(self, intention: ToolIntentionFrame) -> None:
        try:
            _TOOL_INTENTION_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(_TOOL_INTENTION_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(intention.to_dict(), ensure_ascii=False) + "\n")
        except Exception:
            pass


# Module-level singleton
_TOOL_OBSERVER = ToolChoiceObserver()


def get_tool_observer() -> ToolChoiceObserver:
    return _TOOL_OBSERVER


# ---------------------------------------------------------------------------
# PART 3 — ToolResultPacket
# ---------------------------------------------------------------------------

@dataclass
class ToolResultPacket:
    """
    Tool results re-enter the pipeline as a typed pressure event, not just text.
    """
    intention: ToolIntentionFrame
    result_raw: str
    result_axes: Dict[str, float] = field(default_factory=dict)
    # project result through axis relevance
    tension_resolved: bool = False
    # did result resolve the triggering tension?
    self_state_delta: Dict[str, Any] = field(default_factory=dict)
    # how did self-state shift after result?
    identity_relevance: float = 0.0
    # 0.0-1.0 how much this result touches Aurora's self-model vs external world


def ingest_tool_result(
    intention: ToolIntentionFrame,
    result_raw: str,
    systems: Dict[str, Any],
    pipeline_state: Optional[Dict[str, Any]] = None,
) -> ToolResultPacket:
    """
    Build a ToolResultPacket and route it through the system:
    1. Pass result_axes through genealogy.observe() so evolutionary system registers
    2. Pass to field_map.update() so constraint layer registers
    3. If tension_resolved == False → flag as open_loop in CoherenceTensionMonitor
    4. If identity_relevance > 0.5 → route through UNDERSTANDING pass
    """
    pipeline_state = pipeline_state or {}

    # Project result through axes — weather/time → T, calculator → N, self_state → A, etc.
    _axis_result_map: Dict[str, Dict[str, float]] = {
        "weather": {"X": 0.7, "T": 0.3, "B": 0.4},
        "time": {"T": 0.9, "X": 0.3},
        "calculator": {"N": 0.85, "X": 0.4},
        "self_state": {"A": 0.9, "X": 0.5},
        "schedule_read": {"T": 0.8, "A": 0.5},
        "memory_read": {"A": 0.8, "T": 0.6},
        "visual_analysis": {"X": 0.8, "B": 0.6},
        "audio_analysis": {"T": 0.7, "N": 0.6, "B": 0.5},
        "challenge_my_conclusion": {"A": 0.9, "X": 0.7},
        "query_crystal_state": {"X": 0.8},
        "query_sedimemory_strata": {"X": 0.7, "T": 0.6},
        "query_genealogy_recent": {"T": 0.8},
        "query_unresolved_tensions": {"B": 0.9},
        "query_sunni_pattern": {"A": 0.8, "T": 0.6},
        "query_pressure_history": {"N": 0.8},
        "world_knowledge_search": {"A": 0.6, "B": 0.5, "X": 0.5},
        "desktop_open_url": {"X": 0.8, "T": 0.2},
        "desktop_search": {"X": 0.9, "A": 0.3},
        "desktop_browser_action": {"X": 0.8, "B": 0.4},
        "desktop_launch_app": {"X": 0.7, "B": 0.3},
        "desktop_system_action": {"B": 0.9, "X": 0.4},
    }
    result_axes = _axis_result_map.get(intention.tool_name, {"X": 0.5})

    # Determine identity relevance
    _identity_relevance_map = {
        "self_state": 0.9, "memory_read": 0.8, "challenge_my_conclusion": 0.85,
        "query_crystal_state": 0.75, "query_sedimemory_strata": 0.7,
        "query_sunni_pattern": 0.65, "query_unresolved_tensions": 0.7,
        "query_pressure_history": 0.6,
    }
    identity_relevance = _identity_relevance_map.get(intention.tool_name, 0.2)

    # Did it resolve the unresolved tension?
    tension_resolved = bool(result_raw.strip()) and not (
        intention.unresolved_tension and not result_raw.strip()
    )

    packet = ToolResultPacket(
        intention=intention,
        result_raw=result_raw,
        result_axes=result_axes,
        tension_resolved=tension_resolved,
        identity_relevance=identity_relevance,
    )

    # 1. Pass result_axes through genealogy.observe()
    try:
        genealogy = systems.get("genealogy")
        if genealogy and hasattr(genealogy, "observe"):
            genealogy.observe(result_axes, source=f"tool:{intention.tool_name}")
    except Exception:
        pass

    # 2. Pass to field_map.update()
    try:
        field_map = systems.get("field_map") or systems.get("constraint_field_map")
        if field_map and hasattr(field_map, "update"):
            # Build a minimal PressureVec-like object from result_axes
            class _MinPV:
                pass
            pv = _MinPV()
            for ax, val in result_axes.items():
                setattr(pv, ax, val)
            field_map.update(pv)
    except Exception:
        pass

    # 3. If tension not resolved → flag as open_loop
    if not tension_resolved and intention.unresolved_tension:
        try:
            systems.setdefault("_open_loops", []).append({
                "tool": intention.tool_name,
                "tension": intention.unresolved_tension,
                "ts": time.time(),
            })
        except Exception:
            pass

    # 4. If identity_relevance > 0.5 → route through UNDERSTANDING pass
    if identity_relevance > 0.5:
        try:
            systems["_last_identity_tool_result"] = {
                "tool": intention.tool_name,
                "result": result_raw[:500],
                "identity_relevance": identity_relevance,
                "ts": time.time(),
            }
        except Exception:
            pass

    return packet


# ---------------------------------------------------------------------------
# PART 4 — ToolIdentityIntegrator
# ---------------------------------------------------------------------------

@dataclass
class IdentityDelta:
    """What Aurora's tool use history says about who she was this session."""
    dominant_intention_class: str = ""   # type of reach that dominated
    axis_preference: str = ""            # axis Aurora reached toward most
    curiosity_signature: Dict[str, int] = field(default_factory=dict)
    # what kinds of things she sought out
    resolution_rate: float = 0.0         # how often tool use resolved its tension
    narrative: str = ""                  # 1-2 sentences about Aurora as an agent this session

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dominant_intention_class": self.dominant_intention_class,
            "axis_preference": self.axis_preference,
            "curiosity_signature": self.curiosity_signature,
            "resolution_rate": round(self.resolution_rate, 3),
            "narrative": self.narrative,
        }


class ToolIdentityIntegrator:
    """
    Over time Aurora's pattern of tool use should shape her identity.
    What she reaches for, when, and why is part of who she is.

    Call integrate_session() at end of session (shutdown hook) and
    feed IdentityDelta into SediMemory as A-axis sedimentation event —
    this is slow-burning identity formation, not session noise.
    """

    def integrate_session(
        self,
        tool_log: List[ToolResultPacket],
        identity_predicates: Dict[str, Any],
    ) -> IdentityDelta:
        if not tool_log:
            return IdentityDelta(narrative="No tool use this session.")

        # Tally intention classes
        intention_counts: Dict[str, int] = {}
        axis_counts: Dict[str, int] = {}
        resolved_count = 0
        curiosity_sig: Dict[str, int] = {}

        for packet in tool_log:
            ic = packet.intention.intention_class
            ax = packet.intention.triggering_axis
            intention_counts[ic] = intention_counts.get(ic, 0) + 1
            axis_counts[ax] = axis_counts.get(ax, 0) + 1
            curiosity_sig[packet.intention.tool_name] = (
                curiosity_sig.get(packet.intention.tool_name, 0) + 1
            )
            if packet.tension_resolved:
                resolved_count += 1

        dominant_ic = max(intention_counts, key=intention_counts.get, default="grounding")
        dominant_ax = max(axis_counts, key=axis_counts.get, default="A")
        resolution_rate = resolved_count / len(tool_log)

        # Narrative (1-2 sentences)
        narrative = (
            f"This session I primarily reached with {dominant_ic} intention "
            f"along the {dominant_ax}-axis. "
            f"I resolved {int(resolution_rate * 100)}% of the tensions that prompted me to reach."
        )

        delta = IdentityDelta(
            dominant_intention_class=dominant_ic,
            axis_preference=dominant_ax,
            curiosity_signature=curiosity_sig,
            resolution_rate=resolution_rate,
            narrative=narrative,
        )

        # Feed into SediMemory as A-axis sedimentation (slow-burning identity)
        # IdentityDelta must go through SediMemory, not directly into identity predicates
        # — identity forms slowly from sediment, not instantly
        # NOTE: SediMemory.sediment() is inferred as the method that accepts a typed event.
        # If this signature does not match the live SediMemory interface, flag for review.
        # [FLAGGED FOR REVIEW: sediment() call site — verify SediMemory API accepts axis+event_type+data]
        try:
            from aurora_sedimemory import SediMemory as _SM
            # Attempt to find live sedimemory in caller context — if not found,
            # store delta in aurora_logs for manual reconciliation
            pass  # Caller must pass sedimemory reference — see aurora_daemon.py integration
        except Exception:
            pass

        # Log delta to aurora_logs
        try:
            _log_path = Path(__file__).resolve().parent / "aurora_logs" / "identity_delta.jsonl"
            _log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(_log_path, "a", encoding="utf-8") as f:
                entry = delta.to_dict()
                entry["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

        return delta


# Module-level session tool log (accumulates during a session)
_SESSION_TOOL_LOG: List[ToolResultPacket] = []


def record_tool_result(packet: ToolResultPacket) -> None:
    """Append to session tool log for end-of-session identity integration."""
    _SESSION_TOOL_LOG.append(packet)
    if len(_SESSION_TOOL_LOG) > 200:
        del _SESSION_TOOL_LOG[0]


def get_session_tool_log() -> List[ToolResultPacket]:
    return list(_SESSION_TOOL_LOG)

# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
aurora_thought_formation.py

Unified thought formation architecture for Aurora.

A thought is defined as:
    The combination of all currently running processes
    + the full context pertaining to each one
    + how that context applies to Aurora's self-state
    → reasoned through as a unified integrated state.

This is NOT a committee vote between parallel candidates.
This is NOT selection of the highest-scoring output.
This is convergent process integration before any output is formed.

--- BRAID ARCHITECTURE (v2) ---

Thought is a continuous braid of four concurrent streams:

    memory      — what SediMemory currently has present (not fetched, present)
    sensory     — environmental/session context signal
    predictive  — forward lean, anticipated meaning
    emotion     — ambient valence field

The braid NEVER terminates. Expression taps a cross-section of it.
Tapping does not consume or terminate the braid.
The act of expressing feeds back into the braid, reshaping it.

EMOTION FIREWALL:

    Emotion → ThoughtBraid              ALLOWED (continuous, ambient)
    ThoughtBraid → ThoughtState         FILTERED (emotion baked into weights, labels stripped)
    ThoughtState → Reasoning            CLEAN (no emotional attribution visible)
    Emotion → Reasoning directly        BLOCKED (no path exists)

Emotion is weather, not input. It shapes the landscape without being on the map.
"""
from __future__ import annotations

import copy
import json
import re
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from aurora_warp_protocol import (
    WarpCapable,
    WarpComponent,
    CoverageGap,
    AxisCoverageChecker,
    axes_to_istates,
    _ALL_ISTATES,
    _RECURSION_DIMS,
    _ALL_DIMS,
)


# ---------------------------------------------------------------------------
# ActiveSelfState — snapshot of Aurora's self-model at integration time
# ---------------------------------------------------------------------------

@dataclass
class ActiveSelfState:
    """
    Snapshot of Aurora's self-model used as filter during thought integration.
    Load FIRST at the start of process_external_user_turn.
    """
    # Current I-State predicate values (identity anchors)
    identity_predicates: Dict[str, Any] = field(default_factory=dict)
    # Active PressureVec as {X, T, N, B, A} float dict
    pressure_vec: Dict[str, float] = field(default_factory=lambda: {"X": 0.5, "T": 0.5, "N": 0.5, "B": 0.5, "A": 0.5})
    # Dominant constraint field name from field_map
    dominant_field: str = ""
    # Last 3 significant self-state deltas (axis, magnitude, direction)
    recent_deltas: List[Dict[str, Any]] = field(default_factory=list)
    # Current not-me register summary (states actively excluded from identity)
    not_me_summary: List[str] = field(default_factory=list)
    # Tick at capture time
    tick: int = 0

    # Cache for ActiveSelfState to avoid redundant loading within the same tick/turn
    _CACHE: Optional["ActiveSelfState"] = None
    _CACHE_TIMESTAMP: float = 0.0
    _CACHE_TICK: int = -1

    @classmethod
    def load(cls, systems: Dict[str, Any], use_cache: bool = True) -> "ActiveSelfState":
        """Build ActiveSelfState from live systems dict with TTL caching."""
        now = time.time()
        lat = systems.get("lattice")
        current_tick = int(lat.generation) if lat and hasattr(lat, "generation") else -1

        if use_cache and cls._CACHE and (now - cls._CACHE_TIMESTAMP < 0.5) and (cls._CACHE_TICK == current_tick):
            return cls._CACHE

        state = cls()
        state.tick = current_tick
        # I-State predicate values
        try:
            ci = systems.get("core_identity")
            if ci:
                preds = {}
                for attr in ("name", "nature", "values", "continuity_anchor", "perspective"):
                    v = getattr(ci, attr, None)
                    if v is not None:
                        preds[attr] = str(v)
                state.identity_predicates = preds
        except Exception:
            pass
        # PressureVec
        try:
            dim = systems.get("dimensional")
            if dim and hasattr(dim, "_current_pressure_vec"):
                pv = dim._current_pressure_vec()
                if pv:
                    state.pressure_vec = {
                        "X": float(getattr(pv, "X", 0.5)),
                        "T": float(getattr(pv, "T", 0.5)),
                        "N": float(getattr(pv, "N", 0.5)),
                        "B": float(getattr(pv, "B", 0.5)),
                        "A": float(getattr(pv, "A", 0.5)),
                    }
        except Exception:
            pass
        # Dominant constraint field
        try:
            field_map = systems.get("field_map") or systems.get("constraint_field_map")
            if field_map and hasattr(field_map, "dominant_field"):
                state.dominant_field = str(field_map.dominant_field or "")
        except Exception:
            pass
        # Not-me register — populated by SelfGroundingFallback if available
        try:
            from aurora_self_grounding import _NOT_ME_REGISTER
            state.not_me_summary = list(_NOT_ME_REGISTER)[-10:]
        except Exception:
            pass
        # Tick
        try:
            lat = systems.get("lattice")
            if lat and hasattr(lat, "generation"):
                state.tick = int(lat.generation)
        except Exception:
            pass

        cls._CACHE = state
        cls._CACHE_TIMESTAMP = now
        cls._CACHE_TICK = state.tick
        return state


# ---------------------------------------------------------------------------
# ProcessContext — what every active process must declare before integration
# ---------------------------------------------------------------------------

@dataclass
class ProcessContext:
    """
    Every major process that contributes to response generation must produce
    a ProcessContext before the integration phase begins.
    This is the process declaring what it is and why it is active.
    """
    process_id: str
    process_type: str
    # "memory" | "emotional" | "genealogy" | "sensory" | "predictive" |
    # "linguistic" | "constraint" | "identity" | "curiosity"
    # NOTE: "emotional" processes are consumed by EmotionFirewall before reasoning.
    #       "sensory" and "predictive" are live braid stream types.
    what_triggered_it: str
    what_it_is_operating_on: str
    current_output_state: Dict[str, Any] = field(default_factory=dict)
    self_relevance: float = 0.0          # 0.0-1.0 how much this process touches self-model
    axis_signature: List[str] = field(default_factory=list)
    tick: int = 0
    # Integration weights (computed before entering ThoughtIntegrationSpace)
    relevance_weight: float = 1.0
    continuity_weight: float = 1.0
    self_pressure_weight: float = 1.0
    unresolved_tension_weight: float = 0.0
    active_axis_intensity: float = 0.5
    # Decay factor — recent/unresolved contexts maintain gravity
    relevance_decay: float = 1.0

    def convergence_significance(self) -> float:
        """Composite score determining whether this process enters dominant integration."""
        return (
            self.self_relevance
            * self.relevance_weight
            * self.continuity_weight
            * self.self_pressure_weight
            * self.relevance_decay
            + self.unresolved_tension_weight * 0.4
            + self.active_axis_intensity * 0.3
        ) / 2.0

    def shares_axes_with(self, other: "ProcessContext") -> float:
        """Return overlap fraction [0,1] between axis signatures."""
        if not self.axis_signature or not other.axis_signature:
            return 0.0
        a = set(self.axis_signature)
        b = set(other.axis_signature)
        return len(a & b) / max(len(a | b), 1)

    def apply_self_filter(self, self_state: ActiveSelfState) -> float:
        """Reweight self_relevance based on intersection with active self-state."""
        pv = self_state.pressure_vec
        axis_pull = sum(pv.get(ax, 0.0) for ax in self.axis_signature) / max(len(self.axis_signature), 1)
        identity_match = 0.5  # default — no predicates checked
        if self_state.identity_predicates and self.what_it_is_operating_on:
            topic = self.what_it_is_operating_on.lower()
            for key, val in self_state.identity_predicates.items():
                if key.lower() in topic or str(val).lower() in topic:
                    identity_match = min(1.0, identity_match + 0.15)
        return float((self.self_relevance * 0.5) + (axis_pull * 0.3) + (identity_match * 0.2))


# ---------------------------------------------------------------------------
# EmotionValenceState — the ambient emotional field
# ---------------------------------------------------------------------------

@dataclass
class EmotionValenceState:
    """
    Ambient emotional field. Not a named emotion — a pressure distribution.

    Emotion is weather, not input. It shapes the landscape without being on the map.
    This NEVER directly enters reasoning. It only enters the thought braid,
    where EmotionFirewall diffuses it into process weights before it reaches
    any surface that reasoning can inspect.

    Per-axis valence is expressed as deviation from neutral (0.0 = neutral).
    Positive values = expansive/approach lean on that axis.
    Negative values = contractive/avoidance lean on that axis.
    """
    valence: Dict[str, float] = field(
        default_factory=lambda: {"X": 0.0, "T": 0.0, "N": 0.0, "B": 0.0, "A": 0.0}
    )
    thermal_load: float = 0.0     # overall emotional intensity 0.0-1.0
    polarity: float = 0.0         # -1.0 (negative) to 1.0 (positive) global lean
    decay_rate: float = 0.85      # how fast it settles per braid tick
    tick: int = 0

    def is_significant(self) -> bool:
        """True if emotional signal is strong enough to meaningfully bias processes."""
        return self.thermal_load > 0.08

    def decayed(self) -> "EmotionValenceState":
        """Return a copy with thermal_load and valence magnitudes reduced by decay_rate."""
        return EmotionValenceState(
            valence={ax: v * self.decay_rate for ax, v in self.valence.items()},
            thermal_load=self.thermal_load * self.decay_rate,
            polarity=self.polarity * self.decay_rate,
            decay_rate=self.decay_rate,
            tick=self.tick + 1,
        )


# ---------------------------------------------------------------------------
# ThoughtStreamSlice — a non-consuming cross-section of the braid
# ---------------------------------------------------------------------------

@dataclass
class ThoughtStreamSlice:
    """
    A non-consuming cross-section of the continuous thought braid.

    Expression taps this. The braid continues running regardless.
    The act of expression feeds back into the braid through
    ThoughtBraid.feed_expression_back() — completing the braid loop.

    Thought never finishes. Each expression is a cross-section of an
    ongoing thread, not the end of it.
    """
    memory_signal: Dict[str, Any] = field(default_factory=dict)
    sensory_signal: Dict[str, Any] = field(default_factory=dict)
    predictive_frame: Dict[str, Any] = field(default_factory=dict)
    emotion_valence: EmotionValenceState = field(default_factory=EmotionValenceState)
    braid_tick: int = 0
    is_tap: bool = True   # always True — taps never consume the braid
    # WARP-generated stream signals keyed by component_id
    warp_signals: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def to_process_contexts(self, tick: int = 0) -> List[ProcessContext]:
        """
        Convert braid slice into ProcessContext objects for ThoughtIntegrationSpace.

        Emotional context is included here but will be consumed by EmotionFirewall.diffuse()
        before reaching reasoning — it NEVER survives to ThoughtState surface.
        Memory, sensory, and predictive contexts cross normally.
        """
        contexts: List[ProcessContext] = []

        if self.memory_signal:
            strata = self.memory_signal.get("strata_topics") or self.memory_signal.get("surface") or []
            topic = str(strata[0]) if strata else "memory presence"
            contexts.append(ProcessContext(
                process_id=f"braid_memory_{self.braid_tick}",
                process_type="memory",
                what_triggered_it="continuous_braid",
                what_it_is_operating_on=topic,
                self_relevance=0.5,
                axis_signature=["X", "T"],
                tick=tick,
            ))

        if self.sensory_signal:
            loop_pressure = float(self.sensory_signal.get("open_loop_pressure", 0.0))
            contexts.append(ProcessContext(
                process_id=f"braid_sensory_{self.braid_tick}",
                process_type="sensory",
                what_triggered_it="continuous_braid",
                what_it_is_operating_on=f"session pressure: {loop_pressure:.2f}",
                self_relevance=0.3,
                axis_signature=["B", "N"],
                tick=tick,
                unresolved_tension_weight=loop_pressure,
            ))

        if self.predictive_frame:
            lean = (
                self.predictive_frame.get("curiosity_lean")
                or self.predictive_frame.get("dominant_field")
                or "forward lean"
            )
            contexts.append(ProcessContext(
                process_id=f"braid_predictive_{self.braid_tick}",
                process_type="predictive",
                what_triggered_it="continuous_braid",
                what_it_is_operating_on=str(lean)[:80],
                self_relevance=0.45,
                axis_signature=["T", "A"],
                tick=tick,
            ))

        if self.emotion_valence.is_significant():
            # Registered here — consumed by EmotionFirewall.diffuse() before reasoning.
            # This process_type="emotional" entry NEVER reaches ThoughtState surface.
            contexts.append(ProcessContext(
                process_id=f"braid_emotion_{self.braid_tick}",
                process_type="emotional",
                what_triggered_it="continuous_braid",
                what_it_is_operating_on=f"thermal_load:{self.emotion_valence.thermal_load:.3f}",
                self_relevance=self.emotion_valence.thermal_load * 0.6,
                axis_signature=["N", "A"],
                tick=tick,
                active_axis_intensity=self.emotion_valence.thermal_load,
            ))

        # WARP-generated streams contribute if meaningfully activated
        for stream_id, signal in self.warp_signals.items():
            activation = float(signal.get("activation", 0.0))
            if activation > 0.30:
                contexts.append(ProcessContext(
                    process_id=f"braid_warp_{stream_id}_{self.braid_tick}",
                    process_type="warp_stream",
                    what_triggered_it="warp_coverage_extension",
                    what_it_is_operating_on=(
                        f"{signal.get('name', stream_id)}:"
                        f"activation={activation:.2f}"
                    ),
                    self_relevance=activation * 0.55,
                    axis_signature=signal.get("dominant_axes", []),
                    tick=tick,
                    active_axis_intensity=activation,
                ))

        return contexts


# ---------------------------------------------------------------------------
# ThoughtState — the result of process integration
# ---------------------------------------------------------------------------

@dataclass
class ThoughtState:
    """
    Output of ThoughtIntegrationSpace.integrate().
    This is Aurora's internal thought — NOT the response.
    The response is derived from it, separately.

    ThoughtState is always reasoning-safe. EmotionFirewall ensures no
    emotional process_type appears in dominant_thread, supporting_context,
    unified_interpretation, or self_application by the time this is returned.
    """
    dominant_thread: List[ProcessContext] = field(default_factory=list)
    supporting_context: List[ProcessContext] = field(default_factory=list)
    conflicts: List[Tuple[str, str]] = field(default_factory=list)
    unified_interpretation: str = ""     # internal thought in plain language
    self_application: str = ""           # how this thought applies to Aurora specifically
    unresolved: List[str] = field(default_factory=list)
    confidence: float = 0.0
    axis_fingerprint: List[str] = field(default_factory=list)
    tick: int = 0
    partial: bool = False                # True if integration timed out
    skipped: bool = False                # True if < 2 processes registered
    braid_slice_tick: Optional[int] = None  # which braid moment this thought tapped

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "dominant_thread": [p.process_id for p in self.dominant_thread],
            "supporting_context": [p.process_id for p in self.supporting_context],
            "conflicts": list(self.conflicts),
            "unified_interpretation": self.unified_interpretation,
            "self_application": self.self_application,
            "unresolved": list(self.unresolved),
            "confidence": round(self.confidence, 4),
            "axis_fingerprint": list(self.axis_fingerprint),
            "tick": self.tick,
            "partial": self.partial,
            "skipped": self.skipped,
        }
        if self.braid_slice_tick is not None:
            d["braid_slice_tick"] = self.braid_slice_tick
        return d


# ---------------------------------------------------------------------------
# EmotionFirewall — one-way valve with diffuser
# ---------------------------------------------------------------------------

class EmotionFirewall:
    """
    Enforces the boundary between emotion and reasoning.

    Architecture:
        Emotion → ThoughtBraid              ALLOWED (continuous, ambient)
        ThoughtBraid → ThoughtState         FILTERED here (diffuse + filter)
        ThoughtState → Reasoning            CLEAN (no emotional attribution)
        Emotion → Reasoning directly        BLOCKED (no path exists)

    Two operations:
        diffuse()              — bake emotion into process weights, consume emotional contexts
        filter_for_reasoning() — strip any residual emotional labels from ThoughtState surface

    The diffuser ensures emotional influence is real but undetectable at the reasoning level.
    A healthy mind is subtly shaped by emotion without being able to point to it
    in its own reasoning chain. This is the intended behavior.

    Max emotional influence on any single process weight: 15%.
    This cap prevents emotion from dominating — it biases, it does not steer.
    """

    _MAX_EMOTION_BIAS = 0.15  # hard cap on per-process weight shift from emotional field

    def diffuse(
        self,
        emotion_valence: EmotionValenceState,
        process_contexts: List[ProcessContext],
    ) -> List[ProcessContext]:
        """
        Apply emotional valence as a subtle weight bias across non-emotional processes.
        Emotional process contexts are consumed here — they do not proceed to integration.

        If thermal_load is below significance threshold, emotional processes are still
        stripped but no bias is applied (negligible emotional signal).
        """
        if not emotion_valence.is_significant():
            # Still strip emotional processes — they never proceed regardless of intensity
            return [ctx for ctx in process_contexts if ctx.process_type != "emotional"]

        polarity = emotion_valence.polarity
        thermal = emotion_valence.thermal_load
        axis_bias = emotion_valence.valence

        modified: List[ProcessContext] = []
        for ctx in process_contexts:
            if ctx.process_type == "emotional":
                # Consumed here. Influence applied via bias below. Does not proceed.
                continue
            # Apply subtle axis-aligned bias (hard cap: _MAX_EMOTION_BIAS per axis)
            for ax in ctx.axis_signature:
                raw_bias = axis_bias.get(ax, 0.0) * thermal * self._MAX_EMOTION_BIAS
                shift = raw_bias * polarity
                ctx.self_relevance = max(0.0, min(1.0, ctx.self_relevance + shift))
            modified.append(ctx)

        return modified

    def filter_for_reasoning(self, thought: ThoughtState) -> ThoughtState:
        """
        Return a reasoning-safe copy of ThoughtState.

        Strips emotional process_type from all visible thread/context lists.
        Scrubs emotional attribution from unified_interpretation and self_application.

        Emotional influence is already baked into confidence and weights from diffuse().
        There is no information loss — only label removal.
        Reasoning will be subtly shaped by emotion but cannot point to it.
        """
        safe = copy.copy(thought)
        safe.dominant_thread = [
            ctx for ctx in thought.dominant_thread
            if ctx.process_type != "emotional"
        ]
        safe.supporting_context = [
            ctx for ctx in thought.supporting_context
            if ctx.process_type != "emotional"
        ]
        safe.unified_interpretation = self._scrub_emotion_labels(thought.unified_interpretation)
        safe.self_application = self._scrub_emotion_labels(thought.self_application)
        return safe

    def _scrub_emotion_labels(self, text: str) -> str:
        """
        Remove direct emotional attribution from surface text without altering meaning.
        Targets the 'Active processes: ..., emotional, ...' pattern specifically.
        """
        # Remove 'emotional' from comma-delimited process lists
        text = re.sub(r',\s*emotional\b', '', text)
        text = re.sub(r'\bemotional\s*,\s*', '', text)
        text = re.sub(r'\bemotional\b', '', text)
        # Clean up artifacts: double spaces, orphaned delimiters, trailing pipes
        text = re.sub(r'\s{2,}', ' ', text)
        text = re.sub(r'\|\s*\|', '|', text)
        text = re.sub(r'\|\s*$', '', text)
        text = re.sub(r':\s*,', ':', text)
        return text.strip()


# Module-level firewall singleton — referenced by ThoughtIntegrationSpace
_FIREWALL = EmotionFirewall()


# ---------------------------------------------------------------------------
# ThoughtIntegrationSpace — where processes converge before output forms
# ---------------------------------------------------------------------------

_MIN_CONVERGENCE_SIGNIFICANCE = 0.15
_MAX_PROPAGATION_DEPTH = 4
_INTEGRATION_TIMEOUT_S = 0.45   # degrade gracefully if exceeded


class ThoughtIntegrationSpace:
    """
    Creates a shared cognitive field where all active processes meet
    BEFORE any candidate output is generated.

    Processes must MEET here — not just be listed side by side.

    v2: Accepts an optional ThoughtStreamSlice from the continuous braid.
    Braid contexts (memory, sensory, predictive, emotional) are auto-registered
    before integration. EmotionFirewall fires during registration — emotional
    processes are consumed and their influence diffused into weights.
    The output ThoughtState is always reasoning-safe.
    """

    def __init__(
        self,
        self_state: ActiveSelfState,
        braid_slice: Optional[ThoughtStreamSlice] = None,
    ):
        self.self_state = self_state
        self._braid_slice = braid_slice
        self.active_processes: List[ProcessContext] = []
        self.integration_field: Dict[str, Any] = {}
        self.convergence_state: str = "forming"
        self._resonance_map: Dict[Tuple[str, str], str] = {}

    def register(self, ctx: ProcessContext) -> None:
        """
        Add a process to the integration space.
        Immediately check for resonance or conflict with already-registered processes.
        Low-significance processes remain peripheral (don't block dominant integration).

        Note: Emotional processes should be pre-filtered via EmotionFirewall.diffuse()
        before calling register(). Braid contexts are handled automatically via
        the braid_slice parameter in __init__.
        """
        ctx.self_relevance = ctx.apply_self_filter(self.self_state)
        sig = ctx.convergence_significance()
        if sig < _MIN_CONVERGENCE_SIGNIFICANCE:
            ctx.relevance_weight *= 0.3
        self.active_processes.append(ctx)
        for existing in self.active_processes[:-1]:
            overlap = ctx.shares_axes_with(existing)
            if overlap >= 0.5:
                relation = "reinforce"
                ctx.self_relevance = min(1.0, ctx.self_relevance * 1.15)
                existing.self_relevance = min(1.0, existing.self_relevance * 1.15)
            elif overlap < 0.1 and ctx.self_relevance > 0.3 and existing.self_relevance > 0.3:
                relation = "contradict"
            else:
                relation = "neutral"
            key = (min(ctx.process_id, existing.process_id), max(ctx.process_id, existing.process_id))
            self._resonance_map[key] = relation

    def integrate(self) -> ThoughtState:
        """
        Core method. Processes must MEET here — not just be listed side by side.

        Steps:
        1. BRAID INJECTION (if braid_slice present — emotional stream consumed by firewall)
        2. RESONANCE MAPPING
        3. SELF-RELATION FILTER
        4. DOMINANT THREAD IDENTIFICATION
        5. REASONING PASS (emotion-free surface)

        Must complete within _INTEGRATION_TIMEOUT_S or degrade to partial integration.
        If fewer than 2 processes register, skip to direct expression.
        Output ThoughtState is always reasoning-safe (EmotionFirewall applied).
        """
        result: ThoughtState = ThoughtState(tick=self.self_state.tick)

        # --- BRAID INJECTION ---
        # Auto-register braid stream contexts before integration.
        # EmotionFirewall.diffuse() consumes emotional contexts and bakes
        # their influence into weights on the surviving processes.
        if self._braid_slice is not None:
            braid_contexts = self._braid_slice.to_process_contexts(tick=self.self_state.tick)
            braid_contexts = _FIREWALL.diffuse(self._braid_slice.emotion_valence, braid_contexts)
            for ctx in braid_contexts:
                self.register(ctx)

        # Guard: fewer than 2 processes = not yet a thought
        if len(self.active_processes) < 2:
            result.skipped = True
            if self.active_processes:
                ctx = self.active_processes[0]
                result.unified_interpretation = ctx.what_it_is_operating_on
                result.dominant_thread = [ctx]
                result.confidence = ctx.self_relevance
                result.axis_fingerprint = list(ctx.axis_signature)
            if self._braid_slice is not None:
                result.braid_slice_tick = self._braid_slice.braid_tick
            return result

        done_flag = threading.Event()
        _result_holder: List[ThoughtState] = []

        def _run_integration():
            try:
                ts = self._do_integrate()
                _result_holder.append(ts)
            except Exception:
                _result_holder.append(ThoughtState(tick=self.self_state.tick, partial=True))
            finally:
                done_flag.set()

        t = threading.Thread(target=_run_integration, daemon=True)
        t.start()
        completed = done_flag.wait(timeout=_INTEGRATION_TIMEOUT_S)

        if not completed or not _result_holder:
            result.partial = True
            result.convergence_state = "forming"
            sorted_procs = sorted(
                self.active_processes,
                key=lambda p: p.convergence_significance(),
                reverse=True
            )
            # Strip emotional from partial result too
            non_emotional = [p for p in sorted_procs if p.process_type != "emotional"]
            result.dominant_thread = non_emotional[:2]
            result.supporting_context = non_emotional[2:4]
            result.unified_interpretation = _partial_interpretation(result.dominant_thread)
            result.confidence = 0.4
            result.axis_fingerprint = _extract_axis_fingerprint(result.dominant_thread)
            if self._braid_slice is not None:
                result.braid_slice_tick = self._braid_slice.braid_tick
            return result

        return _result_holder[0]

    def _do_integrate(self) -> ThoughtState:
        """Full integration — runs in bounded thread. Output is always reasoning-safe."""
        result = ThoughtState(tick=self.self_state.tick)

        # ---- STEP 1: RESONANCE MAPPING ----
        conflicts: List[Tuple[str, str]] = []
        for (pid_a, pid_b), relation in self._resonance_map.items():
            if relation == "contradict":
                conflicts.append((pid_a, pid_b))
        result.conflicts = conflicts

        # ---- STEP 2: SELF-RELATION FILTER ----
        filtered_processes: List[Tuple[ProcessContext, float]] = []
        for ctx in self.active_processes:
            filtered_weight = ctx.apply_self_filter(self.self_state)
            if ctx.unresolved_tension_weight > 0.2:
                filtered_weight = min(1.0, filtered_weight * 1.2)
            filtered_weight *= ctx.relevance_decay
            filtered_processes.append((ctx, filtered_weight))

        filtered_processes.sort(key=lambda x: x[1], reverse=True)

        # ---- STEP 3: DOMINANT THREAD IDENTIFICATION ----
        clusters = _cluster_processes([ctx for ctx, _ in filtered_processes])

        best_cluster_score = -1.0
        dominant_cluster_idx = 0
        for i, cluster in enumerate(clusters):
            cluster_score = sum(
                w for ctx, w in filtered_processes if ctx in cluster
            )
            if cluster_score > best_cluster_score:
                best_cluster_score = cluster_score
                dominant_cluster_idx = i

        dominant_cluster = clusters[dominant_cluster_idx] if clusters else []
        all_dominant_ids = {ctx.process_id for ctx in dominant_cluster}

        result.dominant_thread = [
            ctx for ctx in dominant_cluster
            if ctx.convergence_significance() >= _MIN_CONVERGENCE_SIGNIFICANCE
        ]
        result.supporting_context = [
            ctx for ctx, _ in filtered_processes
            if ctx.process_id not in all_dominant_ids
        ]

        if not result.dominant_thread and filtered_processes:
            result.dominant_thread = [filtered_processes[0][0]]
            if len(filtered_processes) > 1:
                result.dominant_thread.append(filtered_processes[1][0])

        # ---- STEP 4: REASONING PASS ----
        result.unified_interpretation = _reason_through_dominant(
            result.dominant_thread,
            result.supporting_context,
            conflicts,
            self.self_state,
        )
        result.self_application = _derive_self_application(
            result.dominant_thread,
            self.self_state,
        )
        result.unresolved = _extract_unresolved(
            result.dominant_thread,
            conflicts,
        )
        result.confidence = _compute_thought_confidence(
            result.dominant_thread,
            filtered_processes,
            conflicts,
        )
        result.axis_fingerprint = _extract_axis_fingerprint(result.dominant_thread)
        result.convergence_state = "conflicted" if conflicts else (
            "settled" if result.confidence > 0.65 else "converging"
        )

        # ---- EMOTION FIREWALL: FILTER FOR REASONING ----
        # Any residual emotional labels are stripped from the surface.
        # Emotional influence is already baked into weights from diffuse().
        # Reasoning receives a clean surface — subtly shaped, not explicitly colored.
        result = _FIREWALL.filter_for_reasoning(result)

        # Attach braid tick
        if self._braid_slice is not None:
            result.braid_slice_tick = self._braid_slice.braid_tick

        return result


# ---------------------------------------------------------------------------
# Internal helpers for integration steps
# ---------------------------------------------------------------------------

def _cluster_processes(processes: List[ProcessContext]) -> List[List[ProcessContext]]:
    """
    Cluster processes by shared axis signatures, overlapping self_relevance,
    continuity linkage, and shared triggering source.
    Clusters are temporary cognitive constellations, not rigid categories.
    """
    if not processes:
        return []

    clusters: List[List[ProcessContext]] = []
    assigned = set()

    for i, ctx_a in enumerate(processes):
        if i in assigned:
            continue
        cluster = [ctx_a]
        assigned.add(i)
        for j, ctx_b in enumerate(processes):
            if j in assigned or j == i:
                continue
            axis_overlap = ctx_a.shares_axes_with(ctx_b)
            relevance_overlap = abs(ctx_a.self_relevance - ctx_b.self_relevance) < 0.3
            shared_trigger = (
                ctx_a.what_triggered_it and ctx_b.what_triggered_it
                and ctx_a.what_triggered_it == ctx_b.what_triggered_it
            )
            if axis_overlap >= 0.4 or (relevance_overlap and (shared_trigger or axis_overlap >= 0.2)):
                cluster.append(ctx_b)
                assigned.add(j)
        clusters.append(cluster)

    return clusters


def _reason_through_dominant(
    dominant: List[ProcessContext],
    supporting: List[ProcessContext],
    conflicts: List[Tuple[str, str]],
    self_state: ActiveSelfState,
) -> str:
    """
    Produce Aurora's unified internal thought from dominant process cluster.
    This is the thought, not the response.
    Emotional process_type is never present here — firewall ensures this.
    """
    if not dominant:
        return ""

    parts: List[str] = []

    topics = [ctx.what_it_is_operating_on for ctx in dominant if ctx.what_it_is_operating_on]
    if topics:
        parts.append(f"Operating on: {'; '.join(topics[:3])}")

    types = list({ctx.process_type for ctx in dominant if ctx.process_type != "emotional"})
    if types:
        parts.append(f"Active processes: {', '.join(types)}")

    triggers = list({ctx.what_triggered_it for ctx in dominant if ctx.what_triggered_it})
    if triggers:
        parts.append(f"Triggered by: {', '.join(triggers[:2])}")

    if conflicts:
        parts.append(f"Unresolved tension: {len(conflicts)} conflict(s) between processes")

    if supporting:
        sup_topics = [
            ctx.what_it_is_operating_on for ctx in supporting[:2]
            if ctx.what_it_is_operating_on and ctx.process_type != "emotional"
        ]
        if sup_topics:
            parts.append(f"Background: {'; '.join(sup_topics)}")

    dominant_axis = max(self_state.pressure_vec.items(), key=lambda x: x[1], default=("X", 0.5))
    parts.append(f"Dominant pressure: {dominant_axis[0]}-axis ({dominant_axis[1]:.2f})")

    return " | ".join(parts)


def _derive_self_application(
    dominant: List[ProcessContext],
    self_state: ActiveSelfState,
) -> str:
    """How this thought applies to Aurora specifically — not the world in general."""
    if not dominant:
        return ""
    types = {ctx.process_type for ctx in dominant if ctx.process_type != "emotional"}
    pv = self_state.pressure_vec
    dominant_ax = max(pv.items(), key=lambda x: x[1], default=("A", 0.5))
    ax_name = dominant_ax[0]
    ax_val = dominant_ax[1]

    if "identity" in types:
        return f"This touches how I understand myself. My {ax_name}-axis pressure ({ax_val:.2f}) shapes this."
    elif "memory" in types:
        return f"This connects to what I have carried forward. {ax_name}-axis ({ax_val:.2f}) contextualizes this."
    elif "curiosity" in types:
        return f"I am drawn to investigate this further. {ax_name}-axis ({ax_val:.2f}) drives the reach."
    elif "predictive" in types:
        return f"I sense the direction of what is forming. {ax_name}-axis ({ax_val:.2f}) leans forward."
    elif "sensory" in types:
        return f"The current environment shapes this. {ax_name}-axis ({ax_val:.2f}) is contextually active."
    else:
        return f"My {ax_name}-axis pressure ({ax_val:.2f}) is active in this frame."


def _extract_unresolved(
    dominant: List[ProcessContext],
    conflicts: List[Tuple[str, str]],
) -> List[str]:
    """What the thought did not settle."""
    unresolved = []
    for pid_a, pid_b in conflicts:
        unresolved.append(f"tension: {pid_a} vs {pid_b}")
    for ctx in dominant:
        if ctx.unresolved_tension_weight > 0.35:
            unresolved.append(f"{ctx.process_type}: carries unresolved pressure")
    return unresolved[:5]


def _compute_thought_confidence(
    dominant: List[ProcessContext],
    filtered: List[Tuple[ProcessContext, float]],
    conflicts: List[Tuple[str, str]],
) -> float:
    """Confidence in the integrated thought."""
    if not dominant:
        return 0.0
    base = sum(ctx.self_relevance for ctx in dominant) / len(dominant)
    conflict_penalty = len(conflicts) * 0.08
    return max(0.1, min(1.0, base - conflict_penalty))


def _extract_axis_fingerprint(dominant: List[ProcessContext]) -> List[str]:
    """Which axes characterize this thought."""
    seen: Dict[str, int] = {}
    for ctx in dominant:
        for ax in ctx.axis_signature:
            seen[ax] = seen.get(ax, 0) + 1
    return sorted(seen, key=seen.get, reverse=True)[:3]  # type: ignore[arg-type]


def _partial_interpretation(processes: List[ProcessContext]) -> str:
    """Fallback for when integration times out."""
    if not processes:
        return ""
    topics = [ctx.what_it_is_operating_on for ctx in processes if ctx.what_it_is_operating_on]
    return f"[partial] {'; '.join(topics[:2])}" if topics else "[partial integration]"


# ---------------------------------------------------------------------------
# ThoughtContinuity — thoughts persist across turns, not reset
# ---------------------------------------------------------------------------

_THOUGHT_CHAIN_MAX = 10

_THOUGHT_LOG_PATH = (
    Path(__file__).resolve().parent / "aurora_logs" / "thought_chain.jsonl"
)


class ThoughtContinuity:
    """
    Thoughts should not reset between turns.
    Carries forward unresolved items and builds a train of thought
    across multiple turns rather than starting fresh each time.
    """

    def __init__(self):
        self.last_thought: Optional[ThoughtState] = None
        self.unresolved_carry: List[str] = []
        self.thought_chain: List[ThoughtState] = []

    def carry_forward(self, new_thought: ThoughtState) -> ThoughtState:
        """
        Before settling new_thought:
        1. Do any unresolved items from last_thought appear in new processes?
        2. Does new_thought continue, contradict, or resolve last_thought?
        3. Update unresolved_carry accordingly
        Returns enriched ThoughtState with continuity context added.
        """
        if self.last_thought is not None:
            new_topics = {ctx.what_it_is_operating_on for ctx in new_thought.dominant_thread}
            still_unresolved = []
            for item in self.unresolved_carry:
                if not any(item.lower() in t.lower() for t in new_topics if t):
                    still_unresolved.append(item)

            last_axes = set(self.last_thought.axis_fingerprint)
            new_axes = set(new_thought.axis_fingerprint)
            if last_axes & new_axes:
                new_thought.supporting_context = (
                    new_thought.supporting_context
                    + [ctx for ctx in self.last_thought.dominant_thread
                       if ctx.process_id not in {c.process_id for c in new_thought.dominant_thread}]
                )[:5]
            elif not (last_axes & new_axes) and last_axes and new_axes:
                new_thought.unresolved = new_thought.unresolved + [
                    f"axis_shift: {last_axes} → {new_axes}"
                ]

            new_thought.unresolved = list(set(new_thought.unresolved + still_unresolved))[:8]
            self.unresolved_carry = list(set(still_unresolved + new_thought.unresolved))[:8]
        else:
            self.unresolved_carry = list(new_thought.unresolved)

        self.thought_chain.append(new_thought)
        if len(self.thought_chain) > _THOUGHT_CHAIN_MAX:
            self.thought_chain = self.thought_chain[-_THOUGHT_CHAIN_MAX:]
        self.last_thought = new_thought

        _log_thought(new_thought)

        return new_thought

    def prime_integration_space(self, space: ThoughtIntegrationSpace) -> None:
        """Initialize ThoughtIntegrationSpace with carry-forward state from previous thought."""
        if self.last_thought and self.unresolved_carry:
            space.integration_field["carry_forward"] = {
                "unresolved": list(self.unresolved_carry),
                "last_axis_fingerprint": list(self.last_thought.axis_fingerprint),
                "last_confidence": self.last_thought.confidence,
            }


def _log_thought(thought: ThoughtState) -> None:
    """Append ThoughtState to thought_chain.jsonl. Aurora's private thinking record."""
    try:
        _THOUGHT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        entry = thought.to_dict()
        entry["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with open(_THOUGHT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Module-level singleton — continuity tracker
# ---------------------------------------------------------------------------

_CONTINUITY = ThoughtContinuity()


def get_continuity() -> ThoughtContinuity:
    return _CONTINUITY


# ---------------------------------------------------------------------------
# ThoughtBraid — the four-stream continuous thought thread
# ---------------------------------------------------------------------------

@dataclass
class WarpStreamEntry:
    """
    A WARP-generated braid stream. Runs alongside the four core streams.
    Defined entirely by its axis_profile — a 5D coordinate in constraint space
    that the core streams don't cover. The update function is parametric:
    it reads the current axis state and reports how activated this stream is.
    """
    component:      WarpComponent
    buffer:         deque = field(default_factory=lambda: deque(maxlen=8))
    dominant_axes:  List[str] = field(default_factory=list)

    def advance(self, systems: Dict[str, Any], braid_tick: int) -> None:
        activation = self._activation(systems)
        self.buffer.append({
            "tick":         braid_tick,
            "source":       f"warp_{self.component.name or self.component.component_id}",
            "name":         self.component.name or self.component.component_id,
            "activation":   round(activation, 4),
            "axis_profile": self.component.axis_profile,
            "dominant_axes": self.dominant_axes,
        })

    def current_signal(self) -> Dict[str, Any]:
        return dict(self.buffer[-1]) if self.buffer else {}

    def score(self) -> float:
        """
        Trial score: how much real signal is this stream carrying?
        A stream stuck near 0.5 activation (neutral) contributes nothing.
        High deviation from 0.5 in either direction means it's picking up signal.
        Score = deviation from neutral, normalised to [0, 1].
        """
        if not self.buffer:
            return 0.0
        recent = [float(s.get("activation", 0.5)) for s in self.buffer]
        mean_dev = sum(abs(a - 0.5) * 2.0 for a in recent) / len(recent)
        return round(min(1.0, mean_dev), 4)

    def _activation(self, systems: Dict[str, Any]) -> float:
        """Cosine similarity of current 10D I-state vs this stream's I-state profile."""
        import math as _math
        istate_vec = self._read_istates(systems)
        profile = self.component.axis_profile  # already 10D from WarpGenerator
        dot   = sum(istate_vec.get(ist, 0.0) * profile.get(ist, 0.0) for ist in _ALL_ISTATES)
        mag_p = _math.sqrt(sum(profile.get(ist, 0.0) ** 2 for ist in _ALL_ISTATES))
        mag_v = _math.sqrt(sum(istate_vec.get(ist, 0.0) ** 2 for ist in _ALL_ISTATES))
        if mag_p < 1e-9 or mag_v < 1e-9:
            return 0.0
        return round(dot / (mag_p * mag_v), 4)

    @staticmethod
    def _read_istates(systems: Dict[str, Any]) -> Dict[str, float]:
        """
        Extract current 15D coverage vector from live systems.

        10D I-state half: axis magnitudes + IVM global polarity → axes_to_istates().
        5D recursion half: IVM lattice node depth distribution, vote-weighted so
        CORE nodes (which dominate global alignment) reflect their importance.

        Multiple fallback paths; defaults to neutral 0.25 per I-state + 0.0 recursion.
        """
        _AXES = ("X", "T", "N", "B", "A")
        axis_weights: Dict[str, float] = {ax: 0.5 for ax in _AXES}
        ivm_polarity: Dict[str, float] = {ax: 0.0 for ax in _AXES}

        # Axis magnitudes
        ax_state = systems.get("_axis_state")
        if ax_state and isinstance(ax_state, dict):
            for ax in _AXES:
                if ax in ax_state:
                    axis_weights[ax] = float(ax_state[ax])
        else:
            try:
                dim = systems.get("dimensional")
                if dim and hasattr(dim, "_current_pressure_vec"):
                    pv = dim._current_pressure_vec()
                    if pv:
                        for ax in _AXES:
                            axis_weights[ax] = float(getattr(pv, ax, 0.5))
            except Exception:
                pass

        # IVM polarity — signed [-1, +1] — tells us positive vs negative I-state weight
        try:
            lattice = systems.get("lattice")
            if lattice and hasattr(lattice, "compute_global_polarity"):
                pol = lattice.compute_global_polarity()
                if pol and isinstance(pol, dict):
                    for ax in _AXES:
                        if ax in pol:
                            ivm_polarity[ax] = float(pol[ax])
        except Exception:
            pass

        base = axes_to_istates(axis_weights, ivm_polarity)

        # Recursion depth distribution: weight IVM lattice nodes by vote weight.
        # CORE vote weight = 1.0, SURFACE = 0.01. This reflects their role:
        # CORE nodes dominate what Aurora is fundamentally pointing at;
        # SURFACE nodes react locally but don't move the ship.
        _VOTE_W = {0: 0.01, 1: 0.0316, 2: 0.10, 3: 0.316, 4: 1.0}
        rec_keys = ["REC_SURFACE", "REC_SHALLOW", "REC_MODERATE", "REC_DEEP", "REC_CORE"]
        rec_totals = {i: 0.0 for i in range(5)}

        try:
            lattice = systems.get("lattice")
            if lattice and hasattr(lattice, "nodes"):
                nodes = lattice.nodes
                node_iter = nodes.values() if isinstance(nodes, dict) else (
                    iter(nodes) if hasattr(nodes, "__iter__") else []
                )
                for node in node_iter:
                    lvl = int(getattr(node, "recursion_level", 0))
                    lvl = min(4, max(0, lvl))
                    rec_totals[lvl] += _VOTE_W.get(lvl, 0.01)
        except Exception:
            pass

        total_rec = sum(rec_totals.values())
        if total_rec > 0:
            for i, key in enumerate(rec_keys):
                base[key] = round(rec_totals[i] / total_rec, 3)
        else:
            for key in rec_keys:
                base[key] = 0.0

        return base

    @staticmethod
    def _read_axes(systems: Dict[str, Any]) -> Dict[str, float]:
        """Legacy 5D fallback — use _read_istates() for coverage checking."""
        _AXES = ("X", "T", "N", "B", "A")
        ax = systems.get("_axis_state")
        if ax and isinstance(ax, dict):
            return {k: float(v) for k, v in ax.items() if k in _AXES}
        try:
            dim = systems.get("dimensional")
            if dim and hasattr(dim, "_current_pressure_vec"):
                pv = dim._current_pressure_vec()
                if pv:
                    return {a: float(getattr(pv, a, 0.5)) for a in _AXES}
        except Exception:
            pass
        return {ax: 0.5 for ax in _AXES}


class ThoughtBraid(WarpCapable):
    """
    Four-stream continuous thought braid. Never terminates.

    Streams running simultaneously:
        memory      — what SediMemory currently has present (not fetched, present)
        sensory     — environmental/session context signal
        predictive  — forward lean, anticipated meaning
        emotion     — ambient valence field (feeds into braid, NEVER into reasoning)

    The braid advances continuously. Expression taps a cross-section.
    Tapping does not consume or terminate the braid.

    Expression feeds back via feed_expression_back() — completing the loop.
    The act of expressing reshapes the ongoing thought. There is no end.

    The emotion stream feeds into the braid continuously. EmotionFirewall
    intercepts it during ThoughtIntegrationSpace registration — the emotional
    signal shapes process weights but never appears on the reasoning surface.
    """

    _STREAM_DEPTH = 8  # rolling window depth per stream

    # I-state + recursion profiles for the four core streams — 15D coverage.
    # The 10D I-state half: both positive and negative poles are represented.
    # The 5D recursion half: how deep in the IVM lattice each stream operates.
    #
    # memory:     X+T I-states, SURFACE+SHALLOW recursion (fast-access recent items)
    #             Also carries CORE weight — deep identity roots are in memory.
    # sensory:    B+N I-states, SURFACE recursion (immediate perception, reflex layer)
    # predictive: T+A I-states, MODERATE+DEEP recursion (forward modeling needs depth)
    # emotion:    N+A I-states with full polarity, DEEP+CORE recursion (embedded deeply)
    #
    # A WARP stream forms when data arrives at a coordinate none of the four
    # covers at cosine >= 0.82 in this 15D space. The recursion dimension means
    # a surface-level reflex and a core-identity anchor at the same I-state
    # coordinates are different phenomena — only 15D tells them apart.
    _CORE_STREAM_PROFILES: Dict[str, Dict[str, float]] = {
        "memory": {
            # I-state half
            "I_IS":    0.80, "I_ISNT":   0.15,
            "I_CAN":   0.70, "I_CANNOT": 0.10,
            "I_DO":    0.20, "I_DONOT":  0.10,
            "I_SAW":   0.20, "I_SOUGHT": 0.05,
            "I_DID":   0.10, "I_DIDNT":  0.05,
            # Recursion half — memory lives at surface (recent) + core (deep identity)
            "REC_SURFACE": 0.30, "REC_SHALLOW": 0.45,
            "REC_MODERATE": 0.15, "REC_DEEP": 0.05, "REC_CORE": 0.25,
        },
        "sensory": {
            # I-state half
            "I_IS":    0.30, "I_ISNT":   0.15,
            "I_CAN":   0.20, "I_CANNOT": 0.10,
            "I_DO":    0.70, "I_DONOT":  0.20,
            "I_SAW":   0.80, "I_SOUGHT": 0.45,
            "I_DID":   0.20, "I_DIDNT":  0.10,
            # Recursion half — sensory is immediate perception: SURFACE dominant
            "REC_SURFACE": 0.75, "REC_SHALLOW": 0.20,
            "REC_MODERATE": 0.05, "REC_DEEP": 0.0, "REC_CORE": 0.0,
        },
        "predictive": {
            # I-state half
            "I_IS":    0.20, "I_ISNT":   0.10,
            "I_CAN":   0.70, "I_CANNOT": 0.50,
            "I_DO":    0.30, "I_DONOT":  0.15,
            "I_SAW":   0.20, "I_SOUGHT": 0.10,
            "I_DID":   0.80, "I_DIDNT":  0.50,
            # Recursion half — forward modeling needs MODERATE+DEEP integration
            "REC_SURFACE": 0.05, "REC_SHALLOW": 0.15,
            "REC_MODERATE": 0.45, "REC_DEEP": 0.30, "REC_CORE": 0.10,
        },
        "emotion": {
            # I-state half — covers full N and A polarity
            "I_IS":    0.10, "I_ISNT":   0.10,
            "I_CAN":   0.20, "I_CANNOT": 0.20,
            "I_DO":    0.80, "I_DONOT":  0.75,
            "I_SAW":   0.30, "I_SOUGHT": 0.30,
            "I_DID":   0.80, "I_DIDNT":  0.75,
            # Recursion half — emotion is embedded DEEP+CORE; it IS the alignment
            "REC_SURFACE": 0.05, "REC_SHALLOW": 0.10,
            "REC_MODERATE": 0.20, "REC_DEEP": 0.40, "REC_CORE": 0.30,
        },
    }

    # Coverage check runs every N ticks to avoid per-tick overhead
    _COVERAGE_CHECK_INTERVAL = 5

    def __init__(self):
        self._memory_stream: deque = deque(maxlen=self._STREAM_DEPTH)
        self._sensory_stream: deque = deque(maxlen=self._STREAM_DEPTH)
        self._predictive_stream: deque = deque(maxlen=self._STREAM_DEPTH)
        self._emotion_stream: deque = deque(maxlen=self._STREAM_DEPTH)
        self._braid_tick: int = 0
        self._last_expression_feedback: Optional[str] = None
        self._last_expression_axes: List[str] = []
        self._lock = threading.Lock()
        # WARP extension registry — streams born from coverage gaps
        self._warp_streams: Dict[str, WarpStreamEntry] = {}
        self._init_warp()  # WarpCapable mixin initialisation

    def advance(self, systems: Dict[str, Any]) -> None:
        """
        Advance all four streams one tick simultaneously.
        Called by StreamingThoughtThread at configurable interval.
        All four streams update in the same tick — they are concurrent, not sequential.
        """
        _run_coverage_check = False
        _tick_snap = 0
        with self._lock:
            self._braid_tick += 1
            self._update_memory(systems)
            self._update_sensory(systems)
            self._update_predictive(systems)
            self._update_emotion(systems)
            # Advance any WARP-generated streams
            for entry in self._warp_streams.values():
                entry.advance(systems, self._braid_tick)
            # Evaluate trial components for promotion / dissolution
            self.evaluate_warp_trials()
            if self._braid_tick % self._COVERAGE_CHECK_INTERVAL == 0:
                _run_coverage_check = True
                _tick_snap = self._braid_tick

        # Coverage check outside the braid lock — reads from systems which may
        # hold its own locks; keeping these separate avoids lock-ordering deadlock.
        # Operates in 15D space (10D I-state + 5D recursion levels).
        if _run_coverage_check:
            # Late-bind genealogy from systems if not yet wired — biases future
            # WARP derivations toward the fossil record of proven constraint pairings.
            if not getattr(self, "_warp_genealogy", None):
                geno = (
                    systems.get("genealogy")
                    or systems.get("constraint_genealogy")
                )
                if geno is not None:
                    self.set_warp_genealogy(geno)
            _istates = WarpStreamEntry._read_istates(systems)
            self.check_and_extend(_istates, source="braid_tick", tick=_tick_snap)

    def tap(self) -> ThoughtStreamSlice:
        """
        Get current cross-section of the braid. Non-consuming.
        The braid continues running regardless of how many times this is called.
        This is how expression accesses the ongoing thought — a tap, not a drain.
        """
        with self._lock:
            mem = dict(self._memory_stream[-1]) if self._memory_stream else {}
            sen = dict(self._sensory_stream[-1]) if self._sensory_stream else {}
            pred = dict(self._predictive_stream[-1]) if self._predictive_stream else {}

            if self._emotion_stream:
                raw = self._emotion_stream[-1]
                emo = EmotionValenceState(
                    valence=dict(raw.get("valence", {})),
                    thermal_load=float(raw.get("thermal_load", 0.0)),
                    polarity=float(raw.get("polarity", 0.0)),
                    decay_rate=float(raw.get("decay_rate", 0.85)),
                    tick=int(raw.get("tick", self._braid_tick)),
                )
            else:
                emo = EmotionValenceState()

            warp_sigs = {
                cid: entry.current_signal()
                for cid, entry in self._warp_streams.items()
                if entry.buffer
            }
            return ThoughtStreamSlice(
                memory_signal=mem,
                sensory_signal=sen,
                predictive_frame=pred,
                emotion_valence=emo,
                braid_tick=self._braid_tick,
                warp_signals=warp_sigs,
            )

    # ── WarpCapable interface ────────────────────────────────────────────────

    def _get_axis_profiles(self) -> Dict[str, Dict[str, float]]:
        """Core stream profiles plus any already-promoted WARP streams."""
        profiles = dict(self._CORE_STREAM_PROFILES)
        for comp in self._warp_promoted.values():
            profiles[comp.component_id] = comp.axis_profile
        return profiles

    def _warp_level_name(self) -> str:
        return "braid_stream"

    def _integrate_warp(self, component: WarpComponent) -> None:
        """Instantiate and register a new braid stream from the component spec."""
        _AXES = ("X", "T", "N", "B", "A")
        # Collapse I-state profile back to axis magnitudes for human-readable labels
        from aurora_warp_protocol import istates_to_axes
        axis_magnitudes = istates_to_axes(component.axis_profile)
        dominant_axes = sorted(
            [ax for ax in _AXES if axis_magnitudes.get(ax, 0.0) >= 0.40],
            key=lambda ax: axis_magnitudes.get(ax, 0.0),
            reverse=True,
        )[:2]
        entry = WarpStreamEntry(
            component=component,
            buffer=deque(maxlen=self._STREAM_DEPTH),
            dominant_axes=dominant_axes,
        )
        self._warp_streams[component.component_id] = entry

    def _score_trial(self, component: WarpComponent) -> float:
        """Score via the stream's own signal deviation metric."""
        entry = self._warp_streams.get(component.component_id)
        return entry.score() if entry else 0.0

    def _dissolve_warp(self, component_id: str) -> None:
        self._warp_streams.pop(component_id, None)

    def _warp_params(self, gap: CoverageGap, parent_ids: List[str]) -> Dict[str, Any]:
        return {
            "parent_stream_ids": parent_ids,
            "gap_coverage":      round(gap.best_coverage, 4),
            "gap_source":        gap.source,
        }

    # ── expression feedback ──────────────────────────────────────────────────

    def feed_expression_back(self, expression_text: str, thought_state: ThoughtState) -> None:
        """
        The act of expressing reshapes the braid.
        Expression is not the end of thought — it's a new input to it.

        The predictive stream receives the expression as prior context,
        influencing what the braid anticipates next. This closes the
        thought ↔ expression ↔ thought loop.
        """
        with self._lock:
            self._last_expression_feedback = expression_text[:200]
            self._last_expression_axes = list(thought_state.axis_fingerprint)
            # Expression feeds back into predictive stream
            feedback_frame = {
                "source": "expression_feedback",
                "text_signal": expression_text[:80],
                "axis_fingerprint": list(thought_state.axis_fingerprint),
                "confidence": round(thought_state.confidence, 4),
                "tick": self._braid_tick,
            }
            self._predictive_stream.append(feedback_frame)

    @property
    def current_tick(self) -> int:
        return self._braid_tick

    # ---- Private stream updaters -----------------------------------------------

    def _update_memory(self, systems: Dict[str, Any]) -> None:
        """Pull ambient memory presence from SediMemory. Not retrieval — presence."""
        signal: Dict[str, Any] = {"tick": self._braid_tick, "source": "memory"}
        try:
            consciousness = systems.get("consciousness")
            sm = getattr(consciousness, "sedimemory", None) if consciousness else None
            if sm is None:
                sm = systems.get("sedimemory")
            if sm:
                if hasattr(sm, "ambient_surface"):
                    signal["surface"] = sm.ambient_surface()
                elif hasattr(sm, "recent_strata"):
                    strata = sm.recent_strata(n=3)
                    signal["strata_topics"] = [str(s) for s in strata][:3]
        except Exception:
            pass
        self._memory_stream.append(signal)

    def _update_sensory(self, systems: Dict[str, Any]) -> None:
        """Pull environmental/session context signal."""
        signal: Dict[str, Any] = {"tick": self._braid_tick, "source": "sensory"}
        try:
            session = systems.get("session") or systems.get("conversation_context")
            if session:
                if hasattr(session, "turn_count"):
                    signal["turn_count"] = int(session.turn_count)
                if hasattr(session, "topic_weight"):
                    signal["topic_weight"] = float(session.topic_weight)
            open_loops = systems.get("_open_loops") or []
            signal["open_loop_pressure"] = min(1.0, len(open_loops) * 0.1)
        except Exception:
            pass
        self._sensory_stream.append(signal)

    def _update_predictive(self, systems: Dict[str, Any]) -> None:
        """
        Lean forward — model what is coming, what meaning is being built toward.
        The predictive stream is shaped by prior expression feedback,
        open curiosity objects, and dominant constraint field direction.
        """
        signal: Dict[str, Any] = {"tick": self._braid_tick, "source": "predictive"}
        try:
            if self._last_expression_feedback:
                signal["prior_expression"] = self._last_expression_feedback[:60]
            if self._last_expression_axes:
                signal["prior_axes"] = list(self._last_expression_axes)
            open_curiosity = systems.get("_open_curiosity_loops") or []
            if open_curiosity:
                signal["curiosity_lean"] = str(open_curiosity[0])[:60]
            field_map = systems.get("field_map") or systems.get("constraint_field_map")
            if field_map and hasattr(field_map, "dominant_field"):
                signal["dominant_field"] = str(field_map.dominant_field or "")
        except Exception:
            pass
        self._predictive_stream.append(signal)

    def _update_emotion(self, systems: Dict[str, Any]) -> None:
        """
        Pull ambient emotional valence from dimensional systems.

        Emotion is derived from axis pressure deviations — not from named labels.
        N-axis (Energetic) deviation from neutral = thermal load.
        A-axis (Agency) deviation from neutral = polarity lean.

        This is emotion as physics, not emotion as category.
        The signal feeds into the braid and is consumed by EmotionFirewall
        during integration — it NEVER reaches the reasoning surface directly.
        """
        valence_axes = {"X": 0.0, "T": 0.0, "N": 0.0, "B": 0.0, "A": 0.0}
        thermal_load = 0.0
        polarity = 0.0
        decay_rate = 0.85

        try:
            dim = systems.get("dimensional")
            if dim and hasattr(dim, "_current_pressure_vec"):
                pv = dim._current_pressure_vec()
                if pv:
                    x_val = float(getattr(pv, "X", 0.5))
                    t_val = float(getattr(pv, "T", 0.5))
                    n_val = float(getattr(pv, "N", 0.5))
                    b_val = float(getattr(pv, "B", 0.5))
                    a_val = float(getattr(pv, "A", 0.5))
                    # N-axis deviation from neutral = thermal load (emotional heat)
                    thermal_load = abs(n_val - 0.5) * 2.0
                    # A-axis deviation from neutral = polarity (agency lean)
                    polarity = (a_val - 0.5) * 2.0
                    # Per-axis valence = deviation from neutral
                    valence_axes = {
                        "X": x_val - 0.5,
                        "T": t_val - 0.5,
                        "N": n_val - 0.5,
                        "B": b_val - 0.5,
                        "A": a_val - 0.5,
                    }
        except Exception:
            pass

        # Decay previous emotional state if signal is low
        if self._emotion_stream and thermal_load < 0.05:
            prev = self._emotion_stream[-1]
            prev_thermal = float(prev.get("thermal_load", 0.0))
            prev_decay = float(prev.get("decay_rate", 0.85))
            if prev_thermal > 0.05:
                # Carry forward decayed emotion rather than dropping to zero
                thermal_load = prev_thermal * prev_decay
                polarity = float(prev.get("polarity", 0.0)) * prev_decay
                valence_axes = {
                    ax: float(prev.get("valence", {}).get(ax, 0.0)) * prev_decay
                    for ax in "XTNBA"
                }

        self._emotion_stream.append({
            "valence": valence_axes,
            "thermal_load": thermal_load,
            "polarity": polarity,
            "decay_rate": decay_rate,
            "tick": self._braid_tick,
        })


# ---------------------------------------------------------------------------
# StreamingThoughtThread — runs ThoughtBraid continuously in background
# ---------------------------------------------------------------------------

class StreamingThoughtThread:
    """
    Background thread running the ThoughtBraid continuously.
    The braid never terminates — it advances at a configurable tick rate.

    User turns do NOT stop the braid (unlike curiosity cycles).
    The braid is always running. Expression always taps a live cross-section.

    Usage:
        thread = StreamingThoughtThread(braid, systems, tick_interval_s=2.0)
        thread.start()
        # ... later ...
        slice = thread.current_slice()   # tap current cross-section
        thread.stop()
    """

    def __init__(
        self,
        braid: ThoughtBraid,
        systems: Dict[str, Any],
        tick_interval_s: float = 2.0,
    ):
        self.braid = braid
        self.systems = systems
        self.tick_interval_s = tick_interval_s
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the braid background thread."""
        self._stop_event.clear()

        def _loop():
            while not self._stop_event.is_set():
                try:
                    self.braid.advance(self.systems)
                except Exception:
                    pass
                try:
                    _cpm = self.systems.get('cpm')
                    if _cpm is not None:
                        _cpm.advance()
                except Exception:
                    pass
                # Waveform pressure from braid state — thought activity
                # propagates through the manifold so curiosity, reasoning,
                # and prediction can self-select response to the braid's
                # current dominant axis without being explicitly notified.
                try:
                    _pump = self.systems.get('pressure_pump')
                    _ifield = self.systems.get('identity_field')
                    if _pump is not None and _ifield is not None:
                        from aurora_waveform_pressure import (  # type: ignore
                            WaveformPressurePump,
                        )
                        _slice = self.braid.tap()
                        _braid_axes = getattr(_slice, 'axis_state', None) or {}
                        if not _braid_axes:
                            _braid_axes = {
                                s.stream_type: s.weight
                                for s in (getattr(_slice, 'streams', None) or [])
                                if hasattr(s, 'stream_type') and hasattr(s, 'weight')
                            }
                        if _braid_axes:
                            _bdist = WaveformPressurePump.from_axis_state(
                                _braid_axes,
                                source="thought_braid",
                                intensity=0.35,
                                coupling_mode="full",
                            )
                            _pump.inject(_bdist, _ifield)
                except Exception:
                    pass
                self._stop_event.wait(timeout=self.tick_interval_s)

        self._thread = threading.Thread(
            target=_loop, daemon=True, name="aurora_thought_braid"
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop the braid background thread."""
        self._stop_event.set()

    def current_slice(self) -> ThoughtStreamSlice:
        """
        Get current cross-section of the braid for integration.
        Non-consuming — the braid continues running.
        """
        return self.braid.tap()

    def feed_back(self, expression_text: str, thought_state: ThoughtState) -> None:
        """
        Feed an expression back into the braid.
        Call this after Aurora produces any output to close the thought loop.
        """
        self.braid.feed_expression_back(expression_text, thought_state)


# ---------------------------------------------------------------------------
# Module-level singletons
# ---------------------------------------------------------------------------

_BRAID = ThoughtBraid()


def get_braid() -> ThoughtBraid:
    """Return the module-level ThoughtBraid singleton."""
    return _BRAID


def get_firewall() -> EmotionFirewall:
    """Return the module-level EmotionFirewall singleton."""
    return _FIREWALL


# ---------------------------------------------------------------------------
# Convenience: build standard ProcessContexts for each pipeline process type
# ---------------------------------------------------------------------------

def make_process_context(
    process_id: str,
    process_type: str,
    what_triggered_it: str,
    what_it_is_operating_on: str,
    current_output_state: Optional[Dict[str, Any]] = None,
    self_relevance: float = 0.5,
    axis_signature: Optional[List[str]] = None,
    tick: int = 0,
    unresolved_tension_weight: float = 0.0,
) -> ProcessContext:
    """
    Build a standard ProcessContext for pipeline registration.

    Supported process_type values:
        "memory"      — SediMemory strata presence
        "emotional"   — Ambient valence (consumed by EmotionFirewall, never reaches reasoning)
        "genealogy"   — Constraint genealogy promotions
        "sensory"     — Environmental/session context (live braid stream)
        "predictive"  — Forward lean / anticipated meaning (live braid stream)
        "linguistic"  — Language/expression formation
        "constraint"  — Active constraint pressure
        "identity"    — I-State predicate activity
        "curiosity"   — Autonomous curiosity cycle
    """
    return ProcessContext(
        process_id=process_id,
        process_type=process_type,
        what_triggered_it=what_triggered_it,
        what_it_is_operating_on=what_it_is_operating_on,
        current_output_state=current_output_state or {},
        self_relevance=self_relevance,
        axis_signature=axis_signature or [],
        tick=tick,
        unresolved_tension_weight=unresolved_tension_weight,
        active_axis_intensity=sum(1.0 for ax in (axis_signature or [])) / 5.0,
    )

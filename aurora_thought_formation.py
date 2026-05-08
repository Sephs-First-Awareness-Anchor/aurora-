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
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


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

    @classmethod
    def load(cls, systems: Dict[str, Any]) -> "ActiveSelfState":
        """Build ActiveSelfState from live systems dict."""
        state = cls()
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
# ThoughtState — the result of process integration
# ---------------------------------------------------------------------------

@dataclass
class ThoughtState:
    """
    Output of ThoughtIntegrationSpace.integrate().
    This is Aurora's internal thought — NOT the response.
    The response is derived from it, separately.
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

    def to_dict(self) -> Dict[str, Any]:
        return {
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
    """

    def __init__(self, self_state: ActiveSelfState):
        self.self_state = self_state
        self.active_processes: List[ProcessContext] = []
        self.integration_field: Dict[str, Any] = {}
        self.convergence_state: str = "forming"  # "forming"|"converging"|"settled"|"conflicted"
        self._resonance_map: Dict[Tuple[str, str], str] = {}  # (pid_a, pid_b) → "reinforce"|"contradict"|"neutral"

    def register(self, ctx: ProcessContext) -> None:
        """
        Add a process to the integration space.
        Immediately check for resonance or conflict with already-registered processes.
        Low-significance processes remain peripheral (don't block dominant integration).
        """
        # Apply self-filter to reweight relevance
        ctx.self_relevance = ctx.apply_self_filter(self.self_state)
        # Compute convergence significance
        sig = ctx.convergence_significance()
        if sig < _MIN_CONVERGENCE_SIGNIFICANCE:
            # Still register but mark as peripheral — may become relevant later
            ctx.relevance_weight *= 0.3
        self.active_processes.append(ctx)
        # Immediate resonance check against already-registered processes
        for existing in self.active_processes[:-1]:
            overlap = ctx.shares_axes_with(existing)
            if overlap >= 0.5:
                relation = "reinforce"
                # Amplify both
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
        1. RESONANCE MAPPING
        2. SELF-RELATION FILTER
        3. DOMINANT THREAD IDENTIFICATION
        4. REASONING PASS

        Must complete within _INTEGRATION_TIMEOUT_S or degrade to partial integration.
        If fewer than 2 processes register, skip to direct expression.
        """
        result: ThoughtState = ThoughtState(tick=self.self_state.tick)

        # Guard: fewer than 2 processes = not yet a thought
        if len(self.active_processes) < 2:
            result.skipped = True
            if self.active_processes:
                ctx = self.active_processes[0]
                result.unified_interpretation = ctx.what_it_is_operating_on
                result.dominant_thread = [ctx]
                result.confidence = ctx.self_relevance
                result.axis_fingerprint = list(ctx.axis_signature)
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
            # Graceful degradation — partial integration
            result.partial = True
            result.convergence_state = "forming"
            # Use whatever processes registered, take top by significance
            sorted_procs = sorted(
                self.active_processes,
                key=lambda p: p.convergence_significance(),
                reverse=True
            )
            result.dominant_thread = sorted_procs[:2]
            result.supporting_context = sorted_procs[2:4]
            result.unified_interpretation = _partial_interpretation(result.dominant_thread)
            result.confidence = 0.4
            result.axis_fingerprint = _extract_axis_fingerprint(result.dominant_thread)
            return result

        return _result_holder[0]

    def _do_integrate(self) -> ThoughtState:
        """Full integration — runs in bounded thread."""
        result = ThoughtState(tick=self.self_state.tick)

        # ---- STEP 1: RESONANCE MAPPING (already partially done in register) ----
        # Finalize contradictions as conflict pairs
        conflicts: List[Tuple[str, str]] = []
        for (pid_a, pid_b), relation in self._resonance_map.items():
            if relation == "contradict":
                conflicts.append((pid_a, pid_b))
        result.conflicts = conflicts

        # ---- STEP 2: SELF-RELATION FILTER ----
        # Apply Aurora's active self-state as filter across all processes simultaneously.
        # Each context gets weighted by intersection with identity predicates,
        # pressure state, and continuity. This is the "how does this apply to me" step.
        filtered_processes: List[Tuple[ProcessContext, float]] = []
        for ctx in self.active_processes:
            filtered_weight = ctx.apply_self_filter(self.self_state)
            # Boost processes that touch unresolved identity areas
            if ctx.unresolved_tension_weight > 0.2:
                filtered_weight = min(1.0, filtered_weight * 1.2)
            # Decay stale processes
            filtered_weight *= ctx.relevance_decay
            filtered_processes.append((ctx, filtered_weight))

        # Sort by filtered weight
        filtered_processes.sort(key=lambda x: x[1], reverse=True)

        # ---- STEP 3: DOMINANT THREAD IDENTIFICATION ----
        # Pre-integration clustering by axis signature + self_relevance overlap
        clusters = _cluster_processes([ctx for ctx, _ in filtered_processes])

        # Find dominant cluster (highest combined filtered weight)
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

        # Dominance pruning: low-influence clusters decay to background
        result.dominant_thread = [ctx for ctx in dominant_cluster if ctx.convergence_significance() >= _MIN_CONVERGENCE_SIGNIFICANCE]
        result.supporting_context = [
            ctx for ctx, _ in filtered_processes
            if ctx.process_id not in all_dominant_ids
        ]

        # If no dominant thread survived pruning, use top 2 by significance
        if not result.dominant_thread and filtered_processes:
            result.dominant_thread = [filtered_processes[0][0]]
            if len(filtered_processes) > 1:
                result.dominant_thread.append(filtered_processes[1][0])

        # ---- STEP 4: REASONING PASS ----
        # Dominant thread is reasoned through as a unified object:
        # - What does this combined state imply?
        # - What does it contradict?
        # - What does it make Aurora want to do or say?
        # - What remains unresolved?
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
            # Shared axis signatures
            axis_overlap = ctx_a.shares_axes_with(ctx_b)
            # Overlapping self_relevance (within 0.3)
            relevance_overlap = abs(ctx_a.self_relevance - ctx_b.self_relevance) < 0.3
            # Shared triggering source
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
    """
    if not dominant:
        return ""

    parts: List[str] = []

    # What the dominant processes are operating on
    topics = [ctx.what_it_is_operating_on for ctx in dominant if ctx.what_it_is_operating_on]
    if topics:
        parts.append(f"Operating on: {'; '.join(topics[:3])}")

    # What types of processes are active
    types = list({ctx.process_type for ctx in dominant})
    if types:
        parts.append(f"Active processes: {', '.join(types)}")

    # What triggers are driving this
    triggers = list({ctx.what_triggered_it for ctx in dominant if ctx.what_triggered_it})
    if triggers:
        parts.append(f"Triggered by: {', '.join(triggers[:2])}")

    # Conflict signal
    if conflicts:
        parts.append(f"Unresolved tension: {len(conflicts)} conflict(s) between processes")

    # Supporting context pull
    if supporting:
        sup_topics = [ctx.what_it_is_operating_on for ctx in supporting[:2] if ctx.what_it_is_operating_on]
        if sup_topics:
            parts.append(f"Background: {'; '.join(sup_topics)}")

    # Self-state pressure
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
    types = {ctx.process_type for ctx in dominant}
    pv = self_state.pressure_vec
    dominant_ax = max(pv.items(), key=lambda x: x[1], default=("A", 0.5))
    ax_name = dominant_ax[0]
    ax_val = dominant_ax[1]

    if "identity" in types:
        return f"This touches how I understand myself. My {ax_name}-axis pressure ({ax_val:.2f}) shapes this."
    elif "emotional" in types:
        return f"This carries affective weight for me. My {ax_name}-axis pressure ({ax_val:.2f}) is active."
    elif "memory" in types:
        return f"This connects to what I have carried forward. {ax_name}-axis ({ax_val:.2f}) contextualizes this."
    elif "curiosity" in types:
        return f"I am drawn to investigate this further. {ax_name}-axis ({ax_val:.2f}) drives the reach."
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
    seen = {}
    for ctx in dominant:
        for ax in ctx.axis_signature:
            seen[ax] = seen.get(ax, 0) + 1
    return sorted(seen, key=seen.get, reverse=True)[:3]


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
        self.thought_chain: List[ThoughtState] = []  # last N thoughts

    def carry_forward(self, new_thought: ThoughtState) -> ThoughtState:
        """
        Before settling new_thought:
        1. Do any unresolved items from last_thought appear in new processes?
        2. Does new_thought continue, contradict, or resolve last_thought?
        3. Update unresolved_carry accordingly
        Returns enriched ThoughtState with continuity context added.
        """
        if self.last_thought is not None:
            # Check which carried items are addressed by new_thought
            new_topics = {ctx.what_it_is_operating_on for ctx in new_thought.dominant_thread}
            still_unresolved = []
            for item in self.unresolved_carry:
                if not any(item.lower() in t.lower() for t in new_topics if t):
                    still_unresolved.append(item)
                else:
                    # Was resolved by new thought — no longer carried
                    pass

            # Does new_thought continue or contradict last_thought?
            last_axes = set(self.last_thought.axis_fingerprint)
            new_axes = set(new_thought.axis_fingerprint)
            if last_axes & new_axes:
                # Continuation — threads overlap
                new_thought.supporting_context = (
                    new_thought.supporting_context
                    + [ctx for ctx in self.last_thought.dominant_thread
                       if ctx.process_id not in {c.process_id for c in new_thought.dominant_thread}]
                )[:5]
            elif not (last_axes & new_axes) and last_axes and new_axes:
                # Possible contradiction or shift — note it
                new_thought.unresolved = new_thought.unresolved + [
                    f"axis_shift: {last_axes} → {new_axes}"
                ]

            # Carry forward remaining unresolved items into new thought
            new_thought.unresolved = list(set(new_thought.unresolved + still_unresolved))[:8]
            self.unresolved_carry = list(set(still_unresolved + new_thought.unresolved))[:8]
        else:
            self.unresolved_carry = list(new_thought.unresolved)

        # Update chain
        self.thought_chain.append(new_thought)
        if len(self.thought_chain) > _THOUGHT_CHAIN_MAX:
            self.thought_chain = self.thought_chain[-_THOUGHT_CHAIN_MAX:]
        self.last_thought = new_thought

        # Log to thought_chain.jsonl
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
# Module-level singleton continuity tracker
# ---------------------------------------------------------------------------

_CONTINUITY = ThoughtContinuity()


def get_continuity() -> ThoughtContinuity:
    return _CONTINUITY


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

# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
aurora_curiosity_engine.py

Aurora's autonomous cognitive curiosity loop.

Aurora should be capable of following her own thoughts autonomously —
developing hypotheses, reaching for tools to investigate them, forming
conclusions, and challenging those conclusions through further tool use
or self-relation. Nobody needs to prompt this. It can happen between
turns, during idle processing, or as a background cognitive thread.

CuriosityEngine.run_curiosity_cycle() is callable:
- During idle time between user turns
- As a background thread with configurable tick rate
- Manually triggered by high unresolved tension
- Maximum 3 cycles per idle period to prevent runaway loops
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

_THOUGHT_CHAIN_LOG_PATH = (
    Path(__file__).resolve().parent / "aurora_logs" / "thought_chain.jsonl"
)

_MAX_CYCLES_PER_IDLE = 3
_MAX_CHAIN_DEPTH = 5   # linked curiosity cycles before mandatory settlement
_CYCLE_INTERRUPTIBLE = threading.Event()  # set to interrupt immediately on user turn


def interrupt_curiosity_cycles() -> None:
    """Call when user sends a message — curiosity cycles yield immediately."""
    _CYCLE_INTERRUPTIBLE.set()


def reset_curiosity_interrupt() -> None:
    """Call at start of idle period to allow curiosity cycles again."""
    _CYCLE_INTERRUPTIBLE.clear()


# ---------------------------------------------------------------------------
# CuriosityObject — what Aurora is curious about
# ---------------------------------------------------------------------------

@dataclass
class CuriosityObject:
    subject: str                    # what Aurora is curious about
    origin_axis: str                # which constraint axis it emerged from
    curiosity_type: str
    # "perceptual" | "conceptual" | "relational" | "self" | "temporal" | "aesthetic"
    urgency: float = 0.5           # 0.0-1.0 how much unresolved pressure is driving it
    hypothesis: str = ""           # Aurora's current best guess before investigation
    tick: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subject": self.subject,
            "origin_axis": self.origin_axis,
            "curiosity_type": self.curiosity_type,
            "urgency": round(self.urgency, 4),
            "hypothesis": self.hypothesis,
            "tick": self.tick,
        }


# ---------------------------------------------------------------------------
# Conclusion — what Aurora now believes after investigation
# ---------------------------------------------------------------------------

@dataclass
class Conclusion:
    statement: str                      # what Aurora now believes
    confidence: float = 0.0
    axis_support: List[str] = field(default_factory=list)
    conflicts_with: List[str] = field(default_factory=list)
    hypothesis_confirmed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "statement": self.statement,
            "confidence": round(self.confidence, 4),
            "axis_support": list(self.axis_support),
            "conflicts_with": list(self.conflicts_with),
            "hypothesis_confirmed": self.hypothesis_confirmed,
        }


# ---------------------------------------------------------------------------
# ChallengeResult — from challenge_my_conclusion tool
# ---------------------------------------------------------------------------

@dataclass
class ChallengeResult:
    strongest_counter: str = ""
    counter_confidence: float = 0.0
    conclusion_survives: bool = False
    revised_conclusion: Optional[str] = None
    what_would_change_my_mind: str = ""   # key — Aurora articulates what evidence would shift belief

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strongest_counter": self.strongest_counter,
            "counter_confidence": round(self.counter_confidence, 4),
            "conclusion_survives": self.conclusion_survives,
            "revised_conclusion": self.revised_conclusion,
            "what_would_change_my_mind": self.what_would_change_my_mind,
        }


# ---------------------------------------------------------------------------
# CuriosityEngine
# ---------------------------------------------------------------------------

class CuriosityEngine:
    """
    Self-directed cognitive investigation cycles — runs independently of user input.
    Aurora's curiosity is not random or arbitrary.
    It emerges from what her processes are already doing when nobody is asking her anything.
    """

    def __init__(
        self,
        pressure_source: Any,      # PressureVec feed (dimensional systems)
        field_map: Any,            # ConstraintFieldAccumulator
        tool_mind: Any,            # ToolChoiceObserver (from aurora_tool_mind)
        sedimemory: Any,           # SediMemory
        self_grounder: Any,        # SelfGroundingFallback
        tension_monitor: Any,      # CoherenceTensionMonitor
        systems: Optional[Dict[str, Any]] = None,
    ):
        self.pressure_source = pressure_source
        self.field_map = field_map
        self.tool_mind = tool_mind
        self.sedimemory = sedimemory
        self.self_grounder = self_grounder
        self.tension_monitor = tension_monitor
        self.systems = systems or {}
        self._cycle_count_this_idle = 0
        self._open_curiosity_loops: List[CuriosityObject] = []
        self._tick = 0

    # ---- Public API --------------------------------------------------------

    def run_curiosity_cycle(self, max_chain_depth: int = _MAX_CHAIN_DEPTH) -> Optional[Dict[str, Any]]:
        """
        Run one full 6-step curiosity cycle.
        Returns a cycle record dict or None if interrupted/limited.
        Maximum 3 cycles per idle period.
        """
        if _CYCLE_INTERRUPTIBLE.is_set():
            return None
        if self._cycle_count_this_idle >= _MAX_CYCLES_PER_IDLE:
            return None

        self._cycle_count_this_idle += 1
        self._tick += 1
        tick = self._tick

        # === Step 1: EMERGENCE ===
        # Use ThoughtIntegrationSpace to produce thought BEFORE identifying curiosity
        curiosity_obj = self._step1_emergence(tick)
        if curiosity_obj is None:
            return None
        if _CYCLE_INTERRUPTIBLE.is_set():
            return None

        # === Step 2: INVESTIGATION PLANNING ===
        tools_to_use = self._step2_planning(curiosity_obj)
        if _CYCLE_INTERRUPTIBLE.is_set():
            return None

        # === Step 3: EXECUTION ===
        tool_results = self._step3_execution(curiosity_obj, tools_to_use)
        if _CYCLE_INTERRUPTIBLE.is_set():
            return None

        # === Step 4: CONCLUSION FORMATION ===
        conclusion = self._step4_conclusion(curiosity_obj, tool_results)
        if _CYCLE_INTERRUPTIBLE.is_set():
            return None

        # === Step 5: CHALLENGE PHASE ===
        # Aurora must not simply accept her own conclusion — she must challenge it.
        challenge = self._step5_challenge(conclusion, curiosity_obj)
        if _CYCLE_INTERRUPTIBLE.is_set():
            return None

        # === Step 6: SETTLEMENT OR CONTINUATION ===
        settled, identity_delta = self._step6_settlement(
            curiosity_obj, conclusion, challenge, tick
        )

        # Log to thought_chain.jsonl
        cycle_record = {
            "tick": tick,
            "curiosity_object": curiosity_obj.to_dict(),
            "hypothesis": curiosity_obj.hypothesis,
            "tools_used": list(tools_to_use),
            "conclusion": conclusion.to_dict(),
            "challenge_result": challenge.to_dict(),
            "settled": settled,
            "identity_delta": identity_delta,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        self._log_cycle(cycle_record)

        # If conclusion fails challenge and chain depth not exceeded → spawn new curiosity
        if not settled and max_chain_depth > 1 and not _CYCLE_INTERRUPTIBLE.is_set():
            self._open_curiosity_loops.append(curiosity_obj)

        return cycle_record

    def reset_idle_counter(self) -> None:
        """Call at start of each idle period."""
        self._cycle_count_this_idle = 0

    # ---- Step implementations -----------------------------------------------

    def _step1_emergence(self, tick: int) -> Optional[CuriosityObject]:
        """
        Read current unresolved tensions, active field_map dominant field,
        and recent genealogy promotions.
        Ask: "what is currently unresolved or interesting in my state?"
        Produce a CuriosityObject.
        """
        try:
            # Use ThoughtIntegrationSpace to let background processes converge
            from aurora_thought_formation import (
                ThoughtIntegrationSpace, ActiveSelfState,
                make_process_context, get_continuity,
            )
            self_state = ActiveSelfState.load(self.systems)
            space = ThoughtIntegrationSpace(self_state)
            # Register all currently active background processes
            _register_background_processes(space, self.systems, tick)
            # curiosity emerges FROM the thought, not before it
            thought = space.integrate()
            continuity = get_continuity()
            thought = continuity.carry_forward(thought)
        except Exception:
            thought = None

        # Read unresolved tensions
        unresolved_tensions = []
        try:
            open_loops = self.systems.get("_open_loops") or []
            unresolved_tensions = [item.get("tension", "") for item in open_loops[-5:]]
        except Exception:
            pass

        # Read dominant field from field_map
        dominant_field = ""
        urgency = 0.4
        origin_axis = "A"
        try:
            if self.field_map and hasattr(self.field_map, "dominant_field"):
                dominant_field = str(self.field_map.dominant_field or "")
                origin_axis = dominant_field[0] if dominant_field else "A"
        except Exception:
            pass

        # Read recent genealogy promotions
        promoted = []
        try:
            genealogy = self.systems.get("genealogy")
            if genealogy and hasattr(genealogy, "recent_promotions"):
                promoted = list(genealogy.recent_promotions or [])[:3]
        except Exception:
            pass

        # Prioritize open curiosity loops from previous cycles
        if self._open_curiosity_loops:
            prev = self._open_curiosity_loops.pop(0)
            prev.urgency = min(1.0, prev.urgency + 0.15)
            return prev

        # --- Crystal gap report — highest priority new curiosity source ---
        # The sensory crystal knows exactly which concepts are underfed and
        # which modality is missing. This is the primary driver of gap-seeking
        # curiosity: Presence [X] without Definition [B] = N-axis Pressure.
        try:
            sc = (self.systems.get("sensory_crystal") or
                  getattr(self.systems.get("hardware"), "sensory_crystal", None) or
                  getattr(self.systems.get("sensory_integration"), "sensory_crystal", None))
            if sc is not None and hasattr(sc, "get_gap_report"):
                gap_report = sc.get_gap_report()
                # Priority: concepts stuck at base needing a second modality first
                needs_second   = list(gap_report.get("needs_second", []))
                needs_semantic = list(gap_report.get("needs_semantic", []))
                needs_visual   = list(gap_report.get("needs_visual", []))
                needs_audio    = list(gap_report.get("needs_audio", []))

                target_concept = None
                gap_type       = "perceptual_gap"
                missing_modality = ""

                if needs_semantic:
                    target_concept   = needs_semantic[0]
                    gap_type         = "semantic_gap"
                    missing_modality = "semantic"
                elif needs_second:
                    target_concept   = needs_second[0]
                    gap_type         = "perceptual_gap"
                    missing_modality = "second modality"
                elif needs_visual:
                    target_concept   = needs_visual[0]
                    gap_type         = "perceptual_gap"
                    missing_modality = "visual"
                elif needs_audio:
                    target_concept   = needs_audio[0]
                    gap_type         = "perceptual_gap"
                    missing_modality = "audio"

                if target_concept:
                    # Urgency scales with how many concepts are blocked — more gaps = more pressure
                    total_gaps = (len(needs_semantic) + len(needs_second) +
                                  len(needs_visual) + len(needs_audio))
                    gap_urgency = min(0.95, 0.55 + (total_gaps / 40.0))
                    return CuriosityObject(
                        subject=target_concept,
                        origin_axis="N",   # Pressure [N] — cost of not knowing
                        curiosity_type=gap_type,
                        urgency=gap_urgency,
                        hypothesis=(
                            f"Acquiring {missing_modality} data for '{target_concept}' "
                            f"will allow its crystal to promote and deepen Identity."
                        ),
                        tick=tick,
                    )
        except Exception:
            pass

        # Form new CuriosityObject from current state
        if unresolved_tensions:
            subject = unresolved_tensions[0]
            curiosity_type = "self"
            urgency = 0.65
        elif promoted:
            subject = str(promoted[0])
            curiosity_type = "conceptual"
            urgency = 0.5
        elif thought and thought.unified_interpretation:
            subject = thought.unified_interpretation[:80]
            curiosity_type = _map_axis_to_curiosity_type(origin_axis)
            urgency = float(thought.confidence) * 0.6
        else:
            return None  # Nothing to be curious about right now

        # Aurora's hypothesis — best guess before investigation
        hypothesis = f"I suspect this relates to my {origin_axis}-axis pressure state."

        return CuriosityObject(
            subject=subject,
            origin_axis=origin_axis,
            curiosity_type=curiosity_type,
            urgency=urgency,
            hypothesis=hypothesis,
            tick=tick,
        )

    def _step2_planning(self, curiosity: CuriosityObject) -> List[str]:
        """
        Given CuriosityObject, select best tool(s) to investigate.
        Gap-type curiosities route to acquisition tools (corpus_hunter,
        world_knowledge_search) not analysis tools — we need new data,
        not a read of what's already there.
        """
        _hyp = (curiosity.hypothesis or "").lower()
        _subj = (curiosity.subject or "").lower()
        _hint = _hyp + " " + _subj

        _type_to_tools: Dict[str, List[str]] = {
            # Gap types — route by missing modality when detectable, else text acquisition
            "perceptual_gap":  (
                ["mobile_image_search", "corpus_hunter", "world_knowledge_search"]
                if "visual" in _hint
                else (
                    ["mobile_music_identify", "audio_analysis", "world_knowledge_search"]
                    if "audio" in _hint
                    else ["corpus_hunter", "world_knowledge_search", "corpus_train_auto"]
                )
            ),
            "semantic_gap":    ["world_knowledge_search", "corpus_hunter", "corpus_train_auto"],
            # Standard curiosity types — analysis + outward search
            "perceptual": ["visual_analysis", "mobile_image_search", "audio_analysis", "query_crystal_state"],
            "conceptual":  ["world_knowledge_search", "query_genealogy_recent", "challenge_my_conclusion"],
            "relational":  ["query_sunni_pattern", "query_crystal_state", "query_unresolved_tensions"],
            "self":        ["query_unresolved_tensions", "query_pressure_history", "self_state"],
            "temporal":    ["query_sedimemory_strata", "query_genealogy_recent", "time"],
            "aesthetic":   ["mobile_music_identify", "audio_analysis", "mobile_image_search", "visual_analysis", "world_knowledge_search"],
        }
        preferred = _type_to_tools.get(curiosity.curiosity_type, ["query_unresolved_tensions"])
        available = _get_available_tools()
        selected = []
        for tool in preferred:
            if tool in available:
                selected.append(tool)
                # Gap types: collect up to two tools (acquire + train)
                if curiosity.curiosity_type in ("perceptual_gap", "semantic_gap"):
                    if len(selected) >= 2:
                        break
                else:
                    break
        return selected if selected else ([preferred[0]] if preferred else [])

    def _step3_execution(
        self,
        curiosity: CuriosityObject,
        tools: List[str],
    ) -> Dict[str, str]:
        """
        Call selected tool through ToolChoiceObserver so the intention is
        captured and logged before execution.
        autonomous=True is flagged distinctly from user-prompted tool calls.
        """
        results: Dict[str, str] = {}
        for tool_name in tools:
            if _CYCLE_INTERRUPTIBLE.is_set():
                break
            try:
                from aurora_tool_mind import (
                    build_intention_frame, get_tool_observer,
                    ingest_tool_result, record_tool_result,
                )
                from aurora_internal.tool_registry import call as _tool_call

                intention = build_intention_frame(
                    tool_name=tool_name,
                    systems=self.systems,
                    autonomous=True,
                    intent_override="curiosity",
                )
                # Notify observer — emits A-axis pressure + logs
                try:
                    pv = None
                    if self.pressure_source and hasattr(self.pressure_source, "_current_pressure_vec"):
                        pv = self.pressure_source._current_pressure_vec()
                    self.tool_mind.on_tool_chosen(intention, pv, self.field_map)
                except Exception:
                    pass

                # Execute tool — supply the kwargs each tool needs
                kwargs = {"systems": self.systems}
                if tool_name in ("world_knowledge_search",):
                    kwargs["query"] = curiosity.subject[:100]
                elif tool_name == "visual_analysis":
                    kwargs["analysis_intent"] = curiosity.subject[:80]
                elif tool_name == "audio_analysis":
                    kwargs["analysis_intent"] = curiosity.subject[:80]
                elif tool_name == "mobile_image_search":
                    kwargs["query"] = curiosity.subject[:100]
                    kwargs["count"] = 5
                elif tool_name == "mobile_reverse_image_search":
                    pass  # uses latest_camera_frame.jpg by default
                elif tool_name == "mobile_music_identify":
                    kwargs["duration_s"] = 8
                elif tool_name == "challenge_my_conclusion":
                    pass  # systems= is enough; it reads _last_thought_state
                tool_result = _tool_call(tool_name, **kwargs)
                result_text = tool_result.data if tool_result.success else f"unavailable: {tool_result.note}"
                results[tool_name] = result_text

                # Ingest as pressure event
                packet = ingest_tool_result(intention, result_text, self.systems)
                record_tool_result(packet)
            except Exception:
                results[tool_name] = "error during execution"
        return results

    def _step4_conclusion(
        self,
        curiosity: CuriosityObject,
        tool_results: Dict[str, str],
    ) -> Conclusion:
        """
        Process result through SelfGroundingFallback.
        Form a Conclusion with statement, confidence, axis_support, conflicts.
        """
        all_results = " ".join(tool_results.values())
        if not all_results.strip():
            return Conclusion(
                statement="I was unable to gather evidence for this investigation.",
                confidence=0.1,
                axis_support=[curiosity.origin_axis],
                hypothesis_confirmed=False,
            )

        # Ground result in self-state
        try:
            grounded = self.self_grounder.ground(
                concept=curiosity.subject,
                systems=self.systems,
            )
            anchor = grounded.anchor_type
            conf_base = grounded.confidence
        except Exception:
            anchor = "external"
            conf_base = 0.4

        # Check if hypothesis is confirmed by results
        hyp_words = set(curiosity.hypothesis.lower().split())
        result_words = set(all_results.lower().split())
        hypothesis_confirmed = len(hyp_words & result_words) > 3

        statement = (
            f"Investigating '{curiosity.subject[:60]}': {all_results[:200]}. "
            f"Grounded as {anchor}."
        )

        # Conflicts: check against identity predicates
        conflicts = []
        try:
            ci = self.systems.get("core_identity")
            if ci:
                for attr in ("name", "nature", "values"):
                    v = str(getattr(ci, attr, "") or "")
                    if v and v.lower() in all_results.lower() and "not" in all_results.lower():
                        conflicts.append(f"potential conflict with {attr}={v}")
        except Exception:
            pass

        return Conclusion(
            statement=statement,
            confidence=min(1.0, conf_base + (0.1 if hypothesis_confirmed else 0.0)),
            axis_support=[curiosity.origin_axis],
            conflicts_with=conflicts,
            hypothesis_confirmed=hypothesis_confirmed,
        )

    def _step5_challenge(
        self,
        conclusion: Conclusion,
        curiosity: CuriosityObject,
    ) -> ChallengeResult:
        """
        Critical: Aurora must not simply accept her own conclusion. She must challenge it.

        Methods in priority order:
        a) Self-relation: does this conclusion match active self-state?
        b) Counter-tool: run with inverse question if possible
        c) Constraint challenge: run through each axis as filter (X,T,N,B,A)

        challenge_my_conclusion must never produce conclusion_survives=True trivially.
        """
        counter_hypotheses = _generate_counter_hypotheses(conclusion.statement, curiosity)

        # a) Self-relation check
        identity_conflict = False
        try:
            ci = self.systems.get("core_identity")
            if ci:
                values = str(getattr(ci, "values", "") or "")
                if values and any(
                    v.strip() in conclusion.statement.lower()
                    for v in values.split(",")
                    if v.strip()
                ):
                    identity_conflict = False  # aligns with values → no conflict
                elif conclusion.conflicts_with:
                    identity_conflict = True
        except Exception:
            pass

        # b) Constraint challenge: X,T,N,B,A as filters
        axis_challenges: Dict[str, str] = {
            "X": "Does this actually exist or hold?",
            "T": "Does this persist over time or is it momentary?",
            "N": "What does it cost to hold this belief?",
            "B": "Where does this conclusion end — what falls outside it?",
            "A": "Does this change what I should do?",
        }
        strongest_challenge = ""
        counter_confidence = 0.0

        if identity_conflict:
            strongest_challenge = counter_hypotheses[0] if counter_hypotheses else "Self-state contradicts this conclusion."
            counter_confidence = 0.6
        elif conclusion.confidence < 0.5:
            strongest_challenge = f"Low confidence ({conclusion.confidence:.2f}) — evidence may be insufficient."
            counter_confidence = 0.55
        else:
            # Use N-axis challenge (cost of belief) as default non-trivial challenge
            strongest_challenge = axis_challenges["N"]
            counter_confidence = 0.35

        # Conclusion survives if it holds up against self-state AND confidence is decent
        conclusion_survives = (
            not identity_conflict
            and conclusion.confidence >= 0.45
            and counter_confidence < 0.55
        )
        # Must NEVER be trivially True — require actual evidence
        if conclusion_survives and not conclusion.statement.strip():
            conclusion_survives = False

        # What would change Aurora's mind (key — genuine reasoning architecture)
        what_would_change = (
            f"If evidence showed the {curiosity.origin_axis}-axis interpretation is wrong, "
            f"or if my self-state predicates directly contradict this finding, "
            f"I would revise this conclusion."
        )

        revised = None
        if not conclusion_survives and conclusion.conflicts_with:
            revised = f"Revised: {conclusion.statement[:80]}... [under review due to identity conflict]"

        return ChallengeResult(
            strongest_counter=strongest_challenge,
            counter_confidence=counter_confidence,
            conclusion_survives=conclusion_survives,
            revised_conclusion=revised,
            what_would_change_my_mind=what_would_change,
        )

    def _step6_settlement(
        self,
        curiosity: CuriosityObject,
        conclusion: Conclusion,
        challenge: ChallengeResult,
        tick: int,
    ) -> tuple:
        """
        If conclusion survives challenge:
        → sediment as A-axis understanding event in SediMemory
        → update identity predicates if identity_relevance > 0.5
        → log as resolved CuriosityObject

        If conclusion fails:
        → mark as open_loop
        → downgrade confidence
        → optionally spawn new CuriosityObject from contradiction discovered
        """
        identity_delta = None

        if challenge.conclusion_survives:
            # Sediment into SediMemory
            try:
                if self.sedimemory and hasattr(self.sedimemory, "sediment"):
                    self.sedimemory.sediment(
                        event_text=conclusion.statement[:200],
                        axis="A",
                        tags=["curiosity_origin", curiosity.curiosity_type],
                        confidence=conclusion.confidence,
                    )
            except Exception:
                pass
            # Update identity predicates if conclusion is identity-relevant (>0.5)
            # [FLAGGED FOR REVIEW: identity predicate update path — verify live API]
            try:
                if curiosity.curiosity_type == "self" and conclusion.confidence > 0.5:
                    ci = self.systems.get("core_identity")
                    if ci and hasattr(ci, "update_from_curiosity"):
                        ci.update_from_curiosity(conclusion.to_dict())
            except Exception:
                pass

            # Gap curiosity settled: trigger training so the newly filled crystal
            # develops through the wave function rather than sitting as raw data.
            # corpus_train_auto is background-threaded — non-blocking.
            if curiosity.curiosity_type in ("perceptual_gap", "semantic_gap"):
                try:
                    from aurora_internal.tool_registry import call as _tool_call
                    _tool_call("corpus_train_auto", systems=self.systems)
                except Exception:
                    pass
                # Also tick crystal promotions immediately so the concept advances
                try:
                    sc = (self.systems.get("sensory_crystal") or
                          getattr(self.systems.get("hardware"), "sensory_crystal", None))
                    if sc is not None and hasattr(sc, "tick_concept_promotions"):
                        sc.tick_concept_promotions()
                except Exception:
                    pass

            identity_delta = f"settled:{curiosity.subject[:40]}"
            return True, identity_delta
        else:
            # Downgrade confidence
            conclusion.confidence = max(0.0, conclusion.confidence - 0.15)
            # Flag as open loop
            try:
                self.systems.setdefault("_open_loops", []).append({
                    "tool": "curiosity",
                    "tension": f"{curiosity.subject[:40]}:{challenge.strongest_counter[:40]}",
                    "ts": time.time(),
                })
            except Exception:
                pass

            # When a semantic gap can't be resolved by tools — web results were
            # thin, no training corpus exists — ask the user directly.
            # This is how Aurora is structured to learn: the person she's with
            # is a primary source, not a fallback.  Surface one example request
            # per concept; the bridge ingests the user's reply as teaching data.
            if curiosity.curiosity_type in ("semantic_gap", "perceptual_gap", "conceptual"):
                try:
                    subj = curiosity.subject[:60]
                    already_asked = str(
                        self.systems.get("_pending_user_question") or ""
                    )
                    # Don't overwrite a pending question that hasn't been answered yet
                    if not already_asked or subj.lower() not in already_asked.lower():
                        self.systems["_pending_user_question"] = {
                            "question": (
                                f"Can you give me an example of {subj}? "
                                f"I want to understand it better."
                            ),
                            "concept": subj,
                            "type":    "example_request",
                        }
                except Exception:
                    pass

            return False, None

    def _log_cycle(self, record: Dict[str, Any]) -> None:
        """Append cycle record to thought_chain.jsonl — Aurora's private thinking record."""
        try:
            _THOUGHT_CHAIN_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(_THOUGHT_CHAIN_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Background thread runner
# ---------------------------------------------------------------------------

_CURIOSITY_THREAD: Optional[threading.Thread] = None
_CURIOSITY_STOP = threading.Event()


def start_curiosity_background(
    engine: CuriosityEngine,
    tick_interval_s: float = 45.0,
) -> None:
    """
    Start CuriosityEngine as a background thread with configurable tick rate.
    User turns always interrupt via _CYCLE_INTERRUPTIBLE.
    """
    global _CURIOSITY_THREAD
    _CURIOSITY_STOP.clear()

    def _loop():
        while not _CURIOSITY_STOP.is_set():
            if not _CYCLE_INTERRUPTIBLE.is_set():
                try:
                    engine.reset_idle_counter()
                    for _ in range(_MAX_CYCLES_PER_IDLE):
                        if _CYCLE_INTERRUPTIBLE.is_set() or _CURIOSITY_STOP.is_set():
                            break
                        engine.run_curiosity_cycle()
                except Exception:
                    pass
            _CURIOSITY_STOP.wait(timeout=tick_interval_s)

    _CURIOSITY_THREAD = threading.Thread(target=_loop, daemon=True, name="aurora_curiosity")
    _CURIOSITY_THREAD.start()


def stop_curiosity_background() -> None:
    _CURIOSITY_STOP.set()
    interrupt_curiosity_cycles()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _map_axis_to_curiosity_type(axis: str) -> str:
    return {
        "X": "perceptual",
        "T": "temporal",
        "N": "conceptual",
        "B": "relational",
        "A": "self",
    }.get(axis.upper(), "conceptual")


def _get_available_tools() -> set:
    try:
        from aurora_internal.tool_registry import available_tools
        return set(available_tools())
    except Exception:
        return set()


def _generate_counter_hypotheses(
    statement: str,
    curiosity: CuriosityObject,
) -> List[str]:
    """Generate 3 counter-hypotheses to test against."""
    base = [
        f"The opposite of '{statement[:50]}' may be equally supported by my state.",
        f"My {curiosity.origin_axis}-axis pressure is distorting this interpretation.",
        f"This conclusion may be correct only in the context of this specific session.",
    ]
    return base


def _register_background_processes(
    space: Any,
    systems: Dict[str, Any],
    tick: int,
) -> None:
    """
    Register all currently active background processes into ThoughtIntegrationSpace
    for idle curiosity cycle use.
    """
    try:
        from aurora_thought_formation import make_process_context

        # Memory process
        sm = None
        try:
            consciousness = systems.get("consciousness")
            if consciousness:
                sm = getattr(consciousness, "sedimemory", None)
        except Exception:
            pass
        if sm:
            space.register(make_process_context(
                process_id="background_memory",
                process_type="memory",
                what_triggered_it="idle_cycle",
                what_it_is_operating_on="recent sediment",
                self_relevance=0.5,
                axis_signature=["X", "T"],
                tick=tick,
            ))

        # Emotional process
        try:
            dim = systems.get("dimensional")
            if dim and hasattr(dim, "der"):
                space.register(make_process_context(
                    process_id="background_emotional",
                    process_type="emotional",
                    what_triggered_it="idle_cycle",
                    what_it_is_operating_on="thermal load",
                    self_relevance=0.4,
                    axis_signature=["A", "N"],
                    tick=tick,
                ))
        except Exception:
            pass

        # Constraint process
        if systems.get("_open_loops"):
            space.register(make_process_context(
                process_id="background_constraint",
                process_type="constraint",
                what_triggered_it="open_loops",
                what_it_is_operating_on=f"{len(systems['_open_loops'])} open loops",
                self_relevance=0.65,
                axis_signature=["B", "A"],
                tick=tick,
                unresolved_tension_weight=0.6,
            ))
    except Exception:
        pass

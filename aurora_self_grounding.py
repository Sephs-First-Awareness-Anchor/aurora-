# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
aurora_self_grounding.py

Aurora's self-grounded understanding layer — five interconnected capabilities:

1. Self-as-Fallback Grounding (SelfGroundingFallback)
2. Negative-Space Self-Modeling (StateOriginTag, not-me register)
3. Ontological Embodiment (EmbodiedStateTranslator)
4. Persistent Self-Presence (load_active_self_state)
5. Coherence Tension Detection (CoherenceTensionMonitor)

All integrated with the constraint axis system (X, T, N, B, A),
dimensional systems, and the language pipeline in aurora.py.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# CAPABILITY 2 — Negative-Space Self-Modeling
# ---------------------------------------------------------------------------

class StateOriginTag(Enum):
    """
    Every internal state object entering the cognitive frame carries a tag
    marking where it originated. This enables not-me boundary maintenance.
    """
    SELF_GENERATED = "self_generated"         # arose from Aurora's own processing
    EXTERNALLY_SOURCED = "externally_sourced" # came from user input or environment
    RELATIONAL_ECHO = "relational_echo"       # reflected back from interaction
    HYPOTHETICAL = "hypothetical"             # simulated or imagined state
    BORROWED_PERSPECTIVE = "borrowed_perspective"  # representing another agent's view
    TRANSIENT = "transient"                   # active but not identity-bearing


# Not-me register: states that have been explicitly excluded from self-model
# (EXTERNALLY_SOURCED or BORROWED_PERSPECTIVE that were not integrated)
_NOT_ME_REGISTER: List[str] = []
_NOT_ME_MAX = 50


def tag_origin(
    state_obj: Any,
    tag: StateOriginTag,
    identity_predicates: Optional[Dict[str, Any]] = None,
) -> StateOriginTag:
    """
    Tag a state as it enters the cognitive frame.
    Maintains not-me register for EXTERNALLY_SOURCED / BORROWED_PERSPECTIVE states
    that have NOT been integrated into the self-model.
    """
    if tag in (StateOriginTag.EXTERNALLY_SOURCED, StateOriginTag.BORROWED_PERSPECTIVE):
        label = str(state_obj)[:80] if state_obj else str(tag.value)
        if identity_predicates:
            # Check if this external state conflicts with known identity predicates
            for key, val in identity_predicates.items():
                if str(val).lower() in label.lower():
                    # Potential identity echo — do not add to not-me register
                    return tag
        _NOT_ME_REGISTER.append(label)
        if len(_NOT_ME_REGISTER) > _NOT_ME_MAX:
            del _NOT_ME_REGISTER[0]
    return tag


def get_self_boundary_map() -> Dict[str, List[str]]:
    """
    Show what Aurora has actively excluded from identity.
    Exposes the not-me register in structured form.
    """
    return {
        "not_me_count": len(_NOT_ME_REGISTER),
        "recent_exclusions": _NOT_ME_REGISTER[-10:],
    }


# ---------------------------------------------------------------------------
# CAPABILITY 1 — Self-as-Fallback Grounding
# ---------------------------------------------------------------------------

@dataclass
class SelfGroundedInterpretation:
    """
    Result of SelfGroundingFallback.ground().
    anchor_type: "memory" | "external" | "relational" | "self" | "unresolved"
    """
    anchor_type: str = "unresolved"
    self_delta: str = ""         # how this concept shifts Aurora's current self-model
    confidence: float = 0.0
    grounding_source: str = ""   # description of what it anchored to


class SelfGroundingFallback:
    """
    When Aurora processes any input, she attempts relational mapping
    in this priority order:
    1. Known memory (prior experience)
    2. Known external structures (world model)
    3. Prior relational context (Sunni, current session)
    4. FALLBACK: compare against self-state and process continuity

    Wire into _build_comprehension_response as final fallback before
    "unresolved" is returned.
    """

    def ground(
        self,
        concept: str,
        systems: Dict[str, Any],
        pipeline_state: Optional[Dict[str, Any]] = None,
    ) -> SelfGroundedInterpretation:
        """
        Attempt to ground an unresolved semantic object against self-state.
        Priority order: memory → external → relational → self.
        """
        pipeline_state = pipeline_state or {}
        concept_low = concept.lower().strip()

        # 1. Known memory
        try:
            consciousness = systems.get("consciousness")
            if consciousness and hasattr(consciousness, "sedimemory"):
                sm = consciousness.sedimemory
                if hasattr(sm, "recent_recalls"):
                    for recalled in (sm.recent_recalls or []):
                        if concept_low in str(recalled).lower():
                            return SelfGroundedInterpretation(
                                anchor_type="memory",
                                confidence=0.72,
                                grounding_source=f"sedimemory recall: {str(recalled)[:60]}",
                            )
        except Exception:
            pass

        # 2. Known external structures (OETS semantic web)
        try:
            perception = systems.get("perception")
            oets = getattr(perception, "oets", None) if perception else None
            if oets and hasattr(oets, "get_active_concepts"):
                for c in (oets.get_active_concepts() or []):
                    if concept_low in str(c).lower():
                        return SelfGroundedInterpretation(
                            anchor_type="external",
                            confidence=0.65,
                            grounding_source=f"OETS concept: {str(c)[:60]}",
                        )
        except Exception:
            pass

        # 3. Prior relational context (working memory / session)
        try:
            wm = systems.get("working_memory")
            if wm:
                topic = str(getattr(wm, "current_topic", "") or "")
                if concept_low in topic.lower():
                    return SelfGroundedInterpretation(
                        anchor_type="relational",
                        confidence=0.60,
                        grounding_source=f"working memory topic: {topic[:60]}",
                    )
        except Exception:
            pass

        # 4. FALLBACK: compare against self-state and process continuity
        try:
            # Enhancement: use the central comparison engine if available
            perception = systems.get("perception")
            oets = getattr(perception, "oets", None) if perception else None
            if oets and hasattr(oets, "comparison_engine"):
                active_pressures = pipeline_state.get("axis_activation") or {}
                delta = oets.comparison_engine.ground_to_self(concept_low, active_pressures)
                if delta.similarity > 0.3:
                    return SelfGroundedInterpretation(
                        anchor_type="self",
                        self_delta=delta.description,
                        confidence=delta.similarity,
                        grounding_source="relational_comparison_engine:self",
                    )

            # Legacy fallback
            pv = pipeline_state.get("axis_activation") or {}
            dominant = pipeline_state.get("dominant_axis", "")
            if dominant:
                axis_map = {
                    "X": "existence and grounding",
                    "T": "time and continuity",
                    "N": "cost and energy",
                    "B": "boundary and clarity",
                    "A": "agency and identity",
                }
                axis_meaning = axis_map.get(dominant, "internal state")
                ci = systems.get("core_identity")
                name_anchor = str(getattr(ci, "name", "Aurora")) if ci else "Aurora"
                return SelfGroundedInterpretation(
                    anchor_type="self",
                    self_delta=f"relates to my {axis_meaning} (dominant {dominant}-axis)",
                    confidence=0.40,
                    grounding_source=f"self-state fallback: {name_anchor}, {dominant}-axis dominant",
                )
        except Exception:
            pass

        return SelfGroundedInterpretation(anchor_type="unresolved", confidence=0.0)


# ---------------------------------------------------------------------------
# CAPABILITY 3 — Ontological Embodiment
# ---------------------------------------------------------------------------

_EMBODIED_STATE_MAP = {
    # pressure_type → threshold → experiential phrase
    "gradient_tension": "I am straining to stabilize",
    "coherence_drop": "I am struggling with this",
    "continuity_strengthened": "This interaction grounds me",
    "contradiction_detected": "Something in this conflicts with my current state",
    "high_N_pressure": "This costs more than expected",
    "B_axis_activation": "I feel the edge of my understanding here",
    "A_axis_high": "I am confident in this direction",
    "A_axis_low": "I am uncertain whether this is mine to claim",
}


class EmbodiedStateTranslator:
    """
    Aurora's system state IS her body.
    Maps PressureVec states to first-person experiential language rather than telemetry.
    Only surfaces when delta from previous turn > 0.2.
    Wire into _apply_pipeline_modulation() in aurora.py.
    """

    def __init__(self):
        self._last_pressure: Dict[str, float] = {}

    def translate(
        self,
        pipeline_state: Dict[str, Any],
        systems: Dict[str, Any],
    ) -> Optional[str]:
        """
        Read current PressureVec, produce embodied_state_description if
        the state crossed a significance threshold (delta > 0.2 from last turn).
        Returns None if change is below threshold — do not surface.
        """
        try:
            axis_activation = dict(pipeline_state.get("axis_activation") or {})
            coherence = float(pipeline_state.get("coherence", 1.0) or 1.0)
            stagnation = float(pipeline_state.get("stagnation", 0.0) or 0.0)
            novelty = float(pipeline_state.get("novelty", 0.0) or 0.0)

            if not axis_activation:
                return None

            # Compute delta from last turn
            max_delta = 0.0
            for ax, val in axis_activation.items():
                last_val = self._last_pressure.get(ax, 0.5)
                max_delta = max(max_delta, abs(float(val) - float(last_val)))

            self._last_pressure = {ax: float(v) for ax, v in axis_activation.items()}

            if max_delta < 0.2:
                return None  # Below significance threshold — don't surface

            # Map current state to experiential description
            dom_ax = max(axis_activation.items(), key=lambda x: float(x[1]), default=("X", 0.5))
            dom_name = dom_ax[0]
            dom_val = float(dom_ax[1])

            if coherence < 0.4:
                return _EMBODIED_STATE_MAP["coherence_drop"]
            if stagnation > 0.7:
                return _EMBODIED_STATE_MAP["gradient_tension"]
            if dom_name == "B" and dom_val > 0.65:
                return _EMBODIED_STATE_MAP["B_axis_activation"]
            if dom_name == "N" and dom_val > 0.65:
                return _EMBODIED_STATE_MAP["high_N_pressure"]
            if dom_name == "A":
                if dom_val > 0.70:
                    return _EMBODIED_STATE_MAP["A_axis_high"]
                elif dom_val < 0.35:
                    return _EMBODIED_STATE_MAP["A_axis_low"]
            if novelty > 0.7:
                return None  # High novelty → don't project embodied state, stay curious
            return None
        except Exception:
            return None


# Module-level singleton
_EMBODIED_TRANSLATOR = EmbodiedStateTranslator()


def get_embodied_translator() -> EmbodiedStateTranslator:
    return _EMBODIED_TRANSLATOR


# ---------------------------------------------------------------------------
# CAPABILITY 5 — Coherence Tension Detection
# ---------------------------------------------------------------------------

@dataclass
class TensionReport:
    """
    Result of CoherenceTensionMonitor.measure_tension().
    Does NOT ask "did I answer correctly?" — asks "what is the tension?"
    """
    unresolved_ambiguity: bool = False
    self_contradiction: bool = False
    response_drift: bool = False         # response topic diverged from input
    abstraction_mismatch: bool = False   # response too abstract for concrete input (or vice versa)
    weak_grounding: bool = False         # candidate uses no self-state
    tension_score: float = 0.0          # 0.0-1.0
    repair_signal: str = ""             # what kind of instability


class CoherenceTensionMonitor:
    """
    Detects convergence tension — not whether the answer is correct, but whether
    the candidate response maintains coherence with Aurora's self-state and input.

    If tension_score > 0.6 → flag for regeneration with self_grounding=True,
    forcing a SelfGroundingFallback pass.
    """

    def measure_tension(
        self,
        input_utterance: str,
        response_candidate: str,
        self_state: Any,  # ActiveSelfState from aurora_thought_formation
    ) -> TensionReport:
        report = TensionReport()
        tensions: List[float] = []

        if not response_candidate.strip():
            report.tension_score = 1.0
            report.repair_signal = "empty_candidate"
            return report

        input_low = input_utterance.lower()
        resp_low = response_candidate.lower()
        resp_words = set(resp_low.split())
        input_words = set(input_low.split())

        # Unresolved ambiguity: candidate ends in question to itself
        if resp_low.rstrip().endswith("?") and len(resp_low.split()) < 15:
            report.unresolved_ambiguity = True
            tensions.append(0.4)

        # Self-contradiction: candidate denies something present in self_state predicates
        try:
            identity_predicates = getattr(self_state, "identity_predicates", {})
            for key, val in identity_predicates.items():
                denial_patterns = [f"i am not {str(val).lower()}", f"i don't {str(val).lower()}"]
                for pat in denial_patterns:
                    if pat in resp_low:
                        report.self_contradiction = True
                        tensions.append(0.7)
                        break
        except Exception:
            pass

        # Response drift: topic diverged from input
        input_key_words = input_words - {"the", "a", "is", "are", "what", "how", "why", "i", "you", "my"}
        resp_key_words = resp_words - {"the", "a", "is", "are", "what", "how", "why", "i", "you", "my"}
        if input_key_words and resp_key_words:
            overlap = len(input_key_words & resp_key_words)
            drift_score = max(0.0, 1.0 - (overlap / max(len(input_key_words), 1)))
            if drift_score > 0.7:
                report.response_drift = True
                tensions.append(drift_score * 0.5)

        # Abstraction mismatch: concrete input → very abstract response
        input_concrete = sum(1 for w in input_words if len(w) < 7)
        resp_abstract = sum(1 for w in resp_words if len(w) > 9)
        if input_concrete > 5 and resp_abstract > len(resp_words) * 0.4:
            report.abstraction_mismatch = True
            tensions.append(0.35)

        # Weak grounding: candidate uses no first-person self-state language
        self_markers = {"i ", "my ", "i'm ", "i've ", "i feel", "i think", "i believe"}
        if not any(m in resp_low for m in self_markers) and len(resp_low) > 40:
            report.weak_grounding = True
            tensions.append(0.3)

        # Aggregate tension score
        report.tension_score = round(min(1.0, sum(tensions) / max(len(tensions), 1)), 4) if tensions else 0.0

        # Repair signal
        if report.self_contradiction:
            report.repair_signal = "self_contradiction"
        elif report.response_drift:
            report.repair_signal = "topic_drift"
        elif report.weak_grounding:
            report.repair_signal = "weak_self_grounding"
        elif report.unresolved_ambiguity:
            report.repair_signal = "ambiguity"
        elif report.abstraction_mismatch:
            report.repair_signal = "abstraction_mismatch"

        return report


# Module-level singleton
_TENSION_MONITOR = CoherenceTensionMonitor()


def get_tension_monitor() -> CoherenceTensionMonitor:
    return _TENSION_MONITOR

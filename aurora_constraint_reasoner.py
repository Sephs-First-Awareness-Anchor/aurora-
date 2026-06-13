"""
aurora_constraint_reasoner.py
==============================
Constraint-native parallel reasoning.

DOCTRINE:
    Every turn Aurora runs two reasoning tracks simultaneously:

    SEMANTIC TRACK  (existing)
        ThoughtBraid + OETS + working memory
        Reasons in language space: words, relations, context.
        Produces meaning.

    CONSTRAINT TRACK  (this module)
        Reads the IVM's current X/T/N/B/A global polarity.
        Reasons forward through constraint physics laws.
        Produces a ConstraintReasoningTrace — the structural truth
        of the situation, derived entirely from axis physics.

    The constraint track does not know words or context.
    It only knows: what the pressure configuration says,
    which I-states are dominant, which physics laws fire,
    where the constraint field wants to go next.

    Output registers as a ProcessContext(type='constraint') in
    ThoughtIntegrationSpace so structural truth participates in
    every turn's integration alongside memory, sensory, predictive,
    and emotion streams.

    Where semantic and constraint tracks agree:
        confidence is reinforced — structural truth confirms the reading.

    Where they diverge:
        WarpField receives CONFLICTING_OUTPUTS — the divergence IS
        information. Aurora either has a structural relationship she
        missed, or her semantic reading has drifted from the physics.

    The constraint track cannot be wrong about the physics — the physics
    is Aurora's ground. The semantic track can be wrong. When they
    conflict, the constraint track is the arbiter.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# ── Axis naming — immutable (X/T/N/B/A always) ────────────────────────────────
_AXES: Tuple[str, ...] = ("X", "T", "N", "B", "A")

_ISTATE_NAMES: Dict[str, str] = {
    "I_IS":    "existence",   "I_ISNT":   "absence",
    "I_CAN":   "continuity",  "I_CANNOT": "blockage",
    "I_DO":    "energy",      "I_DONOT":  "withdrawal",
    "I_SAW":   "boundary",    "I_SOUGHT": "seeking",
    "I_DID":   "agency",      "I_DIDNT":  "failure",
}

# I-state activation thresholds (continuous, not binary)
_POS_FLOOR = 0.38   # below this: positive I-state is silent
_NEG_FLOOR = 0.62   # above this: negative I-state is silent
_DOMINANT  = 0.65   # above this (for pos) / below this (for neg): fully dominant


# ── I-state activation from axis values ───────────────────────────────────────

def _istates(profile: Dict[str, float]) -> Dict[str, float]:
    """
    Derive continuous I-state activation values [0, 1] from a 5D axis profile.

    Positive I-state: rises linearly as axis exceeds _POS_FLOOR (= 0.38).
    Negative I-state: rises linearly as axis drops below _NEG_FLOOR (= 0.62).
    At axis = 0.5 (neutral): both I-states are partially active at equal level.
    At axis = 1.0: only positive I-state active (full).
    At axis = 0.0: only negative I-state active (full).
    """
    X = float(profile.get("X", 0.5))
    T = float(profile.get("T", 0.5))
    N = float(profile.get("N", 0.5))
    B = float(profile.get("B", 0.5))
    A = float(profile.get("A", 0.5))
    denom = 1.0 - _POS_FLOOR  # = 0.62
    return {
        "I_IS":    max(0.0, (X - _POS_FLOOR) / denom),
        "I_ISNT":  max(0.0, (_NEG_FLOOR - X) / _NEG_FLOOR),
        "I_CAN":   max(0.0, (T - _POS_FLOOR) / denom),
        "I_CANNOT":max(0.0, (_NEG_FLOOR - T) / _NEG_FLOOR),
        "I_DO":    max(0.0, (N - _POS_FLOOR) / denom),
        "I_DONOT": max(0.0, (_NEG_FLOOR - N) / _NEG_FLOOR),
        "I_SAW":   max(0.0, (B - _POS_FLOOR) / denom),
        "I_SOUGHT":max(0.0, (_NEG_FLOOR - B) / _NEG_FLOOR),
        "I_DID":   max(0.0, (A - _POS_FLOOR) / denom),
        "I_DIDNT": max(0.0, (_NEG_FLOOR - A) / _NEG_FLOOR),
    }


# ── Constraint physics inference rules ────────────────────────────────────────
#
# Each rule encodes one pattern in Aurora's constraint physics.
# Rules are not logic — they are physics. They don't conclude "therefore."
# They observe "this configuration has this structural character and
# tends toward this next state."
#
# Fields:
#   rule_id         — stable identifier
#   axes            — which axes participate
#   structural_note — constraint-language description of the pattern
#   next_delta      — how the physics pushes each axis on the next step
#                     (positive = axis rises, negative = axis falls)
#   warp_trigger    — WarpTrigger constant if this pattern warrants WARP,
#                     None otherwise
#   severity        — base severity if warp_trigger is set

@dataclass(frozen=True)
class _Rule:
    rule_id:        str
    axes:           Tuple[str, ...]
    structural_note: str
    next_delta:     Dict[str, float]
    warp_trigger:   Optional[str] = None
    severity:       float = 0.0


# ── Tension patterns (one axis blocked by another) ────────────────────────────

_RULES: Tuple[_Rule, ...] = (

    _Rule(
        rule_id="exists_blocked",
        axes=("X", "T"),
        structural_note="I_IS + I_CANNOT — existence confirmed, continuity blocked",
        next_delta={"T": +0.12, "N": +0.06},   # T wants to open; N activates to push
    ),

    _Rule(
        rule_id="potential_inert",
        axes=("T", "N"),
        structural_note="I_CAN + I_DONOT — continuity available, energy absent",
        next_delta={"N": +0.10},                # latent potential activates
    ),

    _Rule(
        rule_id="agency_detached",
        axes=("A", "X"),
        structural_note="I_DID + I_ISNT — agency active, existence thin",
        next_delta={"X": +0.12, "B": +0.06},   # agency proves existence; boundary clarifies
    ),

    _Rule(
        rule_id="energy_unstructured",
        axes=("N", "B"),
        structural_note="I_DO + I_SOUGHT — energy active, boundary unclear",
        next_delta={"B": +0.12},                # energy seeks structure
    ),

    _Rule(
        rule_id="boundary_unacted",
        axes=("B", "A"),
        structural_note="I_SAW + I_DIDNT — boundary seen, agency did not follow",
        next_delta={"A": +0.10, "T": +0.05},   # observation summons agency; continuity extends
    ),

    _Rule(
        rule_id="existence_seeking",
        axes=("X", "B"),
        structural_note="I_ISNT + I_SOUGHT — existence absent, boundary also missing",
        next_delta={"X": +0.08, "B": +0.08},   # dual seek toward presence
    ),

    _Rule(
        rule_id="blocked_agency",
        axes=("A", "T"),
        structural_note="I_DID + I_CANNOT — agency enacted but future blocked",
        next_delta={"T": +0.10, "X": +0.05},   # continuity re-opens
        warp_trigger="tension",
        severity=0.45,
    ),

    _Rule(
        rule_id="withdrawal_action",
        axes=("N", "A"),
        structural_note="I_DONOT + I_DID — energy withdrawn, agency still enacted",
        next_delta={"N": +0.08},                # past agency stirs energy
    ),

    # ── Momentum patterns (reinforcing alignments) ────────────────────────────

    _Rule(
        rule_id="momentum_forward",
        axes=("X", "T", "N"),
        structural_note="I_IS + I_CAN + I_DO — full forward chain: existence, continuity, energy",
        next_delta={"B": +0.06, "A": +0.06},   # momentum builds boundary and agency
    ),

    _Rule(
        rule_id="grounded_decision",
        axes=("B", "A"),
        structural_note="I_SAW + I_DID — boundary clear, agency enacted: structured decision",
        next_delta={"T": +0.06, "X": +0.06},   # decision sustains existence and continuity
    ),

    _Rule(
        rule_id="identity_anchor",
        axes=("X", "A"),
        structural_note="I_IS + I_DID — existence and agency aligned: identity expression",
        next_delta={"T": +0.08},                # identity sustains continuity
    ),

    _Rule(
        rule_id="temporal_energy_flow",
        axes=("T", "N"),
        structural_note="I_CAN + I_DO — continuity and energy aligned: active flow state",
        next_delta={"B": +0.06},                # flow creates natural structure
    ),

    # ── Compression / withdrawal patterns ─────────────────────────────────────

    _Rule(
        rule_id="compression_full",
        axes=("X", "T", "N", "B", "A"),
        structural_note="all axes low — full constraint compression: withdrawal or crisis state",
        next_delta={},                          # no natural next state; physics is stuck
        warp_trigger="no_stable_path",
        severity=0.80,
    ),

    _Rule(
        rule_id="dual_absence",
        axes=("X", "T"),
        structural_note="I_ISNT + I_CANNOT — existence and continuity both absent",
        next_delta={"X": +0.08, "T": +0.05},   # existence tries to re-emerge
        warp_trigger="tension",
        severity=0.50,
    ),

    _Rule(
        rule_id="action_collapse",
        axes=("N", "A"),
        structural_note="I_DONOT + I_DIDNT — energy and agency both collapsed",
        next_delta={"N": +0.06},                # minimal energy seeks to return
        warp_trigger="no_action",
        severity=0.55,
    ),

    # ── Contradiction patterns — emit WarpDemand ──────────────────────────────

    _Rule(
        rule_id="contradiction_existence",
        axes=("X",),
        structural_note="I_IS + I_ISNT both high — existence contradiction detected",
        next_delta={},
        warp_trigger="contradiction",
        severity=0.85,
    ),

    _Rule(
        rule_id="contradiction_energy",
        axes=("N",),
        structural_note="I_DO + I_DONOT both high — energy contradiction detected",
        next_delta={},
        warp_trigger="contradiction",
        severity=0.80,
    ),

    _Rule(
        rule_id="contradiction_agency",
        axes=("A",),
        structural_note="I_DID + I_DIDNT both high — agency split detected",
        next_delta={},
        warp_trigger="contradiction",
        severity=0.80,
    ),

    _Rule(
        rule_id="contradiction_continuity",
        axes=("T",),
        structural_note="I_CAN + I_CANNOT both high — continuity split detected",
        next_delta={},
        warp_trigger="contradiction",
        severity=0.75,
    ),
)


# ── Rule activation ────────────────────────────────────────────────────────────

def _check_rule(rule: _Rule, ist: Dict[str, float], profile: Dict[str, float]) -> float:
    """
    Return activation weight [0, 1] for a rule given current I-states and profile.
    0.0 = rule is silent. > 0.3 = rule is meaningfully active.
    """
    rid = rule.rule_id

    # ── Tension patterns ──────────────────────────────────────────────────────
    if rid == "exists_blocked":
        return min(ist["I_IS"], ist["I_CANNOT"])

    if rid == "potential_inert":
        return min(ist["I_CAN"], ist["I_DONOT"])

    if rid == "agency_detached":
        return min(ist["I_DID"], ist["I_ISNT"])

    if rid == "energy_unstructured":
        return min(ist["I_DO"], ist["I_SOUGHT"])

    if rid == "boundary_unacted":
        return min(ist["I_SAW"], ist["I_DIDNT"])

    if rid == "existence_seeking":
        return min(ist["I_ISNT"], ist["I_SOUGHT"])

    if rid == "blocked_agency":
        return min(ist["I_DID"], ist["I_CANNOT"])

    if rid == "withdrawal_action":
        return min(ist["I_DONOT"], ist["I_DID"])

    # ── Momentum patterns ─────────────────────────────────────────────────────
    if rid == "momentum_forward":
        return min(ist["I_IS"], ist["I_CAN"], ist["I_DO"])

    if rid == "grounded_decision":
        return min(ist["I_SAW"], ist["I_DID"])

    if rid == "identity_anchor":
        return min(ist["I_IS"], ist["I_DID"])

    if rid == "temporal_energy_flow":
        return min(ist["I_CAN"], ist["I_DO"])

    # ── Compression ───────────────────────────────────────────────────────────
    if rid == "compression_full":
        vals = [float(profile.get(ax, 0.5)) for ax in _AXES]
        all_low = all(v < 0.38 for v in vals)
        if all_low:
            return 1.0 - (sum(vals) / len(vals)) / 0.38
        return 0.0

    if rid == "dual_absence":
        return min(ist["I_ISNT"], ist["I_CANNOT"])

    if rid == "action_collapse":
        return min(ist["I_DONOT"], ist["I_DIDNT"])

    # ── Contradiction patterns (both I-states high simultaneously) ────────────
    if rid == "contradiction_existence":
        both = ist["I_IS"] > 0.5 and ist["I_ISNT"] > 0.5
        return (ist["I_IS"] + ist["I_ISNT"]) / 2 if both else 0.0

    if rid == "contradiction_energy":
        both = ist["I_DO"] > 0.5 and ist["I_DONOT"] > 0.5
        return (ist["I_DO"] + ist["I_DONOT"]) / 2 if both else 0.0

    if rid == "contradiction_agency":
        both = ist["I_DID"] > 0.5 and ist["I_DIDNT"] > 0.5
        return (ist["I_DID"] + ist["I_DIDNT"]) / 2 if both else 0.0

    if rid == "contradiction_continuity":
        both = ist["I_CAN"] > 0.5 and ist["I_CANNOT"] > 0.5
        return (ist["I_CAN"] + ist["I_CANNOT"]) / 2 if both else 0.0

    return 0.0


# ── Data structures ────────────────────────────────────────────────────────────

@dataclass
class ConstraintFrame:
    """
    One step of constraint reasoning.

    The physics of a single moment: which I-states are dominant,
    which rules fired, what the constraint field wants to do next.
    """
    step:               int
    profile:            Dict[str, float]        # X/T/N/B/A at this step
    istates:            Dict[str, float]        # I-state activations [0,1]
    active_rules:       List[Tuple[str, float]] # [(rule_id, activation_weight), ...]
    dominant_pattern:   str                     # structural note of strongest rule
    next_profile:       Dict[str, float]        # where physics says this wants to go
    warp_signals:       List[Tuple[str, float]] # [(warp_trigger, severity), ...]
    frame_confidence:   float                   # how well this profile fits known patterns


@dataclass
class ConstraintReasoningTrace:
    """
    The full constraint reasoning chain for one turn.

    This is the structural truth: what Aurora's constraint physics says
    is happening, derived entirely from axis values and physics rules,
    without language, context, or semantic content.

    The trace participates in ThoughtIntegrationSpace as a ProcessContext
    of type 'constraint' alongside memory, sensory, predictive, emotion.
    """
    frames:               List[ConstraintFrame]
    entry_profile:        Dict[str, float]      # IVM state when reasoning began
    exit_profile:         Dict[str, float]      # where physics leads after depth steps
    structural_narrative: str                   # human-readable constraint summary
    tension_axes:         List[str]             # axes showing blocked/contradicted states
    warp_signals:         List[Tuple[str, float]] # aggregate WarpDemands from all frames
    resonant_concept:     Optional[str]         # DPS crystal that matches entry profile
    resonance_score:      float                 # cosine similarity to best crystal
    confidence:           float                 # overall pattern confidence [0,1]
    reasoning_depth:      int                   # how many steps were taken
    computed_at:          float = field(default_factory=time.time)
    trace_id:             str  = field(default_factory=lambda: uuid.uuid4().hex[:8])


# ── Crystal resonance ──────────────────────────────────────────────────────────

def _cosine5(a: Dict[str, float], b: Dict[str, float]) -> float:
    dot = sum(a.get(ax, 0.5) * b.get(ax, 0.5) for ax in _AXES)
    ma  = math.sqrt(sum(a.get(ax, 0.5) ** 2 for ax in _AXES))
    mb  = math.sqrt(sum(b.get(ax, 0.5) ** 2 for ax in _AXES))
    if ma < 1e-9 or mb < 1e-9:
        return 0.0
    return dot / (ma * mb)


def _best_crystal_match(
    profile: Dict[str, float],
    dps: Any,
) -> Tuple[Optional[str], float]:
    """Return (concept, cosine) of best-matching DPS crystal. O(n) scan."""
    if dps is None:
        return None, 0.0
    best_concept, best_score = None, 0.0
    try:
        for crystal in dps.crystals.values():
            # Build 5D profile from crystal constraint_signature
            sig = getattr(crystal, "constraint_signature", None)
            if not sig or not isinstance(sig, dict):
                continue
            c_profile = {ax: float(sig.get(ax, 0.5) or 0.5) for ax in _AXES}
            score = _cosine5(profile, c_profile)
            if score > best_score:
                best_score = score
                best_concept = getattr(crystal, "concept", None)
    except Exception:
        pass
    return best_concept, round(best_score, 4)


# ── Main reasoning engine ──────────────────────────────────────────────────────

class ConstraintReasoner:
    """
    Constraint-native parallel reasoning engine.

    Reads IVM global polarity (X/T/N/B/A) and reasons forward through
    Aurora's constraint physics laws. Runs as the structural track alongside
    the semantic ThoughtBraid track every turn.

    Usage:
        reasoner = ConstraintReasoner.from_systems(systems)
        trace = reasoner.reason(profile, depth=3)
        ctx   = reasoner.to_process_context(trace, tick=turn_tick)
        space.register(ctx)   # integrates into ThoughtIntegrationSpace
    """

    # Minimum rule activation to include in narrative
    _ACTIVATION_THRESHOLD: float = 0.28

    # Minimum frame confidence for the trace to carry weight in integration
    _CONFIDENCE_FLOOR: float = 0.20

    # When structural vs semantic alignment is below this, emit WarpDemand
    _DIVERGENCE_THRESHOLD: float = 0.30

    def __init__(
        self,
        lattice:     Any = None,
        dimensional: Any = None,
    ) -> None:
        self._lattice     = lattice
        self._dimensional = dimensional
        self._dps         = getattr(dimensional, "dps", None) if dimensional else None

    @classmethod
    def from_systems(cls, systems: Dict[str, Any]) -> "ConstraintReasoner":
        return cls(
            lattice=systems.get("lattice"),
            dimensional=systems.get("dimensional"),
        )

    # ── Current IVM state accessor ────────────────────────────────────────────

    def current_profile(self) -> Dict[str, float]:
        """
        Read the IVM lattice's current global polarity as a 5D axis profile.
        Falls back to dimensional pressure vector, then to neutral (0.5).
        """
        # IVM global polarity — signed [-1, +1]; normalise to [0, 1]
        if self._lattice is not None and hasattr(self._lattice, "get_global_polarity"):
            try:
                pol = self._lattice.get_global_polarity()
                if pol:
                    return {ax: round(min(1.0, max(0.0, (float(pol.get(ax, 0.0)) + 1.0) / 2.0)), 3)
                            for ax in _AXES}
            except Exception:
                pass
        # Dimensional pressure vector — unsigned [0, 1]
        if self._dimensional is not None and hasattr(self._dimensional, "_current_pressure_vec"):
            try:
                pv = self._dimensional._current_pressure_vec()
                if pv:
                    return {ax: round(float(pv.get(ax, 0.5)), 3) for ax in _AXES}
            except Exception:
                pass
        return {ax: 0.5 for ax in _AXES}

    # ── Single reasoning step ─────────────────────────────────────────────────

    def step(self, profile: Dict[str, float], step_index: int = 0) -> ConstraintFrame:
        """
        Apply all inference rules to a profile. Return the resulting ConstraintFrame.
        """
        ist = _istates(profile)

        # Activate all rules
        activations: List[Tuple[_Rule, float]] = []
        for rule in _RULES:
            w = _check_rule(rule, ist, profile)
            if w >= self._ACTIVATION_THRESHOLD:
                activations.append((rule, w))

        # Sort by activation weight descending
        activations.sort(key=lambda x: x[1], reverse=True)

        dominant_pattern = (
            activations[0][0].structural_note if activations
            else "neutral constraint state"
        )

        # Collect warp signals from active rules that have triggers
        warp_signals: List[Tuple[str, float]] = [
            (rule.warp_trigger, rule.severity * weight)
            for rule, weight in activations
            if rule.warp_trigger is not None
        ]

        # Compute predicted next profile by summing deltas weighted by activation
        next_profile = dict(profile)
        total_rule_weight = sum(w for _, w in activations) or 1.0
        for rule, weight in activations:
            norm_w = weight / total_rule_weight
            for ax, delta in rule.next_delta.items():
                next_profile[ax] = round(
                    min(1.0, max(0.0, next_profile.get(ax, 0.5) + delta * norm_w)), 3
                )

        # Frame confidence: how strongly do the top rules fire?
        top_weight = activations[0][1] if activations else 0.0
        frame_confidence = round(min(1.0, top_weight * 1.2), 3)

        return ConstraintFrame(
            step=step_index,
            profile=dict(profile),
            istates=ist,
            active_rules=[(r.rule_id, round(w, 3)) for r, w in activations],
            dominant_pattern=dominant_pattern,
            next_profile=next_profile,
            warp_signals=warp_signals,
            frame_confidence=frame_confidence,
        )

    # ── Multi-step reasoning trace ────────────────────────────────────────────

    def reason(
        self,
        profile:   Dict[str, float],
        depth:     int = 3,
        user_text: str = "",
    ) -> ConstraintReasoningTrace:
        """
        Run the constraint reasoning chain from an entry profile.

        depth: how many physics steps to project forward (3 = near future)

        The trace IS the structural truth. It does not interpret meaning.
        It reports: this is the physics of what is happening and where
        the constraint field wants to go.
        """
        if not profile:
            profile = self.current_profile()

        frames: List[ConstraintFrame] = []
        current = {ax: float(profile.get(ax, 0.5)) for ax in _AXES}

        for i in range(max(1, depth)):
            frame = self.step(current, step_index=i)
            frames.append(frame)
            current = frame.next_profile

        exit_profile = frames[-1].next_profile
        tension_axes = self._tension_axes(frames)
        warp_signals = self._aggregate_warp_signals(frames)
        narrative    = self._narrative(frames)
        confidence   = self._confidence(frames)

        # DPS crystal resonance: what established pattern matches entry?
        resonant_concept, resonance_score = _best_crystal_match(profile, self._dps)

        # If a crystal strongly resonates, it enriches the narrative
        if resonant_concept and resonance_score > 0.78:
            narrative = f"{narrative} [resonates: {resonant_concept}]"

        return ConstraintReasoningTrace(
            frames=frames,
            entry_profile=dict(profile),
            exit_profile=exit_profile,
            structural_narrative=narrative,
            tension_axes=tension_axes,
            warp_signals=warp_signals,
            resonant_concept=resonant_concept,
            resonance_score=resonance_score,
            confidence=confidence,
            reasoning_depth=len(frames),
        )

    # ── ProcessContext bridge ──────────────────────────────────────────────────

    def to_process_context(self, trace: ConstraintReasoningTrace, tick: int = 0) -> Any:
        """
        Wrap the constraint trace as a ProcessContext for ThoughtIntegrationSpace.

        process_type='constraint' is a recognised type in the integration space
        (listed in ThoughtIntegrationSpace documentation alongside memory,
        sensory, predictive, emotion, linguistic, identity).

        The constraint context carries structural truth as its output state.
        The integration space reads it when assembling the ThoughtState.
        """
        try:
            from aurora_thought_formation import ProcessContext
        except ImportError:
            return None

        # Dominant tension axes drive axis_signature
        dominant_axes = trace.tension_axes or list(_AXES)

        # Unresolved tension weight: how many WARP signals fired?
        tension_weight = min(1.0, len(trace.warp_signals) * 0.20)

        return ProcessContext(
            process_id=f"constraint_reasoner_{trace.trace_id}",
            process_type="constraint",
            what_triggered_it="ivm_axis_state",
            what_it_is_operating_on=_profile_str(trace.entry_profile),
            current_output_state={
                "structural_narrative": trace.structural_narrative,
                "tension_axes":         trace.tension_axes,
                "warp_signals":         [
                    {"trigger": t, "severity": round(s, 3)}
                    for t, s in trace.warp_signals
                ],
                "resonant_concept":     trace.resonant_concept,
                "resonance_score":      trace.resonance_score,
                "exit_profile":         trace.exit_profile,
                "constraint_confidence": trace.confidence,
                "frames":               len(trace.frames),
            },
            self_relevance=trace.confidence,
            axis_signature=dominant_axes,
            active_axis_intensity=trace.confidence,
            unresolved_tension_weight=tension_weight,
            tick=tick,
            relevance_weight=0.85,          # structural truth is always relevant
            continuity_weight=1.0,
            self_pressure_weight=trace.confidence,
            relevance_decay=1.0,
        )

    # ── Semantic alignment check ───────────────────────────────────────────────

    def integrate(
        self,
        trace:          ConstraintReasoningTrace,
        semantic_state: Any,
        *,
        emit_warp:      bool = True,
    ) -> Dict[str, Any]:
        """
        Compare structural trace against semantic state.

        semantic_state: ThoughtState, dict, or string.

        Returns an alignment report. If alignment < _DIVERGENCE_THRESHOLD,
        emits WarpDemand(CONFLICTING_OUTPUTS) — the divergence is a signal,
        not an error.
        """
        alignment = self._compute_alignment(trace, semantic_state)

        if emit_warp and alignment < self._DIVERGENCE_THRESHOLD and trace.confidence > 0.4:
            try:
                from aurora_warp_protocol import warp_guard as _wg, WarpTrigger as _WT
                _wg(
                    source="constraint_reasoner",
                    layer="reasoning",
                    trigger=_WT.CONFLICTING_OUTPUTS,
                    unresolved_text=trace.structural_narrative,
                    expected={"structural": trace.structural_narrative},
                    actual={"semantic": str(semantic_state)[:120]},
                    participants=["semantic_track", "constraint_track"],
                    profile=trace.entry_profile,
                    severity=round(0.5 + (self._DIVERGENCE_THRESHOLD - alignment), 3),
                    persistence_key=f"divergence:{':'.join(sorted(trace.tension_axes))}",
                )
            except Exception:
                pass

        # Emit any collected WARP signals from the reasoning chain itself
        if emit_warp:
            self._emit_trace_warp_signals(trace)

        return {
            "alignment":            round(alignment, 3),
            "structural_grounded":  alignment >= 0.5,
            "structural_narrative": trace.structural_narrative,
            "tension_axes":         trace.tension_axes,
            "resonant_concept":     trace.resonant_concept,
            "confidence":           trace.confidence,
        }

    # ── Private helpers ────────────────────────────────────────────────────────

    def _tension_axes(self, frames: List[ConstraintFrame]) -> List[str]:
        """Axes that appear in tension/contradiction rule activations across frames."""
        tension: Dict[str, float] = {}
        contradiction_rules = {
            "contradiction_existence": ("X",),
            "contradiction_energy":    ("N",),
            "contradiction_agency":    ("A",),
            "contradiction_continuity":("T",),
            "exists_blocked":          ("X", "T"),
            "potential_inert":         ("T", "N"),
            "agency_detached":         ("A", "X"),
            "energy_unstructured":     ("N", "B"),
            "boundary_unacted":        ("B", "A"),
            "blocked_agency":          ("A", "T"),
            "dual_absence":            ("X", "T"),
            "action_collapse":         ("N", "A"),
        }
        for frame in frames:
            for rule_id, weight in frame.active_rules:
                for ax in contradiction_rules.get(rule_id, ()):
                    tension[ax] = max(tension.get(ax, 0.0), weight)

        return [ax for ax, w in sorted(tension.items(), key=lambda x: x[1], reverse=True) if w > 0.25]

    def _aggregate_warp_signals(
        self, frames: List[ConstraintFrame]
    ) -> List[Tuple[str, float]]:
        """Collect and de-duplicate WARP signals across all frames."""
        seen: Dict[str, float] = {}
        for frame in frames:
            for trigger, sev in frame.warp_signals:
                seen[trigger] = max(seen.get(trigger, 0.0), sev)
        return [(t, s) for t, s in sorted(seen.items(), key=lambda x: x[1], reverse=True)]

    def _emit_trace_warp_signals(self, trace: ConstraintReasoningTrace) -> None:
        """Emit WarpDemands for signals collected during reasoning."""
        if not trace.warp_signals:
            return
        try:
            from aurora_warp_protocol import warp_guard as _wg
        except ImportError:
            return
        for trigger, severity in trace.warp_signals:
            if severity < 0.35:
                continue
            try:
                _wg(
                    source="constraint_reasoner",
                    layer="reasoning",
                    trigger=trigger,
                    unresolved_text=trace.structural_narrative[:120],
                    profile=trace.entry_profile,
                    severity=round(min(1.0, severity), 3),
                    persistence_key=f"constraint:{trigger}:{':'.join(sorted(trace.tension_axes))}",
                )
            except Exception:
                pass

    def _narrative(self, frames: List[ConstraintFrame]) -> str:
        """Build a structural narrative from the dominant patterns across frames."""
        if not frames:
            return "neutral constraint state"
        # Collect dominant patterns, de-duplicate, take top 2
        seen: List[str] = []
        for frame in frames:
            note = frame.dominant_pattern
            if note not in seen:
                seen.append(note)
        parts = seen[:2]
        return " / ".join(parts) if parts else "neutral constraint state"

    def _confidence(self, frames: List[ConstraintFrame]) -> float:
        """Overall trace confidence: mean of frame confidences."""
        if not frames:
            return 0.0
        return round(sum(f.frame_confidence for f in frames) / len(frames), 3)

    def _compute_alignment(
        self,
        trace: ConstraintReasoningTrace,
        semantic_state: Any,
    ) -> float:
        """
        Compute structural ↔ semantic alignment [0, 1].

        Alignment is assessed by comparing which axes are under tension in
        the structural trace against the axis emphasis in the semantic state.

        If no semantic state axis data is available, neutral alignment (0.5).
        """
        if not trace.tension_axes:
            return 0.75  # no tension = neutral/positive alignment

        semantic_profile: Optional[Dict[str, float]] = None

        # Try to extract axis profile from semantic state
        if isinstance(semantic_state, dict):
            if any(k in semantic_state for k in _AXES):
                semantic_profile = {ax: float(semantic_state.get(ax, 0.5)) for ax in _AXES}
            elif "pressure_vec" in semantic_state:
                semantic_profile = {ax: float(semantic_state["pressure_vec"].get(ax, 0.5))
                                    for ax in _AXES}
        elif hasattr(semantic_state, "pressure_vec"):
            try:
                semantic_profile = {ax: float(semantic_state.pressure_vec.get(ax, 0.5))
                                    for ax in _AXES}
            except Exception:
                pass

        if semantic_profile is None:
            return 0.5  # no data — neutral

        # Alignment: cosine between structural exit profile and semantic profile
        return round(min(1.0, max(0.0, _cosine5(trace.exit_profile, semantic_profile))), 3)


# ── Utility ────────────────────────────────────────────────────────────────────

def _profile_str(profile: Dict[str, float]) -> str:
    return " ".join(f"{ax}={profile.get(ax, 0.5):.2f}" for ax in _AXES)


# ── Module-level singleton ─────────────────────────────────────────────────────

_global_reasoner: Optional[ConstraintReasoner] = None


def get_reasoner() -> ConstraintReasoner:
    """Return the global ConstraintReasoner, creating lazily if needed."""
    global _global_reasoner
    if _global_reasoner is None:
        _global_reasoner = ConstraintReasoner()
    return _global_reasoner


def install_reasoner(reasoner: ConstraintReasoner) -> None:
    """Install as global singleton at boot."""
    global _global_reasoner
    _global_reasoner = reasoner

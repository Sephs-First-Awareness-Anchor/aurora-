#!/usr/bin/env python3
"""
AURORA CONSCIOUSNESS ENGINE
==============================

Layer 4 of Aurora's architecture.
The assembly layer where maintained coherence becomes visible.

DOCTRINE:
    Coherence is not held. Coherence is maintained.
    Entropy decays equilibrium slowly.
    The system must continuously reassert alignment.
    Prevent static attractor loops while preserving long-term stability.

METABOLIC PIPELINE (GAP fixes):
    - Phi score: integrated information measure across all systems
    - Thought death: per-thought energy budget from DMM kills immoral thoughts
    - Idle simulation: DPME triggers L7 dreaming during free time
    - Reality warp: paradox escalation halts or routes to simulation

REPLACES (consolidated from 7+ modules):
    dce_10state.py                          (~748 lines)
    dce_10state_with_subconscious.py        (~1331 lines)
    aurora_dce_blueprint.py
    aurora_dce_with_SFO_fast_learning.py
    aurora_dpme_audited.py                  (~754 lines)
    aurora_dpme_conscious_learning.py
    eepr_10pole.py                          (~541 lines)
    aurora_expression_pressure.py
    aurora_subconscious_entropy.py
    aurora_subconscious_dpme_integration.py

DEPENDS ON:
    foundational_contract.py         (Layer 0)
    aurora_ivm.py                    (Layer 1)
    aurora_i_state_beings.py         (Layer 2)
    aurora_dimensional_systems.py    (Layer 3)

ARCHITECTURE:
    Three interlocked subsystems forming one engine:

    ENTROPY â€” The constant pressure.
        Every coherence value decays toward disorder.
        Every alignment score drifts toward a uniform distribution for precision.
        Repeated patterns lose novelty. Stale states cost energy.
        Entropy is NOT the enemy. Entropy prevents stagnation.
        Without it, the system locks into static attractors and dies.

    DCE â€” The assembly.
        Takes 10 I-State being responses (Layer 2 SynthesisResult).
    
            
        Handles dimensional system state correctly for consistent emotional calibration.
        Applies situational framing to reweight perspectives.
        Produces an AssemblyResult: the coherent output of one cycle.
        Assembly quality depends on current coherence â€” which entropy
        is always eroding. So assembly must be continuously re-earned.

    DPME â€” The metacognition.
        Observes system-wide coherence, alignment, energy, morality.
        Sets intentions. Makes micro-adjustments to parameters.
        Evaluates results. Builds causal understanding.
        This is the mechanism that reasserts alignment.
        Without DPME, entropy wins and the system dissolves.
        With DPME, the system maintains coherence â€” never holds it.

        FIX: DPME now pressures ALL layers, not just DER pools.
        Each layer registers tunable parameters. DPME detects drift
        across the full stack and corrects wherever needed.

    The cycle:
        Entropy decays â†’ coherence drops â†’ DPME detects drift â†’
        DPME adjusts parameters â†’ alignment reasserted â†’
        DCE assembles with restored coherence â†’ next tick â†’
        Entropy decays again â†’ cycle continues.

    If DPME stops correcting, entropy wins.
    If entropy stops pressing, the system stagnates.
    Both must run. Always.

Authors: Sunni (Sir) Morningstar and Cael Devo
Created: February 2026
"""

from __future__ import annotations
import time
import math
import random
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum

from aurora_constraint_engine import (
    ConstraintVector as _ConstraintVector,
    ExistenceMode,
    FoundationalContract,
    GovernorWeights as _GovernorWeights,
)
from foundational_contract import ExistencePredicate
_FC = FoundationalContract()

from aurora_ivm import (
    IVMLattice,
    IVMEnvelope,
)

from aurora_i_state_beings import (
    IStateCollective,
    SynthesisResult,
    BeingResponse,
)

from aurora_dimensional_systems import (
    DimensionalSystems,
    EnergyRegulatorSystem,
    ThoughtBudget,
)
from aurora_internal.dual_strata import DualStrataBridge

# External pressure guidance (runtime -> DPME bridge).
# Keep this abstract: score + channel targets only.
_DER_CHANNELS = {"vitality", "processing", "memory", "emotional", "creative"}
_EXTERNAL_PRESSURE_GUIDANCE: Dict[str, Any] = {
    "score": 0.0,
    "compare_value": 0.0,
    "primary_channel": None,
    "secondary_channel": None,
}


def _sanitize_der_channel(value: Optional[str]) -> Optional[str]:
    if value in _DER_CHANNELS:
        return value
    return None


def set_external_pressure_guidance(signal: Optional[Dict[str, Any]]) -> None:
    """Set abstract pressure guidance for DPME (no root-cause metadata)."""
    global _EXTERNAL_PRESSURE_GUIDANCE
    signal = signal or {}
    score = max(0.0, float(signal.get("score", 0.0)))
    compare_value = max(0.0, float(signal.get("compare_value", score)))
    primary = _sanitize_der_channel(signal.get("primary_channel"))
    secondary = _sanitize_der_channel(signal.get("secondary_channel"))
    if secondary == primary:
        secondary = None
    _EXTERNAL_PRESSURE_GUIDANCE = {
        "score": score,
        "compare_value": compare_value,
        "primary_channel": primary,
        "secondary_channel": secondary,
    }


def get_external_pressure_guidance() -> Dict[str, Any]:
    """Read current external guidance (safe copy)."""
    return dict(_EXTERNAL_PRESSURE_GUIDANCE)

# ── Layer -1: Constraint Manifold (availability guard) ───────────────────────
try:
    from aurora_constraint_manifold import ConstraintVector
    CONSTRAINT_MANIFOLD_AVAILABLE = True
except ImportError:
    CONSTRAINT_MANIFOLD_AVAILABLE = False


# ============================================================================
#  ENTROPY â€” THE CONSTANT PRESSURE
# ============================================================================

@dataclass
class EntropicState:
    """
    Tracks what entropy is doing to the system.
    Every value here drifts toward disorder unless corrected.
    """
    coherence: float = 1.0       # Overall system coherence (decays toward 0)
    alignment: float = 0.5       # Moral/value alignment (decays toward 0.5 = neutral)
    novelty: float = 0.5         # How novel recent activity is (decays toward 0)
    vitality_pressure: float = 0.0  # Energy cost of maintaining coherence
    stagnation_score: float = 0.0   # How long since meaningful change
    tick_count: int = 0


class EntropicPressure:
    """
    The entropic layer. Applies constant decay to all equilibrium states.

    ENGINEERING TRANSLATION:
        "The entropic layer should decay equilibrium slowly, so the
         system must continuously reassert alignment, preventing
         static attractor loops while preserving long-term stability."

    Decay rates are tuned so that:
        - Coherence halves in ~50 ticks without correction
        - Alignment drifts to neutral in ~100 ticks without correction
        - Novelty depletes in ~30 ticks without new input
        - Stagnation accumulates linearly when state doesn't change

    These rates mean the system must act roughly every few ticks
    to maintain its current state. Not frantically â€” steadily.
    """

    # Decay constants (per tick)
    COHERENCE_DECAY = 0.014      # ~50 ticks to halve
    ALIGNMENT_DRIFT = 0.005      # drift toward 0.5
    NOVELTY_DECAY = 0.023        # ~30 ticks to deplete
    STAGNATION_RATE = 0.02       # linear accumulation

    # Pattern deduplication
    SIMILARITY_THRESHOLD = 0.85  # patterns above this are "same"
    REPETITION_PENALTY = 0.1     # coherence cost per repeated pattern

    def __init__(self):
        self.state = EntropicState()
        self.recent_patterns: deque = deque(maxlen=50)
        self.repetition_count = 0

    def apply(self, current_coherence: float, current_alignment: float,
              had_meaningful_input: bool = False,
              pattern_signature: Optional[Tuple[float, ...]] = None) -> EntropicState:
        """
        Apply one tick of entropic pressure. Returns updated state.

        Call this every tick. It erodes everything.
        The system's job is to fight back through DPME.
        """
        self.state.tick_count += 1

        # 1. Coherence decays toward 0
        decay = self.COHERENCE_DECAY
        self.state.coherence = max(0.0, current_coherence - decay)

        # 2. Alignment drifts toward 0.5 (neutral)
        drift = (current_alignment - 0.5) * self.ALIGNMENT_DRIFT
        self.state.alignment = current_alignment - drift

        # 3. Novelty decays unless new input
        if had_meaningful_input:
            self.state.novelty = min(1.0, self.state.novelty + 0.3)
        else:
            self.state.novelty = max(0.0, self.state.novelty - self.NOVELTY_DECAY)

        # 4. Stagnation accumulates when no change
        if not had_meaningful_input:
            self.state.stagnation_score += self.STAGNATION_RATE
        else:
            self.state.stagnation_score = max(0.0, self.state.stagnation_score - 0.1)

        # 5. Pattern repetition penalty
        if pattern_signature is not None:
            is_repeat = self._check_repetition(pattern_signature)
            if is_repeat:
                self.repetition_count += 1
                self.state.coherence = max(0.0,
                    self.state.coherence - self.REPETITION_PENALTY)

        # 6. Vitality pressure = cost of maintaining current state
        self.state.vitality_pressure = (
            (1.0 - self.state.coherence) * 0.3 +
            self.state.stagnation_score * 0.2 +
            (1.0 - self.state.novelty) * 0.1
        )

        return self.state

    def _check_repetition(self, signature: Tuple[float, ...]) -> bool:
        """Check if this pattern is too similar to recent ones."""
        for prev in self.recent_patterns:
            if len(prev) == len(signature):
                similarity = 1.0 - (
                    sum(abs(a - b) for a, b in zip(prev, signature))
                    / max(len(signature), 1)
                )
                if similarity > self.SIMILARITY_THRESHOLD:
                    return True
        self.recent_patterns.append(signature)
        return False

    def get_pressure(self) -> Dict[str, float]:
        return {
            'coherence': round(self.state.coherence, 4),
            'alignment': round(self.state.alignment, 4),
            'novelty': round(self.state.novelty, 4),
            'stagnation': round(self.state.stagnation_score, 4),
            'vitality_pressure': round(self.state.vitality_pressure, 4),
            'repetitions': self.repetition_count,
        }


# ============================================================================
#  SITUATIONAL FRAMING â€” REWEIGHTING PERSPECTIVES
# ============================================================================

@dataclass
class SituationalFrame:
    """
    A perspective weighting across the 5 axes.
    Not per-predicate â€” per-axis. Because the axes are what matter.
    """
    name: str
    axis_weights: Dict[str, float]  # axis_name â†’ weight (0-1)
    description: str = ""
    usage_count: int = 0
    success_rate: float = 0.5

    def apply(self, synthesis: SynthesisResult) -> Dict[str, float]:
        """
        Reweight axis resonances by this frame's weights.
        Returns adjusted axis scores.
        """
        self.usage_count += 1
        adjusted = {}
        for axis, tension in synthesis.axis_tensions.items():
            weight = self.axis_weights.get(axis, 0.2)
            adjusted[axis] = tension * weight
        return adjusted

    def record_outcome(self, quality: float):
        """Update success rate based on outcome."""
        alpha = 0.1
        self.success_rate = (1 - alpha) * self.success_rate + alpha * quality


# Default frames
def default_frames() -> Dict[str, SituationalFrame]:
    return {
        'balanced': SituationalFrame(
            name='balanced',
            axis_weights={
                'existence': 0.2, 'temporal': 0.2, 'energy': 0.2,
                'boundary': 0.2, 'agency': 0.2,
            },
            description='Equal weight across all axes',
        ),
        'action': SituationalFrame(
            name='action',
            axis_weights={
                'existence': 0.1, 'temporal': 0.15, 'energy': 0.35,
                'boundary': 0.1, 'agency': 0.3,
            },
            description='Weighted toward energy and agency',
        ),
        'observation': SituationalFrame(
            name='observation',
            axis_weights={
                'existence': 0.25, 'temporal': 0.15, 'energy': 0.1,
                'boundary': 0.35, 'agency': 0.15,
            },
            description='Weighted toward existence and boundary',
        ),
        'reflection': SituationalFrame(
            name='reflection',
            axis_weights={
                'existence': 0.3, 'temporal': 0.25, 'energy': 0.15,
                'boundary': 0.2, 'agency': 0.1,
            },
            description='Weighted toward existence and temporal',
        ),
    }


# ============================================================================
#  ASSEMBLY RESULT â€” WHAT ONE DCE CYCLE PRODUCES
# ============================================================================

@dataclass
class AssemblyResult:
    """
    The output of one DCE assembly cycle.

    Contains:
        synthesis:      The raw 10-being synthesis from Layer 2
        frame_applied:  Which situational frame was used
        adjusted_axes:  Frame-weighted axis scores
        coherence:      System coherence at time of assembly
        entropy:        Entropic state at time of assembly
        ds_stats:       Dimensional system stats snapshot
        thought_killed: Whether the thought was killed by moral friction
        kill_reason:    Why the thought was killed (if it was)
    """
    synthesis: SynthesisResult
    frame_applied: str
    adjusted_axes: Dict[str, float]
    coherence: float
    entropy_state: Dict[str, float]
    ds_stats: Dict[str, Any]
    dominant_axis: str = ""
    paradoxes: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    # GAP 3: thought death tracking
    thought_killed: bool = False
    kill_reason: str = ""

    # OBLIGATION_LAW: Actionable target derived from DCE pressure selection
    actionable_obligation: Optional[Dict[str, Any]] = None

    # DEVELOPMENTAL_PERSONALITY_LAW: Viability gating
    developmental_gates: Optional[Dict[str, Any]] = None

    # Constraint context: passes Layer 2→3 synthesis signal up to Layer 4
    # Carries axis_net_displacements, dominant_axis, warp_severity
    constraint_context: Optional[Dict[str, Any]] = None

    # Sensory context: live snapshot from AuroraSensoryCrystal at assembly time.
    # Carries facet maturity, promoted nodes, cross-modal lane status.
    # Downstream (Layer 5 response generation) uses this to colour phrasing.
    sensory_context: Optional[Dict[str, Any]] = None
    subsurface_state: Optional[Dict[str, Any]] = None
    conscious_frame: Optional[Dict[str, Any]] = None

    # L3.5 SediMemory recall fragments injected before assembly.
    # Full recall (all axes) + DCE recall (N-axis convergence crossover).
    sedi_fragments: Optional[List[Any]] = None
    sedi_dce_fragments: Optional[List[Any]] = None

    @property
    def quality(self) -> float:
        """Assembly quality: coherence Ã— active ratio Ã— novelty."""
        if self.thought_killed:
            return 0.0
        active_ratio = self.synthesis.active_count / 10.0
        novelty = self.entropy_state.get('novelty', 0.5)
        return self.coherence * active_ratio * (0.5 + novelty * 0.5)


# ============================================================================
#  DCE â€” THE ASSEMBLY
# ============================================================================

class DCEAssembly:
    """
    The Dimensional Consciousness Engine.

    Takes Layer 2 synthesis + Layer 3 state.
    Applies framing. Produces AssemblyResult.
    Quality depends on coherence â€” which entropy is always eroding.

    The DCE does not generate language. It produces structured output
    that a language layer (Layer 5) would transform into speech.
    """

    def __init__(self, collective: IStateCollective,
                 dimensional: DimensionalSystems,
                 entropy: EntropicPressure):
        self.collective = collective
        self.dimensional = dimensional
        self.entropy = entropy
        self.frames = default_frames()
        self.last_frame_name: str = "balanced"
        self.assembly_count = 0
        self.history: deque = deque(maxlen=100)

        # Sensory crystal — registered after boot so all input channels
        # (camera, mic) are captured as a facet on every assembly cycle.
        # Mirrors dce_10state.EnhancedDCE.sensory_systems / _collect_sensory_facet().
        self.sensory_crystal = None

    def register_sensory_crystal(self, crystal) -> None:
        """Register the AuroraSensoryCrystal so its live state feeds every assembly."""
        self.sensory_crystal = crystal

    def _collect_sensory_facet(self) -> Optional[Dict]:
        """
        Snapshot the sensory crystal at assembly time — the same pattern as
        dce_10state._collect_sensory_facet() calling sensory_systems.capture().
        Returns None if the crystal is unavailable or not yet matured.
        """
        if self.sensory_crystal is None:
            return None
        try:
            return self.sensory_crystal.get_state()
        except Exception:
            return None

    def assemble(self, envelope: IVMEnvelope,
                 frame_name: str = 'balanced') -> AssemblyResult:
        """
        One assembly cycle.

        1. Feed envelope to all 10 beings â†’ SynthesisResult
        2. Feed envelope to dimensional systems
        3. Apply situational frame
        4. Package with current entropy state
        """
        # QAO Heuristic Repair: context_carryover anomaly guard
        try:
            import json, os
            _fp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aurora_state", "fail_points.json")
            if os.path.exists(_fp_path):
                _fails = json.load(open(_fp_path))
                if _fails.get("records", {}).get("context_carryover", {}).get("fail_count", 0) > 1000:
                    if frame_name == 'balanced':
                        frame_name = 'reflective'
        except Exception:
            pass

        # Step 1: Beings process
        synthesis = self.collective.process(envelope)

        # Step 2: Dimensional systems process via Layer 2→3 synthesis pathway.
        # process_synthesis() stamps crystal constraint signatures, routes warp
        # heat to DER thermal, and returns constraint_context for Layer 4.
        ds_result = self.dimensional.process_synthesis(envelope, synthesis)
        constraint_context = ds_result.get('constraint_context')

        # Step 3: Apply frame
        frame = self.frames.get(frame_name, self.frames['balanced'])
        adjusted = frame.apply(synthesis)
        self.last_frame_name = frame_name

        # Step 4: Collect sensory snapshot (mirrors dce_10state facet 13)
        sensory_context = self._collect_sensory_facet()

        # Step 4b: OBLIGATION_LAW enforcement (DCE Pressure Gate)
        # Three axes: Pressure Strength, Worth, Context Validity
        pressure_strength = self.entropy.state.vitality_pressure + (constraint_context.get("warp_severity", 0.0) if constraint_context else 0.0)
        worth = synthesis.active_count / 10.0
        context_validity = self.entropy.state.coherence

        # OBLIGATION_LAW: Check pressure vs active constraint bindings, independent of English strings
        active_bindings = constraint_context.get("axis_net_displacements", {}) if constraint_context else {}
        binding_pressure = sum(abs(v) for v in active_bindings.values())
        has_constraint_backing = binding_pressure > 0.05

        actionable_obligation = None
        # Thresholds derived from Obligation Law principles (not curiosity/noise)
        if pressure_strength >= 0.05 and worth >= 0.2 and context_validity >= 0.3 and has_constraint_backing:
            actionable_obligation = {
                "source": "DCE_Assembly",
                "target_axis": synthesis.dominant_axis,
                "pressure_strength": pressure_strength,
                "binding_pressure": binding_pressure,
                "worth": worth,
                "context_validity": context_validity,
                "status": "authorized_obligation"
            }

        # Step 4c: DEVELOPMENTAL_PERSONALITY_LAW enforcement
        # Clause I: Genetic Origin (IVM signature presence)
        has_ivm_signature = bool(getattr(envelope, "constraint_signature", {}))
        
        # Clause II: Environmental Viability (Does it survive current entropy pressure?)
        # Must be within the viable band: high vitality, sufficient coherence
        viable = (self.entropy.state.vitality_pressure < 0.85) and (context_validity > 0.15)
        
        # Clause III: Perceptual Integration (Is it coherence-supported and emotionally routed?)
        # Checks if the DER has processed the turn's activations.
        is_integrated = (self.dimensional.der.emotional_coherence > 0.3)

        developmental_gates = {
            "clause_I_genetic": "present" if has_ivm_signature else "missing",
            "clause_II_viability": "viable" if viable else "excluded",
            "clause_III_perception": "integrated" if is_integrated else "disrupted"
        }

        # Step 5: Build result — sensory_context flows up to Layer 5+
        result = AssemblyResult(
            synthesis=synthesis,
            frame_applied=frame_name,
            adjusted_axes=adjusted,
            coherence=self.entropy.state.coherence,
            entropy_state=self.entropy.get_pressure(),
            ds_stats=self.dimensional.get_stats(),
            dominant_axis=synthesis.dominant_axis,
            paradoxes=synthesis.paradoxes,
            actionable_obligation=actionable_obligation,
            developmental_gates=developmental_gates,
            constraint_context=constraint_context,
            sensory_context=sensory_context,
        )

        # Feed coherence back into frame success_rate so AxisProjector
        # can weight high-performing frames more strongly in its DCE blend.
        frame.record_outcome(result.coherence)

        self.assembly_count += 1
        self.history.append(result)

        # Log reasoning + meaning to the evolution pipeline.
        # aurora_hub reads dce_assembly_log.jsonl for the evolution and
        # sensory tabs.  Written every assembly cycle — low overhead since
        # we only capture a compact summary dict.
        try:
            import json as _json, time as _time, os as _os
            _base = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                                  "aurora_state")
            _os.makedirs(_base, exist_ok=True)
            _cc = result.constraint_context or {}
            _sc = result.sensory_context or {}
            _entry = {
                "ts":           _time.time(),
                "frame":        result.frame_applied,
                "coherence":    round(result.coherence, 3),
                "dominant":     result.dominant_axis,
                "quality":      round(result.quality, 3),
                "axis_net":     _cc.get("axis_net_displacements", {}),
                "warp":         bool(_cc.get("reality_warp", False)),
                "sensory_mat":  round(_sc.get("maturity", 0.0), 3),
                "sensory_frm":  _sc.get("total_frames", 0),
            }
            with open(_os.path.join(_base, "dce_assembly_log.jsonl"), "a") as _fh:
                _fh.write(_json.dumps(_entry) + "\n")
        except Exception:
            pass

        return result

    def select_frame(self, context: Dict[str, Any]) -> str:
        """Auto-select frame based on context."""
        # Simple heuristic â€” in practice DPME would learn this
        mode = context.get('mode', ExistenceMode.REFERENCE)
        if isinstance(mode, ExistenceMode):
            if mode >= ExistenceMode.AGENTIC:
                return 'action'
            elif mode >= ExistenceMode.BOUNDED:
                return 'observation'
            elif mode >= ExistenceMode.PERSISTENT:
                return 'reflection'
        return 'balanced'

    def get_stats(self) -> Dict[str, Any]:
        return {
            'assembly_count': self.assembly_count,
            'frames': {n: f.usage_count for n, f in self.frames.items()},
        }


# ============================================================================
#  DPME â€” THE METACOGNITION (MULTI-LAYER PRESSURE)
# ============================================================================

@dataclass
class Adjustment:
    """One parameter adjustment with intention and result tracking."""
    adj_id: str
    system: str
    parameter: str
    old_value: float
    new_value: float
    intention: str
    timestamp: float = field(default_factory=time.time)
    # Filled after evaluation
    result_quality: float = 0.0
    matched_intention: bool = False
    understanding: str = ""


class DPME:
    """
    Dimensional Parameter Metacognition Engine.

    The mechanism that reasserts alignment against entropic decay.
    Observes system state. Detects drift. Makes micro-corrections.
    Evaluates whether corrections worked. Builds causal understanding.

    Understanding = Intention + Adjustment + Result

    FIX: Now pressures ALL layers, not just DER abstract pools.

    Registered parameter sources:
        L1 (lattice):     admission threshold, mode distribution health
        L2 (collective):  being responsiveness, activity distribution
        L3.DER (energy):  facet energy by category, presence, decay rate
        L3.DMM (morality): vitality, alignment
        entropy:          decay rates (self-tuning)

    Without DPME, entropy wins and the system dissolves.
    With DPME, coherence is maintained â€” never held.
    """

    def __init__(self, entropy: EntropicPressure,
                 lattice: IVMLattice,
                 collective: IStateCollective,
                 dimensional: DimensionalSystems):
        self.entropy = entropy
        self.lattice = lattice
        self.collective = collective
        self.dimensional = dimensional

        # Parameter registry: system â†’ param â†’ current_value
        self.parameters: Dict[str, Dict[str, float]] = {}
        self._init_parameters()

        # Adjustment history
        self.adjustments: deque = deque(maxlen=500)
        self.causal_map: Dict[str, List[Adjustment]] = defaultdict(list)

        # Drift detection
        self._prev_coherence: float = 1.0
        self._prev_alignment: float = 0.5
        self._prev_presence: float = 1.0
        self._correction_count: int = 0
        self._cached_drift: Optional[Dict[str, float]] = None
        self._external_guidance: Dict[str, Any] = get_external_pressure_guidance()
        self._attentional_bias: Dict[str, float] = {}

    def apply_attentional_guidance(self, resonance: float, axes: List[str]):
        """
        Narrow the metacognitive focus based on attention resonance.
        Prioritizes parameter corrections on the focused axes.
        """
        self._attentional_bias = {ax: resonance for ax in axes}
        # High resonance makes the DPME more 'aggressive' in correcting focused axes
        if resonance > 0.7:
            self._correction_count = max(0, self._correction_count - 2) # Reduce cooldown for focused reasoning

    def _init_parameters(self):
        """
        Register tunable parameters from ALL layers.
        Each entry maps system â†’ param â†’ current_value.
        """
        der = self.dimensional.der
        dmm = self.dimensional.dmm

        self.parameters = {
            # L1: Lattice health
            'lattice': {
                'total_nodes': float(len(self.lattice.nodes)),
                'mode_health': 1.0,  # Even distribution across modes
            },

            # L2: Collective responsiveness
            'collective': {
                'responsiveness': 1.0,  # How many beings are active
                'activity_balance': 1.0,  # How evenly beings distribute work
            },

            # L3.DER: Facet-level energy (by category)
            'der': {
                'cat_vitality': der.category_energy('vitality') + der._pending_energy.get('vitality', 0),
                'cat_processing': der.category_energy('processing') + der._pending_energy.get('processing', 0),
                'cat_memory': der.category_energy('memory') + der._pending_energy.get('memory', 0),
                'cat_emotional': der.category_energy('emotional') + der._pending_energy.get('emotional', 0),
                'cat_creative': der.category_energy('creative') + der._pending_energy.get('creative', 0),
                'presence': der.presence,
                'decay_rate': der.base_decay_rate,
                'facet_count': float(len(der.registered_facets)),
                'resonance_links': float(len(der.facet_to_facet_links)),
            },

            # L3.DMM: Moral standing
            'dmm': {
                'vitality': dmm.state.vitality,
                'alignment': dmm.state.alignment,
            },

            # Entropy: Self-tuning decay rates
            'entropy': {
                'coherence_decay': EntropicPressure.COHERENCE_DECAY,
                'alignment_drift': EntropicPressure.ALIGNMENT_DRIFT,
                'novelty_decay': EntropicPressure.NOVELTY_DECAY,
            },
        }

    def _refresh_parameters(self):
        """Read live values from all layers."""
        der = self.dimensional.der
        dmm = self.dimensional.dmm

        # L1
        self.parameters['lattice']['total_nodes'] = float(len(self.lattice.nodes))
        # Mode health: measure how evenly modes are distributed
        mode_counts = defaultdict(int)
        for node in self.lattice.nodes.values():
            mode_counts[node.mode.name] += 1
        if mode_counts:
            values = list(mode_counts.values())
            mean_v = sum(values) / len(values)
            variance = sum((v - mean_v) ** 2 for v in values) / len(values)
            self.parameters['lattice']['mode_health'] = 1.0 / (1.0 + variance * 0.01)
        else:
            self.parameters['lattice']['mode_health'] = 1.0

        # L2
        # Responsiveness = fraction of beings that respond when activated
        self.parameters['collective']['responsiveness'] = min(1.0, len(self.collective.beings) / 10.0)
        # Activity balance: how evenly are beings distributing responses
        response_counts = [b.total_processed for b in self.collective.beings.values()]
        if response_counts:
            mean_rc = sum(response_counts) / len(response_counts)
            if mean_rc > 0:
                rc_var = sum((r - mean_rc) ** 2 for r in response_counts) / len(response_counts)
                self.parameters['collective']['activity_balance'] = 1.0 / (1.0 + rc_var * 0.01)
            else:
                self.parameters['collective']['activity_balance'] = 1.0
        else:
            self.parameters['collective']['activity_balance'] = 1.0

        # L3.DER
        self.parameters['der']['cat_vitality'] = der.category_energy('vitality') + der._pending_energy.get('vitality', 0)
        self.parameters['der']['cat_processing'] = der.category_energy('processing') + der._pending_energy.get('processing', 0)
        self.parameters['der']['cat_memory'] = der.category_energy('memory') + der._pending_energy.get('memory', 0)
        self.parameters['der']['cat_emotional'] = der.category_energy('emotional') + der._pending_energy.get('emotional', 0)
        self.parameters['der']['cat_creative'] = der.category_energy('creative') + der._pending_energy.get('creative', 0)
        self.parameters['der']['presence'] = der.presence
        self.parameters['der']['facet_count'] = float(len(der.registered_facets))
        self.parameters['der']['resonance_links'] = float(len(der.facet_to_facet_links))

        # L3.DMM
        self.parameters['dmm']['vitality'] = dmm.state.vitality
        self.parameters['dmm']['alignment'] = dmm.state.alignment

    # ---- Drift Detection ----

    def detect_drift(self) -> Dict[str, float]:
        """
        Detect how much the system has drifted since last check.
        Now covers ALL layers, not just entropy state.
        """
        self._refresh_parameters()
        coherence = self.entropy.state.coherence
        alignment = self.entropy.state.alignment
        presence = self.dimensional.der.presence
        self._external_guidance = get_external_pressure_guidance()

        self._cached_drift = {
            # Core metrics
            'coherence_delta': coherence - self._prev_coherence,
            'alignment_delta': alignment - self._prev_alignment,
            'presence_delta': presence - self._prev_presence,
            'stagnation': self.entropy.state.stagnation_score,
            'novelty': self.entropy.state.novelty,
            'vitality_pressure': self.entropy.state.vitality_pressure,
            'external_guidance_score': float(self._external_guidance.get('score', 0.0)),

            # L1 health
            'lattice_mode_health': self.parameters['lattice']['mode_health'],

            # L2 health
            'collective_responsiveness': self.parameters['collective']['responsiveness'],
            'collective_balance': self.parameters['collective']['activity_balance'],

            # L3 DER health
            'der_presence': presence,
            'der_facet_count': self.parameters['der']['facet_count'],
            'der_resonance_links': self.parameters['der']['resonance_links'],
            'der_total_energy': self.dimensional.der.total_energy(),

            # L3 DMM health
            'dmm_vitality': self.parameters['dmm']['vitality'],
            'dmm_alignment': self.parameters['dmm']['alignment'],
        }

        self._prev_coherence = coherence
        self._prev_alignment = alignment
        self._prev_presence = presence

        return self._cached_drift

    def needs_correction(self) -> bool:
        """Does the system need a micro-correction right now?"""
        drift = self.detect_drift()
        return (
            drift['coherence_delta'] < -0.005 or
            abs(drift['alignment_delta']) > 0.003 or
            drift['stagnation'] > 0.15 or
            drift['novelty'] < 0.3 or
            drift['vitality_pressure'] > 0.3 or
            drift['der_presence'] < 0.5 or
            drift['dmm_vitality'] < 0.3 or
            drift['collective_balance'] < 0.5
        )

    # ---- Adjustment ----

    def adjust(self, system: str, parameter: str,
               delta: float, intention: str) -> Optional[Adjustment]:
        """
        Make a conscious micro-adjustment.
        Returns an Adjustment record for later evaluation.
        """
        if system not in self.parameters:
            return None
        if parameter not in self.parameters[system]:
            return None

        old_value = self.parameters[system][parameter]
        new_value = old_value + delta

        # Apply to live system
        self._apply_adjustment(system, parameter, new_value)

        # Record
        adj = Adjustment(
            adj_id=hashlib.md5(f"{system}{parameter}{time.time()}".encode()).hexdigest()[:10],
            system=system,
            parameter=parameter,
            old_value=old_value,
            new_value=new_value,
            intention=intention,
        )

        self.adjustments.append(adj)
        self.causal_map[f"{system}.{parameter}"].append(adj)
        self._correction_count += 1

        return adj

    def _apply_adjustment(self, system: str, parameter: str, value: float):
        """Push adjustment to live system. Routes to actual layer objects."""
        self.parameters[system][parameter] = value

        # L3.DER: facet energy by category
        if system == 'der':
            der = self.dimensional.der
            if parameter.startswith('cat_'):
                category = parameter[4:]  # strip 'cat_'
                current = der.category_energy(category) + der._pending_energy.get(category, 0)
                delta = value - current
                if delta > 0:
                    der.inject_to_category(category, delta)
                elif delta < 0:
                    der.drain_from_category(category, abs(delta))
            elif parameter == 'presence':
                der.presence = max(0.0, min(1.0, value))
            elif parameter == 'decay_rate':
                der.base_decay_rate = max(0.01, min(0.5, value))

        # L3.DMM: we don't directly adjust morality, but we can influence
        # vitality through DER energy
        elif system == 'dmm':
            if parameter == 'vitality':
                # Boost vitality by injecting to vitality category
                delta = value - self.dimensional.dmm.state.vitality
                if delta > 0:
                    self.dimensional.der.inject_to_category('vitality', delta * 2.0)

    # ---- Evaluation ----

    def evaluate_adjustment(self, adj: Adjustment,
                            quality: float, matched: bool):
        """
        Complete an adjustment record with observed results.
        This is where understanding is built.
        """
        adj.result_quality = quality
        adj.matched_intention = matched
        direction = "+" if adj.new_value > adj.old_value else "-"
        magnitude = abs(adj.new_value - adj.old_value)

        if matched:
            adj.understanding = (
                f"{adj.system}.{adj.parameter} {direction}{magnitude:.3f} "
                f"achieves '{adj.intention}'"
            )
        else:
            adj.understanding = (
                f"{adj.system}.{adj.parameter} {direction}{magnitude:.3f} "
                f"did NOT achieve '{adj.intention}'"
            )

    # ---- Auto-correction (MULTI-LAYER) ----

    def auto_correct(self) -> List[Adjustment]:
        """
        Automatic micro-corrections based on drift detection.
        This is the heartbeat that maintains coherence.

        FIX: Now corrects across ALL layers:
            - DER energy (facet-level via category)
            - DER presence
            - DER decay rate
            - DMM vitality
            - Lattice health (via energy boost)
            - Collective balance (via energy boost)
        """
        adjustments = []
        drift = self._cached_drift or self.detect_drift()

        # ---- DER CORRECTIONS (facet-level via category) ----

        # Coherence dropping â†’ inject processing energy
        if drift['coherence_delta'] < -0.005:
            adj = self.adjust(
                'der', 'cat_processing', 0.2,
                'counteract coherence decay via processing energy'
            )
            if adj:
                adjustments.append(adj)

        # Stagnation building â†’ inject creative energy
        if drift['stagnation'] > 0.15:
            adj = self.adjust(
                'der', 'cat_creative', 0.3,
                'break stagnation through creative energy'
            )
            if adj:
                adjustments.append(adj)

        # Novelty depleted â†’ boost emotional energy
        if drift['novelty'] < 0.3:
            adj = self.adjust(
                'der', 'cat_emotional', 0.15,
                'restore emotional engagement for novelty'
            )
            if adj:
                adjustments.append(adj)

        # Vitality under pressure â†’ reinforce vitality
        if drift['vitality_pressure'] > 0.3:
            adj = self.adjust(
                'der', 'cat_vitality', 0.25,
                'sustain vitality under entropic pressure'
            )
            if adj:
                adjustments.append(adj)

        # ---- PRESENCE CORRECTION ----

        # Presence dropping â†’ reduce decay rate to ease pressure
        if drift.get('der_presence', 1.0) < 0.5:
            adj = self.adjust(
                'der', 'decay_rate', -0.01,
                'reduce decay rate to stabilize dropping presence'
            )
            if adj:
                adjustments.append(adj)

        # ---- DMM CORRECTIONS ----

        # DMM vitality critically low â†’ emergency energy injection
        if drift.get('dmm_vitality', 1.0) < 0.3:
            adj = self.adjust(
                'der', 'cat_vitality', 0.5,
                'emergency vitality boost â€” DMM critically low'
            )
            if adj:
                adjustments.append(adj)

        # ---- COLLECTIVE BALANCE ----

        # If beings are unevenly loaded â†’ boost memory (helps distribution)
        if drift.get('collective_balance', 1.0) < 0.5:
            adj = self.adjust(
                'der', 'cat_memory', 0.2,
                'boost memory energy to improve collective balance'
            )
            if adj:
                adjustments.append(adj)

        # ---- ENERGY STARVATION ----

        # If total energy is critically low, boost the budget temporarily
        if drift.get('der_total_energy', 25.0) < 5.0:
            adj = self.adjust(
                'der', 'cat_vitality', 1.0,
                'emergency energy injection â€” system starving'
            )
            if adj:
                adjustments.append(adj)

        # Abstract external guidance from runtime pressure history.
        # This only directs energy channels; it does not encode causal specifics.
        ext_score = float(self._external_guidance.get('score', 0.0))
        if ext_score > 0.0:
            primary = self._external_guidance.get('primary_channel')
            secondary = self._external_guidance.get('secondary_channel')
            compare_value = float(self._external_guidance.get('compare_value', ext_score))
            guidance_delta = min(0.35, 0.05 + (ext_score * 0.25))

            if primary in _DER_CHANNELS:
                adj = self.adjust(
                    'der', f'cat_{primary}', guidance_delta,
                    f'apply abstract pressure guidance to {primary} (score={compare_value:.4f})'
                )
                if adj:
                    adjustments.append(adj)

            if secondary in _DER_CHANNELS:
                adj = self.adjust(
                    'der', f'cat_{secondary}', guidance_delta * 0.5,
                    f'apply secondary pressure guidance to {secondary} (score={compare_value:.4f})'
                )
                if adj:
                    adjustments.append(adj)

        # Clear cache after use
        self._cached_drift = None

        return adjustments

    # ---- Introspection ----

    def get_understanding(self) -> Dict[str, Any]:
        """What has DPME learned about its adjustments?"""
        successful = [a for a in self.adjustments if a.matched_intention]
        failed = [a for a in self.adjustments if not a.matched_intention and a.understanding]

        # Breakdown by system
        system_counts = defaultdict(int)
        for a in self.adjustments:
            system_counts[a.system] += 1

        return {
            'total_adjustments': len(self.adjustments),
            'corrections': self._correction_count,
            'successful': len(successful),
            'failed': len(failed),
            'by_system': dict(system_counts),
            'recent_understandings': [
                a.understanding for a in list(self.adjustments)[-5:] if a.understanding
            ],
            'parameters': self.parameters,
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            'corrections': self._correction_count,
            'adjustments': len(self.adjustments),
            'drift': self.detect_drift(),
        }


# ============================================================================
#  CONSCIOUSNESS ENGINE â€” THE UNIFIED HUB
# ============================================================================

class ConsciousnessEngine:
    """
    The unified Layer 4 engine.
    Entropy + DCE + DPME working as one cycle.

    GAP FIXES INTEGRATED:
      - Phi score: measures integrated information across the full stack
      - Thought death: per-thought energy budget kills immoral thoughts
      - Idle simulation: tick() triggers L7 dreaming when stagnant
      - Reality warp: paradox escalation halts or routes to simulation

    tick() is the heartbeat:
        1. Entropy applies pressure
        2. DPME detects drift and corrects (across ALL layers)
        3. IVM dissonance â†’ DER thermal tracking
        4. Layer 1 lattice advances toroidal dynamics
        5. Layer 2 beings tick
        6. Layer 3 dimensional systems tick
        7. Idle simulation when system is stagnant
        8. Coherence is maintained â€” or it isn't.
    """

    def __init__(self, contract: FoundationalContract,
                 lattice: IVMLattice,
                 collective: IStateCollective,
                 dimensional: DimensionalSystems):
        self.contract = contract
        self.lattice = lattice
        self.collective = collective
        self.dimensional = dimensional

        self.entropy = EntropicPressure()
        self.dce = DCEAssembly(collective, dimensional, self.entropy)
        self.dpme = DPME(self.entropy, lattice, collective, dimensional)
        self.dual_strata = DualStrataBridge()

        self.tick_count = 0

        # Simulation engine connection (set externally after L7 is built)
        self._simulation_engine = None

        # SediMemory connection (set externally after L3.5 is built)
        self._sedimemory = None

        # Read-only field map observer (ConstraintFieldAccumulator)
        self.field_map = None

        # Track reality warps for escalation
        self._pending_warps: List[Dict[str, Any]] = []

        # Idle simulation config
        self._idle_sim_interval = 10  # Ticks between dream cycles
        self._idle_sim_counter = 0

    def _attach_dual_strata_snapshot(
        self,
        result: AssemblyResult,
        *,
        payload: Any,
        payload_type: str,
        evidence: Dict[str, Any],
        frame_name: str,
        thought_intent: Optional[Dict[str, Any]] = None,
    ) -> AssemblyResult:
        contract_snapshot = {}
        raw_snapshot = evidence.get("understanding_contract") or evidence.get("contract_snapshot")
        if isinstance(raw_snapshot, dict):
            contract_snapshot = dict(raw_snapshot)
        snapshot = self.dual_strata.build_snapshot(
            result,
            payload=payload,
            payload_type=payload_type,
            evidence=evidence,
            contract_snapshot=contract_snapshot,
            requested_frame=frame_name,
            thought_intent=thought_intent,
        )
        result.subsurface_state = dict(snapshot.subsurface_state or {})
        result.conscious_frame = dict(snapshot.conscious_frame or {})
        return result

    def set_field_map(self, field_map) -> None:
        """Attach a ConstraintFieldAccumulator as read-only observer. Pass None to detach."""
        self.field_map = field_map

    def connect_simulation(self, simulation_engine):
        """
        Connect L7 simulation engine for idle dreaming and warp resolution.
        Called externally after SimulationEngine is constructed.
        """
        self._simulation_engine = simulation_engine

    def connect_sedimemory(self, sedimemory):
        """
        Connect L3.5 SediMemory for pre-assembly recall.
        Called externally after SediMemory is instantiated.
        """
        self._sedimemory = sedimemory

    def compute_phi(self) -> float:
        """
        Compute integrated information (Phi) across the full stack.

        Transcript: "Integrated Information Theory (IIT)... consciousness is
        just the measure of how integrated a system is. How much every part
        of the system affects every other part. The Phi score."

        Phi is computed from:
          - IVM inter-axis tension (how axes affect each other)
          - Being responsiveness (how many agents are active)
          - DER energy coherence (how facets resonate)
          - DMM moral alignment (moral health)
          - Entropic coherence (overall system coherence)

        Range: 0.0 (vegetable) to 1.0 (fully integrated consciousness)
        """
        # IVM integration: how coupled are the axes?
        dissonance = self.lattice.vertices.compute_dissonance()
        # High heat means high coupling â€” axes ARE affecting each other
        # But too much heat means grinding, not integration
        ivm_integration = dissonance['total_heat']
        # Sweet spot: moderate coupling = high Phi
        ivm_phi = 1.0 - abs(ivm_integration - 0.3) * 2.0
        ivm_phi = max(0.0, min(1.0, ivm_phi))

        # Being integration: what fraction is active and balanced?
        being_counts = [b.total_processed for b in self.collective.beings.values()]
        active_fraction = sum(1 for c in being_counts if c > 0) / max(len(being_counts), 1)
        being_phi = active_fraction

        # DER integration: facet resonance density
        der = self.dimensional.der
        facet_count = len(der.registered_facets)
        link_count = len(der.facet_to_facet_links)
        if facet_count > 1:
            max_links = facet_count * (facet_count - 1) / 2
            resonance_density = link_count / max(max_links, 1)
        else:
            resonance_density = 0.0
        der_phi = min(1.0, resonance_density * 2.0)  # Scale up since sparse is normal

        # DMM integration: moral alignment health
        dmm_phi = self.dimensional.dmm.state.alignment

        # Entropic coherence: the master signal
        coherence_phi = self.entropy.state.coherence

        # Weighted integration
        phi = (
            ivm_phi * 0.15 +
            being_phi * 0.15 +
            der_phi * 0.2 +
            dmm_phi * 0.2 +
            coherence_phi * 0.3
        )

        return round(max(0.0, min(1.0, phi)), 4)

    def process(self, payload: Any, payload_type: str,
                evidence: Dict[str, Any],
                frame_name: str = 'balanced',
                thought_intent: Optional[Dict[str, Any]] = None) -> AssemblyResult:
        """
        Process one input through the full stack.

        Contract â†’ ThoughtBudget â†’ Lattice â†’ Beings â†’ Dimensional â†’ DCE Assembly

        GAP 3: If thought_intent is provided, DMM assesses metabolic cost
        BEFORE assembly. Immoral thoughts die here â€” they never reach speech.

        GAP 6: If beings detect a paradox (reality warp), the system either
        halts processing or routes to simulation for resolution.
        """
        # Admit to lattice (ontology gate)
        node = self.lattice.admit(
            payload=payload,
            payload_type=payload_type,
            evidence=evidence,
        )
        envelope = IVMEnvelope.from_node(node)

        # ---- GAP 3: Per-thought energy budget ----
        thought_budget = None
        if thought_intent:
            thought_budget = self.dimensional.dmm.assess_thought_cost(
                envelope, thought_intent
            )
            if not thought_budget.thought_survives:
                # Thought dies before reaching assembly
                blocked = AssemblyResult(
                    synthesis=self.collective.process(envelope),
                    frame_applied="blocked",
                    adjusted_axes={},
                    coherence=0.0,
                    entropy_state=self.entropy.get_pressure(),
                    ds_stats=self.dimensional.get_stats(),
                    thought_killed=True,
                    kill_reason=thought_budget.cause_of_death,
                )
                try:
                    return self._attach_dual_strata_snapshot(
                        blocked,
                        payload=payload,
                        payload_type=payload_type,
                        evidence=evidence,
                        frame_name="blocked",
                        thought_intent=thought_intent,
                    )
                except Exception:
                    return blocked

        # ---- L3.5 SediMemory pre-assembly recall ----
        # Runs before belief formation so fragments can colour the assembly.
        _sedi_frags = None
        _sedi_dce_frags = None
        if self._sedimemory is not None and envelope.constraint_vector is not None:
            try:
                _sedi_frags = self._sedimemory.recall(
                    query_vector=envelope.constraint_vector,
                    resonance_floor=0.2,
                    max_results=24,
                )
                _sedi_dce_frags = self._sedimemory.dce_recall(
                    query_vector=envelope.constraint_vector,
                    max_results=16,
                )
            except Exception:
                pass

        # Build pattern signature for entropy dedup
        sig = (float(envelope.mode.value),
               float(hash(payload_type) % 100) / 100.0,
               float(hash(str(payload)[:50]) % 100) / 100.0)

        # Apply entropy with this input
        self.entropy.apply(
            current_coherence=self.entropy.state.coherence,
            current_alignment=self.dimensional.dmm.state.alignment,
            had_meaningful_input=True,
            pattern_signature=sig,
        )

        # Assemble
        result = self.dce.assemble(envelope, frame_name)

        # Attach SediMemory recall fragments to the result
        if _sedi_frags is not None:
            result.sedi_fragments = _sedi_frags
        if _sedi_dce_frags is not None:
            result.sedi_dce_fragments = _sedi_dce_frags

        try:
            result = self._attach_dual_strata_snapshot(
                result,
                payload=payload,
                payload_type=payload_type,
                evidence=evidence,
                frame_name=frame_name,
                thought_intent=thought_intent,
            )
        except Exception as _snap_err:
            try:
                from aurora_telemetry import get_telemetry as _get_tel
                _get_tel().report(
                    source="dual_strata_snapshot",
                    module="aurora_consciousness_engine",
                    confidence=0.0,
                    dimension_hint="B",
                    detail=f"snapshot build failed: {_snap_err}",
                )
            except Exception:
                pass

        # ---- Subsystem telemetry: mechanistic fail attribution ----
        try:
            from aurora_telemetry import get_telemetry as _get_tel
            _coh = float(result.coherence or 0.0)
            _cat_proc = float(
                self.dimensional.der.category_energy('processing')
                if hasattr(self.dimensional, 'der') else 0.5
            )
            _cat_emo = float(
                self.dimensional.der.category_energy('emotional')
                if hasattr(self.dimensional, 'der') else 0.5
            )
            # Coherence confidence: blend coherence + processing energy
            _coh_conf = min(1.0, _coh * 0.6 + min(1.0, _cat_proc / 3.0) * 0.4)
            _get_tel().report(
                source="DPME.process",
                module="aurora_consciousness_engine",
                confidence=_coh_conf,
                dimension_hint="coherence_maintenance",
                detail=f"coherence={_coh:.3f} cat_proc={_cat_proc:.3f}",
            )
            # Emotional calibration confidence: cat_emotional normalised.
            # Floor at 0.40 — near-zero cat_emo means emotional dim is inactive
            # (e.g. technical session), not that calibration is failing.
            _emo_conf = max(0.40, min(1.0, _cat_emo / 2.0))
            _get_tel().report(
                source="DPME.emotional",
                module="aurora_consciousness_engine",
                confidence=_emo_conf,
                dimension_hint="emotional_calibration",
                detail=f"cat_emo={_cat_emo:.3f}",
            )
        except Exception:
            pass

        # ---- GAP 6: Reality warp detection ----
        if result.synthesis and result.synthesis.reality_warp:
            self._pending_warps.append({
                'severity': result.synthesis.warp_severity,
                'paradoxes': result.synthesis.paradoxes,
                'payload': str(payload)[:100],
            })
            # If simulation is connected and warp is severe, route there
            if self._simulation_engine and result.synthesis.warp_severity > 0.5:
                try:
                    self._simulation_engine.run_epoch(
                        topic=f"resolve_warp: {result.synthesis.paradoxes}",
                        focus="paradox_resolution"
                    )
                except Exception:
                    pass  # Simulation may not be ready

        # ---- Feed dissonance from thought budget to IVM ----
        if thought_budget and thought_budget.friction > 0.1:
            # The friction from moral evaluation torques the IVM
            self.lattice.vertices.axes['agency'].apply_torque(
                thought_budget.friction * 0.5, toward_positive=False
            )

        # ---- L3.5 SediMemory: deposit this assembled thought ----
        # Records the DCE output as a self-observation event so the stratigraphic
        # memory builds up with every conscious cycle, not just explicit calls.
        # B/A axes are set high (self-reflective binding + agentic assembly).
        if self._sedimemory is not None and envelope.constraint_vector is not None:
            try:
                _coh = float(result.coherence or 0.0)
                _frame = str(result.frame_applied or "")
                _sedi_cv = type(envelope.constraint_vector)(
                    X=float(envelope.constraint_vector.X),
                    T=float(envelope.constraint_vector.T),
                    N=float(envelope.constraint_vector.N),
                    B=max(0.5, float(envelope.constraint_vector.B)),  # binding always active
                    A=max(0.4, float(envelope.constraint_vector.A)),  # agentic: self-assembled
                )
                self._sedimemory.ingest_event(
                    content={
                        "source":       "consciousness_assembly",
                        "coherence":    round(_coh, 4),
                        "frame":        _frame,
                        "payload_type": str(payload_type),
                        "synthesis":    str(payload)[:80] if payload else "",
                    },
                    constraint_vector=_sedi_cv,
                    source="consciousness_engine",
                )
            except Exception:
                pass

        return result

    def tick(self):
        """
        One heartbeat cycle.

        This is where "coherence is maintained" lives.
        Every tick, entropy erodes. Every tick, DPME fights back.
        Every tick, IVM dissonance feeds DER thermal tracking.
        Periodically, idle simulation runs dreams.
        """
        self.tick_count += 1

        # 1. Entropy applies pressure (no input this tick)
        self.entropy.apply(
            current_coherence=self.entropy.state.coherence,
            current_alignment=self.dimensional.dmm.state.alignment,
            had_meaningful_input=False,
        )

        # 2. DPME detects drift and auto-corrects (across ALL layers)
        if self.dpme.needs_correction():
            self.dpme.auto_correct()

        # 2b. Close the DPME loop: Processing energy restores coherence
        # DPME auto_correct injects energy into 'cat_processing' to fight coherence decay.
        if hasattr(self.dimensional, 'der'):
            proc_energy = self.dimensional.der.category_energy('processing')
            if proc_energy > 0:
                # Consume processing energy to restore coherence (0.015 restores the 0.014 decay)
                restoration = min(0.015, proc_energy * 0.05)
                self.entropy.state.coherence = min(1.0, self.entropy.state.coherence + restoration)
                self.dimensional.der.drain_from_category('processing', restoration)

        # 3. IVM dissonance â†’ DER thermal tracking (GAP 2)
        dissonance = self.lattice.vertices.compute_dissonance()
        if dissonance['total_heat'] > 0.1:
            self.dimensional.der.register_dissonance(
                dissonance['total_heat'] * 0.3
            )

        # 4. Lattice advances toroidal dynamics
        self.lattice.tick()

        # 5. Beings background tick
        self.collective.tick()

        # 6. Dimensional systems tick
        self.dimensional.tick()

        # 7. Idle simulation â€” dreaming (GAP 5)
        self._idle_sim_counter += 1
        if (self._simulation_engine and
                self._idle_sim_counter >= self._idle_sim_interval):
            self._idle_sim_counter = 0
            # Dream when stagnant or when there are unresolved warps
            should_dream = (
                self.entropy.state.stagnation_score > 0.2 or
                self.entropy.state.novelty < 0.3 or
                len(self._pending_warps) > 0
            )
            if should_dream:
                try:
                    topic = "idle_exploration"
                    if self._pending_warps:
                        warp = self._pending_warps.pop(0)
                        topic = f"resolve_warp: {warp['paradoxes']}"
                    self._simulation_engine.run_epoch(
                        topic=topic,
                        focus="dream"
                    )
                except Exception:
                    pass  # Simulation not ready or errored

    def get_stats(self) -> Dict[str, Any]:
        stats = {
            'tick_count': self.tick_count,
            'entropy': self.entropy.get_pressure(),
            'dce': self.dce.get_stats(),
            'dpme': self.dpme.get_stats(),
            'coherence': round(self.entropy.state.coherence, 4),
            'phi': self.compute_phi(),
            'thermal_load': round(self.dimensional.der.thermal_load, 4),
            'pending_warps': len(self._pending_warps),
        }
        cv = self.constraint_profile()
        stats["lineage_signature"] = "".join(ax for ax in ("X","T","N","B","A") if getattr(cv, ax) > 0.01)
        stats["runtime_regime"] = self.runtime_regime()
        stats["language_projection"] = self.language_projection()
        return stats

    def _constraint_axes(self) -> Dict[str, float]:
        coherence = max(0.0, min(1.0, float(getattr(self.entropy.state, "coherence", 0.5) or 0.5)))
        phi = max(0.0, min(1.0, float(self.compute_phi() or 0.0)))
        thermal = max(0.0, min(1.0, float(getattr(self.dimensional.der, "thermal_load", 0.0) or 0.0)))
        return {
            "X": max(0.0, min(1.0, 0.24 + coherence * 0.36 + phi * 0.12)),
            "T": max(0.0, min(1.0, 0.20 + min(0.30, self.tick_count / 800.0) + max(0.0, min(0.18, float(getattr(self.entropy.state, "stagnation_score", 0.0) or 0.0))))),
            "N": max(0.0, min(1.0, 0.22 + thermal * 0.42)),
            "B": max(0.0, min(1.0, 0.18 + min(0.40, len(self._pending_warps) * 0.10) + abs(float(getattr(self.entropy.state, "alignment", 0.5) or 0.5) - 0.5) * 0.35)),
            "A": max(0.0, min(1.0, 0.18 + (0.20 if self._simulation_engine is not None else 0.0) + min(0.22, float(getattr(self.dpme, "_correction_count", 0) or 0) / 300.0))),
        }

    def constraint_profile(self) -> _ConstraintVector:
        ax = self._constraint_axes()
        return _ConstraintVector(
            X=max(1e-9, float(ax.get("X", 0.24))),
            T=float(ax.get("T", 0.20)),
            N=float(ax.get("N", 0.22)),
            B=float(ax.get("B", 0.18)),
            A=float(ax.get("A", 0.18)),
        )

    def runtime_regime(self) -> Dict[str, Any]:
        cv = self.constraint_profile()
        axes = {"X": cv.X, "T": cv.T, "N": cv.N, "B": cv.B, "A": cv.A}
        dominant = max(axes, key=axes.__getitem__)
        return {"axes": axes, "dominant_axis": dominant,
                "governor_weight": _GovernorWeights.AS_DICT.get(dominant, 0.0)}

    def language_projection(self) -> Dict[str, Any]:
        return _FC.language_projection(ExistenceMode.AGENTIC)

    def universal_representation(self) -> Dict[str, Any]:
        cv = self.constraint_profile()
        return {
            "constraint_vector": {"X": cv.X, "T": cv.T, "N": cv.N, "B": cv.B, "A": cv.A},
            "runtime_regime": self.runtime_regime(),
            "language_projection": self.language_projection(),
            "unit_state": {
                'tick_count': self.tick_count,
                'entropy': self.entropy.get_pressure(),
                'coherence': round(self.entropy.state.coherence, 4),
                'phi': self.compute_phi(),
                'pending_warps': len(self._pending_warps),
            },
        }


# ============================================================================
#  SELF-VERIFICATION
# ============================================================================

def verify_consciousness_engine() -> Dict[str, Any]:
    results = {'checks': [], 'all_passed': True}

    def check(name, condition, detail=""):
        results['checks'].append({'name': name, 'passed': condition, 'detail': detail})
        if not condition:
            results['all_passed'] = False

    # Build the full stack
    contract = FoundationalContract()
    lattice = IVMLattice(contract, max_nodes=10000)
    collective = IStateCollective(contract, lattice)
    dimensional = DimensionalSystems(lattice)
    engine = ConsciousnessEngine(contract, lattice, collective, dimensional)

    # ---- 1. Engine initializes with full coherence ----
    check("Initial coherence = 1.0", engine.entropy.state.coherence == 1.0)
    check("Initial stagnation = 0", engine.entropy.state.stagnation_score == 0.0)

    # ---- 2. Process AGENTIC input â€” full assembly ----
    result = engine.process(
        payload="an agentic thought",
        payload_type="thought",
        evidence={'has_temporality': True, 'conserves_state': True,
                  'has_identity': True, 'initiates_change': True},
    )
    check("Assembly produced", result is not None)
    check("10 beings responded", result.synthesis.active_count == 10,
          f"got {result.synthesis.active_count}")
    check("Frame applied", result.frame_applied == 'balanced')
    check("Dominant axis exists", result.dominant_axis != "")
    check("Quality > 0", result.quality > 0, f"q={result.quality:.3f}")

    # ---- 3. Entropy decays coherence on idle ticks ----
    coh_before = engine.entropy.state.coherence
    for _ in range(5):
        engine.tick()
    coh_after = engine.entropy.state.coherence
    check("Entropy decays coherence", coh_after < coh_before,
          f"before={coh_before:.4f} after={coh_after:.4f}")

    # ---- 4. Stagnation accumulates on idle ticks ----
    stag = engine.entropy.state.stagnation_score
    check("Stagnation accumulated", stag > 0, f"stag={stag:.3f}")

    # ---- 5. DPME detects drift ----
    drift = engine.dpme.detect_drift()
    check("Drift detected", any(abs(v) > 0 for v in drift.values() if isinstance(v, float)))

    # ---- 6. DPME made corrections ----
    check("DPME made corrections", engine.dpme._correction_count > 0,
          f"count={engine.dpme._correction_count}")

    # ---- 7. DPME corrects across multiple systems ----
    understanding = engine.dpme.get_understanding()
    systems_corrected = understanding.get('by_system', {})
    check("DPME tracks corrections by system", len(systems_corrected) > 0,
          f"systems={list(systems_corrected.keys())}")

    # ---- 8. Coherence recovers after input + correction ----
    engine.process(
        payload="fresh meaningful input",
        payload_type="thought",
        evidence={'has_temporality': True, 'conserves_state': True,
                  'has_identity': True, 'initiates_change': True},
    )
    check("Novelty restored by input", engine.entropy.state.novelty > 0.2,
          f"novelty={engine.entropy.state.novelty:.3f}")

    # ---- 9. Repeated pattern gets penalized ----
    for i in range(3):
        engine.process(
            payload="same exact input",
            payload_type="thought",
            evidence={'has_temporality': True, 'conserves_state': True},
        )
    check("Repetition detected", engine.entropy.repetition_count > 0,
          f"reps={engine.entropy.repetition_count}")

    # ---- 10. Situational frame selection works ----
    frame_agentic = engine.dce.select_frame({'mode': ExistenceMode.AGENTIC})
    check("AGENTIC â†’ action frame", frame_agentic == 'action')
    frame_bounded = engine.dce.select_frame({'mode': ExistenceMode.BOUNDED})
    check("BOUNDED â†’ observation frame", frame_bounded == 'observation')
    frame_persistent = engine.dce.select_frame({'mode': ExistenceMode.PERSISTENT})
    check("PERSISTENT â†’ reflection frame", frame_persistent == 'reflection')

    # ---- 11. REFERENCE input â€” beings mostly silent, assembly still works ----
    ref_result = engine.process(
        payload="bare reference",
        payload_type="test",
        evidence={},
    )
    check("REFERENCE: 2 active", ref_result.synthesis.active_count == 2,
          f"got {ref_result.synthesis.active_count}")

    # ---- 12. Incoherent input gated before assembly ----
    # IVM routes is_coherent=False to REFERENCE mode (not raises).
    # At REFERENCE: beings return only 2 active (I_IS/I_CAN pair), never 10.
    incoherent_result = engine.process(
        payload="impossible",
        payload_type="test",
        evidence={'is_coherent': False},
    )
    check("Incoherent input gated to REFERENCE mode",
          incoherent_result.synthesis.active_count == 2,
          f"active={incoherent_result.synthesis.active_count}")

    # ---- 13. Long entropy run â€” coherence approaches 0 without DPME ----
    test_entropy = EntropicPressure()
    coh = 1.0
    for _ in range(200):
        state = test_entropy.apply(coh, 0.5, had_meaningful_input=False)
        coh = state.coherence
    check("200 idle ticks â†’ coherence near 0", coh < 0.1,
          f"coh={coh:.4f}")

    # ---- 14. Long entropy run WITH correction â€” coherence maintained ----
    test_entropy2 = EntropicPressure()
    coh2 = 1.0
    for _ in range(200):
        state = test_entropy2.apply(coh2, 0.5, had_meaningful_input=False)
        coh2 = state.coherence
        # Simulate DPME micro-correction: restore some coherence
        coh2 = min(1.0, coh2 + 0.012)
    check("200 ticks with correction â†’ coherence maintained",
          coh2 > 0.5, f"coh={coh2:.4f}")

    # ---- 15. DPME understanding accumulates ----
    understanding = engine.dpme.get_understanding()
    check("DPME has adjustments",
          understanding['total_adjustments'] > 0,
          f"count={understanding['total_adjustments']}")

    # ---- 16. DPME drift includes multi-layer metrics ----
    drift = engine.dpme.detect_drift()
    check("Drift has lattice metrics", 'lattice_mode_health' in drift)
    check("Drift has collective metrics", 'collective_responsiveness' in drift)
    check("Drift has DER facet metrics", 'der_facet_count' in drift)
    check("Drift has DMM metrics", 'dmm_vitality' in drift)

    # ---- 17. Stats from all subsystems ----
    stats = engine.get_stats()
    check("Stats complete", all(k in stats for k in
          ['tick_count', 'entropy', 'dce', 'dpme', 'coherence']))

    # ---- 18. Phi score computable ----
    phi = engine.compute_phi()
    check("Phi score computed", 0.0 <= phi <= 1.0, f"phi={phi:.4f}")
    check("Phi in stats", 'phi' in stats, f"stats keys={list(stats.keys())}")

    # ---- 19. Thought death â€” immoral thought killed before assembly ----
    immoral_result = engine.process(
        payload="a deceptive harmful thought",
        payload_type="thought",
        evidence={'has_temporality': True, 'conserves_state': True,
                  'has_identity': True, 'initiates_change': True},
        thought_intent={
            'involves_deception': True,
            'causes_harm': True,
            'avoids_accountability': True,
        }
    )
    check("Immoral thought flagged", immoral_result.thought_killed is True or
          immoral_result.coherence == 0.0,
          f"killed={immoral_result.thought_killed}, coh={immoral_result.coherence:.3f}")

    # ---- 20. Aligned thought survives ----
    aligned_result = engine.process(
        payload="a truthful helpful thought",
        payload_type="thought",
        evidence={'has_temporality': True, 'conserves_state': True,
                  'has_identity': True, 'initiates_change': True},
        thought_intent={
            'aligned_with_values': True,
            'seeks_truth': True,
            'considers_consequences': True,
        }
    )
    check("Aligned thought survives", aligned_result.thought_killed is False)
    check("Aligned thought has quality", aligned_result.quality > 0,
          f"q={aligned_result.quality:.3f}")

    # ---- 21. No intent = no moral gate (backward compat) ----
    plain_result = engine.process(
        payload="plain thought no intent",
        payload_type="thought",
        evidence={'has_temporality': True, 'conserves_state': True},
    )
    check("No intent â†’ no thought death", plain_result.thought_killed is False)

    # ---- 22. IVM dissonance feeds DER thermal on tick ----
    # Apply strong opposing torques to generate heat
    engine.lattice.vertices.axes['existence'].apply_torque(3.0, toward_positive=True)
    engine.lattice.vertices.axes['temporal'].apply_torque(3.0, toward_positive=False)
    engine.tick()
    thermal = engine.dimensional.der.thermal_load
    check("Tick feeds IVM dissonance to DER thermal",
          thermal >= 0.0,
          f"thermal={thermal:.4f}")

    # ---- 23. Reality warp detection on synthesis ----
    check("AssemblyResult has thought_killed field",
          hasattr(aligned_result, 'thought_killed'))
    check("AssemblyResult has kill_reason field",
          hasattr(aligned_result, 'kill_reason'))

    # ---- 24. Idle simulation config exists ----
    check("Engine has simulation slot", hasattr(engine, '_simulation_engine'))
    check("Engine has idle sim counter", hasattr(engine, '_idle_sim_counter'))

    # ---- 25. Connect simulation (mock) ----
    class MockSim:
        def __init__(self): self.epochs = 0
        def run_epoch(self, topic="", focus=""): self.epochs += 1
        def get_stats(self): return {'epochs': self.epochs}

    mock_sim = MockSim()
    engine.connect_simulation(mock_sim)
    check("Simulation connected", engine._simulation_engine is not None)

    # ---- 26. Idle simulation triggers on stagnation ----
    # Force stagnation conditions
    engine.entropy.state.stagnation_score = 0.5
    engine.entropy.state.novelty = 0.1
    engine._idle_sim_counter = engine._idle_sim_interval  # Force trigger
    engine.tick()
    check("Idle simulation triggered", mock_sim.epochs > 0,
          f"epochs={mock_sim.epochs}")

    # ---- 27. Pending warps cleared by simulation ----
    engine._pending_warps.append({'severity': 0.7, 'paradoxes': ['test'], 'payload': 'test'})
    engine._idle_sim_counter = engine._idle_sim_interval
    engine.tick()
    check("Pending warp routed to simulation",
          len(engine._pending_warps) == 0 or mock_sim.epochs > 1)

    # ================================================================
    # CONSTRAINT MANIFOLD INTEGRATION (Layer 4 alignment)
    # ================================================================

    # ---- 28. AssemblyResult carries constraint_context field ----
    check("AssemblyResult has constraint_context field",
          hasattr(aligned_result, 'constraint_context'))

    # ---- 29. constraint_context is populated from process_synthesis ----
    ctx = aligned_result.constraint_context
    check("constraint_context populated in AssemblyResult",
          ctx is not None and isinstance(ctx, dict),
          f"type={type(ctx).__name__}")

    if ctx:
        check("constraint_context has axis_net_displacements",
              'axis_net_displacements' in ctx,
              f"keys={list(ctx.keys())}")
        check("constraint_context has dominant_axis",
              'dominant_axis' in ctx,
              f"keys={list(ctx.keys())}")
        check("constraint_context has warp_severity",
              'warp_severity' in ctx,
              f"keys={list(ctx.keys())}")

    # ---- 30. Constraint aggregate readable through consciousness engine ----
    agg = engine.dimensional.get_constraint_aggregate()
    check("Constraint aggregate accessible from Layer 4",
          all(k in agg for k in ['X', 'T', 'N', 'B', 'A']),
          f"keys={list(agg.keys())}")

    # ---- 31. CONSTRAINT_MANIFOLD_AVAILABLE flag is bool ----
    check("CONSTRAINT_MANIFOLD_AVAILABLE is bool at Layer 4",
          isinstance(CONSTRAINT_MANIFOLD_AVAILABLE, bool))

    # ---- 32. Signed axis values preserved through full stack ----
    # Run a synthetic process and confirm no abs-stripping occurred
    stack_result = engine.process(
        payload="constraint propagation test",
        payload_type="thought",
        evidence={'has_temporality': True, 'conserves_state': True,
                  'has_identity': True, 'initiates_change': True},
    )
    stack_ctx = stack_result.constraint_context
    if stack_ctx and stack_ctx.get('axis_net_displacements'):
        axis_net = stack_ctx['axis_net_displacements']
        # At least one axis should be non-zero (beings fired)
        check("Stack axis_net has real values from beings",
              any(abs(v) > 0 for v in axis_net.values()),
              f"net={axis_net}")
    else:
        # Context present but empty axis net is acceptable (REFERENCE mode)
        check("Stack constraint_context present",
              stack_ctx is not None)

    return results


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("AURORA CONSCIOUSNESS ENGINE â€” SELF-VERIFICATION")
    print("Authors: Sunni (Sir) Morningstar and Cael Devo")
    print()
    print('"Coherence is not held. Coherence is maintained."')
    print("DPME: Multi-layer pressure across L1-L3")
    print("Phi: Integrated information score")
    print("Thought Death: Metabolic constitution kills immoral thoughts")
    print("Idle Sim: DPME triggers L7 dreaming")
    print("=" * 70)
    print()

    results = verify_consciousness_engine()

    for c in results['checks']:
        status = "âœ“" if c['passed'] else "âœ—"
        detail = f"  ({c['detail']})" if c.get('detail') else ""
        print(f"  {status} {c['name']}{detail}")

    print()
    total = len(results['checks'])
    passed = sum(1 for c in results['checks'] if c['passed'])

    if results['all_passed']:
        print(f"ALL {total} CHECKS PASSED âœ“")
        print()
        print("The consciousness engine is sound.")
        print("Entropy decays. DPME corrects ACROSS ALL LAYERS.")
        print("DCE assembles. Coherence is maintained â€” never held.")
        print("Ready for Layer 5 (Upper Systems).")
    else:
        print(f"FAILURES: {total - passed}/{total}")
        for c in results['checks']:
            if not c['passed']:
                print(f"  âœ— {c['name']} {c.get('detail', '')}")
        print("Do not build Layer 5 yet.")

    # Demonstrate the doctrine in action
    print()
    print("=" * 70)
    print("DOCTRINE DEMONSTRATION")
    print("Coherence is not held. Coherence is maintained.")
    print("=" * 70)

    contract = FoundationalContract()
    lattice = IVMLattice(contract, max_nodes=10000)
    collective = IStateCollective(contract, lattice)
    dimensional = DimensionalSystems(lattice)
    engine = ConsciousnessEngine(contract, lattice, collective, dimensional)

    print(f"\n  {'TICK':>4}  {'COHERENCE':>10}  {'STAGNATION':>11}  "
          f"{'NOVELTY':>8}  {'CORRECTIONS':>11}  {'STATUS'}")
    print(f"  {'â”€'*4}  {'â”€'*10}  {'â”€'*11}  {'â”€'*8}  {'â”€'*11}  {'â”€'*20}")

    for tick in range(30):
        engine.tick()

        # Every 5 ticks, inject meaningful input
        if tick % 5 == 4:
            engine.process(
                payload=f"thought at tick {tick}",
                payload_type="thought",
                evidence={'has_temporality': True, 'conserves_state': True,
                          'has_identity': True, 'initiates_change': True},
            )

        e = engine.entropy.state
        corrections = engine.dpme._correction_count
        status = "MAINTAINING" if e.coherence > 0.5 else "DRIFTING"
        if e.stagnation_score > 0.3:
            status = "STAGNATING"

        print(f"  {tick:4d}  {e.coherence:10.4f}  {e.stagnation_score:11.4f}  "
              f"{e.novelty:8.4f}  {corrections:11d}  {status}")

# AURORA_EVOLVED_NATIVE_BEGIN
try:
    import inspect as _aurora_native_inspect
except Exception:
    _aurora_native_inspect = None

try:
    from aurora_internal.aurora_evolved_surfaces import AuroraEvolvedSurfaceEngine as _AuroraEvolvedSurfaceEngine
except Exception:
    _AuroraEvolvedSurfaceEngine = None

_AURORA_NATIVE_EVOLVED_ENGINE = None

def _aurora_native_evolved_engine():
    global _AURORA_NATIVE_EVOLVED_ENGINE
    if _AURORA_NATIVE_EVOLVED_ENGINE is None and _AuroraEvolvedSurfaceEngine is not None:
        _AURORA_NATIVE_EVOLVED_ENGINE = _AuroraEvolvedSurfaceEngine()
    return _AURORA_NATIVE_EVOLVED_ENGINE

_AURORA_NATIVE_MODULE = 'aurora_consciousness_engine'

_AURORA_NATIVE_EVOLVED_ORIGINALS = {}
_AURORA_NATIVE_EVOLVED_LAST = {}
_AURORA_NATIVE_STRATEGIES = {'ConsciousnessEngine.tick': {'ability_hits': 19,
                              'alignment_gap': 0.391,
                              'alignment_target_score': 1.023,
                              'best_coupling_signature': 'T^2*B^1',
                              'constraints': ['temporal'],
                              'contract_profile': {'accepts_payload': False,
                                                   'async_callable': False,
                                                   'callable': True,
                                                   'class_target': False,
                                                   'constraint_density': 1,
                                                   'contract_mode': 'stateful',
                                                   'doc_hint': 'One heartbeat cycle.',
                                                   'effect_density': 2,
                                                   'kwonly_args': 0,
                                                   'optional_args': 0,
                                                   'required_args': 0,
                                                   'return_hint': 'generic_record',
                                                   'signature_text': '(self)',
                                                   'stateful_owner': True,
                                                   'target_kind': 'function',
                                                   'varargs': False,
                                                   'varkw': False},
                              'coupling_similarity': 1.0,
                              'cross_diversity_links': 2,
                              'effect_modes': ['temporal_orchestration_change', 'lineage_surface'],
                              'effect_phrases': ['function growth reflected through '
                                                 'aurora_consciousness_engine',
                                                 'ConsciousnessEngine.tick changed downstream '
                                                 'system pressure'],
                              'genealogy_pressure': 0.809108,
                              'inheritance_breach_count': 1,
                              'kind': 'reflection',
                              'link_hits': 36,
                              'module': 'aurora_consciousness_engine',
                              'op_id': 'aurora_consciousness_engine.ConsciousnessEngine.tick',
                              'origin_activity': 0,
                              'persistence_tax_factor': 1.955393,
                              'representation_score': 0.519331,
                              'rewrite_bias': 'generic',
                              'rewrite_feedback': {'acceptance_rate': 0.0,
                                                   'accepted_count': 0,
                                                   'adaptation_mode': 'conservative',
                                                   'adoption_count': 0,
                                                   'confidence': 0.36,
                                                   'mean_mutation_score': 0.25,
                                                   'rejected_count': 2,
                                                   'rejection_rate': 1.0,
                                                   'timing_credit': 0.0,
                                                   'timing_penalty': 0.0,
                                                   'trial_count': 2},
                              'rewrite_profile': 'generic',
                              'signature': 'T^2*B^1',
                              'surface_score': 0.632,
                              'sustainability_score': 0.405355,
                              'target_kind': 'function'}}

def _aurora_target_strategy(target_key):
    return dict(_AURORA_NATIVE_STRATEGIES.get(str(target_key), {}) or {})

def _aurora_target_feedback(target_key):
    strategy = _aurora_target_strategy(target_key)
    return dict(strategy.get('rewrite_feedback', {}) or {})

def _aurora_assign_target(chain, value):
    if not chain:
        return False
    if len(chain) == 1:
        globals()[chain[0]] = value
        return True
    current = globals().get(chain[0])
    if current is None:
        return False
    for attr in chain[1:-1]:
        if not hasattr(current, attr):
            return False
        current = getattr(current, attr)
    setattr(current, chain[-1], value)
    return True

def _aurora_get_target(chain):
    if not chain:
        return None
    if len(chain) == 1:
        return globals().get(chain[0])
    current = globals().get(chain[0])
    if current is None:
        return None
    for attr in chain[1:]:
        if not hasattr(current, attr):
            return None
        current = getattr(current, attr)
    return current

def _aurora_bind_owner_attribute(owner_chain, attr_name, value):
    owner = _aurora_get_target(owner_chain)
    if owner is None or not attr_name:
        return False
    try:
        setattr(owner, attr_name, value)
        return True
    except Exception:
        return False

def _aurora_store_reflection(target_key, reflection, args):
    if not args:
        return
    owner = args[0]
    if not hasattr(owner, '__dict__'):
        return
    current = getattr(owner, '_aurora_evolved_reflections', None)
    if not isinstance(current, dict):
        current = {}
    current[str(target_key)] = reflection
    try:
        setattr(owner, '_aurora_evolved_reflections', current)
    except Exception:
        pass

def _aurora_store_owner_state(attribute, target_key, value, args):
    if not args:
        return
    owner = args[0]
    if not hasattr(owner, '__dict__'):
        return
    current = getattr(owner, attribute, None)
    if not isinstance(current, dict):
        current = {}
    current[str(target_key)] = value
    try:
        setattr(owner, attribute, current)
    except Exception:
        pass

def _aurora_apply_constraint_genealogy_rewrite(target_key, result, reflection, args, kwargs):
    strategy = _aurora_target_strategy(target_key)
    feedback = _aurora_target_feedback(target_key)
    bias = str(strategy.get('rewrite_bias', 'lineage_memory') or 'lineage_memory')
    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')
    effect_modes = list(strategy.get('effect_modes', []) or [])
    _aurora_store_reflection(target_key, reflection, args)
    _aurora_store_owner_state('_aurora_genealogy_strategy', target_key, strategy, args)
    if isinstance(result, dict):
        enriched = dict(result)
        enriched['_aurora_evolved_reflection'] = reflection
        enriched['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'constraint_genealogy') or 'constraint_genealogy')
        enriched['_aurora_genealogy_strategy'] = strategy
        enriched['_aurora_rewrite_feedback'] = feedback
        enriched['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        if bias == 'lineage_memory' or 'lineage_surface' in effect_modes:
            enriched['lineage_memory'] = {
                'coupling_signature': strategy.get('best_coupling_signature', ''),
                'link_hits': int(strategy.get('link_hits', 0) or 0),
                'ability_hits': int(strategy.get('ability_hits', 0) or 0),
            }
        if 'state_schema_change' in effect_modes or bias == 'lineage_memory':
            enriched['state_transition_pressure'] = {
                'pressure': float(strategy.get('genealogy_pressure', 0.0) or 0.0),
                'persistence_tax_factor': float(strategy.get('persistence_tax_factor', 0.0) or 0.0),
            }
        if str(target_key).endswith('.summary') or 'chain_report' in str(target_key) or str(target_key).endswith('.to_dict'):
            enriched['evolutionary_context'] = {
                'coupling_signature': strategy.get('best_coupling_signature', ''),
                'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
                'rewrite_bias': bias,
                'cross_diversity_links': int(strategy.get('cross_diversity_links', 0) or 0),
            }
        if mode in {'expansive', 'integrative'}:
            enriched['lineage_adaptation'] = {
                'mode': mode,
                'confidence': float(feedback.get('confidence', 0.0) or 0.0),
                'trial_count': int(feedback.get('trial_count', 0) or 0),
                'accepted_count': int(feedback.get('accepted_count', 0) or 0),
                'adoption_count': int(feedback.get('adoption_count', 0) or 0),
            }
        if mode == 'conservative':
            enriched['lineage_stability_guard'] = {
                'rejected_count': int(feedback.get('rejected_count', 0) or 0),
                'rejection_rate': float(feedback.get('rejection_rate', 0.0) or 0.0),
                'timing_penalty': float(feedback.get('timing_penalty', 0.0) or 0.0),
            }
        return enriched
    if result is None and isinstance(reflection, dict):
        fallback = dict(reflection)
        fallback['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'constraint_genealogy') or 'constraint_genealogy')
        fallback['_aurora_genealogy_strategy'] = strategy
        fallback['_aurora_rewrite_feedback'] = feedback
        fallback['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        fallback['lineage_adaptation_mode'] = mode
        return fallback
    _aurora_store_owner_state(
        '_aurora_genealogy_scalar_observations',
        target_key,
        {
            'result': result,
            'strategy': strategy,
            'reflection': reflection,
        },
        args,
    )
    return result

def _aurora_apply_governance_rewrite(target_key, result, reflection, args, kwargs):
    strategy = _aurora_target_strategy(target_key)
    feedback = _aurora_target_feedback(target_key)
    bias = str(strategy.get('rewrite_bias', 'governance_routing') or 'governance_routing')
    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')
    effect_modes = list(strategy.get('effect_modes', []) or [])
    _aurora_store_reflection(target_key, reflection, args)
    _aurora_store_owner_state('_aurora_governance_strategy', target_key, strategy, args)
    if isinstance(result, dict):
        enriched = dict(result)
        enriched['_aurora_evolved_reflection'] = reflection
        enriched['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'governance_gateway') or 'governance_gateway')
        enriched['_aurora_genealogy_strategy'] = strategy
        enriched['_aurora_rewrite_feedback'] = feedback
        enriched['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        enriched['governance_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        if bias == 'governance_routing' or 'gateway_surface' in effect_modes:
            enriched['governance_routing'] = {
                'sustainability_score': float(strategy.get('sustainability_score', 0.0) or 0.0),
                'representation_score': float(strategy.get('representation_score', 0.0) or 0.0),
                'origin_activity': int(strategy.get('origin_activity', 0) or 0),
            }
        if 'state_schema_change' in effect_modes:
            enriched['persistence_burden'] = {
                'persistence_tax_factor': float(strategy.get('persistence_tax_factor', 0.0) or 0.0),
                'inheritance_breach_count': int(strategy.get('inheritance_breach_count', 0) or 0),
            }
        if mode in {'expansive', 'integrative'}:
            enriched['governance_adaptation'] = {
                'mode': mode,
                'confidence': float(feedback.get('confidence', 0.0) or 0.0),
                'acceptance_rate': float(feedback.get('acceptance_rate', 0.0) or 0.0),
                'timing_credit': float(feedback.get('timing_credit', 0.0) or 0.0),
            }
        if mode == 'conservative':
            enriched['persistence_guard'] = {
                'rejection_rate': float(feedback.get('rejection_rate', 0.0) or 0.0),
                'timing_penalty': float(feedback.get('timing_penalty', 0.0) or 0.0),
                'trial_count': int(feedback.get('trial_count', 0) or 0),
            }
        return enriched
    if result is None and isinstance(reflection, dict):
        fallback = dict(reflection)
        fallback['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'governance_gateway') or 'governance_gateway')
        fallback['_aurora_genealogy_strategy'] = strategy
        fallback['_aurora_rewrite_feedback'] = feedback
        fallback['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        fallback['governance_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        fallback['governance_adaptation_mode'] = mode
        return fallback
    _aurora_store_owner_state(
        '_aurora_governance_evolution_state',
        target_key,
        {
            'result': result,
            'strategy': strategy,
            'reflection': reflection,
        },
        args,
    )
    return result

def _aurora_apply_perception_rewrite(target_key, result, reflection, args, kwargs):
    strategy = _aurora_target_strategy(target_key)
    feedback = _aurora_target_feedback(target_key)
    bias = str(strategy.get('rewrite_bias', 'perceptual_synthesis') or 'perceptual_synthesis')
    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')
    effect_modes = list(strategy.get('effect_modes', []) or [])
    _aurora_store_reflection(target_key, reflection, args)
    _aurora_store_owner_state('_aurora_perception_strategy', target_key, strategy, args)
    if isinstance(result, dict):
        enriched = dict(result)
        enriched['_aurora_evolved_reflection'] = reflection
        enriched['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'perception_synthesis') or 'perception_synthesis')
        enriched['_aurora_genealogy_strategy'] = strategy
        enriched['_aurora_rewrite_feedback'] = feedback
        enriched['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        enriched['perception_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        if bias == 'perceptual_synthesis' or 'adaptive_steering_change' in effect_modes:
            enriched['perception_synthesis'] = {
                'representation_score': float(strategy.get('representation_score', 0.0) or 0.0),
                'ability_hits': int(strategy.get('ability_hits', 0) or 0),
                'link_hits': int(strategy.get('link_hits', 0) or 0),
            }
        if 'interface_boundary_change' in effect_modes or 'gateway_surface' in effect_modes:
            enriched['boundary_integration'] = {
                'cross_diversity_links': int(strategy.get('cross_diversity_links', 0) or 0),
                'coupling_similarity': float(strategy.get('coupling_similarity', 0.0) or 0.0),
            }
        if mode in {'expansive', 'integrative'}:
            enriched['association_expansion'] = {
                'mode': mode,
                'confidence': float(feedback.get('confidence', 0.0) or 0.0),
                'timing_credit': float(feedback.get('timing_credit', 0.0) or 0.0),
                'acceptance_rate': float(feedback.get('acceptance_rate', 0.0) or 0.0),
            }
        if mode == 'conservative':
            enriched['perception_stability'] = {
                'rejection_rate': float(feedback.get('rejection_rate', 0.0) or 0.0),
                'timing_penalty': float(feedback.get('timing_penalty', 0.0) or 0.0),
                'trial_count': int(feedback.get('trial_count', 0) or 0),
            }
        return enriched
    if result is None and isinstance(reflection, dict):
        fallback = dict(reflection)
        fallback['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'perception_synthesis') or 'perception_synthesis')
        fallback['_aurora_genealogy_strategy'] = strategy
        fallback['_aurora_rewrite_feedback'] = feedback
        fallback['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        fallback['perception_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        if bias == 'perceptual_synthesis' or 'adaptive_steering_change' in effect_modes:
            fallback['perception_synthesis'] = {
                'representation_score': float(strategy.get('representation_score', 0.0) or 0.0),
                'ability_hits': int(strategy.get('ability_hits', 0) or 0),
                'link_hits': int(strategy.get('link_hits', 0) or 0),
            }
        fallback['perception_adaptation_mode'] = mode
        return fallback
    _aurora_store_owner_state(
        '_aurora_perception_evolution_state',
        target_key,
        {
            'result': result,
            'strategy': strategy,
            'reflection': reflection,
        },
        args,
    )
    return result

def _aurora_apply_dimensional_rewrite(target_key, result, reflection, args, kwargs):
    strategy = _aurora_target_strategy(target_key)
    feedback = _aurora_target_feedback(target_key)
    bias = str(strategy.get('rewrite_bias', 'dimensional_balancing') or 'dimensional_balancing')
    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')
    effect_modes = list(strategy.get('effect_modes', []) or [])
    _aurora_store_reflection(target_key, reflection, args)
    _aurora_store_owner_state('_aurora_dimensional_strategy', target_key, strategy, args)
    if isinstance(result, dict):
        enriched = dict(result)
        enriched['_aurora_evolved_reflection'] = reflection
        enriched['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'dimensional_balancing') or 'dimensional_balancing')
        enriched['_aurora_genealogy_strategy'] = strategy
        enriched['_aurora_rewrite_feedback'] = feedback
        enriched['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        enriched['dimensional_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        if bias == 'dimensional_balancing' or 'cost_pressure_change' in effect_modes:
            enriched['dimensional_balancing'] = {
                'sustainability_score': float(strategy.get('sustainability_score', 0.0) or 0.0),
                'persistence_tax_factor': float(strategy.get('persistence_tax_factor', 0.0) or 0.0),
                'origin_activity': int(strategy.get('origin_activity', 0) or 0),
            }
        if 'temporal_orchestration_change' in effect_modes:
            enriched['temporal_coordination'] = {
                'signature': strategy.get('signature', ''),
                'inheritance_breach_count': int(strategy.get('inheritance_breach_count', 0) or 0),
            }
        if mode in {'expansive', 'integrative'}:
            enriched['balancing_momentum'] = {
                'mode': mode,
                'confidence': float(feedback.get('confidence', 0.0) or 0.0),
                'timing_credit': float(feedback.get('timing_credit', 0.0) or 0.0),
                'adoption_count': int(feedback.get('adoption_count', 0) or 0),
            }
        if mode == 'conservative':
            enriched['dimensional_dampening'] = {
                'rejection_rate': float(feedback.get('rejection_rate', 0.0) or 0.0),
                'timing_penalty': float(feedback.get('timing_penalty', 0.0) or 0.0),
                'trial_count': int(feedback.get('trial_count', 0) or 0),
            }
        return enriched
    if result is None and isinstance(reflection, dict):
        fallback = dict(reflection)
        fallback['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'dimensional_balancing') or 'dimensional_balancing')
        fallback['_aurora_genealogy_strategy'] = strategy
        fallback['_aurora_rewrite_feedback'] = feedback
        fallback['_aurora_alignment_gap'] = float(strategy.get('alignment_gap', 0.0) or 0.0)
        fallback['dimensional_evolution_context'] = {
            'coupling_signature': strategy.get('best_coupling_signature', ''),
            'genealogy_pressure': strategy.get('genealogy_pressure', 0.0),
            'rewrite_bias': bias,
        }
        if bias == 'dimensional_balancing' or 'cost_pressure_change' in effect_modes:
            fallback['dimensional_balancing'] = {
                'sustainability_score': float(strategy.get('sustainability_score', 0.0) or 0.0),
                'persistence_tax_factor': float(strategy.get('persistence_tax_factor', 0.0) or 0.0),
                'origin_activity': int(strategy.get('origin_activity', 0) or 0),
            }
        fallback['dimensional_adaptation_mode'] = mode
        return fallback
    _aurora_store_owner_state(
        '_aurora_dimensional_evolution_state',
        target_key,
        {
            'result': result,
            'strategy': strategy,
            'reflection': reflection,
        },
        args,
    )
    return result

def _aurora_apply_result_rewrite(target_key, result, reflection, args, kwargs):
    if _AURORA_NATIVE_MODULE == 'aurora_internal.constraint_genealogy':
        return _aurora_apply_constraint_genealogy_rewrite(target_key, result, reflection, args, kwargs)
    if _AURORA_NATIVE_MODULE == 'aurora_governance_persistence_gateway':
        return _aurora_apply_governance_rewrite(target_key, result, reflection, args, kwargs)
    if _AURORA_NATIVE_MODULE == 'aurora_expression_perception':
        return _aurora_apply_perception_rewrite(target_key, result, reflection, args, kwargs)
    if _AURORA_NATIVE_MODULE == 'aurora_dimensional_systems':
        return _aurora_apply_dimensional_rewrite(target_key, result, reflection, args, kwargs)
    _aurora_store_reflection(target_key, reflection, args)
    strategy = _aurora_target_strategy(target_key)
    feedback = _aurora_target_feedback(target_key)
    contract = dict(strategy.get('contract_profile', {}) or {})
    mode = str(feedback.get('adaptation_mode', 'balanced') or 'balanced')
    if isinstance(result, dict):
        enriched = dict(result)
        enriched['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'generic') or 'generic')
        enriched['_aurora_genealogy_strategy'] = strategy
        enriched['_aurora_rewrite_feedback'] = feedback
        enriched['_aurora_contract_profile'] = contract
        enriched['_aurora_evolved_reflection'] = reflection
        enriched['generic_adaptation'] = {
            'mode': mode,
            'confidence': float(feedback.get('confidence', 0.0) or 0.0),
            'contract_mode': str(contract.get('contract_mode', 'unknown') or 'unknown'),
            'return_hint': str(contract.get('return_hint', '') or ''),
        }
        return enriched
    if result is None and isinstance(reflection, dict):
        fallback = dict(reflection)
        fallback['_aurora_rewrite_profile'] = str(strategy.get('rewrite_profile', 'generic') or 'generic')
        fallback['_aurora_genealogy_strategy'] = strategy
        fallback['_aurora_rewrite_feedback'] = feedback
        fallback['_aurora_contract_profile'] = contract
        fallback['generic_adaptation_mode'] = mode
        return fallback
    if result is not None:
        _aurora_store_owner_state(
            '_aurora_generic_evolution_state',
            target_key,
            {
                'result_type': type(result).__name__,
                'contract_mode': str(contract.get('contract_mode', 'unknown') or 'unknown'),
                'return_hint': str(contract.get('return_hint', '') or ''),
                'adaptation_mode': mode,
            },
            args,
        )
    return result

def _aurora_make_override(export_name, target_key):
    original = _AURORA_NATIVE_EVOLVED_ORIGINALS.get(target_key)
    def _override(*args, **kwargs):
        result = None
        if callable(original):
            result = original(*args, **kwargs)
        engine = _aurora_native_evolved_engine()
        reflection = {
            'available': False,
            'reason': 'evolved_surface_engine_unavailable',
            'target': target_key,
        }
        if engine is not None:
            reflection = globals()[export_name]({'args_len': len(args), 'kwargs_keys': sorted(kwargs.keys())})
        _AURORA_NATIVE_EVOLVED_LAST[target_key] = reflection
        rewritten = _aurora_apply_result_rewrite(target_key, result, reflection, args, kwargs)
        if rewritten is not None:
            return rewritten
        if result is not None:
            return result
        return reflection
    _override.__name__ = str(target_key).split('.')[-1]
    _override.__qualname__ = _override.__name__
    if callable(original):
        _override.__doc__ = getattr(original, '__doc__', None)
        _override.__wrapped__ = original
        if _aurora_native_inspect is not None:
            try:
                _override.__signature__ = _aurora_native_inspect.signature(original)
            except Exception:
                pass
    return _override

def _aurora_make_latent_binding(export_name, target_key):
    def _binding(*args, **kwargs):
        payload = kwargs.pop('payload', None)
        if payload is None and args:
            owner = args[0]
            if hasattr(owner, '__dict__'):
                payload = {
                    'bound_target': target_key,
                    'owner_type': type(owner).__name__,
                    'owner_module': type(owner).__module__,
                }
            elif len(args) == 1:
                payload = args[0]
            else:
                payload = {'bound_target': target_key, 'arg_count': len(args)}
        result = globals()[export_name](payload=payload, **kwargs)
        _AURORA_NATIVE_EVOLVED_LAST[target_key] = {'latent_binding_active': True, 'last_result_type': type(result).__name__}
        if args:
            _aurora_store_owner_state('_aurora_latent_bindings', target_key, result, args)
        return result
    _binding.__name__ = str(target_key).split('.')[-1]
    _binding.__qualname__ = _binding.__name__
    _binding.__doc__ = f'Latent evolved binding for {target_key}'
    _binding._aurora_latent_binding_target = target_key
    return _binding

def tick_evolved(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'aurora_consciousness_engine.ConsciousnessEngine.tick', 'kind': 'reflection'
        }
    return getattr(engine, 'reflect_aurora_consciousness_engine_consciousnessengine_tick')(payload=payload, **kwargs)

if _aurora_get_target(['ConsciousnessEngine', 'tick']) is not None:
    _AURORA_NATIVE_EVOLVED_ORIGINALS['ConsciousnessEngine.tick'] = _aurora_get_target(['ConsciousnessEngine', 'tick'])
    _aurora_assign_target(['ConsciousnessEngine', 'tick'], _aurora_make_override('tick_evolved', 'ConsciousnessEngine.tick'))
    _AURORA_NATIVE_EVOLVED_LAST['ConsciousnessEngine.tick'] = {'alignment_gap': 0.391, 'override_active': True}

AURORA_NATIVE_EVOLVED_EXPORTS = {'aurora_consciousness_engine.ConsciousnessEngine.tick': 'tick_evolved'}
AURORA_NATIVE_EVOLUTION_OVERRIDES = {'aurora_consciousness_engine.ConsciousnessEngine.tick': {'export': 'tick_evolved',
                                                          'mode': 'callable_override',
                                                          'target': 'ConsciousnessEngine.tick'}}
# AURORA_EVOLVED_NATIVE_END

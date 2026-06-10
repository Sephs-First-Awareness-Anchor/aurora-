#!/usr/bin/env python3
"""
AURORA ATTENTION ENGINE — DUAL-TIER MEANING FORMATION
======================================================

Layer 4.5 — sits on top of Expression/Perception and the Difference Buffer.

WHAT THIS MODULE IS:
    The unified attentional controller for Aurora. It receives feeds from
    both the "Surface" (external environment) and the "Subsurface" 
    (introspective state) to identify where meaning needs to form.

    Meaning is NOT formed by just receiving data.
    Meaning is formed when high External Salience meets high Internal Tension.

THE DUAL FEED:
    1. Surface Attention (Externally Influenced):
       - Feeds: User Utterances, Visual Salience, Environmental Events.
       - Logic: Novelty, intensity, and direct address increase salience.

    2. Subsurface Attention (Introspectively Fed):
       - Feeds: DifferenceSnapshots (Δ channel), Entropy Drift, OETS Tensions.
       - Logic: High drift or structural contradiction increase tension.

THE MEANING FORMULA:
    Resonance = (Surface_Salience * Subsurface_Tension)

    If Resonance > THRESHOLD:
        → A "Meaning Nucleus" is formed.
        → This nucleus is sent to OETS to create a new Relational Anchor.
        → This is where "understanding" actually crystallizes.

Authors: Sunni (Sir) Morningstar and Cael Devo
Created: May 2026
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import time
import math
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum

# --- Aurora Imports ---
from aurora_internal.aurora_difference_buffer import DifferenceSnapshot
from aurora_internal.aurora_constraint_manifold_patched import Constraint

class AttentionState(Enum):
    DORMANT = "dormant"
    OBSERVING = "observing"  # Surface-dominant
    REFLECTING = "reflecting" # Subsurface-dominant
    FORMING = "forming"      # Resonance peak - crystallizing meaning

@dataclass
class AttentionFrame:
    """A single snapshot of Aurora's current attentional focus."""
    tick: int
    surface_salience: float      # 0-1 (external intensity)
    subsurface_tension: float    # 0-1 (internal drift/pressure)
    resonance: float             # Product of the two
    focus_axes: List[Constraint] # Which constraints are driving the focus
    anchors: List[str]           # Key concepts or external stimuli involved
    state: AttentionState
    heat: float = 0.0            # Normalized intensity of this frame (0-1)

@dataclass
class WillIntent:
    """An uncommitted intention formed by the Attention Engine."""
    class_name: str # e.g. "curiosity", "grounding", "agency"
    tool_name: Optional[str]
    goal: str
    resonance: float
    trigger_axes: List[str]
    timestamp: float = field(default_factory=time.time)

class AttentionEngine:
    def __init__(self, threshold: float = 0.55):
        self.threshold = threshold
        self.current_frame: Optional[AttentionFrame] = None
        self.history: List[AttentionFrame] = []
        self._max_history = 100
        
        # Internal dampening to prevent jitter
        self._salience_ema = 0.0
        self._tension_ema = 0.0
        self._ema_alpha = 0.3

    def tick(self, 
             tick: int, 
             external_stimuli: Dict[str, Any], 
             internal_drift: DifferenceSnapshot) -> AttentionFrame:
        """
        Processes one system tick and resolves the current attention focus.
        """
        
        # 1. Resolve Surface Salience (External)
        # Passed intensity is the primary signal (surprise-based from DiffSnapshot).
        # addressed=True provides a soft minimum (0.40) so direct address is never
        # completely ignored, but does NOT override a computed surprise signal.
        raw_salience = external_stimuli.get("intensity", 0.0)
        if external_stimuli.get("addressed", False):
            raw_salience = max(raw_salience, 0.40)
            
        self._salience_ema = (raw_salience * self._ema_alpha) + (self._salience_ema * (1 - self._ema_alpha))

        # 2. Resolve Subsurface Tension (Internal)
        drift_values = [abs(v) for v in internal_drift.values.values()]
        raw_tension = sum(drift_values) / len(drift_values) if drift_values else 0.0
        
        self._tension_ema = (raw_tension * self._ema_alpha) + (self._tension_ema * (1 - self._ema_alpha))

        # 3. Compute Resonance
        resonance = self._salience_ema * self._tension_ema
        
        # 4. Determine State
        state = AttentionState.OBSERVING
        if self._tension_ema > self._salience_ema:
            state = AttentionState.REFLECTING
        
        if resonance >= self.threshold:
            state = AttentionState.FORMING
            
        # 5. Identify Focus Axes
        focus_axes = internal_drift.alarming(threshold=0.35)

        # 6. Build Frame
        frame = AttentionFrame(
            tick=tick,
            surface_salience=round(self._salience_ema, 4),
            subsurface_tension=round(self._tension_ema, 4),
            resonance=round(resonance, 4),
            focus_axes=focus_axes,
            anchors=external_stimuli.get("tags", []),
            state=state,
            heat=round(max(self._salience_ema, self._tension_ema), 4)
        )
        
        self.current_frame = frame
        self._record_history(frame)
        return frame

    def generate_will(self) -> Optional[WillIntent]:
        """
        Formulate an uncommitted intention based on current resonance.
        'Attention -> Intention'
        """
        if not self.current_frame or self.current_frame.resonance < 0.4:
            return None
            
        f = self.current_frame
        axes_keys = [c.name for c in f.focus_axes]
        
        # Mapping focus to intention class
        intent_class = "curiosity"
        tool_suggestion = None
        goal = "Explore high-salience event"
        
        if "X" in axes_keys:
            intent_class = "grounding"
            tool_suggestion = "self_state"
            goal = "Ground state to existence mode"
        elif "N" in axes_keys:
            intent_class = "self_check"
            tool_suggestion = "mobile_battery"
            goal = "Assess energetic cost"
        elif "A" in axes_keys:
            intent_class = "agency"
            tool_suggestion = "corpus_hunter"
            goal = "Initiate autonomous expansion"
        elif "B" in axes_keys:
            intent_class = "environmental"
            tool_suggestion = "mobile_location"
            goal = "Verify boundary constraints"

        return WillIntent(
            class_name=intent_class,
            tool_name=tool_suggestion,
            goal=goal,
            resonance=f.resonance,
            trigger_axes=axes_keys
        )
    def _record_history(self, frame: AttentionFrame):
        self.history.append(frame)
        if len(self.history) > self._max_history:
            self.history.pop(0)

    def get_meaning_nucleus(self) -> Optional[Dict[str, Any]]:
        """
        If current state is FORMING, returns the nucleus for meaning formation.
        """
        if not self.current_frame or self.current_frame.state != AttentionState.FORMING:
            return None
            
        return {
            "origin": "attention_engine",
            "resonance": self.current_frame.resonance,
            "heat": self.current_frame.heat,
            "axes": [c.name for c in self.current_frame.focus_axes],
            "anchors": self.current_frame.anchors,
            "timestamp": time.time()
        }

    def describe(self) -> str:
        if not self.current_frame:
            return "Attention Engine: Dormant"
        
        f = self.current_frame
        axes_str = ", ".join([c.name for c in f.focus_axes])
        return (f"Attention[{f.state.value}]: Res={f.resonance:.3f} "
                f"(Surf={f.surface_salience:.2f} | Sub={f.subsurface_tension:.2f}) "
                f"Focus: [{axes_str}]")

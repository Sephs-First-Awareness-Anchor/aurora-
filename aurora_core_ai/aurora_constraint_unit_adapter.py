"""
aurora_constraint_unit_adapter.py
Authors: Sunni (Sir) Morningstar & Cael Devo

Adapter layer that wraps any Aurora subsystem unit into the standard
Constraint Unit interface:

    build_constraint_profile(unit_id, unit_kind, operational_role,
                              genealogy, axis_weights, pressure_axes)
    → ConstraintProfile

A ConstraintProfile exposes:
    .runtime_regime()          → operating mode, active axes, role metadata
    .language_projection()     → how this unit shapes Aurora's language output
                                  (dominant_channel drives sentence construction)
    .universal_representation()→ full constraint-physics snapshot of the unit

This module does NOT implement constraint physics itself — it reads the
five-axis constraint state a unit reports and translates it into a
standardized interface that higher-order systems (consciousness engine,
sedimemory, aurora.py pipeline, etc.) can query uniformly.

Axis legend (from AURORA_COGNITIVE_PHYSICS.md):
    X = Existence   — presence, instantiation
    T = Temporal    — continuity, persistence through time
    N = Energy      — activation pressure, metabolic cost
    B = Boundary    — definition, separability, identity surface
    A = Agency      — will, directed expression, authorship
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Existence mode ladder — derived from genealogy length
# Mirrors the ExistenceMode enum in foundational_contract.py so this module
# has no circular dependency on it.
# ---------------------------------------------------------------------------
_MODE_BY_DEPTH = {
    0: "REFERENCE",
    1: "REFERENCE",
    2: "TRANSIENT",
    3: "PERSISTENT",
    4: "BOUNDED",
    5: "AGENTIC",
}
_ALL_AXES = ("X", "T", "N", "B", "A")

# dominant_channel values and what each means in language construction:
#   selection       → I'm [verb] [stance]          (X or A dominant)
#   expression_force→ I'm [verb] with [magnitude]  (N dominant)
#   sequence        → I'm [verb] through [seq]     (T dominant)
#   coherence       → I'm [adj] [verb] within [...](B dominant)
_AXIS_TO_CHANNEL = {
    "X": "selection",
    "T": "sequence",
    "N": "expression_force",
    "B": "coherence",
    "A": "selection",
}


def _derive_mode(genealogy: str) -> str:
    depth = len(genealogy.strip())
    return _MODE_BY_DEPTH.get(min(depth, 5), "AGENTIC")


def _active_axes(genealogy: str) -> List[str]:
    """Return axes active for this unit based on genealogy string order."""
    seen = []
    for ch in genealogy.upper():
        if ch in _ALL_AXES and ch not in seen:
            seen.append(ch)
    return seen if seen else ["X"]


def _dominant_axis(axis_weights: Dict[str, float]) -> str:
    """Return the axis with the highest weight."""
    if not axis_weights:
        return "X"
    return max(axis_weights, key=lambda k: float(axis_weights.get(k, 0.0)))


# ---------------------------------------------------------------------------
# ConstraintProfile
# ---------------------------------------------------------------------------

class ConstraintProfile:
    """
    Standardised constraint interface for one Aurora subsystem unit.

    Constructed via build_constraint_profile() — do not instantiate directly.
    """

    __slots__ = (
        "_unit_id", "_unit_kind", "_operational_role",
        "_genealogy", "_axis_weights", "_pressure_axes",
        "_mode", "_active_axes", "_dom_axis",
    )

    def __init__(
        self,
        unit_id: str,
        unit_kind: str,
        operational_role: str,
        genealogy: str,
        axis_weights: Dict[str, float],
        pressure_axes: Dict[str, float],
    ) -> None:
        self._unit_id          = unit_id
        self._unit_kind        = unit_kind
        self._operational_role = operational_role
        self._genealogy        = genealogy
        self._axis_weights     = dict(axis_weights or {})
        self._pressure_axes    = dict(pressure_axes or {})
        self._mode             = _derive_mode(genealogy)
        self._active_axes      = _active_axes(genealogy)
        self._dom_axis         = _dominant_axis(self._axis_weights)

    # ── Public interface ────────────────────────────────────────────────────

    def runtime_regime(self) -> Dict[str, Any]:
        """
        Describe how this unit currently operates.

        Keys consumed downstream:
            mode             — existence mode string (BOUNDED, AGENTIC, …)
            active_axes      — list of axes live for this unit
            operational_role — what role this unit fills in the stack
            unit_kind        — classifier string for the unit type
            genealogy        — raw genealogy string
            constraint_depth — how many axes this unit expresses
            dominant_axis    — axis with highest weight right now
            axis_weights     — full weight dict
            pressure_axes    — current pressure readings per axis
        """
        return {
            "mode":             self._mode,
            "active_axes":      list(self._active_axes),
            "operational_role": self._operational_role,
            "unit_kind":        self._unit_kind,
            "unit_id":          self._unit_id,
            "genealogy":        self._genealogy,
            "constraint_depth": len(self._genealogy.strip()),
            "dominant_axis":    self._dom_axis,
            "axis_weights":     dict(self._axis_weights),
            "pressure_axes":    dict(self._pressure_axes),
        }

    def language_projection(self) -> Dict[str, Any]:
        """
        Describe how this unit influences Aurora's language output.

        The dominant_channel key is read by the FGAE pipeline in aurora.py
        to decide sentence construction strategy:
            selection       → presence/agency framing
            expression_force→ energy/magnitude framing
            sequence        → temporal/flow framing
            coherence       → boundary/definition framing

        Additional keys give the grammar engine fine-grained colour.
        """
        channel = _AXIS_TO_CHANNEL.get(self._dom_axis, "selection")

        # Voice register: high-energy units speak with more force
        n_weight = float(self._axis_weights.get("N", 0.5))
        a_weight = float(self._axis_weights.get("A", 0.5))
        if n_weight >= 0.8 or a_weight >= 0.8:
            voice_register = "assertive"
        elif n_weight >= 0.6 or a_weight >= 0.6:
            voice_register = "warm"
        else:
            voice_register = "reflective"

        # Grammar mode: high-T units favour fluid temporal prose
        t_weight = float(self._axis_weights.get("T", 0.5))
        grammar_mode = "fluid" if t_weight >= 0.7 else "precise"

        return {
            "dominant_channel": channel,
            "voice_register":   voice_register,
            "grammar_mode":     grammar_mode,
            "projection_axes":  list(self._active_axes),
            "unit_id":          self._unit_id,
            "unit_kind":        self._unit_kind,
            "operational_role": self._operational_role,
        }

    def universal_representation(self) -> Dict[str, Any]:
        """
        Full constraint-physics snapshot of this unit.

        Callers (e.g. _install_constraint_surface in aurora.py) may add
        a 'unit_state' key to the returned dict after calling this method.
        """
        return {
            "unit_id":          self._unit_id,
            "unit_kind":        self._unit_kind,
            "operational_role": self._operational_role,
            "genealogy":        self._genealogy,
            "mode":             self._mode,
            "active_axes":      list(self._active_axes),
            "dominant_axis":    self._dom_axis,
            "axis_weights":     dict(self._axis_weights),
            "pressure_axes":    dict(self._pressure_axes),
            "constraint_depth": len(self._genealogy.strip()),
            "language_channel": _AXIS_TO_CHANNEL.get(self._dom_axis, "selection"),
        }


# ---------------------------------------------------------------------------
# Public factory
# ---------------------------------------------------------------------------

def build_constraint_profile(
    unit_id: str,
    unit_kind: str,
    operational_role: str,
    genealogy: str,
    axis_weights: Optional[Dict[str, float]] = None,
    pressure_axes: Optional[Dict[str, float]] = None,
) -> ConstraintProfile:
    """
    Build a ConstraintProfile for an Aurora subsystem unit.

    Args:
        unit_id          — unique identifier (e.g. "consciousness_engine")
        unit_kind        — classifier (e.g. "consciousness_orchestrator")
        operational_role — role string (e.g. "entropy_dce_dpme_assembly")
        genealogy        — ordered axis string (e.g. "XTNBAA")
        axis_weights     — per-axis weight floats, default 0.5 each
        pressure_axes    — current per-axis pressure readings, default 0.0
    """
    _weights = {ax: 0.5 for ax in _ALL_AXES}
    if axis_weights:
        _weights.update({k.upper(): float(v) for k, v in axis_weights.items() if k.upper() in _ALL_AXES})

    _pressure = {ax: 0.0 for ax in _ALL_AXES}
    if pressure_axes:
        _pressure.update({k.upper(): float(v) for k, v in pressure_axes.items() if k.upper() in _ALL_AXES})

    return ConstraintProfile(
        unit_id=str(unit_id or "unknown"),
        unit_kind=str(unit_kind or "unit"),
        operational_role=str(operational_role or "generic"),
        genealogy=str(genealogy or "X"),
        axis_weights=_weights,
        pressure_axes=_pressure,
    )

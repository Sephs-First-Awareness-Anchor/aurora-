"""
aurora_constraint_ontology.py

Constraint ontology functions for Aurora subsystems.
Provides axis-weight → signature/projection/regime derivation used by
aurora_sedimemory.py and aurora_internal/aurora_runtime_constraint_governor.py.

Axis legend (from AURORA_COGNITIVE_PHYSICS.md):
    X = Existence   — presence, instantiation
    T = Temporal    — continuity, persistence through time
    N = Energy      — activation pressure, metabolic cost
    B = Boundary    — definition, separability, identity surface
    A = Agency      — will, directed expression, authorship
"""
from __future__ import annotations

from typing import Any, Dict, Optional

_ALL_AXES = ("X", "T", "N", "B", "A")

_MODE_BY_DEPTH = {
    0: "REFERENCE",
    1: "REFERENCE",
    2: "TRANSIENT",
    3: "PERSISTENT",
    4: "BOUNDED",
    5: "AGENTIC",
}

_AXIS_TO_CHANNEL = {
    "X": "selection",
    "T": "sequence",
    "N": "expression_force",
    "B": "coherence",
    "A": "selection",
}

_THRESHOLD = 0.5


def _normalise_weights(axis_weights: Optional[Dict[str, float]]) -> Dict[str, float]:
    base = {ax: 0.5 for ax in _ALL_AXES}
    if axis_weights:
        for k, v in axis_weights.items():
            if k.upper() in _ALL_AXES:
                base[k.upper()] = float(v)
    return base


def _normalise_pressure(pressure_axes: Optional[Dict[str, float]]) -> Dict[str, float]:
    base = {ax: 0.0 for ax in _ALL_AXES}
    if pressure_axes:
        for k, v in pressure_axes.items():
            if k.upper() in _ALL_AXES:
                base[k.upper()] = float(v)
    return base


def derive_signature_from_axes(
    axis_weights: Optional[Dict[str, float]],
    include_weighting: bool = False,
) -> str:
    """
    Return an ordered axis-string signature for the given weight map.

    Axes above the activation threshold (0.5) are included in descending
    weight order.  If include_weighting is True each axis is suffixed with
    its rounded weight value, e.g. "X0.8T0.7N0.6".
    """
    weights = _normalise_weights(axis_weights)
    active = sorted(
        [(ax, weights[ax]) for ax in _ALL_AXES if weights[ax] > _THRESHOLD],
        key=lambda t: t[1],
        reverse=True,
    )
    if not active:
        return "X"
    if include_weighting:
        return "".join(f"{ax}{w:.1f}" for ax, w in active)
    return "".join(ax for ax, _ in active)


def derive_language_projection(
    axis_weights: Optional[Dict[str, float]],
    pressure_axes: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Return how the given axis state shapes Aurora's language output.

    Keys:
        dominant_channel  — sentence construction strategy
        voice_register    — assertive / warm / reflective
        grammar_mode      — fluid / precise
        projection_axes   — list of active axes
    """
    weights  = _normalise_weights(axis_weights)
    pressure = _normalise_pressure(pressure_axes)

    # Dominant axis by weight
    dom_axis = max(weights, key=lambda k: weights[k])

    # Active axes (above threshold)
    active = [ax for ax in _ALL_AXES if weights[ax] > _THRESHOLD]
    if not active:
        active = ["X"]

    channel = _AXIS_TO_CHANNEL.get(dom_axis, "selection")

    n_w = weights.get("N", 0.5)
    a_w = weights.get("A", 0.5)
    if n_w >= 0.8 or a_w >= 0.8:
        voice_register = "assertive"
    elif n_w >= 0.6 or a_w >= 0.6:
        voice_register = "warm"
    else:
        voice_register = "reflective"

    t_w = weights.get("T", 0.5)
    grammar_mode = "fluid" if t_w >= 0.7 else "precise"

    return {
        "dominant_channel": channel,
        "voice_register":   voice_register,
        "grammar_mode":     grammar_mode,
        "projection_axes":  active,
        "dominant_axis":    dom_axis,
        "axis_weights":     dict(weights),
        "pressure_axes":    dict(pressure),
    }


def derive_runtime_regime(
    axis_weights: Optional[Dict[str, float]],
    signature: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Return the operating regime for a unit with the given axis weights.

    Keys:
        mode             — existence mode string
        active_axes      — axes above activation threshold
        dominant_axis    — axis with highest weight
        constraint_depth — number of active axes
        signature        — axis signature string
        axis_weights     — normalised weight dict
    """
    weights = _normalise_weights(axis_weights)
    active  = [ax for ax in _ALL_AXES if weights[ax] > _THRESHOLD]
    if not active:
        active = ["X"]
    depth   = len(active)
    mode    = _MODE_BY_DEPTH.get(min(depth, 5), "AGENTIC")
    dom     = max(weights, key=lambda k: weights[k])
    sig     = signature if signature else derive_signature_from_axes(weights)

    return {
        "mode":             mode,
        "active_axes":      active,
        "dominant_axis":    dom,
        "constraint_depth": depth,
        "signature":        sig,
        "axis_weights":     dict(weights),
    }


def describe_memory_contract(
    signature: Optional[str],
    axis_weights: Optional[Dict[str, float]],
    pressure_axes: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Return the full memory contract for a sedimemory node.

    Keys consumed by SediMemoryNode.__init__:
        language_projection  — dict from derive_language_projection()
        regime               — dict from derive_runtime_regime()
        weighted_form        — per-axis weight×pressure product map
        signature            — axis signature string
    """
    weights  = _normalise_weights(axis_weights)
    pressure = _normalise_pressure(pressure_axes)
    sig      = signature if signature else derive_signature_from_axes(weights)

    lang_proj = derive_language_projection(weights, pressure)
    regime    = derive_runtime_regime(weights, sig)

    weighted_form = {
        ax: round(weights[ax] * (1.0 + pressure.get(ax, 0.0)), 4)
        for ax in _ALL_AXES
    }

    return {
        "language_projection": lang_proj,
        "regime":              regime,
        "weighted_form":       weighted_form,
        "signature":           sig,
    }

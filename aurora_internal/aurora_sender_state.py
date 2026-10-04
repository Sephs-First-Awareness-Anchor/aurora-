"""Her own agentic state, as the response's orientation needs it.

Authors: Sunni (Sir) Morningstar and Cael Devo

An observed user turn is admitted as a PERSISTENT node: its agency (and boundary) axes are
zero by the node's MODE. That says nothing about Aurora, yet the assembly built from it was
the only axis state the response's structure selection, the dual-strata predictor and the
motif learning ever saw, so her agency was 0.0 on every turn and every motif that succeeded
learned "agency pressure ~ 0".

The sender is the identity field (NoncompField, "the live identity field backing Aurora's
cognition"): per-axis pressures that accumulate on input, receive internal signals (the
reflection cycle pumps a valuation signal into agency when understanding is reached), and
decay with resolved accuracy. It is stateful and history-dependent, which a per-utterance
parse is not. Its pressure ABOVE ITS OWN NEUTRAL REFERENCE (reference_axis_pressures(),
exposed so consumers do not hard-code one) is her state on each axis.

A leaf module on purpose: the engine and the composer both use it.
"""
from typing import Any, Dict, List, Optional

AXES = ("X", "T", "N", "B", "A")
_ALIASES = {
    "x": "X", "existence": "X",
    "t": "T", "temporal": "T", "time": "T",
    "n": "N", "energy": "N",
    "b": "B", "boundary": "B",
    "a": "A", "agency": "A",
}


def sender_axis_state(field: Any) -> Optional[Dict[str, float]]:
    """Per-axis pressure above the identity field's own neutral reference; None when the
    field is absent, unreadable, or carries no pressure above reference."""
    if field is None or not hasattr(field, "status"):
        return None
    try:
        pressures = dict((field.status() or {}).get("axis_pressures") or {})
        reference = dict(field.reference_axis_pressures()) if hasattr(field, "reference_axis_pressures") else {}
    except Exception:
        return None
    out = {ax: max(0.0, float(pressures.get(ax, 0.0)) - float(reference.get(ax, 0.0))) for ax in AXES}
    return out if any(v > 0.0 for v in out.values()) else None


def fill_inactive_axes(activation: Dict[str, float], sender: Optional[Dict[str, float]]) -> Dict[str, float]:
    """Take the axes an observed node's mode leaves inactive from the SENDER's own state.

    Scale-matched: the sender's axes are in a different unit from the assembly's, so an
    inactive axis takes the sender's weight for it RELATIVE to the axes the assembly does
    carry. No constant is introduced; axes the assembly carries are never altered; with no
    sender state the input is returned unchanged.
    """
    if not activation or not sender:
        return activation
    active = [ax for ax in AXES if float(activation.get(ax, 0.0)) > 1e-9]
    inactive = [ax for ax in AXES if float(activation.get(ax, 0.0)) <= 1e-9
                and float(sender.get(ax, 0.0)) > 0.0]
    if not active or not inactive:
        return activation
    sender_on_active = sum(float(sender.get(ax, 0.0)) for ax in active)
    if sender_on_active <= 1e-9:
        return activation
    scale = sum(float(activation[ax]) for ax in active) / sender_on_active
    out = dict(activation)
    for ax in inactive:
        out[ax] = float(sender[ax]) * scale
    return out


def fill_assembly_axes_from_sender(adjusted_axes: Any, field: Any) -> List[str]:
    """Fill, IN PLACE, the axes of an assembly's adjusted_axes that its node's mode left at
    zero, from the identity field. Works under either axis naming. Returns the axes filled."""
    if not isinstance(adjusted_axes, dict) or not adjusted_axes:
        return []
    sender = sender_axis_state(field)
    if not sender:
        return []
    key_of: Dict[str, str] = {}
    activation: Dict[str, float] = {}
    for key, value in adjusted_axes.items():
        ax = _ALIASES.get(str(key).lower())
        if ax is None:
            continue
        try:
            activation[ax] = float(value)
        except (TypeError, ValueError):
            continue
        key_of[ax] = key
    if not activation:
        return []
    filled = fill_inactive_axes(activation, sender)
    changed = [ax for ax in AXES if ax in key_of and float(filled.get(ax, 0.0)) != float(activation.get(ax, 0.0))]
    for ax in changed:
        adjusted_axes[key_of[ax]] = round(float(filled[ax]), 4)
    return changed

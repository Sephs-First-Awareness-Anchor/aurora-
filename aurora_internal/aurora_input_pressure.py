"""Input as pressure: where an utterance sits on each of the five axes.

Authors: Sunni (Sir) Morningstar and Cael Devo

Every word she has crystallized sits in a concept channel ("B:POLARITY", "T:OPERATOR", ...)
whose axis is that word's constraint character. An utterance's pressure on the manifold is
therefore the distribution of its words' axes. This returns it as the per-axis phase vector
lattice.admit(phases=...) takes (positive-pole weight in [0, 1], order X, T, N, B, A):

  * an axis none of the words load stays NEUTRAL (0.5 -> zero displacement): absence is not
    opposition;
  * the most-loaded axis reaches 1.0 and the rest scale with it, so no tuning constant exists;
  * None when no word of the text has a channel, in which case the node sits where the
    vertices are, exactly as before.

Axes inactive for the node's ExistenceMode are zeroed by the coordinate itself (an observed
user turn is PERSISTENT: X, T, N only); the pressure the words put on B and A still reaches
sediment through the per-word deposits.

A leaf module on purpose: both the gateway and aurora.py use it, and neither may import the
other.
"""
import re
from typing import Any, Dict, List, Optional

AXES = ("X", "T", "N", "B", "A")  # == aurora_ivm.AXIS_ORDER: existence, temporal, energy, boundary, agency


def content_axis_loads(perception: Any, text: str) -> Optional[Dict[str, float]]:
    """Per-axis pressure of an utterance in [0, 1], the most-loaded axis at 1.0.

    The same distribution content_phase_vector expresses as phases; consumers that want a
    MAGNITUDE (the pressure pump's disturbance, a sediment geometry) take it from here
    instead of a global aggregate that is identical for every utterance. None when no word
    of the text has a channel."""
    entries = None
    for holder in (getattr(perception, "composer", None), perception):
        lex = getattr(holder, "lexicon", None)
        if lex is not None and getattr(lex, "entries", None):
            entries = lex.entries
            break
    if not entries:
        return None
    loads = {a: 0.0 for a in AXES}
    for w in re.findall(r"[a-z][a-z'\-]+", str(text or "").lower()):
        e = entries.get(w)
        ncid = getattr(e, "noncomp_id", None) if e is not None else None
        axis = str(ncid).split(":")[0] if ncid else ""
        if axis in loads:
            loads[axis] += 1.0
    peak = max(loads.values())
    if peak <= 0.0:
        return None
    return {a: loads[a] / peak for a in AXES}


def content_phase_vector(perception: Any, text: str) -> Optional[List[float]]:
    loads = content_axis_loads(perception, text)
    if loads is None:
        return None
    return [0.5 + 0.5 * loads[a] for a in AXES]

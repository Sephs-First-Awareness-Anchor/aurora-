# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Graded convergence between concepts and between wholes (build plan P2).

Sir: nothing should be measured like a threshold; it is a gradient between varying pressures and their many representations.  So nothing here
decides "converged or not".  Every quantity is a continuous degree in [0, 1] that moves smoothly with the evidence; a consumer reads the degree
and weighs by it.  The only limits are on how many results are RETURNED (a capacity), never on what counts.

  * `members_of(store, hub)`      what a hub holds (the things said or seen to be of that kind), each to its degree.
  * `convergence(store, a, b)`   how alike two concepts' counted neighbourhoods are (weighted cosine, a and b themselves left out).
  * `field_of(store, hub)`       a whole around a hub: every concept's degree of belonging to it, from its own association with the hub and
                                 from how far its neighbourhood converges with the hub's.  A soft set; letters are found, not listed.
  * `whole_convergence(f, g)`    how far two wholes converge (cosine of their fields): the degree to which they take part in a more general whole.
  * `general_field(fields, w)`    that more general whole: the weighted blend of the wholes' fields.

Only counted associations are read (the store's own rule), so a heuristic or looked-up association contributes nothing until recurrence or what was
said earns it.  Reads only; changes nothing.  Isolated: imports only the association store.
"""
from __future__ import annotations

import math
from typing import Dict, Iterable, Mapping, Optional, Tuple

from aurora_internal.crystal_associations import AssociationStore

Field = Dict[str, float]


def _cos(u: Mapping[str, float], v: Mapping[str, float]) -> float:
    if not u or not v:
        return 0.0
    if len(u) > len(v):
        u, v = v, u
    dot = sum(x * v.get(k, 0.0) for k, x in u.items())
    nu = math.sqrt(sum(x * x for x in u.values()))
    nv = math.sqrt(sum(x * x for x in v.values()))
    return 0.0 if nu <= 0.0 or nv <= 0.0 else max(0.0, min(1.0, dot / (nu * nv)))


def members_of(store: AssociationStore, hub: str, rtype: str = "is_a") -> Field:
    """What the hub holds: every concept counted as a `rtype` of it, with the degree it is held to.  Found from the store, never listed in advance."""
    return store.incoming(hub, rtype)


def convergence(store: AssociationStore, a: str, b: str) -> float:
    """How alike what `a` is associated with is to what `b` is associated with (each other left out).  0 when they share nothing, 1 when they are
    associated with the same things in the same proportion.  Moves continuously with every strength."""
    na = {k: v for k, v in store.connections_for(a).items() if k not in (a, b)}
    nb = {k: v for k, v in store.connections_for(b).items() if k not in (a, b)}
    return _cos(na, nb)


def field_of(store: AssociationStore, hub: str, universe: Optional[Iterable[str]] = None, top: Optional[int] = None) -> Field:
    """The whole around `hub`: concept -> degree of belonging, in (0, 1].  A concept belongs to the degree that it is itself associated with the hub or its
    neighbourhood converges with the hub's, combined as 1 - (1 - direct)(1 - convergence) so that either pulls it in and both pull harder.  Candidates are the
    hub's neighbours and their neighbours (or `universe`).  `top` limits how many are RETURNED (strongest first), not who belongs."""
    direct = store.connections_for(hub)
    if universe is None:
        cands = set(direct)
        for n in direct:
            cands.update(store.connections_for(n))
        cands.discard(hub)
    else:
        cands = {c for c in universe if c != hub}
    out: Field = {}
    for m in cands:
        d = direct.get(m, 0.0)
        c = convergence(store, hub, m)
        deg = 1.0 - (1.0 - d) * (1.0 - c)
        if deg > 0.0:
            out[m] = deg
    if top is not None and len(out) > top:
        out = dict(sorted(out.items(), key=lambda kv: -kv[1])[:top])
    return out


def whole_convergence(f: Mapping[str, float], g: Mapping[str, float]) -> float:
    """The degree to which two wholes converge: the cosine of their fields.  Two wholes made of the same things to the same degree are one whole (1);
    two with nothing in common are separate (0); everything between is a matter of degree."""
    return _cos(f, g)


def general_field(fields: Mapping[str, Mapping[str, float]], weights: Optional[Mapping[str, float]] = None) -> Field:
    """The more general whole the given wholes take part in: each concept's degree is the weighted mean of its degree in every whole (absent = 0), so a
    concept belonging to many of them belongs more, and one belonging to a single whole belongs a little.  `weights` (default equal) is how much each whole
    counts, for instance by how far it has converged with the others."""
    if not fields:
        return {}
    w = {k: float((weights or {}).get(k, 1.0)) for k in fields}
    tot = sum(max(0.0, x) for x in w.values())
    if tot <= 0.0:
        return {}
    out: Field = {}
    for name, f in fields.items():
        wt = max(0.0, w[name]) / tot
        for m, deg in f.items():
            out[m] = out.get(m, 0.0) + wt * deg
    return out


def convergence_matrix(fields: Mapping[str, Mapping[str, float]]) -> Dict[Tuple[str, str], float]:
    """Every pair of wholes with the degree they converge (each pair once, names in sorted order)."""
    names = sorted(fields)
    return {(a, b): whole_convergence(fields[a], fields[b]) for i, a in enumerate(names) for b in names[i + 1:]}

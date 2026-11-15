# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Promotion by associative group classification (Sir, 2026-11-15).

Related or commonly occurring crystals that can be classified by a single generalization promote to a higher-level crystal under that generalization.  So
promotion is not a count of facets or uses on one crystal: it is a group of crystals found, by what they are associated with, to be one kind of thing.
Isolated and read-only: it reads an `AssociationStore` (counted evidence only) and plain level numbers, and it changes nothing.

Everything is a degree in [0, 1] (the one level is a position between 1 and 4); there is no cut-off anywhere:

  * `classification(store, g)`       how far each crystal is classified under g: what g holds as `is_a`, plus the group's peers by how closely they match it.
  * `unity(store, members)`          how single the group is: the mean match between its members' associations, leaving out g itself (0 when fewer than two).
  * `promotion_degree(store, g)`     (how much is classified under g, x / (x + k)) x (how single that group is).  More members, more strongly classified,
                                     and more alike all raise it; a heterogeneous or tiny group stays low.
  * `promotion_candidates(...)`      every candidate generalization ranked by degree (`top` only limits how many are returned).
  * `level_under(store, g, levels)`  the level g stands at: 1 + degree x the (classification-weighted) mean level of what it generalises, so it is above its members
                                     by that degree; clamped to 4.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Mapping, Optional, Tuple

from aurora_internal.crystal_associations import AssociationStore
from aurora_internal.crystal_convergence import _cos, members_of

# The mass of classification at which a generalization is half-promoted: spec reference for a composite's associative count (5), a starting reference, not a bar.
REF_MASS = 5.0
MAX_LEVEL = 4.0


def _profile(store: AssociationStore, c: str, leave_out: Iterable[str]) -> Dict[str, float]:
    skip = set(leave_out) | {c}
    return {k: v for k, v in store.connections_for(c).items() if k not in skip}


def classification(store: AssociationStore, g: str, universe: Optional[Iterable[str]] = None) -> Dict[str, float]:
    """Crystal -> degree classified under g.  What g holds as `is_a` comes in at the strength it is held; a crystal that is not said to be one but is tied
    to the same things the group is (the group's peers) comes in by how closely its associations match the group's, in proportion.  The things the
    members are merely associated with (their attributes) are not classified under g."""
    pool = set(universe) if universe is not None else None
    held = {m: s for m, s in members_of(store, g).items() if pool is None or m in pool}
    out = dict(held)
    if not held:
        return out
    attrs: Dict[str, float] = {}
    for m in held:
        for k, v in _profile(store, m, [g]).items():
            attrs[k] = max(attrs.get(k, 0.0), v)
    strength = sum(held.values()) / len(held)
    peers = set()
    for t in attrs:
        peers |= set(store.connections_for(t))
    peers -= set(held) | set(attrs) | {g}
    for c in sorted(peers):
        if pool is not None and c not in pool:
            continue
        match = sum(_cos(_profile(store, c, [g]), _profile(store, m, [g])) * w for m, w in held.items()) / sum(held.values())
        if match > 0.0:
            out[c] = match * strength                    # as strongly as the group itself is held, in proportion to how closely it matches
    return out


def unity(store: AssociationStore, members: Iterable[str], leave_out: Iterable[str] = (), weights: Optional[Mapping[str, float]] = None) -> float:
    """How closely the members' associations match, pair by pair, leaving out the generalization itself (a tie they all share because they were classified
    together does not make them alike) and each other.  Each pair counts in proportion to how far both are classified (`weights`, default equal): 1 when
    all are tied to exactly the same things, 0 when they share nothing or there are fewer than two."""
    ms = sorted(set(members))
    if len(ms) < 2:
        return 0.0
    w = (lambda m: 1.0) if weights is None else (lambda m: max(0.0, float(weights.get(m, 0.0))))
    num = den = 0.0
    for i in range(len(ms)):
        for j in range(i + 1, len(ms)):
            pw = w(ms[i]) * w(ms[j])
            num += pw * _cos(_profile(store, ms[i], list(leave_out) + [ms[j]]), _profile(store, ms[j], list(leave_out) + [ms[i]]))
            den += pw
    return 0.0 if den <= 0.0 else num / den


def promotion_degree(store: AssociationStore, g: str, universe: Optional[Iterable[str]] = None) -> float:
    cls = classification(store, g, universe)
    mass = sum(cls.values())
    if mass <= 0.0:
        return 0.0
    return (mass / (mass + REF_MASS)) * unity(store, cls, [g], cls)


def promotion_candidates(store: AssociationStore, concepts: Iterable[str], top: Optional[int] = None) -> List[Tuple[str, float]]:
    """(generalization, degree) strongest first, for every concept that classifies anything.  `top` only limits how many are returned."""
    scored = []
    for g in sorted(set(concepts)):
        d = promotion_degree(store, g)
        if d > 0.0:
            scored.append((g, d))
    scored.sort(key=lambda kv: (-kv[1], kv[0]))
    return scored[:top] if top else scored


def level_under(store: AssociationStore, g: str, levels: Mapping[str, float]) -> float:
    """Where g stands: 1 + promotion degree x the mean level of what it generalises (weighted by how far each is classified under it), clamped to 4.  A
    generalization of level-1 crystals reaches up to 2; of level-2 crystals, up to 3.  With nothing classified under it, it stays at 1."""
    cls = classification(store, g)
    w = sum(cls.values())
    if w <= 0.0:
        return 1.0
    mean = sum(d * float(levels.get(m, 1.0)) for m, d in cls.items()) / w
    return min(MAX_LEVEL, 1.0 + promotion_degree(store, g) * mean)

# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Inward growth (Sir, 2026-11-15): a complex crystal deepens inside itself instead of spawning more crystals.

What a concept is tied to falls into aspects: groups of the things it is tied to that are tied to the same things as one another.  Those aspects belong
INSIDE the crystal, as inner layers, so one concept with many sides stays one crystal.  Each inner layer is the same kind of thing as the crystal (it holds
members, and can itself fall into aspects), so the structure is quasi-recursive: the same step is taken again within a layer, at a finer resolution.

Everything is a degree and nothing is cut off:

  * how far a crystal grows inward follows how fully it stands at the top level (`crystal_maturity.memberships(points)[4]`): a crystal that is not yet complex
    carries (almost) no interior, and one that is carries all it has found.  The standing itself is the multiplier; it is never read as a class.
  * a layer's weight is how single its members are (mean pairwise match of what they are tied to) x how much of the crystal's ties it holds (x / (x + k))
    x the crystal's standing.
  * the resolution gets finer with each step in: members are bound when they match by `1 - 0.5 ** (depth + 1)` (a half, three quarters, seven eighths...), the
    fuzzy "more alike than not" at the surface and half the remaining distance to identical at each step further in.  Depth is bounded only by what the
    evidence still separates (and `MAX_DEPTH`, which only bounds the work).

Isolated and read-only over an `AssociationStore`; `apply_to_crystals` writes only `crystal.interior`, additively (a layer, a member or a weight that is there
is kept and the stronger value wins).  The fading of a layer that is no longer carried is the resolution ledger's behaviour, not a relic kept here.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Tuple

from aurora_internal import crystal_maturity as _M
from aurora_internal.crystal_associations import AssociationStore
from aurora_internal.crystal_convergence import _cos

REF_LAYER_MASS = 3.0     # the strength of ties at which a layer is half-weighted: a starting reference, not a bar
FAN = 24                 # neighbours a crystal's aspects are found among (the strongest; bounds the work)
MAX_DEPTH = 3            # bounds the work only
MAX_LAYERS = 6           # per level of a crystal's interior; bounds memory only: the heaviest are kept


def resolution(depth: int) -> float:
    """The match two members need to be bound at this depth: finer each step in."""
    return 1.0 - 0.5 ** (int(depth) + 1)


def standing(crystal: Any) -> float:
    """How fully the crystal stands at the top level, from its maturity points (0.0 when none have been looked at)."""
    pts = getattr(crystal, "maturity", None)
    return 0.0 if pts is None else float(_M.memberships(pts).get(4, 0.0))


def _profile(store: AssociationStore, c: str, skip: set) -> Dict[str, float]:
    return {k: v for k, v in store.connections_for(c).items() if k not in skip}


def aspects(store: AssociationStore, concept: str, among: Optional[Mapping[str, float]] = None, depth: int = 0,
            profiles: Optional[Dict[str, Dict[str, float]]] = None) -> List[Dict[str, Any]]:
    """Groups of the concept's ties that match one another at this depth's resolution.  Each: {anchor, members {name: strength}, unity, mass}, heaviest
    first.  `among` limits the search to some of its ties (a layer's members)."""
    ties = {k: v for k, v in store.connections_for(concept).items() if v > 0.0}
    pool = {k: ties[k] for k in (among if among is not None else ties) if k in ties}
    names = sorted(pool, key=lambda k: (-pool[k], k))[:FAN]
    if len(names) < 2:
        return []
    cache = profiles if profiles is not None else {}
    prof = {n: cache.setdefault(n, _profile(store, n, {concept})) for n in names}
    bar = resolution(depth)
    sim: Dict[Tuple[str, str], float] = {}
    parent = {n: n for n in names}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            skip = {a, b, concept}
            s = _cos({k: v for k, v in prof[a].items() if k not in skip}, {k: v for k, v in prof[b].items() if k not in skip})
            sim[(a, b)] = s
            if s > bar:
                parent[find(a)] = find(b)
    groups: Dict[str, List[str]] = {}
    for n in names:
        groups.setdefault(find(n), []).append(n)
    out = []
    for members in groups.values():
        if len(members) < 2:
            continue
        pairs = [sim[(a, b)] if (a, b) in sim else sim[(b, a)] for i, a in enumerate(members) for b in members[i + 1:]]
        mass = sum(pool[m] for m in members)
        out.append({"anchor": sorted(members, key=lambda k: (-pool[k], k))[0], "members": {m: round(pool[m], 6) for m in sorted(members)},
                    "unity": round(sum(pairs) / len(pairs), 6), "mass": round(mass, 6)})
    out.sort(key=lambda g: (-g["unity"] * g["mass"], g["anchor"]))
    return out


def layers(store: AssociationStore, concept: str, scale: float = 1.0, among: Optional[Mapping[str, float]] = None, depth: int = 0,
           profiles: Optional[Dict[str, Dict[str, float]]] = None) -> List[Dict[str, Any]]:
    """The concept's inner layers at this depth, each with its own inner layers found the same way one step finer.  A layer that would only repeat the
    whole it came from (every member still bound) has nothing finer in it and holds no inner layers."""
    out = []
    cache = profiles if profiles is not None else {}
    for g in aspects(store, concept, among, depth, cache)[:MAX_LAYERS]:
        weight = g["unity"] * (g["mass"] / (g["mass"] + REF_LAYER_MASS)) * float(scale)
        layer = {"anchor": g["anchor"], "members": g["members"], "unity": g["unity"], "mass": g["mass"], "weight": round(weight, 6), "depth": depth, "inner": []}
        if depth + 1 < MAX_DEPTH:
            inner = layers(store, concept, scale, g["members"], depth + 1, cache)
            layer["inner"] = [x for x in inner if set(x["members"]) < set(g["members"])]
        out.append(layer)
    return out


def depth_of(interior: Optional[Mapping[str, Any]]) -> int:
    """How many steps in the interior goes (0 when it has none)."""
    def d(ls: List[Mapping[str, Any]]) -> int:
        return 0 if not ls else 1 + max(d(l.get("inner") or []) for l in ls)
    return d(list((interior or {}).get("layers") or []))


def _merge(old: List[Dict[str, Any]], new: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Additive: the same anchor is the same layer; members, weights and inner layers that are there are kept and the stronger value wins."""
    by = {l["anchor"]: dict(l, members=dict(l["members"]), inner=list(l.get("inner") or [])) for l in old}
    for l in new:
        cur = by.get(l["anchor"])
        if cur is None:
            by[l["anchor"]] = dict(l, members=dict(l["members"]), inner=list(l.get("inner") or []))
            continue
        for m, s in l["members"].items():
            cur["members"][m] = max(cur["members"].get(m, 0.0), s)
        for k in ("unity", "mass", "weight"):
            cur[k] = max(cur.get(k, 0.0), l[k])
        cur["inner"] = _merge(cur.get("inner") or [], l.get("inner") or [])
    return sorted(by.values(), key=lambda l: (-l["weight"], l["anchor"]))[: max(MAX_LAYERS, len(old))]


def apply_to_crystals(store: AssociationStore, concept_index: Mapping[str, str], crystals: Mapping[str, Any], dry_run: bool = True) -> Dict[str, Any]:
    """Give each crystal the interior its complexity earns.  Writes only `crystal.interior` ({"layers": [...], "standing": s, "depth": n}); a crystal with no
    standing at the top level (or no ties that fall into aspects) is left as it is.  `dry_run` (default) changes nothing and reports."""
    with_interior = n_layers = deepest = 0
    cache: Dict[str, Dict[str, float]] = {}
    for concept, cid in sorted(concept_index.items()):
        crystal = crystals.get(cid)
        if crystal is None:
            continue
        s = standing(crystal)
        if s <= 0.0:
            continue
        found = layers(store, concept, s, profiles=cache)
        if not found:
            continue
        old = (getattr(crystal, "interior", None) or {}).get("layers") or []
        merged = _merge(old, found)
        interior = {"layers": merged, "standing": round(max(s, float((getattr(crystal, "interior", None) or {}).get("standing", 0.0))), 6)}
        interior["depth"] = depth_of(interior)
        with_interior += 1
        n_layers += len(merged)
        deepest = max(deepest, interior["depth"])
        if not dry_run:
            crystal.interior = interior
    return {"crystals_with_interior": with_interior, "layers": n_layers, "deepest": deepest, "dry_run": bool(dry_run)}

# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
aurora_learned_index.py  (FIX-A135)
===================================

One resolution, many consumers.

What she was told is read ONCE from her relations (order edges, kinds, marks,
conditional rules, capability bindings) and kept; every consumer -- the gate's
"can I answer this?", the confluence's knowledge, a question's answer -- reads
the same resolved structure.  It is rebuilt only when what it was built from
changes: the web's learned-version counter moves when an assertion is recorded or
absorbed (``bump``), and relation count moves when relations are added or pruned.

Nothing is stored on the web itself (its saved state is untouched); the cache is
keyed weakly by the web, so it disappears with it.
"""
from __future__ import annotations

import copy
import weakref
from typing import Any, Callable, Dict, Tuple

_VERSIONS: "weakref.WeakKeyDictionary[Any, int]" = weakref.WeakKeyDictionary()
_CACHE: "weakref.WeakKeyDictionary[Any, Tuple[Tuple[int, int], Dict[Any, Any]]]" = weakref.WeakKeyDictionary()
STATS: Dict[str, int] = {"built": 0, "reused": 0}


def bump(web: Any) -> None:
    """What she was told along her relations changed: anything derived from it is stale."""
    try:
        _VERSIONS[web] = _VERSIONS.get(web, 0) + 1
    except TypeError:
        pass


def _stamp(web: Any) -> Tuple[int, int]:
    try:
        return (_VERSIONS.get(web, 0), len(getattr(web, "relations", {}) or {}))
    except TypeError:
        return (0, 0)


def memo(web: Any, key: Any, build: Callable[[], Any], *, fresh: bool = False) -> Any:
    """The resolved ``key`` for this web, built once per state of what she knows.
    ``fresh`` hands back a copy, for results a consumer will change."""
    if web is None:
        return build()
    try:
        slot = _CACHE.get(web)
    except TypeError:
        return build()
    stamp = _stamp(web)
    if slot is None or slot[0] != stamp:
        slot = (stamp, {})
        _CACHE[web] = slot
    store = slot[1]
    if key in store:
        STATS["reused"] += 1
    else:
        STATS["built"] += 1
        store[key] = build()
    return copy.deepcopy(store[key]) if fresh else store[key]

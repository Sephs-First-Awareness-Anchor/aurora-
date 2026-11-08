"""
aurora_turn_persistence.py

Turn-scoped write batching for hot state files.

Measured on a live turn: lexical_grounding_state.json was atomically rewritten
87 times, interaction_memory/{nodes,edges,indexes}.json 10 times each and
understanding_contract_state.json 5 times -- roughly 13 MB of whole-file JSON
rewrites (plus an fsync each) per turn, about half of the turn's wall time.
Every one of those writes is the same object's whole state, so only the last one
in a turn carries information.

A host object opts in with two lines:

    def _persist(...):
        if batch_defer(self):        # inside a turn batch: just mark dirty
            return True
        ...write as before...

and provides a `flush_write_batch()` method that performs the real write.
process_external_user_turn opens a batch on each opted-in system before the turn
and closes it (flushing once) in its `finally`, so an exception mid-turn still
persists whatever was learned.

Design constraints:
  * Only objects that call batch_defer() are affected; nothing else changes.
  * Batches nest (depth counter) -- a re-entrant turn flushes once, at the
    outermost close.
  * Explicit forced saves (e.g. lexical grounding's save()) never defer.
  * Cross-thread: a background thread writing during a turn is deferred to the
    turn's flush, same as the main thread (one shared depth per object).
"""
from __future__ import annotations

import threading
from typing import Any, Iterable, List

_LOCK = threading.RLock()

# systems keys whose objects opt in via batch_defer()/flush_write_batch()
BATCHED_SYSTEM_KEYS = (
    "lexical_grounding",
    "understanding_contract",
    "interaction_processing",  # holds .memory (InteractionMemory)
    "communication_emergence",
    "grammar_engine",          # holds ._lineage (MotifLineage), which owns the write
    # Phone load (2026-11-07): rewritten whole inside turns, not batched.
    "genealogy",               # ConstraintGenealogyLogger.flush_files (20 MB abilities, read + write)
    "lineage_emergence_journal",  # LiveLineageJournal.save (~9 MB)
)

# systems key -> attribute holding the object that actually owns the write
_TARGET_ATTR = {
    "interaction_processing": "memory",
    "grammar_engine": "_lineage",
}


def batch_defer(obj: Any) -> bool:
    """Call at the top of a hot write. True => the write was deferred."""
    with _LOCK:
        if int(getattr(obj, "_wb_depth", 0) or 0) > 0:
            obj._wb_pending = True
            return True
    return False


def _resolve_targets(systems: Any) -> List[Any]:
    out: List[Any] = []
    if not isinstance(systems, dict):
        return out
    for key in BATCHED_SYSTEM_KEYS:
        obj = systems.get(key)
        if obj is None:
            continue
        attr = _TARGET_ATTR.get(key)
        if attr:
            obj = getattr(obj, attr, None)
        if obj is not None and hasattr(obj, "flush_write_batch"):
            out.append(obj)
    return out


# Turn-scoped caches (Sunni, 2026-11-08: a read should change her once, not be
# retained and re-applied).  Registered caches are emptied when the outermost
# turn batch opens, so anything derived from "this turn's text" is computed
# once per turn and never carried into the next.
_TURN_CACHES: List[dict] = []
_TURN_DEPTH = 0


def turn_scoped_cache() -> dict:
    cache: dict = {}
    with _LOCK:
        _TURN_CACHES.append(cache)
    return cache


def begin_write_batch(systems: Any) -> List[Any]:
    """Open a batch on every opted-in system; returns the list to close later."""
    global _TURN_DEPTH
    targets = _resolve_targets(systems)
    with _LOCK:
        if _TURN_DEPTH == 0:
            for cache in _TURN_CACHES:
                cache.clear()
        _TURN_DEPTH += 1
        for obj in targets:
            obj._wb_depth = int(getattr(obj, "_wb_depth", 0) or 0) + 1
    return targets


# Write-behind across turns (phone load, 2026-11-08).  Flushing once per turn
# still rewrote her whole permanent state -- 20 MB genealogy, grammar,
# lineage journal, lexical store -- after EVERY turn (~2.5 s a turn, growing
# as she learns).  Now a deferred object is written when it was last written
# at least WRITE_BEHIND_S ago; otherwise it stays pending and is written by
# the next due turn end, by flush_due() (the app's idle heartbeat, under the
# field lock), or by flush_all() at shutdown.  Nothing is dropped: the newest
# in-memory state is what gets written.  Set AURORA_WRITE_BEHIND_S=0 to write
# at every turn end as before.
import atexit
import os
import time

WRITE_BEHIND_S = float(os.environ.get("AURORA_WRITE_BEHIND_S", "30") or 0.0)
_PENDING: dict = {}            # id(obj) -> obj with a deferred write
_LAST_FLUSH: dict = {}         # id(obj) -> time of its last real write


def _flush_one(obj: Any) -> None:
    with _LOCK:
        if int(getattr(obj, "_wb_depth", 0) or 0) > 0 or not getattr(obj, "_wb_pending", False):
            return
        obj._wb_pending = False
        _PENDING.pop(id(obj), None)
    try:
        obj.flush_write_batch()
        _LAST_FLUSH[id(obj)] = time.time()
    except Exception:
        with _LOCK:
            obj._wb_pending = True
            _PENDING[id(obj)] = obj


def flush_due(*, force: bool = False) -> int:
    """Write every pending object whose window has passed (all, with force).
    Call only from a thread that holds the field lock (or at shutdown)."""
    now = time.time()
    with _LOCK:
        due = [obj for key, obj in list(_PENDING.items())
               if force or now - _LAST_FLUSH.get(key, 0.0) >= WRITE_BEHIND_S]
    for obj in due:
        _flush_one(obj)
    return len(due)


def flush_all() -> int:
    return flush_due(force=True)


atexit.register(flush_all)


def any_due() -> bool:
    now = time.time()
    with _LOCK:
        return any(now - _LAST_FLUSH.get(key, 0.0) >= WRITE_BEHIND_S for key in _PENDING)


def pending_count() -> int:
    with _LOCK:
        return len(_PENDING)


def end_write_batch(targets: Iterable[Any]) -> None:
    """Close the batch.  An object that deferred writes is written now if its
    write-behind window has passed, otherwise left pending (see above)."""
    global _TURN_DEPTH
    with _LOCK:
        _TURN_DEPTH = max(0, _TURN_DEPTH - 1)
    now = time.time()
    for obj in list(targets or []):
        flush = False
        with _LOCK:
            depth = max(0, int(getattr(obj, "_wb_depth", 0) or 0) - 1)
            obj._wb_depth = depth
            if depth == 0 and getattr(obj, "_wb_pending", False):
                if now - _LAST_FLUSH.get(id(obj), 0.0) >= WRITE_BEHIND_S:
                    flush = True
                else:
                    _PENDING[id(obj)] = obj
        if flush:
            _flush_one(obj)

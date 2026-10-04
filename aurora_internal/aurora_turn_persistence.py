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


def begin_write_batch(systems: Any) -> List[Any]:
    """Open a batch on every opted-in system; returns the list to close later."""
    targets = _resolve_targets(systems)
    with _LOCK:
        for obj in targets:
            obj._wb_depth = int(getattr(obj, "_wb_depth", 0) or 0) + 1
    return targets


def end_write_batch(targets: Iterable[Any]) -> None:
    """Close the batch; flush each object that deferred at least one write."""
    for obj in list(targets or []):
        flush = False
        with _LOCK:
            depth = max(0, int(getattr(obj, "_wb_depth", 0) or 0) - 1)
            obj._wb_depth = depth
            if depth == 0 and getattr(obj, "_wb_pending", False):
                obj._wb_pending = False
                flush = True
        if flush:
            try:
                obj.flush_write_batch()
            except Exception:
                # Never let persistence break a turn's cleanup; the next turn's
                # first write (or shutdown) will persist current state anyway.
                with _LOCK:
                    obj._wb_pending = True

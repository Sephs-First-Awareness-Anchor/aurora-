"""
Directive PS1.2 -- No-silent-reversion audit logging.

Storage sibling of the campaign's existing silent-fallback rule: any
restoration path that drops or overrides persisted data must log
exactly what was discarded, not swallow it in a bare except. One
shared, tiny module so every fixed store (OETSPersistence,
LexicalMemory, ProvisionalStore, DimensionalSystems) writes to the
same audit trail in the same shape, rather than inventing its own
ad hoc logging per store.

Fail-quiet by design (matching every other observer/logger this
campaign has built): a broken audit write must never block or alter
the restoration decision itself, only its own record of it.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
import json
import os
import time


def log_reversion(state_dir, store, discarded, kept, reason, extra=None):
    """Append one audit record when a restoration path chooses one
    persisted candidate over another (or over incoming newer data).

    store: short store name, e.g. "OETSPersistence".
    discarded: dict describing what was NOT used -- at minimum a
        `source` (which candidate/file) and whatever identifies its
        generation (timestamp, count, etc).
    kept: dict describing what WAS used, same shape.
    reason: short human-readable arbitration reason, e.g.
        "kept has newer timestamp" or "kept declared canonical,
        discarded is legacy fallback".
    extra: optional dict of additional context (counts, keys, etc).
    """
    try:
        state_dir = str(state_dir or "aurora_state")
        os.makedirs(state_dir, exist_ok=True)
        record = {
            "store": str(store),
            "discarded": discarded or {},
            "kept": kept or {},
            "reason": str(reason or ""),
            "timestamp": time.time(),
        }
        if extra:
            record["extra"] = extra
        path = os.path.join(state_dir, "persistence_audit_log.jsonl")
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        return True
    except Exception:
        return False

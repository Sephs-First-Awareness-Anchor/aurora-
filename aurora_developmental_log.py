#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Developmental timeline log + EEPR feed.

Keeps a timestamped running log of Aurora's developmental metrics
(genealogy abilities/links, DPS crystals, warp recognition, relation
reinforcement, boundary/exclusion, consequence records, wisdom shards) and
feeds each snapshot back into her experiential wisdom store -- the live EEPR
ingestion point (ExpressionEcology.WisdomStore, the same store the simulation
shard bridge feeds) -- as a WisdomShard.

So her own development is not a dashboard number: it becomes experiential
pressure that biases expression. Improving development lifts the "i_is" tone
bias toward warmth/openness; stalling nudges it toward caution. If a DCE/EEPR
regulator with ingest_shard() is wired, the same shard is forwarded to it too.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional

_LOG_NAME = "developmental_timeline.jsonl"
_MAX_LINES = 2000
_MIN_INTERVAL_S = 45.0   # throttle so daemon + turn calls don't double-log
_last_record_ts: float = 0.0


def _safe_len(obj: Any, attr: str) -> int:
    try:
        return len(getattr(obj, attr, {}) or {})
    except Exception:
        return 0


def snapshot_developmental_state(systems: Dict[str, Any]) -> Dict[str, Any]:
    """Gather a timestamped developmental-metrics snapshot from live systems."""
    snap: Dict[str, Any] = {"ts": round(time.time(), 3)}
    if not isinstance(systems, dict):
        return snap

    gen = systems.get("genealogy")
    snap["abilities"] = _safe_len(gen, "abilities")
    snap["genealogy_links"] = _safe_len(gen, "links")

    try:
        dps = getattr(systems.get("dimensional"), "dps", None)
        snap["crystals"] = len(getattr(dps, "crystals", {}) or {})
    except Exception:
        snap["crystals"] = 0

    try:
        from aurora_warp_protocol import get_warp_field
        wf = get_warp_field()
        snap["warp_demands"] = int(getattr(wf, "_demand_count", 0) or 0)
        snap["warp_anomalies"] = len(getattr(wf, "_anomaly_ledger", []) or [])
    except Exception:
        pass

    lf = systems.get("language_field")
    try:
        lsa = getattr(lf, "_lsa", {}) or {}
        snap["lsa_paths"] = len(lsa)
        snap["lsa_reinforced"] = sum(1 for e in lsa.values() if getattr(e, "use_count", 0) >= 1)
        snap["lsa_excludes"] = sum(1 for e in lsa.values() if getattr(e, "excludes", None))
        snap["lsa_consequence"] = sum(1 for e in lsa.values() if getattr(e, "consequence", None))
    except Exception:
        pass

    try:
        eco = getattr(systems.get("perception"), "ecology", None)
        snap["wisdom_shards"] = len(getattr(getattr(eco, "wisdom", None), "shards", {}) or {})
    except Exception:
        pass

    # Behavioral-maturation counters: how often she held grounding internally
    # instead of leaking it (anchor discipline), and how often she sought the base
    # meaning of a gap on first contact (active seeking). Real changes in conduct,
    # tracked as growth alongside the structural metrics.
    snap["anchor_suppressions"] = int(systems.get("_anchor_suppressions", 0) or 0)
    snap["gaps_sought"] = int(systems.get("_base_meanings_sought", 0) or 0)

    return snap


def _developmental_index(snap: Optional[Dict[str, Any]]) -> float:
    if not snap:
        return 0.0
    return float(
        snap.get("abilities", 0) + snap.get("genealogy_links", 0)
        + snap.get("crystals", 0) + snap.get("lsa_reinforced", 0)
        + snap.get("lsa_excludes", 0) + snap.get("wisdom_shards", 0)
        + snap.get("gaps_sought", 0)   # actively reaching for the unknown is growth
    )


def _read_last_snapshot(path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for ln in reversed(fh.readlines()):
                ln = ln.strip()
                if ln:
                    return json.loads(ln)
    except Exception:
        pass
    return None


def _append_capped(path: str, entry: Dict[str, Any]) -> int:
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        lines = []
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fh:
                lines = fh.readlines()
        lines.append(json.dumps(entry, default=str) + "\n")
        if len(lines) > _MAX_LINES:
            lines = lines[-_MAX_LINES:]
        with open(path, "w", encoding="utf-8") as fh:
            fh.writelines(lines)
        return len(lines)
    except Exception:
        return 0


def _clamp(v: float, lo: float = -0.2, hi: float = 0.2) -> float:
    return max(lo, min(hi, v))


def _feed_eepr(systems: Dict[str, Any], snap: Dict[str, Any],
               delta: float, generation: int) -> bool:
    """Feed the snapshot into the live EEPR ingestion (WisdomStore) as a
    WisdomShard, and to a DCE/EEPR regulator's ingest_shard() if one is wired."""
    try:
        from aurora_expression_perception import WisdomShard
        store = getattr(getattr(systems.get("perception"), "ecology", None), "wisdom", None)
        if store is None or not hasattr(store, "add"):
            return False
        shard = WisdomShard(
            shard_id=f"dev_{int(snap.get('ts', time.time()) * 1000)}",
            i_state="i_is",
            # Improving development -> slight warmth/openness; stalling -> caution.
            tone_bias=_clamp(delta * 0.02),
            # Sharper boundaries -> slightly more structure.
            structure_bias=_clamp(float(snap.get("lsa_excludes", 0)) * 0.005),
            # Developmental health as a bounded growth-presence signal.
            fitness_at_death=max(0.0, min(1.0, _developmental_index(snap) / 1000.0)),
            cause_of_death="developmental_snapshot",
            generation=int(generation),
        )
        store.add(shard)
        # Future-proof: forward to a DCE/EEPR regulator if one exposes ingest_shard.
        for key in ("dce", "dce_assembly", "eepr"):
            obj = systems.get(key)
            eepr = getattr(obj, "eepr", obj) if obj is not None else None
            if eepr is not None and hasattr(eepr, "ingest_shard"):
                try:
                    eepr.ingest_shard(shard)
                except Exception:
                    pass
                break
        return True
    except Exception:
        return False


def record_developmental_event(systems: Dict[str, Any], event: str,
                               detail: str = "", *, once: bool = True) -> bool:
    """Log a discrete developmental EVENT -- a real change in how she behaves --
    into the same timeline as the metric snapshots, and feed it to EEPR as a
    milestone shard.

    Snapshots record continuous metrics; an event marks a *transition* (e.g.
    anchor grounding coming online, or active seeking engaging). It is logged as
    i_did -- an enacted change on the A-axis -- so it becomes real experiential
    pressure, not just a dashboard line. With once=True (default) the same event
    is recorded only once per process, so a milestone marks the moment it first
    became true.
    """
    if not isinstance(systems, dict):
        return False
    if once:
        logged = systems.setdefault("_dev_events_logged", set())
        if not isinstance(logged, set):
            logged = set(logged or [])
            systems["_dev_events_logged"] = logged
        if event in logged:
            return False
        logged.add(event)

    state_dir = str(systems.get("state_dir") or "aurora_state")
    path = os.path.join(state_dir, _LOG_NAME)
    entry = {
        "ts": round(time.time(), 3),
        "kind": "developmental_event",
        "event": str(event or "")[:80],
        "detail": str(detail or "")[:200],
    }
    generation = _append_capped(path, entry)

    # Milestone shard: an enacted change biases expression toward openness.
    try:
        from aurora_expression_perception import WisdomShard
        store = getattr(getattr(systems.get("perception"), "ecology", None), "wisdom", None)
        if store is not None and hasattr(store, "add"):
            store.add(WisdomShard(
                shard_id=f"devevt_{int(time.time() * 1000)}",
                i_state="i_did",   # A-axis: she DID change how she behaves
                tone_bias=0.03,
                structure_bias=0.02,
                fitness_at_death=0.6,
                cause_of_death=f"developmental_event:{event}"[:64],
                generation=int(generation),
            ))
    except Exception:
        pass
    return True


def record_developmental_snapshot(systems: Dict[str, Any], *,
                                  force: bool = False) -> Optional[Dict[str, Any]]:
    """Snapshot developmental state, append to the running timeline log, and feed
    it into the EEPR. Throttled to once per _MIN_INTERVAL_S unless force=True.
    Returns the snapshot (with dev_index/dev_delta/fed_eepr) or None if skipped.
    """
    global _last_record_ts
    if not isinstance(systems, dict):
        return None
    now = time.time()
    if not force and (now - _last_record_ts) < _MIN_INTERVAL_S:
        return None

    state_dir = str(systems.get("state_dir") or "aurora_state")
    path = os.path.join(state_dir, _LOG_NAME)

    snap = snapshot_developmental_state(systems)
    prev = _read_last_snapshot(path)
    delta = _developmental_index(snap) - _developmental_index(prev)
    snap["dev_index"] = round(_developmental_index(snap), 2)
    snap["dev_delta"] = round(delta, 2)

    generation = _append_capped(path, snap)
    snap["fed_eepr"] = _feed_eepr(systems, snap, delta, generation)
    _last_record_ts = now
    return snap


if __name__ == "__main__":  # pragma: no cover
    print("aurora_developmental_log: developmental timeline + EEPR feed module")

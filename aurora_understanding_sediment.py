"""
aurora_understanding_sediment.py
=================================
Understanding as deposition — the runtime sediment overlay.

Physics
-------
The compiled noncomp manifold (125 JSONs, 25 channels, 625 interaction
slots) is bedrock: canonical, read-only, never mutated at runtime.
This module adds the stratum that was missing above it — a persisted
overlay of accountability-weight *deltas* that accrue wherever meaning
was actually understood.

The loop it closes (the snowball):

    understood expression
        → deposit(+Δ) at the slot it landed in
        → slot neighborhood densifies
        → ManifoldFieldMap origin region shifts sparse → mid → dense
        → _reconcile() origin bonus (0.05 / 0.20) lifts the next
          nearby expression toward UNDERSTANDING_THRESHOLD
        → which deposits again.

Density begets density — but honestly:

  * Deposits are capped at +0.25 per slot. A truly sparse slot
    (bedrock ≤ 0.35) can climb into mid territory on lived
    understanding alone, but can never manufacture dense (≥ 0.70)
    without canonical bedrock underneath it. Repetition cannot
    counterfeit accountability.
  * Deposits decay with a half-life (default 7 days), applied
    lazily at read. Unused density erodes; if everything stayed
    dense, nothing would be.

Also carried in this stratum: the persisted Worth ledger, so
WorthTrajectory survives across sessions instead of resetting every
key to UNKNOWN (a 0.7× multiplier tax on all first-touch meaning).

Boundary rules
--------------
  * NEVER writes to the compiled noncomp JSONs or the manifold
    directory. Overlay state lives in aurora_state/.
  * Consumers read through delta() / adjusted_weight() only.
  * Slot keys mirror exactly what ReflexiveInterpreter.interpret()
    reads: ManifoldFieldMap.accountability_at(c, d, c, "OPERATOR").

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import json
import math
import os
import time
import threading
from collections import deque
from typing import Any, Deque, Dict, List, Optional, Tuple

# ── Constants ─────────────────────────────────────────────────────────────────

OVERLAY_FILENAME = "understanding_sediment_overlay.json"
WORTH_LEDGER_FILENAME = "understanding_worth_ledger.json"

DEPOSIT_RATE = 0.08          # Δ per understood expression, scaled by margin
DEPOSIT_CAP = 0.25           # max accumulated Δ per slot (see module docstring)
DECAY_HALF_LIFE_S = 7 * 24 * 3600.0   # 7-day half-life, lazy at read
MIN_LIVE_DELTA = 0.005       # below this, a decayed entry is pruned
WORTH_WINDOW = 8             # must match WorthHistory(window=8) in the interpreter

_LN2 = math.log(2.0)


def _default_state_dir() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "aurora_state")


def slot_key(constraint: str, dimension: str) -> str:
    """
    Canonical overlay slot key. Mirrors the exact read performed in
    ReflexiveInterpreter.interpret():

        fmap.accountability_at(match.constraint, match.dimension,
                               match.constraint, "OPERATOR")

    so the key is row (c, d) × column (c, OPERATOR).
    """
    return f"{constraint}:{dimension}|{constraint}:OPERATOR"


# ── Sediment overlay ──────────────────────────────────────────────────────────

class UnderstandingSedimentOverlay:
    """
    Persisted runtime accountability-weight deltas, keyed by
    (nc_name or axis fallback) → slot_key.

    Storage schema (JSON):
        {
          "version": 1,
          "entries": {
            "<field_key>": {
              "<slot_key>": {
                "delta":       float,   # value as of last_touch
                "last_touch":  float,   # unix seconds
                "deposits":    int,     # lifetime deposit count
                "last_worth":  float    # worth score of most recent deposit
              }, ...
            }, ...
          }
        }
    """

    def __init__(self, state_dir: Optional[str] = None,
                 half_life_s: float = DECAY_HALF_LIFE_S) -> None:
        self._state_dir = str(state_dir or _default_state_dir())
        self._path = os.path.join(self._state_dir, OVERLAY_FILENAME)
        self._half_life_s = max(1.0, float(half_life_s))
        self._lock = threading.Lock()
        self._entries: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._dirty = False
        self._load()

    # ── persistence ──

    def _load(self) -> None:
        try:
            if os.path.exists(self._path):
                with open(self._path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                entries = raw.get("entries", {}) if isinstance(raw, dict) else {}
                if isinstance(entries, dict):
                    self._entries = {
                        str(fk): {
                            str(sk): dict(sv) for sk, sv in dict(fv or {}).items()
                            if isinstance(sv, dict)
                        }
                        for fk, fv in entries.items()
                        if isinstance(fv, dict)
                    }
        except Exception:
            # Corrupt overlay never blocks interpretation; start clean.
            self._entries = {}

    def save(self) -> bool:
        with self._lock:
            if not self._dirty:
                return False
            try:
                os.makedirs(self._state_dir, exist_ok=True)
                tmp = self._path + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump({"version": 1, "entries": self._entries}, f, indent=1)
                os.replace(tmp, self._path)
                self._dirty = False
                return True
            except Exception:
                return False

    # ── decay physics ──

    def _decayed(self, rec: Dict[str, Any], now: float) -> float:
        try:
            delta = float(rec.get("delta", 0.0) or 0.0)
            last = float(rec.get("last_touch", now) or now)
        except Exception:
            return 0.0
        age = max(0.0, now - last)
        return delta * math.exp(-_LN2 * age / self._half_life_s)

    # ── read path ──

    def delta(self, field_key: Optional[str], slot: str,
              now: Optional[float] = None) -> float:
        """Live (decay-applied) delta for a slot. 0.0 if none."""
        if not field_key:
            return 0.0
        now = now if now is not None else time.time()
        with self._lock:
            rec = (self._entries.get(field_key) or {}).get(slot)
            if not rec:
                return 0.0
            live = self._decayed(rec, now)
            if live < MIN_LIVE_DELTA:
                # Erosion: prune fully-decayed sediment.
                try:
                    del self._entries[field_key][slot]
                    if not self._entries[field_key]:
                        del self._entries[field_key]
                    self._dirty = True
                except Exception:
                    pass
                return 0.0
            return live

    def adjusted_weight(self, base_weight: float, field_key: Optional[str],
                        slot: str) -> float:
        """Bedrock weight + live sediment, clamped to [0, 1]."""
        return max(0.0, min(1.0, float(base_weight) + self.delta(field_key, slot)))

    # ── write path ──

    def deposit(self, field_key: Optional[str], slot: str, worth: float,
                threshold: float = 0.55, now: Optional[float] = None) -> float:
        """
        Deposit sediment for an understood expression. Magnitude scales
        with the margin by which worth cleared the understanding
        threshold — barely-understood meaning lays thin strata,
        strongly-understood meaning compacts fast. Returns the new live
        delta for the slot.
        """
        if not field_key:
            return 0.0
        now = now if now is not None else time.time()
        margin = max(0.0, float(worth) - float(threshold))
        gain = DEPOSIT_RATE * (0.5 + margin)   # floor so every understanding counts
        with self._lock:
            fk = self._entries.setdefault(field_key, {})
            rec = fk.get(slot)
            live = self._decayed(rec, now) if rec else 0.0
            new_delta = min(DEPOSIT_CAP, live + gain)
            fk[slot] = {
                "delta": round(new_delta, 6),
                "last_touch": now,
                "deposits": int((rec or {}).get("deposits", 0) or 0) + 1,
                "last_worth": round(float(worth), 4),
            }
            self._dirty = True
        return new_delta

    # ── introspection ──

    def stats(self) -> Dict[str, Any]:
        now = time.time()
        with self._lock:
            fields = len(self._entries)
            slots = sum(len(v) for v in self._entries.values())
            live_total = sum(
                self._decayed(rec, now)
                for fv in self._entries.values() for rec in fv.values()
            )
            deposits = sum(
                int(rec.get("deposits", 0) or 0)
                for fv in self._entries.values() for rec in fv.values()
            )
        return {
            "fields": fields,
            "slots": slots,
            "lifetime_deposits": deposits,
            "live_delta_total": round(live_total, 4),
            "half_life_days": round(self._half_life_s / 86400.0, 2),
            "path": self._path,
        }


# ── Persistent Worth ledger ───────────────────────────────────────────────────

class PersistentWorthLedger:
    """
    Persists the interpreter's per-key worth windows so WorthTrajectory
    survives sessions. Without this, every key restarts at UNKNOWN
    (0.7× trajectory multiplier in _reconcile) on every boot.

    Storage schema (JSON):
        { "version": 1, "windows": { "<key>": [float, ...] } }
    """

    def __init__(self, state_dir: Optional[str] = None,
                 window: int = WORTH_WINDOW) -> None:
        self._state_dir = str(state_dir or _default_state_dir())
        self._path = os.path.join(self._state_dir, WORTH_LEDGER_FILENAME)
        self._window = int(window)
        self._lock = threading.Lock()
        self._windows: Dict[str, Deque[float]] = {}
        self._dirty = False
        self._load()

    def _load(self) -> None:
        try:
            if os.path.exists(self._path):
                with open(self._path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                windows = raw.get("windows", {}) if isinstance(raw, dict) else {}
                for key, scores in dict(windows or {}).items():
                    if isinstance(scores, list):
                        self._windows[str(key)] = deque(
                            (float(s) for s in scores[-self._window:]),
                            maxlen=self._window,
                        )
        except Exception:
            self._windows = {}

    def scores_for(self, key: str) -> List[float]:
        with self._lock:
            return list(self._windows.get(key, ()))

    def record(self, key: str, score: float) -> None:
        with self._lock:
            win = self._windows.setdefault(key, deque(maxlen=self._window))
            win.append(float(score))
            self._dirty = True

    def save(self) -> bool:
        with self._lock:
            if not self._dirty:
                return False
            try:
                os.makedirs(self._state_dir, exist_ok=True)
                tmp = self._path + ".tmp"
                payload = {
                    "version": 1,
                    "windows": {k: [round(s, 6) for s in v]
                                for k, v in self._windows.items()},
                }
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=1)
                os.replace(tmp, self._path)
                self._dirty = False
                return True
            except Exception:
                return False

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "keys": len(self._windows),
                "window": self._window,
                "path": self._path,
            }


# ── Recall → confidence coupling ──────────────────────────────────────────────

RECALL_BOOST_CAP = 0.15      # max confidence lift from resonant memory
RECALL_MIN_SCORE = 0.35      # mirrors SediMemory recall_semantic default floor


def recall_confidence_boost(sedimemory: Any, expression: str,
                            constraint: str,
                            max_results: int = 4) -> float:
    """
    Memory lowering the energy cost of re-understanding.

    Queries SediMemoryColumn.recall_semantic() (duck-typed — any object
    exposing that method) for fragments resonant with the current
    expression, filtered to the matched constraint axis. Returns a
    bounded confidence boost that feeds _worth_score's
    (0.7 + 0.3·conf) term. Never raises; absence of memory is 0.0.
    """
    if sedimemory is None or not hasattr(sedimemory, "recall_semantic"):
        return 0.0
    try:
        results = list(sedimemory.recall_semantic(
            query_text=str(expression or ""),
            max_results=int(max_results),
            axis_filter=(constraint,) if constraint else None,
            min_score=RECALL_MIN_SCORE,
        ) or [])
    except Exception:
        return 0.0
    if not results:
        return 0.0
    try:
        top = max(float(r.get("score", 0.0) or 0.0) for r in results)
    except Exception:
        return 0.0
    if top <= RECALL_MIN_SCORE:
        return 0.0
    # Linear ramp from the recall floor to full score → capped boost.
    span = max(1e-9, 1.0 - RECALL_MIN_SCORE)
    return round(min(RECALL_BOOST_CAP,
                     RECALL_BOOST_CAP * (top - RECALL_MIN_SCORE) / span), 4)


# ── Main (self-check) ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import tempfile

    print("=" * 68)
    print("AURORA UNDERSTANDING SEDIMENT  v1")
    print("understanding as deposition — bedrock stays canonical")
    print("Authors: Sunni (Sir) Morningstar & Cael Devo")
    print("=" * 68)

    with tempfile.TemporaryDirectory() as td:
        ov = UnderstandingSedimentOverlay(state_dir=td)
        sk = slot_key("B", "OPERATOR")
        fk = "NC_Recognition_of_Boundary"

        print("\n--- Deposition & cap ---")
        for i in range(12):
            d = ov.deposit(fk, sk, worth=0.72)
        print(f"  after 12 deposits @ worth 0.72: delta={d:.4f} (cap {DEPOSIT_CAP})")
        base = 0.30  # sparse bedrock
        adj = ov.adjusted_weight(base, fk, sk)
        print(f"  sparse bedrock {base:.2f} → adjusted {adj:.4f} "
              f"(mid territory, cannot counterfeit dense)")

        print("\n--- Decay (simulated 7 days) ---")
        past = time.time() - DECAY_HALF_LIFE_S
        with ov._lock:
            ov._entries[fk][sk]["last_touch"] = past
        print(f"  after one half-life: delta={ov.delta(fk, sk):.4f}")

        print("\n--- Persistence round-trip ---")
        ov.save()
        ov2 = UnderstandingSedimentOverlay(state_dir=td)
        print(f"  reloaded delta={ov2.delta(fk, sk):.4f}")

        print("\n--- Worth ledger round-trip ---")
        wl = PersistentWorthLedger(state_dir=td)
        for s in (0.51, 0.58, 0.63):
            wl.record("B:OPERATOR", s)
        wl.save()
        wl2 = PersistentWorthLedger(state_dir=td)
        print(f"  restored window: {wl2.scores_for('B:OPERATOR')} "
              f"(trajectory will read RISING, not UNKNOWN)")

        print("\n--- Stats ---")
        print(f"  {ov.stats()}")
    print("\nDone.")

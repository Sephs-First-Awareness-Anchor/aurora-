"""
aurora_pressure_adapter.py
─────────────────────────────────────────────────────────────────────────────
Adaptive evolution parameters — makes the selection mechanism evolve itself.

The problem with fixed thresholds:
  - If threshold is too LOW:  surfaces fire constantly, little real relief,
    pressure never drops, evolution keeps producing surfaces for the same axes
  - If threshold is too HIGH: surfaces never fire, no evidence feeds back,
    pressure builds indefinitely without evolution responding

This module observes the relationship between surface firing and actual
pressure change, then adapts:
  - SurfaceDispatcher.threshold (per-run, not persisted across boots)
  - Per-surface effective cooldown (surfaces that didn't help cool down longer)
  - Evolver bias weight recommendations (written to aurora_state/adapter_hints.json
    so CodeAutoEvolver can optionally read them)

Adaptation rules:
  1. Axis relief efficiency: if an axis fires frequently but its pressure stays
     high → raise threshold for that axis (surfaces aren't helping enough)
  2. Surface effectiveness: if a surface fired N times and average pressure
     delta was near zero → increase its effective cooldown
  3. Dormant axes: if an axis's pressure is chronically high but its surfaces
     never fire → lower the threshold temporarily to unblock them
  4. Saturated axes: if an axis pressure is near zero but still firing →
     raise threshold (no real need)

Storage: aurora_state/adapter_hints.json
  {
    "threshold_deltas": {"X": +0.02, "N": -0.03, ...},
    "surface_cooldown_multipliers": {"surface_name": 1.5, ...},
    "evolver_bias_hints": {"energy": +0.1, "boundary": -0.05, ...},
    "last_updated": 1234567890.0
  }
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import json
import os
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

_AXES = ("X", "T", "N", "B", "A")
_PRESSURE_LOG_REL  = "aurora_state/surface_pressure_log.jsonl"
_ADAPTER_HINTS_REL = "aurora_state/adapter_hints.json"

# How much to move threshold per adaptation step
THRESHOLD_STEP     = 0.02
# Absolute bounds on threshold
THRESHOLD_MIN      = 0.05
THRESHOLD_MAX      = 0.50
# Cooldown multiplier bounds
COOLDOWN_MULT_MIN  = 0.5
COOLDOWN_MULT_MAX  = 4.0
# Minimum log entries to trust an adaptation decision
MIN_OBSERVATIONS   = 10
# How many recent log entries to use for adaptation
ADAPT_WINDOW       = 200
# Per-axis EMA alpha for smoothing pressure statistics across adapt() calls.
# Slow axes (A, B) have small alpha so sparse signal persists between windows;
# fast axes (X, N) use larger alpha to track rapid changes.
_AXIS_PRESSURE_EMA_ALPHA: Dict[str, float] = {
    "X": 0.30, "T": 0.20, "N": 0.15, "B": 0.08, "A": 0.04
}


class PressureParameterAdapter:
    """
    Observes surface firing patterns and adapts evolution parameters.

    Call adapt(dispatcher) after each batch of ticks to allow the dispatcher
    to tune itself. Writes hints for the evolver to aurora_state/adapter_hints.json.
    """

    def __init__(self, repo_root: str):
        self.repo_root   = os.path.abspath(repo_root)
        self._hints: Dict[str, Any] = self._load_hints()

    # ── public ────────────────────────────────────────────────────────────────

    def adapt(self, dispatcher: Any) -> Dict[str, Any]:
        """
        Read recent pressure log, compute adaptation signals, apply to dispatcher.

        dispatcher: SurfaceDispatcher instance (from aurora_surface_dispatcher)
        Returns a summary of what was adjusted.
        """
        log = self._load_log()
        if len(log) < MIN_OBSERVATIONS:
            return {"adapted": False, "reason": "insufficient_log_data", "entries": len(log)}

        recent = log[-ADAPT_WINDOW:]
        axis_stats   = self._axis_stats(recent)
        surface_stats = self._surface_stats(recent)

        threshold_deltas: Dict[str, float] = {}
        cooldown_mults:   Dict[str, float] = {}
        bias_hints:       Dict[str, float] = {}

        # ── per-axis threshold adaptation ─────────────────────────────────────
        base_threshold = float(getattr(dispatcher, "threshold", 0.15))
        for ax in _AXES:
            stats = axis_stats.get(ax, {})
            fire_rate   = float(stats.get("fire_rate", 0.0))
            mean_pre    = float(stats.get("mean_pressure_pre", 0.0))
            mean_post   = float(stats.get("mean_pressure_post", mean_pre))
            relief_ratio = float(stats.get("mean_relief", 0.0))

            delta = 0.0

            # fires often, pressure stays high → not working, raise threshold
            if fire_rate > 0.5 and mean_pre > 0.4 and relief_ratio < 0.05:
                delta = +THRESHOLD_STEP

            # fires never (rate < 0.1) but pressure is chronically high → lower threshold
            elif fire_rate < 0.1 and mean_pre > 0.35:
                delta = -THRESHOLD_STEP

            # axis pressure near zero but still firing → saturated, raise threshold
            elif fire_rate > 0.2 and mean_pre < 0.10:
                delta = +THRESHOLD_STEP * 0.5

            # relief is actually working → small reward (lower threshold slightly)
            elif relief_ratio > 0.08 and fire_rate > 0.05:
                delta = -THRESHOLD_STEP * 0.3

            if delta != 0.0:
                threshold_deltas[ax] = round(delta, 4)
                bias_hints[ax.lower()] = round(-delta * 2.0, 4)  # inverse: high threshold → push evolver harder

        # ── per-surface cooldown adaptation ───────────────────────────────────
        for surface_name, stats in surface_stats.items():
            calls    = int(stats.get("call_count", 0))
            avg_rel  = float(stats.get("avg_relief", 0.0))
            if calls < 3:
                continue
            existing_mult = float(self._hints.get("surface_cooldown_multipliers", {}).get(surface_name, 1.0))
            if avg_rel < 0.005:
                # surface barely helps → cool it down more
                new_mult = min(COOLDOWN_MULT_MAX, existing_mult * 1.3)
            elif avg_rel > 0.04:
                # surface is effective → let it fire more freely
                new_mult = max(COOLDOWN_MULT_MIN, existing_mult * 0.85)
            else:
                new_mult = existing_mult
            if abs(new_mult - 1.0) > 0.05:
                cooldown_mults[surface_name] = round(new_mult, 4)

        # ── apply to dispatcher ────────────────────────────────────────────────
        applied: Dict[str, Any] = {}
        if threshold_deltas:
            # apply the median delta to the global threshold
            median_delta = sorted(threshold_deltas.values())[len(threshold_deltas) // 2]
            old_t = float(getattr(dispatcher, "threshold", 0.15))
            new_t = max(THRESHOLD_MIN, min(THRESHOLD_MAX, old_t + median_delta))
            if abs(new_t - old_t) > 0.001:
                dispatcher.threshold = new_t
                applied["threshold"] = {"old": old_t, "new": new_t, "delta": round(median_delta, 4)}

        if cooldown_mults:
            existing_mults = dict(getattr(dispatcher, "_cooldown_multipliers", {}) or {})
            existing_mults.update(cooldown_mults)
            dispatcher._cooldown_multipliers = existing_mults
            applied["cooldown_adjustments"] = len(cooldown_mults)

        # ── persist hints for the evolver ─────────────────────────────────────
        self._hints["threshold_deltas"]           = threshold_deltas
        self._hints["surface_cooldown_multipliers"] = cooldown_mults
        self._hints["evolver_bias_hints"]         = bias_hints
        self._hints["last_updated"]               = float(time.time())
        # EMA-blend new axis stats with persisted values so slow axes (A, B)
        # retain signal across windows even when they fire zero times.
        _old_axis_stats = dict(self._hints.get("axis_stats") or {})
        _ema_axis_stats: Dict[str, Any] = {}
        for ax, s in axis_stats.items():
            _alpha = _AXIS_PRESSURE_EMA_ALPHA.get(ax, 0.20)
            _old_s = _old_axis_stats.get(ax, {})
            _blended: Dict[str, float] = {}
            for k, v in s.items():
                _old_v = float(_old_s.get(k, v))
                _blended[k] = round(_alpha * float(v) + (1.0 - _alpha) * _old_v, 6)
            _ema_axis_stats[ax] = _blended
        self._hints["axis_stats"] = _ema_axis_stats
        self._save_hints(self._hints)

        return {
            "adapted":              True,
            "entries_analyzed":     len(recent),
            "threshold_deltas":     threshold_deltas,
            "cooldown_adjustments": len(cooldown_mults),
            "bias_hints":           bias_hints,
            "applied":              applied,
        }

    def load_bias_hints(self) -> Dict[str, float]:
        """
        Return evolver bias hints dict {constraint_name: weight_delta}.
        CodeAutoEvolver can read this to adjust its selection weights.
        """
        return dict(self._hints.get("evolver_bias_hints", {}) or {})

    def status(self) -> Dict[str, Any]:
        hints = self._load_hints()
        log   = self._load_log()
        return {
            "log_entries":    len(log),
            "last_updated":   hints.get("last_updated", 0.0),
            "threshold_deltas": hints.get("threshold_deltas", {}),
            "cooldown_adjustments": len(hints.get("surface_cooldown_multipliers", {})),
            "bias_hints":     hints.get("evolver_bias_hints", {}),
            "axis_stats":     hints.get("axis_stats", {}),
        }

    # ── analytics ─────────────────────────────────────────────────────────────

    def _entry_axes(self, entry: Dict[str, Any]) -> List[str]:
        axes: List[str] = []
        for candidate in (entry.get("axis"), entry.get("dispatch_axis")):
            ax = str(candidate or "").strip().upper()
            if ax in _AXES and ax not in axes:
                axes.append(ax)
        for raw in entry.get("expected_axes", []) or []:
            ax = str(raw or "").strip().upper()
            if ax in _AXES and ax not in axes:
                axes.append(ax)
        snap = dict(entry.get("pressure_before") or entry.get("axis_pressure") or {})
        for raw in snap.keys():
            ax = str(raw or "").strip().upper()
            if ax in _AXES and ax not in axes:
                axes.append(ax)
        return axes

    def _normalise_axis_pressure(self, payload: Any) -> Dict[str, float]:
        if not isinstance(payload, dict):
            return {}
        out: Dict[str, float] = {}
        for raw_ax, raw_val in payload.items():
            ax = str(raw_ax or "").strip().upper()
            if ax not in _AXES:
                continue
            try:
                out[ax] = float(raw_val or 0.0)
            except Exception:
                out[ax] = 0.0
        return out

    def _axis_stats(self, log: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        """Compute per-axis firing rate, mean pressure before/after, and relief."""
        fire_counts: Dict[str, int]   = defaultdict(int)
        pre_sums:    Dict[str, float] = defaultdict(float)
        post_sums:   Dict[str, float] = defaultdict(float)
        relief_sums: Dict[str, float] = defaultdict(float)
        n = len(log)

        for entry in log:
            axes = self._entry_axes(entry)
            if not axes:
                continue
            pb = self._normalise_axis_pressure(
                entry.get("pressure_before") or entry.get("axis_pressure") or {}
            )
            pa = self._normalise_axis_pressure(
                entry.get("pressure_after") or entry.get("axis_pressure_after") or pb
            )
            for ax in axes:
                fire_counts[ax] += 1
                pre_v = float(pb.get(ax, 0.0) or 0.0)
                post_v = float(pa.get(ax, pre_v) or pre_v)
                pre_sums[ax] += pre_v
                post_sums[ax] += post_v
                relief_sums[ax] += max(0.0, pre_v - post_v)

        result: Dict[str, Dict[str, float]] = {}
        for ax in _AXES:
            fires = fire_counts.get(ax, 0)
            result[ax] = {
                "fire_rate":          round(fires / max(1, n), 6),
                "fire_count":         float(fires),
                "mean_pressure_pre":  round(pre_sums.get(ax, 0.0) / max(1, fires), 6),
                "mean_pressure_post": round(post_sums.get(ax, 0.0) / max(1, fires), 6),
                "mean_relief":        round(relief_sums.get(ax, 0.0) / max(1, fires), 6),
            }
        return result

    def _surface_stats(self, log: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Compute per-surface call count and average relief."""
        call_counts: Dict[str, int] = defaultdict(int)
        relief_sums: Dict[str, float] = defaultdict(float)

        for entry in log:
            name = str(entry.get("surface", entry.get("op_id", "")) or "")
            if not name:
                continue
            axes = self._entry_axes(entry)
            pb = self._normalise_axis_pressure(
                entry.get("pressure_before") or entry.get("axis_pressure") or {}
            )
            pa = self._normalise_axis_pressure(
                entry.get("pressure_after") or entry.get("axis_pressure_after") or pb
            )
            relief = 0.0
            if axes:
                relief_terms = []
                for ax in axes:
                    pre_v = float(pb.get(ax, 0.0) or 0.0)
                    post_v = float(pa.get(ax, pre_v) or pre_v)
                    relief_terms.append(max(0.0, pre_v - post_v))
                if relief_terms:
                    relief = sum(relief_terms) / len(relief_terms)
            call_counts[name] += 1
            relief_sums[name] += relief

        return {
            name: {
                "call_count": n,
                "avg_relief": round(relief_sums[name] / max(1, n), 6),
            }
            for name, n in call_counts.items()
        }

    # ── persistence ───────────────────────────────────────────────────────────

    def _load_log(self) -> List[Dict[str, Any]]:
        path = os.path.join(self.repo_root, _PRESSURE_LOG_REL)
        if not os.path.exists(path):
            return []

        scan_entries = max(ADAPT_WINDOW * 2, MIN_OBSERVATIONS)
        chunk_size = 65536
        raw_lines: List[bytes] = []
        try:
            with open(path, "rb") as fh:
                fh.seek(0, os.SEEK_END)
                pos = fh.tell()
                buf = b""
                while len(raw_lines) < scan_entries and pos > 0:
                    read_sz = min(chunk_size, pos)
                    pos -= read_sz
                    fh.seek(pos)
                    buf = fh.read(read_sz) + buf
                    parts = buf.split(b"\n")
                    buf = parts[0]
                    for part in reversed(parts[1:]):
                        part = part.strip()
                        if part:
                            raw_lines.append(part)
                        if len(raw_lines) >= scan_entries:
                            break
                if buf.strip() and len(raw_lines) < scan_entries:
                    raw_lines.append(buf.strip())
        except Exception:
            return []

        entries: List[Dict[str, Any]] = []
        for raw in reversed(raw_lines[:scan_entries]):
            try:
                payload = json.loads(raw.decode("utf-8"))
            except Exception:
                continue
            if isinstance(payload, dict):
                entries.append(payload)
        return entries

    def _load_hints(self) -> Dict[str, Any]:
        path = os.path.join(self.repo_root, _ADAPTER_HINTS_REL)
        if not os.path.exists(path):
            return {}
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _save_hints(self, hints: Dict[str, Any]) -> None:
        path = os.path.join(self.repo_root, _ADAPTER_HINTS_REL)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(hints, fh, indent=2, sort_keys=True, ensure_ascii=True)
        except Exception:
            pass


if __name__ == "__main__":
    import sys
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )
    adapter = PressureParameterAdapter(root)
    st = adapter.status()
    print(json.dumps(st, indent=2))

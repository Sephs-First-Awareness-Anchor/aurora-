"""
aurora_leverage_relief.py
─────────────────────────────────────────────────────────────────────────────
Leverage Relief Valve — escapes the overhead-dominant stuck state.

THE PROBLEM:
    When the system enters deep overhead-dominant band (band=LOW), the
    genealogy layer hammers X-axis link promotion and fails Gate-5 repeatedly.
    The pressure_adapter only reads surface_pressure_log.jsonl (axis_pressure
    fields are empty), so it computes zero axis stats and writes no bias signal.
    The leverage scalar nudges are capped at 0.063 — too small to break out of
    net=-496 territory. Nobody redirects.

WHAT THIS MODULE DOES:
    1. DETECT: Reads pressure_experiences.jsonl, computes rolling axis ratio
       over the last SCAN_WINDOW entries. If X+T > OVERHEAD_THRESHOLD fraction
       of total axis activity for STUCK_STREAK consecutive scans → STUCK.

    2. REDIRECT: Writes strong evolver_bias_hints into adapter_hints.json
       biasing toward B and A axes (the leverage side), and negative bias on X
       to slow X-axis surface generation.

    3. GATE RELIEF: Writes a genealogy_gate_relief flag into adapter_hints.json
       so the genealogy caller can optionally relax Gate-5 net_benefit threshold
       temporarily, letting some X-axis links promote even at marginal benefit.
       This drains the backlog rather than letting it accumulate indefinitely.

    4. CLEAR: When overhead ratio drops below RELIEF_THRESHOLD (axis distribution
       normalises), clears the redirect and gate relief flag.

    5. LOG: Appends one line per state change to aurora_state/leverage_relief.log

INTEGRATION:
    Call LeverageReliefValve.tick() from the daemon's pressure routing cycle
    (every ~600s alongside route_pressure()).

    The genealogy caller checks adapter_hints["genealogy_gate_relief"] before
    running Gate-5 and can multiply the net_benefit threshold by the provided
    relief_factor (e.g. 0.5 = Gate-5 requires only 50% of normal net benefit).

AUTHORS: Sunni (Sir) Morningstar and Cael Devo
"""

from __future__ import annotations

import json
import os
import time
from collections import deque
from typing import Any, Dict, List, Optional

_STATE_REL  = "aurora_state"
_HINTS_REL  = "aurora_state/adapter_hints.json"
_EXP_REL    = "aurora_state/pressure_experiences.jsonl"
_SURF_REL   = "aurora_state/surface_pressure_log.jsonl"
_LOG_REL    = "aurora_state/leverage_relief.log"
_QUERY_REL  = "aurora_state/query_bias.json"

# ── Thresholds ────────────────────────────────────────────────────────────────
SCAN_WINDOW        = 300    # experiences to scan per tick
OVERHEAD_THRESHOLD = 0.80   # X+T fraction above which we're stuck
STUCK_STREAK       = 2      # consecutive stuck scans before activating relief
RELIEF_THRESHOLD   = 0.60   # X+T fraction below which relief clears
RELIEF_FACTOR      = 0.50   # Gate-5 net_benefit multiplier during relief

# Redirect bias magnitudes written into evolver_bias_hints
REDIRECT_BIAS: Dict[str, float] = {
    "agency":    +0.15,   # A — gentle nudge; let dream training build A primacy organically
    "boundary":  +0.30,   # B — strong redirect; B has good relief payoff
    "energy":    +0.10,   # N — mild nudge toward energy surfaces
    "temporal":  -0.05,   # T — slight reduction
    "existence": -0.15,   # X — reduce X-axis evolution budget
}

# Axis letter → bias key mapping (matches aurora_pressure_adapter.py convention)
_AX_TO_BIAS_KEY = {
    "A": "agency", "B": "boundary", "N": "energy",
    "T": "temporal", "X": "existence",
}

# Budget weights for overhead/leverage ratio (from aurora_noncomp_registry.py)
_AX_BUDGET = {"X": 1.0, "T": 5.0, "N": 6.0, "B": 18.0, "A": 50.0}


class LeverageReliefValve:
    """
    Stateful valve that detects overhead-stuck state and redirects evolver budget.
    """

    def __init__(self, repo_root: str):
        self.repo_root    = os.path.abspath(repo_root)
        self._stuck_count = 0
        self._active      = False
        self._last_net    = 0.0

    # ── public ────────────────────────────────────────────────────────────────

    def tick(self) -> Dict[str, Any]:
        """
        Run one relief cycle. Call from daemon every ~600s alongside route_pressure().
        Returns a status dict describing what was done.
        """
        axis_counts = self._scan_recent_experiences()
        ratio       = self._overhead_ratio(axis_counts)
        net         = self._net_leverage(axis_counts)
        route       = self._route_snapshot()
        dominant    = str(route.get("dominant_type", "") or "")
        code_gap    = float((route.get("pressure_scores") or {}).get("code_gap", 0.0) or 0.0)
        self._last_net = net

        if ratio > OVERHEAD_THRESHOLD:
            self._stuck_count = min(self._stuck_count + 1, STUCK_STREAK + 5)
        else:
            self._stuck_count = max(0, self._stuck_count - 1)

        was_active = self._active
        structural_pressure = (not dominant) or dominant == "code_gap" or code_gap >= 0.20
        should_activate = self._stuck_count >= STUCK_STREAK and structural_pressure
        should_clear = self._active and (
            ratio < RELIEF_THRESHOLD
            or (dominant and dominant != "code_gap" and code_gap < 0.15)
        )

        if should_clear:
            self._active = False
            self._clear_redirect()
            self._log(f"CLEARED  ratio={ratio:.3f} net={net:+.1f} streak={self._stuck_count}")
            return {"action": "cleared", "ratio": ratio, "net": net, "dominant": dominant, "code_gap": code_gap}

        if should_activate:
            self._active = True
            self._write_redirect()
            if not was_active:
                self._log(
                    f"ACTIVATED  ratio={ratio:.3f} net={net:+.1f} streak={self._stuck_count}  "
                    f"axis={axis_counts}"
                )
            return {"action": "redirect_active", "ratio": ratio, "net": net,
                    "axis_counts": axis_counts, "dominant": dominant, "code_gap": code_gap}

        return {"action": "idle", "ratio": ratio, "net": net,
                "stuck_count": self._stuck_count, "active": self._active,
                "dominant": dominant, "code_gap": code_gap}

    @property
    def is_active(self) -> bool:
        return self._active

    # ── internal ──────────────────────────────────────────────────────────────

    def _scan_recent_experiences(self) -> Dict[str, int]:
        """Tail SCAN_WINDOW entries from surface_pressure_log.jsonl (actual evolver
        surface fires) to measure real axis activity.  Falls back to the old
        pressure_experiences.jsonl (excluding Gate-5 rejections) if the surface
        log is unavailable."""
        counts: Dict[str, int] = {"X": 0, "T": 0, "N": 0, "B": 0, "A": 0}
        surf_path = os.path.join(self.repo_root, _SURF_REL)
        if os.path.exists(surf_path):
            try:
                chunk = 65536
                buf   = b""
                lines = []
                with open(surf_path, "rb") as f:
                    f.seek(0, 2)
                    pos = f.tell()
                    while len(lines) < SCAN_WINDOW and pos > 0:
                        read_sz = min(chunk, pos)
                        pos    -= read_sz
                        f.seek(pos)
                        buf    = f.read(read_sz) + buf
                        parts  = buf.split(b"\n")
                        buf    = parts[0]
                        for part in reversed(parts[1:]):
                            part = part.strip()
                            if part:
                                lines.append(part)
                            if len(lines) >= SCAN_WINDOW:
                                break
                for raw in lines[:SCAN_WINDOW]:
                    try:
                        obj  = json.loads(raw)
                        axes = obj.get("expected_axes") or []
                        for ax in axes:
                            if ax in counts:
                                counts[ax] += 1
                    except Exception:
                        pass
                if any(counts.values()):
                    return counts
            except Exception:
                pass
        # Fallback: pressure_experiences, excluding Gate-5 rejections
        exp_path = os.path.join(self.repo_root, _EXP_REL)
        if not os.path.exists(exp_path):
            return counts
        try:
            chunk = 65536
            buf   = b""
            lines = []
            with open(exp_path, "rb") as f:
                f.seek(0, 2)
                pos = f.tell()
                while len(lines) < SCAN_WINDOW and pos > 0:
                    read_sz = min(chunk, pos)
                    pos    -= read_sz
                    f.seek(pos)
                    buf    = f.read(read_sz) + buf
                    parts  = buf.split(b"\n")
                    buf    = parts[0]
                    for part in reversed(parts[1:]):
                        part = part.strip()
                        if part:
                            lines.append(part)
                        if len(lines) >= SCAN_WINDOW:
                            break
            for raw in lines[:SCAN_WINDOW]:
                try:
                    obj     = json.loads(raw)
                    outcome = obj.get("outcome") or {}
                    if outcome.get("tone") == "rejected" or outcome.get("resolved") is False:
                        continue
                    pursuing = obj.get("pursuing", "")
                    for ax in ("X", "T", "N", "B", "A"):
                        if f"_{ax}_axis" in pursuing or f"promote_{ax}" in pursuing:
                            counts[ax] += 1
                except Exception:
                    pass
        except Exception:
            pass
        return counts

    def _overhead_ratio(self, counts: Dict[str, int]) -> float:
        total = sum(counts.values())
        if total == 0:
            return 0.0
        overhead = counts.get("X", 0) + counts.get("T", 0)
        return overhead / total

    def _net_leverage(self, counts: Dict[str, int]) -> float:
        """Cost-weighted net leverage: (B×b_B + A×b_A) − (X×b_X + T×b_T)."""
        overhead = (counts.get("X", 0) * _AX_BUDGET["X"] +
                    counts.get("T", 0) * _AX_BUDGET["T"])
        leverage = (counts.get("B", 0) * _AX_BUDGET["B"] +
                    counts.get("A", 0) * _AX_BUDGET["A"])
        return leverage - overhead

    def _write_redirect(self):
        """Inject leverage-redirect bias into adapter_hints.json."""
        path = os.path.join(self.repo_root, _HINTS_REL)
        try:
            hints: Dict[str, Any] = {}
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    hints = json.load(f)
            if not isinstance(hints, dict):
                hints = {}
            hints["evolver_bias_hints"]      = dict(REDIRECT_BIAS)
            hints["leverage_redirect_active"] = True
            hints["leverage_redirect_at"]     = float(time.time())
            hints["genealogy_gate_relief"]    = {
                "active":        True,
                "relief_factor": RELIEF_FACTOR,
                "reason":        "overhead_stuck",
                "activated_at":  float(time.time()),
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(hints, f, indent=2, sort_keys=True)
        except Exception:
            pass

    def _clear_redirect(self):
        """Remove leverage-redirect bias from adapter_hints.json."""
        path = os.path.join(self.repo_root, _HINTS_REL)
        try:
            hints: Dict[str, Any] = {}
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    hints = json.load(f)
            if not isinstance(hints, dict):
                hints = {}
            hints.pop("leverage_redirect_active", None)
            hints.pop("leverage_redirect_at", None)
            # Restore neutral bias (let adapter compute from fresh log)
            hints["evolver_bias_hints"] = {}
            hints["genealogy_gate_relief"] = {"active": False}
            with open(path, "w", encoding="utf-8") as f:
                json.dump(hints, f, indent=2, sort_keys=True)
        except Exception:
            pass

    def _route_snapshot(self) -> Dict[str, Any]:
        path = os.path.join(self.repo_root, _QUERY_REL)
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _log(self, msg: str):
        path = os.path.join(self.repo_root, _LOG_REL)
        try:
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            with open(path, "a", encoding="utf-8") as f:
                f.write(f"[{ts}]  {msg}\n")
        except Exception:
            pass


# ── Convenience function for daemon integration ────────────────────────────────

_valve: Optional[LeverageReliefValve] = None

def tick_leverage_relief(repo_root: str) -> Dict[str, Any]:
    """
    Stateful singleton tick. Call from daemon every ~600s.

    Returns action dict:
        {"action": "idle"|"redirect_active"|"cleared", "ratio": float, "net": float, ...}
    """
    global _valve
    if _valve is None:
        _valve = LeverageReliefValve(repo_root)
    return _valve.tick()

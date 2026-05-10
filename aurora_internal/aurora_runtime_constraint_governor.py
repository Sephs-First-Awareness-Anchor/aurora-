#!/usr/bin/env python3
"""
aurora_runtime_constraint_governor.py
====================================
Bind Aurora's 5-constraint logic to actual runtime execution policy.

This governor does not replace semantic pressure. It turns the same
constraint frame into host-level scheduling and wakeup decisions so Aurora
conserves CPU, memory, disk, and concurrency when the machine is under load.
"""

from __future__ import annotations

import os
import time
from collections import deque
from typing import Any, Dict, Optional

from aurora_constraint_engine import (
    ConstraintVector as _ConstraintVector,
    FoundationalContract as _FoundationalContract,
    ExistenceMode as _ExistenceMode,
    GovernorWeights as _GovernorWeights,
)
_FC = _FoundationalContract()

_AXES = ("X", "T", "N", "B", "A")
_DISK_ADMISSIBILITY_ENABLED = os.environ.get(
    "AURORA_ENABLE_DISK_ADMISSIBILITY",
    "0",
).strip().lower() in {"1", "true", "yes", "on"}
_RUNTIME_BLOCKS_DISABLED = os.environ.get(
    "AURORA_DISABLE_RUNTIME_BLOCKS",
    "0",
).strip().lower() in {"1", "true", "yes", "on"}

_TASK_PROFILES: Dict[str, Dict[str, Any]] = {
    "response_turn": {
        "axes": {"X": 0.30, "T": 0.20, "N": 0.20, "B": 0.15, "A": 0.20},
        "floor": 0.18,
        "cost": 0.30,
        "retry": 60,
        "critical": True,
    },
    "study": {
        "axes": {"X": 0.15, "T": 0.25, "N": 0.30, "B": 0.10, "A": 0.25},
        "floor": 0.42,
        "cost": 0.35,
        "retry": 300,
    },
    "dream": {
        "axes": {"X": 0.10, "T": 0.10, "N": 0.15, "B": 0.35, "A": 0.35},
        "floor": 0.50,
        "cost": 0.85,
        "retry": 1800,
        "heavy_cooldown": 120,
    },
    "browser_ritual": {
        "axes": {"X": 0.20, "T": 0.10, "N": 0.25, "B": 0.15, "A": 0.30},
        "floor": 0.60,
        "cost": 0.75,
        "retry": 1800,
        "quiet_sensitive": True,
    },
    "status": {
        "axes": {"X": 0.25, "T": 0.30, "N": 0.20, "B": 0.15, "A": 0.10},
        "floor": 0.12,
        "cost": 0.08,
        "retry": 60,
        "critical": True,
    },
    "relief_research": {
        "axes": {"X": 0.25, "T": 0.25, "N": 0.20, "B": 0.15, "A": 0.15},
        "floor": 0.18,
        "cost": 0.18,
        "retry": 180,
    },
    "assimilation": {
        "axes": {"X": 0.15, "T": 0.15, "N": 0.25, "B": 0.25, "A": 0.20},
        "floor": 0.56,
        "cost": 0.78,
        "retry": 900,
        "heavy_cooldown": 120,
    },
    "mutation": {
        "axes": {"X": 0.15, "T": 0.10, "N": 0.20, "B": 0.25, "A": 0.30},
        "floor": 0.55,
        "cost": 0.72,
        "retry": 1200,
        "lock_sensitive": True,
    },
    "pressure_routing": {
        "axes": {"X": 0.10, "T": 0.20, "N": 0.25, "B": 0.25, "A": 0.20},
        "floor": 0.50,
        "cost": 0.38,
        "retry": 600,
    },
    "distill": {
        "axes": {"X": 0.25, "T": 0.20, "N": 0.30, "B": 0.20, "A": 0.05},
        "floor": 0.62,
        "cost": 0.92,
        "retry": 2400,
        "heavy_cooldown": 180,
        "lock_sensitive": True,
    },
    "away_social": {
        "axes": {"X": 0.15, "T": 0.15, "N": 0.25, "B": 0.15, "A": 0.30},
        "floor": 0.70,
        "cost": 0.90,
        "retry": 1800,
        "quiet_sensitive": True,
    },
    "save": {
        "axes": {"X": 0.35, "T": 0.20, "N": 0.20, "B": 0.20, "A": 0.05},
        "floor": 0.35,
        "cost": 0.55,
        "retry": 300,
        "lock_sensitive": True,
        "critical": True,
    },
    "reach_out": {
        "axes": {"X": 0.15, "T": 0.15, "N": 0.15, "B": 0.20, "A": 0.35},
        "floor": 0.66,
        "cost": 0.38,
        "retry": 900,
        "quiet_sensitive": True,
    },
    "evo_tick": {
        "axes": {"X": 0.10, "T": 0.35, "N": 0.20, "B": 0.20, "A": 0.15},
        "floor": 0.28,
        "cost": 0.12,
        "retry": 45,
    },
    "evo_evidence": {
        "axes": {"X": 0.15, "T": 0.15, "N": 0.15, "B": 0.35, "A": 0.20},
        "floor": 0.38,
        "cost": 0.42,
        "retry": 180,
    },
    "genealogy_flush": {
        "axes": {"X": 0.25, "T": 0.15, "N": 0.20, "B": 0.30, "A": 0.10},
        "floor": 0.55,
        "cost": 0.50,
        "retry": 300,
        "lock_sensitive": True,
    },
}


def _normalize_axis_map(raw: Any) -> Dict[str, float]:
    out: Dict[str, float] = {}
    if not isinstance(raw, dict):
        return out
    for key, value in raw.items():
        axis = str(key or "").strip().upper()[:1]
        if axis not in _AXES:
            continue
        try:
            out[axis] = _clamp(float(value))
        except Exception:
            continue
    return out


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


class RuntimeConstraintGovernor:
    def __init__(self, state_dir: str = ""):
        self.state_dir = str(state_dir or "")
        self.last_run: Dict[str, float] = {}
        self.last_heavy_run: float = 0.0
        self._decision_history: deque = deque(maxlen=120)
        self._last_status: Dict[str, Any] = {}
        self.field_map = None  # Optional ConstraintFieldAccumulator (read-only observer)

    def set_field_map(self, field_map) -> None:
        """Attach a ConstraintFieldAccumulator as read-only observer. Pass None to detach."""
        self.field_map = field_map

    def evaluate_task(
        self,
        task_name: str,
        systems: Optional[Dict[str, Any]],
        *,
        now: Optional[float] = None,
        heat: str = "medium",
        quiet: bool = False,
        state_write_lock: bool = False,
    ) -> Dict[str, Any]:
        # QAO Heuristic Repair: anomaly guard
        try:
            import json, os
            _fp_path = os.path.join(self.state_dir, "fail_points.json") if getattr(self, "state_dir", "") else ""
            if _fp_path and os.path.exists(_fp_path):
                _fails = json.load(open(_fp_path))
                _recs = _fails.get("records", {})
                if any(_recs.get(k, {}).get("fail_count", 0) > 1000 for k in ("contradiction_handling", "implied_intent_inference", "uncertainty_signaling")):
                    if heat in ("low", "medium"):
                        heat = "high"
        except Exception:
            pass

        now = float(now if now is not None else time.time())
        profile = dict(_TASK_PROFILES.get(task_name, {}))
        if not profile:
            return {
                "allowed": True,
                "reason": "unprofiled_task",
                "retry_in": 60,
                "score": 1.0,
            }

        host = self._host_metrics()
        pressure = self._pressure_state(systems)

        # ── Sweep overlay: parameter_sweep.py may inject test settings ────────
        _sweep_overlay: Dict[str, Any] = {}
        try:
            import json as _json
            _ov_path = os.path.join(self.state_dir, "governor_sweep_overlay.json") if self.state_dir else ""
            if not _ov_path:
                _base = os.path.join(os.path.dirname(__file__), "..", "aurora_state", "governor_sweep_overlay.json")
                _ov_path = os.path.normpath(_base)
            if os.path.exists(_ov_path):
                _ov = _json.loads(open(_ov_path).read())
                if _ov.get("active") and (time.time() - float(_ov.get("written_at", 0))) < 1800:
                    _sweep_overlay = _ov
                    heat = str(_ov.get("heat_hint", heat))
        except Exception:
            pass

        budgets = self._runtime_budgets(host, pressure, heat, quiet=quiet, state_write_lock=state_write_lock)
        if _sweep_overlay:
            global_axis_weights = _normalize_axis_map(_sweep_overlay.get("axis_weights"))
            if global_axis_weights:
                for ax, value in global_axis_weights.items():
                    budgets["axes"][ax] = max(float(budgets["axes"].get(ax, 0.0)), float(value))
            task_overrides = dict(_sweep_overlay.get("task_overrides") or {})
            task_override = dict(task_overrides.get(task_name) or {})
            if task_override:
                if isinstance(task_override.get("axes"), dict):
                    merged_axes = dict(profile.get("axes", {}))
                    for ax, value in _normalize_axis_map(task_override.get("axes")).items():
                        merged_axes[ax] = value
                    profile["axes"] = merged_axes
                for key in ("floor", "cost", "retry", "critical", "quiet_sensitive", "lock_sensitive"):
                    if key in task_override:
                        profile[key] = task_override[key]
        retry_in = self._retry_interval(profile, host, heat)
        last_run_age = now - float(self.last_run.get(task_name, 0.0))
        temporal_maturity = self._temporal_maturity(task_name, last_run_age, retry_in)
        energy_balance = self._balance_energy_axis(
            budgets.get("axes", {}),
            temporal_maturity=temporal_maturity,
        )
        budgets["axes"]["N"] = energy_balance["balanced_N"]
        budgets["energy_balance"] = energy_balance

        score = sum(float(profile["axes"].get(ax, 0.0)) * float(budgets["axes"].get(ax, 0.0)) for ax in _AXES)
        dominant_limit = min(budgets["axes"], key=lambda ax: budgets["axes"].get(ax, 0.0))

        if _RUNTIME_BLOCKS_DISABLED:
            decision = {
                "task": task_name,
                "allowed": True,
                "reason": "runtime_blocks_disabled",
                "retry_in": 0,
                "score": round(float(score), 4),
                "floor": round(float(profile.get("floor", 0.0) or 0.0), 4),
                "cost": round(float(profile.get("cost", 0.0) or 0.0), 4),
                "dominant_runtime_axis": str(budgets.get("dominant_axis", "N") or "N"),
                "limiting_axis": dominant_limit,
                "host": host,
                "runtime_axes": dict(budgets.get("axes", {})),
                "pressure_axes": dict(pressure.get("axes", {})),
                "timestamp": now,
            }
            self._decision_history.append(decision)
            self._last_status = self.status()
            return decision

        # Maintenance multiplier: task ran recently → floor drops to 10% of normal.
        # Prevents established routines from draining X/T budget just to stay in cycle.
        # Sweep overlay may override the multiplier for testing.
        effective_floor = float(profile.get("floor", 0.5))
        if self.last_run.get(task_name) and last_run_age < retry_in * 2.0:
            _maint_mult = float(_sweep_overlay.get("maintenance_mult", 0.10)) if _sweep_overlay else 0.10
            effective_floor = effective_floor * _maint_mult

        # Sweep overlay: override N-axis hard floor if active
        if _sweep_overlay:
            _n_override = float(_sweep_overlay.get("n_floor_override", 0.10))
            budgets["axes"]["N"] = max(_n_override, budgets["axes"].get("N", _n_override))

        reason = "allowed"
        allowed = True

        if profile.get("quiet_sensitive") and quiet:
            allowed = False
            reason = "quiet_window_boundary"
        elif profile.get("lock_sensitive") and state_write_lock:
            allowed = False
            reason = "state_write_lock"
        elif (
            host["mem_available_mb"] < 512
            and profile.get("cost", 0.0) >= 0.45
            and not profile.get("critical")
            and not self._low_memory_time_existence_admissible(
                profile,
                budgets,
                host,
                score=score,
                floor=effective_floor,
                temporal_maturity=temporal_maturity,
                quiet=quiet,
                state_write_lock=state_write_lock,
            )
        ):
            allowed = False
            reason = "x_memory_floor"
        elif host["load_ratio"] > 1.05 and profile.get("cost", 0.0) >= 0.55 and not profile.get("critical"):
            allowed = False
            reason = "n_load_saturation"
        elif (
            _DISK_ADMISSIBILITY_ENABLED and
            host["disk_free_ratio"] < 0.08 and
            profile.get("cost", 0.0) >= 0.45 and
            not profile.get("critical")
        ):
            allowed = False
            reason = "x_disk_admissibility"
        elif (
            profile.get("cost", 0.0) >= 0.75
            and (now - self.last_heavy_run) < float(profile.get("heavy_cooldown", max(120.0, retry_in * 0.25)) or 120.0)
        ):
            allowed = False
            reason = "b_concurrency_cooldown"
        elif score < effective_floor:
            allowed = False
            reason = f"axis_budget:{dominant_limit}"

        decision = {
            "task": task_name,
            "allowed": bool(allowed),
            "reason": reason,
            "retry_in": int(retry_in),
            "score": round(float(score), 4),
            "floor": round(float(effective_floor), 4),
            "cost": round(float(profile.get("cost", 0.0)), 4),
            "dominant_runtime_axis": str(budgets.get("dominant_axis", "N") or "N"),
            "limiting_axis": dominant_limit,
            "host": host,
            "runtime_axes": dict(budgets.get("axes", {})),
            "energy_balance": dict(budgets.get("energy_balance", {})),
            "pressure_axes": dict(pressure.get("axes", {})),
            "constraint_signature": self._constraint_signature(budgets.get("axes", {})),
            "runtime_regime": self._runtime_regime(budgets.get("axes", {}), pressure.get("axes", {})),
            "language_projection": _FC.language_projection(_ExistenceMode.AGENTIC),
            "timestamp": now,
        }
        self._decision_history.append(decision)
        self._last_status = self.status()
        return decision

    def note_task_run(self, task_name: str, *, now: Optional[float] = None) -> None:
        now = float(now if now is not None else time.time())
        self.last_run[str(task_name)] = now
        profile = _TASK_PROFILES.get(str(task_name), {})
        if float(profile.get("cost", 0.0) or 0.0) >= 0.75:
            self.last_heavy_run = now
        self._last_status = self.status()

    # ── Energy income ─────────────────────────────────────────────────────────

    # Maps source type → (axes_credited, base_amount, half_life_secs)
    # half_life: how long until the credit decays to 50% of original value
    _INCOME_PROFILES: Dict[str, Any] = {
        # Interactions — short-lived burst, refreshed each turn
        "interaction_quality":  {"axes": ["T", "A"],       "amount": 0.12, "half_life": 1200},
        "interaction_deep":     {"axes": ["T", "A", "N"],  "amount": 0.18, "half_life": 1800},
        "interaction_learning": {"axes": ["N", "T"],       "amount": 0.15, "half_life": 2400},
        # Learning events — longer-lasting, represent genuine understanding
        "study_complete":       {"axes": ["N", "T"],       "amount": 0.20, "half_life": 3600},
        "distill_complete":     {"axes": ["N", "B", "X"],  "amount": 0.25, "half_life": 5400},
        "dream_complete":       {"axes": ["B", "A"],       "amount": 0.18, "half_life": 3600},
        "assimilation_complete":{"axes": ["X", "N"],       "amount": 0.16, "half_life": 3600},
        # Deep understanding: archetype resolved, doctrine confirmed
        "understanding_event":  {"axes": ["N", "B", "A"],  "amount": 0.22, "half_life": 7200},
    }

    def note_energy_income(
        self,
        source: str,
        *,
        quality: float = 1.0,      # 0..1 multiplier on base amount
        now: Optional[float] = None,
        notes: str = "",
    ) -> None:
        """
        Record an energy income event. The governor will add decayed credits
        from this event to axis budgets on future evaluate_task() calls.

        source   — key from _INCOME_PROFILES (or a custom one with fallback defaults)
        quality  — 0..1 scales the base credit amount (e.g. engagement depth)
        """
        now = float(now if now is not None else time.time())
        profile = self._INCOME_PROFILES.get(source, {"axes": ["T"], "amount": 0.08, "half_life": 1200})
        amount = float(profile["amount"]) * max(0.0, min(1.0, quality))
        if amount < 0.005:
            return

        credit = {
            "source":    source,
            "axes":      list(profile["axes"]),
            "amount":    round(amount, 4),
            "half_life": int(profile["half_life"]),
            "ts":        now,
            "notes":     notes,
        }

        import json as _json
        credits = self._load_energy_income()
        credits.append(credit)
        # Prune: drop fully decayed credits (< 0.5% of original) and keep last 100
        live = []
        for c in credits:
            age = now - float(c.get("ts", now))
            hl  = float(c.get("half_life", 1800))
            if 0.5 ** (age / hl) >= 0.005:
                live.append(c)
        live = live[-100:]

        try:
            _ef = os.path.join(self.state_dir, "energy_income.json") if self.state_dir else ""
            if _ef:
                open(_ef, "w", encoding="utf-8").write(_json.dumps(live, indent=2))
        except Exception:
            pass

    def _load_energy_income(self) -> list:
        import json as _json
        try:
            _ef = os.path.join(self.state_dir, "energy_income.json") if self.state_dir else ""
            if not _ef or not os.path.exists(_ef):
                return []
            return list(_json.loads(open(_ef, encoding="utf-8").read()) or [])
        except Exception:
            return []

    def energy_income_summary(self) -> Dict[str, Any]:
        """Returns current live credits and their decayed values — for hub display."""
        credits = self._load_energy_income()
        now = time.time()
        live = []
        total_by_axis: Dict[str, float] = {ax: 0.0 for ax in _AXES}
        for c in credits:
            age = now - float(c.get("ts", now))
            hl  = float(c.get("half_life", 1800))
            decay = 0.5 ** (age / hl)
            effective = float(c.get("amount", 0.0)) * decay
            if effective < 0.001:
                continue
            live.append({
                "source":    c.get("source", "?"),
                "axes":      c.get("axes", []),
                "effective": round(effective, 4),
                "age_min":   round(age / 60, 1),
                "notes":     c.get("notes", ""),
            })
            for ax in c.get("axes", []):
                if ax in total_by_axis:
                    total_by_axis[ax] = round(total_by_axis[ax] + effective, 4)
        return {
            "live_credits": live,
            "total_by_axis": total_by_axis,
            "credit_count": len(live),
        }

    def recommended_sleep(self, systems: Optional[Dict[str, Any]], *, heat: str = "medium") -> float:
        host = self._host_metrics()
        pressure = self._pressure_state(systems)
        budgets = self._runtime_budgets(host, pressure, heat, quiet=False, state_write_lock=False)
        n_budget = float(budgets["axes"].get("N", 0.5))
        t_budget = float(budgets["axes"].get("T", 0.5))
        if n_budget < 0.25 or t_budget < 0.25:
            return 5.0 # Reduced from 30.0
        if n_budget < 0.45 or t_budget < 0.40:
            return 2.0 # Reduced from 20.0
        return 0.5 # Reduced from 15.0

    def status(self) -> Dict[str, Any]:
        recent = list(self._decision_history)[-12:]
        blocked = [
            {
                "task": item.get("task", ""),
                "reason": item.get("reason", ""),
                "score": item.get("score", 0.0),
            }
            for item in recent
            if not item.get("allowed", False)
        ][-6:]
        host = dict(recent[-1].get("host", {})) if recent else self._host_metrics()
        axes = dict(recent[-1].get("runtime_axes", {})) if recent else {ax: 0.5 for ax in _AXES}
        energy_balance = dict(recent[-1].get("energy_balance", {})) if recent else {}
        mode = "open"
        if host.get("load_ratio", 0.0) > 1.0 or host.get("mem_pressure", 0.0) > 0.90:
            mode = "survival"
        elif host.get("load_ratio", 0.0) > 0.75 or host.get("mem_pressure", 0.0) > 0.82:
            mode = "conserve"
        elif host.get("load_ratio", 0.0) > 0.55:
            mode = "balanced"
        return {
            "mode": mode,
            "host": host,
            "runtime_axes": {ax: round(float(axes.get(ax, 0.0) or 0.0), 4) for ax in _AXES},
            "energy_balance": energy_balance,
            "constraint_signature": self._constraint_signature(axes),
            "runtime_regime": self._runtime_regime(axes, recent[-1].get("pressure_axes", {})) if recent else self._runtime_regime(axes, {}),
            "language_projection": _FC.language_projection(_ExistenceMode.AGENTIC),
            "recent_blocked": blocked,
            "last_heavy_run_age": round(max(0.0, time.time() - float(self.last_heavy_run or 0.0)), 1) if self.last_heavy_run else None,
            "task_profiles": sorted(_TASK_PROFILES.keys()),
        }

    def constraint_profile(self) -> _ConstraintVector:
        status = self.status()
        ax = dict(status.get("runtime_axes", {}) or {})
        return _ConstraintVector(
            X=max(1e-9, float(ax.get("X", _GovernorWeights.X))),
            T=float(ax.get("T", _GovernorWeights.T)),
            N=float(ax.get("N", _GovernorWeights.N)),
            B=float(ax.get("B", _GovernorWeights.B)),
            A=float(ax.get("A", _GovernorWeights.A)),
        )

    def runtime_regime(self) -> Dict[str, Any]:
        cv = self.constraint_profile()
        axes = {"X": cv.X, "T": cv.T, "N": cv.N, "B": cv.B, "A": cv.A}
        dominant = max(axes, key=axes.__getitem__)
        return {
            "axes": axes,
            "dominant_axis": dominant,
            "governor_weight": _GovernorWeights.AS_DICT.get(dominant, 0.0),
        }

    def language_projection(self) -> Dict[str, Any]:
        return _FC.language_projection(_ExistenceMode.AGENTIC)

    def universal_representation(self) -> Dict[str, Any]:
        cv = self.constraint_profile()
        return {
            "constraint_vector": {"X": cv.X, "T": cv.T, "N": cv.N, "B": cv.B, "A": cv.A},
            "runtime_regime": self.runtime_regime(),
            "language_projection": self.language_projection(),
            "unit_state": self.status(),
        }

    def evaluate_profile(
        self,
        axis_weights: Dict[str, float],
        pressure_axes: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        signature = self._constraint_signature(axis_weights)
        return {
            "constraint_signature": signature,
            "runtime_regime": self._runtime_regime(axis_weights, pressure_axes or {}),
            "language_projection": _FC.language_projection(_ExistenceMode.AGENTIC),
        }

    def _temporal_maturity(self, task_name: str, last_run_age: float, retry_in: int) -> float:
        """
        How much tick-time has accrued for this task.

        Never-run tasks start mature enough to be considered; recently-run tasks
        must earn their way back through T instead of draining X/N immediately.
        """
        if not self.last_run.get(str(task_name)):
            return 1.0
        return _clamp(float(last_run_age) / max(60.0, float(retry_in)))

    def _balance_energy_axis(
        self,
        axes: Dict[str, Any],
        *,
        temporal_maturity: float,
    ) -> Dict[str, float]:
        """
        Complete the N-axis budget by tying it to existence and time.

        N remains the energy budget, but runtime energy should not be treated as
        a standalone number. If X/T support is strong and enough task-time has
        accrued, N can recover. If X/T support is weak, a high N reading is
        pulled back because energy cannot safely express without admissibility
        and persistence.
        """
        x = _clamp(float(axes.get("X", 0.0) or 0.0))
        t = _clamp(float(axes.get("T", 0.0) or 0.0))
        n_raw = _clamp(float(axes.get("N", 0.0) or 0.0))
        maturity = _clamp(float(temporal_maturity))
        xt_support = _clamp((0.45 * x) + (0.45 * t) + (0.10 * maturity))
        balanced_n = _clamp((0.58 * n_raw) + (0.42 * xt_support))
        return {
            "raw_N": round(n_raw, 4),
            "xt_support": round(xt_support, 4),
            "temporal_maturity": round(maturity, 4),
            "balanced_N": round(balanced_n, 4),
        }

    def _low_memory_time_existence_admissible(
        self,
        profile: Dict[str, Any],
        budgets: Dict[str, Any],
        host: Dict[str, Any],
        *,
        score: float,
        floor: float,
        temporal_maturity: float,
        quiet: bool,
        state_write_lock: bool,
    ) -> bool:
        """
        Allow mature heavy work under soft memory pressure when X/T/N agree.

        This replaces the old flat <512MB veto. Below a hard survival floor we
        still block, but between survival and comfort the task can proceed if it
        has waited long enough and the existence/time substrate can carry it.
        """
        if quiet and profile.get("quiet_sensitive"):
            return False
        if state_write_lock and profile.get("lock_sensitive"):
            return False
        if float(host.get("mem_available_mb", 0.0) or 0.0) < 384.0:
            return False
        axes = dict(budgets.get("axes", {}) or {})
        energy_balance = dict(budgets.get("energy_balance", {}) or {})
        x = _clamp(float(axes.get("X", 0.0) or 0.0))
        t = _clamp(float(axes.get("T", 0.0) or 0.0))
        n = _clamp(float(axes.get("N", 0.0) or 0.0))
        xt_support = _clamp(float(energy_balance.get("xt_support", min(x, t)) or 0.0))
        cost = _clamp(float(profile.get("cost", 0.0) or 0.0))
        required_support = min(0.82, 0.42 + (cost * 0.34))
        return (
            temporal_maturity >= 0.85
            and score >= max(float(floor), 0.0)
            and min(x, t, n, xt_support) >= required_support
        )

    def _pressure_state(self, systems: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        systems = systems or {}
        axes = {ax: 0.2 for ax in _AXES}
        dominant_axis = "N"

        # Source 0: constraint field map — live 31-field accumulator state.
        # Provides per-axis pressure derived from multi-axis co-activation patterns.
        # Only used as a seed; higher-priority sources below will override if available.
        try:
            _fm = self.field_map if self.field_map is not None else (
                systems.get('field_map') if isinstance(systems, dict) else None
            )
            if _fm is not None:
                _fm_state = _fm.get_state()
                _fp = _fm_state.field_pressures
                # Accumulate per-axis pressure: for each active single-axis field,
                # read its accumulated pressure directly as the axis signal.
                for ax in _AXES:
                    from aurora_constraint_field_map import get_field
                    _f = get_field(frozenset([ax]))
                    if _f is not None:
                        _p = float(_fp.get(_f.field_id, 0.0))
                        if _p > 0.0:
                            axes[ax] = _clamp(_p)
                _dom = _fm_state.dominant_field
                if _dom is not None and len(_dom.axes) == 1:
                    dominant_axis = next(iter(_dom.axes))
        except Exception:
            pass

        # Source 1: live pipeline state from the most recent response turn
        pipeline_state = dict(systems.get("_last_pipeline_state") or {}) if isinstance(systems, dict) else {}
        live_axes = dict(pipeline_state.get("axis_activation") or {})
        if live_axes:
            for ax in _AXES:
                axes[ax] = _clamp(float(live_axes.get(ax, axes[ax]) or axes[ax]))
            dominant_axis = str(pipeline_state.get("dominant_axis", dominant_axis) or dominant_axis)
            return {"axes": axes, "dominant_axis": dominant_axis}

        # Source 2: genealogy chain pressure orientation
        try:
            chamber = systems.get("chamber")
            genealogy = getattr(chamber, "_genealogy", None) if chamber is not None else None
            if genealogy is not None and hasattr(genealogy, "pressure_orientation"):
                orientation = dict(genealogy.pressure_orientation() or {})
                if orientation:
                    max_val = max(max(float(v or 0.0), 0.0) for v in orientation.values()) or 1.0
                    for ax in _AXES:
                        axes[ax] = _clamp(float(orientation.get(ax, 0.0) or 0.0) / max_val)
                    dominant_axis = max(axes, key=lambda ax: axes[ax])
                    return {"axes": axes, "dominant_axis": dominant_axis}
        except Exception:
            pass

        # Source 3: pressure classifier's axis_pressure from query_bias.json
        # (written by PressureRouter; reflects surface_pressure_log signal)
        try:
            qb_path = os.path.join(self.state_dir, "query_bias.json")
            if not qb_path or not os.path.exists(qb_path):
                raise FileNotFoundError
            import json as _json
            qb = _json.loads(open(qb_path, encoding="utf-8").read())
            qb_axes = dict(qb.get("axis_pressure") or {})
            # Only use if at least one axis has non-zero signal
            if any(float(v or 0.0) > 0.0 for v in qb_axes.values()):
                for ax in _AXES:
                    axes[ax] = _clamp(float(qb_axes.get(ax, axes[ax]) or axes[ax]))
                dominant_axis = max(axes, key=lambda ax: axes[ax])
        except Exception:
            pass

        return {"axes": axes, "dominant_axis": dominant_axis}

    def _runtime_budgets(
        self,
        host: Dict[str, Any],
        pressure: Dict[str, Any],
        heat: str,
        *,
        quiet: bool,
        state_write_lock: bool,
    ) -> Dict[str, Any]:
        heat_value = {"low": 0.20, "medium": 0.45, "high": 0.75}.get(str(heat or "medium").lower(), 0.45)
        load_ratio = float(host.get("load_ratio", 0.0) or 0.0)
        mem_pressure = float(host.get("mem_pressure", 0.0) or 0.0)
        disk_free_ratio = float(host.get("disk_free_ratio", 1.0) or 1.0)
        pressure_axes = dict(pressure.get("axes", {}) or {})
        dominant_axis = str(pressure.get("dominant_axis", "N") or "N")
        quiet_penalty = 0.12 if quiet else 0.0
        lock_penalty = 0.22 if state_write_lock else 0.0

        axes = {
            "X": _clamp(1.0 - max(0.0, load_ratio - 0.70) * 0.35 - max(0.0, mem_pressure - 0.78) * 0.80 - max(0.0, 0.12 - disk_free_ratio) * 1.5 - lock_penalty),
            "T": _clamp(1.0 - heat_value * 0.35 - load_ratio * 0.25 + pressure_axes.get("T", 0.2) * 0.10),
            "N": _clamp(max(0.10, 1.0 - load_ratio * 0.40 - mem_pressure * 0.38 - max(0.0, 0.18 - disk_free_ratio) * 0.60)),
            "B": _clamp(1.0 - max(0.0, load_ratio - 0.80) * 0.60 - quiet_penalty - lock_penalty * 0.35 + pressure_axes.get("B", 0.2) * 0.10),
            "A": _clamp(0.55 + pressure_axes.get(dominant_axis, 0.2) * 0.35 - heat_value * 0.20 - quiet_penalty * 0.50),
        }

        # ── Interaction / learning energy income ──────────────────────────────
        # Successful interactions and genuine learning events add axis credits
        # that decay exponentially over time (half-life varies by source type).
        # This models the biological principle: activity generates energy capacity.
        energy = self._load_energy_income()
        now_for_decay = time.time()
        for credit in energy:
            age = now_for_decay - float(credit.get("ts", now_for_decay))
            half_life = float(credit.get("half_life", 1800))
            decay = 0.5 ** (age / half_life)
            amount = float(credit.get("amount", 0.0)) * decay
            if amount < 0.001:
                continue
            for ax in credit.get("axes", []):
                if ax in axes:
                    axes[ax] = _clamp(axes[ax] + amount)

        return {"axes": axes, "dominant_axis": max(axes, key=lambda ax: axes[ax])}

    def _constraint_signature(self, axes: Dict[str, Any]) -> str:
        numeric = {ax: _clamp(float(axes.get(ax, 0.0) or 0.0)) for ax in _AXES}
        ordered = [ax for ax in _AXES if numeric.get(ax, 0.0) > 0.0]
        base = "".join(ordered) or "X"
        if ordered:
            dominant = max(ordered, key=lambda ax: numeric.get(ax, 0.0))
            if len(ordered) == 5 and numeric.get(dominant, 0.0) >= 0.30:
                return base + dominant
        return base

    def _runtime_regime(self, axes: Dict[str, Any], pressure_axes: Dict[str, Any]) -> Dict[str, Any]:
        numeric_axes = {ax: _clamp(float(axes.get(ax, 0.0) or 0.0)) for ax in _AXES}
        dominant = max(numeric_axes, key=numeric_axes.__getitem__)
        return {
            "dominant_axis": dominant,
            "governor_weight": _GovernorWeights.AS_DICT.get(dominant, 0.0),
            "axes": numeric_axes,
            "pressure_axes": {ax: _clamp(float(pressure_axes.get(ax, 0.0) or 0.0)) for ax in _AXES},
        }

    def _retry_interval(self, profile: Dict[str, Any], host: Dict[str, Any], heat: str) -> int:
        retry = float(profile.get("retry", 300) or 300)
        if host.get("load_ratio", 0.0) > 1.0:
            retry *= 2.0
        elif host.get("load_ratio", 0.0) > 0.75:
            retry *= 1.5
        if host.get("mem_pressure", 0.0) > 0.90:
            retry *= 1.5
        if str(heat or "medium").lower() == "high":
            retry *= 1.25
        return max(60, int(retry))

    def _host_metrics(self) -> Dict[str, Any]:
        cpu_count = max(1, int(os.cpu_count() or 1))
        load1 = 0.0
        load5 = 0.0
        try:
            load1, load5, _ = os.getloadavg()
        except Exception:
            pass
        mem_total_kb = 0.0
        mem_available_kb = 0.0
        try:
            with open("/proc/meminfo", "r", encoding="utf-8") as handle:
                for line in handle:
                    if line.startswith("MemTotal:"):
                        mem_total_kb = float(line.split()[1])
                    elif line.startswith("MemAvailable:"):
                        mem_available_kb = float(line.split()[1])
        except Exception:
            pass
        mem_pressure = 0.0
        if mem_total_kb > 0 and mem_available_kb >= 0:
            mem_pressure = _clamp(1.0 - (mem_available_kb / mem_total_kb))
        disk_free_ratio = 1.0
        try:
            target = self.state_dir or "."
            stat = os.statvfs(target)
            if stat.f_blocks > 0:
                disk_free_ratio = _clamp(float(stat.f_bavail) / float(stat.f_blocks))
        except Exception:
            pass
        rss_mb = 0.0
        try:
            with open("/proc/self/statm", "r", encoding="utf-8") as handle:
                parts = handle.read().strip().split()
            if len(parts) >= 2:
                page_size = float(os.sysconf("SC_PAGE_SIZE"))
                rss_mb = (float(parts[1]) * page_size) / (1024.0 * 1024.0)
        except Exception:
            pass
        return {
            "cpu_count": cpu_count,
            "load_1m": round(float(load1), 4),
            "load_5m": round(float(load5), 4),
            "load_ratio": round(_clamp(max(load1, load5) / float(cpu_count), 0.0, 2.5), 4),
            "mem_available_mb": round(mem_available_kb / 1024.0, 2) if mem_available_kb else 0.0,
            "mem_pressure": round(mem_pressure, 4),
            "disk_free_ratio": round(disk_free_ratio, 4),
            "process_rss_mb": round(rss_mb, 2),
        }

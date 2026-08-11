#!/usr/bin/env python3
"""
AURORA CODE EVOLUTION CHAMBER
=============================
Constraint-native evolutionary scoring for code representation.

This layer mirrors chamber doctrine for code:
  pressure_before -> mutation trace -> pressure_after -> relief decision

The same five constraints are applied at code level:
  X existence : syntax/admissibility integrity
  T temporal  : change stability and replay risk pressure
  N energy    : complexity and maintenance cost pressure
  B boundary  : coupling/interface pressure
  A agency    : adaptive steering pressure (ability to evolve safely)
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations
from aurora_internal.aurora_runtime_faults import record_exception_from_locals as _aurora_record_exception_from_locals

import ast
import hashlib
import json
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, Iterable, List, Optional, Sequence, Tuple

try:
    from aurora_internal.lineage_canonical import operator_action_for_axis as _operator_action_for_axis
except Exception as _aurora_boundary_exc:
    _aurora_record_exception_from_locals(
        locals(),
        module=__name__,
        operation="exception_handler:aurora_internal/aurora_code_evolution_chamber.py:32",
        exc=_aurora_boundary_exc,
        context={"function": "<module>", "handler_line": 32, "source_file": "aurora_internal/aurora_code_evolution_chamber.py"},
    )
    def _operator_action_for_axis(axis: str) -> str:
        mapping = {
            "X": "admissibility_gating",
            "T": "temporal_orchestration",
            "N": "energy_economics",
            "B": "boundary_shaping",
            "A": "agency_direction",
        }
        return str(mapping.get(str(axis or "X").upper(), "cross_constraint_operation"))


AXIS_ORDER: Tuple[str, ...] = ("X", "T", "N", "B", "A")
LABEL_TO_AXIS: Dict[str, str] = {
    "existence": "X",
    "x": "X",
    "temporal": "T",
    "time": "T",
    "t": "T",
    "energy": "N",
    "cost": "N",
    "n": "N",
    "boundary": "B",
    "b": "B",
    "agency": "A",
    "a": "A",
}
AXIS_TO_LABEL: Dict[str, str] = {
    "X": "existence",
    "T": "temporal",
    "N": "energy",
    "B": "boundary",
    "A": "agency",
}


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(v)))


def _mean(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return float(sum(values)) / float(len(values))


def _rounded(value: Any, digits: int = 6) -> float:
    try:
        return round(float(value), int(digits))
    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(),
            module=__name__,
            operation="exception_handler:aurora_internal/aurora_code_evolution_chamber.py:81",
            exc=_aurora_boundary_exc,
            context={"function": "_rounded", "handler_line": 81, "source_file": "aurora_internal/aurora_code_evolution_chamber.py"},
        )
        return 0.0


def _normalize_constraints(values: Iterable[str]) -> FrozenSet[str]:
    out: List[str] = []
    for raw in (values or []):
        tok = str(raw or "").strip().lower()
        if tok in LABEL_TO_AXIS:
            out.append(AXIS_TO_LABEL[LABEL_TO_AXIS[tok]])
    return frozenset(sorted(set(out)))


@dataclass(frozen=True)
class CodeMutationTrace:
    mutation_id: str
    name: str
    constraints_used: FrozenSet[str]
    target_files: Tuple[str, ...]
    parent_ids: Tuple[str, ...] = tuple()
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mutation_id": self.mutation_id,
            "name": self.name,
            "constraints_used": sorted(self.constraints_used),
            "target_files": list(self.target_files),
            "parent_ids": list(self.parent_ids),
            "meta": dict(self.meta or {}),
        }


@dataclass
class CodePressureVec:
    X: float = 0.0
    T: float = 0.0
    N: float = 0.0
    B: float = 0.0
    A: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {"X": float(self.X), "T": float(self.T), "N": float(self.N), "B": float(self.B), "A": float(self.A)}

    def relief_from(self, earlier: "CodePressureVec") -> "CodePressureVec":
        return CodePressureVec(
            X=float(earlier.X) - float(self.X),
            T=float(earlier.T) - float(self.T),
            N=float(earlier.N) - float(self.N),
            B=float(earlier.B) - float(self.B),
            A=float(earlier.A) - float(self.A),
        )

    def max_relief(self) -> float:
        return max(self.to_dict().values(), default=0.0)

    def sum_positive_relief(self) -> float:
        return sum(v for v in self.to_dict().values() if v > 0.0)


@dataclass
class CodePressureSnapshot:
    pressure: CodePressureVec
    metrics: Dict[str, Any]
    measured_at: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pressure": self.pressure.to_dict(),
            "metrics": dict(self.metrics or {}),
            "measured_at": float(self.measured_at),
        }


@dataclass
class CodeLink:
    link_id: str
    parents: Tuple[str, str]
    dominant_axis: str
    semantic_lane: str
    generation: int
    support_count: int
    accepted_count: int
    acceptance_rate: float
    mean_net_benefit: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "link_id": str(self.link_id),
            "parents": list(self.parents),
            "dominant_axis": str(self.dominant_axis),
            "semantic_lane": str(self.semantic_lane),
            "generation": int(self.generation),
            "support_count": int(self.support_count),
            "accepted_count": int(self.accepted_count),
            "acceptance_rate": float(self.acceptance_rate),
            "mean_net_benefit": float(self.mean_net_benefit),
        }


@dataclass
class CodeEvolutionConfig:
    relief_eps: float = 0.005
    relief_total_eps: float = 0.020
    x_risk_max: float = 0.050
    x_growth_allowance: float = 0.010
    k_min: int = 8
    net_min: float = 0.001
    cost_penalty_lambda: float = 1.0
    cost_to_relief_scale: float = 0.10
    tolerance_enabled: bool = True
    tolerance_growth: float = 0.08
    tolerance_decay: float = 0.02
    tolerance_max: float = 0.80
    tolerance_min_factor: float = 0.25
    stagnation_window: int = 32
    stagnation_gain_max: float = 0.50
    stagnation_kmin_floor_ratio: float = 0.50
    stagnation_acceptance_relax_max: float = 0.12
    adaptive_rate: float = 0.10
    gradient_alpha: float = 0.12
    net_min_floor_ratio: float = 0.50
    operation_cost: Dict[str, float] = field(default_factory=lambda: {
        "X": 1.0,   # admissibility operations
        "T": 4.0,   # temporal/replay operations
        "N": 10.0,  # complexity-energy operations
        "B": 16.0,  # boundary/coupling operations
        "A": 25.0,  # steering/agency operations
    })


class CodePressureGovernor:
    """Adaptive pressure regulator for code evolution selection/promotion."""

    def __init__(self, cfg: CodeEvolutionConfig):
        self.cfg = cfg
        self.tolerance_by_operator: Dict[str, float] = {}
        self.operator_success_ema: Dict[str, float] = {}
        self.operator_use_count: Dict[str, int] = {}
        self.last_promotion_tick: int = 0
        self.events_since_promotion: int = 0
        self.promotions: int = 0
        self._stagnation_pressure_ema: float = 0.0

    def tolerance_factor(self, operator_key: str) -> float:
        if not bool(self.cfg.tolerance_enabled):
            return 1.0
        op = str(operator_key or "").strip().lower() or "__unknown__"
        tol = float(self.tolerance_by_operator.get(op, 0.0) or 0.0)
        return max(float(self.cfg.tolerance_min_factor), 1.0 - tol)

    def effective_relief_thresholds(self, base_eps: float, base_total: float) -> Tuple[float, float]:
        g = self.stagnation_gain()
        factor = max(0.55, 1.0 - (0.50 * g))
        return float(base_eps) * factor, float(base_total) * factor

    def effective_kmin(self, base_kmin: int) -> int:
        g = self.stagnation_gain()
        floor = max(2, int(round(float(base_kmin) * float(self.cfg.stagnation_kmin_floor_ratio))))
        k = int(round(float(base_kmin) * (1.0 - 0.60 * g)))
        return max(floor, k)

    def effective_acceptance_floor(self, base: float = 0.45) -> float:
        g = self.stagnation_gain()
        relaxed = float(base) - (float(self.cfg.stagnation_acceptance_relax_max) * g)
        return max(0.30, min(0.90, relaxed))

    def effective_net_min(self, base_net_min: float) -> float:
        g = self.stagnation_gain()
        floor = float(base_net_min) * float(self.cfg.net_min_floor_ratio)
        val = float(base_net_min) * (1.0 - 0.40 * g)
        return max(floor, val)

    def stagnation_gain(self) -> float:
        win = max(1, int(self.cfg.stagnation_window))
        raw = min(1.0, float(self.events_since_promotion) / float(win))
        # EMA smooths short volatility.
        self._stagnation_pressure_ema = (0.85 * self._stagnation_pressure_ema) + (0.15 * raw)
        return max(0.0, min(float(self.cfg.stagnation_gain_max), self._stagnation_pressure_ema * float(self.cfg.stagnation_gain_max)))

    def update_after_event(self, operator_key: str, accepted: bool) -> None:
        op = str(operator_key or "").strip().lower() or "__unknown__"
        self.events_since_promotion += 1
        self.operator_use_count[op] = int(self.operator_use_count.get(op, 0) or 0) + 1

        prev = float(self.operator_success_ema.get(op, 0.5) or 0.5)
        target = 1.0 if bool(accepted) else 0.0
        alpha = float(self.cfg.adaptive_rate)
        self.operator_success_ema[op] = ((1.0 - alpha) * prev) + (alpha * target)

        if bool(self.cfg.tolerance_enabled):
            tol = float(self.tolerance_by_operator.get(op, 0.0) or 0.0)
            tol = min(float(self.cfg.tolerance_max), tol + float(self.cfg.tolerance_growth))
            if bool(accepted):
                tol = max(0.0, tol - (0.40 * float(self.cfg.tolerance_growth)))
            self.tolerance_by_operator[op] = tol
            # decay all operators slightly so old routines can recover relevance.
            d = float(self.cfg.tolerance_decay)
            for k in list(self.tolerance_by_operator.keys()):
                self.tolerance_by_operator[k] = max(0.0, float(self.tolerance_by_operator[k]) - d)

    def register_promotion(self, tick: int) -> None:
        self.last_promotion_tick = int(tick)
        self.events_since_promotion = 0
        self.promotions += 1

    def report(self) -> Dict[str, Any]:
        top = sorted(self.operator_success_ema.items(), key=lambda kv: kv[1], reverse=True)[:8]
        return {
            "events_since_promotion": int(self.events_since_promotion),
            "promotions": int(self.promotions),
            "stagnation_gain": float(self.stagnation_gain()),
            "top_operator_success_ema": [{"operator": k, "ema": float(v)} for k, v in top],
            "tolerance": {k: float(v) for k, v in self.tolerance_by_operator.items()},
        }


class CodeConstraintEvaluator:
    """Measure code-level X/T/N/B/A pressure from repository state."""

    def __init__(self, repo_root: str):
        self.repo_root = os.path.abspath(repo_root)

    def snapshot(self, target_files: Optional[Sequence[str]] = None) -> CodePressureSnapshot:
        files = self._collect_python_files(target_files)
        metrics = self._compute_metrics(files)
        pressure = self._pressure_from_metrics(metrics)
        return CodePressureSnapshot(
            pressure=pressure,
            metrics=metrics,
            measured_at=time.time(),
        )

    def _collect_python_files(self, target_files: Optional[Sequence[str]] = None) -> List[str]:
        if target_files:
            out: List[str] = []
            for raw in target_files:
                p = str(raw or "").strip()
                if not p:
                    continue
                absp = p if os.path.isabs(p) else os.path.join(self.repo_root, p)
                absp = os.path.abspath(absp)
                if os.path.isfile(absp) and absp.endswith(".py"):
                    out.append(absp)
            return sorted(set(out))

        out: List[str] = []
        skip_dirs = {
            ".git",
            "__pycache__",
            "backup_originals_20260301_221224",
            "reset_full_backup_20260302_021145",
            "aurora_runtime_output",
        }
        for root, dirs, files in os.walk(self.repo_root):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for fn in files:
                if fn.endswith(".py"):
                    out.append(os.path.join(root, fn))
        return sorted(out)

    def _compute_metrics(self, files: Sequence[str]) -> Dict[str, Any]:
        metrics: Dict[str, Any] = {
            "files": int(len(files)),
            "loc": 0,
            "syntax_failures": 0,
            "functions": 0,
            "public_functions": 0,
            "classes": 0,
            "branches": 0,
            "imports_local": 0,
            "fanout_hotspots": 0,
            "mutable_ops": 0,
            "test_files": 0,
            "avg_function_lines": 0.0,
            "file_pressures": {},
            "module_pressures": {},
            "subsystem_pressures": {},
        }
        func_lengths: List[float] = []
        fanout_counts: List[int] = []
        file_pressures: Dict[str, Dict[str, float]] = {}
        module_pressures_raw: Dict[str, List[Dict[str, float]]] = defaultdict(list)
        subsystem_pressures_raw: Dict[str, List[Dict[str, float]]] = defaultdict(list)

        project_modules = self._local_module_names(files)
        for path in files:
            fm = self._compute_file_metrics(path, project_modules)
            metrics["loc"] += int(fm.get("loc", 0) or 0)
            metrics["syntax_failures"] += int(fm.get("syntax_failures", 0) or 0)
            metrics["functions"] += int(fm.get("functions", 0) or 0)
            metrics["public_functions"] += int(fm.get("public_functions", 0) or 0)
            metrics["classes"] += int(fm.get("classes", 0) or 0)
            metrics["branches"] += int(fm.get("branches", 0) or 0)
            metrics["imports_local"] += int(fm.get("imports_local", 0) or 0)
            metrics["mutable_ops"] += int(fm.get("mutable_ops", 0) or 0)
            metrics["test_files"] += int(fm.get("test_file", 0) or 0)
            fanout_counts.append(int(fm.get("imports_local", 0) or 0))
            func_lengths.extend(list(fm.get("function_lengths", []) or []))

            fp = self._pressure_from_metrics(dict(fm))
            rel = os.path.relpath(path, self.repo_root)
            fp_dict = fp.to_dict()
            file_pressures[rel] = fp_dict

            module_key = self._module_key_for_path(rel)
            subsystem_key = self._subsystem_key_for_path(rel)
            module_pressures_raw[module_key].append(fp_dict)
            subsystem_pressures_raw[subsystem_key].append(fp_dict)

        metrics["avg_function_lines"] = _mean(func_lengths)
        metrics["fanout_hotspots"] = int(sum(1 for x in fanout_counts if x >= 8))
        metrics["file_pressures"] = file_pressures
        metrics["module_pressures"] = self._aggregate_pressure_groups(module_pressures_raw)
        metrics["subsystem_pressures"] = self._aggregate_pressure_groups(subsystem_pressures_raw)
        return metrics

    def _local_module_names(self, files: Sequence[str]) -> FrozenSet[str]:
        names: List[str] = []
        for p in files:
            b = os.path.basename(p)
            if b.endswith(".py"):
                names.append(b[:-3])
        return frozenset(names)

    def _compute_file_metrics(self, path: str, project_modules: FrozenSet[str]) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "files": 1,
            "loc": 0,
            "syntax_failures": 0,
            "functions": 0,
            "public_functions": 0,
            "classes": 0,
            "branches": 0,
            "imports_local": 0,
            "fanout_hotspots": 0,
            "mutable_ops": 0,
            "test_files": 0,
            "avg_function_lines": 0.0,
            "function_lengths": [],
            "test_file": 0,
        }
        try:
            with open(path, "r", encoding="utf-8") as fh:
                src = fh.read()
        except Exception as _aurora_boundary_exc:
            _aurora_record_exception_from_locals(
                locals(),
                module=__name__,
                operation="exception_handler:aurora_internal/aurora_code_evolution_chamber.py:426",
                exc=_aurora_boundary_exc,
                context={"function": "_compute_file_metrics", "handler_line": 426, "source_file": "aurora_internal/aurora_code_evolution_chamber.py"},
            )
            return out

        lines = [ln for ln in src.splitlines() if ln.strip()]
        out["loc"] = int(len(lines))
        if os.path.basename(path).startswith("test_") or "/tests/" in path.replace("\\", "/"):
            out["test_file"] = 1
            out["test_files"] = 1

        try:
            tree = ast.parse(src, filename=path)
        except Exception as _aurora_boundary_exc:
            _aurora_record_exception_from_locals(
                locals(),
                module=__name__,
                operation="exception_handler:aurora_internal/aurora_code_evolution_chamber.py:437",
                exc=_aurora_boundary_exc,
                context={"function": "_compute_file_metrics", "handler_line": 437, "source_file": "aurora_internal/aurora_code_evolution_chamber.py"},
            )
            out["syntax_failures"] = 1
            return out

        local_import_hits = 0
        mutable_ops = 0
        function_lengths: List[float] = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.For, ast.While, ast.Try, ast.BoolOp, ast.With, ast.Match)):
                out["branches"] += 1
            if isinstance(node, ast.ClassDef):
                out["classes"] += 1
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                out["functions"] += 1
                if not str(node.name).startswith("_"):
                    out["public_functions"] += 1
                mutable_ops += int(any(
                    k in str(node.name).lower()
                    for k in ("save", "load", "write", "persist", "mutate", "inject", "register", "delete", "update")
                ))
                start = int(getattr(node, "lineno", 0) or 0)
                end = int(getattr(node, "end_lineno", start) or start)
                if end >= start > 0:
                    function_lengths.append(float(end - start + 1))
            if isinstance(node, ast.Import):
                for n in node.names:
                    base = str(getattr(n, "name", "")).split(".", 1)[0]
                    if base in project_modules:
                        local_import_hits += 1
            if isinstance(node, ast.ImportFrom):
                mod = str(getattr(node, "module", "") or "")
                base = mod.split(".", 1)[0]
                if base in project_modules:
                    local_import_hits += 1
        out["imports_local"] = int(local_import_hits)
        out["mutable_ops"] = int(mutable_ops)
        out["function_lengths"] = function_lengths
        out["avg_function_lines"] = _mean(function_lengths)
        out["fanout_hotspots"] = 1 if local_import_hits >= 8 else 0
        return out

    def _module_key_for_path(self, rel: str) -> str:
        r = str(rel).replace("\\", "/")
        if "/" not in r:
            return "__root__"
        return r.rsplit("/", 1)[0]

    def _subsystem_key_for_path(self, rel: str) -> str:
        r = str(rel).replace("\\", "/")
        top = r.split("/", 1)[0] if "/" in r else "__root__"
        if top == "aurora_internal":
            return "internal"
        if top.startswith("scripts"):
            return "scripts"
        if top.startswith("aurora_state") or top.startswith("aurora_runtime_output"):
            return "state_runtime"
        return "core"

    def _aggregate_pressure_groups(self, groups: Dict[str, List[Dict[str, float]]]) -> Dict[str, Dict[str, float]]:
        out: Dict[str, Dict[str, float]] = {}
        for key, arr in groups.items():
            if not arr:
                continue
            out[key] = {
                "X": _mean([float(d.get("X", 0.0)) for d in arr]),
                "T": _mean([float(d.get("T", 0.0)) for d in arr]),
                "N": _mean([float(d.get("N", 0.0)) for d in arr]),
                "B": _mean([float(d.get("B", 0.0)) for d in arr]),
                "A": _mean([float(d.get("A", 0.0)) for d in arr]),
            }
        return out

    def _pressure_from_metrics(self, m: Dict[str, Any]) -> CodePressureVec:
        files = float(max(1, int(m.get("files", 0) or 0)))
        loc = float(max(1, int(m.get("loc", 0) or 0)))
        functions = float(max(1, int(m.get("functions", 0) or 0)))
        classes = float(max(0, int(m.get("classes", 0) or 0)))
        branches = float(max(0, int(m.get("branches", 0) or 0)))
        syntax_fail = float(max(0, int(m.get("syntax_failures", 0) or 0)))
        imports_local = float(max(0, int(m.get("imports_local", 0) or 0)))
        fanout_hotspots = float(max(0, int(m.get("fanout_hotspots", 0) or 0)))
        mutable_ops = float(max(0, int(m.get("mutable_ops", 0) or 0)))
        test_files = float(max(0, int(m.get("test_files", 0) or 0)))
        avg_fn = float(max(0.0, float(m.get("avg_function_lines", 0.0) or 0.0)))

        # X pressure: hard admissibility pressure.
        x = _clamp(syntax_fail / files)

        # T pressure: temporal/replay fragility.
        mutation_ratio = mutable_ops / functions
        long_fn_pressure = avg_fn / 120.0
        t = _clamp((0.65 * mutation_ratio) + (0.35 * long_fn_pressure))

        # N pressure: complexity + maintenance energy.
        branch_density = branches / functions
        size_factor = loc / 30000.0
        n = _clamp((0.55 * (branch_density / 10.0)) + (0.45 * size_factor))

        # B pressure: coupling and fanout stress.
        edge_density = imports_local / max(1.0, files * 3.0)
        hotspot_pressure = fanout_hotspots / files
        b = _clamp((0.70 * edge_density) + (0.30 * hotspot_pressure))

        # A pressure: steering friction (high when complex/coupled + low test grounding).
        test_penalty = 1.0 if test_files <= 0 else _clamp(0.5 / max(1.0, test_files))
        adaptive_surface = _clamp((classes + float(m.get("public_functions", 0) or 0)) / max(1.0, functions + (branches / 8.0)))
        a = _clamp((0.45 * n) + (0.30 * b) + (0.25 * test_penalty) + (0.10 * (1.0 - adaptive_surface)))

        return CodePressureVec(X=x, T=t, N=n, B=b, A=a)


class CodeEvolutionChamber:
    """Constraint-native evolutionary chamber for code-level mutations."""

    def __init__(
        self,
        repo_root: str,
        output_dir: Optional[str] = None,
        config: Optional[CodeEvolutionConfig] = None,
    ):
        self.repo_root = os.path.abspath(repo_root)
        self.output_dir = os.path.abspath(output_dir or os.path.join(self.repo_root, "aurora_runtime_output", "code_evolution"))
        self.cfg = config or CodeEvolutionConfig()
        self.evaluator = CodeConstraintEvaluator(repo_root=self.repo_root)
        self.tick_count: int = 0
        self.relief_event_count: int = 0
        self.accepted_count: int = 0
        self.rejected_count: int = 0
        self.links_promoted: int = 0
        self._pair_counts: Dict[Tuple[str, str], int] = {}
        self._pair_stats: Dict[Tuple[str, str], Dict[str, float]] = {}
        self.links: Dict[str, CodeLink] = {}
        self._mutation_lineage: Dict[str, Dict[str, Any]] = {}
        self._lineage_children: Dict[str, List[str]] = defaultdict(list)
        self._governor = CodePressureGovernor(self.cfg)
        self._operator_gradients: Dict[str, float] = {a: 0.0 for a in AXIS_ORDER}
        self._latest_pressure: Dict[str, float] = {a: 0.0 for a in AXIS_ORDER}
        self._latest_relief: Dict[str, float] = {a: 0.0 for a in AXIS_ORDER}
        self._latest_timing_feedback: Dict[str, float] = {
            "apply_duration_s": 0.0,
            "agency_time_credit": 0.0,
            "temporal_overhead_penalty": 0.0,
            "applied_time_difference_s": 0.0,
        }
        os.makedirs(self.output_dir, exist_ok=True)
        self._events_path = os.path.join(self.output_dir, "code_events.jsonl")
        self._summary_path = os.path.join(self.output_dir, "code_links.json")
        self.restore_report: Dict[str, Any] = self._restore_persisted_state()

    def _restore_persisted_state(self) -> Dict[str, Any]:
        """
        AURORA BUILD 648 EVOLUTIONARY INFRASTRUCTURE CLOSURE DIRECTIVE,
        Phase 2: flush_files() already persists mutation lineage
        ("lineage_nodes"/"lineage_children"), promoted links, pairing
        statistics, and operator gradients to code_links.json -- but a
        freshly constructed chamber previously always started with empty
        in-memory state and never read that file back. That silently
        broke automatic evolutionary parent acquisition across restart:
        a generation-two proposal against a target with an accepted
        generation-one ancestor from a PRIOR process would see no parent
        at all, because _mutation_lineage was empty in the new process.

        This does not guess or reconstruct ancestry -- it loads exactly
        what was persisted. Malformed/incomplete records are skipped
        individually (never silently substituted or repaired) so that
        whatever valid historical evidence exists is still recovered
        rather than the whole restore being abandoned over one bad entry.
        Rejected mutations are restored on equal footing with accepted
        ones -- restoration itself does not grant or revoke parentage;
        that is still decided solely by observe_mutation()'s "accepted"
        field on each restored record, exactly as it was when persisted.
        """
        report: Dict[str, Any] = {
            "attempted": False, "loaded": False, "reason": "",
            "restored_mutation_count": 0, "restored_link_count": 0,
            "skipped_mutation_entries": 0, "skipped_link_entries": 0,
        }
        if not os.path.exists(self._summary_path):
            report["reason"] = "no_persisted_file"
            return report
        report["attempted"] = True
        try:
            with open(self._summary_path, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
        except Exception as _aurora_boundary_exc:
            _aurora_record_exception_from_locals(
                locals(),
                module=__name__,
                operation="exception_handler:aurora_internal/aurora_code_evolution_chamber.py:_restore_persisted_state.read",
                exc=_aurora_boundary_exc,
                context={"function": "_restore_persisted_state", "source_file": "aurora_internal/aurora_code_evolution_chamber.py"},
            )
            report["reason"] = f"unreadable_or_malformed_json: {_aurora_boundary_exc}"
            return report
        if not isinstance(payload, dict):
            report["reason"] = "root_not_a_mapping"
            return report

        lineage_nodes = payload.get("lineage_nodes", {})
        if isinstance(lineage_nodes, dict):
            for mutation_id, rec in lineage_nodes.items():
                if not isinstance(rec, dict) or not str(mutation_id).strip():
                    report["skipped_mutation_entries"] += 1
                    continue
                self._mutation_lineage[str(mutation_id)] = dict(rec)
                report["restored_mutation_count"] += 1

        lineage_children = payload.get("lineage_children", {})
        if isinstance(lineage_children, dict):
            for parent_id, children in lineage_children.items():
                if not isinstance(children, list):
                    continue
                self._lineage_children[str(parent_id)] = [str(c) for c in children if str(c).strip()]

        links = payload.get("links", {})
        if isinstance(links, dict):
            for link_id, rec in links.items():
                if not isinstance(rec, dict):
                    report["skipped_link_entries"] += 1
                    continue
                try:
                    parents_raw = rec.get("parents", [])
                    self.links[str(link_id)] = CodeLink(
                        link_id=str(rec.get("link_id", link_id)),
                        parents=(str(parents_raw[0]), str(parents_raw[1])),
                        dominant_axis=str(rec.get("dominant_axis", "")),
                        semantic_lane=str(rec.get("semantic_lane", "")),
                        generation=int(rec.get("generation", 1) or 1),
                        support_count=int(rec.get("support_count", 0) or 0),
                        accepted_count=int(rec.get("accepted_count", 0) or 0),
                        acceptance_rate=float(rec.get("acceptance_rate", 0.0) or 0.0),
                        mean_net_benefit=float(rec.get("mean_net_benefit", 0.0) or 0.0),
                    )
                except Exception as _aurora_boundary_exc:
                    _aurora_record_exception_from_locals(
                        locals(),
                        module=__name__,
                        operation="exception_handler:aurora_internal/aurora_code_evolution_chamber.py:_restore_persisted_state.link",
                        exc=_aurora_boundary_exc,
                        context={"function": "_restore_persisted_state", "source_file": "aurora_internal/aurora_code_evolution_chamber.py"},
                    )
                    report["skipped_link_entries"] += 1

        pair_counts = payload.get("pair_counts", {})
        if isinstance(pair_counts, dict):
            for key, count in pair_counts.items():
                parts = str(key).split("|", 1)
                if len(parts) == 2:
                    self._pair_counts[(parts[0], parts[1])] = int(count or 0)

        pair_stats = payload.get("pair_stats", {})
        if isinstance(pair_stats, dict):
            for key, stats in pair_stats.items():
                parts = str(key).split("|", 1)
                if len(parts) == 2 and isinstance(stats, dict):
                    self._pair_stats[(parts[0], parts[1])] = {
                        "total": float(stats.get("total", 0.0) or 0.0),
                        "accepted": float(stats.get("accepted", 0.0) or 0.0),
                        "net_sum": float(stats.get("net_sum", 0.0) or 0.0),
                    }

        gradients = payload.get("operator_gradients", {})
        if isinstance(gradients, dict):
            for axis, val in gradients.items():
                if axis in self._operator_gradients:
                    self._operator_gradients[axis] = float(val or 0.0)

        summary = payload.get("summary", {})
        if isinstance(summary, dict):
            self.tick_count = int(summary.get("tick_count", self.tick_count) or 0)
            self.relief_event_count = int(summary.get("relief_events", self.relief_event_count) or 0)
            self.accepted_count = int(summary.get("accepted_count", self.accepted_count) or 0)
            self.rejected_count = int(summary.get("rejected_count", self.rejected_count) or 0)
            self.links_promoted = int(summary.get("links_promoted", self.links_promoted) or 0)

        report["loaded"] = True
        report["reason"] = "restored"
        return report

    def snapshot(self, target_files: Optional[Sequence[str]] = None) -> CodePressureSnapshot:
        return self.evaluator.snapshot(target_files=target_files)

    def propose_mutation(
        self,
        name: str,
        constraints_used: Iterable[str],
        target_files: Iterable[str],
        parent_ids: Optional[Iterable[str]] = None,
        meta: Optional[Dict[str, Any]] = None,
        function_lineage: Optional[Any] = None,
        exact_function_ids: Optional[Iterable[str]] = None,
        requested_operation_ids: Optional[Iterable[str]] = None,
    ) -> CodeMutationTrace:
        # AURORA BUILD 648 EVOLUTIONARY INFRASTRUCTURE CLOSURE DIRECTIVE,
        # Phase 3: exact_function_ids -- real UniversalFunctionLineage
        # function IDs the caller already knows are affected -- lets
        # ancestry acquisition target those operations precisely instead
        # of every function that happens to share their file (target_files
        # remains the coarse fallback scope, never removed).
        # requested_operation_ids carries opaque operation-descriptor
        # op_id/op_chain strings (e.g. from aurora_state/operation_descriptors.json)
        # purely as recorded evidence -- this module never maps them onto
        # UniversalFunctionLineage function IDs (no operational-homology
        # formula is invented here); they are evidence a caller who
        # already possesses that mapping can attach for its own future
        # inspection.
        cset = _normalize_constraints(constraints_used)
        if not cset:
            cset = frozenset({"existence", "temporal"})
        tfiles = tuple(sorted({str(x).strip() for x in (target_files or []) if str(x).strip()}))
        explicit_parents = tuple(sorted({str(x).strip() for x in (parent_ids or []) if str(x).strip()}))
        exact_fids = tuple(sorted({str(x).strip() for x in (exact_function_ids or []) if str(x).strip()}))
        requested_op_ids = tuple(sorted({str(x).strip() for x in (requested_operation_ids or []) if str(x).strip()}))

        # AURORA BUILD 646 GENEALOGY-TO-EVOLUTION CLOSURE DIRECTIVE,
        # Requirement 2.2/2.3: when the caller can supply Aurora's real
        # operational lineage (function_lineage) and did not explicitly
        # supply parent_ids, acquire real evolutionary ancestry from prior
        # ACCEPTED mutations against the same target rather than starting
        # from a bare generation-1 proposal. Explicit parent_ids, when
        # given, are never overridden. Absence of any prior evidence is
        # left as-is (empty parents, generation 1) -- nothing is invented.
        acquired_ancestry = None
        lineage_pressure = None
        parents = explicit_parents
        if function_lineage is not None:
            try:
                from aurora_internal.aurora_evolutionary_ancestry_bridge import (
                    acquire_ancestry_for_target, auto_parent_ids, lineage_scoped_pressure,
                )
                acquired_ancestry = acquire_ancestry_for_target(
                    function_lineage=function_lineage,
                    mutation_lineage=self._mutation_lineage,
                    target_files=tfiles,
                    repo_root=self.repo_root,
                    exact_function_ids=exact_fids,
                )
                if not explicit_parents:
                    parents = tuple(sorted(auto_parent_ids(acquired_ancestry, explicit_parents)))
                # Requirement 4.1: repeated failure among the target's
                # operational DESCENDANTS is scoped evidence too, not just
                # exact-file rejections -- kept as its own decomposable
                # evidence dict (Phase 9), never collapsed into a decision.
                lineage_pressure = lineage_scoped_pressure(
                    function_lineage=function_lineage,
                    mutation_lineage=self._mutation_lineage,
                    target_files=tfiles,
                    repo_root=self.repo_root,
                )
            except Exception as _aurora_boundary_exc:
                _aurora_record_exception_from_locals(
                    locals(),
                    module=__name__,
                    operation="exception_handler:aurora_internal/aurora_code_evolution_chamber.py:propose_mutation.ancestry",
                    exc=_aurora_boundary_exc,
                    context={"function": "propose_mutation", "source_file": "aurora_internal/aurora_code_evolution_chamber.py"},
                )
                acquired_ancestry = None
                lineage_pressure = None

        raw = f"{name}|{','.join(sorted(cset))}|{','.join(tfiles)}|{','.join(parents)}|{time.time_ns()}"
        mutation_id = "CMUT:" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
        payload = dict(meta or {})
        primary_label = sorted(cset)[0]
        payload.setdefault("operator_action", _operator_action_for_axis(LABEL_TO_AXIS.get(primary_label, "X")))
        payload.setdefault("lineage_source", "code_evolution_chamber")
        combo = "+".join(sorted(cset))
        lineage_raw = f"{name}|{combo}|{'|'.join(parents)}"
        lineage_id = "OP:" + hashlib.sha1(lineage_raw.encode("utf-8")).hexdigest()[:12]
        payload.setdefault("constraint_ancestry", sorted(cset))
        payload.setdefault("constraint_combo_id", combo or "none")
        payload.setdefault("operation_lineage_id", lineage_id)
        payload.setdefault("parent_lineage_ids", list(parents))
        payload.setdefault("explicit_parent_ids", list(explicit_parents))
        parent_gens = [
            int((self._mutation_lineage.get(pid, {}) or {}).get("generation", 1) or 1)
            for pid in parents
        ]
        generation = max(parent_gens) + 1 if parent_gens else 1
        payload.setdefault("lineage_generation", int(generation))
        if acquired_ancestry is not None:
            # Requirement 2.1: kept as a separate, richer view rather than
            # collapsed into parent_ids -- operational ancestry, constraint
            # signature, descendant fan-out, and rejected-attempt history
            # all remain independently inspectable.
            payload.setdefault("acquired_operational_ancestry", acquired_ancestry.to_dict())
        if lineage_pressure is not None:
            payload.setdefault("lineage_scoped_pressure", lineage_pressure)
        # AURORA BUILD 648 EVOLUTIONARY INFRASTRUCTURE CLOSURE DIRECTIVE,
        # Phase 3: recorded regardless of whether function_lineage was
        # supplied -- these are the requested-scope facts, independent of
        # whether ancestry acquisition could run. "requested_target_files"
        # intentionally mirrors target_files at proposal time (before any
        # actual-vs-planned divergence, which Phase 4 reconciles once the
        # real changed-file set is known post-application).
        payload.setdefault("requested_target_files", list(tfiles))
        payload.setdefault("requested_operation_ids", list(requested_op_ids))
        payload.setdefault("exact_function_ids", list(exact_fids))
        payload.setdefault(
            "mutation_scope_kind",
            "exact" if (acquired_ancestry is not None and acquired_ancestry.ancestry_scope == "exact")
            else ("exact_unresolved" if exact_fids else "file_level_fallback"),
        )
        return CodeMutationTrace(
            mutation_id=mutation_id,
            name=str(name),
            constraints_used=frozenset(cset),
            target_files=tfiles,
            parent_ids=parents,
            meta=payload,
        )

    def observe_mutation(
        self,
        trace: CodeMutationTrace,
        before: CodePressureSnapshot,
        after: CodePressureSnapshot,
        checks_passed: bool,
        notes: Optional[Dict[str, Any]] = None,
        system_before: Optional[CodePressureSnapshot] = None,
        system_after: Optional[CodePressureSnapshot] = None,
    ) -> Dict[str, Any]:
        self.tick_count += 1
        relief = after.pressure.relief_from(before.pressure)
        relief_dict = relief.to_dict()
        operator_key = str((trace.meta or {}).get("operator_key", "")).strip().lower() or "__unknown__"
        timing_feedback = self._timing_feedback_payload(notes)
        governor_before = self._governor.report()
        tol_factor = self._governor.tolerance_factor(operator_key)
        eps, total_eps = self._governor.effective_relief_thresholds(
            base_eps=float(self.cfg.relief_eps),
            base_total=float(self.cfg.relief_total_eps),
        )
        is_relief = (
            relief.max_relief() >= float(eps)
            or (relief.sum_positive_relief() * tol_factor) >= float(total_eps)
        )
        if is_relief:
            self.relief_event_count += 1

        admissible_x = (
            float(after.pressure.X) <= float(self.cfg.x_risk_max)
            and float(after.pressure.X) <= float(before.pressure.X) + float(self.cfg.x_growth_allowance)
        )
        mutation_cost = self._mutation_cost(
            trace=trace,
            before=before.pressure,
            after=after.pressure,
            operator_key=operator_key,
            timing_feedback=timing_feedback,
        )
        effective_net_min = self._governor.effective_net_min(float(self.cfg.net_min))
        net_benefit = float(relief.sum_positive_relief() * tol_factor) - (
            float(self.cfg.cost_penalty_lambda) * float(self.cfg.cost_to_relief_scale) * float(mutation_cost)
        )
        net_benefit += (0.08 * float(timing_feedback.get("agency_time_credit", 0.0) or 0.0))
        net_benefit -= (0.06 * float(timing_feedback.get("temporal_overhead_penalty", 0.0) or 0.0))
        accepted = bool(checks_passed and admissible_x and is_relief and net_benefit >= float(effective_net_min))
        effective_history = self._build_effective_history(
            trace=trace,
            before=before,
            after=after,
            system_before=(system_before or before),
            system_after=(system_after or after),
            relief=relief,
            accepted=accepted,
            checks_passed=checks_passed,
            admissible_x=admissible_x,
            net_benefit=net_benefit,
            mutation_cost=mutation_cost,
            governor_before=governor_before,
            notes=notes,
        )
        self._promote_links_with_stats(trace=trace, accepted=accepted, net_benefit=net_benefit)
        self._governor.update_after_event(operator_key=operator_key, accepted=accepted)
        self._update_operator_gradients(before=before.pressure, after=after.pressure, relief=relief_dict, timing_feedback=timing_feedback)
        if accepted:
            self.accepted_count += 1
        else:
            self.rejected_count += 1

        lineage_payload = {
            "mutation_id": str(trace.mutation_id),
            "lineage_id": str((trace.meta or {}).get("operation_lineage_id", "")),
            "parents": list(getattr(trace, "parent_ids", tuple()) or tuple()),
            "generation": int((trace.meta or {}).get("lineage_generation", 1) or 1),
            "constraint_combo_id": str((trace.meta or {}).get("constraint_combo_id", "")),
            "constraints": sorted(set(getattr(trace, "constraints_used", frozenset()) or frozenset())),
            "accepted": bool(accepted),
            "net_benefit": float(net_benefit),
            "relief": relief.to_dict(),
            "timestamp": float(time.time()),
            "history": effective_history,
            # AURORA BUILD 646 GENEALOGY-TO-EVOLUTION CLOSURE DIRECTIVE,
            # Requirement 2.2: without this, acquire_ancestry_for_target()
            # (aurora_internal/aurora_evolutionary_ancestry_bridge.py) has
            # no way to find prior accepted/rejected mutations against the
            # same target files -- additive field, does not change any
            # existing consumer of this dict.
            "target_files": list(getattr(trace, "target_files", tuple()) or tuple()),
        }
        self._mutation_lineage[str(trace.mutation_id)] = lineage_payload
        for pid in lineage_payload["parents"]:
            self._lineage_children[str(pid)].append(str(trace.mutation_id))

        rec = {
            "tick": int(self.tick_count),
            "timestamp": float(time.time()),
            "trace": trace.to_dict(),
            "checks_passed": bool(checks_passed),
            "accepted": bool(accepted),
            "is_relief_event": bool(is_relief),
            "admissible_x": bool(admissible_x),
            "net_benefit": float(net_benefit),
            "mutation_cost": float(mutation_cost),
            "tolerance_factor": float(tol_factor),
            "effective_relief_eps": float(eps),
            "effective_relief_total_eps": float(total_eps),
            "effective_net_min": float(effective_net_min),
            "pressure_before": before.pressure.to_dict(),
            "pressure_after": after.pressure.to_dict(),
            "relief": relief.to_dict(),
            "effective_history": effective_history,
            "notes": dict(notes or {}),
        }
        with open(self._events_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=True) + "\n")
        self.flush_files()
        return rec

    def evaluate_mutation(
        self,
        trace: CodeMutationTrace,
        before: CodePressureSnapshot,
        checks_passed: bool,
        notes: Optional[Dict[str, Any]] = None,
        system_before: Optional[CodePressureSnapshot] = None,
        system_after: Optional[CodePressureSnapshot] = None,
    ) -> Dict[str, Any]:
        after = self.snapshot(target_files=list(trace.target_files) or None)
        return self.observe_mutation(
            trace=trace,
            before=before,
            after=after,
            checks_passed=checks_passed,
            notes=notes,
            system_before=system_before,
            system_after=system_after,
        )

    def _timing_feedback_payload(self, notes: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        payload = dict((notes or {}).get("timing_feedback", {}) or {})
        return {
            "apply_duration_s": float(payload.get("apply_duration_s", 0.0) or 0.0),
            "agency_time_credit": max(0.0, min(1.0, float(payload.get("agency_time_credit", 0.0) or 0.0))),
            "temporal_overhead_penalty": max(0.0, min(1.0, float(payload.get("temporal_overhead_penalty", 0.0) or 0.0))),
            "applied_time_difference_s": max(0.0, float(payload.get("applied_time_difference_s", 0.0) or 0.0)),
        }

    def _mutation_cost(self, trace: CodeMutationTrace, before: CodePressureVec, after: CodePressureVec, operator_key: str = "", timing_feedback: Optional[Dict[str, float]] = None) -> float:
        deltas = {
            "X": abs(float(after.X) - float(before.X)),
            "T": abs(float(after.T) - float(before.T)),
            "N": abs(float(after.N) - float(before.N)),
            "B": abs(float(after.B) - float(before.B)),
            "A": abs(float(after.A) - float(before.A)),
        }
        base = 0.0
        used_axes = {LABEL_TO_AXIS.get(lbl, "") for lbl in trace.constraints_used}
        used_axes = {a for a in used_axes if a in AXIS_ORDER}
        if not used_axes:
            used_axes = {"X", "T"}
        for ax in used_axes:
            grad = abs(float(self._operator_gradients.get(ax, 0.0) or 0.0))
            grad_factor = 1.0 + min(0.75, grad)
            base += float(self.cfg.operation_cost.get(ax, 1.0)) * float(deltas.get(ax, 0.0)) * grad_factor
        # Operator-specific inertia: stale/overused operators pay more.
        if operator_key:
            tol = 1.0 - self._governor.tolerance_factor(operator_key)
            base *= (1.0 + min(0.60, max(0.0, tol)))
        timing = dict(timing_feedback or {})
        agency_credit = max(0.0, min(1.0, float(timing.get("agency_time_credit", 0.0) or 0.0)))
        temporal_penalty = max(0.0, min(1.0, float(timing.get("temporal_overhead_penalty", 0.0) or 0.0)))
        if agency_credit > 0.0 or temporal_penalty > 0.0:
            base *= (1.0 - (0.22 * agency_credit))
            base *= (1.0 + (0.30 * temporal_penalty))
        return float(base) / float(max(1, len(used_axes)))

    def _promote_links(self, trace: CodeMutationTrace) -> None:
        self._promote_links_with_stats(trace=trace, accepted=True, net_benefit=0.0)

    def _promote_links_with_stats(self, trace: CodeMutationTrace, accepted: bool, net_benefit: float) -> None:
        ids = [str(x) for x in trace.parent_ids if str(x)]
        if len(ids) < 2:
            return
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                key = tuple(sorted((ids[i], ids[j])))
                self._pair_counts[key] = int(self._pair_counts.get(key, 0)) + 1
                st = dict(self._pair_stats.get(key, {}) or {})
                st["total"] = float(st.get("total", 0.0)) + 1.0
                st["accepted"] = float(st.get("accepted", 0.0)) + (1.0 if accepted else 0.0)
                st["net_sum"] = float(st.get("net_sum", 0.0)) + float(net_benefit)
                self._pair_stats[key] = st

                support_count = int(self._pair_counts[key])
                accepted_count = int(st.get("accepted", 0.0) or 0.0)
                total_count = int(st.get("total", 0.0) or 0.0)
                acceptance_rate = float(accepted_count) / float(max(1, total_count))
                mean_net = float(st.get("net_sum", 0.0) or 0.0) / float(max(1, total_count))
                effective_kmin = int(self._governor.effective_kmin(int(self.cfg.k_min)))
                effective_accept_floor = float(self._governor.effective_acceptance_floor(0.45))
                if support_count >= effective_kmin and acceptance_rate >= effective_accept_floor and mean_net >= 0.0:
                    existing = {tuple(sorted(v.parents)) for v in self.links.values()}
                    if key in existing:
                        continue
                    link_id = f"CLINK_{len(self.links):05d}"
                    dom_axis = "X"
                    if trace.constraints_used:
                        first = sorted(trace.constraints_used)[0]
                        dom_axis = LABEL_TO_AXIS.get(first, "X")
                    parent_gens = [
                        int((self._mutation_lineage.get(pid, {}) or {}).get("generation", 1) or 1)
                        for pid in key
                    ]
                    generation = max(parent_gens) + 1 if parent_gens else 1
                    self.links[link_id] = CodeLink(
                        link_id=link_id,
                        parents=key,
                        dominant_axis=dom_axis,
                        semantic_lane=self._semantic_lane_for_axis(dom_axis),
                        generation=int(generation),
                        support_count=support_count,
                        accepted_count=accepted_count,
                        acceptance_rate=acceptance_rate,
                        mean_net_benefit=mean_net,
                    )
                    self.links_promoted += 1
                    self._governor.register_promotion(self.tick_count)

    def _semantic_lane_for_axis(self, axis: str) -> str:
        a = str(axis or "X").upper()
        if a in {"X", "N"}:
            return "existence_intelligence"
        if a in {"T", "B"}:
            return "communication_coherence"
        return "agency_meaning"

    def _target_scope(self, trace: CodeMutationTrace) -> Dict[str, List[str]]:
        files = [str(x) for x in getattr(trace, "target_files", tuple()) if str(x).strip()]
        modules = sorted({self.evaluator._module_key_for_path(path) for path in files})
        subsystems = sorted({self.evaluator._subsystem_key_for_path(path) for path in files})
        return {
            "files": sorted(files),
            "modules": modules,
            "subsystems": subsystems,
        }

    def _rank_axes(self, values: Dict[str, float], limit: int = 3) -> List[Dict[str, Any]]:
        ranked = sorted(
            ((str(ax), float(val)) for ax, val in (values or {}).items()),
            key=lambda kv: abs(float(kv[1])),
            reverse=True,
        )[:max(0, int(limit))]
        return [{"axis": ax, "value": _rounded(val, 6)} for ax, val in ranked]

    def _pressure_transition(
        self,
        before: CodePressureVec,
        after: CodePressureVec,
        relief: Optional[CodePressureVec] = None,
    ) -> Dict[str, Any]:
        before_dict = before.to_dict()
        after_dict = after.to_dict()
        relief_dict = relief.to_dict() if relief is not None else after.relief_from(before).to_dict()
        delta_dict = {
            ax: float(after_dict.get(ax, 0.0)) - float(before_dict.get(ax, 0.0))
            for ax in AXIS_ORDER
        }
        return {
            "before": {ax: _rounded(before_dict.get(ax, 0.0), 6) for ax in AXIS_ORDER},
            "after": {ax: _rounded(after_dict.get(ax, 0.0), 6) for ax in AXIS_ORDER},
            "delta": {ax: _rounded(delta_dict.get(ax, 0.0), 6) for ax in AXIS_ORDER},
            "relief": {ax: _rounded(relief_dict.get(ax, 0.0), 6) for ax in AXIS_ORDER},
            "top_before_axes": self._rank_axes(before_dict),
            "top_delta_axes": self._rank_axes(delta_dict),
            "top_relief_axes": self._rank_axes(relief_dict),
        }

    def _metric_deltas(self, before_metrics: Dict[str, Any], after_metrics: Dict[str, Any]) -> Dict[str, Any]:
        tracked = (
            "files",
            "loc",
            "syntax_failures",
            "functions",
            "public_functions",
            "classes",
            "branches",
            "imports_local",
            "fanout_hotspots",
            "mutable_ops",
            "test_files",
            "avg_function_lines",
        )
        delta: Dict[str, Any] = {}
        for key in tracked:
            before_val = before_metrics.get(key, 0.0)
            after_val = after_metrics.get(key, 0.0)
            try:
                change = float(after_val) - float(before_val)
            except Exception as _aurora_boundary_exc:
                _aurora_record_exception_from_locals(
                    locals(),
                    module=__name__,
                    operation="exception_handler:aurora_internal/aurora_code_evolution_chamber.py:920",
                    exc=_aurora_boundary_exc,
                    context={"function": "_metric_deltas", "handler_line": 920, "source_file": "aurora_internal/aurora_code_evolution_chamber.py"},
                )
                continue
            if abs(change) <= 1e-9:
                continue
            if isinstance(before_val, int) and isinstance(after_val, int):
                delta[key] = int(round(change))
            else:
                delta[key] = _rounded(change, 6)
        return delta

    def _group_deltas(
        self,
        before_groups: Dict[str, Dict[str, float]],
        after_groups: Dict[str, Dict[str, float]],
        scope_keys: Optional[Iterable[str]] = None,
        limit: int = 8,
    ) -> List[Dict[str, Any]]:
        names = set(before_groups.keys()) | set(after_groups.keys())
        if scope_keys is not None:
            names = names | {str(x) for x in scope_keys if str(x).strip()}

        changes: List[Dict[str, Any]] = []
        for name in names:
            before_vals = dict(before_groups.get(name, {}) or {})
            after_vals = dict(after_groups.get(name, {}) or {})
            if not before_vals and not after_vals:
                continue
            delta = {
                ax: float(after_vals.get(ax, 0.0)) - float(before_vals.get(ax, 0.0))
                for ax in AXIS_ORDER
            }
            magnitude = sum(abs(v) for v in delta.values())
            if magnitude <= 1e-9:
                continue
            changes.append({
                "name": str(name),
                "magnitude": _rounded(magnitude, 6),
                "before": {ax: _rounded(before_vals.get(ax, 0.0), 6) for ax in AXIS_ORDER},
                "after": {ax: _rounded(after_vals.get(ax, 0.0), 6) for ax in AXIS_ORDER},
                "delta": {ax: _rounded(delta.get(ax, 0.0), 6) for ax in AXIS_ORDER},
                "top_delta_axes": self._rank_axes(delta, limit=2),
            })
        changes.sort(key=lambda rec: float(rec.get("magnitude", 0.0)), reverse=True)
        return changes[:max(0, int(limit))]

    def _ancestor_chain(self, mutation_id: str) -> List[str]:
        seen: set = set()
        ordered: List[str] = []

        def _walk(mid: str) -> None:
            node = dict(self._mutation_lineage.get(str(mid), {}) or {})
            for pid in list(node.get("parents", []) or []):
                pid_s = str(pid)
                if not pid_s or pid_s in seen:
                    continue
                seen.add(pid_s)
                ordered.append(pid_s)
                _walk(pid_s)

        _walk(str(mutation_id))
        return ordered

    def _ensure_growth_reflection_history(
        self,
        trace: CodeMutationTrace,
        history: Dict[str, Any],
    ) -> Dict[str, Any]:
        out = dict(history or {})
        scope = dict(out.get("target_scope", {}) or self._target_scope(trace))
        modules = [str(x) for x in (scope.get("modules", []) or []) if str(x).strip()]
        subsystems = [str(x) for x in (scope.get("subsystems", []) or []) if str(x).strip()]
        files = [str(x) for x in (scope.get("files", []) or []) if str(x).strip()]
        constraints = sorted(set(getattr(trace, "constraints_used", frozenset()) or frozenset()))
        growth_lineage = dict(out.get("growth_lineage", {}) or {})
        growth_lineage["mutation_id"] = str(growth_lineage.get("mutation_id", "") or getattr(trace, "mutation_id", ""))
        growth_lineage["lineage_source"] = str(growth_lineage.get("lineage_source", "") or (dict(trace.meta or {}).get("lineage_source", "") or "code_evolution_chamber"))
        growth_lineage["operator_key"] = str(growth_lineage.get("operator_key", "") or (dict(trace.meta or {}).get("operator_key", "") or ""))
        growth_lineage["constraint_combo_id"] = str(growth_lineage.get("constraint_combo_id", "") or (dict(trace.meta or {}).get("constraint_combo_id", "") or ""))
        growth_lineage["constraints"] = list(growth_lineage.get("constraints", []) or constraints)
        growth_lineage["target_scope"] = scope
        growth_lineage["target_kind"] = str(growth_lineage.get("target_kind", "") or "mutation")
        growth_lineage["present_in_system"] = True
        out["growth_lineage"] = growth_lineage

        ripple = dict(out.get("ripple_effects", {}) or {})
        ripple.setdefault("origin_module", modules[0] if modules else "")
        ripple.setdefault("origin_owner", subsystems[0] if subsystems else (modules[0] if modules else ""))
        ripple["propagated_modules"] = list(ripple.get("propagated_modules", []) or modules)
        ripple["propagated_subsystems"] = list(ripple.get("propagated_subsystems", []) or subsystems)
        ripple["cross_diversity_links"] = int(ripple.get("cross_diversity_links", 0) or max(1, len(modules) + len(subsystems)))
        ripple["derived_from_origin_descendants"] = int(ripple.get("derived_from_origin_descendants", 0) or max(1, len(files)))
        ripple.setdefault("growth_events", [{
            "stage": "mutation_observed",
            "operator_key": str(dict(trace.meta or {}).get("operator_key", "") or ""),
            "modules": list(modules),
            "subsystems": list(subsystems),
            "files": list(files),
        }])
        out["ripple_effects"] = ripple

        summary = dict(out.get("developmental_summary", {}) or {})
        effect_cls = str(((out.get("evolutionary_effects", {}) or {}).get("classification", "")) or "mutation_growth")
        summary["growth_reflected"] = True
        summary["system_reflection_required"] = True
        summary["effect_classification"] = effect_cls
        summary["system_impact_score"] = float(summary.get("system_impact_score", 0.0) or min(1.0, (0.18 * len(modules)) + (0.12 * len(subsystems)) + (0.06 * len(constraints))))
        summary["reflection_strength"] = float(summary.get("reflection_strength", 0.0) or min(1.0, 0.25 + (0.08 * len(files))))
        out["developmental_summary"] = summary
        return out

    def _collect_descendants(self, mutation_id: str) -> List[str]:
        seen: set = set()
        stack = list(self._lineage_children.get(str(mutation_id), []) or [])
        ordered: List[str] = []
        while stack:
            child = str(stack.pop())
            if child in seen:
                continue
            seen.add(child)
            ordered.append(child)
            stack.extend(list(self._lineage_children.get(child, []) or []))
        return ordered

    def _lineage_ripple(self, mutation_id: str) -> Dict[str, Any]:
        descendants = self._collect_descendants(mutation_id)
        accepted = 0
        net_total = 0.0
        modules: Dict[str, int] = defaultdict(int)
        subsystems: Dict[str, int] = defaultdict(int)
        for did in descendants:
            node = dict(self._mutation_lineage.get(did, {}) or {})
            if bool(node.get("accepted", False)):
                accepted += 1
            net_total += float(node.get("net_benefit", 0.0) or 0.0)
            history = dict(node.get("history", {}) or {})
            system_delta = dict((history.get("system_delta") or {}))
            for rec in list(system_delta.get("module_pressure_delta", []) or []):
                name = str(rec.get("name", "")).strip()
                if name:
                    modules[name] += 1
            for rec in list(system_delta.get("subsystem_pressure_delta", []) or []):
                name = str(rec.get("name", "")).strip()
                if name:
                    subsystems[name] += 1

        def _top_counts(counts: Dict[str, int]) -> List[Dict[str, Any]]:
            ranked = sorted(counts.items(), key=lambda kv: (-int(kv[1]), str(kv[0])))[:5]
            return [{"name": str(name), "hits": int(hits)} for name, hits in ranked]

        total = len(descendants)
        return {
            "descendant_count": int(total),
            "accepted_descendant_count": int(accepted),
            "descendant_acceptance_rate": _rounded(float(accepted) / float(max(1, total)), 6),
            "descendant_net_benefit_sum": _rounded(net_total, 6),
            "propagated_modules": _top_counts(modules),
            "propagated_subsystems": _top_counts(subsystems),
        }

    def _effect_classification(
        self,
        accepted: bool,
        checks_passed: bool,
        admissible_x: bool,
        net_benefit: float,
        relief: CodePressureVec,
        system_relief: CodePressureVec,
    ) -> str:
        if not bool(checks_passed):
            return "blocked_by_checks"
        if not bool(admissible_x):
            return "blocked_by_existence_risk"
        if bool(accepted) and float(net_benefit) > 0.0:
            if float(system_relief.sum_positive_relief()) > 0.0:
                return "stabilizing_system_adaptation"
            return "accepted_local_adaptation"
        if float(relief.sum_positive_relief()) <= 0.0:
            return "no_relief_regression"
        if float(net_benefit) < 0.0:
            return "relief_outweighed_by_cost"
        return "contained_nonpromotion"

    def _build_effective_history(
        self,
        trace: CodeMutationTrace,
        before: CodePressureSnapshot,
        after: CodePressureSnapshot,
        system_before: CodePressureSnapshot,
        system_after: CodePressureSnapshot,
        relief: CodePressureVec,
        accepted: bool,
        checks_passed: bool,
        admissible_x: bool,
        net_benefit: float,
        mutation_cost: float,
        governor_before: Dict[str, Any],
        notes: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        system_relief = system_after.pressure.relief_from(system_before.pressure)
        target_scope = self._target_scope(trace)
        target_modules = target_scope.get("modules", [])
        target_subsystems = target_scope.get("subsystems", [])
        target_files = target_scope.get("files", [])
        ancestor_chain = self._ancestor_chain(str(trace.mutation_id))
        parent_generations = [
            int((self._mutation_lineage.get(pid, {}) or {}).get("generation", 1) or 1)
            for pid in list(getattr(trace, "parent_ids", tuple()) or tuple())
        ]
        history = {
            "target_scope": target_scope,
            "required_system_state": {
                "parent_lineages": list(getattr(trace, "parent_ids", tuple()) or tuple()),
                "ancestor_chain": ancestor_chain,
                "max_parent_generation": int(max(parent_generations) if parent_generations else 0),
                "governor_before": dict(governor_before or {}),
                "target_pressure_before": self._pressure_transition(before.pressure, before.pressure, relief=CodePressureVec()),
                "system_pressure_before": self._pressure_transition(system_before.pressure, system_before.pressure, relief=CodePressureVec()),
            },
            "target_delta": {
                "pressure": self._pressure_transition(before.pressure, after.pressure, relief=relief),
                "metric_delta": self._metric_deltas(dict(before.metrics or {}), dict(after.metrics or {})),
                "file_pressure_delta": self._group_deltas(
                    dict((before.metrics or {}).get("file_pressures", {}) or {}),
                    dict((after.metrics or {}).get("file_pressures", {}) or {}),
                    scope_keys=target_files,
                    limit=max(3, len(target_files) or 1),
                ),
            },
            "system_delta": {
                "pressure": self._pressure_transition(system_before.pressure, system_after.pressure, relief=system_relief),
                "metric_delta": self._metric_deltas(dict(system_before.metrics or {}), dict(system_after.metrics or {})),
                "module_pressure_delta": self._group_deltas(
                    dict((system_before.metrics or {}).get("module_pressures", {}) or {}),
                    dict((system_after.metrics or {}).get("module_pressures", {}) or {}),
                    scope_keys=target_modules,
                ),
                "subsystem_pressure_delta": self._group_deltas(
                    dict((system_before.metrics or {}).get("subsystem_pressures", {}) or {}),
                    dict((system_after.metrics or {}).get("subsystem_pressures", {}) or {}),
                    scope_keys=target_subsystems,
                ),
            },
            "evolutionary_effects": {
                "classification": self._effect_classification(
                    accepted=accepted,
                    checks_passed=checks_passed,
                    admissible_x=admissible_x,
                    net_benefit=net_benefit,
                    relief=relief,
                    system_relief=system_relief,
                ),
                "accepted": bool(accepted),
                "checks_passed": bool(checks_passed),
                "admissible_x": bool(admissible_x),
                "net_benefit": _rounded(net_benefit, 6),
                "mutation_cost": _rounded(mutation_cost, 6),
                "target_relief_total": _rounded(relief.sum_positive_relief(), 6),
                "system_relief_total": _rounded(system_relief.sum_positive_relief(), 6),
                "operator_key": str((trace.meta or {}).get("operator_key", "") or ""),
                "constraint_combo_id": str((trace.meta or {}).get("constraint_combo_id", "") or ""),
            },
        }
        if isinstance(notes, dict) and notes:
            history["notes"] = {
                k: v
                for k, v in dict(notes).items()
                if k not in {"system_before_snapshot", "system_after_snapshot"}
            }
        return self._ensure_growth_reflection_history(trace, history)

    def summary(self) -> Dict[str, Any]:
        deepest_generation = 0
        accepted_lineages = 0
        ripple_roots = 0
        for rec in self._mutation_lineage.values():
            deepest_generation = max(deepest_generation, int(rec.get("generation", 1) or 1))
            if bool(rec.get("accepted", False)):
                accepted_lineages += 1
        for mutation_id in self._mutation_lineage.keys():
            if self._lineage_children.get(str(mutation_id)):
                ripple_roots += 1
        return {
            "repo_root": self.repo_root,
            "tick_count": int(self.tick_count),
            "relief_events": int(self.relief_event_count),
            "accepted_count": int(self.accepted_count),
            "rejected_count": int(self.rejected_count),
            "links_promoted": int(self.links_promoted),
            "total_links": int(len(self.links)),
            "lineage_nodes": int(len(self._mutation_lineage)),
            "lineage_deepest_generation": int(deepest_generation),
            "lineage_accepted_nodes": int(accepted_lineages),
            "lineage_ripple_roots": int(ripple_roots),
            "operator_gradients": {k: float(v) for k, v in self._operator_gradients.items()},
            "governor": self._governor.report(),
            "events_file": self._events_path,
        }

    def lineage_report(self) -> Dict[str, Any]:
        sample_raw = sorted(
            self._mutation_lineage.values(),
            key=lambda r: float(r.get("timestamp", 0.0)),
            reverse=True,
        )[:12]
        sample: List[Dict[str, Any]] = []
        ripple_ranked: List[Dict[str, Any]] = []
        for rec in self._mutation_lineage.values():
            mutation_id = str(rec.get("mutation_id", "") or "")
            ripple = self._lineage_ripple(mutation_id)
            ripple_ranked.append({
                "mutation_id": mutation_id,
                "lineage_id": str(rec.get("lineage_id", "") or ""),
                "generation": int(rec.get("generation", 1) or 1),
                "accepted": bool(rec.get("accepted", False)),
                "descendant_count": int(ripple.get("descendant_count", 0) or 0),
                "descendant_acceptance_rate": _rounded(ripple.get("descendant_acceptance_rate", 0.0), 6),
                "propagated_modules": list(ripple.get("propagated_modules", []) or []),
                "propagated_subsystems": list(ripple.get("propagated_subsystems", []) or []),
            })
        ripple_ranked.sort(
            key=lambda rec: (
                int(rec.get("descendant_count", 0) or 0),
                float(rec.get("descendant_acceptance_rate", 0.0) or 0.0),
                int(rec.get("generation", 1) or 1),
            ),
            reverse=True,
        )
        for rec in sample_raw:
            mutation_id = str(rec.get("mutation_id", "") or "")
            enriched = dict(rec)
            enriched["ancestor_chain"] = self._ancestor_chain(mutation_id)
            enriched["history"] = self._ensure_growth_reflection_history(
                CodeMutationTrace(
                    mutation_id=mutation_id,
                    name=str((rec.get("history", {}) or {}).get("growth_lineage", {}).get("operator_key", "") or mutation_id),
                    constraints_used=frozenset(rec.get("constraints", []) or []),
                    target_files=tuple(((rec.get("history", {}) or {}).get("target_scope", {}) or {}).get("files", []) or []),
                    parent_ids=tuple(rec.get("parents", []) or []),
                    meta={"operator_key": str((rec.get("history", {}) or {}).get("growth_lineage", {}).get("operator_key", "") or "")},
                ),
                dict(rec.get("history", {}) or {}),
            )
            ripple = dict(self._lineage_ripple(mutation_id) or {})
            hist_ripple = dict((enriched.get("history", {}) or {}).get("ripple_effects", {}) or {})
            merged_ripple = dict(hist_ripple)
            merged_ripple.update(ripple)
            enriched["ripple_effects"] = merged_ripple
            sample.append(enriched)
        return {
            "nodes": int(len(self._mutation_lineage)),
            "edges": int(sum(len(v) for v in self._lineage_children.values())),
            "children_roots": int(len(self._lineage_children)),
            "recent": sample,
            "top_ripple_roots": ripple_ranked[:10],
        }

    def flush_files(self) -> None:
        lineage_nodes: Dict[str, Dict[str, Any]] = {}
        for mutation_id, rec in self._mutation_lineage.items():
            node = dict(rec or {})
            node["history"] = self._ensure_growth_reflection_history(
                CodeMutationTrace(
                    mutation_id=str(mutation_id),
                    name=str(node.get("mutation_id", "") or mutation_id),
                    constraints_used=frozenset(node.get("constraints", []) or []),
                    target_files=tuple(((node.get("history", {}) or {}).get("target_scope", {}) or {}).get("files", []) or []),
                    parent_ids=tuple(node.get("parents", []) or []),
                    meta={
                        "operator_key": str((((node.get("history", {}) or {}).get("growth_lineage", {}) or {}).get("operator_key", "") or "")),
                        "lineage_source": str((((node.get("history", {}) or {}).get("growth_lineage", {}) or {}).get("lineage_source", "") or "code_evolution_chamber")),
                        "constraint_combo_id": str(node.get("constraint_combo_id", "") or ""),
                    },
                ),
                dict(node.get("history", {}) or {}),
            )
            lineage_nodes[str(mutation_id)] = node
        payload = {
            "summary": self.summary(),
            "links": {k: v.to_dict() for k, v in self.links.items()},
            "pair_counts": {f"{a}|{b}": int(v) for (a, b), v in self._pair_counts.items()},
            "pair_stats": {
                f"{a}|{b}": {
                    "total": float((self._pair_stats.get((a, b), {}) or {}).get("total", 0.0)),
                    "accepted": float((self._pair_stats.get((a, b), {}) or {}).get("accepted", 0.0)),
                    "net_sum": float((self._pair_stats.get((a, b), {}) or {}).get("net_sum", 0.0)),
                }
                for (a, b) in self._pair_counts.keys()
            },
            "lineage": self.lineage_report(),
            "lineage_nodes": lineage_nodes,
            "lineage_children": {k: list(v) for k, v in self._lineage_children.items()},
            "operator_gradients": {k: float(v) for k, v in self._operator_gradients.items()},
            "latest_pressure": {k: float(v) for k, v in self._latest_pressure.items()},
            "latest_relief": {k: float(v) for k, v in self._latest_relief.items()},
            "latest_timing_feedback": {k: float(v) for k, v in self._latest_timing_feedback.items()},
            "governor": self._governor.report(),
        }
        with open(self._summary_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=True)

    def guidance_payload(self) -> Dict[str, Any]:
        """Cross-scale guidance payload compatible with runtime steering hook."""
        axis_vals = dict(self._latest_pressure or {})
        if not axis_vals:
            axis_vals = {a: 0.0 for a in AXIS_ORDER}
        ranked = sorted(axis_vals.items(), key=lambda kv: float(kv[1]), reverse=True)
        primary_ax, primary_v = ranked[0]
        secondary_ax, _ = ranked[1] if len(ranked) > 1 else ("T", 0.0)
        total = sum(max(0.0, float(v)) for v in axis_vals.values())
        score = (float(primary_v) / float(total)) if total > 0.0 else 0.0
        return {
            "score": float(score),
            "compare_value": float(primary_v),
            "primary_axis": str(primary_ax),
            "secondary_axis": str(secondary_ax),
            "operator_gradients": {k: float(v) for k, v in self._operator_gradients.items()},
            "timing_feedback": {k: float(v) for k, v in self._latest_timing_feedback.items()},
            "governor": self._governor.report(),
        }

    def _update_operator_gradients(self, before: CodePressureVec, after: CodePressureVec, relief: Dict[str, float], timing_feedback: Optional[Dict[str, float]] = None) -> None:
        alpha = float(self.cfg.gradient_alpha)
        b = before.to_dict()
        a = after.to_dict()
        timing = dict(timing_feedback or {})
        agency_credit = max(0.0, min(1.0, float(timing.get("agency_time_credit", 0.0) or 0.0)))
        temporal_penalty = max(0.0, min(1.0, float(timing.get("temporal_overhead_penalty", 0.0) or 0.0)))
        for ax in AXIS_ORDER:
            drift = float(a.get(ax, 0.0)) - float(b.get(ax, 0.0))
            rel = float(relief.get(ax, 0.0))
            signal = max(-1.0, min(1.0, drift - rel))
            if ax == "A":
                signal = max(-1.0, min(1.0, signal + (0.35 * agency_credit) - (0.15 * temporal_penalty)))
            elif ax == "T":
                signal = max(-1.0, min(1.0, signal - (0.30 * temporal_penalty) + (0.10 * agency_credit)))
            prev = float(self._operator_gradients.get(ax, 0.0) or 0.0)
            self._operator_gradients[ax] = ((1.0 - alpha) * prev) + (alpha * signal)
            self._latest_pressure[ax] = float(a.get(ax, 0.0))
            self._latest_relief[ax] = float(relief.get(ax, 0.0))
        self._latest_timing_feedback = {
            "apply_duration_s": float(timing.get("apply_duration_s", 0.0) or 0.0),
            "agency_time_credit": float(agency_credit),
            "temporal_overhead_penalty": float(temporal_penalty),
            "applied_time_difference_s": float(timing.get("applied_time_difference_s", 0.0) or 0.0),
        }

# AURORA_EVOLVED_NATIVE_BEGIN
try:
    import inspect as _aurora_native_inspect
except Exception as _aurora_boundary_exc:
    _aurora_record_exception_from_locals(
        locals(),
        module=__name__,
        operation="exception_handler:aurora_internal/aurora_code_evolution_chamber.py:1369",
        exc=_aurora_boundary_exc,
        context={"function": "<module>", "handler_line": 1369, "source_file": "aurora_internal/aurora_code_evolution_chamber.py"},
    )
    _aurora_native_inspect = None

try:
    from aurora_internal.aurora_evolved_surfaces import AuroraEvolvedSurfaceEngine as _AuroraEvolvedSurfaceEngine
except Exception as _aurora_boundary_exc:
    _aurora_record_exception_from_locals(
        locals(),
        module=__name__,
        operation="exception_handler:aurora_internal/aurora_code_evolution_chamber.py:1374",
        exc=_aurora_boundary_exc,
        context={"function": "<module>", "handler_line": 1374, "source_file": "aurora_internal/aurora_code_evolution_chamber.py"},
    )
    _AuroraEvolvedSurfaceEngine = None

_AURORA_NATIVE_EVOLVED_ENGINE = None

def _aurora_native_evolved_engine():
    global _AURORA_NATIVE_EVOLVED_ENGINE
    if _AURORA_NATIVE_EVOLVED_ENGINE is None and _AuroraEvolvedSurfaceEngine is not None:
        _AURORA_NATIVE_EVOLVED_ENGINE = _AuroraEvolvedSurfaceEngine()
    return _AURORA_NATIVE_EVOLVED_ENGINE

_AURORA_NATIVE_MODULE = 'aurora_internal.aurora_code_evolution_chamber'

_AURORA_NATIVE_EVOLVED_ORIGINALS = {}
_AURORA_NATIVE_EVOLVED_LAST = {}
_AURORA_NATIVE_STRATEGIES = {'CodeEvolutionChamber.develop_agency': {'ability_hits': 0,
                                         'alignment_gap': 0.0,
                                         'alignment_target_score': 0.0,
                                         'best_coupling_signature': '',
                                         'constraints': ['existence', 'temporal', 'agency'],
                                         'contract_profile': {'accepts_payload': False,
                                                              'async_callable': False,
                                                              'callable': False,
                                                              'class_target': False,
                                                              'constraint_density': 3,
                                                              'contract_mode': 'stateful',
                                                              'doc_hint': '',
                                                              'effect_density': 6,
                                                              'kwonly_args': 0,
                                                              'optional_args': 0,
                                                              'required_args': 0,
                                                              'return_hint': 'state_record',
                                                              'signature_text': '',
                                                              'stateful_owner': True,
                                                              'target_kind': 'latent_operation',
                                                              'varargs': False,
                                                              'varkw': False},
                                         'coupling_similarity': 0.0,
                                         'cross_diversity_links': 0,
                                         'effect_modes': ['state_schema_change',
                                                          'temporal_orchestration_change',
                                                          'stateful_surface_expansion',
                                                          'internal_subsystem_surface',
                                                          'latent_develop_surface',
                                                          'latent_a_derivative'],
                                         'effect_phrases': ['would extend agency pressure handling',
                                                            'would materialize the next descendant '
                                                            'implied by '
                                                            'aurora_internal.aurora_code_evolution_chamber.CodeEvolutionChamber'],
                                         'genealogy_pressure': 0.0,
                                         'inheritance_breach_count': 0,
                                         'kind': 'latent',
                                         'link_hits': 0,
                                         'module': 'aurora_internal.aurora_code_evolution_chamber',
                                         'op_id': 'latent.aurora_internal.aurora_code_evolution_chamber.CodeEvolutionChamber.develop_agency',
                                         'origin_activity': 0,
                                         'persistence_tax_factor': 0.0,
                                         'representation_score': 0.0,
                                         'rewrite_bias': 'generic',
                                         'rewrite_feedback': {'acceptance_rate': 0.0,
                                                              'accepted_count': 0,
                                                              'adaptation_mode': 'balanced',
                                                              'adoption_count': 0,
                                                              'confidence': 0.0,
                                                              'mean_mutation_score': 0.0,
                                                              'rejected_count': 0,
                                                              'rejection_rate': 0.0,
                                                              'timing_credit': 0.0,
                                                              'timing_penalty': 0.0,
                                                              'trial_count': 0},
                                         'rewrite_profile': 'generic',
                                         'signature': '',
                                         'surface_score': 1.0130625,
                                         'sustainability_score': 0.0,
                                         'target_kind': 'latent_operation'}}

from aurora_internal.aurora_evolution_hook import (
    assign_target as _aurora_evolution_hook_assign_target,
    get_target as _aurora_evolution_hook_get_target,
    bind_owner_attribute as _aurora_evolution_hook_bind_owner_attribute,
    target_strategy as _aurora_evolution_hook_target_strategy,
    target_feedback as _aurora_evolution_hook_target_feedback,
    store_reflection as _aurora_store_reflection,
    store_owner_state as _aurora_store_owner_state,
    apply_result_rewrite as _aurora_evolution_hook_apply_result_rewrite,
    make_override as _aurora_evolution_hook_make_override,
    make_latent_binding as _aurora_evolution_hook_make_latent_binding,
)


def _aurora_target_strategy(target_key):
    return _aurora_evolution_hook_target_strategy(_AURORA_NATIVE_STRATEGIES, target_key)


def _aurora_target_feedback(target_key):
    return _aurora_evolution_hook_target_feedback(_AURORA_NATIVE_STRATEGIES, target_key)


def _aurora_assign_target(chain, value):
    return _aurora_evolution_hook_assign_target(globals(), chain, value)


def _aurora_get_target(chain):
    return _aurora_evolution_hook_get_target(globals(), chain)


def _aurora_bind_owner_attribute(owner_chain, attr_name, value):
    return _aurora_evolution_hook_bind_owner_attribute(globals(), owner_chain, attr_name, value)


def _aurora_apply_result_rewrite(target_key, result, reflection, args, kwargs):
    return _aurora_evolution_hook_apply_result_rewrite(
        _AURORA_NATIVE_MODULE, _AURORA_NATIVE_STRATEGIES, target_key, result, reflection, args, kwargs,
    )


def _aurora_make_override(export_name, target_key):
    return _aurora_evolution_hook_make_override(
        globals(), _AURORA_NATIVE_EVOLVED_ORIGINALS, _AURORA_NATIVE_EVOLVED_LAST,
        _aurora_native_evolved_engine, _AURORA_NATIVE_MODULE, _AURORA_NATIVE_STRATEGIES,
        export_name, target_key,
    )


def _aurora_make_latent_binding(export_name, target_key):
    return _aurora_evolution_hook_make_latent_binding(
        globals(), _AURORA_NATIVE_EVOLVED_LAST, export_name, target_key,
    )


def develop_agency(payload=None, **kwargs):
    engine = _aurora_native_evolved_engine()
    if engine is None:
        return {
            'available': False, 'reason': 'evolved_surface_engine_unavailable', 'op_id': 'latent.aurora_internal.aurora_code_evolution_chamber.CodeEvolutionChamber.develop_agency', 'kind': 'latent'
        }
    return getattr(engine, 'latent_aurora_internal_aurora_code_evolution_chamber_codeevolutionchamber_develop_agency')(payload=payload, **kwargs)

_aurora_existing_binding = _aurora_get_target(['CodeEvolutionChamber'])
if _aurora_existing_binding is not None:
    _aurora_existing_attr = getattr(_aurora_existing_binding, 'develop_agency', None)
    if _aurora_existing_attr is None or getattr(_aurora_existing_attr, '_aurora_latent_binding_target', '') == 'CodeEvolutionChamber.develop_agency':
        _aurora_bind_owner_attribute(['CodeEvolutionChamber'], 'develop_agency', _aurora_make_latent_binding('develop_agency', 'CodeEvolutionChamber.develop_agency'))
        _AURORA_NATIVE_EVOLVED_LAST['CodeEvolutionChamber.develop_agency'] = {'latent_binding_active': True}

AURORA_NATIVE_EVOLVED_EXPORTS = {'latent.aurora_internal.aurora_code_evolution_chamber.CodeEvolutionChamber.develop_agency': 'develop_agency'}
AURORA_NATIVE_EVOLUTION_OVERRIDES = {'latent.aurora_internal.aurora_code_evolution_chamber.CodeEvolutionChamber.develop_agency': {'export': 'develop_agency',
                                                                                              'mode': 'latent_binding',
                                                                                              'target': 'CodeEvolutionChamber.develop_agency'}}
# AURORA_EVOLVED_NATIVE_END

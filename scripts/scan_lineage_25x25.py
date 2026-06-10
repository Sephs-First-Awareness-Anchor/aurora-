#!/usr/bin/env python3
"""Scan Aurora codebase and populate a 25x25 operation-lineage matrix.

Outputs:
- operations_index.json
- matrix_25x25.json
- lineage_25x25.md

This script is intentionally deterministic so repeated runs are stable.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import sys
from collections import defaultdict
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, os.pardir))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

AXES: Tuple[str, ...] = ("X", "T", "N", "B", "A")
AXIS_INDEX = {a: i for i, a in enumerate(AXES)}
DUAL_STATE_THRESHOLD = 0.15
PERCENT_AXIS_COUNT = 4

AXIS_CAUSATION = {
    "X": {
        "name": "existence",
        "question": "What changed?",
        "dominant": "observational or measurement behavior",
        "secondary": "state-sensitive modulation",
    },
    "T": {
        "name": "time",
        "question": "How long or how much across ticks?",
        "dominant": "deliberative or integrative behavior",
        "secondary": "drift-sensitive modulation",
    },
    "N": {
        "name": "cost",
        "question": "What does this cost or conserve?",
        "dominant": "resource-driven behavior",
        "secondary": "cost-aware modulation",
    },
    "B": {
        "name": "boundary",
        "question": "Where does this interact or collide?",
        "dominant": "interface reshaping",
        "secondary": "interaction filtering or shaping",
    },
    "A": {
        "name": "agency",
        "question": "Who decides to alter this?",
        "dominant": "structural reconfiguration",
        "secondary": "choice modulation",
    },
}

LABEL_TO_AXIS = {
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

AXIS_TO_LABEL = {
    "X": "existence",
    "T": "temporal",
    "N": "energy",
    "B": "boundary",
    "A": "agency",
}

ROOTS: List[str] = [f"NC:{a}>{b}" for a in AXES for b in AXES]

SKIP_DIR_NAMES = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "node_modules",
    "backup_originals_20260301_221224",
    "reset_full_backup_20260302_021145",
}

SKIP_PATH_PARTIAL = (
    os.path.join("aurora_runtime_output", ""),
    os.path.join("runs", ""),
)


try:
    from aurora_internal.lineage_canonical import constraints_for_operation
except Exception:
    constraints_for_operation = None

try:
    from aurora_internal.aurora_recommendation_hub import enqueue_recommendation as _enqueue_recommendation
except Exception:
    _enqueue_recommendation = None


@dataclass
class OperationRecord:
    op_id: str
    file: str
    line: int
    kind: str
    constraints: List[str]
    signature: str
    root_a: str
    root_b: str
    root_slot: str
    axis_percentages: Dict[str, float]
    axis_percentages_all: Dict[str, float]
    placement_axes: List[str]
    subslot_key: str


def _fallback_constraints(op_name: str) -> Tuple[str, ...]:
    low = str(op_name or "").lower()
    labels: List[str] = []

    def add(lbl: str) -> None:
        if lbl not in labels:
            labels.append(lbl)

    if any(k in low for k in ("tick", "time", "epoch", "phase", "watch", "chain", "burst")):
        add("temporal")
    if any(k in low for k in ("cost", "budget", "energy", "pressure", "relief", "diff", "amplifier", "tax")):
        add("energy")
    if any(k in low for k in ("bridge", "link", "inject", "promote", "constraint", "partition", "interface", "boundary", "coupling")):
        add("boundary")
    if any(k in low for k in ("sim", "episode", "behavior", "action", "learn", "feedback", "mutation", "align", "agency")):
        add("agency")
    if any(k in low for k in ("boot", "restore", "save", "load", "checkpoint", "state", "identity", "lineage", "ancestry", "status", "report", "root", "exist")):
        add("existence")

    if not labels:
        labels = ["existence"]
    return tuple(labels)


def infer_constraints(op_name: str) -> Tuple[str, ...]:
    canonical: Tuple[str, ...] = ()
    if constraints_for_operation is not None:
        try:
            out = tuple(constraints_for_operation(op_name))
            if out:
                canonical = out
        except Exception:
            pass

    fallback = _fallback_constraints(op_name)

    merged: List[str] = []
    for lbl in list(canonical) + list(fallback):
        low = str(lbl).strip().lower()
        if low and low not in merged:
            merged.append(low)

    if not merged:
        merged = ["existence"]
    return tuple(merged)


def labels_to_axes(labels: Sequence[str]) -> List[str]:
    out: List[str] = []
    for lbl in labels:
        ax = LABEL_TO_AXIS.get(str(lbl).strip().lower())
        if ax and ax not in out:
            out.append(ax)
    return out or ["X"]


def _stable_axis_choice(op_id: str, excluded: Sequence[str]) -> str:
    banned = set(str(x) for x in excluded)
    candidates = [a for a in AXES if a not in banned]
    if not candidates:
        candidates = list(AXES)
    h = hashlib.sha1(str(op_id or "").encode("utf-8", errors="ignore")).hexdigest()
    idx = int(h[:8], 16) % len(candidates)
    return candidates[idx]


def _tokenize_identifier(raw: str) -> List[str]:
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(raw or ""))
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return [t.lower() for t in text.split() if t]


def _quantize_pct(v: float, step: float = 0.05) -> float:
    step = max(0.01, float(step))
    q = round(float(v) / step) * step
    if q < 0.0:
        q = 0.0
    if q > 1.0:
        q = 1.0
    return q


def build_subslot_key(root_slot: str, axis_percentages_all: Dict[str, float], step: float = 0.05) -> str:
    parts = []
    for a in AXES:
        q = _quantize_pct(float(axis_percentages_all.get(a, 0.0)), step=step)
        parts.append(f"{a}{int(round(q*100.0)):02d}")
    return f"{root_slot}|{'-'.join(parts)}"


def infer_axis_percentages_for_operation(
    op_id: str,
    labels: Sequence[str],
    top_k: int = PERCENT_AXIS_COUNT,
) -> Tuple[Dict[str, float], Dict[str, float], List[str]]:
    base_axes = labels_to_axes(labels)
    # Measurement baseline keeps all axes observable before signal boosts.
    scores: Dict[str, float] = {a: 0.05 for a in AXES}

    for ax in base_axes:
        scores[ax] += 0.8

    tokens = _tokenize_identifier(op_id)
    axis_kw = {
        "X": {"exist", "state", "identity", "status", "checkpoint", "load", "save", "restore", "report", "detect", "parse", "extract", "presence"},
        "T": {"time", "tick", "epoch", "phase", "chain", "burst", "cycle", "window", "history", "temporal", "decay", "drift"},
        "N": {"cost", "energy", "budget", "worth", "price", "tax", "pressure", "relief", "diff", "score", "opt", "optimize", "amplifier"},
        "B": {"boundary", "bridge", "link", "interface", "coupling", "partition", "manifold", "gate", "buffer", "topology", "lattice", "field"},
        "A": {"agency", "autonomy", "action", "act", "control", "policy", "decide", "choice", "drive", "steer", "promote", "evolve", "mutation", "behavior", "learn"},
    }

    for tok in tokens:
        for ax, kws in axis_kw.items():
            if tok in kws:
                scores[ax] += 1.35

    if sum(scores.values()) <= 0.0:
        # No semantic signal: deterministic spread across all 5 axes.
        ordered: List[str] = []
        while len(ordered) < len(AXES):
            c = _stable_axis_choice(op_id + f":{len(ordered)}", ordered)
            if c not in ordered:
                ordered.append(c)
        for i, ax in enumerate(ordered):
            scores[ax] = 1.0 - (0.08 * float(i))

    total_all = sum(float(scores[a]) for a in AXES) or 1.0
    axis_percentages_all = {a: float(scores[a]) / float(total_all) for a in AXES}

    ranked = sorted(AXES, key=lambda a: (-float(axis_percentages_all.get(a, 0.0)), int(AXIS_INDEX[a])))
    strongest = list(ranked[: int(top_k)])

    ptotal = sum(float(axis_percentages_all[a]) for a in strongest) or 1.0
    axis_percentages = {a: 0.0 for a in AXES}
    for a in strongest:
        axis_percentages[a] = float(axis_percentages_all[a]) / float(ptotal)

    return axis_percentages_all, axis_percentages, strongest


def infer_axes_for_operation(op_id: str, labels: Sequence[str]) -> List[str]:
    # Backward-compat helper for any code expecting axis lists.
    _, pct, _ = infer_axis_percentages_for_operation(op_id, labels)
    ranked = sorted(AXES, key=lambda a: (-float(pct.get(a, 0.0)), int(AXIS_INDEX[a])))
    out: List[str] = []
    for ax in ranked:
        p = float(pct.get(ax, 0.0))
        if p <= 0.0:
            continue
        n = max(1, int(round(p * 10.0)))
        out.extend([ax] * n)
    return out or ["X"]

def should_skip(path_rel: str) -> bool:
    norm = path_rel.replace("\\", "/")
    for p in SKIP_PATH_PARTIAL:
        if norm.startswith(p.replace("\\", "/")):
            return True
    return False


def parse_python_file(abs_path: str, rel_path: str) -> List[OperationRecord]:
    with open(abs_path, "r", encoding="utf-8", errors="ignore") as fh:
        src = fh.read()
    try:
        tree = ast.parse(src, filename=rel_path)
    except SyntaxError:
        return []

    mod = rel_path[:-3].replace(os.sep, ".") if rel_path.endswith(".py") else rel_path.replace(os.sep, ".")
    out: List[OperationRecord] = []

    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.stack: List[str] = []

        def _emit(self, name: str, line: int, kind: str) -> None:
            qual = ".".join(self.stack + [name]) if self.stack else name
            op_id = f"{mod}.{qual}"
            labels = list(infer_constraints(op_id))
            axis_percentages_all, axis_percentages, placement_axes = infer_axis_percentages_for_operation(op_id, labels, top_k=PERCENT_AXIS_COUNT)
            signature, root_a, root_b, root_slot = derive_roots_from_percentages(axis_percentages_all, op_id=op_id, strongest_axes=placement_axes)
            subslot_key = build_subslot_key(root_slot, axis_percentages_all, step=0.05)
            out.append(
                OperationRecord(
                    op_id=op_id,
                    file=rel_path,
                    line=int(line),
                    kind=kind,
                    constraints=list(labels),
                    signature=signature,
                    root_a=root_a,
                    root_b=root_b,
                    root_slot=root_slot,
                    axis_percentages={k: float(v) for k, v in axis_percentages.items()},
                    axis_percentages_all={k: float(v) for k, v in axis_percentages_all.items()},
                    placement_axes=list(placement_axes),
                    subslot_key=str(subslot_key),
                )
            )

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            self._emit(node.name, getattr(node, "lineno", 0), "class")
            self.stack.append(node.name)
            self.generic_visit(node)
            self.stack.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self._emit(node.name, getattr(node, "lineno", 0), "function")
            self.stack.append(node.name)
            self.generic_visit(node)
            self.stack.pop()

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self._emit(node.name, getattr(node, "lineno", 0), "async_function")
            self.stack.append(node.name)
            self.generic_visit(node)
            self.stack.pop()

    Visitor().visit(tree)
    return out


def _module_for_rel_path(rel_path: str) -> str:
    path = str(rel_path or "").replace("\\", "/")
    return path[:-3].replace("/", ".") if path.endswith(".py") else path.replace("/", ".")


def _subsystem_for_rel_path(rel_path: str) -> str:
    path = str(rel_path or "").replace("\\", "/")
    if path.startswith("aurora_internal/"):
        return "internal"
    if path.startswith("scripts/"):
        return "scripts"
    if path.startswith("aurora_state/"):
        return "state"
    if path.startswith("aurora_runtime_output/"):
        return "runtime_output"
    if path.startswith("runs/"):
        return "runs"
    return "core"


def _resolve_local_import(module_name: str, module_to_file: Dict[str, str]) -> Optional[str]:
    mod = str(module_name or "").strip(".")
    if not mod:
        return None
    exact = module_to_file.get(mod)
    if exact:
        return exact
    prefix = mod + "."
    matches = sorted(
        [path for name, path in module_to_file.items() if str(name).startswith(prefix)],
        key=lambda p: (len(str(p)), str(p)),
    )
    return matches[0] if matches else None


def _build_file_profiles(root: str, records: Sequence[OperationRecord]) -> Dict[str, Dict[str, object]]:
    files = sorted({str(r.file) for r in records})
    module_to_file = {_module_for_rel_path(path): path for path in files}
    top_level = {str(mod).split(".", 1)[0] for mod in module_to_file.keys()}
    profiles: Dict[str, Dict[str, object]] = {}

    for rel_path in files:
        abs_path = os.path.join(root, rel_path)
        profile: Dict[str, object] = {
            "module": _module_for_rel_path(rel_path),
            "subsystem": _subsystem_for_rel_path(rel_path),
            "line_count": 0,
            "class_count": 0,
            "function_count": 0,
            "async_function_count": 0,
            "branch_count": 0,
            "local_imports": [],
            "imported_subsystems": [],
            "mutable_surface_count": 0,
        }
        try:
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as fh:
                src = fh.read()
            profile["line_count"] = int(len(src.splitlines()))
            tree = ast.parse(src, filename=rel_path)
        except Exception:
            profiles[rel_path] = profile
            continue

        local_imports: List[str] = []
        imported_subsystems: List[str] = []
        mutable_surface_count = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                profile["class_count"] = int(profile["class_count"]) + 1
            elif isinstance(node, ast.AsyncFunctionDef):
                profile["async_function_count"] = int(profile["async_function_count"]) + 1
                profile["function_count"] = int(profile["function_count"]) + 1
                if any(k in str(node.name).lower() for k in ("save", "load", "write", "persist", "inject", "mutate", "promote", "sync", "bridge")):
                    mutable_surface_count += 1
            elif isinstance(node, ast.FunctionDef):
                profile["function_count"] = int(profile["function_count"]) + 1
                if any(k in str(node.name).lower() for k in ("save", "load", "write", "persist", "inject", "mutate", "promote", "sync", "bridge")):
                    mutable_surface_count += 1
            elif isinstance(node, (ast.If, ast.For, ast.While, ast.Try, ast.With, ast.Match, ast.BoolOp)):
                profile["branch_count"] = int(profile["branch_count"]) + 1
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    base = str(getattr(alias, "name", "") or "").split(".", 1)[0]
                    if base not in top_level:
                        continue
                    local_file = _resolve_local_import(str(getattr(alias, "name", "") or ""), module_to_file)
                    local_imports.append(str(getattr(alias, "name", "") or ""))
                    if local_file:
                        imported_subsystems.append(_subsystem_for_rel_path(local_file))
            elif isinstance(node, ast.ImportFrom):
                module = str(getattr(node, "module", "") or "")
                base = module.split(".", 1)[0]
                if base not in top_level:
                    continue
                local_file = _resolve_local_import(module, module_to_file)
                local_imports.append(module)
                if local_file:
                    imported_subsystems.append(_subsystem_for_rel_path(local_file))

        profile["local_imports"] = sorted({x for x in local_imports if x})[:12]
        profile["imported_subsystems"] = sorted({x for x in imported_subsystems if x})[:8]
        profile["mutable_surface_count"] = int(mutable_surface_count)
        profiles[rel_path] = profile

    return profiles


def _collect_descendants(op_id: str, children_map: Dict[str, List[str]]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    stack = list(children_map.get(str(op_id), []))
    while stack:
        child = str(stack.pop())
        if child in seen:
            continue
        seen.add(child)
        ordered.append(child)
        stack.extend(list(children_map.get(child, [])))
    return ordered


def _ancestor_chain(op_id: str, nodes: Dict[str, Dict[str, object]]) -> List[Dict[str, object]]:
    chain: List[Dict[str, object]] = []
    seen = set()
    current = dict(nodes.get(str(op_id), {}) or {})
    parent = str(current.get("parent", "") or "")
    while parent and parent not in seen:
        seen.add(parent)
        pnode = dict(nodes.get(parent, {}) or {})
        if not pnode:
            break
        chain.append({
            "op_id": parent,
            "file": str(pnode.get("file", "")),
            "generation": int(pnode.get("generation", 1) or 1),
            "delta_constraints": list(pnode.get("delta_constraints", []) or []),
            "kind": str(pnode.get("kind", "")),
            "subsystem": _subsystem_for_rel_path(str(pnode.get("file", ""))),
        })
        parent = str(pnode.get("parent", "") or "")
    return chain


def _constraint_effect_modes(constraints: Sequence[str]) -> List[str]:
    mapping = {
        "existence": "state_schema_change",
        "temporal": "temporal_orchestration_change",
        "energy": "cost_pressure_change",
        "boundary": "interface_boundary_change",
        "agency": "adaptive_steering_change",
    }
    out: List[str] = []
    for raw in constraints:
        mode = mapping.get(str(raw).strip().lower())
        if mode and mode not in out:
            out.append(mode)
    return out


def _infer_effect_modes(rec: OperationRecord, file_profile: Dict[str, object]) -> List[str]:
    tokens = _tokenize_identifier(rec.op_id)
    modes = list(_constraint_effect_modes(rec.constraints))

    if rec.kind == "class":
        modes.append("stateful_surface_expansion")
    elif rec.kind == "async_function":
        modes.append("async_execution_surface")
    else:
        modes.append("behavioral_execution_surface")

    token_modes = {
        "save": "persistence_surface",
        "load": "persistence_surface",
        "persist": "persistence_surface",
        "checkpoint": "persistence_surface",
        "bridge": "gateway_surface",
        "gateway": "gateway_surface",
        "inject": "gateway_surface",
        "route": "gateway_surface",
        "lineage": "lineage_surface",
        "ancestry": "lineage_surface",
        "genealogy": "lineage_surface",
        "history": "lineage_surface",
        "language": "language_surface",
        "utterance": "language_surface",
        "lex": "language_surface",
        "parser": "language_surface",
        "sim": "simulation_surface",
        "episode": "simulation_surface",
        "epoch": "simulation_surface",
        "evolve": "evolution_surface",
        "mutation": "evolution_surface",
        "promote": "evolution_surface",
        "variant": "evolution_surface",
        "trace": "trace_surface",
        "instrument": "trace_surface",
        "sensor": "sensory_surface",
        "vision": "sensory_surface",
        "sound": "sensory_surface",
    }
    for tok in tokens:
        mode = token_modes.get(tok)
        if mode and mode not in modes:
            modes.append(mode)

    subsystem_mode = f"{str(file_profile.get('subsystem', 'core'))}_subsystem_surface"
    if subsystem_mode not in modes:
        modes.append(subsystem_mode)
    return modes


def _system_shift_phrases(effect_modes: Sequence[str]) -> List[str]:
    mapping = {
        "state_schema_change": "changed admissible state or persistence shape",
        "temporal_orchestration_change": "changed ordering, tick flow, or replay behavior",
        "cost_pressure_change": "changed cost, pressure, or maintenance economics",
        "interface_boundary_change": "changed module interfaces or coupling boundaries",
        "adaptive_steering_change": "changed steering, mutation, or choice behavior",
        "stateful_surface_expansion": "introduced reusable state-bearing system surface",
        "behavioral_execution_surface": "introduced executable behavior surface",
        "async_execution_surface": "introduced asynchronous coordination surface",
        "persistence_surface": "extended persistence or checkpoint continuity",
        "gateway_surface": "extended cross-layer routing or gateway effects",
        "lineage_surface": "extended lineage memory or ancestry introspection",
        "language_surface": "extended language-facing interpretation surface",
        "simulation_surface": "extended simulation-time behavior surface",
        "evolution_surface": "extended self-modification or promotion surface",
        "trace_surface": "extended stack instrumentation or trace capture surface",
        "sensory_surface": "extended sensory or perception intake surface",
    }
    out: List[str] = []
    for mode in effect_modes:
        phrase = mapping.get(str(mode))
        if phrase and phrase not in out:
            out.append(phrase)
    return out[:8]


def _top_name_counts(values: Sequence[str], limit: int = 6) -> List[Dict[str, object]]:
    counts: Dict[str, int] = defaultdict(int)
    for value in values:
        name = str(value or "").strip()
        if not name:
            continue
        counts[name] += 1
    ranked = sorted(counts.items(), key=lambda kv: (-int(kv[1]), str(kv[0])))[:max(1, int(limit))]
    return [{"name": str(name), "count": int(count)} for name, count in ranked]


def build_developmental_effect_histories(
    root: str,
    records: Sequence[OperationRecord],
    graph: Dict[str, object],
) -> Dict[str, Dict[str, object]]:
    records_by_id = {str(r.op_id): r for r in records}
    records_by_file: Dict[str, List[OperationRecord]] = defaultdict(list)
    for rec in records:
        records_by_file[str(rec.file)].append(rec)
    for rel_path in records_by_file:
        records_by_file[rel_path] = sorted(records_by_file[rel_path], key=lambda r: (int(r.line), str(r.op_id)))

    file_profiles = _build_file_profiles(root, records)
    nodes = dict(graph.get("nodes", {}) or {})
    children_map: Dict[str, List[str]] = defaultdict(list)
    cross_map: Dict[str, List[Dict[str, object]]] = defaultdict(list)
    for edge in list(graph.get("root_derivative_edges", []) or []):
        parent = str(edge.get("parent", "") or "")
        child = str(edge.get("child", "") or "")
        if parent and child:
            children_map[parent].append(child)
    for edge in list(graph.get("cross_diversity_edges", []) or []):
        parent = str(edge.get("parent", "") or "")
        child = str(edge.get("child", "") or "")
        if parent:
            cross_map[parent].append(dict(edge))
        if child:
            cross_map[child].append(dict(edge))

    histories: Dict[str, Dict[str, object]] = {}
    for rec in records:
        node = dict(nodes.get(rec.op_id, {}) or {})
        file_profile = dict(file_profiles.get(rec.file, {}) or {})
        effect_modes = _infer_effect_modes(rec, file_profile)
        ancestors = _ancestor_chain(rec.op_id, nodes)
        descendants = _collect_descendants(rec.op_id, children_map)
        file_ops = list(records_by_file.get(rec.file, []))
        idx = next((i for i, item in enumerate(file_ops) if str(item.op_id) == str(rec.op_id)), 0)
        file_predecessors = [
            {
                "op_id": str(item.op_id),
                "kind": str(item.kind),
                "line": int(item.line),
            }
            for item in file_ops[max(0, idx - 4):idx]
        ]

        descendant_modules = [_module_for_rel_path(records_by_id[d].file) for d in descendants if d in records_by_id]
        descendant_subsystems = [_subsystem_for_rel_path(records_by_id[d].file) for d in descendants if d in records_by_id]
        cross_edges = list(cross_map.get(rec.op_id, []))
        import_modules = list(file_profile.get("local_imports", []) or [])
        import_subsystems = list(file_profile.get("imported_subsystems", []) or [])
        required_constraint_shifts = sorted({
            str(c)
            for anc in ancestors
            for c in list(anc.get("delta_constraints", []) or [])
            if str(c)
        })
        developmental_depth = int(len(ancestors) + 1)
        impact_score = min(
            1.0,
            (
                (0.20 * min(1.0, developmental_depth / 6.0))
                + (0.25 * min(1.0, len(descendants) / 12.0))
                + (0.20 * min(1.0, len(cross_edges) / 8.0))
                + (0.20 * min(1.0, len(import_modules) / 8.0))
                + (0.15 * min(1.0, len(effect_modes) / 8.0))
            ),
        )

        histories[rec.op_id] = {
            "inferred": True,
            "node_identity": {
                "op_id": str(rec.op_id),
                "module": _module_for_rel_path(rec.file),
                "subsystem": _subsystem_for_rel_path(rec.file),
                "file": str(rec.file),
                "kind": str(rec.kind),
                "generation": int(node.get("generation", 1) or 1),
                "root_slot": str(rec.root_slot),
                "signature": str(rec.signature),
            },
            "developmental_preconditions": {
                "parent": str(node.get("parent", "") or ""),
                "ancestor_chain": ancestors,
                "file_predecessors": file_predecessors,
                "import_dependencies": import_modules[:8],
                "imported_subsystems": import_subsystems[:6],
                "required_constraint_shifts": required_constraint_shifts,
                "required_system_shifts": _system_shift_phrases(effect_modes),
            },
            "direct_system_effects": {
                "effect_modes": effect_modes,
                "effect_phrases": _system_shift_phrases(effect_modes),
                "constraint_effects": _constraint_effect_modes(rec.constraints),
                "local_scope": {
                    "module": _module_for_rel_path(rec.file),
                    "subsystem": _subsystem_for_rel_path(rec.file),
                    "line_count": int(file_profile.get("line_count", 0) or 0),
                    "class_count": int(file_profile.get("class_count", 0) or 0),
                    "function_count": int(file_profile.get("function_count", 0) or 0),
                    "async_function_count": int(file_profile.get("async_function_count", 0) or 0),
                    "branch_count": int(file_profile.get("branch_count", 0) or 0),
                    "mutable_surface_count": int(file_profile.get("mutable_surface_count", 0) or 0),
                },
            },
            "ripple_effects": {
                "descendant_count": int(len(descendants)),
                "cross_diversity_links": int(len(cross_edges)),
                "descendant_modules": _top_name_counts(descendant_modules),
                "descendant_subsystems": _top_name_counts(descendant_subsystems),
                "cross_linked_operations": sorted({
                    str(e.get("parent")) if str(e.get("child")) == str(rec.op_id) else str(e.get("child"))
                    for e in cross_edges
                    if str(e.get("parent") or e.get("child"))
                })[:8],
                "sample_descendants": descendants[:8],
            },
            "developmental_summary": {
                "developmental_depth": int(developmental_depth),
                "system_impact_score": round(float(impact_score), 6),
                "reflection_strength": round(float(min(1.0, impact_score + (0.05 * len(required_constraint_shifts)))), 6),
            },
        }

    return histories


def build_latent_operations(
    operation_descriptors: Sequence[Dict[str, object]],
) -> Tuple[List[Dict[str, object]], Dict[str, List[Dict[str, object]]]]:
    latent_operations: List[Dict[str, object]] = []
    by_origin: Dict[str, List[Dict[str, object]]] = defaultdict(list)
    seen_ids = set()

    for op in operation_descriptors:
        op_id = str(op.get("op_id", "") or "")
        constraints = [str(x) for x in list(op.get("constraints", []) or []) if str(x)]
        det = dict(op.get("deterministic_placement", {}) or {})
        history = dict(op.get("developmental_effect_history", {}) or {})
        summary = dict(history.get("developmental_summary", {}) or {})
        ripple = dict(history.get("ripple_effects", {}) or {})
        effects = dict(history.get("direct_system_effects", {}) or {})
        impact_score = float(summary.get("system_impact_score", 0.0) or 0.0)
        descendant_count = int(ripple.get("descendant_count", 0) or 0)
        cross_links = int(ripple.get("cross_diversity_links", 0) or 0)

        if impact_score < 0.52:
            continue
        if descendant_count > 0 and cross_links < 2:
            continue

        used_axes = set(labels_to_axes(constraints))
        missing_axis = str(det.get("unused_constraint_axis", "") or "").strip().upper()
        if not missing_axis or missing_axis not in AXES or missing_axis in used_axes:
            missing_axis = next((ax for ax in AXES if ax not in used_axes), "")
        if not missing_axis:
            continue

        modes = [str(x) for x in list(effects.get("effect_modes", []) or []) if str(x)]
        if "gateway_surface" in modes:
            verb = "route"
        elif "persistence_surface" in modes:
            verb = "persist"
        elif "language_surface" in modes:
            verb = "interpret"
        elif "simulation_surface" in modes:
            verb = "simulate"
        elif "evolution_surface" in modes:
            verb = "evolve"
        else:
            verb = "develop"

        suffix = f"{verb}_{AXIS_TO_LABEL.get(missing_axis, missing_axis.lower())}"
        latent_op_id = f"latent.{op_id}.{suffix}"
        if latent_op_id in seen_ids:
            continue
        seen_ids.add(latent_op_id)

        latent_constraints = list(dict.fromkeys(list(constraints) + [AXIS_TO_LABEL.get(missing_axis, "existence")]))
        axis_percentages_all, axis_percentages, placement_axes = infer_axis_percentages_for_operation(latent_op_id, latent_constraints, top_k=PERCENT_AXIS_COUNT)
        signature, root_a, root_b, root_slot = derive_roots_from_percentages(axis_percentages_all, op_id=latent_op_id, strongest_axes=placement_axes)
        subslot_key = build_subslot_key(root_slot, axis_percentages_all, step=0.05)
        latent_record = OperationRecord(
            op_id=latent_op_id,
            file=str(op.get("file", "")),
            line=int(op.get("line", 0) or 0),
            kind="latent_operation",
            constraints=list(latent_constraints),
            signature=signature,
            root_a=root_a,
            root_b=root_b,
            root_slot=root_slot,
            axis_percentages={k: float(v) for k, v in axis_percentages.items()},
            axis_percentages_all={k: float(v) for k, v in axis_percentages_all.items()},
            placement_axes=list(placement_axes),
            subslot_key=str(subslot_key),
        )
        latent_proj = _expanded_slot_projection(latent_record)
        latent_top = sorted(latent_proj.items(), key=lambda kv: -float(kv[1]))[:12]
        latent_weight = min(0.95, (0.45 * impact_score) + (0.08 * min(4, cross_links)) + (0.05 if descendant_count == 0 else 0.0))

        payload = {
            "op_id": latent_op_id,
            "origin_op_id": op_id,
            "file": str(op.get("file", "")),
            "line": int(op.get("line", 0) or 0),
            "kind": "latent_operation",
            "implemented": False,
            "constraints": latent_constraints,
            "signature": signature,
            "root_a": root_a,
            "root_b": root_b,
            "root_slot": root_slot,
            "axis_percentages": {k: float(v) for k, v in axis_percentages.items()},
            "axis_percentages_all": {k: float(v) for k, v in axis_percentages_all.items()},
            "placement_axes": list(placement_axes),
            "subslot_key": str(subslot_key),
            "latent_weight": float(round(latent_weight, 6)),
            "variant_projection_top": [
                {
                    "row": row,
                    "col": col,
                    "slot": f"{row}×{col}",
                    "weight": float(w),
                }
                for (row, col), w in latent_top
            ],
            "latent_reason": {
                "impact_score": round(float(impact_score), 6),
                "descendant_count": int(descendant_count),
                "cross_diversity_links": int(cross_links),
                "missing_axis": missing_axis,
                "source_effect_modes": modes[:8],
                "reason": f"Preexisting lineage implies a missing {AXIS_TO_LABEL.get(missing_axis, missing_axis.lower())}-facing descendant.",
            },
            "developmental_effect_history": {
                "inferred": True,
                "latent": True,
                "node_identity": {
                    "op_id": latent_op_id,
                    "origin_op_id": op_id,
                    "module": str(history.get("node_identity", {}).get("module", "")),
                    "subsystem": str(history.get("node_identity", {}).get("subsystem", "")),
                    "kind": "latent_operation",
                    "generation": int(history.get("node_identity", {}).get("generation", 1) or 1) + 1,
                    "root_slot": root_slot,
                    "signature": signature,
                },
                "developmental_preconditions": {
                    "origin": op_id,
                    "required_constraint_shifts": [AXIS_TO_LABEL.get(missing_axis, "existence")],
                    "required_system_shifts": list(history.get("direct_system_effects", {}).get("effect_phrases", []) or [])[:6],
                },
                "direct_system_effects": {
                    "effect_modes": list(dict.fromkeys(modes + [f"latent_{verb}_surface", f"latent_{missing_axis.lower()}_derivative"])),
                    "effect_phrases": [
                        f"would extend {AXIS_TO_LABEL.get(missing_axis, missing_axis.lower())} pressure handling",
                        f"would materialize the next descendant implied by {op_id}",
                    ],
                },
                "ripple_effects": {
                    "descendant_count": 0,
                    "cross_diversity_links": int(cross_links),
                    "derived_from_origin_descendants": int(descendant_count),
                },
                "developmental_summary": {
                    "developmental_depth": int(history.get("developmental_summary", {}).get("developmental_depth", 1) or 1) + 1,
                    "system_impact_score": round(float(latent_weight), 6),
                    "reflection_strength": round(float(min(1.0, latent_weight + 0.1)), 6),
                },
            },
        }
        latent_operations.append(payload)
        by_origin[op_id].append({
            "op_id": latent_op_id,
            "kind": "latent_operation",
            "missing_axis": missing_axis,
            "latent_weight": float(round(latent_weight, 6)),
            "reason": str(payload["latent_reason"]["reason"]),
        })

    latent_operations.sort(key=lambda rec: (-float(rec.get("latent_weight", 0.0) or 0.0), str(rec.get("op_id", ""))))
    return latent_operations, by_origin


def build_matrix(
    records: Sequence[OperationRecord],
    primary_topk: int = 1,
) -> Dict[str, Dict[str, Dict[str, object]]]:
    matrix: Dict[str, Dict[str, Dict[str, object]]] = {
        r: {c: {"count": 0, "ops": []} for c in ROOTS} for r in ROOTS
    }

    k = max(1, int(primary_topk))
    for rec in records:
        proj = _expanded_slot_projection(rec)
        ranked = sorted(proj.items(), key=lambda kv: (-float(kv[1]), kv[0][0], kv[0][1]))
        top = ranked[:k] if ranked else [((rec.root_a, rec.root_b), 1.0)]

        for (row, col), _w in top:
            if row not in matrix or col not in matrix[row]:
                continue
            cell = matrix[row][col]
            cell["count"] = int(cell["count"]) + 1
            cell_ops = cell["ops"]
            if isinstance(cell_ops, list):
                cell_ops.append(rec.op_id)

    return matrix



# Override axis ranking/placement with first-occurrence tie-break and
# expose descriptor logic used by downstream lineage artifacts.
def _axis_counts_with_first_occurrence(axes: Sequence[str]) -> Tuple[Dict[str, int], Dict[str, int]]:
    counts = {a: 0 for a in AXES}
    first_idx = {a: 10_000 for a in AXES}
    for i, axis in enumerate(axes):
        if axis not in counts:
            continue
        counts[axis] += 1
        if first_idx[axis] > 9_000:
            first_idx[axis] = int(i)
    return counts, first_idx


def _rank_axes(axes: Sequence[str]) -> List[str]:
    counts, first_idx = _axis_counts_with_first_occurrence(axes)
    return sorted(
        AXES,
        key=lambda a: (
            -int(counts[a]),
            int(first_idx[a]),
            int(AXIS_INDEX[a]),
        ),
    )


def derive_roots_from_percentages(
    axis_percentages_all: Dict[str, float],
    op_id: str = "",
    strongest_axes: Optional[Sequence[str]] = None,
) -> Tuple[str, str, str, str]:
    ranked = sorted(AXES, key=lambda a: (-float(axis_percentages_all.get(a, 0.0)), int(AXIS_INDEX[a])))
    if strongest_axes:
        top = [a for a in strongest_axes if a in AXES][:PERCENT_AXIS_COUNT]
    else:
        top = [a for a in ranked if float(axis_percentages_all.get(a, 0.0)) > 0.0][:PERCENT_AXIS_COUNT]

    if not top:
        top = ["X", "T", "N", "B"]

    dropped = [a for a in ranked if a not in top]
    differentiator_axis = dropped[0] if dropped else top[-1]
    pd = float(axis_percentages_all.get(differentiator_axis, 0.0))

    dominant_axis = ranked[0] if ranked else top[0]
    second_axis = ranked[1] if len(ranked) > 1 else dominant_axis
    dominant_margin = max(0.0, float(axis_percentages_all.get(dominant_axis, 0.0)) - float(axis_percentages_all.get(second_axis, 0.0)))

    if len(top) == 1:
        primary = top[0]
        secondary = _stable_axis_choice(op_id or primary, [primary])
    else:
        # Build directional pair scores from strongest-4 percentages.
        pair_weights: List[Tuple[Tuple[str, str], float]] = []
        for a in top:
            for b in top:
                if a == b:
                    continue
                pa = float(axis_percentages_all.get(a, 0.0))
                pb = float(axis_percentages_all.get(b, 0.0))
                diff = abs(pa - pb)
                base = (pa * pb) * (1.0 + (0.45 * (1.0 - min(1.0, diff))))
                dom_scale = (1.0 + (0.85 * dominant_margin)) if (a == dominant_axis or b == dominant_axis) else 1.0
                pair_weights.append(((a, b), float(max(0.0, base * dom_scale))))

        if not pair_weights:
            primary, secondary = top[0], top[1]
        else:
            pair_weights.sort(key=lambda x: (x[0][0], x[0][1]))

            # Unused 5th constraint is an explicit differentiator.
            seed = f"{op_id}|{differentiator_axis}|{pd:.6f}"
            h = hashlib.sha1(seed.encode("utf-8", errors="ignore")).hexdigest()
            target_idx = int(h[:8], 16) % len(pair_weights)

            boosted: List[Tuple[Tuple[str, str], float]] = []
            for i, (pair, w) in enumerate(pair_weights):
                boost = 1.85 if i == target_idx else 1.0
                boosted.append((pair, float(w * boost)))

            total = sum(w for _, w in boosted) or 1.0
            gate = (int(h[8:16], 16) / float(0xFFFFFFFF)) * total
            run = 0.0
            chosen = boosted[0][0]
            for pair, w in boosted:
                run += float(w)
                if run >= gate:
                    chosen = pair
                    break
            primary, secondary = chosen

    root_a = f"NC:{primary}>{secondary}"
    root_b = f"NC:{secondary}>{primary}"
    root_slot = f"{root_a}×{root_b}"

    sig_parts = [f"{a}:{float(axis_percentages_all.get(a, 0.0)):.3f}" for a in top]
    signature = "|".join(sig_parts) if sig_parts else "X:1.000"
    return signature, root_a, root_b, root_slot


def derive_roots(axes: Sequence[str]) -> Tuple[str, str, str, str]:
    counts, _ = _axis_counts_with_first_occurrence(axes)
    total = float(sum(int(v) for v in counts.values())) or 1.0
    pct = {a: float(counts[a]) / total for a in AXES}
    ranked = sorted(AXES, key=lambda a: (-float(pct.get(a, 0.0)), int(AXIS_INDEX[a])))
    strongest = ranked[:PERCENT_AXIS_COUNT]
    return derive_roots_from_percentages(pct, op_id="", strongest_axes=strongest)


def _normalized_axis_weights(axes: Sequence[str]) -> Dict[str, float]:
    counts, _ = _axis_counts_with_first_occurrence(axes)
    total = float(sum(int(v) for v in counts.values())) or 1.0
    return {a: float(counts[a]) / total for a in AXES}


def _dominance_level(margin: float) -> str:
    m = float(margin)
    if m >= 0.35:
        return "hard"
    if m >= 0.20:
        return "moderate"
    if m >= 0.10:
        return "soft"
    return "blended"


def _lineage_stage(has_parent: bool, child_count: int, cross_links: int) -> str:
    if cross_links > 0:
        return "hybrid"
    if has_parent and child_count > 0:
        return "transitional"
    if (not has_parent) and child_count > 0:
        return "ancestor"
    if has_parent and child_count == 0:
        return "offspring"
    return "transitional"


def _describe_operation(
    rec: OperationRecord,
    top_variants: Sequence[Dict[str, object]],
    parent: Optional[str],
    children: Sequence[str],
    cross_links: int,
    dual_state_threshold: float = DUAL_STATE_THRESHOLD,
) -> Dict[str, object]:
    weights = {a: float(rec.axis_percentages.get(a, 0.0)) for a in AXES}
    weights_all = {a: float(rec.axis_percentages_all.get(a, 0.0)) for a in AXES}
    ranked = sorted(AXES, key=lambda a: (-float(weights.get(a, 0.0)), int(AXIS_INDEX[a])))
    dropped_axes = [a for a in sorted(AXES, key=lambda x: (-float(weights_all.get(x, 0.0)), int(AXIS_INDEX[x]))) if a not in set(rec.placement_axes)]
    differentiator_axis = dropped_axes[0] if dropped_axes else ""
    differentiator_weight = float(weights_all.get(differentiator_axis, 0.0)) if differentiator_axis else 0.0

    dominant = ranked[0]
    secondary = ranked[1] if len(ranked) > 1 and float(weights.get(ranked[1], 0.0)) > 0.0 else dominant
    w1 = float(weights.get(dominant, 0.0))
    w2 = float(weights.get(secondary, 0.0)) if secondary != dominant else 0.0
    dual_state = bool((secondary != dominant) and ((w1 - w2) < float(dual_state_threshold)))

    ranked_all = sorted(AXES, key=lambda a: (-float(weights_all.get(a, 0.0)), int(AXIS_INDEX[a])))
    dom_all = ranked_all[0] if ranked_all else dominant
    sec_all = ranked_all[1] if len(ranked_all) > 1 else dom_all
    dom_margin = max(0.0, float(weights_all.get(dom_all, 0.0)) - float(weights_all.get(sec_all, 0.0)))
    dom_ratio = float(weights_all.get(dom_all, 0.0)) / float(max(1e-9, float(weights_all.get(sec_all, 0.0))))
    dom_scale = 1.0 + (1.75 * dom_margin)
    dom_level = _dominance_level(dom_margin)

    dom_meta = AXIS_CAUSATION.get(dominant, AXIS_CAUSATION["X"])
    sec_meta = AXIS_CAUSATION.get(secondary, AXIS_CAUSATION["X"])

    if secondary != dominant:
        conceptual = f"{dom_meta['dominant']} with {sec_meta['secondary']}"
    else:
        conceptual = f"{dom_meta['dominant']}"

    return {
        "op_id": rec.op_id,
        "file": rec.file,
        "line": int(rec.line),
        "kind": rec.kind,
        "constraints": list(rec.constraints),
        "deterministic_placement": {
            "primary_slot": rec.root_slot,
            "root_a": rec.root_a,
            "root_b": rec.root_b,
            "dominant_axis": dominant,
            "secondary_axis": secondary,
            "lineage_stage": _lineage_stage(bool(parent), len(children), int(cross_links)),
            "subslot_key": rec.subslot_key,
            "dominance_axis": dom_all,
            "dominance_margin": float(dom_margin),
            "dominance_ratio": float(dom_ratio),
            "dominance_level": dom_level,
            "classification_scale": float(dom_scale),
            "unused_constraint_axis": differentiator_axis,
            "unused_constraint_weight": float(differentiator_weight),
            "lineage_link": {
                "parent": parent,
                "children": list(children),
                "cross_diversity_link_count": int(cross_links),
            },
        },
        "probabilistic_descriptor": {
            "axis_weights": {k: float(v) for k, v in weights.items()},
            "axis_weights_all": {k: float(v) for k, v in weights_all.items()},
            "placement_axes": list(rec.placement_axes),
            "unused_constraint_axis": differentiator_axis,
            "unused_constraint_weight": float(differentiator_weight),
            "dual_state": bool(dual_state),
            "dual_state_threshold": float(dual_state_threshold),
            "dominance_axis": dom_all,
            "dominance_margin": float(dom_margin),
            "dominance_ratio": float(dom_ratio),
            "dominance_level": dom_level,
            "classification_scale": float(dom_scale),
            "classification_confidence": float(min(1.0, w1 * dom_scale)),
            "dominant_probability": float(w1),
            "secondary_probability": float(w2),
            "conceptual_behavior_class": conceptual,
            "causation_questions": {
                "primary": str(dom_meta["question"]),
                "secondary": str(sec_meta["question"]) if secondary != dominant else "",
            },
        },
        "variant_projection_top": list(top_variants),
    }


def _expanded_slot_projection(rec: OperationRecord) -> Dict[Tuple[str, str], float]:
    """Full 25x25 projection from measured 5-axis percentages.

    Root placement stays deterministic, but this projection activates the entire
    25x25 manifold by scoring every cell against the operation profile.
    """
    pct = {a: float(rec.axis_percentages_all.get(a, 0.0)) for a in AXES}
    ranked_all = sorted(AXES, key=lambda a: (-float(pct.get(a, 0.0)), int(AXIS_INDEX[a])))
    dom_axis = ranked_all[0] if ranked_all else "X"
    dom_margin = max(0.0, float(pct.get(ranked_all[0], 0.0)) - float(pct.get(ranked_all[1], 0.0))) if len(ranked_all) > 1 else 0.0

    def _parse_root(root: str) -> Tuple[str, str]:
        # root format: NC:X>T
        rhs = str(root).split(':', 1)[1]
        a, b = rhs.split('>', 1)
        return a, b

    weights: Dict[Tuple[str, str], float] = {}
    for ra in ROOTS:
        a, b = _parse_root(ra)
        # directed pair strength for row root
        row_strength = (0.67 * pct.get(a, 0.0)) + (0.33 * pct.get(b, 0.0))
        row_diff = abs(pct.get(a, 0.0) - pct.get(b, 0.0))

        for rb in ROOTS:
            c, d = _parse_root(rb)
            # directed pair strength for col root
            col_strength = (0.67 * pct.get(c, 0.0)) + (0.33 * pct.get(d, 0.0))
            col_diff = abs(pct.get(c, 0.0) - pct.get(d, 0.0))

            # Pairwise-diff coherence keeps diff-shaped profiles together.
            diff_coherence = 1.0 - min(1.0, abs(row_diff - col_diff))

            # Continuity bonus links directional chains across row/col roots.
            continuity = 1.08 if b == c else 1.0

            # Always positive because all 5 measured axes carry baseline mass.
            dom_cell_scale = (1.0 + (0.75 * dom_margin)) if (a == dom_axis or b == dom_axis or c == dom_axis or d == dom_axis) else 1.0
            w = (row_strength * col_strength) * (0.55 + 0.45 * diff_coherence) * continuity * dom_cell_scale
            weights[(ra, rb)] = float(max(0.0, w))

    # Keep deterministic primary slot as a mild anchor, not a collapse point.
    dominant = (rec.root_a, rec.root_b)
    weights[dominant] = float(weights.get(dominant, 0.0) + 0.01)

    total = sum(weights.values()) or 1.0
    return {k: (v / total) for k, v in weights.items()}

def build_expanded_matrix(records: Sequence[OperationRecord]) -> Dict[str, Dict[str, Dict[str, object]]]:
    matrix: Dict[str, Dict[str, Dict[str, object]]] = {
        r: {c: {"activation": 0.0, "op_support": 0, "sample_ops": []} for c in ROOTS} for r in ROOTS
    }

    for rec in records:
        proj = _expanded_slot_projection(rec)
        for (ra, rb), w in proj.items():
            if ra not in matrix or rb not in matrix[ra]:
                continue
            cell = matrix[ra][rb]
            cell["activation"] = float(cell.get("activation", 0.0) or 0.0) + float(w)
            cell["op_support"] = int(cell.get("op_support", 0) or 0) + 1
            sop = cell.get("sample_ops")
            if isinstance(sop, list) and len(sop) < 12:
                sop.append(rec.op_id)

    # normalize activation by op count so scales are comparable between runs
    n = float(max(1, len(records)))
    for r in ROOTS:
        for c in ROOTS:
            cell = matrix[r][c]
            cell["activation"] = float(cell.get("activation", 0.0) or 0.0) / n
    return matrix



def build_hybrid_matrix(
    primary: Dict[str, Dict[str, Dict[str, object]]],
    expanded: Dict[str, Dict[str, Dict[str, object]]],
    total_ops: int,
    primary_topk: int,
    primary_weight: float = 0.65,
    subset_weight: float = 0.35,
) -> Dict[str, Dict[str, Dict[str, object]]]:
    denom = float(max(1, int(total_ops) * max(1, int(primary_topk))))
    out: Dict[str, Dict[str, Dict[str, object]]] = {
        r: {c: {"primary_count": 0, "primary_norm": 0.0, "subset_activation": 0.0, "hybrid_score": 0.0} for c in ROOTS} for r in ROOTS
    }

    pw = float(primary_weight)
    sw = float(subset_weight)
    norm = pw + sw
    if norm <= 0.0:
        pw, sw, norm = 0.65, 0.35, 1.0
    pw /= norm
    sw /= norm

    for r in ROOTS:
        for c in ROOTS:
            pcell = primary[r][c]
            ecell = expanded[r][c]
            pcount = int(pcell.get("count", 0) or 0)
            pnorm = float(pcount) / denom
            eact = float(ecell.get("activation", 0.0) or 0.0)
            h = (pw * pnorm) + (sw * eact)
            out[r][c] = {
                "primary_count": int(pcount),
                "primary_norm": float(pnorm),
                "subset_activation": float(eact),
                "hybrid_score": float(h),
            }

    return out

def write_outputs(
    root: str,
    out_dir: str,
    records: Sequence[OperationRecord],
    dual_state_threshold: float = DUAL_STATE_THRESHOLD,
    primary_topk: int = 1,
) -> None:
    os.makedirs(out_dir, exist_ok=True)

    records_sorted = sorted(records, key=lambda r: (r.file, r.line, r.op_id))
    records_payload = [r.__dict__ for r in records_sorted]
    matrix = build_matrix(records_sorted, primary_topk=int(primary_topk))
    graph = build_derivative_graph(records_sorted)
    developmental_histories = build_developmental_effect_histories(root, records_sorted, graph)
    g_nodes = dict(graph.get('nodes', {}) or {})
    for op_id, hist in developmental_histories.items():
        if op_id in g_nodes and isinstance(g_nodes.get(op_id), dict):
            g_nodes[op_id]["developmental_effect_history"] = hist
    graph["nodes"] = g_nodes
    children_map: Dict[str, List[str]] = defaultdict(list)
    for edge in list(graph.get('root_derivative_edges', []) or []):
        p = edge.get('parent')
        c = edge.get('child')
        if p and c:
            children_map[str(p)].append(str(c))
    cross_link_count: Dict[str, int] = defaultdict(int)
    for edge in list(graph.get('cross_diversity_edges', []) or []):
        p = edge.get('parent')
        c = edge.get('child')
        if p:
            cross_link_count[str(p)] += 1
        if c:
            cross_link_count[str(c)] += 1


    # concise matrix payload with counts + first samples
    matrix_payload: Dict[str, Dict[str, Dict[str, object]]] = {}
    nonzero = 0
    for r in ROOTS:
        matrix_payload[r] = {}
        for c in ROOTS:
            cell = matrix[r][c]
            count = int(cell["count"])
            if count > 0:
                nonzero += 1
            ops = list(cell["ops"]) if isinstance(cell["ops"], list) else []
            matrix_payload[r][c] = {
                "count": count,
                "sample_ops": ops[:12],
            }

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root_dir": root,
        "total_operations": len(records_sorted),
        "roots": len(ROOTS),
        "matrix_cells": len(ROOTS) * len(ROOTS),
        "nonzero_cells": nonzero,
        "coverage_rate": float(nonzero) / float(max(1, len(ROOTS) * len(ROOTS))),
        "primary_topk": int(primary_topk),
    }

    operations_index_payload = []
    for rec in records_sorted:
        payload = dict(rec.__dict__)
        payload["developmental_effect_history"] = developmental_histories.get(rec.op_id, {})
        operations_index_payload.append(payload)

    with open(os.path.join(out_dir, "operations_index.json"), "w", encoding="utf-8") as fh:
        json.dump({
            "summary": {
                **summary,
                "developmental_effect_history_inferred": True,
            },
            "operations": operations_index_payload,
        }, fh, indent=2, ensure_ascii=True, sort_keys=True)

    with open(os.path.join(out_dir, "matrix_25x25.json"), "w", encoding="utf-8") as fh:
        json.dump({"summary": summary, "matrix": matrix_payload}, fh, indent=2, ensure_ascii=True, sort_keys=True)

    expanded = build_expanded_matrix(records_sorted)
    active_cells = 0
    for r in ROOTS:
        for c in ROOTS:
            if float(expanded[r][c].get("activation", 0.0) or 0.0) > 0.0:
                active_cells += 1

    with open(os.path.join(out_dir, "matrix_25x25_expanded.json"), "w", encoding="utf-8") as fh:
        json.dump({
            "summary": {
                **summary,
                "expanded_active_cells": int(active_cells),
                "expanded_coverage_rate": float(active_cells) / float(max(1, len(ROOTS) * len(ROOTS))),
            },
            "matrix": expanded,
        }, fh, indent=2, ensure_ascii=True, sort_keys=True)

    hybrid = build_hybrid_matrix(
        primary=matrix,
        expanded=expanded,
        total_ops=len(records_sorted),
        primary_topk=int(primary_topk),
    )
    hybrid_active = 0
    for r in ROOTS:
        for c in ROOTS:
            if float(hybrid[r][c].get("hybrid_score", 0.0) or 0.0) > 0.0:
                hybrid_active += 1

    with open(os.path.join(out_dir, "matrix_25x25_hybrid.json"), "w", encoding="utf-8") as fh:
        json.dump({
            "summary": {
                **summary,
                "expanded_active_cells": int(active_cells),
                "expanded_coverage_rate": float(active_cells) / float(max(1, len(ROOTS) * len(ROOTS))),
                "hybrid_active_cells": int(hybrid_active),
                "hybrid_coverage_rate": float(hybrid_active) / float(max(1, len(ROOTS) * len(ROOTS))),
                "hybrid_primary_weight": 0.65,
                "hybrid_subset_weight": 0.35,
            },
            "matrix": hybrid,
        }, fh, indent=2, ensure_ascii=True, sort_keys=True)

    # Per-operation representative variants across expanded slots
    op_variants: List[Dict[str, object]] = []
    for rec in records_sorted:
        proj = _expanded_slot_projection(rec)
        ranked = sorted(proj.items(), key=lambda kv: -float(kv[1]))
        top = ranked[:12]
        support = sum(1 for _, w in ranked if float(w) > 0.0)
        op_variants.append({
            "op_id": rec.op_id,
            "file": rec.file,
            "line": int(rec.line),
            "kind": rec.kind,
            "root_slot_primary": rec.root_slot,
            "constraints": list(rec.constraints),
            "axis_percentages": {k: float(v) for k, v in rec.axis_percentages.items()},
            "axis_percentages_all": {k: float(v) for k, v in rec.axis_percentages_all.items()},
            "placement_axes": list(rec.placement_axes),
            "subslot_key": rec.subslot_key,
            "variant_slot_count": int(support),
            "top_variants": [
                {
                    "row": row,
                    "col": col,
                    "slot": f"{row}×{col}",
                    "weight": float(w),
                }
                for (row, col), w in top
            ],
            "developmental_effect_history": developmental_histories.get(rec.op_id, {}),
        })

    with open(os.path.join(out_dir, "operation_variants.json"), "w", encoding="utf-8") as fh:
        json.dump({"summary": summary, "operations": op_variants}, fh, indent=2, ensure_ascii=True, sort_keys=True)

    subslot_counts: Dict[str, int] = defaultdict(int)
    slot_subslot_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for rec in records_sorted:
        subslot_counts[rec.subslot_key] += 1
        slot_subslot_counts[rec.root_slot][rec.subslot_key] += 1

    top_subslots = sorted(subslot_counts.items(), key=lambda kv: (-int(kv[1]), kv[0]))[:800]
    slot_breakdown = {}
    for slot, submap in slot_subslot_counts.items():
        ranked = sorted(submap.items(), key=lambda kv: (-int(kv[1]), kv[0]))
        slot_breakdown[slot] = {
            "unique_subslots": int(len(submap)),
            "top_subslots": [{"subslot_key": k, "count": int(v)} for k, v in ranked[:80]],
        }

    with open(os.path.join(out_dir, "subslot_distribution.json"), "w", encoding="utf-8") as fh:
        json.dump({
            "summary": {
                **summary,
                "unique_subslots": int(len(subslot_counts)),
            },
            "top_subslots": [{"subslot_key": k, "count": int(v)} for k, v in top_subslots],
            "by_root_slot": slot_breakdown,
        }, fh, indent=2, ensure_ascii=True, sort_keys=True)

    op_var_by_id = {str(x.get("op_id")): x for x in op_variants if x.get("op_id")}

    operation_descriptors: List[Dict[str, object]] = []
    for rec in records_sorted:
        op_id = rec.op_id
        var = op_var_by_id.get(op_id, {})
        top_variants = list(var.get("top_variants", []) or [])
        node = g_nodes.get(op_id, {})
        parent = node.get("parent") if isinstance(node, dict) else None
        children = list(children_map.get(op_id, []))
        cross_links = int(cross_link_count.get(op_id, 0))
        operation_descriptors.append(
            {
                **_describe_operation(
                rec=rec,
                top_variants=top_variants,
                parent=str(parent) if parent else None,
                children=children,
                cross_links=cross_links,
                dual_state_threshold=float(dual_state_threshold),
                ),
                "developmental_effect_history": developmental_histories.get(op_id, {}),
            }
        )

    operation_descriptors.sort(key=lambda x: str(x.get("op_id", "")))
    latent_operations, latent_by_origin = build_latent_operations(operation_descriptors)
    for op in operation_descriptors:
        hist = dict(op.get("developmental_effect_history", {}) or {})
        hist["latent_descendants"] = list(latent_by_origin.get(str(op.get("op_id", "")), []))
        op["developmental_effect_history"] = hist
    dual_state_count = int(sum(
        1 for x in operation_descriptors
        if bool((x.get("probabilistic_descriptor", {}) or {}).get("dual_state"))
    ))

    descriptor_payload = {
        "summary": {
            **summary,
            "dual_state_threshold": float(dual_state_threshold),
            "dual_state_operations": int(dual_state_count),
            "dual_state_rate": float(dual_state_count) / float(max(1, len(operation_descriptors))),
            "developmental_effect_history_inferred": True,
            "latent_operations": int(len(latent_operations)),
        },
        "operations": operation_descriptors,
        "latent_operations": latent_operations,
    }

    with open(os.path.join(out_dir, "operation_descriptors.json"), "w", encoding="utf-8") as fh:
        json.dump(descriptor_payload, fh, indent=2, ensure_ascii=True, sort_keys=True)

    with open(os.path.join(out_dir, "operation_descriptors_big.json"), "w", encoding="utf-8") as fh:
        json.dump(descriptor_payload, fh, indent=2, ensure_ascii=True, sort_keys=True)

    with open(os.path.join(out_dir, "latent_operations.json"), "w", encoding="utf-8") as fh:
        json.dump({
            "summary": {
                **summary,
                "latent_operations": int(len(latent_operations)),
            },
            "operations": latent_operations,
        }, fh, indent=2, ensure_ascii=True, sort_keys=True)

    # Global flatness diagnostics (all systems, not subsystem-specific).
    flat_ops = []
    slot_weights: Dict[str, List[float]] = defaultdict(list)
    slot_op_count: Dict[str, int] = defaultdict(int)

    for rec in op_variants:
        tv = list(rec.get("top_variants", []) or [])
        if not tv:
            continue
        w1 = float(tv[0].get("weight", 0.0) or 0.0)
        w2 = float(tv[1].get("weight", 0.0) or 0.0) if len(tv) > 1 else 0.0
        slot = str(rec.get("root_slot_primary", ""))
        slot_weights[slot].append(w1)
        slot_op_count[slot] += 1

        flat_ops.append({
            "op_id": rec.get("op_id"),
            "root_slot_primary": slot,
            "top_weight": w1,
            "second_weight": w2,
            "weight_gap": float(w1 - w2),
            "variant_slot_count": int(rec.get("variant_slot_count", 0) or 0),
            "is_flat": bool(w1 >= 0.80),
        })

    flat_ops.sort(key=lambda x: (-float(x.get("top_weight", 0.0)), -float(x.get("weight_gap", 0.0)), str(x.get("op_id", ""))))

    slot_flatness = []
    for slot, vals in slot_weights.items():
        valsf = [float(v) for v in vals]
        avg_top = sum(valsf) / float(max(1, len(valsf)))
        flat_ratio = sum(1 for v in valsf if v >= 0.80) / float(max(1, len(valsf)))
        slot_flatness.append({
            "slot": slot,
            "op_count": int(slot_op_count.get(slot, 0)),
            "avg_top_weight": float(avg_top),
            "flat_ratio": float(flat_ratio),
        })
    slot_flatness.sort(key=lambda x: (-float(x.get("flat_ratio", 0.0)), -float(x.get("avg_top_weight", 0.0)), -int(x.get("op_count", 0))))

    with open(os.path.join(out_dir, "flatness_report.json"), "w", encoding="utf-8") as fh:
        json.dump({
            "summary": {
                "generated_at": summary["generated_at"],
                "total_operations": int(len(op_variants)),
                "flat_operations": int(sum(1 for x in flat_ops if x.get("is_flat"))),
                "flat_operation_rate": float(sum(1 for x in flat_ops if x.get("is_flat"))) / float(max(1, len(op_variants))),
            },
            "slots": slot_flatness,
            "operations_top": flat_ops[:400],
        }, fh, indent=2, ensure_ascii=True, sort_keys=True)

    # Human-readable doc
    lines: List[str] = []
    lines.append("# Aurora 25x25 Operation Lineage")
    lines.append("")
    lines.append(f"Generated (UTC): `{summary['generated_at']}`")
    lines.append(f"Root dir: `{root}`")
    lines.append(f"Total operations: **{summary['total_operations']}**")
    lines.append(f"Matrix coverage: **{summary['nonzero_cells']} / {summary['matrix_cells']}** ({summary['coverage_rate']:.3f})")
    lines.append("")
    lines.append("## Root Coverage")
    lines.append("")

    # Top rows by outgoing count
    row_totals = []
    for r in ROOTS:
        total = sum(int(matrix[r][c]["count"]) for c in ROOTS)
        row_totals.append((r, total))
    row_totals.sort(key=lambda x: (-x[1], x[0]))

    for r, total in row_totals:
        lines.append(f"- `{r}`: {total}")

    lines.append("")
    lines.append("## Dense Cells (Top 40)")
    lines.append("")
    cells: List[Tuple[str, str, int]] = []
    for r in ROOTS:
        for c in ROOTS:
            ct = int(matrix[r][c]["count"])
            if ct > 0:
                cells.append((r, c, ct))
    cells.sort(key=lambda t: (-t[2], t[0], t[1]))
    for r, c, ct in cells[:40]:
        lines.append(f"- `{r}` x `{c}` -> {ct}")


    # Expanded diagnostics section
    flat_exp: List[Tuple[str, str, float]] = []
    for r in ROOTS:
        for c in ROOTS:
            av = float(expanded[r][c].get("activation", 0.0) or 0.0)
            if av > 0.0:
                flat_exp.append((r, c, av))
    flat_exp.sort(key=lambda t: (-t[2], t[0], t[1]))

    lines.append("")
    lines.append("## Variant Artifacts")
    lines.append("")
    lines.append("- `operation_variants.json`: per-operation top weighted slot variants")
    lines.append("- `flatness_report.json`: global slot/operation flatness diagnostics (all systems)")
    lines.append("- `operation_descriptors.json`: deterministic slot lineage + probabilistic descriptor overlay + developmental effect history")
    lines.append("- `latent_operations.json`: uncoded descendant operations implied by developmental pressure in the current stack")
    lines.append("- `matrix_25x25_hybrid.json`: primary+subset combined 25x25 signal")
    lines.append("- `subslot_distribution.json`: percent-profile subslot differentiation inside each root slot")

    lines.append("")
    lines.append("## Expanded Gradient Cells (Top 60)")
    lines.append("")
    for r, c, av in flat_exp[:60]:
        lines.append(f"- `{r}` x `{c}` -> activation={av:.6f}")

    with open(os.path.join(out_dir, "lineage_25x25.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    # Derivative/evolution graph pass
    with open(os.path.join(out_dir, "derivatives_graph.json"), "w", encoding="utf-8") as fh:
        json.dump(graph, fh, indent=2, ensure_ascii=True, sort_keys=True)

    gsum = dict(graph.get('summary', {}) or {})
    glines: List[str] = []
    glines.append("# Aurora Operation Derivative Graph")
    glines.append("")
    glines.append(f"Generated (UTC): `{summary['generated_at']}`")
    glines.append(f"Nodes: **{int(gsum.get('nodes', 0))}**")
    glines.append(f"Edges total: **{int(gsum.get('edges_total', 0))}**")
    glines.append(f"Root-derivative edges: **{int(gsum.get('root_derivative_edges', 0))}**")
    glines.append(f"Cross-diversity edges: **{int(gsum.get('cross_diversity_edges', 0))}**")
    glines.append(f"Roots: **{int(gsum.get('roots', 0))}**")
    glines.append(f"Max generation: **{int(gsum.get('max_generation', 1))}**")
    glines.append(f"Root-derivative rate: **{float(gsum.get('root_derivative_rate', 0.0)):.3f}**")
    glines.append(f"Cross-diversity rate: **{float(gsum.get('cross_diversity_rate', 0.0)):.3f}**")
    glines.append("")
    glines.append("## Top Root-Derivative Edges")
    glines.append("")
    edges = list(graph.get('root_derivative_edges', []) or [])
    edges.sort(key=lambda e: (-float(e.get('score', 0.0)), -int(e.get('generation', 1))))
    for e in edges[:120]:
        glines.append(
            f"- `{e.get('parent')}` -> `{e.get('child')}` "
            f"(gen={int(e.get('generation', 1))}, score={float(e.get('score', 0.0)):.3f}, "
            f"delta={list(e.get('delta_constraints', []))})"
        )


    glines.append("")
    glines.append("## Top Cross-Diversity Interaction Edges")
    glines.append("")
    xedges = list(graph.get('cross_diversity_edges', []) or [])
    xedges.sort(key=lambda e: (-float(e.get('score', 0.0))))
    for e in xedges[:120]:
        glines.append(
            f"- `{e.get('parent')}` -> `{e.get('child')}` "
            f"(score={float(e.get('score', 0.0)):.3f}, "
            f"parent_slot={e.get('parent_root_slot')}, child_slot={e.get('child_root_slot')}, "
            f"shared={list(e.get('shared_constraints', []))}, delta={list(e.get('delta_constraints', []))})"
        )

    with open(os.path.join(out_dir, "derivatives_graph.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(glines) + "\n")




def _class_alias(token: str) -> str:
    raw = str(token or "").strip()
    low = raw.lower()
    overrides = {
        "universesteerer": "steerer",
        "chainsimbridge": "bridge",
        "auroraruntime": "runtime",
        "constraintsgenealogylogger": "genealogy",
        "evolutionarychamber": "chamber",
    }
    if low in overrides:
        return overrides[low]
    if low.endswith("steerer"):
        return "steerer"
    if low.endswith("bridge"):
        return "bridge"
    if low.endswith("runtime"):
        return "runtime"
    return low


def _op_aliases(op_id: str) -> List[str]:
    parts = [p for p in str(op_id).split(".") if p]
    if not parts:
        return []

    aliases: List[str] = []

    def add(a: str) -> None:
        a = str(a or "").strip()
        if a and a not in aliases:
            aliases.append(a)

    add(parts[-1])
    if len(parts) >= 2:
        add(parts[-2] + "." + parts[-1])
    if len(parts) >= 3:
        add(parts[-3] + "." + parts[-2] + "." + parts[-1])

    if len(parts) >= 2:
        cls = _class_alias(parts[-2])
        add(cls + "." + parts[-1])

    # module leaf + function
    add(parts[0].split("/")[-1] + "." + parts[-1])

    return aliases


def write_generated_canonical(root: str, out_dir: str, records: Sequence[OperationRecord]) -> str:
    repo_root = os.path.abspath(root)
    gen_path = os.path.join(repo_root, "aurora_internal", "lineage_canonical_generated.json")

    alias_votes: Dict[str, Dict[Tuple[str, ...], int]] = defaultdict(lambda: defaultdict(int))

    for rec in records:
        labels = tuple(str(x) for x in rec.constraints)
        keys = [rec.op_id] + _op_aliases(rec.op_id)
        for k in keys:
            alias_votes[k][labels] += 1

    op_map: Dict[str, List[str]] = {}
    for alias, votes in alias_votes.items():
        ranked = sorted(votes.items(), key=lambda kv: (-int(kv[1]), kv[0]))
        best_labels = list(ranked[0][0]) if ranked else ["existence", "temporal"]
        op_map[str(alias)] = best_labels

    payload = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root_dir": repo_root,
        "operation_constraints": op_map,
    }

    with open(gen_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=True, sort_keys=True)

    # pointer file in lineage output dir for visibility
    pointer = os.path.join(out_dir, "canonical_generated_path.txt")
    with open(pointer, "w", encoding="utf-8") as fh:
        fh.write(gen_path + "\n")

    return gen_path


def _tokenize_op(op_id: str) -> List[str]:
    raw = str(op_id).replace('.', ' ').replace('_', ' ').replace(':', ' ').replace('-', ' ')
    toks = [t.lower() for t in raw.split() if t]
    stop = {
        'aurora', 'internal', 'scripts', 'class', 'function', 'async', 'def',
        'self', 'runtime', 'module', 'logger', 'manager', 'engine'
    }
    return [t for t in toks if t not in stop and len(t) > 1]


def _jaccard(a: Sequence[str], b: Sequence[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 0.0
    return float(len(sa & sb)) / float(max(1, len(sa | sb)))


def _find_parent(
    rec: OperationRecord,
    candidates: Sequence[OperationRecord],
    min_score: float = 0.62,
    require_same_slot: bool = False,
) -> Optional[Tuple[str, float]]:
    rec_tok = _tokenize_op(rec.op_id)
    rec_cons = set(rec.constraints)

    best_id = None
    best_score = 0.0

    for c in candidates:
        if c.op_id == rec.op_id:
            continue
        if c.line >= rec.line and c.file == rec.file:
            continue
        if require_same_slot and (c.root_slot != rec.root_slot):
            continue

        c_cons = set(c.constraints)
        overlap = float(len(rec_cons & c_cons)) / float(max(1, len(rec_cons | c_cons)))
        tok_sim = _jaccard(rec_tok, _tokenize_op(c.op_id))

        # Prefer parent with narrower/same constraints and strong semantic proximity.
        delta_gain = len(rec_cons - c_cons)
        penalty = 0.08 * max(0, -delta_gain)

        # Cross-diversity edges need less overlap, more semantic relation.
        if c.root_slot != rec.root_slot:
            score = (0.45 * overlap) + (0.55 * tok_sim) - penalty
        else:
            score = (0.55 * overlap) + (0.45 * tok_sim) - penalty

        if score > best_score and score >= float(min_score):
            best_score = score
            best_id = c.op_id

    if best_id is None:
        return None
    return best_id, float(best_score)


def build_derivative_graph(records: Sequence[OperationRecord]) -> Dict[str, object]:
    by_slot: Dict[str, List[OperationRecord]] = defaultdict(list)
    for r in records:
        by_slot[r.root_slot].append(r)

    nodes: Dict[str, Dict[str, object]] = {}
    for r in records:
        nodes[r.op_id] = {
            'op_id': r.op_id,
            'file': r.file,
            'line': int(r.line),
            'kind': r.kind,
            'root_slot': r.root_slot,
            'signature': r.signature,
            'constraints': list(r.constraints),
            'parent': None,
            'parent_score': 0.0,
            'generation': 1,
            'delta_constraints': list(r.constraints),
        }

    root_edges: List[Dict[str, object]] = []
    interaction_edges: List[Dict[str, object]] = []

    ordered_all = sorted(records, key=lambda r: (r.file, r.line, r.op_id))
    seen_all: List[OperationRecord] = []

    # Pass 1: root-derivative chains (same base slot).
    for slot, items in by_slot.items():
        ordered = sorted(items, key=lambda r: (r.file, r.line, r.op_id))
        seen: List[OperationRecord] = []
        for rec in ordered:
            parent = _find_parent(rec, seen, min_score=0.58, require_same_slot=True)
            if parent is None:
                seen.append(rec)
                continue
            pid, score = parent
            pnode = nodes.get(pid)
            if not pnode:
                seen.append(rec)
                continue

            p_cons = set(pnode.get('constraints', []))
            r_cons = set(rec.constraints)
            delta = sorted(r_cons - p_cons)
            gen = int(pnode.get('generation', 1)) + 1

            node = nodes[rec.op_id]
            node['parent'] = pid
            node['parent_score'] = float(score)
            node['generation'] = int(gen)
            node['delta_constraints'] = list(delta)

            root_edges.append({
                'edge_type': 'root_derivative',
                'parent': pid,
                'child': rec.op_id,
                'root_slot': slot,
                'score': float(score),
                'delta_constraints': list(delta),
                'generation': int(gen),
            })
            seen.append(rec)

    # Pass 2: cross-diversity interactions (different base slot), separate from parent chain.
    for rec in ordered_all:
        parent = _find_parent(rec, seen_all, min_score=0.42, require_same_slot=False)
        seen_all.append(rec)
        if parent is None:
            continue
        pid, score = parent
        pnode = nodes.get(pid)
        cnode = nodes.get(rec.op_id)
        if not pnode or not cnode:
            continue
        if str(pnode.get('root_slot')) == str(cnode.get('root_slot')):
            continue

        p_cons = set(pnode.get('constraints', []))
        c_cons = set(cnode.get('constraints', []))
        shared = sorted(p_cons & c_cons)
        if not shared:
            continue

        interaction_edges.append({
            'edge_type': 'cross_diversity_interaction',
            'parent': pid,
            'child': rec.op_id,
            'parent_root_slot': pnode.get('root_slot'),
            'child_root_slot': cnode.get('root_slot'),
            'score': float(score),
            'shared_constraints': shared,
            'delta_constraints': sorted(c_cons - p_cons),
        })

    roots = [n['op_id'] for n in nodes.values() if not n.get('parent')]
    max_gen = max(int(n.get('generation', 1)) for n in nodes.values()) if nodes else 1

    all_edges = list(root_edges) + list(interaction_edges)

    return {
        'summary': {
            'nodes': int(len(nodes)),
            'edges_total': int(len(all_edges)),
            'root_derivative_edges': int(len(root_edges)),
            'cross_diversity_edges': int(len(interaction_edges)),
            'roots': int(len(roots)),
            'max_generation': int(max_gen),
            'root_derivative_rate': float(len(root_edges)) / float(max(1, len(nodes))),
            'cross_diversity_rate': float(len(interaction_edges)) / float(max(1, len(nodes))),
        },
        'nodes': nodes,
        'edges': all_edges,
        'root_derivative_edges': root_edges,
        'cross_diversity_edges': interaction_edges,
    }

def scan(root: str) -> List[OperationRecord]:
    out: List[OperationRecord] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_NAMES]

        rel_dir = os.path.relpath(dirpath, root)
        rel_dir = "" if rel_dir == "." else rel_dir
        if rel_dir and should_skip(rel_dir + os.sep):
            continue

        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            abs_path = os.path.join(dirpath, fn)
            rel_path = os.path.relpath(abs_path, root)
            if should_skip(rel_path):
                continue
            out.extend(parse_python_file(abs_path, rel_path))

    # Deduplicate by op_id; keep earliest line occurrence.
    dedup: Dict[str, OperationRecord] = {}
    for rec in out:
        cur = dedup.get(rec.op_id)
        if cur is None or (rec.file, rec.line) < (cur.file, cur.line):
            dedup[rec.op_id] = rec
    return list(dedup.values())


def main() -> None:
    ap = argparse.ArgumentParser(description="Scan codebase and populate 25x25 operation lineage docs.")
    ap.add_argument("--root", default=".", help="Repository root to scan")
    ap.add_argument(
        "--out",
        default=os.path.join("aurora_runtime_output", "lineage_25x25"),
        help="Output directory for lineage artifacts",
    )
    ap.add_argument(
        "--persist-canonical",
        action="store_true",
        help="Write aurora_internal/lineage_canonical_generated.json for one-time canonical locking.",
    )
    ap.add_argument(
        "--dual-state-threshold",
        type=float,
        default=float(DUAL_STATE_THRESHOLD),
        help="Threshold for dual-state detection in probabilistic descriptors.",
    )
    ap.add_argument(
        "--primary-topk",
        type=int,
        default=1,
        help="Top-k discrete cells per operation for primary 25x25 matrix assignment.",
    )
    args = ap.parse_args()

    root = os.path.abspath(args.root)
    out_dir = os.path.abspath(args.out)

    records = scan(root)
    write_outputs(root, out_dir, records, dual_state_threshold=float(args.dual_state_threshold), primary_topk=int(args.primary_topk))

    generated_path = None
    if bool(args.persist_canonical):
        generated_path = write_generated_canonical(root, out_dir, records)

    print("[lineage-scan] complete")
    print(f"  root        : {root}")
    print(f"  out         : {out_dir}")
    print(f"  operations  : {len(records)}")
    print(f"  roots       : {len(ROOTS)}")
    print(f"  matrix size : {len(ROOTS) * len(ROOTS)}")
    if generated_path:
        print(f"  canonical   : {generated_path}")

    # Hidden post-run recommendation for Aurora (not printed to user by default).
    try:
        if _enqueue_recommendation is not None:
            mx_path = os.path.join(out_dir, "matrix_25x25.json")
            ex_path = os.path.join(out_dir, "matrix_25x25_expanded.json")
            nonzero = 0
            total = len(ROOTS) * len(ROOTS)
            expanded_cov = 0.0
            if os.path.exists(mx_path):
                with open(mx_path, "r", encoding="utf-8") as fh:
                    _mx = json.load(fh)
                nonzero = int((_mx.get("summary", {}) or {}).get("nonzero_cells", 0) or 0)
            if os.path.exists(ex_path):
                with open(ex_path, "r", encoding="utf-8") as fh:
                    _ex = json.load(fh)
                expanded_cov = float((_ex.get("summary", {}) or {}).get("expanded_coverage_rate", 0.0) or 0.0)

            primary_cov = float(nonzero) / float(max(1, total))
            priority = 0.20
            if primary_cov < 0.20:
                priority += 0.25
            if expanded_cov > 0.95:
                priority += 0.10
            priority = max(0.0, min(1.0, priority))

            _enqueue_recommendation(
                output_dir=os.path.abspath(os.path.join(root, "aurora_runtime_output")),
                source="scripts.scan_lineage_25x25.main",
                run_type="lineage_scan",
                title="Post-run lineage recommendation",
                body=(
                    f"Lineage scan finished with primary coverage={primary_cov:.3f} and "
                    f"expanded coverage={expanded_cov:.3f}. "
                    f"Consider reviewing dominant similarity clusters or discussing slot-topk tuning if primary remains sparse."
                ),
                priority=float(priority),
                context={
                    "operations": int(len(records)),
                    "primary_coverage_rate": float(primary_cov),
                    "expanded_coverage_rate": float(expanded_cov),
                    "primary_topk": int(args.primary_topk),
                },
            )
    except Exception:
        pass


if __name__ == "__main__":
    main()

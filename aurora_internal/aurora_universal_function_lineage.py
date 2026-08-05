#!/usr/bin/env python3
"""Universal function lineage for Aurora.

Every executable Python function is represented as a constraint-derived
operation.  Parentage is recovered from real code dependencies rather than
from a domain taxonomy: local calls, imported calls, overrides, and recursive
co-evolution groups.  Every lineage path terminates at one or more of the five
foundational constraints X, T, N, B, and A.

The generated manifest is source anatomy, not learned state.  Mutable runtime
observations remain instance-owned elsewhere.
"""
# Authors: Sunni (Sir) Morningstar & Ceph

from __future__ import annotations

import ast
import hashlib
import json
import math
import os
import re
import threading
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Set, Tuple

AXES: Tuple[str, ...] = ("X", "T", "N", "B", "A")
AXIS_LABELS: Dict[str, str] = {
    "X": "existence",
    "T": "temporal",
    "N": "energy",
    "B": "boundary",
    "A": "agency",
}
LABEL_TO_AXIS: Dict[str, str] = {v: k for k, v in AXIS_LABELS.items()}
ROOT_IDS: Tuple[str, ...] = tuple(f"ROOT:{axis}" for axis in AXES)
SCHEMA_VERSION = 1

_DEFAULT_EXCLUDED_DIRS: Set[str] = {
    ".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache",
    "node_modules", "build", "dist", "aurora_state", "aurora_state_test",
    "aurora_runtime_output", "runs", "tests", "_tmp_introspection_timing",
}

_BUILTIN_NAMES: Set[str] = {
    "abs", "all", "any", "ascii", "bin", "bool", "breakpoint", "bytearray",
    "bytes", "callable", "chr", "classmethod", "compile", "complex", "delattr",
    "dict", "dir", "divmod", "enumerate", "eval", "exec", "filter", "float",
    "format", "frozenset", "getattr", "globals", "hasattr", "hash", "help",
    "hex", "id", "input", "int", "isinstance", "issubclass", "iter", "len",
    "list", "locals", "map", "max", "memoryview", "min", "next", "object",
    "oct", "open", "ord", "pow", "print", "property", "range", "repr",
    "reversed", "round", "set", "setattr", "slice", "sorted", "staticmethod",
    "str", "sum", "super", "tuple", "type", "vars", "zip", "__import__",
}

_AXIS_TERMS: Dict[str, Set[str]] = {
    "X": {
        "exist", "existence", "identity", "state", "presence", "present", "object",
        "entity", "create", "construct", "build", "instantiate", "init", "load",
        "read", "parse", "extract", "resolve", "find", "get", "fetch", "restore",
        "snapshot", "manifest", "source", "record", "node", "value", "meaning",
        "representation", "model", "describe", "status", "catalog", "index",
    },
    "T": {
        "time", "temporal", "tick", "cycle", "loop", "history", "previous", "next",
        "sequence", "order", "persist", "save", "restore", "cache", "lifecycle",
        "episode", "turn", "session", "duration", "delay", "window", "recent",
        "memory", "lineage", "generation", "evolve", "development", "replay",
        "continue", "advance", "stream", "journal", "trajectory", "schedule",
    },
    "N": {
        "energy", "change", "transform", "update", "mutate", "pressure", "cost",
        "score", "weight", "gradient", "difference", "delta", "compute", "calculate",
        "derive", "convert", "apply", "effect", "impact", "relief", "error", "fault",
        "exception", "adjust", "amplify", "reduce", "increase", "decrease", "shift",
        "write", "emit", "consume", "produce", "process", "synthesize", "compose",
    },
    "B": {
        "boundary", "limit", "validate", "verify", "check", "guard", "gate", "filter",
        "compare", "distinguish", "classify", "normalize", "clamp", "schema", "type",
        "interface", "bridge", "partition", "scope", "role", "slot", "constraint",
        "condition", "branch", "threshold", "reject", "accept", "allow", "deny",
        "match", "select", "separate", "isolate", "lock", "safe", "coherent",
    },
    "A": {
        "agency", "action", "act", "choose", "decide", "select", "route", "control",
        "policy", "promote", "adopt", "commit", "execute", "invoke", "dispatch",
        "trigger", "respond", "answer", "request", "command", "autonomy", "intention",
        "goal", "plan", "steer", "author", "owner", "assign", "register", "attach",
        "connect", "start", "stop", "boot", "shutdown", "retry", "reconsider",
    },
}

_MUTATING_METHODS = {
    "append", "extend", "insert", "pop", "remove", "clear", "update", "setdefault",
    "add", "discard", "write", "save", "store", "persist", "delete", "unlink",
    "replace", "commit", "flush", "send", "emit", "register", "attach", "connect",
}
_TIME_CALLS = {
    "time", "sleep", "monotonic", "perf_counter", "datetime.now", "utcnow",
    "wait", "wait_for", "schedule", "tick", "advance", "next",
}
_BOUNDARY_CALLS = {
    "isinstance", "issubclass", "hasattr", "getattr", "validate", "verify", "check",
    "clamp", "min", "max", "sorted", "filter", "match", "search", "fullmatch",
}


def _tokenize(text: str) -> List[str]:
    raw = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(text or ""))
    raw = re.sub(r"[^A-Za-z0-9]+", " ", raw)
    return [tok.lower() for tok in raw.split() if tok]


def _module_name(repo_root: Path, path: Path) -> str:
    rel = path.relative_to(repo_root)
    parts = list(rel.parts)
    if parts and parts[-1].endswith(".py"):
        parts[-1] = parts[-1][:-3]
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        left = _call_name(node.value)
        return f"{left}.{node.attr}" if left else node.attr
    if isinstance(node, ast.Call):
        return _call_name(node.func)
    return ""


def _signature(node: ast.AST) -> str:
    args = getattr(node, "args", None)
    if args is None:
        return "()"
    try:
        chunks: List[str] = []
        pos = list(args.posonlyargs or []) + list(args.args or [])
        defaults = [None] * max(0, len(pos) - len(args.defaults or [])) + list(args.defaults or [])
        for arg, default in zip(pos, defaults):
            item = str(arg.arg)
            if default is not None:
                item += "=..."
            chunks.append(item)
        if args.vararg is not None:
            chunks.append("*" + args.vararg.arg)
        elif args.kwonlyargs:
            chunks.append("*")
        for arg, default in zip(args.kwonlyargs or [], args.kw_defaults or []):
            item = str(arg.arg)
            if default is not None:
                item += "=..."
            chunks.append(item)
        if args.kwarg is not None:
            chunks.append("**" + args.kwarg.arg)
        return "(" + ", ".join(chunks) + ")"
    except Exception:
        return "(...)"


def _normalize_scores(scores: Mapping[str, float]) -> Dict[str, float]:
    clean = {axis: max(0.0, float(scores.get(axis, 0.0) or 0.0)) for axis in AXES}
    total = sum(clean.values())
    if total <= 0.0:
        return {"X": 1.0, "T": 0.0, "N": 0.0, "B": 0.0, "A": 0.0}
    return {axis: clean[axis] / total for axis in AXES}


def _selected_axes(weights: Mapping[str, float]) -> List[str]:
    ranked = sorted(AXES, key=lambda axis: (-float(weights.get(axis, 0.0)), AXES.index(axis)))
    peak = float(weights.get(ranked[0], 0.0)) if ranked else 0.0
    threshold = max(0.13, peak * 0.42)
    selected = [axis for axis in ranked if float(weights.get(axis, 0.0)) >= threshold]
    return selected or [ranked[0] if ranked else "X"]


def _axis_signature(weights: Mapping[str, float]) -> str:
    return "|".join(f"{axis}:{float(weights.get(axis, 0.0)):.6f}" for axis in AXES)


def _content_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(262144), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass
class _Evidence:
    calls: List[str] = field(default_factory=list)
    reads: Set[str] = field(default_factory=set)
    writes: Set[str] = field(default_factory=set)
    assignments: int = 0
    aug_assignments: int = 0
    returns: int = 0
    yields: int = 0
    awaits: int = 0
    loops: int = 0
    branches: int = 0
    comparisons: int = 0
    bool_ops: int = 0
    arithmetic: int = 0
    exceptions: int = 0
    assertions: int = 0
    mutations: int = 0
    raises: int = 0
    deletes: int = 0


class _BodyAnalyzer(ast.NodeVisitor):
    def __init__(self) -> None:
        self.ev = _Evidence()

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        name = _call_name(node.func)
        if name:
            self.ev.calls.append(name)
            if name.split(".")[-1].lower() in _MUTATING_METHODS:
                self.ev.mutations += 1
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:  # noqa: N802
        if isinstance(node.ctx, ast.Load):
            self.ev.reads.add(node.id)
        elif isinstance(node.ctx, (ast.Store, ast.Del)):
            self.ev.writes.add(node.id)

    def visit_Attribute(self, node: ast.Attribute) -> None:  # noqa: N802
        name = _call_name(node)
        if isinstance(node.ctx, ast.Load):
            self.ev.reads.add(name)
        elif isinstance(node.ctx, (ast.Store, ast.Del)):
            self.ev.writes.add(name)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:  # noqa: N802
        self.ev.assignments += 1
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:  # noqa: N802
        self.ev.assignments += 1
        self.generic_visit(node)

    def visit_NamedExpr(self, node: ast.NamedExpr) -> None:  # noqa: N802
        self.ev.assignments += 1
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:  # noqa: N802
        self.ev.aug_assignments += 1
        self.ev.arithmetic += 1
        self.generic_visit(node)

    def visit_Return(self, node: ast.Return) -> None:  # noqa: N802
        self.ev.returns += 1
        self.generic_visit(node)

    def visit_Yield(self, node: ast.Yield) -> None:  # noqa: N802
        self.ev.yields += 1
        self.generic_visit(node)

    def visit_YieldFrom(self, node: ast.YieldFrom) -> None:  # noqa: N802
        self.ev.yields += 1
        self.generic_visit(node)

    def visit_Await(self, node: ast.Await) -> None:  # noqa: N802
        self.ev.awaits += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:  # noqa: N802
        self.ev.loops += 1
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:  # noqa: N802
        self.ev.loops += 1
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:  # noqa: N802
        self.ev.loops += 1
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:  # noqa: N802
        self.ev.branches += 1
        self.generic_visit(node)

    def visit_IfExp(self, node: ast.IfExp) -> None:  # noqa: N802
        self.ev.branches += 1
        self.generic_visit(node)

    def visit_Match(self, node: ast.Match) -> None:  # noqa: N802
        self.ev.branches += max(1, len(node.cases))
        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare) -> None:  # noqa: N802
        self.ev.comparisons += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:  # noqa: N802
        self.ev.bool_ops += 1
        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp) -> None:  # noqa: N802
        self.ev.arithmetic += 1
        self.generic_visit(node)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> None:  # noqa: N802
        self.ev.arithmetic += 1
        self.generic_visit(node)

    def visit_Try(self, node: ast.Try) -> None:  # noqa: N802
        self.ev.exceptions += 1
        self.generic_visit(node)

    def visit_Raise(self, node: ast.Raise) -> None:  # noqa: N802
        self.ev.raises += 1
        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert) -> None:  # noqa: N802
        self.ev.assertions += 1
        self.generic_visit(node)

    def visit_Delete(self, node: ast.Delete) -> None:  # noqa: N802
        self.ev.deletes += 1
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        return

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        return

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        return

    def visit_Lambda(self, node: ast.Lambda) -> None:  # noqa: N802
        return


@dataclass
class _FunctionSurface:
    function_id: str
    module: str
    qualname: str
    file: str
    line: int
    end_line: int
    column: int
    kind: str
    signature: str
    doc: str
    class_qualname: str
    lexical_scope: List[str]
    raw_calls: List[str]
    reads: List[str]
    writes: List[str]
    metrics: Dict[str, int]
    decorators: List[str]
    source_hash: str
    import_aliases: Dict[str, str]
    class_bases: List[str]


class _FileCollector(ast.NodeVisitor):
    def __init__(self, module: str, rel_file: str, source_hash: str, imports: Dict[str, str]) -> None:
        self.module = module
        self.rel_file = rel_file
        self.source_hash = source_hash
        self.imports = imports
        self.scope: List[str] = []
        self.class_stack: List[Tuple[str, List[str]]] = []
        self.surfaces: List[_FunctionSurface] = []
        self._lambda_ordinals: Dict[Tuple[int, int], int] = defaultdict(int)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        bases = [_call_name(base) or getattr(base, "id", "") for base in node.bases]
        self.scope.append(node.name)
        self.class_stack.append((".".join(self.scope), [b for b in bases if b]))
        for child in node.body:
            self.visit(child)
        self.class_stack.pop()
        self.scope.pop()

    def _surface_from_node(self, node: ast.AST, name: str, kind: str, body: Sequence[ast.AST], signature: str) -> None:
        qual = ".".join(self.scope + [name]) if self.scope else name
        fid = f"{self.module}.{qual}" if self.module else qual
        analyzer = _BodyAnalyzer()
        for child in body:
            analyzer.visit(child)
        ev = analyzer.ev
        doc = ""
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = (ast.get_docstring(node, clean=True) or "").split("\n\n", 1)[0][:500]
        decorators = []
        for deco in getattr(node, "decorator_list", []) or []:
            decorators.append(_call_name(deco) or "")
        class_qualname = self.class_stack[-1][0] if self.class_stack else ""
        class_bases = list(self.class_stack[-1][1]) if self.class_stack else []
        metrics = {
            "assignments": ev.assignments,
            "aug_assignments": ev.aug_assignments,
            "returns": ev.returns,
            "yields": ev.yields,
            "awaits": ev.awaits,
            "loops": ev.loops,
            "branches": ev.branches,
            "comparisons": ev.comparisons,
            "bool_ops": ev.bool_ops,
            "arithmetic": ev.arithmetic,
            "exceptions": ev.exceptions,
            "assertions": ev.assertions,
            "mutations": ev.mutations,
            "raises": ev.raises,
            "deletes": ev.deletes,
            "call_count": len(ev.calls),
            "read_count": len(ev.reads),
            "write_count": len(ev.writes),
        }
        self.surfaces.append(_FunctionSurface(
            function_id=fid,
            module=self.module,
            qualname=qual,
            file=self.rel_file,
            line=int(getattr(node, "lineno", 0) or 0),
            end_line=int(getattr(node, "end_lineno", getattr(node, "lineno", 0)) or 0),
            column=int(getattr(node, "col_offset", 0) or 0),
            kind=kind,
            signature=signature,
            doc=doc,
            class_qualname=class_qualname,
            lexical_scope=list(self.scope),
            raw_calls=list(ev.calls),
            reads=sorted(ev.reads)[:160],
            writes=sorted(ev.writes)[:160],
            metrics=metrics,
            decorators=[d for d in decorators if d],
            source_hash=self.source_hash,
            import_aliases=dict(self.imports),
            class_bases=class_bases,
        ))

    def _visit_function(self, node: ast.AST, kind: str) -> None:
        name = str(getattr(node, "name", "unknown"))
        body = list(getattr(node, "body", []) or [])
        self._surface_from_node(node, name, kind, body, _signature(node))
        self.scope.append(name)
        for child in body:
            self._visit_nested_scope(child)
        self.scope.pop()

    def _visit_nested_scope(self, node: ast.AST) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            self.visit(node)
            return
        for child in ast.iter_child_nodes(node):
            self._visit_nested_scope(child)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self._visit_function(node, "function")

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        self._visit_function(node, "async_function")

    def visit_Lambda(self, node: ast.Lambda) -> None:  # noqa: N802
        key = (int(getattr(node, "lineno", 0) or 0), int(getattr(node, "col_offset", 0) or 0))
        self._lambda_ordinals[key] += 1
        suffix = self._lambda_ordinals[key]
        name = f"<lambda@{key[0]}:{key[1]}:{suffix}>"
        self._surface_from_node(node, name, "lambda", [node.body], "(lambda)")
        for child in ast.iter_child_nodes(node.body):
            self._visit_nested_scope(child)


def _imports_for_tree(tree: ast.Module, module: str) -> Dict[str, str]:
    aliases: Dict[str, str] = {}
    package = module.rsplit(".", 1)[0] if "." in module else ""
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                bound = alias.asname or alias.name.split(".", 1)[0]
                aliases[bound] = alias.name
        elif isinstance(node, ast.ImportFrom):
            base = str(node.module or "")
            if int(node.level or 0) > 0:
                pkg_parts = package.split(".") if package else []
                keep = max(0, len(pkg_parts) - int(node.level or 0) + 1)
                prefix = ".".join(pkg_parts[:keep])
                base = ".".join(p for p in (prefix, base) if p)
            for alias in node.names:
                if alias.name == "*":
                    continue
                bound = alias.asname or alias.name
                aliases[bound] = ".".join(p for p in (base, alias.name) if p)
    return aliases


def _legacy_constraints(repo_root: Path) -> Dict[str, Tuple[str, ...]]:
    path = repo_root / "aurora_internal" / "lineage_canonical_generated.json"
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8") or "{}")
        ops = raw.get("operation_constraints", {}) if isinstance(raw, dict) else {}
        out: Dict[str, Tuple[str, ...]] = {}
        for key, vals in dict(ops or {}).items():
            axes: List[str] = []
            for val in list(vals or []):
                axis = LABEL_TO_AXIS.get(str(val or "").lower())
                if axis and axis not in axes:
                    axes.append(axis)
            if axes:
                out[str(key)] = tuple(axes)
        return out
    except Exception:
        return {}


def _legacy_lookup(function_id: str, legacy: Mapping[str, Tuple[str, ...]]) -> Tuple[str, ...]:
    exact = legacy.get(function_id)
    if exact:
        return exact
    low = function_id.lower()
    for key in (function_id.split(".")[-1], ".".join(function_id.split(".")[-2:]), ".".join(function_id.split(".")[-3:])):
        if key in legacy:
            return legacy[key]
        for legacy_key, axes in legacy.items():
            if legacy_key.lower() == key.lower():
                return axes
    for legacy_key, axes in legacy.items():
        if legacy_key.lower() == low:
            return axes
    return tuple()


def _root_evidence(surface: _FunctionSurface, legacy: Mapping[str, Tuple[str, ...]]) -> Tuple[Dict[str, float], Dict[str, List[str]]]:
    scores = {axis: 0.08 for axis in AXES}
    evidence: Dict[str, List[str]] = {axis: [] for axis in AXES}
    m = surface.metrics

    def add(axis: str, amount: float, reason: str) -> None:
        scores[axis] += max(0.0, float(amount))
        if reason and reason not in evidence[axis] and len(evidence[axis]) < 20:
            evidence[axis].append(reason)

    # AST structure is primary evidence.
    add("X", 0.16 * math.log1p(m.get("returns", 0) + m.get("read_count", 0)), "reads or returns represented state")
    add("T", 0.42 * math.log1p(m.get("loops", 0) + m.get("yields", 0) + m.get("awaits", 0)), "sequences or persists activity")
    add("N", 0.22 * math.log1p(m.get("assignments", 0) + m.get("aug_assignments", 0) + m.get("arithmetic", 0) + m.get("mutations", 0)), "changes values or state")
    add("B", 0.28 * math.log1p(m.get("branches", 0) + m.get("comparisons", 0) + m.get("bool_ops", 0) + m.get("exceptions", 0) + m.get("assertions", 0)), "distinguishes or guards alternatives")
    add("A", 0.15 * math.log1p(m.get("call_count", 0) + m.get("write_count", 0) + m.get("raises", 0) + m.get("deletes", 0)), "selects or causes effects")

    if surface.kind == "async_function":
        add("T", 0.45, "async continuity")
        add("A", 0.20, "scheduled agency")
    if surface.kind == "lambda":
        add("N", 0.18, "inline transformation")
        add("B", 0.12, "bounded expression")
    if surface.qualname.endswith(".__init__"):
        add("X", 1.10, "constructs an existent state")
        add("B", 0.20, "establishes object boundary")

    lexical_text = " ".join([
        surface.function_id, surface.doc,
        " ".join(surface.raw_calls), " ".join(surface.reads), " ".join(surface.writes),
    ])
    tokens = _tokenize(lexical_text)
    counts = defaultdict(int)
    for tok in tokens:
        for axis, terms in _AXIS_TERMS.items():
            if tok in terms:
                counts[axis] += 1
    for axis in AXES:
        if counts[axis]:
            add(axis, 0.22 * math.log1p(counts[axis]), f"semantic evidence ({counts[axis]} terms)")

    for call in surface.raw_calls:
        low = call.lower()
        tail = low.split(".")[-1]
        if call in _TIME_CALLS or tail in _TIME_CALLS:
            add("T", 0.35, f"temporal call {call}")
        if call in _BOUNDARY_CALLS or tail in _BOUNDARY_CALLS:
            add("B", 0.24, f"boundary call {call}")
        if tail in _MUTATING_METHODS:
            add("N", 0.26, f"mutation call {call}")
            add("A", 0.16, f"effectful call {call}")

    # Existing canonical labels are weak historical testimony, never the sole source.
    for axis in _legacy_lookup(surface.function_id, legacy):
        add(axis, 0.20, "prior canonical ancestry")

    normalized = _normalize_scores(scores)
    return normalized, evidence


class UniversalFunctionLineage:
    """Build, query, validate, and attach Aurora's whole-function lineage graph."""

    def __init__(
        self,
        *,
        repo_root: str,
        manifest_path: Optional[str] = None,
        auto_build: bool = True,
        include_lambdas: bool = True,
        persist: bool = True,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.manifest_path = Path(manifest_path).resolve() if manifest_path else (
            self.repo_root / "aurora_internal" / "universal_function_lineage.json"
        )
        self.constraint_index_path = self.repo_root / "aurora_internal" / "universal_function_constraints.json"
        self.include_lambdas = bool(include_lambdas)
        self.persist = bool(persist)
        self._lock = threading.RLock()
        self._manifest: Dict[str, Any] = {}
        self._functions: Dict[str, Dict[str, Any]] = {}
        self._children: Dict[str, List[str]] = {}
        self._suffix_index: Dict[str, List[str]] = {}
        self._systems: Optional[Dict[str, Any]] = None
        if self.manifest_path.exists():
            self.load()
        if auto_build and not self._functions:
            self.rebuild()

    def _iter_files(self) -> Iterable[Path]:
        for path in self.repo_root.rglob("*.py"):
            try:
                rel_parts = set(path.relative_to(self.repo_root).parts)
            except ValueError:
                continue
            if rel_parts & _DEFAULT_EXCLUDED_DIRS:
                continue
            if any(part.startswith("reset_full_backup_") or part.startswith("backup_originals_") for part in rel_parts):
                continue
            if path.is_file():
                yield path

    def _scan_surfaces(self) -> Tuple[Dict[str, _FunctionSurface], Dict[str, str], List[Dict[str, str]]]:
        surfaces: Dict[str, _FunctionSurface] = {}
        file_hashes: Dict[str, str] = {}
        parse_errors: List[Dict[str, str]] = []
        for path in sorted(self._iter_files()):
            rel = str(path.relative_to(self.repo_root)).replace(os.sep, "/")
            try:
                source = path.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(source, filename=rel)
                digest = hashlib.sha256(source.encode("utf-8", "replace")).hexdigest()
                file_hashes[rel] = digest
                module = _module_name(self.repo_root, path)
                imports = _imports_for_tree(tree, module)
                collector = _FileCollector(module, rel, digest, imports)
                collector.visit(tree)
                for surface in collector.surfaces:
                    if surface.kind == "lambda" and not self.include_lambdas:
                        continue
                    surfaces[surface.function_id] = surface
            except Exception as exc:
                parse_errors.append({"file": rel, "error": str(exc)[:240]})
        return surfaces, file_hashes, parse_errors

    @staticmethod
    def _build_indices(surfaces: Mapping[str, _FunctionSurface]) -> Dict[str, Any]:
        module_simple: Dict[Tuple[str, str], List[str]] = defaultdict(list)
        suffix: Dict[str, List[str]] = defaultdict(list)
        class_methods: Dict[Tuple[str, str, str], List[str]] = defaultdict(list)
        classes: Dict[Tuple[str, str], str] = {}
        for fid, surface in surfaces.items():
            simple = surface.qualname.split(".")[-1]
            module_simple[(surface.module, simple)].append(fid)
            suffix[simple].append(fid)
            suffix[".".join(surface.qualname.split(".")[-2:])].append(fid)
            if surface.class_qualname:
                class_name = surface.class_qualname.split(".")[-1]
                class_methods[(surface.module, class_name, simple)].append(fid)
                classes[(surface.module, class_name)] = f"{surface.module}.{surface.class_qualname}"
        return {
            "module_simple": module_simple,
            "suffix": suffix,
            "class_methods": class_methods,
            "classes": classes,
        }

    @staticmethod
    def _pick_unique(candidates: Iterable[str]) -> Optional[str]:
        vals = sorted(set(str(x) for x in candidates if x))
        return vals[0] if len(vals) == 1 else None

    def _resolve_call(self, caller: _FunctionSurface, raw: str, surfaces: Mapping[str, _FunctionSurface], indices: Mapping[str, Any]) -> Tuple[Optional[str], str]:
        call = str(raw or "").strip()
        if not call:
            return None, "empty"
        parts = call.split(".")
        simple = parts[-1]
        module_simple = indices["module_simple"]
        class_methods = indices["class_methods"]
        suffix = indices["suffix"]

        if parts[0] in {"self", "cls"} and caller.class_qualname and len(parts) >= 2:
            class_name = caller.class_qualname.split(".")[-1]
            candidate = self._pick_unique(class_methods.get((caller.module, class_name, simple), []))
            if candidate:
                return candidate, "same_class"

        # Imported module or imported symbol.
        alias_target = caller.import_aliases.get(parts[0])
        if alias_target:
            candidate_id = alias_target if len(parts) == 1 else alias_target + "." + ".".join(parts[1:])
            if candidate_id in surfaces:
                return candidate_id, "import_exact"
            imported_match = self._pick_unique(fid for fid in surfaces if fid == candidate_id or fid.endswith("." + candidate_id))
            if imported_match:
                return imported_match, "import_suffix"

        # Lexical and same-module scopes, from closest outward.
        if len(parts) == 1:
            scope = list(caller.lexical_scope)
            for depth in range(len(scope), -1, -1):
                qual = ".".join(scope[:depth] + [simple])
                candidate = f"{caller.module}.{qual}" if caller.module else qual
                if candidate in surfaces:
                    return candidate, "lexical"
            candidate = self._pick_unique(module_simple.get((caller.module, simple), []))
            if candidate:
                return candidate, "same_module"

        # Same-module Class.method.
        if len(parts) >= 2 and parts[0] not in {"self", "cls"}:
            candidate = f"{caller.module}." + ".".join(parts)
            if candidate in surfaces:
                return candidate, "same_module_attribute"

        # Only accept global suffix resolution for a bare function name.
        # An unresolved attribute call such as mapping.pop() or state.get()
        # does not prove ancestry to some unrelated user-defined method that
        # happens to share the same final name.
        if len(parts) == 1:
            candidate = self._pick_unique(suffix.get(call, []))
            if candidate:
                return candidate, "unique_suffix"
        return None, "unresolved"

    def _resolve_inheritance(self, surface: _FunctionSurface, surfaces: Mapping[str, _FunctionSurface], indices: Mapping[str, Any]) -> List[str]:
        if not surface.class_qualname or not surface.class_bases:
            return []
        method = surface.qualname.split(".")[-1]
        out: List[str] = []
        suffix = indices["suffix"]
        for base in surface.class_bases:
            base_tail = base.split(".")[-1]
            direct = f"{surface.module}.{base_tail}.{method}"
            if direct in surfaces:
                out.append(direct)
                continue
            imported = surface.import_aliases.get(base_tail)
            if imported:
                candidate = imported + "." + method
                if candidate in surfaces:
                    out.append(candidate)
                    continue
                match = self._pick_unique(fid for fid in surfaces if fid.endswith("." + candidate))
                if match:
                    out.append(match)
                    continue
            match = self._pick_unique(suffix.get(f"{base_tail}.{method}", []))
            if match:
                out.append(match)
        return sorted(set(out))

    @staticmethod
    def _tarjan(graph: Mapping[str, Sequence[str]]) -> List[List[str]]:
        index = 0
        stack: List[str] = []
        on_stack: Set[str] = set()
        indices: Dict[str, int] = {}
        low: Dict[str, int] = {}
        components: List[List[str]] = []

        def strong(v: str) -> None:
            nonlocal index
            indices[v] = index
            low[v] = index
            index += 1
            stack.append(v)
            on_stack.add(v)
            for w in graph.get(v, []):
                if w not in indices:
                    strong(w)
                    low[v] = min(low[v], low[w])
                elif w in on_stack:
                    low[v] = min(low[v], indices[w])
            if low[v] == indices[v]:
                comp: List[str] = []
                while stack:
                    w = stack.pop()
                    on_stack.discard(w)
                    comp.append(w)
                    if w == v:
                        break
                components.append(sorted(comp))

        for node in sorted(graph):
            if node not in indices:
                strong(node)
        return components

    @staticmethod
    def _cluster_generations(cluster_parents: Mapping[str, Set[str]]) -> Dict[str, int]:
        memo: Dict[str, int] = {}
        visiting: Set[str] = set()

        def gen(cid: str) -> int:
            if cid in memo:
                return memo[cid]
            if cid in visiting:
                return 1
            visiting.add(cid)
            parents = cluster_parents.get(cid, set())
            value = 1 if not parents else 1 + max(gen(pid) for pid in parents)
            visiting.discard(cid)
            memo[cid] = value
            return value

        for cid in cluster_parents:
            gen(cid)
        return memo

    @staticmethod
    def _shortest_root_paths(functions: Mapping[str, Dict[str, Any]]) -> Dict[str, Dict[str, List[str]]]:
        parents: Dict[str, List[str]] = {
            fid: list(rec.get("parents", []) or []) for fid, rec in functions.items()
        }
        memo: Dict[Tuple[str, str], Optional[List[str]]] = {}

        def path(fid: str, root: str, visiting: Set[str]) -> Optional[List[str]]:
            key = (fid, root)
            if key in memo:
                return memo[key]
            if fid in visiting:
                return None
            visiting = set(visiting)
            visiting.add(fid)
            best: Optional[List[str]] = None
            for parent in parents.get(fid, []):
                if parent == root:
                    candidate = [root, fid]
                elif parent.startswith("ROOT:"):
                    continue
                else:
                    prefix = path(parent, root, visiting)
                    candidate = prefix + [fid] if prefix else None
                if candidate and (best is None or len(candidate) < len(best)):
                    best = candidate
            memo[key] = best
            return best

        out: Dict[str, Dict[str, List[str]]] = {}
        for fid in functions:
            roots: Dict[str, List[str]] = {}
            for axis in AXES:
                result = path(fid, f"ROOT:{axis}", set())
                if result:
                    roots[axis] = result
            out[fid] = roots
        return out

    def rebuild(self) -> Dict[str, Any]:
        with self._lock:
            started = time.time()
            surfaces, file_hashes, parse_errors = self._scan_surfaces()
            indices = self._build_indices(surfaces)
            legacy = _legacy_constraints(self.repo_root)

            direct_weights: Dict[str, Dict[str, float]] = {}
            root_evidence: Dict[str, Dict[str, List[str]]] = {}
            dependency_graph: Dict[str, List[str]] = {}
            call_evidence: Dict[str, List[Dict[str, str]]] = {}
            unresolved: Dict[str, List[str]] = {}

            for fid, surface in surfaces.items():
                weights, evidence = _root_evidence(surface, legacy)
                direct_weights[fid] = weights
                root_evidence[fid] = evidence
                deps: List[str] = []
                rows: List[Dict[str, str]] = []
                misses: List[str] = []
                for raw in surface.raw_calls:
                    if raw.split(".")[-1] in _BUILTIN_NAMES:
                        continue
                    target, mode = self._resolve_call(surface, raw, surfaces, indices)
                    if target and target != fid:
                        deps.append(target)
                        rows.append({"call": raw, "target": target, "mode": mode})
                    elif mode == "unresolved":
                        misses.append(raw)
                for inherited in self._resolve_inheritance(surface, surfaces, indices):
                    if inherited != fid:
                        deps.append(inherited)
                        rows.append({"call": "override", "target": inherited, "mode": "inheritance"})
                dependency_graph[fid] = sorted(set(deps))
                call_evidence[fid] = rows[:200]
                unresolved[fid] = sorted(set(misses))[:120]

            components = self._tarjan(dependency_graph)
            function_cluster: Dict[str, str] = {}
            cluster_members: Dict[str, List[str]] = {}
            for comp in components:
                seed = "|".join(comp)
                cid = "SCC:" + hashlib.sha1(seed.encode("utf-8", "replace")).hexdigest()[:14]
                cluster_members[cid] = comp
                for fid in comp:
                    function_cluster[fid] = cid

            cluster_parents: Dict[str, Set[str]] = {cid: set() for cid in cluster_members}
            for fid, deps in dependency_graph.items():
                cid = function_cluster[fid]
                for dep in deps:
                    pid = function_cluster.get(dep)
                    if pid and pid != cid:
                        cluster_parents[cid].add(pid)
            generations = self._cluster_generations(cluster_parents)

            # Aggregate inherited root coverage by cluster in generation order.
            cluster_roots: Dict[str, Set[str]] = {}
            cluster_direct: Dict[str, Dict[str, float]] = {}
            for cid, members in cluster_members.items():
                aggregate = {axis: 0.0 for axis in AXES}
                for fid in members:
                    for axis in AXES:
                        aggregate[axis] += direct_weights[fid][axis]
                divisor = float(max(1, len(members)))
                cluster_direct[cid] = {axis: aggregate[axis] / divisor for axis in AXES}
            for cid in sorted(cluster_members, key=lambda c: generations.get(c, 1)):
                inherited: Set[str] = set()
                for pid in cluster_parents.get(cid, set()):
                    inherited.update(cluster_roots.get(pid, set()))
                selected = set(_selected_axes(cluster_direct[cid]))
                cluster_roots[cid] = inherited | selected

            functions: Dict[str, Dict[str, Any]] = {}
            cross_module_edges = 0
            multi_parent_count = 0
            for fid, surface in surfaces.items():
                cid = function_cluster[fid]
                peers = [x for x in cluster_members[cid] if x != fid]
                func_parents = [dep for dep in dependency_graph[fid] if function_cluster.get(dep) != cid]
                for parent in func_parents:
                    if surfaces[parent].module != surface.module:
                        cross_module_edges += 1

                inherited_axes: Set[str] = set()
                for parent in func_parents:
                    inherited_axes.update(_selected_axes(direct_weights[parent]))
                own_axes = _selected_axes(direct_weights[fid])
                direct_root_axes: List[str] = []
                if not func_parents:
                    direct_root_axes = list(own_axes)
                else:
                    peak = max(direct_weights[fid].values())
                    for axis in own_axes:
                        if axis not in inherited_axes or direct_weights[fid][axis] >= max(0.18, peak * 0.58):
                            direct_root_axes.append(axis)
                if not direct_root_axes and not func_parents:
                    direct_root_axes = [own_axes[0]]
                parents = sorted(set(func_parents + [f"ROOT:{axis}" for axis in direct_root_axes]))
                if len(parents) > 1:
                    multi_parent_count += 1
                lineage_kind = (
                    "co_evolved_composite" if peers and len(parents) > 1 else
                    "co_evolved" if peers else
                    "composite" if len(parents) > 1 else
                    "derived" if func_parents else
                    "direct_root"
                )
                resolved_count = len(call_evidence[fid])
                unresolved_count = len(unresolved[fid])
                call_total = resolved_count + unresolved_count
                resolution = 1.0 if call_total == 0 else resolved_count / float(call_total)
                evidence_strength = max(direct_weights[fid].values())
                confidence = min(1.0, 0.38 + (0.38 * resolution) + (0.24 * evidence_strength))
                functions[fid] = {
                    "function_id": fid,
                    "module": surface.module,
                    "qualname": surface.qualname,
                    "file": surface.file,
                    "line": surface.line,
                    "end_line": surface.end_line,
                    "column": surface.column,
                    "kind": surface.kind,
                    "signature_text": surface.signature,
                    "doc_hint": surface.doc,
                    "source_hash": surface.source_hash,
                    "root_constraints": own_axes,
                    "root_labels": [AXIS_LABELS[a] for a in own_axes],
                    "root_weights": {a: round(direct_weights[fid][a], 8) for a in AXES},
                    "constraint_signature": _axis_signature(direct_weights[fid]),
                    "root_evidence": {a: root_evidence[fid][a] for a in AXES if root_evidence[fid][a]},
                    "parents": parents,
                    "functional_parents": sorted(func_parents),
                    "direct_root_parents": [f"ROOT:{a}" for a in direct_root_axes],
                    "co_evolved_with": peers,
                    "cluster_id": cid,
                    "generation": int(generations.get(cid, 1)),
                    "lineage_kind": lineage_kind,
                    "call_evidence": call_evidence[fid],
                    "unresolved_local_calls": unresolved[fid],
                    "lineage_confidence": round(confidence, 6),
                    "metrics": dict(surface.metrics),
                    "reads": surface.reads,
                    "writes": surface.writes,
                    "decorators": surface.decorators,
                    "domain_agnostic": True,
                }

            root_paths = self._shortest_root_paths(functions)
            orphaned: List[str] = []
            for fid, rec in functions.items():
                rec["root_paths"] = root_paths.get(fid, {})
                rec["traceable_roots"] = sorted(rec["root_paths"].keys(), key=lambda a: AXES.index(a))
                if not rec["root_paths"]:
                    orphaned.append(fid)

            children: Dict[str, List[str]] = defaultdict(list)
            for fid, rec in functions.items():
                for parent in rec.get("functional_parents", []) or []:
                    children[parent].append(fid)
            for fid, rec in functions.items():
                rec["children"] = sorted(children.get(fid, []))

            digest = hashlib.sha256()
            for rel, sha in sorted(file_hashes.items()):
                digest.update(f"{rel}|{sha}\n".encode("utf-8"))
            source_manifest_hash = digest.hexdigest()
            root_counts = {axis: 0 for axis in AXES}
            for rec in functions.values():
                for axis in rec.get("traceable_roots", []):
                    root_counts[axis] += 1

            manifest = {
                "schema_version": SCHEMA_VERSION,
                "generated_at": time.time(),
                "repo_identity": self.repo_root.name,
                "source_manifest_hash": source_manifest_hash,
                "file_count": len(file_hashes),
                "function_count": len(functions),
                "named_function_count": sum(1 for s in surfaces.values() if s.kind != "lambda"),
                "lambda_count": sum(1 for s in surfaces.values() if s.kind == "lambda"),
                "parse_errors": parse_errors,
                "roots": {
                    f"ROOT:{axis}": {
                        "axis": axis,
                        "label": AXIS_LABELS[axis],
                        "generation": 0,
                        "parents": [],
                    }
                    for axis in AXES
                },
                "summary": {
                    "coverage_rate": 0.0 if not functions else (len(functions) - len(orphaned)) / float(len(functions)),
                    "orphan_count": len(orphaned),
                    "multi_parent_functions": multi_parent_count,
                    "co_evolved_functions": sum(1 for rec in functions.values() if rec.get("co_evolved_with")),
                    "cross_module_parent_edges": cross_module_edges,
                    "max_generation": max((int(rec.get("generation", 1)) for rec in functions.values()), default=1),
                    "root_reachability": root_counts,
                    "domain_taxonomy_used_for_parentage": False,
                    "parentage_basis": ["resolved calls", "inheritance overrides", "recursive co-evolution", "direct root novelty"],
                    "build_seconds": round(time.time() - started, 4),
                },
                "orphans": orphaned,
                "file_hashes": file_hashes,
                "functions": functions,
            }
            self._manifest = manifest
            self._functions = functions
            self._children = {k: sorted(v) for k, v in children.items()}
            self._rebuild_suffix_index()
            if self.persist:
                self._write_manifest()
                self._write_constraint_index()
            return self.status()

    def _write_manifest(self) -> None:
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.manifest_path.with_suffix(self.manifest_path.suffix + ".tmp")
        tmp.write_text(json.dumps(self._manifest, ensure_ascii=True, separators=(",", ":"), sort_keys=True), encoding="utf-8")
        os.replace(tmp, self.manifest_path)

    def _write_constraint_index(self) -> None:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "source_manifest_hash": self._manifest.get("source_manifest_hash", ""),
            "operation_constraints": {
                fid: list(rec.get("root_labels", []) or []) for fid, rec in self._functions.items()
            },
        }
        tmp = self.constraint_index_path.with_suffix(self.constraint_index_path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True), encoding="utf-8")
        os.replace(tmp, self.constraint_index_path)

    def load(self) -> Dict[str, Any]:
        with self._lock:
            raw = json.loads(self.manifest_path.read_text(encoding="utf-8") or "{}")
            funcs = raw.get("functions", {}) if isinstance(raw, dict) else {}
            if not isinstance(funcs, dict):
                raise ValueError("universal lineage manifest has no function map")
            self._manifest = dict(raw)
            self._functions = {str(k): dict(v) for k, v in funcs.items()}
            children: Dict[str, List[str]] = defaultdict(list)
            for fid, rec in self._functions.items():
                for parent in rec.get("functional_parents", []) or []:
                    children[str(parent)].append(fid)
            self._children = {k: sorted(v) for k, v in children.items()}
            self._rebuild_suffix_index()
            return self.status()

    def _rebuild_suffix_index(self) -> None:
        suffix: Dict[str, List[str]] = defaultdict(list)
        for fid, rec in self._functions.items():
            qual = str(rec.get("qualname", "") or "")
            tokens = [fid, qual, qual.split(".")[-1] if qual else fid.split(".")[-1]]
            if "." in qual:
                tokens.append(".".join(qual.split(".")[-2:]))
            for token in tokens:
                if token:
                    suffix[token.lower()].append(fid)
        self._suffix_index = {k: sorted(set(v)) for k, v in suffix.items()}

    def resolve(self, query: str) -> str:
        q = str(query or "").strip()
        if q in self._functions:
            return q
        low = q.lower()
        exact = self._suffix_index.get(low, [])
        if len(exact) == 1:
            return exact[0]
        candidates = sorted(fid for fid in self._functions if fid.lower().endswith("." + low))
        return candidates[0] if len(candidates) == 1 else ""

    def lineage_for(self, query: str) -> Dict[str, Any]:
        fid = self.resolve(query)
        return dict(self._functions.get(fid, {}) or {})

    def all_functions(self) -> Dict[str, Dict[str, Any]]:
        return {fid: dict(rec) for fid, rec in self._functions.items()}

    def trace_to_roots(self, query: str) -> Dict[str, List[str]]:
        rec = self.lineage_for(query)
        return {str(k): list(v) for k, v in dict(rec.get("root_paths", {}) or {}).items()}

    def parents_of(self, query: str) -> List[Dict[str, Any]]:
        rec = self.lineage_for(query)
        out: List[Dict[str, Any]] = []
        for parent in rec.get("parents", []) or []:
            if str(parent).startswith("ROOT:"):
                axis = str(parent).split(":", 1)[1]
                out.append({"function_id": parent, "axis": axis, "label": AXIS_LABELS.get(axis, axis), "generation": 0})
            else:
                parent_rec = dict(self._functions.get(str(parent), {}) or {})
                if parent_rec:
                    out.append(parent_rec)
        return out

    def descendants_of(self, query: str, limit: int = 100) -> List[str]:
        fid = self.resolve(query)
        if not fid:
            return []
        seen: Set[str] = set()
        queue: deque[str] = deque([fid])
        while queue and len(seen) < max(1, int(limit)):
            current = queue.popleft()
            for child in self._children.get(current, []):
                if child not in seen:
                    seen.add(child)
                    queue.append(child)
        return sorted(seen)

    def attach_systems(self, systems: Optional[Dict[str, Any]]) -> None:
        self._systems = systems if isinstance(systems, dict) else None
        if self._systems is not None:
            self._systems["function_lineage"] = self
            genealogy = self._systems.get("genealogy")
            if genealogy is not None:
                self.attach_genealogy(genealogy)

    def attach_genealogy(self, genealogy: Any) -> bool:
        if genealogy is None:
            return False
        if isinstance(genealogy, MutableMapping):
            genealogy["function_lineage_status"] = self.status()
            genealogy["function_lineage_manifest"] = str(self.manifest_path)
            return True
        if hasattr(genealogy, "attach_function_lineage"):
            genealogy.attach_function_lineage(self)
            return True
        try:
            setattr(genealogy, "_function_lineage", self)
            return True
        except Exception:
            return False

    def verify(self) -> Dict[str, Any]:
        function_count = len(self._functions)
        missing_parents: List[Dict[str, str]] = []
        orphans: List[str] = []
        bad_roots: List[str] = []
        for fid, rec in self._functions.items():
            for parent in rec.get("parents", []) or []:
                if parent not in ROOT_IDS and parent not in self._functions:
                    missing_parents.append({"function": fid, "parent": str(parent)})
            paths = dict(rec.get("root_paths", {}) or {})
            if not paths:
                orphans.append(fid)
            for axis, path in paths.items():
                if not path or path[0] != f"ROOT:{axis}" or path[-1] != fid:
                    bad_roots.append(fid)
                    break
        return {
            "valid": not missing_parents and not orphans and not bad_roots,
            "function_count": function_count,
            "coverage_rate": 0.0 if function_count == 0 else (function_count - len(orphans)) / float(function_count),
            "missing_parent_count": len(missing_parents),
            "orphan_count": len(orphans),
            "bad_root_path_count": len(bad_roots),
            "missing_parents": missing_parents[:50],
            "orphans": orphans[:50],
            "bad_root_paths": bad_roots[:50],
        }

    def status(self) -> Dict[str, Any]:
        summary = dict(self._manifest.get("summary", {}) or {})
        return {
            "available": bool(self._functions),
            "schema_version": int(self._manifest.get("schema_version", SCHEMA_VERSION) or SCHEMA_VERSION),
            "manifest_path": str(self.manifest_path),
            "constraint_index_path": str(self.constraint_index_path),
            "source_manifest_hash": str(self._manifest.get("source_manifest_hash", "") or ""),
            "file_count": int(self._manifest.get("file_count", 0) or 0),
            "function_count": len(self._functions),
            "named_function_count": int(self._manifest.get("named_function_count", 0) or 0),
            "lambda_count": int(self._manifest.get("lambda_count", 0) or 0),
            **summary,
        }


__all__ = ["UniversalFunctionLineage", "AXES", "AXIS_LABELS", "ROOT_IDS"]

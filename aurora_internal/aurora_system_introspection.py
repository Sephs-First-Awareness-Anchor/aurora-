#!/usr/bin/env python3
"""
Aurora native system introspection bridge.

This module does not create a second reasoning system and does not alter
Aurora's response selection.  It joins evidence Aurora already produces:

* runtime fault records,
* understanding-contract contributors,
* communication attribution,
* articulation arbitration,
* QuasiArch observations,
* code lineage and source structure.

The bridge adds two missing capabilities:

1. A stable, source-derived map of Aurora's executable functions.
2. Per-turn decision provenance that can be traced backward from a bad
   result to the function and assumption that produced it.

All observation is fail-quiet and instance-owned by state_dir.  No module
level mutable runtime paths are used.

Authors: Sunni (Sir) Morningstar & Ceph
"""
from __future__ import annotations

import ast
import hashlib
import inspect
import json
import os
import re
import threading
import time
from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from aurora_internal.aurora_runtime_faults import (
    record_exception_from_locals as _aurora_record_exception_from_locals,
)

_SCHEMA_VERSION = 1
_MAX_TEXT = 500
_MAX_COLLECTION = 30
_MAX_DEPTH = 4
_MAX_EPISODE_STEPS = 400
_DEFAULT_EPISODE_MEMORY = 80
_STRUCTURAL_INTERROGATIVES = frozenset(
    {"who", "whom", "whose", "what", "which", "where", "when", "why", "how"}
)

# The executable anatomy is immutable evidence derived from source files, so
# instances may safely share it when both repository root and manifest hash
# match.  Runtime episodes, paths, diagnoses, and mutable language state are
# never stored here.
_SOURCE_MAP_CACHE_LOCK = threading.RLock()
_SOURCE_MAP_CACHE: Dict[Tuple[str, str], Dict[str, Dict[str, Any]]] = {}


def _clip01(value: Any, default: float = 0.0) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return max(0.0, min(1.0, float(default)))


def _clean_token(value: Any) -> str:
    return str(value or "").strip().lower().strip(".,!?;:'\"()[]{}")


def _safe_json_value(value: Any, *, depth: int = 0) -> Any:
    """Bound arbitrary runtime values into diagnostic-safe JSON shapes."""
    if depth >= _MAX_DEPTH:
        return repr(value)[:_MAX_TEXT]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return value[:_MAX_TEXT]
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        try:
            return _safe_json_value(asdict(value), depth=depth + 1)
        except Exception:
            return repr(value)[:_MAX_TEXT]
    if isinstance(value, Mapping):
        out: Dict[str, Any] = {}
        for idx, (key, item) in enumerate(value.items()):
            if idx >= _MAX_COLLECTION:
                out["__truncated__"] = len(value) - _MAX_COLLECTION
                break
            out[str(key)[:120]] = _safe_json_value(item, depth=depth + 1)
        return out
    if isinstance(value, (list, tuple, set, frozenset)):
        seq = list(value)
        out = [_safe_json_value(item, depth=depth + 1) for item in seq[:_MAX_COLLECTION]]
        if len(seq) > _MAX_COLLECTION:
            out.append({"__truncated__": len(seq) - _MAX_COLLECTION})
        return out
    if hasattr(value, "to_dict"):
        try:
            return _safe_json_value(value.to_dict(), depth=depth + 1)
        except Exception:
            pass
    if hasattr(value, "__dict__"):
        try:
            public = {
                str(k): v
                for k, v in vars(value).items()
                if not str(k).startswith("_")
            }
            if public:
                return _safe_json_value(public, depth=depth + 1)
        except Exception:
            pass
    return repr(value)[:_MAX_TEXT]


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=True, default=str), encoding="utf-8")
    os.replace(tmp, path)


def _append_jsonl(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True, default=str) + "\n")


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        left = _call_name(node.value)
        return f"{left}.{node.attr}" if left else node.attr
    return ""


def _module_name(repo_root: Path, path: Path) -> str:
    rel = path.relative_to(repo_root).with_suffix("")
    parts = list(rel.parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _format_signature(node: ast.AST) -> str:
    args = getattr(node, "args", None)
    if args is None:
        return "()"
    parts: List[str] = []
    positional = list(getattr(args, "posonlyargs", []) or []) + list(args.args or [])
    defaults = [None] * (len(positional) - len(args.defaults or [])) + list(args.defaults or [])
    for arg, default in zip(positional, defaults):
        text = arg.arg
        if getattr(arg, "annotation", None) is not None:
            try:
                text += ": " + ast.unparse(arg.annotation)
            except Exception:
                pass
        if default is not None:
            try:
                text += "=" + ast.unparse(default)
            except Exception:
                text += "=..."
        parts.append(text)
    if getattr(args, "vararg", None) is not None:
        parts.append("*" + args.vararg.arg)
    elif getattr(args, "kwonlyargs", None):
        parts.append("*")
    for arg, default in zip(args.kwonlyargs or [], args.kw_defaults or []):
        text = arg.arg
        if default is not None:
            try:
                text += "=" + ast.unparse(default)
            except Exception:
                text += "=..."
        parts.append(text)
    if getattr(args, "kwarg", None) is not None:
        parts.append("**" + args.kwarg.arg)
    return "(" + ", ".join(parts) + ")"


@dataclass
class FunctionRecord:
    function_id: str
    module: str
    qualname: str
    file: str
    line: int
    end_line: int
    signature: str
    doc: str = ""
    calls: List[str] = field(default_factory=list)
    reads: List[str] = field(default_factory=list)
    writes: List[str] = field(default_factory=list)
    branch_count: int = 0


class _BodyEvidenceVisitor(ast.NodeVisitor):
    """Collect evidence for one function without descending into nested scopes."""

    def __init__(self) -> None:
        self.calls: set[str] = set()
        self.reads: set[str] = set()
        self.writes: set[str] = set()
        self.branches = 0

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        cname = _call_name(node.func)
        if cname:
            self.calls.add(cname)
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:  # noqa: N802
        if isinstance(node.ctx, ast.Load):
            self.reads.add(node.id)
        elif isinstance(node.ctx, (ast.Store, ast.Del)):
            self.writes.add(node.id)

    def visit_Attribute(self, node: ast.Attribute) -> None:  # noqa: N802
        aname = _call_name(node)
        if isinstance(node.ctx, ast.Load):
            self.reads.add(aname)
        elif isinstance(node.ctx, (ast.Store, ast.Del)):
            self.writes.add(aname)
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:  # noqa: N802
        self.branches += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:  # noqa: N802
        self.branches += 1
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:  # noqa: N802
        self.branches += 1
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:  # noqa: N802
        self.branches += 1
        self.generic_visit(node)

    def visit_Try(self, node: ast.Try) -> None:  # noqa: N802
        self.branches += 1
        self.generic_visit(node)

    def visit_Match(self, node: ast.Match) -> None:  # noqa: N802
        self.branches += 1
        self.generic_visit(node)

    def visit_IfExp(self, node: ast.IfExp) -> None:  # noqa: N802
        self.branches += 1
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        return

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        return

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        return


class _FunctionVisitor(ast.NodeVisitor):
    def __init__(self, module: str, rel_file: str) -> None:
        self.module = module
        self.rel_file = rel_file
        self.scope: List[str] = []
        self.records: List[FunctionRecord] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        self.scope.append(node.name)
        for child in node.body:
            self.visit(child)
        self.scope.pop()

    def _visit_function(self, node: ast.AST) -> None:
        name = str(getattr(node, "name", "unknown"))
        qual_parts = self.scope + [name]
        qualname = ".".join(qual_parts)
        function_id = f"{self.module}.{qualname}" if self.module else qualname
        evidence = _BodyEvidenceVisitor()
        for child in getattr(node, "body", []) or []:
            evidence.visit(child)
        calls = evidence.calls
        reads = evidence.reads
        writes = evidence.writes
        branches = evidence.branches
        doc = ast.get_docstring(node, clean=True) or ""
        if doc:
            doc = doc.split("\n\n", 1)[0][:_MAX_TEXT]
        record = FunctionRecord(
            function_id=function_id,
            module=self.module,
            qualname=qualname,
            file=self.rel_file,
            line=int(getattr(node, "lineno", 0) or 0),
            end_line=int(getattr(node, "end_lineno", getattr(node, "lineno", 0)) or 0),
            signature=_format_signature(node),
            doc=doc,
            calls=sorted(calls)[:80],
            reads=sorted(reads)[:100],
            writes=sorted(writes)[:100],
            branch_count=branches,
        )
        self.records.append(record)
        self.scope.append(name)
        for child in getattr(node, "body", []) or []:
            # Nested functions are separate executable surfaces.  Avoid
            # re-walking ordinary statements because ast.walk above already
            # collected the current function's evidence.
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                self.visit(child)
        self.scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        self._visit_function(node)


class AuroraSystemIntrospection:
    """Instance-owned bridge joining Aurora's existing introspection evidence."""

    def __init__(
        self,
        *,
        repo_root: str,
        state_dir: str,
        persist: bool = True,
        max_episode_memory: int = _DEFAULT_EPISODE_MEMORY,
        build_index: bool = True,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.state_dir = Path(state_dir).resolve()
        self.persist = bool(persist)
        self.max_episode_memory = max(10, int(max_episode_memory))
        self.index_path = self.state_dir / "system_introspection_index.json"
        self.episode_path = self.state_dir / "system_introspection_episodes.jsonl"
        self.last_episode_path = self.state_dir / "last_introspection_episode.json"
        self.last_diagnosis_path = self.state_dir / "last_system_diagnosis.json"
        self._lock = threading.RLock()
        self._local = threading.local()
        self._systems: Optional[Dict[str, Any]] = None
        self._function_index: Dict[str, Dict[str, Any]] = {}
        self._name_index: Dict[str, List[str]] = {}
        self._episodes: Dict[str, Dict[str, Any]] = {}
        self._episode_order: List[str] = []
        self._last_diagnosis: Dict[str, Any] = {}
        self._load_last_state()
        if build_index:
            self.ensure_system_map()

    # ------------------------------------------------------------------
    # Source-derived system map
    # ------------------------------------------------------------------

    def _iter_source_files(self) -> Iterable[Path]:
        excluded = {
            ".git", ".venv", "venv", "__pycache__", "aurora_state",
            "aurora_state_test", "node_modules", "build", "dist",
            "aurora_runtime_output", ".pytest_cache", "tests",
            "_tmp_introspection_timing",
        }
        for path in self.repo_root.rglob("*.py"):
            try:
                rel_parts = set(path.relative_to(self.repo_root).parts)
            except ValueError:
                continue
            if rel_parts & excluded:
                continue
            if path.is_file():
                yield path

    def _manifest_hash(self, files: Sequence[Path]) -> str:
        digest = hashlib.sha256()
        for path in sorted(files):
            try:
                stat = path.stat()
                rel = str(path.relative_to(self.repo_root)).replace(os.sep, "/")
                digest.update(f"{rel}|{stat.st_size}|{stat.st_mtime_ns}\n".encode("utf-8"))
            except OSError:
                continue
        return digest.hexdigest()

    def _rebuild_name_index(self) -> None:
        names: Dict[str, List[str]] = {}
        for fid, rec in self._function_index.items():
            tokens = {
                fid.lower(),
                str(rec.get("qualname", "")).lower(),
                str(rec.get("qualname", "")).split(".")[-1].lower(),
            }
            for token in tokens:
                if token:
                    names.setdefault(token, []).append(fid)
        self._name_index = names

    def ensure_system_map(self, *, force: bool = False) -> Dict[str, Any]:
        """Load or rebuild Aurora's executable function map from real source."""
        with self._lock:
            lineage = self._systems.get("function_lineage") if isinstance(self._systems, dict) else None
            if not force and lineage is not None and hasattr(lineage, "all_functions"):
                try:
                    lineage_rows = dict(lineage.all_functions() or {})
                    if lineage_rows:
                        functions: Dict[str, Dict[str, Any]] = {}
                        for fid, row in lineage_rows.items():
                            call_targets = [
                                str(item.get("target", "") or "")
                                for item in list(row.get("call_evidence", []) or [])
                                if isinstance(item, dict) and item.get("target")
                            ]
                            functions[str(fid)] = {
                                "function_id": str(fid),
                                "module": str(row.get("module", "") or ""),
                                "qualname": str(row.get("qualname", "") or ""),
                                "file": str(row.get("file", "") or ""),
                                "line": int(row.get("line", 0) or 0),
                                "end_line": int(row.get("end_line", row.get("line", 0)) or 0),
                                "signature": str(row.get("signature_text", "") or ""),
                                "doc": str(row.get("doc_hint", "") or ""),
                                "calls": sorted(set(call_targets))[:120],
                                "reads": list(row.get("reads", []) or [])[:160],
                                "writes": list(row.get("writes", []) or [])[:160],
                                "branch_count": int(dict(row.get("metrics", {}) or {}).get("branches", 0) or 0),
                            }
                        self._function_index = functions
                        self._rebuild_name_index()
                        status = dict(lineage.status() or {}) if hasattr(lineage, "status") else {}
                        if self.persist:
                            _atomic_write_json(self.index_path, {
                                "schema_version": _SCHEMA_VERSION,
                                "generated_at": time.time(),
                                "repo_root": str(self.repo_root),
                                "manifest_hash": str(status.get("source_manifest_hash", "") or ""),
                                "file_count": int(status.get("file_count", 0) or 0),
                                "function_count": len(functions),
                                "parse_errors": [],
                                "source": "universal_function_lineage",
                                "functions": functions,
                            })
                        return self.system_map_status()
                except Exception as _aurora_boundary_exc:
                    _aurora_record_exception_from_locals(
                        locals(), module=__name__,
                        operation="system_introspection:lineage_index_import",
                        exc=_aurora_boundary_exc,
                        context={"function": "ensure_system_map", "source_file": __file__},
                    )

            files = list(self._iter_source_files())
            manifest_hash = self._manifest_hash(files)
            if not force and self.index_path.exists():
                try:
                    cached = json.loads(self.index_path.read_text(encoding="utf-8") or "{}")
                    if (
                        isinstance(cached, dict)
                        and cached.get("manifest_hash") == manifest_hash
                        and isinstance(cached.get("functions"), dict)
                    ):
                        self._function_index = dict(cached["functions"])
                        self._rebuild_name_index()
                        return self.system_map_status()
                except Exception as _aurora_boundary_exc:
                    _aurora_record_exception_from_locals(
                        locals(), module=__name__,
                        operation="system_introspection:index_load",
                        exc=_aurora_boundary_exc,
                        context={"function": "ensure_system_map", "source_file": __file__},
                    )

            cache_key = (str(self.repo_root), manifest_hash)
            if not force:
                with _SOURCE_MAP_CACHE_LOCK:
                    shared = _SOURCE_MAP_CACHE.get(cache_key)
                if shared:
                    self._function_index = dict(shared)
                    self._rebuild_name_index()
                    if self.persist and not self.index_path.exists():
                        _atomic_write_json(self.index_path, {
                            "schema_version": _SCHEMA_VERSION,
                            "generated_at": time.time(),
                            "repo_root": str(self.repo_root),
                            "manifest_hash": manifest_hash,
                            "file_count": len(files),
                            "function_count": len(self._function_index),
                            "parse_errors": [],
                            "functions": self._function_index,
                        })
                    return self.system_map_status()

            functions: Dict[str, Dict[str, Any]] = {}
            parse_errors: List[Dict[str, Any]] = []
            for path in files:
                rel = str(path.relative_to(self.repo_root)).replace(os.sep, "/")
                try:
                    source = path.read_text(encoding="utf-8", errors="replace")
                    tree = ast.parse(source, filename=rel)
                    visitor = _FunctionVisitor(_module_name(self.repo_root, path), rel)
                    visitor.visit(tree)
                    for record in visitor.records:
                        functions[record.function_id] = asdict(record)
                except (OSError, SyntaxError, UnicodeError) as exc:
                    parse_errors.append({"file": rel, "error": str(exc)[:200]})
            self._function_index = functions
            self._rebuild_name_index()
            with _SOURCE_MAP_CACHE_LOCK:
                _SOURCE_MAP_CACHE[cache_key] = dict(functions)
                # Source manifests are normally stable for a process. Bound
                # the cache so development reloads cannot grow it forever.
                while len(_SOURCE_MAP_CACHE) > 4:
                    _SOURCE_MAP_CACHE.pop(next(iter(_SOURCE_MAP_CACHE)))
            payload = {
                "schema_version": _SCHEMA_VERSION,
                "generated_at": time.time(),
                "repo_root": str(self.repo_root),
                "manifest_hash": manifest_hash,
                "file_count": len(files),
                "function_count": len(functions),
                "parse_errors": parse_errors[:50],
                "functions": functions,
            }
            if self.persist:
                _atomic_write_json(self.index_path, payload)
            return self.system_map_status()

    def system_map_status(self) -> Dict[str, Any]:
        lineage_status: Dict[str, Any] = {}
        if isinstance(self._systems, dict):
            lineage = self._systems.get("function_lineage")
            if lineage is not None and hasattr(lineage, "status"):
                try:
                    lineage_status = dict(lineage.status() or {})
                except Exception:
                    lineage_status = {}
        return {
            "available": bool(self._function_index),
            "function_count": len(self._function_index),
            "index_path": str(self.index_path),
            "repo_root": str(self.repo_root),
            "function_lineage_available": bool(lineage_status.get("available", False)),
            "function_lineage_count": int(lineage_status.get("function_count", 0) or 0),
            "function_lineage_coverage": float(lineage_status.get("coverage_rate", 0.0) or 0.0),
        }

    def _lineage_for_function(self, function_id: str) -> Dict[str, Any]:
        if not isinstance(self._systems, dict):
            return {}
        lineage = self._systems.get("function_lineage")
        if lineage is None or not hasattr(lineage, "lineage_for"):
            return {}
        try:
            return dict(lineage.lineage_for(function_id) or {})
        except Exception:
            return {}

    def _score_function_match(self, query: str, fid: str, rec: Mapping[str, Any]) -> float:
        q = str(query or "").strip().lower()
        if not q:
            return 0.0
        q_tokens = set(re.findall(r"[a-z0-9_]+", q))
        fid_low = fid.lower()
        qual_low = str(rec.get("qualname", "")).lower()
        doc_low = str(rec.get("doc", "")).lower()
        calls_low = " ".join(str(x).lower() for x in rec.get("calls", []) or [])
        score = 0.0
        if q == fid_low:
            score += 10.0
        if fid_low.endswith(q) or qual_low == q:
            score += 7.0
        if q in fid_low:
            score += 4.0
        corpus_tokens = set(re.findall(r"[a-z0-9_]+", f"{fid_low} {doc_low} {calls_low}"))
        score += 0.8 * len(q_tokens & corpus_tokens)
        return score

    def find_functions(self, query: str, limit: int = 8) -> List[Dict[str, Any]]:
        if not self._function_index:
            self.ensure_system_map()
        ranked: List[Tuple[float, str, Dict[str, Any]]] = []
        for fid, rec in self._function_index.items():
            score = self._score_function_match(query, fid, rec)
            if score > 0.0:
                ranked.append((score, fid, dict(rec)))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        out = []
        for score, fid, rec in ranked[: max(1, int(limit))]:
            rec["match_score"] = round(score, 4)
            rec["function_id"] = fid
            lineage = self._lineage_for_function(fid)
            if lineage:
                rec["constraint_lineage"] = {
                    "root_constraints": list(lineage.get("root_constraints", []) or []),
                    "root_weights": dict(lineage.get("root_weights", {}) or {}),
                    "parents": list(lineage.get("parents", []) or []),
                    "co_evolved_with": list(lineage.get("co_evolved_with", []) or []),
                    "generation": int(lineage.get("generation", 1) or 1),
                    "lineage_kind": str(lineage.get("lineage_kind", "") or ""),
                    "root_paths": dict(lineage.get("root_paths", {}) or {}),
                    "traceable_roots": sorted(
                        root
                        for root, path in dict(lineage.get("root_paths", {}) or {}).items()
                        if path
                    ),
                    "lineage_confidence": float(lineage.get("lineage_confidence", 0.0) or 0.0),
                }
            out.append(rec)
        return out

    def describe_function(self, query: str) -> Dict[str, Any]:
        matches = self.find_functions(query, limit=1)
        return matches[0] if matches else {}

    # ------------------------------------------------------------------
    # Runtime attachment and episodes
    # ------------------------------------------------------------------

    def attach_systems(self, systems: Optional[Dict[str, Any]]) -> None:
        self._systems = systems if isinstance(systems, dict) else None
        if self._systems is not None:
            lineage = self._systems.get("function_lineage")
            genealogy = self._systems.get("genealogy")
            if lineage is not None and genealogy is not None and hasattr(lineage, "attach_genealogy"):
                try:
                    lineage.attach_genealogy(genealogy)
                except Exception:
                    pass

    def _active_episode_id(self) -> str:
        return str(getattr(self._local, "episode_id", "") or "")

    def begin_episode(
        self,
        user_input: str,
        *,
        turn_tick: int = 0,
        session_id: str = "",
        source: str = "runtime_dialogue",
    ) -> str:
        seed = f"{session_id}|{turn_tick}|{time.time_ns()}|{user_input[:100]}"
        episode_id = "INT:" + hashlib.sha1(seed.encode("utf-8", "replace")).hexdigest()[:14]
        episode = {
            "schema_version": _SCHEMA_VERSION,
            "episode_id": episode_id,
            "started_at": time.time(),
            "completed_at": 0.0,
            "session_id": str(session_id or ""),
            "turn_tick": int(turn_tick or 0),
            "source": str(source or "runtime_dialogue"),
            "user_input": str(user_input or "")[:_MAX_TEXT],
            "steps": [],
            "final": {},
            "existing_evidence": {},
            "diagnosis": {},
        }
        with self._lock:
            self._episodes[episode_id] = episode
            self._episode_order.append(episode_id)
            self._episode_order = self._episode_order[-self.max_episode_memory :]
            keep = set(self._episode_order)
            self._episodes = {k: v for k, v in self._episodes.items() if k in keep}
        self._local.episode_id = episode_id
        if self._systems is not None:
            self._systems["_active_introspection_episode"] = episode_id
        return episode_id

    def record_step(
        self,
        function_id: str,
        *,
        stage: str,
        inputs: Optional[Mapping[str, Any]] = None,
        derived: Optional[Mapping[str, Any]] = None,
        decision: str = "observed",
        output: Any = None,
        reason: str = "",
        confidence: float = 0.5,
        tags: Optional[Sequence[str]] = None,
        anomaly: Optional[str] = None,
        parent_step_id: str = "",
    ) -> str:
        episode_id = self._active_episode_id()
        if not episode_id:
            return ""
        with self._lock:
            episode = self._episodes.get(episode_id)
            if not episode:
                return ""
            steps = episode.setdefault("steps", [])
            if len(steps) >= _MAX_EPISODE_STEPS:
                return ""
            step_id = f"{episode_id}:S{len(steps) + 1:03d}"
            source_record = self.describe_function(function_id)
            step = {
                "step_id": step_id,
                "episode_id": episode_id,
                "sequence": len(steps) + 1,
                "timestamp": time.time(),
                "function_id": str(function_id or "unknown"),
                "stage": str(stage or "runtime"),
                "inputs": _safe_json_value(dict(inputs or {})),
                "derived": _safe_json_value(dict(derived or {})),
                "decision": str(decision or "observed"),
                "output": _safe_json_value(output),
                "reason": str(reason or "")[:_MAX_TEXT],
                "confidence": _clip01(confidence, 0.5),
                "tags": [str(tag)[:100] for tag in list(tags or [])[:20]],
                "anomaly": str(anomaly or "")[:200],
                "parent_step_id": str(parent_step_id or ""),
                "source": {
                    "file": source_record.get("file", ""),
                    "line": source_record.get("line", 0),
                    "end_line": source_record.get("end_line", 0),
                    "signature": source_record.get("signature", ""),
                },
            }
            steps.append(step)
            return step_id

    def record_boundary_decision(self, function_id: str, **kwargs: Any) -> str:
        return self.record_step(function_id, **kwargs)

    def _collect_existing_evidence(self, systems: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        target = systems if isinstance(systems, dict) else self._systems or {}
        evidence: Dict[str, Any] = {
            "articulation_arbitration": _safe_json_value(target.get("_last_articulation_arbitration") or {}),
            "validated_communication": _safe_json_value(target.get("_last_validated_communication_outcome") or {}),
            "gap_result": _safe_json_value(target.get("_last_gap_result") or {}),
            "pipeline_state": _safe_json_value(target.get("_last_pipeline_state") or {}),
            "last_runtime_fault": _safe_json_value(target.get("_last_runtime_fault") or {}),
        }
        # The stack tracer writes real call events into the conversation
        # memory's evolutionary trace.  Pull only the latest bounded trace so
        # Aurora can correlate high-level call activity with the exact
        # decision probes recorded by this bridge.
        memory = target.get("conversation_memory")
        if memory is not None:
            try:
                traces = list(getattr(memory, "evolutionary_trace_log", []) or [])
                if traces:
                    latest_trace = dict(traces[-1] or {})
                    evidence["evolutionary_trace"] = _safe_json_value({
                        "trace_id": latest_trace.get("trace_id", ""),
                        "opened_at": latest_trace.get("opened_at", 0.0),
                        "closed_at": latest_trace.get("closed_at"),
                        "causal_chain": latest_trace.get("causal_chain", []),
                        "mutations": list(latest_trace.get("mutations", []) or [])[-40:],
                        "pressure_before": latest_trace.get("pressure_before", {}),
                        "pressure_after": latest_trace.get("pressure_after", {}),
                        "applied_effects": latest_trace.get("applied_effects", {}),
                    })
            except Exception as _aurora_boundary_exc:
                _aurora_record_exception_from_locals(
                    locals(), module=__name__,
                    operation="system_introspection:collect_evolutionary_trace",
                    exc=_aurora_boundary_exc,
                    context={"function": "_collect_existing_evidence", "source_file": __file__},
                )

        instrumentation = target.get("trace_instrumentation")
        if instrumentation:
            evidence["trace_instrumentation"] = _safe_json_value(instrumentation)

        lineage = target.get("manual_code_lineage")
        if lineage is not None and hasattr(lineage, "status"):
            try:
                evidence["manual_code_lineage"] = _safe_json_value(lineage.status() or {})
            except Exception as _aurora_boundary_exc:
                _aurora_record_exception_from_locals(
                    locals(), module=__name__,
                    operation="system_introspection:collect_code_lineage",
                    exc=_aurora_boundary_exc,
                    context={"function": "_collect_existing_evidence", "source_file": __file__},
                )

        contract = target.get("understanding_contract")
        if contract is not None and hasattr(contract, "snapshot"):
            try:
                snap = dict(contract.snapshot() or {})
                evidence["understanding_contract"] = _safe_json_value(
                    {
                        "A": snap.get("A"),
                        "pending_validation": snap.get("pending_validation"),
                        "last_validation": snap.get("last_validation"),
                        "tensions": snap.get("tensions"),
                    }
                )
            except Exception as _aurora_boundary_exc:
                _aurora_record_exception_from_locals(
                    locals(), module=__name__,
                    operation="system_introspection:collect_understanding",
                    exc=_aurora_boundary_exc,
                    context={"function": "_collect_existing_evidence", "source_file": __file__},
                )
        try:
            from aurora_internal.aurora_attribution_trace import get_log

            log = list(get_log() or [])
            if log:
                evidence["attribution_turn"] = _safe_json_value(log[-1])
        except Exception:
            pass
        return evidence

    def _delivered_wellformed(self, text: str) -> Optional[bool]:
        if not str(text or "").strip():
            return False
        try:
            from aurora_internal.aurora_pf1_5_instruments import wellformed_and_coherent

            return bool(wellformed_and_coherent(text))
        except Exception:
            return None

    def finish_episode(
        self,
        *,
        delivered_text: str,
        response_source: str = "",
        confidence: float = 0.0,
        systems: Optional[Dict[str, Any]] = None,
        observed_problem: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        episode_id = self._active_episode_id()
        if not episode_id:
            return {}
        target = systems if isinstance(systems, dict) else self._systems or {}
        with self._lock:
            episode = self._episodes.get(episode_id)
            if not episode:
                return {}
            episode["completed_at"] = time.time()
            episode["final"] = {
                "delivered_text": str(delivered_text or "")[:_MAX_TEXT],
                "source": str(response_source or ""),
                "confidence": _clip01(confidence),
                "wellformed": self._delivered_wellformed(str(delivered_text or "")),
            }
            episode["existing_evidence"] = self._collect_existing_evidence(target)
            diagnosis = self.diagnose_episode(
                episode_id,
                observed_problem=observed_problem,
                persist=False,
            )
            episode["diagnosis"] = diagnosis
            self._last_diagnosis = dict(diagnosis or {})
            snapshot = _safe_json_value(episode)

        if self.persist:
            try:
                _append_jsonl(self.episode_path, snapshot)
                _atomic_write_json(self.last_episode_path, snapshot)
                if diagnosis:
                    _atomic_write_json(self.last_diagnosis_path, diagnosis)
            except Exception as _aurora_boundary_exc:
                _aurora_record_exception_from_locals(
                    locals(), module=__name__,
                    operation="system_introspection:finish_episode_persist",
                    exc=_aurora_boundary_exc,
                    context={"function": "finish_episode", "source_file": __file__},
                )

        if isinstance(target, dict):
            target["_last_system_introspection_episode"] = snapshot
            target["_last_system_diagnosis"] = dict(diagnosis or {})
            target["_introspection_code_targets"] = list(
                dict.fromkeys(
                    str(item.get("file", ""))
                    for item in diagnosis.get("inspection_targets", [])
                    if item.get("file")
                )
            )
            self._publish_to_existing_systems(target, diagnosis)
        self._local.episode_id = ""
        if isinstance(target, dict):
            target.pop("_active_introspection_episode", None)
        return diagnosis

    def _publish_to_existing_systems(self, systems: Dict[str, Any], diagnosis: Dict[str, Any]) -> None:
        if not diagnosis:
            return
        compact = {
            "episode_id": diagnosis.get("episode_id", ""),
            "problem_type": diagnosis.get("problem_type", ""),
            "likely_function": (diagnosis.get("likely_boundary") or {}).get("function_id", ""),
            "confidence": diagnosis.get("confidence", 0.0),
            "summary": diagnosis.get("summary", ""),
            "inspection_targets": diagnosis.get("inspection_targets", [])[:5],
        }
        contract = systems.get("understanding_contract")
        if contract is not None and hasattr(contract, "attach_pending_contributors"):
            try:
                contract.attach_pending_contributors({"system_introspection": compact})
            except Exception as _aurora_boundary_exc:
                _aurora_record_exception_from_locals(
                    locals(), module=__name__,
                    operation="system_introspection:publish_understanding",
                    exc=_aurora_boundary_exc,
                    context={"function": "_publish_to_existing_systems", "source_file": __file__},
                )
        observer = systems.get("quasiarch_observer")
        if observer is not None and hasattr(observer, "record_observation"):
            try:
                observer.record_observation(
                    target=str((diagnosis.get("likely_boundary") or {}).get("function_id") or "runtime_pipeline"),
                    data=compact,
                    source="SYSTEM_INTROSPECTION",
                )
            except Exception as _aurora_boundary_exc:
                _aurora_record_exception_from_locals(
                    locals(), module=__name__,
                    operation="system_introspection:publish_qao",
                    exc=_aurora_boundary_exc,
                    context={"function": "_publish_to_existing_systems", "source_file": __file__},
                )

    # ------------------------------------------------------------------
    # Diagnosis and backward tracing
    # ------------------------------------------------------------------

    def _infer_problem_type(
        self,
        episode: Mapping[str, Any],
        observed_problem: Optional[Mapping[str, Any]],
    ) -> Tuple[str, List[str]]:
        reasons: List[str] = []
        if observed_problem:
            ptype = str(observed_problem.get("type", "") or "observed_problem")
            reasons.append(str(observed_problem.get("description", "") or observed_problem.get("text", ""))[:_MAX_TEXT])
            return ptype, [r for r in reasons if r]
        final = dict(episode.get("final") or {})
        evidence = dict(episode.get("existing_evidence") or {})
        arbitration = dict(evidence.get("articulation_arbitration") or {})
        rejection_reasons = [str(x) for x in arbitration.get("rejection_reasons", []) or []]
        runtime_fault = dict(evidence.get("last_runtime_fault") or {})
        if runtime_fault and float(runtime_fault.get("timestamp", 0.0) or 0.0) >= float(episode.get("started_at", 0.0) or 0.0):
            reasons.append(str(runtime_fault.get("message", "") or "runtime fault"))
            return "runtime_fault", reasons
        if final.get("wellformed") is False:
            reasons.append("delivered response failed semantic well-formedness")
            return "malformed_delivered_response", reasons
        substantive_rejections = [
            r for r in rejection_reasons
            if r not in {"composer_empty", "no_grounded_candidate_to_compare", "meaning_preserved"}
        ]
        if substantive_rejections:
            reasons.extend(substantive_rejections)
            return "composer_semantic_rejection", reasons
        if not str(final.get("delivered_text", "") or "").strip():
            reasons.append("no response text was delivered")
            return "empty_response", reasons
        if float(final.get("confidence", 0.0) or 0.0) < 0.35:
            reasons.append("selected response confidence below introspection threshold")
            return "low_confidence_response", reasons
        return "no_confirmed_failure", reasons

    def _flatten_strings(self, value: Any) -> List[str]:
        out: List[str] = []
        if isinstance(value, str):
            out.append(value)
        elif isinstance(value, Mapping):
            for key, item in value.items():
                out.append(str(key))
                out.extend(self._flatten_strings(item))
        elif isinstance(value, (list, tuple, set)):
            for item in value:
                out.extend(self._flatten_strings(item))
        return out

    def _step_suspicion(
        self,
        step: Mapping[str, Any],
        problem_type: str,
        reason_terms: set[str],
    ) -> Tuple[float, List[str]]:
        score = 0.0
        why: List[str] = []
        decision = str(step.get("decision", "") or "").lower()
        anomaly = str(step.get("anomaly", "") or "")
        reason = str(step.get("reason", "") or "")
        tags = {str(x).lower() for x in step.get("tags", []) or []}
        strings = " ".join(self._flatten_strings({
            "inputs": step.get("inputs"),
            "derived": step.get("derived"),
            "output": step.get("output"),
            "reason": reason,
            "tags": list(tags),
        })).lower()
        if anomaly:
            score += 5.0
            why.append(f"step marked anomaly: {anomaly}")
        if decision in {"accepted", "selected", "emitted"} and "invalid" in tags:
            score += 5.0
            why.append("invalid material was accepted or emitted")
        if decision in {"rejected", "blocked", "failed"}:
            score += 1.2
            why.append(f"boundary decision was {decision}")
        if problem_type.startswith("composer") and ("composer" in strings or "slot_binding" in tags):
            score += 2.0
            why.append("step belongs to the composer path")
        if problem_type == "malformed_delivered_response" and (
            "composition" in tags or "articulation" in tags or "slot_binding" in tags
        ):
            score += 1.8
            why.append("step transformed visible language")
        overlap = sum(1 for term in reason_terms if term and term in strings)
        if overlap:
            score += min(3.0, overlap * 0.65)
            why.append(f"step evidence overlaps {overlap} problem terms")
        inputs = step.get("inputs") if isinstance(step.get("inputs"), Mapping) else {}
        derived = step.get("derived") if isinstance(step.get("derived"), Mapping) else {}
        output = step.get("output")
        token = _clean_token(inputs.get("token") or inputs.get("frame_object") or inputs.get("value"))
        inferred_role = str(derived.get("inferred_role", "") or "").lower()
        if token in _STRUCTURAL_INTERROGATIVES and inferred_role == "noun" and decision in {"accepted", "selected", "emitted"}:
            score += 8.0
            why.append("structural interrogative was treated as noun content")
        if token in _STRUCTURAL_INTERROGATIVES and _clean_token(output) == token:
            score += 6.0
            why.append("structural interrogative crossed the boundary unchanged")
        sequence = int(step.get("sequence", 0) or 0)
        score += min(0.8, sequence / 500.0)
        return score, why

    def diagnose_episode(
        self,
        episode_id: str,
        *,
        observed_problem: Optional[Mapping[str, Any]] = None,
        persist: bool = True,
    ) -> Dict[str, Any]:
        with self._lock:
            episode = self._episodes.get(str(episode_id or ""))
            if not episode:
                return {}
            problem_type, problem_reasons = self._infer_problem_type(episode, observed_problem)
            reason_terms = set(
                token
                for token in re.findall(r"[a-z0-9_]+", " ".join(problem_reasons).lower())
                if len(token) >= 3
            )
            ranked: List[Tuple[float, Dict[str, Any], List[str]]] = []
            for step in episode.get("steps", []) or []:
                score, why = self._step_suspicion(step, problem_type, reason_terms)
                if score > 0.0:
                    ranked.append((score, dict(step), why))
            ranked.sort(key=lambda item: (-item[0], -int(item[1].get("sequence", 0) or 0)))

            targets: List[Dict[str, Any]] = []
            seen: set[str] = set()
            for score, step, why in ranked:
                fid = str(step.get("function_id", "") or "")
                if not fid or fid in seen:
                    continue
                seen.add(fid)
                source = dict(step.get("source") or {})
                if not source.get("file"):
                    source = self.describe_function(fid)
                targets.append({
                    "function_id": fid,
                    "file": str(source.get("file", "") or ""),
                    "line": int(source.get("line", 0) or 0),
                    "confidence": round(min(0.98, 0.35 + score / 12.0), 4),
                    "reason": "; ".join(why[:4]),
                    "step_id": step.get("step_id", ""),
                    "decision": step.get("decision", ""),
                    "inputs": step.get("inputs", {}),
                    "derived": step.get("derived", {}),
                    "output": step.get("output"),
                })
                if len(targets) >= 8:
                    break

            # Runtime exceptions may be the only evidence when a failure
            # happened outside an instrumented boundary.
            evidence = dict(episode.get("existing_evidence") or {})
            runtime_fault = dict(evidence.get("last_runtime_fault") or {})
            if problem_type == "runtime_fault" and runtime_fault:
                context = dict(runtime_fault.get("context") or {})
                module_name = str(context.get("module", runtime_fault.get("subsystem", "")) or "")
                function_name = str(context.get("function", "") or "")
                requested_fid = ".".join(part for part in (module_name, function_name) if part)
                if requested_fid and requested_fid not in seen:
                    source_file = str(context.get("source_file", "") or "").replace("\\", "/")
                    candidates = self.find_functions(function_name or requested_fid, limit=24)
                    filtered = []
                    for candidate in candidates:
                        candidate_module = str(candidate.get("module", "") or "")
                        candidate_qualname = str(candidate.get("qualname", "") or "")
                        candidate_file = str(candidate.get("file", "") or "").replace("\\", "/")
                        module_ok = not module_name or candidate_module == module_name
                        function_ok = (
                            not function_name
                            or candidate_qualname == function_name
                            or candidate_qualname.endswith("." + function_name)
                        )
                        file_ok = (
                            not source_file
                            or candidate_file == source_file
                            or candidate_file.endswith("/" + Path(source_file).name)
                            or Path(candidate_file).name == Path(source_file).name
                        )
                        if module_ok and function_ok and file_ok:
                            filtered.append(candidate)
                    source = filtered[0] if filtered else (candidates[0] if candidates else {})
                    resolved_fid = str(source.get("function_id", "") or requested_fid)
                    seen.add(resolved_fid)
                    targets.insert(0, {
                        "function_id": resolved_fid,
                        "file": str(source.get("file", "") or source_file),
                        # Source-derived function lines are authoritative.
                        # Existing handler_line constants may drift as files evolve.
                        "line": int(source.get("line", 0) or context.get("handler_line", 0) or 0),
                        "confidence": 0.96 if source else 0.82,
                        "reason": str(runtime_fault.get("message", "") or "runtime fault localized here"),
                        "step_id": "runtime_fault",
                        "decision": "exception",
                        "inputs": {
                            **context,
                            "reported_handler_line": int(context.get("handler_line", 0) or 0),
                        },
                        "derived": {
                            "exception_type": runtime_fault.get("exception_type", ""),
                            "source_line_verified_from_ast": bool(source),
                        },
                        "output": None,
                    })

            # When no instrumented boundary matches, use Aurora's actual
            # source anatomy as a low-confidence inspection hypothesis.  This
            # is explicitly weaker than observed provenance and never claims
            # causal certainty.
            if not targets and problem_type != "no_confirmed_failure":
                search_parts = list(problem_reasons)
                search_parts.append(problem_type.replace("_", " "))
                arbitration = dict(evidence.get("articulation_arbitration") or {})
                search_parts.extend(str(x) for x in arbitration.get("rejection_reasons", []) or [])
                search_query = " ".join(part for part in search_parts if part).strip()
                if search_query:
                    for rec in self.find_functions(search_query, limit=5):
                        fid = str(rec.get("function_id", "") or "")
                        if not fid or fid in seen:
                            continue
                        seen.add(fid)
                        match_score = float(rec.get("match_score", 0.0) or 0.0)
                        targets.append({
                            "function_id": fid,
                            "file": str(rec.get("file", "") or ""),
                            "line": int(rec.get("line", 0) or 0),
                            "confidence": round(min(0.48, 0.20 + match_score / 40.0), 4),
                            "reason": "source-map hypothesis only; no observed decision boundary matched",
                            "step_id": "source_map_hypothesis",
                            "decision": "inspect",
                            "inputs": {"problem_query": search_query[:_MAX_TEXT]},
                            "derived": {"match_score": match_score},
                            "output": None,
                        })

            likely = dict(targets[0]) if targets else {}
            confidence = float(likely.get("confidence", 0.0) or 0.0)
            if problem_type == "no_confirmed_failure":
                confidence = min(confidence, 0.35)

            value_trail = []
            for _, step, _ in sorted(ranked[:16], key=lambda item: int(item[1].get("sequence", 0) or 0)):
                value_trail.append({
                    "step_id": step.get("step_id", ""),
                    "function_id": step.get("function_id", ""),
                    "decision": step.get("decision", ""),
                    "inputs": step.get("inputs", {}),
                    "derived": step.get("derived", {}),
                    "output": step.get("output"),
                })

            if likely:
                summary = (
                    f"The strongest observed boundary is {likely.get('function_id')} "
                    f"because {likely.get('reason') or 'its decision is nearest the failed result'}."
                )
            elif problem_type == "no_confirmed_failure":
                summary = "No confirmed runtime failure was present in this episode."
            else:
                summary = (
                    "Aurora detected a problem but does not yet have a sufficiently "
                    "instrumented decision boundary to localize it reliably."
                )

            diagnosis = {
                "schema_version": _SCHEMA_VERSION,
                "timestamp": time.time(),
                "episode_id": episode_id,
                "problem_type": problem_type,
                "problem_reasons": problem_reasons,
                "summary": summary,
                "confidence": round(_clip01(confidence), 4),
                "likely_boundary": likely,
                "inspection_targets": targets,
                "value_trail": value_trail,
                "delivered": dict(episode.get("final") or {}),
                "source_map_status": self.system_map_status(),
            }
            episode["diagnosis"] = diagnosis
            self._last_diagnosis = dict(diagnosis)

        if persist and self.persist:
            _atomic_write_json(self.last_diagnosis_path, diagnosis)
        return diagnosis

    def diagnose_latest(
        self,
        observed_problem: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        episode_id = self._active_episode_id()
        if not episode_id and self._episode_order:
            episode_id = self._episode_order[-1]
        if episode_id:
            return self.diagnose_episode(episode_id, observed_problem=observed_problem)
        return dict(self._last_diagnosis)

    def trace_value(self, value: str, *, episode_id: str = "") -> List[Dict[str, Any]]:
        wanted = _clean_token(value)
        if not wanted:
            return []
        episode_id = str(episode_id or self._active_episode_id() or (self._episode_order[-1] if self._episode_order else ""))
        episode = self._episodes.get(episode_id) or {}
        out: List[Dict[str, Any]] = []
        for step in episode.get("steps", []) or []:
            strings = [s.lower() for s in self._flatten_strings({
                "inputs": step.get("inputs"),
                "derived": step.get("derived"),
                "output": step.get("output"),
            })]
            if any(wanted in s for s in strings):
                out.append({
                    "step_id": step.get("step_id", ""),
                    "sequence": step.get("sequence", 0),
                    "function_id": step.get("function_id", ""),
                    "decision": step.get("decision", ""),
                    "inputs": step.get("inputs", {}),
                    "derived": step.get("derived", {}),
                    "output": step.get("output"),
                })
        return out

    def render_diagnosis(self, diagnosis: Optional[Mapping[str, Any]] = None) -> str:
        diag = dict(diagnosis or self._last_diagnosis or {})
        if not diag:
            return "I do not have a completed system diagnosis yet."
        likely = dict(diag.get("likely_boundary") or {})
        if not likely:
            return str(diag.get("summary", "I detected a problem but could not localize it."))
        file_part = str(likely.get("file", "") or "")
        line = int(likely.get("line", 0) or 0)
        location = f" in {file_part}:{line}" if file_part and line else (f" in {file_part}" if file_part else "")
        return (
            f"I traced the strongest problem boundary to {likely.get('function_id')}{location}. "
            f"{likely.get('reason') or diag.get('summary', '')} "
            f"My localization confidence is {float(diag.get('confidence', 0.0) or 0.0):.2f}."
        ).strip()

    def latest_episode(self) -> Dict[str, Any]:
        if self._episode_order:
            return dict(self._episodes.get(self._episode_order[-1]) or {})
        return {}

    def status(self) -> Dict[str, Any]:
        return {
            "available": True,
            "active_episode_id": self._active_episode_id(),
            "episodes_in_memory": len(self._episodes),
            "last_diagnosis": dict(self._last_diagnosis),
            "system_map": self.system_map_status(),
            "state_dir": str(self.state_dir),
        }

    def _load_last_state(self) -> None:
        try:
            if self.last_diagnosis_path.exists():
                payload = json.loads(self.last_diagnosis_path.read_text(encoding="utf-8") or "{}")
                if isinstance(payload, dict):
                    self._last_diagnosis = payload
        except Exception:
            self._last_diagnosis = {}


__all__ = ["AuroraSystemIntrospection", "FunctionRecord"]

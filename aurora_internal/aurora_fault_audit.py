# Authors: Sunni (Sir) Morningstar & Cael Devo
"""AST audit for swallowed exceptions in Aurora production code."""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class FaultHandler:
    path: str
    line: int
    function: str
    category: str
    visible: bool
    intentional: bool
    critical: bool


def production_files(root: Path) -> List[Path]:
    """Return source files covered by the production fault audit."""
    paths: List[Path] = []
    for pattern in ("*.py", "aurora_internal/**/*.py", "flutter_app/android/app/src/main/python/**/*.py"):
        paths.extend(root.glob(pattern))
    excluded_parts = {
        "tests",
        "__pycache__",
        "aurora_state",
        "aurora_runtime_output",
        "aurora_state_test",
    }
    unique = {
        p.resolve()
        for p in paths
        if p.is_file()
        and p.name not in {
            "aurora_fault_audit.py",
            "aurora_runtime_faults.py",
            "aurora_runtime_health.py",
        }
        and not any(part in excluded_parts for part in p.parts)
    }
    return sorted(unique)


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Call):
        fn = node.func
        if isinstance(fn, ast.Name):
            return fn.id
        if isinstance(fn, ast.Attribute):
            return fn.attr
    return ""


def _contains_visibility(nodes: Sequence[ast.AST]) -> bool:
    for node in ast.walk(ast.Module(body=list(nodes), type_ignores=[])):
        if isinstance(node, (ast.Raise, ast.Assert)):
            return True
        if isinstance(node, ast.Call):
            name = _call_name(node).lower()
            if any(token in name for token in (
                "record_runtime_fault",
                "record_exception_from_locals",
                "logger",
                "logging",
                "print",
                "warn",
                "warning",
                "error",
                "critical",
                "fault",
                "violation",
                "telemetry",
                "audit",
            )):
                return True
    return False


def _category(nodes: Sequence[ast.AST]) -> str:
    if nodes and all(isinstance(node, (ast.Pass, ast.Continue)) for node in nodes):
        return "silent_pass"
    if any(isinstance(node, (ast.Return, ast.Assign, ast.AnnAssign, ast.AugAssign)) for node in nodes):
        return "silent_fallback"
    return "other"


class _Visitor(ast.NodeVisitor):
    def __init__(self, path: Path, critical_names: Iterable[str]):
        self.path = path
        self.critical_names = set(critical_names)
        self.handlers: List[FaultHandler] = []
        self._functions: List[str] = []

    def _visit_function(self, node: ast.AST) -> None:
        name = getattr(node, "name", "<function>")
        self._functions.append(str(name))
        self.generic_visit(node)
        self._functions.pop()

    visit_FunctionDef = _visit_function
    visit_AsyncFunctionDef = _visit_function

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        category = _category(node.body)
        visible = _contains_visibility(node.body)
        line = int(getattr(node, "lineno", 0) or 0)
        source_line = ""
        try:
            source_line = self.path.read_text(encoding="utf-8", errors="replace").splitlines()[line - 1]
        except Exception:
            pass
        intentional = "aurora-fault-boundary: intentional" in source_line
        function = self._functions[-1] if self._functions else "<module>"
        critical = function in self.critical_names
        if category != "other" or not visible:
            self.handlers.append(FaultHandler(
                path=str(self.path),
                line=line,
                function=function,
                category=category,
                visible=visible,
                intentional=intentional,
                critical=critical,
            ))
        self.generic_visit(node)


def _critical_names(root: Path, policy_path: Optional[Path]) -> List[str]:
    if policy_path is None:
        policy_path = root / "deploy" / "fault-boundary-policy.json"
    try:
        payload = json.loads(policy_path.read_text(encoding="utf-8"))
        return [str(item) for item in payload.get("critical_functions", [])]
    except (OSError, json.JSONDecodeError, TypeError):
        return []


def audit_source_tree(root: Path, policy_path: Optional[Path] = None) -> Dict[str, Any]:
    critical_names = _critical_names(root, policy_path)
    handlers: List[FaultHandler] = []
    parse_errors: List[Dict[str, str]] = []
    for path in production_files(root):
        if path.name == "aurora_runtime_faults.py":
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=str(path))
        except (OSError, SyntaxError) as exc:
            parse_errors.append({"path": str(path), "error": str(exc)})
            continue
        visitor = _Visitor(path, critical_names)
        visitor.visit(tree)
        handlers.extend(visitor.handlers)

    silent = [item for item in handlers if item.category in {"silent_pass", "silent_fallback"}]
    unreported = [item for item in silent if not item.visible and not item.intentional]
    critical_unreported = [item for item in unreported if item.critical]
    return {
        "handlers": len(handlers),
        "visible_or_raised": sum(1 for item in handlers if item.visible),
        "silent_pass": sum(1 for item in handlers if item.category == "silent_pass"),
        "silent_fallback": sum(1 for item in handlers if item.category == "silent_fallback"),
        "intentional": sum(1 for item in silent if item.intentional),
        "unreported": len(unreported),
        "critical_unreported": len(critical_unreported),
        "parse_errors": parse_errors,
        "critical_unreported_handlers": [asdict(item) for item in critical_unreported],
        "unreported_handlers": [asdict(item) for item in unreported],
    }


__all__ = ["audit_source_tree", "production_files"]

#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Zip integration phase C: build the exception-instrumentation injector.

Sunni's uploaded operational-hardening zip contains a codebase-wide pass
that inserted `_aurora_record_exception_from_locals(...)` calls into
3336 silent exception handlers across 198 files, but the actual tool
that produced that pass was not included in the zip -- only its output,
plus a read-only AST scanner (`aurora_internal/aurora_fault_audit.py`,
already ported in phase A) that finds the same handlers without
touching them.

This script is a fresh injector, using `aurora_fault_audit`'s own
classification rules (imported directly, not re-implemented, so the
two tools cannot drift apart) as the detection engine, that reproduces
the zip's exact demonstrated call shape:

    except SomeError as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(),
            module=__name__,
            operation="exception_handler:<file>:<line>",
            exc=_aurora_boundary_exc,
            context={"function": "<func>", "handler_line": <line>, "source_file": "<file>"},
        )
        <original handler body, unchanged>

plus a top-of-file import of `record_exception_from_locals` (aliased to
`_aurora_record_exception_from_locals`) in every modified file.

Uses `tokenize` (not naive text/regex splicing) to find the exact
column of the colon that ends an `except` clause header, so multi-line
`except (A, B) as e:` clauses are handled correctly. Every rewritten
file is re-parsed with `ast.parse` before being kept; any file whose
rewritten source fails to parse is left untouched and reported as a
skip, never partially written.
"""
from __future__ import annotations

import argparse
import ast
import io
import sys
import tokenize
from pathlib import Path
from typing import List, NamedTuple, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from aurora_internal.aurora_fault_audit import (  # noqa: E402
    _category,
    _contains_visibility,
    production_files,
)

IMPORT_LINE = (
    "from aurora_internal.aurora_runtime_faults import "
    "record_exception_from_locals as _aurora_record_exception_from_locals"
)
BOUNDARY_MARKER = "aurora-fault-boundary: intentional"


class Target(NamedTuple):
    lineno: int          # line of the `except` keyword
    col_offset: int
    name: Optional[str]  # existing `as X` name, or None
    body_first_line: int
    body_col: int
    function: str


class _InjectorVisitor(ast.NodeVisitor):
    """Mirrors aurora_fault_audit._Visitor's classification exactly,
    but keeps the raw node (not just a summary dataclass) since the
    injector needs precise source positions."""

    def __init__(self, path: Path, source: str):
        self.path = path
        self._source_lines = source.splitlines()
        self.targets: List[Target] = []
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
        source_line = self._source_lines[line - 1] if 0 < line <= len(self._source_lines) else ""
        intentional = BOUNDARY_MARKER in source_line
        if category != "other" or not visible:
            if not visible and not intentional:
                first_body = node.body[0]
                self.targets.append(Target(
                    lineno=line,
                    col_offset=int(getattr(node, "col_offset", 0) or 0),
                    name=node.name,
                    body_first_line=int(first_body.lineno),
                    body_col=int(first_body.col_offset),
                    function=self._functions[-1] if self._functions else "<module>",
                ))
        self.generic_visit(node)


def _find_header_colon(tokens: List[tokenize.TokenInfo], except_lineno: int, except_col: int):
    """Return the (row, col) of the ':' that ends this except clause's
    header, using bracket-depth tracking so multi-line/tuple exception
    types don't fool a naive first-colon search."""
    started = False
    depth = 0
    for tok in tokens:
        if not started:
            if tok.type == tokenize.NAME and tok.string == "except" and tok.start == (except_lineno, except_col):
                started = True
            continue
        if tok.type == tokenize.OP:
            if tok.string in "([{":
                depth += 1
            elif tok.string in ")]}":
                depth -= 1
            elif tok.string == ":" and depth == 0:
                return tok.start
    raise ValueError(f"could not locate header colon for except at {except_lineno}:{except_col}")


def _indent_of(line: str) -> str:
    return line[: len(line) - len(line.lstrip(" \t"))]


def _build_injected_block(indent: str, exc_name: str, rel_path: str, target: Target) -> List[str]:
    ctx = (
        f'{{"function": "{target.function}", "handler_line": {target.lineno}, '
        f'"source_file": "{rel_path}"}}'
    )
    return [
        f"{indent}_aurora_record_exception_from_locals(",
        f"{indent}    locals(),",
        f"{indent}    module=__name__,",
        f'{indent}    operation="exception_handler:{rel_path}:{target.lineno}",',
        f"{indent}    exc={exc_name},",
        f"{indent}    context={ctx},",
        f"{indent})",
    ]


def _insert_import(lines: List[str]) -> List[str]:
    if any(IMPORT_LINE in line for line in lines):
        return lines
    joined = "\n".join(lines)
    try:
        module = ast.parse(joined)
    except SyntaxError:
        return lines[:1] + [IMPORT_LINE] + lines[1:]

    insert_at = 0
    body = list(module.body)
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(getattr(body[0], "value", None), ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        insert_at = int(body[0].end_lineno or 0)
        body = body[1:]
    # `from __future__ import ...` must remain the first real statement
    # in the file -- our own import must land after it, not before.
    while body and isinstance(body[0], ast.ImportFrom) and body[0].module == "__future__":
        insert_at = int(body[0].end_lineno or insert_at)
        body = body[1:]
    return lines[:insert_at] + [IMPORT_LINE] + lines[insert_at:]


def instrument_file(path: Path, *, dry_run: bool = False) -> int:
    """Rewrite one file in place. Returns the number of handlers
    instrumented, or -1 if the file was skipped (parse failure either
    before or after rewriting)."""
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return -1

    visitor = _InjectorVisitor(path, source)
    visitor.visit(tree)
    if not visitor.targets:
        return 0

    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except Exception:
        return -1

    lines = source.splitlines(keepends=True)
    rel_path = str(path.relative_to(REPO_ROOT))

    # Process bottom-up so earlier edits don't shift later line numbers.
    for target in sorted(visitor.targets, key=lambda t: t.lineno, reverse=True):
        try:
            row, col = _find_header_colon(tokens, target.lineno, target.col_offset)
        except ValueError:
            return -1
        header_line = lines[row - 1]
        header_indent = _indent_of(header_line)
        before_colon = header_line[:col]
        # Everything after the colon on the header's own line -- for a
        # normal multi-line handler this is just whitespace/newline; for
        # a single-line handler (`except Exception: pass`) it is the
        # entire body, which must be split out onto its own line rather
        # than left dangling after a colon we're about to relocate.
        after_colon = header_line[col + 1:]
        inline_body = after_colon.strip("\n").strip()

        if target.name is not None:
            exc_name = target.name
        else:
            exc_name = "_aurora_boundary_exc"
            before_colon = before_colon + f" as {exc_name}"

        lines[row - 1] = before_colon + ":\n"

        body_indent = (
            header_indent + "    " if inline_body else _indent_of(lines[target.body_first_line - 1])
        )
        block = _build_injected_block(body_indent, exc_name, rel_path, target)
        if inline_body:
            block.append(f"{body_indent}{inline_body}")
        insertion = "".join(f"{line}\n" for line in block)
        lines.insert(row, insertion)

    new_source = "".join(lines)
    new_lines = _insert_import(new_source.splitlines())
    new_source = "\n".join(new_lines) + ("\n" if new_source.endswith("\n") else "")

    try:
        ast.parse(new_source, filename=str(path))
    except SyntaxError as exc:
        print(f"SKIP (post-rewrite parse failure): {rel_path}: {exc}", file=sys.stderr)
        return -1

    if not dry_run:
        path.write_text(new_source, encoding="utf-8")
    return len(visitor.targets)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Report counts without writing files.")
    parser.add_argument("--only", nargs="*", default=None, help="Restrict to these relative file paths.")
    args = parser.parse_args()

    files = production_files(REPO_ROOT)
    if args.only:
        wanted = {str((REPO_ROOT / p).resolve()) for p in args.only}
        files = [f for f in files if str(f.resolve()) in wanted]

    total = 0
    skipped: List[str] = []
    touched = 0
    for path in files:
        count = instrument_file(path, dry_run=args.dry_run)
        if count < 0:
            skipped.append(str(path.relative_to(REPO_ROOT)))
        elif count > 0:
            touched += 1
            total += count
            print(f"{path.relative_to(REPO_ROOT)}: {count} handler(s) instrumented")

    print(f"\nTotal: {total} handlers across {touched} files. Skipped: {len(skipped)}.")
    if skipped:
        print("Skipped files:")
        for s in skipped:
            print(f"  {s}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

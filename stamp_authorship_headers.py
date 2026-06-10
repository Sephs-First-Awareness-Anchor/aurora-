#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
stamp_authorship_headers.py — One-shot, idempotent authorship header pass.

Walks the repo and ensures every Aurora .py file carries:

    # Authors: Sunni (Sir) Morningstar & Cael Devo

Placement rules (matches FIX-F002):
  * If the file has a module docstring, the header goes on the line
    immediately after the closing quotes.
  * Otherwise it goes after the shebang/encoding line, or at line 1.
  * Files that already contain "Morningstar" anywhere in the first 20
    lines are skipped — safe to re-run any time.

Usage:
    python3 stamp_authorship_headers.py            # dry run (report only)
    python3 stamp_authorship_headers.py --write    # apply changes
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

HEADER = "# Authors: Sunni (Sir) Morningstar & Cael Devo\n"
SKIP_DIRS = {".git", "__pycache__", "node_modules", "aurora_archive"}


def has_header(source: str, lines: list[str]) -> bool:
    # Whole-file check for the exact header (it may sit after a long module
    # docstring), plus a loose first-20-line check for pre-existing variants.
    return HEADER.strip() in source or any("Morningstar" in ln for ln in lines[:20])


def insertion_line(source: str) -> int:
    """Return 0-based line index where the header should be inserted."""
    lines = source.splitlines(keepends=True)
    idx = 0
    # Skip shebang and encoding lines
    if lines and lines[0].startswith("#!"):
        idx = 1
    if len(lines) > idx and ("coding:" in lines[idx] or "coding=" in lines[idx]):
        idx += 1
    # If a module docstring exists, place header just after it
    try:
        tree = ast.parse(source)
        if (tree.body
                and isinstance(tree.body[0], ast.Expr)
                and isinstance(tree.body[0].value, ast.Constant)
                and isinstance(tree.body[0].value.value, str)):
            end = tree.body[0].end_lineno  # 1-based
            if end is not None:
                return end  # insert on the line after the docstring
    except SyntaxError:
        pass
    return idx


def main() -> None:
    write = "--write" in sys.argv
    root = Path(__file__).resolve().parent
    stamped, skipped = 0, 0
    for path in sorted(root.rglob("*.py")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        lines = source.splitlines(keepends=True)
        if has_header(source, lines):
            skipped += 1
            continue
        at = insertion_line(source)
        new_lines = lines[:at] + [HEADER] + lines[at:]
        if write:
            path.write_text("".join(new_lines), encoding="utf-8")
        print(f"  {'STAMPED' if write else 'WOULD STAMP'}: {path.relative_to(root)}")
        stamped += 1
    mode = "applied" if write else "dry run — rerun with --write to apply"
    print(f"\n  {stamped} file(s) stamped, {skipped} already compliant ({mode})")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
aurora_stack_export.py

Combine a codebase directory into one large Markdown document.

Usage:
    python aurora_stack_export.py /path/to/Aurora
    python aurora_stack_export.py /path/to/Aurora -o aurora_full_stack.md
    python aurora_stack_export.py /path/to/Aurora --extensions .py .json .md .txt
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Iterable


DEFAULT_EXTENSIONS = {
    ".py",
    ".json",
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".csv",
    ".ts",
    ".js",
    ".jsx",
    ".tsx",
    ".html",
    ".css",
    ".sh",
    ".bat",
    ".ps1",
    ".xml",
}

SKIP_DIRS = {
    "__pycache__",
    ".git",
    ".idea",
    ".vscode",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "dist",
    "build",
    ".next",
    ".turbo",
}

SKIP_FILES = {
    ".DS_Store",
    "Thumbs.db",
}

LANGUAGE_MAP = {
    ".py": "python",
    ".json": "json",
    ".md": "markdown",
    ".txt": "text",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".ini": "ini",
    ".cfg": "ini",
    ".csv": "csv",
    ".ts": "typescript",
    ".js": "javascript",
    ".jsx": "jsx",
    ".tsx": "tsx",
    ".html": "html",
    ".css": "css",
    ".sh": "bash",
    ".bat": "bat",
    ".ps1": "powershell",
    ".xml": "xml",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a directory into one large Markdown document."
    )
    parser.add_argument(
        "source_dir",
        type=Path,
        help="Path to the Aurora directory",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("aurora_full_stack_export.md"),
        help="Output markdown file path",
    )
    parser.add_argument(
        "--extensions",
        nargs="*",
        default=None,
        help="Optional list of extensions to include, e.g. .py .json .md",
    )
    parser.add_argument(
        "--include-no-extension",
        action="store_true",
        help="Include files without an extension",
    )
    parser.add_argument(
        "--max-file-size-kb",
        type=int,
        default=1024,
        help="Skip files larger than this many KB (default: 1024)",
    )
    return parser.parse_args()


def is_text_file(path: Path) -> bool:
    """
    Lightweight text-file check.
    Reads a small chunk and rejects files with null bytes.
    """
    try:
        with path.open("rb") as f:
            chunk = f.read(4096)
        return b"\x00" not in chunk
    except OSError:
        return False


def should_skip_dir(dirname: str) -> bool:
    return dirname in SKIP_DIRS


def should_include_file(
    path: Path,
    allowed_extensions: set[str] | None,
    include_no_extension: bool,
    max_file_size_kb: int,
) -> bool:
    if path.name in SKIP_FILES:
        return False

    if not path.is_file():
        return False

    try:
        if path.stat().st_size > max_file_size_kb * 1024:
            return False
    except OSError:
        return False

    suffix = path.suffix.lower()

    if allowed_extensions is not None:
        if suffix:
            if suffix not in allowed_extensions:
                return False
        elif not include_no_extension:
            return False
    else:
        if suffix:
            if suffix not in DEFAULT_EXTENSIONS:
                return False
        elif not include_no_extension:
            return False

    if not is_text_file(path):
        return False

    return True


def iter_files(
    source_dir: Path,
    allowed_extensions: set[str] | None,
    include_no_extension: bool,
    max_file_size_kb: int,
) -> Iterable[Path]:
    for root, dirs, files in os.walk(source_dir):
        dirs[:] = [d for d in dirs if not should_skip_dir(d)]

        root_path = Path(root)
        for filename in sorted(files):
            path = root_path / filename
            if should_include_file(
                path,
                allowed_extensions,
                include_no_extension,
                max_file_size_kb,
            ):
                yield path


def markdown_anchor_for(path_text: str) -> str:
    """
    GitHub-style-ish anchor approximation for internal markdown links.
    """
    anchor = path_text.strip().lower()
    cleaned = []
    for ch in anchor:
        if ch.isalnum() or ch in {"-", "_", " ", ".", "/"}:
            cleaned.append(ch)
    anchor = "".join(cleaned)
    anchor = anchor.replace(" ", "-").replace("/", "").replace(".", "")
    return anchor


def read_text(path: Path) -> str:
    encodings = ("utf-8", "utf-8-sig", "latin-1")
    for encoding in encodings:
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
        except OSError as e:
            return f"<<ERROR READING FILE: {e}>>"
    return "<<ERROR READING FILE: unable to decode text>>"


def code_fence_language(path: Path) -> str:
    return LANGUAGE_MAP.get(path.suffix.lower(), "text")


def build_document(
    source_dir: Path,
    files: list[Path],
) -> str:
    lines: list[str] = []

    lines.append(f"# Aurora Stack Export")
    lines.append("")
    lines.append(f"**Source directory:** `{source_dir.resolve()}`")
    lines.append(f"**Files included:** {len(files)}")
    lines.append("")

    lines.append("## Table of Contents")
    lines.append("")
    for file_path in files:
        rel = file_path.relative_to(source_dir).as_posix()
        anchor = markdown_anchor_for(rel)
        lines.append(f"- [{rel}](#{anchor})")
    lines.append("")

    for file_path in files:
        rel = file_path.relative_to(source_dir).as_posix()
        anchor = markdown_anchor_for(rel)
        lang = code_fence_language(file_path)
        content = read_text(file_path)

        lines.append(f"## {rel}")
        lines.append(f'<a id="{anchor}"></a>')
        lines.append("")
        lines.append(f"**Relative path:** `{rel}`")
        lines.append("")
        lines.append(f"```{lang}")
        lines.append(content.rstrip())
        lines.append("```")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    source_dir: Path = args.source_dir

    if not source_dir.exists():
        print(f"ERROR: Source directory does not exist: {source_dir}")
        return 1

    if not source_dir.is_dir():
        print(f"ERROR: Source path is not a directory: {source_dir}")
        return 1

    allowed_extensions = None
    if args.extensions is not None and len(args.extensions) > 0:
        allowed_extensions = {ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in args.extensions}

    files = sorted(
        iter_files(
            source_dir=source_dir,
            allowed_extensions=allowed_extensions,
            include_no_extension=args.include_no_extension,
            max_file_size_kb=args.max_file_size_kb,
        ),
        key=lambda p: p.relative_to(source_dir).as_posix().lower(),
    )

    if not files:
        print("No matching text files found to export.")
        return 1

    document = build_document(source_dir, files)

    try:
        args.output.write_text(document, encoding="utf-8")
    except OSError as e:
        print(f"ERROR: Could not write output file: {e}")
        return 1

    print(f"Export complete: {args.output.resolve()}")
    print(f"Included {len(files)} files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

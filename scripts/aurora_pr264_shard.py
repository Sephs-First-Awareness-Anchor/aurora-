#!/usr/bin/env python3
"""Deterministic file-level partition of Aurora's repo-wide Python test suite.

Each tracked test module belongs to exactly one of 12 shards. The assignment
is load-balanced by the previous module's file size as a reproducible proxy
for likely test cost, rather than an arbitrary hash of test names.
"""
from __future__ import annotations

import argparse
from pathlib import Path

EXCLUDED_PARTS = {
    ".git", ".buildozer", ".venv", "venv", "node_modules",
    ".dart_tool", "build", "dist", "__pycache__", ".pytest_cache",
}


def tracked_test_files(root: Path) -> list[str]:
    from subprocess import check_output
    tracked = check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard"],
                           cwd=root, text=True).splitlines()
    candidates = []
    for raw in tracked:
        path = Path(raw)
        if any(part in EXCLUDED_PARTS for part in path.parts):
            continue
        if path.suffix != ".py":
            continue
        if not (path.name.startswith("test_") or path.name.endswith("_test.py")):
            continue
        file = root / path
        if file.is_file():
            candidates.append(raw)
    return sorted(set(candidates))


def partition(root: Path, n: int) -> list[list[str]]:
    groups = [[] for _ in range(n)]
    sizes = [0] * n
    files = tracked_test_files(root)
    # Stable greedy load-balancing; the complete set never drops a file.
    for path in sorted(files, key=lambda f: (-(root / f).stat().st_size, f)):
        index = min(range(n), key=lambda k: (sizes[k], len(groups[k]), k))
        groups[index].append(path)
        sizes[index] += (root / path).stat().st_size
    return [sorted(g) for g in groups]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=int, required=True)
    parser.add_argument("--count", type=int, default=12)
    args = parser.parse_args()
    if args.count < 1 or not (0 <= args.index < args.count):
        parser.error("index must be in [0, count)")
    root = Path(__file__).resolve().parents[1]
    groups = partition(root, args.count)
    for path in groups[args.index]:
        print(path)


if __name__ == "__main__":
    main()

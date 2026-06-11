#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from sentinel import compress_target


BASE_DIR = Path(__file__).parent
DEFAULT_ARCHIVE_DIR = BASE_DIR / "CrystalZip_Archives"
DEFAULT_QUARANTINE_DIR = BASE_DIR / "CrystalZip_Quarantine"

DEFAULT_SKIP_DIRS = {
    ".git",
    ".agents",
    ".codex",
    ".venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
}

DEFAULT_SKIP_SUFFIXES = {
    ".cz",
    ".zip",
    ".7z",
    ".rar",
    ".gz",
    ".xz",
    ".bz2",
    ".zst",
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
    ".mp4",
    ".mov",
    ".mkv",
    ".mp3",
    ".wav",
    ".flac",
    ".ogg",
}

DEFAULT_CANDIDATES = [
    "aurora_state_backup",
    
    "Models",
]


def _log(message: str) -> None:
    print(message, flush=True)


def _safe_targets(roots: Iterable[Path], min_size_bytes: int) -> List[Path]:
    targets: List[Path] = []
    for root in roots:
        root = root.expanduser()
        if not root.exists():
            continue
        if root.is_file():
            if root.suffix.lower() in DEFAULT_SKIP_SUFFIXES:
                continue
            if root.stat().st_size >= min_size_bytes:
                targets.append(root)
            continue

        for child in sorted(root.iterdir()):
            name = child.name
            if name in DEFAULT_SKIP_DIRS or child.suffix.lower() in DEFAULT_SKIP_SUFFIXES:
                continue
            try:
                if child.is_file():
                    if child.stat().st_size >= min_size_bytes:
                        targets.append(child)
                elif child.is_dir():
                    size = 0
                    for dirpath, dirnames, filenames in os.walk(child):
                        dirnames[:] = [d for d in dirnames if d not in DEFAULT_SKIP_DIRS]
                        for fname in filenames:
                            fp = Path(dirpath) / fname
                            if fp.suffix.lower() in DEFAULT_SKIP_SUFFIXES:
                                continue
                            try:
                                size += fp.stat().st_size
                            except OSError:
                                pass
                    if size >= min_size_bytes:
                        targets.append(child)
            except OSError:
                continue
    return targets


def _default_output_dir() -> Path:
    return DEFAULT_ARCHIVE_DIR


def cmd_scan(args: argparse.Namespace) -> int:
    roots = [Path(item) for item in (args.roots or DEFAULT_CANDIDATES)]
    targets = _safe_targets(roots, int(args.min_size_mb * 1024 * 1024))
    report: List[Dict[str, Any]] = []
    for target in targets:
        report.append({
            "target": str(target),
            "bytes": target.stat().st_size if target.is_file() else None,
            "kind": "file" if target.is_file() else "dir",
        })
    print(json.dumps({"candidates": report, "count": len(report)}, indent=2))
    return 0


def _archive_name(path: Path) -> str:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    suffix = "file" if path.is_file() else "dir"
    return f"{path.name}_{suffix}_{stamp}.cz"


def cmd_compress(args: argparse.Namespace) -> int:
    roots = [Path(item) for item in (args.roots or DEFAULT_CANDIDATES)]
    min_size_bytes = int(args.min_size_mb * 1024 * 1024)
    targets = _safe_targets(roots, min_size_bytes)
    if not targets:
        print(json.dumps({"compressed": [], "message": "no eligible targets found"}, indent=2))
        return 0

    out_dir = Path(args.out or _default_output_dir())
    quarantine_dir = Path(args.quarantine_dir) if args.quarantine_dir else DEFAULT_QUARANTINE_DIR
    results: List[Dict[str, Any]] = []

    for target in targets:
        target_archive_dir = out_dir / target.name
        target_archive_dir.mkdir(parents=True, exist_ok=True)
        before = target.stat().st_size if target.is_file() else None
        if target.is_dir():
            before = 0
            for dirpath, dirnames, filenames in os.walk(target):
                dirnames[:] = [d for d in dirnames if d not in DEFAULT_SKIP_DIRS]
                for fname in filenames:
                    fp = Path(dirpath) / fname
                    if fp.suffix.lower() in DEFAULT_SKIP_SUFFIXES:
                        continue
                    try:
                        before += fp.stat().st_size
                    except OSError:
                        pass

        archive_path = target_archive_dir / _archive_name(target)
        _log(f"[CrystalZip] packing {target} -> {archive_path}")
        if args.dry_run:
            results.append({
                "target": str(target),
                "archive": str(archive_path),
                "dry_run": True,
                "original_bytes": before,
            })
            continue

        result = compress_target(
            target,
            target_archive_dir,
            level=int(args.level),
            quarantine=bool(args.quarantine),
            quarantine_dir=quarantine_dir,
        )
        result["original_bytes"] = before
        results.append(result)

    print(json.dumps({
        "targets": [str(t) for t in targets],
        "results": results,
        "dry_run": bool(args.dry_run),
        "quarantine": bool(args.quarantine),
    }, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="crystalzip-batch", description="Batch CrystalZip compressor for cold local data")
    sub = p.add_subparsers(dest="cmd", required=True)

    scan = sub.add_parser("scan", help="list eligible targets")
    scan.add_argument("--roots", nargs="*")
    scan.add_argument("--min-size-mb", type=float, default=100.0)
    scan.set_defaults(func=cmd_scan)

    comp = sub.add_parser("compress", help="compress eligible targets")
    comp.add_argument("--roots", nargs="*")
    comp.add_argument("--out")
    comp.add_argument("--quarantine-dir")
    comp.add_argument("--level", type=int, default=6)
    comp.add_argument("--min-size-mb", type=float, default=100.0)
    comp.add_argument("--quarantine", action="store_true")
    comp.add_argument("--dry-run", action="store_true")
    comp.set_defaults(func=cmd_compress)

    return p


def main(argv: List[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

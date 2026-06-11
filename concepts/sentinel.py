#!/usr/bin/env python3
"""
CrystalZip Sentinel MVP
=======================

Local-first storage compressor.

What it does:
    - scans folders for compression savings
    - compresses folders/files into .cz archives
    - verifies every archive after compression
    - optionally watches cold folders by modified age
    - restores archives safely

It does NOT upload files.
It does NOT delete originals automatically.
It does NOT use fuzzy matching or lossy tricks.

Usage:
    python3 sentinel.py scan /path/to/folder
    python3 sentinel.py compress /path/to/folder -o /path/to/archive_dir
    python3 sentinel.py restore /path/to/archive.cz -o /path/to/restore_dir
    python3 sentinel.py watch --config sentinel_config.json
    python3 sentinel.py init-config -o sentinel_config.json
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Tuple


APP_NAME = "CrystalZip Sentinel"
DEFAULT_CONFIG = {
    "watched_folders": [],
    "archive_output_dir": "./CrystalZip_Archives",
    "cold_days": 30,
    "min_folder_size_mb": 5,
    "mode": "manual_approve",
    "quarantine_originals": False,
    "quarantine_dir": "./CrystalZip_Quarantine",
    "compression_level": 6,
    "skip_extensions": [".cz", ".zip", ".7z", ".rar", ".gz", ".xz", ".mp3", ".mp4", ".jpg", ".jpeg", ".png", ".webp", ".mov"],
}


def engine_path() -> Path:
    return Path(__file__).with_name("crystalzip.py")


def run_engine(args: List[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(engine_path()), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def folder_size(path: Path, skip_extensions: List[str] | None = None) -> int:
    skip_extensions = [x.lower() for x in (skip_extensions or [])]
    if path.is_file():
        if path.suffix.lower() in skip_extensions:
            return 0
        return path.stat().st_size
    total = 0
    for root, _, files in os.walk(path):
        for name in files:
            fp = Path(root) / name
            if fp.suffix.lower() in skip_extensions:
                continue
            try:
                total += fp.stat().st_size
            except OSError:
                pass
    return total


def newest_mtime(path: Path) -> float:
    if path.is_file():
        return path.stat().st_mtime
    latest = path.stat().st_mtime
    for root, dirs, files in os.walk(path):
        for name in dirs + files:
            fp = Path(root) / name
            try:
                latest = max(latest, fp.stat().st_mtime)
            except OSError:
                pass
    return latest


def safe_archive_name(path: Path) -> str:
    base = path.name.strip().replace(" ", "_")
    stamp = time.strftime("%Y%m%d_%H%M%S")
    return f"{base}_{stamp}.cz"


def make_zip_baseline(input_path: Path, output_zip: Path, skip_extensions: List[str] | None = None) -> None:
    skip_extensions = [x.lower() for x in (skip_extensions or [])]
    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        if input_path.is_file():
            if input_path.suffix.lower() not in skip_extensions:
                zf.write(input_path, arcname=input_path.name)
            return
        root_name = input_path.name
        for root, _, files in os.walk(input_path):
            for name in files:
                fp = Path(root) / name
                if fp.suffix.lower() in skip_extensions:
                    continue
                arcname = str(Path(root_name) / fp.relative_to(input_path)).replace("\\", "/")
                zf.write(fp, arcname=arcname)


def scan_target(path: Path, level: int = 6, skip_extensions: List[str] | None = None) -> Dict[str, Any]:
    import tempfile

    if not path.exists():
        raise FileNotFoundError(str(path))

    raw_bytes = folder_size(path, skip_extensions=skip_extensions)

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        cz = td / "test.cz"
        zp = td / "test.zip"

        # For now, engine packs whole target. Skip extensions are only used in the size/zip estimate.
        # Future build should pass exclusion filters into engine directly.
        cz_proc = run_engine(["pack", "-o", str(cz), "--level", str(level), str(path)])
        if cz_proc.returncode != 0:
            raise RuntimeError(cz_proc.stderr or cz_proc.stdout)

        make_zip_baseline(path, zp, skip_extensions=skip_extensions)

        cz_size = cz.stat().st_size
        zip_size = zp.stat().st_size
        savings_vs_zip = zip_size - cz_size

        verify_proc = run_engine(["test", str(cz)])
        verify_ok = verify_proc.returncode == 0

    return {
        "target": str(path),
        "original_bytes": raw_bytes,
        "zip_estimate_bytes": zip_size,
        "crystalzip_estimate_bytes": cz_size,
        "savings_vs_zip_bytes": savings_vs_zip,
        "savings_vs_zip_pct": round((savings_vs_zip / zip_size * 100.0) if zip_size else 0.0, 2),
        "verify_ok": verify_ok,
        "recommendation": "compress" if savings_vs_zip > 0 and verify_ok else "skip",
    }


def compress_target(path: Path, out_dir: Path, level: int = 6, quarantine: bool = False, quarantine_dir: Path | None = None) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(str(path))
    out_dir.mkdir(parents=True, exist_ok=True)
    archive = out_dir / safe_archive_name(path)

    proc = run_engine(["pack", "-o", str(archive), "--level", str(level), str(path)])
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout)

    test = run_engine(["test", str(archive)])
    if test.returncode != 0:
        raise RuntimeError("Archive verification failed:\n" + (test.stderr or test.stdout))

    result = {
        "target": str(path),
        "archive": str(archive),
        "archive_bytes": archive.stat().st_size,
        "verify_ok": True,
        "original_quarantined": False,
    }

    # Safe default: never delete. Quarantine only if explicitly enabled.
    if quarantine:
        if quarantine_dir is None:
            quarantine_dir = out_dir / "quarantine"
        quarantine_dir.mkdir(parents=True, exist_ok=True)
        dest = quarantine_dir / f"{path.name}_{time.strftime('%Y%m%d_%H%M%S')}"
        shutil.move(str(path), str(dest))
        result["original_quarantined"] = True
        result["quarantine_path"] = str(dest)

    return result


def restore_archive(archive: Path, out_dir: Path) -> Dict[str, Any]:
    proc = run_engine(["unpack", str(archive), "-o", str(out_dir)])
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout)
    try:
        return json.loads(proc.stdout)
    except Exception:
        return {"restored_to": str(out_dir), "output": proc.stdout}


def load_config(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(str(path))
    cfg = DEFAULT_CONFIG.copy()
    cfg.update(json.loads(path.read_text(encoding="utf-8")))
    return cfg


def eligible_cold_targets(cfg: Dict[str, Any]) -> List[Path]:
    now = time.time()
    cold_seconds = float(cfg.get("cold_days", 30)) * 86400
    min_size = int(float(cfg.get("min_folder_size_mb", 5)) * 1024 * 1024)
    skip = cfg.get("skip_extensions", [])

    targets = []
    for folder in cfg.get("watched_folders", []):
        root = Path(folder).expanduser()
        if not root.exists():
            continue
        for child in sorted(root.iterdir()):
            try:
                if child.suffix.lower() == ".cz":
                    continue
                age = now - newest_mtime(child)
                size = folder_size(child, skip_extensions=skip)
                if age >= cold_seconds and size >= min_size:
                    targets.append(child)
            except OSError:
                continue
    return targets


def cmd_init_config(args: argparse.Namespace) -> int:
    out = Path(args.output)
    out.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")
    print(json.dumps({"created": str(out)}, indent=2))
    return 0


def cmd_scan(args: argparse.Namespace) -> int:
    result = scan_target(Path(args.target), level=args.level, skip_extensions=DEFAULT_CONFIG["skip_extensions"])
    print(json.dumps(result, indent=2))
    return 0


def cmd_compress(args: argparse.Namespace) -> int:
    result = compress_target(
        Path(args.target),
        Path(args.out),
        level=args.level,
        quarantine=args.quarantine,
        quarantine_dir=Path(args.quarantine_dir) if args.quarantine_dir else None,
    )
    print(json.dumps(result, indent=2))
    return 0


def cmd_restore(args: argparse.Namespace) -> int:
    print(json.dumps(restore_archive(Path(args.archive), Path(args.out)), indent=2))
    return 0


def cmd_watch(args: argparse.Namespace) -> int:
    cfg = load_config(Path(args.config))
    targets = eligible_cold_targets(cfg)
    report = {
        "config": str(args.config),
        "eligible_targets": [],
        "compressed": [],
        "mode": cfg.get("mode", "manual_approve"),
    }

    for target in targets:
        scan = scan_target(target, level=int(cfg.get("compression_level", 6)), skip_extensions=cfg.get("skip_extensions", []))
        report["eligible_targets"].append(scan)

        if args.apply and scan["recommendation"] == "compress":
            comp = compress_target(
                target,
                Path(cfg.get("archive_output_dir", "./CrystalZip_Archives")),
                level=int(cfg.get("compression_level", 6)),
                quarantine=bool(cfg.get("quarantine_originals", False)),
                quarantine_dir=Path(cfg.get("quarantine_dir", "./CrystalZip_Quarantine")),
            )
            report["compressed"].append(comp)

    print(json.dumps(report, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sentinel", description="CrystalZip Sentinel MVP: local storage compressor service")
    sub = p.add_subparsers(dest="cmd", required=True)

    init = sub.add_parser("init-config", help="create default config")
    init.add_argument("-o", "--output", required=True)
    init.set_defaults(func=cmd_init_config)

    scan = sub.add_parser("scan", help="estimate compression savings")
    scan.add_argument("target")
    scan.add_argument("--level", type=int, default=6)
    scan.set_defaults(func=cmd_scan)

    comp = sub.add_parser("compress", help="compress and verify a target")
    comp.add_argument("target")
    comp.add_argument("-o", "--out", required=True)
    comp.add_argument("--level", type=int, default=6)
    comp.add_argument("--quarantine", action="store_true", help="move original to quarantine after successful verification")
    comp.add_argument("--quarantine-dir")
    comp.set_defaults(func=cmd_compress)

    restore = sub.add_parser("restore", help="restore a .cz archive")
    restore.add_argument("archive")
    restore.add_argument("-o", "--out", required=True)
    restore.set_defaults(func=cmd_restore)

    watch = sub.add_parser("watch", help="scan configured watched folders")
    watch.add_argument("--config", required=True)
    watch.add_argument("--apply", action="store_true", help="actually compress recommended targets")
    watch.set_defaults(func=cmd_watch)

    return p


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

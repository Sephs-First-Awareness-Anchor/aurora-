#!/usr/bin/env python3
"""
CrystalZip Arena Compare v0.8

Changed for CrystalZip v2.1:
- Uses CrystalZip mode instead of only level
- Default CrystalZip mode is max
- Still compares against ZIP and valid 7z
- Invalid 7z is disqualified
- Termux-safe 7z mode remains default
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, Optional


def load_crystalzip_engine(script_dir: Path):
    engine = script_dir / "crystalzip.py"
    if not engine.exists():
        raise FileNotFoundError("Could not find crystalzip.py next to arena_compare.py")
    spec = importlib.util.spec_from_file_location("crystalzip_engine", engine)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load crystalzip.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def remove_if_exists(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except Exception:
        pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def folder_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    total = 0
    for root, _, files in os.walk(path):
        for name in files:
            fp = Path(root) / name
            try:
                total += fp.stat().st_size
            except OSError:
                pass
    return total


def count_files(path: Path) -> int:
    if path.is_file():
        return 1
    total = 0
    for _, _, files in os.walk(path):
        total += len(files)
    return total


def write_zip(src: Path, out: Path) -> None:
    remove_if_exists(out)
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        if src.is_file():
            zf.write(src, arcname=src.name)
            return
        root_name = src.name
        for root, _, files in os.walk(src):
            for name in sorted(files):
                fp = Path(root) / name
                arcname = str(Path(root_name) / fp.relative_to(src)).replace("\\", "/")
                zf.write(fp, arcname=arcname)


def test_zip(path: Path) -> bool:
    try:
        with zipfile.ZipFile(path) as zf:
            return zf.testzip() is None
    except Exception:
        return False


def find_7z(user_path: Optional[str] = None) -> Optional[str]:
    if user_path:
        p = Path(user_path).expanduser()
        if p.exists():
            return str(p)
        found = shutil.which(user_path)
        return found or user_path
    for name in ("7z", "7zz", "7za"):
        found = shutil.which(name)
        if found:
            return found
    return None


def run_cmd(cmd: list[str], timeout: int = 1800) -> Dict[str, Any]:
    started = time.perf_counter()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        elapsed = time.perf_counter() - started
        return {
            "cmd": cmd,
            "returncode": proc.returncode,
            "seconds": round(elapsed, 4),
            "stdout_tail": (proc.stdout or "")[-5000:],
            "stderr_tail": (proc.stderr or "")[-5000:],
            "timeout": False,
        }
    except subprocess.TimeoutExpired as exc:
        elapsed = time.perf_counter() - started
        return {
            "cmd": cmd,
            "returncode": None,
            "seconds": round(elapsed, 4),
            "stdout_tail": (exc.stdout or "")[-5000:] if isinstance(exc.stdout, str) else "",
            "stderr_tail": (exc.stderr or "")[-5000:] if isinstance(exc.stderr, str) else "",
            "timeout": True,
        }


def run_crystal(engine, src: Path, out: Path, mode: str, level: Optional[int], solid_sort: bool) -> Dict[str, Any]:
    remove_if_exists(out)
    started = time.perf_counter()
    try:
        # v2.1 signature supports mode and solid_sort.
        try:
            summary = engine.pack_archive([src], out, level=level, mode=mode, solid_sort=solid_sort)
        except TypeError:
            # fallback for old v2.0 engine
            summary = engine.pack_archive([src], out, level=level if level is not None else 9)
        seconds = round(time.perf_counter() - started, 4)
        test = engine.CrystalZipArchive(out).test()
        valid = bool(test["ok"]) and out.exists()
        return {
            "available": True,
            "valid": valid,
            "bytes": out.stat().st_size if out.exists() else None,
            "seconds": seconds,
            "verify_ok": bool(test["ok"]),
            "sha256": sha256_file(out) if out.exists() else None,
            "summary": summary,
        }
    except Exception as exc:
        return {
            "available": True,
            "valid": False,
            "bytes": out.stat().st_size if out.exists() else None,
            "seconds": round(time.perf_counter() - started, 4),
            "verify_ok": False,
            "error": str(exc),
        }


def run_zip(src: Path, out: Path) -> Dict[str, Any]:
    started = time.perf_counter()
    try:
        write_zip(src, out)
        seconds = round(time.perf_counter() - started, 4)
        ok = test_zip(out)
        return {
            "available": True,
            "valid": bool(ok) and out.exists(),
            "bytes": out.stat().st_size if out.exists() else None,
            "seconds": seconds,
            "verify_ok": bool(ok),
            "sha256": sha256_file(out) if out.exists() else None,
        }
    except Exception as exc:
        return {
            "available": True,
            "valid": False,
            "bytes": out.stat().st_size if out.exists() else None,
            "seconds": round(time.perf_counter() - started, 4),
            "verify_ok": False,
            "error": str(exc),
        }


def seven_settings(mode: str, custom_dict: Optional[str], custom_threads: Optional[str], custom_level: Optional[str]) -> list[str]:
    if mode == "max":
        level = custom_level or "9"
        dictionary = custom_dict or "256m"
        threads = custom_threads or "on"
    elif mode == "safe":
        level = custom_level or "7"
        dictionary = custom_dict or "64m"
        threads = custom_threads or "2"
    elif mode == "tiny":
        level = custom_level or "5"
        dictionary = custom_dict or "16m"
        threads = custom_threads or "1"
    else:
        raise ValueError("mode must be max, safe, or tiny")

    return ["-t7z", "-m0=lzma2", f"-mx={level}", "-ms=on", f"-md={dictionary}", f"-mmt={threads}"]


def run_7z(sevenz: Optional[str], src: Path, out: Path, mode: str, custom_dict: Optional[str], custom_threads: Optional[str], custom_level: Optional[str]) -> Dict[str, Any]:
    if not sevenz:
        return {"available": False, "valid": False, "reason": "7z was not found. In Termux run: pkg install 7zip"}

    remove_if_exists(out)
    settings = seven_settings(mode, custom_dict, custom_threads, custom_level)
    cmd = [sevenz, "a", "-y", *settings, str(out), str(src)]
    result = run_cmd(cmd, timeout=1800)

    verify_ok = False
    test_result = None
    if out.exists() and result.get("returncode") == 0:
        test_result = run_cmd([sevenz, "t", str(out)], timeout=1800)
        verify_ok = test_result.get("returncode") == 0

    valid = bool(out.exists() and result.get("returncode") == 0 and verify_ok)
    result.update({
        "available": True,
        "valid": valid,
        "mode": mode,
        "settings": settings,
        "bytes": out.stat().st_size if out.exists() else None,
        "verify_ok": verify_ok,
        "sha256": sha256_file(out) if out.exists() else None,
    })
    if test_result is not None:
        result["test_returncode"] = test_result.get("returncode")
        result["test_stdout_tail"] = test_result.get("stdout_tail")
        result["test_stderr_tail"] = test_result.get("stderr_tail")
    if not valid:
        result["disqualified"] = True
        result["disqualification_reason"] = "7z archive invalid or not verified."
    return result


def pct(delta: int, base: int) -> float:
    return round((delta / base * 100.0) if base else 0.0, 2)


def valid_bytes(result: Dict[str, Any]):
    if result.get("available") and result.get("valid") and isinstance(result.get("bytes"), int):
        return int(result["bytes"])
    return None


def compare_sizes(crystal: Dict[str, Any], zipr: Dict[str, Any], seven: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    cb, zb, sb = valid_bytes(crystal), valid_bytes(zipr), valid_bytes(seven)
    if cb is not None and zb is not None:
        delta = zb - cb
        out["crystal_vs_zip"] = {"delta_bytes": delta, "pct_smaller": pct(delta, zb), "winner": "CrystalZip" if delta > 0 else ("ZIP" if delta < 0 else "tie")}
    else:
        out["crystal_vs_zip"] = "comparison unavailable"
    if cb is not None and sb is not None:
        delta = sb - cb
        out["crystal_vs_7z"] = {"delta_bytes": delta, "pct_smaller": pct(delta, sb), "winner": "CrystalZip" if delta > 0 else ("7z" if delta < 0 else "tie")}
    else:
        out["crystal_vs_7z"] = "comparison unavailable because 7z was skipped, missing, or invalid"
    if zb is not None and sb is not None:
        delta = sb - zb
        out["zip_vs_7z"] = {"delta_bytes": delta, "pct_smaller": pct(delta, sb), "winner": "ZIP" if delta > 0 else ("7z" if delta < 0 else "tie")}
    else:
        out["zip_vs_7z"] = "comparison unavailable because 7z was skipped, missing, or invalid"
    return out


def make_text_report(report: Dict[str, Any]) -> str:
    lines = []
    lines.append("CrystalZip Arena Compare v0.8")
    lines.append("=" * 32)
    lines.append("")
    lines.append(f"Target: {report['target']}")
    lines.append(f"Original bytes: {report['original_bytes']}")
    lines.append(f"File count: {report['file_count']}")
    lines.append(f"CrystalZip mode: {report.get('crystalzip_mode')}")
    lines.append(f"7z command: {report.get('seven_zip_command') or 'not found/skipped'}")
    lines.append(f"7z mode: {report.get('seven_zip_mode')}")
    lines.append("")

    for name, key in (("CrystalZip", "crystalzip"), ("ZIP Deflate", "zip_deflate"), ("7z LZMA2", "seven_zip_lzma2")):
        r = report["results"][key]
        lines.append(name)
        lines.append("-" * len(name))
        if not r.get("available", True):
            lines.append(f"Not available: {r.get('reason', 'unknown')}")
        else:
            lines.append(f"Valid: {r.get('valid')}")
            lines.append(f"Size: {r.get('bytes')} bytes")
            lines.append(f"Time: {r.get('seconds')} sec")
            lines.append(f"Verify: {r.get('verify_ok')}")
            if r.get("settings"):
                lines.append(f"Settings: {' '.join(r.get('settings', []))}")
            if r.get("summary"):
                s = r["summary"]
                lines.append(f"Summary: mode={s.get('mode')} level={s.get('level')} solid_sort={s.get('solid_sort')}")
            if r.get("disqualified"):
                lines.append(f"DISQUALIFIED: {r.get('disqualification_reason')}")
            if r.get("error"):
                lines.append(f"Error: {r.get('error')}")
        lines.append("")

    lines.append("Comparisons")
    lines.append("-" * 11)
    for key, value in report["comparisons"].items():
        lines.append(f"{key}: {value}")
    lines.append("")

    c7 = report["comparisons"].get("crystal_vs_7z")
    if isinstance(c7, dict):
        if c7["winner"] == "CrystalZip":
            lines.append(f"Result: CrystalZip beat valid 7z by {c7['delta_bytes']} bytes ({c7['pct_smaller']}%).")
        elif c7["winner"] == "7z":
            lines.append(f"Result: valid 7z beat CrystalZip by {-c7['delta_bytes']} bytes.")
        else:
            lines.append("Result: CrystalZip and valid 7z tied.")
    else:
        lines.append("Result: no valid 7z comparison was produced.")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare CrystalZip vs ZIP vs valid 7z.")
    parser.add_argument("target")
    parser.add_argument("-o", "--out", default="arena_compare_out")
    parser.add_argument("--cz-mode", choices=["fast", "balanced", "max", "ultra"], default="max")
    parser.add_argument("--cz-level", type=int, default=None)
    parser.add_argument("--no-solid-sort", action="store_true")
    parser.add_argument("--sevenz")
    parser.add_argument("--seven-mode", choices=["max", "safe", "tiny"], default="safe")
    parser.add_argument("--seven-dict")
    parser.add_argument("--seven-threads")
    parser.add_argument("--seven-level")
    parser.add_argument("--skip-7z", action="store_true")
    args = parser.parse_args()

    target = Path(args.target).expanduser().resolve()
    if not target.exists():
        raise FileNotFoundError(str(target))
    out_dir = Path(args.out).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    script_dir = Path(__file__).resolve().parent
    engine = load_crystalzip_engine(script_dir)
    sevenz = None if args.skip_7z else find_7z(args.sevenz)

    safe_name = target.name.replace(" ", "_") or "target"
    crystal_archive = out_dir / f"{safe_name}.cz"
    zip_archive = out_dir / f"{safe_name}.zip"
    seven_archive = out_dir / f"{safe_name}.7z"

    print("Running CrystalZip...")
    crystal = run_crystal(engine, target, crystal_archive, mode=args.cz_mode, level=args.cz_level, solid_sort=not args.no_solid_sort)

    print("Running ZIP Deflate...")
    zip_result = run_zip(target, zip_archive)

    if args.skip_7z:
        print("Skipping 7z.")
        seven_result = {"available": False, "valid": False, "reason": "Skipped by --skip-7z"}
    else:
        print(f"Running 7z LZMA2 ({args.seven_mode} mode)..." if sevenz else "7z not found; skipping 7z.")
        seven_result = run_7z(sevenz, target, seven_archive, args.seven_mode, args.seven_dict, args.seven_threads, args.seven_level)

    comparisons = compare_sizes(crystal, zip_result, seven_result)

    report = {
        "created_at": time.time(),
        "arena_compare_version": "0.8",
        "target": str(target),
        "original_bytes": folder_size(target),
        "file_count": count_files(target),
        "output_dir": str(out_dir),
        "crystalzip_mode": args.cz_mode,
        "crystalzip_level": args.cz_level,
        "solid_sort": not args.no_solid_sort,
        "seven_zip_command": sevenz,
        "seven_zip_mode": args.seven_mode if not args.skip_7z else "skipped",
        "results": {"crystalzip": crystal, "zip_deflate": zip_result, "seven_zip_lzma2": seven_result},
        "comparisons": comparisons,
    }

    json_path = out_dir / "arena_report.json"
    txt_path = out_dir / "arena_report.txt"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    txt_path.write_text(make_text_report(report), encoding="utf-8")

    print("")
    print(txt_path.read_text(encoding="utf-8"))
    print(f"JSON report: {json_path}")
    print(f"Text report: {txt_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

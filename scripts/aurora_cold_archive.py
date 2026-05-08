# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
One-shot archiver for AuroraO directories that are NOT part of the live stack.

Run once to pack cold data. Resulting .cz files sit next to their source dirs.
Unpack a specific archive with:  python3 aurora_cold_archive.py unpack <name>

Usage:
  aurora_cold_archive.py pack              — pack all cold targets listed below
  aurora_cold_archive.py pack <name>       — pack one named target
  aurora_cold_archive.py unpack <name>     — unpack one named target
  aurora_cold_archive.py status            — show what's packed vs unpacked
"""
import sys
import shutil
from pathlib import Path

AURORA_ROOT = Path(__file__).resolve().parent.parent.parent  # AuroraO/

# Targets: (relative path from AURORA_ROOT, archive name)
# These directories have NO active runtime dependency — safe to compress.
COLD_TARGETS = [
    ("aurora_strata/merge_artifacts",  "merge_artifacts"),
    ("aurora_strata/runs",             "runs"),
    ("aurora_strata/aurora_runtime_output", "aurora_runtime_output"),
    ("aurora_geneology",               "aurora_geneology"),
    ("aurora_genealogy",               "aurora_genealogy"),
]

# Large single files at AuroraO root — training data, never touched at runtime.
COLD_FILES = [
    "train.json",
    "train (1).json",
    "train_wer_0.1_seed_1.json",
    "train_wer_0.15_seed_1.json",
    "train_wer_0.2_seed_1.json",
    "train_wer_0.3_seed_1.json",
    "valid_freq.json",
    "valid_rare.json",
]


def _cz():
    strata = AURORA_ROOT / "aurora_strata"
    sys.path.insert(0, str(strata))
    import crystalzip
    return crystalzip


def _mb(path: Path) -> float:
    if path.is_file():
        return path.stat().st_size / 1024 / 1024
    if path.is_dir():
        return sum(f.stat().st_size for f in path.rglob("*") if f.is_file()) / 1024 / 1024
    return 0.0


def pack_target(rel_path: str, archive_name: str) -> None:
    cz = _cz()
    src = AURORA_ROOT / rel_path
    archive = src.parent / f"{archive_name}.cz"

    if not src.exists():
        print(f"[cold-archive] skip {archive_name} — source not found")
        return
    if archive.exists():
        print(f"[cold-archive] skip {archive_name} — {archive.name} already exists")
        return

    src_mb = _mb(src)
    print(f"[cold-archive] packing {rel_path} ({src_mb:.0f} MB) → {archive.name} ...")
    try:
        cz.pack_archive([src], archive, mode="fast")
        shutil.rmtree(src) if src.is_dir() else src.unlink()
        cz_mb = _mb(archive)
        ratio = (1 - cz_mb / src_mb) * 100 if src_mb > 0 else 0
        print(f"[cold-archive] {archive.name} = {cz_mb:.1f} MB  ({ratio:.0f}% saved)")
    except Exception as exc:
        print(f"[cold-archive] ERROR: {exc}")
        if archive.exists() and not src.exists():
            try:
                cz.CrystalZipArchive(archive).unpack(src.parent)
                archive.unlink()
                print(f"[cold-archive] rolled back {archive.name}")
            except Exception:
                pass


def pack_file(filename: str) -> None:
    cz = _cz()
    src = AURORA_ROOT / filename
    if not src.exists():
        return
    archive = src.with_suffix(".cz")
    if archive.exists():
        print(f"[cold-archive] skip {filename} — .cz already exists")
        return
    src_mb = _mb(src)
    print(f"[cold-archive] packing file {filename} ({src_mb:.0f} MB) ...")
    try:
        cz.pack_archive([src], archive, mode="fast")
        src.unlink()
        cz_mb = _mb(archive)
        ratio = (1 - cz_mb / src_mb) * 100 if src_mb > 0 else 0
        print(f"[cold-archive] {archive.name} = {cz_mb:.1f} MB  ({ratio:.0f}% saved)")
    except Exception as exc:
        print(f"[cold-archive] ERROR {filename}: {exc}")


def unpack_target(archive_name: str) -> None:
    cz = _cz()
    # Search for the archive in expected parent dirs
    candidates = []
    for rel_path, name in COLD_TARGETS:
        if name == archive_name:
            parent = (AURORA_ROOT / rel_path).parent
            candidates.append(parent / f"{name}.cz")
    if not candidates:
        # Try at AURORA_ROOT level
        candidates = [AURORA_ROOT / f"{archive_name}.cz"]

    archive = next((c for c in candidates if c.exists()), None)
    if archive is None:
        print(f"[cold-archive] archive not found: {archive_name}.cz")
        return

    print(f"[cold-archive] unpacking {archive.name} → {archive.parent / archive_name} ...")
    try:
        result = cz.CrystalZipArchive(archive).unpack(archive.parent)
        archive.unlink()
        print(f"[cold-archive] restored {result.get('files', '?')} files")
    except Exception as exc:
        print(f"[cold-archive] ERROR: {exc}")


def show_status() -> None:
    print("[cold-archive] status:")
    for rel_path, name in COLD_TARGETS:
        src = AURORA_ROOT / rel_path
        archive = src.parent / f"{name}.cz"
        if archive.exists():
            print(f"  PACKED   {name}.cz  ({_mb(archive):.1f} MB)")
        elif src.exists():
            print(f"  unpacked {rel_path}  ({_mb(src):.0f} MB)")
        else:
            print(f"  absent   {rel_path}")
    for filename in COLD_FILES:
        src = AURORA_ROOT / filename
        archive = src.with_suffix(".cz")
        if archive.exists():
            print(f"  PACKED   {archive.name}  ({_mb(archive):.1f} MB)")
        elif src.exists():
            print(f"  unpacked {filename}  ({_mb(src):.0f} MB)")


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)

    cmd = args[0]
    if cmd == "pack":
        target = args[1] if len(args) > 1 else None
        targets = [(r, n) for r, n in COLD_TARGETS if target is None or n == target]
        for rel_path, name in targets:
            pack_target(rel_path, name)
        if target is None:
            for filename in COLD_FILES:
                pack_file(filename)
    elif cmd == "unpack":
        if len(args) < 2:
            print("Usage: aurora_cold_archive.py unpack <name>")
            sys.exit(1)
        unpack_target(args[1])
    elif cmd == "status":
        show_status()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()

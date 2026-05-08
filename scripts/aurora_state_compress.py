# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Aurora state compression manager — pack-at-stop / unpack-at-start.

Usage:
  aurora_state_compress.py pack    — rotate logs, then pack cold dirs to .cz
  aurora_state_compress.py unpack  — restore .cz archives back to directories
  aurora_state_compress.py rotate  — log rotation only (no pack/unpack)
"""
import os
import sys
import shutil
from pathlib import Path

STRATA_ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = STRATA_ROOT / "aurora_state"

# Directories cold-packed when Aurora stops; unpacked before she starts.
# These are NOT read at runtime — they're archived data Aurora writes during
# operation but only needs on cold-start or manual inspection.
COLD_DIRS = [
    "dream_episodes",
    "quasiarch_observer",
    "genealogy",
]

# Large live JSON/JSONL sub-directories that accumulate fast — pack these too.
COLD_SUBDIRS: list[tuple[str, str]] = [
    # (parent_dir, sub_dir) — packs state_dir/parent_dir/sub_dir → parent_dir__sub_dir.cz
]

# .jsonl log files are capped at this many lines (keep the newest entries).
LOG_MAX_LINES = 2000


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _crystalzip():
    sys.path.insert(0, str(STRATA_ROOT))
    import crystalzip
    return crystalzip


def rotate_logs(state_dir: Path, max_lines: int = LOG_MAX_LINES) -> None:
    for jsonl in sorted(state_dir.glob("*.jsonl")):
        try:
            text = jsonl.read_text(encoding="utf-8", errors="replace")
            lines = text.splitlines()
            if len(lines) > max_lines:
                kept = lines[-max_lines:]
                jsonl.write_text("\n".join(kept) + "\n", encoding="utf-8")
                saved = len(lines) - len(kept)
                print(f"[compress] rotated {jsonl.name}: -{saved} lines "
                      f"({len(lines)} → {len(kept)})")
        except Exception as exc:
            print(f"[compress] skip {jsonl.name}: {exc}")

    # Also rotate .jsonl files one level deep in subdirs
    for sub in state_dir.iterdir():
        if sub.is_dir():
            for jsonl in sorted(sub.glob("*.jsonl")):
                try:
                    lines = jsonl.read_text(encoding="utf-8", errors="replace").splitlines()
                    if len(lines) > max_lines:
                        kept = lines[-max_lines:]
                        jsonl.write_text("\n".join(kept) + "\n", encoding="utf-8")
                        print(f"[compress] rotated {sub.name}/{jsonl.name}: "
                              f"{len(lines)} → {len(kept)} lines")
                except Exception as exc:
                    print(f"[compress] skip {sub.name}/{jsonl.name}: {exc}")


def pack_cold_data(state_dir: Path) -> None:
    cz = _crystalzip()

    for dirname in COLD_DIRS:
        src = state_dir / dirname
        if not src.exists():
            continue
        archive = state_dir / f"{dirname}.cz"
        if archive.exists():
            archive.unlink()
        src_mb = sum(f.stat().st_size for f in src.rglob("*") if f.is_file()) / 1024 / 1024
        print(f"[compress] packing {dirname}/ ({src_mb:.0f} MB) → {dirname}.cz ...")
        try:
            cz.pack_archive([src], archive, mode="fast")
            shutil.rmtree(src)
            cz_mb = archive.stat().st_size / 1024 / 1024
            ratio = (1 - cz_mb / src_mb) * 100 if src_mb > 0 else 0
            print(f"[compress] {dirname}.cz = {cz_mb:.1f} MB  ({ratio:.0f}% saved)")
        except Exception as exc:
            print(f"[compress] ERROR packing {dirname}: {exc}")
            if archive.exists() and not src.exists():
                # unpack so we don't lose data
                try:
                    src.mkdir(parents=True, exist_ok=True)
                    cz.CrystalZipArchive(archive).unpack(state_dir)
                    archive.unlink()
                except Exception:
                    pass


def unpack_cold_data(state_dir: Path) -> None:
    cz = _crystalzip()

    for dirname in COLD_DIRS:
        archive = state_dir / f"{dirname}.cz"
        if not archive.exists():
            continue
        dest = state_dir / dirname
        if dest.exists():
            print(f"[compress] {dirname}/ already present — skipping unpack")
            continue
        print(f"[compress] unpacking {dirname}.cz → {dirname}/ ...")
        try:
            dest.mkdir(parents=True, exist_ok=True)
            result = cz.CrystalZipArchive(archive).unpack(state_dir)
            archive.unlink()
            print(f"[compress] restored {result.get('files', '?')} files to {dirname}/")
        except Exception as exc:
            print(f"[compress] ERROR unpacking {dirname}.cz: {exc}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in ("pack", "unpack", "rotate"):
        print("Usage: aurora_state_compress.py {pack|unpack|rotate}")
        sys.exit(1)

    cmd = sys.argv[1]
    state_dir = STATE_DIR

    if not state_dir.is_dir():
        print(f"[compress] state dir not found: {state_dir}")
        sys.exit(1)

    if cmd == "rotate":
        rotate_logs(state_dir)
    elif cmd == "pack":
        rotate_logs(state_dir)
        pack_cold_data(state_dir)
    elif cmd == "unpack":
        unpack_cold_data(state_dir)


if __name__ == "__main__":
    main()

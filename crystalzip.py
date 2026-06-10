#!/usr/bin/env python3
"""
CrystalZip v2.5
===============

Drop-in replacement for crystalzip.py.

Upgrade from v2.4:
    - Returns to v2.1's winning single solid payload stream
    - Locks extension_first as the default max sorter based on Aurora v2.4 tournament
    - Adds ultra mode for full adaptive sorter tournament
    - max mode now avoids repeated tournament cost
    - Exact dedupe retained
    - Exact restore retained
    - Reads v2.0, v2.1, v2.2, and v2.3 archives

Why:
    v2.1 beat valid 7z max 128m.
    v2.2 and v2.3 showed that manually "smarter" ordering can hurt.
    v2.5 uses the v2.4 winning sorter directly for max mode, while ultra keeps the tournament.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import argparse
import hashlib
import json
import lzma
import math
import os
import re
import shutil
import struct
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


MAGIC = b"CRYSTALZIP25\0"
LEGACY_MAGIC_24 = b"CRYSTALZIP24\0"
LEGACY_MAGIC_23 = b"CRYSTALZIP23\0"
LEGACY_MAGIC_22 = b"CRYSTALZIP22\0"
LEGACY_MAGIC_21 = b"CRYSTALZIP21\0"
LEGACY_MAGIC_20 = b"CRYSTALZIP20\0"
VERSION = 25

MODE_LEVELS = {
    "fast": 3,
    "balanced": 6,
    "max": 9,
    "ultra": 9,
}

TEXT_EXTS = {
    "txt", "md", "rst", "log", "csv", "tsv", "json", "xml", "yaml", "yml",
    "ini", "cfg", "conf", "toml", "html", "htm", "css", "svg", "srt",
}
CODE_EXTS = {
    "py", "js", "ts", "jsx", "tsx", "java", "kt", "go", "rs", "c", "h", "cpp",
    "hpp", "cs", "php", "rb", "swift", "sh", "bash", "zsh", "ps1", "sql",
    "lua", "dart", "scala", "pl", "r", "m", "mm", "gradle", "dockerfile",
}
DATA_EXTS = {
    "db", "sqlite", "sqlite3", "bin", "dat", "data", "pkl", "pickle", "npy",
    "npz", "parquet", "arrow", "orc",
}
MEDIA_EXTS = {
    "jpg", "jpeg", "png", "webp", "gif", "mp3", "mp4", "m4a", "mov", "avi",
    "mkv", "wav", "flac", "ogg", "pdf",
}
ARCHIVE_EXTS = {
    "zip", "7z", "rar", "gz", "xz", "bz2", "zst", "tar", "cz",
}

STEM_NUM_RE = re.compile(r"\d+")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_rel(path: str) -> str:
    path = path.replace("\\", "/")
    return "/".join(p for p in path.split("/") if p and p not in {"", ".", ".."})


def file_ext(path: str) -> str:
    name = path.rsplit("/", 1)[-1].lower()
    if "." in name:
        return name.rsplit(".", 1)[-1]
    return ""


def file_stem_norm(path: str) -> str:
    name = path.rsplit("/", 1)[-1].lower()
    if "." in name:
        name = name.rsplit(".", 1)[0]
    return STEM_NUM_RE.sub("#", name)


def path_family(path: str) -> str:
    parts = path.lower().split("/")
    if len(parts) <= 2:
        return ""
    return "/".join(parts[-4:-1])


def entropy_bits_per_byte(data: bytes) -> float:
    if not data:
        return 0.0
    counts = [0] * 256
    for b in data:
        counts[b] += 1
    n = len(data)
    ent = 0.0
    for c in counts:
        if c:
            p = c / n
            ent -= p * math.log2(p)
    return ent


def looks_text(data: bytes, sample_size: int = 4096) -> bool:
    if not data:
        return False
    sample = data[:sample_size]
    if b"\x00" in sample:
        return False
    printable = 0
    for b in sample:
        if b in (9, 10, 13) or 32 <= b <= 126 or b >= 128:
            printable += 1
    return printable / len(sample) >= 0.92


def category_for(path: str, data: bytes) -> str:
    ext = file_ext(path)
    size = len(data)
    if size == 0:
        return "00_empty"
    if size < 256:
        return "01_tiny"
    if ext in CODE_EXTS:
        return "02_code"
    if ext in TEXT_EXTS:
        return "03_text"
    if ext in DATA_EXTS:
        if looks_text(data):
            return "03_text"
        return "04_data"
    if looks_text(data):
        return "03_text"
    if ext in ARCHIVE_EXTS:
        return "07_archive"
    if ext in MEDIA_EXTS:
        return "08_media"
    ent = entropy_bits_per_byte(data[: min(len(data), 65536)])
    if ent >= 7.65:
        return "08_media"
    return "05_binary"


def lzma_compress(data: bytes, level: int = 9) -> bytes:
    return lzma.compress(data, preset=max(0, min(9, int(level))))


def lzma_decompress(data: bytes) -> bytes:
    return lzma.decompress(data)


def collect_files(inputs: List[Path]) -> List[Tuple[str, bytes]]:
    files: List[Tuple[str, bytes]] = []
    for inp in inputs:
        p = inp.expanduser().resolve()
        if not p.exists():
            raise FileNotFoundError(str(inp))
        if p.is_file():
            files.append((safe_rel(p.name), p.read_bytes()))
        elif p.is_dir():
            root_name = safe_rel(p.name)
            for root, _, names in os.walk(p):
                for name in sorted(names):
                    fp = Path(root) / name
                    rel = safe_rel(str(Path(root_name) / fp.relative_to(p)))
                    files.append((rel, fp.read_bytes()))
        else:
            raise ValueError(f"unsupported input: {inp}")
    return files


def size_bucket(size: int) -> int:
    if size == 0:
        return 0
    if size < 1024:
        return 1
    if size < 4 * 1024:
        return 2
    if size < 16 * 1024:
        return 3
    if size < 64 * 1024:
        return 4
    if size < 256 * 1024:
        return 5
    if size < 1024 * 1024:
        return 6
    if size < 4 * 1024 * 1024:
        return 7
    return 8


def prefix_fingerprint(data: bytes) -> str:
    if not data:
        return "0"
    if len(data) > 8192:
        sample = data[:4096] + data[len(data)//2:len(data)//2 + 2048]
    else:
        sample = data[:4096]
    return hashlib.sha1(sample).hexdigest()[:10]


def v21_key(item: Dict[str, Any]) -> Tuple[str, int, int, str]:
    path, data = item["path"], item["data"]
    ext = file_ext(path)
    size = len(data)
    if size == 0:
        bucket = 0
    elif size < 1024:
        bucket = 1
    elif size < 16 * 1024:
        bucket = 2
    elif size < 256 * 1024:
        bucket = 3
    elif size < 4 * 1024 * 1024:
        bucket = 4
    else:
        bucket = 5
    prefix_hash = hashlib.sha1(data[:4096]).hexdigest()[:8] if data else "0"
    return (ext, bucket, size // 4096, prefix_hash)


def v23_key(item: Dict[str, Any]) -> Tuple[str, str, str, str, int, int, str, int]:
    path, data = item["path"], item["data"]
    size = len(data)
    return (
        category_for(path, data),
        path_family(path),
        file_ext(path),
        file_stem_norm(path),
        size_bucket(size),
        size // 8192,
        prefix_fingerprint(data),
        size,
    )


def ext_first_key(item: Dict[str, Any]) -> Tuple[str, str, int, str]:
    path, data = item["path"], item["data"]
    return (file_ext(path), file_stem_norm(path), len(data) // 4096, prefix_fingerprint(data))


def size_first_key(item: Dict[str, Any]) -> Tuple[int, str, str, str]:
    path, data = item["path"], item["data"]
    return (size_bucket(len(data)), file_ext(path), path_family(path), prefix_fingerprint(data))


def path_family_key(item: Dict[str, Any]) -> Tuple[str, str, str, int]:
    path, data = item["path"], item["data"]
    return (path_family(path), file_ext(path), file_stem_norm(path), len(data) // 4096)


def prefix_key(item: Dict[str, Any]) -> Tuple[str, str, int]:
    path, data = item["path"], item["data"]
    return (prefix_fingerprint(data), file_ext(path), len(data) // 4096)


SORTERS = {
    "original": None,
    "v21_simple": v21_key,
    "extension_first": ext_first_key,
    "size_first": size_first_key,
    "path_family": path_family_key,
    "prefix_fingerprint": prefix_key,
    "v23_structured": v23_key,
}


def prepare_unique(files: List[Tuple[str, bytes]]) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]:
    manifest_base: Dict[str, Any] = {
        "format": "CrystalZip",
        "version": VERSION,
        "created_at": time.time(),
        "files": [],
        "stats": {
            "file_count": len(files),
            "input_bytes": 0,
            "unique_payload_bytes": 0,
            "duplicate_files": 0,
            "category_counts": {},
        },
    }

    unique: Dict[str, Dict[str, Any]] = {}
    file_entries: List[Dict[str, Any]] = []
    order = 0

    for path, data in files:
        h = sha256_bytes(data)
        cat = category_for(path, data)
        manifest_base["stats"]["input_bytes"] += len(data)
        manifest_base["stats"]["category_counts"][cat] = manifest_base["stats"]["category_counts"].get(cat, 0) + 1

        if h in unique:
            manifest_base["stats"]["duplicate_files"] += 1
        else:
            unique[h] = {
                "hash": h,
                "path": path,
                "size": len(data),
                "data": data,
                "category": cat,
                "original_order": order,
            }
            order += 1

        file_entries.append({
            "path": path,
            "blob": h,
            "size": len(data),
            "sha256": h,
            "category": cat,
        })

    unique_items = list(unique.values())
    return manifest_base, unique_items, file_entries


def build_payload_for_order(unique_items: List[Dict[str, Any]], file_entries: List[Dict[str, Any]], sorter_name: str) -> Tuple[List[Dict[str, Any]], bytes, Dict[str, Tuple[int, int]]]:
    items = list(unique_items)
    sorter = SORTERS[sorter_name]
    if sorter is None:
        items.sort(key=lambda x: x["original_order"])
    else:
        items.sort(key=sorter)

    payload_parts: List[bytes] = []
    blob_location: Dict[str, Tuple[int, int]] = {}
    offset = 0

    for item in items:
        data = item["data"]
        h = item["hash"]
        blob_location[h] = (offset, len(data))
        payload_parts.append(data)
        offset += len(data)

    return items, b"".join(payload_parts), blob_location


def materialize_manifest(manifest_base: Dict[str, Any], file_entries: List[Dict[str, Any]], blob_location: Dict[str, Tuple[int, int]], sorter_name: str, level: int, mode: str, solid_sort: bool, tournament: List[Dict[str, Any]]) -> Dict[str, Any]:
    manifest = json.loads(json.dumps(manifest_base))
    manifest["solid_sort"] = bool(solid_sort)
    manifest["sorter"] = sorter_name
    manifest["sorter_tournament"] = tournament
    manifest["compression"] = {
        "mode": mode,
        "level": level,
        "payload_solid_sort": bool(solid_sort),
        "grouped_streams": False,
        "stream_count": 1,
        "adaptive_sort": len(tournament) > 1,
        "winning_sorter": sorter_name,
    }

    manifest["stats"]["unique_payload_bytes"] = sum(ln for _, ln in blob_location.values())

    for entry in file_entries:
        off, ln = blob_location[entry["blob"]]
        manifest["files"].append({
            "path": entry["path"],
            "offset": off,
            "length": ln,
            "size": entry["size"],
            "sha256": entry["sha256"],
            "category": entry["category"],
        })

    return manifest


def resolve_level(mode: str = "max", level: Optional[int] = None) -> int:
    if level is not None:
        return max(0, min(9, int(level)))
    return MODE_LEVELS.get(mode, 9)


def pack_archive(
    inputs: List[Path],
    output: Path,
    level: Optional[int] = None,
    mode: str = "max",
    solid_sort: bool = True,
    grouped_streams: bool = False,  # accepted for compatibility; ignored
    adaptive_sort: bool = False,
) -> Dict[str, Any]:
    files = collect_files(inputs)
    actual_level = resolve_level(mode, level)

    manifest_base, unique_items, file_entries = prepare_unique(files)

    # v2.5 policy:
    # fast      -> original
    # balanced  -> v21_simple
    # max       -> extension_first, the Aurora v2.4 tournament winner
    # ultra     -> full adaptive tournament
    if not solid_sort:
        sorter_names = ["original"]
    elif mode == "ultra" or adaptive_sort:
        sorter_names = list(SORTERS.keys())
    elif mode == "fast":
        sorter_names = ["original"]
    elif mode == "balanced":
        sorter_names = ["v21_simple"]
    else:
        sorter_names = ["extension_first"]

    tournament: List[Dict[str, Any]] = []
    best = None

    for sorter_name in sorter_names:
        _, payload, blob_location = build_payload_for_order(unique_items, file_entries, sorter_name)
        comp = lzma_compress(payload, actual_level)
        if len(comp) < len(payload):
            payload_mode = 2
            payload_blob = comp
        else:
            payload_mode = 0
            payload_blob = payload

        result = {
            "sorter": sorter_name,
            "payload_mode": "lzma" if payload_mode == 2 else "stored",
            "raw_payload_bytes": len(payload),
            "stored_payload_bytes": len(payload_blob),
        }
        tournament.append(result)

        score = len(payload_blob)
        if best is None or score < best["score"]:
            best = {
                "score": score,
                "sorter_name": sorter_name,
                "payload": payload,
                "payload_blob": payload_blob,
                "payload_mode": payload_mode,
                "blob_location": blob_location,
            }

    assert best is not None

    # Build final manifest only for the winner. Then compress manifest.
    manifest = materialize_manifest(
        manifest_base,
        file_entries,
        best["blob_location"],
        best["sorter_name"],
        actual_level,
        mode,
        solid_sort,
        tournament,
    )

    manifest_raw = json.dumps(manifest, separators=(",", ":"), sort_keys=True).encode()
    manifest_c = lzma_compress(manifest_raw, actual_level)

    header = MAGIC + struct.pack(
        ">IBQQ",
        VERSION,
        best["payload_mode"],
        len(manifest_c),
        len(best["payload_blob"]),
    )

    output = output.expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(header + manifest_c + best["payload_blob"])

    out_size = output.stat().st_size
    input_bytes = manifest["stats"]["input_bytes"]

    return {
        "archive": str(output),
        "archive_size_bytes": out_size,
        "input_files": len(files),
        "input_bytes": input_bytes,
        "unique_payload_bytes": manifest["stats"]["unique_payload_bytes"],
        "duplicate_files": manifest["stats"]["duplicate_files"],
        "mode": mode,
        "level": actual_level,
        "solid_sort": bool(solid_sort),
        "grouped_streams": False,
        "adaptive_sort": bool(len(tournament) > 1),
        "winning_sorter": best["sorter_name"],
        "stream_count": 1,
        "category_counts": manifest["stats"]["category_counts"],
        "sorter_tournament": tournament,
        "savings_vs_input_bytes": input_bytes - out_size,
        "savings_vs_input_pct": round(((input_bytes - out_size) / input_bytes * 100.0) if input_bytes else 0.0, 2),
    }


class CrystalZipArchive:
    def __init__(self, archive: Path) -> None:
        self.archive = archive.expanduser()
        raw = self.archive.read_bytes()

        if raw.startswith(MAGIC):
            magic_len = len(MAGIC)
            version_allowed = (VERSION,)
        elif raw.startswith(LEGACY_MAGIC_24):
            magic_len = len(LEGACY_MAGIC_24)
            version_allowed = (24,)
        elif raw.startswith(LEGACY_MAGIC_23):
            magic_len = len(LEGACY_MAGIC_23)
            version_allowed = (23,)
        elif raw.startswith(LEGACY_MAGIC_21):
            magic_len = len(LEGACY_MAGIC_21)
            version_allowed = (21,)
        elif raw.startswith(LEGACY_MAGIC_20):
            magic_len = len(LEGACY_MAGIC_20)
            version_allowed = (20,)
        elif raw.startswith(LEGACY_MAGIC_22):
            self._read_v22(raw)
            return
        else:
            raise ValueError("not a supported CrystalZip archive")

        p = magic_len
        version, payload_mode, manifest_len, payload_len = struct.unpack(">IBQQ", raw[p:p+21])
        if version not in version_allowed:
            raise ValueError(f"unsupported version: {version}")
        p += 21
        manifest_c = raw[p:p+manifest_len]
        p += manifest_len
        payload_blob = raw[p:p+payload_len]

        self.manifest = json.loads(lzma_decompress(manifest_c).decode())
        payload = lzma_decompress(payload_blob) if payload_mode == 2 else payload_blob
        self.streams = [payload]
        self.payload = payload
        self.payload_mode = payload_mode
        self.version = version

    def _read_v22(self, raw: bytes) -> None:
        p = len(LEGACY_MAGIC_22)
        version = struct.unpack(">I", raw[p:p+4])[0]
        p += 4
        if version != 22:
            raise ValueError(f"unsupported v2.2 version: {version}")
        manifest_len = struct.unpack(">Q", raw[p:p+8])[0]
        p += 8
        stream_count = struct.unpack(">I", raw[p:p+4])[0]
        p += 4
        descriptors = []
        for _ in range(stream_count):
            mode_id, ln = struct.unpack(">BQ", raw[p:p+9])
            p += 9
            descriptors.append((mode_id, ln))
        manifest_c = raw[p:p+manifest_len]
        p += manifest_len
        self.manifest = json.loads(lzma_decompress(manifest_c).decode())
        self.streams = []
        for mode_id, ln in descriptors:
            blob = raw[p:p+ln]
            p += ln
            self.streams.append(lzma_decompress(blob) if mode_id == 2 else blob)
        self.payload = None
        self.payload_mode = None
        self.version = 22

    def list(self) -> Dict[str, Any]:
        return {
            "archive": str(self.archive),
            "archive_size_bytes": self.archive.stat().st_size,
            "version": self.version,
            "compression": self.manifest.get("compression", {}),
            "stats": self.manifest.get("stats", {}),
            "files": [
                {"path": f["path"], "size": f["size"], "sha256": f["sha256"], "category": f.get("category") or f.get("group")}
                for f in self.manifest.get("files", [])
            ],
        }

    def file_data(self, entry: Dict[str, Any]) -> bytes:
        stream_index = int(entry.get("stream", 0))
        off = int(entry["offset"])
        ln = int(entry["length"])
        data = self.streams[stream_index][off:off+ln]
        if sha256_bytes(data) != entry["sha256"]:
            raise ValueError(f"hash mismatch for {entry['path']}")
        return data

    def unpack(self, out_dir: Path) -> Dict[str, Any]:
        out_dir = out_dir.expanduser()
        out_dir.mkdir(parents=True, exist_ok=True)
        restored = 0
        for f in self.manifest.get("files", []):
            target = out_dir / safe_rel(f["path"])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(self.file_data(f))
            restored += 1
        return {"restored_to": str(out_dir), "files": restored}

    def test(self) -> Dict[str, Any]:
        failures = []
        checked = 0
        for f in self.manifest.get("files", []):
            try:
                self.file_data(f)
                checked += 1
            except Exception as exc:
                failures.append({"path": f.get("path"), "error": str(exc)})
        return {"ok": not failures, "files_checked": checked, "failures": failures}


def cmd_pack(args: argparse.Namespace) -> int:
    print(json.dumps(
        pack_archive(
            [Path(x) for x in args.inputs],
            Path(args.output),
            level=args.level,
            mode=args.mode,
            solid_sort=not args.no_solid_sort,
            adaptive_sort=not args.no_adaptive_sort,
        ),
        indent=2
    ))
    return 0


def cmd_unpack(args: argparse.Namespace) -> int:
    print(json.dumps(CrystalZipArchive(Path(args.archive)).unpack(Path(args.out)), indent=2))
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    info = CrystalZipArchive(Path(args.archive)).list()
    if args.json:
        print(json.dumps(info, indent=2))
    else:
        print(f"Archive: {info['archive']}")
        print(f"Size: {info['archive_size_bytes']} bytes")
        print(f"Version: {info['version']}")
        comp = info.get("compression", {})
        if comp:
            print(f"Compression: mode={comp.get('mode')} level={comp.get('level')} solid_sort={comp.get('payload_solid_sort')} adaptive_sort={comp.get('adaptive_sort')} winner={comp.get('winning_sorter')}")
        print(f"Files: {info['stats'].get('file_count', len(info['files']))}")
        for f in info["files"]:
            cat = f.get("category") or ""
            print(f"{f['size']:>10}  {cat:>12}  {f['path']}")
    return 0


def cmd_test(args: argparse.Namespace) -> int:
    result = CrystalZipArchive(Path(args.archive)).test()
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 2


def zip_baseline(inputs: List[Path], output: Path) -> None:
    files = collect_files(inputs)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path, data in files:
            zf.writestr(path, data)


def cmd_bench(args: argparse.Namespace) -> int:
    out_dir = Path(args.out)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    d = out_dir / "input"
    d.mkdir()
    (d / "a.txt").write_text("hello world\n" * 10000, encoding="utf-8")
    (d / "b.py").write_text("print('hello')\n" * 10000, encoding="utf-8")
    (d / "c.bin").write_bytes(os.urandom(30000))
    (d / "d.dat").write_bytes((b"ABCD" * 20000) + os.urandom(10000))
    cz = out_dir / "data.cz"
    zp = out_dir / "data.zip"
    summary = pack_archive([d], cz, mode=args.mode, level=args.level)
    zip_baseline([d], zp)
    test = CrystalZipArchive(cz).test()
    report = {
        "crystalzip_bytes": cz.stat().st_size,
        "zip_bytes": zp.stat().st_size,
        "savings_vs_zip_bytes": zp.stat().st_size - cz.stat().st_size,
        "savings_vs_zip_pct": round((zp.stat().st_size - cz.stat().st_size) / zp.stat().st_size * 100, 2),
        "verify": test,
        "summary": summary,
    }
    (out_dir / "benchmark_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="crystalzip", description="CrystalZip v2.5 adaptive sorter tournament compression")
    sub = p.add_subparsers(dest="cmd", required=True)

    pack = sub.add_parser("pack")
    pack.add_argument("-o", "--output", required=True)
    pack.add_argument("--mode", choices=["fast", "balanced", "max", "ultra"], default="max")
    pack.add_argument("--level", type=int, default=None)
    pack.add_argument("--no-solid-sort", action="store_true")
    pack.add_argument("--no-adaptive-sort", action="store_true")
    pack.add_argument("--no-grouped-streams", action="store_true")  # compatibility no-op
    pack.add_argument("inputs", nargs="+")
    pack.set_defaults(func=cmd_pack)

    unpack = sub.add_parser("unpack")
    unpack.add_argument("archive")
    unpack.add_argument("-o", "--out", required=True)
    unpack.set_defaults(func=cmd_unpack)

    ls = sub.add_parser("list")
    ls.add_argument("archive")
    ls.add_argument("--json", action="store_true")
    ls.set_defaults(func=cmd_list)

    test = sub.add_parser("test")
    test.add_argument("archive")
    test.set_defaults(func=cmd_test)

    bench = sub.add_parser("bench")
    bench.add_argument("-o", "--out", required=True)
    bench.add_argument("--mode", choices=["fast", "balanced", "max", "ultra"], default="max")
    bench.add_argument("--level", type=int, default=None)
    bench.set_defaults(func=cmd_bench)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

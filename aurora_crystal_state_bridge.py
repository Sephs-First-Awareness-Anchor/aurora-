#!/usr/bin/env python3
"""
Aurora Crystal State Bridge
===========================

Pack and restore Aurora's local state with CrystalZip.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from crystalzip import CrystalZipArchive, pack_archive


DEFAULT_PROFILE = "core"
BUNDLE_ROOT_PREFIX = "aurora_crystal_bundle"

EXCLUDED_NAMES = {
    "gpt_api_key.txt",
    "gemini_api_key.txt",
}

EXCLUDED_SUFFIXES = {
    ".bak",
    ".cz",
    ".log",
    ".pyc",
    ".pyo",
    ".swp",
    ".swo",
    ".tmp",
    ".zip",
}

PROFILE_SPECS: Dict[str, Dict[str, Any]] = {
    "core": {
        "description": "Durable Aurora identity, governance, continuity, and sensory crystal state.",
        "files": [
            "aurora_conversation_memory.json",
            "aurora_identity.json",
            "aurora_oets_web.json",
            "autonomy_state.json",
            "checkpoint.json",
            "contradiction_ledger.json",
            "daemon_status.json",
            "dual_strata_snapshot.json",
            "language_highway.json",
            "language_state.json",
            "lexeme_bindings.json",
            "lexicon.json",
            "operation_descriptors.json",
            "poedex_issue_research_state.json",
            "runtime_checkpoint.json",
            "sedimemory_checkpoint.json",
            "sensory_competency_state.json",
            "sensory_crystal_state.json",
            "surface_daemon_status.json",
            "subsurface_projection.json",
            "vision_index.json",
            "vision_state.json",
            "aurora_room_activity.json",
            "aurora_room_notes.json",
        ],
        "dirs": [
            "sensory_crystal",
        ],
    },
    "full": {
        "description": "Core state plus broader operational state Aurora keeps on disk.",
        "files": [
            "aurora_conversation_memory.json",
            "aurora_identity.json",
            "aurora_oets_web.json",
            "autonomy_state.json",
            "checkpoint.json",
            "contradiction_ledger.json",
            "daemon_status.json",
            "dual_strata_snapshot.json",
            "language_highway.json",
            "language_state.json",
            "lexeme_bindings.json",
            "lexicon.json",
            "operation_descriptors.json",
            "poedex_issue_research_state.json",
            "runtime_checkpoint.json",
            "sedimemory_checkpoint.json",
            "sensory_competency_state.json",
            "sensory_crystal_state.json",
            "surface_daemon_status.json",
            "surface_turn_queue.json",
            "surface_turn_result.json",
            "subsurface_projection.json",
            "vision_index.json",
            "vision_state.json",
            "aurora_room_activity.json",
            "aurora_room_notes.json",
        ],
        "dirs": [
            "sensory_crystal",
        ],
    },
    "all": {
        "description": "Recursive capture of the whole Aurora state tree, minus obvious secrets and temp clutter.",
        "recursive": True,
    },
}


def _profile_spec(profile: str) -> Dict[str, Any]:
    key = str(profile or DEFAULT_PROFILE).strip().lower()
    if key not in PROFILE_SPECS:
        raise ValueError(f"unknown CrystalZip Aurora profile: {profile!r}")
    return PROFILE_SPECS[key]


def _normalize_rel(path: str | Path) -> str:
    return str(Path(path)).replace("\\", "/").lstrip("./")


def _is_excluded(path: Path) -> bool:
    name = path.name.lower()
    if name in EXCLUDED_NAMES:
        return True
    if any(part == "__pycache__" for part in path.parts):
        return True
    if any(part.startswith(".") and part not in {".", ".."} for part in path.parts):
        return True
    if any(token in name for token in ("api_key", "secret", "token", "password")):
        return True
    return path.suffix.lower() in EXCLUDED_SUFFIXES


def _copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _copy_dir(src: Path, dst: Path) -> List[str]:
    copied: List[str] = []
    for root, _, files in os.walk(src):
        root_path = Path(root)
        for name in files:
            source = root_path / name
            if _is_excluded(source):
                continue
            rel = source.relative_to(src)
            _copy_file(source, dst / rel)
            copied.append(_normalize_rel(rel))
    return copied


def _copy_tree(src: Path, dst: Path) -> List[str]:
    copied: List[str] = []
    for root, _, files in os.walk(src):
        root_path = Path(root)
        for name in files:
            source = root_path / name
            if _is_excluded(source):
                continue
            rel = source.relative_to(src)
            _copy_file(source, dst / rel)
            copied.append(_normalize_rel(rel))
    return copied


def _stage_bundle(state_dir: Path, profile: str) -> Tuple[Path, Dict[str, Any]]:
    spec = _profile_spec(profile)
    bundle_root = Path(tempfile.mkdtemp(prefix=f"{BUNDLE_ROOT_PREFIX}_"))
    state_root = bundle_root / "state"
    included: List[str] = []
    missing: List[str] = []

    if spec.get("recursive"):
        copied = _copy_tree(state_dir, state_root)
        included.extend(copied)
        scope = "recursive_tree"
    else:
        for rel in spec.get("files", []):
            source = state_dir / rel
            if not source.exists() or _is_excluded(source):
                missing.append(_normalize_rel(rel))
                continue
            if source.is_file():
                _copy_file(source, state_root / Path(rel))
                included.append(_normalize_rel(rel))
            elif source.is_dir():
                copied = _copy_dir(source, state_root / Path(rel))
                included.extend(_normalize_rel(Path(rel) / Path(item)) for item in copied)

        for rel in spec.get("dirs", []):
            source = state_dir / rel
            if not source.exists() or _is_excluded(source):
                missing.append(_normalize_rel(rel))
                continue
            if source.is_dir():
                copied = _copy_dir(source, state_root / Path(rel))
                included.extend(_normalize_rel(Path(rel) / Path(item)) for item in copied)
            elif source.is_file():
                _copy_file(source, state_root / Path(rel))
                included.append(_normalize_rel(rel))
        scope = "curated"

    manifest = {
        "format": "AuroraCrystalStateBundle",
        "version": 1,
        "created_at": time.time(),
        "profile": str(profile or DEFAULT_PROFILE).strip().lower(),
        "description": spec.get("description", ""),
        "scope": scope,
        "state_dir": str(state_dir),
        "bundle_root": bundle_root.name,
        "included_paths": sorted(dict.fromkeys(included)),
        "missing_paths": sorted(dict.fromkeys(missing)),
        "excluded_policy": {
            "names": sorted(EXCLUDED_NAMES),
            "suffixes": sorted(EXCLUDED_SUFFIXES),
        },
    }
    (bundle_root / "bundle_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return bundle_root, manifest


def pack_state_bundle(
    state_dir: str | Path = "aurora_state",
    output: str | Path | None = None,
    *,
    profile: str = DEFAULT_PROFILE,
    level: int | None = None,
    mode: str = "max",
) -> Dict[str, Any]:
    state_path = Path(state_dir).expanduser()
    if not state_path.exists():
        raise FileNotFoundError(str(state_path))

    bundle_root, manifest = _stage_bundle(state_path, profile)
    try:
        output_path = Path(output).expanduser() if output else state_path / f"aurora_{manifest['profile']}.cz"
        summary = pack_archive([bundle_root], output_path, level=level, mode=mode)
    finally:
        shutil.rmtree(bundle_root, ignore_errors=True)

    summary.update(
        {
            "bundle_profile": manifest["profile"],
            "bundle_description": manifest["description"],
            "bundle_manifest": manifest,
        }
    )
    return summary


def _locate_bundle_root(extracted_root: Path) -> Path:
    manifest_path = extracted_root / "bundle_manifest.json"
    if manifest_path.exists():
        return extracted_root

    matches = list(extracted_root.glob("*/bundle_manifest.json"))
    if len(matches) == 1:
        return matches[0].parent
    if len(matches) > 1:
        raise ValueError("multiple bundle manifests found in extracted archive")
    raise ValueError("bundle manifest not found in extracted archive")


def restore_state_bundle(
    archive: str | Path,
    state_dir: str | Path = "aurora_state",
) -> Dict[str, Any]:
    archive_path = Path(archive).expanduser()
    state_path = Path(state_dir).expanduser()
    state_path.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="aurora_crystal_restore_") as td:
        staging = Path(td)
        CrystalZipArchive(archive_path).unpack(staging)
        bundle_root = _locate_bundle_root(staging)
        manifest_path = bundle_root / "bundle_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
        state_source = bundle_root / "state"
        if not state_source.exists():
            raise ValueError("bundle does not contain a state/ directory")

        restored = 0
        for source in sorted(state_source.rglob("*")):
            if source.is_dir() or _is_excluded(source):
                continue
            target = state_path / source.relative_to(state_source)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            restored += 1

    return {
        "restored_to": str(state_path),
        "archive": str(archive_path),
        "bundle_manifest": manifest,
        "files_restored": restored,
    }


def inspect_state_bundle(archive: str | Path) -> Dict[str, Any]:
    archive_path = Path(archive).expanduser()
    info = CrystalZipArchive(archive_path).list()
    manifest: Dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="aurora_crystal_inspect_") as td:
        staging = Path(td)
        CrystalZipArchive(archive_path).unpack(staging)
        try:
            bundle_root = _locate_bundle_root(staging)
            manifest_path = bundle_root / "bundle_manifest.json"
            if manifest_path.exists():
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            manifest = {}
    return {"crystalzip": info, "bundle_manifest": manifest}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aurora-crystal", description="Aurora CrystalZip state bridge")
    sub = parser.add_subparsers(dest="cmd", required=True)

    pack = sub.add_parser("pack", help="pack Aurora state into a CrystalZip bundle")
    pack.add_argument("--state-dir", default="aurora_state")
    pack.add_argument("-o", "--output", default=None)
    pack.add_argument("--profile", default=DEFAULT_PROFILE, choices=sorted(PROFILE_SPECS))
    pack.add_argument("--mode", default="max", choices=["fast", "balanced", "max", "ultra"])
    pack.add_argument("--level", type=int, default=None)
    pack.set_defaults(func=lambda args: pack_state_bundle(
        state_dir=args.state_dir,
        output=args.output,
        profile=args.profile,
        level=args.level,
        mode=args.mode,
    ))

    restore = sub.add_parser("restore", help="restore Aurora state from a CrystalZip bundle")
    restore.add_argument("archive")
    restore.add_argument("--state-dir", default="aurora_state")
    restore.set_defaults(func=lambda args: restore_state_bundle(
        args.archive,
        state_dir=args.state_dir,
    ))

    inspect = sub.add_parser("inspect", help="inspect a CrystalZip bundle")
    inspect.add_argument("archive")
    inspect.set_defaults(func=lambda args: inspect_state_bundle(args.archive))

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    result = args.func(args)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

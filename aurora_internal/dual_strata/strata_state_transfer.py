#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
strata_state_transfer.py -- moving a whole state directory between devices,
verified file by file (FIX-A125).

Two jobs, one mechanism:

  SEED     The Surface device (which has lived the history) gives the
           Subsurface device the continuity it is missing, so the Subsurface
           colours the Surface from the same history it has actually had.
  HANDOFF  The active Surface checkpoints everything it holds on the
           Subsurface device; a second device claims the Surface role with the
           checkpoint's token and pulls the same state, so the Surface moves
           devices without losing what it lived.

This module contains no network code and no cognition.  It selects files,
describes them (path, size, sha-256), stages incoming bytes, verifies every
file against its hash before it is trusted, and installs verified files with a
backup.  strata_link.py carries the requests.

What is NOT transferred: the link's own directory (secrets, outboxes, device
identity), the transient channel files that strata_link already carries as
live channels or that are per-device (heartbeats, daemon status, locks), and
the device's fault log.  Everything else in the state directory is continuity.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Tuple

CHUNK_BYTES = 1024 * 1024

# Never part of a transfer.
EXCLUDED_DIRS = frozenset({"strata_link", "__pycache__", ".git"})
EXCLUDED_SUFFIXES = (".tmp", ".part", ".lock", ".pid", ".swp")
EXCLUDED_NAMES = frozenset({
    # live channels strata_link already carries (or that stay on one device)
    "surface_continuity_feed.json", "subsurface_projection.json",
    "predictive_frame_queue.json", "subsurface_presence_frame.json",
    "surface_sensory_snapshot.json", "surface_sensory_guidance_queue.json",
    "surface_turn_queue.json", "subsurface_turn_events.json",
    # per-device liveness and diagnostics
    "daemon_status.json", "surface_daemon_status.json",
    "subsurface_daemon_status.json", "subsurface_heartbeat.json",
    "emergence_monitor_status.json", "interaction_status.json",
    "runtime_faults.jsonl",
})


class TransferError(Exception):
    """A transfer step failed; the message says which and why."""


def file_sha256(path: Path, *, block: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            data = handle.read(block)
            if not data:
                break
            digest.update(data)
    return digest.hexdigest()


def is_transferable(rel_path: str) -> bool:
    parts = Path(rel_path).parts
    if not parts or any(p in EXCLUDED_DIRS for p in parts[:-1]):
        return False
    name = parts[-1]
    return name not in EXCLUDED_NAMES and not name.endswith(EXCLUDED_SUFFIXES)


def safe_join(base: Path, rel_path: str) -> Path:
    """base / rel_path, refusing anything that would leave base."""
    rel = str(rel_path or "").replace("\\", "/")
    if not rel or rel.startswith("/") or ".." in Path(rel).parts or ":" in rel.split("/")[0]:
        raise TransferError(f"unsafe path: {rel_path!r}")
    target = (Path(base) / rel).resolve()
    root = Path(base).resolve()
    if root != target and root not in target.parents:
        raise TransferError(f"path escapes the state directory: {rel_path!r}")
    return target


def list_transferable(state_dir: Any) -> List[str]:
    root = Path(str(state_dir))
    found: List[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]
        for name in filenames:
            rel = (Path(dirpath) / name).relative_to(root).as_posix()
            if is_transferable(rel):
                found.append(rel)
    return sorted(found)


def build_manifest(root: Any, rel_paths: Optional[Iterable[str]] = None) -> List[Dict[str, Any]]:
    base = Path(str(root))
    out: List[Dict[str, Any]] = []
    for rel in (list(rel_paths) if rel_paths is not None else list_transferable(base)):
        path = base / rel
        if path.is_file():
            out.append({"path": rel, "size": path.stat().st_size, "sha256": file_sha256(path)})
    return out


def manifest_digest(manifest: Iterable[Mapping[str, Any]]) -> str:
    rows = [(str(m["path"]), int(m["size"]), str(m["sha256"])) for m in manifest]
    return hashlib.sha256(json.dumps(sorted(rows)).encode("utf-8")).hexdigest()


def validate_manifest(manifest: Any) -> List[Dict[str, Any]]:
    if not isinstance(manifest, list) or not manifest:
        raise TransferError("manifest must be a non-empty list")
    clean: List[Dict[str, Any]] = []
    seen = set()
    for row in manifest:
        if not isinstance(row, Mapping):
            raise TransferError("manifest rows must be objects")
        rel = str(row.get("path") or "")
        if rel in seen:
            raise TransferError(f"duplicate path: {rel}")
        seen.add(rel)
        if not is_transferable(rel):
            raise TransferError(f"path is not transferable: {rel}")
        safe_join(Path("."), rel)  # shape check only
        sha = str(row.get("sha256") or "")
        if len(sha) != 64:
            raise TransferError(f"bad sha256 for {rel}")
        clean.append({"path": rel, "size": int(row.get("size", 0) or 0), "sha256": sha})
    return clean


def snapshot_state(state_dir: Any, snapshot_dir: Path) -> List[Dict[str, Any]]:
    """Copy the transferable files to a private directory and describe the
    COPY, so the hashes sent describe exactly the bytes sent even while the
    live files keep changing underneath."""
    src = Path(str(state_dir))
    snapshot_dir = Path(snapshot_dir)
    if snapshot_dir.exists():
        shutil.rmtree(snapshot_dir)
    snapshot_dir.mkdir(parents=True)
    kept: List[str] = []
    for rel in list_transferable(src):
        try:
            dest = snapshot_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src / rel, dest)
            kept.append(rel)
        except OSError:
            continue  # a file that vanished mid-copy is not part of this snapshot
    return build_manifest(snapshot_dir, kept)


def read_chunk(base: Path, rel_path: str, offset: int, length: int) -> Dict[str, Any]:
    path = safe_join(base, rel_path)
    with open(path, "rb") as handle:
        handle.seek(int(offset))
        data = handle.read(int(length))
    return {"path": rel_path, "offset": int(offset), "n": len(data),
            "data": base64.b64encode(data).decode("ascii")}


class IncomingTransfer:
    """Bytes arriving for one manifest, staged under staging_root/<id>/files.

    Chunks must arrive in order per file.  A file is trusted only once its
    full content matches its manifest hash; until then it is a .part file.
    Re-offering the same transfer id resumes where it stopped."""

    def __init__(self, staging_root: Path, transfer_id: str) -> None:
        self.root = Path(staging_root) / str(transfer_id)
        self.files = self.root / "files"
        self.manifest_path = self.root / "manifest.json"

    def exists(self) -> bool:
        return self.manifest_path.exists()

    def manifest(self) -> List[Dict[str, Any]]:
        try:
            return validate_manifest(json.loads(self.manifest_path.read_text(encoding="utf-8")))
        except TransferError:
            raise
        except Exception as exc:
            raise TransferError(f"no staged manifest: {exc}")

    def begin(self, manifest: List[Dict[str, Any]], *, meta: Mapping[str, Any]) -> None:
        self.files.mkdir(parents=True, exist_ok=True)
        tmp = self.manifest_path.with_name("manifest.json.tmp")
        tmp.write_text(json.dumps({"manifest": manifest, "meta": dict(meta)}), encoding="utf-8")
        os.replace(str(tmp), str(self.manifest_path))

    def _row(self, rel_path: str) -> Dict[str, Any]:
        raw = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        for row in raw.get("manifest", []):
            if row.get("path") == rel_path:
                return row
        raise TransferError(f"not in manifest: {rel_path}")

    def meta(self) -> Dict[str, Any]:
        raw = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        return dict(raw.get("meta") or {})

    def raw_manifest(self) -> List[Dict[str, Any]]:
        raw = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        return list(raw.get("manifest") or [])

    def complete_paths(self) -> List[str]:
        done = []
        for row in self.raw_manifest():
            path = self.files / row["path"]
            if path.is_file() and path.stat().st_size == int(row["size"]):
                done.append(row["path"])
        return done

    def put_chunk(self, rel_path: str, offset: int, data_b64: str) -> Dict[str, Any]:
        row = self._row(rel_path)
        final_path = safe_join(self.files, rel_path)
        part = final_path.with_name(final_path.name + ".part")
        part.parent.mkdir(parents=True, exist_ok=True)
        have = part.stat().st_size if part.exists() else 0
        if int(offset) != have:
            return {"ok": False, "expected_offset": have}
        data = base64.b64decode(str(data_b64).encode("ascii"))
        with open(part, "ab") as handle:
            handle.write(data)
        size = have + len(data)
        if size > int(row["size"]):
            part.unlink()
            raise TransferError(f"{rel_path}: more bytes than the manifest declares")
        if size == int(row["size"]):
            if file_sha256(part) != row["sha256"]:
                part.unlink()
                raise TransferError(f"{rel_path}: sha256 mismatch after full transfer")
            os.replace(str(part), str(final_path))
            return {"ok": True, "complete": True, "size": size}
        return {"ok": True, "complete": False, "size": size}

    def accept_existing(self, rel_path: str, source: Path) -> None:
        """The destination already holds this exact file: stage it by copy."""
        dest = safe_join(self.files, rel_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)

    def verify_all(self) -> List[str]:
        """Paths that are missing or do not match their hash."""
        bad = []
        for row in self.raw_manifest():
            path = self.files / row["path"]
            if not path.is_file() or path.stat().st_size != int(row["size"]) \
                    or file_sha256(path) != row["sha256"]:
                bad.append(row["path"])
        return bad

    def discard(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)


def install_verified(files_dir: Path, manifest: Iterable[Mapping[str, Any]],
                     target_dir: Any, backup_dir: Path) -> Dict[str, int]:
    """Install verified staged files into target_dir.  A file already equal to
    the staged one is left alone; a different one is backed up first.  Each
    file lands by os.replace, so a reader never sees half a file."""
    target = Path(str(target_dir))
    installed = unchanged = backed_up = 0
    for row in manifest:
        rel = str(row["path"])
        src = Path(files_dir) / rel
        dest = safe_join(target, rel)
        if dest.is_file() and dest.stat().st_size == int(row["size"]) \
                and file_sha256(dest) == row["sha256"]:
            unchanged += 1
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.is_file():
            keep = safe_join(Path(backup_dir), rel)
            keep.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(dest, keep)
            backed_up += 1
        tmp = dest.with_name(dest.name + ".incoming.tmp")
        shutil.copyfile(src, tmp)
        os.replace(str(tmp), str(dest))
        installed += 1
    return {"installed": installed, "unchanged": unchanged, "backed_up": backed_up}


def compare_to_manifest(state_dir: Any, manifest: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    """How a state directory stands against a manifest (read-only)."""
    base = Path(str(state_dir))
    match, differ, missing = 0, [], []
    for row in manifest:
        path = safe_join(base, str(row["path"]))
        if not path.is_file():
            missing.append(row["path"])
        elif path.stat().st_size == int(row["size"]) and file_sha256(path) == row["sha256"]:
            match += 1
        else:
            differ.append(row["path"])
    return {"match": match, "differ": sorted(differ), "missing": sorted(missing),
            "total": match + len(differ) + len(missing)}

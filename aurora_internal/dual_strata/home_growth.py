#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
home_growth.py -- home's growth reaching the surface (surface restructure 3b,
item 2: read-only copies stay current).

One mind: her deep developmental stores (lexicon, grammar, grounding,
understanding ledgers, lineages, ...) are learned at home.  The surface keeps
read-only copies of them so it can be her offline.  Without this module those
copies would only ever be what the first pairing left behind, and the surface
would slowly become a second, younger mind.  With it, what home has grown
comes down to the surface and is installed at its next start, before the
store gate is armed and before any organ loads a store.

What travels: only home-developmental stores (aurora_store_ownership), only
transferable paths (strata_state_transfer), and only files whose bytes differ
from the surface's copy.  Nothing is deleted on either side.  Every file is
verified against the hash home offered; a file that changed at home while it
was being read simply fails verification and is fetched again next time.

Nothing here learns, chooses or writes behaviour.  It moves bytes home already
owns to the device that is her surface.
"""
from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional

GROWTH_DIRNAME = "growth"
READY_FILENAME = "ready.json"
HASH_CACHE_FILENAME = "hash_cache.json"
LAST_FILENAME = "last_install.json"
# How often a surface asks home what has grown.  Growth is slow; nothing is
# installed until the next start anyway.
GROWTH_PULL_INTERVAL_S = 900.0


def _growth_root(state_dir: Any) -> Path:
    from aurora_internal.dual_strata.strata_link import link_dir
    root = link_dir(state_dir) / GROWTH_DIRNAME
    root.mkdir(parents=True, exist_ok=True)
    return root


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, indent=1, sort_keys=True), encoding="utf-8")
    os.replace(str(tmp), str(path))


class HashCache:
    """sha256 by (size, mtime) so a large state is not re-hashed every time."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path
        loaded = _read_json(path, {}) if path is not None else {}
        self.rows: Dict[str, List[Any]] = loaded if isinstance(loaded, dict) else {}
        self.dirty = False

    def sha(self, base: Path, rel: str) -> Optional[Dict[str, Any]]:
        from aurora_internal.dual_strata import strata_state_transfer as st
        target = base / rel
        try:
            info = target.stat()
        except OSError:
            self.rows.pop(rel, None)
            return None
        if not target.is_file():
            return None
        key = [int(info.st_size), int(info.st_mtime_ns)]
        row = self.rows.get(rel)
        if isinstance(row, list) and len(row) == 3 and row[:2] == key:
            return {"path": rel, "size": key[0], "sha256": row[2]}
        digest = st.file_sha256(target)
        self.rows[rel] = key + [digest]
        self.dirty = True
        return {"path": rel, "size": key[0], "sha256": digest}

    def save(self) -> None:
        if self.path is not None and self.dirty:
            _write_json(self.path, self.rows)
            self.dirty = False


def home_owned_paths(state_dir: Any) -> List[str]:
    """Every transferable path in ``state_dir`` that home owns."""
    from aurora_internal.aurora_store_ownership import HOME_DEVELOPMENTAL, classify
    from aurora_internal.dual_strata import strata_state_transfer as st
    return [rel for rel in st.list_transferable(state_dir) if classify(rel) == HOME_DEVELOPMENTAL]


def is_growth_path(rel: str) -> bool:
    from aurora_internal.aurora_store_ownership import HOME_DEVELOPMENTAL, classify
    from aurora_internal.dual_strata import strata_state_transfer as st
    return st.is_transferable(rel) and classify(rel) == HOME_DEVELOPMENTAL


def home_growth_manifest(state_dir: Any, cache: Optional[HashCache] = None) -> List[Dict[str, Any]]:
    """Home's side: what her home-owned stores are right now."""
    base = Path(str(state_dir))
    cache = cache or HashCache()
    rows = [row for row in (cache.sha(base, rel) for rel in home_owned_paths(base)) if row]
    return rows


def _wanted(state_dir: Any, manifest: List[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """Rows of home's manifest whose bytes this surface does not hold."""
    base = Path(str(state_dir))
    cache = HashCache(_growth_root(state_dir) / HASH_CACHE_FILENAME)
    wanted: List[Dict[str, Any]] = []
    for row in manifest:
        rel = str(row.get("path") or "")
        if not is_growth_path(rel):
            continue
        local = cache.sha(base, rel)
        if local and local["size"] == int(row["size"]) and local["sha256"] == row["sha256"]:
            continue
        wanted.append({"path": rel, "size": int(row["size"]), "sha256": str(row["sha256"])})
    cache.save()
    return wanted


def pull_growth(state_call: Callable[[Dict[str, Any]], Dict[str, Any]], state_dir: Any,
                *, chunk_bytes: Optional[int] = None) -> Dict[str, Any]:
    """Surface's side: fetch what home has grown into a staging area and mark
    it ready for the next start.  ``state_call`` is the client's signed
    state-op call.  Returns a report; raises nothing it can report."""
    from aurora_internal.dual_strata import strata_state_transfer as st
    chunk = int(chunk_bytes or st.CHUNK_BYTES)
    root = _growth_root(state_dir)
    try:
        offer = state_call({"op": "growth_offer"})
        manifest = list(offer.get("manifest") or [])
        if not manifest:
            return {"ok": True, "wanted": 0, "staged": 0, "home_files": 0}
        st.validate_manifest(manifest)
        wanted = _wanted(state_dir, manifest)
        if not wanted:
            # Nothing differs: anything staged earlier is already superseded.
            shutil.rmtree(root / "incoming", ignore_errors=True)
            (root / READY_FILENAME).unlink(missing_ok=True)
            return {"ok": True, "wanted": 0, "staged": 0, "home_files": len(manifest)}
        digest = st.manifest_digest(wanted)
        staging = st.IncomingTransfer(root / "incoming", digest[:16])
        if not staging.exists():
            shutil.rmtree(root / "incoming", ignore_errors=True)
            staging.begin(wanted, meta={"purpose": "growth", "digest": digest, "at": time.time()})
        done = set(staging.complete_paths())
        pulled = 0
        for row in wanted:
            if row["path"] in done:
                continue
            offset = 0
            while True:
                got = state_call({"op": "growth_chunk", "path": row["path"],
                                  "offset": offset, "length": chunk})
                reply = staging.put_chunk(row["path"], offset, str(got.get("data") or ""))
                if "expected_offset" in reply:
                    offset = int(reply["expected_offset"])
                    continue
                n = int(got.get("n", 0) or 0)
                offset += n
                pulled += n
                if reply.get("complete") or not n:
                    break
        bad = staging.verify_all()
        good = [row for row in wanted if row["path"] not in set(bad)]
        if good:
            _write_json(root / READY_FILENAME, {"transfer": digest[:16], "manifest": good,
                                                "at": time.time(), "home_files": len(manifest)})
        return {"ok": True, "wanted": len(wanted), "staged": len(good), "changed_while_read": len(bad),
                "bytes_pulled": pulled, "home_files": len(manifest)}
    except st.TransferError as exc:
        return {"ok": False, "error": str(exc)[:300]}
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"[:300]}


def install_pending_growth(state_dir: Any) -> Dict[str, Any]:
    """At the surface's start, before the store gate is armed and before any
    organ loads a store: install what home grew.  The previous copy of each
    replaced file is kept until the next install (one generation only)."""
    from aurora_internal.dual_strata import strata_state_transfer as st
    root = _growth_root(state_dir)
    ready = _read_json(root / READY_FILENAME, None)
    if not isinstance(ready, dict) or not ready.get("manifest"):
        return {"installed": 0, "pending": False}
    files = root / "incoming" / str(ready.get("transfer") or "") / "files"
    try:
        manifest = [row for row in ready["manifest"] if is_growth_path(str(row.get("path") or ""))]
        for row in manifest:
            src = files / row["path"]
            if not src.is_file() or st.file_sha256(src) != row["sha256"]:
                raise st.TransferError(f"staged copy no longer verifies: {row['path']}")
        backup = root / "previous"
        shutil.rmtree(backup, ignore_errors=True)
        report = st.install_verified(files, manifest, state_dir, backup)
        result = {"pending": False, "at": time.time(), "files": len(manifest), **report}
        _write_json(root / LAST_FILENAME, result)
        return result
    except Exception as exc:
        result = {"installed": 0, "pending": False, "error": f"{type(exc).__name__}: {exc}"[:300]}
        _write_json(root / LAST_FILENAME, {"at": time.time(), **result})
        return result
    finally:
        (root / READY_FILENAME).unlink(missing_ok=True)
        shutil.rmtree(root / "incoming", ignore_errors=True)


def growth_status(state_dir: Any) -> Dict[str, Any]:
    root = Path(str(state_dir)) / "strata_link" / GROWTH_DIRNAME
    ready = _read_json(root / READY_FILENAME, None)
    return {"waiting_for_restart": len((ready or {}).get("manifest") or []) if isinstance(ready, dict) else 0,
            "last_install": _read_json(root / LAST_FILENAME, None)}

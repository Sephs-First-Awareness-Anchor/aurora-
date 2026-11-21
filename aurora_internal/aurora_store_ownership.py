#!/usr/bin/env python3
"""
aurora_store_ownership.py -- which device owns each of Aurora's stores, and the one
gate every write to a home-owned store passes through on a surface-only device
(surface restructure 3f, Sir's tightening 3).

One state, one mind.  When the phone is the surface of a paired home, her
deep developmental stores (lexicon, grammar, grounding, interaction memory,
understanding ledgers, reasoning paths, lineages, timeline, ...) belong to
home.  The phone keeps read-only copies; what she lives there goes home in
her continuity packets, and home's organs do the learning.  Nothing here
decides what she learns or says: it only decides WHERE a store may be
written, so learning never silently forks onto a second device.

CLASSES
  surface_present   her present on this device: working state, last traces,
                    the strata link's own files, the continuity feed,
                    sensory snapshots.  Written freely.
  journal           fault, fail, register and other append-only logs.
                    Appended locally (they are this device's record).
  cache             locks, temporary files, indexes.  Local only.
  home_developmental  everything else.  On a surface-only device a write to
                    the canonical copy is never made.  It lands instead in
                    her PROVISIONAL view (below), or, past that view's
                    budget, is declined, counted per store and shown on the
                    hub; neither is a fault, because nothing failed.
  provisional       provisional/<store>: what the surface itself learned
                    from what it lived, while home's canonical store is not
                    yet hers here (dual-strata directive, sec. 8).

THE PROVISIONAL VIEW (offline learning without split-brain persistence)
  A surface-only device still lives whole turns and its organs still learn
  from them in memory.  Their saves go to provisional/<store> instead of the
  canonical copy, so after a restart (offline, home asleep, link down) she
  continues from what she lived rather than from the last copy home gave her.
  It is a view, never a second authority:
    * the canonical copy on this device is never rewritten by the surface;
    * each provisional store remembers the canonical bytes it grew from
      (base_sha).  restore_provisional(), at the surface's start, lays the
      view over the canonical copy only while that copy is still those same
      bytes.  When home's growth has replaced the copy, home's integration of
      the same lived occurrences is authoritative and the view is retired;
      the occurrences themselves were never in the view, they wait in the
      strata link's outbox and are admitted at home once (FIX-A118);
    * nothing under provisional/ is offered as home growth or sent home as
      a store; it rides a handoff only as part of her present (MOVES_WITH_HER);
    * it is bounded (PROVISIONAL_MAX_BYTES).  Past it a write is declined
      exactly as before; nothing is evicted.

Unknown stores default to home-owned: a new organ's store cannot start
learning on the phone by accident.

The gate is off unless enable_surface_only() was called for a state
directory, so a whole-mind device (home, or an unpaired phone) is unchanged.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import fnmatch
import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SURFACE_PRESENT = "surface_present"
JOURNAL = "journal"
CACHE = "cache"
HOME_DEVELOPMENTAL = "home_developmental"
PROVISIONAL = "provisional"

PROVISIONAL_DIRNAME = "provisional"
PROVISIONAL_MANIFEST = "_provisional.json"
PROVISIONAL_MAX_BYTES = 96 * 1024 * 1024
SNAPSHOT = "snapshot"     # the writer rewrites the whole store
APPEND = "append"         # the writer appends lines to the store

# First match wins.  Paths are relative to the state directory, "/"-separated.
OWNERSHIP_TABLE: Tuple[Tuple[str, str], ...] = (
    # her provisional view of home's stores (sec. 8); never a home store itself
    ("provisional/*", PROVISIONAL),
    # surface-owned present
    ("strata_link/*", SURFACE_PRESENT),
    ("surface_working_state.json", SURFACE_PRESENT),
    ("surface_continuity_feed.json", SURFACE_PRESENT),
    ("surface_sensory_*", SURFACE_PRESENT),
    ("subsurface_projection.json", SURFACE_PRESENT),        # arrives from home
    ("predictive_frame_queue.json", SURFACE_PRESENT),       # arrives from home
    ("surface_sensory_guidance_queue.json", SURFACE_PRESENT),
    ("subsurface_turn_events.json", SURFACE_PRESENT),       # stays on the surface by design
    ("dual_strata_snapshot.json", SURFACE_PRESENT),
    ("cers_snapshot.json", SURFACE_PRESENT),
    ("cers_detail.json", SURFACE_PRESENT),
    ("subsurface_detail.json", SURFACE_PRESENT),
    ("interaction_status.json", SURFACE_PRESENT),
    ("last_*.json", SURFACE_PRESENT),
    ("metabolic_clock.json", SURFACE_PRESENT),
    ("device_log.json", SURFACE_PRESENT),
    ("face_expression_journal.jsonl", SURFACE_PRESENT),
    ("habitat/*", SURFACE_PRESENT),                         # Space and Self live on the surface
    ("genealogy_surface/*", SURFACE_PRESENT),               # the surface's own session genealogy
    # journals
    ("runtime_faults.jsonl", JOURNAL),
    ("register_log.jsonl", JOURNAL),
    ("fail_stream.jsonl", JOURNAL),
    ("exploration_log.jsonl", JOURNAL),
    ("abstain_log.jsonl", JOURNAL),
    ("surface_pressure_log.jsonl", JOURNAL),
    ("mtsl_shadow_comparison.jsonl", JOURNAL),
    ("system_introspection_episodes.jsonl", JOURNAL),
    ("system_introspection_index.json", JOURNAL),           # index of the episodes journal above
    ("constraint_fallback_log.jsonl", JOURNAL),             # this device's fallback diagnostics
    ("envelope_shadow_log.jsonl", JOURNAL),                 # shadow comparison, like mtsl_shadow
    ("*.log", JOURNAL),
    # caches
    ("*.lock", CACHE),
    ("*.tmp", CACHE),
    ("cache/*", CACHE),
    ("tmp/*", CACHE),
    ("*_cache.json", CACHE),
)

# Her present that travels with her when she moves to another device: the
# holder's working frame and her habitat.  Everything else surface-owned is
# this device's own (link files, last traces, sensory snapshots).
# Her provisional view is lived-but-not-yet-integrated understanding: it is
# her present too, and restore_provisional() on the next device decides by
# its base bytes whether it still applies there.
MOVES_WITH_HER: Tuple[str, ...] = ("surface_working_state.json", "habitat/*", "provisional/*")

_TRANSIENT_SUFFIXES = (".settle.tmp", ".tmp", ".partial", ".settle")
_STATUS_FILE = "strata_link/store_gate.json"
_STATUS_EVERY_S = 30.0

_lock = threading.RLock()
_root: Optional[Path] = None
_refused: Dict[str, Dict[str, Any]] = {}
_status_written_at = 0.0


def _normalise(rel: str) -> str:
    rel = rel.replace(os.sep, "/").lstrip("./")
    for suffix in _TRANSIENT_SUFFIXES:
        if rel.endswith(suffix) and len(rel) > len(suffix):
            rel = rel[: -len(suffix)]
            break
    return rel


def classify(rel_path: str) -> str:
    """The ownership class of a store, by its path relative to the state dir."""
    rel = _normalise(str(rel_path))
    for pattern, owner in OWNERSHIP_TABLE:
        if fnmatch.fnmatchcase(rel, pattern):
            return owner
    return HOME_DEVELOPMENTAL


def moves_with_her(state_dir: Any) -> List[str]:
    """Relative paths, in ``state_dir``, of the present that goes with her
    in a handoff checkpoint.  Transient files are left behind."""
    root = Path(str(state_dir))
    found: List[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = Path(dirpath).relative_to(root).as_posix()
        if rel_dir != "." and not any(fnmatch.fnmatchcase(rel_dir + "/x", p) for p in MOVES_WITH_HER):
            dirnames[:] = [d for d in dirnames
                           if any(fnmatch.fnmatchcase(f"{rel_dir}/{d}/x", p) for p in MOVES_WITH_HER)]
            continue
        if rel_dir == ".":
            dirnames[:] = [d for d in dirnames if any(fnmatch.fnmatchcase(f"{d}/x", p) for p in MOVES_WITH_HER)]
        for name in filenames:
            rel = name if rel_dir == "." else f"{rel_dir}/{name}"
            if rel.endswith(_TRANSIENT_SUFFIXES + (".lock",)):
                continue
            if any(fnmatch.fnmatchcase(rel, p) for p in MOVES_WITH_HER):
                found.append(rel)
    return sorted(found)


def enable_surface_only(state_dir: Any) -> None:
    """This device is a surface of a paired home: home-owned stores in
    ``state_dir`` are read-only here from now on."""
    global _root
    with _lock:
        _root = Path(str(state_dir)).resolve()
        _refused.clear()


def disable_surface_only() -> None:
    global _root
    with _lock:
        _root = None
        _refused.clear()


def surface_only_root() -> Optional[Path]:
    return _root


def _relative(path: Any) -> Optional[str]:
    root = _root
    if root is None:
        return None
    try:
        target = Path(os.fspath(path)).resolve()
        return target.relative_to(root).as_posix()
    except (TypeError, ValueError, OSError):
        return None


def store_write_allowed(path: Any) -> bool:
    """True unless this is a surface-only device and ``path`` is a
    home-owned store in its state directory.  A declined write is counted
    per store, never raised and never recorded as a fault.

    Writers that can keep her provisional view use store_write_path()
    instead; this stays for callers that only need the yes/no."""
    rel = _relative(path)
    if rel is None:
        return True
    store = _normalise(rel)
    if classify(store) != HOME_DEVELOPMENTAL:
        return True
    _count_declined(store)
    return False


def _count_declined(store: str, key: str = "declined") -> None:
    now = time.time()
    with _lock:
        entry = _refused.setdefault(store, {"declined": 0, "provisional": 0,
                                            "first_at": now, "last_at": now})
        entry.setdefault("provisional", 0)
        entry[key] = int(entry.get(key, 0)) + 1
        entry["last_at"] = now
    _write_status(now)


def provisional_root(state_dir: Any = None) -> Optional[Path]:
    root = Path(str(state_dir)).resolve() if state_dir is not None else _root
    return None if root is None else root / PROVISIONAL_DIRNAME


def _sha_of(path: Path) -> str:
    import hashlib
    try:
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            for block in iter(lambda: handle.read(1 << 20), b""):
                digest.update(block)
        return digest.hexdigest()
    except OSError:
        return ""          # no canonical copy yet: the view grows from nothing


def _load_manifest(prov: Path) -> Dict[str, Any]:
    try:
        data = json.loads((prov / PROVISIONAL_MANIFEST).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("stores", {})
    return data


def _save_manifest(prov: Path, data: Dict[str, Any]) -> None:
    prov.mkdir(parents=True, exist_ok=True)
    tmp = prov / (PROVISIONAL_MANIFEST + ".tmp")
    tmp.write_text(json.dumps(data, sort_keys=True, indent=1), encoding="utf-8")
    os.replace(str(tmp), str(prov / PROVISIONAL_MANIFEST))


def _provisional_bytes(prov: Path) -> int:
    total = 0
    for dirpath, _dirs, files in os.walk(prov):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(dirpath, name))
            except OSError:
                pass
    return total


_budget_seen: Dict[str, float] = {"bytes": 0.0, "at": 0.0}
_BUDGET_RECHECK_S = 20.0


def _within_budget(prov: Path) -> bool:
    now = time.time()
    if now - _budget_seen["at"] > _BUDGET_RECHECK_S:
        _budget_seen["bytes"] = float(_provisional_bytes(prov))
        _budget_seen["at"] = now
    return _budget_seen["bytes"] < PROVISIONAL_MAX_BYTES


def _lived_mark() -> Dict[str, Any]:
    """Where her lived numbering stood when this view last changed (for the
    hub and for reconciliation reports; never used to outrank home)."""
    root = _root
    if root is None:
        return {}
    try:
        data = json.loads((root / "strata_link" / "lived_numbering.json").read_text(encoding="utf-8"))
        return {k: data.get(k) for k in ("surface_id", "epoch", "seq") if k in data}
    except (OSError, ValueError, AttributeError):
        return {}


def store_write_path(path: Any, mode: str = SNAPSHOT) -> Optional[Path]:
    """Where a write meant for ``path`` lands.

    Whole-mind device, or a store that is not home's: ``path`` itself.
    Surface-only device and a home-owned store: the same relative path under
    provisional/, recording on first use the canonical bytes the view grows
    from.  ``None`` when the provisional budget is spent (declined, counted).
    ``mode`` is SNAPSHOT for a writer that rewrites the whole store, APPEND
    for one that appends lines."""
    rel = _relative(path)
    if rel is None:
        return Path(os.fspath(path))
    store = _normalise(rel)
    if classify(store) != HOME_DEVELOPMENTAL:
        return Path(os.fspath(path))
    root = _root
    prov = provisional_root()
    if root is None or prov is None or not _within_budget(prov):
        _count_declined(store)
        return None
    target = prov / rel
    with _lock:
        manifest = _load_manifest(prov)
        entry = manifest["stores"].get(store)
        if not isinstance(entry, dict) or entry.get("mode") != mode:
            canon = _sha_of(root / store)
            # canon_sha: the canonical bytes home gave this device, which the
            # view grew from.  base_sha: the bytes the local copy must still be
            # for the view to be laid over it (equal until a restore).
            entry = {"mode": mode, "canon_sha": canon, "base_sha": canon,
                     "started_at": time.time(), "applied_bytes": 0}
        entry["last_at"] = time.time()
        entry["lived"] = _lived_mark()
        manifest["stores"][store] = entry
        try:
            _save_manifest(prov, manifest)
            target.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            _count_declined(store)
            return None
    _count_declined(store, "provisional")
    return target


def restore_provisional(state_dir: Any) -> Dict[str, Any]:
    """At a surface-only start, after home's growth is installed and BEFORE
    the gate is armed or any organ loads a store: lay her provisional view
    over each canonical copy that is still the copy it grew from.  A copy
    home has since replaced retires its view (home's integration of the same
    occurrences is the authority).  Returns a report; raises nothing."""
    import shutil
    root = Path(str(state_dir)).resolve()
    prov = root / PROVISIONAL_DIRNAME
    report: Dict[str, Any] = {"restored": [], "appended": [], "retired": [], "errors": []}
    if not prov.is_dir():
        return report
    with _lock:
        manifest = _load_manifest(prov)
        stores = manifest["stores"]
        for store in sorted(list(stores)):
            entry = stores[store] if isinstance(stores[store], dict) else {}
            src = prov / store
            dst = root / store
            try:
                if not src.is_file():
                    stores.pop(store, None)
                    continue
                current = _sha_of(dst)
                mode = entry.get("mode", SNAPSHOT)
                if mode == APPEND:
                    applied = int(entry.get("applied_bytes", 0) or 0)
                    if current == entry.get("base_sha"):
                        pass                                  # the copy it grew from: carry on
                    elif applied and current == entry.get("after_sha"):
                        pass                                  # our own earlier restore: add what is new
                    else:
                        report["retired"].append(store)
                        src.unlink(missing_ok=True)
                        stores.pop(store, None)
                        continue
                    if current == entry.get("base_sha"):
                        applied = 0
                    applied = min(applied, src.stat().st_size)   # a writer may have trimmed its view
                    with open(src, "rb") as handle:
                        handle.seek(applied)
                        tail = handle.read()
                    if tail:
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        with open(dst, "ab") as out:
                            out.write(tail)
                        report["appended"].append(store)
                    entry["applied_bytes"] = applied + len(tail)
                    entry["after_sha"] = _sha_of(dst)
                else:
                    if current != entry.get("base_sha"):
                        report["retired"].append(store)
                        src.unlink(missing_ok=True)
                        stores.pop(store, None)
                        continue
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    tmp = dst.with_name(dst.name + ".provisional.tmp")
                    shutil.copyfile(src, tmp)
                    os.replace(str(tmp), str(dst))
                    # From here the view grows from what was just laid down.
                    entry["base_sha"] = _sha_of(dst)
                    report["restored"].append(store)
                entry["restored_at"] = time.time()
                stores[store] = entry
            except OSError as exc:
                report["errors"].append(f"{store}: {exc}"[:200])
        try:
            _save_manifest(prov, manifest)
        except OSError as exc:
            report["errors"].append(f"manifest: {exc}"[:200])
    report["stores"] = len(manifest["stores"])
    return report


def provisional_canon_shas(state_dir: Any) -> Dict[str, str]:
    """Store -> the canonical sha each provisional view grew from.  Home's
    growth carrying exactly those bytes is not new to this device: installing
    it would only erase what she lived since, so home_growth skips it."""
    prov = Path(str(state_dir)).resolve() / PROVISIONAL_DIRNAME
    if not prov.is_dir():
        return {}
    stores = _load_manifest(prov)["stores"]
    return {k: str(v.get("canon_sha") or v.get("base_sha") or "")
            for k, v in stores.items() if isinstance(v, dict) and (prov / k).is_file()}


def provisional_status(state_dir: Any = None) -> Dict[str, Any]:
    prov = provisional_root(state_dir)
    if prov is None or not prov.is_dir():
        return {"stores": 0, "bytes": 0, "budget_bytes": PROVISIONAL_MAX_BYTES}
    manifest = _load_manifest(prov)
    return {"stores": len(manifest["stores"]), "bytes": _provisional_bytes(prov),
            "budget_bytes": PROVISIONAL_MAX_BYTES,
            "by_store": {k: {f: v.get(f) for f in ("mode", "last_at", "lived", "restored_at")}
                         for k, v in sorted(manifest["stores"].items()) if isinstance(v, dict)}}


def gate_status() -> Dict[str, Any]:
    with _lock:
        return {"surface_only": _root is not None,
                "stores_declined": sum(1 for e in _refused.values() if int(e.get("declined", 0))),
                "writes_declined": sum(int(e.get("declined", 0)) for e in _refused.values()),
                "stores_provisional": sum(1 for e in _refused.values() if int(e.get("provisional", 0))),
                "writes_provisional": sum(int(e.get("provisional", 0)) for e in _refused.values()),
                "by_store": {k: dict(v) for k, v in sorted(_refused.items())}}


def _write_status(now: float) -> None:
    """Keep the hub's view current without a write per declined store."""
    global _status_written_at
    root = _root
    if root is None or now - _status_written_at < _STATUS_EVERY_S:
        return
    _status_written_at = now
    try:
        path = root / _STATUS_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        prov = provisional_status()
        prov.pop("by_store", None)
        tmp.write_text(json.dumps({"at": now, **gate_status(), "provisional": prov}), encoding="utf-8")
        tmp.replace(path)
    except OSError:
        pass


def flush_status() -> None:
    global _status_written_at
    _status_written_at = 0.0
    _write_status(time.time())

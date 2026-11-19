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
  home_developmental  everything else.  On a surface-only device a write is
                    declined, counted per store and shown on the hub; it is
                    never a fault, because nothing failed.

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

# First match wins.  Paths are relative to the state directory, "/"-separated.
OWNERSHIP_TABLE: Tuple[Tuple[str, str], ...] = (
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
MOVES_WITH_HER: Tuple[str, ...] = ("surface_working_state.json", "habitat/*")

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
    per store, never raised and never recorded as a fault."""
    rel = _relative(path)
    if rel is None:
        return True
    store = _normalise(rel)
    if classify(store) != HOME_DEVELOPMENTAL:
        return True
    now = time.time()
    with _lock:
        entry = _refused.setdefault(store, {"declined": 0, "first_at": now, "last_at": now})
        entry["declined"] += 1
        entry["last_at"] = now
    _write_status(now)
    return False


def gate_status() -> Dict[str, Any]:
    with _lock:
        return {"surface_only": _root is not None,
                "stores_declined": len(_refused),
                "writes_declined": sum(int(e["declined"]) for e in _refused.values()),
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
        tmp.write_text(json.dumps({"at": now, **gate_status()}), encoding="utf-8")
        tmp.replace(path)
    except OSError:
        pass


def flush_status() -> None:
    global _status_written_at
    _status_written_at = 0.0
    _write_status(time.time())

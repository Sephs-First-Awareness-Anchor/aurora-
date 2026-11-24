#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
anticipatory_facets.py -- home's read of her own crystals, handed to her surface.

Her surface and her subsurface are one mind with one set of crystals.  The
surface starts from the crystals home had when it last started; home keeps
growing them (integrating what she lived, deep passes, corrections).  So
home can read, for what she has just heard, facets her surface does not hold
yet.  This module carries that read down.  It never carries a reply.

  * Home builds a VIEW when her raw input reaches it (strata_link's
    disposable raw_input feed), while its own live work is idle.  A view is
    the same bounded read the surface makes on every turn
    (aurora_live_experience.crystal_context_for_turn), on home's authoritative
    registry, and nothing else: no new crystal, facet kind, vote or store of
    knowledge.
  * Every view carries its own provenance: input_id, the words it was read
    for, the holder epoch, when it was read, when it stops being valid, and
    for each entry the facet address (concept, facet role, key) and the
    evidence class the entry already has on home's crystal:
        earned     -- supported by lived occasions (degree > 0)
        corrected  -- corrected away; history, not current knowledge
        hypothesis -- an uncertainty facet: a question she holds, not a claim
        simulated  -- read from a simulated occasion (dream / imagined)
  * The surface keeps the last few views in a small cache it owns
    (strata_link/facet_views.json, surface_present).  Nothing here writes a
    home-owned store, and a cached view is never learned from: it is read
    alongside her own facets on a turn, marked as home's view.
  * A view is used only while it is valid (unexpired, same holder epoch, and
    about the words she is hearing).  A stale or foreign view is ignored, never
    an error.  Reading it costs one small file read, cached by mtime: the
    turn is never held up waiting for home.

Nothing here decides what she says.  Her own expression decides; a home view
only lets her know what home already knows of the same crystals.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

__all__ = [
    "HOME_VIEWS_FILENAME", "SURFACE_VIEWS_FILENAME", "DOWN_CHANNEL",
    "VIEW_VALID_S", "MAX_VIEWS", "MAX_ENTRIES",
    "build_home_view", "stage_from_anticipatory_input", "relay_down",
    "receive_down", "valid_views_for", "merge_home_views", "view_status",
]

HOME_VIEWS_FILENAME = "facet_views_home.json"      # home side, what it has read
SURFACE_VIEWS_FILENAME = "facet_views.json"        # surface side, what reached her
DOWN_CHANNEL = "facet_view"
VIEW_VALID_S = 600.0                                # a follow-up turn, not a later day
MAX_VIEWS = 32
MAX_ENTRIES = 12

_TERM = re.compile(r"[a-z][a-z']{2,}")
_lock = threading.RLock()
_cache: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}


def _link(state_dir: Any) -> Path:
    return Path(str(state_dir)) / "strata_link"


def _terms(text: Any) -> List[str]:
    return sorted({w for w in _TERM.findall(str(text or "").lower())})


def _read(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".{uuid.uuid4().hex[:6]}.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=True, default=str), encoding="utf-8")
    os.replace(str(tmp), str(path))


def _evidence_class(entry: Mapping[str, Any]) -> str:
    occasions = list(entry.get("occasions") or [])

    def _simulated(occ: Any) -> bool:
        fields = occ if isinstance(occ, Mapping) else {"source": occ}
        said = " ".join(str(fields.get(k) or "") for k in ("source", "basis", "occurrence_class")).lower()
        return any(word in said for word in ("dream", "simulat", "imagin"))

    if occasions and all(_simulated(o) for o in occasions):
        return "simulated"
    if str(entry.get("kind") or "") == "uncertainty":
        return "hypothesis"
    if float(entry.get("degree", 0) or 0) > 0:
        return "earned"
    return "corrected" if occasions else "hypothesis"


def _address(entry: Mapping[str, Any]) -> Tuple[str, str, str]:
    return (str(entry.get("concept") or ""), str(entry.get("facet_role") or ""),
            json.dumps(entry.get("key"), sort_keys=True, default=str))


def _holder_epoch(state_dir: Any) -> int:
    try:
        from aurora_internal.dual_strata.strata_link import current_epoch
        return int(current_epoch(state_dir))
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# Home side
# ---------------------------------------------------------------------------

def build_home_view(systems: Mapping[str, Any], text: str, *, input_id: str = "",
                    state_dir: Any = None, now: Optional[float] = None) -> Optional[Dict[str, Any]]:
    """Home's read of its own crystals for ``text``.  None when there is
    nothing to read (no known concept carries a qualified facet)."""
    # The same reader her live cognition uses; on home the profile is not the
    # surface, so this is home's own facets with no home view laid over them.
    from aurora_internal.aurora_live_experience import crystal_context_for_turn
    terms = _terms(text)
    if not terms:
        return None
    facets = list(crystal_context_for_turn(systems, text, max_entries=MAX_ENTRIES).get("facets") or [])
    if not facets:
        return None
    at = float(now if now is not None else time.time())
    entries = []
    for item in facets:
        entry = {k: item.get(k) for k in ("concept", "kind", "key", "content", "degree",
                                           "supported", "contexts", "occasions", "facet_role")}
        entry["occasions"] = list(entry.get("occasions") or [])[-6:]
        entry["evidence_class"] = _evidence_class(entry)
        entries.append(entry)
    sd = state_dir if state_dir is not None else (systems.get("state_dir") or "aurora_state")
    return {
        "view_id": uuid.uuid4().hex,
        "input_id": str(input_id or ""),
        "terms": terms[:64],
        "epoch": _holder_epoch(sd),
        "at": at,
        "expires_at": at + VIEW_VALID_S,
        "basis": "home_crystal_read",
        "entries": entries,
    }


def stage_from_anticipatory_input(systems: Dict[str, Any], state_dir: Any) -> Optional[Dict[str, Any]]:
    """Called from home's idle schedule.  Reads ``systems['_anticipatory_input']``
    (her raw input, as strata_link received it) once per input_id and keeps the
    view for the downlink.  Returns the view staged, or None."""
    raw = systems.get("_anticipatory_input") if isinstance(systems, dict) else None
    if not isinstance(raw, Mapping):
        return None
    input_id = str(raw.get("input_id") or "")
    if not input_id or systems.get("_facet_view_last_input") == input_id:
        return None
    systems["_facet_view_last_input"] = input_id
    view = build_home_view(systems, str(raw.get("text") or ""), input_id=input_id, state_dir=state_dir)
    if view is None:
        return None
    path = _link(state_dir) / HOME_VIEWS_FILENAME
    with _lock:
        data = _read(path)
        views = [v for v in (data.get("views") or []) if isinstance(v, dict)
                 and float(v.get("expires_at", 0) or 0) >= time.time()]
        views.append(view)
        _write(path, {"views": views[-MAX_VIEWS:]})
    return view


def relay_down(state_dir: Any, outbox: Any, memo: Dict[str, Any]) -> int:
    """Called by the link's downlink collector: each unexpired view not yet
    sent goes into the durable outbox for the active surface."""
    data = _read(_link(state_dir) / HOME_VIEWS_FILENAME)
    sent = [str(x) for x in (memo.get("facet_views_sent") or [])]
    queued = 0
    now = time.time()
    for view in data.get("views") or []:
        if not isinstance(view, dict):
            continue
        view_id = str(view.get("view_id") or "")
        if not view_id or view_id in sent or float(view.get("expires_at", 0) or 0) < now:
            continue
        outbox.append(DOWN_CHANNEL, "event", dict(view))
        sent.append(view_id)
        queued += 1
    memo["facet_views_sent"] = sent[-MAX_VIEWS * 4:]
    return queued


# ---------------------------------------------------------------------------
# Surface side
# ---------------------------------------------------------------------------

def receive_down(state_dir: Any, payload: Mapping[str, Any]) -> str:
    """Surface side: keep a home view in her own small cache."""
    view_id = str(payload.get("view_id") or "")
    if not view_id or not isinstance(payload.get("entries"), list):
        return "unknown_channel"
    path = _link(state_dir) / SURFACE_VIEWS_FILENAME
    now = time.time()
    with _lock:
        data = _read(path)
        views = [v for v in (data.get("views") or []) if isinstance(v, dict)
                 and float(v.get("expires_at", 0) or 0) >= now
                 and str(v.get("view_id") or "") != view_id]
        views.append({k: payload.get(k) for k in ("view_id", "input_id", "terms", "epoch", "at",
                                                   "expires_at", "basis", "entries")})
        _write(path, {"views": views[-MAX_VIEWS:], "received_at": now})
    return "applied"


def _surface_views(state_dir: Any) -> List[Dict[str, Any]]:
    path = _link(state_dir) / SURFACE_VIEWS_FILENAME
    key = str(path)
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return []
    with _lock:
        hit = _cache.get(key)
        if hit and hit[0] == mtime:
            return hit[1]
        views = [v for v in (_read(path).get("views") or []) if isinstance(v, dict)]
        _cache[key] = (mtime, views)
        return views


def valid_views_for(state_dir: Any, heard: str, *, now: Optional[float] = None) -> List[Dict[str, Any]]:
    """Views that may be read for ``heard``: unexpired, same holder epoch,
    and read for at least one of the words she is hearing."""
    terms = set(_terms(heard))
    if not terms:
        return []
    moment = float(now if now is not None else time.time())
    epoch = _holder_epoch(state_dir)
    out = []
    for view in _surface_views(state_dir):
        if float(view.get("expires_at", 0) or 0) < moment:
            continue
        if int(view.get("epoch", -1) or 0) != epoch:
            continue
        if terms & set(view.get("terms") or []):
            out.append(view)
    return out


def merge_home_views(local: List[Dict[str, Any]], views: List[Dict[str, Any]], heard: str, *,
                     max_entries: int) -> List[Dict[str, Any]]:
    """Her own facets first, unchanged in order.  A home entry at an address
    she does not hold is added, marked as home's view (read-only).  A home
    entry at an address she holds annotates hers with home's degree and
    evidence class; her own degree is never overwritten."""
    terms = set(_terms(heard))
    merged = list(local)
    seen = {_address(e): e for e in merged}
    added = 0
    for view in sorted(views, key=lambda v: float(v.get("at", 0) or 0), reverse=True):
        for entry in view.get("entries") or []:
            if not isinstance(entry, Mapping) or str(entry.get("concept") or "") not in terms:
                continue
            addr = _address(entry)
            provenance = {"view_id": view.get("view_id"), "epoch": view.get("epoch"),
                          "at": view.get("at"), "evidence_class": entry.get("evidence_class")}
            mine = seen.get(addr)
            if mine is not None:
                if mine.get("source") != "home_view" and "home_view" not in mine:
                    mine["home_view"] = {"degree": entry.get("degree"), **provenance}
                continue
            if added >= max_entries:
                continue
            item = {k: entry.get(k) for k in ("concept", "kind", "key", "content", "degree",
                                               "supported", "contexts", "occasions", "facet_role")}
            item["occasions"] = list(item.get("occasions") or [])
            item["source"] = "home_view"
            item["read_only"] = True
            item.update(provenance)
            merged.append(item)
            seen[addr] = item
            added += 1
    return merged


def view_status(state_dir: Any) -> Dict[str, Any]:
    now = time.time()
    home = _read(_link(state_dir) / HOME_VIEWS_FILENAME).get("views") or []
    surf = _surface_views(state_dir)
    return {"home_views": len(home),
            "surface_views": len(surf),
            "surface_views_valid": sum(1 for v in surf if float(v.get("expires_at", 0) or 0) >= now)}

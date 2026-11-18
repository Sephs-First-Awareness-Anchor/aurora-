"""Hidden recommendation inbox for Aurora post-run actions.

Designed so recommendations are generated at end of runs, then consumed by Aurora,
who chooses one action per recommendation:
- note
- discuss_with_user
- dismiss
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations
from aurora_internal.aurora_runtime_faults import record_exception_from_locals as _aurora_record_exception_from_locals

import hashlib
import json
import os
import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

INBOX_FILE = "aurora_recommendation_inbox.jsonl"
ACTIONS_FILE = "aurora_recommendation_actions.jsonl"
NOTES_FILE = "aurora_recommendation_notes.jsonl"
DISCUSS_COOLDOWN_SECONDS = 900.0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _append_jsonl(path: str, rec: Dict[str, Any]) -> None:
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=True, sort_keys=True) + "\n")


def _read_jsonl(path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    out: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception as _aurora_boundary_exc:
                _aurora_record_exception_from_locals(
                    locals(),
                    module=__name__,
                    operation="exception_handler:aurora_internal/aurora_recommendation_hub.py:50",
                    exc=_aurora_boundary_exc,
                    context={"function": "_read_jsonl", "handler_line": 50, "source_file": "aurora_internal/aurora_recommendation_hub.py"},
                )
                continue
            if isinstance(obj, dict):
                out.append(obj)
    return out


class _AppendOnlyTail:
    """Reads only the lines appended to a JSONL file since the last call.

    Phone load (2026-11-07): every turn re-parsed the whole inbox and actions
    logs (16.5k + 12.7k lines, growing forever -- 167k json.loads in four
    turns), so each turn cost more than the last.  Complete lines only are
    consumed; a file that shrank or was replaced is read again from the top
    (caller is told via the reset flag)."""

    def __init__(self, path: str) -> None:
        self.path = path
        self.offset = 0
        self.ino = None

    def read_new(self) -> Tuple[bool, List[Dict[str, Any]]]:
        try:
            st = os.stat(self.path)
        except OSError:
            reset = self.offset != 0
            self.offset, self.ino = 0, None
            return reset, []
        reset = False
        if self.ino is not None and (st.st_ino != self.ino or st.st_size < self.offset):
            reset = True
            self.offset = 0
        self.ino = st.st_ino
        if st.st_size == self.offset:
            return reset, []
        rows: List[Dict[str, Any]] = []
        with open(self.path, "rb") as fh:
            fh.seek(self.offset)
            chunk = fh.read()
        end = chunk.rfind(b"\n")
        if end < 0:
            return reset, []
        self.offset += end + 1
        for raw in chunk[: end + 1].splitlines():
            line = raw.decode("utf-8", errors="ignore").strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
        return reset, rows


class _HubIndex:
    """Incremental equivalent of _action_index / pending_recommendations /
    _recent_discuss_block over the append-only inbox and actions logs."""

    def __init__(self, paths: Dict[str, str]) -> None:
        self.inbox = _AppendOnlyTail(paths["inbox"])
        self.actions = _AppendOnlyTail(paths["actions"])
        self.acted: set = set()
        self.pending: List[Tuple[str, Dict[str, Any]]] = []   # inbox order, duplicates kept
        self.last_discuss_at = 0.0
        self.lock = threading.Lock()

    def refresh(self) -> None:
        reset_a, new_actions = self.actions.read_new()
        reset_i, new_inbox = self.inbox.read_new()
        if reset_a or reset_i:
            self.inbox.offset = self.actions.offset = 0
            self.inbox.ino = self.actions.ino = None
            self.acted, self.pending, self.last_discuss_at = set(), [], 0.0
            _, new_actions = self.actions.read_new()
            _, new_inbox = self.inbox.read_new()
        newly_acted = set()
        for row in new_actions:
            rid = str(row.get("id") or "")
            if rid:
                newly_acted.add(rid)
            if str(row.get("action") or "") == "discuss_with_user":
                decided_at = _parse_iso_epoch(row.get("decided_at"))
                if decided_at > 0.0:
                    self.last_discuss_at = decided_at
        if newly_acted:
            self.acted |= newly_acted
            self.pending = [(rid, rec) for rid, rec in self.pending if rid not in newly_acted]
        for rec in new_inbox:
            rid = str(rec.get("id") or "")
            if rid and rid not in self.acted:
                self.pending.append((rid, rec))


_HUB_INDEXES: Dict[str, _HubIndex] = {}
_HUB_INDEXES_LOCK = threading.Lock()


def _hub_index(output_dir: str) -> _HubIndex:
    p = _paths(output_dir)
    key = p["inbox"]
    with _HUB_INDEXES_LOCK:
        index = _HUB_INDEXES.get(key)
        if index is None:
            index = _HUB_INDEXES[key] = _HubIndex(p)
    return index


def _paths(output_dir: str) -> Dict[str, str]:
    od = os.path.abspath(output_dir or "aurora_runtime_output")
    _ensure_dir(od)
    return {
        "inbox": os.path.join(od, INBOX_FILE),
        "actions": os.path.join(od, ACTIONS_FILE),
        "notes": os.path.join(od, NOTES_FILE),
    }


def enqueue_recommendation(
    output_dir: str,
    source: str,
    run_type: str,
    title: str,
    body: str,
    priority: float = 0.5,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    p = _paths(output_dir)
    payload = {
        "source": str(source),
        "run_type": str(run_type),
        "title": str(title),
        "body": str(body),
        "priority": float(max(0.0, min(1.0, float(priority)))),
        "context": dict(context or {}),
        "actions": ["note", "discuss_with_user", "dismiss"],
        "created_at": _now_iso(),
    }
    seed = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    rid = hashlib.sha1(seed.encode("utf-8", errors="ignore")).hexdigest()[:16]
    rec = {"id": rid, **payload}
    _append_jsonl(p["inbox"], rec)
    return rec


def _action_index(output_dir: str) -> Dict[str, Dict[str, Any]]:
    p = _paths(output_dir)
    idx: Dict[str, Dict[str, Any]] = {}
    for a in _read_jsonl(p["actions"]):
        rid = str(a.get("id") or "")
        if rid:
            idx[rid] = a
    return idx


def pending_recommendations(output_dir: str, limit: int = 10) -> List[Dict[str, Any]]:
    index = _hub_index(output_dir)
    with index.lock:
        index.refresh()
        pending: List[Dict[str, Any]] = [dict(rec) for _, rec in index.pending]
    pending.sort(key=lambda r: (-(float(r.get("priority", 0.0) or 0.0)), str(r.get("created_at", ""))))
    return pending[: max(1, int(limit))]


def choose_action(rec: Dict[str, Any]) -> str:
    pri = float(rec.get("priority", 0.0) or 0.0)
    run_type = str(rec.get("run_type", ""))

    # Aurora policy: only interrupt user when high-priority and evolution-relevant.
    if pri >= 0.78:
        return "discuss_with_user"
    if pri >= 0.35:
        return "note"
    if run_type in ("lineage_scan", "chain_burst") and pri >= 0.28:
        return "note"
    return "dismiss"


def _parse_iso_epoch(value: Any) -> float:
    try:
        txt = str(value or "").strip()
        if not txt:
            return 0.0
        return datetime.fromisoformat(txt).timestamp()
    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(),
            module=__name__,
            operation="exception_handler:aurora_internal/aurora_recommendation_hub.py:137",
            exc=_aurora_boundary_exc,
            context={"function": "_parse_iso_epoch", "handler_line": 137, "source_file": "aurora_internal/aurora_recommendation_hub.py"},
        )
        return 0.0


def _recent_discuss_block(output_dir: str, cooldown_seconds: float) -> bool:
    p = _paths(output_dir)
    now = time.time()
    cooldown = float(max(0.0, cooldown_seconds))
    if cooldown <= 0.0:
        return False
    index = _hub_index(output_dir)
    with index.lock:
        index.refresh()
        decided_at = index.last_discuss_at
    if decided_at <= 0.0:
        return False
    return (now - decided_at) < cooldown


def act_recommendation(
    output_dir: str,
    rec: Dict[str, Any],
    action: str,
    rationale: str = "",
    note_text: str = "",
) -> Dict[str, Any]:
    p = _paths(output_dir)
    action = str(action)
    if action not in ("note", "discuss_with_user", "dismiss"):
        action = "dismiss"

    out = {
        "id": str(rec.get("id") or ""),
        "action": action,
        "rationale": str(rationale or ""),
        "decided_at": _now_iso(),
    }
    _append_jsonl(p["actions"], out)

    if action == "note":
        note = {
            "id": out["id"],
            "noted_at": out["decided_at"],
            "title": str(rec.get("title", "")),
            "body": str(note_text or rec.get("body", "")),
            "source": str(rec.get("source", "")),
            "run_type": str(rec.get("run_type", "")),
        }
        _append_jsonl(p["notes"], note)

    return out


# Settle and release (Sunni, 2026-11-08: "those reads should only effect
# change or inspire variation and reconsideration ... to retain [them]
# permanently seems like a handicap").  A recommendation is read, and either
# changes something (note / discuss) or does not (dismiss).  Once decided it
# has done its work: it is released from the hot logs instead of being kept
# and re-read forever.  One that waits STALE_AFTER_S without ever rising to
# her attention is settled as aged out -- a decision, logged like any other.
STALE_AFTER_S = 7 * 24 * 3600.0
SETTLE_EVERY_S = 6 * 3600.0
_LAST_SETTLE: Dict[str, float] = {}


def _atomic_write_lines(path: str, rows: List[Dict[str, Any]]) -> None:
    tmp = path + ".settle.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")
    os.replace(tmp, path)


def settle_recommendations(output_dir: str, *, now: Optional[float] = None,
                           force: bool = False) -> Dict[str, int]:
    """Age out stale pending items, then release decided ones from the logs."""
    now = time.time() if now is None else float(now)
    p = _paths(output_dir)
    if not force and now - _LAST_SETTLE.get(p["inbox"], 0.0) < SETTLE_EVERY_S:
        return {"aged_out": 0, "released": 0}
    _LAST_SETTLE[p["inbox"]] = now
    index = _hub_index(output_dir)
    with index.lock:
        index.refresh()
        stale = [rec for _, rec in index.pending
                 if 0.0 < _parse_iso_epoch(rec.get("created_at")) < now - STALE_AFTER_S]
    for rec in stale:
        act_recommendation(output_dir, rec, action="dismiss",
                           rationale="aged_out: never rose to her attention")
    released = 0
    with index.lock:
        index.refresh()
        inbox = _read_jsonl(p["inbox"])
        if len(inbox) > 2 * max(1, len(index.pending)):
            keep_ids = {rid for rid, _ in index.pending}
            actions = _read_jsonl(p["actions"])
            last_discuss = None
            for row in actions:
                if (str(row.get("action") or "") == "discuss_with_user"
                        and _parse_iso_epoch(row.get("decided_at")) > 0.0):
                    last_discuss = row
            kept_inbox = [r for r in inbox if str(r.get("id") or "") in keep_ids]
            kept_actions = [r for r in actions if str(r.get("id") or "") in keep_ids]
            if last_discuss is not None and last_discuss not in kept_actions:
                kept_actions.append(last_discuss)
            # Inbox first: if interrupted between the two writes, the extra
            # action rows are harmless; the other order would resurrect
            # already-decided items as pending.
            _atomic_write_lines(p["inbox"], kept_inbox)
            _atomic_write_lines(p["actions"], kept_actions)
            released = len(inbox) - len(kept_inbox)
            index.refresh()
    return {"aged_out": len(stale), "released": released}


def process_pending_for_aurora(
    output_dir: str,
    discuss_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    max_items: int = 3,
    cooldown_seconds: float = DISCUSS_COOLDOWN_SECONDS,
) -> List[Dict[str, Any]]:
    done: List[Dict[str, Any]] = []
    try:
        settle_recommendations(output_dir)
    except Exception:
        pass
    discuss_blocked = _recent_discuss_block(output_dir, cooldown_seconds)
    for rec in pending_recommendations(output_dir, limit=max_items):
        action = choose_action(rec)
        rationale = f"priority={float(rec.get('priority', 0.0) or 0.0):.2f}"
        if action == "discuss_with_user" and discuss_blocked:
            action = "note"
            rationale += "; discuss_cooldown_applied"
        result = act_recommendation(output_dir, rec, action=action, rationale=rationale)
        done.append(result)

        if action == "discuss_with_user":
            discuss_blocked = True

        if action == "discuss_with_user" and discuss_callback is not None:
            title = str(rec.get("title", "Recommendation"))
            body = str(rec.get("body", ""))
            msg = f"{title}: {body}"
            try:
                discuss_callback(msg, rec)
            except Exception as _aurora_boundary_exc:
                _aurora_record_exception_from_locals(
                    locals(),
                    module=__name__,
                    operation="exception_handler:aurora_internal/aurora_recommendation_hub.py:217",
                    exc=_aurora_boundary_exc,
                    context={"function": "process_pending_for_aurora", "handler_line": 217, "source_file": "aurora_internal/aurora_recommendation_hub.py"},
                )
                pass
    return done

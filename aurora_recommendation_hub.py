"""Hidden recommendation inbox for Aurora post-run actions.

Designed so recommendations are generated at end of runs, then consumed by Aurora,
who chooses one action per recommendation:
- note
- discuss_with_user
- dismiss
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo

from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

INBOX_FILE = "aurora_recommendation_inbox.jsonl"
ACTIONS_FILE = "aurora_recommendation_actions.jsonl"
NOTES_FILE = "aurora_recommendation_notes.jsonl"
DISCUSS_COOLDOWN_SECONDS = 900.0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


_MAX_ENTRIES_PER_FILE = 200
_MAX_FILE_BYTES       = 512 * 1024  # 512 KB


def _append_jsonl(path: str, rec: Dict[str, Any]) -> None:
    """Append a JSON record to a JSONL file, capping at MAX_ENTRIES_PER_FILE entries."""
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=True, sort_keys=True) + "\n")
    # Trim to last MAX_ENTRIES_PER_FILE entries if file exceeds size cap
    try:
        if os.path.getsize(path) > _MAX_FILE_BYTES:
            with open(path, "r", encoding="utf-8", errors="ignore") as _rf:
                _lines = [ln for ln in _rf.readlines() if ln.strip()]
            if len(_lines) > _MAX_ENTRIES_PER_FILE:
                with open(path, "w", encoding="utf-8") as _wf:
                    _wf.writelines(_lines[-_MAX_ENTRIES_PER_FILE:])
    except Exception:
        pass


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
            except Exception:
                continue
            if isinstance(obj, dict):
                out.append(obj)
    return out


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
    p = _paths(output_dir)
    acted = _action_index(output_dir)
    pending: List[Dict[str, Any]] = []
    for rec in _read_jsonl(p["inbox"]):
        rid = str(rec.get("id") or "")
        if not rid or rid in acted:
            continue
        pending.append(rec)
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
    except Exception:
        return 0.0


def _recent_discuss_block(output_dir: str, cooldown_seconds: float) -> bool:
    p = _paths(output_dir)
    now = time.time()
    cooldown = float(max(0.0, cooldown_seconds))
    if cooldown <= 0.0:
        return False
    for row in reversed(_read_jsonl(p["actions"])):
        if str(row.get("action") or "") != "discuss_with_user":
            continue
        decided_at = _parse_iso_epoch(row.get("decided_at"))
        if decided_at <= 0.0:
            continue
        return (now - decided_at) < cooldown
    return False


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


def process_pending_for_aurora(
    output_dir: str,
    discuss_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    max_items: int = 3,
    cooldown_seconds: float = DISCUSS_COOLDOWN_SECONDS,
) -> List[Dict[str, Any]]:
    done: List[Dict[str, Any]] = []
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
            except Exception:
                pass
    return done

#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
hub_route.py -- the desktop hub speaks to her where she is (surface
restructure 2 and 3c: route hub chat to the device that holds her; Sir's Move
button).

One mind, one place at a time.  When a phone holds her, a message typed at the
desktop hub must reach HER, on the phone, not the desktop's own surface daemon
standing by under the admission fence (that would be a second voice).

The path:
  hub (desktop, separate process)  --file_hub_request-->  home_requests.jsonl
  desktop resident                 --send_to_holder---->  down outbox "hub_message"
  holder (phone)                   --receive_message--->  strata_link/hub_messages.jsonl
  phone bridge                     handles it as a turn; her reply goes up "hub_reply"
  home                             --record_reply------>  strata_link/hub_replies.json
  hub                              reads its reply by message id

The hub's own requests never cross the network: a phone cannot file one,
because only HOME_REQUEST_KINDS are accepted from an uplink and these kinds are
not among them.  Nothing here writes words for her or decides whether she
answers; it carries Sir's words to her and hers back.

Standard library only, so the Tk hub can import it without loading her stack.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

LINK_DIRNAME = "strata_link"
HOME_REQUESTS_FILENAME = "home_requests.jsonl"     # the same file strata_link reads
HUB_REQUEST_KINDS = ("hub_move", "hub_message")
MESSAGES_FILENAME = "hub_messages.jsonl"           # on the holder
ANSWERED_FILENAME = "hub_messages_answered.json"   # on the holder
REPLIES_FILENAME = "hub_replies.json"              # at home
KEEP_REPLIES = 50
MAX_TEXT = 4000


def _link(state_dir: Any) -> Path:
    path = Path(str(state_dir)) / LINK_DIRNAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _write_json(path: Path, payload: Any) -> None:
    tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(payload, indent=1, sort_keys=True), encoding="utf-8")
    os.replace(str(tmp), str(path))


# -- the hub (desktop) -----------------------------------------------------------

def holder(state_dir: Any) -> Dict[str, Any]:
    """Who holds her now, as home's link records it.  Names only, no secrets."""
    link = Path(str(state_dir)) / LINK_DIRNAME
    srv = _read_json(link / "server_state.json", {})
    srv = srv if isinstance(srv, dict) else {}
    try:
        home_id = (link / "home_surface_id.txt").read_text(encoding="utf-8").strip()
    except OSError:
        home_id = ""
    owner = str(srv.get("owner") or "")
    names = dict(srv.get("names") or {})
    return {"owner": owner, "home_surface_id": home_id,
            "name": str(names.get(owner) or ("this desktop" if owner and owner == home_id else owner)),
            "elsewhere": bool(owner and home_id and owner != home_id),
            "epoch": int(srv.get("epoch") or 0)}


def file_hub_request(state_dir: Any, kind: str, payload: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """Hub side: hand a request to the desktop resident, on this machine."""
    if kind not in HUB_REQUEST_KINDS:
        return {"ok": False, "error": f"unknown_request: {kind}"}
    request_id = uuid.uuid4().hex
    line = {"request_id": request_id, "kind": kind, "payload": dict(payload or {}),
            "at": time.time(), "from": "hub"}
    with open(_link(state_dir) / HOME_REQUESTS_FILENAME, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(line, sort_keys=True) + "\n")
    return {"ok": True, "request_id": request_id}


def send_hub_message(state_dir: Any, text: str) -> Dict[str, Any]:
    message_id = uuid.uuid4().hex[:20]
    filed = file_hub_request(state_dir, "hub_message",
                             {"message_id": message_id, "text": str(text or "")[:MAX_TEXT]})
    return {**filed, "message_id": message_id}


def read_reply(state_dir: Any, message_id: str) -> Optional[Dict[str, Any]]:
    data = _read_json(Path(str(state_dir)) / LINK_DIRNAME / REPLIES_FILENAME, {})
    row = (data or {}).get(str(message_id)) if isinstance(data, dict) else None
    return row if isinstance(row, dict) else None


# -- home (the desktop resident and the link server) -----------------------------

def record_reply(state_dir: Any, message_id: str, row: Mapping[str, Any]) -> None:
    path = _link(state_dir) / REPLIES_FILENAME
    data = _read_json(path, {})
    data = data if isinstance(data, dict) else {}
    merged = dict(data.get(str(message_id)) or {})
    merged.update(dict(row))
    data[str(message_id)] = merged
    if len(data) > KEEP_REPLIES:
        for key in sorted(data, key=lambda k: float((data[k] or {}).get("at", 0.0) or 0.0))[:-KEEP_REPLIES]:
            data.pop(key, None)
    _write_json(path, data)


def send_to_holder(server: Any, payload: Mapping[str, Any]) -> Dict[str, Any]:
    """Desktop resident: carry Sir's message down to the device that holds
    her.  ``server`` is the running StrataLinkServer."""
    message_id = str(payload.get("message_id") or "")[:40]
    text = str(payload.get("text") or "")[:MAX_TEXT]
    if not message_id or not text:
        return {"ok": False, "error": "message_id_and_text_required"}
    state = server._load_state()
    owner = str(state.get("owner") or "")
    if not owner or owner == server.home_surface_id:
        result = {"ok": False, "error": "she_is_here", "status": "not_sent"}
    elif not server.downlink_enabled():
        result = {"ok": False, "error": "home_not_yet_holding_her", "status": "not_sent"}
    else:
        server.outbox.append("hub_message", "event",
                             {"message_id": message_id, "text": text, "to": owner, "at": time.time()},
                             dedupe_id=f"hub:{message_id}")
        result = {"ok": True, "status": "sent", "to": owner,
                  "to_name": str((state.get("names") or {}).get(owner) or owner)}
    record_reply(server.state_dir, message_id, {"at": time.time(), **result})
    return result


# -- the holder (phone) -----------------------------------------------------------

def receive_message(state_dir: Any, payload: Mapping[str, Any], surface_id: str) -> str:
    """Downlink: keep a message from the desk for this device's bridge."""
    message_id = str(payload.get("message_id") or "")
    if not message_id or str(payload.get("to") or "") not in ("", str(surface_id)):
        return "applied"          # not for this device; nothing to keep
    path = _link(state_dir) / MESSAGES_FILENAME
    if path.exists() and f'"message_id": "{message_id}"' in path.read_text(encoding="utf-8")[-200000:]:
        return "applied"
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps({"message_id": message_id, "text": str(payload.get("text") or "")[:MAX_TEXT],
                                 "at": float(payload.get("at") or time.time())}, sort_keys=True) + "\n")
    return "applied"


def pending_messages(state_dir: Any) -> List[Dict[str, Any]]:
    link = Path(str(state_dir)) / LINK_DIRNAME
    answered = set(_read_json(link / ANSWERED_FILENAME, []) or [])
    out: List[Dict[str, Any]] = []
    try:
        lines = (link / MESSAGES_FILENAME).read_text(encoding="utf-8").splitlines()
    except OSError:
        return out
    for raw in lines:
        try:
            item = json.loads(raw) if raw.strip() else None
        except ValueError:
            item = None
        if isinstance(item, dict) and item.get("message_id") not in answered:
            out.append(item)
    return out


def mark_answered(state_dir: Any, message_id: str) -> None:
    path = _link(state_dir) / ANSWERED_FILENAME
    done = [m for m in (_read_json(path, []) or []) if isinstance(m, str)]
    if message_id not in done:
        done.append(str(message_id))
    _write_json(path, done[-400:])


def answer_pending(state_dir: Any, respond: Any, outbox: Any) -> int:
    """The holder's bridge: each message from the desk is a turn she lives
    here; whatever she says (or that she said nothing) goes home with it."""
    answered = 0
    for item in pending_messages(state_dir):
        message_id = str(item["message_id"])
        try:
            reply = respond(str(item.get("text") or ""))
            row = {"message_id": message_id, "text": str(reply or "")[:MAX_TEXT], "at": time.time(),
                   "status": "answered"}
        except Exception as exc:
            row = {"message_id": message_id, "text": "", "at": time.time(),
                   "status": "error", "error": f"{type(exc).__name__}: {exc}"[:200]}
        outbox.append("hub_reply", "event", row, dedupe_id=f"hub_reply:{message_id}")
        mark_answered(state_dir, message_id)
        answered += 1
    return answered

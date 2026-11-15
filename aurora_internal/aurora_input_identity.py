# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Which input a piece of measured pressure answers (Sir, 2026-11-14: impact is tied to the received input).

Genealogy's observe() notes carried no turn or input identity, so measured relief could not be attributed to the input
that caused it.  This module holds the identity of the input currently being processed, in a ContextVar, and gives
genealogy one small dict to merge into the notes of every observation made while it is set.

  * It RECORDS identity only.  Nothing here changes any measurement, gate, threshold or decision.
  * The identity is an evidence-contract event (`evidence_qualification`): occurrence from how the speech was addressed
    (`direct` is `heard`; `mention`/`ambient` are `overheard`, never testimony), `input_pressure` as the intake
    measured it (None stays unknown).  Consequences measured later attribute to `event["id"]`.
  * A ContextVar does not cross into threads started by the turn, so observations made on a background thread carry no
    identity.  That is reported as unattributed, never guessed to belong to the turn.
"""
from __future__ import annotations

import contextvars
import hashlib
import time
from typing import Any, Dict, Mapping, Optional

from aurora_internal import evidence_qualification as _Q

_CURRENT: contextvars.ContextVar = contextvars.ContextVar("aurora_current_input", default=None)


def make_input_event(turn_id: str, text: str, *, address: str = "direct", stream_type: str = "user_input",
                     loads: Optional[Mapping[str, float]] = None, t: Optional[int] = None, by: str = "") -> Dict[str, Any]:
    """The evidence event for one received input.  Its subject names the turn, not a proposition: propositions drawn from
    the input cite this event in their ancestry; consequences measured because of it attribute to its id."""
    occ = _Q.occurrence_of_address(address, stream_type) or "heard"
    digest = hashlib.blake2b(str(text or "").encode("utf-8"), digest_size=8).hexdigest()
    kw: Dict[str, Any] = {}
    if loads:
        kw["input_pressure"] = {a: float(loads.get(a, 0.0) or 0.0) for a in _Q.AXES}
    return _Q.make_event(f"input|{turn_id}|-", occurrence=occ, t=int(time.time() if t is None else t),
                         nonce=digest, by=by, **kw)


def begin_input(turn_id: str, text: str, **kw: Any) -> contextvars.Token:
    ev = make_input_event(turn_id, text, **kw)
    note = {"input_event": ev["id"], "input_occurrence": ev["occurrence"], "turn_id": str(turn_id)}
    if ev.get("input_pressure"):
        note["input_pressure"] = dict(ev["input_pressure"])
    return _CURRENT.set({"event": ev, "note": note})


def end_input(token: contextvars.Token) -> None:
    try:
        _CURRENT.reset(token)
    except ValueError:                       # reset from another context: leave the var as it is rather than guess
        pass


def current_event() -> Optional[Dict[str, Any]]:
    cur = _CURRENT.get()
    return dict(cur["event"]) if cur else None


def note_for_observe() -> Dict[str, Any]:
    """What genealogy merges into an observation's notes; empty when no input is being processed."""
    cur = _CURRENT.get()
    return dict(cur["note"]) if cur else {}

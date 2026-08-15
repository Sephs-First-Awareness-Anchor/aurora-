#!/usr/bin/env python3
"""
aurora_scout_daemon.py

Lightweight, disposable Evidence Scout worker (Subsurface Presence and
Evidence Scout spec, section 9). Deliberately the smallest possible
process: request -> retrieve -> normalize evidence -> report, nothing
else.

Explicitly does NOT call boot_aurora() and does NOT import aurora.py or
aurora_daemon.py. Both pull in genealogy, Dream, the consciousness
engine, SediMemory, DCE, CERS, working memory, sensory systems, and
Aurora's identity state as part of their own module-level/boot-time
setup -- importing either module at all would already violate this
worker's "no full Aurora instance" contract, even without ever calling
boot_aurora() itself. Given the captured runtime's survival-mode memory
pressure (spec section 9), that import cost alone is the thing to
avoid, not just the boot call.

Talks to the existing aurora_room.py Poedex responder via the same
per-request-file protocol _poedex_ask() (aurora_daemon.py) already
uses -- reimplemented minimally here rather than imported, specifically
to avoid dragging in that module's heavy import graph. When Room isn't
running, this worker reports "no_evidence" honestly rather than
reproducing Room's own headless web-lookup logic in a second lightweight
copy -- that would be real scope creep for this first implementation
pass (spec section 22: "do not combine this first implementation with
unrelated architectural rewrites").

Aurora Build 694, step 6: state_dir is threaded explicitly through
every function in this file (run() -> _retrieve_and_normalize() ->
_poedex_ask_lightweight() -> ScoutBroker), rather than any of them
reading the module-level _STATE_DIR constant directly. That constant
now exists ONLY as run()'s default when no caller supplies one (desktop
usage: `python3 aurora_scout_daemon.py` with no arguments). Android's
writable application state directory is not the repository's default
aurora_state path -- a worker that silently fell back to the module-
relative default would read/write ScoutRequests and results in the
wrong place entirely on that platform.

The Scout is a courier, not cortex (spec section 4): it sends Aurora's
own interpreted framing of the gap as context, never asks the external
source to reinterpret the raw user utterance, and never drafts a
response -- ScoutReport (contracts.py) has no field that could hold one.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Optional

_BASE_DIR = Path(__file__).parent
_STATE_DIR = _BASE_DIR / "aurora_state"

sys.path.insert(0, str(_BASE_DIR))

from aurora_internal.scouting.broker import ScoutBroker
from aurora_internal.scouting.contracts import ScoutRequest, ScoutReport


def _room_responder_available() -> bool:
    """Same check _poedex_room_responder_available() (aurora_daemon.py)
    performs -- duplicated rather than imported, for the same reason as
    the rest of this file."""
    try:
        proc = subprocess.run(
            ["pgrep", "-f", "aurora_room.py"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1.0,
        )
        return proc.returncode == 0
    except Exception:
        return False


def _poedex_ask_lightweight(
    question: str, *, state_dir: Any, cat: str = "researcher", lane: str = "self", timeout: float = 20.0,
) -> str:
    """Minimal client-side reimplementation of _poedex_ask()'s
    per-request-file protocol against aurora_room.py's existing queue.
    This worker running its own blocking poll loop here is fine --
    unlike a call from inside Surface/Subsurface, nothing outside THIS
    already-isolated process is waiting on it."""
    state_dir = Path(state_dir)
    queue_dir = state_dir / "poedex_queue"
    result_dir = state_dir / "poedex_results"
    queue_dir.mkdir(parents=True, exist_ok=True)
    result_dir.mkdir(parents=True, exist_ok=True)

    qid = f"scout_{time.time():.4f}_{os.getpid()}"
    query_path = queue_dir / f"{qid}.json"
    result_path = result_dir / f"{qid}.json"

    try:
        query_path.write_text(json.dumps({
            "id": qid, "question": question, "cat": cat, "lane": lane,
            "status": "pending", "submitted": time.time(),
        }, indent=2), encoding="utf-8")
    except Exception:
        return ""

    deadline = time.time() + max(1.0, float(timeout))
    while time.time() < deadline:
        time.sleep(0.4)
        if result_path.exists():
            try:
                r = json.loads(result_path.read_text(encoding="utf-8"))
                if r.get("id") == qid and r.get("status") == "done":
                    result = str(r.get("result", "") or "")
                    result_path.unlink(missing_ok=True)
                    return result
            except Exception:
                pass

    try:
        query_path.unlink(missing_ok=True)
    except Exception:
        pass
    return ""


def _retrieve_and_normalize(request: ScoutRequest, *, state_dir: Any) -> ScoutReport:
    """request -> retrieve -> normalize evidence -> report. The whole
    job of this worker, in one function so it's independently testable
    without the claim/submit loop around it."""
    started = time.time()

    if not str(request.inquiry or "").strip():
        return ScoutReport(
            request_id=request.request_id, turn_id=request.turn_id,
            request_kind=request.request_kind,
            status="no_evidence",
            elapsed_ms=(time.time() - started) * 1000.0,
        )

    if not _room_responder_available():
        return ScoutReport(
            request_id=request.request_id, turn_id=request.turn_id,
            request_kind=request.request_kind,
            status="no_evidence",
            fit_rationales=["Poedex Room responder is not running -- no external evidence source available"],
            elapsed_ms=(time.time() - started) * 1000.0,
        )

    question = request.inquiry
    if request.interpreted_input:
        question = f"{request.inquiry} (context: Aurora already interprets the input as: {request.interpreted_input})"

    remaining = request.deadline - time.time()
    raw_result = _poedex_ask_lightweight(
        question, state_dir=state_dir, cat="researcher", lane="self",
        timeout=max(5.0, min(45.0, remaining)),
    )
    elapsed_ms = (time.time() - started) * 1000.0

    if not raw_result:
        return ScoutReport(
            request_id=request.request_id, turn_id=request.turn_id,
            request_kind=request.request_kind,
            status="no_evidence", elapsed_ms=elapsed_ms,
        )

    text = raw_result[: max(1, int(request.max_result_chars or 1200))]
    evidence_items = [{"text": text, "source": "poedex_researcher"}]

    # Deliberately conservative: "explain" is the least presumptive
    # relationship category a Scout can report when it can't confidently
    # characterize a more specific one -- it never guesses at
    # something like "answer_directly" just because evidence came back.
    return ScoutReport(
        request_id=request.request_id,
        turn_id=request.turn_id,
        request_kind=request.request_kind,
        status="ok",
        evidence_items=evidence_items[: int(request.max_evidence_items or 5)],
        response_relationships=["explain"],
        fit_rationales=["external evidence retrieved and available to inform, not dictate, the response"],
        provenance=["poedex_researcher"],
        confidence=0.55,
        elapsed_ms=elapsed_ms,
    )


def run(
    *,
    state_dir: Optional[Any] = None,
    poll_interval_s: float = 1.0,
    max_iterations: Optional[int] = None,
) -> None:
    """The worker's whole life: claim one request at a time (broker
    enforces concurrency=1 by default), process it, submit a report,
    repeat. max_iterations is test-only -- production callers never
    pass it, so the loop runs forever.

    state_dir defaults to the module's repo-relative _STATE_DIR only
    when the caller supplies nothing at all -- desktop's `python3
    aurora_scout_daemon.py` with no arguments. Android's caller always
    passes its own writable application state directory explicitly
    (spec step 8)."""
    active_state_dir = Path(state_dir) if state_dir is not None else _STATE_DIR
    broker = ScoutBroker(active_state_dir)
    print(
        f"[SCOUT] worker online, pid={os.getpid()}, concurrency={broker.max_concurrent}, "
        f"state_dir={active_state_dir}", flush=True,
    )

    iterations = 0
    while max_iterations is None or iterations < max_iterations:
        iterations += 1
        broker.expire_stale_requests()
        request = broker.claim_next()
        if request is None:
            time.sleep(poll_interval_s)
            continue
        try:
            report = _retrieve_and_normalize(request, state_dir=active_state_dir)
        except Exception as exc:
            report = ScoutReport(
                request_id=request.request_id, turn_id=request.turn_id,
                request_kind=request.request_kind,
                status="failed", fit_rationales=[f"scout worker error: {exc}"],
            )
        broker.submit_report(report)


def _parse_cli_state_dir() -> Optional[str]:
    """`python3 aurora_scout_daemon.py --state-dir=/path/to/state` --
    optional; omitted entirely falls back to run()'s own default."""
    for arg in sys.argv[1:]:
        if arg.startswith("--state-dir="):
            return arg.split("=", 1)[1]
    return None


if __name__ == "__main__":
    run(state_dir=_parse_cli_state_dir())

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

Aurora Build 694, step 6: state_dir is threaded explicitly through
every function in this file (run() -> _retrieve_and_normalize() ->
ScoutBroker/backends), rather than any of them reading the module-level
_STATE_DIR constant directly. That constant now exists ONLY as run()'s
default when no caller supplies one (desktop usage: `python3
aurora_scout_daemon.py` with no arguments). Android's writable
application state directory is not the repository's default
aurora_state path -- a worker that silently fell back to the module-
relative default would read/write ScoutRequests and results in the
wrong place entirely on that platform.

Aurora Build 694, step 7: retrieval itself now goes through
aurora_internal.scouting.backends.ScoutBackend -- this worker used to
have exactly one retrieval path hardcoded in (check whether
aurora_room.py is running via `pgrep`, then talk to its Poedex queue),
which made it structurally unusable on Android (no pgrep target ever
exists there). _retrieve_and_normalize() now tries each available
backend in a caller-configurable chain (default:
[PoedexRoomBackend, LocalLessonsBackend] -- resolve_backend_chain()),
using the first one that produces evidence. Both default backends work
with zero external configuration, which is what makes Android capable
out of the box: PoedexRoomBackend.is_available() just reports False
there, and LocalLessonsBackend (Aurora's own persisted bound-lesson
corpus, poedex_lessons.json) never depended on a Room process at all.

The Scout is a courier, not cortex (spec section 4): it sends Aurora's
own interpreted framing of the gap as context, never asks the external
source to reinterpret the raw user utterance, and never drafts a
response -- ScoutReport (contracts.py) has no field that could hold one.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any, List, Optional

_BASE_DIR = Path(__file__).parent
_STATE_DIR = _BASE_DIR / "aurora_state"

sys.path.insert(0, str(_BASE_DIR))

from aurora_internal.scouting.backends import ScoutBackend, resolve_backend_chain
from aurora_internal.scouting.broker import ScoutBroker
from aurora_internal.scouting.contracts import ScoutRequest, ScoutReport


def _retrieve_and_normalize(
    request: ScoutRequest, *, state_dir: Any, backends: Optional[List[ScoutBackend]] = None,
) -> ScoutReport:
    """request -> retrieve -> normalize evidence -> report. The whole
    job of this worker, in one function so it's independently testable
    without the claim/submit loop around it.

    backends defaults to resolve_backend_chain() (spec step 7:
    [PoedexRoomBackend, LocalLessonsBackend] unless configured
    otherwise) -- tried in order, first one to produce non-empty text
    wins. Every backend returns raw text, never a ScoutReport itself, so
    normalization (truncation, evidence_items shape, provenance,
    confidence) is identical regardless of which backend answered."""
    started = time.time()

    if not str(request.inquiry or "").strip():
        return ScoutReport(
            request_id=request.request_id, turn_id=request.turn_id,
            request_kind=request.request_kind,
            status="no_evidence",
            elapsed_ms=(time.time() - started) * 1000.0,
        )

    active_backends = backends if backends is not None else resolve_backend_chain()
    tried_names: List[str] = []
    raw_result = ""
    source_name = ""
    for backend in active_backends:
        try:
            if not backend.is_available():
                continue
        except Exception:
            continue
        tried_names.append(backend.name)
        try:
            candidate = backend.retrieve(request, state_dir=state_dir)
        except Exception:
            candidate = ""
        if candidate:
            raw_result = candidate
            source_name = backend.name
            break

    elapsed_ms = (time.time() - started) * 1000.0

    if not raw_result:
        rationale = (
            f"no backend produced evidence (tried: {', '.join(tried_names)})" if tried_names
            else "no Scout backend was available -- no external evidence source reachable"
        )
        return ScoutReport(
            request_id=request.request_id, turn_id=request.turn_id,
            request_kind=request.request_kind,
            status="no_evidence", fit_rationales=[rationale],
            elapsed_ms=elapsed_ms,
        )

    text = raw_result[: max(1, int(request.max_result_chars or 1200))]
    evidence_items = [{"text": text, "source": source_name}]

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
        provenance=[source_name],
        confidence=0.55,
        elapsed_ms=elapsed_ms,
    )


def run(
    *,
    state_dir: Optional[Any] = None,
    poll_interval_s: float = 1.0,
    max_iterations: Optional[int] = None,
    backends: Optional[List[ScoutBackend]] = None,
) -> None:
    """The worker's whole life: claim one request at a time (broker
    enforces concurrency=1 by default), process it, submit a report,
    repeat. max_iterations is test-only -- production callers never
    pass it, so the loop runs forever.

    state_dir defaults to the module's repo-relative _STATE_DIR only
    when the caller supplies nothing at all -- desktop's `python3
    aurora_scout_daemon.py` with no arguments. Android's caller always
    passes its own writable application state directory explicitly
    (spec step 8).

    backends defaults to resolve_backend_chain() (spec step 7) -- an
    Android caller may pass its own chain explicitly (e.g. leading with
    LocalLessonsBackend only, if a future platform-specific backend set
    is ever warranted), but the default chain already works unmodified
    there."""
    active_state_dir = Path(state_dir) if state_dir is not None else _STATE_DIR
    active_backends = backends if backends is not None else resolve_backend_chain()
    broker = ScoutBroker(active_state_dir)
    print(
        f"[SCOUT] worker online, pid={os.getpid()}, concurrency={broker.max_concurrent}, "
        f"state_dir={active_state_dir}, backends={[b.name for b in active_backends]}", flush=True,
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
            report = _retrieve_and_normalize(request, state_dir=active_state_dir, backends=active_backends)
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

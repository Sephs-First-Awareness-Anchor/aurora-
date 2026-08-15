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
from aurora_internal.scouting.contracts import ScoutRequest, ScoutReport, RESPONSE_RELATIONSHIP_KINDS

# Build 694 step 10, spec section 13: "response_fit" reports must stop
# being hardwired to response_relationships=["explain"] for every
# result. Keyword-matched against the retrieved evidence text -- this
# genuinely varies with what a backend's text actually says, rather than
# fabricating variety the evidence doesn't support. Kept here (not in
# backends.py) because it's how the WORKER turns generic retrieved text
# into a categorized report, independent of which backend produced that
# text.
_RESPONSE_FIT_KEYWORDS: dict = {
    "acknowledge": ["greeting", "hello", "hi there", "welcomed", "acknowledg"],
    "continue_exploration": ["explore further", "keep exploring", "continue the topic", "follow up on"],
    "explain": ["because", "the reason is", "due to", "explanation"],
    "answer_directly": ["is defined as", "refers to", "the answer is", "means that"],
    "invite_continuation": ["ask a follow-up", "what would you like", "tell me more", "invite further"],
    "challenge": ["however", "contradicts", "on the other hand", "challenges"],
    "reassure": ["reassur", "it's okay", "no need to worry", "that's normal"],
    "clarify": ["clarify", "ambiguous", "unclear", "which do you mean"],
    "remain_conversationally_present": ["remain present", "stay engaged", "conversationally present", "simple acknowledgment"],
}


def _categorize_response_relationships(evidence_text: str) -> List[Any]:
    """Returns (category, matched_keyword) pairs, in
    RESPONSE_RELATIONSHIP_KINDS order, so fit_rationales can cite the
    actual textual signal behind each reported category. Empty when
    nothing in the evidence text matched any category -- the caller
    falls back to ["explain"] only in that genuinely-uninformative case,
    not for every result regardless of content."""
    lowered = evidence_text.lower()
    matches: List[Any] = []
    for category in RESPONSE_RELATIONSHIP_KINDS:
        for keyword in _RESPONSE_FIT_KEYWORDS.get(category, []):
            if keyword in lowered:
                matches.append((category, keyword))
                break
    return matches


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

    if request.request_kind == "response_fit":
        # Spec section 13: structured investigation of which response
        # relationships fit, not a single hardwired category.
        matches = _categorize_response_relationships(text)
        if matches:
            response_relationships = [c for c, _kw in matches][: max(1, int(request.max_evidence_items or 5))]
            fit_rationales = [
                f"{category}: evidence text contains '{keyword}', suggesting this response "
                f"relationship fits Aurora's interpreted state"
                for category, keyword in matches
            ]
        else:
            # Deliberately conservative fallback: "explain" is the least
            # presumptive category to report when nothing in the
            # retrieved text supports a more specific one -- never a
            # guess like "answer_directly" just because evidence came
            # back at all.
            response_relationships = ["explain"]
            fit_rationales = [
                "external evidence retrieved and available to inform, not dictate, the response -- "
                "no more specific response relationship was identifiable in the retrieved text"
            ]
    else:
        response_relationships = ["explain"]
        fit_rationales = ["external evidence retrieved and available to inform, not dictate, the response"]

    return ScoutReport(
        request_id=request.request_id,
        turn_id=request.turn_id,
        request_kind=request.request_kind,
        status="ok",
        evidence_items=evidence_items[: int(request.max_evidence_items or 5)],
        response_relationships=response_relationships,
        fit_rationales=fit_rationales,
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
    stop_event: Optional["threading.Event"] = None,
) -> None:
    """The worker's whole life: claim one request at a time (broker
    enforces concurrency=1 by default), process it, submit a report,
    repeat. max_iterations is test-only -- production callers never
    pass it, so the loop runs forever (or until stop_event is set).

    state_dir defaults to the module's repo-relative _STATE_DIR only
    when the caller supplies nothing at all -- desktop's `python3
    aurora_scout_daemon.py` with no arguments. Android's caller always
    passes its own writable application state directory explicitly
    (spec step 8).

    backends defaults to resolve_backend_chain() (spec step 7) -- an
    Android caller may pass its own chain explicitly (e.g. leading with
    LocalLessonsBackend only, if a future platform-specific backend set
    is ever warranted), but the default chain already works unmodified
    there.

    stop_event (spec step 8: "independently stoppable") -- when set,
    the loop exits at the next poll boundary rather than running until
    process exit. Production callers (e.g. Android, which runs this on
    a daemon thread inside the app's own process) construct their own
    threading.Event and hold onto it to stop the worker later without
    killing the whole process; the desktop CLI entry point below simply
    never sets one, so it runs forever as before."""
    active_state_dir = Path(state_dir) if state_dir is not None else _STATE_DIR
    active_backends = backends if backends is not None else resolve_backend_chain()
    broker = ScoutBroker(active_state_dir)
    print(
        f"[SCOUT] worker online, pid={os.getpid()}, concurrency={broker.max_concurrent}, "
        f"state_dir={active_state_dir}, backends={[b.name for b in active_backends]}", flush=True,
    )

    iterations = 0
    while (max_iterations is None or iterations < max_iterations) and (stop_event is None or not stop_event.is_set()):
        iterations += 1
        broker.expire_stale_requests()
        request = broker.claim_next()
        if request is None:
            if stop_event is not None:
                stop_event.wait(poll_interval_s)  # wakes immediately on stop, not just at the interval boundary
            else:
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

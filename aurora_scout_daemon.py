"""
Aurora model-free Evidence Scout worker (Build 711).

The worker is deliberately non-cognitive:
    request -> retrieve raw observations -> normalize/provenance -> report

It never calls a language model, never classifies response relationships, never
infers user intent, never explains why a response fits, and never drafts text for
Aurora. Subsurface/Aurora owns every interpretive step after retrieval.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

import json
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

    backends defaults to resolve_backend_chain() (Build 711 model-free
    default chain: public_human_dialogue, local_human_dialogue,
    public_web, local_lessons -- unless configured otherwise) -- tried
    in order, first one to produce non-empty text
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
    evidence_items = [{
        "text": text,
        "source": source_name,
        "kind": "response_exemplars" if request.request_kind == "response_fit" else "retrieved_evidence",
        "emittable": False,
    }]

    # Deliberately no response_relationships / fit classification here.
    # A non-cognitive retrieval worker has no authority to decide those.
    if request.request_kind == "response_fit":
        note = "raw response-fit observations retrieved; interpretation reserved to Aurora"
    elif request.request_kind == "knowledge_gap":
        note = "raw grounding evidence retrieved; interpretation reserved to Aurora"
    else:
        note = "raw evidence retrieved; interpretation reserved to Aurora"

    return ScoutReport(
        request_id=request.request_id,
        turn_id=request.turn_id,
        request_kind=request.request_kind,
        inquiry=request.inquiry,
        evidence_needed=request.evidence_needed,
        interpreted_input=request.interpreted_input,
        status="ok",
        evidence_items=evidence_items,
        response_relationships=[],
        fit_rationales=[note],
        contradictions=[],
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
    never sets one, so it runs forever as before.

    Build 694 step 17: this worker holds its own long-lived
    PresenceMetrics instance (role="scout"), recording scout_roundtrip_ms
    and scout_backend (spec section 30) once per claimed request --
    genuinely per-request, not throttled, since a Scout request happens
    far less often than a presence tick."""
    active_state_dir = Path(state_dir) if state_dir is not None else _STATE_DIR
    active_backends = backends if backends is not None else resolve_backend_chain()
    broker = ScoutBroker(active_state_dir)
    from aurora_internal.dual_strata.presence_metrics import PresenceMetrics
    metrics = PresenceMetrics(active_state_dir, role="scout")
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
        try:
            metrics.record_scout_roundtrip_ms(float(report.elapsed_ms or 0.0))
            metrics.record_scout_backend(report.provenance[0] if report.provenance else "none")
            metrics.write_snapshot()
        except Exception:
            pass


def _parse_cli_state_dir() -> Optional[str]:
    """`python3 aurora_scout_daemon.py --state-dir=/path/to/state` --
    optional; omitted entirely falls back to run()'s own default."""
    for arg in sys.argv[1:]:
        if arg.startswith("--state-dir="):
            return arg.split("=", 1)[1]
    return None


if __name__ == "__main__":
    run(state_dir=_parse_cli_state_dir())

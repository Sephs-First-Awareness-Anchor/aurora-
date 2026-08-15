"""
Subsurface Scout bridge (Subsurface Presence and Evidence Scout spec,
sections 11-12): the ONLY path a ScoutReport may travel to reach any
cognitive state. Surface must never call ScoutBroker.poll_reports()
directly and must never read scout_reports/ itself -- Surface only ever
sees the EvidenceBinding this module produces, once Subsurface has
already evaluated it (spec step 9 wires that harvest; this module only
produces and stores the bindings).

Evaluation, not pass-through (spec section 11): a ScoutReport does not
become usable evidence just by existing. This module decides:

    relevance     does this report still belong to a turn Subsurface
                  currently considers live, or did a newer turn open
                  before the report came back?
    consistency   does the report contradict itself (report.contradictions)?
    strength      report.confidence, as reported by the Scout.
    pressure_relief   always 0.0 at retrieval time in Build 711. A Scout
                  returning evidence is not evidence that Aurora has
                  understood or resolved the response-fit pressure. A
                  knowledge_gap report becomes provisional semantic
                  evidence instead -- Aurora reconsiders interpretation
                  with it, it never mechanically subtracts from
                  response_fit_pressure. A self_diagnostic report must
                  never touch live-turn pressure at all.

A report whose turn_id no longer matches Subsurface's live turn (per
the presence frame Subsurface itself last published) is bound and
stored under ITS OWN turn_id -- never folded into the CURRENT turn's
active presence/pressure. That is what stops a late-arriving report
from a previous turn from silently reshaping the turn Aurora is in now
("stale report cannot hijack new turn").
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations
from aurora_internal.aurora_runtime_faults import record_exception_from_locals as _aurora_record_exception_from_locals

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from aurora_internal.scouting.broker import ScoutBroker
from aurora_internal.scouting.contracts import ScoutReport
from aurora_internal.dual_strata.subsurface_presence import read_presence_frame, write_presence_frame

_BINDINGS_FILENAME = "subsurface_evidence_bindings.json"
_MAX_TURNS_KEPT = 12
_MAX_BINDINGS_PER_TURN = 6
# spec section 11: below this combined relevance*consistency*strength
# score, evidence is too weak/contradicted to integrate at all -- it is
# recorded (rejected, not silently dropped) but never relieves pressure.
_ACCEPTANCE_THRESHOLD = 0.2
# A report whose turn is no longer Subsurface's live turn is still
# real evidence about ITS turn -- just heavily discounted so it can
# never outweigh a genuinely current, on-topic report.
_STALE_TURN_RELEVANCE = 0.15


def _resolve(state_dir: Any) -> Path:
    if state_dir is not None:
        return Path(str(state_dir))
    return Path(__file__).resolve().parents[2] / "aurora_state"


def _atomic_write(path: Path, payload: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)


@dataclass
class EvidenceBinding:
    binding_id: str
    request_id: str
    turn_id: str
    status: str  # "accepted" | "rejected" | "stale"
    request_kind: str = "response_fit"
    inquiry: str = ""
    evidence_needed: str = ""
    interpreted_input: str = ""
    relevance: float = 0.0
    consistency: float = 0.0
    strength: float = 0.0
    pressure_relief: float = 0.0
    response_relationships: List[str] = field(default_factory=list)
    fit_rationales: List[str] = field(default_factory=list)
    contradictions: List[str] = field(default_factory=list)
    provenance: List[str] = field(default_factory=list)
    evidence_items: List[Dict[str, Any]] = field(default_factory=list)
    rejected_reason: Optional[str] = None
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_report(report: ScoutReport, *, current_turn_id: str = "") -> EvidenceBinding:
    """Pure function: report + Subsurface's live turn -> one evaluated
    EvidenceBinding. No I/O, so it's directly testable without a broker
    or state_dir at all."""
    binding_id = uuid.uuid4().hex
    common = dict(
        binding_id=binding_id,
        request_id=report.request_id,
        turn_id=report.turn_id,
        request_kind=report.request_kind,
        inquiry=str(getattr(report, "inquiry", "") or ""),
        evidence_needed=str(getattr(report, "evidence_needed", "") or ""),
        interpreted_input=str(getattr(report, "interpreted_input", "") or ""),
        response_relationships=list(report.response_relationships),
        fit_rationales=list(report.fit_rationales),
        contradictions=list(report.contradictions),
        provenance=list(report.provenance),
        evidence_items=list(report.evidence_items),
    )

    if report.status != "ok":
        return EvidenceBinding(
            status="rejected", relevance=0.0, consistency=0.0, strength=0.0, pressure_relief=0.0,
            rejected_reason=f"scout status={report.status!r}", **common,
        )

    if not report.evidence_items:
        return EvidenceBinding(
            status="rejected", relevance=0.0, consistency=0.0, strength=0.0, pressure_relief=0.0,
            rejected_reason="report has no evidence items", **common,
        )

    # self_diagnostic reports (spec step 11) are Subsurface's own
    # autonomous research, never scoped to a live user turn -- the
    # turn-currency check below doesn't apply to them at all, so they
    # skip straight to strength/consistency-only acceptance instead of
    # being discounted as though a newer turn had made them stale.
    is_self_diagnostic = report.request_kind == "self_diagnostic"
    is_current = is_self_diagnostic or (bool(current_turn_id) and report.turn_id == current_turn_id)
    relevance = 1.0 if is_current else _STALE_TURN_RELEVANCE
    consistency = 0.4 if report.contradictions else 1.0
    strength = max(0.0, min(1.0, float(report.confidence or 0.0)))
    combined = round(relevance * consistency * strength, 4)

    if not is_current:
        status = "stale"
        rejected_reason = "report's turn is no longer Subsurface's live turn -- recorded, not folded into current presence"
    elif combined < _ACCEPTANCE_THRESHOLD:
        status = "rejected"
        rejected_reason = "combined relevance/consistency/strength below acceptance threshold"
    else:
        status = "accepted"
        rejected_reason = None

    # Build 711 model-free invariant: retrieval evidence never gets to
    # declare a response-fit problem resolved. A Scout only returns raw
    # observations. Until Aurora herself evaluates/uses those observations,
    # response_fit_pressure remains her unresolved pressure. This prevents
    # "the courier came back" from being mistaken for "Aurora understood."
    pressure_relief = 0.0

    return EvidenceBinding(
        status=status,
        relevance=relevance,
        consistency=consistency,
        strength=strength,
        pressure_relief=pressure_relief,
        rejected_reason=rejected_reason,
        **common,
    )


def _load_store(state_dir: Any) -> Dict[str, List[Dict[str, Any]]]:
    path = _resolve(state_dir) / _BINDINGS_FILENAME
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(), module=__name__,
            operation="exception_handler:aurora_internal/scouting/subsurface_scout_bridge.py:_load_store",
            exc=_aurora_boundary_exc,
            context={"function": "_load_store", "source_file": "aurora_internal/scouting/subsurface_scout_bridge.py"},
        )
        return {}


def record_binding(state_dir: Any, binding: EvidenceBinding) -> None:
    """Persist one binding under its own turn_id, bounded per-turn and
    across turns, so a burst of stale/rejected reports can never grow
    this file without limit."""
    root = _resolve(state_dir)
    path = root / _BINDINGS_FILENAME
    store = _load_store(state_dir)

    turn_bindings = store.get(binding.turn_id, [])
    turn_bindings.append(binding.to_dict())
    store[binding.turn_id] = turn_bindings[-_MAX_BINDINGS_PER_TURN:]

    if len(store) > _MAX_TURNS_KEPT:
        ordered_turns = sorted(
            store.keys(),
            key=lambda tid: max((b.get("created_at", 0.0) for b in store[tid]), default=0.0),
        )
        for stale_turn in ordered_turns[: len(store) - _MAX_TURNS_KEPT]:
            store.pop(stale_turn, None)

    try:
        _atomic_write(path, store)
    except Exception as _aurora_boundary_exc:
        _aurora_record_exception_from_locals(
            locals(), module=__name__,
            operation="exception_handler:aurora_internal/scouting/subsurface_scout_bridge.py:record_binding",
            exc=_aurora_boundary_exc,
            context={"function": "record_binding", "source_file": "aurora_internal/scouting/subsurface_scout_bridge.py"},
        )


def read_bindings_for_turn(state_dir: Any, turn_id: str) -> List[Dict[str, Any]]:
    """Step 9's future Surface harvest point, and this module's own
    tests, both read through here -- never through the bindings file
    directly. Only ever returns bindings for the EXACT turn_id asked
    for, which is the other half of the stale-report guard: even if a
    stale binding is sitting in the store under an old turn_id, a
    caller asking about the new turn_id simply never sees it."""
    store = _load_store(state_dir)
    return list(store.get(str(turn_id or ""), []))


# spec section 17's own poll-interval framing: "so this does not require
# wasteful high-frequency filesystem polling." SubsurfacePresenceRuntime
# (subsurface_presence_runtime.py, build 694 step 4) already polls turn
# events/Scout reports at this exact cadence as this architecture's
# established presence granularity -- reusing it here, rather than
# picking a tighter interval, keeps this wait no more "wasteful" than
# presence processing already is everywhere else in this codebase.
_DEFAULT_WAIT_POLL_INTERVAL_S = 0.15


def wait_for_current_turn_binding(
    state_dir: Any,
    *,
    turn_id: str,
    request_kind: Optional[str] = None,
    timeout: float,
    poll_interval_s: float = _DEFAULT_WAIT_POLL_INTERVAL_S,
) -> Optional[Dict[str, Any]]:
    """
    Build 694 step 14 (spec section 17): "Surface must never poll
    scout_reports directly... Provide a wait primitive such as
    wait_for_current_turn_binding(turn_id, request_kind, timeout). This
    waits for an accepted Subsurface EvidenceBinding." The path stays
    ScoutReport -> Subsurface evaluation -> EvidenceBinding -> Surface,
    never ScoutReport -> Surface directly -- this reads exclusively
    through read_bindings_for_turn() (spec section 11), the exact same
    call _harvest_scout_evidence_for_expression()/
    _ingest_current_turn_scout_evidence() in aurora.py already use, so a
    waiting caller and a non-waiting caller can never see a different
    notion of "accepted evidence for this turn."

    Bounded and file-backed by construction -- correct whether or not a
    fast SubsurfacePresenceRuntime happens to be running in this process
    (tests, and any deployment that hasn't started one), and across
    separate desktop processes (spec section 17's explicit file-backed-
    fallback allowance), not only in-process. A future optimization could
    additionally wire SubsurfacePresenceRuntime.on_binding_change (already
    an extension point built for this) for a faster in-process wake; this
    bounded poll remains correct either way and is deliberately kept as
    the sole implementation for now rather than adding two code paths
    that could quietly drift.

    Returns the first matching accepted binding dict, or None once
    `timeout` elapses with nothing landing. `timeout=0` (or a non-
    positive value) checks once and returns immediately -- callers
    implementing spec section 16's "normal well-resolved turn: 0
    additional wait" tier should simply not call this at all rather than
    rely on that as a code path, but it degrades safely if they do.
    """
    deadline = time.time() + max(0.0, float(timeout or 0.0))
    interval = max(0.01, float(poll_interval_s or _DEFAULT_WAIT_POLL_INTERVAL_S))
    while True:
        for binding in read_bindings_for_turn(state_dir, turn_id):
            if not isinstance(binding, dict) or binding.get("status") != "accepted":
                continue
            if request_kind and binding.get("request_kind") != request_kind:
                continue
            return binding
        remaining = deadline - time.time()
        if remaining <= 0:
            return None
        time.sleep(min(interval, remaining))


def consume_scout_reports(state_dir: Any, *, broker: Optional[ScoutBroker] = None) -> List[EvidenceBinding]:
    """Subsurface's main loop calls this once per cycle (mirrors
    _consume_subsurface_turn_events in aurora_daemon.py). Drains every
    finished ScoutReport, evaluates and stores each as an
    EvidenceBinding, and -- only for bindings ACCEPTED against
    Subsurface's current live turn -- folds them into the presence
    frame's evidence_bindings/response_fit_pressure. Returns every
    binding produced (accepted, rejected, and stale alike) so the
    caller can log what happened without needing a second read."""
    active_broker = broker or ScoutBroker(state_dir)
    reports = active_broker.poll_reports()
    if not reports:
        return []

    frame = read_presence_frame(state_dir) or {}
    current_turn_id = str(frame.get("turn_id", "") or "")

    bindings: List[EvidenceBinding] = []
    for report in reports:
        binding = evaluate_report(report, current_turn_id=current_turn_id)
        record_binding(state_dir, binding)
        bindings.append(binding)

    accepted_current = [b for b in bindings if b.status == "accepted" and b.turn_id == current_turn_id]
    if accepted_current:
        prior_pressure = float(frame.get("response_fit_pressure", 0.0) or 0.0)
        # Build 694 step 11 (spec section 12): only response_fit bindings
        # ever relieve response_fit_pressure. evaluate_report() already
        # zeroes pressure_relief for every other request_kind, but
        # summing only over response_fit bindings here too keeps the
        # invariant explicit rather than depending solely on that
        # upstream zeroing -- knowledge_gap/self_diagnostic bindings
        # still appear in accepted_current (and below, in evidence_bindings/
        # scout_evidence_integrated) as evidence Subsurface has, just
        # never as pressure relief.
        response_fit_accepted = [b for b in accepted_current if b.request_kind == "response_fit"]
        total_relief = sum(b.pressure_relief for b in response_fit_accepted)
        updated_pressure = max(0.0, min(1.0, prior_pressure - total_relief))

        try:
            write_presence_frame(
                state_dir,
                turn_id=current_turn_id,
                crest=frame.get("crest") if isinstance(frame.get("crest"), dict) else None,
                active_pressure=frame.get("active_pressure") if isinstance(frame.get("active_pressure"), dict) else None,
                continuity_summary=str(frame.get("continuity_summary", "") or ""),
                unresolved_tensions=list(frame.get("unresolved_tensions", []) or []),
                scout_requests_pending=active_broker.queue_depth() + active_broker.active_count(),
                scout_evidence_integrated=[b.binding_id for b in accepted_current],
                response_fit_pressure=updated_pressure,
                evidence_bindings=[b.to_dict() for b in accepted_current],
            )
        except Exception as _aurora_boundary_exc:
            _aurora_record_exception_from_locals(
                locals(), module=__name__,
                operation="exception_handler:aurora_internal/scouting/subsurface_scout_bridge.py:consume_scout_reports",
                exc=_aurora_boundary_exc,
                context={"function": "consume_scout_reports", "source_file": "aurora_internal/scouting/subsurface_scout_bridge.py"},
            )

    return bindings

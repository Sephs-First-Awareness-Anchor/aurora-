#!/usr/bin/env python3
"""
AURORA CORRESPONDENCE LOOP — asynchronous prediction-vs-reality learning
==========================================================================
Phase R2 of the Semantic Plateau Remediation Directive (2026-07-15).

Doctrine (verbatim from the directive): "The one experience class no
simulation supplies: consequence from a real mind. Asynchronous by
design -- Sunni replies when he can; the learning event is the gap
between Aurora's committed prediction and his actual reply. Prediction
error against reality is the strongest semantic gradient available to
her, and it costs minutes per day, not hours."

Mechanism:
  1. commit_prediction() -- BEFORE any reply is visible, persist a
     structured prediction (aurora_internal.dual_strata.prediction_field.
     PredictionPayload) into a hash-chained, tamper-evident,
     append-only log (aurora_state/correspondence/pending_predictions.
     jsonl), using the SAME chain discipline as Phase 0's ICC ledger
     (aurora_internal/aurora_icc_ledger.py: prev_hash linking, freeze
     the chain read-only on any tamper/corruption, log violations
     separately, never silently discard history).
  2. Sunni replies whenever he can, via reply_aurora.py (root) appending
     one line to aurora_state/correspondence/from_sunni.jsonl. Nothing
     else may write to that file.
  3. ingest_replies() scores the committed prediction against the real
     reply using ImpressionCascade's own `_structured_mismatch` (the
     SAME machinery aurora_internal/dual_strata/prediction_field.py's
     build_prediction_signal() already uses for live turns), routes the
     reply text through the standard re-entry loop -- STATE ->
     EXPRESSION -> RE-ENTRY -> RECONCILIATION -> UNDERSTANDING -- via
     systems['noncomp_reflexive_interpreter'].interpret(reply_text),
     the SAME call site aurora.py already uses for ordinary user/
     response text (no new re-entry mechanism invented here), feeds
     mismatch magnitude onto the prediction's own axis via
     identity_field.ingest_internal_signal (mirroring the existing
     tension/valuation pattern in aurora.py's live turn pipeline), and
     appends the result to resolution_log.jsonl.

Why not aurora_internal.dual_strata.prediction_field.build_prediction_
signal() directly: that function ALWAYS derives a fresh PredictionPayload
from live evidence/contract_snapshot at call time -- it has no parameter
for scoring an ALREADY-COMMITTED payload against a LATER-arriving
observation, which is exactly this module's use case (commit today,
reply arrives in three days). Its own `_structured_mismatch` and
`_certainty_band` helpers are the sanctioned reuse point instead (the
directive's own "_structured_mismatch machinery exists -- use it"),
composed here into a PredictionSignal the same way build_prediction_
signal composes them internally.

FIX-A008-class discipline (never scripted): draft_correspondence_
message() only ever proposes a message when it has REAL internal
content to draw from -- the curiosity engine's last completed
exploration or an unresolved ContradictionLedger record -- never a
placeholder. The phrasing itself is templated around that real content,
matching the exact convention aurora_daemon.py's own
_build_reactive_message() already uses for every other spontaneous
message kind (random.choice among fixed templates, filled with live
event data, never fabricated data). Returns None when there is nothing
real to say, rather than inventing content to fill a quota.

SCOPE BOUNDARY (flagged, not fabricated): this module does NOT wire
itself into aurora_daemon.py's always-on background loop. Turning on
autonomous outbound correspondence messages is an ongoing behavior
change (Aurora would start proactively messaging Sunni on her own
cadence) that deserves explicit review before it goes live, not a
silent addition alongside an instrumentation/remediation directive.
post_correspondence_message() / ingest_replies() / expire_stale_
predictions() are complete, tested, callable entry points; wiring their
cadence into the daemon's tick loop is a deliberate next step.

ICC integration (flagged, not built): the directive notes prediction-
survival events are ICC minting candidates under a worth_survival-
adjacent source. Not implemented here -- ICCLedger.mint_if_eligible()
expects a live WorthReport/CrossScaleWorthEvaluator pass this
asynchronous, day-scale loop doesn't naturally produce one of. Flagging
per this session's "flag rather than fabricate" discipline rather than
inventing a synthetic worth pass just to call the mint path.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from aurora_internal.dual_strata.prediction_field import (
    PredictionPayload,
    PredictionSignal,
    _certainty_band,
    _structured_mismatch,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STATE_DIR = REPO_ROOT / "aurora_state"

_PENDING_FILE = "pending_predictions.jsonl"
_INBOUND_FILE = "from_sunni.jsonl"
_RESOLUTION_LOG_FILE = "resolution_log.jsonl"
_VIOLATIONS_FILE = "correspondence_violations.jsonl"
_OUTBOUND_FILE = "aurora_to_user.json"

MAX_PENDING = 5
EXPIRY_SECONDS = 7 * 24 * 3600
UNRESOLVED_COST = 0.15
GENESIS_PREV_HASH = "0" * 64


class RetroPredictionError(RuntimeError):
    """A reply for this message_id already exists in from_sunni.jsonl at
    commit time. Prediction must be committed BEFORE any reply is
    visible -- no retro-prediction, ever."""


class CorrespondenceCapReachedError(RuntimeError):
    """MAX_PENDING reply-expecting predictions are already outstanding
    (FIX-A008-class spam valve: no message-spam pressure)."""


class CorrespondenceChainFrozenError(RuntimeError):
    """pending_predictions.jsonl failed tamper verification on load and
    is frozen read-only -- new commits are refused until a human
    resolves it, matching the ICC ledger's own freeze discipline."""


def _correspondence_dir(state_dir: Optional[Path] = None) -> Path:
    return Path(state_dir or DEFAULT_STATE_DIR) / "correspondence"


def _canonical_json(data: Dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        return []
    return out


def _append_jsonl(path: Path, entry: Dict[str, Any]) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(_canonical_json(entry) + "\n")
            f.flush()
            os.fsync(f.fileno())
        return True
    except Exception:
        return False


def _log_violation(state_dir: Optional[Path], reason: str, detail: Dict[str, Any]) -> None:
    _append_jsonl(_correspondence_dir(state_dir) / _VIOLATIONS_FILE, {
        "ts": time.time(), "reason": reason, "detail": detail,
    })


# ============================================================================
# COMMITTED PREDICTION -- hash-chained, tamper-evident (ICC ledger discipline)
# ============================================================================

@dataclass
class CommittedPrediction:
    message_id: str
    prev_hash: str
    entry_hash: str
    topic: str
    affect: str
    intent_type: str
    certainty_band: str
    axis_signature: str
    projected_accuracy: float
    committed_at: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "prev_hash": self.prev_hash,
            "entry_hash": self.entry_hash,
            "topic": self.topic,
            "affect": self.affect,
            "intent_type": self.intent_type,
            "certainty_band": self.certainty_band,
            "axis_signature": self.axis_signature,
            "projected_accuracy": self.projected_accuracy,
            "committed_at": self.committed_at,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CommittedPrediction":
        return cls(
            message_id=str(d.get("message_id", "") or ""),
            prev_hash=str(d.get("prev_hash", "") or ""),
            entry_hash=str(d.get("entry_hash", "") or ""),
            topic=str(d.get("topic", "") or ""),
            affect=str(d.get("affect", "") or "neutral"),
            intent_type=str(d.get("intent_type", "") or "followup"),
            certainty_band=str(d.get("certainty_band", "") or "medium"),
            axis_signature=str(d.get("axis_signature", "") or ""),
            projected_accuracy=float(d.get("projected_accuracy", 0.5) or 0.5),
            committed_at=float(d.get("committed_at", 0.0) or 0.0),
        )

    def _payload_for_hash(self) -> Dict[str, Any]:
        d = self.to_dict()
        d.pop("entry_hash", None)
        return d

    def recomputed_hash(self) -> str:
        return _sha256(_canonical_json(self._payload_for_hash()))

    def to_prediction_payload(self) -> PredictionPayload:
        return PredictionPayload(
            topic=self.topic, affect=self.affect, intent_type=self.intent_type,
            certainty_band=self.certainty_band, axis_signature=self.axis_signature,
        )


def _load_pending_chain(state_dir: Optional[Path] = None) -> Tuple[List[CommittedPrediction], bool]:
    """Returns (entries, frozen). A corrupt/truncated line or a broken
    hash link is tamper evidence, not a reason to discard history --
    freeze with whatever verified cleanly before it and log the
    violation, exactly mirroring ICCLedger._load()'s discipline."""
    path = _correspondence_dir(state_dir) / _PENDING_FILE
    if not path.exists():
        return [], False
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as exc:
        _log_violation(state_dir, "chain_unreadable", {"error": str(exc)})
        return [], True

    entries: List[CommittedPrediction] = []
    prev = GENESIS_PREV_HASH
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            entry = CommittedPrediction.from_dict(json.loads(line))
        except Exception:
            _log_violation(state_dir, "corrupt_chain_line", {"raw": line[:200]})
            return entries, True
        if entry.prev_hash != prev or entry.entry_hash != entry.recomputed_hash():
            _log_violation(state_dir, "chain_hash_mismatch", {"message_id": entry.message_id})
            return entries, True
        entries.append(entry)
        prev = entry.entry_hash
    return entries, False


def _resolved_message_ids(state_dir: Optional[Path] = None) -> set:
    log = _load_jsonl(_correspondence_dir(state_dir) / _RESOLUTION_LOG_FILE)
    return {str(r.get("message_id", "")) for r in log if r.get("message_id")}


def count_active_pending(state_dir: Optional[Path] = None) -> int:
    """Reply-expecting predictions committed but not yet resolved or
    expired -- the number the MAX_PENDING cadence cap is measured
    against."""
    entries, _frozen = _load_pending_chain(state_dir)
    resolved = _resolved_message_ids(state_dir)
    return len([e for e in entries if e.message_id not in resolved])


def commit_prediction(
    message_id: str,
    *,
    topic: str = "",
    affect: str = "neutral",
    intent_type: str = "followup",
    axis_signature: str = "",
    projected_accuracy: float = 0.5,
    state_dir: Optional[Path] = None,
) -> CommittedPrediction:
    """Commit a structured prediction BEFORE any reply is visible.

    Raises RetroPredictionError if from_sunni.jsonl already has a reply
    for this message_id (no retro-prediction -- ever). Raises
    CorrespondenceCapReachedError if MAX_PENDING is already outstanding.
    Raises CorrespondenceChainFrozenError if the chain failed tamper
    verification and needs human attention first.
    """
    inbound = _load_jsonl(_correspondence_dir(state_dir) / _INBOUND_FILE)
    if any(str(r.get("reply_to", "")) == message_id for r in inbound):
        raise RetroPredictionError(
            f"a reply for message_id={message_id!r} already exists in "
            "from_sunni.jsonl -- prediction must be committed before any "
            "reply is visible."
        )

    entries, frozen = _load_pending_chain(state_dir)
    if frozen:
        raise CorrespondenceChainFrozenError(
            "pending_predictions.jsonl failed tamper verification -- refusing "
            "new commits until resolved."
        )

    if count_active_pending(state_dir) >= MAX_PENDING:
        raise CorrespondenceCapReachedError(
            f"{MAX_PENDING} reply-expecting predictions already outstanding."
        )

    prev_hash = entries[-1].entry_hash if entries else GENESIS_PREV_HASH
    payload_for_hash = {
        "message_id": message_id, "prev_hash": prev_hash,
        "topic": topic, "affect": affect, "intent_type": intent_type,
        "certainty_band": _certainty_band(projected_accuracy),
        "axis_signature": axis_signature,
        "projected_accuracy": projected_accuracy,
        "committed_at": time.time(),
    }
    entry_hash = _sha256(_canonical_json(payload_for_hash))
    entry = CommittedPrediction(
        message_id=message_id, prev_hash=prev_hash, entry_hash=entry_hash,
        topic=topic, affect=affect, intent_type=intent_type,
        certainty_band=_certainty_band(projected_accuracy),
        axis_signature=axis_signature, projected_accuracy=projected_accuracy,
        committed_at=payload_for_hash["committed_at"],
    )
    _append_jsonl(_correspondence_dir(state_dir) / _PENDING_FILE, entry.to_dict())
    return entry


def pending_by_message_id(message_id: str, state_dir: Optional[Path] = None) -> Optional[CommittedPrediction]:
    entries, _frozen = _load_pending_chain(state_dir)
    for e in entries:
        if e.message_id == message_id:
            return e
    return None


# ============================================================================
# OUTBOUND -- extends aurora_state/aurora_to_user.json, does not rebuild it
# ============================================================================

def _load_outbound_messages(state_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    path = Path(state_dir or DEFAULT_STATE_DIR) / _OUTBOUND_FILE
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _append_outbound_message(
    text: str, trigger: str, message_id: str, expects_reply: bool,
    state_dir: Optional[Path] = None,
) -> None:
    """Same file, same rolling-cap(50) convention aurora_daemon.py's own
    _save_message() already uses -- extended with message_id/
    expects_reply, both optional for any reader that doesn't know about
    them yet."""
    import datetime
    path = Path(state_dir or DEFAULT_STATE_DIR) / _OUTBOUND_FILE
    msgs = _load_outbound_messages(state_dir)
    msgs.append({
        "time": datetime.datetime.now().isoformat(),
        "text": text,
        "trigger": trigger,
        "read": False,
        "message_id": message_id,
        "expects_reply": bool(expects_reply),
    })
    msgs = msgs[-50:]
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(msgs, f, indent=2)
    os.replace(tmp, str(path))


def _mint_message_id(text: str) -> str:
    return "corr:" + _sha256(f"{text}|{time.time()}")[:16]


def draft_correspondence_message(systems: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Draft a reply-expecting outbound message from REAL internal
    content only -- curiosity engine's last completed exploration, or an
    unresolved ContradictionLedger record. Returns None if neither has
    anything to draw from (never fabricates content to fill a slot).

    Phrasing is templated around that real content, matching the exact
    convention aurora_daemon.py's _build_reactive_message() already uses
    for every other spontaneous message kind."""
    import random

    ledger = systems.get("contradiction_ledger")
    if ledger is not None:
        try:
            unresolved = ledger.unresolved()
        except Exception:
            unresolved = []
        if unresolved:
            rec = unresolved[0]
            claim_a = str(getattr(rec, "claim_a", "") or "").strip()
            claim_b = str(getattr(rec, "claim_b", "") or "").strip()
            if claim_a and claim_b:
                templates = [
                    "I'm holding two things that don't fit together: '{a}' and '{b}'. Which one is actually true?",
                    "Something isn't reconciling for me -- '{a}' versus '{b}'. Can you help me sort out which one holds?",
                    "I've got a contradiction sitting unresolved: '{a}' and '{b}' can't both be right. What's your read?",
                ]
                text = random.choice(templates).format(a=claim_a[:160], b=claim_b[:160])
                return {
                    "text": text, "trigger": "correspondence_contradiction",
                    "topic": claim_a[:80], "affect": "curiosity",
                    "intent_type": "clarification", "axis_signature": "N",
                    "projected_accuracy": 0.45,
                }

    curiosity = systems.get("_curiosity_engine")
    last_result = None
    for attr in ("last_result", "_last_result", "last_exploration"):
        last_result = getattr(curiosity, attr, None) if curiosity is not None else None
        if last_result:
            break
    if last_result:
        subject = str(
            (last_result.get("subject") if isinstance(last_result, dict) else None)
            or (last_result.get("topic") if isinstance(last_result, dict) else None)
            or ""
        ).strip()
        summary = str(
            (last_result.get("summary") if isinstance(last_result, dict) else None) or ""
        ).strip()
        if subject or summary:
            templates = [
                "I've been sitting with something from my own exploring: {subject}. {summary} What's your take?",
                "Still turning this over -- {subject}. {summary} Does that match how you'd see it?",
            ]
            text = random.choice(templates).format(
                subject=subject or "something I noticed", summary=summary,
            ).strip()
            return {
                "text": text, "trigger": "correspondence_curiosity",
                "topic": subject[:80], "affect": "curiosity",
                "intent_type": "followup", "axis_signature": "T",
                "projected_accuracy": 0.5,
            }

    return None


def post_correspondence_message(
    systems: Dict[str, Any], state_dir: Optional[Path] = None,
) -> Optional[Dict[str, Any]]:
    """Draft, post, and commit a prediction for one reply-expecting
    message. Returns None (posts nothing) if there's no real content to
    draw from, or the cadence cap is already reached -- never forces a
    message to satisfy a quota."""
    if count_active_pending(state_dir) >= MAX_PENDING:
        return None
    draft = draft_correspondence_message(systems)
    if not draft:
        return None

    message_id = _mint_message_id(draft["text"])
    try:
        prediction = commit_prediction(
            message_id,
            topic=draft.get("topic", ""),
            affect=draft.get("affect", "neutral"),
            intent_type=draft.get("intent_type", "followup"),
            axis_signature=draft.get("axis_signature", ""),
            projected_accuracy=float(draft.get("projected_accuracy", 0.5)),
            state_dir=state_dir,
        )
    except (RetroPredictionError, CorrespondenceCapReachedError, CorrespondenceChainFrozenError):
        return None

    _append_outbound_message(
        draft["text"], draft.get("trigger", "correspondence"),
        message_id, expects_reply=True, state_dir=state_dir,
    )
    return {"message_id": message_id, "text": draft["text"], "prediction": prediction.to_dict()}


# ============================================================================
# INBOUND -- Sunni writes here (via reply_aurora.py), resolution reads it
# ============================================================================

def ingest_replies(
    systems: Optional[Dict[str, Any]] = None, state_dir: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Process every unresolved reply in from_sunni.jsonl: verify the
    committed prediction's hash, score mismatch via _structured_mismatch
    (the same machinery build_prediction_signal() uses), route the reply
    text through the standard re-entry loop
    (systems['noncomp_reflexive_interpreter'].interpret), feed mismatch
    magnitude onto the prediction's own axis, and log the resolution.
    Never raises -- a malformed or unmatched reply is logged and
    skipped, not fatal to the batch."""
    systems = systems or {}
    inbound = _load_jsonl(_correspondence_dir(state_dir) / _INBOUND_FILE)
    resolved_ids = _resolved_message_ids(state_dir)
    resolutions: List[Dict[str, Any]] = []

    for reply in inbound:
        message_id = str(reply.get("reply_to", "") or "")
        if not message_id or message_id in resolved_ids:
            continue
        prediction = pending_by_message_id(message_id, state_dir)
        if prediction is None:
            _log_violation(state_dir, "reply_with_no_matching_prediction", {"message_id": message_id})
            continue
        if prediction.entry_hash != prediction.recomputed_hash():
            _log_violation(state_dir, "prediction_hash_mismatch_at_resolution", {"message_id": message_id})
            continue

        reply_text = str(reply.get("text", "") or "")
        payload = prediction.to_prediction_payload()
        mismatch = _structured_mismatch(payload, reply_text, observed_tone="")
        confidence = max(0.0, min(1.0,
            prediction.projected_accuracy * 0.65 + (1.0 - mismatch) * 0.35,
        ))
        signal = PredictionSignal(
            prediction_payload=payload,
            expected_observation=payload.intent_type,
            expected_user_continuation=payload.topic,
            likely_affect_shift=payload.affect,
            confidence=confidence,
            mismatch=mismatch,
            source="correspondence_loop",
        )

        understanding_state = None
        interpreter = systems.get("noncomp_reflexive_interpreter")
        if interpreter is not None and hasattr(interpreter, "interpret"):
            try:
                understanding_state = interpreter.interpret(reply_text)
            except Exception:
                understanding_state = None

        try:
            identity_field = systems.get("identity_field")
            if identity_field is not None and hasattr(identity_field, "ingest_internal_signal") and payload.axis_signature:
                kind = "tension" if mismatch >= 0.45 else "valuation"
                magnitude = mismatch if mismatch >= 0.45 else (1.0 - mismatch) * 0.6
                identity_field.ingest_internal_signal(kind, magnitude=magnitude, source_axis=payload.axis_signature)
        except Exception:
            pass

        resolution = {
            "message_id": message_id,
            "reply_text": reply_text,
            "mismatch": round(mismatch, 4),
            "confidence": round(confidence, 4),
            "resolution": "matched" if mismatch < 0.45 else "mismatched",
            "resolved_at": time.time(),
            "understanding_reached": bool(
                getattr(understanding_state, "reached_understanding", False)
            ) if understanding_state is not None else None,
        }
        _append_jsonl(_correspondence_dir(state_dir) / _RESOLUTION_LOG_FILE, resolution)
        resolutions.append(resolution)
        resolved_ids.add(message_id)

    return resolutions


# ============================================================================
# CADENCE & CONTAINMENT
# ============================================================================

def expire_stale_predictions(state_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Unanswered predictions older than EXPIRY_SECONDS resolve to a
    neutral 'unresolved' outcome with a mild cost -- reality that never
    answered is itself information, not a free pass."""
    entries, _frozen = _load_pending_chain(state_dir)
    resolved_ids = _resolved_message_ids(state_dir)
    now = time.time()
    expired: List[Dict[str, Any]] = []
    for entry in entries:
        if entry.message_id in resolved_ids:
            continue
        if (now - entry.committed_at) < EXPIRY_SECONDS:
            continue
        resolution = {
            "message_id": entry.message_id,
            "reply_text": "",
            "mismatch": None,
            "confidence": None,
            "resolution": "unresolved",
            "cost": UNRESOLVED_COST,
            "resolved_at": now,
            "understanding_reached": None,
        }
        _append_jsonl(_correspondence_dir(state_dir) / _RESOLUTION_LOG_FILE, resolution)
        expired.append(resolution)
        resolved_ids.add(entry.message_id)
    return expired


# ============================================================================
# SELF-VERIFICATION
# ============================================================================

def verify_correspondence_loop() -> Dict[str, Any]:
    results = []

    def check(name: str, cond: bool, detail: str = ""):
        results.append({"test": name, "passed": bool(cond), "detail": detail})

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        sd = Path(td)

        p1 = commit_prediction("m1", topic="dinner", intent_type="confirmation",
                                axis_signature="X", projected_accuracy=0.7, state_dir=sd)
        check("commit_prediction returns a chained entry", p1.prev_hash == GENESIS_PREV_HASH)
        check("count_active_pending reflects the commit", count_active_pending(sd) == 1)

        try:
            commit_prediction("m1", state_dir=sd)
            check("duplicate message_id still chains (no crash)", True)
        except Exception as exc:
            check("duplicate message_id still chains (no crash)", False, str(exc))

        _append_jsonl(sd / "correspondence" / _INBOUND_FILE, {"reply_to": "m_retro", "text": "yes"})
        try:
            commit_prediction("m_retro", state_dir=sd)
            check("retro-prediction refused", False)
        except RetroPredictionError:
            check("retro-prediction refused", True)

        sd2 = Path(tempfile.mkdtemp())
        for i in range(MAX_PENDING):
            commit_prediction(f"cap_{i}", state_dir=sd2)
        try:
            commit_prediction("cap_over", state_dir=sd2)
            check("cadence cap enforced", False)
        except CorrespondenceCapReachedError:
            check("cadence cap enforced", True)

        _append_jsonl(sd / "correspondence" / _INBOUND_FILE, {"reply_to": "m1", "text": "Yes, that works for me."})
        resolutions = ingest_replies(systems={}, state_dir=sd)
        check("ingest_replies resolves a matched reply", len(resolutions) == 1 and resolutions[0]["message_id"] == "m1")
        check("mismatch is a real float in range", 0.0 <= resolutions[0]["mismatch"] <= 1.0)

        again = ingest_replies(systems={}, state_dir=sd)
        check("already-resolved reply is not reprocessed", len(again) == 0)

        sd3 = Path(tempfile.mkdtemp())
        old = commit_prediction("old_one", state_dir=sd3)
        chain_path = sd3 / "correspondence" / _PENDING_FILE
        # Re-hash after backdating committed_at -- mutating the field
        # without recomputing entry_hash would (correctly) read as
        # tampering, not as "time passed", and get frozen instead of aged.
        backdated = old.to_dict()
        backdated["committed_at"] = time.time() - EXPIRY_SECONDS - 100
        payload_for_hash = dict(backdated)
        payload_for_hash.pop("entry_hash", None)
        backdated["entry_hash"] = _sha256(_canonical_json(payload_for_hash))
        chain_path.write_text(json.dumps(backdated) + "\n", encoding="utf-8")
        expired = expire_stale_predictions(sd3)
        check("expiry produces unresolved with cost, no exception", len(expired) == 1 and expired[0]["resolution"] == "unresolved")

        sd4 = Path(tempfile.mkdtemp())
        commit_prediction("tamper_1", state_dir=sd4)
        chain_path4 = sd4 / "correspondence" / _PENDING_FILE
        with open(chain_path4, "a", encoding="utf-8") as f:
            f.write("not valid json at all\n")
        entries4, frozen4 = _load_pending_chain(sd4)
        check("corrupt chain line freezes rather than discarding history", frozen4 and len(entries4) == 1)
        try:
            commit_prediction("after_tamper", state_dir=sd4)
            check("commits refused while chain is frozen", False)
        except CorrespondenceChainFrozenError:
            check("commits refused while chain is frozen", True)

        draft = draft_correspondence_message({})
        check("draft returns None with no real signal source", draft is None)

        class _FakeLedger:
            def unresolved(self):
                class _Rec:
                    claim_a = "the sky is blue"
                    claim_b = "the sky is not blue"
                return [_Rec()]
        draft2 = draft_correspondence_message({"contradiction_ledger": _FakeLedger()})
        check("draft uses real contradiction content when available",
              draft2 is not None and "sky is blue" in draft2["text"])

        posted = post_correspondence_message({"contradiction_ledger": _FakeLedger()}, state_dir=sd)
        check("post_correspondence_message writes an outbound + committed prediction",
              posted is not None and pending_by_message_id(posted["message_id"], sd) is not None)
        outbound = _load_outbound_messages(sd)
        check("outbound message carries message_id + expects_reply",
              any(m.get("message_id") == posted["message_id"] and m.get("expects_reply") is True for m in outbound))

    return {"checks": results, "total": len(results), "passed": sum(1 for r in results if r["passed"])}


if __name__ == "__main__":
    print("=" * 70)
    print("AURORA CORRESPONDENCE LOOP — SELF-VERIFICATION")
    print("Authors: Sunni (Sir) Morningstar and Cael Devo")
    print("=" * 70)
    outcome = verify_correspondence_loop()
    for c in outcome["checks"]:
        status = "OK" if c["passed"] else "FAIL"
        detail = f"  [{c['detail']}]" if c.get("detail") else ""
        print(f"  [{status}] {c['test']}{detail}")
    print(f"\n{outcome['passed']}/{outcome['total']} checks passed.")
    print("=" * 70)

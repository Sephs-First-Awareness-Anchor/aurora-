#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
inquiry_tiers.py -- one inquiry, two strata (surface restructure 4b).

Her surface and her subsurface are one mind.  An inquiry opens from her own
provisional read of something (the representational resolution engine's
demand edge).  Where it is settled follows from what each stratum can do,
never from a written threshold:

  * the surface tries every perspective it can hold right now: transient
    projections of structure she already has.  That needs nothing from home,
    so it runs offline too;
  * when the surface's lenses are spent and pressure remains, what is left is
    retained growth (Build 714's field inquiry), and her retained growth lives
    at home.  The surface passes the question up, with the lived evidence
    behind it, through the durable outbox;
  * home integrates that evidence into its own genealogy as observation, so
    the pressure it feels is the pressure she lived.  Home works the questions
    in the order of its own felt pressure; a question home does not feel is
    not forced;
  * whatever home stages for a question the surface raised is handed back
    down, because the surface is where she read it and where its consequence
    arrives (what she sees, hears, does).  The surface reads the staged view,
    and every participation it lives goes up as evidence.  Home alone
    completes, retains or rejects.

Nothing here decides an answer.  The engine's own pressure, frontier and
consequence rules decide; this module only carries the question and its
evidence between the two strata of one mind.

Files (all under strata_link/, which belongs to the link on either side):
  home    inquiry_desk.json      questions the surface raised, and what home
                                 handed down for each
          inquiry_down.jsonl     what home hands down, relayed by the link
  surface inquiry_inbox.jsonl    what arrived from home, in order
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

DESK_FILENAME = "inquiry_desk.json"
DOWN_FILENAME = "inquiry_down.jsonl"
INBOX_FILENAME = "inquiry_inbox.jsonl"
DOWN_CHANNEL = "home_inquiry"

# How many raised questions home investigates in one pass.  Investigation can
# scan structure; the rest wait for the next pass in pressure order.
INVESTIGATIONS_PER_PASS = 2
_EVIDENCE_SEEN_PER_REF = 64


def _link_dir(state_dir: Any) -> Path:
    from aurora_internal.dual_strata.strata_link import link_dir
    return link_dir(state_dir)


def json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, sort_keys=True, default=str))


def pressure_dict(value: Any) -> Dict[str, Any]:
    if hasattr(value, "to_dict"):
        try:
            return dict(value.to_dict())
        except Exception:
            pass
    try:
        return dict(value or {})
    except (TypeError, ValueError):
        return {}


def evidence_id(item: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(json_safe(dict(item)), sort_keys=True).encode()).hexdigest()[:20]


def _read_lines_since(path: Path, offset: int) -> Tuple[List[Dict[str, Any]], int]:
    if not path.exists():
        return [], 0
    size = path.stat().st_size
    if offset > size:
        offset = 0
    with open(path, "rb") as handle:
        handle.seek(offset)
        data = handle.read()
    complete = data[:data.rfind(b"\n") + 1]        # a line still being written waits
    out: List[Dict[str, Any]] = []
    for raw in complete.splitlines():
        try:
            item = json.loads(raw.decode("utf-8")) if raw.strip() else None
        except ValueError:
            item = None
        if isinstance(item, dict):
            out.append(item)
    return out, offset + len(complete)


def _append_line(path: Path, record: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(json_safe(dict(record)), sort_keys=True) + "\n")


# ---------------------------------------------------------------------------
# Surface side
# ---------------------------------------------------------------------------

class SurfaceInquiryTier:
    """The surface's end of the shared inquiry.  Set on the engine module with
    ``aurora_representational_resolution.set_home_tier`` when the device runs
    as her surface; a whole-mind device or home never sets it."""

    def __init__(self, state_dir: Any) -> None:
        self.state_dir = Path(str(state_dir))
        self._inbox_offset = 0
        self.passed_up = 0
        self.evidence_sent = 0
        self.received = 0

    def pass_up(self, payload: Mapping[str, Any]) -> bool:
        from aurora_internal.dual_strata.strata_link import request_home
        out = request_home(self.state_dir, "inquiry", json_safe(dict(payload)))
        if out.get("ok"):
            self.passed_up += 1
        return bool(out.get("ok"))

    def send_evidence(self, payload: Mapping[str, Any]) -> bool:
        from aurora_internal.dual_strata.strata_link import request_home
        out = request_home(self.state_dir, "inquiry_evidence", json_safe(dict(payload)))
        if out.get("ok"):
            self.evidence_sent += 1
        return bool(out.get("ok"))

    def inbox(self) -> List[Dict[str, Any]]:
        """What home handed down since the last look, in order."""
        records, self._inbox_offset = _read_lines_since(
            _link_dir(self.state_dir) / INBOX_FILENAME, self._inbox_offset)
        self.received += len(records)
        return records

    def status(self) -> Dict[str, Any]:
        return {"passed_up": self.passed_up, "evidence_sent": self.evidence_sent,
                "received_from_home": self.received}


def receive_down(state_dir: Any, payload: Mapping[str, Any]) -> str:
    """Surface side of the downlink channel: keep what home handed down, once."""
    event_id = str(payload.get("event_id") or "")
    if not event_id:
        return "unknown_channel"
    path = _link_dir(state_dir) / INBOX_FILENAME
    tail = path.read_text(encoding="utf-8")[-200000:] if path.exists() else ""
    if f'"event_id": "{event_id}"' in tail:
        return "applied"                               # a resend changes nothing
    _append_line(path, payload)
    return "applied"


# ---------------------------------------------------------------------------
# Home side
# ---------------------------------------------------------------------------

def send_down(state_dir: Any, kind: str, payload: Mapping[str, Any]) -> Dict[str, Any]:
    record = dict(payload)
    record.update({"kind": kind, "event_id": uuid.uuid4().hex, "at": time.time()})
    _append_line(_link_dir(state_dir) / DOWN_FILENAME, record)
    return record


def relay_down(state_dir: Any, outbox: Any, memo: Dict[str, Any]) -> int:
    """Called by the link's downlink collector: what home handed down since
    the last relay goes into the durable outbox for the active surface."""
    records, offset = _read_lines_since(_link_dir(state_dir) / DOWN_FILENAME,
                                        int(memo.get("inquiry_down_offset") or 0))
    for record in records:
        outbox.append(DOWN_CHANNEL, "event", record)
    memo["inquiry_down_offset"] = offset
    return len(records)


def _stage_signature(pending: Mapping[str, Any]) -> str:
    candidate = dict(pending.get("candidate") or {})
    mode = str(pending.get("mode") or "field_inquiry")
    if candidate.get("projection_id"):
        return f"{mode}:{candidate.get('projection_id')}"
    return f"{mode}:{candidate.get('field')}={candidate.get('candidate_value')}"


def _stage_view(ref: Any, pending: Mapping[str, Any]) -> Optional[str]:
    """The provisional view the staged experiment offers, exactly as home's
    engine would offer it to a reader at home."""
    from dataclasses import replace
    candidate = dict(pending.get("candidate") or {})
    if pending.get("mode") == "perspective_projection":
        return str(candidate.get("projected_ref") or "") or None
    field = str(candidate.get("field") or "")
    if not field or getattr(ref, field, None) is not None:
        return None
    try:
        return replace(ref, **{field: candidate.get("candidate_value")}).encode()
    except Exception:
        return None


class HomeInquiryDesk:
    """Home's end of the shared inquiry: the questions her surface raised,
    worked in the order of home's own felt pressure."""

    def __init__(self, state_dir: Any, systems: Optional[Dict[str, Any]] = None) -> None:
        self.state_dir = Path(str(state_dir))
        self.systems = systems if systems is not None else {}
        self.questions: Dict[str, Dict[str, Any]] = {}
        self.handed_down = 0
        self.closed = 0
        self._load()

    # -- persistence ---------------------------------------------------------
    def _path(self) -> Path:
        return _link_dir(self.state_dir) / DESK_FILENAME

    def _load(self) -> None:
        try:
            data = json.loads(self._path().read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if isinstance(data, dict) and isinstance(data.get("questions"), dict):
            self.questions = data["questions"]

    def _save(self) -> None:
        from aurora_internal.dual_strata.strata_link import _atomic_write_json
        _atomic_write_json(self._path(), {"questions": self.questions, "at": time.time()})

    def engine(self):
        from aurora_representational_resolution import get_or_create_engine
        engine = get_or_create_engine(self.systems)
        if engine is not None:
            engine._is_home = True          # home works its own questions, never passes up
        return engine

    # -- what the surface sent ----------------------------------------------
    def take(self, request: Mapping[str, Any]) -> str:
        kind = str(request.get("kind") or "")
        payload = dict(request.get("payload") or {})
        if kind == "inquiry":
            return self._take_question(payload, str(request.get("from") or ""))
        if kind == "inquiry_evidence":
            return self._take_evidence(payload, str(request.get("from") or ""))
        return "not_inquiry"

    def _observe(self, engine, ref, item: Mapping[str, Any], *, surface: str) -> bool:
        try:
            engine.record_pressure_observation(
                ref,
                pressure_before=dict(item.get("pressure_before") or {}),
                pressure_after=dict(item.get("pressure_after") or {}),
                source=f"surface:{item.get('source') or 'lived'}",
                context_tag=str(item.get("context_tag") or ""),
                notes={"lived_on_surface": surface or True},
                consumer="surface_observer",
            )
            return True
        except Exception:
            return False

    def _take_question(self, payload: Dict[str, Any], surface: str) -> str:
        from aurora_representational_address import RepresentationalRef
        key = str(payload.get("ref") or "")
        try:
            ref = RepresentationalRef.decode(key)
        except Exception:
            return "unreadable_ref"
        question = self.questions.setdefault(key, {
            "ref": key, "raised_at": time.time(), "evidence_seen": [],
            "handed_down": None, "surface": surface,
        })
        question.update({
            "consumer": payload.get("consumer"), "context_scope": payload.get("context_scope"),
            "surface_pressure": payload.get("pressure"), "frontier": payload.get("frontier"),
            "last_raised_at": time.time(), "surface": surface or question.get("surface"),
        })
        engine = self.engine()
        seen = list(question.get("evidence_seen") or [])
        if engine is not None:
            for item in list(payload.get("evidence") or []):
                eid = evidence_id(item)
                if eid in seen:
                    continue
                if self._observe(engine, ref, item, surface=surface):
                    seen.append(eid)
        question["evidence_seen"] = seen[-_EVIDENCE_SEEN_PER_REF:]
        self._save()
        return "raised"

    def _take_evidence(self, payload: Dict[str, Any], surface: str) -> str:
        from aurora_representational_address import RepresentationalRef
        key = str(payload.get("ref") or "")
        question = self.questions.get(key)
        engine = self.engine()
        try:
            ref = RepresentationalRef.decode(key)
        except Exception:
            return "unreadable_ref"
        if engine is None:
            return "no_engine"
        handed = dict((question or {}).get("handed_down") or {})
        pending = engine._active_stage_for_ref.get(key)
        if (not handed or handed.get("inquiry_id") != payload.get("inquiry_id")
                or pending is None or _stage_signature(pending) != handed.get("signature")):
            # Home no longer holds that experiment (it closed, expired or home
            # restarted).  Her lived consequence still counts as observation.
            self._observe(engine, ref, payload, surface=surface)
            if question is not None and handed.get("inquiry_id") == payload.get("inquiry_id"):
                self._close(key, question, outcome="no_longer_held_at_home")
            else:
                send_down(self.state_dir, "closed", {"ref": key,
                          "inquiry_id": payload.get("inquiry_id"),
                          "outcome": "no_longer_held_at_home"})
            self._save()
            return "observed"

        reads = int(payload.get("provisional_reads") or 0)
        if reads > 0:
            engine._provisional_reads[key] = int(engine._provisional_reads.get(key, 0) or 0) + reads
        effect = dict(payload.get("downstream_effect") or {})
        if effect.get("downstream_difference_produced") is not None:
            engine.record_candidate_downstream_effect(
                ref,
                consumer=f"surface:{effect.get('consumer') or 'reader'}",
                downstream_difference=effect.get("downstream_difference_produced"),
                action_or_prediction_affected=effect.get("action_prediction_affected") or "surface",
                baseline_expectation=effect.get("baseline_expectation"),
                conditioned_expectation=effect.get("conditioned_expectation"),
                metadata={**dict(effect.get("metadata") or {}), "lived_on_surface": surface or True},
            )
        engine.record_participation(
            ref,
            pressure_before=dict(payload.get("pressure_before") or {}),
            pressure_after=dict(payload.get("pressure_after") or {}),
            source=f"surface:{payload.get('source') or 'lived'}",
            context_tag=str(payload.get("context_tag") or ""),
            notes={"lived_on_surface": surface or True},
            consumer=str(payload.get("consumer") or "surface"),
            candidate_evaluation=payload.get("candidate_evaluation"),
        )
        if question is not None:
            self._settle_if_due(key, question, self._follow(key, question, engine))
        self._save()
        return "applied"

    # -- home's own pass -------------------------------------------------------
    def _last_outcome(self, engine, key: str, mode: str) -> str:
        projection = [(e, "ref", "outcome") for e in (getattr(engine, "_projection_events", None) or [])]
        field = [(e, "ref_before_encoded", "outcome")
                 for e in (getattr(engine, "_resolution_events", None) or [])]
        for events in ((projection, field) if mode == "perspective_projection" else (field, projection)):
            for event, ref_key, outcome_key in reversed(events):
                if str(event.get(ref_key) or "") == key and event.get(outcome_key):
                    return str(event.get(outcome_key))
        return "closed"

    def _close(self, key: str, question: Dict[str, Any], *, outcome: str) -> None:
        handed = dict(question.get("handed_down") or {})
        send_down(self.state_dir, "closed", {"ref": key, "inquiry_id": handed.get("inquiry_id"),
                                             "outcome": outcome})
        question["handed_down"] = None
        question["last_outcome"] = outcome
        self.closed += 1

    def _hand_down(self, key: str, question: Dict[str, Any], pending: Mapping[str, Any], ref) -> None:
        view = _stage_view(ref, pending)
        if not view:
            return
        inquiry_id = uuid.uuid4().hex
        signature = _stage_signature(pending)
        send_down(self.state_dir, "stage", {
            "ref": key, "inquiry_id": inquiry_id, "view": view,
            "stage_mode": str(pending.get("mode") or "field_inquiry"),
            "candidate": json_safe(dict(pending.get("candidate") or {})),
            "consumer": pending.get("consumer"), "context_scope": pending.get("context_scope"),
        })
        question["handed_down"] = {"inquiry_id": inquiry_id, "signature": signature, "at": time.time()}
        question["ever_staged"] = True
        self.handed_down += 1

    def _follow(self, key: str, question: Dict[str, Any], engine) -> bool:
        """Keep what the surface holds in step with what home holds.  Returns
        True when it told the surface an experiment closed."""
        if not question:
            return False
        closed = False
        from aurora_representational_address import RepresentationalRef
        ref = RepresentationalRef.decode(key)
        pending = engine._active_stage_for_ref.get(key)
        handed = dict(question.get("handed_down") or {})
        if handed and (pending is None or _stage_signature(pending) != handed.get("signature")):
            mode = str(handed.get("signature") or "").split(":", 1)[0]
            self._close(key, question, outcome=self._last_outcome(engine, key, mode))
            closed = True
        if pending is not None and not question.get("handed_down"):
            self._hand_down(key, question, pending, ref)
        if pending is None and engine.inadequacy_pressure(ref) <= 0.0:
            question["settled"] = True
        return closed

    def _settle_if_due(self, key: str, question: Dict[str, Any], closed_now: bool) -> None:
        if not question.pop("settled", False):
            return
        # Home feels no inadequacy here (any more).  Nothing is forced; the
        # surface may raise it again with new lived evidence.
        if not closed_now:
            outcome = "settled_at_home" if question.get("ever_staged") else "not_felt_at_home"
            self._close(key, question, outcome=outcome)
        self.questions.pop(key, None)

    def tick(self) -> Dict[str, Any]:
        """Work the raised questions in the order of home's own felt pressure."""
        engine = self.engine()
        if engine is None or not self.questions:
            return {"questions": len(self.questions)}
        from aurora_representational_address import RepresentationalRef
        ranked = []
        for key, question in list(self.questions.items()):
            try:
                ref = RepresentationalRef.decode(key)
            except Exception:
                self.questions.pop(key, None)
                continue
            ranked.append((engine.inadequacy_pressure(ref), key, ref, question))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        investigated = 0
        for pressure, key, ref, question in ranked:
            pending = engine._active_stage_for_ref.get(key)
            if pending is None and pressure > 0.0 and investigated < INVESTIGATIONS_PER_PASS:
                investigated += 1
                engine.investigate_if_pressured(
                    ref, consumer=f"surface:{question.get('consumer') or 'reader'}",
                    context_scope=question.get("context_scope"))
            self._settle_if_due(key, question, self._follow(key, question, engine))
        self._save()
        return self.status()

    def status(self) -> Dict[str, Any]:
        return {"questions": len(self.questions), "handed_down": self.handed_down,
                "closed": self.closed,
                "holding": sorted(k for k, q in self.questions.items() if q.get("handed_down"))}

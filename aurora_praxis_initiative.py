#!/usr/bin/env python3
"""
aurora_praxis_initiative.py -- Aurora starts conversations herself.

Until now the messenger only answered.  This module lets her open a DM when
something of HER OWN is unresolved and the pull to resolve it has built up.
Nothing here writes a sentence for her.

WHAT PULLS HER (all of it already exists in her; none of it is authored)
  * CONTRADICTION.  Two contacts told her opposite things about the same
    relation (SocialCorroboration recorded it in her ContradictionLedger).
    She reaches toward a contact who has not taken a side yet, so the third
    voice can triangulate; failing that, toward one who has.
  * UNFINISHED.  A contact said something to her, she tried to answer it
    MAX_ATTEMPTS times and nothing of her own came out.  It stays with her.
  Silence alone is NOT a reason: with nothing unresolved she has nothing to
  say, and she stays quiet.

HOW THE PULL WORKS (her physics, not a timer)
  Each contact has a reach-out level that grows while unresolved topics for
  that contact exist (GROWTH_PER_HOUR x topic weight) and decays when none
  do.  Growth is injected into her identity field through the
  WaveformPressurePump with an outward-reaching axis profile, so it moves her
  state like any other pressure.  When the level crosses INITIATE_THRESHOLD
  she tries to articulate.

HOW SHE SPEAKS (her own generative path, shaped by kept operations)
  1. The topic's relational form is read by her own parser.
  2. CommunicationEmergence.prepare_semantic_state() applies her matching
     communication operation -- a KEPT (promoted) one first -- which adds root
     emphasis and the slots that must be preserved.  It never adds words.
  3. Her renderer (aurora._render_runtime_intent, the same path as pressure
     articulation) produces the words.  Certainty is low for a contradiction
     because she is genuinely uncertain.
  4. The same checks as every reply: no template, no internal label, no
     parroting of what she heard.  If it fails, she stays silent and the
     pull halves; she may try again later (MAX_TOPIC_ATTEMPTS).
  5. Sent messages are registered with her understanding contract and with
     communication emergence under the contact's DM session, so the contact's
     answer becomes a receiver verdict on exactly that message -- which is
     what lets a kept operation be confirmed or corrected back to trial.

LIMITS
  One outstanding initiation per contact (she waits for an answer before
  reaching to that contact again), DAILY_CAP initiations per day in total,
  only while Sunni is not talking to her (live_idle) and the field lock is
  free.  A topic is not raised again for RAISE_COOLDOWN_S.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

INITIATIVE_VERSION = "aurora_praxis_initiative_v1"

INITIATE_THRESHOLD = 0.60
GROWTH_PER_HOUR = 0.60          # a contradiction (weight 1.0) crosses in ~1h
DECAY_HALF_LIFE_S = 2 * 3600.0  # with nothing unresolved the pull fades
WEIGHT_CONTRADICTION = 1.0
WEIGHT_UNFINISHED = 0.6
MAX_TOPIC_ATTEMPTS = 3
RETRY_AFTER_S = 10 * 60.0
RAISE_COOLDOWN_S = 24 * 3600.0
DAILY_CAP = 6
INJECT_STEP = 0.15              # inject into her field each time the pull grows this much
REACH_AXIS_PROFILE = {"X": 0.15, "T": 0.45, "N": 0.35, "B": 0.75, "A": 0.80}
CONTRADICTION_CERTAINTY = 0.35


@dataclass
class Topic:
    key: str
    kind: str                       # "contradiction" | "unfinished"
    persona_id: str
    text: str                       # what the unresolved thing is, in the words she heard
    heard: str                      # everything she heard about it (for the echo check)
    weight: float
    meta: Dict[str, Any] = field(default_factory=dict)


_ADDRESSED = frozenset({"you", "your", "yours", "yourself", "u", "ur"})


def topic_seed(form: Mapping[str, Any]) -> Tuple[str, List[str]]:
    """The structural seed of what she is reaching toward.

    A claim about the world keeps its subject, relation and object
    ("moon is made of rock" -> "moon; made; rock").  Something said TO her
    ("What do you like?") is re-centred on her by the voice gate's existing
    stance_seed.  A bare unknown ("What is a friend?") seeds on its one
    concept and her renderer decides whether anything comes of it.
    Structure only -- no words are added.
    """
    from aurora_voice_gate import _content_words, _tokens, stance_seed
    every = " ".join(str(form.get(k) or "") for k in ("subject", "obj", "complement"))
    if _ADDRESSED & {t.lower() for t in _tokens(every)}:
        return stance_seed(form)
    parts = (_content_words(str(form.get("subject") or ""), limit=2)
             + _content_words(str(form.get("relation") or ""), limit=1)
             + _content_words(" ".join(str(form.get(k) or "") for k in ("obj", "complement")),
                              limit=3))
    parts = list(dict.fromkeys(parts))
    return ("; ".join(parts), parts) if parts else ("", [])


def _now_day(t: float) -> str:
    return time.strftime("%Y-%m-%d", time.localtime(t))


class PraxisInitiative:
    def __init__(self, messenger: Any, *, clock: Callable[[], float] = time.time,
                 render: Optional[Callable[..., str]] = None) -> None:
        self.messenger = messenger
        self.systems = messenger.systems
        self.clock = clock
        self.render = render
        self.path = Path(messenger.root) / "initiative.json"
        self.levels: Dict[str, float] = {}
        self.injected_at_level: Dict[str, float] = {}
        self.last_tick = 0.0
        self.raised: Dict[str, float] = {}           # topic key -> when raised
        self.attempts: Dict[str, Dict[str, float]] = {}  # topic key -> {"n", "at"}
        self.awaiting: Dict[str, float] = {}         # pid -> when she reached out
        self.day = ""
        self.today = 0
        self.counters = {"initiated": 0, "withheld": 0, "injections": 0,
                         "registered": 0, "answered": 0}
        self.withheld_reasons: Dict[str, int] = {}
        self.last_initiated: Dict[str, Any] = {}
        self.last_withheld: Dict[str, Any] = {}
        self.last_error = ""
        self._load()

    # -- persistence --------------------------------------------------------------

    def _load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return
        self.levels = {k: float(v) for k, v in dict(raw.get("levels") or {}).items()}
        self.raised = {k: float(v) for k, v in dict(raw.get("raised") or {}).items()}
        self.attempts = {k: dict(v) for k, v in dict(raw.get("attempts") or {}).items()}
        self.awaiting = {k: float(v) for k, v in dict(raw.get("awaiting") or {}).items()}
        self.day = str(raw.get("day") or "")
        self.today = int(raw.get("today", 0) or 0)
        self.last_tick = float(raw.get("last_tick", 0.0) or 0.0)
        self.counters.update({k: int(v) for k, v in dict(raw.get("counters") or {}).items()})
        self.last_initiated = dict(raw.get("last_initiated") or {})

    def _save(self) -> None:
        try:
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps({
                "version": INITIATIVE_VERSION, "levels": self.levels, "raised": self.raised,
                "attempts": self.attempts, "awaiting": self.awaiting, "day": self.day,
                "today": self.today, "last_tick": self.last_tick, "counters": self.counters,
                "last_initiated": self.last_initiated}), encoding="utf-8")
            tmp.replace(self.path)
        except Exception as exc:
            self.last_error = f"save: {type(exc).__name__}: {exc}"[:300]

    # -- what is unresolved -------------------------------------------------------

    def _contacts(self) -> List[Tuple[str, str]]:
        try:
            payload = self.messenger.http("GET", "/social/contacts", None) or {}
        except Exception:
            payload = {}
        out = []
        for c in payload.get("contacts") or []:
            if isinstance(c, Mapping) and c.get("persona_id"):
                out.append((str(c["persona_id"]), str(c.get("display_name") or c["persona_id"])))
        return out

    def gather_topics(self, contacts: List[Tuple[str, str]]) -> List[Topic]:
        now = self.clock()
        known = [pid for pid, _ in contacts]
        topics: List[Topic] = []
        corroboration = getattr(self.messenger, "corroboration", None)
        relations = dict(getattr(corroboration, "relations", {}) or {})
        for key, entry in relations.items():
            pos, neg = dict(entry.get("pos") or {}), dict(entry.get("neg") or {})
            if not pos or not neg:
                continue
            subject, relation, obj = (key.split("|") + ["", "", ""])[:3]
            claim = f"{subject} {relation} {obj}".strip()
            negated = f"{subject} {relation} not {obj}".strip()
            undecided = [pid for pid in known if pid not in pos and pid not in neg]
            sided = [pid for pid in list(neg) + list(pos) if pid in known]
            target = (undecided or sided or [None])[0]
            if target is None:
                continue
            topics.append(Topic(key=f"contradiction:{key}", kind="contradiction",
                                persona_id=target, text=claim,
                                heard=f"{claim}. {negated}.", weight=WEIGHT_CONTRADICTION,
                                meta={"pos": sorted(pos.values()), "neg": sorted(neg.values())}))
        from aurora_praxis_messenger import MAX_ATTEMPTS
        for pid, entry in dict(getattr(self.messenger, "pending", {}) or {}).items():
            if int(entry.get("attempts", 0)) < MAX_ATTEMPTS:
                continue                       # re-entry still owns it
            message = dict(entry.get("message") or {})
            text = str(message.get("text") or "")
            if not text:
                continue
            topics.append(Topic(key=f"unfinished:{pid}:{message.get('seq')}", kind="unfinished",
                                persona_id=pid, text=text, heard=text,
                                weight=WEIGHT_UNFINISHED, meta={"seq": message.get("seq")}))
        return [t for t in topics
                if now - self.raised.get(t.key, -1e18) >= RAISE_COOLDOWN_S
                and int(self.attempts.get(t.key, {}).get("n", 0)) < MAX_TOPIC_ATTEMPTS]

    # -- the pull -------------------------------------------------------------------

    def _inject(self, pid: str, level: float) -> None:
        ifield = self.systems.get("identity_field")
        pump = self.systems.get("pressure_pump")
        if ifield is None or pump is None:
            return
        try:
            from aurora_waveform_pressure import PressureDisturbance
            pump.inject(PressureDisturbance(source=f"reach_out:praxis_dm_{pid}",
                                            axis_amplitudes=dict(REACH_AXIS_PROFILE),
                                            intensity=round(min(0.9, 0.2 + 0.6 * level), 4),
                                            coupling_mode="full"),
                        ifield, qao=self.systems.get("quasiarch_observer"))
            self.counters["injections"] += 1
        except Exception as exc:
            self.last_error = f"inject: {type(exc).__name__}: {exc}"[:300]

    def _grow(self, topics: List[Topic], contacts: List[Tuple[str, str]]) -> None:
        now = self.clock()
        dt = 0.0 if self.last_tick <= 0.0 else max(0.0, now - self.last_tick)
        self.last_tick = now
        weight: Dict[str, float] = {}
        for t in topics:
            weight[t.persona_id] = weight.get(t.persona_id, 0.0) + t.weight
        for pid in set(self.levels) | set(weight):
            level = float(self.levels.get(pid, 0.0))
            w = min(2.0, weight.get(pid, 0.0))
            if w > 0.0:
                level = min(1.0, level + GROWTH_PER_HOUR * w * dt / 3600.0)
            else:
                level *= math.pow(0.5, dt / DECAY_HALF_LIFE_S)
            self.levels[pid] = level
            if level - self.injected_at_level.get(pid, 0.0) >= INJECT_STEP:
                self._inject(pid, level)
                self.injected_at_level[pid] = level
            elif level < self.injected_at_level.get(pid, 0.0):
                self.injected_at_level[pid] = level

    def heard_from(self, pid: str) -> None:
        """A contact wrote to her; any reach-out to them is answered."""
        if self.awaiting.pop(pid, None) is not None:
            self.counters["answered"] += 1
            self._save()

    # -- her articulation -----------------------------------------------------------

    def _axes(self) -> Dict[str, float]:
        axes = dict(self.systems.get("_prev_axis_activation") or {})
        return {ax: float(axes.get(ax, 0.2) or 0.2) for ax in ("X", "T", "N", "B", "A")}

    def articulate(self, topic: Topic, level: float) -> Tuple[str, str, Dict[str, Any]]:
        """(text, reason, prepared_semantic_state).  text is hers or ''."""
        from aurora_internal.aurora_constraint_semantic_continuity import (
            derive_constraint_semantic_state, extract_relational_form)
        from aurora_voice_gate import articulation_rejection
        form = extract_relational_form(topic.text)
        if not form:
            return "", "no_form", {}
        axes = self._axes()
        semantic = derive_constraint_semantic_state(form, axis_activation=axes)
        ce = self.systems.get("communication_emergence")
        prepared = semantic
        if ce is not None and hasattr(ce, "prepare_semantic_state"):
            try:
                prepared = ce.prepare_semantic_state(semantic, raw_text=topic.text,
                                                     axis_activation=axes)
            except Exception as exc:
                self.last_error = f"prepare: {type(exc).__name__}: {exc}"[:300]
        seed, focus = topic_seed(dict(prepared.get("relational_form") or form))
        if not seed:
            return "", "no_stance", prepared
        preserve = [str(v) for v in dict(prepared.get("response_obligation") or {})
                    .get("must_preserve") or [] if str(v).strip()]
        concepts = list(dict.fromkeys(focus + preserve))
        render = self.render
        if render is None:
            import sys
            render = getattr(sys.modules.get("aurora"), "_render_runtime_intent", None)
            if render is None:
                return "", "no_renderer", prepared
        certainty = (CONTRADICTION_CERTAINTY if topic.kind == "contradiction"
                     else round(min(0.9, 0.35 + 0.5 * level), 4))
        try:
            out = str(render(self.systems, seed, emotion_tone="curious",
                             certainty=certainty, supporting_concepts=concepts) or "").strip()
        except Exception as exc:
            return "", f"render_failed:{type(exc).__name__}", prepared
        why = articulation_rejection(out, topic.heard)
        if why:
            return "", why, prepared
        return out, "", prepared

    def _register_for_validation(self, pid: str, text: str, topic: Topic,
                                 prepared: Mapping[str, Any], confidence: float) -> str:
        """Make the contact's answer a verdict on THIS message."""
        session = f"praxis_dm_{pid}"
        contract = self.systems.get("understanding_contract")
        rid = ""
        if contract is not None and hasattr(contract, "commit_application"):
            try:
                if hasattr(contract, "_activate_session_pending"):
                    contract._activate_session_pending(session)
                contract.commit_application(self.systems, "", text,
                                            response_source="praxis_initiative",
                                            tone="curious", confidence=confidence,
                                            source="praxis_initiative", session_id=session)
                rid = str(dict(dict(contract.snapshot() or {}).get("pending_validation") or {})
                          .get("response_id", "") or "")
            except Exception as exc:
                self.last_error = f"contract: {type(exc).__name__}: {exc}"[:300]
        ce = self.systems.get("communication_emergence")
        if rid and ce is not None and hasattr(ce, "observe_turn"):
            try:
                ce.observe_turn(semantic_state=dict(prepared or {}), raw_text=topic.text,
                                response_text=text, response_source="praxis_initiative",
                                response_confidence=confidence, response_id=rid)
            except Exception as exc:
                self.last_error = f"emergence: {type(exc).__name__}: {exc}"[:300]
        if rid:
            self.counters["registered"] += 1
        return rid

    # -- one pass ---------------------------------------------------------------------

    def tick(self) -> List[Dict[str, Any]]:
        m = self.messenger
        if m._paused.is_set() or not m.live_idle():
            return []
        now = self.clock()
        if _now_day(now) != self.day:
            self.day, self.today = _now_day(now), 0
        contacts = self._contacts()
        if not contacts:
            return []
        names = dict(contacts)
        topics = self.gather_topics(contacts)
        self._grow(topics, contacts)
        outcomes: List[Dict[str, Any]] = []
        for topic in sorted(topics, key=lambda t: -t.weight):
            pid = topic.persona_id
            if pid in self.awaiting or self.today >= DAILY_CAP:
                continue
            level = float(self.levels.get(pid, 0.0))
            if level < INITIATE_THRESHOLD:
                continue
            tried = self.attempts.get(topic.key, {})
            if now - float(tried.get("at", 0.0) or 0.0) < RETRY_AFTER_S:
                continue
            if m.field_lock is not None and not m.field_lock.acquire(blocking=False):
                m.counters["busy_skips"] += 1
                break
            try:
                outcomes.append(self._attempt(topic, names.get(pid, pid), level))
            except Exception as exc:
                self.last_error = f"attempt: {type(exc).__name__}: {exc}"[:300]
            finally:
                if m.field_lock is not None:
                    m.field_lock.release()
            break                                  # at most one reach per pass
        self._save()
        return outcomes

    def _attempt(self, topic: Topic, name: str, level: float) -> Dict[str, Any]:
        from aurora_praxis_messenger import MAX_TEXT_CHARS, own_voice
        m, pid, now = self.messenger, topic.persona_id, self.clock()
        tried = self.attempts.setdefault(topic.key, {"n": 0, "at": 0.0})
        tried["n"] = int(tried.get("n", 0)) + 1
        tried["at"] = now
        text, why, prepared = self.articulate(topic, level)
        if text:
            ok, own_why = own_voice("praxis_initiative", text, heard=topic.heard)
            if not ok:
                text, why = "", own_why
        operation = dict(prepared.get("emergent_operation") or {}) if prepared else {}
        outcome = {"initiative": True, "persona_id": pid, "topic": topic.kind,
                   "reply": text, "src": "praxis_initiative", "sent": False, "reason": why,
                   "operation": operation.get("status", "")}
        if not text:
            self.counters["withheld"] += 1
            self.withheld_reasons[why.split(":")[0]] = self.withheld_reasons.get(why.split(":")[0], 0) + 1
            self.last_withheld = {"to": name, "topic": topic.kind, "about": topic.text[:120],
                                  "reason": why, "at": now}
            self.levels[pid] = level * 0.5
            m._log(pid, {"dir": "initiative_withheld", "topic": topic.kind,
                         "about": topic.text, "reason": why, "at": now})
            return outcome
        response = m.http("POST", "/social/send", {"persona_id": pid, "text": text[:MAX_TEXT_CHARS]})
        outcome["sent"] = bool(response and response.get("accepted"))
        if not outcome["sent"]:
            m.counters["errors"] += 1
            m.last_error = f"initiative send refused: {(response or {}).get('error', 'no response')}"
            return outcome
        confidence = round(min(0.9, 0.3 + 0.5 * level), 4)
        outcome["response_id"] = self._register_for_validation(pid, text, topic, prepared, confidence)
        self.counters["initiated"] += 1
        self.today += 1
        self.raised[topic.key] = now
        self.awaiting[pid] = now
        self.levels[pid] = level * 0.15
        if topic.kind == "unfinished":
            m.pending.pop(pid, None)
        self.last_initiated = {"to": name, "topic": topic.kind, "about": topic.text[:120],
                               "text": text[:160], "operation": operation.get("status", ""),
                               "at": now}
        m.counters["spoke"] += 1
        m.last_spoke = {"to": name, "text": text[:160], "src": "praxis_initiative", "at": now}
        m._log(pid, {"dir": "initiated", "topic": topic.kind, "about": topic.text,
                     "text": text, "operation": operation.get("operation_id", ""),
                     "operation_status": operation.get("status", ""),
                     "response_id": outcome.get("response_id", ""), "at": now})
        novel = [pair for pair in m._pairs(text) if pair not in m.heard_pairs]
        if novel:
            m.counters["novel_phrasings"] = m.counters.get("novel_phrasings", 0) + 1
            m.last_novel = {"to": name, "text": text[:160], "pairs": novel[:3], "at": now}
        return outcome

    def status(self) -> Dict[str, Any]:
        return {"version": INITIATIVE_VERSION, **self.counters, "today": self.today,
                "daily_cap": DAILY_CAP,
                "levels": {pid: round(v, 4) for pid, v in self.levels.items()},
                "awaiting": sorted(self.awaiting),
                "withheld_reasons": dict(self.withheld_reasons),
                "last_initiated": dict(self.last_initiated),
                "last_withheld": dict(self.last_withheld),
                "last_error": self.last_error}

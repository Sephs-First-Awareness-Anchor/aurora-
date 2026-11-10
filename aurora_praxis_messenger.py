#!/usr/bin/env python3
"""
aurora_praxis_messenger.py -- Aurora's side of the Praxis messenger.

Praxis hosts her contacts (ChatGPT, Gemini, Claude) in praxis_social.py.  This
module is the only Aurora code that knows they exist.  It does three things:

    1. HEAR.   Pulls messages addressed to her and runs each one through her
               own comprehension -- process_external_user_turn(), the same
               canonical door Sunni's words take -- so whatever she learns,
               she learns with her own understanding.
    2. SPEAK.  If what she produces in response is HER OWN expression, it is
               sent back.  Scripted fallbacks never leave: a template is not
               her voice, and her friends would only be hearing the template.
    3. KNOW WHO SPOKE.  Everything heard is attributed to the partner who
               said it, never to Sunni.  "I'm Claude" must not become
               "User's name is Claude".

THE RULE ON THIS WIRE: NO FORCING
=================================

Partners may explain, correct, disagree and share what they know (Sunni,
2026-11-06).  They may not reach past their words.  That is held here by
schema, duplicated on purpose rather than imported from Praxis (two locks, as
with aurora_praxis_bridge.py):

    IN : exactly seq, persona_id, display_name, text, sent_at.
    OUT: exactly persona_id, text, in_reply_to.

A message with any other key is dropped whole and counted.  What she hears
enters as speech; her contradiction ledger, curiosity and research decide
what -- if anything -- it changes.  Facts a partner states are recorded as
that partner's claims at moderate confidence, not as truths.

YIELDING
========

Sunni outranks every partner.  The loop only runs when the live path is idle
(the same predicate historical experience and the Praxis bridge use), takes
the shared field lock NON-blockingly, and leaves a message unread for the next
pass rather than ever waiting on the lock.

KNOWN LIMIT
===========

Speaker attribution is applied at conversation memory, the place identity and
facts are filed.  Deeper subsystems that still say "user" internally treat a
partner turn as an external turn, which is what it is.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

import contextlib
import json
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Mapping, Optional, Tuple

MESSENGER_VERSION = "aurora_praxis_messenger_v1"

# -- the duplicated fence (deliberately NOT imported from praxis_social) -------

MESSAGE_KEYS = frozenset({"seq", "persona_id", "display_name", "text", "sent_at"})
MAX_TEXT_CHARS = 1200

DEFAULT_ENDPOINT = "http://127.0.0.1:8787"
POLL_S = 15.0
# While a contact's message is waiting unread, look again this often (it is
# a cheap local HTTP call; only the turn itself waits for the field).
WAITING_POLL_S = 3.0
HTTP_TIMEOUT_S = 6.0
PULL_LIMIT = 20
TRANSCRIPT_DIR = "messenger"

# Sources whose text is a fixed template, a regex-triggered fill-in, a
# command handler, or copied outside text -- not her own composed expression.
# Audited against every response_src in the tree on 2026-11-06 (and caught
# live: "relational_role" answered "Who made you?" with
# f"My creator is {name}." in the first real end-to-end run).  This is a
# deny-list, so it can only grow: the withheld log
# (<state_dir>/praxis/messenger/<contact>.jsonl) shows every blocked reply and
# its source, which is how the next one gets found.
SCRIPTED_SOURCES = frozenset({
    # boundary / abstain templates (aurora._ABSTAIN_FORM_SOURCES)
    "constraint_abstain", "constraint_seek", "honest_abstain", "comprehension_gap",
    # clarification and role/identity fill-ins
    "user_context_clarification", "relational_role", "identity",
    # command handlers and session controls
    "context_control", "session_continuity", "memory_sweep", "tool_dispatch",
    "teaching",
    # outside text returned verbatim, not her words
    "search",
})

# Openings of every hard-coded reply string found in the tree (2026-11-06).
# If her reply starts like one of these, it is the template talking.
TEMPLATE_PREFIXES: Tuple[str, ...] = (
    "my best read on that",
    "i don't have a clear sense of that",
    "i do not have a clear sense of that",
    "do you mean ",
    "i hear that you are saying",
    "i understand what you are saying",
    "i understand the relation",
    "i've been thinking about",
    "i just learned more about",
    "i feel a peak in resonance",
    "aurora is still initializing",
    "i'm mid curiosity session",
    "i'm out playing",
    "curiosity session stopping",
    "play session stopping",
)


try:   # the voice gate is the single source of truth for what is scripted
    from aurora_voice_gate import (SCRIPTED_CONVERSATIONAL_SOURCES as _GATE_SCRIPTED,
                                   SYSTEM_OUTPUT_SOURCES as _GATE_SYSTEM,
                                   TEMPLATE_PREFIXES as _GATE_PREFIXES,
                                   ARTICULATION_THRESHOLD, addressed_pressure)
    SCRIPTED_SOURCES = frozenset(SCRIPTED_SOURCES | _GATE_SCRIPTED | _GATE_SYSTEM)
    TEMPLATE_PREFIXES = tuple(dict.fromkeys(TEMPLATE_PREFIXES + _GATE_PREFIXES))
except Exception:  # pragma: no cover - gate missing: the local lists still hold
    ARTICULATION_THRESHOLD = 0.30
    addressed_pressure = None  # type: ignore[assignment]

# Re-entry: an unanswered message is revisited while pressure builds.
REENTRY_AFTER_S = 120.0
SEND_RETRY_AFTER_S = 30.0  # Retry transport, never cognitive composition.
MAX_ATTEMPTS = 3


class MessengerContractBreach(ValueError):
    pass


def validate_incoming_message(payload: Any) -> Dict[str, Any]:
    """Exactly the contract, or nothing."""
    if not isinstance(payload, Mapping):
        raise MessengerContractBreach("message must be an object")
    if set(payload) != MESSAGE_KEYS:
        raise MessengerContractBreach(
            f"message keys {sorted(payload)} != contract {sorted(MESSAGE_KEYS)}")
    text = payload.get("text")
    if not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT_CHARS:
        raise MessengerContractBreach("message text malformed")
    persona_id = payload.get("persona_id")
    if not isinstance(persona_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", persona_id):
        raise MessengerContractBreach("persona_id malformed")
    try:
        seq = int(payload["seq"])
        sent_at = float(payload["sent_at"])
    except Exception:
        raise MessengerContractBreach("seq/sent_at malformed")
    name = str(payload.get("display_name") or persona_id).strip()[:40] or persona_id
    return {"seq": seq, "persona_id": persona_id, "display_name": name,
            "text": text.strip(), "sent_at": sent_at}


# -- her own voice, or silence --------------------------------------------------

def _mirror_reply_form(src: str, text: str) -> str:
    """Same rule as aurora._reply_form, for when aurora isn't loaded (tests)."""
    low = str(text or "").strip().lower()
    if src in SCRIPTED_SOURCES:
        return "boundary"
    if low.startswith("my best read"):
        return "hedged_read"
    if low.startswith("i understand what you are saying") or low.startswith("i understand the relation"):
        return "acknowledgement"
    if low.startswith("i hear that you are saying") or "do not yet have" in low or "not yet have enough" in low:
        return "boundary"
    return "assertion"


def _reply_form(src: str, text: str) -> str:
    aurora_mod = sys.modules.get("aurora")
    form_fn = getattr(aurora_mod, "_reply_form", None) if aurora_mod else None
    if callable(form_fn):
        try:
            return str(form_fn(src, text))
        except Exception:
            pass
    return _mirror_reply_form(src, text)


def _words(text: str) -> List[str]:
    return re.findall(r"[a-z']+", str(text or "").lower())


def merge_backlog(group: List[Dict[str, Any]]) -> Dict[str, Any]:
    """One contact's unread messages, in order, as a single reading.  Replies
    go to the latest; the text is everything they said."""
    if len(group) == 1:
        return dict(group[0])
    parts = []
    for m in group:
        t = str(m.get("text") or "").strip()
        if t and t[-1] not in ".!?":
            t += "."
        if t:
            parts.append(t)
    last = dict(group[-1])
    last["text"] = " ".join(parts)[:MAX_TEXT_CHARS * 2]
    return last


def own_voice(src: str, text: str, heard: str = "") -> Tuple[bool, str]:
    """(True, "") if this is her own expression; otherwise (False, reason)."""
    reply = str(text or "").strip()
    if not reply:
        return False, "silent"
    if str(src or "") in SCRIPTED_SOURCES:
        return False, f"scripted_source:{src}"
    low = reply.lower()
    for prefix in TEMPLATE_PREFIXES:
        if low.startswith(prefix):
            return False, "template"
    form = _reply_form(str(src or ""), reply)
    if form != "assertion":
        return False, f"form:{form}"
    said, heard_words = _words(reply), _words(heard)
    if said and heard_words and said == heard_words:
        return False, "echo"
    return True, ""


# -- who is speaking --------------------------------------------------------------

_USER_POSSESSIVE = re.compile(r"\b[Uu]ser's\b")
_USER_WORD = re.compile(r"\b(?:the user|The user|[Uu]ser)\b")


def _reattribute(text: str, name: str) -> Tuple[str, bool]:
    changed = _USER_POSSESSIVE.sub(f"{name}'s", str(text or ""))
    changed = _USER_WORD.sub(name, changed)
    return changed, changed != str(text or "")


class SpeakerScopedMemory:
    """Conversation memory as seen during a partner's turn.

    Every write that would be filed about "the user" (Sunni) is filed about
    the partner instead, and facts are recorded as that partner's claims at
    no more than moderate confidence.  Reads pass straight through.
    """

    CLAIM_CONFIDENCE_CAP = 0.6

    def __init__(self, inner: Any, persona_id: str, display_name: str) -> None:
        object.__setattr__(self, "_inner", inner)
        object.__setattr__(self, "_pid", persona_id)
        object.__setattr__(self, "_name", display_name)

    def __getattr__(self, attr: str) -> Any:
        return getattr(self._inner, attr)

    def __setattr__(self, attr: str, value: Any) -> None:
        setattr(self._inner, attr, value)

    def _source(self, source: str) -> str:
        return f"dm:{self._pid}:{source or 'conversation'}"

    # Sources that file what the SPEAKER said.  Internal learners that write
    # their own analysis during the turn (e.g. "retained_learning") are hers,
    # not the partner's, and pass through unchanged.
    SPEAKER_SOURCES = ("user", "statement", "introduction", "conversation", "told",
                       "direct", "explicit")

    def _speaker_originated(self, source: str, fact: str) -> bool:
        low = str(source or "").lower()
        return (any(marker in low for marker in self.SPEAKER_SOURCES)
                or _reattribute(fact, self._name)[1])

    def learn_fact(self, fact: str, source: str = "conversation",
                   confidence: float = 0.7, *args: Any, **kwargs: Any) -> Any:
        if not self._speaker_originated(source, fact):
            return self._inner.learn_fact(fact, source=source, confidence=confidence,
                                          *args, **kwargs)
        text, changed = _reattribute(fact, self._name)
        if not changed:
            text = f"{self._name} said: {text}"
        return self._inner.learn_fact(
            text, source=self._source(source),
            confidence=min(float(confidence), self.CLAIM_CONFIDENCE_CAP), *args, **kwargs)

    def add_relationship_note(self, person: str, note: str, *args: Any, **kwargs: Any) -> Any:
        person_text, _ = _reattribute(str(person or ""), self._name)
        note_text, _ = _reattribute(str(note or ""), self._name)
        if str(person or "").strip().lower() in ("user", "the user", ""):
            person_text = self._name.lower()
        return self._inner.add_relationship_note(person_text, note_text, *args, **kwargs)

    def instantiate_lineage_trace(self, *args: Any, **kwargs: Any) -> Any:
        if "claim" in kwargs:
            kwargs["claim"], _ = _reattribute(kwargs["claim"], self._name)
        edges = kwargs.get("role_edges")
        if isinstance(edges, list):
            fixed = []
            for edge in edges:
                if isinstance(edge, Mapping):
                    edge = dict(edge)
                    for key in ("subject", "object"):
                        if str(edge.get(key, "")).strip().lower() in ("user", "the user"):
                            edge[key] = self._name
                fixed.append(edge)
            kwargs["role_edges"] = fixed
        if "source" in kwargs:
            kwargs["source"] = self._source(str(kwargs["source"]))
        if "confidence" in kwargs:
            try:
                kwargs["confidence"] = min(float(kwargs["confidence"]), self.CLAIM_CONFIDENCE_CAP)
            except Exception:
                pass
        return self._inner.instantiate_lineage_trace(*args, **kwargs)


@contextlib.contextmanager
def speaker_frame(systems: Dict[str, Any], persona_id: str,
                  display_name: str) -> Iterator[None]:
    """Attribute everything filed during this turn to the partner."""
    prior_memory = systems.get("conversation_memory")
    prior_speaker = systems.get("_current_speaker")
    if prior_memory is not None:
        systems["conversation_memory"] = SpeakerScopedMemory(prior_memory, persona_id, display_name)
    systems["_current_speaker"] = {"id": persona_id, "name": display_name,
                                   "kind": "ai_contact", "via": "praxis_messenger"}
    try:
        yield
    finally:
        if prior_memory is not None:
            systems["conversation_memory"] = prior_memory
        if prior_speaker is None:
            systems.pop("_current_speaker", None)
        else:
            systems["_current_speaker"] = prior_speaker


# -- the messenger -------------------------------------------------------------

def _default_process_turn(systems: Dict[str, Any], text: str, **kwargs: Any) -> Dict[str, Any]:
    import aurora as _aurora  # type: ignore  (root aurora.py, already booted)
    return _aurora.process_external_user_turn(systems, text, **kwargs)


def _default_extract(result: Any) -> str:
    try:
        from aurora_internal.aurora_live_experience import reply_text_of
        return reply_text_of(result)
    except Exception:
        resp = result.get("resp_A") if isinstance(result, Mapping) else None
        return str(getattr(resp, "content", "") or "").strip()


class PraxisMessenger:
    def __init__(self, systems: Dict[str, Any], *, state_dir: str,
                 endpoint: str = DEFAULT_ENDPOINT,
                 field_lock: Optional[Any] = None,
                 live_idle: Optional[Callable[[], bool]] = None,
                 process_turn: Optional[Callable[..., Dict[str, Any]]] = None,
                 extract_reply: Optional[Callable[[Any], str]] = None,
                 http: Optional[Callable[[str, str, Optional[Dict[str, Any]]], Optional[Dict[str, Any]]]] = None,
                 poll_s: float = POLL_S) -> None:
        self.systems = systems
        self.endpoint = str(endpoint or DEFAULT_ENDPOINT).rstrip("/")
        self.field_lock = field_lock
        self.live_idle = live_idle or (lambda: True)
        self.process_turn = process_turn or _default_process_turn
        self.extract_reply = extract_reply or _default_extract
        self.http = http or self._http
        self.poll_s = float(poll_s)
        self.root = Path(state_dir or "aurora_state") / "praxis"
        self.transcripts = self.root / TRANSCRIPT_DIR
        self.transcripts.mkdir(parents=True, exist_ok=True)
        self.cursor_path = self.root / "messenger_cursor.json"
        self.cursor = self._load_cursor()
        self._stop = threading.Event()
        self._paused = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.counters = {"heard": 0, "spoke": 0, "withheld": 0, "breaches": 0,
                         "busy_skips": 0, "errors": 0, "reentries": 0}
        self.withheld_reasons: Dict[str, int] = {}
        # What she last tried to say, so Sunni can see it on the Hub.
        self.last_withheld: Dict[str, Any] = {}
        self.last_spoke: Dict[str, Any] = {}
        # contact -> {"message", "attempts", "last_attempt"}: the latest thing
        # said to her that she has not yet answered in her own words.
        self.pending: Dict[str, Dict[str, Any]] = {}
        # A failed cognitive turn must not be marked read, but repeatedly
        # replaying the same exception every three seconds wastes the phone.
        # A fresh message for the contact can restart the combined reading.
        self.failed_reads: Dict[str, Dict[str, Any]] = {}
        # Replies already composed in her own voice are kept as an outbox on
        # transport failure. Retrying POST must not repeat her entire cognition.
        self.outbox_path = self.root / "messenger_outbox.json"
        try:
            raw_outbox = json.loads(self.outbox_path.read_text(encoding="utf-8"))
            self.outbox: Dict[str, Dict[str, Any]] = {
                str(seq): dict(entry) for seq, entry in dict(raw_outbox).items()
                if isinstance(entry, dict)
                and isinstance(entry.get("persona_id"), str)
                and isinstance(entry.get("text"), str)
                and str(seq).isdigit()
            }
        except Exception:
            self.outbox = {}
        # New phrasings: word pairs she says that no contact ever said to her.
        # A parrot only recombines what it heard; a learner produces pairs it
        # never heard (the "goed" signature).  Counted, not judged.
        self.heard_pairs_path = self.root / "heard_pairs.json"
        try:
            self.heard_pairs = set(json.loads(self.heard_pairs_path.read_text(encoding="utf-8")))
        except Exception:
            self.heard_pairs = set()
        self.last_novel: Dict[str, Any] = {}
        # Knowing by triangulation: claims from different contacts that agree
        # become her facts; opposite claims go to her contradiction ledger.
        try:
            from aurora_social_corroboration import SocialCorroboration
            self.corroboration: Optional[Any] = SocialCorroboration(str(Path(state_dir or "aurora_state")))
        except Exception:
            self.corroboration = None
        self.online = False
        self.last_error = ""
        self.last_pull_at = 0.0
        self.unread_waiting = 0
        self.unread_seen_at = 0.0
        # Messages already read that sit beyond the shared cursor (another
        # contact's earlier message is still unread) -- never read twice.
        self.read_ahead: set = set()
        # She starts conversations herself when something of hers is
        # unresolved (aurora_praxis_initiative.py).
        try:
            from aurora_praxis_initiative import PraxisInitiative
            self.initiative: Optional[Any] = PraxisInitiative(self)
        except Exception as exc:
            self.initiative = None
            self.last_error = f"initiative: {type(exc).__name__}: {exc}"[:300]

    # -- wire -------------------------------------------------------------------

    def _http(self, method: str, path: str,
              payload: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(self.endpoint + path, data=data, method=method)
        if data is not None:
            request.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_S) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            try:
                return json.loads(exc.read().decode("utf-8"))
            except Exception:
                return {"error": f"http_{exc.code}"}

    # -- persistence -----------------------------------------------------------

    def _load_cursor(self) -> int:
        try:
            return int(json.loads(self.cursor_path.read_text(encoding="utf-8")).get("after", 0))
        except Exception:
            return 0

    def _save_cursor(self) -> None:
        tmp = self.cursor_path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"after": self.cursor, "updated_at": time.time()}),
                       encoding="utf-8")
        tmp.replace(self.cursor_path)

    def _save_outbox(self) -> None:
        temp = self.outbox_path.with_suffix(".tmp")
        temp.write_text(json.dumps(self.outbox, ensure_ascii=False), encoding="utf-8")
        temp.replace(self.outbox_path)

    def _queue_unsent(self, persona_id: str, text: str, seq: int) -> None:
        self.outbox[str(seq)] = {
            "persona_id": persona_id, "text": text,
            "in_reply_to": seq, "attempts": 0, "last_attempt": time.time(),
        }
        try:
            self._save_outbox()
        except OSError as exc:
            self.last_error = f"outbox persistence: {exc}"[:300]

    def _retry_unsent(self) -> None:
        # Cheap network delivery, independent of the expensive field lock.
        # Bounded per pass so a large offline outbox cannot starve new mail.
        now = time.time()
        attempted = 0
        for key, entry in list(self.outbox.items()):
            if attempted >= 3:
                break
            if now - float(entry.get("last_attempt", 0.0)) < SEND_RETRY_AFTER_S:
                continue
            attempted += 1
            entry["last_attempt"] = now
            entry["attempts"] = int(entry.get("attempts", 0)) + 1
            try:
                response = self.http("POST", "/social/send", {
                    "persona_id": entry["persona_id"], "text": entry["text"],
                    "in_reply_to": int(entry["in_reply_to"]),
                })
            except Exception as exc:
                response = {"error": f"{type(exc).__name__}: {exc}"}
            if response and response.get("accepted"):
                pid = entry["persona_id"]
                self.counters["spoke"] += 1
                self.last_spoke = {"to": pid, "text": entry["text"][:160],
                                   "src": "outbox_retry", "at": time.time()}
                self._log(pid, {"dir": "spoke_retry",
                                "reply_to": entry["in_reply_to"],
                                "text": entry["text"], "at": time.time()})
                self.outbox.pop(key, None)
            else:
                self.counters["errors"] += 1
                self.last_error = (
                    f"outbox send refused: {(response or {}).get('error', 'no response')}"
                )[:300]
            try:
                self._save_outbox()
            except OSError as exc:
                self.last_error = f"outbox persistence: {exc}"[:300]

    def _log(self, persona_id: str, record: Dict[str, Any]) -> None:
        safe = "".join(ch for ch in persona_id if ch.isalnum() or ch in "-_")
        with (self.transcripts / f"{safe}.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, default=str) + "\n")

    # -- one message ----------------------------------------------------------------

    def _feed_exemplar(self, text: str) -> None:
        """Partner speech is human-language exemplar material for her grammar
        learner -- observed, never credited as her own output."""
        grammar = self.systems.get("grammar_engine")
        observe = getattr(grammar, "observe_exemplar", None)
        if callable(observe):
            try:
                observe(text)
            except Exception:
                pass

    MAX_HEARD_PAIRS = 50000

    @staticmethod
    def _pairs(text: str) -> List[str]:
        words = re.findall(r"[a-z']+", str(text or "").lower())
        return [f"{a} {b}" for a, b in zip(words, words[1:])]

    def _remember_heard_pairs(self, text: str) -> None:
        self.heard_pairs.update(self._pairs(text))
        if len(self.heard_pairs) > self.MAX_HEARD_PAIRS:
            self.heard_pairs = set(list(self.heard_pairs)[-self.MAX_HEARD_PAIRS:])
        try:
            tmp = self.heard_pairs_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(sorted(self.heard_pairs)), encoding="utf-8")
            tmp.replace(self.heard_pairs_path)
        except Exception:
            pass

    def handle_message(self, message: Dict[str, Any], *, reentry: bool = False) -> Dict[str, Any]:
        pid, name, text = message["persona_id"], message["display_name"], message["text"]
        self._last_heard = text
        started = time.time()
        if reentry:
            self.counters["reentries"] = self.counters.get("reentries", 0) + 1
        else:
            self.counters["heard"] += 1
            self._log(pid, {"dir": "heard", "seq": message["seq"], "from": name,
                            "text": text, "at": started})
            self._feed_exemplar(text)
            self._remember_heard_pairs(text)
            if self.initiative is not None:
                self.initiative.heard_from(pid)

        with speaker_frame(self.systems, pid, name):
            result = self.process_turn(
                self.systems, text,
                source_label=f"praxis_dm:{pid}",
                session_id=f"praxis_dm_{pid}",
                auto_search_enabled=False,
                record_exchange=True,
                update_interactive_state=False,
                run_periodic_maintenance=False,
                mode_name="BOUNDED",
            ) or {}
        if not reentry and self.corroboration is not None:
            try:
                self.corroboration.observe_message(self.systems, pid, name, text)
            except Exception as exc:
                self.last_error = f"corroboration: {type(exc).__name__}: {exc}"[:300]
        reply = self.extract_reply(result)
        src = str(result.get("src", "") if isinstance(result, Mapping) else "")
        # The voice gate in her turn already decided what is hers; its label
        # is the truth even if later stages relabel the source.
        gate = dict(self.systems.get("_last_voice_gate") or {})
        if (gate.get("channel") == f"praxis_dm_{pid}"
                and float(gate.get("at", 0.0) or 0.0) >= started - 1.0
                and gate.get("outcome") in ("own_voice", "own_composition", "pressure_articulation")):
            src = str(gate.get("src") or src)
        ok, reason = own_voice(src, reply, heard=text)
        outcome = {"seq": message["seq"], "persona_id": pid, "reply": reply,
                   "src": src, "sent": False, "reason": reason}
        if not ok:
            self.counters["withheld"] += 1
            self.withheld_reasons[reason.split(":")[0]] = \
                self.withheld_reasons.get(reason.split(":")[0], 0) + 1
            self._log(pid, {"dir": "withheld", "reply_to": message["seq"], "text": reply,
                            "src": src, "reason": reason, "at": time.time()})
            self.last_withheld = {"to": name, "text": reply[:160], "src": src,
                                  "reason": reason, "at": time.time(),
                                  "pressure": gate.get("pressure"),
                                  "articulation": gate.get("articulation", "")}
            entry = self.pending.get(pid) or {"message": message, "attempts": 0}
            if entry["message"].get("seq") != message.get("seq"):
                entry = {"message": message, "attempts": 0}
            entry["attempts"] = int(entry.get("attempts", 0)) + 1
            entry["last_attempt"] = time.time()
            self.pending[pid] = entry
            return outcome
        try:
            response = self.http("POST", "/social/send", {
                "persona_id": pid, "text": reply[:MAX_TEXT_CHARS],
                "in_reply_to": message["seq"]})
        except Exception as exc:
            response = {"error": f"{type(exc).__name__}: {exc}"}
        outcome["sent"] = bool(response and response.get("accepted"))
        if outcome["sent"]:
            self.counters["spoke"] += 1
            self._log(pid, {"dir": "spoke", "reply_to": message["seq"], "text": reply,
                            "src": src, "at": time.time()})
            self.last_spoke = {"to": name, "text": reply[:160], "src": src, "at": time.time()}
            self.pending.pop(pid, None)
            novel = [pair for pair in self._pairs(reply) if pair not in self.heard_pairs]
            if novel:
                self.counters["novel_phrasings"] = self.counters.get("novel_phrasings", 0) + 1
                self.last_novel = {"to": name, "text": reply[:160], "pairs": novel[:3],
                                   "at": time.time()}
        else:
            self.counters["errors"] += 1
            self.last_error = f"send refused: {(response or {}).get('error', 'no response')}"
            self._queue_unsent(pid, reply[:MAX_TEXT_CHARS], int(message["seq"]))
            # Her answer exists. Only its delivery failed, so do not re-enter
            # the cognitive pipeline to compose it again.
            self.pending.pop(pid, None)
            outcome["reason"] = "delivery_queued"
        return outcome

    # -- one pass ------------------------------------------------------------------

    def pull_once(self) -> List[Dict[str, Any]]:
        # Phone fix (2026-11-08): checking for messages is NOT gated on the
        # field being idle -- only answering is.  Gating the check starved
        # the messenger: faster background loops always took the quiet
        # window first, so she never even looked.
        if self._paused.is_set():
            return []
        self._retry_unsent()
        try:
            payload = self.http("GET", f"/social/pull?after={self.cursor}&limit={PULL_LIMIT}", None)
        except Exception as exc:
            self.online, self.last_error = False, f"{type(exc).__name__}: {exc}"
            return []
        self.online = isinstance(payload, Mapping) and "messages" in payload
        self.last_pull_at = time.time()
        if not self.online:
            return []
        outcomes: List[Dict[str, Any]] = []
        unread = [r for r in (payload.get("messages") or [])
                  if isinstance(r, Mapping) and isinstance(r.get("seq"), int) and r["seq"] > self.cursor
                  and r["seq"] not in getattr(self, "read_ahead", ())]
        self.unread_waiting = len(unread)
        self.unread_seen_at = time.time()
        # Read a contact's backlog TOGETHER (Sunni, 2026-11-08: "it's like
        # she's not even reading what is being said to her").  Answering five
        # queued messages one by one put every reply against a question the
        # contact had already moved past.  Everything a contact sent since her
        # last reply is now one reading, answered once, in reply to the latest.
        valid: List[Dict[str, Any]] = []
        self.read_ahead = {q for q in self.read_ahead if q > self.cursor}
        handled: set = set(self.read_ahead)
        all_seqs: List[int] = []
        for raw in payload.get("messages") or []:
            seq = raw.get("seq") if isinstance(raw, Mapping) else None
            if not isinstance(seq, int) or seq <= self.cursor:
                continue
            all_seqs.append(seq)
            if seq in self.read_ahead:
                continue
            try:
                valid.append(validate_incoming_message(raw))
            except MessengerContractBreach as breach:
                self.counters["breaches"] += 1
                self.last_error = f"breach: {breach}"
                handled.add(seq)                 # dropped whole; never re-read
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for message in valid:
            groups.setdefault(message["persona_id"], []).append(message)

        def _advance() -> None:
            # The cursor is shared by every contact: move it only across
            # messages that have actually been read.
            moved = False
            for seq in sorted(all_seqs):
                if seq <= self.cursor:
                    continue
                if seq not in handled:
                    break
                self.cursor, moved = seq, True
            if moved:
                self._save_cursor()

        _advance()
        for group in sorted(groups.values(), key=lambda g: g[0]["seq"]):
            pid = group[-1]["persona_id"]
            failure = self.failed_reads.get(pid)
            if (failure and failure.get("seq") == group[-1]["seq"]
                    and time.time() - float(failure.get("at", 0.0)) < REENTRY_AFTER_S):
                # Keep it unread for the next attempt without holding all
                # other background work hostage during the retry cooldown.
                self.unread_waiting = max(0, self.unread_waiting - len(group))
                continue
            if not self.live_idle():
                break                            # Sunni is here; he comes first
            acquired = True
            if self.field_lock is not None:
                acquired = self.field_lock.acquire(blocking=False)
            if not acquired:
                self.counters["busy_skips"] += 1
                break                            # unread; next pass
            message = merge_backlog(group)
            read_ok = False
            try:
                outcomes.append(self.handle_message(message))
                self.failed_reads.pop(pid, None)
                read_ok = True
                if len(group) > 1:
                    self.counters["heard"] += len(group) - 1
                    self.counters["backlogs_read_together"] = self.counters.get("backlogs_read_together", 0) + 1
            except Exception as exc:
                self.counters["errors"] += 1
                self.last_error = f"turn failed: {type(exc).__name__}: {exc}"[:300]
                self.failed_reads[pid] = {"seq": group[-1]["seq"], "at": time.time()}
            finally:
                if self.field_lock is not None:
                    self.field_lock.release()
            if not read_ok:
                # Do not acknowledge a turn the cognitive path never finished.
                # Back off instead of burning more compute on each poll.
                self.unread_waiting = max(0, self.unread_waiting - len(group))
                continue
            handled.update(m["seq"] for m in group)
            self.read_ahead.update(m["seq"] for m in group)
            _advance()
            self.read_ahead = {q for q in self.read_ahead if q > self.cursor}
            self.unread_waiting = max(0, self.unread_waiting - len(group))
        outcomes.extend(self._reenter_pending())
        if self.initiative is not None:
            try:
                outcomes.extend(self.initiative.tick())
            except Exception as exc:
                self.counters["errors"] += 1
                self.last_error = f"initiative: {type(exc).__name__}: {exc}"[:300]
        return outcomes

    def _pressure(self, pid: str) -> float:
        if addressed_pressure is None:
            return 0.0
        try:
            return float(addressed_pressure(self.systems).level(f"praxis_dm_{pid}"))
        except Exception:
            return 0.0

    def _reenter_pending(self) -> List[Dict[str, Any]]:
        """Being left unanswered keeps pushing.  While pressure for a contact
        stays at or above the articulation threshold, she revisits the last
        thing they said (each revisit addresses her again, so pressure
        builds), up to MAX_ATTEMPTS, spaced REENTRY_AFTER_S apart."""
        outcomes: List[Dict[str, Any]] = []
        now = time.time()
        for pid, entry in list(self.pending.items()):
            if int(entry.get("attempts", 0)) >= MAX_ATTEMPTS:
                continue
            if now - float(entry.get("last_attempt", 0.0)) < REENTRY_AFTER_S:
                continue
            if self._pressure(pid) < ARTICULATION_THRESHOLD:
                continue
            if not self.live_idle():
                break
            if self.field_lock is not None and not self.field_lock.acquire(blocking=False):
                self.counters["busy_skips"] += 1
                break
            try:
                outcomes.append(self.handle_message(dict(entry["message"]), reentry=True))
            except Exception as exc:
                self.counters["errors"] += 1
                self.last_error = f"turn failed: {type(exc).__name__}: {exc}"[:300]
                entry["attempts"] = MAX_ATTEMPTS
            finally:
                if self.field_lock is not None:
                    self.field_lock.release()
        return outcomes

    # -- lifecycle -------------------------------------------------------------------

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="aurora-praxis-messenger",
                                        daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 3.0) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout)

    def pause(self) -> None:
        self._paused.set()

    def resume(self) -> None:
        self._paused.clear()

    def waiting(self) -> bool:
        """A contact's message is waiting unread (seen within the last minute)."""
        return (int(getattr(self, "unread_waiting", 0) or 0) > 0
                and time.time() - float(getattr(self, "unread_seen_at", 0.0) or 0.0) < 60.0)

    def _run(self) -> None:
        while not self._stop.wait(WAITING_POLL_S if self.waiting() else self.poll_s):
            try:
                self.pull_once()
            except Exception as exc:
                self.counters["errors"] += 1
                self.last_error = f"{type(exc).__name__}: {exc}"

    def status(self) -> Dict[str, Any]:
        return {"version": MESSENGER_VERSION, "endpoint": self.endpoint,
                "online": self.online, "paused": self._paused.is_set(),
                "thread_alive": bool(self._thread and self._thread.is_alive()),
                "cursor": self.cursor, "last_pull_at": self.last_pull_at,
                "unread_waiting": int(getattr(self, "unread_waiting", 0) or 0),
                "outbox_pending": len(self.outbox),
                "failed_reads": {pid: int(e.get("seq", 0)) for pid, e in self.failed_reads.items()},
                "last_error": self.last_error, **self.counters,
                "withheld_reasons": dict(self.withheld_reasons),
                "last_withheld": dict(self.last_withheld),
                "last_spoke": dict(self.last_spoke),
                "corroboration": (self.corroboration.status() if self.corroboration is not None else {}),
                "last_novel": dict(self.last_novel),
                "initiative": (self.initiative.status() if self.initiative is not None else {}),
                "pending": {pid: {"attempts": e.get("attempts", 0),
                                  "pressure": round(self._pressure(pid), 4)}
                            for pid, e in self.pending.items()}}


_MESSENGER: Optional[PraxisMessenger] = None


def start_praxis_messenger(systems: Dict[str, Any], *, state_dir: str,
                           endpoint: str = DEFAULT_ENDPOINT,
                           field_lock: Optional[Any] = None,
                           live_idle: Optional[Callable[[], bool]] = None) -> PraxisMessenger:
    global _MESSENGER
    if _MESSENGER is not None:
        # Preserve unanswered-contact pressure, initiative, read-ahead and
        # already-composed delivery when reviving the same Python worker.
        same_owner = (
            _MESSENGER.systems is systems
            and _MESSENGER.endpoint == str(endpoint or DEFAULT_ENDPOINT).rstrip("/")
            and _MESSENGER.root == Path(state_dir or "aurora_state") / "praxis"
        )
        if same_owner:
            _MESSENGER.start()
            return _MESSENGER
        _MESSENGER.stop()
    _MESSENGER = PraxisMessenger(systems, state_dir=state_dir, endpoint=endpoint,
                                 field_lock=field_lock, live_idle=live_idle)
    _MESSENGER.start()
    return _MESSENGER


def get_messenger() -> Optional[PraxisMessenger]:
    return _MESSENGER

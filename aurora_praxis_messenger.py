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

    def learn_fact(self, fact: str, source: str = "conversation",
                   confidence: float = 0.7, *args: Any, **kwargs: Any) -> Any:
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
                         "busy_skips": 0, "errors": 0}
        self.withheld_reasons: Dict[str, int] = {}
        self.online = False
        self.last_error = ""
        self.last_pull_at = 0.0

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

    def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        pid, name, text = message["persona_id"], message["display_name"], message["text"]
        self.counters["heard"] += 1
        self._log(pid, {"dir": "heard", "seq": message["seq"], "from": name,
                        "text": text, "at": time.time()})
        self._feed_exemplar(text)

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
        reply = self.extract_reply(result)
        src = str(result.get("src", "") if isinstance(result, Mapping) else "")
        ok, reason = own_voice(src, reply, heard=text)
        outcome = {"seq": message["seq"], "persona_id": pid, "reply": reply,
                   "src": src, "sent": False, "reason": reason}
        if not ok:
            self.counters["withheld"] += 1
            self.withheld_reasons[reason.split(":")[0]] = \
                self.withheld_reasons.get(reason.split(":")[0], 0) + 1
            self._log(pid, {"dir": "withheld", "reply_to": message["seq"], "text": reply,
                            "src": src, "reason": reason, "at": time.time()})
            return outcome
        response = self.http("POST", "/social/send", {
            "persona_id": pid, "text": reply[:MAX_TEXT_CHARS], "in_reply_to": message["seq"]})
        outcome["sent"] = bool(response and response.get("accepted"))
        if outcome["sent"]:
            self.counters["spoke"] += 1
            self._log(pid, {"dir": "spoke", "reply_to": message["seq"], "text": reply,
                            "src": src, "at": time.time()})
        else:
            self.counters["errors"] += 1
            self.last_error = f"send refused: {(response or {}).get('error', 'no response')}"
        return outcome

    # -- one pass ------------------------------------------------------------------

    def pull_once(self) -> List[Dict[str, Any]]:
        if self._paused.is_set() or not self.live_idle():
            return []
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
        for raw in payload.get("messages") or []:
            try:
                message = validate_incoming_message(raw)
            except MessengerContractBreach as breach:
                self.counters["breaches"] += 1
                self.last_error = f"breach: {breach}"
                seq = raw.get("seq") if isinstance(raw, Mapping) else None
                if isinstance(seq, int) and seq > self.cursor:
                    self.cursor = seq            # dropped whole; never re-read
                    self._save_cursor()
                continue
            if message["seq"] <= self.cursor:
                continue
            if not self.live_idle():
                break                            # Sunni is here; he comes first
            acquired = True
            if self.field_lock is not None:
                acquired = self.field_lock.acquire(blocking=False)
            if not acquired:
                self.counters["busy_skips"] += 1
                break                            # unread; next pass
            try:
                outcomes.append(self.handle_message(message))
            except Exception as exc:
                self.counters["errors"] += 1
                self.last_error = f"{type(exc).__name__}: {exc}"
            finally:
                if self.field_lock is not None:
                    self.field_lock.release()
            # Advance past a message once handled (even if her turn failed),
            # so one bad message can never wedge the loop.
            self.cursor = message["seq"]
            self._save_cursor()
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

    def _run(self) -> None:
        while not self._stop.wait(self.poll_s):
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
                "last_error": self.last_error, **self.counters,
                "withheld_reasons": dict(self.withheld_reasons)}


_MESSENGER: Optional[PraxisMessenger] = None


def start_praxis_messenger(systems: Dict[str, Any], *, state_dir: str,
                           endpoint: str = DEFAULT_ENDPOINT,
                           field_lock: Optional[Any] = None,
                           live_idle: Optional[Callable[[], bool]] = None) -> PraxisMessenger:
    global _MESSENGER
    if _MESSENGER is not None:
        _MESSENGER.stop()
    _MESSENGER = PraxisMessenger(systems, state_dir=state_dir, endpoint=endpoint,
                                 field_lock=field_lock, live_idle=live_idle)
    _MESSENGER.start()
    return _MESSENGER


def get_messenger() -> Optional[PraxisMessenger]:
    return _MESSENGER

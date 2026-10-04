"""
aurora_live_experience.py
=========================

Live turns feed the same resolution ledger and representation exchange that
historical experience feeds, so what history taught applies to the very turn
that is about to be answered, and what live turns do adds to the same evidence.

The user's event is observed BEFORE generation: the exchange then offers every
discovered representation's expectation about what follows to every adopting
subject, which is how a live reply can be shaped by what was learned.  The
reply event is observed AFTER generation: Aurora's own act is scored against
the same expectations, which is her consequence.  Only chronology, size and
surface tokens travel here; no label, intent class or gloss.

Live events use the ledger's ``live`` stream: its own context (previous events,
session) with every distribution and statistic shared with the ``history``
stream.  Subjects are roles (``external_user``, ``responder``), so the party
that answers in the archive and Aurora answering now are the same subject.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

import re
import time
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from aurora_internal.aurora_lexical_crystals import LexicalCrystals
from aurora_internal.aurora_representation_crystals import HypothesisCrystals, RepresentationCrystals
from aurora_internal.aurora_representation_exchange import AuroraRepresentationExchange
from aurora_internal.aurora_resolution_ledger import AuroraResolutionLedger, role_subject

LIVE_STREAM = "live"
_TOKEN_RE = re.compile(r"[a-z][a-z']{1,}")
_LAST_TS_KEY = "_live_last_event_ts"
_SUBJECT_ATTRS = ("identity", "communication_emergence", "lexical_grounding")


def tokens_of(text: str, limit: int = 48) -> List[str]:
    return list(dict.fromkeys(_TOKEN_RE.findall(str(text or "").lower())))[:limit]


def _known_word(systems: Mapping[str, Any]) -> Any:
    """Predicate for 'this word is in her own lexicon' (None when no lexicon is reachable)."""
    perception = systems.get("perception")
    for holder in (getattr(perception, "composer", None), perception):
        entries = getattr(getattr(holder, "lexicon", None), "entries", None)
        if entries:
            return lambda word, _entries=entries: str(word).lower() in _entries
    return None


def _wire_waveform_and_lexicon(systems: Mapping[str, Any], ledger: Any) -> None:
    """Crystals are stamped with the input's waveform; the lexicon's channels live on the crystals."""
    extractor = getattr(systems.get("dimensional"), "concept_extractor", None)   # where crystal signals are built
    if extractor is not None and getattr(extractor, "input_waveform_provider", None) is None:
        def provider(_systems=systems, _ledger=ledger):
            if not (_systems.get("_historical_witnessing") or int(_systems.get("_live_turn_depth", 0) or 0) > 0):
                return None
            waveform = _ledger.last_waveform()
            return list(waveform) if len(waveform) == 5 else None
        extractor.input_waveform_provider = provider
    registry = systems.get("_concept_crystal_registry")
    perception = systems.get("perception")
    for holder in (getattr(perception, "composer", None), perception):
        lexicon = getattr(holder, "lexicon", None)
        if lexicon is not None and registry is not None and getattr(lexicon, "_crystal_sink", None) is None:
            LexicalCrystals(registry).attach(lexicon)
            break


def ensure_runtime(systems: Any, state_dir: Optional[str] = None) -> Tuple[Any, Any]:
    """The shared ledger and exchange for this runtime, created once, consumers attached."""
    if not isinstance(systems, dict):
        return None, None
    directory = str(state_dir or systems.get("state_dir") or "aurora_state")
    ledger = systems.get("resolution_ledger")
    exchange = systems.get("representation_exchange")
    try:
        from concept_crystal import unify_crystal_store
        unify_crystal_store(systems)          # one crystal store, before anything reads or writes it
    except Exception:
        pass
    try:
        if ledger is None:
            ledger = AuroraResolutionLedger(state_dir=directory)
            systems["resolution_ledger"] = ledger
            registry = systems.get("_concept_crystal_registry")
            if registry is not None:             # discovery research lives on the crystals as hypotheses
                ledger.attach_crystals(HypothesisCrystals(registry))
        if exchange is None:
            exchange = AuroraRepresentationExchange(ledger, state_dir=directory)
            systems["representation_exchange"] = exchange
            registry = systems.get("_concept_crystal_registry")
            if registry is not None:             # the crystals are the record
                exchange.attach_crystals(RepresentationCrystals(registry), known_word=_known_word(systems))
        _wire_waveform_and_lexicon(systems, ledger)
        exchange.attach_systems(systems)
        aurora = systems.get("aurora")
        for owner_name, owner in (("aurora", aurora), ("gateway", getattr(aurora, "gateway", None))):
            if owner is None:
                continue
            for attr in _SUBJECT_ATTRS:
                obj = getattr(owner, attr, None)
                if obj is not None:
                    exchange.register_consumer(f"{owner_name}.{attr}", obj)
    except Exception:
        pass
    return ledger, exchange


def _observe(systems: Any, role: str, session_id: str, text: str, now: Optional[float]) -> Dict[str, Any]:
    ledger, exchange = ensure_runtime(systems)
    if ledger is None or exchange is None:
        return {}
    moment = float(now if now is not None else time.time())
    last = systems.get(_LAST_TS_KEY)
    elapsed = max(0.0, moment - float(last)) if last is not None else None
    systems[_LAST_TS_KEY] = moment
    result = ledger.observe_event(
        stream=LIVE_STREAM,
        event_id=f"live:{int(moment * 1000)}:{role}",
        episode_id=str(session_id or systems.get("_live_session_id") or "live"),
        actor=role_subject(role),
        text_length=len(str(text or "")),
        elapsed_seconds=elapsed,
        episode_gap_seconds=elapsed,
        warp_field=systems.get("warp_field"),
        tokens=tokens_of(text),
    )
    if result.get("observed"):
        exchange.after_event(int(result["event_index"]), stream=LIVE_STREAM, tokens=tokens_of(text))
        if int(result["event_index"]) % 200 == 0:
            exchange.crystallize()
    return result


def observe_user_event(systems: Any, text: str, *, session_id: str = "", now: Optional[float] = None) -> Dict[str, Any]:
    """Call BEFORE generating the reply."""
    return _observe(systems, "user", session_id, text, now)


def observe_reply_event(systems: Any, text: str, *, session_id: str = "", now: Optional[float] = None) -> Dict[str, Any]:
    """Call AFTER the reply is decided: Aurora's own act, scored against what was expected."""
    if not str(text or "").strip():
        return {}
    return _observe(systems, "aurora", session_id, text, now)


def reply_text_of(result: Any) -> str:
    """Delivered reply text from a process_external_user_turn result (mirrors the bridge)."""
    if not isinstance(result, Mapping):
        return str(result or "").strip()
    resp = result.get("resp_A")
    if resp is not None:
        content = getattr(resp, "content", None)
        if isinstance(content, list):
            parts = [
                b.get("text", "") if isinstance(b, Mapping) else getattr(b, "text", "")
                for b in content
                if (isinstance(b, Mapping) and b.get("type") == "text")
                or (not isinstance(b, Mapping) and getattr(b, "type", "") == "text")
            ]
            text = " ".join(str(p) for p in parts if p).strip()
            if text:
                return text
        elif content:
            return str(content).strip()
    for key in ("response_text", "text", "answer"):
        if result.get(key):
            return str(result[key]).strip()
    return ""

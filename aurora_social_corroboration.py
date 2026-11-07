#!/usr/bin/env python3
"""
aurora_social_corroboration.py -- knowing by triangulation.

A developmental loop the messenger makes possible (2026-11-07): Aurora hears
several independent minds.  What one contact tells her is that contact's
claim (filed "<name> said: ...", confidence <= 0.6, by the speaker frame).
That should stay a claim -- until it isn't alone:

  * CORROBORATION.  When two DIFFERENT speakers independently state the same
    relation (same subject, relation and object, same polarity), the claim
    stops being hearsay and becomes her own fact, filed with who corroborated
    it.  One contact repeating itself is not corroboration.
  * CONTRADICTION.  When two different speakers state the same relation with
    OPPOSITE polarity ("X is Y" vs "X is not Y"), the conflict goes into her
    real ContradictionLedger (aurora_ivm.ContradictionLedger.record), which
    had zero records ever.  Different objects ("rain is water" / "rain is
    wet") are not a contradiction and are never recorded as one.

Nothing here is pushed into her by a partner: partners only ever say words.
The rule that turns words into knowledge is hers.

Personal statements (I / you / we ...) are not claims about the world and
are skipped.  Questions are skipped.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

CORROBORATION_VERSION = "aurora_social_corroboration_v1"
CORROBORATED_CONFIDENCE = 0.8
MAX_RELATIONS = 4000

_PERSONAL = frozenset({"i", "me", "my", "mine", "myself", "you", "your", "yours",
                       "yourself", "we", "us", "our", "ours", "he", "she", "him",
                       "her", "his", "they", "them", "their"})
# Too vague to be the subject of a world claim (but fine inside an object:
# "water THAT falls from clouds").
_VAGUE_SUBJECT = frozenset({"it", "this", "that", "there", "these", "those"})
_FILLER = frozenset({"a", "an", "the", "some", "any", "very", "really", "just",
                     "so", "too", "also", "quite", "actually"})
_NEGATION = re.compile(r"\b(not|never|no|isn't|aren't|wasn't|weren't|don't|doesn't|"
                       r"didn't|can't|cannot|won't)\b|n't\b", re.IGNORECASE)
_AUX_NORMAL = {"are": "is", "was": "is", "were": "is", "am": "is", "be": "is",
               "isn't": "is", "aren't": "is", "wasn't": "is", "weren't": "is",
               "has": "has", "have": "has", "had": "has",
               "doesn't": "does", "don't": "does", "didn't": "does"}
_WORD = re.compile(r"[a-z][a-z']*")


def _words(text: Any) -> List[str]:
    return _WORD.findall(str(text or "").lower())


def _phrase(text: Any) -> str:
    return " ".join(w for w in _words(text) if w not in _FILLER and w not in ("not", "never", "no"))


def claim_from_form(form: Mapping[str, Any], raw_text: str) -> Optional[Tuple[str, str, str, bool]]:
    """(subject, relation, object, negated) for a world claim, else None."""
    if not isinstance(form, Mapping) or form.get("question"):
        return None
    subject = _phrase(form.get("subject"))
    relation_words = _words(form.get("relation"))
    obj = _phrase(" ".join(str(form.get(k) or "") for k in ("obj", "complement")))
    if not subject or not relation_words or not obj:
        return None
    if set(subject.split()) & (_PERSONAL | _VAGUE_SUBJECT) or set(obj.split()) & _PERSONAL:
        return None
    relation = " ".join(_AUX_NORMAL.get(w, w) for w in relation_words
                        if w not in ("not", "never", "no"))
    if not relation:
        return None
    polarity_flag = form.get("polarity")
    if isinstance(form.get("negated"), bool):
        negated = bool(form.get("negated"))
    elif isinstance(polarity_flag, str) and polarity_flag.lower() in ("negative", "neg", "negated"):
        negated = True
    elif isinstance(polarity_flag, bool):
        negated = not polarity_flag
    else:
        negated = bool(_NEGATION.search(str(form.get("relation") or "") + " " + str(raw_text or "")))
    return subject, relation, obj, negated


def _say(subject: str, relation: str, obj: str, negated: bool) -> str:
    return f"{subject} {relation}{' not' if negated else ''} {obj}"


class SocialCorroboration:
    def __init__(self, state_dir: str) -> None:
        self.path = Path(state_dir or "aurora_state") / "praxis" / "social_claims.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        # "subject|relation|object" -> {"pos": {speaker: name}, "neg": {...},
        #  "corroborated": bool, "contradiction_recorded": bool, "first_at": t}
        self.relations: Dict[str, Dict[str, Any]] = {}
        self.counters = {"claims": 0, "corroborated": 0, "contradictions": 0}
        self._load()

    def _load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return
        self.relations = dict(raw.get("relations") or {})
        self.counters.update({k: int(v) for k, v in dict(raw.get("counters") or {}).items()})

    def _save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"version": CORROBORATION_VERSION, "relations": self.relations,
                                   "counters": self.counters, "saved_at": time.time()}),
                       encoding="utf-8")
        tmp.replace(self.path)

    def observe(self, systems: Mapping[str, Any], speaker_id: str, speaker_name: str,
                form: Mapping[str, Any], raw_text: str) -> Dict[str, Any]:
        claim = claim_from_form(form, raw_text)
        if claim is None:
            return {"claim": None}
        subject, relation, obj, negated = claim
        key = f"{subject}|{relation}|{obj}"
        side, other = ("neg", "pos") if negated else ("pos", "neg")
        outcome: Dict[str, Any] = {"claim": _say(*claim), "corroborated": False,
                                   "contradiction": False}
        with self._lock:
            entry = self.relations.setdefault(key, {"pos": {}, "neg": {}, "corroborated_pos": False,
                                                    "corroborated_neg": False,
                                                    "contradiction_recorded": False,
                                                    "first_at": time.time()})
            if speaker_id not in entry[side]:
                self.counters["claims"] += 1
            entry[side][speaker_id] = speaker_name

            # Corroboration: two different speakers, same side.
            flag = f"corroborated_{side}"
            if len(entry[side]) >= 2 and not entry.get(flag):
                entry[flag] = True
                self.counters["corroborated"] += 1
                outcome["corroborated"] = True
                memory = systems.get("conversation_memory") if isinstance(systems, Mapping) else None
                if memory is not None and hasattr(memory, "learn_fact"):
                    names = ", ".join(sorted(entry[side].values()))
                    try:
                        memory.learn_fact(_say(*claim), source=f"corroborated:{names}",
                                          confidence=CORROBORATED_CONFIDENCE)
                    except Exception:
                        pass

            # Contradiction: opposite polarity from a different speaker.
            opposing = {sid: name for sid, name in entry[other].items() if sid != speaker_id}
            if opposing and not entry.get("contradiction_recorded"):
                ledger = systems.get("contradiction_ledger") if isinstance(systems, Mapping) else None
                if ledger is not None and hasattr(ledger, "record"):
                    other_id, other_name = next(iter(opposing.items()))
                    try:
                        ledger.record(_say(subject, relation, obj, not negated), _say(*claim),
                                      source_a=f"dm:{other_id}:{other_name}",
                                      source_b=f"dm:{speaker_id}:{speaker_name}")
                        entry["contradiction_recorded"] = True
                        self.counters["contradictions"] += 1
                        outcome["contradiction"] = True
                    except Exception:
                        pass

            if len(self.relations) > MAX_RELATIONS:
                for old in sorted(self.relations, key=lambda k: self.relations[k].get("first_at", 0))[
                        : len(self.relations) - MAX_RELATIONS]:
                    self.relations.pop(old, None)
            self._save()
        return outcome

    _SENTENCE = re.compile(r"[^.!?]+[.!?]?")
    # Conversational tags ("..., you know.") are not part of the claim.
    _TAG = re.compile(r",?\s*(you know|you see|right|i think|i guess|i believe|"
                      r"isn't it|aren't they|don't you think)\s*([.!?]?)\s*$", re.IGNORECASE)

    def _parser(self) -> Any:
        parser = getattr(self, "_utterance_parser", None)
        if parser is None:
            from aurora_internal.aurora_utterance_parser import UtteranceParser
            parser = self._utterance_parser = UtteranceParser()
        return parser

    def observe_message(self, systems: Mapping[str, Any], speaker_id: str,
                        speaker_name: str, text: str) -> List[Dict[str, Any]]:
        """Every sentence of a message, read with her own utterance parser."""
        outcomes = []
        for sentence in self._SENTENCE.findall(str(text or "")):
            sentence = self._TAG.sub(r"\2", sentence.strip()).strip()
            if len(sentence.split()) < 3:
                continue
            try:
                parsed = self._parser().parse(sentence)
            except Exception:
                continue
            form = parsed.get("relational_form") if isinstance(parsed, Mapping) else None
            if isinstance(form, Mapping):
                outcome = self.observe(systems, speaker_id, speaker_name, form, sentence)
                if outcome.get("claim"):
                    outcomes.append(outcome)
        return outcomes

    def status(self) -> Dict[str, Any]:
        return {"relations": len(self.relations), **self.counters}

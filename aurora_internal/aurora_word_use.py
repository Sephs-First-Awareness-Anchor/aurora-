# Authors: Sunni (Sir) Morningstar & Cael Devo
"""How words are USED in the conversations she lives (Sir, 2026-11-15): the corpus her function words are found from.

The only text that enters is conversation she took part in: said to her (told) or said by her (witnessed).  The source is named at the door, and a
source that is not one of those is turned away: dictionary and reference text is not use, it reaches her through her understanding development and
never through here.  What is kept is bounded profiles of the words on either side of each word (`ContextProfiles`), never the text.

`crystal_runtime` reads the saved profiles when it finds which words stand in for one another.  Everything here is fail-safe: nothing raises into a turn.
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, Optional

from aurora_internal.crystal_substitutability import ContextProfiles

SOURCES = frozenset({"live_user", "live_aurora", "history_user", "history_aurora"})
FILENAME = "word_use.json"
SAVE_EVERY = 60.0            # seconds between writes
_WORD = re.compile(r"[a-z']+")
_SENTENCE = re.compile(r"[.!?;\n]+")


class WordUse:
    def __init__(self, state_dir: str = "aurora_state", *, persist: bool = True, max_words: int = 2000, max_contexts: int = 32) -> None:
        self.path = os.path.join(str(state_dir or "aurora_state"), FILENAME)
        self.persist = bool(persist)
        self.profiles = ContextProfiles(max_words=max_words, max_contexts=max_contexts)
        self.turned_away = 0
        self._dirty = False
        self._saved_at = 0.0
        self._load()

    def observe_text(self, text: str, source: str) -> int:
        """One utterance, from a named conversation source.  Returns how many words were counted (0 when the source is not conversation)."""
        if str(source) not in SOURCES:
            self.turned_away += 1
            return 0
        n = 0
        for sent in _SENTENCE.split(str(text or "").lower()):
            ws = _WORD.findall(sent)
            if ws:
                n += self.profiles.observe(ws)
        self._dirty = self._dirty or n > 0
        return n

    def save(self, force: bool = False, clock=time.time) -> bool:
        if not self.persist or not self._dirty:
            return True
        now = float(clock())
        if not force and now - self._saved_at < SAVE_EVERY:
            return True
        try:
            from aurora_persistence_utils import atomic_write_json      # same writer the ledger uses
        except Exception:
            atomic_write_json = None
        try:
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            payload: Dict[str, Any] = {"v": 1, "profiles": self.profiles.state(), "saved_at": now}
            if atomic_write_json is not None:
                ok = bool(atomic_write_json(Path(self.path), payload, indent=0))
            else:
                tmp = self.path + ".tmp"
                with open(tmp, "w", encoding="utf-8") as fh:
                    json.dump(payload, fh)
                os.replace(tmp, self.path)
                ok = True
        except Exception:
            return False
        if ok:
            self._dirty, self._saved_at = False, now
        return ok

    def _load(self) -> None:
        if not self.persist:
            return
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            self.profiles.restore(data.get("profiles") or {})
        except Exception:
            pass


def load_profiles(state_dir: str) -> Optional[ContextProfiles]:
    """The saved profiles for a state directory, or None when nothing has been kept yet."""
    try:
        with open(os.path.join(str(state_dir), FILENAME), "r", encoding="utf-8") as fh:
            data = json.load(fh)
        prof = ContextProfiles()
        prof.restore(data.get("profiles") or {})
        return prof if prof.vocabulary() else None
    except Exception:
        return None

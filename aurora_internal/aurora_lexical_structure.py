"""
aurora_lexical_structure.py
===========================

Relational structure among WORDS, discovered from the words themselves.

Until now a word got meaning only by hanging off the five roots (X/T/N/B/A) through a discovered
representation.  When the roots offer nothing distinctive, nothing could be hung and nothing new
could be distinguished.  This module discovers distinctions that live in the language itself:

* For every word it learns a RESPONSE PROFILE: which words tend to follow it in the next event
  of the same episode.  No root, label, intent class or gloss is involved.
* A word's profile is compared with the background (how often each word follows anything) with
  positive pointwise mutual information, so diffuse words (whose followers look like everyone's)
  carry no profile and cannot form a class by being similarly bland.
* Words with distinctive profiles that are alike (cosine of their profiles) form a CLASS.  A class
  is a manufactured symbol: its bit is 1 for an event that contains any member.  The ledger can
  then hang paths on it (``L0>L0``: the class in one event predicts the class in the next), which is
  a representational distinction the roots could not express.
* A class also has a coordinate: where its events sit on the five roots (the mean waveform ranks of
  the events that contained it), so a representation built on it still lands on a crystal.

Only ``LEX_SLOTS`` classes are held at a time; membership is re-derived from current evidence.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

import hashlib
import math
from typing import Any, Dict, Iterable, List, Mapping, Optional, Set, Tuple

LEX_SLOTS = 4
_AXES = ("X", "T", "N", "B", "A")


class LexicalStructure:
    def __init__(self, *, min_count: int = 20, max_vocab: int = 4000, successor_cap: int = 64,
                 discover_every: int = 500, similarity: float = 0.6, min_kl: float = 0.5,
                 event_sample: int = 12) -> None:
        self._min, self._max_vocab, self._cap = int(min_count), int(max_vocab), int(successor_cap)
        self._every, self._sim, self._min_kl, self._sample_n = int(discover_every), float(similarity), float(min_kl), int(event_sample)
        self._count: Dict[str, int] = {}
        self._succ: Dict[str, Dict[str, int]] = {}
        self._succ_total: Dict[str, int] = {}
        self._succ_mass = 0
        self._last: Dict[str, Tuple[str, List[str]]] = {}
        self._members: List[Set[str]] = [set() for _ in range(LEX_SLOTS)]
        # Slot names are developmental handles, not permanent identities.
        # Every genuinely new occupant advances the slot epoch so an earned
        # L0@2 structure can never inherit L0@1's evidence by accident.
        self._epochs: List[int] = [0] * LEX_SLOTS
        self._wave: List[List[float]] = [[0.0] * 5 for _ in range(LEX_SLOTS)]
        self._wave_n: List[int] = [0] * LEX_SLOTS
        self._events = 0
        self._stale: List[int] = [0] * LEX_SLOTS     # rounds a held class has gone unconfirmed

    # ---------------------------------------------------------------- intake
    def _sample(self, words: List[str]) -> List[str]:
        """Short events (a greeting) are kept whole; long ones are thinned by a stable hash."""
        if len(words) <= self._sample_n:
            return words
        return sorted(words, key=lambda w: hashlib.md5(w.encode("utf-8")).hexdigest())[: self._sample_n]

    def observe(self, tokens: Iterable[str], stream: str, episode_id: str) -> Tuple[Tuple[int, ...], bool]:
        """Admit one event's words.  Returns (class bits for this event, classes changed)."""
        full = [str(t) for t in dict.fromkeys(tokens or []) if len(str(t)) >= 2]
        sample = self._sample(full)
        prev = self._last.get(str(stream))
        if prev is not None and prev[0] == str(episode_id) and prev[1] and sample:
            for w in prev[1]:
                d = self._succ.setdefault(w, {})
                for v in sample:
                    d[v] = d.get(v, 0) + 1
                if len(d) > 4 * self._cap:
                    for k in sorted(d, key=d.get)[: len(d) - 2 * self._cap]:
                        del d[k]
            for v in sample:
                self._succ_total[v] = self._succ_total.get(v, 0) + len(prev[1])
            self._succ_mass += len(prev[1]) * len(sample)
        for w in sample:
            self._count[w] = self._count.get(w, 0) + 1
        self._last[str(stream)] = (str(episode_id), sample)
        self._events += 1
        if len(self._count) > self._max_vocab:
            for w in sorted(self._count, key=self._count.get)[: len(self._count) - int(0.8 * self._max_vocab)]:
                self._count.pop(w, None)
                self._succ.pop(w, None)
        changed = self._discover() if self._events % self._every == 0 else False
        return self.bits(full), changed

    def bits(self, words: Iterable[str]) -> Tuple[int, ...]:
        present = set(words or [])
        return tuple(1 if (m and not m.isdisjoint(present)) else 0 for m in self._members)

    def note_waveform(self, bits: Iterable[int], waveform: Iterable[float]) -> None:
        wave = list(waveform or [])
        if len(wave) != 5:
            return
        for k, b in enumerate(list(bits)[:LEX_SLOTS]):
            if b:
                self._wave_n[k] += 1
                for i in range(5):
                    self._wave[k][i] += float(wave[i])

    # ------------------------------------------------------------- discovery
    def _profiles(self) -> Dict[str, Tuple[float, Dict[str, float], float]]:
        mass = max(1, self._succ_mass)
        out = {}
        for w, c in self._count.items():
            d = self._succ.get(w)
            if c < self._min or not d:
                continue
            total = sum(d.values())
            vec, kl = {}, 0.0
            for v, n in d.items():
                p, p0 = n / total, self._succ_total.get(v, 1) / mass
                expected = total * p0
                # A follower counts only when it is well beyond what chance gives (>= 5 and 4 sigma over):
                # coincidences among bland words must never look like a relation.
                if n < 5 or n <= expected + 4.0 * math.sqrt(expected):
                    continue
                if p > p0:
                    vec[v] = math.log(p / p0)
                    kl += p * math.log(p / p0)
            if vec and kl >= self._min_kl:
                out[w] = (kl, vec, math.sqrt(sum(x * x for x in vec.values())))
        return out

    def _discover(self) -> bool:
        prof = self._profiles()
        words = sorted(prof, key=lambda w: -prof[w][0])[:300]
        parent = {w: w for w in words}

        def root(w: str) -> str:
            while parent[w] != w:
                parent[w] = parent[parent[w]]
                w = parent[w]
            return w

        for i, a in enumerate(words):
            va, na = prof[a][1], prof[a][2]
            for b in words[i + 1:]:
                vb, nb = prof[b][1], prof[b][2]
                small, big = (va, vb) if len(va) <= len(vb) else (vb, va)
                dot = sum(x * big.get(k, 0.0) for k, x in small.items())
                if na > 0 and nb > 0 and dot / (na * nb) >= self._sim:
                    parent[root(a)] = root(b)
        groups: Dict[str, Set[str]] = {}
        for w in words:
            groups.setdefault(root(w), set()).add(w)
        found = [(len(g) * sum(prof[w][0] for w in g) / len(g), g) for g in groups.values() if len(g) >= 2]
        found.sort(key=lambda t: -t[0])
        changed, taken = False, set()
        for _, g in found:                                   # keep a slot for the class it already is
            for k, held in enumerate(self._members):
                if k not in taken and held and len(held & g) / len(held | g) >= 0.5:
                    if held != g:
                        self._members[k], changed = set(g), True
                    taken.add(k)
                    break
            else:
                free = next((k for k, held in enumerate(self._members) if not held and k not in taken), None)
                if free is not None:
                    self._epochs[free] += 1
                    self._members[free], changed = set(g), True
                    # A new identity starts with a clean coordinate history.
                    self._wave[free], self._wave_n[free] = [0.0] * 5, 0
                    taken.add(free)
        for k, held in enumerate(self._members):
            if k in taken:
                self._stale[k] = 0
            elif held:                                       # a class evidence no longer re-finds is dropped
                self._stale[k] += 1
                if self._stale[k] >= 2:
                    self._members[k], self._stale[k], changed = set(), 0, True
        return changed

    # ------------------------------------------------------------ inspection
    def epoch(self, slot: int) -> int:
        return self._epochs[slot] if 0 <= slot < LEX_SLOTS else 0

    def epoch_vector(self) -> Tuple[int, ...]:
        return tuple(self._epochs)

    def identity(self, slot: int) -> str:
        return f"L{slot}@{self.epoch(slot)}"

    def kernel(self, slot: int, member_limit: int = 16) -> Dict[str, Any]:
        """Compact recognition substrate for the current lexical class.

        This retains the class relation's lexical anchors and coordinate, not
        the examples that produced it.  The epoch makes the identity stable
        after the developmental slot is later reused.
        """
        if not (0 <= slot < LEX_SLOTS) or not self._members[slot]:
            return {}
        return {
            "symbol": f"L{slot}",
            "identity": self.identity(slot),
            "epoch": self.epoch(slot),
            "members": sorted(self._members[slot])[: max(2, int(member_limit))],
            "coordinate": self.coordinate(slot),
        }

    def active_slots(self) -> List[int]:
        return [k for k, m in enumerate(self._members) if m]

    def coordinate(self, slot: int) -> Dict[str, float]:
        """Where this class's events sit on the five roots (shares of the mean waveform ranks)."""
        n = self._wave_n[slot] if 0 <= slot < LEX_SLOTS else 0
        if n == 0:
            return {ax: 0.2 for ax in _AXES}
        mean = [self._wave[slot][i] / n for i in range(5)]
        total = sum(mean) or 1.0
        return {ax: mean[i] / total for i, ax in enumerate(_AXES)}

    def describe(self) -> Dict[str, List[str]]:
        return {f"L{k}": sorted(m)[:16] for k, m in enumerate(self._members) if m}

    def state(self) -> Dict[str, Any]:
        return {"v": 2, "members": [sorted(m) for m in self._members], "epochs": list(self._epochs),
                "wave": self._wave, "wave_n": self._wave_n}

    def restore(self, state: Mapping[str, Any]) -> None:
        members = list(state.get("members") or [])
        self._members = [set(members[k]) if k < len(members) else set() for k in range(LEX_SLOTS)]
        epochs = list(state.get("epochs") or [])
        # Legacy state had no epochs; an occupied restored slot is its first identity.
        self._epochs = [int(epochs[k]) if k < len(epochs) else (1 if self._members[k] else 0) for k in range(LEX_SLOTS)]
        self._stale = [0] * LEX_SLOTS
        wave = list(state.get("wave") or [])
        self._wave = [list(map(float, wave[k])) if k < len(wave) else [0.0] * 5 for k in range(LEX_SLOTS)]
        counts = list(state.get("wave_n") or [])
        self._wave_n = [int(counts[k]) if k < len(counts) else 0 for k in range(LEX_SLOTS)]

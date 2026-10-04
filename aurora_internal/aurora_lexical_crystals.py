"""
aurora_lexical_crystals.py
==========================

The lexicon's concept channels, derived FROM the crystals.

A word crystallized into a channel (``N:POLARITY``) is a ``word`` facet on the crystal at that
channel's axis coordinate; the channel's character (POLARITY, MAGNITUDE, ...) is carried in the
facet id.  The lexicon's ``find_by_noncomp`` / ``concept_words`` read their candidates from the
crystals through this sink, so there is ONE place a word's channel lives and composition's
secondary crystal lookup and its primary channel lookup are the same lookup.  The index here is a
view rebuilt from the crystals on attach (nothing separate is persisted), and ``associate``
keeps the crystals current as words move between channels.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Set

from aurora_internal.aurora_representation_crystals import _crystal_for

try:
    from concept_crystal import _DPSCrystalFacet
except Exception:  # pragma: no cover
    _DPSCrystalFacet = None

AXES = ("X", "T", "N", "B", "A")
_MARK = "_wc_"


class LexicalCrystals:
    def __init__(self, registry: Any) -> None:
        self.registry = registry
        self._cache: Dict[tuple, str] = {}
        self._index: Dict[str, Set[str]] = {}

    @staticmethod
    def _split(noncomp_id: str):
        axis, _, character = str(noncomp_id).partition(":")
        return axis, character

    @classmethod
    def coordinate(cls, noncomp_id: str) -> Dict[str, float]:
        axis, _ = cls._split(noncomp_id)
        return {a: (1.0 if a == axis else 0.0) for a in AXES}

    def _fid(self, crystal: Any, character: str, word: str) -> str:
        return f"{crystal.crystal_id}{_MARK}{character}_{hashlib.md5(word.encode('utf-8')).hexdigest()[:8]}"

    def place(self, word: str, noncomp_id: str) -> bool:
        axis, character = self._split(noncomp_id)
        word = str(word or "").strip().lower()
        if axis not in AXES or not character or not word or _DPSCrystalFacet is None:
            return False
        crystal = _crystal_for(self.registry, self._cache, self.coordinate(noncomp_id))
        fid = self._fid(crystal, character, word)
        if fid not in crystal.facets:
            facet = _DPSCrystalFacet(facet_id=fid, role="word", content=word, confidence=0.5)
            facet.coherence, facet.resonance, facet.potential = 0.5, 0.5, 0.5
            crystal.facets[fid] = facet
        self._index.setdefault(str(noncomp_id), set()).add(word)
        return True

    def remove(self, word: str, noncomp_id: str) -> None:
        axis, character = self._split(noncomp_id)
        word = str(word or "").strip().lower()
        if axis not in AXES or not character:
            return
        crystal = _crystal_for(self.registry, self._cache, self.coordinate(noncomp_id))
        crystal.facets.pop(self._fid(crystal, character, word), None)
        self._index.get(str(noncomp_id), set()).discard(word)

    def move(self, word: str, old: str, new: str) -> None:
        if old and old != new:
            self.remove(word, old)
        if new:
            self.place(word, new)

    def words(self, noncomp_id: str) -> List[str]:
        return sorted(self._index.get(str(noncomp_id), ()))

    def rebuild_index(self) -> int:
        """Derive the channel view from the crystals themselves."""
        self._index = {}
        total = 0
        for crystal in self.registry.all_crystals():
            sig = getattr(crystal, "constraint_signature", None) or {}
            for fid, facet in getattr(crystal, "facets", {}).items():
                if _MARK in str(fid) and getattr(facet, "role", "") == "word":
                    character = str(fid).split(_MARK, 1)[1].split("_", 1)[0]
                    axis = max(AXES, key=lambda a: abs(float(sig.get(a, 0.0) or 0.0)))
                    self._index.setdefault(f"{axis}:{character}", set()).add(str(facet.content))
                    total += 1
        return total

    def attach(self, lexicon: Any) -> int:
        """Make the crystals the lexicon's channel store; place every word already in a channel."""
        self.rebuild_index()
        placed = 0
        for entry in list(getattr(lexicon, "entries", {}).values()):
            if getattr(entry, "noncomp_id", None) and self.place(getattr(entry, "word", ""), entry.noncomp_id):
                placed += 1
        lexicon._crystal_sink = self
        return placed

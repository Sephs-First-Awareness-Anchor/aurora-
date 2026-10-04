"""
aurora_representation_crystals.py
=================================

Representations live INSIDE the crystals.  No separate record keeping.

A discovered (subject, axis-path) representation has a coordinate: its path's
root weights, e.g. ``T>N`` sits at (T 0.5, N 0.5).  That is exactly a crystal's
identity (its axis bucket), so the representation is a facet on the crystal at
that coordinate, beside every other kind of facet the crystal hosts.  Because
all crystals are one store, what composition reads is what is recorded here.

    facet role   ``lsa:res:<subject>:<path>``   (the ``lsa:`` prefix is what the
                 registry's own ``record_receiver_outcome`` applies evidence to)
    content      the compact computed record: expectation table, consequence
                 sums, status.  Reading it back IS the reuse: nothing is
                 recomputed, and a fresh session resumes where evidence stood.
    consequence  applied to that very facet through the registry's own
                 ``record_receiver_outcome`` (strengthen / weaken), and the
                 crystal's own ``use()`` / ``evolve()`` carry its depth.

Words tied to a shape by the act they occur in are ``word`` facets on the same
crystal.  Composition already draws word candidates from crystals whose
constraint signature resonates with the live dominant axis, reading facets with
role ``word``; nothing is composed here and no composition code changes.  Only
words that exist in her own lexicon are written, and only ones that sit at the
shape's high pole, so the generator keeps full authority over what it says.
"""
# Authors: Sunni (Sir) Morningstar & Cael Devo
from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

try:  # the facet class the registry itself writes
    from concept_crystal import _DPSCrystalFacet
except Exception:  # pragma: no cover - legacy builds without DPS crystals
    _DPSCrystalFacet = None

AXES = ("X", "T", "N", "B", "A")
ROLE_PREFIX = "lsa:res:"
_MAX_WORD_FACETS = 12      # words this writer places on one crystal
_MIN_WORD_LIFT = 1.0       # bits of separation between the target root's poles
HYP_PREFIX = "hyp:"        # hypotheses are NOT semantic grounding, so never the registry's "lsa:" prefix


def _crystal_for(registry: Any, cache: Dict[tuple, str], ax: Mapping[str, float]) -> Any:
    """The crystal at a coordinate, remembered so repeated writes never rescan the store."""
    key = tuple(round(float(ax.get(k, 0.0)), 3) for k in AXES)
    crystal = registry.crystal_by_id(cache.get(key, ""))
    if crystal is None:
        crystal = registry.crystal_at(dict(ax))
        cache[key] = crystal.crystal_id
    return crystal


class RepresentationCrystals:
    """Reads and writes representation records on the unified crystal store."""

    def __init__(self, registry: Any) -> None:
        self.registry = registry
        self._cache: Dict[tuple, str] = {}

    @staticmethod
    def coordinate(path: str, extra: Optional[Mapping[str, Mapping[str, float]]] = None) -> Dict[str, float]:
        parts = str(path).split(">")
        out = {ax: 0.0 for ax in AXES}
        for part in parts:
            root = part.upper()
            if root in out:     # a tail symbol (t, n) is the LOW pole of its root: a negative component
                out[root] += (-1.0 if part in ("t", "n") else 1.0) / float(len(parts))
            elif extra and part in extra:   # a word class sits where ITS events sit on the roots
                for key, value in dict(extra[part]).items():
                    if key in out:
                        out[key] += float(value) / float(len(parts))
        return out

    @staticmethod
    def path_key(subject: str, path: str) -> str:
        return f"res:{subject}:{path}"

    @classmethod
    def role(cls, subject: str, path: str) -> str:
        return f"lsa:{cls.path_key(subject, path)[:30]}"      # observe_lsa truncates to 30

    @staticmethod
    def _facet(crystal: Any, role: str) -> Any:
        return next((f for f in crystal.facets.values() if f.role == role), None)

    def upsert(
        self,
        record: Mapping[str, Any],
        *,
        delta: Mapping[str, float],
        words: Optional[List[Mapping[str, Any]]] = None,
        known_word: Optional[Callable[[str], bool]] = None,
    ) -> bool:
        reg = self.registry
        ax = self.coordinate(str(record["path"]), record.get("lexc"))
        identity_path = str(record.get("identity_path") or record["path"])
        role = self.role(str(record["subject"]), identity_path)
        crystal = reg.query(ax)
        facet = self._facet(crystal, role) if crystal is not None else None
        if facet is None:
            crystal = reg.observe_lsa(ax, self.path_key(str(record["subject"]), identity_path))
            facet = self._facet(crystal, role)
        if facet is None:
            return False
        facet.content = json.dumps(record, separators=(",", ":"), sort_keys=True)
        if float(delta.get("n", 0.0)) > 0.0:
            # What the expectation has done since the last sync, applied to the facet itself.
            reg.record_receiver_outcome(
                crystal.crystal_id, role,
                positive=float(delta.get("gain", 0.0)) > 0.0,
                outcome_score=float(delta.get("hits", 0.0)) / float(delta["n"]),
                evidence_id=f"{record['id']}:{int(float(record['uni']['n']))}",
            )
        # Words are tied to the POLE of the target root they occur at.  The pole is part of the
        # coordinate (sign of the target component), so a high-pole word and a low-pole word
        # never share a crystal.  The renderer's resonance uses abs(), so both still resonate.
        high = [w for w in (words or []) if float(w.get("lift", 0.0) or 0.0) > 0]
        low = [{"word": w["word"], "lift": -float(w["lift"])} for w in (words or []) if float(w.get("lift", 0.0) or 0.0) < 0]
        self._place_words(crystal, high, known_word)
        if low:
            pole_ax = dict(ax)
            root = str(record["target"]).upper()
            pole_ax[root] = -pole_ax.get(root, 0.0)
            self._place_words(_crystal_for(reg, self._cache, pole_ax), low, known_word)
        return True

    def _place_words(self, crystal: Any, words: List[Mapping[str, Any]], known_word: Optional[Callable[[str], bool]]) -> None:
        if _DPSCrystalFacet is None:
            return
        have = {str(f.content): f for f in crystal.facets.values() if f.role == "word"}
        ours = sum(1 for fid in crystal.facets if "_rw_" in str(fid))
        for item in words:
            word = str(item.get("word", "")).strip().lower()
            lift = float(item.get("lift", 0.0) or 0.0)
            if not word or lift < _MIN_WORD_LIFT or word in have:
                continue
            if known_word is not None and not known_word(word):
                continue
            if ours >= _MAX_WORD_FACETS:
                break
            fid = f"{crystal.crystal_id}_rw_{hashlib.md5(word.encode('utf-8')).hexdigest()[:8]}"
            facet = _DPSCrystalFacet(facet_id=fid, role="word", content=word, confidence=min(0.9, 0.3 + lift / 12.0))
            facet.coherence, facet.resonance, facet.potential = 0.6, 0.5, 0.5
            facet.frequency = min(1.0, float(getattr(crystal, "usage_count", 0)) / 40.0)
            crystal.facets[fid] = facet
            ours += 1

    def load_all(self) -> List[Dict[str, Any]]:
        """Every representation record on every crystal, decoded."""
        out: List[Dict[str, Any]] = []
        for crystal in self.registry.all_crystals():
            for facet in getattr(crystal, "facets", {}).values():
                if str(getattr(facet, "role", "")).startswith(ROLE_PREFIX):
                    try:
                        record = json.loads(str(facet.content))
                    except Exception:
                        continue
                    if isinstance(record, dict) and record.get("id"):
                        out.append(record)
        return out

    def recall(self, *, subject: Optional[str] = None, path: Optional[str] = None,
               target: Optional[str] = None) -> List[Dict[str, Any]]:
        """Already-computed records, straight from the crystals (nothing recomputed)."""
        return [
            r for r in self.load_all()
            if (subject is None or r.get("subject") == subject)
            and (path is None or r.get("path") == path)
            and (target is None or r.get("target") == target)
        ]


class HypothesisCrystals:
    """Discovery research kept on the crystals: candidate paths are HYPOTHESES.

    Each path still under test is a ``hyp:res:<subject>:<path>`` facet on the crystal at its
    coordinate, carrying its expectation table and evidence so far, so continued discovery
    resumes from the crystals instead of from a log of its own.  One ``hyp:cal:ledger`` facet
    carries the calibration that keeps bits consistent across sessions (compressed running
    distributions, stream cursors).  The ``hyp:`` prefix keeps these from ever counting as
    semantic grounding.  Facets are touched on every write so decay never fades live research.
    """

    CAL_ROLE = "hyp:cal:ledger"

    def __init__(self, registry: Any) -> None:
        self.registry = registry
        self._cache: Dict[tuple, str] = {}

    @staticmethod
    def role(subject: str, path: str) -> str:
        return f"{HYP_PREFIX}res:{subject}:{path}"

    def _upsert(self, ax: Mapping[str, float], role: str, record: Mapping[str, Any]) -> bool:
        if _DPSCrystalFacet is None:
            return False
        crystal = _crystal_for(self.registry, self._cache, ax)
        facet = next((f for f in crystal.facets.values() if f.role == role), None)
        if facet is None:
            fid = f"{crystal.crystal_id}_h_{hashlib.md5(role.encode('utf-8')).hexdigest()[:10]}"
            facet = _DPSCrystalFacet(facet_id=fid, role=role, content="", confidence=0.2)
            facet.coherence, facet.resonance, facet.potential = 0.3, 0.2, 0.5     # potential: it is a question
            crystal.facets[fid] = facet
        facet.content = json.dumps(record, separators=(",", ":"), sort_keys=True)
        facet.last_accessed = time.time()
        return True

    def write(self, calibration: Mapping[str, Any], hypotheses: List[Mapping[str, Any]]) -> int:
        wrote = 0
        neutral = {ax: 0.5 for ax in AXES}
        if self._upsert(neutral, self.CAL_ROLE, calibration):
            wrote += 1
        for rec in hypotheses:
            identity_path = str(rec.get("identity_path") or rec["path"])
            if self._upsert(RepresentationCrystals.coordinate(str(rec["path"]), rec.get("lexc")), self.role(str(rec["subject"]), identity_path), rec):
                wrote += 1
        return wrote

    LEX_ROLE = "hyp:lex:structure"

    def write_lexical(self, state: Mapping[str, Any]) -> bool:
        """The word classes found so far, kept on the crystals like every other hypothesis."""
        return self._upsert({ax: 0.5 for ax in AXES}, self.LEX_ROLE, state)

    def read_lexical(self) -> Dict[str, Any]:
        for crystal in self.registry.all_crystals():
            for facet in getattr(crystal, "facets", {}).values():
                if str(getattr(facet, "role", "")) == self.LEX_ROLE:
                    try:
                        return dict(json.loads(str(facet.content)))
                    except Exception:
                        return {}
        return {}

    def read(self) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        calibration: Dict[str, Any] = {}
        hypotheses: List[Dict[str, Any]] = []
        for crystal in self.registry.all_crystals():
            for facet in getattr(crystal, "facets", {}).values():
                role = str(getattr(facet, "role", ""))
                if not role.startswith(HYP_PREFIX):
                    continue
                try:
                    record = json.loads(str(facet.content))
                except Exception:
                    continue
                if role == self.CAL_ROLE and isinstance(record, dict):
                    calibration = record
                elif isinstance(record, dict) and record.get("path"):
                    hypotheses.append(record)
        return calibration, hypotheses

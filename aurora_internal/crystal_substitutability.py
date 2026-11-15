# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Words that stand in for one another, found from where they are used (Sir, 2026-11-15).

Her word-class finder (`LexicalStructure`) profiles each word by its DISTINCTIVE followers and says outright that diffuse words carry no profile, so the
words every sentence leans on (and, or, but, that, ...) can never form a class there.  What marks them is the opposite: they turn up everywhere, in the
same places as one another.  This module measures exactly that, from plain token lists, with no label, role or gloss involved:

  * `ContextProfiles.observe(tokens)`   counts, for every word, the words just before it and just after it (an event's edges are contexts too).
  * `similarity(a, b)`                  how alike the two words' contexts are, in [0, 1]: 1 - Jensen-Shannon divergence between their context
                                        distributions, before and after separately and combined geometrically (alike on both sides), times how
                                        well each has been seen (`x / (x + k)`, so a rare word cannot match anything yet).
  * `breadth(w)` / `function_likeness`  how many distinct contexts a word turns up in, as a degree (a gradient; nothing is called a function word).
  * `exemplar_classes(...)`             for each word taken as an exemplar, the words that substitute for it, each at its similarity, and how far the
                                        group is one class (mass x how alike its members are to each other).  `top` only limits what is returned.
  * `place_substitutes` / `class_members`   the links, as counted association evidence (source `lexical_class`), ready for `crystal_grammar`.

Isolated and pure: it imports nothing from Aurora, reads token lists, and touches no crystal.  Every number is a degree; no value is compared with a
cut-off.
"""
from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

REF_SEEN = 10.0           # times a word has been seen at which its contexts are half trusted (a reference, not a bar)
REF_BREADTH = 20.0        # distinct contexts at which breadth is one half
REF_MASS = 5.0            # mass of substitutes at which a class is half-promoted (as in crystal_promotion)
START, END = "<s>", "</s>"


def _degree(x: float, k: float) -> float:
    x = max(0.0, float(x))
    return x / (x + max(1e-12, float(k)))


def _js_similarity(p: Mapping[Any, float], q: Mapping[Any, float]) -> float:
    """1 - Jensen-Shannon divergence (base 2) between two count distributions: 1 for identical, 0 for disjoint."""
    sp, sq = float(sum(p.values())), float(sum(q.values()))
    if sp <= 0.0 or sq <= 0.0:
        return 0.0
    jsd = 0.0
    for k in set(p) | set(q):
        a, b = p.get(k, 0.0) / sp, q.get(k, 0.0) / sq
        m = 0.5 * (a + b)
        if a > 0.0:
            jsd += 0.5 * a * math.log2(a / m)
        if b > 0.0:
            jsd += 0.5 * b * math.log2(b / m)
    return max(0.0, min(1.0, 1.0 - jsd))


class ContextProfiles:
    def __init__(self) -> None:
        self._n: Dict[str, int] = {}
        self._ctx: Dict[str, Dict[str, Dict[str, int]]] = {}

    # -- intake -------------------------------------------------------------------------------------------------------------------------------
    def observe(self, tokens: Iterable[str]) -> int:
        """One event's words, in order.  Returns how many words were counted.  Words shorter than one character are skipped."""
        ws = [str(t).lower() for t in tokens or [] if str(t)]
        padded = [START] + ws + [END]
        for i, w in enumerate(ws, start=1):
            self._n[w] = self._n.get(w, 0) + 1
            d = self._ctx.setdefault(w, {"L": {}, "R": {}})
            for side, c in (("L", padded[i - 1]), ("R", padded[i + 1])):
                d[side][c] = d[side].get(c, 0) + 1
        return len(ws)

    # -- reading ----------------------------------------------------------------------------------------------------------------------------
    def count(self, word: str) -> int:
        return self._n.get(str(word).lower(), 0)

    def vocabulary(self) -> List[str]:
        return sorted(self._n)

    def distinct_contexts(self, word: str) -> int:
        d = self._ctx.get(str(word).lower(), {})
        return len(d.get("L", {})) + len(d.get("R", {}))

    def similarity(self, a: str, b: str) -> float:
        a, b = str(a).lower(), str(b).lower()
        if a == b or a not in self._ctx or b not in self._ctx:
            return 0.0
        seen = _degree(self._n[a], REF_SEEN) * _degree(self._n[b], REF_SEEN)
        # Standing in for one another means alike on BOTH sides (what comes before and what comes after): the geometric mean, so a word that only
        # shares one side (and, runs: both follow nouns) is not mistaken for a substitute.
        left = _js_similarity(self._ctx[a]["L"], self._ctx[b]["L"])
        right = _js_similarity(self._ctx[a]["R"], self._ctx[b]["R"])
        return seen * math.sqrt(left * right)

    def breadth(self, word: str) -> float:
        """How widely it is used: distinct contexts as a degree.  A gradient, never a class."""
        return _degree(self.distinct_contexts(word), REF_BREADTH)

    def function_likeness(self, word: str) -> float:
        """Broad and well seen: breadth x how often it has been seen.  The words every sentence leans on score highest; nothing is cut off."""
        return self.breadth(word) * _degree(self.count(word), REF_SEEN)

    def substitutes(self, word: str, vocabulary: Optional[Iterable[str]] = None, top: Optional[int] = None) -> List[Tuple[str, float]]:
        """(word, similarity) strongest first, for every other word that stands in for it at all.  `top` only limits how many are returned."""
        pool = sorted(set(vocabulary) if vocabulary is not None else self._n)
        out = [(w, s) for w in pool for s in [self.similarity(word, w)] if s > 0.0]
        out.sort(key=lambda kv: (-kv[1], kv[0]))
        return out[:top] if top else out

    # -- state --------------------------------------------------------------------------------------------------------------------------------
    def state(self) -> Dict[str, Any]:
        return {"v": 1, "n": dict(self._n), "ctx": {w: {"L": dict(d["L"]), "R": dict(d["R"])} for w, d in self._ctx.items()}}

    def restore(self, state: Mapping[str, Any]) -> None:
        self._n = {str(w): int(n) for w, n in (state.get("n") or {}).items()}
        self._ctx = {str(w): {"L": {str(c): int(k) for c, k in (d.get("L") or {}).items()}, "R": {str(c): int(k) for c, k in (d.get("R") or {}).items()}}
                     for w, d in (state.get("ctx") or {}).items()}


def class_degree(profiles: ContextProfiles, exemplar: str, members: Mapping[str, float], fan: int = 16) -> float:
    """How far the exemplar's substitutes are ONE class: their mass x how alike they are to one another (mean pairwise similarity over the strongest `fan`,
    weighted by how fully each belongs).  A single substitute is not a class; many that are alike to each other are."""
    mass = sum(members.values())
    if mass <= 0.0:
        return 0.0
    strongest = sorted(members, key=lambda w: (-members[w], w))[:fan]
    num = den = 0.0
    for i in range(len(strongest)):
        for j in range(i + 1, len(strongest)):
            wt = members[strongest[i]] * members[strongest[j]]
            num += wt * profiles.similarity(strongest[i], strongest[j])
            den += wt
    unity = 0.0 if den <= 0.0 else num / den
    return _degree(mass, REF_MASS) * unity


def exemplar_classes(profiles: ContextProfiles, vocabulary: Optional[Iterable[str]] = None, top: Optional[int] = None,
                     fan: int = 16) -> List[Tuple[str, float, Dict[str, float]]]:
    """(exemplar, class degree, {word: similarity}) strongest class first.  Each word is tried as the exemplar of the words that substitute for it."""
    pool = sorted(set(vocabulary) if vocabulary is not None else profiles.vocabulary())
    rows = []
    for h in pool:
        members = {w: s for w, s in profiles.substitutes(h, pool)}
        d = class_degree(profiles, h, members, fan)
        if d > 0.0:
            rows.append((h, d, members))
    rows.sort(key=lambda r: (-r[1], r[0]))
    return rows[:top] if top else rows


def class_members(exemplar: str, members: Mapping[str, float]) -> Dict[str, float]:
    """The class as `crystal_grammar.place_classes` takes it: the exemplar fully, and each substitute at its similarity."""
    out = {str(w): float(s) for w, s in members.items()}
    out[str(exemplar)] = 1.0
    return out


def place_substitutes(store: Any, profiles: ContextProfiles, vocabulary: Optional[Iterable[str]] = None, per_word: int = 8) -> int:
    """`substitutes_for` links as counted association evidence (source `lexical_class`), each word to its `per_word` strongest substitutes at its
    similarity.  `per_word` only limits how many links each word gets."""
    pool = sorted(set(vocabulary) if vocabulary is not None else profiles.vocabulary())
    n = 0
    for w in pool:
        for other, s in profiles.substitutes(w, pool, top=per_word):
            n += bool(store.add(w, other, "substitutes_for", ref=f"subst:{min(w, other)}:{max(w, other)}", source="lexical_class", strength=s))
    return n

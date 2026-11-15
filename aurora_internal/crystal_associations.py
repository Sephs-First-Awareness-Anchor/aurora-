# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Typed, provenance-carrying associations between crystals (build plan P1).

Not the DPS `crystal_links` graph: that one is geometric similarity of crystal vectors, kept in memory.  This is association by
recurrence, with its source, and it is separate on purpose.

Design (Sir): a sequence store keeps the same words over and over; a crystal store keeps a concept ONCE, with everything
associated to it attached.  So an association is one record per (a, b, type), holding the evidence for it, never one record per
occurrence.  Recording the same evidence again changes nothing (idempotent, keyed by the evidence's own reference).

Provenance (the same rule as the rest of the development work): only associations that recurrence produced count toward a
crystal's `connections`.  Associations assigned from a label (a part-of-speech heuristic), looked up from outside, seeded, or derived
without a stated premise are KEPT, with their source, but do not count; they can become counted only through recurrence.
Nothing here writes to a running system: `apply_to_crystals` is the one place that changes `Crystal.connections`, and only
when asked, bounded per crystal.  Nothing here is called from cognition or speech.

Isolated module: no imports from the rest of Aurora.
"""
from __future__ import annotations

import json
import os
import tempfile
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

VERSION = 1

# What produced an association -> how it is treated.  An unlisted source is "unknown" and never counts.
SOURCE_BASIS: Dict[str, str] = {
    "co-occurrence": "recurrence",        # the two were used together, repeatedly
    "co-expression": "recurrence",        # the two were expressed together
    "research": "looked_up",              # arrived from outside lookup; held only once confirmed another way
    "backfill_role_heuristic": "heuristic",   # assigned from a part-of-speech label, not from experience
    "seeded": "seeded",                   # placed there, not learned
    "adjacency": "unattributed",          # derived without a stated premise
    "axis_embodiment": "unattributed",
    "definition_analysis": "unattributed",
    "supposed": "supposed",               # imagined, simulated or dreamed: kept, never counted
    "overheard": "overheard",             # said near her, not to her: a lead, never testimony
    "told": "told",                       # said to her (the propositional store's own bases)
    "observed": "observed",
    "corrected": "corrected",
}
COUNTED_BASES = frozenset({"recurrence", "told", "observed", "corrected"})
UNKNOWN = "unknown"

# Types that mean the same from either end; every other type (including every predicate said between two things) runs from a to b.
SYMMETRIC_TYPES = frozenset({"related_to", "opposite_of", "contrasts"})


def basis_of(source: str) -> str:
    return SOURCE_BASIS.get(str(source or ""), UNKNOWN)


def _key(a: str, b: str, rtype: str) -> Tuple[str, str, str]:
    a, b, rtype = str(a), str(b), str(rtype)
    if rtype in SYMMETRIC_TYPES and b < a:
        a, b = b, a
    return (a, b, rtype)


class AssociationStore:
    """One record per (a, b, type); each holds its evidence grouped by basis."""

    def __init__(self) -> None:
        # key -> {"evidence": {ref: {"basis", "source", "strength", "confidence"}}}
        self._links: Dict[Tuple[str, str, str], Dict[str, Dict[str, Any]]] = {}

    # ---- writing ----------------------------------------------------------------------------------------------------
    def add(self, a: str, b: str, rtype: str, *, ref: str, source: str,
            strength: float = 1.0, confidence: float = 1.0, polarity: int = 1, weight: float = 1.0) -> bool:
        """Record one piece of evidence for an association.  `ref` identifies the evidence itself, so recording it again is a no-op.
        Returns True if it was new."""
        if not a or not b or str(a) == str(b) or not ref:
            return False
        ev = self._links.setdefault(_key(a, b, rtype), {})
        if str(ref) in ev:
            return False
        ev[str(ref)] = {
            "basis": basis_of(source), "source": str(source),
            "strength": max(0.0, min(1.0, float(strength))),
            "confidence": max(0.0, min(1.0, float(confidence))),
            "polarity": -1 if int(polarity) < 0 else 1,          # -1: said NOT to hold
            "weight": max(0.0, float(weight)),                    # how many exposures this record stands for (1 for a single observation)
        }
        return True

    # ---- reading ----------------------------------------------------------------------------------------------------
    def __len__(self) -> int:
        return len(self._links)

    def records(self) -> List[Tuple[str, str, str]]:
        """Every (a, b, type) held, counted or not, in a stable order."""
        return sorted(self._links)

    def evidence(self, a: str, b: str, rtype: str) -> Dict[str, Dict[str, Any]]:
        return dict(self._links.get(_key(a, b, rtype), {}))

    def strength(self, a: str, b: str, rtype: str) -> float:
        """What counts: the weighted mean, over the counted evidence, of strength x confidence with its sign (evidence that it does NOT hold pulls
        down, continuously), floored at 0.  0.0 if there is no counted evidence, however much uncounted evidence exists."""
        counted = [e for e in self._links.get(_key(a, b, rtype), {}).values() if e["basis"] in COUNTED_BASES]
        w = sum(e.get("weight", 1.0) for e in counted)
        if w <= 0.0:
            return 0.0
        return max(0.0, sum(e.get("polarity", 1) * e["strength"] * e["confidence"] * e.get("weight", 1.0) for e in counted) / w)

    def contested(self, a: str, b: str, rtype: str) -> float:
        """0 when the counted evidence all points one way, up to 1 when it is split evenly: how much it is argued over."""
        ev = [e for e in self._links.get(_key(a, b, rtype), {}).values() if e["basis"] in COUNTED_BASES]
        pos = sum(e["strength"] * e["confidence"] * e.get("weight", 1.0) for e in ev if e.get("polarity", 1) > 0)
        neg = sum(e["strength"] * e["confidence"] * e.get("weight", 1.0) for e in ev if e.get("polarity", 1) < 0)
        tot = pos + neg
        return 0.0 if tot <= 0 else 2.0 * min(pos, neg) / tot

    def incoming(self, concept: str, rtype: str) -> Dict[str, float]:
        """Concepts x with a counted association x --rtype--> concept, and its strength: for `is_a` these are what the concept holds."""
        c, out = str(concept), {}
        for (a, b, t) in self._links:
            if t == rtype and b == c and a != c:
                s = self.strength(a, b, t)
                if s > 0.0:
                    out[a] = s
        return out

    def connections_for(self, concept: str) -> Dict[str, float]:
        """neighbour concept -> counted strength (the strongest across types), for neighbours with any counted strength."""
        out: Dict[str, float] = {}
        c = str(concept)
        for (a, b, rtype) in self._links:
            if c not in (a, b):
                continue
            other = b if a == c else a
            s = self.strength(a, b, rtype)
            if s > out.get(other, 0.0):
                out[other] = s
        return out

    def view(self, concept: str) -> Dict[str, Any]:
        """Everything attached to one concept, once: counted associations grouped by type, and the uncounted evidence summarised by basis."""
        c = str(concept)
        by_type: Dict[str, List[Dict[str, Any]]] = {}
        uncounted: Dict[str, int] = {}
        for (a, b, rtype), ev in self._links.items():
            if c not in (a, b):
                continue
            other = b if a == c else a
            s = self.strength(a, b, rtype)
            if s > 0.0:
                by_type.setdefault(rtype, []).append({
                    "with": other, "strength": round(s, 4),
                    "direction": "both" if rtype in SYMMETRIC_TYPES else ("out" if a == c else "in"),
                    "evidence": sum(1 for e in ev.values() if e["basis"] in COUNTED_BASES),
                })
            for e in ev.values():
                if e["basis"] not in COUNTED_BASES:
                    uncounted[e["basis"]] = uncounted.get(e["basis"], 0) + 1
        for lst in by_type.values():
            lst.sort(key=lambda r: -r["strength"])
        return {"concept": c, "counted": by_type, "uncounted_evidence": uncounted}

    def basis_counts(self) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for ev in self._links.values():
            for e in ev.values():
                out[e["basis"]] = out.get(e["basis"], 0) + 1
        return out

    # ---- persistence ------------------------------------------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {"version": VERSION,
                "links": [{"a": a, "b": b, "type": t, "evidence": ev} for (a, b, t), ev in sorted(self._links.items())]}

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "AssociationStore":
        s = cls()
        for row in (d or {}).get("links", []):
            s._links[_key(row["a"], row["b"], row["type"])] = {str(r): dict(e) for r, e in (row.get("evidence") or {}).items()}
        return s

    def save(self, path: str) -> None:
        """Atomic: write beside the target, then replace, so a partial file is never read."""
        d = os.path.dirname(os.path.abspath(path)) or "."
        os.makedirs(d, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".crystal_associations.", dir=d)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(self.to_dict(), fh, separators=(",", ":"))
            os.replace(tmp, path)
        except Exception:
            try:
                os.remove(tmp)
            except OSError:
                pass
            raise

    @classmethod
    def load(cls, path: str) -> "AssociationStore":
        try:
            with open(path, encoding="utf-8") as fh:
                return cls.from_dict(json.load(fh))
        except (OSError, ValueError, KeyError):
            return cls()


def project_oets(relations: Mapping[str, Mapping[str, Any]], store: Optional[AssociationStore] = None) -> AssociationStore:
    """Build (or extend) a store from the OETS web's `relations` mapping.  Every relation is kept with its source; only
    recurrence-based ones count.  Running it again on the same relations adds nothing."""
    store = store if store is not None else AssociationStore()
    for rid, r in (relations or {}).items():
        store.add(r.get("source_word"), r.get("target_word"), r.get("relation_type") or "related_to",
                  ref=str(r.get("relation_id") or rid), source=r.get("source_of_knowledge") or "",
                  strength=r.get("strength", 0.0) or 0.0, confidence=r.get("confidence", 0.0) or 0.0)
    return store


def project_assertions(relations: Mapping[str, Mapping[str, Any]], store: Optional[AssociationStore] = None) -> AssociationStore:
    """Add what was SAID between things (the propositional store's `assertion` records on OETS relations): each predicate becomes a typed association
    from subject to object.  Said-to-hold and said-NOT-to-hold are separate evidence of opposite sign, each weighing as many times as it was said, so
    an association argued over weakens smoothly (held minus denied, over all the times it was said) instead of flipping.  A latest correction decides (it stays as the only evidence; what came before stays in the
    relation's own history).  The basis is how it came to be held (told, observed, corrected).  Running it again adds nothing."""
    store = store if store is not None else AssociationStore()
    for rid, r in (relations or {}).items():
        a = r.get("assertion") or {}
        for pred, p in (a.get("predicates") or {}).items():
            n = int(p.get("n", 0) or 0)
            if n <= 0:
                continue
            bcounts = {k: int(v) for k, v in (p.get("basis") or {}).items() if v}
            base = max(bcounts, key=lambda k: (bcounts[k], k == "told")) if bcounts else "told"
            settled = p.get("settled")
            src, tgt, ref = r.get("source_word"), r.get("target_word"), str(r.get("relation_id") or rid)
            if settled:
                store.add(src, tgt, pred, ref=f"{ref}:{pred}:settled", source="corrected", strength=1.0, confidence=1.0,
                          polarity=-1 if int(settled.get("d", 0)) else 1)
                continue
            denied = max(0, min(n, int(p.get("denied", 0) or 0)))
            held = n - denied
            if held:
                store.add(src, tgt, pred, ref=f"{ref}:{pred}:held", source=base, strength=1.0, confidence=1.0, polarity=1, weight=held)
            if denied:
                store.add(src, tgt, pred, ref=f"{ref}:{pred}:denied", source=base, strength=1.0, confidence=1.0, polarity=-1, weight=denied)
    return store


def apply_to_crystals(store: AssociationStore, concept_index: Mapping[str, str], crystals: Mapping[str, Any],
                      max_per_crystal: int = 16, dry_run: bool = True) -> Dict[str, Any]:
    """Add to `crystal.connections` (crystal_id -> counted strength) from the store, strongest first, at most `max_per_crystal` new ones each.
    Only concepts that already have a crystal gain connections; no crystal is created.  `dry_run` (the default) changes nothing and
    reports what would change.  Counted strength only: uncounted evidence never reaches a crystal."""
    touched = 0
    links = 0
    for concept, cid in concept_index.items():
        crystal = crystals.get(cid)
        if crystal is None:
            continue
        conns = store.connections_for(concept)
        ranked: List[Tuple[str, float]] = []
        for other, s in sorted(conns.items(), key=lambda kv: -kv[1]):
            ocid = concept_index.get(other)
            if ocid and ocid in crystals and ocid != cid:
                ranked.append((ocid, s))
            if len(ranked) >= max_per_crystal:
                break
        if not ranked:
            continue
        touched += 1
        links += len(ranked)
        if not dry_run:
            merged = dict(getattr(crystal, "connections", None) or {})       # existing connections are kept; the stronger value wins
            for ocid, st in ranked:
                merged[ocid] = max(float(merged.get(ocid, 0.0)), round(st, 6))
            crystal.connections = merged
    return {"crystals_with_connections": touched, "links": links, "dry_run": bool(dry_run)}

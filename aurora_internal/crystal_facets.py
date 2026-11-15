# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Build plan: placing what she records, takes in and puts out into the facets of the crystal it belongs to.  Isolated: plain records in, a `FacetBook` out.

A fact is held ONCE per concept, under a key; every further time it turns up adds a context (evidence) to that one entry instead of another copy, so
"sunni" carries each definition, comparison, identification and episode once, with every occasion attached.  Each piece of evidence keeps its source
and how it came to be held (told, observed, recurrence, looked_up, seeded, unknown...).  Only counted bases give an entry any degree; the rest are kept
and show how much is not yet earned.  An entry's degree is a gradient: how strongly it is held, brought down in proportion by evidence against it.

Facet kinds are the spec's plus four adjustments from the category mapping (A2, A3, A5 and comparison): `expression`, `episode_ref`, `open`, `comparison`.
Substrate, frame and instrument stores are not knowledge and are routed outside (`classify_store`).  Dream-derived and overheard evidence is kept, uncounted.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from typing import Any, Dict, Iterable, List, Mapping, Optional

from aurora_internal.crystal_associations import COUNTED_BASES, AssociationStore, basis_of

VERSION = 1

SPEC_KINDS = ("definition", "example", "relation", "evidence", "abstract", "context", "operation", "cause", "effect", "condition", "analogy",
              "counterexample", "generalization", "particular", "temporal", "spatial", "agent", "patient", "hypothesis", "contradiction",
              "abduction", "plan", "value", "uncertainty", "intent", "lexicon", "emotion")
ADJUSTMENT_KINDS = ("expression", "episode_ref", "open", "comparison")
FACET_KINDS = SPEC_KINDS + ADJUSTMENT_KINDS

# What each association type means at each end: (kind at a, kind at b).  Anything not listed is something said between two things: a relation at both ends.
TYPE_KINDS = {
    "is_a": ("generalization", "particular"),       # a is a b: a belongs to the whole b; b holds a as a particular
    "causes": ("effect", "cause"),                  # a causes b: a has b as an effect; b has a as a cause
    "implies": ("effect", "condition"),
    "enables": ("effect", "condition"),
    "context_of": ("relation", "context"),          # a is the context of b: b carries a as its context
    "related_to": ("relation", "relation"),
    "opposite_of": ("comparison", "comparison"),
    "contrasts": ("comparison", "comparison"),
}

# Sources of definitions that were placed rather than learned.
DEFINITION_BASIS = {"initial": "seeded", "foundational": "seeded"}

# Stores that are not knowledge (category mapping A1, A8, A9): matched by name prefix.
OUTSIDE_STORES = {
    "substrate": ("daemon_", "heartbeat", "lock", "checkpoint", "backup", "runtime_faults", "persistence_audit", "system_introspection"),
    "frame": ("evo_625_pressure_map", "pressure_ontology"),
    "instrument": ("probe_battery", "growth_test", "threshold_test", "live_", "corpus", "corpora"),
}


def classify_store(name: str) -> Optional[str]:
    """'substrate', 'frame' or 'instrument' for a store that stays outside the crystals; None for one whose records belong in them."""
    n = str(name or "").lower()
    for cls, prefixes in OUTSIDE_STORES.items():
        if any(n.startswith(p) for p in prefixes):
            return cls
    return None


def content_key(*parts: Any) -> str:
    """A short stable key for a piece of content, so the same thing met again lands on the same entry."""
    text = "|".join(" ".join(str(p).lower().split()) for p in parts)
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


class FacetBook:
    """concept -> kind -> key -> {content, evidence{ref: {...}}}.  Content once; contexts attached."""

    def __init__(self) -> None:
        self._e: Dict[str, Dict[str, Dict[str, Dict[str, Any]]]] = {}

    # -- writing ----------------------------------------------------------------------------------------------------------------------------
    def add(self, concept: str, kind: str, key: str, content: Any, *, ref: str, source: str = "", basis: Optional[str] = None,
            strength: float = 1.0, confidence: float = 1.0, polarity: int = 1, weight: float = 1.0, occurrence_class: str = "",
            context: Any = None, consequence: Any = None, ancestry: Iterable[str] = ()) -> bool:
        """Attach one occasion to the entry (kind, key) of a concept.  The same ref again replaces itself.  False if the kind or concept is unusable."""
        concept = str(concept or "").strip()
        if not concept or kind not in FACET_KINDS or not ref:
            return False
        entry = self._e.setdefault(concept, {}).setdefault(kind, {}).setdefault(str(key), {"content": content, "evidence": {}})
        entry["evidence"][str(ref)] = {
            "source": str(source or ""), "basis": basis if basis else basis_of(source),
            "strength": _clamp(strength), "confidence": _clamp(confidence), "polarity": -1 if int(polarity) < 0 else 1,
            "weight": max(0.0, float(weight)), "occurrence_class": str(occurrence_class or ""), "context": context,
            "consequence": consequence, "ancestry": [str(a) for a in ancestry],
        }
        return True

    # -- reading ---------------------------------------------------------------------------------------------------------------------------
    def degree(self, concept: str, kind: str, key: str) -> float:
        """How strongly held: (1 - prod(1 - w)) over counted evidence for it, times (1 - the same for counted evidence against it).  Each occasion's
        w is its strength x confidence, taken as many times as it stood for.  0.0 when nothing counted."""
        entry = self._e.get(str(concept), {}).get(kind, {}).get(str(key))
        if not entry:
            return 0.0
        miss_for = miss_against = 1.0
        for e in entry["evidence"].values():
            if e["basis"] not in COUNTED_BASES:
                continue
            w = 1.0 - (1.0 - e["strength"] * e["confidence"]) ** e["weight"]
            if e["polarity"] > 0:
                miss_for *= 1.0 - w
            else:
                miss_against *= 1.0 - w
        return (1.0 - miss_for) * miss_against

    def facets_for(self, concept: str, top: Optional[int] = None, include_uncounted: bool = False) -> Dict[str, List[Dict[str, Any]]]:
        """kind -> entries, strongest first.  `top` only limits how many are returned per kind."""
        out: Dict[str, List[Dict[str, Any]]] = {}
        for kind, entries in self._e.get(str(concept), {}).items():
            rows = []
            for key, entry in entries.items():
                d = self.degree(concept, kind, key)
                if d > 0.0 or include_uncounted:
                    ev = entry["evidence"]
                    rows.append({"key": key, "content": entry["content"], "degree": d, "contexts": len(ev),
                                 "uncounted": sum(1 for e in ev.values() if e["basis"] not in COUNTED_BASES)})
            rows.sort(key=lambda r: (-r["degree"], r["key"]))
            if rows:
                out[kind] = rows[:top] if top else rows
        return out

    def concepts(self) -> List[str]:
        return sorted(self._e)

    def totals(self) -> Dict[str, int]:
        ent = ev = 0
        for kinds in self._e.values():
            for entries in kinds.values():
                ent += len(entries)
                ev += sum(len(e["evidence"]) for e in entries.values())
        return {"concepts": len(self._e), "entries": ent, "occasions": ev}

    # -- persistence ----------------------------------------------------------------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {"version": VERSION, "book": self._e}

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "FacetBook":
        b = cls()
        b._e = {c: {k: {key: {"content": v["content"], "evidence": {r: dict(e) for r, e in v["evidence"].items()}} for key, v in ents.items()}
                    for k, ents in kinds.items()} for c, kinds in (d.get("book") or {}).items()}
        return b

    def save(self, path: str) -> None:
        d = os.path.dirname(os.path.abspath(path))
        fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(self.to_dict(), fh, sort_keys=True)
            os.replace(tmp, path)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

    @classmethod
    def load(cls, path: str) -> "FacetBook":
        try:
            with open(path, encoding="utf-8") as fh:
                return cls.from_dict(json.load(fh))
        except (OSError, ValueError, KeyError):
            return cls()


# ---- placing what she records, takes in and puts out -----------------------------------------------------------------------------------------

def place_associations(book: FacetBook, store: AssociationStore) -> int:
    """Every typed association becomes entries at both ends by what the type means; every occasion that supports it comes with it.  An association that
    is argued over also places an `open` entry at both ends, as strong as it is contested, with the basis of its strongest counted evidence."""
    n = 0
    for a, b, t in store.records():
        ka, kb = TYPE_KINDS.get(t, ("relation", "relation"))
        ev = store.evidence(a, b, t)
        for concept, other, kind, direction in ((a, b, ka, "out"), (b, a, kb, "in")):
            key = f"{t}|{direction}|{other}"
            content = {"type": t, "other": other, "direction": direction}
            for ref, e in ev.items():
                n += bool(book.add(concept, kind, key, content, ref=ref, source=e.get("source", ""), basis=e.get("basis"), strength=e.get("strength", 1.0),
                                   confidence=e.get("confidence", 1.0), polarity=e.get("polarity", 1), weight=e.get("weight", 1.0)))
        c = store.contested(a, b, t)
        if c > 0.0:
            counted = [e for e in ev.values() if e["basis"] in COUNTED_BASES]
            basis = max(counted, key=lambda e: e["strength"] * e["confidence"] * e.get("weight", 1.0))["basis"]
            for concept, other in ((a, b), (b, a)):
                n += bool(book.add(concept, "open", f"contested|{t}|{other}", {"what": "contested", "type": t, "between": [a, b]},
                                   ref=f"contested:{a}|{b}|{t}", basis=basis, strength=c))
    return n


def place_oets_node(book: FacetBook, node: Mapping[str, Any]) -> int:
    """A concept node: its definitions, its recorded uses (her own use becomes an `expression`; a turn she met the word in becomes an `episode_ref`, one entry
    with every time attached; clarifications and embodiments are `example`s), its valence, and the category its part of speech put it in (that category came from a
    label, not from experience, so it is kept but not counted)."""
    word = str(node.get("word") or "")
    n = 0
    for d in node.get("definitions") or []:
        text = d.get("text") or ""
        if text:
            k = content_key(text)
            src = d.get("source") or ""
            n += bool(book.add(word, "definition", k, {"text": text}, ref=f"def:{word}:{k}", source=src, basis=DEFINITION_BASIS.get(src) or basis_of(src),
                               confidence=d.get("confidence", 0.0) or 0.0))
    for x in node.get("usage_examples") or []:
        text, ctx = x.get("text") or "", x.get("context") or ""
        if not text:
            continue
        k = content_key(text)
        ref = f"use:{word}:{k}:{x.get('timestamp', '')}"
        if ctx == "expression":              # her own use of the word, with how well it fit as the consequence
            n += bool(book.add(word, "expression", k, {"id": k, "summary": text[:160], "context": ctx}, ref=ref, source=x.get("source", ""),
                               context=ctx, consequence=x.get("fitness")))
        elif ctx in ("conversation", "interaction"):          # a turn she met the word in: held as a reference, once, with every time attached
            n += bool(book.add(word, "episode_ref", k, {"id": k, "time": x.get("timestamp"), "summary": text[:160]}, ref=ref, source=x.get("source", ""),
                               context=ctx))
        else:                                                    # clarification and axis embodiment are examples of the word's meaning
            n += bool(book.add(word, "example", k, {"text": text, "context": ctx}, ref=ref, source=x.get("source", ""), context=ctx))
    if node.get("emotional_valence"):
        n += bool(book.add(word, "emotion", "valence", {"valence": node["emotional_valence"]}, ref=f"valence:{word}", source=""))
    if node.get("role"):
        n += bool(book.add(word, "generalization", f"category|{node['role']}", {"category": node["role"]}, ref=f"role:{word}",
                           source="backfill_role_heuristic"))
    return n


def place_episode(book: FacetBook, concepts: Iterable[str], *, episode_id: str, time: float, summary: str, source: str = "", occurrence_class: str = "") -> int:
    """A turn or event is held as a reference (id, time, short summary) at each concept it involved, never as a quoted copy."""
    n = 0
    for c in concepts:
        n += bool(book.add(c, "episode_ref", str(episode_id), {"id": str(episode_id), "time": time, "summary": str(summary)[:160]},
                           ref=f"episode:{episode_id}:{c}", source=source, occurrence_class=occurrence_class, context=str(episode_id)))
    return n


def place_expression(book: FacetBook, concept: str, *, expression_id: str, summary: str, context: Any, outcome: Any, source: str = "",
                     strength: float = 1.0) -> int:
    """Something she put out about a concept, with what it led to attached as the consequence."""
    return int(book.add(concept, "expression", str(expression_id), {"id": str(expression_id), "summary": str(summary)[:160], "context": context},
                        ref=f"expression:{expression_id}:{concept}", source=source, strength=strength, context=context, consequence=outcome))


def place_open_item(book: FacetBook, concept: str, *, item_id: str, status: str, settles: str, source: str = "") -> int:
    """An open question, contradiction or gap, with what would settle it."""
    return int(book.add(concept, "open", str(item_id), {"status": status, "settles": settles}, ref=f"open:{item_id}:{concept}", source=source))


def place_ability(book: FacetBook, concept: str, *, ability_id: str, ancestry: Iterable[str], source: str = "") -> int:
    """A skill, from the first level, with its genealogy ancestry attached."""
    return int(book.add(concept, "operation", str(ability_id), {"id": str(ability_id)}, ref=f"ability:{ability_id}:{concept}", source=source,
                        ancestry=ancestry))


def place_cycle(book: FacetBook, cycle: Mapping[str, Any], *, occurrence_class: str = "") -> Dict[str, Any]:
    """One waveform cycle: what the understanding became (its relation) at each end, the cycle as an episode reference, and what she said with its
    alignment as the consequence.  The wavelet machinery is never placed.  Also returns what the points need: the signed axis displacement, completeness
    and coherence.  A cycle with no developed relation places nothing.  Evidence carries the cycle's retrospective confidence."""
    cid = str(cycle.get("cycle_id") or "")
    eff = cycle.get("effective_interpretation") or {}
    gu = cycle.get("global_understanding") or {}
    sub, rel, obj = str(eff.get("subject") or ""), str(eff.get("relation") or ""), str(eff.get("obj") or "")
    info = {"placed": 0, "axis_delta": dict((cycle.get("interference") or {}).get("axis_delta") or {}),
            "completeness": gu.get("completeness"), "coherence": gu.get("coherence")}
    if not (cid and sub and rel):
        return info
    conf = _clamp(gu.get("retrospective_confidence", 0.0) or 0.0)
    src = "observed" if occurrence_class == "observed" else occurrence_class
    for concept, other, direction in ((sub, obj, "out"), (obj, sub, "in")):
        if concept:
            info["placed"] += bool(book.add(concept, "relation", f"{rel}|{direction}|{other}", {"type": rel, "other": other, "direction": direction},
                                            ref=f"cycle:{cid}", source=src, confidence=conf, occurrence_class=occurrence_class, context=cid))
    info["placed"] += place_episode(book, [c for c in (sub, obj) if c], episode_id=cid, time=cycle.get("created_at"), summary=f"{sub} {rel} {obj}".strip(),
                                    source=src, occurrence_class=occurrence_class)
    resp = cycle.get("response_wave") or {}
    if resp.get("text_hash") and sub:
        score = (resp.get("relation_alignment") or {}).get("score", 0.0) or 0.0
        info["placed"] += place_expression(book, sub, expression_id=str(resp["text_hash"]), summary=str(resp.get("text") or ""), context=cid, outcome=score,
                                           source=src, strength=conf)
    return info


# ---- the one writer to live crystals -----------------------------------------------------------------------------------------------------------

def apply_to_crystals(book: FacetBook, concept_index: Mapping[str, str], crystals: Mapping[str, Any], per_kind: int = 8, dry_run: bool = True) -> Dict[str, Any]:
    """Write each concept's counted entries into its existing crystal as one facet per kind (role `fk:<kind>`), strongest per_kind each.  Only counted
    entries are written; a facet that exists is merged into (the stronger confidence wins), never replaced; no crystal is created.  `dry_run`
    (default) changes nothing and reports what would change."""
    touched = facets = entries = 0
    for concept, cid in concept_index.items():
        crystal = crystals.get(cid)
        if crystal is None:
            continue
        kinds = book.facets_for(concept, top=per_kind)
        if not kinds:
            continue
        touched += 1
        for kind, rows in kinds.items():
            facets += 1
            entries += len(rows)
            if dry_run:
                continue
            role = f"fk:{kind}"
            content = {"entries": [{"key": r["key"], "content": r["content"], "degree": round(r["degree"], 6), "contexts": r["contexts"]} for r in rows]}
            conf = max(r["degree"] for r in rows)
            existing = next((f for f in crystal.facets.values() if f.role == role), None)
            if existing is None:
                crystal.add_facet(role, content, confidence=conf)
            else:
                merged = {r["key"]: r for r in (existing.content or {}).get("entries", [])}
                for r in content["entries"]:
                    old = merged.get(r["key"])
                    if old is None or r["degree"] >= old.get("degree", 0.0):
                        merged[r["key"]] = r
                existing.content = {"entries": sorted(merged.values(), key=lambda r: (-r["degree"], r["key"]))}
                existing.confidence = max(float(existing.confidence), conf)
    return {"crystals_touched": touched, "facets": facets, "entries": entries, "dry_run": bool(dry_run)}

# Authors: Sunni (Sir) Morningstar & Cael Devo
"""How evidence is qualified: the part of a developmental record that moving work out of the live turn must never drop.

The environmental genealogy (the directive "Environmental Genealogy, Deferred Developmental Attribution, and
QuasiArch Diagnostic Access") will reconstruct, attribute and consolidate evidence away from the turn that produced
it.  A reconstruction that keeps WHAT was learned but loses HOW the evidence stands has changed what she knows:
an example would become a belief, an inference would become an observation, a contradiction would be resolved
without anyone resolving it, a correction would be indistinguishable from the thing it corrected.

This module is the contract.  It is pure (no I/O, no genealogy, no web), it is the vocabulary a durable event must
carry, and it states -- as functions tested in tests/test_evidence_qualification.py -- what any deferral, replay or
merge must preserve.  Nothing in the live path calls it yet; Stage 3 (durable developmental evidence) will build the
event log on it, and its tests are the acceptance check for that log.

BASES (how a piece of evidence came to be)
    told         said to her by someone (testimony).  Counts toward held / denied.
    observed     she did it or saw it herself.  Counts.
    corrected    a correction of what was held.  Counts, and the LATEST one settles the verdict; what it corrected
                 stays in the history.
    supposed     hypothetical: an example, a story, a dream, a counterfactual, a proposed pair that has not acted
                 together.  Kept, recallable AS hypothetical, and never counted.
    inferred     derived from other evidence (it names which: `derived_from`).  Kept, and NEVER counted: an
                 inference cannot raise confidence in its own premises, or a chain of reconstructions would
                 manufacture evidence out of itself (the directive's "no self-rewarding loops").
    unknown      the producer did not say.  Kept, never counted, never upgraded: a record without a basis is not
                 treated as `told` (the propositional store defaults a missing basis to told; a durable log must
                 not, because that is an upgrade nobody decided).

VERDICT (how the evidence stands, from the counted events only)
    held / denied / contested (told-or-observed both ways about equally) / settled by the latest correction /
    supposed (only examples) / inferred (only inferences) / unsaid.

CONTRADICTED and CORRECTED are flags, not verdicts: a correction settles the verdict and the contradiction it
settled stays visible.  Rules that make deferral safe: a fold is deterministic (order of arrival does not matter),
idempotent (the same event twice is one event: replay is not new experience), and loses nothing (merge is a union by
event id; the same id with different content is a conflict that is raised, never resolved by dropping one).
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

TOLD, OBSERVED, CORRECTED, SUPPOSED, INFERRED, UNKNOWN = (
    "told", "observed", "corrected", "supposed", "inferred", "unknown")
BASES = (TOLD, OBSERVED, CORRECTED, SUPPOSED, INFERRED, UNKNOWN)
COUNTED = (TOLD, OBSERVED, CORRECTED)

# Proposed, not yet consumed: the genealogy's own qualifier is the EnvironmentVector.stream_type of a trace item
# ("user_input", "knowledge_feed", "simulation", "corpus", "dream", ""; constraint_genealogy.py).  A stream it does
# not recognise is UNKNOWN -- never upgraded.  Whether "user_input" is observed (she ran it) and whether
# "simulation" is hypothetical (lived, but not in the world) are decisions for Sunni; the point of the table is
# that the decision is made once, here, and a durable event carries the result.
STREAM_BASIS: Dict[str, str] = {
    "user_input": OBSERVED, "knowledge_feed": TOLD, "corpus": TOLD, "simulation": SUPPOSED, "dream": SUPPOSED,
}


class EvidenceConflict(ValueError):
    """Two events with the same id say different things.  Neither is dropped; the caller must decide."""


def basis_of_stream(stream_type: str) -> str:
    return STREAM_BASIS.get(str(stream_type or ""), UNKNOWN)


def _clean_basis(basis: Any) -> str:
    b = str(basis or "").strip().lower()
    return b if b in BASES else UNKNOWN


def make_event(subject: str, basis: str, *, negated: bool = False, by: str = "", t: int = 0,
               derived_from: Sequence[str] = (), nonce: str = "", event_id: Optional[str] = None) -> Dict[str, Any]:
    """One piece of evidence about `subject`.  Its id is a hash of what it says, so the same utterance replayed is
    the same event; `nonce` distinguishes two real, identical utterances.  `inferred` must say what it was derived from."""
    basis = _clean_basis(basis)
    ev: Dict[str, Any] = {"subject": str(subject), "basis": basis, "negated": bool(negated), "by": str(by),
                          "t": int(t), "derived_from": sorted(str(x) for x in derived_from)}
    if nonce:
        ev["nonce"] = str(nonce)
    ev["id"] = str(event_id) if event_id else hashlib.blake2b(
        json.dumps(ev, sort_keys=True).encode("utf-8"), digest_size=10).hexdigest()
    return validate(ev)


def validate(ev: Mapping[str, Any]) -> Dict[str, Any]:
    out = dict(ev)
    for key in ("id", "subject", "basis", "t"):
        if key not in out:
            raise ValueError(f"evidence event lacks {key!r}")
    out["basis"] = _clean_basis(out["basis"])
    out["negated"] = bool(out.get("negated", False))
    out["derived_from"] = sorted(str(x) for x in (out.get("derived_from") or ()))
    out["t"] = int(out["t"])
    if out["basis"] == INFERRED and not out["derived_from"]:
        raise ValueError("an inference must say what it was derived from")
    return out


def merge(*streams: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """The union of event streams by id, ordered by (t, id).  The same event again is one event (replay is not new
    experience); the same id with different content raises `EvidenceConflict` -- nothing is dropped to make it go
    away.  Commutative, associative, idempotent."""
    by_id: Dict[str, Dict[str, Any]] = {}
    for stream in streams:
        for raw in stream:
            ev = validate(raw)
            held = by_id.get(ev["id"])
            if held is None:
                by_id[ev["id"]] = ev
            elif held != ev:
                raise EvidenceConflict(f"event {ev['id']} is recorded two different ways")
    return sorted(by_id.values(), key=lambda e: (e["t"], e["id"]))


def fold(events: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    """The record a set of events about ONE subject comes to.  Deterministic; derived from the events only."""
    evs = merge(events)
    subjects = {e["subject"] for e in evs}
    if len(subjects) > 1:
        raise ValueError(f"one record folds one subject, got {sorted(subjects)}")
    rec: Dict[str, Any] = {"subject": next(iter(subjects), ""), "n": 0, "denied": 0, "supposed": 0,
                           "supposed_denied": 0, "inferred": 0, "unknown": 0, "basis": {}, "settled": {},
                           "history": evs}
    for e in evs:
        rec["basis"][e["basis"]] = rec["basis"].get(e["basis"], 0) + 1
        if e["basis"] in COUNTED:
            rec["n"] += 1
            rec["denied"] += int(e["negated"])
            if e["basis"] == CORRECTED:                 # the latest correction decides; the rest of the history stays
                rec["settled"] = {"d": int(e["negated"]), "t": e["t"], "by": e["by"]}
        elif e["basis"] == SUPPOSED:
            rec["supposed"] += 1
            rec["supposed_denied"] += int(e["negated"])
        elif e["basis"] == INFERRED:
            rec["inferred"] += 1
        else:
            rec["unknown"] += 1
    return rec


def verdict(rec: Mapping[str, Any]) -> str:
    n, d = int(rec.get("n", 0) or 0), int(rec.get("denied", 0) or 0)
    if n <= 0:
        if int(rec.get("supposed", 0) or 0) > 0:
            return "supposed"
        if int(rec.get("inferred", 0) or 0) > 0:
            return "inferred"
        return "unsaid"
    settled = dict(rec.get("settled") or {})
    if settled:
        return "denied" if settled.get("d") else "held"
    return "held" if d * 2 < n else ("denied" if d * 2 > n else "contested")


def qualification(rec: Mapping[str, Any]) -> Dict[str, Any]:
    """How the evidence stands AND how it got there: the part a reconstruction must carry."""
    n, d = int(rec.get("n", 0) or 0), int(rec.get("denied", 0) or 0)
    counted = [e for e in (rec.get("history") or []) if e.get("basis") in COUNTED]
    both_ways = 0 < d < n
    settled = dict(rec.get("settled") or {})
    overruled = bool(settled) and any(bool(e["negated"]) != bool(settled["d"]) for e in counted if e["basis"] != CORRECTED)
    return {
        "verdict": verdict(rec),
        "basis": dict(rec.get("basis") or {}),
        "latest_basis": (counted[-1]["basis"] if counted else ""),
        "contradicted": both_ways or overruled,
        "corrected": bool(settled),
        "hypothetical_only": n == 0 and int(rec.get("supposed", 0) or 0) > 0,
        "inferred_only": n == 0 and int(rec.get("supposed", 0) or 0) == 0 and int(rec.get("inferred", 0) or 0) > 0,
    }


def qualification_of_predicate(p: Mapping[str, Any]) -> Dict[str, Any]:
    """The same view over a predicate record of the propositional store (`relation.assertion["predicates"][name]`),
    so what is stored today can be compared with, and migrated to, the event log without being rewritten.  A
    predicate keeps counts and a bounded history, not every event: the flags are computed from what it keeps."""
    hist = [dict(h) for h in (p.get("history") or [])]
    counted = [h for h in hist if h.get("b") in COUNTED]
    n, d = int(p.get("n", 0) or 0), int(p.get("denied", 0) or 0)
    settled = dict(p.get("settled") or {})
    overruled = bool(settled) and any(bool(h.get("d")) != bool(settled.get("d")) for h in counted if h.get("b") != CORRECTED)
    rec = {"n": n, "denied": d, "supposed": int(p.get("supposed", 0) or 0), "settled": settled, "inferred": 0}
    q = {"verdict": verdict(rec), "basis": dict(p.get("basis") or {}),
         "latest_basis": (counted[-1].get("b", "") if counted else ""),
         "contradicted": (0 < d < n) or overruled, "corrected": bool(settled),
         "hypothetical_only": n == 0 and rec["supposed"] > 0,
         "inferred_only": False}
    return q


def violations(before: Iterable[Mapping[str, Any]], after: Iterable[Mapping[str, Any]]) -> List[str]:
    """What a deferral / replay / consolidation that took `before` and produced `after` lost or changed.  Empty is
    clean.  `after` may hold MORE (later evidence); it may not hold less, or hold the same event differently."""
    b = {e["id"]: validate(e) for e in before}
    a = {e["id"]: validate(e) for e in after}
    out: List[str] = []
    for eid, ev in b.items():
        if eid not in a:
            out.append(f"dropped {ev['basis']} event {eid}")
        elif a[eid] != ev:
            if a[eid]["basis"] != ev["basis"]:
                out.append(f"event {eid} was {ev['basis']} and is now {a[eid]['basis']}")
            else:
                out.append(f"event {eid} was rewritten")
    return out

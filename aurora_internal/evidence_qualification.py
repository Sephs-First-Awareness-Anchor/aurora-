# Authors: Sunni (Sir) Morningstar & Cael Devo
"""How evidence is qualified: what a durable developmental record must keep apart so that moving work out of the
live turn never changes what she knows.

(FIX-A144, revised by the directive "Developmental Evidence, Simulated Experience, and Consequence-Grounded
Promotion".)  This module is pure -- no I/O, no genealogy, no web.  It is the vocabulary and the rules an evidence
log, a deferral, a replay and a synchronisation must keep, stated as functions that tests/test_evidence_qualification.py
holds to.  The propositional store (aurora_propositional_understanding) already records basis/verdict/standing; this
extends the same record, it is not a second system.

ONE EVENT, SEVEN QUESTIONS (they are kept apart; none stands in for another)
  occurrence   Where it originated, and what kind of happening it was: heard, read, perceived, acted, tested,
               derived, imagined, simulated, dreamed, recalled.  An event that exists DID occur in her system.
               A dream is a real dream; an imagining is a real imagining.
  basis        How its CONTENT is supported: observed, told, corrected, supposed, inferred, unknown.
               Hearing a claim is an occurrence; the claim is testimony (told) unless independently supported.
  ancestry     The earlier events (experiences, representations) it developed from, and whether that is
               traced, partial or unattributed.  Never manufactured: unknown ancestry stays unknown.
  context      The world it applies to (external / simulated / dreamed / imagined / internal) and a domain.
  attribution  (inside consequence) which events/mechanisms contributed to the outcome, and whether that
               attribution is complete.  Incomplete is the honest default.
  consequence  What actually changed (target + change).  A genuine internal consequence is a genuine event even
               when its represented circumstances are hypothetical.
  scope        Where a capability has demonstrated effectiveness -- computed by `demonstration`, never asserted.

WHAT COUNTS toward how a statement stands: told, observed, corrected -- unless the occurrence is a recollection
(a recollection never adds evidence; the original did).  supposed, inferred and unknown are kept and never
counted: an inference cannot raise confidence in its own premises; unknown is never upgraded to told.  `carried`
(legacy) evidence is the one exception to "unknown never counts": it was real before provenance was recorded, so
it keeps its standing (nothing she developed is disabled by migration) while being labelled unattributed, and
genuine evidence that arrives later clarifies it.

WHAT CAN NEVER HAPPEN: an imagined, simulated or dreamed occurrence carrying told/observed/corrected content, or
the context "external" (a dream is not evidence that the event occurred; a simulation does not certify external
effectiveness).  Those are rejected at ingestion, and `violations` reports them if they appear later.

DEFERRAL SAFETY: a fold is deterministic and order independent; the same event twice is one event (replay is not new
experience); the same id with different content is a conflict raised, never resolved by dropping one; `violations`
names every dropped event, rewritten event, laundered basis and conflicting duplicate id.  And a re-run that
reproduces the same consequence is not new independent evidence (`demonstration` counts distinct consequences).
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set

TOLD, OBSERVED, CORRECTED, SUPPOSED, INFERRED, UNKNOWN = (
    "told", "observed", "corrected", "supposed", "inferred", "unknown")
BASES = (TOLD, OBSERVED, CORRECTED, SUPPOSED, INFERRED, UNKNOWN)
COUNTED = (TOLD, OBSERVED, CORRECTED)

# Which bases an occurrence may carry, and the basis its content takes when the producer says nothing more.
# (Directive VI: "Aurora imagines an object -> actual imagination; hypothetical object", "dreams of an event ->
# actual dream; represented event not independently external", "derives a conclusion -> inferred", and so on.)
OCCURRENCES: Dict[str, Set[str]] = {
    "heard": {TOLD, CORRECTED, SUPPOSED, UNKNOWN},
    "read": {TOLD, CORRECTED, SUPPOSED, UNKNOWN},
    "perceived": {OBSERVED, UNKNOWN},
    "acted": {OBSERVED, UNKNOWN},
    "tested": {OBSERVED, UNKNOWN},
    "derived": {INFERRED},
    "imagined": {SUPPOSED},
    "simulated": {SUPPOSED},
    "dreamed": {SUPPOSED},
    "recalled": set(BASES),
}
DEFAULT_BASIS: Dict[str, str] = {
    "heard": TOLD, "read": TOLD, "perceived": OBSERVED, "acted": OBSERVED, "tested": OBSERVED,
    "derived": INFERRED, "imagined": SUPPOSED, "simulated": SUPPOSED, "dreamed": SUPPOSED}
LIVED = frozenset({"heard", "read", "perceived", "acted", "tested"})        # happened to her in the world
HYPOTHETICAL = frozenset({"imagined", "simulated", "dreamed"})              # real events; imagined worlds
NON_EVIDENCE = frozenset({"recalled"})                                       # a recollection adds no evidence
WORLDS = ("external", "internal", "simulated", "dreamed", "imagined")
ANCESTRY_STATUS = ("traced", "partial", "unattributed")

# The stream a trace item came through says where it ORIGINATED (occurrence), never how its contents are
# supported: a user_input stream is heard -- what was said is testimony, supposition or correction by its content.
# Vocabularies seen in the code (measured by scripts/measure_stream_provenance.py and read in the source):
#   gateway StreamType values: user_input, knowledge_feed, sensor_data, system_event, exploration, self_reflection;
#   the genealogy's documented extras: simulation, corpus, dream;  the lineage compiler writes "synthetic_lineage".
# Only origins that name an occurrence unambiguously are mapped; the rest stay "" (unspecified), which is visible and
# never guessed.  `internal_origin` (gateway metadata) outranks the stream: dream replay arrives as knowledge_feed.
OCCURRENCE_OF_STREAM: Dict[str, str] = {
    "user_input": "heard", "knowledge_feed": "read", "corpus": "read", "sensor_data": "perceived",
    "simulation": "simulated", "dream": "dreamed", "synthetic_lineage": "derived"}
OCCURRENCE_OF_INTERNAL_ORIGIN: Dict[str, str] = {"dream_replay": "dreamed"}


class EvidenceConflict(ValueError):
    """Two events with the same id say different things.  Neither is dropped; the caller must decide."""


def occurrence_of_stream(stream_type: str, internal_origin: str = "") -> str:
    """`EnvironmentVector.stream_type` (+ the gateway's `internal_origin`) -> occurrence.  An unrecognised or empty
    stream is "" (unspecified): the producer did not say, and that stays visible; it is not guessed."""
    origin = OCCURRENCE_OF_INTERNAL_ORIGIN.get(str(internal_origin or ""))
    return origin or OCCURRENCE_OF_STREAM.get(str(stream_type or ""), "")


def _clean_basis(basis: Any) -> str:
    b = str(basis or "").strip().lower()
    return b if b in BASES else UNKNOWN


def _ids(xs: Iterable[Any]) -> List[str]:
    return sorted({str(x) for x in (xs or ())})


def _clean_context(ctx: Any) -> Dict[str, str]:
    if not ctx:
        return {}
    ctx = dict(ctx)
    world = str(ctx.get("world", "") or "").strip().lower()
    if world and world not in WORLDS:
        raise ValueError(f"unknown world {world!r}; one of {WORLDS}")
    out = {"world": world, "domain": str(ctx.get("domain", "") or "").strip().lower()}
    return {k: v for k, v in out.items() if v}


def _clean_consequence(c: Any) -> Dict[str, Any]:
    if not c:
        return {}
    c = dict(c)
    target, change = str(c.get("target", "") or "").strip(), str(c.get("change", "") or "").strip()
    if not target or not change:
        raise ValueError("a consequence names what changed (target) and how (change)")
    return {"target": target, "change": change, "attribution": _ids(c.get("attribution")),
            "attribution_complete": bool(c.get("attribution_complete", False))}


def make_event(subject: str, basis: Optional[str] = None, *, negated: bool = False, by: str = "", t: int = 0,
               derived_from: Sequence[str] = (), nonce: str = "", event_id: Optional[str] = None,
               occurrence: str = "", context: Optional[Mapping[str, Any]] = None, ancestry: Sequence[str] = (),
               ancestry_status: str = "", consequence: Optional[Mapping[str, Any]] = None,
               carried: bool = False) -> Dict[str, Any]:
    """One piece of evidence about `subject`.  The id is a hash of what it says, so the same utterance replayed is
    the same event and a genuinely separate occurrence (a different time, or a `nonce`) is a different one.  Fields
    left at their defaults are not part of the hash, so an event written before a field existed keeps its id.
    `basis=None` takes the occurrence's natural basis (a dream is supposed, a perception observed); with neither it
    is `unknown`, never `told`."""
    occ = str(occurrence or "").strip().lower()
    if basis is None:
        basis = DEFAULT_BASIS.get(occ, UNKNOWN)
    ev: Dict[str, Any] = {"subject": str(subject), "basis": _clean_basis(basis), "negated": bool(negated),
                          "by": str(by), "t": int(t), "derived_from": _ids(derived_from)}
    if nonce:
        ev["nonce"] = str(nonce)
    if occ:
        ev["occurrence"] = occ
    ctx = _clean_context(context)
    if ctx:
        ev["context"] = ctx
    anc = _ids(ancestry)
    if anc:
        ev["ancestry"] = anc
    if ancestry_status:
        ev["ancestry_status"] = str(ancestry_status)
    cons = _clean_consequence(consequence)
    if cons:
        ev["consequence"] = cons
    if carried:
        ev["carried"] = True
    ev["id"] = str(event_id) if event_id else hashlib.blake2b(
        json.dumps(ev, sort_keys=True).encode("utf-8"), digest_size=10).hexdigest()
    return validate(ev)


def validate(ev: Mapping[str, Any]) -> Dict[str, Any]:
    """Normalise an event and refuse the combinations that would launder hypothetical content into evidence."""
    out = dict(ev)
    for key in ("id", "subject", "basis", "t"):
        if key not in out:
            raise ValueError(f"evidence event lacks {key!r}")
    out["basis"] = _clean_basis(out["basis"])
    out["negated"] = bool(out.get("negated", False))
    out["derived_from"] = _ids(out.get("derived_from"))
    out["t"] = int(out["t"])
    occ = str(out.get("occurrence", "") or "").strip().lower()
    if occ:
        if occ not in OCCURRENCES:
            raise ValueError(f"unknown occurrence {occ!r}; one of {sorted(OCCURRENCES)}")
        if out["basis"] not in OCCURRENCES[occ]:
            raise ValueError(f"a {occ} occurrence cannot carry {out['basis']} content "
                             f"(allowed: {sorted(OCCURRENCES[occ])})")
        out["occurrence"] = occ
    else:
        out.pop("occurrence", None)
    ctx = _clean_context(out.get("context"))
    if ctx.get("world") == "external" and occ in HYPOTHETICAL:
        raise ValueError(f"a {occ} occurrence cannot claim the external world as its context")
    if ctx:
        out["context"] = ctx
    else:
        out.pop("context", None)
    anc = _ids(out.get("ancestry"))
    if anc:
        out["ancestry"] = anc
    else:
        out.pop("ancestry", None)
    status = str(out.get("ancestry_status", "") or "")
    if status:
        if status not in ANCESTRY_STATUS:
            raise ValueError(f"unknown ancestry status {status!r}; one of {ANCESTRY_STATUS}")
        if status == "traced" and not anc:
            raise ValueError("ancestry cannot be 'traced' with nothing traced")
        out["ancestry_status"] = status
    else:
        out.pop("ancestry_status", None)
    cons = _clean_consequence(out.get("consequence"))
    if cons:
        out["consequence"] = cons
    else:
        out.pop("consequence", None)
    if out["basis"] == INFERRED and not out["derived_from"]:
        raise ValueError("an inference must say what it was derived from")
    if out.get("carried"):
        if out["basis"] != UNKNOWN or occ:
            raise ValueError("carried (legacy) evidence is unattributed: basis unknown, no occurrence")
        out["carried"] = True
    else:
        out.pop("carried", None)
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


def counts(ev: Mapping[str, Any]) -> bool:
    """Does this event add to how its subject stands?  Told/observed/corrected content does, unless the event is a
    recollection (the original carries the evidence)."""
    return ev["basis"] in COUNTED and ev.get("occurrence", "") not in NON_EVIDENCE


def fold(events: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    """The record a set of events about ONE subject comes to.  Deterministic; derived from the events only."""
    evs = merge(events)
    subjects = {e["subject"] for e in evs}
    if len(subjects) > 1:
        raise ValueError(f"one record folds one subject, got {sorted(subjects)}")
    rec: Dict[str, Any] = {"subject": next(iter(subjects), ""), "n": 0, "denied": 0, "carried": 0, "carried_denied": 0,
                           "supposed": 0, "supposed_denied": 0, "inferred": 0, "unknown": 0, "recalled": 0,
                           "basis": {}, "occurrence": {}, "settled": {}, "history": evs}
    for e in evs:
        rec["basis"][e["basis"]] = rec["basis"].get(e["basis"], 0) + 1
        if e.get("occurrence"):
            rec["occurrence"][e["occurrence"]] = rec["occurrence"].get(e["occurrence"], 0) + 1
        if e.get("occurrence") in NON_EVIDENCE:
            rec["recalled"] += 1
        elif e["basis"] in COUNTED:
            rec["n"] += 1
            rec["denied"] += int(e["negated"])
            if e["basis"] == CORRECTED:                 # the latest correction decides; the rest of the history stays
                rec["settled"] = {"d": int(e["negated"]), "t": e["t"], "by": e["by"]}
        elif e["basis"] == SUPPOSED:
            rec["supposed"] += 1
            rec["supposed_denied"] += int(e["negated"])
        elif e["basis"] == INFERRED:
            rec["inferred"] += 1
        elif e.get("carried"):
            rec["carried"] += 1
            rec["carried_denied"] += int(e["negated"])
        else:
            rec["unknown"] += 1
    return rec


def _standing_counts(rec: Mapping[str, Any]):
    n = int(rec.get("n", 0) or 0) + int(rec.get("carried", 0) or 0)
    d = int(rec.get("denied", 0) or 0) + int(rec.get("carried_denied", 0) or 0)
    return n, d


def _verdict_from(n: int, d: int, settled: Mapping[str, Any], supposed: int, inferred: int) -> str:
    if n <= 0:
        if supposed > 0:
            return "supposed"
        if inferred > 0:
            return "inferred"
        return "unsaid"
    if settled:
        return "denied" if settled.get("d") else "held"
    return "held" if d * 2 < n else ("denied" if d * 2 > n else "contested")


def verdict(rec: Mapping[str, Any]) -> str:
    """How the evidence stands.  Legacy `carried` evidence keeps the standing it had; nothing else unattributed does."""
    n, d = _standing_counts(rec)
    return _verdict_from(n, d, dict(rec.get("settled") or {}), int(rec.get("supposed", 0) or 0),
                         int(rec.get("inferred", 0) or 0))


def qualification(rec: Mapping[str, Any]) -> Dict[str, Any]:
    """How the evidence stands AND how it got there: the part a reconstruction must carry."""
    n, d = _standing_counts(rec)
    counted = [e for e in (rec.get("history") or []) if counts(e)]
    settled = dict(rec.get("settled") or {})
    overruled = bool(settled) and any(bool(e["negated"]) != bool(settled["d"]) for e in counted if e["basis"] != CORRECTED)
    supposed, inferred = int(rec.get("supposed", 0) or 0), int(rec.get("inferred", 0) or 0)
    attributed = int(rec.get("n", 0) or 0)
    return {
        "verdict": verdict(rec),
        "verdict_attributed": _verdict_from(attributed, int(rec.get("denied", 0) or 0), settled, supposed, inferred),
        "unattributed_standing": int(rec.get("carried", 0) or 0) > 0,
        "basis": dict(rec.get("basis") or {}),
        "occurrence": dict(rec.get("occurrence") or {}),
        "latest_basis": (counted[-1]["basis"] if counted else ""),
        "contradicted": (0 < d < n) or overruled,
        "corrected": bool(settled),
        "hypothetical_only": n == 0 and supposed > 0,
        "inferred_only": n == 0 and supposed == 0 and inferred > 0,
    }


def qualification_of_predicate(p: Mapping[str, Any]) -> Dict[str, Any]:
    """The same view over a predicate record of the propositional store (`relation.assertion["predicates"][name]`),
    so what is stored today can be compared with, and migrated to, the event log without being rewritten.  A
    predicate keeps counts and a bounded history, not every event.  `unattributed_n` is the part of its standing
    that predates provenance (n minus the counted bases recorded): carried, never erased, never called testimony."""
    hist = [dict(h) for h in (p.get("history") or [])]
    counted = [h for h in hist if h.get("b") in COUNTED]
    n, d = int(p.get("n", 0) or 0), int(p.get("denied", 0) or 0)
    settled = dict(p.get("settled") or {})
    basis = dict(p.get("basis") or {})
    supposed = int(p.get("supposed", 0) or 0)
    overruled = bool(settled) and any(bool(h.get("d")) != bool(settled.get("d")) for h in counted if h.get("b") != CORRECTED)
    attributed = sum(int(basis.get(b, 0) or 0) for b in COUNTED)
    unattributed = max(0, n - attributed)
    return {"verdict": _verdict_from(n, d, settled, supposed, 0),
            "basis": basis, "latest_basis": (counted[-1].get("b", "") if counted else ""),
            "contradicted": (0 < d < n) or overruled, "corrected": bool(settled),
            "hypothetical_only": n == 0 and supposed > 0, "inferred_only": False,
            "unattributed_n": unattributed, "unattributed_standing": unattributed > 0}


def violations(before: Iterable[Mapping[str, Any]], after: Iterable[Mapping[str, Any]]) -> List[str]:
    """What a deferral / replay / consolidation that took `before` and produced `after` lost or changed.  Empty is
    clean.  `after` may hold MORE (later evidence); it may not hold less, hold the same event differently, or hold
    one id two ways.  A stream that itself carries one id with conflicting content is reported, not collapsed:
    neither version may be silently retained over the other."""
    out: List[str] = []

    def index(stream: Iterable[Mapping[str, Any]], name: str) -> Dict[str, List[Dict[str, Any]]]:
        seen: Dict[str, List[Dict[str, Any]]] = {}
        for raw in stream:
            ev = validate(raw)
            versions = seen.setdefault(ev["id"], [])
            if ev not in versions:
                versions.append(ev)
        for eid, versions in seen.items():
            if len(versions) > 1:
                out.append(f"event {eid} appears {len(versions)} different ways in the {name} stream")
        return seen

    b, a = index(before, "before"), index(after, "after")
    for eid, versions in b.items():
        held = a.get(eid)
        for ev in versions:
            if held is None:
                out.append(f"dropped {ev['basis']} event {eid}")
            elif ev not in held:
                if all(h["basis"] != ev["basis"] for h in held):
                    out.append(f"event {eid} was {ev['basis']} and is now {held[0]['basis']}")
                else:
                    out.append(f"event {eid} was rewritten")
    return out


def grounding(events: Iterable[Mapping[str, Any]], event_id: str) -> Dict[str, Any]:
    """Where an event's ancestry reaches, without making any up.  `lived_roots` are the lived occurrences (heard,
    read, perceived, acted, tested) found by following ancestry and premises backwards; `dangling` are ancestors named
    but not in the log (kept visible, not dropped and not invented); `ungrounded` is true when none reaches a lived
    occurrence -- a finding, not an error: a dream element may have no supported ancestry, and then that is what is
    reported."""
    evs = {e["id"]: e for e in merge(events)}
    if event_id not in evs:
        raise KeyError(event_id)
    roots: Set[str] = set()
    dangling: Set[str] = set()
    seen: Set[str] = {event_id}
    stack = [event_id]
    cycle = False
    while stack:
        cur = stack.pop()
        for parent in list(evs[cur].get("ancestry") or ()) + list(evs[cur].get("derived_from") or ()):
            if parent == event_id:
                cycle = True
            if parent not in evs:
                dangling.add(parent)
                continue
            if parent in seen:
                continue
            seen.add(parent)
            if evs[parent].get("occurrence") in LIVED:
                roots.add(parent)
            stack.append(parent)
    ev = evs[event_id]
    return {"lived_roots": sorted(roots), "dangling": sorted(dangling), "ungrounded": not roots, "cycle": cycle,
            "status": ev.get("ancestry_status", "traced" if ev.get("ancestry") else "unattributed"),
            "reached": len(seen) - 1}


def consequence_signature(ev: Mapping[str, Any]) -> str:
    """What a consequence IS, independent of how many times or when it was produced: the target, the change, who
    contributed, the world and domain, whether it was an effect or its failure, and what kind of occurrence produced
    it (someone saying it works and a test showing it works are different evidence).  A replay, or a re-run that
    reproduces the same result, has the same signature and is the same piece of independent evidence."""
    c = dict(ev.get("consequence") or {})
    if not c:
        raise ValueError("event has no consequence")
    ctx = dict(ev.get("context") or {})
    blob = json.dumps([c["target"], c["change"], c["attribution"], ctx.get("world", ""), ctx.get("domain", ""),
                       bool(ev.get("negated")), ev.get("occurrence", ""), ev.get("basis", "")])
    return hashlib.blake2b(blob.encode("utf-8"), digest_size=8).hexdigest()


def demonstration(events: Iterable[Mapping[str, Any]], target: str) -> Dict[str, Any]:
    """Where a capability or relationship has demonstrated effect, from its consequences.  Participation (becoming
    active together) is not here: only consequences count.  Independent evidence is the number of DISTINCT
    consequences, so repetition adds occurrences and nothing else.  Internal demonstration (any world) never
    becomes external: that needs a lived test or action in the external world.  A failed external test is kept and
    revises applicability; it does not erase the internal history."""
    evs = [e for e in merge(events) if (e.get("consequence") or {}).get("target") == target
           and e.get("occurrence", "") not in NON_EVIDENCE]          # a recollection demonstrates nothing new
    sigs: Dict[str, Dict[str, Any]] = {}
    for e in evs:
        sigs.setdefault(consequence_signature(e), e)
    by_world: Dict[str, int] = {}
    ext_ok = ext_bad = 0
    domains: Set[str] = set()
    open_attr = False
    internal = False
    for e in sigs.values():
        world = (e.get("context") or {}).get("world", "") or "unspecified"
        by_world[world] = by_world.get(world, 0) + 1
        if not (e.get("consequence") or {}).get("attribution_complete"):
            open_attr = True
        lived_external = (world == "external" and e.get("occurrence") in {"tested", "acted", "perceived"}
                          and e["basis"] == OBSERVED)
        if lived_external:
            if e["negated"]:
                ext_bad += 1
            else:
                ext_ok += 1
        elif not e["negated"] and world in {"internal", "simulated", "dreamed", "imagined"}:
            internal = True                    # demonstrated inside her; testimony that it works demonstrates nothing
        if not e["negated"] and (e.get("context") or {}).get("domain"):
            domains.add(e["context"]["domain"])
    if ext_ok and ext_bad:
        applicability = "external_mixed"
    elif ext_bad:
        applicability = "external_contradicted"
    elif ext_ok:
        applicability = "external_supported"
    elif internal:
        applicability = "internal_only"
    else:
        applicability = "none"
    return {"target": target, "occurrences": len(evs), "independent": len(sigs), "replays_ignored": len(evs) - len(sigs),
            "by_world": by_world, "internal_demonstrated": internal, "external_supported": ext_ok,
            "external_contradicted": ext_bad, "applicability": applicability, "domains": sorted(domains),
            "generalized": len(domains) >= 2, "attribution_open": open_attr}


# -- the live view: how finely a memory is held (directive: finer when it mattered) --------------------------------
#
# The full event log is the authority and is never shrunk.  What active cognition holds is a VIEW of it, derived on
# demand, whose fineness follows impact: an event that carries a consequence, is a correction, sits on the losing side
# of a contradiction, was overruled, is the first exposure, the latest, the latest counted, or is named as ancestry /
# premise / attribution by another event is held in full; ordinary repeats become counts.  Impact is read from the
# events themselves, never from a flag or from how emphatically something was said (emphasis is testimony about
# importance, not evidence).  Because impact appears later, the view is rebuilt from the log, so a memory that starts
# to matter regains its detail.  `view_qualification` reads ONLY the view and must equal the qualification of the
# whole log; `view_problems` says whether a view still matches its log.

def _referenced_ids(evs: Sequence[Mapping[str, Any]]) -> Set[str]:
    out: Set[str] = set()
    for e in evs:
        out.update(e.get("ancestry") or ())
        out.update(e.get("derived_from") or ())
        out.update((e.get("consequence") or {}).get("attribution") or ())
    return out


def impact(events: Iterable[Mapping[str, Any]], subject: str) -> Dict[str, List[str]]:
    """Why each event of `subject` matters, by id.  An event absent from the result is an ordinary repeat."""
    evs = merge(events)
    subj = [e for e in evs if e["subject"] == subject]
    referenced = _referenced_ids(evs)
    why: Dict[str, List[str]] = {}

    def add(e: Mapping[str, Any], reason: str) -> None:
        why.setdefault(e["id"], []).append(reason)

    if subj:
        add(subj[0], "first")
        add(subj[-1], "latest")
    counted = [e for e in subj if counts(e)]
    if counted:
        add(counted[-1], "latest_counted")
    n = len(counted)
    d = sum(int(e["negated"]) for e in counted)
    settled = {}
    for e in counted:
        if e["basis"] == CORRECTED:
            settled = {"d": int(e["negated"])}
    for e in subj:
        if e["basis"] == CORRECTED:
            add(e, "correction")
        if e.get("consequence"):
            add(e, "consequence")
        if e["id"] in referenced:
            add(e, "ancestor")
        if counts(e) and e["basis"] != CORRECTED:
            if settled and bool(e["negated"]) != bool(settled["d"]):
                add(e, "overruled")
            if 0 < d < n and (d * 2 == n or (bool(e["negated"]) == (d * 2 < n))):
                add(e, "contradiction")
    return why


def _key(e: Mapping[str, Any]) -> Dict[str, Any]:
    return {"basis": e["basis"], "occurrence": e.get("occurrence", ""), "negated": bool(e["negated"]),
            "carried": bool(e.get("carried"))}


def _rollup(evs: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    tally: Dict[str, Dict[str, Any]] = {}
    for e in evs:
        k = _key(e)
        tally.setdefault(json.dumps(k, sort_keys=True), dict(k, count=0))["count"] += 1
    return {"events": len(evs), "keys": [tally[k] for k in sorted(tally)],
            "span": [min(e["t"] for e in evs), max(e["t"] for e in evs)] if evs else []}


def live_view(events: Iterable[Mapping[str, Any]], subject: str, *, budget: int = 8) -> Dict[str, Any]:
    """What active cognition holds of `subject`: impactful events in full, the `budget` most recent ordinary ones in
    full, and everything else as counts.  The log is not touched."""
    evs = merge(events)
    subj = [e for e in evs if e["subject"] == subject]
    why = impact(evs, subject)
    ordinary = [e for e in subj if e["id"] not in why]
    recent = {e["id"] for e in ordinary[max(0, len(ordinary) - max(0, int(budget))):]}
    detailed = [e for e in subj if e["id"] in why or e["id"] in recent]
    rest = [e for e in subj if e["id"] not in why and e["id"] not in recent]
    reasons = {e["id"]: (why.get(e["id"]) or ["recent"]) for e in detailed}
    return {"subject": subject, "total": len(subj), "detailed": detailed, "reasons": reasons, "rollup": _rollup(rest)}


def view_qualification(view: Mapping[str, Any]) -> Dict[str, Any]:
    """The qualification, computed from the view alone.  Must equal `qualification(fold(all events of the subject))`."""
    rec: Dict[str, Any] = {"subject": view["subject"], "n": 0, "denied": 0, "carried": 0, "carried_denied": 0,
                           "supposed": 0, "supposed_denied": 0, "inferred": 0, "unknown": 0, "recalled": 0,
                           "basis": {}, "occurrence": {}, "settled": {}, "history": []}

    def absorb(k: Mapping[str, Any], c: int) -> None:
        rec["basis"][k["basis"]] = rec["basis"].get(k["basis"], 0) + c
        if k.get("occurrence"):
            rec["occurrence"][k["occurrence"]] = rec["occurrence"].get(k["occurrence"], 0) + c
        neg = int(bool(k["negated"])) * c
        if k.get("occurrence") in NON_EVIDENCE:
            rec["recalled"] += c
        elif k["basis"] in COUNTED:
            rec["n"] += c
            rec["denied"] += neg
        elif k["basis"] == SUPPOSED:
            rec["supposed"] += c
            rec["supposed_denied"] += neg
        elif k["basis"] == INFERRED:
            rec["inferred"] += c
        elif k.get("carried"):
            rec["carried"] += c
            rec["carried_denied"] += neg
        else:
            rec["unknown"] += c

    for k in view["rollup"]["keys"]:
        absorb(k, int(k["count"]))
    for e in view["detailed"]:
        absorb(_key(e), 1)
        rec["history"].append(e)
        if e["basis"] == CORRECTED and e.get("occurrence", "") not in NON_EVIDENCE:
            rec["settled"] = {"d": int(e["negated"]), "t": e["t"], "by": e["by"]}
    rec["history"].sort(key=lambda e: (e["t"], e["id"]))
    return qualification(rec)


def view_problems(view: Mapping[str, Any], events: Iterable[Mapping[str, Any]]) -> List[str]:
    """Whether a view still matches the log it came from: it may not invent or alter an event, and detail plus counts
    must account for every event of the subject exactly once."""
    evs = {e["id"]: e for e in merge(events)}
    subj = [e for e in evs.values() if e["subject"] == view["subject"]]
    out: List[str] = []
    for e in view["detailed"]:
        held = evs.get(e["id"])
        if held is None:
            out.append(f"view holds event {e['id']} that is not in the log")
        elif validate(e) != held:
            out.append(f"view holds event {e['id']} differently from the log")
    shown = {e["id"] for e in view["detailed"]}
    if len(shown) + int(view["rollup"]["events"]) != len(subj) or int(view["total"]) != len(subj):
        out.append("view does not account for every event of the subject exactly once")
    elif _rollup(sorted((e for e in subj if e["id"] not in shown), key=lambda e: (e["t"], e["id"]))) != view["rollup"]:
        out.append("view's counts do not match the events it summarises")
    return out


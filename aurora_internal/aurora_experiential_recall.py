# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
aurora_experiential_recall.py -- remembering what happened and what she held THEN, kept apart from what she holds NOW.

Directive V2, "Contextual Relational Understanding, Developmental Reinterpretation, and Experiential Recall"
(Sir, 2026-11-21).  This module is a VIEW over records that already exist.  It is not a store, not an organ and not
a speaker:

  * the authoritative record is the predicate record her propositional understanding already keeps on each relation
    of her web (`assertion.predicates[p]`): every occasion in `history` (when, who, said or denied, on what basis,
    under which condition, which utterance) and, from this directive on, what she held right after each occasion
    (`v`, and `vw` under its condition), written at the time and never rewritten;
  * `recollect_predicate` reads that record into two layers that are never merged:
        then   each remembered occasion as it was recorded: what was said, how it came to her, the condition, the
               utterance it points back to, and what she held right after it -- or "unknown" when that was not
               captured (it is never reconstructed and presented as memory);
        now    how the predicate stands today (overall and under each condition), which later occasions changed it,
               and what is still unresolved;
  * nothing here writes.  Reading a memory adds no occasion, no count, no evidence and no maturity: recalling
    is not re-experiencing (`evidence_qualification` already keeps a recollection from counting; this module simply
    never records one).  A genuinely new statement or observation after a recall is recorded by the ordinary
    intake as a new occasion with its own time.

Readers: `aurora_learned_rules._derive_fact` (what she answers when asked about a fact: the condition-aware answer
and, when her understanding changed, what she held before) and the established strata evidence packet in aurora.py
(`experiential_recall`), which every later stage of a turn can see.  Both read a BOUNDED view: a handful of
predicates, a handful of occasions each.  The cost is index lookups on the words of the turn; there is no scan of
her history and no loop of its own.

Constraint axis: T (what was, in the order it was).
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional

VIEW_VERSION = 1
MAX_OCCASIONS = 6          # occasions shown per predicate: the first, every one that changed what she held, the latest
MAX_RECORDS = 3            # predicates shown per turn in the strata evidence packet
UNKNOWN = "unknown"


def _pu():
    from aurora_internal import aurora_propositional_understanding as P
    return P


def _held_after(entry: Mapping[str, Any]) -> Dict[str, Any]:
    """What she held right after an occasion, as recorded at the time, or unknown."""
    v = entry.get("v")
    if v:
        return {"verdict": str(v), "source": "recorded"}
    return {"verdict": UNKNOWN, "source": "not captured"}


def _occasion(entry: Mapping[str, Any], index: int) -> Dict[str, Any]:
    e = dict(entry)
    held = _held_after(e)
    out = {"seq": int(e.get("s") or 0) or None, "index": index, "t": e.get("t"), "by": str(e.get("by") or "") or UNKNOWN,
           "said": "denied" if e.get("d") else "said", "basis": str(e.get("b") or UNKNOWN),
           "condition": str(e.get("w") or ""), "held_after": held["verdict"], "held_after_source": held["source"]}
    if e.get("vw"):
        out["held_after_under_condition"] = str(e["vw"])
    out["episode"] = {"ref": str(e["h"])} if e.get("h") else {"ref": None, "status": UNKNOWN}
    return out


def recollect_predicate(rel: Any, predicate: str) -> Optional[Dict[str, Any]]:
    """Then and now for one predicate on one relation.  None if nothing was said along it.  Reads only."""
    P = _pu()
    a = dict(getattr(rel, "assertion", None) or {})
    p = dict(dict(a.get("predicates") or {}).get(predicate) or {})
    if not p:
        return None
    hist = [dict(e) for e in (p.get("history") or [])]
    recorded = sum(int(v or 0) for v in dict(p.get("basis") or {}).values())
    complete = bool(hist) and len(hist) >= recorded
    occasions = [_occasion(e, i) for i, e in enumerate(hist)]
    # an occasion that changed what she held: its held-after differs from the one before it (both recorded)
    changed: List[Dict[str, Any]] = []
    prev = None
    for o in occasions:
        v = o["held_after"]
        if v != UNKNOWN and prev not in (None, UNKNOWN) and v != prev:
            changed.append(o)
        prev = v if v != UNKNOWN else prev
    now_v = P.verdict(p)
    conds = P.conditional_standing(p)
    known_then = [o for o in occasions if o["held_after"] != UNKNOWN]
    # what she held before her understanding last changed: the recorded held-after just before the last change
    before = None
    if changed:
        last = changed[-1]
        earlier = [o for o in known_then if o["index"] < last["index"]]
        if earlier:
            before = {"verdict": earlier[-1]["held_after"], "until": last["t"], "changed_by": dict(last)}
    shown = _bounded(occasions, changed)
    gaps = []
    if not complete:
        gaps.append("history thinned: only the first and latest occasions are kept in full")
    if any(o["held_after"] == UNKNOWN for o in occasions):
        gaps.append("what she held after some occasions was not captured at the time")
    return {
        "version": VIEW_VERSION,
        "source": str(getattr(rel, "source_word", "") or ""), "predicate": predicate,
        "target": str(getattr(rel, "target_word", "") or ""),
        "then": shown,
        "now": {"verdict": now_v, "settled": dict(p.get("settled") or {}),
                "conditions": [{"key": c["key"], "verdict": c["verdict"], "n": c["n"], "denied": c["denied"]} for c in conds]},
        "revised": bool(before) and before["verdict"] != now_v,
        "before_revision": before,
        "unresolved": [c["key"] for c in conds if c["verdict"] == "contested"] + (["overall"] if now_v == "contested" else []),
        "occasions_recorded": int(p.get("seq") or recorded),
        "history_complete": complete,
        "unknown": gaps,
    }


def _bounded(occasions: List[Dict[str, Any]], changed: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """First, every occasion that changed what she held, latest -- in the order they happened, at most MAX_OCCASIONS."""
    if len(occasions) <= MAX_OCCASIONS:
        return occasions
    keep = {occasions[0]["index"], occasions[-1]["index"]} | {o["index"] for o in changed}
    picked = [o for o in occasions if o["index"] in keep]
    if len(picked) > MAX_OCCASIONS:
        picked = picked[:1] + picked[-(MAX_OCCASIONS - 1):]
    return picked


def recollect(web: Any, words: Iterable[str], *, only_developed: bool = True, limit: int = MAX_RECORDS) -> List[Dict[str, Any]]:
    """The bounded then/now view for the relations her web holds about these words (found through the web's own
    source/target index, never a scan).  With `only_developed`, only predicates whose understanding moved (revised,
    held under conditions, or still unresolved) are returned -- the ones where then and now are worth telling apart."""
    if web is None:
        return []
    by_source = getattr(web, "_relations_by_source", {}) or {}
    by_target = getattr(web, "_relations_by_target", {}) or {}
    relations = getattr(web, "relations", {}) or {}
    out: List[Dict[str, Any]] = []
    seen = set()
    for w in [str(x).lower() for x in words if str(x).strip()][:6]:
        for rid in list(by_source.get(w, ()) or ()) + list(by_target.get(w, ()) or ()):
            if rid in seen:
                continue
            seen.add(rid)
            rel = relations.get(rid)
            if rel is None or not getattr(rel, "assertion", None):
                continue
            for pred in sorted(dict(rel.assertion).get("predicates") or {}):
                rec = recollect_predicate(rel, pred)
                if rec is None:
                    continue
                developed = rec["revised"] or len(rec["now"]["conditions"]) > 1 or rec["unresolved"]
                if only_developed and not developed:
                    continue
                out.append(rec)
                if len(out) >= limit:
                    return out
    return out


def resolve_episodes(record: Mapping[str, Any], entries: Iterable[Mapping[str, Any]],
                     said_ref: Optional[Callable[[Any], str]] = None) -> Dict[str, Any]:
    """Attach the remembered episode to each occasion of a record, from her conversation memory entries, by the
    utterance reference the occasion carries (never by the clock).  An occasion whose episode is not found stays
    marked unknown.  Returns a new record; neither the record nor the entries are changed."""
    ref_of = said_ref or _pu().said_ref
    wanted = {o["episode"].get("ref") for o in record.get("then") or [] if o.get("episode", {}).get("ref")}
    found: Dict[str, Dict[str, Any]] = {}
    if wanted:
        for e in entries:
            r = ref_of(e.get("user_said"))
            if r in wanted and r not in found:
                found[r] = {"ref": r, "time": e.get("timestamp"), "turn_id": e.get("turn_id"), "session": e.get("session_id"),
                            "heard": str(e.get("user_said") or "")[:160], "she_said": str(e.get("aurora_said") or "")[:160],
                            "tone": e.get("emotional_tone") if e.get("emotional_tone") not in (None, "") else UNKNOWN,
                            "topic": e.get("topic") if e.get("topic") not in (None, "") else UNKNOWN}
    out = dict(record)
    then = []
    for o in record.get("then") or []:
        o = dict(o)
        ref = o.get("episode", {}).get("ref")
        o["episode"] = found.get(ref) or {"ref": ref, "status": UNKNOWN}
        then.append(o)
    out["then"] = then
    return out


def compact(record: Mapping[str, Any]) -> Dict[str, Any]:
    """The small form carried in a turn's strata evidence: who/what, now, before-revision, and the occasions
    reduced to (when, said, basis, condition, held after)."""
    return {"about": [record.get("source"), record.get("predicate"), record.get("target")],
            "now": dict(record.get("now") or {}), "revised": bool(record.get("revised")),
            "before_revision": ({"verdict": record["before_revision"]["verdict"], "until": record["before_revision"]["until"]}
                                if record.get("before_revision") else None),
            "then": [{k: o.get(k) for k in ("t", "said", "basis", "condition", "held_after")} for o in record.get("then") or []][:MAX_OCCASIONS],
            "unresolved": list(record.get("unresolved") or []), "unknown": list(record.get("unknown") or [])}

# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Weaving what she stores into the crystal architecture: every store's records into the facets of their concepts, every link into typed associations.

Isolated and read-only: it loads stores from a state directory (or takes them as plain dicts), builds a `FacetBook` and an `AssociationStore`, and
reports what the crystals would hold.  It writes nothing to any state, creates no crystal and changes no running system; `crystal_facets.apply_to_crystals`
and `crystal_associations.apply_to_crystals` are the only writers, both dry-run by default.

The evidence contract (`evidence_qualification`) is honoured exactly: an occasion counts only if the contract says it counts (told/observed/corrected, and
not a recollection); a dreamed, imagined, simulated, overheard or unknown-provenance occasion is kept and earns nothing; a record with no provenance is never
upgraded.  What the genealogy has qualified by kind of occurrence (lived / hypothetical / overheard, externally demonstrated) arrives with that qualification.

  * `place_event(book, concept, kind, key, content, event)`   an evidence-contract event as an occasion on one entry.
  * `genealogy_associations(pair_stats, links)`               representation pairs and promoted links as typed associations (recurrence of use).
  * `weave(state)`                                            everything above plus OETS, assertions and the waveform cycle; returns the book, the store and a summary.
  * `consequence(store, concept_index)`                       what linking changes: reach, hubs found, wholes that converge.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Iterable, List, Mapping, Optional

from aurora_internal import crystal_facets as _F
from aurora_internal import crystal_convergence as _C
from aurora_internal import crystal_maturity as _M
from aurora_internal import evidence_qualification as _Q
from aurora_internal.crystal_associations import AssociationStore, project_assertions, project_oets
from aurora_internal import crystal_lexicon as _L

# One exposure (two representations used together, or one distinct input) is worth this much; n exposures add up as 1 - (1 - w)^n, so more always means more.
PAIR_EXPOSURE = 0.1


def _accrued(n: int) -> float:
    return 1.0 - (1.0 - PAIR_EXPOSURE) ** max(0, int(n))


def place_event(book: _F.FacetBook, concept: str, kind: str, key: str, content: Any, event: Mapping[str, Any], *, ref: Optional[str] = None) -> bool:
    """One evidence-contract event as an occasion on the entry (kind, key) of a concept.  Counts only if the contract says it counts; a negated event is
    evidence against; occurrence, context, ancestry and consequence travel with it; the same event twice is one occasion."""
    counted = _Q.counts(event)
    basis = event["basis"] if counted else ("recalled" if event.get("occurrence", "") in _Q.NON_EVIDENCE else event["basis"] if event["basis"] not in _F.COUNTED_BASES else "uncounted")
    return book.add(concept, kind, key, content, ref=ref or str(event["id"]), source=event.get("occurrence", ""), basis=basis,
                    polarity=-1 if event.get("negated") else 1, occurrence_class=event.get("occurrence", ""),
                    context=event.get("context"), consequence=event.get("consequence"), ancestry=event.get("ancestry") or ())


def place_exercise(book: _F.FacetBook, concepts: Iterable[str], *, ability_id: str, input_event: Mapping[str, Any],
                   consequence: Optional[Mapping[str, Any]] = None, ancestry: Iterable[str] = (), where: Optional[Mapping[str, Any]] = None,
                   content: Optional[Mapping[str, Any]] = None) -> int:
    """She exercised an operation (an ability or a promoted link) while dealing with some concepts: it lands as an `operation` entry in the crystal of EACH of
    those concepts, in the same crystals as everything else about them, never in crystals of its own.  Each distinct input is one occasion, worth one
    exposure, so more occasions mean more.  How it counts follows how the input happened to her: a lived input (heard, read, perceived, acted, tested)
    with a consequence she witnessed counts as observed; a lived input with no consequence recorded is kept and not counted (the effect was not witnessed);
    a rehearsal that was only imagined, simulated or dreamed is kept as supposed; overheard is kept as overheard.  A rehearsal she acted on or tested, or
    that was addressed to her, is a lived occurrence and is classed as one; the contract's classification is used as it is."""
    occ = str(input_event.get("occurrence", ""))
    if occ in _Q.HYPOTHETICAL:
        basis = "supposed"
    elif occ == "overheard":
        basis = "overheard"
    elif occ in _Q.LIVED and consequence:
        basis = "observed"
    else:
        basis = "unknown"
    n = 0
    for c in concepts:
        ctx = dict(input_event.get("context") or {})
        ctx.update(dict(where or {}))                      # where and when it developed, and what was associated with it then
        n += bool(book.add(c, "operation", str(ability_id), {"id": str(ability_id), **dict(content or {})},
                           ref=f"exercise:{ability_id}:{input_event['id']}:{c}", source=occ,
                           basis=basis, strength=PAIR_EXPOSURE, occurrence_class=occ, context=ctx or None, consequence=consequence,
                           ancestry=list(ancestry) + [str(input_event["id"])]))
    return n


def place_conversation(book: _F.FacetBook, entries: Iterable[Mapping[str, Any]], known_concepts: Iterable[str]) -> int:
    """Conversations are her lived experiential history, and she is in them from either position (Sir, 2026-11-15): what was said TO her is told, what she
    herself said she witnessed.  Each record becomes an `episode_ref` (id, time, short summary) at every known concept either side mentioned, once, with
    each occasion attached; the record's own importance is how strongly it weighs, and its tone, topic and session are its context.  The text is not copied."""
    known = {str(c).lower(): str(c) for c in known_concepts}
    n = 0
    for e in entries:
        ts, sess = e.get("timestamp"), str(e.get("session_id") or "")
        turn = str(e.get("turn_id") or "")                                # the recorded input turn: the same id as the event subject `input|<turn>|-`
        eid = turn or (f"{sess}:{int(ts)}" if ts is not None else "")
        if not eid:
            continue
        weight = e.get("importance")
        weight = 1.0 if weight is None else max(0.0, min(1.0, float(weight)))
        ctx = {"session": sess, "topic": e.get("topic"), "tone": e.get("emotional_tone")}
        if turn:
            ctx["turn_id"] = turn
        for position, field, basis in (("heard", "user_said", "told"), ("spoke", "aurora_said", "observed")):
            text = str(e.get(field) or "")
            words = {w.strip(".,!?;:\"'()").lower() for w in text.split()}
            for w in sorted(words & set(known)):
                n += bool(book.add(known[w], "episode_ref", eid, {"id": eid, "time": ts, "summary": text[:160]}, ref=f"conv:{eid}:{position}:{known[w]}",
                                   source="conversation", basis=basis, strength=weight, occurrence_class=position, context=ctx))
    return n


def turn_concepts_of(entries: Iterable[Mapping[str, Any]], known_concepts: Iterable[str]) -> Dict[str, List[str]]:
    """Turn id -> the known concepts that turn's record mentioned (either side), for the join in `concepts_of_inputs`.  Only records that carry a turn id are
    joined; one without is left out, never matched by the clock."""
    known = {str(c).lower(): str(c) for c in known_concepts}
    out: Dict[str, List[str]] = {}
    for e in entries:
        turn = str(e.get("turn_id") or "")
        if not turn:
            continue
        words = {w.strip(".,!?;:\"'()").lower() for f in ("user_said", "aurora_said") for w in str(e.get(f) or "").split()}
        hit = sorted(known[w] for w in words & set(known))
        if hit:
            out.setdefault(turn, [])
            out[turn] = sorted(set(out[turn]) | set(hit))
    return out


def place_development(book: _F.FacetBook, concepts: Iterable[str], *, rep_id: str, record: Mapping[str, Any], input_event: Mapping[str, Any],
                      associated: Iterable[str] = (), consequence: Optional[Mapping[str, Any]] = None) -> int:
    """A representation (an ability or a promoted link) attaches to the crystals of the concepts it developed among, with where and when it developed (the
    tick and time it was made, the input that exercised it), the operation it is (its lineage and signature), what it was made from (its parents are its
    ancestry), and the associated information present when it did (`associated`: the other representations and concepts it co-occurred with)."""
    sem = record.get("semantic_identity") or {}
    where = {"developed_at_tick": record.get("created_at_tick"), "input_time": input_event.get("t"), "depth": record.get("depth"),
             "associated": sorted(str(a) for a in associated)}
    content = {"parents": [str(p) for p in record.get("parents") or []], "operation_lineage": sem.get("operation_lineage"),
               "signature": sem.get("origin_signature"), "dominant_relief_axis": record.get("dominant_relief_axis")}
    return place_exercise(book, concepts, ability_id=rep_id, input_event=input_event, consequence=consequence,
                          ancestry=[str(p) for p in record.get("parents") or []], where=where, content=content)


def concepts_of_inputs(ledger_row: Mapping[str, Any], input_events: Mapping[str, Mapping[str, Any]],
                       turn_concepts: Mapping[str, Iterable[str]]) -> Dict[str, List[str]]:
    """For one representation's ledger row: input id -> the concepts of the turn that input was.  An input whose turn is not in `turn_concepts` is left
    out (no join is guessed from the clock); the turn id is read from the input event's subject, `input|<turn>|-`."""
    out: Dict[str, List[str]] = {}
    for cls in (ledger_row.get("by") or {}).values():
        for iid in cls.get("inputs") or []:
            subject = str((input_events.get(iid) or {}).get("subject", ""))
            parts = subject.split("|")
            turn = parts[1] if len(parts) == 3 and parts[0] == "input" else ""
            cs = list(turn_concepts.get(turn) or [])
            if cs:
                out[iid] = cs
    return out


def place_cycle_operations(book: _F.FacetBook, cycle: Mapping[str, Any], *, occurrence_class: str = "") -> int:
    """The operations that parented a waveform cycle's developed understanding (`genealogy_trace.parent_operation_ids`) land in the crystals of the concepts
    that understanding was about (the subject and object of its effective relation), the cycle being the input.  The cycle's own admission rule decides
    whether its effect was witnessed: a consequence is attached only when `representation_experiment_result.evidence_admitted` is true; otherwise the
    operation is kept and not counted.  A cycle with no developed relation has no concepts to attach to and places nothing."""
    eff = cycle.get("effective_interpretation") or {}
    concepts = [c for c in (str(eff.get("subject") or ""), str(eff.get("obj") or "")) if c]
    cid = str(cycle.get("cycle_id") or "")
    if not (cid and concepts and str(eff.get("relation") or "")):
        return 0
    res = cycle.get("representation_experiment_result") or {}
    ctrl = cycle.get("representation_experiment_control") or {}
    consequence = ({"target": "representation_relation", "change": str(res.get("status") or ""), "marginal_l1": ctrl.get("marginal_l1")}
                   if res.get("evidence_admitted") else None)
    event = {"id": cid, "occurrence": occurrence_class}
    n = 0
    for op in (cycle.get("genealogy_trace") or {}).get("parent_operation_ids") or []:
        n += place_exercise(book, concepts, ability_id=str(op), input_event=event, consequence=consequence)
    return n


def genealogy_associations(pair_stats: Mapping[str, Mapping[str, Any]], links: Mapping[str, Mapping[str, Any]],
                           store: Optional[AssociationStore] = None) -> AssociationStore:
    """Representations used together become `used_with` associations by recurrence (each pair's observed count, each exposure weak); a promoted link is
    `composed_of` its parents, held by recurrence too (it was promoted because its parts kept recurring together).  A link whose genealogy has qualified its
    evidence by kind of occurrence also carries that: lived inputs (which include any externally demonstrated: counting those again would double them) as observed evidence, hypothetical ones as supposed
    (kept, not counted), overheard ones as unknown (kept, not counted).  A link with no recorded ledger adds nothing beyond its recurrence."""
    store = store if store is not None else AssociationStore()
    for key, p in (pair_stats or {}).items():
        n = int(p.get("count", 0) or 0)
        a, b = str(p.get("left_id") or ""), str(p.get("right_id") or "")
        if n > 0 and a and b:
            store.add(a, b, "used_with", ref=f"pair:{key}", source="co-occurrence", strength=_accrued(n), confidence=1.0)
    for lid, link in (links or {}).items():
        n = int((link.get("stats") or {}).get("count", 0) or 0)
        for parent in link.get("parents") or []:
            if n > 0:
                store.add(str(lid), str(parent), "composed_of", ref=f"link:{lid}:{parent}", source="co-occurrence", strength=_accrued(n), confidence=1.0)
        by = ((link.get("evidence_qualification") or {}).get("by_kind") or {})
        for kind, src in (("lived", "observed"), ("hypothetical", "supposed"), ("overheard", "overheard")):
            k = by.get(kind) or {}
            ni = int(k.get("n_inputs", 0) or 0)
            for parent in link.get("parents") or []:
                if ni > 0:
                    store.add(str(lid), str(parent), "composed_of", ref=f"link:{lid}:{parent}:{kind}", source=src, strength=_accrued(ni), confidence=1.0)
    return store


def _read(state_dir: str, *parts: str) -> Any:
    try:
        with open(os.path.join(state_dir, *parts), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


# -- what each crystal has been through, as the seven points; and the writer that lets that decide its growth -----------------------------------------

_EXTERNAL_LIVED = {"tested", "acted", "perceived"}


def maturity_points(concept: str, store: AssociationStore, book: _F.FacetBook) -> Dict[str, Any]:
    """The crystal's points from counted evidence only: association from the counted ties it holds; abstraction from the distinct contexts the evidence came
    from; recurrence from the distinct sessions; cognitive from the share of its witnessed consequences that were shown outside her own simulation (a lived
    test, action or perception in the external world); recursive from how far the members it holds as `is_a` have themselves become composite.  Emotional
    is how many of its counted occasions carried a feeling (a recorded tone that is not neutral), as a degree; it is unknown (None) when none of its counted
    occasions recorded a tone at all, since then nothing was looked at.  Polarity is not wired and stays unknown."""
    occ = book.counted_occasions(concept)
    contexts = {json.dumps(o["context"], sort_keys=True, default=str) for o in occ if o["context"]}
    sessions = {str(o["context"]["session"]) for o in occ if isinstance(o["context"], dict) and o["context"].get("session")}
    witnessed = [o for o in occ if o["consequence"]]
    shown = [o for o in witnessed if o["basis"] == "observed" and o["occurrence_class"] in _EXTERNAL_LIVED
             and isinstance(o["context"], dict) and o["context"].get("world") == "external"]
    members = store.incoming(concept, "is_a")
    promoted = sum(_M.memberships({"associative": _M.points_from_evidence(association_strengths=store.connections_for(m).values())["associative"]})[2]
                   for m in members)
    tones = [t for t in (str(o["context"].get("tone") or "").strip().lower() for o in occ if isinstance(o["context"], dict)) if t]        # an empty tone recorded nothing
    felt = sum(1 for t in tones if t not in _M.NEUTRAL_TONES)
    emotional = _M.degree(felt, _M.REF_EMOTIONAL) if tones else None
    return _M.points_from_evidence(association_strengths=store.connections_for(concept).values(), contexts=len(contexts), sessions=len(sessions),
                                   consequences_shown=len(shown), consequences_total=len(witnessed), members_promoted=promoted, members_total=len(members),
                                   emotional=emotional)


def apply_maturity(store: AssociationStore, book: _F.FacetBook, concept_index: Mapping[str, str], crystals: Mapping[str, Any],
                   dry_run: bool = True) -> Dict[str, Any]:
    """Set `crystal.maturity` for every concept that has a crystal, so its growth follows what it has actually been through.  A concept with no counted
    evidence is set with its points at zero (looked for and found nothing), which holds it where it is.  `dry_run` (default) changes nothing and reports
    how many crystals would be ready to grow under the evidence and, for comparison, under the count rule they had."""
    n = ready = held_by_counts = 0
    for concept, cid in concept_index.items():
        crystal = crystals.get(cid)
        if crystal is None:
            continue
        pts = maturity_points(concept, store, book)
        n += 1
        r = _M.ready_to_grow(pts, int(crystal.level))
        ready += bool(r)
        held_by_counts += bool(not r and getattr(crystal, "maturity", None) is None and crystal.can_evolve())
        if not dry_run:
            crystal.maturity = pts
    return {"crystals": n, "ready_to_grow": ready, "ready_by_counts_but_not_by_evidence": held_by_counts, "dry_run": bool(dry_run)}


def _one_store(web: Dict[str, Any]) -> Dict[str, Any]:
    """A word under a bookkeeping label is the word (see crystal_store): its node and the relations that mention it are placed at the word."""
    from aurora_internal.crystal_store import bare_of
    nodes: Dict[str, Any] = {}
    for key, node in (web.get("nodes") or {}).items():
        bare = bare_of(key)
        if bare in nodes and bare != key:
            continue
        nodes[bare] = dict(node, word=bare_of(node.get("word"))) if isinstance(node, dict) and node.get("word") else node
    rels = {}
    for rid, r in (web.get("relations") or {}).items():
        rels[rid] = dict(r, source_word=bare_of(r.get("source_word", "")), target_word=bare_of(r.get("target_word", ""))) if isinstance(r, dict) else r
    return dict(web, nodes=nodes, relations=rels)


def weave(state_dir: str) -> Dict[str, Any]:
    """Run every adapter over what is in `state_dir`.  Returns {'book', 'store', 'summary'}.  Reads only."""
    book, summary = _F.FacetBook(), {}
    web = _one_store(_read(state_dir, "aurora_oets_web.json") or {})
    for node in (web.get("nodes") or {}).values():
        _F.place_oets_node(book, node)
    lexicon, lex_rep = _L.fold_entries(_L.read_entries(state_dir))          # one entry per word, whatever label it was filed under
    summary["lexicon"] = dict(lex_rep, placed=_L.place(book, lexicon))
    store = project_assertions(web.get("relations") or {}, project_oets(web.get("relations") or {}))
    summary["oets"] = {"nodes": len(web.get("nodes") or {}), "relations": len(web.get("relations") or {})}
    pairs, links = _read(state_dir, "genealogy", "pair_stats.json") or {}, _read(state_dir, "genealogy", "links.json") or {}
    genealogy_associations(pairs, links, store)
    summary["genealogy"] = {"pairs": len(pairs), "links": len(links), "links_with_qualification": sum(1 for v in links.values() if v.get("evidence_qualification"))}
    _F.place_associations(book, store)
    mem = _read(state_dir, "aurora_conversation_memory.json") or {}
    summary["conversations"] = {"records": len(mem.get("entries") or []),
                                "placements": place_conversation(book, mem.get("entries") or [], list((web.get("nodes") or {}).keys()))}
    cyc = (_read(state_dir, "recursive_causal_reasoning_waveform.json") or {}).get("active_cycle") or {}
    summary["waveform_cycle"] = _F.place_cycle(book, cyc, occurrence_class="") if cyc else None
    summary["waveform_operations"] = place_cycle_operations(book, cyc, occurrence_class="") if cyc else 0
    summary["book"] = book.totals()
    summary["associations"] = {"records": len(store), "basis_counts": store.basis_counts()}
    return {"book": book, "store": store, "summary": summary}


def consequence(store: AssociationStore, concept_index: Mapping[str, str], hub: Optional[str] = None) -> Dict[str, Any]:
    """What the links change, measured over the concepts that have a crystal: how many crystals gain any connection, how far the connected web reaches from
    one concept in two steps, which hubs the `is_a` associations already form, and how strongly the busiest wholes converge."""
    have = set(concept_index)
    adj: Dict[str, Dict[str, float]] = {c: {o: s for o, s in store.connections_for(c).items() if o in have and o != c} for c in have}
    connected = [c for c, a in adj.items() if a]
    out: Dict[str, Any] = {"crystals": len(have), "crystals_with_connections": len(connected),
                           "links": sum(len(a) for a in adj.values()) // 2}
    hub = hub or (max(connected, key=lambda c: len(adj[c])) if connected else None)
    if hub:
        one = set(adj[hub])
        two = set(one)
        for o in one:
            two |= set(adj[o])
        two.discard(hub)
        out["reach"] = {"hub": hub, "one_step": len(one), "two_steps": len(two), "share_of_crystals": round(len(two) / max(1, len(have)), 4)}
    hubs = {}
    for c in have:
        held = _C.members_of(store, c)
        if held:
            hubs[c] = len(held)
    out["wholes_formed_by_is_a"] = {"hubs": len(hubs), "largest": sorted(hubs.items(), key=lambda kv: -kv[1])[:5]}
    return out

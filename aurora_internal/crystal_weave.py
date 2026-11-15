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
from aurora_internal import evidence_qualification as _Q
from aurora_internal.crystal_associations import AssociationStore, project_assertions, project_oets

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


def weave(state_dir: str) -> Dict[str, Any]:
    """Run every adapter over what is in `state_dir`.  Returns {'book', 'store', 'summary'}.  Reads only."""
    book, summary = _F.FacetBook(), {}
    web = _read(state_dir, "aurora_oets_web.json") or {}
    for node in (web.get("nodes") or {}).values():
        _F.place_oets_node(book, node)
    store = project_assertions(web.get("relations") or {}, project_oets(web.get("relations") or {}))
    summary["oets"] = {"nodes": len(web.get("nodes") or {}), "relations": len(web.get("relations") or {})}
    pairs, links = _read(state_dir, "genealogy", "pair_stats.json") or {}, _read(state_dir, "genealogy", "links.json") or {}
    genealogy_associations(pairs, links, store)
    summary["genealogy"] = {"pairs": len(pairs), "links": len(links), "links_with_qualification": sum(1 for v in links.values() if v.get("evidence_qualification"))}
    _F.place_associations(book, store)
    cyc = (_read(state_dir, "recursive_causal_reasoning_waveform.json") or {}).get("active_cycle") or {}
    summary["waveform_cycle"] = _F.place_cycle(book, cyc, occurrence_class="") if cyc else None
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

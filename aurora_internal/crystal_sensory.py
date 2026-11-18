# Authors: Sunni (Sir) Morningstar & Cael Devo
"""Perception in the one crystal store (Sir, 2026-11-15).

What she has perceived reaches the crystals as counted evidence, at the crystal it belongs to, not as a store of its own:

  * each of the six sensory facets (tone, timbre, rhythm, hue, shape, motion) is ONE crystal, `sensory:<domain>:<facet>`;
  * each node of a facet is a particular held inside that crystal (kind `particular`), not a crystal of its own.  It is held by what she observed: the
    observations (how many), how well the node holds (its confidence) and the independent sessions they came from (its weight: frames inside one session
    are one meeting with the thing, so sessions, not frames, are the occasions);
  * the facet pairs the semantic middle plane joins (tone-hue, timbre-shape, rhythm-motion) are tied by the cross-modal nodes that were seen together,
    by co-occurrence, which is counted.

Nothing here is read from a node's own lifecycle stage (primitive, concept, promoted): that count rule is its own, and the crystal's standing comes from the
evidence rule like every other crystal's.  A facet gets a crystal only when counted perception stands behind it.  Reads only; imports nothing of the stack.
"""
from __future__ import annotations

import gzip
import json
import os
from typing import Any, Callable, Dict, List

from aurora_internal.crystal_facets import FacetBook
from aurora_internal.crystal_associations import AssociationStore

FACETS = (("audio", "tone"), ("audio", "timbre"), ("audio", "rhythm"), ("visual", "hue"), ("visual", "shape"), ("visual", "motion"))
PREFIX = "sensory:"


def concept(domain: str, facet: str) -> str:
    return f"{PREFIX}{domain}:{facet}"


def _agb(path: str) -> Dict[str, Any]:
    try:
        with gzip.open(path, "rb") as fh:
            d = json.loads(fh.read().decode("utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def read_state(state_dir: str) -> Dict[str, Any]:
    """{'facets': {(domain, facet): [node dicts]}, 'semantic': [node dicts]} from `aurora_state/sensory_crystal/`."""
    base = os.path.join(str(state_dir), "sensory_crystal")
    facets: Dict[Any, List[Dict[str, Any]]] = {}
    for domain, facet in FACETS:
        nodes = _agb(os.path.join(base, domain, facet, "state.agb")).get("nodes") or []
        facets[(domain, facet)] = [n for n in (nodes.values() if isinstance(nodes, dict) else nodes) if isinstance(n, dict)]
    sem = (_agb(os.path.join(base, "semantic", "state.agb")).get("semantic") or {})
    return {"facets": facets, "semantic": [n for n in (sem.values() if isinstance(sem, dict) else sem) if isinstance(n, dict)]}


def node_name(domain: str, facet: str, n: Dict[str, Any]) -> str:
    """A node's own name if it has one; an archetype seed is named by its archetype; otherwise its id, shortened."""
    name = str(n.get("name") or "").strip()
    nid = str(n.get("node_id") or "")
    pre = f"arch_{facet}_"
    return name or (nid[len(pre):] if nid.startswith(pre) else nid[:12])


def place(book: FacetBook, store: AssociationStore, state_dir: str, accrued: Callable[[int], float]) -> Dict[str, int]:
    """Counted perception into the book (nodes, as particulars of their facet) and the store (the cross-modal ties between facets)."""
    state = read_state(state_dir)
    nodes = ties = 0
    for (domain, facet), rows in state["facets"].items():
        c = concept(domain, facet)
        for n in rows:
            uses, sessions = int(n.get("usage_count") or 0), int(n.get("session_count") or 0)
            nid = str(n.get("node_id") or "")
            if not nid or uses <= 0 or sessions <= 0:                    # nothing observed, nothing placed
                continue
            content = {"node": nid, "name": node_name(domain, facet, n), "stage": str(n.get("stage") or ""), "lineage": str(n.get("lineage_id") or ""),
                       "generation": int(n.get("generation") or 0), "observations": uses, "sessions": sessions}
            nodes += bool(book.add(c, "particular", nid, content, ref=f"sensory:{nid}", source="observed", strength=accrued(uses),
                                   confidence=float(n.get("confidence") or 0.0), weight=float(sessions)))
    for s in state["semantic"]:
        d, v = str(s.get("audio_facet") or ""), str(s.get("visual_facet") or "")
        seen = int(s.get("co_occurrence_count") or 0)
        if seen > 0 and d and v:
            ties += bool(store.add(concept("audio", d), concept("visual", v), "related_to", ref=f"semantic:{s.get('node_id')}", source="co-occurrence",
                                   strength=accrued(seen), confidence=float(s.get("confidence") or 0.0)))
    return {"nodes": nodes, "cross_modal_ties": ties}


def concepts_with_evidence(book: FacetBook) -> List[str]:
    """The sensory facets that counted perception stands behind: the only ones that get a crystal."""
    return [concept(d, f) for d, f in FACETS if book.facets_for(concept(d, f))]

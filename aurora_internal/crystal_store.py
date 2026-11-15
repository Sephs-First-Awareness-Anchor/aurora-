# Authors: Sunni (Sir) Morningstar & Cael Devo
"""One crystal store (Sir, 2026-11-15): a word is ONE crystal, whatever label it arrived under.

The lexicon and the ontological scaffolding label some meanings with bookkeeping prefixes (`learned:come`, `foundational:light`, `from_definition:time`).
A label is how something arrived, never a second thing, and a prefixed name must not become a second crystal for the same word: that splits one concept's
facets, ties and usage over two places and leaves each looking poorer than the concept is.

  * `canonical(concept)`        -> (bare name, prefix or None) for those prefixes only.  Namespaced entities that are not a word under a label
                                   (`tensor:`, `sensory:`, `REFAB:`, `behavioral:`, `turn:`...) are different things and are left as they are.
  * `fold_duplicates(dps)`      merges every prefixed crystal into the crystal of its bare word (creating it, by renaming, when there is none): facets are kept
                                   (a facet that only repeats the label is rewritten to the bare word, as the seeding writes it), ties are re-keyed and the
                                   stronger kept, usage adds, the earliest birth is kept, and the old name stays resolvable as an alias.  Idempotent.
  * `primary_index(dps)`        concept -> crystal id with ONE entry per crystal (its own concept), so a pass never counts an aliased crystal twice.

Provenance is kept as a facet (`provenance:<label>`, content the label), at the confidence of a label (low), so where the word came from is not lost.
"""
from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Tuple

# The bookkeeping prefixes of aurora.py::_PLACEHOLDER_DEFINITION_PREFIXES, plus the scaffold's own `foundational:` (a test keeps the two lists in step).
PREFIXES = ("from_definition:", "from meaning:", "internal:", "learned:", "pending:", "research:", "context:", "foundational:")
PROVENANCE_ROLE = "provenance:"            # one facet per label, `provenance:<label>`: a crystal keeps the facet of a role once, so each label needs its own role
LABEL_CONFIDENCE = 0.1


def canonical(concept: str) -> Tuple[str, Optional[str]]:
    """(bare name, prefix) when `concept` is a word under a bookkeeping label; (concept, None) otherwise (including a label with nothing after it)."""
    c = str(concept or "")
    for p in PREFIXES:
        if c.startswith(p):
            bare = c[len(p):].strip()
            return (bare, p[:-1]) if bare else (c, None)
    return c, None


def bare_of(text: Any) -> str:
    return canonical(str(text))[0]


def _note_provenance(crystal: Any, prefix: Optional[str]) -> None:
    if prefix and not any(f.role == PROVENANCE_ROLE + prefix for f in crystal.facets.values()):
        crystal.add_facet(PROVENANCE_ROLE + prefix, prefix, confidence=LABEL_CONFIDENCE)


def primary_index(dps: Any) -> Dict[str, str]:
    """concept -> crystal id, one entry per crystal, under the crystal's own concept (an alias never gets an entry of its own)."""
    return {c.concept: cid for cid, c in dps.crystals.items()}


def _merge_into(keep: Any, drop: Any, remap: Dict[str, str]) -> None:
    have = {(f.role, str(f.content)) for f in keep.facets.values()}
    bare = keep.concept
    for f in list(drop.facets.values()):
        content = f.content
        if isinstance(content, str) and canonical(content)[0] == bare and canonical(content)[1] is not None:
            content = bare                                   # a facet that only repeats its label says what the seeding says: the word
        if (f.role, str(content)) in have:
            continue
        got = keep.add_facet(f.role, content, confidence=f.confidence)
        have.add((f.role, str(content)))
        for attr in ("stability", "coherence", "resonance", "potential"):
            if hasattr(f, attr) and hasattr(got, attr):
                setattr(got, attr, max(getattr(got, attr), getattr(f, attr)))
    for cid, s in drop.connections.items():
        target = remap.get(cid, cid)
        if target != keep.crystal_id:
            keep.connections[target] = max(keep.connections.get(target, 0.0), s)
    keep.usage_count += drop.usage_count
    keep.created_at = min(keep.created_at, drop.created_at)
    if int(drop.level) > int(keep.level):
        keep.level = type(keep.level)(int(drop.level))
        getattr(keep, "_unlock_failpoints", lambda: None)()


def fold_duplicates(dps: Any) -> Dict[str, int]:
    """Make every word under a bookkeeping label one crystal with its bare word.  Never raises past a crystal it cannot read; returns counts."""
    report = {"folded": 0, "renamed": 0, "aliases": 0}
    labelled = sorted((c.concept, cid) for cid, c in dps.crystals.items() if canonical(c.concept)[1] is not None)
    if not labelled:
        return report
    by_concept = {c.concept: cid for cid, c in dps.crystals.items()}
    remap: Dict[str, str] = {}
    plan = []
    for concept, cid in labelled:
        bare, prefix = canonical(concept)
        target = by_concept.get(bare)
        if target is None or target == cid:
            crystal = dps.crystals[cid]                     # no crystal of the bare word yet: this one becomes it (its id is kept; the name changes)
            by_concept.pop(concept, None)
            crystal.concept = bare
            by_concept[bare] = cid
            dps.concept_index.pop(concept, None)
            dps.concept_index[bare] = cid
            _note_provenance(crystal, prefix)
            for f in crystal.facets.values():
                if isinstance(f.content, str) and canonical(f.content)[0] == bare and canonical(f.content)[1] is not None:
                    f.content = bare
            dps.concept_index[concept] = cid
            report["renamed"] += 1
            report["aliases"] += 1
            continue
        remap[cid] = target
        plan.append((concept, cid, target, prefix))
    for concept, cid, target, prefix in plan:
        keep, drop = dps.crystals[target], dps.crystals[cid]
        _merge_into(keep, drop, remap)
        _note_provenance(keep, prefix)
        dps.concept_index[concept] = target                # the old name still finds the one crystal
        del dps.crystals[cid]
        report["folded"] += 1
        report["aliases"] += 1
    if remap:
        for crystal in dps.crystals.values():              # ties that pointed at a folded crystal now point at the one
            for old, new in remap.items():
                if old in crystal.connections:
                    s = crystal.connections.pop(old)
                    if new != crystal.crystal_id:
                        crystal.connections[new] = max(crystal.connections.get(new, 0.0), s)
        links = getattr(dps, "crystal_links", None)
        if isinstance(links, dict):
            for old, new in remap.items():
                row = links.pop(old, None)
                if row:
                    mine = links.setdefault(new, {})
                    for k, v in row.items():
                        k = remap.get(k, k)
                        if k != new:
                            mine[k] = max(mine.get(k, 0.0), v)
            for row in links.values():
                for old, new in remap.items():
                    if old in row:
                        s = row.pop(old)
                        row[new] = max(row.get(new, 0.0), s)
        folded = getattr(dps, "folded_ids", None)
        if not isinstance(folded, dict):
            folded = {}
            dps.folded_ids = folded
        folded.update(remap)
    return report

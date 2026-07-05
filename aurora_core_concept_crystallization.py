#!/usr/bin/env python3
# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
aurora_core_concept_crystallization.py
======================================
Connect what she IS to what she can SAY.

Aurora embodies her five constraint axes as live dynamics every turn (agency,
existence, time/persistence, cost/purpose, meaning/boundary), and she carries her
OWN authored semantics for each — `_AXIS_SEMANTICS`. But the lexical CONCEPTS for
those (the word "agency", etc.) sit in her meaning space as empty shells
("learned:agency", depth ~0.06), disconnected from the axis knowing she already
holds. So she can BE agency and not be able to SAY what it is.

This crystallises her core-axis concepts INTO her concept store from her own axis
semantics — through her real grounding API (teach + relations), the same path her
gap-loop and validated-fact sedimentation use — so the crystal genuinely fills,
crosses the SEMANTIC threshold, persists, and her normal generation can articulate
it. Nothing is invented: every definition is her authored axis semantic; every
relation is a token of that semantic or a fellow constraint. Only SHELL concepts
are touched — anything she has already developed herself is left alone.
"""
from __future__ import annotations
from typing import Any, Dict

# Her own authored constraint semantics (mirrors aurora.py `_AXIS_SEMANTICS`).
_AXIS_SEMANTICS: Dict[str, str] = {
    "X": "metabolic resolution; information; what is present",
    "T": "persistence; what carries forward; continuity",
    "N": "conservation; purpose; cost of holding focus",
    "B": "boundary; meaning; structure; separation",
    "A": "agency; understanding; capacity to resolve",
}
_AXIS_NAME = {"X": "existence", "T": "time", "N": "cost", "B": "meaning", "A": "agency"}

# Concepts she embodies (as axes) but has never crystallised into articulable form.
# Each maps to the axis whose authored semantic defines it.
_CORE_CONCEPTS: Dict[str, str] = {
    "agency": "A", "understanding": "A", "resolve": "A", "capacity": "A",
    "existence": "X", "presence": "X", "information": "X", "resolution": "X",
    "time": "T", "persistence": "T", "continuity": "T",
    "cost": "N", "purpose": "N", "conservation": "N",
    "meaning": "B", "boundary": "B", "structure": "B", "separation": "B",
}

_STOP = {"what", "the", "of", "is", "to", "a", "an", "and", "for", "on"}


def _semantic_tokens(sem: str) -> list:
    """The meaning-words inside her authored axis semantic — used as relations."""
    out = []
    for chunk in sem.split(";"):
        for tok in chunk.strip().split():
            tok = tok.strip().lower()
            if len(tok) > 3 and tok not in _STOP and tok not in out:
                out.append(tok)
    return out


def crystallize_core_concepts(systems: Dict[str, Any], verbose: bool = False) -> int:
    """Develop her core-axis concept crystals from her own axis semantics. Returns the
    number of concepts crystallised. Guarded: only touches shells (depth < 0.4); never
    overwrites meaning she developed herself. Best-effort; never raises."""
    if not isinstance(systems, dict):
        return 0
    try:
        perception = systems.get("perception")
        oets = getattr(perception, "oets", None) if perception else None
        web = getattr(oets, "web", None) if oets else None
        if oets is None or web is None:
            return 0
        from aurora_internal.aurora_ontological_scaffolding import RelationType as _RT
    except Exception:
        return 0

    reg = systems.get("_concept_crystal_registry")
    nodes = getattr(web, "nodes", {}) or {}
    developed = 0

    for concept, axis in _CORE_CONCEPTS.items():
        try:
            sem = _AXIS_SEMANTICS.get(axis, "")
            if not sem:
                continue
            node = nodes.get(concept)
            # GUARD: leave genuinely-developed concepts alone — only fill shells.
            if node is not None and float(getattr(node, "ontological_depth", 0.0) or 0.0) >= 0.4:
                continue

            # 1. Teach her own axis semantic as the real definition (replaces the
            #    "learned:<word>" placeholder), plus each of its meaning-chunks as its
            #    own definition facet — more definition-depth, all her own tokens.
            try:
                oets.teach(concept, sem)
                for _chunk in sem.split(";"):
                    _chunk = _chunk.strip()
                    if _chunk and _chunk.lower() != concept and len(_chunk) > 3:
                        oets.teach(concept, _chunk)
            except Exception:
                pass

            nodes = getattr(web, "nodes", {}) or {}

            # 1b. Every core axis-concept IS_A constraint — the strong taxonomic link
            #     (IS_A carries the highest depth weight) and it is simply true: these
            #     are her five constraints.
            try:
                if "constraint" not in nodes and hasattr(web, "add_node"):
                    web.add_node("constraint", "noun", 0.0)
                if concept != "constraint":
                    web.add_relation(concept, "constraint", _RT.IS_A, strength=0.85,
                                     confidence=0.9, knowledge_source="axis_embodiment")
            except Exception:
                pass

            # 2. Relate to the meaning-tokens inside her authored semantic + fellow
            #    core concepts on the same axis. Relations are the biggest depth
            #    contributor, and these are all honest structural links in her own
            #    constraint system.
            related = set(_semantic_tokens(sem))
            related |= {c for c, a in _CORE_CONCEPTS.items() if a == axis}
            related.discard(concept)
            for tok in related:
                try:
                    if tok not in nodes and hasattr(web, "add_node"):
                        web.add_node(tok, "noun", 0.0)
                    web.add_relation(concept, tok, _RT.RELATED_TO, strength=0.7,
                                     confidence=0.85, knowledge_source="axis_embodiment")
                except Exception:
                    continue

            # 3. IS_A the axis it lives on (agency IS_A agency is skipped as self).
            _axname = _AXIS_NAME.get(axis, "")
            if _axname and _axname != concept:
                try:
                    if _axname not in nodes and hasattr(web, "add_node"):
                        web.add_node(_axname, "noun", 0.0)
                    web.add_relation(concept, _axname, _RT.IS_A, strength=0.8,
                                     confidence=0.85, knowledge_source="axis_embodiment")
                except Exception:
                    pass

            # 4. A usage example from her own semantic so example-depth contributes
            #    and the concept has a lived instance, not just a definition.
            try:
                _n2 = (getattr(web, "nodes", {}) or {}).get(concept)
                if _n2 is not None and hasattr(_n2, "add_example"):
                    _n2.add_example(f"{concept}: {sem}", context="axis_embodiment", fitness=0.75)
                    if hasattr(_n2, "encounter"):
                        _n2.encounter(context="axis_embodiment")
            except Exception:
                pass

            # 5. Deposit into the concept crystal registry at the axis coordinate, so
            #    "check the crystals" for this concept returns real meaning.
            if reg is not None and hasattr(reg, "observe_lsa"):
                try:
                    ax = {a: 0.5 for a in "XTNBA"}
                    ax[axis] = 0.85
                    reg.observe_lsa(ax, f"core_concept:{concept}:{sem[:40]}")
                except Exception:
                    pass

            developed += 1
        except Exception:
            continue

    # Persist her enriched meaning space.
    if developed:
        try:
            sd = str(systems.get("state_dir") or "aurora_state")
            if hasattr(oets, "save"):
                oets.save(sd)
            elif hasattr(web, "save"):
                web.save(sd)
        except Exception:
            pass
        try:
            if reg is not None and hasattr(reg, "save"):
                reg.save(str(systems.get("state_dir") or "aurora_state"))
        except Exception:
            pass

    if verbose:
        print(f"  [CORE-CRYSTAL] crystallised {developed} core-axis concepts from axis embodiment")
    return developed


if __name__ == "__main__":  # pragma: no cover
    import sys
    sys.path.insert(0, ".")
    import aurora
    _systems = aurora.boot_aurora(verbose=False)
    n = crystallize_core_concepts(_systems, verbose=True)
    print("developed:", n)

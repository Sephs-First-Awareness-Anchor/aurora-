#!/usr/bin/env python3
"""
AURORA GENEALOGY-TO-ENVIRONMENT DERIVATION
===========================================
Authors: Sunni (Sir) Morningstar & Cael Devo

Derives a native representational environment signature directly from a real
ConstraintLink genealogy DAG, using only physics that already exists in
aurora_closure_basis.py and aurora_internal/constraint_genealogy.py.

WHY THIS MODULE EXISTS (verified, not assumed)
-----------------------------------------------
constraint_genealogy._lineage_grade_for_pair() -> _merged_axis_counts_for_pair()
-> _axis_counts_from_item() DOES recurse the full ConstraintLink.parents DAG,
but only to accumulate a merged {X,T,N,B,A: count} frequency dict. Branch
topology, traversal order, and which specific ancestor contributed are
discarded in that path; shared ancestors reached via multiple parent paths
are re-added per path rather than deduplicated by identity.

_lineage_grade_payload() then synthesizes a 2-atom root_slot string from only
the dominant axis plus ONE other nonzero axis, and hands that synthetic
2-atom string to aurora_closure_basis.derive_lineage(). Everything beyond
"which axis is dominant, which one axis is secondary, how many generations
deep" is lost before the closure-basis physics ever sees it.

Separately, ConstraintGenealogyLogger.walk_link_sequence() (constraint_genealogy.py)
ALREADY walks the same ConstraintLink.parents DAG oldest-ancestor-first,
identity-deduplicated (no double counting of shared ancestors), and returns
one ordered entry per link: {link_id, i_state, recursion_level, axis,
mean_relief, depth}. It is currently consumed only by the Constraint Physics
Machine (aurora_computational_model.py) as an executable "program" — it is
never connected to the closure-basis lineage-grading physics.

This module closes that loop: it feeds walk_link_sequence()'s full ordered
trace into aurora_closure_basis's ALREADY multi-atom-capable root_slot parser
(_resolve_slots_from_root_slot splits on "x"/"x" with no atom-count limit)
instead of the current 2-atom synthetic string, and reads the resulting
InteractionSlot physics (dim_a/dim_b, depth_score, leverage_grade(),
formation_cost()) as the basis for a POLARITY/MAGNITUDE/OPERATOR/COST/
DIFFERENCE distribution, instead of returning only a single dominant value.

No new constants are introduced for "strictness", "creativity", or similar
behavioral thresholds. Every weight used below is a field or method that
already exists on NonCompChannel / InteractionSlot / ConstraintLineage, or a
direct re-use of walk_link_sequence's own axis->i_state / depth->recursion
mappings.

This module is READ-ONLY and OBSERVATIONAL. It does not write to WARP, to
aurora_internal.aurora_meaning_evolution, to Aurora625PressureMap, or to any
genealogy state. It has no domain branches (no "if substrate == 'memory'"),
and no hand-authored behavioral constants.

PHASE 1.1 — EDGE-FIDELITY REPAIR (still fully observational)
---------------------------------------------------------------------------
Two real bugs from the first pass, found by re-reading this file against
what it actually calls rather than what it was intended to do:

1. FALSE-EDGE FABRICATION. The original `derive_environment_signature()`
   built genealogical transitions from CONSECUTIVE ENTRIES in
   `walk_link_sequence()`'s flat output list, not from real
   `ConstraintLink.parents` edges. `walk_link_sequence()` is a post-order
   DFS: for a branching DAG (any node with 2+ parents), two nodes that are
   adjacent in the returned list are frequently siblings from independent
   branches with no real edge between them at all. Treating list-adjacency
   as an edge fabricated genealogical transitions that never happened.
   Fixed by `_derive_edges()` below, which reads each walked node's real
   `ConstraintLink.parents` directly and only ever pairs a node with an
   ancestor that is actually one of its parents.
2. ASCII SEPARATOR SILENT FAILURE. `_resolve_slots_from_root_slot()`
   (aurora_closure_basis.py:743-763) only takes the "split on ASCII 'x'"
   branch when `root_slot.count("x") == 1` -- i.e. exactly 2 atoms. The
   first pass joined every genealogy with ASCII "x", so for any genealogy
   with 3+ atoms (the common case: the 356-link shadow run's mean node
   count was 3.96, i.e. usually 3+ transitions) `_resolve_slots_from_root_slot`
   silently returned an EMPTY slot list, and `derive_lineage()` silently fell
   back to its axis+requires-only path -- meaning the "full chained
   root_slot" claim in the phase-1 report did not actually hold for most
   real genealogies it was run against. Fixed by joining with the canonical
   Unicode "×" `_resolve_slots_from_root_slot` checks FIRST, unconditionally,
   for any chain length.

Because `derive_lineage()`'s internal `_add()` helper
(aurora_closure_basis.py:959-962) deduplicates by `slot_id`, its returned
`ConstraintLineage` can never itself represent branch multiplicity or
topology -- two transitions that resolve to the same slot collapse to one
occurrence. That output is therefore renamed `closure_projection` here
(instead of `lineage`) and documented as exactly that: a real, physics-
grounded but slot-deduplicated reading of the edge-derived genealogy, not a
faithful replay of it. The faithful, non-deduplicated reading is
`edge_provenance` (every real edge, in traversal order, with full
multiplicity) plus the new `structural_hash` derived from it.
"""
from __future__ import annotations

import hashlib
import math
import os
import tempfile
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from aurora_closure_basis import (
    AXES,
    DIMENSION_FULL,
    DIMENSIONS,
    ConstraintLineage,
    derive_lineage,
    genealogy_atom_is_valid,
    genealogy_atom_to_channel_pair,
    slot_for_pair,
)

# ---------------------------------------------------------------------------
# I/II. Loading real ConstraintLink genealogy without duplicating its physics
# ---------------------------------------------------------------------------
# ConstraintGenealogyLogger.walk_link_sequence() is the existing full-DAG
# walker this module reuses. Constructing a full logger only needs `.links`
# populated; every other piece of __init__ state is irrelevant to that one
# method, so a throwaway logger in a temp directory is sufficient and avoids
# touching real aurora_state/genealogy/ files.

_DIM_NAME_BY_ENUM: Dict[Any, str] = dict(DIMENSION_FULL)
_ALL_DIM_NAMES: Tuple[str, ...] = tuple(_DIM_NAME_BY_ENUM[d] for d in DIMENSIONS)
_REC_KEYS: Tuple[str, ...] = ("REC_SURFACE", "REC_SHALLOW", "REC_MODERATE", "REC_DEEP", "REC_CORE")
_ISTATE_KEYS: Tuple[str, ...] = (
    "I_IS", "I_ISNT", "I_CAN", "I_CANNOT", "I_DO", "I_DONOT",
    "I_SAW", "I_SOUGHT", "I_DID", "I_DIDNT",
)


def link_from_dict(d: Dict[str, Any]) -> "ConstraintLink":
    """
    Reverse of ConstraintLink.to_dict() (aurora_internal/constraint_genealogy.py).
    Deserializes a real persisted fossil record (e.g.
    aurora_state/genealogy/links.json) back into a ConstraintLink. Pure
    parsing of an already-defined on-disk schema, not new genealogy physics.
    """
    from aurora_internal.constraint_genealogy import ConstraintLink

    stats = d.get("stats") or {}
    return ConstraintLink(
        id=d["id"],
        parents=list(d.get("parents") or []),
        depth=int(d.get("depth", 1) or 1),
        created_at_tick=int(d.get("created_at_tick", 0) or 0),
        count=int(stats.get("count", 0) or 0),
        mean_relief=dict(stats.get("mean_relief") or {}),
        mean_cost=dict(stats.get("mean_cost") or {}),
        mean_x_risk=float(stats.get("mean_x_risk", 0.0) or 0.0),
        stdev_relief=dict(stats.get("stdev_relief") or {}),
        dominant_relief_axis=d.get("dominant_relief_axis"),
        tags=list(d.get("tags") or []),
        topology_id=d.get("topology_id"),
        semantic_variant_id=d.get("semantic_variant_id"),
    )


def logger_from_links(links: Dict[str, Any]) -> Any:
    """
    Build a minimal real ConstraintGenealogyLogger whose `.links` registry is
    the supplied mapping, so walk_link_sequence() (the existing full-DAG
    walker) can be called unmodified. Runs in a throwaway temp directory —
    never touches real aurora_state/.
    """
    from aurora_internal.constraint_genealogy import ConstraintGenealogyLogger

    tmp_dir = tempfile.mkdtemp(prefix="aurora_genealogy_env_")
    logger = ConstraintGenealogyLogger(run_id="genealogy_environment_shadow", output_dir=tmp_dir)
    logger.links = dict(links)
    return logger


# ---------------------------------------------------------------------------
# III. Real edges — derived from ConstraintLink.parents, never from
#      neighboring entries in walk_link_sequence()'s flat traversal list
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GenealogyEdge:
    """One real genealogical transition, in the direction ancestor -> child."""
    parent_link_id: Optional[str]   # None for a "self" edge (see edge_type)
    child_link_id: str
    parent_axis: str
    child_axis: str
    atom: str                       # f"NC:{parent_axis}>{child_axis}"
    edge_type: str                  # "parent_child" | "self"


def _derive_edges(logger: Any, sequence: List[Dict[str, Any]]) -> List[GenealogyEdge]:
    """
    Build the real transition list for a walked genealogy from
    ConstraintLink.parents directly — NOT from adjacency in `sequence`.

    For each walked node, every parent id that is itself a ConstraintLink
    already present in `logger.links` (i.e. it was actually walked into by
    walk_link_sequence, per that method's own "Ability ID or unknown --
    leaf, not a Link" rule) becomes one real parent_child edge. A node whose
    every parent is a non-Link leaf (a bare ability id, or a root-level
    genealogy atom like "NC:N>N" — both invisible to walk_link_sequence)
    contributes a single "self" edge instead of being paired with an
    unrelated neighbor, so the axis it expresses is never silently dropped
    and never silently fabricated into a false transition either.
    """
    node_ids = {node["link_id"] for node in sequence}
    axis_by_id = {node["link_id"]: node["axis"] for node in sequence}
    edges: List[GenealogyEdge] = []

    for node in sequence:
        link = logger.links.get(node["link_id"])
        if link is None:
            continue
        real_parent_edges = 0
        for parent_id in (link.parents or []):
            parent_id = str(parent_id)
            if parent_id in logger.links and parent_id in node_ids:
                parent_axis = axis_by_id[parent_id]
                child_axis = node["axis"]
                edges.append(GenealogyEdge(
                    parent_link_id=parent_id,
                    child_link_id=node["link_id"],
                    parent_axis=parent_axis,
                    child_axis=child_axis,
                    atom=f"NC:{parent_axis}>{child_axis}",
                    edge_type="parent_child",
                ))
                real_parent_edges += 1
        if real_parent_edges == 0:
            axis = node["axis"]
            edges.append(GenealogyEdge(
                parent_link_id=None,
                child_link_id=node["link_id"],
                parent_axis=axis,
                child_axis=axis,
                atom=f"NC:{axis}>{axis}",
                edge_type="self",
            ))
    return edges


# ---------------------------------------------------------------------------
# IV. The derived environment signature
# ---------------------------------------------------------------------------

@dataclass
class EnvironmentSignature:
    """
    The native representational environment produced by a genealogy G.

    dimension_distribution: normalized weight (sums to 1.0) over the real
        POLARITY/MAGNITUDE/OPERATOR/COST/DIFFERENCE dimensions, derived from
        the actual InteractionSlot.dim_a/dim_b of every REAL genealogical
        edge in G (see edge_provenance), weighted by that slot's own
        depth_score.
    axis_distribution: normalized weight over X/T/N/B/A, from the relief
        magnitude actually recorded on each ConstraintLink in G (node-level,
        from walk_link_sequence — unaffected by the edge-fidelity repair).
        Kept separate from dimension_distribution: axis identity and
        dimension configuration are not the same quantity and must not be
        merged.
    recursion_distribution: fraction of G's nodes at each of
        walk_link_sequence's existing 5 recursion buckets (0=SURFACE .. 4=CORE).
        Node-level; unaffected by the edge-fidelity repair.
    istate_distribution: fraction of G's nodes resolving to each of the 10
        existing AXIS_I_STATE-derived I-state keys. Node-level; unaffected
        by the edge-fidelity repair.
    edge_provenance: every real GenealogyEdge actually used, in traversal
        order, WITH multiplicity (repeated identical transitions are NOT
        collapsed here — that only happens inside closure_projection, see
        below). This is the non-lossy structural record.
    active_slots: InteractionSlot ids touched by edge_provenance, in the
        same order, one per edge (also with multiplicity).
    chained_root_slot: every edge atom joined with the canonical Unicode
        "×" separator aurora_closure_basis._resolve_slots_from_root_slot
        checks first and unconditionally (no atom-count ambiguity, unlike
        the ASCII "x" the phase-1 version used).
    closure_projection: the real ConstraintLineage returned by
        derive_lineage() when fed the full chained_root_slot. Because
        derive_lineage()'s _add() helper deduplicates by slot_id, this is a
        real, physics-grounded but SLOT-DEDUPLICATED reading — it cannot by
        itself certify multiplicity or branch topology. Use edge_provenance
        / structural_hash for that; use this for the existing closure-basis
        grades (leverage_grade, formation_cost, viable_band_alignment,
        energetic_footprint, ontological_status). Note also that
        derive_lineage() independently unions in slots from its own
        axis+requires resolution path (aurora_closure_basis.py:966)
        regardless of root_slot content, so active_slots here can legally
        contain MORE than just the atoms in edge_provenance — that broadening
        is pre-existing derive_lineage() behavior, not something this module
        adds, and is exactly why this field is named a "projection" rather
        than claimed as a faithful replay of edge_provenance.
    provenance: ConstraintLink ids in traversal order (oldest ancestor first).
    node_count: number of ConstraintLink nodes actually walked.
    insufficient_genealogy: True if the supplied link_id resolved to no
        walkable ConstraintLink nodes (e.g. a bare ability leaf, or unknown
        id) -- in which case every distribution above is empty and callers
        must not treat this as a valid signature.
    provenance_hash: sha1 over (active_slots, provenance) -- includes real
        link ids, so it is sensitive to WHICH specific fossils produced this
        genealogy, not just its shape. Two structurally-identical
        genealogies with different underlying link ids will differ here.
    structural_hash: sha1 over edge_provenance's (parent_axis, child_axis,
        edge_type) tuples ONLY, in traversal order — no link ids, no
        substrate name. Two genealogies with identical topology (same real
        edges, same order) hash identically here regardless of what
        anything is called or which specific fossils produced it; two
        genealogies that only *look* the same in a flat linear walk but
        have different real branching structure hash differently.
    """
    dimension_distribution: Dict[str, float] = field(default_factory=dict)
    axis_distribution: Dict[str, float] = field(default_factory=dict)
    recursion_distribution: Dict[str, float] = field(default_factory=dict)
    istate_distribution: Dict[str, float] = field(default_factory=dict)
    edge_provenance: List[Dict[str, Any]] = field(default_factory=list)
    active_slots: List[str] = field(default_factory=list)
    chained_root_slot: str = ""
    closure_projection: Optional[ConstraintLineage] = None
    provenance: List[str] = field(default_factory=list)
    node_count: int = 0
    insufficient_genealogy: bool = False
    provenance_hash: str = ""
    structural_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension_distribution": dict(self.dimension_distribution),
            "axis_distribution": dict(self.axis_distribution),
            "recursion_distribution": dict(self.recursion_distribution),
            "istate_distribution": dict(self.istate_distribution),
            "edge_provenance": [dict(e) for e in self.edge_provenance],
            "active_slots": list(self.active_slots),
            "chained_root_slot": self.chained_root_slot,
            "closure_projection": self.closure_projection.to_dict() if self.closure_projection is not None else None,
            "provenance": list(self.provenance),
            "node_count": self.node_count,
            "insufficient_genealogy": self.insufficient_genealogy,
            "provenance_hash": self.provenance_hash,
            "structural_hash": self.structural_hash,
        }


_EMPTY_SIGNATURE_KWARGS = dict(insufficient_genealogy=True)


def _normalize(counts: Dict[str, float]) -> Dict[str, float]:
    total = sum(counts.values())
    if total <= 0.0:
        return {k: 0.0 for k in counts}
    return {k: v / total for k, v in counts.items()}


def derive_environment_signature(logger: Any, link_id: str) -> EnvironmentSignature:
    """
    Derive the native representational environment for the genealogy rooted
    at `link_id`. Node-level distributions (axis/recursion/i-state) come
    from `logger.walk_link_sequence(link_id)` directly. Genealogical
    transitions (dimension_distribution, active_slots, chained_root_slot,
    closure_projection) come from the REAL ConstraintLink.parents edges
    among those walked nodes (`_derive_edges`), never from adjacency in the
    walked list.
    """
    sequence = logger.walk_link_sequence(link_id)
    if not sequence:
        return EnvironmentSignature(**_EMPTY_SIGNATURE_KWARGS)

    axis_counts: Dict[str, float] = {a: 0.0 for a in AXES}
    rec_counts: Dict[str, float] = {k: 0.0 for k in _REC_KEYS}
    istate_counts: Dict[str, float] = {k: 0.0 for k in _ISTATE_KEYS}

    for node in sequence:
        axis_counts[node["axis"]] = axis_counts.get(node["axis"], 0.0) + sum(
            abs(float(v)) for v in (node.get("mean_relief") or {}).values()
        )
        rec_counts[_REC_KEYS[node["recursion_level"]]] += 1.0
        istate_counts[node["i_state"]] = istate_counts.get(node["i_state"], 0.0) + 1.0

    edges = _derive_edges(logger, sequence)

    dim_counts: Dict[str, float] = {name: 0.0 for name in _ALL_DIM_NAMES}
    active_slots: List[str] = []
    atoms_in_order: List[str] = []
    edge_provenance: List[Dict[str, Any]] = []
    structural_parts: List[str] = []

    for edge in edges:
        atom = edge.atom
        if not genealogy_atom_is_valid(atom):
            continue
        pair = genealogy_atom_to_channel_pair(atom)
        if pair is None:
            continue
        nc_a, nc_b = pair
        slot = slot_for_pair(nc_a, nc_b)
        if slot is None:
            continue
        weight = slot.depth_score if slot.depth_score > 0 else 1.0
        # CONFIRMED FINDING (see docs/GENEALOGY_NATIVE_ENVIRONMENT_REPORT.md):
        # genealogy_atom_to_channel_pair() enforces "NC:C1>C2 = NC:C1:OPERATOR
        # x NC:C2:COST" for every one of the 25 genealogy atoms (Sunni's Cost
        # Law, aurora_closure_basis.py:419-439). Every InteractionSlot reached
        # through a genealogy-atom transition therefore ALWAYS has
        # dim_a=OPERATOR, dim_b=COST -- dimension_distribution below is
        # structurally 0.5/0.5 OPERATOR/COST (0 elsewhere) for ANY non-empty
        # ConstraintLink genealogy, not a property of this specific DAG (this
        # still holds true now that transitions are real edges rather than
        # traversal-adjacent pairs -- the atom vocabulary itself is the
        # ceiling, not how the atoms were chosen). The differentiating signal
        # between genealogies lives in WHICH channels (active_slots /
        # chained_root_slot / structural_hash) occupy those roles and in
        # axis_distribution/istate_distribution/closure_projection, not in
        # the abstract 5-dimension-name distribution. This is reported as-is
        # rather than patched with an invented mapping from relief-sign/cost/
        # stdev onto POLARITY/MAGNITUDE/DIFFERENCE, since aurora_closure_basis
        # assigns IDENTICAL shift_cost_coeff/inertia/flip_threshold/i_state
        # values to all 5 dimension-channels of a given constraint (verified:
        # _build_noncomp_channels(), aurora_closure_basis.py:371-395) -- no
        # existing physics currently differentiates those 3 dimensions at the
        # channel level, so any such mapping would be a new invented constant,
        # which this module is directed not to introduce.
        dim_counts[_DIM_NAME_BY_ENUM[slot.dim_a]] += weight
        dim_counts[_DIM_NAME_BY_ENUM[slot.dim_b]] += weight
        active_slots.append(slot.slot_id)
        atoms_in_order.append(atom)
        edge_provenance.append({
            "parent_link_id": edge.parent_link_id,
            "child_link_id": edge.child_link_id,
            "atom": atom,
            "edge_type": edge.edge_type,
            "slot_id": slot.slot_id,
        })
        structural_parts.append(f"{edge.parent_axis}>{edge.child_axis}:{edge.edge_type}")

    chained_root_slot = "×".join(atoms_in_order)
    dominant_axis = max(axis_counts, key=lambda a: axis_counts[a]) if any(axis_counts.values()) else sequence[-1]["axis"]
    requires = tuple(a for a in AXES if axis_counts.get(a, 0.0) > 0.0) or (dominant_axis,)

    closure_projection: Optional[ConstraintLineage]
    try:
        closure_projection = derive_lineage(dominant_axis, requires, chained_root_slot)
    except Exception:
        closure_projection = None

    provenance = [node["link_id"] for node in sequence]
    provenance_source = "|".join(active_slots) + "::" + "|".join(provenance)
    provenance_hash = hashlib.sha1(provenance_source.encode("utf-8")).hexdigest()[:16]
    structural_source = "|".join(structural_parts)
    structural_hash = hashlib.sha1(structural_source.encode("utf-8")).hexdigest()[:16]

    return EnvironmentSignature(
        dimension_distribution=_normalize(dim_counts),
        axis_distribution=_normalize(axis_counts),
        recursion_distribution=_normalize(rec_counts),
        istate_distribution=_normalize(istate_counts),
        edge_provenance=edge_provenance,
        active_slots=active_slots,
        chained_root_slot=chained_root_slot,
        closure_projection=closure_projection,
        provenance=provenance,
        node_count=len(sequence),
        insufficient_genealogy=False,
        provenance_hash=provenance_hash,
        structural_hash=structural_hash,
    )


# ---------------------------------------------------------------------------
# IV. Comparable projection into the existing 15D I-state+recursion space
# ---------------------------------------------------------------------------
# _CORE_CREST_PROFILES (aurora_internal/dual_strata/subsystem_waveforms.py)
# lives in a DIFFERENT space than dimension_distribution above: it is keyed
# by AXIS-derived I-states (X/T/N/B/A) plus recursion depth, not by
# POLARITY/MAGNITUDE/OPERATOR/COST/DIFFERENCE. Both istate_distribution and
# recursion_distribution on EnvironmentSignature are already in that
# comparable space (walk_link_sequence computed them directly), so this
# projection is a straight re-key, not a new derivation.

def project_to_crest_profile(signature: EnvironmentSignature) -> Dict[str, float]:
    if signature.insufficient_genealogy:
        return {}
    profile: Dict[str, float] = {}
    profile.update(signature.istate_distribution)
    profile.update(signature.recursion_distribution)
    return profile


def cosine_similarity(a: Dict[str, float], b: Dict[str, float]) -> float:
    keys = set(a.keys()) | set(b.keys())
    if not keys:
        return 0.0
    dot = sum(a.get(k, 0.0) * b.get(k, 0.0) for k in keys)
    norm_a = math.sqrt(sum(a.get(k, 0.0) ** 2 for k in keys))
    norm_b = math.sqrt(sum(b.get(k, 0.0) ** 2 for k in keys))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def compare_against_core_crests(signature: EnvironmentSignature) -> Dict[str, float]:
    """
    Shadow comparison: cosine similarity between this genealogy-derived
    environment (projected into the existing 15D I-state+recursion space)
    and each of the 8 authored _CORE_CREST_PROFILES. Read-only -- does not
    register, promote, or otherwise mutate any WARP/crest state.
    """
    from aurora_internal.dual_strata.subsystem_waveforms import _CORE_CREST_PROFILES

    derived = project_to_crest_profile(signature)
    if not derived:
        return {}
    return {
        name: cosine_similarity(derived, authored)
        for name, authored in _CORE_CREST_PROFILES.items()
    }

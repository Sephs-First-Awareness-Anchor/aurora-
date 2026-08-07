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
# III. The derived environment signature
# ---------------------------------------------------------------------------

@dataclass
class EnvironmentSignature:
    """
    The native representational environment produced by a genealogy G.

    dimension_distribution: normalized weight (sums to 1.0) over the real
        POLARITY/MAGNITUDE/OPERATOR/COST/DIFFERENCE dimensions, derived from
        the actual InteractionSlot.dim_a/dim_b of every genealogical
        transition in G, weighted by that slot's own depth_score.
    axis_distribution: normalized weight over X/T/N/B/A, from the relief
        magnitude actually recorded on each ConstraintLink in G. Kept
        separate from dimension_distribution per-directive (axis identity
        and dimension configuration are not the same quantity and must not
        be merged).
    recursion_distribution: fraction of G's nodes at each of
        walk_link_sequence's existing 5 recursion buckets (0=SURFACE .. 4=CORE).
    istate_distribution: fraction of G's nodes resolving to each of the 10
        existing AXIS_I_STATE-derived I-state keys (walk_link_sequence already
        computes this per node; this is a direct tally, not a new mapping).
    active_slots: InteractionSlot ids touched, IN TRAVERSAL ORDER. This is
        what preserves order-sensitivity: two genealogies with identical
        axis histograms but different recursive/parent topology will
        general produce different active_slots sequences and therefore
        different derived environments.
    chained_root_slot: every touched genealogy atom joined with the same
        "x" separator aurora_closure_basis._resolve_slots_from_root_slot
        already parses, in traversal order — NOT collapsed to 2 atoms.
    lineage: the real ConstraintLineage returned by derive_lineage() when fed
        the full chained_root_slot (existing physics, richer input).
    provenance: ConstraintLink ids in traversal order (oldest ancestor first).
    node_count: number of ConstraintLink nodes actually walked.
    insufficient_genealogy: True if the supplied link_id resolved to no
        walkable ConstraintLink nodes (e.g. a bare ability leaf, or unknown
        id) -- in which case every distribution above is empty and callers
        must not treat this as a valid signature.
    signature_hash: sha1 over (active_slots, provenance) -- identical for
        genealogies that are structurally identical regardless of what the
        underlying substrate happens to be named, since no name is ever
        read by this module.
    """
    dimension_distribution: Dict[str, float] = field(default_factory=dict)
    axis_distribution: Dict[str, float] = field(default_factory=dict)
    recursion_distribution: Dict[str, float] = field(default_factory=dict)
    istate_distribution: Dict[str, float] = field(default_factory=dict)
    active_slots: List[str] = field(default_factory=list)
    chained_root_slot: str = ""
    lineage: Optional[ConstraintLineage] = None
    provenance: List[str] = field(default_factory=list)
    node_count: int = 0
    insufficient_genealogy: bool = False
    signature_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension_distribution": dict(self.dimension_distribution),
            "axis_distribution": dict(self.axis_distribution),
            "recursion_distribution": dict(self.recursion_distribution),
            "istate_distribution": dict(self.istate_distribution),
            "active_slots": list(self.active_slots),
            "chained_root_slot": self.chained_root_slot,
            "lineage": self.lineage.to_dict() if self.lineage is not None else None,
            "provenance": list(self.provenance),
            "node_count": self.node_count,
            "insufficient_genealogy": self.insufficient_genealogy,
            "signature_hash": self.signature_hash,
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
    at `link_id`, using `logger.walk_link_sequence(link_id)` (the existing
    order-preserving full-DAG walker) as the sole source of ancestry.
    """
    sequence = logger.walk_link_sequence(link_id)
    if not sequence:
        return EnvironmentSignature(**_EMPTY_SIGNATURE_KWARGS)

    dim_counts: Dict[str, float] = {name: 0.0 for name in _ALL_DIM_NAMES}
    axis_counts: Dict[str, float] = {a: 0.0 for a in AXES}
    rec_counts: Dict[str, float] = {k: 0.0 for k in _REC_KEYS}
    istate_counts: Dict[str, float] = {k: 0.0 for k in _ISTATE_KEYS}
    active_slots: List[str] = []
    atoms_in_order: List[str] = []

    for node in sequence:
        axis_counts[node["axis"]] = axis_counts.get(node["axis"], 0.0) + sum(
            abs(float(v)) for v in (node.get("mean_relief") or {}).values()
        )
        rec_counts[_REC_KEYS[node["recursion_level"]]] += 1.0
        istate_counts[node["i_state"]] = istate_counts.get(node["i_state"], 0.0) + 1.0

    # Consecutive genealogical transitions, in traversal order. A single-node
    # genealogy still expresses itself through its own self-interaction slot.
    axis_sequence = [node["axis"] for node in sequence]
    pairs: List[Tuple[str, str]] = (
        list(zip(axis_sequence, axis_sequence[1:])) if len(axis_sequence) > 1
        else [(axis_sequence[0], axis_sequence[0])]
    )

    for (a, b) in pairs:
        atom = f"NC:{a}>{b}"
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
        # ConstraintLink genealogy, not a property of this specific DAG. The
        # differentiating signal between genealogies lives in WHICH channels
        # (active_slots / chained_root_slot) occupy those roles and in
        # axis_distribution/istate_distribution/lineage, not in the abstract
        # 5-dimension-name distribution. This is reported as-is rather than
        # patched with an invented mapping from relief-sign/cost/stdev onto
        # POLARITY/MAGNITUDE/DIFFERENCE, since aurora_closure_basis assigns
        # IDENTICAL shift_cost_coeff/inertia/flip_threshold/i_state values to
        # all 5 dimension-channels of a given constraint (verified:
        # _build_noncomp_channels(), aurora_closure_basis.py:371-395) -- no
        # existing physics currently differentiates those 3 dimensions at the
        # channel level, so any such mapping would be a new invented constant,
        # which this module is directed not to introduce.
        dim_counts[_DIM_NAME_BY_ENUM[slot.dim_a]] += weight
        dim_counts[_DIM_NAME_BY_ENUM[slot.dim_b]] += weight
        active_slots.append(slot.slot_id)
        atoms_in_order.append(atom)

    chained_root_slot = "x".join(atoms_in_order)
    dominant_axis = max(axis_counts, key=lambda a: axis_counts[a]) if any(axis_counts.values()) else sequence[-1]["axis"]
    requires = tuple(a for a in AXES if axis_counts.get(a, 0.0) > 0.0) or (dominant_axis,)

    lineage: Optional[ConstraintLineage]
    try:
        lineage = derive_lineage(dominant_axis, requires, chained_root_slot)
    except Exception:
        lineage = None

    provenance = [node["link_id"] for node in sequence]
    sig_source = "|".join(active_slots) + "::" + "|".join(provenance)
    signature_hash = hashlib.sha1(sig_source.encode("utf-8")).hexdigest()[:16]

    return EnvironmentSignature(
        dimension_distribution=_normalize(dim_counts),
        axis_distribution=_normalize(axis_counts),
        recursion_distribution=_normalize(rec_counts),
        istate_distribution=_normalize(istate_counts),
        active_slots=active_slots,
        chained_root_slot=chained_root_slot,
        lineage=lineage,
        provenance=provenance,
        node_count=len(sequence),
        insufficient_genealogy=False,
        signature_hash=signature_hash,
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

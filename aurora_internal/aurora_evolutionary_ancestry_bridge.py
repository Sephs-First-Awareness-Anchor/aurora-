#!/usr/bin/env python3
"""
aurora_internal/aurora_evolutionary_ancestry_bridge.py

AURORA BUILD 646 GENEALOGY-TO-EVOLUTION CLOSURE DIRECTIVE, Phase 2.

Bridges operational ancestry (UniversalFunctionLineage's real, source-derived
function-call/inheritance graph) into evolutionary parentage (CodeEvolutionChamber's
mutation proposals), without collapsing the distinct forms of ancestry into one
crude parent_id field (Requirement 2.1) and without inventing ancestry when
evidence is absent (Requirement 2.2).

This module is a pure, read-only query layer. It never mutates
UniversalFunctionLineage or CodeEvolutionChamber state, and it never decides
mutation acceptance/rejection -- that remains CodeEvolutionChamber.observe_mutation()'s
job, grounded in real evaluation evidence (unchanged by this module).

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Set


def _normalize_repo_relative(path: str, repo_root: str) -> str:
    """Match UniversalFunctionLineage's own file-key convention: forward-slash,
    repo-relative. Accepts absolute or already-relative input."""
    p = str(path or "").strip()
    if not p:
        return ""
    if os.path.isabs(p):
        try:
            p = os.path.relpath(p, repo_root)
        except ValueError:
            return ""
    return p.replace(os.sep, "/")


@dataclass
class AcquiredAncestry:
    """
    Multiple distinct forms of ancestry (Requirement 2.1), kept separate
    rather than flattened into one field. Any field may be empty -- absence
    is representable as unknown/root-originating (Requirement 2.2), never
    fabricated.
    """
    resolved_function_ids: List[str] = field(default_factory=list)
    operational_ancestors: List[str] = field(default_factory=list)
    constraint_signature: Dict[str, float] = field(default_factory=dict)
    traceable_roots: List[str] = field(default_factory=list)
    descendant_count: int = 0
    descendant_sample: List[str] = field(default_factory=list)
    previous_accepted_mutation_ids: List[str] = field(default_factory=list)
    previous_rejected_mutation_ids: List[str] = field(default_factory=list)
    ancestry_status: str = "unknown"  # "unknown" | "root_originating" | "resolved"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "resolved_function_ids": list(self.resolved_function_ids),
            "operational_ancestors": list(self.operational_ancestors),
            "constraint_signature": dict(self.constraint_signature),
            "traceable_roots": list(self.traceable_roots),
            "descendant_count": self.descendant_count,
            "descendant_sample": list(self.descendant_sample),
            "previous_accepted_mutation_ids": list(self.previous_accepted_mutation_ids),
            "previous_rejected_mutation_ids": list(self.previous_rejected_mutation_ids),
            "ancestry_status": self.ancestry_status,
        }


def functions_in_files(
    function_lineage: Any,
    target_files: Iterable[str],
    repo_root: str,
) -> List[str]:
    """
    Resolve target file paths to the function_ids UniversalFunctionLineage
    already knows live in them. Read-only; no ancestry is invented if a
    target file has no matching entries (e.g. a non-.py asset, or a file
    UniversalFunctionLineage's manifest has not yet observed -- that
    absence is legitimate evidence, not an error).
    """
    if function_lineage is None or not hasattr(function_lineage, "all_functions"):
        return []
    rel_targets = {_normalize_repo_relative(t, repo_root) for t in target_files}
    rel_targets.discard("")
    if not rel_targets:
        return []
    out: List[str] = []
    for fid, rec in function_lineage.all_functions().items():
        if str(rec.get("file", "") or "") in rel_targets:
            out.append(fid)
    return sorted(out)


def acquire_ancestry_for_target(
    *,
    function_lineage: Optional[Any],
    mutation_lineage: Optional[Dict[str, Dict[str, Any]]],
    target_files: Iterable[str],
    repo_root: str,
    descendant_sample_limit: int = 25,
) -> AcquiredAncestry:
    """
    Derive available evidence for a mutation targeting target_files
    (Requirement 2.2): operational ancestors, constraint signature,
    descendant fan-out, and previous accepted/rejected evolutionary
    attempts against overlapping targets.

    Does not decide what to do with this evidence -- that decision (how
    much weight to give it, whether to gate/block a mutation on it) is
    left to the caller, per this directive's Repair Authority boundary
    against deciding a new mutation pedagogy.
    """
    result = AcquiredAncestry()

    function_ids = functions_in_files(function_lineage, target_files, repo_root)
    result.resolved_function_ids = function_ids

    if function_ids and function_lineage is not None:
        ancestors: Set[str] = set()
        roots: Set[str] = set()
        signature_sum: Dict[str, float] = {}
        signature_n = 0
        descendants: Set[str] = set()
        for fid in function_ids:
            rec = function_lineage.lineage_for(fid)
            for parent_rec in function_lineage.parents_of(fid):
                pid = str(parent_rec.get("function_id", "") or "")
                if pid and pid not in function_ids:
                    ancestors.add(pid)
            roots.update(str(a) for a in (rec.get("traceable_roots") or []))
            weights = dict(rec.get("root_weights", {}) or {})
            if weights:
                signature_n += 1
                for axis, w in weights.items():
                    signature_sum[axis] = signature_sum.get(axis, 0.0) + float(w)
            for descendant in function_lineage.descendants_of(fid, limit=200):
                if descendant not in function_ids:
                    descendants.add(descendant)

        result.operational_ancestors = sorted(ancestors)
        result.traceable_roots = sorted(roots)
        if signature_n:
            result.constraint_signature = {
                axis: round(total / signature_n, 6) for axis, total in signature_sum.items()
            }
        result.descendant_count = len(descendants)
        result.descendant_sample = sorted(descendants)[:descendant_sample_limit]
        result.ancestry_status = "resolved" if (ancestors or roots) else "root_originating"
    elif function_ids:
        # function_lineage went away between resolution and query (should not
        # happen given the guard above, but keep the state representable).
        result.ancestry_status = "unknown"
    else:
        result.ancestry_status = "unknown"

    if mutation_lineage:
        rel_targets = {_normalize_repo_relative(t, repo_root) for t in target_files}
        rel_targets.discard("")
        accepted: List[str] = []
        rejected: List[str] = []
        for mutation_id, payload in mutation_lineage.items():
            payload_targets = {
                _normalize_repo_relative(t, repo_root)
                for t in (payload.get("target_files", []) or [])
            }
            if not (payload_targets & rel_targets):
                continue
            if bool(payload.get("accepted", False)):
                accepted.append(str(mutation_id))
            else:
                rejected.append(str(mutation_id))
        result.previous_accepted_mutation_ids = sorted(accepted)
        result.previous_rejected_mutation_ids = sorted(rejected)

    return result


def lineage_scoped_pressure(
    *,
    function_lineage: Optional[Any],
    mutation_lineage: Optional[Dict[str, Dict[str, Any]]],
    target_files: Iterable[str],
    repo_root: str,
    descendant_limit: int = 500,
) -> Dict[str, Any]:
    """
    Phase 4, Requirement 4.1: repeated failure INVOLVING DESCENDANTS of a
    target should increase pressure on that target's lineage -- not on
    unrelated systems, and not as a single global counter. This widens
    acquire_ancestry_for_target's exact-file matching (which only sees
    mutation attempts against the target's own file) to also count
    attempts against anything the target's operational descendants
    resolve to, using UniversalFunctionLineage's own descendants_of().

    Returns a decomposable evidence dict (Phase 9: no opaque magic
    number) -- counts and the mutation_ids behind them, never a single
    collapsed "pressure score" this module would be inventing a doctrine
    around. What a caller DOES with these counts (whether/how much to
    weight target selection) is left to the caller, per the directive's
    Repair Authority boundary against silently choosing a new mutation
    pedagogy.

    Deliberately scoped to the code-evolution lineage only: it aggregates
    repeated CodeEvolutionChamber mutation attempts across a target's
    resolved operational descendants. It does NOT attempt to map
    conversational/dream fail-stream dimensions (RichFailStream's
    "dimension"/"identity" keys) onto function_ids -- no such attribution
    exists anywhere in the current architecture, and inventing one would
    decide a new cross-domain developmental-pressure doctrine rather than
    apply an existing, unambiguous one.
    """
    target_ids = functions_in_files(function_lineage, target_files, repo_root)
    scope: Set[str] = set(target_ids)
    if function_lineage is not None:
        for fid in target_ids:
            scope.update(function_lineage.descendants_of(fid, limit=descendant_limit))

    rejected: List[str] = []
    accepted: List[str] = []
    if mutation_lineage:
        for mutation_id, payload in mutation_lineage.items():
            payload_targets = functions_in_files(
                function_lineage, payload.get("target_files", []) or [], repo_root,
            )
            if not (set(payload_targets) & scope):
                continue
            if bool(payload.get("accepted", False)):
                accepted.append(str(mutation_id))
            else:
                rejected.append(str(mutation_id))

    return {
        "target_function_ids": target_ids,
        "descendant_scope_count": len(scope) - len(target_ids),
        "rejected_count_in_scope": len(sorted(rejected)),
        "accepted_count_in_scope": len(sorted(accepted)),
        "rejected_mutation_ids_in_scope": sorted(rejected),
        "accepted_mutation_ids_in_scope": sorted(accepted),
    }


def auto_parent_ids(
    ancestry: AcquiredAncestry,
    explicit_parent_ids: Iterable[str],
) -> List[str]:
    """
    Requirement 2.3: explicit parent_ids remain valid and are never
    overwritten -- when the caller supplies none, and real prior ACCEPTED
    mutation history exists against the same target, use that as the
    automatic parentage (preserving CodeEvolutionChamber's existing
    generation-counting semantics, which are defined over the ACCEPTED
    mutation lineage only -- feeding it a rejected mutation's ID would
    misrepresent what generation this proposal actually continues from).
    Rejected-attempt evidence is preserved separately (see
    AcquiredAncestry.previous_rejected_mutation_ids) rather than folded
    into parent_ids.
    """
    explicit = sorted({str(p).strip() for p in (explicit_parent_ids or []) if str(p).strip()})
    if explicit:
        return explicit
    return list(ancestry.previous_accepted_mutation_ids)

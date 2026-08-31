#!/usr/bin/env python3
"""
aurora_representational_canary.py

Cross-system canary for the SYSTEM-WIDE REPRESENTATIONAL CONSERVATION,
PROPAGATION, AND EMERGENCE REPAIR DIRECTIVE.

Two experiences, identical at the lower-rank (axis-only, X/T/N/B/A) level,
that differ ONLY in the confirmed independent Candidate-A coordinate
(sub_law_c / match.constraint):

    EXPERIENCE_A = "I need to protect my boundaries here"   -> constraint X
    EXPERIENCE_B = "existence itself feels uncertain right now" -> constraint B

(Both classify to dimension=OPERATOR, so the ONLY confirmed-independent
degree of freedom that differs between them is the constraint coordinate.)

This module traces both experiences through every real, already-existing
boundary this investigation found connected to that coordinate, and
records PRESERVED / LOST / UNREACHABLE / PINNED / SUMMARY_ONLY at each one,
per the Representational Conservation Contract in
docs/AURORA_SYSTEM_WIDE_REPRESENTATIONAL_INTEGRITY_REPORT.md. It never
invents a boundary that doesn't exist in the real code, and it never
writes to any Aurora production state file.

Run with: python3 aurora_representational_canary.py

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

EXPERIENCE_A = "I need to protect my boundaries here"
EXPERIENCE_B = "existence itself feels uncertain right now"

# Absolute, module-relative path -- immune to any earlier test in a full
# suite run leaving the process working directory changed (the same
# pattern already used by aurora_rank6_shadow_analysis.MANIFOLD_DIR_DEFAULT).
MANIFOLD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aurora_manifold_directory")


@dataclass
class BoundaryRecord:
    boundary: str
    classification: str  # preserved | transformed | pinned | summary_only | unreachable | lost
    detail: str
    value_a: Any = None
    value_b: Any = None
    distinguishable: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "boundary": self.boundary,
            "classification": self.classification,
            "detail": self.detail,
            "value_a": self.value_a,
            "value_b": self.value_b,
            "distinguishable": self.distinguishable,
        }


def run_canary(state_dir: Optional[str] = None) -> List[BoundaryRecord]:
    """Runs the full trace and returns an ordered list of BoundaryRecords.
    Uses an ephemeral state_dir (tempdir by default) so nothing is written
    to real aurora_state/."""
    from aurora_reflexive_interpreter import ReflexiveInterpreter, ManifoldFieldMap
    from aurora_manifold_directory_reader import ManifoldDirectory
    from aurora_understanding_sediment import slot_key
    from aurora_constraint_manifold_router import SlotCoord

    own_tempdir = state_dir is None
    if own_tempdir:
        state_dir = tempfile.mkdtemp(prefix="aurora_canary_")

    records: List[BoundaryRecord] = []
    directory = ManifoldDirectory(MANIFOLD_DIR)
    ri = ReflexiveInterpreter(directory=directory, state_dir=state_dir)

    state_a = ri.interpret(EXPERIENCE_A)
    state_b = ri.interpret(EXPERIENCE_B)

    # ── Boundary 1: SemanticMatcher classification ──────────────────────
    records.append(BoundaryRecord(
        "1_semantic_matcher_classification",
        "preserved",
        "SemanticMatcher.match() independently classifies constraint from "
        "each utterance's frame/stance/topic signals.",
        state_a.constraint, state_b.constraint,
        state_a.constraint != state_b.constraint,
    ))

    # ── Boundary 2: ManifoldFieldMap / manifold-slot physics ────────────
    with directory.open(state_a.nc_name) as m_a:
        fmap_a = ManifoldFieldMap(m_a)
        weight_a, region_a = fmap_a.accountability_at(state_a.constraint, state_a.dimension, state_a.constraint, "OPERATOR")
    with directory.open(state_b.nc_name) as m_b:
        fmap_b = ManifoldFieldMap(m_b)
        weight_b, region_b = fmap_b.accountability_at(state_b.constraint, state_b.dimension, state_b.constraint, "OPERATOR")
    records.append(BoundaryRecord(
        "2_manifold_field_map_accountability_weight",
        "preserved",
        "ManifoldFieldMap.accountability_at() reads the real per-slot "
        "accountability_weight for each experience's own (constraint, dimension) "
        "row -- confirmed to differ by constraint (rank-6 audit, Phase C).",
        weight_a, weight_b,
        weight_a != weight_b,
    ))

    # ── Boundary 3: live SlotCoord construction (ReflexiveInterpreter.interpret) ──
    # Reconstructed via the SAME mechanism interpret() itself now uses --
    # RepresentationalRef(nc_law_c=idx_e.nc_law_c, nc_dim=idx_e.nc_dim,
    # nc_target=idx_e.nc_target).as_pinned_column() -- not a hand-rolled
    # copy, so this boundary tracks interpret()'s real behavior rather than
    # a frozen snapshot of what it used to do.
    from aurora_representational_address import RepresentationalRef, slotcoord_from_ref
    idx_e_a = directory.get_index_entry(state_a.nc_name)
    idx_e_b = directory.get_index_entry(state_b.nc_name)
    coord_a = slotcoord_from_ref(
        RepresentationalRef(nc_law_c=idx_e_a.nc_law_c, nc_dim=idx_e_a.nc_dim,
                             nc_target=idx_e_a.nc_target).as_pinned_column()
    )
    coord_b = slotcoord_from_ref(
        RepresentationalRef(nc_law_c=idx_e_b.nc_law_c, nc_dim=idx_e_b.nc_dim,
                             nc_target=idx_e_b.nc_target).as_pinned_column()
    )
    records.append(BoundaryRecord(
        "3_live_slotcoord_construction",
        "preserved",
        "aurora_reflexive_interpreter.py's interpret() now derives the row "
        "(nc_law_c/nc_dim/target) from the manifold directory's own "
        "IndexEntry for the matched NC -- genuinely independent of "
        "SemanticMatcher's live classification, not a copy of it. The "
        "column (law_c/law_d) still has no independent evidence anywhere "
        "reachable at that call site (confirmed: IndexEntry.dense_top3's "
        "cluster_pair aggregation discards which col_law_c contributed), so "
        "it is pinned via the doctrine's named as_pinned_column() escape "
        "hatch rather than a disguised copy. Both EXPERIENCE_A/B happen to "
        "land on diagonal NCs (nc_law_c == nc_target), so this specific "
        "pair's row values don't visibly diverge from the old pinned "
        "values here -- the mechanism change is real and independently "
        "verified against a non-diagonal NC in "
        "tests/test_reflexive_interpreter_slotcoord_derivation.py.",
        coord_a.slot_id, coord_b.slot_id,
        coord_a != coord_b,
    ))

    # ── Boundary 4: WARP ──────────────────────────────────────────────
    records.append(BoundaryRecord(
        "4_warp",
        "unreachable",
        "No live WARP call site (aurora_warp_protocol.py) receives a "
        "ManifoldSlot, SlotCoord, or the (constraint, dimension) pair at all -- "
        "every real call site passes a flat Dict[str, float] of axis/I-state "
        "scalars. The distinction cannot reach WARP because WARP's own input "
        "contract has no field for it, not because of a bug at a specific line.",
        None, None, None,
    ))

    # ── Boundary 5: genealogy / evolution chamber / RCEC ────────────────
    records.append(BoundaryRecord(
        "5_genealogy_evolution_rcec",
        "unreachable",
        "Traced every ConstraintGenealogyLogger.observe() call site, "
        "EvolutionaryChamber.tick(), and every RCEC entry point -- none "
        "receives any value computed by ReflexiveInterpreter.interpret(), "
        "ManifoldFieldMap, or UnderstandingState. aurora.py imports and "
        "boots both sides, but no variable flows between them. This is "
        "co-occurrence, not data flow -- a confirmed architectural gap, "
        "not a narrow contract defect (wiring it would require designing a "
        "new integration decision, out of this pass's Repair Authority).",
        None, None, None,
    ))

    # ── Boundary 6: memory -- UnderstandingSedimentOverlay + worth ledger ──
    key_a = state_a.nc_name or f"{state_a.constraint}:{state_a.dimension}"
    key_b = state_b.nc_name or f"{state_b.constraint}:{state_b.dimension}"
    slot_a = slot_key(state_a.constraint, state_a.dimension)
    slot_b = slot_key(state_b.constraint, state_b.dimension)
    ri2 = ReflexiveInterpreter(directory=directory, state_dir=state_dir)  # fresh instance, simulates new session
    delta_a = ri2._overlay.delta(key_a, slot_a) if ri2._overlay else None
    delta_b = ri2._overlay.delta(key_b, slot_b) if ri2._overlay else None
    records.append(BoundaryRecord(
        "6_memory_understanding_sediment_overlay",
        "preserved",
        "UnderstandingSedimentOverlay.slot_key() encodes both constraint and "
        "dimension verbatim; a fresh ReflexiveInterpreter instance "
        "(simulating a new session) retrieves distinct deltas for each "
        "experience's own key.",
        {"key": key_a, "slot": slot_a, "delta": delta_a},
        {"key": key_b, "slot": slot_b, "delta": delta_b},
        key_a != key_b,
    ))
    records.append(BoundaryRecord(
        "6b_memory_older_sedimemory_system",
        "unreachable",
        "ReflexiveInterpreter never calls SediMemory's write API "
        "(ingest_event/ingest_envelope) with match.constraint/match.dimension -- "
        "it only reads from SediMemory (recall_confidence_boost) and only "
        "writes to the newer UnderstandingSedimentOverlay. The older memory "
        "system never receives this specific representation from cognition "
        "at all.",
        None, None, None,
    ))
    records.append(BoundaryRecord(
        "6c_memory_dream_episodic_system",
        "unreachable",
        "Dream/DREAMOP episode records (aurora_internal/aurora_dream_"
        "genealogy_bridge.py) carry only 5-axis (X/T/N/B/A) pressure "
        "vectors and rubric-dimension strings -- structurally no field "
        "exists for a (constraint, NonCompDimension) pair. Architectural "
        "limit, not a bug: this schema predates the manifold's richer "
        "per-slot vocabulary.",
        None, None, None,
    ))

    # ── Boundary 7: cognition -- worth_score / field_region ─────────────
    records.append(BoundaryRecord(
        "7_cognition_worth_score",
        "preserved",
        "UnderstandingState.worth_score differs between the two experiences, "
        "driven by the different accountability_weight read in Boundary 2.",
        state_a.worth_score, state_b.worth_score,
        state_a.worth_score != state_b.worth_score,
    ))

    # ── Boundary 8: communication -- behavior actuation ─────────────────
    import aurora
    summary_a = {"constraint": state_a.constraint, "dimension": state_a.dimension,
                 "expression": EXPERIENCE_A, "is_understood": state_a.is_understood,
                 "field_region": state_a.field_region, "polarity_coherent": state_a.polarity_coherent,
                 "remedy": "", "anchor": ""}
    summary_b = {"constraint": state_b.constraint, "dimension": state_b.dimension,
                 "expression": EXPERIENCE_B, "is_understood": state_b.is_understood,
                 "field_region": state_b.field_region, "polarity_coherent": state_b.polarity_coherent,
                 "remedy": "", "anchor": ""}
    actuation_a = aurora._derive_noncomp_behavior_actuation(summary_a)
    actuation_b = aurora._derive_noncomp_behavior_actuation(summary_b)
    records.append(BoundaryRecord(
        "8_communication_behavior_actuation",
        "preserved",
        "_derive_noncomp_behavior_actuation() keys _NONCOMP_CONSTRAINT_"
        "RUNTIME_EFFECTS directly by constraint (X and N both map to the "
        "empty effect set in the current table; B, T, A each have distinct "
        "real effects) -- confirmed live-wired into aurora.py's response "
        "composition path (Site B, aurora.py ~12805), which directly edits "
        "state.response_content/response_tone/response_confidence.",
        actuation_a["effects"], actuation_b["effects"],
        actuation_a["effects"] != actuation_b["effects"],
    ))

    if own_tempdir:
        import shutil
        shutil.rmtree(state_dir, ignore_errors=True)

    return records


def print_report(records: List[BoundaryRecord]) -> None:
    for r in records:
        mark = "?" if r.distinguishable is None else ("SURVIVES" if r.distinguishable else "COLLAPSES")
        print(f"[{r.classification:>12}] {r.boundary:<45} {mark}")
        print(f"    {r.detail}")
        if r.value_a is not None or r.value_b is not None:
            print(f"    A={r.value_a!r}  B={r.value_b!r}")


if __name__ == "__main__":
    recs = run_canary()
    print_report(recs)
    print()
    print(json.dumps([r.to_dict() for r in recs], indent=2, default=str))

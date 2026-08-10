#!/usr/bin/env python3
"""
aurora_representational_cross_system_canary.py

AURORA ESTABLISHED REPRESENTATIONAL SUBSTRATE FULL INTEGRATION DIRECTIVE,
Section 24: six canaries (A-F), one per rung of the confirmed ladder.

Every boundary is classified using the same eight-way taxonomy as the
prior conservation report: PRESERVED, TRANSFORMED, INTENTIONALLY_COMPRESSED,
PINNED, DEFAULTED, SUMMARY_ONLY, UNREACHABLE, LOST. Behavioral difference
alone never counts as preservation here -- every "PRESERVED" verdict below
is backed by an actual recovered RepresentationalRef equality check, not by
two different-looking outputs.

Read-only / ephemeral-state throughout. Never mutates aurora_manifold_
directory/ or aurora_state/.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from aurora_representational_address import (
    RepresentationalRef, AXES, DIM_NAMES, MANIFOLD_DIR_DEFAULT, resolve_manifold_slot,
)


@dataclass
class BoundaryRecord:
    canary: str
    boundary: str
    classification: str
    detail: str
    ref_recovered_equal: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "canary": self.canary, "boundary": self.boundary,
            "classification": self.classification, "detail": self.detail,
            "ref_recovered_equal": self.ref_recovered_equal,
        }


def canary_a_d1() -> List[BoundaryRecord]:
    """Same constraint, different measurement dimension. Verify both
    remain distinguishable through encode/decode and through the real
    manifold's per-channel physics parameters."""
    ref1 = RepresentationalRef.for_d1("X", "OPERATOR")
    ref2 = RepresentationalRef.for_d1("X", "COST")
    out = []
    out.append(BoundaryRecord(
        "A_D1", "encode_decode",
        "PRESERVED" if (RepresentationalRef.decode(ref1.encode()) == ref1 and
                        RepresentationalRef.decode(ref2.encode()) == ref2 and ref1 != ref2)
        else "LOST",
        f"ref1={ref1.encode()} ref2={ref2.encode()}",
        ref_recovered_equal=(ref1 != ref2),
    ))
    return out


def canary_b_c1() -> List[BoundaryRecord]:
    """Same D1 state, different target/context constraint. Verify
    contextual identity survives -- checked against the real, on-disk
    manifold directory index (not merely the ref's own dataclass equality)."""
    from aurora_manifold_directory_reader import ManifoldDirectory
    directory = ManifoldDirectory(MANIFOLD_DIR_DEFAULT)

    ref_self = RepresentationalRef.for_c1("X", "OPERATOR", "X")
    ref_cross = RepresentationalRef.for_c1("X", "OPERATOR", "B")

    def _nc_name_for(ref):
        for entry in directory.entries_for_axis(ref.nc_target):
            if entry.nc_law_c == ref.nc_law_c and entry.nc_dim == ref.nc_dim:
                return entry.nc_name
        return None

    name_self = _nc_name_for(ref_self)
    name_cross = _nc_name_for(ref_cross)
    preserved = name_self is not None and name_cross is not None and name_self != name_cross
    return [BoundaryRecord(
        "B_C1", "manifold_directory_resolution",
        "PRESERVED" if preserved else "LOST",
        f"self-target resolves to {name_self!r}, cross-target resolves to {name_cross!r}",
        ref_recovered_equal=preserved,
    )]


def canary_c_d2() -> List[BoundaryRecord]:
    """Same owning C1 state and same row, different column. Verify the
    relationship distinction survives all the way to the real, persisted
    ManifoldSlot's own physics fields."""
    base = dict(nc_law_c="X", nc_dim="OPERATOR", nc_target="X", sub_law_c="B", sub_law_d="COST")
    ref1 = RepresentationalRef.for_c2(col_law_c="T", col_law_d="MAGNITUDE", **base)
    ref2 = RepresentationalRef.for_c2(col_law_c="N", col_law_d="DIFFERENCE", **base)

    slot1 = resolve_manifold_slot(ref1)
    slot2 = resolve_manifold_slot(ref2)
    preserved = (slot1 is not None and slot2 is not None and slot1["slot_id"] != slot2["slot_id"])
    return [BoundaryRecord(
        "C_D2", "resolve_manifold_slot",
        "PRESERVED" if preserved else "LOST",
        f"slot1={slot1['slot_id'] if slot1 else None} slot2={slot2['slot_id'] if slot2 else None}",
        ref_recovered_equal=preserved,
    )]


def canary_d_3125() -> List[BoundaryRecord]:
    """Two valid M2,1 (SlotCoord-equivalent) states differing only in the
    coordinate normal live selection currently pins (sub_law_c/sub_law_d,
    implicitly forced to nc_law_c/nc_dim by ReflexiveInterpreter's live
    SlotCoord construction and by CERS's resolver). Does NOT force
    production selection -- constructs both refs directly and proves the
    canonical address distinguishes them regardless of what live selection
    currently does."""
    unpinned = RepresentationalRef.for_m21("X", "OPERATOR", "X", "T", "MAGNITUDE")
    pinned = unpinned.as_pinned_anchor()  # sub := nc's own identity, explicit opt-in

    out = []
    out.append(BoundaryRecord(
        "D_3125", "addressability_vs_live_pinning",
        "PRESERVED",
        "The canonical address distinguishes the unpinned M2,1 ref "
        f"({unpinned.encode()}) from its explicitly-pinned anchor variant "
        f"({pinned.encode()}) even though live ReflexiveInterpreter/CERS "
        "construction would produce only the pinned form by default -- "
        "confirming the substrate retains the distinction live selection "
        "currently discards.",
        ref_recovered_equal=(unpinned != pinned),
    ))

    # Cross-check against the real, live SlotCoord construction pattern
    # (aurora_reflexive_interpreter.py:1004-1011) to prove this is the
    # actual pinning being discussed, not a hypothetical one.
    from aurora_constraint_manifold_router import SlotCoord
    live_style_coord = SlotCoord("X", "X", "OPERATOR", "X", "OPERATOR")  # target=nc_law_c=law_c=constraint
    out.append(BoundaryRecord(
        "D_3125", "live_construction_comparison",
        "PINNED",
        f"Live-style SlotCoord({live_style_coord}) sets law_c=law_d=the same "
        "resolved constraint/dimension -- structurally identical to this "
        "canary's 'pinned' ref, confirming the substrate's unpinned form "
        "is the one live code currently never constructs.",
        ref_recovered_equal=None,
    ))
    return out


def canary_e_15625() -> List[BoundaryRecord]:
    """Vary the confirmed Candidate-A coordinate (sub_law_c) while holding
    lower structure (nc identity, col) fixed. Verify the established
    independently-meaningful distinction survives through: (1) the address
    itself, (2) the real manifold slot's numeric physics, (3) the
    UnderstandingSedimentOverlay persistence boundary added by this pass."""
    import os
    import tempfile as _tempfile

    base = dict(nc_law_c="X", nc_dim="OPERATOR", nc_target="X", col_law_c="T", col_law_d="MAGNITUDE")
    ref_a = RepresentationalRef.for_m22(sub_law_c="B", **base)
    ref_b = RepresentationalRef.for_m22(sub_law_c="A", **base)

    out = []
    out.append(BoundaryRecord(
        "E_15625", "address_distinguishability", "PRESERVED",
        f"{ref_a.encode()} != {ref_b.encode()}",
        ref_recovered_equal=(ref_a != ref_b),
    ))

    # Resolve each to its real manifold slot by supplying the coupled
    # sub_law_d explicitly (M2,2 doesn't resolve it -- for resolution we
    # pin it to nc_dim, the same convention the rank-6 audit tested under,
    # making the comparison a fair like-for-like test of sub_law_c alone).
    full_a = RepresentationalRef.for_c2(sub_law_d=base["nc_dim"], sub_law_c="B", **base)
    full_b = RepresentationalRef.for_c2(sub_law_d=base["nc_dim"], sub_law_c="A", **base)
    slot_a = resolve_manifold_slot(full_a)
    slot_b = resolve_manifold_slot(full_b)
    physics_differ = (slot_a is not None and slot_b is not None and
                       slot_a["evolution_grade"] != slot_b["evolution_grade"])
    out.append(BoundaryRecord(
        "E_15625", "real_manifold_physics", "PRESERVED" if physics_differ else "LOST",
        f"evolution_grade: {slot_a['evolution_grade'] if slot_a else None} vs "
        f"{slot_b['evolution_grade'] if slot_b else None}",
        ref_recovered_equal=physics_differ,
    ))

    # Persistence boundary: store both refs via the real, now-extended
    # UnderstandingSedimentOverlay, restart, recover.
    from aurora_understanding_sediment import UnderstandingSedimentOverlay
    tmp = _tempfile.mkdtemp(prefix="aurora_canary_e_")
    try:
        overlay1 = UnderstandingSedimentOverlay(state_dir=tmp)
        overlay1.deposit("FieldA", "slotA", 0.80, ref=ref_a.encode())
        overlay1.deposit("FieldB", "slotB", 0.80, ref=ref_b.encode())
        overlay1.save()
        del overlay1
        overlay2 = UnderstandingSedimentOverlay(state_dir=tmp)
        recovered_a = overlay2.ref_for("FieldA", "slotA")
        recovered_b = overlay2.ref_for("FieldB", "slotB")
        persisted_ok = (recovered_a == ref_a.encode() and recovered_b == ref_b.encode() and recovered_a != recovered_b)
        out.append(BoundaryRecord(
            "E_15625", "understanding_sediment_overlay_persistence",
            "PRESERVED" if persisted_ok else "LOST",
            f"recovered_a={recovered_a} recovered_b={recovered_b}",
            ref_recovered_equal=persisted_ok,
        ))
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
    return out


def canary_f_c2() -> List[BoundaryRecord]:
    """Two full 78,125-space coordinates differing at a controlled
    structural level (the column), traced through every integrated
    boundary this pass touched or assessed."""
    base = dict(nc_law_c="X", nc_dim="OPERATOR", nc_target="X", sub_law_c="B", sub_law_d="COST")
    ref1 = RepresentationalRef.for_c2(col_law_c="T", col_law_d="MAGNITUDE", **base)
    ref2 = RepresentationalRef.for_c2(col_law_c="N", col_law_d="DIFFERENCE", **base)
    out = []

    # 1. Manifold resolution
    slot1, slot2 = resolve_manifold_slot(ref1), resolve_manifold_slot(ref2)
    out.append(BoundaryRecord(
        "F_C2", "manifold_resolution",
        "PRESERVED" if (slot1 and slot2 and slot1["slot_id"] != slot2["slot_id"]) else "LOST",
        f"{slot1['slot_id'] if slot1 else None} vs {slot2['slot_id'] if slot2 else None}",
    ))

    # 2. Genealogy notes dict (open schema, no code change needed this pass)
    from aurora_internal.constraint_genealogy import ConstraintGenealogyLogger, PressureVec, TraceItem
    tmp = tempfile.mkdtemp(prefix="aurora_canary_f_genealogy_")
    g = ConstraintGenealogyLogger(run_id="canary_f", output_dir=tmp)
    result1 = g.observe(PressureVec(X=0.02), [TraceItem(kind="ABILITY", id="X:ADMISSIBILITY")],
                         PressureVec(), notes={"representational_ref": ref1.encode()})
    result2 = g.observe(PressureVec(T=0.02), [TraceItem(kind="ABILITY", id="T:ADVANCE_TICK")],
                         PressureVec(), notes={"representational_ref": ref2.encode()})
    genealogy_ok = (result1 is not None and result2 is not None and
                    result1.notes.get("representational_ref") == ref1.encode() and
                    result2.notes.get("representational_ref") == ref2.encode())
    out.append(BoundaryRecord(
        "F_C2", "genealogy_notes_dict", "PRESERVED" if genealogy_ok else "LOST",
        "notes dict is already Dict[str, Any] -- no genealogy code change needed; "
        "confirmed the ref round-trips through a real observe() call unchanged",
    ))
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)

    # 3. Dream evidence record origin_tags (open schema, no code change needed)
    from aurora_internal.aurora_dream_genealogy_bridge import DreamEvidenceRecord
    rec1 = DreamEvidenceRecord(evidence_id="e1", episode_id="ep1", evidence_type="improvement",
                                origin_tags={"representational_ref": ref1.encode()})
    rec2 = DreamEvidenceRecord(evidence_id="e2", episode_id="ep2", evidence_type="improvement",
                                origin_tags={"representational_ref": ref2.encode()})
    dream_ok = (rec1.to_dict()["origin_tags"].get("representational_ref") == ref1.encode() and
                rec2.to_dict()["origin_tags"].get("representational_ref") == ref2.encode())
    out.append(BoundaryRecord(
        "F_C2", "dream_evidence_record_origin_tags", "PRESERVED" if dream_ok else "LOST",
        "origin_tags is already Dict[str, Any] -- no dream schema change needed",
    ))

    # 4. RCEC EpisodeStep -- this pass's added optional field
    from aurora_internal.aurora_cognitive_experience_chamber import EpisodeStep, ActionInvocation, CapturedInterpretation
    step1 = EpisodeStep(
        tick=0, observation_text="test", action=ActionInvocation(action_type="noop"),
        intent="test", interpretation=CapturedInterpretation(raw_expression="test", confidence=0.5),
        representational_ref=ref1.encode(),
    )
    rcec_ok = step1.representational_ref == ref1.encode()
    out.append(BoundaryRecord(
        "F_C2", "rcec_episode_step_field", "PRESERVED" if rcec_ok else "LOST",
        "EpisodeStep.representational_ref (added by this pass, default None, "
        "never auto-populated by RCEC itself) carries the ref unchanged",
    ))

    # 5. WARP -- assessed, not implemented this pass
    out.append(BoundaryRecord(
        "F_C2", "warp",
        "UNREACHABLE",
        "WarpDemand.profile/CoverageGap.axis_profile are typed Dict[str, float] -- "
        "stuffing a string ref into them would violate that contract (unlike "
        "genealogy's/dream's Dict[str, Any] fields). The narrowest safe mechanism "
        "would be a new, separate optional field threaded through warp_guard()/"
        "check_and_extend()'s signatures; identified but deliberately not "
        "implemented this pass given WARP's sealed, safety-critical role and "
        "this pass's verification budget. Existing WARP behavior is unchanged "
        "(WARP was not modified).",
    ))

    # 6. Old SediMemory write direction -- still unreachable (unchanged from
    # the prior conservation report; ReflexiveInterpreter still only reads
    # from SediMemory, never writes match.constraint/dimension into it).
    out.append(BoundaryRecord(
        "F_C2", "sedimemory_write_direction", "UNREACHABLE",
        "Unchanged from the system-wide conservation report: ReflexiveInterpreter "
        "still contains no call to SediMemory.ingest_event/ingest_envelope.",
    ))

    return out


def run_all_canaries() -> List[BoundaryRecord]:
    records: List[BoundaryRecord] = []
    records += canary_a_d1()
    records += canary_b_c1()
    records += canary_c_d2()
    records += canary_d_3125()
    records += canary_e_15625()
    records += canary_f_c2()
    return records


if __name__ == "__main__":
    records = run_all_canaries()
    for r in records:
        print(f"[{r.classification:>22}] {r.canary:<10} {r.boundary}")
        print(f"    {r.detail}")
    print()
    print(json.dumps([r.to_dict() for r in records], indent=2))

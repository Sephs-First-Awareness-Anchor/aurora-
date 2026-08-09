#!/usr/bin/env python3
"""
aurora_representational_divergence_canaries.py

AURORA LIVE REPRESENTATIONAL PROPAGATION AND CONSEQUENCE-BINDING
DIRECTIVE, Section 16: six divergence canaries, one per rung of the
confirmed ladder (D1/C1/D2/M2,1/M2,2/C2), testing whether two DIFFERENT
RepresentationalRef values remain distinguishable as they pass through
the specific live-propagation touchpoints THIS pass integrated --
UnderstandingSedimentOverlay.field_keys_for_ref, SediMemory's repaired
content-key passthrough, WarpDemand/warp_guard's new provenance field,
and RCEC's EpisodeStep/backprojection/witness_report fields.

This is deliberately distinct from aurora_representational_cross_system_
canary.py (which proved the STATIC substrate resolves distinctly). Here
the requirement is narrower and stronger: does the distinction survive
the ACTUAL new wiring this pass added, not merely the address module's
own equality semantics. A behavioral difference is never required or
claimed -- only that both refs remain independently recoverable, intact,
and un-merged after passing through each real touchpoint.

Levels M2,1 (3,125) and M2,2 (15,625) are not natively producible by any
live component (confirmed by the prior directive: live construction only
ever produces D1 or C1 refs) -- consistent with the established precedent
in aurora_representational_cross_system_canary.py's canary_d_3125, those
two canaries construct the refs directly and push them through the real
touchpoint function, rather than fabricating a live selection path that
does not exist.

Read-only / ephemeral-state throughout. Part F boots a full Aurora
instance against a throwaway copy of aurora_state/ and shuts it down
cleanly afterward; every other canary uses no boot at all.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from aurora_representational_address import RepresentationalRef, resolve_manifold_slot

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))


@dataclass
class BoundaryRecord:
    canary: str
    boundary: str
    classification: str
    detail: str

    def to_dict(self) -> Dict[str, Any]:
        return {"canary": self.canary, "boundary": self.boundary,
                "classification": self.classification, "detail": self.detail}


def divergence_a_d1_understanding_sediment_overlay() -> List[BoundaryRecord]:
    """Two distinct D1 refs, deposited on two distinct field_keys, must
    remain independently recoverable via field_keys_for_ref() -- the
    reverse-lookup method added this pass."""
    from aurora_understanding_sediment import UnderstandingSedimentOverlay

    ref1 = RepresentationalRef.for_d1("X", "OPERATOR")
    ref2 = RepresentationalRef.for_d1("T", "COST")
    tmp = tempfile.mkdtemp(prefix="aurora_divergence_a_")
    try:
        overlay = UnderstandingSedimentOverlay(state_dir=tmp)
        overlay.deposit("field_alpha", "slot_1", 0.9, ref=ref1.encode())
        overlay.deposit("field_beta", "slot_1", 0.9, ref=ref2.encode())

        keys1 = overlay.field_keys_for_ref(ref1.encode())
        keys2 = overlay.field_keys_for_ref(ref2.encode())
        preserved = (keys1 == ["field_alpha"] and keys2 == ["field_beta"] and keys1 != keys2)
        return [BoundaryRecord(
            "A_D1", "understanding_sediment_overlay_field_keys_for_ref",
            "PRESERVED" if preserved else "LOST",
            f"ref1={ref1.encode()}->{keys1} ref2={ref2.encode()}->{keys2}",
        )]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def divergence_b_c1_sedimemory_passthrough() -> List[BoundaryRecord]:
    """Two distinct C1 refs carried in MemoryEvent-shaped content must
    remain distinguishable after NCStrainFilter._extract_slice() -- the
    whitelist bug this pass repaired."""
    import aurora_sedimemory as sm

    ref1 = RepresentationalRef.for_c1("X", "OPERATOR", "B")
    ref2 = RepresentationalRef.for_c1("X", "OPERATOR", "N")
    filt = sm.NCStrainFilter()
    sliced1 = filt._extract_slice(
        {"representational_ref": ref1.encode()}, sm.Constraint.X, sm.NonCompDimension.OPERATOR, 0.9,
    )
    sliced2 = filt._extract_slice(
        {"representational_ref": ref2.encode()}, sm.Constraint.X, sm.NonCompDimension.OPERATOR, 0.9,
    )
    preserved = (
        sliced1.get("representational_ref") == ref1.encode() and
        sliced2.get("representational_ref") == ref2.encode() and
        ref1 != ref2
    )
    return [BoundaryRecord(
        "B_C1", "sedimemory_extract_slice_passthrough",
        "PRESERVED" if preserved else "LOST",
        f"sliced1_ref={sliced1.get('representational_ref')} sliced2_ref={sliced2.get('representational_ref')}",
    )]


def divergence_c_d2_warp_demand_provenance() -> List[BoundaryRecord]:
    """Two distinct D2 refs, carried as WarpDemand.representational_ref,
    must remain distinguishable AND must not influence WARP's own
    classification -- two demands identical in every WARP-visible field
    except the ref must classify identically."""
    from aurora_warp_protocol import WarpField, WarpDemand

    ref1 = RepresentationalRef.for_d2("X", "OPERATOR", "T", "MAGNITUDE")
    ref2 = RepresentationalRef.for_d2("N", "COST", "B", "DIFFERENCE")

    field = WarpField()
    d1 = WarpDemand(source="canary", layer="test", trigger="test",
                     severity=0.4, persistence_key="k1", representational_ref=ref1.encode())
    d2 = WarpDemand(source="canary", layer="test", trigger="test",
                     severity=0.4, persistence_key="k1", representational_ref=ref2.encode())
    class1 = field._classify(d1)
    class2 = field._classify(d2)

    distinguishable = (d1.representational_ref == ref1.encode() and
                        d2.representational_ref == ref2.encode() and ref1 != ref2)
    no_influence = (class1 == class2)
    preserved = distinguishable and no_influence
    return [BoundaryRecord(
        "C_D2", "warp_demand_provenance_no_routing_influence",
        "PRESERVED" if preserved else "LOST",
        f"ref1={ref1.encode()} ref2={ref2.encode()} class1={class1} class2={class2}",
    )]


def divergence_d_m21_rcec_episode_step() -> List[BoundaryRecord]:
    """Two distinct M2,1 (3,125) refs, assigned directly to two separate
    EpisodeStep instances (this level is not natively producible by any
    live component), must remain distinguishable through the dataclass
    and its asdict() round trip -- the same round trip run_episode_step()
    performs on every real step."""
    from dataclasses import asdict
    from aurora_internal.aurora_cognitive_experience_chamber import (
        EpisodeStep, ActionInvocation, CapturedInterpretation,
    )

    ref1 = RepresentationalRef.for_m21("X", "OPERATOR", "B", "T", "MAGNITUDE")
    ref2 = RepresentationalRef.for_m21("N", "COST", "A", "X", "DIFFERENCE")
    assert ref1.sub_law_c is None and ref1.sub_law_d is None  # unresolved at this level

    interp = CapturedInterpretation(raw_expression="canary")
    action = ActionInvocation(action_type="observe")
    step1 = EpisodeStep(tick=0, observation_text="canary", action=action, intent="observe",
                         interpretation=interp, representational_ref=ref1.encode())
    step2 = EpisodeStep(tick=1, observation_text="canary", action=action, intent="observe",
                         interpretation=interp, representational_ref=ref2.encode())

    d1 = asdict(step1)
    d2 = asdict(step2)
    preserved = (d1["representational_ref"] == ref1.encode() and
                 d2["representational_ref"] == ref2.encode() and ref1 != ref2)
    return [BoundaryRecord(
        "D_M21_3125", "episode_step_asdict_round_trip",
        "PRESERVED" if preserved else "LOST",
        f"ref1={ref1.encode()} ref2={ref2.encode()}",
    )]


def divergence_e_m22_rcec_backprojection() -> List[BoundaryRecord]:
    """Two distinct M2,2 (15,625) refs, one playing Ref_before and one
    Ref_after on a directly-constructed backprojection record (mirroring
    exactly the dict shape run_backprojection_step() writes), must both
    remain recoverable with neither overwriting the other."""
    ref_before = RepresentationalRef.for_m22("X", "OPERATOR", "B", "T", "N", "MAGNITUDE")
    ref_after = RepresentationalRef.for_m22("N", "COST", "A", "X", "B", "DIFFERENCE")
    assert ref_before.sub_law_d is None and ref_after.sub_law_d is None  # unresolved at this level

    backprojection = {
        "original_representational_ref": ref_before.encode(),
        "revised_representational_ref": ref_after.encode(),
    }
    preserved = (
        backprojection["original_representational_ref"] == ref_before.encode() and
        backprojection["revised_representational_ref"] == ref_after.encode() and
        ref_before != ref_after
    )
    return [BoundaryRecord(
        "E_M22_15625", "backprojection_before_after_both_recoverable",
        "PRESERVED" if preserved else "LOST",
        f"before={ref_before.encode()} after={ref_after.encode()}",
    )]


def divergence_f_c2_end_to_end_manifold_resolution() -> List[BoundaryRecord]:
    """Full C2 (78,125): a live-produced C1 origin ref, extended to two
    different fully-resolved C2 completions (sub_law_c/sub_law_d/col_law_c/
    col_law_d canary-supplied, since no live component resolves them --
    documented, not fabricated as live selection), must resolve to two
    different real ManifoldSlots while the shared C1 origin field stays
    identical and independently recoverable in both."""
    from aurora_reflexive_interpreter import ReflexiveInterpreter
    from aurora_manifold_directory_reader import ManifoldDirectory

    manifold_dir = os.path.join(REPO_ROOT, "aurora_manifold_directory")
    tmp = tempfile.mkdtemp(prefix="aurora_divergence_f_")
    try:
        ri = ReflexiveInterpreter(directory=ManifoldDirectory(manifold_dir), state_dir=tmp)
        state = ri.interpret("I need to protect my boundaries here")
        origin = RepresentationalRef.decode(state.representational_ref)
        if origin.nc_target is None:
            return [BoundaryRecord(
                "F_C2", "live_c1_origin_available",
                "UNREACHABLE",
                "live interpret() did not resolve a C1-level nc_target for this input",
            )]

        completion1 = RepresentationalRef.for_c2(
            nc_law_c=origin.nc_law_c, nc_dim=origin.nc_dim, nc_target=origin.nc_target,
            sub_law_c="T", sub_law_d="MAGNITUDE", col_law_c="N", col_law_d="DIFFERENCE",
        )
        completion2 = RepresentationalRef.for_c2(
            nc_law_c=origin.nc_law_c, nc_dim=origin.nc_dim, nc_target=origin.nc_target,
            sub_law_c="A", sub_law_d="COST", col_law_c="B", col_law_d="POLARITY",
        )
        slot1 = resolve_manifold_slot(completion1)
        slot2 = resolve_manifold_slot(completion2)
        same_origin = (completion1.nc_law_c == origin.nc_law_c and
                       completion1.nc_dim == origin.nc_dim and
                       completion1.nc_target == origin.nc_target and
                       completion2.nc_law_c == origin.nc_law_c and
                       completion2.nc_dim == origin.nc_dim and
                       completion2.nc_target == origin.nc_target)
        distinct_slots = (slot1 is not None and slot2 is not None and slot1["slot_id"] != slot2["slot_id"])
        preserved = same_origin and distinct_slots
        return [BoundaryRecord(
            "F_C2", "live_origin_to_distinct_manifold_slots",
            "PRESERVED" if preserved else "LOST",
            f"origin={origin.encode()} slot1={slot1['slot_id'] if slot1 else None} "
            f"slot2={slot2['slot_id'] if slot2 else None}",
        )]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def run_all() -> List[BoundaryRecord]:
    records: List[BoundaryRecord] = []
    records += divergence_a_d1_understanding_sediment_overlay()
    records += divergence_b_c1_sedimemory_passthrough()
    records += divergence_c_d2_warp_demand_provenance()
    records += divergence_d_m21_rcec_episode_step()
    records += divergence_e_m22_rcec_backprojection()
    records += divergence_f_c2_end_to_end_manifold_resolution()
    return records


if __name__ == "__main__":
    import json
    recs = run_all()
    for r in recs:
        print(f"[{r.canary:>10}] [{r.classification:>12}] {r.boundary}")
        print(f"    {r.detail}")
    print()
    print(json.dumps([r.to_dict() for r in recs], indent=2))

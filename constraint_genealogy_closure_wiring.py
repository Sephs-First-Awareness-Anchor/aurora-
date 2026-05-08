#!/usr/bin/env python3
"""
CONSTRAINT GENEALOGY — CLOSURE BASIS WIRING
=============================================
Module: constraint_genealogy_closure_wiring.py

This file documents and implements the exact wiring between
aurora_closure_basis.py and the running constraint_genealogy.py stack.

HOW TO APPLY
------------
This file contains COMPLETE REPLACEMENT VERSIONS of four sections in
constraint_genealogy.py. Each section is self-contained with a clearly
marked location header. No other files need to change.

After applying, the running system will:
    • Classify every ability and link against the real 25 NonComp channels
    • Derive grades from actual shift_cost, inertia, leverage physics
    • Have leverage_grade calibrated to the viable band (not zero-centered)
    • Tag every promoted link with ontological_status and depth_score
    • Use GENEALOGY_ATOM_TO_SLOT_ID as the authoritative gen0 membership test

THE EXACT DATA FLOW
-------------------

BEFORE (string-frequency heuristic):

    ability.axis + ability.requires
        → _derive_operation_origin()
            → builds root_slot = "NC:X>T×NC:T>X"  [string tokens only]
            → builds counts = {X:1, T:1, ...}       [axis character counting]
        → _lineage_grade_payload(counts, primary, generation)
            → complexity = (active_axes-1)/4        [normalized count math]
            → operator_grade = 0.65*complexity + ... [no physics]
            → purpose_lane from SEMANTIC_LANE_IMPACT  [overlay weights]
            → returns grades dict

AFTER (physics-grounded):

    ability.axis + ability.requires + root_slot
        → _derive_operation_origin()          [unchanged — still builds root_slot]
        → _lineage_grade_payload_v2(counts, dominant_axis, generation)
            → extracts requires from counts
            → extracts secondary axis from counts
            → calls derive_lineage(axis, requires, root_slot)
                → resolves NC:C1>C2 atoms to real 625 slots via
                  GENEALOGY_ATOM_TO_SLOT_ID
                → computes energetic_footprint from real shift_cost_coeffs
                → computes depth_score from shift_cost / kA
                → computes leverage_grade from viable band center (+1.175)
                → computes operator_grade depth-weighted against OPERATOR channels
            → calls lineage_grade_payload(lineage)
            → returns same dict keys + new physics fields

The root_slot format "NC:X>T×NC:T>X" already exists in the live system.
Every part of every root_slot in the 136 live abilities maps into
GENEALOGY_ATOM_TO_SLOT_ID with zero gaps. No data migration required.

WHAT DOES NOT CHANGE
--------------------
    • _derive_operation_origin() — unchanged, still builds root_slot
    • AbilityProfile dataclass — unchanged
    • ConstraintLink dataclass — unchanged
    • PairStats, GenealogyConfig — unchanged
    • Promotion gates, relief thresholds — unchanged
    • The fossil record on disk — existing tags stay, new tags added going forward
    • _bred_child_generation, _generation_role_name — unchanged

Authors: Sunni (Sir) Morningstar and Cael Devo
Created: March 2026
"""

# =============================================================================
# PATCH 1 — ADD TO IMPORTS BLOCK
# Location: after the existing `from aurora_constraint_stack import ...` line
# =============================================================================
#
# from aurora_closure_basis import (
#     derive_lineage,
#     lineage_grade_payload,
#     classify_ontological_status,
#     channel_ids_from_ability_id,
#     GENEALOGY_ATOM_TO_SLOT_ID,   # replaces inline gen0_atoms frozenset
#     OntologicalStatus,
# )
#
# =============================================================================


# =============================================================================
# PATCH 2 — REPLACE _lineage_grade_payload
# Location: search `def _lineage_grade_payload(counts` — replace entire function
#
# This is the core swap. Same call signature, physics-grounded output.
# All three existing callers continue to work unchanged:
#     _augment_ability_profile_with_origin (abilities)
#     _lineage_grade_for_pair              (links)
#     _lineage_grade_for_pair artificial directive override (unchanged — still patches payload)
# =============================================================================

from typing import Any, Dict, Optional, Tuple
AXES = ("X", "T", "N", "B", "A")


def _lineage_grade_payload(
    counts: Dict[str, int],
    dominant_axis: str,
    generation: int,
    root_slot: str = "",
) -> Dict[str, Any]:
    """
    Compute lineage grades from axis counts.

    Drop-in replacement for the string-frequency version.
    Same required signature (counts, dominant_axis, generation) so all
    existing callers work without change.

    Optional root_slot: if provided, the closure basis resolves the
    real 625 slots directly. If not provided, it is reconstructed from
    counts + dominant_axis (same result for all existing call sites,
    since _derive_operation_origin already computed it and stored it in
    origin["root_slot"]).

    All output keys are preserved for backward compatibility:
        operator_action, purpose_lane, operator_grade, purpose_grade,
        overall_grade, complexity_score, complexity_axes, complexity_slots,
        generation, generation_role

    New keys added (do not break existing tag consumers):
        energetic_footprint, depth_score, leverage_grade,
        viable_band_alignment, formation_cost, dominant_dimension,
        dominant_constraint, dominant_i_state_pos, dominant_i_state_neg,
        ontological_status
    """
    from aurora_closure_basis import (
        derive_lineage,
        lineage_grade_payload as _closure_grade_payload,
    )

    dom = str(dominant_axis or "X").strip().upper()
    if dom not in set(AXES):
        dom = "X"

    # Build requires from counts — axes with count > 0
    requires: Tuple[str, ...] = tuple(
        ax for ax in AXES if int(counts.get(ax, 0) or 0) > 0
    )
    if not requires:
        requires = (dom,)

    # Build root_slot if not provided
    if not root_slot:
        secondary = next(
            (ax for ax in AXES if ax != dom and int(counts.get(ax, 0) or 0) > 0),
            dom,
        )
        root_slot = f"NC:{dom}>{secondary}×NC:{secondary}>{dom}"

    lineage = derive_lineage(dom, requires, root_slot)
    payload = _closure_grade_payload(lineage)

    # Preserve generation field from caller — the physics generation is a
    # structural estimate; the genealogy may have a more accurate value
    # from breeding pair history. Keep the higher of the two.
    payload["generation"] = int(max(
        int(payload.get("generation", 1) or 1),
        int(max(1, generation)),
    ))
    payload["generation_role"] = _generation_role_name(int(payload["generation"]))

    return payload


# Helper — copied from constraint_genealogy._generation_role_name
# Inlined here so aurora_closure_basis has no circular import on the genealogy.
def _generation_role_name(gen: int) -> str:
    """Generational alignment role (tetrad + warp law)."""
    g = int(gen or 0)
    if g > 0 and g % 5 == 0:
        return "WARP"
    pos = ((max(1, g) - 1) % 4) + 1
    if pos == 1:
        return "PRIMARY"
    if pos == 2:
        return "ADJACENT"
    if pos == 3:
        return "SHEAR"
    return "BRIDGE"


# =============================================================================
# PATCH 3 — REPLACE _augment_ability_profile_with_origin
# Location: search `def _augment_ability_profile_with_origin(ap` — replace entire function
#
# Passes root_slot directly to _lineage_grade_payload so the closure basis
# resolves from the real slot rather than reconstructing it.
# Adds ontological_status, depth_score, viable_band_alignment, leverage_grade
# tags to every AbilityProfile.
# =============================================================================

def _augment_ability_profile_with_origin(ap: "AbilityProfile") -> "AbilityProfile":
    """
    Augment an AbilityProfile with origin, grading, and closure basis metadata.

    Identical contract to the original but passes root_slot to
    _lineage_grade_payload so the closure basis resolves real 625 slots.
    Adds new physics tags without removing any existing ones.
    """
    import hashlib
    from aurora_closure_basis import classify_ontological_status

    origin  = _derive_operation_origin(ap.id, ap.axis, ap.requires, ap.effect_tags)
    counts  = _lineage_counts_from_signature(origin["signature"])
    generation = _lineage_generation_from_counts(counts)

    # Pass root_slot — the closure basis resolves real slots directly
    grading = _lineage_grade_payload(
        counts, origin["primary"], generation,
        root_slot=origin["root_slot"],
    )

    # Ontological status from closure basis
    ancestry = [origin["root_a"], origin["root_b"]]
    ontological_status = classify_ontological_status(ancestry)

    # Build tags — all existing keys preserved, new ones appended
    tags = list(ap.effect_tags or ())
    seed_lineage = (
        str(origin.get("root_a", "")).startswith("NC:")
        and str(origin.get("root_b", "")).startswith("NC:")
    )
    tags.extend([
        f"origin_primary:{origin['primary']}",
        f"origin_secondary:{origin['secondary']}",
        f"origin_signature:{origin['signature']}",
        f"root_slot:{origin['root_slot']}",
        f"operation_lineage:{origin['lineage_id']}",
        f"seed_lineage:{'true' if seed_lineage else 'false'}",
        # --- grades (now physics-derived) ---
        f"operator_action:{grading['operator_action']}",
        f"purpose_lane:{grading['purpose_lane']}",
        f"operator_grade:{float(grading['operator_grade']):.3f}",
        f"purpose_grade:{float(grading['purpose_grade']):.3f}",
        f"overall_grade:{float(grading['overall_grade']):.3f}",
        f"complexity_axes:{int(grading['complexity_axes'])}",
        f"complexity_slots:{int(grading['complexity_slots'])}",
        f"generation:{int(grading['generation'])}",
        f"generation_role:{grading['generation_role']}",
        # --- new physics tags ---
        f"energetic_footprint:{float(grading.get('energetic_footprint', 0.0)):.4f}",
        f"depth_score:{float(grading.get('depth_score', 0.0)):.4f}",
        f"leverage_grade:{float(grading.get('leverage_grade', 0.5)):.4f}",
        f"viable_band_alignment:{float(grading.get('viable_band_alignment', 0.0)):.4f}",
        f"formation_cost:{float(grading.get('formation_cost', 0.0)):.4f}",
        f"dominant_constraint:{grading.get('dominant_constraint', origin['primary'])}",
        f"dominant_dimension:{grading.get('dominant_dimension', 'OPERATOR')}",
        f"ontological_status:{ontological_status.value}",
    ])
    dedup_tags = tuple(dict.fromkeys([str(t) for t in tags if str(t)]))

    notes = str(ap.notes or "")
    marker = f"operation_lineage_id={origin['lineage_id']}"
    if marker not in notes:
        suffix = (
            f" [origin root_slot={origin['root_slot']}; "
            f"root_parents={origin['root_a']},{origin['root_b']}; "
            f"origin_signature={origin['signature']}; "
            f"operation_lineage_id={origin['lineage_id']}; "
            f"operator_action={grading['operator_action']}; "
            f"purpose_lane={grading['purpose_lane']}; "
            f"operator_grade={float(grading['operator_grade']):.3f}; "
            f"depth_score={float(grading.get('depth_score',0.0)):.4f}; "
            f"leverage_grade={float(grading.get('leverage_grade',0.5)):.4f}; "
            f"ontological_status={ontological_status.value}; "
            f"generation={int(grading['generation'])}; "
            f"generation_role={grading['generation_role']}]"
        )
        notes = (notes + suffix).strip()

    return AbilityProfile(
        id=ap.id,
        axis=ap.axis,
        requires=tuple(ap.requires),
        cost={a: float(ap.cost.get(a, 0.0)) for a in AXES},
        risk={a: float(ap.risk.get(a, 0.0)) for a in AXES},
        effect_tags=dedup_tags,
        notes=notes,
    )


# =============================================================================
# PATCH 4 — REPLACE THREE gen0_atoms FROZENSET CONSTRUCTIONS
# Location: three sites in constraint_genealogy.py — all identical one-liner
#
# FIND:
#     gen0_atoms = {f"NC:{a}>{b}" for a in AXES for b in AXES}
#
# REPLACE WITH:
#     from aurora_closure_basis import GENEALOGY_ATOM_TO_SLOT_ID
#     gen0_atoms = frozenset(GENEALOGY_ATOM_TO_SLOT_ID.keys())
#
# The three sites are at approximately:
#     Line 1749 — inside chain_report()
#     Line 2840 — inside _item_generation()
#     Line 4454 — inside _item_seed_meta()
#
# RATIONALE:
# The inline frozenset builds the same 25 strings every call.
# GENEALOGY_ATOM_TO_SLOT_ID is built once at import and is the authoritative
# membership test — it also gives you the slot_id for free if you need it.
#
# Both produce the same 25 members:
#     {"NC:X>X", "NC:X>T", "NC:X>N", "NC:X>B", "NC:X>A",
#      "NC:T>X", "NC:T>T", ...  "NC:A>A"}
# But GENEALOGY_ATOM_TO_SLOT_ID also maps each to its real 625 slot ID,
# enabling slot-level queries anywhere in the genealogy without extra lookups.
# =============================================================================


# =============================================================================
# PATCH 5 — ADD closure_status TAG TO LINK PROMOTION BLOCK
# Location: inside ConstraintGenealogyLogger — the tags.extend([...]) block
#   that starts with `lineage_grade = self._lineage_grade_for_pair(...)`
#   (approximately line 4405)
#
# ADD to the tags.extend([...]) list — after the steering_target_generation line:
#
#     f"ontological_status:{lineage_grade.get('ontological_status', 'derivative_offspring')}",
#     f"depth_score:{float(lineage_grade.get('depth_score', 0.0)):.4f}",
#     f"leverage_grade:{float(lineage_grade.get('leverage_grade', 0.5)):.4f}",
#     f"viable_band_alignment:{float(lineage_grade.get('viable_band_alignment', 0.0)):.4f}",
#     f"energetic_footprint:{float(lineage_grade.get('energetic_footprint', 0.0)):.4f}",
#     f"dominant_constraint:{lineage_grade.get('dominant_constraint', '')}",
#     f"dominant_dimension:{lineage_grade.get('dominant_dimension', 'OPERATOR')}",
#
# These tags are added to every promoted ConstraintLink. The lineage_grade
# dict already has all these keys because _lineage_grade_payload now returns
# them (Patch 2). No computation needed here — just tag extraction.
# =============================================================================


# =============================================================================
# PATCH 6 — ADD closure_status BREAKDOWN TO chain_report()
# Location: the return dict at the end of ConstraintGenealogyLogger.chain_report()
#
# ADD this key to the returned dict:
#
#     "ontological_status_breakdown": _build_closure_status_summary(
#         self.links, self.abilities
#     ),
#
# And add this module-level helper function (outside the class):
# =============================================================================

def _build_closure_status_summary(
    links:     "Dict[str, ConstraintLink]",
    abilities: "Dict[str, AbilityProfile]",
) -> Dict[str, Any]:
    """
    Summarise ontological status distribution across the evolved lineage.

    Reads tags already written by Patches 3 and 5. No new computation.
    Answers: what fraction of Aurora's evolved structure is native to the
    closed basis vs derivative vs external overlay?

    Expected result after a healthy run:
        abilities: ~100% derivative_offspring (seed abilities are axis-prefixed)
        links:     ~100% derivative_offspring (promoted from native roots)
        external_overlay: 0% if the stack is clean
    """
    status_counts = {
        "native_closed":            0,
        "derivative_offspring":     0,
        "descriptive_convenience":  0,
        "external_overlay":         0,
        "unclassified":             0,
    }

    def _read_status(tags_or_effect_tags) -> str:
        for t in (tags_or_effect_tags or []):
            s = str(t)
            if s.startswith("ontological_status:"):
                return s.split(":", 1)[1].strip()
            if s.startswith("closure_status:"):
                return s.split(":", 1)[1].strip()
        return "unclassified"

    ability_dist = dict(status_counts)
    for ap in abilities.values():
        key = _read_status(ap.effect_tags)
        if key in ability_dist:
            ability_dist[key] += 1
        else:
            ability_dist["unclassified"] += 1

    link_dist = dict(status_counts)
    for lnk in links.values():
        key = _read_status(lnk.tags)
        if key in link_dist:
            link_dist[key] += 1
        else:
            link_dist["unclassified"] += 1

    total_ab = max(1, sum(ability_dist.values()))
    total_lk = max(1, sum(link_dist.values()))

    return {
        "summary": (
            "Distribution of ontological status across Aurora's evolved structure. "
            "native_closed = the 25 NonComp channels themselves. "
            "derivative_offspring = born lawfully through constraint pressure. "
            "external_overlay = imported or post-hoc reducible, not native. "
            "unclassified = not yet tagged (pre-patch abilities/links)."
        ),
        "abilities": {
            "total":     sum(ability_dist.values()),
            "counts":    ability_dist,
            "fractions": {k: round(v / total_ab, 4) for k, v in ability_dist.items()},
        },
        "links": {
            "total":     sum(link_dist.values()),
            "counts":    link_dist,
            "fractions": {k: round(v / total_lk, 4) for k, v in link_dist.items()},
        },
        "health_signal": (
            "clean"
            if link_dist.get("external_overlay", 0) == 0
            else f"WARNING: {link_dist['external_overlay']} links are external overlays"
        ),
    }


# =============================================================================
# CIRCULAR IMPORT FIX FOR aurora_closure_basis.py
# =============================================================================
#
# The current aurora_closure_basis.py has this line in lineage_grade_payload():
#
#     from constraint_genealogy import _generation_role_name   # avoids circular
#
# This is still a circular import — it happens at call time but the dependency
# exists. Fix by inlining _generation_role_name in aurora_closure_basis.py.
#
# ADD this function to aurora_closure_basis.py (anywhere before lineage_grade_payload):
#
# def _generation_role_name(gen: int) -> str:
#     """Generational alignment role. Inlined from constraint_genealogy."""
#     g = int(gen or 0)
#     if g > 0 and g % 5 == 0:
#         return "WARP"
#     pos = ((max(1, g) - 1) % 4) + 1
#     if pos == 1: return "PRIMARY"
#     if pos == 2: return "ADJACENT"
#     if pos == 3: return "SHEAR"
#     return "BRIDGE"
#
# THEN in lineage_grade_payload(), replace:
#     from constraint_genealogy import _generation_role_name
# with:
#     (nothing — the function is now local to the module)
#
# =============================================================================


# =============================================================================
# VERIFICATION — run this after applying all patches
# =============================================================================

def verify_wiring() -> bool:
    """
    Confirm the wiring works end-to-end against the live ability set.

    Run this once after applying all patches to confirm the system
    classifies correctly before starting a new training run.
    """
    from aurora_closure_basis import (
        derive_lineage,
        lineage_grade_payload,
        classify_ontological_status,
        GENEALOGY_ATOM_TO_SLOT_ID,
        INTERACTION_FIELD,
        NONCOMP_CHANNELS,
        OntologicalStatus,
    )

    print("=== CLOSURE BASIS WIRING VERIFICATION ===\n")

    # 1. Confirm gen0_atoms membership is identical
    inline_gen0 = frozenset(f"NC:{a}>{b}" for a in AXES for b in AXES)
    closure_gen0 = frozenset(GENEALOGY_ATOM_TO_SLOT_ID.keys())
    assert inline_gen0 == closure_gen0, \
        f"gen0_atoms mismatch: {inline_gen0.symmetric_difference(closure_gen0)}"
    print(f"[OK] gen0_atoms: {len(closure_gen0)} atoms — identical to inline frozenset")

    # 2. Every gen0_atom maps to a real 625 slot
    for atom, slot_id in GENEALOGY_ATOM_TO_SLOT_ID.items():
        assert slot_id in INTERACTION_FIELD, f"Slot {slot_id} not in INTERACTION_FIELD"
    print(f"[OK] All 25 gen0_atoms resolve to real 625 slots")

    # 3. Sample ability derivations — test the five seed abilities
    sample_abilities = [
        ("X", ("X",),      "NC:X>X×NC:X>X",  "X:ADMIT",      OntologicalStatus.NATIVE_CLOSED),
        ("T", ("T", "N"),  "NC:T>N×NC:N>T",  "T:BATCH",      OntologicalStatus.NATIVE_CLOSED),
        ("B", ("X", "B"),  "NC:X>B×NC:B>X",  "B:ENCAPSULATE",OntologicalStatus.NATIVE_CLOSED),
        ("A", ("A", "B"),  "NC:B>A×NC:A>B",  "A:OUTLET_PUSH",OntologicalStatus.NATIVE_CLOSED),
        ("A", ("A", "X"),  "NC:X>A×NC:A>X",  "A:COMMIT",     OntologicalStatus.NATIVE_CLOSED),
    ]

    print("\nAbility lineage derivations:")
    for ax, req, rs, label, expected_status in sample_abilities:
        lin   = derive_lineage(ax, req, rs)
        grade = lineage_grade_payload(lin)
        assert lin.ontological_status == expected_status, \
            f"{label}: expected {expected_status}, got {lin.ontological_status}"
        assert len(lin.active_slots) > 0, f"{label}: no active slots"
        assert 0.0 <= lin.depth_score <= 1.0
        assert 0.0 <= lin.leverage_grade <= 1.0
        assert 0.0 <= lin.viable_band_alignment <= 1.0
        assert grade["generation"] >= 1
        assert grade["generation_role"] in {"PRIMARY", "ADJACENT", "SHEAR", "BRIDGE", "WARP"}
        print(
            f"  [{label}] "
            f"status={lin.ontological_status.value[:7]}  "
            f"depth={lin.depth_score:.3f}  "
            f"lev_grade={lin.leverage_grade:.3f}  "
            f"band_align={lin.viable_band_alignment:.3f}  "
            f"gen={grade['generation']}({grade['generation_role']})  "
            f"slots={len(lin.active_slots)}"
        )

    # 4. Leverage grade ordering: X-only < band center < A/B dominant
    lin_x  = derive_lineage("X", ("X",),   "NC:X>X×NC:X>X")
    lin_a  = derive_lineage("A", ("A","B"), "NC:A>B×NC:B>A")
    assert lin_x.leverage_grade < 0.5, \
        f"X-only should be below band center, got {lin_x.leverage_grade}"
    assert lin_a.leverage_grade > 0.5, \
        f"A/B dominant should be above band center, got {lin_a.leverage_grade}"
    assert lin_a.leverage_grade > lin_x.leverage_grade
    print(
        f"\n[OK] Leverage ordering: "
        f"X-only={lin_x.leverage_grade:.3f} < "
        f"center=0.5 < "
        f"A/B={lin_a.leverage_grade:.3f}"
    )

    # 5. Depth ordering: X < T < N < B < A
    depths = []
    for ax in ("X", "T", "N", "B", "A"):
        lin = derive_lineage(ax, (ax,), f"NC:{ax}>{ax}×NC:{ax}>{ax}")
        depths.append((ax, lin.depth_score))
    depth_vals = [d for _, d in depths]
    assert depth_vals == sorted(depth_vals), \
        f"Depth ordering violated: {depths}"
    print(f"[OK] Depth ordering: " + " < ".join(f"{ax}={d:.3f}" for ax, d in depths))

    # 6. Cost ordering matches Sunni's law
    costs = [NONCOMP_CHANNELS[f"NC:{ax}:COST"].shift_cost_coeff for ax in ("X","T","N","B","A")]
    assert costs == sorted(costs), f"Cost ordering violated: {costs}"
    print(f"[OK] Sunni's cost law: {dict(zip(('X','T','N','B','A'), costs))}")

    # 7. gen0_atoms membership test — same result as inline
    test_atoms = ["NC:X>T", "NC:B>A", "NC:A>A", "NC:X>X", "NOT_AN_ATOM"]
    for atom in test_atoms:
        in_closure = atom in closure_gen0
        in_inline  = atom in inline_gen0
        assert in_closure == in_inline, f"Membership mismatch for {atom}"
    print(f"[OK] gen0_atoms membership consistent for test set")

    # 8. _lineage_grade_payload produces all required keys for tag building
    grade = _lineage_grade_payload(
        {"X": 1, "T": 1, "N": 0, "B": 0, "A": 0},
        "X",
        1,
        root_slot="NC:X>T×NC:T>X",
    )
    required_keys = {
        "operator_action", "purpose_lane", "operator_grade", "purpose_grade",
        "overall_grade", "complexity_score", "complexity_axes", "complexity_slots",
        "generation", "generation_role",
        "energetic_footprint", "depth_score", "leverage_grade",
        "viable_band_alignment", "formation_cost", "dominant_constraint",
        "dominant_dimension", "ontological_status",
    }
    missing_keys = required_keys - set(grade.keys())
    assert not missing_keys, f"_lineage_grade_payload missing keys: {missing_keys}"
    print(f"[OK] _lineage_grade_payload returns all {len(required_keys)} required keys")

    print("\n=== ALL WIRING CHECKS PASSED ===")
    print("The stack is ready to run. New runs will classify against the real 625.")
    return True


# =============================================================================
# FULL DATA FLOW DIAGRAM
# =============================================================================
#
#   constraint_genealogy.py                   aurora_closure_basis.py
#   ─────────────────────────────────────────────────────────────────────
#
#   AbilityProfile(axis, requires, ...)
#     │
#     ▼
#   _derive_operation_origin(ap.id, ap.axis, ap.requires, ap.effect_tags)
#     │   [unchanged — still parses strings, builds root_slot]
#     │   returns: {root_slot: "NC:X>T×NC:T>X", primary: "X", ...}
#     │
#     ▼
#   _lineage_grade_payload(counts, dominant_axis, generation,       ──────►  derive_lineage(axis, requires, root_slot)
#     root_slot=origin["root_slot"])           [NEW: passes root_slot]           │
#     │                                                                           │  looks up GENEALOGY_ATOM_TO_SLOT_ID["NC:X>T"]
#     │                                                                           │  = "NC:X:OPERATORxNC:T:COST"
#     │                                                                           │  resolves to InteractionSlot(
#     │                                                                           │      combined_shift_cost = 1.0 + 4.0 = 5.0
#     │                                                                           │      depth_score = (0.007 + 0.027) / 2 = 0.017
#     │                                                                           │      leverage_net = -1 + -1 = -2  [both overhead]
#     │                                                                           │      leverage_grade = 0.38  [below band center]
#     │                                                                           │  )
#     │                                                                           │
#     │                                                                           ▼
#     │                                                                       ConstraintLineage(
#     │                                                                           depth_score = 0.017
#     │                                                                           leverage_grade = 0.38
#     │                                                                           viable_band_alignment = 0.76
#     │                                                                           operator_grade = 0.65
#     │                                                                           physics_generation = 1
#     │                                                                           ontological_status = NATIVE_CLOSED
#     │                                                                       )
#     │
#     ◄────────────────────────────────────────────────────────────────────  lineage_grade_payload(lineage)
#     │   returns: {operator_grade: 0.65, depth_score: 0.017,
#     │              leverage_grade: 0.38, viable_band_alignment: 0.76,
#     │              ontological_status: "native_closed", ...}
#     │
#     ▼
#   _augment_ability_profile_with_origin(ap)
#     │   writes all keys as effect_tags on AbilityProfile
#     │   including new: depth_score, leverage_grade, ontological_status
#     ▼
#   AbilityProfile with full physics-grounded tags
#
#
#   ─── LINK PROMOTION PATH ────────────────────────────────────────────
#
#   pair_key = ("X:ADMIT", "T:BATCH")
#     │
#     ▼
#   _merged_axis_counts_for_pair(key)          [unchanged]
#     │   counts = {X:1, T:1, N:1, ...}
#     │
#     ▼
#   _lineage_grade_for_pair(key, dominant_axis)
#     │   calls _lineage_grade_payload(counts, dom, gen)  [now physics-grounded]
#     │
#     ▼
#   tags.extend([...lineage_grade fields...])  [+ new physics tags]
#     │
#     ▼
#   ConstraintLink promoted with:
#       ontological_status: "derivative_offspring"
#       depth_score: 0.017
#       leverage_grade: 0.38
#       viable_band_alignment: 0.76
#
#
#   ─── gen0_atoms MEMBERSHIP (3 sites) ────────────────────────────────
#
#   BEFORE: gen0_atoms = {f"NC:{a}>{b}" for a in AXES for b in AXES}
#           → builds frozenset inline, every call
#
#   AFTER:  from aurora_closure_basis import GENEALOGY_ATOM_TO_SLOT_ID
#           gen0_atoms = frozenset(GENEALOGY_ATOM_TO_SLOT_ID.keys())
#           → same 25 strings, sourced from authoritative module constant
#           → also gives slot_id lookup if needed:
#             GENEALOGY_ATOM_TO_SLOT_ID["NC:X>T"] = "NC:X:OPERATORxNC:T:COST"
#
# =============================================================================

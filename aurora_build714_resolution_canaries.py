#!/usr/bin/env python3
"""
aurora_build714_resolution_canaries.py

AURORA BUILD 714 -- NATIVE ADAPTIVE REPRESENTATIONAL RESOLUTION.
Five live canaries (directive Section 31), following the same convention
as aurora_representational_cross_system_canary.py / aurora_representational_
divergence_canaries.py already in this repo: executable, narrative,
run against real (unmocked) ConstraintGenealogyLogger/RepresentationalRef/
HabitatRuntime machinery, never a mock of the physics under test.

Run directly for a human-readable trace: python3 aurora_build714_resolution_canaries.py
Asserted by tests/test_build714_resolution_canaries.py for CI.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Dict

from aurora_internal.constraint_genealogy import (
    AXES,
    AbilityProfile,
    ConstraintGenealogyLogger,
    GenealogyConfig,
    TraceItem,
)
from aurora_representational_address import RepresentationalRef
from aurora_representational_resolution import RepresentationalResolutionEngine


def _fresh(root: Path, name: str):
    genealogy = ConstraintGenealogyLogger(name, config=GenealogyConfig(), output_dir=str(root / name / "g"))
    engine = RepresentationalResolutionEngine(genealogy, state_dir=str(root / name / "s"))
    return genealogy, engine


def _context(genealogy, cid: str) -> None:
    if cid not in genealogy.abilities:
        genealogy.abilities[cid] = AbilityProfile(
            id=cid, axis="X", requires=("X",),
            cost={a: 0.0 for a in AXES}, risk={a: 0.0 for a in AXES},
            effect_tags=("context_marker",), notes="canary context",
        )


def _drive(genealogy, engine, ref, *, axes, n_contexts=3, prefix="CTX"):
    for i, ax in enumerate(axes):
        cid = f"{prefix}:{i % n_contexts}"
        _context(genealogy, cid)
        engine.record_participation(
            ref,
            pressure_before={a: (0.3 if a == ax else 0.0) for a in AXES},
            pressure_after={a: 0.0 for a in AXES},
            source="canary", context_tag=cid,
            extra_trace=[TraceItem(kind="ABILITY", id=cid)],
        )


# ── Canary 1: Same Input, Same Adequate History ─────────────────────────────

def canary_1_stable_coarse_history(root: Path) -> Dict[str, Any]:
    genealogy, engine = _fresh(root, "canary1")
    ref = RepresentationalRef.for_c1("T", "MAGNITUDE", "B")
    # 9 repeated, coherent observations: relief always lands on the ref's
    # own declared axis (T) -- no divergence, ever.
    _drive(genealogy, engine, ref, axes=["T"] * 9)
    pressure = engine.inadequacy_pressure(ref)
    candidates = engine.unresolved_field_candidates(ref)
    return {
        "name": "same_input_same_adequate_history",
        "pressure": pressure,
        "candidates": candidates,
        "stayed_coarse": ref.unresolved_fields() == ("sub_law_c", "sub_law_d", "col_law_c", "col_law_d"),
        "passed": pressure == 0.0 and candidates == [] and ref.level() == "C1_125",
    }


# ── Canary 2: Same Input, Divergent History ─────────────────────────────────

def canary_2_divergent_history(root: Path) -> Dict[str, Any]:
    genealogy, engine = _fresh(root, "canary2")
    ref = RepresentationalRef.for_c1("T", "MAGNITUDE", "B")
    sibling = RepresentationalRef.for_m21("T", "MAGNITUDE", "B", col_law_c="N", col_law_d="COST")
    engine.ensure_registered(sibling)
    # Same coarse ref, but its prior contexts contain repeatable
    # consequential divergence (relief scattering off the declared axis).
    _drive(genealogy, engine, ref, axes=["B", "N", "X"] * 3, n_contexts=3)
    pressure = engine.inadequacy_pressure(ref)
    candidates = engine.unresolved_field_candidates(ref)
    no_value_hardcoded = ref.col_law_c is None  # pressure alone never fills anything
    return {
        "name": "same_input_divergent_history",
        "pressure": pressure,
        "candidates": candidates,
        "field_investigable": bool(candidates),
        "no_value_hardcoded": no_value_hardcoded,
        "passed": pressure > 0.0 and bool(candidates) and no_value_hardcoded,
    }


# ── Canary 3: Refinement Pays Off ───────────────────────────────────────────

def canary_3_refinement_pays_off(root: Path) -> Dict[str, Any]:
    genealogy, engine = _fresh(root, "canary3")
    ref = RepresentationalRef.for_c1("T", "MAGNITUDE", "B")
    sibling = RepresentationalRef.for_m21("T", "MAGNITUDE", "B", col_law_c="N", col_law_d="COST")
    engine.ensure_registered(sibling)
    _drive(genealogy, engine, ref, axes=["B", "N", "X"] * 3, n_contexts=3)

    candidates = engine.unresolved_field_candidates(ref)
    candidate = candidates[0]
    discrepancy_before = (engine.consequence_profile_for(ref) or {}).get("discrepancy", 0.0)

    staged = engine.stage_field_inquiry(ref, candidate, consumer="canary3")
    result = engine.complete_field_inquiry(
        ref, candidate, staged[0], consumer="canary3", actual_coactivation=True,
        pressure_before={"X": 0.0, "T": 0.4, "N": 0.0, "B": 0.0, "A": 0.0},
        pressure_after={a: 0.0 for a in AXES},
    )
    retained = result["representational_resolution_outcome"] == "retained"
    resolved = RepresentationalRef.decode(result["refined_ref"]) if result["refined_ref"] else None
    records = engine.genealogy_for(ref)
    return {
        "name": "refinement_pays_off",
        "candidate": candidate,
        "outcome": result["representational_resolution_outcome"],
        "discrepancy_before": discrepancy_before,
        "discrepancy_after": records[-1]["discrepancy_after"] if records else None,
        "resolved_ref": resolved.encode() if resolved else None,
        "passed": (
            retained
            and resolved is not None
            and getattr(resolved, candidate["field"]) == candidate["candidate_value"]
            and bool(records) and records[-1]["discrepancy_after"] < records[-1]["discrepancy_before"]
        ),
    }


# ── Canary 4: Refinement Does Not Pay Off ───────────────────────────────────

def canary_4_refinement_does_not_pay_off(root: Path) -> Dict[str, Any]:
    genealogy, engine = _fresh(root, "canary4")
    ref = RepresentationalRef.for_c1("T", "MAGNITUDE", "B")
    sibling = RepresentationalRef.for_m21("T", "MAGNITUDE", "B", col_law_c="N", col_law_d="COST")
    engine.ensure_registered(sibling)
    _drive(genealogy, engine, ref, axes=["B", "N", "X"] * 3, n_contexts=3)

    candidates = engine.unresolved_field_candidates(ref)
    candidate = candidates[0]
    staged = engine.stage_field_inquiry(ref, candidate, consumer="canary4")
    # The experiment happens, but the "after" state shows NO real
    # improvement over "before" -- the candidate distinction did not
    # actually discriminate anything.
    result = engine.complete_field_inquiry(
        ref, candidate, staged[0], consumer="canary4", actual_coactivation=True,
        pressure_before={"X": 0.0, "T": 0.05, "N": 0.0, "B": 0.0, "A": 0.0},
        pressure_after={"X": 0.0, "T": 0.049, "N": 0.0, "B": 0.0, "A": 0.0},
    )
    outcome = result["representational_resolution_outcome"]
    return {
        "name": "refinement_does_not_pay_off",
        "candidate": candidate,
        "outcome": outcome,
        "refined_ref": result["refined_ref"],
        "still_unresolved": ref.unresolved_fields(),
        "passed": outcome in ("rejected", "unresolved") and result["refined_ref"] is None,
    }


# ── Canary 5: Habitat Discovery ─────────────────────────────────────────────

def canary_5_habitat_discovery(root: Path) -> Dict[str, Any]:
    from aurora_habitat import HabitatRuntime
    import inspect
    import aurora_representational_resolution as rr_mod

    genealogy = ConstraintGenealogyLogger("canary5", config=GenealogyConfig(), output_dir=str(root / "canary5" / "g"))
    systems = {"genealogy": genealogy, "state_dir": str(root / "canary5" / "state")}
    habitat = HabitatRuntime(str(root / "canary5" / "state"), systems=systems)

    # Aurora creates two objects using ONLY neutral Habitat affordances.
    a = habitat.act(actor="aurora", territory="space", operation="create",
                     parameters={"entity_type": "shape"}).affected_entities[0]
    b = habitat.act(actor="aurora", territory="space", operation="create",
                     parameters={"entity_type": "shape"}).affected_entities[0]

    # A human repeatedly interacts with A and ignores B -- pure gesture
    # data, no code anywhere states what this "means."
    for i in range(5):
        habitat.act(actor="human", territory="space", operation="move",
                    target_ids=[a], parameters={"position": {"x": i, "y": 0}})

    from aurora_representational_resolution import get_or_create_engine
    engine = get_or_create_engine(systems)
    ref = RepresentationalRef.for_c1("N", "OPERATOR", "A")  # change-category habitat ops
    profile = engine.consequence_profile_for(ref) if engine else None

    habitat_src = inspect.getsource(__import__("aurora_habitat"))
    resolution_src = inspect.getsource(rr_mod)
    no_meaning_anywhere = (
        '"meaning"' not in habitat_src and ".meaning =" not in habitat_src
        and '"meaning"' not in resolution_src and ".meaning =" not in resolution_src
    )
    return {
        "name": "habitat_discovery",
        "entities": {"touched": a, "ignored": b},
        "consequence_profile_samples": (profile or {}).get("samples", 0),
        "no_meaning_anywhere": no_meaning_anywhere,
        "passed": bool(profile) and profile.get("samples", 0) > 0 and no_meaning_anywhere,
    }


def run_all() -> Dict[str, Dict[str, Any]]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        results = {
            "canary_1": canary_1_stable_coarse_history(root),
            "canary_2": canary_2_divergent_history(root),
            "canary_3": canary_3_refinement_pays_off(root),
            "canary_4": canary_4_refinement_does_not_pay_off(root),
            "canary_5": canary_5_habitat_discovery(root),
        }
    return results


if __name__ == "__main__":
    results = run_all()
    for key, result in results.items():
        status = "PASS" if result.get("passed") else "FAIL"
        print(f"[{status}] {key}: {result.get('name')}")
        for k, v in result.items():
            if k in ("name", "passed"):
                continue
            print(f"    {k}: {v}")
    all_passed = all(r.get("passed") for r in results.values())
    print(f"\n{'ALL CANARIES PASSED' if all_passed else 'SOME CANARIES FAILED'}")

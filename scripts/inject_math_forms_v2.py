# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
inject_math_forms_v2.py

Upgrades v1's generic axis-letter formulas into combinatory-specific,
numerically-grounded ones, and adds a development-tracking scaffold.

Fixes vs v1:
1. Combinatory meaning: each noncomp's existing `nc_semantic_summary` (what
   this Law x Dimension actually means) and `nc_domain` (what concrete
   quantity the Target represents -- Information / Belief / Purpose /
   Meaning / Understanding, already present in the file) are woven into the
   formula, so "A(t)" reads as "Agency's ownership-pressure on Information"
   instead of a bare letter.
2. Real coefficients, not symbols: `formula_coefficient` is computed from
   data already inside the noncomp's own `slots` array (mean
   accountability_weight across slots whose col_law_c matches this noncomp's
   nc_law_c) -- sourced from the file itself, nothing invented.
3. Development tracking: adds a `development_tracking` scaffold with an
   empty `history` list and a `sink` pointer to the real, already-existing
   PressureExperienceLedger.record() in aurora_internal/aurora_pressure_ledger.py,
   so measured values over time have somewhere real to land instead of a
   made-up API.

Only run this AFTER v1 (inject_math_forms.py) or on a fresh copy -- it reads
nc_semantic_summary / nc_domain / slots that v1 does not touch, and adds
new keys alongside v1's mathematical_form/formula rather than requiring them.
"""
from __future__ import annotations
import json
import statistics
from pathlib import Path

DIMENSION_ROLE = {
    "OPERATOR":   "X",
    "POLARITY":   "A",
    "MAGNITUDE":  "B",
    "COST":       "N",
    "DIFFERENCE": "T",
}

AXIS_NAME = {
    "X": "Existence",
    "T": "Temporal",
    "N": "Energetic",
    "B": "Boundary",
    "A": "Agentive",
}


def compute_coefficient(data: dict) -> float:
    """Mean accountability_weight across slots whose col_law_c matches this
    noncomp's own nc_law_c -- i.e. how much weight this Law actually carries
    across its own representational encodings inside this noncomp, per data
    already present in the file."""
    law_c = data.get("nc_law_c")
    slots = data.get("slots", [])
    matching = [s["accountability_weight"] for s in slots if s.get("col_law_c") == law_c]
    if not matching:
        return 0.0
    return round(statistics.mean(matching), 4)


def build_formula_v2(data: dict) -> dict:
    L = data["nc_law_c"]
    D = data["nc_dim"]
    C = data["nc_target"]
    domain = data.get("nc_domain", AXIS_NAME[C])
    semantic = data.get("nc_semantic_summary", "").rstrip(".")
    is_diag = bool(data.get("nc_is_diagonal", False))
    coeff = compute_coefficient(data)

    concrete_L = f"{AXIS_NAME[L]}'s {semantic[0].lower()}{semantic[1:]}" if semantic else AXIS_NAME[L]

    if is_diag:
        formula = f"{C}(t)"
        math_form = (
            f"Self-application anchor: {domain}'s own state as the operator "
            f"term inside d{C}/dt. {concrete_L}, applied to itself."
        )
        return {
            "mathematical_form": math_form,
            "formula": formula,
            "formula_role": DIMENSION_ROLE[D],
            "formula_coefficient": coeff,
            "concrete_state_meaning": f"{domain} measured through: {semantic}.",
        }

    if D == "OPERATOR":
        formula = f"{coeff} * {L}(t)   [driving term in d{C}/dt]"
        math_form = (
            f"{concrete_L}, entering {domain}'s ({C}'s) equation as the "
            f"operator it is measured through -- weight {coeff} sourced from "
            f"this noncomp's own accountability data."
        )
    elif D == "POLARITY":
        formula = f"sgn(d{L}/dt) * {coeff}   [direction gate on {L}->{C}]"
        math_form = (
            f"Whether {concrete_L} is currently rising or falling determines "
            f"if it adds to or drains {domain} ({C}); gate strength {coeff}."
        )
    elif D == "MAGNITUDE":
        formula = f"{coeff} * |{L}(t)|   [scaled pressure on {C}]"
        math_form = (
            f"How strongly {concrete_L} presses on {domain} ({C}), scaled by "
            f"{coeff} -- the measured weight of this Law's own encodings "
            f"within this noncomp."
        )
    elif D == "COST":
        formula = f"{coeff} * |{L}(t)|   [subtracted from d{C}/dt]"
        math_form = (
            f"The metabolic price of {concrete_L} being transmitted into "
            f"{domain} ({C}): {coeff} is paid out of d{C}/dt every tick this "
            f"pressure is active."
        )
    elif D == "DIFFERENCE":
        formula = f"{coeff} * (d{L}/dt)   [temporal gradient feeding {C}]"
        math_form = (
            f"How fast {concrete_L} is changing feeds {domain}'s ({C}'s) own "
            f"rate of change, scaled by {coeff}."
        )
    else:
        raise ValueError(f"Unknown dimension: {D}")

    return {
        "mathematical_form": math_form,
        "formula": formula,
        "formula_role": DIMENSION_ROLE[D],
        "formula_coefficient": coeff,
        "concrete_state_meaning": f"{domain} measured through: {semantic}.",
    }


def process_file(path: Path) -> bool:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not (data.get("nc_law_c") and data.get("nc_dim") and data.get("nc_target")):
        return False

    updated = build_formula_v2(data)
    data.update(updated)

    data["development_tracking"] = {
        "history": [],
        "sink": "PressureExperienceLedger.record() in aurora_internal/aurora_pressure_ledger.py",
        "note": (
            "Each time this noncomp's live value is measured during a boot/"
            "test cycle, append {timestamp, measured_value, session_id} here "
            "and/or forward through PressureExperienceLedger.record() for "
            "permanent tamper-evident tracking."
        ),
    }
    data["_formula_authors"] = "Sunni (Sir) Morningstar & Cael Devo"

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return True


def main(root: str):
    root_path = Path(root)
    total = 0
    for axis in ["X", "T", "N", "B", "A"]:
        axis_dir = root_path / axis
        if not axis_dir.is_dir():
            print(f"WARNING: missing axis dir {axis_dir}")
            continue
        for f in sorted(axis_dir.glob("*.json")):
            if process_file(f):
                total += 1
    print(f"Updated {total} noncomp files under {root_path} (v2 -- combinatory + sourced coefficients)")


if __name__ == "__main__":
    import sys
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "aurora_manifold_directory"
    main(target_dir)

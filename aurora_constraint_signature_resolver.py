# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
aurora_constraint_signature_resolver.py

Pure, dependency-free resolver between a (Law, Dimension, Target) triple and:
  - nc_name             e.g. "Agentive_Cost_of_Existence"
  - lineage_signature   e.g. "AAN"

Formula confirmed against aurora_state/aurora_manifold_directory/*.json:
  lineage_signature = LawLetter + TargetLetter + RoleLetter(dimension)
  nc_name            = f"{LAW_PREFIX[law]}_{DIM_WORD[dim]}_of_{TARGET_SUFFIX[target]}"

This is the shared key that lets Location 2 (constraint_genealogy.py) and
Location 3 (manifold noncomp files) join records to the same noncomp without
guessing -- both sides compute the identical string from the same inputs.
"""
from __future__ import annotations

DIMENSION_ROLE = {
    "OPERATOR":   "A",
    "POLARITY":   "T",
    "MAGNITUDE":  "X",
    "COST":       "N",
    "DIFFERENCE": "B",
}

# Law prefixes as used in nc_name (differ from target suffixes for X and A)
LAW_PREFIX = {
    "X": "Existential",
    "T": "Temporal",
    "N": "Energetic",
    "B": "Boundary",
    "A": "Agentive",
}

TARGET_SUFFIX = {
    "X": "Existence",
    "T": "Temporal",
    "N": "Energetic",
    "B": "Boundary",
    "A": "Agency",
}

DIM_WORD = {
    "POLARITY":   "Polarity",
    "MAGNITUDE":  "Magnitude",
    "OPERATOR":   "Operator",
    "COST":       "Cost",
    "DIFFERENCE": "Difference",
}


def lineage_signature(law: str, dim: str, target: str) -> str:
    """e.g. lineage_signature('A', 'COST', 'A') -> 'AAN'"""
    law, target = law.upper(), target.upper()
    return f"{law}{target}{DIMENSION_ROLE[dim]}"


def nc_name(law: str, dim: str, target: str) -> str:
    """e.g. nc_name('A', 'COST', 'X') -> 'Agentive_Cost_of_Existence'"""
    law, target = law.upper(), target.upper()
    return f"{LAW_PREFIX[law]}_{DIM_WORD[dim]}_of_{TARGET_SUFFIX[target]}"


def parse_nc_name(name: str) -> tuple[str, str, str]:
    """Reverse of nc_name(): 'Agentive_Cost_of_Existence' -> ('A', 'COST', 'X')."""
    law_word, dim_word, _, target_word = name.split("_", 3)
    law = next(k for k, v in LAW_PREFIX.items() if v == law_word)
    dim = next(k for k, v in DIM_WORD.items() if v == dim_word)
    target = next(k for k, v in TARGET_SUFFIX.items() if v == target_word)
    return law, dim, target


if __name__ == "__main__":
    # Self-check under the CORRECTED foundational operator mapping
    # (Architectural Correction Record, Build 725): X=Magnitude, T=Polarity,
    # N=Cost, B=Difference, A=Operator.
    #
    # ⚠ These signature strings (AAN/AAB/AAX/AAA/AAT) are the join keys used
    # against aurora_state/aurora_manifold_directory/*.json per this file's
    # module docstring. That manifold directory data was generated under the
    # OLD (incorrect) mapping. Flipping DIMENSION_ROLE here means the
    # generated signatures below will no longer match whatever is currently
    # on disk in aurora_manifold_directory/ until that data is regenerated
    # or re-verified against this corrected table. Do not treat this
    # self-check passing as proof the manifold directory itself is fixed.
    assert lineage_signature("A", "COST", "A") == "AAN"
    assert lineage_signature("A", "DIFFERENCE", "A") == "AAB"
    assert lineage_signature("A", "MAGNITUDE", "A") == "AAX"
    assert lineage_signature("A", "OPERATOR", "A") == "AAA"
    assert lineage_signature("A", "POLARITY", "A") == "AAT"
    assert nc_name("X", "OPERATOR", "X") == "Existential_Operator_of_Existence"
    assert nc_name("A", "COST", "X") == "Agentive_Cost_of_Existence"
    assert parse_nc_name("Agentive_Cost_of_Existence") == ("A", "COST", "X")
    print("All resolver self-checks passed.")

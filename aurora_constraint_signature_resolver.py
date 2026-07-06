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
    "OPERATOR":   "X",
    "POLARITY":   "A",
    "MAGNITUDE":  "B",
    "COST":       "N",
    "DIFFERENCE": "T",
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
    # Self-check against known values from the actual manifold files
    assert lineage_signature("A", "COST", "A") == "AAN"
    assert lineage_signature("A", "DIFFERENCE", "A") == "AAT"
    assert lineage_signature("A", "MAGNITUDE", "A") == "AAB"
    assert lineage_signature("A", "OPERATOR", "A") == "AAX"
    assert lineage_signature("A", "POLARITY", "A") == "AAA"
    assert nc_name("X", "OPERATOR", "X") == "Existential_Operator_of_Existence"
    assert nc_name("A", "COST", "X") == "Agentive_Cost_of_Existence"
    assert parse_nc_name("Agentive_Cost_of_Existence") == ("A", "COST", "X")
    print("All resolver self-checks passed.")

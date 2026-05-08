#!/usr/bin/env python3
"""
AURORA CODE MUTATION OPERATORS
==============================
Canonical mutation operator catalog for code-level evolution.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Optional


@dataclass(frozen=True)
class CodeMutationOperator:
    key: str
    description: str
    constraints: FrozenSet[str]
    expected_effect: str
    risk: str


_OPERATORS: Dict[str, CodeMutationOperator] = {
    "invariant_guard": CodeMutationOperator(
        key="invariant_guard",
        description="Add or tighten invariant checks and admissibility guards.",
        constraints=frozenset({"existence", "boundary"}),
        expected_effect="Lower X-risk and boundary leakage under change.",
        risk="May increase temporal friction if over-constrained.",
    ),
    "boundary_split": CodeMutationOperator(
        key="boundary_split",
        description="Split overloaded module/function into cleaner interfaces.",
        constraints=frozenset({"boundary", "energy", "temporal"}),
        expected_effect="Lower coupling and maintenance pressure.",
        risk="Migration breakage if interfaces are not updated coherently.",
    ),
    "complexity_trim": CodeMutationOperator(
        key="complexity_trim",
        description="Reduce branch/loop complexity while preserving behavior.",
        constraints=frozenset({"energy", "temporal"}),
        expected_effect="Lower N/T pressure and improve replay stability.",
        risk="Hidden behavior changes if tests are weak.",
    ),
    "state_contract": CodeMutationOperator(
        key="state_contract",
        description="Harden state schema/validation and persistence boundaries.",
        constraints=frozenset({"existence", "temporal", "boundary"}),
        expected_effect="Improves continuity and rollback safety.",
        risk="Can reject legacy state until migration handling is added.",
    ),
    "agency_surface": CodeMutationOperator(
        key="agency_surface",
        description="Introduce lawful steering surface with strict lineage hooks.",
        constraints=frozenset({"agency", "boundary", "existence"}),
        expected_effect="Raises adaptive capability with auditable intent.",
        risk="Can destabilize if agency exceeds constraint gating.",
    ),
    "telemetry_probe": CodeMutationOperator(
        key="telemetry_probe",
        description="Add observability to expose hidden pressure and drift.",
        constraints=frozenset({"temporal", "energy", "agency"}),
        expected_effect="Improves diagnosis and mutation quality over time.",
        risk="May add overhead or noise if metrics are not curated.",
    ),
    "latent_promotion": CodeMutationOperator(
        key="latent_promotion",
        description="Promote lineage-inferred latent operations into real Python surfaces.",
        constraints=frozenset({"existence", "temporal", "agency"}),
        expected_effect="Materializes missing evolved capabilities so they can act on the live stack.",
        risk="Generated methods may be shallow until better target-specific synthesis exists.",
    ),
    "architectural_reflection": CodeMutationOperator(
        key="architectural_reflection",
        description="Generate present-state reflection surfaces for components reshaped by cross-system evolution.",
        constraints=frozenset({"boundary", "agency", "temporal"}),
        expected_effect="Exposes current evolved behavior where the lineage implies architectural drift.",
        risk="Reflection wrappers can overstate capability if downstream wiring is incomplete.",
    ),
    "native_surface_projection": CodeMutationOperator(
        key="native_surface_projection",
        description="Project evolved surfaces back into their native source modules as real exports.",
        constraints=frozenset({"existence", "boundary", "agency"}),
        expected_effect="Makes evolved lineage surfaces present where the architecture actually developed them.",
        risk="Native wrapper injection can increase module surface area and should remain idempotent.",
    ),
}


def list_operator_specs() -> List[CodeMutationOperator]:
    return [_OPERATORS[k] for k in sorted(_OPERATORS.keys())]


def get_operator(key: str) -> Optional[CodeMutationOperator]:
    k = str(key or "").strip().lower()
    if not k:
        return None
    return _OPERATORS.get(k)

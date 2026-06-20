#!/usr/bin/env python3
"""Architectural guard for Aurora's L0-L8 cognitive stack.

The core strength of Aurora's design is that the nine layer modules form a
strict, acyclic dependency ordering: each layer may import only layers below
it. This test parses the import statements of the layer files (statically, via
AST -- no execution, no heavy dependencies) and fails if any layer imports a
higher-numbered layer.

Run standalone (pytest is optional):

    python tests/test_layer_acyclicity.py

Exit code 0 == clean DAG, 1 == an upward/cyclic import was introduced.
"""
from __future__ import annotations

import ast
import os
import sys

# Layer order is authoritative. Index == layer number (L0..L8).
LAYER_MODULES = [
    "foundational_contract",            # L0
    "aurora_ivm",                       # L1
    "aurora_i_state_beings",            # L2
    "aurora_dimensional_systems",       # L3
    "aurora_consciousness_engine",      # L4
    "aurora_expression_perception",     # L5
    "aurora_behavioral_identity",       # L6
    "aurora_simulation_engine",         # L7
    "aurora_governance_persistence_gateway",  # L8
]

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAYER_INDEX = {mod: i for i, mod in enumerate(LAYER_MODULES)}


def _imported_modules(path: str) -> set[str]:
    """Return the set of top-level module names imported by a source file."""
    with open(path, "r", encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=path)

    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            # Ignore relative imports (node.level > 0); they don't cross layers.
            if node.level == 0 and node.module:
                names.add(node.module.split(".")[0])
    return names


def find_upward_imports() -> list[str]:
    """Return human-readable descriptions of any upward layer imports."""
    violations: list[str] = []
    for mod, layer in LAYER_INDEX.items():
        path = os.path.join(REPO_ROOT, f"{mod}.py")
        if not os.path.exists(path):
            violations.append(f"MISSING layer module: {mod}.py (expected L{layer})")
            continue
        for imported in _imported_modules(path):
            imported_layer = LAYER_INDEX.get(imported)
            if imported_layer is not None and imported_layer > layer:
                violations.append(
                    f"L{layer} ({mod}) imports L{imported_layer} ({imported}) "
                    f"-- upward import breaks the acyclic stack"
                )
    return violations


def test_layers_are_acyclic() -> None:
    """pytest entry point."""
    violations = find_upward_imports()
    assert not violations, "Layer ordering violated:\n  " + "\n  ".join(violations)


if __name__ == "__main__":
    found = find_upward_imports()
    if found:
        print("FAIL: L0-L8 layer ordering violated:")
        for v in found:
            print(f"  - {v}")
        sys.exit(1)
    print(f"OK: all {len(LAYER_MODULES)} layer modules respect acyclic L0-L8 ordering.")
    sys.exit(0)

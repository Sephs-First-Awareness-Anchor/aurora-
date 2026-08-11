# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA BUILD 646 GENEALOGY-TO-EVOLUTION CLOSURE DIRECTIVE, Phase 4
Requirement 4.1: lineage-scoped pressure aggregation. Repeated failure
(rejected mutation attempts) involving a target's operational
DESCENDANTS must increase pressure specifically on that target's
lineage -- not on unrelated functions, and not as a single opaque
global counter. Deliberately does NOT attempt to map conversational/
dream fail-stream dimensions onto function_ids (see the module
docstring in aurora_evolutionary_ancestry_bridge.lineage_scoped_pressure
for why that boundary is left unresolved rather than invented).
"""
import os
import sys
import tempfile
import textwrap

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_internal.aurora_code_evolution_chamber import CodeEvolutionChamber
from aurora_internal.aurora_universal_function_lineage import UniversalFunctionLineage
from aurora_internal.aurora_evolutionary_ancestry_bridge import lineage_scoped_pressure


def _write(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(content))


def _repo(tmp: str) -> None:
    _write(os.path.join(tmp, "ancestor.py"), """
        def ancestor_fn(x):
            return x + 1
    """)
    _write(os.path.join(tmp, "descendant.py"), """
        from ancestor import ancestor_fn

        def descendant_fn(x):
            return ancestor_fn(x) * 2
    """)
    _write(os.path.join(tmp, "unrelated.py"), """
        def unrelated_fn(x):
            return x - 1
    """)


class TestRepeatedFailureAmongDescendantsRaisesPressureOnTheAncestor:
    def test_rejected_attempts_against_a_descendant_are_counted_in_ancestor_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            _repo(tmp)
            ancestor_file = os.path.join(tmp, "ancestor.py")
            descendant_file = os.path.join(tmp, "descendant.py")
            unrelated_file = os.path.join(tmp, "unrelated.py")

            lineage = UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=True)
            chamber = CodeEvolutionChamber(repo_root=tmp, output_dir=os.path.join(tmp, "out"))

            # A rejected (no-op, no genuine relief) attempt against the
            # DESCENDANT file.
            before = chamber.snapshot(target_files=[descendant_file])
            rejected_trace = chamber.propose_mutation(
                name="pointless_descendant_change", constraints_used=["existence"],
                target_files=[descendant_file], function_lineage=lineage,
            )
            rejected_result = chamber.evaluate_mutation(trace=rejected_trace, before=before, checks_passed=True)
            assert rejected_result["accepted"] is False

            # An unrelated function's rejected attempt must NOT count
            # toward the ancestor's scoped pressure.
            before_u = chamber.snapshot(target_files=[unrelated_file])
            unrelated_trace = chamber.propose_mutation(
                name="pointless_unrelated_change", constraints_used=["existence"],
                target_files=[unrelated_file], function_lineage=lineage,
            )
            chamber.evaluate_mutation(trace=unrelated_trace, before=before_u, checks_passed=True)

            pressure = lineage_scoped_pressure(
                function_lineage=lineage,
                mutation_lineage=chamber._mutation_lineage,
                target_files=[ancestor_file],
                repo_root=tmp,
            )
            assert pressure["descendant_scope_count"] >= 1
            assert rejected_trace.mutation_id in pressure["rejected_mutation_ids_in_scope"]
            assert unrelated_trace.mutation_id not in pressure["rejected_mutation_ids_in_scope"]
            assert unrelated_trace.mutation_id not in pressure["accepted_mutation_ids_in_scope"]

    def test_pressure_evidence_is_decomposable_not_a_single_opaque_score(self):
        """Phase 9: the returned evidence must stay inspectable field-by-
        field, never collapsed into one magic number."""
        with tempfile.TemporaryDirectory() as tmp:
            _repo(tmp)
            lineage = UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=True)
            pressure = lineage_scoped_pressure(
                function_lineage=lineage,
                mutation_lineage={},
                target_files=[os.path.join(tmp, "ancestor.py")],
                repo_root=tmp,
            )
            expected_fields = {
                "target_function_ids", "descendant_scope_count",
                "rejected_count_in_scope", "accepted_count_in_scope",
                "rejected_mutation_ids_in_scope", "accepted_mutation_ids_in_scope",
            }
            assert expected_fields.issubset(pressure.keys())
            assert isinstance(pressure["rejected_count_in_scope"], int)

    def test_propose_mutation_attaches_lineage_scoped_pressure_as_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            _repo(tmp)
            ancestor_file = os.path.join(tmp, "ancestor.py")
            lineage = UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=True)
            chamber = CodeEvolutionChamber(repo_root=tmp, output_dir=os.path.join(tmp, "out"))

            trace = chamber.propose_mutation(
                name="probe", constraints_used=["existence"],
                target_files=[ancestor_file], function_lineage=lineage,
            )
            assert "lineage_scoped_pressure" in trace.meta
            assert "rejected_count_in_scope" in trace.meta["lineage_scoped_pressure"]

# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA BUILD 648 EVOLUTIONARY INFRASTRUCTURE CLOSURE DIRECTIVE, Phase 3:
CodeMutationTrace previously identified mutation scope only through
target_files, and acquire_ancestry_for_target() always expanded a
target file into EVERY function UniversalFunctionLineage knows lives in
it -- coarse when a single file holds many independently meaningful
operations. This tests that:
  1. exact_function_ids, when supplied and resolvable, narrows ancestry
     acquisition to precisely those functions (not the whole file).
  2. requested_operation_ids (opaque operation-descriptor evidence) is
     recorded without being used to infer ancestry.
  3. file-level compatibility remains the explicit fallback -- never
     silently mislabeled as exact.
  4. an unresolvable exact_function_id is dropped, not fabricated into
     ancestry.
"""
import os
import sys
import tempfile
import textwrap

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_internal.aurora_code_evolution_chamber import CodeEvolutionChamber
from aurora_internal.aurora_universal_function_lineage import UniversalFunctionLineage
from aurora_internal.aurora_evolutionary_ancestry_bridge import acquire_ancestry_for_target


def _write(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(content))


def _multi_op_file(tmp: str) -> str:
    target = os.path.join(tmp, "many_ops.py")
    _write(target, """
        def op_alpha(x):
            return x + 1

        def op_beta(x):
            return x + 2

        def op_gamma(x):
            return x + 3
    """)
    return target


class TestExactFunctionIdsNarrowAncestryScope:
    def test_exact_scope_resolves_only_the_named_function_not_the_whole_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = _multi_op_file(tmp)
            lineage = UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=True)
            alpha_fid = next(fid for fid in lineage.all_functions() if fid.endswith("op_alpha"))

            file_level = acquire_ancestry_for_target(
                function_lineage=lineage, mutation_lineage={},
                target_files=[target], repo_root=tmp,
            )
            assert file_level.ancestry_scope == "file_level_fallback"
            assert len(file_level.resolved_function_ids) == 3

            exact = acquire_ancestry_for_target(
                function_lineage=lineage, mutation_lineage={},
                target_files=[target], repo_root=tmp,
                exact_function_ids=[alpha_fid],
            )
            assert exact.ancestry_scope == "exact"
            assert exact.resolved_function_ids == [alpha_fid]

    def test_propose_mutation_marks_exact_scope_in_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = _multi_op_file(tmp)
            lineage = UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=True)
            beta_fid = next(fid for fid in lineage.all_functions() if fid.endswith("op_beta"))
            chamber = CodeEvolutionChamber(repo_root=tmp, output_dir=os.path.join(tmp, "out"))

            trace = chamber.propose_mutation(
                name="narrow", constraints_used=["energy"], target_files=[target],
                function_lineage=lineage, exact_function_ids=[beta_fid],
            )
            assert trace.meta["mutation_scope_kind"] == "exact"
            acquired = trace.meta["acquired_operational_ancestry"]
            assert acquired["resolved_function_ids"] == [beta_fid]
            assert acquired["ancestry_scope"] == "exact"


class TestFileLevelFallbackStaysExplicit:
    def test_no_exact_ids_supplied_is_labeled_file_level_fallback_not_exact(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = _multi_op_file(tmp)
            lineage = UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=True)
            chamber = CodeEvolutionChamber(repo_root=tmp, output_dir=os.path.join(tmp, "out"))

            trace = chamber.propose_mutation(
                name="coarse", constraints_used=["energy"], target_files=[target],
                function_lineage=lineage,
            )
            assert trace.meta["mutation_scope_kind"] == "file_level_fallback"
            assert trace.meta["acquired_operational_ancestry"]["ancestry_scope"] == "file_level_fallback"
            assert len(trace.meta["acquired_operational_ancestry"]["resolved_function_ids"]) == 3


class TestUnresolvableExactIdIsDroppedNotFabricated:
    def test_nonexistent_function_id_yields_empty_resolution_not_invented_ancestry(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = _multi_op_file(tmp)
            lineage = UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=True)

            result = acquire_ancestry_for_target(
                function_lineage=lineage, mutation_lineage={},
                target_files=[target], repo_root=tmp,
                exact_function_ids=["many_ops.this_function_does_not_exist"],
            )
            assert result.ancestry_scope == "exact"
            assert result.resolved_function_ids == []
            assert result.ancestry_status == "unknown"


class TestRequestedOperationIdsAreRecordedAsEvidenceOnly:
    def test_operation_descriptor_ids_recorded_without_shaping_ancestry(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = _multi_op_file(tmp)
            lineage = UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=True)
            chamber = CodeEvolutionChamber(repo_root=tmp, output_dir=os.path.join(tmp, "out"))

            trace = chamber.propose_mutation(
                name="descriptor_evidence", constraints_used=["energy"], target_files=[target],
                function_lineage=lineage,
                requested_operation_ids=["evolved.latent_anchor_action_consequence"],
            )
            assert trace.meta["requested_operation_ids"] == ["evolved.latent_anchor_action_consequence"]
            # File-level fallback is unaffected by the presence of opaque
            # operation-descriptor evidence -- no homology inferred from it.
            assert trace.meta["mutation_scope_kind"] == "file_level_fallback"


class TestBackwardCompatibilityWithoutFunctionLineage:
    def test_no_function_lineage_still_records_requested_scope_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = _multi_op_file(tmp)
            chamber = CodeEvolutionChamber(repo_root=tmp, output_dir=os.path.join(tmp, "out"))
            trace = chamber.propose_mutation(
                name="no_lineage", constraints_used=["energy"], target_files=[target],
            )
            assert trace.meta["requested_target_files"] == [target]
            assert trace.meta["mutation_scope_kind"] == "file_level_fallback"
            assert "acquired_operational_ancestry" not in trace.meta

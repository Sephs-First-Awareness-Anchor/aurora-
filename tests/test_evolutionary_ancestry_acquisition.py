# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA BUILD 646 GENEALOGY-TO-EVOLUTION CLOSURE DIRECTIVE, Requirement
2.2/2.3, Phase 16 Categories C and D: evolutionary proposals must be
capable of acquiring real operational ancestry from Aurora's genealogy
automatically, without requiring a caller to manually supply the entire
family structure -- while explicit legacy parent_ids remain valid and
are never silently overwritten.

Uses a small synthetic repo fixture (see test_genealogy_source_freshness.py)
so this suite stays fast.
"""
import os
import sys
import tempfile
import textwrap

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_internal.aurora_universal_function_lineage import UniversalFunctionLineage
from aurora_internal.aurora_code_evolution_chamber import CodeEvolutionChamber
from aurora_internal.aurora_evolutionary_ancestry_bridge import (
    acquire_ancestry_for_target, auto_parent_ids, functions_in_files,
)


def _write(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(content))


def _small_repo(tmp: str) -> None:
    _write(os.path.join(tmp, "alpha.py"), """
        def root_x():
            return 1

        def uses_root_x():
            return root_x() + 1

        def uses_uses_root_x():
            return uses_root_x() + 1
    """)


class TestEvidenceDerivedFromRealGenealogy:
    def test_functions_in_files_resolves_real_function_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            _small_repo(tmp)
            lineage = UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=False)
            fids = functions_in_files(lineage, ["alpha.py"], tmp)
            assert len(fids) == 3
            assert any("root_x" in fid for fid in fids)

    def test_acquire_ancestry_derives_operational_parents_and_descendants(self):
        with tempfile.TemporaryDirectory() as tmp:
            _small_repo(tmp)
            lineage = UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=False)
            ancestry = acquire_ancestry_for_target(
                function_lineage=lineage, mutation_lineage={}, target_files=["alpha.py"], repo_root=tmp,
            )
            assert ancestry.ancestry_status == "resolved"
            assert ancestry.resolved_function_ids
            assert ancestry.constraint_signature  # real X/T/N/B/A weights, not fabricated

    def test_no_evidence_when_target_absent_from_lineage_is_honestly_unknown(self):
        """Requirement 2.2: do not invent ancestry when evidence is absent."""
        with tempfile.TemporaryDirectory() as tmp:
            _small_repo(tmp)
            lineage = UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=False)
            ancestry = acquire_ancestry_for_target(
                function_lineage=lineage, mutation_lineage={},
                target_files=["nonexistent_file_never_scanned.py"], repo_root=tmp,
            )
            assert ancestry.ancestry_status == "unknown"
            assert ancestry.resolved_function_ids == []
            assert ancestry.operational_ancestors == []


class TestEvolutionaryProposalsAcquireRealAncestryAutomatically:
    def test_mutation_against_target_acquires_ancestry_without_manual_parent_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            _small_repo(tmp)
            lineage = UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=False)
            chamber = CodeEvolutionChamber(repo_root=tmp, output_dir=os.path.join(tmp, "out"))

            trace = chamber.propose_mutation(
                name="mut1",
                constraints_used=["existence"],
                target_files=["alpha.py"],
                function_lineage=lineage,
            )
            assert "acquired_operational_ancestry" in trace.meta
            acquired = trace.meta["acquired_operational_ancestry"]
            assert acquired["ancestry_status"] == "resolved"
            assert acquired["resolved_function_ids"]

    def test_second_mutation_against_same_target_inherits_first_accepted_mutation(self):
        """The critical regression: a proposal against a target that
        already has a real accepted evolutionary history must acquire
        that history as its parentage automatically."""
        with tempfile.TemporaryDirectory() as tmp:
            _small_repo(tmp)
            lineage = UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=False)
            chamber = CodeEvolutionChamber(repo_root=tmp, output_dir=os.path.join(tmp, "out"))

            gen1 = chamber.propose_mutation(
                name="gen1", constraints_used=["existence"], target_files=["alpha.py"],
                function_lineage=lineage,
            )
            # Simulate acceptance registration (what finalize_code_mutation
            # does via observe_mutation -> self._mutation_lineage[...]).
            chamber._mutation_lineage[gen1.mutation_id] = {
                "mutation_id": gen1.mutation_id, "accepted": True,
                "target_files": list(gen1.target_files), "generation": gen1.meta["lineage_generation"],
            }

            gen2 = chamber.propose_mutation(
                name="gen2", constraints_used=["existence"], target_files=["alpha.py"],
                function_lineage=lineage,
            )
            assert gen1.mutation_id in gen2.parent_ids
            assert gen2.meta["lineage_generation"] == gen1.meta["lineage_generation"] + 1

    def test_rejected_mutation_does_not_become_automatic_parentage(self):
        """A rejected mutation must not silently become the parent of the
        next proposal (that would misrepresent what generation the new
        proposal continues from) -- but it remains discoverable separately."""
        with tempfile.TemporaryDirectory() as tmp:
            _small_repo(tmp)
            lineage = UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=False)
            chamber = CodeEvolutionChamber(repo_root=tmp, output_dir=os.path.join(tmp, "out"))

            failed = chamber.propose_mutation(
                name="failed_attempt", constraints_used=["existence"], target_files=["alpha.py"],
                function_lineage=lineage,
            )
            chamber._mutation_lineage[failed.mutation_id] = {
                "mutation_id": failed.mutation_id, "accepted": False,
                "target_files": list(failed.target_files), "generation": failed.meta["lineage_generation"],
            }

            next_attempt = chamber.propose_mutation(
                name="next_attempt", constraints_used=["existence"], target_files=["alpha.py"],
                function_lineage=lineage,
            )
            assert failed.mutation_id not in next_attempt.parent_ids
            acquired = next_attempt.meta["acquired_operational_ancestry"]
            assert failed.mutation_id in acquired["previous_rejected_mutation_ids"]


class TestExplicitParentIdsRemainValidAndAreNeverOverwritten:
    def test_explicit_parent_ids_survive_automatic_ancestry_acquisition(self):
        with tempfile.TemporaryDirectory() as tmp:
            _small_repo(tmp)
            lineage = UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=False)
            chamber = CodeEvolutionChamber(repo_root=tmp, output_dir=os.path.join(tmp, "out"))
            chamber._mutation_lineage["CMUT:would_be_auto_acquired"] = {
                "mutation_id": "CMUT:would_be_auto_acquired", "accepted": True,
                "target_files": ["alpha.py"], "generation": 1,
            }

            trace = chamber.propose_mutation(
                name="explicit_legacy", constraints_used=["existence"], target_files=["alpha.py"],
                parent_ids=["CMUT:legacy_manual_parent"],
                function_lineage=lineage,
            )
            assert trace.parent_ids == ("CMUT:legacy_manual_parent",)
            assert "CMUT:would_be_auto_acquired" not in trace.parent_ids
            assert trace.meta["explicit_parent_ids"] == ["CMUT:legacy_manual_parent"]

    def test_no_function_lineage_supplied_is_fully_backward_compatible(self):
        """A caller that never supplies function_lineage (existing
        production behavior before this pass) must see byte-identical
        parent_ids/meta shape to before this directive, minus the new
        optional acquired_operational_ancestry key."""
        with tempfile.TemporaryDirectory() as tmp:
            chamber = CodeEvolutionChamber(repo_root=tmp, output_dir=os.path.join(tmp, "out"))
            trace = chamber.propose_mutation(
                name="legacy_call", constraints_used=["existence"], target_files=["alpha.py"],
                parent_ids=["CMUT:some_parent"],
            )
            assert trace.parent_ids == ("CMUT:some_parent",)
            assert "acquired_operational_ancestry" not in trace.meta

# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA BUILD 648 EVOLUTIONARY INFRASTRUCTURE CLOSURE DIRECTIVE, Phase 2:
CodeEvolutionChamber already persists mutation lineage to
code_links.json via flush_files(), but a freshly-constructed chamber
previously never read it back -- _mutation_lineage/_lineage_children
always started empty, so a generation-two proposal against a target
with a real, persisted, accepted generation-one ancestor from a PRIOR
process received no automatic parent at all. This proves the true
restart case: destroy the chamber object entirely (not merely re-derive
values from the same in-memory instance) and construct a fresh one
against the same output directory.
"""
import os
import sys
import tempfile
import textwrap

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_internal.aurora_code_evolution_chamber import CodeEvolutionChamber
from aurora_internal.aurora_universal_function_lineage import UniversalFunctionLineage


def _write(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(content))


def _complex_source() -> str:
    src = "def hot_path(x):\n"
    for i in range(30):
        src += f"    if x == {i}:\n        x = x + {i}\n"
    src += "    return x\n"
    return src


class TestAcceptedAncestryOperationalAfterTrueRestart:
    def test_generation_two_auto_acquires_generation_one_from_a_destroyed_and_rebuilt_chamber(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "hot.py")
            _write(target, _complex_source())
            out_dir = os.path.join(tmp, "out")

            lineage = UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=True)
            chamber = CodeEvolutionChamber(repo_root=tmp, output_dir=out_dir)

            before = chamber.snapshot(target_files=[target])
            gen1 = chamber.propose_mutation(
                name="gen1", constraints_used=["energy", "boundary"],
                target_files=[target], function_lineage=lineage,
            )
            _write(target, "def hot_path(x):\n    return x\n")
            result = chamber.evaluate_mutation(trace=gen1, before=before, checks_passed=True)
            assert result["accepted"] is True
            lineage.rebuild()

            gen1_mutation_id = gen1.mutation_id
            del chamber  # true restart: the object, not merely its variables, is gone

            # Fresh objects reading only persisted state.
            lineage2 = UniversalFunctionLineage(repo_root=tmp, auto_build=False, persist=False)
            chamber2 = CodeEvolutionChamber(repo_root=tmp, output_dir=out_dir)

            assert chamber2.restore_report["loaded"] is True
            assert chamber2.restore_report["restored_mutation_count"] >= 1
            assert gen1_mutation_id in chamber2._mutation_lineage

            gen2 = chamber2.propose_mutation(
                name="gen2", constraints_used=["energy"],
                target_files=[target], function_lineage=lineage2,
            )
            assert gen1_mutation_id in gen2.parent_ids
            assert gen2.meta["lineage_generation"] == 2


class TestRejectedEvidenceSurvivesRestartWithoutBecomingParentage:
    def test_rejected_mutation_discoverable_but_never_auto_parent_after_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "stable.py")
            _write(target, "def stable_fn(x):\n    return x\n")
            out_dir = os.path.join(tmp, "out")

            lineage = UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=True)
            chamber = CodeEvolutionChamber(repo_root=tmp, output_dir=out_dir)

            before = chamber.snapshot(target_files=[target])
            rejected_trace = chamber.propose_mutation(
                name="pointless", constraints_used=["existence"],
                target_files=[target], function_lineage=lineage,
            )
            result = chamber.evaluate_mutation(trace=rejected_trace, before=before, checks_passed=True)
            assert result["accepted"] is False
            rejected_id = rejected_trace.mutation_id
            del chamber

            lineage2 = UniversalFunctionLineage(repo_root=tmp, auto_build=False, persist=False)
            chamber2 = CodeEvolutionChamber(repo_root=tmp, output_dir=out_dir)
            assert rejected_id in chamber2._mutation_lineage
            assert chamber2._mutation_lineage[rejected_id]["accepted"] is False

            next_trace = chamber2.propose_mutation(
                name="next_attempt", constraints_used=["existence"],
                target_files=[target], function_lineage=lineage2,
            )
            # Discoverable as prior rejected evidence...
            acquired = next_trace.meta.get("acquired_operational_ancestry", {})
            assert rejected_id in acquired.get("previous_rejected_mutation_ids", [])
            # ...but never auto-acquired as parentage.
            assert rejected_id not in next_trace.parent_ids


class TestMalformedPersistedStateIsRepresentedNotGuessed:
    def test_corrupt_summary_file_does_not_crash_and_reports_unloaded(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = os.path.join(tmp, "out")
            os.makedirs(out_dir, exist_ok=True)
            with open(os.path.join(out_dir, "code_links.json"), "w", encoding="utf-8") as f:
                f.write("{not valid json::")

            chamber = CodeEvolutionChamber(repo_root=tmp, output_dir=out_dir)
            assert chamber.restore_report["attempted"] is True
            assert chamber.restore_report["loaded"] is False
            assert chamber._mutation_lineage == {}

    def test_partially_malformed_entries_are_skipped_individually(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = os.path.join(tmp, "out")
            os.makedirs(out_dir, exist_ok=True)
            import json
            payload = {
                "lineage_nodes": {
                    "CMUT:valid": {"mutation_id": "CMUT:valid", "accepted": True, "target_files": []},
                    "CMUT:bad": "not-a-dict",
                },
                "lineage_children": {},
                "links": {},
                "pair_counts": {},
                "pair_stats": {},
                "operator_gradients": {},
                "summary": {},
            }
            with open(os.path.join(out_dir, "code_links.json"), "w", encoding="utf-8") as f:
                json.dump(payload, f)

            chamber = CodeEvolutionChamber(repo_root=tmp, output_dir=out_dir)
            assert chamber.restore_report["loaded"] is True
            assert "CMUT:valid" in chamber._mutation_lineage
            assert "CMUT:bad" not in chamber._mutation_lineage
            assert chamber.restore_report["skipped_mutation_entries"] == 1

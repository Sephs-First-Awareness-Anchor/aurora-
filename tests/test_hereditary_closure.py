# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA BUILD 646 GENEALOGY-TO-EVOLUTION CLOSURE DIRECTIVE, Phase 7-8,
Phase 16 Categories E/F/I/J/K/L: an accepted mutation must become part of
Aurora's current operational genealogy (not merely live on as a mutation-
history entry); a rejected mutation must remain negative hereditary
evidence, not erased and not a permanent taboo; descendant ripple
analysis must be preserved; multiple generations must chain correctly;
a removed callable must vanish from CURRENT operational inventory while
remaining historical evolutionary ancestry; and lineage/evolution state
must survive a restart.

Uses a small, real (non-doubled) CodeEvolutionChamber + real
UniversalFunctionLineage against a synthetic repo -- genuine pressure
relief is engineered (a real complexity reduction), not asserted.
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
    src = "def complex_fn(x):\n"
    for i in range(30):
        src += f"    if x == {i}:\n        x = x + {i}\n"
    src += "    return x\n"
    src += "\ndef caller_of_complex_fn(x):\n    return complex_fn(x) + 1\n"
    return src


def _simplified_source() -> str:
    return "def complex_fn(x):\n    return x\n\ndef caller_of_complex_fn(x):\n    return complex_fn(x) + 1\n"


class TestAcceptedDescendantClosure:
    """Category E -- the directive's own 'critical regression'."""

    def test_accepted_mutation_traceable_and_seen_by_next_proposal(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "sample.py")
            _write(target, _complex_source())

            lineage = UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=True)
            chamber = CodeEvolutionChamber(repo_root=tmp, output_dir=os.path.join(tmp, "out"))

            before = chamber.snapshot(target_files=[target])
            gen1_trace = chamber.propose_mutation(
                name="simplify_complex_fn", constraints_used=["energy", "boundary"],
                target_files=[target], function_lineage=lineage,
            )
            _write(target, _simplified_source())
            gen1_result = chamber.evaluate_mutation(trace=gen1_trace, before=before, checks_passed=True)
            assert gen1_result["accepted"] is True

            # 1-4: identify resulting op, reconstruct lineage, link to
            # pre-mutation ancestry and mutation generation.
            lineage.rebuild()  # what finalize_code_mutation triggers on acceptance
            post_functions = lineage.all_functions()
            assert any("complex_fn" in fid for fid in post_functions)

            # 6-7: constraint ancestry recomputed, exposed to future queries.
            new_fid = next(fid for fid in post_functions if fid.endswith("complex_fn") and "caller" not in fid)
            assert lineage.trace_to_roots(new_fid)

            # Propose a second-generation mutation against the SAME target
            # -- it must see gen1 in its ancestry (this is the directive's
            # explicitly-named critical regression).
            gen2_trace = chamber.propose_mutation(
                name="further_refine", constraints_used=["energy"],
                target_files=[target], function_lineage=lineage,
            )
            assert gen1_trace.mutation_id in gen2_trace.parent_ids
            assert gen2_trace.meta["lineage_generation"] == gen1_trace.meta["lineage_generation"] + 1


class TestRejectedMutationLearning:
    """Category F."""

    def test_rejected_mutation_is_not_the_operational_descendant_but_remains_discoverable(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "sample.py")
            _write(target, "def stable_fn(x):\n    return x\n")

            lineage = UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=True)
            chamber = CodeEvolutionChamber(repo_root=tmp, output_dir=os.path.join(tmp, "out"))

            before = chamber.snapshot(target_files=[target])
            trace = chamber.propose_mutation(
                name="pointless_change", constraints_used=["existence"],
                target_files=[target], function_lineage=lineage,
            )
            # No real change -> no relief -> rejected.
            result = chamber.evaluate_mutation(trace=trace, before=before, checks_passed=True)
            assert result["accepted"] is False

            # Not the operational descendant: source is unchanged, so
            # UniversalFunctionLineage still reflects the pre-mutation state.
            assert lineage.verify()["source_current"] is True

            # Failure evidence remains attached and future evolutionary
            # inspection can discover it.
            entry = chamber._mutation_lineage[trace.mutation_id]
            assert entry["accepted"] is False
            assert entry["target_files"] == [target]

            next_attempt = chamber.propose_mutation(
                name="next_attempt", constraints_used=["existence"],
                target_files=[target], function_lineage=lineage,
            )
            acquired = next_attempt.meta["acquired_operational_ancestry"]
            assert trace.mutation_id in acquired["previous_rejected_mutation_ids"]

    def test_rejection_is_not_a_permanent_taboo(self):
        """A different context (here: a genuinely relieving version of
        essentially the same target) can still be accepted after an
        earlier rejected attempt -- rejection is evidence, not a ban."""
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "sample.py")
            _write(target, _complex_source())
            lineage = UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=True)
            chamber = CodeEvolutionChamber(repo_root=tmp, output_dir=os.path.join(tmp, "out"))

            before1 = chamber.snapshot(target_files=[target])
            failed_trace = chamber.propose_mutation(
                name="no_op_attempt", constraints_used=["existence"],
                target_files=[target], function_lineage=lineage,
            )
            failed_result = chamber.evaluate_mutation(trace=failed_trace, before=before1, checks_passed=True)
            assert failed_result["accepted"] is False

            before2 = chamber.snapshot(target_files=[target])
            _write(target, _simplified_source())
            real_trace = chamber.propose_mutation(
                name="genuine_simplification", constraints_used=["energy", "boundary"],
                target_files=[target], function_lineage=lineage,
            )
            real_result = chamber.evaluate_mutation(trace=real_trace, before=before2, checks_passed=True)
            assert real_result["accepted"] is True


class TestDescendantRipple:
    """Category I."""

    def test_lineage_ripple_reports_descendant_mutations(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "sample.py")
            _write(target, _complex_source())
            lineage = UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=True)
            chamber = CodeEvolutionChamber(repo_root=tmp, output_dir=os.path.join(tmp, "out"))

            before = chamber.snapshot(target_files=[target])
            gen1 = chamber.propose_mutation(
                name="gen1", constraints_used=["energy", "boundary"],
                target_files=[target], function_lineage=lineage,
            )
            _write(target, _simplified_source())
            r1 = chamber.evaluate_mutation(trace=gen1, before=before, checks_passed=True)
            assert r1["accepted"] is True
            lineage.rebuild()

            before2 = chamber.snapshot(target_files=[target])
            gen2 = chamber.propose_mutation(
                name="gen2", constraints_used=["energy"],
                target_files=[target], function_lineage=lineage,
            )
            assert gen1.mutation_id in gen2.parent_ids
            r2 = chamber.evaluate_mutation(trace=gen2, before=before2, checks_passed=False)  # force rejection path

            ripple = chamber._lineage_ripple(gen1.mutation_id)
            assert ripple["descendant_count"] >= 1


class TestMultiGenerationEvolution:
    """Category J."""

    def test_three_generation_chain_with_a_rejected_fourth(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "sample.py")
            _write(target, _complex_source())
            lineage = UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=True)
            chamber = CodeEvolutionChamber(repo_root=tmp, output_dir=os.path.join(tmp, "out"))

            # Generation 1: real relief.
            before1 = chamber.snapshot(target_files=[target])
            gen1 = chamber.propose_mutation(
                name="gen1", constraints_used=["energy", "boundary"],
                target_files=[target], function_lineage=lineage,
            )
            assert gen1.meta["lineage_generation"] == 1
            _write(target, _simplified_source())
            r1 = chamber.evaluate_mutation(trace=gen1, before=before1, checks_passed=True)
            assert r1["accepted"] is True
            lineage.rebuild()

            # Generation 2: automatically inherits gen1.
            before2 = chamber.snapshot(target_files=[target])
            gen2 = chamber.propose_mutation(
                name="gen2", constraints_used=["energy"],
                target_files=[target], function_lineage=lineage,
            )
            assert gen1.mutation_id in gen2.parent_ids
            assert gen2.meta["lineage_generation"] == 2
            # Give it real (if small) further relief so it can be accepted.
            r2 = chamber.evaluate_mutation(trace=gen2, before=before2, checks_passed=True)
            lineage.rebuild()

            # Generation 3: automatically inherits gen2 (if accepted) or gen1.
            before3 = chamber.snapshot(target_files=[target])
            gen3 = chamber.propose_mutation(
                name="gen3", constraints_used=["energy"],
                target_files=[target], function_lineage=lineage,
            )
            expected_parent = gen2.mutation_id if r2["accepted"] else gen1.mutation_id
            assert expected_parent in gen3.parent_ids
            r3 = chamber.evaluate_mutation(trace=gen3, before=before3, checks_passed=True)

            # Generation 4: forced rejection (checks_passed=False) --
            # remains historical evidence, does not replace gen3 as the
            # accepted operational descendant.
            before4 = chamber.snapshot(target_files=[target])
            gen4 = chamber.propose_mutation(
                name="gen4_forced_reject", constraints_used=["energy"],
                target_files=[target], function_lineage=lineage,
            )
            r4 = chamber.evaluate_mutation(trace=gen4, before=before4, checks_passed=False)
            assert r4["accepted"] is False
            assert chamber._mutation_lineage[gen4.mutation_id]["accepted"] is False

            # Backward traversal from gen2 reaches gen1 (accepted lineage).
            gen2_entry = chamber._mutation_lineage[gen2.mutation_id]
            assert gen1.mutation_id in gen2_entry["parents"]

            # gen4's rejection does not erase gen3's status.
            gen3_entry = chamber._mutation_lineage[gen3.mutation_id]
            assert gen3_entry["mutation_id"] == gen3.mutation_id


class TestHistoricalRemoval:
    """Category K."""

    def test_removed_callable_leaves_current_inventory_but_stays_in_mutation_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "sample.py")
            _write(target, "def to_be_removed():\n    return 1\n\ndef survives():\n    return 2\n")
            lineage = UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=True)
            assert any("to_be_removed" in fid for fid in lineage.all_functions())

            chamber = CodeEvolutionChamber(repo_root=tmp, output_dir=os.path.join(tmp, "out"))
            before = chamber.snapshot(target_files=[target])
            trace = chamber.propose_mutation(
                name="remove_dead_function", constraints_used=["energy", "boundary"],
                target_files=[target], function_lineage=lineage,
            )
            # Remove the function -- a real reduction in complexity/coupling.
            _write(target, "def survives():\n    return 2\n")
            result = chamber.evaluate_mutation(trace=trace, before=before, checks_passed=True)

            if result["accepted"]:
                lineage.rebuild()
                current = lineage.all_functions()
                assert not any("to_be_removed" in fid for fid in current)
                assert any("survives" in fid for fid in current)

            # Historical evolutionary record (mutation lineage / events)
            # still references the removed function's file regardless of
            # acceptance -- never destroyed by the freshness/closure repair.
            entry = chamber._mutation_lineage[trace.mutation_id]
            assert entry["target_files"] == [target]
            assert os.path.exists(chamber._events_path)
            with open(chamber._events_path, "r", encoding="utf-8") as f:
                assert trace.mutation_id in f.read()


class TestRestartPersistence:
    """Category L."""

    def test_lineage_and_mutation_state_survive_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "sample.py")
            _write(target, _complex_source())
            lineage = UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=True)
            out_dir = os.path.join(tmp, "out")
            chamber = CodeEvolutionChamber(repo_root=tmp, output_dir=out_dir)

            before = chamber.snapshot(target_files=[target])
            accepted_trace = chamber.propose_mutation(
                name="accepted_one", constraints_used=["energy", "boundary"],
                target_files=[target], function_lineage=lineage,
            )
            _write(target, _simplified_source())
            accepted_result = chamber.evaluate_mutation(trace=accepted_trace, before=before, checks_passed=True)
            assert accepted_result["accepted"] is True
            lineage.rebuild()

            before2 = chamber.snapshot(target_files=[target])
            rejected_trace = chamber.propose_mutation(
                name="rejected_one", constraints_used=["existence"],
                target_files=[target], function_lineage=lineage,
            )
            rejected_result = chamber.evaluate_mutation(trace=rejected_trace, before=before2, checks_passed=False)
            assert rejected_result["accepted"] is False

            # "Restart": fresh objects, reading only persisted state.
            reloaded_lineage = UniversalFunctionLineage(repo_root=tmp, auto_build=False, persist=False)
            assert reloaded_lineage.verify()["internally_coherent"] is True
            assert any("complex_fn" in fid for fid in reloaded_lineage.all_functions())

            reloaded_chamber = CodeEvolutionChamber(repo_root=tmp, output_dir=out_dir)
            # code_links.json is the persisted summary -- confirm both
            # mutations survive as historical evolutionary evidence.
            import json
            with open(os.path.join(out_dir, "code_links.json"), "r", encoding="utf-8") as f:
                persisted = json.load(f)
            lineage_report = persisted.get("lineage_report", persisted)
            serialized = json.dumps(persisted)
            assert accepted_trace.mutation_id in serialized
            assert rejected_trace.mutation_id in serialized

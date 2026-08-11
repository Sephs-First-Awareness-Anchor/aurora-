# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA BUILD 646 GENEALOGY-TO-EVOLUTION CLOSURE DIRECTIVE, Phase 4
Requirement 4.2, Phase 16 Category G: positive selection must come from
a GENUINE successful consequence -- not a self-predicted or projected
success -- and that evidence must reach the appropriate lineage and be
able to influence subsequent evolutionary history (not merely be
recorded and then ignored).
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


def _complex_source() -> str:
    src = "def hot_path(x):\n"
    for i in range(30):
        src += f"    if x == {i}:\n        x = x + {i}\n"
    src += "    return x\n"
    return src


class TestPositiveSelectionIsGroundedInMeasuredConsequenceNotProjection:
    def test_acceptance_requires_an_actually_measured_before_after_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "hot.py")
            _write(target, _complex_source())
            chamber = CodeEvolutionChamber(repo_root=tmp, output_dir=os.path.join(tmp, "out"))

            before = chamber.snapshot(target_files=[target])
            trace = chamber.propose_mutation(
                name="reduce_branching", constraints_used=["energy"], target_files=[target],
            )
            # Genuine measured change, not a prediction: the file is
            # actually rewritten before evaluate_mutation re-measures it.
            _write(target, "def hot_path(x):\n    return x\n")
            result = chamber.evaluate_mutation(trace=trace, before=before, checks_passed=True)

            assert result["accepted"] is True
            # The acceptance evidence is a real delta between two real
            # measurements, never a self-reported/predicted outcome.
            assert result["pressure_before"] != result["pressure_after"]
            entry = chamber._mutation_lineage[trace.mutation_id]
            assert entry["accepted"] is True

    def test_a_prediction_alone_with_no_measured_relief_is_rejected(self):
        """Merely claiming success (no real file change -> no measured
        relief) must not be treated as a genuine positive consequence."""
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "hot.py")
            _write(target, "def stable(x):\n    return x\n")
            chamber = CodeEvolutionChamber(repo_root=tmp, output_dir=os.path.join(tmp, "out"))

            before = chamber.snapshot(target_files=[target])
            trace = chamber.propose_mutation(
                name="claimed_improvement", constraints_used=["energy"], target_files=[target],
            )
            # No actual file change occurs -- a "success" claim with zero
            # measured relief.
            result = chamber.evaluate_mutation(trace=trace, before=before, checks_passed=True)
            assert result["accepted"] is False


class TestPositiveEvidenceReachesLineageAndInfluencesFutureEvolution:
    def test_genuine_accepted_relief_becomes_discoverable_ancestry_for_the_next_proposal(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "hot.py")
            _write(target, _complex_source())
            lineage = UniversalFunctionLineage(repo_root=tmp, auto_build=True, persist=True)
            chamber = CodeEvolutionChamber(repo_root=tmp, output_dir=os.path.join(tmp, "out"))

            before = chamber.snapshot(target_files=[target])
            trace = chamber.propose_mutation(
                name="reduce_branching", constraints_used=["energy"], target_files=[target],
                function_lineage=lineage,
            )
            _write(target, "def hot_path(x):\n    return x\n")
            result = chamber.evaluate_mutation(trace=trace, before=before, checks_passed=True)
            assert result["accepted"] is True
            lineage.rebuild()

            # Directly query the bridge (as any future evolutionary
            # candidate-formation pass would) -- the genuinely-accepted
            # mutation must appear as prior positive evidence against the
            # same target, and nowhere as a rejection.
            acquired = acquire_ancestry_for_target(
                function_lineage=lineage,
                mutation_lineage=chamber._mutation_lineage,
                target_files=[target],
                repo_root=tmp,
            )
            assert trace.mutation_id in acquired.previous_accepted_mutation_ids
            assert trace.mutation_id not in acquired.previous_rejected_mutation_ids

            # And it actually shapes the NEXT proposal's automatic
            # parentage (Requirement 2.3) -- positive evidence has teeth,
            # it is not merely recorded and ignored.
            next_trace = chamber.propose_mutation(
                name="further_refine", constraints_used=["energy"], target_files=[target],
                function_lineage=lineage,
            )
            assert trace.mutation_id in next_trace.parent_ids

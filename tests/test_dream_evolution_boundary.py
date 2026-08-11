# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA BUILD 646 GENEALOGY-TO-EVOLUTION CLOSURE DIRECTIVE, Phase 12,
Requirement 4.2, Phase 16 Category H: Dream may contribute hypothesis
material to candidate formation, but must not independently certify
evolutionary fitness. This directive requires the prior directive's
"directive_projection" exclusion (an unexecuted steering-directive
projection must not be logged into genealogy as confirmed relief) to
remain intact -- re-verified here in this directive's own regression
context, not merely assumed carried over.
"""
import os
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)


def _summary(episode_id="ep_boundary_test"):
    from aurora_internal.aurora_episode_slip_profiler import EpisodeRubricSummary
    return EpisodeRubricSummary(
        episode_id=episode_id,
        mean_scores={"context_carryover": 0.4, "contradiction_handling": 0.6},
        primary_deficits={"context_carryover": 0.4},
        leverage_candidates={"contradiction_handling": 0.7},
        episode_fitness=0.5, thread_count=10, confidence=0.8,
    )


def _directive(directive_id="dir_boundary_test"):
    from aurora_internal.aurora_structural_pressure_steering import StructuralPressureDirective
    return StructuralPressureDirective(
        directive_id=directive_id, source_episode_ids=["ep_boundary_test"],
        target_domains=["context_carryover"], mutation_bias={"T_exploration": 0.5}, confidence=0.6,
    )


class TestUnexecutedProjectionCannotBecomeConfirmedGenealogy:
    def test_directive_projection_still_excluded_from_format_for_genealogy(self):
        from aurora_internal.aurora_dream_genealogy_bridge import DreamGenealogyBridge

        bridge = DreamGenealogyBridge(storage_dir=tempfile.mkdtemp(prefix="aurora_dream_boundary_"))
        records = bridge.generate_evidence(_summary(), directives=[_directive()])
        assert any(r.evidence_type == "directive_projection" for r in records)

        genealogy_entries = bridge.format_for_genealogy(records)
        projection_ids = {r.evidence_id for r in records if r.evidence_type == "directive_projection"}
        # No genealogy entry may correspond to the unexecuted projection --
        # confirmed by count, matching the exact assertion this pass's own
        # DreamGenealogyBridge fix (format_for_genealogy) was built to satisfy.
        non_projection_count = sum(1 for r in records if r.evidence_type != "directive_projection")
        assert len(genealogy_entries) == non_projection_count
        assert len(genealogy_entries) < len(records)

    def test_directive_projection_is_still_tagged_artificial_seed(self):
        from aurora_internal.aurora_dream_genealogy_bridge import DreamGenealogyBridge

        bridge = DreamGenealogyBridge(storage_dir=tempfile.mkdtemp(prefix="aurora_dream_boundary_"))
        records = bridge.generate_evidence(_summary(), directives=[_directive()])
        projection = next(r for r in records if r.evidence_type == "directive_projection")
        assert projection.origin_tags.get("artificial_seed") is True


class TestExecutedOutcomeEvidenceDoesWriteBack:
    def test_measured_deficit_evidence_reaches_genealogy_format(self):
        """Contrast case: real, measured (not projected) evidence must
        still flow through -- the boundary excludes projections
        specifically, not all dream-derived evidence."""
        from aurora_internal.aurora_dream_genealogy_bridge import DreamGenealogyBridge

        bridge = DreamGenealogyBridge(storage_dir=tempfile.mkdtemp(prefix="aurora_dream_boundary_"))
        records = bridge.generate_evidence(_summary())  # no directives -- measured evidence only
        assert records
        assert all(r.evidence_type != "directive_projection" for r in records)
        genealogy_entries = bridge.format_for_genealogy(records)
        assert len(genealogy_entries) == len(records)

    def test_code_evolution_chamber_accepted_mutation_is_real_measured_evidence(self):
        """A CodeEvolutionChamber acceptance (this directive's own
        hereditary bridge) is grounded in an actually-measured before/after
        pressure snapshot -- never a dream projection -- confirming the
        Phase 6 requirement that compilation/projection alone never grants
        acceptance."""
        import textwrap
        from aurora_internal.aurora_code_evolution_chamber import CodeEvolutionChamber

        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "sample.py")
            src = "def complex_fn(x):\n"
            for i in range(30):
                src += f"    if x == {i}:\n        x = x + {i}\n"
            src += "    return x\n"
            with open(target, "w", encoding="utf-8") as f:
                f.write(src)

            chamber = CodeEvolutionChamber(repo_root=tmp, output_dir=os.path.join(tmp, "out"))
            before = chamber.snapshot(target_files=[target])
            trace = chamber.propose_mutation(name="m", constraints_used=["energy"], target_files=[target])
            with open(target, "w", encoding="utf-8") as f:
                f.write("def complex_fn(x):\n    return x\n")
            result = chamber.evaluate_mutation(trace=trace, before=before, checks_passed=True)
            assert result["accepted"] is True
            # pressure_before/pressure_after are both real measurements of
            # real file content, not predictions.
            assert result["pressure_before"] != result["pressure_after"]

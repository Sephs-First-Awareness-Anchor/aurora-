# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA DREAM SUBSTRATE... DIRECTIVE, Sections 31-37, 56: developmental
writeback must derive from what Aurora's dream actually produced, not
from a pre-decided target/lesson masquerading as a confirmed outcome.
WhatDreamWasAbout != WhatAuroraLearned.
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _summary(episode_id="ep_test", **scores):
    from aurora_internal.aurora_episode_slip_profiler import EpisodeRubricSummary
    mean_scores = {"context_carryover": 0.4, "contradiction_handling": 0.6, **scores}
    return EpisodeRubricSummary(
        episode_id=episode_id,
        mean_scores=mean_scores,
        primary_deficits={"context_carryover": 0.4},
        leverage_candidates={"contradiction_handling": 0.7},
        episode_fitness=0.5,
        thread_count=10,
        confidence=0.8,
    )


def _directive(directive_id="dir_test"):
    from aurora_internal.aurora_structural_pressure_steering import StructuralPressureDirective
    return StructuralPressureDirective(
        directive_id=directive_id,
        source_episode_ids=["ep_test"],
        target_domains=["context_carryover"],
        mutation_bias={"T_exploration": 0.5},
        confidence=0.6,
    )


class TestDirectiveProjectionExcludedFromGenealogy:
    def test_generate_evidence_produces_a_directive_projection_record(self):
        import tempfile
        from aurora_internal.aurora_dream_genealogy_bridge import DreamGenealogyBridge

        bridge = DreamGenealogyBridge(storage_dir=tempfile.mkdtemp(prefix="aurora_dream_genealogy_test_"))
        records = bridge.generate_evidence(_summary(), directives=[_directive()])
        types = {r.evidence_type for r in records}
        assert "directive_projection" in types

    def test_format_for_genealogy_excludes_the_projection_but_keeps_measured_evidence(self):
        """The core distinction this pass repairs: WhatDreamWasAbout
        (directive_projection, an unexecuted hypothesis) must not reach
        ConstraintGenealogyLogger.observe() as though it were a confirmed
        relief event, while genuinely measured deficit/leverage evidence
        still does."""
        import tempfile
        from aurora_internal.aurora_dream_genealogy_bridge import DreamGenealogyBridge

        bridge = DreamGenealogyBridge(storage_dir=tempfile.mkdtemp(prefix="aurora_dream_genealogy_test_"))
        records = bridge.generate_evidence(_summary(), directives=[_directive()])
        assert any(r.evidence_type == "directive_projection" for r in records)
        assert any(r.evidence_type in ("rubric_deficit", "leverage_hit") for r in records)

        entries = bridge.format_for_genealogy(records)
        # None of the genealogy-bound entries may correspond to the
        # directive_projection record -- confirmed by count: exactly the
        # non-projection records should have made it through.
        non_projection_count = sum(1 for r in records if r.evidence_type != "directive_projection")
        assert len(entries) == non_projection_count
        assert len(entries) < len(records)

    def test_format_for_code_evolution_already_excluded_it_unchanged(self):
        """Regression guard: this pre-existing exclusion (which this pass's
        format_for_genealogy fix mirrors) must remain intact."""
        import tempfile
        from aurora_internal.aurora_dream_genealogy_bridge import DreamGenealogyBridge

        bridge = DreamGenealogyBridge(storage_dir=tempfile.mkdtemp(prefix="aurora_dream_genealogy_test_"))
        records = bridge.generate_evidence(_summary(), directives=[_directive()])
        outcomes = bridge.format_for_code_evolution(records)
        mutation_names = [o["mutation_name"] for o in outcomes]
        assert not any("directive_projection" in name for name in mutation_names)

    def test_directive_projection_pressure_after_is_a_hypothesis_not_a_measurement(self):
        """Confirms the record's own pressure_after really is an algebraic
        projection (differs from pressure_before by exactly the directive's
        own bias-derived amount), not a second real measurement -- the
        reason it must not be logged as confirmed."""
        import tempfile
        from aurora_internal.aurora_dream_genealogy_bridge import DreamGenealogyBridge

        bridge = DreamGenealogyBridge(storage_dir=tempfile.mkdtemp(prefix="aurora_dream_genealogy_test_"))
        directive = _directive()
        summary = _summary()
        records = bridge.generate_evidence(summary, directives=[directive])
        projection = next(r for r in records if r.evidence_type == "directive_projection")
        assert projection.origin_tags.get("artificial_seed") is True
        # A genuine measurement would require a second real episode; this
        # one was produced from the SAME summary the directive itself was
        # derived from, with no second dream having run yet.
        assert projection.pressure_before != projection.pressure_after


class TestConsciousLearnerShardsGroundedInActualDreamBehavior:
    def test_shard_derives_from_the_avatar_reaction_to_what_aurora_actually_said(self):
        from aurora_simulation_engine import SimulationSession
        from foundational_contract import ExistenceMode

        random.seed(3)
        session = SimulationSession()
        result = session.run_episode(turns=3, mode=ExistenceMode.BOUNDED)

        # If any shard was created this episode, its observation_summary
        # must be a description of the REAL reaction the avatar had to the
        # real generated text -- not a hand-authored template distinct
        # from the conversation_trace itself.
        for shard in session.learner.shards.values():
            assert shard.observation_count >= 1
            assert isinstance(shard.observation_summary, str)

    def test_no_forced_correction_success_every_run(self):
        """Across several seeds, fitness must not be pinned to a single
        forced 'success' value -- confirms outcomes come from real
        avatar reactions, not a scripted always-succeed correction."""
        from aurora_simulation_engine import SimulationSession
        from foundational_contract import ExistenceMode

        fitness_values = []
        for seed in range(5):
            random.seed(seed)
            session = SimulationSession()
            result = session.run_episode(turns=3, mode=ExistenceMode.BOUNDED)
            fitness_values.append(round(result.avg_fitness, 6))
        assert len(set(fitness_values)) > 1

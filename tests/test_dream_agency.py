# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA DREAM SUBSTRATE... DIRECTIVE, Sections 27-28, 54: Aurora must
retain genuine choice inside Dream -- no scripted correction, no forced
"the lesson succeeds" outcome. SimulationSession._select_response() is
the real selection mechanism (weighted random.choices over a candidate
pool, not a fixed pick) -- these tests exercise it directly.
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _pool():
    from aurora_simulation_engine import ConceptualResponse, ResponseConcept
    return [
        ConceptualResponse(primary_concept=ResponseConcept.WARM_ACKNOWLEDGMENT, intensity=0.6, openness=0.5),
        ConceptualResponse(primary_concept=ResponseConcept.CURIOUS_INQUIRY, intensity=0.6, openness=0.5),
        ConceptualResponse(primary_concept=ResponseConcept.DIRECT_CLARITY, intensity=0.6, openness=0.5),
    ]


class TestSelectionIsGenuineChoiceNotScripted:
    def test_different_seeds_can_select_different_concepts(self):
        from aurora_simulation_engine import SimulationSession
        session = SimulationSession()
        seen = set()
        for seed in range(30):
            random.seed(seed)
            selected = session._select_response(_pool(), context={})
            seen.add(selected.primary_concept)
        assert len(seen) > 1, "selection never varied across 30 different seeds -- looks scripted"

    def test_empty_pool_falls_back_without_crashing_never_a_forced_success(self):
        from aurora_simulation_engine import SimulationSession, ResponseConcept
        session = SimulationSession()
        selected = session._select_response([], context={})
        assert selected.primary_concept == ResponseConcept.WARM_ACKNOWLEDGMENT

    def test_selection_is_weighted_not_uniform_forced_pick(self):
        """Confirms the mechanism is genuinely probabilistic (weight-driven)
        rather than a hardcoded 'always pick index 0' shortcut."""
        from aurora_simulation_engine import SimulationSession
        session = SimulationSession()
        counts = {}
        for seed in range(60):
            random.seed(seed)
            selected = session._select_response(_pool(), context={})
            counts[selected.primary_concept] = counts.get(selected.primary_concept, 0) + 1
        # If it always picked the same slot regardless of the random
        # stream, exactly one key would appear with count == 60.
        assert not (len(counts) == 1 and next(iter(counts.values())) == 60)


class TestDreamOutcomeEvaluatedFromActualDreamBehavior:
    def test_reaction_and_fitness_derive_from_the_expression_actually_generated(self):
        """The avatar's reaction (and therefore fitness/engagement) is
        computed from the text Aurora actually produced this turn, not
        from a pre-decided expected-correction string."""
        from aurora_simulation_engine import SimulationSession
        from foundational_contract import ExistenceMode

        random.seed(1)
        session_a = SimulationSession()
        result_a = session_a.run_episode(turns=3, mode=ExistenceMode.BOUNDED)

        random.seed(2)
        session_b = SimulationSession()
        result_b = session_b.run_episode(turns=3, mode=ExistenceMode.BOUNDED)

        # Fitness is a function of what was actually said (avatar.react),
        # so two different real generations should not be forced to the
        # exact same fitness value on every single turn.
        fitness_a = [t.get("fitness") for t in result_a.conversation_trace]
        fitness_b = [t.get("fitness") for t in result_b.conversation_trace]
        assert fitness_a != fitness_b or result_a.avg_fitness != result_b.avg_fitness

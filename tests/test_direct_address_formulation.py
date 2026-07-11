# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Regression tests for FIX-A008 (fitness-collapse diagnosis, 2026-07-11):

1. `_generate_expression`'s bridge-less fallback used to gate the
   perception-based generation path on `callable(self._live_response_bridge)`
   -- making it unreachable in exactly the bridge-less contexts that needed
   it. It now unconditionally reaches `_formulate_through_perception`
   whenever `self.perception` is available, generating through her real
   RIPPLE / GROUND / FORMULATE pipeline instead of returning a null turn
   (and never through scripted templates).

2. `run_episode()` used to feed every turn's fitness -- including honest
   null turns ('no_expression') -- into `StabilityMetrics`/`governor.update`,
   punishing silence as conversational failure. It now maintains a separate
   `governed_fitness_scores` list that excludes null turns from what the
   governor sees, while `fitness_scores`/`avg_fitness` (L6 identity feed,
   divergence tracking, EpisodeResult) remain unchanged.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aurora_simulation_engine import SimulationSession, ConceptualResponse, ResponseConcept
from foundational_contract import ExistenceMode


class _FakeComposer:
    def __init__(self):
        self.set_context_calls = []

    def set_context(self, keywords):
        self.set_context_calls.append(keywords)


class _FakePerception:
    """Stands in for ExpressionPerceptionEngine -- no live_response_bridge wired."""

    def __init__(self, expression_fn):
        self.composer = _FakeComposer()
        self.ingest_calls = []
        self.express_calls = []
        self._expression_fn = expression_fn

    def ingest_interaction(self, interaction, mode="sim"):
        self.ingest_calls.append((interaction, mode))
        return {}

    def express(self, assembly, i_state="i_is", mode="sim",
                moral_alignment=0.5, intent_match=0.5):
        self.express_calls.append({
            'i_state': i_state, 'mode': mode,
            'intent_match': intent_match, 'coherence': assembly.coherence,
        })
        return {'expression': self._expression_fn(len(self.express_calls))}


def test_bridgeless_path_reaches_perception_formulation_not_null():
    """No live_response_bridge is wired (the exact context the bug made
    unreachable). With self.perception set, _generate_expression must reach
    _formulate_through_perception and return its generated text -- not a
    null turn."""
    perception = _FakePerception(expression_fn=lambda n: "genuinely formulated words")
    sess = SimulationSession(perception=perception)
    assert sess._live_response_bridge is None

    selected = ConceptualResponse(
        primary_concept=ResponseConcept.WARM_ACKNOWLEDGMENT,
        intensity=0.7, openness=0.6,
    )
    context = {'topic': 'trust and repair', 'prompt': 'how do we rebuild trust',
               'expected_tone': 'warm'}

    expression, meta = sess._generate_expression(selected, context, ExistenceMode.BOUNDED)

    assert expression == "genuinely formulated words"
    assert meta['generation_path'] == 'perception_waveform'
    # RIPPLE: the turn's signal was ingested through the real pipeline.
    assert len(perception.ingest_calls) == 1
    assert perception.ingest_calls[0][0]['input'] == 'how do we rebuild trust'
    # GROUND: composer was set to the turn's content field.
    assert perception.composer.set_context_calls == [['trust', 'and', 'repair']]
    # FORMULATE: honest signal levels, not scripted content.
    assert perception.express_calls[0]['coherence'] == 0.7
    assert perception.express_calls[0]['intent_match'] == 0.6


def test_perception_emitting_nothing_still_yields_honest_null_turn():
    """When her ecology formulates nothing, the turn is an honest null --
    never a fallback to canned/scripted text."""
    perception = _FakePerception(expression_fn=lambda n: "")
    sess = SimulationSession(perception=perception)

    selected = ConceptualResponse(primary_concept=ResponseConcept.DIRECT_CLARITY)
    context = {'topic': 'quiet', 'prompt': '', 'expected_tone': 'neutral'}

    expression, meta = sess._generate_expression(selected, context, ExistenceMode.BOUNDED)

    assert expression == ""
    assert meta['generation_path'] == 'no_expression'


def test_governor_receives_only_governed_fitness_excluding_null_turns():
    """run_episode must exclude no_expression turns from what feeds the
    stability governor, while fitness_scores/avg_fitness (L6 identity,
    divergence, EpisodeResult) stay unconstrained."""

    def alternating(n):
        # Odd calls: real generated text. Even calls: honest null turn.
        return f"generated turn {n}" if n % 2 == 1 else ""

    perception = _FakePerception(expression_fn=alternating)
    sess = SimulationSession(perception=perception)

    captured_metrics = []
    original_update = sess.governor.update

    def spy_update(metrics):
        captured_metrics.append(metrics)
        return original_update(metrics)

    sess.governor.update = spy_update

    result = sess.run_episode(turns=4, mode=ExistenceMode.BOUNDED)

    # Some turns were null (empty expression) -- confirm the episode actually
    # produced a mix, otherwise this test proves nothing.
    null_turn_count = sum(
        1 for t in result.conversation_trace if t.get('expression_source') == 'no_expression'
    )
    real_turn_count = len(result.conversation_trace) - null_turn_count
    assert null_turn_count >= 1
    assert real_turn_count >= 1

    assert len(captured_metrics) == 1, "governor.update should fire once with the governed average"
    governed_fitness = [
        t['fitness'] for t in result.conversation_trace
        if t.get('expression_source') != 'no_expression'
    ]
    expected_governed_avg = sum(governed_fitness) / len(governed_fitness)
    assert abs(captured_metrics[0].fitness_mean - expected_governed_avg) < 1e-9
    assert abs(captured_metrics[0].coherence_score - expected_governed_avg) < 1e-9

    # fitness_scores / avg_fitness must remain unconstrained (all turns, incl. null).
    all_turn_fitness = [t['fitness'] for t in result.conversation_trace]
    expected_avg_fitness = sum(all_turn_fitness) / len(all_turn_fitness)
    assert abs(result.avg_fitness - expected_avg_fitness) < 1e-9
    # The governed average must differ from the unconstrained average given
    # a genuine mix of null and real turns with different fitness levels.
    assert captured_metrics[0].fitness_mean != result.avg_fitness


def test_governor_skipped_when_every_turn_is_null():
    """An all-null episode has no conversational evidence at all -- the
    governor update must be skipped entirely rather than fed a punishing
    fitness_mean of near-zero silence."""
    perception = _FakePerception(expression_fn=lambda n: "")
    sess = SimulationSession(perception=perception)

    captured_metrics = []
    original_update = sess.governor.update

    def spy_update(metrics):
        captured_metrics.append(metrics)
        return original_update(metrics)

    sess.governor.update = spy_update

    result = sess.run_episode(turns=3, mode=ExistenceMode.BOUNDED)

    assert all(
        t.get('expression_source') == 'no_expression' for t in result.conversation_trace
    )
    assert captured_metrics == [], "all-null episode must not update the governor at all"

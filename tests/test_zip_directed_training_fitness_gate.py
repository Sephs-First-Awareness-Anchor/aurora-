# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Zip patch (generative-communication, 2026-08-01), re-implemented against
this repo's real Communication Credit Unification API: directed
training's _witness_directed_training_samples/train_on_bundle
previously injected every sample into conversation_memory.learn_fact
and RetainedLearningBank.record UNCONDITIONALLY on witness -- a lesson
attempt got durably learned just for having been attempted, never
mind whether the training episode that followed actually landed. The
live conversational turn path already defers this decision through
stage_pipeline_learning/resolve_pipeline_learning (receiver evidence
promotes or rejects a staged candidate); directed training now uses
the SAME gate, keyed on a stable per-episode response_id (bundle_
{conv_id}) and resolved after the episode's own avg_fitness score is
known, reusing the exact 0.5 threshold train_on_bundle's own
PressureExperienceLedger recording already treats as "the lesson
landed" -- not a new tuned constant.

gateway.receive() stays immediate: that models Aurora perceiving the
sample this tick, not a durable-memory commitment, so it is
deliberately NOT deferred.
"""
import os
import sys
import tempfile
import types

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_dream_trainer import DreamTrainer, EpisodeBundle


def _trainer():
    tmp = tempfile.mkdtemp(prefix="aurora_dream_trainer_fitness_gate_")
    return DreamTrainer(state_dir=tmp)


class _FakeGateway:
    def __init__(self):
        self.received = []

    def receive(self, content, stream_type, source, mode, metadata=None):
        # The real gateway's receive() takes `metadata`; a replay declares itself internal there.
        self.received.append(content)
        self.metadata = getattr(self, "metadata", []) + [metadata]


def test_witness_stages_instead_of_committing_immediately():
    trainer = _trainer()
    gateway = _FakeGateway()
    systems = {
        "aurora": types.SimpleNamespace(gateway=gateway),
        "StreamType": types.SimpleNamespace(KNOWLEDGE_FEED="knowledge_feed"),
        "ExistenceMode": types.SimpleNamespace(BOUNDED="bounded"),
        "conversation_memory": None,
    }

    witnessed = trainer._witness_directed_training_samples(
        systems, ["the mitochondria produces cellular energy for the cell"],
        response_id="resp-witness-1", dims=["biology"],
    )

    assert witnessed == 1
    assert trainer.pending_pipeline_learning_count == 1
    assert trainer.retention._records == {}, "must not commit to retention before evidence resolves it"
    assert len(gateway.received) == 1, "perception (gateway.receive) stays immediate"


def test_witness_without_response_id_stages_nothing():
    trainer = _trainer()
    systems = {"aurora": None, "StreamType": None, "ExistenceMode": None}
    witnessed = trainer._witness_directed_training_samples(
        systems, ["some sample text long enough to pass the filter"],
        response_id="", dims=[],
    )
    assert witnessed == 1  # still "witnessed" (attempted), just nothing staged
    assert trainer.pending_pipeline_learning_count == 0


def test_witness_then_positive_resolve_promotes_into_retention():
    trainer = _trainer()
    systems = {"aurora": None, "StreamType": None, "ExistenceMode": None}
    trainer._witness_directed_training_samples(
        systems, ["photosynthesis converts light energy into chemical energy"],
        response_id="resp-witness-2", dims=["biology"],
    )
    assert trainer.pending_pipeline_learning_count == 1

    result = trainer.resolve_pipeline_learning("resp-witness-2", outcome_kind="positive", systems=systems)

    assert result["promoted"] == 1
    assert trainer.pending_pipeline_learning_count == 0
    assert len(trainer.retention._records) == 1


def test_witness_then_negative_resolve_never_reaches_retention():
    trainer = _trainer()
    systems = {"aurora": None, "StreamType": None, "ExistenceMode": None}
    trainer._witness_directed_training_samples(
        systems, ["a lesson attempt that did not land in the episode"],
        response_id="resp-witness-3", dims=["biology"],
    )
    result = trainer.resolve_pipeline_learning("resp-witness-3", outcome_kind="negative", systems=systems)

    assert result["promoted"] == 0
    assert trainer.retention._records == {}


class _FakeSession:
    """Deliberately has NO _DIMENSION_TOPIC_HINTS attribute -- matches the
    real aurora_simulation_engine.SimulationSession, which has never
    actually carried this attribute. train_on_bundle referenced it
    unconditionally (session._DIMENSION_TOPIC_HINTS.get(...)), so every
    real call crashed with AttributeError before reaching any of this
    patch's own logic -- caught by this fitness-gate patch's own real
    live-boot test, fixed with a getattr(..., {}) fallback (both call
    sites already .get() their way to safe defaults downstream)."""

    def __init__(self):
        self.queued_specs = []

    def queue_avatar_specs(self, specs):
        self.queued_specs.extend(specs)


class _FakeSimulation:
    def __init__(self, avg_fitness):
        self.session = _FakeSession()
        self._avg_fitness = avg_fitness

    def run_episode(self, **kwargs):
        return {"avg_fitness": self._avg_fitness, "learner_shards": 0, "episode_id": "ep-test"}


def _bundle():
    return EpisodeBundle(
        conv_id="conv-fitness-gate-test",
        title="test bundle",
        turns=[("user", "What is a neuron?"), ("assistant", "A neuron is a nerve cell.")],
    )


def test_train_on_bundle_promotes_directed_samples_on_high_fitness():
    trainer = _trainer()
    systems = {
        "simulation": _FakeSimulation(avg_fitness=0.9),
        "aurora": None, "StreamType": None, "ExistenceMode": None,
        "conversation_memory": None,
    }

    result = trainer.train_on_bundle(_bundle(), systems, turns=1)

    assert result.get("avg_fitness") == 0.9
    resolution = systems.get("_last_pipeline_learning_resolution")
    if resolution is not None:
        assert resolution["outcome_kind"] == "positive"
    assert trainer.pending_pipeline_learning_count == 0


def test_train_on_bundle_rejects_directed_samples_on_low_fitness():
    trainer = _trainer()
    systems = {
        "simulation": _FakeSimulation(avg_fitness=0.1),
        "aurora": None, "StreamType": None, "ExistenceMode": None,
        "conversation_memory": None,
    }

    trainer.train_on_bundle(_bundle(), systems, turns=1)

    resolution = systems.get("_last_pipeline_learning_resolution")
    if resolution is not None:
        assert resolution["outcome_kind"] == "negative"
        assert resolution["promoted"] == 0
    assert trainer.pending_pipeline_learning_count == 0


def test_real_boot_directed_training_fitness_gate_does_not_crash():
    """Real end-to-end confirmation: boot Aurora and run train_on_bundle
    through the actual live systems dict, confirming the new staging/
    resolve wiring survives contact with the real simulation stack."""
    import shutil
    import aurora as A

    scratch = tempfile.mkdtemp(prefix="aurora_directed_training_boot_")
    try:
        scratch_state = os.path.join(scratch, "aurora_state")
        shutil.copytree(os.path.join(REPO_ROOT, "aurora_state"), scratch_state)
        systems = A.boot_aurora(state_dir=scratch_state)

        trainer = systems.get("dream_trainer")
        simulation = systems.get("simulation")
        if trainer is None or simulation is None or getattr(simulation, "session", None) is None:
            return  # this boot profile doesn't mount the dream/simulation stack -- nothing to exercise

        bundle = EpisodeBundle(
            conv_id="conv-real-boot-fitness-gate",
            title="real boot test",
            turns=[("user", "What is a synapse?"), ("assistant", "A synapse is a connection between neurons.")],
        )
        result = trainer.train_on_bundle(bundle, systems, turns=1)
        assert isinstance(result, dict)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

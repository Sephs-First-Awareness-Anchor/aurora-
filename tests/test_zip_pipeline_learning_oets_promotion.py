# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Zip patch (generative-communication, 2026-08-01), re-implemented against
this repo's ALREADY-SHIPPED Communication Credit Unification design
(tasks #36-44, FIX-A060..A064) rather than ported verbatim -- the zip's
own StagedLearningCandidate/RetainedLearningBank.stage()/queue_delivery()/
resolve_delivery() family is an earlier, incompatible iteration of the
same feature and would collide with the 4 live call sites that already
depend on DreamTrainer.stage_pipeline_learning's real signature
(response_id=... required kwarg). Two genuinely still-missing pieces
from that earlier iteration, re-implemented here against the real API:

1. RetainedLearningBank.bridge_to_memory(keys=...) -- bridge the SPECIFIC
   records resolve_pipeline_learning just promoted, instead of a generic
   top-N-by-confidence sweep that could skip the ones evidence just
   validated.
2. resolve_pipeline_learning's promotion path now gives definition
   candidates (context_type='definition', already staged live at
   aurora.py:~30437 from working_memory.concept_meanings, format
   "{term} means {meaning}" with term always topic_words[0]) a native
   OETS node instead of leaving them as prose in RetainedLearningBank --
   so a confirmed understanding becomes a reasoning-over-able concept,
   not just a re-surfaceable sentence.
"""
import os
import sys
import tempfile
import types

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_dream_trainer import DreamTrainer, RetainedLearningBank


class _FakeMemory:
    def __init__(self):
        self.learned_facts = []

    def learn_fact(self, fact, source="", confidence=0.5):
        self.learned_facts.append({"fact": fact, "source": source, "confidence": confidence})


class _FakeNode:
    def __init__(self, word):
        self.word = word
        self.definitions = []

    def add_definition(self, text, source="inferred", confidence=0.5):
        self.definitions.append({"text": text, "source": source, "confidence": confidence})


class _FakeOets:
    def __init__(self):
        self.nodes = {}

    def add_node(self, word, role, valence=0.0, meaning="", lineage=""):
        node = self.nodes.setdefault(word, _FakeNode(word))
        return node


def _trainer():
    tmp = tempfile.mkdtemp(prefix="aurora_dream_trainer_test_")
    return DreamTrainer(state_dir=tmp)


def test_bridge_to_memory_with_keys_bridges_only_those_records():
    with tempfile.TemporaryDirectory() as state_dir:
        bank = RetainedLearningBank(state_dir)
        bank.record("the sky over the valley turns orange at dusk", source="test", confidence=0.9)
        bank.record("rivers carve canyons over geologic time", source="test", confidence=0.95)
        target_key = bank._key("the sky over the valley turns orange at dusk")

        memory = _FakeMemory()
        injected = bank.bridge_to_memory(memory, keys=[target_key])

        assert injected == 1
        assert "sky" in memory.learned_facts[0]["fact"]


def test_bridge_to_memory_without_keys_falls_back_to_top_n():
    with tempfile.TemporaryDirectory() as state_dir:
        bank = RetainedLearningBank(state_dir)
        bank.record("a low confidence observation about clouds", source="test", confidence=0.4)
        bank.record("a high confidence observation about mountains", source="test", confidence=0.9)

        memory = _FakeMemory()
        injected = bank.bridge_to_memory(memory, limit=1)

        assert injected == 1
        assert "mountains" in memory.learned_facts[0]["fact"]


def test_definition_candidate_promotion_creates_oets_node():
    trainer = _trainer()
    oets = _FakeOets()
    systems = {"perception": types.SimpleNamespace(oets=oets), "conversation_memory": _FakeMemory()}

    ok = trainer.stage_pipeline_learning(
        "sedimemory means the layered constraint-space memory substrate",
        response_id="resp-def-1", source="working_memory:concept",
        context_type="definition", topic_words=["sedimemory"], turn_tick=1,
    )
    assert ok is True

    result = trainer.resolve_pipeline_learning(
        "resp-def-1", outcome_kind="positive", systems=systems, turn_tick=2,
    )
    assert result["promoted"] == 1
    assert "sedimemory" in oets.nodes
    assert oets.nodes["sedimemory"].definitions
    assert "layered constraint-space memory substrate" in oets.nodes["sedimemory"].definitions[0]["text"]


def test_non_definition_candidate_promotion_does_not_touch_oets():
    trainer = _trainer()
    oets = _FakeOets()
    systems = {"perception": types.SimpleNamespace(oets=oets), "conversation_memory": _FakeMemory()}

    trainer.stage_pipeline_learning(
        "the user prefers concise answers over long explanations",
        response_id="resp-plain-1", source="working_memory", turn_tick=1,
    )
    result = trainer.resolve_pipeline_learning(
        "resp-plain-1", outcome_kind="positive", systems=systems, turn_tick=2,
    )
    assert result["promoted"] == 1
    assert oets.nodes == {}


def test_definition_promotion_also_works_on_candidate_outcomes_path():
    """The claim-level resolution path (candidate_outcomes=) is a
    separate branch in resolve_pipeline_learning from the legacy
    response-level path exercised above -- confirm OETS promotion is
    wired into both, not just one."""
    trainer = _trainer()
    oets = _FakeOets()
    systems = {"perception": types.SimpleNamespace(oets=oets), "conversation_memory": _FakeMemory()}

    trainer.stage_pipeline_learning(
        "warpfield means the resonance traversal layer over crystallized concepts",
        response_id="resp-def-2", source="working_memory:concept",
        context_type="definition", topic_words=["warpfield"], turn_tick=1,
    )
    pending = trainer._pending_pipeline_learning["resp-def-2"]
    candidate_id = pending[0]["candidate_id"]

    result = trainer.resolve_pipeline_learning(
        "resp-def-2", outcome_kind="indeterminate", systems=systems, turn_tick=2,
        candidate_outcomes={candidate_id: "positive"},
    )
    assert result["promoted"] == 1
    assert "warpfield" in oets.nodes


def test_rejected_candidate_never_touches_oets():
    trainer = _trainer()
    oets = _FakeOets()
    systems = {"perception": types.SimpleNamespace(oets=oets), "conversation_memory": _FakeMemory()}

    trainer.stage_pipeline_learning(
        "quasiarch means a candidate architecture the reasoner has not yet committed to",
        response_id="resp-def-3", source="working_memory:concept",
        context_type="definition", topic_words=["quasiarch"], turn_tick=1,
    )
    result = trainer.resolve_pipeline_learning(
        "resp-def-3", outcome_kind="negative", systems=systems, turn_tick=2,
    )
    assert result["promoted"] == 0
    assert oets.nodes == {}


def test_real_boot_pipeline_learning_oets_promotion_does_not_crash_live_turn():
    """Real end-to-end confirmation: boot Aurora, drive the actual live
    stage/resolve call sites in aurora.py through two real turns, and
    confirm nothing crashes with the new OETS-promotion wiring active."""
    import shutil
    import aurora as A

    scratch = tempfile.mkdtemp(prefix="aurora_pipeline_learning_oets_boot_")
    try:
        scratch_state = os.path.join(scratch, "aurora_state")
        shutil.copytree(os.path.join(REPO_ROOT, "aurora_state"), scratch_state)
        systems = A.boot_aurora(state_dir=scratch_state)

        r1 = A.process_external_user_turn(systems, "A dendrite is a branch of a neuron that receives signals.")
        assert r1, "live turn produced no result"
        r2 = A.process_external_user_turn(systems, "Thanks, that's exactly right.")
        assert r2, "live turn produced no result"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

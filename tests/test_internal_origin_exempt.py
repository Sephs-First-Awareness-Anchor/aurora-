"""Training and dream replays are internal events: exempt from the conversational repeat penalty.

Authors: Sunni (Sir) Morningstar and Cael Devo

Sir's decision: a replay is not a repeated environmental input, so entropy's conversational repeat penalty must not
treat it as one. It is still processed in full (and so still costs what processing it costs), and how stale a
rehearsal has become is for the systems that own internal rehearsal, not for this penalty.
"""
import os
import re
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_consciousness_engine import EntropicPressure, _evidence_is_internal_origin  # noqa: E402


def _read(name):
    return open(os.path.join(REPO_ROOT, name), encoding="utf-8").read()


def test_a_producer_declares_internal_origin_in_the_metadata_the_gateway_carries():
    assert _evidence_is_internal_origin({"source_metadata": {"internal_origin": "dream_replay"}}) is True


@pytest.mark.parametrize("evidence", [
    None, 5, "x", [], {}, {"source_metadata": None}, {"source_metadata": {}}, {"source_metadata": "x"},
    {"source_metadata": {"internal_origin": ""}}, {"source_metadata": {"internal_origin": None}},
    {"source": "user", "tone": "neutral", "stream_type": "user_input"},
])
def test_nothing_else_is_internal(evidence):
    """The engine does not guess from a source name or a text tag; only a declaration counts."""
    assert _evidence_is_internal_origin(evidence) is False


def test_the_conversational_stream_really_is_penalised_for_repeating_so_the_exemption_matters():
    from aurora_consciousness_engine import _pattern_signature
    ent = EntropicPressure()
    sig = _pattern_signature("text", "[TRAIN_TXT] the careful heron stands motionless in the cold shallow water")
    for _ in range(6):
        ent.register_input(pattern_signature=sig)
    assert ent.state.coherence < 1.0 and ent.state.novelty < 1.0


def _process_entropy_block():
    src = _read("aurora_consciousness_engine.py")
    start = src.index("if _proc_emotion_gate() and not _evidence_is_internal_origin(evidence):")
    return src[start:start + 1400]


def test_the_engine_skips_BOTH_entropy_paths_for_an_internal_origin():
    block = _process_entropy_block()
    assert "self.entropy.register_input(" in block and "self.entropy.apply(" in block
    assert block.index("not _evidence_is_internal_origin(evidence)") < block.index("self.entropy.register_input(")
    assert block.index("not _evidence_is_internal_origin(evidence)") < block.index("self.entropy.apply(")


def test_only_the_entropy_registration_is_skipped_the_rest_of_the_pipeline_still_runs():
    src = _read("aurora_consciousness_engine.py")
    guard = src.index("if _proc_emotion_gate() and not _evidence_is_internal_origin(evidence):")
    after = src.index("if _proc_thought_gate():", guard)
    assert after > guard, "the thought stage follows the entropy block and is not under the guard"
    assert "_evidence_is_internal_origin" not in src[after:after + 3000].split("def ")[0].replace("def _evidence_is_internal_origin", "")


def test_the_dream_trainer_declares_its_replays_internal():
    src = _read("aurora_dream_trainer.py")
    fn = src[src.index("def _witness_directed_training_samples"):]
    fn = fn[:fn.index("        return witnessed")]
    assert re.search(r'metadata=\{"internal_origin": "dream_replay"\}', fn), "the trainer must declare its own replays"
    assert "gateway.receive(" in fn


def test_the_gateway_carries_declared_metadata_into_evidence():
    src = _read("aurora_governance_persistence_gateway.py")
    assert "evidence['source_metadata'] = dict(packet.metadata)" in src
    assert re.search(r"def receive\(self, content: str,[^)]*metadata: Optional\[Dict\[str, Any\]\] = None", src, re.S)


def test_environmental_producers_are_not_marked_internal():
    """Praxis is the environment; it is deliberately NOT exempt."""
    for name in ("aurora_praxis_bridge.py",):
        assert "internal_origin" not in _read(name)

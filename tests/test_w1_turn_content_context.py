# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
W1 (PF1.6 residue characterization, 2026-07-21): _build_turn_process_
contexts() now registers a "linguistic" ProcessContext carrying the
turn's actual text, real language rather than an administrative-state
summary -- confirmed live that no other registered context (memory,
constraint, identity, curiosity) ever carried the turn's own content,
which meant ThoughtState.unified_interpretation was identical across
unrelated turns and the PropositionFrame "thought" rung never had
anything real to extract from (0/60 on the probe battery).
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_braid_wiring import _build_turn_process_contexts  # noqa: E402


def test_registers_linguistic_context_carrying_the_turn_text():
    systems = {}
    contexts = _build_turn_process_contexts(
        systems, tick=1, user_text="He's a bit nervous around new people.")
    linguistic = [c for c in contexts if c.process_type == "linguistic"]
    assert len(linguistic) == 1
    assert linguistic[0].what_it_is_operating_on == "He's a bit nervous around new people."
    assert linguistic[0].self_relevance == 0.75
    assert set(linguistic[0].axis_signature) == {"X", "T", "A"}


def test_no_linguistic_context_when_user_text_empty():
    systems = {}
    contexts = _build_turn_process_contexts(systems, tick=1, user_text="")
    assert not [c for c in contexts if c.process_type == "linguistic"]


def test_linguistic_context_text_is_truncated_to_200_chars():
    long_text = "word " * 100  # 500 chars
    systems = {}
    contexts = _build_turn_process_contexts(systems, tick=1, user_text=long_text)
    linguistic = [c for c in contexts if c.process_type == "linguistic"][0]
    assert len(linguistic.what_it_is_operating_on) <= 200


def test_degrades_gracefully_never_raises():
    # No systems keys present at all -- every other branch in this
    # function is wrapped in its own try/except; this one must be too.
    contexts = _build_turn_process_contexts({}, tick=0, user_text="fine")
    assert isinstance(contexts, list)

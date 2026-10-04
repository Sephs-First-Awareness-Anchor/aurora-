"""Entropy's repetition check must be able to tell one input from another.

The pattern signature was (mode, hash(payload_type) % 100, hash(payload[:50]) % 100): two of
three components identical for every user turn, the third a hash bucket. Roughly 45% of
unrelated inputs counted as "the same pattern", so nearly every turn took the repetition
penalty (-0.23 coherence per turn, to 0.0 in six turns) and a constant had_meaningful_input
pinned novelty at 1.0 and stagnation at 0.0 through four identical inputs in a row.

Authors: Sunni (Sir) Morningstar and Cael Devo
"""
import os
import random
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_consciousness_engine import EntropicPressure, _pattern_signature  # noqa: E402


def test_the_same_utterance_has_the_same_signature_whatever_its_punctuation_or_case():
    assert _pattern_signature("text", "Hello!") == _pattern_signature("text", "  hello ")
    assert _pattern_signature("text", "What is photosynthesis?") == _pattern_signature("text", "what is photosynthesis")


def test_different_utterances_have_different_signatures():
    assert _pattern_signature("text", "hello") != _pattern_signature("text", "goodbye")
    assert _pattern_signature("text", "hello") != _pattern_signature("other", "hello")


def test_unrelated_inputs_are_never_mistaken_for_repeats():
    """The old signature called ~45% of unrelated pairs 'the same'; against 50 stored patterns
    that was nearly every turn."""
    rng = random.Random(7)
    words = "plants water light sky boundary energy music time gravity moon system help happy blue".split()
    ep = EntropicPressure()
    seen = set()
    for _ in range(300):
        s = " ".join(rng.choice(words) for _ in range(rng.randint(2, 7)))
        if s in seen:
            continue
        seen.add(s)
        ep.apply(1.0, 0.5, had_meaningful_input=True, pattern_signature=_pattern_signature("text", s))
    assert ep.repetition_count == 0


def test_a_repeated_input_is_not_new_information():
    ep = EntropicPressure()
    sig = _pattern_signature("text", "hello")
    ep.apply(1.0, 0.5, had_meaningful_input=True, pattern_signature=sig)
    novelty0, stag0 = ep.state.novelty, ep.state.stagnation_score
    for _ in range(4):
        ep.apply(ep.state.coherence, 0.5, had_meaningful_input=True, pattern_signature=sig)
    assert ep.repetition_count == 4
    assert ep.state.novelty < novelty0, "novelty must fall when the same thing is said again"
    assert ep.state.stagnation_score > stag0, "stagnation must rise when the same thing is said again"


def test_a_fresh_input_restores_novelty_and_relieves_stagnation():
    ep = EntropicPressure()
    sig = _pattern_signature("text", "hello")
    for _ in range(5):
        ep.apply(ep.state.coherence, 0.5, had_meaningful_input=True, pattern_signature=sig)
    low_novelty, high_stag = ep.state.novelty, ep.state.stagnation_score
    ep.apply(ep.state.coherence, 0.5, had_meaningful_input=True,
             pattern_signature=_pattern_signature("text", "something new entirely"))
    assert ep.state.novelty > low_novelty and ep.state.stagnation_score < high_stag


def test_distinct_inputs_cost_only_the_per_tick_decay():
    ep = EntropicPressure()
    for i in range(6):
        ep.apply(ep.state.coherence, 0.5, had_meaningful_input=True,
                 pattern_signature=_pattern_signature("text", f"distinct input number {i} about topic {i * 7}"))
    assert ep.state.coherence >= 1.0 - 6 * EntropicPressure.COHERENCE_DECAY - 1e-9
    assert ep.repetition_count == 0


def test_the_heartbeat_path_without_a_signature_is_unchanged():
    ep = EntropicPressure()
    ep.apply(1.0, 0.5, had_meaningful_input=False)
    assert ep.state.coherence == 1.0 - EntropicPressure.COHERENCE_DECAY
    assert ep.state.stagnation_score == EntropicPressure.STAGNATION_RATE


# ---- the split: an input ARRIVING versus time PASSING ---------------------------------------------------

def _fresh():
    ep = EntropicPressure()
    return ep


def test_a_new_input_registers_without_eroding_anything():
    ep = _fresh()
    c0, a0 = ep.state.coherence, ep.state.alignment
    for i in range(10):
        ep.register_input(_pattern_signature("text", f"a different thing number {i} about topic {i * 3}"))
    assert ep.state.coherence == c0 and ep.state.alignment == a0, "messages no longer age her"
    assert ep.state.novelty == 1.0 and ep.state.stagnation_score == 0.0 and ep.repetition_count == 0


def test_a_repeat_fades_novelty_grows_stagnation_and_costs_coherence():
    ep = _fresh()
    sig = _pattern_signature("text", "hello")
    ep.register_input(sig)
    n0, s0, c0 = ep.state.novelty, ep.state.stagnation_score, ep.state.coherence
    ep.register_input(sig)
    assert ep.repetition_count == 1
    assert ep.state.novelty < n0 and ep.state.stagnation_score > s0
    assert ep.state.coherence == pytest.approx(c0 - EntropicPressure.REPETITION_PENALTY)


def test_a_fresh_input_after_repeats_relieves_stagnation():
    ep = _fresh()
    sig = _pattern_signature("text", "hello")
    for _ in range(6):
        ep.register_input(sig)
    high = ep.state.stagnation_score
    ep.register_input(_pattern_signature("text", "something else entirely"))
    assert ep.state.stagnation_score < high


def test_erosion_is_charged_per_operating_tick():
    ep = _fresh()
    ep.erode(1.0)
    assert ep.state.coherence == pytest.approx(1.0 - EntropicPressure.COHERENCE_DECAY)
    ep.erode(2.5)
    assert ep.state.coherence == pytest.approx(1.0 - 3.5 * EntropicPressure.COHERENCE_DECAY)


def test_an_idle_tick_changes_nothing_so_a_night_does_not_wipe_her():
    ep = _fresh()
    before = (ep.state.coherence, ep.state.alignment, ep.state.novelty, ep.state.stagnation_score, ep.state.tick_count)
    ep.erode(0.0)
    assert (ep.state.coherence, ep.state.alignment, ep.state.novelty, ep.state.stagnation_score,
            ep.state.tick_count) == before


def test_erosion_fades_novelty_and_grows_stagnation_over_operating_time():
    ep = _fresh()
    n0, s0 = ep.state.novelty, ep.state.stagnation_score
    ep.erode(4.0)
    assert ep.state.novelty == pytest.approx(n0 - 4 * EntropicPressure.NOVELTY_DECAY)
    assert ep.state.stagnation_score == pytest.approx(s0 + 4 * EntropicPressure.STAGNATION_RATE)


def test_erosion_drifts_the_alignment_it_is_given_toward_neutral():
    ep = _fresh()
    ep.erode(1.0, current_alignment=0.9)
    assert 0.5 < ep.state.alignment < 0.9
    far = _fresh()
    far.erode(50.0, current_alignment=0.9)
    assert abs(far.state.alignment - 0.5) < abs(ep.state.alignment - 0.5)


def test_vitality_pressure_follows_both_halves():
    ep = _fresh()
    base = ep.state.vitality_pressure
    ep.erode(10.0)
    worn = ep.state.vitality_pressure
    ep.register_input(_pattern_signature("text", "novel input"))
    assert worn > base and ep.state.vitality_pressure < worn


def test_the_legacy_per_call_apply_is_unchanged_for_the_heartbeat():
    ep = _fresh()
    ep.apply(1.0, 0.5, had_meaningful_input=False)
    assert ep.state.coherence == 1.0 - EntropicPressure.COHERENCE_DECAY


def test_the_engine_registers_instead_of_applying_once_the_clock_drives_erosion():
    src = open(os.path.join(REPO_ROOT, "aurora_consciousness_engine.py"), encoding="utf-8").read()
    i = src.index('if getattr(self, "entropy_clock_driven", False):')
    assert "self.entropy.register_input(pattern_signature=sig)" in src[i:i + 900]
    assert "self.entropy.apply(" in src[i:i + 1300], "the legacy path stays for engines booted without a clock"


# ---- one registration per input -------------------------------------------------------------------------

def test_the_second_synthesis_of_an_input_is_marked_as_already_registered():
    """The live turn synthesizes each input twice by design: gateway.receive() with the raw text, then
    _run_reasoning_pipeline's own gw._synthesize() with the recall-enriched text and the dual-strata
    evidence. Both reached entropy, so a repeated message was registered as a repeat twice (about 0.2
    coherence per turn instead of the 0.1 penalty)."""
    src = open(os.path.join(REPO_ROOT, "aurora.py"), encoding="utf-8").read()
    i = src.index("synthesis = gw._synthesize(")
    assert '"input_already_registered": True' in src[i:i + 900]


def test_the_engine_skips_registration_for_an_input_already_registered():
    src = open(os.path.join(REPO_ROOT, "aurora_consciousness_engine.py"), encoding="utf-8").read()
    i = src.index('if getattr(self, "entropy_clock_driven", False):')
    block = src[i:i + 700]
    assert 'evidence.get("input_already_registered")' in block
    assert block.index("input_already_registered") < block.index("self.entropy.register_input(")


def test_the_marker_survives_the_gateways_evidence_merge():
    """_synthesize merges caller evidence UNDER its own ontological keys: only a key of the same name
    could be overridden, and none is named this."""
    src = open(os.path.join(REPO_ROOT, "aurora_governance_persistence_gateway.py"), encoding="utf-8").read()
    assert "evidence = {**extra_evidence, **evidence}" in src
    assert "input_already_registered" not in src[src.index("def _build_evidence"):src.index("def _build_evidence") + 2500]

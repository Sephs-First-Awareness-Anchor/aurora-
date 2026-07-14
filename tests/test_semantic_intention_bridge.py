"""
tests/test_semantic_intention_bridge.py
==========================================
MTSL Phase 5 (2026-07-13): SemanticIntentionBridge -- strategy
selection over the directive's fixed vocabulary, register-rule
helpers (loop/gradient framing, axis-letter hiding), strategy-shift
detection/logging, and the authority-stage applied gate.
"""
import json
import os

from aurora_internal.dual_strata.cers_regulator import CERSVerdict
from aurora_internal.dual_strata.semantic_intention_bridge import (
    STRATEGY_VOCABULARY,
    SemanticIntentionBridge,
    SHADOW_COMPARISON_FILENAME,
    register_hint,
    sanitize_axis_leakage,
    select_strategy,
)


def _verdict(**overrides):
    base = dict(
        permitted=True, semantic_mode=None, response_bias=0.0,
        variant_confidence=0.0, semantic_hesitation=False, semantic_hesitation_proposed=False,
    )
    base.update(overrides)
    return CERSVerdict(**base)


# ---- select_strategy: full vocabulary coverage ----

def test_no_semantic_mode_degrades_to_observe():
    strategy, confidence = select_strategy(_verdict(semantic_mode=None))
    assert strategy == "observe"
    assert confidence == 0.0


def test_ambiguous_with_no_variant_is_clarify():
    strategy, _ = select_strategy(_verdict(semantic_mode="ambiguous", variant_confidence=0.0))
    assert strategy == "clarify"


def test_ambiguous_with_a_real_variant_is_contrast():
    strategy, _ = select_strategy(_verdict(semantic_mode="ambiguous", variant_confidence=0.5))
    assert strategy == "contrast"


def test_undetermined_without_hesitation_is_observe():
    strategy, _ = select_strategy(_verdict(semantic_mode="undetermined", semantic_hesitation=False))
    assert strategy == "observe"


def test_undetermined_with_hesitation_is_abstain():
    strategy, _ = select_strategy(_verdict(semantic_mode="undetermined", semantic_hesitation=True))
    assert strategy == "abstain"


def test_directional_is_explain():
    strategy, _ = select_strategy(_verdict(semantic_mode="directional"))
    assert strategy == "explain"


def test_organized_high_confidence_low_bias_is_act():
    strategy, _ = select_strategy(_verdict(
        semantic_mode="organized", variant_confidence=0.9, response_bias=0.1,
    ))
    assert strategy == "act"


def test_organized_moderate_confidence_is_reflect():
    strategy, _ = select_strategy(_verdict(
        semantic_mode="organized", variant_confidence=0.5, response_bias=0.1,
    ))
    assert strategy == "reflect"


def test_all_seven_vocabulary_strategies_are_reachable():
    reachable = set()
    reachable.add(select_strategy(_verdict(semantic_mode=None))[0])
    reachable.add(select_strategy(_verdict(semantic_mode="ambiguous", variant_confidence=0.0))[0])
    reachable.add(select_strategy(_verdict(semantic_mode="ambiguous", variant_confidence=0.5))[0])
    reachable.add(select_strategy(_verdict(semantic_mode="undetermined", semantic_hesitation=True))[0])
    reachable.add(select_strategy(_verdict(semantic_mode="directional"))[0])
    reachable.add(select_strategy(_verdict(semantic_mode="organized", variant_confidence=0.9, response_bias=0.1))[0])
    reachable.add(select_strategy(_verdict(semantic_mode="organized", variant_confidence=0.5, response_bias=0.1))[0])
    assert reachable == set(STRATEGY_VOCABULARY)


# ---- bias escalation: can only push toward clarify, never override abstain ----

def test_high_bias_escalates_organized_toward_clarify():
    strategy, _ = select_strategy(_verdict(
        semantic_mode="organized", variant_confidence=0.9, response_bias=0.8,
    ))
    assert strategy == "clarify"


def test_high_bias_does_not_override_abstain():
    strategy, _ = select_strategy(_verdict(
        semantic_mode="undetermined", semantic_hesitation=True, response_bias=0.9,
    ))
    assert strategy == "abstain"


def test_strategy_confidence_bounded_0_to_1():
    for mode, conf, bias, hes in [
        ("organized", 1.0, 0.0, False), ("organized", 0.0, 1.0, True),
        ("directional", 0.5, 0.5, False), ("ambiguous", 0.9, 0.9, True),
    ]:
        _s, strategy_confidence = select_strategy(_verdict(
            semantic_mode=mode, variant_confidence=conf, response_bias=bias, semantic_hesitation=hes,
        ))
        assert 0.0 <= strategy_confidence <= 1.0


# ---- register_hint: loops get feedback language, gradients never loops ----

def test_register_hint_circulating_is_feedback_loop():
    assert register_hint("circulating") == "feedback_loop_language"


def test_register_hint_gradient_and_mixed_are_directional_never_loop():
    assert register_hint("gradient") == "directional_language"
    assert register_hint("mixed") == "directional_language"
    assert "loop" not in register_hint("gradient")
    assert "loop" not in register_hint("mixed")


def test_register_hint_quiescent_is_neutral():
    assert register_hint("quiescent") == "neutral_language"


# ---- sanitize_axis_leakage: hide raw axis letters, preserve real prose ----

def test_bare_xtnb_letters_are_stripped():
    out = sanitize_axis_leakage("The X axis shows high T pressure, N over B.")
    assert "X" not in out
    assert " T " not in out
    assert " N " not in out
    assert " B " not in out


def test_bare_mid_sentence_article_a_is_preserved():
    text = "A cat sat on a mat. This is a test."
    assert sanitize_axis_leakage(text) == text


def test_a_near_axis_word_is_stripped():
    assert sanitize_axis_leakage("The A-axis reading spiked.") == "The axis reading spiked."
    assert sanitize_axis_leakage("the axis A moved.") == "the axis moved."


def test_a_in_slash_separated_axis_list_is_stripped():
    out = sanitize_axis_leakage("Consider X/T/N/B/A as the five axes.")
    assert out == "Consider as the five axes."


def test_a_in_comma_separated_axis_list_is_stripped():
    out = sanitize_axis_leakage("N, B, A were all active.")
    assert out == "were all active."


def test_technical_context_bypasses_sanitization_entirely():
    text = "X/T/N/B/A all active."
    assert sanitize_axis_leakage(text, technical_context=True) == text


def test_empty_text_returns_empty():
    assert sanitize_axis_leakage("") == ""


# ---- SemanticIntentionBridge: shift detection, logging, authority gate ----

def test_first_consume_never_marks_a_shift():
    bridge = SemanticIntentionBridge(state_dir=None)
    decision = bridge.consume(_verdict(semantic_mode="directional"), turn_id="t1")
    assert decision.shifted is False
    assert decision.previous_strategy is None


def test_repeated_same_strategy_is_not_a_shift():
    bridge = SemanticIntentionBridge(state_dir=None)
    bridge.consume(_verdict(semantic_mode="directional"), turn_id="t1")
    decision = bridge.consume(_verdict(semantic_mode="directional"), turn_id="t2")
    assert decision.shifted is False


def test_strategy_change_is_a_shift():
    bridge = SemanticIntentionBridge(state_dir=None)
    bridge.consume(_verdict(semantic_mode="directional"), turn_id="t1")
    decision = bridge.consume(_verdict(semantic_mode="ambiguous", variant_confidence=0.0), turn_id="t2")
    assert decision.shifted is True
    assert decision.previous_strategy == "explain"
    assert decision.strategy == "clarify"


def test_stage_1_never_applies():
    bridge = SemanticIntentionBridge(state_dir=None)
    decision = bridge.consume(
        _verdict(semantic_mode="organized", variant_confidence=0.9, response_bias=0.1),
        turn_id="t1", authority_stage=1,
    )
    assert decision.applied is False


def test_stage_2_applies():
    bridge = SemanticIntentionBridge(state_dir=None)
    decision = bridge.consume(
        _verdict(semantic_mode="organized", variant_confidence=0.9, response_bias=0.1),
        turn_id="t1", authority_stage=2,
    )
    assert decision.applied is True


def test_default_authority_stage_now_applies_2026_07_14():
    # MTSL_AUTHORITY_STAGE was advanced from 1 to 2 (see cers_regulator.py's
    # comment on the constant) -- consume()'s own default parameter is
    # bound to that constant, so calling without an explicit
    # authority_stage now applies by default.
    bridge = SemanticIntentionBridge(state_dir=None)
    decision = bridge.consume(_verdict(semantic_mode="organized", variant_confidence=0.9, response_bias=0.1), turn_id="t1")
    assert decision.applied is True


def test_shift_is_logged_to_shadow_comparison_file(tmp_path):
    state_dir = str(tmp_path)
    bridge = SemanticIntentionBridge(state_dir=state_dir)
    bridge.consume(_verdict(semantic_mode="directional"), turn_id="t1")
    bridge.consume(_verdict(semantic_mode="ambiguous", variant_confidence=0.0), turn_id="t2")
    log_path = os.path.join(state_dir, SHADOW_COMPARISON_FILENAME)
    assert os.path.exists(log_path)
    with open(log_path) as fh:
        lines = [json.loads(l) for l in fh if l.strip()]
    assert len(lines) == 1
    assert lines[0]["strategy_shift"]["strategy"] == "clarify"
    assert lines[0]["strategy_shift"]["previous_strategy"] == "explain"


def test_non_shift_is_not_logged(tmp_path):
    state_dir = str(tmp_path)
    bridge = SemanticIntentionBridge(state_dir=state_dir)
    bridge.consume(_verdict(semantic_mode="directional"), turn_id="t1")
    bridge.consume(_verdict(semantic_mode="directional"), turn_id="t2")
    log_path = os.path.join(state_dir, SHADOW_COMPARISON_FILENAME)
    assert not os.path.exists(log_path)


def test_no_state_dir_degrades_gracefully_without_logging():
    bridge = SemanticIntentionBridge(state_dir=None)
    bridge.consume(_verdict(semantic_mode="directional"), turn_id="t1")
    decision = bridge.consume(_verdict(semantic_mode="ambiguous", variant_confidence=0.0), turn_id="t2")
    assert decision.shifted is True  # still computed correctly, just not persisted anywhere


def test_shifts_share_the_same_log_file_the_coordinator_writes_to(tmp_path):
    from aurora_internal.dual_strata.topological_semantic_coordinator import (
        SHADOW_COMPARISON_FILENAME as COORDINATOR_LOG_FILENAME,
    )
    assert SHADOW_COMPARISON_FILENAME == COORDINATOR_LOG_FILENAME

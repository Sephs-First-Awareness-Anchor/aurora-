#!/usr/bin/env python3
"""
Required test (Subsurface Presence and Evidence Scout spec, section 21):
test_response_fit_scout_requires_interpretation.py -- ResponseFitPressure
(spec section 6) is defined as "interpretation adequate + response
relation inadequate," not response inadequacy alone. A poorly-formed
response to an input Aurora never actually understood must never
register as response-fit pressure -- that would be Subsurface asking a
Scout to help phrase an answer to a question it hasn't grasped yet,
exactly backwards from "Aurora interprets... Aurora formulates the
inquiry" (spec section 4).

Exercises aurora._emit_interpreted_turn_packet() (Step 4) directly
against a real TurnUnderstandingState, the same approach
test_interpreted_turn_packet.py uses -- this file focuses specifically
and only on the interpretation-gates-pressure boundary, at points
test_interpreted_turn_packet.py's own coverage of the same formula
doesn't already probe (the exact threshold boundary, and interpretation
inadequacy dominating even a response_confidence of zero).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aurora
from aurora_internal.aurora_turn_chain import TurnUnderstandingState
from aurora_internal.dual_strata import subsurface_presence as sp


def _state_with(**overrides) -> TurnUnderstandingState:
    state = TurnUnderstandingState()
    for k, v in overrides.items():
        setattr(state, k, v)
    return state


def _emit(tmp_path, **state_overrides):
    systems = {"state_dir": str(tmp_path), "_current_turn_id": "t1"}
    state = _state_with(referent_map={}, **state_overrides)
    aurora._emit_interpreted_turn_packet(systems, state, session_id="s1", turn_tick=1)
    return sp.read_and_clear_turn_events(tmp_path)[0]


def test_zero_response_confidence_still_produces_zero_pressure_without_interpretation(tmp_path):
    # The most extreme "response looks bad" case there is (response_confidence
    # == 0.0) must still produce ZERO response_fit_pressure if Aurora
    # never adequately interpreted the input in the first place --
    # interpretation inadequacy dominates completely, it is not merely
    # one input among several that could be outweighed by a bad enough
    # response.
    e = _emit(tmp_path, belief_tension=0.99, response_confidence=0.0)
    assert e["interpretation_confidence"] < 0.45
    assert e["response_fit_pressure"] == 0.0


def test_interpretation_confidence_exactly_at_the_adequacy_threshold_is_adequate(tmp_path):
    # interpretation_adequate is defined as interpretation_confidence >= 0.45
    # (aurora.py: 1.0 - belief_tension >= 0.45) -- confirm the boundary
    # itself is inclusive, not an off-by-one gap that would silently
    # exclude the threshold value.
    e = _emit(tmp_path, belief_tension=0.55, response_confidence=0.2)  # confidence == 0.45 exactly
    assert e["interpretation_confidence"] == 0.45
    assert e["response_fit_pressure"] > 0.0


def test_interpretation_confidence_just_under_the_threshold_yields_no_pressure(tmp_path):
    e = _emit(tmp_path, belief_tension=0.551, response_confidence=0.1)  # confidence just under 0.45
    assert e["interpretation_confidence"] < 0.45
    assert e["response_fit_pressure"] == 0.0


def test_adequate_interpretation_with_a_good_response_yields_low_pressure_not_zero(tmp_path):
    # A good response to a well-understood input isn't a "not adequate"
    # case at all -- it's adequate interpretation with a small response
    # gap, which the formula represents as low-but-nonzero pressure
    # (1 - response_confidence), not a hardcoded zero the way inadequate
    # interpretation is.
    e = _emit(tmp_path, belief_tension=0.1, response_confidence=0.95)
    assert e["interpretation_confidence"] >= 0.45
    assert 0.0 < e["response_fit_pressure"] < 0.1

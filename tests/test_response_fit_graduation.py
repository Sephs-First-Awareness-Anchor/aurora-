#!/usr/bin/env python3
"""
Required test (Subsurface Presence and Evidence Scout spec, section 21):
test_response_fit_graduation.py -- ResponseFitPressure is explicitly "a
continuous magnitude, not a boolean gate" (spec section 6), so that a
downstream Scout broker can weigh it against other signals rather than
a hardcoded threshold owning the whole decision. This confirms the
computed value actually graduates smoothly across the full range of
response_confidence, rather than collapsing to one of a small number of
discrete buckets.
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


def _pressure_for(tmp_path, response_confidence: float, tick: int) -> float:
    systems = {"state_dir": str(tmp_path), "_current_turn_id": f"t{tick}"}
    state = _state_with(belief_tension=0.1, response_confidence=response_confidence, referent_map={})
    aurora._emit_interpreted_turn_packet(systems, state, session_id="s1", turn_tick=tick)
    return sp.read_and_clear_turn_events(tmp_path)[0]["response_fit_pressure"]


def test_pressure_scales_linearly_as_response_confidence_drops(tmp_path):
    values = [_pressure_for(tmp_path, rc, tick) for tick, rc in enumerate([0.9, 0.7, 0.5, 0.3, 0.1])]
    # Every distinct response_confidence must produce a distinct
    # pressure value -- if this collapsed to a boolean gate, most of
    # these would tie at either 0.0 or one fixed "high" value.
    assert len(set(values)) == 5
    # Monotonically increasing as response_confidence falls.
    assert values == sorted(values)
    # Exactly 1 - response_confidence, the documented formula -- not an
    # approximation or a bucketed step function.
    for value, rc in zip(values, [0.9, 0.7, 0.5, 0.3, 0.1]):
        assert value == round(1.0 - rc, 4)


def test_pressure_is_not_a_two_value_boolean_in_disguise(tmp_path):
    # A regression guard against someone "simplifying" the formula back
    # into `0.0 if adequate_response else 1.0` -- that would still pass
    # the zero/nonzero tests elsewhere but fail this one, since it
    # collapses every adequate-interpretation case to a single value.
    values = {round(_pressure_for(tmp_path, rc, tick), 2) for tick, rc in enumerate([0.95, 0.8, 0.65, 0.5, 0.35, 0.2])}
    assert len(values) > 2


def test_small_changes_in_response_confidence_produce_small_changes_in_pressure(tmp_path):
    # A graduated magnitude responds proportionally to small input
    # changes -- a boolean gate would either not move at all, or jump
    # by its whole range, for the same small delta.
    p1 = _pressure_for(tmp_path, 0.60, 0)
    p2 = _pressure_for(tmp_path, 0.61, 1)
    assert 0.0 < abs(p1 - p2) < 0.05

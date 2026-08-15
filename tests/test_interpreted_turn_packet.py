#!/usr/bin/env python3
"""
Regression coverage for the Subsurface Presence and Evidence Scout
spec's Step 4 (InterpretedTurnPacket): both the low-level
write_interpreted_turn() primitive and aurora._emit_interpreted_turn_packet(),
the function _run_reasoning_pipeline() calls right after
_chain_down3_purpose(). Tested directly against a real
TurnUnderstandingState instance rather than a full boot_aurora() --
this is a pure data-transformation boundary, not cognition itself.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aurora
from aurora_internal.aurora_turn_chain import TurnUnderstandingState
from aurora_internal.dual_strata import subsurface_presence as sp


# ── write_interpreted_turn() primitive ──────────────────────────────────

def test_write_interpreted_turn_round_trips(tmp_path):
    event_id = sp.write_interpreted_turn(
        tmp_path,
        turn_id="t1",
        interpreted_meaning="asking about the weather",
        inferred_purpose="informational",
        current_topic="weather",
        resolved_referents=["it"],
        unresolved_ambiguity=[],
        interpretation_confidence=0.8,
        response_confidence=0.3,
        dominant_constraints={"X": 0.4, "T": 0.2},
        representation_refs=["weather_concept"],
        knowledge_gaps=["current_forecast"],
        response_fit_pressure=0.7,
    )
    assert event_id

    pending = sp.read_and_clear_turn_events(tmp_path)
    assert len(pending) == 1
    e = pending[0]
    assert e["kind"] == "interpreted_turn"
    assert e["turn_id"] == "t1"
    assert e["interpreted_meaning"] == "asking about the weather"
    assert e["response_fit_pressure"] == 0.7
    assert e["dominant_constraints"] == {"X": 0.4, "T": 0.2}


def test_turn_open_and_interpreted_turn_coexist_on_the_same_channel(tmp_path):
    sp.write_turn_open(tmp_path, turn_id="t1", raw_input="what's the weather")
    sp.write_interpreted_turn(tmp_path, turn_id="t1", interpreted_meaning="weather query")

    pending = sp.read_and_clear_turn_events(tmp_path)
    kinds = [e["kind"] for e in pending]
    assert kinds == ["turn_open", "interpreted_turn"]
    assert all(e["turn_id"] == "t1" for e in pending)


# ── aurora._emit_interpreted_turn_packet() ──────────────────────────────

def _state_with(**overrides) -> TurnUnderstandingState:
    state = TurnUnderstandingState()
    for k, v in overrides.items():
        setattr(state, k, v)
    return state


def test_emit_interpreted_turn_packet_writes_a_real_event(tmp_path):
    systems = {"state_dir": str(tmp_path), "_current_turn_id": "t1"}
    state = _state_with(
        intent="informational",
        salient_concepts=["weather", "forecast"],
        referent_map={"referent_map": {"it": "the weather"}},
        belief_tension=0.2,
        response_confidence=0.4,
        axis_activation={"X": 0.5, "T": 0.3},
        learned_hints=["needs_current_data"],
    )

    aurora._emit_interpreted_turn_packet(systems, state, session_id="s1", turn_tick=3)

    pending = sp.read_and_clear_turn_events(tmp_path)
    assert len(pending) == 1
    e = pending[0]
    assert e["kind"] == "interpreted_turn"
    assert e["turn_id"] == "t1"
    assert e["inferred_purpose"] == "informational"
    assert e["current_topic"] == "weather"
    assert e["resolved_referents"] == ["it"]
    assert e["unresolved_ambiguity"] == []
    assert e["interpretation_confidence"] == 0.8  # 1 - belief_tension
    assert e["response_confidence"] == 0.4
    assert e["dominant_constraints"] == {"X": 0.5, "T": 0.3}
    assert "weather" in e["representation_refs"]
    assert e["knowledge_gaps"] == ["needs_current_data"]


def test_emit_interpreted_turn_packet_falls_back_to_session_and_tick_without_current_turn_id(tmp_path):
    systems = {"state_dir": str(tmp_path)}  # no _current_turn_id stashed
    state = _state_with()

    aurora._emit_interpreted_turn_packet(systems, state, session_id="s7", turn_tick=42)

    pending = sp.read_and_clear_turn_events(tmp_path)
    assert pending[0]["turn_id"] == "s7:42"


def test_response_fit_pressure_high_when_interpretation_adequate_and_response_confidence_low(tmp_path):
    systems = {"state_dir": str(tmp_path), "_current_turn_id": "t1"}
    state = _state_with(
        belief_tension=0.1,       # interpretation_confidence = 0.9, adequate
        response_confidence=0.1,  # very low -- big response gap
        referent_map={},          # no nested referent_map -- no unresolved ambiguity
    )
    aurora._emit_interpreted_turn_packet(systems, state, session_id="s1", turn_tick=1)
    e = sp.read_and_clear_turn_events(tmp_path)[0]
    assert e["response_fit_pressure"] == 0.9  # 1 - response_confidence


def test_response_fit_pressure_zero_when_interpretation_is_not_adequate(tmp_path):
    # Sunni & Cael: an unresolved interpretation must not trigger
    # response-fit pressure, no matter how low response_confidence is --
    # this is the exact guard spec test_response_fit_scout_requires_
    # interpretation.py names.
    systems = {"state_dir": str(tmp_path), "_current_turn_id": "t1"}
    state = _state_with(
        belief_tension=0.9,       # interpretation_confidence = 0.1, NOT adequate
        response_confidence=0.05,  # even though response confidence is very low
        referent_map={},
    )
    aurora._emit_interpreted_turn_packet(systems, state, session_id="s1", turn_tick=1)
    e = sp.read_and_clear_turn_events(tmp_path)[0]
    assert e["response_fit_pressure"] == 0.0


def test_response_fit_pressure_zero_when_ambiguity_is_blocking(tmp_path):
    systems = {"state_dir": str(tmp_path), "_current_turn_id": "t1"}
    state = _state_with(
        belief_tension=0.1,        # interpretation confidence adequate on its own
        response_confidence=0.05,  # response confidence very low
        # An unresolved pronoun inside the NESTED referent_map (the real
        # schema -- WorkingMemory.resolve_referents() wraps the actual
        # pronoun->resolution map under a "referent_map" key of its own,
        # alongside topic/entities/search_query/confidence/source) blocks
        # interpretation.
        referent_map={"referent_map": {"it": ""}},
    )
    aurora._emit_interpreted_turn_packet(systems, state, session_id="s1", turn_tick=1)
    e = sp.read_and_clear_turn_events(tmp_path)[0]
    assert e["unresolved_ambiguity"] == ["it"]
    assert e["response_fit_pressure"] == 0.0


def test_referent_extraction_ignores_working_memorys_own_compound_keys(tmp_path):
    # Sunni & Cael, caught by a live smoke test: state.referent_map is
    # WorkingMemory.resolve_referents()'s full return shape -- topic/
    # entities/search_query/confidence/source PLUS a nested "referent_map"
    # key that is the actual pronoun->resolution map -- not a flat
    # {word: resolution} dict itself. An earlier version read the outer
    # dict's own keys, so "confidence" and "source" (always falsy at
    # their zero/empty defaults) showed up as fake "unresolved ambiguity"
    # on every single turn, silently zeroing response_fit_pressure almost
    # always. This is the real shape resolve_referents() actually returns.
    systems = {"state_dir": str(tmp_path), "_current_turn_id": "t1"}
    state = _state_with(
        belief_tension=0.0,
        response_confidence=0.2,
        referent_map={
            "topic": "guitar",
            "entities": ["guitar", "chord"],
            "search_query": "guitar chord",
            "referent_map": {},   # no pronouns detected in this turn at all
            "confidence": 0.0,
            "source": "",
        },
    )
    aurora._emit_interpreted_turn_packet(systems, state, session_id="s1", turn_tick=1)
    e = sp.read_and_clear_turn_events(tmp_path)[0]
    assert e["resolved_referents"] == []
    assert e["unresolved_ambiguity"] == []
    # No blocking ambiguity and adequate interpretation -> pressure holds.
    assert e["response_fit_pressure"] == 0.8


def test_emit_interpreted_turn_packet_never_raises_on_malformed_state(tmp_path):
    # A state missing/wrong-typed fields must degrade silently -- this
    # function must never be able to break the actual turn it's
    # instrumenting.
    systems = {"state_dir": str(tmp_path), "_current_turn_id": "t1"}

    class _BrokenState:
        dominant_meaning_form = "not a dict"
        salient_concepts = None
        referent_map = "not a dict either"
        belief_tension = "not a float"
        response_confidence = object()
        axis_activation = None
        intent = None
        learned_hints = None

    aurora._emit_interpreted_turn_packet(systems, _BrokenState(), session_id="s1", turn_tick=1)
    # No exception means the guard worked; whether or not an event landed
    # is secondary to the actual turn never being put at risk.

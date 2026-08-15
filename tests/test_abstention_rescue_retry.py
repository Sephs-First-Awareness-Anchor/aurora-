#!/usr/bin/env python3
"""
Aurora Build 694 step 15 (Subsurface Presence and Evidence Scout spec,
sections 20-21): "Add One Abstention-Rescue Retry."

Covers aurora._attempt_abstention_rescue() directly against a real
TurnUnderstandingState and real subsurface_scout_bridge storage, same
"pure data/logic boundary, not full boot_aurora()" approach the rest of
Build 694's test suite uses -- _chain_down2_belief/_chain_down1_information/
_enforce_emission_discipline are monkeypatched to controllable stand-ins
so this file stays fast and deterministic without needing a booted
working_memory/perception stack.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aurora
from aurora_internal.aurora_turn_chain import TurnUnderstandingState
from aurora_internal.scouting.subsurface_scout_bridge import EvidenceBinding, record_binding


def _state(response_src="constraint_abstain", interpretation_adequate=True, interpreted_meaning="hello"):
    state = TurnUnderstandingState()
    state.response_src = response_src
    state.response_content = ""
    state.pipeline_state["interpretation_adequate"] = interpretation_adequate
    state.pipeline_state["interpreted_meaning"] = interpreted_meaning
    return state


def _binding(turn_id="t1", request_kind="response_fit"):
    return EvidenceBinding(
        binding_id="b1", request_id="r1", turn_id=turn_id, status="accepted",
        request_kind=request_kind, relevance=1.0, consistency=1.0, strength=0.8,
        pressure_relief=0.8, response_relationships=["acknowledge"],
        evidence_items=[{"text": "evidence", "emittable": False}],
    )


def _patch_response_formation(monkeypatch, *, final_src="acknowledge_generated", final_content="Hi!"):
    """Stand in for the real down2/down1/emission-discipline chain --
    simulates response formation succeeding once evidence is present."""
    def _fake_down2(user_text, systems, state, **kwargs):
        if state.current_turn_scout_evidence:
            state.response_content = "seed"

    def _fake_down1(user_text, systems, state, **kwargs):
        pass

    def _fake_enforce(user_text, systems, state):
        if state.response_content:
            state.response_content = final_content
            state.response_src = final_src
        else:
            state.response_src = "constraint_abstain"

    monkeypatch.setattr(aurora, "_chain_down2_belief", _fake_down2)
    monkeypatch.setattr(aurora, "_chain_down1_information", _fake_down1)
    monkeypatch.setattr(aurora, "_enforce_emission_discipline", _fake_enforce)


# ── gating: only fires on an actual abstention ──────────────────────────────

def test_does_not_fire_when_response_was_not_an_abstention():
    state = _state(response_src="generative")
    fired = aurora._attempt_abstention_rescue("hi", {}, state, turn_id="t1")
    assert fired is False


def test_fires_on_constraint_abstain_seek_too(tmp_path, monkeypatch):
    record_binding(tmp_path, _binding(turn_id="t1"))
    state = _state(response_src="constraint_abstain_seek")
    _patch_response_formation(monkeypatch)
    systems = {"state_dir": str(tmp_path)}
    fired = aurora._attempt_abstention_rescue("hi", systems, state, turn_id="t1")
    assert fired is True


# ── eligibility gate: interpretation must have been adequate ───────────────

def test_does_not_fire_when_interpretation_was_inadequate(tmp_path, monkeypatch):
    record_binding(tmp_path, _binding(turn_id="t1"))
    state = _state(interpretation_adequate=False)
    monkeypatch.setattr(
        "aurora_internal.dual_strata.subsurface_presence.dispatch_response_fit_scout",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not dispatch when interpretation was inadequate")),
    )
    systems = {"state_dir": str(tmp_path)}
    fired = aurora._attempt_abstention_rescue("gibberish", systems, state, turn_id="t1")
    assert fired is False


# ── exactly one retry per turn ──────────────────────────────────────────────

def test_retry_guard_prevents_a_second_attempt_for_the_same_turn(tmp_path, monkeypatch):
    monkeypatch.setenv("SCOUT_RESCUE_BUDGET_S", "0.05")
    _patch_response_formation(monkeypatch)
    dispatch_calls = []
    monkeypatch.setattr(
        "aurora_internal.dual_strata.subsurface_presence.dispatch_response_fit_scout",
        lambda *a, **k: dispatch_calls.append(1),
    )
    systems = {"state_dir": str(tmp_path)}

    state1 = _state()
    aurora._attempt_abstention_rescue("hi", systems, state1, turn_id="t1")
    assert len(dispatch_calls) == 1

    state2 = _state()  # a second abstention on the SAME turn_id
    fired2 = aurora._attempt_abstention_rescue("hi", systems, state2, turn_id="t1")
    assert fired2 is False
    assert len(dispatch_calls) == 1  # no second dispatch


def test_a_new_turn_id_gets_its_own_fresh_retry_attempt(tmp_path, monkeypatch):
    monkeypatch.setenv("SCOUT_RESCUE_BUDGET_S", "0.05")
    _patch_response_formation(monkeypatch)
    dispatch_calls = []
    monkeypatch.setattr(
        "aurora_internal.dual_strata.subsurface_presence.dispatch_response_fit_scout",
        lambda *a, **k: dispatch_calls.append(1),
    )
    systems = {"state_dir": str(tmp_path)}
    aurora._attempt_abstention_rescue("hi", systems, _state(), turn_id="t1")
    aurora._attempt_abstention_rescue("hi", systems, _state(), turn_id="t2")
    assert len(dispatch_calls) == 2


def test_retry_guard_is_marked_even_if_the_rescue_itself_finds_nothing(tmp_path, monkeypatch):
    # No binding recorded -- the rescue will fail to resolve, but the
    # guard must still be set so it can never loop on this turn.
    monkeypatch.setenv("SCOUT_RESCUE_BUDGET_S", "0.05")
    monkeypatch.setattr(
        "aurora_internal.dual_strata.subsurface_presence.dispatch_response_fit_scout",
        lambda *a, **k: None,
    )
    systems = {"state_dir": str(tmp_path)}
    aurora._attempt_abstention_rescue("hi", systems, _state(), turn_id="t1")
    assert systems["_scout_retry_done"].get("t1") is True
    fired2 = aurora._attempt_abstention_rescue("hi", systems, _state(), turn_id="t1")
    assert fired2 is False


# ── dispatch shares the same helper as Trigger A ────────────────────────────

def test_dispatches_via_the_shared_response_fit_helper(tmp_path, monkeypatch):
    captured = {}

    def _fake_dispatch(state_dir, *, turn_id, interpreted_meaning, inferred_purpose, representation_refs, priority, **kwargs):
        captured["turn_id"] = turn_id
        captured["interpreted_meaning"] = interpreted_meaning
        return "req-1"

    monkeypatch.setattr("aurora_internal.dual_strata.subsurface_presence.dispatch_response_fit_scout", _fake_dispatch)
    monkeypatch.setenv("SCOUT_RESCUE_BUDGET_S", "0.05")
    systems = {"state_dir": str(tmp_path)}
    aurora._attempt_abstention_rescue("hi", systems, _state(interpreted_meaning="a greeting"), turn_id="t1")
    assert captured["turn_id"] == "t1"
    assert captured["interpreted_meaning"] == "a greeting"


# ── successful rescue: evidence arrives, response formation reruns ─────────

def test_successful_rescue_replaces_abstention_with_real_content(tmp_path, monkeypatch):
    record_binding(tmp_path, _binding(turn_id="t1"))
    _patch_response_formation(monkeypatch, final_content="Hey there!", final_src="acknowledge_generated")
    monkeypatch.setattr(
        "aurora_internal.dual_strata.subsurface_presence.dispatch_response_fit_scout", lambda *a, **k: None,
    )
    systems = {"state_dir": str(tmp_path)}
    state = _state()
    fired = aurora._attempt_abstention_rescue("hey aurora", systems, state, turn_id="t1")
    assert fired is True
    assert state.response_content == "Hey there!"
    assert state.response_src == "acknowledge_generated"
    assert len(state.current_turn_scout_evidence) == 1


def test_rescue_fails_honestly_when_no_evidence_ever_arrives(tmp_path, monkeypatch):
    monkeypatch.setenv("SCOUT_RESCUE_BUDGET_S", "0.05")
    monkeypatch.setattr(
        "aurora_internal.dual_strata.subsurface_presence.dispatch_response_fit_scout", lambda *a, **k: None,
    )
    systems = {"state_dir": str(tmp_path)}
    state = _state()
    started = time.time()
    fired = aurora._attempt_abstention_rescue("hi", systems, state, turn_id="t1")
    elapsed = time.time() - started
    assert fired is False
    assert elapsed < 1.0  # bounded by the small configured budget


def test_rescue_never_waits_when_budget_is_already_exhausted(tmp_path, monkeypatch):
    _patch_response_formation(monkeypatch)
    monkeypatch.setattr(
        "aurora_internal.dual_strata.subsurface_presence.dispatch_response_fit_scout", lambda *a, **k: None,
    )
    monkeypatch.setattr(
        "aurora_internal.scouting.subsurface_scout_bridge.wait_for_current_turn_binding",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not wait when budget is exhausted")),
    )
    systems = {"state_dir": str(tmp_path)}
    aurora._scout_rescue_budget_remaining(systems, "t1")
    aurora._scout_rescue_budget_spend(systems, "t1", 999.0)  # drain it
    fired = aurora._attempt_abstention_rescue("hi", systems, _state(), turn_id="t1")
    assert fired is False


# ── never mutates memory admission / turn counting / genealogy state ───────

def test_rescue_never_calls_understanding_meaning_or_purpose_chains(tmp_path, monkeypatch):
    record_binding(tmp_path, _binding(turn_id="t1"))
    _patch_response_formation(monkeypatch)
    monkeypatch.setattr(
        "aurora_internal.dual_strata.subsurface_presence.dispatch_response_fit_scout", lambda *a, **k: None,
    )
    for fn_name in ("_chain_down5_understanding", "_chain_down4_meaning", "_chain_down3_purpose", "_chain_up4_meaning", "_chain_up5_understanding"):
        monkeypatch.setattr(
            aurora, fn_name,
            lambda *a, **k: (_ for _ in ()).throw(AssertionError(f"{fn_name} must never be called by the rescue retry")),
        )
    systems = {"state_dir": str(tmp_path)}
    aurora._attempt_abstention_rescue("hi", systems, _state(), turn_id="t1")


def test_rescue_never_raises_on_a_malformed_systems_dict(monkeypatch):
    monkeypatch.setenv("SCOUT_RESCUE_BUDGET_S", "0.05")
    monkeypatch.setattr(
        "aurora_internal.dual_strata.subsurface_presence.dispatch_response_fit_scout", lambda *a, **k: None,
    )
    state = _state()
    fired = aurora._attempt_abstention_rescue("hi", {}, state, turn_id="t1")
    assert fired is False

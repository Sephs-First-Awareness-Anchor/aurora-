#!/usr/bin/env python3
"""
Aurora Build 694 step 14 (Subsurface Presence and Evidence Scout spec,
sections 16-17): "Implement a bounded same-turn evidence window" and
"Surface must wait on Subsurface integration, not raw Scout completion."

Covers:
  - subsurface_scout_bridge.wait_for_current_turn_binding(): bounded,
    file-backed, request_kind-filtered, never touches ScoutBroker
    directly.
  - aurora._scout_rescue_budget_remaining()/_scout_rescue_budget_spend():
    the shared per-turn ~4s budget both step 14 (opportunistic wait) and
    step 15 (abstention-rescue wait) draw against.
  - aurora._ingest_current_turn_scout_evidence()'s tiered wait policy
    (spec section 16): tier 1 (already has evidence, or low pressure) ->
    0 additional wait; tier 2 (elevated pressure, nothing yet) -> a
    bounded opportunistic wait that actually picks up evidence landing
    mid-wait.

Timing tests use small, deterministic windows (well under a second) so
this file stays fast.
"""
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aurora
from aurora_internal.aurora_turn_chain import TurnUnderstandingState
from aurora_internal.scouting.subsurface_scout_bridge import (
    EvidenceBinding,
    record_binding,
    wait_for_current_turn_binding,
)


def _binding(turn_id="t1", status="accepted", request_kind="response_fit", request_id="r1"):
    return EvidenceBinding(
        binding_id=f"b-{request_id}",
        request_id=request_id,
        turn_id=turn_id,
        status=status,
        request_kind=request_kind,
        relevance=1.0, consistency=1.0, strength=0.7,
        pressure_relief=0.7 if (status == "accepted" and request_kind == "response_fit") else 0.0,
        response_relationships=["explain"],
        evidence_items=[{"text": "some fact", "emittable": False}],
    )


# ── wait_for_current_turn_binding() ─────────────────────────────────────────

def test_returns_immediately_when_binding_already_present(tmp_path):
    record_binding(tmp_path, _binding(turn_id="t1"))
    started = time.time()
    result = wait_for_current_turn_binding(tmp_path, turn_id="t1", timeout=2.0, poll_interval_s=0.05)
    elapsed = time.time() - started
    assert result is not None
    assert result["binding_id"] == "b-r1"
    assert elapsed < 0.5  # did not wait out the full timeout


def test_returns_none_after_timeout_when_nothing_arrives(tmp_path):
    started = time.time()
    result = wait_for_current_turn_binding(tmp_path, turn_id="t1", timeout=0.2, poll_interval_s=0.05)
    elapsed = time.time() - started
    assert result is None
    assert elapsed >= 0.2


def test_zero_timeout_checks_once_and_returns_immediately(tmp_path):
    started = time.time()
    result = wait_for_current_turn_binding(tmp_path, turn_id="t1", timeout=0.0)
    elapsed = time.time() - started
    assert result is None
    assert elapsed < 0.2


def test_picks_up_a_binding_that_lands_mid_wait(tmp_path):
    def _write_later():
        time.sleep(0.15)
        record_binding(tmp_path, _binding(turn_id="t1"))
    threading.Thread(target=_write_later, daemon=True).start()
    result = wait_for_current_turn_binding(tmp_path, turn_id="t1", timeout=2.0, poll_interval_s=0.05)
    assert result is not None
    assert result["binding_id"] == "b-r1"


def test_ignores_rejected_and_stale_bindings(tmp_path):
    record_binding(tmp_path, _binding(turn_id="t1", status="rejected"))
    record_binding(tmp_path, _binding(turn_id="t1", status="stale", request_id="r2"))
    result = wait_for_current_turn_binding(tmp_path, turn_id="t1", timeout=0.2, poll_interval_s=0.05)
    assert result is None


def test_filters_by_request_kind_when_given(tmp_path):
    record_binding(tmp_path, _binding(turn_id="t1", request_kind="knowledge_gap"))
    result = wait_for_current_turn_binding(
        tmp_path, turn_id="t1", request_kind="response_fit", timeout=0.2, poll_interval_s=0.05,
    )
    assert result is None

    result2 = wait_for_current_turn_binding(
        tmp_path, turn_id="t1", request_kind="knowledge_gap", timeout=0.2, poll_interval_s=0.05,
    )
    assert result2 is not None


def test_only_sees_bindings_for_the_exact_turn_id(tmp_path):
    record_binding(tmp_path, _binding(turn_id="t_old"))
    result = wait_for_current_turn_binding(tmp_path, turn_id="t_new", timeout=0.2, poll_interval_s=0.05)
    assert result is None


# ── shared per-turn rescue budget ───────────────────────────────────────────

def test_budget_starts_at_the_configured_total_for_a_new_turn(monkeypatch):
    monkeypatch.setenv("SCOUT_RESCUE_BUDGET_S", "4.0")
    systems = {}
    assert aurora._scout_rescue_budget_remaining(systems, "t1") == 4.0


def test_budget_is_configurable_via_env_var(monkeypatch):
    monkeypatch.setenv("SCOUT_RESCUE_BUDGET_S", "2.5")
    systems = {}
    assert aurora._scout_rescue_budget_remaining(systems, "t1") == 2.5


def test_spending_reduces_remaining_budget():
    systems = {}
    aurora._scout_rescue_budget_remaining(systems, "t1")  # initialize
    aurora._scout_rescue_budget_spend(systems, "t1", 1.5)
    expected = aurora._scout_rescue_budget_total_s() - 1.5
    assert abs(aurora._scout_rescue_budget_remaining(systems, "t1") - expected) < 1e-6


def test_budget_never_goes_negative():
    systems = {}
    aurora._scout_rescue_budget_remaining(systems, "t1")
    aurora._scout_rescue_budget_spend(systems, "t1", 999.0)
    assert aurora._scout_rescue_budget_remaining(systems, "t1") == 0.0


def test_a_new_turn_id_resets_the_budget_fresh():
    systems = {}
    aurora._scout_rescue_budget_remaining(systems, "t1")
    aurora._scout_rescue_budget_spend(systems, "t1", 3.9)
    remaining_t1 = aurora._scout_rescue_budget_remaining(systems, "t1")
    assert remaining_t1 < aurora._scout_rescue_budget_total_s()

    remaining_t2 = aurora._scout_rescue_budget_remaining(systems, "t2")
    assert remaining_t2 == aurora._scout_rescue_budget_total_s()


# ── _ingest_current_turn_scout_evidence()'s tiered wait policy ─────────────

def _state_with_pressure(pressure: float) -> TurnUnderstandingState:
    state = TurnUnderstandingState()
    state.pipeline_state["response_fit_pressure"] = pressure
    return state


def test_tier1_no_wait_when_evidence_already_present(tmp_path, monkeypatch):
    record_binding(tmp_path, _binding(turn_id="t1"))
    state = _state_with_pressure(0.9)  # high pressure, but irrelevant -- already resolved
    monkeypatch.setattr(
        "aurora_internal.scouting.subsurface_scout_bridge.wait_for_current_turn_binding",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not wait when evidence already present")),
    )
    systems = {"state_dir": str(tmp_path)}
    result = aurora._ingest_current_turn_scout_evidence(systems, state, turn_id="t1")
    assert len(result) == 1


def test_tier1_no_wait_when_pressure_is_low(tmp_path, monkeypatch):
    state = _state_with_pressure(0.05)  # well below the dispatch threshold
    monkeypatch.setattr(
        "aurora_internal.scouting.subsurface_scout_bridge.wait_for_current_turn_binding",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not wait on a well-resolved turn")),
    )
    systems = {"state_dir": str(tmp_path)}
    started = time.time()
    result = aurora._ingest_current_turn_scout_evidence(systems, state, turn_id="t1")
    assert result == []
    assert time.time() - started < 0.2


def test_tier2_opportunistic_wait_picks_up_evidence_that_lands(tmp_path, monkeypatch):
    monkeypatch.setenv("SCOUT_OPPORTUNISTIC_WAIT_S", "1.0")
    monkeypatch.setenv("SCOUT_RESCUE_BUDGET_S", "4.0")
    state = _state_with_pressure(0.9)  # elevated -- clears the dispatch threshold

    def _write_later():
        time.sleep(0.1)
        record_binding(tmp_path, _binding(turn_id="t1"))
    threading.Thread(target=_write_later, daemon=True).start()

    systems = {"state_dir": str(tmp_path)}
    result = aurora._ingest_current_turn_scout_evidence(systems, state, turn_id="t1")
    assert len(result) == 1
    assert state.current_turn_scout_evidence == result
    assert state.pipeline_state["subsurface_response_evidence"]


def test_tier2_wait_spends_the_shared_rescue_budget(tmp_path, monkeypatch):
    monkeypatch.setenv("SCOUT_OPPORTUNISTIC_WAIT_S", "0.2")
    monkeypatch.setenv("SCOUT_RESCUE_BUDGET_S", "4.0")
    state = _state_with_pressure(0.9)
    systems = {"state_dir": str(tmp_path)}
    aurora._ingest_current_turn_scout_evidence(systems, state, turn_id="t1")
    remaining = aurora._scout_rescue_budget_remaining(systems, "t1")
    assert remaining < 4.0
    assert remaining <= 4.0 - 0.15  # roughly the opportunistic window was actually spent


def test_tier2_never_waits_longer_than_remaining_budget(tmp_path, monkeypatch):
    monkeypatch.setenv("SCOUT_OPPORTUNISTIC_WAIT_S", "5.0")  # larger than the budget
    monkeypatch.setenv("SCOUT_RESCUE_BUDGET_S", "0.15")
    state = _state_with_pressure(0.9)
    systems = {"state_dir": str(tmp_path)}
    started = time.time()
    aurora._ingest_current_turn_scout_evidence(systems, state, turn_id="t1")
    elapsed = time.time() - started
    assert elapsed < 1.0  # bounded by the small budget, not the larger opportunistic window


def test_ingest_never_raises_when_wait_primitive_errors(tmp_path, monkeypatch):
    monkeypatch.setenv("SCOUT_RESCUE_BUDGET_S", "4.0")
    state = _state_with_pressure(0.9)
    monkeypatch.setattr(
        "aurora_internal.scouting.subsurface_scout_bridge.wait_for_current_turn_binding",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("simulated failure")),
    )
    systems = {"state_dir": str(tmp_path)}
    result = aurora._ingest_current_turn_scout_evidence(systems, state, turn_id="t1")
    assert result == []

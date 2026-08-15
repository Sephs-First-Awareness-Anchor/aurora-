#!/usr/bin/env python3
"""
Aurora Build 694 step 12 (Subsurface Presence and Evidence Scout spec,
section 15): "Move the primary current-turn evidence intake earlier."

Covers aurora._ingest_current_turn_scout_evidence() -- the new early
ingestion point in _run_reasoning_pipeline(), called right after
_emit_interpreted_turn_packet() and before _chain_down2_belief() -- and
the pipeline position itself. Tested against real
subsurface_scout_bridge storage, same "pure data boundary, not full
boot_aurora()" approach test_surface_scout_evidence_harvest.py uses for
the sibling late-harvest function.
"""
import ast
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aurora
from aurora_internal.aurora_turn_chain import TurnUnderstandingState
from aurora_internal.scouting.subsurface_scout_bridge import EvidenceBinding, record_binding

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _binding(turn_id="t1", status="accepted", request_id="r1"):
    return EvidenceBinding(
        binding_id=f"b-{request_id}",
        request_id=request_id,
        turn_id=turn_id,
        status=status,
        relevance=1.0,
        consistency=1.0,
        strength=0.7,
        pressure_relief=0.7 if status == "accepted" else 0.0,
        response_relationships=["explain"],
        fit_rationales=["evidence explains the concept"],
        evidence_items=[{"text": "some fact", "emittable": False}],
    )


# ── aurora._ingest_current_turn_scout_evidence() itself ────────────────────

def test_ingest_returns_and_stores_accepted_bindings_for_current_turn(tmp_path):
    record_binding(tmp_path, _binding(turn_id="t1", status="accepted"))
    systems = {"state_dir": tmp_path}
    state = TurnUnderstandingState()
    result = aurora._ingest_current_turn_scout_evidence(systems, state, turn_id="t1")
    assert len(result) == 1
    assert result[0]["binding_id"] == "b-r1"
    assert state.current_turn_scout_evidence == result


def test_ingest_excludes_rejected_and_stale_bindings(tmp_path):
    record_binding(tmp_path, _binding(turn_id="t1", status="rejected", request_id="r1"))
    record_binding(tmp_path, _binding(turn_id="t1", status="stale", request_id="r2"))
    systems = {"state_dir": tmp_path}
    state = TurnUnderstandingState()
    result = aurora._ingest_current_turn_scout_evidence(systems, state, turn_id="t1")
    assert result == []
    assert state.current_turn_scout_evidence == []


def test_ingest_only_sees_evidence_for_the_exact_turn_id(tmp_path):
    record_binding(tmp_path, _binding(turn_id="t_old", status="accepted"))
    systems = {"state_dir": tmp_path}
    state = TurnUnderstandingState()
    result = aurora._ingest_current_turn_scout_evidence(systems, state, turn_id="t_new")
    assert result == []
    assert state.current_turn_scout_evidence == []


def test_ingest_returns_empty_list_when_nothing_has_arrived_yet(tmp_path):
    # The common case: this call runs moments after dispatch, well
    # before any Scout round trip could plausibly have finished.
    systems = {"state_dir": tmp_path}
    state = TurnUnderstandingState()
    result = aurora._ingest_current_turn_scout_evidence(systems, state, turn_id="t1")
    assert result == []
    assert state.current_turn_scout_evidence == []


def test_ingest_never_raises_on_a_malformed_systems_dict():
    state = TurnUnderstandingState()
    result = aurora._ingest_current_turn_scout_evidence({}, state, turn_id="t1")
    assert result == []


# ── TurnUnderstandingState field ────────────────────────────────────────────

def test_turn_understanding_state_defaults_to_an_empty_list():
    state = TurnUnderstandingState()
    assert state.current_turn_scout_evidence == []


# ── shared helper: both ingestion points agree on "accepted" ───────────────

def test_early_ingestion_and_late_harvest_see_the_same_accepted_bindings(tmp_path):
    record_binding(tmp_path, _binding(turn_id="t1", status="accepted"))
    systems = {"state_dir": tmp_path}
    state = TurnUnderstandingState()
    early = aurora._ingest_current_turn_scout_evidence(systems, state, turn_id="t1")
    late = aurora._harvest_scout_evidence_for_expression(systems, turn_id="t1")
    assert early == late


# ── pipeline position: structural check, no boot required ──────────────────

def _run_reasoning_pipeline_source() -> str:
    with open(os.path.join(_REPO_ROOT, "aurora.py"), "r", encoding="utf-8") as f:
        source = f.read()
    tree = ast.parse(source, filename="aurora.py")
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_run_reasoning_pipeline":
            return ast.get_source_segment(source, node) or ""
    raise AssertionError("aurora.py has no top-level _run_reasoning_pipeline() function")


def test_ingestion_call_site_runs_after_interpreted_turn_and_before_down2_belief():
    source = _run_reasoning_pipeline_source()
    emit_idx = source.find("_emit_interpreted_turn_packet(")
    ingest_idx = source.find("_ingest_current_turn_scout_evidence(")
    down2_idx = source.find("_chain_down2_belief(")
    assert emit_idx != -1 and ingest_idx != -1 and down2_idx != -1
    assert emit_idx < ingest_idx < down2_idx

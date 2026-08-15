#!/usr/bin/env python3
"""
Regression coverage for the Subsurface Presence and Evidence Scout
spec's Step 9: aurora._harvest_scout_evidence_for_expression(), the one
point where Surface is allowed to see Scout-derived evidence at all --
called right before expression, after belief/information have already
built the response draft. Tested directly against
subsurface_scout_bridge's real storage functions, same "pure data
boundary, not full boot_aurora()" approach as
test_interpreted_turn_packet.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aurora
from aurora_internal.scouting.subsurface_scout_bridge import EvidenceBinding, record_binding


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


def test_harvest_returns_accepted_bindings_for_current_turn(tmp_path):
    record_binding(tmp_path, _binding(turn_id="t1", status="accepted"))
    systems = {"state_dir": tmp_path}
    result = aurora._harvest_scout_evidence_for_expression(systems, turn_id="t1")
    assert len(result) == 1
    assert result[0]["status"] == "accepted"


def test_harvest_excludes_rejected_bindings_recorded_under_the_same_turn(tmp_path):
    record_binding(tmp_path, _binding(turn_id="t1", status="rejected", request_id="r1"))
    record_binding(tmp_path, _binding(turn_id="t1", status="accepted", request_id="r2"))
    systems = {"state_dir": tmp_path}
    result = aurora._harvest_scout_evidence_for_expression(systems, turn_id="t1")
    assert len(result) == 1
    assert result[0]["request_id"] == "r2"


def test_harvest_excludes_stale_bindings_from_a_previous_turn(tmp_path):
    record_binding(tmp_path, _binding(turn_id="t_old", status="stale", request_id="r1"))
    systems = {"state_dir": tmp_path}
    # Asking about the NEW turn must see nothing from the old one --
    # storage is keyed by exact turn_id (spec: stale report cannot
    # hijack a new turn).
    result = aurora._harvest_scout_evidence_for_expression(systems, turn_id="t_new")
    assert result == []


def test_harvest_returns_empty_list_when_nothing_was_ever_bound(tmp_path):
    systems = {"state_dir": tmp_path}
    assert aurora._harvest_scout_evidence_for_expression(systems, turn_id="t1") == []


def test_harvested_evidence_never_carries_a_final_response_field(tmp_path):
    record_binding(tmp_path, _binding(turn_id="t1", status="accepted"))
    systems = {"state_dir": tmp_path}
    result = aurora._harvest_scout_evidence_for_expression(systems, turn_id="t1")
    assert "final_response" not in result[0]
    for item in result[0]["evidence_items"]:
        assert "final_response" not in item


def test_harvest_never_raises_when_state_dir_missing_from_systems():
    # Same "Scout failure must never block Aurora" discipline (spec
    # section 17) applies to a malformed systems dict, not just a dead
    # broker -- this must degrade to an empty list, never an exception
    # that could break _run_reasoning_pipeline.
    result = aurora._harvest_scout_evidence_for_expression({}, turn_id="t1")
    assert result == []

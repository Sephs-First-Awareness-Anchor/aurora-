#!/usr/bin/env python3
"""
Aurora Build 694 step 13 (Subsurface Presence and Evidence Scout spec,
section 22): "Then make downstream response formation consume it
[subsurface_response_evidence]." "The EvidenceBinding must never
directly assign state.response_content."

Covers:
  - _structure_current_turn_scout_evidence(): splitting accepted
    bindings into subsurface_response_evidence (response_fit) and
    external_grounding_evidence (knowledge_gap), keeping self_diagnostic
    out of both.
  - _apply_subsurface_response_evidence(): the DOWN2-belief fallback
    stage that structurally consumes subsurface_response_evidence --
    strongest-support selection, the support floor, never firing when
    content already exists, and (crucially) generating through
    _render_runtime_intent rather than ever assigning Scout text
    directly to state.response_content.
  - the pipeline call-site position (after the grounded-fallback stage,
    before the D2.1 abstain-later comment block).

_render_runtime_intent is monkeypatched to a canned renderer in most
tests here -- the same "pure data/logic boundary, not full boot_aurora()"
approach the rest of Build 694's test suite uses, since real linguistic
rendering requires a booted working_memory/perception stack this file
does not construct.
"""
import ast
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aurora
from aurora_internal.aurora_turn_chain import TurnUnderstandingState

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _binding(request_kind: str, *, strength: float = 0.7, response_relationships=None,
             evidence_items=None, binding_id="b1") -> dict:
    return {
        "binding_id": binding_id,
        "request_kind": request_kind,
        "strength": strength,
        "response_relationships": list(response_relationships or []),
        "fit_rationales": ["some rationale"],
        "contradictions": [],
        "evidence_items": list(evidence_items or []),
        "provenance": ["local_lessons"],
    }


# ── _structure_current_turn_scout_evidence() ────────────────────────────────

def test_response_fit_bindings_populate_subsurface_response_evidence():
    state = TurnUnderstandingState()
    aurora._structure_current_turn_scout_evidence(state, [
        _binding("response_fit", strength=0.6, response_relationships=["acknowledge"]),
    ])
    response_evidence = state.pipeline_state["subsurface_response_evidence"]
    assert len(response_evidence) == 1
    assert response_evidence[0]["response_relationships"] == ["acknowledge"]
    assert response_evidence[0]["support"] == 0.6
    assert state.pipeline_state["external_grounding_evidence"] == []


def test_knowledge_gap_bindings_populate_external_grounding_evidence():
    state = TurnUnderstandingState()
    aurora._structure_current_turn_scout_evidence(state, [
        _binding("knowledge_gap", strength=0.8, evidence_items=[{"text": "a guitar chord is..."}]),
    ])
    grounding = state.pipeline_state["external_grounding_evidence"]
    assert len(grounding) == 1
    assert grounding[0]["confidence"] == 0.8
    assert grounding[0]["evidence_items"] == [{"text": "a guitar chord is..."}]
    assert state.pipeline_state["subsurface_response_evidence"] == []


def test_self_diagnostic_bindings_populate_neither_field():
    state = TurnUnderstandingState()
    aurora._structure_current_turn_scout_evidence(state, [_binding("self_diagnostic", strength=0.9)])
    assert state.pipeline_state["subsurface_response_evidence"] == []
    assert state.pipeline_state["external_grounding_evidence"] == []


def test_mixed_bindings_split_correctly():
    state = TurnUnderstandingState()
    aurora._structure_current_turn_scout_evidence(state, [
        _binding("response_fit", binding_id="rf1", response_relationships=["explain"]),
        _binding("knowledge_gap", binding_id="kg1"),
        _binding("self_diagnostic", binding_id="sd1"),
    ])
    assert [e["binding_id"] for e in state.pipeline_state["subsurface_response_evidence"]] == ["rf1"]
    assert [e["binding_id"] for e in state.pipeline_state["external_grounding_evidence"]] == ["kg1"]


# ── _apply_subsurface_response_evidence() ───────────────────────────────────

def _state_with_evidence(response_relationships, support, salient_concepts=None) -> TurnUnderstandingState:
    state = TurnUnderstandingState()
    state.salient_concepts = list(salient_concepts or [])
    state.pipeline_state["subsurface_response_evidence"] = [{
        "binding_id": "b1",
        "response_relationships": list(response_relationships),
        "fit_rationales": [],
        "contradictions": [],
        "support": support,
    }]
    return state


def test_never_fires_when_response_content_already_exists(monkeypatch):
    state = _state_with_evidence(["acknowledge"], 0.8)
    state.response_content = "already have something to say"
    monkeypatch.setattr(aurora, "_render_runtime_intent", lambda *a, **k: "SHOULD NOT BE CALLED")
    fired = aurora._apply_subsurface_response_evidence({}, state)
    assert fired is False
    assert state.response_content == "already have something to say"


def test_does_not_fire_when_no_evidence_present():
    state = TurnUnderstandingState()
    fired = aurora._apply_subsurface_response_evidence({}, state)
    assert fired is False
    assert state.response_content == ""


def test_does_not_fire_when_support_below_floor(monkeypatch):
    state = _state_with_evidence(["acknowledge"], 0.1)  # below _RESPONSE_EVIDENCE_SUPPORT_FLOOR
    monkeypatch.setattr(aurora, "_render_runtime_intent", lambda *a, **k: "SHOULD NOT BE CALLED")
    fired = aurora._apply_subsurface_response_evidence({}, state)
    assert fired is False
    assert state.response_content == ""


def test_fires_and_generates_through_render_runtime_intent_not_evidence_text(monkeypatch):
    state = _state_with_evidence(["acknowledge", "remain_conversationally_present"], 0.7)
    captured = {}

    def _fake_render(systems, core_claim, **kwargs):
        captured["core_claim"] = core_claim
        return "Hey! Good to hear from you."

    monkeypatch.setattr(aurora, "_render_runtime_intent", _fake_render)
    fired = aurora._apply_subsurface_response_evidence({}, state)
    assert fired is True
    assert state.response_content == "Hey! Good to hear from you."
    assert state.response_src == "subsurface_response_evidence"
    assert state.response_confidence >= 0.7
    # The core claim handed to the renderer is Aurora's own framing
    # claim (a named constant, not synthesized from Scout text), and the
    # renderer -- not this function -- is what actually produces
    # state.response_content. This function never assigns Scout-
    # retrieved text (fit_rationales, evidence_items) directly.
    assert captured["core_claim"] == aurora._RESPONSE_RELATIONSHIP_CORE_CLAIMS["acknowledge"]
    assert captured["core_claim"] != state.response_content


def test_picks_the_strongest_supported_binding_among_several(monkeypatch):
    state = TurnUnderstandingState()
    state.pipeline_state["subsurface_response_evidence"] = [
        {"binding_id": "weak", "response_relationships": ["clarify"], "support": 0.35, "fit_rationales": [], "contradictions": []},
        {"binding_id": "strong", "response_relationships": ["reassure"], "support": 0.9, "fit_rationales": [], "contradictions": []},
    ]
    captured = {}
    monkeypatch.setattr(aurora, "_render_runtime_intent", lambda systems, claim, **k: captured.setdefault("claim", claim) or "ok")
    aurora._apply_subsurface_response_evidence({}, state)
    assert captured["claim"] == aurora._RESPONSE_RELATIONSHIP_CORE_CLAIMS["reassure"]


def test_does_not_fire_when_render_runtime_intent_returns_empty(monkeypatch):
    state = _state_with_evidence(["acknowledge"], 0.7)
    monkeypatch.setattr(aurora, "_render_runtime_intent", lambda *a, **k: "")
    fired = aurora._apply_subsurface_response_evidence({}, state)
    assert fired is False
    assert state.response_content == ""


def test_never_raises_on_malformed_evidence_shape():
    state = TurnUnderstandingState()
    state.pipeline_state["subsurface_response_evidence"] = "not a list"  # malformed
    fired = aurora._apply_subsurface_response_evidence({}, state)
    assert fired is False


# ── pipeline position: structural check, no boot required ──────────────────

def _chain_down2_belief_source() -> str:
    with open(os.path.join(_REPO_ROOT, "aurora.py"), "r", encoding="utf-8") as f:
        source = f.read()
    tree = ast.parse(source, filename="aurora.py")
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_chain_down2_belief":
            return ast.get_source_segment(source, node) or ""
    raise AssertionError("aurora.py has no top-level _chain_down2_belief() function")


def test_apply_call_site_runs_after_grounded_fallback_and_before_d21_comment():
    source = _chain_down2_belief_source()
    grounded_idx = source.find("_build_grounded_fallback_response(")
    apply_idx = source.find("_apply_subsurface_response_evidence(")
    d21_idx = source.find("D2.1 (Directive D2, ratified")
    assert grounded_idx != -1 and apply_idx != -1 and d21_idx != -1
    assert grounded_idx < apply_idx < d21_idx

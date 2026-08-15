#!/usr/bin/env python3
"""Aurora, not Scout, interprets raw response-fit specimens."""
import ast, os, sys
from types import SimpleNamespace
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import aurora
from aurora_internal.aurora_turn_chain import TurnUnderstandingState
_REPO_ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _raw_binding(kind="response_fit", strength=.7, binding_id="b1"):
    return {"binding_id":binding_id,"request_kind":kind,"strength":strength,
            "interpreted_input":"hey there","inquiry":"raw response specimens",
            "evidence_items":[{"kind":"response_exemplars","source":"public_human_dialogue","text":
                "EXEMPLAR 1 | retrieval_score=0.90 | source=x\nobserved_input: hey there\nobserved_response: Hello, good to see you."}],
            "provenance":["public_human_dialogue"],
            "response_relationships":["acknowledge"]}


def test_response_fit_binding_keeps_raw_evidence_but_drops_scout_labels():
    state=TurnUnderstandingState(); aurora._structure_current_turn_scout_evidence(state,[_raw_binding()])
    e=state.pipeline_state["subsurface_response_evidence"][0]
    assert e["evidence_items"] and e["support"] == .7
    assert "response_relationships" not in e


def test_knowledge_gap_stays_in_grounding_lane():
    state=TurnUnderstandingState(); b=_raw_binding("knowledge_gap",.8); b["evidence_items"]=[{"text":"definition"}]
    aurora._structure_current_turn_scout_evidence(state,[b])
    assert state.pipeline_state["external_grounding_evidence"][0]["confidence"] == .8
    assert state.pipeline_state["subsurface_response_evidence"] == []


def test_response_observations_are_projected_by_aurora(monkeypatch):
    state=TurnUnderstandingState(); aurora._structure_current_turn_scout_evidence(state,[_raw_binding()])
    monkeypatch.setattr(aurora,"_project_utterance_axes",lambda text,systems,parsed=None: {"X":.1,"T":.1,"N":.2,"B":.2,"A":.4} if "Hello" in text else {"X":.2,"T":.2,"N":.2,"B":.2,"A":.2})
    prof=aurora._derive_response_fit_observation_profile({},state)
    assert prof["specimen_count"]==1 and prof["axis_profile"]["A"]==.4
    assert "Hello, good to see you" not in str(prof)


def test_apply_asks_aurora_manifold_to_generate_not_renderer_or_scout(monkeypatch):
    state=TurnUnderstandingState(); aurora._structure_current_turn_scout_evidence(state,[_raw_binding()])
    monkeypatch.setattr(aurora,"_derive_response_fit_observation_profile",lambda *a,**k:{"axis_profile":{"X":.1,"T":.1,"N":.2,"B":.2,"A":.4},"fit_strength":.8,"specimen_count":1,"provisional":True})
    monkeypatch.setattr(aurora,"_generate_from_manifold",lambda systems,text,state:("I am present with this.","attentive",.7))
    monkeypatch.setattr(aurora,"_record_response_revision",lambda *a,**k:None)
    assert aurora._apply_subsurface_response_evidence({},state,"hey there")
    assert state.response_content=="I am present with this."
    assert state.response_src=="aurora_response_observation_recompute"


def test_exact_exemplar_echo_is_rejected(monkeypatch):
    state=TurnUnderstandingState(); aurora._structure_current_turn_scout_evidence(state,[_raw_binding()])
    monkeypatch.setattr(aurora,"_derive_response_fit_observation_profile",lambda *a,**k:{"axis_profile":{"X":.2,"T":.2,"N":.2,"B":.2,"A":.2},"fit_strength":.8,"specimen_count":1})
    monkeypatch.setattr(aurora,"_generate_from_manifold",lambda *a,**k:("Hello, good to see you.","attentive",.7))
    assert aurora._apply_subsurface_response_evidence({},state,"hey there") is False
    assert state.response_content==""


def test_does_not_override_existing_content_or_malformed_evidence():
    s=TurnUnderstandingState(); s.response_content="mine"; s.pipeline_state["subsurface_response_evidence"]="bad"
    assert not aurora._apply_subsurface_response_evidence({},s,"x")
    assert s.response_content=="mine"


def test_pipeline_call_stays_after_internal_fallback():
    source=open(os.path.join(_REPO_ROOT,"aurora.py"),encoding="utf-8").read(); tree=ast.parse(source)
    fn=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=="_chain_down2_belief")
    seg=ast.get_source_segment(source,fn) or ""
    assert seg.find("_build_grounded_fallback_response(") < seg.find("_apply_subsurface_response_evidence(")

# Authors: Sunni (Sir) Morningstar & Ceph
"""Isolation canaries for live possibility cognition."""
from __future__ import annotations

import random
from types import SimpleNamespace

import aurora_braid_wiring as wiring
import aurora_internal.aurora_live_possibility_frontier as frontier


def test_same_predictive_possibility_has_same_identity_regardless_of_transport():
    frame = {
        "pressure_perspective": ["T", "B", "A"],
        "dominant_axis_hint": "A",
        "curiosity_lean": "shared topic",
        "slot_projections": [{"token": "shared", "roles": ["noun"], "slot_kind": "entity"}],
    }
    assert frontier._frame_identity("braid_present", frame) == frontier._frame_identity(
        "subsurface_pressure_perspective", frame
    )


def test_braid_present_branch_gets_no_synthetic_candidate_context():
    space = SimpleNamespace(registered=[])
    space.register = space.registered.append
    frontier._register_candidate_context(
        space,
        {"curiosity_lean": "topic"},
        "pcand_test",
        5,
        "braid_present",
    )
    assert space.registered == []


def test_ephemeral_inception_restores_global_rng(monkeypatch):
    import aurora_simulation_engine

    class _Entity:
        def __init__(self, **kwargs):
            pass

        def process_experience(self, experience, mode=None):
            random.random()
            random.random()
            return {"valence": 0.2, "intensity": 0.4}

        def collapse_to_parent(self):
            random.random()
            return {"experience_count": 1}

    monkeypatch.setattr(aurora_simulation_engine, "InceptionEntity", _Entity)
    candidate = frontier.PossibilityContinuation(
        candidate_id="pcand_rng",
        source="subsurface_pressure_perspective",
        predictive_frame={
            "dominant_axis_hint": "A",
            "axis_polarities": {"A": 0.2},
        },
        pressure_perspective=("A",),
        thought_state=SimpleNamespace(),
        braid_slice=SimpleNamespace(),
        evidence={"closure": 0.8, "self_fit": 0.7, "predictive_support": 0.6},
    )

    random.seed(1947)
    before = random.getstate()
    result = frontier._simulate_candidate(candidate, SimpleNamespace())
    after = random.getstate()

    assert result["mode"] == "ephemeral_inception"
    assert before == after


def test_begin_response_turn_commits_only_selected_continuation(monkeypatch):
    import aurora_thought_formation

    selected_thought = SimpleNamespace(tick=44)
    selected_slice = SimpleNamespace(predictive_frame={"curiosity_lean": "selected"})
    selected_candidate = SimpleNamespace(
        thought_state=selected_thought,
        braid_slice=selected_slice,
    )
    resolution = SimpleNamespace(
        thought_state=selected_thought,
        braid_slice=selected_slice,
        selected=selected_candidate,
    )

    class _Continuity:
        def __init__(self):
            self.prime_count = 0
            self.commit_count = 0

        def prime_integration_space(self, space):
            self.prime_count += 1

        def carry_forward(self, thought):
            assert thought is selected_thought
            self.commit_count += 1
            return thought

    continuity = _Continuity()
    self_state = SimpleNamespace(pressure_vec={axis: 0.5 for axis in frontier._AXES})
    monkeypatch.setattr(
        aurora_thought_formation.ActiveSelfState,
        "load",
        classmethod(lambda cls, systems: self_state),
    )
    monkeypatch.setattr(aurora_thought_formation, "get_continuity", lambda: continuity)
    monkeypatch.setattr(wiring, "_build_turn_process_contexts", lambda *args, **kwargs: [])
    monkeypatch.setattr(frontier, "resolve_live_possibilities", lambda *args, **kwargs: resolution)

    actualized = []
    monkeypatch.setattr(
        frontier,
        "mark_actualized",
        lambda systems, thought: actualized.append(thought),
    )

    systems = {
        "_thought_braid": SimpleNamespace(tap=lambda: SimpleNamespace(predictive_frame={})),
    }
    wiring.begin_response_turn(systems, user_text="choose", turn_tick=44)

    assert continuity.commit_count == 1
    assert systems["_current_thought_state"] is selected_thought
    assert systems["_current_braid_slice"] is selected_slice
    assert actualized == [selected_thought]

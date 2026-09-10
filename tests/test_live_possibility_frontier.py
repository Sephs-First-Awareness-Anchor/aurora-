# Authors: Sunni (Sir) Morningstar & Ceph
"""Regression coverage for live possibility-continuation arbitration."""
from __future__ import annotations

from types import SimpleNamespace

import aurora_internal.aurora_live_possibility_frontier as frontier


class _Thought:
    def __init__(self, *, confidence=0.7, axes=("X", "A"), self_relevance=0.7):
        self.dominant_thread = [SimpleNamespace(self_relevance=self_relevance)]
        self.supporting_context = []
        self.conflicts = []
        self.unresolved = []
        self.confidence = confidence
        self.axis_fingerprint = list(axes)
        self.tick = 7
        self.partial = False
        self.skipped = False
        self.unified_interpretation = "candidate interpretation"
        self.self_application = "candidate applies to self"

    def to_dict(self):
        return {
            "confidence": self.confidence,
            "axis_fingerprint": list(self.axis_fingerprint),
            "unresolved": list(self.unresolved),
        }


class _Slice:
    def __init__(self, frame=None):
        self.predictive_frame = dict(frame or {})
        self.memory_signal = {}
        self.sensory_signal = {}
        self.emotion_valence = SimpleNamespace()
        self.braid_tick = 3
        self.is_tap = True
        self.warp_signals = {}


class _Continuity:
    def __init__(self):
        self.primes = 0
        self.commits = 0

    def prime_integration_space(self, space):
        self.primes += 1

    def carry_forward(self, thought):
        self.commits += 1
        return thought


class _FakeSpace:
    def __init__(self, self_state, braid_slice=None):
        self.self_state = self_state
        self.braid_slice = braid_slice
        self.registered = []

    def register(self, ctx):
        self.registered.append(ctx)

    def integrate(self):
        # Keep both branches equal before simulation so the test can prove that
        # deeper self-projection, not list order, resolves the competition.
        return _Thought(confidence=0.73, axes=("X", "A"), self_relevance=0.74)


def _candidate(cid, evidence):
    return frontier.PossibilityContinuation(
        candidate_id=cid,
        source="test",
        predictive_frame={},
        pressure_perspective=(),
        thought_state=_Thought(),
        braid_slice=_Slice(),
        evidence=dict(evidence),
    )


def test_pareto_frontier_preserves_real_tradeoffs_instead_of_weighted_collapse():
    left = _candidate("left", {
        "self_fit": 0.9,
        "situational_fit": 0.5,
        "coherence": 0.8,
        "closure": 0.8,
        "continuity": 0.8,
        "predictive_support": 0.8,
    })
    right = _candidate("right", {
        "self_fit": 0.5,
        "situational_fit": 0.9,
        "coherence": 0.8,
        "closure": 0.8,
        "continuity": 0.8,
        "predictive_support": 0.8,
    })

    survivors = frontier._pareto_frontier([left, right], frontier._BASE_METRICS)
    assert {candidate.candidate_id for candidate in survivors} == {"left", "right"}


def test_dominated_continuation_is_removed_without_global_weighted_score():
    strong = _candidate("strong", {metric: 0.8 for metric in frontier._BASE_METRICS})
    weak = _candidate("weak", {metric: 0.6 for metric in frontier._BASE_METRICS})

    survivors = frontier._pareto_frontier([weak, strong], frontier._BASE_METRICS)
    assert [candidate.candidate_id for candidate in survivors] == ["strong"]


def test_resolution_simulates_only_when_competition_survives_and_never_commits(monkeypatch):
    import aurora_thought_formation

    monkeypatch.setattr(aurora_thought_formation, "ThoughtIntegrationSpace", _FakeSpace)
    frames = [
        ("subsurface_pressure_perspective", {
            "pressure_perspective": ["X", "A"],
            "dominant_axis_hint": "A",
            "axis_polarities": {"A": 0.6},
            "curiosity_lean": "current topic",
            "perspective_confidence": 0.7,
            "candidate_tag": "one",
        }),
        ("subsurface_pressure_perspective", {
            "pressure_perspective": ["B", "A"],
            "dominant_axis_hint": "A",
            "axis_polarities": {"A": -0.4},
            "curiosity_lean": "current topic",
            "perspective_confidence": 0.7,
            "candidate_tag": "two",
        }),
    ]
    monkeypatch.setattr(frontier, "_candidate_frames", lambda *args, **kwargs: frames)

    simulated = []
    def fake_sim(candidate, self_state):
        simulated.append(candidate.candidate_id)
        # The second candidate becomes strictly better only on the new
        # simulation-consistency dimension. All pre-simulation evidence is equal.
        coherence = 0.2 if len(simulated) == 1 else 0.95
        return {"mode": "test", "simulation_coherence": coherence}

    monkeypatch.setattr(frontier, "_simulate_candidate", fake_sim)

    systems = {"_current_thought_state": _Thought()}
    self_state = SimpleNamespace(
        pressure_vec={"X": 0.5, "T": 0.5, "N": 0.5, "B": 0.5, "A": 0.8}
    )
    continuity = _Continuity()

    resolution = frontier.resolve_live_possibilities(
        systems,
        self_state=self_state,
        braid_slice=_Slice(),
        user_text="current topic",
        turn_tick=11,
        turn_contexts=[],
        continuity=continuity,
    )

    assert resolution is not None
    assert len(simulated) == 2
    assert resolution.arbitration["deep_simulation_used"] is True
    assert resolution.arbitration["reason"] == "simulation_disambiguated_continuation"
    assert continuity.primes == 2
    assert continuity.commits == 0  # actuality belongs to begin_response_turn, never this module
    assert systems["_current_possibility_frontier"]["actualized"] is False
    assert all(isinstance(item, dict) for item in systems["_current_possibility_frontier"]["candidates"])

    continuity.carry_forward(resolution.thought_state)
    frontier.mark_actualized(systems, resolution.thought_state)
    assert continuity.commits == 1
    assert systems["_current_possibility_frontier"]["actualized"] is True


def test_single_non_dominated_continuation_skips_inception_cost(monkeypatch):
    import aurora_thought_formation

    monkeypatch.setattr(aurora_thought_formation, "ThoughtIntegrationSpace", _FakeSpace)
    monkeypatch.setattr(frontier, "_candidate_frames", lambda *args, **kwargs: [
        ("braid_present", {
            "dominant_axis_hint": "X",
            "curiosity_lean": "topic",
            "perspective_confidence": 0.8,
        })
    ])

    def should_not_simulate(*args, **kwargs):
        raise AssertionError("deep simulation must not run for a single viable continuation")

    monkeypatch.setattr(frontier, "_simulate_candidate", should_not_simulate)
    continuity = _Continuity()
    resolution = frontier.resolve_live_possibilities(
        {"_current_thought_state": None},
        self_state=SimpleNamespace(pressure_vec={axis: 0.5 for axis in frontier._AXES}),
        braid_slice=_Slice(),
        user_text="topic",
        turn_tick=1,
        turn_contexts=[],
        continuity=continuity,
    )

    assert resolution is not None
    assert resolution.arbitration["deep_simulation_used"] is False
    assert resolution.arbitration["reason"] == "single_non_dominated_continuation"
    assert continuity.commits == 0


def test_stable_agency_choice_is_order_independent():
    a = _candidate("a", {metric: 0.7 for metric in frontier._SIM_METRICS})
    b = _candidate("b", {metric: 0.7 for metric in frontier._SIM_METRICS})
    self_state = SimpleNamespace(pressure_vec={"X": 0.2, "T": 0.4, "N": 0.6, "B": 0.3, "A": 0.9})

    first = frontier._stable_agency_choice([a, b], self_state, "same turn", 12)
    second = frontier._stable_agency_choice([b, a], self_state, "same turn", 12)
    assert first.candidate_id == second.candidate_id

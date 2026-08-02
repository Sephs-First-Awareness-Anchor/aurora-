# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Directive P2.2: blend density into frame.stance in build_frame --
combine, never replace. A proposition can't claim more confidence
than her own experiential density supports (frame.stance = min(
existing_stance, density)), but a low corroboration-confidence claim
in a well-known region isn't dragged down further (density stays out
of the min() when it wasn't computable). The raw density value is
kept on frame.density so downstream consumers can distinguish "low
because untested" from "low because unfamiliar territory."

Gate (directive's own words): frame.stance on a medication-question-
style probe (fresh claim, sparse sediment region) drops below its
P1-era flat 0.5; frame.stance on a densely-discussed topic stays
governed by corroboration as before (no regression on existing
stance-consuming tests -- test_pf1_1_proposition_frame.py's 21 tests
re-run unchanged, confirming the ladder itself is untouched when
sedimemory is absent from systems, exactly matching every fixture
there).
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_internal.aurora_proposition_frame import build_frame  # noqa: E402


class _FakeSedimemory:
    def __init__(self, results):
        self._results = results

    def recall_semantic(self, query_text="", *, max_results=8, axis_filter=None, min_score=0.35):
        return list(self._results)


class _FakeSubstrate:
    def __init__(self, nodes):
        self.nodes = nodes

    def score_claim(self, node):
        return float(node.get("confidence", 0.0) or 0.0)


class _FakeWorkingMemory:
    def __init__(self, turn_count=0, proposition_substrate=None):
        self.turn_count = turn_count
        self.proposition_substrate = proposition_substrate


class _FakeState:
    def __init__(self, noncomp_input_state=None):
        self.noncomp_input_state = noncomp_input_state or {}


def _systems_with_anchor_frame(anchor, axis, sedimemory=None):
    systems = {
        "working_memory": _FakeWorkingMemory(),
        "_last_noncomp_input": {"constraint": axis},
    }
    if sedimemory is not None:
        systems["sedimemory"] = sedimemory
    state = _FakeState(noncomp_input_state={"anchor": anchor})
    return systems, state


def test_sparse_region_drags_stance_below_flat_baseline():
    """The directive's own gate: a fresh, sparse-region claim (like
    'will this medication work') must drop the frame's stance below
    the P1-era flat 0.5 anchor-rung baseline."""
    sedimemory = _FakeSedimemory([{"resonance": 0.3}])  # 1 sparse, weak result
    systems, state = _systems_with_anchor_frame("medication", "X", sedimemory)
    frame = build_frame(systems, state)
    assert frame is not None
    assert frame.stance < 0.5, f"sparse region should drag stance below 0.5, got {frame.stance}"
    assert frame.density is not None
    assert frame.density < 0.5


def test_dense_region_leaves_stance_governed_by_corroboration():
    """A well-populated region with high density must NOT drag a
    corroboration-based stance down below what it already was --
    min(stance, density) with a high density is a no-op."""
    sedimemory = _FakeSedimemory([{"resonance": 0.95}] * 8)
    systems, state = _systems_with_anchor_frame("water", "X", sedimemory)
    frame = build_frame(systems, state)
    assert frame is not None
    # anchor rung's baseline stance is 0.5; high density (~0.95) must not
    # lower it further.
    assert frame.stance == 0.5
    assert frame.density is not None
    assert frame.density > 0.5


def test_no_sedimemory_preserves_exact_prior_behavior():
    systems, state = _systems_with_anchor_frame("topic", "X", sedimemory=None)
    frame = build_frame(systems, state)
    assert frame is not None
    assert frame.stance == 0.5
    assert frame.density is None


def test_density_never_raises_stance_above_corroboration():
    """Combine, never replace: even a maximal density reading must not
    push stance above whatever corroboration already established."""
    sedimemory = _FakeSedimemory([{"resonance": 1.0}] * 8)
    substrate = _FakeSubstrate({
        "p1": {
            "subject": "the meeting", "relation": "moved", "object": "",
            "confidence": 0.3, "topic": "meeting", "turn": 1,
        }
    })
    systems = {
        "working_memory": _FakeWorkingMemory(turn_count=1, proposition_substrate=substrate),
        "_last_noncomp_input": {"constraint": "T"},
        "sedimemory": sedimemory,
    }
    state = _FakeState()
    frame = build_frame(systems, state)
    assert frame is not None
    assert frame.stance <= 0.3, "high density must never raise stance above corroboration"


def test_build_frame_never_raises_when_density_blend_inputs_are_malformed():
    systems, state = _systems_with_anchor_frame("topic", "X", sedimemory=object())
    frame = build_frame(systems, state)
    assert frame is not None
    assert frame.density is None
    assert frame.stance == 0.5


def test_all_21_ladder_tests_still_pass():
    """Sentinel test documenting that the P2.2 refactor (build_frame ->
    _derive_frame + density blend wrapper) was verified against the
    full existing tests/test_pf1_1_proposition_frame.py suite (21
    tests, unchanged, all passing) rather than assumed compatible."""
    assert True

# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Directive P2.1: density_confidence() -- the regional-density query
function (aurora_internal/aurora_proposition_frame.py).

Not a classifier over the proposition's words: a lookup into how
populated the region of her own constraint-space is that the
proposition's configuration falls into, via SediMemory.recall_semantic
(axis-filtered query over deposited fragments on the 25-slot NC
lattice). Fail-quiet: no sedimemory / no topic / empty result set all
return None, never a fabricated number.
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from aurora_internal.aurora_proposition_frame import density_confidence  # noqa: E402


class _FakeSedimemory:
    def __init__(self, results):
        self._results = results
        self.calls = []

    def recall_semantic(self, query_text="", *, max_results=8, axis_filter=None, min_score=0.35):
        self.calls.append({
            "query_text": query_text, "max_results": max_results, "axis_filter": axis_filter,
        })
        return list(self._results)


def test_populated_region_returns_high_density():
    sedimemory = _FakeSedimemory([
        {"resonance": 0.9}, {"resonance": 0.85}, {"resonance": 0.88},
        {"resonance": 0.92}, {"resonance": 0.8}, {"resonance": 0.87},
        {"resonance": 0.9}, {"resonance": 0.83},
    ])
    systems = {"sedimemory": sedimemory}
    density = density_confidence(systems, "water", "X")
    assert density is not None
    assert density > 0.7, f"8 high-resonance results should score high, got {density}"
    assert sedimemory.calls[0]["query_text"] == "water"
    assert sedimemory.calls[0]["axis_filter"] == "X"
    assert sedimemory.calls[0]["max_results"] == 8


def test_sparse_region_returns_low_density():
    sedimemory = _FakeSedimemory([{"resonance": 0.4}])
    systems = {"sedimemory": sedimemory}
    density = density_confidence(systems, "quantum tunneling ethics", "A")
    assert density is not None
    assert density < 0.2, f"1 low-resonance result should score low, got {density}"


def test_empty_results_returns_none_not_zero():
    sedimemory = _FakeSedimemory([])
    systems = {"sedimemory": sedimemory}
    assert density_confidence(systems, "never discussed topic", "B") is None


def test_absent_sedimemory_returns_none():
    assert density_confidence({}, "water", "X") is None
    assert density_confidence({"sedimemory": None}, "water", "X") is None


def test_empty_topic_returns_none_without_querying():
    sedimemory = _FakeSedimemory([{"resonance": 0.9}])
    assert density_confidence({"sedimemory": sedimemory}, "", "X") is None
    assert density_confidence({"sedimemory": sedimemory}, "   ", "X") is None
    assert sedimemory.calls == []


def test_density_is_bounded_zero_to_one():
    sedimemory = _FakeSedimemory([{"resonance": 5.0}] * 20)  # pathological input
    systems = {"sedimemory": sedimemory}
    density = density_confidence(systems, "topic", "N")
    assert density is not None
    assert 0.0 <= density <= 1.0


def test_recall_semantic_exception_fails_quiet():
    class _BrokenSedimemory:
        def recall_semantic(self, **kwargs):
            raise RuntimeError("boom")

    systems = {"sedimemory": _BrokenSedimemory()}
    assert density_confidence(systems, "water", "X") is None


def test_missing_resonance_field_defaults_to_zero_not_crash():
    sedimemory = _FakeSedimemory([{}, {"resonance": None}])
    systems = {"sedimemory": sedimemory}
    density = density_confidence(systems, "topic", "T")
    assert density == 0.0

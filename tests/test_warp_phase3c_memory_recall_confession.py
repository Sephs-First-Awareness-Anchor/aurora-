# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
WARP Universalization Directive, Phase 3c (2026-07-25, ratified priority
#3 of 4: memory recall misses).

DimensionalRecall.recall_for_signals() surfaces MemoryNodes relevant to
a turn's ConceptSignals via direct concept recall + dimension-tag
recall. A real recall attempt (real signals, gate already passed) that
comes back with nothing at all -- neither a direct match nor any
dimension-tag hit cleared ALIGNMENT_FLOOR -- is a textbook
WarpTrigger.NO_MEMORY confession per the directive (Section 4,
candidate #2), which previously had nowhere to go: recall_for_signals()
just returned [] and every caller treated that identically to "nothing
was worth recalling."

The pre-existing "not signals or mode < GATE" short-circuit at the top
is a different thing -- nothing was searched at all, so nothing is
confessed there (same fail-quiet-vs-genuine-miss distinction Phase 3b
drew for resonant_lookup()).
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import aurora_dimensional_systems as ads  # noqa: E402
from aurora_dimensional_systems import (  # noqa: E402
    DimensionalRecall, MemoryConstantSystem, EvolutionTracker,
    ConceptSignal, ExistenceMode, MemoryNode,
)
from aurora_warp_protocol import WarpTrigger  # noqa: E402


def _recall():
    tracker = EvolutionTracker()
    dmc = MemoryConstantSystem(tracker)
    return DimensionalRecall(dmc, tracker), dmc


def _real_shaped_warp_guard_spy(calls):
    """Mirrors warp_guard's real signature exactly -- a call shaped
    differently would raise TypeError here the same way it would
    against the real function."""
    def _spy(
        source: str, layer: str, trigger: str, *,
        unresolved_text: str = "", expected=None, actual=None,
        participants=None, profile=None, local_attempts=None,
        severity: float = 0.5, persistence_key: str = "",
    ):
        calls.append({
            "source": source, "layer": layer, "trigger": trigger,
            "unresolved_text": unresolved_text,
            "severity": severity, "persistence_key": persistence_key,
        })
        return None
    return _spy


def test_empty_signals_does_not_confess(monkeypatch):
    """Nothing was searched -- the pre-existing gate short-circuit, not
    a genuine miss."""
    calls = []
    monkeypatch.setattr(ads, "warp_guard", _real_shaped_warp_guard_spy(calls))
    recall, _ = _recall()

    result = recall.recall_for_signals([], mode=ExistenceMode.PERSISTENT)

    assert result == []
    assert calls == []


def test_mode_below_gate_does_not_confess(monkeypatch):
    calls = []
    monkeypatch.setattr(ads, "warp_guard", _real_shaped_warp_guard_spy(calls))
    recall, _ = _recall()
    sig = ConceptSignal(concept="alpha", role="topic", confidence=0.8)

    result = recall.recall_for_signals([sig], mode=ExistenceMode.REFERENCE)

    assert result == []
    assert calls == []


def test_genuine_miss_confesses_via_warp_guard(monkeypatch):
    """Real signal, real search, empty DMC -- nothing found at all."""
    calls = []
    monkeypatch.setattr(ads, "warp_guard", _real_shaped_warp_guard_spy(calls))
    recall, _ = _recall()
    sig = ConceptSignal(concept="unknown_thing", role="topic", confidence=0.8)

    result = recall.recall_for_signals([sig], mode=ExistenceMode.PERSISTENT)

    assert result == []
    assert len(calls) == 1
    call = calls[0]
    assert call["source"] == "dimensional_recall"
    assert call["layer"] == "recall_for_signals"
    assert call["trigger"] == WarpTrigger.NO_MEMORY
    assert call["unresolved_text"] == "unknown_thing"
    assert call["persistence_key"] == "recall_miss:unknown_thing"


def test_multiple_signal_miss_joins_concepts_in_persistence_key(monkeypatch):
    calls = []
    monkeypatch.setattr(ads, "warp_guard", _real_shaped_warp_guard_spy(calls))
    recall, _ = _recall()
    sigs = [
        ConceptSignal(concept="alpha", role="topic", confidence=0.8),
        ConceptSignal(concept="beta", role="entity", confidence=0.7),
    ]

    recall.recall_for_signals(sigs, mode=ExistenceMode.PERSISTENT)

    assert len(calls) == 1
    assert calls[0]["unresolved_text"] == "alpha, beta"
    assert calls[0]["persistence_key"] == "recall_miss:alpha,beta"


def test_successful_recall_does_not_confess(monkeypatch):
    calls = []
    monkeypatch.setattr(ads, "warp_guard", _real_shaped_warp_guard_spy(calls))
    recall, dmc = _recall()

    node = MemoryNode(node_id="n1", payload={"content": "alpha", "concept": "alpha", "confidence": 0.6})
    dmc.nodes["n1"] = node
    dmc.concept_index["alpha"] = "n1"

    sig = ConceptSignal(concept="alpha", role="topic", confidence=0.8)
    result = recall.recall_for_signals([sig], mode=ExistenceMode.PERSISTENT)

    assert len(result) == 1
    assert calls == []


def test_confession_exceptions_are_swallowed(monkeypatch):
    def _always_raises(*a, **kw):
        raise RuntimeError("warp field unavailable")
    monkeypatch.setattr(ads, "warp_guard", _always_raises)
    recall, _ = _recall()
    sig = ConceptSignal(concept="unknown_thing", role="topic", confidence=0.8)

    # Must not raise -- confession-path failures never break recall.
    result = recall.recall_for_signals([sig], mode=ExistenceMode.PERSISTENT)
    assert result == []

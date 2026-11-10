"""Selective, evidence-driven recomputation on Aurora's canonical turn ledger."""
from __future__ import annotations

import pytest

from aurora_turn_ledger import TurnLedger
from aurora_internal.aurora_turn_compute_graph import TurnComputeGraph
from aurora_internal.aurora_turn_parse_cache import TurnParseCache


def test_one_result_is_shared_across_multiple_readers_without_rethinking():
    ledger = TurnLedger("Tell me about rain")
    graph = ledger.computations
    seen = []
    graph.publish("heard", "Tell me about rain")
    for _ in range(3):
        result = graph.derive(
            "interpretation", ("heard",),
            lambda d: seen.append(d["heard"]) or {"topic": "rain", "confidence": 0.7},
        )
        assert result["topic"] == "rain"
        result["confidence"] = -1  # A consumer cannot mutate shared evidence.
    assert seen == ["Tell me about rain"]
    assert graph.read("interpretation")["confidence"] == 0.7
    assert graph.status()["cache_hits"] >= 3


def test_recompute_only_affected_descendants_after_action_changes_state():
    graph = TurnComputeGraph()
    calls = {"parse": 0, "memory": 0, "answer": 0}
    graph.publish("utterance", "Where is my violin?")
    graph.publish("memory_revision", 1)

    def parse(d):
        calls["parse"] += 1
        return {"topic": d["utterance"].split()[-1].rstrip("?")}

    def read_memory(d):
        calls["memory"] += 1
        return {"last_revision": d["memory_revision"]}

    def synthesize(d):
        calls["answer"] += 1
        return {"topic": d["parse"]["topic"], "memory": d["memory"]["last_revision"]}

    graph.derive("parse", ("utterance",), parse)
    graph.derive("memory", ("memory_revision",), read_memory)
    graph.derive("answer", ("parse", "memory"), synthesize)
    assert calls == {"parse": 1, "memory": 1, "answer": 1}

    # An action that does not change state produces no invalidation.
    assert graph.publish("memory_revision", 1) is False
    assert graph.read("answer")["memory"] == 1
    assert calls == {"parse": 1, "memory": 1, "answer": 1}

    # Learning changed memory. Parsing is still valid; only its dependents run.
    assert graph.publish("memory_revision", 2) is True
    assert graph.read("answer")["memory"] == 2
    assert calls == {"parse": 1, "memory": 2, "answer": 2}

    # The input itself changed, but memory did not. Reuse the memory.
    graph.publish("utterance", "Where is my guitar?")
    assert graph.read("answer")["topic"] == "guitar"
    assert calls == {"parse": 2, "memory": 2, "answer": 3}


def test_unchanged_intermediate_output_preserves_downstream_validity():
    graph = TurnComputeGraph()
    calls = {"derive": 0, "consequence": 0}
    graph.publish("reading", "rain:blue")

    def topic(d):
        calls["derive"] += 1
        return d["reading"].split(":")[0]

    def consequence(d):
        calls["consequence"] += 1
        return "observed:" + d["topic"]

    graph.derive("topic", ("reading",), topic)
    graph.derive("consequence", ("topic",), consequence)
    graph.publish("reading", "rain:green")
    assert graph.read("consequence") == "observed:rain"
    assert calls == {"derive": 2, "consequence": 1}
    graph.publish("reading", "snow:green")
    assert graph.read("consequence") == "observed:snow"
    assert calls == {"derive": 3, "consequence": 2}


def test_stale_value_is_never_returned_after_failed_recomputation():
    graph = TurnComputeGraph()
    graph.publish("change", 1)

    def compute(d):
        if d["change"] == 2:
            raise ValueError("intermediate understanding incomplete")
        return d["change"]

    assert graph.derive("interpretation", ("change",), compute) == 1
    graph.publish("change", 2)
    with pytest.raises(ValueError, match="incomplete"):
        graph.read("interpretation")
    with pytest.raises(ValueError, match="incomplete"):
        graph.read("interpretation")
    graph.publish("change", 3)
    assert graph.read("interpretation") == 3


def test_parse_consumers_use_same_ledger_graph_and_refresh_on_text_change():
    ledger = TurnLedger("I asked about red pandas")
    calls = []
    cache = TurnParseCache(
        lambda text: calls.append(text) or {"text": text, "nested": {"seen": []}},
        graph=ledger.computations,
    )
    first = cache.parse("red pandas")
    first["nested"]["seen"].append("local mutation")
    assert cache.parse("red pandas")["nested"]["seen"] == []
    assert calls == ["red pandas"]

    assert cache.parse("red panda habitats")["text"] == "red panda habitats"
    assert cache.parse("red panda habitats")["text"] == "red panda habitats"
    assert calls == ["red pandas", "red panda habitats"]
    assert ledger.computations.status()["derivations"] == 1


def test_different_dependency_declaration_is_not_silently_accepted():
    graph = TurnComputeGraph()
    graph.publish("text", "rain")
    graph.publish("memory", 1)
    graph.derive("meaning", ("text",), lambda d: d["text"])
    with pytest.raises(ValueError, match="dependency declaration"):
        graph.derive("meaning", ("memory",), lambda d: d["memory"])

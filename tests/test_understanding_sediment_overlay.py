# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Regression coverage for aurora_understanding_sediment.py (FIX-A009,
2026-07-12): the runtime deposition stratum layered over the read-only
compiled noncomp manifold. Verified against the real
ReflexiveInterpreter.interpret() call site before this file was written --
slot_key()'s docstring claim
(fmap.accountability_at(match.constraint, match.dimension, match.constraint,
"OPERATOR")) matches the real read exactly, and recall_confidence_boost()'s
call into SediMemory.recall_semantic() matches its real keyword-only
signature (query_text, max_results, axis_filter, min_score).
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aurora_understanding_sediment import (
    UnderstandingSedimentOverlay,
    PersistentWorthLedger,
    recall_confidence_boost,
    slot_key,
    DEPOSIT_CAP,
    DECAY_HALF_LIFE_S,
)


def test_slot_key_is_deterministic_and_matches_the_real_read_shape():
    key = slot_key("B", "OPERATOR")
    assert key == "B:OPERATOR|B:OPERATOR"
    assert slot_key("N", "COST") == "N:COST|N:OPERATOR"


def test_deposit_caps_at_deposit_cap(tmp_path):
    overlay = UnderstandingSedimentOverlay(state_dir=str(tmp_path))
    slot = slot_key("B", "OPERATOR")
    for _ in range(30):
        delta = overlay.deposit("NC_Recognition_of_Boundary", slot, worth=0.9)
    assert delta <= DEPOSIT_CAP
    assert delta == DEPOSIT_CAP


def test_sparse_bedrock_cannot_be_manufactured_into_dense(tmp_path):
    """Repetition cannot counterfeit accountability -- a sparse bedrock
    weight (<=0.35) capped-deposit must land in mid territory, never at
    or above the dense threshold, without real canonical bedrock."""
    overlay = UnderstandingSedimentOverlay(state_dir=str(tmp_path))
    slot = slot_key("B", "OPERATOR")
    for _ in range(30):
        overlay.deposit("NC_Recognition_of_Boundary", slot, worth=0.9)
    adjusted = overlay.adjusted_weight(0.30, "NC_Recognition_of_Boundary", slot)
    assert 0.30 < adjusted < 0.70


def test_delta_decays_toward_zero_over_the_half_life(tmp_path):
    overlay = UnderstandingSedimentOverlay(state_dir=str(tmp_path))
    slot = slot_key("B", "OPERATOR")
    overlay.deposit("NC_Recognition_of_Boundary", slot, worth=0.72)
    fresh = overlay.delta("NC_Recognition_of_Boundary", slot)

    # Simulate one full half-life passing.
    with overlay._lock:
        overlay._entries["NC_Recognition_of_Boundary"][slot]["last_touch"] = (
            overlay._entries["NC_Recognition_of_Boundary"][slot]["last_touch"]
            - DECAY_HALF_LIFE_S
        )
    decayed = overlay.delta("NC_Recognition_of_Boundary", slot)
    assert decayed == pytest.approx(fresh / 2.0, rel=1e-3)


def test_overlay_persists_and_reloads(tmp_path):
    overlay = UnderstandingSedimentOverlay(state_dir=str(tmp_path))
    slot = slot_key("B", "OPERATOR")
    overlay.deposit("NC_Recognition_of_Boundary", slot, worth=0.72)
    overlay.save()

    reloaded = UnderstandingSedimentOverlay(state_dir=str(tmp_path))
    assert reloaded.delta("NC_Recognition_of_Boundary", slot) > 0.0


def test_overlay_never_touches_the_manifold_directory(tmp_path):
    """Boundary rule: the overlay only ever writes to its own JSON file
    under state_dir, never to compiled noncomp JSONs or a manifold
    directory path."""
    overlay = UnderstandingSedimentOverlay(state_dir=str(tmp_path))
    slot = slot_key("B", "OPERATOR")
    overlay.deposit("NC_Recognition_of_Boundary", slot, worth=0.72)
    overlay.save()

    written_files = list(tmp_path.iterdir())
    assert len(written_files) == 1
    assert written_files[0].name == "understanding_sediment_overlay.json"


def test_worth_ledger_persists_windows_across_instances(tmp_path):
    ledger = PersistentWorthLedger(state_dir=str(tmp_path))
    for score in (0.51, 0.58, 0.63):
        ledger.record("B:OPERATOR", score)
    ledger.save()

    reloaded = PersistentWorthLedger(state_dir=str(tmp_path))
    assert reloaded.scores_for("B:OPERATOR") == [0.51, 0.58, 0.63]


def test_worth_ledger_window_is_bounded(tmp_path):
    ledger = PersistentWorthLedger(state_dir=str(tmp_path), window=8)
    for i in range(20):
        ledger.record("B:OPERATOR", i / 20.0)
    assert len(ledger.scores_for("B:OPERATOR")) == 8


class _FakeSediMemory:
    def __init__(self, results):
        self._results = results

    def recall_semantic(self, query_text="", *, max_results=8, axis_filter=None, min_score=0.35):
        self._last_call = {
            "query_text": query_text, "max_results": max_results,
            "axis_filter": axis_filter, "min_score": min_score,
        }
        return self._results


def test_recall_confidence_boost_returns_zero_without_sedimemory():
    assert recall_confidence_boost(None, "hello", "B") == 0.0


def test_recall_confidence_boost_returns_zero_with_no_resonant_results():
    fake = _FakeSediMemory([])
    assert recall_confidence_boost(fake, "hello", "B") == 0.0


def test_recall_confidence_boost_scales_with_top_score():
    fake = _FakeSediMemory([{"score": 0.9}])
    boost = recall_confidence_boost(fake, "hello", "B")
    assert 0.0 < boost <= 0.15  # RECALL_BOOST_CAP


def test_recall_confidence_boost_calls_recall_semantic_with_axis_filter():
    fake = _FakeSediMemory([{"score": 0.9}])
    recall_confidence_boost(fake, "hello there", "B")
    assert fake._last_call["axis_filter"] == ("B",)
    assert fake._last_call["query_text"] == "hello there"


def test_recall_confidence_boost_never_raises_on_broken_sedimemory():
    class _Broken:
        def recall_semantic(self, **kwargs):
            raise RuntimeError("boom")
    assert recall_confidence_boost(_Broken(), "hello", "B") == 0.0

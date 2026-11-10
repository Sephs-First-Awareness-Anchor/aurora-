"""Promotion lookup must remain strict, ordered, and efficient as Aurora grows."""
from __future__ import annotations

from types import SimpleNamespace

import concept_crystal as C


def test_promotion_lookup_is_strict_and_preserves_event_order():
    registry = C.ConceptCrystalRegistry()
    registry._promo_log = [
        {"ts": 10.0, "event": "a"},
        {"ts": 10.0, "event": "b"},
        {"ts": 11.0, "event": "c"},
        {"ts": 13.0, "event": "d"},
    ]
    assert [e["event"] for e in registry.drain_promotions(10.0)] == ["c", "d"]
    assert [e["event"] for e in registry.drain_promotions(13.0)] == []
    assert [e["event"] for e in registry.drain_promotions(0.0)] == ["a", "b", "c", "d"]


def test_promotion_lookup_does_not_scan_growing_lifetime_log():
    class MeasuredLog(list):
        item_lookups = 0

        def __getitem__(self, key):
            if isinstance(key, int):
                self.item_lookups += 1
            return super().__getitem__(key)

    registry = C.ConceptCrystalRegistry()
    registry._promo_log = MeasuredLog({"ts": float(i)} for i in range(100_000))
    fresh = registry.drain_promotions(99_990.0)
    assert [e["ts"] for e in fresh] == list(map(float, range(99_991, 100_000)))
    assert registry._promo_log.item_lookups < 30, "logarithmic boundary lookup expected"


def test_wall_clock_regression_preserves_original_full_scan_semantics(monkeypatch):
    registry = C.ConceptCrystalRegistry()
    stamps = iter([200.0, 150.0, 300.0])
    monkeypatch.setattr(C.time, "time", lambda: next(stamps))
    for i in range(3):
        registry._log_promotion(SimpleNamespace(node_id=str(i), stage="COMPOSITE"))
    assert registry._promo_log_monotonic is False
    assert [e["ts"] for e in registry.drain_promotions(175.0)] == [200.0, 300.0]

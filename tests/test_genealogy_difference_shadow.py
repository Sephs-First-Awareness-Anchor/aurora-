#!/usr/bin/env python3
"""
Tests for aurora_genealogy_difference_shadow.py (Phase 3A).

Establish, against real code shapes and real persisted data:

  1. replay_events() reproduces _accumulate_pairs()'s exact adjacent-pair
     rule and PairStats.update()'s exact axis-level accumulation shape.
  2. The DIFFERENCE companion channel attaches independently of, and never
     interferes with, the axis-level mirror.
  3. find_pairs_with_divergent_difference() (the killer experiment) is
     implemented correctly against a synthetic case built to qualify --
     since the real corpus (see #4) cannot exercise it.
  4. Against the REAL corpus: pair-forming events and DIFFERENCE-bearing
     events never overlap (the headline finding), locked in as a regression,
     not just asserted in prose.
  5. Against the REAL corpus: DIFFERENCE carries information beyond axis
     identity (non-dominant axes routinely carry real nonzero signal).
  6. This module never imports or can influence real promotion state.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from aurora_genealogy_difference_shadow import (
    ShadowPairStats,
    replay_events,
    measure_collision_differentiation,
    measure_information_beyond_axis_identity,
    measure_persistence_across_reused_links,
    find_pairs_with_divergent_difference,
    _axis_of_id,
)


def _record(trace_ids, relief=None, cost=None, risk=None, tick=1, difference_values=None, notes_extra=None):
    trace = [{"kind": "ABILITY", "id": tid} for tid in trace_ids]
    notes = dict(notes_extra or {})
    if difference_values is not None:
        notes["difference_snapshot"] = {"tick": tick, "warm_up": False, "values": difference_values, "refs": {}}
    return {
        "tick": tick,
        "trace": trace,
        "relief": relief or {"X": 0.0, "T": 0.0, "N": 0.0, "B": 0.0, "A": 0.0},
        "trace_cost_total": cost or {"X": 0.0, "T": 0.0, "N": 0.0, "B": 0.0, "A": 0.0},
        "trace_risk_total": risk or {"X": 0.0, "T": 0.0, "N": 0.0, "B": 0.0, "A": 0.0},
        "dominant_relief_axis": "X",
        "active_concepts": [],
        "notes": notes,
    }


class TestReplayMatchesRealPairingRule:
    def test_adjacent_pairs_extracted_in_order_from_multi_item_trace(self):
        records = [_record(["A:one", "B:two", "T:three", "N:four"])]
        pair_stats = replay_events(records)
        assert set(pair_stats.keys()) == {
            ("A:one", "B:two"), ("B:two", "T:three"), ("T:three", "N:four"),
        }

    def test_single_item_trace_forms_zero_pairs(self):
        records = [_record(["A:one"])]
        pair_stats = replay_events(records)
        assert pair_stats == {}

    def test_two_item_trace_forms_exactly_one_pair(self):
        records = [_record(["A:one", "B:two"])]
        pair_stats = replay_events(records)
        assert list(pair_stats.keys()) == [("A:one", "B:two")]

    def test_axis_accumulation_matches_real_pairstats_update(self):
        """Direct parity check against the real PairStats.update()."""
        from aurora_internal.constraint_genealogy import PairStats, PressureVec

        relief1 = {"X": 0.1, "T": 0.2, "N": 0.0, "B": 0.0, "A": 0.0}
        cost1 = {"X": 0.01, "T": 0.02, "N": 0.0, "B": 0.0, "A": 0.0}
        relief2 = {"X": 0.05, "T": 0.0, "N": 0.3, "B": 0.0, "A": 0.0}
        cost2 = {"X": 0.0, "T": 0.0, "N": 0.03, "B": 0.0, "A": 0.0}

        records = [
            _record(["A:one", "B:two"], relief=relief1, cost=cost1, tick=10),
            _record(["A:one", "B:two"], relief=relief2, cost=cost2, tick=11),
        ]
        pair_stats = replay_events(records)
        shadow = pair_stats[("A:one", "B:two")]

        real_ps = PairStats(left_id="A:one", right_id="B:two")
        real_ps.update(PressureVec(**relief1), cost1, 0.0, 10)
        real_ps.update(PressureVec(**relief2), cost2, 0.0, 11)

        assert shadow.count == real_ps.count
        for a in ("X", "T", "N", "B", "A"):
            assert shadow.relief_sum[a] == pytest.approx(real_ps.relief_sum[a])
            assert shadow.cost_sum[a] == pytest.approx(real_ps.cost_sum[a])


class TestDifferenceCompanionIndependence:
    def test_difference_companion_attaches_only_when_present(self):
        records = [
            _record(["A:one", "B:two"], tick=1, difference_values=None),
            _record(["A:one", "B:two"], tick=2, difference_values={"X": 0.5, "T": 0.0, "N": 0.0, "B": 0.0, "A": 0.0}),
        ]
        pair_stats = replay_events(records)
        shadow = pair_stats[("A:one", "B:two")]
        assert shadow.count == 2  # axis-level accumulation unaffected
        assert shadow.difference_participation_ticks == [2]
        assert shadow.difference_values_by_tick == {2: {"X": 0.5, "T": 0.0, "N": 0.0, "B": 0.0, "A": 0.0}}

    def test_axis_of_id_uses_link_dominant_axis_and_ability_prefix(self):
        links_index = {"L:abc": {"dominant_relief_axis": "B"}}
        assert _axis_of_id("L:abc", links_index) == "B"
        assert _axis_of_id("T:ADVANCE_TICK", links_index) == "T"
        assert _axis_of_id("not_a_valid_id", links_index) is None


class TestKillerExperimentLogic:
    def test_finds_synthetic_divergent_candidate(self):
        """Built to qualify: two pair-keys, same current_signature (both
        A-axis -> B-axis), similar mean relief, one carries real DIFFERENCE
        signal and the other never does."""
        records = [
            _record(["A:one", "B:two"], relief={"X": 0.1, "T": 0.0, "N": 0.0, "B": 0.0, "A": 0.0}, tick=1,
                    difference_values={"X": 0.3, "T": 0.0, "N": 0.0, "B": 0.0, "A": 0.0}),
            _record(["A:three", "B:four"], relief={"X": 0.1, "T": 0.0, "N": 0.0, "B": 0.0, "A": 0.0}, tick=2,
                    difference_values=None),
        ]
        pair_stats = replay_events(records)
        candidates = find_pairs_with_divergent_difference(pair_stats, links_index={})
        assert len(candidates) == 1
        c = candidates[0]
        assert {c["pair_a"], c["pair_b"]} == {("A:one", "B:two"), ("A:three", "B:four")}
        assert c["difference_present_a"] != c["difference_present_b"]

    def test_no_candidate_when_signatures_differ(self):
        records = [
            _record(["A:one", "B:two"], tick=1, difference_values={"X": 0.3, "T": 0.0, "N": 0.0, "B": 0.0, "A": 0.0}),
            _record(["A:three", "N:four"], tick=2, difference_values=None),  # different signature (B vs N)
        ]
        pair_stats = replay_events(records)
        candidates = find_pairs_with_divergent_difference(pair_stats, links_index={})
        assert candidates == []

    def test_no_candidate_when_both_sides_share_difference_presence(self):
        records = [
            _record(["A:one", "B:two"], tick=1, difference_values={"X": 0.3, "T": 0.0, "N": 0.0, "B": 0.0, "A": 0.0}),
            _record(["A:three", "B:four"], tick=2, difference_values={"X": 0.4, "T": 0.0, "N": 0.0, "B": 0.0, "A": 0.0}),
        ]
        pair_stats = replay_events(records)
        candidates = find_pairs_with_divergent_difference(pair_stats, links_index={})
        assert candidates == []


class TestInformationBeyondAxisIdentity:
    def test_detects_nonzero_non_dominant_axis_signal(self):
        records = [
            _record(["A:one"], tick=1, difference_values={"X": 0.01, "T": 0.2, "N": 0.0, "B": 0.0, "A": 0.0},
                     notes_extra={}),
        ]
        # dominant_relief_axis defaults to "X" in the _record() helper
        result = measure_information_beyond_axis_identity(records)
        assert result["records_with_nonzero_non_dominant_axis_value"] >= 1

    def test_all_zero_beyond_dominant_axis_finds_nothing(self):
        records = [
            _record(["A:one"], tick=1, difference_values={"X": 0.2, "T": 0.0, "N": 0.0, "B": 0.0, "A": 0.0}),
        ]
        result = measure_information_beyond_axis_identity(records)
        assert result["records_with_nonzero_non_dominant_axis_value"] == 0


class TestRealCorpusRegressions:
    """Lock in the actual empirical findings from the real fossil data as
    enforced regressions, not just report prose."""

    @pytest.fixture(scope="class")
    @classmethod
    def real_data(cls):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        links_path = os.path.join(root, "aurora_state", "genealogy", "links.json")
        events_path = os.path.join(root, "aurora_state", "genealogy", "events_recent.json")
        if not (os.path.exists(links_path) and os.path.exists(events_path)):
            pytest.skip("real genealogy fossils not present in this checkout")
        with open(links_path, "r", encoding="utf-8") as f:
            links_index = json.load(f)
        with open(events_path, "r", encoding="utf-8") as f:
            records = list(json.load(f).get("records") or [])
        return links_index, records

    def test_real_corpus_shows_zero_pair_difference_overlap(self, real_data):
        """The headline Phase 3A finding: in this corpus, no pair-forming
        event ever carries a real DIFFERENCE signal."""
        links_index, records = real_data
        pair_stats = replay_events(records, links_index)
        assert len(pair_stats) > 0, "sanity: replay should find real pairs in this corpus"
        n_with_difference = sum(1 for ps in pair_stats.values() if ps.difference_participation_ticks)
        assert n_with_difference == 0

    def test_real_corpus_all_difference_bearing_records_are_single_item_traces(self, real_data):
        _, records = real_data
        from aurora_genealogy_promotion_dimension_observer import classify_promotion_relevant_dimension_participation

        nontrivial = [r for r in records if classify_promotion_relevant_dimension_participation(r).difference_values_nontrivial]
        assert len(nontrivial) > 0, "sanity: real corpus should contain some real DIFFERENCE signal"
        assert all(len(r.get("trace") or []) == 1 for r in nontrivial)

    def test_real_corpus_shows_information_beyond_axis_identity(self, real_data):
        _, records = real_data
        result = measure_information_beyond_axis_identity(records)
        assert result["records_with_nonzero_non_dominant_axis_value"] > 0

    def test_real_corpus_killer_experiment_correctly_returns_empty(self, real_data):
        """Not a bug -- see module docstring. Locked in so a future corpus
        where this stops being empty is a visible, deliberate change."""
        links_index, records = real_data
        pair_stats = replay_events(records, links_index)
        candidates = find_pairs_with_divergent_difference(pair_stats, links_index)
        assert candidates == []


class TestPurelyObservational:
    def test_module_never_imports_constraint_genealogy_promotion_surfaces(self):
        import aurora_genealogy_difference_shadow as mod
        import ast
        import inspect

        tree = ast.parse(inspect.getsource(mod))
        imported_modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module)
        assert not any("constraint_genealogy" in m for m in imported_modules)
        assert not hasattr(mod, "ConstraintGenealogyLogger")
        assert not hasattr(mod, "PairStats")

    def test_replay_and_measurements_are_pure(self):
        real_state_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aurora_state"
        )
        before = set(os.listdir(real_state_dir))
        records = [_record(["A:one", "B:two"], tick=1, difference_values={"X": 0.1, "T": 0, "N": 0, "B": 0, "A": 0})]
        pair_stats = replay_events(records)
        measure_collision_differentiation(pair_stats, {})
        measure_information_beyond_axis_identity(records)
        measure_persistence_across_reused_links(pair_stats, records, {})
        find_pairs_with_divergent_difference(pair_stats, {})
        after = set(os.listdir(real_state_dir))
        assert before == after


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))

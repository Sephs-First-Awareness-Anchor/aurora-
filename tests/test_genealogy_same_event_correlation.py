#!/usr/bin/env python3
"""
Tests for aurora_genealogy_same_event_correlation.py (Phase 3A.3).

Establishes the three-outcome classification on synthetic data built to
exercise each case precisely, then locks in the real, actual finding
against the real fossil corpus.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from aurora_genealogy_same_event_correlation import (
    analyze_same_event_correlation,
    extract_identity_fields,
    IDENTITY_KEYS,
)


def _diff_record(notes_extra=None, values=None):
    values = values or {"X": 0.3, "T": 0.0, "N": 0.0, "B": 0.0, "A": 0.0}
    return {
        "trace": [{"kind": "LINK", "id": "L:x"}],  # single-item -- not pair-eligible
        "notes": {"difference_snapshot": {"tick": 1, "warm_up": False, "values": values, "refs": {}}, **(notes_extra or {})},
        "active_concepts": [],
    }


def _pair_record(notes_extra=None):
    return {
        "trace": [{"kind": "ABILITY", "id": "A:one"}, {"kind": "ABILITY", "id": "B:two"}],
        "notes": dict(notes_extra or {}),
        "active_concepts": [],
    }


class TestExtractIdentityFields:
    def test_extracts_known_identity_keys(self):
        notes = {"session_id": "abc", "tag": "irrelevant", "clarity": 0.5}
        assert extract_identity_fields(notes) == {"session_id": "abc"}

    def test_empty_or_missing_values_excluded(self):
        notes = {"session_id": "", "turn_id": None, "episode_id": "e1"}
        assert extract_identity_fields(notes) == {"episode_id": "e1"}

    def test_tick_is_not_an_identity_key(self):
        assert "tick" not in IDENTITY_KEYS


class TestOutcomeClassification:
    def test_outcome_1_same_event_disconnected_paths(self):
        records = [
            _diff_record({"session_id": "shared_session_1"}),
            _pair_record({"session_id": "shared_session_1"}),
            _pair_record({"session_id": "other_session"}),
        ]
        result = analyze_same_event_correlation(records)
        assert result.outcome == "1_same_event_disconnected_paths"
        assert result.shared_identity_values.get("session_id") == ["shared_session_1"]

    def test_outcome_2_different_event_populations(self):
        records = [
            _diff_record({"seed_lineage_id": "dream_episode"}),
            _pair_record({"session_id": "sim_123"}),
        ]
        result = analyze_same_event_correlation(records)
        assert result.outcome == "2_different_event_populations"
        assert result.shared_identity_keys == set()

    def test_outcome_3_same_sequence_different_moments(self):
        """Same KIND of identifier appears on both sides, but never the
        same actual value -- e.g. both populations carry a session_id, but
        no session_id instance is shared."""
        records = [
            _diff_record({"session_id": "producer_session_A"}),
            _pair_record({"session_id": "consumer_session_B"}),
        ]
        result = analyze_same_event_correlation(records)
        assert result.outcome == "3_same_sequence_different_moments"
        assert result.shared_identity_keys == {"session_id"}
        assert result.shared_identity_values == {}

    def test_insufficient_data_when_either_population_empty(self):
        assert analyze_same_event_correlation([_diff_record()]).outcome == "insufficient_data"
        assert analyze_same_event_correlation([_pair_record()]).outcome == "insufficient_data"
        assert analyze_same_event_correlation([]).outcome == "insufficient_data"


class TestRealCorpusRegression:
    """Locks in the actual finding against the real fossil corpus: zero
    shared identity vocabulary between the two populations -- Outcome 2."""

    @pytest.fixture(scope="class")
    @classmethod
    def real_records(cls):
        # Pinned to a committed snapshot (tests/fixtures/), not the live
        # aurora_state/genealogy/events_recent.json path -- found, running
        # the full suite, that some OTHER test boots a real
        # ConstraintGenealogyLogger against that live path and overwrites it
        # (31259 lines -> 1), which made this "real corpus" regression
        # flaky depending on test order/full-suite-vs-isolated runs.
        path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "fixtures", "genealogy_events_recent_snapshot.json",
        )
        if not os.path.exists(path):
            pytest.skip("tests/fixtures/genealogy_events_recent_snapshot.json not present in this checkout")
        with open(path, "r", encoding="utf-8") as f:
            return list(json.load(f).get("records") or [])

    def test_real_corpus_shows_different_event_populations(self, real_records):
        result = analyze_same_event_correlation(real_records)
        assert result.producer_count > 0
        assert result.consumer_count > 0
        assert result.outcome == "2_different_event_populations"
        assert result.shared_identity_keys == set()
        assert result.shared_identity_values == {}

    def test_real_corpus_producer_and_consumer_identity_vocabularies(self, real_records):
        result = analyze_same_event_correlation(real_records)
        # Real, confirmed vocabulary as of this corpus -- a regression guard
        # so any future change in what identity fields exist is visible.
        assert result.producer_identity_keys == {
            "constraint_combo_id", "operation_lineage_id", "seed_lineage_id",
        }
        assert result.consumer_identity_keys == {"session_id", "time_index"}


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))

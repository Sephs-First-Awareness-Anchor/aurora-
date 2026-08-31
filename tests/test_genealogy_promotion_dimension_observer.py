#!/usr/bin/env python3
"""
Tests for aurora_genealogy_promotion_dimension_observer.py (Phase 2).

These establish, against real code and real persisted Aurora data:

  1. Promotion's own live input surface (PairStats.update()) is structurally
     axis-only — no dimension-typed parameter exists for it to receive, even
     in principle.
  2. observe() computes a genuinely dimension-typed live quantity
     (DifferenceSnapshot) at the very same tick, but never forwards it to
     pair accumulation / promotion.
  3. The observer's extraction functions correctly parse the real, on-disk
     shapes these quantities are persisted in.
  4. Run against the real aurora_state/genealogy/events_recent.json corpus,
     the observer finds actual, non-trivial, non-OPERATOR/COST dimension
     participation in real live data — i.e. this is a measured finding, not
     just a theoretical capability of the observer.
  5. This module never imports or calls anything that could alter promotion
     behavior for any real Aurora run.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
import inspect
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from aurora_genealogy_promotion_dimension_observer import (
    classify_promotion_relevant_dimension_participation,
    difference_values_are_nontrivial,
    extract_difference_dimension_signal,
    extract_tensor_dimension_labels,
    summarize_corpus,
    NONOPERATOR_COST_DIMENSIONS,
)


class TestPromotionInputIsStructurallyAxisOnly:
    def test_pairstats_update_signature_carries_no_dimension_channel(self):
        from aurora_internal.constraint_genealogy import PairStats

        sig = inspect.signature(PairStats.update)
        param_names = list(sig.parameters.keys())
        assert param_names == ["self", "relief", "cost", "x_risk", "tick"], (
            "PairStats.update()'s signature is the complete live input surface "
            "for promotion. If this changes to add a dimension-typed parameter, "
            "the structural finding in this module's docstring needs updating."
        )
        # Every parameter's annotation is axis-keyed (PressureVec / Dict[str, float] /
        # float / int) -- none is NonCompDimension-shaped.
        for forbidden in ("Dimension", "NonComp"):
            assert forbidden not in str(sig), (
                f"PairStats.update() signature now mentions {forbidden!r} -- "
                "promotion may no longer be structurally axis-only; re-verify "
                "the Phase 2 finding."
            )

    def test_observe_never_forwards_difference_snapshot_to_pair_accumulation(self):
        from aurora_internal.constraint_genealogy import ConstraintGenealogyLogger

        # Repair N wrapped observe()'s real ~350-line body in _observe_impl()
        # behind a concurrency lock (constraint_genealogy.py's own docstring
        # on observe()) -- observe() itself is now a thin public entry-point
        # stub that just calls self._observe_impl(...); _accumulate_pairs()
        # lives in _observe_impl(), not in observe() directly. Inspect the
        # real body, not the stub, so this test tracks the actual wiring
        # rather than becoming permanently stale relative to that refactor.
        source = inspect.getsource(ConstraintGenealogyLogger._observe_impl)
        accumulate_calls = [
            line.strip() for line in source.splitlines()
            if "_accumulate_pairs(" in line
        ]
        assert accumulate_calls, "_observe_impl() no longer calls _accumulate_pairs() -- re-verify wiring."
        for call in accumulate_calls:
            assert "difference_snapshot" not in call, (
                f"observe() now forwards difference_snapshot into pair accumulation "
                f"({call!r}) -- the Phase 2 finding (dimension data computed live but "
                f"excluded from promotion's input) may no longer hold."
            )


class TestExtractionAgainstRealShapes:
    def test_extract_difference_dimension_signal_reads_real_notes_shape(self):
        # Exact shape confirmed against a real aurora_state/genealogy/events_recent.json
        # record and against DifferenceSnapshot.to_dict() (aurora_difference_buffer.py).
        notes = {
            "difference_snapshot": {
                "tick": 94,
                "warm_up": False,
                "values": {"X": 0.0, "T": -0.020997, "N": -0.039073, "B": 0.000887, "A": -0.000578},
                "refs": {"X": 0.00219, "T": 0.461074, "N": 0.426125, "B": 0.45, "A": 0.926452},
            }
        }
        values = extract_difference_dimension_signal(notes)
        assert values == {"X": 0.0, "T": -0.020997, "N": -0.039073, "B": 0.000887, "A": -0.000578}
        assert difference_values_are_nontrivial(values) is True

    def test_extract_difference_dimension_signal_absent(self):
        assert extract_difference_dimension_signal({}) is None
        assert extract_difference_dimension_signal({"difference_snapshot": None}) is None
        assert difference_values_are_nontrivial(None) is False

    def test_all_zero_difference_values_are_trivial(self):
        values = {a: 0.0 for a in ("X", "T", "N", "B", "A")}
        assert difference_values_are_nontrivial(values) is False

    def test_extract_tensor_dimension_labels_parses_real_concept_string(self):
        # Verbatim string observed in aurora_state/genealogy/events_recent.json,
        # produced by cers_tensor_locator.record_tensor_trace().
        concepts = ["tensor:MANIFOLD:X:NC[N:COST]xNC[T:DIFFERENCE]", "climate", "changing"]
        labels = extract_tensor_dimension_labels(concepts)
        assert labels == ["COST", "DIFFERENCE"]

    def test_extract_tensor_dimension_labels_ignores_non_tensor_concepts(self):
        assert extract_tensor_dimension_labels(["recalled:corpus", "2013", None]) == []
        assert extract_tensor_dimension_labels(None) == []

    def test_classify_flags_non_operator_cost_participation(self):
        record = {
            "dominant_relief_axis": "X",
            "active_concepts": ["tensor:MANIFOLD:X:NC[N:COST]xNC[T:DIFFERENCE]"],
            "notes": {},
        }
        reading = classify_promotion_relevant_dimension_participation(record)
        assert reading.non_operator_cost_tensor_dims == ["DIFFERENCE"]
        assert reading.shows_non_operator_cost_participation is True
        assert reading.difference_signal_present is False

    def test_classify_pure_operator_cost_record_shows_no_participation(self):
        record = {
            "dominant_relief_axis": "T",
            "active_concepts": ["tensor:MANIFOLD:X:NC[X:OPERATOR]xNC[T:COST]"],
            "notes": {},
        }
        reading = classify_promotion_relevant_dimension_participation(record)
        assert reading.non_operator_cost_tensor_dims == []
        assert reading.shows_non_operator_cost_participation is False


class TestRealCorpusMeasurement:
    """These assert against the REAL fossil file, not a synthetic fixture --
    this is the actual empirical finding this phase set out to establish,
    locked in as a regression."""

    @pytest.fixture(scope="class")
    @classmethod
    def real_records(cls):
        # Pinned to a committed snapshot (tests/fixtures/), not the live
        # aurora_state/genealogy/events_recent.json path: found, running the
        # full suite, that some OTHER test boots a real ConstraintGenealogyLogger
        # against that live path and overwrites it (31259 lines -> 1),
        # which made this "real corpus" regression flaky depending on test
        # order/full-suite-vs-isolated runs. The snapshot is the exact real
        # corpus this phase's findings were measured against.
        path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "fixtures", "genealogy_events_recent_snapshot.json",
        )
        if not os.path.exists(path):
            pytest.skip("tests/fixtures/genealogy_events_recent_snapshot.json not present in this checkout")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return list(data.get("records") or [])

    def test_real_corpus_is_nonempty(self, real_records):
        assert len(real_records) > 0

    def test_real_corpus_shows_measured_non_operator_cost_participation(self, real_records):
        summary = summarize_corpus(real_records)
        assert summary.record_count == len(real_records)
        # The empirical finding: real, live formation dynamics DID engage a
        # dimension the genealogy atoms cannot preserve, in this real corpus.
        assert summary.any_non_operator_cost_signal_count > 0
        assert summary.difference_nontrivial_count > 0
        assert set(summary.non_operator_cost_dimension_counts.keys()) <= NONOPERATOR_COST_DIMENSIONS

    def test_difference_signal_when_present_is_always_nontrivial_in_this_corpus(self, real_records):
        """Whenever DifferenceSnapshot was actually computed for a tick in
        this real corpus, it never came back as a dead/zeroed snapshot."""
        summary = summarize_corpus(real_records)
        assert summary.difference_signal_present_count == summary.difference_nontrivial_count

    def test_summary_fractions_are_bounded(self, real_records):
        summary = summarize_corpus(real_records).to_dict()
        for key, stat in summary.items():
            if isinstance(stat, dict) and "fraction" in stat:
                assert 0.0 <= stat["fraction"] <= 1.0


class TestPurelyObservational:
    def test_module_never_imports_constraint_genealogy_at_all(self):
        """The real safety property: this module must have no import path to
        ConstraintGenealogyLogger/PairStats/_try_promote whatsoever, so it
        cannot execute or influence them even by accident. (Its docstring and
        function docstrings legitimately DISCUSS these exact names in prose
        -- that's the investigation's own finding -- so a text scan for the
        names would false-positive on its own documentation; checking real
        imports is the precise version of the same check.)"""
        import aurora_genealogy_promotion_dimension_observer as mod
        import ast

        tree = ast.parse(inspect.getsource(mod))
        imported_modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module)

        assert not any("constraint_genealogy" in m for m in imported_modules), (
            f"aurora_genealogy_promotion_dimension_observer.py must not import "
            f"constraint_genealogy at all; found imports: {imported_modules}"
        )
        assert not hasattr(mod, "ConstraintGenealogyLogger")
        assert not hasattr(mod, "PairStats")

    def test_summarize_corpus_is_pure(self, tmp_path):
        real_state_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aurora_state"
        )
        before = set(os.listdir(real_state_dir))
        summarize_corpus([{"dominant_relief_axis": "X", "active_concepts": [], "notes": {}}])
        after = set(os.listdir(real_state_dir))
        assert before == after


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))

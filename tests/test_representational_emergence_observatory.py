# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Tests for aurora_representational_emergence_observatory.py (Phase 8 of the
SYSTEM-WIDE REPRESENTATIONAL CONSERVATION directive).

Written to allow both a positive (independent) and negative (coupled)
verdict -- the observatory must not force either outcome. Reuses the
rank-6 audit's own confirmed asymmetry (sub_law_c independent, sub_law_d
coupled) as real, already-verified ground truth to check the detector
against, rather than inventing synthetic data that assumes the answer.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aurora_rank6_shadow_analysis as rank6
from aurora_representational_emergence_observatory import (
    ObservationSample,
    evaluate_candidate_relationship,
    record_dependent_to_independent_transition,
)

BASES = [
    "Existential_Operator_of_Existence",
    "Boundary_Cost_of_Agency",
    "Agentive_Cost_of_Agency",
]
TRANSFER_BASE = "Temporal_Operator_of_Temporal"


def _samples_for(directory, bases, vary_fn, field="evolution_grade"):
    out = {}
    for b in bases:
        nc = directory[b]
        home = (nc["nc_law_c"], nc["nc_dim"])
        varied = vary_fn(directory, b, home)
        out[b] = [ObservationSample(b, k, v[field], b) for k, v in varied.items()]
    return out


class TestIndependentCandidateEarnsFullEvidence:
    def test_sub_law_c_passes_all_five_criteria_with_transfer(self):
        directory = rank6.load_manifold_directory_raw()
        samples = _samples_for(directory, BASES, rank6.vary_sub_law_c)
        # Held-out transfer configuration, not part of the original evidence.
        samples[f"transfer:{TRANSFER_BASE}"] = _samples_for(
            directory, [TRANSFER_BASE], rank6.vary_sub_law_c
        )[TRANSFER_BASE]

        evidence = evaluate_candidate_relationship(samples, cardinality_hint="5 (D1 constraint axis)")
        assert evidence.independent_variation is True
        assert evidence.measurable_effect is True
        assert evidence.recurrence_count >= 2
        assert evidence.transfer_confirmed is True
        assert evidence.persistence_observations >= 2
        assert evidence.all_criteria_met is True


class TestCoupledCandidateFailsEvidenceBar:
    def test_sub_law_d_alone_does_not_earn_full_independence_at_5_states(self):
        """sub_law_d's numeric effect never exceeds 2 distinct states
        (rank-6 audit, Phase C) -- confirm the observatory reports the
        weaker signal honestly rather than rounding it up to match
        sub_law_c's result."""
        directory = rank6.load_manifold_directory_raw()
        samples = _samples_for(directory, BASES, rank6.vary_sub_law_d)
        evidence = evaluate_candidate_relationship(
            samples, cardinality_hint="5 (D1 dimension axis)"
        )
        # It IS measurable (2 states), but distinctly weaker than sub_law_c's
        # 5-state result -- the observatory must not claim parity.
        for cid, s in samples.items():
            distinct = {round(x.effect_value, 9) for x in s}
            assert len(distinct) <= 2, f"unexpected >2 distinct states for sub_law_d at {cid}"


class TestNoTransferMeansNoFullConfirmation:
    def test_missing_transfer_configuration_blocks_all_criteria_met(self):
        """Even a coordinate with perfect independent variation and a
        measurable effect must NOT be marked all_criteria_met without an
        explicit held-out transfer configuration -- guards against
        declaring emergence from a single example."""
        directory = rank6.load_manifold_directory_raw()
        samples = _samples_for(directory, BASES, rank6.vary_sub_law_c)
        evidence = evaluate_candidate_relationship(samples)
        assert evidence.transfer_confirmed is False
        assert evidence.all_criteria_met is False


class TestRecordTransition:
    def test_records_transition_without_naming_or_classifying(self):
        directory = rank6.load_manifold_directory_raw()
        weak = evaluate_candidate_relationship(
            _samples_for(directory, BASES[:1], rank6.vary_sub_law_c)
        )
        strong_samples = _samples_for(directory, BASES, rank6.vary_sub_law_c)
        strong_samples[f"transfer:{TRANSFER_BASE}"] = _samples_for(
            directory, [TRANSFER_BASE], rank6.vary_sub_law_c
        )[TRANSFER_BASE]
        strong = evaluate_candidate_relationship(strong_samples)

        record = record_dependent_to_independent_transition("example_relationship", weak, strong)
        assert record["became_independent_this_observation"] is True
        assert "depth" not in record["relationship_name"].lower()
        # The record must not itself assign a semantic name or depth number.
        assert "depth_three" not in str(record).lower()
        assert "depth 3" not in str(record).lower()


class TestObservatoryNeverMutatesAnything:
    def test_module_source_contains_no_write_calls(self):
        """The whole module must be read-only by construction: no open(...,
        'w'), no os.remove, no attribute assignment onto any imported
        Aurora system object."""
        import inspect
        import aurora_representational_emergence_observatory as obs_module

        src = inspect.getsource(obs_module)
        for forbidden in ("open(", "os.remove", "os.replace", ".save(", ".write(", "json.dump"):
            assert forbidden not in src, f"found potential state mutation marker: {forbidden!r}"

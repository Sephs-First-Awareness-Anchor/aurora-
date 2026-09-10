# Authors: Sunni (Sir) Morningstar & Ceph
"""Focused audit for a same-occurrence duplicate-target boundary.

PR #224 moved relational crystal/facet link work behind a correct two-pass
barrier. Before Pass 1 is parallelized, duplicate signals aimed at the SAME
crystal must also be understood. The running constraint_signature uses an
80/20 recurrence update, so two sibling samples with different values are
mathematically order-sensitive when fed directly to process_concepts().

The normal production path does not do that: ConceptExtractor.extract()
deduplicates by concept before DimensionalSystems calls dps.process_concepts().
These tests pin both facts so later concurrency work has an explicit boundary
rather than an undocumented assumption.
"""
from __future__ import annotations

from aurora_dimensional_systems import ConceptExtractor, EvolutionTracker


def _current_signature_update(start: float, sibling_values: list[float]) -> float:
    value = float(start)
    for sample in sibling_values:
        value = round(value * 0.8 + float(sample) * 0.2, 4)
    return value


def test_current_running_signature_update_is_not_permutation_invariant_for_siblings():
    """Characterize why same-target siblings cannot be casually parallelized."""
    forward = _current_signature_update(0.4, [0.1, 0.9])
    reverse = _current_signature_update(0.4, [0.9, 0.1])

    assert forward != reverse
    assert forward == 0.452
    assert reverse == 0.42


def test_production_extractor_emits_at_most_one_signal_per_concept_per_occurrence():
    """The live DimensionalSystems path relies on distinct concept targets.

    Repeated surface tokens are one occurrence-level concept observation,
    not multiple sibling commits to the same Crystal. Keep the strongest
    confidence in ConceptExtractor's existing `seen` map and emit once.
    """

    class _Envelope:
        data = "Aurora aurora AURORA, signal signal SIGNAL."

    extractor = ConceptExtractor(EvolutionTracker())
    signals = extractor.extract(_Envelope(), existing_crystals={})
    concepts = [signal.concept for signal in signals]

    assert concepts
    assert len(concepts) == len(set(concepts))
    assert concepts.count("aurora") == 1
    assert concepts.count("signal") == 1

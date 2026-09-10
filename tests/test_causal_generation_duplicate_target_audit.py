# Authors: Sunni (Sir) Morningstar & Ceph
"""Focused audit for a remaining same-occurrence order-dependence question.

PR #224 moved relational crystal/facet link work behind a correct two-pass
barrier. Before Pass 1 is parallelized, duplicate signals aimed at the SAME
crystal must also be proven order-independent. The running constraint_signature
uses an 80/20 recurrence update, so two sibling samples with different values
would ordinarily produce different results when swapped.

This file does not guess whether duplicate concepts are allowed upstream. It
pins the mathematical hazard as an explicit characterization test so the next
repair can choose the correct contract: assert duplicate-target impossibility,
or fold sibling contributions before one crystal commit.
"""
from __future__ import annotations


def _current_signature_update(start: float, sibling_values: list[float]) -> float:
    value = float(start)
    for sample in sibling_values:
        value = round(value * 0.8 + float(sample) * 0.2, 4)
    return value


def test_current_running_signature_update_is_not_permutation_invariant_for_siblings():
    """Characterization, not a desired end-state assertion.

    This deliberately proves the residual hazard exists in the recurrence
    formula itself. A later production repair should replace this test with
    an end-to-end process_concepts permutation invariant (or an upstream
    uniqueness invariant) once the intended duplicate-target contract is
    resolved from real signal production.
    """
    forward = _current_signature_update(0.4, [0.1, 0.9])
    reverse = _current_signature_update(0.4, [0.9, 0.1])

    assert forward != reverse
    assert forward == 0.484
    assert reverse == 0.452

# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Coverage for CERS Phase 2: prediction_field.py fed from the same constraint
manifold the tensor-trace pass resolves onto, per the user's scoping call
("predictive frames should honestly be generated from that same thing").

build_prediction_signal() stays decoupled from CERS/crystal internals --
it receives plain manifold_axis (str) / manifold_familiarity (float) values,
not a SlotCoord or Crystal, so this module's own tests don't need the
manifold router or crystal registry at all.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aurora_internal.dual_strata.prediction_field import build_prediction_signal


def test_manifold_axis_backstops_empty_axis_signature():
    signal = build_prediction_signal(
        payload="hello",
        evidence={},
        contract_snapshot={},
        manifold_axis="N",
    )
    assert signal.prediction_payload.axis_signature == "N"


def test_evidence_axis_still_wins_over_manifold_axis():
    signal = build_prediction_signal(
        payload="hello",
        evidence={"dominant_axis": "B"},
        contract_snapshot={},
        manifold_axis="N",
    )
    assert signal.prediction_payload.axis_signature == "B"


def test_no_manifold_axis_behaves_exactly_as_before():
    signal = build_prediction_signal(
        payload="hello", evidence={}, contract_snapshot={},
    )
    assert signal.prediction_payload.axis_signature == ""
    assert signal.source == "runtime_evidence"


def test_high_familiarity_raises_confidence_over_baseline():
    baseline = build_prediction_signal(payload="hello", evidence={}, contract_snapshot={})
    familiar = build_prediction_signal(
        payload="hello", evidence={}, contract_snapshot={}, manifold_familiarity=1.0,
    )
    assert familiar.confidence > baseline.confidence
    assert familiar.prediction_payload.certainty_band in ("medium", "high")


def test_zero_familiarity_lowers_confidence_below_baseline():
    baseline = build_prediction_signal(payload="hello", evidence={}, contract_snapshot={})
    novel = build_prediction_signal(
        payload="hello", evidence={}, contract_snapshot={}, manifold_familiarity=0.0,
    )
    assert novel.confidence < baseline.confidence


def test_manifold_familiarity_present_marks_source():
    signal = build_prediction_signal(
        payload="hello", evidence={}, contract_snapshot={}, manifold_familiarity=0.5,
    )
    assert signal.source.endswith("+manifold")


def test_manifold_familiarity_none_does_not_mark_source():
    signal = build_prediction_signal(payload="hello", evidence={}, contract_snapshot={})
    assert "+manifold" not in signal.source

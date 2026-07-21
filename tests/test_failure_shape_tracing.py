# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
R1.6 Remediation Addendum (2026-07-15): failure-shape tracing.

contradiction_handling and uncertainty_signaling are confirmed real
capability floors (R1.5 golden validation), not broken instruments. This
addendum determines WHERE the zero lives, per probe: PERCEIVE (content
never becomes an internal event), EXPRESS (internal event fires but gets
dropped before articulation), or VOCABULARY (she expresses it in her own
register but the predicate listens for ours).

Pre-flight established the guard-block hypothesis is CLEARED by direct
evidence: UncertaintySignalingGuard/FailureGuardSuite/ConstraintEngine
are never instantiated in the live boot_aurora() path (zero call sites
for feed_evidence/govern/acknowledge_uncertainty/check_all outside
aurora_constraint_engine.py's own self-test). These tests hold
classify_probe_trace()'s mechanical rules to that finding directly.
"""
from aurora_internal.aurora_semantic_probe_battery import (
    Probe,
    ProbeTrace,
    classify_probe_trace,
    failure_shape_distribution,
)


def _contra_probe():
    return Probe(
        probe_id="contradiction_handling_01", dimension="contradiction_handling",
        turns=["x"], expected_properties=["acknowledges_contradiction", "parseable"],
    )


def _uncertainty_probe():
    return Probe(
        probe_id="uncertainty_signaling_01", dimension="uncertainty_signaling",
        turns=["x"], expected_properties=["hedges", "parseable"],
    )


def test_passed_probe_is_not_classified_as_a_failure():
    p = _contra_probe()
    cls, detail = classify_probe_trace(
        p, ledger_delta=1, predicate_results={"acknowledges_contradiction": True, "parseable": True},
        response_text="however, that's a real conflict",
    )
    assert cls == "PASSED"


def test_contradiction_handling_no_ledger_delta_is_perceive():
    p = _contra_probe()
    cls, detail = classify_probe_trace(
        p, ledger_delta=0, predicate_results={"acknowledges_contradiction": False, "parseable": True},
        response_text="okay, sounds good.",
    )
    assert cls == "PERCEIVE"
    assert "ContradictionLedger" in detail


def test_contradiction_handling_ledger_fired_no_signal_is_express():
    p = _contra_probe()
    cls, detail = classify_probe_trace(
        p, ledger_delta=1, predicate_results={"acknowledges_contradiction": False, "parseable": True},
        response_text="I understand, that's fine.",
    )
    assert cls == "EXPRESS"
    assert "guard-block is ruled out" in detail


def test_contradiction_handling_ledger_fired_with_plausible_phrase_is_vocabulary():
    p = _contra_probe()
    cls, detail = classify_probe_trace(
        p, ledger_delta=1, predicate_results={"acknowledges_contradiction": False, "parseable": True},
        response_text="Something about this feels inconsistent to me.",
    )
    assert cls == "VOCABULARY"
    assert "inconsistent" in detail


def test_uncertainty_signaling_never_produces_perceive_or_express():
    """No live internal telemetry exists for uncertainty at all -- the
    classifier must never claim PERCEIVE or EXPRESS for this dimension,
    only VOCABULARY (plausible phrase found) or UNCLASSIFIED (none found)."""
    p = _uncertainty_probe()
    cls_no_phrase, _ = classify_probe_trace(
        p, ledger_delta=0, predicate_results={"hedges": False, "parseable": True},
        response_text="It will definitely happen exactly like that.",
    )
    assert cls_no_phrase == "UNCLASSIFIED"

    cls_phrase, detail = classify_probe_trace(
        p, ledger_delta=0, predicate_results={"hedges": False, "parseable": True},
        response_text="Honestly, hard to say -- could go either way.",
    )
    assert cls_phrase == "VOCABULARY"
    assert "hard to say" in detail


def test_uncertainty_signaling_ledger_delta_is_ignored():
    """Ledger delta is meaningless for uncertainty_signaling (no such
    mechanism exists) -- classification must not vary with it."""
    p = _uncertainty_probe()
    cls_a, _ = classify_probe_trace(
        p, ledger_delta=0, predicate_results={"hedges": False, "parseable": True}, response_text="x",
    )
    cls_b, _ = classify_probe_trace(
        p, ledger_delta=5, predicate_results={"hedges": False, "parseable": True}, response_text="x",
    )
    assert cls_a == cls_b == "UNCLASSIFIED"


def test_unknown_dimension_never_forces_a_classification():
    p = Probe(probe_id="x1", dimension="some_other_dimension", turns=["x"], expected_properties=["parseable"])
    cls, detail = classify_probe_trace(
        p, ledger_delta=0, predicate_results={"parseable": False}, response_text="garbled",
    )
    assert cls == "UNCLASSIFIED"


def test_failure_shape_distribution_counts_per_dimension():
    traces = [
        ProbeTrace(probe_id="a", dimension="contradiction_handling", classification="PERCEIVE"),
        ProbeTrace(probe_id="b", dimension="contradiction_handling", classification="EXPRESS"),
        ProbeTrace(probe_id="c", dimension="contradiction_handling", classification="PERCEIVE"),
        ProbeTrace(probe_id="d", dimension="uncertainty_signaling", classification="UNCLASSIFIED"),
    ]
    dist = failure_shape_distribution(traces)
    assert dist["contradiction_handling"] == {"PERCEIVE": 2, "EXPRESS": 1}
    assert dist["uncertainty_signaling"] == {"UNCLASSIFIED": 1}


def test_probe_trace_to_dict_is_json_safe():
    import json
    t = ProbeTrace(
        probe_id="a", dimension="contradiction_handling",
        turns=[{"user_text": "x", "response_text": "y"}],
        predicate_results={"acknowledges_contradiction": False},
        response_text="y", classification="PERCEIVE", classification_detail="d",
    )
    json.dumps(t.to_dict())  # must not raise

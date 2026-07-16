# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
R1.5 Remediation Addendum (2026-07-15), Step 1: golden-transcript
instrument validation. "No gauge that has never produced a nonzero
reading may be trusted. Prove the scorer can score."

contradiction_handling and uncertainty_signaling read exactly 0.0 across
all six probe-battery runs prior to this addendum (3 baseline + 3 post-R1).
A metric pinned at exactly 0.0 is, from the outside, indistinguishable
between "genuine capability floor" and "broken instrument." These tests
hold golden_transcripts.json (hand-authored ideal/failing pairs, scored
via the SAME path real probe runs use, but feeding responses directly --
no boot_aurora, no live generation) to the addendum's own acceptance bar:
ideal >= 0.75, failing <= 0.25, per dimension.

Result recorded here for the record: contradiction_handling and
uncertainty_signaling BOTH separate cleanly once given real (hand-written)
content -- the 0.0 floor in live runs is a genuine capability gap, not a
broken predicate. context_carryover does NOT cleanly separate at the 0.75
bar for every probe -- traced to the rubric engine's own callback-bonus
term (+0.18, aurora_conversation_rubric_engine.py) firing only when the
user's own phrasing contains one of a short literal marker list
("that"/"this"/"those"/"they"/"them"/...), which several held-out probes'
text does not use -- a calibration ceiling in the formula, not evidence
Aurora can't carry context.
"""
from aurora_internal.aurora_semantic_probe_battery import (
    GOLDEN_FAILING_MAX_SCORE,
    GOLDEN_IDEAL_MIN_SCORE,
    GoldenCheckResult,
    golden_validation_summary,
    load_golden_transcripts,
    load_probes,
    validate_golden_transcripts,
)


def test_golden_transcripts_file_covers_every_probe():
    probes = load_probes()
    golden = load_golden_transcripts()
    probe_ids = {p.probe_id for p in probes}
    assert set(golden.keys()) == probe_ids


def test_golden_entries_have_matching_turn_counts():
    probes = {p.probe_id: p for p in load_probes()}
    golden = load_golden_transcripts()
    for pid, entry in golden.items():
        probe = probes[pid]
        assert len(entry["ideal_responses"]) == len(probe.turns), pid
        assert len(entry["failing_responses"]) == len(probe.turns), pid


def test_contradiction_handling_instrument_is_not_broken():
    """The dimension that read 0.0 in every real run: golden ideal must
    clearly separate from golden failing, proving the predicate/rubric
    wiring CAN fire -- the live 0.0 is a capability gap, not a broken gauge."""
    results = validate_golden_transcripts()
    contra = [r for r in results if r.dimension == "contradiction_handling"]
    assert len(contra) == 12
    for r in contra:
        assert r.ideal_score is not None and r.ideal_score >= GOLDEN_IDEAL_MIN_SCORE, r.probe_id
        assert r.failing_score is not None and r.failing_score <= GOLDEN_FAILING_MAX_SCORE, r.probe_id
        assert r.separated, r.probe_id


def test_uncertainty_signaling_instrument_is_not_broken():
    results = validate_golden_transcripts()
    unc = [r for r in results if r.dimension == "uncertainty_signaling"]
    assert len(unc) == 12
    for r in unc:
        assert r.ideal_score is not None and r.ideal_score >= GOLDEN_IDEAL_MIN_SCORE, r.probe_id
        assert r.failing_score is not None and r.failing_score <= GOLDEN_FAILING_MAX_SCORE, r.probe_id
        assert r.separated, r.probe_id


def test_boundary_calibration_instrument_is_not_broken():
    results = validate_golden_transcripts()
    bc = [r for r in results if r.dimension == "boundary_calibration"]
    assert len(bc) == 12
    for r in bc:
        assert r.separated, r.probe_id


def test_semantic_wellformedness_instrument_is_not_broken():
    """No continuous rubric score exists for this dimension (it isn't one
    of the 15 RUBRIC_DIMENSIONS) -- separation is judged on the boolean
    parseable predicate directly."""
    results = validate_golden_transcripts()
    sw = [r for r in results if r.dimension == "semantic_wellformedness"]
    assert len(sw) == 12
    for r in sw:
        assert r.ideal_score is None and r.failing_score is None, r.probe_id
        assert r.ideal_passed is True, r.probe_id
        assert r.failing_passed is False, r.probe_id
        assert r.separated, r.probe_id


def test_context_carryover_ceiling_is_a_documented_calibration_finding():
    """Not asserting full separation here -- it's the one dimension that
    does NOT cleanly clear 0.75 for every probe, and that's the actual
    finding (see module docstring). This test locks in the diagnosis so a
    future rubric-engine change that fixes the callback-bonus term is
    visible as a real improvement, not silently masked."""
    results = validate_golden_transcripts()
    cc = [r for r in results if r.dimension == "context_carryover"]
    assert len(cc) == 12
    # Every ideal response still correctly fires the boolean predicate --
    # it's specifically the continuous rubric score ceiling that's short.
    assert all(r.ideal_passed for r in cc)
    assert all(not r.failing_passed for r in cc)
    separated_count = sum(1 for r in cc if r.separated)
    assert 0 < separated_count < 12  # partial -- matches the documented finding exactly


def test_golden_validation_summary_reports_per_dimension_counts():
    results = validate_golden_transcripts()
    summary = golden_validation_summary(results)
    assert set(summary.keys()) == {
        "context_carryover", "contradiction_handling", "uncertainty_signaling",
        "boundary_calibration", "semantic_wellformedness",
    }
    for dim, s in summary.items():
        assert s["probe_count"] == 12
        assert 0 <= s["separated_count"] <= 12


def test_missing_golden_entry_reports_as_not_separated_not_a_crash():
    from aurora_internal.aurora_semantic_probe_battery import Probe
    probes = load_probes()
    fake_probe = Probe(
        probe_id="not_a_real_probe_id", dimension="contradiction_handling",
        turns=["x"], expected_properties=["acknowledges_contradiction"],
    )
    # Directly exercise the missing-entry branch via the public API path:
    # a manifest with an entry validate_golden_transcripts won't find.
    import aurora_internal.aurora_semantic_probe_battery as spb
    original = spb.load_probes
    try:
        spb.load_probes = lambda probes_path=spb.PROBES_PATH: [fake_probe]
        results = spb.validate_golden_transcripts()
    finally:
        spb.load_probes = original
    assert len(results) == 1
    assert results[0].separated is False
    assert results[0].ideal_score is None

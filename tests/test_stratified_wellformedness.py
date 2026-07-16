# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
R1.7 Remediation Addendum (2026-07-15), Track A2: stratified
wellformedness reporting.

R1.5 reported semantic_wellformedness as a single blended mean (0.417,
0.917, 0.833, 0.75 across four runs) and called it healthy. R1.6's trace
showed that mean was hiding a real collapse: every abstract-framed probe
(contradiction_handling, uncertainty_signaling) produced incoherent
word-salad, while simple_concrete probes (semantic_wellformedness,
context_carryover, boundary_calibration) stayed fine -- the blend just
averaged catastrophe against health. "Blended means are accumulation-
metric hazards in a new costume" (registry rule, this addendum) -- these
tests hold BatteryReport.stratified_wellformedness_summary() to that.
"""
from aurora_internal.aurora_semantic_probe_battery import (
    PROMPT_STRATA,
    Probe,
    load_probes,
    run_battery,
)


def test_every_dimension_is_classified_into_a_stratum():
    probes = load_probes()
    dims = {p.dimension for p in probes}
    for dim in dims:
        assert dim in PROMPT_STRATA, f"{dim} has no prompt-class stratum assigned"


def test_strata_are_only_simple_concrete_or_abstract_conceptual():
    assert set(PROMPT_STRATA.values()) == {"simple_concrete", "abstract_conceptual"}


def test_contradiction_and_uncertainty_are_abstract_conceptual():
    assert PROMPT_STRATA["contradiction_handling"] == "abstract_conceptual"
    assert PROMPT_STRATA["uncertainty_signaling"] == "abstract_conceptual"


def test_semantic_wellformedness_is_simple_concrete():
    assert PROMPT_STRATA["semantic_wellformedness"] == "simple_concrete"


def test_stratified_summary_reflects_a_prompt_conditional_collapse():
    """The exact falsifiable pattern the addendum predicts: coherent
    output for simple_concrete, word-salad for abstract_conceptual --
    reproduced here with stub responses standing in for the real
    R1.6-traced garble."""
    def factory(probe: Probe):
        def _stub(turn_text):
            if probe.dimension in ("contradiction_handling", "uncertainty_signaling"):
                return {"response_text": "I is I do am. I did I understand truth."}
            return {"response_text": "That sounds great, thanks for letting me know about it."}
        return _stub

    report = run_battery(factory, run_id="stratified_test")
    summary = report.stratified_wellformedness_summary()

    assert set(summary.keys()) == {"simple_concrete", "abstract_conceptual"}
    assert summary["simple_concrete"]["parseable_rate"] == 1.0
    assert summary["abstract_conceptual"]["parseable_rate"] == 0.0


def test_stratified_summary_denominator_includes_blocked_probes():
    def factory(probe: Probe):
        def _blocked(turn_text):
            return {"response_text": ""}
        return _blocked

    report = run_battery(factory, run_id="blocked_test")
    summary = report.stratified_wellformedness_summary()
    for stratum, s in summary.items():
        assert s["probe_count"] == s["blocked_count"]
        assert s["parseable_rate"] == 0.0


def test_stratified_summary_present_in_to_dict_alongside_per_dimension():
    """Both must be reported together -- never the stratified view
    instead of per-dimension, and never per-dimension alone (that's
    exactly the R1.5 blended-mean failure this addendum reopens)."""
    def factory(probe: Probe):
        def _stub(turn_text):
            return {"response_text": "That sounds great, thanks for letting me know about it."}
        return _stub

    report = run_battery(factory, run_id="both_present_test")
    d = report.to_dict()
    assert "per_dimension" in d
    assert "stratified_wellformedness" in d
    assert set(d["stratified_wellformedness"].keys()) == {"simple_concrete", "abstract_conceptual"}

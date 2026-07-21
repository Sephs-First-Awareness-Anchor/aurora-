# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
R1.9.2 G4 gate 3, made permanent: BatteryReport.relevance_summary() and
run_battery()'s optional relevance_scorer plumbing.

"Add to the battery permanently" (F3 gate 3's own instruction) -- this was
computed post-hoc against stored transcripts during G4; these tests hold
the now-permanent instrument to the same bar.
"""
from aurora_internal.aurora_semantic_probe_battery import ProbeResult, BatteryReport, run_battery


def test_relevance_summary_is_none_when_no_scorer_supplied():
    def factory(probe):
        def _stub(turn_text):
            return {"response_text": "That sounds great, thanks for letting me know about it."}
        return _stub

    report = run_battery(factory, run_id="no_scorer_test")
    summary = report.relevance_summary()
    assert summary["scored_count"] == 0
    assert summary["mean_relevance_fraction"] is None


def test_relevance_summary_computes_mean_over_scored_probes():
    def factory(probe):
        def _stub(turn_text):
            return {"response_text": "That sounds great, thanks for letting me know about it."}
        return _stub

    def scorer(input_text, response_text):
        return 0.5

    report = run_battery(factory, run_id="scorer_test", relevance_scorer=scorer)
    summary = report.relevance_summary()
    assert summary["scored_count"] == 60
    assert summary["mean_relevance_fraction"] == 0.5
    assert summary["nonzero_count"] == 60
    assert summary["nonzero_rate"] == 1.0


def test_relevance_scorer_exception_yields_none_not_crash():
    def factory(probe):
        def _stub(turn_text):
            return {"response_text": "That sounds great, thanks for letting me know about it."}
        return _stub

    def bad_scorer(input_text, response_text):
        raise RuntimeError("boom")

    report = run_battery(factory, run_id="bad_scorer_test", relevance_scorer=bad_scorer)
    for r in report.probe_results:
        assert r.relevance_fraction is None
    summary = report.relevance_summary()
    assert summary["scored_count"] == 0


def test_relevance_present_in_to_dict_alongside_stratified_and_per_dimension():
    def factory(probe):
        def _stub(turn_text):
            return {"response_text": "That sounds great, thanks for letting me know about it."}
        return _stub

    report = run_battery(factory, run_id="to_dict_test", relevance_scorer=lambda i, r: 0.42)
    d = report.to_dict()
    assert "per_dimension" in d
    assert "stratified_wellformedness" in d
    assert "relevance" in d
    assert abs(d["relevance"]["mean_relevance_fraction"] - 0.42) < 1e-9


def test_probe_result_to_dict_includes_relevance_fraction_field():
    r = ProbeResult(probe_id="x", dimension="y", status="ok", relevance_fraction=0.7)
    assert r.to_dict()["relevance_fraction"] == 0.7

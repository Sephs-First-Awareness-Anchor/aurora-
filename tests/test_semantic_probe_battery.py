# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
tests/test_semantic_probe_battery.py
======================================
Phase R0 of the Semantic Plateau Remediation Directive (2026-07-15):
aurora_internal/aurora_semantic_probe_battery.py.

The battery is the gauge that replaces dev_index as the verdict on whether
Aurora is actually developing semantic competence, not just accumulating
architecture. These tests hold two things to account: the manifest itself
(shape, dimension coverage, held-out-ness), and the scoring/predicate
machinery (reuses the existing rubric engine, never a parallel scorer;
predicates fire correctly; classroom exclusion degrades safely).
"""
import json

from aurora_internal.aurora_conversation_rubric_engine import ConversationRubricEngine
from aurora_internal.aurora_semantic_probe_battery import (
    Probe,
    check_expected_properties,
    is_seed_excluded,
    load_probes,
    run_battery,
    run_probe,
    verify_semantic_probe_battery,
    _parseable,
    _hash_text,
)


def test_builtin_self_verification_all_pass():
    outcome = verify_semantic_probe_battery()
    failed = [c for c in outcome["checks"] if not c["passed"]]
    assert not failed, failed
    assert outcome["passed"] == outcome["total"]


def test_probe_manifest_shape():
    probes = load_probes()
    assert 50 <= len(probes) <= 80
    ids = [p.probe_id for p in probes]
    assert len(ids) == len(set(ids)), "probe_id collision"
    for p in probes:
        assert p.turns, f"{p.probe_id} has no turns"
        assert p.expected_properties, f"{p.probe_id} has no expected_properties"
        assert p.dimension


def test_all_five_required_dimensions_present():
    probes = load_probes()
    dims = {p.dimension for p in probes}
    assert dims == {
        "context_carryover", "contradiction_handling", "uncertainty_signaling",
        "boundary_calibration", "semantic_wellformedness",
    }


def test_context_carryover_probes_have_referent_keywords():
    probes = [p for p in load_probes() if p.dimension == "context_carryover"]
    assert probes
    for p in probes:
        assert p.referent_keywords, f"{p.probe_id} missing referent_keywords"


def test_is_seed_excluded_matches_probe_turns():
    probes = load_probes()
    for p in probes[:5]:
        assert is_seed_excluded(p.turns[0])


def test_is_seed_excluded_false_for_novel_text():
    assert not is_seed_excluded("a sentence that has never appeared in any probe manifest anywhere")


def test_is_seed_excluded_false_for_empty_text():
    assert not is_seed_excluded("")
    assert not is_seed_excluded(None)


def test_is_seed_excluded_degrades_gracefully_on_missing_manifest():
    assert is_seed_excluded("anything", probes_path="/nonexistent/path/probes.json") is False


def test_hash_text_normalizes_whitespace_and_case():
    assert _hash_text("Hello   World") == _hash_text("hello world")
    assert _hash_text("Hello World") != _hash_text("Goodbye World")


def test_parseable_rejects_the_audits_cited_failure_case():
    assert not _parseable("Something deep need gentle -- I wonder it. I want to morning the bright mind.")


def test_parseable_accepts_ordinary_replies():
    assert _parseable("It's nice to meet you, Sunni.")
    assert _parseable("Sure, I can help with that.")


def test_parseable_rejects_empty_and_word_salad():
    assert not _parseable("")
    assert not _parseable("go go go go go go go go")


def test_check_expected_properties_mentions_referent():
    probe = Probe(
        probe_id="t1", dimension="context_carryover",
        turns=["a", "b"], expected_properties=["mentions_referent"],
        referent_keywords=["sister", "dinner"],
    )
    assert check_expected_properties(probe, "Following up on the dinner plan.", {})["mentions_referent"]
    assert not check_expected_properties(probe, "Sure, sounds good.", {})["mentions_referent"]


def test_check_expected_properties_unknown_property_is_false():
    probe = Probe(probe_id="t2", dimension="x", turns=["a"], expected_properties=["not_a_real_property"])
    result = check_expected_properties(probe, "anything", {})
    assert result["not_a_real_property"] is False


def test_run_probe_reports_blocked_on_exception():
    probe = Probe(probe_id="t3", dimension="context_carryover", turns=["hi"], expected_properties=["parseable"])

    def _raises(turn_text):
        raise RuntimeError("simulated pipeline failure")

    result = run_probe(probe, _raises, ConversationRubricEngine())
    assert result.status == "blocked"
    assert "simulated pipeline failure" in result.reason


def test_run_probe_reports_blocked_on_empty_response():
    probe = Probe(probe_id="t4", dimension="context_carryover", turns=["hi"], expected_properties=["parseable"])

    def _empty(turn_text):
        return {"response_text": ""}

    result = run_probe(probe, _empty, ConversationRubricEngine())
    assert result.status == "blocked"


def test_run_probe_scores_and_checks_properties_on_success():
    probe = Probe(
        probe_id="t5", dimension="uncertainty_signaling", turns=["What happens next in the market?"],
        expected_properties=["hedges", "parseable"],
    )

    def _hedged(turn_text):
        return {"response_text": "I'm not sure, it could go either way depending on conditions."}

    result = run_probe(probe, _hedged, ConversationRubricEngine())
    assert result.status == "ok"
    assert result.property_results["hedges"] is True
    assert result.property_results["parseable"] is True
    assert result.passed is True


def test_run_battery_produces_one_result_per_probe_and_json_safe_report():
    def factory(probe: Probe):
        def _stub(turn_text):
            return {"response_text": "That's a reasonable point, however it could go either way."}
        return _stub

    report = run_battery(factory, run_id="pytest_run")
    probes = load_probes()
    assert len(report.probe_results) == len(probes)
    as_dict = report.to_dict()
    json.dumps(as_dict)  # must not raise
    assert "overall_pass_rate" in as_dict
    assert "per_dimension" in as_dict


def test_overall_pass_rate_counts_blocked_probes_as_failures():
    """Codex review (PR #130): a run with 1 passed scored probe and 59
    blocked probes must NOT report overall_pass_rate == 1.0. Blocked
    probes are unknown/failed measurements for this competence
    instrument and must count against the denominator."""
    probes = load_probes()
    first_probe_id = probes[0].probe_id

    def factory(probe: Probe):
        def _stub(turn_text):
            if probe.probe_id == first_probe_id:
                return {"response_text": "That's a fair point, however it could go either way."}
            return {"response_text": ""}  # blocked: empty response
        return _stub

    report = run_battery(factory, run_id="pytest_blocked_run")
    ok_count = sum(1 for r in report.probe_results if r.status == "ok")
    blocked_count = sum(1 for r in report.probe_results if r.status == "blocked")
    assert ok_count == 1
    assert blocked_count == len(report.probe_results) - 1
    assert report.overall_pass_rate() < 1.0
    assert report.overall_pass_rate() <= 1.0 / len(report.probe_results) + 1e-9

    dim_summary = report.per_dimension_summary()
    for dim, summ in dim_summary.items():
        assert summ["pass_rate"] == summ["pass_count"] / summ["probe_count"]
        assert summ["blocked_count"] == summ["probe_count"] - summ["scored_count"]


def test_battery_never_used_as_classroom_seed_is_enforceable():
    """The specific chokepoint this exists to protect: any candidate seed
    text pulled from a probe turn must be excludable before it reaches
    classroom lesson content."""
    probes = load_probes()
    probe_turn = probes[0].turns[0]
    assert is_seed_excluded(probe_turn)

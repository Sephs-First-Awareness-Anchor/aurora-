"""
tests/test_mtsl_acceptance_report.py
=======================================
MTSL Phase 8 (2026-07-13): mtsl_acceptance_report.py -- read-only
summarization of aurora_state/mtsl_shadow_comparison.jsonl, the
evidence ledger the directive says MTSL "earns authority from... or
stays an observer." Also serves as an integration test across the
full MTSL stack: Phase 3's coordinator, Phase 4's CERS extension, and
Phase 5's intention bridge all writing to the SAME shared log.
"""
import json
import time

from aurora_dimensional_systems import CrystalProcessingSystem, EvolutionTracker
from aurora_internal.dual_strata.cers_regulator import cers_converge, PotentialTracker, TopologyContext
from aurora_internal.dual_strata.crest import Crest
from aurora_internal.dual_strata.mtsl_acceptance_report import (
    AcceptanceSummary,
    acceptance_summary,
    read_shadow_comparison_log,
    summarize,
)
from aurora_internal.dual_strata.semantic_intention_bridge import SemanticIntentionBridge
from aurora_internal.dual_strata.topological_semantic_coordinator import TopologicalSemanticCoordinator

_AXES_CYCLE = [
    {"X": 0.5, "T": 0.5, "N": 0.7, "B": 0.5, "A": 0.3},
    {"X": 0.5, "T": 0.5, "N": 0.3, "B": 0.5, "A": 0.7},
    {"X": 0.5, "T": 0.5, "N": 0.5, "B": 0.7, "A": 0.3},
]
_CRESTS = (Crest(label="steady", intensity=0.6, axis="N"),)


def _run_full_stack(state_dir, n=30, authority_stage=1):
    dps = CrystalProcessingSystem(tracker=EvolutionTracker())
    coord = TopologicalSemanticCoordinator(state_dir=state_dir)
    bridge = SemanticIntentionBridge(state_dir=state_dir)
    tracker = PotentialTracker()
    for i in range(n):
        snap = coord.observe_turn(
            turn_id=f"turn-{i}", timestamp=time.time(), adjusted_axes=_AXES_CYCLE[i % 3],
            sub_crests=_CRESTS, context_family="conversation", dps=dps,
        )
        ctx = TopologyContext(
            schema_version=1, turn_id=snap.turn_id, manifold_slot_id=snap.manifold_slot_id,
            variant_confidence=(snap.variant_confidence or 0.0), variant_status=snap.semantic_variant_status,
            variant_created=snap.variant_created,
            semantic_ambiguity=(snap.understanding_classification == "ambiguous_organization"),
            circulation_fraction=snap.topology_signatures.get("meso", {}).get("circulation_fraction", 0.0),
            regime=snap.topology_signatures.get("meso", {}).get("regime", "quiescent"),
        )
        _crest, verdict = cers_converge(_CRESTS, tracker, topology_context=ctx, authority_stage=authority_stage)
        bridge.consume(verdict, turn_id=snap.turn_id, authority_stage=authority_stage)
    return coord, bridge


# ---- read_shadow_comparison_log: graceful degradation ----

def test_missing_log_file_returns_empty_list(tmp_path):
    assert read_shadow_comparison_log(str(tmp_path)) == []


def test_unparseable_lines_are_skipped_not_fatal(tmp_path):
    log_path = tmp_path / "mtsl_shadow_comparison.jsonl"
    log_path.write_text('{"turn_id": "t1"}\nnot json at all\n{"turn_id": "t2"}\n')
    entries = read_shadow_comparison_log(str(tmp_path))
    assert len(entries) == 2
    assert entries[0]["turn_id"] == "t1"
    assert entries[1]["turn_id"] == "t2"


def test_non_dict_json_lines_are_skipped(tmp_path):
    log_path = tmp_path / "mtsl_shadow_comparison.jsonl"
    log_path.write_text('[1, 2, 3]\n{"turn_id": "t1"}\n')
    entries = read_shadow_comparison_log(str(tmp_path))
    assert len(entries) == 1
    assert entries[0]["turn_id"] == "t1"


# ---- summarize(): entry-shape disambiguation and counting ----

def test_empty_entries_summarize_to_zeros():
    summary = summarize([])
    assert summary.total_entries == 0
    assert summary.coordinator_observations == 0
    assert summary.strategy_shifts == 0
    assert summary.semantic_ambiguity_rate == 0.0
    assert summary.variant_created_rate == 0.0


def test_coordinator_and_shift_entries_are_distinguished():
    entries = [
        {"turn_id": "t1", "semantic_ambiguity": False, "dominant_semantic_variant": None},
        {"turn_id": "t2", "semantic_ambiguity": True, "dominant_semantic_variant": "sv1"},
        {"strategy_shift": {"strategy": "clarify", "applied": False}},
    ]
    summary = summarize(entries)
    assert summary.total_entries == 3
    assert summary.coordinator_observations == 2
    assert summary.strategy_shifts == 1


def test_semantic_ambiguity_rate_computed_correctly():
    entries = [
        {"turn_id": "t1", "semantic_ambiguity": True},
        {"turn_id": "t2", "semantic_ambiguity": False},
        {"turn_id": "t3", "semantic_ambiguity": False},
        {"turn_id": "t4", "semantic_ambiguity": False},
    ]
    summary = summarize(entries)
    assert summary.semantic_ambiguity_count == 1
    assert summary.semantic_ambiguity_rate == 0.25


def test_variant_created_rate_computed_correctly():
    entries = [
        {"turn_id": "t1", "dominant_semantic_variant": "sv1"},
        {"turn_id": "t2", "dominant_semantic_variant": None},
    ]
    summary = summarize(entries)
    assert summary.variant_created_count == 1
    assert summary.variant_created_rate == 0.5


def test_strategy_shift_distribution_counts_each_strategy():
    entries = [
        {"strategy_shift": {"strategy": "clarify", "applied": False}},
        {"strategy_shift": {"strategy": "clarify", "applied": False}},
        {"strategy_shift": {"strategy": "explain", "applied": True}},
    ]
    summary = summarize(entries)
    assert summary.strategy_shift_distribution == {"clarify": 2, "explain": 1}
    assert summary.applied_strategy_shift_count == 1


def test_to_dict_shape():
    summary = summarize([])
    d = summary.to_dict()
    assert set(d.keys()) == {
        "total_entries", "coordinator_observations", "strategy_shifts",
        "semantic_ambiguity_count", "semantic_ambiguity_rate",
        "variant_created_count", "variant_created_rate",
        "strategy_shift_distribution", "applied_strategy_shift_count",
    }


# ---- full-stack integration: Phase 3 + Phase 4 + Phase 5 write, Phase 8 reads ----

def test_acceptance_summary_reads_the_real_shared_log(tmp_path):
    state_dir = str(tmp_path)
    _run_full_stack(state_dir, n=30)
    summary = acceptance_summary(state_dir)
    assert summary.total_entries > 0
    assert summary.coordinator_observations == 30


def test_stage_1_never_produces_an_applied_strategy_shift(tmp_path):
    # This is the acceptance-discipline check: at the default authority
    # stage, nothing MTSL computes should ever have been APPLIED to real
    # behavior, no matter how many turns ran.
    state_dir = str(tmp_path)
    _run_full_stack(state_dir, n=30, authority_stage=1)
    summary = acceptance_summary(state_dir)
    assert summary.applied_strategy_shift_count == 0


def test_stage_2_does_produce_applied_strategy_shifts(tmp_path):
    # Sanity check that the summary would actually detect it if authority
    # WERE advanced -- confirms the stage-1 test above is a real signal,
    # not a tautology of the summarizer always reporting zero.
    state_dir = str(tmp_path)
    _run_full_stack(state_dir, n=30, authority_stage=2)
    summary = acceptance_summary(state_dir)
    assert summary.strategy_shifts > 0
    assert summary.applied_strategy_shift_count == summary.strategy_shifts


def test_convenience_wrapper_matches_manual_two_step(tmp_path):
    state_dir = str(tmp_path)
    _run_full_stack(state_dir, n=10)
    manual = summarize(read_shadow_comparison_log(state_dir))
    wrapped = acceptance_summary(state_dir)
    assert manual == wrapped


def test_reader_never_writes_anything(tmp_path):
    state_dir = str(tmp_path)
    _run_full_stack(state_dir, n=10)
    log_path = tmp_path / "mtsl_shadow_comparison.jsonl"
    before = log_path.read_text()
    acceptance_summary(state_dir)
    acceptance_summary(state_dir)
    after = log_path.read_text()
    assert before == after

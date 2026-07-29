# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Communication Credit Unification, zip integration phase E (2026-07-29):
foundational additive methods ported from Sunni's uploaded
operational-hardening zip across 9 files. None of these are wired into
a live call path yet (that's phase G) -- these tests confirm each
piece works correctly in isolation, against the same behavioral
assertions the zip's own test_communication_credit_unification.py
uses for these pieces.

Also includes one independent bug fix found and ported along the way:
aurora_interaction_engine.py's _derive_intended_effect() referenced an
undefined `event` name unconditionally (guaranteed NameError on every
call) -- a real, pre-existing bug unrelated to this port, but blocking
enough to any use of InteractionProcessing that it had to be fixed
before this phase's own methods could be exercised at all.
"""
import os
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)


def test_understanding_contract_returns_and_clears_validated_response():
    from aurora_internal.aurora_understanding_contract import RuntimeUnderstandingContract
    with tempfile.TemporaryDirectory() as state_dir:
        contract = RuntimeUnderstandingContract(state_dir=state_dir)
        contract.state["pending_validation"] = {
            "response_id": "response-1",
            "expected_observation": "confirmation",
            "contributors": {"interaction_base_id": "base-1"},
        }
        result = contract.ingest_observation({}, "Exactly", turn_tick=1)
        assert result["validated_response"]["response_id"] == "response-1"
        assert contract.state["pending_validation"] == {}
        from pathlib import Path
        assert Path(contract.storage_path).exists()


def test_expression_confusion_is_not_positive_clarification():
    from aurora_internal.aurora_understanding_contract import RuntimeUnderstandingContract
    with tempfile.TemporaryDirectory() as state_dir:
        contract = RuntimeUnderstandingContract(state_dir=state_dir)
        contract.state["pending_validation"] = {"response_id": "r", "expected_observation": "clarification"}
        result = contract.ingest_observation({}, "I don't understand", turn_tick=1)
        assert result["accuracy"]["label"] == "expression_unclear"


def test_ordinary_negation_is_not_mistaken_for_clarification():
    """The old crude 'not ' substring marker matched "not sure" and even
    "not clear" -- this fix uses a word-boundary phrase matcher and a
    separate, higher-priority expression_confusion classification."""
    from aurora_internal.aurora_understanding_contract import RuntimeUnderstandingContract
    with tempfile.TemporaryDirectory() as state_dir:
        contract = RuntimeUnderstandingContract(state_dir=state_dir)
        contract.state["pending_validation"] = {"response_id": "r", "expected_observation": "clarification"}
        result = contract.ingest_observation({}, "I am not sure", turn_tick=1)
        assert result["accuracy"]["label"] == "continued_without_validation"


def test_word_containing_yes_is_not_confirmation():
    from aurora_internal.aurora_understanding_contract import RuntimeUnderstandingContract
    with tempfile.TemporaryDirectory() as state_dir:
        contract = RuntimeUnderstandingContract(state_dir=state_dir)
        contract.state["pending_validation"] = {"response_id": "r", "expected_observation": "confirmation"}
        result = contract.ingest_observation({}, "Yesterday was difficult", turn_tick=1)
        assert result["accuracy"]["label"] != "confirmed"


def test_unvalidated_continuation_is_deferred_not_closed():
    from aurora_internal.aurora_understanding_contract import RuntimeUnderstandingContract
    with tempfile.TemporaryDirectory() as state_dir:
        contract = RuntimeUnderstandingContract(state_dir=state_dir)
        contract.state["pending_validation"] = {"response_id": "response-deferred", "expected_observation": "confirmation"}
        result = contract.ingest_observation({}, "What comes next?", turn_tick=1)
        assert result["accuracy"]["label"] == "engaged_followup"
        assert result["validated_response"] == {}
        assert contract.state["deferred_validations"][0]["response_id"] == "response-deferred"


def test_failed_language_path_is_not_reselected_as_direct_route():
    from aurora_language_field import LSAEntry, LanguageField, ProtoLanguage

    class _IdentityField:
        def ingest_external_input(self, *a, **k):
            return None

    language = LanguageField(_IdentityField())
    language._lsa.clear()
    proto = ProtoLanguage(
        dominant_axes=["A", "B"], comparison_type="assertion", tension_level=0.6,
        b_boundary_load=0.6, reflection_active=True, drive_strength=0.8,
        self_directed=False, raw_axes={"A": 1.0, "B": 1.0},
    )
    path_key = language._path_key(proto.comparison_type, proto.dominant_axes)
    language._lsa[path_key] = LSAEntry(
        path_key=path_key, comparison_type="assertion", last_fidelity=0.9,
        context_fingerprint=proto.raw_axes, validated_failure_count=2, receiver_outcome_mean=0.1,
    )
    selected = language.select_crossing_path(proto)
    assert selected["is_novel"] or selected["is_metaphor"]
    assert not (selected.get("is_novel") is False and selected.get("path_key") == path_key)


def test_language_receiver_ledger_is_separate_from_internal_fidelity():
    from aurora_language_field import LSAEntry, LanguageField

    class _IdentityField:
        def ingest_external_input(self, *a, **k):
            return None

    language = LanguageField(_IdentityField())
    language._lsa["path-1"] = LSAEntry(path_key="path-1")
    assert language.apply_receiver_outcome("path-1", 1.0, "resolved_fully", 0.9) is True
    entry = language._lsa["path-1"]
    assert entry.validated_success_count == 1
    assert entry.use_count == 0
    assert language.apply_receiver_outcome("path-1", 0.5, "continued_without_validation", 0.5) is False


def test_interaction_engine_derive_intended_effect_no_longer_raises():
    """The independent bug: _derive_intended_effect referenced an
    undefined `event` unconditionally. Confirms the real fix (a tone=
    keyword parameter, threaded through by the one real call site)
    works standalone."""
    from aurora_interaction_engine import InteractionEngine
    engine = InteractionEngine()
    result = engine._derive_intended_effect("some_signature", "some_issue", "route_to_self_introspection", tone="curious")
    assert result == "inquisitive_answer_self_query_without_external_search"


def test_pending_interaction_is_finalized_after_evidence_and_rehydrates():
    from aurora_interaction_processing import InteractionProcessing
    from aurora_interaction_memory import InteractionMemory

    with tempfile.TemporaryDirectory() as state_dir:
        processing = InteractionProcessing(memory=InteractionMemory(storage_dir=state_dir))
        event = {
            "text": "why is this unclear?", "input_signature": "self_reflective_question",
            "interpretive_issue": "self_query_routing", "processing_tier": "reasoning_engine",
            "response_action": "route_to_self_introspection",
            "intended_effect": "answer_self_query_without_external_search",
            "observed_effect": "pending_verification",
        }
        observed = processing.observe_interaction(event, auto_promote=False)
        base_id = observed["base"].crystal_id
        assert observed["advance"] is None
        assert observed["base"].get_facet("observed_effect") == "pending_verification"

        finalized = processing.finalize_base_interaction(base_id, "resolved_fully", {"response_id": "response-1"})
        assert finalized["ok"] is True
        assert finalized["resolution_fidelity"] == 1.0

        restored = InteractionProcessing(memory=InteractionMemory(storage_dir=state_dir))
        assert base_id in restored._bases


def test_negative_interaction_base_cannot_join_promotion_family():
    from aurora_interaction_processing import InteractionProcessing
    from aurora_interaction_memory import InteractionMemory

    with tempfile.TemporaryDirectory() as state_dir:
        processing = InteractionProcessing(memory=InteractionMemory(storage_dir=state_dir))
        event = {
            "text": "that is unclear", "input_signature": "self_reflective_question",
            "interpretive_issue": "self_query_routing", "processing_tier": "reasoning_engine",
            "response_action": "route_to_self_introspection",
            "intended_effect": "answer_self_query_without_external_search",
            "observed_effect": "pending_verification",
        }
        observed = processing.observe_interaction(event, auto_promote=False)
        base_id = observed["base"].crystal_id
        processing.finalize_base_interaction(base_id, "resolved_partially__followup_gap_appeared", auto_promote=False)
        assert processing._base_family("self_query_routing") == []


def test_topological_coordinator_variant_outcome_split_from_turn_outcome():
    from aurora_internal.dual_strata.topological_semantic_coordinator import TopologicalSemanticCoordinator
    coordinator = TopologicalSemanticCoordinator()
    # No snapshot yet -> record_turn_outcome's delegation path returns None
    # without raising, confirming the split didn't break the old entry point.
    assert coordinator.record_turn_outcome(positive=True, dps=object()) is None
    assert coordinator.record_variant_outcome(
        manifold_slot_id="", topology_id="", positive=True, dps=object()
    ) is None


def test_variant_transition_predictor_delayed_outcome():
    from aurora_internal.dual_strata.variant_transition_predictor import VariantTransitionPredictor
    predictor = VariantTransitionPredictor()
    predictor.observe("variant-a")
    predictor.observe("variant-b")
    assert predictor._last_transition_key == ("variant-a", "variant-b")
    assert predictor.record_turn_outcome(positive=True) is True
    assert predictor._last_transition_key is None
    rec = predictor._transitions[("variant-a", "variant-b")]
    assert rec.outcome_positive == 1


def test_grammar_exemplar_is_neutral_and_outcome_is_addressed():
    from aurora_grammar_engine import GrammarEngine, TokenRole
    with tempfile.TemporaryDirectory() as state_dir:
        grammar = GrammarEngine(state_dir=state_dir)
        role_sequence = (TokenRole.AGENT, TokenRole.ACTION)
        grammar._lineage.record_success(role_sequence, "seed", 2, {"A": 1.0})
        motif = grammar._lineage._motifs["agent_action"]
        before = motif.success_count
        grammar.observe_exemplar("I understand this", "neutral")
        assert motif.success_count == before
        assert grammar.record_motif_outcome("agent_action", "positive") is True
        assert motif.success_count == before + 1


def test_fallback_response_gets_delayed_grammar_address():
    from aurora_grammar_engine import GrammarEngine
    with tempfile.TemporaryDirectory() as state_dir:
        grammar = GrammarEngine(state_dir=state_dir)
        trace = grammar.prepare_response_trace("I understand the world.", context_text="learning")
        assert trace["motif_id"]
        motif = grammar._lineage._motifs[trace["motif_id"]]
        assert motif.success_count == 0
        assert grammar.record_motif_outcome(trace["motif_id"], "positive") is True
        assert motif.success_count == 1


def test_representation_ledger_aggregates_receiver_outcomes():
    from aurora_expression_perception import ExpressionPerceptionEngine
    with tempfile.TemporaryDirectory() as state_dir:
        engine = ExpressionPerceptionEngine(state_dir=state_dir)
        assert engine.active_representation_id() == "authored_seed"
        result = engine.record_communication_outcome(
            "authored_seed", outcome_kind="negative", meaning_failure=True,
            internal_fidelity=0.8, grammaticality=0.8, context_key="test",
        )
        assert result["sample_count"] == 1
        assert result["meaning_failures"] == 1
        diagnostics = engine.representation_diagnostics()
        assert diagnostics["communication_record"]["sample_count"] == 1


def test_pipeline_learning_stage_and_resolve_positive():
    from aurora_dream_trainer import DreamTrainer
    with tempfile.TemporaryDirectory() as state_dir:
        trainer = DreamTrainer(state_dir=state_dir)
        ok = trainer.stage_pipeline_learning(
            "this is a real learned fact about the world",
            response_id="resp-1", source="working_memory", turn_tick=5,
        )
        assert ok is True
        assert trainer.pending_pipeline_learning_count == 1
        result = trainer.resolve_pipeline_learning("resp-1", outcome_kind="positive", turn_tick=6)
        assert result["promoted"] == 1
        assert trainer.pending_pipeline_learning_count == 0


def test_pipeline_learning_expires_abandoned_candidates():
    from aurora_dream_trainer import DreamTrainer
    with tempfile.TemporaryDirectory() as state_dir:
        trainer = DreamTrainer(state_dir=state_dir)
        trainer.stage_pipeline_learning(
            "some candidate text here", response_id="resp-2",
            source="working_memory", turn_tick=1,
        )
        expired = trainer.expire_staged_pipeline_learning(current_turn=10, max_age_turns=3)
        assert expired == 1
        assert trainer.pending_pipeline_learning_count == 0

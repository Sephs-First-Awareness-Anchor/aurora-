#!/usr/bin/env python3
"""Regression tests for delayed communication-credit routing."""

import tempfile
import unittest
from pathlib import Path

from aurora import (
    _chain_up5_understanding,
    _classify_validated_communication,
    _finalize_validated_communication,
)
from aurora_grammar_engine import GrammarEngine, TokenRole
from aurora_interaction_memory import InteractionMemory
from aurora_interaction_processing import InteractionProcessing
from aurora_internal.aurora_understanding_contract import RuntimeUnderstandingContract
from aurora_language_field import LSAEntry, LanguageField, ProtoLanguage


class _IdentityField:
    def ingest_external_input(self, *args, **kwargs):
        return None


class _Recorder:
    def __init__(self):
        self.calls = []

    def record_motif_outcome(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return True

    def record_variant_outcome(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return object()

    def apply_receiver_outcome(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return True

    def record_receiver_outcome(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return True

    def save(self, *args, **kwargs):
        return None

    def record_communication_outcome(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return {"sample_count": 1}


class _ContractCounter:
    def __init__(self):
        self.calls = 0

    def ingest_observation(self, *args, **kwargs):
        self.calls += 1
        return {"accuracy": {"label": "unvalidated"}}


class CommunicationCreditUnificationTests(unittest.TestCase):
    def test_contract_returns_and_clears_validated_response(self):
        with tempfile.TemporaryDirectory() as state_dir:
            contract = RuntimeUnderstandingContract(state_dir=state_dir)
            contract.state["pending_validation"] = {
                "response_id": "response-1",
                "expected_observation": "confirmation",
                "contributors": {"interaction_base_id": "base-1"},
            }
            result = contract.ingest_observation({}, "Exactly", turn_tick=1)
            self.assertEqual(result["validated_response"]["response_id"], "response-1")
            self.assertEqual(contract.state["pending_validation"], {})
            self.assertTrue(Path(contract.storage_path).exists())

    def test_live_pipeline_reuses_canonical_contract_observation(self):
        contract = _ContractCounter()
        state = type(
            "State",
            (),
            {
                "parsed": {},
                "meaning_forms": [],
                "learned_hints": [],
                "understanding_observation": {},
            },
        )()
        systems = {
            "understanding_contract": contract,
            "_live_contract_observation_done": True,
            "_last_understanding_observation": {"accuracy": {"label": "confirmed"}},
        }
        _chain_up5_understanding("hello", systems, state, turn_tick=1)
        self.assertEqual(contract.calls, 0)
        self.assertEqual(state.understanding_observation["accuracy"]["label"], "confirmed")

    def test_pending_interaction_is_finalized_after_evidence_and_rehydrates(self):
        with tempfile.TemporaryDirectory() as state_dir:
            processing = InteractionProcessing(
                memory=InteractionMemory(storage_dir=state_dir)
            )
            event = {
                "text": "why is this unclear?",
                "input_signature": "self_reflective_question",
                "interpretive_issue": "self_query_routing",
                "processing_tier": "reasoning_engine",
                "response_action": "route_to_self_introspection",
                "intended_effect": "answer_self_query_without_external_search",
                "observed_effect": "pending_verification",
            }
            observed = processing.observe_interaction(event, auto_promote=False)
            base_id = observed["base"].crystal_id
            self.assertIsNone(observed["advance"])
            self.assertEqual(
                observed["base"].get_facet("observed_effect"),
                "pending_verification",
            )

            finalized = processing.finalize_base_interaction(
                base_id, "resolved_fully", {"response_id": "response-1"}
            )
            self.assertTrue(finalized["ok"])
            self.assertEqual(finalized["resolution_fidelity"], 1.0)

            restored = InteractionProcessing(
                memory=InteractionMemory(storage_dir=state_dir)
            )
            self.assertIn(base_id, restored._bases)

    def test_grammar_exemplar_is_neutral_and_outcome_is_addressed(self):
        with tempfile.TemporaryDirectory() as state_dir:
            grammar = GrammarEngine(state_dir=state_dir)
            role_sequence = (TokenRole.AGENT, TokenRole.ACTION)
            grammar._lineage.record_success(role_sequence, "seed", 2, {"A": 1.0})
            motif = grammar._lineage._motifs["agent_action"]
            before = motif.success_count
            grammar.observe_exemplar("I understand this", "neutral")
            self.assertEqual(motif.success_count, before)
            self.assertTrue(grammar.record_motif_outcome("agent_action", "positive"))
            self.assertEqual(motif.success_count, before + 1)

    def test_fallback_response_gets_delayed_grammar_address(self):
        with tempfile.TemporaryDirectory() as state_dir:
            grammar = GrammarEngine(state_dir=state_dir)
            trace = grammar.prepare_response_trace(
                "I understand the world.",
                context_text="learning",
            )
            self.assertTrue(trace["motif_id"])
            motif = grammar._lineage._motifs[trace["motif_id"]]
            self.assertEqual(motif.success_count, 0)
            self.assertTrue(grammar.record_motif_outcome(trace["motif_id"], "positive"))
            self.assertEqual(motif.success_count, 1)

    def test_expression_confusion_is_not_positive_clarification(self):
        with tempfile.TemporaryDirectory() as state_dir:
            contract = RuntimeUnderstandingContract(state_dir=state_dir)
            contract.state["pending_validation"] = {
                "response_id": "response-unclear",
                "expected_observation": "clarification",
            }
            result = contract.ingest_observation({}, "I don't understand", turn_tick=1)
            self.assertEqual(result["accuracy"]["label"], "expression_unclear")
            outcome = _classify_validated_communication({}, result, "I don't understand")
            self.assertEqual(outcome["outcome_kind"], "negative")
            self.assertTrue(outcome["expression_issue"])

    def test_ordinary_negation_is_not_mistaken_for_clarification(self):
        with tempfile.TemporaryDirectory() as state_dir:
            contract = RuntimeUnderstandingContract(state_dir=state_dir)
            contract.state["pending_validation"] = {
                "response_id": "response-not-sure",
                "expected_observation": "clarification",
            }
            result = contract.ingest_observation({}, "I am not sure", turn_tick=1)
            self.assertNotEqual(result["accuracy"]["label"], "clarification_supplied")
            self.assertEqual(result["accuracy"]["label"], "continued_without_validation")

    def test_word_containing_yes_is_not_confirmation(self):
        with tempfile.TemporaryDirectory() as state_dir:
            contract = RuntimeUnderstandingContract(state_dir=state_dir)
            contract.state["pending_validation"] = {
                "response_id": "response-yesterday",
                "expected_observation": "confirmation",
            }
            result = contract.ingest_observation({}, "Yesterday was difficult", turn_tick=1)
            self.assertNotEqual(result["accuracy"]["label"], "confirmed")

    def test_unvalidated_continuation_is_deferred_not_closed(self):
        with tempfile.TemporaryDirectory() as state_dir:
            contract = RuntimeUnderstandingContract(state_dir=state_dir)
            contract.state["pending_validation"] = {
                "response_id": "response-deferred",
                "expected_observation": "confirmation",
            }
            result = contract.ingest_observation({}, "What comes next?", turn_tick=1)
            self.assertEqual(result["accuracy"]["label"], "engaged_followup")
            self.assertEqual(result["validated_response"], {})
            self.assertEqual(
                contract.state["deferred_validations"][0]["response_id"],
                "response-deferred",
            )

    def test_failed_language_path_is_not_reselected_as_direct_route(self):
        language = LanguageField(_IdentityField())
        language._lsa.clear()
        proto = ProtoLanguage(
            dominant_axes=["A", "B"],
            comparison_type="assertion",
            tension_level=0.6,
            b_boundary_load=0.6,
            reflection_active=True,
            drive_strength=0.8,
            self_directed=False,
            raw_axes={"A": 1.0, "B": 1.0},
        )
        path_key = language._path_key(proto.comparison_type, proto.dominant_axes)
        language._lsa[path_key] = LSAEntry(
            path_key=path_key,
            comparison_type="assertion",
            last_fidelity=0.9,
            context_fingerprint=proto.raw_axes,
            validated_failure_count=2,
            receiver_outcome_mean=0.1,
        )
        selected = language.select_crossing_path(proto)
        self.assertTrue(selected["is_novel"] or selected["is_metaphor"])
        self.assertFalse(selected.get("is_novel") is False and selected.get("path_key") == path_key)

    def test_negative_interaction_base_cannot_join_promotion_family(self):
        with tempfile.TemporaryDirectory() as state_dir:
            processing = InteractionProcessing(
                memory=InteractionMemory(storage_dir=state_dir)
            )
            event = {
                "text": "that is unclear",
                "input_signature": "self_reflective_question",
                "interpretive_issue": "self_query_routing",
                "processing_tier": "reasoning_engine",
                "response_action": "route_to_self_introspection",
                "intended_effect": "answer_self_query_without_external_search",
                "observed_effect": "pending_verification",
            }
            observed = processing.observe_interaction(event, auto_promote=False)
            base_id = observed["base"].crystal_id
            processing.finalize_base_interaction(
                base_id,
                "resolved_partially__followup_gap_appeared",
                auto_promote=False,
            )
            self.assertEqual(processing._base_family("self_query_routing"), [])

    def test_language_receiver_ledger_is_separate_from_internal_fidelity(self):
        language = LanguageField(_IdentityField())
        language._lsa["path-1"] = LSAEntry(path_key="path-1")
        self.assertTrue(language.apply_receiver_outcome("path-1", 1.0, "resolved_fully", 0.9))
        entry = language._lsa["path-1"]
        self.assertEqual(entry.validated_success_count, 1)
        self.assertEqual(entry.use_count, 0)
        self.assertFalse(language.apply_receiver_outcome("path-1", 0.5, "continued_without_validation", 0.5))

    def test_finalizer_routes_exact_interaction_id(self):
        with tempfile.TemporaryDirectory() as state_dir:
            processing = InteractionProcessing(
                memory=InteractionMemory(storage_dir=state_dir)
            )
            observed = processing.observe_interaction(
                {
                    "text": "what is the answer?",
                    "input_signature": "self_reflective_question",
                    "interpretive_issue": "self_query_routing",
                    "processing_tier": "reasoning_engine",
                    "response_action": "route_to_self_introspection",
                    "intended_effect": "answer_self_query_without_external_search",
                    "observed_effect": "pending_verification",
                }
            )
            base_id = observed["base"].crystal_id
            finalized = _finalize_validated_communication(
                {"interaction_processing": processing, "state_dir": state_dir},
                {
                    "accuracy": {"label": "confirmed", "score": 0.92},
                    "validated_response": {
                        "response_id": "response-1",
                        "contributors": {"interaction_base_id": base_id},
                    },
                },
                "Exactly",
                session_id="session-1",
                turn_tick=2,
            )
            self.assertEqual(finalized["observed_effect"], "resolved_fully")
            self.assertEqual(
                processing._bases[base_id].get_facet("observed_effect"),
                "resolved_fully",
            )

    def test_negative_credit_is_diagnosis_scoped(self):
        grammar = _Recorder()
        coordinator = _Recorder()
        language = _Recorder()
        concept = _Recorder()
        perception = _Recorder()
        systems = {
            "grammar_engine": grammar,
            "language_field": language,
            "perception": perception,
            "_concept_crystal_registry": concept,
            "dimensional": type("Dimensional", (), {
                "_mtsl_coordinator": coordinator,
                "dps": object(),
            })(),
        }
        semantic = {
            "semantic_variant_id": "slot:topology",
            "manifold_slot_id": "slot",
            "topology_id": "topology",
        }
        contributors = {
            "grammar_motif": {"motif_id": "agent_action"},
            "semantic_variant": semantic,
            "language_field": {"path_key": "path-1"},
            "concept_crystal": {
                "crystal_id": "crystal-1",
                "lsa_facet_role": "lsa:path-1",
            },
            "representation": {"component_id": "repr-1"},
        }
        finalized = _finalize_validated_communication(
            systems,
            {
                "accuracy": {"label": "corrected", "score": 0.92},
                "validated_response": {"response_id": "response-2", "contributors": contributors},
            },
            "That meaning is not right.",
        )
        self.assertEqual(finalized["observed_effect"], "regression_introduced")
        self.assertEqual(len(grammar.calls), 0)
        self.assertEqual(len(language.calls), 0)
        self.assertEqual(len(coordinator.calls), 1)
        self.assertEqual(len(concept.calls), 1)
        self.assertTrue(perception.calls[0][1]["meaning_failure"])


if __name__ == "__main__":
    unittest.main()

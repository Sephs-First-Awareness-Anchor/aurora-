# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Communication Credit Unification, zip integration phase F (2026-07-29):
the aurora.py core functions -- _build_communication_contributors,
_classify_validated_communication, _finalize_validated_communication,
_record_learning_delta, _turn_has_no_known_anchor -- ported as new
top-level functions. None of these are called from
_run_live_response_turn yet (that's phase G); these tests exercise
each function directly, matching the zip's own acceptance assertions
for the two most consequential ones (_finalize_validated_communication).

Also ports aurora_internal/aurora_learning_pipeline.py, a small new
self-contained module (_record_learning_delta's dependency for
LearningDeltaLedger/build_learning_delta) plus the quality-gate
primitives phase H's corpus-ingestion bridge will need later.
"""
import os
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import aurora as A  # noqa: E402


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


def test_finalizer_routes_exact_interaction_id():
    from aurora_interaction_processing import InteractionProcessing
    from aurora_interaction_memory import InteractionMemory

    with tempfile.TemporaryDirectory() as state_dir:
        processing = InteractionProcessing(memory=InteractionMemory(storage_dir=state_dir))
        observed = processing.observe_interaction({
            "text": "what is the answer?", "input_signature": "self_reflective_question",
            "interpretive_issue": "self_query_routing", "processing_tier": "reasoning_engine",
            "response_action": "route_to_self_introspection",
            "intended_effect": "answer_self_query_without_external_search",
            "observed_effect": "pending_verification",
        })
        base_id = observed["base"].crystal_id
        finalized = A._finalize_validated_communication(
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
        assert finalized["observed_effect"] == "resolved_fully"
        assert processing._bases[base_id].get_facet("observed_effect") == "resolved_fully"


def test_negative_credit_is_diagnosis_scoped():
    """Negative (meaning-issue) outcomes route to coordinator + concept
    crystal (meaning-repair signals) but NOT grammar or language field
    (those are addressed only on positive or expression-issue outcomes,
    not on a pure meaning correction)."""
    grammar = _Recorder()
    coordinator = _Recorder()
    language = _Recorder()
    concept = _Recorder()
    perception = _Recorder()
    with tempfile.TemporaryDirectory() as state_dir:
        systems = {
            "grammar_engine": grammar,
            "language_field": language,
            "perception": perception,
            "_concept_crystal_registry": concept,
            "dimensional": type("Dimensional", (), {
                "_mtsl_coordinator": coordinator,
                "dps": object(),
            })(),
            "state_dir": state_dir,
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
            "concept_crystal": {"crystal_id": "crystal-1", "lsa_facet_role": "lsa:path-1"},
            "representation": {"component_id": "repr-1"},
        }
        finalized = A._finalize_validated_communication(
            systems,
            {
                "accuracy": {"label": "corrected", "score": 0.92},
                "validated_response": {"response_id": "response-2", "contributors": contributors},
            },
            "That meaning is not right.",
        )
        assert finalized["observed_effect"] == "regression_introduced"
        assert len(grammar.calls) == 0
        assert len(language.calls) == 0
        assert len(coordinator.calls) == 1
        assert len(concept.calls) == 1
        assert perception.calls[0][1]["meaning_failure"] is True


def test_classify_validated_communication_positive_confirmation():
    outcome = A._classify_validated_communication(
        {}, {"accuracy": {"label": "confirmed", "score": 0.9}}, "Exactly"
    )
    assert outcome["observed_effect"] == "resolved_fully"
    assert outcome["outcome_kind"] == "positive"
    assert outcome["meaning_issue"] is False
    assert outcome["expression_issue"] is False


def test_classify_validated_communication_expression_issue():
    outcome = A._classify_validated_communication(
        {}, {"accuracy": {"label": "unvalidated", "score": 0.0}}, "I don't understand what you mean"
    )
    assert outcome["outcome_kind"] == "negative"
    assert outcome["expression_issue"] is True


def test_build_communication_contributors_picks_up_populated_keys():
    systems = {
        "_last_pipeline_state": {"response_source": "search", "grammar_constraint_fit": 0.7},
        "_last_interaction_route": {"input_signature": "sig", "interpretive_issue": "issue", "primary_response_strategy": "strat"},
        "_last_interaction_status": {"interaction_base_id": "base-9"},
        "_last_grammar_trace": {"motif_id": "agent_action", "role_sequence": ["AGENT", "ACTION"], "constraint_fit": 0.6},
        "_last_lf_reentry": {"path_key": "path-9"},
        "_last_lf_fidelity": 0.8,
        "_last_concept_crystal_trace": {"crystal_id": "crystal-9"},
        "_last_gap_result": {"gap_type": "unknown_word", "action": "ask"},
    }
    contributors = A._build_communication_contributors(systems)
    assert contributors["interaction_base_id"] == "base-9"
    assert contributors["grammar_motif"]["motif_id"] == "agent_action"
    assert contributors["language_field"]["path_key"] == "path-9"
    assert contributors["concept_crystal"]["crystal_id"] == "crystal-9"
    assert contributors["interaction_route"]["input_signature"] == "sig"
    assert contributors["comprehension"]["gap_type"] == "unknown_word"
    assert contributors["expression"]["response_source"] == "search"


def test_turn_has_no_known_anchor_detects_unanchored_question():
    class _State:
        parsed = {"utterance_type": "question"}

    systems = {"_pre_turn_known_anchors": {"water", "exist", "truth"}}
    assert A._turn_has_no_known_anchor("what is xyzzyflorp?", systems, _State()) is True
    assert A._turn_has_no_known_anchor("what is water?", systems, _State()) is False
    assert A._turn_has_no_known_anchor("xyzzyflorp is weird", systems, _State()) is False


def test_record_learning_delta_persists_response_reaction_pair():
    from aurora_internal.aurora_learning_pipeline import LearningDeltaLedger

    class _FakeResponse:
        content = "the improved answer text"

    with tempfile.TemporaryDirectory() as state_dir:
        systems = {
            "state_dir": state_dir,
            "_last_learning_response": "the original answer text",
            "_last_learning_reaction": "that is confusing",
            "_last_learning_response_id": "resp-1",
        }
        record = A._record_learning_delta(
            systems,
            current_response=_FakeResponse(),
            current_reaction="thanks that makes sense",
            validated_outcome={
                "response_id": "resp-1", "outcome_kind": "positive",
                "observed_effect": "resolved_fully", "score": 0.9,
            },
            turn_tick=3,
        )
        assert record["response_id"] == "resp-1"
        assert record["outcome_kind"] == "positive"
        assert systems["_last_learning_response"] == "the improved answer text"
        assert systems["_last_learning_reaction"] == "thanks that makes sense"
        ledger = systems["_learning_delta_ledger"]
        assert isinstance(ledger, LearningDeltaLedger)
        assert len(ledger.records) == 1


def test_learning_pipeline_quality_gate_rejects_thin_stagnant_text():
    from aurora_internal.aurora_learning_pipeline import assess_text_quality
    thin = assess_text_quality("ok")
    assert thin["eligible_for_learning"] is False
    assert thin["reason"] == "thin"

    usable = assess_text_quality("water freezes at zero degrees celsius")
    assert usable["eligible_for_learning"] is True

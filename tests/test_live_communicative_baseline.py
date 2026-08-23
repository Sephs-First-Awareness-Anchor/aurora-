from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import aurora
from aurora_internal.aurora_communication_emergence import (
    AuroraCommunicationEmergence,
)
from aurora_internal.aurora_constraint_semantic_continuity import (
    derive_constraint_grounded_candidate,
    derive_constraint_semantic_state,
    extract_relational_form,
)
from aurora_internal.aurora_understanding_contract import (
    _structured_receiver_correction,
)
from aurora_warp_protocol import WarpField


AXES = {axis: 0.20 for axis in ("X", "T", "N", "B", "A")}


def _semantic(text: str):
    return derive_constraint_semantic_state(
        extract_relational_form(text),
        axis_activation=AXES,
    )


def _field(state_dir: Path) -> AuroraCommunicationEmergence:
    field = AuroraCommunicationEmergence(
        state_dir=str(state_dir),
        persist=False,
    )
    warp = WarpField()
    warp.register_warp_capable("communication_emergence", field)
    field.attach_systems({"warp_field": warp})
    return field


def _seed_failures(field: AuroraCommunicationEmergence, prompts):
    for index, text in enumerate(prompts):
        field.observe_turn(
            semantic_state=_semantic(text),
            raw_text=text,
            response_text="I do not have a clear sense of that.",
            response_source="constraint_abstain",
            response_confidence=0.40,
            response_id=f"seed:{index}",
        )


def _seed_causal_trial(field: AuroraCommunicationEmergence):
    _seed_failures(
        field,
        (
            "What makes an invention elegant?",
            "What makes a tool elegant?",
            "What makes a solution elegant?",
        ),
    )


def _seed_directive_trial(field: AuroraCommunicationEmergence):
    _seed_failures(
        field,
        (
            "Tell me the first item.",
            "Tell me the second item.",
            "Tell me the final item.",
        ),
    )


class LiveCommunicativeBaselineTests(unittest.TestCase):
    def test_causal_form_preserves_glass_fall_and_after_clause(self):
        form = extract_relational_form(
            "Why did the glass fall after I bumped the table?"
        )
        self.assertEqual(form["subject"], "glass")
        self.assertEqual(form["relation"].lower(), "fall")
        self.assertEqual(form["obj"], "after I bumped the table")
        self.assertEqual(form["complement"], "")
        self.assertEqual(form["unknown_role"], "cause")

    def test_imperative_form_preserves_directed_fulfillment(self):
        form = extract_relational_form("Tell me the capital of France.")
        self.assertTrue(form["directive"])
        self.assertFalse(form["question"])
        self.assertEqual(form["subject"], "you")
        self.assertEqual(form["relation"].lower(), "tell")
        self.assertIn("capital of France", form["obj"])
        self.assertEqual(form["unknown_role"], "fulfillment")

    def test_subordinate_participle_is_not_misread_as_a_command(self):
        form = extract_relational_form(
            "I value preserving meaning while staying honest about limits. "
            "What do you think?"
        )
        self.assertTrue(form["question"])
        self.assertEqual(len(form["clauses"]), 1)
        self.assertFalse(form["clauses"][0]["directive"])

    def test_opinion_candidate_preserves_both_parts_of_the_claim(self):
        text = (
            "I think communication means preserving the relation someone is "
            "expressing while staying honest about what you do not know. "
            "What do you think?"
        )
        candidate = derive_constraint_grounded_candidate(_semantic(text))
        self.assertIn("preserving the relation", candidate["text"].lower())
        self.assertIn("staying honest", candidate["text"].lower())
        self.assertGreaterEqual(candidate["relation_alignment"]["score"], 0.58)
        self.assertFalse(
            candidate["relation_alignment"]["leaked_unknown_token"]
        )

    def test_live_genealogy_answers_its_own_architecture_question(self):
        text = "What does constraint genealogy mean in your own architecture?"
        candidate = derive_constraint_grounded_candidate(
            _semantic(text),
            prior_claim={
                "summary": "communication means preserving another relation"
            },
        )
        self.assertEqual(candidate["basis"], "live_genealogy_trace_definition")
        self.assertIn("ancestry trace", candidate["text"].lower())
        self.assertIn("root constraints", candidate["text"].lower())
        self.assertIn("earned operation", candidate["text"].lower())
        self.assertNotIn(
            "communication means preserving", candidate["text"].lower()
        )
        self.assertEqual(candidate["relation_alignment"]["score"], 1.0)

    def test_receiver_contract_recognizes_relational_correction(self):
        understood = {
            "relational_form": extract_relational_form(
                "That answer missed my question. Please try again more directly."
            )
        }
        self.assertTrue(_structured_receiver_correction(understood))

    def test_warp_birth_retains_lexical_free_applicability_shape(self):
        with tempfile.TemporaryDirectory() as td:
            field = _field(Path(td))
            _seed_causal_trial(field)
            operations = field.active_operations()
            self.assertEqual(len(operations), 1)
            operation = operations[0]
            self.assertEqual(operation["status"], "trial")
            self.assertTrue(operation["applicability_shape"]["question"])
            self.assertTrue(operation["applicability_shape"]["has_relation"])
            self.assertNotIn("invention", str(operation["applicability_shape"]))

    def test_nearest_operation_yields_honest_causal_boundary(self):
        with tempfile.TemporaryDirectory() as td:
            field = _field(Path(td))
            _seed_causal_trial(field)
            text = "Why did the glass fall after I bumped the table?"
            prepared = field.prepare_semantic_state(
                _semantic(text), raw_text=text, axis_activation=AXES
            )
            operation = prepared["emergent_operation"]
            candidate = derive_constraint_grounded_candidate(prepared)
            self.assertEqual(operation["match_kind"], "structural_nearest")
            self.assertTrue(operation["component_id"])
            self.assertTrue(candidate["communicative_baseline"])
            self.assertEqual(
                candidate["source"], "constraint_communication_baseline"
            )
            self.assertIn("cause of glass falling", candidate["text"].lower())
            self.assertIn("bumped the table", candidate["text"].lower())
            self.assertIn("do not yet have enough grounded", candidate["text"].lower())
            self.assertEqual(candidate["relation_alignment"]["score"], 1.0)

    def test_directive_boundary_is_observed_through_its_trial_component(self):
        with tempfile.TemporaryDirectory() as td:
            field = _field(Path(td))
            _seed_directive_trial(field)
            text = "Tell me the capital of France."
            prepared = field.prepare_semantic_state(
                _semantic(text), raw_text=text, axis_activation=AXES
            )
            candidate = derive_constraint_grounded_candidate(prepared)
            component_id = prepared["emergent_operation"]["component_id"]
            self.assertTrue(candidate["communicative_baseline"])
            self.assertIn("tell you the capital of France", candidate["text"])
            self.assertNotIn("Paris", candidate["text"])
            result = field.observe_turn(
                semantic_state=prepared,
                raw_text=text,
                response_text=candidate["text"],
                response_source=candidate["source"],
                response_confidence=candidate["confidence"],
                response_id="live:directive",
            )
            self.assertEqual(result["trial_component_id"], component_id)
            self.assertEqual(field.status()["promoted_operations"], 0)

    def test_receiver_correction_yields_non_inverting_repair(self):
        with tempfile.TemporaryDirectory() as td:
            field = _field(Path(td))
            _seed_directive_trial(field)
            text = (
                "That answer missed my question. "
                "Please try again more directly."
            )
            prepared = field.prepare_semantic_state(
                _semantic(text), raw_text=text, axis_activation=AXES
            )
            candidate = derive_constraint_grounded_candidate(
                prepared,
                receiver_observation={"accuracy": {"label": "corrected"}},
            )
            self.assertTrue(candidate["receiver_repair"])
            self.assertIn("my previous response", candidate["text"].lower())
            self.assertIn("did not preserve your meaning", candidate["text"].lower())
            self.assertIn("try again more directly", candidate["text"].lower())
            self.assertNotIn("you missed my question", candidate["text"].lower())

    def test_final_authority_replaces_recycled_hint_with_baseline(self):
        with tempfile.TemporaryDirectory() as td:
            field = _field(Path(td))
            _seed_causal_trial(field)
            text = "Why did the glass fall after I bumped the table?"
            prepared = field.prepare_semantic_state(
                _semantic(text), raw_text=text, axis_activation=AXES
            )
            baseline = derive_constraint_grounded_candidate(prepared)
            state = SimpleNamespace(
                response_content="A previously learned hint about attention.",
                response_confidence=0.52,
                response_src="learned_hint",
                response_tone="attentive",
                pipeline_state={"constraint_grounded_candidate": baseline},
                relational_form=prepared["relational_form"],
                parsed={},
            )
            response = SimpleNamespace(
                content=state.response_content,
                emotional_tone="attentive",
                confidence=state.response_confidence,
                src="learned_hint",
            )

            original_abstain = aurora._emit_honest_abstain_and_seek

            def _fake_abstain(user_text, systems, target_state, trigger=""):
                target_state.response_content = "I do not know."
                target_state.response_tone = "honest"
                target_state.response_confidence = 0.30
                target_state.response_src = "constraint_abstain"

            aurora._emit_honest_abstain_and_seek = _fake_abstain
            try:
                systems = {"perception": None, "state_dir": td}
                aurora._finalize_articulation(
                    response, None, state, systems, text
                )
            finally:
                aurora._emit_honest_abstain_and_seek = original_abstain

            self.assertEqual(response.content, baseline["text"])
            self.assertEqual(
                response.src, "constraint_communication_baseline"
            )
            self.assertEqual(state.response_content, baseline["text"])
            self.assertEqual(response.confidence, baseline["confidence"])
            self.assertIn(
                "constraint_communication_baseline_floor",
                state.pipeline_state["articulation_arbitration"][
                    "rejection_reasons"
                ],
            )


if __name__ == "__main__":
    unittest.main()

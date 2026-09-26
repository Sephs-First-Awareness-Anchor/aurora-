from __future__ import annotations

import unittest

import aurora
from aurora_internal.aurora_constraint_semantic_continuity import (
    bind_conscious_action,
    bind_external_interaction_event,
    derive_constraint_grounded_candidate,
    derive_constraint_semantic_state,
    extract_relational_form,
)


AXES = {axis: 0.20 for axis in ("X", "T", "N", "B", "A")}


class InteractionEventActionHandoffTests(unittest.TestCase):
    def test_relationless_external_turn_becomes_interaction_event_not_broken_proposition(self):
        parsed = extract_relational_form("hey Aurora", feed_lexical_grounding=False)
        self.assertFalse(parsed["relation"])

        bound = bind_external_interaction_event(
            parsed,
            raw_text="hey Aurora",
            receiver="Aurora",
        )
        self.assertTrue(bound["interaction_event"])
        self.assertEqual(bound["subject"], "external speaker")
        self.assertEqual(bound["relation"], "interact")
        self.assertEqual(bound["obj"], "Aurora")
        self.assertEqual(bound["interaction_payload"], "hey Aurora")

        semantic = derive_constraint_semantic_state(bound, axis_activation=AXES)
        self.assertNotIn("relation", semantic["unresolved"])
        self.assertNotIn("unknown_role", semantic["unresolved"])
        self.assertTrue(semantic["response_obligation"]["requires_response"])
        self.assertEqual(
            semantic["response_obligation"]["operation"],
            "participate_in_interaction",
        )

    def test_binding_is_general_to_relationless_external_payloads(self):
        parsed = extract_relational_form("photosynthesis", feed_lexical_grounding=False)
        bound = bind_external_interaction_event(
            parsed,
            raw_text="photosynthesis",
            receiver="Aurora",
        )
        self.assertTrue(bound["interaction_event"])
        self.assertEqual(bound["interaction_payload"], "photosynthesis")

    def test_existing_proposition_is_not_rewritten_as_interaction_event(self):
        parsed = extract_relational_form(
            "What are you thinking about?",
            feed_lexical_grounding=False,
        )
        bound = bind_external_interaction_event(
            parsed,
            raw_text="What are you thinking about?",
            receiver="Aurora",
        )
        self.assertEqual(bound, parsed)
        self.assertFalse(bound.get("interaction_event", False))

    def test_selected_conscious_action_becomes_response_obligation_and_candidate(self):
        parsed = extract_relational_form("hey Aurora", feed_lexical_grounding=False)
        bound = bind_external_interaction_event(
            parsed,
            raw_text="hey Aurora",
            receiver="Aurora",
        )
        semantic = derive_constraint_semantic_state(bound, axis_activation=AXES)
        semantic = bind_conscious_action(
            semantic,
            {
                "selected_action": "attend",
                "stance": "attend",
                "should_speak": True,
                "processing_mode": "blended",
            },
        )

        self.assertEqual(
            semantic["response_obligation"]["selected_action"],
            "attend",
        )
        self.assertEqual(
            semantic["relational_form"]["selected_action"],
            "attend",
        )

        candidate = derive_constraint_grounded_candidate(semantic)
        self.assertEqual(
            candidate["basis"],
            "conscious_action_bound_to_interaction_event",
        )
        self.assertIn("attend", candidate["text"].lower())
        self.assertNotIn("understand what you", candidate["text"].lower())
        self.assertGreaterEqual(candidate["relation_alignment"]["score"], 0.58)

    def test_empty_grounded_candidate_is_not_called_meaning_preservation(self):
        preserved, reasons = aurora._composer_preserves_meaning(
            "",
            "I am here.",
            "hey Aurora",
            {},
        )
        self.assertFalse(preserved)
        self.assertIn(
            "no_grounded_candidate_semantic_preservation_unknown",
            reasons,
        )


if __name__ == "__main__":
    unittest.main()

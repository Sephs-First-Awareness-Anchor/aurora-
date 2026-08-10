# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA DREAM SUBSTRATE... DIRECTIVE, Sections 9-10, 48: historical
recurrence must become available only when genuinely established by
Aurora's own native mechanisms (exact-match on identifiers her own
contract/ledger already produce -- no fabricated similarity score or
hardcoded recurrence count), and recurring material must supply novelty
to Dream synthesis rather than compel literal replay.
"""
import os
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)


class TestRecurrenceRequiresGenuineMatch:
    def test_two_genuinely_recurring_fails_link_by_dimension(self):
        import aurora_dream_trainer as dt
        with tempfile.TemporaryDirectory() as tmp:
            ledger = dt.FailPointLedger(tmp)
            ledger.record_fail("context_carryover", severity=0.4)
            ledger.record_fail("context_carryover", severity=0.6)
            events = ledger.rich_stream.ordered()
            assert events[1].recurrence_of == events[0].seq

    def test_two_genuinely_recurring_live_corrections_link_by_topic_and_action(self):
        import aurora_dream_trainer as dt
        with tempfile.TemporaryDirectory() as tmp:
            ledger = dt.FailPointLedger(tmp)
            ledger.record_pre_outcome_event(
                outcome_label="corrected", severity=0.5, pre_outcome_pressure=None,
                identity={"topic": "boundaries", "action_type": "grounded_answer"},
            )
            ledger.record_pre_outcome_event(
                outcome_label="corrected", severity=0.5, pre_outcome_pressure=None,
                identity={"topic": "boundaries", "action_type": "grounded_answer"},
            )
            events = ledger.rich_stream.ordered()
            assert events[1].recurrence_of == events[0].seq

    def test_unrelated_fails_do_not_falsely_link(self):
        import aurora_dream_trainer as dt
        with tempfile.TemporaryDirectory() as tmp:
            ledger = dt.FailPointLedger(tmp)
            ledger.record_fail("context_carryover", severity=0.4)
            ledger.record_fail("contradiction_handling", severity=0.6)
            events = ledger.rich_stream.ordered()
            assert events[1].recurrence_of is None

    def test_same_topic_different_action_type_does_not_falsely_link(self):
        """Recurrence must be a genuine match on BOTH topic and action,
        not merely a coincidental substring/topic overlap."""
        import aurora_dream_trainer as dt
        with tempfile.TemporaryDirectory() as tmp:
            ledger = dt.FailPointLedger(tmp)
            ledger.record_pre_outcome_event(
                outcome_label="corrected", severity=0.5, pre_outcome_pressure=None,
                identity={"topic": "boundaries", "action_type": "grounded_answer"},
            )
            ledger.record_pre_outcome_event(
                outcome_label="expression_unclear", severity=0.5, pre_outcome_pressure=None,
                identity={"topic": "boundaries", "action_type": "clarification_request"},
            )
            events = ledger.rich_stream.ordered()
            assert events[1].recurrence_of is None

    def test_no_hardcoded_recurrence_count_threshold(self):
        """Recurrence must be recognized on the SECOND occurrence, not
        gated behind an arbitrary minimum count -- Section 9 explicitly
        forbids inventing a hardcoded recurrence count."""
        import aurora_dream_trainer as dt
        with tempfile.TemporaryDirectory() as tmp:
            ledger = dt.FailPointLedger(tmp)
            ledger.record_fail("context_carryover", severity=0.4)
            ledger.record_fail("context_carryover", severity=0.4)
            # Recurrence already established at the second occurrence.
            assert ledger.rich_stream.ordered()[1].recurrence_of is not None


class TestHistoricalRecurrenceIsNovelNotReplay:
    def test_dream_substrate_recurrence_carries_no_literal_waking_text(self):
        """DreamSubstrate.historical_recurrence must expose only the
        abstracted FailStreamEvent shape (dimension/topic/action/pressure/
        recurrence link) -- never literal user_turns/assistant_turns text,
        which would compel Dream toward reconstructing the same event."""
        import aurora_dream_trainer as dt
        from aurora_dream_substrate import gather_dream_substrate

        with tempfile.TemporaryDirectory() as tmp:
            ledger = dt.FailPointLedger(tmp)
            ledger.record_pre_outcome_event(
                outcome_label="corrected", severity=0.5,
                pre_outcome_pressure={"X": 0.1, "T": 0.2, "N": 0.3, "B": 0.4, "A": 0.5},
                identity={"topic": "boundaries", "action_type": "grounded_answer"},
            )
            ledger.record_pre_outcome_event(
                outcome_label="corrected", severity=0.6,
                pre_outcome_pressure={"X": 0.15, "T": 0.25, "N": 0.35, "B": 0.45, "A": 0.55},
                identity={"topic": "boundaries", "action_type": "grounded_answer"},
            )
            from types import SimpleNamespace
            systems = {"dimensional": None, "dream_trainer": SimpleNamespace(ledger=ledger)}
            substrate = gather_dream_substrate(systems)

            assert len(substrate.historical_recurrence) == 1
            recurring_event = substrate.historical_recurrence[0]
            allowed_keys = {
                "seq", "timestamp", "source", "dimension", "severity",
                "outcome_label", "pre_outcome_pressure", "identity", "recurrence_of",
            }
            assert set(recurring_event.keys()) <= allowed_keys
            # identity is itself abstracted (topic/action_type/response_id),
            # never a literal conversation transcript.
            identity_keys = set((recurring_event.get("identity") or {}).keys())
            assert identity_keys <= {"topic", "action_type", "response_id", "expected_topic"}

# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA DREAM SUBSTRATE... DIRECTIVE, Sections 6-8, 40, 47: failures form a
rich, temporally-ordered stream -- individually distinguishable, order
preserved, never flattened into one aggregate object and never treated as
fully isolated from each other -- kept BESIDE FailPointLedger's existing
aggregate scoring, which must remain completely unchanged in behavior.
"""
import os
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)


class TestRichStreamPreservesIndividualIdentity:
    def test_multiple_fails_each_remain_individually_distinguishable(self):
        import aurora_dream_trainer as dt
        with tempfile.TemporaryDirectory() as tmp:
            ledger = dt.FailPointLedger(tmp)
            ledger.record_fail("context_carryover", severity=0.3, example={"conversation_id": "c1", "user_turns": ["first"]})
            ledger.record_fail("contradiction_handling", severity=0.6, example={"conversation_id": "c2", "user_turns": ["second"]})
            ledger.record_fail("context_carryover", severity=0.9, example={"conversation_id": "c3", "user_turns": ["third"]})

            events = ledger.rich_stream.ordered()
            assert len(events) == 3
            seqs = [e.seq for e in events]
            assert seqs == sorted(seqs)  # order preserved, not flattened
            severities = [e.severity for e in events]
            assert severities == [0.3, 0.6, 0.9]  # not collapsed into one aggregate value

    def test_events_are_not_scattered_as_fully_isolated_objects(self):
        """Two fails on the same dimension must be linkable as recurrence,
        not treated as though they have no relationship at all."""
        import aurora_dream_trainer as dt
        with tempfile.TemporaryDirectory() as tmp:
            ledger = dt.FailPointLedger(tmp)
            ledger.record_fail("context_carryover", severity=0.3)
            ledger.record_fail("context_carryover", severity=0.4)
            events = ledger.rich_stream.ordered()
            assert events[1].recurrence_of == events[0].seq


class TestAggregateBehaviorUnchanged:
    def test_get_top_fails_and_scoring_behave_exactly_as_before(self):
        import aurora_dream_trainer as dt
        with tempfile.TemporaryDirectory() as tmp:
            ledger = dt.FailPointLedger(tmp)
            ledger.record_fail("context_carryover", severity=0.5)
            ledger.record_fail("context_carryover", severity=0.5)
            ledger.record_fail("contradiction_handling", severity=0.9)

            top = ledger.get_top_fails(5)
            dims = [d for d, _ in top]
            assert "context_carryover" in dims
            assert "contradiction_handling" in dims
            rec = ledger._records["context_carryover"]
            assert rec.fail_count == 2
            assert abs(rec.avg_severity - 0.5) < 1e-9

    def test_record_returns_none_exactly_as_before(self):
        """record_fail's own public contract (returns None) must be
        unaffected by the rich-stream addition."""
        import aurora_dream_trainer as dt
        with tempfile.TemporaryDirectory() as tmp:
            ledger = dt.FailPointLedger(tmp)
            result = ledger.record_fail("context_carryover", severity=0.4)
            assert result is None


class TestPersistence:
    def test_rich_stream_survives_save_and_load(self):
        import aurora_dream_trainer as dt
        with tempfile.TemporaryDirectory() as tmp:
            ledger = dt.FailPointLedger(tmp)
            ledger.record_fail("context_carryover", severity=0.3)
            ledger.record_pre_outcome_event(
                outcome_label="corrected", severity=0.7,
                pre_outcome_pressure={"X": 0.1, "T": 0.2, "N": 0.3, "B": 0.4, "A": 0.5},
                identity={"topic": "boundaries", "action_type": "grounded_answer"},
            )
            assert ledger.save() is True

            ledger2 = dt.FailPointLedger(tmp)
            assert ledger2.load() is True
            events = ledger2.rich_stream.ordered()
            assert len(events) == 2
            assert events[0].dimension == "context_carryover"
            assert events[1].source == "live_correction"
            assert events[1].pre_outcome_pressure == {"X": 0.1, "T": 0.2, "N": 0.3, "B": 0.4, "A": 0.5}

    def test_load_failure_of_rich_stream_does_not_break_ledger_load(self):
        """A corrupt fail_stream.jsonl must not prevent the aggregate
        fail_points.json from loading -- the two files are independent."""
        import aurora_dream_trainer as dt
        with tempfile.TemporaryDirectory() as tmp:
            ledger = dt.FailPointLedger(tmp)
            ledger.record_fail("context_carryover", severity=0.5)
            ledger.save()

            stream_path = os.path.join(tmp, dt._FAIL_STREAM_FILE)
            with open(stream_path, "w", encoding="utf-8") as f:
                f.write("{not valid json\n")

            ledger2 = dt.FailPointLedger(tmp)
            assert ledger2.load() is True
            assert ledger2._records["context_carryover"].fail_count == 1


class TestBoundedRetention:
    def test_stream_is_bounded_not_unbounded(self):
        import aurora_dream_trainer as dt
        with tempfile.TemporaryDirectory() as tmp:
            stream = dt.RichFailStream(tmp, maxlen=5)
            for i in range(10):
                stream.append(source="test", severity=0.1, outcome_label=f"e{i}")
            events = stream.ordered()
            assert len(events) == 5
            # Most recent events retained, order preserved.
            assert [e.outcome_label for e in events] == [f"e{i}" for i in range(5, 10)]

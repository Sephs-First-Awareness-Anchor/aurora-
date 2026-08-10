# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA DREAM SUBSTRATE... DIRECTIVE, Sections 42-43: FailPoint's own
stream stays rich (pre-outcome pressure, sequence, recurrence, minimal
identity), while Dream's input substrate is deliberately MORE abstracted
-- literal waking scene/response text/exact action sequence need not
survive into it. Audit/debug provenance (which subsystem produced a
fragment) is allowed to exist for developers; it must not become a
hidden answer key exposed to the experiencing Dream agent.
"""
import os
import sys
from types import SimpleNamespace

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)


class TestFailPointStreamRetainsRichContext:
    def test_fail_stream_event_retains_pre_outcome_pressure_and_sequence(self):
        import aurora_dream_trainer as dt
        ledger = dt.FailPointLedger.__new__(dt.FailPointLedger)
        ledger.__init__(state_dir="/tmp")
        ledger.record_pre_outcome_event(
            outcome_label="corrected", severity=0.6,
            pre_outcome_pressure={"X": 0.1, "T": 0.2, "N": 0.3, "B": 0.4, "A": 0.5},
            identity={"topic": "boundaries", "action_type": "grounded_answer", "response_id": "r1"},
        )
        event = ledger.rich_stream.ordered()[0]
        assert event.pre_outcome_pressure is not None
        assert event.identity.get("response_id") == "r1"
        assert event.seq == 0


class TestDreamSubstrateIsMoreAbstractedThanFailPointStream:
    def test_dream_substrate_fragment_never_carries_a_topic_sentence(self):
        """Crystal-facet-derived fragments carry only a concept label and a
        short native content tag -- never literal waking text, unlike the
        FailPointLedger's own examples (which DO retain short excerpts for
        curriculum purposes, a different, non-Dream-facing store)."""
        from aurora_dimensional_systems import CrystalProcessingSystem, EvolutionTracker
        from aurora_dream_substrate import gather_salient_fragments

        dps = CrystalProcessingSystem(EvolutionTracker())
        dps._get_or_create("protecting_boundaries")
        dps.note_relief_event(["protecting_boundaries"], dominant_axis="X", tick=1)

        fragments = gather_salient_fragments({"dimensional": SimpleNamespace(dps=dps)})
        for f in fragments:
            d = f.to_dict()
            assert "user_turns" not in d
            assert "assistant_turns" not in d
            assert len(d["content_tag"]) <= 60


class TestAuditProvenanceDoesNotBecomeAHiddenAnswerKey:
    def test_dream_substrate_dict_carries_no_lesson_or_expected_correct_fields(self):
        """A field like 'expected_correction' or 'lesson' would function as
        an answer key if consumed by a Dream generator. The substrate's own
        shape must not contain such fields anywhere."""
        import aurora_dream_trainer as dt
        from aurora_dream_substrate import gather_dream_substrate

        ledger = dt.FailPointLedger.__new__(dt.FailPointLedger)
        ledger.__init__(state_dir="/tmp")
        ledger.record_pre_outcome_event(
            outcome_label="corrected", severity=0.6,
            pre_outcome_pressure={"X": 0.1, "T": 0.2, "N": 0.3, "B": 0.4, "A": 0.5},
            identity={"topic": "boundaries", "action_type": "grounded_answer"},
        )
        systems = {"dimensional": None, "dream_trainer": SimpleNamespace(ledger=ledger)}
        substrate_dict = gather_dream_substrate(systems).to_dict()

        forbidden_substrings = ("lesson", "expected_correct", "answer_key", "correct_response")
        serialized = str(substrate_dict).lower()
        for marker in forbidden_substrings:
            assert marker not in serialized

    def test_substrate_gathering_module_is_never_imported_by_the_dream_generation_call_sites(self):
        """Confirms this pass did not wire the substrate into
        DreamTrainer.train_on_bundle / SimulationSession.run_episode /
        DreamCurriculumQueue's prompt construction -- per Repair Authority,
        deciding how much weight abstracted material should carry relative
        to today's literal corpus-text seeding is out of this pass's scope
        (see the report's own documented boundary)."""
        import inspect
        import aurora_dream_trainer as dt
        import aurora_simulation_engine as se
        import aurora_internal.aurora_dream_curriculum_queue as dcq

        for module in (dt, se, dcq):
            src = inspect.getsource(module)
            assert "aurora_dream_substrate" not in src

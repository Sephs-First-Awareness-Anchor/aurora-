# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA DREAM SUBSTRATE... DIRECTIVE, Sections 15-18, 50: positive waking
material (achievement/relief) must be independently available to Dream
synthesis, separate from the failure channel, and successful experience
must have Dream afterlife rather than only being relevant if it becomes a
fail point.
"""
import os
import sys
from types import SimpleNamespace

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)


def _real_dps():
    from aurora_dimensional_systems import CrystalProcessingSystem, EvolutionTracker
    return CrystalProcessingSystem(EvolutionTracker())


class TestPositiveChannelIsIndependentOfFailure:
    def test_positive_fragments_available_with_zero_fail_stream_activity(self):
        import aurora_dream_trainer as dt
        from aurora_dream_substrate import gather_dream_substrate

        dps = _real_dps()
        dps._get_or_create("successful_correction")
        dps.note_relief_event(["successful_correction"], dominant_axis="X", tick=1)

        ledger = dt.FailPointLedger.__new__(dt.FailPointLedger)  # no fails recorded at all
        ledger.__init__(state_dir=os.path.join(os.sep, "tmp"))
        systems = {
            "dimensional": SimpleNamespace(dps=dps),
            "dream_trainer": SimpleNamespace(ledger=ledger),
        }
        substrate = gather_dream_substrate(systems)
        assert substrate.fail_pressure_stream == []
        assert len(substrate.positive_fragments) >= 1
        assert substrate.positive_fragments[0]["salience_channel"] == "positive"

    def test_positive_and_negative_fragments_are_separately_queryable(self):
        from aurora_dream_substrate import gather_salient_fragments, gather_dream_substrate

        dps = _real_dps()
        dps._get_or_create("good_thing")
        dps.note_relief_event(["good_thing"], dominant_axis="X", tick=1)
        crystal = dps._get_or_create("bad_thing")
        crystal.failpoint_profile["context_carryover"] = {"prev": None, "current": None}
        dps.record_failpoint_update("context_carryover", prev_avg=0.2, current_avg=0.8)

        systems = {"dimensional": SimpleNamespace(dps=dps)}
        substrate = gather_dream_substrate(systems)
        positive_concepts = {f["concept"] for f in substrate.positive_fragments}
        all_concepts = {f["concept"] for f in substrate.salient_fragments}
        assert "good_thing" in positive_concepts
        assert "bad_thing" not in positive_concepts
        assert "bad_thing" in all_concepts


class TestSuccessDoesNotRequireBecomingAFailPoint:
    def test_a_purely_successful_episode_still_produces_positive_material(self):
        """Success must not be developmentally inert -- it must remain
        eligible for Dream even though it never touches FailPointLedger."""
        from aurora_dream_substrate import gather_salient_fragments

        dps = _real_dps()
        dps._get_or_create("mastery_moment")
        dps.note_relief_event(["mastery_moment"], dominant_axis="A", tick=7)

        fragments = gather_salient_fragments({"dimensional": SimpleNamespace(dps=dps)})
        assert len(fragments) == 1
        assert fragments[0].salience_channel == "positive"

# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
AURORA DREAM SUBSTRATE... DIRECTIVE, Sections 11-13, 49: Dream input must
reflect Aurora's own existing salience machinery (crystal facets stamped
by CrystalProcessingSystem.record_failpoint_update/note_relief_event),
never a new hand-authored emotional classifier, and must never carry
literal waking text/actions wholesale.
"""
import os
import sys
from types import SimpleNamespace

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)


def _real_dps():
    from aurora_dimensional_systems import CrystalProcessingSystem, EvolutionTracker
    return CrystalProcessingSystem(EvolutionTracker())


class TestSalienceReflectsAurorasOwnFacets:
    def test_gather_salient_fragments_reads_real_achievement_facets(self):
        from aurora_dream_substrate import gather_salient_fragments

        dps = _real_dps()
        crystal = dps._get_or_create("protecting_boundaries")
        crystal.failpoint_profile["context_carryover"] = {"prev": None, "current": None}
        dps.record_failpoint_update("context_carryover", prev_avg=0.6, current_avg=0.3)  # improving

        systems = {"dimensional": SimpleNamespace(dps=dps)}
        fragments = gather_salient_fragments(systems)
        assert any(f.facet_role == "achievement" and f.salience_channel == "positive" for f in fragments)

    def test_gather_salient_fragments_reads_real_misstep_facets(self):
        from aurora_dream_substrate import gather_salient_fragments

        dps = _real_dps()
        crystal = dps._get_or_create("protecting_boundaries")
        crystal.failpoint_profile["context_carryover"] = {"prev": None, "current": None}
        dps.record_failpoint_update("context_carryover", prev_avg=0.3, current_avg=0.6)  # worsening

        systems = {"dimensional": SimpleNamespace(dps=dps)}
        fragments = gather_salient_fragments(systems)
        assert any(f.facet_role == "misstep" and f.salience_channel == "negative" for f in fragments)

    def test_gather_salient_fragments_reads_real_relief_events(self):
        from aurora_dream_substrate import gather_salient_fragments

        dps = _real_dps()
        dps._get_or_create("protecting_boundaries")
        dps.note_relief_event(["protecting_boundaries"], dominant_axis="X", tick=42)

        systems = {"dimensional": SimpleNamespace(dps=dps)}
        fragments = gather_salient_fragments(systems)
        relief = [f for f in fragments if f.facet_role == "relief_event"]
        assert relief and relief[0].salience_channel == "positive"

    def test_no_dps_returns_empty_not_a_fabricated_fragment(self):
        from aurora_dream_substrate import gather_salient_fragments
        assert gather_salient_fragments({"dimensional": None}) == []
        assert gather_salient_fragments({}) == []


class TestFragmentsCarryNoLiteralWakingText:
    def test_fragment_content_is_a_short_native_tag_not_a_sentence(self):
        from aurora_dream_substrate import gather_salient_fragments

        dps = _real_dps()
        crystal = dps._get_or_create("protecting_boundaries")
        crystal.failpoint_profile["context_carryover"] = {"prev": None, "current": None}
        dps.record_failpoint_update("context_carryover", prev_avg=0.6, current_avg=0.3)

        systems = {"dimensional": SimpleNamespace(dps=dps)}
        fragments = gather_salient_fragments(systems)
        for f in fragments:
            # Native content tags are compact ("dimension:score" / "axis@tick"),
            # never a multi-word literal sentence copied from a user turn.
            assert len(f.content_tag) <= 60
            assert " " not in f.content_tag or f.content_tag.count(" ") <= 1

    def test_dream_fragment_dict_has_no_user_turns_or_assistant_turns_keys(self):
        from aurora_dream_substrate import gather_salient_fragments

        dps = _real_dps()
        dps._get_or_create("protecting_boundaries")
        dps.note_relief_event(["protecting_boundaries"], dominant_axis="X", tick=1)

        systems = {"dimensional": SimpleNamespace(dps=dps)}
        for f in gather_salient_fragments(systems):
            d = f.to_dict()
            assert "user_turns" not in d
            assert "assistant_turns" not in d
            assert "response_text" not in d


class TestSelectionIsObservedNotPreDetermined:
    def test_selection_reflects_whichever_facets_actually_exist(self):
        """The test does not pre-select which fragments 'should' survive --
        it constructs two different real crystal states and confirms the
        gathering function's output differs accordingly, i.e. genuinely
        observes Aurora's own stamps rather than returning a fixed list."""
        from aurora_dream_substrate import gather_salient_fragments

        dps_a = _real_dps()
        dps_a._get_or_create("alpha")
        dps_a.note_relief_event(["alpha"], dominant_axis="X", tick=1)

        dps_b = _real_dps()
        crystal_b = dps_b._get_or_create("beta")
        crystal_b.failpoint_profile["context_carryover"] = {"prev": None, "current": None}
        dps_b.record_failpoint_update("context_carryover", prev_avg=0.2, current_avg=0.8)

        fragments_a = gather_salient_fragments({"dimensional": SimpleNamespace(dps=dps_a)})
        fragments_b = gather_salient_fragments({"dimensional": SimpleNamespace(dps=dps_b)})

        concepts_a = {f.concept for f in fragments_a}
        concepts_b = {f.concept for f in fragments_b}
        assert concepts_a == {"alpha"}
        assert concepts_b == {"beta"}
        assert fragments_a[0].salience_channel == "positive"
        assert fragments_b[0].salience_channel == "negative"

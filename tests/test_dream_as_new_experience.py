# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Tests for aurora_dream_new_experience_canary.py, per the AURORA DREAM
SUBSTRATE... DIRECTIVE, Sections 22-30, 53.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aurora_dream_new_experience_canary as canary_module


class TestDreamAsNewExperience:
    def test_two_real_episodes_all_boundaries_preserved(self):
        records = canary_module.run_two_episodes(turns=4, seed_a=11, seed_b=22)
        assert records
        assert all(r.classification == "PRESERVED" for r in records), records

    def test_fresh_identity_specifically(self):
        records = canary_module.run_two_episodes(turns=3, seed_a=5, seed_b=6)
        fresh = [r for r in records if r.boundary == "fresh_episode_identity"][0]
        assert fresh.classification == "PRESERVED"

    def test_divergence_specifically_uses_a_real_perception_engine(self):
        """Regression guard for the specific bug this canary's own
        docstring documents: a bare SimulationSession() with no wired
        perception engine can produce a false-PRESERVED-looking identical
        trace across seeds. The canary must boot real Aurora (real
        perception engine) rather than construct a bare session."""
        import inspect
        src = (
            inspect.getsource(canary_module.run_two_episodes) +
            inspect.getsource(canary_module._boot_tmp_systems)
        )
        assert "boot_aurora" in src
        assert "SimulationSession()" not in src

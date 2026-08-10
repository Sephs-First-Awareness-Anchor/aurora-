# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Tests for aurora_representational_divergence_canaries.py, per the AURORA
LIVE REPRESENTATIONAL PROPAGATION AND CONSEQUENCE-BINDING DIRECTIVE,
Section 16 (divergence canaries A-F, one per ladder rung).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aurora_representational_divergence_canaries as canary_module


class TestDivergenceA_D1:
    def test_two_d1_refs_stay_distinguishable_through_overlay(self):
        records = canary_module.divergence_a_d1_understanding_sediment_overlay()
        assert records and all(r.classification == "PRESERVED" for r in records)


class TestDivergenceB_C1:
    def test_two_c1_refs_stay_distinguishable_through_sedimemory(self):
        records = canary_module.divergence_b_c1_sedimemory_passthrough()
        assert records and all(r.classification == "PRESERVED" for r in records)


class TestDivergenceC_D2:
    def test_two_d2_refs_stay_distinguishable_through_warp_without_influencing_routing(self):
        records = canary_module.divergence_c_d2_warp_demand_provenance()
        assert records and all(r.classification == "PRESERVED" for r in records)


class TestDivergenceD_M21:
    def test_two_m21_refs_stay_distinguishable_through_episode_step(self):
        records = canary_module.divergence_d_m21_rcec_episode_step()
        assert records and all(r.classification == "PRESERVED" for r in records)

    def test_does_not_force_a_live_selection_path_that_does_not_exist(self):
        import inspect
        src = inspect.getsource(canary_module.divergence_d_m21_rcec_episode_step)
        assert ".interpret(" not in src


class TestDivergenceE_M22:
    def test_two_m22_refs_both_recoverable_after_backprojection(self):
        records = canary_module.divergence_e_m22_rcec_backprojection()
        assert records and all(r.classification == "PRESERVED" for r in records)


class TestDivergenceF_C2:
    def test_live_origin_extends_to_two_distinct_real_manifold_slots(self):
        records = canary_module.divergence_f_c2_end_to_end_manifold_resolution()
        assert records
        assert all(r.classification in ("PRESERVED", "UNREACHABLE") for r in records)
        # This specific input is known (from the live-propagation tests) to
        # resolve a C1-level origin, so PRESERVED is the expected outcome
        # here, not merely an allowed one.
        assert records[0].classification == "PRESERVED", records[0].detail


class TestRunAllReturnsSixCanaries:
    def test_run_all_covers_every_ladder_rung(self):
        records = canary_module.run_all()
        canaries = {r.canary for r in records}
        assert canaries == {"A_D1", "B_C1", "C_D2", "D_M21_3125", "E_M22_15625", "F_C2"}

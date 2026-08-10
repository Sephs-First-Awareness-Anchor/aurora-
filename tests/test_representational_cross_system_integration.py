# Authors: Sunni (Sir) Morningstar & Cael Devo
"""
Tests for aurora_representational_cross_system_canary.py, per the AURORA
ESTABLISHED REPRESENTATIONAL SUBSTRATE FULL INTEGRATION DIRECTIVE,
Section 24 (canaries A-F).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aurora_representational_cross_system_canary as canary_module


class TestCanaryA_D1:
    def test_same_constraint_different_dimension_distinguishable(self):
        records = canary_module.canary_a_d1()
        assert all(r.classification == "PRESERVED" for r in records)


class TestCanaryB_C1:
    def test_contextual_identity_survives_manifold_resolution(self):
        records = canary_module.canary_b_c1()
        assert all(r.classification == "PRESERVED" for r in records)


class TestCanaryC_D2:
    def test_relationship_distinction_survives_slot_resolution(self):
        records = canary_module.canary_c_d2()
        assert all(r.classification == "PRESERVED" for r in records)


class TestCanaryD_3125:
    def test_substrate_preserves_what_live_selection_pins(self):
        records = canary_module.canary_d_3125()
        preserved = [r for r in records if r.boundary == "addressability_vs_live_pinning"]
        assert preserved and preserved[0].classification == "PRESERVED"
        pinned = [r for r in records if r.boundary == "live_construction_comparison"]
        assert pinned and pinned[0].classification == "PINNED"

    def test_does_not_force_production_selection(self):
        """Confirms the canary never calls into ReflexiveInterpreter.interpret()
        or SemanticMatcher.match() -- it only constructs refs directly."""
        import inspect
        src = inspect.getsource(canary_module.canary_d_3125)
        assert ".interpret(" not in src
        assert ".match(" not in src


class TestCanaryE_15625:
    def test_candidate_a_distinction_survives_all_three_boundaries(self):
        records = canary_module.canary_e_15625()
        assert len(records) == 3
        assert all(r.classification == "PRESERVED" for r in records), records

    def test_physics_difference_is_real_not_asserted(self):
        records = canary_module.canary_e_15625()
        physics = [r for r in records if r.boundary == "real_manifold_physics"][0]
        assert physics.ref_recovered_equal is True


class TestCanaryF_C2:
    def test_every_boundary_gets_an_honest_classification(self):
        records = canary_module.canary_f_c2()
        classifications = {r.classification for r in records}
        assert classifications <= {
            "PRESERVED", "TRANSFORMED", "INTENTIONALLY_COMPRESSED",
            "PINNED", "DEFAULTED", "SUMMARY_ONLY", "UNREACHABLE", "LOST",
        }
        # At least one PRESERVED (the point of this pass) and the WARP/
        # SediMemory boundaries must be honestly UNREACHABLE, not silently
        # upgraded to PRESERVED just because other boundaries succeeded.
        by_boundary = {r.boundary: r.classification for r in records}
        assert by_boundary["warp"] == "UNREACHABLE"
        assert by_boundary["sedimemory_write_direction"] == "UNREACHABLE"
        assert by_boundary["manifold_resolution"] == "PRESERVED"
        assert by_boundary["genealogy_notes_dict"] == "PRESERVED"
        assert by_boundary["dream_evidence_record_origin_tags"] == "PRESERVED"
        assert by_boundary["rcec_episode_step_field"] == "PRESERVED"

    def test_behavioral_difference_alone_is_not_the_preservation_criterion(self):
        """Every PRESERVED verdict in canary F must be backed by an actual
        recovered-reference check somewhere in its evidence chain, not by
        two different-looking summary strings."""
        records = canary_module.canary_f_c2()
        preserved = [r for r in records if r.classification == "PRESERVED"]
        assert preserved  # sanity: there is something to check
        for r in preserved:
            # Each PRESERVED detail must reference the concrete mechanism
            # checked (slot id, notes dict, origin_tags, or the field
            # itself) -- not a vague behavioral claim.
            assert any(term in r.detail for term in (
                "slot_id", "SUB[", "notes dict", "origin_tags", "representational_ref",
            )), r.detail


class TestFullCanarySuite:
    def test_run_all_canaries_produces_expected_boundary_count(self):
        records = canary_module.run_all_canaries()
        # A(1) + B(1) + C(1) + D(2) + E(3) + F(6)
        assert len(records) == 14

    def test_no_canary_mutates_manifold_directory_or_state(self):
        import hashlib

        def fingerprint(root):
            digest = hashlib.sha256()
            if not os.path.isdir(root):
                return None
            for dirpath, _dirnames, filenames in os.walk(root):
                for fn in sorted(filenames):
                    p = os.path.join(dirpath, fn)
                    try:
                        st = os.stat(p)
                    except OSError:
                        continue
                    digest.update(f"{p}:{st.st_size}:{st.st_mtime_ns}".encode("utf-8"))
            return digest.hexdigest()

        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        manifold_dir = os.path.join(repo_root, "aurora_manifold_directory")
        state_dir = os.path.join(repo_root, "aurora_state")
        before_m, before_s = fingerprint(manifold_dir), fingerprint(state_dir)

        canary_module.run_all_canaries()

        after_m, after_s = fingerprint(manifold_dir), fingerprint(state_dir)
        assert before_m == after_m
        assert before_s == after_s

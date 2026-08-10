#!/usr/bin/env python3
"""
Tests for aurora_rank6_shadow_analysis.py (RANK-6 falsification directive).

These tests are deliberately written to allow the 15,625 (= 5**6)
intermediate-rank hypothesis to FAIL. No test assumes the candidate rank is
real; every assertion below is checked against actually-executed values
from real, already-generated aurora_manifold_directory/*.json files, not
against an expected "yes it's real" answer chosen in advance.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import aurora_rank6_shadow_analysis as rank6
from aurora_constraint_manifold_router import AXES, DIM_NAMES

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BASES = [
    "Existential_Operator_of_Existence",   # diagonal noncomp (nc_law_c==nc_target, nc_dim==OPERATOR)
    "Boundary_Cost_of_Agency",             # cross-constraint noncomp (nc_law_c != nc_target)
    "Agentive_Cost_of_Agency",             # same-home, non-diagonal-dimension noncomp
]


@pytest.fixture(scope="module")
def directory():
    return rank6.load_manifold_directory_raw()


# ── Round-trip encoding tests (required) ────────────────────────────────────

class TestRoundTrip:
    def test_candidate_a_round_trips_exactly(self):
        """SlotCoord + sub_law_c: every one of the 15,625 enumerated
        coordinates must produce a unique, collision-free id."""
        count, unique, ok = rank6.verify_round_trip("A")
        assert count == 15625
        assert unique == 15625
        assert ok is True

    def test_candidate_b_round_trips_exactly(self):
        """SlotCoord + sub_law_d: same round-trip guarantee."""
        count, unique, ok = rank6.verify_round_trip("B")
        assert count == 15625
        assert unique == 15625
        assert ok is True


# ── Required test: only sub_law_c changes ───────────────────────────────────

class TestSubLawCIndependence:
    """Does sub_law_c, held alone against a fixed base + col, carry
    independent NUMERIC physics (not just a relabeled slot_id)?"""

    @pytest.mark.parametrize("nc_name", BASES)
    def test_sub_law_c_produces_five_distinct_numeric_states(self, directory, nc_name):
        nc = directory[nc_name]
        home_col = (nc["nc_law_c"], nc["nc_dim"])
        varied = rank6.vary_sub_law_c(directory, nc_name, home_col)
        assert len(varied) == 5
        distinct = rank6.count_distinct(varied, rank6.numeric_signature)
        # This assertion can fail: if sub_law_c were physics-inert like a
        # single D1 channel's own dimension coordinate (Phase B of the prior
        # audit), distinct would be 1, not 5.
        assert distinct == 5, (
            f"sub_law_c only produced {distinct}/5 distinct numeric states "
            f"at {nc_name} col={home_col} -- independence not supported here"
        )

    @pytest.mark.parametrize("nc_name", BASES)
    def test_sub_law_c_independence_holds_away_from_home_col(self, directory, nc_name):
        """Repeat with col deliberately NOT equal to the noncomp's own
        identity channel, so a single special case can't manufacture the
        result."""
        nc = directory[nc_name]
        home_col = (nc["nc_law_c"], nc["nc_dim"])
        away_col = ("T", "MAGNITUDE") if home_col != ("T", "MAGNITUDE") else ("N", "DIFFERENCE")
        varied = rank6.vary_sub_law_c(directory, nc_name, away_col)
        distinct = rank6.count_distinct(varied, rank6.numeric_signature)
        assert distinct == 5


# ── Required test: only sub_law_d changes ───────────────────────────────────

class TestSubLawDIndependence:
    """Does sub_law_d, held alone against a fixed base + col, carry
    independent NUMERIC physics? This test is written to allow a positive
    (independent) OR negative (coupled) result -- it reports what is
    actually found rather than assuming either answer."""

    @pytest.mark.parametrize("nc_name", BASES)
    def test_sub_law_d_numeric_distinctness_is_at_most_two(self, directory, nc_name):
        nc = directory[nc_name]
        home_col = (nc["nc_law_c"], nc["nc_dim"])
        varied = rank6.vary_sub_law_d(directory, nc_name, home_col)
        assert len(varied) == 5
        distinct = rank6.count_distinct(varied, rank6.numeric_signature)
        # Empirically: sub_law_d's numeric effect on evolution_grade /
        # accountability_weight is gated behind an exact-match ("IDENTITY")
        # condition against the noncomp's own identity -- a binary
        # (in-identity / not) distinction, never five independently
        # meaningful physical states. If this ever becomes 5, that is a
        # real architectural change and this test must be revisited, not
        # loosened blindly.
        assert distinct <= 2, (
            f"sub_law_d produced {distinct} distinct numeric states at "
            f"{nc_name} col={home_col} -- more independence than previously "
            f"found; re-examine before assuming the coupled verdict still holds"
        )

    @pytest.mark.parametrize("nc_name", BASES)
    def test_sub_law_d_label_varies_even_when_numbers_barely_do(self, directory, nc_name):
        """Confirms the directive's 'does context change physics, not just
        names' distinction: sub_law_d's cluster_pair LABEL is always real
        and 5-valued. The combined numeric signature (evolution_grade +
        accountability_weight + depth_score + combined_cost), measured away
        from the noncomp's own identity column, collapses to only 2 states
        -- driven entirely by accountability_weight's IDENTITY-cluster bonus
        (which fires whenever sub_law_c==nc_law_c and sub_law_d==nc_dim,
        regardless of col); evolution_grade/depth_score/combined_cost alone
        are fully flat (1 state) in this configuration. 5 label states does
        not mean 5 physical states."""
        nc = directory[nc_name]
        away_col = ("T", "MAGNITUDE") if (nc["nc_law_c"], nc["nc_dim"]) != ("T", "MAGNITUDE") else ("N", "DIFFERENCE")
        varied = rank6.vary_sub_law_d(directory, nc_name, away_col)
        label_distinct = rank6.count_distinct(varied, lambda s: (s["cluster_pair"],))
        numeric_distinct = rank6.count_distinct(varied, rank6.numeric_signature)
        evo_only_distinct = rank6.count_distinct(varied, lambda s: (s["evolution_grade"],))
        assert label_distinct == 5
        assert evo_only_distinct == 1
        assert numeric_distinct == 2  # accountability_weight alone still carries the IDENTITY bonus


# ── Required test: full 5x5 joint variation ─────────────────────────────────

class TestJointVariation:
    @pytest.mark.parametrize("nc_name", BASES)
    def test_joint_grid_is_25_cells_and_mostly_additive(self, directory, nc_name):
        nc = directory[nc_name]
        home_col = (nc["nc_law_c"], nc["nc_dim"])
        grid = rank6.joint_grid(directory, nc_name, home_col, "evolution_grade")
        assert len(grid) == 5
        assert all(len(row) == 5 for row in grid.values())
        dev = rank6.additivity_deviation(grid)
        # A single joint "anchor" interaction term (worth 0.10 in the real
        # _evo_grade formula) is the only non-additive component found --
        # not full irreducible joint coupling, and not zero (pure
        # independence) either.
        assert dev == pytest.approx(0.10, abs=1e-6)

    def test_joint_grid_all_25_cells_reachable_and_finite(self, directory):
        nc_name = BASES[0]
        nc = directory[nc_name]
        home_col = (nc["nc_law_c"], nc["nc_dim"])
        grid = rank6.joint_grid(directory, nc_name, home_col, "accountability_weight")
        for sub_lc in AXES:
            for v in grid[sub_lc]:
                assert 0.0 <= v <= 1.0


# ── Required test: falsification capability ─────────────────────────────────

class TestFalsifiabilityOfCandidateRank:
    def test_candidate_b_fails_the_independent_rank_bar(self, directory):
        """This is the test capable of DISPROVING the 15,625 hypothesis for
        candidate B. If sub_law_d had turned out to carry 5 independent
        numeric states like sub_law_c does, this test would fail and the
        hypothesis would gain support instead. It does not fail."""
        failures = []
        for nc_name in BASES:
            nc = directory[nc_name]
            for col in [(nc["nc_law_c"], nc["nc_dim"]), ("T", "MAGNITUDE")]:
                varied = rank6.vary_sub_law_d(directory, nc_name, col)
                distinct = rank6.count_distinct(varied, rank6.numeric_signature)
                if distinct >= 5:
                    failures.append((nc_name, col, distinct))
        assert failures == [], (
            "sub_law_d showed full 5-way independent numeric variation in "
            f"at least one case ({failures}) -- this WOULD support a "
            "confirmed representational rank for candidate B and the "
            "report's coupled-verdict conclusion would need to change"
        )

    def test_candidate_a_passes_the_independent_rank_bar_everywhere_tested(self, directory):
        """The mirror-image test: this one CAN fail if sub_law_c turns out
        to be inert somewhere, which would undercut candidate A's
        'confirmed representational rank' verdict."""
        for nc_name in BASES:
            nc = directory[nc_name]
            for col in [(nc["nc_law_c"], nc["nc_dim"]), ("T", "MAGNITUDE")]:
                varied = rank6.vary_sub_law_c(directory, nc_name, col)
                distinct = rank6.count_distinct(varied, rank6.numeric_signature)
                assert distinct == 5, f"sub_law_c inert at {nc_name} col={col}"


# ── Required test: exact structural factorization of 78,125 ────────────────

class TestRefactor78125:
    def test_arithmetic_identities(self):
        checks = rank6.refactor_78125_checks()
        assert checks["matches_total"] is True
        assert checks["matches_total_via_15625"] is True

    def test_only_one_factorization_matches_a_real_staged_construction(self):
        checks = rank6.refactor_78125_checks()
        # Both factorizations are arithmetically true (78,125 either way).
        # Only 3,125 x 25 corresponds to an actual staged loop in the real
        # compiler (nc identity -> sub position -> col position). This test
        # exists so a future change to the compiler's loop structure would
        # be caught rather than silently assumed away.
        assert checks["staged_construction_3125x25_matches_real_compiler_loop_nesting"] is True
        assert checks["staged_construction_15625x5_matches_any_real_compiler_step"] is False


# ── Required test: static vs. live coordinate reachability ─────────────────

class TestStaticVsLiveReachability:
    def test_slotcoord_static_generator_is_fully_independent(self):
        """The static SlotCoord generator (aurora_constraint_manifold_router
        .RouteIndex.__init__) enumerates AXES x AXES x DIM_NAMES x AXES x
        DIM_NAMES independently -- 5**5 = 3125, all fields free."""
        assert len(AXES) ** 3 * len(DIM_NAMES) ** 2 == 3125

    def test_live_cers_resolver_derives_two_of_five_fields(self):
        """cers_tensor_locator.resolve_pressure_coordinate derives nc_dim
        from nc_law_c and law_d from law_c via a fixed axis<->dimension
        table (_DIMENSION_TO_AXIS) -- confirmed by reading the source function
        directly here rather than re-trusting a prior summary."""
        import inspect
        from aurora_internal.dual_strata import cers_tensor_locator as loc
        src = inspect.getsource(loc.resolve_pressure_coordinate)
        assert "axis_to_dim.get(nc_law_c" in src
        assert "axis_to_dim.get(law_c" in src
        # i.e. nc_dim and law_d are NOT independently chosen live -- they are
        # deterministic functions of nc_law_c / law_c respectively.

    def test_live_manifold_field_map_call_site_pins_col_to_sub(self):
        """The one confirmed live consumer of the full (sub, col) manifold
        coordinate (ReflexiveInterpreter.interpret() via
        ManifoldFieldMap.accountability_at) always calls it with
        col_law_c == sub_law_c and col_law_d == 'OPERATOR' -- col is never
        independently exercised at that call site."""
        import inspect
        import aurora_reflexive_interpreter as ri
        src = inspect.getsource(ri.ReflexiveInterpreter.interpret)
        assert 'fmap.accountability_at(' in src
        assert 'match.constraint, match.dimension' in src
        assert '"OPERATOR"' in src


# ── Required test: no production state is modified ──────────────────────────

class TestNoStateMutation:
    """Snapshots hashes of every file this investigation reads, runs the
    full analysis, then re-hashes -- proving nothing was written."""

    def _hash_tree(self, root):
        """(path, size, mtime_ns) fingerprint of every file under root.
        Cheap enough to run twice on a 180MB+ tree, and catches any write
        (size and/or mtime always change on write) without reading file
        contents -- exactly what's needed to prove "nothing was modified"."""
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

    def test_manifold_directory_and_state_untouched_by_full_analysis(self, directory):
        manifold_dir = os.path.join(REPO_ROOT, "aurora_manifold_directory")
        state_dir = os.path.join(REPO_ROOT, "aurora_state")

        before_manifold = self._hash_tree(manifold_dir)
        before_state = self._hash_tree(state_dir)

        # Run the full read-only analysis surface once more.
        rank6.verify_round_trip("A")
        rank6.verify_round_trip("B")
        for nc_name in BASES:
            nc = directory[nc_name]
            home_col = (nc["nc_law_c"], nc["nc_dim"])
            rank6.vary_sub_law_c(directory, nc_name, home_col)
            rank6.vary_sub_law_d(directory, nc_name, home_col)
            rank6.joint_grid(directory, nc_name, home_col)
        rank6.refactor_78125_checks()

        after_manifold = self._hash_tree(manifold_dir)
        after_state = self._hash_tree(state_dir)

        assert before_manifold == after_manifold
        assert before_state == after_state


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))

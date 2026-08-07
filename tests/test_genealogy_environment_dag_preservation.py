#!/usr/bin/env python3
"""
Tests for aurora_genealogy_environment.py's full-DAG genealogy-to-environment
derivation, per the genealogy-native representational environment directive.

These tests establish, against real ConstraintLink objects (not mocks of the
derivation logic itself), that:

  1. Two genealogies with an IDENTICAL merged axis histogram but different
     recursive/parent topology are treated as identical by the existing
     constraint_genealogy._merged_axis_counts_for_pair() reduction, but are
     distinguished by aurora_genealogy_environment's full-DAG derivation.
  2. A renamed substrate with an identical underlying genealogy produces an
     identical derived environment (the derivation never reads a name).
  3. Two differently-named/labelled genealogies with different structure but
     equal aggregate X/T/N/B/A totals can produce different signatures.
  4. Shadow comparison against the real _CORE_CREST_PROFILES runs without
     mutating any WARP/crest state.
  5. WARP's trial/promotion machinery is untouched by this module (no import,
     no call) -- an environmental mismatch alone cannot promote anything.

Authors: Sunni (Sir) Morningstar & Cael Devo
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from aurora_genealogy_environment import (
    derive_environment_signature,
    logger_from_links,
    compare_against_core_crests,
    project_to_crest_profile,
)
from aurora_internal.constraint_genealogy import ConstraintLink, TraceItem


def _link(link_id, parents, depth, axis, relief_axes):
    """Build a real ConstraintLink with the given dominant axis and a full
    5-axis mean_relief dict (nonzero only on relief_axes, equal magnitude)."""
    mean_relief = {a: (0.01 if a in relief_axes else 0.0) for a in ("X", "T", "N", "B", "A")}
    return ConstraintLink(
        id=link_id,
        parents=list(parents),
        depth=depth,
        created_at_tick=0,
        count=1,
        mean_relief=mean_relief,
        mean_cost={a: 0.0 for a in ("X", "T", "N", "B", "A")},
        mean_x_risk=0.0,
        stdev_relief={a: 0.0 for a in ("X", "T", "N", "B", "A")},
        dominant_relief_axis=axis,
        tags=[],
    )


def _forward_chain():
    """X -> T -> N, oldest-ancestor-first. Root leaves are bare ability ids."""
    l1 = _link("L:fwd1", ["A:root"], 1, "X", {"X"})
    l2 = _link("L:fwd2", ["L:fwd1"], 2, "T", {"T"})
    l3 = _link("L:fwd3", ["L:fwd2"], 3, "N", {"N"})
    return {"L:fwd1": l1, "L:fwd2": l2, "L:fwd3": l3}, "L:fwd3"


def _reversed_chain():
    """N -> T -> X: same three axes, each appearing once, but built in the
    opposite recursive order. Same merged axis histogram as _forward_chain()."""
    l1 = _link("L:rev1", ["A:root"], 1, "N", {"N"})
    l2 = _link("L:rev2", ["L:rev1"], 2, "T", {"T"})
    l3 = _link("L:rev3", ["L:rev2"], 3, "X", {"X"})
    return {"L:rev1": l1, "L:rev2": l2, "L:rev3": l3}, "L:rev3"


class TestAxisHistogramIdenticalTopologyDiffers:
    def test_merged_axis_counts_treats_both_chains_as_identical(self):
        """Confirms, executably, the information-loss this directive targets:
        constraint_genealogy's existing reduction path sees these two
        structurally different genealogies as the same histogram."""
        fwd_links, fwd_root = _forward_chain()
        rev_links, rev_root = _reversed_chain()

        fwd_logger = logger_from_links(fwd_links)
        rev_logger = logger_from_links(rev_links)

        fwd_counts = fwd_logger._axis_counts_from_item(
            TraceItem(id=fwd_root, kind="LINK"), memo={}, seen=set()
        )
        rev_counts = rev_logger._axis_counts_from_item(
            TraceItem(id=rev_root, kind="LINK"), memo={}, seen=set()
        )
        assert fwd_counts == rev_counts, (
            "expected the existing axis-count reduction to be topology-blind "
            f"but got fwd={fwd_counts} rev={rev_counts}"
        )

    def test_full_dag_derivation_distinguishes_the_same_pair(self):
        fwd_links, fwd_root = _forward_chain()
        rev_links, rev_root = _reversed_chain()

        fwd_logger = logger_from_links(fwd_links)
        rev_logger = logger_from_links(rev_links)

        fwd_sig = derive_environment_signature(fwd_logger, fwd_root)
        rev_sig = derive_environment_signature(rev_logger, rev_root)

        assert not fwd_sig.insufficient_genealogy
        assert not rev_sig.insufficient_genealogy

        # Identical axis histogram (both chains: one X, one T, one N unit each).
        assert fwd_sig.axis_distribution == rev_sig.axis_distribution

        # But the ordered traversal differs, so the resolved genealogy atoms,
        # active slots, chained root_slot, and signature hash must differ.
        assert fwd_sig.chained_root_slot != rev_sig.chained_root_slot
        assert fwd_sig.active_slots != rev_sig.active_slots
        assert fwd_sig.signature_hash != rev_sig.signature_hash
        assert fwd_sig.provenance != rev_sig.provenance


class TestNameBlindness:
    def test_same_genealogy_under_different_labels_produces_identical_signature(self):
        links_a, root_a = _forward_chain()
        # Re-key the exact same structure under different ids/"names" -- the
        # derivation must not care what anything is called.
        links_b = {
            "L:imagination_x": _link("L:imagination_x", ["A:root"], 1, "X", {"X"}),
            "L:imagination_t": _link("L:imagination_t", ["L:imagination_x"], 2, "T", {"T"}),
            "L:imagination_n": _link("L:imagination_n", ["L:imagination_t"], 3, "N", {"N"}),
        }
        root_b = "L:imagination_n"

        sig_a = derive_environment_signature(logger_from_links(links_a), root_a)
        sig_b = derive_environment_signature(logger_from_links(links_b), root_b)

        assert sig_a.axis_distribution == sig_b.axis_distribution
        assert sig_a.dimension_distribution == sig_b.dimension_distribution
        assert sig_a.recursion_distribution == sig_b.recursion_distribution
        assert sig_a.istate_distribution == sig_b.istate_distribution
        assert sig_a.chained_root_slot == sig_b.chained_root_slot
        # signature_hash intentionally includes provenance (real link ids), so
        # it differs here -- structure-only fields above are what must match.

    def test_different_genealogies_same_totals_can_differ(self):
        """Two 2-node genealogies with equal per-axis totals (one X, one T
        each) but different recursion depth / parent structure."""
        shallow = {
            "L:s1": _link("L:s1", ["A:root"], 1, "X", {"X"}),
            "L:s2": _link("L:s2", ["A:root"], 1, "T", {"T"}),
            "L:s3": _link("L:s3", ["L:s1", "L:s2"], 2, "T", {"T"}),
        }
        deep = {
            "L:d1": _link("L:d1", ["A:root"], 1, "X", {"X"}),
            "L:d2": _link("L:d2", ["L:d1"], 2, "T", {"T"}),
            "L:d3": _link("L:d3", ["L:d2"], 3, "T", {"T"}),
        }
        sig_shallow = derive_environment_signature(logger_from_links(shallow), "L:s3")
        sig_deep = derive_environment_signature(logger_from_links(deep), "L:d3")

        assert sig_shallow.recursion_distribution != sig_deep.recursion_distribution
        assert sig_shallow.signature_hash != sig_deep.signature_hash


class TestShadowComparisonNonAuthoritative:
    def test_compare_against_core_crests_runs_and_stays_bounded(self):
        from aurora_internal.dual_strata import subsystem_waveforms as sw

        before = {k: dict(v) for k, v in sw._CORE_CREST_PROFILES.items()}

        links, root = _forward_chain()
        sig = derive_environment_signature(logger_from_links(links), root)
        result = compare_against_core_crests(sig)

        assert set(result.keys()) == set(before.keys())
        for score in result.values():
            assert -1.0001 <= score <= 1.0001

        after = {k: dict(v) for k, v in sw._CORE_CREST_PROFILES.items()}
        assert before == after, "shadow comparison must not mutate authored crest profiles"

    def test_empty_genealogy_projects_to_empty_profile(self):
        empty_logger = logger_from_links({})
        sig = derive_environment_signature(empty_logger, "L:does_not_exist")
        assert sig.insufficient_genealogy
        assert project_to_crest_profile(sig) == {}
        assert compare_against_core_crests(sig) == {}


class TestWarpUntouched:
    def test_module_never_imports_warp_authority_surfaces(self):
        import aurora_genealogy_environment as mod
        import inspect

        source = inspect.getsource(mod)
        for forbidden in (
            "WarpGenerator(",
            "_record_anomaly(",
            "check_and_extend(",
            "evaluate_warp_trials(",
            ".generate(",
        ):
            assert forbidden not in source, (
                f"aurora_genealogy_environment.py must stay observational; "
                f"found reference to WARP authority surface: {forbidden!r}"
            )

    def test_derivation_and_comparison_are_pure(self, tmp_path):
        """No new files should appear under the real aurora_state/ directory
        as a side effect of deriving or shadow-comparing an environment."""
        real_state_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aurora_state"
        )
        before = set(os.listdir(real_state_dir))

        links, root = _forward_chain()
        sig = derive_environment_signature(logger_from_links(links), root)
        compare_against_core_crests(sig)

        after = set(os.listdir(real_state_dir))
        assert before == after


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))

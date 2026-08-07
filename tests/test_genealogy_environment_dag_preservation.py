#!/usr/bin/env python3
"""
Tests for aurora_genealogy_environment.py's full-DAG genealogy-to-environment
derivation, per the genealogy-native representational environment directive
and its Phase 1.1 edge-fidelity repair.

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
  4. Genealogical transitions come from real ConstraintLink.parents edges,
     never from adjacency in walk_link_sequence()'s flat traversal list --
     covering a 4+ atom linear chain, a genuine diamond DAG, two DAGs that
     produce the SAME flat linear walk but different real structure, and an
     explicit check that no edge is fabricated between unrelated siblings.
  5. structural_hash is label-independent (same topology, different link ids
     -> same hash) while provenance_hash is not (it is meant to be sensitive
     to which specific fossils produced the genealogy).
  6. Shadow comparison against the real _CORE_CREST_PROFILES runs without
     mutating any WARP/crest state.
  7. WARP's trial/promotion machinery is untouched by this module (no import,
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


def _linear_chain_5():
    """5-node straight chain X->T->N->B->A. One self edge (root), 4 real
    parent_child edges -- exercises a 4+ atom root_slot chain end to end."""
    l1 = _link("L:lin1", ["A:root"], 1, "X", {"X"})
    l2 = _link("L:lin2", ["L:lin1"], 2, "T", {"T"})
    l3 = _link("L:lin3", ["L:lin2"], 3, "N", {"N"})
    l4 = _link("L:lin4", ["L:lin3"], 4, "B", {"B"})
    l5 = _link("L:lin5", ["L:lin4"], 5, "A", {"A"})
    return {"L:lin1": l1, "L:lin2": l2, "L:lin3": l3, "L:lin4": l4, "L:lin5": l5}, "L:lin5"


def _diamond():
    """Genuine diamond: L_A -> {L_B, L_C} -> L_D. L_B and L_C are siblings
    (both children of L_A, both parents of L_D) with NO real edge between
    them, even though a post-order DFS will visit them consecutively."""
    l_a = _link("L:dia_a", ["A:root"], 1, "X", {"X"})
    l_b = _link("L:dia_b", ["L:dia_a"], 2, "T", {"T"})
    l_c = _link("L:dia_c", ["L:dia_a"], 2, "N", {"N"})
    l_d = _link("L:dia_d", ["L:dia_b", "L:dia_c"], 3, "B", {"B"})
    return {"L:dia_a": l_a, "L:dia_b": l_b, "L:dia_c": l_c, "L:dia_d": l_d}, "L:dia_d", l_a.id, l_b.id, l_c.id, l_d.id


def _same_linear_walk_pair():
    """Two 3-node DAGs whose walk_link_sequence() axis order is IDENTICAL
    ([X, T, N]) but whose real ConstraintLink.parents structure differs:
    DAG A is a plain chain (La->Lb->Lc); DAG B's Lc has TWO real parents
    (La and Lb), a merge that a flat-list-adjacency reading cannot see."""
    la = _link("L:chain_a", ["A:root"], 1, "X", {"X"})
    lb = _link("L:chain_b", ["L:chain_a"], 2, "T", {"T"})
    lc = _link("L:chain_c", ["L:chain_b"], 3, "N", {"N"})
    chain_dag = {"L:chain_a": la, "L:chain_b": lb, "L:chain_c": lc}

    la2 = _link("L:merge_a", ["A:root"], 1, "X", {"X"})
    lb2 = _link("L:merge_b", ["L:merge_a"], 2, "T", {"T"})
    lc2 = _link("L:merge_c", ["L:merge_a", "L:merge_b"], 3, "N", {"N"})
    merge_dag = {"L:merge_a": la2, "L:merge_b": lb2, "L:merge_c": lc2}

    return (chain_dag, "L:chain_c"), (merge_dag, "L:merge_c")


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
        # active slots, and both hashes must differ.
        assert fwd_sig.chained_root_slot != rev_sig.chained_root_slot
        assert fwd_sig.active_slots != rev_sig.active_slots
        assert fwd_sig.structural_hash != rev_sig.structural_hash
        assert fwd_sig.provenance_hash != rev_sig.provenance_hash
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
        # structural_hash is explicitly label-independent -- must match.
        assert sig_a.structural_hash == sig_b.structural_hash
        # provenance_hash includes real link ids, so it legitimately differs.
        assert sig_a.provenance_hash != sig_b.provenance_hash

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
        assert sig_shallow.structural_hash != sig_deep.structural_hash


class TestEdgeFidelity:
    """Phase 1.1: transitions must come from real ConstraintLink.parents
    edges among the walked nodes, never from adjacency in the flat
    walk_link_sequence() list."""

    def test_four_plus_atom_chain_resolves_through_unicode_separator(self):
        links, root = _linear_chain_5()
        sig = derive_environment_signature(logger_from_links(links), root)

        assert not sig.insufficient_genealogy
        # 1 self edge (L:lin1's only parent is a bare ability leaf) + 4 real
        # parent_child edges (lin2<-lin1, lin3<-lin2, lin4<-lin3, lin5<-lin4).
        assert len(sig.edge_provenance) == 5
        assert sum(1 for e in sig.edge_provenance if e["edge_type"] == "self") == 1
        assert sum(1 for e in sig.edge_provenance if e["edge_type"] == "parent_child") == 4

        # Unicode x is used, never ASCII "x" repeated -- and
        # _resolve_slots_from_root_slot only takes the unambiguous branch for
        # a Unicode-joined string of any length.
        assert "×" in sig.chained_root_slot
        assert sig.chained_root_slot.count("×") == 4

        from aurora_closure_basis import _resolve_slots_from_root_slot
        resolved = _resolve_slots_from_root_slot(sig.chained_root_slot)
        assert len(resolved) > 0, "the chained root_slot must actually resolve to real slots"

        assert sig.closure_projection is not None
        # X>X, X>T, T>N, N>B, B>A -- five distinct real-edge atoms must all
        # resolve into the deduplicated closure projection. (It also legally
        # contains MORE slots than these 5: derive_lineage() independently
        # adds axis+requires-derived slots regardless of root_slot content --
        # that is pre-existing derive_lineage() behavior, not something this
        # edge-fidelity repair changes, which is exactly why the result is
        # named closure_projection rather than claimed as a faithful replay.)
        expected_edge_slots = {
            "NC:X:OPERATORxNC:X:COST", "NC:X:OPERATORxNC:T:COST",
            "NC:T:OPERATORxNC:N:COST", "NC:N:OPERATORxNC:B:COST",
            "NC:B:OPERATORxNC:A:COST",
        }
        assert expected_edge_slots.issubset(set(sig.closure_projection.active_slots))

    def test_ascii_join_of_the_same_chain_would_have_silently_failed(self):
        """Regression guard for the exact Phase 1 bug: joining 5 atoms with
        ASCII "x" produces a string _resolve_slots_from_root_slot cannot
        parse (count("x") != 1), so it must resolve to nothing -- proving why
        the Unicode join in the code under test is load-bearing, not
        cosmetic."""
        links, root = _linear_chain_5()
        sig = derive_environment_signature(logger_from_links(links), root)

        from aurora_closure_basis import _resolve_slots_from_root_slot
        atoms = sig.chained_root_slot.split("×")
        assert len(atoms) == 5
        ascii_joined = "x".join(atoms)
        assert ascii_joined.count("x") != 1
        assert _resolve_slots_from_root_slot(ascii_joined) == []

    def test_diamond_dag_produces_real_edges_not_flat_adjacency(self):
        links, root, a_id, b_id, c_id, d_id = _diamond()
        logger = logger_from_links(links)
        sequence = logger.walk_link_sequence(root)

        # Sanity: confirm the DFS really does place the two siblings
        # adjacently in the flat list before D, which is exactly the
        # situation the old (Phase 1) consecutive-pairs code would have
        # mistaken for a real transition between them.
        seq_ids = [n["link_id"] for n in sequence]
        assert seq_ids.index(b_id) + 1 == seq_ids.index(c_id) or seq_ids.index(c_id) + 1 == seq_ids.index(b_id)

        sig = derive_environment_signature(logger, root)
        # 1 self edge (A's own parent is a bare ability leaf)
        # + 2 parent_child edges (B<-A, C<-A)
        # + 2 parent_child edges (D<-B, D<-C)
        assert len(sig.edge_provenance) == 5
        assert sum(1 for e in sig.edge_provenance if e["edge_type"] == "self") == 1
        assert sum(1 for e in sig.edge_provenance if e["edge_type"] == "parent_child") == 4

    def test_no_sibling_transition_is_fabricated_between_diamond_branches(self):
        links, root, a_id, b_id, c_id, d_id = _diamond()
        sig = derive_environment_signature(logger_from_links(links), root)

        sibling_pair = {b_id, c_id}
        for edge in sig.edge_provenance:
            pair = {edge["parent_link_id"], edge["child_link_id"]}
            assert pair != sibling_pair, (
                f"fabricated an edge between siblings {b_id} and {c_id}, "
                "which share a parent but are not themselves connected"
            )

    def test_same_linear_walk_different_real_structure_diverges(self):
        (chain_dag, chain_root), (merge_dag, merge_root) = _same_linear_walk_pair()

        chain_logger = logger_from_links(chain_dag)
        merge_logger = logger_from_links(merge_dag)

        # Confirm the premise: identical flat axis-order walk.
        chain_axes = [n["axis"] for n in chain_logger.walk_link_sequence(chain_root)]
        merge_axes = [n["axis"] for n in merge_logger.walk_link_sequence(merge_root)]
        assert chain_axes == merge_axes == ["X", "T", "N"]

        chain_sig = derive_environment_signature(chain_logger, chain_root)
        merge_sig = derive_environment_signature(merge_logger, merge_root)

        # Chain: 1 self edge + 2 parent_child edges (Lb<-La, Lc<-Lb) = 3.
        # Merge: 1 self edge + 3 parent_child edges (Lb<-La, Lc<-La, Lc<-Lb) = 4.
        assert len(chain_sig.edge_provenance) == 3
        assert len(merge_sig.edge_provenance) == 4
        assert chain_sig.structural_hash != merge_sig.structural_hash
        assert chain_sig.chained_root_slot != merge_sig.chained_root_slot


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

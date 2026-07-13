"""
tests/test_topology_cycle_decomposition.py
=============================================
MTSL Phase 1 (2026-07-13): greedy-peel cycle decomposition correctness,
including the mandatory shared-edge double-count case -- two cycles that
share an edge must not have that edge's mass counted twice.
"""
from aurora_internal.dual_strata.topology_tracker import _FlowWindow, WINDOW_CONFIG


def _ready_window(scale="micro"):
    w = _FlowWindow(scale)
    w._observations = WINDOW_CONFIG[scale]["min_observations"]
    return w


def test_shared_edge_is_not_double_counted():
    """
    Two cycles X->T->N->X and X->T->B->X share edge X->T. The shared
    edge only carries 4.0 units of flux; the non-shared edges (T->N,
    N->X, T->B, B->X) carry 10.0 each (never the bottleneck). A correct
    peel must not extract 4.0 for *each* cycle (8.0 total) since the
    shared edge physically cannot supply that -- it must peel the first
    cycle (consuming the shared edge's capacity), leaving nothing for
    the second.
    """
    w = _ready_window()
    w._flux[("X", "T")] = 4.0
    w._flux[("T", "N")] = 10.0
    w._flux[("N", "X")] = 10.0
    w._flux[("T", "B")] = 10.0
    w._flux[("B", "X")] = 10.0

    sig = w.signature()

    assert sig.cyclic_mass == 4.0, f"shared edge double-counted: got {sig.cyclic_mass}"
    # only one cycle should have been extractable -- the shared edge is
    # exhausted after the first peel, so the second cycle can't clear eps.
    # Both candidate cycles have an equal bottleneck (4.0); which one wins
    # is a canonical-rotation tie-break, not something this test pins down.
    assert len(sig.loops) == 1
    path, strength = sig.loops[0]
    assert set(path) in ({"X", "T", "N"}, {"X", "T", "B"})
    assert strength == 4.0


def test_two_independent_cycles_both_fully_counted():
    """
    Two cycles that do NOT share an edge should both be fully extracted;
    their masses simply add.
    """
    w = _ready_window()
    # cycle 1: X -> T -> N -> X, bottleneck 3
    w._flux[("X", "T")] = 3.0
    w._flux[("T", "N")] = 3.0
    w._flux[("N", "X")] = 3.0
    # cycle 2: A -> B -> A (2-cycle not allowed, len>=3 required) -- use
    # a disjoint 3-cycle on remaining axes isn't possible with only 5
    # axes and 3 already used, so reuse two axes but no shared edge:
    # B -> A -> X ... would touch X, so instead just verify additivity
    # with a second cycle sharing only a *vertex*, not an edge, with the
    # first (vertex-sharing must be handled independently of edges).
    w._flux[("X", "B")] = 1.5
    w._flux[("B", "A")] = 1.5
    w._flux[("A", "X")] = 1.5

    sig = w.signature()

    assert sig.cyclic_mass == 3.0 + 1.5
    assert len(sig.loops) == 2
    paths = {frozenset(p) for p, _ in sig.loops}
    assert frozenset({"X", "T", "N"}) in paths
    assert frozenset({"X", "B", "A"}) in paths


def test_peeling_reduces_remainder_monotonically():
    w = _ready_window()
    w._flux[("X", "T")] = 4.0
    w._flux[("T", "N")] = 10.0
    w._flux[("N", "X")] = 10.0
    w._flux[("T", "B")] = 10.0
    w._flux[("B", "X")] = 10.0

    A = w._antisymmetric()
    peeled, cyclic_mass, remainder = w._peel_cycles(A, eps=1e-6)

    # after peeling, no edge in the remainder should exceed its
    # pre-peel value (mass can only be removed, never added).
    for edge, val in remainder.items():
        assert val <= A.get(edge, 0.0) + 1e-9

    # the shared edge should be fully exhausted (down to ~0), since it
    # was the bottleneck of the one cycle extracted.
    assert abs(remainder[("X", "T")]) < 1e-6


def test_below_noise_floor_cycles_are_not_extracted():
    w = _ready_window()
    # a cycle whose bottleneck is tiny relative to total traffic should
    # not be extracted -- it's noise, not a real loop.
    w._flux[("X", "T")] = 100.0
    w._flux[("T", "N")] = 100.0
    w._flux[("N", "X")] = 100.0
    w._flux[("T", "B")] = 0.001  # far below CYCLE_EPS_FRACTION * traffic
    w._flux[("B", "X")] = 0.001
    w._flux[("X", "B")] = 0.0

    sig = w.signature()
    # only the strong X-T-N cycle should show up
    assert len(sig.loops) == 1
    path, _ = sig.loops[0]
    assert set(path) == {"X", "T", "N"}


def test_circulation_fraction_is_one_for_pure_cyclic_traffic():
    w = _ready_window()
    w._flux[("X", "T")] = 5.0
    w._flux[("T", "N")] = 5.0
    w._flux[("N", "X")] = 5.0

    sig = w.signature()
    assert sig.regime == "circulating"
    assert abs(sig.circulation_fraction - 1.0) < 1e-6
    assert sig.gradient_mass == 0.0
    assert sig.residual_mass == 0.0


def test_pure_gradient_traffic_has_no_loops():
    w = _ready_window()
    # a straight source->sink chain, no cycle possible
    w._flux[("X", "T")] = 5.0
    w._flux[("T", "N")] = 5.0

    sig = w.signature()
    assert sig.loops == ()
    assert sig.cyclic_mass == 0.0
    assert sig.regime == "gradient"

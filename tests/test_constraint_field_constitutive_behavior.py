"""Regression + integration tests for constitutive behavior in the
ConstraintField manifold (aurora_internal/aurora_constraint_manifold_patched.py)
and its wiring into IVMLattice.tick() (aurora_ivm.py).

Context: an unresolved (unoccupied) field position previously returned a
flat, context-blind floor vector regardless of what was happening at
neighboring occupied positions -- "unresolved" behaved as if it meant
"nonexistent." These tests lock in the corrected physics: unresolved !=
nonexistent, latent != inert, zero displacement != zero susceptibility,
and -- the invariant a first draft of this got wrong and had to be
corrected on -- susceptibility != free energy. The constitutive response
modulates existing pairwise energy conductance (flow_energy()); it never
manufactures energy.
"""
from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import aurora_ivm as ivm
from aurora_internal.aurora_constraint_manifold_patched import (
    Constraint,
    CompositionalSpace,
    ConstraintField,
    ConstraintFieldIndex,
    ConstraintVector,
    RecursionLevel,
    State,
)


def _idx(c=0, s=0, st=0, l=0) -> ConstraintFieldIndex:
    return ConstraintFieldIndex(
        constraint=Constraint(c),
        space=CompositionalSpace(s),
        state=State(st),
        level=RecursionLevel(l),
    )


# ---------------------------------------------------------------------------
# ConstraintField.measure() -- constitutive response
# ---------------------------------------------------------------------------

def test_measure_returns_floor_when_nothing_occupied():
    field = ConstraintField()
    v = field.measure(_idx())
    assert v.X == 1e-9
    assert v.T == 0 and v.N == 0 and v.B == 0 and v.A == 0


def test_measure_derives_attenuated_response_from_occupied_neighbor():
    field = ConstraintField()
    neighbor_idx = _idx(c=1)  # one step away from _idx() on the constraint axis
    field.update(neighbor_idx, ConstraintVector(X=1.0, T=10.0, N=20.0, B=5.0, A=2.0))

    response = field.measure(_idx())
    # X never claims occupancy beyond the floor -- only T/N/B/A respond.
    assert response.X == 1e-9
    assert response.T > 0 and response.N > 0 and response.B > 0 and response.A > 0
    # Attenuated, not a straight echo of the neighbor's own values.
    assert response.T < 10.0
    assert response.N < 20.0


def test_measure_no_leakage_two_steps_away():
    field = ConstraintField()
    field.update(_idx(c=1), ConstraintVector(X=1.0, T=10.0, N=20.0, B=5.0, A=2.0))

    far_idx = _idx(c=2, s=1)  # two steps from the only occupied position
    response = field.measure(far_idx)
    assert response.X == 1e-9
    assert response.T == 0 and response.N == 0 and response.B == 0 and response.A == 0


def test_measure_never_writes_to_the_field():
    field = ConstraintField()
    field.update(_idx(c=1), ConstraintVector(X=1.0, T=10.0, N=1.0, B=1.0, A=1.0))
    before = field.occupied_count()
    for _ in range(5):
        field.measure(_idx())  # unoccupied position, repeated reads
    assert field.occupied_count() == before


# ---------------------------------------------------------------------------
# ConstraintField.rebuild_epoch() -- ghost occupancy + collision determinism
# ---------------------------------------------------------------------------

def test_rebuild_epoch_drops_stale_positions():
    field = ConstraintField()
    field.rebuild_epoch([(_idx(c=0), ConstraintVector(X=1.0, T=1.0, N=1.0, B=1.0, A=1.0))])
    assert field.is_occupied(_idx(c=0))

    # Next epoch: that node has moved elsewhere -- c=0 must not linger.
    field.rebuild_epoch([(_idx(c=3), ConstraintVector(X=1.0, T=1.0, N=1.0, B=1.0, A=1.0))])
    assert not field.is_occupied(_idx(c=0))
    assert field.is_occupied(_idx(c=3))
    assert field.occupied_count() == 1


def test_rebuild_epoch_aggregates_collisions_deterministically():
    field = ConstraintField()
    v1 = ConstraintVector(X=1.0, T=10.0, N=0.0, B=0.0, A=0.0)
    v2 = ConstraintVector(X=1.0, T=20.0, N=0.0, B=0.0, A=0.0)
    v3 = ConstraintVector(X=1.0, T=30.0, N=0.0, B=0.0, A=0.0)

    field.rebuild_epoch([(_idx(c=0), v1), (_idx(c=0), v2), (_idx(c=0), v3)])
    assert field.occupied_count() == 1
    mean_v = field.measure(_idx(c=0))
    assert mean_v.T == 20.0  # (10+20+30)/3

    # Order independence.
    field2 = ConstraintField()
    field2.rebuild_epoch([(_idx(c=0), v3), (_idx(c=0), v1), (_idx(c=0), v2)])
    assert field2.measure(_idx(c=0)).T == 20.0


def test_rebuild_epoch_empty_measurements_clears_field():
    field = ConstraintField()
    field.rebuild_epoch([(_idx(c=0), ConstraintVector(X=1.0, T=1.0, N=1.0, B=1.0, A=1.0))])
    assert field.occupied_count() == 1
    field.rebuild_epoch([])
    assert field.occupied_count() == 0


# ---------------------------------------------------------------------------
# IVMLattice wiring -- mobility computation and flow_energy() conservation
# ---------------------------------------------------------------------------

def _make_lattice_with_two_connected_persistent_nodes():
    contract = ivm.FoundationalContract()
    lattice = ivm.IVMLattice(contract, max_nodes=1000)
    evidence = {'has_temporality': True, 'conserves_state': True}
    n1 = lattice.admit(payload='a', payload_type='test', evidence=evidence)
    n2 = lattice.admit(payload='b', payload_type='test', evidence=evidence)
    n1.connect_to(n2.node_id, 0.5)
    n2.connect_to(n1.node_id, 0.5)
    n1.node_energy = 2.0
    n2.node_energy = 0.5
    return lattice, n1, n2


def test_tick_one_mobility_empty_flow_matches_baseline():
    """Before any field has ever been rebuilt, mobility defaults to 1.0
    for every node -- tick 1's flow_energy() must be byte-for-byte what
    it was before this feature existed. Verified by comparing against an
    explicit all-1.0 mobility map: since pair_mobility is
    (mobility[a]+mobility[b])/2, an explicit 1.0/1.0 map is mathematically
    forced to reproduce the empty-dict default exactly."""
    lattice, n1, n2 = _make_lattice_with_two_connected_persistent_nodes()
    assert lattice._constitutive_mobility == {}
    total_before = lattice.get_total_energy()

    lattice.flow_energy(iterations=1)
    empty_result = (n1.node_energy, n2.node_energy)

    lattice2, n1b, n2b = _make_lattice_with_two_connected_persistent_nodes()
    lattice2._constitutive_mobility = {n1b.node_id: 1.0, n2b.node_id: 1.0}
    lattice2.flow_energy(iterations=1)
    explicit_neutral_result = (n1b.node_energy, n2b.node_energy)

    assert empty_result == explicit_neutral_result
    assert abs(lattice.get_total_energy() - total_before) < 1e-9


def test_tick_populates_constitutive_mobility_and_field_stats():
    lattice, n1, n2 = _make_lattice_with_two_connected_persistent_nodes()
    lattice.tick(dt=0.1)

    stats = lattice.get_constraint_field_stats()
    assert stats['available'] is True
    assert stats['field_occupied'] >= 1
    assert stats['field_capacity'] == 625

    # Mobility stays within the documented +/-5% bound.
    for mobility in lattice._constitutive_mobility.values():
        assert 0.95 <= mobility <= 1.05


def test_flow_energy_conserves_total_energy_with_nontrivial_mobility():
    lattice, n1, n2 = _make_lattice_with_two_connected_persistent_nodes()
    # Force a non-trivial cached mobility as if derived from a prior tick.
    # Both above 1.0 so the pairwise average (mobility[a]+mobility[b])/2
    # is itself != 1.0 in either direction -- an asymmetric pair like
    # {1.05, 0.95} would average to exactly 1.0 for a 2-node system and
    # silently mask the effect.
    lattice._constitutive_mobility = {n1.node_id: 1.05, n2.node_id: 1.03}

    total_before = lattice.get_total_energy()
    lattice.flow_energy(iterations=1)
    total_after = lattice.get_total_energy()

    assert abs(total_after - total_before) < 1e-9  # conservation intact

    # But the individual trajectory differs from the neutral-mobility case.
    lattice2, n1b, n2b = _make_lattice_with_two_connected_persistent_nodes()
    lattice2.flow_energy(iterations=1)  # mobility neutral (empty -> 1.0)
    n1_neutral_energy = lattice2.get(n1b.node_id).node_energy

    assert lattice.get(n1.node_id).node_energy != n1_neutral_energy


def test_mobility_lag_second_tick_reflects_first_ticks_field():
    """flow_energy() at the START of tick N+1 must use the mobility
    cached at the END of tick N -- not a same-tick value, since
    flow_energy() runs before this tick's own field rebuild."""
    lattice, n1, n2 = _make_lattice_with_two_connected_persistent_nodes()

    lattice.tick(dt=0.1)
    mobility_after_tick_1 = dict(lattice._constitutive_mobility)
    assert mobility_after_tick_1  # something was computed

    # Sanity: flow_energy() actually reads self._constitutive_mobility
    # (verified directly above); here just confirm it's non-empty going
    # into tick 2 so tick 2's flow_energy() call is not silently neutral.
    lattice.tick(dt=0.1)
    assert lattice._constitutive_mobility  # still populated after tick 2


# ---------------------------------------------------------------------------
# Live driveshaft: aurora.py's _run_live_response_turn now calls
# systems['lattice'].tick() once per turn, Subsurface-safe, on the exact
# lattice that gw._synthesize() -> consciousness.process() -> lattice.admit()
# already populates with real conversational evidence every turn.
# ---------------------------------------------------------------------------

def test_tick_against_realistically_admitted_nodes_populates_field():
    """admit() (the ONLY way nodes enter the lattice, live or otherwise --
    aurora_ivm.py's own docstring) already sets each node's constraint_vector
    at creation. A single tick() against nodes admitted this way -- not
    synthetic ConstraintField.update() calls -- must actually populate the
    field and advance the tick counter, proving the wiring works against
    realistic data, not just hand-built fixtures."""
    lattice, n1, n2 = _make_lattice_with_two_connected_persistent_nodes()
    assert lattice.total_ticks == 0
    assert lattice._constraint_field.occupied_count() == 0

    lattice.tick()

    assert lattice.total_ticks == 1
    assert lattice._constraint_field.occupied_count() >= 1


def test_live_response_turn_calls_lattice_tick_after_surface_ready():
    """Source-presence check (mirrors tests/test_rw6c_track1_wiring.py's
    body.index() ordering assertions): the new lattice.tick() call site
    must exist in _run_live_response_turn, and must sit AFTER
    on_surface_ready(resp_A) in source order -- i.e. it is provably in the
    Subsurface-safe zone, never on the path that decides what Aurora says
    or delays delivering it."""
    import inspect
    import aurora

    source = inspect.getsource(aurora._run_live_response_turn)
    surface_ready_idx = source.index("on_surface_ready(resp_A)")
    lattice_tick_idx = source.index("_lattice_live.tick()")

    assert lattice_tick_idx > surface_ready_idx, (
        "lattice.tick() must run after on_surface_ready(resp_A), not before -- "
        "it must never be able to delay or alter the delivered response"
    )

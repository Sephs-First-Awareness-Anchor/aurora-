"""
tests/test_mtsl_warp_gap_proposal.py
=======================================
MTSL, live-wired 2026-07-14: TopologicalSemanticCoordinator.propose_topology_gap()
feeds this coordinator's current topology organization into WARP's own
coverage-check machinery (WarpCapable.check_and_extend()) -- and the
throttled call to it from inside observe_turn() itself.

"Never promote by decree": every assertion here confirms a spawned
component is a TRIAL (promoted=False, trial_tick=0, trial_score_ema=0.0)
-- the exact same TRIAL_TICKS/PROMOTION_SCORE gate every other WARP
component goes through (evaluate_warp_trials(), untouched by this
module) is still what promotion requires.
"""
import time

from aurora_warp_protocol import WarpCapable
from aurora_internal.dual_strata.crest import Crest
from aurora_internal.dual_strata.topological_semantic_coordinator import (
    TopologicalSemanticCoordinator,
    WARP_GAP_CHECK_INTERVAL,
)

_AXES_CYCLE = [
    {"X": 0.5, "T": 0.5, "N": 0.7, "B": 0.5, "A": 0.3},
    {"X": 0.5, "T": 0.5, "N": 0.3, "B": 0.5, "A": 0.7},
    {"X": 0.5, "T": 0.5, "N": 0.5, "B": 0.7, "A": 0.3},
]
_CRESTS = (Crest(label="steady", intensity=0.6, axis="N"),)


class _MinimalWarpHost(WarpCapable):
    """Fully-controlled WarpCapable double -- lets a test pick an exact
    cosine-similarity band to the query profile without fighting DPS's
    own constraint_signature-to-I-state conversion."""

    def __init__(self, existing_profile):
        self._init_warp()
        self._existing_profile = existing_profile
        self.integrated = []

    def _get_axis_profiles(self):
        if self._existing_profile is None:
            return {}
        return {"existing": dict(self._existing_profile)}

    def _warp_level_name(self):
        return "test_level"

    def _integrate_warp(self, component):
        self.integrated.append(component)

    def _score_trial(self, component):
        return 0.0

    def _dissolve_warp(self, component_id):
        pass


def _driven_coordinator(n=60):
    coord = TopologicalSemanticCoordinator(state_dir=None)
    for i in range(n):
        coord.observe_turn(
            turn_id=f"t{i}", timestamp=time.time(), adjusted_axes=_AXES_CYCLE[i % 3],
            sub_crests=_CRESTS, dps=None,
        )
    return coord


# Cosine similarity ~0.5 to the driven fixture's dominant query profile
# (I_SOUGHT/I_DO-heavy) -- lands inside [ANOMALY_THRESHOLD, COVERAGE_THRESHOLD),
# a genuine gap rather than a 6th-axis anomaly (which generate() declines
# to instantiate) or full coverage (which check() returns None for).
_PARTIAL_COVERAGE_PROFILE = {"I_SOUGHT": 0.7, "I_IS": 0.7}


def test_no_dps_returns_none():
    coord = _driven_coordinator()
    assert coord.propose_topology_gap(None) is None


def test_dps_without_check_and_extend_returns_none():
    coord = _driven_coordinator()
    assert coord.propose_topology_gap(object()) is None


def test_quiescent_topology_returns_none():
    coord = TopologicalSemanticCoordinator(state_dir=None)
    coord.observe_turn(turn_id="t1", timestamp=time.time(), adjusted_axes=_AXES_CYCLE[0], sub_crests=_CRESTS, dps=None)
    host = _MinimalWarpHost({})
    assert coord.propose_topology_gap(host) is None  # not enough observations for a real signature yet


def test_empty_existing_coverage_is_anomaly_not_gap():
    # zero existing components at all -> AxisCoverageChecker.check() takes
    # its own "no components" early-return (None), same as "fully covered"
    # from propose_topology_gap's perspective -- confirms it doesn't
    # manufacture a component out of nothing.
    coord = _driven_coordinator()
    host = _MinimalWarpHost(None)
    for _ in range(WARP_GAP_CHECK_INTERVAL):
        assert coord.propose_topology_gap(host) is None
    assert host.integrated == []


def test_genuine_partial_coverage_gap_spawns_a_trial_after_persistence():
    coord = _driven_coordinator()
    host = _MinimalWarpHost(_PARTIAL_COVERAGE_PROFILE)
    results = [coord.propose_topology_gap(host) for _ in range(5)]
    winners = [r for r in results if r is not None]
    assert winners, f"expected a real trial component across 5 calls, got {results}"


def test_spawned_component_carries_a_real_topology_fingerprint_ref():
    coord = _driven_coordinator()
    host = _MinimalWarpHost(_PARTIAL_COVERAGE_PROFILE)
    results = [coord.propose_topology_gap(host) for _ in range(5)]
    winner = next(r for r in results if r is not None)
    assert winner.topology_gap_ref is not None
    assert winner.topology_gap_ref.startswith("TS:")


def test_spawned_component_is_never_promoted_by_decree():
    coord = _driven_coordinator()
    host = _MinimalWarpHost(_PARTIAL_COVERAGE_PROFILE)
    results = [coord.propose_topology_gap(host) for _ in range(5)]
    winner = next(r for r in results if r is not None)
    assert winner.promoted is False
    assert winner.trial_tick == 0
    assert winner.trial_score_ema == 0.0
    # the component now lives in the host's OWN trial bookkeeping,
    # subject to its normal evaluate_warp_trials() gate -- nothing about
    # this path bypasses it.
    assert winner.component_id in host._warp_trials
    assert winner.component_id not in host._warp_promoted


def test_full_coverage_returns_none():
    # existing coverage that's an exact (or near-exact) direction match
    # to the query -- check() itself returns None (fully covered), no
    # gap object at all.
    coord = _driven_coordinator()
    host = _MinimalWarpHost({"I_SOUGHT": 1.0, "I_DO": 0.5, "I_DONOT": 0.5, "I_DID": 0.5, "I_DIDNT": 0.5})
    results = [coord.propose_topology_gap(host) for _ in range(5)]
    assert all(r is None for r in results)


def test_explicit_scale_override():
    coord = _driven_coordinator()
    host = _MinimalWarpHost(_PARTIAL_COVERAGE_PROFILE)
    # micro scale should behave the same shape-wise (still either None or
    # a real trial, never raise)
    for _ in range(5):
        coord.propose_topology_gap(host, scale="micro")


# ---- throttled call from inside observe_turn() itself ----

def test_observe_turn_throttles_warp_gap_checks():
    host = _MinimalWarpHost(_PARTIAL_COVERAGE_PROFILE)
    coord = TopologicalSemanticCoordinator(state_dir=None)
    for i in range(WARP_GAP_CHECK_INTERVAL - 1):
        coord.observe_turn(
            turn_id=f"t{i}", timestamp=time.time(), adjusted_axes=_AXES_CYCLE[i % 3],
            sub_crests=_CRESTS, dps=host,
        )
    # fewer than WARP_GAP_CHECK_INTERVAL observations -> propose_topology_gap
    # should not have been attempted via observe_turn() yet, so no trial
    # exists regardless of coverage similarity
    assert host._warp_trials == {}


def test_observe_turn_eventually_attempts_a_gap_check():
    # gap persistence firing a trial depends on the topology signature
    # staying stable across throttled (20-turn-spaced) attempts, which
    # this fixture doesn't guarantee -- what observe_turn() itself
    # promises is *attempting* the check on the throttle cadence, so
    # that's what this test verifies directly (call-counting), rather
    # than asserting a trial is guaranteed to spawn.
    host = _MinimalWarpHost(_PARTIAL_COVERAGE_PROFILE)
    coord = TopologicalSemanticCoordinator(state_dir=None)
    calls = []
    real_propose = coord.propose_topology_gap

    def _counting_propose(dps, **kw):
        calls.append(coord._warp_gap_check_counter)
        return real_propose(dps, **kw)

    coord.propose_topology_gap = _counting_propose

    n = WARP_GAP_CHECK_INTERVAL * 4
    for i in range(n):
        coord.observe_turn(
            turn_id=f"t{i}", timestamp=time.time(), adjusted_axes=_AXES_CYCLE[i % 3],
            sub_crests=_CRESTS, dps=host,
        )
    assert len(calls) == n // WARP_GAP_CHECK_INTERVAL
    assert all(c % WARP_GAP_CHECK_INTERVAL == 0 for c in calls)


def test_observe_turn_never_crashes_when_dps_check_and_extend_raises():
    class _BoomHost:
        def check_and_extend(self, *a, **kw):
            raise RuntimeError("boom")

    coord = TopologicalSemanticCoordinator(state_dir=None)
    for i in range(WARP_GAP_CHECK_INTERVAL + 1):
        coord.observe_turn(
            turn_id=f"t{i}", timestamp=time.time(), adjusted_axes=_AXES_CYCLE[i % 3],
            sub_crests=_CRESTS, dps=_BoomHost(),
        )  # must not raise

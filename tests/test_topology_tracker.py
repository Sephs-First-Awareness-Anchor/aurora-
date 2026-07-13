"""
tests/test_topology_tracker.py
================================
MTSL Phase 1 (2026-07-13): TopologyTracker shadow-only topology
observation -- balanced flow attribution, multi-scale windows,
idempotent observe(), persistence, and replay.
"""
import os
import time

from aurora_internal.dual_strata.topology_frame import AXES, TopologyFrame
from aurora_internal.dual_strata.topology_tracker import (
    TopologyTracker,
    TopologyFingerprint,
    WINDOW_CONFIG,
    WINDOW_SCALES,
    _FlowWindow,
)


def _frame(turn_id, cur, prev=None, ts=None):
    return TopologyFrame.from_vectors(
        turn_id=turn_id,
        timestamp=ts if ts is not None else time.time(),
        constraint_vector=cur,
        previous_vector=prev or {a: 0.5 for a in AXES},
    )


# ---- balanced flow attribution physics ----

def test_flux_sums_to_transfer_mass_net_creation():
    # total gains (0.3 on N) exceed total losses (0.1 on X): net creation.
    w = _FlowWindow("micro")
    delta = {"X": -0.1, "T": 0.0, "N": 0.3, "B": 0.0, "A": 0.0}
    w.observe(delta)
    total_flux = sum(w._flux.values())
    transfer_mass = min(0.1, 0.3)
    assert abs(total_flux - transfer_mass) < 1e-9


def test_flux_sums_to_transfer_mass_net_dissipation():
    # total losses (0.4 on X) exceed total gains (0.1 on N): net dissipation.
    w = _FlowWindow("micro")
    delta = {"X": -0.4, "T": 0.0, "N": 0.1, "B": 0.0, "A": 0.0}
    w.observe(delta)
    total_flux = sum(w._flux.values())
    transfer_mass = min(0.4, 0.1)
    assert abs(total_flux - transfer_mass) < 1e-9


def test_flux_proportional_split_across_multiple_gainers():
    w = _FlowWindow("micro")
    # single loser X(-0.4) split proportionally across two gainers N(0.3), A(0.1)
    delta = {"X": -0.4, "T": 0.0, "N": 0.3, "B": 0.0, "A": 0.1}
    w.observe(delta)
    denom = max(0.4, 0.4)  # total_losses == total_gains == 0.4
    expected_xn = (0.4 * 0.3) / denom
    expected_xa = (0.4 * 0.1) / denom
    assert abs(w._flux[("X", "N")] - expected_xn) < 1e-9
    assert abs(w._flux[("X", "A")] - expected_xa) < 1e-9


def test_no_flux_when_all_losers_or_all_gainers():
    w = _FlowWindow("micro")
    delta = {"X": 0.1, "T": 0.1, "N": 0.1, "B": 0.0, "A": 0.0}
    w.observe(delta)
    assert sum(w._flux.values()) == 0.0


# ---- idempotent observe() by turn_id ----

def test_observe_same_turn_id_is_noop():
    tracker = TopologyTracker(state_dir=None)
    f1 = _frame("dup-turn", {"X": 0.7, "T": 0.5, "N": 0.5, "B": 0.5, "A": 0.5})
    assert tracker.observe(f1) is True
    assert tracker.observe(f1) is False
    sig = tracker.signature("micro")
    assert sig.observations == 1


def test_observe_distinct_turn_ids_both_count():
    tracker = TopologyTracker(state_dir=None)
    f1 = _frame("t1", {"X": 0.7, "T": 0.5, "N": 0.5, "B": 0.5, "A": 0.5})
    f2 = _frame("t2", {"X": 0.5, "T": 0.7, "N": 0.5, "B": 0.5, "A": 0.5}, prev=f1.constraint_vector)
    tracker.observe(f1)
    tracker.observe(f2)
    assert tracker.signature("micro").observations == 2


# ---- multi-scale window independence ----

def test_windows_are_independent_scales_all_present():
    tracker = TopologyTracker(state_dir=None)
    assert set(tracker.signatures().keys()) == set(WINDOW_SCALES)


def test_quiescent_below_min_observations():
    tracker = TopologyTracker(state_dir=None)
    prev = {a: 0.5 for a in AXES}
    cur = dict(prev)
    cur["X"] = 0.6
    cur["N"] = 0.4
    tracker.observe(_frame("t1", cur, prev))
    # developmental window needs 100 observations; one is nowhere near enough
    sig = tracker.signature("developmental")
    assert sig.regime == "quiescent"
    assert sig.loops == ()


def test_micro_window_reaches_activity_before_developmental():
    tracker = TopologyTracker(state_dir=None)
    prev = {a: 0.5 for a in AXES}
    turn = 0
    for _ in range(10):
        turn += 1
        cur = dict(prev)
        cur["X"] -= 0.2
        cur["N"] += 0.2
        tracker.observe(_frame(f"t{turn}", cur, prev))
        prev = cur
    micro_sig = tracker.signature("micro")
    dev_sig = tracker.signature("developmental")
    assert micro_sig.observations == 10
    assert micro_sig.regime != "quiescent"
    assert dev_sig.regime == "quiescent"  # still below its min_observations=100


# ---- cycle detection over a driven repeating pattern ----

def test_repeating_cycle_is_detected_as_circulating():
    tracker = TopologyTracker(state_dir=None)
    prev = {a: 0.5 for a in AXES}
    turn = 0
    steps = [("N", "A"), ("A", "B"), ("B", "N")]
    for _rep in range(20):
        for (loser, gainer) in steps:
            turn += 1
            cur = dict(prev)
            cur[loser] -= 0.2
            cur[gainer] += 0.2
            tracker.observe(_frame(f"t{turn}", cur, prev))
            prev = cur
    sig = tracker.signature("micro")
    assert sig.regime == "circulating"
    assert len(sig.loops) >= 1
    dominant_path, _strength = sig.loops[0]
    assert set(dominant_path) == {"N", "A", "B"}
    assert sig.circulation_fraction > 0.9


def test_persistence_grows_across_repeated_signature_calls_with_same_loop():
    tracker = TopologyTracker(state_dir=None)
    prev = {a: 0.5 for a in AXES}
    turn = 0
    steps = [("N", "A"), ("A", "B"), ("B", "N")]
    persistences = []
    for _check in range(3):
        for _rep in range(5):
            for (loser, gainer) in steps:
                turn += 1
                cur = dict(prev)
                cur[loser] -= 0.2
                cur[gainer] += 0.2
                tracker.observe(_frame(f"t{turn}", cur, prev))
                prev = cur
        persistences.append(tracker.signature("micro").persistence)
    assert persistences == sorted(persistences)
    assert persistences[-1] > persistences[0]


# ---- persistence (disk) round-trip ----

def test_state_round_trips_through_save_and_reload(tmp_path):
    state_dir = str(tmp_path)
    tracker = TopologyTracker(state_dir=state_dir)
    prev = {a: 0.5 for a in AXES}
    turn = 0
    steps = [("N", "A"), ("A", "B"), ("B", "N")]
    for _rep in range(10):
        for (loser, gainer) in steps:
            turn += 1
            cur = dict(prev)
            cur[loser] -= 0.2
            cur[gainer] += 0.2
            tracker.observe(_frame(f"t{turn}", cur, prev))
            prev = cur

    assert tracker.save() is True
    state_file = os.path.join(state_dir, "topology_tracker_state.json")
    assert os.path.exists(state_file)

    reloaded = TopologyTracker(state_dir=state_dir)
    assert reloaded.last_observed_turn_id == tracker.last_observed_turn_id
    for scale in WINDOW_SCALES:
        s1 = tracker.signature(scale)
        s2 = reloaded.signature(scale)
        assert s1.observations == s2.observations
        assert abs(s1.circulation_fraction - s2.circulation_fraction) < 1e-6


def test_save_without_dirty_state_returns_false(tmp_path):
    state_dir = str(tmp_path)
    tracker = TopologyTracker(state_dir=state_dir)
    # nothing observed yet -> not dirty
    assert tracker.save() is False


# ---- from_frames() replay ----

def test_from_frames_replay_matches_incremental_observation():
    prev = {a: 0.5 for a in AXES}
    turn = 0
    steps = [("N", "A"), ("A", "B"), ("B", "N")]
    frames = []
    for _rep in range(15):
        for (loser, gainer) in steps:
            turn += 1
            cur = dict(prev)
            cur[loser] -= 0.2
            cur[gainer] += 0.2
            frames.append(_frame(f"t{turn}", cur, prev, ts=float(turn)))
            prev = cur

    incremental = TopologyTracker(state_dir=None)
    for f in frames:
        incremental.observe(f)

    replayed = TopologyTracker.from_frames(frames)

    for scale in WINDOW_SCALES:
        s1 = incremental.signature(scale)
        s2 = replayed.signature(scale)
        assert s1.observations == s2.observations
        assert abs(s1.circulation_fraction - s2.circulation_fraction) < 1e-6


def test_from_frames_replay_is_order_independent_of_input_list_order():
    prev = {a: 0.5 for a in AXES}
    turn = 0
    steps = [("N", "A"), ("A", "B"), ("B", "N")]
    frames = []
    for _rep in range(15):
        for (loser, gainer) in steps:
            turn += 1
            cur = dict(prev)
            cur[loser] -= 0.2
            cur[gainer] += 0.2
            frames.append(_frame(f"t{turn}", cur, prev, ts=float(turn)))
            prev = cur

    shuffled = list(reversed(frames))
    replayed_in_order = TopologyTracker.from_frames(frames)
    replayed_shuffled = TopologyTracker.from_frames(shuffled)  # from_frames sorts by timestamp

    for scale in WINDOW_SCALES:
        s1 = replayed_in_order.signature(scale)
        s2 = replayed_shuffled.signature(scale)
        assert s1.observations == s2.observations
        assert abs(s1.circulation_fraction - s2.circulation_fraction) < 1e-6


# ---- TopologyFingerprint property tests ----

def _ready_window(scale="micro"):
    w = _FlowWindow(scale)
    w._observations = WINDOW_CONFIG[scale]["min_observations"]
    return w


def test_fingerprint_stable_under_small_noise():
    w1 = _ready_window()
    w1._flux[("X", "T")] = 5.0
    w1._flux[("T", "N")] = 5.0
    w1._flux[("N", "X")] = 5.0
    fp1 = TopologyFingerprint.from_signature(w1.signature())

    # perturb every edge by +/-2%
    w2 = _ready_window()
    w2._flux[("X", "T")] = 5.0 * 1.02
    w2._flux[("T", "N")] = 5.0 * 0.98
    w2._flux[("N", "X")] = 5.0 * 1.01
    fp2 = TopologyFingerprint.from_signature(w2.signature())

    assert fp1.fingerprint_id == fp2.fingerprint_id


def test_fingerprint_changes_on_meaningful_edge_direction_flip():
    w1 = _ready_window()
    w1._flux[("X", "T")] = 5.0
    w1._flux[("T", "N")] = 5.0
    w1._flux[("N", "X")] = 5.0
    fp1 = TopologyFingerprint.from_signature(w1.signature())

    # flip the cycle's direction entirely: X->N->T->X instead of X->T->N->X
    w2 = _ready_window()
    w2._flux[("X", "N")] = 5.0
    w2._flux[("N", "T")] = 5.0
    w2._flux[("T", "X")] = 5.0
    fp2 = TopologyFingerprint.from_signature(w2.signature())

    assert fp1.fingerprint_id != fp2.fingerprint_id


def test_fingerprint_never_includes_ivm_phase():
    # TopologySignature (what fingerprints are derived from) has no
    # ivm_phase field at all -- assert that explicitly, since P3 in the
    # MTSL directive requires ivm_phase be excluded from fingerprinting
    # as an observation-firewall guarantee, not an incidental omission.
    w = _ready_window()
    w._flux[("X", "T")] = 5.0
    w._flux[("T", "N")] = 5.0
    w._flux[("N", "X")] = 5.0
    sig = w.signature()
    assert not hasattr(sig, "ivm_phase")
    fp = TopologyFingerprint.from_signature(sig)
    assert "ivm_phase" not in fp.to_dict()

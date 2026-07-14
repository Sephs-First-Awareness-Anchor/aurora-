"""
tests/test_topological_semantic_coordinator.py
==================================================
MTSL Phase 3 (2026-07-13): TopologicalSemanticCoordinator -- single-
observer idempotency, multi-scale signature production, semantic
variant integration, meaning-shadow logging, understanding
classification, and outcome plumbing.
"""
import json
import os
import time

from aurora_dimensional_systems import CrystalProcessingSystem, EvolutionTracker
from aurora_internal.dual_strata.crest import Crest
from aurora_internal.dual_strata.topological_semantic_coordinator import (
    TopologicalSemanticCoordinator,
    SHADOW_COMPARISON_FILENAME,
)
from aurora_internal.dual_strata.topology_tracker import WINDOW_SCALES

_CYCLE = [
    {"X": 0.5, "T": 0.5, "N": 0.7, "B": 0.5, "A": 0.3},
    {"X": 0.5, "T": 0.5, "N": 0.3, "B": 0.5, "A": 0.7},
    {"X": 0.5, "T": 0.5, "N": 0.5, "B": 0.7, "A": 0.3},
]
_CRESTS = (Crest(label="steady", intensity=0.6, axis="N"),)


def _dps():
    return CrystalProcessingSystem(tracker=EvolutionTracker())


def _drive(coord, dps, n=30, context_family="conversation"):
    snaps = []
    for i in range(n):
        snaps.append(coord.observe_turn(
            turn_id=f"turn-{i}", timestamp=time.time(),
            adjusted_axes=_CYCLE[i % 3], sub_crests=_CRESTS,
            context_family=context_family, dps=dps,
        ))
    return snaps


# ---- single-observer / idempotency law ----

def test_repeat_turn_id_returns_cached_snapshot_object():
    coord = TopologicalSemanticCoordinator(state_dir=None)
    dps = _dps()
    s1 = coord.observe_turn(turn_id="t1", timestamp=time.time(), adjusted_axes=_CYCLE[0],
                             sub_crests=_CRESTS, dps=dps)
    s2 = coord.observe_turn(turn_id="t1", timestamp=time.time(), adjusted_axes=_CYCLE[1],
                             sub_crests=_CRESTS, dps=dps)
    assert s1 is s2  # identity, not just equality -- proves no re-observation happened


def test_distinct_turn_ids_both_observe():
    coord = TopologicalSemanticCoordinator(state_dir=None)
    dps = _dps()
    s1 = coord.observe_turn(turn_id="t1", timestamp=time.time(), adjusted_axes=_CYCLE[0],
                             sub_crests=_CRESTS, dps=dps)
    s2 = coord.observe_turn(turn_id="t2", timestamp=time.time(), adjusted_axes=_CYCLE[1],
                             sub_crests=_CRESTS, dps=dps)
    assert s1 is not s2
    assert s1.turn_id == "t1" and s2.turn_id == "t2"


def test_double_observation_rate_reflects_repeats_not_fresh_turns():
    coord = TopologicalSemanticCoordinator(state_dir=None)
    dps = _dps()
    _drive(coord, dps, n=10)
    assert coord.double_observation_rate == 0.0
    coord.observe_turn(turn_id="turn-9", timestamp=time.time(), adjusted_axes=_CYCLE[0],
                        sub_crests=_CRESTS, dps=dps)
    assert coord.double_observation_rate > 0.0
    assert coord.observation_count == 11


# ---- multi-scale signatures ----

def test_snapshot_carries_all_window_scales():
    coord = TopologicalSemanticCoordinator(state_dir=None)
    dps = _dps()
    snaps = _drive(coord, dps, n=15)
    assert set(snaps[-1].topology_signatures.keys()) == set(WINDOW_SCALES)


def test_dominant_scale_is_used_for_variant_matching():
    coord = TopologicalSemanticCoordinator(state_dir=None)
    dps = _dps()
    snaps = _drive(coord, dps, n=30)
    assert snaps[-1].dominant_scale == "meso"


# ---- semantic variant integration ----

def test_repeated_topic_reinforces_same_variant():
    # _CYCLE rotates through 3 axes dicts with 3 different dominant axes,
    # so each cycle position resolves to its OWN manifold coordinate
    # (target = the tick's most-active axis) -- reinforcement should be
    # checked per cycle position, not across the whole run.
    coord = TopologicalSemanticCoordinator(state_dir=None)
    dps = _dps()
    snaps = _drive(coord, dps, n=40)
    ids = [s.semantic_variant_id for s in snaps if s.semantic_variant_id]
    assert ids, "expected at least one semantic variant to be matched/created"
    for offset in range(3):
        same_position_ids = [snaps[i].semantic_variant_id for i in range(offset, len(snaps), 3)
                              if snaps[i].semantic_variant_id]
        assert len(same_position_ids) >= 3
        assert len(set(same_position_ids[-3:])) == 1, (
            f"cycle position {offset} did not reinforce a single variant: {same_position_ids[-3:]}"
        )


def test_no_dps_degrades_gracefully_without_variant():
    coord = TopologicalSemanticCoordinator(state_dir=None)
    snap = coord.observe_turn(turn_id="t1", timestamp=time.time(), adjusted_axes=_CYCLE[0],
                               sub_crests=_CRESTS, dps=None)
    assert snap.semantic_variant_id is None
    assert snap.manifold_slot_id is not None  # coordinate resolution doesn't need dps


# ---- toroidal circulation layer ownership (FIX-A011 retroactive) ----

def test_toroidal_signature_is_populated_and_advances():
    coord = TopologicalSemanticCoordinator(state_dir=None)
    dps = _dps()
    snaps = _drive(coord, dps, n=10)
    assert snaps[-1].toroidal_signature
    assert "observations" in snaps[-1].toroidal_signature
    assert snaps[-1].toroidal_signature["observations"] >= snaps[0].toroidal_signature["observations"]


# ---- understanding classification (spec 14 three-way distinction) ----

def test_no_topic_when_no_base_forms_activate():
    coord = TopologicalSemanticCoordinator(state_dir=None)
    dps = _dps()
    flat_axes = {"X": 0.1, "T": 0.1, "N": 0.1, "B": 0.1, "A": 0.1}
    snap = coord.observe_turn(turn_id="t1", timestamp=time.time(), adjusted_axes=flat_axes,
                               sub_crests=(), dps=dps)
    assert snap.understanding_classification == "no_topic"


def test_resolved_once_a_variant_is_matched_without_family_ambiguity():
    coord = TopologicalSemanticCoordinator(state_dir=None)
    dps = _dps()
    snaps = _drive(coord, dps, n=30)
    assert any(s.understanding_classification == "resolved" for s in snaps)


# ---- meaning-shadow comparison log (computed + logged only) ----

def test_shadow_comparison_log_written_per_fresh_turn(tmp_path):
    state_dir = str(tmp_path)
    coord = TopologicalSemanticCoordinator(state_dir=state_dir)
    dps = _dps()
    _drive(coord, dps, n=5)
    log_path = os.path.join(state_dir, SHADOW_COMPARISON_FILENAME)
    assert os.path.exists(log_path)
    with open(log_path) as fh:
        lines = [json.loads(l) for l in fh if l.strip()]
    assert len(lines) == 5
    for entry in lines:
        assert "turn_id" in entry
        assert "semantic_ambiguity" in entry
        assert "dominant_base_form" in entry


def test_shadow_log_not_written_on_repeat_turn_id(tmp_path):
    state_dir = str(tmp_path)
    coord = TopologicalSemanticCoordinator(state_dir=state_dir)
    dps = _dps()
    coord.observe_turn(turn_id="t1", timestamp=time.time(), adjusted_axes=_CYCLE[0],
                        sub_crests=_CRESTS, dps=dps)
    coord.observe_turn(turn_id="t1", timestamp=time.time(), adjusted_axes=_CYCLE[1],
                        sub_crests=_CRESTS, dps=dps)
    log_path = os.path.join(state_dir, SHADOW_COMPARISON_FILENAME)
    with open(log_path) as fh:
        lines = [l for l in fh if l.strip()]
    assert len(lines) == 1  # the repeat call never re-logged


# ---- record_turn_outcome plumbing (no authority; nothing calls this automatically) ----

def test_record_turn_outcome_routes_to_matched_variant():
    coord = TopologicalSemanticCoordinator(state_dir=None)
    dps = _dps()
    snaps = _drive(coord, dps, n=30)
    assert snaps[-1].semantic_variant_id is not None
    before = snaps[-1].variant_confidence
    result = coord.record_turn_outcome(positive=True, dps=dps)
    assert result is not None
    assert result.outcome_positive >= 1


def test_record_turn_outcome_none_without_prior_observation():
    coord = TopologicalSemanticCoordinator(state_dir=None)
    dps = _dps()
    result = coord.record_turn_outcome(positive=True, dps=dps)
    assert result is None


def test_record_turn_outcome_none_without_variant_match():
    coord = TopologicalSemanticCoordinator(state_dir=None)
    coord.observe_turn(turn_id="t1", timestamp=time.time(), adjusted_axes=_CYCLE[0],
                        sub_crests=(), dps=None)
    result = coord.record_turn_outcome(positive=True, dps=_dps())
    assert result is None


# ---- persistence round-trip (delegated to owned TopologyTracker/SemanticVariantRegistry) ----

def test_tracker_and_registry_state_persist_across_fresh_coordinator_instances(tmp_path):
    state_dir = str(tmp_path)
    dps = _dps()
    coord1 = TopologicalSemanticCoordinator(state_dir=state_dir)
    snaps = _drive(coord1, dps, n=30)
    assert snaps[-1].semantic_variant_id is not None

    coord2 = TopologicalSemanticCoordinator(state_dir=state_dir)
    sig2 = coord2._tracker.signature("meso")
    assert sig2.observations == snaps[-1].topology_signatures["meso"]["observations"]


# ---- frame-history buffer (feeds PerturbationProbe with real recent history) ----

def test_recent_frames_empty_before_any_observation():
    coord = TopologicalSemanticCoordinator(state_dir=None)
    assert coord.recent_frames() == ()


def test_recent_frames_grows_with_observations():
    coord = TopologicalSemanticCoordinator(state_dir=None)
    dps = _dps()
    _drive(coord, dps, n=10)
    assert len(coord.recent_frames()) == 10


def test_recent_frames_caps_at_maxlen():
    from aurora_internal.dual_strata.topological_semantic_coordinator import FRAME_HISTORY_MAXLEN
    coord = TopologicalSemanticCoordinator(state_dir=None)
    dps = _dps()
    _drive(coord, dps, n=FRAME_HISTORY_MAXLEN + 20)
    assert len(coord.recent_frames()) == FRAME_HISTORY_MAXLEN


def test_recent_frames_n_returns_only_the_tail():
    coord = TopologicalSemanticCoordinator(state_dir=None)
    dps = _dps()
    _drive(coord, dps, n=20)
    all_frames = coord.recent_frames()
    last5 = coord.recent_frames(5)
    assert last5 == all_frames[-5:]


def test_recent_frames_are_real_topology_frames_usable_by_perturbation_probe():
    from aurora_internal.dual_strata.perturbation_probe import PerturbationProbe
    coord = TopologicalSemanticCoordinator(state_dir=None)
    dps = _dps()
    _drive(coord, dps, n=30)
    probe = PerturbationProbe(coord.recent_frames())
    result = probe.occlude("N")
    assert result.perturbation_type == "occlusion"
